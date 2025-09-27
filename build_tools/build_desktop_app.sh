#!/bin/bash

# Complete build script for desktop GUI application
# Creates a double-clickable desktop application

set -e

echo "🖥️  Building Desktop GUI Application..."

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Install PyInstaller if needed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Clean previous builds
echo -e "${BLUE}Cleaning previous builds...${NC}"
rm -rf build/ dist/

# Build the GUI application
echo -e "${BLUE}Building GUI executable...${NC}"

pyinstaller \
    --onefile \
    --windowed \
    --name "RWLocalTunnel" \
    --icon "rw-local-tunnel.ico" \
    --add-data "README.md:." \
    --add-data "LICENSE:." \
    --add-data "rw-local-tunnel.png:." \
    --hidden-import customtkinter \
    --hidden-import PIL._tkinter_finder \
    --hidden-import psutil._psutil_linux \
    --hidden-import psutil._psutil_posix \
    --hidden-import pystray \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --clean \
    rw_tunnel_gui.py

# Check if build succeeded
if [ -f "dist/RWLocalTunnel" ]; then
    echo -e "\n${GREEN}✅ Build successful!${NC}"

    # Make it executable
    chmod +x dist/RWLocalTunnel

    # Show info
    echo -e "\n${BLUE}📊 Application built:${NC}"
    ls -lh dist/RWLocalTunnel

    echo -e "\n${GREEN}🎯 Your desktop app is ready!${NC}"
    echo -e "\n${BLUE}To run it:${NC}"
    echo -e "1. Double-click: ${GREEN}dist/RWLocalTunnel${NC}"
    echo -e "2. Or from terminal: ${GREEN}sudo ./dist/RWLocalTunnel${NC}"

    echo -e "\n${BLUE}To install on desktop:${NC}"
    echo -e "• Copy to Applications: ${GREEN}sudo cp dist/RWLocalTunnel /usr/local/bin/${NC}"
    echo -e "• Add to menu: ${GREEN}./scripts/install-desktop.sh${NC}"

    # Create desktop file for double-click
    cat > dist/RWLocalTunnel.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=RW Local Tunnel
Comment=Tailscale tunnel manager
Exec=pkexec /usr/local/bin/RWLocalTunnel
Icon=network-server
Terminal=false
Categories=Network;System;
EOF

    chmod +x dist/RWLocalTunnel.desktop

    echo -e "\n${GREEN}💡 TIP: You can drag dist/RWLocalTunnel to your desktop or dock!${NC}"

else
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi