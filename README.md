# rw-local-tunnel 🌐

> **Specialized Tailscale tunnel manager for servers running NPM (Nginx Proxy Manager) alongside Headscale/Tailscale**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tailscale](https://img.shields.io/badge/tailscale%2Fheadscale-ready-orange)](https://tailscale.com/)

## 🎯 **Specialized Use Case**

This tool is designed for a **very specific setup**:
- **Server** running [Headscale](https://headscale.net/) or [Tailscale](https://tailscale.com/)
- **NPM (Nginx Proxy Manager)** handling HTTPS/SSL termination
- **Local services** that need to be exposed through the Tailscale network
- **Firewall management** via UFW and nftables for secure access control

**Perfect for:** Home labs, self-hosted services, development environments with NPM reverse proxy setups.

## ✨ Features

- **🔒 Secure Tunneling** - Expose local services through your Tailscale/Headscale network
- **🎨 Modern Desktop GUI** - Beautiful windowed interface for managing multiple tunnels
- **🔥 Automatic Firewall Management** - UFW and nftables integration with NPM compatibility
- **📊 Real-time Monitoring** - Visual status indicators for service health
- **🎯 Flexible Access Control** - VPS-only or full Tailnet access patterns
- **🧹 Auto Cleanup** - Proper signal handling ensures clean shutdown
- **🚀 Multiple Tunnel Support** - Manage several exposed ports simultaneously

## 📋 Prerequisites

### System Requirements
- **Python 3.8+**
- **Linux with systemd** (Ubuntu, Debian, Fedora, etc.)
- **Root privileges** (for firewall management)

### Required Services
- **Tailscale or Headscale** installed and configured ([Tailscale Download](https://tailscale.com/download) | [Headscale Setup](https://headscale.net/))
- **NPM (Nginx Proxy Manager)** running on your server
- **UFW firewall** enabled (usually pre-installed on Ubuntu/Debian)
- **nftables** (modern Linux firewall)

### Network Setup
- Server connected to Tailscale/Headscale network
- NPM configured with your domain names and SSL certificates
- Local services (Docker containers, web apps, etc.) running on various ports

## 🚀 Quick Start

### Installation

#### Method 1: System Installation (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/rw-local-tunnel.git
cd rw-local-tunnel

# Install dependencies
pip install -r requirements.txt

# Build desktop application
./build_tools/build_desktop_app.sh

# Install system-wide with desktop integration
./install.sh
```

#### Method 2: Development Setup
```bash
# Clone and install for development
git clone https://github.com/yourusername/rw-local-tunnel.git
cd rw-local-tunnel
pip install -r requirements.txt
```

### Usage Options

#### 🖥️ **Desktop Application (Recommended)**
Modern desktop application with multiple tunnel management:

```bash
# After system installation - launch from applications menu
# Or from terminal:
rw-tunnel-launcher.sh

# Development mode:
sudo python rw_tunnel_gui.py
```

**GUI Features:**
- 📊 Real-time monitoring dashboard
- ➕ Easy tunnel creation
- 🔄 Multiple tunnel management
- 🎛️ Visual status indicators
- 🛑 One-click tunnel stopping
- 🎨 Beautiful CustomTkinter interface

#### 📟 **Command Line Interface**
Traditional terminal interface:

```bash
# Start tunnel with monitoring (interactive mode)
sudo python rw-local-tunnel.py start

# Start tunnel on specific port
sudo python rw-local-tunnel.py start 8080

# Start tunnel without monitoring
sudo python rw-local-tunnel.py start 3000 --no-monitor

# Stop a tunnel
sudo python rw-local-tunnel.py stop 8080
```

## 🎯 Use Cases

### 1. **NPM Integration - Web Services**
Expose local web applications through NPM reverse proxy:
```bash
# Local web app running on port 3000
docker run -p 3000:3000 my-web-app

# Create tunnel for NPM to access
rw-tunnel-launcher.sh  # Launch GUI
# In GUI: Create tunnel for port 3000

# Configure in NPM:
# Domain: app.yourdomain.com
# Forward Host/IP: localhost (or 127.0.0.1)
# Forward Port: 3000
```

### 2. **API Services Behind NPM**
Expose API endpoints with SSL termination:
```bash
# API service on port 8080
rw-tunnel-launcher.sh  # Launch GUI
# Create tunnel for port 8080

# NPM config:
# Domain: api.yourdomain.com
# Forward to: localhost:8080
# SSL: Enabled via NPM
```

### 3. **Development Environment**
Quick access to development servers:
```bash
# Development server
npm run dev  # Running on port 5173

# Quick tunnel via CLI
sudo python rw-local-tunnel.py start 5173

# Access via: https://dev.yourdomain.com (configured in NPM)
```

### 4. **Database Admin Interfaces**
Secure database management tools:
```bash
# phpMyAdmin, Adminer, pgAdmin, etc.
docker run -p 8081:80 phpmyadmin

# Tunnel the interface
rw-tunnel-launcher.sh  # Launch GUI, create tunnel for port 8081

# Access via NPM: https://db.yourdomain.com
```

## 🔧 Configuration

### Environment Variables

Configure default behavior with environment variables:

```bash
export VPS_NAME="vpn"                    # Your VPS hostname in Tailscale
export TAILNET_CIDR="100.64.0.0/10"     # Your Tailnet IP range
export DEFAULT_SCOPE="vps"              # Default access scope: "vps" or "tailnet"
```

### Access Scopes

When starting a tunnel, you can choose the access scope:

1. **VPS Only** (Recommended) - Only your VPS can access the port
2. **Entire Tailnet** - All devices in your Tailscale network can access

## 📊 Monitoring

The real-time monitoring displays:
- Port status (listening/not listening)
- VPS IP address
- Active connection count
- Live timestamp

Press `Ctrl+C` to stop monitoring and automatically close the tunnel.

## 🏗️ Architecture

```
Internet ──HTTPS──▶ NPM (443) ──HTTP──▶ Local Service (8080)
    │                   │                       ▲
    │                   │                       │
    ▼                   ▼                       │
┌─────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   Domain    │ │ Nginx Proxy     │ │   rw-local-tunnel   │
│ SSL Certs   │ │   Manager       │ │                     │
│ Let's       │ │ - SSL Term      │ │ ┌─────────────────┐ │
│ Encrypt     │ │ - Reverse Proxy │ │ │   UFW Rules     │ │
└─────────────┘ │ - Load Balance  │ │ │ Tailscale Allow │ │
                └─────────────────┘ │ └─────────────────┘ │
                                    │ ┌─────────────────┐ │
                Tailscale Network   │ │ nftables Rules  │ │
                ┌─────────────────┐ │ │ Port Control    │ │
                │   VPS/Server    │ │ └─────────────────┘ │
                │ Headscale Node  │ └─────────────────────┘
                └─────────────────┘
```

**Flow:** Internet → NPM (SSL) → Local Service (via rw-tunnel firewall rules) → Tailscale Network

## 🛡️ Security

### Multi-Layer Security Model
- **Tailscale/Headscale Encryption** - All traffic encrypted via WireGuard tunnels
- **NPM SSL Termination** - HTTPS with Let's Encrypt certificates
- **Firewall Rules** - Automatic UFW and nftables configuration
- **Access Control** - VPS-only or Tailnet-wide access patterns
- **Auto Cleanup** - Rules are removed when tunnel closes
- **Private Network Only** - No direct public internet exposure

### NPM Integration Benefits
- **SSL/TLS Encryption** - End-to-end encryption from browser to service
- **Domain-based Access** - Clean URLs instead of IP:port combinations
- **Certificate Management** - Automatic SSL certificate renewal
- **Load Balancing** - NPM can distribute traffic across multiple instances

## 🐛 Troubleshooting

### Common Issues

**1. Permission Denied**
```bash
# Script requires root for firewall management
sudo python rw-local-tunnel.py start
```

**2. Tailscale Not Running**
```bash
# Start Tailscale daemon
sudo systemctl start tailscaled
tailscale up
```

**3. Service Not Accessible via NPM**
Ensure your service is bound to `0.0.0.0` not `127.0.0.1`:
```bash
# Flask example
app.run(host='0.0.0.0', port=8080)

# Docker example
docker run -p 8080:8080 --bind 0.0.0.0 my-app

# Node.js example
app.listen(8080, '0.0.0.0', () => {
    console.log('Server running on 0.0.0.0:8080');
});
```

**4. NPM Cannot Reach Service**
Check NPM proxy configuration:
```
Forward Host/IP: localhost (or 127.0.0.1)
Forward Port: [your tunnel port]
Block Common Exploits: ON
Websockets Support: ON (if needed)
```

**4. UFW Not Active**
```bash
# Enable UFW
sudo ufw enable
```

### Debug Mode

For verbose output, check the script logs and system logs:
```bash
# Check UFW rules
sudo ufw status numbered

# Check nftables rules
sudo nft list ruleset

# Check Tailscale status
tailscale status
```

## 🏗️ Building Desktop Application

Create standalone executable with desktop integration:

### Project Structure
```
rw-local-tunnel/
├── rw-local-tunnel.py      # CLI version
├── rw_tunnel_gui.py        # GUI version
├── build_tools/            # Build scripts and tools
├── desktop_files/          # Desktop integration files
├── icons/                  # Icon files and data
├── dist/                   # Built executable
└── install.sh              # System installer
```

### Quick Build

```bash
# 1. Setup environment
source venv/bin/activate
pip install -r requirements.txt

# 2. Build desktop application
./build_tools/build_desktop_app.sh

# 3. Install system-wide with desktop integration
./install.sh
```

### What Gets Built

- **`dist/RWLocalTunnel`** - Standalone GUI executable (22MB)
- **Desktop integration** - Application menu entry with icon
- **PolicyKit support** - Proper authentication for GUI root access
- **Launcher scripts** - Multiple desktop launcher options

### Desktop Integration Features

The installer creates:
- **Application menu entry**: "RW Local Tunnel"
- **Desktop icon**: Embedded icon works on any system
- **PolicyKit policy**: Proper GUI authentication
- **System launcher**: `rw-tunnel-launcher.sh` command
- **Multiple launch options**: Simple, Fixed, and PolicyKit versions

### Installation Options

#### System Installation (Recommended)
```bash
# Install to /usr/local/bin with full desktop integration
./install.sh

# Launch from applications menu or:
rw-tunnel-launcher.sh
```

#### Portable Usage
```bash
# Run directly from dist/ folder
sudo ./dist/RWLocalTunnel
```

### Desktop Launcher Variants

1. **RWLocalTunnel-Simple.desktop** - Uses gnome-terminal (most reliable)
2. **RWLocalTunnel-Fixed.desktop** - Advanced launcher with environment preservation
3. **PolicyKit integration** - System-level authentication

### Build Requirements

- Python 3.8+
- Virtual environment (recommended)
- PyInstaller 6.16+
- CustomTkinter, PIL, psutil
- All dependencies from `requirements.txt`

## 🧪 Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run tests
pytest tests/
```

### Code Style

```bash
# Format code with black
black rw-local-tunnel.py

# Check code style
black --check rw-local-tunnel.py
```

## 🔗 **Typical NPM + Tailscale Workflow**

### Step-by-Step Integration

1. **Setup Tailscale/Headscale** on your server
2. **Install NPM** (usually via Docker)
3. **Configure NPM** with your domains and SSL certificates
4. **Install and use rw-local-tunnel** to expose services to NPM:

```bash
# Install system-wide
./install.sh

# Launch GUI application
rw-tunnel-launcher.sh
# Create tunnel for port 3000

# In NPM Web UI:
# - Domain Names: app.yourdomain.com
# - Scheme: http
# - Forward Hostname/IP: localhost
# - Forward Port: 3000
# - SSL: Enable with Let's Encrypt
```

5. **Access via clean URL**: `https://app.yourdomain.com`

### Common NPM Services to Tunnel
- **Portainer** (Docker management) - Port 9000
- **Grafana** (Monitoring dashboards) - Port 3000
- **Home Assistant** (Home automation) - Port 8123
- **Nextcloud** (File sharing) - Port 80/443
- **Jellyfin** (Media server) - Port 8096
- **Vaultwarden** (Password manager) - Port 80
- **Custom web applications** - Various ports

## 🤝 Contributing

Contributions are welcome! This tool is specifically designed for NPM + Tailscale/Headscale setups, so please keep that focus when contributing.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/npm-integration`)
3. Test with NPM and Tailscale/Headscale setup
4. Commit your changes (`git commit -m 'Add NPM-specific feature'`)
5. Push to the branch (`git push origin feature/npm-integration`)
6. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Tailscale](https://tailscale.com/) for the amazing VPN solution
- [Rich](https://github.com/Textualize/rich) for beautiful terminal interfaces
- [psutil](https://github.com/giampaolo/psutil) for cross-platform process utilities

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/rw-local-tunnel/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/rw-local-tunnel/discussions)

---

**Made with ❤️ for the Tailscale community**