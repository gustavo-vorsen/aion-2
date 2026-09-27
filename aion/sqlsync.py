"""SQLite <-> portable SQL dump. Standard library only (used by run.py before the venv exists)."""
from __future__ import annotations

import os
import shutil
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = Path(os.environ.get("AION_DB", DATA_DIR / "aion2.db"))
SQL_PATH = Path(os.environ.get("AION_SQL", DATA_DIR / "aion2.sql"))
BACKUP_DIR = DATA_DIR / "backups"
KEEP_BACKUPS = 10


def dump_sql(db_path: Path = DB_PATH, sql_path: Path = SQL_PATH) -> bool:
    """Write the whole database as SQL text. Atomic replace; skipped if unchanged."""
    if not db_path.exists():
        return False
    src = sqlite3.connect(db_path, timeout=30)
    try:
        text = "\n".join(src.iterdump()) + "\n"
    finally:
        src.close()
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    if sql_path.exists() and sql_path.read_text(encoding="utf-8") == text:
        return False
    tmp = sql_path.with_suffix(".sql.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, sql_path)
    return True


def backup_db(db_path: Path = DB_PATH) -> Path | None:
    if not db_path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"{db_path.stem}-{time.strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(db_path, dest)
    backups = sorted(BACKUP_DIR.glob(f"{db_path.stem}-*.db"))
    for old in backups[:-KEEP_BACKUPS]:
        old.unlink(missing_ok=True)
    return dest


def restore_from_sql(db_path: Path = DB_PATH, sql_path: Path = SQL_PATH) -> bool:
    """Rebuild the database from the SQL dump (previous DB is backed up first)."""
    if not sql_path.exists():
        return False
    tmp = db_path.with_suffix(".db.tmp")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    try:
        conn.executescript(sql_path.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()
    backup_db(db_path)
    for suffix in ("-wal", "-shm", "-journal"):
        Path(str(db_path) + suffix).unlink(missing_ok=True)
    os.replace(tmp, db_path)
    return True
