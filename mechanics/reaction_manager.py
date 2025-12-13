from core.enums import Element, PhysAnomalyType
from mechanics.buff_system import BurningBuff, ConductiveBuff, CorrosionBuff, FrozenBuff

class ReactionManager:
    def __init__(self, owner, engine):
        self.owner = owner
        self.engine = engine
        self.attachment_element = None
        self.attachment_stacks = 0
        self.phys_break_stacks = 0

    def has_magic_attachment(self):
        return self.attachment_element is not None
    
    # 安塔尔QTE效果：刷新/再次施加当前状态
    def reapply_current_status(self, attacker_atk):
        """
        如果处于法术附着或物理破防，再次施加一次同类型状态
        """
        log_msg = "无状态可刷新"
        
        # 1. 刷新法术附着
        if self.attachment_element:
            # 递归调用 apply_hit，相当于又打了一次该属性
            _, _, log = self.apply_hit(self.attachment_element, attacker_atk=attacker_atk)
            log_msg = f"刷新状态 -> {log}"
            
        # 2. 刷新物理破防
        elif self.phys_break_stacks > 0:
            _, _, log = self.apply_hit(Element.PHYSICAL, PhysAnomalyType.BREAK)
            log_msg = f"刷新状态 -> {log}"
            
        return log_msg

    def apply_hit(self, incoming_element: Element, phys_type: PhysAnomalyType = PhysAnomalyType.NONE, attacker_atk=1000):
        """
        :return: (extra_damage_mv, reaction_type, log_msg)
        """
        extra_mv = 0
        reaction_type = "none"
        log_msg = ""

        # --- 物理逻辑 ---
        if incoming_element == Element.PHYSICAL:
            if self.owner.buffs.has_tag("frozen"):
                 self.owner.buffs.consume_tag("frozen")
                 return 300, "shatter", "🧊🔨 [碎冰] 击碎冻结！"
            
            if phys_type == PhysAnomalyType.BREAK:
                self.phys_break_stacks = min(4, self.phys_break_stacks + 1)
                log_msg = f"物理破防({self.phys_break_stacks}层)"
            elif phys_type == PhysAnomalyType.IMPACT:
                if self.phys_break_stacks > 0:
                    dmg_mult = 50 * self.phys_break_stacks
                    self.phys_break_stacks = 0
                    log_msg = f"猛击结算! 额外倍率 {dmg_mult}%"
                    extra_mv += dmg_mult
            return extra_mv, "physical_anomaly", log_msg

        # --- 法术逻辑 ---
        if self.attachment_element is None:
            self.attachment_element = incoming_element
            self.attachment_stacks = 1
            return 0, "attach", f"施加 {incoming_element.value} 附着"

        if self.attachment_element == incoming_element:
            self.attachment_stacks = min(4, self.attachment_stacks + 1)
            burst_mv = 40 * self.attachment_stacks
            return burst_mv, "burst", f"法术爆发({incoming_element.value} {self.attachment_stacks}层)"

        # 异色反应
        current = self.attachment_element
        incoming = incoming_element
        
        if incoming == Element.HEAT:
            reaction_type = "burning"
            self.owner.add_buff(BurningBuff(attacker_atk * 0.2), self.engine)
        elif incoming == Element.ELECTRIC:
            reaction_type = "conductive"
            self.owner.add_buff(ConductiveBuff(), self.engine)
        elif incoming == Element.FROST:
            reaction_type = "frozen"
            self.owner.add_buff(FrozenBuff(), self.engine)
        elif incoming == Element.NATURE:
            reaction_type = "corrosion"
            self.owner.add_buff(CorrosionBuff(), self.engine)

        self.attachment_element = None
        self.attachment_stacks = 0
        
        return 0, reaction_type, f"触发反应: 【{reaction_type}】 ({current.value}+{incoming.value})"