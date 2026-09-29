"""SQLite schema, migrations and small CRUD helpers."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Iterable

import pandas as pd

from aion.sqlsync import DB_PATH

# table -> (column definitions, table constraints). Columns declared BOOLEAN are
# returned as bool by read_table. New columns added here are migrated automatically.
SCHEMA: dict[str, tuple[list[tuple[str, str]], list[str]]] = {
    "settings": ([("key", "TEXT PRIMARY KEY"), ("value", "TEXT")], []),
    "progress": ([("key", "TEXT PRIMARY KEY"), ("done", "BOOLEAN DEFAULT 0")], []),  # "page" or "page:tab"
    "rulesets": (
        [
            ("key", "TEXT PRIMARY KEY"),
            ("label", "TEXT"),
            ("color", "TEXT DEFAULT 'gray'"),
            ("description", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "characters": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("name", "TEXT NOT NULL DEFAULT 'New character'"),
            ("class", "TEXT DEFAULT 'Gladiator'"),
            ("faction", "TEXT DEFAULT 'Asmodian'"),
            ("server", "TEXT DEFAULT 'Server 1'"),
            ("is_main", "BOOLEAN DEFAULT 0"),
            ("membership", "BOOLEAN DEFAULT 1"),
            ("level", "INTEGER DEFAULT 1"),
            ("item_level", "INTEGER DEFAULT 0"),
            ("combat_power", "INTEGER"),
            ("pvp_item_level", "INTEGER"),
            ("pvp_combat_power", "INTEGER"),
            ("pvp_power_metric", "REAL"),
            ("active", "BOOLEAN DEFAULT 1"),
            ("sort_order", "INTEGER DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "leveling_templates": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("role", "TEXT"),  # main | alt
            ("block_type", "TEXT"),  # early | mid | cleanup
            ("label", "TEXT"),
            ("start_level", "INTEGER"),
            ("end_level", "INTEGER"),
            ("hours", "REAL"),
            ("required", "BOOLEAN DEFAULT 1"),
            ("critical", "BOOLEAN DEFAULT 1"),
            ("priority", "INTEGER DEFAULT 1"),
            ("checklist", "TEXT DEFAULT ''"),
            ("options", "TEXT DEFAULT '{}'"),
        ],
        ["UNIQUE(role, block_type)"],
    ),
    "leveling_blocks": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("character_id", "INTEGER REFERENCES characters(id) ON DELETE CASCADE"),
            ("block_type", "TEXT"),
            ("label", "TEXT"),
            ("start_level", "INTEGER"),
            ("end_level", "INTEGER"),
            ("hours", "REAL"),
            ("required", "BOOLEAN DEFAULT 1"),
            ("critical", "BOOLEAN DEFAULT 1"),
            ("schedule_order", "INTEGER DEFAULT 0"),
            ("session", "INTEGER"),
            ("part_hours", "REAL"),  # split part size; NULL = remainder of the Leveling-tab hours
            ("done", "BOOLEAN DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "sessions": (
        [
            ("number", "INTEGER PRIMARY KEY"),
            ("name", "TEXT"),
            ("permanent", "BOOLEAN DEFAULT 0"),  # recurring weekly-loop session
            ("times_per_week", "REAL DEFAULT 7"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "session_items": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("session", "INTEGER"),
            ("schedule_order", "REAL DEFAULT 0"),
            ("character_id", "INTEGER REFERENCES characters(id) ON DELETE CASCADE"),
            ("activity_id", "INTEGER REFERENCES activities(id) ON DELETE CASCADE"),
            ("runs", "REAL DEFAULT 1"),
            ("done", "BOOLEAN DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "progression_items": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("system", "TEXT"),  # progression tab key, e.g. skills, daevanion, side_quests
            ("faction", "TEXT DEFAULT 'own'"),  # own | enemy
            ("name", "TEXT NOT NULL DEFAULT 'New item'"),
            ("region", "TEXT DEFAULT ''"),
            ("level_req", "INTEGER"),
            ("count", "REAL DEFAULT 1"),  # how many of these exist (e.g. 12 strongholds)
            ("capacity", "REAL"),  # Daevanion boards: points the board can take
            ("minutes_each", "REAL DEFAULT 0"),
            ("scope", "TEXT DEFAULT 'per_character'"),  # per_character | per_server | unknown
            ("enabled", "BOOLEAN DEFAULT 1"),
            ("main_default", "BOOLEAN DEFAULT 1"),
            ("alt_default", "BOOLEAN DEFAULT 1"),
            ("ruleset", "TEXT DEFAULT 'user_override'"),
            ("source_status", "TEXT DEFAULT 'unknown'"),
            ("sort_order", "INTEGER DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "progression_rewards": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("item_id", "INTEGER REFERENCES progression_items(id) ON DELETE CASCADE"),
            ("pool", "TEXT DEFAULT ''"),  # optional label, e.g. "Basic · Pool 4"
            ("currency_key", "TEXT REFERENCES currencies(key) ON DELETE CASCADE"),
            ("amount", "REAL DEFAULT 0"),  # per completion of one item
            ("draws", "REAL DEFAULT 1"),  # times this line is rolled
            ("chance", "REAL DEFAULT 100"),  # % per draw; value used = amount × draws × chance
        ],
        [],
    ),
    "currencies": (
        [
            ("key", "TEXT PRIMARY KEY"),
            ("name", "TEXT"),
            ("category", "TEXT DEFAULT 'material'"),  # kinah | ap | material | currency | progress | gear
            ("tradable", "BOOLEAN DEFAULT 0"),
            ("bound", "BOOLEAN DEFAULT 1"),
            ("shared", "BOOLEAN DEFAULT 0"),
            ("estimated_kinah_value", "REAL"),
            ("weight", "REAL DEFAULT 0"),
            ("gs_per_unit", "REAL DEFAULT 0"),  # Item Level (GS) gained per unit of this reward
            ("sort_order", "INTEGER DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "activities": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("name", "TEXT NOT NULL DEFAULT 'New activity'"),
            ("category", "TEXT DEFAULT 'Daily & Weekly'"),
            ("dungeon", "TEXT"),
            ("mode", "TEXT"),
            ("tier", "TEXT"),
            ("enabled", "BOOLEAN DEFAULT 1"),
            ("main_default", "BOOLEAN DEFAULT 1"),
            ("alt_default", "BOOLEAN DEFAULT 0"),
            ("scope", "TEXT DEFAULT 'unknown'"),
            ("cadence", "TEXT DEFAULT 'weekly'"),
            ("attempts_per_reset", "REAL"),
            ("membership_bonus_attempts", "REAL DEFAULT 0"),
            ("charges_per_day", "REAL"),
            ("charge_cap", "REAL"),
            ("charge_cap_membership", "REAL"),  # max stored with membership
            ("reward_tier", "TEXT"),  # tiered rewards: the tier / score bracket / level the plan counts
            # Recharge: `amount` every `hours` (set = overrides cadence-based weekly attempts), per membership state.
            ("recharge_amount", "REAL"),
            ("recharge_hours", "REAL"),
            ("recharge_amount_membership", "REAL"),
            ("recharge_hours_membership", "REAL"),
            ("reward_claims_per_attempt", "REAL DEFAULT 1"),
            ("membership_extra_claims", "REAL DEFAULT 0"),
            ("weekly_claim_limit", "REAL"),
            ("duration_minutes", "REAL DEFAULT 10"),
            ("odyle_per_claim", "REAL DEFAULT 0"),
            ("kinah_cost", "REAL DEFAULT 0"),
            ("ap_cost", "REAL DEFAULT 0"),
            ("ticket_cost", "REAL DEFAULT 0"),
            ("entry_item_level", "REAL"),
            ("recommended_item_level", "REAL"),
            ("consumes_abyss_time", "BOOLEAN DEFAULT 0"),
            ("ap_cap_category", "TEXT DEFAULT 'none'"),  # none | pve | pvp | excluded
            ("forced_initial_claims", "REAL DEFAULT 0"),
            ("guaranteed_reward_after_claims", "REAL"),
            ("guaranteed_reward_value", "REAL"),
            ("repeat_after_guarantee", "BOOLEAN DEFAULT 1"),
            ("ruleset", "TEXT DEFAULT 'user_override'"),
            ("source_status", "TEXT DEFAULT 'unknown'"),
            ("sort_order", "INTEGER DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "activity_rewards": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("activity_id", "INTEGER REFERENCES activities(id) ON DELETE CASCADE"),
            ("pool", "TEXT DEFAULT ''"),  # optional label, e.g. "Basic · Pool 4"
            ("currency_key", "TEXT REFERENCES currencies(key) ON DELETE CASCADE"),
            ("amount", "REAL DEFAULT 0"),  # per claim
            ("draws", "REAL DEFAULT 1"),  # times this line is rolled
            ("chance", "REAL DEFAULT 100"),  # % per draw; value used = amount × draws × chance
        ],
        [],
    ),
    "character_activity": (
        [
            ("character_id", "INTEGER REFERENCES characters(id) ON DELETE CASCADE"),
            ("activity_id", "INTEGER REFERENCES activities(id) ON DELETE CASCADE"),
            ("enabled", "BOOLEAN"),  # NULL = follow main/alt default
            ("planned_runs", "REAL"),  # NULL = max allowed / auto
            ("use_extra_claim", "BOOLEAN DEFAULT 1"),
            ("milestone_claims_done", "REAL DEFAULT 0"),
        ],
        ["PRIMARY KEY (character_id, activity_id)"],
    ),
    "pity": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("category", "TEXT DEFAULT 'Expedition'"),
            ("mode", "TEXT"),
            ("dungeon", "TEXT"),
            ("claims_needed", "REAL"),  # cube claims that fill the Condensed Cube Energy
            ("reward", "TEXT DEFAULT ''"),  # guaranteed reward (choose one)
            ("repeats", "BOOLEAN DEFAULT 1"),
            ("max_times", "REAL"),  # blank = no limit
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "feather_regions": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("faction", "TEXT"),  # Elyos | Asmodian
            ("region", "TEXT"),
            ("count", "REAL"),
            ("collected", "REAL DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "monolith_levels": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("monolith", "TEXT"),
            ("level", "INTEGER"),
            ("feathers", "REAL"),  # feathers for this level (cumulative is computed)
            ("reward", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "one_time": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("kind", "TEXT"),  # hidden_dungeon | stronghold
            ("faction", "TEXT"),  # Elyos | Asmodian
            ("region", "TEXT"),
            ("name", "TEXT"),
            ("level", "REAL"),
            ("done", "BOOLEAN DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "fill": (
        [
            ("key", "TEXT PRIMARY KEY"),  # page file, or "page:tab"
            ("filled", "REAL DEFAULT 0"),
            ("total", "REAL DEFAULT 0"),  # 0 = nothing to fill on this page / tab
        ],
        [],
    ),
    "odyle_sources": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("name", "TEXT"),
            ("source_type", "TEXT DEFAULT 'shop'"),  # shop | morph | other
            ("scope", "TEXT DEFAULT 'per_character'"),  # per_character | per_server
            ("purchases", "REAL DEFAULT 0"),
            ("odyle_each", "REAL DEFAULT 40"),
            ("kinah_cost_each", "REAL DEFAULT 0"),
            # Crafting materials consumed per craft (Substance Morph).
            ("odyle_cost_each", "REAL DEFAULT 0"),
            ("pure_odyle_cost_each", "REAL DEFAULT 0"),
            ("refined_odyle_cost_each", "REAL DEFAULT 0"),
            ("enabled", "BOOLEAN DEFAULT 1"),
            ("membership_required", "BOOLEAN DEFAULT 0"),
            ("ruleset", "TEXT DEFAULT 'kr_tw_reference'"),
            ("source_status", "TEXT DEFAULT 'provisional'"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "gear_slots": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("character_id", "INTEGER REFERENCES characters(id) ON DELETE CASCADE"),
            ("profile", "TEXT DEFAULT 'pve'"),
            ("slot", "TEXT"),
            ("priority_score", "REAL DEFAULT 0"),
            ("enhancement_level", "INTEGER DEFAULT 0"),
            ("target_level", "INTEGER DEFAULT 0"),
            ("material_budget", "REAL DEFAULT 0"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
    "weekly_log": (
        [
            ("week_start", "TEXT"),
            ("character_id", "INTEGER REFERENCES characters(id) ON DELETE CASCADE"),
            ("activity_id", "INTEGER REFERENCES activities(id) ON DELETE CASCADE"),
            ("runs_done", "REAL DEFAULT 0"),
        ],
        ["PRIMARY KEY (week_start, character_id, activity_id)"],
    ),
    "sources": (
        [
            ("id", "INTEGER PRIMARY KEY"),
            ("activity_id", "INTEGER REFERENCES activities(id) ON DELETE SET NULL"),
            ("ruleset", "TEXT DEFAULT 'user_override'"),
            ("source_name", "TEXT"),
            ("source_url", "TEXT"),
            ("verified_date", "TEXT"),
            ("status", "TEXT DEFAULT 'provisional'"),
            ("notes", "TEXT DEFAULT ''"),
        ],
        [],
    ),
}


def bool_columns(table: str) -> list[str]:
    return [c for c, d in SCHEMA[table][0] if d.upper().startswith("BOOLEAN")]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _rebuild_reward_tables(conn: sqlite3.Connection) -> None:
    """Old reward tables had one row per (owner, currency); rebuild them with a row id so a reward can repeat."""
    for table in ("activity_rewards", "progression_rewards"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not cols or "id" in cols:
            continue
        conn.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
        new_cols, constraints = SCHEMA[table]
        conn.execute(f"CREATE TABLE {table} ({', '.join([f'{c} {d}' for c, d in new_cols] + constraints)})")
        keep = [c for c, _ in new_cols if c in cols]
        conn.execute(f"INSERT INTO {table} ({', '.join(keep)}) SELECT {', '.join(keep)} FROM {table}_old")
        conn.execute(f"DROP TABLE {table}_old")


def init_db() -> None:
    """Create missing tables/columns, then seed an empty database."""
    from aion import seed

    with connect() as conn:
        _rebuild_reward_tables(conn)
        for table, (cols, constraints) in SCHEMA.items():
            body = ", ".join([f"{c} {d}" for c, d in cols] + constraints)
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({body})")
            existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
            for c, d in cols:
                if c not in existing:
                    # ALTER TABLE cannot add PRIMARY KEY / REFERENCES clauses.
                    d = d.replace("PRIMARY KEY", "").split("REFERENCES")[0]
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {c} {d}")
        if conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
            seed.seed(conn)
        seed.ensure_defaults(conn)


def _py(v: Any) -> Any:
    """Convert numpy/pandas scalars to plain Python for sqlite3."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v


