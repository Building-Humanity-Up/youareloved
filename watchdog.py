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
import re
import shutil
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CHECK_INTERVAL = 30  # seconds between checks
PYTHON = "/opt/homebrew/opt/python@3.11/bin/python3.11"
VERSION = "5"
UPDATE_BOOTSTRAP_URL = "https://gist.githubusercontent.com/danielliangquestions/455ec3994fc980c1ee9b14f4d02afc27/raw/yal_update.json"
UPDATE_INTERVAL_SECONDS = 300
UPDATE_STATE_FILE = Path("/tmp/yal_last_update_check")
WATCHDOG_PATH = Path(__file__).resolve()
GUARDIAN_PATH = WATCHDOG_PATH.parent / "guardian.py"
CONFIG_FILE = Path.home() / ".yal_config.json"
LOG_FILE = Path.home() / "yal_log.txt"

GUARDIAN_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.youareloved.guardian.plist"
GUARDIAN_PLIST_BAK = Path.home() / "Library" / "LaunchAgents" / "com.youareloved.guardian.plist.bak"
WATCHDOG_PLIST = Path("/Library/LaunchDaemons/com.youareloved.watchdog.plist")
UPDATE_LOCK = threading.Lock()
UPDATE_IN_PROGRESS = False

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

def _read_last_update_check_ts() -> int:
    try:
        if UPDATE_STATE_FILE.exists():
            return int(UPDATE_STATE_FILE.read_text().strip() or "0")
    except Exception as e:
        log.debug(f"UPDATE: State read failed: {e}")
    return 0

def _write_last_update_check_ts(ts: int) -> bool:
    try:
        UPDATE_STATE_FILE.write_text(str(int(ts)))
        return True
    except Exception as e:
        log.error(f"UPDATE: State write failed — {e}")
        return False

def maybe_start_update_check_async():
    global UPDATE_IN_PROGRESS
    now = int(time.time())
    with UPDATE_LOCK:
        if UPDATE_IN_PROGRESS:
            return
        last_ts = _read_last_update_check_ts()
        if last_ts and (now - last_ts) < UPDATE_INTERVAL_SECONDS:
            return
        if not _write_last_update_check_ts(now):
            return
        UPDATE_IN_PROGRESS = True
        try:
            t = threading.Thread(target=check_for_updates, daemon=True)
            t.start()
            log.info(f"UPDATE: Scheduled async check (interval={UPDATE_INTERVAL_SECONDS}s)")
        except Exception as e:
            UPDATE_IN_PROGRESS = False
            log.error(f"UPDATE: Failed to start async check — {e}")

def _parse_guardian_local_version() -> int:
    try:
        src = GUARDIAN_PATH.read_text()
    except Exception as e:
        raise RuntimeError(f"guardian read failed: {e}")
    m = re.search(r'VERSION\s*=\s*"(\d+)"', src)
    if not m:
        raise RuntimeError("guardian VERSION not found")
    return int(m.group(1))

def _cleanup_temp_paths(paths: set[Path]):
    for p in list(paths):
        try:
            if p.exists():
                p.unlink()
        except Exception as e:
            log.warning(f"UPDATE: Temp cleanup failed for {p.name}: {e}")

def check_for_updates():
    global UPDATE_IN_PROGRESS
    temp_paths: set[Path] = set()
    try:
        with urllib.request.urlopen(UPDATE_BOOTSTRAP_URL, timeout=10) as r:
            bootstrap = json.loads(r.read())

        if not isinstance(bootstrap, dict):
            log.error("UPDATE: Bootstrap payload is not an object")
            return

        try:
            remote_version = bootstrap["version"]
            guardian_url = bootstrap["guardian_url"]
            watchdog_url = bootstrap["watchdog_url"]
        except KeyError as e:
            log.error(f"UPDATE: Bootstrap missing key {e}")
            return

        try:
            remote_int = int(str(remote_version))
            watchdog_local_int = int(VERSION)
            guardian_local_int = _parse_guardian_local_version()
        except Exception as e:
            log.error(f"UPDATE: Version parse failed — {e}")
            return

        guardian_needs_update = remote_int > guardian_local_int
        watchdog_needs_update = remote_int > watchdog_local_int
        if not guardian_needs_update and not watchdog_needs_update:
            log.info(
                f"UPDATE: No upgrade needed — remote v{remote_version}, "
                f"guardian v{guardian_local_int}, watchdog v{watchdog_local_int}"
            )
            return

        log.info(
            f"UPDATE: Available v{remote_version} "
            f"(guardian v{guardian_local_int}, watchdog v{watchdog_local_int})"
        )

        downloads = []
        if guardian_needs_update:
            downloads.append(("guardian", guardian_url,
                              WATCHDOG_PATH.parent / "guardian_new.py", GUARDIAN_PATH))
        if watchdog_needs_update:
            downloads.append(("watchdog", watchdog_url,
                              WATCHDOG_PATH.parent / "watchdog_new.py", WATCHDOG_PATH))

        # Remove stale temp files before download
        for _, _, temp_path, _ in downloads:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    log.error(f"UPDATE: Failed to remove stale temp {temp_path.name} — {e}")
                    return
            temp_paths.add(temp_path)

        # Download all needed artifacts before any replacement
        for name, url, temp_path, _ in downloads:
            log.info(f"UPDATE: Downloading {name} from bootstrap URL")
            with urllib.request.urlopen(url, timeout=30) as r:
                code = r.read()
            with open(temp_path, "wb") as f:
                f.write(code)

        # Validate all downloads before any replacement (all-or-nothing)
        for name, _, temp_path, _ in downloads:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(temp_path)],
                capture_output=True)
            if result.returncode != 0:
                log.error(f"UPDATE: Validation failed for {name} — aborting update")
                _cleanup_temp_paths(temp_paths)
                return

        # Backup existing files
        for name, _, _, original_path in downloads:
            shutil.copy2(str(original_path), str(original_path) + ".backup")
            log.info(f"UPDATE: Backed up {name} to {original_path}.backup")

        guardian_updated = False
        watchdog_updated = False

        # Replace guardian first, watchdog second
        for name in ("guardian", "watchdog"):
            for item in downloads:
                iname, _, temp_path, original_path = item
                if iname != name:
                    continue
                shutil.move(str(temp_path), str(original_path))
                temp_paths.discard(temp_path)
                if iname == "guardian":
                    guardian_updated = True
                else:
                    watchdog_updated = True
                log.info(f"UPDATE: Replaced {iname}.py")

        if guardian_updated:
            restart_guardian()

        if watchdog_updated:
            log.info("UPDATE: Restarting watchdog via execv")
            os.execv(sys.executable, [sys.executable] + sys.argv)

    except Exception as e:
        log.error(f"UPDATE: Check failed — {e} — continuing v{VERSION}")
    finally:
        _cleanup_temp_paths(temp_paths)
        with UPDATE_LOCK:
            UPDATE_IN_PROGRESS = False

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 40)
    log.info("Watchdog started")
    log.info(f"  Guardian: {GUARDIAN_PATH}")
    log.info(f"  Watchdog: {WATCHDOG_PATH}")
    log.info(f"  Plist: {GUARDIAN_PLIST}")
    log.info(f"  Check interval: {CHECK_INTERVAL}s")
    log.info(f"  Update poll: every {UPDATE_INTERVAL_SECONDS}s (authority)")
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
            maybe_start_update_check_async()

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
