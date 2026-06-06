#include "components.h"

class SunNut : public HybridPlant {
public:
    SunNut(int r, int c) : HybridPlant(r, c) {
        components.push_back(std::make_unique<SunHead>(1, 800));
        components.push_back(std::make_unique<WallNutHead>());
        finalize();
    }
};

PVZ_REGISTER_HYBRID(SunNut, 202, "SunNut")
