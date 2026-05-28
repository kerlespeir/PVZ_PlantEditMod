from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap


COMPONENT_IMAGE_MAP = {
    "PeaHead": "Picture1.png",
    "SunHead": "Picture2.png",
    "WallNutHead": "Picture3.png",
    "PotatoMineHead": "Picture3.png",
}


def compose_plant_image(components: list[str], base_dir: Path) -> QPixmap | None:
    img_dir = base_dir / "components_images"
    if not img_dir.exists():
        return None

    canvas = QPixmap(100, 140)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)

    base_path = img_dir / "basic.png"
    if base_path.exists():
        base = QPixmap(str(base_path))
        painter.drawPixmap((100 - base.width()) // 2, 100, base)

    y_offset = 75
    for comp_name in reversed(components):
        img_file = COMPONENT_IMAGE_MAP.get(comp_name)
        if not img_file:
            continue
        img_path = img_dir / img_file
        if not img_path.exists():
            continue
        pix = QPixmap(str(img_path))
        x = (100 - pix.width()) // 2
        painter.drawPixmap(x, y_offset, pix)
        y_offset -= pix.height() // 3

    painter.end()
    return canvas
