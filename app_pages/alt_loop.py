import streamlit as st

from aion import calc, ui

d = ui.data()
p = ui.plan()
alts = calc.active_characters(d)
alts = alts[~alts["is_main"].astype(bool)]

st.caption(
    "Default Alt loop: Supply Requests, Expedition/Conquest with the Alt's own Odyle, Nightmare and Ascension Trial. "
    "Server-wide content (Daily Duties, Command Scrolls, Abyss Commands, Shugo) is excluded by default."
)

if alts.empty:
    st.info("No active Alt characters (or 'Include alts' is off in the sidebar).", icon=":material/info:")
    st.stop()

ap = p[p["character_id"].isin(alts["id"])] if not p.empty else p
ui.kpis(ap)

with st.container(border=True):
    st.subheader("Alt comparison")
    ui.bar(ap, "character", "kinah_value",
           color="category", title="Kinah value / week", fmt_=",.0f")

who = ui.pick_character(alts, "Alt", key="alt_loop_pick")
with st.container(border=True):
    st.subheader(f"{who['name']} — weekly activities")
    st.caption("Activities marked **Alt** in the content tabs. Organize them into sessions on **Weekly planner**.")
    ui.character_activity_editor(who, None, key=f"alt_loop_{who['id']}", only_in_loop=True)
    ui.plan_table(ap[ap["character_id"] == who["id"]], key=f"alt_plan_{who['id']}")
