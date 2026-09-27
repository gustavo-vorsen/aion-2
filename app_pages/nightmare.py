import streamlit as st

from aion import ui

st.caption(
    "Character-specific recurring content. Charges regenerate daily up to a cap "
    "(reference: 2/day, cap 14). Weekly runs = charges/day × 7. Nightmare unlocks through the MSQ chain."
)
ui.category_page(
    ["Nightmare"], key="nightmare",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "charges_per_day", "charge_cap",
             "duration_minutes", "kinah_cost", "ruleset", "source_status", "notes"],
    reward_keys=["nightmare_currency", "kinah_bound", "kinah_unbound", "enhancement_stones", "gear_drops"],
)
