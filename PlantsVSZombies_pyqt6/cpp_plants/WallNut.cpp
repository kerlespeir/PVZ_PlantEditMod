#include "../cpp_api/pvz_api.h"

class WallNut : public Plant {
private:
    int state = 1;

public:
    WallNut(int r, int c) : Plant(r, c, 4000) {}

    void Update(GameAPI& api) override {
        if (hp <= 0) {
            return;
        }
        if (hp < 1333 && state != 3) {
            state = 3;
            api.change_animation(row, col, "WallNut2.gif");
        } else if (hp <= 2666 && state == 1) {
            state = 2;
            api.change_animation(row, col, "WallNut1.gif");
        }
    }
};

PVZ_REGISTER_PLANT(WallNut, 3, "WallNut", "WallNut.gif", 50, 30000)
