# entities/characters/antal_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType
from mechanics.buff_system import ElementalDmgBuff, FragilityBuff, FocusDebuff
from .antal_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS


class AntalSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("安塔尔", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=129, agility=86, intelligence=165, willpower=82)
        self.base_stats = CombatStats(base_hp=5495, base_atk=297, atk_pct=0.0)

        # 主副属性
        self.main_attr = "intelligence"
        self.sub_attr = "strength"

        # 天赋一冷却记录
        self.passive_heal_cd = {}

    # ===== 状态管理 =====
    def on_tick(self, engine):
        super().on_tick(engine)
        # 冷却倒计时
        for name in list(self.passive_heal_cd.keys()):
            if self.passive_heal_cd[name] > 0:
                self.passive_heal_cd[name] -= 1

    # ===== 天赋机制 =====
    def check_passive_heal(self, actor):
        """天赋一：即兴发挥 - 增幅状态下回复生命"""
        has_amp = actor.buffs.has_tag("electric_buff") or actor.buffs.has_tag("heat_buff")

        if has_amp and self.passive_heal_cd.get(actor.name, 0) == 0:
            heal = MECHANICS['passive_heal_base'] + self.attrs.strength * MECHANICS['passive_heal_scale']
            self.engine.log(f"   [天赋] 安塔尔为 {actor.name} 回复 {int(heal)} 生命")
            self.passive_heal_cd[actor.name] = MECHANICS['passive_cd']

    # ===== 伤害计算 =====
    def _deal_damage(self, mv, move_type, apply_element=True):
        """统一伤害计算方法"""
        panel = self.get_current_panel()

        # 安塔尔总是触发电属性反应
        res = self.target.reaction_mgr.apply_hit(
            Element.ELECTRIC,
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
            mv, Element.ELECTRIC, move_type=move_type
        )

        reaction_dmg = 0
        if extra_mv > 0:
            reaction_dmg = DamageEngine.calculate(
                panel, self.target.get_defense_stats(),
                extra_mv, Element.ELECTRIC, move_type=move_type
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
                element=Element.ELECTRIC,
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
                    element=Element.ELECTRIC,
                    move_type=MoveType.OTHER,
                    is_crit=False,
                    is_reaction=True
                )

        if move_type == MoveType.SKILL:
            self.check_passive_heal(self)

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
            # 连携条件: 聚焦 AND (物理异常 OR 法术附着)
            is_focused = self.target.buffs.has_tag("focus")  # 使用字符串tag
            has_attach = self.target.reaction_mgr.has_magic_attachment()
            has_break = self.target.reaction_mgr.phys_break_stacks > 0

            if is_focused and (has_attach or has_break):
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
            self._deal_damage(mv, MoveType.NORMAL)

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：指定研究对象"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]

        def hit():
            self._deal_damage(mv, MoveType.SKILL)

            # 施加 Debuff
            dur = MECHANICS['skill_fragility_dur']
            val = MECHANICS['skill_fragility_val']
            self.engine.log("   [战技] 施加聚焦 & 电/火脆弱 (独立乘区)")

            # 聚焦
            self.target.buffs.add_buff(FocusDebuff(duration=dur), self.engine)
            # 脆弱
            self.target.buffs.add_buff(FragilityBuff("电磁脆弱", dur, val, "electric"), self.engine)
            self.target.buffs.add_buff(FragilityBuff("灼热脆弱", dur, val, "heat"), self.engine)

        return Action("指定研究对象", f_data['total'], [DamageEvent(f_data['hit'], hit)])

    def create_ult(self):
        """终结技：超频时刻"""
        f_data = FRAME_DATA["ult"]
        
        def activate():
            self.engine.log("   >>> [终结技] 全队电/火增幅！")
            dur = MECHANICS['ult_buff_dur']
            val = MECHANICS['ult_buff_val']
            
            # 给全队加增幅 (遍历 engine.entities 中有 buffs 属性的角色)
            for ent in self.engine.entities:
                if hasattr(ent, "buffs") and hasattr(ent, "attrs"): # 简单的判定是角色
                    ent.buffs.add_buff(ElementalDmgBuff("电磁增幅", dur, "electric", val), self.engine)
                    ent.buffs.add_buff(ElementalDmgBuff("灼热增幅", dur, "heat", val), self.engine)

        return Action("超频时刻", f_data['total'], [DamageEvent(f_data['hit'], activate)])

    def create_qte(self):
        """连携技：磁暴试验场"""
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]

        def perform():
            self.engine.log("   [连携技] 能量爆炸！")

            # 记录当前状态
            current_elem = self.target.reaction_mgr.attachment_element
            current_break = self.target.reaction_mgr.phys_break_stacks

            # 造成伤害
            self._deal_damage(mv, MoveType.QTE)

            # 强制恢复/再次施加状态
            if current_elem:
                self.target.reaction_mgr.apply_hit(current_elem)
                self.engine.log(f"   [连携技] 刷新/再次施加: {current_elem.value}")
            elif current_break > 0:
                self.target.reaction_mgr.apply_hit(Element.PHYSICAL, PhysAnomalyType.BREAK)
                self.engine.log(f"   [连携技] 刷新物理破防")

        return Action("磁暴试验场", f_data['total'], [DamageEvent(f_data['hit'], perform)])