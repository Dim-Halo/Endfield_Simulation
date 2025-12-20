from entities.characters.chen_sim import ChenSim
from entities.characters.admin_sim import AdminSim
from entities.characters.guard_sim import GuardSim
from entities.characters.erdila_sim import ErdilaSim
from entities.characters.levatine_sim import LevatineSim
from entities.characters.antal_sim import AntalSim
from entities.characters.wolfguard_sim import WolfguardSim

PRESETS = {
    "物理爆发队 (陈千语/管理员/骏卫/艾尔黛拉)": {
        "description": "以陈千语重击启动，艾尔黛拉易伤辅助，管理员与骏卫双核爆发的物理队伍。",
        "target_def": 100,
        "team": [
            {
                "class": ChenSim, 
                "name": "陈千语", 
                "script": [
                    "a1", "a2", "a3", "a4", "a5",  # a5重击 -> 触发艾尔黛拉QTE
                    "wait 3.0",                    # 等待QTE连携与辅助技能
                    "ult",                         # 冽风霜 (物理大招爆发)
                    "skill",                       # 归穹宇 (击飞 -> 触发铁誓)
                    "a1", "a2"
                ]
            },
            {
                "class": ErdilaSim, 
                "name": "艾尔黛拉", 
                "script": [
                    "qte",       # 阻塞直到检测到重击 (无附着/无破防) -> 施加腐蚀
                    "skill",     # 奔腾的多利 (消耗腐蚀 -> 施加物理易伤)
                    "wait 10.0"
                ]
            },
            {
                "class": AdminSim, 
                "name": "管理员", 
                "script": [
                    "qte",       # 阻塞直到检测到队友QTE (艾尔黛拉) -> 施加封印 (持续5s)
                    # "wait 0",  # 必须立即接大招，否则封印会过期 (QTE后摇1.5s + 大招前摇3.0s = 4.5s < 5s)
                    "ult",       # 轰击序列 (击碎结晶 -> 巨额伤害)
                    "skill",     # 构成序列 (猛击 -> 触发铁誓/骏卫QTE)
                    "wait 5.0"
                ]
            },
            {
                "class": GuardSim, 
                "name": "骏卫", 
                "script": [
                    "wait 3.5",  # 等待艾尔黛拉连招完成
                    "ult",       # 盾卫旗队 (展开铁誓，准备后续追击)
                    "wait 2.0",  # 等待管理员爆发
                    "skill",     # 粉碎阵线 (碎甲 -> 触发铁誓)
                    "qte"        # 盈月邀击 (响应管理员的猛击或自身的碎甲)
                ]
            }
        ]
    }
}
