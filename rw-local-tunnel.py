#!/usr/bin/env python3
"""
rw-local-tunnel: Secure Tailscale Local Port Tunneling
A Python implementation with better error handling and monitoring.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil
import rich
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
from rich import box as rich_box

console = Console()

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
            time.sleep(2)  # Give it time to start
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
                cmd_no_comment = cmd[:-2]  # Remove comment part
                subprocess.run(cmd_no_comment, check=True, capture_output=True)
                return True
            except subprocess.CalledProcessError:
                return False
    
    def remove_ufw_rules(self, port: int) -> int:
        """Remove UFW rules for a port"""
        removed = 0
        try:
            # Get numbered rules
            result = subprocess.run(
                ["ufw", "status", "numbered"],
                capture_output=True, text=True, check=True
            )
            
            # Find rules for our port (simple approach)
            lines = result.stdout.split('\n')
            rule_numbers = []
            
            for line in lines:
                if f"port {port}" in line and "rwlt:" in line:
                    # Extract rule number
                    parts = line.strip().split(']', 1)
                    if len(parts) > 0:
                        num_part = parts[0].replace('[', '').strip()
                        if num_part.isdigit():
                            rule_numbers.append(int(num_part))
            
            # Delete rules in reverse order
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
            # Ensure table and chain exist
            subprocess.run([
                "nft", "add", "table", self.config.nft_family, self.config.nft_table
            ], capture_output=True)
            
            chain_cmd = [
                "nft", "add", "chain", self.config.nft_family, 
                self.config.nft_table, self.config.nft_chain,
                f'{{ type filter hook input priority {self.config.nft_priority}; policy accept; }}'
            ]
            subprocess.run(chain_cmd, capture_output=True)
            
            # Add drop rule
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
            # List rules with handles
            result = subprocess.run([
                "nft", "-a", "list", "chain", 
                self.config.nft_family, self.config.nft_table, self.config.nft_chain
            ], capture_output=True, text=True, check=True)
            
            # Find handles for our port rules
            for line in result.stdout.split('\n'):
                if f'tcp dport {port}' in line and 'tailscale0' in line:
                    # Extract handle (last word)
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

class PortMonitor:
    """Simple port monitoring with rich display"""
    
    def __init__(self, port: int, vps_ip: str):
        self.port = port
        self.vps_ip = vps_ip
        self.running = True
        
    def get_port_info(self) -> bool:
        """Get port listening status"""
        listening = False

        try:
            # Check if port is listening
            for conn in psutil.net_connections():
                # Check if laddr exists and has port attribute
                if hasattr(conn, 'laddr') and conn.laddr:
                    if (hasattr(conn.laddr, 'port') and
                        conn.laddr.port == self.port):
                        if conn.status == psutil.CONN_LISTEN:
                            listening = True
                            break

        except (psutil.AccessDenied, AttributeError, OSError):
            pass

        return listening
    
    def create_dashboard(self) -> Panel:
        """Create simple dashboard for display"""
        listening = self.get_port_info()

        # Status table
        status_table = Table(show_header=False, box=None, padding=(0, 2))
        status_table.add_column("Field", style="bold cyan", width=15)
        status_table.add_column("Value", style="bold white")

        status_color = "green" if listening else "red"
        status_icon = "✅ LISTENING" if listening else "❌ NOT LISTENING"
        status_detail = "Service is running and accessible" if listening else "No service detected on this port"

        status_table.add_row("📍 Local Port", f"[bold yellow]{self.port}[/bold yellow]")
        status_table.add_row("🌐 VPS IP", f"[bold blue]{self.vps_ip}[/bold blue]")
        status_table.add_row("🔌 Status", f"[{status_color}]{status_icon}[/{status_color}]")
        status_table.add_row("📋 Details", f"[dim]{status_detail}[/dim]")
        status_table.add_row("⏰ Updated", time.strftime("%H:%M:%S"))

        # Simple info panel
        info_text = f"""
🔗 [bold]Access URL:[/bold] http://{self.vps_ip}:{self.port}
🛡️ [bold]Security:[/bold] Tailscale encrypted tunnel
📡 [bold]Protocol:[/bold] TCP tunnel via UFW firewall rules

