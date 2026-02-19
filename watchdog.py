#!/usr/bin/env python3
"""
You Are Loved — Watchdog

Lightweight self-healing daemon that:
  - Checks every 30 seconds if guardian.py is running
  - Restarts it if killed
  - Detects plist deletion/modification and restores from backup
  - Alerts accountability partner on tamper attempts

Runs as its own LaunchDaemon: com.youareloved.watchdog
"""

import os
import sys
import time
import subprocess
import json
import hashlib
import logging
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CHECK_INTERVAL = 30  # seconds between checks
PYTHON = "/opt/homebrew/opt/python@3.11/bin/python3.11"
GUARDIAN_PATH = Path.home() / "youareloved" / "guardian.py"
CONFIG_FILE = Path.home() / ".yal_config.json"
LOG_FILE = Path.home() / "yal_log.txt"

GUARDIAN_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.youareloved.guardian.plist"
GUARDIAN_PLIST_BAK = Path.home() / "Library" / "LaunchAgents" / "com.youareloved.guardian.plist.bak"
WATCHDOG_PLIST = Path("/Library/LaunchDaemons/com.youareloved.watchdog.plist")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("watchdog")
log.setLevel(logging.DEBUG)
log.propagate = False
log.handlers.clear()

_fmt = logging.Formatter("%(asctime)s [WATCHDOG] %(message)s")

_fh = logging.FileHandler("/tmp/yal_watchdog.log")
_fh.setLevel(logging.DEBUG)
_fh.setFormatter(_fmt)
log.addHandler(_fh)

_fh2 = logging.FileHandler("/tmp/yal.log")
_fh2.setLevel(logging.INFO)
_fh2.setFormatter(_fmt)
log.addHandler(_fh2)

_sh = logging.StreamHandler(sys.stdout)
_sh.setLevel(logging.INFO)
_sh.setFormatter(_fmt)
log.addHandler(_sh)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}

def log_incident(reason: str, detail: str):
    ts = datetime.now().isoformat()
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{ts}] WATCHDOG_{reason} | {detail}\n")
    except Exception:
        pass

def is_guardian_running() -> bool:
    """Check if guardian.py process is alive."""
    try:
        r = subprocess.run(["pgrep", "-f", "guardian.py"],
                           capture_output=True, text=True, timeout=5)
        pids = [p.strip() for p in r.stdout.strip().split("\n") if p.strip()]
        # Filter out watchdog's own PID and pgrep itself
        my_pid = str(os.getpid())
        real_pids = [p for p in pids if p != my_pid]
        return len(real_pids) > 0
    except Exception:
        return False

def get_plist_hash(path: Path) -> str:
    """SHA-256 hash of plist file for tamper detection."""
    if path.exists():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    return ""

def alert_partner(detail: str):
    """Send tamper alert to accountability partner."""
    cfg = load_config()
    partner_email = cfg.get("partner_email", "")
    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")

    if partner_email and sendgrid_key:
        try:
            data = json.dumps({
                "personalizations": [{"to": [{"email": partner_email}]}],
                "from": {"email": "guardian@youareloved.app",
                         "name": "You Are Loved"},
                "subject": "⚠️ Tamper Attempt Detected",
                "content": [{"type": "text/plain", "value": (
                    f"The You Are Loved watchdog detected a tamper attempt.\n\n"
                    f"Detail: {detail}\n"
                    f"Time: {datetime.now().isoformat()}\n\n"
                    f"The guardian has been automatically restored.\n\n"
                    f"— You Are Loved"
                )}]
            }).encode()
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send", data=data,
                headers={"Authorization": f"Bearer {sendgrid_key}",
                         "Content-Type": "application/json"},
                method="POST")
            urllib.request.urlopen(req, timeout=10)
            log.info(f"Alert sent to {partner_email}")
        except Exception as e:
            log.error(f"Email alert failed: {e}")
    else:
        log.warning("No email config — alert not sent")

