#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
APP_NAME="YouAreLoved"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"
DMG_NAME="YouAreLoved.dmg"
VOLUME_NAME="You Are Loved"

rm -rf "$BUILD_DIR"
mkdir -p "$APP_BUNDLE/Contents/MacOS"

# ── Info.plist ────────────────────────────────────────────────────────────────

cat > "$APP_BUNDLE/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>You Are Loved</string>
    <key>CFBundleIdentifier</key>
    <string>app.youareloved.mac</string>
    <key>CFBundleExecutable</key>
    <string>YouAreLoved</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <false/>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
</dict>
</plist>
PLIST

# ── Launcher script ──────────────────────────────────────────────────────────

cat > "$APP_BUNDLE/Contents/MacOS/$APP_NAME" << 'LAUNCHER'
#!/bin/bash
PYTHON="/opt/homebrew/bin/python3.11"
YAL_DIR="$HOME/youareloved"
if [ ! -d "$YAL_DIR" ]; then
  osascript -e 'tell app "Terminal" to do script "bash <(curl -fsSL https://raw.githubusercontent.com/Building-Humanity-Up/youareloved/main/install.sh)"'
else
  $PYTHON "$YAL_DIR/setup.py"
fi
LAUNCHER

chmod +x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"

echo "✓ Built $APP_BUNDLE"

# ── DMG staging ───────────────────────────────────────────────────────────────

STAGING="$BUILD_DIR/dmg_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP_BUNDLE" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

# ── Create DMG ────────────────────────────────────────────────────────────────

DMG_PATH="$SCRIPT_DIR/$DMG_NAME"
rm -f "$DMG_PATH"

hdiutil create \
  -volname "$VOLUME_NAME" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

rm -rf "$BUILD_DIR"

echo ""
echo "✓ $DMG_PATH"
echo "  $(du -h "$DMG_PATH" | cut -f1) compressed"
