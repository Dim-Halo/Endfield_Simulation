import streamlit as st
import pandas as pd
import re
import sys
import os

# 确保能导入本地模块
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from entities.characters.levatine_sim import LevatineSim
from entities.characters.wolfguard_sim import WolfguardSim
from entities.characters.erdila_sim import ErdilaSim
from entities.characters.antal_sim import AntalSim
from core.enums import Element

# ==========================================
# 1. 适配层：重写引擎以捕获日志
# ==========================================
class StreamlitEngine(SimEngine):
    def __init__(self):
        super().__init__()
        self.logs = [] # 存储结构化日志
        self.raw_logs = [] # 存储纯文本

    def log(self, message):
        seconds = self.tick / 10.0
        timestamp = f"[{int(seconds // 60):02}:{seconds % 60:04.1f}]"
        full_msg = f"{timestamp} {message}"
        
        self.raw_logs.append(full_msg)
        
        # 简单的日志分类 (用于后续可能的颜色高亮)
        log_type = "info"
        if "Hit造成伤害" in message: log_type = "damage"
        elif "触发反应" in message: log_type = "reaction"
        elif "Buff" in message: log_type = "buff"
        elif "施加" in message: log_type = "status"
        
        self.logs.append({
            "time": timestamp,
            "message": message,
            "type": log_type
        })

# ==========================================
# 2. 界面配置与工具函数
# ==========================================
st.set_page_config(page_title="终末地战斗模拟器", layout="wide")

CHAR_MAP = {
    "无": None,
    "莱瓦汀 (Levatine)": LevatineSim,
    "狼卫 (Wolfguard)": WolfguardSim,
    "艾尔黛拉 (Erdila)": ErdilaSim,
    "安塔尔 (Antal)": AntalSim
}

# 预设剧本 (为了方便用户)
DEFAULT_SCRIPTS = {
    "莱瓦汀 (Levatine)": "wait 8.5\nult\nwait 0.5\na1\nwait 0.5\nskill",
    "狼卫 (Wolfguard)": "wait 11.4\nqte\nwait 2.0\nskill",
    "艾尔黛拉 (Erdila)": "wait 4.0\nqte\nwait 1.5\nskill",
    "安塔尔 (Antal)": "skill\nwait 0.5\nult"
}

def parse_script_input(text):
    """将文本框内容转换为列表"""
    lines = text.split('\n')
    return [line.strip() for line in lines if line.strip()]

# ==========================================
# 3. 侧边栏：全局设置
# ==========================================
st.sidebar.title("⚙️ 模拟设置")

sim_duration = st.sidebar.slider("模拟时长 (秒)", 5, 60, 20)

st.sidebar.subheader("🎯 敌人属性")
enemy_def = st.sidebar.number_input("物抗", value=800)
res_heat = st.sidebar.slider("灼热抗性", -1.0, 1.0, 0.0, 0.1)
res_elec = st.sidebar.slider("电磁抗性", -1.0, 1.0, 0.0, 0.1)
res_nature = st.sidebar.slider("自然抗性", -1.0, 1.0, 0.0, 0.1)
res_frost = st.sidebar.slider("冰霜抗性", -1.0, 1.0, 0.0, 0.1)

# ==========================================
# 4. 主界面：小队配置
# ==========================================
st.title("⚔️ 终末地战斗排轴模拟器")

st.info("提示：直接在下方文本框输入指令，支持 `wait 0.5`, `a1`, `skill`, `ult`, `qte`。")

cols = st.columns(4)
selected_chars = []

# 创建4个位置的配置卡片
for i in range(4):
    with cols[i]:
        st.markdown(f"### 位置 {i+1}")
        char_name = st.selectbox(f"选择干员 #{i+1}", list(CHAR_MAP.keys()), index=0 if i > 3 else (i+1) if i < len(CHAR_MAP)-1 else 0)
        
        if char_name != "无":
            # 获取默认脚本
            default_txt = DEFAULT_SCRIPTS.get(char_name, "wait 1.0\na1")
            script_txt = st.text_area(f"行动轴脚本 #{i+1}", value=default_txt, height=200)
            
            # 特殊选项
            start_stacks = 0
            if "Levatine" in str(CHAR_MAP[char_name]):
                start_stacks = st.number_input("初始熔火层数", 0, 4, 3, key=f"stack_{i}")
            
            selected_chars.append({
                "class": CHAR_MAP[char_name],
                "script": script_txt,
                "stacks": start_stacks
            })

# ==========================================
# 5. 运行逻辑
# ==========================================
run_btn = st.button("▶️ 开始模拟", type="primary", use_container_width=True)

if run_btn:
    # 1. 初始化引擎
    sim = StreamlitEngine()
    
    # 2. 初始化敌人
    target = DummyEnemy(sim, "测试机甲", defense=enemy_def, 
                        resistances={"heat": res_heat, "electric": res_elec, "nature": res_nature})
    sim.entities.append(target)
    
    # 3. 初始化角色
    char_instances = []
    for char_data in selected_chars:
        # 实例化角色 (传入 sim 和 target)
        char_obj = char_data["class"](sim, target)
        
        # 应用特殊设置 (如莱瓦汀层数)
        if hasattr(char_obj, "molten_stacks"):
            char_obj.molten_stacks = char_data["stacks"]
            
        # 装载脚本
        script_list = parse_script_input(char_data["script"])
        char_obj.set_script(script_list)
        
        sim.entities.append(char_obj)
        char_instances.append(char_obj)
        
    # 4. 运行模拟
    with st.spinner('模拟演算中...'):
        try:
            sim.run(max_seconds=sim_duration)
            
            # 5. 结果展示
            st.divider()
            
            # 汇总数据
            r_col1, r_col2 = st.columns([1, 3])
            
            with r_col1:
                st.metric(label="总伤害", value=f"{int(target.total_damage_taken):,}")
                st.markdown("#### 伤害构成")
                # 这里简单展示总伤，如果有分角色统计需求需修改 BaseActor
                st.caption("*当前系统暂未区分单人伤害统计，显示全队总伤*")

            with r_col2:
                st.subheader("📜 战斗日志")
                
                # 渲染漂亮的日志
                log_container = st.container(height=500)
                for log in sim.logs:
                    color = "black"
                    icon = "🔹"
                    if log['type'] == 'damage': 
                        color = "#d63031"; icon = "💥"
                    elif log['type'] == 'reaction': 
                        color = "#e17055"; icon = "⚡"
                    elif log['type'] == 'buff': 
                        color = "#0984e3"; icon = "⬆️"
                    elif log['type'] == 'status':
                        color = "#6c5ce7"; icon = "🔮"
                        
                    log_container.markdown(f"<span style='color:gray'>{log['time']}</span> {icon} <span style='color:{color}'>{log['message']}</span>", unsafe_allow_html=True)

        except Exception as e:
            st.error(f"模拟过程发生错误: {str(e)}")
            st.exception(e)