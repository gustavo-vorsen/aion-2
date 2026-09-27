import streamlit as st

from aion import ui

st.caption(
    "Dimensional Invasion: charges regenerate daily up to a cap (reference: 1 per day, cap 7). "
    "Rewards depend on contribution."
)
ui.category_page(
    ["Dimensional Invasion"], key="invasion",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "charges_per_day", "charge_cap",
             "duration_minutes", "ruleset", "source_status", "notes"],
    reward_keys=["kinah_bound", "kinah_unbound", "enhancement_stones", "abyss_points"],
)
