from enum import Enum

class Element(Enum):
    PHYSICAL = "physical"
    HEAT = "heat"
    ELECTRIC = "electric"
    FROST = "frost"
    NATURE = "nature"

class PhysAnomalyType(Enum):
    NONE = "none"
    BREAK = "break"
    IMPACT = "impact"
    SHATTER = "shatter"
    LAUNCH = "launch"
    KNOCKDOWN = "down"

class MoveType(Enum):
    NORMAL = "normal"
    SKILL = "skill"
    ULTIMATE = "ultimate"
    QTE = "qte"
    OTHER = "other"

class StatType(Enum):
    STR = "strength"
    AGI = "agility"
    INT = "intelligence"
    WIL = "willpower"

# Buff分类（正面/负面）
class BuffCategory(Enum):
    BUFF = "buff"           # 正面效果
    DEBUFF = "debuff"       # 负面效果
    NEUTRAL = "neutral"     # 中性效果

# Buff效果类型
class BuffEffect(Enum):
    STAT_MODIFIER = "stat_modifier"  # 属性修改（攻击、暴击等）
    DOT = "dot"                      # 持续伤害
    CC = "cc"                        # 控制效果
    ELEMENTAL_REACTION = "elemental_reaction"  # 元素反应状态

# 【新增】反应类型常量
class ReactionType(Enum):
    NONE = "none"
    ATTACH = "attach"       # 施加附着
    BURST = "burst"         # 法术爆发
    BURNING = "burning"     # 燃烧
    CONDUCTIVE = "conductive" # 导电
    FROZEN = "frozen"       # 冻结
    CORROSION = "corrosion" # 腐蚀
    SHATTER = "shatter"     # 碎冰
    PHYS_ANOMALY = "physical_anomaly" # 物理异常