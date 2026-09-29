import streamlit as st

from aion import ui

st.caption(
    "Character-specific weekly attempts (reference: 3/week). Later level-50 Trial systems are not part "
    "of the Global level-45 launch loop."
)
ui.entries_box("Ascension Trial", "entries")
ui.category_page(
    ["Ascension Trial"], key="ascension",
    show_params=False,
    show_rewards=False,
)

# Trials > difficulty (with its required GS) > score brackets; the structure is editable on the page.
ui.tier_reward_editor(
    "Ascension Trial", {}, key="ascension_tiers", tier_label="Score",
    columns=[("Enhancement Stones", "enhancement_stones", ""), ("Growth Pet Chest", "growth_pet_chest", ""),
             ("Amplify Stone Fragments", "amplify_fragments", ""),
             ("Ascension Binding Chest", "ascension_binding_chest", "")],
    picker=False, group_names=("Trial", "Difficulty"), group_icons=("emoji_events", "signal_cellular_alt"),
    help_text="Rewards by final score (Global playtest data, Elyos). Add trials / difficulties with Edit; add score "
              "rows in the table.",
)
