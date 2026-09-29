import pandas as pd
import streamlit as st

from aion import db, one_time_ui, ui

st.caption("Empyrean Traces (feathers): collected once each, they raise the Monolith (shared per server).")
faction, mine = one_time_ui.side_picker("feathers_side")

with st.container(border=True):
    st.subheader("Feathers per region")
    rows = db.read_table("feather_regions", where="faction = ?", params=[faction], order="id")
    ui.table_editor(
        "feather_regions", rows[["id", "region", "count", "collected", "notes"]], key=f"feathers_{faction}",
        defaults={"faction": faction},
        column_config={"region": ui.cc.TextColumn("Region", pinned=True, width="medium"),
                       "count": ui.cc.NumberColumn("Feathers", min_value=0),
                       "collected": ui.cc.NumberColumn("Collected", min_value=0),
                       "notes": ui.cc.TextColumn("Notes")})
    total, got = rows["count"].fillna(0).sum(), rows["collected"].fillna(0).sum()
    st.caption(f"Total **{total:,.0f}** · collected **{got:,.0f}** · remaining **{max(total - got, 0):,.0f}**. "
               "Per-region counts: Korean community tallies (inven); the total (560) matches the Global data.")

with st.container(border=True):
    st.subheader("Monolith")
    levels = db.read_table("monolith_levels", order="monolith, level")
    names = list(dict.fromkeys(levels["monolith"])) if not levels.empty else []
    mono = st.pills("Monolith", names, default=names[0] if names else None, required=True, key="monolith_pick",
                    label_visibility="collapsed") if names else None
    if mono:
        lv = levels[levels["monolith"] == mono]
        ui.table_editor(
            "monolith_levels", lv[["id", "level", "feathers", "reward"]], key=f"monolith_{mono}",
            defaults={"monolith": mono},
            column_config={"level": ui.cc.NumberColumn("Level", pinned=True),
                           "feathers": ui.cc.NumberColumn("Feathers for this level", min_value=0),
                           "reward": ui.cc.TextColumn("Reward", width="large")})
        cum = lv.sort_values("level")["feathers"].fillna(0).cumsum()
        with st.container(horizontal=True):
            st.metric("Feathers to max level", f"{cum.iloc[-1]:,.0f}" if not cum.empty else "0", border=True)
            st.metric("Levels", f"{len(lv)}", border=True)

with st.container(border=True):
    st.subheader("Leftover feathers")
    st.markdown("After **Monolith level 30** you learn a Substance Morph recipe: **1 Empyrean Trace → 10 Power Shard "
                "(Bound)**, 100 % success, up to **1,120 times per character** (no reset). Global playtest data.")
