# 角色Constants API使用说明

## 概述

前端已经集成了角色constants API，**不再需要在前端硬编码角色数据**。所有角色的帧数据、技能倍率等信息都从后端的`entities/characters/*_constants.py`文件动态获取。

## 架构

```
后端: entities/characters/levatine_constants.py (FRAME_DATA)
  ↓
API: GET /characters/莱瓦汀/constants
  ↓
前端: web/src/utils/constants.ts (缓存 + 获取)
  ↓
组件: TimelineEditor.tsx (使用)
```

## 前端使用方式

### 自动预加载

应用启动时会自动预加载所有角色的constants：

```typescript
// 在 useSimulationStore.ts 中
fetchAvailableCharacters: async () => {
  const res = await apiClient.get('/characters');
  const characters = res.data.characters || [];

  // 自动预加载所有角色的constants
  preloadCharacterConstants(characters);
}
```

### 获取动作时长

```typescript
import { getActionDuration } from '../utils/constants';

// 异步获取动作时长
const duration = await getActionDuration('莱瓦汀', 'Skill');
// 返回: 1.5 (秒)
```

### 直接获取角色Constants

```typescript
import { fetchCharacterConstants } from '../utils/constants';

const constants = await fetchCharacterConstants('莱瓦汀');
// 返回完整的constants对象，包含frame_data, skill_multipliers, mechanics
```

```json
{
  "character_name": "莱瓦汀",
  "frame_data": {
    "normal": [
      {"total": 6, "hit": 4},
      {"total": 5, "hit": 3},
      {"total": 7, "hit": 4},
      {"total": 9, "hit": 5},
      {"total": 12, "hit": 8}
    ],
    "enhanced_normal": [
      {"total": 7, "hit": 4},
      {"total": 6, "hit": 3},
      {"total": 8, "hit": 5},
      {"total": 13, "hit": 9}
    ],
    "skill": {
      "total": 15,
      "hit_init": 5,
      "hit_burst": 10
    },
    "ult": {
      "total": 20,
      "hit": 10
    },
    "qte": {
      "total": 12,
      "hit": 5
    }
  },
  "skill_multipliers": {
    "normal": [36, 54, 56, 88, 119],
    "enhanced_normal": [162, 203, 289, 506],
    "skill_initial": 140,
    "skill_burst": 770,
    "skill_dot": 14,
    "qte": 540
  },
  "mechanics": {
    "molten_max_stacks": 4,
    "heat_res_shred": 20,
    "qte_energy_gain": [0, 25, 30, 35]
  }
}
```

## 前端使用示例

### React/TypeScript示例

```typescript
// 获取角色的帧数据
async function getCharacterFrameData(characterName: string) {
  const response = await fetch(
    `http://localhost:8000/characters/${encodeURIComponent(characterName)}/constants`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch constants for ${characterName}`);
  }

  const data = await response.json();
  return data;
}

// 使用示例：在创建事件时自动设置时间块长度
async function createEventWithFrameData(characterName: string, actionType: string) {
  const constants = await getCharacterFrameData(characterName);
  const frameData = constants.frame_data;

  // 根据动作类型获取帧长度
  let duration = 0;

  if (actionType === 'skill' && frameData.skill) {
    duration = frameData.skill.total * 0.1; // 转换为秒（1帧 = 0.1秒）
  } else if (actionType === 'ult' && frameData.ult) {
    duration = frameData.ult.total * 0.1;
  } else if (actionType === 'qte' && frameData.qte) {
    duration = frameData.qte.total * 0.1;
  } else if (actionType.startsWith('a') && frameData.normal) {
    // 普攻序列，例如 'a1', 'a2', etc.
    const index = parseInt(actionType.substring(1)) - 1;
    if (index >= 0 && index < frameData.normal.length) {
      duration = frameData.normal[index].total * 0.1;
    }
  }

  return {
    name: actionType,
    duration: duration,
    startTime: 0 // 由用户或自动计算设置
  };
}

// 快捷键创建事件示例
function handleKeyboardShortcut(key: string, characterName: string, currentTime: number) {
  let actionType = '';

  switch(key) {
    case 'e':
      actionType = 'skill';
      break;
    case 'q':
      actionType = 'ult';
      break;
    case 'r':
      actionType = 'qte';
      break;
    case '1':
    case '2':
    case '3':
    case '4':
    case '5':
      actionType = `a${key}`;
      break;
    default:
      return;
  }

  createEventWithFrameData(characterName, actionType).then(event => {
    event.startTime = currentTime;
    // 将事件添加到时间轴
    addEventToTimeline(event);
  });
}
```

## 帧数据说明

### 字段含义

- `total`: 动作总帧数（1帧 = 0.1秒）
- `hit`: 伤害判定帧（从动作开始计算）
- `hit_init`: 初始命中帧（用于多段技能）
- `hit_burst`: 爆发命中帧（用于多段技能）

### 时间转换

```typescript
// 帧数转秒
const seconds = frames * 0.1;

// 秒转帧数
const frames = Math.round(seconds * 10);
```

## 注意事项

1. **URL编码**: 角色名称包含中文字符，需要使用`encodeURIComponent()`进行URL编码
2. **错误处理**: 如果角色没有对应的constants模块，API会返回空的frame_data对象
3. **缓存**: 建议在前端缓存constants数据，避免重复请求
4. **帧率**: 游戏使用固定帧率，1帧 = 0.1秒 = 100毫秒

## 完整的前端集成示例

```typescript
// CharacterConstantsCache.ts
class CharacterConstantsCache {
  private cache: Map<string, any> = new Map();

  async get(characterName: string) {
    if (this.cache.has(characterName)) {
      return this.cache.get(characterName);
    }

    const response = await fetch(
      `http://localhost:8000/characters/${encodeURIComponent(characterName)}/constants`
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch constants for ${characterName}`);
    }

    const data = await response.json();
    this.cache.set(characterName, data);
    return data;
  }

  clear() {
    this.cache.clear();
  }
}

export const constantsCache = new CharacterConstantsCache();

// TimelineEditor.tsx
import { constantsCache } from './CharacterConstantsCache';

function TimelineEditor({ characterName }: { characterName: string }) {
  const [constants, setConstants] = useState<any>(null);

  useEffect(() => {
    constantsCache.get(characterName).then(setConstants);
  }, [characterName]);

  const handleCreateEvent = async (actionType: string, startTime: number) => {
    if (!constants) return;

    const frameData = constants.frame_data;
    let duration = 0;

    // 根据actionType获取duration
    if (actionType === 'skill' && frameData.skill) {
      duration = frameData.skill.total * 0.1;
    }
    // ... 其他动作类型

    const event = {
      name: actionType,
      startTime: startTime,
      duration: duration
    };

    // 添加到时间轴
    addEvent(event);
  };

  return (
    <div>
      {/* 时间轴UI */}
    </div>
  );
}
```
