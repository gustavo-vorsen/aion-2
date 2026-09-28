import streamlit as st

from aion import calc, progress, ui

d = ui.data()
p = ui.plan()

tab_calc, tab_all = progress.tabs("economy", [("calculator", ":material/calculate: Economy calculator"), ("all", ":material/table: All activities (master editor)")])

with tab_calc:
    progress.tab_done("economy", "calculator")
    mem = st.toggle("Assume membership extra claims", value=True, key="econ_mem")
    cats = sorted(d.activities["category"].unique())
    chosen = st.pills("Categories", cats, default=cats, selection_mode="multi")
    tbl = calc.dungeon_table(d, None, mem)
    tbl = tbl[d.activities["category"].reset_index(drop=True).isin(chosen or [])]
    fmt = {c: ui.cc.NumberColumn(format="%,.1f") for c in tbl.columns if tbl[c].dtype.kind == "f"}
    with st.container(border=True):
        st.subheader("Per-run economics")
        ui.show(tbl, hide_index=True, column_config={**fmt, "Activity": ui.cc.TextColumn(pinned=True)})

    if not p.empty:
        weekly = p[p["category"].isin(chosen or [])].groupby("activity", as_index=False)[
            ["hours", "kinah_unbound", "kinah_bound", "abyss_points", "odyle", "kinah_value"]].sum()
        weekly["Kinah value / hour"] = (weekly["kinah_value"] / weekly["hours"]).where(weekly["hours"] > 0)
        with st.container(border=True):
            st.subheader("Weekly totals from the current plan")
            ui.show(weekly, hide_index=True, column_config={
                "activity": ui.cc.TextColumn("Activity", pinned=True),
                "hours": ui.cc.NumberColumn("Weekly time (h)", format="%.2f"),
                "kinah_unbound": ui.cc.NumberColumn("Weekly unbound Kinah", format="%,.0f"),
                "kinah_bound": ui.cc.NumberColumn("Weekly bound Kinah", format="%,.0f"),
                "abyss_points": ui.cc.NumberColumn("Weekly AP", format="%,.0f"),
                "odyle": ui.cc.NumberColumn("Weekly Odyle", format="%,.0f"),
                "kinah_value": ui.cc.NumberColumn("Weekly Kinah value", format="%,.0f"),
                "Kinah value / hour": ui.cc.NumberColumn(format="%,.0f"),
            })
            ui.bar(weekly.fillna(0), "activity", "Kinah value / hour", horizontal=True, fmt_=",.0f", height=420)
        st.caption(f"Odyle purchases cost **{calc.odyle_source_costs(d, respect_toggles=True)["kinah_cost_each"]:,.0f}** Kinah/week; activity entry costs total **{p['kinah_cost'].sum():,.0f}** Kinah/week.")

with tab_all:
    progress.tab_done("economy", "all")
    st.caption("Every activity parameter in one grid. Add rows to create new activities (any category name works).")
    ui.ruleset_badges()
    cats = sorted(d.activities["category"].unique())
    ui.activity_editor(
        cats, key="master_activity_editor",
        columns=[c for c in ui.activity_columns() if c not in ("sort_order",)],
    )
