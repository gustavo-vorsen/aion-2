import streamlit as st

from aion import ui

st.caption("Solo challenge, 3 per week per character (KR), Combat Power 1,000 or more.")
ui.entries_box("Awakening Battle", "entries", gs=True)
ui.category_page(
    ["Awakening Battle"], key="awakening",
    show_params=False,
    reward_keys=["silentium","ariel_shards","stigma_shards"],
)
