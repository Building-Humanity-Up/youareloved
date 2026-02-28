import os, sqlite3, secrets, string, json, requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import io, uuid

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "https://finallyfreeai.com", "https://www.finallyfreeai.com"])

# ── Config ────────────────────────────────────────────────────────────────────
NEXTDNS_CONFIG_ID  = os.environ["NEXTDNS_CONFIG_ID"]
NEXTDNS_API_KEY    = os.environ["NEXTDNS_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DB_PATH            = os.environ.get("DB_PATH", "devices.db")
BASE_URL           = os.environ["BASE_URL"]
SILENCE_THRESHOLD  = 30 * 60    # 30 minutes
ACTIVE_WINDOW      = 2 * 60 * 60  # 2 hours

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email       TEXT PRIMARY KEY,
                firstname   TEXT,
                created_at  INTEGER
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS partners (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email       TEXT,
                partner_name     TEXT,
                partner_email    TEXT,
                partner_telegram TEXT,
                added_at         INTEGER,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                token            TEXT PRIMARY KEY,
                user_email       TEXT,
                user_firstname   TEXT,
                last_seen        INTEGER DEFAULT 0,
                removal_alerted  INTEGER DEFAULT 0,
                created_at       INTEGER,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS download_links (
                link_token   TEXT PRIMARY KEY,
                device_token TEXT,
                expires_at   INTEGER,
                used         INTEGER DEFAULT 0
            )
        """)

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def send_telegram(chat_id: str, message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def make_random(n=4):
    return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def make_link_token():
    return secrets.token_urlsafe(16)

def get_partners(user_email: str):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM partners WHERE user_email=?", (user_email,)
        ).fetchall()

def notify_all_partners(user_email: str, message: str):
    for partner in get_partners(user_email):
        if partner["partner_telegram"]:
            send_telegram(partner["partner_telegram"], message)

# ── .mobileconfig generation ──────────────────────────────────────────────────
def generate_mobileconfig(device_token: str, firstname: str) -> str:
    doh_url = f"https://dns.nextdns.io/{NEXTDNS_CONFIG_ID}/{device_token}"
    profile_uuid  = str(uuid.uuid4()).upper()
    dns_uuid      = str(uuid.uuid4()).upper()

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>PayloadContent</key>
    <array>
        <dict>
            <key>PayloadType</key><string>com.apple.dnsSettings.managed</string>
            <key>PayloadIdentifier</key><string>app.youareloved.dns.{device_token}</string>
            <key>PayloadUUID</key><string>{dns_uuid}</string>
            <key>PayloadVersion</key><integer>1</integer>
            <key>PayloadDisplayName</key><string>You Are Loved — DNS Protection</string>
            <key>DNSSettings</key>
            <dict>
                <key>DNSProtocol</key><string>HTTPS</string>
                <key>ServerURL</key><string>{doh_url}</string>
                <key>ServerAddresses</key>
                <array>
                    <string>45.90.28.58</string>
                    <string>45.90.30.58</string>
                </array>
            </dict>
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

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "yal-ios"})

@app.route("/cron/check-silence", methods=["POST"])
def cron_check_silence():
    if request.headers.get("X-Cron-Secret") != os.environ.get("CRON_SECRET", "yal-cron-2026"):
        abort(403)
    check_silence()
    return jsonify({"status": "ok"})

@app.route("/debug/devices", methods=["GET"])
def debug_devices():
    if request.args.get("secret") != "yal-debug-2026":
        abort(403)
    with get_db() as db:
        devices = db.execute(
            "SELECT token, user_firstname, user_email, last_seen, removal_alerted, created_at FROM devices"
        ).fetchall()
        return jsonify([dict(d) for d in devices])

@app.route("/debug/users", methods=["GET"])
def debug_users():
    if request.args.get("secret") != "yal-debug-2026":
        abort(403)
    with get_db() as db:
        users    = db.execute("SELECT * FROM users").fetchall()
        partners = db.execute("SELECT * FROM partners").fetchall()
        return jsonify({
            "users":    [dict(u) for u in users],
            "partners": [dict(p) for p in partners]
        })

# ── Account: register user + add partners ─────────────────────────────────────

@app.route("/account/register", methods=["POST"])
def register():
    """Create or update a user account."""
    data      = request.json or {}
    email     = data.get("email", "").strip().lower()
    firstname = data.get("firstname", "").strip().lower()
    if not email or not firstname:
        return jsonify({"error": "email and firstname required"}), 400
    now = int(datetime.now(timezone.utc).timestamp())
    with get_db() as db:
        db.execute("""
            INSERT INTO users (email, firstname, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET firstname=excluded.firstname
        """, (email, firstname, now))
    return jsonify({"status": "ok", "email": email})

@app.route("/account/partners", methods=["POST"])
def add_partner():
    """Append-only: add an accountability partner to a user account."""
    data             = request.json or {}
    user_email       = data.get("user_email", "").strip().lower()
    partner_name     = data.get("partner_name", "").strip()
    partner_email    = data.get("partner_email", "").strip().lower()
    partner_telegram = data.get("partner_telegram", "").strip().lstrip("@")
    if not user_email or not partner_name:
        return jsonify({"error": "user_email and partner_name required"}), 400
    now = int(datetime.now(timezone.utc).timestamp())
    with get_db() as db:
        # Ensure user exists
        user = db.execute("SELECT * FROM users WHERE email=?", (user_email,)).fetchone()
        if not user:
            return jsonify({"error": "User not found. Register first."}), 404
        db.execute("""
            INSERT INTO partners (user_email, partner_name, partner_email, partner_telegram, added_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_email, partner_name, partner_email, partner_telegram, now))
    return jsonify({"status": "ok", "message": f"Partner {partner_name} added"})

@app.route("/account/partners", methods=["GET"])
def list_partners():
    """Get all partners for a user — called by install.sh and iOS enrollment."""
    email = request.args.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "email required"}), 400
    partners = get_partners(email)
    return jsonify([dict(p) for p in partners])

