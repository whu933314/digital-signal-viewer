# -*- coding: utf-8 -*-
"""plotkit.bus — 邏輯分析儀（MATLAB dsp.LogicAnalyzer）式的數位匯流排顯示與進位制格式。

- 進位制（DisplayChannelRadix）：Hex／Binary／Octal／Signed decimal／Unsigned decimal；位元寬度決定補零位數與二補數。
  ``format_value(v, radix, bits)``：非整數（或 NaN）回 None，呼叫端退回原本的十進位格式。
- 匯流排（DisplayChannelFormat = Digital）：值不變的區段畫成兩端尖的六角框（上緣、下緣在轉態處交叉），數值寫在框中間。
  ``BusArtist`` 在每次 draw 時只處理目前 x 視圖內的轉態：
  轉態比像素還密時，同一像素欄只留一個交叉（1e6 樣本也只畫幾千個頂點）；框太窄放不下文字就不寫；文字數上限 ``MAX_LABELS``。
  只平移（尺度沒變）時沿用舊的文字（它們以資料座標定位，跟著移動），停下來 ``RELAYOUT_MS`` 後再重排（防抖）；縮放立即重排。
不依賴 tkinter；防抖的計時器由呼叫端給（``schedule(ms, fn) -> cancel_fn``），沒給就每次都重排（Agg／存檔）。
"""
from __future__ import annotations

import math
from typing import Any, Callable, List, Optional, Sequence, Tuple

import numpy as np
from matplotlib.artist import Artist
from matplotlib.lines import Line2D
from matplotlib.text import Text

RADIXES = ("hex", "bin", "oct", "sdec", "udec")
RADIX_PREFIX = {"hex": "0x", "bin": "0b", "oct": "0o", "sdec": "", "udec": ""}
DISPLAY_FORMATS = ("analog", "digital")      # 只有手動選擇（不自動判斷）；舊設定檔的 "auto" 讀成 analog
MAX_BITS = 64
SLANT_PX = 4.0            # 六角框兩端斜邊的寬（像素；框太窄時縮成框寬的一半）
MAX_LABELS = 300          # 一條匯流排在畫面上最多寫幾個數值
RELAYOUT_MS = 120         # 平移停下來多久之後重排文字
LABEL_PAD_PX = 6.0        # 文字左右至少留的空白（像素）
BAND_HALF = 0.4           # 匯流排列（一條一列）的半高（資料單位；列距 1）


