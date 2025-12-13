from enum import Enum

class Element(Enum):
    PHYSICAL = "physical"
    HEAT = "heat"        # 灼热
    ELECTRIC = "electric"# 电磁
    FROST = "frost"      # 寒冷
    NATURE = "nature"    # 自然

class PhysAnomalyType(Enum):
    NONE = "none"
    BREAK = "break"      # 破防
    IMPACT = "impact"    # 猛击
    SHATTER = "shatter"  # 碎甲
    LAUNCH = "launch"    # 击飞
    KNOCKDOWN = "down"   # 倒地

class StatType(Enum):
    STR = "strength"
    AGI = "agility"
    INT = "intelligence"
    WIL = "willpower"

class MoveType(Enum):
    NORMAL = "normal"      # 普攻
    SKILL = "skill"        # 战技
    ULTIMATE = "ultimate"  # 终结技
    QTE = "qte"            # 连携技
    OTHER = "other"        # 其他 (如燃烧伤害)