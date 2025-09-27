#!/usr/bin/env python3
"""
rw-local-tunnel GUI: Modern desktop application for managing Tailscale tunnels
"""

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import threading
import subprocess
import json
import psutil
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import os
import signal
from pathlib import Path

# Import our tunnel manager components
import sys
import os

# For standalone executable, include the tunnel manager code directly
if getattr(sys, 'frozen', False):
    # Running as compiled executable - define classes directly
    from dataclasses import dataclass, field
    from pathlib import Path
    import subprocess
    import json

    @dataclass
    class TunnelConfig:
        """Configuration for tunnel setup"""
        vps_name: str = os.getenv("VPS_NAME", "vpn")
        tailnet_cidr: str = os.getenv("TAILNET_CIDR", "100.64.0.0/10")
        default_scope: str = os.getenv("DEFAULT_SCOPE", "vps")
        state_dir: Path = Path.home() / ".config" / "rw-local-tunnel"
        nft_family: str = "inet"
        nft_table: str = "rwlt"
        nft_chain: str = "input"
        nft_priority: str = "-450"

    class TailscaleManager:
        """Manages Tailscale operations"""

        def __init__(self, config: TunnelConfig):
            self.config = config

        def check_installation(self) -> bool:
            """Check if Tailscale is installed"""
            try:
                subprocess.run(["tailscale", "--version"],
                              capture_output=True, check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

        def get_status(self) -> Dict:
            """Get Tailscale status as JSON"""
            try:
                result = subprocess.run(
                    ["tailscale", "status", "--json"],
                    capture_output=True, text=True, check=True
                )
                return json.loads(result.stdout)
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                return {}

        def is_running(self) -> bool:
            """Check if Tailscale daemon is running"""
            return any(p.name() == "tailscaled" for p in psutil.process_iter())

        def start_daemon(self) -> bool:
            """Start Tailscale daemon"""
            try:
                subprocess.run(["systemctl", "start", "tailscaled"],
                              check=True, capture_output=True)
                time.sleep(2)
                return True
            except subprocess.CalledProcessError:
                return False

        def authenticate(self) -> bool:
            """Authenticate with Tailscale"""
            try:
                subprocess.run(["tailscale", "up"], check=True)
                return True
            except subprocess.CalledProcessError:
                return False

        def get_vps_ip(self) -> Optional[str]:
            """Get VPS IP from Tailscale status"""
            status = self.get_status()
            peers = status.get("Peer", {})

            for peer in peers.values():
                if peer.get("HostName") == self.config.vps_name:
                    # Get first IPv4 address
                    for ip in peer.get("TailscaleIPs", []):
                        if ":" not in ip:  # IPv4
                            return ip
            return None

    class FirewallManager:
        """Manages UFW and nftables firewall rules"""

        def __init__(self, config: TunnelConfig):
            self.config = config

        def check_ufw_status(self) -> bool:
            """Check if UFW is active"""
            try:
                result = subprocess.run(
                    ["ufw", "status"],
                    capture_output=True, text=True, check=True
                )
                return "Status: active" in result.stdout
            except subprocess.CalledProcessError:
                return False

        def enable_ufw(self) -> bool:
            """Enable UFW firewall"""
            try:
                subprocess.run(["ufw", "--force", "enable"],
                              check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                return False

        def add_ufw_rule(self, source: str, port: int) -> bool:
            """Add UFW allow rule"""
            try:
                cmd = [
                    "ufw", "allow",
                    "from", source,
                    "to", "any",
                    "port", str(port),
                    "proto", "tcp",
                    "comment", f"rwlt:{port}"
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                # Try without comment
                try:
                    cmd_no_comment = cmd[:-2]
                    subprocess.run(cmd_no_comment, check=True, capture_output=True)
                    return True
                except subprocess.CalledProcessError:
                    return False

        def remove_ufw_rules(self, port: int) -> int:
            """Remove UFW rules for a port"""
            removed = 0
            try:
                result = subprocess.run(
                    ["ufw", "status", "numbered"],
                    capture_output=True, text=True, check=True
                )

                lines = result.stdout.split('\n')
                rule_numbers = []

                for line in lines:
                    if str(port) in line and "tcp" in line.lower():
                        if line.strip().startswith('['):
                            parts = line.strip().split(']', 1)
                            if len(parts) > 0:
                                num_part = parts[0].replace('[', '').strip()
                                if num_part.isdigit():
                                    rule_numbers.append(int(num_part))

                for rule_num in sorted(rule_numbers, reverse=True):
                    try:
                        subprocess.run(
                            ["ufw", "--force", "delete", str(rule_num)],
                            check=True, capture_output=True
                        )
                        removed += 1
                    except subprocess.CalledProcessError:
                        pass

            except subprocess.CalledProcessError:
                pass

            return removed

        def add_nft_drop_rule(self, port: int) -> bool:
            """Add nftables drop rule"""
            try:
                subprocess.run([
                    "nft", "add", "table", self.config.nft_family, self.config.nft_table
                ], capture_output=True)

                chain_cmd = [
                    "nft", "add", "chain", self.config.nft_family,
                    self.config.nft_table, self.config.nft_chain,
                    f'{{ type filter hook input priority {self.config.nft_priority}; policy accept; }}'
                ]
                subprocess.run(chain_cmd, capture_output=True)

                rule_cmd = [
                    "nft", "add", "rule", self.config.nft_family,
                    self.config.nft_table, self.config.nft_chain,
                    "iif", "tailscale0", "tcp", "dport", str(port), "counter", "drop"
                ]
                subprocess.run(rule_cmd, check=True, capture_output=True)
                return True

            except subprocess.CalledProcessError:
                return False

        def remove_nft_drop_rules(self, port: int) -> int:
            """Remove nftables drop rules for a port"""
            removed = 0
            try:
                result = subprocess.run([
                    "nft", "-a", "list", "chain",
                    self.config.nft_family, self.config.nft_table, self.config.nft_chain
                ], capture_output=True, text=True, check=True)

                for line in result.stdout.split('\n'):
                    if f'tcp dport {port}' in line and 'tailscale0' in line:
                        parts = line.strip().split()
                        if parts and parts[-1].isdigit():
                            handle = parts[-1]
                            try:
                                subprocess.run([
                                    "nft", "delete", "rule",
                                    self.config.nft_family, self.config.nft_table,
                                    self.config.nft_chain, "handle", handle
                                ], check=True, capture_output=True)
                                removed += 1
                            except subprocess.CalledProcessError:
                                pass

            except subprocess.CalledProcessError:
                pass

            return removed

else:
    # Running as Python script - import from file
    import importlib.util
    try:
        spec = importlib.util.spec_from_file_location("rw_local_tunnel", "rw-local-tunnel.py")
        rw_local_tunnel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rw_local_tunnel)
        TailscaleManager = rw_local_tunnel.TailscaleManager
        FirewallManager = rw_local_tunnel.FirewallManager
        TunnelConfig = rw_local_tunnel.TunnelConfig
    except Exception as e:
        print(f"Error importing tunnel manager: {e}")
        print("Make sure rw-local-tunnel.py is in the same directory")
        sys.exit(1)

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

@dataclass
class TunnelInfo:
    """Information about an active tunnel"""
    port: int
    vps_ip: str
    access_scope: str
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    listening: bool = False

class TunnelMonitor(threading.Thread):
    """Background thread for monitoring tunnel status"""

    def __init__(self, port: int, callback):
        super().__init__(daemon=True)
        self.port = port
        self.callback = callback
        self.running = True

    def run(self):
        while self.running:
            try:
                listening = self.check_port_status()
                self.callback(self.port, listening)
                time.sleep(2)
            except Exception as e:
                print(f"Monitor error for port {self.port}: {e}")

    def check_port_status(self) -> bool:
        """Check if port is listening"""
        listening = False

        try:
            for conn in psutil.net_connections():
                if hasattr(conn, 'laddr') and conn.laddr:
                    if hasattr(conn.laddr, 'port') and conn.laddr.port == self.port:
                        if conn.status == psutil.CONN_LISTEN:
                            listening = True
                            break
        except (psutil.AccessDenied, AttributeError):
            pass

        return listening

    def stop(self):
        self.running = False

class TunnelManagerGUI:
    """Main GUI application for tunnel management"""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("RW Local Tunnel Manager")
        self.root.geometry("1200x700")

        # Set window icon if possible
        try:
            if getattr(sys, 'frozen', False):
                # Running as executable - create icon from embedded data
                import tempfile
                import base64
                import io
                from PIL import Image

                # Embedded icon (small version for window)
                icon_b64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAA7AAAAOwBeShxvQAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAOPSURBVFiFtZdPbBtFFMZ/M7u2vXbsxEmcOHFCUkhJaQoFqVCQUA9VT1x64VhV4sIFJC5cuHHhAhLqCXHgxAEhIXEoBxAHWqGqFVRQRWkDaUlK/ifESWzHju31er2zw2EdO7bjNAR4T1rtm5n3fe+bb3ZnBP7HCIfD4VAoJAFvAYPAw3q1CPwE3NJkj2w2m3V3wxcKhaYlSfro0qVLP0qS1P3fygSwBbyRzWZvdFJQjh8/LgVPTSkPJibQdJ3d+gbyTqm+V6xUqNVVAGw2K249Hi62tTEyNoaUOEoikaCQy28MD7/cXywWf2wLcPr06XcmJyd/cPSJFDwCG6uc2t5lQNNwKEpLwaJ2vUJ3a6vMvTaM/vIgLlmupgcGfnv01ltftwC8MDZ2fX9gwKlJdhbLZcIb2/h2yni0Rv2WzBxF4fSGJWLVFi9PziFQJRzNrz9/5ow3PTX1B4AsRSKRg5K/j/V6A1xbW6M3k+WR8jZ2w3itIYHBEOCzxzxTXJQKVXgvxJRzCKO+hzWL5Wzpxo1c0xRUvD5KFIU3d3Y4XCqjCL03H8BgtUBZg5MnyJqPkGvzIASN9g6AJhVOHTqEzWJheHubRx4X8tFjLQBihzxnN/i89oAgBO3/JkXaKfLUqzPz8r1/lXhsFFlfJJ5OExs7TG42wUs9PdhsNjKpFPGjr9PTy2VfHa0LELc04nfrYQBRCMNxvb01fyEeb0kx9spdlFptL3cCEpz7/jPGQ9N7EgBRBMON5JzX6iA05EtXFgkPzLec/fI9OFUrMu/xNa0vSRK6vrdoCFD3GJ1k19S6Y5Z8/T2/5XIzACWxBgQCKLWmZBwAJrMJrDa86+tksjla8BXwySLfWZ3UdA1JQRQECARw9zLo+PVCBOaJZx+RLa/gUzSaQCg+P5qmUSmtEi8EZJvFhiAkCQRwOA4UzCYzFvP/vH3/i6pF56/1JJfdyT6KArMSJ3p3tqX/ggJYgCXD8R6wJEmrSYvdX1vNsFm/Zrn8F4X+QOu6VUG3CCjfT0I8z0H0qfekzWYzWq+fOAAECNf9Fxpnwgqoz0Wi3zBNgFAo9B2wDbQOQQdsA2EjzrRFJBL5QxCE9yzH+1GWM6tKJqOplY0q+SJD4N65c0kzOE3xESDaQaMAjBjxpGdHQxQfAnwGJ8DbBisgNi5GAIzCRUNxrCNnHjgKOA2xJuAnoNj9JOPa37k/ACt2/S5nfD9VAAAAAElFTkSuQmCC"

                icon_data = base64.b64decode(icon_b64)
                icon_img = Image.open(io.BytesIO(icon_data))

                # Save to temp and set as window icon
                temp_icon = os.path.join(tempfile.gettempdir(), "rw_icon.png")
                icon_img.save(temp_icon)
                self.root.iconbitmap(temp_icon)
                self.root.iconphoto(True, tk.PhotoImage(file=temp_icon))
            else:
                # Running as script - try to use local icon
                if os.path.exists("rw-local-tunnel.png"):
                    self.root.iconphoto(True, tk.PhotoImage(file="rw-local-tunnel.png"))
        except Exception:
            pass  # Icon is optional

        # Initialize tunnel management
        self.config = TunnelConfig()
        self.tailscale = TailscaleManager(self.config)
        self.firewall = FirewallManager(self.config)

        # Active tunnels tracking
        self.active_tunnels: Dict[int, TunnelInfo] = {}
        self.monitors: Dict[int, TunnelMonitor] = {}
        self.tunnel_frames: Dict[int, ctk.CTkFrame] = {}

        # VPS IP cache
        self.vps_ip = None

        # Setup UI
        self.setup_ui()

        # Check requirements on startup
        self.check_requirements()

        # Start status update loop
        self.update_status()

    def setup_ui(self):
        """Setup the main UI components"""

        # Main container
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Panel - Control Panel
        left_panel = ctk.CTkFrame(main_container, width=350)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)

        # Title
        title = ctk.CTkLabel(
            left_panel,
            text="🌐 Tunnel Control",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(pady=20)

        # Status Frame
        self.status_frame = ctk.CTkFrame(left_panel)
        self.status_frame.pack(fill="x", padx=20, pady=10)

        self.tailscale_status = ctk.CTkLabel(
            self.status_frame,
            text="⚫ Tailscale: Checking...",
            font=ctk.CTkFont(size=12)
        )
        self.tailscale_status.pack(anchor="w", padx=10, pady=5)

        self.vps_status = ctk.CTkLabel(
            self.status_frame,
            text="⚫ VPS: Not connected",
            font=ctk.CTkFont(size=12)
        )
        self.vps_status.pack(anchor="w", padx=10, pady=5)

        # New Tunnel Section
        new_tunnel_frame = ctk.CTkFrame(left_panel)
        new_tunnel_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            new_tunnel_frame,
            text="Create New Tunnel",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)

        # Port input
        port_frame = ctk.CTkFrame(new_tunnel_frame)
        port_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(port_frame, text="Port:").pack(side="left", padx=5)
        self.port_entry = ctk.CTkEntry(port_frame, width=100, placeholder_text="8080")
        self.port_entry.pack(side="left", padx=5)

        # Access scope
        scope_frame = ctk.CTkFrame(new_tunnel_frame)
        scope_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(scope_frame, text="Access:").pack(side="left", padx=5)
        self.scope_var = ctk.StringVar(value="vps")

        ctk.CTkRadioButton(
            scope_frame,
            text="VPS Only",
            variable=self.scope_var,
            value="vps"
        ).pack(side="left", padx=5)

        ctk.CTkRadioButton(
            scope_frame,
            text="Full Tailnet",
            variable=self.scope_var,
            value="tailnet"
        ).pack(side="left", padx=5)

        # Create button
        self.create_btn = ctk.CTkButton(
            new_tunnel_frame,
            text="➕ Create Tunnel",
            command=self.create_tunnel,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.create_btn.pack(pady=15)

        # Quick Actions
        actions_frame = ctk.CTkFrame(left_panel)
        actions_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            actions_frame,
            text="Quick Actions",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)

        ctk.CTkButton(
            actions_frame,
            text="🔄 Refresh Status",
            command=self.refresh_status,
            height=30
        ).pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            actions_frame,
            text="🛑 Stop All Tunnels",
            command=self.stop_all_tunnels,
            height=30,
            fg_color="red",
            hover_color="darkred"
        ).pack(fill="x", padx=10, pady=5)

        # Right Panel - Active Tunnels
        right_panel = ctk.CTkFrame(main_container)
        right_panel.pack(side="right", fill="both", expand=True)

        # Header
        header = ctk.CTkLabel(
            right_panel,
            text="📊 Active Tunnels",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.pack(pady=10)

        # Scrollable frame for tunnels
        self.tunnels_scroll = ctk.CTkScrollableFrame(right_panel)
        self.tunnels_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # Empty state
        self.empty_label = ctk.CTkLabel(
            self.tunnels_scroll,
            text="No active tunnels\nCreate one to get started!",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.empty_label.pack(pady=50)

    def check_requirements(self):
        """Check system requirements on startup"""
        def check():
            try:
                # Check Tailscale
                if self.tailscale.check_installation():
                    if self.tailscale.is_running():
                        status = self.tailscale.get_status()
                        backend_state = status.get("BackendState", "Unknown")
                        print(f"Tailscale backend state: {backend_state}")

                        if backend_state == "Running":
                            self.update_tailscale_status("connected")
                            # Get VPS IP
                            self.vps_ip = self.tailscale.get_vps_ip()
                            print(f"VPS IP found: {self.vps_ip}")
                            if self.vps_ip:
                                self.update_vps_status("connected", self.vps_ip)
                            else:
                                print("Warning: No VPS found with configured hostname")
                        else:
                            self.update_tailscale_status("not_authenticated")
                    else:
                        self.update_tailscale_status("not_running")
                else:
                    self.update_tailscale_status("not_installed")

                # Check UFW status
                ufw_active = self.firewall.check_ufw_status()
                print(f"UFW active: {ufw_active}")

                # Check root privileges
                import os
                has_root = os.geteuid() == 0
                print(f"Running as root: {has_root}")

            except Exception as e:
                print(f"Error checking requirements: {e}")

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def update_tailscale_status(self, status):
        """Update Tailscale status in UI"""
        status_map = {
            "connected": ("🟢", "Connected"),
            "not_authenticated": ("🟡", "Not authenticated"),
            "not_running": ("🔴", "Not running"),
            "not_installed": ("🔴", "Not installed")
        }
        icon, text = status_map.get(status, ("⚫", "Unknown"))
        self.tailscale_status.configure(text=f"{icon} Tailscale: {text}")

    def update_vps_status(self, status, ip=None):
        """Update VPS status in UI"""
        if status == "connected" and ip:
            self.vps_status.configure(text=f"🟢 VPS: {ip}")
        else:
            self.vps_status.configure(text="🔴 VPS: Not found")

    def create_tunnel(self):
        """Create a new tunnel"""
        try:
            port = int(self.port_entry.get())
            if port < 1 or port > 65535:
                raise ValueError("Port out of range")
        except ValueError:
            messagebox.showerror("Invalid Port", "Please enter a valid port (1-65535)")
            return

        if port in self.active_tunnels:
            messagebox.showwarning("Port In Use", f"Port {port} already has an active tunnel")
            return

        # Check VPS IP
        if not self.vps_ip:
            self.vps_ip = self.tailscale.get_vps_ip()
            if not self.vps_ip:
                messagebox.showerror("VPS Not Found", "Could not find VPS on Tailscale network")
                return

        # Create tunnel in background
        self.create_btn.configure(state="disabled", text="Creating...")
        thread = threading.Thread(target=self._create_tunnel_thread, args=(port,), daemon=True)
        thread.start()

    def _create_tunnel_thread(self, port):
        """Background thread for creating tunnel using full TunnelManager logic"""
        try:
            # Get access scope
            scope = self.scope_var.get()
            if scope == "vps":
                access_source = f"{self.vps_ip}/32"
            else:
                access_source = self.config.tailnet_cidr

            # Check UFW status first
            if not self.firewall.check_ufw_status():
                self.root.after(0, lambda: messagebox.showerror(
                    "UFW Not Active",
                    "UFW firewall is not active. Please enable UFW first."
                ))
                return

            # Remove any existing nft drop rules for this port
            removed = self.firewall.remove_nft_drop_rules(port)
            if removed:
                print(f"Removed {removed} existing nftables drop rules for port {port}")

            # Add UFW allow rule (this is the key step that creates the tunnel)
            print(f"Creating UFW rule: allow from {access_source} to any port {port}")
            success = self.firewall.add_ufw_rule(access_source, port)
            print(f"UFW rule creation result: {success}")

            if success:
                # Check if service is bound properly (same as CLI version)
                self.check_service_binding_gui(port)

                # Create tunnel info
                tunnel = TunnelInfo(
                    port=port,
                    vps_ip=self.vps_ip,
                    access_scope=scope
                )

                # Add to active tunnels
                self.active_tunnels[port] = tunnel

                # Start monitoring
                monitor = TunnelMonitor(port, self.update_tunnel_status)
                monitor.start()
                self.monitors[port] = monitor

                # Update UI
                self.root.after(0, self.add_tunnel_card, tunnel)
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success",
                    f"Tunnel created on port {port}!\n\n"
                    f"🌐 Access from VPS: {self.vps_ip}:{port}\n"
                    f"🔒 Scope: {scope.upper()}\n\n"
                    f"Make sure your service is running on 0.0.0.0:{port}"
                ))
            else:
                self.root.after(0, lambda: messagebox.showerror(
                    "Failed",
                    f"Failed to create UFW firewall rule for port {port}.\n"
                    f"Check that UFW is active and you have root privileges."
                ))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Tunnel creation failed: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.create_btn.configure(
                state="normal",
                text="➕ Create Tunnel"
            ))

    def check_service_binding_gui(self, port):
        """Check if service is properly bound (GUI version)"""
        bound_to_all = False
        try:
            for conn in psutil.net_connections():
                if hasattr(conn, 'laddr') and conn.laddr:
                    if hasattr(conn.laddr, 'port') and conn.laddr.port == port:
                        if conn.status == psutil.CONN_LISTEN:
                            if conn.laddr.ip in ["0.0.0.0", "::"]:
                                bound_to_all = True
                                break
        except (psutil.AccessDenied, AttributeError):
            pass

        if not bound_to_all:
            self.root.after(0, lambda: messagebox.showwarning(
                "Service Binding Warning",
                f"⚠️ Warning: No service detected listening on port {port}\n\n"
                f"Make sure your application is:\n"
                f"1. Running and listening on port {port}\n"
                f"2. Bound to 0.0.0.0:{port} (not 127.0.0.1:{port})\n\n"
                f"Example: python -m http.server {port} --bind 0.0.0.0"
            ))

    def add_tunnel_card(self, tunnel: TunnelInfo):
        """Add a tunnel card to the UI"""
        # Hide empty label
        self.empty_label.pack_forget()

        # Create card frame
        card = ctk.CTkFrame(self.tunnels_scroll, height=150)
        card.pack(fill="x", padx=5, pady=5)

        # Header
        header_frame = ctk.CTkFrame(card)
        header_frame.pack(fill="x", padx=10, pady=10)

        port_label = ctk.CTkLabel(
            header_frame,
            text=f"Port {tunnel.port}",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        port_label.pack(side="left", padx=10)

        # Status indicator
        status_indicator = ctk.CTkLabel(
            header_frame,
            text="⚫ Checking...",
            font=ctk.CTkFont(size=12)
        )
        status_indicator.pack(side="left", padx=20)

        # Stop button
        stop_btn = ctk.CTkButton(
            header_frame,
            text="🛑 Stop",
            command=lambda: self.stop_tunnel(tunnel.port),
            width=80,
            height=30,
            fg_color="red",
            hover_color="darkred"
        )
        stop_btn.pack(side="right", padx=10)

        # Info frame
        info_frame = ctk.CTkFrame(card)
        info_frame.pack(fill="x", padx=20, pady=5)

        # Create info labels
        info_labels = [
            f"🌐 VPS: {tunnel.vps_ip}",
            f"🔒 Access: {tunnel.access_scope.upper()}",
            f"⏱️ Started: {tunnel.created_at}"
        ]

        for text in info_labels:
            label = ctk.CTkLabel(info_frame, text=text, font=ctk.CTkFont(size=11))
            label.pack(anchor="w", pady=2)

        # Status detail frame
        detail_frame = ctk.CTkFrame(card)
        detail_frame.pack(fill="x", padx=20, pady=5)

        # Status detail label
        detail_label = ctk.CTkLabel(
            detail_frame,
            text="Checking service status...",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        detail_label.pack(side="left", padx=10)

        # Store references
        self.tunnel_frames[tunnel.port] = {
            'card': card,
            'status': status_indicator,
            'detail': detail_label
        }

        # Clear port entry
        self.port_entry.delete(0, 'end')

    def update_tunnel_status(self, port: int, listening: bool):
        """Update tunnel status from monitor"""
        if port in self.tunnel_frames:
            frame = self.tunnel_frames[port]

            # Update status indicator
            if listening:
                status_text = "🟢 Listening"
                status_detail = "Service is running and accessible"
            else:
                status_text = "🟡 Not Listening"
                status_detail = "No service detected on this port"

            self.root.after(0, lambda: frame['status'].configure(text=status_text))
            self.root.after(0, lambda: frame['detail'].configure(text=status_detail))

            # Update tunnel info
            if port in self.active_tunnels:
                self.active_tunnels[port].listening = listening

    def stop_tunnel(self, port: int):
        """Stop a tunnel and clean up firewall rules"""
        if port not in self.active_tunnels:
            return

        # Confirm
        if not messagebox.askyesno("Confirm", f"Stop tunnel on port {port}?"):
            return

        def cleanup_thread():
            """Background cleanup to avoid blocking UI"""
            try:
                # Stop monitor
                if port in self.monitors:
                    self.monitors[port].stop()

                # Add nftables drop rule first
                drop_success = self.firewall.add_nft_drop_rule(port)
                if drop_success:
                    print(f"Added nftables drop rule for port {port}")

                # Remove UFW rules
                removed = self.firewall.remove_ufw_rules(port)
                if removed:
                    print(f"Removed {removed} UFW rules for port {port}")

                # Update UI in main thread
                self.root.after(0, self.finish_stop_tunnel, port, removed)

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to stop tunnel: {e}"))

        # Start cleanup in background
        thread = threading.Thread(target=cleanup_thread, daemon=True)
        thread.start()

    def finish_stop_tunnel(self, port: int, removed_rules: int):
        """Finish stopping tunnel in main thread"""
        # Clean up monitors
        if port in self.monitors:
            del self.monitors[port]

        # Remove from UI
        if port in self.tunnel_frames:
            self.tunnel_frames[port]['card'].destroy()
            del self.tunnel_frames[port]

        # Remove from active tunnels
        if port in self.active_tunnels:
            del self.active_tunnels[port]

        # Show empty label if no tunnels
        if not self.active_tunnels:
            self.empty_label.pack(pady=50)

        # Show success message
        messagebox.showinfo(
            "Success",
            f"Tunnel on port {port} stopped!\n\n"
            f"🚫 Removed {removed_rules} firewall rule(s)\n"
            f"🛡️ Port is now blocked on Tailscale interface"
        )

    def stop_all_tunnels(self):
        """Stop all active tunnels"""
        if not self.active_tunnels:
            messagebox.showinfo("Info", "No active tunnels to stop")
            return

        if not messagebox.askyesno("Confirm", "Stop ALL active tunnels?"):
            return

        ports = list(self.active_tunnels.keys())
        for port in ports:
            self.stop_tunnel(port)

    def refresh_status(self):
        """Refresh system status"""
        self.check_requirements()
        messagebox.showinfo("Refreshed", "Status refreshed successfully")

    def update_status(self):
        """Periodic status update"""
        # This runs in main thread, safe to update UI
        self.root.after(5000, self.update_status)

    def run(self):
        """Start the GUI application"""
        # Check if running as root
        if os.geteuid() != 0:
            messagebox.showwarning(
                "Root Required",
                "This application needs root privileges for firewall management.\n"
                "Please restart with sudo."
            )

        self.root.mainloop()

        # Cleanup on exit
        for monitor in self.monitors.values():
            monitor.stop()

def main():
    app = TunnelManagerGUI()
    app.run()

if __name__ == "__main__":
    main()