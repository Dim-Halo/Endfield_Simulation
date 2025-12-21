import streamlit as st
import pandas as pd
import plotly.express as px
from ui.char_manage import CHAR_MAP

def init_timeline_state():
    if 'timeline_data' not in st.session_state:
        st.session_state['timeline_data'] = [] # List of dicts: {time, char, action, type}
    if 'selected_team' not in st.session_state:
        st.session_state['selected_team'] = ["陈千语", "管理员", "骏卫", "大潘"]

def time_to_script(timeline, char_name):
    """Convert absolute timeline to relative wait script"""
    events = sorted([e for e in timeline if e['char'] == char_name], key=lambda x: x['time'])
    script_lines = []
    current_time = 0.0
    
    for event in events:
        wait_time = event['time'] - current_time
        if wait_time > 0.01: # Ignore tiny waits
            script_lines.append(f"wait {wait_time:.1f}")
        
        action = event['action']
        script_lines.append(action)
        
        # Estimate duration to update current_time? 
        # No, the script engine handles "wait" as "wait before next command".
        # But `wait` in our engine means "idling".
        # If we say "wait 2.0", then "skill", the skill happens at 2.0.
        # The engine consumes time *during* the action execution separately?
        # Actually, `wait` consumes time. Action execution *also* consumes time in the engine logic 
        # (e.g. `action.duration`).
        # If we want to schedule an action at exactly T=5.0s:
        # We need to account for previous action durations?
        # Current engine logic: 
        # `wait t` -> advances engine time by t.
        # `skill` -> executes skill (which has duration). 
        # The engine processes the action *duration* when `tick_loop` runs?
        # In `ChenSim.parse_command`, it returns an `Action`.
        # In `main.py` loop: `char.update(dt)`? 
        # Actually, let's check `set_script` and `on_tick`.
        # The `ScriptController` (in base_actor?) handles execution.
        # Usually: "wait 2.0" -> idle for 2s. Then execute "skill".
        # "Skill" takes 1.5s.
        # If next line is "wait 1.0", does it wait *after* skill finishes?
        # Yes, typically script executes sequentially.
        # So: Action 1 (starts T=0, dur=1.0) -> finishes T=1.0.
        # If we want Action 2 at T=5.0:
        # We need to wait (5.0 - 1.0) = 4.0s.
        # So we need to track *end time* of previous actions to generate correct waits.
        # BUT: We don't know exact duration of actions here without Sim data.
        # Simplified approach: Assume actions are instant for scheduling *start time*, 
        # and the user is responsible for not overlapping?
        # OR: We just generate "wait X" where X is delta from *previous command start*?
        # No, standard script is: Wait (idle) -> Action (busy) -> Wait (idle).
        # So `wait` is "additional idle time".
        # If we want absolute timing, we assume the user knows what they are doing.
        # Let's try to approximate durations:
        # Normal: ~0.5s, Skill: ~1.5s, Ult: ~3.0s, QTE: ~2.0s.
        
        est_duration = 0.5
        if 'skill' in action: est_duration = 1.5
        elif 'ult' in action: est_duration = 3.0
        elif 'qte' in action: est_duration = 2.0
        elif 'a' in action: est_duration = 0.6
        
        current_time = event['time'] + est_duration
        
    return "\n".join(script_lines)

def render_timeline_editor():
    st.header("🎬 编队排轴")
    init_timeline_state()

    # --- Team Selection ---
    cols = st.columns(4)
    for i in range(4):
        with cols[i]:
            options = ["无"] + [c for c in CHAR_MAP.keys() if c != "无"]
            current = st.session_state['selected_team'][i]
            # Handle case where current might not be in options
            idx = options.index(current) if current in options else 0
            new_char = st.selectbox(f"位置 {i+1}", options, index=idx, key=f"team_sel_{i}")
            st.session_state['selected_team'][i] = new_char

    st.divider()

    # --- Timeline Interaction ---
    # Master Slider
    cursor_time = st.slider("⏱️ 时间轴光标 (秒)", 0.0, 30.0, 0.0, 0.1, key="timeline_slider")
    
    st.caption("在当前光标时间点插入动作：")
    
    # Action Buttons for each active character
    action_cols = st.columns(4)
    for i in range(4):
        char_name = st.session_state['selected_team'][i]
        with action_cols[i]:
            if char_name and char_name != "无":
                st.markdown(f"**{char_name}**")
                
                # Check QTE availability (Simple check: is there a QTE recently?)
                # This is a weak check but fulfills "availability judgment" requirement for UI
                last_qte = max([e['time'] for e in st.session_state['timeline_data'] 
                                if e['char'] == char_name and 'qte' in e['action']] + [-999])
                qte_cooldown = 10.0 # Rough estimate
                qte_ready = (cursor_time - last_qte) >= qte_cooldown
                
                if st.button("普攻", key=f"add_atk_{i}"):
                    add_event(cursor_time, char_name, "a1", "普攻")
                if st.button("战技", key=f"add_skill_{i}"):
                    add_event(cursor_time, char_name, "skill", "战技")
                if st.button("终结技", key=f"add_ult_{i}"):
                    add_event(cursor_time, char_name, "ult", "终结技")
                
                # QTE Button with visual state
                qte_label = "连携技" if qte_ready else "连携技(CD?)"
                if st.button(qte_label, key=f"add_qte_{i}", disabled=False):
                    if not qte_ready:
                        st.toast(f"⚠️ 注意：{char_name} 的连携技可能未冷却或未满足条件", icon="⚠️")
                    add_event(cursor_time, char_name, "qte", "连携技")

    st.divider()
    
    # --- Visualization ---
    data = st.session_state['timeline_data']
    if data:
        df = pd.DataFrame(data)
        # Gannt-like chart
        # We need 'Start' and 'Finish'. We estimate duration for visualization.
        df['Start'] = df['time']
        df['Duration'] = df['action'].apply(lambda x: 3.0 if 'ult' in x else (2.0 if 'qte' in x else (1.5 if 'skill' in x else 0.6)))
        df['Finish'] = df['Start'] + df['Duration']
        df['Resource'] = df['char']
        
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Resource", color="type", 
                          title="排轴预览", hover_data=["action"])
        fig.update_yaxes(categoryorder="array", categoryarray=st.session_state['selected_team'][::-1])
        st.plotly_chart(fig, use_container_width=True)
        
        # Edit/Delete List
        with st.expander("查看/删除已添加动作"):
            for idx, item in enumerate(sorted(data, key=lambda x: x['time'])):
                c1, c2, c3 = st.columns([1, 4, 1])
                c1.write(f"{item['time']}s")
                c2.write(f"{item['char']} - {item['type']}")
                if c3.button("删除", key=f"del_{idx}"):
                    st.session_state['timeline_data'].remove(item)
                    st.rerun()
                    
        # Clear All
        if st.button("清空所有动作"):
            st.session_state['timeline_data'] = []
            st.rerun()
    else:
        st.info("暂无动作，请拖动滑块并添加动作。")

def add_event(time, char, action, type_label):
    st.session_state['timeline_data'].append({
        "time": time,
        "char": char,
        "action": action,
        "type": type_label
    })
    st.toast(f"已添加: {char} {type_label} @ {time}s")

def get_generated_scripts():
    """Returns dict of scripts for the simulation"""
    scripts = {}
    team = st.session_state.get('selected_team', [])
    data = st.session_state.get('timeline_data', [])
    
    for char in team:
        if char and char != "无":
            scripts[char] = time_to_script(data, char)
            
    return scripts
