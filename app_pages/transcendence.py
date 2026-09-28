import streamlit as st

from aion import ui

st.caption(
    "Main-focused Odyle sink. Each reward claim costs Odyle (the membership extra claim costs its own Odyle). "
    "Arcana itself is a reward destination, not a recurring activity."
)
ui.claims_box("Transcendence")
ui.category_page(
    ["Transcendence"], key="transcendence",
    columns=["name", "tier", "entry_item_level", "recommended_item_level", "duration_minutes",
             "ruleset", "source_status", "notes"],
    reward_keys=["kinah_unbound", "amplify_fragments", "enhancement_stones", "silentium", "arcana_rewards"],
    wide_rewards=True, shared_from_category=True,
)
