import streamlit as st

from aion import ui

st.caption("Field and world bosses on fixed timers. Kinah per kill is capped (Nahma 1M, Kaira/Executors 200k); values here are the caps.")
ui.category_page(
    ["Field Bosses"], key="field_bosses",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "duration_minutes", "entry_item_level", "recommended_item_level", "ruleset", "source_status", "notes"],
    reward_keys=["kinah_unbound","kinah_bound","abyss_points","gear_drops"],
)
