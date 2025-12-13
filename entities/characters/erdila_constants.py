# entities/erdila_constants.py

SKILL_MULTIPLIERS = {
    # 普攻 4段
    "normal": [68, 90, 118, 124],
    "plunge": 180,
    "execution": 900,
    
    # 战技: 奔腾的多利
    "skill": 320,
    
    # 终结技: 毛茸茸派对 (散射)
    # 描述是随机散射，这里模拟平均命中次数，假设单怪能吃 5段
    "ult_hit": 165, 
    
    # 连携技: 火山蘑菇云
    "qte_hit": 100,
    "qte_explode": 250
}

FRAME_DATA = {
    "normal": [
        {"total": 8, "hit": 5}, {"total": 8, "hit": 5}, 
        {"total": 10, "hit": 6}, {"total": 14, "hit": 8}
    ],
    "skill": {"total": 20, "hit": 8}, # 冲撞
    "ult": {"total": 30, "interval": 5}, # 持续施法
    "qte": {"total": 15, "hit": 5, "explode": 10}
}

MECHANICS = {
    "vuln_value": 0.25,        # 25% 脆弱
    "vuln_duration": 30.0,     # 30秒
    "corrosion_duration": 7.0, # QTE施加腐蚀时长
    
    # 治疗相关 (假设数值)
    "heal_base": 500,
    "heal_scale": 1.2, # 意志倍率
}