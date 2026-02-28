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
from datetime import datetime, timedelta
from pathlib import Path

EARLY_IMAGE_ONLY = "--image-only" in sys.argv[1:]

# ---------------------------------------------------------------------------
# Version & Auto-Update
# ---------------------------------------------------------------------------

VERSION = "11"

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
TRIGGER_THRESHOLD = 0.3
COARSE_GRID = 5
FINE_GRID = 3
DETECTION_ANY = 0.1

SCAN_ACTIVE = 5
SCAN_IDLE = 30
SCAN_DEEP_IDLE = SCAN_ACTIVE
SCAN_AWAY_CHECK = 60
IDLE_THRESHOLD_1 = 60
IDLE_THRESHOLD_2 = 600
IDLE_THRESHOLD_3 = 1800
IMAGE_ONLY_MODE = EARLY_IMAGE_ONLY
LOG_DIR = Path.home() / "Library" / "Logs" / "youareloved"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "yal_incidents.log"
RUNTIME_LOG = LOG_DIR / "guardian.log"
RUNTIME_ERR = LOG_DIR / "guardian.error.log"

MEMORY_FILE = Path.home() / ".yal_memory.json"
CONFIG_FILE = Path.home() / ".yal_config.json"

AUDIT_DIR = Path.home() / "youareloved" / "audit"
GUARDIAN_PATH = Path.home() / "youareloved" / "guardian.py"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / "com.youareloved.guardian.plist"

TEXT_LOG = Path.home() / "Desktop" / "yal_text.log"

TMP_DIR = Path.home() / "Library" / "Caches" / "youareloved" / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

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
    r'\bbabepedia\b', r'\bfreeones\b', r'\biafd\b', r'\bgonewild\b',
    r'\bhentaihaven\b', r'\bnhentai\b', r'\brule34\b', r'\bcockwarmer\b',
    r'\bgelbooru\b', r'\bdanbooru\b',
    r'\bbangbros\b', r'\bmofos\b', r'\brealitykings\b', r'\bxempire\b',
    r'\bcumshot\b', r'\bcreampie\b',  r'\basiansgonewild\b'
    r'\banal\b', r'\bblowjob\b', r'\bhandjob\b', r'\bfootjob\b',
    r'\bgangbang\b', r'\bthreesome\b', r'\borgy\b', r'\bf4m\b'
    r'\bpenetration\b', r'\bintercourse\b', r'\bfellatio\b', r'\bgonewild\b'
    r'\bmasturbat', r'\bfingering\b', r'\bNSFW\b'
    r'\bpussy\b', r'\bcock\b', r'\bdick\b', r'\bsoundgasm\b',
    r'\bnipple\b', r'\bareola\b', r'\blabia\b', r'\bscrotum\b',
    r'\bxxx\b', r'\bnsfw\b', r'\bredgifs\b', r'\borgasm\b',
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
    r'\bmature.*woman\b', r'\bnsfw\b',
    r'\bonlyfans\s*leak\b', r'\bnude\s*leak\b', r'\bfappening\b',
    r'\bgonewild\b', r'\breddit.*nsfw\b', r'\breddit.*porn\b',
    r'\bgravure\b', r'\bgravure\s*idol\b', r'\bav\s*idol\b', r'\bidol\b', r'\bscrolller\b',
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
    _fh = logging.FileHandler(str(RUNTIME_LOG))
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
        _fh_fallback = logging.FileHandler(str(LOG_DIR / "yal_text.log"))
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

# Enforcement cooldown: scanning continues, but penalty actions (close/dialog/lock/alerts)
# are suppressed until this unix timestamp.
enforcement_until: float = 0.0

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
    now = time.time()
    if now < enforcement_until:
        remaining = int(enforcement_until - now)
        return f"COOLDOWN ({remaining}s)", SCAN_ACTIVE
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

