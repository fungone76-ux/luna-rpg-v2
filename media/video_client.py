import json
import os
import time
import uuid
import requests
import websocket
from config.settings import Settings
from media.llm_client import LLMClient


class VideoClient:
    def __init__(self):
        self.settings = Settings.get_instance()
        self.llm = LLMClient()
        self.client_id = str(uuid.uuid4())

        # Recupera l'URL base di SD dalle impostazioni
        sd_base = self.settings.get_sd_url().rstrip("/")

        # Configurazione Automatica URL (RunPod vs Locale)
        if "runpod.net" in sd_base:
            self.comfy_url = sd_base.replace("-7860", "-8188")
            self.sd_url = sd_base
        else:
            self.comfy_url = "http://127.0.0.1:8188"
            self.sd_url = "http://127.0.0.1:7860"

        print(f"📡 Video Client configurato su: {self.comfy_url}")
        self.workflow_path = "wan_gguf_workflow.json"

    def generate_video(self, image_path: str, context_text: str) -> str:
        if not os.path.exists(image_path):
            print(f"❌ Errore Video: Immagine non trovata: {image_path}")
            return ""

        print("\n🎬 [VIDEO] Inizializzazione procedura video...")

        # 1. Prompt Engineering
        video_prompt = self._get_enhanced_prompt(context_text)
        print(f"📝 Prompt Regia: {video_prompt}")

        # 2. Staffetta VRAM
        self._manage_vram(action="unload_sd")

        try:
            # 3. Preparazione Workflow
            workflow = self._load_and_prepare_workflow(image_path, video_prompt)
            if not workflow:
                print("❌ Errore: Impossibile preparare il workflow.")
                return ""

            # 4. Esecuzione WebSocket
            print("🚀 [VIDEO] Invio a ComfyUI...")
            ws = websocket.WebSocket()
            ws_url = self.comfy_url.replace("http://", "ws://").replace("https://", "wss://")

            try:
                ws.connect(f"{ws_url}/ws?clientId={self.client_id}")
            except Exception as e:
                print(f"❌ Errore Connessione WebSocket: {e}")
                print(f"   (Verifica che ComfyUI stia girando su {ws_url})")
                return ""

            result_path = self._execute_workflow(ws, workflow)
            return result_path

        except Exception as e:
            print(f"❌ Errore Critico Video (Generico): {e}")
            return ""

    def _get_enhanced_prompt(self, context: str) -> str:
        sys_prompt = "You are an AI Video Director. Create a SHORT, TECHNICAL prompt for Wan 2.1. Focus on subtle motion. Output ONLY English text."
        try:
            resp = self.llm.generate_response(context, sys_prompt, [])
            return resp.get("text", context)
        except:
            return "high quality, cinematic, subtle motion"

    def _manage_vram(self, action="unload_sd"):
        if action == "unload_sd":
            print("📉 [VRAM] Richiesta rilascio memoria a Stable Diffusion...")
            try:
                resp = requests.post(f"{self.sd_url}/sdapi/v1/unload-checkpoint", timeout=10)
                if resp.status_code == 200:
                    print("✅ [VRAM] SD ha confermato.")
                else:
                    print(f"⚠️ [VRAM] SD Risposta anomala: {resp.status_code} - {resp.text[:50]}")
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ [VRAM] SD non raggiungibile (potrebbe essere spento): {e}")

    def _upload_image_to_comfy(self, img_path):
        """Carica l'immagine in modo sicuro"""
        try:
            with open(img_path, 'rb') as f:
                files = {'image': f}
                data = {'overwrite': 'true'}
                response = requests.post(f"{self.comfy_url}/upload/image", files=files, data=data, timeout=30)

                if response.status_code != 200:
                    print(f"❌ Errore Upload Immagine: Status {response.status_code}")
                    print(f"   Risposta Server: {response.text}")
                    return None

                return response.json().get("name")
        except json.JSONDecodeError:
            print("❌ Errore: Il server ComfyUI non ha risposto con un JSON valido.")
            print(f"   Risposta ricevuta: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"❌ Errore Upload: {e}")
            return None

    def _load_and_prepare_workflow(self, image_path, prompt):
        if not os.path.exists(self.workflow_path):
            print(f"❌ Manca il file: {self.workflow_path}")
            return None

        try:
            with open(self.workflow_path, 'r') as f:
                workflow = json.load(f)
        except json.JSONDecodeError:
            print("❌ Errore: Il file wan_gguf_workflow.json è corrotto.")
            return None

        # Carica Immagine
        filename = self._upload_image_to_comfy(image_path)
        if not filename:
            return None

        # Inietta dati nel JSON
        if "10" in workflow: workflow["10"]["inputs"]["image"] = filename
        if "6" in workflow: workflow["6"]["inputs"]["text"] = prompt

        # Pulizia sicurezza
        if "12" in workflow and "model" in workflow["12"]["inputs"]:
            del workflow["12"]["inputs"]["model"]

        return workflow

    def _execute_workflow(self, ws, workflow):
        try:
            p = {"prompt": workflow, "client_id": self.client_id}
            req = requests.post(f"{self.comfy_url}/prompt", json=p, timeout=10)

            if req.status_code != 200:
                print(f"❌ Errore Invio Workflow: {req.status_code} - {req.text}")
                return ""

            try:
                prompt_id = req.json()['prompt_id']
            except:
                print(f"❌ Errore lettura ID Prompt. Risposta server: {req.text}")
                return ""

            print(f"⏳ Rendering avviato (ID: {prompt_id})...")

            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break

                            # Recupera risultato
            history_req = requests.get(f"{self.comfy_url}/history/{prompt_id}", timeout=10)
            history = history_req.json()
            outputs = history[prompt_id]['outputs']

            for node_id in outputs:
                node_output = outputs[node_id]
                files_list = node_output.get('gifs', []) + node_output.get('images', []) + node_output.get('videos', [])

                for vid_info in files_list:
                    fname = vid_info['filename']
                    print(f"📥 Scaricamento video: {fname}")

                    video_data = requests.get(f"{self.comfy_url}/view?filename={fname}&type=output", timeout=60).content
                    save_dir = "storage/videos"
                    os.makedirs(save_dir, exist_ok=True)
                    local_path = os.path.join(save_dir, f"Luna_Video_{int(time.time())}.mp4")

                    with open(local_path, "wb") as f:
                        f.write(video_data)
                    return local_path
        except Exception as e:
            print(f"❌ Errore Esecuzione: {e}")
            return ""