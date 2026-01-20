# file: media/image_client.py
import requests
import base64
import time
import os
from pathlib import Path
from config.settings import Settings


class ImageClient:
    def __init__(self):
        self.sd_url = Settings.get_sd_url()
        self.output_dir = Path("storage/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Test connettività silenzioso
        self.online = self._check_connection()
        if self.online:
            print(f"✅ Image Client: Connesso a SD ({self.sd_url})")
        else:
            print(f"⚠️ Image Client: SD Offline ({self.sd_url}). Generazione disabilitata.")

    def _check_connection(self):
        """Verifica se SD è raggiungibile."""
        if not self.sd_url: return False
        try:
            # Chiamata leggera per vedere se l'API risponde
            requests.get(f"{self.sd_url}/sdapi/v1/progress", timeout=3)
            return True
        except:
            return False

    def generate_image(self, positive_prompt: str, negative_prompt: str) -> str:
        """
        Invia la richiesta a SD e salva l'immagine.
        Restituisce il percorso del file salvato.
        """
        if not self.online:
            print("🎨 [MOCK] SD Offline - Immagine immaginaria generata.")
            return ""

        payload = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "steps": 25,
            "width": 896,  # Formato cinematico
            "height": 1152,
            "cfg_scale": 7,
            "sampler_name": "Euler a",
            "batch_size": 1,
        }

        try:
            print("🎨 Invio richiesta a Stable Diffusion...")
            response = requests.post(f"{self.sd_url}/sdapi/v1/txt2img", json=payload, timeout=120)

            if response.status_code == 200:
                r = response.json()
                image_data = base64.b64decode(r['images'][0])

                # Nome file univoco
                filename = f"img_{int(time.time())}.png"
                filepath = self.output_dir / filename

                with open(filepath, "wb") as f:
                    f.write(image_data)

                print(f"🖼️ Immagine salvata: {filepath}")
                return str(filepath)
            else:
                print(f"❌ Errore SD: {response.status_code}")
                return ""

        except Exception as e:
            print(f"❌ Errore Generazione: {e}")
            return ""
