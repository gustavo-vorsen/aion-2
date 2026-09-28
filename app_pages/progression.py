import streamlit as st

from aion import progress, progression_ui

st.caption(
    "One-time / permanent progression, separate from the weekly loop. Each system has an **own faction** and an "
    "**enemy faction** section. Use **Scope = per_server** for progress shared by all characters."
)

all_items = progression_ui.items()
wide = progression_ui.rewards_wide()
progression_ui.summary(all_items, wide)

tabs = progress.tabs("progression", [(s.key, f":material/{s.icon}: {s.label}") for s in progression_ui.SYSTEMS])
for tab, sys in zip(tabs, progression_ui.SYSTEMS):
    with tab:
        progression_ui.system_tab(sys, all_items, wide)
