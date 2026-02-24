"""装备系统"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum


class EquipmentSlot(Enum):
    """装备槽位"""
    GLOVES = "gloves"      # 护手
    ARMOR = "armor"        # 护甲
    ACCESSORY_1 = "accessory_1"  # 配件1
    ACCESSORY_2 = "accessory_2"  # 配件2


@dataclass
class EquipmentEffect:
    """装备特殊效果"""
    effect_type: str  # "on_reaction", "on_skill_cast", "passive" etc.
    trigger_condition: Dict[str, Any]  # 触发条件
    buff_stats: Dict[str, float]  # 提供的属性加成
    duration: float  # 持续时间（秒）
    description: str  # 效果描述


@dataclass
class EquipmentSetBonus:
    """套装效果"""
    pieces_required: int  # 需要的装备件数（通常是3）
    stat_bonuses: Dict[str, float]  # 属性加成
    effects: List[EquipmentEffect] = field(default_factory=list)  # 特殊效果
    description: str = ""  # 效果描述

    def to_dict(self):
        data = asdict(self)
        return data


@dataclass
class EquipmentSet:
    """装备套装"""
    id: str
    name: str
    description: str
    bonuses: List[EquipmentSetBonus] = field(default_factory=list)  # 套装效果列表

    def to_dict(self):
        data = asdict(self)
        return data


@dataclass
class Equipment:
    """装备数据类"""
    id: str
    name: str
    description: str
    slot: str  # 装备槽位（gloves, armor, accessory_1, accessory_2）
    stat_bonuses: Dict[str, float]  # 属性加成
    effects: List[EquipmentEffect] = field(default_factory=list)  # 特殊效果
    set_id: Optional[str] = None  # 套装ID（如果是套装装备）
    set_name: Optional[str] = None  # 套装名称（如果是套装装备）

    def to_dict(self):
        data = asdict(self)
        return data


class EquipmentManager:
    """装备管理器"""

    def __init__(self, equipment_dir: str = "equipment"):
        self.equipment_dir = Path(equipment_dir)
        self.equipments: Dict[str, Equipment] = {}
        self.load()

    def load(self):
        """从文件夹加载装备"""
        if not self.equipment_dir.exists():
            return

        # 加载独立装备
        standalone_dir = self.equipment_dir / "standalone"
        if standalone_dir.exists():
            for file_path in standalone_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 支持单个装备或装备列表
                        if isinstance(data, list):
                            for item in data:
                                self._load_equipment_item(item)
                        else:
                            self._load_equipment_item(data)
                except Exception as e:
                    print(f"加载独立装备文件 {file_path} 失败: {e}")

        # 加载套装装备
        set_pieces_dir = self.equipment_dir / "set_pieces"
        if set_pieces_dir.exists():
            for set_dir in set_pieces_dir.iterdir():
                if set_dir.is_dir():
                    for file_path in set_dir.glob("*.json"):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                # 支持单个装备或装备列表
                                if isinstance(data, list):
                                    for item in data:
                                        self._load_equipment_item(item)
                                else:
                                    self._load_equipment_item(data)
                        except Exception as e:
                            print(f"加载套装装备文件 {file_path} 失败: {e}")

    def _load_equipment_item(self, item: Dict):
        """加载单个装备项"""
        # 重建 EquipmentEffect 对象
        effects = []
        for eff_data in item.get('effects', []):
            effects.append(EquipmentEffect(**eff_data))
        item['effects'] = effects
        equipment = Equipment(**item)
        self.equipments[equipment.id] = equipment

    def save(self):
        """保存装备到文件夹"""
        # 确保目录存在
        standalone_dir = self.equipment_dir / "standalone"
        set_pieces_dir = self.equipment_dir / "set_pieces"
        standalone_dir.mkdir(parents=True, exist_ok=True)
        set_pieces_dir.mkdir(parents=True, exist_ok=True)

        # 按槽位分组独立装备
        standalone_by_slot = {}
        # 按套装分组套装装备
        set_pieces_by_set = {}

        for equipment in self.equipments.values():
            if equipment.set_id:
                # 套装装备
                if equipment.set_id not in set_pieces_by_set:
                    set_pieces_by_set[equipment.set_id] = {}
                if equipment.slot not in set_pieces_by_set[equipment.set_id]:
                    set_pieces_by_set[equipment.set_id][equipment.slot] = []
                set_pieces_by_set[equipment.set_id][equipment.slot].append(equipment)
            else:
                # 独立装备
                if equipment.slot not in standalone_by_slot:
                    standalone_by_slot[equipment.slot] = []
                standalone_by_slot[equipment.slot].append(equipment)

        # 保存独立装备（按槽位）
        for slot, equipments in standalone_by_slot.items():
            file_path = standalone_dir / f"{slot}.json"
            data = [eq.to_dict() for eq in equipments]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        # 保存套装装备（按套装和槽位）
        for set_id, slots in set_pieces_by_set.items():
            # 使用套装名称作为文件夹名（如果有的话）
            set_name = None
            for slot_equipments in slots.values():
                if slot_equipments:
                    set_name = slot_equipments[0].set_name
                    break

            if set_name:
                # 清理文件夹名称（移除特殊字符）
                safe_set_name = set_name.replace('/', '_').replace('\\', '_')
                set_dir = set_pieces_dir / safe_set_name
            else:
                set_dir = set_pieces_dir / set_id

            set_dir.mkdir(parents=True, exist_ok=True)

            for slot, equipments in slots.items():
                file_path = set_dir / f"{slot}.json"
                data = [eq.to_dict() for eq in equipments]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def create(self, name: str, description: str, slot: str,
               stat_bonuses: Dict[str, float], effects: List[Dict[str, Any]] = None,
               set_id: str = None, set_name: str = None) -> Equipment:
        """创建新装备"""
        equipment_effects = []
        if effects:
            for eff in effects:
                equipment_effects.append(EquipmentEffect(**eff))

        equipment = Equipment(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            slot=slot,
            stat_bonuses=stat_bonuses,
            effects=equipment_effects,
            set_id=set_id,
            set_name=set_name
        )
        self.equipments[equipment.id] = equipment
        self.save()
        return equipment

    def get(self, equipment_id: str) -> Optional[Equipment]:
        """获取装备"""
        return self.equipments.get(equipment_id)

    def get_all(self) -> List[Equipment]:
        """获取所有装备"""
        return list(self.equipments.values())

    def get_by_slot(self, slot: str) -> List[Equipment]:
        """获取指定槽位的所有装备"""
        return [eq for eq in self.equipments.values() if eq.slot == slot]

    def update(self, equipment_id: str, name: Optional[str] = None,
               description: Optional[str] = None, slot: Optional[str] = None,
               stat_bonuses: Optional[Dict[str, float]] = None,
               effects: Optional[List[Dict[str, Any]]] = None) -> Optional[Equipment]:
        """更新装备"""
        equipment = self.equipments.get(equipment_id)
        if not equipment:
            return None

        if name is not None:
            equipment.name = name
        if description is not None:
            equipment.description = description
        if slot is not None:
            equipment.slot = slot
        if stat_bonuses is not None:
            equipment.stat_bonuses = stat_bonuses
        if effects is not None:
            equipment.effects = [EquipmentEffect(**eff) for eff in effects]

        self.save()
        return equipment

    def delete(self, equipment_id: str) -> bool:
        """删除装备"""
        if equipment_id in self.equipments:
            del self.equipments[equipment_id]
            self.save()
            return True
        return False

    def create_default_equipments(self):
        """创建默认装备库（已禁用，装备需手动创建）"""
        print("默认装备创建已禁用，请手动创建装备")


class EquipmentSetManager:
    """套装管理器"""

    def __init__(self, equipment_dir: str = "equipment"):
        self.equipment_dir = Path(equipment_dir)
        self.sets_dir = self.equipment_dir / "sets"
        self.sets: Dict[str, EquipmentSet] = {}
        self.load()

    def load(self):
        """从文件夹加载套装"""
        if not self.sets_dir.exists():
            return

        for file_path in self.sets_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 重建 EquipmentSetBonus 对象
                    bonuses = []
                    for bonus_data in data.get('bonuses', []):
                        # 重建 EquipmentEffect 对象
                        effects = []
                        for eff_data in bonus_data.get('effects', []):
                            effects.append(EquipmentEffect(**eff_data))
                        bonus_data['effects'] = effects
                        bonuses.append(EquipmentSetBonus(**bonus_data))
                    data['bonuses'] = bonuses
                    equipment_set = EquipmentSet(**data)
                    self.sets[equipment_set.id] = equipment_set
            except Exception as e:
                print(f"加载套装文件 {file_path} 失败: {e}")

    def save(self):
        """保存套装到文件夹"""
        # 确保目录存在
        self.sets_dir.mkdir(parents=True, exist_ok=True)

        for equipment_set in self.sets.values():
            # 使用套装名称作为文件名（清理特殊字符）
            safe_name = equipment_set.name.replace('/', '_').replace('\\', '_').replace(' ', '_')
            file_path = self.sets_dir / f"{safe_name}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(equipment_set.to_dict(), f, ensure_ascii=False, indent=2)

    def create(self, name: str, description: str, bonuses: List[Dict[str, Any]]) -> EquipmentSet:
        """创建新套装"""
        set_bonuses = []
        for bonus_data in bonuses:
            effects = []
            if 'effects' in bonus_data:
                for eff in bonus_data['effects']:
                    effects.append(EquipmentEffect(**eff))
            bonus_data['effects'] = effects
            set_bonuses.append(EquipmentSetBonus(**bonus_data))

        equipment_set = EquipmentSet(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            bonuses=set_bonuses
        )
        self.sets[equipment_set.id] = equipment_set
        self.save()
        return equipment_set

    def get(self, set_id: str) -> Optional[EquipmentSet]:
        """获取套装"""
        return self.sets.get(set_id)

    def get_all(self) -> List[EquipmentSet]:
        """获取所有套装"""
        return list(self.sets.values())

    def delete(self, set_id: str) -> bool:
        """删除套装"""
        if set_id in self.sets:
            del self.sets[set_id]
            self.save()
            return True
        return False

    def check_set_bonuses(self, equipped_items: List[Equipment]) -> Dict[str, List[EquipmentSetBonus]]:
        """
        检查装备列表中的套装效果
        返回：{set_id: [激活的套装效果列表]}
        """
        # 统计每个套装的装备数量
        set_counts = {}
        for item in equipped_items:
            if item.set_id:
                set_counts[item.set_id] = set_counts.get(item.set_id, 0) + 1

        # 检查哪些套装效果被激活
        active_bonuses = {}
        for set_id, count in set_counts.items():
            equipment_set = self.get(set_id)
            if equipment_set:
                activated = []
                for bonus in equipment_set.bonuses:
                    if count >= bonus.pieces_required:
                        activated.append(bonus)
                if activated:
                    active_bonuses[set_id] = activated

        return active_bonuses

    def create_default_sets(self):
        """创建默认套装（已禁用，套装需手动创建）"""
        print("默认套装创建已禁用，请手动创建套装")
        return {}

