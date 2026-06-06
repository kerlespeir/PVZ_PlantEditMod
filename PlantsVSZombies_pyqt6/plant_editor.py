from __future__ import annotations

import shutil
import subprocess
import sys
import re
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from syntax_highlighter import CppHighlighter
from image_composer import component_image_path, compose_plant_image
from custom_plant_store import (
    card_image_name,
    cleanup_orphan_custom_assets,
    create_or_update_record,
    draft_components_path,
    draft_plant_path,
    normalize_components_source,
    normalize_plant_source,
    parse_registration,
    plant_image_name,
    PlantRecord,
)
from ui_helpers import asset


MODE_LABELS = {
    "A": "玩法 A：组合官方组件",
    "B": "玩法 B：编辑组件并组合植物",
}


def default_plant_template(mode: str) -> str:
    include_name = "../cpp_core/components.h" if mode == "A" else "mode_b_components.h"
    class_name = "MyHybridPlantA" if mode == "A" else "MyHybridPlantB"
    plant_id = 200 if mode == "A" else 201
    return f'''\\
#include "{include_name}"

class {class_name} : public HybridPlant {{
public:
    {class_name}(int r, int c) : HybridPlant(r, c) {{
        // 在这里添加组件: 传入参数含义请参考 components.h 
        components.push_back(std::make_unique<PeaHead>(1, 200));
        // components.push_back(std::make_unique<SunHead>(1, 1000));
        // components.push_back(std::make_unique<WallNutHead>());
        finalize();
    }}
}};

// 填写规则: 派生类类名(可重复使用), ID(自定义植物的唯一标识 不可重复), 显示卡片名
// 植物贴图文件名会自动生成为 custom_<ID>.png
PVZ_REGISTER_HYBRID({class_name}, {plant_id}, "{class_name}")
'''


