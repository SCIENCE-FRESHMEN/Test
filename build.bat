@echo off
setlocal
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python scripts\full_score_demo.py
if errorlevel 1 exit /b 1
python -m pytest tests --basetemp=C:\\tmp\\pytest_tmp
if errorlevel 1 exit /b 1
if not exist outputs\package mkdir outputs\package
python main.py demo --output-dir outputs\package
if errorlevel 1 exit /b 1
echo Build complete. Web: uvicorn web_app:app --host 127.0.0.1 --port 8000
endlocal

