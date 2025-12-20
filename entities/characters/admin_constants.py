# entities/characters/admin_constants.py

SKILL_MULTIPLIERS = {
    # 普攻 5段
    "normal": [51, 61, 68, 78, 90],
    "plunge": 180,
    "execution": 900,
    
    # 战技: 构成序列
    "skill": 350,
    
    # 终结技: 轰击序列
    "ult": 800,
    "ult_extra": 600,
    
    # 连携技: 锁闭序列
    "qte": 100,
    "qte_shatter": 400
}

FRAME_DATA = {
    "normal": [
        {"total": 20, "hit": 10}, 
        {"total": 20, "hit": 10},
        {"total": 20, "hit": 10},
        {"total": 25, "hit": 12},
        {"total": 35, "hit": 15}
    ],
    "skill": {"total": 40, "hit": 20},
    "ult": {"total": 60, "hit": 30},
    "qte": {"total": 30, "hit": 15}
}

MECHANICS = {
    # 封印
    "seal_duration": 5.0,
    "seal_vuln": 0.10, # 假设10%易伤
    
    # 天赋一
    "passive_cd_reduce": 2.0, # 假设2秒
}
