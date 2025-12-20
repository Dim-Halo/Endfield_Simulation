import logging
import sys
from simulation.party_manager import PartyManager
from typing import List
from core.statistics import CombatStatistics
from core.config_manager import ConfigManager
from simulation.event_system import EventBus, Event, EventType

# 避免重复配置
_LOGGING_CONFIGURED = False

class SimEngine:
    def __init__(self):
        self.tick = 0        # 1 tick = 0.1s
        self.entities = []
        
        # 集成新系统
        self.config = ConfigManager.get_instance()
        self.statistics = CombatStatistics()
        self.event_bus = EventBus()
        self.party_manager = PartyManager()
        
        # 配置日志
        self._setup_logging()

    def _setup_logging(self):
        global _LOGGING_CONFIGURED
        self.logger = logging.getLogger("SimEngine")
        
        # 如果已经配置过（比如在多次运行模拟时），只更新级别
        if not _LOGGING_CONFIGURED:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(message)s') # 保持原有的简洁输出格式，因为我们自己在 log 方法里加了时间戳
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            _LOGGING_CONFIGURED = True
        
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR
        }
        log_level = level_map.get(self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

    def log(self, message: str, level: str = "INFO"):
        """
        统一日志接口
        Args:
            message: 日志内容
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        """
        seconds = self.tick / 10.0
        timestamp = f"[{int(seconds // 60):02}:{seconds % 60:04.1f}]"
        formatted_msg = f"{timestamp} {message}"
        
        if level == "DEBUG":
            self.logger.debug(formatted_msg)
        elif level == "WARNING":
            self.logger.warning(formatted_msg)
        elif level == "ERROR":
            self.logger.error(formatted_msg)
        else:
            self.logger.info(formatted_msg)

    def run(self, max_seconds=30):
        max_ticks = int(max_seconds * 10)
        self.log(f"=== 模拟开始 (时长: {max_seconds}s) ===")

        # 发布战斗开始事件
        self.event_bus.emit_simple(EventType.COMBAT_START, tick=self.tick)

        for _ in range(max_ticks):
            self.tick += 1
            self.statistics.update_combat_duration(self.tick)

            # 发布Tick开始事件
            self.event_bus.emit_simple(EventType.TICK_START, tick=self.tick)

            # 更新队伍资源
            self.party_manager.update(0.1)

            # 处理所有实体
            for entity in self.entities:
                try:
                    entity.on_tick(self)
                except Exception as e:
                    self.log(f"错误: {entity.name} 处理tick时出错: {e}", level="ERROR")
                    import traceback
                    traceback.print_exc()

            # 发布Tick结束事件
            self.event_bus.emit_simple(EventType.TICK_END, tick=self.tick)

        # 发布战斗结束事件
        self.event_bus.emit_simple(EventType.COMBAT_END, tick=self.tick)
        self.log("=== 模拟结束 ===")