@echo off
REM Build script for transkript executable
REM Usage: build.bat

echo === Building transkript executable ===

REM Install dev dependencies
echo Installing dependencies...
uv sync --group dev

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build with PyInstaller
echo Building executable...
uv run pyinstaller transkript.spec --clean --noconfirm

echo.
echo === Build complete ===
echo Executable location: dist\transkript\transkript.exe
echo.
echo To distribute:
echo   1. Zip the dist\transkript\ folder
echo   2. Users extract and run transkript.exe
echo.
pause
