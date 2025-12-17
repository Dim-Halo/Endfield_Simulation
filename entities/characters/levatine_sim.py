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
            self.cooldowns["skill"] = 100
            return self.create_skill()
        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0: return None
            self.cooldowns["ult"] = 300
            return self.create_ult()
        if cmd == "qte":
            if self.cooldowns.get("qte", 0) > 0: return None
            self.cooldowns["qte"] = 200
            return self.create_qte()

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
            # 强化普攻天赋：第3段施加灼热附着
            if self.is_ult_active and (seq_index + 1) == 3:
                self.target.buffs.add_buff(HeatInflict(), self.engine)
            # 重击失衡：普攻第5段造成18点失衡
            if not self.is_ult_active and seq_index == 4:  # 普通普攻第5段
                self.target.apply_stagger(18.0, self.engine)
            # 吸收天赋
            is_last = (seq_index == 4) if not self.is_ult_active else False
            if is_last and self.target.buffs.consume_tag("heat_inflict"):
                 self.molten_stacks = min(4, self.molten_stacks + 1)
                 self.engine.log(f"   [天赋] 吸收附着！层数: {self.molten_stacks}")

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        f_data = FRAME_DATA['skill']
        events = []

        # 判断施放时是否已有4层熔火
        has_full_stacks = self.molten_stacks >= 4

        def hit_init():
            self._deal_damage(SKILL_MULTIPLIERS['skill_initial'], MoveType.SKILL, apply_element=True)
            if not has_full_stacks:  # 只在非满层时增加
                self.molten_stacks = min(4, self.molten_stacks + 1)
                self.engine.log(f"   (状态) 熔火层数: {self.molten_stacks}")

        def hit_burst():
            self.molten_stacks = 0
            self.engine.log(f"   >>> 熔火核爆！")

            # 核爆伤害
            self._deal_damage(SKILL_MULTIPLIERS['skill_burst'], MoveType.SKILL, apply_element=True)

            # 强制施加燃烧
            stats = self.get_current_panel()
            burn_dmg = stats['final_atk'] * (SKILL_MULTIPLIERS['skill_dot'] / 100.0)
            self.target.buffs.add_buff(BurningBuff(burn_dmg), self.engine)

        events.append(DamageEvent(f_data['hit_init'], hit_init))
        # 只在满层时才追加核爆攻击
        if has_full_stacks:
            events.append(DamageEvent(f_data['hit_burst'], hit_burst))
        return Action("焚灭", f_data['total'], events)

    def create_ult(self):
        f_data = FRAME_DATA['ult']
        def activate():
            self.ult_duration_ticks = 150
            self.engine.log("   >>> 进入强化状态")
        return Action("黄昏", f_data['total'], [DamageEvent(f_data['hit'], activate)])

    def create_qte(self):
        """连携技：沸腾 - 对燃烧/腐蚀状态的敌人造成伤害"""
        f_data = FRAME_DATA['qte']

        def perform():
            # 检查目标是否处于燃烧或腐蚀状态
            has_burning = any(buff.name == "燃烧" for buff in self.target.buffs.active_buffs)
            has_corrosion = any(buff.name == "腐蚀" for buff in self.target.buffs.active_buffs)

            if has_burning or has_corrosion:
                self.engine.log(f"   [QTE] 目标处于燃烧/腐蚀状态，触发沸腾！")
                self._deal_damage(SKILL_MULTIPLIERS['qte'], MoveType.SKILL, apply_element=True)
                # 命中敌人获得1层熔火
                self.molten_stacks = min(4, self.molten_stacks + 1)
                self.engine.log(f"   (状态) 熔火层数: {self.molten_stacks}")
            else:
                self.engine.log(f"   [QTE] 目标未处于燃烧/腐蚀状态，无效果")

        return Action("沸腾", f_data['total'], [DamageEvent(f_data['hit'], perform)])