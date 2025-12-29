"""干员配置管理系统"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class OperatorConfig:
    """干员配置数据类"""
    id: str
    character_name: str
    config_name: str
    level: int
    attrs: Dict[str, int]  # strength, agility, intelligence, willpower
    base_stats: Dict[str, float]  # base_hp, base_atk, etc.

    def to_dict(self):
        return asdict(self)


class OperatorConfigManager:
    """干员配置管理器"""

    def __init__(self, config_file: str = "operator_configs.json"):
        self.config_file = Path(config_file)
        self.configs: Dict[str, OperatorConfig] = {}
        self.load()

    def load(self):
        """从文件加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    config = OperatorConfig(**item)
                    self.configs[config.id] = config

    def save(self):
        """保存配置到文件"""
        data = [config.to_dict() for config in self.configs.values()]
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def create(self, character_name: str, config_name: str, level: int,
               attrs: Dict[str, int], base_stats: Dict[str, float]) -> OperatorConfig:
        """创建新配置"""
        config = OperatorConfig(
            id=str(uuid.uuid4()),
            character_name=character_name,
            config_name=config_name,
            level=level,
            attrs=attrs,
            base_stats=base_stats
        )
        self.configs[config.id] = config
        self.save()
        return config

    def get(self, config_id: str) -> Optional[OperatorConfig]:
        """获取配置"""
        return self.configs.get(config_id)

    def get_all(self) -> List[OperatorConfig]:
        """获取所有配置"""
        return list(self.configs.values())

    def get_by_character(self, character_name: str) -> List[OperatorConfig]:
        """获取指定角色的所有配置"""
        return [c for c in self.configs.values() if c.character_name == character_name]

    def update(self, config_id: str, config_name: Optional[str] = None,
               level: Optional[int] = None, attrs: Optional[Dict[str, int]] = None,
               base_stats: Optional[Dict[str, float]] = None) -> Optional[OperatorConfig]:
        """更新配置"""
        config = self.configs.get(config_id)
        if not config:
            return None

        if config_name is not None:
            config.config_name = config_name
        if level is not None:
            config.level = level
        if attrs is not None:
            config.attrs = attrs
        if base_stats is not None:
            config.base_stats = base_stats

        self.save()
        return config

    def delete(self, config_id: str) -> bool:
        """删除配置"""
        if config_id in self.configs:
            del self.configs[config_id]
            self.save()
            return True
        return False
