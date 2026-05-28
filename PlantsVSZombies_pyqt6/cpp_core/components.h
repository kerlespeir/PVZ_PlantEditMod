#pragma once

#include "hybrid_plant.h"
#include <cmath>
#include <memory>

class Component {
private:
    int cost_;
    int cooldown_;
    int hp_;
public:
    Component(int c, int co, int _hp) : cost_(c), cooldown_(co), hp_(_hp) {}
    virtual ~Component() = default;
    virtual void step(GameAPI& api, HybridPlant* owner) = 0;
    int get_cost() const { return cost_; }
    int get_cooldown() const { return cooldown_; }
    int get_hp() const { return hp_; }
};

class PeaHead : public Component {
private:
    int shot_number;
    int time_prd;
public:
    PeaHead(int n, int prd)
        : Component(static_cast<int>(std::ceil(20000.0 / prd * n)), 7500, 300),
          shot_number(n), time_prd(prd) {}

    void step(GameAPI& api, HybridPlant* owner) override {
        if (!owner) return;
        if (owner->timer % time_prd == 0 && api.if_Zombies_ahead(owner->row, owner->col)) {
            api.shoot_pea(owner->row, owner->col, shot_number);
        }
    }
};

class SunHead : public Component {
private:
    int amount;
    int time_prd;
public:
    SunHead(int n, int prd)
        : Component(static_cast<int>(std::ceil(50000.0 / prd * n)), 7500, 300),
          amount(n), time_prd(prd) {}

    void step(GameAPI& api, HybridPlant* owner) override {
        if (!owner) return;
        if (owner->timer % time_prd == 0) {
            for (int i = 0; i < amount; i++) {
                api.raise_sun(owner->row, owner->col);
            }
        }
    }
};

class PotatoMineHead : public Component {
private:
    bool mature = false;
public:
    PotatoMineHead() : Component(25, 30000, 300) {}

    void step(GameAPI& api, HybridPlant* owner) override {
        if (!owner) return;
        if (!mature && owner->timer >= 1500) {
            mature = true;
            owner->hp = 50000;
            api.set_hp(owner->row, owner->col, owner->hp);
            api.change_animation(owner->row, owner->col, "PotatoMine.gif");
        }
        if (mature && api.if_Zombies_touch(owner->row, owner->col)) {
            api.explode(owner->row, owner->col);
            owner->hp = 0;
            api.set_hp(owner->row, owner->col, 0);
        }
    }
};

class WallNutHead : public Component {
private:
    int state = 1;
public:
    WallNutHead() : Component(50, 30000, 4000) {}

    void step(GameAPI& api, HybridPlant* owner) override {
        if (!owner || owner->hp <= 0) return;
        int max_hp = get_hp();
        int threshold_low = max_hp / 3;
        int threshold_mid = max_hp * 2 / 3;
        if (owner->hp < threshold_low && state != 3) {
            state = 3;
            api.change_animation(owner->row, owner->col, "WallNut2.gif");
        } else if (owner->hp <= threshold_mid && state == 1) {
            state = 2;
            api.change_animation(owner->row, owner->col, "WallNut1.gif");
        }
    }
};

#define PVZ_REGISTER_HYBRID(CLASS_NAME, PLANT_ID, DISPLAY_NAME, IMAGE_NAME) \
    extern "C" PVZ_EXPORT Plant* create_plant(int row, int col) { return new CLASS_NAME(row, col); } \
    extern "C" PVZ_EXPORT void destroy_plant(Plant* p) { delete p; } \
    extern "C" PVZ_EXPORT void update_plant(Plant* p, PVZGameAPI* raw) { GameAPI api(raw); p->Update(api); } \
    extern "C" PVZ_EXPORT int get_plant_hp(Plant* p) { return p->hp; } \
    extern "C" PVZ_EXPORT void set_plant_hp(Plant* p, int hp) { p->hp = hp; } \
    extern "C" PVZ_EXPORT int plant_id() { return PLANT_ID; } \
    extern "C" PVZ_EXPORT const char* plant_name() { return DISPLAY_NAME; } \
    extern "C" PVZ_EXPORT const char* plant_image() { return IMAGE_NAME; } \
    extern "C" PVZ_EXPORT int plant_sun_cost() { CLASS_NAME tmp(0, 0); return tmp.total_cost(); } \
    extern "C" PVZ_EXPORT int plant_cooldown_ms() { CLASS_NAME tmp(0, 0); return tmp.total_cooldown(); }

// Inline implementations of HybridPlant methods (require complete Component type)
inline void HybridPlant::finalize() {
    int total_hp = 0;
    for (auto& comp : components) {
        total_hp += comp->get_hp();
    }
    hp = total_hp;
}

inline int HybridPlant::total_cost() const {
    int sum = 0;
    for (auto& comp : components) {
        sum += comp->get_cost();
    }
    return sum;
}

inline int HybridPlant::total_cooldown() const {
    int mx = 0;
    for (auto& comp : components) {
        mx = std::max(mx, comp->get_cooldown());
    }
    return mx;
}

inline void HybridPlant::Update(GameAPI& api) {
    timer++;
    for (auto& comp : components) {
        comp->step(api, this);
    }
}
