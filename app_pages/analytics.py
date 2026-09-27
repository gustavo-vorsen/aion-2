import altair as alt
import pandas as pd
import streamlit as st

from aion import calc, progress, ui

d = ui.data()
p = ui.plan()

if p.empty:
    st.info("Nothing planned yet.", icon=":material/info:")
    st.stop()

names = d.currencies.set_index("key")["name"].to_dict()
keys = [k for k in d.rewards.columns if k in p.columns]

t_time, t_kinah, t_ap, t_odyle, t_mat, t_mva, t_front = progress.tabs("analytics", [
    ("time", ":material/schedule: Weekly time"), ("kinah", ":material/paid: Kinah"), ("ap", ":material/military_tech: AP"),
    ("odyle", ":material/bolt: Odyle"), ("materials", ":material/category: Materials"),
    ("mva", ":material/compare_arrows: Main vs alt"), ("frontier", ":material/scatter_plot: Efficiency frontier"),
])


def card(title, fn):
    with st.container(border=True):
        st.subheader(title)
        fn()


with t_time:
    progress.tab_done("analytics", "time")
    ui.kpis(p)
    c1, c2 = st.columns(2)
    with c1:
        card("Hours by character", lambda: ui.bar(p, "character", "hours", title="Hours / week"))
        card("Hours by category", lambda: ui.bar(p, "category", "hours", horizontal=True, title="Hours / week"))
    with c2:
        card("Main vs alts", lambda: ui.bar(p, "role", "hours", title="Hours / week"))
        card("Hours by activity", lambda: ui.bar(p, "activity", "hours", horizontal=True, title="Hours / week", height=460))

with t_kinah:
    progress.tab_done("analytics", "kinah")
    act = p.groupby("activity", as_index=False)[["kinah_unbound", "kinah_bound", "minutes", "odyle"]].sum()
    act["Unbound / hour"] = calc.per_hour(act, "kinah_unbound")
    act["Bound / hour"] = calc.per_hour(act, "kinah_bound")
    act["Kinah / Odyle"] = ((act["kinah_unbound"] + act["kinah_bound"]) / act["odyle"]).where(act["odyle"] > 0)
    ch = p.groupby("character", as_index=False)[["kinah_unbound", "kinah_bound", "minutes"]].sum()
    ch["Unbound / hour"] = calc.per_hour(ch, "kinah_unbound")
    with st.container(horizontal=True):
        st.metric("Unbound Kinah / week", ui.fmt(p["kinah_unbound"].sum()), border=True)
        st.metric("Bound Kinah / week", ui.fmt(p["kinah_bound"].sum()), border=True)
        st.metric("Combined / hour", ui.fmt((p["kinah_unbound"].sum() + p["kinah_bound"].sum()) / p["hours"].sum()), border=True, help="Display only; bound and unbound are tracked separately.")
    c1, c2 = st.columns(2)
    with c1:
        card("Kinah / week by character", lambda: ui.bar(
            ch.melt(id_vars="character", value_vars=["kinah_unbound", "kinah_bound"], var_name="type", value_name="kinah"),
            "character", "kinah", color="type", title="Kinah / week", fmt_=",.0f"))
        card("Unbound Kinah / hour by activity", lambda: ui.bar(act.fillna(0), "activity", "Unbound / hour", horizontal=True, fmt_=",.0f", height=420))
    with c2:
        card("Unbound Kinah / hour by character", lambda: ui.bar(ch.fillna(0), "character", "Unbound / hour", fmt_=",.0f"))
        card("Kinah / Odyle", lambda: ui.bar(act.dropna(subset=["Kinah / Odyle"]), "activity", "Kinah / Odyle", horizontal=True, fmt_=",.0f"))

    def cumulative():
        cum = p.groupby("activity", as_index=False)[["kinah_unbound", "kinah_bound"]].sum()
        cum["total"] = cum["kinah_unbound"] + cum["kinah_bound"]
        cum = cum.sort_values("total", ascending=False)
        cum["cumulative"] = cum["total"].cumsum()
        _, labels = ui.chart_options("cumulative_kinah", [None], None)
        base = alt.Chart(cum).encode(
            x=alt.X("activity:N", sort=None, title=None), y=alt.Y("cumulative:Q", title="Cumulative Kinah / week", axis=alt.Axis(format=",.0f")))
        chart = base.mark_line(point=True).encode(
            tooltip=["activity", alt.Tooltip("total:Q", format=",.0f"), alt.Tooltip("cumulative:Q", format=",.0f")])
        if labels != "None":
            cum["_text"] = cum["cumulative"].map(lambda v: f"{v:,.0f}") if labels == "Values" else cum["activity"]
            chart = chart + alt.Chart(cum).mark_text(dy=-10, fontSize=10).encode(
                x=alt.X("activity:N", sort=None), y="cumulative:Q", text="_text:N")
        st.altair_chart(chart.properties(height=300))
    card("Cumulative weekly Kinah (largest sources first)", cumulative)

