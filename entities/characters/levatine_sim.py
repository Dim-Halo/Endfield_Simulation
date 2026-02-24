# entities/characters/levatine_sim.py
from core.damage_helper import deal_damage
from core.enums import Element, MoveType, ReactionType, BuffCategory
from core.stats import CombatStats, Attributes, StatKey
from mechanics.buff_system import Buff, BurningBuff
from simulation.action import Action, DamageEvent
from simulation.event_system import EventType

from .base_actor import BaseActor
from .levatine_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS

class HeatInflict(Buff):
    """莱瓦汀天赋：灼热附着 - 标记目标"""
    def __init__(self):
        super().__init__("灼热附着", duration_sec=20.0, category=BuffCategory.NEUTRAL)
        self.tags.append("heat_inflict")  # 添加自定义标签


class LevatineSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("莱瓦汀", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=121, agility=99, intelligence=177, willpower=89)
        self.base_stats = CombatStats(base_hp=5495, base_atk=318)

        # 主副属性
        self.main_attr = "intelligence"
        self.sub_attr = "strength"

        # 机制状态
        self.molten_stacks = 0
        self.ult_duration_ticks = 0

        # 订阅事件
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self.on_reaction_triggered)
        self.engine.event_bus.subscribe(EventType.BUFF_APPLIED, self.on_buff_event)
        self.engine.event_bus.subscribe(EventType.BUFF_STACKED, self.on_buff_event)

    # ===== 状态管理 =====
    def on_tick(self, engine):
        if self.ult_duration_ticks > 0:
            self.ult_duration_ticks -= 1
            if self.ult_duration_ticks == 0:
                engine.log(f"[{self.name}] 终结技状态结束")
        super().on_tick(engine)
        
        # qte_ready_timer 已在父类处理

    def on_reaction_triggered(self, event):
        pass

    def on_buff_event(self, event):
        """监听 Buff 施加/叠加事件"""
        # QTE触发条件：敌人被施加燃烧或腐蚀 (瞬间)
        buff_name = event.get("buff_name")
        tags = event.get("tags", [])
        
        # 如果是 STACKED 事件，tags 可能为空，需通过 name 判断
        # 或者 BuffManager 在 STACKED 时不传 tags?
        # 简单通过 buff_name 判断 (硬编码常见Buff名) 或者假设 tags 会被传递 (如果修改过 BuffManager)
        # 鉴于 BuffManager 未必传递 tags，我们增加名称检查作为 fallback
        
        is_trigger = False
        
        # 1. 检查 Tags
        if ReactionType.BURNING in tags or ReactionType.CORROSION in tags:
            is_trigger = True
            
        # 2. 检查 Name (Fallback)
        if not is_trigger:
            if buff_name in ["燃烧", "腐蚀"]:
                is_trigger = True
                
        if is_trigger:
            self.qte_ready_timer = 30
            self.engine.log(f"   [莱瓦汀] 检测到异常施加({buff_name})，沸腾就绪！")

    @property
    def is_ult_active(self):
        return self.ult_duration_ticks > 0

    def _modify_panel_before_buffs(self, stats):
        if self.molten_stacks >= 4:
            stats[StatKey.RES_PEN] += MECHANICS['heat_res_shred']

    # ===== 伤害计算 =====
    # _deal_damage 已移除，使用 core.damage_helper.deal_damage

    # ===== 命令解析 =====
    # 莱瓦汀保留 parse_command，因为其QTE是基于条件而非CD/Timer
    def parse_command(self, cmd_str: str):
        parts = cmd_str.split()
        cmd = parts[0].lower()

        # 优先处理通用命令（包括wait和wait_until）
        if cmd in ["wait", "wait_until"]:
            return super().parse_command(cmd_str)

        if cmd.startswith("a") and cmd[1:].isdigit():
            return self.create_normal_attack(int(cmd[1:]) - 1)
        if cmd in ["skill", "e"]:
            return self.create_skill()
        if cmd in ["ult", "q"]:
            return self.create_ult()
        if cmd == "qte":
            if self.qte_ready_timer > 0:
                self.qte_ready_timer = 0
                return self.create_qte()
            return None

        return Action("未知", 0, [])

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        key = "enhanced_normal" if self.is_ult_active else "normal"
        mvs = SKILL_MULTIPLIERS[key]
        frames = FRAME_DATA[key]
        idx = min(seq_index, len(mvs)-1)
        mv = mvs[idx]
        f_data = frames[min(seq_index, len(frames)-1)]

        def perform():
            is_heavy = (not self.is_ult_active and seq_index == 4)
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"普攻{seq_index+1}",
                skill_mv=mv,
                element=Element.HEAT,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL
            )
            # 强化普攻天赋：第3段施加灼热附着
            if self.is_ult_active and (seq_index + 1) == 3:
                self.target.buffs.add_buff(HeatInflict(), self.engine)
            # 重击失衡：普攻第5段造成18点失衡
            if is_heavy:  # 普通普攻第5段
                self.target.apply_stagger(18.0, self.engine)
            # 吸收天赋
            is_last = (seq_index == 4) if not self.is_ult_active else False
            if is_last and self.target.buffs.consume_tag("heat_inflict"):
                 self.molten_stacks = min(4, self.molten_stacks + 1)
                 self.engine.log(f"   [天赋] 吸收附着！层数: {self.molten_stacks}")

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        f_data = FRAME_DATA['skill']
        events = []

        # 判断施放时是否已有4层熔火
        has_full_stacks = self.molten_stacks >= 4

        def hit_init():
            deal_damage(
                self.engine, self, self.target,
                skill_name="焚灭(起手)",
                skill_mv=SKILL_MULTIPLIERS['skill_initial'],
                element=Element.HEAT,
                move_type=MoveType.SKILL
            )
            if not has_full_stacks:  # 只在非满层时增加
                self.molten_stacks = min(4, self.molten_stacks + 1)
                self.engine.log(f"   (状态) 熔火层数: {self.molten_stacks}")

        def hit_burst():
            self.molten_stacks = 0
            self.engine.log(f"   >>> 熔火核爆！")

            # 核爆伤害
            deal_damage(
                self.engine, self, self.target,
                skill_name="焚灭(核爆)",
                skill_mv=SKILL_MULTIPLIERS['skill_burst'],
                element=Element.HEAT,
                move_type=MoveType.SKILL
            )

            # 强制施加燃烧
            stats = self.get_current_panel()
            burn_dmg = stats[StatKey.FINAL_ATK] * (SKILL_MULTIPLIERS['skill_dot'] / 100.0)
            self.target.buffs.add_buff(BurningBuff(burn_dmg), self.engine)

        events.append(DamageEvent(f_data['hit_init'], hit_init))
        # 只在满层时才追加核爆攻击
        if has_full_stacks:
            events.append(DamageEvent(f_data['hit_burst'], hit_burst))
        return Action("焚灭", f_data['total'], events, move_type=MoveType.SKILL)

    def create_ult(self):
        f_data = FRAME_DATA['ult']
        def activate():
            self.ult_duration_ticks = 150
            self.engine.log("   >>> 进入强化状态")
        return Action("黄昏", f_data['total'], [DamageEvent(f_data['hit'], activate)], move_type=MoveType.ULTIMATE)

    def create_qte(self):
        """连携技：沸腾 - 对燃烧/腐蚀状态的敌人造成伤害"""
        f_data = FRAME_DATA['qte']

        def perform():
            # 1. 筛选目标 (燃烧/腐蚀)
            targets = []
            # 模拟器环境只有 self.target
            if self.target.is_alive:
                has_burn = self.target.buffs.has_tag(ReactionType.BURNING)
                has_corr = self.target.buffs.has_tag(ReactionType.CORROSION)
                if has_burn or has_corr:
                    targets.append(self.target)

            if not targets:
                self.engine.log(f"   [QTE] 无满足条件(燃烧/腐蚀)的目标，未触发")
                return

            hit_count = len(targets)
            self.engine.log(f"   [QTE] 沸腾触发！命中 {hit_count} 个目标")

            # 2. 对每个目标造成伤害 + 失衡
            for t in targets:
                # 造成灼热伤害
                deal_damage(
                    self.engine, self, t,
                    skill_name="沸腾",
                    skill_mv=SKILL_MULTIPLIERS['qte'],
                    element=Element.HEAT,
                    move_type=MoveType.QTE
                )
                t.apply_stagger(10, self.engine)

            # 3. 获得熔火 (只要命中至少1个，获得1层)
            if hit_count > 0:
                self.molten_stacks = min(4, self.molten_stacks + 1)
                self.engine.log(f"   (状态) 熔火层数: {self.molten_stacks}")

            # 4. 回复终结技能量 (基于命中数)
            # 命中1->25, 2->30, 3+->35
            energy_gain = 0
            if hit_count == 1: energy_gain = MECHANICS["qte_energy_gain"][1]
            elif hit_count == 2: energy_gain = MECHANICS["qte_energy_gain"][2]
            elif hit_count >= 3: energy_gain = MECHANICS["qte_energy_gain"][3]
            
            if energy_gain > 0:
                self.engine.log(f"   [资源] 获得终结技能量: {energy_gain}")
                # 尝试调用 party_manager (如果存在)
                if hasattr(self.engine, 'party_manager'):
                    # 假设有接口，或者我们暂时只 log
                    # self.engine.party_manager.add_ult_energy(energy_gain)
                    pass

        return Action("沸腾", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)