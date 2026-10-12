"""Core: macro data, recording, playback and on-screen image search."""

import base64
import io
import json
import os
import threading
import time

import cv2
import mss
import numpy as np
from PIL import Image
from pynput import keyboard, mouse

_MSS = getattr(mss, "MSS", None) or mss.mss

HOTKEY_RECORD = keyboard.Key.f9
HOTKEY_PLAY = keyboard.Key.f10
HOTKEY_WATCH = keyboard.Key.f11
HOTKEY_STOP = keyboard.Key.f12
HOTKEYS = {HOTKEY_RECORD, HOTKEY_PLAY, HOTKEY_WATCH, HOTKEY_STOP}

MOVE_MIN_INTERVAL = 0.01  # record at most 100 mouse moves per second


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

def new_macro(name):
    return {
        "name": name,
        "events": [],
        "anchor": None,          # template image center at the moment of recording
        "repeats": 1,            # 0 = forever
        "speed": 1.0,
        "repeat_delay": 0.5,
        "skip_moves": False,
        "record_keyboard": False,
        "trigger": {
            "enabled": False,
            "template": None,    # PNG as base64
            "region": None,      # [left, top, width, height] or None = full screen
            "threshold": 85,     # %
            "relative": True,
            "multiscale": False,
            "cooldown": 2.0,
        },
    }


def fix_macro(m):
    base = new_macro(m.get("name", "Macro"))
    trig = base["trigger"]
    trig.update(m.get("trigger", {}))
    base.update(m)
    base["trigger"] = trig
    return base


def load_macros(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [fix_macro(m) for m in data.get("macros", [])]


def save_macros(path, macros, indent=None):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"macros": macros}, f, ensure_ascii=False, indent=indent)
    os.replace(tmp, path)


def macro_stats(m):
    ev = m["events"]
    duration = ev[-1][0] if ev else 0.0
    clicks = sum(1 for e in ev if e[1] == "c" and e[5])
    return len(ev), clicks, duration


def image_to_b64(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def b64_to_image(data):
    img = Image.open(io.BytesIO(base64.b64decode(data)))
    img.load()
    return img


def key_to_str(key):
    if isinstance(key, keyboard.Key):
        return "Key." + key.name
    if getattr(key, "char", None):
        return "char:" + key.char
    if getattr(key, "vk", None) is not None:
        return "vk:" + str(key.vk)
    return None


def str_to_key(s):
    if s.startswith("Key."):
        return keyboard.Key[s[4:]]
    if s.startswith("char:"):
        return keyboard.KeyCode.from_char(s[5:])
    if s.startswith("vk:"):
        return keyboard.KeyCode.from_vk(int(s[3:]))
    raise ValueError(s)


# --------------------------------------------------------------------------
# Image search
# --------------------------------------------------------------------------

class Template:
    """Template prepared for OpenCV (BGR + transparency mask)."""

    def __init__(self, pil_img):
        arr = np.array(pil_img.convert("RGBA"))
        self.bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        alpha = arr[:, :, 3]
        self.mask = None
        if alpha.min() < 250:
            # transparent pixels (e.g. a sticker background) are ignored
            m = (alpha > 127).astype(np.uint8) * 255
            self.mask = cv2.merge([m, m, m])


class TemplateCache:
    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, m):
        b64 = m["trigger"]["template"]
        if not b64:
            return None
        with self._lock:
            cached = self._cache.get(id(m))
            if cached and cached[0] is b64:
                return cached[1]
            tpl = Template(b64_to_image(b64))
            self._cache[id(m)] = (b64, tpl)
            return tpl


def grab_screen(rect=None):
    """Screenshot of a rectangle (physical pixels) -> (BGR array, left, top)."""
    with _MSS() as sct:
        if rect:
            mon = {"left": int(rect[0]), "top": int(rect[1]),
                   "width": int(rect[2]), "height": int(rect[3])}
        else:
            mon = sct.monitors[0]  # the whole virtual screen (all monitors)
        shot = np.array(sct.grab(mon))[:, :, :3]
        return np.ascontiguousarray(shot), mon["left"], mon["top"]


def grab_pil(rect):
    with _MSS() as sct:
        raw = sct.grab({"left": int(rect[0]), "top": int(rect[1]),
                        "width": int(rect[2]), "height": int(rect[3])})
        return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


SCALES = [1.0, 0.9, 1.1, 0.8, 1.25, 0.7, 1.4, 0.6, 1.6, 0.5]


