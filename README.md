# Keep Awake

A lightweight Windows system tray utility that prevents your computer from going to sleep when you step away.

---

## How It Works

| Tray Icon | Meaning |
|-----------|---------|
| 🟢 Green | No user activity detected — actively blocking sleep |
| 🔴 Red   | Mouse or keyboard activity detected — user is present |

The app uses the Windows `SetThreadExecutionState` API to block both system sleep and display shutoff. It monitors `GetLastInputInfo` every second to detect whether the user is active. If no input is detected for **5 seconds**, the icon turns green and sleep prevention kicks in. When activity resumes, the icon turns red.

To exit, **right-click the tray icon** and select **Quit**. Normal sleep behaviour is restored immediately on exit.

---

## Files

```
keep_awake.py       # Source code (single file)
dist/keep_awake.exe # Standalone Windows executable (no install needed)
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

```
pip install pyinstaller pystray pillow
pyinstaller --onefile --noconsole --name keep_awake keep_awake.py
```
Output lands in `dist\keep_awake.exe`.

---

## Configuration

Open `keep_awake.py` and adjust the constant near the top:

```python
IDLE_THRESHOLD_SECONDS = 5   # seconds of inactivity before icon turns green
```

Rebuild the exe after any changes.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| [pystray](https://github.com/moses-palmer/pystray) | System tray icon |
| [Pillow](https://python-pillow.org/) | Drawing the coloured circle icons |
| ctypes (built-in) | Windows API calls (sleep prevention, idle detection) |
