# -*- coding: utf-8 -*-
"""Digital Signal Viewer — 數位匯流排顯示（工具缺口 11：MATLAB Logic Analyzer 的 DisplayChannelFormat／DisplayChannelRadix）。

每條訊號三個欄位（Signal.disp／radix／bits，存進設定檔、可復原）：
- 顯示格式 disp：analog（類比：原本的階梯線，預設）／digital（數位）。只由使用者手動選，不自動判斷（2026-10-23 使用者指定）。
  數位＝值不變的區段畫成六角框並寫上數值（plotkit.bus.BusArtist）；只有 0／1 的訊號照 MATLAB 畫成邏輯準位線（＝原本的樣子）。
  舊設定檔裡的 "auto" 讀成 analog。
- 進位制 radix：""＝自動（讀數照舊用十進位；匯流排文字在 HEX／HEXS 檔用十六進位，其他十進位）、hex／bin／oct／sdec／udec。
  套用到：匯流排文字、十字游標、資料提示（含提示內容的 Y 列）、量測面板的 Max／Min／峰對峰值、游標量測的 y1／y2。
- 位元寬度 bits：0＝自動（HEX token 的字數 × 4 與數值範圍取大的）；決定補零位數與二補數。
這個模組不 import signal_viewer（避免循環）：要用到 signal_viewer 裡的函式時，從 Signal 類別所在的模組取（_sv()）。
"""
from __future__ import annotations

import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import plotkit as pk
from plotkit import bus as pbus
from plotkit.i18n import tr

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover - headless
    tk = ttk = None  # type: ignore

BUS_FONTSIZE = 8.0
FORMAT_LABELS = (("analog", "類比"), ("digital", "數位"))
RADIX_LABELS = (("", "自動"), ("hex", "十六進位（Hex）"), ("bin", "二進位（Binary）"), ("oct", "八進位（Octal）"),
                ("sdec", "有號十進位（Signed decimal）"), ("udec", "無號十進位（Unsigned decimal）"))
SCHEDULE: Optional[Callable[[int, Callable[[], None]], Callable[[], None]]] = None   # 防抖計時器（GUI 建好時設定）
_HEX_TOKEN = re.compile(r"^[+-]?(0[xX])?([0-9a-fA-F]+)$")


def _sv(obj) -> Any:
    """Signal／SignalViewer 所在的模組（以 script 執行時是 __main__，被 import 時是 signal_viewer）。"""
    return sys.modules.get(type(obj).__module__)


# ---------------------------------------------------------------------------
# 欄位與統計（純計算）
# ---------------------------------------------------------------------------
def normalize_fields(sig) -> None:
    """Signal.from_dict 之後：舊設定檔沒有這三欄＝預設；不認得的值改回預設。"""
    sig.disp = pbus.parse_display_format(getattr(sig, "disp", "analog"))
    sig.radix = pbus.parse_radix(getattr(sig, "radix", ""))
    sig.bits = pbus.clamp_bits(getattr(sig, "bits", 0))


def bus_stats(sig) -> dict:
    """整條訊號（處理後的值）的：是否全是有限整數、是否只有 0／1、轉態數、最小／最大值。依 data 物件快取。"""
    y = sig.get_data()
    cache = getattr(sig, "_dsv_bus_stats", None)
    if cache is not None and cache[0] is y:
        return cache[1]
    y = np.asarray(y, dtype=float)
    st: Dict[str, Any] = {"n": int(len(y)), "int": False, "bin01": False, "ntrans": 0, "lo": 0.0, "hi": 0.0}
    if len(y):
        with np.errstate(invalid="ignore"):
            fin = np.isfinite(y)
            st["int"] = bool(fin.all() and np.all(y == np.floor(y)))
            st["bin01"] = bool(np.all((y == 0) | (y == 1)))
        st["ntrans"] = int(len(pbus.transitions(y)))
        if fin.any():
            st["lo"], st["hi"] = float(np.min(y[fin])), float(np.max(y[fin]))
    sig._dsv_bus_stats = (sig.get_data(), st)
    return st


