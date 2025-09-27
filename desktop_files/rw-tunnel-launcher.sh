#!/bin/bash
# Launcher script for RW Local Tunnel GUI
# Handles proper environment setup for GUI with root privileges

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set the executable path
EXECUTABLE="$SCRIPT_DIR/dist/RWLocalTunnel"

# Check if executable exists
if [ ! -f "$EXECUTABLE" ]; then
    zenity --error --text="RWLocalTunnel executable not found at:\n$EXECUTABLE" 2>/dev/null || \
    notify-send "Error" "RWLocalTunnel executable not found" || \
    echo "Error: Executable not found at $EXECUTABLE"
    exit 1
fi

# Method 1: Try with PolicyKit action
if pkexec --action-id com.rwlocaltunnel.run "$EXECUTABLE" 2>/dev/null; then
    exit 0
fi

# Method 2: Fallback to preserving environment manually
exec pkexec env DISPLAY="$DISPLAY" \
              XAUTHORITY="$XAUTHORITY" \
              HOME="$HOME" \
              USER="$USER" \
              LANG="$LANG" \
              PATH="$PATH" \
              XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
              WAYLAND_DISPLAY="$WAYLAND_DISPLAY" \
              "$EXECUTABLE"