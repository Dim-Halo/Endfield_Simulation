from collections import deque
from dataclasses import asdict

from core.enums import MoveType
from core.stats import CombatStats, Attributes, StatKey
from mechanics.buff_system import BuffManager
from simulation.action import Action
from simulation.engine import SimEngine
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

        # QTE 就绪计时器 (通用机制)
        self.qte_ready_timer = 0

        # 面板缓存
        self._panel_cache = None
        self._panel_cache_version = -1

    def get_current_panel(self):
        """
        获取当前面板属性（计算 Buff 后的快照）
        使用缓存机制避免重复计算
        """
        # 检查缓存是否有效
        current_version = self.buffs.get_version()
        if self._panel_cache is not None and self._panel_cache_version == current_version:
            return self._panel_cache

        # 1. 基础属性
        panel = asdict(self.base_stats)

        # 1.5 应用四维属性的影响（如果角色有attrs）
        if hasattr(self, 'attrs') and self.attrs:
            # 计算最大生命值: 基础生命 + 力量 * 5
            panel[StatKey.BASE_HP] = self.base_stats.base_hp + (self.attrs.strength * 5)

            # 计算物理抗性 (敏捷衍生)
            panel[StatKey.PHYS_RES] = self.base_stats.calculate_phys_res(self.attrs)

            # 计算法术抗性 (智识衍生)
            panel[StatKey.MAGIC_RES] = self.base_stats.calculate_magic_res(self.attrs)

            # 计算属性乘区（主副属性）
            if self.main_attr and self.sub_attr:
                attr_mult = self.base_stats.get_attr_multiplier(self.attrs, self.main_attr, self.sub_attr)
                # 属性乘区作为独立乘区，在最终攻击力计算后应用
                panel['_attr_multiplier'] = attr_mult

        # 2. 预处理 Hook (子类可覆盖)
        self._modify_panel_before_buffs(panel)

        # 3. 应用自身 Buff
        self.buffs.apply_stats(panel)

        # 4. 计算最终攻击力 (Final Atk)
        # 公式: (基础攻击 + 武器攻击 + 固定攻击) * (1 + 攻击百分比) * 属性乘区
        base = panel[StatKey.BASE_ATK] + panel[StatKey.WEAPON_ATK] + panel[StatKey.FLAT_ATK]
        atk_mult = 1.0 + panel[StatKey.ATK_PCT]
        attr_mult = panel.get('_attr_multiplier', 1.0)
        panel[StatKey.FINAL_ATK] = base * atk_mult * attr_mult

        # 缓存结果
        self._panel_cache = panel
        self._panel_cache_version = current_version

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
            tick=self.engine.tick,
            move_type=action.move_type
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

        # 1.5 等待到指定时间（绝对时间）
        if cmd == "wait_until":
            target_time = float(parts[1]) if len(parts) > 1 else 0.0
            current_time = self.engine.tick / 10.0  # 转换为秒
            wait_duration = max(0, target_time - current_time)
            # 如果目标时间已经过去，返回0持续时间的动作（立即执行下一个命令）
            return Action(f"等待至{target_time:.2f}s", int(wait_duration * 10), [])

        # 2. 普攻指令 (a1, a2, ...)
        if cmd.startswith("a") and cmd[1:].isdigit():
            idx = int(cmd[1:])
            if hasattr(self, 'create_normal_attack'):
                return self.create_normal_attack(idx - 1)

        # 3. 战技指令 (skill, e)
        if cmd in ["skill", "e"]:
            if hasattr(self, 'create_skill'):
                return self.create_skill()

        # 4. 终结技指令 (ult, q)
        if cmd in ["ult", "q"]:
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