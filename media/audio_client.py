# file: media/audio_client.py
import os
import time
import tempfile
import pygame
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

        # 1. Carica Credenziali
        cred_path = "google_credentials.json"

        if os.path.exists(cred_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(cred_path)
                self.client = texttospeech.TextToSpeechClient(credentials=credentials)

                # Init Pygame Mixer con configurazione sicura
                # Buffer più alto riduce il rischio di crash
                pygame.mixer.init(frequency=24000, buffer=4096)
                self.enabled = True
                print("✅ Audio Client: Google TTS Connesso (Modalità File Temp).")
            except Exception as e:
                print(f"⚠️ Errore Audio: Impossibile caricare credenziali ({e})")
        else:
            print(f"⚠️ Audio Disabilitato: Manca '{cred_path}' nella cartella.")

    def play_voice(self, text: str, character_name: str = "Narrator"):
        """Genera audio, lo salva su temp e lo riproduce."""
        if not self.enabled or not text:
            return

        # Configura la richiesta
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_config = VOICE_MAP.get(character_name, VOICE_MAP["Narrator"])
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config["name"][:5],
            name=voice_config["name"],
            ssml_gender=voice_config["gender"]
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=1.0
        )

        try:
            # Chiama Google
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            # SALVATAGGIO SICURO SU FILE TEMPORANEO
            # Pygame è molto più stabile leggendo da disco che da RAM
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_filename = fp.name
                fp.write(response.audio_content)

            self._play_file(temp_filename)

        except Exception as e:
            print(f"❌ Errore Google TTS: {e}")

    def _play_file(self, filename):
        """Riproduce da file e poi pulisce."""
        try:
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

            # Loop di attesa (Thread Safe)
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)

            pygame.mixer.music.unload()

        except Exception as e:
            print(f"❌ Errore Playback: {e}")
        finally:
            # Pulizia file temporaneo
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except:
                pass

    def stop_all(self):
        if self.enabled:
            pygame.mixer.music.stop()