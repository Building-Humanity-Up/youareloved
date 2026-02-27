import os, sqlite3, secrets, string, json, requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file, abort
from apscheduler.schedulers.background import BackgroundScheduler
import io

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
NEXTDNS_CONFIG_ID  = os.environ["NEXTDNS_CONFIG_ID"]        # e.g. abc123
NEXTDNS_API_KEY    = os.environ["NEXTDNS_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DB_PATH            = os.environ.get("DB_PATH", "devices.db")
BASE_URL           = os.environ["BASE_URL"]                  # https://YOUR_RAILWAY_URL
SILENCE_THRESHOLD  = 30 * 60   # 30 minutes in seconds
ACTIVE_WINDOW      = 2 * 60 * 60  # only alert if active in last 2 hours

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                token           TEXT PRIMARY KEY,
                user_firstname  TEXT,
                user_email      TEXT,
                partner_email   TEXT,
                partner_telegram TEXT,
                last_seen       INTEGER,
                removal_alerted INTEGER DEFAULT 0,
                created_at      INTEGER
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS download_links (
                link_token  TEXT PRIMARY KEY,
                device_token TEXT,
                expires_at  INTEGER,
                used        INTEGER DEFAULT 0
            )
        """)

init_db()

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)

# ── Token helpers ─────────────────────────────────────────────────────────────
def make_random(n=4):
    return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def make_link_token():
    return secrets.token_urlsafe(16)

# ── .mobileconfig generation ──────────────────────────────────────────────────
def generate_mobileconfig(device_token: str, firstname: str) -> str:
    doh_url = f"https://dns.nextdns.io/{NEXTDNS_CONFIG_ID}/{device_token}"
    profile_uuid   = str(__import__('uuid').uuid4()).upper()
    dns_uuid       = str(__import__('uuid').uuid4()).upper()
    filter_uuid    = str(__import__('uuid').uuid4()).upper()
    restrict_uuid  = str(__import__('uuid').uuid4()).upper()
    st_uuid        = str(__import__('uuid').uuid4()).upper()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>

        <!-- 1. DNS over HTTPS via NextDNS -->
        <dict>
            <key>PayloadType</key><string>com.apple.dnsSettings.managed</string>
            <key>PayloadIdentifier</key><string>app.youareloved.dns.{device_token}</string>
            <key>PayloadUUID</key><string>{dns_uuid}</string>
            <key>PayloadVersion</key><integer>1</integer>
            <key>PayloadDisplayName</key><string>You Are Loved — DNS Protection</string>
            <key>DNSProtocol</key><string>HTTPS</string>
            <key>ServerURL</key><string>{doh_url}</string>
            <key>DNSOverHTTPSMatchDomains</key>
            <array><string></string></array>
        </dict>

        <!-- 2. WebKit content filter (Apple native) -->
        <dict>
            <key>PayloadType</key><string>com.apple.webContentFilter</string>
            <key>PayloadIdentifier</key><string>app.youareloved.filter.{device_token}</string>
            <key>PayloadUUID</key><string>{filter_uuid}</string>
            <key>PayloadVersion</key><integer>1</integer>
            <key>PayloadDisplayName</key><string>You Are Loved — Content Filter</string>
            <key>FilterType</key><string>BuiltIn</string>
            <key>AutoFilterEnabled</key><true/>
            <key>FilterBrowsers</key><true/>
            <key>FilterSockets</key><false/>
        </dict>

        <!-- 3. Restrictions — no VPN, no private browsing -->
        <dict>
            <key>PayloadType</key><string>com.apple.applicationaccess</string>
            <key>PayloadIdentifier</key><string>app.youareloved.restrictions.{device_token}</string>
            <key>PayloadUUID</key><string>{restrict_uuid}</string>
            <key>PayloadVersion</key><integer>1</integer>
            <key>PayloadDisplayName</key><string>You Are Loved — Restrictions</string>
            <key>allowVPNCreation</key><false/>
            <key>allowSafariPrivateBrowsing</key><false/>
            <key>allowAccountModification</key><false/>
        </dict>

        <!-- 4. Screen Time lock -->
        <dict>
            <key>PayloadType</key><string>com.apple.screentime</string>
            <key>PayloadIdentifier</key><string>app.youareloved.screentime.{device_token}</string>
            <key>PayloadUUID</key><string>{st_uuid}</string>
            <key>PayloadVersion</key><integer>1</integer>
            <key>PayloadDisplayName</key><string>You Are Loved — Screen Time</string>
            <key>restrictedContent</key><true/>
            <key>contentFilterEnabled</key><true/>
        </dict>

    </array>
    <key>PayloadDescription</key>
    <string>You Are Loved accountability protection for {firstname}</string>
    <key>PayloadDisplayName</key><string>You Are Loved Protection</string>
    <key>PayloadIdentifier</key><string>app.youareloved.profile.{device_token}</string>
    <key>PayloadOrganization</key><string>Building Humanity Up</string>
    <key>PayloadRemovalDisallowed</key><false/>
    <key>PayloadType</key><string>Configuration</string>
    <key>PayloadUUID</key><string>{profile_uuid}</string>
    <key>PayloadVersion</key><integer>1</integer>
</dict>
</plist>"""

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/ios/enroll", methods=["POST"])
def enroll():
    """Called by onboarding form. Generates profile + one-time download link."""
    data = request.json or {}
    firstname        = data.get("firstname", "").strip().lower()
    user_email       = data.get("user_email", "").strip()
    partner_email    = data.get("partner_email", "").strip()
    partner_telegram = data.get("partner_telegram", "").strip().lstrip("@")

    if not all([firstname, user_email, partner_telegram]):
        return jsonify({"error": "Missing required fields"}), 400

    device_token = f"{firstname}-{make_random(4)}"
    link_token   = make_link_token()
    now          = int(datetime.now(timezone.utc).timestamp())
    expires      = now + 86400  # 24 hours

    with get_db() as db:
        db.execute("""
            INSERT INTO devices (token, user_firstname, user_email, partner_email,
                                 partner_telegram, last_seen, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (device_token, firstname, user_email, partner_email, partner_telegram, 0, now))
        db.execute("""
            INSERT INTO download_links (link_token, device_token, expires_at)
            VALUES (?, ?, ?)
        """, (link_token, device_token, expires))

    download_url = f"{BASE_URL}/ios/install?token={link_token}"
    return jsonify({"download_url": download_url, "device_token": device_token})


@app.route("/ios/install", methods=["GET"])
def install():
    """Serves the personalised .mobileconfig. One-time use."""
    link_token = request.args.get("token", "")
    now = int(datetime.now(timezone.utc).timestamp())

    with get_db() as db:
        link = db.execute(
            "SELECT * FROM download_links WHERE link_token=? AND used=0 AND expires_at>?",
            (link_token, now)
        ).fetchone()
        if not link:
            abort(404)

        device = db.execute(
            "SELECT * FROM devices WHERE token=?", (link["device_token"],)
        ).fetchone()
        if not device:
            abort(404)

        # Mark link used
        db.execute("UPDATE download_links SET used=1 WHERE link_token=?", (link_token,))

    profile_xml = generate_mobileconfig(device["token"], device["user_firstname"])
    profile_bytes = profile_xml.encode("utf-8")

    return send_file(
        io.BytesIO(profile_bytes),
        mimetype="application/x-apple-aspen-config",
        as_attachment=True,
        download_name="YouAreLoved.mobileconfig"
    )


@app.route("/webhook/nextdns", methods=["POST"])
def nextdns_webhook():
    """NextDNS fires this on every blocked domain query."""
    payload = request.json or {}
    device_label = payload.get("device", {}).get("name", "")  # e.g. "daniel-k7x2"
    domain       = payload.get("domain", "unknown")
    timestamp    = payload.get("timestamp", "")

    now = int(datetime.now(timezone.utc).timestamp())

    with get_db() as db:
        device = db.execute(
            "SELECT * FROM devices WHERE token=?", (device_label,)
        ).fetchone()

        if device:
            # Update last_seen and reset removal alert flag
            db.execute(
                "UPDATE devices SET last_seen=?, removal_alerted=0 WHERE token=?",
                (now, device_label)
            )
            partner_tg = device["partner_telegram"]
            firstname  = device["user_firstname"].capitalize()

            msg = (
                f"🔴 <b>Blocked attempt on {firstname}'s iPhone</b>\n"
                f"Domain: <code>{domain}</code>\n"
                f"Time: {datetime.now(timezone.utc).strftime('%I:%M%p UTC')}\n"
                f"Device: {device_label}"
            )
            send_telegram(partner_tg, msg)

    return jsonify({"status": "ok"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "yal-ios"})


# ── Silence detection cron (runs every 5 min) ─────────────────────────────────
def check_silence():
    now = int(datetime.now(timezone.utc).timestamp())
    cutoff_active  = now - ACTIVE_WINDOW      # must have been active in last 2h
    cutoff_silence = now - SILENCE_THRESHOLD  # silent for 30+ min

    with get_db() as db:
        # Devices that were recently active but have gone silent
        gone_silent = db.execute("""
            SELECT * FROM devices
            WHERE last_seen > ?
              AND last_seen < ?
              AND removal_alerted = 0
        """, (cutoff_active, cutoff_silence)).fetchall()

        for device in gone_silent:
            firstname  = device["user_firstname"].capitalize()
            partner_tg = device["partner_telegram"]
            last_seen_dt = datetime.fromtimestamp(device["last_seen"], tz=timezone.utc)
            silent_mins  = (now - device["last_seen"]) // 60

            msg = (
                f"⚠️ <b>Protection may have been removed from {firstname}'s iPhone</b>\n"
                f"No DNS queries for {silent_mins} minutes\n"
                f"Last seen: {last_seen_dt.strftime('%I:%M%p UTC')}\n"
                f"If {firstname} is not in Airplane Mode or a dead zone, "
                f"the protection profile may have been removed."
            )
            send_telegram(partner_tg, msg)
            db.execute(
                "UPDATE devices SET removal_alerted=1 WHERE token=?",
                (device["token"],)
            )

scheduler = BackgroundScheduler()
scheduler.add_job(check_silence, "interval", minutes=5)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
