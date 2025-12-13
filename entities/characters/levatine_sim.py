# entities/levatine_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType
from mechanics.buff_system import BurningBuff, Buff
from .levatine_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS

class HeatInflict(Buff):
    def __init__(self):
        super().__init__("灼热附着", duration_sec=20.0, tags=["heat_inflict"])

class LevatineSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("莱瓦汀", engine)
        self.target = target
        
        self.attrs = Attributes(strength=121, agility=99, intelligence=197, willpower=89)
        self.base_stats = CombatStats(base_hp = 5495, base_atk=318)
        
        self.molten_stacks = 0
        self.ult_duration_ticks = 0

    def on_tick(self, engine):
        if self.ult_duration_ticks > 0:
            self.ult_duration_ticks -= 1
            if self.ult_duration_ticks == 0:
                engine.log(f"[{self.name}] 终结技状态结束")
        super().on_tick(engine)

    @property
    def is_ult_active(self):
        return self.ult_duration_ticks > 0

    def get_current_panel(self):
        # 1. 暴露基础数据
        stats = {
            "base_atk": self.base_stats.base_atk + self.base_stats.weapon_atk,
            "atk_pct": self.base_stats.atk_pct,
            "flat_atk": self.base_stats.flat_atk,
            
            "dmg_bonus": self.base_stats.dmg_bonus,
            "crit_rate": self.base_stats.crit_rate,
            "crit_dmg": self.base_stats.crit_dmg,
            "res_pen": self.base_stats.res_pen,
            "amplification": self.base_stats.amplification,
            
            # 特定增伤
            "normal_dmg_bonus": self.base_stats.normal_dmg_bonus,
            "skill_dmg_bonus": self.base_stats.skill_dmg_bonus,
            "ult_dmg_bonus": self.base_stats.ult_dmg_bonus,
            "qte_dmg_bonus": self.base_stats.qte_dmg_bonus,
        }
        
        # 2. 莱瓦汀天赋 (熔火层数加穿透)
        if self.molten_stacks >= 4:
            stats['res_pen'] += MECHANICS['heat_res_shred']

        # 3. 应用 Buff (允许修改 atk_pct)
        stats = self.buffs.apply_stats(stats)
        
        # 4. 计算 Final ATK
        base_zone = stats["base_atk"] * (1 + stats["atk_pct"]) + stats["flat_atk"]
        attr_mult = self.base_stats.get_attr_multiplier(self.attrs, "intelligence", "strength")
        stats["final_atk"] = base_zone * attr_mult
        
        return stats

    # --- 辅助：统一伤害处理 ---
    def _deal_dmg_and_react(self, mv, move_type, apply_heat=True):
        panel = self.get_current_panel()
        extra_mv = 0
        
        # 元素反应判定
        if apply_heat:
            ex_mv, r_type, log = self.target.reaction_mgr.apply_hit(
                Element.HEAT, attacker_atk=panel['final_atk']
            )
            extra_mv = ex_mv
            if log: self.engine.log(f"   [{log}]")

        # 1. 计算
        dmg = DamageEngine.calculate(
            panel, self.target.get_defense_stats(), 
            mv + extra_mv, Element.HEAT, move_type=move_type
        )
        
        # 2. 应用伤害
        self.target.take_damage(dmg)
        self.engine.log(f"   💥 Hit造成伤害: {dmg}")

    # --- 解析器 ---
    def parse_command(self, cmd_str: str):
        parts = cmd_str.split()
        cmd = parts[0].lower()

        if cmd == "wait":
            return Action(f"等待", int(float(parts[1])*10), [])
        if cmd.startswith("a") and cmd[1:].isdigit():
            return self.create_normal_attack(int(cmd[1:]) - 1)
        if cmd in ["skill", "e"]:
            if self.cooldowns.get("skill", 0) > 0: return None
            # 简化：假设技能命中给3层方便演示核爆
            self.molten_stacks = 3 
            self.cooldowns["skill"] = 100 
            return self.create_skill()
        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0: return None
            self.cooldowns["ult"] = 300
            return self.create_ult()

        return Action("未知", 0, [])

    # --- 动作工厂 ---
    def create_normal_attack(self, seq_index):
        key = "enhanced_normal" if self.is_ult_active else "normal"
        mvs = SKILL_MULTIPLIERS[key]
        frames = FRAME_DATA[key]
        idx = min(seq_index, len(mvs)-1)
        mv = mvs[idx]
        f_data = frames[min(seq_index, len(frames)-1)]

        def perform():
            self._deal_dmg_and_react(mv, MoveType.NORMAL, apply_heat=True)
            # 强化普攻天赋
            if self.is_ult_active and (seq_index + 1) in [2, 4]:
                self.target.buffs.add_buff(HeatInflict(), self.engine)
            # 吸收天赋
            is_last = (seq_index == 4) if not self.is_ult_active else False
            if is_last and self.target.buffs.consume_tag("heat_inflict"):
                 self.molten_stacks = min(4, self.molten_stacks + 1)
                 self.engine.log(f"   [天赋] 吸收附着！层数: {self.molten_stacks}")

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        f_data = FRAME_DATA['skill']
        events = []
        
        def hit_init():
            self._deal_dmg_and_react(SKILL_MULTIPLIERS['skill_initial'], MoveType.SKILL, apply_heat=True)
            self.molten_stacks = min(4, self.molten_stacks + 1)
            self.engine.log(f"   (状态) 熔火层数: {self.molten_stacks}")
        
        def hit_burst():
            if self.molten_stacks >= 4:
                self.molten_stacks = 0
                self.engine.log(f"   >>> 熔火核爆！")
                
                # 核爆伤害
                self._deal_dmg_and_react(SKILL_MULTIPLIERS['skill_burst'], MoveType.SKILL, apply_heat=True)
                
                # 强制施加燃烧
                stats = self.get_current_panel()
                burn_dmg = stats['final_atk'] * (SKILL_MULTIPLIERS['skill_dot'] / 100.0)
                self.target.buffs.add_buff(BurningBuff(burn_dmg), self.engine)

        events.append(DamageEvent(f_data['hit_init'], hit_init))
        events.append(DamageEvent(f_data['hit_burst'], hit_burst))
        return Action("灼热荆棘", f_data['total'], events)

    def create_ult(self):
        f_data = FRAME_DATA['ult']
        def activate():
            self.ult_duration_ticks = 150
            self.engine.log("   >>> 进入强化状态")
        return Action("黄昏", f_data['total'], [DamageEvent(f_data['hit'], activate)])