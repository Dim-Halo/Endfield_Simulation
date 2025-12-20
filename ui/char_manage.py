import streamlit as st
from entities.characters.chen_sim import ChenSim
from entities.characters.admin_sim import AdminSim
from entities.characters.guard_sim import GuardSim
from entities.characters.dapan_sim import DaPanSim
from entities.characters.levatine_sim import LevatineSim
from entities.characters.wolfguard_sim import WolfguardSim
from entities.characters.erdila_sim import ErdilaSim
from entities.characters.antal_sim import AntalSim

CHAR_MAP = { 
    "无": None, 
    "莱瓦汀": LevatineSim, 
    "狼卫": WolfguardSim, 
    "艾尔黛拉": ErdilaSim, 
    "安塔尔": AntalSim,
    "陈千语": ChenSim,
    "管理员": AdminSim,
    "骏卫": GuardSim,
    "大潘": DaPanSim
}

def render_char_manage():
    st.header("👥 角色管理")
    
    st.info("在此页面查看干员信息。（未来将支持装备与武器选择）")
    
    cols = st.columns(3)
    chars = [c for c in CHAR_MAP.keys() if c != "无"]
    
    for i, char_name in enumerate(chars):
        with cols[i % 3]:
            with st.container(border=True):
                st.subheader(char_name)
                # 这里可以展示更多静态信息，目前仅展示名称占位
                st.caption("武器: 默认")
                st.caption("装备: 默认")
                if st.button(f"查看详情 {char_name}", key=f"btn_info_{i}"):
                    st.toast(f"已选择 {char_name} (详情功能开发中)")
