#include "../cpp_api/pvz_api.h"

class PotatoMine : public Plant {
private:
    int timer = 0;
    bool mature = false;

public:
    PotatoMine(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;
        if (!mature && timer >= 1500) {
            mature = true;
            hp = 50000;
            api.set_hp(row, col, hp);
            api.change_animation(row, col, "PotatoMine.gif");
        }
        if (mature && api.if_Zombies_touch(row, col)) {
            api.explode(row, col);
            hp = 0;
            api.set_hp(row, col, 0);
        }
    }
};

PVZ_REGISTER_PLANT(PotatoMine, 4, "PotatoMine", "PotatoMine1.gif", 25, 30000)
