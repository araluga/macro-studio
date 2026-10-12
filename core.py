"""Core: macro data, recording, playback and on-screen image search."""

import base64
import io
import json
import os
import subprocess
import tempfile
import threading
import time

import cv2
import mss
import numpy as np
from PIL import Image
from pynput import keyboard, mouse

_MSS = getattr(mss, "MSS", None) or mss.mss

MOVE_MIN_INTERVAL = 0.01  # record at most 100 mouse moves per second


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------

def new_macro(name):
    return {
        "name": name,
        "events": [],
        "anchor": None,          # template image center at the moment of recording
        "anchor_scale": 1.0,     # template scale at the moment of recording
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
            "wait_gone": True,   # after a run, wait until the image disappears before firing again
            "max_runs": 0,       # per monitoring session, 0 = unlimited
            "require": True,     # Play: skip a repeat when the image isn't on screen
        },
        "command": {
            "enabled": False,
            "text": "",          # cmd / PowerShell script written in advance
            "shell": "cmd",      # cmd | powershell
            "when": "after",     # before | after the recorded clicks
            "wait": True,        # wait for it to finish (output and exit code go to the log)
            "show": False,       # show a console window
        },
    }


def fix_macro(m):
    base = new_macro(m.get("name", "Macro"))
    nested = {key: {**base[key], **(m.get(key) or {})} for key in ("trigger", "command")}
    base.update(m)
    base.update(nested)
    return base


def has_command(m):
    c = m["command"]
    return bool(c["enabled"] and c["text"].strip())


def runnable(m):
    """A macro can run if it has recorded actions or a command."""
    return bool(m["events"]) or has_command(m)


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
    """Special keys by name, everything else by virtual-key code (layout- and modifier-independent)."""
    if isinstance(key, keyboard.Key):
        return "Key." + key.name
    if getattr(key, "vk", None) is not None:
        return "vk:" + str(key.vk)
    if getattr(key, "char", None):
        return "char:" + key.char
    return None


def str_to_key(s):
    if s.startswith("Key."):
        return keyboard.Key[s[4:]]
    if s.startswith("vk:"):
        return keyboard.KeyCode.from_vk(int(s[3:]))
    if s.startswith("char:"):  # recordings made before 1.1
        return keyboard.KeyCode.from_char(s[5:])
    raise ValueError(s)


# --------------------------------------------------------------------------
# Screen capture
# --------------------------------------------------------------------------

_tls = threading.local()


def _sct():
    """One mss instance per thread (mss handles are not thread-safe)."""
    sct = getattr(_tls, "sct", None)
    if sct is None:
        sct = _tls.sct = _MSS()
    return sct


def grab_screen(rect=None):
    """Screenshot of a rectangle (physical pixels) -> (BGR array, left, top)."""
    sct = _sct()
    if rect:
        mon = {"left": int(rect[0]), "top": int(rect[1]), "width": int(rect[2]), "height": int(rect[3])}
    else:
        mon = sct.monitors[0]  # the whole virtual screen (all monitors)
    shot = np.array(sct.grab(mon))[:, :, :3]
    return np.ascontiguousarray(shot), mon["left"], mon["top"]


def grab_pil(rect):
    raw = _sct().grab({"left": int(rect[0]), "top": int(rect[1]), "width": int(rect[2]), "height": int(rect[3])})
    return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")


# --------------------------------------------------------------------------
# Image search
# --------------------------------------------------------------------------

