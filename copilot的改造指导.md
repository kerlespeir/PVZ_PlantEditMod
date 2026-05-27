# 改造指导

## 1. 先理解现有 PlantsVSZombies_pyqt6 的运行逻辑

从 game_scene.py 可以看到：

- 游戏时间推进由 `QTimer` 实现
  - `monitor_timer` 每 10ms 调用 `monitor_zombies`
  - `create_timer` 每 8000ms 调用 `create_zombie_tick`
  - 植物自身也用 `QTimer` 调度射击、产阳光、马铃薯地雷成熟等

- 资源/世界状态
  - `self.sun_num` 管理当前阳光数
  - `update_sun()` 负责 UI 更新和种子卡片可用性检查
  - `self.map`、`self.plt_hp` 管理格子占用和植物生命
  - `self.zombies` 管理僵尸列表

- 植物行为现在是“硬编码”
  - `born_sunflower()`
  - `born_peashooter()`
  - `born_wallnut()`
  - `born_potato()`
  - 每个植物直接在 Python 里创建定时器、创建 QLabel、检测僵尸、造成伤害

这说明：你想做的“C++ 植物编辑系统”并不是只改 components.cpp，而是要改造整个游戏中的“植物接口”。

---

## 2. 你当前 components.cpp 的问题

你现在的 components.cpp 只定义了：

- `Component` 基类
- `PeaHead` 派生类

但它目前还缺少：

- `Component::hurt` / `Component::step` 的实现
- `Component` 的 `virtual` 析构函数
- 与游戏世界的交互接口
- `Plant` 类
- 与 Python 侧桥接的导出接口

所以现在你遇到的“融合问题”，本质上是：

- 你写了组件，但还没有定义“植物如何使用组件”
- 你写了组件，但还没有定义“游戏世界如何调用组件”
- 你写了组件，但还没有定义“Python 与 C++ 之间的通道”

---

## 3. 推荐的改造路线

### 3.1 先从“接口层”开始设计

你要拆成两层：

- C++ 侧：`Component` 系统 + `Plant` 系统
- Python 侧：`GameScene` 作为“世界/调度器”

推荐设计：

#### C++ 侧

- `class Component`
  - `int id, cost, life, level`
  - `virtual ~Component() = default;`
  - `virtual void hurt(int atk);`
  - `virtual void step(WorldContext &world, int row, int col) = 0;`

- `class Plant`
  - 私有成员：`std::vector<std::unique_ptr<Component>> components;`
  - `int hp; int row, col;`
  - `bool alive() const;`
  - `virtual void update(WorldContext &world);`
  - `virtual void hurt(int atk);`

- `WorldContext` / `WorldAPI`
  - `void add_sun(int amount);`
  - `void spawn_projectile(int row, int col, int damage);`
  - `bool has_zombie_ahead(int row, int x);`
  - `void hurt_zombie(int id, int damage);`
  - `int get_sun();` 等等

`Plant` 只负责“组合组件和转发行为”，不要让它直接画界面。

#### Python 侧

- 继续保留 `GameScene` 作为场景管理器
- 增加一个 `self.plants` 或 `self.cpp_plants` 网格
- 每个格子存一个 “C++ 植物句柄”
- 在 Python 的定时器里调用 `plant_step(plant_handle, world_callbacks)`

---

### 3.2 你现在可以先做一个最简接口

#### C++ 内部样例结构

```cpp
struct WorldContext {
    std::function<void(int)> add_sun;
    std::function<void(int,int,int)> spawn_pea;
    std::function<bool(int,int)> zombie_exists;
    std::function<void(int,int,int)> hurt_zombie;
};

class Component {
public:
    int id, cost, life, level;
    Component(int i, int c, int lf, int lv): id(i), cost(c), life(lf), level(lv) {}
    virtual ~Component() = default;
    virtual void hurt(int atk) { life = std::max(0, life - atk); }
    virtual void step(WorldContext &world, int row, int col) = 0;
};

class ShooterComponent : public Component {
    int damage;
    int cooldown;
    int tick = 0;
public:
    ShooterComponent(int dmg, int cd): Component(2, 10, 30, 0), damage(dmg), cooldown(cd) {}
    void step(WorldContext &world, int row, int col) override {
        if (++tick >= cooldown) {
            tick = 0;
            if (world.zombie_exists(row, col)) {
                world.spawn_pea(row, col, damage);
            }
        }
    }
};
```

#### Plant 基类

```cpp
class Plant {
private:
    std::vector<std::unique_ptr<Component>> comps;
    int hp;
    int row, col;

public:
    Plant(int hp_, int row_, int col_) : hp(hp_), row(row_), col(col_) {}
    virtual ~Plant() = default;

    void add_component(std::unique_ptr<Component> c) {
        comps.push_back(std::move(c));
    }

    virtual void update(WorldContext &world) {
        for (auto &c : comps) {
            c->step(world, row, col);
        }
    }

    virtual void hurt(int atk) {
        hp = std::max(0, hp - atk);
    }

    bool alive() const { return hp > 0; }
};
```

#### 用户自定义植物

```cpp
class HybridPlant : public Plant {
    ShooterComponent shooter;
    SunProducerComponent producer;
public:
    HybridPlant(int row, int col)
      : Plant(300, row, col),
        shooter(40, 20),
        producer(25, 50)
    {
        add_component(std::make_unique<ShooterComponent>(shooter));
        add_component(std::make_unique<SunProducerComponent>(producer));
    }

    void update(WorldContext &world) override {
        Plant::update(world);
    }
};
```

注意：`Plant` 内部封闭 `Component`，外部只通过 `Plant::update()`、`Plant::hurt()` 与它交互。

---

## 4. 和当前 Python 项目怎么融合

