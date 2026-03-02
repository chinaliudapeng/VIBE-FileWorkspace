#!/bin/bash
# Workspace File Indexer - macOS Build Script
# Creates standalone executables and .app bundle using PyInstaller

set -e  # Exit on any error

# Script configuration
APP_NAME="Workspace File Indexer"
VERSION="1.0.0"
AUTHOR="VIBE"
BUILD_DIR="build"
DIST_DIR="dist"
CLEAN=false
DEBUG=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--clean] [--debug] [--help]"
            echo "  --clean  Clean previous builds"
            echo "  --debug  Build with debugging info and console"
            echo "  --help   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== $APP_NAME - macOS Build Script v$VERSION ===${NC}"
echo -e "${GREEN}Author: $AUTHOR${NC}"
echo ""

# Check if PyInstaller is available
echo -e "${BLUE}Checking PyInstaller...${NC}"
if command -v pyinstaller >/dev/null 2>&1; then
    pyinstaller_version=$(pyinstaller --version)
    echo -e "${GREEN}✓ PyInstaller found: $pyinstaller_version${NC}"
else
    echo -e "${RED}✗ PyInstaller not found. Please install it first:${NC}"
    echo -e "${YELLOW}  pip install pyinstaller>=6.0.0${NC}"
    exit 1
fi

# Check if Python and required modules are available
echo -e "${BLUE}Checking Python environment...${NC}"
if ! python3 -c "import sys; print(f'Python {sys.version}')" 2>/dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi

# Check required modules
for module in PySide6 watchdog send2trash click; do
    if python3 -c "import $module" 2>/dev/null; then
        echo -e "${GREEN}✓ $module available${NC}"
    else
        echo -e "${RED}✗ $module not available. Please install requirements:${NC}"
        echo -e "${YELLOW}  pip install -r requirements.txt${NC}"
        exit 1
    fi
done

# Clean previous builds if requested
if [ "$CLEAN" = true ]; then
    echo -e "${BLUE}Cleaning previous builds...${NC}"
    rm -rf "$BUILD_DIR" "$DIST_DIR"
    echo -e "${GREEN}✓ Cleaned build directories${NC}"
fi

# Create output directories
mkdir -p "$DIST_DIR"

# Common PyInstaller options
COMMON_ARGS=(
    "--clean"
    "--distpath" "$DIST_DIR"
    "--workpath" "$BUILD_DIR"
)

if [ "$DEBUG" = false ]; then
    COMMON_ARGS+=("--windowed")
    COMMON_ARGS+=("--onefile")
fi

# Build GUI Application
echo ""
echo -e "${BLUE}Building GUI Application...${NC}"

GUI_ARGS=(
    "${COMMON_ARGS[@]}"
    "--name" "WorkspaceIndexer-GUI"
    "--osx-bundle-identifier" "com.vibe.workspaceindexer"
    "--windowed"
    "--add-data" "core:core"
    "--add-data" "gui:gui"
    "--hidden-import" "PySide6.QtCore"
    "--hidden-import" "PySide6.QtGui"
    "--hidden-import" "PySide6.QtWidgets"
    "--hidden-import" "watchdog.observers"
    "--hidden-import" "watchdog.events"
    "--hidden-import" "send2trash"
    "launch_gui.py"
)

# Add icon if available
if [ -f "gui/icon.icns" ]; then
    GUI_ARGS+=("--icon" "gui/icon.icns")
elif [ -f "gui/icon.png" ]; then
    echo -e "${YELLOW}⚠ Found PNG icon but ICNS preferred for macOS${NC}"
    GUI_ARGS+=("--icon" "gui/icon.png")
else
    echo -e "${YELLOW}⚠ No icon file found, continuing without icon...${NC}"
fi

if pyinstaller "${GUI_ARGS[@]}"; then
    echo -e "${GREEN}✓ GUI application built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build GUI application${NC}"
    exit 1
fi

# Build CLI Application
echo ""
echo -e "${BLUE}Building CLI Application...${NC}"

CLI_ARGS=(
    "${COMMON_ARGS[@]}"
    "--name" "WorkspaceIndexer-CLI"
    "--console"
    "--onefile"
    "--add-data" "core:core"
    "--hidden-import" "watchdog.observers"
    "--hidden-import" "watchdog.events"
    "--hidden-import" "send2trash"
    "--hidden-import" "click"
    "cli/main.py"
)

if pyinstaller "${CLI_ARGS[@]}"; then
    echo -e "${GREEN}✓ CLI application built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build CLI application${NC}"
    exit 1
fi

# Display build results
echo ""
echo -e "${GREEN}=== Build Complete ===${NC}"
echo -e "${BLUE}Output directory: $DIST_DIR${NC}"

