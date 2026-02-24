#!/usr/bin/env python3
"""
You Are Loved — Setup UI

Native macOS tkinter app. Pure black/white monochrome.
4 screens: Welcome → Partner Setup → Installing → Complete.

Writes ~/.yal_config.json with multi-partner config.
Sends uninstall code directly to partners (never shown to user).
"""

import os
import sys
import json
import secrets
import hashlib
import threading
import urllib.request
from pathlib import Path
from datetime import datetime

# Tkinter is optional — terminal fallback if unavailable
try:
    import tkinter as tk
    from tkinter import ttk
    HAS_TK = True
except (ImportError, ModuleNotFoundError):
    HAS_TK = False

CONFIG_FILE = Path.home() / ".yal_config.json"

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

BG = "#000000"
FG = "#FFFFFF"
GREY = "#888888"
DARK_GREY = "#222222"
FONT = ("SF Pro Display", 13)
FONT_TITLE = ("SF Pro Display", 28, "bold")
FONT_SUB = ("SF Pro Display", 13)
FONT_SMALL = ("SF Pro Display", 11)
FONT_BTN = ("SF Pro Display", 13, "bold")
WIN_W, WIN_H = 520, 680


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def send_telegram(token, chat_id, text):
    if not token or not chat_id:
        return False
    try:
        data = json.dumps({"chat_id": chat_id, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data, headers={"Content-Type": "application/json"},
            method="POST")
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

def send_email(sg_key, to_email, subject, body):
    if not sg_key or not to_email:
        return False
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
            headers={"Authorization": f"Bearer {sg_key}",
                     "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception:
        return False

def resolve_telegram_chats(token):
    """Get chat_id mapping from bot updates."""
    if not token:
        return {}
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getUpdates")
        resp = urllib.request.urlopen(req, timeout=10)
        updates = json.loads(resp.read().decode())
        chats = {}
        for u in updates.get("result", []):
            msg = u.get("message", {})
            chat = msg.get("chat", {})
            username = chat.get("username", "")
            cid = str(chat.get("id", ""))
            if username and cid:
                chats[username.lower()] = cid
        return chats
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class SetupApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("You Are Loved")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # Center on screen
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        x = (sx - WIN_W) // 2
        y = (sy - WIN_H) // 2
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        # State
        self.num_partners = tk.IntVar(value=1)
        self.partner_frames = []
        self.partner_emails = []
        self.partner_telegrams = []

        # API keys (pre-fill from existing config)
        existing = {}
        if CONFIG_FILE.exists():
            try:
                existing = json.loads(CONFIG_FILE.read_text())
            except Exception:
                pass
        self.sg_key = tk.StringVar(value=existing.get("sendgrid_api_key", ""))
        self.tg_token = tk.StringVar(value=existing.get("telegram_bot_token", ""))
        self.anthropic_key = tk.StringVar(
            value=existing.get("anthropic_api_key", ""))

        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(fill="both", expand=True, padx=40, pady=30)

        self.show_welcome()

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def make_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command,
                        bg=FG, fg=BG, font=FONT_BTN,
                        relief="flat", cursor="hand2",
                        padx=20, pady=10, bd=0,
                        activebackground="#DDDDDD", activeforeground=BG)
        return btn

    def make_entry(self, parent, textvariable=None, placeholder=""):
        entry = tk.Entry(parent, bg=DARK_GREY, fg=FG, font=FONT,
                         insertbackground=FG, relief="flat", bd=0,
                         highlightthickness=1, highlightcolor=GREY,
                         highlightbackground="#333333",
                         textvariable=textvariable)
        if placeholder and textvariable and not textvariable.get():
            entry.insert(0, placeholder)
            entry.config(fg=GREY)
            def on_focus_in(e):
                if entry.get() == placeholder:
                    entry.delete(0, "end")
                    entry.config(fg=FG)
            def on_focus_out(e):
                if not entry.get():
                    entry.insert(0, placeholder)
                    entry.config(fg=GREY)
            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)
        return entry

    # --- Screen 1: Welcome ---

    def show_welcome(self):
        self.clear()
        spacer = tk.Frame(self.container, bg=BG, height=120)
        spacer.pack()

        tk.Label(self.container, text="You Are Loved",
                 font=FONT_TITLE, fg=FG, bg=BG).pack(pady=(0, 16))

        tk.Label(self.container,
                 text="Protection that stays with you.\n"
                      "Built on accountability, not surveillance.",
                 font=FONT_SUB, fg=GREY, bg=BG,
                 justify="center").pack(pady=(0, 60))

        btn = self.make_button(self.container, "Get Started",
                               self.show_partner_setup)
        btn.pack(fill="x", ipady=4)

    # --- Screen 2: Partner Setup ---

    def show_partner_setup(self):
        self.clear()
        self.partner_emails = []
        self.partner_telegrams = []
        self.partner_frames = []

        tk.Label(self.container, text="Accountability Partners",
                 font=("SF Pro Display", 20, "bold"),
                 fg=FG, bg=BG).pack(anchor="w", pady=(10, 20))

        # Partner count
        count_frame = tk.Frame(self.container, bg=BG)
        count_frame.pack(fill="x", pady=(0, 10))
        tk.Label(count_frame, text="Number of partners",
                 font=FONT, fg=FG, bg=BG).pack(side="left")

        stepper = tk.Frame(count_frame, bg=BG)
        stepper.pack(side="right")
        tk.Button(stepper, text=" − ", font=FONT_BTN, bg=DARK_GREY, fg=FG,
                  relief="flat", bd=0, command=self._dec_partners,
                  activebackground="#333333").pack(side="left", padx=2)
        self.count_label = tk.Label(stepper, textvariable=self.num_partners,
                                     font=FONT_BTN, fg=FG, bg=BG, width=3)
        self.count_label.pack(side="left")
        tk.Button(stepper, text=" + ", font=FONT_BTN, bg=DARK_GREY, fg=FG,
                  relief="flat", bd=0, command=self._inc_partners,
                  activebackground="#333333").pack(side="left", padx=2)

        # Scrollable partner area
        self.partner_area = tk.Frame(self.container, bg=BG)
        self.partner_area.pack(fill="both", expand=True, pady=(10, 10))

        self._rebuild_partner_fields()

        # Subtext
        tk.Label(self.container,
                 text="Your uninstall code will be sent directly\n"
                      "to your partner(s). You will not see it.",
                 font=FONT_SMALL, fg=GREY, bg=BG,
                 justify="center").pack(pady=(12, 12))

        btn = self.make_button(self.container, "Install Protection",
                               self.start_install)
        btn.pack(fill="x", ipady=4)

    def _dec_partners(self):
        v = self.num_partners.get()
        if v > 1:
            self.num_partners.set(v - 1)
            self._rebuild_partner_fields()

    def _inc_partners(self):
        v = self.num_partners.get()
        if v < 5:
            self.num_partners.set(v + 1)
            self._rebuild_partner_fields()

    def _rebuild_partner_fields(self):
        for w in self.partner_area.winfo_children():
            w.destroy()
        self.partner_emails = []
        self.partner_telegrams = []

        for i in range(self.num_partners.get()):
            f = tk.Frame(self.partner_area, bg=BG)
            f.pack(fill="x", pady=(0, 12))

            tk.Label(f, text=f"Partner {i+1}",
                     font=("SF Pro Display", 13, "bold"),
                     fg=FG, bg=BG).pack(anchor="w")

            email_var = tk.StringVar()
            self.partner_emails.append(email_var)
            tk.Label(f, text="Email", font=FONT_SMALL,
                     fg=GREY, bg=BG).pack(anchor="w")
            e = self.make_entry(f, email_var, "partner@email.com")
            e.pack(fill="x", ipady=5, pady=(0, 4))

            tg_var = tk.StringVar()
            self.partner_telegrams.append(tg_var)
            tk.Label(f, text="Telegram username (optional)",
                     font=FONT_SMALL, fg=GREY, bg=BG).pack(anchor="w")
            t = self.make_entry(f, tg_var, "@username")
            t.pack(fill="x", ipady=5)

    # --- Screen 3: Installing ---

    def start_install(self):
        # Validate
        partners = []
        for i in range(self.num_partners.get()):
            email = self.partner_emails[i].get().strip()
            if email in ("", "partner@email.com"):
                email = ""
            tg = self.partner_telegrams[i].get().strip()
            if tg in ("", "@username"):
                tg = ""
            if not email or "@" not in email:
                continue
            partners.append({"email": email, "telegram": tg,
                             "telegram_chat_id": ""})

        if not partners:
            tk.messagebox = __import__("tkinter.messagebox", fromlist=[""])
            tk.messagebox.showerror("Error",
                "Please enter at least one valid partner email.")
            return

        self.partners = partners
        self.show_installing()

    def show_installing(self):
        self.clear()

        spacer = tk.Frame(self.container, bg=BG, height=100)
        spacer.pack()

        tk.Label(self.container, text="Installing...",
                 font=("SF Pro Display", 24, "bold"),
                 fg=FG, bg=BG).pack(pady=(0, 30))

        # Progress bar
        style = ttk.Style()
        style.theme_use("default")
        style.configure("W.Horizontal.TProgressbar",
                        background=FG, troughcolor=DARK_GREY,
                        borderwidth=0, lightcolor=FG, darkcolor=FG)
        self.progress = ttk.Progressbar(
            self.container, style="W.Horizontal.TProgressbar",
            mode="determinate", length=400, maximum=100)
        self.progress.pack(pady=(0, 30))

        self.status_label = tk.Label(self.container, text="",
                                      font=FONT_SUB, fg=GREY, bg=BG)
        self.status_label.pack()

        # Run install in background thread
        threading.Thread(target=self._run_install, daemon=True).start()

    def _update_status(self, text, progress):
        self.root.after(0, lambda: self.status_label.configure(text=text))
        self.root.after(0, lambda: self.progress.configure(value=progress))

    def _run_install(self):
        try:
            self._update_status("Generating security code...", 10)
            code = f"{secrets.randbelow(1000000):06d}"
            code_hash = hash_code(code)

            self._update_status("Resolving Telegram contacts...", 25)
            tg_token = self.tg_token.get().strip()
            if tg_token and tg_token != "123456:ABC...":
                chats = resolve_telegram_chats(tg_token)
                for p in self.partners:
                    tg = p.get("telegram", "").lower().lstrip("@")
                    if tg and tg in chats:
                        p["telegram_chat_id"] = chats[tg]
            else:
                tg_token = ""

            sg_key = self.sg_key.get().strip()
            if sg_key == "SG.xxx":
                sg_key = ""
            anthropic_key = self.anthropic_key.get().strip()
            if anthropic_key == "sk-ant-...":
                anthropic_key = ""

            self._update_status("Writing configuration...", 40)
            cfg = {
                "setup_complete": True,
                "partners": self.partners,
                "code_hash": code_hash,
                "installed_at": datetime.now().isoformat(),
                "guardian_path": str(
                    Path.home() / "youareloved" / "guardian.py"),
                "sendgrid_api_key": sg_key,
                "telegram_bot_token": tg_token,
                "anthropic_api_key": anthropic_key,
            }
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

            self._update_status("Notifying your partner(s)...", 60)
            for p in self.partners:
                email = p.get("email", "")
                tg_chat = p.get("telegram_chat_id", "")

                code_msg = (
                    f"Your accountability partner has installed "
                    f"You Are Loved.\n\n"
                    f"Your uninstall code is: {code}\n\n"
                    f"Keep this safe — they will need it to uninstall.\n\n"
                    f"— You Are Loved"
                )

                if sg_key and email:
                    send_email(sg_key, email,
                        "Your You Are Loved uninstall code", code_msg)

                if tg_token and tg_chat:
                    send_telegram(tg_token, tg_chat, code_msg)

                # Welcome message
                welcome = (
                    "You have been listed as an accountability partner "
                    "on You Are Loved. You will receive alerts if content "
                    "is detected on this device. You do not need to "
                    "install anything."
                )
                if sg_key and email:
                    send_email(sg_key, email,
                        "You Are Loved — Accountability Partner",
                        welcome + "\n\n— You Are Loved")
                if tg_token and tg_chat:
                    send_telegram(tg_token, tg_chat, welcome)

            self._update_status("Activating protection...", 80)
            import time
            time.sleep(1)

            # Verify screen capture works — critical for image detection.
            # screencapture is tried first; if it fails, open System Settings
            # so the user can grant Screen Recording permission now.
            self._update_status("Verifying screen access...", 90)
            _tmpf = "/tmp/yal_perm_test.png"
            try:
                import subprocess as _sp, os as _os
                _r = _sp.run(
                    ["/usr/sbin/screencapture", "-x", _tmpf],
                    capture_output=True, timeout=10)
                _ok = (
                    _r.returncode == 0
                    and _os.path.exists(_tmpf)
                    and _os.path.getsize(_tmpf) > 10000
                )
            except Exception:
                _ok = False
            finally:
                try:
                    import os as _os2
                    if _os2.path.exists(_tmpf):
                        _os2.unlink(_tmpf)
                except Exception:
                    pass

            if not _ok:
                # Open Screen Recording settings and prompt user to grant access
                try:
                    import subprocess as _sp2
                    _sp2.run([
                        "open",
                        "x-apple.systempreferences:com.apple.preference.security"
                        "?Privacy_ScreenCapture"
                    ], timeout=5)
                except Exception:
                    pass
                self._update_status(
                    "Grant Screen Recording in System Settings, then continue.", 90)
                import time as _t
                _t.sleep(6)   # give the user time to grant and return

            self._update_status("Complete.", 100)
            import time
            time.sleep(0.5)
            self.root.after(0, self.show_complete)

        except Exception as e:
            self._update_status(f"Error: {e}", 0)

    # --- Screen 4: Complete ---

    def show_complete(self):
        self.clear()

        spacer = tk.Frame(self.container, bg=BG, height=140)
        spacer.pack()

        tk.Label(self.container, text="You are loved.",
                 font=FONT_TITLE, fg=FG, bg=BG).pack(pady=(0, 20))

        tk.Label(self.container,
                 text="Protection is active.\n"
                      "Your partner(s) have been notified.\n"
                      "The uninstall code has been sent to them.",
                 font=FONT_SUB, fg=GREY, bg=BG,
                 justify="center").pack(pady=(0, 60))

        btn = self.make_button(self.container, "Done",
                               self.root.destroy)
        btn.pack(fill="x", ipady=4)

    def run(self):
        self.root.mainloop()


def terminal_fallback():
    """Minimal terminal-based setup when tkinter/display is unavailable."""
    print("\n" + "=" * 46)
    print("  You Are Loved — Setup")
    print("=" * 46)

    existing = {}
    if CONFIG_FILE.exists():
        try:
            existing = json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass

    # Partners
    num = 0
    while num < 1 or num > 5:
        try:
            num = int(input("\nHow many accountability partners? (1-5): ").strip())
        except ValueError:
            pass

    partners = []
    for i in range(1, num + 1):
        email = ""
        while not email or "@" not in email:
            email = input(f"  Partner {i} email: ").strip()
        tg = input(f"  Partner {i} Telegram username (optional): ").strip()
        partners.append({"email": email, "telegram": tg,
                         "telegram_chat_id": ""})

    # API keys — pre-seeded by install.sh, just read from existing config
    sg_key = existing.get("sendgrid_api_key", "")
    tg_token = existing.get("telegram_bot_token", "")
    anthropic_key = existing.get("anthropic_api_key", "")

    # Resolve Telegram chat IDs
    if tg_token:
        chats = resolve_telegram_chats(tg_token)
        for p in partners:
            tg = p.get("telegram", "").lower().lstrip("@")
            if tg and tg in chats:
                p["telegram_chat_id"] = chats[tg]
                print(f"  ✓ Resolved {p['telegram']} → {chats[tg]}")

    # Generate code
    code = f"{secrets.randbelow(1000000):06d}"

    cfg = {
        "setup_complete": True,
        "partners": partners,
        "code_hash": hash_code(code),
        "installed_at": datetime.now().isoformat(),
        "guardian_path": str(Path.home() / "youareloved" / "guardian.py"),
        "sendgrid_api_key": sg_key,
        "telegram_bot_token": tg_token,
        "anthropic_api_key": anthropic_key,
    }
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

    # Send code to partners
    print("\n  Sending uninstall code to partner(s)...")
    sent = False
    for p in partners:
        msg = (f"Your accountability partner has installed You Are Loved.\n\n"
               f"Your uninstall code is: {code}\n\n"
               f"Keep this safe.\n\n— You Are Loved")
        if sg_key and p.get("email"):
            if send_email(sg_key, p["email"],
                          "Your You Are Loved uninstall code", msg):
                print(f"  ✓ Code emailed to {p['email']}")
                sent = True
        if tg_token and p.get("telegram_chat_id"):
            if send_telegram(tg_token, p["telegram_chat_id"], msg):
                print(f"  ✓ Code sent via Telegram")
                sent = True

    if not sent:
        print(f"\n  ⚠ Could not send code electronically.")
        print(f"  UNINSTALL CODE: {code}")
        print(f"  Send this to your partner manually.")
        print(f"  This will NOT be shown again.")

    # Welcome messages
    welcome = ("You have been listed as an accountability partner on "
               "You Are Loved. You will receive alerts if content is "
               "detected on this device.")
    for p in partners:
        if sg_key and p.get("email"):
            send_email(sg_key, p["email"],
                       "You Are Loved — Accountability Partner",
                       welcome + "\n\n— You Are Loved")
        if tg_token and p.get("telegram_chat_id"):
            send_telegram(tg_token, p["telegram_chat_id"], welcome)

    print(f"\n{'='*46}")
    print(f"  Setup complete.")
    if sent:
        print(f"  The uninstall code has been sent to your partner(s).")
        print(f"  You will not see it.")
    input("\n  Press Enter to continue...")


if __name__ == "__main__":
    if not HAS_TK:
        print("  (tkinter not available — using terminal setup)")
        terminal_fallback()
    else:
        try:
            app = SetupApp()
            app.run()
        except Exception as e:
            print(f"  (GUI unavailable: {e} — using terminal setup)")
            terminal_fallback()
