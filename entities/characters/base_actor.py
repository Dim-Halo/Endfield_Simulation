from collections import deque
from simulation.engine import SimEngine
from simulation.action import Action
from mechanics.buff_system import BuffManager

class BaseActor:
    def __init__(self, name, engine: SimEngine):
        self.name = name
        self.engine = engine
        self.buffs = BuffManager(self)
        
        self.current_action: Action = None
        self.action_timer = 0
        self.is_busy = False
        self.cooldowns = {} 
        self.action_queue = deque()
        self.is_script_finished = False

    def set_script(self, script_list):
        self.action_queue = deque(script_list)
        self.engine.log(f"[{self.name}] 脚本已装载，共 {len(script_list)} 个指令")

    def on_tick(self, engine):
        self.buffs.tick_all(engine)
        for skill in list(self.cooldowns.keys()):
            if self.cooldowns[skill] > 0:
                self.cooldowns[skill] -= 1

        if self.is_busy and self.current_action:
            self._process_action()
        else:
            self.process_next_command()

    def _process_action(self):
        self.action_timer += 1
        act = self.current_action
        while True:
            event = act.get_next_event()
            if event is None or event.time_offset > self.action_timer:
                break
            event.damage_func()
            act.advance_event()

        if self.action_timer >= act.duration:
            self.is_busy = False
            self.current_action = None

    def start_action(self, action: Action):
        if self.is_busy: return False
        self.is_busy = True
        self.current_action = action
        self.action_timer = 0
        action.reset()
        self.engine.log(f"[{self.name}] 执行: {action.name}")
        return True

    def process_next_command(self):
        if not self.action_queue:
            if not self.is_script_finished:
                self.engine.log(f"[{self.name}] 脚本执行完毕。")
                self.is_script_finished = True
            return
        cmd = self.action_queue[0]
        action = self.parse_command(cmd)
        if action:
            if self.start_action(action):
                self.action_queue.popleft()
        
    def parse_command(self, cmd_str):
        raise NotImplementedError