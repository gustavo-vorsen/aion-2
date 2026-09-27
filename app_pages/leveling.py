import streamlit as st

from aion import progress
from aion.leveling_ui import leveling_defaults

st.caption(
    "Fixed blocks: **1→22**, **22→45** and **Cleanup** at 45. Durations are planning values, not guaranteed "
    "Global completion times. Alt cleanup is lower by default because shared progression isn't repeated."
)
main, alt = progress.tabs("leveling", [("main", ":material/star: Main"), ("alt", ":material/people: Alt")])
with main:
    progress.tab_done("leveling", "main")
    leveling_defaults("main")
with alt:
    progress.tab_done("leveling", "alt")
    leveling_defaults("alt")
