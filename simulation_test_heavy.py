
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.chen_sim import ChenSim
from simulation.event_system import EventType, Event
from core.enums import MoveType

def test_heavy_attack_event():
    print("=== Testing Heavy Attack Event Identification ===")
    
    engine = SimEngine()
    target = DummyEnemy("TestTarget", engine)
    chen = ChenSim(engine, target)
    engine.add_entity(chen)
    
    # Listener for Heavy Attacks
    def on_damage(event: Event):
        move_type = event.get("move_type")
        skill_name = event.get("skill_name")
        tick = event.tick
        
        if move_type == MoveType.HEAVY:
            print(f"[{tick:.1f}s] CAUGHT HEAVY ATTACK EVENT!")
            print(f"  Skill: {skill_name}")
            print(f"  Source: {event.source.name}")
            print(f"  Damage: {event.get('actual_damage')}")
        elif move_type == MoveType.NORMAL:
            print(f"[{tick:.1f}s] Normal Attack: {skill_name}")

    engine.event_bus.subscribe(EventType.POST_DAMAGE, on_damage)
    
    # Execute 5 normal attacks to trigger heavy attack (5th hit)
    print("\nExecuting 5 Normal Attacks...")
    for i in range(1, 6):
        action = chen.create_normal_attack(i-1)
        engine.schedule_action(chen, action)
        # Advance time enough for action to complete (approx 0.5s per hit)
        engine.update(1.0) 
        
    print("\nTest Complete.")

if __name__ == "__main__":
    test_heavy_attack_event()
