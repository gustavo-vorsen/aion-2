"""Sessions shared by the Leveling schedule and the Weekly planner.

A session holds leveling block parts (hours always come from the Leveling tab) and
activity items from the Main/Alt loops. Permanent sessions repeat `times_per_week`.
"""
from __future__ import annotations

import math
import sqlite3

import pandas as pd

from aion import db


# ------------------------------------------------------------------ leveling parts (sqlite level)

def block_hours(conn: sqlite3.Connection) -> dict[int, dict]:
    """Hours/critical per leveling_blocks row, derived live from the Leveling-tab templates.

    A block may be split into parts: parts with part_hours keep that size and the part with
    NULL part_hours gets the remainder of the template hours.
    """
    tmpl = {(r[0], r[1]): (float(r[2] or 0), bool(r[3])) for r in conn.execute(
        "SELECT role, block_type, hours, critical FROM leveling_templates")}
    rows = conn.execute(
        "SELECT b.id, b.character_id, b.block_type, b.part_hours, c.is_main FROM leveling_blocks b "
        "JOIN characters c ON c.id = b.character_id ORDER BY b.session, b.schedule_order, b.id").fetchall()
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r[1], r[2]), []).append(r)
    out = {}
    for (cid, bt), parts in groups.items():
        total, critical = tmpl.get(("main" if parts[0][4] else "alt", bt), (0.0, False))
        fixed = sum(float(p[3]) for p in parts if p[3] is not None)
        n_rem = sum(1 for p in parts if p[3] is None)
        remainder = max(total - fixed, 0.0) / n_rem if n_rem else 0.0
        done_h = 0.0
        for i, p in enumerate(parts, start=1):
            h = float(p[3]) if p[3] is not None else remainder
            out[p[0]] = dict(hours=h, critical=critical, part=i, parts=len(parts), total=total,
                             frac_start=done_h / total if total else 0.0,
                             frac_end=min((done_h + h) / total, 1.0) if total else 1.0)
            done_h += h
    return out


def ensure_sessions(conn: sqlite3.Connection) -> None:
    used = {r[0] for r in conn.execute(
        "SELECT session FROM leveling_blocks WHERE session IS NOT NULL UNION SELECT session FROM session_items WHERE session IS NOT NULL")}
    for n in used:
        conn.execute("INSERT OR IGNORE INTO sessions (number, name, permanent, times_per_week) VALUES (?, ?, 0, 7)",
                     (int(n), f"Session {int(n)}"))


def split_block(block_id: int, first_hours: float, new_session: int) -> None:
    """Split a leveling part: this row keeps `first_hours`, a new part gets the rest."""
    with db.connect() as conn:
        info = block_hours(conn)[block_id]
        cid, bt, part_hours, order = conn.execute(
            "SELECT character_id, block_type, part_hours, schedule_order FROM leveling_blocks WHERE id = ?",
            (block_id,)).fetchone()
        rest = info["hours"] - first_hours
        conn.execute("UPDATE leveling_blocks SET part_hours = ? WHERE id = ?", (first_hours, block_id))
        # The new part stays the remainder (NULL) when this row was the remainder.
        conn.execute(
            "INSERT INTO leveling_blocks (character_id, block_type, label, start_level, end_level, hours, required, critical, "
            "schedule_order, session, part_hours, done) SELECT character_id, block_type, label, start_level, end_level, hours, "
            "required, critical, ?, ?, ?, 0 FROM leveling_blocks WHERE id = ?",
            (order + 0.5, new_session, None if part_hours is None else rest, block_id))
        ensure_sessions(conn)


def merge_block(character_id: int, block_type: str) -> None:
    with db.connect() as conn:
        ids = [r[0] for r in conn.execute(
            "SELECT id FROM leveling_blocks WHERE character_id = ? AND block_type = ? ORDER BY session, schedule_order, id",
            (character_id, block_type))]
        if len(ids) > 1:
            conn.execute(f"DELETE FROM leveling_blocks WHERE id IN ({','.join('?' * (len(ids) - 1))})", ids[1:])
        conn.execute("UPDATE leveling_blocks SET part_hours = NULL WHERE id = ?", (ids[0],))


# ------------------------------------------------------------------ items (pandas level)

ITEM_COLS = ["uid", "kind", "ref_id", "session", "order", "session_name", "permanent", "times_per_week",
             "character_id", "character", "class", "role", "content", "category", "runs", "hours",
             "critical", "done", "start_level", "end_level", "frac_start", "frac_end", "block_type", "parts"]


