from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass
from pathlib import Path


GET_TIME = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
GET_SUN = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)
GET_HP = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
GET_ZOMBIE_COUNT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int)
COUNT_ZOMBIES_AHEAD = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
NEAREST_ZOMBIE_X = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
BOOL_ROW_COL = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
ACTION_ROW_COL_NUMBER = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int)
ACTION_ROW_COL = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
ACTION_EXPLODE_AREA = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
ACTION_ANIMATION = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_char_p)


class PVZGameAPI(ctypes.Structure):
    _fields_ = [
        ("ctx", ctypes.c_void_p),
        ("get_time", GET_TIME),
        ("get_sun", GET_SUN),
        ("get_hp", GET_HP),
        ("get_zombie_count", GET_ZOMBIE_COUNT),
        ("count_zombies_ahead", COUNT_ZOMBIES_AHEAD),
        ("nearest_zombie_x", NEAREST_ZOMBIE_X),
        ("if_zombies_ahead", BOOL_ROW_COL),
        ("if_zombies_touch", BOOL_ROW_COL),
        ("is_cell_empty", BOOL_ROW_COL),
        ("shoot_pea", ACTION_ROW_COL_NUMBER),
        ("shoot_snow_pea", ACTION_ROW_COL_NUMBER),
        ("explode", ACTION_ROW_COL),
        ("explode_area", ACTION_EXPLODE_AREA),
        ("raise_sun", ACTION_ROW_COL),
        ("change_animation", ACTION_ANIMATION),
        ("set_hp", ACTION_ROW_COL_NUMBER),
        ("damage_self", ACTION_ROW_COL_NUMBER),
    ]


@dataclass(frozen=True)
class PlantPlugin:
    path: Path
    plant_id: int
    name: str
    image: str
    sun_cost: int
    cooldown_ms: int
    lib: ctypes.CDLL

    def create(self, row: int, col: int) -> ctypes.c_void_p:
        return ctypes.c_void_p(self.lib.create_plant(row, col))

    def destroy(self, handle: ctypes.c_void_p) -> None:
        self.lib.destroy_plant(handle)

    def update(self, handle: ctypes.c_void_p, api: PVZGameAPI) -> None:
        self.lib.update_plant(handle, ctypes.byref(api))

    def get_hp(self, handle: ctypes.c_void_p) -> int:
        return int(self.lib.get_plant_hp(handle))

    def set_hp(self, handle: ctypes.c_void_p, hp: int) -> None:
        self.lib.set_plant_hp(handle, int(hp))


@dataclass
class PlantInstance:
    plugin: PlantPlugin
    handle: ctypes.c_void_p
    row: int
    col: int
    plant_id: int
    image: str

    @property
    def hp(self) -> int:
        return self.plugin.get_hp(self.handle)

    def set_hp(self, hp: int) -> None:
        self.plugin.set_hp(self.handle, hp)

    def update(self, api: PVZGameAPI) -> None:
        self.plugin.update(self.handle, api)

    def destroy(self) -> None:
        if self.handle:
            self.plugin.destroy(self.handle)
            self.handle = ctypes.c_void_p()


class CppPlantLoader:
    def __init__(self, plugin_dir: Path) -> None:
        self.plugin_dir = plugin_dir
        self.plugins_by_id: dict[int, PlantPlugin] = {}

    def load_all(self) -> dict[int, PlantPlugin]:
        suffixes = {".dll"} if sys.platform == "win32" else {".dylib", ".so"}
        if not self.plugin_dir.exists():
            return self.plugins_by_id
        self.plugins_by_id = {}
        for path in sorted(self.plugin_dir.iterdir()):
            if path.suffix not in suffixes:
                continue
            plugin = self._load_plugin(path)
            current = self.plugins_by_id.get(plugin.plant_id)
            if current is None or path.stat().st_mtime >= current.path.stat().st_mtime:
                self.plugins_by_id[plugin.plant_id] = plugin
        return self.plugins_by_id

    def _load_plugin(self, path: Path) -> PlantPlugin:
        lib = ctypes.CDLL(str(path))
        lib.create_plant.argtypes = [ctypes.c_int, ctypes.c_int]
        lib.create_plant.restype = ctypes.c_void_p
        lib.destroy_plant.argtypes = [ctypes.c_void_p]
        lib.destroy_plant.restype = None
        lib.update_plant.argtypes = [ctypes.c_void_p, ctypes.POINTER(PVZGameAPI)]
        lib.update_plant.restype = None
        lib.get_plant_hp.argtypes = [ctypes.c_void_p]
        lib.get_plant_hp.restype = ctypes.c_int
        lib.set_plant_hp.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.set_plant_hp.restype = None
        lib.plant_id.argtypes = []
        lib.plant_id.restype = ctypes.c_int
        lib.plant_name.argtypes = []
        lib.plant_name.restype = ctypes.c_char_p
        lib.plant_image.argtypes = []
        lib.plant_image.restype = ctypes.c_char_p
        lib.plant_sun_cost.argtypes = []
        lib.plant_sun_cost.restype = ctypes.c_int
        lib.plant_cooldown_ms.argtypes = []
        lib.plant_cooldown_ms.restype = ctypes.c_int

        return PlantPlugin(
            path=path,
            plant_id=int(lib.plant_id()),
            name=lib.plant_name().decode("utf-8"),
            image=lib.plant_image().decode("utf-8"),
            sun_cost=int(lib.plant_sun_cost()),
            cooldown_ms=int(lib.plant_cooldown_ms()),
            lib=lib,
        )


