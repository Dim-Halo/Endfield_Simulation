# entities/characters/erdila_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes
from core.enums import Element, MoveType, PhysAnomalyType, ReactionType
from mechanics.buff_system import Buff, CorrosionBuff, VulnerabilityBuff
from .erdila_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage
from simulation.event_system import EventType


class ErdilaSim(BaseActor):
    # ===== 初始化 =====
    def __init__(self, engine, target):
        super().__init__("艾尔黛拉", engine)
        self.target = target

        # 角色属性
        self.attrs = Attributes(strength=112, agility=93, intelligence=145, willpower=118)
        self.base_stats = CombatStats(base_hp=5495, base_atk=323, atk_pct=0.0)

        # 主副属性
        self.main_attr = "intelligence"
        self.sub_attr = "willpower"

        # 技能CD - 移除 CD 机制
        # self.skill_cd = 150
        # self.ult_cd = 300
        
        # 订阅事件
        self.engine.event_bus.subscribe(EventType.POST_DAMAGE, self.on_post_damage)

    # ===== 状态管理 =====
    def on_tick(self, engine):
        super().on_tick(engine)
        # qte_ready_timer 已在父类处理

    def on_post_damage(self, event):
        """监听队友的重击(Heavy Hit)以触发QTE"""
        # 连携条件: 队友触发重击
        move_type = event.get('move_type')
        source = event.source
        
        if source != self and move_type == MoveType.HEAVY:
            # 检查目标状态: 不处于破防 且 不处于法术附着
            # Event对象中包含target (防御者)
            target = event.target
            if not target:
                target = self.target # 回退到当前目标
                
            has_attach = target.reaction_mgr.has_magic_attachment()
            has_break = target.reaction_mgr.phys_break_stacks > 0
            
            if not has_attach and not has_break:
                self.qte_ready_timer = 30 # 3秒内可发动
                self.engine.log(f"   [艾尔黛拉] 检测到队友重击且目标状态符合(无附着/无破防)，火山蘑菇云就绪！")
            else:
                self.engine.log(f"   [艾尔黛拉] 检测到队友重击但目标状态不符 (Attach:{has_attach}, Break:{has_break})")

    # ===== 天赋机制 =====
    def _perform_heal(self):
        """天赋一：多利影子治疗"""
        panel = self.get_current_panel()
        wil = self.attrs.willpower

        # 公式: [基础 + 意志 * 倍率] * (1 + 治疗加成)
        base_heal = MECHANICS['heal_base'] + wil * MECHANICS['heal_scale']
        final_heal = base_heal * (1.0 + panel.get('heal_bonus', 0.0))

        self.engine.log(f"   [治疗] 艾尔黛拉回复全队 {int(final_heal)} 点生命值")

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
            # 假设第4段（索引3）是重击
            is_heavy = (seq_index == 3)
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"普攻{seq_index+1}",
                skill_mv=mv,
                element=Element.NATURE,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL
            )

        return Action(f"普攻{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：奔腾的多利"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]

        def hit():
            # 检测腐蚀
            has_corrosion = self.target.buffs.consume_tag(ReactionType.CORROSION)

            # 造成伤害
            deal_damage(
                self.engine, self, self.target,
                skill_name="奔腾的多利",
                skill_mv=mv,
                element=Element.NATURE,
                move_type=MoveType.SKILL
            )

            # 产生影子治疗
            self._perform_heal()

            # 如果消耗了腐蚀 -> 施加双脆弱
            if has_corrosion:
                self.engine.log("   [战技] 消耗腐蚀！施加物理/法术脆弱，并触发二次冲撞！")
                dur = MECHANICS['vuln_duration']
                val = MECHANICS['vuln_value']

                # 施加脆弱
                self.target.buffs.add_buff(
                    VulnerabilityBuff("物理脆弱", dur, val, vuln_type="physical"), self.engine
                )
                self.target.buffs.add_buff(
                    VulnerabilityBuff("法术脆弱", dur, val, vuln_type="magic"), self.engine
                )

                # 天赋二：山顶冲浪
                self.engine.log("   [天赋] 山顶冲浪：检测周围其他腐蚀敌人... (无目标)")

        return Action("奔腾的多利", f_data['total'], [DamageEvent(f_data['hit'], hit)], move_type=MoveType.SKILL)

    def create_qte(self):
        """连携技：火山蘑菇云"""
        f_data = FRAME_DATA["qte"]

        def hit_throw():
            self.engine.log("   [连携技] 抛出火山云...")
            deal_damage(
                self.engine, self, self.target,
                skill_name="火山蘑菇云(投掷)",
                skill_mv=SKILL_MULTIPLIERS['qte_hit'],
                element=Element.NATURE,
                move_type=MoveType.QTE
            )

        def hit_explode():
            self.engine.log("   [连携技] 蘑菇云爆炸！强制腐蚀！")
            deal_damage(
                self.engine, self, self.target,
                skill_name="火山蘑菇云(爆炸)",
                skill_mv=SKILL_MULTIPLIERS['qte_explode'],
                element=Element.NATURE,
                move_type=MoveType.QTE
            )
            # 强制施加腐蚀
            self.target.buffs.add_buff(CorrosionBuff(duration=MECHANICS['corrosion_duration']), self.engine)

        events = [
            DamageEvent(f_data['hit'], hit_throw),
            DamageEvent(f_data['explode'], hit_explode)
        ]
        return Action("火山蘑菇云", f_data['total'], events)

    def create_ult(self):
        """终结技：毛茸茸派对"""
        f_data = FRAME_DATA["ult"]
        hits = 5
        events = []

        for i in range(hits):
            def hit(idx=i):
                deal_damage(
                    self.engine, self, self.target,
                    skill_name="毛茸茸派对",
                    skill_mv=SKILL_MULTIPLIERS['ult_hit'],
                    element=Element.NATURE,
                    move_type=MoveType.ULTIMATE
                )
                # 模拟概率掉落影子治疗
                import random
                if random.random() < 0.5:
                    self._perform_heal()

            events.append(DamageEvent(i * f_data['interval'] + 2, hit))

        return Action("毛茸茸派对", f_data['total'], events, move_type=MoveType.ULTIMATE)
