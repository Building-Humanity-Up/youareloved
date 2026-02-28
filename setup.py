#!/usr/bin/env python3
"""
You Are Loved — Setup UI

Native macOS tkinter app. Pure black/white monochrome.
5 screens: Welcome → Partner Setup → Screen Access → Installing → Complete.

Writes ~/.yal_config.json with multi-partner config.
Sends uninstall code directly to partners (never shown to user).

The Screen Access screen gates installation: the user cannot proceed
until Screen Recording is verified to return full desktop content
(not just wallpaper). This prevents the silent failure mode where
Guardian runs but sees nothing.
"""

import os
import sys
import json
import hmac
import time
import secrets
import hashlib
import subprocess
import threading
import webbrowser
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
# Parse --python-real from install.sh
# ---------------------------------------------------------------------------

def _parse_python_real() -> str:
    """Extract --python-real value from argv, or resolve it ourselves."""
    for i, arg in enumerate(sys.argv):
        if arg == "--python-real" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    # Fallback: resolve our own executable
    return os.path.realpath(sys.executable)

PYTHON_REAL = _parse_python_real()

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

BG = "#000000"
FG = "#FFFFFF"
GREY = "#888888"
DARK_GREY = "#222222"
YELLOW = "#FFD60A"
GREEN = "#44CC44"
RED = "#FF6666"
FONT = ("SF Pro Display", 13)
FONT_TITLE = ("SF Pro Display", 28, "bold")
FONT_SUB = ("SF Pro Display", 13)
FONT_SMALL = ("SF Pro Display", 11)
FONT_BTN = ("SF Pro Display", 13, "bold")
FONT_MONO = ("SF Mono", 11)
WIN_W, WIN_H = 520, 720


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
# Screen Recording verification
# ---------------------------------------------------------------------------

def verify_screen_recording(python_path: str = "") -> str:
    """
    Content-aware Screen Recording verification.

    Uses the resolved Python binary to capture the screen, then measures
    luminance standard deviation to distinguish:
      - Full desktop (windows, text, UI chrome): std > 45 → "yes"
      - Wallpaper-only (smooth gradient, no windows): std 3-45 → "wallpaper"
      - Black / failed: std < 3 or error → "no"

    Returns: "yes", "wallpaper", or "no"
    """
    py = python_path or PYTHON_REAL
    try:
        r = subprocess.run(
            [py, "-c", """
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
    if all(b == 0 for b in data[:2000]):
        print('no'); sys.exit(0)
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
"""],
            capture_output=True, text=True, timeout=15)
        return r.stdout.strip() or "no"
    except Exception:
        return "no"


def trigger_tcc_prepopulation(python_path: str = ""):
    """
    Attempt a screen capture with the resolved binary so macOS adds it
    to the TCC Screen Recording list (toggled OFF). On macOS 14+, this
    means the user may only need to toggle ON instead of manually adding.
    """
    py = python_path or PYTHON_REAL
    try:
        subprocess.run(
            [py, "-c", """
try:
    import Quartz
    Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
        Quartz.kCGWindowImageDefault)
except: pass
"""],
            capture_output=True, timeout=10)
    except Exception:
        pass


def open_screen_recording_settings():
    """Open System Settings to the Screen Recording pane."""
    try:
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security"
            "?Privacy_ScreenCapture"
        ], capture_output=True, timeout=5)
    except Exception:
        pass
    try:
        subprocess.run([
            "osascript", "-e",
            'tell application "System Settings" to activate'
        ], capture_output=True, timeout=5)
    except Exception:
        pass


def copy_to_clipboard(text: str):
    """Copy text to macOS clipboard."""
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode())
    except Exception:
        pass


API_BASE = "https://api.finallyfreeai.com"


def api_post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}{path}", data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode())


def api_get(path: str) -> dict:
    req = urllib.request.Request(f"{API_BASE}{path}")
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read().decode())


def verify_accessibility() -> bool:
    """Check if Accessibility (AX) permission is granted."""
    try:
        r = subprocess.run(
            [PYTHON_REAL, "-c", """
import sys
try:
    from ApplicationServices import AXIsProcessTrusted
    print("yes" if AXIsProcessTrusted() else "no")
except Exception:
    try:
        import subprocess
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of first process'],
            capture_output=True, timeout=5)
        print("yes" if r.returncode == 0 else "no")
    except Exception:
        print("no")
"""],
            capture_output=True, text=True, timeout=10)
        return r.stdout.strip() == "yes"
    except Exception:
        return False


def open_accessibility_settings():
    """Open System Settings to the Accessibility pane."""
    try:
        subprocess.run([
            "open",
            "x-apple.systempreferences:com.apple.preference.security"
            "?Privacy_Accessibility"
        ], capture_output=True, timeout=5)
    except Exception:
        pass


