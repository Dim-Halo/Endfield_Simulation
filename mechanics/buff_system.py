from typing import List, Dict, Optional
from core.enums import BuffCategory, BuffEffect, ReactionType
from core.formulas import calculate_tech_enhancement
from core.stats import StatKey

class Buff:
    """Buff基类"""
    def __init__(self, name: str, duration_sec: float, max_stacks: int = 1,
                 category: BuffCategory = BuffCategory.NEUTRAL,
                 effect_type: BuffEffect = BuffEffect.STAT_MODIFIER):
        self.name = name
        self.duration_ticks = int(duration_sec * 10)
        self.max_stacks = max_stacks
        self.stacks = 1
        self.category = category  # 使用枚举
        self.effect_type = effect_type  # 使用枚举
        self.timer = 0
        self.owner = None  # 持有者引用

        # 额外标签（用于特殊识别，如反应类型）
        self.tags = set()

    def on_apply(self, owner, engine=None):
        """Buff施加时触发"""
        self.owner = owner
        
    def on_reaction_enhancement(self, reaction_result):
        """
        元素反应增强钩子
        Args:
            reaction_result: mechanics.reaction_manager.ReactionResult 实例
        """
        pass

    def modify_stats(self, stats: Dict):
        """修改目标属性"""
        pass

    def on_stack(self, new_buff):
        """Buff叠加时触发"""
        self.stacks = min(self.max_stacks, self.stacks + new_buff.stacks)
        self.duration_ticks = new_buff.duration_ticks

    def on_tick(self, owner, engine):
        """每tick触发，返回True表示过期"""
        self.timer += 1
        self.duration_ticks -= 1
        return self.duration_ticks <= 0

class UsageBuff(Buff):
    """次数限制Buff基类"""
    def __init__(self, name: str, duration: float, usages: int = 1, 
                 category: BuffCategory = BuffCategory.BUFF, 
                 effect_type: BuffEffect = BuffEffect.STAT_MODIFIER):
        super().__init__(name, duration, category=category, effect_type=effect_type)
        self.usages = usages
        
    def consume(self):
        """消耗一次使用次数，归零时尝试移除"""
        self.usages -= 1
        if self.usages <= 0:
            if self.owner and hasattr(self.owner, 'buffs'):
                self.owner.buffs.remove_buff(self.name)

# ============================================================
# 通用Buff类 - 大多数简单Buff可以用这个类
# ============================================================

class StatModifierBuff(Buff):
    """
    通用属性修改Buff

    可以替代: AtkPctBuff, VulnerabilityBuff, FragilityBuff, ElementalDmgBuff等

    使用示例:
        # 攻击力提升
        StatModifierBuff("攻击强化", 10.0, {"atk_pct": 0.2}, BuffCategory.BUFF)

        # 易伤效果
        StatModifierBuff("易伤", 8.0, {"vulnerability": 0.15}, BuffCategory.DEBUFF)

        # 元素增伤
        StatModifierBuff("热能增伤", 12.0, {"heat_dmg_bonus": 0.25}, BuffCategory.BUFF)
    """
    def __init__(self, name: str, duration: float,
                 stat_modifiers: Dict[str, float],
                 category: BuffCategory = BuffCategory.BUFF,
                 max_stacks: int = 1):
        super().__init__(name, duration, max_stacks, category, BuffEffect.STAT_MODIFIER)
        self.stat_modifiers = stat_modifiers

    def modify_stats(self, stats: Dict):
        for key, value in self.stat_modifiers.items():
            if key in stats:
                stats[key] += value * self.stacks  # 支持叠加
            else:
                stats[key] = value * self.stacks

# ============================================================
# 保持向后兼容的简化类（使用StatModifierBuff实现）
# ============================================================

class AtkPctBuff(StatModifierBuff):
    """攻击力百分比增益Buff（向后兼容）"""
    def __init__(self, name: str, value: float, duration: float):
        super().__init__(name, duration, {StatKey.ATK_PCT: value}, BuffCategory.BUFF)

class VulnerabilityBuff(StatModifierBuff):
    """易伤Buff（向后兼容）"""
    def __init__(self, name: str, duration: float, value: float, vuln_type: str = "all"):
        key_map = {
            "all": StatKey.VULNERABILITY,
            "magic": StatKey.MAGIC_VULN,
            "physical": StatKey.PHYS_VULN
        }
        key = key_map.get(vuln_type, StatKey.VULNERABILITY)
        super().__init__(name, duration, {key: value}, BuffCategory.DEBUFF)

