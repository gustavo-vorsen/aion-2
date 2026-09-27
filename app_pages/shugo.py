import streamlit as st

from aion import ui

st.caption(
    "Shugo Festival: weekly entries (KR/TW reference: 7 per week, 14 with membership), counted per server. "
    "Not Global-confirmed until the launch client."
)
ui.category_page(
    ["Shugo Festival"], key="shugo",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "membership_bonus_attempts", "duration_minutes", "ruleset", "source_status", "notes"],
    reward_keys=["kinah_bound", "kinah_unbound", "hidden_cube_keys", "enhancement_stones"],
)
