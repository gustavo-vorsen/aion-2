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
        if ids:
            ui.wide_reward_editor(ids, key=f"dungeon_rewards_{key}", label="Dungeon",
                                  row_names=acts.set_index("id")["dungeon"].fillna(acts.set_index("id")["name"]))
        else:
            st.caption("Add a dungeon above to fill its rewards.")


MODES = ["Exploration", "Conquest Normal", "Conquest Hard"]


def mode_counts(mode: str) -> tuple[float, float]:
    """Filled / total cells of one mode's parameter and reward tables (whether shown or not)."""
    acts = d.activities[d.activities["category"].isin(CATS) & (d.activities["mode"] == mode)]
    p_f, p_t = ui.fill_counts(acts[COLUMNS])
    r_f, r_t = ui.reward_grid_counts(acts["id"].astype(int).tolist())
    return p_f + r_f, p_t + r_t


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
