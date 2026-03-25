@echo off
title He Thong Giao Thong AI - Final Stable
color 0B
cd /d "%~dp0"

echo ======================================================
echo    TRAFFIC AI - KHOI TAO MOI TRUONG TU DONG
echo ======================================================

:: 1. TÌM FOLDER PYTHON
set "PY_EXE="
if exist "python310\python.exe" set "PY_EXE=python310\python.exe"
if exist "python-3.10.11\python.exe" set "PY_EXE=python-3.10.11\python.exe"
if exist "python3.10.11\python.exe" set "PY_EXE=python3.10.11\python.exe"

if "%PY_EXE%"=="" (
    echo [LOI] Khong tim thay folder Python!
    pause
    exit
)

:: Lay duong dan thu muc Python
for %%i in ("%PY_EXE%") do set "PY_DIR=%%~dpi"
set "PY_DIR=%PY_DIR:~0,-1%"

:: 2. THIẾT LẬP PIP (Dùng nhãn GOTO để tránh lỗi ngoặc đơn)
if exist "%PY_DIR%\Scripts\pip.exe" goto SKIP_PIP
    echo [!] Dang thiet lap Pip...
    powershell -Command "Invoke-WebRequest -Uri https://bootstrap.pypa.io/get-pip.py -OutFile get-pip.py"
    "%PY_EXE%" get-pip.py
    del get-pip.py
:SKIP_PIP

:: 3. TẢI THƯ VIỆN (Kiểm tra folder torch để biết đã tải chưa)
if exist "venv_data\torch" goto SKIP_INSTALL
    echo [!] Dang tai thu vien AI (Torch, YOLO, OpenCV...)
    echo [!] Vui long cho trong giay lat...
    if not exist "venv_data" mkdir venv_data
    "%PY_EXE%" -m pip install --target venv_data -r requirement.text
    "%PY_EXE%" -m pip install --target venv_data ncnn
:SKIP_INSTALL

:: 4. CẤU HÌNH FILE ._PTH (Dùng PowerShell để tránh lỗi dấu chấm của Batch)
echo [!] Dang cau hinh file he thong...
powershell -Command "$p = join-path '%PY_DIR%' 'python310._pth'; Set-Content $p 'python310.zip'; Add-Content $p '.'; Add-Content $p '..\venv_data'; Add-Content $p 'import site'"

:: 5. CHẠY ỨNG DỤNG
echo ---------------------------------------------------
echo    DANG KHOI DONG GIAO DIEN AI...
echo ---------------------------------------------------

:: Thiết lập đường dẫn tuyệt đối cho PYTHONPATH
set "BASE_DIR=%~dp0"
set "PYTHONPATH=%BASE_DIR%venv_data;%BASE_DIR%web_test"

:: Chạy App (Sử dụng đường dẫn tuyệt đối)
"%BASE_DIR%%PY_EXE%" "%BASE_DIR%web_test\app.py"

if %errorlevel% neq 0 (
    echo.
    echo [LOI] App dung lai. Co the do thieu thu vien hoac loi code.
    pause
)