def load_items(include_activities: bool = True) -> pd.DataFrame:
    with db.connect() as conn:
        ensure_sessions(conn)
        bh = block_hours(conn)
    chars = db.read_table("characters")
    chars = chars[chars["active"].astype(bool)].set_index("id")
    sessions = db.read_table("sessions").set_index("number")
    rows = []
    for _, b in db.read_table("leveling_blocks").iterrows():
        if b["character_id"] not in chars.index or b["id"] not in bh:
            continue
        c, h = chars.loc[b["character_id"]], bh[b["id"]]
        rows.append(dict(
            uid=f"L{b['id']}", kind="Leveling", ref_id=int(b["id"]), session=int(b["session"] or 1),
            order=float(b["schedule_order"] or 0), character_id=int(b["character_id"]), character=c["name"],
            **{"class": c["class"]}, role="Main" if c["is_main"] else "Alt",
            content=b["label"] + (f" ({h['part']}/{h['parts']})" if h["parts"] > 1 else ""), category="Leveling",
            runs=None, hours=h["hours"], critical=h["critical"], done=bool(b["done"]),
            start_level=int(b["start_level"]), end_level=int(b["end_level"]),
            frac_start=h["frac_start"], frac_end=h["frac_end"], block_type=b["block_type"], parts=h["parts"],
        ))
    if include_activities:
        acts = db.read_table("activities").set_index("id")
        for _, it in db.read_table("session_items").iterrows():
            if it["character_id"] not in chars.index or it["activity_id"] not in acts.index:
                continue
            c, a = chars.loc[it["character_id"]], acts.loc[it["activity_id"]]
            runs = float(it["runs"] or 0)
            rows.append(dict(
                uid=f"A{it['id']}", kind="Activity", ref_id=int(it["id"]), session=int(it["session"] or 1),
                order=float(it["schedule_order"] or 0), character_id=int(it["character_id"]), character=c["name"],
                **{"class": c["class"]}, role="Main" if c["is_main"] else "Alt",
                content=a["name"], category=a["category"], runs=runs,
                hours=runs * float(a["duration_minutes"] or 0) / 60.0, critical=None, done=bool(it["done"]),
                start_level=None, end_level=None, frac_start=None, frac_end=None, block_type=None, parts=None,
            ))
    df = pd.DataFrame(rows, columns=[c for c in ITEM_COLS if c not in ("session_name", "permanent", "times_per_week")])
    if df.empty:
        return pd.DataFrame(columns=ITEM_COLS + ["session_hours"])
    df["session_name"] = df["session"].map(sessions["name"]).fillna(df["session"].map(lambda s: f"Session {s}"))
    df["permanent"] = df["session"].map(sessions["permanent"]).fillna(False).astype(bool)
    df["times_per_week"] = df["session"].map(sessions["times_per_week"]).fillna(1.0).astype(float)
    df = df.sort_values(["session", "order", "kind", "ref_id"]).reset_index(drop=True)
    df["session_hours"] = df.groupby("session")["hours"].cumsum()
    return df


def activity_pool(plan: pd.DataFrame, items: pd.DataFrame) -> pd.DataFrame:
    """Weekly runs from the Main/Alt loops vs runs already placed in sessions."""
    if plan.empty:
        return pd.DataFrame()
    pool = plan.groupby(["character_id", "character", "role", "activity_id", "activity", "category"], as_index=False).agg(
        weekly_runs=("attempts", "sum"), weekly_hours=("hours", "sum"))
    pool["hours_per_run"] = (pool["weekly_hours"] / pool["weekly_runs"]).where(pool["weekly_runs"] > 0, 0.0)
    placed = pd.Series(dtype=float)
    if not items.empty:
        acts = items[items["kind"] == "Activity"].copy()
        if not acts.empty:
            ids = db.read_table("session_items").set_index("id")["activity_id"]
            acts["activity_id"] = acts["ref_id"].map(ids)
            acts["weekly"] = acts["runs"] * acts["times_per_week"].where(acts["permanent"], 1.0)
            placed = acts.groupby(["character_id", "activity_id"])["weekly"].sum()
    pool["placed_runs"] = [placed.get((c, a), 0.0) for c, a in zip(pool["character_id"], pool["activity_id"])]
    pool["remaining_runs"] = (pool["weekly_runs"] - pool["placed_runs"]).clip(lower=0)
    return pool


def add_activity_items(rows: pd.DataFrame, session: int, runs_mode: str, fixed_runs: float) -> int:
    sess = db.read_table("sessions", where="number = ?", params=[session])
    permanent = bool(sess.iloc[0]["permanent"]) if not sess.empty else False
    times = float(sess.iloc[0]["times_per_week"] or 1) if not sess.empty else 1.0
    with db.connect() as conn:
        order = conn.execute("SELECT COALESCE(MAX(schedule_order), 0) FROM session_items WHERE session = ?", (session,)).fetchone()[0]
        lv = conn.execute("SELECT COALESCE(MAX(schedule_order), 0) FROM leveling_blocks WHERE session = ?", (session,)).fetchone()[0]
        order = max(order, lv)
        n = 0
        for _, r in rows.iterrows():
            if runs_mode == "fixed":
                runs = fixed_runs
            else:  # fill what is left of the weekly runs
                runs = r["remaining_runs"] / times if permanent else r["remaining_runs"]
                runs = math.ceil(runs * 100) / 100
            if runs <= 0:
                continue
            order += 1
            conn.execute("INSERT INTO session_items (session, schedule_order, character_id, activity_id, runs) VALUES (?, ?, ?, ?, ?)",
                         (session, order, int(r["character_id"]), int(r["activity_id"]), runs))
            n += 1
        ensure_sessions(conn)
    return n


def remove_items(uids: list[str]) -> None:
    ids = [int(u[1:]) for u in uids if u.startswith("A")]
    for i in ids:
        db.delete("session_items", {"id": i})


def save_item(uid: str, values: dict) -> None:
    table = "leveling_blocks" if uid.startswith("L") else "session_items"
    allowed = {"session", "schedule_order", "done"} | ({"runs"} if table == "session_items" else set())
    db.update(table, {"id": int(uid[1:])}, {k: v for k, v in values.items() if k in allowed})
