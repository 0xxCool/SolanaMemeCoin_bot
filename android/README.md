# 📱 Solana Memecoin Trading Bot - Android App

**Professional mobile trading app with real-time synchronization**

## ✨ Features

- 📊 **Mobile Dashboard** - Real-time metrics on the go
- 🔄 **Auto-Sync** - Syncs with Windows app and Telegram bot
- 📱 **Native Performance** - Optimized for Android
- 🎨 **Material Design** - Modern, intuitive interface
- 🔔 **Push Notifications** - Trade alerts and updates
- ⚙️ **Easy Configuration** - Touch-friendly settings
- 📈 **Live Charts** - Real-time price tracking
- 🌙 **Dark Mode** - Easy on the eyes

## 📋 Requirements

- **OS:** Android 5.0 (Lollipop) or higher
- **RAM:** 2GB minimum, 4GB recommended
- **Storage:** 100MB free space
- **Internet:** WiFi or mobile data

## 🚀 Installation

### From Google Play Store

1. Open [Google Play Store](https://play.google.com/store)
2. Search "Solana Trading Bot Pro"
3. Tap Install
4. Open and configure

### From APK (Direct Install)

1. Download `SolanaTradingBot-v1.0.0.apk`
2. Enable "Install from Unknown Sources" in Settings
3. Open downloaded APK
4. Tap Install
5. Configure and start trading

### Build from Source

```bash
# 1. Install Buildozer
pip install buildozer cython

# 2. Install Android SDK & NDK
# Follow: https://buildozer.readthedocs.io/

# 3. Build APK
cd android
buildozer android debug

# Output: bin/SolanaTradingBot-1.0.0-debug.apk
```

## 🔧 Configuration

### Initial Setup

1. **Connect to Sync Server**
   - Open Settings
   - Enter server IP address
   - Default: `http://YOUR_PC_IP:8765`
   - Tap "Test Connection"

2. **Trading Settings**
   - Set base trade amount
   - Configure auto-trading
   - Enable push notifications

3. **Permissions**
   - Internet access (required)
   - Notifications (recommended)
   - Wake lock (for background updates)

## 📱 App Screens

### Dashboard

- Real-time bot status
- Active positions list
- Total P&L display
- Quick actions buttons

### Positions

- List of all open trades
- Tap to view details
- Swipe to close position
- Sort by profit/loss

### Settings

- Auto-Buy toggle
- Auto-Sell toggle
- Trade amount slider
- Stop loss configuration
- Strategy presets

### Alerts

- Trade notifications
- Price alerts
- System notifications
- Alert history

## 🔄 Synchronization

The Android app syncs in real-time with:

- **Windows Desktop App** - Full bi-directional sync
- **Telegram Bot** - Commands and updates
- **Other Devices** - Multi-device support

### How to Enable Sync

1. Make sure sync server is running on PC:
   ```bash
   python windows/api/sync_server.py
   ```

2. Get PC IP address:
   ```bash
   ipconfig  # Windows
   ifconfig  # Mac/Linux
   ```

3. In Android app:
   - Settings → Sync Configuration
   - Enter PC IP (e.g., `192.168.1.100`)
   - Port: `8765`
   - Tap "Connect"

4. Status indicator shows connection:
   - 🟢 Green = Connected
   - 🔴 Red = Disconnected
   - 🟡 Yellow = Connecting

## 📦 Building for Production

### Prerequisites

```bash
# Install dependencies
pip install buildozer python-for-android

# Install Java JDK 11
# Download from: https://adoptium.net/

# Set environment variables
export JAVA_HOME=/path/to/jdk
export ANDROID_HOME=/path/to/android-sdk
```

### Build Release APK

```bash
# 1. Update version in buildozer.spec
# version = 1.0.0

# 2. Build release APK
buildozer android release

# 3. Sign APK
jarsigner -verbose -sigalg SHA256withRSA \
  -digestalg SHA-256 \
  -keystore my-release-key.keystore \
  bin/SolanaTradingBot-1.0.0-release-unsigned.apk \
  alias_name

# 4. Align APK
zipalign -v 4 \
  bin/SolanaTradingBot-1.0.0-release-unsigned.apk \
  bin/SolanaTradingBot-1.0.0-release.apk
```

### Play Store Submission

1. **Create Developer Account**
   - Go to [Google Play Console](https://play.google.com/console)
   - Pay $25 one-time fee
   - Complete account setup

2. **Prepare Assets**
   - App icon (512x512 PNG)
   - Feature graphic (1024x500)
   - Screenshots (at least 2)
   - Privacy policy URL
   - App description

3. **Create App Listing**
   - Upload APK
   - Fill in all required fields
   - Set pricing ($4.99 recommended)
   - Choose countries
   - Content rating

4. **Review & Publish**
   - Submit for review
   - Wait 2-7 days
   - App goes live!

## 🎯 Usage Tips

### Best Practices

1. **Stay Connected**
   - Keep WiFi/data enabled
   - Enable background data
   - Allow battery optimization exception

2. **Manage Notifications**
   - Customize alert levels
   - Set quiet hours
   - Priority notifications for trades

3. **Battery Optimization**
   - Disable for this app
   - Settings → Apps → Solana Bot → Battery
   - Choose "Unrestricted"

4. **Data Usage**
   - App uses ~10-20 MB/day
   - Mostly WebSocket updates
   - Use WiFi when possible

### Gestures

- **Swipe Right** on position → Close trade
- **Long Press** on position → View details
- **Pull Down** → Refresh data
- **Swipe Left/Right** on dashboard → Switch tabs

## 🔔 Push Notifications

### Setup

1. Settings → Notifications → Enable
2. Grant notification permission
3. Configure alert types:
   - Trade executed
   - Position closed
   - Price alerts
   - System status

### Notification Channels

- **Critical** - Trade executions, errors
- **Important** - Position updates, alerts
- **Info** - Status updates, general info

## 🐛 Troubleshooting

### App Crashes on Start

**Solution:**
```bash
# Clear app data
Settings → Apps → Solana Bot → Storage → Clear Data

# Reinstall app
# Or rebuild from source
buildozer android clean
buildozer android debug
```

### Cannot Connect to Server

**Causes:**
1. PC firewall blocking port 8765
2. Wrong IP address
3. Not on same WiFi network
4. Server not running

**Solutions:**
1. Check firewall settings on PC
2. Verify IP with `ipconfig`
3. Connect phone to same WiFi
4. Start server: `python api/sync_server.py`

### Notifications Not Working

**Solutions:**
1. Check notification permissions
2. Disable battery optimization
3. Allow background data
4. Check Do Not Disturb settings

### High Battery Drain

**Solutions:**
1. Reduce update frequency (Settings → Advanced)
2. Disable real-time charts
3. Enable WiFi instead of mobile data
4. Close app when not trading

## 📊 Performance

Typical resource usage:
- **RAM:** 50-150 MB
- **CPU:** 1-5% (background), 10-20% (active)
- **Battery:** ~2-5% per hour (active)
- **Data:** ~10-20 MB per day
- **Storage:** ~50 MB

## 🔒 Security & Privacy

- **No Data Collection** - We don't track your activity
- **Local Storage** - Settings stored on device only
- **Encrypted Keys** - API keys encrypted with Android Keystore
- **Secure Connection** - TLS 1.3 for all network traffic
- **No Ads** - Premium app, no advertisements
- **No Third-Party SDKs** - No analytics or tracking

**⚠️ IMPORTANT:** Only use burner wallets! Never your main wallet.

## 🌐 Network Requirements

### Firewall Configuration

On your PC running the sync server:

**Windows Firewall:**
```powershell
# Allow inbound on port 8765
netsh advfirewall firewall add rule name="Solana Bot Sync" ^
  dir=in action=allow protocol=TCP localport=8765
```

**Linux iptables:**
```bash
sudo iptables -A INPUT -p tcp --dport 8765 -j ACCEPT
```

### Router Port Forwarding (for remote access)

1. Access router admin panel
2. Port Forwarding → Add Rule
3. Internal Port: 8765
4. External Port: 8765
5. IP: Your PC's local IP
6. Protocol: TCP

⚠️ **Security Warning:** Only do this if you understand the risks!

## 📞 Support

- **In-App Help** - Tap "?" icon
- **Documentation** - [docs.solanatradingbot.com](https://docs.solanatradingbot.com)
- **Discord** - [Join Community](https://discord.gg/...)
- **Email** - support@solanatradingbot.com

## 🆕 Updates

App auto-checks for updates from Play Store. Manual update:

1. Open Google Play Store
2. Search "Solana Trading Bot Pro"
3. Tap "Update" if available

## 📄 License

Commercial License - See LICENSE.txt

## 🏆 Credits

Built with:
- Kivy - Cross-platform Python framework
- Buildozer - Android APK builder
- Material Design - Google's design system
- WebSockets - Real-time communication

## 🎬 Tutorial Videos

- [Getting Started](https://youtube.com/...)
- [Advanced Configuration](https://youtube.com/...)
- [Troubleshooting](https://youtube.com/...)