def read_table(table: str, order: str | None = None, where: str = "", params: Iterable = ()) -> pd.DataFrame:
    sql = f"SELECT * FROM {table}"
    if where:
        sql += f" WHERE {where}"
    if order:
        sql += f" ORDER BY {order}"
    with connect() as conn:
        df = pd.read_sql_query(sql, conn, params=list(params))
    for c in bool_columns(table):
        if c in df.columns:
            df[c] = df[c].map(lambda x: None if pd.isna(x) else bool(x)).astype("object" if df[c].isna().any() else bool)
    return df


def execute(sql: str, params: Iterable = ()) -> int:
    with connect() as conn:
        cur = conn.execute(sql, [_py(p) for p in params])
        return cur.lastrowid


def insert(table: str, values: dict[str, Any]) -> int:
    valid = {c for c, _ in SCHEMA[table][0]}
    values = {k: _py(v) for k, v in values.items() if k in valid}
    cols = ", ".join(values)
    qs = ", ".join("?" for _ in values)
    return execute(f"INSERT INTO {table} ({cols}) VALUES ({qs})", values.values())


def update(table: str, where: dict[str, Any], values: dict[str, Any]) -> None:
    valid = {c for c, _ in SCHEMA[table][0]}
    values = {k: _py(v) for k, v in values.items() if k in valid}
    if not values:
        return
    sets = ", ".join(f"{k} = ?" for k in values)
    cond = " AND ".join(f"{k} = ?" for k in where)
    execute(f"UPDATE {table} SET {sets} WHERE {cond}", [*values.values(), *where.values()])


