# file: core/prompt_builder.py
from __future__ import annotations
from typing import Dict, List, Tuple

# Tenta di importare il sistema di regole (sd_prompt_rules.py)
try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None


def _get_outfit_prompt(char_data: Dict, outfit_key: str) -> str:
    """
    Recupera il prompt dell'outfit dal 'guardaroba' nel YAML.
    """
    wardrobe = char_data.get("wardrobe", {})
    raw_outfit = wardrobe.get(outfit_key, outfit_key)

    # Logica Nude
    nude_keywords = ["nude", "naked", "wearing nothing", "undressed"]
    if any(k in raw_outfit.lower() for k in nude_keywords):
        return f"(nude:1.3), (wearing nothing:1.2), (nipples:1.1), {raw_outfit}"

    # FIX: Se inizia già con "wearing", NON aggiungerlo di nuovo
    if raw_outfit.lower().strip().startswith("wearing"):
        return f"({raw_outfit}:1.1)"

    # Se è una descrizione lunga senza 'wearing', lo aggiungiamo
    if len(raw_outfit.split()) > 1:
        return f"(wearing {raw_outfit}:1.1)"

    return f"(wearing {raw_outfit}:1.1)"


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """Costruisce il prompt finale per Stable Diffusion."""

    style_data = world_data.get("visual_style", {})
    base_env_prompt = style_data.get("base_prompt", "masterpiece, best quality")
    base_negative = style_data.get("negative_prompt", "low quality, bad anatomy")

    companion_name = game_state.get("companion_name", "")
    current_outfit_key = game_state.get("current_outfit", "default")

    clean_tags = [t.strip() for t in tags_en if t.strip()]
    visual_text = (visual_en or "").strip()
    full_text_search = (visual_text + " " + " ".join(clean_tags)).lower()

    companions_db = world_data.get("companions", {})
    subject = game_state.get("image_subject", "companion").lower()

    if subject == "environment":
        full_prompt = f"{base_env_prompt}, {visual_text}, {', '.join(clean_tags)}"
        return _finalize_prompt(full_prompt, base_negative, clean_tags, visual_text, full_text_search)

    found_chars = []
    for name in companions_db.keys():
        if name.lower() in full_text_search:
            found_chars.append(name)

    if not found_chars and subject == "companion" and companion_name in companions_db:
        found_chars.append(companion_name)

    prompt_parts = [base_env_prompt]

    # A. CASO GRUPPO (Multi-Girl)
    if len(found_chars) >= 2:
        prompt_parts.append(f"{len(found_chars)}girls")
        for name in found_chars:
            char_data = companions_db[name]
            clean_base = char_data.get("base_prompt", "").replace("1girl,", "").replace("1girl", "").strip()
            prompt_parts.append(clean_base)

            if name == companion_name:
                prompt_parts.append(_get_outfit_prompt(char_data, current_outfit_key))

    # B. CASO SINGOLO
    elif len(found_chars) == 1:
        name = found_chars[0]
        char_data = companions_db[name]
        prompt_parts.append(char_data.get("base_prompt", ""))

        if name == companion_name:
            outfit_p = _get_outfit_prompt(char_data, current_outfit_key)
        else:
            default_key = char_data.get("default_outfit", "default")
            outfit_p = _get_outfit_prompt(char_data, default_key)
        prompt_parts.append(outfit_p)

    else:
        npc_logic = world_data.get("npc_logic", {})
        male_hints = npc_logic.get("male_hints", [])
        female_hints = npc_logic.get("female_hints", [])

        is_male = any(h in full_text_search for h in male_hints)
        is_female = any(h in full_text_search for h in female_hints)

        if is_male:
            prompt_parts.append(npc_logic.get("male_prompt", "1boy"))
        elif is_female:
            prompt_parts.append(npc_logic.get("female_prompt", "1girl"))
        else:
            prompt_parts.append("detailed character")

    prompt_parts.append(visual_text)
    prompt_parts.append(", ".join(clean_tags))

    global_loras = style_data.get("loras", [])
    if global_loras:
        prompt_parts.extend(global_loras)

    full_prompt_str = ", ".join(prompt_parts)
    return _finalize_prompt(full_prompt_str, base_negative, clean_tags, visual_text, full_text_search)


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg