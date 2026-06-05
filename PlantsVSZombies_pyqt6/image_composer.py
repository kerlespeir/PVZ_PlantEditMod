from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap


COMPONENT_IMAGE_MAP = {
    "PeaHead": "PeaHeadComponent.png",
    "SunHead": "SunHeadComponent.png",
    "WallNutHead": "WallNutHeadComponent.png",
    "PotatoMineHead": "PotatoMineHeadComponent.png",
}

THREE_HEAD_BASE_IMAGE = "plant_base_3.png"
THREE_HEAD_BASE_SIZE = (2064, 2030)
THREE_HEAD_COMPONENT_SIZE = (600, 600)
THREE_HEAD_ANCHORS = [(163, 688), (684, 357), (1374, 718)]


def component_image_path(component_name: str, base_dir: Path) -> Path | None:
    img_dir = base_dir / "components_images"
    mapped = COMPONENT_IMAGE_MAP.get(component_name)
    if mapped:
        mapped_path = img_dir / mapped
        if mapped_path.exists():
            return mapped_path

    fallback = img_dir / f"{component_name}.png"
    if fallback.exists():
        return fallback
    return None


def compose_plant_image(components: list[str], base_dir: Path) -> QPixmap | None:
    img_dir = base_dir / "components_images"
    if not img_dir.exists():
        return None

    if len(components) <= 3:
        return _compose_three_head_plant(components, img_dir, base_dir)

    return _compose_stacked_plant(components, img_dir, base_dir)


def _compose_three_head_plant(components: list[str], img_dir: Path, base_dir: Path) -> QPixmap | None:
    base_path = img_dir / THREE_HEAD_BASE_IMAGE
    if not base_path.exists():
        return None

    canvas = QPixmap(*THREE_HEAD_BASE_SIZE)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    base = QPixmap(str(base_path))
    painter.drawPixmap(0, 0, base)

    for comp_name, (x, y) in zip(components[:3], THREE_HEAD_ANCHORS):
        img_path = component_image_path(comp_name, base_dir)
        if not img_path:
            continue
        pix = QPixmap(str(img_path)).scaled(
            *THREE_HEAD_COMPONENT_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap(x, y, pix)

    painter.end()
    return canvas


def _compose_stacked_plant(components: list[str], img_dir: Path, base_dir: Path) -> QPixmap | None:

    canvas = QPixmap(100, 140)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)

    base_path = img_dir / "basic.png"
    if base_path.exists():
        base = QPixmap(str(base_path))
        painter.drawPixmap((100 - base.width()) // 2, 100, base)

    y_offset = 75
    for comp_name in reversed(components):
        img_path = component_image_path(comp_name, base_dir)
        if not img_path:
            continue
        pix = QPixmap(str(img_path))
        x = (100 - pix.width()) // 2
        painter.drawPixmap(x, y_offset, pix)
        y_offset -= pix.height() // 3

    painter.end()
    return canvas
