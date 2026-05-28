# PVZ PlantEditMod

一个基于 PyQt6 的植物大战僵尸复刻项目，核心特色是 **C++ 植物插件系统** 和 **游戏内植物编辑器**：玩家可以在编辑器中通过组合预定义组件来创建杂交植物，编译为动态库后直接在游戏中使用。

## 项目结构

```
PlantsVSZombies_pyqt6/       ← 主项目（PyQt6 游戏 + C++ 插件系统）
├── main.py                  ← 入口
├── main_window.py           ← 主窗口、菜单/游戏/编辑器场景切换
├── game_scene.py            ← 游戏核心逻辑（植物放置、僵尸生成、碰撞检测）
├── plant_editor.py          ← 植物编辑器场景（代码编辑、编译、预览）
├── syntax_highlighter.py    ← C++ 语法高亮器
├── image_composer.py        ← 组件贴图合成
├── plants/
│   └── cpp_bridge.py        ← Python ↔ C++ 桥接层（ctypes 加载 .dylib/.so）
├── cpp_api/
│   └── pvz_api.h            ← C++ 植物 API 头文件（Plant 基类 + GameAPI + 注册宏）
├── cpp_core/                ← 组件化杂交植物系统（header-only）
│   ├── hybrid_plant.h       ← HybridPlant 基类（自动计算 HP/cost/cooldown）
│   └── components.h         ← Component 基类 + 所有组件 + PVZ_REGISTER_HYBRID 宏
├── cpp_plants/              ← 内置植物 C++ 源码
│   ├── SunFlower.cpp
│   ├── Peashooter.cpp
│   ├── WallNut.cpp
│   ├── PotatoMine.cpp
│   ├── Repeater.cpp
│   ├── DoubleSunShooter.cpp ← 示例自定义植物
│   └── CMakeLists.txt
├── user_plants/             ← 玩家通过编辑器创建的植物源码
├── plugins/plants/          ← 编译产物（.dylib/.so），运行时自动加载
├── components_images/       ← 组件贴图素材（用于合成杂交植物图片）
├── build_cpp_plants.py      ← 构建脚本（支持 CMake 或直接 clang++/g++）
├── res/                     ← UI 资源（菜单、按钮、音效、种子卡片图）
├── plantimages/             ← 植物/僵尸动画 GIF 和合成贴图
├── zombie/                  ← 僵尸动画和音效
└── docs/
    └── CPP_PLANT_API.md     ← C++ 植物 API 完整文档

PlantsVSZombies_old/         ← 原始 Qt/C++ 版本（参考用）
```

## 快速开始

```bash
# 1. 激活虚拟环境
cd /Users/css/Documents/科研/PVZ
source .venv/bin/activate

# 2. 安装依赖
pip install -r PlantsVSZombies_pyqt6/requirements.txt

# 3. 编译 C++ 植物插件
python3 PlantsVSZombies_pyqt6/build_cpp_plants.py

# 4. 运行游戏
python PlantsVSZombies_pyqt6/main.py
```

## 架构设计

### 职责分离

| 层 | 职责 | 技术 |
|---|---|---|
| Python 游戏引擎 | UI 渲染、定时器调度、僵尸管理、阳光系统、碰撞检测 | PyQt6 |
| C++ 植物行为 | 植物逻辑（射击、产阳光、爆炸、动画切换） | C++17 动态库 |
| C++ 组件系统 | 预定义组件，可组合为杂交植物 | C++17 header-only |
| 桥接层 | ctypes 加载 .dylib/.so，函数指针回调 | Python ctypes |
| 植物编辑器 | 游戏内代码编辑、编译、贴图合成、预览 | PyQt6 + subprocess |

### 游戏循环

1. `GameScene` 的 `monitor_timer` 每 10ms 触发一次 `game_tick()`
2. `game_tick()` 调用 `update_plants()`：遍历所有 C++ 植物实例，同步血量后调用 `plant->Update(api)`
3. C++ 植物通过 `GameAPI` 的函数指针回调 Python 侧执行动作（发射豌豆、产阳光、爆炸等）
4. Python 侧处理 UI 表现（创建子弹 QLabel、播放动画等）

