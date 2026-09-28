import streamlit as st

from aion import ui

st.caption("Season-long content (e.g. the season Supply Request). Weekly amounts = season total ÷ season weeks.")
ui.category_page(
    ["Daily & Weekly", "Supply Requests"], key="season", cadences=["seasonal"],
    columns=["name", "scope", "cadence", "attempts_per_reset", "duration_minutes", "kinah_cost",
             "ruleset", "source_status", "notes"],
)
