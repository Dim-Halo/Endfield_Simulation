from collections import deque
from simulation.engine import SimEngine
from simulation.action import Action
from mechanics.buff_system import BuffManager
from simulation.event_system import EventType, EventBuilder

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

        self.main_attr = None # e.g. "intelligence"
        self.sub_attr = None  # e.g. "willpower"
    
    def get_current_panel(self):
        if not self.main_attr or not self.sub_attr:
            raise ValueError(f"{self.name} 未定义主/副属性！")
        
        # 1. 所有可能的属性字段 (Snapshot)
        stats = {
            # 基础与成长
            "level": self.base_stats.level,
            "technique_power": self.base_stats.technique_power,
            
            # 攻击力构成
            "base_atk": self.base_stats.base_atk + self.base_stats.weapon_atk,
            "atk_pct": self.base_stats.atk_pct,
            "flat_atk": self.base_stats.flat_atk,
            
            # 增伤与暴击
            "dmg_bonus": self.base_stats.dmg_bonus,
            "crit_rate": self.base_stats.crit_rate,
            "crit_dmg": self.base_stats.crit_dmg,
            "res_pen": self.base_stats.res_pen,
            "amplification": self.base_stats.amplification,
            
            # 特定增伤
            "normal_dmg_bonus": self.base_stats.normal_dmg_bonus,
            "skill_dmg_bonus": self.base_stats.skill_dmg_bonus,
            "ult_dmg_bonus": self.base_stats.ult_dmg_bonus,
            "qte_dmg_bonus": self.base_stats.qte_dmg_bonus,
            
            # 元素增伤
            "heat_dmg_bonus": self.base_stats.heat_dmg_bonus,
            "electric_dmg_bonus": self.base_stats.electric_dmg_bonus,
            "frost_dmg_bonus": self.base_stats.frost_dmg_bonus,
            "nature_dmg_bonus": self.base_stats.nature_dmg_bonus,
            "physical_dmg_bonus": self.base_stats.physical_dmg_bonus,
            
            # 其他
            "heal_bonus": self.base_stats.heal_bonus,
        }

        # 2. 钩子：允许子类在Buff计算前修改面板 (例如基于层数的被动)
        self._modify_panel_before_buffs(stats)

        # 3. 应用 Buff
        stats = self.buffs.apply_stats(stats)
        
        # 4. 计算 Final ATK
        base_zone = stats["base_atk"] * (1 + stats["atk_pct"]) + stats["flat_atk"]
        attr_mult = self.base_stats.get_attr_multiplier(self.attrs, self.main_attr, self.sub_attr)
        stats["final_atk"] = base_zone * attr_mult
        
        return stats
    
    def _modify_panel_before_buffs(self, stats):
        """子类可选重写"""
        pass

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
            # 发布行动结束事件
            event = EventBuilder.action_event(
                EventType.ACTION_END,
                character=self,
                action_name=act.name,
                duration=act.duration,
                tick=self.engine.tick
            )
            self.engine.event_bus.emit(event)

            self.is_busy = False
            self.current_action = None

    def start_action(self, action: Action):
        if self.is_busy: return False
        self.is_busy = True
        self.current_action = action
        self.action_timer = 0
        action.reset()
        self.engine.log(f"[{self.name}] 执行: {action.name}")

        # 发布行动开始事件
        event = EventBuilder.action_event(
            EventType.ACTION_START,
            character=self,
            action_name=action.name,
            duration=action.duration,
            tick=self.engine.tick
        )
        self.engine.event_bus.emit(event)

        # 记录技能使用
        self.engine.statistics.record_skill_usage(
            tick=self.engine.tick,
            character=self.name,
            skill_name=action.name,
            duration=action.duration
        )

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