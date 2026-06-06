#include "components.h"

class SunFortress : public HybridPlant {
public:
    SunFortress(int r, int c) : HybridPlant(r, c) {
        components.push_back(std::make_unique<WallNutHead>());
        components.push_back(std::make_unique<PeaHead>(1, 250));
        components.push_back(std::make_unique<SunHead>(1, 600));
        finalize();
    }
};

PVZ_REGISTER_HYBRID(SunFortress, 205, "SunFortress")
