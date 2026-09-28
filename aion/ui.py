"""Shared Streamlit widgets: DB-backed editors, settings inputs, status badges, charts."""
from __future__ import annotations

import copy
import datetime as dt
import re
import uuid
from typing import Any, Callable

import altair as alt
import pandas as pd
import streamlit as st

from aion import calc, db, seed, progress

cc = st.column_config


# ------------------------------------------------------------------ data access

def data() -> calc.Data:
    """Fresh data for this rerun (SQLite is small; edits must show immediately)."""
    if "_data" not in st.session_state or st.session_state.get("_data_run") != st.session_state.get("_run_id"):
        st.session_state["_data"] = calc.load()
        st.session_state["_data_run"] = st.session_state.get("_run_id")
    return st.session_state["_data"]


def plan() -> pd.DataFrame:
    if st.session_state.get("_plan_run") != st.session_state.get("_run_id"):
        st.session_state["_plan"] = calc.build_plan(data())
        st.session_state["_plan_run"] = st.session_state.get("_run_id")
    return st.session_state["_plan"]


def invalidate() -> None:
    st.session_state["_run_id"] = uuid.uuid4().hex


# ------------------------------------------------------------------ settings widgets

def _save_setting(k: str, widget_key: str) -> None:
    raw = st.session_state[widget_key]
    v = raw
    if isinstance(v, dt.time):
        v = v.strftime("%H:%M")
    elif isinstance(v, dt.date):
        v = v.isoformat()
    db.set_setting(k, v)
    # Keep other widgets bound to the same setting (e.g. sidebar + page) in sync.
    for other in [x for x in st.session_state if str(x).startswith(f"setting__{k}__") and x != widget_key]:
        st.session_state[other] = raw
    invalidate()


def _kw(k: str, where: str) -> dict:
    wk = f"setting__{k}__{where}"
    return dict(key=wk, on_change=_save_setting, args=(k, wk))


def s_number(label: str, k: str, step: float = 1.0, where: str = "page", **kw) -> float:
    return st.number_input(label, value=float(data().settings[k]), step=float(step), **_kw(k, where), **kw)


def s_toggle(label: str, k: str, where: str = "page", **kw) -> bool:
    return st.toggle(label, value=bool(data().settings[k]), **_kw(k, where), **kw)


def s_select(label: str, k: str, options: list, format_func: Callable = str, where: str = "page", **kw) -> Any:
    cur = data().settings[k]
    return st.selectbox(label, options, index=options.index(cur) if cur in options else 0,
                        format_func=format_func, **_kw(k, where), **kw)


def s_multiselect(label: str, k: str, options: list, format_func: Callable = str, where: str = "page", **kw) -> list:
    cur = [x for x in data().settings[k] if x in options]
    return st.multiselect(label, options, default=cur, format_func=format_func, **_kw(k, where), **kw)


def s_segmented(label: str, k: str, options: list, where: str = "page", **kw) -> Any:
    return st.segmented_control(label, options, default=data().settings[k], **_kw(k, where), **kw)


def s_date(label: str, k: str, where: str = "page", **kw) -> dt.date:
    return st.date_input(label, value=dt.date.fromisoformat(data().settings[k]), **_kw(k, where), **kw)


def s_time(label: str, k: str, where: str = "page", **kw) -> dt.time:
    return st.time_input(label, value=dt.time.fromisoformat(data().settings[k]), **_kw(k, where), **kw)


def s_text(label: str, k: str, where: str = "page", **kw) -> str:
    return st.text_input(label, value=str(data().settings[k]), **_kw(k, where), **kw)


# ------------------------------------------------------------------ generic DB editor

READ_ONLY_CSS = {"background-color": "rgba(128, 128, 128, 0.12)", "color": "#8b8d98"}


def show(df: pd.DataFrame, **kw):
    """Read-only table: every value is grayed out (nothing here can be edited)."""
    data = df.reset_index(drop=True) if isinstance(df, pd.DataFrame) and not kw.get("keep_index") else df
    kw.pop("keep_index", None)
    if isinstance(data, pd.DataFrame) and not data.empty and data.columns.is_unique:
        data = data.style.set_properties(**READ_ONLY_CSS)
    return st.dataframe(data, **kw)

def _apply_edits(key: str, row_keys: list[dict], on_update: Callable, on_insert: Callable | None,
                 on_delete: Callable | None, base_key: str) -> None:
    state = st.session_state[key]
    # New widget key next run: the editor restarts from the saved data (no stale positional edits).
    st.session_state[f"_ver_{base_key}"] = st.session_state.get(f"_ver_{base_key}", 0) + 1
    for pos, changes in state.get("edited_rows", {}).items():
        on_update(row_keys[int(pos)], changes)
    if on_insert:
        for new in state.get("added_rows", []):
            on_insert(new)
    if on_delete:
        for pos in state.get("deleted_rows", []):
            on_delete(row_keys[int(pos)])
    invalidate()


# Columns that may legitimately stay blank (blank = no limit / unknown / optional): not counted as unfilled.
OPTIONAL_COLUMNS = {
    "notes", "Notes", "ruleset", "source_status", "pool", "Pool", "dungeon", "mode", "tier", "description", "color",
    "attempts_per_reset", "charges_per_day", "charge_cap", "weekly_claim_limit", "membership_bonus_attempts",
    "membership_extra_claims", "kinah_cost", "ap_cost", "ticket_cost",
    "Planned runs", "capacity", "level_req", "region", "estimated_kinah_value", "sort_order",
}


def fill_counts(df: pd.DataFrame, skip: set[str] | frozenset = frozenset()) -> tuple[float, float]:
    """(filled, total) required cells of a table."""
    cols = [c for c in df.columns if c not in OPTIONAL_COLUMNS and c not in skip]
    if df.empty or not cols:
        return 0.0, 0.0
    block = df[cols]
    filled = block.notna() & block.astype(str).ne("")
    return float(filled.values.sum()), float(block.size)


def track_fill(df: pd.DataFrame, skip: set[str] | frozenset = frozenset()) -> None:
    """Report a table's filled / total required cells to the page's fill percentage."""
    progress.track(*fill_counts(df, skip))


def reward_grid_counts(activity_ids: list[int]) -> tuple[float, float]:
    """(filled, total) cells of the wide rewards grid for these activities (as wide_reward_editor shows it)."""
    raw = db.read_table("activity_rewards")
    raw = raw[raw["activity_id"].isin(activity_ids) & (raw["pool"].fillna("") == "")] if not raw.empty else raw
    keys = raw["currency_key"].unique() if not raw.empty else []
    have = set(zip(raw["activity_id"], raw["currency_key"])) if not raw.empty else set()
    return float(len(have)), float(len(activity_ids) * len(keys))


def editor(df: pd.DataFrame, key: str, row_keys: list[dict], on_update: Callable,
           on_insert: Callable | None = None, on_delete: Callable | None = None, **kw) -> pd.DataFrame:
    """st.data_editor that writes every change straight to SQLite (and counts toward the page's fill %)."""
    track_fill(df, {c for c in (kw.get("disabled") or []) if isinstance(c, str)})
    num_rows = "dynamic" if (on_insert and on_delete) else "add" if on_insert else "delete" if on_delete else "fixed"
    wkey = f"{key}__v{st.session_state.get(f'_ver_{key}', 0)}"
    data = df.reset_index(drop=True)
    read_only = [c for c in (kw.get("disabled") or []) if isinstance(c, str) and c in data.columns]
    if read_only:
        # Styler colors only apply to non-editable columns: gray them out.
        data = data.style.set_properties(subset=read_only, **READ_ONLY_CSS)
    return st.data_editor(
        data, key=wkey, num_rows=num_rows, hide_index=True,
        on_change=_apply_edits, args=(wkey, row_keys, on_update, on_insert, on_delete, key), **kw,
    )


