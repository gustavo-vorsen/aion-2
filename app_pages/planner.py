import altair as alt
import pandas as pd
import streamlit as st

from aion import db, session_ui, sessions, ui

items = sessions.load_items()
pool = sessions.activity_pool(ui.plan(), items)

st.caption(
    "Create sessions and organize the pool: leveling lines come from **Leveling schedule** automatically, and you "
    "add activities from the **Main loop** / **Alt loop** pool. **Permanent** sessions are your recurring weekly "
    "loop and repeat *times per week*; one-off sessions (e.g. launch days) happen once."
)

# ------------------------------------------------------------------ sessions
@st.dialog("Add session")
def add_session_dialog(next_number: int):
    name = st.text_input("Name", value=f"Session {next_number}")
    permanent = st.toggle("Permanent (recurring weekly loop)", value=True)
    times = st.number_input("Times per week", min_value=1.0, value=7.0, step=1.0, disabled=not permanent)
    if st.button("Add", type="primary", icon=":material/add:"):
        db.insert("sessions", {"number": next_number, "name": name.strip() or f"Session {next_number}",
                               "permanent": permanent, "times_per_week": times})
        session_ui._bump("planner_grid")
        st.rerun()


@st.dialog("Remove session")
def remove_session_dialog(removable: pd.DataFrame):
    labels = {int(r.number): f"{r.number} · {r.name}" for r in removable.itertuples()}
    n = st.selectbox("Session", list(labels), format_func=labels.get)
    n_items = len(db.read_table("session_items", where="session = ?", params=[n]))
    if n_items:
        st.warning(f"Its {n_items} activities will be removed too (they go back to the pool).", icon=":material/warning:")
    if st.button("Remove", type="primary", icon=":material/delete:"):
        db.execute("DELETE FROM session_items WHERE session = ?", [n])
        db.delete("sessions", {"number": n})
        session_ui._bump("planner_grid")
        st.rerun()


def delete_session(rk: dict) -> None:
    if rk["number"] in {int(x) for x in db.read_table("leveling_blocks")["session"].dropna()}:
        st.toast(f"Session {rk['number']} is used by the Leveling schedule and can't be removed.", icon=":material/block:")
        return
    db.execute("DELETE FROM session_items WHERE session = ?", [rk["number"]])
    db.delete("sessions", rk)
    session_ui._bump("planner_grid")


with st.container(border=True):
    st.subheader("Sessions")
    st.caption("Sessions used by the **Leveling schedule** are always here. Add your own (e.g. a permanent daily loop) "
               "and remove them when no longer needed.")
    sess = db.read_table("sessions", order="number")
    leveling_sessions = {int(x) for x in db.read_table("leveling_blocks")["session"].dropna()}
    sess["from_leveling"] = sess["number"].isin(leveling_sessions)
    ui.editor(
        sess[["number", "name", "from_leveling", "permanent", "times_per_week", "notes"]], "sessions_editor",
        [{"number": int(n)} for n in sess["number"]],
        on_update=lambda rk, ch: db.update("sessions", rk, {k: v for k, v in ch.items() if k not in ("number", "from_leveling")}),
        on_delete=delete_session,
        disabled=["number", "from_leveling"],
        column_config={
            "number": ui.cc.NumberColumn("Session #"),
            "name": ui.cc.TextColumn("Name"),
            "from_leveling": ui.cc.CheckboxColumn("Leveling", help="Used by the Leveling schedule; can't be removed."),
            "permanent": ui.cc.CheckboxColumn("Permanent", help="Recurring weekly-loop session."),
            "times_per_week": ui.cc.NumberColumn("Times / week", min_value=0.0, step=1.0,
                                                 help="Only used for permanent sessions."),
            "notes": ui.cc.TextColumn("Notes", width="large"),
        },
    )
    removable = sess[~sess["from_leveling"]]
    with st.container(horizontal=True):
        if st.button("Add session", icon=":material/add:", type="primary"):
            add_session_dialog(int(sess["number"].max()) + 1 if not sess.empty else 1)
        if st.button("Remove session", icon=":material/delete:", disabled=removable.empty,
                     help=None if not removable.empty else "Only leveling sessions exist; they can't be removed."):
            remove_session_dialog(removable)

