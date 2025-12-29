"""武器系统"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field


@dataclass
class WeaponEffect:
    """武器特殊效果"""
    effect_type: str  # "on_reaction", "on_hit", "passive" etc.
    trigger_condition: Dict[str, Any]  # 触发条件
    buff_stats: Dict[str, float]  # 提供的属性加成
    duration: float  # 持续时间（秒）
    description: str  # 效果描述


@dataclass
class Weapon:
    """武器数据类"""
    id: str
    name: str
    description: str
    weapon_atk: float  # 武器攻击力
    stat_bonuses: Dict[str, float]  # 属性加成（如 intelligence, technique_power, heat_dmg_bonus）
    effects: List[WeaponEffect] = field(default_factory=list)  # 特殊效果

    def to_dict(self):
        data = asdict(self)
        return data


class WeaponManager:
    """武器管理器"""

    def __init__(self, weapon_file: str = "weapons.json"):
        self.weapon_file = Path(weapon_file)
        self.weapons: Dict[str, Weapon] = {}
        self.load()

    def load(self):
        """从文件加载武器"""
        if self.weapon_file.exists():
            with open(self.weapon_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    # 重建 WeaponEffect 对象
                    effects = []
                    for eff_data in item.get('effects', []):
                        effects.append(WeaponEffect(**eff_data))
                    item['effects'] = effects
                    weapon = Weapon(**item)
                    self.weapons[weapon.id] = weapon

    def save(self):
        """保存武器到文件"""
        data = [weapon.to_dict() for weapon in self.weapons.values()]
        with open(self.weapon_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create(self, name: str, description: str, weapon_atk: float,
               stat_bonuses: Dict[str, float], effects: List[Dict[str, Any]] = None) -> Weapon:
        """创建新武器"""
        weapon_effects = []
        if effects:
            for eff in effects:
                weapon_effects.append(WeaponEffect(**eff))

        weapon = Weapon(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            weapon_atk=weapon_atk,
            stat_bonuses=stat_bonuses,
            effects=weapon_effects
        )
        self.weapons[weapon.id] = weapon
        self.save()
        return weapon

    def get(self, weapon_id: str) -> Optional[Weapon]:
        """获取武器"""
        return self.weapons.get(weapon_id)

    def get_all(self) -> List[Weapon]:
        """获取所有武器"""
        return list(self.weapons.values())

    def update(self, weapon_id: str, name: Optional[str] = None,
               description: Optional[str] = None, weapon_atk: Optional[float] = None,
               stat_bonuses: Optional[Dict[str, float]] = None,
               effects: Optional[List[Dict[str, Any]]] = None) -> Optional[Weapon]:
        """更新武器"""
        weapon = self.weapons.get(weapon_id)
        if not weapon:
            return None

        if name is not None:
            weapon.name = name
        if description is not None:
            weapon.description = description
        if weapon_atk is not None:
            weapon.weapon_atk = weapon_atk
        if stat_bonuses is not None:
            weapon.stat_bonuses = stat_bonuses
        if effects is not None:
            weapon.effects = [WeaponEffect(**eff) for eff in effects]

        self.save()
        return weapon

    def delete(self, weapon_id: str) -> bool:
        """删除武器"""
        if weapon_id in self.weapons:
            del self.weapons[weapon_id]
            self.save()
            return True
        return False

    def create_default_weapons(self):
        """创建默认武器库"""
        # 白夜新星
        self.create(
            name="白夜新星",
            description="高级法杖，提供强大的法术增幅",
            weapon_atk=567,
            stat_bonuses={
                "intelligence": 156,
                "technique_power": 78,
                "heat_dmg_bonus": 0.336,
                "electric_dmg_bonus": 0.336
            },
            effects=[{
                "effect_type": "on_reaction",
                "trigger_condition": {
                    "reactions": ["BURNING", "CONDUCTIVE"]
                },
                "buff_stats": {
                    "heat_dmg_bonus": 0.336,
                    "electric_dmg_bonus": 0.336,
                    "technique_power": 70
                },
                "duration": 15.0,
                "description": "对敌方施加燃烧或导电后法术伤害+33.6%，源石技艺强度+70，持续15s"
            }]
        )
        print("默认武器已创建")
