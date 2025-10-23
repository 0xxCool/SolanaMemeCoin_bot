#!/bin/bash
# ===================================================
# Solana Trading Bot - Android APK Build Script
# Automated build script for creating Android APK
# ===================================================

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function print_success { echo -e "${GREEN}$1${NC}"; }
function print_info { echo -e "${CYAN}$1${NC}"; }
function print_warning { echo -e "${YELLOW}$1${NC}"; }
function print_error { echo -e "${RED}$1${NC}"; }

print_info "======================================"
print_info "Solana Trading Bot - APK Builder"
print_info "======================================"
echo ""

# ===================================================
# 1. Prerequisites Check
# ===================================================
print_info "[1/8] Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "✓ Python found: $PYTHON_VERSION"
else
    print_error "✗ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    print_success "✓ pip3 found"
else
    print_error "✗ pip3 not found. Please install pip3"
    exit 1
fi

# Check buildozer
if command -v buildozer &> /dev/null; then
    print_success "✓ Buildozer found"
else
    print_warning "✗ Buildozer not found. Installing..."
    pip3 install --user buildozer cython
    export PATH="$HOME/.local/bin:$PATH"
fi

# Check Java JDK
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
    print_success "✓ Java JDK found: $JAVA_VERSION"
else
    print_warning "✗ Java JDK not found"
    print_info "Install with: sudo apt-get install openjdk-11-jdk (Ubuntu/Debian)"
    print_info "Or download from: https://adoptium.net/"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Android SDK
if [ -z "$ANDROID_HOME" ]; then
    print_warning "✗ ANDROID_HOME not set"
    print_info "Buildozer will download Android SDK automatically"
    print_info "Or set manually: export ANDROID_HOME=/path/to/android-sdk"
else
    print_success "✓ ANDROID_HOME: $ANDROID_HOME"
fi

# Check available disk space (need ~5GB)
AVAILABLE_SPACE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE_SPACE" -lt 5 ]; then
    print_warning "⚠ Low disk space: ${AVAILABLE_SPACE}GB available (5GB+ recommended)"
fi

# ===================================================
# 2. Install System Dependencies (Linux only)
# ===================================================
print_info ""
print_info "[2/8] Checking system dependencies..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    print_info "Detected Linux. Checking required packages..."

    REQUIRED_PACKAGES=(
        "build-essential"
        "git"
        "python3-dev"
        "ffmpeg"
        "libsdl2-dev"
        "libsdl2-image-dev"
        "libsdl2-mixer-dev"
        "libsdl2-ttf-dev"
        "libportmidi-dev"
        "libswscale-dev"
        "libavformat-dev"
        "libavcodec-dev"
        "zlib1g-dev"
    )

    MISSING_PACKAGES=()
    for pkg in "${REQUIRED_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii  $pkg"; then
            MISSING_PACKAGES+=("$pkg")
        fi
    done

    if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
        print_warning "Missing packages: ${MISSING_PACKAGES[*]}"
        print_info "Install with: sudo apt-get install ${MISSING_PACKAGES[*]}"
        read -p "Install now? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo apt-get update
            sudo apt-get install -y "${MISSING_PACKAGES[@]}"
        fi
    else
        print_success "✓ All system dependencies found"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    print_info "Detected macOS. Install dependencies with Homebrew if needed:"
    print_info "  brew install python3 sdl2 sdl2_image sdl2_ttf sdl2_mixer"
fi

# ===================================================
# 3. Setup Python Environment
# ===================================================
print_info ""
print_info "[3/8] Setting up Python environment..."

# Install Python dependencies
pip3 install --user --upgrade pip setuptools wheel
pip3 install --user buildozer cython

print_success "✓ Python environment ready"

# ===================================================
# 4. Clean Previous Builds
# ===================================================
print_info ""
print_info "[4/8] Cleaning previous builds..."

if [ -d ".buildozer" ]; then
    print_info "Removing .buildozer directory..."
    rm -rf .buildozer
fi

if [ -d "bin" ]; then
    print_info "Removing bin directory..."
    rm -rf bin
fi

print_success "✓ Build directories cleaned"

# ===================================================
# 5. Verify buildozer.spec
# ===================================================
print_info ""
print_info "[5/8] Verifying buildozer.spec..."

if [ ! -f "buildozer.spec" ]; then
    print_error "✗ buildozer.spec not found!"
    print_info "Creating default buildozer.spec..."
    buildozer init
fi

# Update version with timestamp
BUILD_DATE=$(date +%Y%m%d)
sed -i "s/^version =.*/version = 1.0.0/" buildozer.spec

print_success "✓ buildozer.spec verified"

# ===================================================
# 6. Build Debug APK
# ===================================================
print_info ""
print_info "[6/8] Building debug APK..."
print_warning "This may take 15-30 minutes on first build (downloads Android SDK/NDK)"
print_info ""

# Build with buildozer
buildozer android debug

