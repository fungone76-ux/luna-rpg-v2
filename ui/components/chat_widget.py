# file: ui/components/chat_widget.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt


class ChatWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.layout.addWidget(self.text_browser)

    def append_message(self, sender: str, text: str, is_user: bool = False):
        """Aggiunge un messaggio formattato alla chat."""
        color = "#007acc" if is_user else "#4ec9b0"  # Blu per user, Verde acqua per AI
        align = "right" if is_user else "left"

        # Formattazione HTML semplice
        html = f"""
        <div style='text-align: {align}; margin-bottom: 10px;'>
            <b style='color: {color}; font-size: 14px;'>{sender}</b><br>
            <span style='font-size: 15px;'>{text}</span>
        </div>
        <hr style='border: 0; border-top: 1px solid #333;'>
        """
        self.text_browser.append(html)

        # Auto-scroll in basso
        sb = self.text_browser.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear_chat(self):
        self.text_browser.clear()
