import streamlit as st

from aion import ui

st.caption("Weekly 4-player content, 3 per week. Removed in KR Season 3 but likely at the level-45 Global launch.")
ui.category_page(
    ["Subjugation"], key="subjugation",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "duration_minutes", "entry_item_level", "recommended_item_level", "ruleset", "source_status", "notes"],
    reward_keys=["enhancement_stones","ariel_shards","breakthrough_shards"],
)