def _draw_settings_diagram(canvas, w, h, highlight_section, highlight_item):
    """Draw a simplified System Settings visual on a tkinter Canvas.

    highlight_section: text to highlight in the sidebar (e.g. "Privacy & Security")
    highlight_item: text for the right pane row (e.g. "Screen Recording")
    """
    canvas.delete("all")

    # Window chrome
    rx, ry, rw, rh = 20, 10, w - 40, h - 20
    canvas.create_rectangle(rx, ry, rx + rw, ry + rh,
                            outline="#555555", width=1, fill="#1A1A1A")
    # Title bar
    canvas.create_rectangle(rx, ry, rx + rw, ry + 24,
                            outline="#555555", fill="#2A2A2A")
    canvas.create_text(rx + rw // 2, ry + 12,
                       text="System Settings", fill=GREY,
                       font=("SF Pro Display", 9))
    # Traffic lights
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        canvas.create_oval(rx + 8 + i * 16, ry + 6, rx + 20 + i * 16, ry + 18,
                           fill=c, outline="")

    # Sidebar
    sidebar_w = rw // 3
    canvas.create_line(rx + sidebar_w, ry + 24, rx + sidebar_w, ry + rh,
                       fill="#333333")
    sidebar_items = ["General", "Appearance", highlight_section, "Notifications"]
    for i, item in enumerate(sidebar_items):
        iy = ry + 36 + i * 22
        if item == highlight_section:
            canvas.create_rectangle(rx + 4, iy - 2, rx + sidebar_w - 4, iy + 16,
                                    fill="#3A3A3A", outline="")
            canvas.create_text(rx + 14, iy + 7, text=item, fill=FG,
                               font=("SF Pro Display", 9, "bold"), anchor="w")
            # Arrow from sidebar to right pane
            ax = rx + sidebar_w + 6
            canvas.create_text(ax, iy + 7, text="\u2192", fill=YELLOW,
                               font=("SF Pro Display", 12))
        else:
            canvas.create_text(rx + 14, iy + 7, text=item, fill="#666666",
                               font=("SF Pro Display", 9), anchor="w")

    # Right pane
    pane_x = rx + sidebar_w + 16
    pane_y = ry + 36
    pane_items = ["Accessibility", highlight_item, "Files and Folders"]
    if highlight_item == "Accessibility":
        pane_items = [highlight_item, "Screen Recording", "Files and Folders"]
    for i, item in enumerate(pane_items):
        iy = pane_y + i * 26
        if item == highlight_item:
            canvas.create_rectangle(pane_x - 4, iy - 2,
                                    rx + rw - 8, iy + 20,
                                    fill="#3A3A3A", outline="")
            canvas.create_text(pane_x + 4, iy + 9, text=item, fill=FG,
                               font=("SF Pro Display", 10, "bold"), anchor="w")
            # Toggle indicator
            tx = rx + rw - 32
            canvas.create_oval(tx, iy + 2, tx + 16, iy + 16,
                               fill=GREEN, outline="")
            # Arrow pointing at the toggle
            canvas.create_text(tx - 10, iy + 9, text="\u2190", fill=YELLOW,
                               font=("SF Pro Display", 12))
        else:
            canvas.create_text(pane_x + 4, iy + 9, text=item, fill="#555555",
                               font=("SF Pro Display", 9), anchor="w")

    # "Python" sub-row under the highlighted item
    py_y = pane_y + pane_items.index(highlight_item) * 26 + 24
    canvas.create_text(pane_x + 20, py_y + 6, text="Python 3.11",
                       fill=GREY, font=("SF Pro Display", 9), anchor="w")
    tx2 = rx + rw - 32
    canvas.create_oval(tx2, py_y, tx2 + 16, py_y + 12,
                       fill=GREEN, outline="")


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
        self.screen_verified = False
        self._sr_check_after_id = None
        # Account sign-in state
        self.account_token = ""
        self.account_email = ""
        self.account_firstname = ""

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

        self.show_signin()

    def clear(self):
        # Cancel any pending after() callbacks
        if self._sr_check_after_id:
            self.root.after_cancel(self._sr_check_after_id)
            self._sr_check_after_id = None
        for w in self.container.winfo_children():
            w.destroy()

    def make_button(self, parent, text, command, enabled=True):
        state = "normal" if enabled else "disabled"
        bg = FG if enabled else "#444444"
        fg = BG if enabled else "#888888"
        btn = tk.Button(parent, text=text, command=command,
                        bg=bg, fg=fg, font=FONT_BTN,
                        relief="flat", cursor="hand2" if enabled else "",
                        padx=20, pady=10, bd=0, state=state,
                        activebackground="#DDDDDD", activeforeground=BG,
                        disabledforeground="#666666")
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

    # --- Screen 0: Sign In or Create Account ---

    def show_signin(self):
        self.clear()

        spacer = tk.Frame(self.container, bg=BG, height=60)
        spacer.pack()

        tk.Label(self.container, text="Sign In",
                 font=("SF Pro Display", 22, "bold"),
                 fg=FG, bg=BG).pack(pady=(0, 6))

        tk.Label(self.container,
                 text="Sign in to restore your account\nand skip partner setup.",
                 font=FONT_SUB, fg=GREY, bg=BG,
                 justify="center").pack(pady=(0, 24))

        tk.Label(self.container, text="Email", font=FONT_SMALL,
                 fg=GREY, bg=BG).pack(anchor="w")
        self._si_email = tk.StringVar(value=self.account_email)
        self.make_entry(self.container, self._si_email,
                        "you@example.com").pack(fill="x", ipady=5, pady=(2, 10))

        tk.Label(self.container, text="Password", font=FONT_SMALL,
                 fg=GREY, bg=BG).pack(anchor="w")
        self._si_pw = tk.StringVar()
        pw_entry = tk.Entry(self.container, bg=DARK_GREY, fg=FG, font=FONT,
                            insertbackground=FG, relief="flat", bd=0,
                            highlightthickness=1, highlightcolor=GREY,
                            highlightbackground="#333333",
                            textvariable=self._si_pw, show="\u2022")
        pw_entry.pack(fill="x", ipady=5, pady=(2, 10))

        self._si_status = tk.Label(self.container, text="",
                                   font=FONT_SMALL, fg="#FF6666", bg=BG)
        self._si_status.pack(anchor="w", pady=(0, 8))

        self._si_btn = self.make_button(self.container, "Sign In",
                                        self._do_signin)
        self._si_btn.pack(fill="x", ipady=4, pady=(0, 10))

        tk.Button(self.container,
                  text="Create account at finallyfreeai.com \u2192",
                  command=lambda: webbrowser.open("https://finallyfreeai.com/setup"),
                  bg=BG, fg=GREY, font=FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=BG, activeforeground=FG).pack(pady=(0, 4))

        tk.Button(self.container,
                  text="Skip \u2014 set up manually instead",
                  command=self.show_welcome,
                  bg=BG, fg="#444444", font=FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground=BG).pack(pady=(16, 0))

    def _do_signin(self):
        email = self._si_email.get().strip().lower()
        pw    = self._si_pw.get().strip()
        if not email or "@" not in email:
            self._si_status.configure(text="Please enter a valid email.")
            return
        if not pw:
            self._si_status.configure(text="Please enter your password.")
            return
        self._si_btn.configure(state="disabled", text="Signing in\u2026")
        self._si_status.configure(text="")
        threading.Thread(target=self._signin_thread,
                         args=(email, pw), daemon=True).start()

    def _signin_thread(self, email: str, pw: str):
        try:
            result = api_post("/account/login", {"email": email, "password": pw})
            token     = result.get("token", "")
            firstname = result.get("firstname", "")
            if not token:
                raise ValueError("No token in response")
            me = api_get(f"/account/me?token={token}")
            partners_raw = me.get("partners", [])
            partners = [
                {
                    "email":            p.get("partner_email", ""),
                    "telegram":         p.get("partner_telegram", ""),
                    "telegram_chat_id": "",
                    "name":             p.get("partner_name", ""),
                }
                for p in partners_raw
            ]
            self.root.after(0, lambda: self._signin_success(
                token, email, firstname, partners))
        except Exception as ex:
            msg = str(ex)
            if "401" in msg or "403" in msg:
                msg = "Incorrect email or password."
            elif "urlopen" in msg.lower() or "socket" in msg.lower():
                msg = "Could not connect. Check your internet."
            self.root.after(0, lambda: self._signin_error(msg))

    def _signin_success(self, token: str, email: str,
                        firstname: str, partners: list):
        self.account_token     = token
        self.account_email     = email
        self.account_firstname = firstname
        if partners:
            self.partners = partners
        self._show_signin_welcome(firstname, partners)

    def _signin_error(self, msg: str):
        self._si_btn.configure(state="normal", text="Sign In")
        self._si_status.configure(text=msg)

    def _show_signin_welcome(self, firstname: str, partners: list):
        self.clear()

        spacer = tk.Frame(self.container, bg=BG, height=120)
        spacer.pack()

        n = len(partners)
        partner_text = (f"{n} partner{'s' if n != 1 else ''} ready"
                        if partners else "no partners yet")

        tk.Label(self.container,
                 text=f"Welcome back, {firstname.capitalize()}.",
                 font=("SF Pro Display", 22, "bold"),
                 fg=FG, bg=BG).pack(pady=(0, 14))

        tk.Label(self.container,
                 text=f"Your {partner_text}.\n\n"
                      "Partner setup will be skipped.\n"
                      "Going straight to installing.",
                 font=FONT_SUB, fg=GREY, bg=BG,
                 justify="center").pack(pady=(0, 50))

        btn = self.make_button(self.container, "Continue \u2192",
                               self.show_screen_access)
        btn.pack(fill="x", ipady=4)

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

        btn = self.make_button(self.container, "Continue",
                               self._validate_and_continue)
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

    def _validate_and_continue(self):
        """Validate partner fields, then show Screen Access gate."""
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
        self.show_screen_access()

    # --- Screen 3: Screen Recording (verification gate) ---

    def show_screen_access(self):
        self.clear()
        self.screen_verified = False

        tk.Label(self.container, text="Screen Recording",
                 font=("SF Pro Display", 20, "bold"),
                 fg=FG, bg=BG).pack(anchor="w", pady=(10, 4))

        tk.Label(self.container,
                 text="Guardian needs to see your screen to detect content.",
                 font=FONT_SUB, fg=GREY, bg=BG, wraplength=440,
                 justify="left").pack(anchor="w", pady=(0, 10))

        # Visual diagram
        self.sr_canvas = tk.Canvas(self.container, width=WIN_W - 80,
                                   height=140, bg=BG, highlightthickness=0)
        self.sr_canvas.pack(pady=(0, 8))
        _draw_settings_diagram(self.sr_canvas, WIN_W - 80, 140,
                               "Privacy & Security", "Screen Recording")

        # Status area
        self.sr_status_frame = tk.Frame(self.container, bg=BG)
        self.sr_status_frame.pack(fill="x", pady=(0, 6))

        self.sr_status_icon = tk.Label(self.sr_status_frame,
                                       text="\u25cb",
                                       font=("SF Pro Display", 16),
                                       fg=GREY, bg=BG)
        self.sr_status_icon.pack(side="left", padx=(0, 10))
        self.sr_status_text = tk.Label(self.sr_status_frame,
                                       text="Checking\u2026",
                                       font=FONT, fg=GREY, bg=BG)
        self.sr_status_text.pack(side="left")

        # Steps area (shown when not yet verified)
        self.sr_steps = tk.Frame(self.container, bg=BG)
        self.sr_steps.pack(fill="x", pady=(0, 4))
        self._sr_build_steps()

        # Path display (hidden initially)
        self.sr_path_frame = tk.Frame(self.container, bg=DARK_GREY,
                                      highlightthickness=1,
                                      highlightbackground="#333333")
        self.sr_path_label = tk.Label(self.sr_path_frame,
                                      text=PYTHON_REAL,
                                      font=FONT_MONO, fg=GREY, bg=DARK_GREY,
                                      wraplength=420, justify="left")
        self.sr_path_label.pack(padx=12, pady=6, anchor="w")

        # Copy button (hidden initially)
        self.sr_copy_btn = tk.Button(
            self.container, text="Copy Path to Clipboard",
            command=self._copy_path,
            bg=DARK_GREY, fg=FG, font=FONT_SMALL,
            relief="flat", bd=0, cursor="hand2",
            activebackground="#333333")

        # Continue button (disabled until verified)
        self.sr_continue_btn = self.make_button(
            self.container, "Continue",
            self.show_accessibility, enabled=False)
        self.sr_continue_btn.pack(fill="x", ipady=4, side="bottom")

        # Skip link (after several failed attempts)
        self.sr_skip_frame = tk.Frame(self.container, bg=BG)
        self.sr_skip_frame.pack(fill="x", side="bottom", pady=(8, 0))

        self.sr_attempt_count = 0

        # Trigger TCC pre-population and start checking
        threading.Thread(target=self._sr_initial_check, daemon=True).start()

    def _sr_build_steps(self):
        """Populate numbered steps."""
        for w in self.sr_steps.winfo_children():
            w.destroy()
        tk.Label(self.sr_steps, text="Here's exactly what to do:",
                 font=("SF Pro Display", 11, "bold"),
                 fg=FG, bg=BG).pack(anchor="w", pady=(0, 4))
        steps = [
            "Open System Settings \u2192 Privacy & Security",
            "Click Screen Recording",
            "Find Python and toggle it ON",
            "If Python isn't listed: click +, press\n"
            "Cmd+Shift+G, paste the path below, click Open",
        ]
        for i, s in enumerate(steps, 1):
            row = tk.Frame(self.sr_steps, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{i}.", font=FONT_SMALL, fg=YELLOW,
                     bg=BG, width=2).pack(side="left", anchor="n")
            tk.Label(row, text=s, font=FONT_SMALL, fg=GREY, bg=BG,
                     wraplength=400, justify="left").pack(side="left",
                                                          anchor="w")

    def _sr_initial_check(self):
        trigger_tcc_prepopulation()
        time.sleep(1)
        result = verify_screen_recording()
        self.root.after(0, lambda: self._sr_handle_result(result))

    def _sr_handle_result(self, result: str):
        if result == "yes":
            self.screen_verified = True
            self.sr_status_icon.configure(text="\u2713", fg=GREEN)
            self.sr_status_text.configure(
                text="Screen Recording is enabled.", fg=FG)
            self.sr_steps.pack_forget()
            self.sr_path_frame.pack_forget()
            self.sr_copy_btn.pack_forget()
            self.sr_skip_frame.pack_forget()
            self.sr_continue_btn.configure(
                state="normal", bg=FG, fg=BG, cursor="hand2")
        elif result == "wallpaper":
            self.sr_attempt_count += 1
            self.sr_status_icon.configure(text="\u25d0", fg=RED)
            self.sr_status_text.configure(
                text="Almost \u2014 wrong Python selected.\n"
                     "Make sure the path below is toggled ON:",
                fg=RED)
            self._sr_show_path_and_buttons()
        else:
            self.sr_attempt_count += 1
            self.sr_status_icon.configure(text="\u25cb", fg=RED)
            self.sr_status_text.configure(
                text="Screen Recording not enabled yet.", fg=RED)
            self._sr_show_path_and_buttons()
            if self.sr_attempt_count == 1:
                open_screen_recording_settings()

    def _sr_show_path_and_buttons(self):
        self.sr_path_frame.pack(fill="x", pady=(4, 4),
                                before=self.sr_continue_btn)
        self.sr_copy_btn.pack(anchor="w", pady=(2, 4),
                              before=self.sr_continue_btn)

        # Rebuild steps area with action buttons
        for w in self.sr_steps.winfo_children():
            w.destroy()

        tk.Button(self.sr_steps,
                  text="Open Screen Recording Settings",
                  command=open_screen_recording_settings,
                  bg=DARK_GREY, fg=FG, font=FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground="#333333").pack(anchor="w", pady=(4, 2))

        tk.Button(self.sr_steps,
                  text="I've enabled it \u2014 check again",
                  command=self._sr_recheck,
                  bg=DARK_GREY, fg=FG, font=FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground="#333333").pack(anchor="w", pady=(2, 0))

        if self.sr_attempt_count >= 3:
            for w in self.sr_skip_frame.winfo_children():
                w.destroy()
            tk.Button(self.sr_skip_frame,
                      text="Skip for now \u2014 I'll fix this later",
                      command=self._sr_skip,
                      bg=BG, fg="#666666", font=FONT_SMALL,
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=BG).pack(anchor="center")
            self.sr_skip_frame.pack(fill="x", side="bottom", pady=(8, 0))

        self._sr_schedule_autopoll()

    def _sr_schedule_autopoll(self):
        if self.screen_verified:
            return

        def _poll():
            result = verify_screen_recording()
            if result == "yes":
                self.root.after(0, lambda: self._sr_handle_result("yes"))
            else:
                self._sr_check_after_id = self.root.after(
                    3000, self._sr_schedule_autopoll)

        threading.Thread(target=_poll, daemon=True).start()

    def _sr_recheck(self):
        self.sr_status_icon.configure(text="\u25cb", fg=GREY)
        self.sr_status_text.configure(text="Checking\u2026", fg=GREY)

        def _check():
            result = verify_screen_recording()
            self.root.after(0, lambda: self._sr_handle_result(result))

        threading.Thread(target=_check, daemon=True).start()

    def _sr_skip(self):
        self.screen_verified = False
        self.show_accessibility()

    def _copy_path(self):
        copy_to_clipboard(PYTHON_REAL)
        self.sr_copy_btn.configure(text="Copied \u2713")
        self.root.after(2000, lambda: self.sr_copy_btn.configure(
            text="Copy Path to Clipboard"))

    # --- Screen 3b: Accessibility Permission ---

    def show_accessibility(self):
        self.clear()
        self.ax_verified = False

        tk.Label(self.container, text="Accessibility",
                 font=("SF Pro Display", 20, "bold"),
                 fg=FG, bg=BG).pack(anchor="w", pady=(10, 4))

        tk.Label(self.container,
                 text="Required to detect browser tab content\n"
                      "and close windows when harmful content is found.",
                 font=FONT_SUB, fg=GREY, bg=BG, wraplength=440,
                 justify="left").pack(anchor="w", pady=(0, 10))

        # Visual diagram
        ax_canvas = tk.Canvas(self.container, width=WIN_W - 80,
                              height=140, bg=BG, highlightthickness=0)
        ax_canvas.pack(pady=(0, 8))
        _draw_settings_diagram(ax_canvas, WIN_W - 80, 140,
                               "Privacy & Security", "Accessibility")

        # Status
        ax_status_frame = tk.Frame(self.container, bg=BG)
        ax_status_frame.pack(fill="x", pady=(0, 6))

        self.ax_status_icon = tk.Label(ax_status_frame,
                                       text="\u25cb",
                                       font=("SF Pro Display", 16),
                                       fg=GREY, bg=BG)
        self.ax_status_icon.pack(side="left", padx=(0, 10))
        self.ax_status_text = tk.Label(ax_status_frame,
                                       text="Checking\u2026",
                                       font=FONT, fg=GREY, bg=BG)
        self.ax_status_text.pack(side="left")

        # Steps
        self.ax_steps = tk.Frame(self.container, bg=BG)
        self.ax_steps.pack(fill="x", pady=(0, 4))
        tk.Label(self.ax_steps, text="Here's exactly what to do:",
                 font=("SF Pro Display", 11, "bold"),
                 fg=FG, bg=BG).pack(anchor="w", pady=(0, 4))
        steps = [
            "Open System Settings \u2192 Privacy & Security",
            "Click Accessibility",
            "Find Python and toggle it ON",
            "If Python isn't listed: click +, press\n"
            "Cmd+Shift+G, paste the path below, click Open",
        ]
        for i, s in enumerate(steps, 1):
            row = tk.Frame(self.ax_steps, bg=BG)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"{i}.", font=FONT_SMALL, fg=YELLOW,
                     bg=BG, width=2).pack(side="left", anchor="n")
            tk.Label(row, text=s, font=FONT_SMALL, fg=GREY, bg=BG,
                     wraplength=400, justify="left").pack(side="left",
                                                          anchor="w")

        # Path + copy
        ax_path_frame = tk.Frame(self.container, bg=DARK_GREY,
                                  highlightthickness=1,
                                  highlightbackground="#333333")
        ax_path_frame.pack(fill="x", pady=(4, 4))
        tk.Label(ax_path_frame, text=PYTHON_REAL,
                 font=FONT_MONO, fg=GREY, bg=DARK_GREY,
                 wraplength=420, justify="left").pack(padx=12, pady=6,
                                                      anchor="w")

        self.ax_copy_btn = tk.Button(
            self.container, text="Copy Path to Clipboard",
            command=self._ax_copy_path,
            bg=DARK_GREY, fg=FG, font=FONT_SMALL,
            relief="flat", bd=0, cursor="hand2",
            activebackground="#333333")
        self.ax_copy_btn.pack(anchor="w", pady=(0, 4))

        # Buttons
        btn_frame = tk.Frame(self.container, bg=BG)
        btn_frame.pack(fill="x", pady=(4, 0))

        tk.Button(btn_frame,
                  text="Open Accessibility Settings",
                  command=open_accessibility_settings,
                  bg=DARK_GREY, fg=FG, font=FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground="#333333").pack(anchor="w", pady=(0, 2))

        tk.Button(btn_frame,
                  text="I've enabled it \u2014 check again",
                  command=self._ax_recheck,
                  bg=DARK_GREY, fg=FG, font=FONT_SMALL,
                  relief="flat", bd=0, cursor="hand2",
                  activebackground="#333333").pack(anchor="w", pady=(2, 0))

        # Continue (disabled until verified)
        self.ax_continue_btn = self.make_button(
            self.container, "Continue",
            self.show_permission_summary, enabled=False)
        self.ax_continue_btn.pack(fill="x", ipady=4, side="bottom")

        # Skip
        self.ax_skip_frame = tk.Frame(self.container, bg=BG)
        self.ax_skip_frame.pack(fill="x", side="bottom", pady=(8, 0))
        self.ax_attempt_count = 0

        # Start checking
        threading.Thread(target=self._ax_initial_check, daemon=True).start()

    def _ax_initial_check(self):
        result = verify_accessibility()
        self.root.after(0, lambda: self._ax_handle_result(result))

    def _ax_handle_result(self, ok: bool):
        if ok:
            self.ax_verified = True
            self.ax_status_icon.configure(text="\u2713", fg=GREEN)
            self.ax_status_text.configure(
                text="Accessibility is enabled.", fg=FG)
            self.ax_continue_btn.configure(
                state="normal", bg=FG, fg=BG, cursor="hand2")
        else:
            self.ax_attempt_count += 1
            self.ax_status_icon.configure(text="\u25cb", fg=RED)
            self.ax_status_text.configure(
                text="Accessibility not enabled yet.", fg=RED)
            if self.ax_attempt_count == 1:
                open_accessibility_settings()
            if self.ax_attempt_count >= 3:
                for w in self.ax_skip_frame.winfo_children():
                    w.destroy()
                tk.Button(self.ax_skip_frame,
                          text="Skip for now \u2014 I'll fix this later",
                          command=self.show_permission_summary,
                          bg=BG, fg="#666666", font=FONT_SMALL,
                          relief="flat", bd=0, cursor="hand2",
                          activebackground=BG).pack(anchor="center")
                self.ax_skip_frame.pack(fill="x", side="bottom", pady=(8, 0))
            self._ax_schedule_autopoll()

    def _ax_schedule_autopoll(self):
        if self.ax_verified:
            return

        def _poll():
            if verify_accessibility():
                self.root.after(0, lambda: self._ax_handle_result(True))
            else:
                self.root.after(3000, self._ax_schedule_autopoll)

        threading.Thread(target=_poll, daemon=True).start()

    def _ax_recheck(self):
        self.ax_status_icon.configure(text="\u25cb", fg=GREY)
        self.ax_status_text.configure(text="Checking\u2026", fg=GREY)

        def _check():
            ok = verify_accessibility()
            self.root.after(0, lambda: self._ax_handle_result(ok))

        threading.Thread(target=_check, daemon=True).start()

    def _ax_copy_path(self):
        copy_to_clipboard(PYTHON_REAL)
        self.ax_copy_btn.configure(text="Copied \u2713")
        self.root.after(2000, lambda: self.ax_copy_btn.configure(
            text="Copy Path to Clipboard"))

    # --- Screen 3c: Permission Summary ---

    def show_permission_summary(self):
        self.clear()

        spacer = tk.Frame(self.container, bg=BG, height=60)
        spacer.pack()

        tk.Label(self.container, text="Protection is now active.",
                 font=("SF Pro Display", 22, "bold"),
                 fg=FG, bg=BG).pack(pady=(0, 24))

        # Permission checklist
        perms = [
            ("Screen Recording",
             self.screen_verified,
             "Detects harmful visual content"),
            ("Accessibility",
             getattr(self, "ax_verified", False),
             "Reads browser tab content"),
        ]
        for name, ok, desc in perms:
            row = tk.Frame(self.container, bg=BG)
            row.pack(fill="x", pady=4)
            icon = "\u2713" if ok else "\u2717"
            color = GREEN if ok else RED
            tk.Label(row, text=icon, font=("SF Pro Display", 16),
                     fg=color, bg=BG, width=2).pack(side="left")
            col = tk.Frame(row, bg=BG)
            col.pack(side="left")
            tk.Label(col, text=name, font=("SF Pro Display", 13, "bold"),
                     fg=FG, bg=BG).pack(anchor="w")
            tk.Label(col, text=desc, font=FONT_SMALL,
                     fg=GREY, bg=BG).pack(anchor="w")

        if not all(ok for _, ok, _ in perms):
            tk.Label(self.container,
                     text="Some permissions are missing.\n"
                          "Guardian will alert your partners if\n"
                          "screen access is unavailable.",
                     font=FONT_SMALL, fg=YELLOW, bg=BG,
                     justify="center").pack(pady=(12, 0))

        # Partners list
        partners = getattr(self, "partners", [])
        if partners:
            tk.Label(self.container,
                     text="Your partners will be notified if\n"
                          "protection is ever removed:",
                     font=FONT_SUB, fg=GREY, bg=BG,
                     justify="center").pack(pady=(24, 8))
            for p in partners:
                name = (p.get("name", "") or p.get("email", "") or "Partner")
                tk.Label(self.container, text=f"\u2022  {name}",
                         font=FONT, fg=FG, bg=BG).pack(anchor="w", padx=40)

        btn = self.make_button(self.container, "Continue to Install",
                               self.start_install)
        btn.pack(fill="x", ipady=4, pady=(30, 0))

    # --- Screen 4: Installing ---

    def start_install(self):
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
                "python_real_path": PYTHON_REAL,
                "screen_recording_verified": self.screen_verified,
                "accessibility_verified": getattr(self, "ax_verified", False),
                "sendgrid_api_key": sg_key,
                "telegram_bot_token": tg_token,
                "anthropic_api_key": anthropic_key,
            }
            if self.account_token:
                cfg["account_token"] = self.account_token
            if self.account_email:
                cfg["user_email"] = self.account_email
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

            self._update_status("Activating protection...", 85)
            import time
            time.sleep(1)

            self._update_status("Complete.", 100)
            time.sleep(0.5)
            self.root.after(0, self.show_complete)

        except Exception as e:
            self._update_status(f"Error: {e}", 0)

    # --- Screen 5: Complete ---

    def show_complete(self):
        self.clear()

        spacer = tk.Frame(self.container, bg=BG, height=120)
        spacer.pack()

        tk.Label(self.container, text="You are loved.",
                 font=FONT_TITLE, fg=FG, bg=BG).pack(pady=(0, 20))

        status_lines = "Protection is active.\nYour partner(s) have been notified.\nThe uninstall code has been sent to them."
        if not self.screen_verified:
            status_lines += (
                "\n\nScreen Recording was not verified.\n"
                "Guardian will alert your partner if screen\n"
                "access is missing when it starts."
            )

        tk.Label(self.container,
                 text=status_lines,
                 font=FONT_SUB, fg=GREY, bg=BG,
                 justify="center").pack(pady=(0, 50))

        btn = self.make_button(self.container, "Done",
                               self.root.destroy)
        btn.pack(fill="x", ipady=4)

    def run(self):
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Terminal fallback
# ---------------------------------------------------------------------------

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

    # Screen Recording verification (terminal version)
    print("\n  Verifying screen access...")
    trigger_tcc_prepopulation()
    import time
    time.sleep(1)
    sr_result = verify_screen_recording()
    sr_verified = sr_result == "yes"

    if sr_verified:
        print("  ✓ Screen Recording: working")
    else:
        copy_to_clipboard(PYTHON_REAL)
        print("")
        print(f"  Screen Recording needs to be enabled for:")
        print(f"  {PYTHON_REAL}")
        print(f"  (Path copied to clipboard)")
        print("")
        print(f"  Open System Settings → Screen Recording.")
        print(f"  Toggle Python ON, or click + and paste the path above.")
        open_screen_recording_settings()

        for attempt in range(1, 11):
            input(f"\n  Press Enter after enabling it...")
            sr_result = verify_screen_recording()
            if sr_result == "yes":
                sr_verified = True
                print("  ✓ Screen Recording: working")
                break
            elif sr_result == "wallpaper":
                print(f"  Almost — seeing wallpaper only. Make sure this exact path is enabled:")
                print(f"  {PYTHON_REAL}")
                copy_to_clipboard(PYTHON_REAL)
            else:
                print(f"  Not working yet. Make sure Python is toggled ON.")

            if attempt >= 5:
                skip = input("  Skip for now? (y/N): ").strip().lower()
                if skip == "y":
                    break

    # Generate code
    code = f"{secrets.randbelow(1000000):06d}"

    cfg = {
        "setup_complete": True,
        "partners": partners,
        "code_hash": hash_code(code),
        "installed_at": datetime.now().isoformat(),
        "guardian_path": str(Path.home() / "youareloved" / "guardian.py"),
        "python_real_path": PYTHON_REAL,
        "screen_recording_verified": sr_verified,
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
    if not sr_verified:
        print(f"\n  ⚠ Screen Recording was not verified.")
        print(f"  Guardian will run but may not detect visual content")
        print(f"  until Screen Recording is enabled for:")
        print(f"  {PYTHON_REAL}")
    input("\n  Press Enter to continue...")


if __name__ == "__main__":
    # CLI utility: resolve Telegram chat_ids after initial setup.
    # Usage:
    #   python3 ~/youareloved/setup.py --resolve-telegram [--telegram-token TOKEN] [--wait]
    if "--resolve-telegram" in sys.argv[1:]:
        token_override = ""
        wait = "--wait" in sys.argv[1:]
        if "--telegram-token" in sys.argv[1:]:
            try:
                token_override = sys.argv[sys.argv.index("--telegram-token") + 1]
            except Exception:
                token_override = ""

        cfg = {}
        if CONFIG_FILE.exists():
            try:
                cfg = json.loads(CONFIG_FILE.read_text())
            except Exception:
                cfg = {}

        token = (token_override or cfg.get("telegram_bot_token", "") or "").strip()
        partners = cfg.get("partners", []) or []

        print("\n=== Telegram Chat ID Resolution (setup.py) ===")
        if not token:
            print("Telegram bot token: not set")
            sys.exit(2)

        if wait and sys.stdin.isatty():
            print("Partners must send /start to the bot first.")
            input("Press Enter to fetch updates now...")

        chats = resolve_telegram_chats(token)
        changed = False
        resolved = 0
        unresolved = 0
        skipped = 0

        for p in partners:
            tg_raw = (p.get("telegram", "") or "").strip()
            tg_u = tg_raw.lower().lstrip("@").strip()
            if (p.get("telegram_chat_id", "") or "").strip():
                skipped += 1
                continue
            if not tg_u:
                skipped += 1
                continue
            cid = chats.get(tg_u, "")
            if cid:
                p["telegram_chat_id"] = cid
                resolved += 1
                changed = True
                print(f"  ✓ {tg_raw or '@'+tg_u} → {cid}")
            else:
                unresolved += 1
                print(f"  ⚠ {tg_raw or '@'+tg_u} (not found in updates)")

        if changed:
            cfg["partners"] = partners
            if token_override and token_override.strip() and token_override.strip() != cfg.get("telegram_bot_token", ""):
                cfg["telegram_bot_token"] = token_override.strip()
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
            print("Config updated: yes")
        else:
            print("Config updated: no")

        print(f"Resolved: {resolved} | Unresolved: {unresolved} | Skipped: {skipped}")
        sys.exit(0)

    # Filter out --python-real from argv before tkinter sees it
    filtered_argv = []
    skip_next = False
    for arg in sys.argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if arg == "--python-real":
            skip_next = True
            continue
        filtered_argv.append(arg)
    sys.argv = [sys.argv[0]] + filtered_argv

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
