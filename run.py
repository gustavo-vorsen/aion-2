"""Launch the AION 2 planner.

1. Creates/updates .venv from requirements.txt when needed.
2. Rebuilds data/aion2.db from data/aion2.sql (the old DB is backed up to data/backups).
3. Runs Streamlit.
4. On stop (Ctrl+C, closing the window, or Streamlit exiting) writes the DB back to data/aion2.sql.
   The SQL is also autosaved every AUTOSAVE_SECONDS while the app runs.

Standard library only, so it works with any Python 3.10+ before the venv exists.
Usage: python run.py [extra streamlit args, e.g. --server.port 8502]
"""
from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from aion import sqlsync  # noqa: E402

VENV = ROOT / ".venv"
VENV_PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
REQS = ROOT / "requirements.txt"
REQS_STAMP = VENV / ".requirements.sha256"
AUTOSAVE_SECONDS = 30

_save_lock = threading.Lock()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def log(msg: str) -> None:
    print(f"[aion2] {msg}", flush=True)


def ensure_venv() -> None:
    if not VENV_PY.exists():
        log("Creating .venv ...")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    digest = hashlib.sha256(REQS.read_bytes()).hexdigest()
    if not REQS_STAMP.exists() or REQS_STAMP.read_text().strip() != digest:
        log("Installing requirements ...")
        subprocess.check_call([str(VENV_PY), "-m", "pip", "install", "--upgrade", "pip", "-q"])
        subprocess.check_call([str(VENV_PY), "-m", "pip", "install", "-r", str(REQS), "-q"])
        REQS_STAMP.write_text(digest)


def save(reason: str) -> None:
    with _save_lock:
        try:
            if sqlsync.dump_sql():
                log(f"Saved {_rel(sqlsync.SQL_PATH)} ({reason}).")
        except Exception as exc:  # never lose the shutdown path to a dump error
            log(f"SQL dump failed ({reason}): {exc}")


def install_windows_close_handler() -> None:
    """Dump the SQL when the console window is closed / user logs off / shutdown."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    HANDLER = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    def handler(event: int) -> bool:
        if event in (2, 5, 6):  # CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, CTRL_SHUTDOWN_EVENT
            save("window closed")
        return False  # let default handling continue (Ctrl+C -> KeyboardInterrupt)

    install_windows_close_handler._ref = HANDLER(handler)  # keep a reference alive
    ctypes.windll.kernel32.SetConsoleCtrlHandler(install_windows_close_handler._ref, True)


def main() -> int:
    os.chdir(ROOT)
    ensure_venv()

    if sqlsync.SQL_PATH.exists():
        sqlsync.restore_from_sql()
        log(f"Database rebuilt from {_rel(sqlsync.SQL_PATH)}.")
    # Create tables / apply schema migrations / seed an empty database.
    subprocess.check_call([str(VENV_PY), "-c", "from aion import db; db.init_db()"], cwd=ROOT)
    save("startup")

    install_windows_close_handler()

    def interrupt(*_):
        raise KeyboardInterrupt

    stop_signals = [signal.SIGBREAK] if os.name == "nt" else [signal.SIGTERM, signal.SIGHUP]
    for sig in stop_signals:
        signal.signal(sig, interrupt)

    cmd = [str(VENV_PY), "-m", "streamlit", "run", str(ROOT / "streamlit_app.py"), *sys.argv[1:]]
    log("Starting Streamlit - press Ctrl+C to stop (data is saved on exit).")
    proc = subprocess.Popen(cmd, cwd=ROOT)
    last_mtime = sqlsync.DB_PATH.stat().st_mtime if sqlsync.DB_PATH.exists() else 0.0
    last_check = time.monotonic()
    try:
        while proc.poll() is None:
            time.sleep(1)
            if time.monotonic() - last_check >= AUTOSAVE_SECONDS:
                last_check = time.monotonic()
                mtime = sqlsync.DB_PATH.stat().st_mtime if sqlsync.DB_PATH.exists() else 0.0
                if mtime != last_mtime:
                    last_mtime = mtime
                    save("autosave")
    except KeyboardInterrupt:
        log("Stopping Streamlit ...")
        try:
            proc.wait(timeout=10)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    finally:
        save("shutdown")
    return proc.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
