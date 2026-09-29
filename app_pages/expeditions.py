import streamlit as st

from aion import db, progress, ui

d = ui.data()
CATS = ["Expedition"]

st.caption(
    "Dungeon parameters. Each reward claim costs Odyle (see **Odyle budget**); the membership extra claim "
    "costs its own Odyle."
)

COLUMNS = ["dungeon", "tier", "entry_item_level", "recommended_item_level", "odyle_per_claim", "duration_minutes",
           "ruleset", "source_status", "notes"]
# The mode is implied by the tab, so only the dungeon is shown; the full name (used by the plan and loops) follows it.
db.execute("UPDATE activities SET name = dungeon || ' — ' || mode WHERE category = 'Expedition' AND dungeon <> '' "
           "AND mode <> '' AND name <> dungeon || ' — ' || mode")
ui.claims_box("Expedition", odyle_per_row=True)


def mode_section(mode: str) -> None:
    """Parameters and rewards for one mode (Exploration, Conquest Normal, Conquest Hard)."""
    key = mode.lower().replace(" ", "_")
    with st.container(border=True):
        st.subheader("Dungeon parameters")
        ui.activity_editor(CATS, key=f"dungeon_editor_{key}", columns=COLUMNS, new_category="Expedition", mode=mode,
                           shared_from_category=True)
    with st.container(border=True):
        st.subheader("Rewards per claim")
        acts = d.activities[d.activities["category"].isin(CATS) & (d.activities["mode"] == mode)]
        ids = acts["id"].astype(int).tolist()
        st.caption("Averages per claim = one full clear: the final cube plus both mid-bosses. Chance-based rewards "
                   "are averaged, e.g. Epic gear 2 = 1 guaranteed from the cube + 50 % from each mid-boss; Soul Codex "
                   "0.72 = 36 % from each mid-boss. Blank = not given.")
        if ids:
            ui.wide_reward_editor(ids, key=f"dungeon_rewards_{key}", label="Dungeon",
                                  row_names=acts.set_index("id")["dungeon"].fillna(acts.set_index("id")["name"]))
        else:
            st.caption("Add a dungeon above to fill its rewards.")
    with st.container(border=True):
        st.subheader("Pity (Condensed Cube Energy)")
        st.caption("Every claim adds to the dungeon's counter; at the required count you get one guaranteed reward "
                   "of your choice. Global playtest reward lists; counts from Korean sources (unverified).")
        pity = db.read_table("pity", where="category = 'Expedition' AND mode = ?", params=[mode], order="id")
        ui.table_editor(
            "pity", pity[["id", "dungeon", "claims_needed", "reward", "repeats", "max_times", "notes"]],
            key=f"pity_{key}", defaults={"category": "Expedition", "mode": mode},
            column_config={
                "dungeon": ui.cc.TextColumn("Dungeon", pinned=True),
                "claims_needed": ui.cc.NumberColumn("Claims needed", min_value=1, help="Cube claims per guaranteed reward."),
                "reward": ui.cc.TextColumn("Guaranteed reward (choose one)", width="large"),
                "repeats": ui.cc.CheckboxColumn("Repeats"),
                "max_times": ui.cc.NumberColumn("Max times", help="Blank = no limit."),
                "notes": ui.cc.TextColumn("Notes", width="medium"),
            },
            dash={"claims_needed": -1, "max_times": -1},
        )


MODES = ["Exploration", "Conquest Normal", "Conquest Hard"]


def mode_counts(mode: str) -> tuple[float, float]:
    """Filled / total cells of one mode's parameter and reward tables (whether shown or not)."""
    acts = d.activities[d.activities["category"].isin(CATS) & (d.activities["mode"] == mode)]
    p_f, p_t = ui.fill_counts(acts[COLUMNS])
    r_f, r_t = ui.reward_grid_counts(acts["id"].astype(int).tolist())
    pity = db.read_table("pity", where="category = 'Expedition' AND mode = ?", params=[mode])
    y_f, y_t = ui.fill_counts(pity[["dungeon", "claims_needed", "reward"]]) if not pity.empty else (0.0, 0.0)
    return p_f + r_f + y_f, p_t + r_t + y_t


counts = {m: mode_counts(m) for m in MODES}
for f, t in counts.values():  # the page % covers every mode, not only the one on screen
    progress.track(f, t)


def complete(*modes: str) -> bool:
    return all(counts[m][0] >= counts[m][1] for m in modes)


def done(*modes: str) -> str:
    return progress.mark(complete(*modes), "expeditions:" + " · ".join(modes))


# Same selectors as Nightmare: buttons for the mode, pills for the difficulty.
kind = st.segmented_control("Expedition", ["Exploration", "Conquest"], default="Exploration", required=True,
                            key="exp_kind", label_visibility="collapsed", width="stretch",
                            format_func={"Exploration": f"{done('Exploration')} :material/explore: Exploration",
                                         "Conquest": f"{done('Conquest Normal', 'Conquest Hard')} "
                                                     ":material/swords: Conquest"}.get)
with st.container(border=True):
    mode = "Exploration"
    if kind == "Conquest":
        difficulty = st.pills("Difficulty", ["Normal", "Hard"], default="Normal", required=True,
                              key="exp_difficulty", label_visibility="collapsed",
                              format_func={"Normal": f"{done('Conquest Normal')} :material/shield: Normal",
                                           "Hard": f"{done('Conquest Hard')} :material/local_fire_department: Hard"}.get)
        mode = f"Conquest {difficulty}"
    if complete(mode):
        progress.validate_toggle("expeditions:" + mode, f"{mode} validated")
    progress.pause_tracking()  # already counted above
    mode_section(mode)
    progress.resume_tracking()
