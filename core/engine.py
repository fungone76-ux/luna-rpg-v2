# file: core/engine.py
import time
from typing import Dict, List, Tuple, Optional

from core.world_loader import WorldLoader
from core.state_manager import StateManager
from core.prompt_builder import build_image_prompt
from media.llm_client import LLMClient
from media.image_client import ImageClient
from media.audio_client import AudioClient

MEMORY_LIMIT = 12
MEMORY_PRUNE_COUNT = 4


class GameEngine:
    def __init__(self):
        self.loader = WorldLoader()
        self.state_manager = StateManager()
        self.llm = LLMClient()
        self.imager = ImageClient()
        self.audio = AudioClient()
        self.world_data = {}
        self.session_active = False

    def list_worlds(self):
        return self.loader.list_available_worlds()

    def start_new_game(self, world_id: str, companion_name: str = "Luna"):
        self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
        if not self.world_data:
            # Fallback
            available = self.loader.list_available_worlds()
            if available:
                self.world_data = self.loader.load_world_data(f"{available[0]['id']}.yaml")
            else:
                raise ValueError(f"Cannot load world: {world_id}")

        self.state_manager.create_new_session(self.world_data, companion_name)
        self.session_active = True

        if "summary_log" not in self.state_manager.current_state:
            self.state_manager.current_state["summary_log"] = []

        return True

    def load_game(self, filename: str):
        if self.state_manager.load_game(filename):
            world_id = self.state_manager.current_state["meta"].get("world_id")
            self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
            self.session_active = True
            return True
        return False

    # --- BRAIN ---
    def process_turn_llm(self, user_input: str, is_intro: bool = False) -> Dict:
        if not self.session_active:
            return {"text": "Error: No session.", "visual_en": "", "tags_en": []}

        state = self.state_manager.current_state
        if not is_intro:
            self._manage_long_term_memory()

        system_prompt = self._build_system_prompt()
        history = state.get("history", [])
        summaries = state.get("summary_log", [])

        final_input = user_input

        # --- FIX INTRODUZIONE + FIX PROSPETTIVA + FIX SCONOSCIUTI ---
        if is_intro:
            companion_name = state["game"].get("companion_name", "Unknown")
            final_input = (
                f"[SYSTEM INSTRUCTION]: START THE GAME NOW.\n"
                f"LANGUAGE: ITALIAN.\n"
                f"SCENE: Morning, First Day of School, Entrance Gate.\n"
                f"CONTEXT: It is the very first day. You and {companion_name} are STRANGERS. You have never met before.\n"  # <--- ECCO IL PEZZO MANCANTE!
                f"ACTION: The protagonist arrives at school and sees {companion_name}.\n"
                f"RULES:\n"
                f"1. Narrate in 'Tu' (You) perspective. Example: 'Tu arrivi davanti al cancello...'.\n"
                f"2. Do NOT describe the protagonist's feelings (like 'il mio cuore batte'). Leave that to the player.\n"
                f"3. Do NOT use First Person ('Io') for narration.\n"
                f"4. Describe the scene and {companion_name}'s outfit."
            )

        response_data = self.llm.generate_response(
            user_input=final_input,
            system_instruction=system_prompt,
            history=history,
            summaries=summaries
        )

        if "updates" in response_data:
            self.state_manager.update_state(response_data["updates"])

        if not is_intro:
            state["history"].append({"role": "user", "content": final_input})
        state["history"].append({"role": "model", "content": response_data["text"]})

        self.state_manager.save_game("autosave.json")
        return response_data

    # --- EYES ---
    def process_image_generation(self, visual_en: str, tags_en: List[str]) -> str:
        game_state = self.state_manager.current_state.get("game", {})
        pos, neg = build_image_prompt(visual_en, tags_en, game_state, self.world_data)

        print(f"\n🎨 [SD PROMPT]: {pos[:200]}...")
        return self.imager.generate_image(pos, neg)

    # --- VOICE ---
    def process_audio(self, text: str):
        name = self.state_manager.current_state["game"].get("companion_name", "Narrator")
        self.audio.play_voice(text, name)

    # --- HELPERS ---
    def _manage_long_term_memory(self):
        history = self.state_manager.current_state.get("history", [])
        if len(history) > MEMORY_LIMIT:
            print(f"🧠 Compressing Memory...")
            to_prune = history[:MEMORY_PRUNE_COUNT]
            remaining = history[MEMORY_PRUNE_COUNT:]
            summary = self.llm.summarize_history(to_prune)
            self.state_manager.current_state["summary_log"].append(summary)
            self.state_manager.current_state["history"] = remaining

    def _get_affinity_personality(self, char_name: str, current_points: int) -> str:
        companions_db = self.world_data.get("companions", {})
        char_data = companions_db.get(char_name, {})
        tiers = char_data.get("personality_tiers", {})

        selected_desc = "Standard personality."
        best_threshold = -1

        for threshold, desc in tiers.items():
            thresh_int = int(threshold)
            if current_points >= thresh_int and thresh_int > best_threshold:
                best_threshold = thresh_int
                selected_desc = desc

        return f"Affinity {current_points} -> {selected_desc}"

    def _build_system_prompt(self) -> str:
        meta = self.world_data.get("meta", {})
        game = self.state_manager.current_state.get("game", {})

        char_name = game.get('companion_name')
        current_aff = game.get("affinity", {}).get(char_name, 0)

        partner_personality = self._get_affinity_personality(char_name, current_aff)

        all_companions = list(self.world_data.get("companions", {}).keys())
        other_chars = [c for c in all_companions if c != char_name]

        npc_instructions = ""
        for npc in other_chars:
            npc_aff = game.get("affinity", {}).get(npc, 0)
            npc_pers = self._get_affinity_personality(npc, npc_aff)
            npc_instructions += f"- {npc}: {npc_pers}\n"

        story_struct = meta.get("story_structure", {})
        key_events = story_struct.get("key_events", [])

        events_str = "POSSIBLE PLOT POINTS:\n"
        for e in key_events: events_str += f"- [KEY] {e}\n"

        # --- REGOLE AGGIORNATE ---
        return f"""
        You are the Game Master of a {meta.get('genre')} game.
        World: {meta.get('name')}
        Lore: {meta.get('world_lore')}

        ==================================================
        🔴 CRITICAL RULES:
        1. **LANGUAGE**: Narrate in **ITALIAN**. JSON in **ENGLISH**.
        2. **PERSPECTIVE**: Narrate in **SECOND PERSON** ("Tu", "You"). 
           - CORRECT: "Tu vedi Luna avvicinarsi."
           - WRONG: "Io vedo Luna." (Do not use "Io" for narration).
        3. **NO GOD-MODDING**: 
           - Do NOT describe the Protagonist's internal thoughts or feelings.
           - Only describe external events and NPC reactions. Let the player decide how they feel.
        ==================================================

        ### 📖 STORY & EVENTS
        {events_str}

        ### 💘 RELATIONSHIP SYSTEM
        **ACTIVE PARTNER ({char_name}):**
        {partner_personality}

        **OTHER NPCs:**
        {npc_instructions}

        ### ⌚ TIME & CYCLE
        Current Cycle: MORNING -> AFTERNOON -> NIGHT.
        Current Time: {game.get('time_of_day', 'Morning')}
        Current Location: {game.get('location')}

        **INSTRUCTION**: Update `time_of_day` in the JSON if the story advances naturally (e.g., classes end -> Afternoon).

        ### 🎬 VISUAL DIRECTOR
        - **Subject**: Describe the scene for an AI Image Generator.
        - **Multi-Character**: If multiple girls are present, mention ALL of them in `visual_en`.
        - **Outfit**: Ensure description matches: {game.get('current_outfit')}

        ### OUTPUT FORMAT
        ```json
        {{
           "visual_en": "Cinematic shot of [Subject], [Action], [Environment], [Lighting]",
           "tags_en": ["tag1", "tag2"],
           "updates": {{ 
               "time_of_day": "Morning/Afternoon/Night",
               "location": "...", 
               "affinity_change": {{ "{char_name}": 1 }},
               "stat_changes": {{ "charisma": 1, "mind": 0, "strength": 0 }},
               "current_outfit": "...",
               "add_item": "..."
           }}
        }}
        ```
        """