#include "components.h"

class MinePea : public HybridPlant {
public:
    MinePea(int r, int c) : HybridPlant(r, c) {
        components.push_back(std::make_unique<PeaHead>(1, 200));
        components.push_back(std::make_unique<PotatoMineHead>());
        finalize();
    }
};

PVZ_REGISTER_HYBRID(MinePea, 203, "MinePea")
