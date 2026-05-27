#pragma once
#include <vector>
#include <memory>
#include "../cpp_api/pvz_api.h"
#include "components.h"

class HybridPlant : public Plant{
public:
    //构造函数 hp 记得用零件的 cost 求和
    int timer = 0;      // 计时器, 每个部件都使用所在植物的时间
    virtual void Update(GameAPI& api){
        // TODO
    }
};

// TODO:
PVZ_REGISTER_PLANT() 
// 格式: PVZ_REGISTER_PLANT(CLASS_NAME,PLANT_ID,DISPLAY_NAME,IMAGE_NAME,SUN_COST,COOLDOWN_MS)
// 杂交植物的贴图怎么搞。 零件是否注册自己的贴图, 并存到一个成员变量里?
// SUN_COST,COOLDOWN_MS 由零件加和得到