import streamlit as st

from aion import one_time_ui

st.caption("Sealed ('?' on the map) dungeons: one-time first-clear rewards, per character.")
faction, mine = one_time_ui.side_picker("hidden_dungeons_side")
with st.container(border=True):
    st.subheader("Rewards per clear")
    st.caption("Same for every one on this side. Counted once per character in the Progression Item Level totals.")
    one_time_ui.rewards_for("hidden_dungeons", mine, key=f"hidden_dungeons_rewards_{faction}")
with st.container(border=True):
    st.subheader("List")
    one_time_ui.done_list("hidden_dungeon", faction, key=f"hidden_dungeons_{faction}")
