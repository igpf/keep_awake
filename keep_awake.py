"""
Keep Awake v1.1 - Prevents Windows from sleeping, with a system tray icon.

Install dependencies once:
    pip install pystray pillow

Green icon = no user activity detected, actively preventing sleep
Red icon   = user activity detected (mouse/keyboard in use)

Right-click the tray icon and choose Schedule... to configure a schedule,
or Quit to exit.
"""

import ctypes
import json
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from PIL import Image, ImageDraw
import pystray

APP_VERSION = "v1.1"

# Windows API flags for SetThreadExecutionState
ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# Seconds of idle time before we consider the user "inactive"
IDLE_THRESHOLD_SECONDS = 5

# Config file location: %APPDATA%\KeepAwake\settings.json
CONFIG_DIR  = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KeepAwake")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

# Schedule modes
MODE_ALWAYS = "always"
MODE_WINDOW = "window"
MODE_DAYS   = "days"
MODE_TIMER  = "timer"

DEFAULT_SETTINGS = {
    "mode": MODE_ALWAYS,
    "window_start": "09:00",
    "window_end":   "18:00",
    "days": [0, 1, 2, 3, 4],      # Mon–Fri (0=Mon, 6=Sun)
    "days_start": "09:00",
    "days_end":   "18:00",
    "timer_value": 2,
    "timer_unit": "hours",         # "hours" or "minutes"
}


