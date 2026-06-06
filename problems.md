# PVZ_PlantEditMod 逻辑问题汇总

本文档记录对项目所有源代码的逐行审查中发现的逻辑问题、边界情况、潜在 bug 和设计缺陷。

---

## 一、游戏核心逻辑 (game_scene.py)

### 1. [严重] 死亡僵尸仍阻挡豌豆 — `pea_detect()` 和 `hit()` 未检查 `hp > 0`

**位置**: `game_scene.py:498-499`, `game_scene.py:491-496`

`pea_detect()` 和 `hit()` 在判断僵尸时都不检查 `zombie.hp > 0`。僵尸死亡后 (`hp <= 0`) 不会立即从 `self.zombies` 列表中移除，而是要等死亡动画播完（`monitor_zombies()` 第 477 行才移除）。在此期间：

- **`pea_detect()`** 仍然返回 `True`，导致 `PeaHead` 和 `Peashooter`/`Repeater` 等植物继续朝已死僵尸射击
- **`hit()`** 仍然对已死僵尸造成伤害并消耗豌豆，已死僵尸成为"护盾"吸收本应命中后方僵尸的子弹

对比 `api_count_zombies_ahead()` 和 `api_if_zombies_touch()` 都正确检查了 `zombie.hp > 0`，存在不一致。

### 2. [严重] 植物爆炸后同一 tick 内其他组件仍可执行 — `api_explode` 后组件继续运行

**位置**: `game_scene.py:416-435` (api_explode_area), `cpp_core/components.h:138-143` (Update)

当杂交植物的 `PotatoMineHead` 组件触发 `api.explode()` 时：
- `api_explode_area()` 将 `self.map[col][row] = 0` 并移除植物贴图
- 但 C++ 端 `HybridPlant::Update()` 继续迭代剩余的组件 (`components.h:140`)
- 后续组件（如 `PeaHead`）调用的 Python API（如 `shoot_pea`）**不检查** `self.map[col][row]` 是否已被清空（`api_shoot_pea` 只调用 `valid_cell`，不检查 map）

**后果**: 一个爆炸后已在 Python 侧被移除的植物，在同一 tick 内仍可从空单元格发射豌豆。

### 3. [中等] 死亡僵尸受击时燃烧动画不生效 — `get_hurt()` 与 `die()` 调用顺序

**位置**: `zombies.py:154-157` (get_hurt), `zombies.py:146-152` (die)

流程：
1. `monitor_zombies()` 检测到 `zombie.hp <= 0`，调用 `zombie.die()` 开始播放死亡动画（`if_die = True`）
2. 同一 tick 或稍后，一颗豌豆通过 `hit()` → `get_hurt(40, burn=True)` 命中该僵尸
3. `get_hurt()` 检查 `hp <= 0 and burn`，将 `die_path` 改为 `Burn.gif`
4. 但 `die()` 后续不会再被调用（`if_die` 已为 True）

**后果**: 被火焰击杀的僵尸不会显示燃烧动画（如果它在此之前已被判定死亡）。

### 4. [中等] 豌豆发射器 timer 泄漏 — `_timers` 无限增长

**位置**: `game_scene.py:286-301` (launch_pea), `game_scene.py:44-46` (_timers)

每发射一颗豌豆，`launch_pea()` 创建一个新的 `QTimer` 并追加到 `self._timers`。豌豆命中或飞出屏幕后，timer 停止但**不从 `_timers` 列表中移除**。

一局游戏可能发射数百颗豌豆，`_timers` 列表中会积累大量已停止的 timer 对象引用，造成内存浪费。

### 5. [中等] 僵尸序列结束后游戏无终止条件 — 永不自然结束

**位置**: `game_scene.py:463-471` (create_zombie_tick)

僵尸波次固定为 50 波。50 波后若场上仍有僵尸，`zcnt == 50` 阻止新僵尸生成，但游戏不会因时间推移自动结束。玩家必须手动杀死所有僵尸才能获胜。如果某个僵尸卡在边界外或出现其他异常，游戏可能永远无法结束。

