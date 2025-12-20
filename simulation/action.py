from dataclasses import dataclass
from typing import Callable, List

@dataclass
class DamageEvent:
    time_offset: int       # Tick
    damage_func: Callable  # 回调
    name: str = "Hit"

from core.enums import MoveType

class Action:
    def __init__(self, name: str, duration: int, events: List[DamageEvent] = None, move_type: MoveType = MoveType.OTHER):
        self.name = name
        self.duration = duration
        self.events = sorted(events or [], key=lambda x: x.time_offset)
        self.processed_event_index = 0
        self.move_type = move_type

    def reset(self):
        self.processed_event_index = 0

    def get_next_event(self):
        if self.processed_event_index < len(self.events):
            return self.events[self.processed_event_index]
        return None

    def advance_event(self):
        self.processed_event_index += 1