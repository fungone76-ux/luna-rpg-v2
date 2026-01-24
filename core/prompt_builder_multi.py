# file: core/prompt_builder_multi.py
from __future__ import annotations
from typing import Dict, List, Tuple

from core.prompt_builder import BASE_PROMPTS, NPC_BASE

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

# --- Boost per l'interazione ---
INTERACTION_BOOST = (
    "dynamic composition, interacting, multiple subjects, "
    "coherent interaction, scene coherence, detailed composition, "
    "group shot"
)

# Negative Prompt Specifico per Gruppi (Anti-Clone)
MULTI_NEGATIVE = (
    "score_5, score_4, low quality, anime, monochrome, deformed, bad anatomy, "
    "worst face, extra fingers, cartoon, 3d render, "
    "(same face:1.4), (twins:1.4), (clones:1.4), (same hair color:1.2), "
    "floating limbs, disconnected bodies, (split view:1.3)"
)


def _get_outfit_for_multi(char_name: str, game_state: Dict, world_data: Dict) -> str:
    # 1. Identifica chiave outfit
    current_outfit_key = "default"
    if char_name == game_state.get("companion_name"):
        current_outfit_key = game_state.get("current_outfit", "default")
    else:
        companions_db = world_data.get("companions", {})
        char_data = companions_db.get(char_name, {})
        current_outfit_key = char_data.get("default_outfit", "default")

    # 2. Recupera descrizione
    companions_db = world_data.get("companions", {})
    char_data = companions_db.get(char_name, {})
    wardrobe = char_data.get("wardrobe", {})
    outfit_desc = wardrobe.get(current_outfit_key, "")

    if not outfit_desc:
        outfit_desc = wardrobe.get("default", "clothing")

    # 3. Pulizia e Formattazione
    clean_desc = str(outfit_desc).lower().replace("wearing ", "").strip()
    clean_desc = clean_desc.replace("(", "").replace(")", "")

    nude_keywords = ["naked", "nude", "undressed", "nothing"]

    # OTTIMIZZAZIONE: Peso ridotto da 1.3 a 1.2 per blending migliore
    if any(k in clean_desc for k in nude_keywords):
        return f"(nude:1.2), {clean_desc}"
    else:
        return f"(wearing {clean_desc}:1.2)"


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        subjects: List[str],
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """
    Costruisce il prompt Multi-Soggetto con 'Scene Grounding'.
    Ogni personaggio riceve la Location per evitare sfondi disconnessi.
    """

    # 1. Preparazione Dati Comuni
    loc = game_state.get("location", "")
    loc_fragment = f", background is {loc}" if loc else ""

    num_girls = len(subjects)
    count_tag = f"{num_girls}girls" if num_girls > 1 else "2girls"

    prompt_parts = [count_tag]

    # 2. Loop Personaggi (Con Scene Grounding)
    for name in subjects:
        base = BASE_PROMPTS.get(name, NPC_BASE)
        # Rimuove 1girl e score per pulizia nel blocco
        base = base.replace("1girl,", "").replace("1girl", "").strip()

        outfit = _get_outfit_for_multi(name, game_state, world_data)

        # INIEZIONE LOC: Aggiungiamo lo sfondo a OGNI personaggio
        # Questo costringe SD a disegnare Luna AL CANCELLO e Stella AL CANCELLO.
        prompt_parts.append(f"({base}, {outfit}{loc_fragment})")
        prompt_parts.append("BREAK")

    # 3. Contesto Globale & Interazione
    global_context = []

    global_context.append(INTERACTION_BOOST)

    # Filtro migliorato: toglie anche le varianti con spazi
    banned = [
        "best quality", "masterpiece", "score_9", "score_8_up",
        "1girl", "2girls", "3girls",
        "1 girl", "2 girls", "3 girls", "girls"
    ]
    clean_tags = [t for t in tags_en if t.lower() not in banned]

    # L'azione descritta dall'LLM (visual_en) è prioritaria nel blocco finale
    if visual_en:
        global_context.append(f"({visual_en}:1.1)")

    if clean_tags:
        global_context.append(", ".join(clean_tags))

    # Aggiungiamo la location anche al global per sicurezza
    if loc:
        global_context.append(f"background is {loc}")

    if global_context:
        prompt_parts.append(", ".join(global_context))

    # Assemblaggio Finale
    full_prompt_str = " ".join([p.strip().strip(",") for p in prompt_parts if p])

    return _finalize_prompt(full_prompt_str, MULTI_NEGATIVE, tags_en, visual_en, "multi")


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg