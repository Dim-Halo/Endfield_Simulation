from simulation.engine import SimEngine
from entities.characters.levatine_sim import LevatineSim
from entities.characters.wolfguard_sim import WolfguardSim
from entities.characters.erdila_sim import ErdilaSim
from entities.characters.antal_sim import AntalSim
from entities.dummy import DummyEnemy
from core.enums import Element

def main():
    sim = SimEngine()
    
    # 1. 敌人初始化 (稍微加点防御看减伤效果，无抗性)
    target = DummyEnemy(sim, "测试机甲-01", defense=800, resistances={"heat": 0.0, "nature": 0.0, "electric": 0.0})
    
    # 2. 四人小队集结
    antal = AntalSim(sim, target)   # 辅助/副C
    erdila = ErdilaSim(sim, target) # 易伤辅助
    leva = LevatineSim(sim, target) # 主C
    wolf = WolfguardSim(sim, target) # 收割副C
    
    sim.entities.extend([antal, erdila, leva, wolf, target])

    # ==========================================
    # 剧本编排：核爆流水线
    # ==========================================

    # --- 安塔尔 (Antal) 剧本 ---
    # T=0.0: 战技起手，施加【聚焦】+【电/火脆弱(14%独立乘区)】
    # T=2.5: 终结技，全队【电/火增伤(28%)】
    antal_script = [
        "skill",
        "wait 0.5",
        "ult"
    ]

    # --- 艾尔黛拉 (Erdila) 剧本 ---
    # T=4.0: 此时敌人只有Debuff无附着，触发QTE【火山蘑菇云】-> 施加【腐蚀】
    # T=6.0: 战技【奔腾的多利】消耗腐蚀 -> 施加【法术易伤(25%)】
    erdila_script = [
        "wait 4.0",
        "qte",
        "wait 1.5",
        "skill"
    ]

    # --- 莱瓦汀 (Levatine) 剧本 ---
    # 预设：模拟进场前已经叠了3层 (为了演示第一波直接核爆)
    leva.molten_stacks = 3
    
    # T=8.5: 进场，吃到所有Buff，开启终结技【魔剑解放】(自身强化)
    # T=11.0: 普攻A1，施加【Heat附着】(享受全额易伤+脆弱+增幅)
    # T=12.0: 战技【灼热荆棘】(命中+1层=4层) -> 触发【熔火核爆】 -> 强制【燃烧】
    leva_script = [
        "wait 8.5",
        "ult",
        "wait 0.5", # 等变身动画
        "a1",
        "wait 0.5", # 确认附着生效
        "skill"
    ]

    # --- 狼卫 (Wolfguard) 剧本 ---
    # T=11.5: 看到莱瓦汀挂了火，触发QTE【爆裂手雷】(蹭伤害)
    # T=14.0: 看到莱瓦汀战技挂了燃烧，释放战技【灼热弹痕】 -> 消耗燃烧 -> 追加射击
    wolf_script = [
        "wait 11.4", # 稍微卡在莱瓦汀普攻后
        "qte",
        "wait 2.0",  # 等莱瓦汀打完核爆
        "skill"
    ]

    # 装载剧本
    antal.set_script(antal_script)
    erdila.set_script(erdila_script)
    leva.set_script(leva_script)
    wolf.set_script(wolf_script)

    print(f"==================================================")
    print(f"       终末地 四人小队 极致爆发轴模拟")
    print(f"       安塔尔 -> 艾尔黛拉 -> 莱瓦汀 -> 狼卫")
    print(f"==================================================")
    
    sim.run(max_seconds=18)

    # 统计伤害
    total_dmg = target.total_damage_taken
    print(f"\n====== 战斗结算 ======")
    print(f"敌人承受总伤害: {int(total_dmg)}")
    # 这里的 total_damage_taken 是简单的累加，你可以给 BaseActor 加个 damage_dealt 属性来统计个人伤害

if __name__ == "__main__":
    main()