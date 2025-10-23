# 📱 Android Distribution Directory

This directory contains the built distribution files for the Android Mobile Application.

## 📦 Build Output Files

After running `build_apk.sh`, the following files will appear here:

### Debug APK
- **SolanaTradingBot-1.0.0-debug.apk** - Debug build
  - Size: ~30-50 MB
  - For testing and development
  - Signed with debug keystore
  - Can be installed directly

### Release APK
- **SolanaTradingBot-1.0.0-release.apk** - Production build
  - Size: ~30-50 MB
  - For Google Play Store or direct distribution
  - Must be signed with production keystore
  - Optimized and minified

### Distribution Package
- **SolanaTradingBot-Android-v1.0.0-YYYYMMDD.zip** - Complete distribution
  - Contains APK files
  - Includes documentation
  - Installation instructions
  - Ready for deployment

## 🚀 How to Build

Run the automated build script:

```bash
cd android
./build_apk.sh
```

Or follow the manual steps in [BUILD_GUIDE.md](../BUILD_GUIDE.md)

## 📝 Requirements

**Build Requirements:**
- Ubuntu/Debian Linux or macOS
- Python 3.10+
- Java JDK 11 or 17
- Buildozer
- Android SDK/NDK (auto-downloaded)
- 10GB free disk space

**Runtime Requirements:**
- Android 5.0 (Lollipop) or higher
- 2GB RAM minimum
- 100MB storage
- Internet connection

## ✅ Distribution Checklist

Before distributing, ensure:
- [ ] APK installs on test devices
- [ ] All features work correctly
- [ ] No crashes on startup
- [ ] Network permissions granted
- [ ] Signed with production keystore (for Play Store)
- [ ] Version code incremented
- [ ] Screenshots and assets prepared

## 📊 File Sizes

Typical APK sizes:
- **Debug APK:** ~40-50 MB (unoptimized)
- **Release APK:** ~30-40 MB (optimized)
- **AAB (App Bundle):** ~25-35 MB (for Play Store)

Size by architecture:
- **arm64-v8a only:** ~20 MB
- **armeabi-v7a only:** ~18 MB
- **Both architectures:** ~38 MB

## 🔒 Security

**Production Signing:**

```bash
# Create keystore (first time only)
keytool -genkey -v \
    -keystore ~/solanabotkey.jks \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -alias solanabotkey

# Sign APK
jarsigner -verbose \
    -sigalg SHA256withRSA \
    -digestalg SHA-256 \
    -keystore ~/solanabotkey.jks \
    SolanaTradingBot-1.0.0-release-unsigned.apk \
    solanabotkey

# Align APK
zipalign -v 4 \
    SolanaTradingBot-1.0.0-release-unsigned.apk \
    SolanaTradingBot-1.0.0-release.apk
```

**IMPORTANT:** Keep your keystore file and password secure! Loss of keystore means you cannot update your app on Play Store.

## 📤 Deployment

### Google Play Store

1. **Create App Bundle (AAB):**
```bash
# Configure buildozer.spec
android.release_artifact = aab

# Build
buildozer android release
```

2. **Upload to Play Console:**
   - Go to https://play.google.com/console
   - Create new app
   - Upload AAB file
   - Fill in store listing
   - Submit for review

### Direct Distribution

Upload APK to your website:
```html
<a href="downloads/SolanaTradingBot-release.apk">
  Download for Android
</a>
```

**Users must enable "Install from Unknown Sources"**

### Beta Testing

1. Create closed/open testing track in Play Console
2. Upload beta APK
3. Add testers (email addresses)
4. Share testing link

## 📱 Installation Methods

### Method 1: ADB Install (Development)
```bash
adb install SolanaTradingBot-1.0.0-debug.apk
```

### Method 2: Direct Install (End Users)
1. Transfer APK to device
2. Enable "Unknown Sources" in Settings
3. Tap APK file to install

### Method 3: Play Store (Production)
- Automatic updates
- Best for end users
- Requires developer account ($25 one-time)

## 🧪 Testing

**Test on multiple devices:**
- [ ] Phone (Android 5.0)
- [ ] Phone (Android 10+)
- [ ] Tablet (if supported)
- [ ] Different screen sizes

**Test scenarios:**
- [ ] Fresh install
- [ ] Update from previous version
- [ ] Different network conditions
- [ ] Background operation
- [ ] Battery optimization
- [ ] Notifications

## 🆘 Support

If builds fail or APK doesn't work:
1. Check [BUILD_GUIDE.md](../BUILD_GUIDE.md) troubleshooting section
2. Verify all prerequisites installed
3. Check build logs in `.buildozer/android/platform/build-*/`
4. Test with `adb logcat | grep python`
5. Open issue on GitHub

## 📏 APK Size Optimization

Reduce APK size:
1. **Single architecture builds:**
```ini
# In buildozer.spec
android.archs = arm64-v8a  # Remove armeabi-v7a
```

2. **Remove unused requirements:**
```ini
requirements = python3,kivy==2.2.1,websockets
# Remove: numpy,matplotlib if not used
```

3. **Use App Bundle (AAB):**
- Play Store delivers optimized APK per device
- Typical 30% size reduction

---

**Note:** This directory is created automatically by the build script. Do not commit built APK files to git (add to .gitignore).
