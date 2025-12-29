import sys
import os
import uvicorn
import pkgutil
import importlib
import inspect
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.base_actor import BaseActor
from core.enums import BuffCategory, BuffEffect, ReactionType
from core.operator_config import OperatorConfigManager
from core.weapon_system import WeaponManager
from core.weapon_effects import WeaponEffectHandler

app = FastAPI(title="Endfield Combat Simulator API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dynamic Character Loading ---
CHAR_MAP = {}
CHAR_DEFAULT_SCRIPTS = {}

# --- Operator Config Manager ---
operator_config_manager = OperatorConfigManager()

# --- Weapon Manager ---
weapon_manager = WeaponManager()
# 如果武器库为空，创建默认武器
if len(weapon_manager.get_all()) == 0:
    weapon_manager.create_default_weapons()

def load_all_characters():
    global CHAR_MAP, CHAR_DEFAULT_SCRIPTS
    CHAR_MAP = {}
    CHAR_DEFAULT_SCRIPTS = {}
    
    char_pkg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "entities", "characters")
    
    # Iterate over all modules in entities.characters
    for _, name, _ in pkgutil.iter_modules([char_pkg_path]):
        if name.endswith("_sim") and name != "base_actor":
            try:
                module = importlib.import_module(f"entities.characters.{name}")
                # Find classes that inherit from BaseActor
                for attr_name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseActor) and obj != BaseActor:
                        # Found a character class!
                        # To get the Chinese name, we ideally need to instantiate it or check a class attribute.
                        # Since instantiation requires an engine, let's try to inspect the __init__ source code 
                        # or just instantiate with a dummy engine if possible.
                        # But instantiating with None engine might crash if __init__ uses engine immediately.
                        # Let's try to look for a specific class attribute if we added one, 
                        # OR instantiate with a dummy engine.
                        
                        try:
                            # Create a dummy engine that just eats logs/events
                            class DummyEngineForInit:
                                def __init__(self):
                                    self.event_bus = type('obj', (object,), {'subscribe': lambda *args: None})()
                                    self.log = lambda *args, **kwargs: None
                            
                            # Instantiate just to get the name
                            temp_instance = obj(DummyEngineForInit(), None)
                            char_name = temp_instance.name
                            CHAR_MAP[char_name] = obj
                            
                            # Generate default script based on capabilities
                            script_lines = []
                            if hasattr(obj, 'create_skill'):
                                script_lines.append("skill")
                                script_lines.append("wait 2.0")
                            if hasattr(obj, 'create_ult'):
                                script_lines.append("ult")
                            
                            if not script_lines:
                                script_lines = ["a1", "wait 1.0", "a2"]
                                
                            CHAR_DEFAULT_SCRIPTS[char_name] = "\n".join(script_lines)
                            print(f"Loaded character: {char_name} from {name}")
                            
                        except Exception as e:
                            print(f"Failed to load character from {name}: {e}")
                            
            except Exception as e:
                print(f"Error importing module {name}: {e}")

# Load characters on startup
load_all_characters()

class TimelineAction(BaseModel):
    startTime: float
    name: str

class CharacterConfig(BaseModel):
    name: str
    script: str
    timeline: Optional[List[TimelineAction]] = None
    molten_stacks: Optional[int] = 0
    custom_attrs: Optional[Dict[str, Any]] = None  # 自定义属性覆盖
    weapon_id: Optional[str] = None  # 装备的武器ID

class OperatorConfigCreate(BaseModel):
    character_name: str
    config_name: str
    level: int
    attrs: Dict[str, int]
    base_stats: Dict[str, float]

class OperatorConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    level: Optional[int] = None
    attrs: Optional[Dict[str, int]] = None
    base_stats: Optional[Dict[str, float]] = None

class WeaponEffectModel(BaseModel):
    effect_type: str
    trigger_condition: Dict[str, Any]
    buff_stats: Dict[str, float]
    duration: float
    description: str

class WeaponCreate(BaseModel):
    name: str
    description: str
    weapon_atk: float
    stat_bonuses: Dict[str, float]
    effects: Optional[List[WeaponEffectModel]] = []

class WeaponUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    weapon_atk: Optional[float] = None
    stat_bonuses: Optional[Dict[str, float]] = None
    effects: Optional[List[WeaponEffectModel]] = None

