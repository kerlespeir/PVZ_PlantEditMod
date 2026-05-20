from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QLabel, QMainWindow, QStackedWidget

from game_scene import GameScene
from menu import MainMenu
from ui_helpers import ImageButton, ImageDialog, asset


class MainWindow(QMainWindow):
    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.setWindowIcon(QIcon(asset(base_dir, "res", "pvz.ico")))
        self.setWindowTitle("Plants vs.Zombies")
        self.setFixedSize(960, 720)

        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)
        self.menu = MainMenu(base_dir)
        self.stack.addWidget(self.menu)
        self.game: GameScene | None = None
        self._connect_menu()

    def _connect_menu(self) -> None:
        self.menu.play.connect(self.start_game)
        self.menu.ready_for_quit.connect(self.show_quit)
        self.menu.help_clicked.connect(self.show_help)
        self.menu.option_clicked.connect(lambda: self.show_simple_dialog("Options.png", "yesButton.png", 540))
        self.menu.unable_clicked.connect(lambda: self.show_simple_dialog("Unable.png", "yesButton2.png", 215))

    def center_widget(self, widget) -> None:
        widget.move((self.width() - widget.width()) // 2, (self.height() - widget.height()) // 2)

    def show_quit(self) -> None:
        dialog = ImageDialog(asset(self.base_dir, "res", "QuitWindow.png"), self)
        self.center_widget(dialog)

        quit_btn = ImageButton(self.base_dir, asset(self.base_dir, "res", "QuitButton.png"), parent=dialog)
        quit_btn.move(40, 210)
        quit_btn.clicked.connect(self.close)

        cancel = ImageButton(self.base_dir, asset(self.base_dir, "res", "CancelButton.png"), parent=dialog)
        cancel.move(270, 210)
        cancel.clicked.connect(dialog.deleteLater)
        dialog.show()

    def show_help(self) -> None:
        help_win = QMainWindow(self, Qt.WindowType.FramelessWindowHint)
        pix = QPixmap(asset(self.base_dir, "res", "Help.png"))
        help_win.setFixedSize(pix.size())
        label = QLabel(help_win)
        label.setPixmap(pix)
        label.resize(pix.size())
        back = ImageButton(self.base_dir, asset(self.base_dir, "res", "BackButton.png"), parent=help_win)
        back.move((help_win.width() - back.width()) // 2, 600)
        back.clicked.connect(help_win.deleteLater)
        self.center_widget(help_win)
        help_win.show()

    def show_simple_dialog(self, image_name: str, button_name: str, button_y: int) -> None:
        dialog = ImageDialog(asset(self.base_dir, "res", image_name), self)
        self.center_widget(dialog)
        yes = ImageButton(self.base_dir, asset(self.base_dir, "res", button_name), parent=dialog)
        yes.move((dialog.width() - yes.width()) // 2 - 5, button_y)
        yes.clicked.connect(dialog.deleteLater)
        dialog.show()

    def start_game(self) -> None:
        self.game = GameScene(self.base_dir)
        self.stack.addWidget(self.game)
        self.stack.setCurrentWidget(self.game)
        self.game.menu_clicked.connect(self.show_pause)
        self.game.main_menu.connect(self.return_to_menu)
        self.game.start_game()

    def show_pause(self) -> None:
        dialog = ImageDialog(asset(self.base_dir, "res", "Options.png"), self)
        self.center_widget(dialog)

        return_btn = ImageButton(self.base_dir, asset(self.base_dir, "res", "returnButton.png"), parent=dialog)
        return_btn.move((dialog.width() - return_btn.width()) // 2, 540)
        return_btn.clicked.connect(dialog.deleteLater)

        menu_btn = ImageButton(self.base_dir, asset(self.base_dir, "res", "mainMenu.png"), parent=dialog)
        menu_btn.move((dialog.width() - menu_btn.width()) // 2, 450)
        menu_btn.clicked.connect(lambda: (dialog.deleteLater(), self.return_to_menu()))
        dialog.show()

    def return_to_menu(self) -> None:
        if self.game is not None:
            self.game.stop_all()
            self.stack.setCurrentWidget(self.menu)
            self.stack.removeWidget(self.game)
            self.game.deleteLater()
            self.game = None