# ──────────────────────────────────────────────
# Windows API helpers
# ──────────────────────────────────────────────

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds():
    """Return how many seconds have passed since the last user input."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    elapsed_ms = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return elapsed_ms / 1000.0


def prevent_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )


def restore_sleep():
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def make_icon(color: tuple) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color)
    return img


GREEN = (0, 200, 80)
RED   = (220, 40, 40)
GREY  = (130, 130, 130)


# ──────────────────────────────────────────────
# Settings persistence
# ──────────────────────────────────────────────

def load_settings() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        # Fill in any missing keys with defaults
        for k, v in DEFAULT_SETTINGS.items():
            data.setdefault(k, v)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ──────────────────────────────────────────────
# Schedule evaluation
# ──────────────────────────────────────────────

def _parse_hm(s: str):
    """Parse 'HH:MM' into (hour, minute)."""
    h, m = s.split(":")
    return int(h), int(m)


def _time_in_window(start_str: str, end_str: str, now: datetime) -> bool:
    sh, sm = _parse_hm(start_str)
    eh, em = _parse_hm(end_str)
    start = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
    end   = now.replace(hour=eh, minute=em, second=0, microsecond=0)
    return start <= now < end


def should_be_active(settings: dict, timer_end: list) -> bool:
    """
    Returns True if Keep Awake should currently be preventing sleep.
    `timer_end` is a mutable list [datetime|None] so the monitor thread
    can read the shared timer expiry value.
    """
    mode = settings.get("mode", MODE_ALWAYS)

    if mode == MODE_ALWAYS:
        return True

    now = datetime.now()

    if mode == MODE_WINDOW:
        return _time_in_window(
            settings.get("window_start", "09:00"),
            settings.get("window_end",   "18:00"),
            now,
        )

    if mode == MODE_DAYS:
        today = now.weekday()  # 0=Mon
        active_days = settings.get("days", [0, 1, 2, 3, 4])
        if today not in active_days:
            return False
        return _time_in_window(
            settings.get("days_start", "09:00"),
            settings.get("days_end",   "18:00"),
            now,
        )

    if mode == MODE_TIMER:
        end = timer_end[0]
        if end is None:
            return False
        return now < end

    return True


# ──────────────────────────────────────────────
# Schedule dialog (tkinter)
# ──────────────────────────────────────────────

class ScheduleDialog:
    """
    Modal-style Toplevel window for choosing the Keep Awake schedule.
    Calls `on_apply(new_settings)` when the user clicks Apply.
    """

    DAY_LABELS  = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

    def __init__(self, parent_root: tk.Tk, current_settings: dict, on_apply):
        self._on_apply = on_apply
        self._settings = dict(current_settings)

        self._win = tk.Toplevel(parent_root)
        self._win.title(f"Keep Awake {APP_VERSION} — Schedule")
        self._win.resizable(False, False)
        self._win.grab_set()          # modal
        self._win.focus_force()

        # Centre on screen
        self._win.update_idletasks()
        w, h = 430, 440
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        self._win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        self._build_ui()
        self._load_values()

    # ── UI construction ──────────────────────────────────

    def _build_ui(self):
        win = self._win
        pad = {"padx": 14, "pady": 6}

        # Intro label
        intro = tk.Label(
            win,
            text="Choose when Keep Awake should be active.\n"
                 "Settings are saved automatically between sessions.",
            justify="left",
            wraplength=400,
            fg="#444444",
        )
        intro.pack(anchor="w", padx=14, pady=(12, 4))

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=14, pady=4)

        # ── Radio: Always Active ──
        self._mode_var = tk.StringVar(value=MODE_ALWAYS)

        self._rb_always = ttk.Radiobutton(
            win, text="🟢  Always Active  (default)",
            variable=self._mode_var, value=MODE_ALWAYS,
            command=self._on_mode_change,
        )
        self._rb_always.pack(anchor="w", **pad)

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=14)

        # ── Radio: Time Window ──
        self._rb_window = ttk.Radiobutton(
            win, text="🕐  Active During Time Window",
            variable=self._mode_var, value=MODE_WINDOW,
            command=self._on_mode_change,
        )
        self._rb_window.pack(anchor="w", **pad)

        self._frame_window = tk.Frame(win, padx=30)
        tk.Label(self._frame_window, text="From").pack(side="left")
        self._window_start = tk.Entry(self._frame_window, width=7)
        self._window_start.pack(side="left", padx=4)
        tk.Label(self._frame_window, text="to").pack(side="left")
        self._window_end = tk.Entry(self._frame_window, width=7)
        self._window_end.pack(side="left", padx=4)
        tk.Label(self._frame_window, text="(HH:MM)", fg="#888").pack(side="left")

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=14)

        # ── Radio: Specific Days ──
        self._rb_days = ttk.Radiobutton(
            win, text="📅  Active on Specific Days",
            variable=self._mode_var, value=MODE_DAYS,
            command=self._on_mode_change,
        )
        self._rb_days.pack(anchor="w", **pad)

        self._frame_days = tk.Frame(win, padx=30)
        days_row = tk.Frame(self._frame_days)
        days_row.pack(anchor="w")
        self._day_vars = []
        for label in self.DAY_LABELS:
            var = tk.BooleanVar(value=False)
            cb  = tk.Checkbutton(days_row, text=label, variable=var, indicatoron=False,
                                  width=3, relief="raised", padx=2)
            cb.pack(side="left", padx=2)
            self._day_vars.append((var, cb))

        time_row = tk.Frame(self._frame_days)
        time_row.pack(anchor="w", pady=(6, 0))
        tk.Label(time_row, text="Hours:").pack(side="left")
        self._days_start = tk.Entry(time_row, width=7)
        self._days_start.pack(side="left", padx=4)
        tk.Label(time_row, text="–").pack(side="left")
        self._days_end = tk.Entry(time_row, width=7)
        self._days_end.pack(side="left", padx=4)
        tk.Label(time_row, text="(HH:MM)", fg="#888").pack(side="left")

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=14)

        # ── Radio: One-Time Timer ──
        self._rb_timer = ttk.Radiobutton(
            win, text="⏱️  One-Time Timer",
            variable=self._mode_var, value=MODE_TIMER,
            command=self._on_mode_change,
        )
        self._rb_timer.pack(anchor="w", **pad)

        self._frame_timer = tk.Frame(win, padx=30)
        tk.Label(self._frame_timer, text="Keep awake for").pack(side="left")
        self._timer_val = tk.Spinbox(self._frame_timer, from_=1, to=999, width=5)
        self._timer_val.pack(side="left", padx=4)
        self._timer_unit = ttk.Combobox(
            self._frame_timer, values=["hours", "minutes"], width=8, state="readonly"
        )
        self._timer_unit.pack(side="left", padx=4)
        tk.Label(self._frame_timer, text=", then stop").pack(side="left")

        ttk.Separator(win, orient="horizontal").pack(fill="x", padx=14, pady=(8, 0))

        # ── Footer ──
        footer = tk.Frame(win, bg="#e4e4e4", pady=8)
        footer.pack(fill="x", side="bottom")

        # About button (left side)
        about_btn = ttk.Button(footer, text="About", command=self._on_about, width=8)
        about_btn.pack(side="left", padx=(14, 0))

        # Cancel / Apply (right side)
        apply_btn = ttk.Button(footer, text="Apply", command=self._on_apply_click, width=8)
        apply_btn.pack(side="right", padx=(0, 14))
        cancel_btn = ttk.Button(footer, text="Cancel", command=self._win.destroy, width=8)
        cancel_btn.pack(side="right", padx=(0, 6))

        # Status bar
        self._status_var = tk.StringVar()
        status_bar = tk.Label(
            win, textvariable=self._status_var,
            anchor="w", bg="#dde8ff", fg="#444", font=("Segoe UI", 8),
            relief="sunken", bd=1,
        )
        status_bar.pack(fill="x", side="bottom", padx=0, pady=0)

        self._update_status()

    # ── Value loading ──────────────────────────────────

    def _load_values(self):
        s = self._settings
        self._mode_var.set(s.get("mode", MODE_ALWAYS))

        self._window_start.delete(0, "end")
        self._window_start.insert(0, s.get("window_start", "09:00"))
        self._window_end.delete(0, "end")
        self._window_end.insert(0, s.get("window_end", "18:00"))

        active_days = s.get("days", [0, 1, 2, 3, 4])
        for i, (var, _) in enumerate(self._day_vars):
            var.set(i in active_days)

        self._days_start.delete(0, "end")
        self._days_start.insert(0, s.get("days_start", "09:00"))
        self._days_end.delete(0, "end")
        self._days_end.insert(0, s.get("days_end", "18:00"))

        self._timer_val.delete(0, "end")
        self._timer_val.insert(0, str(s.get("timer_value", 2)))
        self._timer_unit.set(s.get("timer_unit", "hours"))

        self._on_mode_change()

    # ── Mode change ──────────────────────────────────

    def _on_mode_change(self):
        mode = self._mode_var.get()
        frames = {
            MODE_WINDOW: self._frame_window,
            MODE_DAYS:   self._frame_days,
            MODE_TIMER:  self._frame_timer,
        }
        for m, frame in frames.items():
            if m == mode:
                frame.pack(anchor="w", padx=14, pady=(0, 8))
            else:
                frame.pack_forget()
        self._update_status()

    def _update_status(self):
        mode = self._mode_var.get()
        labels = {
            MODE_ALWAYS: "Always Active — no schedule restrictions",
            MODE_WINDOW: "Active during configured time window",
            MODE_DAYS:   "Active on selected days and hours",
            MODE_TIMER:  "One-time timer — stops after duration",
        }
        self._status_var.set(f"  {APP_VERSION}  ·  {labels.get(mode, '')}")

    # ── Button callbacks ──────────────────────────────

    def _on_about(self):
        # Placeholder — to be implemented later
        pass

    def _on_apply_click(self):
        mode = self._mode_var.get()
        new_settings = dict(self._settings)
        new_settings["mode"] = mode

        if mode == MODE_WINDOW:
            new_settings["window_start"] = self._window_start.get().strip()
            new_settings["window_end"]   = self._window_end.get().strip()

        elif mode == MODE_DAYS:
            new_settings["days"]       = [i for i, (v, _) in enumerate(self._day_vars) if v.get()]
            new_settings["days_start"] = self._days_start.get().strip()
            new_settings["days_end"]   = self._days_end.get().strip()

        elif mode == MODE_TIMER:
            try:
                new_settings["timer_value"] = int(self._timer_val.get())
            except ValueError:
                new_settings["timer_value"] = 2
            new_settings["timer_unit"] = self._timer_unit.get()

        save_settings(new_settings)
        self._on_apply(new_settings)
        self._win.destroy()


# ──────────────────────────────────────────────
# Main application
# ──────────────────────────────────────────────

class KeepAwakeApp:
    def __init__(self):
        self._running      = True
        self._user_active  = None       # force first update
        self._tray: pystray.Icon | None = None
        self._settings     = load_settings()
        self._timer_end    = [None]     # [datetime | None] — shared with monitor thread

        # Hidden Tk root for dialogs
        self._root = tk.Tk()
        self._root.withdraw()

    # ── Background monitor ──────────────────────────────

    def _monitor(self):
        while self._running:
            active_period = should_be_active(self._settings, self._timer_end)
            idle          = get_idle_seconds()
            user_active   = idle < IDLE_THRESHOLD_SECONDS

            if active_period:
                prevent_sleep()
                new_color = RED if user_active else GREEN
                new_title = (
                    "Keep Awake — user active"
                    if user_active
                    else "Keep Awake — preventing sleep"
                )
            else:
                restore_sleep()
                new_color = GREY
                new_title = "Keep Awake — schedule inactive"

            if user_active != self._user_active or not active_period:
                self._user_active = user_active
                if self._tray is not None:
                    self._tray.icon  = make_icon(new_color)
                    self._tray.title = new_title

            time.sleep(1)

    # ── Tray callbacks ──────────────────────────────────

    def _open_schedule(self, icon: pystray.Icon, _item):
        """
        Called from pystray's thread — marshal dialog creation
        onto tkinter's main thread via after().
        """
        self._root.after(0, self._show_schedule_dialog)

    def _show_schedule_dialog(self):
        """Must be called on the tkinter main thread."""
        def _on_apply(new_settings):
            self._settings = new_settings
            if new_settings.get("mode") == MODE_TIMER:
                val  = new_settings.get("timer_value", 2)
                unit = new_settings.get("timer_unit", "hours")
                secs = val * 3600 if unit == "hours" else val * 60
                self._timer_end[0] = datetime.fromtimestamp(time.time() + secs)
            else:
                self._timer_end[0] = None

        ScheduleDialog(self._root, self._settings, _on_apply)

    def _quit(self, icon: pystray.Icon, _item):
        self._running = False
        restore_sleep()
        icon.stop()
        self._root.after(0, self._root.quit)  # quit tkinter from its own thread

    # ── Entry point ─────────────────────────────────────

    def run(self):
        # Start background threads
        threading.Thread(target=self._monitor, daemon=True).start()

        menu = pystray.Menu(
            pystray.MenuItem("Keep Awake", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Schedule…", self._open_schedule),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

        self._tray = pystray.Icon(
            name="KeepAwake",
            icon=make_icon(GREEN),
            title="Keep Awake — starting…",
            menu=menu,
        )

        # pystray runs in a background thread; tkinter owns the main thread
        threading.Thread(target=self._tray.run, daemon=True).start()
        self._root.mainloop()  # blocks main thread — required for tkinter dialogs


if __name__ == "__main__":
    KeepAwakeApp().run()
