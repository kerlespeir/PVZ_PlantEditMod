from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBitmap, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget


def asset(base_dir: Path, *parts: str) -> str:
    return str(base_dir.joinpath(*parts))


class ImageButton(QPushButton):
    def __init__(
        self,
        base_dir: Path,
        normal_path: str,
        hover_path: str | None = None,
        parent: QWidget | None = None,
        use_mask: bool = True,
        scale: float = 1.1,
    ) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.normal_path = normal_path
        self.hover_path = hover_path
        self.scale = scale
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton{border:0px;background:transparent;}")
        self._set_image(normal_path, use_mask)

    def _pixmap(self, path: str) -> QPixmap:
        pix = QPixmap(path)
        if self.scale != 1.0 and not pix.isNull():
            pix = pix.scaled(
                int(pix.width() * self.scale),
                int(pix.height() * self.scale),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pix

    def _set_image(self, path: str, use_mask: bool = False) -> None:
        pix = self._pixmap(path)
        self.setFixedSize(pix.size())
        if use_mask:
            self.setMask(QBitmap(pix.mask()))
        self.setIcon(QIcon(pix))
        self.setIconSize(pix.size())

    def enterEvent(self, event) -> None:
        if self.hover_path:
            self._set_image(self.hover_path)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self.hover_path:
            self._set_image(self.normal_path)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self.move(self.x() + 1, self.y() + 1)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.move(self.x() - 1, self.y() - 1)
        super().mouseReleaseEvent(event)


class ImageDialog(QWidget):
    def __init__(self, image_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.FramelessWindowHint)
        pix = QPixmap(image_path)
        self.setFixedSize(pix.size())
        label = QLabel(self)
        label.setPixmap(pix)
        label.resize(pix.size())


def tinted_pixmap(source: QPixmap, alpha: int = 150) -> QPixmap:
    temp = QPixmap(source.size())
    temp.fill(Qt.GlobalColor.transparent)
    painter = QPainter(temp)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    painter.drawPixmap(0, 0, source)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    painter.fillRect(temp.rect(), Qt.GlobalColor.transparent)
    painter.fillRect(temp.rect(), Qt.GlobalColor.black)
    painter.setOpacity(alpha / 255)
    painter.end()
    return temp
