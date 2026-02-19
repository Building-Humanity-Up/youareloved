#!/bin/bash
# ============================================================================
# You Are Loved — Installer
#
# Install:
#   bash <(curl -fsSL https://raw.githubusercontent.com/Building-Humanity-Up/youareloved/main/install.sh)
# ============================================================================

REPO="https://raw.githubusercontent.com/Building-Humanity-Up/youareloved/main"
YAL_DIR="$HOME/youareloved"

# Ensure we're in a valid directory (fixes getcwd errors after rm -rf)
cd "$HOME" 2>/dev/null || cd / 2>/dev/null

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
DIM="\033[2m"
RESET="\033[0m"

# ── Self-bootstrap: if stdin is not a terminal, re-run interactively ─────

if [[ ! -t 0 ]]; then
    TMPSCRIPT=$(mktemp /tmp/yal_install.XXXXXX.sh)
    curl -fsSL "$REPO/install.sh" -o "$TMPSCRIPT" 2>/dev/null \
        || cat > "$TMPSCRIPT"
    exec bash "$TMPSCRIPT"
    exit 0
fi

# ── From here on, stdin is a real terminal ───────────────────────────────

echo ""
echo -e "${BOLD}"
echo "  ┌──────────────────────────────────────┐"
echo "  │                                      │"
echo "  │         You Are Loved  v0.2.0        │"
echo "  │                                      │"
echo "  └──────────────────────────────────────┘"
echo -e "${RESET}"
echo ""

# ── Detect architecture ──────────────────────────────────────────────────

ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
    BREW_PREFIX="/opt/homebrew"
    echo -e "  ${DIM}Architecture: Apple Silicon${RESET}"
else
    BREW_PREFIX="/usr/local"
    echo -e "  ${DIM}Architecture: Intel${RESET}"
fi

MACOS_VER=$(sw_vers -productVersion 2>/dev/null || echo "0")
MAJOR=$(echo "$MACOS_VER" | cut -d. -f1)
[[ "$MAJOR" -lt 12 ]] && echo -e "  ${YELLOW}⚠ macOS $MACOS_VER — recommended 12+${RESET}"
echo -e "  ${DIM}macOS: $MACOS_VER${RESET}"

# ── Early sudo — single prompt, keep alive throughout ────────────────────

echo ""
echo -e "  ${YELLOW}This installer needs administrator access.${RESET}"
echo ""

if ! sudo -v 2>/dev/null; then
    echo -e "  ${RED}Administrator access required. Run from an admin account.${RESET}"
    exit 1
fi

# Keep sudo alive — refresh every 30s (well within the 5min default timeout)
(while kill -0 $$ 2>/dev/null; do sudo -n true 2>/dev/null; sleep 30; done) &
SUDO_PID=$!
trap "kill $SUDO_PID 2>/dev/null" EXIT

echo -e "  ${GREEN}✓ Administrator access granted${RESET}"

# ── Ensure Homebrew ──────────────────────────────────────────────────────

if ! command -v brew &>/dev/null; then
    echo ""
    echo -e "  ${YELLOW}Installing Homebrew...${RESET}"
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
eval "$($BREW_PREFIX/bin/brew shellenv)" 2>/dev/null || true
echo -e "  ${DIM}Homebrew: ✓${RESET}"

# ── Install all brew dependencies ────────────────────────────────────────

echo ""
echo -e "  ${YELLOW}Installing system dependencies...${RESET}"

brew install python@3.11 python-tk@3.11 tesseract 2>/dev/null || true

# ── Find Python ──────────────────────────────────────────────────────────

