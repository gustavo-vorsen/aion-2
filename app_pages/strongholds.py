import streamlit as st

from aion import one_time_ui

st.caption("Garrisons: one-time chest per character. The only source of Noble Belt Enhance Scrolls (2 each per aion2hub; Korean sources say 1).")
faction, mine = one_time_ui.side_picker("strongholds_side")
with st.container(border=True):
    st.subheader("Rewards per clear")
    st.caption("Same for every one on this side. Counted once per character in the Progression Item Level totals.")
    one_time_ui.rewards_for("strongholds", mine, key=f"strongholds_rewards_{faction}")
with st.container(border=True):
    st.subheader("List")
    one_time_ui.done_list("stronghold", faction, key=f"strongholds_{faction}")
