# AION 2 Global planner

Streamlit app for planning leveling and recurring weekly activities. It's built from [aion2_streamlit_spec.md](aion2_streamlit_spec.md).

## Run

```
run.bat          # Windows (or: python run.py)
./run.sh         # macOS / Linux
```

Streamlit arguments are passed through, for example `run.bat --server.port 8502`.

The launcher does the following:

1. It creates or updates `.venv` from `requirements.txt` when needed.
2. It rebuilds `data/aion2.db` from **`data/aion2.sql`** and backs up the old DB to `data/backups/`.
3. It starts Streamlit.
4. When you stop the app, it writes the DB back to `data/aion2.sql`. That covers Ctrl+C, Ctrl+Break, closing the console window and Streamlit exiting. The SQL is also autosaved every 30 s while the app runs.

## Moving to another machine

Only `data/aion2.sql` needs to travel, through git or a synced folder. The `.db` file and `.venv` are local and gitignored. You can also save or download the SQL from **Settings / ruleset → Data**.

## Layout

- `streamlit_app.py`: navigation and the global sidebar
- `app_pages/`: one script per page
- `aion/db.py`: schema. Columns added here are migrated automatically.
- `aion/seed.py`: default data
- `aion/calc.py`: plan, Odyle, Abyss and schedule calculations
- `aion/sessions.py`, `aion/session_ui.py`: shared sessions, the draggable grid and the session charts
- `aion/sqlsync.py`: SQL dump and restore (stdlib only)

The default reward numbers are placeholders tagged `unknown`, and the limits are tagged KR/TW or Global LST. Replace them as Global data is confirmed.
