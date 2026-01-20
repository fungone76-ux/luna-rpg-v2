# file: media/llm_client.py
import os
import json
import re
import google.generativeai as genai
from typing import List, Dict, Any


class LLMClient:
    def __init__(self):
        # Recupera la chiave
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("⚠️ ATTENZIONE: GEMINI_API_KEY non trovata nel file .env")
            self.model = None
            return

        # Configurazione Base
        genai.configure(api_key=api_key)
        self.model = None

        # LISTA MODELLI AGGIORNATA
        # Priorità assoluta al modello che hai richiesto
        candidates = [
            "gemini-3-pro-preview",  # <--- ECCOLO! (Il più potente)
            "gemini-3-flash-preview",  # Alternativa veloce se Pro è occupato
            "gemini-2.5-pro",  # Fallback stabile
            "gemini-1.5-pro",  # Vecchia gloria
        ]

        print("🤖 [LLM Init] Connessione a Gemini 3...")

        for model_name in candidates:
            try:
                # Testiamo se il modello è accessibile con la tua chiave
                test_model = genai.GenerativeModel(model_name)
                # Chiamata dummy per verificare l'accesso
                test_model.generate_content("test")

                # Se funziona, lo assegniamo!
                self.model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config={
                        "temperature": 0.9,  # Creatività alta
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 1024,
                    }
                )
                print(f"✅ Modello LLM attivato: {model_name}")
                break
            except Exception as e:
                # Se fallisce, proviamo il prossimo
                # print(f"   (Skip {model_name}: non disponibile)")
                continue

        if not self.model:
            print("❌ ERRORE CRITICO: Nessun modello Gemini funzionante trovato.")
            print("   Verifica che la tua API KEY supporti Gemini 3.")

    def generate_response(
            self,
            user_input: str,
            system_instruction: str,
            history: List[Dict],
            summaries: List[str]
    ) -> Dict[str, Any]:
        """Invia il contesto a Gemini e parsa la risposta."""
        if not self.model:
            return {"text": "Errore: Nessun modello AI connesso.", "visual_en": "", "tags_en": []}

        # 1. Costruiamo il Prompt Unico
        full_prompt_parts = []

        # Istruzioni Sistema
        full_prompt_parts.append(system_instruction)

        # Memoria a Lungo Termine
        if summaries:
            full_prompt_parts.append("\nRIASSUNTO EVENTI PASSATI:")
            for s in summaries:
                full_prompt_parts.append(f"- {s}")

        # Storia Recente
        full_prompt_parts.append("\nSTORIA RECENTE:")
        for msg in history:
            role = "User" if msg['role'] == 'user' else "Master"
            full_prompt_parts.append(f"{role}: {msg['content']}")

        # Input Attuale
        full_prompt_parts.append(f"\nUser: {user_input}")

        # 2. Chiamata a Gemini
        try:
            response = self.model.generate_content(full_prompt_parts)
            raw_text = response.text
            return self._parse_output(raw_text)

        except Exception as e:
            print(f"❌ Errore Generazione Gemini: {e}")
            return {
                "text": "La connessione neurale è instabile...",
                "visual_en": "",
                "tags_en": []
            }

    def summarize_history(self, messages: List[Dict]) -> str:
        """Chiede a Gemini di riassumere i messaggi."""
        if not self.model: return "Dati persi."

        prompt = "Riassumi in 2 frasi concise (nomi, luoghi, azioni chiave):\n"
        for m in messages:
            prompt += f"{m['role']}: {m['content']}\n"

        try:
            resp = self.model.generate_content(prompt)
            return resp.text.strip()
        except:
            return "Riassunto non disponibile."

    def _parse_output(self, raw_text: str) -> Dict[str, Any]:
        """Estrae JSON e testo pulito."""
        result = {
            "text": raw_text,
            "visual_en": "",
            "tags_en": [],
            "updates": {}
        }

        # Regex per trovare ```json ... ```
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", raw_text, re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            result["text"] = raw_text.replace(json_match.group(0), "").strip()

            try:
                data = json.loads(json_str)
                result["visual_en"] = data.get("visual_en", "")
                result["tags_en"] = data.get("tags_en", [])
                result["updates"] = data.get("updates", {})
            except json.JSONDecodeError:
                print("⚠️ Errore parsing JSON da Gemini")

        return result