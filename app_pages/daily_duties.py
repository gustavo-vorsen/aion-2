import streamlit as st

from aion import ui

st.caption("Daily Duties reset every day. Server-wide limits are never multiplied by character count.")
ui.category_page(
    ["Daily & Weekly"], key="daily_duties", cadences=["daily"],
    columns=["name", "scope", "cadence", "attempts_per_reset", "duration_minutes", "kinah_cost",
             "ruleset", "source_status", "notes"],
)
