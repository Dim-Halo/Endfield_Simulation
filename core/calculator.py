# core/calculator.py
from .enums import Element, MoveType

class DamageEngine:
    @staticmethod
    def calculate(attacker_stats: dict, target_stats: dict, skill_mv: float, 
                  element: Element, is_staggered: bool = False, move_type: MoveType = MoveType.OTHER):
        """
        终末地伤害公式 (参考技术测试)
        Final = (面板攻击 * 属性修正 * 倍率) * (1+增伤) * 暴击 * (1+易伤) * (1+增幅) * 防御区 * 抗性区
        """
        
        # -------------------------------------------------
        # 1. 基础伤害区 (Base Zone)
        # -------------------------------------------------
        atk = attacker_stats['final_atk']
        base_dmg = atk * (skill_mv / 100.0)
        
        # -------------------------------------------------
        # 2. 增伤区 (Damage Bonus Zone) - 加算
        # -------------------------------------------------
        base_bonus = attacker_stats.get('dmg_bonus', 0.0)
        
        # 招式增伤
        move_bonus = 0.0
        if move_type == MoveType.NORMAL: move_bonus = attacker_stats.get('normal_dmg_bonus', 0.0)
        elif move_type == MoveType.SKILL: move_bonus = attacker_stats.get('skill_dmg_bonus', 0.0)
        elif move_type == MoveType.ULTIMATE: move_bonus = attacker_stats.get('ult_dmg_bonus', 0.0)
        elif move_type == MoveType.QTE: move_bonus = attacker_stats.get('qte_dmg_bonus', 0.0)

        elem_bonus = attacker_stats.get(f"{element.value}_dmg_bonus", 0.0)

        # 最终增伤
        bonus_mult = 1.0 + base_bonus + move_bonus + elem_bonus
        
        # -------------------------------------------------
        # 3. 暴击区 (Critical Zone)
        # -------------------------------------------------
        c_rate = min(1.0, max(0.0, attacker_stats.get('crit_rate', 0.0)))
        c_dmg = attacker_stats.get('crit_dmg', 0.5)
        crit_mult = 1.0 + (c_rate * c_dmg)
        
        # -------------------------------------------------
        # 4. 易伤区 (Vulnerability Zone) - 敌方身上的Debuff
        # -------------------------------------------------
        # 包含：通用易伤、受到元素伤害增加
        vuln = target_stats.get('vulnerability', 0.0)
        if element != Element.PHYSICAL:
            vuln += target_stats.get('magic_vulnerability', 0.0)
        else:
            # 物理易伤
            vuln += target_stats.get('physical_vulnerability', 0.0)
            
        # 元素易伤
        vuln += target_stats.get(f"{element.value}_vulnerability", 0.0)
            
        vuln_mult = 1.0 + vuln
        
        # 失衡(Break)状态通常视为一种巨额易伤或独立增幅
        stagger_vuln = 0.3 if is_staggered else 0.0 # 假设失衡提供50%易伤
        
        vuln_mult = 1.0 + vuln + stagger_vuln
        
        # -------------------------------------------------
        # 5. 增幅区 (Amplification Zone) - 稀有独立乘区
        # -------------------------------------------------
        # 来自攻击者的特殊Buff (如: "造成的伤害提高x%，独立计算")
        amp_mult = 1.0 + attacker_stats.get('amplification', 0.0)
        
        # -------------------------------------------------
        # 6. 防御区 (Defense Zone)
        # -------------------------------------------------
        def_mult = 0.5
        
        # -------------------------------------------------
        # 7. 抗性区 (Resistance Zone)
        # -------------------------------------------------
        res_key = f"{element.value}_res"
        raw_res = target_stats.get(res_key, 0.0)
        res_pen = attacker_stats.get('res_pen', 0.0)
        final_res = max(0.0, raw_res - res_pen)
        res_mult = 1.0 - final_res

        # 8. 脆弱区 (Fragility Zone - 独立乘区)
        fragility = target_stats.get('fragility', 0.0) # 通用脆弱
        fragility += target_stats.get(f"{element.value}_fragility", 0.0) # 特定元素脆弱
        fragility_mult = 1.0 + fragility

        
        # -------------------------------------------------
        # 最终汇总
        # -------------------------------------------------
        final_dmg = base_dmg * bonus_mult * crit_mult * vuln_mult * amp_mult * def_mult * res_mult * fragility_mult
        
        return int(max(1, final_dmg))