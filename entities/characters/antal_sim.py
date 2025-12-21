# entities/characters/antal_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType
from mechanics.buff_system import ElementalDmgBuff, FragilityBuff, FocusDebuff
from simulation.event_system import EventType
from .antal_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage


class AntalSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("安塔尔", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=129, agility=86, intelligence=165, willpower=82)
        self.base_stats = CombatStats(base_hp=5495, base_atk=297, atk_pct=0.0)

        # 主副属性
        self.main_attr = "intelligence"
        self.sub_attr = "agility"
        
        # 技能CD - 移除 CD 机制
        # self.skill_cd = 150
        # self.ult_cd = 300
        
        # 天赋一冷却记录
        self.passive_heal_cd = {}
        
        # 订阅事件
        self.engine.event_bus.subscribe(EventType.POST_DAMAGE, self.on_damage_event)
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self.on_reaction_triggered)

    # ===== 状态管理 =====
    def on_tick(self, engine):
        super().on_tick(engine)
        # 冷却倒计时
        for name in list(self.passive_heal_cd.keys()):
            if self.passive_heal_cd[name] > 0:
                self.passive_heal_cd[name] -= 1
        
        # qte_ready_timer 已在父类处理

    def on_reaction_triggered(self, event):
        pass

    def on_damage_event(self, event):
        """监听全局伤害事件，触发天赋一"""
        # 天赋一：队伍中处于增幅状态的干员造成技能伤害时
        move_type = event.get('move_type')
        if move_type == MoveType.SKILL and hasattr(event.source, 'buffs'):
             has_amp = event.source.buffs.has_tag("electric_buff") or event.source.buffs.has_tag("heat_buff")
             if has_amp:
                 self.check_passive_heal(event.source)

    # ===== 天赋机制 =====
    def check_passive_heal(self, actor):
        """天赋一：即兴发挥 - 增幅状态下回复生命"""
        has_amp = actor.buffs.has_tag("electric_buff") or actor.buffs.has_tag("heat_buff")

        if has_amp and self.passive_heal_cd.get(actor.name, 0) == 0:
            heal = MECHANICS['passive_heal_base'] + self.attrs.strength * MECHANICS['passive_heal_scale']
            self.engine.log(f"   [天赋] 安塔尔为 {actor.name} 回复 {int(heal)} 生命")
            self.passive_heal_cd[actor.name] = MECHANICS['passive_cd']

    # ===== 伤害计算 =====
    # _deal_damage 已移除，使用 core.damage_helper.deal_damage

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, len(mvs)-1)  # 统一使用动态计算
        mv = mvs[idx]
        f_data = frames[idx]

        def perform():
            is_heavy = (seq_index == 3)
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"普攻{seq_index+1}",
                skill_mv=mv,
                element=Element.ELECTRIC,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL
            )
            # 普攻第4段（索引3）造成失衡
            if is_heavy:
                self.target.apply_stagger(15, self.engine)

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：指定研究对象"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]

        def hit():
            deal_damage(
                self.engine, self, self.target,
                skill_name="指定研究对象",
                skill_mv=mv,
                element=Element.ELECTRIC,
                move_type=MoveType.SKILL,
                attachments=[]
            )

            # 施加 Debuff
            dur = MECHANICS['skill_fragility_dur']
            val = MECHANICS['skill_fragility_val']
            self.engine.log("   [战技] 施加聚焦 & 电/火脆弱 (独立乘区)")

            # 聚焦
            self.target.buffs.add_buff(FocusDebuff(duration=dur), self.engine)
            # 脆弱
            self.target.buffs.add_buff(FragilityBuff("电磁脆弱", dur, val, "electric"), self.engine)
            self.target.buffs.add_buff(FragilityBuff("灼热脆弱", dur, val, "heat"), self.engine)

        return Action("指定研究对象", f_data['total'], [DamageEvent(f_data['hit'], hit)], move_type=MoveType.SKILL)

    def create_ult(self):
        """终结技：超频时刻"""
        f_data = FRAME_DATA["ult"]
        
        def activate():
            self.engine.log("   >>> [终结技] 全队电/火增幅！")
            dur = MECHANICS['ult_buff_dur']
            val = MECHANICS['ult_buff_val']
            
            # 给全队加增幅 (遍历 engine.entities 中有 buffs 属性的角色)
            for ent in self.engine.entities:
                if hasattr(ent, "buffs") and hasattr(ent, "attrs"): # 简单的判定是角色
                    ent.buffs.add_buff(ElementalDmgBuff("电磁增幅", dur, "electric", val), self.engine)
                    ent.buffs.add_buff(ElementalDmgBuff("灼热增幅", dur, "heat", val), self.engine)

        return Action("超频时刻", f_data['total'], [DamageEvent(f_data['hit'], activate)])

    def create_qte(self):
        """连携技：磁暴试验场"""
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]

        def perform():
            self.engine.log("   [连携技] 能量爆炸！")

            # 记录当前状态
            current_elem = self.target.reaction_mgr.attachment_element
            current_break = self.target.reaction_mgr.phys_break_stacks

            # 造成伤害
            deal_damage(
                self.engine, self, self.target,
                skill_name="磁暴试验场",
                skill_mv=mv,
                element=Element.ELECTRIC,
                move_type=MoveType.QTE,
                attachments=[]
            )
            target.apply_stagger(10, self.engine)

            # 强制恢复/再次施加状态
            if current_elem:
                self.target.reaction_mgr.apply_hit(current_elem)
                self.engine.log(f"   [连携技] 刷新/再次施加: {current_elem.value}")
            elif current_break > 0:
                # 使用 ReactionManager 记录的最后一次异常类型刷新
                last_type = self.target.reaction_mgr.last_phys_type
                if last_type and last_type != PhysAnomalyType.NONE:
                    self.target.reaction_mgr.apply_hit(Element.PHYSICAL, last_type)
                    self.engine.log(f"   [连携技] 刷新物理异常: {last_type.value}")

        return Action("磁暴试验场", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)