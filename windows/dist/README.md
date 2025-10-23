# 🪟 Windows Distribution Directory

This directory contains the built distribution files for the Windows Desktop Application.

## 📦 Build Output Files

After running `build_msi.ps1`, the following files will appear here:

### Executable
- **SolanaTradingBot.exe** - Standalone portable executable
  - Size: ~80-150 MB
  - No installation required
  - Can run directly from any location

### MSI Installer
- **SolanaTradingBot-Setup.msi** - Windows Installer package
  - Size: ~80-150 MB
  - Professional installation experience
  - Creates Start Menu shortcuts
  - Adds to Programs & Features
  - Includes uninstaller

### Distribution Package
- **SolanaTradingBot-Windows-v1.0.0-YYYYMMDD.zip** - Complete distribution
  - Contains both EXE and MSI
  - Includes documentation
  - Ready for deployment

## 🚀 How to Build

Run the automated build script:

```powershell
cd windows
.\build_msi.ps1
```

Or follow the manual steps in [BUILD_GUIDE.md](../BUILD_GUIDE.md)

## 📝 Requirements

**Build Requirements:**
- Python 3.10+
- PyInstaller
- WiX Toolset 3.11+
- Windows 10/11

**Runtime Requirements:**
- Windows 10 version 1809+ (64-bit)
- 4GB RAM minimum
- 500MB storage
- Internet connection

## ✅ Distribution Checklist

Before distributing, ensure:
- [ ] Executable runs without errors
- [ ] MSI installs and uninstalls cleanly
- [ ] All dependencies included
- [ ] No sensitive data (API keys, etc.)
- [ ] Documentation included
- [ ] Version numbers correct

## 📊 File Sizes

Typical sizes:
- **Debug build:** ~150 MB
- **Release build:** ~80 MB (with UPX compression)
- **MSI installer:** Same as executable + 5-10 MB overhead

## 🔒 Security

**Code Signing (Recommended for production):**

```powershell
# Sign executable
signtool sign /f certificate.pfx /p password SolanaTradingBot.exe

# Sign MSI
signtool sign /f certificate.pfx /p password SolanaTradingBot-Setup.msi
```

## 📤 Deployment

### GitHub Releases
```powershell
gh release create v1.0.0 *.zip --title "Version 1.0.0"
```

### Direct Download
Upload to your website:
- MSI: For typical users
- EXE: For advanced users / portable use
- ZIP: Complete package

## 🆘 Support

If builds fail or files are missing:
1. Check [BUILD_GUIDE.md](../BUILD_GUIDE.md) troubleshooting section
2. Verify all prerequisites installed
3. Check build logs in `build/` directory
4. Open issue on GitHub

---

**Note:** This directory is created automatically by the build script. Do not commit built files to git.
