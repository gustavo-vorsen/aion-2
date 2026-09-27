"""Shared Streamlit widgets: DB-backed editors, settings inputs, status badges, charts."""
from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any, Callable

import altair as alt
import pandas as pd
import streamlit as st

from aion import calc, db, seed

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


def editor(df: pd.DataFrame, key: str, row_keys: list[dict], on_update: Callable,
           on_insert: Callable | None = None, on_delete: Callable | None = None, **kw) -> pd.DataFrame:
    """st.data_editor that writes every change straight to SQLite."""
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


def activity_columns() -> dict:
    return {
        "name": cc.TextColumn("Activity", pinned=True, width="medium"),
        "category": cc.TextColumn("Category"),
        "enabled": cc.CheckboxColumn("On"),
        "main_default": cc.CheckboxColumn("Main"),
        "alt_default": cc.CheckboxColumn("Alt"),
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
    "name", "enabled", "main_default", "alt_default", "scope", "cadence", "attempts_per_reset",
    "membership_bonus_attempts", "duration_minutes", "ruleset", "source_status", "notes",
]


def activity_editor(categories: list[str], key: str, columns: list[str] | None = None,
                    new_category: str | None = None) -> None:
    acts = data().activities
    df = acts[acts["category"].isin(categories)]
    cols = ["id", *(columns or BASE_ACTIVITY_COLS)]
    if len(categories) > 1 and "category" not in cols:
        cols.insert(2, "category")
    table_editor(
        "activities", df[cols], key=key,
        defaults={"category": new_category or categories[0], "sort_order": int(acts["sort_order"].max() or 0) + 1},
        column_config=activity_columns(),
    )


def reward_editor(activity_ids: list[int], key: str, currency_keys: list[str] | None = None, *,
                  table: str = "activity_rewards", fk: str = "activity_id",
                  row_names: pd.Series | None = None, rewards: pd.DataFrame | None = None,
                  label: str = "Activity") -> None:
    """Rewards table: rows = activities (or progression items), columns = only this content's reward types.

    Columns = the page's reward types + any currency these rows already give;
    other currencies can be added with the picker.
    """
    d = data()
    rewards = d.rewards if rewards is None else rewards
    row_names = d.activities.set_index("id")["name"] if row_names is None else row_names
    used = rewards.reindex(index=activity_ids).fillna(0.0)
    used = [k for k in used.columns if (used[k] != 0).any()]
    base = list(dict.fromkeys([*(currency_keys or []), *used]))
    all_names = dict(zip(d.currencies["key"], d.currencies["name"]))
    extra = st.multiselect(
        "Add reward columns", [k for k in d.currencies["key"] if k not in base], format_func=all_names.get,
        key=f"{key}_extra_cols", placeholder="Other currencies…",
    )
    keys = [k for k in d.currencies["key"] if k in set(base) | set(extra)]  # keep registry order
    names = {k: all_names[k] for k in keys}
    wide = rewards.reindex(index=activity_ids, columns=keys).fillna(0.0)
    wide.columns = [names[k] for k in wide.columns]
    wide.insert(0, label, row_names.reindex(activity_ids).values)
    key_by_name = {v: k for k, v in names.items()}

    def upd(rk: dict, changes: dict) -> None:
        for col, val in changes.items():
            ck = key_by_name.get(col)
            if ck is None:
                continue
            if val in (None, 0, 0.0):
                db.delete(table, {fk: rk["id"], "currency_key": ck})
            else:
                db.upsert(table, {fk: rk["id"], "currency_key": ck}, {"amount": float(val)})

    config = {n: cc.NumberColumn(n, format="%,.2f", min_value=0) for n in names.values()}
    config[label] = cc.TextColumn(label, disabled=True, pinned=True)
    editor(wide, key, [{"id": int(i)} for i in activity_ids], on_update=upd, column_config=config, disabled=[label])


def character_activity_editor(char: pd.Series, categories: list[str] | None, key: str, only_in_loop: bool = False) -> None:
    """Per-character toggles and planned runs for recurring activities."""
    d = data()
    acts = calc.eligible_activities(d)
    if categories:
        acts = acts[acts["category"].isin(categories)]
    if only_in_loop:
        acts = acts[acts["main_default" if char["is_main"] else "alt_default"].astype(bool)]
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

    editor(
        df, key, [{"character_id": int(char["id"]), "activity_id": int(i)} for i in acts["id"]], on_update=upd,
        disabled=["Activity", "Category", "Scope", "Enabled", "Max / week", "Runs in plan", "Hours / week", "Odyle / week", "Allocation", "Status"],
        column_config={
            "Activity": cc.TextColumn(pinned=True),
            "Enabled": cc.CheckboxColumn("In loop", help="Set by the Main / Alt marks in the content tabs."),
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


def category_page(categories: list[str], key: str, columns: list[str] | None = None,
                  reward_keys: list[str] | None = None) -> None:
    """Standard content page: parameters table + rewards table (like Expedition)."""
    d = data()
    with st.container(border=True):
        st.subheader("Parameters")
        st.caption("Every value is editable. Changes save immediately and recalculate the plan.")
        activity_editor(categories, key=f"{key}_acts", columns=columns)
    with st.container(border=True):
        st.subheader("Rewards per claim")
        ids = d.activities.loc[d.activities["category"].isin(categories), "id"].astype(int).tolist()
        if ids:
            reward_editor(ids, key=f"{key}_rewards", currency_keys=reward_keys)
