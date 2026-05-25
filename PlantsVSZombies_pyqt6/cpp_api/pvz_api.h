#pragma once

#include <cstdint>

#if defined(_WIN32)
#define PVZ_EXPORT __declspec(dllexport)
#else
#define PVZ_EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

struct PVZGameAPI {
    void* ctx;

    int (*get_time)(void* ctx);
    int (*get_sun)(void* ctx);
    int (*get_hp)(void* ctx, int row, int col);
    int (*get_zombie_count)(void* ctx, int row);
    int (*count_zombies_ahead)(void* ctx, int row, int col);
    int (*nearest_zombie_x)(void* ctx, int row, int col);
    bool (*if_zombies_ahead)(void* ctx, int row, int col);
    bool (*if_zombies_touch)(void* ctx, int row, int col);
    bool (*is_cell_empty)(void* ctx, int row, int col);

    void (*shoot_pea)(void* ctx, int row, int col, int number);
    void (*shoot_snow_pea)(void* ctx, int row, int col, int number);
    void (*explode)(void* ctx, int row, int col);
    void (*explode_area)(void* ctx, int row, int col, int radius, int damage);
    void (*raise_sun)(void* ctx, int row, int col);
    void (*change_animation)(void* ctx, int row, int col, const char* animation_name);
    void (*set_hp)(void* ctx, int row, int col, int hp);
    void (*damage_self)(void* ctx, int row, int col, int amount);
};

}

class GameAPI {
public:
    explicit GameAPI(PVZGameAPI* api) : api_(api) {}

    int get_time() const { return api_->get_time(api_->ctx); }
    int get_sun() const { return api_->get_sun(api_->ctx); }
    int get_hp(int row, int col) const { return api_->get_hp(api_->ctx, row, col); }
    int get_zombie_count(int row) const { return api_->get_zombie_count(api_->ctx, row); }
    int count_zombies_ahead(int row, int col) const { return api_->count_zombies_ahead(api_->ctx, row, col); }
    int nearest_zombie_x(int row, int col) const { return api_->nearest_zombie_x(api_->ctx, row, col); }
    bool if_Zombies_ahead(int row, int col) const { return api_->if_zombies_ahead(api_->ctx, row, col); }
    bool if_Zombies_touch(int row, int col) const { return api_->if_zombies_touch(api_->ctx, row, col); }
    bool is_cell_empty(int row, int col) const { return api_->is_cell_empty(api_->ctx, row, col); }

    void shoot_pea(int row, int col, int number = 1) { api_->shoot_pea(api_->ctx, row, col, number); }
    void shoot_snow_pea(int row, int col, int number = 1) { api_->shoot_snow_pea(api_->ctx, row, col, number); }
    void explode(int row, int col) { api_->explode(api_->ctx, row, col); }
    void explode_area(int row, int col, int radius, int damage) { api_->explode_area(api_->ctx, row, col, radius, damage); }
    void raise_sun(int row, int col) { api_->raise_sun(api_->ctx, row, col); }
    void change_animation(int row, int col, const char* animation_name) { api_->change_animation(api_->ctx, row, col, animation_name); }
    void set_hp(int row, int col, int hp) { api_->set_hp(api_->ctx, row, col, hp); }
    void damage_self(int row, int col, int amount) { api_->damage_self(api_->ctx, row, col, amount); }

private:
    PVZGameAPI* api_;
};

class Plant {
public:
    int row;
    int col;
    int hp;

    Plant(int r, int c, int initial_hp) : row(r), col(c), hp(initial_hp) {}
    virtual ~Plant() = default;
    virtual void Update(GameAPI& api) = 0;
};

#define PVZ_REGISTER_PLANT(CLASS_NAME, PLANT_ID, DISPLAY_NAME, IMAGE_NAME, SUN_COST, COOLDOWN_MS) \
    extern "C" PVZ_EXPORT Plant* create_plant(int row, int col) { return new CLASS_NAME(row, col); } \
    extern "C" PVZ_EXPORT void destroy_plant(Plant* plant) { delete plant; } \
    extern "C" PVZ_EXPORT void update_plant(Plant* plant, PVZGameAPI* raw_api) { \
        GameAPI api(raw_api); \
        plant->Update(api); \
    } \
    extern "C" PVZ_EXPORT int get_plant_hp(Plant* plant) { return plant->hp; } \
    extern "C" PVZ_EXPORT void set_plant_hp(Plant* plant, int hp) { plant->hp = hp; } \
    extern "C" PVZ_EXPORT int plant_id() { return PLANT_ID; } \
    extern "C" PVZ_EXPORT const char* plant_name() { return DISPLAY_NAME; } \
    extern "C" PVZ_EXPORT const char* plant_image() { return IMAGE_NAME; } \
    extern "C" PVZ_EXPORT int plant_sun_cost() { return SUN_COST; } \
    extern "C" PVZ_EXPORT int plant_cooldown_ms() { return COOLDOWN_MS; }