def token_bits(sig) -> int:
    """HEX／HEXS 讀進來的訊號：檔案裡 hex token 的字數 × 4（只看開頭 400 個 token）；其他格式 0。"""
    if (getattr(sig, "detected", None) or "").upper() not in ("HEX", "HEXS"):
        return 0
    cache = getattr(sig, "_dsv_token_bits", None)
    if cache is not None and cache[0] == (sig.path, sig.column, sig.detected):
        return cache[1]
    toks: List[str] = []
    m = _sv(sig)
    try:
        if sig.column is not None:
            toks = list(m.get_csv_table(sig.path).column_tokens(sig.column)[:400])
        else:
            text = m.read_text_any(sig.path, limit=65536)
            for line in text.splitlines():
                s = line.strip()
                if not s or s.startswith(("#", "%", "//")):
                    continue
                toks.append(re.split(r"[\s,;]+", s, 1)[0])
                if len(toks) >= 400:
                    break
    except Exception:
        toks = []
    w = 0
    for t in toks:
        mm = _HEX_TOKEN.match(str(t).strip())
        if mm:
            w = max(w, len(mm.group(2)))
    bits = min(pbus.MAX_BITS, 4 * w)
    sig._dsv_token_bits = ((sig.path, sig.column, sig.detected), bits)
    return bits


def auto_bits(sig) -> int:
    """自動位元寬度：HEX token 的字數 × 4 與數值範圍需要的位元數取大的（非整數訊號 0）。"""
    st = bus_stats(sig)
    rb = pbus.range_bits(st["lo"], st["hi"]) if st["int"] and st["n"] else 0
    return max(token_bits(sig), rb)


def effective_bits(sig) -> int:
    return int(sig.bits) if getattr(sig, "bits", 0) else auto_bits(sig)


def is_bus(sig) -> bool:
    """這條訊號現在要不要畫成匯流排（六角框＋數值）。"""
    if getattr(sig, "disp", "analog") != "digital":       # 只有手動選「數位」才畫匯流排
        return False
    st = bus_stats(sig)
    if not st["n"] or st["bin01"]:              # 0／1 訊號：Digital 也畫邏輯準位線（MATLAB 的 1 位元 wave）
        return False
    return True


def value_text(sig, v, prefix: bool = True) -> Optional[str]:
    """讀數用：選了進位制而且是整數值 → 進位制文字（hex 加 0x 等）；否則 None（呼叫端用原本的十進位格式）。"""
    radix = getattr(sig, "radix", "") if sig is not None else ""
    if not radix or v is None:
        return None
    return pbus.format_value(v, radix, effective_bits(sig), prefix=prefix)


def fmt_value(sig, v) -> str:
    """十字游標／游標量測的值：進位制文字或 fmt_num。"""
    if v is None:
        return "—"
    return value_text(sig, v) or pk.draw.fmt_num(v)


def meas_formatter(sig) -> Optional[Callable[[float], str]]:
    """量測面板 Max／Min／峰對峰值用的格式（沒選進位制 None＝照舊）。"""
    if not getattr(sig, "radix", ""):
        return None
    return lambda v: value_text(sig, v) or pk.draw.fmt_num(v)


def radix_tip(sig, text: str, y) -> str:
    """資料提示文字（format_tip_text 的結果）最後一列 Y 換成進位制。"""
    vt = value_text(sig, y)
    if not vt or "\n" not in text:
        return text
    return text.rsplit("\n", 1)[0] + f"\nY {vt}"


def bus_radix(sig) -> str:
    """匯流排框內文字的進位制：選了就用；自動＝HEX／HEXS 檔用 hex，其他 ""（十進位）。"""
    r = getattr(sig, "radix", "")
    if r:
        return r
    return "hex" if (getattr(sig, "detected", None) or "").upper() in ("HEX", "HEXS") else ""


def bus_text_fn(sig) -> Callable[[float], Optional[str]]:
    radix = bus_radix(sig)
    if not radix:
        return pk.draw.fmt_num
    bits = effective_bits(sig)
    return lambda v: pbus.format_value(v, radix, bits) or pk.draw.fmt_num(v)


