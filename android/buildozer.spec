[app]

# Application title
title = Solana Trading Bot Pro

# Package name
package.name = solanabot

# Package domain (for Android package name)
package.domain = com.solanatradingbot

# Source code directory
source.dir = ./app

# Main entry point
source.main = main.py

# Version
version = 1.0.0

# Requirements
requirements = python3,kivy==2.2.1,websockets,asyncio,aiohttp,requests,certifi,charset-normalizer,idna,urllib3

# Android specific
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.gradle_dependencies = com.google.android.material:material:1.9.0
android.enable_androidx = True

# Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK

# Android app theme
android.manifest.application.theme = @android:style/Theme.Material.Light.DarkActionBar

# Application icon
icon.filename = resources/icons/app-icon.png

# Presplash image
presplash.filename = resources/icons/presplash.png

# Orientation
orientation = portrait

# Full screen
fullscreen = 0

# Google Play Store
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.release = True

[buildozer]
# Build directory
build_dir = ./.buildozer
bin_dir = ./bin

# Logcat filters
log_level = 2
warn_on_root = 1
