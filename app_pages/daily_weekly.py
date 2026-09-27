import streamlit as st

from aion import ui

st.caption(
    "Daily Duties, Supply Requests, Daily Dungeon and Raid. "
    "Server-wide limits are never multiplied by character count. KR/TW Daily Dungeons are not assumed on Global."
)
ui.category_page(
    ["Daily & Weekly", "Supply Requests", "Daily Dungeon", "Raid"], key="daily_weekly",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "membership_bonus_attempts", "charges_per_day", "charge_cap", "duration_minutes", "kinah_cost",
             "ruleset", "source_status", "notes"],
)
