# -*- coding: utf-8 -*-
"""平移器（Panner）：MATLAB Signal Analyzer「Display → Panner（View panner）」的 DSV 版，檢視 → 平移器 打開。

主圖下方一條小圖，畫出「目前 panel」顯示中訊號的整段長度（2026-10-25 使用者回報第 12 項：點哪張 panel 就換成那張；
MATLAB Signal Analyzer 也是每個顯示畫面各有自己的 panner 座標區）；上面的縮放窗＝那張 panel 目前的 x 範圍，兩邊即時同步。
照 MathWorks 文件（Signal Analyzer → Explore Signals）：
  - "The panner renders signals in their entire duration."
  - "To select a region of interest, click the panner and drag to create a zoom window."
  - "Use the mouse to resize or slide the zoom window along the length of the signal."
文件沒寫、DSV 自己決定的部分（README 也寫了）：
  - 每條訊號各自正規化到 0..1 再疊（同一張圖裡的訊號大小也可能差上千倍，照原值畫，小的會被壓成一條線）；
  - 點一下沒有拖＝不動；縮放窗滑動、拖邊都不超出訊號範圍；
  - 縮放窗外面變暗，看得出目前在整段的哪裡。
"""
from __future__ import annotations

import math
import warnings
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import tkinter as tk
    from tkinter import ttk
    HAVE_TK = True
except Exception:              # pragma: no cover（headless selftest）
    tk = ttk = None
    HAVE_TK = False

from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator

EDGE_PX = 6.0          # 縮放窗左右邊 ± 幾個邏輯像素內按下＝拖邊調寬度
MIN_DRAG_PX = 3.0      # 新建縮放窗至少拖這麼寬才算（點一下不動）
MAX_POINTS = 4000      # 每條訊號最多畫幾個點（min／max 包絡抽樣：1e6 點也很快，尖峰不會不見）
HEIGHT_PX = 78         # 平移器高度（邏輯像素，含刻度字）
TICK_PX = 20           # 下方刻度字的高度


def envelope(y, x0: float, dx: float, max_points: int = MAX_POINTS) -> Tuple[np.ndarray, np.ndarray]:
    """抽樣成最多 max_points 點的 min／max 包絡（每塊取最小、最大各一點，保留尖峰）；回傳 (x, y)。
    整塊都是 NaN 的保持 NaN（線在那裡斷開）。"""
    y = np.asarray(y, dtype=float)
    n = int(y.size)
    if n == 0:
        return np.zeros(0), np.zeros(0)
    if n <= max_points:
        return float(x0) + np.arange(n) * float(dx), y
    k = int(math.ceil(n / (max_points / 2.0)))
    m = n // k
    blk = y[: m * k].reshape(m, k)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)        # 全 NaN 的塊：nanmin 回 NaN 並警告
        lo = np.nanmin(blk, axis=1)
        hi = np.nanmax(blk, axis=1)
        if m * k < n:
            t = y[m * k:]
            lo = np.append(lo, np.nanmin(t))
            hi = np.append(hi, np.nanmax(t))
    starts = np.arange(lo.size) * k
    xs = float(x0) + starts * float(dx)
    xx = np.repeat(xs, 2)
    yy = np.empty(2 * lo.size)
    yy[0::2] = lo
    yy[1::2] = hi
    return xx, yy


def normalize01(y) -> np.ndarray:
    """有限值的 min..max → 0..1；常數訊號放在 0.5；NaN／Inf → NaN（不畫）。"""
    y = np.asarray(y, dtype=float)
    fin = np.isfinite(y)
    out = np.full(y.shape, np.nan)
    if not fin.any():
        return out
    lo = float(np.min(y[fin]))
    hi = float(np.max(y[fin]))
    if hi > lo:
        out[fin] = (y[fin] - lo) / (hi - lo)
    else:
        out[fin] = 0.5
    return out


def clamp_window(lo: float, hi: float, full: Tuple[float, float]) -> Tuple[float, float]:
    """把 [lo, hi] 平移到 full 範圍內（寬度不變）；比 full 還寬就不動。"""
    a, b = full
    w = hi - lo
    if w >= b - a:
        return lo, hi
    if lo < a:
        lo, hi = a, a + w
    if hi > b:
        lo, hi = b - w, b
    return lo, hi


