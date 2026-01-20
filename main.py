import sys
import os
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from config.settings import Settings

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LUNA-RPG v2 - Bootloader")
        self.resize(400, 200)

        mode = Settings.MODE
        sd_url = Settings.get_sd_url()

        lbl = QLabel(f"Sistema avviato.\nModalità: {mode}\nSD URL: {sd_url}", self)
        lbl.setWordWrap(True)
        self.setCentralWidget(lbl)

def main():
    print(f"🚀 Avvio LUNA-RPG v2 in modalità: {Settings.MODE}")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