# ---------------------------------------------------------------------------
# 進位制
# ---------------------------------------------------------------------------
def int_value(v) -> Optional[int]:
    """有限的整數值 → int；其他（小數、NaN、inf、None）→ None。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or f != math.floor(f) or abs(f) >= 2.0 ** 63:
        return None
    return int(f)


def range_bits(lo: float, hi: float) -> int:
    """能裝下 [lo, hi] 整數範圍的最少位元數（有負數就用二補數，多一個符號位元）；至少 1。"""
    lo_i, hi_i = int(math.floor(lo)), int(math.ceil(hi))
    if lo_i >= 0:
        return max(1, hi_i.bit_length())
    return max(1, max(hi_i, 0).bit_length() + 1, (-lo_i - 1).bit_length() + 1)


def clamp_bits(bits) -> int:
    try:
        b = int(bits)
    except (TypeError, ValueError):
        return 0
    return max(0, min(MAX_BITS, b))


def format_value(v, radix: str, bits: int, prefix: bool = False) -> Optional[str]:
    """一個值用進位制寫成文字。bits 決定位數（hex 每 4 位一字、oct 每 3 位、bin 每位）與二補數（signed／負數）。
    超出 bits 的值取低 bits 位（像 MATLAB 的固定寬度 wave）。非整數回 None。prefix＝加 0x／0b／0o（讀數用）。"""
    i = int_value(v)
    if i is None or radix not in RADIXES:
        return None
    b = clamp_bits(bits) or max(1, range_bits(min(i, 0), max(i, 0)))
    mask = (1 << b) - 1
    u = i & mask
    if radix == "udec":
        return str(u)
    if radix == "sdec":
        return str(u - (1 << b) if u >> (b - 1) & 1 else u)
    width = {"hex": (b + 3) // 4, "oct": (b + 2) // 3, "bin": b}[radix]
    body = format(u, {"hex": "X", "oct": "o", "bin": "b"}[radix]).zfill(width)
    return (RADIX_PREFIX[radix] if prefix else "") + body


def parse_radix(value) -> str:
    """設定值 → 進位制鍵；不認得的（含舊設定檔沒有這欄）＝""（自動）。"""
    v = str(value or "").strip().lower()
    return v if v in RADIXES else ""


def parse_display_format(value) -> str:
    v = str(value or "").strip().lower()
    return v if v in DISPLAY_FORMATS else "analog"


# ---------------------------------------------------------------------------
# 轉態與幾何（純計算）
# ---------------------------------------------------------------------------
def transitions(y) -> np.ndarray:
    """值改變的樣本索引 i（y[i] != y[i-1]，i ≥ 1）；NaN→NaN 不算改變。"""
    y = np.asarray(y, dtype=float)
    if len(y) < 2:
        return np.zeros(0, dtype=np.int64)
    a, b = y[1:], y[:-1]
    with np.errstate(invalid="ignore"):
        ch = (a != b) & ~(np.isnan(a) & np.isnan(b))
    return np.flatnonzero(ch).astype(np.int64) + 1


def dedupe_columns(tx: np.ndarray, xlo: float, k: float) -> np.ndarray:
    """同一個像素欄（寬 1/k）只留第一個轉態。"""
    if len(tx) < 2:
        return tx
    col = np.floor((tx - xlo) * k).astype(np.int64)
    keep = np.empty(len(tx), dtype=bool)
    keep[0] = True
    keep[1:] = col[1:] != col[:-1]
    return tx[keep]


def bus_outline(tx: np.ndarray, a: float, b: float, start_in: bool, end_in: bool, d_max: float,
                center: float, half: float) -> Tuple[np.ndarray, np.ndarray]:
    """匯流排上緣的頂點（x 遞增）。tx＝(a, b) 內的轉態 x；a／b 是畫的範圍，start_in／end_in＝訊號頭／尾在範圍內
    （頭尾畫成半個六角的尖端，否則平平地切齊 a／b）。斜邊寬 d＝min(d_max, 左右相鄰間距的一半)。下緣＝對 center 鏡射。"""
    top = center + half
    bnd = np.concatenate(([a], tx, [b]))
    gaps = np.diff(bnd)
    xs: List[np.ndarray] = []
    ys: List[np.ndarray] = []
    if len(tx):
        d = np.minimum(d_max, 0.5 * np.minimum(gaps[:-1], gaps[1:]))
        xs.append(np.column_stack([tx - d, tx, tx + d]).ravel())
        ys.append(np.tile([top, center, top], len(tx)))
    g0, g1 = float(gaps[0]), float(gaps[-1])
    if start_in:
        d0 = min(d_max, 0.5 * g0)
        hx, hy = [a, a + d0], [center, top]
    else:
        hx, hy = [a], [top]
    if end_in:
        d1 = min(d_max, 0.5 * g1)
        tx_, ty_ = [b - d1, b], [top, center]
    else:
        tx_, ty_ = [b], [top]
    x = np.concatenate([np.asarray(hx, float)] + xs + [np.asarray(tx_, float)])
    y = np.concatenate([np.asarray(hy, float)] + ys + [np.asarray(ty_, float)])
    return x, y


def label_runs(T: np.ndarray, x0: float, dx: float, n: int, xlo: float, xhi: float, k: float,
               min_px: float, limit: int = MAX_LABELS) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """可能寫得下文字的區段（值不變的一段）：回 (起始樣本索引, 可見部分的中心 x, 可見寬度 px)，寬的優先、最多 limit 個。
    T＝transitions()；只看 [xlo, xhi] 內的區段。"""
    empty = (np.zeros(0, np.int64), np.zeros(0), np.zeros(0))
    if n <= 0 or k <= 0:
        return empty
    s_lo = (xlo - x0) / dx
    s_hi = (xhi - x0) / dx
    i0 = int(np.searchsorted(T, s_lo, "right"))           # 第一個在視圖內（> xlo）的轉態
    i1 = int(np.searchsorted(T, s_hi, "left"))
    starts = np.concatenate(([T[i0 - 1] if i0 > 0 else 0], T[i0:i1])).astype(np.int64)
    ends = np.concatenate((T[i0:i1], [T[i1] if i1 < len(T) else n])).astype(np.int64)
    xa = np.maximum(x0 + starts * dx, xlo)
    xb = np.minimum(x0 + ends * dx, xhi)
    w = (xb - xa) * k
    ok = np.flatnonzero(w >= min_px)
    if len(ok) > limit:
        ok = np.sort(ok[np.argpartition(-w[ok], limit - 1)[:limit]])
    return starts[ok], 0.5 * (xa[ok] + xb[ok]), w[ok]


# ---------------------------------------------------------------------------
# Artist
# ---------------------------------------------------------------------------
class BusArtist(Artist):
    """一條匯流排：上緣＝呼叫端加進 axes 的 Line2D（圖例、選取加粗、改色都對它做），下緣與數值文字由這個 artist 畫，
    樣式每次 draw 時從上緣複製。zorder 比上緣低一點，所以會先畫、先把上緣的頂點換成目前視圖的。"""

    def __init__(self, ax, top_line: Line2D, x0: float, dx: float, y: np.ndarray, center: float, half: float,
                 text_fn: Callable[[float], Optional[str]], *, fontsize: float = 8.0,
                 schedule: Optional[Callable[[int, Callable[[], None]], Callable[[], None]]] = None):
        super().__init__()
        self.top = top_line
        self.x0, self.dx = float(x0), float(dx)
        self.y = np.asarray(y, dtype=float)
        self.n = len(self.y)
        self.center, self.half = float(center), float(half)
        self.text_fn = text_fn
        self.fontsize = float(fontsize)
        self.schedule = schedule
        self.T = transitions(self.y)
        self.bottom = Line2D([], [])
        self.texts: List[Text] = []
        self.n_labels = 0
        self.n_vertices = 0
        self.layouts = 0                 # 重排文字的次數（測試用）
        self._geom_key = None
        self._label_key = None
        self._label_k = None
        self._force = False
        self._cancel: Optional[Callable[[], None]] = None
        self.set_zorder(top_line.get_zorder() - 0.01)
        self.set_in_layout(False)
        ax.add_artist(self)
        for a in (self.bottom,):
            a.set_figure(ax.figure)
            a.axes = ax
            a.set_transform(ax.transData)
            a.set_clip_path(ax.patch)
        top_line.set_data(*self._full_outline())

    # --- 幾何 -----------------------------------------------------------------
    @property
    def x_end(self) -> float:
        return self.x0 + self.n * self.dx

    def _full_outline(self):
        return np.array([self.x0, self.x_end]), np.array([self.center + self.half] * 2)

    def _view(self):
        ax = self.axes
        x_a, x_b = ax.get_xlim()
        xlo, xhi = (x_a, x_b) if x_a <= x_b else (x_b, x_a)
        w = float(ax.bbox.width)
        return xlo, xhi, w

    def _layout_geometry(self, xlo: float, xhi: float, k: float) -> None:
        span = xhi - xlo
        a = max(self.x0, xlo - 0.05 * span)
        b = min(self.x_end, xhi + 0.05 * span)
        if b <= a or self.n == 0:
            xs, ys = np.zeros(0), np.zeros(0)
        else:
            s_a, s_b = (a - self.x0) / self.dx, (b - self.x0) / self.dx
            T = self.T
            i0 = int(np.searchsorted(T, s_a, "right"))
            i1 = int(np.searchsorted(T, s_b, "left"))
            tx = self.x0 + T[i0:i1] * self.dx
            if len(tx) > 0.5 * max(1.0, (b - a) * k):            # 比像素密：每個像素欄一個交叉
                tx = dedupe_columns(tx, xlo, k)
            xs, ys = bus_outline(tx, a, b, self.x0 >= a, self.x_end <= b, SLANT_PX / k, self.center, self.half)
        self.top.set_data(xs, ys)
        self.bottom.set_data(xs, 2 * self.center - ys if len(ys) else ys)
        self.n_vertices = len(xs)

    def _char_px(self, dpi: float) -> float:
        return 0.62 * self.fontsize * dpi / 72.0

    def _layout_labels(self, xlo: float, xhi: float, k: float) -> None:
        ax = self.axes
        dpi = float(ax.figure.dpi)
        self.layouts += 1
        band_px = abs(ax.transData.transform((0, self.center + self.half))[1]
                      - ax.transData.transform((0, self.center - self.half))[1])
        cpx = self._char_px(dpi)
        n_ok = 0
        if band_px >= self.fontsize * dpi / 72.0 * 1.05:          # 框比字矮就不寫
            starts, cx, w = label_runs(self.T, self.x0, self.dx, self.n, xlo, xhi, k,
                                       cpx + LABEL_PAD_PX + 2 * SLANT_PX, MAX_LABELS)
            for i0, c, wpx in zip(starts.tolist(), cx.tolist(), w.tolist()):
                s = self.text_fn(float(self.y[i0])) if 0 <= i0 < self.n else None
                if not s or len(s) * cpx + LABEL_PAD_PX + 2 * SLANT_PX > wpx:
                    continue
                if n_ok >= len(self.texts):
                    t = Text(0, 0, "", ha="center", va="center", fontsize=self.fontsize)
                    t.set_figure(ax.figure)
                    t.axes = ax
                    t.set_transform(ax.transData)
                    t.set_clip_path(ax.patch)
                    self.texts.append(t)
                t = self.texts[n_ok]
                t.set_position((c, self.center))
                t.set_text(s)
                n_ok += 1
        self.n_labels = n_ok

    def labels(self) -> List[Tuple[float, str]]:
        """目前寫在框裡的 (x, 文字)（測試／除錯用）。"""
        return [(t.get_position()[0], t.get_text()) for t in self.texts[: self.n_labels]]

    def _relayout_later(self) -> None:
        if self.schedule is None:
            return
        if self._cancel is not None:
            try:
                self._cancel()
            except Exception:
                pass

        def fire():
            self._cancel = None
            self._force = True
            try:
                if self.axes is not None and self.axes.figure.canvas is not None:
                    self.axes.figure.canvas.draw_idle()
            except Exception:
                pass
        self._cancel = self.schedule(RELAYOUT_MS, fire)

    def update_layout(self, force: bool = False) -> None:
        """依目前視圖更新上下緣頂點與文字（draw 會自動呼叫；測試可直接叫）。"""
        if self.axes is None:
            return
        xlo, xhi, w = self._view()
        if not (w > 0 and xhi > xlo and math.isfinite(xlo) and math.isfinite(xhi)):
            return
        k = w / (xhi - xlo)
        ax = self.axes
        key = (xlo, xhi, w, float(ax.bbox.height), tuple(ax.get_ylim()))
        if force or key != self._geom_key:
            self._layout_geometry(xlo, xhi, k)
            self._geom_key = key
        if force or self._force or key != self._label_key:
            same_scale = self._label_k is not None and abs(k - self._label_k) <= 1e-9 * k \
                and self._label_key is not None and self._label_key[2:] == key[2:]
            if same_scale and not (force or self._force) and self.schedule is not None:
                self._relayout_later()             # 只是平移：文字跟著資料座標走，停下來再重排
            else:
                self._layout_labels(xlo, xhi, k)
                self._label_key = key
                self._label_k = k
                self._force = False

    # --- matplotlib --------------------------------------------------------------
    def draw(self, renderer) -> None:
        if not self.get_visible() or self.axes is None:
            return
        try:
            self.update_layout()
        except Exception:
            return
        top = self.top
        self.top.set_marker("None")
        b = self.bottom
        b.set_color(top.get_color())
        b.set_linewidth(top.get_linewidth())
        b.set_linestyle(top.get_linestyle())
        b.set_alpha(top.get_alpha())
        b.set_visible(top.get_visible())
        if top.get_visible():
            b.draw(renderer)
            for t in self.texts[: self.n_labels]:
                t.set_color(top.get_color())
                t.draw(renderer)
        self.stale = False

    def remove(self) -> None:
        if self._cancel is not None:
            try:
                self._cancel()
            except Exception:
                pass
            self._cancel = None
        super().remove()


class HitBusArtist(BusArtist):
    """BusArtist ＋ 一條看不見的 hit 線（頂點＝每個樣本、y＝框中心），線寬跟著框高：點框內任何地方都算點到這條線。"""

    def __init__(self, *a, hit_line: Optional[Line2D] = None, **k):
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


def text_fn_for(radix: str, bits: int, fallback: Callable[[float], str]) -> Callable[[float], Optional[str]]:
    """框內文字：選了進位制用 format_value（非整數退回 fallback），沒選用 fallback（十進位）。"""
    if radix not in RADIXES:
        return fallback
    return lambda v: format_value(v, radix, bits) or fallback(v)


def band_rows(count: int) -> List[Tuple[float, float]]:
    """一張圖只有匯流排時一條一列：由上而下第 i 條的 (中心, 半高)。"""
    return [(float(count - 1 - i), BAND_HALF) for i in range(count)]


def band_from_values(yp) -> Tuple[float, float]:
    """和類比線混在同一軸時：框的上下＝這條訊號（畫出來的值）自己的最小／最大值。"""
    yp = np.asarray(yp, dtype=float)
    fin = yp[np.isfinite(yp)]
    if not fin.size:
        return 0.0, BAND_HALF
    lo, hi = float(fin.min()), float(fin.max())
    if hi <= lo:
        return lo, max(abs(lo) * 0.05, BAND_HALF)
    return 0.5 * (lo + hi), 0.5 * (hi - lo)


# ---------------------------------------------------------------------------
# selftest（plotkit.selftest 呼叫；Agg）
# ---------------------------------------------------------------------------
def selftest(check) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    fv = format_value
    check(fv(171, "hex", 8) == "AB" and fv(171, "hex", 12) == "0AB" and fv(171, "hex", 8, prefix=True) == "0xAB"
          and fv(5, "bin", 4) == "0101" and fv(5, "bin", 4, prefix=True) == "0b0101" and fv(8, "oct", 6) == "10"
          and fv(255, "sdec", 8) == "-1" and fv(127, "sdec", 8) == "127" and fv(-1, "udec", 8) == "255"
          and fv(-1, "hex", 16) == "FFFF" and fv(-2, "sdec", 4) == "-2",
          "format_value：Hex／Binary／Octal 依位元寬度補零、Signed／Unsigned 二補數、負數取低 bits 位")
    check(fv(2.5, "hex", 8) is None and fv(float("nan"), "hex", 8) is None and fv(3, "zzz", 8) is None
          and fv(0x1FF, "hex", 8) == "FF" and fv(300, "udec", 0) == "300",
          "format_value：小數／NaN／不認得的進位制＝None（呼叫端退回十進位）；超出寬度取低位；bits 0＝依值")
    check(range_bits(0, 255) == 8 and range_bits(0, 256) == 9 and range_bits(-128, 127) == 8 and range_bits(-3, 5) == 4
          and range_bits(0, 0) == 1 and clamp_bits("x") == 0 and clamp_bits(99) == MAX_BITS,
          "range_bits：無號／二補數需要的位元數；clamp_bits 0..64")
    check(parse_radix("HEX") == "hex" and parse_radix(None) == "" and parse_radix("dec") == ""
          and parse_display_format("Digital") == "digital" and parse_display_format("x") == "analog" and parse_display_format("auto") == "analog",
          "parse_radix／parse_display_format：不認得＝自動")
    T = transitions([1, 1, 2, 2, np.nan, np.nan, 3])
    check(T.tolist() == [2, 4, 6], f"transitions：值改變的樣本索引、NaN→NaN 不算（{T.tolist()}）")
    check(dedupe_columns(np.array([0.1, 0.2, 1.5, 1.6, 3.0]), 0.0, 1.0).tolist() == [0.1, 1.5, 3.0], "dedupe_columns：同一像素欄只留一個交叉")
    xs, ys = bus_outline(np.array([2.0, 4.0]), 0.0, 6.0, True, True, 0.5, 0.0, 0.4)
    check(xs.tolist() == [0.0, 0.5, 1.5, 2.0, 2.5, 3.5, 4.0, 4.5, 5.5, 6.0]
          and ys.tolist() == [0.0, 0.4, 0.4, 0.0, 0.4, 0.4, 0.0, 0.4, 0.4, 0.0] and np.all(np.diff(xs) >= 0),
          "bus_outline：頭尾尖端、每個轉態上緣降到中心（六角框）、x 遞增")
    xs2, _ys2 = bus_outline(np.array([1.0, 1.2]), 0.0, 3.0, False, False, 0.5, 0.0, 0.4)
    check(xs2[0] == 0.0 and xs2[-1] == 3.0 and np.all(np.diff(xs2) >= -1e-12) and abs(xs2[3] - xs2[2] - 0.1) < 1e-12,
          "bus_outline：切在視圖邊緣平切；相鄰轉態很近時斜邊縮成間距的一半（不交疊）")
    st, cx, w = label_runs(np.array([10, 20, 21, 40]), 0.0, 1.0, 50, 5.0, 45.0, 10.0, 30.0, limit=10)
    check(st.tolist() == [0, 10, 21, 40] and cx.tolist() == [7.5, 15.0, 30.5, 42.5] and w.tolist() == [50.0, 100.0, 190.0, 50.0],
          f"label_runs：只看視圖內的區段、中心取可見部分、太窄（1 個樣本＝10 px）不列（{st.tolist()} {cx.tolist()}）")
    st3, _c3, _w3 = label_runs(np.arange(1, 1000), 0.0, 1.0, 1000, 0.0, 1000.0, 50.0, 10.0, limit=7)
    check(len(st3) == 7, "label_runs：文字數上限")
    # Artist：只畫看得到的、平移防抖、縮放立即重排
    fig = Figure(figsize=(6, 2), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    y = np.repeat(np.arange(100) % 16, 10).astype(float)
    top, = ax.plot([0, 1000], [1, 1])
    jobs = []
    art = BusArtist(ax, top, 0.0, 1.0, y, 0.5, 0.4, lambda v: format_value(v, "hex", 4), schedule=lambda ms, fn: (jobs.append((ms, fn)) or (lambda: None)))
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 1.5)
    fig.canvas.draw()
    l0 = art.labels()
    check(art.n_labels == 10 and [t for _x, t in l0] == [format(i, "X") for i in range(10)] and art.layouts == 1,
          f"BusArtist：視圖內 10 段各寫一個數值（{[t for _x, t in l0]}）")
    check(len(art.bottom.get_xdata()) == len(top.get_xdata()) and np.allclose(art.bottom.get_ydata(), 1.0 - np.asarray(top.get_ydata())),
          "下緣＝上緣對中心鏡射")
    ax.set_xlim(5, 105)
    fig.canvas.draw()
    check(art.layouts == 1 and jobs and jobs[-1][0] == RELAYOUT_MS and art.labels() == l0, "只平移：文字沿用（跟著資料座標移）、排程防抖重排")
    jobs[-1][1]()
    fig.canvas.draw()
    check(art.layouts == 2 and art.n_labels == 11, f"防抖時間到：重排（看得到 11 段：{art.n_labels}）")
    ax.set_xlim(0, 50)
    fig.canvas.draw()
    check(art.layouts == 3 and art.n_labels == 5, "縮放：立即重排")
    top.set_color("#123456")
    top.set_linewidth(3.0)
    fig.canvas.draw()
    check(art.bottom.get_color() == "#123456" and art.bottom.get_linewidth() == 3.0
          and all(t.get_color() == "#123456" for t in art.texts[: art.n_labels]), "下緣與文字跟著上緣的顏色／線寬（選取加粗、改色）")
    import io as _io
    b = _io.BytesIO()
    fig.savefig(b, format="png", bbox_inches="tight")
    check(len(b.getvalue()) > 1000 and art.n_labels == 5, "savefig（bbox_inches=tight）可存、不影響畫面配置")
