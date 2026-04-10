# Keep Awake

A lightweight Windows system tray utility that prevents your computer from going to sleep when you step away.

---

## What's New in v1.1

- **Schedule dialog** — right-click the tray icon and choose **Schedule…** to configure when the app is active
- **Settings persistence** — your chosen schedule is saved automatically and restored on next launch
- **Grey icon** — shown when the app is running but the current schedule has it inactive

---

## How It Works

| Tray Icon | Meaning |
|-----------|---------|
| 🟢 Green | No user activity — actively blocking sleep |
| 🔴 Red   | Mouse or keyboard activity detected — user is present |
| ⚫ Grey  | Schedule is currently inactive — sleep allowed |

The app uses the Windows `SetThreadExecutionState` API to block both system sleep and display shutoff. It monitors `GetLastInputInfo` every second to detect whether the user is active. If no input is detected for **5 seconds**, the icon turns green and sleep prevention kicks in. When activity resumes, the icon turns red.

To exit, **right-click the tray icon** and select **Quit**. Normal sleep behaviour is restored immediately on exit.

---

## Schedule Options

Right-click the tray icon and choose **Schedule…** to open the schedule dialog.

| Mode | Description |
|------|-------------|
| **Always Active** *(default)* | Keeps awake continuously while running |
| **Active During Time Window** | Only active between two times of day (e.g. 09:00–18:00) |
| **Active on Specific Days** | Choose weekdays/weekend days, with an optional time window |
| **One-Time Timer** | Stay awake for a set number of hours or minutes, then stop |

Settings are saved to `%APPDATA%\KeepAwake\settings.json` and loaded automatically on next launch.

---

## Files

```
keep_awake.py           # Source code (single file)
keep_awake.spec         # PyInstaller build spec
dist\keep_awake.exe     # Standalone Windows executable (no install needed)
```

---

## Running

### Option A — Executable (recommended)
Just double-click:
```
dist\keep_awake.exe
```
No Python or pip required. Works on any Windows 10/11 machine.

### Option B — Python source
1. Install dependencies (one time only):
   ```
   pip install pystray pillow
   ```
2. Run:
   ```
   python keep_awake.py
   ```
   Requires Python 3.10+.

---

## Building the EXE Yourself

Using the included spec file:
```
pip install pyinstaller pystray pillow
pyinstaller keep_awake.spec
```

Or from scratch:
```
pyinstaller --onefile --noconsole --name keep_awake keep_awake.py
```

Output lands in `dist\keep_awake.exe`.

---

## Configuration

The idle threshold (how long before the icon turns green) can be adjusted in `keep_awake.py`:

```python
IDLE_THRESHOLD_SECONDS = 5   # seconds of inactivity before icon turns green
```

All other settings (schedule, time windows, active days) are configured through the **Schedule…** dialog at runtime.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| [pystray](https://github.com/moses-palmer/pystray) | System tray icon |
| [Pillow](https://python-pillow.org/) | Drawing the coloured circle icons |
| tkinter (built-in) | Schedule dialog UI |
| ctypes (built-in) | Windows API calls (sleep prevention, idle detection) |
