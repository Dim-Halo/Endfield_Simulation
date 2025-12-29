# QTE条件触发系统使用指南

## 📖 系统概述

QTE（Quick Time Event）条件触发系统是一个基于事件总线的反应式技能框架，允许角色在特定游戏事件发生时自动触发技能。

### 核心特性

✅ **事件驱动** - 基于 EventBus，松耦合设计
✅ **灵活配置** - 支持多种触发条件组合
✅ **优先级控制** - 可设置事件处理优先级
✅ **CD管理** - 内置冷却时间管理
✅ **组合条件** - 支持时间窗口内的连续触发

---

## 🏗️ 架构概览

```
┌─────────────────────────────────────────────────┐
│                 游戏事件                          │
│  (Buff施加、元素反应、技能释放、伤害造成...)       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              EventBus 事件总线                    │
│  - 发布事件 (emit)                                │
│  - 订阅事件 (subscribe)                           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│            QTEManager 管理器                      │
│  - 注册QTE技能                                    │
│  - 监听事件                                        │
│  - 检查条件                                        │
│  - 管理CD                                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              QTE技能触发                          │
│  - 执行回调函数                                    │
│  - 造成伤害/施加Buff/播放特效                      │
└─────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 基础使用

```python
from mechanics.qte_system import QTEManager, QTESkill, QTEConditions

# 创建QTE管理器
qte_manager = QTEManager(character, engine)

# 定义QTE技能
qte_skill = QTESkill(
    name="炽焰喷发",
    description="当敌人进入燃烧状态时触发",
    conditions=[
        QTEConditions.enemy_burning(target_name=target.name)
    ],
    cooldown=50,  # 5秒CD
    on_trigger=my_callback_function
)

# 注册QTE
qte_manager.register_qte(qte_skill)
```

### 2. 实现触发回调

```python
def my_callback_function(event: Event):
    """QTE触发时执行"""
    # 获取事件数据
    buff_name = event.get('buff_name')
    target = event.get('target')

    # 造成伤害
    damage = calculate_damage(...)
    target.take_damage(damage)

    # 记录日志
    engine.log(f"[QTE触发] {buff_name}!")
```

### 3. 在角色类中集成

```python
class MyCharacter(BaseActor):
    def __init__(self, engine, target):
        super().__init__("角色名", engine)
        self.target = target

        # 创建QTE管理器
        self.qte_manager = QTEManager(self, engine)
        self._setup_qte_skills()

    def _setup_qte_skills(self):
        """注册角色的QTE技能"""
        self.qte_manager.register_qte(...)

    def on_tick(self, engine):
        # 更新QTE CD
        self.qte_manager.on_tick()
        super().on_tick(engine)

    def __del__(self):
        """清理监听器"""
        if hasattr(self, 'qte_manager'):
            self.qte_manager.cleanup()
```

---

## 📚 预定义条件库

### 敌人状态触发

```python
# 敌人进入燃烧状态
QTEConditions.enemy_burning(target_name="敌人名称")

# 敌人进入腐蚀状态
QTEConditions.enemy_corrosion(target_name="敌人名称")

# 敌人进入任何DOT状态（燃烧/腐蚀/流血等）
QTEConditions.enemy_dot(target_name="敌人名称")
```

### 元素反应触发

```python
# 触发任意元素反应
QTEConditions.enemy_reaction()

# 触发特定反应（burning/conductive/frozen/corrosion）
QTEConditions.enemy_reaction(reaction_type="burning")
```

### 队友行动触发

```python
# 队友释放重击
QTEConditions.ally_heavy_attack(ally_name="队友名称")

# 队友释放任意技能
QTEConditions.ally_skill_cast(ally_name="队友名称")

