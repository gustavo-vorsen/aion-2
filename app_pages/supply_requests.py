import streamlit as st

from aion import ui

st.caption("Daily and weekly Supply Requests (the season one is on the Season page). Server-wide limits are never multiplied by character count.")
ui.category_page(
    ["Supply Requests"], key="supply_requests", cadences=["daily", "weekly"],
    columns=["name", "scope", "cadence", "attempts_per_reset", "duration_minutes", "kinah_cost",
             "ruleset", "source_status", "notes"],
)
