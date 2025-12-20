# mechanics/qte_system.py
"""
条件触发技能系统（QTE System）
支持基于游戏事件的反应式技能触发
"""
from typing import Callable, Optional, List, Dict, Any
from dataclasses import dataclass
from simulation.event_system import Event, EventType


@dataclass
class QTECondition:
    """QTE触发条件"""
    name: str                           # 条件名称
    description: str                    # 条件描述
    check: Callable[[Event], bool]      # 条件检查函数
    priority: int = 0                   # 优先级


@dataclass
class QTESkill:
    """QTE技能定义"""
    name: str                           # 技能名称
    description: str                    # 技能描述
    conditions: List[QTECondition]      # 触发条件列表
    cooldown: int = 0                   # 冷却时间（ticks）
    can_trigger: Callable[[], bool] = lambda: True  # 额外检查（如资源、CD）
    on_trigger: Optional[Callable[[Event], None]] = None  # 触发回调


class QTEManager:
    """
    条件触发技能管理器
    管理角色的QTE技能和条件监听
    """

    def __init__(self, character, engine):
        """
        Args:
            character: 角色实例
            engine: 引擎实例（包含event_bus）
        """
        self.character = character
        self.engine = engine
        self.event_bus = engine.event_bus

        # QTE技能列表
        self.qte_skills: List[QTESkill] = []

        # CD追踪
        self.cooldowns: Dict[str, int] = {}

        # 监听器记录（用于清理）
        self.listeners = []

    def register_qte(self, qte_skill: QTESkill):
        """注册一个QTE技能"""
        self.qte_skills.append(qte_skill)

        # 为每个条件订阅对应的事件
        for condition in qte_skill.conditions:
            # 根据条件名称推断需要监听的事件类型
            event_types = self._infer_event_types(condition)

            for event_type in event_types:
                listener = self.event_bus.subscribe(
                    event_type,
                    lambda event, cond=condition, qte=qte_skill: self._on_event(event, cond, qte),
                    priority=condition.priority
                )
                self.listeners.append((event_type, listener))

    def _infer_event_types(self, condition: QTECondition) -> List[EventType]:
        """根据条件名称推断需要监听的事件类型"""
        event_mapping = {
            'buff_applied': [EventType.BUFF_APPLIED],
            'burning': [EventType.BUFF_APPLIED],
            'corrosion': [EventType.BUFF_APPLIED],
            'reaction': [EventType.REACTION_TRIGGERED],
            'heavy_attack': [EventType.SKILL_CAST, EventType.ACTION_START],
            'damage': [EventType.DAMAGE_DEALT],
            'crit': [EventType.CRIT_DEALT],
        }

        # 根据条件名称关键词匹配
        for keyword, event_types in event_mapping.items():
            if keyword in condition.name.lower():
                return event_types

        # 默认监听所有事件
        return [EventType.BUFF_APPLIED, EventType.REACTION_TRIGGERED,
                EventType.SKILL_CAST, EventType.ACTION_START]

    def _on_event(self, event: Event, condition: QTECondition, qte_skill: QTESkill):
        """事件回调处理"""
        # 检查CD
        if self.cooldowns.get(qte_skill.name, 0) > 0:
            return

        # 检查条件
        if not condition.check(event):
            return

        # 额外检查
        if not qte_skill.can_trigger():
            return

        # 触发QTE
        self._trigger_qte(event, qte_skill)

    def _trigger_qte(self, event: Event, qte_skill: QTESkill):
        """触发QTE技能"""
        self.engine.log(f"[QTE触发] {self.character.name} -> {qte_skill.name}")

        # 设置CD
        self.cooldowns[qte_skill.name] = qte_skill.cooldown

        # 执行回调
        if qte_skill.on_trigger:
            qte_skill.on_trigger(event)

    def on_tick(self):
        """每tick更新CD"""
        for skill_name in list(self.cooldowns.keys()):
            if self.cooldowns[skill_name] > 0:
                self.cooldowns[skill_name] -= 1

    def cleanup(self):
        """清理所有监听器"""
        for event_type, listener in self.listeners:
            self.event_bus.unsubscribe(event_type, listener)
        self.listeners.clear()


