from simulation.engine import SimEngine
from mechanics.buff_system import BuffManager
from mechanics.reaction_manager import ReactionManager

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
        stats = {
            # 易伤区
            "defense": self.defense,
            "vulnerability": 0.0,       # 通用易伤
            "magic_vulnerability": 0.0,    # 元素易伤
            "physical_vulnerability": 0.0, # 物理易伤
            "electric_vulnerability": 0.0, # 电磁易伤
            "heat_vulnerability": 0.0,     # 灼热易伤
            "cold_vulnerability": 0.0,     # 冰霜易伤
            "nature_vulnerability": 0.0,   # 自然易伤
            # 脆弱区
            "fragility": 0.0,           # 通用脆弱
            "heat_fragility": 0.0,      # 灼热脆弱
            "electric_fragility": 0.0,  # 电磁脆弱
            "cold_fragility": 0.0,      # 冰霜脆弱
            "nature_fragility": 0.0,    # 自然脆弱
        }

        # 应用失衡易伤
        if self.is_staggered:
            stagger_vuln = getattr(self.engine.config, 'stagger_vuln_multiplier', 1.3) - 1.0
            stats['vulnerability'] += stagger_vuln

        for k, v in self.resistances.items():
            stats[f"{k}_res"] = v

        return self.buffs.apply_stats(stats)

    def take_damage(self, amount):
        self.total_damage_taken += amount

    def add_buff(self, buff, engine):
        self.buffs.add_buff(buff, engine)