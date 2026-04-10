# Keep Awake v1.1

## What's New

### Schedule Dialog
Right-click the system tray icon and choose **Schedule…** to configure when Keep Awake should be active. A new dialog lets you pick from four modes:

- **Always Active** *(default)* — runs continuously, same behaviour as v1.0
- **Active During Time Window** — only keeps awake between a start and end time (e.g. 09:00–18:00)
- **Active on Specific Days** — choose weekdays or weekend days, with an optional time window
- **One-Time Timer** — stay awake for a fixed number of hours or minutes, then automatically stop

### Persistent Settings
Your chosen schedule is saved to `%APPDATA%\KeepAwake\settings.json` and restored automatically the next time the app launches.

### Grey Tray Icon
A new grey icon state indicates the app is running but the current schedule has sleep prevention paused.

### About Button
The Schedule dialog includes an About button (placeholder for a future release).

### Version Number
Version is now shown in the Schedule dialog status bar (`v1.1`).

---

## Tray Icon Reference

| Icon | Meaning |
|------|---------|
| 🟢 Green | Actively preventing sleep — no user activity detected |
| 🔴 Red | User is active (mouse/keyboard input detected) |
| ⚫ Grey | Schedule is currently inactive — sleep is allowed |

---

## Bug Fixes

- Fixed threading issue where the Schedule dialog would not open (pystray and tkinter now run on separate threads correctly)

---

## Installation

Download `keep_awake.exe` below — no Python or install required. Runs on Windows 10 and Windows 11.

To build from source:
```
pip install pystray pillow pyinstaller
pyinstaller keep_awake.spec
```