class Template:
    """Template prepared for OpenCV (BGR + transparency mask), with per-scale caching."""

    def __init__(self, pil_img):
        arr = np.array(pil_img.convert("RGBA"))
        self.bgr = cv2.cvtColor(arr[:, :, :3], cv2.COLOR_RGB2BGR)
        alpha = arr[:, :, 3]
        self.mask = None
        if alpha.min() < 250:
            # transparent pixels (e.g. a sticker background) are ignored
            m = (alpha > 127).astype(np.uint8) * 255
            self.mask = cv2.merge([m, m, m])
        self._scaled = {}

    def scaled(self, s):
        s = round(s, 3)
        if s == 1.0:
            return self.bgr, self.mask
        if s not in self._scaled:
            w = max(4, int(round(self.bgr.shape[1] * s)))
            h = max(4, int(round(self.bgr.shape[0] * s)))
            t = cv2.resize(self.bgr, (w, h), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
            m = None if self.mask is None else cv2.resize(self.mask, (w, h), interpolation=cv2.INTER_NEAREST)
            self._scaled[s] = (t, m)
        return self._scaled[s]


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


SCALES = [1.0, 0.9, 1.1, 0.8, 1.25, 0.7, 1.4, 0.6, 1.6, 0.5]


def _best_match(img, t, m):
    """Best TM_CCOEFF_NORMED score and location. Flat (zero-variance) areas give inf/NaN
    with a mask, and occasionally values above 1 — both are discarded, not clipped."""
    if t.shape[0] > img.shape[0] or t.shape[1] > img.shape[1]:
        return -1.0, None
    res = cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED, mask=m) if m is not None \
        else cv2.matchTemplate(img, t, cv2.TM_CCOEFF_NORMED)
    res[~np.isfinite(res) | (res > 1.0001)] = -1.0
    _, mx, _, loc = cv2.minMaxLoc(res)
    return min(float(mx), 1.0), loc


def _search(img, tpl, multiscale):
    """-> (score, (x, y, w, h) inside img, scale)"""
    if not multiscale:
        score, loc = _best_match(img, tpl.bgr, tpl.mask)
        th, tw = tpl.bgr.shape[:2]
        return score, (loc[0], loc[1], tw, th) if loc else None, 1.0

    # 1) coarse pass on a half-size frame over all scales
    th, tw = tpl.bgr.shape[:2]
    f = 0.5 if min(th, tw) * 0.5 * min(SCALES) >= 10 else 1.0
    small = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f < 1 else img
    coarse = (-1.0, None, 1.0)
    for s in SCALES:
        t, m = tpl.scaled(s * f)
        score, loc = _best_match(small, t, m)
        if loc and score > coarse[0]:
            coarse = (score, loc, s)
    if coarse[1] is None:
        return 0.0, None, 1.0

    # 2) refine at full resolution around the coarse hit with neighbouring scales
    _, (cx, cy), s0 = coarse
    best = (-1.0, None, s0)
    for s in (s0 * 0.94, s0 * 0.97, s0, s0 * 1.03, s0 * 1.06):
        t, m = tpl.scaled(s)
        h, w = t.shape[:2]
        pad = max(8, int(max(w, h) * 0.25))
        x1, y1 = max(0, int(cx / f) - pad), max(0, int(cy / f) - pad)
        x2, y2 = min(img.shape[1], int(cx / f) + w + pad), min(img.shape[0], int(cy / f) + h + pad)
        score, loc = _best_match(img[y1:y2, x1:x2], t, m)
        if loc and score > best[0]:
            best = (score, (x1 + loc[0], y1 + loc[1], w, h), s)
    return best


def find_template(tpl, region=None, multiscale=False, frame=None):
    """Returns (similarity 0..1, (x, y, w, h) in screen coordinates or None, scale).

    frame: optional (BGR array, left, top) of an already captured screen, so several
    macros can be checked against one screenshot."""
    if frame is None:
        img, ox, oy = grab_screen(region)
    else:
        full, fx, fy = frame
        if region:
            x1, y1 = max(0, region[0] - fx), max(0, region[1] - fy)
            x2 = min(full.shape[1], region[0] + region[2] - fx)
            y2 = min(full.shape[0], region[1] + region[3] - fy)
            img, ox, oy = full[y1:y2, x1:x2], fx + x1, fy + y1
        else:
            img, ox, oy = full, fx, fy
    if img.size == 0:
        return 0.0, None, 1.0
    score, rect, scale = _search(img, tpl, multiscale)
    if rect is None:
        return 0.0, None, 1.0
    return max(score, 0.0), (rect[0] + ox, rect[1] + oy, rect[2], rect[3]), scale


def rect_center(rect):
    return rect[0] + rect[2] // 2, rect[1] + rect[3] // 2


def click_transform(m, rect, scale):
    """Maps recorded coordinates to where the image is now: shift by the anchor movement and,
    for multi-scale matches, scale the distance from the anchor by the size change."""
    if not m["trigger"]["relative"] or not m.get("anchor") or not rect:
        return None
    ax, ay = m["anchor"]
    cx, cy = rect_center(rect)
    k = scale / (m.get("anchor_scale") or 1.0) if m["trigger"]["multiscale"] else 1.0
    return ax, ay, cx, cy, k


