# file: core/prompt_builder_multi.py
from __future__ import annotations
from typing import Dict, List, Tuple

from core.prompt_builder import BASE_PROMPTS, NPC_BASE

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

# --- NUOVO: Boost per l'interazione ---
# Aiuta SD a capire che non sono due statue separate
INTERACTION_BOOST = (
    "dynamic composition, interacting, multiple subjects, "
    "coherent interaction, scene coherence, detailed composition"
)

# Negative Prompt Specifico per Gruppi (Anti-Clone)
MULTI_NEGATIVE = (
    "score_5, score_4, low quality, anime, monochrome, deformed, bad anatomy, "
    "worst face, extra fingers, cartoon, 3d render, "
    "(same face:1.4), (twins:1.4), (clones:1.4), (same hair color:1.2), "
    "floating limbs, disconnected bodies"
)


def _get_outfit_for_multi(char_name: str, game_state: Dict, world_data: Dict) -> str:
    # ... (Il codice dell'outfit rimane identico a prima) ...
    # Per brevità copio solo la logica essenziale:
    current_outfit_key = "default"
    if char_name == game_state.get("companion_name"):
        current_outfit_key = game_state.get("current_outfit", "default")
    else:
        companions_db = world_data.get("companions", {})
        char_data = companions_db.get(char_name, {})
        current_outfit_key = char_data.get("default_outfit", "default")

    companions_db = world_data.get("companions", {})
    char_data = companions_db.get(char_name, {})
    wardrobe = char_data.get("wardrobe", {})
    outfit_desc = wardrobe.get(current_outfit_key, "")
    if not outfit_desc:
        outfit_desc = wardrobe.get("default", "clothing")

    clean_desc = str(outfit_desc).lower().replace("wearing ", "").strip()
    clean_desc = clean_desc.replace("(", "").replace(")", "")

    nude_keywords = ["naked", "nude", "undressed", "nothing"]
    if any(k in clean_desc for k in nude_keywords):
        return f"(nude:1.3), {clean_desc}"
    else:
        return f"(wearing {clean_desc}:1.3)"


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        subjects: List[str],
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """
    Costruisce il prompt Multi-Soggetto con Interaction Boost.
    """

    # 1. Header
    num_girls = len(subjects)
    count_tag = f"{num_girls}girls" if num_girls > 1 else "2girls"

    prompt_parts = [count_tag]

    # 2. Loop Personaggi
    for name in subjects:
        base = BASE_PROMPTS.get(name, NPC_BASE)
        base = base.replace("1girl,", "").replace("1girl", "").strip()
        outfit = _get_outfit_for_multi(name, game_state, world_data)

        prompt_parts.append(f"({base}, {outfit})")
        prompt_parts.append("BREAK")

    # 3. Contesto Globale & INTERAZIONE
    global_context = []

    # Aggiungiamo SUBITO i booster di interazione
    global_context.append(INTERACTION_BOOST)

    banned = ["best quality", "masterpiece", "score_9", "1girl", "2girls", "3girls"]
    clean_tags = [t for t in tags_en if t.lower() not in banned]

    if visual_en:
        global_context.append(f"({visual_en}:1.1)")

    if clean_tags:
        global_context.append(", ".join(clean_tags))

    loc = game_state.get("location", "")
    if loc:
        global_context.append(f"background is {loc}")

    if global_context:
        prompt_parts.append(", ".join(global_context))

    full_prompt_str = " ".join([p.strip().strip(",") for p in prompt_parts if p])

    return _finalize_prompt(full_prompt_str, MULTI_NEGATIVE, tags_en, visual_en, "multi")


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg