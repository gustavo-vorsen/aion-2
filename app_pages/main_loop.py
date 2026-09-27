import streamlit as st

from aion import calc, ui

d = ui.data()
p = ui.plan()
mains = calc.active_characters(d)
mains = mains[mains["is_main"].astype(bool)]

st.caption(
    "Recurring / reset / recharging activities only. One-time progression (collections, wardrobe, gear upgrades, "
    "cleanup) is never part of the weekly loop. Server-wide content is counted once per server."
)

if mains.empty:
    st.warning("No active Main character. Mark one on the Characters page.", icon=":material/warning:")
    st.stop()

who = ui.pick_character(mains, "Main", key="main_loop_pick")

mp = p[p["character_id"] == who["id"]] if not p.empty else p
ui.kpis(mp)

with st.container(border=True):
    st.subheader(f"{who['name']} — weekly activities")
    st.caption("Activities marked **Main** in the content tabs. Set planned runs (blank = max or auto Odyle) and "
               "whether to use the membership extra claim. Organize them into sessions on **Weekly planner**.")
    ui.character_activity_editor(who, None, key=f"main_loop_{who['id']}", only_in_loop=True)

col1, col2 = st.columns(2)
with col1, st.container(border=True):
    st.subheader("Time by activity")
    ui.bar(mp, "activity", "hours", horizontal=True, title="Hours / week")
with col2, st.container(border=True):
    st.subheader("Kinah value by activity")
    ui.bar(mp, "activity", "kinah_value", horizontal=True, title="Kinah value / week", fmt_=",.0f")

