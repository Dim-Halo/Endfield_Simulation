from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType
from mechanics.buff_system import Buff, CorrosionBuff, VulnerabilityBuff
from .erdila_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS

class ErdilaSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("艾尔黛拉", engine)
        self.target = target
        
        # 面板数据
        self.attrs = Attributes(strength=112, agility=93, intelligence=145, willpower=118)
        self.base_stats = CombatStats(base_hp=5495, base_atk=323, atk_pct=0.0)
        
        # 艾尔黛拉: 主智识(Int), 副意志(Wil)
        
    def get_current_panel(self):
        # 1. 暴露基础数据
        stats = {
            # 攻击力构成部分
            "base_atk": self.base_stats.base_atk + self.base_stats.weapon_atk,
            "atk_pct": self.base_stats.atk_pct,
            "flat_atk": self.base_stats.flat_atk,
            
            # 基础属性
            "dmg_bonus": self.base_stats.dmg_bonus,
            "crit_rate": self.base_stats.crit_rate,
            "crit_dmg": self.base_stats.crit_dmg,
            "res_pen": self.base_stats.res_pen,
            "amplification": self.base_stats.amplification,
            
            # 治疗加成
            "heal_bonus": self.base_stats.heal_bonus,
            
            # 特定增伤
            "normal_dmg_bonus": self.base_stats.normal_dmg_bonus,
            "skill_dmg_bonus": self.base_stats.skill_dmg_bonus,
            "ult_dmg_bonus": self.base_stats.ult_dmg_bonus,
            "qte_dmg_bonus": self.base_stats.qte_dmg_bonus,
        }
        
        stats = self.buffs.apply_stats(stats)

        base_zone = stats["base_atk"] * (1 + stats["atk_pct"]) + stats["flat_atk"]
        attr_mult = self.base_stats.get_attr_multiplier(self.attrs, "intelligence", "strength")
        stats["final_atk"] = base_zone * attr_mult

        return stats

    # --- 辅助：治疗计算 ---
    def _perform_heal(self):
        """天赋一：多利影子治疗"""
        panel = self.get_current_panel()
        wil = self.attrs.willpower
        
        # 公式: [基础 + 意志 * 倍率] * (1 + 治疗加成)
        base_heal = MECHANICS['heal_base'] + wil * MECHANICS['heal_scale']
        final_heal = base_heal * (1.0 + panel.get('heal_bonus', 0.0))
        
        self.engine.log(f"   💚 [治疗] 艾尔黛拉回复全队 {int(final_heal)} 点生命值")

    # --- 辅助：伤害处理 ---
    def _deal_dmg(self, mv, move_type, apply_nature_react=False):
        panel = self.get_current_panel()
        extra_mv = 0
        
        # 艾尔黛拉是自然(Nature)伤害
        if apply_nature_react:
            ex_mv, r_type, log = self.target.reaction_mgr.apply_hit(
                Element.NATURE, attacker_atk=panel['final_atk']
            )
            extra_mv = ex_mv
            if log: self.engine.log(f"   [{log}]")
            
        dmg = DamageEngine.calculate(
            panel, self.target.get_defense_stats(), 
            mv + extra_mv, Element.NATURE, move_type=move_type
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
            # CD 假设 15s
            self.cooldowns["skill"] = 150 
            return self.create_skill()
            
        if cmd in ["ult", "q"]:
            if self.cooldowns.get("ult", 0) > 0: return None
            self.cooldowns["ult"] = 300
            return self.create_ult()
            
        if cmd == "qte":
            # 连携条件: 敌人不处于破防 且 不处于法术附着
            has_attach = self.target.reaction_mgr.has_magic_attachment()
            # 注意：这里需要访问 target 的 break stacks，假设 reaction_mgr 暴露了这个属性
            has_break = self.target.reaction_mgr.phys_break_stacks > 0
            
            if not has_attach and not has_break:
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
            self._deal_dmg(mv, MoveType.NORMAL, apply_nature_react=True)
            
        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：奔腾的多利"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]
        
        def hit():
            # 1. 检测腐蚀
            has_corrosion = self.target.buffs.consume_tag("corrosion")
            
            # 2. 造成伤害 (自然反应)
            self._deal_dmg(mv, MoveType.SKILL, apply_nature_react=True)
            
            # 3. 产生影子 (治疗)
            self._perform_heal()
            
            # 4. 如果消耗了腐蚀 -> 施加双脆弱
            if has_corrosion:
                self.engine.log("   [战技] 消耗腐蚀！施加物理/法术脆弱，并触发二次冲撞！")
                dur = MECHANICS['vuln_duration']
                val = MECHANICS['vuln_value']
                
                # 施加物理脆弱
                self.target.buffs.add_buff(
                    VulnerabilityBuff("物理脆弱", dur, val, vuln_type="physical"), self.engine
                )
                # 施加法术脆弱
                self.target.buffs.add_buff(
                    VulnerabilityBuff("法术脆弱", dur, val, vuln_type="magic"), self.engine
                )
                
                # 5. 天赋二：山顶冲浪 (再次发动战技)
                # 模拟器简化：直接对当前目标再造成一次伤害
                self.engine.log("   >>> [天赋] 山顶冲浪：额外冲撞！")
                self._deal_dmg(mv, MoveType.SKILL, apply_nature_react=False) # 假设额外攻击不产球/不强附着

        return Action("奔腾的多利", f_data['total'], [DamageEvent(f_data['hit'], hit)])

    def create_qte(self):
        """连携技：火山蘑菇云"""
        f_data = FRAME_DATA["qte"]
        
        def hit_throw():
            self.engine.log("   [连携技] 抛出火山云...")
            self._deal_dmg(SKILL_MULTIPLIERS['qte_hit'], MoveType.QTE)
            
        def hit_explode():
            self.engine.log("   [连携技] 蘑菇云爆炸！强制腐蚀！")
            self._deal_dmg(SKILL_MULTIPLIERS['qte_explode'], MoveType.QTE)
            # 强制施加腐蚀 (Corrosion)
            self.target.buffs.add_buff(CorrosionBuff(duration=MECHANICS['corrosion_duration']), self.engine)

        events = [
            DamageEvent(f_data['hit'], hit_throw),
            DamageEvent(f_data['explode'], hit_explode)
        ]
        return Action("火山蘑菇云", f_data['total'], events)

    def create_ult(self):
        """终结技：毛茸茸派对 (多段伤害 + 随机掉落影子)"""
        f_data = FRAME_DATA["ult"]
        # 假设命中 5 次
        hits = 5
        events = []
        
        for i in range(hits):
            def hit(idx=i):
                self._deal_dmg(SKILL_MULTIPLIERS['ult_hit'], MoveType.ULTIMATE, apply_nature_react=True)
                # 模拟概率掉落影子治疗
                import random
                if random.random() < 0.5: # 假设50%概率
                    self._perform_heal()
            
            events.append(DamageEvent(i * f_data['interval'] + 2, hit))
            
        return Action("毛茸茸派对", f_data['total'], events)