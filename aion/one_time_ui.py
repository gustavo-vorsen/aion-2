"""Shared bits of the One-time content pages."""
from __future__ import annotations

import streamlit as st

from aion import db, ui

FACTIONS = ["Asmodian", "Elyos"]


def my_faction() -> str:
    chars = ui.data().characters
    mains = chars[chars["is_main"].astype(bool)] if not chars.empty else chars
    f = (mains if not mains.empty else chars)["faction"].dropna()
    return f.iloc[0] if not f.empty and f.iloc[0] in FACTIONS else "Asmodian"


def side_picker(key: str) -> tuple[str, bool]:
    """Elyos / Asmodian buttons (your side first). Returns (faction, is your side)."""
    mine = my_faction()
    order = [mine, *[f for f in FACTIONS if f != mine]]
    pick = st.segmented_control(
        "Side", order, default=mine, required=True, key=key, label_visibility="collapsed", width="stretch",
        format_func=lambda f: f":material/shield: {f} (your side)" if f == mine else f":material/swords: {f}")
    return pick or mine, (pick or mine) == mine


def done_list(kind: str, faction: str, key: str) -> None:
    """Per-item checklist (name, region, level, done)."""
    rows = db.read_table("one_time", where="kind = ? AND faction = ?", params=[kind, faction], order="region, level, id")
    ui.table_editor(
        "one_time", rows[["id", "name", "region", "level", "done", "notes"]], key=key,
        defaults={"kind": kind, "faction": faction},
        column_config={"name": ui.cc.TextColumn("Name", pinned=True, width="medium"),
                       "region": ui.cc.TextColumn("Region"), "level": ui.cc.NumberColumn("Level"),
                       "done": ui.cc.CheckboxColumn("Done"), "notes": ui.cc.TextColumn("Notes", width="medium")})
    done = int(rows["done"].fillna(False).astype(bool).sum()) if not rows.empty else 0
    st.caption(f"Done **{done} / {len(rows)}**.")


def rewards_for(system: str, own: bool, key: str) -> None:
    """Per-clear rewards: the Progression row for your side or the other side (feeds the Item Level totals)."""
    items = db.read_table("progression_items", where="system = ? AND faction = ?", params=[system, "own" if own else "enemy"])
    if items.empty:
        st.caption("No rewards row.")
        return
    ui.reward_editor(items["id"].astype(int).tolist(), key=key, table="progression_rewards", fk="item_id",
                     row_names=items.set_index("id")["name"], label="Item")