# ── iOS enrollment ────────────────────────────────────────────────────────────

@app.route("/ios/enroll", methods=["POST"])
def enroll():
    """Generate profile + one-time download link. Uses unified partner list."""
    data      = request.json or {}
    firstname = data.get("firstname", "").strip().lower()
    user_email = data.get("user_email", "").strip().lower()

    # Support legacy single-partner fields for backward compat
    partner_email    = data.get("partner_email", "").strip()
    partner_telegram = data.get("partner_telegram", "").strip().lstrip("@")

    if not firstname or not user_email:
        return jsonify({"error": "firstname and user_email required"}), 400

    now          = int(datetime.now(timezone.utc).timestamp())
    device_token = f"{firstname}-{make_random(4)}"
    link_token   = make_link_token()
    expires      = now + 86400

    with get_db() as db:
        # Upsert user
        db.execute("""
            INSERT INTO users (email, firstname, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET firstname=excluded.firstname
        """, (user_email, firstname, now))

        # If legacy partner fields provided and no partners exist yet, add them
        existing_partners = db.execute(
            "SELECT COUNT(*) as c FROM partners WHERE user_email=?", (user_email,)
        ).fetchone()["c"]

        if existing_partners == 0 and partner_telegram:
            db.execute("""
                INSERT INTO partners (user_email, partner_name, partner_email, partner_telegram, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_email, "Accountability Partner", partner_email, partner_telegram, now))

        # Create device
        db.execute("""
            INSERT INTO devices (token, user_email, user_firstname, last_seen, created_at)
            VALUES (?, ?, ?, 0, ?)
        """, (device_token, user_email, firstname, now))

        db.execute("""
            INSERT INTO download_links (link_token, device_token, expires_at)
            VALUES (?, ?, ?)
        """, (link_token, device_token, expires))

    download_url = f"{BASE_URL}/ios/install?token={link_token}"
    return jsonify({"download_url": download_url, "device_token": device_token})

@app.route("/ios/install", methods=["GET"])
def install():
    link_token = request.args.get("token", "")
    now = int(datetime.now(timezone.utc).timestamp())
    with get_db() as db:
        link = db.execute(
            "SELECT * FROM download_links WHERE link_token=? AND expires_at>?",
            (link_token, now)
        ).fetchone()
        if not link:
            abort(404)
        device = db.execute(
            "SELECT * FROM devices WHERE token=?", (link["device_token"],)
        ).fetchone()
        if not device:
            abort(404)

    firstname = device["user_firstname"].capitalize()

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>You Are Loved — Install Protection</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                background: #f2f2f7; padding: 40px 20px; text-align: center; }}
        h1 {{ font-size: 1.5rem; font-weight: 700; color: #1c1c1e; margin-bottom: 8px; }}
        .sub {{ color: #6c6c70; font-size: 0.95rem; line-height: 1.6; margin-bottom: 28px; }}
        .step {{ background: white; border-radius: 14px; padding: 16px 18px;
                 margin: 10px 0; text-align: left; display: flex;
                 align-items: flex-start; gap: 14px; }}
        .num {{ background: #1c1c1e; color: white; border-radius: 50%;
                min-width: 28px; height: 28px; display: flex; align-items: center;
                justify-content: center; font-size: 0.8rem; font-weight: 700; }}
        .step-text {{ font-size: 0.9rem; color: #1c1c1e; line-height: 1.5; padding-top: 3px; }}
        .btn {{ display: block; background: #1c1c1e; color: white; padding: 16px;
                border-radius: 14px; text-decoration: none; font-weight: 600;
                font-size: 1rem; margin: 24px 0 10px; }}
        .footer {{ font-size: 0.78rem; color: #aeaeb2; margin-top: 20px; }}
    </style>
    <script>
        window.onload = function() {{
            setTimeout(function() {{
                window.location.href = 'https://api.finallyfreeai.com/ios/profile/{link_token}';
            }}, 800);
        }};
    </script>
</head>
<body>
    <h1>Hi {firstname} 👋</h1>
    <p class="sub">Your protection profile is downloading now.<br>Follow these steps to install it.</p>
    <div class="step"><div class="num">1</div>
        <div class="step-text">Tap <b>Allow</b> when Safari asks to download a configuration profile</div></div>
    <div class="step"><div class="num">2</div>
        <div class="step-text">Tap <b>Close</b> on the "Profile Downloaded" banner</div></div>
    <div class="step"><div class="num">3</div>
        <div class="step-text">Open <b>Settings → General → VPN &amp; Device Management</b></div></div>
    <div class="step"><div class="num">4</div>
        <div class="step-text">Tap <b>You Are Loved Protection</b> → <b>Install</b> → enter your passcode</div></div>
    <a href="https://api.finallyfreeai.com/ios/profile/{link_token}" class="btn">
        Download Profile →
    </a>
    <p class="footer">You Are Loved · Building Humanity Up</p>
</body>
</html>"""

@app.route("/ios/profile/<link_token>", methods=["GET"])
def serve_profile(link_token):
    now = int(datetime.now(timezone.utc).timestamp())
    with get_db() as db:
        link = db.execute(
            "SELECT * FROM download_links WHERE link_token=? AND expires_at>?",
            (link_token, now)
        ).fetchone()
        if not link:
            abort(404)
        device = db.execute(
            "SELECT * FROM devices WHERE token=?", (link["device_token"],)
        ).fetchone()
        if not device:
            abort(404)
    profile_xml = generate_mobileconfig(device["token"], device["user_firstname"])
    return send_file(
        io.BytesIO(profile_xml.encode("utf-8")),
        mimetype="application/x-apple-aspen-config",
        as_attachment=True,
        download_name="YouAreLoved.mobileconfig"
    )

@app.route("/webhook/nextdns", methods=["POST"])
def nextdns_webhook():
    payload      = request.json or {}
    device_token = payload.get("device", {}).get("name", "")
    domain       = payload.get("domain", "unknown")
    now          = int(datetime.now(timezone.utc).timestamp())
    with get_db() as db:
        device = db.execute(
            "SELECT * FROM devices WHERE token=?", (device_token,)
        ).fetchone()
        if device:
            db.execute(
                "UPDATE devices SET last_seen=?, removal_alerted=0 WHERE token=?",
                (now, device_token)
            )
            firstname = device["user_firstname"].capitalize()
            msg = (
                f"🔴 <b>Blocked attempt on {firstname}'s iPhone</b>\n"
                f"Domain: <code>{domain}</code>\n"
                f"Time: {datetime.now(timezone.utc).strftime('%I:%M %p UTC')}"
            )
            notify_all_partners(device["user_email"], msg)
    return jsonify({"status": "ok"})

@app.route("/api/config", methods=["GET"])
def api_config():
    """Called by macOS install.sh to fetch operator keys."""
    return jsonify({
        "telegram_bot_token": TELEGRAM_BOT_TOKEN,
        "sendgrid_api_key":   os.environ.get("SENDGRID_API_KEY", ""),
        "nextdns_config_id":  NEXTDNS_CONFIG_ID,
        "base_url":           BASE_URL
    })

# ── Silence detection cron ────────────────────────────────────────────────────
def update_last_seen_from_nextdns():
    try:
        resp = requests.get(
            f"https://api.nextdns.io/profiles/{NEXTDNS_CONFIG_ID}/logs?limit=100",
            headers={"X-Api-Key": NEXTDNS_API_KEY},
            timeout=10
        )
        if resp.status_code != 200:
            print(f"NextDNS API error: {resp.status_code}")
            return
        entries = resp.json().get("data", [])
        latest = {}
        for entry in entries:
            token  = entry.get("device", {}).get("name", "")
            ts_str = entry.get("timestamp", "")
            if not token or not ts_str:
                continue
            ts = int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp())
            if token not in latest or ts > latest[token]:
                latest[token] = ts
        with get_db() as db:
            for token, ts in latest.items():
                db.execute(
                    "UPDATE devices SET last_seen=?, removal_alerted=0 WHERE token=? AND last_seen < ?",
                    (ts, token, ts)
                )
        print(f"NextDNS poll: updated {len(latest)} devices")
    except Exception as e:
        print(f"NextDNS poll error: {e}")