def table_editor(table: str, df: pd.DataFrame, key: str, defaults: dict | None = None,
                 allow_add: bool = True, allow_delete: bool = True, after_insert: Callable | None = None,
                 **kw) -> pd.DataFrame:
    """Editor for tables with an integer `id` primary key (hidden from the grid)."""
    pk = "key" if table in ("currencies", "rulesets") else "id"
    row_keys = [{pk: (v.item() if hasattr(v, "item") else v)} for v in df[pk]]

    def ins(new: dict) -> None:
        values = {**(defaults or {}), **{k: v for k, v in new.items() if v is not None}}
        if pk == "key" and not values.get("key"):
            base = re.sub(r"[^a-z0-9]+", "_", str(values.get("name") or "custom").lower()).strip("_") or "custom"
            values["key"] = base if base not in set(df[pk]) else f"{base}_{len(df) + 1}"
        new_id = db.insert(table, values)
        if after_insert:
            after_insert(new_id, values)

    shown = df if pk != "id" else df.drop(columns=["id"])
    return editor(
        shown, key, row_keys,
        on_update=lambda rk, ch: db.update(table, rk, ch),
        on_insert=ins if allow_add else None,
        on_delete=(lambda rk: db.delete(table, rk)) if allow_delete else None,
        **kw,
    )


# ------------------------------------------------------------------ activities

STATUS_OPTIONS = list(calc.STATUS_COLORS)


def ruleset_badges() -> None:
    with st.container(horizontal=True):
        for label, color in calc.STATUS_COLORS.items():
            st.badge(label, color=color)


TIER_OPTIONS = ["1★", "2★", "3★", "4★", "5★", "Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5"]
MODE_OPTIONS = ["Exploration", "Conquest Normal", "Conquest Hard"]


def _options(base: list[str], col: str) -> list[str]:
    """Fixed choices plus any value already used, so existing rows stay valid."""
    used = [v for v in data().activities[col].dropna().unique() if v not in base]
    return [*base, *sorted(used)]


def activity_columns() -> dict:
    return {
        "tier": cc.SelectboxColumn("Tier", options=_options(TIER_OPTIONS, "tier")),
        "dungeon": cc.TextColumn("Dungeon", pinned=True),
        "mode": cc.SelectboxColumn("Mode", options=_options(MODE_OPTIONS, "mode")),
        "name": cc.TextColumn("Activity", pinned=True, width="medium"),
        "category": cc.TextColumn("Category"),
        "scope": cc.SelectboxColumn("Scope", options=calc.SCOPES, required=True),
        "cadence": cc.SelectboxColumn("Cadence", options=calc.CADENCES, required=True),
        "attempts_per_reset": cc.NumberColumn("Attempts / reset", help="Blank = unbounded (Odyle-limited)."),
        "membership_bonus_attempts": cc.NumberColumn("+ Membership attempts"),
        "charges_per_day": cc.NumberColumn("Charges / day"),
        "charge_cap": cc.NumberColumn("Charge cap"),
        "reward_claims_per_attempt": cc.NumberColumn("Claims / attempt"),
        "membership_extra_claims": cc.NumberColumn("+ Membership claims", help="Each extra claim costs its own Odyle."),
        "weekly_claim_limit": cc.NumberColumn("Weekly claim cap"),
        "duration_minutes": cc.NumberColumn("Minutes / attempt", format="%.1f"),
        "odyle_per_claim": cc.NumberColumn("Odyle / claim"),
        "kinah_cost": cc.NumberColumn("Kinah cost", format="%,.0f"),
        "ap_cost": cc.NumberColumn("AP cost"),
        "ticket_cost": cc.NumberColumn("Tickets"),
        "entry_item_level": cc.NumberColumn("Required GS"),
        "recommended_item_level": cc.NumberColumn("Recommended GS"),
        "consumes_abyss_time": cc.CheckboxColumn("Uses Abyss time"),
        "ap_cap_category": cc.SelectboxColumn("AP cap", options=calc.AP_CAP_CATEGORIES),
        "forced_initial_claims": cc.NumberColumn("Forced initial claims"),
        "guaranteed_reward_after_claims": cc.NumberColumn("Guarantee after claims"),
        "guaranteed_reward_value": cc.NumberColumn("Guarantee value"),
        "repeat_after_guarantee": cc.CheckboxColumn("Repeat after guarantee"),
        "ruleset": cc.SelectboxColumn("Ruleset", options=[r[0] for r in seed.RULESETS]),
        "source_status": cc.SelectboxColumn("Source status", options=calc.SOURCE_STATUSES),
        "notes": cc.TextColumn("Notes", width="large"),
        "sort_order": None,
    }


BASE_ACTIVITY_COLS = [
    "name", "scope", "cadence", "attempts_per_reset",
    "membership_bonus_attempts", "duration_minutes", "ruleset", "source_status", "notes",
]


SHARED_COLUMNS = ("odyle_per_claim", "reward_claims_per_attempt", "membership_extra_claims", "scope", "cadence")


def _shared_defaults(rows: pd.DataFrame) -> dict:
    return {} if rows.empty else {c: rows.iloc[0][c] for c in SHARED_COLUMNS if pd.notna(rows.iloc[0][c])}


def activity_editor(categories: list[str], key: str, columns: list[str] | None = None,
                    new_category: str | None = None, cadences: list[str] | None = None,
                    mode: str | None = None, shared_from_category: bool = False) -> None:
    """cadences: only show activities with these cadences (new rows get the first one).
    mode: only show activities with this mode (e.g. an Expedition tab; new rows get it).
    shared_from_category: new rows copy the category's shared settings (Odyle per claim, claims, scope, cadence)."""
    acts = data().activities
    df = acts[acts["category"].isin(categories)]
    if cadences:
        df = df[df["cadence"].isin(cadences)]
    if mode:
        df = df[df["mode"] == mode]
    cols = ["id", *(columns or BASE_ACTIVITY_COLS)]
    if len(categories) > 1 and "category" not in cols:
        cols.insert(2, "category")
    table_editor(
        "activities", df[cols], key=key,
        defaults={"category": new_category or categories[0], "sort_order": int(acts["sort_order"].max() or 0) + 1,
                  **({"cadence": cadences[0]} if cadences else {}), **({"mode": mode} if mode else {}),
                  **(_shared_defaults(acts[acts["category"].isin(categories)]) if shared_from_category else {})},
        column_config=activity_columns(),
    )


