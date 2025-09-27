#!/usr/bin/env python3
"""
System tray integration for RW Local Tunnel
Provides minimized access to tunnel management
"""

import tkinter as tk
from tkinter import messagebox
import pystray
from pystray import MenuItem, Menu
from PIL import Image, ImageDraw
import threading
import subprocess
import sys
import os

class TunnelTray:
    """System tray application for tunnel management"""

    def __init__(self):
        self.icon = None
        self.running = False
        self.gui_process = None

    def create_image(self, color="blue"):
        """Create system tray icon"""
        # Create a simple circular icon
        image = Image.new('RGB', (64, 64), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(image)

        if color == "blue":
            fill_color = (0, 120, 215)  # Blue
        elif color == "green":
            fill_color = (16, 124, 16)  # Green
        else:
            fill_color = (196, 43, 28)  # Red

        # Draw circle
        draw.ellipse([8, 8, 56, 56], fill=fill_color, outline=(255, 255, 255))

        # Draw "T" for tunnel
        draw.text((24, 20), "T", fill=(255, 255, 255), anchor="mm")

        return image

    def show_gui(self, icon=None, item=None):
        """Launch the main GUI application"""
        try:
            if self.gui_process and self.gui_process.poll() is None:
                # GUI is already running
                messagebox.showinfo("Info", "GUI is already running")
                return

            # Launch GUI
            self.gui_process = subprocess.Popen([
                sys.executable, "rw_tunnel_gui.py"
            ])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch GUI: {e}")

    def quick_tunnel(self, icon=None, item=None):
        """Quick tunnel creation dialog"""
        root = tk.Tk()
        root.withdraw()  # Hide main window

        port = tk.simpledialog.askinteger(
            "Quick Tunnel",
            "Enter port number:",
            minvalue=1,
            maxvalue=65535,
            initialvalue=8080
        )

        if port:
            try:
                # Launch CLI version for quick tunnel
                subprocess.run([
                    "sudo", sys.executable, "rw-local-tunnel.py",
                    "start", str(port), "--no-monitor"
                ])
                messagebox.showinfo("Success", f"Tunnel created on port {port}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create tunnel: {e}")

        root.destroy()

    def show_status(self, icon=None, item=None):
        """Show quick status"""
        try:
            # Get active tunnels (simplified check)
            result = subprocess.run([
                "netstat", "-tlnp"
            ], capture_output=True, text=True)

            listening_ports = []
            for line in result.stdout.split('\n'):
                if ':' in line and 'LISTEN' in line:
                    try:
                        port = line.split(':')[1].split()[0]
                        if port.isdigit():
                            listening_ports.append(port)
                    except:
                        pass

            if listening_ports:
                status = f"Listening ports: {', '.join(listening_ports[:5])}"
                if len(listening_ports) > 5:
                    status += f"\n... and {len(listening_ports) - 5} more"
            else:
                status = "No active tunnels"

            messagebox.showinfo("Tunnel Status", status)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get status: {e}")

    def quit_app(self, icon=None, item=None):
        """Quit the application"""
        if self.gui_process and self.gui_process.poll() is None:
            self.gui_process.terminate()

        self.running = False
        if self.icon:
            self.icon.stop()

    def run(self):
        """Start the system tray application"""
        # Create menu
        menu = Menu(
            MenuItem("🖥️ Show GUI", self.show_gui, default=True),
            MenuItem("⚡ Quick Tunnel", self.quick_tunnel),
            MenuItem("📊 Status", self.show_status),
            Menu.SEPARATOR,
            MenuItem("❌ Quit", self.quit_app)
        )

        # Create icon
        image = self.create_image("blue")
        self.icon = pystray.Icon(
            "rw-tunnel",
            image,
            "RW Local Tunnel",
            menu
        )

        self.running = True

        # Run in background
        self.icon.run()

def main():
    """Main entry point"""
    if os.geteuid() != 0:
        print("System tray requires root privileges")
        print("Restarting with sudo...")
        os.execvp("sudo", ["sudo", "-E"] + sys.argv)

    app = TunnelTray()
    app.run()

if __name__ == "__main__":
    main()