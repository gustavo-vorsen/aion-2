import streamlit as st

from aion import progress, ui

st.caption(
    "Two separate systems. Normal Command Scrolls (reference 12/week/server) and Abyss Command Scrolls "
    "(reference 4 types × 5/week = 20/week/server) — 32 missions/week/server combined. Scope is provisional."
)
normal, abyss = progress.tabs("abyss_commands", [("normal", ":material/assignment: Normal Command Missions"), ("abyss", ":material/public: Abyss Command Scrolls")])
cols = ["name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
        "duration_minutes", "ap_cap_category", "ruleset", "source_status", "notes"]
with normal:
    progress.tab_done("abyss_commands", "normal")
    ui.category_page(["Command Missions"], key="cmd_normal", columns=cols,
                     reward_keys=["abyss_points", "hidden_cube_keys", "soul_crystals", "kinah_bound"])
with abyss:
    progress.tab_done("abyss_commands", "abyss")
    ui.category_page(["Abyss Commands"], key="cmd_abyss", columns=cols,
                     reward_keys=["abyss_points", "soul_crystals", "abyss_potential_stones", "kinah_bound"])
