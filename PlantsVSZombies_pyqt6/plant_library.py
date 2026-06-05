from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from custom_plant_store import cleanup_orphan_custom_assets, delete_record, load_record, load_records
from ui_helpers import asset


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


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
        card.setFixedSize(205, 250)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        thumb = ClickableLabel(card)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumb.setFixedSize(180, 150)
        thumb.setStyleSheet("background: rgba(0,0,0,0.25); border: 1px solid #555;")
        image_path = self.base_dir / "plantimages" / record.image_name
        pix = QPixmap(str(image_path))
        if not pix.isNull():
            thumb.setPixmap(pix.scaled(170, 140, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            thumb.setText("无贴图")
            thumb.setStyleSheet("background: rgba(0,0,0,0.25); border: 1px solid #555; color: white;")
        thumb.clicked.connect(lambda record_key=record.key: self._show_actions(record_key))
        layout.addWidget(thumb, alignment=Qt.AlignmentFlag.AlignCenter)

        info = QLabel(f'mode {record.mode}\n{record.display_name}\nID="{record.plant_id}"', card)
        info.setStyleSheet("color: white; font-size: 13px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        return card

    def _show_actions(self, record_key: str) -> None:
        record = load_record(self.base_dir, record_key)
        if not record:
            self.refresh()
            return
        dialog = QMessageBox(self)
        dialog.setWindowTitle(record.display_name)
        dialog.setText("请选择操作")
        delete_button = dialog.addButton("删除植物", QMessageBox.ButtonRole.DestructiveRole)
        edit_button = dialog.addButton("重新编辑", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == edit_button:
            self.edit_plant.emit(record.key)
        elif clicked == delete_button:
            self._confirm_delete(record.key, record.display_name)

    def _confirm_delete(self, record_key: str, display_name: str) -> None:
        dialog = QMessageBox(self)
        dialog.setWindowTitle("确定删除吗？")
        dialog.setText(f"确定删除 {display_name} 吗？")
        confirm = dialog.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("再想想", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() == confirm:
            delete_record(self.base_dir, record_key)
            self.refresh()

    def prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self._render_page()

    def next_page(self) -> None:
        if (self.page + 1) * self.page_size < len(self.records):
            self.page += 1
            self._render_page()
