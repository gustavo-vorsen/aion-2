"""Draggable session grid, split/merge dialogs and per-session charts."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from aion import db, sessions

GRAY = {"backgroundColor": "rgba(128, 128, 128, 0.12)", "color": "#8b8d98"}
LABEL_OPTIONS = {"None": None, "Content": "content", "Character": "character", "Hours": "hours_label"}


def _bump(key: str) -> None:
    st.session_state[f"_ver_{key}"] = st.session_state.get(f"_ver_{key}", 0) + 1


def _apply(items: pd.DataFrame, result: pd.DataFrame, order: list[str]) -> bool:
    """Persist drag-and-drop order and edited cells. Returns True if anything changed."""
    old = list(items["uid"])
    current = items.set_index("uid")
    changed = False
    if order and sorted(order) == sorted(old) and order != old:
        new_session = dict(zip(items["uid"], items["session"]))
        # The dragged row is the one whose removal leaves both orders identical.
        moved = next((u for u in order if [x for x in order if x != u] == [x for x in old if x != u]), None)
        if moved is not None:
            pos = order.index(moved)
            neighbour = order[pos - 1] if pos > 0 else (order[1] if len(order) > 1 else None)
            if neighbour is not None:
                new_session[moved] = new_session[neighbour]  # dropped among another session's rows
        for i, uid in enumerate(order, start=1):
            sessions.save_item(uid, {"schedule_order": i, "session": int(new_session[uid])})
        changed = True
    for _, r in result.iterrows():
        uid = r.get("uid")
        if uid not in current.index:
            continue
        vals = {}
        sess = pd.to_numeric(r.get("session"), errors="coerce")
        if pd.notna(sess) and int(sess) != int(current.at[uid, "session"]):
            vals["session"] = max(int(sess), 1)
        done = r.get("done")
        if done is not None and not pd.isna(done) and bool(done) != bool(current.at[uid, "done"]):
            vals["done"] = bool(done)
        runs = pd.to_numeric(r.get("runs"), errors="coerce")
        if uid.startswith("A") and pd.notna(runs) and float(runs) != float(current.at[uid, "runs"] or 0):
            vals["runs"] = max(float(runs), 0.0)
        if vals:
            sessions.save_item(uid, vals)
            changed = True
    if changed:
        with db.connect() as conn:
            sessions.ensure_sessions(conn)
    return changed


def session_grid(items: pd.DataFrame, key: str, show_runs: bool, selectable: bool, show_done: bool = True) -> list[str]:
    """Render the draggable grid; saves changes and reruns. Returns selected uids."""
    cols = ["uid", "session", "session_name", "character", "class", "role", "content", "category",
            *(["runs"] if show_runs else []), "hours", "session_hours", "critical", *(["done"] if show_done else [])]
    grid_df = items[cols].copy()
    grid_df["critical"] = grid_df["critical"].map(lambda v: None if v is None or pd.isna(v) else bool(v))
    gb = GridOptionsBuilder.from_dataframe(grid_df)
    gb.configure_default_column(editable=False, sortable=False, filter=False, resizable=True, cellStyle=GRAY,
                                suppressMovable=True, suppressHeaderMenuButton=True, suppressHeaderFilterButton=True)
    for c in grid_df.columns:
        gb.configure_column(c, filter=False, type=[])
    gb.configure_column("uid", hide=True)
    gb.configure_column("session", header_name="Session", editable=True, rowDrag=True, cellStyle=None,
                        cellDataType="number", width=115, pinned="left")
    gb.configure_column("session_name", header_name="Session name", width=140)
    gb.configure_column("character", header_name="Character", width=120)
    gb.configure_column("class", header_name="Class", width=110)
    gb.configure_column("role", header_name="Role", width=75)
    gb.configure_column("content", header_name="Content", width=230)
    gb.configure_column("category", header_name="Type", width=130)
    fmt2 = JsCode("p => p.value == null ? '' : Number(p.value).toFixed(2)")
    if show_runs:
        gb.configure_column(
            "runs", header_name="Runs", width=85, cellDataType="number", valueFormatter=fmt2,
            editable=JsCode("p => p.data.uid.startsWith('A')"),
            cellStyle=JsCode("p => p.data.uid.startsWith('A') ? null : {backgroundColor: 'rgba(128,128,128,0.12)', color: '#8b8d98'}"),
        )
    gb.configure_column("hours", header_name="Hours", width=85, valueFormatter=fmt2)
    gb.configure_column("session_hours", header_name="Session cumulative h", width=165, valueFormatter=fmt2)
    gb.configure_column("critical", header_name="Critical", cellDataType="boolean", width=90)
    if show_done:
        gb.configure_column("done", header_name="Done", editable=True, cellStyle=None, cellDataType="boolean", width=80)
    if selectable:
        gb.configure_selection("multiple", use_checkbox=False)
    gb.configure_grid_options(
        rowDragManaged=True, animateRows=True, singleClickEdit=True, stopEditingWhenCellsLoseFocus=True,
        getRowId=JsCode("p => p.data.uid"),
        getRowStyle=JsCode(
            "p => { const n = p.api.getDisplayedRowAtIndex(p.rowIndex + 1);"
            " return n && n.data.session !== p.data.session ? {borderBottom: '2px solid rgba(128,128,128,0.6)'} : null; }"
        ),
    )
    ver = st.session_state.get(f"_ver_{key}", 0)
    resp = AgGrid(
        grid_df, gridOptions=gb.build(), allow_unsafe_jscode=True, theme="streamlit",
        update_on=["rowDragEnd", "cellValueChanged", *(["selectionChanged"] if selectable else [])],
        height=min(48 + 30 * max(len(grid_df), 1), 720), key=f"{key}_{ver}",
        show_toolbar=False, show_search=False, show_download_button=False,
    )
    nodes = [n for n in (resp.grid_response or {}).get("nodes", []) if not n.get("group") and n.get("data")]
    nodes.sort(key=lambda n: n.get("rowIndex", 0))
    if nodes and _apply(items, pd.DataFrame([n["data"] for n in nodes]), [n["data"]["uid"] for n in nodes]):
        _bump(key)
        st.rerun()
    return [n["data"]["uid"] for n in nodes if n.get("isSelected")]


# ------------------------------------------------------------------ split / merge

@st.dialog("Split a leveling block")
def _split_dialog(items: pd.DataFrame, key: str):
    lv = items[items["kind"] == "Leveling"]
    opts = {r.uid: f"S{r.session} · {r.character} · {r.content} · {r.hours:.2f} h" for r in lv.itertuples()}
    uid = st.selectbox("Block part", list(opts), format_func=opts.get,
                       index=next((i for i, u in enumerate(opts) if "Cleanup" in opts[u]), 0))
    part = lv.set_index("uid").loc[uid]
    if part["hours"] <= 0.25:
        st.info("This part is too short to split.", icon=":material/info:")
        return
    first = st.number_input("Hours kept in this part", min_value=0.25, max_value=float(part["hours"]) - 0.25,
                            value=round(float(part["hours"]) / 2 * 4) / 4, step=0.25)
    to = st.number_input("Session for the other part", min_value=1, value=int(part["session"]) + 1, step=1)
    st.caption(f"The other part gets {float(part['hours']) - first:.2f} h. Total hours still come from the Leveling tab.")
    if st.button("Split", type="primary", icon=":material/call_split:"):
        sessions.split_block(int(uid[1:]), float(first), int(to))
        _bump(key)
        st.rerun()


@st.dialog("Merge split parts")
def _merge_dialog(items: pd.DataFrame, key: str):
    lv = items[(items["kind"] == "Leveling") & (items["parts"].fillna(1) > 1)]
    groups = lv.drop_duplicates(["character_id", "block_type"])
    opts = {(int(r.character_id), r.block_type): f"{r.character} · {r.content.split(' (')[0]}" for r in groups.itertuples()}
    choice = st.selectbox("Block", list(opts), format_func=opts.get)
    st.caption("All parts are merged into the first one (its session is kept).")
    if st.button("Merge", type="primary", icon=":material/call_merge:"):
        sessions.merge_block(*choice)
        _bump(key)
        st.rerun()


def split_merge_buttons(items: pd.DataFrame, key: str) -> None:
    has_parts = not items.empty and (items["parts"].fillna(1) > 1).any()
    if st.button("Split block", icon=":material/call_split:", help="Split a block (e.g. Cleanup) across two sessions."):
        _split_dialog(items, key)
    if st.button("Merge parts", icon=":material/call_merge:", disabled=not has_parts):
        _merge_dialog(items, key)


# ------------------------------------------------------------------ charts

def label_picker(key: str) -> str | None:
    choice = st.segmented_control("Chart labels", list(LABEL_OPTIONS), default="Content", key=key)
    return LABEL_OPTIONS.get(choice or "None")


def _level_points(items: pd.DataFrame, session: int) -> pd.DataFrame:
    """Level vs hours into the session, one line per character (flat while others play)."""
    lv = items[items["kind"] == "Leveling"]
    sess = items[items["session"] == session]
    total = sess["hours"].sum()
    level = {}
    for c, grp in lv.groupby("character"):
        before = grp[grp["session"] < session]
        if not before.empty:
            b = before.iloc[-1]
            level[c] = b["start_level"] + (b["end_level"] - b["start_level"]) * b["frac_end"]
        else:
            level[c] = float(grp["start_level"].iloc[0])
    chars = sess.loc[sess["kind"] == "Leveling", "character"].unique()
    pts = [dict(character=c, hours=0.0, level=level[c], content="", hours_label="", end=False) for c in chars]
    t = 0.0
    for _, b in sess.iterrows():
        if b["kind"] != "Leveling":
            t += float(b["hours"])  # activities take time; levels stay flat
            continue
        c = b["character"]
        pts.append(dict(character=c, hours=t, level=level[c], content="", hours_label="", end=False))
        t += float(b["hours"])
        level[c] = b["start_level"] + (b["end_level"] - b["start_level"]) * b["frac_end"]
        pts.append(dict(character=c, hours=t, level=level[c], content=b["content"],
                        hours_label=f"{b['hours']:.1f} h", end=True))
    pts += [dict(character=c, hours=total, level=level[c], content="", hours_label="", end=False) for c in chars]
    df = pd.DataFrame(pts)
    df["seq"] = range(len(df))
    return df


def level_chart(items: pd.DataFrame, session: int, label: str | None, colors: alt.Scale) -> alt.Chart | None:
    pts = _level_points(items, session)
    if pts.empty:
        return None
    base = alt.Chart(pts).encode(
        x=alt.X("hours:Q", title="Hours into session"),
        y=alt.Y("level:Q", title="Level", scale=alt.Scale(domain=[1, 45]),
                axis=alt.Axis(values=[1, *range(5, 46, 5)], grid=True, labelOverlap=False)),
        color=alt.Color("character:N", title=None, scale=colors),
    )
    line = base.mark_line(point=True).encode(
        order="seq:Q", tooltip=["character", alt.Tooltip("hours:Q", format=".2f"), alt.Tooltip("level:Q", format=".0f")])
    if not label:
        return line.properties(height=320)
    text = base.transform_filter("datum.end").mark_text(align="left", dx=4, dy=-8, fontSize=11).encode(
        text=f"{'character' if label == 'character' else label}:N")
    return (line + text).properties(height=320)


def timeline_chart(items: pd.DataFrame, session: int, label: str | None, colors: alt.Scale,
                   color_by: str | None = "character") -> alt.Chart:
    """Gantt-style bars: what each character does, in order, within the session."""
    sess = items[items["session"] == session].copy()
    sess["end"] = sess["hours"].cumsum()
    sess["start"] = sess["end"] - sess["hours"]
    sess["hours_label"] = sess["hours"].map(lambda h: f"{h:.1f} h")
    base = alt.Chart(sess).encode(
        x=alt.X("start:Q", title="Hours into session"), x2="end:Q",
        y=alt.Y("character:N", title=None, sort=list(dict.fromkeys(sess["character"])),
                axis=alt.Axis(labelOverlap=False)),
    )
    bars = base.mark_bar(cornerRadius=3, stroke="white", strokeWidth=1, height={"band": 0.8}).encode(
        color=(alt.Color("character:N", title=None, scale=colors, legend=None) if color_by == "character"
               else alt.Color(f"{color_by}:N", title=None) if color_by else alt.value("#4C78A8")),
        opacity=alt.condition("datum.kind == 'Leveling'", alt.value(1.0), alt.value(0.6)),
        tooltip=["character", "content", "category", alt.Tooltip("hours:Q", format=".2f")],
    )
    height = max(90, 46 * sess["character"].nunique())
    if not label:
        return bars.properties(height=height)
    text = base.mark_text(align="left", dx=3, fontSize=11, fontWeight="bold", color="#262730").encode(
        x="start:Q", text=f"{label}:N")
    return (bars + text).properties(height=height)
