#!/usr/bin/env python3
"""
You Are Loved — Guardian v9 (Unified)

Merged guardian.py (visual) + guardian_text.py (text) into single file.

7-layer detection pipeline, ordered cheapest → most expensive:

  Layer P:  Process check       — psutil, ~1ms, free
  Layer T2: Browser tabs        — AppleScript, ~100ms, free
  Layer T3: Memory recall       — in-memory, ~1ms, free
  Layer T1: OCR surface scan    — pytesseract 3x3, ~2s, free
  Layer V:  Visual scan         — NudeNet 5x5→3x3, ~5s, free
  Layer C:  Claude AI           — API call, ~500ms, $0.001
  Layer B:  Behavioral check    — time check, ~1ms, free

On detection: close windows, show dialog, lock screen, cooldown.
Idle-adaptive scanning: 5s / 30s / 10min / pause.
"""

import os
import sys
import time
import argparse
import subprocess
import logging
import json
import re
import secrets
import hashlib
import socket
import threading
import urllib.request
import py_compile
from datetime import datetime, timedelta
from pathlib import Path

EARLY_IMAGE_ONLY = "--image-only" in sys.argv[1:]

# ---------------------------------------------------------------------------
# Version & Auto-Update
# ---------------------------------------------------------------------------

VERSION = "2"
UPDATE_BOOTSTRAP_URL = "https://gist.githubusercontent.com/danielliangquestions/455ec3994fc980c1ee9b14f4d02afc27/raw/yal_update.json"
UPDATE_CHECK_HOUR = 3
UPDATE_INTERVAL_SECONDS = 300
UPDATE_STATE_FILE = Path("/tmp/yal_last_update_check")

os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DIALOG_COOLDOWN = 30
LOCK_COOLDOWN = 600  # 10 min before next lock
TRIGGER_THRESHOLD = 0.30
COARSE_GRID = 5
FINE_GRID = 3
DETECTION_ANY = 0.10

SCAN_ACTIVE = 5
SCAN_IDLE = 30
SCAN_DEEP_IDLE = 600
SCAN_AWAY_CHECK = 60
IDLE_THRESHOLD_1 = 60
IDLE_THRESHOLD_2 = 600
IDLE_THRESHOLD_3 = 1800
IMAGE_ONLY_MODE = True

LOG_FILE = Path.home() / "yal_log.txt"
MEMORY_FILE = Path.home() / ".yal_memory.json"
CONFIG_FILE = Path.home() / ".yal_config.json"
AUDIT_DIR = Path.home() / "youareloved" / "audit"
GUARDIAN_PATH = Path.home() / "youareloved" / "guardian.py"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.youareloved.guardian.plist"
TEXT_LOG = Path.home() / "Desktop" / "yal_text.log"

# ---------------------------------------------------------------------------
# NudeNet labels
# ---------------------------------------------------------------------------

NUDENET_TRIGGER_LABELS = {
    "FEMALE_BREAST_EXPOSED", "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED", "BUTTOCKS_EXPOSED", "ANUS_EXPOSED",
    "FEMALE_BREAST_COVERED", "FEMALE_GENITALIA_COVERED",
}

NUDENET_INTEREST_LABELS = NUDENET_TRIGGER_LABELS | {
    "BELLY_EXPOSED", "BELLY_COVERED", "FEMALE_BREAST_COVERED",
    "ARMPITS_EXPOSED", "MALE_BREAST_EXPOSED", "FACE_FEMALE",
}

# ---------------------------------------------------------------------------
# Safe URLs — structural only
# ---------------------------------------------------------------------------

SAFE_URLS = {
    "chrome://newtab/", "chrome://new-tab-page/",
    "chrome://settings", "chrome://extensions", "chrome://history",
    "about:blank", "about:newtab",
    "claude.ai",
}

def is_safe_url(url: str) -> bool:
    url_lower = url.lower().strip()
    for safe in SAFE_URLS:
        if safe in url_lower:
            return True
    return False

# ---------------------------------------------------------------------------
# Text keyword tiers (from guardian_text v5)
# ---------------------------------------------------------------------------

EXPLICIT_PATTERNS = [
    r'\bpornhub\b', r'\bxvideos\b', r'\bxhamster\b', r'\bxnxx\b',
    r'\bredtube\b', r'\byouporn\b', r'\bbrazzers\b', r'\bnaughtyamerica\b',
    r'\bchaturbate\b', r'\bonlyfans\b', r'\bmyfreecams\b', r'\bstripchat\b',
    r'\bbongacams\b', r'\blivejasmin\b', r'\bcam4\b', r'\bdirtyroulette\b',
    r'\bjavguru\b', r'\bjavhd\b', r'\bjavbus\b',
    r'\bmissav\b', r'\bsupjav\b', r'\bjavmost\b', r'\bjavdoe\b',
    r'\bspankbang\b', r'\bmotherless\b', r'\befukt\b',
    r'\beporner\b', r'\btnaflix\b', r'\bdrtuber\b', r'\bfapcat\b',
    r'\bbabepedia\b', r'\bfreeones\b', r'\biafd\b',
    r'\bhentaihaven\b', r'\bnhentai\b', r'\brule34\b',
    r'\bgelbooru\b', r'\bdanbooru\b',
    r'\bbangbros\b', r'\bmofos\b', r'\brealitykings\b', r'\bxempire\b',
    r'\bcumshot\b', r'\bcreampie\b',
    r'\banal\b', r'\bblowjob\b', r'\bhandjob\b', r'\bfootjob\b',
    r'\bgangbang\b', r'\bthreesome\b', r'\borgy\b',
    r'\bpenetration\b', r'\bintercourse\b',
    r'\bmasturbat', r'\bfingering\b',
    r'\bpussy\b', r'\bcock\b', r'\bdick\b',
    r'\bnipple\b', r'\bareola\b', r'\blabia\b', r'\bscrotum\b',
    r'\bxxx\b', r'\bnsfw\b',
    r'\bmilf\b', r'\bahegao\b', r'\bdoujin\b',
    r'\bhentai\b', r'\becchi\b', r'\bJAV\b',
    r'\btip\s*menu\b', r'\blovense\b', r'\bcontrol.*toy\b',
    r'\bsend\s*tip\b', r'\bprivate\s*show\b', r'\bnaked.*live\b',
    r'jav\.guru', r'jav\s*guru',
    r'\boral\s*sex\b', r'\banal\s*sex\b', r'\bgroup\s*sex\b',
    r'\bnude\s*reddit\b', r'\bporn\s*reddit\b', r'\bnsfw\s*reddit\b',
    r'\bass\s*nude\b', r'\bnude\s*ass\b', r'\bnude\s*girl\b',
    r'\bnude\s*woman\b', r'\bnude\s*pic\b', r'\bnude\s*photo\b',
    r'\bnude\s*selfie\b', r'\bnude\s*leak\b', r'\bnude\s*asian\b',
    r'\basian\s*ass\b', r'\basian\s*nude\b',
]

AMBIGUOUS_PATTERNS = [
    r'\bnude\b', r'\bnudes\b', r'\bnaked\b',
    r'\bsexy\b', r'\bseductive\b', r'\berotic\b',
    r'\blingerie\b', r'\bunderwear\b', r'\bpanties\b', r'\bthong\b',
    r'\bbikini\b', r'\btopless\b', r'\bbraless\b',
    r'\bcleavage\b', r'\bbusty\b', r'\bbig\s*breast\b', r'\bbig\s*boob\b',
    r'\bbuttock\b', r'\bbooty\b', r'\bbutt\b', r'\bass\b',
    r'\bstriptease\b', r'\bstrip\s*club\b', r'\bexotic\s*dancer\b',
    r'\bescort\b', r'\bcall\s*girl\b', r'\bhooker\b',
    r'\bdoggy\b', r'\bmissionary\b', r'\bcowgirl\b',
    r'\bkink\b', r'\bfetish\b', r'\bbdsm\b', r'\bdomin',
    r'\bsubmissive\b', r'\bslave.*sex\b',
    r'\borgasm\b', r'\bclimax\b', r'\bpleasure\b',
    r'\baroused\b', r'\bturned\s*on\b', r'\bhorny\b',
    r'\bwatch.*sex\b', r'\bfree.*porn\b', r'\bhot.*girl\b',
    r'\bnaked.*girl\b', r'\bnude.*photo\b', r'\bsex.*video\b',
    r'\badult.*content\b', r'\bxxx.*video\b', r'\bporn.*star\b',
    r'\bmature.*woman\b',
    r'\bonlyfans\s*leak\b', r'\bnude\s*leak\b', r'\bfappening\b',
    r'\bgonewild\b', r'\breddit.*nsfw\b', r'\breddit.*porn\b',
    r'\bgravure\b', r'\bgravure\s*idol\b', r'\bav\s*idol\b', r'\bidol\b',
]

_EXPLICIT_RE = [re.compile(p, re.IGNORECASE) for p in EXPLICIT_PATTERNS]
_AMBIGUOUS_RE = [re.compile(p, re.IGNORECASE) for p in AMBIGUOUS_PATTERNS]

ALL_NSFW_TERMS = set()
for _p in EXPLICIT_PATTERNS + AMBIGUOUS_PATTERNS:
    _clean = re.sub(r'\\b|\\s\*|\.\*|\[.*?\]|\(.*?\)', '', _p).strip()
    if _clean:
        ALL_NSFW_TERMS.add(_clean.lower())

