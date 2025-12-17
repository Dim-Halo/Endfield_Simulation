# 架构升级说明文档

## 版本信息
- **升级日期**: 2025-12-15
- **架构版本**: v2.0
- **主要改进**: 核心架构升级（配置管理、统计分析、事件驱动）

---

## 一、新增核心系统

### 1. 统一配置管理系统 (`core/config_manager.py`)

**功能**：
- 集中管理所有游戏数值配置
- 支持从JSON/YAML文件加载配置
- 提供单例模式的全局访问

**使用示例**：
```python
from core.config_manager import get_config

# 获取配置实例
config = get_config()

# 访问配置项
tick_rate = config.tick_rate
reaction_mv = config.reaction_base_mv["burst"]

# 从文件加载配置
config.load_from_json("config.json")

# 导出配置
config.save_to_json("config_backup.json")

# 计算元素反应倍率
mv = config.get_reaction_mv("burst", level=3, tech_power=500, attacker_lvl=80)
```

**配置项分类**：
- 伤害公式参数
- 元素反应基础配置
- 源石技艺增强系数
- Tick系统配置
- 日志和性能开关

---

### 2. 战斗统计分析系统 (`core/statistics.py`)

**功能**：
- 记录所有伤害、技能使用、Buff、元素反应
- 自动计算DPS、暴击率、伤害占比
- 生成详细的战斗报告

**使用示例**：
```python
# 在SimEngine中自动集成
engine = SimEngine()

# 模拟结束后获取统计
stats = engine.statistics

# 查询角色DPS
levatine_dps = stats.calculate_dps("莱瓦汀")
total_dps = stats.calculate_dps()  # 全队DPS

# 获取伤害分解
breakdown = stats.get_damage_breakdown("莱瓦汀")
# 返回: {"灼热荆棘": 0.45, "普攻A1": 0.30, "元素反应": 0.25}

# 获取暴击率
crit_rate = stats.get_crit_rate("莱瓦汀")

# 获取元素反应统计
reactions = stats.get_reaction_summary()
# 返回: {ReactionType.BURNING: 5, ReactionType.BURST: 12}

# 生成文本报告
report = stats.generate_report()
print(report)

# 获取时间线数据（用于绘图）
timeline = stats.generate_timeline_data(window_size=10)
```

**统计数据结构**：
- `CharacterStats`: 单角色统计（总伤、技能伤害、反应数、暴击数）
- `DamageRecord`: 单次伤害记录（时间、来源、目标、伤害值、是否暴击）
- `ReactionRecord`: 元素反应记录
- `SkillUsageRecord`: 技能使用记录

---

### 3. 事件驱动系统 (`simulation/event_system.py`)

**功能**：
- 解耦核心逻辑，支持灵活扩展
- 发布-订阅模式
- 支持事件优先级、事件取消、一次性监听

**使用示例**：

#### 基础用法
```python
from simulation.event_system import EventType, EventBus

# 获取事件总线（已集成在SimEngine中）
event_bus = engine.event_bus

# 订阅事件
def on_damage(event):
    damage = event.get('damage')
    attacker = event.source.name
    print(f"{attacker}造成了{damage}点伤害")

event_bus.subscribe(EventType.POST_DAMAGE, on_damage, priority=10)

# 发布事件
event_bus.emit_simple(EventType.DAMAGE_DEALT, damage=1000, target="敌人")
```

#### 高级用法：实现角色被动
```python
class LevatineSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("莱瓦汀", engine)

        # 订阅自己造成暴击时的事件
        engine.event_bus.subscribe(
            EventType.CRIT_DEALT,
            self.on_crit_dealt,
            priority=50
        )

    def on_crit_dealt(self, event):
        """暴击时获得攻击力加成"""
        if event.source == self:
            buff = AtkPctBuff("暴击加成", 0.15, duration=5.0)
            self.buffs.add_buff(buff, self.engine)
```