if [ $? -ne 0 ]; then
    print_error "✗ Build failed!"
    print_info "Check logs above for errors"
    exit 1
fi

# Find generated APK
APK_FILE=$(find bin -name "*.apk" -type f | head -n 1)

if [ -z "$APK_FILE" ]; then
    print_error "✗ APK file not found in bin/ directory"
    exit 1
fi

APK_SIZE=$(du -h "$APK_FILE" | cut -f1)
print_success "✓ Debug APK built: $APK_FILE"
print_info "  Size: $APK_SIZE"

# ===================================================
# 7. Build Release APK (Optional)
# ===================================================
print_info ""
print_info "[7/8] Build release APK?"
print_warning "Release APK requires signing with a keystore"
read -p "Build release APK? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Building release APK..."

    # Check for keystore
    KEYSTORE_FILE="$HOME/.android/release.keystore"
    if [ ! -f "$KEYSTORE_FILE" ]; then
        print_warning "Keystore not found: $KEYSTORE_FILE"
        print_info "Creating new keystore..."

        mkdir -p "$HOME/.android"
        keytool -genkey -v \
            -keystore "$KEYSTORE_FILE" \
            -alias solanabotkey \
            -keyalg RSA \
            -keysize 2048 \
            -validity 10000

        if [ $? -ne 0 ]; then
            print_error "✗ Failed to create keystore"
            print_warning "Skipping release build"
        else
            print_success "✓ Keystore created"
        fi
    fi

    if [ -f "$KEYSTORE_FILE" ]; then
        # Build release
        buildozer android release

        # Find release APK
        RELEASE_APK=$(find bin -name "*-release*.apk" -type f | head -n 1)

        if [ -n "$RELEASE_APK" ]; then
            RELEASE_SIZE=$(du -h "$RELEASE_APK" | cut -f1)
            print_success "✓ Release APK built: $RELEASE_APK"
            print_info "  Size: $RELEASE_SIZE"
        else
            print_warning "⚠ Release APK not found (may need manual signing)"
        fi
    fi
else
    print_info "Skipping release build"
fi

# ===================================================
# 8. Create Distribution Package
# ===================================================
print_info ""
print_info "[8/8] Creating distribution package..."

# Create distribution directory
DIST_DIR="dist/distribution"
mkdir -p "$DIST_DIR"

# Copy APK files
cp bin/*.apk "$DIST_DIR/" 2>/dev/null || print_warning "No APK files to copy"

# Copy documentation
cp README.md "$DIST_DIR/" 2>/dev/null || true
cp BUILD_GUIDE.md "$DIST_DIR/" 2>/dev/null || true

# Create installation instructions
cat > "$DIST_DIR/INSTALL.txt" << 'EOF'
# Solana Trading Bot - Android Distribution

## Installation

### Option 1: Direct Install (Easiest)
1. Transfer APK to your Android device
2. Enable "Install from Unknown Sources" in Settings
3. Tap the APK file to install
4. Open app and configure

### Option 2: ADB Install (Advanced)
```bash
# Install via USB debugging
adb install SolanaTradingBot-*.apk
```

## Requirements
- Android 5.0 (Lollipop) or higher
- 2GB RAM minimum
- 100MB storage
- Internet connection

## Configuration
1. Open app
2. Go to Settings
3. Enter sync server URL (your PC's IP:8765)
4. Configure trading parameters
5. Enable notifications

## Testing on Device
```bash
# Install and run logs
adb install bin/SolanaTradingBot-*.apk
adb logcat | grep python
```

## Support
- Documentation: See README.md
- Issues: https://github.com/0xxCool/SolanaMemeCoin_bot/issues

EOF

# Create ZIP archive
ZIP_NAME="SolanaTradingBot-Android-v1.0.0-$(date +%Y%m%d).zip"
cd dist
zip -r "$ZIP_NAME" distribution/
cd ..

print_success "✓ Distribution package created: dist/$ZIP_NAME"

# ===================================================
# Build Complete
# ===================================================
print_info ""
print_success "======================================"
print_success "Build completed successfully!"
print_success "======================================"
print_info ""
print_info "Output files:"
print_info "  • Debug APK:    $APK_FILE"
[ -n "$RELEASE_APK" ] && print_info "  • Release APK:  $RELEASE_APK"
print_info "  • Distribution: dist/$ZIP_NAME"
print_info ""
print_info "Next steps:"
print_info "  1. Test on Android device:"
print_info "     adb install $APK_FILE"
print_info ""
print_info "  2. Install on phone:"
print_info "     - Transfer APK to device"
print_info "     - Enable 'Unknown Sources'"
print_info "     - Install and test"
print_info ""
print_info "  3. For Play Store:"
print_info "     - Use the release APK"
print_info "     - Sign with production keystore"
print_info "     - Upload to Play Console"
print_info ""
print_success "Happy mobile trading! 📱🚀"
