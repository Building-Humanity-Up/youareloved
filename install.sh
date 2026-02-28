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

# ── Resolve the REAL binary path ─────────────────────────────────────────
#
# macOS TCC (Transparency, Consent, and Control) grants Screen Recording
# permission to the *resolved* binary, not to symlinks pointing at it.
#
# Homebrew Python: /opt/homebrew/opt/python@3.11/bin/python3.11
#   → resolves to: /opt/homebrew/Cellar/python@3.11/3.11.x/Frameworks/
#                   Python.framework/Versions/3.11/bin/python3.11
#
# If the LaunchAgent uses the symlink but macOS granted permission to the
# resolved path (or vice versa), screen capture silently returns
# wallpaper-only images — the single hardest bug to diagnose in this project.
#
# We resolve once here, use PYTHON_REAL everywhere that matters.

PYTHON_REAL=$("$PYTHON" -c "import os,sys; print(os.path.realpath(sys.executable))" 2>/dev/null)
if [[ -z "$PYTHON_REAL" ]] || [[ ! -x "$PYTHON_REAL" ]]; then
    PYTHON_REAL=$(readlink -f "$PYTHON" 2>/dev/null || echo "$PYTHON")
fi

echo -e "  ${DIM}Python: $PYTHON ($($PYTHON --version 2>&1))${RESET}"
if [[ "$PYTHON_REAL" != "$PYTHON" ]]; then
    echo -e "  ${DIM}Binary: $PYTHON_REAL${RESET}"
fi
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

if [[ ! -f "$MODEL_FILE" ]] || [[ $(wc -c < "$MODEL_FILE") -lt 1000000 ]]; then
    echo ""
    echo -e "  ${YELLOW}Downloading visual detection model...${RESET}"
    mkdir -p "$MODEL_DIR"
    rm -f "$MODEL_FILE" 2>/dev/null

    curl -L \
        "https://github.com/Building-Humanity-Up/youareloved/releases/download/v0.2.0/640m.onnx" \
        -o "$MODEL_FILE" \
        --progress-bar 2>&1 | grep -v "^$"

    if [[ -f "$MODEL_FILE" ]] && \
       [[ $(wc -c < "$MODEL_FILE") -gt 1000000 ]]; then
        echo -e "  ${GREEN}✓ High-accuracy model ready${RESET}"
    else
        rm -f "$MODEL_FILE"
        echo -e "  ${YELLOW}⚠ Using standard model (640m unavailable)${RESET}"
    fi
else
    SIZE=$(du -h "$MODEL_FILE" | cut -f1)
    echo -e "  ${DIM}Visual model: already present ($SIZE)${RESET}"
fi

# ── Generate device token & configure DNS ─────────────────────────────────

echo ""
echo -e "  ${YELLOW}Configuring DNS protection...${RESET}"

NEXTDNS_ID="5d8482"
FIRSTNAME_LOWER=$(echo "$USER" | tr '[:upper:]' '[:lower:]')
RANDOM4=$(LC_ALL=C tr -dc 'a-z0-9' < /dev/urandom | head -c 4)
MAC_DEVICE_TOKEN="${FIRSTNAME_LOWER}-mac-${RANDOM4}"
DOH_URL="https://dns.nextdns.io/${NEXTDNS_ID}/${MAC_DEVICE_TOKEN}"

echo -e "  ${DIM}Device token: $MAC_DEVICE_TOKEN${RESET}"

# Store device token in config
$PYTHON -c "
import json, os
p = os.path.expanduser('~/.yal_config.json')
try:
    cfg = json.load(open(p))
except Exception:
    cfg = {}
cfg['mac_device_token'] = '$MAC_DEVICE_TOKEN'
cfg['nextdns_doh_url'] = '$DOH_URL'
with open(p, 'w') as f:
    json.dump(cfg, f, indent=2)
" 2>/dev/null

