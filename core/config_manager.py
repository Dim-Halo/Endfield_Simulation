"""
统一配置管理系统
集中管理所有游戏数值配置，支持热更新和版本管理
"""
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """单例配置管理器"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 伤害公式相关
        self.damage_formula_const = 100  # 防御公式常数

        # Tick系统配置
        self.tick_rate = 10  # 每秒tick数 (1 tick = 0.1s)

        # 元素反应基础配置
        self.reaction_base_mv = {
            "burst": 160,        # 法术爆发
            "reaction": 80,      # 异色反应
            "burning_dot": 12,   # 燃烧DOT倍率
            "frozen": 130,       # 冻结倍率
            "shatter": 120,      # 碎冰倍率
            "impact": 150,       # 猛击倍率
            "break": 50,         # 碎甲倍率
        }

        # 反应持续时间 (秒)
        self.reaction_duration = {
            "burning": 10.0,
            "conductive": 12.0,
            "frozen": 6.0,
            "corrosion": 15.0,
            "shatter_armor": 12.0,
        }

        # 反应基础系数
        self.reaction_coefficients = {
            "conductive_base_vuln": 0.08,     # 导电基础易伤 (0.08 + 0.04*1 = 0.12)
            "conductive_per_level": 0.04,     # 导电每层增加
            "corrosion_base_shred": 0.024,    # 腐蚀基础削抗 (0.024 + 0.012*1 = 0.036)
            "corrosion_per_level": 0.012,     # 腐蚀每层增加
            "corrosion_tick_base": 0.0056,    # 腐蚀每秒削抗基础 (0.0056 + 0.0028*1 = 0.0084)
            "corrosion_tick_level": 0.0028,   # 腐蚀每秒削抗每层
            "corrosion_max_base": 0.08,       # 腐蚀最大削抗基础 (0.08 + 0.04*1 = 0.12)
            "corrosion_max_level": 0.04,      # 腐蚀最大削抗每层
            "shatter_armor_base": 0.08,       # 碎甲基础易伤
            "shatter_armor_per_level": 0.03,  # 碎甲每层增加
            "frozen_base_duration": 6.0,      # 冻结基础时长
            "frozen_per_level": 1.0,          # 冻结每层增加
        }

        # 源石技艺增强公式参数
        self.tech_power_coefficient = 300.0  # Tech增强分母常数
        self.tech_power_multiplier = 2.0     # Tech增强系数

        # 暴击相关
        self.crit_rate_cap = 1.0   # 暴击率上限
        self.crit_rate_floor = 0.0 # 暴击率下限

        # 元素附着系统
        self.max_attachment_stacks = 4  # 最大附着层数
        self.max_phys_break_stacks = 4  # 最大物理破防层数

        # 失衡系统
        self.stagger_vuln_multiplier = 1.3  # 失衡易伤倍率

        # DOT系统
        self.default_dot_interval = 1.0  # 默认DOT跳伤间隔(秒)

        # 日志配置
        self.log_level = "INFO"  # DEBUG, INFO, WARNING, ERROR
        self.enable_damage_log = True
        self.enable_buff_log = True
        self.enable_reaction_log = True

        # 性能配置
        self.enable_statistics = True   # 启用统计系统
        self.enable_event_system = True  # 启用事件系统
        self.enable_detailed_logging = False  # 启用详细日志

        self._initialized = True

    def load_from_dict(self, config_dict: Dict[str, Any]):
        """从字典加载配置"""
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def load_from_json(self, file_path: str):
        """从JSON文件加载配置"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        with open(path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
            self.load_from_dict(config_dict)

    def load_from_yaml(self, file_path: str):
        """从YAML文件加载配置"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
                self.load_from_dict(config_dict)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")

    def save_to_json(self, file_path: str):
        """保存配置到JSON文件"""
        config_dict = self.to_dict()
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        exclude_keys = {'_instance', '_initialized'}
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith('_') and key not in exclude_keys
        }

    def get_reaction_mv(self, reaction_type: str, level: int = 0,
                       tech_power: float = 0.0, attacker_lvl: int = 90,
                       is_magic: bool = True) -> float:
        """
        计算反应倍率（封装通用计算逻辑）

        Args:
            reaction_type: 反应类型 ("burst", "reaction", "burning_dot" 等)
            level: 反应等级 (附着层数)
            tech_power: 源石技艺
            attacker_lvl: 攻击者等级
            is_magic: 是否为法术伤害/异常
        """
        base_mv = self.reaction_base_mv.get(reaction_type, 0)
        level_mult = base_mv * (1.0 + level)

        # Tech增强
        tech_mult = 1.0 + (tech_power / 100.0)

        # 等级系数区（物理异常和法术异常有不同的系数）
        if is_magic:
            # 法术等级系数 = 1 + (触发者等级 - 1) / 196
            # 适用于：法术异常和法术爆发伤害
            level_coeff = 1.0 + (max(1, attacker_lvl) - 1) / 196.0
        else:
            # 物理等级系数 = 1 + (触发者等级 - 1) / 392
            # 适用于：物理异常伤害
            level_coeff = 1.0 + (max(1, attacker_lvl) - 1) / 392.0

        return level_mult * tech_mult * level_coeff

    def get_tech_enhancement(self, tech_power: float) -> float:
        """
        计算源石技艺增强系数
        增强系数 = 1 + (multiplier * Tech / (Tech + coefficient))
        """
        return 1.0 + (self.tech_power_multiplier * tech_power /
                     (tech_power + self.tech_power_coefficient))

    def reset_to_defaults(self):
        """重置为默认配置"""
        self._initialized = False
        self.__init__()

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """获取单例实例"""
        return cls()


# 提供全局访问点
def get_config() -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager.get_instance()
