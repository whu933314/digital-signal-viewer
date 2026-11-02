# -*- coding: utf-8 -*-
"""實體按鍵：非拉丁文字的輸入法之下，快速鍵照按鍵的實體位置認（plotkit 的圖片視窗、輸入框，以及 DSV 的 dsv_keys 共用）。

非拉丁文字的輸入法（注音 com.apple.keylayout.ZhuyinBopomofo、俄文、希臘文…）之下，macOS 的 Tk 8.6.13 照目前的鍵盤配置把按鍵翻成字，
再從字找 keysym（tkMacOSXKeyboard.c 的 XkbKeycodeToKeysym；⌘、⌃ 不算進去）。注音之下（2026-10-27 用真的按鍵量的）：
  ⌘V → keysym "??"（V 鍵＝ㄒ，沒有 keysym）、⌘W → "??"、⌃A → "??"、⌘3 → caron（3 鍵＝ˇ）
  [ → kana_openingbracket（「）、] → kana_closingbracket（」）、⇧[ → kana_openingbracket＋Shift（『沒有 keysym，Tk 退回不按 Shift 的）
  - → "??"（ㄦ）；= ⇧= ⇧字母 照樣是拉丁字（=、+、A）
所以 <Command-v>、<<Paste>>、<Key-bracketleft> 這些綁定都對不到，快速鍵完全沒反應（第 13 項、10-27 第二次選單「全部都修」）。
這裡把非拉丁的 keysym 換回這顆按鍵在 ABC（美式）配置下的 keysym，和 macOS 的 App 一樣：注音之下 ⌘C 照樣是複製、[ 照樣是上一個轉態。
拉丁的 keysym 一律照用：ABC 之下什麼都不換（不會多觸發、也不會觸發兩次），德文 ü、Dvorak 這類拉丁配置也照它們自己的字。
注音的 3、7、` 三顆鍵 Tk 給的是拉丁名字的 keysym（caron ˇ、abovedot ˙、periodcentered ·）：這三個 keysym 在 ABC 之下不會出現在這三顆鍵上，
所以 keysym 和虛擬鍵碼都對上時也照實體按鍵認成 3、7、`（2026-10-27 使用者第五次選單 3；預設快速鍵沒用到這三顆，只影響使用者自己錄的快速鍵）。
這個模組不 import tkinter（只讀事件的 keysym／keycode／state），可以不開視窗測試；install_text_fallback 用傳進來的 Tk 根視窗。"""
from __future__ import annotations

import re
import sys
from typing import Any, Dict, Optional, Tuple

PLATFORM = "mac" if sys.platform == "darwin" else ("win" if sys.platform.startswith("win") else "linux")

