# entities/characters/wolfguard_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, ReactionType, BuffCategory, BuffEffect
from mechanics.buff_system import Buff, BurningBuff
from .wolfguard_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS


class ScorchingFangBuff(Buff):
    """狼卫天赋：灼热獠牙 - 提供伤害加成"""
    def __init__(self):
        super().__init__(
            "灼热獠牙",
            duration_sec=MECHANICS['passive_duration'],
            category=BuffCategory.BUFF,
            effect_type=BuffEffect.STAT_MODIFIER
        )
        self.bonus = MECHANICS['passive_dmg_bonus']

    def modify_stats(self, stats: dict):
        if "dmg_bonus" in stats:
            stats["dmg_bonus"] += self.bonus


class WolfguardSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("狼卫", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=161, agility=95, intelligence=92, willpower=111)
        self.base_stats = CombatStats(base_hp=5495, base_atk=294, atk_pct=0.0)

        # 主副属性
        self.main_attr = "strength"
        self.sub_attr = "agility"

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
            if res.reaction_type == ReactionType.BURNING:
                self._trigger_passive_one()

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

    # ===== 天赋机制 =====
    def _trigger_passive_one(self):
        """天赋一：触发灼热獠牙"""
        self.buffs.add_buff(ScorchingFangBuff(), self.engine)

    # ===== 命令解析 =====
    def parse_command(self, cmd_str: str):
        parts = cmd_str.split()
        cmd = parts[0].lower()
        if cmd == "wait":
            return Action(f"等待", int(float(parts[1])*10), [])
        if cmd.startswith("a") and cmd[1:].isdigit():
            return self.create_normal_attack(int(cmd[1:]) - 1)
        if cmd in ["skill", "e"]:
            if self.cooldowns.get("skill", 0) > 0:
                return None
            self.cooldowns["skill"] = 120  # CD设置移到这里
            return self.create_skill()
        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0:
                return None
            self.cooldowns["ult"] = 300
            return self.create_ult()
        if cmd == "qte":
            if self.target.reaction_mgr.has_magic_attachment():
                return self.create_qte()
            return None
        return Action("未知", 0, [])

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, len(mvs)-1)  # 统一使用动态计算
        mv = mvs[idx]
        f_data = frames[idx]

        def perform():
            self._deal_damage(mv, MoveType.NORMAL, apply_element=True)
        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        f_data = FRAME_DATA["skill"]
        events = []
        context = {"consumed": False}

        def hit_base():
            # CD已经在parse_command中设置，这里移除
            mv = SKILL_MULTIPLIERS["skill_base"]
            has_burn = self.target.buffs.consume_tag(ReactionType.BURNING)
            has_conduct = self.target.buffs.consume_tag(ReactionType.CONDUCTIVE)

            if has_burn or has_conduct:
                context["consumed"] = True
                self.engine.log(f"   [战技] 成功消耗异常状态！")
                refund = MECHANICS["skill_refund"]
                self.cooldowns["skill"] = max(0, self.cooldowns["skill"] - refund)
                self.engine.log(f"   [天赋] CD减少 {refund/10.0}秒")
                self._deal_damage(mv, MoveType.SKILL, apply_element=False)
            else:
                self._deal_damage(mv, MoveType.SKILL, apply_element=True)

        def hit_extra():
            if context["consumed"]:
                mv = SKILL_MULTIPLIERS["skill_extra"]
                self.engine.log(f"   >>> [战技] 追加射击！")
                self._deal_damage(mv, MoveType.SKILL, apply_element=False)

        events.append(DamageEvent(f_data['hit'], hit_base))
        events.append(DamageEvent(f_data['extra_hit'], hit_extra))
        return Action("灼热弹痕", f_data['total'], events)

    def create_ult(self):
        f_data = FRAME_DATA["ult"]
        events = []
        for i in range(5):
            def hit(idx=i):
                mv = SKILL_MULTIPLIERS["ult_hit"]
                DamageEngine.calculate(
                    self.get_current_panel(), self.target.get_defense_stats(), 
                    mv, Element.HEAT, move_type=MoveType.ULTIMATE
                )
                if idx == 4:
                    self.engine.log("   [终结技] 强制施加 <燃烧>")
                    burn_dmg = self.get_current_panel()['final_atk'] * 0.2
                    self.target.buffs.add_buff(BurningBuff(burn_dmg), self.engine)
                    self._trigger_passive_one()
            events.append(DamageEvent(f_data['hit'] + i*f_data['interval'], hit))
        return Action("狼之怒", f_data['total'], events)

    def create_qte(self):
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]

        def perform():
            self.engine.log("   [连携技] 爆裂手雷投掷！")
            self._deal_damage(mv, MoveType.QTE, apply_element=True)

        return Action("爆裂手雷", f_data['total'], [DamageEvent(f_data['hit'], perform)])