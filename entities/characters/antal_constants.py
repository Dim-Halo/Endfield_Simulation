# entities/antal_constants.py

SKILL_MULTIPLIERS = {
    # 普攻 (电磁)
    "normal": [52, 63, 77, 115],
    "plunge": 180,
    "execution": 900,
    
    # 战技: 指定研究对象
    "skill": 200,
    
    # 终结技: 超频时刻 (无伤害，仅Buff)
    
    # 连携技: 磁暴试验场
    "qte": 340
}

FRAME_DATA = {
    "normal": [
        {"total": 7, "hit": 4}, {"total": 7, "hit": 4}, 
        {"total": 9, "hit": 5}, {"total": 12, "hit": 8}
    ],
    "skill": {"total": 20, "hit": 10}, # 长时间聚焦
    "ult": {"total": 15, "hit": 5},    # 施法动作
    "qte": {"total": 15, "hit": 8}
}

MECHANICS = {
    # fragility
    "skill_fragility_dur": 60.0,
    "skill_fragility_val": 0.14, # 14% 电/火脆弱 (独立乘区)
    
    "ult_buff_val": 0.28,   # 28% 电/火增幅
    "ult_buff_dur": 20.0,   # 假设持续20秒
    
    # 天赋一
    "passive_heal_base": 108,
    "passive_heal_scale": 1.0,
    "passive_cd": 300, # 30秒
}