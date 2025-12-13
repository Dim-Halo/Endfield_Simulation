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

    def on_tick(self, engine: SimEngine):
        self.buffs.tick_all(engine)

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
        for k, v in self.resistances.items():
            stats[f"{k}_res"] = v
        
        return self.buffs.apply_stats(stats)

    def take_damage(self, amount):
        self.total_damage_taken += amount

    def add_buff(self, buff, engine):
        self.buffs.add_buff(buff, engine)