with t_ap:
    progress.tab_done("analytics", "ap")
    ab = calc.abyss_summary(d, p)
    src = p[p.get("abyss_points", 0) > 0].copy()
    src["source"] = src["activity"].where(src["category"] == "Abyss", src["category"])
    with st.container(horizontal=True):
        st.metric("AP / week", ui.fmt(p["abyss_points"].sum()), border=True)
        st.metric("Effective AP after caps", ui.fmt(ab["effective_ap"].sum()) if not ab.empty else "—", border=True)
        st.metric("AP / hour", ui.fmt(src["abyss_points"].sum() / src["hours"].sum()) if not src.empty else "—", border=True)
    c1, c2 = st.columns(2)
    with c1:
        card("AP by source", lambda: ui.bar(src, "source", "abyss_points", horizontal=True, fmt_=",.0f", title="AP / week"))
    with c2:
        def cap_chart():
            if ab.empty:
                return
            u = ab.melt(id_vars="character", value_vars=["pve_cap_pct", "pvp_cap_pct", "abyss_time_pct"], var_name="cap", value_name="utilization").dropna()
            ui.bar(u, "character", "utilization", color="cap", fmt_=".0%", title="Utilization")
        card("AP cap & Abyss time utilization", cap_chart)
    aph = src.groupby("activity", as_index=False)[["abyss_points", "minutes"]].sum()
    aph["AP / hour"] = calc.per_hour(aph, "abyss_points")
    card("AP / hour by activity", lambda: ui.bar(aph.fillna(0), "activity", "AP / hour", horizontal=True, fmt_=",.0f"))

with t_odyle:
    progress.tab_done("analytics", "odyle")
    budget = calc.odyle_budget(d)
    gen = budget[["natural", "shop", "morph", "other"]].sum()
    with st.container(horizontal=True):
        st.metric("Generated", ui.fmt(gen["natural"]), border=True)
        st.metric("Bought", ui.fmt(gen["shop"]), border=True)
        st.metric("Crafted", ui.fmt(gen["morph"]), border=True)
        st.metric("Spent", ui.fmt(p["odyle"].sum()), border=True)
        st.metric("Remaining", ui.fmt(budget["total"].sum() - p["odyle"].sum()), border=True)
    od = p[p["odyle"] > 0].groupby("activity", as_index=False)[["odyle", "kinah_value", "value_score", *[k for k in ["abyss_points"] if k in p]]].sum()
    od["Kinah value / 40 Odyle"] = od["kinah_value"] / od["odyle"] * 40
    od["Value score / Odyle"] = od["value_score"] / od["odyle"]
    c1, c2 = st.columns(2)
    with c1:
        card("Spend allocation by content", lambda: ui.bar(p[p["odyle"] > 0], "activity", "odyle", horizontal=True, fmt_=",.0f", title="Odyle / week"))
    with c2:
        card("Reward per 40 Odyle", lambda: ui.bar(od, "activity", "Kinah value / 40 Odyle", horizontal=True, fmt_=",.0f"))
    card("Total reward value per Odyle", lambda: ui.bar(od, "activity", "Value score / Odyle", horizontal=True, fmt_=",.2f"))

with t_mat:
    progress.tab_done("analytics", "materials")
    metric = st.selectbox("Reward metric", keys, format_func=lambda k: names.get(k, k),
                          index=keys.index("enhancement_stones") if "enhancement_stones" in keys else 0)
    m = p.groupby("activity", as_index=False)[[metric, "minutes", "attempts", "odyle"]].sum()
    m = m[m[metric] > 0]
    m["per hour"] = calc.per_hour(m, metric)
    m["per attempt"] = (m[metric] / m["attempts"]).where(m["attempts"] > 0)
    m["per Odyle"] = (m[metric] / m["odyle"]).where(m["odyle"] > 0)
    st.metric(f"{names.get(metric, metric)} / week", ui.fmt(p[metric].sum(), 1), border=True)
    c1, c2 = st.columns(2)
    with c1:
        card("Per week", lambda: ui.bar(p[p[metric] > 0], "activity", metric, horizontal=True, title="Per week"))
        card("Per attempt", lambda: ui.bar(m.fillna(0), "activity", "per attempt", horizontal=True))
    with c2:
        card("Per hour", lambda: ui.bar(m.fillna(0), "activity", "per hour", horizontal=True))
        card("Per Odyle", lambda: ui.bar(m.dropna(subset=["per Odyle"]), "activity", "per Odyle", horizontal=True, fmt_=",.3f"))
    card("By character", lambda: ui.bar(p, "character", metric, title="Per week"))

