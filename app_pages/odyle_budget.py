import pandas as pd
import streamlit as st

from aion import calc, ui

d = ui.data()

st.caption(
    "Odyle is a scarce **reward-claim** resource, not an entry ticket. Membership can allow an extra cube "
    "selection, but that extra claim consumes its own Odyle."
)

with st.container(border=True):
    st.subheader("Natural regeneration")
    with st.container(horizontal=True):
        ui.s_number("Regen amount (no membership)", "odyle_regen_amount_no_membership", min_value=0.0)
        ui.s_number("Interval hours (no membership)", "odyle_regen_interval_hours_no_membership", min_value=0.25, step=0.25)
        ui.s_number("Cap (no membership)", "odyle_cap_no_membership", min_value=0.0, step=10.0, help="Most Odyle you can store.")
    with st.container(horizontal=True):
        ui.s_number("Regen amount (membership)", "odyle_regen_amount", min_value=0.0)
        ui.s_number("Interval hours (membership)", "odyle_regen_interval_hours", min_value=0.25, step=0.25)
        ui.s_number("Cap (membership)", "odyle_cap", min_value=0.0, step=10.0, help="Most Odyle you can store.")
    nat_m = calc.odyle_natural_per_week(d.settings, True)
    st.caption(f"With membership: {nat_m / 7:,.0f}/day · {nat_m:,.0f}/week per character. "
               "Planning reference: 15 per 3 h = 120/day = 840/week. Caps 560 / 840 are from the Asian build; "
               "Global membership raises the cap (amount TBA).")

SCOPES = ["per_character", "per_server"]
COMMON_COLUMNS = {
    "name": ui.cc.TextColumn("Source"),
    "scope": ui.cc.SelectboxColumn("Scope", options=SCOPES),
    "ruleset": ui.activity_columns()["ruleset"],
    "source_status": ui.activity_columns()["source_status"],
    "notes": ui.cc.TextColumn("Notes", width="large"),
}


def sources_table(source_type: str, per: str, costs: dict[str, str]) -> None:
    """Editor for one source type; each 'Total …' column = cost each × weekly count (per character or per server)."""
    src = d.odyle_sources[d.odyle_sources["source_type"] == source_type]
    df = src[["id", "name", "scope", "purchases", "odyle_each", *costs]].copy()
    totals = {}
    for col, label in costs.items():
        total = f"Total {label}"
        df[total] = df["purchases"].fillna(0) * df[col].fillna(0)
        totals[total] = ui.cc.NumberColumn(f"{total} / week", format="%,.0f")
    df[["ruleset", "source_status", "notes"]] = src[["ruleset", "source_status", "notes"]]
    ui.table_editor(
        "odyle_sources", df, key=f"odyle_sources_{source_type}_editor",
        defaults={"source_type": source_type, "scope": "per_character"},
        disabled=list(totals),
        column_config={
            **COMMON_COLUMNS,
            "purchases": ui.cc.NumberColumn(f"{per} / week"),
            "odyle_each": ui.cc.NumberColumn("Odyle each"),
            **{c: ui.cc.NumberColumn(f"{label} each", format="%,.0f") for c, label in costs.items()},
            **totals,
        },
    )
    all_costs = calc.odyle_source_costs(d, source_type)
    st.caption("All characters / week: " + " · ".join(
        f"{label} **{all_costs[c]:,.0f}**" for c, label in costs.items()))


with st.container(border=True):
    st.subheader("Purchasable / crafted Odyle")
    st.caption("KR/TW reference limits. Not Global-confirmed. Per-character rows count once per character, "
               "server-pool rows once per server.")
    st.markdown("**Purchasable** (Odyle shop)")
    sources_table("shop", "Purchases", {"kinah_cost_each": "Kinah"})
    st.markdown("**Craftable** (Substance Morph)")
    sources_table("morph", "Crafts", {"kinah_cost_each": "Kinah", "odyle_cost_each": "Odyle",
                                      "pure_odyle_cost_each": "Pure Odyle",
                                      "refined_odyle_cost_each": "Refined Pure Odyle"})

with st.container(border=True):
    st.subheader("Weekly Odyle per character")
    membership = st.toggle("With membership", value=True, key="odyle_budget_membership",
                           help="Switches natural regeneration between the membership and no-membership rates.")
    budget = calc.odyle_budget(d, respect_toggles=False, membership=membership)
    chars = calc.active_characters(d).set_index("id")["name"]
    tbl = pd.DataFrame({
        "Character": chars.reindex(budget.index).values,
        "Generated": budget["natural"].values,
        "Purchasable": budget["shop"].values,
        "Craftable": budget["morph"].values,
        "Total": budget["total"].values,
    })
    with st.container(horizontal=True):
        st.metric("Total generated", ui.fmt(tbl["Generated"].sum()), border=True)
        st.metric("Total purchasable", ui.fmt(tbl["Purchasable"].sum()), border=True)
        st.metric("Total craftable", ui.fmt(tbl["Craftable"].sum()), border=True)
        st.metric("Total Odyle", ui.fmt(tbl["Total"].sum()), border=True)
    ui.show(tbl, hide_index=True, column_config={
        c: ui.cc.NumberColumn(c, format="%,.0f") for c in ["Generated", "Purchasable", "Craftable", "Total"]})
    st.caption("Every source above counts toward the budget: per-character sources for every character, per-server "
               "sources for the main. The sidebar toggles decide whether the plan actually uses them.")
