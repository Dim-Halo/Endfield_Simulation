# core/stats.py
from dataclasses import dataclass, field
from .enums import StatType

@dataclass
class Attributes:
    strength: int = 0
    agility: int = 0
    intelligence: int = 0
    willpower: int = 0

class StatKey:
    """属性键名常量"""
    LEVEL = "level"
    BASE_HP = "base_hp"
    BASE_DEF = "base_def"
    BASE_ATK = "base_atk"
    WEAPON_ATK = "weapon_atk"
    ATK_PCT = "atk_pct"
    FLAT_ATK = "flat_atk"
    TECH_POWER = "technique_power"
    TECH_PCT = "tech_pct"
    
    # 最终属性 (CombatStats不直接存，但在 get_current_panel 中计算)
    FINAL_ATK = "final_atk"
    
    # 增伤
    DMG_BONUS = "dmg_bonus"
    NORMAL_DMG_BONUS = "normal_dmg_bonus"
    SKILL_DMG_BONUS = "skill_dmg_bonus"
    ULT_DMG_BONUS = "ult_dmg_bonus"
    QTE_DMG_BONUS = "qte_dmg_bonus"
    
    # 元素增伤
    HEAT_DMG_BONUS = "heat_dmg_bonus"
    ELECTRIC_DMG_BONUS = "electric_dmg_bonus"
    FROST_DMG_BONUS = "frost_dmg_bonus"
    NATURE_DMG_BONUS = "nature_dmg_bonus"
    PHYSICAL_DMG_BONUS = "physical_dmg_bonus"
    
    # 暴击
    CRIT_RATE = "crit_rate"
    CRIT_DMG = "crit_dmg"
    
    # 穿透
    RES_PEN = "res_pen"
    
    # 增幅
    AMPLIFICATION = "amplification"
    SPECIAL_BONUS = "special_bonus"
    HEAL_BONUS = "heal_bonus"
    
    # 防御/易伤属性 (在 get_defense_stats 中使用)
    DEFENSE = "defense"
    PHYS_RES = "physical_res"
    MAGIC_RES = "magic_res"
    VULNERABILITY = "vulnerability"
    PHYS_VULN = "physical_vulnerability"
    MAGIC_VULN = "magic_vulnerability"
    FRAGILITY = "fragility"
    
    # 元素脆弱
    HEAT_FRAGILITY = "heat_fragility"
    ELECTRIC_FRAGILITY = "electric_fragility"
    FROST_FRAGILITY = "frost_fragility"
    NATURE_FRAGILITY = "nature_fragility"
    PHYSICAL_FRAGILITY = "physical_fragility"

@dataclass
class CombatStats:
    # --- 1. 基础区 ---
    level: int = 90
    base_hp: float = 0      # 基础生命
    base_def: float = 0     # 基础防御

    base_atk: float = 0
    weapon_atk: float = 0

    atk_pct: float = 0.0      # 攻击力%
    flat_atk: float = 0.0     # 固定攻击力

    # 源石技艺强度
    technique_power: float = 0.0
    tech_pct: float = 0.0      # 源石技艺强度%

    # --- 2. 增伤区 (Damage Bonus) ---
    # 全区增伤
    dmg_bonus: float = 0.0

    # 招式增伤
    normal_dmg_bonus: float = 0.0 # 普攻增伤
    skill_dmg_bonus: float = 0.0  # 战技增伤
    ult_dmg_bonus: float = 0.0    # 大招增伤
    qte_dmg_bonus: float = 0.0    # 连携技增伤

    # 元素增伤
    heat_dmg_bonus: float = 0.0
    electric_dmg_bonus: float = 0.0
    frost_dmg_bonus: float = 0.0
    nature_dmg_bonus: float = 0.0
    physical_dmg_bonus: float = 0.0
    
    # --- 3. 暴击区 (Critical) ---
    crit_rate: float = 0.05
    crit_dmg: float = 0.50
    
    # --- 4. 穿透区 (Penetration) ---
    res_pen: float = 0.0      # 抗性穿透
    
    # --- 5. 增幅区 (Amplification - 独立乘区) ---
    # 极少见的乘区，通常来自特殊大招或核心被动
    amplification: float = 0.0

    # 特殊加成区(如连击)
    special_bonus: float = 0.0

    # 治疗加成
    heal_bonus: float = 0.0

    def get_attr_multiplier(self, attrs: Attributes, main_attr: str, sub_attr: str):
        """仅计算属性转化系数 (独立乘区)"""
        main_val = getattr(attrs, main_attr)
        sub_val = getattr(attrs, sub_attr)
        # 公式：1 + 主*0.5% + 副*0.2%
        return 1.0 + (main_val * 0.005) + (sub_val * 0.002)
    
    def calculate_max_hp(self, attrs: Attributes):
        """
        计算最大生命值
        公式: 基础生命 + 力量 * 5
        """
        return self.base_hp + (attrs.strength * 5)

    def calculate_phys_res(self, attrs: Attributes):
        """
        计算物理抗性 (敏捷衍生)
        公式: 100 - 100 / (0.001 * 敏捷 + 1) (点数)
        返回百分比 (0.0 - 1.0)
        """
        if attrs.agility == 0:
            return 0.0
        
        # 计算抗性点数
        res_points = 100.0 - (100.0 / (0.001 * attrs.agility + 1.0))
        # 转化为百分比 (1点 = 1%)
        return res_points / 100.0

    def calculate_magic_res(self, attrs: Attributes):
        """
        计算法术抗性 (智识衍生)
        公式: 100 - 100 / (0.001 * 智识 + 1) (点数)
        返回百分比 (0.0 - 1.0)
        """
        if attrs.intelligence == 0:
            return 0.0
            
        # 计算抗性点数
        res_points = 100.0 - (100.0 / (0.001 * attrs.intelligence + 1.0))
        return res_points / 100.0

    def calculate_healing_received(self, attrs: Attributes):
        """
        计算受治疗效率 (意志衍生)
        公式: (意志/10)%
        例如: 35意志 -> 3.5% -> 0.035
        """
        return (attrs.willpower / 10.0) / 100.0