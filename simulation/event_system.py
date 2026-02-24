"""
事件驱动系统
提供灵活的事件订阅和发布机制，支持复杂游戏机制的实现
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
from enum import Enum


class EventType(Enum):
    """事件类型枚举"""
    # 战斗生命周期
    COMBAT_START = "combat_start"
    COMBAT_END = "combat_end"
    TICK_START = "tick_start"
    TICK_END = "tick_end"

    # 伤害相关
    PRE_DAMAGE = "pre_damage"          # 伤害计算前
    POST_DAMAGE = "post_damage"        # 伤害计算后
    DAMAGE_DEALT = "damage_dealt"      # 伤害造成后
    DAMAGE_TAKEN = "damage_taken"      # 伤害承受后

    # 暴击相关
    CRIT_DEALT = "crit_dealt"          # 造成暴击
    CRIT_TAKEN = "crit_taken"          # 承受暴击

    # 行动相关
    ACTION_START = "action_start"      # 行动开始
    ACTION_END = "action_end"          # 行动结束
    SKILL_CAST = "skill_cast"          # 技能释放
    NORMAL_ATTACK = "normal_attack"    # 普攻

    # Buff相关
    BUFF_APPLIED = "buff_applied"      # Buff施加
    BUFF_REMOVED = "buff_removed"      # Buff移除
    BUFF_STACKED = "buff_stacked"      # Buff叠加
    BUFF_EXPIRED = "buff_expired"      # Buff过期

    # 元素反应
    REACTION_TRIGGERED = "reaction_triggered"  # 反应触发
    ELEMENT_ATTACHED = "element_attached"      # 元素附着
    ELEMENT_BURST = "element_burst"            # 元素爆发

    # 状态变化
    HP_CHANGED = "hp_changed"
    SHIELD_BROKEN = "shield_broken"
    STAGGER_START = "stagger_start"
    STAGGER_END = "stagger_end"

    # 自定义事件
    CUSTOM = "custom"


@dataclass
class Event:
    """事件对象"""
    event_type: EventType
    data: Dict[str, Any]
    source: Optional[Any] = None      # 事件源（通常是角色实例）
    target: Optional[Any] = None      # 事件目标
    tick: int = 0                     # 发生时间
    cancelled: bool = False           # 是否取消
    modified: bool = False            # 是否被修改

    def cancel(self):
        """取消事件"""
        self.cancelled = True

    def get(self, key: str, default: Any = None) -> Any:
        """安全地获取事件数据"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        """设置事件数据"""
        self.data[key] = value
        self.modified = True


class EventListener:
    """事件监听器"""

    def __init__(self, callback: Callable[[Event], None],
                 priority: int = 0, once: bool = False):
        """
        Args:
            callback: 回调函数
            priority: 优先级（数值越大越先执行）
            once: 是否只触发一次
        """
        self.callback = callback
        self.priority = priority
        self.once = once
        self.executed_count = 0

    def execute(self, event: Event):
        """执行回调"""
        self.callback(event)
        self.executed_count += 1

    def should_remove(self) -> bool:
        """判断是否应该移除"""
        return self.once and self.executed_count > 0


class EventBus:
    """事件总线"""

    def __init__(self):
        self._listeners: Dict[EventType, List[EventListener]] = defaultdict(list)
        self._global_listeners: List[EventListener] = []
        self._event_history: List[Event] = []
        self._max_history = 100  # 保留最近的事件历史
        self._enabled = True

    def subscribe(self, event_type: EventType,
                 callback: Callable[[Event], None],
                 priority: int = 0, once: bool = False) -> EventListener:
        """
        订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数
            priority: 优先级（0-100，数值越大越先执行）
            once: 是否只触发一次

        Returns:
            EventListener: 监听器对象（可用于取消订阅）
        """
        listener = EventListener(callback, priority, once)
        self._listeners[event_type].append(listener)
        self._listeners[event_type].sort(key=lambda x: x.priority, reverse=True)
        return listener

    def subscribe_all(self, callback: Callable[[Event], None],
                     priority: int = 0) -> EventListener:
        """
        订阅所有事件（全局监听器）

        Args:
            callback: 回调函数
            priority: 优先级

        Returns:
            EventListener: 监听器对象
        """
        listener = EventListener(callback, priority)
        self._global_listeners.append(listener)
        self._global_listeners.sort(key=lambda x: x.priority, reverse=True)
        return listener

    def unsubscribe(self, event_type: EventType, listener: EventListener):
        """取消订阅"""
        if event_type in self._listeners:
            if listener in self._listeners[event_type]:
                self._listeners[event_type].remove(listener)

    def emit(self, event: Event):
        """
        发布事件

        Args:
            event: 事件对象
        """
        if not self._enabled:
            return

        # 记录事件历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # 执行全局监听器
        for listener in list(self._global_listeners):
            if event.cancelled:
                break
            listener.execute(event)

        # 执行特定类型监听器
        if event.event_type in self._listeners:
            listeners_to_remove = []

            for listener in list(self._listeners[event.event_type]):
                if event.cancelled:
                    break

                listener.execute(event)

                if listener.should_remove():
                    listeners_to_remove.append(listener)

            # 移除一次性监听器
            for listener in listeners_to_remove:
                self._listeners[event.event_type].remove(listener)

    def emit_simple(self, event_type: EventType, **kwargs):
        """
        快捷方式：发布简单事件

        Args:
            event_type: 事件类型
            **kwargs: 事件数据
        """
        event = Event(event_type=event_type, data=kwargs)
        self.emit(event)

    def clear_listeners(self, event_type: Optional[EventType] = None):
        """
        清除监听器

        Args:
            event_type: 如果指定，只清除该类型的监听器；否则清除所有
        """
        if event_type is None:
            self._listeners.clear()
            self._global_listeners.clear()
        elif event_type in self._listeners:
            self._listeners[event_type].clear()

    def get_listener_count(self, event_type: Optional[EventType] = None) -> int:
        """获取监听器数量"""
        if event_type is None:
            return sum(len(listeners) for listeners in self._listeners.values()) + len(self._global_listeners)
        return len(self._listeners.get(event_type, []))

    def get_event_history(self, event_type: Optional[EventType] = None,
                         limit: int = 10) -> List[Event]:
        """
        获取事件历史

        Args:
            event_type: 如果指定，只返回该类型的事件
            limit: 返回数量限制

        Returns:
            事件列表（最新的在前）
        """
        if event_type is None:
            return self._event_history[-limit:][::-1]

        filtered = [e for e in self._event_history if e.event_type == event_type]
        return filtered[-limit:][::-1]

    def enable(self):
        """启用事件系统"""
        self._enabled = True

    def disable(self):
        """禁用事件系统"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled

    def reset(self):
        """重置事件总线"""
        self.clear_listeners()
        self._event_history.clear()


# 便捷的装饰器
def on_event(event_bus: EventBus, event_type: EventType, priority: int = 0):
    """
    事件监听装饰器

    Usage:
        @on_event(engine.event_bus, EventType.DAMAGE_DEALT)
        def on_damage(event):
            print(f"Damage dealt: {event.get('damage')}")
    """
    def decorator(func: Callable[[Event], None]):
        event_bus.subscribe(event_type, func, priority)
        return func
    return decorator


# 事件构建器（便捷创建常用事件）
class EventBuilder:
    """事件构建器，提供便捷的事件创建方法"""

    @staticmethod
    def damage_event(source, target, damage: float, skill_name: str,
                    element, move_type, tick: int = 0, is_crit: bool = False) -> Event:
        """创建伤害事件"""
        return Event(
            event_type=EventType.PRE_DAMAGE,
            data={
                "damage": damage,
                "skill_name": skill_name,
                "element": element,
                "move_type": move_type,
                "is_crit": is_crit,
            },
            source=source,
            target=target,
            tick=tick
        )

    @staticmethod
    def buff_event(event_type: EventType, owner, buff_name: str,
                  source, stacks: int = 1, tick: int = 0,
                  tags: list = None, buff_instance = None) -> Event:
        """创建Buff事件"""
        data = {
            "buff_name": buff_name,
            "stacks": stacks,
        }

        # 添加可选参数
        if tags is not None:
            data["tags"] = tags
        if buff_instance is not None:
            data["buff_instance"] = buff_instance

        return Event(
            event_type=event_type,
            data=data,
            source=source,
            target=owner,
            tick=tick
        )

    @staticmethod
    def reaction_event(trigger, target, reaction_type,
                      level: int, tick: int = 0) -> Event:
        """创建反应事件"""
        return Event(
            event_type=EventType.REACTION_TRIGGERED,
            data={
                "reaction_type": reaction_type,
                "level": level,
            },
            source=trigger,
            target=target,
            tick=tick
        )

    @staticmethod
    def action_event(event_type: EventType, character,
                    action_name: str, duration: int, tick: int = 0, move_type=None) -> Event:
        """创建行动事件"""
        data = {
            "action_name": action_name,
            "duration": duration,
        }
        if move_type is not None:
            data["move_type"] = move_type
        return Event(
            event_type=event_type,
            data=data,
            source=character,
            tick=tick
        )
