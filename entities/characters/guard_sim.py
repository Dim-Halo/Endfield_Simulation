# entities/characters/guard_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType, ReactionType, BuffCategory, BuffEffect
from mechanics.buff_system import Buff, StatModifierBuff
from .guard_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage
from simulation.event_system import EventType

class ShiQiBuff(StatModifierBuff):
    """士气激昂"""
    def __init__(self, duration=20.0):
        super().__init__(
            "士气激昂", 
            duration=duration, 
            stat_modifiers={
                "atk_pct": MECHANICS['passive_atk_bonus'],
                "tech_pct": MECHANICS['passive_tech_bonus']
            }, 
            category=BuffCategory.BUFF,
            max_stacks=MECHANICS['passive_max_stacks']
        )

class IronOathBuff(Buff):
    """铁誓 (终结技机制)"""
    def __init__(self, stacks=5):
        super().__init__(
            "铁誓", 
            duration_sec=MECHANICS['iron_oath_duration'], 
            max_stacks=5,
            category=BuffCategory.BUFF
        )
        self.stacks = stacks

class GuardSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("骏卫", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=101, agility=110, intelligence=97, willpower=173)
        self.base_stats = CombatStats(base_hp=5495, base_atk=321)

        # 主副属性
        self.main_attr = "willpower"
        self.sub_attr = "agility"

        # 机制状态
        # qte_ready_timer 已在父类处理
        self.qte_break_stacks = 0 # 记录触发QTE时消耗的破防层数
        
        self.sp_accumulated = 0 # 天赋一累积恢复的技力
        
        # 订阅事件
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self.on_reaction_triggered)

    # ===== 状态管理 =====
    def on_tick(self, engine):
        super().on_tick(engine)
        # qte_ready_timer 已在父类处理

    def _restore_sp(self, amount):
        """恢复技力并处理天赋一"""
        # 实际回能逻辑 (假设有 energy 系统，这里只模拟天赋触发)
        self.sp_accumulated += amount
        if self.sp_accumulated >= MECHANICS['passive_sp_threshold']:
            self.sp_accumulated -= MECHANICS['passive_sp_threshold']
            self._trigger_morale(duration=MECHANICS['passive_buff_duration'])
            
        self.engine.log(f"   [骏卫] 恢复技力 {amount} (累积: {self.sp_accumulated})")

    def _trigger_morale(self, duration):
        """获得士气激昂"""
        self.buffs.add_buff(ShiQiBuff(duration=duration), self.engine)

    def _trigger_morale_for_all(self, duration):
        """天赋二：全队获得士气激昂"""
        # 遍历队伍成员
        # 简单起见，只给自己加，或者需要 SimEngine 提供队伍列表
        # SimEngine.entities 包含所有实体
        for entity in self.engine.entities:
            if entity.name != self.target.name and hasattr(entity, 'buffs'):
                entity.buffs.add_buff(ShiQiBuff(duration=duration), self.engine)

    # ===== 事件监听 =====
    def on_reaction_triggered(self, event):
        """监听反应以触发QTE和回能"""
        reaction_type = event.get("reaction_type")
        attacker_name = event.get("attacker")
        
        # 1. 监听碎甲反应进行回能 (针对战技)
        if attacker_name == self.name and reaction_type == ReactionType.PHYS_ANOMALY:
            phys_type = event.get("phys_type")
            level = event.get("level")
            if phys_type == PhysAnomalyType.SHATTER:
                sp = MECHANICS["skill_sp_restore"].get(level, 0)
                if sp > 0:
                    self._restore_sp(sp)
                    
        # 2. 监听破防状态变化以触发QTE
        # 条件：敌人进入破防状态 (1层)
        if reaction_type == ReactionType.PHYS_ANOMALY:
            level = event.get("level")
            if level == 1:
                self.qte_ready_timer = 30 # 3秒内可发动
                self.engine.log(f"   [骏卫] 检测到物理破防，盈月邀击就绪！")

        # 3. 终结技后续判定 (铁誓)
        # 条件：任意物理异常触发
        if self.buffs.has_tag("iron_oath") and reaction_type == ReactionType.PHYS_ANOMALY:
            self._trigger_iron_oath_attack()

    def on_post_damage(self, event):
        """监听连携技伤害 -> 触发铁誓"""
        if not self.buffs.has_tag("iron_oath"): return
        
        move_type = event.get("move_type")
        source = event.source
        
        if source == self and move_type == MoveType.QTE:
            self._trigger_iron_oath_attack()

    def _trigger_iron_oath_attack(self):
        """触发盾卫袭扰/决胜"""
        # 消耗1层铁誓
        # 需要从 BuffManager 中找到 IronOathBuff 并减层
        for b in self.buffs.buffs:
            if isinstance(b, IronOathBuff):
                b.stacks -= 1
                current_stack = b.stacks
                
                if current_stack == 0:
                    # 决胜
                    self.engine.log("   [终结技] 铁誓耗尽，盾卫决胜！")
                    deal_damage(
                        self.engine, self, self.target,
                        skill_name="盾卫决胜",
                        skill_mv=SKILL_MULTIPLIERS["ult_final"],
                        element=Element.PHYSICAL,
                        move_type=MoveType.ULTIMATE
                    )
                    self.target.apply_stagger(15, self.engine)
                    self._restore_sp(MECHANICS["ult_final_sp"])
                    self._trigger_morale_for_all(MECHANICS["passive2_buff_duration"])
                    self.buffs.buffs.remove(b) # 移除Buff
                else:
                    # 袭扰
                    self.engine.log(f"   [终结技] 盾卫袭扰 (剩余铁誓: {current_stack})")
                    deal_damage(
                        self.engine, self, self.target,
                        skill_name="盾卫袭扰",
                        skill_mv=SKILL_MULTIPLIERS["ult_harass"],
                        element=Element.PHYSICAL,
                        move_type=MoveType.ULTIMATE
                    )
                    self._restore_sp(MECHANICS["ult_harass_sp"])
                    self._trigger_morale_for_all(MECHANICS["passive2_buff_duration"])
                
                return

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, len(mvs)-1)
        mv = mvs[idx]
        f_data = frames[idx]

        def perform():
            is_heavy = (seq_index == 4)
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"全面攻势{seq_index+1}",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL
            )
            if is_heavy:
                self.target.apply_stagger(18, self.engine)

        return Action(f"全面攻势{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：粉碎阵线"""
        f_data = FRAME_DATA["skill"]
        mv1 = SKILL_MULTIPLIERS["skill_1"]
        mv2 = SKILL_MULTIPLIERS["skill_2"]

        def perform():
            # 第一段
            deal_damage(
                self.engine, self, self.target,
                skill_name="粉碎阵线(1)",
                skill_mv=mv1,
                element=Element.PHYSICAL,
                move_type=MoveType.SKILL
            )
            self.target.apply_stagger(5, self.engine)
            
            # 2. 造成主伤害 + 尝试触发碎甲反应
            deal_damage(
                self.engine, self, self.target,
                skill_name="粉碎阵线(2)",
                skill_mv=mv2,
                element=Element.PHYSICAL,
                move_type=MoveType.SKILL,
                attachments=[PhysAnomalyType.SHATTER]
            )
            self.target.apply_stagger(5, self.engine)

        return Action("粉碎阵线", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.SKILL)

    def create_ult(self):
        """终结技：盾卫旗队，上前"""
        f_data = FRAME_DATA["ult"]
        mv = SKILL_MULTIPLIERS["ult_march"]

        def perform():
            self.engine.log("   [终结技] 盾卫进军！")
            deal_damage(
                self.engine, self, self.target,
                skill_name="盾卫进军",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.ULTIMATE
            )
            self.target.apply_stagger(10, self.engine)
            
            # 生成铁誓
            self.buffs.add_buff(IronOathBuff(), self.engine)
            
            # 触发天赋二
            # 逻辑修正：只要释放终结技（进军），就视为触发了“盾卫旗队，上前”
            # 随后进军途中的伤害算作终结技伤害，并生成铁誓。
            # 后续的“袭扰/决胜”会通过消耗铁誓触发，并在那里触发全队士气激昂。
            # 但描述说 "触发...后续效果后...获得士气激昂"。
            # 所以这里（进军）不触发全队buff，而是在袭扰/决胜里触发。
            # 之前的实现已经在 _trigger_iron_oath_attack 里调用了 _trigger_morale_for_all。
            # 所以这里不需要额外操作。
            pass

        return Action("盾卫旗队", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_qte(self):
        """连携技：盈月邀击"""
        # 骏卫特殊的QTE逻辑：消耗层数
        stacks = self.qte_break_stacks if self.qte_break_stacks > 0 else 1
        
        f_data = FRAME_DATA["qte"]
        
        def perform():
            self.engine.log(f"   [连携技] 盈月邀击 (消耗{stacks}层)")
            
            # 斩击次数 = stacks (max 3)
            count = min(stacks, 3)
            
            for i in range(count):
                idx = i + 1
                is_enhanced = (stacks >= 4 and idx == 3)
                
                mv_key = f"qte_{idx}"
                if is_enhanced: mv_key += "_enhanced"
                
                mv = SKILL_MULTIPLIERS[mv_key]
                sp = MECHANICS["qte_sp_restore_enhanced"] if is_enhanced else MECHANICS["qte_sp_restore"][i]
                stagger = 9 if is_enhanced else [3, 3, 4][i]
                
                deal_damage(
                    self.engine, self, self.target,
                    skill_name=f"盈月邀击({idx})",
                    skill_mv=mv,
                    element=Element.PHYSICAL,
                    move_type=MoveType.QTE
                )
                self.target.apply_stagger(stagger, self.engine)
                self._restore_sp(sp)

        return Action("盈月邀击", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)