def reward_editor(activity_ids: list[int], key: str, currency_keys: list[str] | None = None, *,
                  table: str = "activity_rewards", fk: str = "activity_id",
                  row_names: pd.Series | None = None, label: str = "Activity", only_listed: bool = False,
                  pool_prefix: str | None = None, show_pool: bool = True) -> None:
    """Rewards table, one row per reward line, like the in-game reward list:
    [label] | Pool | Reward | Amount | Times | Chance % | Average (= amount × times × chance, what the plan counts).

    The same reward may appear on several rows (e.g. 60 at 50 %, 80 at 30 %). currency_keys: this content's reward
    types (offered first). only_listed: show and offer just those. pool_prefix: show only the lines whose pool
    starts with it (e.g. "Highlights · "), without the prefix. Removing a row removes that reward line.
    """
    d = data()
    row_names = d.activities.set_index("id")["name"] if row_names is None else row_names
    names = dict(zip(d.currencies["key"], d.currencies["name"]))
    order = {k: i for i, k in enumerate(d.currencies["key"])}
    page_keys = [k for k in currency_keys or [] if k in names]
    rank = {k: i for i, k in enumerate(page_keys)}
    options = page_keys if only_listed else page_keys + [k for k in d.currencies["key"] if k not in rank]
    key_by_name = {names[k]: k for k in options}
    ids = [int(i) for i in activity_ids]
    multi = len(ids) > 1
    id_by_name = {row_names.get(i, str(i)): i for i in ids}

    raw = db.read_table(table)
    if not raw.empty:
        raw = raw[raw[fk].isin(ids) & raw["currency_key"].isin(options)]
        if pool_prefix is not None:
            raw = raw[raw["pool"].fillna("").str.startswith(pool_prefix)]
            raw = raw.assign(pool=raw["pool"].str[len(pool_prefix):])
        raw = raw.assign(
            _row=raw[fk].map({i: n for n, i in enumerate(ids)}),
            _pool=raw.groupby("pool", dropna=False)["id"].transform("min"),  # pools in the order they were entered
            _cur=raw["currency_key"].map(lambda k: rank.get(k, len(rank) + order.get(k, 0))),
        ).sort_values(["_row", "_pool", "_cur", "amount"])
    df = pd.DataFrame({
        label: [row_names.get(i, str(i)) for i in raw[fk]] if not raw.empty else [],
        "Pool": raw["pool"].fillna("").values if not raw.empty else [],
        "Reward": [names.get(k, k) for k in raw["currency_key"]] if not raw.empty else [],
        "Amount": raw["amount"].astype(float).values if not raw.empty else [],
        "Times": raw["draws"].fillna(1.0).astype(float).values if not raw.empty else [],
        "Chance %": raw["chance"].fillna(100.0).astype(float).values if not raw.empty else [],
    })
    df = df.astype({label: "object", "Pool": "object", "Reward": "object",
                    "Amount": float, "Times": float, "Chance %": float})  # empty tables need explicit types
    df["Average"] = df["Amount"].fillna(0) * df["Times"].fillna(1) * df["Chance %"].fillna(100) / 100
    if not multi:
        df = df.drop(columns=[label])
    if not show_pool:
        df = df.drop(columns=["Pool"])
    row_keys = [{"id": int(i)} for i in raw["id"]] if not raw.empty else []
    fields = {"Pool": "pool", "Amount": "amount", "Times": "draws", "Chance %": "chance"}
    defaults = {"pool": "", "amount": 0.0, "draws": 1.0, "chance": 100.0}

    def values_from(changes: dict) -> dict:
        vals = {col: (defaults[col] if changes[c] is None else changes[c]) for c, col in fields.items() if c in changes}
        if pool_prefix is not None and "pool" in vals:
            vals["pool"] = pool_prefix + vals["pool"]
        if changes.get("Reward") in key_by_name:
            vals["currency_key"] = key_by_name[changes["Reward"]]
        if changes.get(label) in id_by_name:
            vals[fk] = id_by_name[changes[label]]
        return vals

    def ins(new: dict) -> None:
        vals = {**defaults, **({"pool": pool_prefix} if pool_prefix else {}), **values_from(new)}
        if not multi:
            vals[fk] = ids[0]
        if "currency_key" not in vals or fk not in vals:
            st.toast("Pick a reward" + (f" and an {label.lower()}" if multi else "") + " to add a row.",
                     icon=":material/info:")
            return
        db.insert(table, vals)

    config = {
        "Pool": cc.TextColumn("Pool", help="Optional, e.g. the in-game reward pool."),
        "Reward": cc.SelectboxColumn("Reward", options=[names[k] for k in options], required=True, width="medium"),
        "Amount": cc.NumberColumn("Amount", format="%,.2f", min_value=0),
        "Times": cc.NumberColumn("Times", format="%g", min_value=0, help="Times this line is rolled. Blank = 1."),
        "Chance %": cc.NumberColumn("Chance %", format="%.4g %%", min_value=0, max_value=100,
                                    help="Chance per draw. Blank = 100 %."),
        "Average": cc.NumberColumn("Average", format="%,.2f", help="Amount × times × chance: what the plan counts."),
    }
    if multi:
        config[label] = cc.SelectboxColumn(label, options=list(id_by_name), required=True, pinned=True)
    editor(df, key, row_keys, on_update=lambda rk, ch: db.update(table, rk, values_from(ch)), on_insert=ins,
           on_delete=lambda rk: db.delete(table, rk), column_config=config, disabled=["Average"])


def _save_tier_choice(aid: int, wk: str) -> None:
    db.update("activities", {"id": aid}, {"reward_tier": st.session_state[wk]})
    invalidate()


TierGroups = list[str] | dict[str, "TierGroups"]


def _tier_leaves(groups: TierGroups, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], list[str]]]:
    """(tab path, default rows) for every table in a possibly nested {tab: rows | {tab: ...}} spec."""
    if isinstance(groups, dict):
        return [leaf for name, sub in groups.items() for leaf in _tier_leaves(sub, (*path, name))]
    return [(path, groups)]


def _tier_rows_key(key: str, path: tuple[str, ...]) -> str:
    return f"tier_rows__{key}__" + "__".join(path)


def _tier_pool(path: tuple[str, ...], row: str) -> str:
    return calc.TIER_PREFIX + " · ".join((*path, row))


def _tier_groups_key(key: str) -> str:
    return f"tier_groups__{key}"


def tier_groups(key: str, default: TierGroups, settings: dict | None = None) -> TierGroups:
    """The page's current tab structure: the saved one (after adds / renames / removals) or the default."""
    return (settings if settings is not None else data().settings).get(_tier_groups_key(key), default)


def _tier_node(root: TierGroups, path: tuple[str, ...]) -> TierGroups:
    for name in path:
        root = root[name]
    return root


def _pick_key(key: str, parent: tuple[str, ...]) -> str:
    return f"{key}__pick__" + "__".join(parent)


def _tier_add(key: str, default: TierGroups, parent: tuple[str, ...], wk: str, what: str) -> None:
    name = (st.session_state.get(wk) or "").strip()
    root = copy.deepcopy(tier_groups(key, default, db.get_settings()))
    node = _tier_node(root, parent)
    if not name or name in node:
        st.toast(f"Type a new {what} name that isn't used yet.", icon=":material/info:")
        return
    node[name] = copy.deepcopy(next(iter(node.values()))) if node else []  # same shape as its siblings
    db.set_setting(_tier_groups_key(key), root)
    st.session_state[_pick_key(key, parent)] = name
    st.session_state[wk] = ""
    invalidate()