def _fetch_telegram_chats_from_updates(tg_token: str, timeout_s: int = 10) -> dict:
    """Return mapping of normalized telegram usernames -> chat_id from bot getUpdates.

    Note: Telegram bots can only discover a user's chat_id after the user has interacted
    with the bot (e.g. /start). getUpdates is the simplest polling mechanism.
    """
    if not tg_token:
        return {}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tg_token}/getUpdates")
    resp = urllib.request.urlopen(req, timeout=timeout_s)
    updates = json.loads(resp.read().decode())
    chats = {}
    for update in updates.get("result", []):
        msg = update.get("message", {}) or {}
        chat = msg.get("chat", {}) or {}
        username = (chat.get("username", "") or "").strip()
        chat_id = str(chat.get("id", "") or "").strip()
        if not username or not chat_id:
            continue
        u = username.lower().lstrip("@").strip()
        chats[u] = chat_id
        chats[f"@{u}"] = chat_id
    return chats

def resolve_telegram_chat_ids(
    *,
    tg_token=None,
    wait_for_enter: bool = False,
    save: bool = True,
):
    """Resolve missing partner.telegram_chat_id values and persist into config.

    - Matches by partner["telegram"] username (with/without @), case-insensitive.
    - Safe to run repeatedly; only fills missing chat_ids.
    - Does not require setup wizard; intended as a self-healing operational command.

    Returns a report dict (resolved/unresolved/skipped counts + details).
    """
    cfg = load_config()
    partners = cfg.get("partners", []) or []
    token = (tg_token or cfg.get("telegram_bot_token", "") or "").strip()

    report = {
        "token_present": bool(token),
        "partners_total": len(partners),
        "resolved": [],
        "unresolved": [],
        "skipped": [],
        "changed": False,
    }

    if not token:
        return report

    if wait_for_enter and sys.stdin.isatty():
        print("\nResolving Telegram chat IDs...")
        print("Partners must send /start to the bot first.")
        input("Press Enter to fetch updates now...")

    try:
        chats = _fetch_telegram_chats_from_updates(token)
    except Exception as e:
        report["error"] = str(e)
        return report

    for p in partners:
        tg_raw = (p.get("telegram", "") or "").strip()
        tg_u = tg_raw.lower().lstrip("@").strip()
        existing = (p.get("telegram_chat_id", "") or "").strip()

        if existing:
            report["skipped"].append({"telegram": tg_raw, "chat_id": existing, "reason": "already_set"})
            continue
        if not tg_u:
            report["skipped"].append({"telegram": tg_raw, "chat_id": "", "reason": "no_username"})
            continue

        cid = chats.get(tg_u, "") or chats.get(f"@{tg_u}", "")
        if cid:
            p["telegram_chat_id"] = cid
            report["resolved"].append({"telegram": tg_raw or f"@{tg_u}", "chat_id": cid})
            report["changed"] = True
        else:
            report["unresolved"].append({"telegram": tg_raw or f"@{tg_u}", "reason": "not_in_updates"})

    if report["changed"] and save:
        cfg["partners"] = partners
        if tg_token and str(tg_token).strip() and str(tg_token).strip() != cfg.get("telegram_bot_token", ""):
            cfg["telegram_bot_token"] = str(tg_token).strip()
        save_config(cfg)

    return report

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
            "from": {"email": "alerts@finallyfreeai.com", "name": "You Are Loved"},
            "reply_to": {"email": "alerts@finallyfreeai.com", "name": "You Are Loved"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.sendgrid.com/v3/mail/send",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            msg_id = resp.headers.get("X-Message-Id", "")
            log.info(
                f"  ALERT: Email accepted (HTTP {resp.status}) to {to_email} | msg_id={msg_id}"
            )

    except Exception as e:
        log.error(f"  Email send failed ({to_email}): {e}")


def _send_tamper_alert(api_key: str, to_email: str, detail: str):
    """Send a tamper attempt alert email (routes through _send_email_alert)."""
    _send_email_alert(
        api_key,
        to_email,
        "⚠️ You Are Loved — Tamper Attempt",
        (
            f"Tamper detected.\nDetail: {detail}\n"
            f"Time: {datetime.now().isoformat()}\n\n— You Are Loved"
        ),
    )

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
    """Send a tamper attempt alert email (routes through _send_email_alert)."""
    _send_email_alert(
        api_key,
        to_email,
        "⚠️ You Are Loved — Tamper Attempt",
        (
            f"Tamper detected.\nDetail: {detail}\n"
            f"Time: {datetime.now().isoformat()}\n\n— You Are Loved"
        ),
    )
    
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

# Label list fixed by the NudeNet 640m model (18 classes, order matches ONNX output)
_NUDENET_LABELS = [
    "FEMALE_GENITALIA_COVERED", "FACE_FEMALE", "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED", "FEMALE_GENITALIA_EXPOSED", "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED", "FEET_EXPOSED", "BELLY_COVERED", "FEET_COVERED",
    "ARMPITS_COVERED", "ARMPITS_EXPOSED", "FACE_MALE", "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED", "ANUS_COVERED", "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
]


def _patch_nudenet_threshold():
    """Replace NudeNet's hardcoded 0.25 NMS score floor with DETECTION_ANY (0.10).

    NudeNet's _postprocess function hard-codes two thresholds:
      • Pre-NMS filter  : max_score >= 0.2
      • NMS score gate  : cv2.dnn.NMSBoxes(..., score_threshold=0.25, ...)
    Any detection scoring 0.10–0.24 is silently discarded before reaching our
    code, making TRIGGER_THRESHOLD / DETECTION_ANY values below 0.25 useless.
    This patch replaces both gates with DETECTION_ANY so the guardian actually
    sees everything the model finds above our configured sensitivity.
    """
    import cv2
    import numpy as np
    import nudenet.nudenet as _nn

    _thresh = DETECTION_ANY      # captured once at patch time
    _labels = _NUDENET_LABELS

    def _patched_postprocess(
        output, x_pad, y_pad, x_ratio, y_ratio,
        image_original_width, image_original_height,
        model_width, model_height,
    ):
        outputs = np.transpose(np.squeeze(output[0]))
        rows = outputs.shape[0]
        boxes, scores, class_ids = [], [], []
        for i in range(rows):
            classes_scores = outputs[i][4:]
            max_score = np.amax(classes_scores)
            if max_score >= _thresh:
                class_id = np.argmax(classes_scores)
                x, y, w, h = outputs[i][0:4]
                x = x - w / 2
                y = y - h / 2
                x = x * (image_original_width + x_pad) / model_width
                y = y * (image_original_height + y_pad) / model_height
                w = w * (image_original_width + x_pad) / model_width
                h = h * (image_original_height + y_pad) / model_height
                x = max(0, min(x, image_original_width))
                y = max(0, min(y, image_original_height))
                w = min(w, image_original_width - x)
                h = min(h, image_original_height - y)
                class_ids.append(class_id)
                scores.append(max_score)
                boxes.append([x, y, w, h])
        indices = cv2.dnn.NMSBoxes(boxes, scores, _thresh, 0.45)
        detections = []
        for i in indices:
            box = boxes[i]
            score = scores[i]
            class_id = class_ids[i]
            x, y, w, h = box
            detections.append({
                "class": _labels[class_id],
                "score": float(score),
                "box": [int(x), int(y), int(w), int(h)],
            })
        return detections

    _nn._postprocess = _patched_postprocess
    log.debug(f"  NudeNet _postprocess patched: threshold={_thresh:.2f} (was 0.25)")


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
        _patch_nudenet_threshold()   # lower NMS floor from 0.25 → DETECTION_ANY
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

def _console_uid() -> str:
    """Return the UID of the user currently logged into the GUI session (empty string if unknown)."""
    try:
        r = subprocess.run(
            ["stat", "-f", "%u", "/dev/console"],
            capture_output=True, text=True, timeout=3)
        uid = r.stdout.strip()
        if uid.isdigit() and int(uid) > 0:
            return uid
    except Exception:
        pass
    return ""


def capture_screenshots() -> list:
    """Capture screen using multiple methods until one works.

    Method 0: CGDisplayCreateImage              (IOKit framebuffer — root-safe, GPU content)
    Method 1: launchctl asuser + screencapture  (root-daemon safe — runs inside GUI session)
    Method 2: Quartz CGWindowListCreateImage    (fastest when TCC permission granted to caller)
    Method 3: screencapture CLI direct          (fallback for user-context processes)
    Method 4: mss library                       (last resort, multi-monitor aware)

    Method 0 reads the raw IOKit hardware framebuffer via CGDisplayCreateImage, which bypasses
    the Quartz window compositor. It captures GPU-accelerated content (browsers, video, games)
    even when the caller is a root daemon with no TCC Screen Recording permission.
    """
    from PIL import Image
    import tempfile

    def _try_image(path: str) -> "Image.Image | None":
        try:
            img = Image.open(path)
            img.load()
            # Reject solid-black captures (no permission / blank display)
            extrema = img.convert("L").getextrema()
            if extrema == (0, 0):
                return None
            return img
        except Exception:
            return None

    # Method 0: CGDisplayCreateImage — reads IOKit hardware framebuffer directly.
    # Bypasses the Quartz window compositor so the root daemon captures the same
    # GPU-rendered pixels visible to the user, including browser content.
    # No TCC Screen Recording permission required for this code path.
    try:
        import Quartz
        err, display_ids, count = Quartz.CGGetActiveDisplayList(32, None, None)
        if err == 0 and count > 0:
            images_m0 = []
            for display_id in list(display_ids)[:count]:
                cg_img = Quartz.CGDisplayCreateImage(display_id)
                if cg_img is None:
                    continue
                w = Quartz.CGImageGetWidth(cg_img)
                h = Quartz.CGImageGetHeight(cg_img)
                bpr = Quartz.CGImageGetBytesPerRow(cg_img)
                bpc = Quartz.CGImageGetBitsPerComponent(cg_img)
                if w == 0 or h == 0:
                    continue
                if bpc != 8:
                    # 16-bit HDR display — fall through to next method
                    log.debug(f"  CGDisplayCreateImage: skipping {bpc}bpc display {display_id}")
                    continue
                data = bytes(Quartz.CGDataProviderCopyData(
                    Quartz.CGImageGetDataProvider(cg_img)))
                if len(data) < bpr * h:
                    continue
                img = Image.frombuffer(
                    "RGBA", (w, h), data, "raw", "BGRA", bpr, 1).convert("RGB")
                extrema = img.convert("L").getextrema()
                if extrema != (0, 0):
                    images_m0.append(img)
            if images_m0:
                log.debug(f"  Capture: CGDisplayCreateImage ({len(images_m0)} display(s))")
                return images_m0
            log.debug("  CGDisplayCreateImage: no usable frames (all blank)")
    except Exception as e:
        log.debug(f"  CGDisplayCreateImage failed: {e}")

    # Method 1: launchctl asuser + screencapture
    # Runs screencapture inside the GUI user's launchd session so the daemon
    # sees the same compositor surface as the logged-in user.
    uid = _console_uid()
    if uid:
        tmpfile = tempfile.mktemp(suffix=".png")
        try:
            r = subprocess.run(
                ["launchctl", "asuser", uid,
                 "/usr/sbin/screencapture", "-x", "-C", tmpfile],
                capture_output=True, timeout=15)
            if r.returncode == 0 and os.path.exists(tmpfile) and os.path.getsize(tmpfile) > 10000:
                img = _try_image(tmpfile)
                if img is not None:
                    log.debug("  Capture: launchctl/screencapture")
                    return [img]
        except Exception as e:
            log.debug(f"  launchctl screencapture failed: {e}")
        finally:
            if os.path.exists(tmpfile):
                try:
                    os.unlink(tmpfile)
                except Exception:
                    pass

    # Method 2: Quartz CGWindowListCreateImage
    # Works correctly when the caller has Screen Recording TCC permission.
    try:
        import Quartz
        image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectInfinite,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault)
        if image is not None:
            w = Quartz.CGImageGetWidth(image)
            h = Quartz.CGImageGetHeight(image)
            if w > 0 and h > 0:
                bpr = Quartz.CGImageGetBytesPerRow(image)
                data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(image))
                img = Image.frombuffer("RGBA", (w, h), data, "raw", "BGRA", bpr, 1).convert("RGB")
                extrema = img.convert("L").getextrema()
                if extrema != (0, 0):
                    log.debug("  Capture: Quartz")
                    return [img]
                log.debug("  Quartz returned blank image (TCC permission missing for caller)")
    except Exception as e:
        log.debug(f"  Quartz capture failed: {e}")

    # Method 3: screencapture CLI direct
    try:
        tmpfile = tempfile.mktemp(suffix=".png")
        r = subprocess.run(
            ["/usr/sbin/screencapture", "-x", "-C", tmpfile],
            capture_output=True, timeout=10)
        if r.returncode == 0 and os.path.exists(tmpfile) and os.path.getsize(tmpfile) > 10000:
            img = _try_image(tmpfile)
            if img is not None:
                log.debug("  Capture: screencapture")
                return [img]
        if os.path.exists(tmpfile):
            os.unlink(tmpfile)
    except Exception as e:
        log.debug(f"  screencapture direct failed: {e}")

    # Method 4: mss library (multi-monitor aware)
    try:
        sct = get_mss()
        images = []
        for mon in sct.monitors[1:]:
            raw = sct.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            extrema = img.convert("L").getextrema()
            if extrema != (0, 0):
                images.append(img)
        if images:
            log.debug("  Capture: mss")
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

