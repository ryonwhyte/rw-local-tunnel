#!/bin/bash
# Installation script for RW Local Tunnel

echo "🔧 Installing RW Local Tunnel..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please run this script as a regular user, not as root"
    exit 1
fi

# Set paths
INSTALL_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
POLICY_DIR="/usr/share/polkit-1/actions"
ICON_DIR="/usr/share/pixmaps"

# Install executable
echo "📦 Installing executable..."
sudo cp dist/RWLocalTunnel "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/RWLocalTunnel"

# Install icon
echo "🎨 Installing icon..."
sudo cp icons/rw-local-tunnel.png "$ICON_DIR/"

# Install PolicyKit policy
echo "🔐 Installing PolicyKit policy..."
sudo cp desktop_files/com.rwlocaltunnel.policy "$POLICY_DIR/"

# Update policy path in PolicyKit file
sudo sed -i "s|/home/[^/]*/Documents/GitHub/rw-local-tunnel/dist/RWLocalTunnel|$INSTALL_DIR/RWLocalTunnel|g" "$POLICY_DIR/com.rwlocaltunnel.policy"

# Install desktop launcher
echo "🖥️ Installing desktop launcher..."
sudo cp desktop_files/rw-tunnel-launcher.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/rw-tunnel-launcher.sh

# Update launcher script path
sudo sed -i "s|EXECUTABLE=.*|EXECUTABLE=\"$INSTALL_DIR/RWLocalTunnel\"|" /usr/local/bin/rw-tunnel-launcher.sh

# Install desktop file
cat > /tmp/RWLocalTunnel.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=RW Local Tunnel
Comment=Tailscale tunnel manager for NPM setups
Exec=/usr/local/bin/rw-tunnel-launcher.sh
Icon=/usr/share/pixmaps/rw-local-tunnel.png
Terminal=false
Categories=Network;System;
Keywords=tailscale;tunnel;npm;networking;
StartupNotify=true
StartupWMClass=RWLocalTunnel
EOF

sudo cp /tmp/RWLocalTunnel.desktop "$DESKTOP_DIR/"
sudo chmod 644 "$DESKTOP_DIR/RWLocalTunnel.desktop"
rm /tmp/RWLocalTunnel.desktop

# Reload PolicyKit
echo "🔄 Reloading PolicyKit..."
sudo systemctl reload polkit 2>/dev/null || echo "Note: Could not reload polkit service"

# Update desktop database
echo "🔄 Updating desktop database..."
sudo update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 You can now launch RW Local Tunnel from:"
echo "   • Applications menu"
echo "   • Command: rw-tunnel-launcher.sh"
echo "   • Terminal: sudo RWLocalTunnel"
echo ""
echo "🔧 To uninstall, run: sudo rm -f $INSTALL_DIR/RWLocalTunnel $DESKTOP_DIR/RWLocalTunnel.desktop $POLICY_DIR/com.rwlocaltunnel.policy $ICON_DIR/rw-local-tunnel.png /usr/local/bin/rw-tunnel-launcher.sh"