def _tier_move_rows(aid: int, key: str, old: tuple[str, ...], new: tuple[str, ...] | None, subtree: TierGroups) -> None:
    """Rename (new) or delete (new=None) everything stored under a tab path: reward rows, row lists, plan tier."""
    old_prefix = calc.TIER_PREFIX + " · ".join(old) + " · "
    if new is None:
        db.execute("DELETE FROM activity_rewards WHERE activity_id = ? AND substr(pool, 1, ?) = ?",
                   [aid, len(old_prefix), old_prefix])
    else:
        new_prefix = calc.TIER_PREFIX + " · ".join(new) + " · "
        db.execute("UPDATE activity_rewards SET pool = ? || substr(pool, ?) WHERE activity_id = ? AND substr(pool, 1, ?) = ?",
                   [new_prefix, len(old_prefix) + 1, aid, len(old_prefix), old_prefix])
    settings = db.get_settings()
    for leaf, _ in _tier_leaves(subtree, old):
        rows_key = _tier_rows_key(key, leaf)
        if rows_key in settings and new is not None:
            db.set_setting(_tier_rows_key(key, (*new, *leaf[len(old):])), settings[rows_key])
        db.execute("DELETE FROM settings WHERE key = ?", [rows_key])
    tier = db.read_table("activities", where="id = ?", params=[aid]).iloc[0]["reward_tier"]
    old_label = " · ".join(old) + " · "
    if isinstance(tier, str) and tier.startswith(old_label):
        db.update("activities", {"id": aid},
                  {"reward_tier": None if new is None else " · ".join(new) + " · " + tier[len(old_label):]})


def _tier_rename(key: str, default: TierGroups, aid: int, path: tuple[str, ...], wk: str, what: str) -> None:
    name = (st.session_state.get(wk) or "").strip()
    root = copy.deepcopy(tier_groups(key, default, db.get_settings()))
    parent = _tier_node(root, path[:-1])
    if not name or name in parent:
        st.toast(f"Type a new {what} name that isn't used yet.", icon=":material/info:")
        return
    subtree = parent[path[-1]]
    items = [(name if k == path[-1] else k, v) for k, v in parent.items()]
    parent.clear()
    parent.update(items)
    db.set_setting(_tier_groups_key(key), root)
    _tier_move_rows(aid, key, path, (*path[:-1], name), subtree)
    st.session_state[_pick_key(key, path[:-1])] = name
    invalidate()


def _tier_remove(key: str, default: TierGroups, aid: int, path: tuple[str, ...], ok_key: str) -> None:
    if not st.session_state.get(ok_key):
        st.toast("Tick the confirmation first.", icon=":material/info:")
        return
    root = copy.deepcopy(tier_groups(key, default, db.get_settings()))
    parent = _tier_node(root, path[:-1])
    if len(parent) <= 1:
        st.toast("Can't remove the last one.", icon=":material/info:")
        return
    subtree = parent.pop(path[-1])
    db.set_setting(_tier_groups_key(key), root)
    _tier_move_rows(aid, key, path, None, subtree)
    st.session_state.pop(_pick_key(key, path[:-1]), None)
    invalidate()


def _auto_tier(aid: int, key: str, groups: TierGroups, columns: list[tuple[str, str, str]]) -> None:
    """Plan tier = the last row (in page order) with a value in a counted column."""
    settings = db.get_settings()
    groups = tier_groups(key, groups, settings)
    raw = db.read_table("activity_rewards", where="activity_id = ?", params=[aid])
    filled = set(raw.loc[raw["amount"].notna(), "pool"]) if not raw.empty else set()
    best = None
    for path, default in _tier_leaves(groups):
        for row in settings.get(_tier_rows_key(key, path), default):
            if any(_tier_pool(path, row) + sfx in filled for _, _, sfx in columns if not sfx):
                best = " · ".join((*path, row))
    db.update("activities", {"id": aid}, {"reward_tier": best})


def tier_completion(category: str, key: str, groups: TierGroups, columns: list[tuple[str, str, str]]
                    ) -> dict[tuple[str, ...], bool]:
    """Per table (tab path): True when every row has a value in every column."""
    d = data()
    acts = d.activities[d.activities["category"] == category]
    if acts.empty:
        return {}
    raw = db.read_table("activity_rewards", where="activity_id = ?", params=[int(acts.iloc[0]["id"])])
    have = set(zip(raw["pool"], raw["currency_key"])) if not raw.empty else set()
    out = {}
    for path, default in _tier_leaves(tier_groups(key, groups, d.settings)):
        rows = d.settings.get(_tier_rows_key(key, path), default)
        out[path] = bool(rows) and all((_tier_pool(path, r) + sfx, ck) in have for r in rows for _, ck, sfx in columns)
    return out


