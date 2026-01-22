# file: ui/components/image_viewer.py
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QGraphicsView,
                               QGraphicsScene, QDialog, QPushButton, QHBoxLayout)
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, Signal


class ZoomableGraphicsView(QGraphicsView):
    """Viewer con zoom (rotellina) e pan (trascinamento)."""

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        scene = QGraphicsScene(self)
        scene.addPixmap(pixmap)
        self.setScene(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event):
        factor = 1.25 if event.angleDelta().y() > 0 else 0.8
        self.scale(factor, factor)


class ImagePreviewDialog(QDialog):
    """Finestra popup a schermo intero per l'immagine."""

    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ispezione Visiva")
        self.resize(1000, 800)
        layout = QVBoxLayout(self)
        view = ZoomableGraphicsView(pixmap)
        layout.addWidget(view)


class InteractiveImageViewer(QWidget):
    """Widget principale per la UI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Label cliccabile
        self.image_lbl = QLabel("In attesa di segnale video...")
        self.image_lbl.setAlignment(Qt.AlignCenter)
        self.image_lbl.setStyleSheet("background-color: #000; border: 2px solid #444;")
        self.image_lbl.setMinimumSize(400, 400)  # Dimensione fissa stile vecchio layout
        # Hack per rendere la label cliccabile
        self.image_lbl.mousePressEvent = self._on_click

        self.layout.addWidget(self.image_lbl)
        self.current_pixmap = None

    def update_image(self, path):
        if not path: return
        self.current_pixmap = QPixmap(path)
        if not self.current_pixmap.isNull():
            self.image_lbl.setPixmap(self.current_pixmap.scaled(
                self.image_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            ))
            self.image_lbl.setText("")

    def _on_click(self, event):
        if self.current_pixmap:
            dlg = ImagePreviewDialog(self.current_pixmap, self)
            dlg.exec()