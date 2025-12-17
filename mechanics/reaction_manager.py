from dataclasses import dataclass
from core.enums import Element, PhysAnomalyType, ReactionType
from mechanics.buff_system import BurningBuff, ConductiveBuff, CorrosionBuff, FrozenBuff, ShatterArmorBuff

@dataclass
class ReactionResult:
    extra_mv: float = 0.0
    reaction_type: ReactionType = ReactionType.NONE
    log_msg: str = ""

class ReactionManager:
    def __init__(self, owner, engine):
        self.owner = owner
        self.engine = engine
        self.attachment_element = None
        self.attachment_stacks = 0
        self.phys_break_stacks = 0

    def has_magic_attachment(self):
        return self.attachment_element is not None

    def reapply_current_status(self, attacker_atk, attacker_tech, attacker_lvl):
        res = ReactionResult(log_msg="无状态可刷新")
        if self.attachment_element:
            sub_res = self.apply_hit(self.attachment_element, attacker_atk=attacker_atk, attacker_tech=attacker_tech, attacker_lvl=attacker_lvl)
            res.log_msg = f"刷新状态 -> {sub_res.log_msg}"
        elif self.phys_break_stacks > 0:
            sub_res = self.apply_hit(Element.PHYSICAL, PhysAnomalyType.BREAK, attacker_atk=attacker_atk, attacker_tech=attacker_tech, attacker_lvl=attacker_lvl)
            res.log_msg = f"刷新状态 -> {sub_res.log_msg}"
        return res.log_msg

    def _calc_reaction_mv(self, base_mv, anomaly_level, attacker_tech, attacker_lvl, is_magic=True):
        level_mult = base_mv * (1.0 + anomaly_level)
        tech_mult = 1.0 + (attacker_tech / 100.0)
        spell_level_mult = 1.0
        if is_magic:
            spell_level_mult = 1.0 + (5.0 / 980.0) * (max(1, attacker_lvl) - 1)
        return level_mult * tech_mult * spell_level_mult

    def apply_hit(self, incoming_element: Element, phys_type: PhysAnomalyType = PhysAnomalyType.NONE, attacker_atk=1000, attacker_tech=0, attacker_lvl=80, attacker_name="未知") -> ReactionResult:
        result = ReactionResult()

        # --- 物理逻辑 ---
        if incoming_element == Element.PHYSICAL:
            # 碎冰
            if self.owner.buffs.has_tag(ReactionType.FROZEN):
                 self.owner.buffs.consume_tag(ReactionType.FROZEN)
                 mv = self._calc_reaction_mv(120, 1, attacker_tech, attacker_lvl, is_magic=False)
                 result.extra_mv = mv
                 result.reaction_type = ReactionType.SHATTER
                 result.log_msg = f"🧊🔨 [碎冰] 击碎冻结！(MV:{int(mv)}%)"
                 return result
            
            result.reaction_type = ReactionType.PHYS_ANOMALY
            
            if phys_type == PhysAnomalyType.BREAK:
                self.phys_break_stacks = min(4, self.phys_break_stacks + 1)
                result.log_msg = f"物理破防({self.phys_break_stacks}层)"
                
            elif phys_type == PhysAnomalyType.IMPACT: 
                if self.phys_break_stacks > 0:
                    lv = self.phys_break_stacks
                    result.extra_mv = self._calc_reaction_mv(150, lv, attacker_tech, attacker_lvl, is_magic=False)
                    self.phys_break_stacks = 0
                    result.log_msg = f"猛击结算(Lv{lv})! 额外倍率 {int(result.extra_mv)}%"
            
            elif phys_type == PhysAnomalyType.SHATTER:
                if self.phys_break_stacks > 0:
                    lv = self.phys_break_stacks
                    result.extra_mv = self._calc_reaction_mv(50, lv, attacker_tech, attacker_lvl, is_magic=False)
                    vuln_val = 0.08 + 0.03 * lv
                    self.owner.add_buff(ShatterArmorBuff(base_vuln=vuln_val, tech_power=attacker_tech), self.engine)
                    self.phys_break_stacks = 0
                    result.log_msg = f"碎甲结算(Lv{lv})! 施加物理易伤"
            return result

        # --- 法术逻辑 ---
        if self.attachment_element is None:
            self.attachment_element = incoming_element
            self.attachment_stacks = 1
            result.reaction_type = ReactionType.ATTACH
            result.log_msg = f"施加 {incoming_element.value} 附着"
            return result

        if self.attachment_element == incoming_element:
            result.extra_mv = self._calc_reaction_mv(160, 0, attacker_tech, attacker_lvl, is_magic=True)
            self.attachment_stacks = min(4, self.attachment_stacks + 1)
            result.reaction_type = ReactionType.BURST
            result.log_msg = f"法术爆发({incoming_element.value} {self.attachment_stacks}层)"
            return result

        # 异色反应
        level = self.attachment_stacks
        base_reaction_mv = 80
        result.extra_mv = self._calc_reaction_mv(base_reaction_mv, level, attacker_tech, attacker_lvl, is_magic=True)
        
        if incoming_element == Element.HEAT:
            result.reaction_type = ReactionType.BURNING
            dot_mv = self._calc_reaction_mv(12, level, attacker_tech, attacker_lvl, is_magic=True)
            dot_dmg = attacker_atk * (dot_mv / 100.0)
            self.owner.add_buff(BurningBuff(dot_dmg, source_name=attacker_name), self.engine)
            
        elif incoming_element == Element.ELECTRIC:
            result.reaction_type = ReactionType.CONDUCTIVE
            base_vuln = 0.08 + 0.04 * level
            self.owner.add_buff(ConductiveBuff(base_vuln=base_vuln, tech_power=attacker_tech), self.engine)
            
        elif incoming_element == Element.FROST:
            result.reaction_type = ReactionType.FROZEN
            extra_mv = self._calc_reaction_mv(130, 0, attacker_tech, attacker_lvl, is_magic=True)
            result.extra_mv = extra_mv # 修正覆盖
            dur = 6.0 + (level - 1)
            self.owner.add_buff(FrozenBuff(duration=dur), self.engine)
            
        elif incoming_element == Element.NATURE:
            result.reaction_type = ReactionType.CORROSION
            base_shred = (2 + level) / 100.0
            self.owner.add_buff(CorrosionBuff(base_res_shred=base_shred, tech_power=attacker_tech), self.engine)

        self.attachment_element = None
        self.attachment_stacks = 0
        result.log_msg = f"触发反应(Lv{level}): 【{result.reaction_type.value}】 (MV:{int(result.extra_mv)}%)"

        # 发布反应触发事件
        if hasattr(self.engine, 'event_bus'):
            from simulation.event_system import EventType
            self.engine.event_bus.emit_simple(
                EventType.REACTION_TRIGGERED,
                target=self.owner.name,
                attacker=attacker_name,
                reaction_type=result.reaction_type,
                element=incoming_element,
                level=level,
                extra_mv=result.extra_mv,
                tick=self.engine.tick
            )

        return result