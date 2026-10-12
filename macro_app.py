"""
Macro Studio — record mouse/keyboard actions and replay them when an image appears on screen.

Global hotkeys (configurable in the sidebar):
    F9  — start / stop recording
    F10 — play the selected macro
    F11 — start / stop monitoring (image triggers)
    F12 — emergency stop
Fallback stops: the tray icon and moving the mouse to the top-left screen corner.
"""

import copy
import ctypes
import ctypes.wintypes
import json
import os
import shutil
import sys
import threading
import time

from PIL import Image
from PySide6.QtCore import (QLibraryInfo, QLocale, QObject, QRect, QRectF, QSize, Qt, QTimer, QTranslator,
                            QVariantAnimation, Signal)
from PySide6.QtGui import (QAction, QColor, QFont, QFontMetrics, QGuiApplication, QIcon, QImage,
                           QLinearGradient, QPainter, QPainterPath, QPen, QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QButtonGroup,
                               QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMenu, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSystemTrayIcon,
                               QSizePolicy, QSlider, QSpinBox, QStyle, QStyledItemDelegate,
                               QVBoxLayout, QWidget)
from pynput import keyboard

import core
import i18n
from i18n import count, tr

__version__ = "1.1.0"

if getattr(sys, "frozen", False):
    # packaged .exe: the bundle is unpacked to a temp folder, so keep user data in %APPDATA%
    APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "MacroStudio")
    os.makedirs(APP_DIR, exist_ok=True)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "macros.json")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

ACCENT = "#7c5cff"
ACCENT2 = "#4f8bff"
GREEN = "#34d399"
RED = "#ff4d6d"
ORANGE = "#f59e0b"
MUTED = "#8b90a0"

GRAD = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT2})"
GRAD_HOVER = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8d72ff, stop:1 #6399ff)"

STYLE = f"""
* {{ font-family: "Segoe UI", "Segoe UI Symbol", "Segoe UI Emoji"; font-size: 10pt; color: #e6e8ef; }}
QMainWindow, #root {{ background: #0e1016; }}
#sidebar {{ background: #12141c; border-right: 1px solid #1d2130; }}
#appTitle {{ font-size: 14pt; font-weight: 700; }}
#appSub, #muted {{ color: {MUTED}; }}
#hint {{ color: #6f7486; font-size: 9pt; }}
#section {{ color: #6f7486; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }}
#card {{ background: #161924; border: 1px solid #222736; border-radius: 16px; }}
#cardTitle {{ font-size: 11.5pt; font-weight: 600; }}
#heading {{ font-size: 19pt; font-weight: 700; background: transparent; border: none;
            border-bottom: 2px solid transparent; padding: 0; }}
#heading:focus {{ border-bottom: 2px solid {ACCENT}; }}
#chip {{ background: #1b1f2c; border: 1px solid #252a3a; border-radius: 10px;
         padding: 3px 10px; color: #aab0c2; font-size: 9pt; }}
QPushButton#kbd {{ background: #1b1f2c; border: 1px solid #2c3246; border-bottom: 2px solid #2c3246;
                   border-radius: 6px; padding: 1px 7px; font-family: Consolas; font-size: 9pt; color: #cfd3e0;
                   min-width: 70px; }}
QPushButton#kbd:hover {{ border-color: {ACCENT}; color: white; }}
QPushButton#kbd::menu-indicator {{ image: none; width: 0; }}
#regionLbl {{ color: #aab0c2; font-size: 9pt; }}
#bigValue {{ font-size: 15pt; font-weight: 700; color: #ffffff; }}

QListWidget {{ background: transparent; border: none; outline: 0; }}

QPushButton {{ background: #1e2230; border: 1px solid #2a3042; border-radius: 10px;
               padding: 8px 14px; color: #dfe2ec; }}
QPushButton:hover {{ background: #252a3a; border-color: #363d55; }}
QPushButton:pressed {{ background: #1a1d29; }}
QPushButton:disabled {{ color: #565b6b; background: #171a24; border-color: #20242f; }}
QPushButton#primary, QPushButton#watch {{ background: {GRAD}; border: none; color: white; font-weight: 600; }}
QPushButton#primary:hover, QPushButton#watch:hover {{ background: {GRAD_HOVER}; }}
QPushButton#primary:disabled, QPushButton#watch:disabled {{ background: #23263a; color: #626779; }}
QPushButton#watch[active="true"] {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #22c3a6); }}
QPushButton#record {{ background: #2a1520; border: 1px solid #5a2234; color: #ff8096; font-weight: 600; }}
QPushButton#record:hover {{ background: #351a28; border-color: #7a2b44; }}
QPushButton#record:disabled {{ background: #1c1519; border-color: #2b1d23; color: #6b4a53; }}
QPushButton#record[active="true"] {{ background: {RED}; border: none; color: white; }}
QPushButton#ghost {{ background: transparent; border: 1px solid #2a3042; }}
QPushButton#ghost:hover {{ background: #1c2030; border-color: #3a4160; }}
QPushButton#icon {{ background: transparent; border: none; padding: 2px 8px; color: {MUTED}; font-size: 13pt; }}
QPushButton#icon:hover {{ background: #1c2030; color: white; }}
QPushButton#icon::menu-indicator {{ image: none; width: 0; }}
#segBox {{ background: #10131b; border: 1px solid #232838; border-radius: 10px; }}
QPushButton#seg {{ background: transparent; border: none; border-radius: 8px; padding: 6px 14px; color: {MUTED}; }}
QPushButton#seg:hover {{ color: white; }}
QPushButton#seg:checked {{ background: #2a2f48; color: white; }}

QSpinBox, QDoubleSpinBox {{ background: #10131b; border: 1px solid #262b3a; border-radius: 8px;
                            padding: 6px 10px; min-width: 72px; selection-background-color: {ACCENT}; }}
QSpinBox:hover, QDoubleSpinBox:hover {{ border-color: #343a50; }}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button
    {{ width: 0; border: none; subcontrol-origin: border; }}

QSlider {{ min-height: 22px; }}
QSlider::groove:horizontal {{ height: 6px; background: #262b3a; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {GRAD}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: white; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }}
QSlider::handle:horizontal:hover {{ background: #dcd6ff; }}

QPlainTextEdit#log {{ background: #0f1118; border: 1px solid #1d2130; border-radius: 10px;
                      font-family: Consolas; font-size: 9pt; color: #a9aec0; padding: 6px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2a2f3d; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3a4054; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}
QMenu {{ background: #1a1d28; border: 1px solid #2a3042; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 22px 7px 14px; border-radius: 6px; }}
QMenu::item:selected {{ background: #2a2f48; }}
QMenu::separator {{ height: 1px; background: #2a3042; margin: 5px 8px; }}
QToolTip {{ background: #1a1d28; color: #e6e8ef; border: 1px solid #2a3042; padding: 5px; }}
QMessageBox {{ background: #161924; }}
"""


# --------------------------------------------------------------------------
# Settings and Qt translations
# --------------------------------------------------------------------------

def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Hotkeys
# --------------------------------------------------------------------------

HOTKEY_ACTIONS = ("record", "play", "watch", "stop")
DEFAULT_HOTKEYS = {"record": 0x78, "play": 0x79, "watch": 0x7A, "stop": 0x7B}  # F9–F12 (virtual-key codes)
HOTKEY_CHOICES = [(0x70 + i, f"F{i + 1}") for i in range(12)] + [
    (0x13, "Pause"), (0x91, "Scroll Lock"), (0x2D, "Insert"), (0x24, "Home"),
    (0x23, "End"), (0x21, "Page Up"), (0x22, "Page Down")]
KEY_NAMES = dict(HOTKEY_CHOICES)
WM_KEYUP, WM_SYSKEYUP = 0x0101, 0x0105
LLKHF_INJECTED = 0x10


def load_hotkeys(settings):
    hk = dict(DEFAULT_HOTKEYS)
    saved = settings.get("hotkeys") or {}
    for action in HOTKEY_ACTIONS:
        vk = saved.get(action)
        if vk in KEY_NAMES:
            hk[action] = vk
    if len(set(hk.values())) != len(hk):  # duplicates in a hand-edited file
        hk = dict(DEFAULT_HOTKEYS)
    return hk


def cursor_pos():
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


_qt_translator = None


def apply_qt_translator(lang):
    """Translates Qt's own texts (Yes/No buttons, file dialogs) and sets the number format."""
    global _qt_translator
    QLocale.setDefault(QLocale(QLocale.Language.Russian if lang == "ru" else QLocale.Language.English))
    app = QApplication.instance()
    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)
        _qt_translator = None
    if lang == "en":
        return
    import PySide6
    t = QTranslator()
    for path in (QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
                 os.path.join(os.path.dirname(PySide6.__file__), "translations")):  # packaged .exe layout
        if t.load(f"qtbase_{lang}", path):
            app.installTranslator(t)
            _qt_translator = t
            return


# --------------------------------------------------------------------------
# Windows and coordinate helpers
# --------------------------------------------------------------------------

def dark_title_bar(widget):
    try:
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(int(widget.winId()), 20, ctypes.byref(val), 4)
    except Exception:
        pass


