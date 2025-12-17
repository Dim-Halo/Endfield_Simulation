from core.statistics import CombatStatistics
from core.config_manager import ConfigManager
from simulation.event_system import EventBus, Event, EventType


class SimEngine:
    def __init__(self):
        self.tick = 0        # 1 tick = 0.1s
        self.entities = []

        # 集成新系统
        self.config = ConfigManager.get_instance()
        self.statistics = CombatStatistics()
        self.event_bus = EventBus()

    def log(self, message):
        seconds = self.tick / 10.0
        timestamp = f"[{int(seconds // 60):02}:{seconds % 60:04.1f}]"
        print(f"{timestamp} {message}")

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

            # 处理所有实体
            for entity in self.entities:
                try:
                    entity.on_tick(self)
                except Exception as e:
                    self.log(f"错误: {entity.name} 处理tick时出错: {e}")
                    import traceback
                    traceback.print_exc()

            # 发布Tick结束事件
            self.event_bus.emit_simple(EventType.TICK_END, tick=self.tick)

        # 发布战斗结束事件
        self.event_bus.emit_simple(EventType.COMBAT_END, tick=self.tick)
        self.log("=== 模拟结束 ===")