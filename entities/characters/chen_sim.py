# entities/characters/chen_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType, ReactionType, BuffCategory, BuffEffect
from mechanics.buff_system import Buff, StatModifierBuff
from .chen_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage
from simulation.event_system import EventType

class ZhanFengBuff(StatModifierBuff):
    """天赋二：斩锋 - 攻击力提升"""
    def __init__(self, stacks=1):
        super().__init__(
            "斩锋", 
            duration=MECHANICS['passive_duration'], 
            stat_modifiers={"atk_pct": MECHANICS['passive_atk_bonus']}, 
            category=BuffCategory.BUFF,
            max_stacks=MECHANICS['passive_max_stacks']
        )
        self.stacks = stacks

class ChenSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("陈千语", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=106, agility=171, intelligence=85, willpower=93)
        self.base_stats = CombatStats(base_hp=5495, base_atk=297)

        # 主副属性
        self.main_attr = "agility"
        self.sub_attr = "strength"

        # 技能CD设置 (配合 BaseActor.parse_command) - 移除 CD 机制
        # self.skill_cd = 120
        # self.ult_cd = 300
        
        # 订阅事件
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self.on_reaction_triggered)

    # ===== 状态管理 =====
    def on_tick(self, engine):
        super().on_tick(engine)
        # qte_ready_timer 已在父类处理

    # ===== 事件监听 =====
    def on_reaction_triggered(self, event):
        """监听物理破防以触发QTE"""
        reaction_type = event.get("reaction_type")
        level = event.get("level")
        
        # 条件：敌人进入破防状态 (物理异常且层数为1)
        # 注意：这里假设层数为1即代表"进入"破防状态（从0变1）。
        # 如果是其他异常叠加（例如从1变2），level会大于1。
        if reaction_type == ReactionType.PHYS_ANOMALY and level == 1:
            self.qte_ready_timer = 30 # 3秒内可发动
            self.engine.log(f"   [陈千语] 检测到物理破防(进入状态)，见天河就绪！")

    def _trigger_passive_2(self):
        """触发天赋二：斩锋"""
        self.buffs.add_buff(ZhanFengBuff(), self.engine)

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, len(mvs)-1)
        mv = mvs[idx]
        f_data = frames[idx]
        is_heavy = (seq_index == 4)

        def perform():
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"破飞霞{seq_index+1}",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL
            )
            # 重击（第5段，索引4）造成16点失衡
            if is_heavy:
                self.target.apply_stagger(16, self.engine)

        return Action(f"破飞霞{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL)

    def create_skill(self):
        """战技：归穹宇"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]

        def perform():
            # 造成伤害 + 击飞 (Launch)
            deal_damage(
                self.engine, self, self.target,
                skill_name="归穹宇",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.SKILL,
                attachments=[PhysAnomalyType.LAUNCH]
            )
            self.engine.log(f"   [战技] 击飞敌人 {MECHANICS['airborne_duration']}秒")
            
            # 失衡
            self.target.apply_stagger(10, self.engine)
            
            # 触发天赋二
            self._trigger_passive_2()
            
            # 天赋一：打断蓄力检测 (模拟：假设概率触发或通过外部标志)
            # 这里简单处理：如果目标正在施法(Action不为空)，则视为打断
            # 但DummyEnemy通常没有Action。我们略过或简单加个log。
            pass

        return Action("归穹宇", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.SKILL)

    def create_ult(self):
        """终结技：冽风霜"""
        f_data = FRAME_DATA["ult"]
        mv_slash = SKILL_MULTIPLIERS["ult_slash"]
        mv_final = SKILL_MULTIPLIERS["ult_final"]
        
        # 构建多段伤害
        events = []
        
        # 前6段
        for i in range(6):
            def hit(idx=i):
                deal_damage(
                    self.engine, self, self.target,
                    skill_name=f"冽风霜(斩击{idx+1})",
                    skill_mv=mv_slash,
                    element=Element.PHYSICAL,
                    move_type=MoveType.ULTIMATE
                )
                if idx == 0:
                    self.target.apply_stagger(15, self.engine)
                self._trigger_passive_2()
            
            # 假设每段间隔5帧
            events.append(DamageEvent(10 + i*5, hit))
            
        # 最后一段
        def hit_final():
            deal_damage(
                self.engine, self, self.target,
                skill_name="冽风霜(终结)",
                skill_mv=mv_final,
                element=Element.PHYSICAL,
                move_type=MoveType.ULTIMATE
            )
            self.target.apply_stagger(20, self.engine)
            self._trigger_passive_2()
            
        events.append(DamageEvent(10 + 6*5 + 10, hit_final)) # 稍后一点

        return Action("刺骨寒寒", f_data['total'], events, move_type=MoveType.ULTIMATE)

    def create_qte(self):
        """连携技：见天河"""
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]

        def perform():
            self._trigger_passive_2()
            
            # 伤害 + 击飞
            deal_damage(
                self.engine, self, self.target,
                skill_name="见天河",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.QTE,
                attachments=[PhysAnomalyType.LAUNCH]
            )
            # 失衡
            self.target.apply_stagger(10, self.engine)
            
            self.engine.log(f"   [连携技] 击飞敌人")
            
            # 恢复一点SP

        return Action("见天河", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)