# ---------------------------------------------------------------------------
# render() 用
# ---------------------------------------------------------------------------
def plan_panel(grp) -> Tuple[Dict[int, Optional[Tuple[float, float]]], set]:
    """一個 panel 的匯流排配置：{uid: (中心, 半高)}（這一側只有匯流排＝一條一列，由上而下）或 None（和類比線混在同一軸：
    框＝自己的值範圍，在 draw_bus 裡算），以及「只有匯流排」的側（left／right）。"""
    plan: Dict[int, Optional[Tuple[float, float]]] = {}
    pure: set = set()
    for side in ("left", "right"):
        members = [s for s in grp if ("right" if s.yaxis == "right" else "left") == side and len(s.get_data())]
        buses = [s for s in members if is_bus(s)]
        if not buses:
            continue
        if len(buses) == len(members):
            pure.add(side)
            for s, band in zip(buses, pbus.band_rows(len(buses))):
                plan[s.uid] = band
        else:
            for s in buses:
                plan[s.uid] = None
    return plan, pure


def draw_bus(tgt, sig, x, y, yp, band, kw: dict) -> Tuple[Any, dict]:
    """畫一條匯流排：回 (上緣 Line2D＝圖例／選取／樣式的對象, artists 字典要多存的東西)。
    hit＝看不見的線（頂點＝每個樣本、y＝框中心，線寬隨框高：點框裡任何地方都算點到這條訊號，資料提示釘在樣本上）。"""
    from matplotlib.lines import Line2D
    c, h = band if band is not None else pbus.band_from_values(yp)
    kw2 = {k: v for k, v in kw.items() if k not in ("marker", "ms", "markevery")}
    ln, = tgt.plot([x[0], x[-1]], [c + h, c + h], **kw2)
    n = len(y)
    hit = Line2D(np.asarray(x[:-1], float), np.full(n, c), visible=False, lw=1.0)
    tgt.add_line(hit)
    ext = Line2D([x[0], x[-1]], [c - h, c + h], visible=False)       # 讓 dataLim（還原視圖、自動範圍）含整個框
    tgt.add_line(ext)
    art = BusArtistDSV(tgt, ln, float(x[0]), float(x[1] - x[0]) if len(x) > 1 else 1.0, y, c, h, bus_text_fn(sig),
                       fontsize=BUS_FONTSIZE, schedule=SCHEDULE, hit_line=hit)
    return ln, {"bus": art, "hit": hit, "bus_center": c, "bus_half": h}


class BusArtistDSV(pbus.BusArtist):
    """BusArtist ＋ 讓看不見的 hit 線的線寬跟著框高（點框內任何地方都命中）。"""

    def __init__(self, *a, hit_line=None, **k):
        self.hit_line = hit_line
        super().__init__(*a, **k)

    def update_layout(self, force: bool = False) -> None:
        super().update_layout(force)
        if self.hit_line is not None and self.axes is not None:
            ax = self.axes
            try:
                band_px = abs(ax.transData.transform((0, self.center + self.half))[1]
                              - ax.transData.transform((0, self.center - self.half))[1])
                self.hit_line.set_linewidth(max(1.0, band_px * 72.0 / float(ax.figure.dpi)))
            except Exception:
                pass


def finish_axes(ax, ax_r, pure: set) -> None:
    """只有匯流排的軸不要數值刻度（一條一列，列的位置沒有數值意義）。"""
    if "left" in pure:
        ax.set_yticks([])
    if "right" in pure and ax_r is not None:
        ax_r.set_yticks([])