# macOS 的實體按鍵（虛擬鍵碼 kVK_ANSI_*）→ ABC（美式）配置下 Tk 給的 keysym（不按 Shift、按 Shift）。
# Tk 的 keycode（%k）＝ 虛擬鍵碼 << 24 | Option／Shift << 22 | 字元（tkMacOSXPrivate.h 的 MacKeycode）。
MAC_ANSI_KEYSYMS: Dict[int, Tuple[str, str]] = {
    0x00: ("a", "A"), 0x01: ("s", "S"), 0x02: ("d", "D"), 0x03: ("f", "F"), 0x04: ("h", "H"), 0x05: ("g", "G"),
    0x06: ("z", "Z"), 0x07: ("x", "X"), 0x08: ("c", "C"), 0x09: ("v", "V"), 0x0B: ("b", "B"), 0x0C: ("q", "Q"),
    0x0D: ("w", "W"), 0x0E: ("e", "E"), 0x0F: ("r", "R"), 0x10: ("y", "Y"), 0x11: ("t", "T"), 0x12: ("1", "exclam"),
    0x13: ("2", "at"), 0x14: ("3", "numbersign"), 0x15: ("4", "dollar"), 0x16: ("6", "asciicircum"), 0x17: ("5", "percent"),
    0x18: ("equal", "plus"), 0x19: ("9", "parenleft"), 0x1A: ("7", "ampersand"), 0x1B: ("minus", "underscore"),
    0x1C: ("8", "asterisk"), 0x1D: ("0", "parenright"), 0x1E: ("bracketright", "braceright"), 0x1F: ("o", "O"),
    0x20: ("u", "U"), 0x21: ("bracketleft", "braceleft"), 0x22: ("i", "I"), 0x23: ("p", "P"), 0x25: ("l", "L"),
    0x26: ("j", "J"), 0x27: ("apostrophe", "quotedbl"), 0x28: ("k", "K"), 0x29: ("semicolon", "colon"),
    0x2A: ("backslash", "bar"), 0x2B: ("comma", "less"), 0x2C: ("slash", "question"), 0x2D: ("n", "N"), 0x2E: ("m", "M"),
    0x2F: ("period", "greater"), 0x32: ("grave", "asciitilde"),
}
# keysym → 字（matplotlib 的 key 名用；字母、數字就是自己）
KEYSYM_CHARS = {"equal": "=", "plus": "+", "minus": "-", "underscore": "_", "bracketleft": "[", "braceleft": "{",
                "bracketright": "]", "braceright": "}", "apostrophe": "'", "quotedbl": '"', "semicolon": ";", "colon": ":",
                "backslash": "\\", "bar": "|", "comma": ",", "less": "<", "slash": "/", "question": "?", "period": ".",
                "greater": ">", "grave": "`", "asciitilde": "~", "exclam": "!", "at": "@", "numbersign": "#", "dollar": "$",
                "percent": "%", "asciicircum": "^", "ampersand": "&", "asterisk": "*", "parenleft": "(", "parenright": ")",
                "space": " "}
# 非拉丁文字的 keysym 前綴（X11 keysymdef 的命名）：這些 keysym 不能拿來對快速鍵
NON_LATIN_KEYSYM_PREFIXES = ("kana", "Arabic", "Cyrillic", "Serbian", "Ukrainian", "Ukranian", "Macedonia", "Byelorussian",
                             "Greek", "Hebrew", "hebrew", "Thai", "Hangul", "Korean", "Armenian", "Georgian", "Farsi", "Sinh", "braille")
# 注音之下 Tk 給「拉丁名字」keysym 的三顆鍵（2026-10-27 用真的按鍵量的）：3 鍵＝ˇ（caron）、7 鍵＝˙（abovedot）、` 鍵＝·（periodcentered）
# → 那顆鍵的虛擬鍵碼。這三個 keysym 在 ABC 之下不會出現在這三顆鍵上，所以 keysym 和虛擬鍵碼都對上就照實體按鍵認成 3、7、`
# （使用者第五次選單 3）；別的配置在別的鍵上打出同一個字（捷克文的 ˇ 在 = 鍵）照舊不換。
NAMED_ON_OTHER_KEYS = {"caron": 0x14, "abovedot": 0x1A, "periodcentered": 0x32}
# macOS 的 Tk event.state 位元
STATE_SHIFT, STATE_LOCK, STATE_CONTROL, STATE_CMD, STATE_OPTION = 1, 2, 4, 8, 16


def keysym_not_latin(keysym: str) -> bool:
    """這個 keysym 是非拉丁輸入法給的（沒有 keysym 的 "??"、kana_openingbracket、Cyrillic_es、單一個非 ASCII 字…）。"""
    if not keysym or keysym == "??":
        return True
    if len(keysym) == 1:
        return ord(keysym) > 127
    if keysym[0] == "U" and len(keysym) >= 5 and all(c in "0123456789abcdefABCDEF" for c in keysym[1:]):
        return True                              # Tk 給沒有名字的 Unicode keysym（U3112）
    return keysym.split("_", 1)[0] in NON_LATIN_KEYSYM_PREFIXES


def _state(event) -> int:
    try:
        return int(getattr(event, "state", 0) or 0)
    except (TypeError, ValueError):
        return 0


