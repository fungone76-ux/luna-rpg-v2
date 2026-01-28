# file: core/engine.py
import os
import json
from typing import Dict, List

from core.world_loader import WorldLoader
from core.state_manager import StateManager
from core.memory_manager import MemoryManager
from core.prompt_dispatcher import PromptDispatcher

from media.llm_client import LLMClient
from media.image_client import ImageClient
from media.audio_client import AudioClient


class GameEngine:
    def __init__(self):
        self.loader = WorldLoader()
        self.state_manager = StateManager()
        self.llm = LLMClient()
        self.imager = ImageClient()
        self.audio = AudioClient()
        self.memory = MemoryManager(self.state_manager, self.llm)

        self.world_data = {}
        self.session_active = False

    def list_worlds(self):
        return self.loader.list_available_worlds()

    def start_new_game(self, world_id: str, companion_name: str = "Luna"):
        self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
        if not self.world_data:
            available = self.loader.list_available_worlds()
            if available:
                self.world_data = self.loader.load_world_data(f"{available[0]['id']}.yaml")
            else:
                raise ValueError(f"Cannot load world: {world_id}")

        self.state_manager.create_new_session(self.world_data, companion_name)
        self.session_active = True

        if "summary_log" not in self.state_manager.current_state:
            self.state_manager.current_state["summary_log"] = []
        if "knowledge_base" not in self.state_manager.current_state:
            self.state_manager.current_state["knowledge_base"] = []

        return True

    def load_game(self, filename: str):
        if self.state_manager.load_game(filename):
            world_id = self.state_manager.current_state["meta"].get("world_id")
            self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
            self.session_active = True
            return True
        return False

    def process_turn_llm(self, user_input: str, is_intro: bool = False) -> Dict:
        if not self.session_active:
            return {"text": "Error: No session.", "visual_en": "", "tags_en": []}

        state = self.state_manager.current_state

        if not is_intro:
            try:
                self.memory.manage_memory_drift()
            except Exception as e:
                print(f"⚠️ Errore Memory Manager: {e}")

        system_prompt = self._build_system_prompt()
        history = state.get("history", [])
        memory_block = self.memory.get_context_block()

        final_input = user_input

        if is_intro:
            companion_name = state["game"].get("companion_name", "Unknown")
            world_name = self.world_data.get("meta", {}).get("name", "Unknown World")
            final_input = (
                f"[SYSTEM INSTRUCTION]: START THE GAME NOW.\n"
                f"LANGUAGE: ITALIAN.\n"
                f"CONTEXT: You are in {world_name}. The protagonist meets {companion_name}.\n"
                f"ACTION: Start with a SHORT, IMMEDIATE hook (Max 3 lines). No long descriptions.\n"
                f"IMPORTANT: First write the short Narration in Italian, THEN provide the JSON."
            )

        try:
            response_data = self.llm.generate_response(
                user_input=final_input,
                system_instruction=system_prompt,
                history=history,
                memory_context=memory_block
            )
        except Exception as e:
            print(f"❌ Errore critico LLM: {e}")
            return {"text": "La connessione neurale è instabile... (Errore Tecnico).", "visual_en": "", "tags_en": []}

        if not response_data or "Errore API" in response_data.get("text", ""):
            print("⚠️ Turno annullato per preservare la storia.")
            return response_data if response_data else {"text": "Risposta vuota dall'IA. Riprova.", "visual_en": "",
                                                        "tags_en": []}

        if "updates" in response_data:
            updates = response_data["updates"]
            self.state_manager.update_state(updates)
            if "new_fact" in updates and updates["new_fact"]:
                self.memory.add_fact(updates["new_fact"])

        if not is_intro:
            state["history"].append({"role": "user", "content": final_input})

        state["history"].append({"role": "model", "content": response_data["text"]})
        self.state_manager.save_game("autosave.json")

        return response_data

    def process_image_generation(self, visual_en: str, tags_en: List[str]) -> str:
        history = self.state_manager.current_state.get("history", [])
        last_narrative = ""
        if history and history[-1]["role"] == "model":
            last_narrative = history[-1]["content"]

        pos, neg = PromptDispatcher.dispatch(
            text_response=last_narrative,
            visual_en=visual_en,
            tags_en=tags_en,
            game_state=self.state_manager.current_state,
            world_data=self.world_data
        )

        print(f"\n🎨 [SD PROMPT FINAL]: {pos[:200]}...")
        return self.imager.generate_image(pos, neg)

    def process_audio(self, text: str):
        if not text: return
        name = self.state_manager.current_state["game"].get("companion_name", "Narrator")
        self.audio.play_voice(text, name)

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

    # --- MODIFICA CHIAVE QUI SOTTO ---
    def _build_system_prompt(self) -> str:
        meta = self.world_data.get("meta", {})
        game = self.state_manager.current_state.get("game", {})

        char_name = game.get('companion_name')
        current_aff = game.get("affinity", {}).get(char_name, 0)
        partner_personality = self._get_affinity_personality(char_name, current_aff)

        all_companions = list(self.world_data.get("companions", {}).keys())
        other_chars = [c for c in all_companions if c != char_name]

        # COSTRUZIONE STATO NPC (Include Outfit!)
        npc_instructions = ""
        for npc in other_chars:
            npc_aff = game.get("affinity", {}).get(npc, 0)
            npc_pers = self._get_affinity_personality(npc, npc_aff)

            # Recupera Outfit dallo stato NPC
            npc_outfit = "Default"
            if "npc_states" in game and npc in game["npc_states"]:
                npc_outfit = game["npc_states"][npc].get("current_outfit", "Default")

            npc_instructions += f"- {npc}: {npc_pers} [CURRENT OUTFIT: {npc_outfit}]\n"

        story_struct = meta.get("story_structure", {})
        key_events = story_struct.get("key_events", [])
        events_str = "POSSIBLE PLOT POINTS:\n"
        for e in key_events: events_str += f"- [KEY] {e}\n"

        prompt_vars = {
            "genre": meta.get('genre', 'RPG'),
            "world_name": meta.get('name', 'Unknown World'),
            "world_lore": meta.get('world_lore', 'No lore available.'),
            "events_str": events_str,
            "char_name": char_name,
            "partner_personality": partner_personality,
            "npc_instructions": npc_instructions,
            "time_of_day": game.get('time_of_day', 'Morning'),
            "location": game.get('location', 'Unknown'),
            "current_outfit": game.get('current_outfit', 'default')
        }

        prompt_path = "prompts/system_prompt.txt"
        if not os.path.exists(prompt_path):
            return f"You are a Game Master. Context: {prompt_vars}"

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template.format(**prompt_vars)
        except Exception as e:
            print(f"❌ Error formatting prompt: {e}")
            return "System Error: Prompt generation failed."