PYTHON=""
for p in \
    "$BREW_PREFIX/opt/python@3.11/bin/python3.11" \
    "$BREW_PREFIX/opt/python@3.12/bin/python3.12" \
    "$BREW_PREFIX/opt/python@3.13/bin/python3.13" \
    "$BREW_PREFIX/bin/python3" \
    "/usr/bin/python3"; do
    if [[ -x "$p" ]]; then
        ver=$("$p" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
        pymajor=$(echo "$ver" | cut -d. -f1)
        pyminor=$(echo "$ver" | cut -d. -f2)
        if [[ "$pymajor" -ge 3 ]] && [[ "$pyminor" -ge 9 ]]; then
            PYTHON="$p"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo -e "  ${RED}Python 3.9+ not found. Run: brew install python@3.11${RESET}"
    exit 1
fi

echo -e "  ${DIM}Python: $PYTHON ($($PYTHON --version 2>&1))${RESET}"
echo -e "  ${DIM}Tesseract: $(command -v tesseract 2>/dev/null || echo 'not found')${RESET}"
echo -e "  ${DIM}Tkinter: $($PYTHON -c 'import tkinter; print("✓")' 2>/dev/null || echo 'not found')${RESET}"

# ── Python packages ──────────────────────────────────────────────────────

echo ""
echo -e "  ${YELLOW}Installing Python packages...${RESET}"

$PYTHON -m pip install --quiet --break-system-packages \
    nudenet pillow mss pytesseract psutil \
    pyobjc-framework-Quartz 2>&1 | grep -v "already satisfied" || true

echo -e "  ${GREEN}✓ Dependencies ready${RESET}"

# ── Download files ───────────────────────────────────────────────────────

echo ""
echo -e "  ${YELLOW}Downloading You Are Loved...${RESET}"

mkdir -p "$YAL_DIR"

for file in guardian.py watchdog.py setup.py uninstall.sh; do
    echo -e "  ${DIM}  ↓ $file${RESET}"
    curl -fsSL "$REPO/$file" -o "$YAL_DIR/$file"
done

chmod +x "$YAL_DIR/guardian.py" "$YAL_DIR/watchdog.py" \
         "$YAL_DIR/setup.py" "$YAL_DIR/uninstall.sh"

echo -e "  ${GREEN}✓ Files downloaded${RESET}"

# ── Download visual detection model ─────────────────────────────────────

MODEL_DIR="$YAL_DIR/models"
MODEL_FILE="$MODEL_DIR/640m.onnx"

if [[ ! -f "$MODEL_FILE" ]] || [[ $(stat -f%z "$MODEL_FILE" 2>/dev/null || echo 0) -lt 1000000 ]]; then
    echo ""
    echo -e "  ${YELLOW}Downloading visual detection model...${RESET}"
    mkdir -p "$MODEL_DIR"
    rm -f "$MODEL_FILE" 2>/dev/null

    # GitHub release assets require Accept header to get binary, not HTML
    DOWNLOAD_OK=false

    # Method 1: Python with proper redirect handling (most reliable)
    $PYTHON -c "
import urllib.request, os, sys
url = 'https://github.com/Building-Humanity-Up/youareloved/releases/download/v0.2.0/640m.onnx'
out = '$MODEL_FILE'
try:
    req = urllib.request.Request(url, headers={
        'Accept': 'application/octet-stream',
        'User-Agent': 'YouAreLoved/0.2.0'
    })
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
        if len(data) > 1000000:
            with open(out, 'wb') as f:
                f.write(data)
            print(f'{len(data)/1024/1024:.1f}')
        else:
            print('SMALL')
except Exception as e:
    print(f'ERR:{e}')
" 2>/dev/null | read -r MODEL_RESULT

    if [[ -f "$MODEL_FILE" ]] && [[ $(stat -f%z "$MODEL_FILE" 2>/dev/null || echo 0) -gt 1000000 ]]; then
        DOWNLOAD_OK=true
    fi

    # Method 2: curl with GitHub API (handles redirects)
    if [[ "$DOWNLOAD_OK" != "true" ]]; then
        curl -sL -H "Accept: application/octet-stream" \
            "https://github.com/Building-Humanity-Up/youareloved/releases/download/v0.2.0/640m.onnx" \
            -o "$MODEL_FILE" 2>/dev/null
        if [[ -f "$MODEL_FILE" ]] && [[ $(stat -f%z "$MODEL_FILE" 2>/dev/null || echo 0) -gt 1000000 ]]; then
            DOWNLOAD_OK=true
        fi
    fi

    # Method 3: gh CLI if available
    if [[ "$DOWNLOAD_OK" != "true" ]] && command -v gh &>/dev/null; then
        rm -f "$MODEL_FILE" 2>/dev/null
        gh release download v0.2.0 \
            --repo Building-Humanity-Up/youareloved \
            --pattern "640m.onnx" \
            --dir "$MODEL_DIR" 2>/dev/null
        if [[ -f "$MODEL_FILE" ]] && [[ $(stat -f%z "$MODEL_FILE" 2>/dev/null || echo 0) -gt 1000000 ]]; then
            DOWNLOAD_OK=true
        fi
    fi

    if [[ "$DOWNLOAD_OK" == "true" ]]; then
        SIZE=$(du -h "$MODEL_FILE" | cut -f1)
        echo -e "  ${GREEN}✓ Visual model: NudeNet 640m ($SIZE)${RESET}"
    else
        rm -f "$MODEL_FILE" 2>/dev/null
        echo -e "  ${YELLOW}⚠ Could not download 640m model${RESET}"
        echo -e "  ${DIM}  Visual detection will use default 320n (lower accuracy)${RESET}"
        echo -e "  ${DIM}  To fix later: gh release download v0.2.0 --repo Building-Humanity-Up/youareloved --pattern 640m.onnx --dir $MODEL_DIR${RESET}"
    fi
else
    SIZE=$(du -h "$MODEL_FILE" | cut -f1)
    echo -e "  ${DIM}Visual model: already present ($SIZE)${RESET}"
fi

# ── Configure DNS ────────────────────────────────────────────────────────

echo ""
echo -e "  ${YELLOW}Configuring DNS protection...${RESET}"

while IFS= read -r iface; do
    [[ -n "$iface" ]] && sudo networksetup -setdnsservers "$iface" \
        45.90.28.0 45.90.30.0 2>/dev/null || true
done < <(networksetup -listallnetworkservices | tail -n +2)

echo -e "  ${GREEN}✓ DNS configured${RESET}"

# ── Hosts file ───────────────────────────────────────────────────────────

if ! grep -q "You Are Loved" /etc/hosts 2>/dev/null; then
    echo -e "  ${YELLOW}Adding domain blocks...${RESET}"
    sudo bash -c 'cat >> /etc/hosts << "HOSTS_EOF"

# You Are Loved — Adult Domain Blocks
0.0.0.0 pornhub.com www.pornhub.com
0.0.0.0 xvideos.com www.xvideos.com
0.0.0.0 xhamster.com www.xhamster.com
0.0.0.0 xnxx.com www.xnxx.com
0.0.0.0 redtube.com www.redtube.com
0.0.0.0 youporn.com www.youporn.com
0.0.0.0 chaturbate.com www.chaturbate.com
0.0.0.0 stripchat.com www.stripchat.com
0.0.0.0 bongacams.com www.bongacams.com
0.0.0.0 livejasmin.com www.livejasmin.com
0.0.0.0 cam4.com www.cam4.com
0.0.0.0 myfreecams.com www.myfreecams.com
0.0.0.0 spankbang.com www.spankbang.com
0.0.0.0 motherless.com www.motherless.com
0.0.0.0 brazzers.com www.brazzers.com
0.0.0.0 bangbros.com www.bangbros.com
0.0.0.0 realitykings.com www.realitykings.com
0.0.0.0 naughtyamerica.com www.naughtyamerica.com
0.0.0.0 onlyfans.com www.onlyfans.com
0.0.0.0 nhentai.net www.nhentai.net
0.0.0.0 hentaihaven.xxx
0.0.0.0 rule34.xxx
0.0.0.0 gelbooru.com www.gelbooru.com
0.0.0.0 danbooru.donmai.us
0.0.0.0 javguru.com www.javguru.com
0.0.0.0 jav.guru
0.0.0.0 javhd.com www.javhd.com
0.0.0.0 javbus.com www.javbus.com
0.0.0.0 dirtyroulette.com www.dirtyroulette.com
0.0.0.0 efukt.com www.efukt.com
# End You Are Loved
HOSTS_EOF'
    sudo dscacheutil -flushcache 2>/dev/null || true
    echo -e "  ${GREEN}✓ Domain blocks added${RESET}"
else
    echo -e "  ${DIM}Domain blocks already configured${RESET}"
fi

# ── macOS permissions ────────────────────────────────────────────────────

echo ""
echo -e "  ${YELLOW}Setting up screen detection...${RESET}"

# Test if screen capture works from this Python
SR_OK=$($PYTHON -c "
try:
    import Quartz
    img = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
    if img and Quartz.CGImageGetWidth(img) > 0:
        provider = Quartz.CGImageGetDataProvider(img)
        data = Quartz.CGDataProviderCopyData(provider)
        # Check first few bytes aren't all zero
        sample = bytes(data[:800])
        if any(b != 0 for b in sample):
            print('yes')
        else:
            print('no')
    else:
        print('no')
except Exception as e:
    print('no')
" 2>/dev/null)

if [[ "$SR_OK" != "yes" ]]; then
    echo ""
    echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "  ${YELLOW}  One quick step — Screen Recording${RESET}"
    echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    echo -e "  ${DIM}  System Settings will open to Screen Recording.${RESET}"
    echo -e "  ${DIM}  Click the ${BOLD}+${RESET}${DIM} button at the bottom, then:${RESET}"
    echo -e "  ${DIM}  Press ${BOLD}Cmd+Shift+G${RESET}${DIM} and paste this path:${RESET}"
    echo ""
    echo -e "  ${BOLD}  $PYTHON${RESET}"
    echo ""
    echo -e "  ${DIM}  Click Open, then make sure it's toggled ${BOLD}ON${RESET}${DIM}.${RESET}"
    echo ""

    open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true
    sleep 1
    osascript -e 'tell application "System Settings" to activate' 2>/dev/null || true

    for attempt in 1 2 3 4 5; do
        echo -e "  ${YELLOW}  Press Enter after adding Python...${RESET}"
        read -r

        SR_OK=$($PYTHON -c "
try:
    import Quartz
    img = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
    if img and Quartz.CGImageGetWidth(img) > 0:
        provider = Quartz.CGImageGetDataProvider(img)
        data = Quartz.CGDataProviderCopyData(provider)
        sample = bytes(data[:800])
        print('yes' if any(b != 0 for b in sample) else 'no')
    else: print('no')
except: print('no')
" 2>/dev/null)
        if [[ "$SR_OK" == "yes" ]]; then
            echo -e "  ${GREEN}✓ Screen Recording: working${RESET}"
            break
        fi

        if [[ "$attempt" -lt 5 ]]; then
            echo -e "  ${RED}  Not working yet.${RESET}"
            echo -e "  ${DIM}  Make sure you added: $PYTHON${RESET}"
            echo -e "  ${DIM}  and toggled it ON. You may need to restart Terminal.${RESET}"
        else
            echo -e "  ${YELLOW}  ⚠ Screen Recording not confirmed.${RESET}"
            echo -e "  ${YELLOW}  Guardian will remind you until it's fixed.${RESET}"
        fi
    done
else
    echo -e "  ${GREEN}✓ Screen Recording: working${RESET}"
fi

# ── Launch setup UI ──────────────────────────────────────────────────────

echo ""
echo -e "  ${YELLOW}Launching setup...${RESET}"
echo ""

$PYTHON "$YAL_DIR/setup.py"

echo ""
echo -e "  ${GREEN}✓ Setup complete${RESET}"

# ── Install Guardian as LaunchAgent (user-level, for screen capture) ─────
# ── Install Watchdog as LaunchDaemon (root, for anti-removal) ────────────

echo ""
echo -e "  ${YELLOW}Installing system protection...${RESET}"

GUARDIAN_AGENT="$HOME/Library/LaunchAgents/com.youareloved.guardian.plist"
WATCHDOG_PLIST="/Library/LaunchDaemons/com.youareloved.watchdog.plist"

# Clean up any previous installs
sudo launchctl bootout system/com.youareloved.guardian 2>/dev/null || true
sudo launchctl bootout system/com.youareloved.watchdog 2>/dev/null || true
launchctl unload "$GUARDIAN_AGENT" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.youareloved.guardian.plist" 2>/dev/null
sudo rm -f "/Library/LaunchDaemons/com.youareloved.guardian.plist" 2>/dev/null
pkill -f guardian.py 2>/dev/null || true
pkill -f watchdog.py 2>/dev/null || true
sleep 2

# Guardian — user-level LaunchAgent (inherits user permissions for screen capture)
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$GUARDIAN_AGENT" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youareloved.guardian</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>-u</string>
        <string>${YAL_DIR}/guardian.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>/tmp/yal.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/yal.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Protect agent plist from casual deletion
chmod 444 "$GUARDIAN_AGENT"

# Load guardian as user
launchctl load -w "$GUARDIAN_AGENT" 2>/dev/null || true

# Watchdog — system-level LaunchDaemon (root, monitors guardian, hard to remove)
sudo tee "$WATCHDOG_PLIST" > /dev/null << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.youareloved.watchdog</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON}</string>
        <string>-u</string>
        <string>${YAL_DIR}/watchdog.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>15</integer>
    <key>StandardOutPath</key>
    <string>/tmp/yal_watchdog.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/yal_watchdog.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin</string>
    </dict>
</dict>
</plist>
EOF
sudo chmod 644 "$WATCHDOG_PLIST"
sudo chown root:wheel "$WATCHDOG_PLIST"

sudo launchctl bootstrap system/ "$WATCHDOG_PLIST"
sleep 3

echo -e "  ${GREEN}✓ Protection installed${RESET}"

# ── Verify ───────────────────────────────────────────────────────────────

echo ""
sleep 5
GPID=$(pgrep -f "guardian.py" | head -1)
WPID=$(pgrep -f "watchdog.py" | head -1)

SETUP_OK=$($PYTHON -c "
import json, os
p = os.path.expanduser('~/.yal_config.json')
try:
    c = json.load(open(p))
    print('yes' if c.get('setup_complete') else 'no')
except: print('no')
" 2>/dev/null)

if [[ "$SETUP_OK" != "yes" ]]; then
    echo ""
    echo -e "  ${YELLOW}⚠ Setup did not complete.${RESET}"
    echo -e "  ${YELLOW}  Run:  $PYTHON ~/youareloved/setup.py${RESET}"
fi

[[ -n "$GPID" ]] && echo -e "  ${GREEN}✓ Guardian running (PID: $GPID)${RESET}" \
                  || echo -e "  ${RED}✗ Guardian — check /tmp/yal.error.log${RESET}"
[[ -n "$WPID" ]] && echo -e "  ${GREEN}✓ Watchdog running (PID: $WPID)${RESET}" \
                  || echo -e "  ${RED}✗ Watchdog not running${RESET}"

# ── Pre-flight: verify each detection layer ──────────────────────────────

echo ""
echo -e "  ${YELLOW}Running system check...${RESET}"

$PYTHON -c "
import sys, os, subprocess

ok = True

# 1. Screen capture
try:
    import Quartz
    img = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
    if img and Quartz.CGImageGetWidth(img) > 0:
        w = Quartz.CGImageGetWidth(img)
        h = Quartz.CGImageGetHeight(img)
        provider = Quartz.CGImageGetDataProvider(img)
        data = Quartz.CGDataProviderCopyData(provider)
        sample = bytes(data[:800])
        if any(b != 0 for b in sample):
            print(f'  ✓ Screen capture: {w}x{h}')
        else:
            print('  ✗ Screen capture: BLACK (no permission)')
            ok = False
    else:
        print('  ✗ Screen capture: failed')
        ok = False
except Exception as e:
    print(f'  ✗ Screen capture: {e}')
    ok = False

# 2. NudeNet
try:
    from nudenet import NudeDetector
    d = NudeDetector()
    print('  ✓ NudeNet: loaded')
except Exception as e:
    print(f'  ✗ NudeNet: {e}')
    ok = False

# 3. OCR / Tesseract
try:
    r = subprocess.run(['tesseract', '--version'], capture_output=True, timeout=5)
    ver = r.stdout.decode().split('\n')[0] if r.returncode == 0 else 'unknown'
    print(f'  ✓ Tesseract: {ver}')
except Exception:
    print('  ✗ Tesseract: not found (OCR will be skipped)')

# 4. AppleScript / Browser tabs
try:
    r = subprocess.run(['osascript', '-e',
        'tell application \"System Events\" to return name of every process whose background only is false'],
        capture_output=True, text=True, timeout=5)
    apps = [a.strip() for a in r.stdout.split(',')]
    browsers = [a for a in apps if a in ('Google Chrome', 'Safari', 'Firefox', 'Arc')]
    print(f'  ✓ Browser detection: {len(browsers)} browser(s) visible')
except Exception as e:
    print(f'  ✗ Browser detection: {e}')

# 5. Config
try:
    import json
    from pathlib import Path
    cfg = json.loads((Path.home() / '.yal_config.json').read_text())
    partners = cfg.get('partners', [])
    has_tg = bool(cfg.get('telegram_bot_token'))
    has_sg = bool(cfg.get('sendgrid_api_key'))
    has_ai = bool(cfg.get('anthropic_api_key'))
    print(f'  ✓ Partners: {len(partners)} configured')
    print(f'  ✓ Alerts: Telegram={\"yes\" if has_tg else \"no\"} Email={\"yes\" if has_sg else \"no\"} AI={\"yes\" if has_ai else \"no\"}')
except Exception as e:
    print(f'  ✗ Config: {e}')
    ok = False

if not ok:
    print()
    print('  ⚠ Some checks failed — see above')
" 2>/dev/null

echo ""
echo -e "${BOLD}"
echo "  ┌──────────────────────────────────────┐"
echo "  │                                      │"
if [[ -n "$GPID" ]] && [[ "$SETUP_OK" == "yes" ]]; then
echo "  │       You are loved.                 │"
echo "  │       Protection is active.          │"
else
echo "  │       Almost there.                  │"
echo "  │       See instructions above.        │"
fi
echo "  │                                      │"
echo "  └──────────────────────────────────────┘"
echo -e "${RESET}"
echo ""
echo -e "  ${DIM}Logs:      tail -f /tmp/yal.log${RESET}"
echo -e "  ${DIM}Uninstall: ~/youareloved/uninstall.sh${RESET}"
echo ""

kill $SUDO_PID 2>/dev/null