def exclude_from_capture(widget):
    """Keeps the window out of screenshots so overlays never interfere with image search."""
    try:
        ctypes.windll.user32.SetWindowDisplayAffinity(int(widget.winId()), 0x11)
    except Exception:
        pass


def screen_phys_rect(screen):
    g = screen.geometry()
    d = screen.devicePixelRatio()
    return g.x(), g.y(), round(g.width() * d), round(g.height() * d), d


def phys_to_logical_rect(rect):
    """Physical rectangle (as used by mss/pynput) -> logical rectangle for Qt windows."""
    x, y, w, h = rect
    for s in QGuiApplication.screens():
        sx, sy, sw, sh, d = screen_phys_rect(s)
        if sx <= x < sx + sw and sy <= y < sy + sh:
            return QRect(int(sx + (x - sx) / d), int(sy + (y - sy) / d), max(1, int(w / d)), max(1, int(h / d)))
    return QRect(int(x), int(y), int(w), int(h))


def pil_to_qpixmap(img):
    img = img.convert("RGBA")
    data = img.tobytes()
    qimg = QImage(data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg)


def qimage_to_pil(qimg):
    qimg = qimg.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h, bpl = qimg.width(), qimg.height(), qimg.bytesPerLine()
    data = bytes(qimg.constBits())[: bpl * h]
    return Image.frombuffer("RGBA", (w, h), data, "raw", "RGBA", bpl, 1).copy()


def make_app_icon(size=64):
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 64, size / 64)
    g = QLinearGradient(0, 0, 64, 64)
    g.setColorAt(0, QColor(ACCENT))
    g.setColorAt(1, QColor(ACCENT2))
    p.setBrush(g)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 16, 16)
    path = QPainterPath()
    path.moveTo(26, 19)
    path.lineTo(46, 32)
    path.lineTo(26, 45)
    path.closeSubpath()
    p.setBrush(QColor("white"))
    p.drawPath(path)
    p.setBrush(QColor(RED))
    p.drawEllipse(QRectF(11, 11, 11, 11))
    p.end()
    return QIcon(pm)


# --------------------------------------------------------------------------
# Custom widgets
# --------------------------------------------------------------------------

class Toggle(QAbstractButton):
    """Animated on/off switch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.valueChanged.connect(self._on_anim)
        self.toggled.connect(self._animate)

    def _on_anim(self, v):
        self._pos = float(v)
        self.update()

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        off, on = QColor("#2a2f3d"), QColor(ACCENT)
        t = self._pos
        col = QColor(int(off.red() + (on.red() - off.red()) * t),
                     int(off.green() + (on.green() - off.green()) * t),
                     int(off.blue() + (on.blue() - off.blue()) * t))
        if not self.isEnabled():
            col.setAlpha(110)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = 3 + t * (r.width() - d - 6)
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x, 3, d, d))


class NoWheelMixin:
    """The mouse wheel only changes the value while the field has focus, so page scrolling stays safe."""

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)
        else:
            e.ignore()


class Spin(NoWheelMixin, QSpinBox):
    def __init__(self, lo, hi, suffix="", special=None):
        super().__init__()
        self.setRange(lo, hi)
        self.setSuffix(suffix)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if special:
            self.setSpecialValueText(special)


class DSpin(NoWheelMixin, QDoubleSpinBox):
    def __init__(self, lo, hi, step, suffix=""):
        super().__init__()
        self.setRange(lo, hi)
        self.setSingleStep(step)
        self.setDecimals(1)
        self.setSuffix(suffix)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class Slider(NoWheelMixin, QSlider):
    def __init__(self, lo, hi):
        super().__init__(Qt.Orientation.Horizontal)
        self.setRange(lo, hi)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class SimilarityMeter(QWidget):
    """Similarity bar with a threshold marker."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(32)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.score = None
        self.threshold = 85
        self.note = ""

    def set_values(self, score=None, threshold=None, note=None):
        if threshold is not None:
            self.threshold = threshold
        self.score = score
        if note is not None:
            self.note = note
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        p.setPen(QPen(QColor("#232838"), 1))
        p.setBrush(QColor("#10131b"))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 9, 9)
        ok = self.score is not None and self.score * 100 >= self.threshold
        if self.score is not None and self.score > 0.01:
            w = max(18.0, min(1.0, self.score) * r.width())
            g = QLinearGradient(0, 0, r.width(), 0)
            g.setColorAt(0, QColor("#0f9f72" if ok else "#b4532a"))
            g.setColorAt(1, QColor(GREEN if ok else ORANGE))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(QRectF(0, 0, w, r.height()), 9, 9)
        tx = r.width() * self.threshold / 100
        p.setPen(QPen(QColor(255, 255, 255, 210), 2))
        p.drawLine(int(tx), 5, int(tx), int(r.height() - 5))
        f = QFont(self.font())
        f.setPointSizeF(9)
        f.setBold(self.score is not None)
        p.setFont(f)
        if self.score is not None:
            p.setPen(QColor("white"))
            text = f"{self.score * 100:.1f}%  ·  {tr('found') if ok else tr('below threshold')}"
        else:
            p.setPen(QColor(MUTED))
            text = self.note
        p.drawText(r.adjusted(12, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)


class ImageDrop(QWidget):
    """Template image preview; accepts dropped files and images."""

    imageDropped = Signal(object)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setFixedSize(220, 168)
        self.pixmap = None
        self.caption = ""
        self._hover = False

    def set_image(self, img):
        if img is None:
            self.pixmap, self.caption = None, ""
        else:
            self.pixmap = pil_to_qpixmap(img)
            self.caption = f"{img.width} × {img.height} px"
        self.update()

    def dragEnterEvent(self, e):
        md = e.mimeData()
        if md.hasImage() or md.hasUrls():
            self._hover = True
            self.update()
            e.acceptProposedAction()

    def dragLeaveEvent(self, _e):
        self._hover = False
        self.update()

    def dropEvent(self, e):
        self._hover = False
        self.update()
        md = e.mimeData()
        img = None
        if md.hasUrls():
            for url in md.urls():
                try:
                    img = Image.open(url.toLocalFile())
                    img.load()
                    break
                except Exception:
                    continue
        if img is None and md.hasImage():
            qimg = md.imageData()
            if isinstance(qimg, QImage) and not qimg.isNull():
                img = qimage_to_pil(qimg)
        if img is not None:
            self.imageDropped.emit(img)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        clip = QPainterPath()
        clip.addRoundedRect(r, 12, 12)
        p.setClipPath(clip)
        p.fillRect(r, QColor("#10131b"))
        if self.pixmap:
            s = 10  # checkerboard so transparency is visible
            for y in range(0, self.height(), s):
                for x in range(0, self.width(), s):
                    if (x // s + y // s) % 2:
                        p.fillRect(x, y, s, s, QColor("#181b25"))
            area = r.adjusted(12, 12, -12, -28)
            pm = self.pixmap
            scale = min(area.width() / pm.width(), area.height() / pm.height(), 3.0)
            w, h = pm.width() * scale, pm.height() * scale
            target = QRectF(area.center().x() - w / 2, area.center().y() - h / 2, w, h)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, scale < 1)
            p.drawPixmap(target, pm, QRectF(pm.rect()))
            f = QFont(self.font())
            f.setPointSizeF(8.5)
            p.setFont(f)
            p.setPen(QColor(MUTED))
            p.drawText(r.adjusted(0, 0, 0, -7), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                       self.caption)
        else:
            f = QFont(self.font())
            f.setPointSizeF(22)
            p.setFont(f)
            p.setPen(QColor("#3a4058"))
            p.drawText(r.adjusted(0, 0, 0, -50), Qt.AlignmentFlag.AlignCenter, "🖼")
            f.setPointSizeF(9)
            p.setFont(f)
            p.setPen(QColor(MUTED))
            p.drawText(r.adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignCenter, tr("Drop an image here\nor press Ctrl+V"))
        p.setClipping(False)
        pen = QPen(QColor(ACCENT if self._hover else "#2c3246"), 1.5)
        if not self.pixmap:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r, 12, 12)


class MacroDelegate(QStyledItemDelegate):
    """Macro card in the sidebar list."""

    def sizeHint(self, _opt, _idx):
        return QSize(200, 58)

    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(opt.rect).adjusted(2, 3, -2, -3)
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)
        hover = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        if selected:
            p.setBrush(QColor("#21263f"))
            p.setPen(QPen(QColor("#343c6e"), 1))
        elif hover:
            p.setBrush(QColor("#191d29"))
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 11, 11)
        if selected:
            g = QLinearGradient(0, r.top(), 0, r.bottom())
            g.setColorAt(0, QColor(ACCENT))
            g.setColorAt(1, QColor(ACCENT2))
            p.setBrush(g)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(r.left() + 5, r.top() + 13, 3, r.height() - 26), 1.5, 1.5)

        name = idx.data(Qt.ItemDataRole.DisplayRole) or ""
        sub = idx.data(Qt.ItemDataRole.UserRole) or ""
        trig = idx.data(Qt.ItemDataRole.UserRole + 1)

        f = QFont(opt.font)
        f.setPointSizeF(10)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("white" if selected else "#d5d8e2"))
        text_r = r.adjusted(16, 8, -34, 0)
        p.drawText(text_r, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                   QFontMetrics(f).elidedText(name, Qt.TextElideMode.ElideRight, int(text_r.width())))
        f.setBold(False)
        f.setPointSizeF(8.5)
        p.setFont(f)
        p.setPen(QColor(MUTED))
        p.drawText(r.adjusted(16, 0, -34, -8), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, sub)

        if trig:  # green dot — the macro has an image trigger enabled
            c = QRectF(r.right() - 28, r.center().y() - 11, 22, 22)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(52, 211, 153, 40))
            p.drawEllipse(c)
            p.setBrush(QColor(GREEN))
            p.drawEllipse(c.adjusted(7, 7, -7, -7))
        p.restore()


