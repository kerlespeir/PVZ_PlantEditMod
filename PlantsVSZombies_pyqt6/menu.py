from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QWidget

from ui_helpers import ImageButton, asset


class MainMenu(QWidget):
    play = pyqtSignal()
    editor_a_clicked = pyqtSignal()
    editor_b_clicked = pyqtSignal()
    library_clicked = pyqtSignal()
    ready_for_quit = pyqtSignal()
    help_clicked = pyqtSignal()
    option_clicked = pyqtSignal()
    unable_clicked = pyqtSignal()

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.setFixedSize(960, 720)
        self._build_buttons()

    def _build_buttons(self) -> None:
        newgame = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "SelectorScreen_StartAdventure_Button1.png"),
            asset(self.base_dir, "res", "SelectorScreen_StartAdventure_Highlight.png"),
            self,
        )
        newgame.move(515, 125)
        newgame.clicked.connect(lambda checked=False: self.play.emit())

        editor_a = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "cut_buttons", "row0_normal.png"),
            asset(self.base_dir, "res", "cut_buttons", "row0_highlight.png"),
            self,
        )
        editor_a.move(515, 240)
        editor_a.clicked.connect(lambda checked=False: self.editor_a_clicked.emit())

        editor_b = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "cut_buttons", "row1_normal.png"),
            asset(self.base_dir, "res", "cut_buttons", "row1_highlight.png"),
            self,
        )
        editor_b.move(520, 334)
        editor_b.clicked.connect(lambda checked=False: self.editor_b_clicked.emit())

        library_btn = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "cut_buttons", "row2_normal.png"),
            asset(self.base_dir, "res", "cut_buttons", "row2_highlight.png"),
            self,
        )
        library_btn.move(520, 410)
        library_btn.clicked.connect(lambda checked=False: self.library_clicked.emit())

        help_btn = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "SelectorScreen_Help1.png"),
            asset(self.base_dir, "res", "SelectorScreen_Help2.png"),
            self,
            use_mask=False,
        )
        help_btn.move(790, 635)
        help_btn.clicked.connect(lambda checked=False: self.help_clicked.emit())

        options = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "SelectorScreen_Options1.png"),
            asset(self.base_dir, "res", "SelectorScreen_Options2.png"),
            self,
            use_mask=False,
        )
        options.move(692, 596)
        options.clicked.connect(lambda checked=False: self.option_clicked.emit())

        quit_btn = ImageButton(
            self.base_dir,
            asset(self.base_dir, "res", "SelectorScreen_Quit1.png"),
            asset(self.base_dir, "res", "SelectorScreen_Quit2.png"),
            self,
            use_mask=False,
        )
        quit_btn.move(870, 628)
        quit_btn.clicked.connect(lambda checked=False: self.ready_for_quit.emit())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        bg = QImage(asset(self.base_dir, "res", "bg.png"))
        bg = bg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(0, 0, bg)
