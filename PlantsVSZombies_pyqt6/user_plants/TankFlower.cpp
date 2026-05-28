#include "../cpp_core/components.h"

class TankFlower : public HybridPlant {
public:
    TankFlower(int r, int c) : HybridPlant(r, c) {
        components.push_back(std::make_unique<PeaHead>(1, 200));
        components.push_back(std::make_unique<SunHead>(1, 1000));
        components.push_back(std::make_unique<WallNutHead>());
        finalize();
    }
};

PVZ_REGISTER_HYBRID(TankFlower, 200, "TankFlower", "TankFlower.png")