def make_grid(img, n: int, prefix: str = "g", n_cols: int = None) -> list:
    n_cols = n_cols if n_cols is not None else n
    w, h = img.size
    tw, th = w // n_cols, h // n
    tiles = []
    for row in range(n):
        for col in range(n_cols):
            x1 = col * tw
            y1 = row * th
            x2 = x1 + tw if col < n_cols - 1 else w
            y2 = y1 + th if row < n - 1 else h
            tiles.append((f"{prefix}{row}{col}", img.crop((x1, y1, x2, y2)),
                          (x1, y1, x2, y2)))
    return tiles

def make_overlaps(img, n: int, n_cols: int = None) -> list:
    n_cols = n_cols if n_cols is not None else n
    w, h = img.size
    tw, th = w // n_cols, h // n
    ox, oy = tw // 2, th // 2
    tiles = []
    for row in range(n - 1):
        for col in range(n_cols - 1):
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
    """
    Returns: (results, triggered_bool, detail_str)

    Strategy:
      1) Prefer in-memory detect(tile_img) if NudeNet supports it.
      2) Fallback to a per-user temp PNG (not a shared fixed filename).
      3) Always delete temp file immediately after detect().
    """
    results = []
    triggered = False
    detail = ""

    # 1) Try in-memory path first (fastest, no disk I/O)
    try:
        results = detector.detect(tile_img)
    except Exception:
        results = None

    # 2) Fallback to temp PNG if in-memory detect is unsupported
    if results is None:
        import os
        import tempfile
        from pathlib import Path

        tmp_dir = Path.home() / "Library" / "Caches" / "youareloved" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                prefix=f"yal_tile_{mon_idx}_{tile_name}_",
                suffix=".png",
                dir=str(tmp_dir),
            )
            os.close(fd)
            tile_img.save(tmp_path)
            results = detector.detect(tmp_path)
        except Exception as e:
            log.error(f"    NudeNet error on {tile_name}: {e}")
            return [], False, ""
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass  # never block detection on cleanup

    # Filter to only relevant classes
    relevant = [
        d for d in (results or [])
        if d.get("class", "") in (NUDENET_TRIGGER_LABELS | NUDENET_INTEREST_LABELS)
        and d.get("score", 0) >= 0.10
    ]

    if relevant:
        log.info(
            f"    {tile_name} ({tile_img.size[0]}x{tile_img.size[1]}): "
            f"{len(relevant)} detection(s)"
        )
        for d in relevant:
            score = d.get("score", 0)
            cls = d.get("class", "")
            marker = "🔴" if (cls in NUDENET_TRIGGER_LABELS and score >= TRIGGER_THRESHOLD) else "🟡"
            log.info(f"      {marker} {cls}: {score:.3f}")

    triggered, detail = check_triggered(results or [])
    return results or [], triggered, detail

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
    log.info("LAYER V — NudeNet Adaptive Scan")
    log.info(f"  Trigger: {TRIGGER_THRESHOLD} | Interest: {DETECTION_ANY}")
    detector = get_detector()

    for mon_idx, img in enumerate(images):
        w, h = img.size

        # Adapt grid to aspect ratio so tiles stay roughly square for NudeNet
        aspect = w / h
        sqrt_a = aspect ** 0.5
        n_rows = max(2, round(COARSE_GRID / sqrt_a))
        n_cols = max(COARSE_GRID, round(COARSE_GRID * sqrt_a))

        log.info(
            f"  Monitor {mon_idx}: {w}x{h} → grid {n_cols}×{n_rows} "
            f"(~{w//n_cols}×{h//n_rows}px/tile)"
        )
        log.info(
            f"  Pass 1: {n_cols}x{n_rows} coarse | "
            f"Pass 2: {FINE_GRID}x{FINE_GRID} fine on hot tiles"
        )

        # ─────────────────────────────────────────────────────────────
        # FAST PASS (mandatory): full-frame evaluation before any tiling
        # ─────────────────────────────────────────────────────────────
        full_r, full_t, full_d = scan_tile(detector, "full", img, mon_idx)

        # Always surface the best full-frame score (even when empty)
        # (observability only; does not change detection thresholds)
        b_cls = "NONE"
        b_sc = 0.0
        try:
            if full_r:
                best = max(full_r, key=lambda d: d.get("score", 0.0))
                b_cls = best.get("class", "NONE") or "NONE"
                b_sc = float(best.get("score", 0.0) or 0.0)
        except Exception:
            pass
        log.info(f"  Full-frame top: {b_cls} {b_sc:.3f} | raw={len(full_r)} triggered={full_t}")

        if full_t:
            log.warning(f"  >>> NSFW on full image: {fmt_detections(full_r)}")
            return True, full_d, mon_idx, "full", full_r, img, img

        # ─────────────────────────────────────────────────────────────
        # PASS 1: coarse + overlaps in parallel (unchanged)
        # ─────────────────────────────────────────────────────────────
        log.info(f"  PASS 1 — Coarse {n_cols}×{n_rows} [parallel]")

        coarse = make_grid(img, n_rows, prefix="c", n_cols=n_cols)
        overlaps = make_overlaps(img, n_rows, n_cols=n_cols)
        all_coarse = coarse + overlaps

        import concurrent.futures
        futures_list = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for name, tile, box in all_coarse:
                fut = executor.submit(scan_tile, detector, name, tile, mon_idx)
                futures_list.append((fut, name, tile, box))

        hot = []
        first_trigger = None
        for fut, name, tile, box in futures_list:
            r, t, d = fut.result()
            if t and first_trigger is None:
                log.warning(f"  >>> NSFW on '{name}': {fmt_detections(r)}")
                first_trigger = (True, d, mon_idx, name, r, img, tile)
            elif has_interest(r):
                hot.append((name, tile, box, r))

        if first_trigger:
            return first_trigger

        # ─────────────────────────────────────────────────────────────
        # PASS 2: fine scan only on hot tiles (unchanged)
        # ─────────────────────────────────────────────────────────────
        if hot:
            log.info(f"  PASS 2 — Fine scan on {len(hot)} hot tile(s)")
            for pname, pimg, pbox, pr in hot:
                log.info(
                    f"    Subdividing '{pname}' "
                    f"({pimg.size[0]}x{pimg.size[1]}) into {FINE_GRID}x{FINE_GRID}"
                )
                subs = make_grid(pimg, FINE_GRID, prefix=f"{pname}_f")
                for sname, simg, sbox in subs:
                    r, t, d = scan_tile(detector, sname, simg, mon_idx)
                    if t:
                        log.warning(
                            f"  >>> NSFW on '{sname}' (parent: {pname}): "
                            f"{fmt_detections(r)}"
                        )
                        return True, d, mon_idx, sname, r, img, simg
        else:
            log.info("  PASS 2 — No hot tiles, skipped")

    log.info("  Layer V: CLEAR")
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
    global enforcement_until
    now = time.time()
    in_cooldown = now < enforcement_until

    # Always log something (so repeated incidents are visible)
    if in_cooldown:
        log.warning(f"SUPPRESSED (cooldown active): {layer} | {detail}")
        log_incident(f"SUPPRESSED_{layer}", detail)
    else:
        log.warning(f"{'='*50}")
        log.warning(f"INCIDENT: {layer} | {detail}")
        log.warning(f"{'='*50}")
        log_incident(layer, detail)

    url = get_active_url()
    if url:
        log.info(f"RESPONSE: Active URL: {url}")

    # Always close content, even during cooldown
    close_nsfw_window()

    # During cooldown: stop here (no alerts/dialog/lock/audit)
    if in_cooldown:
        return

    # Save audit if visual data available (only when not in cooldown)
    if full_img and tile_img and mon_idx >= 0:
        if url:
            learn_url_visual(url)
        save_audit(mon_idx, tile_name, results or [], full_img, tile_img,
                   url or "", detail)

    # Fire alerts to all partners (only when not in cooldown)
    fire_alerts(layer, detail, full_img)

    show_dialog()
    lock_screen()

    # Start/extend enforcement cooldown window
    enforcement_until = time.time() + LOCK_COOLDOWN

