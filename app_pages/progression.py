import streamlit as st

from aion import progress, progression_ui

st.caption(
    "One-time / permanent progression, separate from the weekly loop. Each system has an **own faction** and an "
    "**enemy faction** section. Use **Scope = per_server** for progress shared by all characters."
)

all_items = progression_ui.items()
wide = progression_ui.rewards_wide()
progression_ui.summary(all_items, wide)

# Feathers, sealed dungeons and strongholds have their own pages (One-time content); still in the totals above.
SHOWN = [s for s in progression_ui.SYSTEMS if s.key not in ("feathers", "hidden_dungeons", "strongholds")]
tabs = progress.tabs("progression", [(s.key, f":material/{s.icon}: {s.label}") for s in SHOWN])
for tab, sys in zip(tabs, SHOWN):
    with tab:
        progression_ui.system_tab(sys, all_items, wide)
