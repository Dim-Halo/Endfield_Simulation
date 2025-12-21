import streamlit as st
import pandas as pd
import sys
import os
import time
from collections import defaultdict
import plotly.express as px

# ==========================================
# 0. 路径与导入配置
# ==========================================
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.levatine_sim import LevatineSim
from entities.characters.wolfguard_sim import WolfguardSim
from entities.characters.erdila_sim import ErdilaSim
from entities.characters.antal_sim import AntalSim
from entities.characters.chen_sim import ChenSim
from entities.characters.admin_sim import AdminSim
from entities.characters.guard_sim import GuardSim
from core.enums import BuffCategory, BuffEffect, ReactionType
from simulation.presets import PRESETS

# ==========================================
# 1. 样式与辅助函数
# ==========================================
def categorize_buff(buff):
    """
    根据Buff类型和stat_modifiers精确分类到伤害乘区

    对应14个伤害乘区：
    1. 基础伤害区 → 2. 暴击区 → 3. 伤害加成区 → 4. 伤害减免区 →
    5. 易伤区 → 6. 增幅区 → 7. 庇护区 → 8. 脆弱区 → 9. 防御区 →
    10. 失衡易伤区 → 11. 减伤区 → 12. 抗性区 → 13. 非主控减伤区 → 14. 特殊加成区
    """
    # 1. 特殊处理：腐蚀归类到抗性区
    if hasattr(buff, 'tags') and ReactionType.CORROSION in buff.tags:
        return "🌐 抗性区"

    # 2. 检查effect_type - DOT和CC优先识别
    if hasattr(buff, 'effect_type'):
        if buff.effect_type == BuffEffect.DOT:
            return "🔥 DOT伤害"
        if buff.effect_type == BuffEffect.CC:
            return "❄️ 控制"

    # 3. 检查特殊tags（元素反应）
    if hasattr(buff, 'tags'):
        for tag in buff.tags:
            if tag in [ReactionType.BURNING, ReactionType.FROZEN]:
                return "🔥 元素反应"
            if tag == "focus":
                return "🎯 标记"

    # 4. 检查stat_modifiers（对于StatModifierBuff及其子类）
    if hasattr(buff, 'stat_modifiers'):
        modifiers = buff.stat_modifiers

        # 攻击区 (基础伤害)
        if "atk_pct" in modifiers:
            return "💪 攻击区"

        # 脆弱区 (第8位)
        if any("fragility" in key for key in modifiers):
            return "🛡️ 脆弱区"

        # 易伤区 (第5位)
        if any("vulnerability" in key for key in modifiers):
            return "💔 易伤区"

        # 伤害加成区 (第3位) - dmg_bonus, 元素增伤, 招式增伤
        if any(key in modifiers for key in ["dmg_bonus", "heat_dmg_bonus", "electric_dmg_bonus",
                                             "frost_dmg_bonus", "nature_dmg_bonus", "physical_dmg_bonus",
                                             "normal_dmg_bonus", "skill_dmg_bonus", "ult_dmg_bonus", "qte_dmg_bonus"]):
            return "⚔️ 伤害加成区"

        # 增幅区 (第6位)
        if "amplification" in modifiers:
            return "📈 增幅区"

        # 抗性区 (第12位) - 通过检查是否有_res结尾的键
        if any(key.endswith("_res") for key in modifiers):
            return "🌐 抗性区"

    # 5. 根据buff名称fallback判断
    name = buff.name
    if "攻击" in name:
        return "💪 攻击区"
    if "脆弱" in name:
        return "🛡️ 脆弱区"
    if "易伤" in name or name in ["导电", "碎甲"]:
        return "💔 易伤区"
    if "增伤" in name or "伤害" in name:
        return "⚔️ 伤害加成区"
    if "腐蚀" in name:
        return "🌐 抗性区"

    return "📦 其他"