# ===== 预定义常用条件 =====

class QTEConditions:
    """常用QTE条件库"""

    @staticmethod
    def enemy_burning(target_name: str = None):
        """敌人进入燃烧状态"""
        def check(event: Event) -> bool:
            if event.event_type != EventType.BUFF_APPLIED:
                return False

            buff_name = event.get('buff_name', '')
            owner = event.get('owner', '')

            # 检查是否是燃烧buff
            is_burning = 'burn' in buff_name.lower() or '燃烧' in buff_name

            # 如果指定了目标，检查目标
            if target_name:
                return is_burning and target_name in str(owner)

            return is_burning

        return QTECondition(
            name="enemy_burning",
            description="敌人进入燃烧状态",
            check=check,
            priority=10
        )

    @staticmethod
    def enemy_corrosion(target_name: str = None):
        """敌人进入腐蚀状态"""
        def check(event: Event) -> bool:
            if event.event_type != EventType.BUFF_APPLIED:
                return False

            buff_name = event.get('buff_name', '')
            owner = event.get('owner', '')

            # 检查是否是腐蚀buff
            is_corrosion = 'corrosion' in buff_name.lower() or '腐蚀' in buff_name

            if target_name:
                return is_corrosion and target_name in str(owner)

            return is_corrosion

        return QTECondition(
            name="enemy_corrosion",
            description="敌人进入腐蚀状态",
            check=check,
            priority=10
        )

    @staticmethod
    def enemy_dot(target_name: str = None):
        """敌人进入任何DOT状态"""
        def check(event: Event) -> bool:
            if event.event_type != EventType.BUFF_APPLIED:
                return False

            buff_name = event.get('buff_name', '')
            owner = event.get('owner', '')

            # 检查是否是DOT类buff
            is_dot = any(keyword in buff_name.lower() for keyword in
                        ['burn', 'corrosion', '燃烧', '腐蚀', 'bleed', '流血'])

            if target_name:
                return is_dot and target_name in str(owner)

            return is_dot

        return QTECondition(
            name="enemy_dot",
            description="敌人进入任何DOT状态",
            check=check,
            priority=10
        )

    @staticmethod
    def ally_heavy_attack(ally_name: str = None):
        """队友释放重击"""
        def check(event: Event) -> bool:
            if event.event_type not in [EventType.SKILL_CAST, EventType.ACTION_START]:
                return False

            action_name = event.get('action_name', '')
            character = event.get('character', '')

            # 检查是否是重击类技能
            is_heavy = any(keyword in action_name.lower() for keyword in
                          ['heavy', 'charged', '重击', '蓄力', 'burst', '爆发'])

            if ally_name:
                return is_heavy and ally_name in str(character)

            return is_heavy

        return QTECondition(
            name="ally_heavy_attack",
            description="队友释放重击",
            check=check,
            priority=5
        )

    @staticmethod
    def ally_skill_cast(ally_name: str = None, skill_name: str = None):
        """队友释放技能"""
        def check(event: Event) -> bool:
            if event.event_type != EventType.SKILL_CAST:
                return False

            character = event.get('character', '')
            action = event.get('action_name', '')

            if ally_name and ally_name not in str(character):
                return False

            if skill_name and skill_name not in action:
                return False

            return True

        return QTECondition(
            name="ally_skill_cast",
            description=f"队友释放技能{f'({skill_name})' if skill_name else ''}",
            check=check,
            priority=5
        )

    @staticmethod
    def enemy_reaction(reaction_type: str = None):
        """敌人触发元素反应"""
        def check(event: Event) -> bool:
            if event.event_type != EventType.REACTION_TRIGGERED:
                return False

            if reaction_type:
                r_type = event.get('reaction_type', '')
                return reaction_type.lower() in str(r_type).lower()

            return True

        return QTECondition(
            name="enemy_reaction",
            description=f"敌人触发{reaction_type if reaction_type else '元素反应'}",
            check=check,
            priority=8
        )

    @staticmethod
    def combo(conditions: List[QTECondition], window_ticks: int = 30):
        """组合条件：多个条件在时间窗口内依次触发"""
        triggered = []
        last_tick = [0]

        def check(event: Event) -> bool:
            nonlocal triggered, last_tick

            current_tick = event.tick

            # 时间窗口过期，重置
            if current_tick - last_tick[0] > window_ticks:
                triggered.clear()

            # 检查当前事件是否满足下一个条件
            if len(triggered) < len(conditions):
                next_condition = conditions[len(triggered)]
                if next_condition.check(event):
                    triggered.append(event)
                    last_tick[0] = current_tick

                    # 所有条件都满足
                    if len(triggered) == len(conditions):
                        triggered.clear()
                        return True

            return False

        return QTECondition(
            name="combo",
            description=f"组合条件：{len(conditions)}个条件在{window_ticks/10}秒内触发",
            check=check,
            priority=15
        )


# ===== 使用示例 =====

def example_levatine_qte(character, engine, target):
    """
    示例：莱瓦汀的QTE - 当敌人进入燃烧或腐蚀状态时触发

    效果：让所有燃烧/腐蚀敌人脚下喷出火焰，造成灼热伤害，获得1层熔火
    """
    from core.calculator import DamageEngine
    from core.enums import Element, MoveType

    def on_qte_trigger(event: Event):
        """QTE触发回调"""
        engine.log(f"   >>> [炽焰喷发] 燃烧/腐蚀状态触发！")

        # 造成伤害
        panel = character.get_current_panel()
        mv = 250  # 250% 倍率

        base_dmg = DamageEngine.calculate(
            panel, target.get_defense_stats(),
            mv, Element.HEAT, move_type=MoveType.QTE
        )

        target.take_damage(base_dmg)
        engine.log(f"   [伤害] 炽焰喷发造成: {int(base_dmg)}")

        # 获得1层熔火
        if hasattr(character, 'molten_stacks'):
            character.molten_stacks = min(4, character.molten_stacks + 1)
            engine.log(f"   [天赋] 获得熔火层数: {character.molten_stacks}")

        # 记录统计
        if hasattr(engine, 'statistics'):
            engine.statistics.record_damage(
                tick=engine.tick,
                source=character.name,
                target=target.name,
                skill_name="炽焰喷发(QTE)",
                damage=base_dmg,
                element=Element.HEAT,
                move_type=MoveType.QTE,
                is_crit=False,
                is_reaction=False
            )

    # 创建QTE管理器
    qte_manager = QTEManager(character, engine)

    # 定义QTE技能
    flame_burst_qte = QTESkill(
        name="炽焰喷发",
        description="当敌人进入燃烧或腐蚀状态时，对其造成灼热伤害并获得1层熔火",
        conditions=[
            QTEConditions.enemy_burning(target_name=target.name),
            QTEConditions.enemy_corrosion(target_name=target.name)
        ],
        cooldown=50,  # 5秒CD
        can_trigger=lambda: True,  # 无额外条件
        on_trigger=on_qte_trigger
    )

    # 注册QTE
    qte_manager.register_qte(flame_burst_qte)

    return qte_manager


def example_combo_qte(character, engine, target):
    """
    示例：连携QTE - 队友释放重击后，自己释放技能触发
    """
    def on_combo_trigger(event: Event):
        engine.log(f"   >>> [完美连携] 触发！")
        # 执行连携技能...

    qte_manager = QTEManager(character, engine)

    combo_qte = QTESkill(
        name="完美连携",
        description="队友释放重击后，在3秒内自己释放技能触发",
        conditions=[
            QTEConditions.combo([
                QTEConditions.ally_heavy_attack(),
                QTEConditions.ally_skill_cast(ally_name=character.name)
            ], window_ticks=30)
        ],
        cooldown=100,
        on_trigger=on_combo_trigger
    )

    qte_manager.register_qte(combo_qte)
    return qte_manager