class ElementalDmgBuff(StatModifierBuff):
    """元素伤害增益Buff（向后兼容）"""
    def __init__(self, name: str, duration: float, element_type: str, value: float):
        elem_key = f"{element_type}_dmg_bonus"
        super().__init__(name, duration, {elem_key: value}, BuffCategory.BUFF)

class FragilityBuff(StatModifierBuff):
    """脆弱Buff（向后兼容）"""
    def __init__(self, name: str, duration: float, value: float, element_type: str = "all"):
        key = StatKey.FRAGILITY if element_type == "all" else f"{element_type}_fragility"
        super().__init__(name, duration, {key: value}, BuffCategory.DEBUFF)

# ============================================================
# 持续伤害类Buff
# ============================================================

class DoTBuff(Buff):
    """持续伤害Buff基类"""
    def __init__(self, name: str, duration: float, damage_per_tick: float,
                 interval_sec: float = 1.0, source_name: str = "未知",
                 reaction_type: Optional[ReactionType] = None):
        super().__init__(name, duration, max_stacks=1,
                        category=BuffCategory.DEBUFF, effect_type=BuffEffect.DOT)
        self.damage = damage_per_tick
        self.interval_ticks = int(interval_sec * 10)
        self.tick_counter = 0
        self.source_name = source_name

        # 设置反应类型标签
        if reaction_type:
            self.tags.add(reaction_type)

    def on_tick(self, owner, engine):
        is_expired = super().on_tick(owner, engine)
        self.tick_counter += 1

        if self.tick_counter >= self.interval_ticks:
            self.tick_counter = 0
            engine.log(f"   [DOT] [{self.name}] 造成 {int(self.damage)} 点持续伤害")

            if hasattr(owner, 'take_damage'):
                owner.take_damage(self.damage)

                # 记录到统计系统
                if hasattr(engine, 'statistics'):
                    from core.enums import Element, MoveType
                    engine.statistics.record_damage(
                        tick=engine.tick,
                        source=self.source_name,
                        target=owner.name,
                        skill_name=self.name,
                        damage=self.damage,
                        element=Element.HEAT,
                        move_type=MoveType.OTHER,
                        is_crit=False,
                        is_reaction=True
                    )
        return is_expired

# ============================================================
# 元素反应Buff（使用增强计算）
# ============================================================

class BurningBuff(DoTBuff):
    """燃烧Buff"""
    def __init__(self, damage_value: float, duration: float = 10.0, source_name: str = "未知"):
        super().__init__("燃烧", duration, damage_value,
                        interval_sec=1.0, source_name=source_name,
                        reaction_type=ReactionType.BURNING)

class ConductiveBuff(StatModifierBuff):
    """导电Buff - 增加法术易伤"""
    def __init__(self, duration: float = 12.0, base_vuln: float = 0.12, tech_power: float = 0.0):
        final_vuln = calculate_tech_enhancement(tech_power, base_vuln)
        super().__init__("导电", duration, {StatKey.MAGIC_VULN: final_vuln}, BuffCategory.DEBUFF)
        self.tags.add(ReactionType.CONDUCTIVE)

class CorrosionBuff(Buff):
    """腐蚀Buff - 降低所有元素抗性 (随时间叠加)"""
    def __init__(self, duration: float = 15.0, 
                 initial_shred: float = 0.036, 
                 tick_shred: float = 0.0084,
                 max_shred: float = 0.12,
                 tech_power: float = 0.0):
        super().__init__("腐蚀", duration, category=BuffCategory.DEBUFF)
        
        # 应用源石技艺增强
        self.initial_shred = calculate_tech_enhancement(tech_power, initial_shred)
        self.tick_shred = calculate_tech_enhancement(tech_power, tick_shred)
        self.max_shred = calculate_tech_enhancement(tech_power, max_shred)
        
        self.current_shred = self.initial_shred
        self.tags.add(ReactionType.CORROSION)
        
        # 计时器用于每秒叠加
        self.tick_timer = 0
        self.tick_interval = 10  # 1秒 = 10 ticks

    def on_tick(self, owner, engine):
        is_expired = super().on_tick(owner, engine)
        
        # 每秒叠加抗性削减
        self.tick_timer += 1
        if self.tick_timer >= self.tick_interval:
            self.tick_timer = 0
            if self.current_shred < self.max_shred:
                self.current_shred = min(self.max_shred, self.current_shred + self.tick_shred)
                # engine.log(f"   [腐蚀] 抗性削减加深 -> {self.current_shred:.2%}")
                
        return is_expired

    def modify_stats(self, stats: Dict):
        for k in list(stats.keys()):
            if k.endswith("_res"):
                stats[k] -= self.current_shred

