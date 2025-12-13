from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType
from mechanics.buff_system import ElementalDmgBuff, FragilityBuff, FocusDebuff
from .antal_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS

class AntalSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("安塔尔", engine)
        self.target = target
        
        # 面板数据
        self.attrs = Attributes(strength=129, agility=86, intelligence=165, willpower=82)
        self.base_stats = CombatStats(base_hp=5495, base_atk=297, atk_pct=0.0)
        
        # 天赋一冷却记录 {char_name: remaining_ticks}
        self.passive_heal_cd = {}

    def on_tick(self, engine):
        super().on_tick(engine)
        # 冷却倒计时
        for name in list(self.passive_heal_cd.keys()):
            if self.passive_heal_cd[name] > 0:
                self.passive_heal_cd[name] -= 1

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
            
            # 元素增伤
            "heat_dmg_bonus": self.base_stats.heat_dmg_bonus,
            "electric_dmg_bonus": self.base_stats.electric_dmg_bonus,
        }
        
        # 2. 应用 Buff
        stats = self.buffs.apply_stats(stats)
        
        # 3. 计算 Final ATK
        base_zone = stats["base_atk"] * (1 + stats["atk_pct"]) + stats["flat_atk"]
        # 安塔尔: 主智识(INT), 副力量(STR)
        attr_mult = self.base_stats.get_attr_multiplier(self.attrs, "intelligence", "strength")
        
        stats["final_atk"] = base_zone * attr_mult
        return stats

    # --- 天赋一：即兴发挥 ---
    def check_passive_heal(self, actor):
        """当队友(或自己)处于增幅状态造成技能伤害时调用"""
        # 判定增幅：检查是否有电/火增伤Buff (ult_buff)
        has_amp = actor.buffs.has_tag("electric_buff") or actor.buffs.has_tag("heat_buff")
        
        if has_amp and self.passive_heal_cd.get(actor.name, 0) == 0:
            heal = MECHANICS['passive_heal_base'] + self.attrs.strength * MECHANICS['passive_heal_scale']
            self.engine.log(f"   💊 [天赋] 安塔尔为 {actor.name} 回复 {int(heal)} 生命")
            self.passive_heal_cd[actor.name] = MECHANICS['passive_cd']

    # --- 伤害处理 ---
    def _deal_dmg(self, mv, move_type):
        panel = self.get_current_panel()

        # 1. 反应判定
        ex_mv, r_type, log = self.target.reaction_mgr.apply_hit(
            Element.ELECTRIC, attacker_atk=panel['final_atk']
        )
        if log: self.engine.log(f"   [{log}]")
            
        # 2. 伤害结算
        DamageEngine.calculate(
            panel, self.target.get_defense_stats(), 
            mv + ex_mv, Element.ELECTRIC, move_type=move_type
        )
        
        # 3. 天赋触发 (仅限自己造成的技能伤害)
        if move_type == MoveType.SKILL:
            self.check_passive_heal(self)

        dmg = DamageEngine.calculate(
            panel, self.target.get_defense_stats(), 
            mv + ex_mv, Element.ELECTRIC, move_type=move_type
        )
        self.target.take_damage(dmg)
        self.engine.log(f"   💥 Hit造成伤害: {dmg}")

    # --- 解析器 ---
    def parse_command(self, cmd_str: str):
        parts = cmd_str.split()
        cmd = parts[0].lower()
        if cmd == "wait": return Action(f"等待", int(float(parts[1])*10), [])
        if cmd.startswith("a") and cmd[1:].isdigit(): return self.create_normal_attack(int(cmd[1:]) - 1)
        
        if cmd in ["skill", "e"]:
            if self.cooldowns.get("skill", 0) > 0: return None
            self.cooldowns["skill"] = 150 
            return self.create_skill()
            
        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0: return None
            self.cooldowns["ult"] = 300
            return self.create_ult()
            
        if cmd == "qte":
            # 连携条件: 聚焦 AND (物理异常 OR 法术附着)
            is_focused = self.target.buffs.has_tag("focus")
            has_attach = self.target.reaction_mgr.has_magic_attachment()
            has_break = self.target.reaction_mgr.phys_break_stacks > 0
            
            if is_focused and (has_attach or has_break):
                return self.create_qte()
            return None

        return Action("未知", 0, [])

    # --- 动作工厂 ---

    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, 3)
        mv = mvs[idx]
        f_data = frames[idx]
        def perform():
            self._deal_dmg(mv, MoveType.NORMAL)
        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：指定研究对象"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]
        
        def hit():
            self._deal_dmg(mv, MoveType.SKILL)
            
            # 施加 Debuff
            dur = MECHANICS['skill_fragility_dur']
            val = MECHANICS['skill_fragility_val']
            self.engine.log("   [战技] 施加聚焦 & 电/火脆弱 (独立乘区)")
            
            # 聚焦
            self.target.buffs.add_buff(FocusDebuff(duration=dur), self.engine)
            # 脆弱 (使用 FragilityBuff)
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
        """连携技：磁暴试验场 (刷新状态)"""
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]
        
        def perform():
            self.engine.log("   [连携技] 能量爆炸！")
            
            # 1. 记录当前状态 (为了再次施加)
            # 需要访问 target.reaction_mgr
            current_elem = self.target.reaction_mgr.attachment_element
            current_break = self.target.reaction_mgr.phys_break_stacks
            
            # 2. 造成伤害 (可能触发反应清空状态，如电+火=导电)
            self._deal_dmg(mv, MoveType.QTE)
            
            # 3. 强制恢复/再次施加状态
            if current_elem:
                # 重新施加该元素，不造成伤害
                self.target.reaction_mgr.apply_hit(current_elem)
                self.engine.log(f"   [连携技] 刷新/再次施加: {current_elem.value}")
            elif current_break > 0:
                self.target.reaction_mgr.apply_hit(Element.PHYSICAL, PhysAnomalyType.BREAK)
                self.engine.log(f"   [连携技] 刷新物理破防")

        return Action("磁暴试验场", f_data['total'], [DamageEvent(f_data['hit'], perform)])