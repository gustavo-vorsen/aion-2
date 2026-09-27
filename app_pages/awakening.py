import streamlit as st

from aion import ui

st.caption("Solo challenge, 3 per week per character (KR), Combat Power 1,000 or more.")
ui.category_page(
    ["Awakening Battle"], key="awakening",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "duration_minutes", "entry_item_level", "recommended_item_level", "ruleset", "source_status", "notes"],
    reward_keys=["silentium","ariel_shards","stigma_shards"],
)
