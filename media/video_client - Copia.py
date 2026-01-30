import json, os, time, uuid, requests, websocket, gc
from config.settings import Settings
from media.llm_client import LLMClient


class VideoClient:
    def __init__(self):
        self.settings = Settings.get_instance()
        self.llm = LLMClient()
        self.client_id = str(uuid.uuid4())
        sd_url = self.settings.get_sd_url().rstrip("/")
        self.comfy_url = sd_url.replace("-7860", "-8188") if "runpod.net" in sd_url else "http://127.0.0.1:8188"
        self.sd_url = sd_url
        self.workflow_path = "wan_gguf_workflow.json"

    def _manage_vram(self, action="unload"):
        try:
            endpoint = "unload-checkpoint" if action == "unload" else "reload-checkpoint"
            requests.post(f"{self.sd_url}/sdapi/v1/{endpoint}", timeout=10)
            if action == "unload":
                requests.post(f"{self.sd_url}/sdapi/v1/free-memory", timeout=10)
                gc.collect()
                time.sleep(5)
        except:
            pass

    def generate_video(self, image_path: str, context_text: str) -> str:
        if not os.path.exists(image_path): return ""
        self._manage_vram("unload")
        try:
            prompt_en = self.llm.generate_response(context_text, "AI Director. Technical EN prompt.", []).get("text",
                                                                                                              "motion")
            with open(self.workflow_path, "r", encoding="utf-8") as f:
                wf = json.load(f)

            with open(image_path, "rb") as f:
                res = requests.post(f"{self.comfy_url}/upload/image", files={"image": f}).json()

            # Patch essenziale
            wf["6"]["inputs"]["image"] = res["name"]
            wf["5"]["inputs"]["text"] = prompt_en

            ws = websocket.WebSocket()
            ws.connect(f"{self.comfy_url.replace('http', 'ws')}/ws?clientId={self.client_id}")
            p_res = requests.post(f"{self.comfy_url}/prompt", json={"prompt": wf, "client_id": self.client_id}).json()
            pid = p_res['prompt_id']

            while True:
                msg = json.loads(ws.recv())
                if msg.get("type") == "executing" and msg["data"]["node"] is None: break

            hist = requests.get(f"{self.comfy_url}/history/{pid}").json()[pid]
            for nid in hist['outputs']:
                for f in hist['outputs'][nid].get('images', []) + hist['outputs'][nid].get('gifs', []):
                    raw = requests.get(f"{self.comfy_url}/view", params={"filename": f['filename']}).content
                    path = os.path.join("storage/videos", f"Luna_Video_{int(time.time())}.mp4")
                    os.makedirs("storage/videos", exist_ok=True)
                    with open(path, "wb") as file: file.write(raw)
                    return path
        finally:
            self._manage_vram("reload")