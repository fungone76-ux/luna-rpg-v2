# file: core/prompt_builder_multi.py
from __future__ import annotations
from typing import Dict, List, Tuple
import re
from core.prompt_builder import BASE_PROMPTS, NPC_BASE

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

GLOBAL_QUALITY = "score_9, score_8_up, masterpiece, photorealistic, detailed, atmospheric, 8k"
INTERACTION_BOOST = "dynamic composition, interacting, multiple subjects, group shot"
MULTI_NEGATIVE = "score_5, score_4, low quality, anime, monochrome, deformed, bad anatomy, (same face:1.4), (clones:1.4)"
STYLE_LORA_KEYWORDS = ["FantasyWorldPony", "PonyV2", "Expressive", "Style", "Lighting", "Detail", "Pony"]


def _remove_conflicting_footwear(outfit_desc: str, visual_context: str) -> str:
    """Rimuove stivali/scarpe se la scena richiede piedi nudi."""
    vis_lower = visual_context.lower()
    if any(k in vis_lower for k in ["barefoot", "feet", "toes", "foot worship", "soles", "scalza"]):
        clean = re.sub(r"\b(boots|shoes|sneakers|heels|loafers|footwear)\b", "", outfit_desc, flags=re.IGNORECASE)
        return re.sub(r",\s*,", ",", clean).strip(" ,")
    return outfit_desc


def _get_outfit_from_state(char_name: str, game_state: Dict, world_data: Dict, visual_context: str = "") -> str:
    current_outfit_key = "default"

    # Recupero chiave outfit (Supporta NPC States)
    if char_name == game_state.get("game", {}).get("companion_name"):
        current_outfit_key = game_state.get("game", {}).get("current_outfit", "default")
    elif "npc_states" in game_state.get("game", {}) and char_name in game_state["game"]["npc_states"]:
        npc_data = game_state["game"]["npc_states"][char_name]
        current_outfit_key = npc_data.get("current_outfit", "default")
    else:
        companions_db = world_data.get("companions", {})
        if char_name in companions_db:
            current_outfit_key = companions_db[char_name].get("default_outfit", "default")

    # Recupero descrizione
    companions_db = world_data.get("companions", {})
    wardrobe = companions_db.get(char_name, {}).get("wardrobe", {})
    outfit_desc = wardrobe.get(current_outfit_key, current_outfit_key)

    # --- FIX CRITICO PARENTESI ---
    clean_desc = str(outfit_desc).lower().replace("wearing ", "")
    clean_desc = clean_desc.replace("(", "").replace(")", "").strip()  # RIMUOVE TUTTE LE PARENTESI

    # Fix Scarpe
    clean_desc = _remove_conflicting_footwear(clean_desc, visual_context)

    if "nude" in clean_desc or "naked" in clean_desc:
        return f"(nude:1.2), {clean_desc}"
    return f"(wearing {clean_desc}:1.2)"


def _extract_style_loras(text: str) -> Tuple[str, List[str]]:
    found_styles = []

    def cb(m):
        if any(k.lower() in m.group(1).lower() for k in STYLE_LORA_KEYWORDS):
            found_styles.append(m.group(0))
            return ""
        return m.group(0)

    return re.sub(r"<lora:([^:>]+)(?::[^>]+)?>", cb, text).strip(" ,"), found_styles


def _clean_base_prompt(base: str) -> str:
    banned = ["score_9", "score_8_up", "masterpiece", "1girl", "photorealistic"]
    for t in banned: base = re.sub(f",?\\s*{re.escape(t)},?", "", base)
    return base.strip(", ")


def build_image_prompt(visual_en, tags_en, subjects, game_state, world_data):
    loc = game_state.get("game", {}).get("location", "")
    char_blocks, global_loras = [], set()

    for name in subjects:
        raw_base = BASE_PROMPTS.get(name, NPC_BASE)
        base_clean, styles = _extract_style_loras(_clean_base_prompt(raw_base))
        for s in styles: global_loras.add(s)

        # Outfit + Fix Scarpe
        outfit = _get_outfit_from_state(name, game_state, world_data, visual_context=visual_en)
        loc_bg = f", background is {loc}" if loc else ""
        char_blocks.append(f"({name}, {base_clean}, {outfit}{loc_bg})")

    parts = []
    if global_loras: parts.append(" ".join(global_loras))
    parts.append(GLOBAL_QUALITY)
    parts.append(f"{len(subjects)}girls")
    parts.append(" BREAK ".join(char_blocks))

    global_context = [INTERACTION_BOOST]
    if visual_en: global_context.append(f"({visual_en}:1.1)")

    banned_tags = ["best quality", "masterpiece", "score_9", "1girl", "2girls", "3girls"]
    clean_tags = [t for t in tags_en if t.lower() not in banned_tags]
    if clean_tags: global_context.append(", ".join(clean_tags))

    parts.append(", ".join(global_context))
    full_prompt_str = " ".join([p.strip() for p in parts if p])

    return _finalize_prompt(full_prompt_str, MULTI_NEGATIVE, tags_en, visual_en, "multi")


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules: return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg