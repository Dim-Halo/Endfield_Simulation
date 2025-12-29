"""武器特殊效果处理器"""
from simulation.event_system import EventType
from core.enums import ReactionType
from mechanics.buff_system import Buff


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

    def apply_effect_buff(self, effect):
        """应用效果 buff"""
        # 创建 buff
        buff = Buff(
            name=f"{self.weapon.name}效果",
            duration_ticks=int(effect.duration * 10),
            stat_modifiers=effect.buff_stats,
            stacks=1,
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
