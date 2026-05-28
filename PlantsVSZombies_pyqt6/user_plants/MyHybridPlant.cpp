#include "../cpp_core/components.h"

class MyHybridPlant : public HybridPlant {
public:
    MyHybridPlant(int r, int c) : HybridPlant(r, c) {
        // 在这里添加组件:
        components.push_back(std::make_unique<PeaHead>(1, 200));
        components.push_back(std::make_unique<SunHead>(1, 1000));
        components.push_back(std::make_unique<WallNutHead>());
        finalize();
    }
};

PVZ_REGISTER_HYBRID(MyHybridPlant, 200, "MyHybridPlant", "MyHybridPlant.png")