def find_template(tpl, region=None, multiscale=False):
    """Returns (similarity 0..1, (x, y, w, h) of the best match in screen coordinates)."""
    shot, ox, oy = grab_screen(region)
    best_score, best_rect = -1.0, None
    for s in (SCALES if multiscale else [1.0]):
        if s == 1.0:
            t, m = tpl.bgr, tpl.mask
        else:
            w = max(4, int(tpl.bgr.shape[1] * s))
            h = max(4, int(tpl.bgr.shape[0] * s))
            t = cv2.resize(tpl.bgr, (w, h), interpolation=cv2.INTER_AREA)
            m = None if tpl.mask is None else cv2.resize(tpl.mask, (w, h), interpolation=cv2.INTER_NEAREST)
        th, tw = t.shape[:2]
        if th > shot.shape[0] or tw > shot.shape[1]:
            continue
        if m is not None:
            res = cv2.matchTemplate(shot, t, cv2.TM_CCOEFF_NORMED, mask=m)
        else:
            res = cv2.matchTemplate(shot, t, cv2.TM_CCOEFF_NORMED)
        res = np.nan_to_num(res, nan=-1.0, posinf=-1.0, neginf=-1.0)
        _, mx, _, loc = cv2.minMaxLoc(res)
        if mx > best_score:
            best_score = mx
            best_rect = (loc[0] + ox, loc[1] + oy, tw, th)
    return max(best_score, 0.0), best_rect


def rect_center(rect):
    return rect[0] + rect[2] // 2, rect[1] + rect[3] // 2


def click_offset(m, rect):
    """Click offset: where the image is now minus where it was during recording."""
    if not m["trigger"]["relative"] or not m.get("anchor") or not rect:
        return 0, 0
    cx, cy = rect_center(rect)
    return cx - m["anchor"][0], cy - m["anchor"][1]


# --------------------------------------------------------------------------
# Recording
# --------------------------------------------------------------------------

class Recorder:
    def __init__(self):
        self.events = []
        self.active = False
        self.record_keyboard = False
        self._start = 0.0
        self._last_move = 0.0
        self._listener = None

    def elapsed(self):
        return time.perf_counter() - self._start if self.active else 0.0

    def _t(self):
        return round(time.perf_counter() - self._start, 4)

    def start(self, record_keyboard):
        self.events = []
        self.record_keyboard = record_keyboard
        self._start = time.perf_counter()
        self._last_move = 0.0
        self.active = True
        self._listener = mouse.Listener(on_move=self._move, on_click=self._click, on_scroll=self._scroll)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        self.active = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        events, self.events = self.events, []
        return events

    def _move(self, x, y):
        now = time.perf_counter()
        if self.active and now - self._last_move >= MOVE_MIN_INTERVAL:
            self._last_move = now
            self.events.append([self._t(), "m", int(x), int(y)])

    def _click(self, x, y, button, pressed):
        if self.active:
            self.events.append([self._t(), "c", int(x), int(y), button.name, bool(pressed)])

    def _scroll(self, x, y, dx, dy):
        if self.active:
            self.events.append([self._t(), "s", int(x), int(y), int(dx), int(dy)])

    def key(self, key, pressed):
        if not (self.active and self.record_keyboard) or key in HOTKEYS:
            return
        s = key_to_str(key)
        if s:
            self.events.append([self._t(), "k", s, pressed])


# --------------------------------------------------------------------------
# Playback
# --------------------------------------------------------------------------

class Player:
    def __init__(self, stop_event):
        self.stop_event = stop_event
        self.mouse = mouse.Controller()
        self.kb = keyboard.Controller()

    def run(self, m, offset=(0, 0)):
        dx, dy = offset
        speed = max(0.05, float(m["speed"]))
        skip_moves = m["skip_moves"]
        pressed_buttons, pressed_keys = set(), set()
        start = time.perf_counter()
        try:
            for ev in m["events"]:
                if self.stop_event.is_set():
                    break
                kind = ev[1]
                if kind == "m" and skip_moves:
                    continue
                delay = start + ev[0] / speed - time.perf_counter()
                if delay > 0 and self.stop_event.wait(delay):
                    break
                if kind == "m":
                    self.mouse.position = (ev[2] + dx, ev[3] + dy)
                elif kind == "c":
                    self.mouse.position = (ev[2] + dx, ev[3] + dy)
                    btn = getattr(mouse.Button, ev[4], mouse.Button.left)
                    if ev[5]:
                        self.mouse.press(btn)
                        pressed_buttons.add(btn)
                    else:
                        self.mouse.release(btn)
                        pressed_buttons.discard(btn)
                elif kind == "s":
                    self.mouse.position = (ev[2] + dx, ev[3] + dy)
                    self.mouse.scroll(ev[4], ev[5])
                elif kind == "k":
                    try:
                        key = str_to_key(ev[2])
                    except Exception:
                        continue
                    if ev[3]:
                        self.kb.press(key)
                        pressed_keys.add(key)
                    else:
                        self.kb.release(key)
                        pressed_keys.discard(key)
        finally:
            # don't leave buttons/keys held down if stopped midway
            for b in pressed_buttons:
                self.mouse.release(b)
            for k in pressed_keys:
                self.kb.release(k)
