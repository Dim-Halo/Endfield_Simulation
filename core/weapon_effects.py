"""武器特殊效果处理器"""
from simulation.event_system import EventType
from core.enums import ReactionType
from mechanics.buff_system import StatModifierBuff, BuffCategory


class WeaponEffectHandler:
    """处理武器特殊效果"""

    def __init__(self, character, weapon, engine):
        self.character = character
        self.weapon = weapon
        self.engine = engine
        self.active_effects = {}  # 跟踪激活的效果

        # 注册事件监听
        self.register_effects()

    def register_effects(self):
        """注册武器效果的事件监听"""
        for effect in self.weapon.effects:
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

    def apply_effect_buff(self, effect):
        """应用效果 buff"""
        # 创建 buff - 使用 StatModifierBuff
        buff = StatModifierBuff(
            name=f"{self.weapon.name}效果",
            duration=effect.duration,
            stat_modifiers=effect.buff_stats,
            category=BuffCategory.BUFF,
            max_stacks=1
        )

        # 添加到角色
        self.character.buffs.add_buff(buff)

        self.engine.log(
            f"[{self.character.name}] {self.weapon.name}特殊效果触发: {effect.description}",
            level="INFO"
        )

    def cleanup(self):
        """清理事件监听"""
        # 事件总线会自动处理，这里预留接口
        pass
