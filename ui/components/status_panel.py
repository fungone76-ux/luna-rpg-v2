# file: ui/components/status_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QListWidget


class StatusPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)

        # Info Generali
        self.info_group = QGroupBox("Stato")
        info_layout = QVBoxLayout()
        self.lbl_location = QLabel("Luogo: -")
        self.lbl_outfit = QLabel("Outfit: -")
        self.lbl_turn = QLabel("Turno: 0")
        info_layout.addWidget(self.lbl_location)
        info_layout.addWidget(self.lbl_outfit)
        info_layout.addWidget(self.lbl_turn)
        self.info_group.setLayout(info_layout)
        self.layout.addWidget(self.info_group)

        # Affinità
        self.affinity_group = QGroupBox("Affinità")
        aff_layout = QVBoxLayout()
        self.lbl_affinity = QLabel("Nessuna")
        aff_layout.addWidget(self.lbl_affinity)
        self.affinity_group.setLayout(aff_layout)
        self.layout.addWidget(self.affinity_group)

        # Inventario
        self.inv_group = QGroupBox("Inventario")
        inv_layout = QVBoxLayout()
        self.inv_list = QListWidget()
        inv_layout.addWidget(self.inv_list)
        self.inv_group.setLayout(inv_layout)
        self.layout.addWidget(self.inv_group, stretch=1)

    def update_status(self, state: dict):
        """Aggiorna la GUI leggendo lo stato del gioco."""
        game = state.get("game", {})
        meta = state.get("meta", {})

        self.lbl_location.setText(f"📍 Luogo: {game.get('location', 'Unknown')}")
        self.lbl_outfit.setText(f"👗 Outfit: {game.get('current_outfit', 'Default')}")
        self.lbl_turn.setText(f"⏳ Turno: {meta.get('turn_count', 0)}")

        # Affinità
        aff_text = ""
        for name, val in game.get("affinity", {}).items():
            aff_text += f"{name}: {val}\n"
        self.lbl_affinity.setText(aff_text.strip())

        # Inventario
        self.inv_list.clear()
        for item in game.get("inventory", []):
            self.inv_list.addItem(f"📦 {item}")
