"""
战斗统计分析系统
提供详细的战斗数据收集和分析功能
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from core.enums import Element, MoveType, ReactionType


@dataclass
class DamageRecord:
    """单次伤害记录"""
    tick: int              # 发生时间
    source: str           # 伤害来源（角色名）
    target: str           # 目标名
    skill_name: str       # 技能名称
    damage: float         # 伤害值
    element: Element      # 元素类型
    move_type: MoveType   # 招式类型
    is_crit: bool = False # 是否暴击
    is_reaction: bool = False  # 是否来自反应


@dataclass
class BuffRecord:
    """Buff记录"""
    tick_start: int       # 生效时间
    tick_end: int         # 结束时间
    owner: str           # 拥有者
    buff_name: str       # Buff名称
    source: str          # 来源（谁施加的）
    stacks: int = 1      # 层数


@dataclass
class ReactionRecord:
    """元素反应记录"""
    tick: int
    trigger: str         # 触发者
    target: str          # 目标
    reaction_type: ReactionType
    level: int           # 反应等级
    extra_damage: float  # 额外伤害


@dataclass
class SkillUsageRecord:
    """技能使用记录"""
    tick: int
    character: str
    skill_name: str
    duration: int  # 技能持续时间（tick）


@dataclass
class CharacterStats:
    """角色统计数据"""
    name: str
    total_damage: float = 0.0
    skill_damage: Dict[str, float] = field(default_factory=dict)
    skill_count: Dict[str, int] = field(default_factory=dict)
    reaction_damage: float = 0.0
    reaction_count: Dict[ReactionType, int] = field(default_factory=dict)
    crit_count: int = 0
    hit_count: int = 0
    active_time: int = 0  # 活跃时间（tick）


class CombatStatistics:
    """战斗统计收集器"""

    def __init__(self):
        # 原始记录
        self.damage_records: List[DamageRecord] = []
        self.buff_records: List[BuffRecord] = []
        self.reaction_records: List[ReactionRecord] = []
        self.skill_usage_records: List[SkillUsageRecord] = []

        # 聚合数据
        self.character_stats: Dict[str, CharacterStats] = {}
        self.total_damage = 0.0
        self.combat_duration = 0  # tick

        # 时间线数据（用于绘图）
        self.damage_timeline: List[Tuple[int, str, float]] = []  # (tick, source, damage)
        self.dps_timeline: Dict[str, List[Tuple[int, float]]] = defaultdict(list)  # source -> [(tick, dps)]

        # 内部缓存
        self._dps_window = 10  # 计算DPS的窗口大小（tick）
        self._dps_cache: Dict[str, List[float]] = defaultdict(list)

    def record_damage(self, tick: int, source: str, target: str,
                     skill_name: str, damage: float, element: Element,
                     move_type: MoveType, is_crit: bool = False,
                     is_reaction: bool = False):
        """记录伤害事件"""
        record = DamageRecord(
            tick=tick,
            source=source,
            target=target,
            skill_name=skill_name,
            damage=damage,
            element=element,
            move_type=move_type,
            is_crit=is_crit,
            is_reaction=is_reaction
        )
        self.damage_records.append(record)
        self.damage_timeline.append((tick, source, damage))

        # 更新聚合数据
        if source not in self.character_stats:
            self.character_stats[source] = CharacterStats(name=source)

        stats = self.character_stats[source]
        stats.total_damage += damage
        stats.hit_count += 1

        if is_crit:
            stats.crit_count += 1

        if is_reaction:
            stats.reaction_damage += damage
        else:
            if skill_name not in stats.skill_damage:
                stats.skill_damage[skill_name] = 0.0
            stats.skill_damage[skill_name] += damage

        self.total_damage += damage

        # 更新DPS缓存
        self._dps_cache[source].append(damage)

    def record_buff(self, tick_start: int, tick_end: int, owner: str,
                   buff_name: str, source: str, stacks: int = 1):
        """记录Buff事件"""
        record = BuffRecord(
            tick_start=tick_start,
            tick_end=tick_end,
            owner=owner,
            buff_name=buff_name,
            source=source,
            stacks=stacks
        )
        self.buff_records.append(record)

    def record_reaction(self, tick: int, trigger: str, target: str,
                       reaction_type: ReactionType, level: int,
                       extra_damage: float = 0.0):
        """记录元素反应"""
        record = ReactionRecord(
            tick=tick,
            trigger=trigger,
            target=target,
            reaction_type=reaction_type,
            level=level,
            extra_damage=extra_damage
        )
        self.reaction_records.append(record)

        # 更新角色统计
        if trigger not in self.character_stats:
            self.character_stats[trigger] = CharacterStats(name=trigger)

        stats = self.character_stats[trigger]
        if reaction_type not in stats.reaction_count:
            stats.reaction_count[reaction_type] = 0
        stats.reaction_count[reaction_type] += 1

    def record_skill_usage(self, tick: int, character: str,
                          skill_name: str, duration: int):
        """记录技能使用"""
        record = SkillUsageRecord(
            tick=tick,
            character=character,
            skill_name=skill_name,
            duration=duration
        )
        self.skill_usage_records.append(record)

        # 更新技能计数
        if character not in self.character_stats:
            self.character_stats[character] = CharacterStats(name=character)

        stats = self.character_stats[character]
        if skill_name not in stats.skill_count:
            stats.skill_count[skill_name] = 0
        stats.skill_count[skill_name] += 1

    def update_combat_duration(self, tick: int):
        """更新战斗时长"""
        self.combat_duration = max(self.combat_duration, tick)

    def calculate_dps(self, character: Optional[str] = None) -> float:
        """
        计算DPS

        Args:
            character: 角色名，None表示计算全队DPS
        """
        if self.combat_duration == 0:
            return 0.0

        duration_seconds = self.combat_duration / 10.0

        if character is None:
            return self.total_damage / duration_seconds

        if character in self.character_stats:
            return self.character_stats[character].total_damage / duration_seconds

        return 0.0

    def get_damage_breakdown(self, character: str) -> Dict[str, float]:
        """
        获取角色伤害分解（按技能）

        Returns:
            Dict[技能名, 伤害占比]
        """
        if character not in self.character_stats:
            return {}

        stats = self.character_stats[character]
        total = stats.total_damage
        if total == 0:
            return {}

        breakdown = {}
        for skill_name, damage in stats.skill_damage.items():
            breakdown[skill_name] = damage / total

        if stats.reaction_damage > 0:
            breakdown["元素反应"] = stats.reaction_damage / total

        return breakdown

    def get_crit_rate(self, character: str) -> float:
        """计算实际暴击率"""
        if character not in self.character_stats:
            return 0.0

        stats = self.character_stats[character]
        if stats.hit_count == 0:
            return 0.0

        return stats.crit_count / stats.hit_count

    def get_buff_uptime(self, owner: str, buff_name: str) -> float:
        """
        计算Buff覆盖率

        Returns:
            覆盖率 (0.0-1.0)
        """
        if self.combat_duration == 0:
            return 0.0

        total_uptime = 0
        for record in self.buff_records:
            if record.owner == owner and record.buff_name == buff_name:
                duration = record.tick_end - record.tick_start
                total_uptime += duration

        return min(1.0, total_uptime / self.combat_duration)

    def get_reaction_summary(self) -> Dict[ReactionType, int]:
        """获取反应触发汇总"""
        summary = defaultdict(int)
        for record in self.reaction_records:
            summary[record.reaction_type] += 1
        return dict(summary)

    def generate_timeline_data(self, window_size: int = 10) -> Dict[str, List[Tuple[float, float]]]:
        """
        生成DPS时间线数据（用于绘图）

        Args:
            window_size: 滑动窗口大小（tick）

        Returns:
            Dict[角色名, List[(时间(秒), DPS)]]
        """
        # 按角色分组
        character_damages = defaultdict(list)
        for tick, source, damage in self.damage_timeline:
            character_damages[source].append((tick, damage))

        # 计算滑动窗口DPS
        timeline_data = {}
        for character, damages in character_damages.items():
            dps_data = []
            for current_tick in range(0, self.combat_duration, window_size // 2):
                window_start = max(0, current_tick - window_size // 2)
                window_end = current_tick + window_size // 2

                window_damage = sum(
                    dmg for tick, dmg in damages
                    if window_start <= tick < window_end
                )

                window_duration = (window_end - window_start) / 10.0
                dps = window_damage / window_duration if window_duration > 0 else 0

                time_seconds = current_tick / 10.0
                dps_data.append((time_seconds, dps))

            timeline_data[character] = dps_data

        return timeline_data

    def generate_report(self) -> str:
        """生成文本格式的统计报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("战斗统计报告".center(60))
        lines.append("=" * 60)

        # 基本信息
        duration_sec = self.combat_duration / 10.0
        lines.append(f"\n战斗时长: {duration_sec:.1f}秒 ({self.combat_duration} ticks)")
        lines.append(f"总伤害: {int(self.total_damage):,}")
        lines.append(f"全队DPS: {self.calculate_dps():.1f}")

        # 角色伤害排行
        lines.append("\n" + "-" * 60)
        lines.append("角色伤害统计".center(60))
        lines.append("-" * 60)

        sorted_chars = sorted(
            self.character_stats.values(),
            key=lambda x: x.total_damage,
            reverse=True
        )

        for stats in sorted_chars:
            lines.append(f"\n【{stats.name}】")
            # 防止除零错误
            damage_pct = (stats.total_damage/self.total_damage*100) if self.total_damage > 0 else 0.0
            lines.append(f"  总伤害: {int(stats.total_damage):,} ({damage_pct:.1f}%)")
            lines.append(f"  DPS: {self.calculate_dps(stats.name):.1f}")
            lines.append(f"  命中次数: {stats.hit_count}")
            if stats.hit_count > 0:
                lines.append(f"  实际暴击率: {self.get_crit_rate(stats.name)*100:.1f}%")

            # 技能伤害分解
            if stats.skill_damage and stats.total_damage > 0:
                lines.append("  技能伤害:")
                for skill, damage in sorted(stats.skill_damage.items(), key=lambda x: x[1], reverse=True):
                    pct = damage / stats.total_damage * 100
                    lines.append(f"    - {skill}: {int(damage):,} ({pct:.1f}%)")

            # 反应伤害
            if stats.reaction_damage > 0 and stats.total_damage > 0:
                pct = stats.reaction_damage / stats.total_damage * 100
                lines.append(f"  反应伤害: {int(stats.reaction_damage):,} ({pct:.1f}%)")

        # 元素反应统计
        reaction_summary = self.get_reaction_summary()
        if reaction_summary:
            lines.append("\n" + "-" * 60)
            lines.append("元素反应统计".center(60))
            lines.append("-" * 60)
            for reaction_type, count in sorted(reaction_summary.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {reaction_type.value}: {count}次")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def reset(self):
        """重置所有统计数据"""
        self.damage_records.clear()
        self.buff_records.clear()
        self.reaction_records.clear()
        self.skill_usage_records.clear()
        self.character_stats.clear()
        self.damage_timeline.clear()
        self.dps_timeline.clear()
        self._dps_cache.clear()
        self.total_damage = 0.0
        self.combat_duration = 0
