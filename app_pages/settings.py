import streamlit as st

from aion import calc, db, progress, sqlsync, ui

d = ui.data()

tab_gen, tab_rules, tab_sources, tab_data = progress.tabs("settings", [
    ("general", ":material/tune: General"), ("rulesets", ":material/verified: Rulesets"),
    ("sources", ":material/menu_book: Sources"), ("data", ":material/database: Data"),
])

with tab_gen:
    progress.tab_done("settings", "general")
    with st.container(border=True):
        st.subheader("Weekly reset")
        with st.container(horizontal=True):
            ui.s_select("Reset day", "reset_day", calc.WEEKDAYS)
            ui.s_time("Reset time", "reset_time")
            ui.s_number("Weeks per season", "season_weeks", min_value=1.0)
        st.caption(f"Current week started **{calc.week_start(d.settings):%A %d %b %Y}**.")
    with st.container(border=True):
        st.subheader("Valuation")
        with st.container(horizontal=True):
            ui.s_select("Kinah value mode", "kinah_value_mode", calc.KINAH_VALUE_MODES)
            ui.s_toggle("Include bound Kinah", "include_bound_kinah")
        st.caption("Per-currency Kinah values and value-score weights are set on **Rewards & currencies**.")

with tab_rules:
    progress.tab_done("settings", "rulesets")
    st.caption("Global, Global LST and KR/TW values are tagged separately. KR/TW numbers are never silently shown as Global-confirmed.")
    ui.ruleset_badges()
    ui.table_editor(
        "rulesets", d.rulesets[["key", "label", "color", "description"]], key="rulesets_editor",
        allow_add=False, allow_delete=False, disabled=["key"],
        column_config={
            "color": ui.cc.SelectboxColumn("Color", options=["green", "blue", "orange", "violet", "red", "yellow", "gray"]),
            "description": ui.cc.TextColumn("Description", width="large"),
        },
    )
    acts = d.activities.assign(status=[calc.status_label(r, s) for r, s in zip(d.activities["ruleset"], d.activities["source_status"])])
    counts = acts.groupby("status", as_index=False).size().rename(columns={"size": "activities"})
    ui.bar(counts, "status", "activities", title="Activities", fmt_=",.0f", height=220)
    with st.expander("Values still requiring final Global verification", icon=":material/pending:"):
        st.markdown(
            "- Odyle shop & Substance Morph weekly limits\n- Open Abyss weekly time & Rift Stone extension\n"
            "- AP cap structure\n- Corridor availability/reset/rewards\n- 5v5 / 10v10 reward limits & scope\n"
            "- Shugo Festival scope & weekly keys\n- Raid scope/count\n- Supply Request scope\n"
            "- Command Scroll & Abyss Command scope\n- Dungeon reward quantities & Kinah/AP/material values\n- GS gates"
        )

with tab_sources:
    progress.tab_done("settings", "sources")
    st.caption("Track where every value came from. Link a source to an activity to document it.")
    src = db.read_table("sources", order="id")
    act_names = dict(zip(d.activities["id"].astype(int), d.activities["name"]))
    ui.table_editor(
        "sources", src[["id", "activity_id", "ruleset", "source_name", "source_url", "verified_date", "status", "notes"]],
        key="sources_editor",
        column_config={
            "activity_id": ui.cc.SelectboxColumn("Activity", options=list(act_names), format_func=act_names.get),
            "ruleset": ui.activity_columns()["ruleset"],
            "source_name": ui.cc.TextColumn("Source", required=True),
            "source_url": ui.cc.LinkColumn("URL"),
            "verified_date": ui.cc.TextColumn("Verified (YYYY-MM-DD)"),
            "status": ui.cc.SelectboxColumn("Status", options=calc.SOURCE_STATUSES),
            "notes": ui.cc.TextColumn("Notes", width="large"),
        },
    )

with tab_data:
    progress.tab_done("settings", "data")
    st.caption(
        f"Database: `{sqlsync.DB_PATH}`  \nPortable SQL dump: `{sqlsync.SQL_PATH}`  \n"
        "The launcher restores the database from the SQL dump on start and writes it back on stop. "
        "Sync the SQL file (e.g. with git) to continue on another machine."
    )
    with st.container(horizontal=True):
        if st.button("Save SQL dump now", icon=":material/save:", type="primary"):
            changed = sqlsync.dump_sql()
            st.toast("SQL dump written." if changed else "SQL dump already up to date.", icon=":material/check:")
        if sqlsync.SQL_PATH.exists():
            st.download_button("Download SQL dump", sqlsync.SQL_PATH.read_bytes(), file_name="aion2.sql",
                               mime="application/sql", icon=":material/download:")

    @st.dialog("Reset all data?")
    def confirm_reset():
        st.warning("This deletes every character, activity and setting and restores the defaults. A backup of the current database is kept in data/backups.", icon=":material/warning:")
        if st.button("Reset to defaults", type="primary", icon=":material/restart_alt:"):
            sqlsync.backup_db()
            with db.connect() as conn:
                conn.execute("PRAGMA foreign_keys = OFF")
                for t in db.SCHEMA:
                    conn.execute(f"DROP TABLE IF EXISTS {t}")
            db.init_db()
            st.rerun()

    if st.button("Reset to defaults…", icon=":material/restart_alt:"):
        confirm_reset()
