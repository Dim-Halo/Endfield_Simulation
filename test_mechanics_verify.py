from core.config_manager import get_config
from mechanics.buff_system import CorrosionBuff
from core.stats import Attributes, CombatStats

print("Script Start")

def test_config():
    conf = get_config()
    print(f"Conductive Base: {conf.reaction_coefficients['conductive_base_vuln']}")
    print(f"Corrosion Base: {conf.reaction_coefficients['corrosion_base_shred']}")
    
    # Check MV calculation
    mv = conf.get_reaction_mv("reaction", level=1, tech_power=0, attacker_lvl=1, is_magic=True)
    print(f"Reaction MV (Lv1, Tech0, Lvl1): {mv}")
    
    # Check Spell Level Mult
    # Lv99: 1 + 5/980 * 98 = 1 + 0.5 = 1.5
    mv_99 = conf.get_reaction_mv("reaction", level=0, tech_power=0, attacker_lvl=99, is_magic=True)
    base_mv = conf.reaction_base_mv["reaction"] # 80
    print(f"Reaction MV (Lv0, Tech0, Lvl99): {mv_99} (Expected: {80 * 1.5})")

def test_stats():
    stats = CombatStats()
    attrs = Attributes(agility=100, intelligence=100)
    
    phys_res = stats.calculate_phys_res(attrs)
    # 100 - 100/(0.1+1) = 100 - 100/1.1 = 100 - 90.909 = 9.09%
    print(f"Phys Res (Agi 100): {phys_res}")
    
    magic_res = stats.calculate_magic_res(attrs)
    print(f"Magic Res (Int 100): {magic_res}")

def test_buff():
    buff = CorrosionBuff(initial_shred=0.036, tick_shred=0.0084, max_shred=0.12)
    print(f"Corrosion Init: {buff.current_shred}")
    buff.on_tick(None, None) # 1 tick
    print(f"Corrosion Tick 1: {buff.current_shred}") 
    # Need 10 ticks for update
    for _ in range(9):
        buff.on_tick(None, None)
    print(f"Corrosion Tick 10 (1 sec): {buff.current_shred}")

if __name__ == "__main__":
    test_config()
    test_stats()
    test_buff()