#### 修改伤害
```python
def increase_fire_damage(event):
    """火伤提升20%"""
    element = event.get('element')
    if element == Element.HEAT:
        current_dmg = event.get('damage')
        event.set('damage', current_dmg * 1.2)

engine.event_bus.subscribe(EventType.PRE_DAMAGE, increase_fire_damage, priority=90)
```

**可用事件类型**：
- 战斗生命周期: `COMBAT_START`, `COMBAT_END`, `TICK_START`, `TICK_END`
- 伤害相关: `PRE_DAMAGE`, `POST_DAMAGE`, `CRIT_DEALT`
- 行动相关: `ACTION_START`, `ACTION_END`, `SKILL_CAST`
- Buff相关: `BUFF_APPLIED`, `BUFF_REMOVED`, `BUFF_EXPIRED`
- 元素反应: `REACTION_TRIGGERED`, `ELEMENT_ATTACHED`

---

## 二、现有系统升级

### 1. SimEngine 升级

**新增功能**：
```python
class SimEngine:
    def __init__(self):
        # 原有
        self.tick = 0
        self.entities = []

        # 新增
        self.config = ConfigManager.get_instance()
        self.statistics = CombatStatistics()
        self.event_bus = EventBus()
```

**改进**：
- 集成三大新系统
- 增加异常处理（实体on_tick出错不会中断模拟）
- 自动发布战斗生命周期事件

---

### 2. BaseActor 升级

**新增功能**：
- `start_action()` 发布行动开始事件，记录技能使用
- `_process_action()` 发布行动结束事件
- 自动统计技能使用次数

**使用示例**：
```python
# 在角色实现中使用新的伤害接口
from core.damage_helper import deal_damage

def create_skill(self):
    def hit():
        deal_damage(
            engine=self.engine,
            attacker=self,
            target=self.target,
            skill_name="灼热荆棘",
            skill_mv=450,
            element=Element.HEAT,
            move_type=MoveType.SKILL
        )

    return Action("灼热荆棘", duration=30, events=[
        DamageEvent(time_offset=15, damage_func=hit)
    ])
```

---

### 3. BuffManager 升级

**新增功能**：
- Buff施加/刷新/过期时自动发布事件
- 支持事件系统监听Buff变化

---

### 4. Web界面 (app.py) 大幅增强

**新增功能**：
- **角色伤害排行榜**：实时显示每个角色的伤害和DPS
- **伤害占比饼图**：使用Plotly可视化
- **技能伤害分解**：查看单个角色各技能的伤害占比
- **元素反应统计**：显示各类反应触发次数
- **实际暴击率**：对比面板暴击率

---

## 三、新增工具模块

### 1. 伤害处理辅助函数 (`core/damage_helper.py`)

**功能**：
- `deal_damage()`: 统一的伤害处理接口
- `deal_true_damage()`: 真实伤害接口

**优势**：
- 自动处理元素反应
- 自动发布事件
- 自动记录统计
- 统一的日志格式

**替代方案**：
```python
# 旧方式（手动处理）
attacker_stats = self.get_current_panel()
reaction = target.reaction_mgr.apply_hit(Element.HEAT, ...)
target_stats = target.get_defense_stats()
damage = DamageEngine.calculate(...)
target.take_damage(damage)
engine.log(...)

# 新方式（一行搞定）
deal_damage(engine, self, target, "技能名", 450, Element.HEAT, MoveType.SKILL)
```

---

## 四、使用迁移指南

### 对于角色实现者

**如果你想使用新的统计和事件系统**：

1. **使用`deal_damage()`替代手动伤害计算**：
```python
# 旧代码
def hit():
    stats = self.get_current_panel()
    # ... 复杂的手动计算

# 新代码
from core.damage_helper import deal_damage

def hit():
    deal_damage(self.engine, self, self.target, "技能名", 450, Element.HEAT)
```

