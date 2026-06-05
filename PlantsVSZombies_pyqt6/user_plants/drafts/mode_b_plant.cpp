\
#include "components.h"

class MyHybridPlantB : public HybridPlant {
public:
    MyHybridPlantB(int r, int c) : HybridPlant(r, c) {
        // 在这里添加组件: 传入参数含义请参考 components.h !
        components.push_back(std::make_unique<PeaHead>(1, 200));
        components.push_back(std::make_unique<PeaHead>(1, 100));
        components.push_back(std::make_unique<SunHead>(20, 100));
        finalize();
    }
};

// 填写规则: 派生类类名(同一个 cpp 内不能重名), ID(自定义植物的唯一标识 不可重复), 显示卡片名
// 植物贴图文件名会自动生成为 custom_<ID>.png
PVZ_REGISTER_HYBRID(MyHybridPlantB, 204, "MyHybridPlant204")
