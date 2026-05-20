from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QMovie
from PyQt6.QtWidgets import QLabel, QWidget

from ui_helpers import asset


class MySun(QLabel):
    sun_collected = pyqtSignal()

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resize(80, 80)
        self.movie = QMovie(asset(base_dir, "plantimages", "Sun.gif"), parent=self)
        self.setMovie(self.movie)
        self.setScaledContents(True)
        self.movie.start()
        QTimer.singleShot(10000, self.deleteLater)

    def mousePressEvent(self, event) -> None:
        self.sun_collected.emit()
