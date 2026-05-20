from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel, QWidget

from ui_helpers import asset


@dataclass
class ZombieSpec:
    hp: int
    walk_speed: int
    eat_speed: int
    hurt: int
    state: int
    walk_path: str
    eat_path: str
    die_path: str
    hp_ch: tuple[int, int, int] = (0, 0, 0)


class Zombie(QLabel):
    def __init__(self, base_dir: Path, spec: ZombieSpec, znumber: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_dir = base_dir
        self.hp = spec.hp
        self.walk_speed = spec.walk_speed
        self.eat_speed = spec.eat_speed
        self.hurt = spec.hurt
        self.state = spec.state
        self.znumber = znumber
        self.walk_path = spec.walk_path
        self.eat_path = spec.eat_path
        self.die_path = spec.die_path
        self.hp_ch = (0, *spec.hp_ch)
        self.mx = 10
        self.my = 0
        self.if_eat = False
        self.if_die = False
        self.movie: QMovie | None = None
        self.timer = QTimer(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def wm_x(self, x: int) -> int:
        bias = -20
        if x < 56 + bias:
            return 1
        if x < 151 + bias:
            return 2
        if x < 243 + bias:
            return 3
        if x < 346 + bias:
            return 4
        if x < 437 + bias:
            return 5
        if x < 540 + bias:
            return 6
        if x < 636 + bias:
            return 7
        if x < 730 + bias:
            return 8
        if x < 815 + bias:
            return 9
        return 10

    def z_change(self) -> None:
        if self.znumber == 2:
            if self.hp <= self.hp_ch[1] and self.state != 1:
                self.state = 1
                self.walk_path = asset(self.base_dir, "zombie", "ZombieWalk1.gif")
                self.eat_path = asset(self.base_dir, "zombie", "ZombieAttack.gif")
                self.change()
            elif self.hp <= self.hp_ch[2] and self.state != 2:
                self.state = 2
                self.walk_path = asset(self.base_dir, "zombie", "ConeZombieWalk3.gif")
                self.eat_path = asset(self.base_dir, "zombie", "ConeZombieAttack3.gif")
                self.change()
            elif self.hp <= self.hp_ch[3] and self.state != 3:
                self.state = 3
                self.walk_path = asset(self.base_dir, "zombie", "ConeZombieWalk2.gif")
                self.eat_path = asset(self.base_dir, "zombie", "ConeZombieAttack2.gif")
                self.change()
        elif self.znumber == 3:
            if self.hp <= self.hp_ch[1] and self.state != 1:
                self.state = 1
                self.walk_path = asset(self.base_dir, "zombie", "ZombieWalk1.gif")
                self.eat_path = asset(self.base_dir, "zombie", "ZombieAttack.gif")
                self.change()
            elif self.hp <= self.hp_ch[2] and self.state != 2:
                self.state = 2
                self.walk_path = asset(self.base_dir, "zombie", "BucketZombieWalk3.gif")
                self.eat_path = asset(self.base_dir, "zombie", "BucketZombieAttack3.gif")
                self.change()
            elif self.hp <= self.hp_ch[3] and self.state != 3:
                self.state = 3
                self.walk_path = asset(self.base_dir, "zombie", "BucketZombieWalk2(1).gif")
                self.eat_path = asset(self.base_dir, "zombie", "BucketZombieAttack2.gif")
                self.change()

    def _set_movie(self, path: str, speed: int, frame: int = 0) -> None:
        self.movie = QMovie(path, parent=self)
        self.movie.setSpeed(speed)
        self.setMovie(self.movie)
        self.movie.jumpToFrame(frame)
        self.movie.start()
        self.show()

    def change(self) -> None:
        frame = self.movie.currentFrameNumber() if self.movie else 0
        self._set_movie(self.eat_path if self.if_eat else self.walk_path, self.eat_speed // 10 if self.if_eat else self.walk_speed, frame)

    def _disconnect_timer(self) -> None:
        try:
            self.timer.timeout.disconnect()
        except TypeError:
            pass

    def walk(self) -> None:
        self.my = {50: 1, 170: 2, 290: 3, 400: 4}.get(self.y(), 5)
        self.if_eat = False
        frame = self.movie.currentFrameNumber() if self.movie else 0
        self._set_movie(self.walk_path, self.walk_speed, frame)
        self.timer.stop()
        self._disconnect_timer()
        self.timer.timeout.connect(self._walk_step)
        self.timer.start(100)

    def _walk_step(self) -> None:
        self.move(self.x() - self.walk_speed // 100, self.y())
        self.mx = self.wm_x(self.x() - self.walk_speed // 100)
        self.z_change()

    def eat(self) -> None:
        self.if_eat = True
        frame = self.movie.currentFrameNumber() if self.movie else 0
        self._set_movie(self.eat_path, self.eat_speed // 10, frame)
        self.timer.stop()
        self._disconnect_timer()
        self.timer.timeout.connect(self.z_change)
        self.timer.start(self.eat_speed)

    def die(self) -> None:
        if self.if_die:
            return
        self._set_movie(self.die_path, 100)
        self.if_die = True
        self.timer.stop()
        self._disconnect_timer()

    def get_hurt(self, attack: int, burn: bool = False) -> None:
        self.hp -= attack
        if self.hp <= 0 and burn:
            self.die_path = asset(self.base_dir, "zombie", "Burn.gif")

    def stop(self) -> None:
        if self.movie:
            self.movie.stop()
        self.timer.stop()


def make_zombie(base_dir: Path, number: int, parent: QWidget | None = None) -> Zombie:
    specs = {
        1: ZombieSpec(200, 150, 1000, 50, 1, asset(base_dir, "zombie", "ZombieWalk1.gif"), asset(base_dir, "zombie", "ZombieAttack.gif"), asset(base_dir, "zombie", "ZombieDie.gif")),
        2: ZombieSpec(570, 150, 1000, 50, 4, asset(base_dir, "zombie", "ConeZombieWalk.gif"), asset(base_dir, "zombie", "ConeZombieAttack.gif"), asset(base_dir, "zombie", "ZombieDie.gif"), (210, 330, 450)),
        3: ZombieSpec(1300, 150, 1000, 50, 4, asset(base_dir, "zombie", "BucketZombieWalk.gif"), asset(base_dir, "zombie", "BucketZombieAttack.gif"), asset(base_dir, "zombie", "ZombieDie.gif"), (300, 600, 900)),
        4: ZombieSpec(1600, 300, 1000, 50, 1, asset(base_dir, "zombie", "FootballZombieWalk.gif"), asset(base_dir, "zombie", "FootballZombieAttack.gif"), asset(base_dir, "zombie", "FootballZombieDie.gif"), (10000, 10000, 10000)),
    }
    return Zombie(base_dir, specs[number], number, parent)