# ---------------------------------------------------------------------------
# 介面（SignalViewer 的 mixin）
# ---------------------------------------------------------------------------
class BusMixin:
    """訊號屬性 → 訊號參數 的「數位顯示」區、清單／圖上右鍵的「顯示格式／進位制／位元寬度…」。"""

    def _bus_targets(self) -> List[Any]:
        return self._style_targets()

    def _build_bus_props(self) -> None:
        """在「訊號參數」分頁（目前最後一個分頁）最下面加「數位顯示（Logic Analyzer）」區。"""
        global SCHEDULE
        SCHEDULE = self._bus_schedule
        f = self.nametowidget(self.nb.tabs()[-1])
        self.p_bus_disp = tk.StringVar(value=tr("類比"))
        self.p_bus_radix = tk.StringVar(value=tr("自動"))
        self.p_bus_bits = tk.StringVar(value="")
        self.p_bus_info = tk.StringVar(value="")
        g = ttk.LabelFrame(f, text=tr("數位顯示（Logic Analyzer）"))
        g.pack(fill="x", pady=2)
        r = ttk.Frame(g)
        r.pack(fill="x", padx=4, pady=2)
        ttk.Label(r, text=tr("格式")).pack(side="left")
        cb = ttk.Combobox(r, textvariable=self.p_bus_disp, values=[tr(lbl) for _k, lbl in FORMAT_LABELS], width=6, state="readonly")
        cb.pack(side="left", padx=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_bus_format(self._bus_key(FORMAT_LABELS, self.p_bus_disp.get())))
        pk.theme.tooltip(cb, tr("類比＝階梯線（預設）；數位＝值不變的區段畫成六角框＋數值（只有 0／1 的訊號仍畫邏輯準位線）"))
        self.bus_disp_cb = cb
        ttk.Label(r, text=tr("進位制")).pack(side="left", padx=(8, 0))
        cb = ttk.Combobox(r, textvariable=self.p_bus_radix, values=[tr(lbl) for _k, lbl in RADIX_LABELS], width=16, state="readonly")
        cb.pack(side="left", padx=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self.set_bus_radix(self._bus_key(RADIX_LABELS, self.p_bus_radix.get())))
        pk.theme.tooltip(cb, tr("匯流排文字、十字游標、資料提示、量測與游標讀數都用這個進位制；自動＝讀數照舊（十進位）"))
        self.bus_radix_cb = cb
        r = ttk.Frame(g)
        r.pack(fill="x", padx=4, pady=2)
        ttk.Label(r, text=tr("位元寬度")).pack(side="left")
        e = ttk.Entry(r, textvariable=self.p_bus_bits, width=5)
        e.pack(side="left", padx=2)
        e.bind("<Return>", lambda ev: self.apply_bus_bits())
        b = ttk.Button(r, text=tr("套用"), command=self.apply_bus_bits)
        b.pack(side="left", padx=3)
        T_ = pk.theme
        T_.tooltip(b, tr("空白或 0＝自動（HEX 字數 × 4 或數值範圍）；決定補零位數與有號值的二補數"))
        ttk.Label(r, textvariable=self.p_bus_info, style="Hint.TLabel").pack(side="left", padx=4)

    def _bus_schedule(self, ms: int, fn: Callable[[], None]) -> Callable[[], None]:
        try:
            aid = self.after(int(ms), fn)
        except Exception:
            return lambda: None

        def cancel():
            try:
                self.after_cancel(aid)
            except Exception:
                pass
        return cancel

    @staticmethod
    def _bus_key(pairs, label: str) -> str:
        for k, lbl in pairs:
            if tr(lbl) == label or lbl == label:
                return k
        return pairs[0][0]

    @staticmethod
    def _bus_label(pairs, key: str) -> str:
        for k, lbl in pairs:
            if k == key:
                return tr(lbl)
        return tr(pairs[0][1])

    def _sync_bus_props(self) -> None:
        """選取改變：屬性區顯示第一條選取訊號的格式／進位制／位元寬度。"""
        if not hasattr(self, "p_bus_disp"):
            return
        sigs = self.selected_signals()
        if not sigs:
            return
        s = sigs[0]
        self.p_bus_disp.set(self._bus_label(FORMAT_LABELS, s.disp))
        self.p_bus_radix.set(self._bus_label(RADIX_LABELS, s.radix))
        self.p_bus_bits.set(str(s.bits) if s.bits else "")
        try:
            ab = auto_bits(s)
            now = tr("匯流排") if is_bus(s) else tr("線")
        except Exception:
            ab, now = 0, ""
        self.p_bus_info.set(tr("自動 {n} 位元；目前畫成{what}").format(n=ab, what=now) if ab else
                            tr("目前畫成{what}").format(what=now) if now else "")

    def _bus_apply(self, desc: str, field: str, value, sigs=None) -> int:
        sigs = sigs if sigs is not None else self._bus_targets()
        if not sigs:
            return 0
        if all(getattr(s, field) == value for s in sigs):
            self._sync_bus_props()
            return 0
        self._push_undo(desc)
        for s in sigs:
            setattr(s, field, value)
        _sv(self).record_action(tr("{what}（{n} 條）").format(what=desc, n=len(sigs)))
        self.plot(keep=True)
        self._sync_bus_props()
        return len(sigs)

    def set_bus_format(self, fmt: str, sigs=None) -> int:
        fmt = pbus.parse_display_format(fmt)
        n = self._bus_apply(tr("顯示格式"), "disp", fmt, sigs)
        if n:
            nb = sum(1 for s in (sigs or self.selected_signals()) if is_bus(s))
            self.status_var.set(tr("顯示格式：{fmt}（{n} 條；畫成匯流排的 {b} 條）").format(
                fmt=self._bus_label(FORMAT_LABELS, fmt), n=n, b=nb))
        return n

    def set_bus_radix(self, radix: str, sigs=None) -> int:
        radix = pbus.parse_radix(radix)
        n = self._bus_apply(tr("進位制"), "radix", radix, sigs)
        if n:
            self.status_var.set(tr("進位制：{radix}（{n} 條）").format(radix=self._bus_label(RADIX_LABELS, radix), n=n))
        return n

    def set_bus_bits(self, bits, sigs=None) -> int:
        b = pbus.clamp_bits(bits)
        n = self._bus_apply(tr("位元寬度"), "bits", b, sigs)
        if n:
            self.status_var.set(tr("位元寬度：{b}（{n} 條）").format(b=b if b else tr("自動"), n=n))
        return n

    def apply_bus_bits(self) -> None:
        txt = self.p_bus_bits.get().strip()
        try:
            b = int(float(txt)) if txt else 0
        except ValueError:
            self.status_var.set(tr("位元寬度要是 0～64 的整數（0 或空白＝自動）"))
            return
        if not 0 <= b <= pbus.MAX_BITS:
            self.status_var.set(tr("位元寬度要是 0～64 的整數（0 或空白＝自動）"))
            return
        self.set_bus_bits(b)

    def edit_bus_bits(self) -> None:
        sigs = self._bus_targets()
        if not sigs:
            return
        cur = str(sigs[0].bits or "")
        val = _sv(self).ask_string(self, tr("位元寬度"), tr("位元寬度（1～64；0 或空白＝自動）："), cur)
        if val is None:
            return
        self.p_bus_bits.set(val)
        self.apply_bus_bits()

    def _add_bus_menu_items(self, m) -> None:
        """清單與圖上右鍵共用：顯示格式／進位制（radio，勾目前第一條選取訊號的值）、位元寬度…。"""
        sigs = self.selected_signals()
        s0 = sigs[0] if sigs else None
        self._bus_menu_disp = tk.StringVar(value=s0.disp if s0 else "analog")
        self._bus_menu_radix = tk.StringVar(value=s0.radix if s0 else "")
        sub = tk.Menu(m, tearoff=0)
        for k, lbl in FORMAT_LABELS:
            sub.add_radiobutton(label=tr(lbl), value=k, variable=self._bus_menu_disp, command=lambda k=k: self.set_bus_format(k))
        m.add_cascade(label=tr("顯示格式"), menu=sub)
        sub2 = tk.Menu(m, tearoff=0)
        for k, lbl in RADIX_LABELS:
            sub2.add_radiobutton(label=tr(lbl), value=k, variable=self._bus_menu_radix, command=lambda k=k: self.set_bus_radix(k))
        m.add_cascade(label=tr("進位制"), menu=sub2)
        m.add_command(label=tr("位元寬度…"), command=self.edit_bus_bits)


