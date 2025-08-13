# Dongle VPN Gateway System

A comprehensive multi-dongle VPN/SOCKS5 gateway system for managing multiple concurrent connections through USB dongles.

## 🚀 Features

- **Multi-VPN Server**: 6 independent WireGuard interfaces (wg0-wg5)
- **SOCKS5 Proxy**: High-performance proxy servers with minimal overhead
- **Load Balancing**: Automatic traffic distribution across multiple dongles
- **Kill Switch**: Prevents IP leakage on connection failure
- **Dynamic Agent Management**: Auto-assignment of VPN connections to agents
- **Flexible Authentication**: Support for temporary, permanent, and QR code access

## 📋 System Requirements

- Linux (RHEL/CentOS/Fedora)
- Python 3.9+
- WireGuard kernel module
- Multiple USB dongles (11-20 recommended)
- Gigabit Ethernet adapter (recommended for 10+ dongles)

## 🛠️ Quick Installation

```bash
# Clone the repository
git clone https://github.com/service0427/dongle_vpn.git
cd dongle_vpn

# Install dependencies
sudo dnf install -y wireguard-tools dante-server python3-pip
pip3 install -r requirements.txt

# Run setup script
sudo bash scripts/multi_agent_vpn_setup.sh
```

## 📁 Project Structure

```
dongle-vpn-gateway/
├── scripts/           # Shell scripts for setup and management
├── configs/           # Configuration files and templates
├── docs/              # Documentation and guides
├── src/               # Python source code
└── examples/          # Usage examples
```

## 🔧 Configuration

### VPN Setup
Edit the configuration files in `configs/wireguard/` to set up your VPN interfaces.

### SOCKS5 Setup
Configure proxy servers by editing `configs/dante.conf` or run:
```bash
bash scripts/setup_socks5.sh
```

## 🚦 Usage

### Start VPN Servers
```bash
for i in {0..5}; do
    sudo wg-quick up wg$i
done
```

### Connect via SOCKS5
```javascript
// Example with Playwright
const browser = await chromium.launch({
    proxy: { server: 'socks5://your-server-ip:1080' }
});
```

### Connect via VPN
```bash
# Generate client config
python3 src/agent_connection_manager.py
```

## 📊 Performance

| Method | Latency | Bandwidth | CPU Usage |
|--------|---------|-----------|-----------|
| Direct | Baseline | 100% | Minimal |
| SOCKS5 | +0-5ms | 95-100% | 5-10% |
| WireGuard | +10-20ms | 70-80% | 20-30% |

## 🔐 Security

- IP leak protection with kill switch
- Support for both VPN (encrypted) and SOCKS5 (high-speed)
- Mobile carrier IPs for better anonymity
- Automatic failover on dongle disconnection

## 📖 Documentation

- [Complete Setup Guide](docs/COMPLETE_SETUP_GUIDE.md)
- [Client Setup](docs/CLIENT_SETUP.md)
- [Bandwidth Analysis](docs/bandwidth_analysis.md)
- [VPN vs Proxy Comparison](docs/vpn_vs_proxy_anonymity.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## ⚠️ Disclaimer

This system is intended for legitimate network testing and management purposes only. Users are responsible for complying with all applicable laws and regulations.

## 📞 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: Remember to replace IP addresses and sensitive information with your actual configuration.