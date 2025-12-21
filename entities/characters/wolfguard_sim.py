# entities/characters/wolfguard_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, ReactionType, BuffCategory, BuffEffect
from mechanics.buff_system import Buff, BurningBuff
from .wolfguard_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage
from core.stats import CombatStats, Attributes, StatKey
from simulation.event_system import EventType

class ScorchingFangBuff(Buff):
    """狼卫天赋：灼热獠牙 - 提供伤害加成"""
    def __init__(self):
        super().__init__(
            "灼热獠牙",
            duration_sec=MECHANICS['passive_duration'],
            category=BuffCategory.BUFF,
            effect_type=BuffEffect.STAT_MODIFIER
        )
        self.bonus = MECHANICS['passive_dmg_bonus']

    def modify_stats(self, stats: dict):
        if StatKey.DMG_BONUS in stats:
            stats[StatKey.DMG_BONUS] += self.bonus


class WolfguardSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("狼卫", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=161, agility=95, intelligence=92, willpower=111)
        self.base_stats = CombatStats(base_hp=5495, base_atk=294, atk_pct=0.0)

        # 主副属性
        self.main_attr = "strength"
        self.sub_attr = "agility"
        
        # 技能CD - 移除 CD 机制
        # self.skill_cd = 120
        # self.ult_cd = 300

        # 订阅事件
        # 监听反应触发 (主要用于非 Buff 类反应，或作为补充)
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self._on_reaction_trigger)
        # 监听 Buff 施加 (主要用于燃烧、附着等 Buff)
        self.engine.event_bus.subscribe(EventType.BUFF_APPLIED, self._on_buff_applied)

    # ===== 事件监听 =====
    def _on_buff_applied(self, event):
        """监听 Buff 施加事件"""
        buff_name = event.get("buff_name")
        tags = event.get("tags", [])
        buff_instance = event.get("buff_instance")
        
        # 1. QTE触发条件：检测到元素附着 (敌人被施加燃烧/导电/冻结/腐蚀)
        # 只要敌人身上出现这些Buff，QTE就绪
        is_anomaly = False
        if ReactionType.BURNING in tags: is_anomaly = True
        elif ReactionType.CONDUCTIVE in tags: is_anomaly = True
        elif ReactionType.FROZEN in tags: is_anomaly = True
        elif ReactionType.CORROSION in tags: is_anomaly = True
        
        if is_anomaly:
            self.qte_ready_timer = 30
            self.engine.log(f"   [狼卫] 检测到元素异常Buff({buff_name})，爆裂手雷就绪！")
            
        # 2. 天赋一：灼热獠牙
        # 条件：狼卫自己触发了燃烧 (通过技能或普攻)
        # 检查是否是燃烧Buff，且来源是自己
        if ReactionType.BURNING in tags:
            # 检查来源
            source_name = "未知"
            if buff_instance and hasattr(buff_instance, 'source_name'):
                source_name = buff_instance.source_name
            
            if source_name == self.name:
                self._trigger_passive_one()

    def _on_reaction_trigger(self, event):
        """监听反应触发"""
        # 之前的逻辑已迁移到 _on_buff_applied
        # 这里保留监听 ATTACH 反应作为 QTE 的冗余触发 (防止某些情况下只触发ATTACH没生成Buff?)
        # 但通常 ATTACH 会伴随状态变化。如果题目要求只监听 Buff，我们可以移除这里。
        # 为了稳健，暂时保留 ATTACH 监听 QTE，但移除 Passive 监听。
        
        reaction_type = event.get("reaction_type")
        
        # QTE触发条件：REACTION_TRIGGERED 里的 ATTACH 也是一种附着
        if reaction_type == ReactionType.ATTACH:
            self.qte_ready_timer = 30
            self.engine.log(f"   [狼卫] 检测到元素附着(Attach反应)，爆裂手雷就绪！")

    # ===== 天赋机制 =====
    def _trigger_passive_one(self):
        """天赋一：触发灼热獠牙"""
        self.buffs.add_buff(ScorchingFangBuff(), self.engine)

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, len(mvs)-1)  # 统一使用动态计算
        mv = mvs[idx]
        f_data = frames[idx]

        def perform():
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"普攻{seq_index+1}",
                skill_mv=mv,
                element=Element.HEAT,
                move_type=MoveType.NORMAL
            )
            # 普攻第4段（索引3）造成失衡
            if seq_index == 3:
                self.target.apply_stagger(18, self.engine)

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.NORMAL)

    def create_skill(self):
        f_data = FRAME_DATA["skill"]
        events = []
        context = {"consumed": False}

        def hit_base():
            mv = SKILL_MULTIPLIERS["skill_base"]
            has_burn = self.target.buffs.consume_tag(ReactionType.BURNING)
            has_conduct = self.target.buffs.consume_tag(ReactionType.CONDUCTIVE)

            if has_burn or has_conduct:
                context["consumed"] = True
                self.engine.log(f"   [战技] 成功消耗异常状态！")
                refund = MECHANICS["skill_refund"]
                # self.cooldowns["skill"] = max(0, self.cooldowns["skill"] - refund)
                self.engine.log(f"   [天赋] CD减少 {refund/10.0}秒 (已移除CD机制)")
                # 消耗状态时不施加附着，使用新添加的 can_attach 参数
                deal_damage(
                    self.engine, self, self.target,
                    skill_name="灼热弹痕",
                    skill_mv=mv,
                    element=Element.HEAT,
                    move_type=MoveType.SKILL,
                    attachments=[]
                )
                # 移除之前的 Hack 代码
            else:
                deal_damage(
                    self.engine, self, self.target,
                    skill_name="灼热弹痕",
                    skill_mv=mv,
                    element=Element.HEAT,
                    move_type=MoveType.SKILL
                )

        def hit_extra():
            if context["consumed"]:
                mv = SKILL_MULTIPLIERS["skill_extra"]
                self.engine.log(f"   >>> [战技] 追加射击！")
                # 追加射击造成大量火伤。描述没说是否附着，通常追加攻击也是火伤。
                # 假设也会附着（除非特别说明）。
                deal_damage(
                    self.engine, self, self.target,
                    skill_name="灼热弹痕(追加)",
                    skill_mv=mv,
                    element=Element.HEAT,
                    move_type=MoveType.SKILL
                )

        events.append(DamageEvent(f_data['hit'], hit_base))
        events.append(DamageEvent(f_data['extra_hit'], hit_extra))
        return Action("灼热弹痕", f_data['total'], events)

    def create_ult(self):
        f_data = FRAME_DATA["ult"]
        events = []
        # 注意：constants里只定义了 "interval": 3, "total": 25。没有定义 "hit"。
        # 假设 hit 从第5帧开始。
        start_time = 5
        
        for i in range(5):
            def hit(idx=i):
                mv = SKILL_MULTIPLIERS["ult_hit"]
                deal_damage(
                    self.engine, self, self.target,
                    skill_name="狼之怒",
                    skill_mv=mv,
                    element=Element.HEAT,
                    move_type=MoveType.ULTIMATE
                )
                if idx == 4:
                    self.engine.log("   [终结技] 强制施加 <燃烧>")
                    burn_dmg = self.get_current_panel()['final_atk'] * 0.2
                    self.target.buffs.add_buff(BurningBuff(burn_dmg), self.engine)
                    # 强制施加也触发天赋
                    self._trigger_passive_one()
            events.append(DamageEvent(start_time + i*f_data['interval'], hit))
        return Action("狼之怒", f_data['total'], events)

    def create_qte(self):
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]

        def perform():
            self.engine.log("   [连携技] 爆裂手雷投掷！")
            deal_damage(
                self.engine, self, self.target,
                skill_name="爆裂手雷",
                skill_mv=mv,
                element=Element.HEAT,
                move_type=MoveType.QTE
            )

        return Action("爆裂手雷", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)
