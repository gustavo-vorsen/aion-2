import streamlit as st

from aion import progress, ui

d = ui.data()

tab_reg, tab_matrix = progress.tabs("rewards", [("registry", ":material/paid: Currency registry"), ("matrix", ":material/grid_on: Reward matrix")])

with tab_reg:
    progress.tab_done("rewards", "registry")
    st.caption(
        "Dynamic registry — add a row to create a custom currency; it appears in every reward editor and chart. "
        "**Estimated Kinah value** feeds the 'Estimated Kinah value' mode; **weight** feeds the composite value score."
    )
    ui.table_editor(
        "currencies",
        d.currencies[["key", "name", "category", "tradable", "bound", "shared", "estimated_kinah_value", "weight", "sort_order", "notes"]],
        key="currency_editor", defaults={"sort_order": int(d.currencies["sort_order"].max() or 0) + 1},
        disabled=["key"],
        column_config={
            "key": ui.cc.TextColumn("Key", help="Generated from the name when you add a row."),
            "name": ui.cc.TextColumn("Name", required=True, pinned=True),
            "category": ui.cc.SelectboxColumn("Category", options=["kinah", "ap", "material", "currency", "progress", "gear"]),
            "estimated_kinah_value": ui.cc.NumberColumn("Estimated Kinah value", format="%,.2f"),
            "weight": ui.cc.NumberColumn("Weight for value score", format="%.4f"),
            "sort_order": ui.cc.NumberColumn("Order"),
            "notes": ui.cc.TextColumn("Notes", width="large"),
        },
    )

with tab_matrix:
    progress.tab_done("rewards", "matrix")
    st.caption("Rewards per claim for every activity (multiply by claims per attempt for per-run values).")
    cats = sorted(d.activities["category"].unique())
    chosen = st.pills("Categories", cats, default=cats, selection_mode="multi", key="reward_matrix_cats")
    ids = d.activities.loc[d.activities["category"].isin(chosen or []), "id"].astype(int).tolist()
    if ids:
        ui.reward_editor(ids, key=f"reward_matrix_{'_'.join(sorted(chosen))}")