def drag_window(mode: str, x: float, x_press: float, lo0: float, hi0: float,
                full: Tuple[float, float], min_w: float) -> Optional[Tuple[float, float]]:
    """拖曳中的新縮放窗（資料座標）。mode：move＝整個滑動、left／right＝拖那一邊、new＝從 x_press 拉到 x。
    new 時寬度是 0 回傳 None（還沒拖開）。全部截在 full 範圍內。"""
    a, b = full
    xc = min(max(x, a), b)
    if mode == "move":
        return clamp_window(lo0 + (x - x_press), hi0 + (x - x_press), full)
    if mode == "left":
        return min(xc, hi0 - min_w), hi0
    if mode == "right":
        return lo0, max(xc, lo0 + min_w)
    if mode == "new":
        p = min(max(x_press, a), b)
        lo, hi = min(p, xc), max(p, xc)
        return (lo, hi) if hi - lo >= min_w else None
    return None


def hit_zone(px: float, px_lo: float, px_hi: float, edge: float = EDGE_PX) -> str:
    """按下的位置（像素）在縮放窗的哪裡：left／right（邊上 ±edge）、move（中間）、new（外面）。
    窗太窄（兩邊的判定區重疊）時中間一半算 move，才拖得動。"""
    if px_hi - px_lo < 2 * edge:
        mid = (px_lo + px_hi) / 2.0
        if abs(px - mid) <= max(1.0, (px_hi - px_lo) / 4.0):
            return "move"
    if abs(px - px_lo) <= edge:
        return "left"
    if abs(px - px_hi) <= edge:
        return "right"
    if px_lo < px < px_hi:
        return "move"
    return "new"


