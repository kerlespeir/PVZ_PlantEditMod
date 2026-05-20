import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


BASE_DIR = Path(__file__).resolve().parent


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(BASE_DIR)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
