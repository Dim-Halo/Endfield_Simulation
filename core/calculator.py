from .enums import Element, MoveType
from .stats import StatKey

class DamageEngine:
    @staticmethod
    def calculate(attacker_stats: dict, target_stats: dict, skill_mv: float,
                  element: Element, move_type: MoveType = MoveType.OTHER):
        """
        伤害计算公式（14个乘区）：
        基础伤害区 × 暴击区 × 伤害加成区 × 伤害减免区 × 易伤区 × 增幅区 × 庇护区 ×
        脆弱区 × 防御区 × 失衡易伤区 × 减伤区 × 抗性区 × 非主控减伤区 × 特殊加成区
        """

        # ============================================================
        # 1. 基础伤害区
        # ============================================================
        atk = attacker_stats[StatKey.FINAL_ATK]
        base_dmg = atk * (skill_mv / 100.0)

        # ============================================================
        # 2. 暴击区
        # ============================================================
        c_rate = min(1.0, max(0.0, attacker_stats.get(StatKey.CRIT_RATE, 0.0)))
        c_dmg = attacker_stats.get(StatKey.CRIT_DMG, 0.5)
        crit_mult = 1.0 + (c_rate * c_dmg)

        # ============================================================
        # 3. 伤害加成区（加算）
        # ============================================================
        base_bonus = attacker_stats.get(StatKey.DMG_BONUS, 0.0)

        # 招式增伤
        move_bonus = 0.0
        if move_type == MoveType.NORMAL:
            move_bonus = attacker_stats.get(StatKey.NORMAL_DMG_BONUS, 0.0)
        elif move_type == MoveType.HEAVY:
            # 重击通常享受普攻加成，也可以有独立加成
            move_bonus = attacker_stats.get(StatKey.NORMAL_DMG_BONUS, 0.0) + attacker_stats.get('heavy_dmg_bonus', 0.0)
        elif move_type == MoveType.PLUNGE:
            move_bonus = attacker_stats.get('plunge_dmg_bonus', 0.0)
        elif move_type == MoveType.EXECUTION:
            move_bonus = attacker_stats.get('execution_dmg_bonus', 0.0)
        elif move_type == MoveType.SKILL:
            move_bonus = attacker_stats.get(StatKey.SKILL_DMG_BONUS, 0.0)
        elif move_type == MoveType.ULTIMATE:
            move_bonus = attacker_stats.get(StatKey.ULT_DMG_BONUS, 0.0)
        elif move_type == MoveType.QTE:
            move_bonus = attacker_stats.get(StatKey.QTE_DMG_BONUS, 0.0)

        # 元素增伤
        elem_bonus = attacker_stats.get(f"{element.value}_dmg_bonus", 0.0)

        # 失衡增伤（对失衡目标伤害加成，属于伤害加成区）
        stagger_bonus = 0.0
        if target_stats.get('is_staggered', False):
            stagger_bonus = attacker_stats.get('stagger_dmg_bonus', 0.0)

        bonus_mult = 1.0 + base_bonus + move_bonus + elem_bonus + stagger_bonus

        # ============================================================
        # 4. 伤害减免区（目标的基础伤害减免）
        # ============================================================
        dmg_reduction = target_stats.get('dmg_reduction', 0.0)
        dmg_reduction_mult = 1.0 - dmg_reduction

        # ============================================================
        # 5. 易伤区（Vulnerability - 加算） 
        # ============================================================
        vuln = target_stats.get(StatKey.VULNERABILITY, 0.0)
        if element != Element.PHYSICAL:
            vuln += target_stats.get(StatKey.MAGIC_VULN, 0.0)
        else:
            vuln += target_stats.get(StatKey.PHYS_VULN, 0.0)
        vuln += target_stats.get(f"{element.value}_vulnerability", 0.0)
        vuln_mult = 1.0 + vuln

        # ============================================================
        # 6. 增幅区
        # ============================================================
        amp_mult = 1.0 + attacker_stats.get(StatKey.AMPLIFICATION, 0.0)

        # ============================================================
        # 7. 庇护区（独立乘区）
        # ============================================================
        sanctuary = target_stats.get('sanctuary', 0.0)
        sanctuary_mult = 1.0 - sanctuary

        # ============================================================
        # 8. 脆弱区（Fragility - 独立乘区）
        # ============================================================
        fragility = target_stats.get(StatKey.FRAGILITY, 0.0)
        fragility += target_stats.get(f"{element.value}_fragility", 0.0)
        fragility_mult = 1.0 + fragility

        # ============================================================
        # 9. 防御区
        # ============================================================
        defense = max(0, target_stats.get(StatKey.DEFENSE, 0))
        def_const = 100.0
        def_mult = def_const / (def_const + defense)

        # ============================================================
        # 10. 失衡易伤区（独立 1.3倍）
        # ============================================================
        stagger_vuln_mult = 1.3 if target_stats.get('is_staggered', False) else 1.0

        # ============================================================
        # 11. 减伤区（额外的减伤机制，与伤害减免区不同）
        # ============================================================
        dmg_reduction_extra = target_stats.get('dmg_reduction_extra', 0.0)
        dmg_reduction_extra_mult = 1.0 - dmg_reduction_extra

        # ============================================================
        # 12. 抗性区
        # ============================================================
        res_key = f"{element.value}_res"
        raw_res = target_stats.get(res_key, 0.0)
        res_pen = attacker_stats.get(StatKey.RES_PEN, 0.0)
        final_res = max(0.0, raw_res - res_pen)
        res_mult = 1.0 - final_res

        # ============================================================
        # 13. 非主控减伤区（AI惩罚）
        # ============================================================
        non_main_mult = attacker_stats.get('non_main_penalty', 1.0)

        # ============================================================
        # 14. 特殊加成区
        # ============================================================
        special_mult = 1.0 + attacker_stats.get(StatKey.SPECIAL_BONUS, 0.0)

        # ============================================================
        # 最终汇总（严格按照14个乘区的顺序）
        # ============================================================
        final_dmg = (
            base_dmg *                      # 1. 基础伤害区
            crit_mult *                     # 2. 暴击区
            bonus_mult *                    # 3. 伤害加成区
            dmg_reduction_mult *            # 4. 伤害减免区
            vuln_mult *                     # 5. 易伤区
            amp_mult *                      # 6. 增幅区
            sanctuary_mult *                # 7. 庇护区
            fragility_mult *                # 8. 脆弱区
            def_mult *                      # 9. 防御区
            stagger_vuln_mult *             # 10. 失衡易伤区
            dmg_reduction_extra_mult *      # 11. 减伤区
            res_mult *                      # 12. 抗性区
            non_main_mult *                 # 13. 非主控减伤区
            special_mult                    # 14. 特殊加成区
        )

        return int(final_dmg)