class Panner:
    """主圖下方的平移器（Tk frame＋一張小 matplotlib 圖）。

    host 回呼：
      begin()                拖曳開始（主視窗記下原始視圖，讓「上一個視圖／Home」回得去）
      preview(lo, hi)        拖曳中：主圖跟著動（不推 nav stack）
      commit(lo, hi)         放開：主圖定在這個範圍（推 nav stack、狀態列）
    主視窗在畫完主圖後呼叫 set_series()（訊號變了）與 set_view()（x 範圍變了）；x 一律 symbol 單位。"""

    def __init__(self, master, *, begin: Optional[Callable[[], None]] = None,
                 preview: Optional[Callable[[float, float], None]] = None,
                 commit: Optional[Callable[[float, float], None]] = None,
                 px: Callable[[float], int] = lambda v: int(round(v)), height_px: int = HEIGHT_PX):
        self.begin_cb, self.preview_cb, self.commit_cb = begin, preview, commit
        self.px = px
        self.frame = ttk.Frame(master)
        self.fig = Figure(figsize=(6, 0.8), dpi=100)
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.widget = self.canvas.get_tk_widget()
        self.widget.configure(height=px(height_px), highlightthickness=0, takefocus=0)
        self.widget.pack(side="top", fill="x", expand=True)
        self.ax = self.fig.add_axes([0.05, 0.3, 0.9, 0.65])
        self.ax.set_ylim(-0.08, 1.08)
        self.ax.set_yticks([])
        self.ax.xaxis.set_major_locator(MaxNLocator(nbins=10))
        self.factor = 1.0
        self.unit = ""
        self.ax.xaxis.set_major_formatter(FuncFormatter(lambda v, pos: f"{v * self.factor:.6g}"))
        self.full: Optional[Tuple[float, float]] = None
        self.view: Optional[Tuple[float, float]] = None
        self.lines: List[Line2D] = []
        self._align = (None, None)             # (左邊 x、右邊 x)：邏輯像素，和主圖座標區對齊
        self._style: Dict = {}
        self._accent = "#268cdd"
        self._bg = None
        self._drag: Optional[dict] = None
        self._cursor = ""
        # 縮放窗：外面兩塊變暗＋窗框＋兩邊的把手（animated：拖曳時只 blit 這幾個，背景的線不重畫）
        kw = dict(transform=self.ax.get_xaxis_transform(), animated=True, zorder=5)
        self.shade_l = Rectangle((0, 0), 0, 1, lw=0, **kw)
        self.shade_r = Rectangle((0, 0), 0, 1, lw=0, **kw)
        self.win = Rectangle((0, 0), 0, 1, fill=False, lw=1.2, **kw)
        self.grip_l = Line2D([0, 0], [0.2, 0.8], lw=3.0, solid_capstyle="round", **kw)
        self.grip_r = Line2D([0, 0], [0.2, 0.8], lw=3.0, solid_capstyle="round", **kw)
        self._overlay = (self.shade_l, self.shade_r, self.win, self.grip_l, self.grip_r)
        for a in self._overlay:
            self.ax.add_artist(a)
        self.empty_text = self.ax.text(0.5, 0.5, "", transform=self.ax.transAxes, ha="center", va="center", fontsize=8)
        self.canvas.mpl_connect("draw_event", self._on_draw)
        self.canvas.mpl_connect("button_press_event", self._on_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_release)
        self.canvas.mpl_connect("figure_leave_event", lambda e: self._set_cursor(""))
        self.canvas.mpl_connect("resize_event", lambda e: self._apply_align())

    # --- 外觀 -----------------------------------------------------------------------------------------
    def set_style(self, style: dict, accent: str, empty_msg: str = "") -> None:
        """跟主圖同一套顏色（MATLAB 風格深／淺、matplotlib 預設）。"""
        self._style = dict(style or {})
        self._accent = accent or self._accent
        st = self._style
        fg = st.get("text_color", "black")
        self.fig.set_facecolor(st.get("fig_face", "white"))
        self.ax.set_facecolor(st.get("axes_face", "white"))
        for sp in self.ax.spines.values():
            sp.set_color(st.get("axes_edge", fg))
            sp.set_linewidth(float(st.get("axes_lw", 0.8)))
        self.ax.tick_params(axis="x", colors=fg, labelsize=7, length=2, pad=1, direction=st.get("tick_dir", "out"))
        shade = st.get("fig_face", "white")
        for r in (self.shade_l, self.shade_r):
            r.set_facecolor(shade)
            r.set_alpha(0.55)
        self.win.set_edgecolor(self._accent)
        for g in (self.grip_l, self.grip_r):
            g.set_color(self._accent)
        self.empty_text.set_color(fg)
        self.empty_text.set_text(empty_msg)

    def set_units(self, factor: float, unit: str) -> None:
        """刻度字用主圖的顯示單位（symbol → us…）。"""
        self.factor = float(factor or 1.0)
        self.unit = unit or ""

    def align(self, left_px: Optional[float], right_px: Optional[float]) -> None:
        """座標區的左右邊（邏輯像素，從視窗右側區塊的左邊算）和主圖的座標區對齊，上下兩張的 x 才對得起來。"""
        self._align = (left_px, right_px)
        self._apply_align()

    def _apply_align(self) -> None:
        try:
            r = float(getattr(self.canvas, "device_pixel_ratio", 1.0) or 1.0)
            W = float(self.fig.bbox.width) / r
            H = float(self.fig.bbox.height) / r
        except Exception:
            return
        if W <= 10 or H <= 10:
            return
        lp, rp = self._align
        lp = 50.0 if lp is None else float(lp)
        rp = W - 20.0 if rp is None else float(rp)
        lp = max(1.0, min(lp, W - 20))
        rp = max(lp + 10, min(rp, W - 1))
        b = TICK_PX * (self.px(1) or 1) / H
        top = 4.0 / H
        self.ax.set_position([lp / W, b, (rp - lp) / W, max(0.05, 1.0 - b - top)])

    # --- 資料 ---------------------------------------------------------------------------------------
    def set_series(self, series: Sequence[Tuple[np.ndarray, np.ndarray, str]], full: Optional[Tuple[float, float]]) -> None:
        """series：[(x, y_0到1, 顏色)]（已經抽樣、正規化）；full：整段範圍（symbol）。重畫背景。"""
        for ln in self.lines:
            try:
                ln.remove()
            except Exception:
                pass
        self.lines = []
        lw = 0.8
        for x, y, color in series:
            ln, = self.ax.plot(x, y, color=color, lw=lw, zorder=2)
            self.lines.append(ln)
        ok = full is not None and math.isfinite(full[0]) and math.isfinite(full[1]) and full[1] > full[0]
        self.full = (float(full[0]), float(full[1])) if ok else None
        if self.full is not None:
            self.ax.set_xlim(*self.full)
            self.empty_text.set_visible(False)
            self.ax.xaxis.set_visible(True)
        else:
            self.ax.set_xlim(0, 1)
            self.empty_text.set_visible(True)
            self.ax.xaxis.set_visible(False)
        self._update_overlay()
        self.canvas.draw_idle()

    def set_view(self, view: Optional[Tuple[float, float]]) -> None:
        """主圖的 x 範圍變了：只移動縮放窗（blit，不重畫訊號線）。拖曳中不理會（自己正在設）。"""
        if self._drag is not None and self._drag.get("moved"):
            return
        v = None if view is None else (float(min(view)), float(max(view)))
        if v == self.view:
            return
        self.view = v
        self._update_overlay()
        self._blit()

    # --- 縮放窗 ---------------------------------------------------------------------------------------
    def _update_overlay(self) -> None:
        on = self.full is not None and self.view is not None
        for a in self._overlay:
            a.set_visible(on)
        if not on:
            return
        a, b = self.full
        lo, hi = self.view
        lo_c, hi_c = max(lo, a), min(hi, b)          # 主圖縮小到比整段還寬：窗框貼著兩端
        if hi_c < lo_c:                                # 完全在訊號範圍外
            lo_c = hi_c = min(max(lo, a), b)
        self.shade_l.set_x(a)
        self.shade_l.set_width(max(0.0, lo_c - a))
        self.shade_r.set_x(hi_c)
        self.shade_r.set_width(max(0.0, b - hi_c))
        self.win.set_x(lo_c)
        self.win.set_width(max(0.0, hi_c - lo_c))
        self.grip_l.set_xdata([lo_c, lo_c])
        self.grip_r.set_xdata([hi_c, hi_c])

    def _on_draw(self, event) -> None:
        try:
            self._bg = self.canvas.copy_from_bbox(self.fig.bbox)
        except Exception:
            self._bg = None
        self._draw_overlay()

    def _draw_overlay(self) -> None:
        for a in self._overlay:
            if a.get_visible():
                try:
                    self.ax.draw_artist(a)
                except Exception:
                    pass

    def _blit(self) -> None:
        if self._bg is None:
            self.canvas.draw_idle()
            return
        try:
            self.canvas.restore_region(self._bg)
            self._draw_overlay()
            self.canvas.blit(self.fig.bbox)
        except Exception:
            self.canvas.draw_idle()

    # --- 滑鼠 -----------------------------------------------------------------------------------------
    def _data_x(self, event) -> float:
        return float(self.ax.transData.inverted().transform((event.x, event.y))[0])

    def _view_px(self) -> Tuple[float, float]:
        lo, hi = self.view
        a, b = self.full
        p0 = self.ax.transData.transform((max(lo, a), 0))[0]
        p1 = self.ax.transData.transform((min(hi, b), 0))[0]
        return float(p0), float(p1)

    def _dpr(self) -> float:
        return float(getattr(self.canvas, "device_pixel_ratio", 1.0) or 1.0)

    def zone_at(self, event) -> str:
        if self.full is None or self.view is None:
            return ""
        bb = self.ax.bbox
        e = EDGE_PX * self._dpr()
        if not (bb.x0 - e <= event.x <= bb.x1 + e and bb.y0 - TICK_PX * self._dpr() <= event.y <= bb.y1 + e):
            return ""
        p0, p1 = self._view_px()
        return hit_zone(float(event.x), p0, p1, e)

    def _set_cursor(self, name: str) -> None:
        if name == self._cursor:
            return
        self._cursor = name
        try:
            self.widget.configure(cursor=name)
        except Exception:
            pass

    def _on_press(self, event) -> None:
        if event.button != 1 or self.full is None:
            return
        if self.view is None:
            self.view = self.full
        z = self.zone_at(event)
        if not z:
            return
        lo, hi = self.view
        self._drag = {"mode": z, "px": float(event.x), "x": self._data_x(event), "lo0": lo, "hi0": hi,
                      "moved": False, "cur": (lo, hi)}

    def _min_w(self) -> float:
        a, b = self.full
        return max((b - a) * 1e-9, 1e-12)

    def _on_motion(self, event) -> None:
        d = self._drag
        if d is None:
            z = self.zone_at(event)
            self._set_cursor({"left": "sb_h_double_arrow", "right": "sb_h_double_arrow", "move": "fleur"}.get(z, ""))
            return
        if not d["moved"]:
            if abs(float(event.x) - d["px"]) < MIN_DRAG_PX * self._dpr():
                return
            d["moved"] = True
            if self.begin_cb is not None:
                self.begin_cb()
        w = drag_window(d["mode"], self._data_x(event), d["x"], d["lo0"], d["hi0"], self.full, self._min_w())
        if w is None:
            return
        d["cur"] = w
        self.view = w
        self._update_overlay()
        self._blit()
        if self.preview_cb is not None:
            self.preview_cb(*w)

    def _on_release(self, event) -> None:
        d, self._drag = self._drag, None
        if d is None or not d["moved"]:
            return
        lo, hi = d["cur"]
        if d["mode"] == "new" and (lo, hi) == (d["lo0"], d["hi0"]):
            return
        self.view = (lo, hi)
        if self.commit_cb is not None:
            self.commit_cb(lo, hi)

    def cancel_drag(self) -> bool:
        """Esc：拖到一半取消，主圖回到按下前的範圍。"""
        d, self._drag = self._drag, None
        if d is None or not d["moved"]:
            return False
        self.view = (d["lo0"], d["hi0"])
        self._update_overlay()
        self._blit()
        if self.preview_cb is not None:
            self.preview_cb(d["lo0"], d["hi0"])
        return True


