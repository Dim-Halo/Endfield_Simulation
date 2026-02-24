from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, List, Union
from core.enums import Element, PhysAnomalyType, ReactionType
from mechanics.buff_system import BurningBuff, ConductiveBuff, CorrosionBuff, FrozenBuff, ShatterArmorBuff
from core.config_manager import get_config

if TYPE_CHECKING:
    from simulation.engine import SimEngine
    from entities.characters.base_actor import BaseActor

@dataclass
class ReactionResult:
    extra_mv: float = 0.0
    reaction_types: List[ReactionType] = None  # Changed to list
    log_msg: str = ""
    level: int = 0 
    phys_anomaly_type: Optional[PhysAnomalyType] = None # 具体物理异常类型

    def __post_init__(self):
        if self.reaction_types is None:
            self.reaction_types = []

class ReactionManager:
    def __init__(self, owner: 'BaseActor', engine: 'SimEngine'):
        self.owner = owner
        self.engine = engine
        self.config = get_config()
        self.attachment_element: Optional[Element] = None
        self.attachment_stacks: int = 0
        self.phys_break_stacks: int = 0

    def has_magic_attachment(self) -> bool:
        return self.attachment_element is not None

    def reapply_current_status(self, attacker_atk: float, attacker_tech: float, attacker_lvl: int) -> str:
        res = ReactionResult(log_msg="无状态可刷新")
        if self.attachment_element:
            sub_res = self.apply_hit(Element.MAGIC, attachments=[self.attachment_element], attacker_atk=attacker_atk, attacker_tech=attacker_tech, attacker_lvl=attacker_lvl)
            res.log_msg = f"刷新状态 -> {sub_res.log_msg}"
        elif self.phys_break_stacks > 0:
            sub_res = self.apply_hit(Element.PHYSICAL, attachments=[PhysAnomalyType.BREAK], attacker_atk=attacker_atk, attacker_tech=attacker_tech, attacker_lvl=attacker_lvl)
            res.log_msg = f"刷新状态 -> {sub_res.log_msg}"
        return res.log_msg

    def apply_hit(self, damage_element: Element, attachments: List[Union[Element, PhysAnomalyType]] = None, attacker_atk=1000, attacker_tech=0, attacker_lvl=80, attacker_name="未知") -> ReactionResult:
        result = ReactionResult()
        
        # 如果 attachments 为 None 或空列表，则不进行任何附着
        if not attachments:
            return result
            
        for att in attachments:
            sub_res = ReactionResult()
            if isinstance(att, Element):
                sub_res = self._handle_elemental_hit(att, attacker_atk, attacker_tech, attacker_lvl, attacker_name)
            elif isinstance(att, PhysAnomalyType):
                # Note: _handle_physical_hit needs incoming_element logic for Frozen shatter check
                # We assume damage_element is the carrier
                sub_res = self._handle_physical_hit(att, attacker_tech, attacker_lvl, attacker_name, damage_element)
            
            # Merge results
            result.extra_mv += sub_res.extra_mv
            if sub_res.reaction_types:
                result.reaction_types.extend(sub_res.reaction_types)
            if sub_res.log_msg:
                result.log_msg += (" | " if result.log_msg else "") + sub_res.log_msg
            # Level is tricky to merge, usually we care about the last one or specific one
            result.level = sub_res.level 
            
            if sub_res.phys_anomaly_type:
                result.phys_anomaly_type = sub_res.phys_anomaly_type

        return result

    def _handle_physical_hit(self, phys_type, attacker_tech, attacker_lvl, attacker_name, incoming_element) -> ReactionResult:
        result = ReactionResult()
        
        # 碎冰 (优先处理)
        if self.owner.buffs.has_tag(ReactionType.FROZEN):
            self.owner.buffs.consume_tag(ReactionType.FROZEN)
            mv = self.config.get_reaction_mv("shatter", level=1, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=False)
            result.extra_mv = mv
            result.reaction_types.append(ReactionType.SHATTER)
            result.log_msg = f"🧊🔨 [碎冰] 击碎冻结！(MV:{int(mv)}%)"
            self._emit_event(result, attacker_name, incoming_element, 0, phys_type)
            return result
        
        # 如果没有指定物理异常类型，则不视为物理异常，直接返回
        if phys_type == PhysAnomalyType.NONE:
            return result

        # 标记为物理异常
        result.reaction_types.append(ReactionType.PHYS_ANOMALY)
        result.phys_anomaly_type = phys_type
        
        # 记录类型 (如果是有效的物理异常)
        self.last_phys_type = phys_type

        # 状态机逻辑
        # 情况A: 敌人未处于破防状态 (stacks == 0)
        # 描述: "当敌人首次受到物理异常时...进入破防状态"
        if self.phys_break_stacks == 0:
            self.phys_break_stacks = 1
            result.log_msg = "首次受到物理异常 -> 进入破防状态(1层)"
            # 此时不触发具体的 猛击/碎甲/击飞 效果，仅进入状态
            self._emit_event(result, attacker_name, incoming_element, 1, phys_type)
            return result

        # 情况B: 敌人已处于破防状态 (stacks > 0)
        # 1. 猛击 (IMPACT) -> 消耗所有层数，造成伤害
        if phys_type == PhysAnomalyType.IMPACT: 
            lv = self.phys_break_stacks
            result.extra_mv = self.config.get_reaction_mv("impact", level=lv, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=False)
            self.phys_break_stacks = 0
            result.level = lv # 记录消耗的层数
            result.log_msg = f"猛击结算(Lv{lv})! 额外倍率 {int(result.extra_mv)}%"
        
        # 2. 碎甲 (SHATTER) -> 消耗所有层数，施加易伤
        elif phys_type == PhysAnomalyType.SHATTER:
            lv = self.phys_break_stacks
            result.extra_mv = self.config.get_reaction_mv("break", level=lv, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=False)
            
            base_vuln = self.config.reaction_coefficients["shatter_armor_base"]
            per_level = self.config.reaction_coefficients["shatter_armor_per_level"]
            vuln_val = base_vuln + per_level * lv
            
            self.owner.add_buff(ShatterArmorBuff(base_vuln=vuln_val, tech_power=attacker_tech), self.engine)
            self.phys_break_stacks = 0
            result.level = lv # 记录消耗的层数
            result.log_msg = f"碎甲结算(Lv{lv})! 施加物理易伤"

        # 3. 击飞 (LAUNCH) / 倒地 (KNOCKDOWN) -> 叠加层数，触发CC
        elif phys_type in [PhysAnomalyType.LAUNCH, PhysAnomalyType.KNOCKDOWN]:
            # 叠加层数 (max 4)
            old_stacks = self.phys_break_stacks
            self.phys_break_stacks = min(4, self.phys_break_stacks + 1)
            
            cc_name = "击飞" if phys_type == PhysAnomalyType.LAUNCH else "倒地"
            result.log_msg = f"{cc_name}! 破防层数 {old_stacks}->{self.phys_break_stacks}"
            # 这里可以添加额外的CC逻辑，例如 apply_stagger 或状态标记
        
        self._emit_event(result, attacker_name, incoming_element, self.phys_break_stacks, phys_type)
        return result

    def _handle_elemental_hit(self, incoming_element, attacker_atk, attacker_tech, attacker_lvl, attacker_name) -> ReactionResult:
        result = ReactionResult()

        if self.attachment_element is None:
            self.attachment_element = incoming_element
            self.attachment_stacks = 1
            result.reaction_types.append(ReactionType.ATTACH)
            result.log_msg = f"施加 {incoming_element.value} 附着"
            # 发出元素附着事件
            self._emit_element_attached_event(attacker_name, incoming_element, self.attachment_stacks)
            return result

        if self.attachment_element == incoming_element:
            result.extra_mv = self.config.get_reaction_mv("burst", level=0, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=True)
            self.attachment_stacks = min(self.config.max_attachment_stacks, self.attachment_stacks + 1)
            result.reaction_types.append(ReactionType.BURST)
            result.log_msg = f"法术爆发({incoming_element.value} {self.attachment_stacks}层)"
            # 发出元素附着事件（层数增加）
            self._emit_element_attached_event(attacker_name, incoming_element, self.attachment_stacks)
            return result

        # 异色反应
        level = self.attachment_stacks
        result.extra_mv = self.config.get_reaction_mv("reaction", level=level, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=True)
        
        if incoming_element == Element.HEAT:
            result.reaction_types.append(ReactionType.BURNING)
            dot_mv = self.config.get_reaction_mv("burning_dot", level=level, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=True)
            dot_dmg = attacker_atk * (dot_mv / 100.0)
            self.owner.add_buff(BurningBuff(dot_dmg, source_name=attacker_name), self.engine)
            
        elif incoming_element == Element.ELECTRIC:
            result.reaction_types.append(ReactionType.CONDUCTIVE)
            base_vuln = self.config.reaction_coefficients["conductive_base_vuln"]
            per_level = self.config.reaction_coefficients["conductive_per_level"]
            vuln_val = base_vuln + per_level * level
            self.owner.add_buff(ConductiveBuff(base_vuln=vuln_val, tech_power=attacker_tech), self.engine)
            
        elif incoming_element == Element.FROST:
            result.reaction_types.append(ReactionType.FROZEN)
            # 注意：冻结反应的直接伤害倍率是特殊的，这里使用 frozen 键
            extra_mv = self.config.get_reaction_mv("frozen", level=0, tech_power=attacker_tech, attacker_lvl=attacker_lvl, is_magic=True)
            result.extra_mv = extra_mv 
            
            base_dur = self.config.reaction_coefficients["frozen_base_duration"]
            per_level = self.config.reaction_coefficients["frozen_per_level"]
            dur = base_dur + per_level * (level - 1)
            self.owner.add_buff(FrozenBuff(duration=dur), self.engine)
            
        elif incoming_element == Element.NATURE:
            result.reaction_types.append(ReactionType.CORROSION)
            
            # 腐蚀初始削抗
            base_shred_val = self.config.reaction_coefficients["corrosion_base_shred"]
            per_level = self.config.reaction_coefficients["corrosion_per_level"]
            initial_shred = base_shred_val + per_level * level
            
            # 腐蚀每秒叠加
            tick_base = self.config.reaction_coefficients["corrosion_tick_base"]
            tick_level = self.config.reaction_coefficients["corrosion_tick_level"]
            tick_shred = tick_base + tick_level * level
            
            # 腐蚀最大削抗
            max_base = self.config.reaction_coefficients["corrosion_max_base"]
            max_level = self.config.reaction_coefficients["corrosion_max_level"]
            max_shred = max_base + max_level * level
            
            self.owner.add_buff(CorrosionBuff(
                initial_shred=initial_shred,
                tick_shred=tick_shred,
                max_shred=max_shred,
                tech_power=attacker_tech
            ), self.engine)

        self.attachment_element = None
        self.attachment_stacks = 0
        
        # 修复：result.reaction_types 是列表，不能直接取 value
        types_str = [r.value for r in result.reaction_types]
        result.log_msg = f"触发反应(Lv{level}): 【{types_str}】 (MV:{int(result.extra_mv)}%)"

        # 发布反应触发事件
        self._emit_event(result, attacker_name, incoming_element, level)

        return result

    def _emit_event(self, result, attacker_name, incoming_element, level, phys_type=None):
        if hasattr(self.engine, 'event_bus'):
            from simulation.event_system import EventType
            # Emit for each reaction type
            for r_type in result.reaction_types:
                data = {
                    "target": self.owner.name,
                    "attacker": attacker_name,
                    "reaction_type": r_type,
                    "element": incoming_element,
                    "level": level,
                    "extra_mv": result.extra_mv,
                    "tick": self.engine.tick
                }
                if phys_type is not None:
                    data["phys_type"] = phys_type

                self.engine.event_bus.emit_simple(EventType.REACTION_TRIGGERED, **data)

    def _emit_element_attached_event(self, attacker_name, element, stacks):
        """发出元素附着事件"""
        if hasattr(self.engine, 'event_bus'):
            from simulation.event_system import EventType
            self.engine.event_bus.emit_simple(
                EventType.ELEMENT_ATTACHED,
                target=self.owner.name,
                attacker=attacker_name,
                element=element,
                stacks=stacks,
                tick=self.engine.tick
            )