### 6. [低] 无用的 `QTimer.singleShot(800, lambda: None)` — 死代码

**位置**: `game_scene.py:138`

```python
QTimer.singleShot(800, lambda: None)
```

该行不执行任何操作，推测是遗留的调试代码或之前的延迟逻辑。

### 7. [低] 坐标映射缺失 row 5 — `Zombie.my` 默认值依赖

**位置**: `zombies.py:123`

```python
self.my = {50: 1, 170: 2, 290: 3, 400: 4}.get(self.y(), 5)
```

`raw_h = [50, 170, 290, 400, 520]`，但字典中缺失 `520: 5` 的映射。Row 5 的僵尸正确是因为 `.get(..., 5)` 的默认值兜底。如果未来 `raw_h[4]` 的值改变，需要同时更新两处，容易遗漏。

### 8. [低] 僵尸状态切换跳帧 — `z_change()` 的 if-elif 链

**位置**: `zombies.py:70-102`

当僵尸受到一次巨额伤害（如爆炸 5000 伤害），HP 直接跳过多级阈值。`z_change()` 使用 `if-elif` 链只匹配第一个满足的条件，导致中间外观状态被跳过（例如从满血锥形僵尸直接变成断头僵尸，跳过了中度损伤外观）。这可能是有意设计，但仍值得注意。

### 9. [低] 无割草机 — 与原版游戏差异

**位置**: `game_scene.py` 整体

`res/` 中无割草机相关资源，`game_scene.py` 中无割草机逻辑。僵尸到达最左侧直接触发游戏失败（`zwin()`），与原版 PvZ 每个割草机可以救一次的设计不同。

---

## 二、Python-C++ 桥接层 (cpp_bridge.py)

### 10. [中等] `PVZGameAPI.ctx` 始终为 None — 冗余但误导

**位置**: `cpp_bridge.py:171-190`

```python
self.c_api = PVZGameAPI(None, ...)
```

`ctx` 字段被设为 `None`，所有回调闭包都捕获 `self.scene` 而非通过 `ctx` 传参。C 端 `PVZGameAPI.ctx` 永远不会被使用。如果未来有人尝试通过 `ctx` 访问 Python 对象会得到空指针。

### 11. [低] `CppPlantLoader` 重复加载同 ID 插件 — 旧的 DLL 句柄泄漏

**位置**: `cpp_bridge.py:106-112`

当多个 `.dylib` 导出相同 `plant_id` 时，`load_all()` 保留最新修改时间的。但较早加载的 `ctypes.CDLL` 句柄未被卸载（Python ctypes 没有官方卸载机制），库保留在内存中。多次重新编译植物会导致进程内积累多个同名库的副本。

---

## 三、种子卡片与阳光系统 (seed.py, sun.py)

### 12. [低] 阳光 10 秒自动消失在前端无提示 — MySun 悄然消失

**位置**: `sun.py:24`

```python
QTimer.singleShot(10000, self.deleteLater)
```

阳光在 10 秒后直接消失，无闪烁或渐隐提示。原版 PvZ 的阳光在即将消失前会闪烁，这里没有实现。

### 13. [低] 种子冷却动画与定时器竞态

**位置**: `seed.py:59-74`

冷却动画由 `QPropertyAnimation` 驱动，冷却结束由 `QTimer.singleShot(self.cooldown, ...)` 触发。两者理论上同时结束，但如果其中任何一个有微小延迟，可能出现卡片已可用但遮罩未完全消失（或相反）的短暂视觉不一致。

---

## 四、植物编辑器 (plant_editor.py)

### 14. [中等] 每按键都写文件 — 性能问题

**位置**: `plant_editor.py:116-118`

```python
self.plant_editor.textChanged.connect(self._persist_plant_source)
```

每次按键都触发一次完整的文件写入。对于较大的源码文件或频繁编辑场景可能造成磁盘 I/O 抖动。建议使用 debounce 或仅在失去焦点/保存时写入。

### 15. [中等] 仅用正则提取组件名 — 可能误匹配

**位置**: `plant_editor.py:225`

