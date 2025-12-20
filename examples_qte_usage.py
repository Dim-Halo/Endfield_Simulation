# examples_qte_usage.py
"""
QTE条件触发系统使用示例
演示如何为角色添加基于事件的反应式技能
"""

from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.levatine_sim import LevatineSim
from entities.characters.erdila_sim import ErdilaSim
from mechanics.qte_system import QTEManager, QTESkill, QTEConditions
from simulation.event_system import Event
from core.calculator import DamageEngine
from core.enums import Element, MoveType


# ===== 示例1：莱瓦汀 - 燃烧/腐蚀触发QTE =====

def setup_levatine_qte(levatine: LevatineSim, engine: SimEngine, target: DummyEnemy):
    """
    为莱瓦汀设置QTE：当敌人进入燃烧或腐蚀状态时触发
    效果：对敌人造成灼热伤害，并获得1层熔火
    """

    def on_flame_burst(event: Event):
        """炽焰喷发QTE回调"""
        engine.log(f"   >>> [炽焰喷发QTE] {event.get('buff_name')}状态触发！")

        # 造成250%倍率的灼热伤害
        panel = levatine.get_current_panel()
        mv = 250

        base_dmg = DamageEngine.calculate(
            panel, target.get_defense_stats(),
            mv, Element.HEAT, move_type=MoveType.QTE
        )

        target.take_damage(base_dmg)
        engine.log(f"   [QTE伤害] 造成: {int(base_dmg)}")

        # 获得1层熔火
        if hasattr(levatine, 'molten_stacks'):
            levatine.molten_stacks = min(4, levatine.molten_stacks + 1)
            engine.log(f"   [天赋触发] 当前熔火层数: {levatine.molten_stacks}")

        # 记录统计
        if hasattr(engine, 'statistics'):
            engine.statistics.record_damage(
                tick=engine.tick,
                source=levatine.name,
                target=target.name,
                skill_name="炽焰喷发(QTE)",
                damage=base_dmg,
                element=Element.HEAT,
                move_type=MoveType.QTE,
                is_crit=False,
                is_reaction=False
            )

    # 创建QTE管理器
    qte_manager = QTEManager(levatine, engine)

    # 定义QTE技能
    flame_burst = QTESkill(
        name="炽焰喷发",
        description="当敌人进入燃烧或腐蚀状态时触发",
        conditions=[
            QTEConditions.enemy_burning(target_name=target.name),
            QTEConditions.enemy_corrosion(target_name=target.name)
        ],
        cooldown=50,  # 5秒CD
        can_trigger=lambda: True,
        on_trigger=on_flame_burst
    )

    # 注册QTE
    qte_manager.register_qte(flame_burst)

    return qte_manager


# ===== 示例2：艾尔黛拉 - 任何DOT状态触发QTE =====

def setup_erdila_qte(erdila: ErdilaSim, engine: SimEngine, target: DummyEnemy):
    """
    为艾尔黛拉设置QTE：当敌人进入任何DOT状态时触发
    效果：额外治疗量提升50%，并对敌人造成自然伤害
    """

    def on_nature_bloom(event: Event):
        """自然绽放QTE回调"""
        buff_name = event.get('buff_name', '')
        engine.log(f"   >>> [自然绽放QTE] {buff_name}状态触发！")

        # 触发一次增强治疗
        engine.log(f"   [QTE效果] 触发增强治疗！")
        if hasattr(erdila, '_perform_heal'):
            erdila._perform_heal()

        # 造成150%自然伤害
        panel = erdila.get_current_panel()
        mv = 150

        base_dmg = DamageEngine.calculate(
            panel, target.get_defense_stats(),
            mv, Element.NATURE, move_type=MoveType.QTE
        )

        target.take_damage(base_dmg)
        engine.log(f"   [QTE伤害] 自然绽放造成: {int(base_dmg)}")

        # 记录统计
        if hasattr(engine, 'statistics'):
            engine.statistics.record_damage(
                tick=engine.tick,
                source=erdila.name,
                target=target.name,
                skill_name="自然绽放(QTE)",
                damage=base_dmg,
                element=Element.NATURE,
                move_type=MoveType.QTE,
                is_crit=False,
                is_reaction=False
            )

    qte_manager = QTEManager(erdila, engine)

    nature_bloom = QTESkill(
        name="自然绽放",
        description="当敌人进入任何DOT状态时触发额外治疗和伤害",
        conditions=[
            QTEConditions.enemy_dot(target_name=target.name)
        ],
        cooldown=80,  # 8秒CD
        can_trigger=lambda: True,
        on_trigger=on_nature_bloom
    )

    qte_manager.register_qte(nature_bloom)
    return qte_manager


# ===== 示例3：基于反应类型的QTE =====

