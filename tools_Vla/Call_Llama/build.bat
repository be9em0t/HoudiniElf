@echo off
REM Build script for Ollama Chat (Windows)

echo ======================================
echo Ollama Chat - Build Script (Windows)
echo ======================================
echo.

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
)

REM Check if icon exists
if not exist "callama512.png" (
    echo WARNING: callama512.png not found. Building without icon.
    set ICON_ARG=
) else (
    set ICON_ARG=--icon=callama512.png
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "Ollama Chat.spec" del "Ollama Chat.spec"

REM Build the application
echo.
echo Building application...
pyinstaller ^
    --name="Ollama Chat" ^
    --windowed ^
    %ICON_ARG% ^
    --add-data="callama512.png;." ^
    --onefile ^
    --noconfirm ^
    call_lama.py

echo.
echo ======================================
echo Build complete!
echo ======================================
echo.
echo Application created: dist\Ollama Chat.exe
echo.
echo To run: dist\"Ollama Chat.exe"
echo To distribute: Share the "Ollama Chat.exe" file
echo.
echo NOTE: Settings will be saved in callama.ini next to the executable
echo ======================================
pause
