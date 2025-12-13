# entities/levatine_constants.py

SKILL_MULTIPLIERS = {
    # 普攻
    "normal": [64, 75, 107, 118, 160],
    "enhanced_normal": [162, 203, 289, 506],
    
    # 战技
    "skill_initial": 140,
    "skill_burst": 909,
    "skill_dot": 14,
    
    # 连携技
    "qte": 563
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
    "ult": {"total": 20, "hit": 10}
}

MECHANICS = {
    "molten_max_stacks": 4,
    "heat_res_shred": 0.20
}