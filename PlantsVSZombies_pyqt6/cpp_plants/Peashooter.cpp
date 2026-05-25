#include "../cpp_api/pvz_api.h"

class Peashooter : public Plant {
private:
    int timer = 0;

public:
    Peashooter(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;
        if (timer % 200 == 0 && api.if_Zombies_ahead(row, col)) {
            api.shoot_pea(row, col, 1);
        }
    }
};

PVZ_REGISTER_PLANT(Peashooter, 2, "Peashooter", "Peashooter.gif", 100, 7500)
