# -*- coding: utf-8 -*-
"""鍵盤快速鍵系統（仿 MATLAB Preferences ▸ Keyboard ▸ Shortcuts）：
每個「動作」（action）有 id、名稱、分類、預設快速鍵；使用者可以替任何動作加／刪快速鍵，存在設定檔的 "shortcuts" 裡
（只存跟預設不一樣的動作），也能匯出／匯入 JSON（MATLAB 的 key-set 檔）。

快速鍵用字串表示（規格字串）："Cmd+Shift+Z"、"Ctrl+Y"、"F5"、"Home"、"Plus"、"Delete"、"Left"。
- 修飾鍵固定順序 Ctrl、Alt、Shift、Cmd；"Mod" 是「主修飾鍵」：macOS 是 Cmd、其他是 Ctrl（預設表用 Mod，
  存檔與比對前用 canonical() 換成實際的）。
- 鍵名：字母大寫 A–Z、數字 0–9、F1–F24，其餘用 Tk keysym 的名字（首字大寫；對照表 KEYSYM_NAMES）。
- 顯示：macOS 用 ⌃⌥⇧⌘ 符號（"⌘⇧Z"），其他 "Ctrl+Shift+Z"。
這個模組不依賴 tkinter（from_tk_event 只讀 event 的 keysym／keycode／state），可以 headless 測試；實體按鍵的對照表在 plotkit/keys.py
（plotkit 的圖片視窗、輸入框也用同一份）。"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from plotkit import keys as _pkeys

PLATFORM = "mac" if sys.platform == "darwin" else ("win" if sys.platform.startswith("win") else "linux")
MOD_ORDER = ("Ctrl", "Alt", "Shift", "Cmd")
MOD_ALIASES = {"ctrl": "Ctrl", "control": "Ctrl", "ctl": "Ctrl", "alt": "Alt", "option": "Alt", "opt": "Alt", "shift": "Shift",
               "cmd": "Cmd", "command": "Cmd", "meta": "Cmd", "super": "Cmd", "win": "Cmd", "mod": "Mod", "primary": "Mod"}
MAC_SYMBOLS = {"Ctrl": "⌃", "Alt": "⌥", "Shift": "⇧", "Cmd": "⌘"}
# Tk keysym → 鍵名（keysym 本身不在表裡就首字大寫；單一字母大寫；數字照用）
KEYSYM_NAMES = {
    "plus": "Plus", "KP_Add": "Plus", "minus": "Minus", "KP_Subtract": "Minus", "equal": "Equal", "underscore": "Underscore",
    "bracketleft": "BracketLeft", "bracketright": "BracketRight", "braceleft": "BraceLeft", "braceright": "BraceRight",
    "comma": "Comma", "period": "Period", "slash": "Slash", "backslash": "Backslash", "semicolon": "Semicolon",
    "apostrophe": "Quote", "quoteright": "Quote", "grave": "Grave", "quoteleft": "Grave", "space": "Space",
    "Prior": "PageUp", "Next": "PageDown", "Return": "Return", "KP_Enter": "Return", "Escape": "Escape", "Tab": "Tab",
    "BackSpace": "BackSpace", "Delete": "Delete", "Home": "Home", "End": "End", "Left": "Left", "Right": "Right",
    "Up": "Up", "Down": "Down", "Insert": "Insert", "less": "Less", "greater": "Greater", "question": "Question",
    "exclam": "Exclam", "at": "At", "numbersign": "NumberSign", "dollar": "Dollar", "percent": "Percent",
    "asciicircum": "Caret", "ampersand": "Ampersand", "asterisk": "Asterisk", "parenleft": "ParenLeft", "parenright": "ParenRight",
    "KP_Multiply": "Asterisk", "KP_Divide": "Slash", "KP_Decimal": "Period",
}
# 鍵名 → 顯示字（沒有的直接顯示鍵名）
KEY_LABELS = {"Plus": "+", "Minus": "-", "Equal": "=", "Underscore": "_", "BracketLeft": "[", "BracketRight": "]", "BraceLeft": "{",
              "BraceRight": "}", "Comma": ",", "Period": ".", "Slash": "/", "Backslash": "\\", "Semicolon": ";", "Quote": "'",
              "Grave": "`", "Less": "<", "Greater": ">", "Question": "?", "Exclam": "!", "At": "@", "NumberSign": "#", "Dollar": "$",
              "Percent": "%", "Caret": "^", "Ampersand": "&", "Asterisk": "*", "ParenLeft": "(", "ParenRight": ")",
              "Space": "Space", "BackSpace": "⌫", "Delete": "⌦", "Return": "↩", "Escape": "Esc", "Left": "←", "Right": "→",
              "Up": "↑", "Down": "↓", "PageUp": "PgUp", "PageDown": "PgDn"}
KEY_LABELS_WIN = dict(KEY_LABELS, BackSpace="Backspace", Delete="Del", Return="Enter", Left="Left", Right="Right", Up="Up", Down="Down")
# 鍵名 → matplotlib 的 key 名（Interactor 收到的 key_press_event.key 的最後一段）
MPL_KEY = {"Plus": "+", "Minus": "-", "Equal": "=", "BracketLeft": "[", "BracketRight": "]", "Comma": ",", "Period": ".", "Slash": "/",
           "Backslash": "\\", "Semicolon": ";", "Quote": "'", "Grave": "`", "Space": " ", "BackSpace": "backspace", "Delete": "delete",
           "Return": "enter", "Escape": "escape", "Left": "left", "Right": "right", "Up": "up", "Down": "down", "Home": "home",
           "End": "end", "PageUp": "pageup", "PageDown": "pagedown", "Tab": "tab", "Insert": "insert", "Underscore": "_",
           "Less": "<", "Greater": ">", "Question": "?", "Exclam": "!", "At": "@", "NumberSign": "#", "Dollar": "$", "Percent": "%",
           "Caret": "^", "Ampersand": "&", "Asterisk": "*", "ParenLeft": "(", "ParenRight": ")", "BraceLeft": "{", "BraceRight": "}"}
# 修飾鍵在 Tk event.state 的位元（matplotlib backend_tk._mpl_modifiers 同一套）
STATE_BITS = {
    "mac": (("Ctrl", 1 << 2), ("Alt", 1 << 4), ("Shift", 1 << 0), ("Cmd", 1 << 3)),
    "win": (("Ctrl", 1 << 2), ("Alt", 1 << 17), ("Shift", 1 << 0)),
    "linux": (("Ctrl", 1 << 2), ("Alt", 1 << 3), ("Shift", 1 << 0), ("Cmd", 1 << 6)),
}
# 輸入框有焦點時放給它自己處理的鍵：沒有修飾鍵的（打字）、以及文字編輯慣用組合
TEXT_EDIT_KEYS = {"A", "C", "V", "X", "Z", "Y"}
# 非拉丁文字的輸入法（注音 com.apple.keylayout.ZhuyinBopomofo、俄文、希臘文…）之下，Tk 8.6.13 照目前的配置把按鍵翻成字（V 鍵＝ㄒ、[ 鍵＝「），
# 那些字沒有 keysym 或是別的 keysym：⌘V 的 keysym 是 "??"、[ 是 kana_openingbracket、- 是 "??"，快速鍵都對不到（2026-10-26 第 13 項、
# 10-27 第二次選單「全部都修」）。照按鍵的實體位置（ABC 配置）認，和 macOS 的 App 一樣（注音之下 ⌘C 照樣是複製、[ 照樣是上一個轉態）。
# 對照表與規則在 plotkit/keys.py（這裡的名字留著給舊的呼叫端與測試）。
MAC_ANSI_KEYSYMS = _pkeys.MAC_ANSI_KEYSYMS
NON_LATIN_KEYSYM_PREFIXES = _pkeys.NON_LATIN_KEYSYM_PREFIXES
keysym_not_latin = _pkeys.keysym_not_latin


class KeySpecError(ValueError):
    pass


def primary_mod(platform: str = PLATFORM) -> str:
    return "Cmd" if platform == "mac" else "Ctrl"


def key_name_from_keysym(keysym: str) -> str:
    if not keysym:
        return ""
    if keysym in KEYSYM_NAMES:
        return KEYSYM_NAMES[keysym]
    if len(keysym) == 1:
        return keysym.upper() if keysym.isalpha() else keysym
    if keysym.startswith("KP_") and len(keysym) == 4 and keysym[3].isdigit():
        return keysym[3]
    if keysym[0] == "F" and keysym[1:].isdigit():
        return keysym
    return keysym[0].upper() + keysym[1:]


def parse(spec: str, platform: str = PLATFORM) -> Tuple[Tuple[str, ...], str]:
    """規格字串 → (修飾鍵 tuple（固定順序）, 鍵名)。接受大小寫與別名；"Mod" 換成平台主修飾鍵。鍵名空或不認得的修飾鍵就 KeySpecError。"""
    if not isinstance(spec, str) or not spec.strip():
        raise KeySpecError("空的快速鍵")
    text = spec.strip().replace(" ", "")
    if text.endswith("+"):                      # "Ctrl++"／"+" ＝ 最後那個鍵是 +
        text = text[:-1] + "Plus"
    parts = text.split("+")
    if not parts or parts[-1] == "":
        raise KeySpecError(spec)
    key = parts[-1]
    mods = set()
    for m in parts[:-1]:
        name = MOD_ALIASES.get(m.lower())
        if name is None:
            raise KeySpecError(f"不認得的修飾鍵：{m}")
        mods.add(primary_mod(platform) if name == "Mod" else name)
    kname = key_name_from_keysym(key) if key not in KEY_LABELS else key
    if kname.lower() in MOD_ALIASES:
        raise KeySpecError("只有修飾鍵")
    if kname == "+":
        kname = "Plus"
    return tuple(m for m in MOD_ORDER if m in mods), kname


def canonical(spec: str, platform: str = PLATFORM) -> str:
    mods, key = parse(spec, platform)
    return "+".join(mods + (key,))


def label(spec: str, platform: str = PLATFORM) -> str:
    """給人看的字：mac "⌘⇧Z"、"⌃Y"、"F5"、"←"；其他 "Ctrl+Shift+Z"、"Ctrl+Y"、"Left"。"""
    try:
        mods, key = parse(spec, platform)
    except KeySpecError:
        return str(spec)
    if platform == "mac":
        return "".join(MAC_SYMBOLS[m] for m in mods) + KEY_LABELS.get(key, key)
    return "+".join(list(mods) + [KEY_LABELS_WIN.get(key, key)])


def labels(specs: Iterable[str], platform: str = PLATFORM) -> str:
    return ", ".join(label(s, platform) for s in specs)      # ASCII 逗號：英文介面也用


def mods_from_state(state: int, platform: str = PLATFORM) -> Tuple[str, ...]:
    try:
        st = int(state)
    except Exception:
        return ()
    have = {name for name, bit in STATE_BITS.get(platform, STATE_BITS["linux"]) if st & bit}
    return tuple(m for m in MOD_ORDER if m in have)


def mac_physical_keysym(event) -> Optional[str]:
    """macOS 的 Tk 按鍵事件 → 這顆實體按鍵在 ABC（美式）配置下的 keysym（看 Shift）；不是字母、數字、符號鍵（或 keycode 不是整數）回 None。
    Tk 的 keycode（%k）＝ 虛擬鍵碼 << 24 | Option／Shift << 22 | 字元（tkMacOSXPrivate.h 的 MacKeycode）。"""
    return _pkeys.physical_keysym(event, "mac")


_MODIFIER_KEYSYMS = ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R",
                     "Super_L", "Super_R", "Caps_Lock", "Num_Lock", "Mode_switch", "ISO_Level3_Shift", "??")


def _spec_from(keysym: str, event, platform: str) -> Optional[str]:
    if not keysym or keysym in _MODIFIER_KEYSYMS:
        return None
    mods = mods_from_state(getattr(event, "state", 0), platform)
    key = key_name_from_keysym(keysym)
    if len(key) == 1 and key.isalpha():
        key = key.upper()
    return "+".join(mods + (key,))


def from_tk_event(event, platform: str = PLATFORM) -> Optional[str]:
    """Tk <Key> 事件 → 規格字串；修飾鍵本身（只按 Shift）回 None。
    macOS 上目前的輸入法給的不是 ABC 會給的 keysym（注音之下 ⌘V 是 "??"、[ 是 kana_openingbracket、- 是 "??"）：照按鍵的實體位置
    （ABC 配置）認，⌘V 就是 Cmd+V、[ 就是 BracketLeft（plotkit.keys.latin_keysym；只按 Option 打的特殊字照舊）。
    2026-10-26 第 13 項先修了 ⌘／⌃ 的組合鍵；10-27 使用者第二次選單「全部都修」：沒按 ⌘ 的 [ ]、⇧[ ⇧]、- 也照實體按鍵認；
    第五次選單 3：注音的 3、7、` 鍵（Tk 給拉丁名字的 caron、abovedot、periodcentered）也照實體按鍵認成 3、7、Grave。
    ABC 之下 Tk 給的本來就是這些 keysym，什麼都不變。"""
    return _spec_from(_pkeys.latin_keysym(event, platform), event, platform)


# 按 Shift 的符號（ABC 美式配置同一顆鍵）→ 不按 Shift 的那個字的鍵名：BraceLeft → BracketLeft（{ 與 [ 同一顆）、Plus → Equal…
SHIFTED_SYMBOL_BASE = {key_name_from_keysym(hi): key_name_from_keysym(lo) for lo, hi in MAC_ANSI_KEYSYMS.values()
                       if not (len(hi) == 1 and hi.isalpha())}


def shifted_symbol_alternative(spec: str, platform: str = PLATFORM) -> Optional[str]:
    """按著 Shift 的符號鍵：Tk 給的是按 Shift 之後的字（⇧[ 的 keysym 是 braceleft → "Shift+BraceLeft"），預設快速鍵寫的是
    「Shift＋那顆鍵」（⇧[＝"Shift+BracketLeft"）。回傳後者（同一顆鍵、不按 Shift 的字），不是這種按鍵回 None。
    主視窗的分派器在 spec 沒綁任何動作時再用這個試一次（2026-10-27：⇧[／⇧] 上一個／下一個差異以前在 ABC、Windows 之下也對不到；
    使用者自己錄的 ⇧{ 照樣優先）。"""
    try:
        mods, key = parse(spec, platform)
    except KeySpecError:
        return None
    base = SHIFTED_SYMBOL_BASE.get(key)
    if base is None or "Shift" not in mods:
        return None
    return "+".join(mods + (base,))


def shifted_symbol_alternatives(spec: str, platform: str = PLATFORM) -> List[str]:
    """按著 Shift 的符號鍵，spec 本身沒綁任何動作時照順序可以再試的規格：先「Shift＋那顆鍵不按 Shift 的字」（⇧[ → "Shift+BracketLeft"，
    shifted_symbol_alternative），再「那個符號本身、不帶 Shift」（⇧= 的 keysym 是 plus → "Shift+Plus" → "Plus"：預設的「放大」寫的是 Plus，
    以前在圖以外從來對不到，ABC 與注音一樣——2026-10-27 使用者第七次選單 2）。不是這種按鍵回空清單。"""
    alt = shifted_symbol_alternative(spec, platform)
    if alt is None:
        return []
    mods, key = parse(spec, platform)
    plain = "+".join(tuple(m for m in mods if m != "Shift") + (key,))
    return [alt, plain]


def to_mpl_key(spec: str, platform: str = PLATFORM) -> Optional[str]:
    """規格字串 → matplotlib key_press_event.key 的寫法（"ctrl+alt+shift+cmd+key"，小寫）。"""
    try:
        mods, key = parse(spec, platform)
    except KeySpecError:
        return None
    k = MPL_KEY.get(key)
    if k is None:
        k = key.lower() if (len(key) == 1 or key[0] == "F" and key[1:].isdigit()) else key.lower()
    names = {"Ctrl": "ctrl", "Alt": "alt", "Shift": "shift", "Cmd": "cmd" if platform == "mac" else "super"}
    return "+".join([names[m] for m in mods] + [k])


def is_text_edit_key(spec: str, platform: str = PLATFORM) -> bool:
    """輸入框有焦點時要放行的鍵：沒修飾鍵或只有 Shift（打字、方向鍵、Delete…）、主修飾鍵＋A/C/V/X/Z/Y、Shift+主修飾鍵+Z。"""
    try:
        mods, key = parse(spec, platform)
    except KeySpecError:
        return True
    if key[0] == "F" and key[1:].isdigit():
        return False                # F 鍵不是打字
    non_shift = tuple(m for m in mods if m != "Shift")
    if not non_shift:
        return True
    if non_shift == (primary_mod(platform),) and key in TEXT_EDIT_KEYS and ("Shift" not in mods or key == "Z"):
        return True                 # ⌘C／⌘V／⌘Z／⌘⇧Z…交給輸入框；⌘⇧C 這類不是文字編輯鍵
    if platform == "mac" and non_shift == ("Ctrl",) and key in ("A", "E", "K", "D", "H", "F", "B", "N", "P"):
        return True                 # macOS 輸入框的 emacs 鍵
    return False


@dataclass
class Action:
    id: str
    label: str
    group: str
    run: Callable[[], object]
    default: Tuple[str, ...] = ()
    enabled: Optional[Callable[[], bool]] = None
    scope: str = "app"              # "app"＝整個主視窗；"plot"＝圖上（由 Interactor 處理，鍵名要能換成 matplotlib 的）

    def is_enabled(self) -> bool:
        try:
            return bool(self.enabled()) if self.enabled is not None else True
        except Exception:
            return True


class Keymap:
    """動作 → 快速鍵清單。defaults 以 action id 為鍵（規格字串可含 Mod）；overrides 只記跟預設不一樣的動作（canonical 後）。"""
    VERSION = 1

    def __init__(self, defaults: Dict[str, Sequence[str]], platform: str = PLATFORM,
                 aliases: Optional[Dict[str, str]] = None):
        self.platform = platform
        self.defaults: Dict[str, Tuple[str, ...]] = {}
        for aid, specs in defaults.items():
            self.defaults[aid] = self._clean(specs)
        self.overrides: Dict[str, Tuple[str, ...]] = {}
        # 改過名／合併掉的動作 id → 現在的 id：舊設定檔裡綁在舊 id 上的快速鍵套到新 id（兩個都有就合併，不會讓舊鍵失效）
        self.aliases: Dict[str, str] = {a: b for a, b in (aliases or {}).items() if b in self.defaults}

    def _clean(self, specs) -> Tuple[str, ...]:
        out: List[str] = []
        for s in (specs or ()):
            try:
                c = canonical(s, self.platform)
            except KeySpecError:
                continue
            if c not in out:
                out.append(c)
        return tuple(out)

    # --- 查 -------------------------------------------------------------------
    def actions(self) -> List[str]:
        return list(self.defaults)

    def bindings(self, action: str) -> Tuple[str, ...]:
        return self.overrides.get(action, self.defaults.get(action, ()))

    def is_default(self, action: str) -> bool:
        return action not in self.overrides

    def lookup(self, spec: str) -> List[str]:
        """這個快速鍵綁了哪些動作（通常 0 或 1 個；衝突時多個）。"""
        try:
            c = canonical(spec, self.platform)
        except KeySpecError:
            return []
        return [a for a in self.defaults if c in self.bindings(a)]

    def table(self) -> Dict[str, List[str]]:
        """快速鍵 → 動作清單（所有有綁的）。"""
        out: Dict[str, List[str]] = {}
        for a in self.defaults:
            for s in self.bindings(a):
                out.setdefault(s, []).append(a)
        return out

    def conflicts(self) -> Dict[str, List[str]]:
        return {s: acts for s, acts in self.table().items() if len(acts) > 1}

    # --- 改 -------------------------------------------------------------------
    def set(self, action: str, specs: Sequence[str]) -> None:
        if action not in self.defaults:
            raise KeyError(action)
        clean = self._clean(specs)
        if clean == self.defaults[action]:
            self.overrides.pop(action, None)
        else:
            self.overrides[action] = clean

    def add(self, action: str, spec: str, *, steal: bool = False) -> List[str]:
        """加一個快速鍵；回傳原本綁著這個鍵的其他動作（steal=True 會把它們的這個鍵拿掉）。"""
        c = canonical(spec, self.platform)
        others = [a for a in self.lookup(c) if a != action]
        if steal:
            for a in others:
                self.remove(a, c)
        cur = list(self.bindings(action))
        if c not in cur:
            cur.append(c)
        self.set(action, cur)
        return others

    def remove(self, action: str, spec: str) -> None:
        c = canonical(spec, self.platform)
        self.set(action, [s for s in self.bindings(action) if s != c])

    def reset(self, action: str) -> None:
        self.overrides.pop(action, None)

    def reset_all(self) -> None:
        self.overrides.clear()

    # --- 存讀 -----------------------------------------------------------------
    def to_dict(self) -> dict:
        return {"version": self.VERSION, "platform": self.platform, "shortcuts": {a: list(s) for a, s in sorted(self.overrides.items())}}

    def from_dict(self, d: Optional[dict]) -> int:
        """載入 overrides（忽略不認得的動作與壞的規格）；回傳套用的動作數。另一個平台存的檔：Cmd↔Ctrl 互換。"""
        self.overrides.clear()
        if not isinstance(d, dict):
            return 0
        sc = d.get("shortcuts")
        if not isinstance(sc, dict):
            return 0
        src = d.get("platform") or self.platform
        n = 0
        merged: Dict[str, List[str]] = {}
        for a, specs in sc.items():                 # 別名（舊 id）併進新 id；同一個 id 出現兩次（新舊各一）就把鍵合起來
            a = self.aliases.get(a, a)
            if a not in self.defaults or not isinstance(specs, (list, tuple)):
                continue
            merged.setdefault(a, []).extend(s for s in specs if isinstance(s, str))
        for a, specs in merged.items():
            fixed = [self._translate(s, src) for s in specs]
            self.set(a, fixed)
            if a in self.overrides or self._clean(fixed) == self.defaults[a]:
                n += 1
        return n

    def _translate(self, spec: str, src_platform: str) -> str:
        if src_platform == self.platform:
            return spec
        try:
            mods, key = parse(spec, src_platform)
        except KeySpecError:
            return spec
        a, b = primary_mod(src_platform), primary_mod(self.platform)
        mods = tuple(b if m == a else (a if m == b else m) for m in mods)
        return "+".join(tuple(m for m in MOD_ORDER if m in mods) + (key,))

    def copy(self) -> "Keymap":
        k = Keymap({}, self.platform)
        k.defaults = dict(self.defaults)
        k.overrides = dict(self.overrides)
        return k

    def save_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=1)

    def load_json(self, path: str) -> int:
        with open(path, "r", encoding="utf-8") as f:
            return self.from_dict(json.load(f))


def selftest(check) -> None:
    """純邏輯自我測試（signal_viewer --selftest 會呼叫）。"""
    assert canonical("cmd+shift+z", "mac") == "Shift+Cmd+Z"
    check(canonical("ctrl+Y", "win") == "Ctrl+Y" and canonical("Mod+Z", "mac") == "Cmd+Z" and canonical("Mod+Z", "win") == "Ctrl+Z",
          "keys：canonical（修飾鍵順序、Mod 換平台主修飾鍵）")
    check(canonical("Ctrl++", "win") == "Ctrl+Plus" and canonical("+", "win") == "Plus" and canonical("bracketleft", "mac") == "BracketLeft",
          "keys：+ 與符號鍵名")
    check(label("Shift+Cmd+Z", "mac") == "⇧⌘Z" and label("Ctrl+Shift+Z", "win") == "Ctrl+Shift+Z" and label("Left", "mac") == "←"
          and label("Delete", "win") == "Del" and label("Plus", "mac") == "+", "keys：顯示字（mac 符號、Windows 文字）")
    bad = 0
    for s in ("", "Ctrl+Shift", "Foo+Z", "Shift"):
        try:
            parse(s, "mac")
        except KeySpecError:
            bad += 1
    check(bad == 4, "keys：空、只有修飾鍵、不認得的修飾鍵 → KeySpecError")

    class E:
        def __init__(self, keysym, state):
            self.keysym, self.state = keysym, state
    check(from_tk_event(E("z", 0x8), "mac") == "Cmd+Z" and from_tk_event(E("Z", 0x9), "mac") == "Shift+Cmd+Z"
          and from_tk_event(E("y", 0x4), "win") == "Ctrl+Y" and from_tk_event(E("F5", 0), "win") == "F5"
          and from_tk_event(E("Shift_L", 1), "mac") is None and from_tk_event(E("plus", 1), "mac") == "Shift+Plus"
          and from_tk_event(E("Up", 0x20000 | 0x8), "win") == "Alt+Up",
          "keys：Tk 事件 → 規格（mac Cmd=0x8、Windows Alt=0x20000、NumLock 0x8 不算修飾鍵）")
    class K:                                    # 真的 Tk 事件（2026-10-26 在注音輸入法之下送 ⌘V 等 NSEvent 進 Tk 量到的 keysym／keycode／state）
        def __init__(self, keysym, keycode, state):
            self.keysym, self.keycode, self.state = keysym, keycode, state
    check(from_tk_event(K("??", 0x09000076, 0x8), "mac") == "Cmd+V" and from_tk_event(K("??", 0x08000063, 0x8), "mac") == "Cmd+C"
          and from_tk_event(K("??", 0x09000076, 0x4), "mac") == "Ctrl+V" and from_tk_event(K("??", 0x2B00002C, 0x8), "mac") == "Cmd+Comma"
          and from_tk_event(K("kana_openingbracket", 0x2100005B, 0x8), "mac") == "Cmd+BracketLeft"
          and from_tk_event(K("??", 0x07000078, 0x9), "mac") == "Shift+Cmd+X" and from_tk_event(K("??", 0x12000031, 0x9), "mac") == "Shift+Cmd+Exclam"
          and from_tk_event(K("Cyrillic_es", 0x08000441, 0x8), "mac") == "Cmd+C" and from_tk_event(K("U3112", 0x09003112, 0x8), "mac") == "Cmd+V",
          "keys：注音等非拉丁輸入法之下 ⌘／⌃ 快速鍵照實體按鍵認（keysym ?? → ⌘V、⌃V、⌘,、⌘[、⇧⌘X）")
    # 2026-10-27 用真的按鍵在注音之下量到的：[ ] 是 kana_…、⇧[ 是 kana_openingbracket＋Shift（『沒有 keysym）、- 是 ??
    check(from_tk_event(K("??", 0x09000076, 0), "mac") == "V" and from_tk_event(K("kana_openingbracket", 0x2100300C, 0), "mac") == "BracketLeft"
          and from_tk_event(K("kana_closingbracket", 0x1E00300D, 0), "mac") == "BracketRight"
          and from_tk_event(K("kana_openingbracket", 0x2140300E, 0x1), "mac") == "Shift+BraceLeft"
          and shifted_symbol_alternative(from_tk_event(K("kana_closingbracket", 0x1E40300F, 0x1), "mac") or "", "mac") == "Shift+BracketRight"
          and from_tk_event(K("??", 0x1B003126, 0), "mac") == "Minus",
          "keys：注音沒按 ⌘ 的 [ ] ⇧[ ⇧] -（kana_…、??）也照實體按鍵認（10-27 第二次選單「全部都修」）")
    check(from_tk_event(K("??", 0x0600007A, 0x8), "mac") == "Cmd+Z" and from_tk_event(K("??", 0x10000079, 0x8), "mac") == "Cmd+Y"
          and from_tk_event(K("??", 0x00000061, 0x8), "mac") == "Cmd+A" and from_tk_event(K("??", 0x0D000077, 0x8), "mac") == "Cmd+W",
          "keys：注音的 ⌘Z／⌘Y／⌘A／⌘W（keysym ??）→ 照實體按鍵認成 ⌘Z／⌘Y／⌘A／⌘W")
    check(from_tk_event(K("??", "??", 0x8), "mac") is None
          and from_tk_event(K("??", 0x09000076, 0x8), "win") is None and from_tk_event(K("v", 0x09000076, 0x8), "mac") == "Cmd+V"
          and from_tk_event(K("??", 0x7B000000, 0x8), "mac") is None and from_tk_event(K("Z", 0x0640005A, 0x9), "mac") == "Shift+Cmd+Z"
          and from_tk_event(K("braceleft", 0x2140007B, 0x1), "mac") == "Shift+BraceLeft" and from_tk_event(K("aring", 0x008000E5, 0x10), "mac") == "Alt+Aring"
          and from_tk_event(K("udiaeresis", 0x210000FC, 0), "mac") == "Udiaeresis",
          "keys：keycode 不是整數（測試替身）、Windows、拉丁 keysym（ABC，含 ⇧[；德文 ü）、不是字母鍵、只按 Option 打的字 → 照舊")
    check(shifted_symbol_alternative("Shift+BraceLeft", "mac") == "Shift+BracketLeft" and shifted_symbol_alternative("Shift+BraceRight", "win") == "Shift+BracketRight"
          and shifted_symbol_alternative("Shift+A", "mac") is None and shifted_symbol_alternative("BraceLeft", "mac") is None
          and shifted_symbol_alternative("Cmd+V", "mac") is None,
          "keys：⇧{ 也對得到寫成 ⇧[ 的快速鍵（同一顆鍵；預設的「上一個差異」是 Shift+BracketLeft）")
    # 2026-10-27 第七次選單 2：⇧= 的 keysym 是 plus（"Shift+Plus"），預設的「放大」寫的是 Plus（不帶 Shift）→ 再試「那個符號本身」
    check(shifted_symbol_alternatives("Shift+Plus", "mac") == ["Shift+Equal", "Plus"] and shifted_symbol_alternatives("Shift+Plus", "win") == ["Shift+Equal", "Plus"]
          and shifted_symbol_alternatives("Shift+BraceLeft", "mac") == ["Shift+BracketLeft", "BraceLeft"]
          and shifted_symbol_alternatives(from_tk_event(K("plus", 0x1840002B, 0x1), "mac") or "", "mac") == ["Shift+Equal", "Plus"]
          and shifted_symbol_alternatives("Shift+Cmd+Plus", "mac") == ["Shift+Cmd+Equal", "Cmd+Plus"]
          and shifted_symbol_alternatives("Plus", "mac") == [] and shifted_symbol_alternatives("Cmd+V", "mac") == [] and shifted_symbol_alternatives("", "mac") == [],
          "keys：⇧=（Tk 給 Shift+Plus）也對得到預設「放大」的 Plus（先試 Shift+Equal 再試 Plus；⇧[ 同一套）")
    # 2026-10-27 第五次選單 3：注音的 3、7、` 鍵 Tk 給拉丁名字的 keysym（caron／abovedot／periodcentered）→ 照實體按鍵認成 3、7、`
    check(from_tk_event(K("caron", 0x140002C7, 0x8), "mac") == "Cmd+3" and from_tk_event(K("abovedot", 0x1A0002D9, 0x8), "mac") == "Cmd+7"
          and from_tk_event(K("periodcentered", 0x320000B7, 0x8), "mac") == "Cmd+Grave" and from_tk_event(K("caron", 0x140002C7, 0x4), "mac") == "Ctrl+3"
          and from_tk_event(K("caron", 0x180002C7, 0x8), "mac") == "Cmd+Caron" and from_tk_event(K("3", 0x14000033, 0x8), "mac") == "Cmd+3",
          "keys：注音的 ⌘3／⌘7／⌘`（keysym caron／abovedot／periodcentered）照實體按鍵認成 Cmd+3／Cmd+7／Cmd+Grave（別的鍵上的 ˇ 照舊）")
    check(to_mpl_key("Home", "mac") == "home" and to_mpl_key("Plus", "mac") == "+" and to_mpl_key("Shift+Cmd+Z", "mac") == "shift+cmd+z"
          and to_mpl_key("Ctrl+Left", "win") == "ctrl+left" and to_mpl_key("F5", "win") == "f5", "keys：規格 → matplotlib key")
    check(is_text_edit_key("Cmd+C", "mac") and is_text_edit_key("Left", "mac") and is_text_edit_key("Shift+Home", "win")
          and not is_text_edit_key("Cmd+Shift+C", "mac") and not is_text_edit_key("F5", "win")
          and not is_text_edit_key("Ctrl+G", "win"), "keys：輸入框放行的鍵")
    km = Keymap({"edit.undo": ("Mod+Z",), "edit.redo": ("Mod+Y", "Shift+Mod+Z"), "view.grid": (), "file.rescan": ("F5",)}, "mac")
    check(km.bindings("edit.undo") == ("Cmd+Z",) and km.bindings("edit.redo") == ("Cmd+Y", "Shift+Cmd+Z") and km.lookup("cmd+z") == ["edit.undo"]
          and km.lookup("Cmd+G") == [] and not km.conflicts(), "Keymap：預設、lookup、無衝突")
    others = km.add("view.grid", "Cmd+G")
    check(others == [] and km.bindings("view.grid") == ("Cmd+G",) and km.lookup("Cmd+G") == ["view.grid"] and not km.is_default("view.grid"),
          "Keymap：加快速鍵")
    others = km.add("view.grid", "F5")
    check(others == ["file.rescan"] and km.conflicts() == {"F5": ["view.grid", "file.rescan"]}, "Keymap：加別人的鍵 → 回報衝突")
    km.remove("view.grid", "F5")
    others = km.add("view.grid", "F5", steal=True)
    check(others == ["file.rescan"] and km.bindings("file.rescan") == () and not km.conflicts() and km.lookup("F5") == ["view.grid"],
          "Keymap：steal 把鍵從原動作拿走")
    d = km.to_dict()
    check(d["shortcuts"] == {"file.rescan": [], "view.grid": ["Cmd+G", "F5"]} and "edit.undo" not in d["shortcuts"], "Keymap：to_dict 只存改過的")
    km2 = Keymap({"edit.undo": ("Mod+Z",), "edit.redo": ("Mod+Y", "Shift+Mod+Z"), "view.grid": (), "file.rescan": ("F5",)}, "mac")
    n = km2.from_dict(d)
    check(n == 2 and km2.bindings("view.grid") == ("Cmd+G", "F5") and km2.bindings("file.rescan") == (), "Keymap：from_dict 還原")
    kw = Keymap({"edit.undo": ("Mod+Z",), "view.grid": ()}, "win")
    kw.from_dict({"version": 1, "platform": "mac", "shortcuts": {"view.grid": ["Cmd+G", "Ctrl+H"]}})
    check(kw.bindings("view.grid") == ("Ctrl+G", "Cmd+H"), "Keymap：mac 存的檔在 Windows 讀：Cmd↔Ctrl 互換")
    km2.set("view.grid", ())
    km2.reset("file.rescan")
    check(km2.bindings("view.grid") == () and km2.is_default("file.rescan") and km2.from_dict({"shortcuts": {"nope": ["A"], "edit.undo": ["???+Z", "Cmd+U"]}}) == 1
          and km2.bindings("edit.undo") == ("Cmd+U",), "Keymap：set 空、reset、from_dict 略過不認得的動作與壞規格")
    km2.reset_all()
    check(km2.to_dict()["shortcuts"] == {}, "Keymap：reset_all")
    # 別名：舊 id（analysis.fm）綁的鍵套到新 id（analysis.ampm）；新舊都有就合併；別名指向不存在的 id 直接忽略
    ka = Keymap({"analysis.ampm": (), "view.grid": ("Mod+G",)}, "mac", aliases={"analysis.fm": "analysis.ampm", "x.old": "x.gone"})
    n = ka.from_dict({"version": 1, "platform": "mac", "shortcuts": {"analysis.fm": ["F6"], "x.old": ["F7"]}})
    check(n == 1 and ka.bindings("analysis.ampm") == ("F6",) and ka.lookup("F6") == ["analysis.ampm"] and ka.aliases == {"analysis.fm": "analysis.ampm"},
          "Keymap：舊 id 的快速鍵經別名套到新 id、指向不存在的別名忽略")
    ka.from_dict({"version": 1, "platform": "mac", "shortcuts": {"analysis.fm": ["F6"], "analysis.ampm": ["F8"]}})
    check(set(ka.bindings("analysis.ampm")) == {"F6", "F8"}, "Keymap：新舊 id 都有快速鍵 → 合併")