```python
components = re.findall(r"make_unique<(\w+)>", source)
```

从源码中用正则提取组件名，无法区分代码和注释。如果用户在注释中写了 `make_unique<PeaHead>` 也会被当作组件。

### 16. [低] 编辑器不显示编译错误的源代码行号映射

**位置**: `plant_editor.py:271-274`

编译器（clang++/g++）的错误输出包含行号，但编辑器不解析这些行号来高亮对应代码行。用户需要手动在编译输出中找行号再回到编辑器中定位。

### 17. [低] 模板 include 规范化只替换第一个 include — `normalize_plant_source` 局限

**位置**: `custom_plant_store.py:87-93`

```python
source = re.sub(r'#include\s+"[^"]+"', '#include "components.h"', source, count=1)
```

只替换第一个 `#include "..."` 。如果用户在 `#include "../cpp_core/components.h"` 之前添加了其他 include（如 `<string>`、自定义头文件），此正则可能替换错误的行，导致编译失败。

---

## 五、组件系统与 C++ 层

### 18. [中等] `WallNutHead` 损伤阈值基于组件 HP 而非植物总 HP

**位置**: `cpp_core/components.h:80-99`

```cpp
int max_hp = get_hp();  // 返回组件的 4000，而非植物的总 HP
int threshold_low = max_hp / 3;   // 1333
int threshold_mid = max_hp * 2 / 3; // 2666
```

对于杂交植物（如 WallNutHead + PeaHead），植物总 HP = 4300，但墙壁损伤动画的阈值仍基于 4000 计算。意味着：
- 植物总血量 4300，但视觉上在 2666 时就出现损伤，在 1333 时出现严重损伤
- 300 HP 来自 PeaHead，但 PeaHead 的 HP 不受 WallNutHead 视觉逻辑管理
- 可能出现"植物看起来已严重损坏但实际还有许多来自其他组件的 HP"的情况

### 19. [中等] `PotatoMineHead` 成熟后暴力设 HP = 50000

**位置**: `cpp_core/components.h:66-70`

```cpp
if (!mature && owner->timer >= 1500) {
    mature = true;
    owner->hp = 50000;  // 覆盖所有组件的累积 HP
    api.set_hp(owner->row, owner->col, owner->hp);
}
```

对于纯 PotatoMine 植物，成熟后 HP 从 300 跳到 50000 没有问题。但对于杂交植物，这会覆盖其他组件的 HP 贡献。如果植物同时有 WallNutHead 和 PotatoMineHead，WallNutHead 的 HP 贡献在成熟时被一并覆盖为 50000。虽然最终效果是爆炸（HP 设为 0），但在成熟到爆炸之间的窗口期内，HP 计算不正确。

### 20. [低] `PVZ_REGISTER_HYBRID` 每次查询 sun_cost/cooldown 都创建临时植物

**位置**: `cpp_core/components.h:102,108`

```cpp
extern "C" PVZ_EXPORT int plant_sun_cost() { CLASS_NAME tmp(0, 0); return tmp.total_cost(); }
extern "C" PVZ_EXPORT int plant_cooldown_ms() { CLASS_NAME tmp(0, 0); return tmp.total_cooldown(); }
```

每次 Python 侧通过 `CppPlantLoader._load_plugin()` 查询元数据时，C++ 侧都会创建一个完整的临时植物对象（含所有组件的构造和 `finalize()`），然后立即析构。对于简单植物影响可忽略，但组件多的复杂杂交植物会有不必要的开销。

### 21. [低] `HybridPlant` 构造到 `finalize()` 之间 HP = 0

**位置**: `cpp_core/hybrid_plant.h:15`

```cpp
HybridPlant(int r, int c) : Plant(r, c, 0) {}
```

在构造函数和 `finalize()` 调用之间，`hp` 为 0（植物"死亡"状态）。如果用户忘记在构造函数末尾调用 `finalize()`，植物种下后会在第一个 tick 被判定为死亡并移除，无任何错误提示。

### 22. [低] FootballZombie 永不换肤 — `hp_ch` 阈值无效

**位置**: `zombies.py:170`

