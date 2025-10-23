# 🏗️ Windows Desktop Application - Complete Build Guide

**Comprehensive guide for building the Solana Trading Bot Windows MSI installer**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Manual Build Steps](#manual-build-steps)
4. [Troubleshooting](#troubleshooting)
5. [Advanced Configuration](#advanced-configuration)
6. [Distribution](#distribution)

---

## Prerequisites

### Required Software

#### 1. Python 3.10 or Higher

```powershell
# Check Python version
python --version

# Should output: Python 3.10.x or higher
```

**Install Python:**
- Download from: https://www.python.org/downloads/
- During installation:
  - ✅ Check "Add Python to PATH"
  - ✅ Check "Install pip"
  - Choose "Customize installation"
  - ✅ Check "Add Python to environment variables"

#### 2. PyInstaller

```powershell
# Install PyInstaller
pip install pyinstaller

# Verify installation
pyinstaller --version
```

#### 3. WiX Toolset v3.11+

**Option A: Direct Download**
- Download from: https://wixtoolset.org/
- Run installer: `wix311.exe`
- Default install path: `C:\Program Files (x86)\WiX Toolset v3.11\`

**Option B: Package Manager**
```powershell
# Using winget (Windows 11 / Windows 10 with App Installer)
winget install -e --id WiX.Toolset

# Using chocolatey
choco install wixtoolset
```

**Verify Installation:**
```powershell
# Check if WiX is accessible
& "C:\Program Files (x86)\WiX Toolset v3.11\bin\candle.exe" -?
```

#### 4. Git (Optional)

Only needed if cloning from repository.

```powershell
# Install Git
winget install -e --id Git.Git

# Or download from: https://git-scm.com/download/win
```

### System Requirements

- **OS:** Windows 10 version 1809+ or Windows 11
- **RAM:** 8GB minimum (16GB recommended)
- **Storage:** 2GB free space for build tools + 500MB for build
- **CPU:** Any modern x64 processor

---

## Quick Start

### Automated Build (Recommended)

The automated PowerShell script handles everything:

```powershell
# 1. Open PowerShell as Administrator
# Right-click Start → Windows PowerShell (Admin)

# 2. Navigate to windows directory
cd path\to\SolanaMemeCoin_bot\windows

# 3. Enable script execution (if needed)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Run build script
.\build_msi.ps1
```

**What the script does:**
1. ✅ Checks all prerequisites
2. ✅ Creates virtual environment
3. ✅ Installs dependencies
4. ✅ Builds executable with PyInstaller
5. ✅ Creates MSI installer with WiX
6. ✅ Packages everything for distribution

**Build Time:** 5-10 minutes

**Output Files:**
```
windows/
├── dist/
│   ├── SolanaTradingBot.exe          # Standalone executable
│   ├── SolanaTradingBot-Setup.msi    # MSI installer
│   └── SolanaTradingBot-Windows-v1.0.0-YYYYMMDD.zip  # Distribution package
```

---

## Manual Build Steps

If you prefer manual control or the automated script fails:

### Step 1: Setup Environment

```powershell
# 1. Clone repository (if not already done)
git clone https://github.com/0xxCool/SolanaMemeCoin_bot.git
cd SolanaMemeCoin_bot\windows

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 4. Upgrade pip
python -m pip install --upgrade pip
```

### Step 2: Install Dependencies

```powershell
# Install all required packages
pip install -r requirements.txt

# This installs:
# - PyQt6 (GUI framework)
# - FastAPI (API server)
# - websockets (real-time sync)
# - solana (blockchain integration)
# - And 20+ other dependencies
```

**Expected installation time:** 2-3 minutes

### Step 3: Build Executable with PyInstaller

```powershell
# Build using spec file
pyinstaller SolanaTradingBot.spec

# Or build with inline options:
pyinstaller `
  --name="SolanaTradingBot" `
  --windowed `
  --onefile `
  --icon=resources/icons/app.ico `
  --add-data="resources;resources" `
  --add-data="../config.py;." `
  --add-data="../trader.py;." `
  --add-data="../scanner.py;." `
  --add-data="../analyzer.py;." `
  --add-data="../integration.py;." `
  --add-data="../ai_engine.py;." `
  --add-data="../auto_trader.py;." `
  --hidden-import=PyQt6.QtCore `
  --hidden-import=PyQt6.QtGui `
  --hidden-import=PyQt6.QtWidgets `
  gui/main_window.py
```

**Build time:** 3-5 minutes

**Output:** `dist\SolanaTradingBot.exe` (~80-150 MB)

### Step 4: Test Executable

```powershell
# Test if executable runs
.\dist\SolanaTradingBot.exe

# Should launch GUI window
# Press Ctrl+C to close
```

**Common issues:**
- Missing DLL errors → Reinstall dependencies
- Python not found → Use `--onefile` option
- GUI doesn't appear → Check `--windowed` flag

### Step 5: Create MSI Installer

```powershell
# 1. Navigate to WiX directory
cd installer\wix

# 2. Compile WiX source
& "C:\Program Files (x86)\WiX Toolset v3.11\bin\candle.exe" SolanaTradingBot.wxs

# 3. Link to create MSI
& "C:\Program Files (x86)\WiX Toolset v3.11\bin\light.exe" `
  -out SolanaTradingBot-Setup.msi `
  SolanaTradingBot.wixobj `
  -ext WixUIExtension

# 4. Copy to dist folder
Copy-Item SolanaTradingBot-Setup.msi ..\..\dist\
```

**Output:** `dist\SolanaTradingBot-Setup.msi` (~80-150 MB)

### Step 6: Test MSI Installer

```powershell
# Install using MSI
Start-Process msiexec.exe -ArgumentList "/i dist\SolanaTradingBot-Setup.msi" -Wait

# Launch installed app
& "$env:ProgramFiles\Solana Trading Bot\SolanaTradingBot.exe"

# Uninstall (for testing)
Start-Process msiexec.exe -ArgumentList "/x dist\SolanaTradingBot-Setup.msi" -Wait
```

---

## Troubleshooting

### Build Issues

#### Issue: "PyInstaller: command not found"

**Solution:**
```powershell
# Install PyInstaller
pip install pyinstaller

# Or use python -m
python -m PyInstaller SolanaTradingBot.spec
```

#### Issue: "Failed to execute script" when running EXE

**Causes:**
1. Missing hidden imports
2. Data files not included
3. Antivirus blocking execution

**Solutions:**
```powershell
# 1. Add hidden imports to spec file
hiddenimports=['missing_module']

# 2. Include data files
datas=[('path/to/file', 'destination')]

# 3. Add Windows Defender exclusion
Add-MpPreference -ExclusionPath "C:\path\to\dist"
```

#### Issue: "WiX Toolset not found"

**Solution:**
```powershell
# Verify WiX installation
$wixPath = "C:\Program Files (x86)\WiX Toolset v3.11\bin"
Test-Path "$wixPath\candle.exe"

# If not found, reinstall WiX
winget install -e --id WiX.Toolset

# Or download from: https://wixtoolset.org/
```

#### Issue: "MSVCR120.dll missing"

**Solution:**
```powershell
# Install Visual C++ Redistributable
# Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

# Or include in MSI installer via WiX
```

### Runtime Issues

#### Issue: GUI doesn't start / Crashes immediately

**Debug Steps:**
```powershell
# 1. Run with console output (remove --windowed)
pyinstaller --console SolanaTradingBot.spec

# 2. Check logs
Get-Content bot.log -Tail 50

# 3. Test imports
python -c "from PyQt6.QtWidgets import QApplication; print('OK')"
```

#### Issue: "Could not find Qt platform plugin 'windows'"

**Solution:**
```powershell
# Include Qt plugins in spec file
datas=[
    ('venv/Lib/site-packages/PyQt6/Qt6/plugins', 'PyQt6/Qt6/plugins')
]
```

#### Issue: High CPU usage / Memory leaks

**Solution:**
```python
# Add to main_window.py
import gc
gc.enable()

# Periodic cleanup
QTimer.singleShot(60000, gc.collect)  # Every minute
```

### MSI Installer Issues

#### Issue: "This installation package could not be opened"

**Solution:**
```powershell
# MSI is corrupted, rebuild
cd installer\wix
Remove-Item *.wixobj, *.msi
# Rebuild with candle and light
```

#### Issue: Installation fails with error 2819

**Solution:**
```xml
<!-- In SolanaTradingBot.wxs, ensure proper directory structure -->
<Directory Id="TARGETDIR" Name="SourceDir">
  <Directory Id="ProgramFilesFolder">
    <Directory Id="INSTALLFOLDER" Name="Solana Trading Bot" />
  </Directory>
</Directory>
```

---

## Advanced Configuration

### Customizing Build

#### Change Application Icon

```powershell
# 1. Create/obtain .ico file (256x256 recommended)
# 2. Save to: resources/icons/app.ico
# 3. Update spec file:
icon='resources/icons/app.ico'
```

#### Include Additional Files

```python
# In SolanaTradingBot.spec
datas = [
    ('resources', 'resources'),
    ('additional_file.txt', '.'),
    ('config_folder', 'config'),
]
```

#### Optimize Executable Size

```python
# In spec file
excludes = [
    'tkinter',  # Not needed
    'matplotlib',  # If not used
    'IPython',  # Not needed
]

# Enable UPX compression
upx=True,
upx_exclude=[],
```

**Size reduction:** 150MB → 80MB typical

#### Code Signing (for production)

```powershell
# 1. Obtain code signing certificate
# Purchase from: DigiCert, Sectigo, etc.

# 2. Sign executable
& "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe" sign `
  /f "certificate.pfx" `
  /p "password" `
  /tr "http://timestamp.digicert.com" `
  /td SHA256 `
  /fd SHA256 `
  "dist\SolanaTradingBot.exe"

# 3. Sign MSI
signtool sign /f "certificate.pfx" /p "password" "dist\SolanaTradingBot-Setup.msi"
```

### Build Variants

#### Debug Build

```powershell
# With console for debugging
pyinstaller --console --debug=all SolanaTradingBot.spec
```

#### Portable Build

```python
# Create single-folder distribution instead of single-file
# In spec file, use COLLECT instead of EXE:

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='SolanaTradingBot'
)
```

#### Auto-Update Build

```python
# Add auto-update capability
# Include in gui/main_window.py:

def check_for_updates(self):
    url = "https://api.github.com/repos/0xxCool/SolanaMemeCoin_bot/releases/latest"
    # Implement update check logic
```

---

## Distribution

### Creating Distribution Package

```powershell
# 1. Build everything
.\build_msi.ps1

# 2. Package is created automatically:
# dist/SolanaTradingBot-Windows-v1.0.0-YYYYMMDD.zip

# 3. Contents:
# - SolanaTradingBot.exe (portable)
# - SolanaTradingBot-Setup.msi (installer)
# - README.md (documentation)
# - INSTALL.txt (quick start)
```

### Upload to GitHub Releases

```powershell
# Using GitHub CLI
gh release create v1.0.0 `
  dist/SolanaTradingBot-Windows-v1.0.0-*.zip `
  --title "Version 1.0.0" `
  --notes "Release notes here"
```

### Hosting on Website

```html
<a href="downloads/SolanaTradingBot-Setup.msi">
  Download for Windows (MSI Installer)
</a>

<a href="downloads/SolanaTradingBot.exe">
  Download Portable (EXE)
</a>
```

### System Requirements Document

```markdown
## System Requirements

**Minimum:**
- Windows 10 version 1809 (64-bit)
- 4GB RAM
- 500MB storage
- Internet connection

**Recommended:**
- Windows 11 (64-bit)
- 8GB RAM
- 1GB storage
- 10+ Mbps internet

**Software:**
- .NET Framework 4.7.2+ (usually pre-installed)
- Visual C++ Redistributable 2015-2022
```

---

## Build Automation

### CI/CD with GitHub Actions

```yaml
# .github/workflows/build-windows.yml
name: Build Windows Installer

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        cd windows
        pip install -r requirements.txt
        pip install pyinstaller

    - name: Build executable
      run: |
        cd windows
        pyinstaller SolanaTradingBot.spec

    - name: Setup WiX
      run: |
        choco install wixtoolset

    - name: Build MSI
      run: |
        cd windows/installer/wix
        & "C:\Program Files (x86)\WiX Toolset v3.11\bin\candle.exe" SolanaTradingBot.wxs
        & "C:\Program Files (x86)\WiX Toolset v3.11\bin\light.exe" -out SolanaTradingBot-Setup.msi SolanaTradingBot.wixobj -ext WixUIExtension

    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: windows-installer
        path: windows/dist/SolanaTradingBot-Setup.msi
```

---

## Support & Resources

### Documentation
- [Main README](../README.md)
- [Windows README](README.md)
- [API Documentation](docs/api.md)

### Tools
- **PyInstaller Docs:** https://pyinstaller.org/
- **WiX Toolset Docs:** https://wixtoolset.org/documentation/
- **PyQt6 Docs:** https://www.riverbankcomputing.com/static/Docs/PyQt6/

### Community
- **GitHub Issues:** https://github.com/0xxCool/SolanaMemeCoin_bot/issues
- **Discord:** [Join Server](#)
- **Email:** support@solanatradingbot.com

---

## Appendix

### File Structure

```
windows/
├── api/
│   └── sync_server.py          # WebSocket sync server
├── gui/
│   ├── main_window.py          # Main GUI application
│   ├── widgets/                # Custom widgets
│   └── styles/                 # QSS stylesheets
├── installer/
│   └── wix/
│       ├── SolanaTradingBot.wxs    # WiX installer definition
│       └── License.rtf             # License agreement
├── resources/
│   ├── icons/
│   │   ├── app.ico             # Application icon
│   │   └── tray.ico            # System tray icon
│   └── styles/
│       └── dark.qss            # Dark theme stylesheet
├── config/
│   └── default.ini             # Default configuration
├── docs/
│   ├── api.md                  # API documentation
│   └── development.md          # Development guide
├── build_msi.ps1               # Automated build script
├── BUILD_GUIDE.md              # This file
├── README.md                   # Windows app documentation
├── requirements.txt            # Python dependencies
└── SolanaTradingBot.spec       # PyInstaller specification
```

### Common Commands Reference

```powershell
# Build executable only
pyinstaller SolanaTradingBot.spec

# Build and test
.\build_msi.ps1
.\dist\SolanaTradingBot.exe

# Clean build
Remove-Item -Recurse -Force dist, build
pyinstaller SolanaTradingBot.spec

# Install MSI
msiexec /i dist\SolanaTradingBot-Setup.msi

# Uninstall MSI
msiexec /x dist\SolanaTradingBot-Setup.msi

# Silent install
msiexec /i dist\SolanaTradingBot-Setup.msi /quiet /norestart
```

---

**Last Updated:** 2024-10-23
**Version:** 1.0.0
**Build Script Version:** 1.0.0

---

💡 **Tip:** For faster builds, use SSD storage and exclude antivirus scanning of the build directory.

🎉 **Success?** Share your build experience and help improve this guide!