# --------------------------------------------------------------------------
# On-screen overlays
# --------------------------------------------------------------------------

OVERLAY_FLAGS = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                 | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput)


class HudPill(QWidget):
    """Floating status pill on top of all windows (click-through and invisible to screenshots)."""

    def __init__(self):
        super().__init__(None, OVERLAY_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.text = ""
        self.color = QColor(RED)
        self.blink = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(600)
        self.font_ = QFont("Segoe UI", 10)
        self.font_.setBold(True)
        exclude_from_capture(self)

    def _tick(self):
        self.blink = not self.blink
        if self.isVisible():
            self.update()

    def show_text(self, text, color):
        self.text = text
        self.color = QColor(color)
        w = QFontMetrics(self.font_).horizontalAdvance(text) + 58
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(scr.center().x() - w // 2, scr.top() + 14, w, 38)
        if not self.isVisible():
            self.show()
            exclude_from_capture(self)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setBrush(QColor(18, 20, 28, 238))
        border = QColor(self.color)
        border.setAlpha(170)
        p.setPen(QPen(border, 1.5))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        c = QColor(self.color)
        if not self.blink:
            c.setAlpha(80)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(16, r.center().y() - 5, 10, 10))
        p.setFont(self.font_)
        p.setPen(QColor("white"))
        p.drawText(r.adjusted(36, 0, -14, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text)


class FlashRect(QWidget):
    """Labeled frame around a match on screen."""

    def __init__(self, rect, color, label=""):
        super().__init__(None, OVERLAY_FLAGS)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.color = QColor(color)
        self.label = label
        lr = phys_to_logical_rect(rect)
        pad = 4
        self.extra = 26 if label else 0
        self.setGeometry(lr.x() - pad, lr.y() - pad - self.extra, lr.width() + pad * 2,
                         lr.height() + pad * 2 + self.extra)
        exclude_from_capture(self)
        self.show()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(2, self.extra + 2, self.width() - 4, self.height() - self.extra - 4)
        p.setPen(QPen(self.color, 3))
        fill = QColor(self.color)
        fill.setAlpha(28)
        p.setBrush(fill)
        p.drawRoundedRect(box, 6, 6)
        if self.label:
            f = QFont("Segoe UI", 9)
            f.setBold(True)
            p.setFont(f)
            w = QFontMetrics(f).horizontalAdvance(self.label) + 16
            tag = QRectF(2, 0, w, 22)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self.color)
            p.drawRoundedRect(tag, 6, 6)
            p.setPen(QColor("#0e1016"))
            p.drawText(tag, Qt.AlignmentFlag.AlignCenter, self.label)


class RegionSelector(QObject):
    """Rectangle selection on a frozen screenshot (one window per monitor)."""

    finished = Signal(object)  # ([x, y, w, h] in physical pixels, PIL image) or None

    def __init__(self, title):
        super().__init__()
        self.windows = [_SelectorWindow(self, s, title) for s in QGuiApplication.screens()]
        self._done = False
        for w in self.windows:
            w.show()
            w.raise_()
        if self.windows:
            self.windows[0].activateWindow()

    def done(self, result):
        if self._done:
            return
        self._done = True
        for w in self.windows:
            w.hide()
        # destroy the windows only after we have left their event handlers
        QTimer.singleShot(0, lambda: self._finish(result))

    def _finish(self, result):
        for w in self.windows:
            w.deleteLater()
        self.windows = []
        self.finished.emit(result)


class _SelectorWindow(QWidget):
    def __init__(self, owner, screen, title):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.owner = owner
        self.title = title
        self.sx, self.sy, sw, sh, self.dpr = screen_phys_rect(screen)
        self.image = core.grab_pil([self.sx, self.sy, sw, sh])
        self.pix = pil_to_qpixmap(self.image)
        self.pix.setDevicePixelRatio(self.dpr)
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.start = None
        self.cur = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.owner.done(None)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.owner.done(None)
            return
        self.start = e.position().toPoint()
        self.cur = self.start
        self.update()

    def mouseMoveEvent(self, e):
        self.cur = e.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, e):
        if self.start is None or e.button() != Qt.MouseButton.LeftButton:
            return
        r = QRect(self.start, e.position().toPoint()).normalized()
        self.start = None
        if r.width() < 4 or r.height() < 4:
            self.update()
            return
        d = self.dpr
        px = [round(r.x() * d), round(r.y() * d), round(r.width() * d), round(r.height() * d)]
        crop = self.image.crop((px[0], px[1], px[0] + px[2], px[1] + px[3]))
        self.owner.done(([self.sx + px[0], self.sy + px[1], px[2], px[3]], crop))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.drawPixmap(0, 0, self.pix)
        p.fillRect(self.rect(), QColor(8, 10, 16, 150))
        if self.start is not None and self.cur is not None:
            r = QRect(self.start, self.cur).normalized()
            d = self.dpr
            p.drawPixmap(r, self.pix, QRect(int(r.x() * d), int(r.y() * d), int(r.width() * d), int(r.height() * d)))
            p.setPen(QPen(QColor(ACCENT), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)
            label = f"{round(r.width() * d)} × {round(r.height() * d)}"
            f = QFont("Segoe UI", 9)
            f.setBold(True)
            p.setFont(f)
            tw = QFontMetrics(f).horizontalAdvance(label) + 14
            tag = QRectF(r.x(), max(0, r.y() - 26), tw, 22)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ACCENT))
            p.drawRoundedRect(tag, 6, 6)
            p.setPen(QColor("white"))
            p.drawText(tag, Qt.AlignmentFlag.AlignCenter, label)
        elif self.cur is not None:
            p.setPen(QPen(QColor(255, 255, 255, 70), 1, Qt.PenStyle.DashLine))
            p.drawLine(0, self.cur.y(), self.width(), self.cur.y())
            p.drawLine(self.cur.x(), 0, self.cur.x(), self.height())
        f = QFont("Segoe UI", 11)
        f.setBold(True)
        p.setFont(f)
        text = f"{self.title}   ·   {tr('Esc / right-click — cancel')}"
        w = QFontMetrics(f).horizontalAdvance(text) + 44
        box = QRectF(self.width() / 2 - w / 2, 24, w, 42)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(18, 20, 28, 238))
        p.drawRoundedRect(box, 21, 21)
        p.setPen(QColor("white"))
        p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)


# --------------------------------------------------------------------------
# Bridge between worker threads and the UI
# --------------------------------------------------------------------------

class Bridge(QObject):
    log = Signal(str)
    hud = Signal(str, str)
    finished = Signal()
    hotkey = Signal(str)
    meter = Signal(object, float)                       # macro, similarity
    test_result = Signal(object, float, object, float)  # macro, similarity, rect, ms


# --------------------------------------------------------------------------
# UI builders
# --------------------------------------------------------------------------

