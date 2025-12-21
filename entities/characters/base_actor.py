from collections import deque
from dataclasses import asdict
from simulation.engine import SimEngine
from simulation.action import Action
from mechanics.buff_system import BuffManager
from simulation.event_system import EventType, EventBuilder
from core.enums import MoveType
from core.stats import CombatStats, Attributes, StatKey

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

        # QTE 就绪计时器 (通用机制)
        self.qte_ready_timer = 0
    
    def get_current_panel(self):
        """
        获取当前面板属性（计算 Buff 后的快照）
        """
        # 1. 基础属性
        panel = asdict(self.base_stats)
        
        # 计算主副属性带来的攻击力/生命加成（如果有相关机制）
        # 这里暂时只处理属性乘区
        
        # 2. 预处理 Hook (子类可覆盖)
        self._modify_panel_before_buffs(panel)

        # 3. 应用自身 Buff
        self.buffs.apply_stats(panel)

        # 4. 计算最终攻击力 (Final Atk)
        # 公式: (基础攻击 + 武器攻击 + 固定攻击) * (1 + 攻击百分比)
        base = panel[StatKey.BASE_ATK] + panel[StatKey.WEAPON_ATK] + panel[StatKey.FLAT_ATK]
        atk_mult = 1.0 + panel[StatKey.ATK_PCT]
        panel[StatKey.FINAL_ATK] = base * atk_mult

        # 5. 计算源石技艺强度 (如果有)
        # 公式: (基础攻击 * 技艺倍率) * (1 + 技艺百分比) 
        # (简化公式，具体视设定而定)
        # panel['technique_power'] += panel['final_atk'] * panel['tech_pct']
        
        return panel
    
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
        
        # QTE 计时器递减
        if self.qte_ready_timer > 0:
            self.qte_ready_timer -= 1

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
        
        # 检查并消耗技力
        if action.move_type == MoveType.SKILL:
            if not self.engine.party_manager.try_consume_sp(100):
                self.engine.log(f"[{self.name}] 技力不足 ({self.engine.party_manager.get_sp()}/100), 无法释放战技: {action.name}", level="WARNING")
                return False
            else:
                self.engine.log(f"[{self.name}] 消耗100技力, 剩余: {self.engine.party_manager.get_sp()}")

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
        """通用指令解析器"""
        parts = cmd_str.split()
        cmd = parts[0].lower()
        
        # 1. 等待指令
        if cmd == "wait":
            duration = float(parts[1]) if len(parts) > 1 else 1.0
            return Action(f"等待", int(duration * 10), [])
            
        # 2. 普攻指令 (a1, a2, ...)
        if cmd.startswith("a") and cmd[1:].isdigit():
            idx = int(cmd[1:])
            if hasattr(self, 'create_normal_attack'):
                return self.create_normal_attack(idx - 1)
        
        # 3. 战技指令 (skill, e)
        if cmd in ["skill", "e"]:
            # 移除 CD 检查
            # if self.cooldowns.get("skill", 0) > 0:
            #    return None
            
            if hasattr(self, 'create_skill'):
                # 不再设置 CD
                # skill_cd = getattr(self, 'skill_cd', 120)
                # self.cooldowns["skill"] = skill_cd
                return self.create_skill()
        
        # 4. 终结技指令 (ult, q)
        if cmd in ["ult", "q"]:
            # 移除 CD 检查
            # if self.cooldowns.get("ult", 0) > 0:
            #    return None
                
            # 不再设置 CD
            # ult_cd = getattr(self, 'ult_cd', 300)
            # self.cooldowns["ult"] = ult_cd
            return self.create_ult()
            
        # 5. QTE 指令
        if cmd == "qte":
            if self.qte_ready_timer > 0:
                self.qte_ready_timer = 0
                if hasattr(self, 'create_qte'):
                    return self.create_qte()
            return None

        return Action("未知", 0, [])

    # 子类需实现以下工厂方法
    def create_normal_attack(self, idx): raise NotImplementedError
    def create_skill(self): raise NotImplementedError
    def create_ult(self): raise NotImplementedError
    def create_qte(self): raise NotImplementedError