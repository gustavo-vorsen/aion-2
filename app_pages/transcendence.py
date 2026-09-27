import streamlit as st

from aion import ui

st.caption(
    "Main-focused Odyle sink. Each reward claim costs Odyle (the membership extra claim costs its own Odyle). "
    "Arcana itself is a reward destination, not a recurring activity."
)
ui.category_page(
    ["Transcendence"], key="transcendence",
    columns=["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
             "duration_minutes", "odyle_per_claim", "reward_claims_per_attempt", "membership_extra_claims",
             "weekly_claim_limit", "entry_item_level", "ruleset", "source_status", "notes"],
    reward_keys=["kinah_unbound", "amplify_fragments", "enhancement_stones", "silentium", "arcana_rewards"],
)
