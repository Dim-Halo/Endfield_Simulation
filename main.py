from simulation.engine import SimEngine
from entities.characters.levatine_sim import LevatineSim
from entities.characters.erdila_sim import ErdilaSim
from entities.characters.antal_sim import AntalSim
from entities.characters.admin_sim import AdminSim
from entities.characters.chen_sim import ChenSim
from entities.characters.guard_sim import GuardSim
from entities.dummy import DummyEnemy
from core.enums import Element
from simulation.presets import PRESETS

def main():
    sim = SimEngine()
    
    # 使用预设
    preset_name = "物理爆发队 (陈千语/管理员/骏卫/艾尔黛拉)"
    preset = PRESETS[preset_name]
    
    print(f"==================================================")
    print(f"       {preset_name}")
    print(f"       {preset['description']}")
    print(f"==================================================")

    # 1. 敌人初始化
    target = DummyEnemy(sim, "测试机甲-01", defense=preset.get('target_def', 100))
    sim.entities.append(target)
    target.stagger_gauge = 0 # 重置失衡
    
    # 2. 队伍初始化
    for char_data in preset['team']:
        # 实例化角色
        char_cls = char_data['class']
        char = char_cls(sim, target)
        
        # 设置脚本
        script = char_data['script']
        char.set_script(script)
        
        # 加入引擎
        sim.entities.append(char)
        print(f"[{char.name}] 就绪, 脚本长度: {len(script)}")

    # 3. 运行模拟
    sim.run(max_seconds=30)

    # 4. 统计
    total_dmg = target.total_damage_taken
    print(f"\n====== 战斗结算 ======")
    print(f"敌人承受总伤害: {int(total_dmg)}")
    print("\n" + sim.statistics.generate_report())

if __name__ == "__main__":
    main()