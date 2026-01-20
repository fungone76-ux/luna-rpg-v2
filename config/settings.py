import os
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
