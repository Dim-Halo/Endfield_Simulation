# entities/characters/admin_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType, ReactionType, BuffCategory, BuffEffect
from mechanics.buff_system import Buff, VulnerabilityBuff
from .admin_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage
from core.stats import CombatStats, Attributes, StatKey
from simulation.event_system import EventType

class OriginiumCrystalBuff(Buff):
    """源石结晶（封印）"""
    def __init__(self):
        super().__init__(
            "源石结晶",
            duration_sec=MECHANICS['seal_duration'],
            category=BuffCategory.DEBUFF,
            effect_type=BuffEffect.CC
        )
        self.tags.add("originium_crystal")
        self.vuln_value = MECHANICS['seal_vuln']

    def modify_stats(self, stats: dict):
        # 天赋二：被封印的敌人受到额外物理伤害（易伤）
        # 直接修改物理易伤属性
        if StatKey.PHYS_VULN in stats:
            stats[StatKey.PHYS_VULN] += self.vuln_value
        else:
            stats[StatKey.PHYS_VULN] = self.vuln_value

class AdminSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("管理员", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=123, agility=140, intelligence=96, willpower=107)
        self.base_stats = CombatStats(base_hp=5495, base_atk=319)

        # 主副属性
        self.main_attr = "strength"
        self.sub_attr = "agility"

        # 技能CD - 移除 CD 机制
        # self.skill_cd = 120
        # self.ult_cd = 300
        
        # 订阅事件
        self.engine.event_bus.subscribe(EventType.POST_DAMAGE, self.on_post_damage)
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self.on_reaction_triggered)

    # ===== 状态管理 =====
    def on_tick(self, engine):
        super().on_tick(engine)
        # qte_ready_timer 已在父类处理

    # ===== 事件监听 =====
    def on_post_damage(self, event):
        """监听伤害以触发QTE就绪"""
        # 条件：小队内其他干员的连携技造成伤害
        source = event.source
        move_type = event.get("move_type")
        
        if source != self and move_type == MoveType.QTE:
            self.qte_ready_timer = 30 # 3秒内可发动（假设值）
            # self.engine.log(f"   [管理员] 检测到队友连携技，锁闭序列就绪！") 
            # 日志可能太多，暂不打

    def _shatter_crystal(self, is_ult=False):
        """击碎结晶逻辑"""
        # 检查是否存在结晶
        if not self.target.buffs.has_tag("originium_crystal"):
            return

        self.target.buffs.consume_tag("originium_crystal")
        # 移除易伤已由 consume_tag 自动处理（因为易伤绑定在结晶Buff上）
        
        # 根据触发源决定伤害类型和倍率
        if is_ult:
            # 被终结技击碎：只吃终结技倍率和终结技增伤
            # 已经在 create_ult 中处理了额外伤害，这里只负责清理状态
            # 或者为了统一，将 create_ult 中的额外伤害逻辑移到这里？
            # 不，create_ult 的逻辑是独立的。
            # 这里是被动触发（通过物理异常），所以 is_ult=False。
            # 如果是 create_ult 主动调用，需要区分。
            pass
        else:
            # 被物理异常或破防击碎（视为连携技效果）
            # 吃到连携技倍率 (400%)，且该伤害视为连携技伤害 (MoveType.QTE)
            # 这样就能吃到连携技增伤 (qte_dmg_bonus)
            
            mv = SKILL_MULTIPLIERS["qte_shatter"] 
            self.engine.log(f"   [管理员] 源石结晶被物理异常击碎！(连携技伤害)")
            deal_damage(
                self.engine, self, self.target,
                skill_name="结晶碎裂",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.QTE,
                attachments=[]
            )

    def on_reaction_triggered(self, event):
        """监听反应以击碎结晶"""
        # 条件：施加物理异常和破防 -> 击碎源石结晶
        reaction_type = event.get("reaction_type")
        target_name = event.get("target")
        
        if target_name != self.target.name: return
        
        if reaction_type == ReactionType.PHYS_ANOMALY:
            phys_type = event.get("phys_type")
            if phys_type is None or phys_type == PhysAnomalyType.NONE:
                return

            if self.target.buffs.has_tag("originium_crystal"):
                self._shatter_crystal(is_ult=False)

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
                skill_name=f"毁伤序列{seq_index+1}",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL,
                attachments=[]
            )
            # 重击（第5段，索引4）造成18点失衡
            if is_heavy:
                self.target.apply_stagger(18, self.engine)

        return Action(f"毁伤序列{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.NORMAL)

    def create_skill(self):
        """战技：构成序列"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]

        def perform():
            # 造成物理伤害 + 猛击
            deal_damage(
                self.engine, self, self.target,
                skill_name="构成序列",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.SKILL,
                attachments=[PhysAnomalyType.IMPACT]
            )
            
            # 3. 施加失衡
            self.target.apply_stagger(10, self.engine)
            
            # 天赋一检测 (假设命中数)
            # targets_hit = 1
            # if targets_hit >= 2: ...

        return Action("构成序列", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.SKILL)

    def create_ult(self):
        """终结技：轰击序列"""
        f_data = FRAME_DATA["ult"]
        mv = SKILL_MULTIPLIERS["ult"]
        mv_extra = SKILL_MULTIPLIERS["ult_extra"] # 600%

        def perform():
            # 检查是否有结晶
            has_crystal = self.target.buffs.has_tag("originium_crystal")
            
            # 主伤害
            deal_damage(
                self.engine, self, self.target,
                skill_name="轰击序列",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.ULTIMATE,
                attachments=[]
            )
            
            if has_crystal:
                self.engine.log("   [终结技] 击碎源石结晶！(终结技伤害)")
                # 主动击碎，复用 _shatter_crystal 逻辑 (指定 is_ult=True)
                self._shatter_crystal(is_ult=True)
                
                # 额外伤害：吃终结技倍率和增伤
                deal_damage(
                    self.engine, self, self.target,
                    skill_name="轰击序列(额外)",
                    skill_mv=mv_extra,
                    element=Element.PHYSICAL,
                    move_type=MoveType.ULTIMATE,
                    attachments=[]
                )
            
            # 失衡
            self.target.apply_stagger(25, self.engine)

        return Action("轰击序列", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.ULTIMATE)

    def create_qte(self):
        """连携技：锁闭序列"""
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]

        def perform():
            self.engine.log("   [连携技] 冲锋并封印敌人！")
            deal_damage(
                self.engine, self, self.target,
                skill_name="锁闭序列",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.QTE,
                attachments=[]
            )
            
            # 施加源石结晶 (自带易伤)
            self.target.buffs.add_buff(OriginiumCrystalBuff(), self.engine)
            
            # 失衡
            self.target.apply_stagger(10, self.engine)

        return Action("锁闭序列", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)