def tier_reward_editor(category: str, tiers: TierGroups, columns: list[tuple[str, str, str]], key: str,
                       tier_label: str = "Tier", help_text: str = "", auto_tier: bool = False,
                       picker: bool = True, group_names: tuple[str, ...] = ("Group", "Tier"),
                       group_icons: tuple[str, ...] = ("layers", "stairs")) -> None:
    """Rewards that depend on a tier (score bracket, boss level): one row per tier, one column per reward.

    tiers: a list of rows, or {tab: rows | {tab: ...}} for (nested) tabs, e.g. Nightmare layer > tier > level.
    Rows can be added, renamed and removed (kept per table in settings). columns: (label, currency key, pool
    suffix); a suffix such as "|first" stores one-time values the plan never counts. The plan counts one row: the
    one picked in the selector, or with auto_tier the last row that has a counted value. picker=False: reference
    values only (no selector; the plan counts none of these rows). group_names / group_icons name the tab levels
    (e.g. Layer, Tier); each level has an Edit menu to add, rename or remove its tabs.
    """
    d = data()
    acts = d.activities[d.activities["category"] == category]
    if acts.empty:
        return
    a = acts.iloc[0]
    aid = int(a["id"])
    default_tiers = tiers
    tiers = tier_groups(key, default_tiers, d.settings)
    leaves = _tier_leaves(tiers)
    rows_of = {path: list(d.settings.get(_tier_rows_key(key, path), default)) for path, default in leaves}
    raw = db.read_table("activity_rewards", where="activity_id = ?", params=[aid])
    cell = {(r["pool"], r["currency_key"]): r["amount"] for _, r in raw.iterrows()}

    def after_change() -> None:
        if auto_tier:
            _auto_tier(aid, key, tiers, columns)

    def set_cell(pool: str, ck: str, value) -> None:
        db.execute("DELETE FROM activity_rewards WHERE activity_id = ? AND pool = ? AND currency_key = ?",
                   [aid, pool, ck])
        if value not in (None, ""):
            db.insert("activity_rewards", {"activity_id": aid, "pool": pool, "currency_key": ck,
                                           "amount": float(value), "draws": 1.0, "chance": 100.0})

    def table(path: tuple[str, ...], tab_key: str) -> None:
        rows = rows_of[path]
        df = pd.DataFrame({tier_label: pd.Series(rows, dtype="object")})
        for label, ck, sfx in columns:
            df[label] = pd.Series([cell.get((_tier_pool(path, r) + sfx, ck)) for r in rows], dtype=float)

        def save_rows(new_rows: list[str]) -> None:
            db.set_setting(_tier_rows_key(key, path), new_rows)

        def upd(rk: dict, changes: dict) -> None:
            row = rk["row"]
            renamed = changes.get(tier_label)
            if renamed and renamed != row and renamed not in rows:
                for _, ck, sfx in columns:
                    db.execute("UPDATE activity_rewards SET pool = ? WHERE activity_id = ? AND pool = ?",
                               [_tier_pool(path, renamed) + sfx, aid, _tier_pool(path, row) + sfx])
                save_rows([renamed if r == row else r for r in rows])
                row = renamed
            for label, ck, sfx in columns:
                if label in changes:
                    set_cell(_tier_pool(path, row) + sfx, ck, changes[label])
            after_change()

        def ins(new: dict) -> None:
            row = (new.get(tier_label) or "").strip() or f"Row {len(rows) + 1}"
            if row not in rows:
                rows.append(row)
                save_rows(rows)
            for label, ck, sfx in columns:
                if new.get(label) is not None:
                    set_cell(_tier_pool(path, row) + sfx, ck, new[label])
            after_change()

        def delete(rk: dict) -> None:
            for _, ck, sfx in columns:
                set_cell(_tier_pool(path, rk["row"]) + sfx, ck, None)
            rows.remove(rk["row"])
            save_rows(rows)
            after_change()

        editor(df, tab_key, [{"row": r} for r in rows], on_update=upd, on_insert=ins, on_delete=delete,
               column_config={tier_label: cc.TextColumn(tier_label, pinned=True, required=True),
                              **{c[0]: cc.NumberColumn(c[0], format="%,.0f", min_value=0) for c in columns}})

    def filled(path: tuple[str, ...]) -> str:
        rows = rows_of.get(path, [])
        parts = []
        for label, ck, sfx in columns:
            n = sum(cell.get((_tier_pool(path, r) + sfx, ck)) is not None for r in rows)
            parts.append(f"{label} **{n}/{len(rows)}**")
        return "Filled: " + " · ".join(parts)

    done = tier_completion(category, key, tiers, columns)

    def complete(prefix: tuple[str, ...]) -> bool:
        return all(ok for p, ok in done.items() if p[:len(prefix)] == prefix)

    def tabs(groups: TierGroups, path: tuple[str, ...] = ()) -> None:
        """Top level = buttons, second level = pills (only the chosen table is shown), deeper = tabs.
        Each button carries a green tick when all its tables are filled, an exclamation mark otherwise."""
        if not isinstance(groups, dict):
            if path:
                st.caption(filled(path))
            table(path, f"{key}__" + "__".join(path))
            return
        names = list(groups)
        depth = len(path)
        if depth >= 2:
            for tab, name in zip(st.tabs([f"{progress.mark(complete((*path, n)))} {n}" for n in names]), names):
                with tab:
                    tabs(groups[name], (*path, name))
            return
        what = group_names[min(depth, len(group_names) - 1)]
        icon = f":material/{group_icons[min(depth, len(group_icons) - 1)]}:"
        pk = _pick_key(key, path)
        if st.session_state.get(pk) not in names:
            st.session_state[pk] = names[0]  # selection lives in session state (set here or by the Edit menu)
        with st.container(horizontal=True, vertical_alignment="bottom"):
            if depth == 0:  # top level: buttons
                choice = st.segmented_control(
                    what, names, required=True, key=pk, label_visibility="collapsed", width="stretch",
                    format_func=lambda n: f"{progress.mark(complete((*path, n)))} {icon} {n}") or names[0]
            else:  # second level: pills
                choice = st.pills(
                    what, names, required=True, key=pk, label_visibility="collapsed",
                    format_func=lambda n: f"{progress.mark(complete((*path, n)))} {icon} {n}") or names[0]
            group_menu(path, choice, what)
        if depth == 0:
            with st.container(border=True):
                st.markdown(f"##### {icon} {choice}")
                tabs(groups[choice], (*path, choice))
        else:
            tabs(groups[choice], (*path, choice))

    def group_menu(parent: tuple[str, ...], choice: str, what: str) -> None:
        """Add / rename / remove tabs at this level."""
        base = f"{key}__edit__" + "__".join(parent)
        with st.popover(f"Edit {what.lower()}s", icon=":material/edit:", width="content"):
            st.text_input(f"New {what.lower()} name", key=f"{base}__new", placeholder=f"e.g. {what} {len(_tier_node(tiers, parent)) + 1}")
            st.button(f"Add {what.lower()}", icon=":material/add:", key=f"{base}__add", on_click=_tier_add,
                      args=(key, default_tiers, parent, f"{base}__new", what.lower()))
            st.text_input(f"Rename {choice}", value=choice, key=f"{base}__ren__{choice}")
            st.button("Rename", icon=":material/edit_note:", key=f"{base}__rename", on_click=_tier_rename,
                      args=(key, default_tiers, aid, (*parent, choice), f"{base}__ren__{choice}", what.lower()))
            st.checkbox(f"Yes, remove {choice} and all its values", key=f"{base}__ok__{choice}")
            st.button(f"Remove {choice}", icon=":material/delete:", key=f"{base}__remove", on_click=_tier_remove,
                      args=(key, default_tiers, aid, (*parent, choice), f"{base}__ok__{choice}"))

    with st.container(border=True):
        st.subheader("Rewards per claim")
        current = a.get("reward_tier")
        if picker and not auto_tier:
            choices = [" · ".join((*p, r)) for p, rs in rows_of.items() for r in rs]
            wk = f"{key}__tier"
            st.selectbox(f"{tier_label} used in the plan", choices,
                         index=choices.index(current) if current in choices else None,
                         placeholder=f"Pick the {tier_label.lower()} you usually reach", key=wk,
                         on_change=_save_tier_choice, args=(aid, wk))
            flat = raw[raw["pool"].fillna("") == ""] if not raw.empty else raw
            if current not in choices and not flat.empty:
                names = dict(zip(d.currencies["key"], d.currencies["name"]))
                st.caption("Until you pick one, the plan uses the earlier flat values: " + ", ".join(
                    f"{names.get(r['currency_key'], r['currency_key'])} {r['amount']:,.0f}"
                    for _, r in flat.iterrows()) + ".")
        if help_text:
            st.caption(help_text)
        if auto_tier:
            st.caption(f"Plan uses: **{current}**." if current else "Plan uses: nothing yet (no repeat value filled).")
        tabs(tiers)


def wide_reward_editor(activity_ids: list[int], key: str, currency_keys: list[str] | None = None,
                       row_names: pd.Series | None = None, label: str = "Activity") -> None:
    """Rewards grid like the Nightmare table: one row per activity, one column per reward (amount per claim).

    Columns = the page's reward types + any reward these rows already give + ones added with the picker.
    Cells hold plain per-claim amounts (one draw, 100 %); clearing a cell removes that reward.
    """
    d = data()
    names = dict(zip(d.currencies["key"], d.currencies["name"]))
    row_names = d.activities.set_index("id")["name"] if row_names is None else row_names
    raw = db.read_table("activity_rewards")
    raw = raw[raw["activity_id"].isin(activity_ids) & (raw["pool"].fillna("") == "")] if not raw.empty else raw
    used = list(dict.fromkeys(raw.sort_values("id")["currency_key"])) if not raw.empty else []
    base = list(dict.fromkeys([k for k in [*(currency_keys or []), *used] if k in names]))
    extra = st.multiselect("Add reward columns", [k for k in names if k not in base], format_func=names.get,
                           key=f"{key}_extra_cols", placeholder="Other rewards…")
    keys = [*base, *extra]
    value = {}
    if not raw.empty:
        raw = raw.assign(v=raw["amount"] * raw["draws"].fillna(1.0) * raw["chance"].fillna(100.0) / 100.0)
        value = raw.groupby(["activity_id", "currency_key"])["v"].sum().to_dict()
    df = pd.DataFrame({label: pd.Series([row_names.get(i, str(i)) for i in activity_ids], dtype="object")})
    for k in keys:
        df[names[k]] = pd.Series([value.get((i, k)) for i in activity_ids], dtype=float)
    key_by_name = {names[k]: k for k in keys}

    def upd(rk: dict, changes: dict) -> None:
        for col, val in changes.items():
            ck = key_by_name.get(col)
            if ck is None:
                continue
            db.execute("DELETE FROM activity_rewards WHERE activity_id = ? AND currency_key = ? AND "
                       "COALESCE(pool, '') = ''", [rk["id"], ck])
            if val not in (None, ""):
                db.insert("activity_rewards", {"activity_id": rk["id"], "currency_key": ck, "pool": "",
                                               "amount": float(val), "draws": 1.0, "chance": 100.0})

    editor(df, key, [{"id": int(i)} for i in activity_ids], on_update=upd, disabled=[label],
           column_config={label: cc.TextColumn(label, pinned=True),
                          **{names[k]: cc.NumberColumn(names[k], format="%,.2f", min_value=0) for k in keys}})