def check_silence():
    update_last_seen_from_nextdns()
    now            = int(datetime.now(timezone.utc).timestamp())
    cutoff_active  = now - ACTIVE_WINDOW
    cutoff_silence = now - SILENCE_THRESHOLD
    with get_db() as db:
        gone_silent = db.execute("""
            SELECT * FROM devices
            WHERE last_seen > ? AND last_seen < ? AND removal_alerted = 0
        """, (cutoff_active, cutoff_silence)).fetchall()
        for device in gone_silent:
            firstname    = device["user_firstname"].capitalize()
            last_seen_dt = datetime.fromtimestamp(device["last_seen"], tz=timezone.utc)
            silent_mins  = (now - device["last_seen"]) // 60
            msg = (
                f"⚠️ <b>Protection may have been removed from {firstname}'s iPhone</b>\n"
                f"No DNS activity for {silent_mins} minutes\n"
                f"Last seen: {last_seen_dt.strftime('%I:%M %p UTC')}\n"
                f"If {firstname} is not in Airplane Mode, the profile was likely removed."
            )
            notify_all_partners(device["user_email"], msg)
            db.execute(
                "UPDATE devices SET removal_alerted=1 WHERE token=?",
                (device["token"],)
            )

scheduler = BackgroundScheduler()
scheduler.add_job(check_silence, "interval", minutes=5)
scheduler.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
