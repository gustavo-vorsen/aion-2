import altair as alt
import streamlit as st

from aion import db, seed, session_ui, sessions

items = sessions.load_items(include_activities=False)

with st.container(horizontal=True):
    st.metric("Sessions", int(items["session"].nunique()) if not items.empty else 0, border=True)
    st.metric("Total hours", f"{items['hours'].sum():.1f}", border=True)
    crit = items[items["critical"].fillna(False).astype(bool)]
    st.metric("Critical milestones done by", f"Session {int(crit['session'].max())}" if not crit.empty else "—", border=True)

with st.container(border=True):
    st.subheader("Leveling sessions")
    st.caption(
        "Drag a row by its handle (:material/drag_indicator:) to reorder; dropping it among another session's rows moves it "
        "there. You can also type a **Session** number. **Hours** and **Critical** come from the **Leveling** page. "
        "Split a block to spread it over two sessions. These sessions are shared with the **Weekly planner**."
    )
    with st.container(horizontal=True):
        if st.button("Suggested order", icon=":material/auto_fix_high:",
                     help="All 1→22 blocks, then all 22→45, then cleanup; Main first."):
            with db.connect() as conn:
                seed.suggested_block_order(conn)
            session_ui._bump("leveling_grid")
            st.rerun()
        if st.button("Auto-assign sessions", icon=":material/event_repeat:",
                     help="Fill one-off sessions in order using the daily leveling hours from the sidebar."):
            with db.connect() as conn:
                seed.assign_sessions(conn)
            session_ui._bump("leveling_grid")
            st.rerun()
        session_ui.split_merge_buttons(items, "leveling_grid")
    if items.empty:
        st.info("No leveling blocks. Add characters first.", icon=":material/info:")
        st.stop()
    session_ui.session_grid(items, "leveling_grid", show_runs=False, selectable=False, show_done=False)

label = session_ui.label_picker("leveling_chart_labels")
colors = alt.Scale(domain=sorted(items["character"].unique()))
all_sessions = sorted(items["session"].unique())
cols = st.columns(2) if len(all_sessions) > 1 else [st.container()]
for i, s in enumerate(all_sessions):
    sess = items[items["session"] == s]
    with cols[i % len(cols)], st.container(border=True):
        st.markdown(f"**{sess['session_name'].iloc[0]}** · {sess['hours'].sum():.1f} h · {sess['character'].nunique()} characters")
        chart = session_ui.level_chart(items, s, label, colors)
        if chart is not None:
            st.altair_chart(chart)