# Set system DNS to NextDNS resolvers on all interfaces
while IFS= read -r iface; do
    [[ -n "$iface" ]] && sudo networksetup -setdnsservers "$iface" \
        45.90.28.58 45.90.30.58 2>/dev/null || true
done < <(networksetup -listallnetworkservices | tail -n +2)

echo -e "  ${GREEN}✓ DNS configured (NextDNS)${RESET}"

# Register device token with server
$PYTHON -c "
import json, os, urllib.request
p = os.path.expanduser('~/.yal_config.json')
try:
    cfg = json.load(open(p))
    email = cfg.get('user_email', '')
    if not email:
        email = next((p.get('email','') for p in cfg.get('partners',[]) if p.get('email')), '')
    firstname = os.environ.get('USER', 'user')
    body = json.dumps({
        'firstname': firstname,
        'user_email': email or 'unknown@youareloved.app',
        'device_token': '$MAC_DEVICE_TOKEN'
    }).encode()
    req = urllib.request.Request('https://api.finallyfreeai.com/ios/enroll',
        data=body, headers={'Content-Type':'application/json'}, method='POST')
    urllib.request.urlopen(req, timeout=10)
    print('  ✓ Device registered with server')
except Exception as e:
    print(f'  ⚠ Device registration skipped: {e}')
" 2>/dev/null || echo -e "  ${DIM}Device registration skipped (offline OK)${RESET}"

# ── Hosts file (fallback layer) ──────────────────────────────────────────

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

# ── macOS Screen Recording — resolved-path verification ──────────────────
#
# This is the most critical permission step. Without it, Guardian captures
# wallpaper-only images (non-black, but missing all window content) and
# NudeNet sees nothing. The user thinks protection is working. It isn't.
#
# Strategy:
#   1. Trigger a capture with PYTHON_REAL to pre-populate the TCC list
#   2. Verify with content-aware check (luminance std-dev, not just non-black)
#   3. If wallpaper-only: explain the exact binary to enable
#   4. Gate: don't proceed until verified (with escape valve after many attempts)

echo ""
echo -e "  ${YELLOW}Setting up screen detection...${RESET}"

# Step 1: Trigger capture attempt with the resolved binary.
# This causes macOS to add it to the Screen Recording list (toggled OFF).
# On macOS 14+, user may only need to toggle ON instead of manually adding.
"$PYTHON_REAL" -c "
try:
    import Quartz
    Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
except: pass
" 2>/dev/null
sleep 1

# Step 2: Content-aware verification function.
# Returns: "yes" (full desktop), "wallpaper" (non-black but no windows), "no" (failed)
_verify_screen_capture() {
    "$PYTHON_REAL" -c "
import sys
try:
    import Quartz
    from PIL import Image

    img = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
    if not img or Quartz.CGImageGetWidth(img) == 0:
        print('no'); sys.exit(0)

    w = Quartz.CGImageGetWidth(img)
    h = Quartz.CGImageGetHeight(img)
    bpr = Quartz.CGImageGetBytesPerRow(img)
    provider = Quartz.CGImageGetDataProvider(img)
    data = bytes(Quartz.CGDataProviderCopyData(provider))

    # Quick black check
    if all(b == 0 for b in data[:2000]):
        print('no'); sys.exit(0)

    # Convert to grayscale, sample every 4th pixel for speed.
    # Measure luminance standard deviation:
    #   Wallpaper-only: std 15-45 (smooth gradient or solid)
    #   Desktop with windows (text, UI, mixed content): std 50+
    pil = Image.frombuffer('RGBA', (w, h), data, 'raw', 'BGRA', bpr, 1).convert('L')
    pixels = list(pil.getdata())[::4]
    n = len(pixels)
    mean = sum(pixels) / n
    std = (sum((p - mean) ** 2 for p in pixels) / n) ** 0.5

    if std > 45:
        print('yes')
    elif std > 3:
        print('wallpaper')
    else:
        print('no')
except Exception:
    print('no')
" 2>/dev/null
}

SR_OK=$(_verify_screen_capture)

