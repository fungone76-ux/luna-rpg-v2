# file: core/prompt_builder.py
# Modulo per la costruzione intelligente dei prompt (Smart Outfit, Multi-Character)

from typing import Dict, List, Tuple

def build_image_prompt(visual_en: str, tags_en: List[str], game_state: Dict) -> Tuple[str, str]:
    """
    Logica complessa per assemblare il prompt.
    1. Legge il profilo dallo YAML (tramite game_state).
    2. Applica Smart Outfit (Nude/Vestita).
    3. Gestisce gruppi (2girls) se ci sono più personaggi.
    4. Incolla i tag dell'LLM.
    """
    # TODO: Implementare la logica discussa
    return "", ""
