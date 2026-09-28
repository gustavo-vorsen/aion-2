import altair as alt
import pandas as pd
import streamlit as st

from aion import calc, db, ui

d = ui.data()
p = ui.plan()

ui.kpis(p)

unknown = p[p["status"].isin(["Unknown", "KR/TW reference"])] if not p.empty else p
if not unknown.empty:
    share = unknown["hours"].sum() / max(p["hours"].sum(), 1e-9)
    st.warning(
        f"{share:.0%} of planned weekly time uses **Unknown** or **KR/TW reference** values. "
        "Verify them in the activity pages before trusting the totals.",
        icon=":material/warning:",
    )

if p.empty:
    st.info("No activities planned yet. Add characters and enable activities.", icon=":material/info:")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("Hours by character")
        ui.bar(p, "character", "hours", color="category", title="Hours / week")
with col2:
    with st.container(border=True):
        st.subheader("Kinah value by character")
        ui.bar(p, "character", "kinah_value", color="category", title="Kinah value / week", fmt_=",.0f")

col3, col4 = st.columns(2)
with col3:
    with st.container(border=True):
        st.subheader("Odyle budget")
        budget = calc.odyle_budget(d)
        spent = p.groupby("character_id")["odyle"].sum()
        chars = calc.active_characters(d).set_index("id")["name"]
        ob = pd.DataFrame({
            "Character": chars.reindex(budget.index).values,
            "Available": budget["total"].values,
            "Spent": spent.reindex(budget.index).fillna(0).values,
        })
        ob["Remaining"] = ob["Available"] - ob["Spent"]
        ui.show(ob, hide_index=True, column_config={
            c: ui.cc.NumberColumn(format="%,.0f") for c in ["Available", "Spent", "Remaining"]})
with col4:
    with st.container(border=True):
        st.subheader("Main vs alts")
        mva = p.groupby("role", as_index=False)[["hours", "kinah_unbound", "kinah_bound", "abyss_points", "odyle"]].sum()
        ui.show(mva, hide_index=True, column_config={
            "role": "Role", "hours": ui.cc.NumberColumn("Hours", format="%.1f"),
            "kinah_unbound": ui.cc.NumberColumn("Unbound Kinah", format="%,.0f"),
            "kinah_bound": ui.cc.NumberColumn("Bound Kinah", format="%,.0f"),
            "abyss_points": ui.cc.NumberColumn("AP", format="%,.0f"),
            "odyle": ui.cc.NumberColumn("Odyle", format="%,.0f"),
        })

with st.container(border=True):
    st.subheader("Gold by number of characters")
    st.caption("Weekly Kinah if every character spends all its Odyle in that dungeon. The shared server pool is "
               "added once, so it is not multiplied by the number of characters.")
    with st.container(horizontal=True, vertical_alignment="bottom"):
        kinah = st.segmented_control("Kinah", ["Total", "Unbound", "Bound"], default="Total", key="gold_kinah")
        modes = st.pills("Mode", ["Exploration", "Conquest"], default=["Exploration", "Conquest"],
                         selection_mode="multi", key="gold_modes")
        inc_shop = st.toggle("Include purchasable", value=bool(d.settings["use_shop_odyle"]), key="gold_shop")
        inc_morph = st.toggle("Include craftable", value=bool(d.settings["use_morph_odyle"]), key="gold_morph")
        max_n = st.number_input("Up to characters", 1, 20, max(8, len(calc.active_characters(d))), key="gold_n")
    curves = calc.dungeon_gold_curves(d, int(max_n), inc_shop, inc_morph, (kinah or "Total").lower())
    curves = curves[curves["mode"].isin(modes or [])] if not curves.empty else curves
    if curves.empty:
        st.caption("No data.")
    else:
        color, labels = ui.chart_options("gold_chart", ["dungeon", "mode"], "dungeon")
        base = alt.Chart(curves).encode(
            x=alt.X("characters:Q", title="Number of characters", axis=alt.Axis(tickMinStep=1, format="d")),
            y=alt.Y("gold:Q", title=f"{kinah or 'Total'} Kinah / week", axis=alt.Axis(format=",.0f")),
            color=alt.Color(f"{color}:N", title=None) if color else alt.value("#4C78A8"),
            detail="dungeon:N",
        )
        line = base.mark_line(point=True).encode(
            strokeDash=alt.StrokeDash("mode:N", title=None) if color != "mode" else alt.Undefined,
            tooltip=["dungeon", "characters", alt.Tooltip("odyle:Q", format=",.0f", title="Odyle"),
                     alt.Tooltip("gold:Q", format=",.0f", title="Kinah")],
        )
        chart = line
        if labels != "None":
            last = curves[curves["characters"] == curves["characters"].max()].copy()
            last["_text"] = last["gold"].map(lambda v: f"{v:,.0f}") if labels == "Values" else last["dungeon"]
            chart = line + alt.Chart(last).mark_text(align="left", dx=6, fontSize=10).encode(
                x="characters:Q", y="gold:Q", text="_text:N",
                color=alt.Color(f"{color}:N", title=None) if color else alt.value("#262730"))
        st.altair_chart(chart.properties(height=380))

with st.container(border=True):
    week = calc.week_start(d.settings)
    st.subheader("This week's checklist")
    st.caption(f"Week starting {week:%A %d %b %Y} (reset {d.settings['reset_day']} {d.settings['reset_time']}). Log completed runs; progress is saved per week.")
    log = db.read_table("weekly_log", where="week_start = ?", params=[week.isoformat()])
    g = p.groupby(["character_id", "character", "activity_id", "activity"], as_index=False)[["attempts", "hours"]].sum()
    g = g.merge(log[["character_id", "activity_id", "runs_done"]], how="left", on=["character_id", "activity_id"])
    g["runs_done"] = g["runs_done"].fillna(0.0)
    g["progress"] = (g["runs_done"] / g["attempts"]).where(g["attempts"] > 0).clip(upper=1).fillna(0)
    show = g[["character", "activity", "attempts", "runs_done", "progress", "hours"]]

    def upd(rk, changes):
        if "runs_done" in changes:
            db.upsert("weekly_log", rk, {"runs_done": changes["runs_done"] or 0})

    ui.editor(
        show, "weekly_log_editor",
        [{"week_start": week.isoformat(), "character_id": int(r.character_id), "activity_id": int(r.activity_id)} for r in g.itertuples()],
        on_update=upd,
        # Removing a line takes the activity out of this character's plan (0 planned runs).
        on_delete=lambda rk: db.upsert("character_activity", {k: rk[k] for k in ("character_id", "activity_id")},
                                       {"planned_runs": 0}),
        disabled=["character", "activity", "attempts", "progress", "hours"],
        column_config={
            "character": ui.cc.TextColumn("Character", pinned=True),
            "activity": ui.cc.TextColumn("Activity", pinned=True),
            "attempts": ui.cc.NumberColumn("Planned runs", format="%.1f"),
            "runs_done": ui.cc.NumberColumn("Done", min_value=0),
            "progress": ui.cc.ProgressColumn("Progress", min_value=0, max_value=1, format="percent"),
            "hours": ui.cc.NumberColumn("Planned hours", format="%.2f"),
        },
    )
    done_h = (g["runs_done"].clip(upper=g["attempts"]) / g["attempts"].where(g["attempts"] > 0) * g["hours"]).sum()
    st.progress(min(done_h / max(g["hours"].sum(), 1e-9), 1.0), text=f"{done_h:.1f} of {g['hours'].sum():.1f} planned hours done")
