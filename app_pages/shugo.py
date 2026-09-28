import streamlit as st

from aion import ui

st.caption(
    "Shugo Festival: 7 reward keys per week, shared per server (Global membership lists no extra keys; KR gives 14). Each key is one card pick; "
    "placement sets how many picks a run offers (1st–2nd: 6, 3rd–5th: 4). Rewards below are averages per pick, "
    "from the in-game reward table; both tables count toward the plan."
)
ui.entries_box("Shugo Festival", "keys")
ui.category_page(
    ["Shugo Festival"], key="shugo",
    show_params=False,
    show_rewards=False,
)
d = ui.data()
ids = d.activities.loc[d.activities["category"] == "Shugo Festival", "id"].astype(int).tolist()
KEYS = ["centuryroot_tokens", "gear_unique", "gear_epic", "gear_rare", "gear_common", "scrolls_common", "soul_codex",
        "artwork_scraps", "enhancement_stones", "abyss_points", "seed_of_detection", "odyle_material", "fine_odyle",
        "pure_odyle", "radiant_odyle", "refining_stone", "expert_refining_stone", "artisan_refining_stone",
        "artisan_ultimate_refining_stone"]
if ids:
    with st.container(border=True):
        st.subheader("Rewards per pick")
        st.caption("As listed in game. Chance % includes the pool's own chance (e.g. Reward Pool 2 at 15 %); gear and "
                   "scrolls are one line per grade.")
        highlights, basic = st.tabs([":material/star: Reward highlights", ":material/inventory_2: Basic rewards"])
        with highlights:
            ui.pooled_reward_editor(ids, key="shugo_highlights", prefix="Highlights · ", currency_keys=KEYS)
        with basic:
            ui.pooled_reward_editor(ids, key="shugo_basic", prefix="Basic · ", currency_keys=KEYS)