# ═══════════════════════════════════════════════════════════════════════════
# MAIN SCAN CYCLE
# ═══════════════════════════════════════════════════════════════════════════

def scan_cycle():
    global scan_count
    scan_count += 1

    mode, interval = get_scan_mode()
    ts = datetime.now().strftime("%H:%M:%S")
    idle = seconds_idle()

    log.info("")
    log.info(f"{'─'*50}")
    log.info(f"SCAN #{scan_count} at {ts} | {mode}")
    log.info(f"{'─'*50}")

    # If user is away, skip active work regardless of cooldown state.
    if idle > IDLE_THRESHOLD_3:
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
    parser.add_argument("--resolve-telegram", action="store_true", default=False,
                        help="Resolve partner Telegram chat_ids from bot getUpdates and persist to config")
    parser.add_argument("--telegram-token", default="",
                        help="Override Telegram bot token (also persists into config if resolution succeeds)")
    parser.add_argument("--wait", action="store_true", default=False,
                        help="Wait for Enter before fetching getUpdates (useful while partners are /starting)")
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
# SCREEN RECORDING PERMISSION MONITOR
# ═══════════════════════════════════════════════════════════════════════════

_sr_degraded = False          # track state across checks
_SR_CHECK_INTERVAL = 300      # 5 minutes