def physical_keysym(event, platform: str = PLATFORM) -> Optional[str]:
    """macOS 的 Tk 按鍵事件 → 這顆實體按鍵在 ABC 配置下的 keysym（看 Shift）；不是 macOS、不是字母數字符號鍵、keycode 不是整數
    （測試替身、輸入法送的字）回 None。"""
    if platform != "mac":
        return None
    try:
        code = int(getattr(event, "keycode", None))
    except (TypeError, ValueError):
        return None
    pair = MAC_ANSI_KEYSYMS.get((code >> 24) & 0xFF)
    if pair is None:
        return None
    return pair[1] if _state(event) & STATE_SHIFT else pair[0]


def named_on_other_key(keysym: str, event, platform: str = PLATFORM) -> bool:
    """注音的 3、7、` 鍵給的拉丁名字 keysym（caron、abovedot、periodcentered）在它們那顆鍵上（NAMED_ON_OTHER_KEYS 的虛擬鍵碼）：
    要照實體按鍵認成 3、7、`（2026-10-27 第五次選單 3）。別的鍵上的同一個 keysym、不是 macOS、keycode 不是整數都回 False。"""
    vk = NAMED_ON_OTHER_KEYS.get(keysym)
    if vk is None or platform != "mac":
        return False
    try:
        code = int(getattr(event, "keycode", None))
    except (TypeError, ValueError):
        return False
    return (code >> 24) & 0xFF == vk


def latin_keysym(event, platform: str = PLATFORM) -> str:
    """拿來對快速鍵的 keysym：一般就是 event.keysym；macOS 上目前的輸入法給的是非拉丁的 keysym（注音的 ??、kana_…、U3112），
    就換成這顆實體按鍵在 ABC 配置下的 keysym（看 Shift）。
    - 拉丁的 keysym 照用：ABC（含 Shift、CapsLock）什麼都不換，德文 ü、Dvorak 這類拉丁配置也照它們自己的字。
    - 只按 Option 打的字照舊（ABC 的 ⌥P＝Greek_pi 也是）；Option 再加 ⌘ 或 ⌃ 時照樣換（和第 13 項一樣）。
    - 沒有修飾鍵或只有 Shift（注音的 [ ] ⇧[ -）：也換（2026-10-27 第二次選單「全部都修」）。
    - 注音的 3、7、` 鍵給的拉丁名字 keysym（caron、abovedot、periodcentered，NAMED_ON_OTHER_KEYS）：keysym 和虛擬鍵碼都對上時也換
      （第五次選單 3）；同一個 keysym 在別的鍵上（別的配置）照舊。"""
    keysym = getattr(event, "keysym", "") or ""
    if not keysym_not_latin(keysym) and not named_on_other_key(keysym, event, platform):
        return keysym
    phys = physical_keysym(event, platform)
    if phys is None:
        return keysym
    st = _state(event)
    if st & STATE_OPTION and not st & (STATE_CMD | STATE_CONTROL):
        return keysym                            # 只按 Option 打的字
    return phys


def is_remapped(event, platform: str = PLATFORM) -> bool:
    """這個按鍵要照實體按鍵認（latin_keysym 換過了）。"""
    return latin_keysym(event, platform) != (getattr(event, "keysym", "") or "")


def mpl_key(event, platform: str = PLATFORM) -> Optional[str]:
    """照實體按鍵認的 matplotlib key 名（"-"、"["、"ctrl+a"…；和 matplotlib 的 Tk 後端同一套寫法）；不用換的按鍵回 None。
    plotkit 的 Interactor 用：注音之下 - 鍵的 key 是 "ㄦ"，對不到「縮小」。"""
    if not is_remapped(event, platform):
        return None
    ks = latin_keysym(event, platform)
    ch = KEYSYM_CHARS.get(ks, ks if len(ks) == 1 else None)
    if ch is None:
        return None
    st = _state(event)
    mods = [name for name, bit in (("ctrl", STATE_CONTROL), ("alt", STATE_OPTION), ("cmd", STATE_CMD)) if st & bit]
    return "+".join(mods + [ch])


