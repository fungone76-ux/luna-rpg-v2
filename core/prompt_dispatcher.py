# file: core/prompt_dispatcher.py
from typing import Dict, List, Tuple, Any
import core.prompt_builder as builder_single

try:
    import core.prompt_builder_multi as builder_multi
except ImportError:
    builder_multi = None

try:
    import core.prompt_builder_npc as builder_npc
except ImportError:
    builder_npc = None


class PromptDispatcher:
    """
    Analizza il contesto VISIVO (Visual + Tags) per decidere la strategia.
    NOTA: Ignora la narrazione testuale per evitare "falsi positivi".
    """

    @staticmethod
    def dispatch(
            text_response: str,
            visual_en: str,
            tags_en: List[str],
            game_state: Dict[str, Any],
            world_data: Dict[str, Any]
    ) -> Tuple[str, str]:

        # 1. Analisi Focalizzata (Solo Visual + Tags, ignora text_response)
        scene_type, subjects = PromptDispatcher._analyze_subjects(
            visual_en, tags_en, game_state, world_data
        )

        print(f"🚦 [DISPATCHER] Logic: {scene_type} | Subjects: {subjects}")

        # 2. Routing
        if scene_type == "MULTI":
            if builder_multi:
                return builder_multi.build_image_prompt(visual_en, tags_en, subjects, game_state, world_data)
            else:
                temp_state = game_state.copy()
                temp_state["game"]["companion_name"] = subjects[0] if subjects else "Luna"
                return builder_single.build_image_prompt(visual_en, tags_en, temp_state, world_data)

        elif scene_type == "NPC":
            if builder_npc:
                npc_type = subjects[0]
                return builder_npc.build_image_prompt(visual_en, tags_en, npc_type, game_state, world_data)
            else:
                return builder_single.build_image_prompt(visual_en, tags_en, game_state, world_data)

        else:  # CASE: SINGLE
            # Se il Dispatcher ha trovato un soggetto specifico nel Visual (es. Stella invece di Luna)
            # Dobbiamo dirlo al builder singolo.
            target_char = subjects[0] if subjects else game_state.get("game", {}).get("companion_name", "Luna")

            # Creiamo uno stato temporaneo per forzare il soggetto corretto senza alterare il gioco
            temp_state = game_state.copy()
            if "game" in temp_state:
                temp_state["game"] = temp_state["game"].copy()  # Shallow copy del dizionario interno
                temp_state["game"]["companion_name"] = target_char

            return builder_single.build_image_prompt(visual_en, tags_en, temp_state, world_data)

    @staticmethod
    def _analyze_subjects(
            visual: str,
            tags: List[str],
            state: Dict,
            world: Dict
    ) -> Tuple[str, List[str]]:
        """
        Cerca i soggetti SOLO nella descrizione visiva e nei tag.
        """
        # Uniamo solo Visual e Tags (La "Telecamera")
        camera_text = (visual + " " + " ".join(tags)).lower()

        # --- A. Cerca Main Characters (Companions) ---
        known_companions = list(world.get("companions", {}).keys())
        found_main = []

        for name in known_companions:
            if name.lower() in camera_text:
                found_main.append(name)

        found_main = list(dict.fromkeys(found_main))  # Rimuove duplicati

        # 1. SE visual cita 2+ personaggi -> MULTI
        if len(found_main) >= 2:
            return "MULTI", found_main

        # 2. SE visual cita 1 personaggio -> SINGLE (Su quel personaggio)
        if len(found_main) == 1:
            return "SINGLE", found_main

        # 3. SE visual non cita NESSUNO dei Main... Cerca NPC generici
        npc_logic = world.get("npc_logic", {})
        all_npc_hints = npc_logic.get("male_hints", []) + npc_logic.get("female_hints", [])

        for npc_keyword in all_npc_hints:
            check_str = f" {npc_keyword} "
            if check_str in f" {camera_text} " or camera_text.startswith(npc_keyword):
                return "NPC", [npc_keyword]

        # 4. Fallback: Usa la compagna attiva
        current_companion = state.get("game", {}).get("companion_name", "Luna")
        return "SINGLE", [current_companion]