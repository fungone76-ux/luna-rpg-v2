# file: core/state_manager.py
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional


class StateManager:
    """
    Gestisce lo stato corrente della partita (Salvataggio, Caricamento, Creazione).
    """

    def __init__(self, saves_dir: str = "storage/saves"):
        # Percorso assoluto basato sulla posizione dello script
        root = Path(__file__).resolve().parent.parent
        self.saves_path = root / saves_dir
        self.saves_path.mkdir(parents=True, exist_ok=True)

        # Lo stato corrente è vuoto all'inizio
        self.current_state: Dict[str, Any] = {}

    def create_new_session(self, world_data: Dict, companion_name: str = "Luna") -> Dict:
        """
        Inizializza una nuova partita basandosi sui dati del Mondo (YAML).
        """
        # Recupera i dati del companion scelto
        companions_db = world_data.get("companions", {})

        # Fallback se il nome è sbagliato
        if companion_name not in companions_db:
            companion_name = list(companions_db.keys())[0]

        char_data = companions_db[companion_name]
        default_outfit = char_data.get("default_outfit", "default")

        # CREAZIONE STATO INIZIALE
        self.current_state = {
            "meta": {
                "world_id": world_data.get("meta", {}).get("id", "unknown"),
                "created_at": time.time(),
                "turn_count": 1
            },
            "game": {
                "location": "Start",  # Sarà sovrascritto dalla prima scena
                "companion_name": companion_name,
                "current_outfit": default_outfit,
                "inventory": [],
                "gold": 0,
                "affinity": {
                    "Luna": 0, "Stella": 0, "Maria": 0
                },
                "quest_log": ["Sopravvivi."],
                "flags": {}  # Per tracciare eventi (es. "met_boss": True)
            },
            "history": []  # Storico dialoghi per l'LLM
        }

        print(f"✨ Nuova sessione creata: {companion_name} in {world_data.get('meta', {}).get('name')}")
        return self.current_state

    def save_game(self, filename: str = "quicksave.json") -> str:
        """Salva lo stato corrente su disco."""
        full_path = self.saves_path / filename
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(self.current_state, f, indent=2, ensure_ascii=False)
            print(f"💾 Partita salvata in: {full_path}")
            return str(full_path)
        except Exception as e:
            print(f"❌ Errore salvataggio: {e}")
            return ""

    def load_game(self, filename: str) -> bool:
        """Carica un salvataggio da disco."""
        full_path = self.saves_path / filename
        if not full_path.exists():
            print(f"⚠️ File non trovato: {filename}")
            return False

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                self.current_state = json.load(f)
            print(f"📂 Partita caricata: {filename}")
            return True
        except Exception as e:
            print(f"❌ Errore caricamento: {e}")
            return False

    def update_state(self, updates: Dict):
        """
        Aggiorna lo stato con i dati ricevuti dall'LLM (es. nuovi oggetti, cambio location).
        """
        if not updates:
            return

        game_data = self.current_state.get("game", {})

        # Aggiorna campi semplici (location, gold, outfit)
        for key in ["location", "current_outfit", "gold"]:
            if key in updates and updates[key] is not None:
                game_data[key] = updates[key]

        # Gestione Inventario (Aggiunta/Rimozione intelligente)
        # Se l'LLM manda "add_item": "Spada", lo aggiungiamo.
        if "add_item" in updates:
            item = updates["add_item"]
            if item and item not in game_data["inventory"]:
                game_data["inventory"].append(item)

        if "remove_item" in updates:
            item = updates["remove_item"]
            if item in game_data["inventory"]:
                game_data["inventory"].remove(item)

        # Aggiorna Flag e Affinità
        if "flags" in updates:
            game_data["flags"].update(updates["flags"])

        if "affinity_change" in updates:
            # Es: {"Luna": +1, "Maria": -2}
            changes = updates["affinity_change"]
            for char, val in changes.items():
                if char in game_data["affinity"]:
                    game_data["affinity"][char] += val

        # Aggiorna contatore turni
        self.current_state["meta"]["turn_count"] += 1


# Test rapido
if __name__ == "__main__":
    # Simuliamo un flusso
    mgr = StateManager()

    # Finto world data per test
    dummy_world = {
        "meta": {"id": "test_world", "name": "Mondo Test"},
        "companions": {"Luna": {"default_outfit": "tuta_test"}}
    }

    mgr.create_new_session(dummy_world, "Luna")
    mgr.update_state({"location": "Taverna", "add_item": "Chiave arrugginita"})
    mgr.save_game("test_save.json")