class EnemyConfig(BaseModel):
    defense: float = 100.0
    dmg_taken_mult_physical: float = 1.0
    dmg_taken_mult_heat: float = 1.0
    dmg_taken_mult_electric: float = 1.0
    dmg_taken_mult_nature: float = 1.0
    dmg_taken_mult_frost: float = 1.0

class SimulationRequest(BaseModel):
    duration: float = 20.0
    enemy: EnemyConfig
    characters: List[CharacterConfig]

# Reusing SnapshotEngine logic from app.py but adapted for API
# We need to redefine or import SnapshotEngine. 
# Since app.py is a script, importing from it might execute it.
# Better to copy the SnapshotEngine class or move it to a shared module.
# For now, I will redefine it here to avoid side effects of importing app.py.

from collections import defaultdict

def categorize_buff(buff):
    # (Copy of categorize_buff from app.py)
    if hasattr(buff, 'tags') and ReactionType.CORROSION in buff.tags:
        return "🌐 抗性区"
    if hasattr(buff, 'effect_type'):
        if buff.effect_type == BuffEffect.DOT:
            return "🔥 DOT伤害"
        if buff.effect_type == BuffEffect.CC:
            return "❄️ 控制"
    if hasattr(buff, 'tags'):
        for tag in buff.tags:
            if tag in [ReactionType.BURNING, ReactionType.FROZEN]:
                return "🔥 元素反应"
            if tag == "focus":
                return "🎯 标记"
    if hasattr(buff, 'stat_modifiers'):
        modifiers = buff.stat_modifiers
        if "atk_pct" in modifiers: return "💪 攻击区"
        if any("fragility" in key for key in modifiers): return "🛡️ 脆弱区"
        if any("vulnerability" in key for key in modifiers): return "💔 易伤区"
        if any(key in modifiers for key in ["dmg_bonus", "heat_dmg_bonus", "electric_dmg_bonus", "normal_dmg_bonus", "skill_dmg_bonus", "ult_dmg_bonus", "qte_dmg_bonus"]): return "⚔️ 伤害加成区"
        if "amplification" in modifiers: return "📈 增幅区"
        if any(key.endswith("_res") for key in modifiers): return "🌐 抗性区"
    
    name = buff.name
    if "攻击" in name: return "💪 攻击区"
    if "脆弱" in name: return "🛡️ 脆弱区"
    if "易伤" in name or name in ["导电", "碎甲"]: return "💔 易伤区"
    if "增伤" in name or "伤害" in name: return "⚔️ 伤害加成区"
    if "腐蚀" in name: return "🌐 抗性区"
    return "📦 其他"

class SnapshotEngine(SimEngine):
    def __init__(self):
        super().__init__()
        self.history = []
        self.logs_by_tick = defaultdict(list)
        self.damage_by_tick = defaultdict(int)
        self.logs = [] 

    def log(self, message, level="INFO"):
        # 1. Process stats (Always capture damage for stats regardless of display filter)
        if "Hit造成伤害" in message or "造成伤害" in message: 
            try:
                # Attempt to extract the last number which is usually the damage value
                # Format is usually: "... Hit造成伤害 [Crit!] Value | Extra"
                # or "... 造成真实伤害 Value"
                parts = message.split()
                # Find the token that is an integer
                dmg_val = 0
                for part in reversed(parts):
                     # Handle possible trailing chars or pipe
                     clean_part = part.strip("|")
                     if clean_part.isdigit():
                         dmg_val = int(clean_part)
                         break
                if dmg_val > 0:
                    self.damage_by_tick[self.tick] += dmg_val
            except: pass

        # 2. Filter for display based on user request
        # User wants: Time, Name, Skill Execution, Damage Dealt.
        # "执行:" -> Action Start
        # "Hit造成伤害" -> Direct Skill Damage
        # Exclude: Buffs, Status, Reactions (unless dealt damage? usually reaction info is appended to damage log), Script loading, etc.
        
        is_action = "执行:" in message
        is_direct_hit = "Hit造成伤害" in message
        
        if not (is_action or is_direct_hit):
            return

        timestamp = f"[{int(self.tick/10 // 60):02}:{self.tick/10 % 60:04.1f}]"
        log_type = "info"
        if is_direct_hit: 
            log_type = "damage"
        elif is_action: 
            log_type = "action"
        
        # Clean up message if needed?
        # User asked for "Operator Name, Executed Skill, Damage Dealt"
        # The logs are already formatted as "[Name] Action..." so we just pass them through if they match.
        
        self.logs.append({"time": timestamp, "message": message, "type": log_type})
        self.logs_by_tick[self.tick].append(f"{timestamp} {message}")

    def capture_snapshot(self):
        frame_data = {
            "time_str": f"{self.tick / 10.0:.1f}s",
            "tick": self.tick,
            "damage_tick": self.damage_by_tick[self.tick],
            "sp": self.party_manager.get_sp(), # Add Party SP
            "entities": {}
        }
        for ent in self.entities:
            buff_list = []
            if hasattr(ent, "buffs"):
                for b in ent.buffs.buffs:
                    buff_list.append({
                        "name": b.name, "stacks": b.stacks,
                        "duration": b.duration_ticks / 10.0,
                        "category": categorize_buff(b),
                        "desc": getattr(b, "value", "N/A")
                    })
            action_info = None
            if hasattr(ent, "current_action") and ent.current_action:
                act = ent.current_action
                progress = ent.action_timer / act.duration if act.duration > 0 else 0
                action_info = {"name": act.name, "progress": min(1.0, progress)}
            extra_info = ""
            if hasattr(ent, "molten_stacks"): extra_info = f"熔火: {ent.molten_stacks}"
            
            frame_data["entities"][ent.name] = {
                "buffs": buff_list, "action": action_info, "extra": extra_info
            }
        self.history.append(frame_data)

    def run_with_snapshots(self, max_seconds):
        max_ticks = int(max_seconds * 10)
        self.capture_snapshot()
        for _ in range(max_ticks):
            self.tick += 1
            for entity in self.entities:
                entity.on_tick(self)
            self.capture_snapshot()

