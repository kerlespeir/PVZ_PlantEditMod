from __future__ import annotations

from functools import partial
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from custom_plant_store import (
    BUILTIN_HYBRID_IDS,
    cleanup_orphan_custom_assets,
    delete_record,
    load_record,
    load_records,
    load_selected_plants,
    plant_image_name,
    save_selected_plants,
)
from ui_helpers import asset


class _HybridEntry:
    """杂交植物虚拟条目 — 可勾选，不可编辑/删除"""
    def __init__(self, plant_id: int):
        self.plant_id = plant_id
        self.key = f"__hybrid_{plant_id}"
        self.mode = "H"  # Hybrid
        self.display_name = f"杂交植物 #{plant_id}"
        self.image_name = plant_image_name(plant_id)


class PlantLibraryScene(QWidget):
    back_to_menu = pyqtSignal()
    edit_plant = pyqtSignal(str)

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.setFixedSize(960, 720)
        self.page = 0
        self.page_size = 8
        self.records = []
        self.selected_ids: set[int] = set()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        top = QHBoxLayout()
        back_btn = QPushButton("← 返回主菜单", self)
        back_btn.setFixedHeight(30)
        back_btn.setStyleSheet("background: #333; color: white; border: none; padding: 5px 10px;")
        back_btn.clicked.connect(lambda: self.back_to_menu.emit())
        top.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        title = QLabel("Plant Library", self)
        title.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
        top.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        top.addStretch()
        layout.addLayout(top)

        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(self.status_label)

        self.grid_container = QWidget(self)
        self.grid = QGridLayout(self.grid_container)
        self.grid.setHorizontalSpacing(18)
        self.grid.setVerticalSpacing(18)
        layout.addWidget(self.grid_container, 1)

        pager = QHBoxLayout()
        self.prev_btn = QPushButton("< 向左翻页", self)
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setStyleSheet("background: #2d2d2d; color: white; border: 1px solid #666;")
        self.prev_btn.clicked.connect(self.prev_page)
        pager.addWidget(self.prev_btn)

        self.page_label = QLabel(self)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: white; font-size: 14px;")
        pager.addWidget(self.page_label, 1)

        self.next_btn = QPushButton("向右翻页 >", self)
        self.next_btn.setFixedHeight(34)
        self.next_btn.setStyleSheet("background: #2d2d2d; color: white; border: 1px solid #666;")
        self.next_btn.clicked.connect(self.next_page)
        pager.addWidget(self.next_btn)
        layout.addLayout(pager)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        bg = QImage(asset(self.base_dir, "res", "Background.jpg"))
        bg = bg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(-250, 0, bg)

    def refresh(self) -> None:
        cleanup_orphan_custom_assets(self.base_dir)
        self.records = load_records(self.base_dir)

        # 杂交植物（仅当 .dylib 存在时才显示）
        from plants.cpp_bridge import CppPlantLoader
        loader = CppPlantLoader(self.base_dir / "plugins" / "plants")
        existing_plugins = loader.load_all()
        for hid in sorted(BUILTIN_HYBRID_IDS):
            if hid in existing_plugins and hid not in {r.plant_id for r in self.records}:
                self.records.append(_HybridEntry(hid))

        self.records.sort(key=lambda r: (r.plant_id, getattr(r, 'display_name', '')))

        loaded = load_selected_plants(self.base_dir)
        if loaded is None:
            # 首次加载时，所有植物默认选中并保存
            self.selected_ids = {r.plant_id for r in self.records if isinstance(r, _HybridEntry) or r.plant_id not in BUILTIN_HYBRID_IDS}
            # 上面那行太复杂，简化：所有非内置植物ID都加入
            self.selected_ids = {r.plant_id for r in self.records if r.plant_id not in (1, 2, 3, 4, 5)}
            save_selected_plants(self.base_dir, self.selected_ids)
        else:
            self.selected_ids = loaded
        max_page = max(0, (len(self.records) - 1) // self.page_size)
        self.page = min(self.page, max_page)
        self._render_page()

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _render_page(self) -> None:
        self._clear_grid()

        if not self.records:
            self.status_label.setText("还没有保存过自定义植物。")
            self.page_label.setText("第 1 / 1 页")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        self.status_label.setText(f"共 {len(self.records)} 个植物")
        start = self.page * self.page_size
        end = start + self.page_size
        page_records = self.records[start:end]

        for index, record in enumerate(page_records):
            card = self._build_card(record)
            row = index // 4
            col = index % 4
            self.grid.addWidget(card, row, col)

        total_pages = (len(self.records) - 1) // self.page_size + 1
        self.page_label.setText(f"第 {self.page + 1} / {total_pages} 页")
        self.prev_btn.setEnabled(self.page > 0)
        self.next_btn.setEnabled(end < len(self.records))

    def _build_card(self, record) -> QWidget:
        card = QWidget(self)
        card.setStyleSheet("background: rgba(20,20,20,0.6); border: 1px solid #666;")
        card.setFixedSize(205, 275)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        is_hybrid = isinstance(record, _HybridEntry)

        # 缩略图按钮：点击弹出操作菜单
        image_path = self.base_dir / "plantimages" / record.image_name
        pix = QPixmap(str(image_path))
        thumb = QPushButton(card)
        thumb.setFixedSize(180, 150)
        thumb.setCursor(Qt.CursorShape.PointingHandCursor)
        thumb.setStyleSheet(
            "QPushButton { background: rgba(0,0,0,0.25); border: 1px solid #555; }"
            "QPushButton:hover { border: 1px solid #aaa; background: rgba(40,40,40,0.5); }"
        )
        if not pix.isNull():
            scaled = pix.scaled(170, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            thumb.setIcon(QIcon(scaled))
            thumb.setIconSize(scaled.size())
        else:
            thumb.setText("无贴图")
        if is_hybrid:
            thumb.clicked.connect(partial(self._show_hybrid_actions, record.plant_id, record.display_name))
        else:
            thumb.clicked.connect(partial(self._show_record_actions, record.key))
        layout.addWidget(thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        mode_text = "hybrid" if is_hybrid else f"mode {record.mode}"
        info = QLabel(f'{mode_text}\n{record.display_name}\nID="{record.plant_id}"', card)
        info.setStyleSheet("color: white; font-size: 12px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        # 勾选框
        cb = QCheckBox("启用", card)
        cb.setChecked(record.plant_id in self.selected_ids)
        cb.setStyleSheet("color: #ccc; font-size: 12px;")
        cb.stateChanged.connect(partial(self._toggle_selection, record.plant_id))
        layout.addWidget(cb, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        return card

    def _show_hybrid_actions(self, plant_id: int, display_name: str) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle(f"{display_name} (杂交植物)")
        dialog.setText("预编译杂交植物，不可编辑。")
        delete_btn = dialog.addButton("删除", QMessageBox.ButtonRole.DestructiveRole)
        dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() == delete_btn:
            self._delete_hybrid(plant_id, display_name)

    def _show_record_actions(self, record_key: str) -> None:
        record = load_record(self.base_dir, record_key)
        if not record:
            self.refresh()
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle(record.display_name)
        dialog.setText("请选择操作")
        del_btn = dialog.addButton("删除植物", QMessageBox.ButtonRole.DestructiveRole)
        edit_btn = dialog.addButton("重新编辑", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        clicked = dialog.clickedButton()
        if clicked == edit_btn:
            self.edit_plant.emit(record.key)
        elif clicked == del_btn:
            self._confirm_delete(record.key, record.display_name)

    def _delete_hybrid(self, plant_id: int, display_name: str) -> None:
        """删除预编译杂交植物"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle("确定删除吗？")
        dialog.setText(f"确定删除杂交植物 {display_name} (ID {plant_id}) 吗？\n这将移除其插件文件和贴图。")
        confirm = dialog.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("再想想", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() != confirm:
            return

        # 通过 CppPlantLoader 找到对应插件文件
        from plants.cpp_bridge import CppPlantLoader
        loader = CppPlantLoader(self.base_dir / "plugins" / "plants")
        plugins = loader.load_all()
        plugin = plugins.get(plant_id)
        if plugin and plugin.path.exists():
            plugin.path.unlink()

        # 删除贴图
        (self.base_dir / "plantimages" / f"custom_{plant_id}.png").unlink(missing_ok=True)
        (self.base_dir / "res" / f"custom_{plant_id}_card.png").unlink(missing_ok=True)

        # 从杂交植物白名单和选中列表中移除
        BUILTIN_HYBRID_IDS.discard(plant_id)
        self.selected_ids.discard(plant_id)
        save_selected_plants(self.base_dir, self.selected_ids)

        self.refresh()

    def _confirm_delete(self, record_key: str, display_name: str) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("确定删除吗？")
        dialog.setText(f"确定删除 {display_name} 吗？")
        confirm = dialog.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("再想想", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() == confirm:
            delete_record(self.base_dir, record_key)
            self.selected_ids = load_selected_plants(self.base_dir) or set()
            self.refresh()

    def _toggle_selection(self, plant_id: int, state: int) -> None:
        if state == Qt.CheckState.Checked.value:
            self.selected_ids.add(plant_id)
        else:
            self.selected_ids.discard(plant_id)
        save_selected_plants(self.base_dir, self.selected_ids)

    def prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self._render_page()

    def next_page(self) -> None:
        if (self.page + 1) * self.page_size < len(self.records):
            self.page += 1
            self._render_page()