# 队友释放特定技能
QTEConditions.ally_skill_cast(
    ally_name="队友名称",
    skill_name="技能名称"
)
```

### 组合条件

```python
# 多个条件在时间窗口内依次触发
QTEConditions.combo([
    QTEConditions.ally_heavy_attack(),      # 队友重击
    QTEConditions.enemy_burning(),          # 然后敌人燃烧
], window_ticks=30)  # 3秒时间窗口
```

---

## 🎯 实战案例

### 案例1：莱瓦汀 - 燃烧/腐蚀QTE

**需求**：当敌人进入燃烧或腐蚀状态时，触发炽焰喷发，造成250%倍率伤害并获得1层熔火。

```python
def setup_levatine_qte(levatine, engine, target):
    def on_trigger(event: Event):
        engine.log(">>> [炽焰喷发QTE] 触发！")

        # 造成伤害
        panel = levatine.get_current_panel()
        dmg = DamageEngine.calculate(
            panel, target.get_defense_stats(),
            250, Element.HEAT, MoveType.QTE
        )
        target.take_damage(dmg)

        # 增加熔火层数
        levatine.molten_stacks = min(4, levatine.molten_stacks + 1)

    qte_manager = QTEManager(levatine, engine)

    qte_manager.register_qte(QTESkill(
        name="炽焰喷发",
        description="燃烧/腐蚀触发",
        conditions=[
            QTEConditions.enemy_burning(target_name=target.name),
            QTEConditions.enemy_corrosion(target_name=target.name)
        ],
        cooldown=50,
        on_trigger=on_trigger
    ))

    return qte_manager
```

### 案例2：艾尔黛拉 - DOT治疗增强

**需求**：当敌人进入任何DOT状态时，触发额外治疗和自然伤害。

```python
def setup_erdila_qte(erdila, engine, target):
    def on_trigger(event: Event):
        engine.log(">>> [自然绽放QTE] 触发！")

        # 触发治疗
        erdila._perform_heal()

        # 造成自然伤害
        panel = erdila.get_current_panel()
        dmg = DamageEngine.calculate(
            panel, target.get_defense_stats(),
            150, Element.NATURE, MoveType.QTE
        )
        target.take_damage(dmg)

    qte_manager = QTEManager(erdila, engine)

    qte_manager.register_qte(QTESkill(
        name="自然绽放",
        description="DOT状态触发治疗增强",
        conditions=[
            QTEConditions.enemy_dot(target_name=target.name)
        ],
        cooldown=80,
        on_trigger=on_trigger
    ))

    return qte_manager
```

### 案例3：队友连携QTE

**需求**：队友释放技能后，自己在3秒内释放技能触发全队增益。

```python
def setup_combo_qte(character, engine):
    def on_trigger(event: Event):
        engine.log(">>> [完美连携] 触发！")
        # 给全队加攻击力buff
        for entity in engine.entities:
            if hasattr(entity, 'buffs'):
                entity.buffs.add_buff(AtkBuff(...), engine)

    qte_manager = QTEManager(character, engine)

    qte_manager.register_qte(QTESkill(
        name="完美连携",
        description="队友连携触发",
        conditions=[
            QTEConditions.combo([
                QTEConditions.ally_skill_cast(),
                QTEConditions.ally_skill_cast(ally_name=character.name)
            ], window_ticks=30)
        ],
        cooldown=100,
        on_trigger=on_trigger
    ))

    return qte_manager
```

---

## 🔧 自定义条件

如果预定义条件不满足需求，可以自定义：

```python
from mechanics.qte_system import QTECondition

def custom_condition():
    """自定义条件：当敌人生命值低于30%时触发"""
    def check(event: Event) -> bool:
        # 自定义逻辑
        target = event.get('target')
        if target and hasattr(target, 'hp'):
            return target.hp < target.max_hp * 0.3
        return False

    return QTECondition(
        name="low_hp",
        description="敌人生命值<30%",
        check=check,
        priority=10
    )

