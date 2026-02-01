@echo off
REM Launch ComfyUI using the repository virtual environment and open the UI in the default browser
SETLOCAL

set "VENV_PATH=E:\Work\_AI_external_\ComfyUI\.venv"

rem Check that the venv activation script exists
if not exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Virtual environment not found at "%VENV_PATH%".
    echo Please create it first or update the VENV_PATH variable in this script.
    pause
    exit /b 1
)

rem Start ComfyUI in a new window while ensuring the venv is activated there
start "ComfyUI" cmd /k "call "%VENV_PATH%\Scripts\activate.bat" && "%VENV_PATH%\Scripts\python.exe" "%~dp0\ComfyUI\main.py" --enable-manager"

rem Allow a short delay for the server to start, then open the UI in the default browser
timeout /t 8 /nobreak >nul
start "" "http://127.0.0.1:8188"

ENDLOCAL
exit /b 0
