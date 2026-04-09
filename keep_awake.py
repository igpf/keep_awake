"""
Keep Awake - Prevents Windows from sleeping, with a system tray icon.

Install dependencies once:
    pip install pystray pillow

Green icon = no user activity detected, actively preventing sleep
Red icon   = user activity detected (mouse/keyboard in use)

Right-click the tray icon and choose Quit to exit.
"""

import ctypes
import threading
import time
from PIL import Image, ImageDraw
import pystray

# Windows API flags for SetThreadExecutionState
ES_CONTINUOUS        = 0x80000000
ES_SYSTEM_REQUIRED   = 0x00000001
ES_DISPLAY_REQUIRED  = 0x00000002

# Seconds of idle time before we consider the user "inactive"
IDLE_THRESHOLD_SECONDS = 5


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
    """Tell Windows not to sleep or turn off the display."""
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )


def restore_sleep():
    """Re-enable normal Windows sleep behaviour."""
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def make_icon(color: tuple) -> Image.Image:
    """Create a 64×64 circle icon in the given RGB colour."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color)
    return img


GREEN = (0, 200, 80)
RED   = (220, 40, 40)


class KeepAwakeApp:
    def __init__(self):
        self._running = True
        self._user_active = None  # force first update
        self._tray: pystray.Icon | None = None

    # ------------------------------------------------------------------
    # Background monitor
    # ------------------------------------------------------------------

    def _monitor(self):
        while self._running:
            idle = get_idle_seconds()
            active = idle < IDLE_THRESHOLD_SECONDS

            if active != self._user_active:
                self._user_active = active
                if self._tray is not None:
                    if active:
                        self._tray.icon  = make_icon(RED)
                        self._tray.title = "Keep Awake — user active"
                    else:
                        self._tray.icon  = make_icon(GREEN)
                        self._tray.title = "Keep Awake — preventing sleep"

            prevent_sleep()
            time.sleep(1)

    # ------------------------------------------------------------------
    # Tray callbacks
    # ------------------------------------------------------------------

    def _quit(self, icon: pystray.Icon, _item):
        self._running = False
        restore_sleep()
        icon.stop()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def run(self):
        thread = threading.Thread(target=self._monitor, daemon=True)
        thread.start()

        menu = pystray.Menu(
            pystray.MenuItem("Keep Awake", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

        self._tray = pystray.Icon(
            name="KeepAwake",
            icon=make_icon(GREEN),
            title="Keep Awake — starting…",
            menu=menu,
        )
        self._tray.run()


if __name__ == "__main__":
    KeepAwakeApp().run()
