cmake_minimum_required(VERSION 3.16)
project(PVZCppPlants LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}/../plugins/plants)

include_directories(${CMAKE_CURRENT_LIST_DIR}/../cpp_api)

set(PVZ_PLANTS
    SunFlower
    Peashooter
    WallNut
    PotatoMine
    Repeater
    DoubleSunShooter
)

foreach(plant ${PVZ_PLANTS})
    add_library(${plant} SHARED ${plant}.cpp)
    set_target_properties(${plant} PROPERTIES
        PREFIX ""
        OUTPUT_NAME "${plant}"
    )
endforeach()