def _pools_key(key: str) -> str:
    return f"reward_pools__{key}"


def _pool_add(key: str, wk: str) -> None:
    name = (st.session_state.get(wk) or "").strip()
    pools = list(db.get_settings().get(_pools_key(key), []))
    if not name or name in pools:
        st.toast("Type a new pool name that isn't used yet.", icon=":material/info:")
        return
    db.set_setting(_pools_key(key), [*pools, name])
    st.session_state[wk] = ""
    invalidate()


def _pool_remove(key: str, activity_ids: list[int], prefix: str, pool: str, ok_key: str) -> None:
    if not st.session_state.get(ok_key):
        st.toast("Tick the confirmation first.", icon=":material/info:")
        return
    db.execute(f"DELETE FROM activity_rewards WHERE pool = ? AND activity_id IN ({','.join('?' * len(activity_ids))})",
               [prefix + pool, *activity_ids])
    db.set_setting(_pools_key(key), [p for p in db.get_settings().get(_pools_key(key), []) if p != pool])
    invalidate()


def pooled_reward_editor(activity_ids: list[int], key: str, prefix: str, currency_keys: list[str] | None = None) -> None:
    """One tab per reward pool (pool names stored as "<prefix><pool>"), each with its own rewards table."""
    raw = db.read_table("activity_rewards")
    raw = raw[raw["activity_id"].isin(activity_ids) & raw["pool"].fillna("").str.startswith(prefix)] if not raw.empty else raw
    seen = list(dict.fromkeys(raw.sort_values("id")["pool"].str[len(prefix):])) if not raw.empty else []
    pools = list(dict.fromkeys([*seen, *data().settings.get(_pools_key(key), [])]))
    with st.popover("Edit pools", icon=":material/edit:"):
        st.text_input("New pool name", key=f"{key}__new", placeholder=f"e.g. Reward Pool {len(pools) + 1}")
        st.button("Add pool", icon=":material/add:", key=f"{key}__add", on_click=_pool_add, args=(key, f"{key}__new"))
        if pools:
            gone = st.selectbox("Pool to remove", pools, key=f"{key}__rm")
            st.checkbox(f"Yes, remove {gone} and its rewards", key=f"{key}__ok")
            st.button("Remove pool", icon=":material/delete:", key=f"{key}__remove", on_click=_pool_remove,
                      args=(key, activity_ids, prefix, gone, f"{key}__ok"))
    if not pools:
        st.caption("No pools yet. Add one with Edit pools.")
        return
    for tab, pool in zip(st.tabs(pools), pools):
        with tab:
            reward_editor(activity_ids, key=f"{key}__{pool}", currency_keys=currency_keys, pool_prefix=prefix + pool,
                          show_pool=False)


