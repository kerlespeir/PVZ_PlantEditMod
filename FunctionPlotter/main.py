from __future__ import annotations

import ctypes
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


DEFAULT_CODE = """#include <cmath>

float f(float x) {
    return x * x;
}

float wave(float x) {
    return std::sin(6.0f * x);
}
"""


FUNCTION_RE = re.compile(
    r"(?<![\w:])float\s+([A-Za-z_]\w*)\s*\(\s*float\s+([A-Za-z_]\w*)\s*\)",
    re.MULTILINE,
)


@dataclass
class CompiledFunction:
    name: str
    call: object
    points: list[QPointF]


@dataclass
class CompileResult:
    ok: bool
    message: str
    library_path: Path | None = None
    function_names: list[str] | None = None


class CppCompiler:
    def __init__(self) -> None:
        self._build_dir = Path(tempfile.mkdtemp(prefix="pyqt_cpp_plotter_"))
        self._library: ctypes.CDLL | None = None
        self._current_library_path: Path | None = None
        self._build_count = 0

    def compile(self, source: str) -> CompileResult:
        functions = self._find_functions(source)
        if not functions:
            return CompileResult(
                False,
                "未找到可绘制函数。请定义至少一个形如 float name(float x) 的函数。",
            )

        compiler = shutil.which("clang++") or shutil.which("g++")
        if compiler is None:
            return CompileResult(False, "未找到 C++ 编译器：请安装 clang++ 或 g++。")

        wrapper_source = self._make_wrapper(source, functions)
        source_path = self._build_dir / "plotter_wrapper.cpp"
        self._build_count += 1
        library_path = self._build_dir / self._library_name(self._build_count)
        source_path.write_text(wrapper_source, encoding="utf-8")

        command = [
            compiler,
            "-std=c++17",
            "-O2",
            "-fPIC",
            str(source_path),
            "-o",
            str(library_path),
        ]
        if platform.system() == "Darwin":
            command.insert(2, "-dynamiclib")
        else:
            command.insert(2, "-shared")

        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            cwd=self._build_dir,
            check=False,
        )
        if completed.returncode != 0:
            output = (completed.stderr or completed.stdout).strip()
            return CompileResult(False, output or "编译失败，但编译器没有输出错误信息。")

        return CompileResult(
            True,
            f"编译成功，找到 {len(functions)} 个函数：{', '.join(functions)}",
            library_path=library_path,
            function_names=functions,
        )

    def load_functions(self, result: CompileResult) -> list[CompiledFunction]:
        if result.library_path is None or result.function_names is None:
            return []

        self._library = ctypes.CDLL(str(result.library_path))
        self._current_library_path = result.library_path
        loaded: list[CompiledFunction] = []
        for index, function_name in enumerate(result.function_names):
            wrapped = getattr(self._library, f"plotter_call_{index}")
            wrapped.argtypes = [ctypes.c_float]
            wrapped.restype = ctypes.c_float
            loaded.append(
                CompiledFunction(
                    name=function_name,
                    call=wrapped,
                    points=self._sample(wrapped),
                )
            )
        return loaded

    def _find_functions(self, source: str) -> list[str]:
        names: list[str] = []
        for match in FUNCTION_RE.finditer(source):
            name = match.group(1)
            if name not in names:
                names.append(name)
        return names

    def _make_wrapper(self, source: str, functions: list[str]) -> str:
        wrappers = []
        for index, function_name in enumerate(functions):
            wrappers.append(
                f'extern "C" float plotter_call_{index}(float x) '
                f"{{ return {function_name}(x); }}"
            )
        return source + "\n\n" + "\n".join(wrappers) + "\n"

    def _sample(self, function: object) -> list[QPointF]:
        points: list[QPointF] = []
        for i in range(401):
            x = -1.0 + 2.0 * i / 400.0
            try:
                y = float(function(ctypes.c_float(x)))
            except Exception:
                y = math.nan
            if math.isfinite(y):
                points.append(QPointF(x, y))
            else:
                points.append(QPointF(x, math.nan))
        return points

    def _library_name(self, build_count: int) -> str:
        suffix = ".dylib" if platform.system() == "Darwin" else ".so"
        return f"compiled_functions_{os.getpid()}_{build_count}{suffix}"


class PlotWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._functions: list[CompiledFunction] = []
        self.setMinimumSize(520, 420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_functions(self, functions: list[CompiledFunction]) -> None:
        self._functions = functions
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#fafafa"))

        plot_rect = self.rect().adjusted(48, 28, -24, -48)
        self._draw_grid(painter, plot_rect)
        self._draw_curves(painter, plot_rect)
        self._draw_legend(painter, plot_rect)

    def _draw_grid(self, painter: QPainter, rect) -> None:
        axis_pen = QPen(QColor("#333333"), 1.4)
        grid_pen = QPen(QColor("#dddddd"), 1.0)

        painter.setPen(grid_pen)
        for i in range(9):
            x = rect.left() + rect.width() * i / 8.0
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())
        for i in range(9):
            y = rect.top() + rect.height() * i / 8.0
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        painter.setPen(axis_pen)
        painter.drawRect(rect)
        painter.drawLine(
            QPointF(self._map_x(0.0, rect), rect.top()),
            QPointF(self._map_x(0.0, rect), rect.bottom()),
        )
        painter.drawLine(
            QPointF(rect.left(), self._map_y(0.0, rect)),
            QPointF(rect.right(), self._map_y(0.0, rect)),
        )

        painter.setPen(QColor("#555555"))
        painter.drawText(rect.left(), rect.bottom() + 22, "-1")
        painter.drawText(rect.center().x() - 4, rect.bottom() + 22, "0")
        painter.drawText(rect.right() - 10, rect.bottom() + 22, "1")
        painter.drawText(8, rect.top() + 5, "y=1")
        painter.drawText(8, rect.bottom(), "y=-1")

    def _draw_curves(self, painter: QPainter, rect) -> None:
        if not self._functions:
            painter.setPen(QColor("#777777"))
            painter.setFont(QFont("Arial", 15))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "点击“编译并绘图”后显示曲线")
            return

        colors = [
            QColor("#d72638"),
            QColor("#1b998b"),
            QColor("#2e294e"),
            QColor("#f46036"),
            QColor("#3366cc"),
            QColor("#7a3e9d"),
        ]
        for index, compiled in enumerate(self._functions):
            path = QPainterPath()
            started = False
            for point in compiled.points:
                if not math.isfinite(point.y()):
                    started = False
                    continue
                mapped = QPointF(self._map_x(point.x(), rect), self._map_y(point.y(), rect))
                if started:
                    path.lineTo(mapped)
                else:
                    path.moveTo(mapped)
                    started = True
            painter.setPen(QPen(colors[index % len(colors)], 2.2))
            painter.drawPath(path)

    def _draw_legend(self, painter: QPainter, rect) -> None:
        if not self._functions:
            return
        colors = [
            QColor("#d72638"),
            QColor("#1b998b"),
            QColor("#2e294e"),
            QColor("#f46036"),
            QColor("#3366cc"),
            QColor("#7a3e9d"),
        ]
        x = rect.left()
        y = rect.bottom() + 36
        painter.setFont(QFont("Arial", 10))
        for index, compiled in enumerate(self._functions):
            painter.setPen(QPen(colors[index % len(colors)], 3))
            painter.drawLine(x, y - 5, x + 22, y - 5)
            painter.setPen(QColor("#222222"))
            painter.drawText(x + 28, y, compiled.name)
            x += 100

    def _map_x(self, x: float, rect) -> float:
        return rect.left() + (x + 1.0) * rect.width() / 2.0

    def _map_y(self, y: float, rect) -> float:
        clamped = max(-1.0, min(1.0, y))
        return rect.top() + (1.0 - (clamped + 1.0) / 2.0) * rect.height()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.compiler = CppCompiler()
        self.editor = QPlainTextEdit()
        self.output = QPlainTextEdit()
        self.plot = PlotWidget()

        self.setWindowTitle("C++ Function Plotter")
        self.resize(1180, 720)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.editor.setPlainText(DEFAULT_CODE)
        self.editor.setFont(QFont("Menlo", 13))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.output.setReadOnly(True)
        self.output.setMaximumHeight(150)
        self.output.setFont(QFont("Menlo", 11))
        self.output.setPlainText("准备就绪。")

        compile_button = QPushButton("编译并绘图")
        compile_button.clicked.connect(self.compile_and_plot)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("C++ 代码"))
        left_layout.addWidget(self.editor)
        left_layout.addWidget(compile_button)
        left_layout.addWidget(QLabel("编译输出"))
        left_layout.addWidget(self.output)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.plot)
        splitter.setSizes([540, 640])

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

    def compile_and_plot(self) -> None:
        result = self.compiler.compile(self.editor.toPlainText())
        self.output.setPlainText(result.message)
        if not result.ok:
            self.plot.set_functions([])
            return

        try:
            functions = self.compiler.load_functions(result)
        except Exception as exc:
            self.plot.set_functions([])
            self.output.setPlainText(f"动态库加载或函数调用失败：\n{exc}")
            return

        self.plot.set_functions(functions)
        self.output.setPlainText(result.message)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
