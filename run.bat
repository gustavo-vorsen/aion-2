@echo off
rem Start the AION 2 planner (restores DB from data\aion2.sql, saves it back on stop).
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py %*
) else (
    where py >nul 2>nul && (py -3 run.py %*) || (python run.py %*)
)
