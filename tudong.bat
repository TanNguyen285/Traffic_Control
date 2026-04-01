@echo off
title Traffic AI Yolov8 - Optimized
color 0A

:: ======================================================
::   TRAFFIC AI - AUTO SETUP & RUN
:: ======================================================

:: 1. Luôn chạy tại thư mục hiện tại
cd /d "%~dp0"

echo [INFO] Dang khoi tao he thong...

:: 2. TIM PYTHON (linh hoat hon ban cu)
set "PY_EXE="
if exist "%~dp0python310\python.exe" set "PY_EXE=%~dp0python310\python.exe"
if exist "%~dp0python-3.10.11\python.exe" set "PY_EXE=%~dp0python-3.10.11\python.exe"

if "%PY_EXE%"=="" (
echo [LOI] Khong tim thay Python!
pause
exit
)

:: Lay thu muc Python
for %%i in ("%PY_EXE%") do set "PY_DIR=%%~dpi"
set "PY_DIR=%PY_DIR:~0,-1%"

echo [OK] Python: %PY_EXE%

:: 3. CAI PIP NEU CHUA CO
if exist "%PY_DIR%\Scripts\pip.exe" goto SKIP_PIP
echo [!] Dang cai Pip...
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
"%PY_EXE%" get-pip.py
del get-pip.py
:SKIP_PIP

:: 4. CAI THU VIEN (tach rieng de on dinh hon)
if exist "%~dp0venv_data" goto SKIP_INSTALL

echo [!] Dang tai thu vien AI...
mkdir venv_data

"%PY_EXE%" -m pip install --no-warn-script-location --target "%~dp0venv_data" -r "%~dp0requirement.text"

if errorlevel 1 (
echo [LOI] Cai thu vien that bai! Kiem tra mang.
pause
exit
)

:SKIP_INSTALL

:: 5. SET PYTHONPATH (quan trong)
set "BASE_DIR=%~dp0"
set "PYTHONPATH=%BASE_DIR%venv_data;%BASE_DIR%web_test"

:: 6. CHAY APP
echo ==========================================
echo [!] Dang khoi dong Traffic AI...
echo ==========================================

"%PY_EXE%" "%BASE_DIR%web_test\project\app.pyw"

if errorlevel 1 (
echo.
echo [LOI] App bi dung. Kiem tra log ben tren.
)

echo.
echo [INFO] App da dong.
pause
