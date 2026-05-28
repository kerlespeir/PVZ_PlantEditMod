from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPainter, QPixmap
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
from image_composer import compose_plant_image
from plants.cpp_bridge import CppPlantLoader
from ui_helpers import asset


COMPONENTS_HEADER = '''\
// ===== components.h (只读) =====
// 可用组件一览，不可编辑

#pragma once
#include "hybrid_plant.h"
#include <cmath>
#include <memory>

class Component {
public:
    Component(int cost, int cooldown, int hp);
    virtual ~Component() = default;
    virtual void step(GameAPI& api, HybridPlant* owner) = 0;
    int get_cost() const;
    int get_cooldown() const;
    int get_hp() const;
};

// 豌豆射手头: PeaHead(发射数量, 发射间隔tick)
// cost = ceil(20000/间隔*数量), hp = 300
class PeaHead : public Component {
public:
    PeaHead(int shot_number, int time_period);
    void step(GameAPI& api, HybridPlant* owner) override;
};

// 向日葵头: SunHead(阳光数量, 产出间隔tick)
// cost = ceil(50000/间隔*数量), hp = 300
class SunHead : public Component {
public:
    SunHead(int amount, int time_period);
    void step(GameAPI& api, HybridPlant* owner) override;
};

// 土豆地雷头: PotatoMineHead()
// cost = 25, cooldown = 30000, hp = 300
// 1500 tick后成熟, 接触僵尸爆炸
class PotatoMineHead : public Component {
public:
    PotatoMineHead();
    void step(GameAPI& api, HybridPlant* owner) override;
};

// 坚果头: WallNutHead()
// cost = 50, cooldown = 30000, hp = 4000
// 按血量比例切换受损动画
class WallNutHead : public Component {
public:
    WallNutHead();
    void step(GameAPI& api, HybridPlant* owner) override;
};
'''

PLANT_TEMPLATE = '''\
#include "../cpp_core/components.h"

class MyHybridPlant : public HybridPlant {
public:
    MyHybridPlant(int r, int c) : HybridPlant(r, c) {
        // 在这里添加组件:
        // components.push_back(std::make_unique<PeaHead>(1, 200));
        // components.push_back(std::make_unique<SunHead>(1, 1000));
        // components.push_back(std::make_unique<WallNutHead>());
        finalize();
    }
};

PVZ_REGISTER_HYBRID(MyHybridPlant, 200, "MyHybridPlant", "MyHybridPlant.png")
'''

# PLACEHOLDER_CLASS


class PlantEditorScene(QWidget):
    back_to_menu = pyqtSignal()

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.setFixedSize(960, 720)
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        left_panel = QVBoxLayout()
        back_btn = QPushButton("← 返回主菜单", self)
        back_btn.setFixedHeight(30)
        back_btn.setStyleSheet("background: #333; color: white; border: none; padding: 5px 10px;")
        back_btn.clicked.connect(lambda: self.back_to_menu.emit())
        left_panel.addWidget(back_btn)

        self.tabs = QTabWidget(self)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #555; background: #1e1e1e; }
            QTabBar::tab { background: #2d2d2d; color: #ccc; padding: 6px 12px; }
            QTabBar::tab:selected { background: #1e1e1e; color: white; }
        """)

        self.components_editor = QPlainTextEdit(self)
        self.components_editor.setReadOnly(True)
        self.components_editor.setPlainText(COMPONENTS_HEADER)
        self._style_editor(self.components_editor, readonly=True)
        CppHighlighter(self.components_editor.document())

        self.plant_editor = QPlainTextEdit(self)
        self.plant_editor.setPlainText(PLANT_TEMPLATE)
        self._style_editor(self.plant_editor, readonly=False)
        CppHighlighter(self.plant_editor.document())

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

    def compile_plant(self) -> None:
        self.status_output.clear()
        source = self.plant_editor.toPlainText()

        user_dir = self.base_dir / "user_plants"
        user_dir.mkdir(exist_ok=True)
        plugin_dir = self.base_dir / "plugins" / "plants"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        class_name = self._extract_class_name(source)
        if not class_name:
            self.status_output.setPlainText("错误: 未找到类名。请确保代码中有 'class XXX : public HybridPlant'")
            return

        src_path = user_dir / f"{class_name}.cpp"
        src_path.write_text(source, encoding="utf-8")

        compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
        if not compiler:
            self.status_output.setPlainText("错误: 未找到 C++ 编译器。请安装 clang++ 或 g++。")
            return

        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        out_path = plugin_dir / f"{class_name}{suffix}"

        cmd = [
            compiler, "-std=c++17", "-shared", "-fPIC",
            "-I", str(self.base_dir / "cpp_api"),
            "-I", str(self.base_dir / "cpp_core"),
            str(src_path),
            "-o", str(out_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            self.status_output.setPlainText(f"编译失败:\n{result.stderr}")
            return

        self.status_output.setPlainText(f"编译成功! → {out_path.name}\n植物将在下次开始游戏时可用。")
        self._generate_preview(source, class_name)

    def _extract_class_name(self, source: str) -> str | None:
        import re
        match = re.search(r"class\s+(\w+)\s*:\s*public\s+HybridPlant", source)
        return match.group(1) if match else None

    def _generate_preview(self, source: str, class_name: str) -> None:
        import re
        components = re.findall(r"make_unique<(\w+)>", source)
        if not components:
            return
        pixmap = compose_plant_image(components, self.base_dir)
        if pixmap:
            scaled = pixmap.scaled(
                180, 180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)
            save_path = self.base_dir / "plantimages" / f"{class_name}.png"
            pixmap.save(str(save_path))
            card_path = self.base_dir / "res" / f"{class_name}.png"
            card_pixmap = pixmap.scaled(48, 68, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            card_pixmap.save(str(card_path))


