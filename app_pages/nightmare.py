import streamlit as st

from aion import ui
from aion.tier_specs import NIGHTMARE

st.caption(
    "Character-specific recurring content. Charges regenerate daily up to a cap "
    "(reference: 2/day, cap 14). Weekly runs = charges/day × 7. Nightmare unlocks through the MSQ chain."
)
ui.entries_box("Nightmare", "entries")
ui.category_page(["Nightmare"], key="nightmare", show_params=False, show_rewards=False)
ui.tier_reward_editor(
    NIGHTMARE.category, NIGHTMARE.groups, NIGHTMARE.columns, key=NIGHTMARE.key, tier_label=NIGHTMARE.tier_label,
    auto_tier=True, group_names=NIGHTMARE.group_names, group_icons=NIGHTMARE.group_icons,
    help_text="Layer > tier > level. Rows can be added and removed. The plan counts the repeat reward of the "
              "highest level you filled; first clears are one-time and not counted. A tier is done when every "
              "cell of its table is filled.",
)
