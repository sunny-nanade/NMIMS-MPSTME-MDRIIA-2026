@echo off
REM Train stages 1 -> 2 -> 3 on the GPU; results saved to results\  (extra args go to train_all.py, e.g. --stages 2 3)
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python train_all.py %*
