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

BRACKETS = [f"Score ≥ {n:,}" for n in (10, 100, 200, 500, 1000, 1500, 2000, 2500, *range(3000, 14001, 1000))]
TRIALS = ["Chamber of the Dead"]  # one tab per trial; other trials may have different tables
ui.tier_reward_editor(
    "Ascension Trial", {t: BRACKETS for t in TRIALS}, key="ascension_tiers", tier_label="Score",
    columns=[("Silentium", "silentium", ""), ("Ariel fragments", "ariel_shards", ""),
             ("Manastone/Soulstone Chest", "manastones", ""), ("Stigma Shards", "stigma_shards", ""),
             ("Enhancement Stones", "enhancement_stones", "")],
    picker=False, group_names=("Trial",), group_icons=("emoji_events",),
    help_text="Rewards by final score (reference values). Add trials with Edit trials; add score rows in the table.",
)