def upsert(table: str, keys: dict[str, Any], values: dict[str, Any]) -> None:
    """Insert or update a row identified by its composite key."""
    valid = {c for c, _ in SCHEMA[table][0]}
    values = {k: v for k, v in values.items() if k in valid}
    row = {**keys, **values}
    cols = ", ".join(row)
    qs = ", ".join("?" for _ in row)
    conflict = ", ".join(keys)
    sets = ", ".join(f"{k} = excluded.{k}" for k in values) or f"{next(iter(keys))} = excluded.{next(iter(keys))}"
    execute(
        f"INSERT INTO {table} ({cols}) VALUES ({qs}) ON CONFLICT({conflict}) DO UPDATE SET {sets}",
        row.values(),
    )


def delete(table: str, where: dict[str, Any]) -> None:
    cond = " AND ".join(f"{k} = ?" for k in where)
    execute(f"DELETE FROM {table} WHERE {cond}", where.values())


# ---------------------------------------------------------------- settings

def get_settings() -> dict[str, Any]:
    from aion.seed import DEFAULT_SETTINGS

    with connect() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    out = dict(DEFAULT_SETTINGS)
    out.update({k: json.loads(v) for k, v in rows})
    return out


def set_setting(key: str, value: Any) -> None:
    upsert("settings", {"key": key}, {"value": json.dumps(_py(value))})
