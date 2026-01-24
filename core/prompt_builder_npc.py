# file: core/prompt_builder_npc.py
from __future__ import annotations
from typing import Dict, List, Tuple

try:
    from sd_prompt_rules import apply_sd_prompt_rules
except ImportError:
    apply_sd_prompt_rules = None

# --- PROMPT BASE HARDCODATI (Definiti qui, non nello YAML) ---
NPC_MALE_BASE = (
    "score_9, score_8_up, masterpiece, photorealistic, "
    "1boy, male npc, full body, detailed face, cinematic lighting, 8k, "
    "realistic skin texture, depth of field <lora:FantasyWorldPonyV2:0.4>"
)

NPC_FEMALE_BASE = (
    "score_9, score_8_up, masterpiece, photorealistic, "
    "1girl, female npc,full body, detailed face, cinematic lighting, 8k, "
    "beautiful face, realistic skin texture, soft lighting <lora:FantasyWorldPonyV2:0.4>"
)

# Negative Prompt Generico per NPC
NPC_NEGATIVE = "score_5, score_4, low quality, bad anatomy, worst face, extra fingers, cartoon, 3d render, text, watermark"


def build_image_prompt(
        visual_en: str,
        tags_en: List[str],
        npc_type: str,
        game_state: Dict,
        world_data: Dict
) -> Tuple[str, str]:
    """
    Costruisce un prompt per un NPC iniettando il 'tipo' (es. orc, maid)
    nei template base hardcodati qui nel file Python.
    """

    # 1. Recupera SOLO le liste di hint dallo YAML per decidere il genere
    npc_logic = world_data.get("npc_logic", {})
    female_hints = npc_logic.get("female_hints", [])

    # 2. Selezione Template Base (Hardcodato)
    # Se il tipo è nella lista femminile dello YAML -> Base Femmina
    # Altrimenti -> Base Maschio (Default)
    if npc_type.lower() in [h.lower() for h in female_hints]:
        base_prompt = NPC_FEMALE_BASE
    else:
        base_prompt = NPC_MALE_BASE

    # 3. Iniezione del Tipo Specifico nel Prompt
    # Esempio: "1boy..." diventa "orc, 1boy..." per dare priorità alla razza/ruolo
    # Rimuoviamo "1boy" o "1girl" dal base se vogliamo evitare ripetizioni,
    # ma solitamente SD tollera bene "orc, 1boy". Lo lasciamo per sicurezza.
    final_base = f"{npc_type}, {base_prompt}"

    # 4. Costruzione Prompt (Visual + Tags + Location)
    prompt_parts = [final_base]

    # Pulizia tag ridondanti che potrebbero arrivare dall'LLM
    banned = ["best quality", "masterpiece", "score_9", "1boy", "1girl", "photorealistic"]
    clean_tags = [t for t in tags_en if t.lower() not in banned]

    if clean_tags:
        prompt_parts.append(", ".join(clean_tags))

    if visual_en:
        prompt_parts.append(f"({visual_en}:1.1)")

    # Location
    loc = game_state.get("location", "")
    if loc:
        prompt_parts.append(f"background is {loc}")

    # Assemblaggio finale
    full_prompt_str = ", ".join([p.strip().strip(",") for p in prompt_parts if p])

    return _finalize_prompt(full_prompt_str, NPC_NEGATIVE, tags_en, visual_en, npc_type)


def _finalize_prompt(pos, neg, tags, visual, context):
    if apply_sd_prompt_rules:
        return apply_sd_prompt_rules(pos, neg, tags, visual, context)
    return pos, neg