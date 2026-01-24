# file: ui/main_window.py
import sys
import random
from typing import List
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QTextEdit, QLineEdit, QPushButton, QLabel, QFrame,
                               QMessageBox, QCheckBox, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer

from core.engine import GameEngine
from config.settings import Settings
from ui.components.startup_dialog import StartupDialog
from ui.components.image_viewer import InteractiveImageViewer
from ui.components.status_panel import StatusPanel


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Luna RPG v2 - Universal")
        self.resize(1200, 780)

        try:
            with open("ui/styles.qss", "r") as f:
                self.setStyleSheet(f.read())
        except:
            pass

        self.engine = GameEngine()
        self.image_history: List[str] = []
        self.image_index = -1

        self._setup_ui()
        QTimer.singleShot(100, self._start_game_sequence)

    def _start_game_sequence(self):
        dialog = StartupDialog(self)
        if dialog.exec():
            choice = dialog.get_selection()
            if choice["mode"] == "load":
                if self.engine.load_game(choice["path"]):
                    self._update_stats()
                    self._append_story("\n--- SESSION LOADED ---\n")
                    self.status_lbl.setText("Game Loaded.")
            else:
                selected_world = choice.get("world_id", "school_life")
                companion = choice.get("companion", "Luna")

                print(f"🚀 Starting World: {selected_world} with {companion}")

                self.engine.start_new_game(selected_world, companion)
                self._handle_player_input(None, is_intro=True)
        else:
            sys.exit()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # === LEFT COLUMN ===
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        self.status_panel = StatusPanel()
        left_layout.addWidget(self.status_panel)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        left_layout.addWidget(line)

        lbl_scene = QLabel("Visual Scene")
        lbl_scene.setStyleSheet("font-size: 12pt; font-weight: bold;")
        left_layout.addWidget(lbl_scene)

        self.img_viewer = InteractiveImageViewer()
        self.img_viewer.image_lbl.setObjectName("ImageLabel")
        left_layout.addWidget(self.img_viewer, 1)

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

        self.chk_voice = QCheckBox("Voice Narrator")
        self.chk_voice.setChecked(True)
        left_layout.addWidget(self.chk_voice)

        self.status_lbl = QLabel("Ready.")
        self.status_lbl.setStyleSheet("color: #555; font-style: italic;")
        left_layout.addWidget(self.status_lbl)

        sl_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._on_save)
        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self._on_load)
        sl_layout.addWidget(btn_save)
        sl_layout.addWidget(btn_load)
        left_layout.addLayout(sl_layout)

        main_layout.addLayout(left_layout, 2)

        # === RIGHT COLUMN ===
        right_layout = QVBoxLayout()

        lbl_story = QLabel("Story Log")
        lbl_story.setStyleSheet("font-size: 13pt; font-weight: bold; color: #3b2410;")
        right_layout.addWidget(lbl_story)

        self.story_edit = QTextEdit()
        self.story_edit.setReadOnly(True)
        self.story_edit.setObjectName("StoryArea")
        right_layout.addWidget(self.story_edit, 1)

        input_layout = QHBoxLayout()

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("What do you do?")
        self.input_field.returnPressed.connect(self._send_action)
        input_layout.addWidget(self.input_field)

        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self._send_action)
        input_layout.addWidget(self.btn_send)

        right_layout.addLayout(input_layout)
        main_layout.addLayout(right_layout, 3)

    def _send_action(self):
        text = self.input_field.text().strip()
        if not text: return
        self._handle_player_input(text)

    def _handle_player_input(self, text, is_intro=False):
        if not is_intro:
            self._append_story(f"> **YOU**: {text}\n")
            self.input_field.clear()

        self.input_field.setDisabled(True)
        self.input_field.setPlaceholderText("...")
        self.status_lbl.setText("Thinking...")

        self.llm_worker = LLMWorker(self.engine, text, is_intro)
        self.llm_worker.finished.connect(self._on_llm_finished)
        self.llm_worker.error.connect(lambda e: self.status_lbl.setText(f"Err: {e}"))
        self.llm_worker.start()

    @Slot(dict)
    def _on_llm_finished(self, data):
        text = data.get("text", "")
        visual_en = data.get("visual_en", "")
        tags_en = data.get("tags_en", [])

        # --- SICUREZZA API: Intercettiamo l'errore prima della generazione ---
        error_signature = "La connessione neurale è instabile... (Errore API)"
        if error_signature in text:
            # 1. Stampa errore nel log come SYSTEM (non come Luna)
            self._append_story(f"\n**SYSTEM**: ⚠️ {text}\n")
            self.status_lbl.setText("API Error - Connection Failed.")

            # 2. Riabilita Input per permettere di riprovare
            self.input_field.setDisabled(False)
            self.input_field.setPlaceholderText("Try again or check API Key...")
            self.input_field.setFocus()

            # 3. INTERROMPE l'esecuzione: niente Audio, niente Immagini
            self.img_viewer.image_lbl.setText("Generation Aborted (API Error).")
            return
        # ---------------------------------------------------------------------

        name = self.engine.state_manager.current_state["game"]["companion_name"]
        self._append_story(f"\n**{name.upper()}**: {text}\n")

        self._update_stats()

        self.input_field.setDisabled(False)
        self.input_field.setPlaceholderText("What do you do?")
        self.input_field.setFocus()
        self.status_lbl.setText("Waiting...")

        if self.chk_voice.isChecked():
            self.audio_worker = AudioWorker(self.engine, text)
            self.audio_worker.start()

        self.img_viewer.image_lbl.setText("Generating Image...")
        self.img_worker = ImageWorker(self.engine, visual_en, tags_en)
        self.img_worker.finished.connect(self._on_image_finished)
        self.img_worker.start()

    @Slot(str)
    def _on_image_finished(self, path):
        if path:
            self._register_image(path)
            self.status_lbl.setText("Image Ready.")
        else:
            self.img_viewer.image_lbl.setText("Image Error.")

    def _register_image(self, path):
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
        state = self.engine.state_manager.current_state
        self.status_panel.update_status(state)

    def _append_story(self, text):
        self.story_edit.append(text)
        sb = self.story_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_save(self):
        if self.engine.state_manager.save_game("manual_save.json"):
            self.status_lbl.setText("Saved.")

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Game", "storage/saves", "JSON (*.json)")
        if path:
            if self.engine.load_game(path):
                self._update_stats()
                self.status_lbl.setText("Loaded.")