with t_mva:
    progress.tab_done("analytics", "mva")
    cols = ["hours", "kinah_unbound", "kinah_bound", *[k for k in ["abyss_points"] if k in p], "odyle", "value_score"]
    mva = p.groupby("role", as_index=False)[cols].sum()
    budget = calc.odyle_budget(d)
    roles = calc.active_characters(d).set_index("id")["is_main"].map({True: "Main", False: "Alt"})
    gen = budget["total"].groupby(roles.reindex(budget.index)).sum()
    mva["odyle_generated"] = mva["role"].map(gen).fillna(0)
    ui.show(mva, hide_index=True, column_config={
        "role": "Role", "hours": ui.cc.NumberColumn("Weekly time (h)", format="%.1f"),
        "kinah_unbound": ui.cc.NumberColumn("Unbound Kinah", format="%,.0f"),
        "kinah_bound": ui.cc.NumberColumn("Bound Kinah", format="%,.0f"),
        "abyss_points": ui.cc.NumberColumn("AP", format="%,.0f"),
        "odyle": ui.cc.NumberColumn("Odyle spent", format="%,.0f"),
        "odyle_generated": ui.cc.NumberColumn("Odyle available", format="%,.0f"),
        "value_score": ui.cc.NumberColumn("Material value score", format="%,.1f"),
    })
    share = mva.set_index("role")[cols + ["odyle_generated"]]
    share = (share / share.sum()).reset_index().melt(id_vars="role", var_name="metric", value_name="share")
    def share_chart():
        _, labels = ui.chart_options("contribution_share", ["role"], "role")
        s = share.sort_values(["metric", "role"]).copy()
        s["_mid"] = s.groupby("metric")["share"].cumsum() - s["share"] / 2
        chart = alt.Chart(s).mark_bar().encode(
            x=alt.X("share:Q", stack="zero", axis=alt.Axis(format="%"), title=None), y=alt.Y("metric:N", title=None),
            color=alt.Color("role:N", title=None), order=alt.Order("role:N"),
            tooltip=["role", "metric", alt.Tooltip("share:Q", format=".0%")])
        if labels != "None":
            s["_text"] = s["share"].map(lambda v: f"{v:.0%}") if labels == "Values" else s["role"]
            chart = chart + alt.Chart(s).mark_text(fontSize=10, fontWeight="bold", color="#262730").encode(
                x="_mid:Q", y="metric:N", text="_text:N")
        st.altair_chart(chart.properties(height=280))
    card("Contribution share", share_chart)

with t_front:
    progress.tab_done("analytics", "frontier")
    metric = st.selectbox("Y axis reward", ["kinah_value", "value_score", *keys], key="frontier_metric",
                          format_func=lambda k: {"kinah_value": "Kinah value", "value_score": "Value score"}.get(k, names.get(k, k)))
    f = p.groupby(["activity", "category"], as_index=False)[["hours", metric, "odyle"]].sum()
    f = f[(f["hours"] > 0)]
    color, labels = ui.chart_options("frontier", ["activity", "category"], "category", label_default="Names")
    base = alt.Chart(f).encode(
        x=alt.X("hours:Q", title="Hours / week"), y=alt.Y(f"{metric}:Q", title="Reward / week", axis=alt.Axis(format=",.0f")))
    chart = base.mark_circle(opacity=0.7).encode(
        size=alt.Size("odyle:Q", title="Odyle cost", scale=alt.Scale(range=[40, 1200])),
        color=alt.Color(f"{color}:N", title=None) if color else alt.value("#4C78A8"),
        tooltip=["activity", "category", alt.Tooltip("hours:Q", format=".2f"), alt.Tooltip(f"{metric}:Q", format=",.1f"), alt.Tooltip("odyle:Q", format=",.0f")],
    )
    if labels != "None":
        f["_text"] = f[metric].map(lambda v: f"{v:,.0f}") if labels == "Values" else f["activity"]
        chart = chart + alt.Chart(f).mark_text(align="left", dx=8, fontSize=10).encode(
            x="hours:Q", y=f"{metric}:Q", text="_text:N")
    st.altair_chart(chart.properties(height=480))
    st.caption("One point per activity. Up-and-left is efficient; bubble size is Odyle cost.")