def _check_screen_recording_luminance() -> str:
    """Classify screen capture quality using luminance std deviation.

    Returns "yes" (std > 45 = full desktop), "wallpaper" (3-45), or "no".
    """
    try:
        import Quartz
        cg_img = Quartz.CGWindowListCreateImage(
            Quartz.CGRectInfinite,
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID,
            Quartz.kCGWindowImageDefault)
        if not cg_img or Quartz.CGImageGetWidth(cg_img) == 0:
            return "no"
        w = Quartz.CGImageGetWidth(cg_img)
        h = Quartz.CGImageGetHeight(cg_img)
        bpr = Quartz.CGImageGetBytesPerRow(cg_img)
        data = bytes(Quartz.CGDataProviderCopyData(
            Quartz.CGImageGetDataProvider(cg_img)))
        if all(b == 0 for b in data[:2000]):
            return "no"
        from PIL import Image
        pil = Image.frombuffer(
            "RGBA", (w, h), data, "raw", "BGRA", bpr, 1).convert("L")
        pixels = list(pil.getdata())[::4]
        n = len(pixels)
        mean = sum(pixels) / n
        std = (sum((p - mean) ** 2 for p in pixels) / n) ** 0.5
        if std > 45:
            return "yes"
        elif std > 3:
            return "wallpaper"
        return "no"
    except Exception as e:
        log.debug(f"  SR luminance check error: {e}")
        return "no"


