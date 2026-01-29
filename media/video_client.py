import json
import os
import time
import uuid
import requests
import websocket
import gc
from config.settings import Settings
from media.llm_client import LLMClient


class VideoClient:
    def __init__(self):
        self.settings = Settings.get_instance()
        self.llm = LLMClient()
        self.client_id = str(uuid.uuid4())
        sd_base = self.settings.get_sd_url().rstrip("/")
        self.comfy_url = sd_base.replace("-7860", "-8188") if "runpod.net" in sd_base else "http://127.0.0.1:8188"
        self.sd_url = sd_base if "runpod.net" in sd_base else "http://127.0.0.1:7860"
        self.workflow_path = "wan_gguf_workflow.json"

    def _manage_vram(self, target="sd", action="unload"):
        """Gestione staffetta VRAM aggressiva (Logica legacy bridge)."""
        try:
            if target == "sd":
                endpoint = "unload-checkpoint" if action == "unload" else "reload-checkpoint"
                print(f"🔄 [VRAM] SD: {action}...")
                requests.post(f"{self.sd_url}/sdapi/v1/{endpoint}", timeout=10)
                if action == "unload":
                    requests.post(f"{self.sd_url}/sdapi/v1/free-memory", timeout=10)
            elif target == "comfy" and action == "free":
                print("🧹 [VRAM] Liberazione memoria ComfyUI...")
                requests.post(f"{self.comfy_url}/free", json={}, timeout=10)

            gc.collect()
            time.sleep(8)  # Tempo critico per driver NVIDIA
        except Exception as e:
            print(f"⚠️ [VRAM] Error: {e}")

    def generate_video(self, image_path: str, context_text: str) -> str:
        if not os.path.exists(image_path): return ""

        # 1. STAFFETTA: SPEGNIMENTO SD
        self._manage_vram("sd", "unload")

        try:
            # 2. Prompt Engineer (Logica Gemini professionale)
            video_prompt = self._get_engineered_prompt(context_text)

            with open(self.workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            with open(image_path, 'rb') as f:
                res = requests.post(f"{self.comfy_url}/upload/image", files={'image': f}, data={'overwrite': 'true'})
                comfy_name = res.json().get("name")

            # Mapping Nodi e Fix Tensori
            if "10" in workflow: workflow["10"]["inputs"]["image"] = comfy_name
            if "6" in workflow: workflow["6"]["inputs"]["text"] = video_prompt
            if "8" in workflow: workflow["8"]["inputs"]["latent_image"] = ["12", 2]

            ws = websocket.WebSocket()
            ws_url = self.comfy_url.replace("http://", "ws://").replace("https://", "wss://")
            ws.connect(f"{ws_url}/ws?clientId={self.client_id}")

            return self._execute_workflow(ws, workflow)
        finally:
            # 4. PULIZIA E RIPRISTINO SD
            self._manage_vram("comfy", "free")
            self._manage_vram("sd", "reload")

    def _get_engineered_prompt(self, context: str) -> str:
        sys = "You are an elite AI video prompt engineer for Wan 2.1. Output ONLY English. Focus on subtle motion, locked-off tripod."
        resp = self.llm.generate_response(context, sys, [])
        return resp.get("text", "cinematic realism, subtle motion").strip()

    def _execute_workflow(self, ws, workflow):
        # ... (Mantieni la tua logica di polling e download MP4 esistente) ...
        pass