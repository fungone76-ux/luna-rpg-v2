# file: core/prompt_builder.py
from __future__ import annotations
from typing import Dict, List, Tuple

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None


def _get_outfit_prompt(char_data: Dict, outfit_key: str) -> str:
    """Recupera l'outfit dal database gestendo pesi e formattazione."""
    wardrobe = char_data.get("wardrobe", {})
    # Cerca l'outfit specifico, altrimenti fallback su 'default', altrimenti usa la chiave stessa
    raw_outfit = wardrobe.get(outfit_key, wardrobe.get("default", outfit_key))

    if not raw_outfit:
        return ""

    # Formattazione per SD: Aggiunge (wearing ...) se manca
    if "wearing" not in raw_outfit.lower() and "nude" not in raw_outfit.lower():
        return f"(wearing {raw_outfit}:1.2)"
    return f"({raw_outfit}:1.2)"


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """
    Costruisce il prompt analizzando il testo per trovare NPC specifici
    e garantendo coerenza di luogo e vestiti.
    """

    style_data = world_data.get("visual_style", {})
    base_env_prompt = style_data.get("base_prompt", "masterpiece, best quality")
    base_negative = style_data.get("negative_prompt", "low quality, bad anatomy")

    # --- DATI DI STATO ---
    companion_name = game_state.get("companion_name", "")
    current_outfit_key = game_state.get("current_outfit", "default")
    current_location = game_state.get("location", "Unknown Location")
    inventory = game_state.get("inventory", [])

    # --- 1. INTELLIGENCE: CHI È IL SOGGETTO? ---

    # Dati grezzi dall'LLM
    declared_subject = game_state.get("image_subject", "").lower()
    visual_text_lower = visual_en.lower()

    companions_db = world_data.get("companions", {})

    # SCANNER: Cerchiamo se un altro personaggio (es. Stella) è nominato nel testo visivo.
    # Questo ha la priorità su tutto.
    detected_npc_name = None
    for name in companions_db.keys():
        # Se il nome è nel testo E non è la compagna attuale
        if name.lower() in visual_text_lower and name.lower() != companion_name.lower():
            detected_npc_name = name
            break

            # DECISIONE DEL FOCUS
    if detected_npc_name:
        focus_target = "npc_key"  # Trovata Stella/Maria!
    elif companion_name.lower() in declared_subject or declared_subject in ["partner", "companion", "self"]:
        focus_target = "partner"  # L'LLM dice esplicitamente che è la partner
    elif declared_subject == "":
        # Se l'LLM tace, cerchiamo il nome della partner nel testo
        if companion_name.lower() in visual_text_lower:
            focus_target = "partner"
        else:
            focus_target = "generic"  # Nessun nome trovato
    else:
        focus_target = "generic"  # Mostri, Ambiente, Oggetti

    # --- 2. COSTRUZIONE PROMPT ---
    prompt_parts = [base_env_prompt]

    # CASO A: NPC CHIAVE (Stella, Maria, ecc.)
    if focus_target == "npc_key":
        char_data = companions_db[detected_npc_name]
        prompt_parts.append(char_data.get("base_prompt", ""))  # LoRA specifico NPC

        # Outfit NPC (Default)
        npc_outfit = char_data.get("default_outfit", "clothing")
        prompt_parts.append(_get_outfit_prompt(char_data, npc_outfit))

        # Aggiunta contesto nemici (es. se ci sono uomini che la molestano)
        if any(x in visual_text_lower for x in ["men", "drunks", "guys", "clients"]):
            prompt_parts.append("background characters, angry men")

    # CASO B: PARTNER (Luna)
    elif focus_target == "partner":
        if companion_name in companions_db:
            char_data = companions_db[companion_name]
            prompt_parts.append(char_data.get("base_prompt", ""))  # LoRA Luna

            # Outfit Attuale (Coerenza)
            prompt_parts.append(_get_outfit_prompt(char_data, current_outfit_key))

            # Dettagli contestuali dinamici
            if "dirty" in visual_text_lower or "rags" in visual_text_lower:
                prompt_parts.append("dirty clothes, grime, sweat")

            # Controllo Inventario (Armi)
            if any(w in inventory for w in ["Spada", "Sword", "Dagger", "Weapon"]):
                # Aggiunge l'arma solo se c'è azione
                if any(x in visual_text_lower for x in ["fight", "battle", "holding", "attack"]):
                    prompt_parts.append("holding a weapon, holding sword")

    # CASO C: GENERICO / NEMICI / AMBIENTE
    else:
        # Analisi euristica
        npc_logic = world_data.get("npc_logic", {})

        is_monster = any(x in visual_text_lower for x in ["monster", "orc", "goblin", "beast", "creature"])
        is_men = any(x in visual_text_lower for x in ["men", "drunks", "guys", "clients", "thugs", "guards"])
        is_env = "no humans" in tags_en or "scenery" in tags_en or "landscape" in visual_text_lower

        if is_monster:
            prompt_parts.append(f"({declared_subject}:1.3), monster, creature, threatening, horror")
        elif is_men:
            # Usa prompt maschile generico se disponibile
            base_male = npc_logic.get("male_prompt", "1boy, male focus, detailed male")
            prompt_parts.append(f"{base_male}, angry, rough")
        elif is_env:
            prompt_parts.append("scenery, no humans, detailed environment, atmospheric")
        else:
            # Fallback sul soggetto dichiarato
            clean_subj = declared_subject if declared_subject else "detailed scene"
            prompt_parts.append(f"({clean_subj}:1.2)")

    # --- 3. AGGIUNTE FINALI ---

    # Descrizione Artistica LLM
    prompt_parts.append(visual_en)

    # LOCATION ANCHOR (Failsafe)
    # Se il testo non menziona il luogo, lo forziamo noi per coerenza
    if current_location and current_location.lower() not in visual_en.lower():
        prompt_parts.append(f"background is {current_location}, detailed background")

    # TAGS
    clean_tags = [t.strip() for t in tags_en if t.strip()]
    prompt_parts.append(", ".join(clean_tags))

    # LORAS GLOBALI (Stile)
    global_loras = style_data.get("loras", [])
    if global_loras:
        prompt_parts.extend(global_loras)

    # Assemblaggio
    full_prompt_str = ", ".join(prompt_parts)

    # Context per regole extra
    context = (visual_en + " " + full_prompt_str).lower()
    return _finalize_prompt(full_prompt_str, base_negative, clean_tags, visual_en, context)


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg