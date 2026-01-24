# file: core/prompt_builder.py
from __future__ import annotations
from typing import Dict, List, Tuple

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

# --- PROMPT BASE DEFINITIVI (I tuoi) ---
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

# Fallback per NPC generici
NPC_BASE = "score_9, score_8_up, masterpiece, photorealistic, 1girl, detailed face, cinematic lighting"

# Negative Prompt Fisso (Il tuo)
NEGATIVE_PROMPT = "score_5, score_4, low quality, anime, monochrome, deformed, bad anatomy, worst face, extra fingers, cartoon, 3d render"


def _get_outfit_string(char_name: str, game_state: Dict, world_data: Dict) -> str:
    """Recupera l'outfit corrente e lo formatta."""
    # 1. Identifica la chiave outfit (es. "teacher_suit")
    current_outfit_key = "default"
    if char_name == game_state.get("companion_name"):
        current_outfit_key = game_state.get("current_outfit", "default")
    else:
        # Per NPC, usa il default definito nello YAML
        companions_db = world_data.get("companions", {})
        char_data = companions_db.get(char_name, {})
        current_outfit_key = char_data.get("default_outfit", "default")

    # 2. Cerca la descrizione nel Wardrobe dello YAML
    companions_db = world_data.get("companions", {})
    char_data = companions_db.get(char_name, {})
    wardrobe = char_data.get("wardrobe", {})

    outfit_desc = wardrobe.get(current_outfit_key, "")

    # Fallback
    if not outfit_desc:
        outfit_desc = wardrobe.get("default", "clothing")

    # 3. Pulizia e Iniezione
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
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    # 1. Identifica i personaggi presenti
    full_text = (visual_en + " " + " ".join(tags_en)).lower()
    found_chars = []

    for name in BASE_PROMPTS.keys():
        if name.lower() in full_text:
            found_chars.append(name)

    # Se vuoto, usa la compagna attiva
    if not found_chars:
        found_chars.append(game_state.get("companion_name", "Luna"))

    found_chars = list(dict.fromkeys(found_chars))
    is_group = len(found_chars) >= 2

    # 2. Costruzione Prompt
    prompt_parts = []

    if is_group:
        prompt_parts.append(f"{len(found_chars)}girls")

    for char_name in found_chars:
        # A. Base Prompt (Dal Dizionario Hardcoded)
        base = BASE_PROMPTS.get(char_name, NPC_BASE)
        if is_group:
            base = base.replace("1girl,", "").replace("1girl", "").strip()

        # B. Outfit (Iniettato dallo Stato)
        outfit_str = _get_outfit_string(char_name, game_state, world_data)

        prompt_parts.append(f"{base}, {outfit_str}")

        if is_group:
            prompt_parts.append("BREAK")

    # 3. Scena & Tags (Dall'LLM)
    # Rimuoviamo tag di qualità doppi se l'LLM li ha messi
    banned = ["score_9", "score_8_up", "masterpiece", "best quality", "1girl", "photorealistic"]
    clean_tags = [t for t in tags_en if t.lower() not in banned]

    if clean_tags:
        prompt_parts.append(", ".join(clean_tags))

    if visual_en:
        prompt_parts.append(f"({visual_en}:1.1)")

    # 4. Location (Dallo Stato, se non già descritta)
    loc = game_state.get("location", "")
    if loc and loc.lower() not in visual_en.lower():
        prompt_parts.append(f"background is {loc}")

    # Assemblaggio
    separator = " " if is_group else ", "
    full_prompt_str = separator.join([p.strip().strip(",") for p in prompt_parts if p])

    # Negative Prompt (con protezione anti-clone per gruppi)
    final_negative = NEGATIVE_PROMPT
    if is_group:
        final_negative += ", (same face:1.4), (twins:1.4), (clones:1.4), (same hair color:1.2)"

    return _finalize_prompt(full_prompt_str, final_negative, tags_en, visual_en, full_text)


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg