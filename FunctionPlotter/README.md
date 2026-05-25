# Function Plotter

一个独立的 PyQt6 示例程序：在窗口中编辑 C++ 代码，点击编译后，程序会把代码编译成动态库，调用其中所有形如 `float name(float x)` 的函数，并绘制它们在 `[-1, 1]` 上的曲线。

## 运行

```bash
python main.py
```

需要本机可用的 C++ 编译器。macOS/Linux 默认优先使用 `clang++`，找不到时使用 `g++`。

## C++ 代码格式

代码必须符合 C++ 语法。可包含多个不同名字的函数，例如：

```cpp
#include <cmath>

float f(float x) {
    return x * x;
}

float wave(float x) {
    return std::sin(6.0f * x);
}
```

如果编译失败，编译器错误会直接显示在窗口中。
