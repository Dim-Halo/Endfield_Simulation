# entities/characters/dapan_sim.py
from .base_actor import BaseActor
from simulation.action import Action, DamageEvent
from core.calculator import DamageEngine
from core.stats import CombatStats, Attributes, StatKey
from core.enums import Element, MoveType, PhysAnomalyType, ReactionType, BuffCategory, BuffEffect
from mechanics.buff_system import Buff
from .dapan_constants import SKILL_MULTIPLIERS, FRAME_DATA, MECHANICS
from core.damage_helper import deal_damage
from mechanics.buff_system import Buff, UsageBuff

from simulation.event_system import EventType

class BeiLiaoBuff(Buff):
    def __init__(self, duration, max_stacks):
        super().__init__("备料", duration, max_stacks=max_stacks, category=BuffCategory.BUFF, effect_type=BuffEffect.OTHER)
        
    # 不需要 on_apply，BuffManager 已处理堆叠逻辑

class ImpactBoostBuff(UsageBuff):
    def __init__(self, value=0.2):
        super().__init__("加料猛击", 1.0, usages=1, category=BuffCategory.BUFF)
        self.boost_value = value
        
    def on_reaction_enhancement(self, reaction_result):
        # 检查是否触发了 IMPACT 且有倍率
        if reaction_result.phys_anomaly_type == PhysAnomalyType.IMPACT and reaction_result.extra_mv > 0:
            if self.boost_value > 0:
                reaction_result.extra_mv *= (1.0 + self.boost_value)
                reaction_result.log_msg += f" (猛击UP {int(self.boost_value*100)}%)"
                # 消耗一次使用次数 (自动移除)
                self.consume()

