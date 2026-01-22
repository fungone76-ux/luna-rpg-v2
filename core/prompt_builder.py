# file: core/prompt_builder.py
from __future__ import annotations
from typing import Dict, List, Tuple

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None


def _get_char_prompt_data(char_name: str, char_data: Dict, game_state: Dict, is_group: bool) -> str:
    """
    Costruisce la stringa base + outfit.
    Gestisce in modo intelligente '1girl' e 'wearing'.
    """
    # 1. Base Prompt (LoRA ecc)
    base = char_data.get("base_prompt", "")

    # SE siamo in gruppo, togliamo i riferimenti singoli per non confondere l'IA
    if is_group:
        base = base.replace("1girl,", "").replace("1girl", "").strip()

    # 2. Outfit Logic
    current_partner = game_state.get("companion_name", "")
    wardrobe = char_data.get("wardrobe", {})

    outfit_desc = ""
    # Se è la partner attuale, usa l'outfit dallo stato
    if char_name == current_partner:
        outfit_key = game_state.get("current_outfit", "default")
        # Fallback intelligente: se l'outfit non esiste, cerca 'default', altrimenti 'clothing'
        outfit_desc = wardrobe.get(outfit_key, wardrobe.get("default", "clothing"))
    else:
        # Se è un NPC, usa il suo default
        default_key = char_data.get("default_outfit", "default")
        outfit_desc = wardrobe.get(default_key, "clothing")

    # 3. Controllo "Wearing" (BLINDATO)
    # Rimuoviamo parentesi extra se presenti nel YAML per pulizia
    outfit_clean = outfit_desc.replace("(", "").replace(")", "")

    final_outfit_str = ""

    # Se è nuda, non aggiungiamo 'wearing'
    if any(x in outfit_clean.lower() for x in ["nude", "naked", "nothing"]):
        final_outfit_str = f"({outfit_clean}:1.2)"
    else:
        # Se c'è già un verbo di vestizione, non aggiungiamo nulla
        if any(v in outfit_clean.lower() for v in ["wearing", "dressed", "clad", "suit"]):
            final_outfit_str = f"({outfit_clean}:1.2)"
        else:
            # Altrimenti aggiungiamo 'wearing'
            final_outfit_str = f"(wearing {outfit_clean}:1.2)"

    return f"{base}, {final_outfit_str}"


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """
    Generatore di Prompt Unificato e Pulito.
    """

    style_data = world_data.get("visual_style", {})
    base_env_prompt = style_data.get("base_prompt", "masterpiece, best quality")

    # Negativo rinforzato contro i cloni
    base_negative = style_data.get("negative_prompt", "low quality")
    forced_negative = (
        f"{base_negative}, (same face:1.4), (twins:1.4), (clones:1.4), "
        "monochrome, greyscale, text, watermark, (same hair color:1.2), mutation, deformed"
    )

    visual_text_lower = visual_en.lower()
    # Uniamo i tag LLM in una stringa pulita
    tags_string = ", ".join(tags_en).lower()
    full_text_search = f"{visual_text_lower} {tags_string}"

    companions_db = world_data.get("companions", {})

    # --- 1. SCANNER PERSONAGGI ---
    found_chars = []

    # Cerca i nomi nel testo
    for name in companions_db.keys():
        if name.lower() in full_text_search:
            found_chars.append(name)

    # Fallback: Se non trova nessuno, metti la compagna attuale
    current_partner = game_state.get("companion_name")
    if not found_chars and current_partner:
        found_chars.append(current_partner)

    # Rimuovi duplicati mantenendo l'ordine
    found_chars = list(dict.fromkeys(found_chars))

    is_group_scene = len(found_chars) >= 2

    # --- 2. COSTRUZIONE PROMPT ---
    prompt_parts = [base_env_prompt]

    # Header Gruppo (se necessario)
    if is_group_scene:
        count_tag = f"{len(found_chars)}girls"
        # Aggiungiamo BREAK per separare meglio i concetti se usi A1111/Forge, altrimenti virgole
        prompt_parts.append(f"({count_tag}:1.3), interacting, distinct females")

    # Ciclo Unificato sui Personaggi (Così il controllo wearing vale per TUTTI)
    for char_name in found_chars:
        char_data = companions_db[char_name]
        # Chiamiamo la funzione helper corretta
        p_data = _get_char_prompt_data(char_name, char_data, game_state, is_group_scene)
        prompt_parts.append(p_data)

        # Se è un gruppo, aggiungiamo un BREAK per evitare che i capelli si mischino
        if is_group_scene:
            prompt_parts.append("BREAK")

    # --- 3. AMBIENTE E AZIONE ---
    # Descrizione scena LLM pulita
    clean_visual = visual_en.replace(".", ",").replace("(", "").replace(")", "")
    prompt_parts.append(f"({clean_visual}:1.1)")

    # Location Anchor (solo se non già detta)
    loc = game_state.get("location", "")
    if loc and loc.lower() not in visual_text_lower:
        prompt_parts.append(f"background is {loc}")

    # Tags LLM
    if tags_en:
        prompt_parts.append(", ".join(tags_en))

    # LoRAs Globali (Stile)
    global_loras = style_data.get("loras", [])
    if global_loras:
        prompt_parts.extend(global_loras)

    # Assemblaggio finale
    # Pulizia virgole doppie o spazi vuoti
    full_prompt_str = ", ".join([p for p in prompt_parts if p and p != "BREAK"])

    # Se usiamo BREAK, la formattazione è diversa (opzionale per compatibilità)
    if "BREAK" in prompt_parts:
        full_prompt_str = " ".join(prompt_parts)  # Usa spazi per i BREAK

    return _finalize_prompt(full_prompt_str, forced_negative, tags_en, visual_en, full_text_search)


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg