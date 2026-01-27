# file: core/prompt_dispatcher.py
from typing import Dict, List, Tuple, Any

# Importiamo i builder
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
    NOTA: Ignora la narrazione testuale per evitare "falsi positivi"
    (es. citare Stella nel testo ma inquadrare solo Luna).
    """

    @staticmethod
    def dispatch(
            text_response: str,
            visual_en: str,
            tags_en: List[str],
            game_state: Dict[str, Any],
            world_data: Dict[str, Any]
    ) -> Tuple[str, str]:

        # 1. Analisi Focalizzata (Solo Visual + Tags)
        scene_type, subjects = PromptDispatcher._analyze_subjects(
            visual_en, tags_en, game_state, world_data
        )

        print(f"🚦 [DISPATCHER] Logic: {scene_type} | Subjects: {subjects}")

        # 2. Routing
        if scene_type == "MULTI":
            if builder_multi:
                return builder_multi.build_image_prompt(visual_en, tags_en, subjects, game_state, world_data)
            else:
                # Fallback su Single se manca il modulo
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
            # Se il Dispatcher ha trovato un soggetto specifico nel Visual (es. Stella),
            # dobbiamo assicurarci che il builder singolo lo sappia.
            # Il builder singolo attuale scansiona da solo visual_en, quindi siamo coperti.
            return builder_single.build_image_prompt(visual_en, tags_en, game_state, world_data)

    @staticmethod
    def _analyze_subjects(
            visual: str,
            tags: List[str],
            state: Dict,
            world: Dict
    ) -> Tuple[str, List[str]]:
        """
        Cerca i soggetti SOLO nella descrizione visiva e nei tag.
        La narrazione viene ignorata per dare priorità alla regia dell'LLM.
        """
        # Uniamo solo Visual e Tags (La "Telecamera")
        # Ignoriamo 'narrative' perché cita persone presenti ma magari non inquadrate.
        camera_text = (visual + " " + " ".join(tags)).lower()

        # --- A. Cerca Main Characters (Companions) ---
        known_companions = list(world.get("companions", {}).keys())
        found_main = []

        for name in known_companions:
            if name.lower() in camera_text:
                found_main.append(name)

        # Deduplica mantenendo l'ordine
        found_main = list(dict.fromkeys(found_main))

        # LOGICA PRIORITARIA:

        # 1. SE visual cita 2+ personaggi -> MULTI
        if len(found_main) >= 2:
            return "MULTI", found_main

        # 2. SE visual cita 1 personaggio -> SINGLE (Su quel personaggio)
        if len(found_main) == 1:
            return "SINGLE", found_main

        # 3. SE visual non cita NESSUNO dei Main...
        # ...Proviamo a vedere se è un NPC generico (es. "orc", "guard")
        npc_logic = world.get("npc_logic", {})
        male_hints = npc_logic.get("male_hints", [])
        female_hints = npc_logic.get("female_hints", [])
        all_npc_hints = male_hints + female_hints

        for npc_keyword in all_npc_hints:
            check_str = f" {npc_keyword} "
            if check_str in f" {camera_text} " or camera_text.startswith(npc_keyword):
                return "NPC", [npc_keyword]

        # 4. Fallback Totale:
        # Se l'LLM non ha specificato nessuno nel Visual, assumiamo sia la compagna attiva.
        # (Esempio: Visual="Close up of legs", senza nomi -> Usa Luna)
        current_companion = state.get("game", {}).get("companion_name", "Luna")
        return "SINGLE", [current_companion]