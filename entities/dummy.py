from simulation.engine import SimEngine
from mechanics.buff_system import BuffManager
from mechanics.reaction_manager import ReactionManager

from core.enums import Element, PhysAnomalyType
from core.stats import CombatStats, Attributes, StatKey

class DummyEnemy:
    def __init__(self, engine, name, defense=500, resistances=None):
        self.name = name
        self.engine = engine
        self.defense = defense
        self.resistances = resistances or {}

        self.buffs = BuffManager(self)
        self.reaction_mgr = ReactionManager(self, engine)
        self.total_damage_taken = 0

        # 失衡系统
        self.stagger_gauge = 0.0  # 当前失衡值
        self.stagger_max = 100.0  # 失衡阈值
        self.is_staggered = False # 是否处于失衡状态
        self.stagger_duration = 0 # 失衡持续时间(ticks)

    def on_tick(self, engine: SimEngine):
        self.buffs.tick_all(engine)

        # 处理失衡状态
        if self.is_staggered and self.stagger_duration > 0:
            self.stagger_duration -= 1
            if self.stagger_duration <= 0:
                self.is_staggered = False
                self.stagger_gauge = 0.0
                engine.log(f"[{self.name}] 失衡状态结束")

    def apply_stagger(self, value: float, engine: SimEngine):
        """施加失衡值"""
        if self.is_staggered:
            return  # 已经处于失衡状态，不再增加

        self.stagger_gauge += value
        engine.log(f"   [失衡] 施加 {value} 点失衡值，当前: {self.stagger_gauge}/{self.stagger_max}")

        if self.stagger_gauge >= self.stagger_max:
            self.is_staggered = True
            self.stagger_duration = 50  # 5秒失衡时间
            engine.log(f"   >>> [{self.name}] 进入失衡状态！")

    def get_defense_stats(self):
        """获取防御计算所需的属性快照"""
        # 1. 基础属性
        stats = {
            StatKey.DEFENSE: self.defense,
            StatKey.RES_PEN: 0.0, # 防御方通常没有穿透，但为了通用性
            # 基础抗性
            StatKey.PHYS_RES: self.resistances.get(Element.PHYSICAL, 0.0),
            StatKey.MAGIC_RES: self.resistances.get("magic", 0.0), # 通用法术抗性
            "heat_res": self.resistances.get(Element.HEAT, 0.0),
            "electric_res": self.resistances.get(Element.ELECTRIC, 0.0),
            "frost_res": self.resistances.get(Element.FROST, 0.0),
            "nature_res": self.resistances.get(Element.NATURE, 0.0),
            
            # 状态标记
            "is_staggered": self.is_staggered
        }
        
        # 2. 应用 Buff
        # Dummy 的 buffs 会修改上述 stats，例如添加易伤、削减抗性
        stats = self.buffs.apply_stats(stats)
        
        return stats

    def take_damage(self, amount):
        self.total_damage_taken += amount

    def add_buff(self, buff, engine):
        self.buffs.add_buff(buff, engine)