# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec: python -m PyInstaller --noconfirm --clean MacroStudio.spec

a = Analysis(
    ['macro_app.py'],
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32'],
    excludes=['tkinter'],
)


def keep(entry):
    """Drop large files the app never uses."""
    name = entry[0].replace('\\', '/').lower()
    if 'opencv_videoio_ffmpeg' in name:   # OpenCV video I/O
        return False
    if name.endswith('opengl32sw.dll'):    # Qt software OpenGL fallback
        return False
    if name.endswith('.qm'):               # Qt translations: keep only Russian
        base = name.rsplit('/', 1)[-1]
        return base in ('qtbase_ru.qm', 'qt_ru.qm')
    return True


a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MacroStudio',
    console=False,
    upx=False,
    icon='assets/icon.ico',
    version='assets/version_info.txt',
)
