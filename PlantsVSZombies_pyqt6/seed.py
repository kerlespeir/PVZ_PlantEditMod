from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBitmap, QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget

from ui_helpers import asset


class Seed(QPushButton):
    check = pyqtSignal()

    def __init__(self, base_dir: Path, cooldown: int, sun: int, plant_image: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.cooldown = cooldown
        self.sun = sun
        self.in_cd = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton{border:0px;background:transparent;}")

        picture = QPixmap(asset(base_dir, "res", "Card.png"))
        self.setFixedSize(picture.size())
        self.setMask(QBitmap(picture.mask()))

        painter = QPainter(picture)
        plant = QPixmap(plant_image)
        self.plant_cursor = plant.scaled(
            int(plant.width() * 0.7),
            int(plant.height() * 0.7),
        )
        display = plant.scaled(
            int(picture.width() * 0.7),
            int(picture.height() * 0.7),
        )
        painter.drawPixmap((picture.width() - display.width()) // 2, 15, display)
        painter.drawText(16, 71, str(sun))
        painter.end()

        self.setIcon(QIcon(picture))
        self.setIconSize(picture.size())

        mask_path = asset(base_dir, "res", "mask.png")
        self.mask1 = QLabel(self)
        mask_pix = QPixmap(mask_path)
        self.mask1.resize(mask_pix.size())
        self.mask1.setPixmap(mask_pix)

        self.mask2 = QLabel(self)
        self.mask2.resize(mask_pix.size())
        self.mask2.setPixmap(mask_pix)
        self.mask2.move(0, -76)

    def checksun(self, sun_num: int) -> None:
        self.mask1.setVisible(sun_num < self.sun)

    def cdstart(self) -> None:
        self.mask1.show()
        self.in_cd = True
        self.mask2.move(0, 0)
        anime = QPropertyAnimation(self.mask2, b"geometry", self)
        anime.setStartValue(QRect(0, 0, self.mask2.width(), self.mask2.height()))
        anime.setEndValue(QRect(0, -76, self.mask2.width(), self.mask2.height()))
        anime.setEasingCurve(QEasingCurve.Type.Linear)
        anime.setDuration(self.cooldown)
        anime.start()
        self._anime = anime
        QTimer.singleShot(self.cooldown, self._finish_cd)

    def _finish_cd(self) -> None:
        self.in_cd = False
        self.check.emit()

    def mousePressEvent(self, event) -> None:
        if self.mask1.isHidden():
            super().mousePressEvent(event)
        else:
            event.ignore()
