@echo off
setlocal EnableDelayedExpansion

:: Script configuration
set AppName=Workspace File Indexer
set Version=1.0.0
set Author=VIBE
set BuildDir=build
set DistDir=dist

echo === %AppName% - Windows Build Script v%Version% ===
echo Author: %Author%
echo.

:: Parse parameters
set Clean=0
set Debug=0

:parse_args
if /i "%~1"=="-clean" set Clean=1 & shift & goto parse_args
if /i "%~1"=="--clean" set Clean=1 & shift & goto parse_args
if /i "%~1"=="-debug" set Debug=1 & shift & goto parse_args
if /i "%~1"=="--debug" set Debug=1 & shift & goto parse_args
if not "%~1"=="" shift & goto parse_args

:: Check PyInstaller
pyinstaller --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] PyInstaller not found. Please install it first:
    echo   pip install pyinstaller^>=6.0.0
    exit /b 1
) else (
    for /f "tokens=*" %%i in ('pyinstaller --version') do set PyInstallerVer=%%i
    echo [OK] PyInstaller found: !PyInstallerVer!
)

:: Check Python environment
echo Checking Python environment...
python -c "import sys; print('Python ' + sys.version.split()[0])"
if !errorlevel! neq 0 goto missing_modules

python -c "import PySide6; print('[OK] PySide6 ' + PySide6.__version__)"
if !errorlevel! neq 0 goto missing_modules

python -c "import watchdog; print('[OK] watchdog available')"
if !errorlevel! neq 0 goto missing_modules

python -c "import send2trash; print('[OK] send2trash available')"
if !errorlevel! neq 0 goto missing_modules

python -c "import click; print('[OK] click available')"
if !errorlevel! neq 0 goto missing_modules

goto env_ok

:missing_modules
echo [ERROR] Required Python modules not available. Please install them first:
echo   pip install -r requirements.txt
exit /b 1

:env_ok

:: Clean previous builds if requested
if %Clean%==1 (
    echo Cleaning previous builds...
    if exist "%BuildDir%" rmdir /s /q "%BuildDir%"
    if exist "%DistDir%" rmdir /s /q "%DistDir%"
    echo [OK] Cleaned build directories
)

:: Create output directories
if not exist "%DistDir%" mkdir "%DistDir%"

:: Common PyInstaller options
set CommonArgs=--clean --distpath "%DistDir%" --workpath "%BuildDir%"

:: In release mode (-Debug not passed), use onefile.
if %Debug%==0 (
    set GuiCommonArgs=%CommonArgs% --noconsole --onefile
    set CliCommonArgs=%CommonArgs% --onefile
) else (
    set GuiCommonArgs=%CommonArgs%
    set CliCommonArgs=%CommonArgs%
)

:: Build GUI Application
echo.
echo Building GUI Application...
set GuiArgs=%GuiCommonArgs% --name "WorkspaceIndexer-GUI" --windowed --add-data "core;core" --add-data "gui;gui" --hidden-import "PySide6.QtCore" --hidden-import "PySide6.QtGui" --hidden-import "PySide6.QtWidgets" --hidden-import "watchdog.observers" --hidden-import "watchdog.events" --hidden-import "send2trash"

if exist "gui\icon.ico" (
    set GuiArgs=!GuiArgs! --icon "gui\icon.ico"
) else (
    echo [WARNING] No icon file found, continuing without icon...
)

set GuiArgs=!GuiArgs! launch_gui.py

call pyinstaller !GuiArgs!
if !errorlevel! equ 0 (
    echo [OK] GUI application built successfully
) else (
    echo [ERROR] Failed to build GUI application
    exit /b 1
)

:: Build CLI Application
echo.
echo Building CLI Application...
set CliArgs=%CliCommonArgs% --name "WorkspaceIndexer-CLI" --console --add-data "core;core" --hidden-import "watchdog.observers" --hidden-import "watchdog.events" --hidden-import "send2trash" --hidden-import "click" cli\main.py

call pyinstaller !CliArgs!
if !errorlevel! equ 0 (
    echo [OK] CLI application built successfully
) else (
    echo [ERROR] Failed to build CLI application
    exit /b 1
)

:: Display build results
echo.
echo === Build Complete ===
echo Output directory: %DistDir%

if exist "%DistDir%\WorkspaceIndexer-GUI.exe" (
    for %%I in ("%DistDir%\WorkspaceIndexer-GUI.exe") do (
        set /a sizeMB=%%~zI / 1048576
        if !sizeMB! equ 0 set sizeMB=1
        echo [OK] GUI: WorkspaceIndexer-GUI.exe ^(!sizeMB! MB^)
    )
)

if exist "%DistDir%\WorkspaceIndexer-CLI.exe" (
    for %%I in ("%DistDir%\WorkspaceIndexer-CLI.exe") do (
        set /a sizeMB=%%~zI / 1048576
        if !sizeMB! equ 0 set sizeMB=1
        echo [OK] CLI: WorkspaceIndexer-CLI.exe ^(!sizeMB! MB^)
    )
)

:: Test the built executables
echo.
echo Testing built executables...

if exist "%DistDir%\WorkspaceIndexer-CLI.exe" (
    "%DistDir%\WorkspaceIndexer-CLI.exe" --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=*" %%i in ('"%DistDir%\WorkspaceIndexer-CLI.exe" --version') do set CliTest=%%i
        echo [OK] CLI executable working: !CliTest!
    ) else (
        echo [ERROR] CLI executable test failed
    )
) else (
    echo [ERROR] CLI executable not found
)

if exist "%DistDir%\WorkspaceIndexer-GUI.exe" (
    echo [OK] GUI executable created ^(manual testing required^)
) else (
    echo [ERROR] GUI executable not found
)

echo.
echo Build script completed!
echo To test the applications manually:
echo   - GUI: .\%DistDir%\WorkspaceIndexer-GUI.exe
echo   - CLI: .\%DistDir%\WorkspaceIndexer-CLI.exe --help