```python
4: ZombieSpec(1600, ..., hp_ch=(10000, 10000, 10000))
```

橄榄球僵尸最大 HP 为 1600，但外观变化阈值全部设为 10000，意味着它在存活期间永远不会切换外观。这可能是有意设计（橄榄球僵尸确实不换装），但魔法数字 10000 可能让阅读代码的人误以为是 bug。

---

## 六、资源与持久化 (custom_plant_store.py)

### 23. [中等] 孤立资源清理只匹配硬编码前缀

**位置**: `custom_plant_store.py:238-251`

```python
if path.name.startswith(("MyHybridPlant", "TankFlower", "testplant", "custom_")) ...
```

清理逻辑只检查特定的文件名前缀。如果用户创建了名称不以这些前缀开头的自定义植物，其孤立资源（旧图片、旧插件）将不会被自动清理，在 `plugins/plants/` 和 `plantimages/` 中留下垃圾文件。

### 24. [低] 模式 A 使用 `cpp_core/components.h` 但用户在草稿中可能无感知

**位置**: `plant_editor.py:184`

模式 A 中，`components.h` 标签页始终显示 `cpp_core/components.h`（官方组件）。用户在编辑器中修改 `my_plant.cpp` 时写 `#include "../cpp_core/components.h"`，但 `normalize_plant_source()` 将其改为 `#include "components.h"`，依赖 `-I cpp_core` 编译标志解析。如果用户尝试离线编译（不通过编辑器），`#include "components.h"` 可能在当前目录找不到。

---

## 七、图像合成 (image_composer.py)

### 25. [低] >3 组件纵向堆叠可能越界 — 无高度检查

**位置**: `image_composer.py:73-95`

```python
canvas = QPixmap(100, 140)
```

当使用超过 4-5 个组件时，`y_offset -= pix.height() // 3` 会导致组件向上堆叠并可能超出画布顶部边界。没有对组件数量的上限检查或画布尺寸的动态调整。

### 26. [低] 三头布局画布过大 — 2064×2030

**位置**: `image_composer.py:52`

```python
canvas = QPixmap(*THREE_HEAD_BASE_SIZE)  # 2064 × 2030
```

最终保存的植物贴图是全分辨率 2064×2030 的 PNG，文件体积较大。虽然卡片图会被缩放到 48×68，但原始贴图文件会不必要地占用磁盘空间。

---

## 八、内置植物 (C++ Plants)

### 27. [低] `DoubleSunShooter` 缺少独立 GIF — 复用 Repeater.gif

**位置**: `cpp_plants/DoubleSunShooter.cpp:25`

```cpp
PVZ_REGISTER_PLANT(DoubleSunShooter, 100, "DoubleSunShooter", "Repeater.gif", 300, 7500)
```

能产阳光 + 双发射击 + 自爆的植物使用 `Repeater.gif` 作为贴图，与双发射手外观完全相同。玩家从视觉上无法区分。可能是素材缺失的临时方案。

### 28. [低] 不可用的植物卡片无禁用态视觉差异

**位置**: `game_scene.py:84-103` (seed bank 构建)

阳光不足时仅通过 `mask1` 半透明遮罩表示不可用，没有灰度化或降低亮度的处理。与原版 PvZ 的行为有所不同。

---

## 九、构建系统 (build_cpp_plants.py)

### 29. [低] 直接编译模式下无错误隔离

**位置**: `build_cpp_plants.py:29-44`

```python
for source in CPP_DIR.glob("*.cpp"):
    ...
    subprocess.run(..., check=True)
```

如果某个 `.cpp` 文件编译失败，`check=True` 会导致整个脚本中止（抛出 `CalledProcessError`），后续的 `.cpp` 文件不会被编译。部分编译成功的 `.dylib` 保留在 `plugins/plants/`，但无法确定哪些编译成功、哪些失败。

---

## 十、边界情况与鲁棒性

### 30. [中等] 游戏启动时若无任何编译好的插件 — 空种子栏

**位置**: `game_scene.py:50-53`

```python
self.plant_plugins = self.plant_loader.load_all()
self.seed_plant_ids: list[int] = sorted(self.plant_plugins.keys())
```

如果用户从未运行 `build_cpp_plants.py` 或 `plugins/plants/` 为空，`seed_plant_ids` 为空列表。种子栏会有一张空的商店背景图，游戏可以开始但无法放置任何植物。没有任何"请先编译植物"的提示。

### 31. [低] 种子栏宽度计算可能不足 — 长列表布局溢出

**位置**: `game_scene.py:68-76`

```python
bank_width = max(bank_pix.width(), 67 + 55 * num_seeds + 10)
```

自定义植物（通过编辑器创建的）会追加到种子列表中。如果有 10+ 个植物，种子栏可能超出屏幕宽度（960px），右侧按钮被遮挡。

### 32. [低] 铲子移除植物无阳光返还、无音效

**位置**: `game_scene.py:185-194`

铲子模式选中单元格后直接调用 `remove_plant(i, j)`，不返还任何阳光。虽然原版 PvZ 也是如此，但这是一个值得注意的设计选择。另外 `res/shovel.wav` 存在但未被播放。

### 33. [低] 植物放置和豌豆发射均无音效

**位置**: `game_scene.py` 整体

`res/` 目录中存在 `plant.wav`, `seedlift.wav`, `shovel.wav`, `points.wav`, `tap.wav` 等音效文件，`zombie/` 目录中存在 `chomp.wav`, `groan.wav` 等僵尸音效。但整个 Python 代码中没有任何 `QSoundEffect` 或 `QMediaPlayer` 的调用，**所有音效均未实现**。

---

## 十一、用户报告的 Bug 专项分析

### 34. [严重] 自定义植物卡片命名与内置植物冲突 — WallNut 贴图被覆盖为土豆

**位置**: `plant_editor.py:301-303` (保存卡片), `game_scene.py:94` (加载卡片), `custom_plant_store.py:214` (删除)

**根因链条**:

1. `_generate_preview()` 将卡片保存到 `res/<display_name>.png` (plant_editor.py:301) — **不使用任何命名空间前缀**
2. `game_scene.py` 通过 `plugin.name` 加载卡片：`asset(self.base_dir, "res", f"{plant_name}.png")` (第 94 行)
3. `create_or_update_record()` 只检查 **ID 冲突** (`plant_id_in_use`)，**不检查 display_name 是否与内置植物重名**
4. 因此用户可以创建 `PVZ_REGISTER_HYBRID(MyPlant, 999, "WallNut")`，保存的卡片直接覆盖 `res/WallNut.png`

**后果**:

```
用户创建自定义植物: PVZ_REGISTER_HYBRID(TankPlant, 999, "WallNut")
  └─ 包含 PotatoMineHead 组件
  └─ _generate_preview() 生成土豆地雷外观的合成图
  └─ 保存到 res/WallNut.png → 覆盖原版坚果墙卡片！
  └─ 内置 WallNut (ID=3) 加载 res/WallNut.png → 显示土豆图案
```

同理，如果用户创建 `display_name = "Peashooter"` 的自定义植物，`res/Peashooter.png` 被覆盖：
```
自定义植物: PVZ_REGISTER_HYBRID(SunPea, 200, "Peashooter")
  └─ 包含 SunHead + PeaHead 组件
  └─ 覆盖 res/Peashooter.png → 卡片显示自定义植物外观
  └─ 两个种子卡片（ID=2 和 ID=200）共用同一张被覆盖的卡片图
  └─ ID=200 的植物种下后产阳光 → 用户困惑
```

**恶化因素 — `delete_record()`**:

删除自定义植物时，`delete_record()` (line 214) 执行：
```python
card_path = base_dir / "res" / f"{record.display_name}.png"
card_path.unlink(missing_ok=True)  # 直接删除，不检查是否为内置资源
```

如果用户删除了 `display_name = "WallNut"` 的自定义植物 → **`res/WallNut.png` 被彻底删除** → 内置坚果墙丢失卡片图，在种子栏中显示为空白。

### 35. [严重] `cleanup_orphan_custom_assets` 无法恢复被覆盖的内置卡片

**位置**: `custom_plant_store.py:237-251`

清理函数通过硬编码前缀识别自定义资源：
```python
# res/ 清理 (line 242)
if path.name.startswith(("MyHybridPlant", "TankFlower", "testplant", "plant2", "custom_")) ...

# plantimages/ 清理 (line 250)
if path.name.startswith(("MyHybridPlant", "TankFlower", "testplant", "custom_")) ...
```

**三个缺陷**:

1. **不识别无前缀的自定义卡片**: 如果自定义植物 `display_name` 不以这些前缀开头（如 `"WallNut"`, `"Peashooter"`），即使该自定义植物已被删除（不在 `valid_card_names` 中），覆盖后的文件也不会被清理。
2. **无法恢复内置卡片**: 清理函数只能删除文件，不能恢复被覆盖的原版卡片。原版卡片需要从 git 或备份中手动恢复。
3. **`BUILTIN_PLUGIN_NAMES` 不完整**: 只包含 6 个内置植物的 `.dylib/.so` 文件名。如果未来添加更多内置植物，需要手动更新此集合。

### 36. [中等] 无贴图条目的来源分析 — 多种路径导致空白卡片/隐形植物

**位置**: 多处

"无贴图的东西"（种子栏中出现空白卡片，或种下后植物不可见）可能由以下路径产生：

**路径 A — 图片生成失败但 DLL 编译成功**:
- `_generate_preview()` 调用 `compose_plant_image()` (plant_editor.py:291)
- 如果所需组件贴图缺失（如 `components_images/PeaHeadComponent.png` 被删除），`compose_plant_image()` 返回 `None`
- 卡片和植物贴图都不会被保存
- 但 `compile_plant()` **已经编译成功并生成了 DLL**（`_generate_preview` 在第 281 行调用，在 `subprocess.run` 成功之后）
- 游戏启动时加载该 DLL → `plant_image()` 返回 `"custom_200.png"` → 文件不存在 → 植物在网格中不可见
- 卡片 `res/<display_name>.png` 也不存在 → 种子栏显示空白卡片

**路径 B — 清理函数删除了图片但保留了 DLL**:
- 清理函数 `cleanup_orphan_custom_assets` 对 plugins 和 images 使用不同逻辑：
  - Plugins: 保留 `BUILTIN_PLUGIN_NAMES` 中的 + `valid_plugin_names` 中的 ← **条件严格**
  - Images: 只清理**硬编码前缀匹配**的文件 ← **条件宽松**
- 如果自定义 DLL 文件名不在 `BUILTIN_PLUGIN_NAMES` 中，但在 `valid_plugin_names` 中，DLL 被保留
- 但如果其卡片/贴图文件名不以硬编码前缀开头（如 display_name 为 `"Sunny"`），这些图片**不会被当成孤儿删除**
- 反过来：如果图片以硬编码前缀开头（如 `"custom_200.png"`）且不在 `valid_plant_image_names` 中，图片被删除但 DLL 可能还在（如果 DLL 在 `valid_plugin_names` 中或文件名不匹配任何前缀检查）

**路径 C — 手动删除 `user_plants/library/` 文件夹**:
- 如果用户手动删除 `user_plants/library/<key>/` 文件夹（含 metadata.json），但忘记删除 `plugins/plants/<key>.dylib`
- 下次启动时，`cleanup_orphan_custom_assets` 检测到 DLL 不在 `valid_plugin_names` 中 → 删除 DLL
- 但对应的 `res/<name>.png` 和 `plantimages/custom_<ID>.png` 如果不匹配硬编码前缀 → **不被清理，成为孤儿文件**

### 37. [中等] 原生豌豆射手发射频率参数位置及说明

**位置**: `cpp_plants/Peashooter.cpp:12`

```cpp
void Update(GameAPI& api) override {
    timer++;
    if (timer % 200 == 0 && api.if_Zombies_ahead(row, col)) {
        api.shoot_pea(row, col, 1);
    }
}
```

