"""Progression page: one-time / permanent progression systems, own and enemy faction."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from aion import calc, db, progress, seed, ui


@dataclass(frozen=True)
class System:
    key: str
    label: str
    icon: str
    reward_keys: tuple[str, ...]
    description: str


SYSTEMS: list[System] = [
    System("skills", "Skills", "bolt", ("skill_points",),
           "Skill points and Stigmas. Skill levels do NOT add Item Level (GS); they only add Combat Power."),
    System("daevanion", "Daevanion", "hub", ("gear_score", "daevanion_points"),
           "Boards are the sinks (+1 Item Level per point spent); the other rows are point sources not covered by "
           "other tabs (quests, sealed dungeons and strongholds list their own crystals)."),
    System("side_quests", "Side quests", "assignment", ("kinah_bound", "daevanion_points", "abyss_points"),
           "Regional quests per map and Rift quests in enemy territory."),
    System("strongholds", "Strongholds", "fort", ("kinah_bound", "noble_belt_scrolls", "titles"),
           "Garrisons: one-time chest. The only source of Noble Belt Enhance Scrolls."),
    System("hidden_dungeons", "Sealed dungeons", "door_front",
           ("kinah_bound", "daevanion_points", "skill_points", "enhancement_stones", "wing_featherdown",
            "pantheon_scraps", "abyss_points"),
           "Sealed ('?' on the map) dungeons: first-clear rewards."),
    System("feathers", "Empyrean traces", "flight",
           ("skill_points", "amulet_scrolls", "action_power", "hidden_cube_keys", "titles"),
           "Empyrean Traces raise the Monolith (shared per server). Rewards are the cumulative Monolith track."),
    System("genus", "Genus", "pets", ("titles",),
           "Genus Insight: pet understanding by killing monster types (shared per server). Count = pets in the genus."),
    System("titles", "Titles", "military_tech", ("titles",), "Title collection; owned stats always apply."),
    System("wardrobe", "Wardrobe", "checkroom", ("titles",), "Appearance collection (shared per server)."),
    System("wings", "Wings", "air", ("titles", "wing_featherdown"), "Wing collection and enhancement."),
    System("amulet_belt", "Amulet & belt", "diamond", ("gear_score", "amulet_scrolls", "noble_belt_scrolls"),
           "Revelation Amulet (Monolith scrolls) and Noble Belt (Stronghold scrolls): big Item Level gains."),
    System("pantheon", "Pantheon", "account_balance", ("pantheon_scraps",), "Statues and paintings: permanent stats."),
    System("arcana", "Arcana", "style", ("gear_score",),
           "Arcana cards from Transcendence (repeatable). Biggest Item Level jump per card."),
]
FACTIONS = [("own", "Own faction", "shield"), ("enemy", "Enemy faction", "swords")]
SCOPES = calc.SCOPES


def items() -> pd.DataFrame:
    return db.read_table("progression_items", order="system, faction, sort_order, id")


def rewards_wide() -> pd.DataFrame:
    r = db.read_table("progression_rewards")
    if r.empty:
        return pd.DataFrame()
    r["amount"] = r["amount"] * r["draws"].fillna(1.0) * r["chance"].fillna(100.0) / 100.0  # expected value
    return r.pivot_table(index="item_id", columns="currency_key", values="amount", aggfunc="sum").fillna(0.0)


def gs_rates() -> pd.Series:
    """Item Level (GS) per unit of each reward type (editable on this page)."""
    return db.read_table("currencies").set_index("key")["gs_per_unit"].fillna(0.0).astype(float)


def item_gs(df: pd.DataFrame, wide: pd.DataFrame, rates: pd.Series) -> pd.DataFrame:
    """Per item: GS per completion (Σ reward × GS per unit) and GS total (× count, enabled rows only)."""
    w = wide.reindex(index=df["id"], columns=wide.columns if not wide.empty else []).fillna(0.0)
    r = rates.reindex(w.columns).fillna(0.0)
    gs_each = (w * r.values).sum(axis=1) if len(w.columns) else pd.Series(0.0, index=df["id"])
    names = db.read_table("currencies").set_index("key")["name"]
    how = [" + ".join(f"{names.get(k, k)} ×{r[k]:g}" for k in w.columns if r[k] and w.at[i, k]) for i in df["id"]]
    out = pd.DataFrame({
        "Item": df["name"].values,
        "GS per completion": gs_each.values,
        "Count": df["count"].fillna(1).astype(float).values,
        "From": how,
    })
    out["GS total"] = out["GS per completion"] * out["Count"]
    return out[["Item", "GS per completion", "Count", "GS total", "From"]]


def totals(df: pd.DataFrame, wide: pd.DataFrame, rates: pd.Series) -> dict[str, float]:
    """Totals for one completion of every row (reward × count)."""
    on = df
    if on.empty:
        return {"hours": 0.0, "gs": 0.0, "daevanion_points": 0.0, "count": 0.0, "capacity": 0.0}
    w = wide.reindex(index=on["id"]).fillna(0.0)
    per = w.mul(on["count"].fillna(1).astype(float).values, axis=0).sum()
    return {
        "hours": float((on["count"].fillna(1) * on["minutes_each"].fillna(0)).sum() / 60.0),
        "gs": float(item_gs(on, wide, rates)["GS total"].sum()),
        "daevanion_points": float(per.get("daevanion_points", 0.0)),
        "count": float(on["count"].fillna(1).sum()),
        "capacity": float(on["capacity"].fillna(0).sum()),
    }


def gs_conversion_editor() -> None:
    keys = {k for s in SYSTEMS for k in s.reward_keys} | {"gear_score", "daevanion_points"}
    cur = db.read_table("currencies", order="sort_order, key")
    cur = cur[cur["key"].isin(keys)]
    ui.table_editor(
        "currencies", cur[["key", "name", "gs_per_unit", "notes"]], key="gs_conversion",
        allow_add=False, allow_delete=False, disabled=["key", "name"],
        column_config={
            "key": None,
            "name": ui.cc.TextColumn("Reward"),
            "gs_per_unit": ui.cc.NumberColumn("Item Level (GS) per unit", format="%.3f"),
            "notes": ui.cc.TextColumn("Notes", width="large"),
        },
    )
    st.caption("Researched: each Daevanion point spent = +1 Item Level; direct Item Level (e.g. Arcana) counts 1:1; "
               "skill levels add Combat Power only (0 GS); Amulet/Belt scroll and title amounts were not found (0 = unknown).")


def summary(all_items: pd.DataFrame, wide: pd.DataFrame) -> None:
    rates = gs_rates()
    rows = []
    for sys in SYSTEMS:
        for f, flabel, _ in FACTIONS:
            t = totals(all_items[(all_items["system"] == sys.key) & (all_items["faction"] == f)], wide, rates)
            rows.append({"System": sys.label, "Faction": flabel, "Items": t["count"], "Hours": t["hours"],
                         "GS": t["gs"], "Daevanion points": t["daevanion_points"]})
    df = pd.DataFrame(rows)
    with st.container(horizontal=True):
        st.metric("Total hours", f"{df['Hours'].sum():.1f}", border=True)
        st.metric("Item Level (GS) from progression", ui.fmt(df["GS"].sum()), border=True,
                  help="Σ rewards × GS per unit (see GS conversion below).")
        st.metric("Daevanion points earned", ui.fmt(df["Daevanion points"].sum()), border=True)
        st.metric("Enemy-faction hours", f"{df.loc[df['Faction'] == 'Enemy faction', 'Hours'].sum():.1f}", border=True)
    with st.expander("Item Level (GS) by system", icon=":material/table_chart:"):
        ui.show(df, hide_index=True, column_config={
            "Items": ui.cc.NumberColumn(format="%.0f"), "Hours": ui.cc.NumberColumn(format="%.1f"),
            "GS": ui.cc.NumberColumn("Item Level (GS)", format="%,.0f"),
            "Daevanion points": ui.cc.NumberColumn(format="%,.0f")})
    with st.expander("GS conversion (Item Level per reward unit)", icon=":material/calculate:"):
        gs_conversion_editor()


def system_tab(sys: System, all_items: pd.DataFrame, wide: pd.DataFrame) -> None:
    progress.tab_done("progression", sys.key)
    st.caption(sys.description + " Rewards are per completion of one row; totals multiply by **Count**.")
    rates = gs_rates()
    if sys.key == "daevanion":
        earned = totals(all_items, wide, rates)["daevanion_points"]
        capacity = totals(all_items[all_items["system"] == "daevanion"], wide, rates)["capacity"]
        with st.container(horizontal=True):
            st.metric("Daevanion points earned (all tabs)", ui.fmt(earned), border=True)
            st.metric("Board capacity (known boards)", ui.fmt(capacity), border=True,
                      help="Nezekan and Triniel totals were not found.")
            st.metric("Item Level from Daevanion", ui.fmt(min(earned, capacity) if capacity else earned), border=True,
                      help="+1 Item Level per point spent, capped by the known board capacity.")
    for f, flabel, icon in FACTIONS:
        df = all_items[(all_items["system"] == sys.key) & (all_items["faction"] == f)]
        t = totals(df, wide, rates)
        with st.container(border=True):
            st.subheader(f":material/{icon}: {flabel}")
            with st.container(horizontal=True):
                st.metric("Items", f"{t['count']:.0f}", border=True)
                st.metric("Hours", f"{t['hours']:.1f}", border=True)
                st.metric("Item Level (GS)", ui.fmt(t["gs"]), border=True)
                st.metric("Daevanion points", ui.fmt(t["daevanion_points"]), border=True)
            st.markdown("**Parameters**")
            cols = ["id", "name", "region", "level_req", "count", *(["capacity"] if sys.key == "daevanion" else []),
                    "minutes_each", "scope", "ruleset", "source_status", "notes"]
            ui.table_editor(
                "progression_items", df[cols],
                key=f"prog_{sys.key}_{f}", defaults={"system": sys.key, "faction": f},
                column_config={
                    "name": ui.cc.TextColumn("Name", required=True, pinned=True),
                    "region": ui.cc.TextColumn("Region"),
                    "level_req": ui.cc.NumberColumn("Level req."),
                    "count": ui.cc.NumberColumn("Count", min_value=0, help="How many of these exist."),
                    "capacity": ui.cc.NumberColumn("Board points", min_value=0, help="Points this board can take."),
                    "minutes_each": ui.cc.NumberColumn("Minutes each", min_value=0, format="%.1f"),
                    "scope": ui.cc.SelectboxColumn("Scope", options=SCOPES,
                                                   help="per_server = shared progress, done once for all characters."),
                    "ruleset": ui.cc.SelectboxColumn("Ruleset", options=[r[0] for r in seed.RULESETS]),
                    "source_status": ui.cc.SelectboxColumn("Source status", options=calc.SOURCE_STATUSES),
                    "notes": ui.cc.TextColumn("Notes", width="large"),
                },
            )
            if df.empty:
                st.caption("Add a row above to start.")
                continue
            st.markdown("**Rewards per completion**")
            ui.reward_editor(
                df["id"].astype(int).tolist(), key=f"prog_rw_{sys.key}_{f}", currency_keys=list(sys.reward_keys),
                table="progression_rewards", fk="item_id", row_names=df.set_index("id")["name"],
                label="Item",
            )
            st.markdown("**Item Level (GS) given**")
            ui.show(item_gs(df, wide, rates), hide_index=True, column_config={
                "GS per completion": ui.cc.NumberColumn(format="%,.1f"),
                "Count": ui.cc.NumberColumn(format="%.0f"),
                "GS total": ui.cc.NumberColumn(format="%,.1f"),
                "From": ui.cc.TextColumn("Where the GS comes from", width="large"),
            })
