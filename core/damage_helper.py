"""
伤害处理辅助函数
提供统一的伤害计算和记录接口
"""
from core.calculator import DamageEngine
from core.enums import Element, MoveType
from simulation.event_system import EventType, EventBuilder


def deal_damage(engine, attacker, target, skill_name: str, skill_mv: float,
                element: Element, move_type: MoveType = MoveType.OTHER):
    """
    统一的伤害处理接口

    功能：
    1. 获取攻击方面板快照
    2. 处理元素反应
    3. 计算伤害
    4. 发布事件
    5. 记录统计
    6. 应用伤害

    Args:
        engine: 模拟引擎
        attacker: 攻击者（角色实例）
        target: 目标（敌人实例）
        skill_name: 技能名称
        skill_mv: 技能倍率
        element: 元素类型
        move_type: 招式类型

    Returns:
        int: 最终伤害值
    """
    # 1. 获取攻击方面板
    attacker_stats = attacker.get_current_panel()

    # 2. 处理元素反应
    reaction_result = target.reaction_mgr.apply_hit(
        element,
        attacker_atk=attacker_stats['final_atk'],
        attacker_tech=attacker_stats.get('technique_power', 0),
        attacker_lvl=attacker_stats.get('level', 80)
    )

    # 3. 获取防御方数据
    target_stats = target.get_defense_stats()

    # 4. 计算基础伤害
    total_mv = skill_mv + reaction_result.extra_mv
    base_damage = DamageEngine.calculate(
        attacker_stats, target_stats, total_mv, element, move_type
    )

    # 5. 判断是否暴击
    crit_rate = attacker_stats.get('crit_rate', 0.0)
    import random
    is_crit = random.random() < crit_rate

    final_damage = base_damage

    # 6. 发布伤害前事件（允许其他系统修改伤害）
    pre_damage_event = EventBuilder.damage_event(
        source=attacker,
        target=target,
        damage=final_damage,
        skill_name=skill_name,
        element=element,
        move_type=move_type,
        tick=engine.tick,
        is_crit=is_crit
    )
    engine.event_bus.emit(pre_damage_event)

    # 如果事件被取消，则不造成伤害
    if pre_damage_event.cancelled:
        return 0

    # 从事件中获取可能被修改的伤害值
    final_damage = pre_damage_event.get('damage', final_damage)

    # 7. 应用伤害
    target.take_damage(final_damage)

    # 8. 记录统计
    is_reaction = reaction_result.extra_mv > 0
    engine.statistics.record_damage(
        tick=engine.tick,
        source=attacker.name,
        target=target.name,
        skill_name=skill_name,
        damage=final_damage,
        element=element,
        move_type=move_type,
        is_crit=is_crit,
        is_reaction=is_reaction
    )

    # 9. 发布伤害后事件
    post_damage_event = pre_damage_event
    post_damage_event.event_type = EventType.POST_DAMAGE
    post_damage_event.set('actual_damage', final_damage)
    engine.event_bus.emit(post_damage_event)

    # 10. 如果是暴击，发布暴击事件
    if is_crit:
        engine.event_bus.emit_simple(
            EventType.CRIT_DEALT,
            attacker=attacker.name,
            target=target.name,
            damage=final_damage,
            tick=engine.tick
        )

    # 11. 记录元素反应
    if is_reaction and reaction_result.reaction_type:
        engine.statistics.record_reaction(
            tick=engine.tick,
            trigger=attacker.name,
            target=target.name,
            reaction_type=reaction_result.reaction_type,
            level=target.reaction_mgr.attachment_stacks,
            extra_damage=reaction_result.extra_mv * attacker_stats['final_atk'] / 100.0
        )

    # 12. 日志输出
    log_parts = [f"[{attacker.name}] {skill_name} Hit造成伤害"]
    if is_crit:
        log_parts.append("💥 暴击!")
    log_parts.append(f"{int(final_damage)}")
    if reaction_result.log_msg:
        log_parts.append(f"| {reaction_result.log_msg}")

    engine.log(" ".join(log_parts))

    return final_damage


def deal_true_damage(engine, attacker, target, skill_name: str, damage: float):
    """
    造成真实伤害（无视防御和抗性）

    Args:
        engine: 模拟引擎
        attacker: 攻击者
        target: 目标
        skill_name: 技能名称
        damage: 伤害值

    Returns:
        float: 伤害值
    """
    # 应用伤害
    target.take_damage(damage)

    # 记录统计
    engine.statistics.record_damage(
        tick=engine.tick,
        source=attacker.name if hasattr(attacker, 'name') else str(attacker),
        target=target.name,
        skill_name=skill_name,
        damage=damage,
        element=Element.PHYSICAL,  # 真实伤害默认视为物理
        move_type=MoveType.OTHER,
        is_crit=False,
        is_reaction=False
    )

    # 日志
    engine.log(f"[{attacker.name if hasattr(attacker, 'name') else attacker}] {skill_name} 造成真实伤害 {int(damage)}")

    return damage
