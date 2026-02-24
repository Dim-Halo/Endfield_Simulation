# entities/levatine_constants.py

SKILL_MULTIPLIERS = {
    # 普攻
    "normal": [29, 43, 45, 70, 95],
    "enhanced_normal": [117, 146, 208, 365],
    
    # 战技
    "skill_initial": 140,
    "skill_burst": 909,
    "skill_dot": 14,
    
    # 连携技
    "qte": 540
}

FRAME_DATA = {
    "normal": [
        {"total": 6, "hit": 4}, {"total": 5, "hit": 3},
        {"total": 7, "hit": 4}, {"total": 9, "hit": 5}, {"total": 12, "hit": 8}
    ],
    "enhanced_normal": [
        {"total": 7, "hit": 4}, {"total": 6, "hit": 3},
        {"total": 8, "hit": 5}, {"total": 13, "hit": 9}
    ],
    "skill": {"total": 15, "hit_init": 5, "hit_burst": 10},
    "ult": {"total": 20, "hit": 10},
    "qte": {"total": 12, "hit": 5}
}

MECHANICS = {
    "molten_max_stacks": 4,
    "heat_res_shred": 0.20,
    "qte_energy_gain": [0, 25, 30, 35] # 0个, 1个, 2个, 3个+
}