# --------------------------------------------------------------------------
# Terminal commands
# --------------------------------------------------------------------------

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
_CMD_DIR = os.path.join(tempfile.gettempdir(), "MacroStudio")


def match_env(m, score=None, rect=None):
    """Environment variables a command can use: %MATCH_X% in cmd, $env:MATCH_X in PowerShell."""
    env = {"MACRO_NAME": m["name"], "MATCH_FOUND": "0", "MATCH_X": "", "MATCH_Y": "",
           "MATCH_W": "", "MATCH_H": "", "MATCH_SCORE": ""}
    if rect:
        cx, cy = rect_center(rect)
        env.update(MATCH_FOUND="1", MATCH_X=str(cx), MATCH_Y=str(cy), MATCH_W=str(rect[2]),
                   MATCH_H=str(rect[3]), MATCH_SCORE=f"{score * 100:.1f}" if score is not None else "")
    return env


def _script_file(cfg):
    """Writes the command into a temporary .cmd/.ps1 so multi-line scripts and Unicode work."""
    os.makedirs(_CMD_DIR, exist_ok=True)
    if cfg["shell"] == "powershell":
        body = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8\n"
                "$OutputEncoding = [Text.Encoding]::UTF8\n" + cfg["text"])
        fd, path = tempfile.mkstemp(suffix=".ps1", dir=_CMD_DIR)
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:  # PowerShell 5 needs the BOM for Unicode
            f.write(body)
        args = ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path]
    else:
        text = cfg["text"].replace("\r\n", "\n").replace("\n", "\r\n")
        body = "@echo off\r\nchcp 65001 >nul\r\n" + text + "\r\n"
        fd, path = tempfile.mkstemp(suffix=".cmd", dir=_CMD_DIR)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(body)
        args = ["cmd.exe", "/d", "/c", path]
    return path, args


def _remove_later(proc, path):
    def wait_and_remove():
        proc.wait()
        try:
            os.remove(path)
        except OSError:
            pass
    threading.Thread(target=wait_and_remove, daemon=True).start()


def kill_tree(proc):
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True,
                   creationflags=CREATE_NO_WINDOW)


def run_command(cfg, env_extra, stop_event, log):
    """Runs the macro's command. Returns the exit code, or None if it wasn't waited for.

    log(kind, value) receives ("started", pid), ("output", line), ("exit", code), ("killed", None)."""
    path, args = _script_file(cfg)
    env = {**os.environ, **env_extra}
    flags = CREATE_NEW_CONSOLE if cfg["show"] else CREATE_NO_WINDOW
    capture = cfg["wait"] and not cfg["show"]
    proc = subprocess.Popen(args, cwd=os.path.expanduser("~"), env=env, creationflags=flags,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                            stderr=subprocess.STDOUT if capture else subprocess.DEVNULL)
    _remove_later(proc, path)
    log("started", proc.pid)
    if not cfg["wait"]:
        return None
    out = b""
    while True:
        try:
            chunk, _ = proc.communicate(timeout=0.2)
            out += chunk or b""
            break
        except subprocess.TimeoutExpired:
            if stop_event.is_set():
                kill_tree(proc)
                proc.wait()
                log("killed", None)
                return None
    for line in out.decode("utf-8", errors="replace").splitlines()[-20:]:
        if line.strip():
            log("output", line[:300])
    log("exit", proc.returncode)
    return proc.returncode


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
        if not (self.active and self.record_keyboard):
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

    def run(self, m, transform=None):
        """transform: (anchor_x, anchor_y, now_x, now_y, scale) from click_transform(), or None."""
        if transform:
            ax, ay, cx, cy, k = transform

            def pos(x, y):
                return int(round(cx + (x - ax) * k)), int(round(cy + (y - ay) * k))
        else:
            def pos(x, y):
                return x, y

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
                    self.mouse.position = pos(ev[2], ev[3])
                elif kind == "c":
                    self.mouse.position = pos(ev[2], ev[3])
                    btn = getattr(mouse.Button, ev[4], mouse.Button.left)
                    if ev[5]:
                        self.mouse.press(btn)
                        pressed_buttons.add(btn)
                    else:
                        self.mouse.release(btn)
                        pressed_buttons.discard(btn)
                elif kind == "s":
                    self.mouse.position = pos(ev[2], ev[3])
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
