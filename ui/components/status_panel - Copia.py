# file: ui/components/status_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QListWidget, QScrollArea
from PySide6.QtCore import Qt


class StatusPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)

        # 1. INFO GENERALI (Ora include Tempo, Luogo, Outfit)
        self.info_group = QGroupBox("Current Status")
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        self.lbl_time = QLabel("⌚ Time: Morning")
        self.lbl_location = QLabel("📍 Location: -")
        self.lbl_outfit = QLabel("👗 Outfit: -")
        self.lbl_turn = QLabel("⏳ Turn: 1")

        # Stile per renderli più leggibili
        self.lbl_time.setStyleSheet("font-weight: bold; color: #2c3e50;")

        info_layout.addWidget(self.lbl_time)
        info_layout.addWidget(self.lbl_location)
        info_layout.addWidget(self.lbl_outfit)
        info_layout.addWidget(self.lbl_turn)

        self.info_group.setLayout(info_layout)
        self.layout.addWidget(self.info_group)

        # 2. RELAZIONI (Affinità)
        self.affinity_group = QGroupBox("Relationships")
        aff_layout = QVBoxLayout()

        # Usiamo un'etichetta con word-wrap per evitare che i nomi vengano tagliati
        self.lbl_affinity = QLabel("None")
        self.lbl_affinity.setAlignment(Qt.AlignTop)
        self.lbl_affinity.setWordWrap(True)

        aff_layout.addWidget(self.lbl_affinity)
        self.affinity_group.setLayout(aff_layout)
        self.layout.addWidget(self.affinity_group, stretch=1)  # Stretch per dare spazio a Maria

        # 3. INVENTARIO
        self.inv_group = QGroupBox("Inventory")
        inv_layout = QVBoxLayout()
        self.inv_list = QListWidget()
        self.inv_list.setMaximumHeight(100)  # Limitiamo l'altezza per non rubare spazio
        inv_layout.addWidget(self.inv_list)
        self.inv_group.setLayout(inv_layout)
        self.layout.addWidget(self.inv_group)

    def update_status(self, state: dict):
        """Updates GUI from game state."""
        game = state.get("game", {})
        meta = state.get("meta", {})

        # Info
        self.lbl_time.setText(f"⌚ Time: {game.get('time_of_day', 'Morning')}")
        self.lbl_location.setText(f"📍 Loc: {game.get('location', 'Unknown')}")
        self.lbl_outfit.setText(f"👗 Outfit: {game.get('current_outfit', 'Default')}")
        self.lbl_turn.setText(f"⏳ Turn: {meta.get('turn_count', 0)}")

        # Affinità (Lista Semplice e Chiara)
        aff_text = ""
        # Ordiniamo per nome per coerenza
        sorted_aff = sorted(game.get("affinity", {}).items())
        for name, val in sorted_aff:
            aff_text += f"❤️ {name}: {val}\n"

        self.lbl_affinity.setText(aff_text.strip() if aff_text else "No relationships yet.")

        # Inventario
        self.inv_list.clear()
        inventory = game.get("inventory", [])
        if not inventory:
            self.inv_list.addItem("Empty")
        else:
            for item in inventory:
                self.inv_list.addItem(f"📦 {item}")