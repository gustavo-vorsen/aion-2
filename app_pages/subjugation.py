import streamlit as st

from aion import ui

st.caption("Weekly 4-player content, 3 per week. Removed in KR Season 3 but likely at the level-45 Global launch.")
ui.entries_box("Subjugation", "entries", gs=True)
ui.category_page(
    ["Subjugation"], key="subjugation",
    show_params=False,
    reward_keys=["enhancement_stones","ariel_shards","breakthrough_shards"],
)
