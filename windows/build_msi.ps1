# ===================================================
# Solana Trading Bot - Windows MSI Build Script
# Automated build script for creating MSI installer
# ===================================================

# Error handling
$ErrorActionPreference = "Stop"

# Color output functions
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error-Custom { Write-Host $args -ForegroundColor Red }

Write-Info "======================================"
Write-Info "Solana Trading Bot - MSI Builder"
Write-Info "======================================"
Write-Info ""

# ===================================================
# 1. Prerequisites Check
# ===================================================
Write-Info "[1/7] Checking prerequisites..."

# Check Python
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.1[0-9]") {
        Write-Success "✓ Python found: $pythonVersion"
    } else {
        throw "Python 3.10+ required, found: $pythonVersion"
    }
} catch {
    Write-Error-Custom "✗ Python 3.10+ not found. Please install from https://python.org"
    exit 1
}

# Check PyInstaller
try {
    $pyinstallerVersion = pyinstaller --version 2>&1
    Write-Success "✓ PyInstaller found: $pyinstallerVersion"
} catch {
    Write-Warning "✗ PyInstaller not found. Installing..."
    pip install pyinstaller
}

# Check WiX Toolset
$wixPath = "${env:ProgramFiles(x86)}\WiX Toolset v3.11\bin"
if (-not (Test-Path "$wixPath\candle.exe")) {
    Write-Warning "✗ WiX Toolset not found at: $wixPath"
    Write-Info "Download from: https://wixtoolset.org/"
    Write-Info "Or install via: winget install -e --id WiX.Toolset"
    $continue = Read-Host "Continue without WiX? MSI won't be created (y/n)"
    if ($continue -ne "y") { exit 1 }
    $skipWix = $true
} else {
    Write-Success "✓ WiX Toolset found"
    $skipWix = $false
}

# ===================================================
# 2. Setup Virtual Environment
# ===================================================
Write-Info ""
Write-Info "[2/7] Setting up virtual environment..."

if (Test-Path ".\venv") {
    Write-Info "Using existing virtual environment"
} else {
    Write-Info "Creating virtual environment..."
    python -m venv venv
}

# Activate venv
& .\venv\Scripts\Activate.ps1
Write-Success "✓ Virtual environment activated"

# ===================================================
# 3. Install Dependencies
# ===================================================
Write-Info ""
Write-Info "[3/7] Installing dependencies..."

pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "✗ Failed to install dependencies"
    exit 1
}
Write-Success "✓ Dependencies installed"

# ===================================================
# 4. Build Executable with PyInstaller
# ===================================================
Write-Info ""
Write-Info "[4/7] Building executable with PyInstaller..."

# Clean previous builds
if (Test-Path ".\dist") { Remove-Item -Recurse -Force ".\dist" }
if (Test-Path ".\build") { Remove-Item -Recurse -Force ".\build" }

# Run PyInstaller
pyinstaller SolanaTradingBot.spec
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "✗ PyInstaller build failed"
    exit 1
}

# Verify executable exists
if (-not (Test-Path ".\dist\SolanaTradingBot.exe")) {
    Write-Error-Custom "✗ Executable not found: .\dist\SolanaTradingBot.exe"
    exit 1
}

Write-Success "✓ Executable built: .\dist\SolanaTradingBot.exe"

# Get file size
$exeSize = (Get-Item ".\dist\SolanaTradingBot.exe").Length / 1MB
Write-Info "  Size: $([math]::Round($exeSize, 2)) MB"

# ===================================================
# 5. Test Executable
# ===================================================
Write-Info ""
Write-Info "[5/7] Testing executable..."

Write-Info "Testing if executable runs (will timeout after 5 seconds)..."
$testJob = Start-Job -ScriptBlock {
    & "$using:PWD\dist\SolanaTradingBot.exe" --help 2>&1
}

Wait-Job $testJob -Timeout 5 | Out-Null
Stop-Job $testJob -ErrorAction SilentlyContinue
Remove-Job $testJob -ErrorAction SilentlyContinue

if (Test-Path ".\dist\SolanaTradingBot.exe") {
    Write-Success "✓ Executable appears to be valid"
} else {
    Write-Error-Custom "✗ Executable test failed"
    exit 1
}

# ===================================================
# 6. Create MSI Installer with WiX
# ===================================================
Write-Info ""
Write-Info "[6/7] Creating MSI installer..."

if ($skipWix) {
    Write-Warning "⊘ Skipping MSI creation (WiX not found)"
    Write-Info ""
    Write-Success "======================================"
    Write-Success "Build completed (without MSI)!"
    Write-Success "======================================"
    Write-Info "Executable: .\dist\SolanaTradingBot.exe"
    exit 0
}

