# file: ui/main_window.py
import sys
from typing import List
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTextEdit, QLineEdit, QPushButton, QLabel, QFrame,
                               QMessageBox, QCheckBox, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer

from core.engine import GameEngine
from config.settings import Settings
from ui.components.startup_dialog import StartupDialog
from ui.components.image_viewer import InteractiveImageViewer


# --- WORKERS (Motore Parallelo) ---
class LLMWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, engine, text, is_intro):
        super().__init__()
        self.engine, self.text, self.is_intro = engine, text, is_intro

    def run(self):
        try:
            data = self.engine.process_turn_llm(self.text, self.is_intro)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))


class ImageWorker(QThread):
    finished = Signal(str)

    def __init__(self, engine, visual_en, tags_en):
        super().__init__()
        self.engine, self.visual_en, self.tags_en = engine, visual_en, tags_en

    def run(self):
        try:
            path = self.engine.process_image_generation(self.visual_en, self.tags_en)
            self.finished.emit(path)
        except:
            self.finished.emit("")


class AudioWorker(QThread):
    def __init__(self, engine, text):
        super().__init__()
        self.engine, self.text = engine, text

    def run(self):
        try:
            self.engine.process_audio(self.text)
        except:
            pass


# --- FINESTRA PRINCIPALE (Layout Classico) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Luna D&D – Master Libero (v2 Parallel)")
        self.resize(1200, 750)

        # Carica Stile "Carta/RPG"
        try:
            with open("ui/styles.qss", "r") as f:
                self.setStyleSheet(f.read())
        except:
            pass

        self.engine = GameEngine()
        self.image_history: List[str] = []
        self.image_index = -1

        self._setup_ui()

        # Avvio ritardato
        QTimer.singleShot(100, self._start_game_sequence)

    def _start_game_sequence(self):
        dialog = StartupDialog(self)
        if dialog.exec():
            choice = dialog.get_selection()
            if choice["mode"] == "load":
                if self.engine.load_game(choice["path"]):
                    self._update_stats()
                    self._append_story("\n--- SESSIONE CARICATA ---\n")
                    # Recupera ultima immagine se possibile (logica base)
                    self.status_lbl.setText("Partita caricata.")
            else:
                self.engine.start_new_game("fantasy_dark", choice["companion"])
                self._handle_player_input(None, is_intro=True)
        else:
            sys.exit()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # === COLONNA SINISTRA (2/5) ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        # Titolo Stato
        lbl_state = QLabel("Stato party")
        lbl_state.setStyleSheet("font-size: 12pt; font-weight: bold;")
        left_layout.addWidget(lbl_state)

        # Box Statistiche
        self.stats_edit = QTextEdit()
        self.stats_edit.setReadOnly(True)
        self.stats_edit.setMinimumHeight(140)
        self.stats_edit.setObjectName("StatsBox")
        left_layout.addWidget(self.stats_edit)

        # Separatore
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        left_layout.addWidget(line)

        # Titolo Scena
        lbl_scene = QLabel("Scena attuale")
        lbl_scene.setStyleSheet("font-size: 12pt; font-weight: bold;")
        left_layout.addWidget(lbl_scene)

        # Immagine (Uso il nuovo viewer ma stilizzato come il vecchio)
        self.img_viewer = InteractiveImageViewer()
        self.img_viewer.image_lbl.setObjectName("ImageLabel")  # Per il CSS nero
        left_layout.addWidget(self.img_viewer, 1)  # Stretch

        # Navigazione Immagini
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("◀")
        self.btn_prev.setFixedWidth(40)
        self.btn_prev.clicked.connect(self._prev_image)
        self.btn_prev.setEnabled(False)

        self.btn_next = QPushButton("▶")
        self.btn_next.setFixedWidth(40)
        self.btn_next.clicked.connect(self._next_image)
        self.btn_next.setEnabled(False)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        left_layout.addLayout(nav_layout)

        # Checkbox Voce
        self.chk_voice = QCheckBox("Voce narrante attiva")
        self.chk_voice.setChecked(True)
        self.chk_voice.setStyleSheet("font-size: 11pt; color: #333;")
        left_layout.addWidget(self.chk_voice)

        # Status Label
        self.status_lbl = QLabel("Pronto.")
        self.status_lbl.setStyleSheet("color: #555; font-style: italic;")
        left_layout.addWidget(self.status_lbl)

        # Pulsanti Save/Load
        sl_layout = QHBoxLayout()
        btn_save = QPushButton("Salva")
        btn_save.clicked.connect(self._on_save)
        btn_load = QPushButton("Carica")
        btn_load.clicked.connect(self._on_load)
        sl_layout.addWidget(btn_save)
        sl_layout.addWidget(btn_load)
        left_layout.addLayout(sl_layout)

        # Bottone Video
        self.btn_video = QPushButton("Genera Video (ComfyUI)")
        self.btn_video.clicked.connect(lambda: QMessageBox.information(self, "Info", "WIP"))
        left_layout.addWidget(self.btn_video)

        main_layout.addLayout(left_layout, 2)

        # === COLONNA DESTRA (3/5) ===
        right_layout = QVBoxLayout()

        # Titolo Storia
        lbl_story = QLabel("Storia")
        lbl_story.setStyleSheet("font-size: 13pt; font-weight: bold; color: #3b2410;")
        right_layout.addWidget(lbl_story)

        # Diario
        self.story_edit = QTextEdit()
        self.story_edit.setReadOnly(True)
        self.story_edit.setObjectName("StoryArea")
        self.story_edit.setPlaceholderText("L'avventura inizia qui...")
        right_layout.addWidget(self.story_edit, 1)

        # Input Area
        input_layout = QHBoxLayout()

        self.chk_dice = QCheckBox("🎲 Tira")
        self.chk_dice.setStyleSheet("font-weight: bold; color: #333;")
        input_layout.addWidget(self.chk_dice)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Scrivi cosa fai...")
        self.input_field.returnPressed.connect(self._send_action)
        input_layout.addWidget(self.input_field)

        self.btn_send = QPushButton("Invia azione")
        self.btn_send.clicked.connect(self._send_action)
        input_layout.addWidget(self.btn_send)

        right_layout.addLayout(input_layout)
        main_layout.addLayout(right_layout, 3)

    # --- LOGICA DI GIOCO ---
    def _send_action(self):
        text = self.input_field.text().strip()
        if not text: return
        self._handle_player_input(text)

    def _handle_player_input(self, text, is_intro=False):
        if not is_intro:
            # Aggiungi eventuale logica dado qui (es. "[DADO: 15] Azione...")
            prefix = ""
            if self.chk_dice.isChecked():
                # Simuliamo un tiro per ora (o integra dice_widget)
                import random
                roll = random.randint(1, 20)
                prefix = f"[D20: {roll}] "
                self.chk_dice.setChecked(False)  # Reset

            full_text = prefix + text
            self._append_story(f"\n> **TU**: {full_text}\n")
            self.input_field.clear()
            text = full_text  # Passiamo il testo col dado all'LLM

        self.input_field.setDisabled(True)
        self.input_field.setPlaceholderText("Luna sta scrivendo...")
        self.status_lbl.setText("Elaborazione neurale...")

        # 1. Avvia LLM
        self.llm_worker = LLMWorker(self.engine, text, is_intro)
        self.llm_worker.finished.connect(self._on_llm_finished)
        self.llm_worker.error.connect(lambda e: self.status_lbl.setText(f"Errore: {e}"))
        self.llm_worker.start()

    @Slot(dict)
    def _on_llm_finished(self, data):
        text = data.get("text", "")
        visual_en = data.get("visual_en", "")
        tags_en = data.get("tags_en", [])
        name = self.engine.state_manager.current_state["game"]["companion_name"]

        # Mostra Testo
        self._append_story(f"\n**{name.upper()}**: {text}\n")
        self._update_stats()

        # Sblocca UI
        self.input_field.setDisabled(False)
        self.input_field.setPlaceholderText("Scrivi cosa fai...")
        self.input_field.setFocus()
        self.status_lbl.setText("In attesa...")

        # Audio & Video Paralleli
        if self.chk_voice.isChecked():
            self.audio_worker = AudioWorker(self.engine, text)
            self.audio_worker.start()

        self.img_viewer.image_lbl.setText("Generazione immagine...")
        self.img_worker = ImageWorker(self.engine, visual_en, tags_en)
        self.img_worker.finished.connect(self._on_image_finished)
        self.img_worker.start()

    @Slot(str)
    def _on_image_finished(self, path):
        if path:
            self._register_image(path)
            self.status_lbl.setText("Immagine aggiornata.")
        else:
            self.img_viewer.image_lbl.setText("Nessuna immagine.")

    def _register_image(self, path):
        """Gestione cronologia immagini"""
        self.image_history.append(path)
        self.image_index = len(self.image_history) - 1
        self.img_viewer.update_image(path)
        self._update_nav_buttons()

    def _update_nav_buttons(self):
        self.btn_prev.setEnabled(self.image_index > 0)
        self.btn_next.setEnabled(self.image_index < len(self.image_history) - 1)

    def _prev_image(self):
        if self.image_index > 0:
            self.image_index -= 1
            self.img_viewer.update_image(self.image_history[self.image_index])
            self._update_nav_buttons()

    def _next_image(self):
        if self.image_index < len(self.image_history) - 1:
            self.image_index += 1
            self.img_viewer.update_image(self.image_history[self.image_index])
            self._update_nav_buttons()

    def _update_stats(self):
        s = self.engine.state_manager.current_state.get("game", {})
        m = self.engine.state_manager.current_state.get("meta", {})
        txt = (f"LUOGO: {s.get('location')}\n"
               f"OUTFIT: {s.get('current_outfit')}\n"
               f"TURNO: {m.get('turn_count')}\n"
               f"INV: {', '.join(s.get('inventory', []))}")
        self.stats_edit.setPlainText(txt)

    def _append_story(self, text):
        self.story_edit.append(text)
        sb = self.story_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_save(self):
        if self.engine.state_manager.save_game("manual_save.json"):
            self.status_lbl.setText("Partita salvata.")

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Carica", "storage/saves", "JSON (*.json)")
        if path:
            if self.engine.load_game(path):
                self._update_stats()
                self.status_lbl.setText("Caricato.")