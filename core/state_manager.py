# file: core/state_manager.py
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional


class StateManager:
    """
    Gestisce lo stato corrente della partita (Salvataggio, Caricamento, Creazione).
    Include gestione Tempo, Statistiche e Affinità.
    """

    def __init__(self, saves_dir: str = "storage/saves"):
        root = Path(__file__).resolve().parent.parent
        self.saves_path = root / saves_dir
        self.saves_path.mkdir(parents=True, exist_ok=True)
        self.current_state: Dict[str, Any] = {}

    def create_new_session(self, world_data: Dict, companion_name: str = "Luna") -> Dict:
        """Inizializza una nuova partita."""
        companions_db = world_data.get("companions", {})
        if companion_name not in companions_db:
            companion_name = list(companions_db.keys())[0]

        char_data = companions_db[companion_name]
        default_outfit = char_data.get("default_outfit", "default")

        # FIX LOCATION
        world_id = world_data.get("meta", {}).get("id", "unknown")
        start_location = "Start"
        if world_id == "school_life":
            start_location = "School Entrance Gate"
        elif world_id == "fantasy_dark":
            start_location = "Dungeon Cell"

        self.current_state = {
            "meta": {
                "world_id": world_id,
                "created_at": time.time(),
                "turn_count": 1
            },
            "game": {
                "time_of_day": "Morning",
                "location": start_location,
                "companion_name": companion_name,
                "current_outfit": default_outfit,
                "inventory": [],
                "gold": 0,
                "hp": 20,
                "stats": {"strength": 10, "mind": 10, "charisma": 10},
                "affinity": {
                    "Luna": 0, "Stella": 0, "Maria": 0
                },
                "quest_log": ["Survive the School Year."],
                "flags": {}
            },
            "history": [],
            "summary_log": []  # <--- AGGIUNTO: Inizializzato subito per sicurezza
        }
        print(f"✨ Session: {companion_name} @ {start_location} (Morning)")
        return self.current_state

    def save_game(self, filename: str = "quicksave.json") -> str:
        full_path = self.saves_path / filename
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(self.current_state, f, indent=2, ensure_ascii=False)
            return str(full_path)
        except Exception as e:
            print(f"❌ Save Error: {e}")
            return ""

    def load_game(self, filename: str) -> bool:
        full_path = self.saves_path / filename
        if not full_path.exists(): return False
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                self.current_state = json.load(f)

            # Retrocompatibilità
            if "time_of_day" not in self.current_state["game"]:
                self.current_state["game"]["time_of_day"] = "Morning"
            if "stats" not in self.current_state["game"]:
                self.current_state["game"]["stats"] = {"strength": 10, "mind": 10, "charisma": 10}
            # Assicuriamoci che summary_log esista
            if "summary_log" not in self.current_state:
                self.current_state["summary_log"] = []

            return True
        except Exception as e:
            print(f"❌ Load Error: {e}")
            return False

    def update_state(self, updates: Dict):
        """Aggiorna lo stato del gioco con i dati ricevuti dall'LLM."""
        if not updates: return
        game_data = self.current_state.get("game", {})

        # 1. Aggiornamento Campi Diretti
        for key in ["location", "current_outfit", "gold", "hp", "time_of_day"]:
            if key in updates and updates[key] is not None:
                game_data[key] = updates[key]

        # 2. Inventario
        if "add_item" in updates:
            item = updates["add_item"]
            if item and isinstance(item, str) and item not in game_data["inventory"]:
                game_data["inventory"].append(item)

        if "remove_item" in updates:
            item = updates["remove_item"]
            if item and item in game_data["inventory"]:
                game_data["inventory"].remove(item)

        # 3. Flag
        if "flags" in updates:
            game_data["flags"].update(updates["flags"])

        # 4. Affinità (con limiti di sicurezza 0-100)
        if "affinity_change" in updates:
            changes = updates["affinity_change"]
            if isinstance(changes, dict):
                for char, val in changes.items():
                    if val is not None and isinstance(val, (int, float)):
                        if char in game_data["affinity"]:
                            new_val = game_data["affinity"][char] + int(val)
                            # Impedisce di andare sotto zero o sopra 100
                            game_data["affinity"][char] = max(0, min(100, new_val))

        # 5. Statistiche (con limite min 0)
        if "stat_changes" in updates:
            changes = updates["stat_changes"]
            if isinstance(changes, dict):
                for stat, val in changes.items():
                    if val is not None and isinstance(val, (int, float)):
                        if stat in game_data.get("stats", {}):
                            new_val = game_data["stats"][stat] + int(val)
                            # Impedisce statistiche negative
                            game_data["stats"][stat] = max(0, new_val)

        # Avanzamento Turno
        self.current_state["meta"]["turn_count"] += 1