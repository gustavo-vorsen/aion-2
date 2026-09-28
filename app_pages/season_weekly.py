import streamlit as st

from aion import ui

st.caption("Season weekly missions: reset every week during the season.")
ui.category_page(
    ["Daily & Weekly"], key="season_weekly", cadences=["weekly"],
    columns=["name", "scope", "cadence", "attempts_per_reset", "duration_minutes", "kinah_cost",
             "ruleset", "source_status", "notes"],
)
