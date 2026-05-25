# C++ Plant API

Python 负责游戏引擎、PyQt 显示、僵尸、子弹、阳光和对象回收。C++ 只负责植物行为。每个 C++ 植物继承 `Plant`，实现 `Update(GameAPI& api)`，并通过 `GameAPI` 查询状态或发出动作。

## 文件布局

- API 头文件：`PlantsVSZombies_pyqt6/cpp_api/pvz_api.h`
- 内置植物源码：`PlantsVSZombies_pyqt6/cpp_plants/*.cpp`
- 动态库输出目录：`PlantsVSZombies_pyqt6/plugins/plants/`
- 构建脚本：`PlantsVSZombies_pyqt6/build_cpp_plants.py`

## 坐标

API 使用 `row, col`：

- `row`: 1 到 5，从上到下。
- `col`: 1 到 9，从左到右。

`Plant` 基类已经保存了当前植物的 `row`、`col` 和 `hp`。

## 生命周期

每个游戏 tick 约为 10ms。Python 在每个 tick 中：

1. 把 Python 侧血量同步到 C++ 植物对象的 `hp`。
2. 调用 `plant->Update(api)`。
3. 读取 C++ 植物对象的 `hp`，同步回 Python。
4. 如果 `hp <= 0`，Python 负责回收植物。

C++ 不应该保存 Python 或 Qt 指针，也不需要释放任何 Python 对象。

## 最小植物示例

```cpp
#include "../cpp_api/pvz_api.h"

class DoubleSunShooter : public Plant {
private:
    int timer = 0;

public:
    DoubleSunShooter(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;

        if (timer % 300 == 0) {
            api.raise_sun(row, col);
        }

        if (timer % 100 == 0 && api.if_Zombies_ahead(row, col)) {
            api.shoot_pea(row, col, 2);
        }

        if (api.if_Zombies_touch(row, col) && hp <= 50) {
            api.explode(row, col);
            hp = 0;
        }
    }
};

PVZ_REGISTER_PLANT(DoubleSunShooter, 100, "DoubleSunShooter", "Repeater.gif", 300, 7500)
```

## 注册宏

每个插件 `.cpp` 最后调用：

```cpp
PVZ_REGISTER_PLANT(ClassName, plant_id, "Name", "Image.gif", sun_cost, cooldown_ms)
```

- `plant_id`: 植物类型 ID。内置植物使用 1 到 5。
- `Name`: 植物名，也用于卡片图片 `res/Name.png`。
- `Image.gif`: 初始动画，位于 `plantimages/`。
- `sun_cost`: 阳光价格。
- `cooldown_ms`: 卡片冷却毫秒数。

## 只读 API

```cpp
int get_time();
int get_sun();
int get_hp(int row, int col);
int get_zombie_count(int row);
int count_zombies_ahead(int row, int col);
int nearest_zombie_x(int row, int col);
bool if_Zombies_ahead(int row, int col);
bool if_Zombies_touch(int row, int col);
bool is_cell_empty(int row, int col);
```

说明：

- `get_time()` 返回游戏 tick 数。
- `if_Zombies_ahead()` 判断同一行、当前格右侧是否有活僵尸。
- `if_Zombies_touch()` 判断僵尸是否接触当前格。
- `nearest_zombie_x()` 没有目标时返回 `-1`。

## 动作 API

```cpp
void shoot_pea(int row, int col, int number = 1);
void shoot_snow_pea(int row, int col, int number = 1);
void explode(int row, int col);
void explode_area(int row, int col, int radius, int damage);
void raise_sun(int row, int col);
void change_animation(int row, int col, const char* animation_name);
void set_hp(int row, int col, int hp);
void damage_self(int row, int col, int amount);
```

说明：

- `shoot_pea(..., 2)` 会发射双发豌豆，第二发延迟约 300ms。
- `explode()` 等价于一个适合土豆雷的单行爆炸。
- `explode_area()` 的 `radius` 以格为粗略单位。
- `change_animation()` 的动画文件从 `plantimages/` 读取。
- 也可以直接修改当前植物的 `hp` 字段；Python 会在本 tick 后同步。

## 构建

```bash
cd /Users/css/Documents/科研/PVZ
python3 PlantsVSZombies_pyqt6/build_cpp_plants.py
```

如果系统有 CMake，会使用 CMake；否则使用 `clang++` / `g++` 直接编译。

## 内置植物

- `SunFlower.cpp`: 每 1000 tick 生成阳光。
- `Peashooter.cpp`: 每 200 tick 检查前方僵尸并发射 1 发豌豆。
- `WallNut.cpp`: 高血量，按血量切换受损动画。
- `PotatoMine.cpp`: 1500 tick 后成熟，接触僵尸时爆炸。
- `Repeater.cpp`: 每 200 tick 检查前方僵尸并发射 2 发豌豆。
