#!/usr/bin/env python3
"""
Debug script to test tunnel creation manually
"""

import sys
import importlib.util

# Import the tunnel manager
spec = importlib.util.spec_from_file_location("rw_local_tunnel", "rw-local-tunnel.py")
rw_local_tunnel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rw_local_tunnel)

TailscaleManager = rw_local_tunnel.TailscaleManager
FirewallManager = rw_local_tunnel.FirewallManager
TunnelConfig = rw_local_tunnel.TunnelConfig

def test_firewall_rules(port=8080):
    """Test firewall rule creation manually"""
    print(f"🧪 Testing firewall rule creation for port {port}")

    config = TunnelConfig()
    tailscale = TailscaleManager(config)
    firewall = FirewallManager(config)

    # Check requirements
    print("\n📋 Checking requirements:")
    print(f"  Tailscale installed: {tailscale.check_installation()}")
    print(f"  Tailscale running: {tailscale.is_running()}")
    print(f"  UFW active: {firewall.check_ufw_status()}")

    # Get Tailscale status
    status = tailscale.get_status()
    backend_state = status.get("BackendState", "Unknown")
    print(f"  Tailscale state: {backend_state}")

    # Get VPS IP
    vps_ip = tailscale.get_vps_ip()
    print(f"  VPS IP: {vps_ip}")

    if not vps_ip:
        print("❌ Cannot proceed without VPS IP")
        return False

    # Test UFW rule creation
    print(f"\n🔥 Testing UFW rule creation:")
    access_source = f"{vps_ip}/32"
    print(f"  Command would be: ufw allow from {access_source} to any port {port} proto tcp")

    # Actually create the rule
    success = firewall.add_ufw_rule(access_source, port)
    print(f"  UFW rule creation: {'✅ SUCCESS' if success else '❌ FAILED'}")

    if success:
        print(f"\n✅ Tunnel should now be active on port {port}")
        print(f"🌐 Test access from VPS: curl {vps_ip}:{port}")
        print(f"\n🧹 To clean up, run:")
        print(f"  sudo ufw status numbered")
        print(f"  sudo ufw delete [rule_number]")

    return success

def show_current_ufw_rules():
    """Show current UFW rules"""
    import subprocess

    print("\n📜 Current UFW rules:")
    try:
        result = subprocess.run(["ufw", "status", "numbered"],
                              capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error getting UFW status: {e}")

if __name__ == "__main__":
    import os

    if os.geteuid() != 0:
        print("❌ This script requires root privileges")
        print("Run with: sudo python debug_tunnel.py")
        sys.exit(1)

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    show_current_ufw_rules()
    success = test_firewall_rules(port)

    if success:
        show_current_ufw_rules()

        # Test if we can see the rule
        print(f"\n🔍 Testing if port {port} is now accessible...")
        print(f"Start a test service: python -m http.server {port} --bind 0.0.0.0")
        print(f"Then test from VPS: curl localhost:{port}")