def command_key(event, platform: str = PLATFORM) -> Optional[str]:
    """⌘（macOS）或 Ctrl 加一個字母鍵、而且要照實體按鍵認的按鍵 → 那個字母（小寫；按著 Shift 是大寫），其他回 None。
    圖片視窗、分析視窗、表格的 <Key> 後備用：拉丁 keysym 的按鍵由 <Command-v> 這種精確的綁定處理，這裡只接對不到的。"""
    if not is_remapped(event, platform):
        return None
    st = _state(event)
    if not st & (STATE_CMD | STATE_CONTROL) or st & STATE_OPTION:
        return None
    ks = latin_keysym(event, platform)
    return ks if len(ks) == 1 and ks.isalpha() else None


# ---- 輸入框（Entry、ttk.Entry、Text、Spinbox、Combobox、Listbox）--------------------------------------------------------
# 這些元件的 ⌘C／⌘V／⌘X／⌘A／⌘Z、⌃A／⌃E…是 Tk 類別綁定（<<Copy>>＝<Mod1-Key-c>、<Control-Key-d>…），注音之下 keysym 是 "??"，
# 只對到類別的 <Mod1-Key>／<Control-Key>（什麼都不做）。install_text_fallback 在這兩個綁定前面加一段：照實體按鍵換回拉丁 keysym，
# 再照 Tk 的規則在這個類別裡找 ABC 之下會對到的綁定——虛擬事件（<<Paste>>…）就送給這個元件（每一層 bindtag 都會照常處理，
# 和 ABC 一樣），一般綁定（<Control-Key-d>…）就照樣執行它的腳本。拉丁 keysym（ABC）什麼都不做，和原本一樣。
TEXT_FALLBACK_CLASSES = ("Entry", "TEntry", "Text", "Spinbox", "TSpinbox", "TCombobox", "Listbox")
_TK_MOD_BITS = {"Control": STATE_CONTROL, "Shift": STATE_SHIFT, "Lock": STATE_LOCK, "Mod1": STATE_CMD, "M1": STATE_CMD,
                "Command": STATE_CMD, "Mod2": STATE_OPTION, "M2": STATE_OPTION, "Option": STATE_OPTION}
_NEVER_MODS = ("Meta", "M", "Alt", "Mod3", "M3", "Mod4", "M4", "Mod5", "M5", "Extended", "Double", "Triple", "Quadruple")


def _parse_key_pattern(seq: str) -> Optional[Tuple[int, str]]:
    """'<Control-Shift-Key-z>' → (修飾鍵位元, 'z')；不是一個帶 keysym 的按鍵樣式（或帶 macOS 上不會出現的修飾鍵）回 None。"""
    if not (seq.startswith("<") and seq.endswith(">")) or seq.startswith("<<"):
        return None
    parts = seq[1:-1].split("-")
    if len(parts) < 2 or parts[-2] not in ("Key", "KeyPress"):
        return None
    bits = 0
    for m in parts[:-2]:
        if m in _NEVER_MODS or m.startswith("B") or m.startswith("Button"):
            return None
        if m not in _TK_MOD_BITS:
            return None
        bits |= _TK_MOD_BITS[m]
    return bits, parts[-1]


def _bitcount(n: int) -> int:
    return bin(n).count("1")