### C++ 植物插件系统

每个植物是一个独立的 `.cpp` 文件，编译为动态库。植物继承 `Plant` 基类，实现 `Update(GameAPI& api)` 方法，最后用 `PVZ_REGISTER_PLANT` 宏注册元数据。

最小示例：

```cpp
#include "../cpp_api/pvz_api.h"

class MyPlant : public Plant {
    int timer = 0;
public:
    MyPlant(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;
        if (timer % 200 == 0 && api.if_Zombies_ahead(row, col)) {
            api.shoot_pea(row, col, 1);
        }
    }
};

PVZ_REGISTER_PLANT(MyPlant, 101, "MyPlant", "Peashooter.gif", 100, 7500)
```

详细 API 文档见 `PlantsVSZombies_pyqt6/docs/CPP_PLANT_API.md`。

## 植物编辑器

主菜单第三个按钮进入植物编辑器。编辑器提供：

- 左侧代码编辑区，两个标签页：
  - `components.h`（只读）：展示所有可用组件的接口定义
  - `my_plant.cpp`（可编辑）：玩家在此编写杂交植物代码
- 右侧预览区：编译成功后显示合成贴图
- 编译按钮：调用系统 C++ 编译器，错误信息实时显示

### 组件化杂交植物

玩家通过组合预定义组件创建杂交植物。`HybridPlant` 基类自动计算总 HP、阳光花费和冷却时间，玩家写的是真实 C++ 代码：

```cpp
#include "../cpp_core/components.h"

class TankFlower : public HybridPlant {
public:
    TankFlower(int r, int c) : HybridPlant(r, c) {
        components.push_back(std::make_unique<PeaHead>(1, 200));
        components.push_back(std::make_unique<SunHead>(1, 1000));
        components.push_back(std::make_unique<WallNutHead>());
        finalize();  // 自动计算 hp = 300+300+4000 = 4600
    }
};

PVZ_REGISTER_HYBRID(TankFlower, 200, "TankFlower", "TankFlower.png")
```

### 可用组件

| 组件 | 参数 | 效果 | 阳光花费公式 |
|------|------|------|-------------|
| PeaHead(n, prd) | n=发射数量, prd=间隔tick | 每 prd tick 射 n 发豌豆 | ceil(20000/prd*n) |
| SunHead(n, prd) | n=阳光数量, prd=间隔tick | 每 prd tick 产 n 个阳光 | ceil(50000/prd*n) |
| WallNutHead() | 无 | 4000 HP，按血量切换受损动画 | 50 |
| PotatoMineHead() | 无 | 1500 tick 成熟后接触僵尸爆炸 | 25 |

### 编译与加载流程

1. 玩家在编辑器中编写代码
2. 点击"编译"，系统调用 clang++/g++ 编译为 .dylib/.so
3. 编译成功后自动合成组件贴图并保存
4. 返回主菜单开始游戏，新植物出现在种子栏中

## 依赖

- Python 3.10+
- PyQt6 6.11
- C++17 编译器（clang++ 或 g++）
- CMake（可选，也支持直接编译）

## 内置植物

| ID | 名称 | 阳光 | 冷却 | 行为 |
|---|---|---|---|---|
| 1 | SunFlower | 50 | 7.5s | 每 1000 tick 产阳光 |
| 2 | Peashooter | 100 | 7.5s | 每 200 tick 射 1 发豌豆 |
| 3 | WallNut | 200 | 30s | 4000 HP，按血量切换受损动画 |
| 4 | PotatoMine | 25 | 30s | 1500 tick 后成熟，接触僵尸爆炸 |
| 5 | Repeater | 200 | 7.5s | 每 200 tick 射 2 发豌豆 |
| 100 | DoubleSunShooter | 300 | 7.5s | 产阳光 + 双发豌豆 + 低血量自爆（示例） |
