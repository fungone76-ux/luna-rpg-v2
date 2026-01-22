# file: media/image_client.py
import base64
import requests
import os
import time
from datetime import datetime
from config.settings import Settings


class ImageClient:
    def __init__(self):
        self.settings = Settings.get_instance()
        # Non impostiamo l'URL qui nel __init__ perché potrebbe cambiare tra un riavvio e l'altro
        # Lo leggiamo dinamicamente ad ogni chiamata.

    def generate_image(self, pos_prompt: str, neg_prompt: str) -> str:
        """
        Invia richiesta a Stable Diffusion (Locale o RunPod).
        """
        # Recupera l'URL corretto (Locale o RunPod) in base alla checkbox
        base_url = self.settings.get_sd_url()
        api_url = f"{base_url}/sdapi/v1/txt2img"

        payload = {
            "prompt": pos_prompt,
            "negative_prompt": neg_prompt,
            "steps": 24,
            "width": 896,  # Formato verticale per ritratti
            "height": 1152,
            "sampler_name": "Euler a",
            "cfg_scale": 7,
            "enable_hr": False,  # HR Fix rallenta, attivalo se usi RunPod potente
        }

        print(f"📡 Connecting to SD Backend: {base_url} ...")

        try:
            response = requests.post(api_url, json=payload, timeout=720)  # Timeout lungo per RunPod

            if response.status_code == 200:
                r = response.json()
                img_data = base64.b64decode(r['images'][0])

                # Salvataggio
                filename = f"img_{int(time.time())}.png"
                save_path = os.path.join("storage", "images", filename)
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                with open(save_path, "wb") as f:
                    f.write(img_data)

                print(f"🖼️ Immagine salvata: {save_path}")
                return save_path
            else:
                print(f"❌ Errore SD: {response.status_code} - {response.text}")
                return ""

        except Exception as e:
            print(f"❌ Errore Connessione SD ({base_url}): {e}")
            return ""