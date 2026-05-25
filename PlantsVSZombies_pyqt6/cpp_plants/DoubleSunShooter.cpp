#include "../cpp_api/pvz_api.h"

class DoubleSunShooter : public Plant {
private:
    int timer = 0;

public:
    DoubleSunShooter(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;
        if (timer % 300 == 0) {
            api.raise_sun(row, col);
        }
        if (timer % 100 == 0 && api.if_Zombies_ahead(row, col)) {
            api.shoot_pea(row, col, 2);
        }
        if (api.if_Zombies_touch(row, col) && hp <= 50) {
            api.explode(row, col);
            hp = 0;
        }
    }
};

PVZ_REGISTER_PLANT(DoubleSunShooter, 100, "DoubleSunShooter", "Repeater.gif", 300, 7500)