def card(title, subtitle=None, right=None):
    frame = QFrame()
    frame.setObjectName("card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(20, 18, 20, 20)
    lay.setSpacing(14)
    head = QHBoxLayout()
    head.setSpacing(12)
    col = QVBoxLayout()
    col.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("cardTitle")
    col.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setObjectName("muted")
        s.setWordWrap(True)
        col.addWidget(s)
    head.addLayout(col, 1)
    if right is not None:
        head.addWidget(right, 0, Qt.AlignmentFlag.AlignTop)
    lay.addLayout(head)
    return frame, lay


def setting_row(title, desc, widget):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(12)
    col = QVBoxLayout()
    col.setSpacing(1)
    col.addWidget(QLabel(title))
    if desc:
        d = QLabel(desc)
        d.setObjectName("hint")
        d.setWordWrap(True)
        col.addWidget(d)
    h.addLayout(col, 1)
    h.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
    return w


def button(text, name=None, tip=None, slot=None):
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    if tip:
        b.setToolTip(tip)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if slot:
        b.clicked.connect(slot)
    return b


def segmented(options, checked, slot):
    """Segmented control: options = [(key, text)], slot(key) is called on click."""
    box = QFrame()
    box.setObjectName("segBox")
    lay = QHBoxLayout(box)
    lay.setContentsMargins(3, 3, 3, 3)
    lay.setSpacing(2)
    group = QButtonGroup(box)
    buttons = {}
    for key, text in options:
        b = button(text, "seg")
        b.setCheckable(True)
        b.setChecked(key == checked)
        b.clicked.connect(lambda _=False, k=key: slot(k))
        group.addButton(b)
        lay.addWidget(b)
        buttons[key] = b
    return box, buttons


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


def quoted_names(macros):
    return ", ".join(tr("“{name}”", name=m["name"]) for m in macros)


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle(f"Macro Studio {__version__}")
        self.setWindowIcon(make_app_icon())
        self.setMinimumSize(980, 600)

        self.bridge = Bridge()
        self.bridge.log.connect(self._append_log)
        self.bridge.hud.connect(self._show_hud)
        self.bridge.finished.connect(self._finish_worker)
        self.bridge.hotkey.connect(self._on_hotkey)
        self.bridge.meter.connect(self._on_meter)
        self.bridge.test_result.connect(self._on_test_result)

        self.macros = []
        self.current = None
        self._loading = False
        self.templates = core.TemplateCache()
        self.recorder = core.Recorder()
        self.rec_macro = None
        self.stop_event = threading.Event()
        self.player = core.Player(self.stop_event)
        self.worker = None
        self.mode = "idle"          # idle | record | play | watch
        self.selector = None
        self._selecting = False
        self._flashes = []
        self.hud = HudPill()
        self.hotkeys = load_hotkeys(settings)
        self._vk_action = {vk: a for a, vk in self.hotkeys.items()}
        self.data_file = DATA_FILE
        self._backed_up = False
        self._corner_armed = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self.save)

        self._rec_timer = QTimer(self)
        self._rec_timer.setInterval(200)
        self._rec_timer.timeout.connect(self._rec_tick)

        paste = QAction(self)
        paste.setShortcut("Ctrl+V")
        paste.triggered.connect(self.paste_template)
        self.addAction(paste)

        # emergency stop by moving the mouse into the top-left corner (works even when an
        # elevated window has focus and the keyboard hook can't see the hotkeys)
        self._corner_timer = QTimer(self)
        self._corner_timer.setInterval(60)
        self._corner_timer.timeout.connect(self._check_corner)

        self.tray = QSystemTrayIcon(make_app_icon(), self)
        self.tray.activated.connect(self._tray_activated)

        self.load()
        self.build_ui()
        self.refresh_list()
        self.select(0)
        self.set_mode("idle")
        self.tray.show()

        self.kb_listener = keyboard.Listener(on_press=self._kb_press, on_release=self._kb_release,
                                             win32_event_filter=self._kb_filter)
        self.kb_listener.daemon = True
        self.kb_listener.start()

        avail = QGuiApplication.primaryScreen().availableGeometry()
        w, h = min(1240, avail.width() - 40), min(840, avail.height() - 40)
        self.resize(w, h)
        self.move(avail.center().x() - w // 2, avail.center().y() - h // 2)
        dark_title_bar(self)

        self.log(tr("Ready. {record} — record, {play} — play, {watch} — monitor, {stop} — stop.",
                    **{a: self.hk(a) for a in HOTKEY_ACTIONS}))

    def hk(self, action):
        return KEY_NAMES.get(self.hotkeys[action], "?")

    # ================= building the UI =================

    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_sidebar())
        outer.addWidget(self._build_content(), 1)
        self.setCentralWidget(root)  # replaces (and deletes) the previous UI when the language changes

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(262)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(16, 20, 16, 16)
        lay.setSpacing(10)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(make_app_icon().pixmap(38, 38))
        brand.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(0)
        t = QLabel("Macro Studio")
        t.setObjectName("appTitle")
        s = QLabel(tr("record · replay · image triggers"))
        s.setObjectName("appSub")
        col.addWidget(t)
        col.addWidget(s)
        brand.addLayout(col, 1)
        lay.addLayout(brand)
        lay.addSpacing(14)

        head = QHBoxLayout()
        sec = QLabel(tr("MACROS"))
        sec.setObjectName("section")
        head.addWidget(sec)
        head.addStretch(1)
        more = button("⋯", "icon", tr("Import / export"))
        menu = QMenu(more)
        menu.addAction(tr("Import macros…"), self.import_macros)
        menu.addAction(tr("Export all macros…"), self.export_macros)
        more.setMenu(menu)
        head.addWidget(more)
        lay.addLayout(head)

        self.listw = QListWidget()
        self.listw.setItemDelegate(MacroDelegate(self.listw))
        self.listw.setMouseTracking(True)
        self.listw.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.listw.currentRowChanged.connect(self._on_row_changed)
        self.listw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.listw.customContextMenuRequested.connect(self._list_menu)
        lay.addWidget(self.listw, 1)

        add = button("＋  " + tr("New macro"), "primary", slot=self.add_macro)
        add.setMinimumHeight(40)
        lay.addWidget(add)

        keys = QFrame()
        keys.setObjectName("card")
        kl = QGridLayout(keys)
        kl.setContentsMargins(14, 12, 14, 12)
        kl.setHorizontalSpacing(10)
        kl.setVerticalSpacing(7)
        for i, (action, d) in enumerate([("record", tr("Record")), ("play", tr("Play")),
                                         ("watch", tr("Monitor")), ("stop", tr("Stop"))]):
            kb = button(self.hk(action), "kbd", tr("Click to change the hotkey"))
            menu = QMenu(kb)
            for vk, name in HOTKEY_CHOICES:
                act = menu.addAction(name)
                act.setCheckable(True)
                act.setChecked(vk == self.hotkeys[action])
                act.triggered.connect(lambda _=False, a=action, v=vk: self.set_hotkey(a, v))
            kb.setMenu(menu)
            kl.addWidget(kb, i, 0)
            dl = QLabel(d)
            dl.setObjectName("muted")
            kl.addWidget(dl, i, 1)
        kl.setColumnStretch(1, 1)
        lay.addWidget(keys)

        lang = QHBoxLayout()
        ll = QLabel("🌐  " + tr("Language"))
        ll.setObjectName("muted")
        lang.addWidget(ll)
        lang.addStretch(1)
        box, _ = segmented([("en", "EN"), ("ru", "RU")], i18n.language(), self.change_language)
        lang.addWidget(box)
        lay.addLayout(lang)
        return side

    def _build_content(self):
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(28, 22, 18, 16)
        v.setSpacing(12)

        top = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("heading")
        self.name_edit.setPlaceholderText(tr("Macro name"))
        self.name_edit.setToolTip(tr("Click to rename"))
        self.name_edit.editingFinished.connect(self._rename_from_heading)
        top.addWidget(self.name_edit, 1)
        self.status_pill = QLabel()
        top.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignVCenter)
        v.addLayout(top)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chip_events = QLabel()
        self.chip_clicks = QLabel()
        self.chip_dur = QLabel()
        self.chip_anchor = QLabel()
        for c in (self.chip_events, self.chip_clicks, self.chip_dur, self.chip_anchor):
            c.setObjectName("chip")
            chips.addWidget(c)
        chips.addStretch(1)
        v.addLayout(chips)
        v.addSpacing(4)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_record = button("", "record", self.hk("record"), self.toggle_record)
        self.btn_play = button("▶   " + tr("Play"), "primary", self.hk("play"), self.play_selected)
        self.btn_stop = button("■   " + tr("Stop"), "ghost", self.hk("stop"), self.stop_all)
        for b in (self.btn_record, self.btn_play, self.btn_stop):
            b.setMinimumHeight(44)
            b.setMinimumWidth(170)
            actions.addWidget(b)
        actions.addStretch(1)
        v.addLayout(actions)
        v.addSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName("root")
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 10, 4)
        col.setSpacing(14)
        col.addWidget(self._build_trigger_card())
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._build_playback_card(), 1)
        row.addWidget(self._build_watch_card(), 1)
        col.addLayout(row)
        col.addWidget(self._build_log_card())
        col.addStretch(1)
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)
        return wrap

    def _build_trigger_card(self):
        self.tg_enabled = Toggle()
        self.tg_enabled.setToolTip(tr("Enable the trigger for this macro"))
        self.tg_enabled.toggled.connect(self.on_option_change)
        frame, lay = card(tr("Image trigger"),
                          tr("When this image appears on screen, the macro runs automatically (in monitoring mode)."),
                          self.tg_enabled)
        body = QHBoxLayout()
        body.setSpacing(24)

        left = QVBoxLayout()
        left.setSpacing(8)
        self.drop = ImageDrop()
        self.drop.imageDropped.connect(self.set_template)
        left.addWidget(self.drop)
        g = QGridLayout()
        g.setSpacing(6)
        g.addWidget(button("📋 " + tr("Paste"), tip=tr("Ctrl+V — from clipboard"), slot=self.paste_template), 0, 0)
        g.addWidget(button("✂ " + tr("From screen"), tip=tr("Select the image directly on screen"),
                           slot=self.capture_template), 0, 1)
        g.addWidget(button("📁 " + tr("File…"), slot=self.load_template_file), 1, 0)
        g.addWidget(button("✕ " + tr("Remove"), slot=self.clear_template), 1, 1)
        left.addLayout(g)
        left.addStretch(1)
        body.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(14)

        where = QHBoxLayout()
        where.setSpacing(10)
        lbl = QLabel(tr("Search area"))
        lbl.setMinimumWidth(130)
        where.addWidget(lbl)
        seg, btns = segmented([("full", tr("Full screen")), ("rect", tr("Region"))], "full", self._region_mode)
        self.seg_full, self.seg_rect = btns["full"], btns["rect"]
        where.addWidget(seg)
        self.btn_pick = button(tr("Change…"), "ghost", tr("Select the area on screen again"), self.pick_region)
        where.addWidget(self.btn_pick)
        self.region_lbl = QLabel()
        self.region_lbl.setObjectName("regionLbl")
        where.addWidget(self.region_lbl)
        where.addStretch(1)
        right.addLayout(where)

        thr = QHBoxLayout()
        thr.setSpacing(10)
        lbl = QLabel(tr("Similarity threshold"))
        lbl.setMinimumWidth(130)
        thr.addWidget(lbl)
        self.sl_thr = Slider(50, 100)
        self.sl_thr.valueChanged.connect(self.on_option_change)
        thr.addWidget(self.sl_thr, 1)
        self.lbl_thr = QLabel()
        self.lbl_thr.setObjectName("bigValue")
        self.lbl_thr.setMinimumWidth(66)
        self.lbl_thr.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        thr.addWidget(self.lbl_thr)
        right.addLayout(thr)

        test = QHBoxLayout()
        test.setSpacing(10)
        lbl = QLabel(tr("On screen now"))
        lbl.setMinimumWidth(130)
        test.addWidget(lbl)
        self.meter = SimilarityMeter()
        test.addWidget(self.meter, 1)
        test.addWidget(button("🔍 " + tr("Check"), "ghost", tr("Find the image on screen now and show the similarity"),
                              self.test_match))
        right.addLayout(test)

        self.tg_relative = Toggle()
        self.tg_relative.toggled.connect(self.on_option_change)
        right.addWidget(setting_row(tr("Clicks follow the image"),
                                    tr("If the image is somewhere else on screen, the clicks move with it."),
                                    self.tg_relative))
        self.tg_multiscale = Toggle()
        self.tg_multiscale.toggled.connect(self.on_option_change)
        right.addWidget(setting_row(tr("Search at different scales"),
                                    tr("Finds enlarged or shrunk images, but is slower."),
                                    self.tg_multiscale))
        self.sp_cooldown = DSpin(0, 3600, 0.5, tr(" s"))
        self.sp_cooldown.valueChanged.connect(self.on_option_change)
        right.addWidget(setting_row(tr("Cooldown after trigger"),
                                    tr("So the macro doesn't fire again and again on the same image."),
                                    self.sp_cooldown))
        self.tg_wait_gone = Toggle()
        self.tg_wait_gone.toggled.connect(self.on_option_change)
        right.addWidget(setting_row(tr("Wait until the image disappears"),
                                    tr("After a run, the macro can fire again only once the image has left the screen."),
                                    self.tg_wait_gone))
        self.sp_max_runs = Spin(0, 100000, special="∞")
        self.sp_max_runs.valueChanged.connect(self.on_option_change)
        right.addWidget(setting_row(tr("Max runs per monitoring session"),
                                    tr("0 — unlimited. Protects against endless runs if the macro doesn't remove the image."),
                                    self.sp_max_runs))
        self.tg_require = Toggle()
        self.tg_require.toggled.connect(self.on_option_change)
        right.addWidget(setting_row(tr("Play only when the image is found"),
                                    tr("On Play, a repeat is skipped if the image isn't on screen, instead of clicking "
                                       "at the recorded spots."),
                                    self.tg_require))
        body.addLayout(right, 1)
        lay.addLayout(body)
        return frame

    def _build_playback_card(self):
        frame, lay = card(tr("Playback"), tr("How to replay the recorded actions."))
        self.sp_repeats = Spin(0, 100000, special="∞")
        self.sp_repeats.valueChanged.connect(self.on_option_change)
        lay.addWidget(setting_row(tr("Repeats"), tr("0 — forever, until you press {key}", key=self.hk("stop")), self.sp_repeats))
        self.sp_rdelay = DSpin(0, 3600, 0.1, tr(" s"))
        self.sp_rdelay.valueChanged.connect(self.on_option_change)
        lay.addWidget(setting_row(tr("Delay between repeats"), None, self.sp_rdelay))

        sp = QHBoxLayout()
        sp.setSpacing(10)
        sp.addWidget(QLabel(tr("Speed")))
        self.sl_speed = Slider(25, 500)
        self.sl_speed.valueChanged.connect(self.on_option_change)
        sp.addWidget(self.sl_speed, 1)
        self.lbl_speed = QLabel()
        self.lbl_speed.setObjectName("bigValue")
        self.lbl_speed.setMinimumWidth(66)
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sp.addWidget(self.lbl_speed)
        lay.addLayout(sp)

        self.tg_skip = Toggle()
        self.tg_skip.toggled.connect(self.on_option_change)
        lay.addWidget(setting_row(tr("Clicks only"),
                                  tr("Don't replay mouse movement — jump straight to click points."), self.tg_skip))
        self.tg_kb = Toggle()
        self.tg_kb.toggled.connect(self.on_option_change)
        lay.addWidget(setting_row(tr("Record keyboard"), tr("Key presses are recorded too."), self.tg_kb))
        lay.addStretch(1)
        return frame

    def _build_watch_card(self):
        frame, lay = card(tr("Monitoring"),
                          tr("Watches the screen and runs macros with an enabled trigger as soon as their image is found."))
        self.btn_watch = button("", "watch", self.hk("watch"), self.toggle_watch)
        self.btn_watch.setMinimumHeight(44)
        lay.addWidget(self.btn_watch)
        self.sp_interval = Spin(50, 60000, tr(" ms"))
        self.sp_interval.setSingleStep(50)
        self.sp_interval.setValue(int(self.settings.get("interval_ms", 300)))
        self.sp_interval.valueChanged.connect(self._on_app_setting)
        lay.addWidget(setting_row(tr("Check every"), tr("Lower = faster reaction, but more CPU load."),
                                  self.sp_interval))
        self.tg_hide = Toggle()
        self.tg_hide.setChecked(bool(self.settings.get("minimize", True)))
        self.tg_hide.toggled.connect(self._on_app_setting)
        lay.addWidget(setting_row(tr("Minimize window"), tr("During playback and monitoring."), self.tg_hide))
        self.tg_failsafe = Toggle()
        self.tg_failsafe.setChecked(bool(self.settings.get("failsafe", True)))
        self.tg_failsafe.toggled.connect(self._on_app_setting)
        lay.addWidget(setting_row(tr("Corner emergency stop"),
                                  tr("Move the mouse into the top-left corner of the screen to stop playback or "
                                     "monitoring. Works even when hotkeys can't (e.g. over admin windows)."),
                                  self.tg_failsafe))
        self.watch_info = QLabel()
        self.watch_info.setObjectName("hint")
        self.watch_info.setWordWrap(True)
        lay.addWidget(self.watch_info)
        lay.addStretch(1)
        return frame

    def _build_log_card(self):
        clear = button(tr("Clear"), "ghost")
        frame, lay = card(tr("Log"), None, clear)
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("log")
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumBlockCount(500)
        self.log_box.setMinimumHeight(140)
        clear.clicked.connect(self.log_box.clear)
        lay.addWidget(self.log_box)
        return frame

    # ================= language =================

    def change_language(self, lang):
        if lang == i18n.language():
            return
        if self.mode != "idle" or self._selecting:
            return
        # rebuild after the click handler returns: the clicked button is part of the old UI
        QTimer.singleShot(0, lambda: self._apply_language(lang))

    def _apply_language(self, lang):
        i18n.set_language(lang)
        apply_qt_translator(lang)
        self.settings["language"] = lang
        save_settings(self.settings)
        self.rebuild_ui()

    def rebuild_ui(self):
        """Recreates all widgets (after a language or hotkey change), keeping the state."""
        log_text = self.log_box.toPlainText()
        self.setLocale(QLocale())  # new widgets inherit the window's number format
        self.build_ui()
        self.log_box.setPlainText(log_text)
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())
        self.refresh_list()
        self.select(self.current or 0)
        self.set_mode(self.mode)

    def _on_app_setting(self, *_):
        self.settings["interval_ms"] = self.sp_interval.value()
        self.settings["minimize"] = self.tg_hide.isChecked()
        self.settings["failsafe"] = self.tg_failsafe.isChecked()
        save_settings(self.settings)

    # ================= hotkeys, tray and emergency stop =================

    def set_hotkey(self, action, vk):
        if self.mode != "idle" or self.hotkeys[action] == vk:
            return
        for other, ovk in self.hotkeys.items():  # the key was used by another action: swap them
            if ovk == vk:
                self.hotkeys[other] = self.hotkeys[action]
        self.hotkeys[action] = vk
        self._vk_action = {v: a for a, v in self.hotkeys.items()}
        self.settings["hotkeys"] = dict(self.hotkeys)
        save_settings(self.settings)
        QTimer.singleShot(0, self.rebuild_ui)  # the clicked menu belongs to the old UI

    def _kb_filter(self, msg, data):
        """Low-level keyboard hook filter: handles our hotkeys and keeps them away from other apps
        (otherwise F11 would also toggle browser full screen, F10 open window menus, etc.)."""
        action = self._vk_action.get(data.vkCode)
        if action is None or data.flags & LLKHF_INJECTED:
            return True
        if msg in (WM_KEYUP, WM_SYSKEYUP):
            self.bridge.hotkey.emit(action)
        self.kb_listener.suppress_event()

    def _kb_press(self, key):
        self.recorder.key(key, True)

    def _kb_release(self, key):
        self.recorder.key(key, False)

    def _on_hotkey(self, name):
        if self._selecting:
            return
        {"record": self.toggle_record, "play": self.play_selected,
         "watch": self.toggle_watch, "stop": self.stop_all}[name]()

    def _update_tray(self):
        menu = QMenu(self)
        menu.addAction(tr("Show window"), self._show_window)
        stop = menu.addAction(f"■  {tr('Stop')}  ({self.hk('stop')})", self.stop_all)
        stop.setEnabled(self.mode != "idle")
        watch = menu.addAction(tr("Stop monitoring") if self.mode == "watch" else tr("Start monitoring"),
                               self.toggle_watch)
        watch.setEnabled(self.mode in ("idle", "watch"))
        menu.addSeparator()
        menu.addAction(tr("Quit"), self.close)
        old = self.tray.contextMenu()
        self.tray.setContextMenu(menu)
        if old is not None:
            old.deleteLater()
        if self.mode == "idle":
            self.tray.setToolTip("Macro Studio")
        else:
            self.tray.setToolTip("Macro Studio — " + tr("click this icon to stop"))

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger and self.mode != "idle":
            self.stop_all()  # a click on the tray icon is a reliable stop button
        elif reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _check_corner(self):
        if self.mode not in ("play", "watch") or not self.tg_failsafe.isChecked():
            return
        try:
            x, y = cursor_pos()
        except Exception:
            return
        in_corner = x <= 1 and y <= 1
        if in_corner and self._corner_armed:
            self.log(tr("Emergency stop: the mouse was moved into the top-left corner."))
            self.stop_all()
        self._corner_armed = not in_corner  # only fires after the cursor has been outside the corner

    # ================= state and log =================

    def log(self, text):
        self.bridge.log.emit(text)

    def _append_log(self, text):
        self.log_box.appendPlainText(f"{time.strftime('%H:%M:%S')}   {text}")

    def _show_hud(self, text, color):
        if self.mode == "idle":
            return
        self.hud.show_text(text, color)

    def set_mode(self, mode):
        self.mode = mode
        text, fg, bg = {
            "idle": ("●  " + tr("Ready"), "#8b90a0", "#1b1f2c"),
            "record": ("●  " + tr("Recording"), "#ff8096", "#2a1520"),
            "play": ("▶  " + tr("Playing"), "#8fb0ff", "#18203a"),
            "watch": ("●  " + tr("Monitoring"), "#5eead4", "#0f2a26"),
        }[mode]
        self.status_pill.setText(text)
        self.status_pill.setStyleSheet(f"background:{bg}; color:{fg}; border-radius: 13px; padding: 5px 14px;"
                                       f"font-weight: 600; font-size: 9.5pt;")
        recording = mode == "record"
        self.btn_record.setText("■   " + tr("Stop recording") if recording else "●   " + tr("Record"))
        self.btn_record.setProperty("active", recording)
        repolish(self.btn_record)
        watching = mode == "watch"
        self.btn_watch.setText("⏹   " + tr("Stop monitoring") if watching else "👁   " + tr("Start monitoring"))
        self.btn_watch.setProperty("active", watching)
        repolish(self.btn_watch)
        self.btn_play.setEnabled(mode == "idle")
        self.btn_record.setEnabled(mode in ("idle", "record"))
        self.btn_watch.setEnabled(mode in ("idle", "watch"))
        self.listw.setEnabled(mode == "idle")
        if mode == "idle":
            self.hud.hide()
        if mode in ("play", "watch"):
            self._corner_armed = False
            self._corner_timer.start()
        else:
            self._corner_timer.stop()
        self._update_tray()

    # ================= persistence =================

    def load(self):
        if os.path.exists(self.data_file):
            try:
                self.macros = core.load_macros(self.data_file)
            except Exception as e:
                # never overwrite a file we couldn't read: move it aside first
                bad = os.path.splitext(self.data_file)[0] + time.strftime(".corrupt-%Y%m%d-%H%M%S.json")
                try:
                    os.replace(self.data_file, bad)
                    note = tr("The damaged file was renamed to:\n{path}\nso it won't be overwritten.", path=bad)
                except OSError:
                    self.data_file = os.path.splitext(self.data_file)[0] + ".new.json"
                    note = tr("New macros will be saved to:\n{path}\nso the damaged file won't be overwritten.",
                              path=self.data_file)
                QMessageBox.critical(self, tr("Error"), tr("Could not read {path}:\n{err}", path=DATA_FILE, err=e)
                                     + "\n\n" + note)
        if not self.macros:
            self.macros = [core.new_macro(tr("My first macro"))]

    def save_later(self):
        self._save_timer.start()

    def save(self):
        self._save_timer.stop()
        try:
            if not self._backed_up and os.path.exists(self.data_file):
                shutil.copy2(self.data_file, self.data_file + ".bak")  # one backup per session
            self._backed_up = True
            core.save_macros(self.data_file, self.macros)
        except Exception as e:
            self.log(tr("Save error: {err}", err=e))

    # ================= macro list =================

    @staticmethod
    def _item_texts(m):
        n, clicks, dur = core.macro_stats(m)
        sub = f"{count(clicks, 'click')} · {tr('{dur} s', dur=f'{dur:.1f}')}" if n else tr("empty — press “Record”")
        trig = bool(m["trigger"]["enabled"] and m["trigger"]["template"])
        return m["name"], sub, trig

    def refresh_list(self):
        self.listw.blockSignals(True)
        self.listw.clear()
        for m in self.macros:
            name, sub, trig = self._item_texts(m)
            it = QListWidgetItem(name)
            it.setData(Qt.ItemDataRole.UserRole, sub)
            it.setData(Qt.ItemDataRole.UserRole + 1, trig)
            self.listw.addItem(it)
        if self.current is not None and self.current < len(self.macros):
            self.listw.setCurrentRow(self.current)
        self.listw.blockSignals(False)
        self._update_watch_info()

    def refresh_current_item(self):
        m = self.macro()
        it = self.listw.item(self.current) if m else None
        if it:
            name, sub, trig = self._item_texts(m)
            it.setText(name)
            it.setData(Qt.ItemDataRole.UserRole, sub)
            it.setData(Qt.ItemDataRole.UserRole + 1, trig)
        self._update_watch_info()

    def _active_triggers(self):
        return [m for m in self.macros if m["trigger"]["enabled"] and m["trigger"]["template"] and m["events"]]

    def _update_watch_info(self):
        active = self._active_triggers()
        if active:
            self.watch_info.setText(tr("Watching ({n}): {names}", n=len(active), names=quoted_names(active)))
        else:
            self.watch_info.setText(tr("Nothing to watch yet: enable a trigger, add an image and record actions."))

    def _on_row_changed(self, row):
        if row >= 0:
            self.select(row)

    def select(self, idx):
        if not self.macros:
            return
        idx = max(0, min(idx, len(self.macros) - 1))
        self.current = idx
        if self.listw.currentRow() != idx:
            self.listw.blockSignals(True)
            self.listw.setCurrentRow(idx)
            self.listw.blockSignals(False)
        self.load_macro_to_ui()

    def macro(self):
        if self.current is None or self.current >= len(self.macros):
            return None
        return self.macros[self.current]

    def _list_menu(self, pos):
        it = self.listw.itemAt(pos)
        if not it or self.mode != "idle":
            return
        self.select(self.listw.row(it))
        menu = QMenu(self)
        menu.addAction(tr("Rename"), lambda: (self.name_edit.setFocus(), self.name_edit.selectAll()))
        menu.addAction(tr("Duplicate"), self.dup_macro)
        menu.addAction(tr("Export…"), lambda: self.export_macros(only_current=True))
        menu.addSeparator()
        menu.addAction(tr("Delete"), self.delete_macro)
        menu.exec(self.listw.viewport().mapToGlobal(pos))

    def add_macro(self):
        if self.mode != "idle":
            return
        self.macros.append(core.new_macro(tr("Macro {n}", n=len(self.macros) + 1)))
        self.current = len(self.macros) - 1
        self.refresh_list()
        self.select(self.current)
        self.save()
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def dup_macro(self):
        m = self.macro()
        if not m:
            return
        c = copy.deepcopy(m)
        c["name"] = tr("{name} (copy)", name=m["name"])
        self.macros.insert(self.current + 1, c)
        self.current += 1
        self.refresh_list()
        self.select(self.current)
        self.save()

    def delete_macro(self):
        m = self.macro()
        if not m:
            return
        if QMessageBox.question(self, tr("Delete"),
                                tr("Delete macro “{name}”?", name=m["name"])) != QMessageBox.StandardButton.Yes:
            return
        del self.macros[self.current]
        if not self.macros:
            self.macros.append(core.new_macro(tr("Macro {n}", n=1)))
        self.current = min(self.current, len(self.macros) - 1)
        self.refresh_list()
        self.select(self.current)
        self.save()

    def _rename_from_heading(self):
        m = self.macro()
        if not m:
            return
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setText(m["name"])
        elif name != m["name"]:
            m["name"] = name
            self.refresh_current_item()
            self.save_later()

    def export_macros(self, only_current=False):
        items = [self.macro()] if only_current else self.macros
        default = (items[0]["name"] if only_current else "macros") + ".json"
        path, _ = QFileDialog.getSaveFileName(self, tr("Export"), os.path.join(APP_DIR, default), tr("Macros (*.json)"))
        if path:
            core.save_macros(path, items, indent=1)
            self.log(tr("Exported: {path}", path=path))

    def import_macros(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Import"), APP_DIR, tr("Macros (*.json)"))
        if not path:
            return
        try:
            added = core.load_macros(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))
            return
        self.macros.extend(added)
        self.refresh_list()
        self.save()
        self.log(tr("Imported macros: {n}", n=len(added)))

    # ================= syncing UI and data =================

    def load_macro_to_ui(self):
        m = self.macro()
        if not m:
            return
        self._loading = True
        t = m["trigger"]
        self.name_edit.setText(m["name"])
        self.tg_enabled.setChecked(t["enabled"])
        self.sl_thr.setValue(int(t["threshold"]))
        self.tg_relative.setChecked(t["relative"])
        self.tg_multiscale.setChecked(t["multiscale"])
        self.sp_cooldown.setValue(float(t["cooldown"]))
        self.tg_wait_gone.setChecked(t["wait_gone"])
        self.sp_max_runs.setValue(int(t["max_runs"]))
        self.tg_require.setChecked(t["require"])
        self.sp_repeats.setValue(int(m["repeats"]))
        self.sp_rdelay.setValue(float(m["repeat_delay"]))
        self.sl_speed.setValue(int(round(float(m["speed"]) * 100)))
        self.tg_skip.setChecked(m["skip_moves"])
        self.tg_kb.setChecked(m["record_keyboard"])
        self._loading = False
        self.meter.set_values(None, int(t["threshold"]),
                              tr("Press “Check”") if t["template"] else tr("Add an image first"))
        self.update_labels()
        self.update_preview()

    def on_option_change(self, *_):
        self.lbl_thr.setText(f"{self.sl_thr.value()}%")
        self.lbl_speed.setText(f"×{self.sl_speed.value() / 100:.2f}")
        if self._loading:
            return
        m = self.macro()
        if not m:
            return
        t = m["trigger"]
        t["enabled"] = self.tg_enabled.isChecked()
        t["threshold"] = self.sl_thr.value()
        t["relative"] = self.tg_relative.isChecked()
        t["multiscale"] = self.tg_multiscale.isChecked()
        t["cooldown"] = self.sp_cooldown.value()
        t["wait_gone"] = self.tg_wait_gone.isChecked()
        t["max_runs"] = self.sp_max_runs.value()
        t["require"] = self.tg_require.isChecked()
        m["repeats"] = self.sp_repeats.value()
        m["repeat_delay"] = self.sp_rdelay.value()
        m["speed"] = self.sl_speed.value() / 100
        m["skip_moves"] = self.tg_skip.isChecked()
        m["record_keyboard"] = self.tg_kb.isChecked()
        self.meter.set_values(self.meter.score, t["threshold"])
        self.refresh_current_item()
        self.save_later()

    def update_labels(self):
        m = self.macro()
        if not m:
            return
        n, clicks, dur = core.macro_stats(m)
        self.chip_events.setText("⚡ " + count(n, "event"))
        self.chip_clicks.setText("🖱 " + count(clicks, "click"))
        self.chip_dur.setText("⏱ " + tr("{dur} s", dur=f"{dur:.1f}"))
        a = m.get("anchor")
        self.chip_anchor.setText("📍 " + (tr("anchored to image ({x}, {y})", x=a[0], y=a[1]) if a
                                          else tr("not anchored to image")))
        self.chip_anchor.setToolTip(
            tr("Where the image was when recording started — clicks are shifted relative to this point.") if a else
            tr("The image wasn't on screen during recording — clicks use the original coordinates."))
        self.lbl_thr.setText(f"{self.sl_thr.value()}%")
        self.lbl_speed.setText(f"×{self.sl_speed.value() / 100:.2f}")
        r = m["trigger"]["region"]
        self.seg_rect.setChecked(bool(r))
        self.seg_full.setChecked(not r)
        self.btn_pick.setVisible(bool(r))
        self.region_lbl.setText(f"{r[2]}×{r[3]} px" if r else "")

    def update_preview(self):
        m = self.macro()
        b64 = m["trigger"]["template"] if m else None
        self.drop.set_image(core.b64_to_image(b64) if b64 else None)

    # ================= template image =================

    def set_template(self, img):
        m = self.macro()
        if not m or self.mode != "idle":
            return
        if img.width < 4 or img.height < 4:
            QMessageBox.warning(self, tr("Image"), tr("The image is too small."))
            return
        m["trigger"]["template"] = core.image_to_b64(img)
        m["anchor"] = None
        if not m["trigger"]["enabled"]:
            self.tg_enabled.setChecked(True)
        self.refresh_current_item()
        self.update_preview()
        self.update_labels()
        self.meter.set_values(None, m["trigger"]["threshold"], tr("Image added — press “Check”"))
        self.save()
        self.log(tr("Image for “{name}” added ({w}×{h}).", name=m["name"], w=img.width, h=img.height))

    def paste_template(self):
        fw = QApplication.focusWidget()
        if isinstance(fw, QLineEdit):
            fw.paste()
            return
        cb = QGuiApplication.clipboard()
        md = cb.mimeData()
        img = None
        if md.hasImage():
            qimg = cb.image()
            if not qimg.isNull():
                img = qimage_to_pil(qimg)
        if img is None and md.hasUrls():
            for url in md.urls():
                try:
                    img = Image.open(url.toLocalFile())
                    img.load()
                    break
                except Exception:
                    continue
        if img is None:
            QMessageBox.information(self, tr("Clipboard"), tr(
                "There is no image in the clipboard.\n\n"
                "Copy a sticker (right-click → Copy) or take a screenshot with Win+Shift+S."))
            return
        self.set_template(img)

    def load_template_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Image"), APP_DIR,
                                              tr("Images (*.png *.jpg *.jpeg *.bmp *.webp *.gif);;All files (*.*)"))
        if path:
            try:
                img = Image.open(path)
                img.load()
            except Exception as e:
                QMessageBox.critical(self, tr("Error"), str(e))
                return
            self.set_template(img)

    def clear_template(self):
        m = self.macro()
        if m:
            m["trigger"]["template"] = None
            m["anchor"] = None
            self.refresh_current_item()
            self.update_preview()
            self.update_labels()
            self.meter.set_values(None, m["trigger"]["threshold"], tr("Add an image first"))
            self.save()

    def _start_selector(self, title, on_result):
        if self.mode != "idle" or self._selecting:
            return
        self._selecting = True
        self.hide()

        def finished(res):
            self._selecting = False
            self.show()
            self.activateWindow()
            if res:
                on_result(res)

        def start():
            self.selector = RegionSelector(title)
            self.selector.finished.connect(finished)

        QTimer.singleShot(300, start)  # let the window disappear before taking the screenshot

    def capture_template(self):
        self._start_selector(tr("Select the image to search for"), lambda r: self.set_template(r[1]))

    def pick_region(self):
        def apply(res):
            m = self.macro()
            m["trigger"]["region"] = res[0]
            self.update_labels()
            self.save()
            x, y, w, h = res[0]
            self.log(tr("Search area: {w}×{h} at ({x}, {y})", w=w, h=h, x=x, y=y))
        self._start_selector(tr("Select the area to search in"), apply)

    def _region_mode(self, mode):
        m = self.macro()
        if not m:
            return
        if mode == "full":
            m["trigger"]["region"] = None
            self.update_labels()
            self.save()
        elif not m["trigger"]["region"]:
            self.seg_full.setChecked(True)  # until a region is actually selected
            self.pick_region()

    def flash(self, rect, color, label, ms=2200):
        f = FlashRect(rect, color, label)
        self._flashes.append(f)

        def drop():
            f.close()
            if f in self._flashes:
                self._flashes.remove(f)
        QTimer.singleShot(ms, drop)

    def test_match(self):
        m = self.macro()
        tpl = self.templates.get(m) if m else None
        if not tpl:
            QMessageBox.information(self, tr("Check"), tr("Add an image first"))
            return
        if self.mode != "idle" or self._selecting:
            return
        self._selecting = True
        self.hide()

        def run():
            t0 = time.perf_counter()
            try:
                score, rect, _ = core.find_template(tpl, m["trigger"]["region"], m["trigger"]["multiscale"])
            except Exception as e:
                self.log(tr("Search error: {err}", err=e))
                score, rect = 0.0, None
            self.bridge.test_result.emit(m, score, rect, (time.perf_counter() - t0) * 1000)

        QTimer.singleShot(250, lambda: threading.Thread(target=run, daemon=True).start())

    def _on_test_result(self, m, score, rect, ms):
        self._selecting = False
        self.show()
        self.activateWindow()
        thr = m["trigger"]["threshold"]
        ok = score * 100 >= thr
        if m is self.macro():
            self.meter.set_values(score, thr)
        self.log(tr("Check “{name}”: similarity {score}% (threshold {thr}%) — {result}, {ms} ms",
                    name=m["name"], score=f"{score * 100:.1f}", thr=thr,
                    result=tr("found") if ok else tr("not found"), ms=f"{ms:.0f}"))
        if m["trigger"]["region"]:
            self.flash(m["trigger"]["region"], ACCENT2, tr("search area"))
        if rect:
            self.flash(rect, GREEN if ok else ORANGE, f"{score * 100:.0f}%")

    def _on_meter(self, m, score):
        if m is self.macro():
            self.meter.set_values(score, m["trigger"]["threshold"])

    # ================= recording =================

    def toggle_record(self):
        if self.mode == "record":
            self.stop_record()
        elif self.mode == "idle":
            self.start_record()
        else:
            self.log(tr("Stop the current action first ({key}).", key=self.hk("stop")))

    def start_record(self):
        m = self.macro()
        if not m:
            return
        if m["events"] and QMessageBox.question(
                self, tr("Record"),
                tr("Overwrite the actions of macro “{name}”?", name=m["name"])) != QMessageBox.StandardButton.Yes:
            return
        self.rec_macro = m
        self.set_mode("record")
        self.showMinimized()
        self._show_hud(tr("Preparing to record…"), RED)
        QTimer.singleShot(450, self._begin_record)

    def _begin_record(self):
        m = self.rec_macro
        if self.mode != "record" or m is None:
            return
        anchor_msg = ""
        m["anchor"] = None
        tpl = self.templates.get(m)
        if tpl is not None:
            try:
                score, rect, scale = core.find_template(tpl, m["trigger"]["region"], m["trigger"]["multiscale"])
            except Exception:
                score, rect, scale = 0.0, None, 1.0
            pct = f"{score * 100:.0f}"
            if rect and score * 100 >= m["trigger"]["threshold"]:
                m["anchor"] = list(core.rect_center(rect))
                m["anchor_scale"] = scale
                anchor_msg = tr(" Image found ({score}%) — clicks will be anchored to it.", score=pct)
            else:
                anchor_msg = tr(" Image not on screen ({score}%) — no anchor.", score=pct)
        self.recorder.start(m["record_keyboard"])
        self._rec_timer.start()
        self._rec_tick()
        self.log(tr("Recording “{name}” started. {key} — stop.", name=m["name"], key=self.hk("record")) + anchor_msg)

    def _rec_tick(self):
        s = int(self.recorder.elapsed())
        self._show_hud(tr("REC  {time}   ·   {events}   ·   {key} — stop", key=self.hk("record"), time=f"{s // 60:02d}:{s % 60:02d}",
                          events=count(len(self.recorder.events), "event")), RED)

    def stop_record(self):
        if self.mode != "record":
            return
        self._rec_timer.stop()
        events = self.recorder.stop()
        m = self.rec_macro
        self.rec_macro = None
        if m is not None:
            m["events"] = events
        self.set_mode("idle")
        self.showNormal()
        self.activateWindow()
        self.update_labels()
        self.refresh_current_item()
        self.save()
        self.log(tr("Recording stopped: {events}.", events=count(len(events), "event")))

    # ================= playback =================

    def play_selected(self):
        if self.mode != "idle":
            return
        m = self.macro()
        if not m or not m["events"]:
            self.log(tr("No recorded actions in this macro — press “Record” first."))
            return
        self.set_mode("play")
        self.stop_event.clear()
        if self.tg_hide.isChecked():
            self.showMinimized()
        self.worker = threading.Thread(target=self._play_worker, args=(m,), daemon=True)
        self.worker.start()

    def _play_worker(self, m):
        n = 0
        missing = False  # log "not found" only when the state changes, not on every repeat
        try:
            time.sleep(0.3)
            repeats = m["repeats"]
            t = m["trigger"]
            tpl = self.templates.get(m) if t["enabled"] else None
            while not self.stop_event.is_set() and (repeats == 0 or n < repeats):
                n += 1
                transform = None
                if tpl is not None and (t["require"] or (t["relative"] and m.get("anchor"))):
                    score, rect, scale = core.find_template(tpl, t["region"], t["multiscale"])
                    pct = f"{score * 100:.0f}"
                    if score * 100 >= t["threshold"]:
                        transform = core.click_transform(m, rect, scale)
                        missing = False
                    elif t["require"]:
                        if not missing:
                            self.log(tr("Image for “{name}” not found ({score}%) — waiting for it, repeats are skipped.",
                                        name=m["name"], score=pct))
                        missing = True
                        self.bridge.hud.emit(tr("WAITING FOR IMAGE  “{name}”   ·   {key} — stop",
                                                name=m["name"], key=self.hk("stop")), ORANGE)
                        self.stop_event.wait(max(m["repeat_delay"], 0.5))
                        continue
                    elif not missing:
                        self.log(tr("Image for “{name}” not found ({score}%) — clicking at the recorded positions.",
                                    name=m["name"], score=pct))
                        missing = True
                progress = tr("{n} of {total}", n=n, total=repeats if repeats else "∞")
                self.bridge.hud.emit(tr("PLAYING  “{name}”   ·   {progress}   ·   {key} — stop",
                                        name=m["name"], progress=progress, key=self.hk("stop")), ACCENT2)
                self.player.run(m, transform)
                if repeats == 0 or n < repeats:
                    self.stop_event.wait(m["repeat_delay"])
            self.log(tr("Playback of “{name}” finished ({times}).", name=m["name"], times=count(n, "time")))
        except Exception as e:
            self.log(tr("Playback error: {err}", err=e))
        finally:
            self.bridge.finished.emit()

    # ================= monitoring =================

    def toggle_watch(self):
        if self.mode == "watch":
            self.stop_all()
            return
        if self.mode != "idle":
            return
        active = self._active_triggers()
        if not active:
            QMessageBox.information(self, tr("Monitoring"),
                                    tr("No macros with an enabled trigger, an image and recorded actions."))
            return
        self.set_mode("watch")
        self.stop_event.clear()
        if self.tg_hide.isChecked():
            self.showMinimized()
        interval = self.sp_interval.value() / 1000
        self.worker = threading.Thread(target=self._watch_worker, args=(active, interval), daemon=True)
        self.worker.start()
        self.log(tr("Monitoring started: {names}", names=quoted_names(active)))

    def _watch_worker(self, active, interval):
        state = {id(m): {"last": 0.0, "runs": 0, "armed": True} for m in active}
        fired = 0
        try:
            while not self.stop_event.is_set():
                pending = [m for m in active
                           if not m["trigger"]["max_runs"] or state[id(m)]["runs"] < m["trigger"]["max_runs"]]
                if not pending:
                    self.log(tr("All macros reached their run limit — monitoring stopped."))
                    break
                frame = core.grab_screen(None)  # one screenshot per cycle, shared by all macros
                parts = []
                for m in pending:
                    if self.stop_event.is_set():
                        break
                    t, st = m["trigger"], state[id(m)]
                    score, rect, scale = core.find_template(self.templates.get(m), t["region"], t["multiscale"],
                                                            frame=frame)
                    found = score * 100 >= t["threshold"]
                    if not found:
                        st["armed"] = True  # the image is gone: it may trigger again
                    self.bridge.meter.emit(m, score)
                    parts.append(f"{m['name']} {score * 100:.0f}%")
                    if found and st["armed"] and time.perf_counter() - st["last"] >= t["cooldown"]:
                        transform = core.click_transform(m, rect, scale)
                        fired += 1
                        st["runs"] += 1
                        msg = tr("Found “{name}” ({score}%) at ({x}, {y}) — running",
                                 name=m["name"], score=f"{score * 100:.1f}", x=rect[0], y=rect[1])
                        if transform:
                            msg += tr(", offset {offset}", offset=(transform[2] - transform[0], transform[3] - transform[1]))
                        self.log(msg)
                        self.bridge.hud.emit(tr("RUNNING  “{name}”   ·   {key} — stop",
                                                name=m["name"], key=self.hk("stop")), ACCENT2)
                        self.player.run(m, transform)
                        st["last"] = time.perf_counter()
                        if t["wait_gone"]:
                            st["armed"] = False
                        if t["max_runs"] and st["runs"] >= t["max_runs"]:
                            self.log(tr("“{name}” reached its limit of {n} runs.", name=m["name"], n=t["max_runs"]))
                        frame = core.grab_screen(None)  # the screen changed: fresh shot for the next macros
                self.bridge.hud.emit(tr("MONITORING   ·   {parts}   ·   fired: {n}   ·   {key} — stop",
                                        parts="  ·  ".join(parts), n=fired, key=self.hk("watch")), GREEN)
                self.stop_event.wait(interval)
        except Exception as e:
            self.log(tr("Monitoring error: {err}", err=e))
        finally:
            self.log(tr("Monitoring stopped. Triggered: {n}.", n=fired))
            self.bridge.finished.emit()

    # ================= stopping =================

    def stop_all(self):
        if self.mode == "record":
            self.stop_record()
            return
        self.stop_event.set()

    def _finish_worker(self):
        self.worker = None
        self.set_mode("idle")
        self.showNormal()
        self.activateWindow()

    def closeEvent(self, e):
        self.stop_event.set()
        if self.mode == "record":
            self.stop_record()
        self.save()
        try:
            self.kb_listener.stop()
        except Exception:
            pass
        self.hud.close()
        self.tray.hide()
        super().closeEvent(e)
        QApplication.quit()


def main():
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MacroStudio.App")
        except Exception:
            pass
    settings = load_settings()
    i18n.set_language(settings.get("language", "en"))
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI", 10))
    apply_qt_translator(i18n.language())
    win = MainWindow(settings)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
