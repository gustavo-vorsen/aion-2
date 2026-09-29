import streamlit as st

from aion import progress, ui

st.caption("Bosses on fixed spawn timers: repeatable every spawn, not one-time and not part of the weekly loop.")
COLUMNS = ["name", "scope", "cadence", "attempts_per_reset", "duration_minutes", "entry_item_level",
           "recommended_item_level", "ruleset", "source_status", "notes"]
field, world = progress.tabs("bosses", [("field", ":material/public: Field bosses (Abyss)"),
                                        ("world", ":material/landscape: World bosses (regions)")])
with field:
    progress.tab_done("bosses", "field")
    st.caption("Abyss field bosses. Kinah per kill is capped (Nahma 1M, Kaira / Executors 200k); values here are the caps.")
    ui.category_page(["Field Bosses"], key="field_bosses", columns=COLUMNS,
                     reward_keys=["kinah_unbound", "kinah_bound", "abyss_points", "gear_drops"])
with world:
    progress.tab_done("bosses", "world")
    st.caption("Regional world bosses: respawn timer after each kill (Korean official cycles in Notes) and average "
               "loot per kill (Global playtest data). Tracking only: they add no runs to the plan.")
    acts = ui.data().activities
    wb = acts[acts["category"] == "World Bosses"]
    regions = list(dict.fromkeys(wb["mode"].dropna())) if not wb.empty else []
    if regions:
        region = st.segmented_control("Region", regions, default=regions[0], required=True, key="wb_region",
                                      label_visibility="collapsed", width="stretch") or regions[0]
        with st.container(border=True):
            st.subheader("Bosses")
            ui.activity_editor(["World Bosses"], key=f"wb_{region}", columns=["name", "entry_item_level", "notes"],
                               new_category="World Bosses", mode=region)
        with st.container(border=True):
            st.subheader("Loot per kill")
            st.caption("Averages: e.g. Boss set gear 1.25 = one guaranteed piece + 25 % from the loot chest. Gear from "
                       "the shared drop table is grouped by grade.")
            rows = wb[wb["mode"] == region]
            ui.wide_reward_editor(rows["id"].astype(int).tolist(), key=f"wb_loot_{region}", label="Boss")