# ------------------------------------------------------------------ pool
with st.container(border=True):
    st.subheader("Activity pool (Main & Alt loops)")
    if pool.empty:
        st.info("No loop activities. Mark activities as Main/Alt in the content tabs.", icon=":material/info:")
    else:
        show_all = st.toggle("Show fully placed activities", value=False)
        view = pool if show_all else pool[pool["remaining_runs"] > 1e-9]
        view = view.reset_index(drop=True)
        event = ui.show(
            view[["character", "role", "activity", "category", "weekly_runs", "placed_runs", "remaining_runs", "hours_per_run"]],
            hide_index=True, on_select="rerun", selection_mode="multi-row", key="pool_table",
            column_config={
                "character": ui.cc.TextColumn("Character", pinned=True),
                "role": "Role", "activity": ui.cc.TextColumn("Activity"), "category": "Type",
                "weekly_runs": ui.cc.NumberColumn("Weekly runs", format="%.1f"),
                "placed_runs": ui.cc.NumberColumn("Placed / week", format="%.1f"),
                "remaining_runs": ui.cc.NumberColumn("Remaining", format="%.1f"),
                "hours_per_run": ui.cc.NumberColumn("Hours / run", format="%.2f"),
            },
        )
        chosen = view.iloc[event.selection.rows] if event.selection.rows else view.iloc[0:0]
        sess = db.read_table("sessions", order="number")
        labels = {int(r.number): f"{r.number} · {r.name}" + (f" (permanent ×{r.times_per_week:g}/week)" if r.permanent else "")
                  for r in sess.itertuples()}
        with st.container(horizontal=True, vertical_alignment="bottom"):
            target = st.selectbox("Add to session", list(labels), format_func=labels.get, key="pool_target") if labels else None
            mode = st.segmented_control("Runs", ["Fill remaining", "Fixed"], default="Fill remaining", key="pool_mode")
            fixed = st.number_input("Runs per session", min_value=0.25, value=1.0, step=1.0, key="pool_fixed",
                                    disabled=mode != "Fixed")
            if st.button(f"Add {len(chosen)} selected", type="primary", icon=":material/playlist_add:",
                         disabled=chosen.empty or target is None):
                n = sessions.add_activity_items(chosen, int(target), "fixed" if mode == "Fixed" else "fill", float(fixed))
                session_ui._bump("planner_grid")
                st.toast(f"Added {n} activities to session {target}.", icon=":material/check:")
                st.rerun()
        st.caption("Select rows, pick a session and add. *Fill remaining* spreads what is left over the session's "
                   "times per week (permanent) or puts it all in one go (one-off).")

# ------------------------------------------------------------------ organizer
items = sessions.load_items()
with st.container(border=True):
    st.subheader("Sessions organizer")
    st.caption("Drag rows between sessions, edit **Runs** of activities, tick **Done**. Leveling rows follow the "
               "Leveling schedule (same sessions). Click rows to select activities to remove.")
    with st.container(horizontal=True):
        session_ui.split_merge_buttons(items, "planner_grid")
    if items.empty:
        st.info("Nothing scheduled yet.", icon=":material/info:")
        st.stop()
    selected = session_ui.session_grid(items, "planner_grid", show_runs=True, selectable=True)
    removable = [u for u in selected if u.startswith("A")]
    if st.button(f"Remove {len(removable)} selected activities", icon=":material/delete:", disabled=not removable):
        sessions.remove_items(removable)
        session_ui._bump("planner_grid")
        st.rerun()

# ------------------------------------------------------------------ summary & charts
summary = items.groupby(["session", "session_name", "permanent", "times_per_week"], as_index=False).agg(
    hours=("hours", "sum"), characters=("character", "nunique"), items=("uid", "count"))
summary["weekly_hours"] = summary["hours"] * summary["times_per_week"].where(summary["permanent"], 1.0)
with st.container(horizontal=True):
    perm = summary[summary["permanent"]]
    st.metric("Permanent loop hours / week", f"{perm['weekly_hours'].sum():.1f}", border=True)
    st.metric("One-off session hours", f"{summary.loc[~summary['permanent'], 'hours'].sum():.1f}", border=True)
    left = pool["remaining_runs"].gt(1e-9).sum() if not pool.empty else 0
    st.metric("Pool activities not fully placed", int(left), border=True)

with st.container(horizontal=True, vertical_alignment="bottom"):
    label = session_ui.label_picker("planner_chart_labels")
    color_by = st.selectbox("Color / legend by", ["character", "category", "kind", "role", None], key="planner_chart_color",
                            format_func=lambda c: "None (single color)" if c is None else ui.GROUP_LABELS.get(c, c))
colors = alt.Scale(domain=sorted(items["character"].unique()))
all_sessions = sorted(items["session"].unique())
cols = st.columns(2) if len(all_sessions) > 1 else [st.container()]
for i, s in enumerate(all_sessions):
    row = summary[summary["session"] == s].iloc[0]
    with cols[i % len(cols)], st.container(border=True):
        tag = f" · permanent ×{row['times_per_week']:g}/week" if row["permanent"] else ""
        st.markdown(f"**{row['session_name']}** · {row['hours']:.1f} h{tag}")
        st.altair_chart(session_ui.timeline_chart(items, s, label, colors, color_by))
