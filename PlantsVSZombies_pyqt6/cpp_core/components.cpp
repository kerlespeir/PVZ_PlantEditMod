#pragma once
#include <memory>
#include <vector>
#include "../cpp_api/pvz_api.h"
#include "./hybrid_plant.cpp"

class Component {
private:
    int cost;
    int cooldown;
    int hp;
public:
    Component(int c, int co, int _hp): cost(c), cooldown(co), hp(_hp){}
    virtual ~Component() = default;
    virtual void step(GameAPI& api, HybridPlant* owner) = 0;
    // virtual void Hurt(int amount){} 
    int get_cost(){return cost;}
    int get_cooldown(){return cooldown;}
    int get_hp(){return hp;}
};


class PeaHead : public Component{
private:
    int shot_number = 1;
    int time_prd = 200;     //cost=std::ceil(20000*n/prd), 原始=100
public:
    PeaHead(int n, int prd): shot_number(n), time_prd(prd), Component(std::ceil(20000/prd*n), 7500, 300){}
    virtual void step(GameAPI& api, HybridPlant* owner){
        if (!owner) return;
        if (owner->timer % time_prd == 0 && api.if_Zombies_ahead(owner->row, owner->col)) {
            api.shoot_pea(owner->row, owner->col, shot_number);
            // 每间隔 time_prd 从 (r,c) 射出 shot_number 个豌豆
        }
    }
};


class SunHead : public Component{
private:
    int amount = 1;         //cost=std::ceil(50000*n/prd), 原始=50
    int time_prd = 1000;    //制造阳光的间隔
public:
    SunHead(int n, int prd):amount(n), time_prd(prd), Component(std::ceil(50000/prd*n), 7500, 300){}
    virtual void step(GameAPI& api, HybridPlant* owner){
        if (owner->timer % time_prd ==0){
            // 制造amount个阳光, 十分原始地使用了 for 循环
            for (int i=0;i<amount;i++){api.raise_sun(owner->row, owner->col);}
        }
    }
};


class PotatoMineHead : public Component{
private:
    bool mature = false;
public:
    PotatoMineHead():mature(false), Component(25, 30000, 300){}   //cost c=25
    virtual void step(GameAPI& api, HybridPlant* owner){
        if (!mature && owner->timer >= 1500) {
            mature = true;
            owner->hp = 50000;
            api.set_hp(owner->row, owner->col, owner->hp);
            // 这里需要改贴图
            api.change_animation(owner->row, owner->col, "PotatoMine.gif");
        }
        if (mature && api.if_Zombies_touch(owner->row, owner->col)) {
            api.explode(owner->row, owner->col);
            owner->hp = 0;
            api.set_hp(owner->row, owner->col, 0);
        }
    }
};


class WallNutHead : public Component{
private:
    int state = 1;
public:
    WallNutHead():state(1), Component(50, 30000, 4000){}
    virtual void step(GameAPI& api, HybridPlant* owner){
        if (owner->hp <= 0) {
            return;
        }
        // 如果我们改进植物的hp受损时，会等比例给零件扣血，那么就把owner->hp改成this->get_hp()
        if (owner->hp < 1333 && state != 3) {
            state = 3;
            api.change_animation(owner->row, owner->col, "WallNut2.gif");
        } else if (owner->hp <= 2666 && state == 1) {
            state = 2;
            api.change_animation(owner->row, owner->col, "WallNut1.gif");
        }
    }
};