# entities/characters/erdila_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType, ReactionType
from mechanics.buff_system import Buff, CorrosionBuff, VulnerabilityBuff
from .erdila_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS


class ErdilaSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("艾尔黛拉", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=112, agility=93, intelligence=145, willpower=118)
        self.base_stats = CombatStats(base_hp=5495, base_atk=323, atk_pct=0.0)

        # 主副属性
        self.main_attr = "intelligence"
        self.sub_attr = "willpower"

    # ===== 天赋机制 =====
    def _perform_heal(self):
        """天赋一：多利影子治疗"""
        panel = self.get_current_panel()
        wil = self.attrs.willpower

        # 公式: [基础 + 意志 * 倍率] * (1 + 治疗加成)
        base_heal = MECHANICS['heal_base'] + wil * MECHANICS['heal_scale']
        final_heal = base_heal * (1.0 + panel.get('heal_bonus', 0.0))

        self.engine.log(f"   [治疗] 艾尔黛拉回复全队 {int(final_heal)} 点生命值")

    # ===== 伤害计算 =====
    def _deal_damage(self, mv, move_type, apply_element=True):
        """统一伤害计算方法"""
        panel = self.get_current_panel()
        extra_mv = 0
        is_reaction = False

        if apply_element:
            res = self.target.reaction_mgr.apply_hit(
                Element.NATURE,
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
            mv, Element.NATURE, move_type=move_type
        )

        reaction_dmg = 0
        if extra_mv > 0:
            reaction_dmg = DamageEngine.calculate(
                panel, self.target.get_defense_stats(),
                extra_mv, Element.NATURE, move_type=move_type
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
                element=Element.NATURE,
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
                    element=Element.NATURE,
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
            if self.cooldowns.get("skill", 0) > 0:
                return None
            self.cooldowns["skill"] = 150
            return self.create_skill()

        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0:
                return None
            self.cooldowns["ult"] = 300
            return self.create_ult()

        if cmd == "qte":
            # 连携条件: 敌人不处于破防 且 不处于法术附着
            has_attach = self.target.reaction_mgr.has_magic_attachment()
            has_break = self.target.reaction_mgr.phys_break_stacks > 0

            if not has_attach and not has_break:
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
        """战技：奔腾的多利"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]

        def hit():
            # 检测腐蚀
            has_corrosion = self.target.buffs.consume_tag(ReactionType.CORROSION)

            # 造成伤害
            self._deal_damage(mv, MoveType.SKILL, apply_element=True)

            # 产生影子治疗
            self._perform_heal()

            # 如果消耗了腐蚀 -> 施加双脆弱
            if has_corrosion:
                self.engine.log("   [战技] 消耗腐蚀！施加物理/法术脆弱，并触发二次冲撞！")
                dur = MECHANICS['vuln_duration']
                val = MECHANICS['vuln_value']

                # 施加脆弱
                self.target.buffs.add_buff(
                    VulnerabilityBuff("物理脆弱", dur, val, vuln_type="physical"), self.engine
                )
                self.target.buffs.add_buff(
                    VulnerabilityBuff("法术脆弱", dur, val, vuln_type="magic"), self.engine
                )

                # 天赋二：山顶冲浪
                self.engine.log("   >>> [天赋] 山顶冲浪：额外冲撞！")
                self._deal_damage(mv, MoveType.SKILL, apply_element=False)

        return Action("奔腾的多利", f_data['total'], [DamageEvent(f_data['hit'], hit)])

    def create_qte(self):
        """连携技：火山蘑菇云"""
        f_data = FRAME_DATA["qte"]

        def hit_throw():
            self.engine.log("   [连携技] 抛出火山云...")
            self._deal_damage(SKILL_MULTIPLIERS['qte_hit'], MoveType.QTE)

        def hit_explode():
            self.engine.log("   [连携技] 蘑菇云爆炸！强制腐蚀！")
            self._deal_damage(SKILL_MULTIPLIERS['qte_explode'], MoveType.QTE)
            # 强制施加腐蚀
            self.target.buffs.add_buff(CorrosionBuff(duration=MECHANICS['corrosion_duration']), self.engine)

        events = [
            DamageEvent(f_data['hit'], hit_throw),
            DamageEvent(f_data['explode'], hit_explode)
        ]
        return Action("火山蘑菇云", f_data['total'], events)

    def create_ult(self):
        """终结技：毛茸茸派对"""
        f_data = FRAME_DATA["ult"]
        hits = 5
        events = []

        for i in range(hits):
            def hit(idx=i):
                self._deal_damage(SKILL_MULTIPLIERS['ult_hit'], MoveType.ULTIMATE, apply_element=True)
                # 模拟概率掉落影子治疗
                import random
                if random.random() < 0.5:
                    self._perform_heal()

            events.append(DamageEvent(i * f_data['interval'] + 2, hit))

        return Action("毛茸茸派对", f_data['total'], events)