[dim]Tip: Make sure your service binds to 0.0.0.0:{self.port}[/dim]
        """.strip()

        return Panel(
            Align.center(
                status_table,
                vertical="middle"
            ),
            title=f"🚀 [bold blue]Tunnel Monitor - Port {self.port}[/bold blue]",
            subtitle="[dim]Press Ctrl+C to stop tunnel[/dim]",
            border_style="blue"
        )
    
    def monitor(self):
        """Start monitoring with live display"""
        def signal_handler(signum, frame):
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        with Live(console=console, refresh_per_second=1) as live:
            while self.running:
                dashboard = self.create_dashboard()
                live.update(dashboard)
                time.sleep(2)

class TunnelManager:
    """Main tunnel management class"""
    
    def __init__(self):
        self.config = TunnelConfig()
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        self.tailscale = TailscaleManager(self.config)
        self.firewall = FirewallManager(self.config)
        
    def check_dependencies(self) -> List[str]:
        """Check for required dependencies"""
        missing = []
        
        # Check Tailscale
        if not self.tailscale.check_installation():
            missing.append("tailscale")
            
        # Check other tools
        for tool in ["nft", "ufw"]:
            try:
                subprocess.run([tool, "--version"], 
                              capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(tool)
                
        return missing
    
    def setup_tailscale(self) -> bool:
        """Setup and authenticate Tailscale"""
        if not self.tailscale.check_installation():
            console.print("❌ [red]Tailscale not installed[/red]")
            console.print("📦 Install from: https://tailscale.com/download")
            return False
            
        if not self.tailscale.is_running():
            console.print("🔄 Starting Tailscale daemon...")
            if not self.tailscale.start_daemon():
                console.print("❌ [red]Failed to start Tailscale daemon[/red]")
                return False
                
        status = self.tailscale.get_status()
        backend_state = status.get("BackendState", "")
        
        if backend_state == "Running":
            console.print("✅ [green]Tailscale is running and connected[/green]")
            return True
        elif backend_state in ["NeedsLogin", "NeedsMachineAuth"]:
            console.print("🔐 Tailscale needs authentication")
            if Confirm.ask("Run 'tailscale up' now?"):
                return self.tailscale.authenticate()
            return False
        else:
            console.print(f"❌ [red]Tailscale status: {backend_state}[/red]")
            return False
    
    def get_port(self, port_arg: Optional[int] = None) -> int:
        """Get port from argument or prompt"""
        if port_arg:
            return port_arg
            
        last_port_file = self.config.state_dir / "last_port"
        last_port = None
        
        if last_port_file.exists():
            try:
                last_port = int(last_port_file.read_text().strip())
            except (ValueError, FileNotFoundError):
                pass
                
        if last_port:
            port = IntPrompt.ask(
                f"🔌 Enter local TCP port",
                default=last_port,
                show_default=True
            )
        else:
            port = IntPrompt.ask("🔌 Enter local TCP port (1-65535)")
            
        # Validate port range
        if not (1 <= port <= 65535):
            console.print("❌ [red]Invalid port range[/red]")
            return self.get_port()
            
        # Save last port
        last_port_file.write_text(str(port))
        return port
    
    def get_access_scope(self, vps_ip: str) -> str:
        """Get access scope from user"""
        console.print("\n🔒 Choose access scope:")
        console.print(f"   1) VPS only ({vps_ip}/32) - Recommended")
        console.print(f"   2) Entire Tailnet ({self.config.tailnet_cidr})")
        
        default = 1 if self.config.default_scope == "vps" else 2
        choice = IntPrompt.ask("Choose option", choices=["1", "2"], default=default)
        
        if choice == 1:
            console.print(f"✅ [green]Selected: VPS only ({vps_ip}/32)[/green]")
            return f"{vps_ip}/32"
        else:
            console.print(f"✅ [green]Selected: Entire Tailnet ({self.config.tailnet_cidr})[/green]")
            return self.config.tailnet_cidr
    
    def check_service_binding(self, port: int):
        """Check if service is properly bound"""
        console.print(f"\n🔍 Checking service on port {port}...")
        
        bound_to_all = False
        for conn in psutil.net_connections():
            if (conn.laddr.port == port and 
                conn.status == psutil.CONN_LISTEN):
                if conn.laddr.ip in ["0.0.0.0", "::"]:
                    bound_to_all = True
                    break
                    
        if bound_to_all:
            console.print("✅ [green]Service is accessible from external interfaces[/green]")
        else:
            console.print("⚠️  [yellow]Warning: Service may be bound to localhost only[/yellow]")
            console.print("💡 Bind to 0.0.0.0 to allow VPS access")
    
    def start_tunnel(self, port: Optional[int] = None, monitor: bool = True):
        """Start tunnel with optional monitoring"""
        console.print("🚀 [bold blue]Starting Tailscale tunnel setup...[/bold blue]")
        
        # Check dependencies
        missing = self.check_dependencies()
        if missing:
            console.print(f"❌ [red]Missing dependencies: {', '.join(missing)}[/red]")
            return False
            
        # Setup Tailscale
        if not self.setup_tailscale():
            return False
            
        # Get VPS IP
        console.print(f"🔍 Looking for VPS '{self.config.vps_name}' on Tailscale...")
        vps_ip = self.tailscale.get_vps_ip()
        if not vps_ip:
            vps_ip = Prompt.ask("🌐 Enter VPS Tailscale IPv4 address")
            
        console.print(f"✅ [green]Found VPS at: {vps_ip}[/green]")
        
        # Get port and scope
        port = self.get_port(port)
        scope = self.get_access_scope(vps_ip)
        
        # Setup firewall
        console.print("\n🔧 [bold]Configuring firewall rules...[/bold]")
        
        if not self.firewall.check_ufw_status():
            console.print("🔥 UFW is inactive")
            if Confirm.ask("Enable UFW now?"):
                if not self.firewall.enable_ufw():
                    console.print("❌ [red]Failed to enable UFW[/red]")
                    return False
            else:
                console.print("❌ [red]UFW must be active[/red]")
                return False
                
        # Remove any existing nft drop rules
        removed = self.firewall.remove_nft_drop_rules(port)
        if removed:
            console.print(f"✅ Removed {removed} nftables drop rule(s)")
            
        # Add UFW allow rule
        if self.firewall.add_ufw_rule(scope, port):
            console.print("✅ [green]UFW rule added successfully[/green]")
        else:
            console.print("❌ [red]Failed to add UFW rule[/red]")
            return False
            
        self.check_service_binding(port)
        
        console.print("\n✅ [bold green]Tunnel setup complete![/bold green]")
        console.print(f"🔌 Port {port} is accessible from {scope} via Tailscale")
        
        if monitor and Confirm.ask("\n🔍 Start traffic monitoring? (auto-closes tunnel on exit)", default=True):
            # Store PID for cleanup
            pid_file = self.config.state_dir / f"monitor_{port}.pid"
            pid_file.write_text(str(os.getpid()))
            
            def cleanup():
                console.print("\n🛑 [yellow]Cleaning up tunnel...[/yellow]")
                self.firewall.add_nft_drop_rule(port)
                removed = self.firewall.remove_ufw_rules(port)
                if removed:
                    console.print(f"✅ Removed {removed} UFW rule(s)")
                pid_file.unlink(missing_ok=True)
                console.print("✅ [green]Tunnel closed and access blocked[/green]")
                
            def signal_handler(signum, frame):
                cleanup()
                sys.exit(0)
                
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            try:
                monitor_obj = PortMonitor(port, vps_ip)
                monitor_obj.monitor()
            except KeyboardInterrupt:
                pass
            finally:
                cleanup()
        else:
            console.print(f"💡 Use 'rw-local-tunnel stop {port}' to close the tunnel")
            
        return True
    
    def stop_tunnel(self, port: Optional[int] = None):
        """Stop tunnel and clean up rules"""
        console.print("🛑 [bold red]Stopping Tailscale tunnel...[/bold red]")
        
        if not port:
            port = self.get_port()
            
        # Stop any running monitor
        pid_file = self.config.state_dir / f"monitor_{port}.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, signal.SIGTERM)
                console.print(f"🔄 Stopped running monitor for port {port}")
            except (ValueError, ProcessLookupError):
                pass
            pid_file.unlink(missing_ok=True)
            
        # Add nft drop rule
        if self.firewall.add_nft_drop_rule(port):
            console.print("🚫 Added nftables drop rule")
            
        # Remove UFW rules
        removed = self.firewall.remove_ufw_rules(port)
        if removed:
            console.print(f"✅ Removed {removed} UFW rule(s)")
            
        console.print(f"\n🛑 [bold green]Tunnel stopped successfully![/bold green]")
        console.print(f"🚫 Port {port} is now blocked on Tailscale interface")

def main():
    parser = argparse.ArgumentParser(
        description="🌐 Tailscale Local Tunnel Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rw-local-tunnel start 3000    # Open port 3000 with monitoring
  rw-local-tunnel stop 8080     # Close port 8080
  rw-local-tunnel start         # Interactive mode
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start tunnel")
    start_parser.add_argument("port", nargs="?", type=int, help="Local port to expose")
    start_parser.add_argument("--no-monitor", action="store_true", help="Skip monitoring")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop tunnel")
    stop_parser.add_argument("port", nargs="?", type=int, help="Port to close")
    
    # Monitor command (alias for start)
    monitor_parser = subparsers.add_parser("monitor", help="Start tunnel with monitoring")
    monitor_parser.add_argument("port", nargs="?", type=int, help="Local port to expose")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    # Check if running as root
    if os.geteuid() != 0:
        console.print("🔐 This script requires root privileges")
        # Re-exec with sudo
        os.execvp("sudo", ["sudo", "-E"] + sys.argv)
        
    tunnel = TunnelManager()
    
    try:
        if args.command == "start":
            tunnel.start_tunnel(args.port, monitor=not args.no_monitor)
        elif args.command == "stop":
            tunnel.stop_tunnel(args.port)
        elif args.command == "monitor":
            tunnel.start_tunnel(args.port, monitor=True)
    except KeyboardInterrupt:
        console.print("\n👋 [yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"❌ [red]Error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()