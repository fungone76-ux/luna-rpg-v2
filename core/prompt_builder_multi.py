# file: core/prompt_builder_multi.py
from __future__ import annotations
from typing import Dict, List, Tuple
import re

from core.prompt_builder import BASE_PROMPTS, NPC_BASE

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

# --- Costanti Globali ---
GLOBAL_QUALITY = "score_9, score_8_up, masterpiece, photorealistic, detailed, atmospheric, 8k"

# Parole chiave per identificare LoRA di STILE (da spostare in Global)
STYLE_LORA_KEYWORDS = [
    "FantasyWorldPony", "PonyV2", "Expressive", "Style", "Lighting",
    "Detail", "Addon", "xl_more_art", "flat", "anime", "Pony"
]

INTERACTION_BOOST = (
    "dynamic composition, interacting, multiple subjects, "
    "coherent interaction, scene coherence, detailed composition, "
    "group shot"
)

MULTI_NEGATIVE = (
    "score_5, score_4, low quality, anime, monochrome, deformed, bad anatomy, "
    "worst face, extra fingers, cartoon, 3d render, "
    "(same face:1.4), (twins:1.4), (clones:1.4), (same hair color:1.2), "
    "floating limbs, disconnected bodies, (split view:1.3)"
)


def _get_outfit_for_multi(char_name: str, game_state: Dict, world_data: Dict, visual_context: str = "") -> str:
    """
    Recupera l'outfit corretto, controllando sia il Companion che gli NPC dinamici.
    Se la scena visiva impone nudità, sopprime l'outfit.
    """
    # 1. Controllo Priorità Nudità (Context Override)
    # Se l'LLM ha descritto esplicitamente nudità nella scena, ignoriamo l'outfit del DB
    nude_triggers = ["naked", "nude", "undressed", "no clothes", "showering", "bath"]
    if any(t in visual_context.lower() for t in nude_triggers):
        return "(nude:1.2)"

    # 2. Identificazione Chiave Outfit (Dinamica)
    current_outfit_key = "default"

    # A. È la Main Companion?
    if char_name == game_state.get("companion_name"):
        current_outfit_key = game_state.get("current_outfit", "default")

    # B. È un NPC con stato salvato? (FIX CRUCIALE)
    elif "npc_states" in game_state and char_name in game_state["npc_states"]:
        # Cerca l'outfit nello stato dell'NPC
        npc_data = game_state["npc_states"][char_name]
        current_outfit_key = npc_data.get("current_outfit", "default")

    # C. Fallback: Cerca nel database statico dei Companions
    else:
        companions_db = world_data.get("companions", {})
        if char_name in companions_db:
            char_data = companions_db.get(char_name, {})
            current_outfit_key = char_data.get("default_outfit", "default")

    # 3. Recupero Descrizione dal Guardaroba
    companions_db = world_data.get("companions", {})
    char_data = companions_db.get(char_name, {})
    wardrobe = char_data.get("wardrobe", {})
    outfit_desc = wardrobe.get(current_outfit_key, "")

    # Fallback se la chiave non esiste nel guardaroba
    if not outfit_desc:
        outfit_desc = wardrobe.get("default", "clothing")

    # 4. Pulizia Stringa
    clean_desc = str(outfit_desc).lower().replace("wearing ", "").strip()
    clean_desc = clean_desc.replace("(", "").replace(")", "")

    # Doppio controllo nudità nel guardaroba stesso
    local_nude_keys = ["naked", "nude", "undressed", "nothing"]
    if any(k in clean_desc for k in local_nude_keys):
        return f"(nude:1.2), {clean_desc}"
    else:
        return f"(wearing {clean_desc}:1.2)"


def _clean_base_prompt(base_prompt: str) -> str:
    """Rimuove i tag di qualità testuali dal prompt base del personaggio."""
    banned_tags = [
        "score_9", "score_8_up", "score_7_up", "score_6_up",
        "masterpiece", "best quality", "photorealistic", "detailed",
        "atmospheric", "8k", "ultra-detailed", "realistic lighting",
        "1girl", "mature female", "mature woman"
    ]

    clean = base_prompt
    for tag in banned_tags:
        clean = re.sub(f",?\\s*{re.escape(tag)},?", "", clean, flags=re.IGNORECASE)

    return clean.strip().strip(",")


def _extract_style_loras(text: str) -> Tuple[str, List[str]]:
    """
    Estrae i LoRA di stile (Pony, Expressive) per metterli nel global.
    """
    found_styles = []

    def replace_callback(match):
        full_tag = match.group(0)
        lora_name = match.group(1)

        # Controlla se è un LoRA di stile
        is_style = any(k.lower() in lora_name.lower() for k in STYLE_LORA_KEYWORDS)

        if is_style:
            found_styles.append(full_tag)
            return ""
        return full_tag

    pattern = r"<lora:([^:>]+)(?::[^>]+)?>"
    cleaned_text = re.sub(pattern, replace_callback, text)
    cleaned_text = re.sub(r"\s{2,}", " ", cleaned_text).strip(" ,")

    return cleaned_text, found_styles


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        subjects: List[str],
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """
    Costruisce il prompt Multi-Soggetto Dinamico.
    """
    # 1. Preparazione Dati
    loc = game_state.get("location", "")
    loc_fragment = f", background is {loc}" if loc else ""
    num_girls = len(subjects)

    collected_global_loras = set()
    char_blocks = []

    # 2. Loop Personaggi
    for name in subjects:
        raw_base = BASE_PROMPTS.get(name, NPC_BASE)

        # A. Pulizia base
        text_clean = _clean_base_prompt(raw_base)

        # B. Estrazione LoRA Stile
        final_char_text, styles = _extract_style_loras(text_clean)
        for s in styles:
            collected_global_loras.add(s)

        # C. Outfit Dinamico (Passiamo anche visual_en per l'override nudità)
        outfit = _get_outfit_for_multi(name, game_state, world_data, visual_context=visual_en)

        # Costruzione Blocco
        block = f"({name}, {final_char_text}, {outfit}{loc_fragment})"
        char_blocks.append(block)

    # 3. Assemblaggio Finale
    prompt_parts = []

    # A. LoRA Globali (Deduplicati dal set)
    if collected_global_loras:
        prompt_parts.append(" ".join(list(collected_global_loras)))

    # B. Qualità e Conteggio
    prompt_parts.append(GLOBAL_QUALITY)
    prompt_parts.append(f"{num_girls}girls" if num_girls > 1 else "1girl")

    # C. Blocchi Personaggi
    prompt_parts.append(" BREAK ".join(char_blocks))

    # D. Contesto Globale
    global_context = []
    global_context.append(INTERACTION_BOOST)

    banned_context = [
        "best quality", "masterpiece", "score_9", "score_8_up",
        "1girl", "2girls", "3girls", "girls", "woman", "female"
    ]
    clean_tags = [t for t in tags_en if t.lower() not in banned_context]

    if visual_en:
        global_context.append(f"({visual_en}:1.1)")

    if clean_tags:
        global_context.append(", ".join(clean_tags))

    if loc:
        global_context.append(f"in {loc}")

    if global_context:
        prompt_parts.append(", ".join(global_context))

    full_prompt_str = " ".join([p.strip().strip(",") for p in prompt_parts if p])

    return _finalize_prompt(full_prompt_str, MULTI_NEGATIVE, tags_en, visual_en, "multi")


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg