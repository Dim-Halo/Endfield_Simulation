"""
核心架构升级 - 快速使用示例

演示如何使用新的配置管理、统计分析和事件系统
"""
from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.levatine_sim import LevatineSim
from core.config_manager import get_config
from simulation.event_system import EventType


def example_basic_usage():
    """示例1：基本使用（无需修改原有代码）"""
    print("=" * 60)
    print("示例1：基本使用 - 自动统计和事件系统")
    print("=" * 60)

    # 创建引擎（自动集成新系统）
    sim = SimEngine()

    # 创建敌人和角色（与之前完全一样）
    target = DummyEnemy(sim, "测试假人", defense=100, resistances={"heat": 0.0})
    leva = LevatineSim(sim, target)

    sim.entities.extend([leva, target])

    # 设置简单脚本
    leva.set_script(["a1", "skill", "ult"])

    # 运行模拟
    sim.run(max_seconds=10)

    # 新功能：自动生成统计报告
    print("\n" + sim.statistics.generate_report())


def example_config_management():
    """示例2：配置管理"""
    print("\n" + "=" * 60)
    print("示例2：配置管理")
    print("=" * 60)

    # 获取配置单例
    config = get_config()

    # 读取配置
    print(f"当前Tick速率: {config.tick_rate} (1 tick = {1/config.tick_rate}s)")
    print(f"防御公式常数: {config.damage_formula_const}")
    print(f"法术爆发基础倍率: {config.reaction_base_mv['burst']}%")

    # 修改配置
    original_const = config.damage_formula_const
    config.damage_formula_const = 120  # 修改防御公式常数

    print(f"\n修改后防御公式常数: {config.damage_formula_const}")

    # 恢复默认
    config.damage_formula_const = original_const

    # 导出配置到字典
    config_dict = config.to_dict()
    print(f"\n配置项数量: {len(config_dict)}")


def example_event_system():
    """示例3：事件系统 - 监听战斗事件"""
    print("\n" + "=" * 60)
    print("示例3：事件系统 - 实时监听战斗事件")
    print("=" * 60)

    sim = SimEngine()
    target = DummyEnemy(sim, "测试假人", defense=100, resistances={"heat": 0.0})
    leva = LevatineSim(sim, target)

    sim.entities.extend([leva, target])

    # 订阅事件：统计暴击次数
    crit_count = {"count": 0}

    def on_crit(event):
        crit_count["count"] += 1
        damage = event.get("damage")
        print(f"   🎯 监听到暴击! 伤害: {int(damage)}")

    sim.event_bus.subscribe(EventType.CRIT_DEALT, on_crit)

    # 订阅事件：监听技能释放
    def on_action_start(event):
        action_name = event.get("action_name")
        character = event.source.name if hasattr(event.source, 'name') else "未知"
        print(f"   📢 {character} 开始释放: {action_name}")

    sim.event_bus.subscribe(EventType.ACTION_START, on_action_start)

    # 设置脚本
    leva.set_script(["a1", "skill", "ult"])

    # 运行模拟
    sim.run(max_seconds=10)

    print(f"\n本次战斗共触发 {crit_count['count']} 次暴击")


def example_advanced_event():
    """示例4：高级事件使用 - 修改伤害"""
    print("\n" + "=" * 60)
    print("示例4：高级事件使用 - 动态修改伤害")
    print("=" * 60)

    sim = SimEngine()
    target = DummyEnemy(sim, "测试假人", defense=100, resistances={"heat": 0.0})
    leva = LevatineSim(sim, target)

    sim.entities.extend([leva, target])

    # 订阅PRE_DAMAGE事件，修改伤害值
    def boost_damage(event):
        """所有伤害提升50%（仅作演示）"""
        original_damage = event.get("damage")
        boosted_damage = original_damage * 1.5
        event.set("damage", boosted_damage)
        print(f"   💪 伤害增强: {int(original_damage)} -> {int(boosted_damage)}")

    # 使用高优先级确保在其他监听器之前执行
    sim.event_bus.subscribe(EventType.PRE_DAMAGE, boost_damage, priority=100)

    # 设置脚本
    leva.set_script(["a1"])

    # 运行模拟
    sim.run(max_seconds=5)


def example_statistics_analysis():
    """示例5：详细统计分析"""
    print("\n" + "=" * 60)
    print("示例5：详细统计分析")
    print("=" * 60)

    sim = SimEngine()
    target = DummyEnemy(sim, "测试假人", defense=100, resistances={"heat": 0.0})
    leva = LevatineSim(sim, target)

    sim.entities.extend([leva, target])
    leva.set_script(["a1", "skill", "ult", "a1", "skill"])

    sim.run(max_seconds=15)

    # 获取统计对象
    stats = sim.statistics

    # 查询各种统计数据
    print(f"\n战斗时长: {stats.combat_duration / 10.0:.1f}秒")
    print(f"总伤害: {int(stats.total_damage):,}")
    print(f"莱瓦汀DPS: {stats.calculate_dps('莱瓦汀'):.1f}")
    print(f"实际暴击率: {stats.get_crit_rate('莱瓦汀') * 100:.1f}%")

    # 伤害分解
    breakdown = stats.get_damage_breakdown('莱瓦汀')
    print("\n技能伤害占比:")
    for skill, pct in breakdown.items():
        print(f"  {skill}: {pct * 100:.1f}%")

    # 元素反应统计
    reactions = stats.get_reaction_summary()
    if reactions:
        print("\n元素反应触发:")
        for reaction_type, count in reactions.items():
            print(f"  {reaction_type.value}: {count}次")


def example_event_driven_mechanic():
    """示例6：使用事件系统实现角色被动"""
    print("\n" + "=" * 60)
    print("示例6：事件驱动的角色被动机制")
    print("=" * 60)

    # 这个示例展示如何在不修改核心代码的情况下
    # 为角色添加"每次暴击后攻击力提升10%"的被动

    sim = SimEngine()
    target = DummyEnemy(sim, "测试假人", defense=100, resistances={"heat": 0.0})
    leva = LevatineSim(sim, target)

    sim.entities.extend([leva, target])

    # 实现被动：暴击后增加攻击力
    from mechanics.buff_system import AtkPctBuff

    def passive_on_crit(event):
        """被动：暴击后获得攻击力提升"""
        if event.source == leva:  # 只对莱瓦汀生效
            buff = AtkPctBuff("暴击加成", 0.10, duration=3.0)
            leva.buffs.add_buff(buff, sim)
            print("   ⚡ 触发被动: 获得10%攻击力加成(3秒)")

    sim.event_bus.subscribe(EventType.CRIT_DEALT, passive_on_crit)

    leva.set_script(["a1", "a1", "a1"])
    sim.run(max_seconds=10)


if __name__ == "__main__":
    # 运行所有示例
    example_basic_usage()
    example_config_management()
    example_event_system()
    example_advanced_event()
    example_statistics_analysis()
    example_event_driven_mechanic()

    print("\n" + "=" * 60)
    print("所有示例运行完毕!")
    print("=" * 60)
