# file: media/llm_client.py
import os
import json
import re
from typing import List, Dict, Any

# --- LIBRERIE NECESSARIE ---
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CARICAMENTO .ENV ---
load_dotenv()

# Configurazione di emergenza
HARDCODED_KEY = "INCOLLA_QUI_SOLO_SE_ENV_NON_VA"


class LLMClient:
    def __init__(self):
        # 1. Recupera la chiave
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            if "INCOLLA_QUI" not in HARDCODED_KEY:
                self.api_key = HARDCODED_KEY
                print("⚠️ .env non letto correttamente: Utilizzo chiave hardcoded.")
            else:
                print("❌ ERRORE CRITICO: GEMINI_API_KEY non trovata.")
                self.client = None
                self.model_id = None
                return

        # 2. Inizializzazione Client
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            print(f"❌ Errore Inizializzazione Client: {e}")
            self.client = None
            return

        self.model_id = None

        # LISTA MODELLI (Priorità: Potenza -> Velocità)
        candidates = [
            "gemini-2.0-flash-exp",  # Se hai accesso alla 2.0 Flash
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]

        print("🤖 [LLM Init] Connessione a Gemini...")

        for model_name in candidates:
            try:
                self.client.models.generate_content(
                    model=model_name,
                    contents="Test connection"
                )
                self.model_id = model_name
                print(f"✅ Modello LLM attivato: {model_name}")
                break
            except Exception as e:
                pass

        if not self.model_id:
            print("❌ ERRORE: Nessun modello Gemini funzionante trovato.")

    def generate_response(
            self,
            user_input: str,
            system_instruction: str,
            history: List[Dict],
            memory_context: str = ""  # <--- NUOVO PARAMETRO per la Memoria
    ) -> Dict[str, Any]:
        """Invia il contesto a Gemini e parsa la risposta."""
        if not self.client or not self.model_id:
            return {"text": "Errore: Nessun modello AI connesso.", "visual_en": "", "tags_en": []}

        contents = []

        # A. Iniezione Memoria (Fatti + Riassunti precedenti)
        if memory_context:
            # Lo passiamo come un messaggio "di sistema" simulato o user pre-prompt
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"SYSTEM MEMORY LOG:\n{memory_context}")]
            ))
            contents.append(types.Content(
                role="model",
                parts=[types.Part.from_text(text="Memory loaded.")]
            ))

        # B. Storia Recente
        for msg in history:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])]))

        # C. Input Attuale
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        # Configurazione
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.9,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="text/plain"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config=config
            )

            raw_text = response.text
            if not raw_text:
                raise ValueError("Risposta vuota dal modello")

            return self._parse_output(raw_text)

        except Exception as e:
            print(f"❌ Errore Generazione Gemini: {e}")
            return {
                "text": "La connessione neurale è instabile... (Errore API)",
                "visual_en": "",
                "tags_en": []
            }

    def summarize_history(self, messages: List[Dict]) -> str:
        """
        Crea un riassunto intelligente rimuovendo i JSON tecnici.
        """
        if not self.client: return "Dati persi."

        txt_block = ""
        for m in messages:
            role = "Player" if m['role'] == 'user' else "Game Master"
            content = m['content']

            # PULIZIA: Rimuoviamo i blocchi JSON dalle risposte dell'AI
            # (Non serve riassumere i dati tecnici, solo la storia)
            if role == "Game Master":
                content = re.sub(r'```json.*?```', '', content, flags=re.DOTALL).strip()

            txt_block += f"{role}: {content}\n"

        # Prompt specifico per la compressione
        prompt = (
            "Act as a Game Master's Scribe. Compress the following RPG session logs into a concise memory entry.\n"
            "RULES:\n"
            "1. Keep it under 3 sentences.\n"
            "2. Retain ONLY: Key decisions, new facts learned, and important status changes.\n"
            "3. Discard: Small talk, visual descriptions, and technical JSON data.\n"
            "4. Language: Italian.\n\n"
            f"LOGS TO COMPRESS:\n{txt_block}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Summary Error: {e}")
            return "Riassunto non disponibile."

    def _parse_output(self, raw_text: str) -> Dict[str, Any]:
        result = {
            "text": raw_text,
            "visual_en": "",
            "tags_en": [],
            "updates": {}
        }

        # Cerca JSON
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{.*\})", raw_text, re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            clean_text = raw_text.replace(json_match.group(0), "").strip()
            clean_text = clean_text.replace("```json", "").replace("```", "").strip()
            result["text"] = clean_text

            try:
                data = json.loads(json_str)
                result["visual_en"] = data.get("visual_en", "")
                result["tags_en"] = data.get("tags_en", [])
                result["updates"] = data.get("updates", {})
            except json.JSONDecodeError:
                print("⚠️ Errore parsing JSON da Gemini")

        return result