def get_buff_style(category):
    """返回不同buff分类的颜色"""
    colors = {
        # 核心伤害乘区
        "💪 攻击区": "#00b894",        # 绿色 - 基础伤害
        "⚔️ 伤害加成区": "#0984e3",    # 蓝色 - 增伤
        "💔 易伤区": "#ffa500",        # 橙色 - 易伤
        "🛡️ 脆弱区": "#ff4b4b",        # 红色 - 脆弱
        "📈 增幅区": "#6c5ce7",        # 紫色 - 增幅
        "🌐 抗性区": "#fd79a8",        # 粉色 - 抗性削减

        # 特殊状态
        "🔥 DOT伤害": "#d63031",       # 深红 - 持续伤害
        "🔥 元素反应": "#e17055",      # 橙红 - 反应
        "❄️ 控制": "#74b9ff",          # 浅蓝 - 控制
        "🎯 标记": "#fdcb6e",          # 黄色 - 标记
        "📦 其他": "#636e72"           # 灰色 - 其他
    }
    return colors.get(category, "#636e72")

def parse_script_input(text):
    return [line.strip() for line in text.split('\n') if line.strip()]

# ==========================================
# 2. 引擎升级：捕获动作状态
# ==========================================
class SnapshotEngine(SimEngine):
    def __init__(self):
        super().__init__()
        self.history = []
        self.logs_by_tick = defaultdict(list)
        self.damage_by_tick = defaultdict(int)
        self.logs = [] 

    def log(self, message):
        # 记录日志
        timestamp = f"[{int(self.tick/10 // 60):02}:{self.tick/10 % 60:04.1f}]"
        
        log_type = "info"
        if "Hit造成伤害" in message: 
            log_type = "damage"
            try:
                # 提取伤害值用于实时显示
                dmg_val = int(message.split(":")[-1].strip())
                self.damage_by_tick[self.tick] += dmg_val
            except: pass
        elif "触发反应" in message: log_type = "reaction"
        elif "Buff" in message: log_type = "buff"
        elif "施加" in message: log_type = "status"
        
        self.logs.append({"time": timestamp, "message": message, "type": log_type})
        self.logs_by_tick[self.tick].append(f"{timestamp} {message}")

    def capture_snapshot(self):
        frame_data = {
            "time_str": f"{self.tick / 10.0:.1f}s",
            "tick": self.tick,
            "damage_tick": self.damage_by_tick[self.tick],
            "entities": {}
        }
        
        for ent in self.entities:
            # 1. Buff 快照
            buff_list = []
            if hasattr(ent, "buffs"):
                for b in ent.buffs.buffs:
                    buff_list.append({
                        "name": b.name, "stacks": b.stacks,
                        "duration": b.duration_ticks / 10.0,
                        "category": categorize_buff(b),
                        "desc": getattr(b, "value", "N/A")
                    })
            
            # 2. 动作快照
            action_info = None
            if hasattr(ent, "current_action") and ent.current_action:
                act = ent.current_action
                progress = ent.action_timer / act.duration if act.duration > 0 else 0
                action_info = {
                    "name": act.name,
                    "progress": min(1.0, progress)
                }

            # 3. 额外信息
            extra_info = ""
            if hasattr(ent, "molten_stacks"): extra_info = f"熔火: {ent.molten_stacks}"
            
            frame_data["entities"][ent.name] = {
                "buffs": buff_list,
                "action": action_info,
                "extra": extra_info
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

# ==========================================
# 3. 界面配置
# ==========================================
st.set_page_config(page_title="终末地战斗模拟器", layout="wide")

CHAR_MAP = { 
    "无": None, 
    "莱瓦汀": LevatineSim, 
    "狼卫": WolfguardSim, 
    "艾尔黛拉": ErdilaSim, 
    "安塔尔": AntalSim,
    "陈千语": ChenSim,
    "管理员": AdminSim,
    "骏卫": GuardSim
}
DEFAULT_SCRIPTS = {
    "莱瓦汀": "wait 8.5\nult\nwait 0.5\na1\nwait 0.5\nskill",
    "狼卫": "wait 11.4\nqte\nwait 2.0\nskill",
    "艾尔黛拉": "wait 4.0\nqte\nwait 1.5\nskill",
    "安塔尔": "skill\nwait 0.5\nult",
    "陈千语": "a5\nwait 3.0\nult\nskill",
    "管理员": "qte\nwait 1.5\nult\nskill",
    "骏卫": "wait 3.5\nult\nwait 2.0\nskill\nqte"
}

# ==========================================
# 4. 侧边栏
# ==========================================
st.sidebar.title("⚙️ 模拟设置")
sim_duration = st.sidebar.slider("时长", 5, 60, 20)
st.sidebar.write("🎯 **靶子属性**")
enemy_def = st.sidebar.number_input("防御", value=100)
res_heat = st.sidebar.slider("灼热抗性", -1.0, 1.0, 0.0, 0.1)
res_elec = st.sidebar.slider("电磁抗性", -1.0, 1.0, 0.0, 0.1)
res_nature = st.sidebar.slider("自然抗性", -1.0, 1.0, 0.0, 0.1)

# --- 预设选择器 (Sidebar) ---
st.sidebar.divider()
preset_options = ["自定义"] + list(PRESETS.keys())
selected_preset = st.sidebar.selectbox("📥 加载队伍预设", preset_options)

st.title("🎬 终末地战斗排轴演示")

preset_data = None
if selected_preset != "自定义":
    preset_data = PRESETS[selected_preset]
    st.info(f"**当前预设**: {selected_preset}\n\n{preset_data['description']}")

with st.expander("📝 编队与脚本", expanded=True):
    cols = st.columns(4)
    selected_chars = []
    
    # 如果选择了预设，从预设加载
    if preset_data:
        team_data = preset_data['team']
        for i in range(4):
            with cols[i]:
                if i < len(team_data):
                    char_info = team_data[i]
                    c_name = char_info['name']
                    c_cls = char_info['class']
                    # 将列表脚本转换为文本
                    script_text = "\n".join(char_info['script'])
                    
                    st.text_input(f"位置 {i+1}", value=c_name, disabled=True, key=f"p_name_{i}")
                    script = st.text_area("脚本", value=script_text, height=150, key=f"p_s_{i}")
                    
                    selected_chars.append({"class": c_cls, "script": script, "stacks": 0, "name": c_name})
                else:
                    st.text_input(f"位置 {i+1}", value="无", disabled=True, key=f"p_name_{i}")
    else:
        # 自定义模式
        for i in range(4):
            with cols[i]:
                idx = i + 1 if i < 4 else 0
                c_name = st.selectbox(f"位置 {i+1}", list(CHAR_MAP.keys()), index=idx, key=f"c_{i}")
                if c_name != "无":
                    script = st.text_area("脚本", value=DEFAULT_SCRIPTS.get(c_name, ""), height=100, key=f"s_{i}")
                    stacks = 0
                    if "莱瓦汀" in c_name: stacks = st.number_input("熔火", 0, 4, 3, key=f"st_{i}")
                    selected_chars.append({"class": CHAR_MAP[c_name], "script": script, "stacks": stacks, "name": c_name})

# --- 数据预处理：生成甘特图 ---
def build_gantt_data(history, char_names):
    data_list = []
    active_actions = {name: None for name in char_names} 
    
    for frame in history:
        time_sec = frame['tick'] / 10.0
        for name, data in frame['entities'].items():
            if name not in char_names: continue
            current_act_name = data['action']['name'] if data['action'] else None
            last_record = active_actions[name]
            
            if current_act_name:
                if last_record is None or last_record['action'] != current_act_name:
                    if last_record:
                        data_list.append({
                            "Task": name, "Start": last_record['start'], "Finish": time_sec, 
                            "Resource": last_record['action'], "Duration": time_sec - last_record['start']
                        })
                    active_actions[name] = {'action': current_act_name, 'start': time_sec}
            else:
                if last_record:
                    data_list.append({
                        "Task": name, "Start": last_record['start'], "Finish": time_sec, 
                        "Resource": last_record['action'], "Duration": time_sec - last_record['start']
                    })
                    active_actions[name] = None
    
    final_time = history[-1]['tick'] / 10.0
    for name, record in active_actions.items():
        if record:
            data_list.append({
                "Task": name, "Start": record['start'], "Finish": final_time, 
                "Resource": record['action'], "Duration": final_time - record['start']
            })
            
    return pd.DataFrame(data_list)

# --- 运行逻辑 ---
if st.button("🚀 生成时间轴", type="primary", use_container_width=True):
    sim = SnapshotEngine()
    
    # 确保 statistics 模块被初始化 (依赖 SimEngine 的 __init__)
    # 如果你的 SimEngine 没有自动创建 statistics，这里最好手动检查一下
    # 但根据之前的上下文，SimEngine 应该已经集成了 ConfigManager 和 Statistics
    
    target = DummyEnemy(sim, "测试机甲", defense=enemy_def, resistances={"heat": res_heat, "electric": res_elec, "nature": res_nature})
    sim.entities.append(target)
    
    chars = []
    real_char_names = []
    for c in selected_chars:
        obj = c["class"](sim, target)
        if hasattr(obj, "molten_stacks"): obj.molten_stacks = c["stacks"]
        obj.set_script(parse_script_input(c["script"]))
        sim.entities.append(obj)
        chars.append(obj)
        real_char_names.append(obj.name)
        
    sim.run_with_snapshots(sim_duration)
    
    st.session_state['data'] = {
        'history': sim.history,
        'logs': sim.logs_by_tick,
        'gantt': build_gantt_data(sim.history, real_char_names),
        'total_dmg': target.total_damage_taken,
        'char_names': real_char_names,
        # 保存统计对象以便画饼图
        'statistics': sim.statistics if hasattr(sim, 'statistics') else None
    }

# ==========================================
# 6. 核心显示区
# ==========================================
if 'data' in st.session_state:
    data = st.session_state['data']
    history = data['history']
    
    tab_play, tab_gantt, tab_stat = st.tabs(["▶️ 实时播放", "📅 全局时间轴", "📊 数据统计"])
    
    # --- Tab 1: 自动播放器 ---
    with tab_play:
        col_ctrl, col_info = st.columns([1, 2.5]) 
        
        # --- 左侧：控制台 ---
        with col_ctrl:
            st.markdown("### 🎮 控制台")
            is_playing = st.toggle("自动播放", value=False)
            playback_speed = st.select_slider("速度", options=[0.5, 1.0, 2.0, 5.0], value=1.0)
            
            if not is_playing:
                frame_idx = st.slider("时间轴", 0, len(history)-1, 0)
            else:
                frame_idx = 0 

        # --- 右侧：乘区监控表 ---
        with col_info:
            buff_table_placeholder = st.empty()

        # --- 下方：主监控画面 ---
        monitor_container = st.empty()
        
        if not is_playing:
            render_frames = [frame_idx]
        else:
            render_frames = range(len(history))

        last_dmg_text = ""
        dmg_display_timer = 0 

        # === 循环渲染 ===
        for f_idx in render_frames:
            frame = history[f_idx]
            
            # -------------------------------------------------
            # 【核心逻辑重写】：按伤害乘区分类收集 Buff 名称
            # -------------------------------------------------
            # 1. 初始化6个主要乘区的列表（按伤害计算流程排序）
            buff_columns = {
                "💪 攻击/暴击": [],        # 第1-2位：基础伤害区、暴击区
                "⚔️ 伤害加成": [],         # 第3位：伤害加成区
                "💔 易伤/脆弱": [],        # 第5+8位：易伤区、脆弱区
                "📈 增幅/抗性": [],        # 第6+12位：增幅区、抗性区
                "🔥 DOT/反应": [],         # 元素反应、持续伤害
                "🎯 标记/其他": []         # 其他状态
            }

            # 2. 遍历所有人，收集 Buff
            for name, entity_data in frame['entities'].items():
                if not entity_data['buffs']: continue

                for b in entity_data['buffs']:
                    # 确定放入哪一列（根据category映射到合并后的列）
                    raw_cat = b['category']
                    target_col = "🎯 标记/其他"  # 默认

                    if raw_cat in ["💪 攻击区"]:
                        target_col = "💪 攻击/暴击"
                    elif raw_cat in ["⚔️ 伤害加成区"]:
                        target_col = "⚔️ 伤害加成"
                    elif raw_cat in ["💔 易伤区", "🛡️ 脆弱区"]:
                        target_col = "💔 易伤/脆弱"
                    elif raw_cat in ["📈 增幅区", "🌐 抗性区"]:
                        target_col = "📈 增幅/抗性"
                    elif raw_cat in ["🔥 DOT伤害", "🔥 元素反应", "❄️ 控制"]:
                        target_col = "🔥 DOT/反应"

                    # 拼接名称与层数 (格式: 名称 *层数)
                    display_name = b['name']
                    if b['stacks'] > 1:
                        display_name += f" ×{b['stacks']}"

                    buff_columns[target_col].append(display_name)
            
            # -------------------------------------------------
            # 【构建对齐的 DataFrame】
            # -------------------------------------------------
            # 找出最长的一列，用于补齐空字符串，否则 DataFrame 会报错
            max_len = max([len(col) for col in buff_columns.values()] + [0])
            
            # 补齐短的列
            for col in buff_columns:
                curr_len = len(buff_columns[col])
                if curr_len < max_len:
                    buff_columns[col].extend([""] * (max_len - curr_len))
            
            # -------------------------------------------------
            # 【渲染表格】
            # -------------------------------------------------
            with buff_table_placeholder.container():
                # 如果最大长度为0，说明没有任何Buff
                if max_len > 0:
                    df_buffs = pd.DataFrame(buff_columns)
                    st.markdown("##### 📊 伤害乘区监控（按14乘区分类）")
                    st.dataframe(
                        df_buffs,
                        hide_index=True,
                        use_container_width=True,
                        height=200
                    )
                else:
                    st.markdown("##### 📊 伤害乘区监控（按14乘区分类）")
                    st.info("当前场上无生效 Buff")

            # -------------------------------------------------
            # 【渲染画面】 (保持不变)
            # -------------------------------------------------
            if frame['damage_tick'] > 0:
                last_dmg_text = f"💥 -{frame['damage_tick']}"
                dmg_display_timer = 10 
            
            with monitor_container.container():
                c1, c2 = st.columns([1, 5])
                c1.markdown(f"### ⏱️ `{frame['time_str']}`")
                
                if dmg_display_timer > 0:
                    c2.markdown(f"<h3 style='color:#d63031'>{last_dmg_text}</h3>", unsafe_allow_html=True)
                    dmg_display_timer -= 1
                else:
                    c2.write("")

                st.divider()
                
                cols = st.columns(len(data['char_names']) + 1)
                all_ents = [name for name in data['char_names']] + ["测试机甲"]
                
                for i, name in enumerate(all_ents):
                    ent_data = frame['entities'].get(name)
                    if not ent_data: continue
                    with cols[i]:
                        is_enemy = "机甲" in name
                        icon = "👹" if is_enemy else "🧑‍🚀"
                        st.markdown(f"**{icon} {name}**")
                        if ent_data['extra']: st.caption(ent_data['extra'])
                        
                        act = ent_data['action']
                        if act:
                            prog = act['progress'] * 100
                            st.markdown(
                                f"""<div style="background-color:#dfe6e9; border-radius:4px; height:24px; width:100%; position:relative;">
                                    <div style="background-color:#0984e3; width:{prog}%; height:100%; border-radius:4px;"></div>
                                    <span style="position:absolute; left:5px; top:2px; font-size:12px; color:#2d3436; font-weight:bold;">{act['name']}</span>
                                </div>""", unsafe_allow_html=True
                            )
                        else:
                            st.markdown(f"""<div style="height:24px; background-color:#f1f2f6; color:gray; font-size:12px; padding:4px;">空闲</div>""", unsafe_allow_html=True)
                        
                        st.write("")
                        if ent_data['buffs']:
                            for b in ent_data['buffs']:
                                color = get_buff_style(b['category'])
                                duration_text = f"{b['duration']:.1f}s"
                                st.markdown(
                                    f"""<div style="
                                        border-left: 3px solid {color}; 
                                        padding-left: 5px; 
                                        padding-right: 5px;
                                        margin-bottom: 2px; 
                                        font-size: 0.8em; 
                                        background-color: #f8f9fa;
                                        display: flex;
                                        justify-content: space-between;
                                        align-items: center;
                                    ">
                                        <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 65%;">
                                            {b['name']} <small style="color:#636e72">x{b['stacks']}</small>
                                        </span>
                                        <span style="font-family: monospace; font-weight: bold; color: #2d3436; font-size: 0.9em;">
                                            {duration_text}
                                        </span>
                                    </div>""", 
                                    unsafe_allow_html=True
                                )

                st.divider()
                logs = data['logs'].get(frame['tick'], [])
                if logs:
                    for l in logs[-3:]: st.caption(l)
            
            if is_playing:
                time.sleep(0.1 / playback_speed)
                if f_idx == len(history) - 1: is_playing = False

    # --- Tab 2: 全局时间轴 (Gantt) ---
    with tab_gantt:
        st.markdown("### 📅 四条行动轴总览")
        if not data['gantt'].empty:
            df_gantt = data['gantt']
            
            # 1. 定义类型映射逻辑 (保持不变)
            def get_type(res):
                if not res: return "其他"
                res = res.lower()
                if "wait" in res or "等待" in res: return "等待"
                if "a" in res or "普攻" in res: return "普攻" # a1, a2 etc
                if "skill" in res or "战技" in res or "弹痕" in res or "研究" in res or "多利" in res or "荆棘" in res: return "战技"
                if "ult" in res or "魔剑" in res or "超频" in res or "派对" in res or "怒" in res: return "终结技"
                if "qte" in res or "手雷" in res or "蘑菇" in res or "磁暴" in res: return "连携技"
                return "其他"
            
            df_gantt['Type'] = df_gantt['Resource'].apply(get_type)
            
            # 2. 【新增】创建一个用于显示的 Label 列
            # 如果是"等待"类型，标签设为空字符串，避免图表杂乱；否则显示具体的 Resource (动作名)
            df_gantt['Label'] = df_gantt.apply(lambda x: "" if x['Type'] == '等待' else x['Resource'], axis=1)

            # 3. 绘图配置
            fig = px.bar(
                df_gantt, 
                base="Start", 
                x="Duration", 
                y="Task", 
                color="Type", 
                orientation='h',
                text="Label",  # <--- 【关键修改】指定要显示的文本列
                hover_data=["Resource", "Start", "Finish"],
                color_discrete_map={
                    "普攻": "#b2bec3", "战技": "#0984e3", "终结技": "#d63031", 
                    "连携技": "#fdcb6e", "等待": "rgba(0,0,0,0)", "其他": "#636e72"
                }
            )
            
            # 4. 样式微调：设置文字位置和大小，确保文字在条形内部
            fig.update_traces(
                textposition='inside',      # 文字显示在条形内部
                insidetextanchor='middle',  # 文字居中
                textfont_size=10,           # 字体大小
                textfont_color='white'      # 字体颜色（在深色条形上更清晰）
            )

            fig.update_layout(
                xaxis_title="时间 (秒)", 
                yaxis_title="", 
                showlegend=True, 
                height=400, 
                xaxis=dict(tickmode='linear', tick0=0, dtick=1.0)
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无动作数据。")

    # --- Tab 3: 数据统计 (恢复饼图) ---
    with tab_stat:
        st.metric("总伤害", f"{int(data['total_dmg']):,}")
        
        stats_obj = data.get('statistics')
        if stats_obj:
            st.markdown("#### 伤害占比")
            # 从 statistics 对象中提取数据
            char_stats = stats_obj.character_stats
            
            if char_stats:
                pie_data = {
                    "角色": [cs.name for cs in char_stats.values()],
                    "伤害": [cs.total_damage for cs in char_stats.values()]
                }
                fig = px.pie(pie_data, values='伤害', names='角色', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
                
                # 详细数据表
                st.markdown("#### 详细数据")
                rows = []
                for cs in char_stats.values():
                    rows.append({
                        "角色": cs.name,
                        "总伤": int(cs.total_damage),
                        "占比": f"{cs.total_damage / data['total_dmg'] * 100:.1f}%" if data['total_dmg']>0 else "0%"
                    })
                st.dataframe(pd.DataFrame(rows), hide_index=True)
            else:
                st.warning("无伤害数据记录")
        else:
            st.warning("未找到统计模块数据，请确保 SimEngine 正确集成了 Statistics。")