# file: ui/components/startup_dialog.py
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QListWidget,
                               QPushButton, QHBoxLayout, QTabWidget, QWidget,
                               QCheckBox, QLineEdit, QGroupBox, QFormLayout)
from core.world_loader import WorldLoader
from config.settings import Settings


class StartupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LUNA-RPG - Configurazione Sessione")
        self.resize(600, 500)
        self.loader = WorldLoader()
        self.settings = Settings.get_instance()

        self.selected_world = "fantasy_dark"  # Default hardcoded per ora o dinamico
        self.selected_companion = "Luna"
        self.mode = "new"
        self.save_path = ""

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # TAB 1: GIOCO
        tabs = QTabWidget()
        tab_game = QWidget()
        game_layout = QVBoxLayout(tab_game)

        lbl = QLabel("Scegli la tua Compagna:")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        game_layout.addWidget(lbl)

        self.char_list = QListWidget()
        # Carica le compagne dal mondo (mockup rapido, idealmente legge YAML)
        companions = ["Luna", "Stella", "Maria"]
        self.char_list.addItems(companions)
        self.char_list.setCurrentRow(0)
        game_layout.addWidget(self.char_list)

        btn_load = QPushButton("📂 Carica Salvataggio")
        btn_load.clicked.connect(self._on_load_click)
        game_layout.addWidget(btn_load)

        tabs.addTab(tab_game, "🎮 Partita")

        # TAB 2: GPU / RUNPOD (NUOVO)
        tab_gpu = QWidget()
        gpu_layout = QVBoxLayout(tab_gpu)

        gpu_group = QGroupBox("Backend Generazione Immagini (Stable Diffusion)")
        form_layout = QFormLayout()

        self.chk_runpod = QCheckBox("Usa RunPod (Cloud GPU)")
        self.chk_runpod.setChecked(self.settings.config["runpod_active"])
        self.chk_runpod.toggled.connect(self._toggle_runpod_input)

        self.txt_runpod_url = QLineEdit()
        self.txt_runpod_url.setText(self.settings.config["runpod_url"])
        self.txt_runpod_url.setPlaceholderText("Es: https://abc-123-7860.proxy.runpod.net")

        form_layout.addRow(self.chk_runpod)
        form_layout.addRow("RunPod URL:", self.txt_runpod_url)

        gpu_group.setLayout(form_layout)
        gpu_layout.addWidget(gpu_group)

        lbl_info = QLabel("Se disattivato, userà: http://127.0.0.1:7860 (Locale)")
        lbl_info.setStyleSheet("color: gray; font-size: 11px;")
        gpu_layout.addWidget(lbl_info)
        gpu_layout.addStretch()

        tabs.addTab(tab_gpu, "🚀 GPU / RunPod")

        layout.addWidget(tabs)

        # Pulsanti OK/Cancel
        btn_box = QHBoxLayout()
        btn_start = QPushButton("INIZIA AVVENTURA")
        btn_start.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        btn_start.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(btn_start)

        layout.addLayout(btn_box)

        self._toggle_runpod_input()

    def _toggle_runpod_input(self):
        enabled = self.chk_runpod.isChecked()
        self.txt_runpod_url.setEnabled(enabled)

    def _on_load_click(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Carica", "storage/saves", "JSON (*.json)")
        if path:
            self.mode = "load"
            self.save_path = path
            self.accept()

    def get_selection(self):
        # Salva le impostazioni prima di uscire
        self.settings.config["runpod_active"] = self.chk_runpod.isChecked()
        self.settings.config["runpod_url"] = self.txt_runpod_url.text().strip()
        self.settings.save()

        return {
            "mode": self.mode,
            "path": self.save_path,
            "companion": self.char_list.currentItem().text()
        }