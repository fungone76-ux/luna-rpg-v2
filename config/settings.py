# file: config/settings.py
import json
import os

SETTINGS_FILE = "settings.json"

class Settings:
    _instance = None

    def __init__(self):
        self.config = {
            "runpod_active": False,
            "runpod_url": "https://tuo-id-runpod.proxy.runpod.net",
            "local_url": "http://127.0.0.1:7860"
        }
        self.load()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except:
                pass

    def save(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    # Helper rapidi
    def is_runpod(self):
        return self.config.get("runpod_active", False)

    def get_sd_url(self):
        if self.is_runpod():
            # Pulisce l'URL se l'utente mette lo slash finale
            url = self.config.get("runpod_url", "").rstrip("/")
            return url if url else "http://127.0.0.1:7860"
        return self.config.get("local_url", "http://127.0.0.1:7860")