if [ -f "$DIST_DIR/WorkspaceIndexer-GUI.app/Contents/MacOS/WorkspaceIndexer-GUI" ] || [ -f "$DIST_DIR/WorkspaceIndexer-GUI" ]; then
    if [ -d "$DIST_DIR/WorkspaceIndexer-GUI.app" ]; then
        gui_size=$(du -sh "$DIST_DIR/WorkspaceIndexer-GUI.app" | cut -f1)
        echo -e "${GREEN}✓ GUI: WorkspaceIndexer-GUI.app ($gui_size)${NC}"
    else
        gui_size=$(du -sh "$DIST_DIR/WorkspaceIndexer-GUI" | cut -f1)
        echo -e "${GREEN}✓ GUI: WorkspaceIndexer-GUI ($gui_size)${NC}"
    fi
fi

if [ -f "$DIST_DIR/WorkspaceIndexer-CLI" ]; then
    cli_size=$(du -sh "$DIST_DIR/WorkspaceIndexer-CLI" | cut -f1)
    echo -e "${GREEN}✓ CLI: WorkspaceIndexer-CLI ($cli_size)${NC}"
fi

# Test the built executables
echo ""
echo -e "${BLUE}Testing built executables...${NC}"

# Test CLI
if [ -f "$DIST_DIR/WorkspaceIndexer-CLI" ]; then
    if cli_test=$("$DIST_DIR/WorkspaceIndexer-CLI" --version 2>&1); then
        echo -e "${GREEN}✓ CLI executable working: $cli_test${NC}"
    else
        echo -e "${RED}✗ CLI executable test failed${NC}"
    fi
else
    echo -e "${RED}✗ CLI executable not found${NC}"
fi

# Note about GUI testing
if [ -d "$DIST_DIR/WorkspaceIndexer-GUI.app" ]; then
    echo -e "${GREEN}✓ GUI app bundle created (manual testing required)${NC}"
    # Create a symlink for easier access
    ln -sf "WorkspaceIndexer-GUI.app/Contents/MacOS/WorkspaceIndexer-GUI" "$DIST_DIR/WorkspaceIndexer-GUI-direct"
    echo -e "${BLUE}  Created direct executable link: $DIST_DIR/WorkspaceIndexer-GUI-direct${NC}"
elif [ -f "$DIST_DIR/WorkspaceIndexer-GUI" ]; then
    echo -e "${GREEN}✓ GUI executable created (manual testing required)${NC}"
else
    echo -e "${RED}✗ GUI executable not found${NC}"
fi

# Create convenient launcher scripts
echo ""
echo -e "${BLUE}Creating launcher scripts...${NC}"

# GUI launcher script
cat > "$DIST_DIR/launch-gui.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -d "WorkspaceIndexer-GUI.app" ]; then
    open "WorkspaceIndexer-GUI.app"
elif [ -f "WorkspaceIndexer-GUI" ]; then
    ./WorkspaceIndexer-GUI
else
    echo "GUI executable not found"
    exit 1
fi
EOF

chmod +x "$DIST_DIR/launch-gui.sh"
echo -e "${GREEN}✓ Created launch-gui.sh${NC}"

# CLI launcher script
if [ -f "$DIST_DIR/WorkspaceIndexer-CLI" ]; then
    cat > "$DIST_DIR/launch-cli.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./WorkspaceIndexer-CLI "$@"
EOF
    chmod +x "$DIST_DIR/launch-cli.sh"
    echo -e "${GREEN}✓ Created launch-cli.sh${NC}"
fi

echo ""
echo -e "${GREEN}Build script completed!${NC}"
echo -e "${BLUE}To test the applications manually:${NC}"
if [ -d "$DIST_DIR/WorkspaceIndexer-GUI.app" ]; then
    echo -e "${BLUE}  - GUI: open $DIST_DIR/WorkspaceIndexer-GUI.app${NC}"
    echo -e "${BLUE}  - GUI (direct): $DIST_DIR/WorkspaceIndexer-GUI-direct${NC}"
    echo -e "${BLUE}  - GUI (script): $DIST_DIR/launch-gui.sh${NC}"
else
    echo -e "${BLUE}  - GUI: $DIST_DIR/WorkspaceIndexer-GUI${NC}"
fi
if [ -f "$DIST_DIR/WorkspaceIndexer-CLI" ]; then
    echo -e "${BLUE}  - CLI: $DIST_DIR/WorkspaceIndexer-CLI --help${NC}"
    echo -e "${BLUE}  - CLI (script): $DIST_DIR/launch-cli.sh --help${NC}"
fi

# Make the script executable on creation
chmod +x "$0"