class PlantEditorScene(QWidget):
    back_to_menu = pyqtSignal()
    open_library = pyqtSignal()

    def __init__(self, base_dir: Path, mode: str, record: PlantRecord | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.mode = mode if mode in MODE_LABELS else "A"
        self.record = record
        self.user_dir = self.base_dir / "user_plants"
        self.user_dir.mkdir(exist_ok=True)
        self.plant_source_path = record.plant_source_path if record else draft_plant_path(self.base_dir, self.mode)
        self.components_source_path = record.components_source_path if record else draft_components_path(self.base_dir)
        self.default_components_path = self.base_dir / "cpp_core" / "components.h"
        self.setFixedSize(960, 720)
        self._build_ui()
        self._load_sources()

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        left_panel = QVBoxLayout()
        back_btn = QPushButton("← 返回", self)
        back_btn.setFixedHeight(30)
        back_btn.setStyleSheet("background: #333; color: white; border: none; padding: 5px 10px;")
        back_btn.clicked.connect(self._handle_back)
        left_panel.addWidget(back_btn)

        mode_label = QLabel(MODE_LABELS[self.mode], self)
        mode_label.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
        left_panel.addWidget(mode_label)

        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #555; background: #1e1e1e; }
            QTabBar::tab { background: #2d2d2d; color: #ccc; padding: 6px 12px; }
            QTabBar::tab:selected { background: #1e1e1e; color: white; }
        """)

        self.components_editor = QPlainTextEdit(self)
        components_readonly = self.mode == "A"
        self.components_editor.setReadOnly(components_readonly)
        self._style_editor(self.components_editor, readonly=components_readonly)
        CppHighlighter(self.components_editor.document())

        self.plant_editor = QPlainTextEdit(self)
        self._style_editor(self.plant_editor, readonly=False)
        CppHighlighter(self.plant_editor.document())
        self.plant_editor.textChanged.connect(self._persist_plant_source)
        if self.mode == "B":
            self.components_editor.textChanged.connect(self._persist_components_source)

        self.tabs.addTab(self.components_editor, "components.h")
        self.tabs.addTab(self.plant_editor, "my_plant.cpp")
        self.tabs.setCurrentIndex(1)
        left_panel.addWidget(self.tabs)
        main_layout.addLayout(left_panel, 6)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)

        title = QLabel("预览", self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        right_panel.addWidget(title)

        self.preview_label = QLabel(self)
        self.preview_label.setFixedSize(200, 200)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background: rgba(0,0,0,0.3); border: 1px solid #555;")
        right_panel.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)

        compile_btn = QPushButton("编译", self)
        compile_btn.setFixedHeight(36)
        compile_btn.setStyleSheet("background: #4CAF50; color: white; font-size: 14px; border: none; border-radius: 4px;")
        compile_btn.clicked.connect(self.compile_plant)
        right_panel.addWidget(compile_btn)

        self.status_output = QPlainTextEdit(self)
        self.status_output.setReadOnly(True)
        self.status_output.setFixedHeight(180)
        self.status_output.setStyleSheet("background: #1a1a1a; color: #ddd; font-family: monospace; font-size: 11px; border: 1px solid #555;")
        right_panel.addWidget(self.status_output)

        right_panel.addStretch()
        main_layout.addLayout(right_panel, 3)

    def _style_editor(self, editor: QPlainTextEdit, readonly: bool) -> None:
        bg = "#2d2d2d" if readonly else "#1e1e1e"
        editor.setStyleSheet(f"background: {bg}; color: #d4d4d4; border: none;")
        font = QFont("Menlo")
        font.setPointSize(12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        editor.setFont(font)
        editor.setTabStopDistance(32)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        bg = QImage(asset(self.base_dir, "res", "Background.jpg"))
        bg = bg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(-250, 0, bg)

    def _read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _handle_back(self) -> None:
        if self.record is not None:
            self.open_library.emit()
        else:
            self.back_to_menu.emit()

    def _load_sources(self) -> None:
        default_components = self._read_text(self.default_components_path)
        if self.mode == "B":
            components_source = self._read_text(self.components_source_path) or default_components
            components_source = normalize_components_source(components_source)
        else:
            components_source = default_components
        plant_source = self._read_text(self.plant_source_path) or default_plant_template(self.mode)
        plant_source = normalize_plant_source(plant_source)

        self.components_editor.blockSignals(True)
        self.components_editor.setPlainText(components_source)
        self.components_editor.blockSignals(False)

        self.plant_editor.blockSignals(True)
        self.plant_editor.setPlainText(plant_source)
        self.plant_editor.blockSignals(False)

        self._persist_plant_source()
        if self.mode == "B":
            self._persist_components_source()
        registration = self._extract_registration(plant_source)
        if registration:
            _, plant_id, _ = registration
            image_name = plant_image_name(plant_id)
            self._generate_preview(plant_source, card_image_name(plant_id), image_name)
        else:
            self.preview_label.clear()

    def _persist_plant_source(self) -> None:
        self.plant_source_path.write_text(self.plant_editor.toPlainText(), encoding="utf-8")

    def _persist_components_source(self) -> None:
        if self.mode == "B":
            self.components_source_path.write_text(self.components_editor.toPlainText(), encoding="utf-8")

    def compile_plant(self) -> None:
        self.status_output.clear()
        source = self.plant_editor.toPlainText()
        self._persist_plant_source()
        self._persist_components_source()

        components = re.findall(r"make_unique<(\w+)>", source)
        if not components:
            self.status_output.setPlainText("编译失败: 植物至少需要一个组件，否则种下后会立即消失。")
            return

        plugin_dir = self.base_dir / "plugins" / "plants"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        registration = self._extract_registration(source)
        if not registration:
            self.status_output.setPlainText(
                "错误: 未找到 PVZ_REGISTER_HYBRID(ClassName, PlantID, \"Name\")"
            )
            return
        _, plant_id, _ = registration
        image_name = plant_image_name(plant_id)

        components_source = self.components_editor.toPlainText() if self.mode == "B" else None
        try:
            saved_record = create_or_update_record(
                self.base_dir,
                self.mode,
                source,
                components_source,
                existing_key=self.record.key if self.record else None,
            )
        except ValueError as exc:
            self.status_output.setPlainText(f"编译失败: {exc}")
            return

        compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
        if not compiler:
            self.status_output.setPlainText("错误: 未找到 C++ 编译器。请安装 clang++ 或 g++。")
            return

        out_path = saved_record.plugin_path

        cmd = [
            compiler, "-std=c++17", "-shared", "-fPIC",
            "-I", str(self.base_dir / "cpp_api"),
            "-I", str(self.base_dir / "cpp_core"),
            "-I", str(saved_record.folder),
            str(saved_record.plant_source_path),
            "-o", str(out_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.status_output.setPlainText(f"编译失败:\n{result.stderr}")
            return

        self.record = saved_record
        self.plant_source_path = saved_record.plant_source_path
        self.components_source_path = saved_record.components_source_path if saved_record.components_source_path else self.components_source_path
        cleanup_orphan_custom_assets(self.base_dir)
        self.status_output.setPlainText(f"编译成功! → {out_path.name}\n植物将在下次开始游戏时可用。")
        self._generate_preview(source, saved_record.card_name, image_name)

    def _extract_registration(self, source: str) -> tuple[str, int, str] | None:
        return parse_registration(source)

    def _generate_preview(self, source: str, card_name: str, image_name: str) -> None:
        components = re.findall(r"make_unique<(\w+)>", source)
        if not components:
            self.preview_label.clear()
            return
        pixmap = compose_plant_image(components, self.base_dir)
        if pixmap is None:
            # 合成失败(缺底图或组件贴图)。落地一张占位图，避免植物种下后不可见、卡片空白。
            pixmap = self._placeholder_pixmap(components)
            self._append_status(
                "警告: 贴图合成失败，已使用占位图。植物可正常游玩，但外观为占位方块。\n"
                "请检查 components_images/ 下是否缺少底图或组件贴图。"
            )
        scaled = pixmap.scaled(
            180, 180,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled)
        save_path = self.base_dir / "plantimages" / image_name
        pixmap.save(str(save_path))
        card_path = self.base_dir / "res" / card_name
        card_pixmap = pixmap.scaled(48, 68, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        card_pixmap.save(str(card_path))
        missing = [name for name in components if not self._component_preview_exists(name)]
        if missing:
            self._append_status(
                "预览提示: 以下组件没有对应贴图，已在预览中跳过: " + ", ".join(missing)
            )

    def _append_status(self, message: str) -> None:
        current = self.status_output.toPlainText()
        self.status_output.setPlainText(f"{current}\n{message}" if current else message)

    def _placeholder_pixmap(self, components: list[str]) -> QPixmap:
        pixmap = QPixmap(100, 140)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.fillRect(10, 30, 80, 100, QColor(80, 160, 90))
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        label = "+".join(c.replace("Head", "") for c in components[:2]) or "Plant"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, label)
        painter.end()
        return pixmap

    def _component_preview_exists(self, component_name: str) -> bool:
        return component_image_path(component_name, self.base_dir) is not None
