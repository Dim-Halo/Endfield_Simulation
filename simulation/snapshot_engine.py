"""
Snapshot Engine - 用于捕获战斗快照的引擎扩展
"""
from collections import defaultdict
from simulation.engine import SimEngine
from core.enums import ReactionType, BuffEffect


def categorize_buff(buff):
    """将Buff分类到不同的伤害乘区"""
    if hasattr(buff, 'tags') and ReactionType.CORROSION in buff.tags:
        return "🌐 抗性区"
    if hasattr(buff, 'effect_type'):
        if buff.effect_type == BuffEffect.DOT:
            return "🔥 DOT伤害"
        if buff.effect_type == BuffEffect.CC:
            return "❄️ 控制"
    if hasattr(buff, 'tags'):
        for tag in buff.tags:
            if tag in [ReactionType.BURNING, ReactionType.FROZEN]:
                return "🔥 元素反应"
            if tag == "focus":
                return "🎯 标记"
    if hasattr(buff, 'stat_modifiers'):
        modifiers = buff.stat_modifiers
        if "atk_pct" in modifiers:
            return "💪 攻击区"
        if any("fragility" in key for key in modifiers):
            return "🛡️ 脆弱区"
        if any("vulnerability" in key for key in modifiers):
            return "💔 易伤区"
        if any(key in modifiers for key in ["dmg_bonus", "heat_dmg_bonus", "electric_dmg_bonus",
                                              "normal_dmg_bonus", "skill_dmg_bonus", "ult_dmg_bonus",
                                              "qte_dmg_bonus"]):
            return "⚔️ 伤害加成区"
        if "amplification" in modifiers:
            return "📈 增幅区"
        if any(key.endswith("_res") for key in modifiers):
            return "🌐 抗性区"

    name = buff.name
    if "攻击" in name: return "💪 攻击区"
    if "脆弱" in name: return "🛡️ 脆弱区"
    if "易伤" in name or name in ["导电", "碎甲"]: return "💔 易伤区"
    if "增伤" in name or "伤害" in name: return "⚔️ 伤害加成区"
    if "腐蚀" in name: return "🌐 抗性区"
    return "📦 其他"


class SnapshotEngine(SimEngine):
    """扩展SimEngine,添加快照捕获功能"""

    def __init__(self):
        super().__init__()
        self.history = []
        self.logs_by_tick = defaultdict(list)
        self.damage_by_tick = defaultdict(int)
        self.logs = []

    def log(self, message, level="INFO"):
        """重写日志方法,捕获伤害和关键事件"""
        # 1. 处理统计数据(始终捕获伤害用于统计)
        if "Hit造成伤害" in message or "造成伤害" in message:
            try:
                parts = message.split()
                dmg_val = 0
                for part in reversed(parts):
                    clean_part = part.strip("|")
                    if clean_part.isdigit():
                        dmg_val = int(clean_part)
                        break
                if dmg_val > 0:
                    self.damage_by_tick[self.tick] += dmg_val
            except:
                pass

        # 2. 过滤显示日志
        is_action = "执行:" in message
        is_direct_hit = "Hit造成伤害" in message

        if not (is_action or is_direct_hit):
            return

        timestamp = f"[{int(self.tick/10 // 60):02}:{self.tick/10 % 60:04.1f}]"
        log_type = "info"
        if is_direct_hit:
            log_type = "damage"
        elif is_action:
            log_type = "action"

        self.logs.append({"time": timestamp, "message": message, "type": log_type})
        self.logs_by_tick[self.tick].append(f"{timestamp} {message}")

    def capture_snapshot(self):
        """捕获当前战斗状态快照"""
        frame_data = {
            "time_str": f"{self.tick / 10.0:.1f}s",
            "tick": self.tick,
            "damage_tick": self.damage_by_tick[self.tick],
            "sp": self.party_manager.get_sp(),
            "entities": {}
        }
        for ent in self.entities:
            buff_list = []
            if hasattr(ent, "buffs"):
                for b in ent.buffs.buffs:
                    buff_list.append({
                        "name": b.name,
                        "stacks": b.stacks,
                        "duration": b.duration_ticks / 10.0,
                        "category": categorize_buff(b),
                        "desc": getattr(b, "value", "N/A")
                    })
            action_info = None
            if hasattr(ent, "current_action") and ent.current_action:
                act = ent.current_action
                progress = ent.action_timer / act.duration if act.duration > 0 else 0
                action_info = {"name": act.name, "progress": min(1.0, progress)}
            extra_info = ""
            if hasattr(ent, "molten_stacks"):
                extra_info = f"熔火: {ent.molten_stacks}"

            # 捕获QTE就绪状态
            qte_ready = False
            if hasattr(ent, "qte_ready_timer"):
                qte_ready = ent.qte_ready_timer > 0

            frame_data["entities"][ent.name] = {
                "buffs": buff_list,
                "action": action_info,
                "extra": extra_info,
                "qte_ready": qte_ready
            }
        self.history.append(frame_data)

    def run_with_snapshots(self, max_seconds):
        """运行模拟并捕获快照"""
        max_ticks = int(max_seconds * 10)
        self.capture_snapshot()
        for _ in range(max_ticks):
            self.tick += 1
            for entity in self.entities:
                entity.on_tick(self)
            self.capture_snapshot()