**参数 `200` 控制发射频率**：`monitor_timer` 每 ~10ms 触发一次 tick，因此每 `200 × 10ms = 2秒` 发射 1 颗豌豆。

**同一参数在其他位置**:

| 文件 | 行 | 代码 | 频率 | 每次发射 |
|---|---|---|---|---|
| `cpp_plants/Peashooter.cpp` | 12 | `timer % 200 == 0` | 每 2s | 1 颗 |
| `cpp_plants/Repeater.cpp` | 10 | `timer % 200 == 0` | 每 2s | 2 颗 |
| `cpp_plants/DoubleSunShooter.cpp` | 15 | `timer % 100 == 0` | 每 1s | 2 颗 |
| `cpp_core/components.h` (PeaHead) | 33 | `owner->timer % time_prd == 0` | 可变 (默认 200) | n 颗 |
| 编辑器默认模板 | `plant_editor.py:54` | `PeaHead(1, 200)` | 每 2s | 1 颗 |

**注意**: `DoubleSunShooter` 的射击频率是豌豆射手的 **2 倍**（每 1s 发射 2 颗豌豆），同时还能产阳光。若用户感知到"原生豌豆射手太快"，可能是将 `DoubleSunShooter` 误以为普通豌豆射手，或者需要全局调整所有射击类植物的频率参数。

### 38. [低] 菜单按钮文字需要更新 — 图片内文字与实际功能不符

**位置**: `menu.py:28-78`

当前菜单按钮使用原版 PvZ 素材图的文字（"SURVIVAL"、"CHALLENGES"、"VASEBREAKER"），与实际功能不匹配：

| 按钮 | 当前图片 | 实际功能 | 建议文字 |
|---|---|---|---|
| 第 1 个 (line 36-38) | `SelectorScreen_Survival_button.png` | 编辑器模式 A | "组合官方组件" |
| 第 2 个 (line 40-43) | `SelectorScreen_Challenges_button.png` | 编辑器模式 B | "自定义组件组合" |
| 第 3 个 (line 45-48) | `SelectorScreen_Vasebreaker_button.png` | 植物库 | "我的植物库" |

**注意**: 按钮文字嵌入在 PNG 图片中，需要在图片编辑工具中修改（无法通过代码更改）。用户表示会自行用豆包抠图/改图。

**同时需更新的代码内文本标签**:

| 文件 | 行 | 当前文本 | 建议文本 |
|---|---|---|---|
| `plant_editor.py` | 37-39 | `"玩法 A：组合官方组件"`, `"玩法 B：编辑组件并组合植物"` | 保持一致即可 |
| `plant_library.py` | 56 | `"Plant Library"` | `"我的植物库"` |

### 39. [低] 编辑器模板中 `PeaHead(1, 200)` 的 prd=200 导致默认植物与原生豌豆射手完全相同

**位置**: `plant_editor.py:54`

```python
components.push_back(std::make_unique<PeaHead>(1, 200));
```

默认模板创建的杂交植物射击频率与原生 Peashooter **完全相同**（1 颗 / 2 秒）。如果用户不修改参数直接编译，会得到一个行为等同于豌豆射手但可能附加其他组件（如 SunHead）的植物。建议模板使用更保守的默认值（如 `PeaHead(1, 300)`），让自定义植物默认弱于原生植物，鼓励玩家调整参数。

### 问题 34-36 的修复建议概要

1. **卡片图片命名空间隔离**: 自定义植物的卡片应使用 `res/custom_<ID>_card.png` 格式，避免与内置 `res/<Name>.png` 冲突
2. **display_name 校验**: `create_or_update_record()` 应检查 display_name 是否与任何内置植物名重名
3. **内置卡片白名单**: `cleanup_orphan_custom_assets()` 应维护内置卡片名称的白名单，永不删除白名单中的文件
4. **delete_record 安全检查**: 删除卡片前检查是否与内置卡片重名，若是则仅记录日志而不删除
5. **图片生成失败回滚**: 若 `_generate_preview()` 中图片生成失败，应考虑是否回滚插件编译（或至少给出明确警告，告知玩家植物将不可见）
