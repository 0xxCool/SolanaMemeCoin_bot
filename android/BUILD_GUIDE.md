# 📱 Android Mobile Application - Complete Build Guide

**Comprehensive guide for building the Solana Trading Bot Android APK**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Manual Build Steps](#manual-build-steps)
4. [Testing on Device](#testing-on-device)
5. [Troubleshooting](#troubleshooting)
6. [Play Store Deployment](#play-store-deployment)
7. [Advanced Configuration](#advanced-configuration)

---

## Prerequisites

### System Requirements

**Operating Systems:**
- ✅ Ubuntu/Debian Linux (Recommended)
- ✅ macOS 10.14+
- ⚠️ Windows (via WSL2 or cygwin - not recommended)

**Hardware:**
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 10GB free (for Android SDK/NDK)
- **CPU:** Multi-core processor recommended

### Required Software

#### 1. Python 3.10+

```bash
# Check Python version
python3 --version

# Install Python 3.10 on Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-venv python3.10-dev

# Install Python 3.10 on macOS
brew install python@3.10
```

#### 2. Java Development Kit (JDK) 11 or 17

```bash
# Ubuntu/Debian
sudo apt install openjdk-11-jdk

# macOS
brew install openjdk@11

# Verify installation
java -version
```

**Set JAVA_HOME:**
```bash
# Ubuntu/Debian - Add to ~/.bashrc or ~/.zshrc
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$PATH:$JAVA_HOME/bin

# macOS - Add to ~/.bashrc or ~/.zshrc
export JAVA_HOME=/usr/local/opt/openjdk@11
export PATH=$PATH:$JAVA_HOME/bin

# Apply changes
source ~/.bashrc  # or source ~/.zshrc
```

#### 3. Android SDK & NDK

**Option A: Let Buildozer download automatically (Easier)**
- Buildozer will download SDK/NDK on first build
- No manual setup needed
- Takes longer on first build (~20-30 min)

**Option B: Pre-install Android SDK (Faster)**

```bash
# Ubuntu/Debian
sudo apt install android-sdk

# macOS
brew install android-sdk

# Set ANDROID_HOME
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

#### 4. Buildozer

```bash
# Install Buildozer
pip3 install --user buildozer

# Install Cython (required)
pip3 install --user cython

# Add to PATH
export PATH=$PATH:$HOME/.local/bin

# Verify installation
buildozer --version
```

#### 5. System Dependencies (Linux only)

```bash
# Ubuntu/Debian - Install all build dependencies
sudo apt update
sudo apt install -y \
    build-essential \
    git \
    python3-dev \
    ffmpeg \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev \
    libgstreamer1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

# Additional dependencies for 64-bit
sudo apt install -y \
    libncurses5:i386 \
    libc6:i386 \
    libstdc++6:i386 \
    lib32gcc1 \
    lib32ncurses5 \
    lib32z1 \
    libbz2-1.0:i386
```

```bash
# macOS - Install dependencies with Homebrew
brew install \
    sdl2 \
    sdl2_image \
    sdl2_ttf \
    sdl2_mixer \
    gstreamer
```

---

## Quick Start

### Automated Build (Recommended)

```bash
# 1. Navigate to android directory
cd path/to/SolanaMemeCoin_bot/android

# 2. Make script executable (if not already)
chmod +x build_apk.sh

# 3. Run build script
./build_apk.sh
```

**What the script does:**
1. ✅ Checks all prerequisites
2. ✅ Installs system dependencies (Linux)
3. ✅ Sets up Python environment
4. ✅ Cleans previous builds
5. ✅ Builds debug APK with Buildozer
6. ✅ Optionally builds release APK
7. ✅ Creates distribution package

**First Build Time:** 20-40 minutes (downloads SDK/NDK)
**Subsequent Builds:** 2-5 minutes

**Output Files:**
```
android/
├── bin/
│   ├── SolanaTradingBot-1.0.0-debug.apk     # Debug APK (~30-50 MB)
│   └── SolanaTradingBot-1.0.0-release.apk   # Release APK (optional)
└── dist/
    └── SolanaTradingBot-Android-v1.0.0-YYYYMMDD.zip  # Distribution package
```

---

## Manual Build Steps

If you prefer manual control or the automated script fails:

### Step 1: Initialize Buildozer

```bash
# Navigate to android directory
cd path/to/SolanaMemeCoin_bot/android

# Initialize buildozer.spec (if not exists)
buildozer init

# A buildozer.spec file already exists, so skip this step
```

### Step 2: Configure buildozer.spec

The `buildozer.spec` file is already configured. Key settings:

```ini
[app]
title = Solana Trading Bot Pro
package.name = solanabot
package.domain = com.solanatradingbot
source.dir = ./app
source.main = main.py
version = 1.0.0

# Requirements
requirements = python3,kivy==2.2.1,websockets,asyncio,aiohttp,requests

# Android settings
android.api = 33
android.minapi = 21  # Android 5.0+
android.ndk = 25b
android.sdk = 33

# Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK

# Architectures
android.archs = arm64-v8a,armeabi-v7a
```

### Step 3: Clean Previous Builds (Optional)

```bash
# Remove previous build artifacts
rm -rf .buildozer bin

# This forces a clean build
```

### Step 4: Build Debug APK

```bash
# Build debug APK
buildozer android debug

# This will:
# 1. Download Android SDK/NDK (first time only - ~2GB)
# 2. Download Python-for-Android
# 3. Compile Python and dependencies
# 4. Package into APK
# 5. Output: bin/SolanaTradingBot-1.0.0-debug.apk
```

**First build:** 20-40 minutes
**Subsequent builds:** 2-5 minutes

### Step 5: Verify APK

```bash
# Check APK was created
ls -lh bin/*.apk

# Expected output:
# SolanaTradingBot-1.0.0-debug.apk  (~30-50 MB)
```

### Step 6: Build Release APK (Optional)

For production/Play Store deployment:

```bash
# 1. Create keystore (first time only)
keytool -genkey -v \
    -keystore ~/.android/release.keystore \
    -alias solanabotkey \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000

# Follow prompts to set password and details

# 2. Build release APK
buildozer android release

# 3. Sign APK manually (if Buildozer doesn't auto-sign)
jarsigner -verbose \
    -sigalg SHA256withRSA \
    -digestalg SHA-256 \
    -keystore ~/.android/release.keystore \
    bin/SolanaTradingBot-1.0.0-release-unsigned.apk \
    solanabotkey

# 4. Align APK
zipalign -v 4 \
    bin/SolanaTradingBot-1.0.0-release-unsigned.apk \
    bin/SolanaTradingBot-1.0.0-release.apk

# Output: bin/SolanaTradingBot-1.0.0-release.apk
```

---

## Testing on Device

### Method 1: USB Debugging (Recommended)

#### Enable USB Debugging on Android

1. Go to **Settings** → **About Phone**
2. Tap **Build Number** 7 times (enables Developer Mode)
3. Go to **Settings** → **Developer Options**
4. Enable **USB Debugging**
5. Connect device to computer via USB

#### Install via ADB

```bash
# Install Android Debug Bridge
sudo apt install adb  # Ubuntu/Debian
brew install android-platform-tools  # macOS

# Verify device is connected
adb devices
# Should show: List of devices attached
#              XXXXXXXXXXXXXX  device

# Install APK
adb install bin/SolanaTradingBot-1.0.0-debug.apk

# Launch app
adb shell am start -n com.solanatradingbot.solanabot/.MainActivity

# View logs in real-time
adb logcat | grep python
```

### Method 2: Direct Install

```bash
# 1. Transfer APK to device
# - Email to yourself
# - Upload to Google Drive
# - Use USB file transfer
# - Use adb push: adb push bin/*.apk /sdcard/Download/

# 2. On Android device:
# - Settings → Security → Unknown Sources (Enable)
# - File Manager → Downloads
# - Tap APK file
# - Tap "Install"
```

### Method 3: Buildozer Deploy

```bash
# Deploy directly to connected device
buildozer android debug deploy run

# This builds, installs, and launches the app
```

---

## Troubleshooting

### Build Errors

#### Error: "Command failed: python-for-android ..."

**Cause:** Missing system dependencies

**Solution (Ubuntu/Debian):**
```bash
sudo apt install -y \
    build-essential \
    git \
    python3-dev \
    ffmpeg \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libswscale-dev \
    libavformat-dev \
    libavcodec-dev \
    zlib1g-dev
```

#### Error: "JAVA_HOME is not set"

**Solution:**
```bash
# Find Java installation
sudo update-alternatives --config java

# Set JAVA_HOME (Ubuntu/Debian)
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Set JAVA_HOME (macOS)
export JAVA_HOME=$(/usr/libexec/java_home -v 11)

# Add to ~/.bashrc for persistence
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

#### Error: "Android SDK not found"

**Solution:**
```bash
# Let Buildozer download SDK automatically
buildozer android debug

# Or set ANDROID_HOME manually
export ANDROID_HOME=$HOME/.buildozer/android/platform/android-sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools
```

#### Error: "NDK not found" or "NDK version mismatch"

**Solution:**
```bash
# Clean and rebuild
buildozer android clean
buildozer android debug

# Or specify NDK version in buildozer.spec
android.ndk = 25b
```

#### Error: "Build failed with exit code 1"

**Solution:**
```bash
# Enable verbose logging
buildozer -v android debug

# Check logs in .buildozer/android/platform/build-*/

# Common fixes:
# 1. Update Buildozer
pip3 install --upgrade buildozer

# 2. Clear cache
rm -rf .buildozer ~/.buildozer

# 3. Update Cython
pip3 install --upgrade cython
```

### Runtime Errors

#### App crashes on startup

**Debug Steps:**
```bash
# 1. View crash logs
adb logcat | grep -i error

# 2. Check Python errors
adb logcat | grep python

# 3. Common causes:
# - Missing permissions in AndroidManifest.xml
# - Import errors (missing requirements)
# - Network connectivity issues
```

#### "Permission denied" errors

**Solution:**
```ini
# Add required permissions in buildozer.spec
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,WRITE_EXTERNAL_STORAGE
```

#### WebSocket connection fails

**Cause:** Android Network Security Policy

**Solution:**
```xml
<!-- Add to android/app/res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
```

```ini
# Reference in buildozer.spec
android.manifest.application = networkSecurityConfig="@xml/network_security_config"
```

### Performance Issues

#### High battery drain

**Solutions:**
```python
# Optimize update frequency
self.update_interval = 5  # seconds instead of 1

# Use wake lock wisely
android.permissions = WAKE_LOCK  # Only if needed

# Disable when app in background
def on_pause(self):
    self.stop_updates()
    return True
```

#### Slow UI / Lag

**Solutions:**
```python
# Run network calls in threads
from threading import Thread

def update_data(self):
    Thread(target=self.fetch_data).start()

# Use RecycleView for lists
from kivy.uix.recycleview import RecycleView
```

---

## Play Store Deployment

### Preparing for Release

#### 1. Update Version

```ini
# In buildozer.spec
version = 1.0.0
version.code = 1  # Increment for each release
```

#### 2. Create Signing Key

```bash
# Generate release keystore
keytool -genkey -v \
    -keystore ~/solanabotkey.jks \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -alias solanabotkey

# IMPORTANT: Store password and details securely!
```

#### 3. Build Signed APK

```bash
# Build release APK
buildozer android release

# Or configure auto-signing in buildozer.spec
android.release_artifact = aab  # Use AAB for Play Store
```

#### 4. Create App Bundle (AAB)

Play Store prefers AAB over APK:

```ini
# In buildozer.spec
android.release_artifact = aab

# Build
buildozer android release
```

### Play Store Submission

#### 1. Create Developer Account

- Go to: https://play.google.com/console
- Pay $25 one-time registration fee
- Complete account verification

#### 2. Create App Listing

**Required Assets:**
- **Icon:** 512x512 PNG (in `resources/icons/app-icon.png`)
- **Feature Graphic:** 1024x500 PNG
- **Screenshots:** At least 2, max 8 (JPEG or PNG)
  - Phone: 16:9 or 9:16 ratio
  - Tablet: Optional
- **Privacy Policy:** Required (host on website)
- **App Description:** Max 4000 characters

#### 3. Fill App Details

```
App name: Solana Trading Bot Pro
Short description: AI-powered Solana memecoin trading bot
Full description: [See COMMERCIAL_PRODUCT.md]
Category: Finance
Content rating: Mature 17+ (Gambling themes)
Pricing: Free (or Paid: $4.99)
In-app purchases: Yes (Premium features)
```

#### 4. Upload APK/AAB

```bash
# Upload your signed release APK or AAB
# File: bin/SolanaTradingBot-1.0.0-release.aab

# Or use Google Play Console to upload manually
```

#### 5. Content Rating

Complete questionnaire:
- Select "Finance" app category
- Answer questions about trading/gambling
- Submit for rating

#### 6. Pricing & Distribution

```
Countries: All (or select specific countries)
Pricing: Free or $4.99
In-app purchases: $9.99/month subscription
Ads: No
```

#### 7. Submit for Review

- Review all details
- Submit app for review
- Typical review time: 2-7 days

---

## Advanced Configuration

### Customize App

#### Change Package Name

```ini
# In buildozer.spec
package.name = mysolanabot
package.domain = com.mydomain
```

#### Add Splash Screen

```ini
# In buildozer.spec
presplash.filename = resources/icons/presplash.png

# Create 512x512 PNG image
```

#### Change App Theme

```python
# In app/main.py
from kivy.utils import get_color_from_hex

class MyApp(App):
    def build(self):
        # Set primary color
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Dark"
```

#### Add Background Service

```ini
# In buildozer.spec
services = background:service.py

# Create app/service.py with background logic
```

### Optimize Build

#### Reduce APK Size

```ini
# In buildozer.spec

# Only include needed architectures
android.archs = arm64-v8a  # Remove armeabi-v7a

# Exclude unused libraries
requirements = python3,kivy==2.2.1,websockets
# Remove: matplotlib,numpy,scipy if not used
```

**Size reduction:** 50MB → 30MB typical

#### Faster Builds

```bash
# Use ccache for faster C compilation
sudo apt install ccache
export USE_CCACHE=1

# Build with multiple jobs
buildozer android debug -j 4
```

### Testing

#### Automated Testing

```bash
# Unit tests
python -m pytest app/tests/

# UI tests with Kivy
python app/main.py --test

# Integration tests
adb shell am instrument -w com.solanatradingbot.solanabot.test
```

#### Beta Testing

1. Create **Closed Testing** track in Play Console
2. Add beta testers (email addresses)
3. Upload beta APK
4. Share beta testing link

---

## Build Automation

### CI/CD with GitHub Actions

```yaml
# .github/workflows/build-android.yml
name: Build Android APK

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        sudo apt update
        sudo apt install -y build-essential git python3-dev \
          libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev

    - name: Install Buildozer
      run: |
        pip install buildozer cython

    - name: Build APK
      run: |
        cd android
        buildozer android debug

    - name: Upload APK
      uses: actions/upload-artifact@v3
      with:
        name: android-apk
        path: android/bin/*.apk
```

---

## Support & Resources

### Documentation
- [Main README](../README.md)
- [Android README](README.md)
- [Buildozer Docs](https://buildozer.readthedocs.io/)
- [Kivy Docs](https://kivy.org/doc/stable/)

### Tools
- **Buildozer:** https://github.com/kivy/buildozer
- **Python-for-Android:** https://github.com/kivy/python-for-android
- **Android Studio:** https://developer.android.com/studio

### Community
- **GitHub Issues:** https://github.com/0xxCool/SolanaMemeCoin_bot/issues
- **Kivy Discord:** https://chat.kivy.org/
- **Email:** support@solanatradingbot.com

---

## Appendix

### File Structure

```
android/
├── app/
│   ├── main.py                 # Main application entry
│   ├── screens/                # App screens
│   │   ├── dashboard.py
│   │   ├── settings.py
│   │   └── positions.py
│   ├── widgets/                # Custom widgets
│   └── utils/                  # Utility functions
├── resources/
│   ├── icons/
│   │   ├── app-icon.png        # App icon (512x512)
│   │   └── presplash.png       # Splash screen
│   └── fonts/                  # Custom fonts
├── buildozer/                  # Build scripts
├── docs/                       # Documentation
├── build_apk.sh                # Automated build script
├── BUILD_GUIDE.md              # This file
├── README.md                   # Android app docs
└── buildozer.spec              # Buildozer configuration
```

### Common Commands Reference

```bash
# Initialize Buildozer
buildozer init

# Build debug APK
buildozer android debug

# Build release APK
buildozer android release

# Deploy to connected device
buildozer android debug deploy run

# Clean build
buildozer android clean

# Verbose build
buildozer -v android debug

# Update dependencies
buildozer android update

# List available targets
buildozer --help
```

### Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc

# Java
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PATH=$PATH:$JAVA_HOME/bin

# Android SDK
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/tools:$ANDROID_HOME/platform-tools

# Android NDK (if manually installed)
export ANDROID_NDK_HOME=$ANDROID_HOME/ndk/25.1.8937393

# Buildozer
export PATH=$PATH:$HOME/.local/bin

# Apply changes
source ~/.bashrc
```

---

**Last Updated:** 2024-10-23
**Version:** 1.0.0
**Build Script Version:** 1.0.0

---

💡 **Tip:** First build takes 20-40 minutes. Be patient! Subsequent builds are much faster (2-5 min).

🎉 **Success?** Test thoroughly on multiple devices before Play Store submission!
