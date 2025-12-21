# entities/characters/guard_constants.py

SKILL_MULTIPLIERS = {
    "normal": [52, 63, 74, 86, 97],
    "plunge": 180,
    "execution": 900,
    
    # 战技: 粉碎阵线
    "skill_1": 192,
    "skill_2": 238,
    
    # 终结技: 盾卫旗队
    "ult_march": 300,  # 进军
    "ult_harass": 100, # 袭扰
    "ult_final": 450,  # 决胜
    
    # 连携技: 盈月邀击
    "qte_1": 95,
    "qte_2": 122,
    "qte_3": 149,
    "qte_3_enhanced": 297
}

FRAME_DATA = {
    "normal": [
        {"total": 20, "hit": 10}, 
        {"total": 20, "hit": 10},
        {"total": 20, "hit": 10},
        {"total": 25, "hit": 12},
        {"total": 35, "hit": 15}
    ],
    "skill": {"total": 50, "hit": 25}, # 2段
    "qte": {"total": 45, "hit": 15},   # 多段
    "ult": {"total": 60, "hit": 30}
}

MECHANICS = {
    # 战技回能 (根据消耗破防层数)
    "skill_sp_restore": {1: 5, 2: 15, 3: 25, 4: 35},
    
    # QTE (根据消耗破防层数)
    "qte_sp_restore": [5, 7, 13], # 对应第1, 2, 3段
    "qte_sp_restore_enhanced": 2, # 强化第3段额外? 或者是替代? "强化第三段技力恢复 2" -> 可能是替代13? 或者是额外? 通常是替代。
    # 描述: "强化第三段技力恢复 2"。对比普通第三段13，这个强化版恢复反而少？可能是笔误或者设计如此(伤害高了)。
    # 或者是 13+2? 或者是20? 
    # 暂时按替代处理。
    
    # 终结技
    "iron_oath_stacks": 5,
    "iron_oath_duration": 30.0,
    "ult_harass_sp": 10,
    "ult_final_sp": 40,
    
    # 天赋一
    "passive_sp_threshold": 80,
    "passive_buff_duration": 20.0,
    "passive_atk_bonus": 0.08,
    "passive_tech_bonus": 0.08,
    "passive_max_stacks": 3,
    
    # 天赋二
    "passive2_buff_duration": 10.0,
}
