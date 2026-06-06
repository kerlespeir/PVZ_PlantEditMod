from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree


BUILTIN_PLUGIN_NAMES = {
    "DoubleSunShooter.dylib",
    "DoubleSunShooter.so",
    "Peashooter.dylib",
    "Peashooter.so",
    "PotatoMine.dylib",
    "PotatoMine.so",
    "Repeater.dylib",
    "Repeater.so",
    "SunFlower.dylib",
    "SunFlower.so",
    "WallNut.dylib",
    "WallNut.so",
    # 预编译杂交植物（无 PlantRecord，不可被清理）
    "PeaNut.dylib",
    "PeaNut.so",
    "SunNut.dylib",
    "SunNut.so",
    "MinePea.dylib",
    "MinePea.so",
    "SunFortress.dylib",
    "SunFortress.so",
}


# 内置植物的显示名 / ID / 卡片文件名。自定义植物不得与之冲突，清理逻辑也永不删除这些卡片。
BUILTIN_PLANT_NAMES = {
    "SunFlower",
    "Peashooter",
    "WallNut",
    "PotatoMine",
    "Repeater",
    "DoubleSunShooter",
}

BUILTIN_PLANT_IDS = {1, 2, 3, 4, 5}

# 预编译杂交植物 ID（无 PlantRecord，需要在图鉴中显示为可勾选条目）
BUILTIN_HYBRID_IDS = {100, 201, 202, 203, 205}

BUILTIN_CARD_NAMES = {f"{name}.png" for name in BUILTIN_PLANT_NAMES}


REGISTRATION_RE = re.compile(
    r'PVZ_REGISTER_HYBRID\(\s*(\w+)\s*,\s*(\d+)\s*,\s*"([^"]+)"\s*\)'
)


@dataclass
class PlantRecord:
    key: str
    mode: str
    plant_id: int
    display_name: str
    image_name: str
    card_name: str
    class_name: str
    folder: Path
    plant_source_path: Path
    components_source_path: Path | None
    plugin_path: Path


def drafts_dir(base_dir: Path) -> Path:
    path = base_dir / "user_plants" / "drafts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def library_dir(base_dir: Path) -> Path:
    path = base_dir / "user_plants" / "library"
    path.mkdir(parents=True, exist_ok=True)
    return path


def plugin_suffix() -> str:
    return ".dylib" if sys.platform == "darwin" else ".so"


def sanitize_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return cleaned or "plant"


def draft_plant_path(base_dir: Path, mode: str) -> Path:
    return drafts_dir(base_dir) / f"mode_{mode.lower()}_plant.cpp"


def draft_components_path(base_dir: Path) -> Path:
    return drafts_dir(base_dir) / "mode_b_components.h"


def plant_image_name(plant_id: int) -> str:
    return f"custom_{plant_id}.png"


def card_image_name(plant_id: int) -> str:
    # 卡片图使用独立命名空间，避免覆盖内置 res/<Name>.png
    return f"custom_{plant_id}_card.png"


def parse_registration(source: str) -> tuple[str, int, str] | None:
    match = REGISTRATION_RE.search(source)
    if not match:
        return None
    class_name, plant_id, display_name = match.groups()
    return class_name, int(plant_id), display_name


def normalize_plant_source(source: str) -> str:
    source = re.sub(r'#include\s+"[^"]+"', '#include "components.h"', source, count=1)
    source = re.sub(
        r'PVZ_REGISTER_HYBRID\(\s*(\w+)\s*,\s*(\d+)\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)',
        r'PVZ_REGISTER_HYBRID(\1, \2, "\3")',
        source,
    )
    return source


def normalize_components_source(source: str) -> str:
    if not source.strip():
        return source
    if "#include <string>" not in source:
        source = source.replace('#include <memory>', '#include <memory>\n#include <string>')
    source = source.replace(
        '#define PVZ_REGISTER_HYBRID(CLASS_NAME, PLANT_ID, DISPLAY_NAME, IMAGE_NAME) \\\n',
        '#define PVZ_REGISTER_HYBRID(CLASS_NAME, PLANT_ID, DISPLAY_NAME) \\\n',
    )
    source = source.replace(
        '    extern "C" PVZ_EXPORT const char* plant_image() { return IMAGE_NAME; } \\\n',
        '    extern "C" PVZ_EXPORT const char* plant_image() { static std::string name = std::string("custom_") + std::to_string(PLANT_ID) + ".png"; return name.c_str(); } \\\n',
    )
    return source


def load_record(base_dir: Path, key: str) -> PlantRecord | None:
    folder = library_dir(base_dir) / key
    metadata_path = folder / "metadata.json"
    if not metadata_path.exists():
        return None
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    plugin_dir = base_dir / "plugins" / "plants"
    return PlantRecord(
        key=data["key"],
        mode=data["mode"],
        plant_id=int(data["plant_id"]),
        display_name=data["display_name"],
        image_name=plant_image_name(int(data["plant_id"])),
        card_name=card_image_name(int(data["plant_id"])),
        class_name=data["class_name"],
        folder=folder,
        plant_source_path=folder / "plant.cpp",
        components_source_path=(folder / "components.h") if data["mode"] == "B" else None,
        plugin_path=plugin_dir / data["plugin_filename"],
    )


def load_records(base_dir: Path) -> list[PlantRecord]:
    records: list[PlantRecord] = []
    for folder in library_dir(base_dir).iterdir():
        if not folder.is_dir():
            continue
        record = load_record(base_dir, folder.name)
        if record:
            records.append(record)
    return sorted(records, key=lambda record: (record.plant_id, record.display_name.lower(), record.key))