# ---------------------------------------------------------------------------
# Process names (Layer P)
# ---------------------------------------------------------------------------

SUSPECT_PROCESSES = {
    "tor", "tor.real", "Tor Browser", "torbrowser",
    "openvpn", "wireguard-go", "mullvad-daemon",
    "nordvpnd", "expressvpnd",
}

# ---------------------------------------------------------------------------
# App classification (response)
# ---------------------------------------------------------------------------

BROWSERS = ["Google Chrome", "Safari", "Firefox", "Arc", "Brave Browser", "Microsoft Edge"]

APPS_TO_QUIT = {
    "VLC", "IINA", "QuickTime Player", "Infuse", "mpv",
    "Elmedia Player", "Movist", "Movist Pro",
    "Preview", "Simulator",
    "Transmission", "qBittorrent", "uTorrent", "Deluge",
}
APPS_CLOSE_WINDOWS = {
    "Google Chrome", "Safari", "Firefox", "Arc",
    "Brave Browser", "Microsoft Edge",
    "Chromium", "Vivaldi", "Opera", "Orion", "Photos",
}
APPS_PRESERVE = {
    "Finder", "Terminal", "iTerm2", "iTerm",
    "Visual Studio Code", "Cursor", "Xcode",
    "Slack", "Discord", "Messages", "Mail",
    "Notes", "Reminders", "Calendar",
    "System Preferences", "System Settings",
    "Activity Monitor", "Console",
    "Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint",
    "Pages", "Numbers", "Keynote",
    "Notion", "Obsidian", "Bear", "Figma", "Sketch",
    "zoom.us", "FaceTime", "Microsoft Teams",
    "Spotify", "Music",
}

OCR_SUPPRESS = {"you are loved", "accountability partner", "youareloved"}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("guardian")
log.setLevel(logging.DEBUG)
log.propagate = False
log.handlers.clear()

_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

if EARLY_IMAGE_ONLY:
    log.addHandler(logging.NullHandler())
else:
    _fh = logging.FileHandler("/tmp/yal.log")
    _fh.setLevel(logging.DEBUG)
    _fh.setFormatter(_fmt)
    log.addHandler(_fh)

    try:
        _fh_desktop = logging.FileHandler(str(TEXT_LOG))
        _fh_desktop.setLevel(logging.DEBUG)
        _fh_desktop.setFormatter(_fmt)
        log.addHandler(_fh_desktop)
    except (PermissionError, OSError):
        # Daemon runs as root — can't write to ~/Desktop
        # Fall back to /tmp which is always writable
        _fh_fallback = logging.FileHandler("/tmp/yal_text.log")
        _fh_fallback.setLevel(logging.DEBUG)
        _fh_fallback.setFormatter(_fmt)
        log.addHandler(_fh_fallback)

    # Only add stdout handler when running interactively (not as daemon)
    if sys.stdout.isatty():
        _sh = logging.StreamHandler(sys.stdout)
        _sh.setLevel(logging.INFO)
        _sh.setFormatter(_fmt)
        log.addHandler(_sh)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

last_dialog_time: float = 0.0
last_lock_time: float = 0.0
scan_count: int = 0
in_cooldown: bool = False
UPDATE_LOCK = threading.Lock()
UPDATE_IN_PROGRESS: bool = False

# ---------------------------------------------------------------------------
# Idle Detection
# ---------------------------------------------------------------------------

def seconds_idle() -> float:
    try:
        from Quartz import (CGEventSourceSecondsSinceLastEventType,
                            kCGEventSourceStateHIDSystemState,
                            kCGAnyInputEventType)
        return CGEventSourceSecondsSinceLastEventType(
            kCGEventSourceStateHIDSystemState, kCGAnyInputEventType)
    except ImportError:
        try:
            r = subprocess.run(["ioreg", "-c", "IOHIDSystem"],
                               capture_output=True, text=True, timeout=5)
            for line in r.stdout.split("\n"):
                if "HIDIdleTime" in line:
                    return int(line.split("=")[-1].strip()) / 1_000_000_000
        except Exception:
            pass
    return 0.0

def get_scan_mode() -> tuple:
    idle = seconds_idle()
    if in_cooldown:
        return "COOLDOWN", SCAN_ACTIVE
    if idle > IDLE_THRESHOLD_3:
        return f"AWAY ({idle:.0f}s)", SCAN_AWAY_CHECK
    elif idle > IDLE_THRESHOLD_2:
        return f"DEEP_IDLE ({idle:.0f}s)", SCAN_DEEP_IDLE
    elif idle > IDLE_THRESHOLD_1:
        return f"IDLE ({idle:.0f}s)", SCAN_IDLE
    else:
        return f"ACTIVE ({idle:.0f}s)", SCAN_ACTIVE

# ---------------------------------------------------------------------------
# Config & Setup (from guardian.py v8.1)
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def get_api_key() -> str:
    return load_config().get("anthropic_api_key", "")

def get_partners() -> list:
    """Return list of partner dicts from config. Supports both old and new format."""
    cfg = load_config()
    if "partners" in cfg:
        return cfg["partners"]
    # Backward compat: single partner_email
    if "partner_email" in cfg:
        return [{"email": cfg["partner_email"], "telegram": ""}]
    return []

def get_sendgrid_key() -> str:
    cfg = load_config()
    return cfg.get("sendgrid_api_key", "") or os.environ.get("SENDGRID_API_KEY", "")

def get_telegram_token() -> str:
    cfg = load_config()
    return cfg.get("telegram_bot_token", "")

def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

# ---------------------------------------------------------------------------
# Alert System — Telegram + Email (non-blocking)
# ---------------------------------------------------------------------------

def _send_telegram(bot_token: str, chat_id: str, text: str,
                   photo_path: str = ""):
    """Send Telegram message (and optional photo) to a single chat_id."""
    if not bot_token or not chat_id:
        return
    try:
        if photo_path and Path(photo_path).exists():
            # Send photo with caption
            import io
            boundary = "----YALBoundary"
            photo_data = Path(photo_path).read_bytes()
            body = (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n"
                f"{chat_id}\r\n"
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"caption\"\r\n\r\n"
                f"{text}\r\n"
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"photo\"; "
                f"filename=\"alert.png\"\r\n"
                f"Content-Type: image/png\r\n\r\n"
            ).encode() + photo_data + f"\r\n--{boundary}--\r\n".encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{bot_token}/sendPhoto",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST")
            urllib.request.urlopen(req, timeout=15)
        else:
            # Text only
            data = json.dumps({
                "chat_id": chat_id, "text": text, "parse_mode": "HTML"
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST")
            urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.error(f"  Telegram send failed ({chat_id}): {e}")

def _send_email_alert(api_key: str, to_email: str, subject: str, body: str):
    """Send email via SendGrid to a single address."""
    if not api_key or not to_email:
        return
    try:
        data = json.dumps({
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": "alerts@youareloved.app",
                     "name": "You Are Loved"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}]
        }).encode()
        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send", data=data,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.error(f"  Email send failed ({to_email}): {e}")

def _create_blurred_screenshot(full_img) -> str:
    """Create Gaussian-blurred screenshot, return path. Never sends unblurred."""
    blur_path = "/tmp/yal_alert_blurred.png"
    try:
        from PIL import ImageFilter
        blurred = full_img.filter(ImageFilter.GaussianBlur(radius=20))
        blurred.save(blur_path)
        return blur_path
    except Exception as e:
        log.error(f"  Blur failed: {e}")
        return ""

