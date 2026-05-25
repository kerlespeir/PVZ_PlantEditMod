#include "../cpp_api/pvz_api.h"

class SunFlower : public Plant {
private:
    int timer = 0;

public:
    SunFlower(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;
        if (timer % 1000 == 0) {
            api.raise_sun(row, col);
        }
    }
};

PVZ_REGISTER_PLANT(SunFlower, 1, "SunFlower", "SunFlower.gif", 50, 7500)