def setup_reaction_qte(character, engine: SimEngine, target: DummyEnemy):
    """
    通用反应QTE：当触发特定元素反应时执行
    """

    def on_burning_reaction(event: Event):
        """燃烧反应触发"""
        reaction_type = event.get('reaction_type')
        attacker = event.get('attacker')
        engine.log(f"   >>> [反应QTE] {attacker}触发了{reaction_type.value}反应！")

        # 可以在这里添加任何效果
        # 例如：给攻击者加buff、造成额外伤害等

    qte_manager = QTEManager(character, engine)

    reaction_qte = QTESkill(
        name="灼热连锁",
        description="当触发燃烧反应时，追加一次攻击",
        conditions=[
            QTEConditions.enemy_reaction(reaction_type="burning")
        ],
        cooldown=30,
        on_trigger=on_burning_reaction
    )

    qte_manager.register_qte(reaction_qte)
    return qte_manager


# ===== 示例4：组合QTE - 队友连携 =====

def setup_combo_qte(character, engine: SimEngine):
    """
    组合QTE：队友释放技能后，自己在3秒内释放技能触发
    """

    def on_perfect_combo(event: Event):
        """完美连携触发"""
        engine.log(f"   >>> [完美连携] 触发！全队攻击力提升20%！")
        # 可以给全队加buff等

    qte_manager = QTEManager(character, engine)

    combo_qte = QTESkill(
        name="完美连携",
        description="队友释放技能后，3秒内自己释放技能触发",
        conditions=[
            QTEConditions.combo([
                QTEConditions.ally_skill_cast(),  # 任意队友技能
                QTEConditions.ally_skill_cast(ally_name=character.name)  # 自己的技能
            ], window_ticks=30)  # 3秒窗口
        ],
        cooldown=100,
        on_trigger=on_perfect_combo
    )

    qte_manager.register_qte(combo_qte)
    return qte_manager


# ===== 完整运行示例 =====

def run_qte_demo():
    """运行完整的QTE系统演示"""
    print("=" * 50)
    print("  QTE条件触发系统演示")
    print("=" * 50)

    # 初始化引擎
    sim = SimEngine()
    target = DummyEnemy()
    sim.add_entity(target)

    # 创建角色
    levatine = LevatineSim(sim, target)
    erdila = ErdilaSim(sim, target)

    # 加载脚本
    levatine.load_script([
        "wait 2.0",
        "skill",      # 莱瓦汀释放技能（会触发燃烧）
        "wait 3.0"
    ])

    erdila.load_script([
        "wait 5.0",
        "qte",        # 艾尔黛拉释放QTE（会触发腐蚀）
        "wait 3.0"
    ])

    sim.add_entity(levatine)
    sim.add_entity(erdila)

    # ===== 关键：为角色设置QTE =====
    levatine_qte = setup_levatine_qte(levatine, sim, target)
    erdila_qte = setup_erdila_qte(erdila, sim, target)

    # 需要在角色的on_tick中调用qte_manager.on_tick()更新CD
    # 将QTE管理器存储到角色实例中
    levatine.qte_manager = levatine_qte
    erdila.qte_manager = erdila_qte

    # 运行模拟
    print("\n开始模拟...")
    sim.run(max_seconds=10)

    print(f"\n战斗结束！敌人总伤害: {int(target.total_damage_taken)}")

    # 清理
    levatine_qte.cleanup()
    erdila_qte.cleanup()


# ===== 集成到角色类中的示例 =====

def integrate_qte_into_character():
    """
    展示如何将QTE系统集成到角色类中

    在实际使用时，应该在角色的__init__方法中创建QTE管理器：
    """
    example_code = '''
class LevatineSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("莱瓦汀", engine)
        self.target = target
        # ... 其他初始化代码 ...

        # 创建QTE管理器
        self.qte_manager = QTEManager(self, engine)

        # 注册QTE技能
        self._setup_qte_skills()

    def _setup_qte_skills(self):
        """设置角色的QTE技能"""
        # 定义炽焰喷发QTE
        flame_burst = QTESkill(
            name="炽焰喷发",
            description="当敌人进入燃烧或腐蚀状态时触发",
            conditions=[
                QTEConditions.enemy_burning(target_name=self.target.name),
                QTEConditions.enemy_corrosion(target_name=self.target.name)
            ],
            cooldown=50,
            on_trigger=self._on_flame_burst_qte
        )
        self.qte_manager.register_qte(flame_burst)

    def _on_flame_burst_qte(self, event: Event):
        """炽焰喷发QTE回调"""
        # QTE技能逻辑
        pass

    def on_tick(self, engine):
        # 更新QTE CD
        if hasattr(self, 'qte_manager'):
            self.qte_manager.on_tick()

        super().on_tick(engine)

    def __del__(self):
        """清理QTE监听器"""
        if hasattr(self, 'qte_manager'):
            self.qte_manager.cleanup()
    '''
    print(example_code)


if __name__ == "__main__":
    # 运行演示
    run_qte_demo()

    # 显示集成示例
    print("\n" + "=" * 50)
    print("  如何集成到角色类：")
    print("=" * 50)
    integrate_qte_into_character()