def match_class_binding(tkapp, cls: str, keysym: str, state: int) -> Optional[Tuple[str, str]]:
    """在 Tk 類別 cls 的綁定裡，找 ABC 之下 (state, keysym) 這個按鍵會對到的那一個（照 Tk 的規則：修飾鍵越多越精確，一樣時一般綁定優先於虛擬事件）。
    回 ("virtual", "<<Paste>>")、("script", 綁定腳本) 或 None。tkapp＝Tk 根視窗的 .tk。"""
    best: Optional[Tuple[int, int, str, str]] = None      # (修飾鍵數, 一般綁定=1／虛擬=0, kind, value)
    for seq in tkapp.splitlist(tkapp.call("bind", cls)):
        seq = str(seq)
        if seq.startswith("<<"):
            for phys in tkapp.splitlist(tkapp.call("event", "info", seq)):
                pat = _parse_key_pattern(str(phys))
                if pat and pat[1] == keysym and (pat[0] & ~state) == 0:
                    cand = (_bitcount(pat[0]), 0, "virtual", seq)
                    if best is None or cand[:2] > best[:2]:
                        best = cand
            continue
        pat = _parse_key_pattern(seq)
        if pat and pat[1] == keysym and (pat[0] & ~state) == 0:
            cand = (_bitcount(pat[0]), 1, "script", str(tkapp.call("bind", cls, seq)))
            if best is None or cand[:2] > best[:2]:
                best = cand
    return (best[2], best[3]) if best is not None else None


def _tcl_word(v: str) -> str:
    """一個值放進 Tcl 腳本當一個字（Tk 代換 % 欄位時一樣會加引號）。"""
    v = str(v)
    if v == "":
        return "{}"
    return "".join("\\" + {"\t": "t", "\n": "n", "\r": "r"}.get(ch, ch) if ch in '[]{}$"\\; \t\n\r' else ch for ch in v)


def _expand_percents(script: str, fields: Dict[str, str]) -> str:
    return re.sub(r"%[%#a-zA-Z]", lambda m: "%" if m.group(0) == "%%" else _tcl_word(fields.get(m.group(0), "??")), script)


class _Ev:
    __slots__ = ("keysym", "keycode", "state")

    def __init__(self, keysym, keycode, state):
        self.keysym, self.keycode, self.state = keysym, keycode, state


def text_fallback(tkapp, path: str, keysym: str, keycode: str, state: str) -> str:
    """輸入框類別 <Mod1-Key>／<Control-Key> 的後備（install_text_fallback 掛上去的）：照實體按鍵認，回 "break" 表示處理掉了。"""
    try:
        st = int(state)
    except (TypeError, ValueError):
        return ""
    ev = _Ev(keysym, keycode, st)
    if not is_remapped(ev):
        return ""                                # 拉丁 keysym（ABC）：和原本的綁定一樣什麼都不做
    latin = latin_keysym(ev)
    try:
        cls = str(tkapp.call("winfo", "class", path))
    except Exception:
        return ""
    hit = match_class_binding(tkapp, cls, latin, st)
    if hit is None:
        return ""                                # ABC 之下也只對到「什麼都不做」：讓按鍵照常往下傳（主視窗的快速鍵分派器）
    kind, value = hit
    if kind == "virtual":
        tkapp.call("event", "generate", path, value)
        return "break"                           # 虛擬事件已經照每一層 bindtag 處理過了：這個按鍵不再往下傳（不然會做兩次）
    fields = {"%W": path, "%K": latin, "%k": str(keycode), "%s": str(st), "%A": "", "%N": "0", "%T": "2", "%#": "0",
              "%t": "0", "%x": "0", "%y": "0", "%X": "0", "%Y": "0", "%E": "0", "%b": "??", "%D": "??"}
    code = int(tkapp.call("catch", _expand_percents(value, fields), "::pk_keys::res"))
    if code == 1:
        raise RuntimeError(str(tkapp.getvar("::pk_keys::res")))
    return "break" if code == 3 else ""


