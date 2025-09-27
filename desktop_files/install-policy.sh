#!/bin/bash
# Install PolicyKit policy for RW Local Tunnel

POLICY_FILE="com.rwlocaltunnel.policy"
POLICY_DIR="/usr/share/polkit-1/actions"

if [ ! -f "$POLICY_FILE" ]; then
    echo "Error: Policy file $POLICY_FILE not found"
    exit 1
fi

echo "Installing PolicyKit policy..."
sudo cp "$POLICY_FILE" "$POLICY_DIR/"
echo "Policy installed successfully"

echo "Reloading PolicyKit..."
sudo systemctl reload polkit || echo "Note: Could not reload polkit service"

echo "PolicyKit policy installation complete!"
echo "You can now use the desktop launcher with improved GUI support."