class GameAPIAdapter:
    def __init__(self, scene) -> None:
        self.scene = scene
        self._callbacks = {
            "get_time": GET_TIME(lambda ctx: self.scene.game_time),
            "get_sun": GET_SUN(lambda ctx: self.scene.sun_num),
            "get_hp": GET_HP(lambda ctx, row, col: self.scene.api_get_hp(row, col)),
            "get_zombie_count": GET_ZOMBIE_COUNT(lambda ctx, row: self.scene.api_get_zombie_count(row)),
            "count_zombies_ahead": COUNT_ZOMBIES_AHEAD(lambda ctx, row, col: self.scene.api_count_zombies_ahead(row, col)),
            "nearest_zombie_x": NEAREST_ZOMBIE_X(lambda ctx, row, col: self.scene.api_nearest_zombie_x(row, col)),
            "if_zombies_ahead": BOOL_ROW_COL(lambda ctx, row, col: self.scene.api_if_zombies_ahead(row, col)),
            "if_zombies_touch": BOOL_ROW_COL(lambda ctx, row, col: self.scene.api_if_zombies_touch(row, col)),
            "is_cell_empty": BOOL_ROW_COL(lambda ctx, row, col: self.scene.api_is_cell_empty(row, col)),
            "shoot_pea": ACTION_ROW_COL_NUMBER(lambda ctx, row, col, number: self.scene.api_shoot_pea(row, col, number, snow=False)),
            "shoot_snow_pea": ACTION_ROW_COL_NUMBER(lambda ctx, row, col, number: self.scene.api_shoot_pea(row, col, number, snow=True)),
            "explode": ACTION_ROW_COL(lambda ctx, row, col: self.scene.api_explode(row, col)),
            "explode_area": ACTION_EXPLODE_AREA(lambda ctx, row, col, radius, damage: self.scene.api_explode_area(row, col, radius, damage)),
            "raise_sun": ACTION_ROW_COL(lambda ctx, row, col: self.scene.api_raise_sun(row, col)),
            "change_animation": ACTION_ANIMATION(lambda ctx, row, col, name: self.scene.api_change_animation(row, col, name.decode("utf-8"))),
            "set_hp": ACTION_ROW_COL_NUMBER(lambda ctx, row, col, hp: self.scene.api_set_hp(row, col, hp)),
            "damage_self": ACTION_ROW_COL_NUMBER(lambda ctx, row, col, amount: self.scene.api_damage_self(row, col, amount)),
        }
        self.c_api = PVZGameAPI(
            None,
            self._callbacks["get_time"],
            self._callbacks["get_sun"],
            self._callbacks["get_hp"],
            self._callbacks["get_zombie_count"],
            self._callbacks["count_zombies_ahead"],
            self._callbacks["nearest_zombie_x"],
            self._callbacks["if_zombies_ahead"],
            self._callbacks["if_zombies_touch"],
            self._callbacks["is_cell_empty"],
            self._callbacks["shoot_pea"],
            self._callbacks["shoot_snow_pea"],
            self._callbacks["explode"],
            self._callbacks["explode_area"],
            self._callbacks["raise_sun"],
            self._callbacks["change_animation"],
            self._callbacks["set_hp"],
            self._callbacks["damage_self"],
        )