def character_activity_editor(char: pd.Series, categories: list[str] | None, key: str, only_in_loop: bool = False) -> None:
    """Per-character toggles and planned runs for recurring activities."""
    d = data()
    acts = calc.eligible_activities(d)
    if categories:
        acts = acts[acts["category"].isin(categories)]
    if only_in_loop:
        acts = acts[[calc.is_enabled_for(a, char, {}) for _, a in acts.iterrows()]]
    p = plan()
    rows = []
    for _, a in acts.iterrows():
        stg = calc._setting_for(d, char["id"], a["id"])
        pr = p[(p["character_id"] == char["id"]) & (p["activity_id"] == a["id"])] if not p.empty else p
        mx = calc.weekly_max_attempts(a, bool(char["membership"]), d.settings)
        gate = calc._num(a.get("entry_item_level"))
        rows.append({
            "Activity": a["name"], "Category": a["category"], "Scope": a["scope"],
            "Enabled": calc.is_enabled_for(a, char, stg),
            "Planned runs": None if pd.isna(stg.get("planned_runs", None)) else stg.get("planned_runs"),
            "Use extra claim": True if pd.isna(stg.get("use_extra_claim", None)) else bool(stg["use_extra_claim"]),
            "Max / week": mx,
            "Runs in plan": float(pr["attempts"].sum()) if not pr.empty else 0.0,
            "Hours / week": float(pr["hours"].sum()) if not pr.empty else 0.0,
            "Odyle / week": float(pr["odyle"].sum()) if not pr.empty else 0.0,
            "Allocation": ", ".join(pr["allocation"].unique()) if not pr.empty else ("GS gate" if calc._num(char["item_level"]) < gate else ""),
            "Status": calc.status_label(a["ruleset"], a["source_status"]),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No eligible activities.", icon=":material/info:")
        return

    col_map = {"Planned runs": "planned_runs", "Use extra claim": "use_extra_claim"}

    def upd(rk: dict, changes: dict) -> None:
        vals = {col_map[k]: v for k, v in changes.items() if k in col_map}
        db.upsert("character_activity", rk, vals)

    def remove(rk: dict) -> None:
        # Loop membership follows the scope, so removing a line skips it for this character (0 planned runs).
        db.upsert("character_activity", rk, {"planned_runs": 0})

    editor(
        df, key, [{"character_id": int(char["id"]), "activity_id": int(i)} for i in acts["id"]], on_update=upd,
        on_delete=remove,
        disabled=["Activity", "Category", "Scope", "Enabled", "Max / week", "Runs in plan", "Hours / week", "Odyle / week", "Allocation", "Status"],
        column_config={
            "Activity": cc.TextColumn(pinned=True),
            "Enabled": cc.CheckboxColumn("In loop", help="per_character: main and alts. per_server / unknown: main only."),
            "Planned runs": cc.NumberColumn(help="Blank = max allowed, or auto Odyle allocation.", min_value=0),
            "Max / week": cc.NumberColumn(format="%.1f", help="Blank = Odyle-limited"),
            "Runs in plan": cc.NumberColumn(format="%.1f"),
            "Hours / week": cc.NumberColumn(format="%.2f"),
            "Odyle / week": cc.NumberColumn(format="%,.0f"),
            "Status": cc.SelectboxColumn(options=STATUS_OPTIONS),
        },
    )


def pick_character(chars: pd.DataFrame, label: str, key: str) -> pd.Series:
    """Segmented picker over characters; returns the selected row."""
    ids = [int(i) for i in chars["id"]]
    names = dict(zip(ids, chars["name"]))
    if len(ids) == 1:
        return chars.iloc[0]
    sel = st.segmented_control(label, ids, default=ids[0], format_func=names.get, key=key) or ids[0]
    return chars[chars["id"] == sel].iloc[0]


# ------------------------------------------------------------------ summaries & charts

def fmt(v: float, digits: int = 0) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{digits}f}"


def kpis(p: pd.DataFrame) -> None:
    get = lambda c: float(p[c].sum()) if (not p.empty and c in p) else 0.0
    with st.container(horizontal=True):
        st.metric("Hours / week", fmt(get("hours"), 1), border=True)
        st.metric("Unbound Kinah / week", fmt(get("kinah_unbound")), border=True)
        st.metric("Bound Kinah / week", fmt(get("kinah_bound")), border=True)
        st.metric("AP / week", fmt(get("abyss_points")), border=True)
        st.metric("Odyle spent / week", fmt(get("odyle")), border=True)
        hours = get("hours")
        st.metric("Kinah value / hour", fmt(get("kinah_value") / hours) if hours else "—", border=True)


def plan_table(p: pd.DataFrame, extra: list[str] | None = None, key: str | None = None) -> None:
    if p.empty:
        st.info("Nothing planned for this selection.", icon=":material/info:")
        return
    cols = ["character", "activity", "category", "scope", "allocation", "attempts", "claims", "hours",
            "odyle", "kinah_unbound", "kinah_bound", "abyss_points", *(extra or []), "kinah_value", "value_score", "status"]
    cols = [c for c in dict.fromkeys(cols) if c in p.columns]
    show(
        p[cols], hide_index=True, key=key,
        column_config={
            "character": cc.TextColumn("Character", pinned=True),
            "activity": cc.TextColumn("Activity", pinned=True),
            "attempts": cc.NumberColumn("Runs", format="%.1f"),
            "claims": cc.NumberColumn("Claims", format="%.1f"),
            "hours": cc.NumberColumn("Hours", format="%.2f"),
            "odyle": cc.NumberColumn("Odyle", format="%,.0f"),
            "kinah_unbound": cc.NumberColumn("Unbound Kinah", format="%,.0f"),
            "kinah_bound": cc.NumberColumn("Bound Kinah", format="%,.0f"),
            "abyss_points": cc.NumberColumn("AP", format="%,.0f"),
            "kinah_value": cc.NumberColumn("Kinah value", format="%,.0f"),
            "value_score": cc.NumberColumn("Value score", format="%,.1f"),
            **{c: cc.NumberColumn(data().currencies.set_index("key")["name"].get(c, c), format="%,.1f") for c in (extra or [])},
        },
    )


GROUP_LABELS = {
    "character": "Character", "category": "Content type", "activity": "Activity", "role": "Main / Alt",
    "status": "Data status", "allocation": "Allocation", "scope": "Scope", "server": "Server", "source": "Source",
    "type": "Type", "cap": "Cap", "profile": "Profile", "mode": "Mode", "dungeon": "Dungeon", "metric": "Metric",
    "kind": "Kind", "content": "Content", "block_type": "Block",
}
LABEL_MODES = ["None", "Values", "Names"]


def _chart_key(hint: str) -> str:
    """Stable per-run key for chart option widgets (same call order each rerun)."""
    run = st.session_state.get("_run_id")
    if st.session_state.get("_chart_run") != run:
        st.session_state["_chart_run"], st.session_state["_chart_n"] = run, 0
    st.session_state["_chart_n"] += 1
    return f"chartopt_{st.session_state['_chart_n']}_{hint}"


def chart_options(key: str, color_choices: list[str | None], default_color: str | None,
                  label_default: str = "None") -> tuple[str | None, str]:
    """Small popover on every chart: what the colors/legend group by, and which labels are drawn."""
    color_choices = list(dict.fromkeys([default_color, *color_choices]))
    with st.container(horizontal=True, horizontal_alignment="right"):
        with st.popover("Chart options", icon=":material/tune:"):
            color = st.selectbox(
                "Color / legend by", color_choices, key=f"{key}_color",
                format_func=lambda c: "None (single color)" if c is None else GROUP_LABELS.get(c, str(c)),
            )
            label = st.segmented_control("Labels", LABEL_MODES, default=label_default, key=f"{key}_labels") or "None"
    return color, label


def _groupable(df: pd.DataFrame, exclude: set[str]) -> list[str]:
    out = []
    for c in df.columns:
        if c in exclude or c.endswith("_id") or c == "id":
            continue
        if (df[c].dtype == object or str(df[c].dtype).startswith(("str", "string", "category", "bool"))) \
                and 1 <= df[c].nunique() <= 40:
            out.append(c)
    return out


def bar(df: pd.DataFrame, x: str, y: str, color: str | None = None, horizontal: bool = False,
        title: str | None = None, fmt_: str = ",.1f", height: int = 300, sort_by_value: bool = True,
        key: str | None = None) -> None:
    """Bar chart with a 'Chart options' popover (color/legend grouping + labels).

    Pass raw rows (e.g. plan rows) to offer every grouping: values are summed per x / color group.
    """
    if df.empty or y not in df or df[y].abs().sum() == 0:
        st.caption("No data.")
        return
    key = key or _chart_key(f"{x}_{y}")
    color, labels = chart_options(key, [None, *_groupable(df, {x, y})], color)
    keys = [x] + ([color] if color and color != x else [])
    agg = df.groupby(keys, as_index=False, sort=False)[y].sum()
    val_title = title or y
    enc_val = (alt.X(f"{y}:Q", title=val_title, axis=alt.Axis(format=fmt_)) if horizontal
               else alt.Y(f"{y}:Q", title=val_title, axis=alt.Axis(format=fmt_)))
    order = list(dict.fromkeys(df[x]))
    if sort_by_value:
        order = list(agg.groupby(x, sort=False)[y].sum().sort_values(ascending=False).index)
    enc_cat = alt.Y(f"{x}:N", sort=order, title=None) if horizontal else alt.X(f"{x}:N", sort=order, title=None)
    tooltip = [alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=fmt_)]
    has_color = color and color != x
    if has_color:
        tooltip.insert(1, alt.Tooltip(f"{color}:N"))
    bars = alt.Chart(agg).mark_bar().encode(
        x=enc_val if horizontal else enc_cat, y=enc_cat if horizontal else enc_val,
        color=alt.Color(f"{color}:N", title=None) if has_color else alt.value("#4C78A8"),
        order=alt.Order(f"{color}:N") if has_color else alt.Undefined, tooltip=tooltip,
    )
    chart = bars
    if labels != "None":
        # Label at the middle of each (stacked) segment.
        lab = agg.copy()
        if has_color:
            lab = lab.sort_values([x, color])
            lab["_end"] = lab.groupby(x)[y].cumsum()
        else:
            lab["_end"] = lab[y]
        lab["_mid"] = lab["_end"] - lab[y] / 2
        lab = lab[lab[y].abs() > 0]
        if labels == "Values":
            lab["_text"] = lab[y].map(lambda v: format(v, fmt_.lstrip(",")) if "%" in fmt_ else f"{v:,.1f}".rstrip("0").rstrip("."))
        else:
            lab["_text"] = lab[color].astype(str) if has_color else lab[x].astype(str)
        pos = alt.X("_mid:Q") if horizontal else alt.Y("_mid:Q")
        text = alt.Chart(lab).mark_text(fontSize=10, fontWeight="bold", color="#262730").encode(
            **({"x": pos, "y": enc_cat} if horizontal else {"x": enc_cat, "y": pos}), text="_text:N")
        chart = bars + text
    st.altair_chart(chart.properties(height=height))


