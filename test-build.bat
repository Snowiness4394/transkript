@echo off
REM test-build.bat — Verify that all dependencies and imports are ready for PyInstaller
REM Run this before building to catch issues early

setlocal enabledelayedexpansion
set ERRORS=0

echo === transkript — PyInstaller Readiness Check ===
echo.

REM 1. Check Python
echo --- Python ---
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo PASS — %%i
) else (
    echo FAIL — Python not found
    set /a ERRORS+=1
)

REM 2. Check uv
echo.
echo --- uv ---
uv --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('uv --version 2^>^&1') do echo PASS — uv %%i
) else (
    echo FAIL — uv not found
    set /a ERRORS+=1
)

REM 3. Install dependencies
echo.
echo --- Dependencies ---
call uv sync --group dev
echo PASS — Dependencies installed

REM 4. Check PyInstaller
echo.
echo --- PyInstaller ---
uv run pyinstaller --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('uv run pyinstaller --version 2^>^&1') do echo PASS — PyInstaller %%i
) else (
    echo FAIL — PyInstaller not found
    set /a ERRORS+=1
)

REM 5. Test imports
echo.
echo --- Import checks ---
for %%m in (transkript transkript.app transkript.audio transkript.transcriber textual textual.app textual.widgets textual.containers sounddevice faster_whisper numpy) do (
    uv run python -c "import %%m" >nul 2>&1
    if !errorlevel! equ 0 (
        echo PASS — import %%m
    ) else (
        echo FAIL — import %%m
        set /a ERRORS+=1
    )
)

REM 6. Test app instantiation
echo.
echo --- App instantiation ---
uv run python -c "from transkript.app import TranskriptApp; app = TranskriptApp(); print(f'PASS — TranskriptApp created (title: {app.TITLE})')" >nul 2>&1
if %errorlevel% neq 0 (
    echo FAIL — Could not create TranskriptApp
    set /a ERRORS+=1
)

REM 7. Check build files
echo.
echo --- Build files ---
if exist transkript.spec (
    echo PASS — transkript.spec exists
) else (
    echo FAIL — transkript.spec missing
    set /a ERRORS+=1
)
if exist build.bat (
    echo PASS — build.bat exists
) else (
    echo FAIL — build.bat missing
    set /a ERRORS+=1
)

REM 8. Check CSS
echo.
echo --- Assets ---
if exist src\transkript\styles\app.tcss (
    echo PASS — styles\app.tcss exists
) else (
    echo FAIL — styles\app.tcss missing
    set /a ERRORS+=1
)

REM Summary
echo.
echo === Summary ===
if %ERRORS% equ 0 (
    echo All checks passed! Ready to build exe.
    echo.
    echo Run: build.bat
) else (
    echo %ERRORS% check^(s^) failed. Fix issues before building.
)

endlocal
pause