def _get_user_firstname() -> str:
    cfg = load_config()
    partners = cfg.get("partners", [])
    name = cfg.get("user_firstname", "") or cfg.get("firstname", "")
    if not name:
        name = socket.gethostname().split(".")[0].capitalize()
    return name.capitalize()


def _fire_permission_alert(message: str):
    """Send a permission-related alert to all partners."""
    partners = get_partners()
    sg_key = get_sendgrid_key()
    tg_token = get_telegram_token()
    if not partners:
        return

    def _worker():
        for partner in partners:
            tg_chat = partner.get("telegram_chat_id", "")
            email = partner.get("email", "")
            if tg_token and tg_chat:
                try:
                    _send_telegram(tg_token, tg_chat, message)
                except Exception as e:
                    log.error(f"  Permission alert TG failed: {e}")
            if sg_key and email:
                try:
                    _send_email_alert(
                        sg_key, email,
                        "[You Are Loved] Permission change", message)
                except Exception as e:
                    log.error(f"  Permission alert email failed: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def screen_recording_monitor():
    """Background thread: check Screen Recording every 5 minutes.

    On degradation: alert partners, log PERMISSION_DEGRADED.
    On restoration: alert partners, log PERMISSION_RESTORED.
    """
    global _sr_degraded
    firstname = _get_user_firstname()

    while True:
        try:
            result = _check_screen_recording_luminance()
            if result != "yes" and not _sr_degraded:
                _sr_degraded = True
                log.warning("PERMISSION_DEGRADED — Screen Recording not working")
                _fire_permission_alert(
                    f"\u26a0\ufe0f Screen Recording permission was removed "
                    f"from {firstname}\u2019s Mac.\n"
                    f"Visual detection is disabled.")
            elif result == "yes" and _sr_degraded:
                _sr_degraded = False
                log.info("PERMISSION_RESTORED — Screen Recording working again")
                _fire_permission_alert(
                    f"\u2705 Screen Recording restored on "
                    f"{firstname}\u2019s Mac.")
        except Exception as e:
            log.error(f"  SR monitor error: {e}")

        time.sleep(_SR_CHECK_INTERVAL)


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
    log.info("  Auto-update: managed by watchdog")
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

    # Start Screen Recording permission monitor
    sr_result = _check_screen_recording_luminance()
    if sr_result == "yes":
        log.info(f"  Screen Recording: verified (luminance OK)")
    else:
        log.warning(f"  Screen Recording: DEGRADED ({sr_result})")
        global _sr_degraded
        _sr_degraded = True
        firstname = _get_user_firstname()
        _fire_permission_alert(
            f"\u26a0\ufe0f Screen Recording permission was removed "
            f"from {firstname}\u2019s Mac.\n"
            f"Visual detection is disabled.")
    threading.Thread(target=screen_recording_monitor,
                     daemon=True, name="sr-monitor").start()

    while True:
        try:
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
    if getattr(args, "resolve_telegram", False):
        report = resolve_telegram_chat_ids(
            tg_token=(args.telegram_token or None),
            wait_for_enter=bool(getattr(args, "wait", False)),
            save=True,
        )
        print("\n=== Telegram Chat ID Resolution Report ===")
        if not report.get("token_present"):
            print("Telegram bot token: not set")
            sys.exit(2)
        if report.get("error"):
            print(f"Error: {report['error']}")
            sys.exit(2)
        print(f"Partners: {report.get('partners_total', 0)}")
        print(f"Resolved: {len(report.get('resolved', []))}")
        for r in report.get("resolved", []):
            print(f"  ✓ {r.get('telegram')} → {r.get('chat_id')}")
        print(f"Unresolved: {len(report.get('unresolved', []))}")
        for u in report.get("unresolved", []):
            print(f"  ⚠ {u.get('telegram')} (not found in updates)")
        print(f"Skipped: {len(report.get('skipped', []))}")
        for s in report.get("skipped", []):
            reason = s.get("reason", "")
            tg = s.get("telegram") or "(none)"
            if reason == "already_set":
                print(f"  ↷ {tg} (already has chat_id)")
            elif reason == "no_username":
                print(f"  ↷ {tg} (no telegram username on partner)")
        if report.get("changed"):
            print("Config updated: yes")
        else:
            print("Config updated: no")
        sys.exit(0)
    if args.image_only:
        run_image_only_main()
    else:
        main()
