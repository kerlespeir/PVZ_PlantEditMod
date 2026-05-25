from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QImage, QMovie, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from seed import Seed
from sun import MySun
from ui_helpers import ImageButton, ImageDialog, asset
from zombies import Zombie, make_zombie
from plants.cpp_bridge import CppPlantLoader, GameAPIAdapter, PlantInstance


class GameScene(QWidget):
    main_menu = pyqtSignal()
    menu_clicked = pyqtSignal()

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.setFixedSize(960, 720)

        self.sun_num = 100
        self.default_sun_sequence = [50, 100, 50, 25, 200]
        self.default_cooldown_sequence = [7500, 7500, 30000, 30000, 7500]
        self.default_name_sequence = ["SunFlower", "Peashooter", "WallNut", "PotatoMine", "Repeater"]
        self.is_planting = -1

        self.fc_raw = [0, 3, 2, 1, 2, 4, 0, 3, 1, 4]
        self.fc_zombie = [1, 2, 1, 3, 1, 1, 2, 3, 1, 4]
        self.zcnt = 0
        self.max_number = 20
        self.raw_h = [50, 170, 290, 400, 520]
        self.zombies: list[Zombie] = []

        self.map = [[0 for _ in range(6)] for _ in range(10)]
        self.plt_hp = [[0 for _ in range(6)] for _ in range(10)]
        self.pic: list[list[QLabel | None]] = [[None for _ in range(6)] for _ in range(10)]
        self.clix = 0
        self.cliy = 0
        self.xlimit = [56, 151, 243, 346, 437, 540, 636, 730, 815, 919]
        self.ylimit = [98, 217, 328, 446, 567, 680]
        self._timers: list[QTimer] = []
        self._game_over = False
        self.game_time = 0
        self.plant_instances: dict[tuple[int, int], PlantInstance] = {}
        self.plant_loader = CppPlantLoader(self.base_dir / "plugins" / "plants")
        self.plant_plugins = self.plant_loader.load_all()
        self.api_adapter = GameAPIAdapter(self)

        self._build_hud()
        self.monitor_timer = self._timer(10, self.game_tick)
        self.create_timer = self._timer(8000, self.create_zombie_tick)
        self.monitor_timer.stop()
        self.create_timer.stop()

    def _timer(self, interval: int, slot) -> QTimer:
        timer = QTimer(self)
        timer.timeout.connect(slot)
        timer.start(interval)
        self._timers.append(timer)
        return timer

    def _build_hud(self) -> None:
        bank_pix = QPixmap(asset(self.base_dir, "res", "Shop.png"))
        bank = QLabel(self)
        bank.resize(bank_pix.size())
        bank.setPixmap(bank_pix)
        bank.move(200, 0)
        bank.show()

        self.sun_label = QLabel(str(self.sun_num), self)
        self.sun_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sun_label.move(bank.x() + 27, 65)
        self.sun_label.resize(50, 20)
        self.sun_label.show()

        self.seed_bank: list[Seed] = []
        for i in range(5):
            plant_type = i + 1
            plugin = self.plant_plugins.get(plant_type)
            sun_cost = plugin.sun_cost if plugin else self.default_sun_sequence[i]
            cooldown = plugin.cooldown_ms if plugin else self.default_cooldown_sequence[i]
            plant_name = plugin.name if plugin else self.default_name_sequence[i]
            seed = Seed(
                self.base_dir,
                cooldown,
                sun_cost,
                asset(self.base_dir, "res", f"{plant_name}.png"),
                bank,
            )
            seed.checksun(self.sun_num)
            seed.clicked.connect(lambda checked=False, idx=i: self.select_seed(idx))
            seed.check.connect(lambda idx=i: self.seed_bank[idx].checksun(self.sun_num))
            seed.move(67 + 55 * i, 5)
            seed.show()
            self.seed_bank.append(seed)

        self.shovel = ImageButton(self.base_dir, asset(self.base_dir, "res", "ShovelBank.png"), parent=self, scale=1.0)
        shovel_pix = QPixmap(asset(self.base_dir, "res", "Shovel.png"))
        self.shovel_cursor = shovel_pix.scaled(int(shovel_pix.width() * 0.65), int(shovel_pix.height() * 0.65))
        self.shovel.move(bank.x() + bank.width() + 20, 0)
        self.shovel.clicked.connect(self.select_shovel)
        self.shovel.show()

        menu = ImageButton(self.base_dir, asset(self.base_dir, "res", "MenuButton.png"), parent=self)
        menu.move(self.width() - menu.width(), 0)
        menu.clicked.connect(lambda checked=False: self.menu_clicked.emit())
        menu.show()

    def start_game(self) -> None:
        ready = QLabel(self)
        mask = QLabel(self)
        mask.setFixedSize(self.size())
        mask.show()
        ready.show()
        self._show_start_frame(ready, "StartReady.png")
        QTimer.singleShot(620, lambda: self._show_start_frame(ready, "StartSet.png"))
        QTimer.singleShot(1240, lambda: self._show_start_frame(ready, "StartPlant.png"))
        QTimer.singleShot(2040, lambda: self._begin_after_start(ready, mask))

    def _show_start_frame(self, label: QLabel, image_name: str) -> None:
        pix = QPixmap(asset(self.base_dir, "res", image_name))
        label.resize(pix.size())
        label.setPixmap(pix)
        label.move((self.width() - label.width()) // 2, (self.height() - label.height()) // 2)
        label.raise_()

    def _begin_after_start(self, ready: QLabel, mask: QLabel) -> None:
        ready.deleteLater()
        mask.deleteLater()
        self.monitor_timer.start(10)
        QTimer.singleShot(800, lambda: None)
        self.create_timer.start(8000)

    def select_seed(self, idx: int) -> None:
        if self.sun_num < self.seed_bank[idx].sun:
            return
        self.setCursor(QCursor(self.seed_bank[idx].plant_cursor))
        for seed in self.seed_bank:
            if not seed.in_cd:
                seed.checksun(self.sun_num)
        self.seed_bank[idx].mask1.show()
        self.is_planting = idx

    def select_shovel(self) -> None:
        self.setCursor(QCursor(self.shovel_cursor))
        self.is_planting = -2

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        bg = QImage(asset(self.base_dir, "res", "Background.jpg"))
        bg = bg.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawImage(-250, 0, bg)

    def mousePressEvent(self, event) -> None:
        if self.is_planting == -1:
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.RightButton:
            self.cancel_cursor()
            return
        if not QRect(60, 100, 860, 580).contains(event.pos()):
            return super().mousePressEvent(event)
        if self.is_planting >= 0:
            seed_index = self.is_planting
            if not self.visited(event.position().x(), event.position().y()):
                return super().mousePressEvent(event)
            plant_type = seed_index + 1
            if not self.born(plant_type):
                self.cancel_cursor()
                return
            self.sun_num -= self.seed_bank[seed_index].sun
            self.update_sun()
            self.seed_bank[seed_index].cdstart()
            self.cancel_cursor()
        else:
            self.cancel_cursor()
            i = 0
            j = 0
            while i < len(self.xlimit) and event.position().x() >= self.xlimit[i]:
                i += 1
            while j < len(self.ylimit) and event.position().y() >= self.ylimit[j]:
                j += 1
            if 0 <= i < 10 and 0 <= j < 6 and self.map[i][j]:
                self.remove_plant(i, j)

    def cancel_cursor(self) -> None:
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.is_planting >= 0:
            self.seed_bank[self.is_planting].checksun(self.sun_num)
        self.is_planting = -1

    def update_sun(self) -> None:
        self.sun_label.setText(str(self.sun_num))
        for seed in self.seed_bank:
            if not seed.in_cd:
                seed.checksun(self.sun_num)

    def visited(self, x: float, y: float) -> bool:
        f1 = f2 = False
        xx = yy = 0
        for i in range(9):
            if self.xlimit[i] <= x <= self.xlimit[i + 1]:
                xx = i + 1
                f1 = True
        for j in range(5):
            if self.ylimit[j] <= y <= self.ylimit[j + 1]:
                yy = j + 1
                f2 = True
        if f1 and f2 and self.map[xx][yy] == 0:
            self.clix = xx
            self.cliy = yy
            return True
        return False

    def xtrans(self) -> int:
        return {1: 70, 2: 165, 3: 265, 4: 360, 5: 455, 6: 555, 7: 650, 8: 745, 9: 845}[self.clix]

    def ytrans(self) -> int:
        return {1: 120, 2: 240, 3: 360, 4: 480, 5: 600}[self.cliy]

    def create_plant(self, plant_type: int) -> None:
        px = self.xtrans()
        py = self.ytrans()
        plugin = self.plant_plugins.get(plant_type)
        if not plugin:
            return
        label = QLabel(self)
        label.resize(63, 70)
        label.move(px - 5, py - 5)
        gif_name = plugin.image
        if plant_type == 4:
            label.resize(74, 53)
            label.move(px - 5, py + 10)
        movie = QMovie(asset(self.base_dir, "plantimages", gif_name), parent=label)
        label.setMovie(movie)
        label.setScaledContents(True)
        movie.start()
        label.show()
        self.pic[self.clix][self.cliy] = label

    def born(self, plant_type: int) -> bool:
        plugin = self.plant_plugins.get(plant_type)
        if not plugin:
            return False
        self.create_plant(plant_type)
        handle = plugin.create(self.cliy, self.clix)
        instance = PlantInstance(plugin, handle, self.cliy, self.clix, plant_type, plugin.image)
        self.plant_instances[(self.clix, self.cliy)] = instance
        self.map[self.clix][self.cliy] = plant_type
        self.plt_hp[self.clix][self.cliy] = instance.hp
        return True

    def create_sun(self, xx: int, yy: int) -> None:
        sun = MySun(self.base_dir, self)
        sun.move(xx + 10, yy + 15)
        sun.show()
        anime = QPropertyAnimation(sun, b"geometry", self)
        anime.setStartValue(QRect(xx + 10, yy - 15, sun.width(), sun.height()))
        anime.setEndValue(QRect(xx + 10, yy + 15, sun.width(), sun.height()))
        anime.setEasingCurve(QEasingCurve.Type.InBack)
        anime.setDuration(500)
        anime.start()
        sun._anime = anime
        sun.sun_collected.connect(lambda: self.collect_sun(sun))

    def collect_sun(self, sun: MySun) -> None:
        self.sun_num += 25
        self.update_sun()
        sun.hide()
        sun.deleteLater()

    def launch_pea(self, xx: int, yy: int, cy: int, snow: bool = False) -> None:
        pea = QLabel(self)
        pea.resize(25, 25)
        pea.move(xx + 40, yy + 2)
        pea.setPixmap(QPixmap(asset(self.base_dir, "plantimages", "PeaSnow.png" if snow else "Pea.png")))
        pea.show()
        timer = self._timer(33, lambda: None)
        timer.timeout.disconnect()

        def step() -> None:
            pea.move(pea.x() + 10, pea.y())
            if pea.x() > 1000 or self.hit(pea.x(), cy):
                timer.stop()
                pea.deleteLater()

        timer.timeout.connect(step)

    def game_tick(self) -> None:
        if self._game_over:
            return
        self.game_time += 1
        self.update_plants()
        self.monitor_zombies()

    def update_plants(self) -> None:
        for (col, row), plant in list(self.plant_instances.items()):
            if self.map[col][row] == 0 or self.plt_hp[col][row] <= 0:
                self.remove_plant(col, row)
                continue
            plant.set_hp(self.plt_hp[col][row])
            plant.update(self.api_adapter.c_api)
            if (col, row) not in self.plant_instances:
                continue
            hp = plant.hp
            self.plt_hp[col][row] = hp
            if hp <= 0:
                self.remove_plant(col, row)

    def remove_plant(self, col: int, row: int, delete_pic: bool = True) -> None:
        plant = self.plant_instances.pop((col, row), None)
        if plant:
            plant.destroy()
        self.plt_hp[col][row] = 0
        self.map[col][row] = 0
        if delete_pic and self.pic[col][row]:
            self.pic[col][row].deleteLater()
            self.pic[col][row] = None

    def cell_x(self, col: int) -> int:
        return {1: 70, 2: 165, 3: 265, 4: 360, 5: 455, 6: 555, 7: 650, 8: 745, 9: 845}[col]

    def cell_y(self, row: int) -> int:
        return {1: 120, 2: 240, 3: 360, 4: 480, 5: 600}[row]

    def valid_cell(self, row: int, col: int) -> bool:
        return 1 <= row <= 5 and 1 <= col <= 9

    def api_get_hp(self, row: int, col: int) -> int:
        if not self.valid_cell(row, col):
            return 0
        return self.plt_hp[col][row]

    def api_get_zombie_count(self, row: int) -> int:
        if not 1 <= row <= 5:
            return 0
        return sum(1 for zombie in self.zombies if zombie.y() == self.raw_h[row - 1] and zombie.hp > 0)

    def api_count_zombies_ahead(self, row: int, col: int) -> int:
        if not self.valid_cell(row, col):
            return 0
        x = self.cell_x(col)
        return sum(1 for zombie in self.zombies if zombie.y() == self.raw_h[row - 1] and zombie.x() + 100 > x and zombie.hp > 0)

    def api_nearest_zombie_x(self, row: int, col: int) -> int:
        if not self.valid_cell(row, col):
            return -1
        x = self.cell_x(col)
        candidates = [zombie.x() for zombie in self.zombies if zombie.y() == self.raw_h[row - 1] and zombie.x() + 100 > x and zombie.hp > 0]
        return min(candidates) if candidates else -1

    def api_if_zombies_ahead(self, row: int, col: int) -> bool:
        if not self.valid_cell(row, col):
            return False
        return self.pea_detect(self.cell_x(col), row)

    def api_if_zombies_touch(self, row: int, col: int) -> bool:
        if not self.valid_cell(row, col):
            return False
        x = self.cell_x(col)
        return any(
            zombie.y() == self.raw_h[row - 1]
            and zombie.hp > 0
            and (zombie.mx == col or abs(x - (zombie.x() + 200)) <= 90)
            for zombie in self.zombies
        )

    def api_is_cell_empty(self, row: int, col: int) -> bool:
        return self.valid_cell(row, col) and self.map[col][row] == 0

    def api_shoot_pea(self, row: int, col: int, number: int, snow: bool = False) -> None:
        if not self.valid_cell(row, col):
            return
        x, y = self.cell_x(col), self.cell_y(row)
        for idx in range(max(0, number)):
            QTimer.singleShot(300 * idx, lambda x=x, y=y, row=row, snow=snow: self.launch_pea(x, y, row, snow))

    def api_raise_sun(self, row: int, col: int) -> None:
        if self.valid_cell(row, col):
            self.create_sun(self.cell_x(col), self.cell_y(row))

    def api_change_animation(self, row: int, col: int, animation_name: str) -> None:
        if not self.valid_cell(row, col) or self.map[col][row] == 0:
            return
        x, y = self.cell_x(col), self.cell_y(row)
        width, height = (74, 53) if animation_name.startswith("PotatoMine") else (63, 70)
        y_offset = 10 if animation_name.startswith("PotatoMine") else -5
        self.replace_pic(col, row, animation_name, x - 5, y + y_offset, width, height)

    def api_set_hp(self, row: int, col: int, hp: int) -> None:
        if self.valid_cell(row, col):
            hp = max(0, hp)
            self.plt_hp[col][row] = hp
            plant = self.plant_instances.get((col, row))
            if plant:
                plant.set_hp(hp)

    def api_damage_self(self, row: int, col: int, amount: int) -> None:
        if self.valid_cell(row, col):
            self.api_set_hp(row, col, self.plt_hp[col][row] - max(0, amount))

    def api_explode(self, row: int, col: int) -> None:
        self.api_explode_area(row, col, 1, 5000)

    def api_explode_area(self, row: int, col: int, radius: int, damage: int) -> None:
        if not self.valid_cell(row, col):
            return
        x = self.cell_x(col)
        for zombie in self.zombies:
            same_row = zombie.y() == self.raw_h[row - 1]
            in_radius = abs(x - (zombie.x() + 200)) <= max(1, radius) * 200
            if same_row and in_radius:
                zombie.get_hurt(damage, True)
        y = self.cell_y(row)
        self.api_set_hp(row, col, 0)
        self.map[col][row] = 0
        if self.pic[col][row]:
            self.pic[col][row].deleteLater()
            self.pic[col][row] = None
        boom = self.set_plant_movie("PotatoMineBomb.gif", x - 5, y + 10, 74, 53)
        QTimer.singleShot(1000, boom.deleteLater)

    def set_plant_movie(self, gif: str, x: int, y: int, w: int, h: int) -> QLabel:
        label = QLabel(self)
        label.resize(w, h)
        label.move(x, y)
        movie = QMovie(asset(self.base_dir, "plantimages", gif), parent=label)
        label.setMovie(movie)
        label.setScaledContents(True)
        movie.start()
        label.show()
        return label

    def replace_pic(self, cx: int, cy: int, gif: str, x: int, y: int, w: int, h: int) -> None:
        if self.pic[cx][cy]:
            self.pic[cx][cy].deleteLater()
        self.pic[cx][cy] = self.set_plant_movie(gif, x, y, w, h)

    def born_zombie(self, number: int, raw: int) -> None:
        if len(self.zombies) >= self.max_number:
            return
        zombie = make_zombie(self.base_dir, number, self)
        zombie.move(900, self.raw_h[raw])
        zombie.resize(400, 160)
        zombie.walk()
        zombie.show()
        self.zombies.append(zombie)

    def create_zombie_tick(self) -> None:
        if self._game_over:
            return
        if self.zcnt == 50:
            if len(self.zombies) == 0:
                self.pwin()
            return
        self.born_zombie(self.fc_zombie[self.zcnt % 10], self.fc_raw[self.zcnt % 10])
        self.zcnt += 1

    def monitor_zombies(self) -> None:
        for zombie in list(self.zombies):
            if zombie.hp <= 0:
                zombie.die()
                if zombie.movie and zombie.movie.frameCount() == zombie.movie.currentFrameNumber() + 1:
                    self.zombies.remove(zombie)
                    zombie.deleteLater()
                continue
            if zombie.mx != 10 and self.plt_hp[zombie.mx][zombie.my] > 0:
                self.plt_hp[zombie.mx][zombie.my] -= 1
                if not zombie.if_eat:
                    zombie.eat()
            elif zombie.if_eat:
                zombie.walk()
            if zombie.x() <= -100:
                self.zwin()
                return

    def hit(self, x: int, y: int) -> bool:
        for zombie in self.zombies:
            if self.raw_h[y - 1] == zombie.y() and abs(x - (zombie.x() + 100)) <= 15:
                zombie.get_hurt(40)
                return True
        return False

    def pea_detect(self, x: int, y: int) -> bool:
        return any(self.raw_h[y - 1] == zombie.y() and zombie.x() + 100 > x for zombie in self.zombies)

    def pwin(self) -> None:
        if self._game_over:
            return
        self._game_over = True
        self.stop_spawn_and_monitor()
        trophy = ImageButton(self.base_dir, asset(self.base_dir, "res", "trophy.png"), parent=self)
        trophy.move((self.width() - trophy.width()) // 2, (self.height() - trophy.height()) // 2)
        trophy.show()
        trophy.clicked.connect(lambda: self.show_end_dialog("WinWindow.png"))

    def zwin(self) -> None:
        if self._game_over:
            return
        self._game_over = True
        self.stop_spawn_and_monitor()

        def show_lose_pic() -> None:
            lose_label = QLabel(self)
            lose_label.setPixmap(QPixmap(asset(self.base_dir, "res", "losePic.png")))
            lose_label.resize(self.size())
            lose_label.show()
            QTimer.singleShot(3800, lambda: self.show_end_dialog("loseWindow.png"))

        QTimer.singleShot(3800, show_lose_pic)

    def show_end_dialog(self, image_name: str) -> None:
        dialog = ImageDialog(asset(self.base_dir, "res", image_name), self)
        dialog.move((self.width() - dialog.width()) // 2, (self.height() - dialog.height()) // 2)
        yes = ImageButton(self.base_dir, asset(self.base_dir, "res", "yesButton2.png"), parent=dialog)
        yes.move((dialog.width() - yes.width()) // 2 - 5, 215)
        yes.clicked.connect(lambda checked=False: self.main_menu.emit())
        dialog.show()

    def stop_spawn_and_monitor(self) -> None:
        self.monitor_timer.stop()
        self.create_timer.stop()

    def stop_all(self) -> None:
        for timer in self._timers:
            timer.stop()
        for zombie in self.zombies:
            zombie.stop()
        for plant in list(self.plant_instances.values()):
            plant.destroy()
        self.plant_instances.clear()
