# file: core/world_loader.py
import yaml
import os
from pathlib import Path
from typing import List, Dict, Optional


class WorldLoader:
    """
    Gestisce il caricamento delle 'Cartucce' (file YAML) del mondo.
    """

    def __init__(self, worlds_dir: str = "worlds"):
        # FIX: Usiamo __file__ per trovare la root del progetto in modo assoluto
        # Path(__file__) = .../luna-rpg-v2/core/world_loader.py
        # .parent        = .../luna-rpg-v2/core
        # .parent.parent = .../luna-rpg-v2 (ROOT)

        current_script_dir = Path(__file__).resolve().parent
        project_root = current_script_dir.parent

        self.worlds_path = project_root / worlds_dir

    def list_available_worlds(self) -> List[Dict[str, str]]:
        """
        Scansiona la cartella e restituisce una lista di mondi disponibili.
        Ritorna una lista di dict: [{'id': 'fantasy_dark', 'name': 'Il Sigillo...'}, ...]
        """
        results = []

        # Debug: Stampa dove sta cercando, così siamo sicuri
        # print(f"[DEBUG] Cerco mondi in: {self.worlds_path}")

        if not self.worlds_path.exists():
            print(f"⚠️ ATTENZIONE: Cartella '{self.worlds_path}' non trovata.")
            return []

        for file in self.worlds_path.glob("*.yaml"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    # Cerchiamo i metadati
                    meta = data.get("meta", {})
                    world_id = meta.get("id", file.stem)
                    name = meta.get("name", file.stem)
                    genre = meta.get("genre", "Unknown")

                    results.append({
                        "id": world_id,
                        "name": name,
                        "genre": genre,
                        "filename": file.name
                    })
            except Exception as e:
                print(f"❌ Errore lettura {file.name}: {e}")

        return results

    def load_world_data(self, filename: str) -> Optional[Dict]:
        """
        Carica il contenuto completo di un mondo specifico.
        """
        full_path = self.worlds_path / filename
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Errore caricamento mondo {filename}: {e}")
            return None


# Test rapido (eseguito solo se lanci questo file direttamente)
if __name__ == "__main__":
    loader = WorldLoader()
    print(f"📂 Percorso mondi rilevato: {loader.worlds_path}")
    worlds = loader.list_available_worlds()
    print(f"🌎 Mondi trovati: {worlds}")