def install_text_fallback(root, platform: str = PLATFORM) -> bool:
    """在這個 Tk 直譯器的輸入框類別（TEXT_FALLBACK_CLASSES）的 <Mod1-Key>、<Control-Key> 綁定前面加上 text_fallback（只有 macOS；
    同一個直譯器只裝一次）。回傳這次有沒有裝。plotkit 的圖片視窗、DSV 啟動時都會呼叫。"""
    if platform != "mac":
        return False
    try:
        root = root._root()                     # 指令要掛在 Tk 根視窗上：掛在別的視窗，那個視窗關掉時指令就被刪了
    except Exception:
        pass
    tkapp = root.tk
    try:
        if int(tkapp.call("info", "exists", "::pk_keys::installed")):
            return False
    except Exception:
        return False
    tkapp.eval("namespace eval ::pk_keys {}")
    cmd = root.register(lambda path, keysym, keycode, state: text_fallback(tkapp, path, keysym, keycode, state))
    tkapp.setvar("::pk_keys::installed", "1")
    tkapp.setvar("::pk_keys::cmd", cmd)
    for cls in TEXT_FALLBACK_CLASSES:
        for seq in ("<Mod1-Key>", "<Control-Key>"):
            old = str(tkapp.call("bind", cls, seq))
            script = f'if {{"[{cmd} %W %K %k %s]" eq "break"}} break'
            tkapp.call("bind", cls, seq, script + ("\n" + old if old.strip() else ""))
    return True