class DaPanSim(BaseActor):
    def __init__(self, engine, target):
        super().__init__("大潘", engine)
        self.target = target
        
        # 属性：力量175 敏捷96 智识94 意志102
        self.attrs = Attributes(strength=175, agility=96, intelligence=94, willpower=102)
        self.base_stats = CombatStats(base_hp=5495, base_atk=303, atk_pct=0.0)
        
        self.main_attr = "strength"
        self.sub_attr = "willpower"
        
        # 技能CD - 移除 CD 机制
        # self.skill_cd = 150
        # self.ult_cd = 300
        
        self.engine.event_bus.subscribe(EventType.REACTION_TRIGGERED, self.on_reaction_triggered)

    def on_tick(self, engine):
        super().on_tick(engine)
        # qte_ready_timer 已在父类处理
        # 备料Buff由BuffManager自动管理


    def on_reaction_triggered(self, event):
        """监听破防层数变化以触发QTE"""
        reaction_type = event.get("reaction_type")
        level = event.get("level")
        
        # 连携条件: 破防层数达到4层
        if reaction_type == ReactionType.PHYS_ANOMALY and level == 4:
            self.qte_ready_timer = 30 # 3秒
            self.engine.log(f"   [大潘] 检测到敌人4层破防，加料就绪！")

    def get_current_panel(self):
        panel = super().get_current_panel()
        
        # 天赋二：对破防敌人伤害提升
        stacks = self.target.reaction_mgr.phys_break_stacks
        if stacks > 0:
            bonus = stacks * MECHANICS["talent_2_bonus_per_stack"]
            panel[StatKey.PHYSICAL_DMG_BONUS] += bonus
            # log太频繁，略过
            
        return panel

    # ===== 技能工厂 =====
    def create_normal_attack(self, seq_index):
        mvs = SKILL_MULTIPLIERS["normal"]
        frames = FRAME_DATA["normal"]
        idx = min(seq_index, len(mvs)-1)
        mv = mvs[idx]
        f_data = frames[idx]
        
        def perform():
            is_heavy = (seq_index == 3) # 第4段是重击
            deal_damage(
                self.engine, self, self.target,
                skill_name=f"滚刀切{seq_index+1}",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.HEAVY if is_heavy else MoveType.NORMAL
            )
            if is_heavy:
                self.target.apply_stagger(20, self.engine)
                
        return Action(f"滚刀切{seq_index+1}", f_data['total'], [DamageEvent(f_data['hit'], perform)])

    def create_skill(self):
        """战技：颠勺！"""
        f_data = FRAME_DATA["skill"]
        mv = SKILL_MULTIPLIERS["skill"]
        
        def perform():
            # 造成伤害 + 击飞 (LAUNCH)
            deal_damage(
                self.engine, self, self.target,
                skill_name="颠勺！",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.SKILL,
                attachments=[PhysAnomalyType.LAUNCH]
            )
            
            # 施加失衡
            self.target.apply_stagger(10, self.engine)
            
        return Action("颠勺！", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.SKILL)

    def create_ult(self):
        """终结技：切丝入锅！"""
        f_data = FRAME_DATA["ult"]
        mv_slashes = SKILL_MULTIPLIERS["ult_slashes"]
        mv_final = SKILL_MULTIPLIERS["ult_final"]
        
        events = []
        
        # 1. 立即强制击飞 (Start)
        def start_effect():
            self.engine.log("   [终结技] 猛拍砧板，强制击飞！")
            panel = self.get_current_panel()
            self.target.reaction_mgr.apply_hit(
                Element.PHYSICAL,
                attachments=[PhysAnomalyType.LAUNCH],
                attacker_atk=panel['final_atk'],
                attacker_tech=panel['technique_power'],
                attacker_lvl=panel['level'],
                attacker_name=self.name
            )
            
        events.append(DamageEvent(0.1, start_effect))
        
        # 2. 6段连斩
        for i in range(6):
            t = f_data['slashes_start'] + i * f_data['interval']
            def slash(idx=i):
                deal_damage(
                    self.engine, self, self.target,
                    skill_name=f"切丝入锅(斩{idx+1})",
                    skill_mv=mv_slashes,
                    element=Element.PHYSICAL,
                    move_type=MoveType.ULTIMATE
                )
            events.append(DamageEvent(t, slash))
            
        # 3. 终结一击 (Knockdown + Buff)
        def final_hit():
            # 强制倒地 + 伤害
            deal_damage(
                self.engine, self, self.target,
                skill_name="切丝入锅(终结)",
                skill_mv=mv_final,
                element=Element.PHYSICAL,
                move_type=MoveType.ULTIMATE,
                attachments=[PhysAnomalyType.KNOCKDOWN]
            )
            
            # 天赋一：获得备料
            new_buff = BeiLiaoBuff(MECHANICS["talent_1_duration"], MECHANICS["talent_1_stack"])
            self.buffs.add_buff(new_buff, self.engine)
            
            # 获取当前层数用于日志
            current_buff = self.buffs.get_buff("备料")
            stacks = current_buff.stacks if current_buff else 1
            self.engine.log(f"   [天赋] 获得备料状态 (层数: {stacks})")
            
        events.append(DamageEvent(f_data['final_hit'], final_hit))
        
        return Action("切丝入锅！", f_data['total'], events, move_type=MoveType.ULTIMATE)

    def create_qte(self):
        """连携技：加料！"""
        f_data = FRAME_DATA["qte"]
        mv = SKILL_MULTIPLIERS["qte"]
        
        def perform():
            # 1. 给自己添加猛击增伤buff (一次性)
            self.buffs.add_buff(ImpactBoostBuff(MECHANICS["qte_impact_boost"]), self.engine)
            
            # 2. 造成伤害 (自动触发 IMPACT)
            deal_damage(
                self.engine, self, self.target,
                skill_name="加料！",
                skill_mv=mv,
                element=Element.PHYSICAL,
                move_type=MoveType.QTE,
                attachments=[PhysAnomalyType.IMPACT]
            )
            
            self.engine.log(f"[{self.name}] 加料！造成伤害")
            
            # 失衡
            self.target.apply_stagger(15, self.engine)
            
            # 天赋一：消耗备料刷新CD
            buff = self.buffs.get_buff("备料")
            if buff:
                buff.stacks -= 1
                self.engine.log(f"   [天赋] 消耗备料 (剩余: {buff.stacks})，QTE冷却刷新")
                
                # 如果层数为0，移除Buff
                if buff.stacks <= 0:
                    self.buffs.remove_buff("备料")
                
                # 恢复冷却/就绪状态
                # 这里假设"恢复冷却"意味着如果条件满足可以再次使用，或者单纯重置内置CD。
                # 由于QTE主要受限于条件（4层破防），而猛击会消耗层数（清零）。
                # 所以即便刷新了CD，因为破防层数归零了，也无法立即再次释放 QTE。
                # 除非有其他手段快速叠层。
                # 但根据描述 "立即恢复...冷却时间"，可能指该技能的内置CD？
                # 无论如何，我们执行消耗逻辑。
                
        return Action("加料！", f_data['total'], [DamageEvent(f_data['hit'], perform)], move_type=MoveType.QTE)
