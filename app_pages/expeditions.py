import altair as alt
import streamlit as st

from aion import calc, ui

d = ui.data()
CATS = ["Expedition"]

st.caption(
    "Dungeon parameters. Each reward claim costs Odyle (see **Odyle budget**); the membership extra claim "
    "costs its own Odyle."
)

with st.container(border=True):
    st.subheader("Dungeon parameters")
    ui.activity_editor(CATS, key="dungeon_editor", columns=[
        "name", "dungeon", "mode", "tier", "enabled", "main_default", "alt_default", "entry_item_level",
        "recommended_item_level", "duration_minutes", "odyle_per_claim", "reward_claims_per_attempt",
        "membership_extra_claims", "weekly_claim_limit", "attempts_per_reset", "scope", "cadence",
        "ruleset", "source_status", "notes",
    ], new_category="Expedition")

with st.container(border=True):
    st.subheader("Rewards per claim")
    ids = d.activities.loc[d.activities["category"].isin(CATS), "id"].astype(int).tolist()
    if ids:
        ui.reward_editor(ids, key="dungeon_rewards")

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
