# 武器系统使用指南

## 功能概述

武器系统允许你为干员配置武器，武器可以提供基础属性加成和特殊效果。

## 武器属性

每个武器包含以下属性：

1. **基础攻击力** (`weapon_atk`)：直接加到角色的武器攻击力
2. **属性加成** (`stat_bonuses`)：可以加成四维属性或面板属性
   - 四维属性：`intelligence`（智识）、`strength`（力量）、`agility`（敏捷）、`willpower`（意志）
   - 面板属性：`technique_power`（源石技艺强度）、`heat_dmg_bonus`（法术伤害）等
3. **特殊效果** (`effects`)：条件触发的 buff 效果

## 特殊效果系统

### 效果类型

- `on_reaction`：当触发特定元素反应时激活

### 效果结构

```python
{
    "effect_type": "on_reaction",
    "trigger_condition": {
        "reactions": ["BURNING", "CONDUCTIVE"]  # 触发条件：燃烧或导电
    },
    "buff_stats": {
        "heat_dmg_bonus": 0.336,      # 法术伤害+33.6%
        "technique_power": 70          # 源石技艺强度+70
    },
    "duration": 15.0,                  # 持续15秒
    "description": "效果描述"
}
```

## 默认武器：白夜新星

系统自带一个默认武器"白夜新星"：

- **基础攻击力**：567
- **智识**：+156
- **源石技艺强度**：+78
- **法术伤害**：+33.6%
- **特殊效果**：装备者对敌方施加燃烧或导电后，法术伤害+33.6%，源石技艺强度+70，持续15s

## 使用方法

### 在前端编队时选择武器

1. 进入"编队与设置"页面
2. 选择干员
3. 在"武器"下拉菜单中选择武器
4. 运行模拟

### 通过 API 管理武器

#### 获取所有武器
```
GET /weapons
```

#### 获取单个武器
```
GET /weapons/{weapon_id}
```

#### 创建武器
```
POST /weapons
Content-Type: application/json

{
  "name": "白夜新星",
  "description": "高级法杖，提供强大的法术增幅",
  "weapon_atk": 567,
  "stat_bonuses": {
    "intelligence": 156,
    "technique_power": 78,
    "heat_dmg_bonus": 0.336
  },
  "effects": [
    {
      "effect_type": "on_reaction",
      "trigger_condition": {
        "reactions": ["BURNING", "CONDUCTIVE"]
      },
      "buff_stats": {
        "heat_dmg_bonus": 0.336,
        "technique_power": 70
      },
      "duration": 15.0,
      "description": "对敌方施加燃烧或导电后法术伤害+33.6%，源石技艺强度+70，持续15s"
    }
  ]
}
```

#### 更新武器
```
PUT /weapons/{weapon_id}
Content-Type: application/json

{
  "name": "白夜新星+",
  "weapon_atk": 600
}
```

#### 删除武器
```
DELETE /weapons/{weapon_id}
```

## 技术实现

### 后端

1. **数据模型** (`core/weapon_system.py`)
   - `Weapon`：武器数据类
   - `WeaponEffect`：特殊效果数据类
   - `WeaponManager`：武器管理器

2. **特殊效果处理** (`core/weapon_effects.py`)
   - `WeaponEffectHandler`：监听事件并应用效果
   - 自动订阅 `REACTION_TRIGGERED` 事件
   - 根据触发条件应用 buff

3. **API 端点** (`api_server.py`)
   - 完整的 CRUD 接口
   - 在模拟时应用武器属性和效果

### 前端

1. **API 客户端** (`web/src/api/client.ts`)
   - `Weapon` 类型定义
   - `weaponApi` 对象封装所有 API 调用

2. **状态管理** (`web/src/store/useSimulationStore.ts`)
   - `weapons` 状态存储所有武器
   - `fetchWeapons` 方法加载武器数据
   - `CharacterConfig` 中添加 `weapon_id` 字段

3. **编队界面** (`web/src/components/CharacterCard.tsx`)
   - 武器选择下拉菜单
   - 显示武器名称和攻击力

## 数据流

1. 前端从 `/weapons` 获取所有武器
2. 用户在编队时选择武器
3. 运行模拟时，将 `weapon_id` 发送到后端
4. 后端在创建角色实例后：
   - 应用武器攻击力到 `base_stats.weapon_atk`
   - 应用属性加成到对应的属性
   - 创建 `WeaponEffectHandler` 监听事件
5. 战斗中触发反应时，`WeaponEffectHandler` 检查条件并应用 buff
6. Buff 通过 `BuffManager` 系统生效

## 属性加成说明

### 四维属性加成

武器的四维属性加成会直接加到角色的 `attrs` 上：

```python
# 白夜新星的智识+156
obj.attrs.intelligence += 156
```

### 面板属性加成

武器的面板属性加成会直接加到角色的 `base_stats` 上：

```python
# 白夜新星的源石技艺强度+78
obj.base_stats.technique_power += 78

# 法术伤害+33.6%
obj.base_stats.heat_dmg_bonus += 0.336
```

## 特殊效果工作原理

1. **事件监听**：`WeaponEffectHandler` 在角色创建时注册事件监听
2. **条件检查**：当 `REACTION_TRIGGERED` 事件触发时，检查：
   - 是否是该角色触发的反应
   - 反应类型是否匹配触发条件
3. **应用 Buff**：条件满足时，创建并应用 buff
4. **持续时间**：Buff 会在指定时间后自动过期

## 注意事项

- 武器数据存储在 `weapons.json` 文件中
- 首次启动时会自动创建默认武器"白夜新星"
- 武器效果通过事件系统实现，不会影响角色的基础逻辑
- 特殊效果的 buff 会显示在战斗日志中
- 删除武器不会影响已保存的编队（会回退到无武器状态）

## 扩展武器效果

要添加新的效果类型，需要：

1. 在 `WeaponEffectHandler` 中添加新的事件监听
2. 实现对应的触发逻辑
3. 在 `register_effects` 方法中注册新的效果类型

例如，添加"命中时触发"效果：

```python
def register_effects(self):
    for effect in self.weapon.effects:
        if effect.effect_type == "on_hit":
            self.engine.event_bus.subscribe(
                EventType.DAMAGE_DEALT,
                lambda event, eff=effect: self.on_hit(event, eff),
                priority=50
            )
```
