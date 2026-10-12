# Macro Studio

**English** · [Русский](README.ru.md)

A Windows macro recorder that can also **react to what's on screen**. Record your mouse clicks, movements and keystrokes, then replay them on demand, or automatically when a chosen image shows up on screen.

**[⬇ Download MacroStudio.exe](https://github.com/araluga/macro-studio/releases/latest)**: one file for Windows 10/11, nothing to install.

![Macro Studio](docs/screenshot.png)

## Features

- **Record and replay** mouse clicks, movement, scrolling and (optionally) the keyboard.
- **Repeats, speed, delay:** loop a macro N times or forever, at 0.25×–5× speed, or replay only the clicks without the mouse path.
- **Image triggers:** give a macro a picture (paste, drag & drop, open a file, or snip it straight from the screen). In monitoring mode, the macro runs as soon as that picture appears with a similarity above your threshold.
- **Clicks follow the image:** if the picture shows up somewhere else on screen, the recorded clicks are shifted to match.
- **Search area:** look for the picture on the whole screen (all monitors) or only in a selected region.
- **Transparency-aware matching:** transparent pixels (e.g. a sticker's background) are ignored.
- **Multi-scale search:** optionally finds the picture even when it's enlarged or shrunk.
- **Live feedback:** a similarity meter, a "Check" button that outlines the match on screen, and a floating status pill. The pill lets clicks pass through and is excluded from screenshots, so it never confuses the search.
- **Several macros at once:** monitoring watches every macro that has a trigger enabled. A cooldown keeps a macro from firing repeatedly on the same image.
- **English and Russian UI:** switch the language in the sidebar.
- Everything is saved automatically. Macros can be exported and imported as JSON.

## Example: auto-delete a Telegram sticker

1. Create a macro called "Delete sticker".
2. Copy the sticker (right-click → Copy, or `Win+Shift+S`) and press **Ctrl+V** in the app. You can also drop an image file or click **From screen** and select the sticker.
3. Choose where to look: **Full screen** or a **Region**, and set the similarity threshold (e.g. 85%). Press **Check** to see the current similarity and where the match is.
4. With the sticker visible, record the actions: **F9** → right-click the sticker → Delete → **F9**. When recording starts, the app remembers where the sticker was.
5. Press **F11** to start monitoring. Whenever the sticker appears, the macro deletes it, even if it's in a different place.

## Hotkeys (global)

| Key | Action |
|-----|--------|
| `F9`  | Start / stop recording |
| `F10` | Play the selected macro |
| `F11` | Start / stop monitoring |
| `F12` | Emergency stop |

## Download

Grab **`MacroStudio.exe`** from the [latest release](https://github.com/araluga/macro-studio/releases/latest). It's a single file with nothing to install. Just run it (Windows 10/11, 64-bit).

- Windows SmartScreen may warn about an unknown publisher because the exe isn't code-signed. Click **More info → Run anyway**.
- Some antivirus tools flag any app that listens to the keyboard and mouse. That's how hotkeys and recording work. The source is all here, so you can also run it from source or build it yourself (see below).
- The exe keeps your macros and settings in `%APPDATA%\MacroStudio`.

## Run from source

Requires **Windows 10/11** and **Python 3.10+**.

```bash
git clone https://github.com/araluga/macro-studio.git
cd macro-studio
pip install -r requirements.txt
python macro_app.py
```

Or just double-click **`run.bat`**. It installs the dependencies on first launch and starts the app without a console window.

### Build the exe

```bash
build.bat
```

This creates `dist\MacroStudio.exe` with [PyInstaller](https://pyinstaller.org/) (see `MacroStudio.spec`).

## How it works

| File | Purpose |
|------|---------|
| `macro_app.py` | User interface (PySide6 / Qt) |
| `core.py` | Recording and playback ([pynput](https://github.com/moses-palmer/pynput)), screen capture ([mss](https://github.com/BoboTiG/python-mss)), template matching ([OpenCV](https://opencv.org/) `TM_CCOEFF_NORMED`) |
| `i18n.py` | English / Russian translations |

Macros are stored in `macros.json` and app settings in `settings.json`: next to the script when run from source, in `%APPDATA%\MacroStudio` for the exe.

## Notes

- Use macros responsibly: automating some games or services may break their terms of use.
- Apps running as administrator can only be controlled when Macro Studio also runs as administrator.

## License

[MIT](LICENSE)