### 4.1 现在的传播方式是“Python 画界面 + Python 定时器”
这部分你不用改太多：

- 继续让 `GameScene` 承担
  - `sun_num`
  - `zombies`
  - `plant` 的 UI 表现
  - `match` / `hit` / `pea_detect` / `potato_detect`

### 4.2 你需要新增“C++ 植物桥接层”

建议做法：

- 在 C++ 动态库里导出：
  - `extern "C" void* create_plant(int plant_type, int row, int col);`
  - `extern "C" void destroy_plant(void* handle);`
  - `extern "C" void plant_step(void* handle, WorldCallbacks* cb);`
  - `extern "C" void plant_hurt(void* handle, int damage);`
  - `extern "C" bool plant_alive(void* handle);`

- Python 用 `ctypes` / `cffi` 调用
- `WorldCallbacks` 由 Python 提供，用来执行游戏事件

### 4.3 `GameScene` 的改造点

现在 `born()` 和 `born_peashooter()` 等函数都是直接写死的。改造后：

- `born()` 负责：
  - 在网格上记录这个格子有植物
  - 创建一个 C++ `Plant` 实例
  - 记录 UI QLabel（或者后面改成自定义显示）
  - 设定 `self.plt_hp[cx][cy]` 或者改成由 C++ 侧提供生命值

- 每个 `monitor_zombies()` / 定时器步进时：
  - 调用 `plant.step()`
  - 如果植物死亡，清理 UI 和格子
  - 如果植物产生阳光，调用 `GameScene.collect_sun` 或直接 `sun_num += ...`

### 4.4 你可以先做“仅数据驱动”的 MVP

完全不用马上把 C++ 直接画界面。先做：

- C++ 负责行为逻辑：是否发射、是否产阳光、是否受伤
- Python 负责显示：放一个 `Pea.png`、放一个 `SunFlower.gif`

这样你先把“组件系统”和“植物系统”做出来，再做“真正编辑器”。

---

## 5. 如何控制“世界”的内容

你的世界控制点就在 `GameScene`：

- 时间步：`QTimer` 负责
  - `monitor_zombies`：僵尸移动、吃植物、游戏失败
  - `create_zombie_tick`：生成僵尸波
  - 其它植物行为也用自己的 `QTimer`

- 阳光：
  - `self.sun_num` 是当前阳光
  - `update_sun()` 更新显示和卡片禁用
  - `collect_sun()` 增加阳光
  - `Seed.checksun()` 用来控制卡片是否可点击

- 植物生命：
  - 目前 `self.plt_hp[cx][cy]` 表示格子中的植物生命
  - `monitor_zombies()` 中僵尸攻击时直接减 `plt_hp`
  - 你要改成 C++ 植物时，可以让 Python 在攻击时调用 `plant_hurt(handle, damage)`，然后根据 `plant_alive(handle)` 清理格子

---

## 6. 你现在最应该做的三件事

### 6.1 设计 C++ 植物接口
先把 `Plant` / `Component` / `WorldContext` 设计清楚，避免“写了一堆类但不知道怎么调用”。

### 6.2 把 Python 里的硬编码植物行为抽成“统一接口”
现在所有行为分散在 `born_*` 中，先改成：

- `create_plant_in_grid(row, col, plant_type)`
- `plant_step_all()`
- `plant_hurt_at(row, col, damage)`

这样才有机会把 C++ 植物接进去。

### 6.3 先实现“动态编译 + 插件调用”
最开始可以做：
- 用户写 `myplant.cpp`
- 程序保存
- `QProcess` 调 `g++ -shared -fPIC -o myplant.so myplant.cpp`
- 用 `ctypes.CDLL("myplant.so")` 加载
- 调用工厂函数创建植物

---

## 7. 针对你当前 components.cpp 的具体建议

你目前的 components.cpp 可以这样改：

- 为 `Component` 添上一个 `virtual ~Component() = default;`
- 给 `Component::hurt` 和 `Component::step` 写默认实现
- 定义一个 `Plant` 基类
- 定义一个 `struct WorldContext` 或 `struct GameAPI`
- 给 `PeaHead` 添加真实 `step()` 实现，而不是空函数
- 最好不要把“图像逻辑”写在 C++ 里，C++ 只负责“行为逻辑”

例如：

```cpp
class Component {
public:
    int id, cost, life, level;
    Component(int i, int c, int lf, int lv): id(i), cost(c), life(lf), level(lv) {}
    virtual ~Component() = default;
    virtual void hurt(int atk) { life = std::max(0, life - atk); }
    virtual void step(WorldContext &world, int row, int col) = 0;
    bool is_alive() const { return life > 0; }
};
```

注意这个 `step` 需要传入“世界上下文”，否则它不知道怎样发射子弹或生产阳光。

---

## 8. 最终建议

如果你现在最困惑的是“怎么融合原有接口”，答案就是：

- 你需要先把“植物行为”和“游戏世界”分开
- 让 C++ 负责“植物/组件行为”
- 让 Python 负责“场景、阳光、僵尸、UI、时间”
- 通过一个明确的桥接接口把两端连接起来

---

## 9. 你的下一步应该做什么

1. 先把 game_scene.py 里 `born_*` 的植物行为抽象成通用接口
2. 设计 `Component` / `Plant` / `WorldContext` 的 C++ 接口
3. 让 C++ 插件导出工厂函数
4. 先实现一个简单的 `SunFlower` 和 `Peashooter`
5. 再做 PyQt 编辑器：保存 `.cpp`、编译 `.so`、显示编译错误

如果你愿意，我可以继续帮你把这份架构具体落地成：
- `components.h` / components.cpp 的完整接口
- Python 侧 `GameScene` 的改造点
- `ctypes` / `cffi` 动态加载 `.so` 的最小示例