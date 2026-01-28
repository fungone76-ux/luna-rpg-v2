# file: core/prompt_builder.py
from __future__ import annotations
from typing import Dict, List, Tuple
import re

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

BASE_PROMPTS = {
    "Luna": (
        "score_9, score_8_up, masterpiece, photorealistic,  detailed, atmospheric, "
        "stsdebbie, dynamic pose, 1girl, mature woman, brown hair, shiny skin, head tilt, massive breasts, cleavage, "
        "<lora:stsDebbie-10e:0.7> <lora:Expressive_H-000001:0.20><lora:FantasyWorldPonyV2:0.40>"
    ),
    "Stella": (
        "score_9, score_8_up, masterpiece, NSFW, photorealistic, 1girl, "
        "alice_milf_catchers, massive breasts, cleavage, blonde hair, beautiful blue eyes, "
        "shapely legs, hourglass figure, skinny body, narrow waist, wide hips, "
        "<lora:alice_milf_catchers_lora:0.7> <lora:Expressive_H:0.2>"
    ),
    "Maria": (
        "score_9, score_8_up, stsSmith, ultra-detailed, realistic lighting, 1girl, "
        "mature female, (middle eastern woman:1.5), veiny breasts, black hair, short hair, evil smile, glowing magic, "
        "<lora:stsSmith-10e:0.65> <lora:Expressive_H:0.2> <lora:FantasyWorldPonyV2:0.40>"
    )
}

NPC_BASE = "score_9, score_8_up, masterpiece, photorealistic, 1girl, detailed face, cinematic lighting"
NEGATIVE_PROMPT = "score_5, score_4, low quality, anime, monochrome, deformed, bad anatomy, worst face, extra fingers, cartoon, 3d render"


def _remove_conflicting_footwear(outfit_desc: str, visual_context: str) -> str:
    """Rimuove stivali/scarpe se la scena richiede piedi nudi (Versione Single)."""
    vis_lower = visual_context.lower()
    if any(k in vis_lower for k in ["barefoot", "feet", "toes", "foot worship", "soles", "scalza"]):
        clean = re.sub(r"\b(boots|shoes|sneakers|heels|loafers|footwear)\b", "", outfit_desc, flags=re.IGNORECASE)
        return re.sub(r",\s*,", ",", clean).strip(" ,")
    return outfit_desc


def _get_outfit_string(char_name: str, game_state: Dict, world_data: Dict, visual_context: str = "") -> str:
    current_outfit_key = "default"
    if char_name == game_state.get("game", {}).get("companion_name"):
        current_outfit_key = game_state.get("game", {}).get("current_outfit", "default")
    else:
        companions_db = world_data.get("companions", {})
        if char_name in companions_db:
            current_outfit_key = companions_db[char_name].get("default_outfit", "default")

    companions_db = world_data.get("companions", {})
    wardrobe = companions_db.get(char_name, {}).get("wardrobe", {})
    outfit_desc = wardrobe.get(current_outfit_key, current_outfit_key)

    clean_desc = str(outfit_desc).lower().replace("wearing ", "")
    clean_desc = clean_desc.replace("(", "").replace(")", "").strip()  # Fix parentesi

    # Fix Scarpe (Aggiunto anche qui!)
    clean_desc = _remove_conflicting_footwear(clean_desc, visual_context)

    if "nude" in clean_desc or "naked" in clean_desc:
        return f"(nude:1.3), {clean_desc}"
    else:
        return f"(wearing {clean_desc}:1.3)"


def build_image_prompt(visual_en, tags_en, game_state, world_data):
    full_text = (visual_en + " " + " ".join(tags_en)).lower()

    # Il soggetto è deciso dal Dispatcher o dal companion attivo
    char_name = game_state.get("game", {}).get("companion_name", "Luna")

    # Override se il visual cita un altro personaggio (es. "Stella")
    for name in BASE_PROMPTS.keys():
        if name.lower() in full_text:
            char_name = name
            break

    base = BASE_PROMPTS.get(char_name, NPC_BASE)

    # Passiamo visual_en per la logica scarpe
    outfit_str = _get_outfit_string(char_name, game_state, world_data, visual_context=visual_en)

    prompt_parts = [f"{base}, {outfit_str}"]

    banned = ["score_9", "score_8_up", "masterpiece", "best quality", "1girl", "photorealistic"]
    clean_tags = [t for t in tags_en if t.lower() not in banned]

    if clean_tags: prompt_parts.append(", ".join(clean_tags))
    if visual_en: prompt_parts.append(f"({visual_en}:1.1)")

    loc = game_state.get("game", {}).get("location", "")
    if loc and loc.lower() not in visual_en.lower():
        prompt_parts.append(f"background is {loc}")

    full_prompt_str = ", ".join([p.strip().strip(",") for p in prompt_parts if p])
    return _finalize_prompt(full_prompt_str, NEGATIVE_PROMPT, tags_en, visual_en, full_text)


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules: return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg