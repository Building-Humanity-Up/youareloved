#!/bin/bash
# ============================================================================
# You Are Loved — Uninstall
#
# Requires the 6-digit code held by your accountability partner.
# Removes system-level LaunchDaemons (requires sudo).
# ============================================================================

set -e

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

CONFIG="$HOME/.yal_config.json"
GUARDIAN_PLIST="/Library/LaunchDaemons/com.youareloved.guardian.plist"
WATCHDOG_PLIST="/Library/LaunchDaemons/com.youareloved.watchdog.plist"
PYTHON=""

# Find Python
for p in \
    /opt/homebrew/opt/python@3.11/bin/python3.11 \
    /usr/local/opt/python@3.11/bin/python3.11 \
    "$(which python3.11 2>/dev/null)" \
    "$(which python3 2>/dev/null)"; do
    if [[ -n "$p" ]] && [[ -x "$p" ]]; then
        PYTHON="$p"
        break
    fi
done

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
echo -e "${BOLD}       You Are Loved — Uninstall${RESET}"
echo -e "${BOLD}═══════════════════════════════════════════════${RESET}"
echo ""

# Check config
if [[ ! -f "$CONFIG" ]]; then
    echo -e "${RED}No configuration found. Nothing to uninstall.${RESET}"
    exit 1
fi

# Get stored hash
STORED_HASH=$("$PYTHON" -c "
import json
cfg = json.load(open('$CONFIG'))
print(cfg.get('code_hash', ''))
" 2>/dev/null)

if [[ -z "$STORED_HASH" ]]; then
    echo -e "${RED}Configuration is corrupted. Cannot verify code.${RESET}"
    exit 1
fi

# Prompt for code
echo -e "${YELLOW}Enter the 6-digit uninstall code:${RESET}"
read -rp "> " USER_CODE

# Verify
MATCH=$("$PYTHON" -c "
import hashlib
code = '$USER_CODE'
stored = '$STORED_HASH'
computed = hashlib.sha256(code.encode()).hexdigest()
print('yes' if computed == stored else 'no')
" 2>/dev/null)

if [[ "$MATCH" != "yes" ]]; then
    echo ""
    echo -e "${RED}════════════════════════════════════════════${RESET}"
    echo -e "${RED}  INCORRECT CODE${RESET}"
    echo -e "${RED}════════════════════════════════════════════${RESET}"
    echo ""

    # Log the failed attempt
    echo "[$(date -Iseconds)] UNINSTALL_ATTEMPT_FAILED" >> "$HOME/yal_log.txt"

    # Alert partner
    PARTNER=$("$PYTHON" -c "
import json
cfg = json.load(open('$CONFIG'))
print(cfg.get('partner_email', ''))
" 2>/dev/null)

    if [[ -n "$PARTNER" ]]; then
        echo -e "${RED}Your accountability partner ($PARTNER) has been notified.${RESET}"
        # Send alert via Python
        "$PYTHON" -c "
import json, urllib.request, os
cfg = json.load(open('$CONFIG'))
pe = cfg.get('partner_email', '')
sk = os.environ.get('SENDGRID_API_KEY', '')
if pe and sk:
    data = json.dumps({
        'personalizations': [{'to': [{'email': pe}]}],
        'from': {'email': 'guardian@youareloved.app', 'name': 'You Are Loved'},
        'subject': '⚠️ Failed Uninstall Attempt',
        'content': [{'type': 'text/plain', 'value':
            'Someone tried to uninstall You Are Loved with an incorrect code.\\n\\n'
            'Time: $(date -Iseconds)\\n\\nYou may want to check in.\\n\\n— You Are Loved'}]
    }).encode()
    req = urllib.request.Request('https://api.sendgrid.com/v3/mail/send',
        data=data, headers={'Authorization': f'Bearer {sk}',
        'Content-Type': 'application/json'}, method='POST')
    try: urllib.request.urlopen(req, timeout=10)
    except: pass
" 2>/dev/null || true
    fi

    exit 1
fi

# Code correct
echo ""
echo -e "${GREEN}Code verified.${RESET}"
echo ""
echo -e "${YELLOW}This will completely remove You Are Loved:${RESET}"
echo "  - Stop guardian and watchdog daemons (requires sudo)"
echo "  - Remove system-level LaunchDaemons"
echo "  - Restore DNS settings"
echo "  - Remove hosts file entries"
echo "  - Delete ~/youareloved/"
echo ""
read -rp "Type 'REMOVE' to confirm: " CONFIRM

if [[ "$CONFIRM" != "REMOVE" ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}Uninstalling...${RESET}"

# Stop daemons
echo -e "${YELLOW}Stopping daemons (requires sudo)...${RESET}"
sudo launchctl bootout system/com.youareloved.guardian 2>/dev/null || true
sudo launchctl bootout system/com.youareloved.watchdog 2>/dev/null || true
pkill -f guardian.py 2>/dev/null || true
pkill -f watchdog.py 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓ Daemons stopped${RESET}"

# Remove plists
sudo rm -f "$GUARDIAN_PLIST" "${GUARDIAN_PLIST}.bak"
sudo rm -f "$WATCHDOG_PLIST"
# Also remove old user-level agent if present
rm -f "$HOME/Library/LaunchAgents/com.youareloved.guardian.plist"
echo -e "${GREEN}✓ LaunchDaemons removed${RESET}"

# Remove files
sudo rm -rf "$HOME/youareloved"
sudo rm -rf "$HOME/youareloved/__pycache__"
rm -f "$HOME/.yal_memory.json"
rm -f "$HOME/.yal_config.json"
rm -f /tmp/yal.log /tmp/yal.error.log /tmp/yal_text.log
rm -f /tmp/yal_watchdog.log /tmp/yal_watchdog.error.log
rm -f /tmp/yal_tile_*.png
rm -f "$HOME/Desktop/yal_text.log"
echo -e "${GREEN}✓ Files removed${RESET}"

# Restore DNS
while IFS= read -r iface; do
    [[ -n "$iface" ]] && sudo networksetup -setdnsservers "$iface" "Empty" 2>/dev/null || true
done < <(networksetup -listallnetworkservices | tail -n +2)
echo -e "${GREEN}✓ DNS restored${RESET}"

# Remove hosts entries
if grep -q "You Are Loved" /etc/hosts 2>/dev/null; then
    sudo sed -i '' '/# You Are Loved/,/# End You Are Loved/d' /etc/hosts
    sudo dscacheutil -flushcache 2>/dev/null || true
    echo -e "${GREEN}✓ Hosts file cleaned${RESET}"
fi

# Keep incident log
if [[ -f "$HOME/yal_log.txt" ]]; then
    echo -e "${YELLOW}  Incident log preserved: ~/yal_log.txt${RESET}"
fi

echo ""
echo -e "${GREEN}${BOLD}You Are Loved has been uninstalled.${RESET}"
echo ""
echo -e "${BOLD}Remember: you are loved, and it's okay to ask for help.${RESET}"
echo ""
