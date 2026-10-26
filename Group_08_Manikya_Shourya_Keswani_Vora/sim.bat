@echo off
REM Open the simulation: the trained pilot from results\ flies the mission  (e.g. sim.bat --replay, sim.bat --policy expert)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python simulate.py %*