# 使用自定义条件
qte_skill = QTESkill(
    name="终结技",
    conditions=[custom_condition()],
    on_trigger=my_callback
)
```

---

## 🎮 事件系统

### 可监听的事件类型

QTE系统依赖于 `EventBus`，以下是可用的事件类型：

| 事件类型 | 说明 | 携带数据 |
|---------|------|---------|
| `BUFF_APPLIED` | Buff施加 | `buff_name`, `owner`, `stacks`, `tags` |
| `BUFF_EXPIRED` | Buff过期 | `buff_name`, `owner` |
| `REACTION_TRIGGERED` | 元素反应触发 | `reaction_type`, `target`, `attacker`, `level` |
| `SKILL_CAST` | 技能释放 | `character`, `action_name` |
| `ACTION_START` | 行动开始 | `character`, `action_name`, `duration` |
| `DAMAGE_DEALT` | 伤害造成 | `source`, `target`, `damage`, `element` |
| `CRIT_DEALT` | 造成暴击 | `source`, `target`, `damage` |

### 事件数据访问

```python
def on_trigger(event: Event):
    # 安全获取事件数据
    buff_name = event.get('buff_name', '未知')
    owner = event.get('owner')
    stacks = event.get('stacks', 0)

    # 检查事件类型
    if event.event_type == EventType.BUFF_APPLIED:
        # 处理buff施加事件
        pass
```

---

## ⚠️ 注意事项

### 1. 内存管理

QTE管理器会为每个条件订阅事件，必须在角色销毁时清理：

```python
def __del__(self):
    if hasattr(self, 'qte_manager'):
        self.qte_manager.cleanup()
```

### 2. CD更新

必须在角色的 `on_tick()` 中调用 QTE管理器的更新：

```python
def on_tick(self, engine):
    self.qte_manager.on_tick()
    super().on_tick(engine)
```

### 3. 事件发布增强

确保相关系统正确发布事件：

- ✅ `buff_system.py` - 已增强，发布 `BUFF_APPLIED` 事件包含 tags
- ✅ `reaction_manager.py` - 已增强，发布 `REACTION_TRIGGERED` 事件
- ✅ `base_actor.py` - 已集成，发布 `ACTION_START` 事件

### 4. 性能考虑

- 条件检查函数应尽量简单高效
- 避免在条件检查中执行复杂计算
- 合理设置CD，避免频繁触发

---

## 📦 文件结构

```
endfield_sim/
├── mechanics/
│   ├── qte_system.py           # QTE系统核心
│   ├── buff_system.py          # Buff系统（已增强事件）
│   └── reaction_manager.py     # 反应系统（已增强事件）
├── simulation/
│   └── event_system.py         # 事件总线
├── entities/characters/
│   └── *_sim.py                # 角色类（集成QTE）
└── examples_qte_usage.py       # 完整使用示例
```

---

## 🎓 进阶技巧

### 技巧1：多目标QTE

```python
# 为多个敌人设置QTE
for target in all_enemies:
    qte_manager.register_qte(QTESkill(
        name=f"追击-{target.name}",
        conditions=[
            QTEConditions.enemy_burning(target_name=target.name)
        ],
        on_trigger=lambda e, t=target: attack_target(t)
    ))
```

### 技巧2：条件优先级

```python
# 高优先级条件先检查
high_priority = QTECondition(
    name="critical_hp",
    check=lambda e: check_critical(),
    priority=100  # 高优先级
)

low_priority = QTECondition(
    name="normal_trigger",
    check=lambda e: check_normal(),
    priority=0  # 低优先级
)
```

### 技巧3：动态CD

```python
# 根据游戏状态动态调整CD
def dynamic_trigger_check():
    # 根据当前状态决定是否可以触发
    if character.energy >= 50:
        return True
    return False

qte_skill = QTESkill(
    name="能量爆发",
    conditions=[...],
    cooldown=30,
    can_trigger=dynamic_trigger_check  # 额外检查
)
```

---

## 🐛 常见问题

### Q1: QTE没有触发？

检查清单：
- ✅ 是否调用了 `qte_manager.on_tick()`
- ✅ 事件是否正确发布（检查日志）
- ✅ 条件检查函数是否返回 True
- ✅ CD是否冷却完毕
- ✅ `can_trigger` 是否返回 True

### Q2: 内存泄漏？

确保在角色销毁时调用 `qte_manager.cleanup()`

### Q3: QTE触发太频繁？

增加 `cooldown` 参数，或使用 `can_trigger` 添加额外限制

---

## 📞 支持

查看更多示例：`examples_qte_usage.py`
核心代码：`mechanics/qte_system.py`
事件系统：`simulation/event_system.py`

---

**Happy Coding! 🎮**
