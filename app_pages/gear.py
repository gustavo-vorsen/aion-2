import streamlit as st

from aion import db, ui

d = ui.data()
chars = d.characters

with st.container(border=True):
    st.subheader("Initial gearing strategy")
    ui.s_text("Leveling upgrade order", "leveling_gear_strategy")
    with st.container(horizontal=True):
        ui.s_number("Enhancement Stone recovery on extraction (%)", "enhancement_recovery_pct", min_value=0.0, max_value=100.0)
        ui.s_number("Kinah recovery on extraction (%)", "kinah_recovery_pct", min_value=0.0, max_value=100.0)
    st.caption("Offensive upgrades shorten MSQ/dungeon time. Recovery percentages are configurable because Global rules may differ.")

if chars.empty:
    st.info("No characters yet.", icon=":material/info:")
    st.stop()

who = ui.pick_character(chars, "Character", key="gear_pick")
gear = db.read_table("gear_slots", where="character_id = ?", params=[int(who["id"])], order="profile, priority_score DESC")
with st.container(border=True):
    st.subheader(f"{who['name']}: slots & upgrade priority")
    st.caption("Separate PvE and PvP/Abyss profiles. Add or delete rows as needed.")
    ui.table_editor(
        "gear_slots", gear[["id", "profile", "slot", "priority_score", "enhancement_level", "target_level", "material_budget", "notes"]],
        key=f"gear_editor_{who['id']}", defaults={"character_id": int(who["id"]), "profile": "pve"},
        column_config={
            "profile": ui.cc.SelectboxColumn("Profile", options=["pve", "pvp"], required=True),
            "slot": ui.cc.TextColumn("Slot", required=True),
            "priority_score": ui.cc.NumberColumn("Priority score"),
            "enhancement_level": ui.cc.NumberColumn("Current +"),
            "target_level": ui.cc.NumberColumn("Target +"),
            "material_budget": ui.cc.NumberColumn("Material budget", format="%,.0f"),
            "notes": ui.cc.TextColumn("Notes", width="large"),
        },
    )
    if not gear.empty and gear["priority_score"].sum() > 0:
        g = gear.assign(share=gear["priority_score"] / gear["priority_score"].sum())
        ui.bar(g, "slot", "share", color="profile", horizontal=True, title="Share of upgrade priority", fmt_=".0%", height=220)