if [[ "$SR_OK" == "yes" ]]; then
    echo -e "  ${GREEN}✓ Screen Recording: working${RESET}"
else
    echo ""
    echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "  ${YELLOW}  One quick step — Screen Recording${RESET}"
    echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""

    # Copy resolved path to clipboard
    echo -n "$PYTHON_REAL" | pbcopy 2>/dev/null || true

    echo -e "  ${DIM}  System Settings will open to Screen Recording.${RESET}"
    echo ""
    echo -e "  ${DIM}  Look for ${BOLD}Python${RESET}${DIM} in the list and toggle it ${BOLD}ON${RESET}${DIM}.${RESET}"
    echo ""
    echo -e "  ${DIM}  If Python isn't listed:${RESET}"
    echo -e "  ${DIM}  Click ${BOLD}+${RESET}${DIM} at the bottom, press ${BOLD}Cmd+Shift+G${RESET}${DIM},${RESET}"
    echo -e "  ${DIM}  then ${BOLD}Cmd+V${RESET}${DIM} to paste the path, and click Open.${RESET}"
    echo ""
    echo -e "  ${DIM}  Path (copied to clipboard):${RESET}"
    echo -e "  ${BOLD}  $PYTHON_REAL${RESET}"
    echo ""

    open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true
    sleep 1
    osascript -e 'tell application "System Settings" to activate' 2>/dev/null || true

    for attempt in $(seq 1 10); do
        echo -e "  ${YELLOW}  Press Enter after enabling it...${RESET}"
        read -r

        SR_OK=$(_verify_screen_capture)

        if [[ "$SR_OK" == "yes" ]]; then
            echo -e "  ${GREEN}✓ Screen Recording: working${RESET}"
            break
        fi

        # Refresh clipboard in case user copied something else
        echo -n "$PYTHON_REAL" | pbcopy 2>/dev/null || true

        if [[ "$SR_OK" == "wallpaper" ]]; then
            # The critical diagnostic: permission granted to wrong binary.
            echo ""
            echo -e "  ${RED}  Almost — screen capture is returning only the wallpaper.${RESET}"
            echo -e "  ${DIM}  This usually means the wrong Python entry is enabled.${RESET}"
            echo ""
            echo -e "  ${DIM}  Please make sure this exact binary is in the list:${RESET}"
            echo -e "  ${BOLD}  $PYTHON_REAL${RESET}"
            echo ""
            if [[ "$PYTHON_REAL" != "$PYTHON" ]]; then
                echo -e "  ${DIM}  If you see a shorter path like:${RESET}"
                echo -e "  ${DIM}  $PYTHON${RESET}"
                echo -e "  ${DIM}  remove it, then add the full path above (it's in your clipboard).${RESET}"
                echo ""
            fi
        else
            echo -e "  ${RED}  Not working yet.${RESET}"
            echo -e "  ${DIM}  Make sure Python is in the list and toggled ON.${RESET}"
            echo -e "  ${DIM}  Path: $PYTHON_REAL${RESET}"
        fi

        if [[ "$attempt" -ge 10 ]]; then
            echo ""
            echo -e "  ${YELLOW}  ⚠ Screen Recording could not be verified.${RESET}"
            echo -e "  ${YELLOW}  Continuing — your partner will be alerted if protection is degraded.${RESET}"
        fi
    done
fi

# ── Launch setup UI ──────────────────────────────────────────────────────
#
# Write python_real_path to config BEFORE launching setup.py,
# so it can read the correct binary for TCC verification.

$PYTHON -c "
import json, os
p = os.path.expanduser('~/.yal_config.json')
try:
    cfg = json.load(open(p))
except Exception:
    cfg = {}
cfg['python_real_path'] = '$PYTHON_REAL'
with open(p, 'w') as f:
    json.dump(cfg, f, indent=2)
" 2>/dev/null

echo ""
echo -e "  ${YELLOW}Launching setup...${RESET}"
echo ""

$PYTHON "$YAL_DIR/setup.py" --python-real "$PYTHON_REAL"

