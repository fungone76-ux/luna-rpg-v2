# file: core/engine.py
import time
from typing import Dict, List, Tuple, Optional

# --- MODULI CORE ---
from core.world_loader import WorldLoader
from core.state_manager import StateManager
from core.prompt_builder import build_image_prompt

# --- MODULI MEDIA ---
from media.llm_client import LLMClient
from media.image_client import ImageClient
from media.audio_client import AudioClient

# --- COSTANTI MEMORIA ---
MEMORY_LIMIT = 12  # Numero massimo di scambi in memoria attiva
MEMORY_PRUNE_COUNT = 4  # Quanti messaggi vecchi riassumere quando piena


class GameEngine:
    def __init__(self):
        # 1. Caricamento Moduli Dati
        self.loader = WorldLoader()
        self.state_manager = StateManager()

        # 2. Inizializzazione Client Multimediali
        self.llm = LLMClient()
        self.imager = ImageClient()
        self.audio = AudioClient()

        # Stato interno
        self.world_data = {}
        self.session_active = False

    def list_worlds(self):
        """Restituisce la lista dei mondi disponibili (YAML)."""
        return self.loader.list_available_worlds()

    def start_new_game(self, world_id: str, companion_name: str = "Luna"):
        """Avvia una nuova partita da zero."""
        # Carica i dati statici del mondo
        self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
        if not self.world_data:
            raise ValueError(f"Impossibile caricare il mondo: {world_id}")

        # Inizializza la sessione e lo stato
        self.state_manager.create_new_session(self.world_data, companion_name)
        self.session_active = True

        # Inizializza il log dei riassunti se manca
        if "summary_log" not in self.state_manager.current_state:
            self.state_manager.current_state["summary_log"] = []

        # Genera il primo messaggio di benvenuto (senza input utente)
        return self.generate_turn_response(user_input=None, is_intro=True)

    def load_game(self, filename: str):
        """Carica un salvataggio esistente."""
        if self.state_manager.load_game(filename):
            # Recupera l'ID del mondo dal salvataggio per ricaricare i dati YAML
            world_id = self.state_manager.current_state["meta"].get("world_id")
            self.world_data = self.loader.load_world_data(f"{world_id}.yaml")
            self.session_active = True
            return True
        return False

    def _manage_long_term_memory(self):
        """
        Gestisce la memoria a lungo termine riassumendo i messaggi vecchi.
        """
        history = self.state_manager.current_state.get("history", [])

        if len(history) > MEMORY_LIMIT:
            print(f"🧠 Memoria piena ({len(history)}/{MEMORY_LIMIT}). Comprimo i ricordi...")

            to_prune = history[:MEMORY_PRUNE_COUNT]
            remaining = history[MEMORY_PRUNE_COUNT:]

            # Chiede all'LLM di riassumere i messaggi vecchi
            summary_text = self.llm.summarize_history(to_prune)

            # Archivia il riassunto
            self.state_manager.current_state["summary_log"].append(summary_text)

            # Mantiene solo i messaggi recenti
            self.state_manager.current_state["history"] = remaining
            print(f"✅ Memoria compressa. Nuovo riassunto: {summary_text[:50]}...")

    def generate_turn_response(self, user_input: str, is_intro: bool = False) -> Dict:
        """
        CICLO PRINCIPALE DEL GIOCO:
        Input Utente -> LLM -> Immagine -> Audio -> Output UI
        """
        if not self.session_active:
            return {"text": "Nessuna sessione attiva.", "image": None}

        state = self.state_manager.current_state
        game_data = state.get("game", {})
        companion_name = game_data.get("companion_name", "Unknown")

        # 1. Gestione Memoria (solo se non è l'intro)
        if not is_intro:
            self._manage_long_term_memory()

        # 2. Costruzione Prompt per l'LLM
        # Qui diciamo a Gemini COME rispondere (JSON incluso)
        system_prompt = self._build_system_prompt()
        history = state.get("history", [])
        summaries = state.get("summary_log", [])

        # Testo da inviare (se è intro, usiamo un trigger speciale)
        final_input = user_input if not is_intro else "Introduci la storia e descrivi dove ci troviamo."

        # 3. Chiamata LLM (Gemini)
        # Il client si occupa di estrarre il JSON con tags e visual_en
        response_data = self.llm.generate_response(
            user_input=final_input,
            system_instruction=system_prompt,
            history=history,
            summaries=summaries
        )

        # 4. Aggiornamento Stato (Inventario, Affinità, ecc.)
        if "updates" in response_data:
            self.state_manager.update_state(response_data["updates"])

        # Aggiornamento History
        if not is_intro:
            state["history"].append({"role": "user", "content": final_input})
        state["history"].append({"role": "model", "content": response_data["text"]})

        # 5. Generazione Immagine (Stable Diffusion)
        visual_en = response_data.get("visual_en", "")
        tags_en = response_data.get("tags_en", [])

        # Usa il Prompt Builder intelligente (Multi-Girl, Smart Outfit)
        pos_prompt, neg_prompt = build_image_prompt(
            visual_en, tags_en, game_data, self.world_data
        )

        # --- DEBUG: STAMPA I PROMPT ---
        print("\n" + "=" * 50)
        print("🎨 [SD DEBUG] PROMPT GENERATI:")
        print(f"➕ POSITIVE:\n{pos_prompt}")
        print("-" * 20)
        print(f"➖ NEGATIVE:\n{neg_prompt}")
        print("=" * 50 + "\n")
        # ------------------------------

        image_path = self.imager.generate_image(pos_prompt, neg_prompt)

        # 6. Audio / Voce Narrante
        # Passiamo il testo e il nome del personaggio per gestire voci diverse
        self.audio.play_voice(
            text=response_data["text"],
            character_name=companion_name
        )

        # 7. Autosave
        self.state_manager.save_game("autosave.json")

        return {
            "text": response_data["text"],
            "image": image_path,
            "visual_debug": visual_en
        }

    def _build_system_prompt(self) -> str:
        """
        Crea le istruzioni per il Dungeon Master.
        Questa parte è CRUCIALE perché insegna a Gemini a generare il JSON nascosto.
        """
        meta = self.world_data.get("meta", {})
        game = self.state_manager.current_state.get("game", {})

        return f"""
        Sei il Dungeon Master di un'avventura {meta.get('genre')}.
        Mondo: {meta.get('name')} - {meta.get('description')}

        Personaggio Compagno: {game.get('companion_name')}
        Stato Attuale:
        - Luogo: {game.get('location')}
        - Outfit: {game.get('current_outfit')}
        - Inventario: {game.get('inventory')}

        REGOLE OUTPUT (Cruciale):
        1. Rispondi in Italiano narrando la storia in modo coinvolgente.
        2. Mantieni il carattere del personaggio (Luna/Stella/Maria) coerente con la sua descrizione.
        3. Alla fine della risposta, DEVI generare un blocco JSON nascosto in questo formato esatto:

        ```json
        {{
           "visual_en": "descrizione visiva della scena in inglese per generatore immagini (soggetto fisico + azione)",
           "tags_en": ["tag1", "tag2", "lighting condition"],
           "updates": {{
               "location": "Nuovo Luogo se cambiato",
               "add_item": "Oggetto trovato se c'è",
               "affinity_change": {{"Luna": 1}}
           }}
        }}
        ```
        """