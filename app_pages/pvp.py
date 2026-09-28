import streamlit as st

from aion import ui

st.caption(
    "Instanced PvP is separate from Open Abyss and does not consume Abyss time. Model rewarded matches, "
    "win rewards and participation rewards as separate rows; put expected losses into minutes per rewarded attempt. "
    "Scope is provisional (per character) until Global verification."
)
ui.category_page(
    ["Instanced PvP"], key="pvp",
    columns=["name", "scope", "cadence", "attempts_per_reset",
             "weekly_claim_limit", "duration_minutes", "consumes_abyss_time", "ap_cap_category",
             "ruleset", "source_status", "notes"],
    reward_keys=["abyss_points", "silver_medals", "rank_points", "kinah_bound"],
)
