# Workspace File Indexer - Windows Build Script
# Creates standalone executables using PyInstaller

param(
    [switch]$Clean = $false,
    [switch]$Debug = $false
)

# Script configuration
$AppName = "Workspace File Indexer"
$Version = "1.0.0"
$Author = "VIBE"
$BuildDir = "build"
$DistDir = "dist"

Write-Host "=== $AppName - Windows Build Script v$Version ===" -ForegroundColor Green
Write-Host "Author: $Author" -ForegroundColor Green
Write-Host ""

# Check if PyInstaller is available
try {
    $pyinstallerVersion = & pyinstaller --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller not found"
    }
    Write-Host "✓ PyInstaller found: $pyinstallerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ PyInstaller not found. Please install it first:" -ForegroundColor Red
    Write-Host "  pip install pyinstaller>=6.0.0" -ForegroundColor Yellow
    exit 1
}

# Check if Python and required modules are available
Write-Host "Checking Python environment..." -ForegroundColor Blue
try {
    & python -c "import sys; print(f'Python {sys.version}')" | Out-Host
    & python -c "import PySide6; print(f'✓ PySide6 {PySide6.__version__}')" | Out-Host
    & python -c "import watchdog; print(f'✓ watchdog available')" | Out-Host
    & python -c "import send2trash; print(f'✓ send2trash available')" | Out-Host
    & python -c "import click; print(f'✓ click available')" | Out-Host
} catch {
    Write-Host "✗ Required Python modules not available. Please install them first:" -ForegroundColor Red
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Clean previous builds if requested
if ($Clean) {
    Write-Host "Cleaning previous builds..." -ForegroundColor Blue
    Remove-Item -Path $BuildDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $DistDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "✓ Cleaned build directories" -ForegroundColor Green
}

# Create output directories
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

# Common PyInstaller options
$CommonArgs = @(
    "--clean"
    "--distpath", $DistDir
    "--workpath", $BuildDir
)

if (-not $Debug) {
    $CommonArgs += "--noconsole"
    $CommonArgs += "--onefile"
}

# Build GUI Application
Write-Host ""
Write-Host "Building GUI Application..." -ForegroundColor Blue
$GuiArgs = $CommonArgs + @(
    "--name", "WorkspaceIndexer-GUI"
    "--icon", "gui\icon.ico"
    "--windowed"
    "--add-data", "core;core"
    "--add-data", "gui;gui"
    "--hidden-import", "PySide6.QtCore"
    "--hidden-import", "PySide6.QtGui"
    "--hidden-import", "PySide6.QtWidgets"
    "--hidden-import", "watchdog.observers"
    "--hidden-import", "watchdog.events"
    "--hidden-import", "send2trash"
    "launch_gui.py"
)

# Create dummy icon if it doesn't exist
if (-not (Test-Path "gui\icon.ico")) {
    Write-Host "⚠ No icon file found, continuing without icon..." -ForegroundColor Yellow
    $GuiArgs = $GuiArgs | Where-Object { $_ -ne "--icon" -and $_ -ne "gui\icon.ico" }
}

try {
    & pyinstaller @GuiArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ GUI application built successfully" -ForegroundColor Green
    } else {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "✗ Failed to build GUI application: $_" -ForegroundColor Red
    exit 1
}

# Build CLI Application
Write-Host ""
Write-Host "Building CLI Application..." -ForegroundColor Blue
$CliArgs = $CommonArgs + @(
    "--name", "WorkspaceIndexer-CLI"
    "--console"
    "--onefile"
    "--add-data", "core;core"
    "--hidden-import", "watchdog.observers"
    "--hidden-import", "watchdog.events"
    "--hidden-import", "send2trash"
    "--hidden-import", "click"
    "cli\main.py"
)

try {
    & pyinstaller @CliArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ CLI application built successfully" -ForegroundColor Green
    } else {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "✗ Failed to build CLI application: $_" -ForegroundColor Red
    exit 1
}

# Display build results
Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Green
Write-Host "Output directory: $DistDir" -ForegroundColor Blue

if (Test-Path "$DistDir\WorkspaceIndexer-GUI.exe") {
    $GuiSize = [math]::Round((Get-Item "$DistDir\WorkspaceIndexer-GUI.exe").Length / 1MB, 1)
    Write-Host "✓ GUI: WorkspaceIndexer-GUI.exe ($GuiSize MB)" -ForegroundColor Green
}

if (Test-Path "$DistDir\WorkspaceIndexer-CLI.exe") {
    $CliSize = [math]::Round((Get-Item "$DistDir\WorkspaceIndexer-CLI.exe").Length / 1MB, 1)
    Write-Host "✓ CLI: WorkspaceIndexer-CLI.exe ($CliSize MB)" -ForegroundColor Green
}

# Test the built executables
Write-Host ""
Write-Host "Testing built executables..." -ForegroundColor Blue

# Test CLI
if (Test-Path "$DistDir\WorkspaceIndexer-CLI.exe") {
    try {
        $CliTest = & "$DistDir\WorkspaceIndexer-CLI.exe" --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ CLI executable working: $CliTest" -ForegroundColor Green
        } else {
            Write-Host "✗ CLI executable test failed" -ForegroundColor Red
        }
    } catch {
        Write-Host "✗ CLI executable test error: $_" -ForegroundColor Red
    }
} else {
    Write-Host "✗ CLI executable not found" -ForegroundColor Red
}

# Note about GUI testing
if (Test-Path "$DistDir\WorkspaceIndexer-GUI.exe") {
    Write-Host "✓ GUI executable created (manual testing required)" -ForegroundColor Green
} else {
    Write-Host "✗ GUI executable not found" -ForegroundColor Red
}

Write-Host ""
Write-Host "Build script completed!" -ForegroundColor Green
Write-Host "To test the applications manually:" -ForegroundColor Blue
Write-Host "  - GUI: .\$DistDir\WorkspaceIndexer-GUI.exe" -ForegroundColor Blue
Write-Host "  - CLI: .\$DistDir\WorkspaceIndexer-CLI.exe --help" -ForegroundColor Blue