def selftest(check) -> None:
    """純邏輯檢查（plotkit --selftest 呼叫）：2026-10-27 在注音輸入法之下用真的按鍵量到的事件，以及 ABC 之下不換。"""
    E = _Ev
    m = "mac"
    check(latin_keysym(E("??", 0x09000076, STATE_CMD), m) == "v" and latin_keysym(E("??", 0x0D000077, STATE_CMD), m) == "w"
          and latin_keysym(E("??", 0x00000001, STATE_CONTROL), m) == "a" and latin_keysym(E("kana_openingbracket", 0x2100005B, STATE_CMD), m) == "bracketleft",
          "keys：注音的 ⌘V／⌘W／⌃A／⌘[（keysym ??、kana_…）→ 實體按鍵 v／w／a／bracketleft")
    check(latin_keysym(E("kana_openingbracket", 0x2100300C, 0), m) == "bracketleft"
          and latin_keysym(E("kana_closingbracket", 0x1E00300D, 0), m) == "bracketright"
          and latin_keysym(E("kana_openingbracket", 0x2140300E, STATE_SHIFT), m) == "braceleft"
          and latin_keysym(E("??", 0x1B003126, 0), m) == "minus",
          "keys：注音沒按 ⌘ 的 [ ] ⇧[ -（kana_…、??）→ bracketleft／bracketright／braceleft／minus")
    check(latin_keysym(E("bracketleft", 0x2100005B, 0), m) == "bracketleft" and latin_keysym(E("braceleft", 0x2140007B, STATE_SHIFT), m) == "braceleft"
          and latin_keysym(E("v", 0x09000076, STATE_CMD), m) == "v" and latin_keysym(E("Z", 0x0640005A, STATE_SHIFT | STATE_CMD), m) == "Z"
          and latin_keysym(E("A", 0x00000041, STATE_LOCK), m) == "A" and latin_keysym(E("plus", 0x1840002B, STATE_SHIFT), m) == "plus",
          "keys：ABC 的 keysym（含 Shift、CapsLock、⇧⌘Z）照用，不換")
    check(latin_keysym(E("udiaeresis", 0x210000FC, 0), m) == "udiaeresis" and latin_keysym(E("ssharp", 0x1B0000DF, 0), m) == "ssharp"
          and latin_keysym(E("udiaeresis", 0x210000FC, STATE_CMD), m) == "udiaeresis" and latin_keysym(E("j", 0x0800006A, STATE_CMD), m) == "j"
          and latin_keysym(E("caron", 0x180002C7, STATE_CMD), m) == "caron",
          "keys：拉丁配置照它自己的字（德文 ü、ß、Dvorak 的 ⌘J；別的鍵上的 ˇ——捷克文的 = 鍵——照舊）")
    # 2026-10-27 第五次選單 3：注音的 3、7、` 鍵 Tk 給拉丁名字的 keysym（caron ˇ、abovedot ˙、periodcentered ·）→ 照實體按鍵認成 3、7、grave
    check(latin_keysym(E("caron", 0x140002C7, STATE_CMD), m) == "3" and latin_keysym(E("abovedot", 0x1A0002D9, STATE_CMD), m) == "7"
          and latin_keysym(E("periodcentered", 0x320000B7, STATE_CMD), m) == "grave" and latin_keysym(E("caron", 0x140002C7, STATE_CONTROL), m) == "3"
          and latin_keysym(E("caron", 0x140002C7, 0), m) == "3" and is_remapped(E("caron", 0x140002C7, STATE_CMD), m)
          and latin_keysym(E("caron", "??", STATE_CMD), m) == "caron" and latin_keysym(E("caron", 0x140002C7, STATE_CMD), "win") == "caron"
          and latin_keysym(E("3", 0x14000033, STATE_CMD), m) == "3" and latin_keysym(E("numbersign", 0x14400023, STATE_SHIFT | STATE_CMD), m) == "numbersign",
          "keys：注音的 ⌘3／⌘7／⌘`（keysym caron／abovedot／periodcentered 在 3、7、` 鍵上）→ 照實體按鍵認成 3／7／grave（⌃、沒按 ⌘ 也是）；"
          "keycode 不是整數、Windows 照舊；ABC 的 3、⇧3 不變")
    check(latin_keysym(E("aring", 0x008000E5, STATE_OPTION), m) == "aring" and latin_keysym(E("Greek_pi", 0x230003C0, STATE_OPTION), m) == "Greek_pi"
          and latin_keysym(E("aring", 0x008000E5, STATE_OPTION | STATE_CMD), m) == "aring"
          and latin_keysym(E("Greek_pi", 0x230003C0, STATE_OPTION | STATE_CMD), m) == "p",
          "keys：Option 打特殊字照舊；⌥⌘ 只有非拉丁字才換（和第 13 項一樣）")
    check(latin_keysym(E("??", "??", STATE_CMD), m) == "??" and latin_keysym(E("??", 0x7B000000, STATE_CMD), m) == "??"
          and latin_keysym(E("??", 0x09000076, STATE_CMD), "win") == "??" and latin_keysym(E("??", 0x80003105, 0), m) == "??",
          "keys：keycode 不是整數（測試替身）、方向鍵這種特殊鍵、Windows、輸入法送的字（虛擬鍵碼 0x80）→ 不換")
    check(mpl_key(E("??", 0x1B003126, 0), m) == "-" and mpl_key(E("kana_openingbracket", 0x2100300C, 0), m) == "["
          and mpl_key(E("??", 0x00000001, STATE_CONTROL), m) == "ctrl+a" and mpl_key(E("minus", 0x1B00002D, 0), m) is None,
          "keys：matplotlib 的 key 名（注音的 - → '-'、[ → '['、⌃A → 'ctrl+a'；ABC 不用換 → None）")
    check(command_key(E("??", 0x09000076, STATE_CMD), m) == "v" and command_key(E("??", 0x0D000077, STATE_CONTROL), m) == "w"
          and command_key(E("v", 0x09000076, STATE_CMD), m) is None and command_key(E("kana_openingbracket", 0x2100005B, STATE_CMD), m) is None
          and command_key(E("??", 0x09000076, 0), m) is None and command_key(E("??", 0x09000076, STATE_CMD | STATE_OPTION), m) is None,
          "keys：command_key 只接注音之下的 ⌘／⌃＋字母（ABC 的 keysym、[ 這種符號、沒按 ⌘、⌥⌘ 都回 None）")
    check(_parse_key_pattern("<Control-Shift-Key-z>") == (STATE_CONTROL | STATE_SHIFT, "z") and _parse_key_pattern("<Mod1-Key-c>") == (STATE_CMD, "c")
          and _parse_key_pattern("<Mod1-Key>") is None and _parse_key_pattern("<<Copy>>") is None and _parse_key_pattern("<Meta-Key-b>") is None
          and _parse_key_pattern("<Key-F3>") == (0, "F3"), "keys：Tk 按鍵樣式的解析（Meta 在 macOS 不會對到）")
