import streamlit as st

from aion import ui

st.caption(
    "Dimensional Invasion: charges regenerate daily up to a cap (reference: 1 per day, cap 7). "
    "Rewards depend on contribution."
)
ui.entries_box("Dimensional Invasion", "reward claims")
ui.category_page(
    ["Dimensional Invasion"], key="invasion",
    show_params=False,
    reward_keys=["kinah_bound", "kinah_unbound", "enhancement_stones", "abyss_points"],
)
