# file: media/llm_client.py
import os
import json
import re
from typing import List, Dict, Any

# --- LIBRERIE NECESSARIE ---
# 1. pip install google-genai
# 2. pip install python-dotenv
from google import genai
from google.genai import types
from dotenv import load_dotenv

# --- CARICAMENTO .ENV ---
# Questo comando cerca il file .env e carica le variabili
load_dotenv()

# Configurazione di emergenza (lascia vuoto se usi .env)
HARDCODED_KEY = "INCOLLA_QUI_SOLO_SE_ENV_NON_VA"


class LLMClient:
    def __init__(self):
        # 1. Recupera la chiave (Ora load_dotenv() ha caricato il file .env)
        self.api_key = os.getenv("GEMINI_API_KEY")

        # Fallback se .env fallisce
        if not self.api_key:
            if "INCOLLA_QUI" not in HARDCODED_KEY:
                self.api_key = HARDCODED_KEY
                print("⚠️ .env non letto correttamente: Utilizzo chiave hardcoded.")
            else:
                print("❌ ERRORE CRITICO: GEMINI_API_KEY non trovata (né in .env né nel codice).")
                self.client = None
                self.model_id = None
                return

        # 2. Inizializzazione Client V2
        try:
            self.client = genai.Client(api_key=self.api_key)
        except Exception as e:
            print(f"❌ Errore Inizializzazione Client: {e}")
            self.client = None
            return

        self.model_id = None

        # LISTA MODELLI (Priorità alla stabilità)
        candidates = [
            "gemini-3.0-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ]

        print("🤖 [LLM Init] Connessione a Gemini (SDK Google GenAI V2)...")

        for model_name in candidates:
            try:
                # Test di connessione leggero
                self.client.models.generate_content(
                    model=model_name,
                    contents="Test connection"
                )
                self.model_id = model_name
                print(f"✅ Modello LLM attivato: {model_name}")
                break
            except Exception as e:
                # print(f"   (Skip {model_name}: {e})") # Decommenta per debug
                pass

        if not self.model_id:
            print("❌ ERRORE: Nessun modello Gemini funzionante trovato o Chiave non valida.")

    def generate_response(
            self,
            user_input: str,
            system_instruction: str,
            history: List[Dict],
            summaries: List[str]
    ) -> Dict[str, Any]:
        """Invia il contesto a Gemini e parsa la risposta."""
        if not self.client or not self.model_id:
            return {"text": "Errore: Nessun modello AI connesso.", "visual_en": "", "tags_en": []}

        # 3. Costruzione Contenuti
        contents = []

        # A. Inseriamo i riassunti
        if summaries:
            summary_text = "RIASSUNTO EVENTI PASSATI:\n" + "\n".join(f"- {s}" for s in summaries)
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=summary_text)]))
            contents.append(
                types.Content(role="model", parts=[types.Part.from_text(text="Ricevuto.")]))

        # B. Storia Recente
        for msg in history:
            role = "user" if msg['role'] == 'user' else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])]))

        # C. Input Attuale
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))

        # 4. Configurazione
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.9,
            top_p=0.95,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="text/plain"
        )

        # 5. Chiamata API
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
        if not self.client: return "Dati persi."
        prompt_text = "Riassumi in 2 frasi concise:\n"
        for m in messages:
            prompt_text += f"{m['role']}: {m['content']}\n"
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt_text
            )
            return response.text.strip()
        except:
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