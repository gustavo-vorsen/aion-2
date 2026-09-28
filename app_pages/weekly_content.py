import streamlit as st

from aion import ui

st.caption(
    "Daily Dungeon and Raid. Daily Dungeon entries are a weekly allowance. Server-wide limits are never multiplied "
    "by character count. KR/TW Daily Dungeons are not assumed on Global."
)
ui.category_page(
    ["Daily Dungeon", "Raid"], key="weekly_content",
    cadences=["weekly", "seasonal", "event", "opportunity", "regenerating", "none"],
    columns=["name", "scope", "cadence", "attempts_per_reset",
             "membership_bonus_attempts", "charges_per_day", "charge_cap", "duration_minutes", "kinah_cost",
             "ruleset", "source_status", "notes"],
)
