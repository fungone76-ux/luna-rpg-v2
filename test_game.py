# file: test_game.py
import os
import sys

# Aggiunge la root al path per trovare i moduli
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.engine import GameEngine


def run_test():
    print("🔧 --- INIZIO TEST MOTORE LUNA-RPG v2 ---")

    # 1. Inizializzazione
    print("\n[1] Inizializzazione Engine...")
    try:
        engine = GameEngine()
        print("✅ Engine avviato.")
    except Exception as e:
        print(f"❌ CRITICAL: Errore avvio Engine: {e}")
        return

    # 2. Caricamento Mondo
    print("\n[2] Avvio Nuova Partita (Fantasy Dark)...")
    try:
        # Carica il mondo 'fantasy_dark' con companion 'Luna'
        initial_response = engine.start_new_game("fantasy_dark", "Luna")

        print(f"📝 TESTO INTRO: {initial_response['text'][:100]}...")
        # print(f"🎨 VISUAL DEBUG: {initial_response['visual_debug']}")
    except Exception as e:
        print(f"❌ CRITICAL: Errore avvio partita: {e}")
        return

    # 3. Turno di Gioco (Simulazione Input Utente)
    user_input = "Mi guardo attorno e cerco una via di fuga. 'Luna, vedi qualcosa?'"
    print(f"\n[3] Invio Input Utente: \"{user_input}\"")

    try:
        response = engine.generate_turn_response(user_input)

        print("\n--- RISPOSTA DAL MOTORE ---")
        print(f"🗣️ TESTO: {response['text']}")
        # print(f"👁️ SCENA (Prompt): {response['visual_debug']}")

        if response['image']:
            print(f"🖼️ IMMAGINE: Generata in {response['image']}")
        else:
            print("🖼️ IMMAGINE: Non generata (SD Offline o Errore)")

    except Exception as e:
        print(f"❌ CRITICAL: Errore durante il turno: {e}")

    print("\n🔧 --- TEST COMPLETATO ---")


if __name__ == "__main__":
    run_test()