def parse_script_input(text):
    return [line.strip() for line in text.split('\n') if line.strip()]

@app.get("/characters")
async def get_characters():
    return {
        "characters": list(CHAR_MAP.keys()),
        "default_scripts": CHAR_DEFAULT_SCRIPTS
    }

@app.get("/characters/{character_name}/constants")
async def get_character_constants(character_name: str):
    """获取角色的constants数据（FRAME_DATA等）"""
    try:
        if character_name not in CHAR_MAP:
            raise HTTPException(status_code=404, detail=f"Character {character_name} not found")

        # 根据角色名找到对应的模块
        # 从CHAR_MAP反向查找模块名
        char_class = CHAR_MAP[character_name]
        module_name = char_class.__module__

        # 尝试导入对应的constants模块
        # 例如：entities.characters.levatine_sim -> entities.characters.levatine_constants
        if module_name.endswith("_sim"):
            constants_module_name = module_name.replace("_sim", "_constants")
            try:
                constants_module = importlib.import_module(constants_module_name)

                # 提取FRAME_DATA和SKILL_MULTIPLIERS
                frame_data = getattr(constants_module, "FRAME_DATA", {})
                skill_multipliers = getattr(constants_module, "SKILL_MULTIPLIERS", {})
                mechanics = getattr(constants_module, "MECHANICS", {})

                return {
                    "character_name": character_name,
                    "frame_data": frame_data,
                    "skill_multipliers": skill_multipliers,
                    "mechanics": mechanics
                }
            except ImportError:
                # 如果没有constants模块，返回空数据
                return {
                    "character_name": character_name,
                    "frame_data": {},
                    "skill_multipliers": {},
                    "mechanics": {}
                }
        else:
            raise HTTPException(status_code=500, detail="Invalid character module structure")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/characters/{character_name}/default-attrs")
