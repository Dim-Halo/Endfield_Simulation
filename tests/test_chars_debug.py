
from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.wolfguard_sim import WolfguardSim
from entities.characters.erdila_sim import ErdilaSim

def test_char_execution():
    sim = SimEngine()
    target = DummyEnemy(sim, "Target")
    sim.entities.append(target)
    
    wg = WolfguardSim(sim, target)
    erd = ErdilaSim(sim, target)
    
    sim.entities.append(wg)
    sim.entities.append(erd)
    
    print("Testing Wolfguard...")
    wg.set_timeline([(0.5, "skill"), (2.0, "a1"), (3.0, "qte")])
    
    print("Testing Erdila...")
    erd.set_timeline([(0.5, "skill"), (2.0, "a1"), (3.0, "qte")])
    
    # Run for a bit
    for _ in range(50): # 5 seconds
        sim.tick += 1
        for entity in sim.entities:
            entity.on_tick(sim)
        
    # Check logs - SimEngine default logger prints to stdout, so we just watch the output
    print("\n--- Finished ---")

if __name__ == "__main__":
    test_char_execution()
