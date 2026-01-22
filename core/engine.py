# file: core/engine.py
import time
from typing import Dict, List, Tuple, Optional

# --- CORE MODULES ---
from core.world_loader import WorldLoader
from core.state_manager import StateManager
from core.prompt_builder import build_image_prompt

# --- MEDIA MODULES ---
from media.llm_client import LLMClient
from media.image_client import ImageClient
from media.audio_client import AudioClient

# --- MEMORY CONSTANTS ---
MEMORY_LIMIT = 12
MEMORY_PRUNE_COUNT = 4


class GameEngine:
    def __init__(self):
        # 1. Load Data Modules
        self.loader = WorldLoader()
        self.state_manager = StateManager()

        # 2. Init Media Clients
        self.llm = LLMClient()
        self.imager = ImageClient()
        self.audio = AudioClient()

        # Internal State
        self.world_data = {}
        self.session_active = False

    def list_worlds(self):
        """Returns list of available worlds."""
        return self.loader.list_available_worlds()

    def start_new_game(self, world_id: str, companion_name: str = "Luna"):
        """Prepares session, DOES NOT generate intro (UI handles it)."""
        self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
        if not self.world_data:
            raise ValueError(f"Cannot load world: {world_id}")

        self.state_manager.create_new_session(self.world_data, companion_name)
        self.session_active = True

        if "summary_log" not in self.state_manager.current_state:
            self.state_manager.current_state["summary_log"] = []

        return True

    def load_game(self, filename: str):
        """Loads existing save."""
        if self.state_manager.load_game(filename):
            world_id = self.state_manager.current_state["meta"].get("world_id")
            self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
            self.session_active = True
            return True
        return False

    # --- PHASE 1: BRAIN (LLM) - FAST ---
    def process_turn_llm(self, user_input: str, is_intro: bool = False) -> Dict:
        """
        Executes ONLY the thinking part. Returns text and image data.
        Non-blocking.
        """
        if not self.session_active:
            return {"text": "Error: No active session.", "visual_en": "", "tags_en": []}

        state = self.state_manager.current_state
        companion_name = state["game"].get("companion_name", "Unknown")

        # 1. Memory Management
        if not is_intro:
            self._manage_long_term_memory()

        # 2. Build Prompt (English)
        system_prompt = self._build_system_prompt()
        history = state.get("history", [])
        summaries = state.get("summary_log", [])

        final_input = user_input
        if is_intro:
            # Explicit instruction for the start
            final_input = (
                f"[SYSTEM]: Start the story now. The User (Protagonist) wakes up or arrives in a new location "
                f"together with his partner {companion_name}. Describe the scene and her appearance. "
                f"Keep it brief, direct, and immersive (max 4 sentences).")

        # 3. Call LLM
        response_data = self.llm.generate_response(
            user_input=final_input,
            system_instruction=system_prompt,
            history=history,
            summaries=summaries
        )

        # 4. Update State
        if "updates" in response_data:
            self.state_manager.update_state(response_data["updates"])

        # Update History
        if not is_intro:
            state["history"].append({"role": "user", "content": final_input})
        state["history"].append({"role": "model", "content": response_data["text"]})

        # Autosave
        self.state_manager.save_game("autosave.json")

        return response_data

    # --- PHASE 2: EYES (Stable Diffusion) - SLOW ---
    # CORREZIONE QUI: Questa funzione ora è allineata con process_turn_llm, NON dentro!
    def process_image_generation(self, visual_en: str, tags_en: List[str]) -> str:
        """Builds prompt and calls SD. Executed in separate thread."""
        game_data = self.state_manager.current_state.get("game", {})

        # Smart Prompt Builder
        pos_prompt, neg_prompt = build_image_prompt(
            visual_en, tags_en, game_data, self.world_data
        )

        # --- DEBUG COMPLETO NEL TERMINALE ---
        print("\n" + "=" * 50)
        print("🎨 [SD PROMPT DEBUG]")
        print(f"➕ POSITIVE PROMPT:\n{pos_prompt}")
        print("-" * 20)
        print(f"➖ NEGATIVE PROMPT:\n{neg_prompt}")
        print("=" * 50 + "\n")
        # ------------------------------------

        return self.imager.generate_image(pos_prompt, neg_prompt)

    # --- PHASE 3: VOICE (TTS) - MEDIUM ---
    def process_audio(self, text: str):
        """Generates and plays audio."""
        companion_name = self.state_manager.current_state["game"].get("companion_name", "Narrator")
        self.audio.play_voice(text, companion_name)

    def _manage_long_term_memory(self):
        """Compresses old history."""
        history = self.state_manager.current_state.get("history", [])
        if len(history) > MEMORY_LIMIT:
            print(f"🧠 Memory Full ({len(history)}/{MEMORY_LIMIT}). Compressing...")
            to_prune = history[:MEMORY_PRUNE_COUNT]
            remaining = history[MEMORY_PRUNE_COUNT:]

            summary_text = self.llm.summarize_history(to_prune)
            self.state_manager.current_state["summary_log"].append(summary_text)
            self.state_manager.current_state["history"] = remaining
            print(f"✅ Memory Compressed. New summary: {summary_text[:50]}...")

    def _build_system_prompt(self) -> str:
        """
        Builds the System Instruction for Gemini (IN ENGLISH).
        """
        meta = self.world_data.get("meta", {})
        game = self.state_manager.current_state.get("game", {})

        # Current Partner
        char_name = game.get('companion_name')

        # Other NPCs defined in YAML
        all_companions = list(self.world_data.get("companions", {}).keys())
        other_key_chars = [c for c in all_companions if c != char_name]
        key_npcs_str = ", ".join(other_key_chars) if other_key_chars else "None"

        return f"""
        You are the Dungeon Master of a {meta.get('genre')} adventure.
        World: {meta.get('name')}

        ### CHARACTER HIERARCHY
        1. THE USER (Protagonist): Main male character.
        2. THE PARTNER ({char_name}): Main female companion.
        3. KEY NPCs ({key_npcs_str}): Important characters.
        4. GENERIC NPCs: Shopkeepers, guards, monsters, etc.

        ### YOUR ROLE
        - Narrator: Speak for environment and NPCs.
        - **Visual Director**: You are an expert Cinematographer. Your goal is to describe scenes for a high-end AI Image Generator.

        ### CURRENT STATE ({char_name})
        - Location: {game.get('location')}
        - Outfit: {game.get('current_outfit')}

        ### VISUAL STYLE GUIDE (Strictly for 'visual_en')
        When generating the visual description, DO NOT use generic sentences like "There is a man".
        Instead, use **Artistic Tags** and **Photography Terms**:
        - **Lighting**: Volumetric lighting, cinematic lighting, rim light, bioluminescence, harsh shadows, god rays.
        - **Camera**: Low angle, high angle, dutch angle, macro shot, wide shot, depth of field, bokeh.
        - **Texture**: Hyper-realistic, 8k, detailed skin, sweat, grime, blood, rust, metallic.
        - **Focus**: Focus on the subject's expression and action.

        ### RULES
        1. Narrate story in **ITALIAN** (Second Person).
        2. JSON Output in **ENGLISH**.
        3. Camera Director Logic: Decide the main subject (User, Partner, Enemy, or Environment).

        ### OUTPUT FORMAT
        ```json
        {{
           "visual_en": "Cinematic shot of [Subject], [Action], [Lighting], [Camera Angle], [Details]",
           "tags_en": ["tag1", "tag2", "specific_lighting_tag"],
           "updates": {{ 
               "image_subject": "The Main Subject Name", 
               "location": "...", 
               "add_item": "...",
               "affinity_change": {{ "{char_name}": 1 }} 
           }}
        }}
        ```
        """