def plant_id_in_use(base_dir: Path, plant_id: int, except_key: str | None = None) -> PlantRecord | None:
    for record in load_records(base_dir):
        if record.plant_id == plant_id and record.key != except_key:
            return record
    return None


def create_or_update_record(
    base_dir: Path,
    mode: str,
    plant_source: str,
    components_source: str | None,
    existing_key: str | None = None,
) -> PlantRecord:
    registration = parse_registration(plant_source)
    if not registration:
        raise ValueError("未找到 PVZ_REGISTER_HYBRID 宏")

    class_name, plant_id, display_name = registration
    if plant_id in BUILTIN_PLANT_IDS:
        raise ValueError(f"植物 ID {plant_id} 是内置植物保留 ID，请改用其他 ID")
    if display_name in BUILTIN_PLANT_NAMES:
        raise ValueError(f'显示名 "{display_name}" 与内置植物重名，请改用其他名称')
    duplicate = plant_id_in_use(base_dir, plant_id, except_key=existing_key)
    if duplicate:
        raise ValueError(f"植物 ID {plant_id} 已被 {duplicate.display_name} 占用")

    key = existing_key or f"{plant_id}_{sanitize_name(display_name)}"
    folder = library_dir(base_dir) / key
    folder.mkdir(parents=True, exist_ok=True)

    normalized_source = normalize_plant_source(plant_source)
    plant_source_path = folder / "plant.cpp"
    plant_source_path.write_text(normalized_source, encoding="utf-8")

    components_source_path = folder / "components.h" if mode == "B" else None
    if components_source_path and components_source is not None:
        components_source_path.write_text(normalize_components_source(components_source), encoding="utf-8")
    elif components_source_path and not components_source_path.exists():
        components_source_path.write_text(normalize_components_source(""), encoding="utf-8")

    plugin_filename = f"{key}{plugin_suffix()}"
    metadata = {
        "key": key,
        "mode": mode,
        "plant_id": plant_id,
        "display_name": display_name,
        "image_name": plant_image_name(plant_id),
        "card_name": card_image_name(plant_id),
        "class_name": class_name,
        "plugin_filename": plugin_filename,
    }
    (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    return PlantRecord(
        key=key,
        mode=mode,
        plant_id=plant_id,
        display_name=display_name,
        image_name=plant_image_name(plant_id),
        card_name=card_image_name(plant_id),
        class_name=class_name,
        folder=folder,
        plant_source_path=plant_source_path,
        components_source_path=components_source_path,
        plugin_path=base_dir / "plugins" / "plants" / plugin_filename,
    )


def delete_record(base_dir: Path, key: str) -> None:
    record = load_record(base_dir, key)
    if not record:
        return
    if record.plugin_path.exists():
        record.plugin_path.unlink(missing_ok=True)
    card_path = base_dir / "res" / record.card_name
    plant_image_path = base_dir / "plantimages" / record.image_name
    # 仅删除命名空间隔离的自定义卡片，绝不删除内置卡片
    if card_path.name not in BUILTIN_CARD_NAMES:
        card_path.unlink(missing_ok=True)
    plant_image_path.unlink(missing_ok=True)
    rmtree(record.folder, ignore_errors=True)


# ── 植物选中状态持久化 ──────────────────────────────────────────────

SELECTED_FILE_NAME = "selected_plants.json"


def _selected_path(base_dir: Path) -> Path:
    return base_dir / "user_plants" / SELECTED_FILE_NAME


def load_selected_plants(base_dir: Path) -> set[int] | None:
    """返回用户勾选的植物 ID 集合。文件不存在时返回 None（视作全部选中）。"""
    path = _selected_path(base_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {int(x) for x in data if isinstance(x, (int, float))}
    except (json.JSONDecodeError, ValueError):
        return None


def save_selected_plants(base_dir: Path, selected: set[int]) -> None:
    path = _selected_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(selected), ensure_ascii=False, indent=2), encoding="utf-8")


def cleanup_orphan_custom_assets(base_dir: Path) -> None:
    valid_records = load_records(base_dir)
    valid_plugin_names = {record.plugin_path.name for record in valid_records}
    valid_card_names = {record.card_name for record in valid_records}
    valid_plant_image_names = {record.image_name for record in valid_records}

    # 预编译杂交植物（无 PlantRecord）的贴图也受保护
    for hid in BUILTIN_HYBRID_IDS:
        valid_card_names.add(f"custom_{hid}_card.png")
        valid_plant_image_names.add(f"custom_{hid}.png")

    plugin_dir = base_dir / "plugins" / "plants"
    if plugin_dir.exists():
        for path in plugin_dir.iterdir():
            if path.name in BUILTIN_PLUGIN_NAMES:
                continue
            if path.suffix not in {".dylib", ".so", ".dll"}:
                continue
            if path.name not in valid_plugin_names:
                path.unlink(missing_ok=True)

    res_dir = base_dir / "res"
    if res_dir.exists():
        for path in res_dir.iterdir():
            if path.suffix.lower() != ".png":
                continue
            if path.name in BUILTIN_CARD_NAMES:
                continue  # 内置卡片永不清理
            # 自定义卡片统一为 custom_<ID>_card.png；孤儿即删
            if path.name.startswith("custom_") and path.name.endswith("_card.png") and path.name not in valid_card_names:
                path.unlink(missing_ok=True)

    plantimages_dir = base_dir / "plantimages"
    if plantimages_dir.exists():
        for path in plantimages_dir.iterdir():
            if path.suffix.lower() != ".png":
                continue
            if path.name.startswith("custom_") and not path.name.endswith("_card.png") and path.name not in valid_plant_image_names:
                path.unlink(missing_ok=True)
