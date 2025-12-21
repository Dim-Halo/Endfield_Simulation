# entities/characters/chen_constants.py

SKILL_MULTIPLIERS = {
    "normal": [45, 54, 60, 68, 90],
    "plunge": 180,
    "execution": 900,
    "skill": 380,
    "qte": 270,
    "ult_slash": 81,
    "ult_final": 1023
}

FRAME_DATA = {
    "normal": [
        {"total": 20, "hit": 10}, 
        {"total": 20, "hit": 10},
        {"total": 20, "hit": 10},
        {"total": 25, "hit": 12},
        {"total": 35, "hit": 15}
    ],
    "skill": {"total": 45, "hit": 20},
    "qte": {"total": 30, "hit": 15},
    "ult": {"total": 90, "hit": 45} # 简化处理，实际可能有多个hit时间点
}

MECHANICS = {
    "airborne_duration": 2.5,
    "passive_atk_bonus": 0.08,
    "passive_duration": 10.0,
    "passive_max_stacks": 5,
    "interrupt_bonus_stagger": 10
}
