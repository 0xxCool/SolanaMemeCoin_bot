# Installation Guide

## Requirements
- Python 3.11+ (tested with Python 3.11.14)
- pip 25.3+

## Quick Install

### Full Installation (with Deep Learning)
```bash
pip install -r requirements.txt
```

### Minimal Installation (without TensorFlow/PyTorch)
If you don't need deep learning capabilities, install only core dependencies:

```bash
# Install everything except TensorFlow and PyTorch
pip install python-dotenv aiohttp websockets python-telegram-bot \
    solana solders base58 pandas numpy scikit-learn scipy joblib \
    aiofiles aiosqlite sqlalchemy prometheus-client colorlog \
    uvloop orjson pytest pytest-asyncio pytest-cov pytest-mock \
    black pylint mypy cryptography bandit safety
```

Or use the pre-configured minimal requirements:
```bash
pip install -r requirements-minimal.txt
```

### Optional: Deep Learning Only
```bash
pip install torch torchvision tensorflow keras
```

## Installation Notes

### Solana SDK
- Uses `solana==0.36.10` with `solders==0.23.0`
- Requires `websockets==12.0` for compatibility
- SPL Token functionality is included in the `solana` package (no separate `spl-token` package needed)

### numpy Compatibility
- Using `numpy==1.26.4` for compatibility with TensorFlow 2.18.0
- TensorFlow 2.18.0 requires `numpy<2.1.0`

### Security Tools
- Updated to `safety==3.2.11` to resolve packaging dependency conflicts
- The old `safety==2.3.5` had conflicts with `black` and `pytest`

## Verified Compatible Versions

All packages have been tested and verified to work together without conflicts:
- ✅ Core dependencies (Solana, Telegram, etc.)
- ✅ Data processing (pandas, numpy, scikit-learn)
- ✅ Deep Learning (TensorFlow, PyTorch)
- ✅ Development tools (pytest, black, pylint)
- ✅ Security tools (safety, bandit, cryptography)

## Troubleshooting

### Cache Issues
If you encounter cache permission warnings:
```bash
pip install --no-cache-dir -r requirements.txt
```

### Large Downloads
TensorFlow and PyTorch are large packages (several GB). If installation times out:
```bash
# Install in stages
pip install -r requirements-minimal.txt
pip install torch torchvision
pip install tensorflow keras
```

## Updated Packages

The following packages were updated to resolve dependency conflicts:

| Package | Old Version | New Version | Reason |
|---------|-------------|-------------|--------|
| solana | 0.32.0 | 0.36.10 | websockets 12.0 support |
| solders | 0.19.0 | 0.23.0 | Required by solana 0.36+ |
| safety | 2.3.5 | 3.2.11 | Packaging conflict resolution |
| pytest | 7.4.3 | 8.3.4 | Latest stable |
| black | 23.12.0 | 24.10.0 | Latest stable |
| tensorflow | 2.15.0 | 2.18.0 | Latest stable |
| keras | 2.15.0 | 3.7.0 | Keras 3 with TensorFlow 2.16+ |

### Removed Packages
- `asyncio==3.4.3` - Removed (part of Python stdlib since 3.4)
- `spl-token==0.6.0` - Removed (doesn't exist; functionality in solana package)
