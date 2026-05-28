#pragma once

#include "../cpp_api/pvz_api.h"
#include <memory>
#include <vector>
#include <algorithm>

class Component;

class HybridPlant : public Plant {
public:
    int timer = 0;
    std::vector<std::unique_ptr<Component>> components;

    HybridPlant(int r, int c) : Plant(r, c, 0) {}
    virtual ~HybridPlant() = default;

    void finalize();
    int total_cost() const;
    int total_cooldown() const;
    void Update(GameAPI& api) override;
};
