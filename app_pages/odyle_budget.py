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
        ui.s_number("Regen amount (membership)", "odyle_regen_amount", min_value=0.0)
        ui.s_number("Interval hours (membership)", "odyle_regen_interval_hours", min_value=0.25, step=0.25)
        ui.s_number("Regen amount (no membership)", "odyle_regen_amount_no_membership", min_value=0.0)
        ui.s_number("Interval hours (no membership)", "odyle_regen_interval_hours_no_membership", min_value=0.25, step=0.25)
    nat_m = calc.odyle_natural_per_week(d.settings, True)
    st.caption(f"With membership: {nat_m / 7:,.0f}/day · {nat_m:,.0f}/week per character. "
               "Planning reference: 15 per 3 h = 120/day = 840/week.")

with st.container(border=True):
    st.subheader("Purchasable / crafted Odyle")
    st.caption("KR/TW reference limits: enable with **Use shop Odyle** / **Use morph Odyle** in the sidebar's "
               "global parameters. Not Global-confirmed.")
    ui.s_segmented("Server pool goes to", "server_odyle_pool_target", ["Main", "Split evenly"])
    ui.table_editor(
        "odyle_sources", d.odyle_sources[["id", "name", "source_type", "scope", "purchases", "odyle_each", "kinah_cost_each",
                                          "enabled", "membership_required", "ruleset", "source_status", "notes"]],
        key="odyle_sources_editor", defaults={"source_type": "other", "scope": "per_character"},
        column_config={
            "name": ui.cc.TextColumn("Source"),
            "enabled": ui.cc.CheckboxColumn("Enabled"),
            "membership_required": ui.cc.CheckboxColumn("Membership only"),
            "source_type": ui.cc.SelectboxColumn("Type", options=["shop", "morph", "other"]),
            "scope": ui.cc.SelectboxColumn("Scope", options=["per_character", "shared_server_pool"]),
            "purchases": ui.cc.NumberColumn("Purchases / week"),
            "odyle_each": ui.cc.NumberColumn("Odyle each"),
            "kinah_cost_each": ui.cc.NumberColumn("Kinah each", format="%,.0f"),
            "ruleset": ui.activity_columns()["ruleset"],
            "source_status": ui.activity_columns()["source_status"],
            "notes": ui.cc.TextColumn("Notes", width="large"),
        },
    )
    st.caption(f"Kinah spent on Odyle purchases / week: **{calc.odyle_purchase_kinah_cost(d):,.0f}**")

budget = calc.odyle_budget(d, respect_toggles=False)
chars = calc.active_characters(d).set_index("id")["name"]
tbl = pd.DataFrame({
    "Character": chars.reindex(budget.index).values,
    "Generated": budget["natural"].values,
    "Purchasable": budget["shop"].values,
    "Craftable": budget["morph"].values,
})
with st.container(border=True):
    st.subheader("Weekly Odyle per character")
    with st.container(horizontal=True):
        st.metric("Total generated", ui.fmt(tbl["Generated"].sum()), border=True)
        st.metric("Total purchasable", ui.fmt(tbl["Purchasable"].sum()), border=True)
        st.metric("Total craftable", ui.fmt(tbl["Craftable"].sum()), border=True)
    ui.show(tbl, hide_index=True, column_config={
        c: ui.cc.NumberColumn(c, format="%,.0f") for c in ["Generated", "Purchasable", "Craftable"]})
    st.caption("Purchasable and craftable show what each character can get from the sources above "
               "(server-pool purchases follow *Server pool goes to*). The sidebar toggles decide whether "
               "the plan actually uses them.")