def selftest(check) -> None:
    """純函式（不需要 Tk）：抽樣包絡、正規化、拖曳的幾何。"""
    y = np.zeros(1_000_000)
    y[123_457] = 5.0                                  # 單一尖峰：抽樣後還在
    y[600_000:600_010] = np.nan
    x, yy = envelope(y, 10.0, 0.5)
    check(len(x) <= MAX_POINTS + 4 and len(x) == len(yy), f"envelope 點數 {len(x)} ≤ {MAX_POINTS}")
    check(np.nanmax(yy) == 5.0, "envelope 保留尖峰")
    check(x[0] == 10.0 and x[-1] < 10.0 + 0.5 * 1e6, "envelope x 從 x0 開始、在範圍內")
    x2, y2 = envelope(np.arange(10.0), 0.0, 1.0)
    check(len(x2) == 10 and float(y2[3]) == 3.0, "短訊號不抽樣")
    n = normalize01(np.array([2.0, 4.0, np.nan, np.inf, 3.0]))
    check(n[0] == 0.0 and n[1] == 1.0 and math.isnan(n[2]) and math.isnan(n[3]) and n[4] == 0.5, "normalize01 0..1、NaN/Inf 不畫")
    check(np.allclose(normalize01(np.full(4, 7.0)), 0.5), "常數訊號放 0.5")
    full = (0.0, 100.0)
    check(clamp_window(-5, 15, full) == (0.0, 20.0) and clamp_window(90, 110, full) == (80.0, 100.0), "滑動不超出範圍")
    check(drag_window("move", 60, 50, 10, 30, full, 1e-9) == (20.0, 40.0), "move 平移")
    check(drag_window("move", 200, 50, 10, 30, full, 1e-9) == (80.0, 100.0), "move 推到底停在範圍內")
    check(drag_window("left", 5, 10, 10, 30, full, 1e-9) == (5.0, 30.0), "拖左邊")
    check(drag_window("left", 40, 10, 10, 30, full, 1.0) == (29.0, 30.0), "左邊拖過右邊：保留最小寬度")
    check(drag_window("right", 150, 30, 10, 30, full, 1e-9) == (10.0, 100.0), "拖右邊截在範圍內")
    check(drag_window("new", 20, 50, 0, 0, full, 1e-9) == (20.0, 50.0), "new 從按下點拉到目前點（往左）")
    check(drag_window("new", 50, 50, 0, 0, full, 1e-9) is None, "new 沒拖開＝None")
    check(hit_zone(100, 100, 300) == "left" and hit_zone(305, 100, 300) == "right" and hit_zone(200, 100, 300) == "move"
          and hit_zone(50, 100, 300) == "new", "hit_zone 邊／中間／外面")
    check(hit_zone(101, 100, 104) == "move", "窄窗中間可以拖")
