#!/usr/bin/env sh
# Start the AION 2 planner (restores DB from data/aion2.sql, saves it back on stop).
cd "$(dirname "$0")" || exit 1
if [ -x .venv/bin/python ]; then
    exec .venv/bin/python run.py "$@"
else
    exec python3 run.py "$@"
fi
