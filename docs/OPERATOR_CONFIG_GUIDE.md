# 干员配置管理系统使用指南

## 功能概述

干员配置管理系统允许你在前端编队时自定义干员的等级和基础属性，实现更灵活的战斗模拟。

## 主要功能

### 1. 干员配置管理

在前端的"干员管理"页面，你可以：

- **创建配置**：为任意干员创建自定义配置
  - 设置等级（1-90）
  - 自定义四维属性（力量、敏捷、智识、意志）
  - 自定义基础面板（生命值、攻击力、防御力等）

- **编辑配置**：修改已有配置的属性值

- **删除配置**：删除不需要的配置

### 2. 编队时使用配置

在"编队与设置"页面：

1. 选择干员
2. 如果该干员有自定义配置，会显示"干员配置"下拉菜单
3. 选择配置（默认配置或自定义配置）
4. 运行模拟时会使用选中的配置

## 后端 API

### 获取所有配置
```
GET /operator-configs
GET /operator-configs?character_name=莱瓦汀
```

### 获取单个配置
```
GET /operator-configs/{config_id}
```

### 创建配置
```
POST /operator-configs
Content-Type: application/json

{
  "character_name": "莱瓦汀",
  "config_name": "高攻配置",
  "level": 90,
  "attrs": {
    "strength": 150,
    "agility": 100,
    "intelligence": 220,
    "willpower": 90
  },
  "base_stats": {
    "base_hp": 6000,
    "base_atk": 400,
    "base_def": 120
  }
}
```

### 更新配置
```
PUT /operator-configs/{config_id}
Content-Type: application/json

{
  "config_name": "超高攻配置",
  "level": 90,
  "attrs": {...},
  "base_stats": {...}
}
```

### 删除配置
```
DELETE /operator-configs/{config_id}
```

## 数据存储

配置数据存储在项目根目录的 `operator_configs.json` 文件中。

## 使用示例

### 创建一个高攻击力的莱瓦汀配置

1. 进入"干员管理"页面
2. 点击"新建配置"
3. 选择角色：莱瓦汀
4. 配置名称：高攻配置
5. 等级：90
6. 四维属性：
   - 力量：150
   - 敏捷：100
   - 智识：220
   - 意志：90
7. 基础面板：
   - 生命值：6000
   - 攻击力：400
   - 防御力：120
8. 点击"保存"

### 在编队中使用配置

1. 进入"编队与设置"页面
2. 选择莱瓦汀
3. 在"干员配置"下拉菜单中选择"高攻配置 (Lv.90)"
4. 运行模拟

## 技术实现

### 后端
- `core/operator_config.py`：配置管理器
- `api_server.py`：REST API 端点

### 前端
- `web/src/api/client.ts`：API 客户端
- `web/src/store/useSimulationStore.ts`：状态管理
- `web/src/components/OperatorManagement.tsx`：管理页面
- `web/src/components/CharacterCard.tsx`：配置选择

### 数据流
1. 前端从 `/operator-configs` 获取所有配置
2. 用户在编队时选择配置
3. 运行模拟时，将 `operator_config_id` 发送到后端
4. 后端在创建角色实例后，使用配置覆盖基础属性
5. 模拟使用自定义属性运行

## 注意事项

- 配置只影响基础属性，不影响技能逻辑
- 删除配置不会影响已保存的编队（会回退到默认配置）
- 配置文件是纯 JSON，可以手动编辑或备份
