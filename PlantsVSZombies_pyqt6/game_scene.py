from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QImage, QMovie, QPainter, QPixmap
from PyQt6.QtWidgets import QLabel, QWidget

from seed import Seed
from sun import MySun
from ui_helpers import ImageButton, ImageDialog, asset
from zombies import Zombie, make_zombie


class GameScene(QWidget):
    main_menu = pyqtSignal()
    menu_clicked = pyqtSignal()

    def __init__(self, base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.setFixedSize(960, 720)

        self.sun_num = 100
        self.sun_sequence = [50, 100, 50, 25, 200]
        self.cooldown_sequence = [7500, 7500, 30000, 30000, 7500]
        self.name_sequence = ["SunFlower", "Peashooter", "WallNut", "PotatoMine", "Repeater"]
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

        self._build_hud()
        self.monitor_timer = self._timer(10, self.monitor_zombies)
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
            seed = Seed(
                self.base_dir,
                self.cooldown_sequence[i],
                self.sun_sequence[i],
                asset(self.base_dir, "res", f"{self.name_sequence[i]}.png"),
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
            if self.visited(event.position().x(), event.position().y()):
                plant_type = seed_index + 1
                self.create_plant(plant_type)
                self.born(plant_type)
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
                self.plt_hp[i][j] = 0

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
        if plant_type == 3:
            return
        label = QLabel(self)
        label.resize(63, 70)
        label.move(px - 5, py - 5)
        gif_name = {
            1: "SunFlower.gif",
            2: "Peashooter.gif",
            4: "PotatoMine1.gif",
            5: "Repeater.gif",
        }[plant_type]
        if plant_type == 4:
            label.resize(74, 53)
            label.move(px - 5, py + 10)
        movie = QMovie(asset(self.base_dir, "plantimages", gif_name), parent=label)
        label.setMovie(movie)
        label.setScaledContents(True)
        movie.start()
        label.show()
        self.pic[self.clix][self.cliy] = label

    def born(self, plant_type: int) -> None:
        self.map[self.clix][self.cliy] = plant_type
        if plant_type == 1:
            self.born_sunflower()
        elif plant_type == 2:
            self.born_peashooter(repeater=False)
        elif plant_type == 3:
            self.born_wallnut()
        elif plant_type == 4:
            self.born_potato()
        elif plant_type == 5:
            self.born_peashooter(repeater=True)

    def plant_death_timer(self, cx: int, cy: int, on_death=None) -> QTimer:
        timer = self._timer(33, lambda: None)
        timer.timeout.disconnect()

        def check() -> None:
            if self.plt_hp[cx][cy] <= 0:
                timer.stop()
                self.plt_hp[cx][cy] = 0
                self.map[cx][cy] = 0
                if on_death:
                    on_death()
                if self.pic[cx][cy]:
                    self.pic[cx][cy].deleteLater()
                    self.pic[cx][cy] = None

        timer.timeout.connect(check)
        return timer

    def born_sunflower(self) -> None:
        self.plt_hp[self.clix][self.cliy] = 300
        xx, yy, cx, cy = self.xtrans(), self.ytrans(), self.clix, self.cliy
        sun_timer = self._timer(10000, lambda: self.create_sun(xx, yy))
        self.plant_death_timer(cx, cy, sun_timer.stop)

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

    def born_peashooter(self, repeater: bool) -> None:
        self.plt_hp[self.clix][self.cliy] = 300
        xx, yy, cx, cy = self.xtrans(), self.ytrans(), self.clix, self.cliy

        def shoot_tick() -> None:
            if self.pea_detect(xx, cy):
                self.launch_pea(xx, yy, cy)
                if repeater:
                    QTimer.singleShot(300, lambda: self.launch_pea(xx, yy, cy))

        shoot_timer = self._timer(2000, shoot_tick)
        self.plant_death_timer(cx, cy, shoot_timer.stop)

    def launch_pea(self, xx: int, yy: int, cy: int) -> None:
        pea = QLabel(self)
        pea.resize(25, 25)
        pea.move(xx + 40, yy + 2)
        pea.setPixmap(QPixmap(asset(self.base_dir, "plantimages", "Pea.png")))
        pea.show()
        timer = self._timer(33, lambda: None)
        timer.timeout.disconnect()

        def step() -> None:
            pea.move(pea.x() + 10, pea.y())
            if pea.x() > 1000 or self.hit(pea.x(), cy):
                timer.stop()
                pea.deleteLater()

        timer.timeout.connect(step)

    def born_wallnut(self) -> None:
        px, py, cx, cy = self.xtrans(), self.ytrans(), self.clix, self.cliy
        self.plt_hp[cx][cy] = 4000
        label = self.set_plant_movie("WallNut.gif", px - 5, py - 5, 63, 70)
        self.pic[cx][cy] = label
        state = {"value": 1}

        def check() -> None:
            hp = self.plt_hp[cx][cy]
            if hp <= 0:
                timer.stop()
                self.map[cx][cy] = 0
                label.deleteLater()
            elif 1333 <= hp <= 2666 and state["value"] == 1:
                state["value"] = 2
                self.replace_pic(cx, cy, "WallNut1.gif", px - 5, py - 5, 63, 70)
            elif hp < 1333 and state["value"] == 2:
                state["value"] = 3
                self.replace_pic(cx, cy, "WallNut2.gif", px - 5, py - 5, 63, 70)

        timer = self._timer(33, check)

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

    def born_potato(self) -> None:
        self.plt_hp[self.clix][self.cliy] = 300
        xx, yy, cx, cy = self.xtrans(), self.ytrans(), self.clix, self.cliy
        death = self.plant_death_timer(cx, cy)

        def mature() -> None:
            if self.map[cx][cy] != 4:
                return
            if self.pic[cx][cy]:
                self.pic[cx][cy].deleteLater()
            self.pic[cx][cy] = self.set_plant_movie("PotatoMine.gif", xx - 5, yy + 10, 74, 53)
            self.plt_hp[cx][cy] = 50000
            death.stop()
            boom_timer = self._timer(33, lambda: None)
            boom_timer.timeout.disconnect()

            def boom_check() -> None:
                if self.potato_detect(xx, cy):
                    boom_timer.stop()
                    self.plt_hp[cx][cy] = 0
                    self.map[cx][cy] = 0
                    if self.pic[cx][cy]:
                        self.pic[cx][cy].deleteLater()
                        self.pic[cx][cy] = None
                    boom = self.set_plant_movie("PotatoMineBomb.gif", xx - 5, yy + 10, 74, 53)
                    QTimer.singleShot(1000, boom.deleteLater)

            boom_timer.timeout.connect(boom_check)

        QTimer.singleShot(15000, mature)

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

    def potato_detect(self, x: int, y: int) -> bool:
        for zombie in self.zombies:
            if self.raw_h[y - 1] == zombie.y() and abs(x - (zombie.x() + 200)) <= 200:
                zombie.get_hurt(5000, True)
                return True
        return False

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
