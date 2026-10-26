@echo off
REM One-time setup on Windows (lab PC): venv + CUDA PyTorch + deps + scene + live water + tests
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
if not exist .venv %PY% -m venv .venv || goto :err
call .venv\Scripts\activate.bat || goto :err
python -m pip install --upgrade pip
REM CUDA build of PyTorch FIRST (RTX 50-series GPU: change cu126 to cu128)
pip install torch --index-url https://download.pytorch.org/whl/cu126 || goto :err
pip install -r requirements.txt || goto :err
python check_gpu.py
cd environment
python scene_generator.py --houses 5 --seed 1 --output scene_flood.xml || goto :err
cd ..
python -m pytest tests -q
echo.
echo Setup done.  Train:  train.bat      Watch:  sim.bat      Replay:  sim.bat --replay
goto :eof
:err
echo SETUP FAILED - see the error above.
exit /b 1