# ---------------------------------------------------------------------------
# selftest（signal_viewer.py --selftest 呼叫；g＝signal_viewer 的 globals）
# ---------------------------------------------------------------------------
def selftest(check, g) -> None:
    import math
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    Signal, render = g["Signal"], g["render"]

    def mk(uid, raw, **kw):
        s = Signal(key=f"b{uid}", path="", uid=uid, panel=kw.pop("panel", 1), label=kw.pop("label", f"b{uid}"), **kw)
        s.raw = np.asarray(raw, dtype=float)
        return s

    bus_v = np.repeat([0x12, 0xAB, 0x3, 0xFF, 0x12], 8)
    s_bus = mk(990, bus_v)
    s_clk = mk(991, np.tile([0, 0, 1, 1], 10))
    s_adc = mk(992, np.rint(512 + 300 * np.sin(np.arange(400) / 3.0)))
    s_flt = mk(993, np.repeat([0.5, 1.5], 20))
    check(not is_bus(s_bus) and not is_bus(s_clk) and not is_bus(s_adc) and not is_bus(s_flt) and s_bus.disp == "analog",
          "預設＝類比：不自動判斷，HEX 匯流排、0／1、ADC、小數都畫線")
    s_bus.disp = "digital"
    s_clk.disp = "digital"
    s_adc.disp = "digital"
    s_bus2 = mk(994, bus_v, disp="analog")
    check(not is_bus(s_clk) and is_bus(s_adc) and not is_bus(s_bus2), "數位：0／1 仍是邏輯準位線、其他畫匯流排；類比：一律線")
    s_clk.disp = s_adc.disp = "analog"
    check(auto_bits(s_bus) == 8 and effective_bits(mk(995, [-3, 5, 5, 5])) == 4, "自動位元寬度：數值範圍（0xFF → 8；−3..5 → 4 位二補數）")
    d = Signal.from_dict({"key": "k", "path": "", "disp": "weird", "radix": "HEX", "bits": 99})
    d_old = Signal.from_dict({"key": "k", "path": ""})
    d_auto = Signal.from_dict({"key": "k", "path": "", "disp": "auto"})
    check(d.disp == "analog" and d_auto.disp == "analog" and d.radix == "hex" and d.bits == 64 and d_old.disp == "analog" and d_old.radix == "" and d_old.bits == 0
          and {"disp", "radix", "bits"} <= set(d.to_dict()), "設定檔：新欄位存進 to_dict；舊檔沒有＝預設、不認得的值修正")
    s_bus.radix = "hex"
    check(fmt_value(s_bus, 171.0) == "0xAB" and fmt_value(s_bus, 2.5) == "2.5" and fmt_value(s_bus, None) == "—"
          and fmt_value(s_clk, 171.0) == "171", "讀數：選了 Hex → 0xAB；小數照舊；沒選進位制照舊十進位")
    s_bus.radix = "sdec"
    check(fmt_value(s_bus, 255.0) == "-1" and radix_tip(s_bus, "b990\nX 3\nY 255", 255.0) == "b990\nX 3\nY -1",
          "有號十進位（8 位元）255 → −1；資料提示 Y 列換成進位制")
    s_bus.radix = "hex"
    rd = g["cursor_readout"]([s_bus], [9.0, 25.0], {"xunit": "symbol", "symbol_rate": 1e6})
    check(rd[-1] == ("b990", ["0xAB", "0xFF", "84"]), f"游標量測：y1／y2 用進位制、Δy 十進位（{rd[-1]}）")
    res = g["signal_stats"](s_bus.get_data(), 0.0, 1.0)
    fm = g["format_meas"]("max", res, vfmt=meas_formatter(s_bus))
    check(fm.startswith("0xFF @") and g["format_meas"]("p2p", res, vfmt=meas_formatter(s_bus)) == "0xFC"
          and g["format_meas"]("mean", res, vfmt=meas_formatter(s_bus)) == f"{res['mean']:.6g}",
          f"量測：Max／Min／峰對峰值用進位制，其他照舊（{fm}）")
    # render：只有匯流排的 panel 一條一列、hit 線、series 在框中心
    fig = Figure(figsize=(8, 3), dpi=100)
    FigureCanvasAgg(fig)
    s_bus.radix = ""
    s_b2 = mk(996, np.repeat([1, 2, 3, 4, 5], 8), panel=1, disp="digital")
    s_l = mk(997, np.tile([0, 0, 1, 1], 10), panel=2)
    info = render(fig, [s_bus, s_b2, s_l], {"xunit": "symbol", "symbol_rate": 1e6}, None)
    a1, a2 = info["artists"][990], info["artists"][996]
    ax = a1["ax"]
    check("bus" in a1 and "bus" in a2 and "bus" not in info["artists"][997] and a1["bus_center"] == 1.0 and a2["bus_center"] == 0.0
          and len(ax.get_yticks()) == 0, "render：只有匯流排的 panel 一條一列（由上而下）、不顯示 y 刻度；0／1 線照舊")
    s_bus.radix = "hex"
    info = render(fig, [s_bus, s_b2, s_l], {"xunit": "symbol", "symbol_rate": 1e6}, None)
    fig.canvas.draw()
    a1 = info["artists"][990]
    labs = [t for _x, t in a1["bus"].labels()]
    check(labs == ["12", "AB", "03", "FF", "12"], f"匯流排框內寫數值（Hex、8 位元補零）（{labs}）")
    lab2 = [t for _x, t in info["artists"][996]["bus"].labels()]
    check(lab2 == ["1", "2", "3", "4", "5"], f"自動進位制（DEC 檔）＝十進位（{lab2}）")
    host = g["DsvHost"](type("A", (), {"render_info": info, "find_signal_by_uid": staticmethod(
        lambda u: {990: s_bus, 996: s_b2, 997: s_l}.get(u))})())
    sd = host.series_data(990)
    lines = [ln for _u, ln in host.lines_in(a1["ax"])]
    check(sd is not None and np.all(sd[1] == 1.0) and len(sd[0]) == 40 and a1["hit"] in lines and a1["line"] not in lines,
          "series_data：資料提示釘在樣本、y＝框中心；點選判定用 hit 線")
    ax = a1["ax"]
    ax.set_xlim(0, 1.5)
    fig.canvas.draw()
    check(a1["bus"].n_labels == 1 and a1["bus"].labels()[0][1] == "12", "放大到一段：只寫看得到的那段")
    ax.set_xlim(0, 4000)
    fig.canvas.draw()
    check(a1["bus"].n_labels == 0, "縮到框比字窄：不寫文字")
    # 1e6 樣本：只處理看得到的轉態、比像素密時每欄一個交叉、文字上限
    import time as _t
    yb = np.repeat(np.arange(200000) % 256, 5).astype(float)
    big = mk(998, yb, disp="digital")
    fig2 = Figure(figsize=(8, 2), dpi=100)
    FigureCanvasAgg(fig2)
    t0 = _t.perf_counter()
    info2 = render(fig2, [big], {"xunit": "symbol", "symbol_rate": 1e6}, None)
    fig2.canvas.draw()
    t_full = _t.perf_counter() - t0
    bb = info2["artists"][998]["bus"]
    nv_full = bb.n_vertices
    ax2 = info2["artists"][998]["ax"]
    ax2.set_xlim(1000, 1080)
    t1 = _t.perf_counter()
    fig2.canvas.draw()
    t_zoom = _t.perf_counter() - t1
    check(is_bus(big) and nv_full <= 3 * 800 + 10 and bb.n_labels <= pbus.MAX_LABELS and t_full < 3.0 and t_zoom < 0.5,
          f"1e6 樣本匯流排：全部顯示 {nv_full} 個頂點（≤ 每像素一個交叉）、{t_full * 1000:.0f} ms；放大後重排 {t_zoom * 1000:.0f} ms、"
          f"{bb.n_labels} 個數值")
    check(bb.n_labels == 16 and all(math.isfinite(x) for x, _t2 in bb.labels()), f"放大到 16 段：每段都寫上數值（{bb.n_labels}）")
