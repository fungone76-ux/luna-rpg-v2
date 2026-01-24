# file: ui/components/status_panel.py
from PySide6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QLabel, QGroupBox, QListWidget, QTextBrowser, \
    QSizePolicy
from PySide6.QtCore import Qt


class StatusPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # BLOCCO VERTICALE: Diciamo al layout "La mia altezza è fissa, non schiacciarmi"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(15)

        # === 1. STATUS (Top Left) ===
        self.info_group = QGroupBox("📊 Status")
        self.info_group.setObjectName("BoxTop")  # ID per il CSS

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(10, 25, 10, 10)

        self.lbl_time = QLabel("⌚ Time: --")
        self.lbl_location = QLabel("📍 Loc: --")
        self.lbl_outfit = QLabel("👗 Outfit: --")
        self.lbl_turn = QLabel("⏳ Turn: --")

        for lbl in [self.lbl_time, self.lbl_location, self.lbl_outfit, self.lbl_turn]:
            lbl.setProperty("class", "StatusText")
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)

        info_layout.addStretch()
        self.info_group.setLayout(info_layout)
        self.layout.addWidget(self.info_group, 0, 0)

        # === 2. MEMORY (Top Right) ===
        self.mem_group = QGroupBox("🧠 Memory")
        self.mem_group.setObjectName("BoxTop")  # ID per il CSS

        mem_layout = QVBoxLayout()
        mem_layout.setContentsMargins(5, 25, 5, 5)

        self.txt_memory = QTextBrowser()
        self.txt_memory.setObjectName("MemoryBox")
        self.txt_memory.setText("No data.")

        mem_layout.addWidget(self.txt_memory)
        self.mem_group.setLayout(mem_layout)
        self.layout.addWidget(self.mem_group, 0, 1)

        # === 3. RELATIONSHIPS (Bottom Left) ===
        self.affinity_group = QGroupBox("❤️ Relationships")
        self.affinity_group.setObjectName("BoxBottom")  # ID DIVERSO (Più piccolo)

        aff_layout = QVBoxLayout()
        aff_layout.setContentsMargins(10, 25, 10, 10)

        self.lbl_affinity = QLabel("None")
        self.lbl_affinity.setObjectName("AffinityLabel")
        self.lbl_affinity.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_affinity.setWordWrap(True)

        aff_layout.addWidget(self.lbl_affinity)
        self.affinity_group.setLayout(aff_layout)
        self.layout.addWidget(self.affinity_group, 1, 0)

        # === 4. INVENTORY (Bottom Right) ===
        self.inv_group = QGroupBox("🎒 Inventory")
        self.inv_group.setObjectName("BoxBottom")  # ID DIVERSO (Più piccolo)

        inv_layout = QVBoxLayout()
        inv_layout.setContentsMargins(5, 25, 5, 5)

        self.inv_list = QListWidget()

        inv_layout.addWidget(self.inv_list)
        self.inv_group.setLayout(inv_layout)
        self.layout.addWidget(self.inv_group, 1, 1)

        # ALTEZZA TOTALE MINIMA GARANTITA (Somma di Top + Bottom + Spazi)
        # 160 + 130 + spazi = circa 330/350
        self.setMinimumHeight(340)

    def update_status(self, state: dict):
        game = state.get("game", {})
        meta = state.get("meta", {})

        self.lbl_time.setText(f"⌚ Time: {game.get('time_of_day', 'Morning')}")
        self.lbl_location.setText(f"📍 {game.get('location', 'Unknown')}")
        self.lbl_outfit.setText(f"👗 {game.get('current_outfit', '-')}")
        self.lbl_turn.setText(f"⏳ Turn: {meta.get('turn_count', 0)}")

        summaries = state.get("summary_log", [])
        if summaries:
            self.txt_memory.setText(summaries[-1])
        else:
            self.txt_memory.setText("No history yet.")

        aff_text = ""
        sorted_aff = sorted(game.get("affinity", {}).items())
        for name, val in sorted_aff:
            aff_text += f"❤️ {name}: {val}\n"
        self.lbl_affinity.setText(aff_text.strip() if aff_text else "None")

        self.inv_list.clear()
        inventory = game.get("inventory", [])
        if not inventory:
            self.inv_list.addItem("Empty")
        else:
            for item in inventory:
                self.inv_list.addItem(f"📦 {item}")

        self.style().unpolish(self)
        self.style().polish(self)