2. **订阅事件实现特殊机制**：
```python
def __init__(self, engine, target):
    super().__init__("角色名", engine)

    # 监听队友造成伤害
    engine.event_bus.subscribe(EventType.DAMAGE_DEALT, self.on_ally_damage)

def on_ally_damage(self, event):
    # 队友造成伤害时自己获得增益
    pass
```

---

### 对于配置管理

**创建自定义配置文件**：
```json
{
  "damage_formula_const": 100,
  "reaction_base_mv": {
    "burst": 180,
    "burning_dot": 15
  },
  "log_level": "DEBUG"
}
```

**加载配置**：
```python
from core.config_manager import get_config

config = get_config()
config.load_from_json("custom_config.json")
```

---

## 五、性能影响

**内存开销**：
- 统计系统：约占用5-10MB（取决于战斗时长）
- 事件系统：可忽略（<1MB）

**性能开销**：
- 统计记录：约5%性能开销
- 事件发布：约3%性能开销
- **总计**：约8-10%性能下降（可通过配置关闭）

**关闭统计/事件系统**：
```python
config = get_config()
config.enable_statistics = False
config.enable_event_system = False
```

---

## 六、向后兼容性

**完全兼容旧代码**：
- 所有旧的角色实现无需修改即可运行
- 新系统是**增强**而非**替换**
- 可以逐步迁移到新API

**建议迁移优先级**：
1. 立即使用：CLI和Web界面的统计报告（无需修改角色代码）
2. 逐步迁移：将伤害计算改为`deal_damage()`
3. 高级特性：使用事件系统实现复杂机制

---

## 七、示例：完整的角色实现

```python
from entities.characters.base_actor import BaseActor
from core.damage_helper import deal_damage
from core.enums import Element, MoveType
from simulation.action import Action, DamageEvent
from simulation.event_system import EventType

class ExampleChar(BaseActor):
    def __init__(self, engine, target):
        super().__init__("示例角色", engine)
        self.target = target

        # 订阅事件
        engine.event_bus.subscribe(EventType.CRIT_DEALT, self.on_crit)

    def on_crit(self, event):
        """暴击时触发"""
        if event.source == self:
            self.engine.log(f"[{self.name}] 触发被动！")

    def create_skill(self):
        def hit():
            deal_damage(
                self.engine, self, self.target,
                "技能名", 450, Element.HEAT, MoveType.SKILL
            )

        return Action("技能名", duration=30, events=[
            DamageEvent(15, hit)
        ])

    def parse_command(self, cmd):
        if cmd == "skill":
            return self.create_skill()
        # ...
```

---

## 八、常见问题

**Q: 会影响现有模拟结果吗？**
A: 不会。伤害计算公式完全未变，统计和事件系统只是旁路记录。

**Q: 如何关闭详细日志？**
A:
```python
config = get_config()
config.enable_detailed_logging = False
```

**Q: 统计数据会保存吗？**
A: 当前不会自动保存，可以手动导出：
```python
report = engine.statistics.generate_report()
with open("report.txt", "w") as f:
    f.write(report)
```

**Q: 可以监听特定角色的事件吗？**
A: 可以，通过检查`event.source`：
```python
def on_damage(event):
    if event.source.name == "莱瓦汀":
        # 只处理莱瓦汀的伤害
        pass
```

---

## 九、后续规划

**第二阶段改进**（优先级2）：
- [ ] 优化状态快照机制（减少深拷贝）
- [ ] 添加日志系统（使用Python logging）
- [ ] 依赖注入改进
- [ ] 单元测试框架

**第三阶段增强**（优先级3）：
- [ ] DPS时间轴曲线图
- [ ] Buff覆盖率甘特图
- [ ] 排轴对比功能
- [ ] 多目标战斗支持
- [ ] 战斗回放系统

---

## 十、贡献指南

如果你想扩展新系统：

1. **添加新事件类型**：在`EventType`枚举中添加
2. **添加新统计指标**：在`CharacterStats`中添加字段
3. **添加新配置项**：在`ConfigManager`中添加属性

---

## 联系方式

如有问题或建议，请提Issue或查看项目文档。
