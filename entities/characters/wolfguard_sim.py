from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType
from mechanics.buff_system import Buff, BurningBuff
from .wolfguard_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS

class ScorchingFangBuff(Buff):
    """天赋一：灼热獠牙"""
    def __init__(self):
        super().__init__("灼热獠牙", duration_sec=MECHANICS['passive_duration'], tags=["buff", "dmg_bonus"])
        self.bonus = MECHANICS['passive_dmg_bonus']
    def modify_stats(self, stats: dict):
        if "dmg_bonus" in stats:
            stats["dmg_bonus"] += self.bonus

class WolfguardSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("狼卫", engine)
        self.target = target
        self.attrs = Attributes(strength=161, agility=95, intelligence=92, willpower=111)
        self.base_stats = CombatStats(base_hp=5495, base_atk=294, atk_pct=0.0)

    def get_current_panel(self):
        # 1. 构建原始数据字典
        stats = {
            "base_atk": self.base_stats.base_atk + self.base_stats.weapon_atk,
            "atk_pct": self.base_stats.atk_pct,
            "flat_atk": self.base_stats.flat_atk,
            
            # 其他属性
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
        
        # 2. 应用 Buff (此时Buff可以修改 atk_pct)
        stats = self.buffs.apply_stats(stats)
        
        # 3. 计算 Final ATK
        # 公式：基础区 * (1+百分比) + 固定
        base_zone = stats["base_atk"] * (1 + stats["atk_pct"]) + stats["flat_atk"]
        
        # 属性系数 (独立)
        attr_mult = self.base_stats.get_attr_multiplier(self.attrs, "strength", "agility")
        
        # 写入 Final ATK 供计算器使用
        stats["final_atk"] = base_zone * attr_mult
        
        return stats

    def _deal_dmg_and_react(self, mv, move_type, apply_heat=False):
        panel = self.get_current_panel()
        extra_mv = 0
        if apply_heat:
            ex_mv, r_type, log = self.target.reaction_mgr.apply_hit(
                Element.HEAT, attacker_atk=panel['final_atk']
            )
            extra_mv = ex_mv
            if log: self.engine.log(f"   [{log}]")
            if r_type == "burning":
                self._trigger_passive_one()

        dmg = DamageEngine.calculate(
            panel, self.target.get_defense_stats(), 
            mv + extra_mv, Element.HEAT, move_type=move_type
        )
        self.target.take_damage(dmg)
        self.engine.log(f"   💥 Hit造成伤害: {dmg}")

    def _trigger_passive_one(self):
        self.buffs.add_buff(ScorchingFangBuff(), self.engine)

    def parse_command(self, cmd_str: str):
        parts = cmd_str.split()
        cmd = parts[0].lower()
        if cmd == "wait":
            return Action(f"等待", int(float(parts[1])*10), [])
        if cmd.startswith("a") and cmd[1:].isdigit():
            return self.create_normal_attack(int(cmd[1:]) - 1)
        if cmd in ["skill", "e"]:
            if self.cooldowns.get("skill", 0) > 0: return None
            return self.create_skill()
        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0: return None
            self.cooldowns["ult"] = 300
            return self.create_ult()
        if cmd == "qte":
            if self.target.reaction_mgr.has_magic_attachment():
                 return self.create_qte()
            return None
        return Action("未知", 0, [])

    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, 3)
        mv = mvs[idx]
        f_data = frames[idx]
        def perform():
            self._deal_dmg_and_react(mv, MoveType.NORMAL, apply_heat=True)
        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        f_data = FRAME_DATA["skill"]
        events = []
        context = {"consumed": False}

        def hit_base():
            self.cooldowns["skill"] = 120
            mv = SKILL_MULTIPLIERS["skill_base"]
            has_burn = self.target.buffs.consume_tag("burning")
            has_conduct = self.target.buffs.consume_tag("conductive")
            
            if has_burn or has_conduct:
                context["consumed"] = True
                self.engine.log(f"   [战技] 成功消耗异常状态！")
                refund = MECHANICS["skill_refund"]
                self.cooldowns["skill"] = max(0, self.cooldowns["skill"] - refund)
                self.engine.log(f"   [天赋] CD减少 {refund/10.0}秒")
                self._deal_dmg_and_react(mv, MoveType.SKILL, apply_heat=False)
            else:
                self._deal_dmg_and_react(mv, MoveType.SKILL, apply_heat=True)

        def hit_extra():
            if context["consumed"]:
                mv = SKILL_MULTIPLIERS["skill_extra"]
                self.engine.log(f"   >>> [战技] 追加射击！")
                self._deal_dmg_and_react(mv, MoveType.SKILL, apply_heat=False)

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
            self._deal_dmg_and_react(mv, MoveType.QTE, apply_heat=True)
        return Action("爆裂手雷", f_data['total'], [DamageEvent(f_data['hit'], perform)])