# Add WiX to PATH for this session
$env:Path += ";$wixPath"

# Navigate to installer directory
Push-Location ".\installer\wix"

try {
    # Clean previous builds
    if (Test-Path ".\*.wixobj") { Remove-Item ".\*.wixobj" }
    if (Test-Path ".\*.msi") { Remove-Item ".\*.msi" }

    # Compile WiX source
    Write-Info "Compiling WiX source..."
    & "$wixPath\candle.exe" SolanaTradingBot.wxs
    if ($LASTEXITCODE -ne 0) {
        throw "WiX compilation failed"
    }

    # Link to create MSI
    Write-Info "Linking MSI..."
    & "$wixPath\light.exe" -out SolanaTradingBot-Setup.msi SolanaTradingBot.wixobj -ext WixUIExtension
    if ($LASTEXITCODE -ne 0) {
        throw "WiX linking failed"
    }

    # Verify MSI exists
    if (Test-Path ".\SolanaTradingBot-Setup.msi") {
        $msiSize = (Get-Item ".\SolanaTradingBot-Setup.msi").Length / 1MB
        Write-Success "✓ MSI created: .\installer\wix\SolanaTradingBot-Setup.msi"
        Write-Info "  Size: $([math]::Round($msiSize, 2)) MB"

        # Copy to dist folder
        Copy-Item ".\SolanaTradingBot-Setup.msi" "..\..\dist\"
        Write-Success "✓ MSI copied to: .\dist\SolanaTradingBot-Setup.msi"
    } else {
        throw "MSI file not created"
    }

} catch {
    Write-Error-Custom "✗ MSI creation failed: $_"
    Pop-Location
    exit 1
}

Pop-Location

# ===================================================
# 7. Create Distribution Package
# ===================================================
Write-Info ""
Write-Info "[7/7] Creating distribution package..."

# Create dist folder structure
New-Item -ItemType Directory -Force -Path ".\dist\distribution" | Out-Null

# Copy files
Copy-Item ".\dist\SolanaTradingBot.exe" ".\dist\distribution\"
Copy-Item ".\dist\SolanaTradingBot-Setup.msi" ".\dist\distribution\"
Copy-Item "..\README.md" ".\dist\distribution\"
Copy-Item ".\BUILD_GUIDE.md" ".\dist\distribution\" -ErrorAction SilentlyContinue

# Create README for distribution
$distReadme = @"
# Solana Trading Bot - Windows Distribution

## Quick Install

### Option 1: MSI Installer (Recommended)
1. Run ``SolanaTradingBot-Setup.msi``
2. Follow installation wizard
3. Launch from Start Menu

### Option 2: Portable Executable
1. Run ``SolanaTradingBot.exe`` directly
2. No installation required

## Requirements
- Windows 10/11 (64-bit)
- 4GB RAM minimum
- Internet connection

## Configuration
1. Create ``.env`` file with your settings
2. Or configure via GUI Settings panel

## Support
- Documentation: See README.md
- Issues: https://github.com/0xxCool/SolanaMemeCoin_bot/issues

Build Date: $(Get-Date -Format "yyyy-MM-dd HH:mm")
"@

$distReadme | Out-File -FilePath ".\dist\distribution\INSTALL.txt" -Encoding UTF8

# Create ZIP archive
Write-Info "Creating ZIP archive..."
$zipName = "SolanaTradingBot-Windows-v1.0.0-$(Get-Date -Format 'yyyyMMdd').zip"
Compress-Archive -Path ".\dist\distribution\*" -DestinationPath ".\dist\$zipName" -Force

Write-Success "✓ Distribution package created: .\dist\$zipName"

# ===================================================
# Build Complete
# ===================================================
Write-Info ""
Write-Success "======================================"
Write-Success "Build completed successfully!"
Write-Success "======================================"
Write-Info ""
Write-Info "Output files:"
Write-Info "  • Executable:  .\dist\SolanaTradingBot.exe"
Write-Info "  • MSI Installer: .\dist\SolanaTradingBot-Setup.msi"
Write-Info "  • Distribution:  .\dist\$zipName"
Write-Info ""
Write-Info "Next steps:"
Write-Info "  1. Test the executable: .\dist\SolanaTradingBot.exe"
Write-Info "  2. Test the MSI installer"
Write-Info "  3. Distribute the ZIP package"
Write-Info ""
Write-Success "Happy trading! 🚀"