echo ""
echo -e "  ${GREEN}✓ Setup complete${RESET}"

# ── Sync partners to YAL server ──────────────────────────────────────────
echo ""
echo -e "  ${YELLOW}Syncing accountability partners to server...${RESET}"

$PYTHON -c "
import json, os, urllib.request, urllib.error
p = os.path.expanduser('~/.yal_config.json')
try:
    cfg = json.load(open(p))
    email = next((p.get('email',"") for p in cfg.get('partners',[]) if p.get('email')),"")
    user_email = email or 'unknown@youareloved.app'
    firstname = os.environ.get('USER', 'user')
    # Register user
    req = urllib.request.Request('https://api.finallyfreeai.com/account/register',
        data=json.dumps({'email':user_email,'firstname':firstname}).encode(),
        headers={'Content-Type':'application/json'}, method='POST')
    urllib.request.urlopen(req, timeout=10)
    # Sync each partner
    for p in cfg.get('partners',[]):
        body = {'user_email':user_email,'partner_name':p.get('email','Partner').split('@')[0],
                'partner_email':p.get('email',''),'partner_telegram':p.get('telegram_chat_id','') or p.get('telegram','')}
        req = urllib.request.Request('https://api.finallyfreeai.com/account/partners',
            data=json.dumps(body).encode(),
            headers={'Content-Type':'application/json'}, method='POST')
        urllib.request.urlopen(req, timeout=10)
    print('  ✓ Partners synced to server')
except Exception as e:
    print(f'  ⚠ Server sync skipped: {e}')
" 2>/dev/null || echo -e "  ${DIM}Server sync skipped (offline OK)${RESET}"


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

# Guardian — user-level LaunchAgent (inherits user's TCC permissions).
#
# CRITICAL: ProgramArguments uses PYTHON_REAL — the fully resolved binary.
# macOS grants Screen Recording to this exact path. Using the symlink
# causes Guardian to silently receive wallpaper-only screenshots,
# defeating all visual detection.
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
        <string>${PYTHON_REAL}</string>
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

# Watchdog — system-level LaunchDaemon (root, monitors guardian)
# Also uses PYTHON_REAL for consistency.
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
        <string>${PYTHON_REAL}</string>
        <string>-u</string>
        <string>${YAL_DIR}/watchdog.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>15</integer>
    <key>AbandonProcessGroup</key>
    <true/>
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
        <key>PYTHONDONTWRITEBYTECODE</key>
        <string>1</string>
    </dict>
</dict>
</plist>
EOF
sudo chmod 444 "$WATCHDOG_PLIST"
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

# 1. Screen capture — content-aware check
try:
    import json
    from pathlib import Path
    cfg = json.loads((Path.home() / '.yal_config.json').read_text())
    py_real = cfg.get('python_real_path', '')
    if py_real:
        print(f'  ✓ Resolved binary: {py_real}')
except Exception:
    pass

try:
    import Quartz
    from PIL import Image
    img = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
    if img and Quartz.CGImageGetWidth(img) > 0:
        w = Quartz.CGImageGetWidth(img)
        h = Quartz.CGImageGetHeight(img)
        bpr = Quartz.CGImageGetBytesPerRow(img)
        data = bytes(Quartz.CGDataProviderCopyData(
            Quartz.CGImageGetDataProvider(img)))
        pil = Image.frombuffer('RGBA', (w, h), data, 'raw', 'BGRA', bpr, 1).convert('L')
        pixels = list(pil.getdata())[::4]
        mean = sum(pixels) / len(pixels)
        std = (sum((p - mean) ** 2 for p in pixels) / len(pixels)) ** 0.5
        if std > 45:
            print(f'  ✓ Screen capture: {w}x{h} (std={std:.0f}, full desktop)')
        elif std > 3:
            print(f'  ⚠ Screen capture: {w}x{h} (std={std:.0f}, wallpaper-only — check permission)')
            ok = False
        else:
            print(f'  ✗ Screen capture: BLACK (no permission)')
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
