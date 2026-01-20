import os
from pathlib import Path

# Nome progetto (siamo già nella root)
PROJECT_NAME = "."

# Struttura completa
STRUCTURE = {
    "config": [
        "settings.py",  # Gestione Locale/Runpod
        "world_schema.yaml",  # Regole per validare i mondi
    ],
    "worlds": [
        "fantasy_dark.yaml",  # Esempio Fantasy (Ex Canovaccio C)
        "cyberpunk_noir.yaml",  # Esempio Cyberpunk
    ],
    "core": [
        "__init__.py",
        "engine.py",  # Loop di gioco
        "world_loader.py",  # Caricatore YAML
        "state_manager.py",  # Gestione salvataggi
        "prompt_builder.py",  # LOGICA COMPLESSA (Multi-Girl, Smart Outfit, Rules)
    ],
    "media": [
        "__init__.py",
        "llm_client.py",  # Gemini
        "image_client.py",  # Stable Diffusion (Locale/RunPod)
        "video_client.py",  # ComfyUI (RunPod)
        "audio_client.py",  # TTS
    ],
    "ui": [
        "__init__.py",
        "main_window.py",  # GUI PySide6
        "styles.qss",  # CSS per la GUI
    ],
    "ui/components": [
        "__init__.py",
        "chat_widget.py",
        "image_viewer.py",
        "status_panel.py",
    ],
    "assets": [],
    ".": [
        ".env",  # Configurazione segreta
        "main.py",  # Avvio
    ]
}

# --- CONTENUTI INTELLIGENTI ---

ENV_CONTENT = """# --- MODALITÀ ---
# Scegli: LOCAL (PC tuo, no video) oppure RUNPOD (Cloud, video attivo)
EXECUTION_MODE=LOCAL

# --- API KEYS ---
GEMINI_API_KEY=

# --- RUNPOD ---
# Inserisci qui l'ID del pod (es. cpc3l0m...) se usi RUNPOD
RUNPOD_ID=
RUNPOD_API_KEY=
"""

SETTINGS_CONTENT = """import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MODE = os.getenv("EXECUTION_MODE", "LOCAL").upper()
    GEMINI_KEY = os.getenv("GEMINI_API_KEY")

    @staticmethod
    def get_sd_url():
        # Se siamo su RunPod, costruiamo l'URL proxy dinamicamente
        if Settings.MODE == "RUNPOD":
            pod_id = os.getenv("RUNPOD_ID")
            return f"https://{pod_id}-7860.proxy.runpod.net" if pod_id else ""
        # Altrimenti fallback su locale
        return "http://127.0.0.1:7860"

    @staticmethod
    def get_comfy_url():
        if Settings.MODE == "RUNPOD":
            pod_id = os.getenv("RUNPOD_ID")
            return f"https://{pod_id}-8188.proxy.runpod.net" if pod_id else ""
        return None  # Disabilitato in locale per sicurezza

    @staticmethod
    def video_enabled():
        return Settings.MODE == "RUNPOD"
"""

PROMPT_BUILDER_SKELETON = """# file: core/prompt_builder.py
# Modulo per la costruzione intelligente dei prompt (Smart Outfit, Multi-Character)

from typing import Dict, List, Tuple

def build_image_prompt(visual_en: str, tags_en: List[str], game_state: Dict) -> Tuple[str, str]:
    \"\"\"
    Logica complessa per assemblare il prompt.
    1. Legge il profilo dallo YAML (tramite game_state).
    2. Applica Smart Outfit (Nude/Vestita).
    3. Gestisce gruppi (2girls) se ci sono più personaggi.
    4. Incolla i tag dell'LLM.
    \"\"\"
    # TODO: Implementare la logica discussa
    return "", ""
"""

MAIN_CONTENT = """import sys
import os
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from config.settings import Settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LUNA-RPG v2 - Bootloader")
        self.resize(400, 200)

        mode = Settings.MODE
        sd_url = Settings.get_sd_url()

        lbl = QLabel(f"Sistema avviato.\\nModalità: {mode}\\nSD URL: {sd_url}", self)
        lbl.setWordWrap(True)
        self.setCentralWidget(lbl)

def main():
    print(f"🚀 Avvio LUNA-RPG v2 in modalità: {Settings.MODE}")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
"""


# --- ESECUZIONE ---
def create_structure():
    root = Path(PROJECT_NAME)
    print("🔨 Creazione struttura LUNA-RPG v2...")

    for folder, files in STRUCTURE.items():
        if folder == ".":
            current_dir = root
        else:
            current_dir = root / folder
            current_dir.mkdir(parents=True, exist_ok=True)

        for filename in files:
            file_path = current_dir / filename
            if not file_path.exists():
                content = ""
                # Iniezione contenuti base
                if filename == ".env":
                    content = ENV_CONTENT
                elif filename == "settings.py":
                    content = SETTINGS_CONTENT
                elif filename == "main.py":
                    content = MAIN_CONTENT
                elif filename == "prompt_builder.py":
                    content = PROMPT_BUILDER_SKELETON
                elif filename.endswith(".py"):
                    content = f"# file: {folder}/{filename}\n"

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"  ✅ Creato: {filename}")
            else:
                print(f"  ⚠️ Esiste già: {filename}")

    # Cartelle di storage (non vanno su git di solito, ma le creiamo)
    for d in ["storage/saves", "storage/images", "storage/videos"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    print("\n🎉 Struttura completata. Ora torna su GitHub Desktop!")


if __name__ == "__main__":
    create_structure()