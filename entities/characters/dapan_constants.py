# entities/characters/dapan_constants.py

SKILL_MULTIPLIERS = {
    "normal": [63, 75, 113, 136],
    "skill": 300,  # 颠勺
    "ult_slashes": 50, # 空中连斩 (x6)
    "ult_final": 400,  # 终结一击
    "qte": 650,    # 加料
}

FRAME_DATA = {
    "normal": [
        {'total': 0.6, 'hit': 0.3},
        {'total': 0.6, 'hit': 0.3},
        {'total': 0.8, 'hit': 0.4},
        {'total': 1.0, 'hit': 0.5}, # Heavy
    ],
    "skill": {'total': 1.8, 'hit': 0.8}, # 浮空1.8s
    "ult": {
        'total': 4.0, 
        'slashes_start': 0.5, 
        'interval': 0.3, # 6 hits
        'final_hit': 3.0 
    },
    "qte": {'total': 2.0, 'hit': 1.0}
}

MECHANICS = {
    "qte_impact_boost": 0.20, # 猛击伤害提升20%
    "talent_1_duration": 20.0, # 备料状态持续时间 (假设)
    "talent_1_stack": 3,       # 最大层数 (假设)
    "talent_2_bonus_per_stack": 0.10 # 每层破防+10%伤害
}