async def get_character_default_attrs(character_name: str):
    """获取角色的默认属性"""
    try:
        if character_name not in CHAR_MAP:
            raise HTTPException(status_code=404, detail=f"Character {character_name} not found")

        char_class = CHAR_MAP[character_name]

        # 创建临时实例来获取默认属性
        class DummyEngineForAttrs:
            def __init__(self):
                self.event_bus = type('obj', (object,), {'subscribe': lambda *args: None})()
                self.log = lambda *args, **kwargs: None

        temp_instance = char_class(DummyEngineForAttrs(), None)

        # 提取属性
        attrs_dict = {
            "strength": temp_instance.attrs.strength,
            "agility": temp_instance.attrs.agility,
            "intelligence": temp_instance.attrs.intelligence,
            "willpower": temp_instance.attrs.willpower
        }

        base_stats_dict = {
            "level": temp_instance.base_stats.level,
            "base_hp": temp_instance.base_stats.base_hp,
            "base_atk": temp_instance.base_stats.base_atk,
            "base_def": temp_instance.base_stats.base_def,
            "technique_power": temp_instance.base_stats.technique_power
        }

        return {
            "character_name": character_name,
            "attrs": attrs_dict,
            "base_stats": base_stats_dict
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- Operator Config API Endpoints ---

@app.get("/operator-configs")
async def get_operator_configs(character_name: Optional[str] = None):
    """获取所有干员配置或指定角色的配置"""
    if character_name:
        configs = operator_config_manager.get_by_character(character_name)
    else:
        configs = operator_config_manager.get_all()
    return [config.to_dict() for config in configs]

@app.get("/operator-configs/{config_id}")
async def get_operator_config(config_id: str):
    """获取指定ID的干员配置"""
    config = operator_config_manager.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config.to_dict()

@app.post("/operator-configs")
async def create_operator_config(data: OperatorConfigCreate):
    """创建新的干员配置"""
    config = operator_config_manager.create(
        character_name=data.character_name,
        config_name=data.config_name,
        level=data.level,
        attrs=data.attrs,
        base_stats=data.base_stats
    )
    return config.to_dict()

@app.put("/operator-configs/{config_id}")
async def update_operator_config(config_id: str, data: OperatorConfigUpdate):
    """更新干员配置"""
    config = operator_config_manager.update(
        config_id=config_id,
        config_name=data.config_name,
        level=data.level,
        attrs=data.attrs,
        base_stats=data.base_stats
    )
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config.to_dict()

@app.delete("/operator-configs/{config_id}")
async def delete_operator_config(config_id: str):
    """删除干员配置"""
    success = operator_config_manager.delete(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"success": True}

# --- Weapon API Endpoints ---

@app.get("/weapons")
async def get_weapons():
    """获取所有武器"""
    weapons = weapon_manager.get_all()
    return [weapon.to_dict() for weapon in weapons]

@app.get("/weapons/{weapon_id}")
async def get_weapon(weapon_id: str):
    """获取指定ID的武器"""
    weapon = weapon_manager.get(weapon_id)
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")
    return weapon.to_dict()

@app.post("/weapons")
async def create_weapon(data: WeaponCreate):
    """创建新武器"""
    effects = [eff.dict() for eff in data.effects] if data.effects else []
    weapon = weapon_manager.create(
        name=data.name,
        description=data.description,
        weapon_atk=data.weapon_atk,
        stat_bonuses=data.stat_bonuses,
        effects=effects
    )
    return weapon.to_dict()

@app.put("/weapons/{weapon_id}")
async def update_weapon(weapon_id: str, data: WeaponUpdate):
    """更新武器"""
    effects = [eff.dict() for eff in data.effects] if data.effects else None
    weapon = weapon_manager.update(
        weapon_id=weapon_id,
        name=data.name,
        description=data.description,
        weapon_atk=data.weapon_atk,
        stat_bonuses=data.stat_bonuses,
        effects=effects
    )
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")
    return weapon.to_dict()

@app.delete("/weapons/{weapon_id}")
async def delete_weapon(weapon_id: str):
    """删除武器"""
    success = weapon_manager.delete(weapon_id)
    if not success:
        raise HTTPException(status_code=404, detail="Weapon not found")
    return {"success": True}

@app.post("/simulate")
async def run_simulation(request: SimulationRequest):
    try:
        sim = SnapshotEngine()
        
        # Setup Enemy
        from core.enums import Element
        target = DummyEnemy(sim, "测试机甲",
                            defense=request.enemy.defense,
                            resistances={
                                Element.PHYSICAL: 1.0 - request.enemy.dmg_taken_mult_physical,
                                Element.HEAT: 1.0 - request.enemy.dmg_taken_mult_heat,
                                Element.ELECTRIC: 1.0 - request.enemy.dmg_taken_mult_electric,
                                Element.NATURE: 1.0 - request.enemy.dmg_taken_mult_nature,
                                Element.FROST: 1.0 - request.enemy.dmg_taken_mult_frost
                            })
        sim.entities.append(target)
        
        # Setup Characters
        char_names = []
        for c in request.characters:
            # Skip empty slots (name="无") but keep track of them if needed for indexing
            # However, SimEngine usually just needs active entities.
            if c.name == "无":
                continue

            if c.name not in CHAR_MAP:
                continue

            char_class = CHAR_MAP[c.name]
            obj = char_class(sim, target)

            # 应用自定义属性覆盖（如果有）
            if c.custom_attrs:
                # 覆盖等级
                if c.custom_attrs.get('level'):
                    obj.base_stats.level = c.custom_attrs['level']

                # 覆盖四维属性
                if c.custom_attrs.get('attrs'):
                    for attr_name, attr_value in c.custom_attrs['attrs'].items():
                        if hasattr(obj.attrs, attr_name):
                            setattr(obj.attrs, attr_name, attr_value)

                # 覆盖基础面板
                if c.custom_attrs.get('base_stats'):
                    for stat_name, stat_value in c.custom_attrs['base_stats'].items():
                        if hasattr(obj.base_stats, stat_name):
                            setattr(obj.base_stats, stat_name, stat_value)

            # 应用武器（如果有）
            if c.weapon_id:
                weapon = weapon_manager.get(c.weapon_id)
                if weapon:
                    # 应用武器攻击力
                    obj.base_stats.weapon_atk = weapon.weapon_atk

                    # 应用属性加成
                    for stat_name, stat_value in weapon.stat_bonuses.items():
                        # 四维属性
                        if hasattr(obj.attrs, stat_name):
                            current = getattr(obj.attrs, stat_name)
                            setattr(obj.attrs, stat_name, current + int(stat_value))
                        # 基础面板属性
                        elif hasattr(obj.base_stats, stat_name):
                            current = getattr(obj.base_stats, stat_name)
                            setattr(obj.base_stats, stat_name, current + stat_value)

                    # 应用武器特殊效果
                    if weapon.effects:
                        weapon_handler = WeaponEffectHandler(obj, weapon, sim)
                        # 存储 handler 引用以便后续清理
                        if not hasattr(obj, 'weapon_handlers'):
                            obj.weapon_handlers = []
                        obj.weapon_handlers.append(weapon_handler)

            if hasattr(obj, "molten_stacks"):
                obj.molten_stacks = c.molten_stacks
                
            if c.timeline:
                # Use timeline mode
                # Filter out 'wait' actions and normalize commands
                timeline_data = []
                for t in c.timeline:
                    cmd = t.name.lower().strip()
                    # Skip explicit wait commands in timeline mode (handled by timestamps)
                    if "wait" in cmd:
                        continue
                    
                    # Normalize common Frontend issues
                    if cmd == "attack": cmd = "a1"
                    if cmd == "skill": cmd = "skill" # keep
                    if cmd == "ult": cmd = "ult"     # keep
                    if cmd == "qte": cmd = "qte"     # keep
                    
                    timeline_data.append((t.startTime, cmd))
                
                if hasattr(obj, "set_timeline"):
                    obj.set_timeline(timeline_data)
                else:
                    # Fallback to script if set_timeline not available (should be added to BaseActor)
                    obj.set_script(parse_script_input(c.script))
            else:
                obj.set_script(parse_script_input(c.script))
                
            sim.entities.append(obj)
            char_names.append(obj.name)
            
        # Run
        sim.run_with_snapshots(request.duration)
        
        # Prepare Result
        # We need to serialize the statistics manually if it's not JSON serializable
        stats_data = None
        if hasattr(sim, 'statistics'):
            stats_data = {}
            for name, cs in sim.statistics.character_stats.items():
                stats_data[name] = {
                    "name": cs.name,
                    "total_damage": cs.total_damage,
                    "skill_counts": dict(cs.skill_count) # Convert Counter to dict explicitly
                }

        # Ensure logs are serializable
        safe_logs = []
        for log in sim.logs:
            safe_logs.append({
                "time": str(log.get("time", "")),
                "message": str(log.get("message", "")),
                "type": str(log.get("type", "info"))
            })

        return {
            "history": sim.history,
            "logs": safe_logs, # sending flat logs list
            "total_dmg": target.total_damage_taken,
            "char_names": char_names,
            "statistics": stats_data
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files for frontend
web_dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist")
if os.path.exists(web_dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(web_dist_path, "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(web_dist_path, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve static files if they exist, otherwise serve index.html for SPA routing
        file_path = os.path.join(web_dist_path, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(web_dist_path, "index.html"))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