ENTRY_FIELDS = {  # widget key -> activities column
    "amount": "recharge_amount", "cap": "charge_cap",
    "amount_m": "recharge_amount_membership", "cap_m": "charge_cap_membership",
}
PERIOD_HOURS = {"day": 24.0, "week": 168.0}


def _save_entries(aid: int, keys: dict[str, str], per_key: str) -> None:
    hours = PERIOD_HOURS[st.session_state[per_key]]
    values = {ENTRY_FIELDS[k]: st.session_state[wk] for k, wk in keys.items()}
    db.update("activities", {"id": aid}, {**values, "recharge_hours": hours, "recharge_hours_membership": hours})
    invalidate()


def _save_claims(category: str, keys: dict[str, str]) -> None:
    v = {k: st.session_state[wk] for k, wk in keys.items()}
    free = float(v["claims"] or 0)
    db.execute("UPDATE activities SET odyle_per_claim = ?, reward_claims_per_attempt = ?, membership_extra_claims = ?, "
               "scope = ? WHERE category = ?",
               [float(v["odyle"] or 0), free, max(float(v["claims_m"] or 0) - free, 0.0), v["scope"], category])
    invalidate()


def claims_box(category: str) -> None:
    """Settings shared by every row of an Odyle-claim page (Expedition, Transcendence), laid out like entries_box:
    a no-membership row and a membership row (grayed computed value at the end), then the shared fields."""
    acts = data().activities
    acts = acts[acts["category"] == category]
    if acts.empty:
        return
    a = acts.iloc[0]
    keys = {k: f"claims__{category}__{k}" for k in ("odyle", "claims", "claims_m", "scope")}
    args = (category, keys)
    odyle = calc._num(a["odyle_per_claim"])
    claims = calc._num(a["reward_claims_per_attempt"], 1.0)
    rows = (("claims", "no membership", claims), ("claims_m", "membership", claims + calc._num(a["membership_extra_claims"])))
    with st.container(border=True):
        st.subheader("Claims & cost (Odyle)")
        for k, who, n in rows:
            with st.container(horizontal=True):
                st.number_input(f"Claims per run ({who})", value=n, min_value=0.0, step=1.0, key=keys[k],
                                on_change=_save_claims, args=args,
                                help=None if k == "claims" else "Each extra claim costs its own Odyle.")
                st.text_input(f"Odyle per run ({who})", value=f"{n * odyle:,.0f}", disabled=True,
                              key=f"claims__{category}__cost_{k}__{n * odyle}")  # text: no +/- steppers
        with st.container(horizontal=True):
            st.number_input("Odyle per claim", value=odyle, min_value=0.0, step=5.0, key=keys["odyle"],
                            on_change=_save_claims, args=args)
            st.selectbox("Scope", calc.SCOPES, index=calc.SCOPES.index(a["scope"]) if a["scope"] in calc.SCOPES else 0,
                         key=keys["scope"], on_change=_save_claims, args=args,
                         help="per_character: main and alts. per_server / unknown: main only.")
        progress.track(4, 4)


def _save_field(aid: int, col: str, wk: str) -> None:
    db.update("activities", {"id": aid}, {col: st.session_state[wk]})
    invalidate()


def entries_box(category: str, unit: str = "entries", gs: bool = False) -> None:
    """The page's parameters: recharge per day or week and cap, with and without membership (per week computed,
    grayed), plus scope, minutes per entry and optionally the required GS."""
    d = data()
    acts = d.activities[d.activities["category"] == category]
    if acts.empty:
        return
    a = acts.iloc[0]
    aid = int(a["id"])
    keys = {k: f"entries__{aid}__{k}" for k in ENTRY_FIELDS}
    per_key = f"entries__{aid}__per"
    args = (aid, keys, per_key)
    per = "week" if calc._num(a.get("recharge_hours")) >= 168 else "day"
    with st.container(border=True):
        st.subheader(f"Recharge & cap ({unit})")
        st.segmented_control("Recharge per", ["day", "week"], default=per, key=per_key, required=True,
                             on_change=_save_entries, args=args)
        for sfx, who in (("", "no membership"), ("_m", "membership")):
            amount, cap = a.get(ENTRY_FIELDS["amount" + sfx]), a.get(ENTRY_FIELDS["cap" + sfx])
            weekly = calc.weekly_max_attempts(a, bool(sfx), d.settings)
            with st.container(horizontal=True):
                st.number_input(f"Recharge rate ({who})", value=None if pd.isna(amount) else float(amount),
                                min_value=0.0, step=1.0, key=keys["amount" + sfx], on_change=_save_entries, args=args)
                st.number_input(f"Cap ({who})", value=None if pd.isna(cap) else float(cap), min_value=0.0,
                                step=1.0, key=keys["cap" + sfx], on_change=_save_entries, args=args,
                                help="Most you can store.")
                st.text_input(f"Per week ({who})", value=f"{weekly or 0:,.1f}".removesuffix(".0"), disabled=True,
                              key=f"entries__{aid}__week{sfx}__{weekly}")  # text: no +/- steppers
        progress.track(sum(pd.notna(a.get(c)) for c in ENTRY_FIELDS.values()) + pd.notna(a.get("duration_minutes")),
                       len(ENTRY_FIELDS) + 1)
        with st.container(horizontal=True):
            sk, mk, gk = (f"entries__{aid}__{c}" for c in ("scope", "minutes", "gs"))
            st.selectbox("Scope", calc.SCOPES, index=calc.SCOPES.index(a["scope"]) if a["scope"] in calc.SCOPES else 0,
                         key=sk, on_change=_save_field, args=(aid, "scope", sk),
                         help="per_character: main and alts. per_server / unknown: main only.")
            st.number_input("Minutes per entry", value=calc._num(a["duration_minutes"]), min_value=0.0, step=1.0,
                            key=mk, on_change=_save_field, args=(aid, "duration_minutes", mk))
            if gs:
                v = a.get("entry_item_level")
                st.number_input("Required GS", value=None if pd.isna(v) else float(v), min_value=0.0, step=10.0,
                                key=gk, on_change=_save_field, args=(aid, "entry_item_level", gk))


def category_page(categories: list[str], key: str, columns: list[str] | None = None,
                  reward_keys: list[str] | None = None, cadences: list[str] | None = None,
                  show_rewards: bool = True, show_params: bool = True, wide_rewards: bool = False,
                  shared_from_category: bool = False) -> None:
    """Standard content page: parameters table + rewards table (like Expedition).

    show_params: False on pages whose few parameters live in `entries_box` instead.

    cadences: only show activities with these cadences (e.g. the daily or weekly part of a category).
    show_rewards: False for content whose rewards can't be known in advance.
    """
    d = data()
    if show_params:
        with st.container(border=True):
            st.subheader("Parameters")
            st.caption("Every value is editable. Changes save immediately and recalculate the plan.")
            activity_editor(categories, key=f"{key}_acts", columns=columns, cadences=cadences,
                            shared_from_category=shared_from_category)
    if not show_rewards:
        return
    with st.container(border=True):
        st.subheader("Rewards per claim")
        acts = d.activities[d.activities["category"].isin(categories)]
        if cadences:
            acts = acts[acts["cadence"].isin(cadences)]
        ids = acts["id"].astype(int).tolist()
        if ids and wide_rewards:
            wide_reward_editor(ids, key=f"{key}_rewards", currency_keys=reward_keys)
        elif ids:
            reward_editor(ids, key=f"{key}_rewards", currency_keys=reward_keys)