class ShatterArmorBuff(StatModifierBuff):
    """碎甲Buff - 增加物理易伤"""
    def __init__(self, duration: float = 12.0, base_vuln: float = 0.11, tech_power: float = 0.0):
        final_vuln = calculate_tech_enhancement(tech_power, base_vuln)
        super().__init__("碎甲", duration, {StatKey.PHYS_VULN: final_vuln}, BuffCategory.DEBUFF)

# ============================================================
# 控制效果Buff
# ============================================================

class FrozenBuff(Buff):
    """冻结Buff"""
    def __init__(self, duration: float = 6.0):
        super().__init__("冻结", duration, category=BuffCategory.DEBUFF, effect_type=BuffEffect.CC)
        self.tags.add(ReactionType.FROZEN)

class FocusDebuff(Buff):
    """聚焦Debuff"""
    def __init__(self, duration: float = 60.0):
        super().__init__("聚焦", duration, category=BuffCategory.DEBUFF)
        self.tags.add("focus")  # 添加特殊标签以便识别


class BuffManager:
    """Buff管理器"""
    def __init__(self, owner):
        self.owner = owner
        self.buffs: List[Buff] = []

    def get_buff(self, name: str) -> Optional[Buff]:
        """获取指定名称的Buff"""
        for b in self.buffs:
            if b.name == name:
                return b
        return None

    def add_buff(self, new_buff: Buff, engine=None):
        """添加或叠加Buff"""
        for b in self.buffs:
            if b.name == new_buff.name:
                b.on_stack(new_buff)
                if engine:
                    engine.log(f"   (Buff) [{self.owner.name}] 刷新: {b.name} (层数:{b.stacks})")
                    # 发布Buff叠加事件
                    if hasattr(engine, 'event_bus'):
                        from simulation.event_system import EventType, EventBuilder
                        event = EventBuilder.buff_event(
                            EventType.BUFF_STACKED,
                            owner=self.owner,
                            buff_name=b.name,
                            source=None,
                            stacks=b.stacks,
                            tick=engine.tick
                        )
                        engine.event_bus.emit(event)
                return

        self.buffs.append(new_buff)
        # 初始化Buff
        new_buff.on_apply(self.owner, engine)
        
        if engine:
            engine.log(f"   (Buff) [{self.owner.name}] 获得: {new_buff.name}")
            # 发布Buff施加事件
            if hasattr(engine, 'event_bus'):
                from simulation.event_system import EventType, EventBuilder
                event = EventBuilder.buff_event(
                    EventType.BUFF_APPLIED,
                    owner=self.owner,
                    buff_name=new_buff.name,
                    source=None,
                    stacks=new_buff.stacks,
                    tick=engine.tick,
                    tags=new_buff.tags,
                    buff_instance=new_buff
                )
                engine.event_bus.emit(event)

    def tick_all(self, engine):
        """更新所有Buff"""
        active_buffs = []
        for b in self.buffs:
            if not b.on_tick(self.owner, engine):
                active_buffs.append(b)
            else:
                engine.log(f"   (Buff) [{self.owner.name}] 效果结束: {b.name}")
                # 发布Buff过期事件
                if hasattr(engine, 'event_bus'):
                    from simulation.event_system import EventType
                    engine.event_bus.emit_simple(
                        EventType.BUFF_EXPIRED,
                        owner=self.owner.name,
                        buff_name=b.name,
                        tick=engine.tick
                    )
        self.buffs = active_buffs

    def apply_stats(self, base_stats: Dict):
        """应用所有Buff的属性修改"""
        import copy
        final_stats = copy.deepcopy(base_stats)
        for b in self.buffs:
            b.modify_stats(final_stats)
        return final_stats
        
    def apply_reaction_enhancements(self, reaction_result):
        """应用所有Buff的反应增强效果"""
        # 使用副本迭代，防止在迭代中Buff被移除导致的问题
        for b in list(self.buffs):
            b.on_reaction_enhancement(reaction_result)

    def consume_tag(self, tag, engine=None):
        """消耗第一个匹配tag的Buff"""
        for b in self.buffs:
            if tag in b.tags:
                self.buffs.remove(b)
                if engine:
                    engine.log(f"   (Buff) [{self.owner.name}] 消耗: {b.name}")
                return True
        return False

    def remove_buff(self, name: str):
        """移除指定名称的Buff"""
        for b in self.buffs:
            if b.name == name:
                self.buffs.remove(b)
                return True
        return False

    def has_tag(self, tag):
        """检查是否存在指定tag的Buff"""
        return any(tag in b.tags for b in self.buffs)
