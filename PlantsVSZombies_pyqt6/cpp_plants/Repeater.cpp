#include "../cpp_api/pvz_api.h"

class Repeater : public Plant {
private:
    int timer = 0;

public:
    Repeater(int r, int c) : Plant(r, c, 300) {}

    void Update(GameAPI& api) override {
        timer++;
        if (timer % 200 == 0 && api.if_Zombies_ahead(row, col)) {
            api.shoot_pea(row, col, 2);
        }
    }
};

PVZ_REGISTER_PLANT(Repeater, 5, "Repeater", "Repeater.gif", 200, 7500)