def restart_guardian():
    """Restart guardian.py via launchctl (user agent)."""
    log.info("Restarting guardian...")

    # Get the current user's UID for launchctl commands
    uid = os.getuid()

    try:
        # Try launchctl kickstart (modern macOS)
        subprocess.run(
            ["launchctl", "kickstart", "-k",
             f"gui/{uid}/com.youareloved.guardian"],
            capture_output=True, timeout=10)
        time.sleep(3)
        if is_guardian_running():
            log.info("Guardian restarted via launchctl")
            return True
    except Exception:
        pass

    try:
        # Try load/unload
        subprocess.run(
            ["launchctl", "unload", str(GUARDIAN_PLIST)],
            capture_output=True, timeout=5)
        subprocess.run(
            ["launchctl", "load", "-w", str(GUARDIAN_PLIST)],
            capture_output=True, timeout=5)
        time.sleep(3)
        if is_guardian_running():
            log.info("Guardian restarted via load/unload")
            return True
    except Exception:
        pass

    # Fallback: direct launch
    try:
        subprocess.Popen(
            [PYTHON, "-u", str(GUARDIAN_PATH)],
            stdout=open("/tmp/yal.log", "a"),
            stderr=open("/tmp/yal.error.log", "a"),
        )
        time.sleep(3)
        if is_guardian_running():
            log.info("Guardian restarted directly")
            return True
    except Exception as e:
        log.error(f"Direct restart failed: {e}")

    return False

def restore_plist():
    """Restore guardian plist from backup."""
    if GUARDIAN_PLIST_BAK.exists():
        try:
            import shutil
            shutil.copy2(str(GUARDIAN_PLIST_BAK), str(GUARDIAN_PLIST))
            subprocess.run(
                ["launchctl", "load", "-w", str(GUARDIAN_PLIST)],
                capture_output=True, timeout=10)
            log.info("Guardian plist restored from backup")
            return True
        except Exception as e:
            log.error(f"Plist restore failed: {e}")
    else:
        log.error("No backup plist found — cannot restore")
    return False

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 40)
    log.info("Watchdog started")
    log.info(f"  Guardian: {GUARDIAN_PATH}")
    log.info(f"  Plist: {GUARDIAN_PLIST}")
    log.info(f"  Check interval: {CHECK_INTERVAL}s")
    log.info("=" * 40)

    # Record initial plist hash
    plist_hash = get_plist_hash(GUARDIAN_PLIST)
    if plist_hash:
        log.info(f"  Plist hash: {plist_hash[:16]}...")
    else:
        log.warning("  Guardian plist not found at startup")

    check_count = 0

    while True:
        try:
            check_count += 1

            # --- Check 1: Is guardian running? ---
            if not is_guardian_running():
                log.warning(f"Guardian NOT running (check #{check_count})")
                log_incident("PROCESS_DOWN", "guardian.py not running")

                # Alert on unexpected death (not first check)
                if check_count > 1:
                    alert_partner("guardian.py was killed or crashed")

                restart_guardian()

            # --- Check 2: Is guardian plist intact? ---
            current_hash = get_plist_hash(GUARDIAN_PLIST)

            if not GUARDIAN_PLIST.exists():
                log.warning("Guardian plist DELETED")
                log_incident("PLIST_DELETED",
                             str(GUARDIAN_PLIST))
                alert_partner(
                    f"Guardian plist was deleted: {GUARDIAN_PLIST}")
                restore_plist()

            elif plist_hash and current_hash != plist_hash:
                log.warning("Guardian plist MODIFIED")
                log_incident("PLIST_MODIFIED",
                             f"hash changed: {plist_hash[:16]} → "
                             f"{current_hash[:16]}")
                alert_partner("Guardian plist was modified")
                restore_plist()
                plist_hash = get_plist_hash(GUARDIAN_PLIST)

            # --- Check 3: Is guardian.py file still there? ---
            if not GUARDIAN_PATH.exists():
                log.warning("guardian.py file DELETED")
                log_incident("FILE_DELETED", str(GUARDIAN_PATH))
                alert_partner(
                    f"guardian.py was deleted from {GUARDIAN_PATH}")

        except Exception as e:
            log.error(f"Watchdog error: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
