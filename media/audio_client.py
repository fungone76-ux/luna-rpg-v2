# file: media/audio_client.py
import os
import io
import pygame
import time
from google.cloud import texttospeech
from google.oauth2 import service_account

# Mappa delle voci (Google Cloud TTS)
VOICE_MAP = {
    "Luna": {"name": "en-US-Journey-F", "gender": texttospeech.SsmlVoiceGender.FEMALE},
    "Stella": {"name": "en-US-Standard-A", "gender": texttospeech.SsmlVoiceGender.FEMALE},
    "Maria": {"name": "en-GB-Neural2-A", "gender": texttospeech.SsmlVoiceGender.FEMALE},
    "Narrator": {"name": "it-IT-Neural2-A", "gender": texttospeech.SsmlVoiceGender.FEMALE}
}


class AudioClient:
    def __init__(self):
        self.enabled = False
        self.client = None

        # 1. Carica Credenziali (File JSON obbligatorio per l'autenticazione)
        cred_path = "google_credentials.json"

        if os.path.exists(cred_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(cred_path)
                self.client = texttospeech.TextToSpeechClient(credentials=credentials)

                # Init Pygame Mixer
                pygame.mixer.init()
                self.enabled = True
                print("✅ Audio Client: Google TTS Connesso (Modalità RAM).")
            except Exception as e:
                print(f"⚠️ Errore Audio: Impossibile caricare credenziali ({e})")
        else:
            print(f"⚠️ Audio Disabilitato: Manca '{cred_path}' nella cartella.")

    def play_voice(self, text: str, character_name: str = "Narrator"):
        """Genera audio, lo riproduce dalla RAM e lo scarta."""
        if not self.enabled or not text:
            return

        # 1. Configura la richiesta
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_config = VOICE_MAP.get(character_name, VOICE_MAP["Narrator"])
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["name"][:5],
            name=voice_config["name"],
            ssml_gender=voice_config["gender"]
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0,
            pitch=0.0
        )

        try:
            # 2. Chiama Google (Scarica i byte audio)
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # 3. Stream dalla RAM (Nessun salvataggio su disco)
            # Creiamo un file 'virtuale' in memoria
            audio_stream = io.BytesIO(response.audio_content)

            self._play_stream(audio_stream)

        except Exception as e:
            print(f"❌ Errore Google TTS: {e}")

    def _play_stream(self, audio_stream):
        """Riproduce direttamente dall'oggetto in memoria."""
        try:
            pygame.mixer.music.load(audio_stream)
            pygame.mixer.music.play()

            # Blocca il flusso finché non finisce di parlare
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.unload()

        except Exception as e:
            print(f"❌ Errore Playback RAM: {e}")

    def stop_all(self):
        if self.enabled:
            pygame.mixer.music.stop()