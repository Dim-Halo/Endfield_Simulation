"""装备特殊效果处理器"""
from simulation.event_system import EventType
from core.enums import ReactionType
from mechanics.buff_system import StatModifierBuff, BuffCategory


class EquipmentEffectHandler:
    """处理装备特殊效果"""

    def __init__(self, character, equipment, engine):
        self.character = character
        self.equipment = equipment
        self.engine = engine
        self.active_effects = {}  # 跟踪激活的效果

        # 注册事件监听
        self.register_effects()

    def register_effects(self):
        """注册装备效果的事件监听"""
        for effect in self.equipment.effects:
            if effect.effect_type == "on_reaction":
                # 监听反应触发事件
                self.engine.event_bus.subscribe(
                    EventType.REACTION_TRIGGERED,
                    lambda event, eff=effect: self.on_reaction_triggered(event, eff),
                    priority=50
                )
            elif effect.effect_type == "on_skill_cast":
                # 监听技能释放事件
                self.engine.event_bus.subscribe(
                    EventType.ACTION_START,
                    lambda event, eff=effect: self.on_skill_cast(event, eff),
                    priority=50
                )
            elif effect.effect_type == "on_damage_dealt":
                # 监听伤害造成事件
                self.engine.event_bus.subscribe(
                    EventType.DAMAGE_DEALT,
                    lambda event, eff=effect: self.on_damage_dealt(event, eff),
                    priority=50
                )
            elif effect.effect_type == "on_crit":
                # 监听暴击事件
                self.engine.event_bus.subscribe(
                    EventType.CRIT_DEALT,
                    lambda event, eff=effect: self.on_crit(event, eff),
                    priority=50
                )
            elif effect.effect_type == "on_buff_applied":
                # 监听buff施加事件
                self.engine.event_bus.subscribe(
                    EventType.BUFF_APPLIED,
                    lambda event, eff=effect: self.on_buff_applied(event, eff),
                    priority=50
                )
            elif effect.effect_type == "on_element_attach":
                # 监听元素附着事件
                self.engine.event_bus.subscribe(
                    EventType.ELEMENT_ATTACHED,
                    lambda event, eff=effect: self.on_element_attach(event, eff),
                    priority=50
                )

    def on_reaction_triggered(self, event, effect):
        """当反应触发时"""
        # 检查是否是该角色触发的反应
        if event.data.get('attacker') != self.character.name:
            return

        # 检查反应类型是否匹配
        reaction_type = event.data.get('reaction_type')
        if not reaction_type:
            return

        trigger_reactions = effect.trigger_condition.get('reactions', [])
        if reaction_type.name not in trigger_reactions:
            return

        # 应用 buff
        self.apply_effect_buff(effect)

    def on_skill_cast(self, event, effect):
        """当技能释放时"""
        # 检查是否是该角色释放的技能
        if event.source != self.character:
            return

        # 检查技能类型是否匹配
        move_type = event.data.get('move_type')
        if not move_type:
            return

        trigger_move_types = effect.trigger_condition.get('move_types', [])
        if move_type.name not in trigger_move_types:
            return

        # 应用 buff
        self.apply_effect_buff(effect)

    def on_damage_dealt(self, event, effect):
        """当造成伤害时"""
        # 检查是否是该角色造成的伤害
        if event.source != self.character:
            return

        # 检查是否满足触发条件（如伤害阈值）
        trigger_condition = effect.trigger_condition
        if 'min_damage' in trigger_condition:
            damage = event.data.get('final_damage', 0)
            if damage < trigger_condition['min_damage']:
                return

        # 应用 buff
        self.apply_effect_buff(effect)

    def on_crit(self, event, effect):
        """当造成暴击时"""
        # 检查是否是该角色造成的暴击
        if event.source != self.character:
            return

        # 应用 buff
        self.apply_effect_buff(effect)

    def on_buff_applied(self, event, effect):
        """当施加buff时"""
        # 检查是否是该角色施加的buff
        if event.source != self.character:
            return

        # 获取buff实例和名称
        buff_instance = event.data.get('buff_instance')
        buff_name = event.data.get('buff_name', '')

        # 检查buff类型是否匹配触发条件
        trigger_buff_types = effect.trigger_condition.get('buff_types', [])
        if not trigger_buff_types:
            return

        # 判断buff是否匹配（通过stat_modifiers或名称）
        is_match = False

        if buff_instance and hasattr(buff_instance, 'stat_modifiers'):
            # 通过stat_modifiers判断buff类型
            stat_mods = buff_instance.stat_modifiers
            for buff_type in trigger_buff_types:
                if buff_type == "amplification" and "amplification" in stat_mods:
                    is_match = True
                    break
                elif buff_type == "sanctuary" and "sanctuary" in stat_mods:
                    is_match = True
                    break
                elif buff_type == "vulnerability" and ("vulnerability" in stat_mods or "magic_vuln" in stat_mods or "phys_vuln" in stat_mods):
                    is_match = True
                    break
                elif buff_type == "fragility" and "fragility" in stat_mods:
                    is_match = True
                    break

        # 如果通过stat_modifiers没有匹配，尝试通过名称匹配
        if not is_match:
            buff_name_lower = buff_name.lower()
            for buff_type in trigger_buff_types:
                if buff_type in buff_name_lower or self._translate_buff_type(buff_type) in buff_name_lower:
                    is_match = True
                    break

        if not is_match:
            return

        # 给其他队友添加buff
        self.apply_team_buff(effect)

    def on_element_attach(self, event, effect):
        """当元素附着时"""
        # 检查是否是该角色造成的附着
        if event.data.get('attacker') != self.character.name:
            return

        # 检查附着层数是否满足条件
        stacks = event.data.get('stacks', 0)
        min_stacks = effect.trigger_condition.get('min_stacks', 2)
        if stacks < min_stacks:
            return

        # 检查元素类型是否匹配（如果有限制）
        element_types = effect.trigger_condition.get('element_types', [])
        if element_types:
            element = event.data.get('element')
            if element and element.name not in element_types:
                return

        # 应用 buff
        self.apply_effect_buff(effect)

    def _translate_buff_type(self, buff_type):
        """翻译buff类型名称（英文到中文）"""
        translations = {
            "amplification": "增幅",
            "sanctuary": "庇护",
            "vulnerability": "易伤",
            "fragility": "脆弱"
        }
        return translations.get(buff_type, buff_type)

    def apply_effect_buff(self, effect):
        """应用效果 buff"""
        # 创建 buff - 使用 StatModifierBuff
        buff = StatModifierBuff(
            name=f"{self.equipment.name}效果",
            duration=effect.duration,
            stat_modifiers=effect.buff_stats,
            category=BuffCategory.BUFF,
            max_stacks=1
        )

        # 添加到角色
        self.character.buffs.add_buff(buff)

        self.engine.log(
            f"[{self.character.name}] {self.equipment.name}特殊效果触发: {effect.description}",
            level="INFO"
        )

    def apply_team_buff(self, effect):
        """给其他队友添加buff"""
        # 获取所有队友（排除自己）
        teammates = [entity for entity in self.engine.entities
                    if entity != self.character and hasattr(entity, 'buffs')]

        if not teammates:
            return

        # 给每个队友添加buff
        for teammate in teammates:
            buff = StatModifierBuff(
                name=f"{self.equipment.name}团队效果",
                duration=effect.duration,
                stat_modifiers=effect.buff_stats,
                category=BuffCategory.BUFF,
                max_stacks=1  # 确保无法叠加
            )
            teammate.buffs.add_buff(buff)

        self.engine.log(
            f"[{self.character.name}] {self.equipment.name}团队效果触发: {effect.description}",
            level="INFO"
        )

    def cleanup(self):
        """清理事件监听"""
        # 事件总线会自动处理，这里预留接口
        pass
