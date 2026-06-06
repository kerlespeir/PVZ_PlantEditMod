#include "components.h"

class PeaNut : public HybridPlant {
public:
    PeaNut(int r, int c) : HybridPlant(r, c) {
        components.push_back(std::make_unique<PeaHead>(1, 200));
        components.push_back(std::make_unique<WallNutHead>());
        finalize();
    }
};

PVZ_REGISTER_HYBRID(PeaNut, 201, "PeaNut")
