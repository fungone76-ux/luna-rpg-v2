# file: ui/components/startup_dialog.py
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget,
                               QPushButton, QHBoxLayout, QTabWidget, QWidget,
                               QCheckBox, QLineEdit, QGroupBox, QFormLayout, QComboBox)
from core.world_loader import WorldLoader
from config.settings import Settings


class StartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LUNA-RPG - Session Setup")
        self.resize(600, 550)
        self.loader = WorldLoader()
        self.settings = Settings.get_instance()

        self.available_worlds = []
        self.selected_world_id = "school_life"  # Fallback
        self.mode = "new"
        self.save_path = ""

        self._setup_ui()
        self._load_worlds()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # TAB 1: GAME
        tabs = QTabWidget()
        tab_game = QWidget()
        game_layout = QVBoxLayout(tab_game)

        # 1. WORLD SELECTOR (NUOVO!)
        lbl_world = QLabel("Select World / Scenario:")
        lbl_world.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        game_layout.addWidget(lbl_world)

        self.combo_worlds = QComboBox()
        self.combo_worlds.currentIndexChanged.connect(self._on_world_changed)
        game_layout.addWidget(self.combo_worlds)

        # 2. COMPANION SELECTOR
        lbl_char = QLabel("Choose your Partner:")
        lbl_char.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        game_layout.addWidget(lbl_char)

        self.char_list = QListWidget()
        game_layout.addWidget(self.char_list)

        # 3. LOAD BUTTON
        btn_load = QPushButton("📂 Load Save Game")
        btn_load.clicked.connect(self._on_load_click)
        game_layout.addWidget(btn_load)

        tabs.addTab(tab_game, "🎮 Game Setup")

        # TAB 2: GPU / RUNPOD
        tab_gpu = QWidget()
        gpu_layout = QVBoxLayout(tab_gpu)

        gpu_group = QGroupBox("Image Generation Backend (SD)")
        form_layout = QFormLayout()

        self.chk_runpod = QCheckBox("Use RunPod (Cloud GPU)")
        self.chk_runpod.setChecked(self.settings.config.get("runpod_active", False))
        self.chk_runpod.toggled.connect(self._toggle_runpod_input)

        self.txt_runpod_url = QLineEdit()
        self.txt_runpod_url.setText(self.settings.config.get("runpod_url", ""))
        self.txt_runpod_url.setPlaceholderText("Ex: https://abc-123-7860.proxy.runpod.net")

        form_layout.addRow(self.chk_runpod)
        form_layout.addRow("RunPod URL:", self.txt_runpod_url)

        gpu_group.setLayout(form_layout)
        gpu_layout.addWidget(gpu_group)

        lbl_info = QLabel("If disabled, uses: http://127.0.0.1:7860 (Local)")
        lbl_info.setStyleSheet("color: gray; font-size: 11px;")
        gpu_layout.addWidget(lbl_info)
        gpu_layout.addStretch()

        tabs.addTab(tab_gpu, "🚀 GPU / Settings")

        layout.addWidget(tabs)

        # START BUTTON
        btn_box = QHBoxLayout()
        btn_start = QPushButton("START ADVENTURE")
        btn_start.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 12px; font-weight: bold; font-size: 14px;")
        btn_start.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(btn_start)

        layout.addLayout(btn_box)

        self._toggle_runpod_input()

    def _load_worlds(self):
        """Carica la lista dei file YAML dalla cartella worlds/"""
        self.available_worlds = self.loader.list_available_worlds()

        self.combo_worlds.clear()
        for w in self.available_worlds:
            # Mostra "Nome (ID)" nel menu
            display_text = f"{w['name']} ({w['genre']})"
            self.combo_worlds.addItem(display_text, w['id'])

        # Seleziona il primo o School Life se c'è
        index = self.combo_worlds.findData("school_life")
        if index >= 0:
            self.combo_worlds.setCurrentIndex(index)

    def _on_world_changed(self):
        """Quando cambi mondo, aggiorna la lista delle ragazze."""
        if self.combo_worlds.currentIndex() == -1: return

        world_id = self.combo_worlds.currentData()
        self.selected_world_id = world_id

        # Carica il yaml al volo per leggere i nomi
        world_data = self.loader.load_world_data(f"{world_id}.yaml")
        if world_data:
            companions = list(world_data.get("companions", {}).keys())
            self.char_list.clear()
            self.char_list.addItems(companions)
            self.char_list.setCurrentRow(0)

    def _toggle_runpod_input(self):
        enabled = self.chk_runpod.isChecked()
        self.txt_runpod_url.setEnabled(enabled)

    def _on_load_click(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Load Game", "storage/saves", "JSON (*.json)")
        if path:
            self.mode = "load"
            self.save_path = path
            self.accept()

    def get_selection(self):
        # Salva config
        self.settings.config["runpod_active"] = self.chk_runpod.isChecked()
        self.settings.config["runpod_url"] = self.txt_runpod_url.text().strip()
        self.settings.save()

        # Ritorna selezione
        companion = "Luna"
        if self.char_list.currentItem():
            companion = self.char_list.currentItem().text()

        return {
            "mode": self.mode,
            "path": self.save_path,
            "world_id": self.selected_world_id,  # Ora è dinamico!
            "companion": companion
        }