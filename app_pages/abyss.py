import streamlit as st

from aion import ui

d = ui.data()

st.caption(
    "Weekly Abyss time, weekly AP caps, Corridor rewards and Battlefield rewards are **separate constraints**. "
    "Open Abyss is modelled as one attempt per hour of Abyss time; Corridor is an opportunity activity "
    "whose AP can be excluded from the ordinary PvE cap."
)

with st.container(border=True):
    st.subheader("Time allowance & AP caps")
    with st.container(horizontal=True):
        ui.s_number("Weekly Abyss hours", "abyss_weekly_hours", min_value=0.0, step=0.5)
        ui.s_number("Weekly hours with membership", "abyss_membership_weekly_hours", min_value=0.0, step=0.5)
        ui.s_number("Extra hours from Rift Stones", "abyss_rift_stone_hours", min_value=0.0, step=0.5)
    with st.container(horizontal=True):
        ui.s_number("PvE AP weekly cap (0 = none)", "pve_ap_weekly_cap", min_value=0.0, step=1000.0)
        ui.s_number("PvP AP weekly cap (0 = none)", "pvp_ap_weekly_cap", min_value=0.0, step=1000.0)
        ui.s_number("Seasonal AP cap (0 = none)", "seasonal_ap_cap", min_value=0.0, step=1000.0)
    ui.s_text("AP cap model", "ap_cap_model")
    st.caption("KR/TW/community reference: 7 h/week base, 14 h/week with membership. All caps are ruleset-specific.")

ui.category_page(
    ["Abyss"], key="abyss",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "membership_bonus_attempts", "duration_minutes", "consumes_abyss_time", "ap_cap_category",
             "ruleset", "source_status", "notes"],
    reward_keys=["abyss_points", "kinah_unbound", "potential_stones", "abyss_potential_stones", "silver_medals",
                 "rank_points", "gear_drops"],
)
