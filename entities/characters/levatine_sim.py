# entities/characters/levatine_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, ReactionType, BuffCategory
from mechanics.buff_system import Buff, BurningBuff
from .levatine_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS

class HeatInflict(Buff):
    """莱瓦汀天赋：灼热附着 - 标记目标"""
    def __init__(self):
        super().__init__("灼热附着", duration_sec=20.0, category=BuffCategory.NEUTRAL)
        self.tags.append("heat_inflict")  # 添加自定义标签


class LevatineSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("莱瓦汀", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=121, agility=99, intelligence=197, willpower=89)
        self.base_stats = CombatStats(base_hp=5495, base_atk=318)

        # 主副属性
        self.main_attr = "intelligence"
        self.sub_attr = "strength"

        # 机制状态
        self.molten_stacks = 0
        self.ult_duration_ticks = 0

    # ===== 状态管理 =====
    def on_tick(self, engine):
        if self.ult_duration_ticks > 0:
            self.ult_duration_ticks -= 1
            if self.ult_duration_ticks == 0:
                engine.log(f"[{self.name}] 终结技状态结束")
        super().on_tick(engine)

    @property
    def is_ult_active(self):
        return self.ult_duration_ticks > 0

    def _modify_panel_before_buffs(self, stats):
        if self.molten_stacks >= 4:
            stats['res_pen'] += MECHANICS['heat_res_shred']

    # ===== 伤害计算 =====
    def _deal_damage(self, mv, move_type, apply_element=True):
        """统一伤害计算方法"""
        panel = self.get_current_panel()
        extra_mv = 0
        is_reaction = False

        if apply_element:
            res = self.target.reaction_mgr.apply_hit(
                Element.HEAT,
                attacker_atk=panel['final_atk'],
                attacker_tech=panel['technique_power'],
                attacker_lvl=panel['level'],
                attacker_name=self.name
            )
            extra_mv = res.extra_mv
            is_reaction = extra_mv > 0
            if res.log_msg:
                self.engine.log(f"   [{res.log_msg}]")

        # 分别计算基础伤害和反应伤害
        base_dmg = DamageEngine.calculate(
            panel, self.target.get_defense_stats(),
            mv, Element.HEAT, move_type=move_type
        )

        reaction_dmg = 0
        if extra_mv > 0:
            reaction_dmg = DamageEngine.calculate(
                panel, self.target.get_defense_stats(),
                extra_mv, Element.HEAT, move_type=move_type
            )

        total_dmg = base_dmg + reaction_dmg
        self.target.take_damage(total_dmg)
        self.engine.log(f"   [伤害] Hit造成伤害: {total_dmg}")

        # 记录到统计系统
        if hasattr(self.engine, 'statistics'):
            import random
            crit_rate = panel.get('crit_rate', 0.0)
            is_crit = random.random() < crit_rate

            # 记录基础技能伤害
            self.engine.statistics.record_damage(
                tick=self.engine.tick,
                source=self.name,
                target=self.target.name,
                skill_name=self.current_action.name if self.current_action else "未知技能",
                damage=base_dmg,
                element=Element.HEAT,
                move_type=move_type,
                is_crit=is_crit,
                is_reaction=False
            )

            # 如果有反应伤害，单独记录
            if reaction_dmg > 0:
                self.engine.statistics.record_damage(
                    tick=self.engine.tick,
                    source=self.name,
                    target=self.target.name,
                    skill_name="元素反应",
                    damage=reaction_dmg,
                    element=Element.HEAT,
                    move_type=MoveType.OTHER,
                    is_crit=False,
                    is_reaction=True
                )

    # ===== 命令解析 =====
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

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        key = "enhanced_normal" if self.is_ult_active else "normal"
        mvs = SKILL_MULTIPLIERS[key]
        frames = FRAME_DATA[key]
        idx = min(seq_index, len(mvs)-1)
        mv = mvs[idx]
        f_data = frames[min(seq_index, len(frames)-1)]

        def perform():
            self._deal_damage(mv, MoveType.NORMAL, apply_element=True)
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
            self._deal_damage(SKILL_MULTIPLIERS['skill_initial'], MoveType.SKILL, apply_element=True)
            self.molten_stacks = min(4, self.molten_stacks + 1)
            self.engine.log(f"   (状态) 熔火层数: {self.molten_stacks}")
        
        def hit_burst():
            if self.molten_stacks >= 4:
                self.molten_stacks = 0
                self.engine.log(f"   >>> 熔火核爆！")

                # 核爆伤害
                self._deal_damage(SKILL_MULTIPLIERS['skill_burst'], MoveType.SKILL, apply_element=True)
                
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