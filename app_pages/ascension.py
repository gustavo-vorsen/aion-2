import streamlit as st

from aion import ui

st.caption(
    "Character-specific weekly attempts (reference: 3/week). Later level-50 Trial systems are not part "
    "of the Global level-45 launch loop."
)
ui.category_page(
    ["Ascension Trial"], key="ascension",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "duration_minutes", "entry_item_level", "ruleset", "source_status", "notes"],
    reward_keys=["manastones", "stigma_shards", "trial_currency", "enhancement_stones", "kinah_bound"],
)