def fire_alerts(layer: str, detail: str, full_img=None):
    """
    Fire all alert channels in parallel threads.
    Never blocks the main response sequence.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = socket.gethostname()
    partners = get_partners()
    sg_key = get_sendgrid_key()
    tg_token = get_telegram_token()

    if not partners:
        log.info("  ALERTS: No partners configured")
        return

    # Build alert message
    message = (
        f"🔴 You Are Loved — Incident Alert\n"
        f"Time: {ts}\n"
        f"Detected: {layer} — {detail}\n"
        f"Device: {hostname}"
    )

    # Blur screenshot if available
    blur_path = ""
    if full_img:
        blur_path = _create_blurred_screenshot(full_img)

    email_subject = f"[You Are Loved] Incident detected — {ts}"

    def _alert_worker():
        for partner in partners:
            email = partner.get("email", "")
            tg_chat = partner.get("telegram_chat_id", "")

            # Telegram
            if tg_token and tg_chat:
                try:
                    _send_telegram(tg_token, tg_chat, message, blur_path)
                    log.info(f"  ALERT: Telegram sent to {tg_chat}")
                except Exception as e:
                    log.error(f"  ALERT: Telegram failed for {tg_chat}: {e}")

            # Email
            if sg_key and email:
                try:
                    _send_email_alert(sg_key, email, email_subject, message)
                    log.info(f"  ALERT: Email sent to {email}")
                except Exception as e:
                    log.error(f"  ALERT: Email failed for {email}: {e}")

    # Fire in background thread — never block response
    t = threading.Thread(target=_alert_worker, daemon=True)
    t.start()
    log.info(f"  ALERTS: Firing to {len(partners)} partner(s) (background)")

# ---------------------------------------------------------------------------
# First-Run Setup (multi-partner)
# ---------------------------------------------------------------------------

def first_run_setup():
    cfg = load_config()
    if cfg.get("setup_complete"):
        return cfg

    # If no terminal (running as daemon), skip interactive setup
    # Guardian will run with whatever config exists — setup.py handles config
    if not sys.stdin.isatty():
        log.warning("No setup completed and no terminal available.")
        log.warning("Run setup: python3 ~/youareloved/setup.py")
        log.warning("Guardian will run with limited functionality until setup completes.")
        return cfg

    log.info("=" * 50)
    log.info("FIRST RUN SETUP")
    log.info("=" * 50)

    print("\n" + "=" * 50)
    print("  You Are Loved — First Run Setup")
    print("=" * 50)

    # Partner count
    num_partners = 0
    while num_partners < 1 or num_partners > 5:
        try:
            num_partners = int(input(
                "\nHow many accountability partners? (1-5): ").strip())
        except ValueError:
            pass

    partners = []
    for i in range(1, num_partners + 1):
        print(f"\n--- Partner {i} ---")
        email = ""
        while not email:
            email = input(f"  Partner {i} email: ").strip()
            if "@" not in email:
                print("  Please enter a valid email address.")
                email = ""
        telegram = input(
            f"  Partner {i} Telegram username (optional, e.g. @john): "
        ).strip()
        partners.append({"email": email, "telegram": telegram,
                         "telegram_chat_id": ""})

    # API keys
    print("\n--- API Configuration ---")
    print("  (Press Enter to skip any — you can add these later)")

    sg_key = input("\n  SendGrid API key: ").strip()
    tg_token = input("  Telegram bot token: ").strip()
    anthropic_key = input("  Anthropic API key: ").strip()

    # If Telegram bot token provided, try to resolve chat IDs
    if tg_token:
        print("\n  Resolving Telegram chat IDs...")
        print("  Each partner needs to send /start to your bot first.")
        input("  Press Enter when ready...")
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{tg_token}/getUpdates")
            resp = urllib.request.urlopen(req, timeout=10)
            updates = json.loads(resp.read().decode())
            chats = {}
            for update in updates.get("result", []):
                msg = update.get("message", {})
                chat = msg.get("chat", {})
                username = chat.get("username", "")
                chat_id = str(chat.get("id", ""))
                if username:
                    chats[f"@{username}".lower()] = chat_id
                    chats[username.lower()] = chat_id
            for p in partners:
                tg = p.get("telegram", "").lower().lstrip("@")
                if tg:
                    cid = chats.get(tg, "") or chats.get(f"@{tg}", "")
                    if cid:
                        p["telegram_chat_id"] = cid
                        print(f"  ✓ Resolved {p['telegram']} → chat_id {cid}")
                    else:
                        print(f"  ⚠ Could not resolve {p['telegram']} "
                              f"— they need to /start the bot")
        except Exception as e:
            print(f"  ⚠ Telegram resolution failed: {e}")

    # Generate uninstall code
    code = f"{secrets.randbelow(1000000):06d}"
    code_hash = hash_code(code)

    # Build config
    cfg = {
        "setup_complete": True,
        "partners": partners,
        "code_hash": code_hash,
        "installed_at": datetime.now().isoformat(),
        "guardian_path": str(GUARDIAN_PATH),
        "sendgrid_api_key": sg_key,
        "telegram_bot_token": tg_token,
        "anthropic_api_key": anthropic_key,
    }
    save_config(cfg)

    # Send code to partners — NEVER show to installer
    print(f"\n{'='*50}")
    print(f"  Sending uninstall code to your partner(s)...")
    print(f"{'='*50}")

    code_sent = False
    for p in partners:
        email = p.get("email", "")
        tg_chat = p.get("telegram_chat_id", "")

        # Email the code
        if sg_key and email:
            try:
                _send_email_alert(
                    sg_key, email,
                    "Your You Are Loved uninstall code",
                    f"Your accountability partner has installed You Are Loved.\n\n"
                    f"Your uninstall code is: {code}\n\n"
                    f"Keep this safe — they will need it to uninstall.\n\n"
                    f"— You Are Loved"
                )
                print(f"  ✓ Code emailed to {email}")
                code_sent = True
            except Exception as e:
                print(f"  ⚠ Email failed for {email}: {e}")

        # Telegram the code
        if tg_token and tg_chat:
            try:
                _send_telegram(
                    tg_token, tg_chat,
                    f"You've been listed as an accountability partner on "
                    f"You Are Loved.\n\n"
                    f"Your uninstall code is: {code}\n\n"
                    f"Keep this safe — they will need it to uninstall."
                )
                print(f"  ✓ Code sent via Telegram to {p.get('telegram', tg_chat)}")
                code_sent = True
            except Exception as e:
                print(f"  ⚠ Telegram failed for {p.get('telegram', '')}: {e}")

    if code_sent:
        print(f"\n  The uninstall code has been sent directly to your partner(s).")
        print(f"  You will not see it.")
    else:
        # Fallback: if no channels worked, show code as last resort
        print(f"\n  ⚠ Could not send code to any partner.")
        print(f"  UNINSTALL CODE: {code}")
        print(f"  Send this to your partner(s) manually.")
        print(f"  This will NOT be shown again.")

    # Send welcome messages
    print(f"\n  Sending welcome messages to partner(s)...")
    welcome = (
        "You have been listed as an accountability partner on You Are Loved. "
        "You will receive alerts if content is detected on this device. "
        "You do not need to install anything."
    )
    for p in partners:
        if sg_key and p.get("email"):
            try:
                _send_email_alert(sg_key, p["email"],
                    "You Are Loved — Accountability Partner",
                    welcome + "\n\n— You Are Loved")
            except Exception:
                pass
        if tg_token and p.get("telegram_chat_id"):
            try:
                _send_telegram(tg_token, p["telegram_chat_id"], welcome)
            except Exception:
                pass

    print(f"\n{'='*50}")
    log.info(f"Setup complete. {len(partners)} partner(s) configured.")
    input("\nPress Enter once your partner(s) have confirmed receipt...")
    return cfg

def _send_email(api_key: str, to_email: str, code: str):
    """Legacy email sender for backward compat."""
    _send_email_alert(api_key, to_email,
        "You Are Loved — Uninstall Code",
        f"Someone you care about has installed You Are Loved "
        f"and chosen you as their accountability partner.\n\n"
        f"Uninstall code: {code}\n\n"
        f"Keep this code safe.\n\n— You Are Loved")

# ---------------------------------------------------------------------------
# Tamper Detection (from guardian.py v8.1)
# ---------------------------------------------------------------------------

def check_tamper():
    cfg = load_config()
    if not cfg.get("setup_complete"):
        return
    tampered = []
    gp = Path(cfg.get("guardian_path", GUARDIAN_PATH))
    if not gp.exists():
        tampered.append(f"guardian.py missing from {gp}")
    if not PLIST_PATH.exists():
        tampered.append(f"LaunchAgent plist missing")
    if tampered:
        msg = " | ".join(tampered)
        log.warning(f"TAMPER DETECTED: {msg}")
        log_incident("TAMPER", msg)
        # Alert all partners
        partners = get_partners()
        sg_key = get_sendgrid_key()
        tg_token = get_telegram_token()
        for p in partners:
            if sg_key and p.get("email"):
                try:
                    _send_email_alert(sg_key, p["email"],
                        "⚠️ You Are Loved — Tamper Attempt",
                        f"Tamper detected.\nDetail: {msg}\n"
                        f"Time: {datetime.now().isoformat()}\n\n— You Are Loved")
                except Exception:
                    pass
            if tg_token and p.get("telegram_chat_id"):
                try:
                    _send_telegram(tg_token, p["telegram_chat_id"],
                        f"⚠️ Tamper attempt detected\n{msg}\n"
                        f"Time: {datetime.now().isoformat()}")
                except Exception:
                    pass
        if not PLIST_PATH.exists():
            _recreate_plist()

def _send_tamper_alert(api_key: str, to_email: str, detail: str):
    data = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": "guardian@youareloved.app", "name": "You Are Loved"},
        "subject": "⚠️ You Are Loved — Tamper Attempt",
        "content": [{"type": "text/plain", "value": (
            f"Tamper detected.\nDetail: {detail}\n"
            f"Time: {datetime.now().isoformat()}\n\n— You Are Loved"
        )}]
    }).encode()
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send", data=data,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"}, method="POST")
    urllib.request.urlopen(req, timeout=10)

def _recreate_plist():
    try:
        plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.youareloved.guardian</string>
<key>ProgramArguments</key><array>
<string>{sys.executable}</string><string>{GUARDIAN_PATH}</string>
</array>
<key>RunAtLoad</key><true/>
<key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>/tmp/yal.log</string>
<key>StandardErrorPath</key><string>/tmp/yal.error.log</string>
<key>ThrottleInterval</key><integer>10</integer>
</dict></plist>'''
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLIST_PATH.write_text(plist)
        subprocess.run(["launchctl", "load", str(PLIST_PATH)],
                       capture_output=True, timeout=5)
        log.info("TAMPER: Plist recreated")
    except Exception as e:
        log.error(f"TAMPER: Plist recreation failed: {e}")

# ---------------------------------------------------------------------------
# Auto-Update (interval polling, async)
# ---------------------------------------------------------------------------

def _read_last_update_check_ts() -> int:
    try:
        if UPDATE_STATE_FILE.exists():
            return int(UPDATE_STATE_FILE.read_text().strip() or "0")
    except Exception as e:
        log.debug(f"UPDATE: State read failed: {e}")
    return 0

def _write_last_update_check_ts(ts: int):
    try:
        UPDATE_STATE_FILE.write_text(str(int(ts)))
    except Exception as e:
        log.error(f"UPDATE: State write failed — {e}")

def maybe_start_update_check_async():
    global UPDATE_IN_PROGRESS
    now = int(time.time())
    with UPDATE_LOCK:
        if UPDATE_IN_PROGRESS:
            return
        last_ts = _read_last_update_check_ts()
        if last_ts and (now - last_ts) < UPDATE_INTERVAL_SECONDS:
            return
        _write_last_update_check_ts(now)
        UPDATE_IN_PROGRESS = True
        try:
            t = threading.Thread(target=check_for_updates, daemon=True)
            t.start()
            log.info(f"UPDATE: Scheduled async check (interval={UPDATE_INTERVAL_SECONDS}s)")
        except Exception as e:
            UPDATE_IN_PROGRESS = False
            log.error(f"UPDATE: Failed to start async check — {e}")

def check_for_updates():
    """Check for updates via bootstrap JSON (async worker, interval-gated by scheduler)."""
    global UPDATE_IN_PROGRESS
    try:
        # Fetch bootstrap
        with urllib.request.urlopen(UPDATE_BOOTSTRAP_URL, timeout=10) as r:
            bootstrap = json.loads(r.read())

        remote_version = bootstrap["version"]
        guardian_url = bootstrap["guardian_url"]

        try:
            local_version_int = int(VERSION)
            remote_version_int = int(str(remote_version))
        except Exception:
            log.error(f"UPDATE: Malformed remote version '{remote_version}' — skipping")
            return

        if remote_version_int <= local_version_int:
            log.info(f"UPDATE: No upgrade needed — local v{VERSION}, remote v{remote_version}")
            return

        log.info(f"UPDATE: Available v{VERSION} → v{remote_version}")

        # Download, validate, backup, replace, restart
        new_path = str(GUARDIAN_PATH.parent / "guardian_new.py")
        with urllib.request.urlopen(guardian_url, timeout=30) as r:
            new_code = r.read()
        with open(new_path, "wb") as f:
            f.write(new_code)

        result = subprocess.run(
            [sys.executable, "-m", "py_compile", new_path],
            capture_output=True)
        if result.returncode != 0:
            log.error("UPDATE: Validation failed — staying on current")
            os.unlink(new_path)
            return

        import shutil
        shutil.copy2(str(GUARDIAN_PATH), str(GUARDIAN_PATH) + ".backup")
        shutil.move(new_path, str(GUARDIAN_PATH))
        log.info(f"UPDATE: Updated to v{remote_version} — restarting")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        log.error(f"UPDATE: Check failed — {e} — continuing v{VERSION}")
    finally:
        with UPDATE_LOCK:
            UPDATE_IN_PROGRESS = False

# ---------------------------------------------------------------------------
# Memory (unified — Claude-confirmed discipline)
# ---------------------------------------------------------------------------

def load_memory() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except Exception:
            pass
    return {"urls": {}, "domains": {}}

def save_memory(mem: dict):
    try:
        MEMORY_FILE.write_text(json.dumps(mem, indent=2))
    except Exception as e:
        log.error(f"Memory save failed: {e}")

def purge_old_memory():
    mem = load_memory()
    cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    changed = False
    for store in ["urls", "domains"]:
        to_remove = [k for k, v in mem.get(store, {}).items()
                     if v.get("first_seen", "") < cutoff]
        for k in to_remove:
            del mem[store][k]
            changed = True
    if changed:
        save_memory(mem)
        log.info("  Memory: purged entries older than 30 days")

def learn_url_from_claude(url: str):
    """ONLY called after Claude YES in Layer C."""
    if not url or is_safe_url(url):
        return
    mem = load_memory()
    domain = ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = parsed.netloc.lower().replace("www.", "")
    except Exception:
        pass
    ts = datetime.now().isoformat()
    if url not in mem["urls"]:
        mem["urls"][url] = {"reason": "CLAUDE_CONFIRMED", "first_seen": ts, "count": 1}
        log.info(f"  MEMORY LEARNED (Claude): {url[:80]}")
    else:
        mem["urls"][url]["count"] += 1
    if domain and domain not in mem["domains"]:
        mem["domains"][domain] = {"reason": "CLAUDE_CONFIRMED", "first_seen": ts, "count": 1}
    elif domain:
        mem["domains"][domain]["count"] += 1
    save_memory(mem)

def learn_url_visual(url: str):
    """Called after NudeNet visual detection."""
    if not url or is_safe_url(url):
        return
    mem = load_memory()
    domain = ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = parsed.netloc.lower().replace("www.", "")
    except Exception:
        pass
    ts = datetime.now().isoformat()
    if url not in mem["urls"]:
        mem["urls"][url] = {"reason": "VISUAL_CONFIRMED", "first_seen": ts, "count": 1}
        log.info(f"  MEMORY LEARNED (visual): {url[:80]}")
    else:
        mem["urls"][url]["count"] += 1
    if domain and domain not in mem["domains"]:
        mem["domains"][domain] = {"reason": "VISUAL_CONFIRMED", "first_seen": ts, "count": 1}
    elif domain:
        mem["domains"][domain]["count"] += 1
    save_memory(mem)

def validate_memory_hit(url: str) -> bool:
    if is_safe_url(url):
        return False
    mem = load_memory()
    entry = mem.get("urls", {}).get(url)
    if not entry:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url.lower() if "://" in url.lower() else f"https://{url.lower()}")
            domain = parsed.netloc.replace("www.", "")
            entry = mem.get("domains", {}).get(domain)
        except Exception:
            pass
    if not entry:
        return False
    reason = entry.get("reason", "")
    if reason not in ("CLAUDE_CONFIRMED", "VISUAL_CONFIRMED"):
        _purge_memory_entry(url)
        return False
    url_lower = url.lower().replace(".", "")
    if not any(t in url_lower for t in ALL_NSFW_TERMS):
        _purge_memory_entry(url)
        return False
    return True

def _purge_memory_entry(url: str):
    mem = load_memory()
    if url in mem.get("urls", {}):
        del mem["urls"][url]
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url.lower() if "://" in url.lower() else f"https://{url.lower()}")
        domain = parsed.netloc.replace("www.", "")
        if domain in mem.get("domains", {}):
            del mem["domains"][domain]
    except Exception:
        pass
    save_memory(mem)

# ---------------------------------------------------------------------------
# Audit (from guardian.py v8.1)
# ---------------------------------------------------------------------------

def save_audit(mon_idx: int, tile_name: str, results: list,
               full_img, tile_img, url: str, detail: str):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now()
    ts_str = ts.strftime("%Y%m%d_%H%M%S")
    incident_dir = AUDIT_DIR / f"incident_{ts_str}"
    incident_dir.mkdir(exist_ok=True)
    full_img.save(str(incident_dir / f"monitor_{mon_idx}_full.png"))
    tile_img.save(str(incident_dir / f"monitor_{mon_idx}_tile_{tile_name}.png"))
    meta = {
        "timestamp": ts.isoformat(), "monitor": mon_idx,
        "tile": tile_name, "tile_size": list(tile_img.size),
        "threshold": TRIGGER_THRESHOLD,
        "detections": [{"class": d.get("class", ""),
                        "score": round(d.get("score", 0), 4)} for d in results],
        "trigger_detail": detail, "active_url": url,
    }
    (incident_dir / "incident.json").write_text(json.dumps(meta, indent=2))
    log.info(f"AUDIT: Saved to {incident_dir}")

# ---------------------------------------------------------------------------
# Lazy deps
# ---------------------------------------------------------------------------

_detector = None
_mss = None

def get_detector():
    global _detector
    if _detector is None:
        from nudenet import NudeDetector
        # Use 640m model from our models directory (downloaded during install)
        model_path = Path.home() / "youareloved" / "models" / "640m.onnx"
        if model_path.exists():
            _detector = NudeDetector(
                model_path=str(model_path),
                inference_resolution=640)
            log.info("NudeNet 640m model loaded (high-res)")
        else:
            # Fallback: check ~/.NudeNet
            alt_path = Path.home() / ".NudeNet" / "640m.onnx"
            if alt_path.exists():
                _detector = NudeDetector(
                    model_path=str(alt_path),
                    inference_resolution=640)
                log.info("NudeNet 640m model loaded from ~/.NudeNet")
            else:
                log.warning("640m model not found — using default 320n (lower quality)")
                _detector = NudeDetector()
                log.info("NudeNet 320n model loaded")
    return _detector

def get_mss():
    global _mss
    if _mss is None:
        import mss as _mss_mod
        _mss = _mss_mod.mss()
    return _mss

# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------

def capture_screenshots() -> list:
    """Capture screen using multiple methods until one works.
    
    Method 1: Quartz CGWindowListCreateImage (direct API, fastest)
    Method 2: screencapture CLI at /usr/sbin/screencapture
    Method 3: mss library
    
    All require Screen Recording permission for the Python binary.
    """
    from PIL import Image
    import tempfile

    # Method 1: Quartz direct (fastest, most reliable when permission granted)
    try:
        import Quartz
        region = Quartz.CGRectInfinite
        image = Quartz.CGWindowListCreateImage(
            region,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault)
        if image is not None:
            w = Quartz.CGImageGetWidth(image)
            h = Quartz.CGImageGetHeight(image)
            if w > 0 and h > 0:
                # Convert CGImage to PIL
                bpr = Quartz.CGImageGetBytesPerRow(image)
                provider = Quartz.CGImageGetDataProvider(image)
                data = Quartz.CGDataProviderCopyData(provider)
                img = Image.frombuffer("RGBA", (w, h), data, "raw", "BGRA", bpr, 1)
                img = img.convert("RGB")
                # Verify not black
                px = list(img.getdata())[:200]
                if not all(p == (0, 0, 0) for p in px):
                    return [img]
                log.debug("  Quartz returned black image (no permission)")
        log.debug("  Quartz CGWindowListCreateImage returned None")
    except Exception as e:
        log.debug(f"  Quartz capture failed: {e}")

    # Method 2: screencapture CLI
    try:
        tmpfile = tempfile.mktemp(suffix=".png")
        r = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-C", tmpfile],
            capture_output=True, timeout=10)
        if r.returncode == 0 and os.path.exists(tmpfile) and os.path.getsize(tmpfile) > 1000:
            img = Image.open(tmpfile)
            img.load()
            os.unlink(tmpfile)
            px = list(img.getdata())[:200]
            if not all(p == (0, 0, 0) for p in px):
                return [img]
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)
    except Exception as e:
        log.debug(f"  screencapture failed: {e}")

    # Method 3: mss library
    try:
        sct = get_mss()
        images = []
        for mon in sct.monitors[1:]:
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            px = list(img.getdata())[:200]
            if not all(p == (0, 0, 0) for p in px):
                images.append(img)
        if images:
            return images
    except Exception as e:
        log.debug(f"  mss failed: {e}")

    raise PermissionError(
        "Screen capture failed — add Python to Screen Recording: "
        "System Settings → Privacy & Security → Screen & System Audio Recording → "
        "click '+' → Cmd+Shift+G → paste: "
        + (subprocess.run(["which", "python3.11"], capture_output=True, text=True).stdout.strip()
           or "/opt/homebrew/opt/python@3.11/bin/python3.11")
    )

# ---------------------------------------------------------------------------
# AppleScript
# ---------------------------------------------------------------------------

def _osascript(script: str) -> str:
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except Exception:
        return ""

def get_active_url() -> str:
    url = _osascript('''
tell application "System Events"
    if exists (process "Google Chrome") then
        tell application "Google Chrome"
            try
                return URL of active tab of front window
            end try
        end tell
    end if
end tell
''')
    if url:
        return url
    return _osascript('''
tell application "System Events"
    if exists (process "Safari") then
        tell application "Safari"
            try
                return URL of current tab of front window
            end try
        end tell
    end if
end tell
''') or ""

# ---------------------------------------------------------------------------
# Text scanning helper
# ---------------------------------------------------------------------------

def scan_text_tiers(text: str, source_id: str, url: str = "") -> tuple:
    text_lower = text.lower()
    text_nodots = text_lower.replace(".", "")
    for pat in _EXPLICIT_RE:
        m = pat.search(text_lower) or pat.search(text_nodots)
        if m:
            return True, f"explicit='{m.group()}' source={source_id}", []
    ambiguous = []
    seen = set()
    for pat in _AMBIGUOUS_RE:
        m = pat.search(text_lower)
        if m and m.group() not in seen:
            seen.add(m.group())
            idx = m.start()
            start = max(0, idx - 150)
            end = min(len(text), idx + len(m.group()) + 150)
            context = text[start:end].strip()
            ambiguous.append((source_id, m.group(), context, url))
    return False, "", ambiguous

# ---------------------------------------------------------------------------
# Tiling (from guardian.py v8.1)
# ---------------------------------------------------------------------------

def make_grid(img, n: int, prefix: str = "g") -> list:
    w, h = img.size
    tw, th = w // n, h // n
    tiles = []
    for row in range(n):
        for col in range(n):
            x1 = col * tw
            y1 = row * th
            x2 = x1 + tw if col < n - 1 else w
            y2 = y1 + th if row < n - 1 else h
            tiles.append((f"{prefix}{row}{col}", img.crop((x1, y1, x2, y2)),
                          (x1, y1, x2, y2)))
    return tiles

def make_overlaps(img, n: int) -> list:
    w, h = img.size
    tw, th = w // n, h // n
    ox, oy = tw // 2, th // 2
    tiles = []
    for row in range(n - 1):
        for col in range(n - 1):
            x1 = max(0, col * tw + ox)
            y1 = max(0, row * th + oy)
            x2 = min(w, x1 + tw)
            y2 = min(h, y1 + th)
            if x2 - x1 > 50 and y2 - y1 > 50:
                tiles.append((f"o{row}{col}", img.crop((x1, y1, x2, y2)),
                              (x1, y1, x2, y2)))
    return tiles

# ---------------------------------------------------------------------------
# NudeNet helpers (from guardian.py v8.1)
# ---------------------------------------------------------------------------

def fmt_detections(results: list) -> str:
    if not results:
        return "[]"
    return "[" + ", ".join(
        f"{{'class': '{d.get('class','')}', 'score': {d.get('score',0):.3f}}}"
        for d in results) + "]"

def has_interest(results: list) -> bool:
    return any(d.get("class", "") in NUDENET_INTEREST_LABELS
               and d.get("score", 0) >= DETECTION_ANY for d in results)

def check_triggered(results: list) -> tuple:
    for d in results:
        if d.get("class", "") in NUDENET_TRIGGER_LABELS \
           and d.get("score", 0) >= TRIGGER_THRESHOLD:
            return True, f"label={d['class']} score={d['score']:.3f}"
    return False, ""

def scan_tile(detector, tile_name: str, tile_img, mon_idx: int) -> tuple:
    path = f"/tmp/yal_tile_{mon_idx}_{tile_name}.png"
    tile_img.save(path)
    try:
        results = detector.detect(path)
    except Exception as e:
        log.error(f"    NudeNet error on {tile_name}: {e}")
        return [], False, ""
    # Filter to only relevant classes (ignore FACE_MALE, etc.)
    relevant = [d for d in results 
                if d.get("class", "") in NUDENET_TRIGGER_LABELS | NUDENET_INTEREST_LABELS
                and d.get("score", 0) >= 0.10]
    if relevant:
        log.info(f"    {tile_name} ({tile_img.size[0]}x{tile_img.size[1]}): "
                 f"{len(relevant)} detection(s)")
        for d in relevant:
            score = d.get('score', 0)
            cls = d.get('class', '')
            marker = "🔴" if cls in NUDENET_TRIGGER_LABELS and score >= TRIGGER_THRESHOLD else "🟡"
            log.info(f"      {marker} {cls}: {score:.3f}")
    triggered, detail = check_triggered(results)
    return results, triggered, detail

# ═══════════════════════════════════════════════════════════════════════════
# LAYER P — Process Check
# ═══════════════════════════════════════════════════════════════════════════

def layer_P() -> tuple:
    log.info("LAYER P — Process Check")
    try:
        r = subprocess.run(["ps", "-eo", "comm="],
                           capture_output=True, text=True, timeout=5)
        running = {line.strip().split("/")[-1] for line in r.stdout.split("\n")}
    except Exception:
        running = set()
    found = running & SUSPECT_PROCESSES
    if found:
        detail = f"suspect_process={list(found)}"
        log.info(f"  ✗ FOUND: {found}")
        return True, detail
    log.info(f"  Process check: ✓")
    return False, ""

# ═══════════════════════════════════════════════════════════════════════════
# LAYER T2 — Browser Tab Intelligence
# ═══════════════════════════════════════════════════════════════════════════

def layer_T2() -> tuple:
    log.info("LAYER T2 — Browser Tab Intelligence")
    raw_tabs = []
    chrome = _osascript('''
tell application "System Events"
    if exists (process "Google Chrome") then
        tell application "Google Chrome"
            set out to ""
            repeat with w in windows
                repeat with t in tabs of w
                    set out to out & URL of t & "|||" & title of t & linefeed
                end repeat
            end repeat
            return out
        end tell
    end if
end tell
''')
    for line in chrome.split("\n"):
        if "|||" in line:
            u, t = line.split("|||", 1)
            raw_tabs.append(("Chrome", u.strip(), t.strip()))
    safari = _osascript('''
tell application "System Events"
    if exists (process "Safari") then
        tell application "Safari"
            set out to ""
            repeat with w in windows
                repeat with t in tabs of w
                    set out to out & URL of t & "|||" & name of t & linefeed
                end repeat
            end repeat
            return out
        end tell
    end if
end tell
''')
    for line in safari.split("\n"):
        if "|||" in line:
            u, t = line.split("|||", 1)
            raw_tabs.append(("Safari", u.strip(), t.strip()))

    tabs = []
    safe_count = 0
    for browser, url, title in raw_tabs:
        if is_safe_url(url):
            safe_count += 1
        else:
            tabs.append((browser, url, title))
            log.info(f"    [{browser}] {title[:60]}")

    log.info(f"  Total: {len(raw_tabs)} ({safe_count} safe, {len(tabs)} scanned)")

    all_ambiguous = []
    tab_data = [(url, title) for _, url, title in tabs]

    for browser, url, title in tabs:
        combined = url + " " + title
        explicit, detail, ambiguous = scan_text_tiers(combined,
                                                       f"tab:{browser}", url)
        if explicit:
            log.info(f"  ✗ TIER 1: {detail}")
            return True, detail, [], tab_data
        all_ambiguous.extend(ambiguous)

        # Multi-ambiguous auto-escalation: 2+ distinct ambiguous terms
        # in the same tab = treat as explicit (e.g. "nude" + "ass")
        distinct_terms = set(a[1] for a in ambiguous)
        if len(distinct_terms) >= 2:
            terms = sorted(distinct_terms)
            detail = (f"multi-ambiguous={'+'.join(terms)} "
                      f"tab:{browser} url={url[:80]}")
            log.info(f"  ✗ MULTI-AMBIGUOUS → EXPLICIT: {detail}")
            return True, detail, [], tab_data

    # Also check across all tabs — if 3+ distinct ambiguous across all tabs
    all_distinct = set(a[1] for a in all_ambiguous)
    if len(all_distinct) >= 3:
        terms = sorted(all_distinct)
        detail = (f"cross-tab-ambiguous={'+'.join(terms[:5])} "
                  f"({len(all_distinct)} terms)")
        log.info(f"  ✗ CROSS-TAB AMBIGUOUS → EXPLICIT: {detail}")
        return True, detail, [], tab_data

    if all_ambiguous:
        log.info(f"  Tier 2 ambiguous: {len(all_ambiguous)} "
                 f"({', '.join(sorted(set(a[1] for a in all_ambiguous)))})")
    else:
        log.info(f"  No matches")

    log.info(f"  Layer T2: CLEAR")
    return False, "", all_ambiguous, tab_data

# ═══════════════════════════════════════════════════════════════════════════
# LAYER T3 — Confirmed Memory Recall
# ═══════════════════════════════════════════════════════════════════════════

def layer_T3(tab_data: list) -> tuple:
    log.info("LAYER T3 — Confirmed Memory Recall")
    mem = load_memory()
    known_urls = set(mem.get("urls", {}).keys())
    known_domains = set(mem.get("domains", {}).keys())
    if not known_urls and not known_domains:
        log.info(f"  Memory empty")
        log.info(f"  Layer T3: CLEAR")
        return False, ""
    log.info(f"  Memory: {len(known_urls)} URLs, {len(known_domains)} domains")
    for url, title in tab_data:
        if is_safe_url(url):
            continue
        domain = ""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url.lower() if "://" in url.lower()
                              else f"https://{url.lower()}")
            domain = parsed.netloc.replace("www.", "")
        except Exception:
            pass
        if url in known_urls or domain in known_domains:
            log.info(f"  Memory candidate: {url[:80]}")
            if validate_memory_hit(url):
                log.info(f"  ✗ VALID MEMORY HIT")
                return True, f"memory_hit url='{url[:80]}'"
            else:
                log.info(f"  Invalid — purged")
    log.info(f"  Layer T3: CLEAR")
    return False, ""

# ═══════════════════════════════════════════════════════════════════════════
# LAYER T1 — OCR Surface Scan
# ═══════════════════════════════════════════════════════════════════════════

def layer_T1(images: list) -> tuple:
    from PIL import Image
    log.info(f"LAYER T1 — OCR Surface Scan (3x3, {len(images)} monitor(s))")
    if not HAS_TESSERACT:
        log.info(f"  pytesseract unavailable — skipping")
        return False, "", [], 0
    total_words = 0
    all_ambiguous = []
    for mon_idx, img in enumerate(images):
        w, h = img.size
        tw, th = w // 3, h // 3
        mon_words = 0
        log.info(f"  Monitor {mon_idx}: {w}x{h}")
        for row in range(3):
            for col in range(3):
                x1, y1 = col * tw, row * th
                x2 = x1 + tw if col < 2 else w
                y2 = y1 + th if row < 2 else h
                tile_id = f"mon{mon_idx}_r{row}c{col}"
                tile = img.crop((x1, y1, x2, y2))
                small = tile.resize((tile.width // 2, tile.height // 2),
                                    Image.LANCZOS)
                try:
                    text = pytesseract.image_to_string(small, timeout=8)
                except Exception:
                    continue
                if not text.strip():
                    continue
                mon_words += len(text.split())
                if any(p in text.lower() for p in OCR_SUPPRESS):
                    continue
                explicit, detail, ambiguous = scan_text_tiers(text,
                                                               f"ocr:{tile_id}")
                if explicit:
                    log.info(f"  ✗ TIER 1: {detail}")
                    return True, detail, [], total_words + mon_words
                all_ambiguous.extend(ambiguous)
        total_words += mon_words
        log.info(f"    Extracted: {mon_words} words")
    if all_ambiguous:
        log.info(f"  Tier 2 ambiguous: {len(all_ambiguous)}")
    log.info(f"  Layer T1: CLEAR ({total_words} words)")
    return False, "", all_ambiguous, total_words

# ═══════════════════════════════════════════════════════════════════════════
# LAYER V — Visual Scan (NudeNet adaptive two-pass)
# ═══════════════════════════════════════════════════════════════════════════

def layer_V(images: list) -> tuple:
    log.info(f"LAYER V — NudeNet Adaptive Scan")
    log.info(f"  Pass 1: {COARSE_GRID}x{COARSE_GRID} coarse | "
             f"Pass 2: {FINE_GRID}x{FINE_GRID} fine on hot tiles")
    log.info(f"  Trigger: {TRIGGER_THRESHOLD} | Interest: {DETECTION_ANY}")
    detector = get_detector()
    for mon_idx, img in enumerate(images):
        log.info(f"  Monitor {mon_idx}: {img.size[0]}x{img.size[1]}")
        log.info(f"  PASS 1 — Coarse {COARSE_GRID}x{COARSE_GRID}")
        coarse = make_grid(img, COARSE_GRID, prefix="c")
        overlaps = make_overlaps(img, COARSE_GRID)
        all_coarse = coarse + overlaps
        full_r, full_t, full_d = scan_tile(detector, "full", img, mon_idx)
        if full_t:
            log.warning(f"  >>> NSFW on full image: {fmt_detections(full_r)}")
            return True, full_d, mon_idx, "full", full_r, img, img
        hot = []
        for name, tile, box in all_coarse:
            r, t, d = scan_tile(detector, name, tile, mon_idx)
            if t:
                log.warning(f"  >>> NSFW on '{name}': {fmt_detections(r)}")
                return True, d, mon_idx, name, r, img, tile
            if has_interest(r):
                hot.append((name, tile, box, r))
        if hot:
            log.info(f"  PASS 2 — Fine scan on {len(hot)} hot tile(s)")
            for pname, pimg, pbox, pr in hot:
                log.info(f"    Subdividing '{pname}' "
                         f"({pimg.size[0]}x{pimg.size[1]}) into {FINE_GRID}x{FINE_GRID}")
                subs = make_grid(pimg, FINE_GRID, prefix=f"{pname}_f")
                for sname, simg, sbox in subs:
                    r, t, d = scan_tile(detector, sname, simg, mon_idx)
                    if t:
                        log.warning(f"  >>> NSFW on '{sname}' (parent: {pname}): "
                                    f"{fmt_detections(r)}")
                        return True, d, mon_idx, sname, r, img, simg
        else:
            log.info(f"  PASS 2 — No hot tiles, skipped")
    log.info(f"  Layer V: CLEAR")
    return False, "", -1, "", [], None, None

# ═══════════════════════════════════════════════════════════════════════════
# LAYER C — Claude Contextual Classification (batched)
# ═══════════════════════════════════════════════════════════════════════════

CLAUDE_SYSTEM_PROMPT = (
    "You are a binary content safety classifier for a pornography "
    "accountability tool.\n\n"
    "Below are text fragments detected on a user's screen. For each one, "
    "determine whether it provides strong contextual evidence the user is "
    "actively viewing pornographic or sexually explicit content.\n\n"
    "Consider full context carefully. Common words are not sufficient alone.\n\n"
    "For each fragment, respond with only the number and YES or NO:\n"
    "1: NO\n2: YES"
)

def layer_C(ambiguous_all: list) -> tuple:
    if not ambiguous_all:
        log.info("LAYER C — Claude Classification")
        log.info("  No ambiguous matches — skipped")
        return False, ""
    api_key = get_api_key()
    log.info(f"LAYER C — Claude Classification "
             f"({len(ambiguous_all)} fragment(s), 1 API call)")
    if not api_key:
        log.info("  ⚠ No API key — skipped")
        return False, ""
    fragments = ""
    for i, (src, word, ctx, url) in enumerate(ambiguous_all, 1):
        fragments += f'{i}. [{word}]: "{ctx[:300]}"\n'
        log.info(f"  Fragment {i}: '{word}' from {src}")
    try:
        data = json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 100,
            "system": CLAUDE_SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": f"Fragments:\n{fragments}"}],
        }).encode()
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=data,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode())
        answer = "".join(b.get("text", "") for b in result.get("content", [])
                         if b.get("type") == "text")
        log.info(f"  Claude: {answer.strip()}")
        triggered = []
        for line in answer.strip().split("\n"):
            m = re.match(r'(\d+)\s*:\s*(YES|NO)', line, re.IGNORECASE)
            if m and m.group(2).upper() == "YES":
                idx = int(m.group(1))
                if 1 <= idx <= len(ambiguous_all):
                    triggered.append(idx)
        if triggered:
            for idx in triggered:
                src, word, ctx, url = ambiguous_all[idx - 1]
                if url:
                    learn_url_from_claude(url)
                log.info(f"  ✗ Fragment {idx} confirmed: '{word}'")
            first = triggered[0]
            src, word, ctx, url = ambiguous_all[first - 1]
            detail = f"claude=YES word='{word}' source={src}"
            if url:
                detail += f" url='{url[:80]}'"
            return True, detail
    except Exception as e:
        log.error(f"  Claude API error: {e}")
    log.info("  Layer C: CLEAR")
    return False, ""

# ═══════════════════════════════════════════════════════════════════════════
# LAYER B — Behavioral Check
# ═══════════════════════════════════════════════════════════════════════════

def layer_B(tab_count: int) -> tuple:
    hour = datetime.now().hour
    log.info("LAYER B — Behavioral Check")
    if 0 <= hour < 5 and tab_count > 0:
        log.info(f"  ⚠ HIGH RISK: {hour:02d}:00 with {tab_count} browser tabs open")
        log_incident("BEHAVIORAL", f"late_night hour={hour} tabs={tab_count}")
        # Alert all partners
        msg = (f"⚠️ Late night activity detected\n"
               f"Time: {hour:02d}:00 with {tab_count} browser tabs open\n"
               f"Device: {socket.gethostname()}")
        partners = get_partners()
        sg_key = get_sendgrid_key()
        tg_token = get_telegram_token()
        def _beh_alert():
            for p in partners:
                if sg_key and p.get("email"):
                    try:
                        _send_email_alert(sg_key, p["email"],
                            "[You Are Loved] Late night activity", msg)
                    except Exception:
                        pass
                if tg_token and p.get("telegram_chat_id"):
                    try:
                        _send_telegram(tg_token, p["telegram_chat_id"], msg)
                    except Exception:
                        pass
        threading.Thread(target=_beh_alert, daemon=True).start()
        log.info("  Behavioral: ALERT LOGGED (no lock)")
        return False, ""  # Log only, no lock
    log.info(f"  Behavioral: ✓")
    return False, ""

# ═══════════════════════════════════════════════════════════════════════════
# Response
# ═══════════════════════════════════════════════════════════════════════════

def log_incident(reason: str, detail: str):
    ts = datetime.now().isoformat()
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] {reason} | {detail}\n")
    except Exception:
        pass

def get_running_apps() -> list:
    output = _osascript('''
tell application "System Events"
    set appList to ""
    repeat with proc in (every application process whose visible is true)
        set appList to appList & name of proc & linefeed
    end repeat
    return appList
end tell
''')
    return [a.strip() for a in output.split("\n") if a.strip()]

def close_nsfw_window():
    log.info("RESPONSE: Closing content...")
    running = get_running_apps()
    quit_list, closed_list, preserved_list = [], [], []
    for app in running:
        if app in APPS_PRESERVE:
            preserved_list.append(app)
        elif app in APPS_TO_QUIT:
            _osascript(f'tell application "System Events"\n'
                       f'if exists (process "{app}") then\n'
                       f'tell application "{app}" to quit\n'
                       f'end if\nend tell')
            quit_list.append(app)
        elif app in APPS_CLOSE_WINDOWS:
            _osascript(f'tell application "System Events"\n'
                       f'if exists (process "{app}") then\n'
                       f'tell application "{app}"\ntry\n'
                       f'close every window\nend try\n'
                       f'end tell\nend if\nend tell')
            closed_list.append(app)
        else:
            _osascript(f'tell application "System Events"\n'
                       f'if exists (process "{app}") then\n'
                       f'tell process "{app}"\ntry\n'
                       f'keystroke "w" using command down\n'
                       f'end try\nend tell\nend if\nend tell')
            closed_list.append(f"{app} (window)")
    for browser in BROWSERS:
        if browser not in closed_list and browser not in quit_list:
            _osascript(f'tell application "System Events"\n'
                       f'if exists (process "{browser}") then\n'
                       f'tell application "{browser}"\ntry\n'
                       f'close every window\nend try\n'
                       f'end tell\nend if\nend tell')
    if quit_list:
        log.info(f"  QUIT: {', '.join(quit_list)}")
    if closed_list:
        log.info(f"  CLOSED: {', '.join(closed_list)}")
    if preserved_list:
        log.info(f"  PRESERVED: {', '.join(preserved_list)}")
    log.info("RESPONSE: Cleanup complete")

def lock_screen():
    global last_lock_time
    now = time.time()
    if now - last_lock_time < LOCK_COOLDOWN:
        log.info("RESPONSE: Lock cooldown — skipped")
        return
    last_lock_time = now
    _osascript('''
tell application "System Events" to keystroke "q" using {control down, command down}
''')
    log.info("RESPONSE: Screen locked")

def can_show_dialog() -> bool:
    global last_dialog_time
    now = time.time()
    if now - last_dialog_time >= DIALOG_COOLDOWN:
        last_dialog_time = now
        return True
    return False

def show_dialog():
    if not can_show_dialog():
        return
    try:
        subprocess.Popen(["osascript", "-e",
            'display dialog "You are loved.\n\n'
            'Reach out to your accountability partner." '
            'buttons {"I need help 2", "OK"} default button "OK" '
            'with title "You Are Loved" with icon caution'])
        log.info("RESPONSE: Dialog shown")
    except Exception:
        pass

def full_response(layer: str, detail: str, mon_idx=-1, tile_name="",
                  results=None, full_img=None, tile_img=None):
    global in_cooldown
    log.warning(f"{'='*50}")
    log.warning(f"INCIDENT: {layer} | {detail}")
    log.warning(f"{'='*50}")
    log_incident(layer, detail)

    url = get_active_url()
    if url:
        log.info(f"RESPONSE: Active URL: {url}")

    # Save audit if visual data available
    if full_img and tile_img and mon_idx >= 0:
        if url:
            learn_url_visual(url)
        save_audit(mon_idx, tile_name, results or [], full_img, tile_img,
                   url or "", detail)

    # Fire alerts to all partners (non-blocking background thread)
    fire_alerts(layer, detail, full_img)

    close_nsfw_window()
    show_dialog()
    lock_screen()
    in_cooldown = True

# ═══════════════════════════════════════════════════════════════════════════
# MAIN SCAN CYCLE
# ═══════════════════════════════════════════════════════════════════════════

def scan_cycle():
    global scan_count, in_cooldown
    scan_count += 1

    mode, interval = get_scan_mode()
    ts = datetime.now().strftime("%H:%M:%S")
    idle = seconds_idle()

    log.info("")
    log.info(f"{'─'*50}")
    log.info(f"SCAN #{scan_count} at {ts} | {mode}")
    log.info(f"{'─'*50}")

    if idle > IDLE_THRESHOLD_3 and not in_cooldown:
        log.info(f"  User away — skipping")
        return interval

    all_ambiguous = []
    tab_count = 0
    claude_summary = "disabled" if IMAGE_ONLY_MODE else "skipped"

    if not IMAGE_ONLY_MODE:
        # ═══ Layer P: Process Check ═══
        p_hit, p_detail = layer_P()
        if p_hit:
            full_response("PROCESS", p_detail)
            return interval

        # ═══ Layer T2: Browser Tabs ═══
        t2_result = layer_T2()
        t2_hit = t2_result[0]
        if t2_hit:
            full_response("TAB_EXPLICIT", t2_result[1])
            return interval
        t2_ambiguous = t2_result[2]
        tab_data = t2_result[3]
        tab_count = len(tab_data)
        all_ambiguous.extend(t2_ambiguous)

        # ═══ Layer T3: Memory Recall (always before Claude) ═══
        if t2_ambiguous:
            log.info(f"  Ambiguous from T2 — checking memory first")
        t3_hit, t3_detail = layer_T3(tab_data)
        if t3_hit:
            full_response("MEMORY", t3_detail)
            return interval

    # ═══ Layer T1: OCR Surface Scan ═══
    try:
        images = capture_screenshots()
        for i, img in enumerate(images):
            log.info(f"  Monitor {i}: {img.size[0]}x{img.size[1]} captured")
        _screenshot_fails = 0  # reset on success
    except Exception as e:
        log.error(f"  Screenshot failed: {e}")
        images = []
        # Track consecutive failures
        if not hasattr(scan_cycle, '_ss_fails'):
            scan_cycle._ss_fails = 0
        scan_cycle._ss_fails += 1
        # Every 10 failures (~50s), nag the user with notification + open Settings
        if scan_cycle._ss_fails % 10 == 1:
            log.warning("  ⚠ Screen Recording: not granted — opening Settings")
            try:
                subprocess.run([
                    "osascript", "-e",
                    'display notification "Enable Screen Recording for Terminal in System Settings" '
                    'with title "You Are Loved" subtitle "Protection needs screen access"'
                ], capture_output=True, timeout=3)
                subprocess.run([
                    "open",
                    "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
                ], capture_output=True, timeout=3)
                subprocess.run([
                    "osascript", "-e",
                    'tell application "System Settings" to activate'
                ], capture_output=True, timeout=3)
            except Exception:
                pass

    ocr_words = 0
    if images and not IMAGE_ONLY_MODE:
        t1_hit, t1_detail, t1_ambiguous, ocr_words = layer_T1(images)
        if t1_hit:
            full_response("OCR_EXPLICIT", t1_detail)
            return interval
        all_ambiguous.extend(t1_ambiguous)

    # ═══ Layer V: Visual Scan ═══
    visual_summary = "skipped"
    if images:
        v_result = layer_V(images)
        v_hit = v_result[0]
        if v_hit:
            _, v_detail, v_mon, v_tile, v_results, v_full, v_timg = v_result
            full_response("VISUAL", v_detail, v_mon, v_tile,
                          v_results, v_full, v_timg)
            return interval
        visual_summary = (f"{images[0].size[0]}x{images[0].size[1]}"
                          if images else "none")

    # ═══ Layer C: Claude Classification ═══
    if all_ambiguous and not IMAGE_ONLY_MODE:
        log.info(f"  All layers clear — escalating {len(all_ambiguous)} "
                 f"ambiguous to Claude")
        c_hit, c_detail = layer_C(all_ambiguous)
        if c_hit:
            full_response("CLAUDE", c_detail)
            return interval
        claude_summary = f"{len(all_ambiguous)}→clear"

    # ═══ Layer B: Behavioral Check ═══
    if not IMAGE_ONLY_MODE:
        layer_B(tab_count)

    # ═══ All clear ═══
    in_cooldown = False
    log.info(f"SCAN #{scan_count} COMPLETE — ALL CLEAR | "
             f"process:✓ tabs:{tab_count} ocr:{ocr_words}w "
             f"visual:{visual_summary} claude:{claude_summary}")

    if scan_count % 100 == 0:
        check_tamper()

    return interval

# ═══════════════════════════════════════════════════════════════════════════
# IMAGE-ONLY MODE (observational NudeNet evaluation)
# ═══════════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-only", action="store_true", default=False,
                        help="Run only the NudeNet image detection loop (no response/actions)")
    return parser.parse_args()

def _image_only_relevant(results: list) -> list:
    return [d for d in results
            if d.get("class", "") in (NUDENET_TRIGGER_LABELS | NUDENET_INTEREST_LABELS)
            and d.get("score", 0) >= DETECTION_ANY]

def _print_image_only_scan(scan_ts: str, events: list, v_result: tuple, elapsed: float):
    print(f"SCAN START — {scan_ts}")
    print("")
    for idx, evt in enumerate(events, 1):
        mon_idx = evt.get("monitor", -1)
        tile_name = evt.get("tile", "")
        print(f"Tile {idx} (Monitor {mon_idx}, {tile_name}):")
        relevant = evt.get("relevant", [])
        if relevant:
            for d in relevant:
                label = d.get("class", "")
                score = d.get("score", 0.0)
                print(f"  Label: {label}")
                print(f"  Confidence: {score:.2f}")
        else:
            print("  No labels above threshold")
        print(f"  Triggered: {'YES' if evt.get('triggered') else 'NO'}")
        print("")

    v_hit, v_detail = v_result[0], v_result[1]
    if v_hit:
        print("FINAL DECISION: DETECTED")
        print(f"Reason: {v_detail}")
    else:
        print("FINAL DECISION: SAFE")
    print(f"Processing Time: {elapsed:.3f}s")
    print("")

def image_only_scan_cycle():
    started = time.perf_counter()
    scan_ts = datetime.now().isoformat(timespec="seconds")
    events = []

    try:
        images = capture_screenshots()

    except Exception as e:
        elapsed = time.perf_counter() - started
        print(f"SCAN START — {scan_ts}")
        print("")
        print("FINAL DECISION: ERROR")
        print(f"Reason: Screenshot failed: {e}")
        print(f"Processing Time: {elapsed:.3f}s")
        print("")
        return SCAN_ACTIVE

    original_scan_tile = scan_tile

    def wrapped_scan_tile(detector, tile_name: str, tile_img, mon_idx: int):
        results, triggered, detail = original_scan_tile(detector, tile_name, tile_img, mon_idx)
        events.append({
            "monitor": mon_idx,
            "tile": tile_name,
            "relevant": _image_only_relevant(results),
            "triggered": triggered,
            "detail": detail,
        })
        return results, triggered, detail

    try:
        globals()["scan_tile"] = wrapped_scan_tile
        v_result = layer_V(images)
    finally:
        globals()["scan_tile"] = original_scan_tile

    elapsed = time.perf_counter() - started
    _print_image_only_scan(scan_ts, events, v_result, elapsed)
    return SCAN_ACTIVE

def run_image_only_main():
    print("")
    print("=" * 50)
    print(f"  You Are Loved — Guardian v{VERSION} (IMAGE-ONLY)")
    print("=" * 50)
    print("  Mode: Observational only (no lock/close/dialog/response)")
    print(f"  Layer V only: NudeNet {COARSE_GRID}x{COARSE_GRID} → {FINE_GRID}x{FINE_GRID}")
    print(f"  Trigger threshold: {TRIGGER_THRESHOLD}")
    print(f"  Interest threshold: {DETECTION_ANY}")
    print(f"  Scan interval: {SCAN_ACTIVE}s")
    print("=" * 50)
    print("")
    while True:
        try:
            next_interval = image_only_scan_cycle()
        except KeyboardInterrupt:
            print("Stopped.")
            break
        except Exception as e:
            print(f"IMAGE-ONLY cycle error: {e}")
            next_interval = SCAN_ACTIVE
        time.sleep(next_interval)

# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = first_run_setup()

    log.info("")
    log.info(f"{'='*50}")
    log.info(f"  You Are Loved — Guardian v{VERSION}")
    log.info(f"{'='*50}")
    log.info(f"  Layer P:  Process check")
    log.info(f"  Layer T2: Browser tabs (Chrome + Safari)")
    log.info(f"  Layer T3: Confirmed memory recall")
    log.info(f"  Layer T1: OCR surface scan (3x3 grid)")
    log.info(f"  Layer V:  NudeNet {COARSE_GRID}x{COARSE_GRID} → "
             f"{FINE_GRID}x{FINE_GRID}")
    log.info(f"  Layer C:  Claude Haiku (ambiguous only)")
    log.info(f"  Layer B:  Behavioral (late-night alert)")
    log.info(f"{'─'*50}")
    log.info(f"  Patterns: {len(EXPLICIT_PATTERNS)} explicit, "
             f"{len(AMBIGUOUS_PATTERNS)} ambiguous")
    log.info(f"  Visual threshold: {TRIGGER_THRESHOLD}")
    log.info(f"  Claude API: {'✓' if get_api_key() else '✗'}")
    log.info(f"  Tesseract: {'✓' if HAS_TESSERACT else '✗'}")
    log.info(f"  Scan intervals: {SCAN_ACTIVE}s / {SCAN_IDLE}s / "
             f"{SCAN_DEEP_IDLE}s")
    partners = get_partners()
    log.info(f"  Partners: {len(partners)}")
    for p in partners:
        tg = p.get('telegram', '') or p.get('telegram_chat_id', '')
        log.info(f"    {p.get('email', '?')} | TG: {tg or 'not set'}")
    log.info(f"  SendGrid: {'✓' if get_sendgrid_key() else '✗'}")
    log.info(f"  Telegram: {'✓' if get_telegram_token() else '✗'}")
    log.info(f"  Auto-update poll: every {UPDATE_INTERVAL_SECONDS}s (async)")
    if IMAGE_ONLY_MODE:
        log.info("  Detection mode: IMAGE_ONLY_MODE (visual only; enforcement unchanged)")
    log.info(f"  Audit: {AUDIT_DIR}")
    log.info(f"  Desktop log: {TEXT_LOG}")
    log.info(f"{'='*50}")

    if not get_api_key():
        log.warning("⚠ No API key — Layer C will be skipped")
    if not HAS_TESSERACT:
        log.warning("⚠ No pytesseract — Layer T1 will be skipped")

    purge_old_memory()
    mem = load_memory()
    log.info(f"  Memory: {len(mem.get('urls', {}))} URLs, "
             f"{len(mem.get('domains', {}))} domains")
    log.info(f"  Audits: {len(list(AUDIT_DIR.glob('incident_*')))}")

    check_tamper()

    while True:
        try:
            maybe_start_update_check_async()
            next_interval = scan_cycle()
        except KeyboardInterrupt:
            log.info("Stopped.")
            break
        except Exception as e:
            log.error(f"Cycle error: {e}")
            next_interval = SCAN_ACTIVE
        time.sleep(next_interval)


if __name__ == "__main__":
    args = parse_args()
    if args.image_only:
        run_image_only_main()
    else:
        main()
