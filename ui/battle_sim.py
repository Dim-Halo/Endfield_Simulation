import streamlit as st
from simulation.engine import SimEngine
from entities.dummy import DummyEnemy
from ui.char_manage import CHAR_MAP

def render_battle_sim(scripts):
    st.header("⚔️ 战斗模拟")
    
    # Settings
    with st.expander("模拟设置", expanded=True):
        c1, c2 = st.columns(2)
        duration = c1.slider("模拟时长 (秒)", 10, 60, 30)
        enemy_def = c2.number_input("敌人防御", value=100)
    
    if st.button("▶️ 开始模拟", type="primary"):
        run_simulation(scripts, duration, enemy_def)

def run_simulation(scripts, duration, enemy_def):
    sim = SimEngine()
    target = DummyEnemy(sim, "靶子", defense=enemy_def)
    sim.entities.append(target)
    
    # Initialize Team
    team_list = st.session_state.get('selected_team', [])
    active_chars = []
    
    log_placeholder = st.empty()
    logs = []
    
    # Custom logger to capture output
    original_log = sim.log
    def captured_log(msg):
        logs.append(msg)
        # original_log(msg) # Optional: print to console
        
    sim.log = captured_log
    
    for i, char_name in enumerate(team_list):
        if char_name and char_name != "无":
            char_cls = CHAR_MAP[char_name]
            char = char_cls(sim, target)
            
            # Set script
            if char_name in scripts:
                char.set_script(scripts[char_name].split('\n'))
            
            sim.entities.append(char)
            active_chars.append(char)
            
    if not active_chars:
        st.error("队伍为空，无法模拟！")
        return

    # Run
    try:
        with st.spinner("模拟运算中..."):
            sim.run(max_seconds=duration)
            
        st.success("模拟完成！")
        
        # Results
        c1, c2 = st.columns([1, 1])
        with c1:
            st.metric("总伤害", f"{int(target.total_damage_taken):,}")
            dps = target.total_damage_taken / duration
            st.metric("DPS", f"{int(dps):,}")
            
        with c2:
            st.subheader("伤害分布")
            # Simple text distribution
            report = sim.statistics.generate_report()
            st.text(report)
            
        # Logs
        with st.expander("战斗日志"):
            st.text_area("Logs", value="\n".join(logs), height=400)
            
    except Exception as e:
        st.error(f"模拟出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
