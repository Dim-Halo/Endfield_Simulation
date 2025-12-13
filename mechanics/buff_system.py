from typing import List, Dict

class Buff:
    def __init__(self, name, duration_sec, max_stacks=1, tags=None):
        self.name = name
        self.duration_ticks = int(duration_sec * 10)
        self.max_stacks = max_stacks
        self.stacks = 1
        self.tags = tags or []
        self.timer = 0 

    def on_apply(self, owner): pass
    def modify_stats(self, stats: Dict): pass
    
    def on_stack(self, new_buff):
        self.stacks = min(self.max_stacks, self.stacks + new_buff.stacks)
        self.duration_ticks = new_buff.duration_ticks

    def on_tick(self, owner, engine):
        self.timer += 1
        self.duration_ticks -= 1
        return self.duration_ticks <= 0

# --- 具体 Buff 实现 ---

class AtkPctBuff(Buff):
    """
    攻击力百分比Buff
    加算到 atk_pct 中
    """
    def __init__(self, name, value, duration):
        super().__init__(name, duration, tags=["buff", "atk_up"])
        self.value = value

    def modify_stats(self, stats: Dict):
        if "atk_pct" in stats:
            stats["atk_pct"] += self.value

class DoTBuff(Buff):
    def __init__(self, name, duration, damage_per_tick, interval_sec=1.0, tags=None):
        super().__init__(name, duration, max_stacks=1, tags=tags)
        self.damage = damage_per_tick
        self.interval_ticks = int(interval_sec * 10)
        self.tick_counter = 0

    def on_tick(self, owner, engine):
        is_expired = super().on_tick(owner, engine)
        self.tick_counter += 1
        if self.tick_counter >= self.interval_ticks:
            self.tick_counter = 0
            engine.log(f"   ☠️ [{self.name}] 造成 {int(self.damage)} 点持续伤害")
            if hasattr(owner, 'take_damage'):
                owner.take_damage(self.damage)
        return is_expired

class VulnerabilityBuff(Buff):
    """通用易伤Buff基类"""
    def __init__(self, name, duration, value, vuln_type="all"):
        # vuln_type: "all", "magic", "physical"
        tags = ["debuff", "vulnerability", vuln_type]
        super().__init__(name, duration, tags=tags)
        self.value = value
        self.vuln_type = vuln_type

    def modify_stats(self, stats: Dict):
        key_map = {
            "all": "vulnerability",
            "magic": "magic_vulnerability",
            "physical": "physical_vulnerability"
        }
        key = key_map.get(self.vuln_type, "vulnerability")
        if key in stats:
            stats[key] += self.value

class BurningBuff(DoTBuff):
    def __init__(self, damage_value, duration=5.0):
        super().__init__("燃烧", duration, damage_value, interval_sec=1.0, tags=["burning", "dot"])

class ConductiveBuff(Buff):
    def __init__(self, duration=10.0, vuln=0.20):
        super().__init__("导电", duration, tags=["conductive", "debuff"])
        self.vuln = vuln
    def modify_stats(self, stats: Dict):
        if "magic_vulnerability" in stats:
            stats["magic_vulnerability"] += self.vuln

class FrozenBuff(Buff):
    def __init__(self, duration=5.0):
        super().__init__("冻结", duration, tags=["frozen", "cc"])

class CorrosionBuff(Buff):
    def __init__(self, duration=10.0, res_shred=0.15):
        super().__init__("腐蚀", duration, tags=["corrosion", "debuff"])
        self.res_shred = res_shred
    def modify_stats(self, stats: Dict):
        for k in list(stats.keys()):
            if k.endswith("_res"):
                stats[k] -= self.res_shred

class BuffManager:
    def __init__(self, owner):
        self.owner = owner
        self.buffs: List[Buff] = []

    def add_buff(self, new_buff: Buff, engine=None):
        for b in self.buffs:
            if b.name == new_buff.name:
                b.on_stack(new_buff)
                if engine: engine.log(f"   (Buff) [{self.owner.name}] 刷新: {b.name} (层数:{b.stacks})")
                return
        self.buffs.append(new_buff)
        if engine: engine.log(f"   (Buff) [{self.owner.name}] 获得: {new_buff.name}")

    def tick_all(self, engine):
        active_buffs = []
        for b in self.buffs:
            if not b.on_tick(self.owner, engine):
                active_buffs.append(b)
            else:
                engine.log(f"   (Buff) [{self.owner.name}] 效果结束: {b.name}")
        self.buffs = active_buffs

    def apply_stats(self, base_stats: Dict):
        import copy
        final_stats = copy.deepcopy(base_stats)
        for b in self.buffs:
            b.modify_stats(final_stats)
        return final_stats

    def consume_tag(self, tag):
        for b in self.buffs:
            if tag in b.tags:
                self.buffs.remove(b)
                return True
        return False
        
    def has_tag(self, tag):
        return any(tag in b.tags for b in self.buffs)
    
class ElementalDmgBuff(Buff):
    """特定元素伤害加成Buff"""
    def __init__(self, name, duration, element_type: str, value: float):
        # element_type: "heat", "electric", etc.
        super().__init__(name, duration, tags=["buff", f"{element_type}_buff"])
        self.elem_key = f"{element_type}_dmg_bonus"
        self.value = value

    def modify_stats(self, stats: Dict):
        if self.elem_key in stats:
            stats[self.elem_key] += self.value

class FragilityBuff(Buff):
    """
    脆弱Buff
    作用于目标的脆弱区
    """
    def __init__(self, name, duration, value, element_type="all"):
        # element_type: "all", "heat", "electric", etc.
        tags = ["debuff", "fragility", element_type]
        super().__init__(name, duration, tags=tags)
        self.value = value
        self.element_type = element_type

    def modify_stats(self, stats: Dict):
        # 映射到 dummy.py 中定义的字段
        if self.element_type == "all":
            key = "fragility"
        else:
            key = f"{self.element_type}_fragility"
            
        if key in stats:
            stats[key] += self.value
        else:
            stats[key] = self.value # 防止字典里没定义

class FocusDebuff(Buff):
    """聚焦状态: 用于安塔尔QTE判定"""
    def __init__(self, duration=60.0):
        super().__init__("聚焦", duration, tags=["debuff", "focus"])