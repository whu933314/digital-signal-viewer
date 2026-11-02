# -*- coding: utf-8 -*-
"""plotkit.cursors — 量測游標（MATLAB Time Scope／Signal Analyzer 的 Data Cursors：None／One／Two）。

一條或兩條垂直游標（標 1、2），貫穿 attach() 給的每個座標區（多 panel 共用 x 軸）；可用滑鼠拖曳、
「Snap to data」吸附到樣本的 x、「Lock cursor spacing」拖一條兩條一起動。游標的 artist 是 animated：每次整張重畫
（draw_event，由 Interactor._on_draw 轉來 on_draw()）先存一份不含游標的背景再把游標畫上去，所以開始拖曳不用整張重畫，
每個 motion 只貼背景＋畫游標（blit），1e6 點的檔也順。別的 blit（host 的十字游標）貼回自己的背景後要呼叫 draw_artists() 補畫游標。
savefig 會畫 animated 的 artist，所以匯出／複製圖時游標照樣在。滑鼠的判定與拖曳由 plotkit.Interactor 轉來（Interactor.cursors＝本物件）：
游標線左右幾個像素內優先於點線釘資料提示、拖曳平移、暫時提示（像 MATLAB）。

host 在 fig.clear() 重畫之後呼叫 attach(axes) 重建 artist；位置（資料 x）與模式留在本物件，重畫不會丟。

水平游標（MATLAB Time Scope 的 Screen Cursors → Horizontal，和垂直的可以同時開）：h_on 開著時每個座標區（attach 的 hkeys 給每個座標區的鍵，
None＝這個座標區不放）各有兩條水平線 y1、y2（該座標區左軸的資料 y），標 1、2 在右緣。同樣可拖、鎖定間距一起動，不吸附（Screen cursor）。

游標的「把手」（handle）：垂直＝0／1（int），水平＝("h", 鍵, 0／1)。點一下游標＝選取（selected，線變粗），
step(handle, n) 給鍵盤微調：垂直 Snap 開＝n 個樣本（host 的 step_fn）、關＝n 個像素；水平＝n 個像素。游標移動不進 undo（MATLAB 也不進）。
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

CURSOR_MODES = ("none", "one", "two")
CURSOR_HIT_PX = 4.0          # 游標線左右這麼多（邏輯）像素內＝抓得到游標
CURSOR_LABELS = ("1", "2")   # Time Scope：游標上方的編號


def cursor_count(mode: str) -> int:
    """模式 → 游標條數（none 0、one 1、two 2；不認得的當 none）。"""
    return {"one": 1, "two": 2}.get(str(mode or "none"), 0)


def default_positions(lo: float, hi: float, mode: str) -> List[float]:
    """剛打開時的位置（MATLAB：放在看得到的地方）：一條＝視圖中央；兩條＝中央 ± 視圖寬的 1/4。"""
    lo, hi = sorted((float(lo), float(hi)))
    c, w = (lo + hi) / 2.0, hi - lo
    n = cursor_count(mode)
    if n == 1:
        return [c]
    if n == 2:
        return [c - w / 4.0, c + w / 4.0]
    return []


def parse_positions(text) -> List[float]:
    """設定檔裡的位置字串（"1.5,3.25"）→ 有限值的 list；壞掉的項目略過。"""
    out: List[float] = []
    if isinstance(text, (list, tuple)):
        items = list(text)
    else:
        items = str(text or "").replace(";", ",").split(",")
    for it in items:
        try:
            v = float(str(it).strip())
        except (TypeError, ValueError):
            continue
        if math.isfinite(v):
            out.append(v)
    return out[:2]


def format_positions(xs: Sequence[float]) -> str:
    return ",".join(repr(float(x)) for x in xs)


def snap_to_grid(x: float, x0: float, dx: float, n: int) -> float:
    """等間隔樣本（x0 + i·dx，i = 0..n-1）裡離 x 最近的那個樣本的 x。"""
    if n <= 0 or not (dx > 0) or not math.isfinite(x):
        return float(x)
    i = int(round((float(x) - float(x0)) / float(dx)))
    i = min(max(i, 0), int(n) - 1)
    return float(x0) + i * float(dx)


def snap_to_samples(xv, x: float) -> float:
    """遞增的樣本 x（不必等間隔）裡離 x 最近的那個；空的回原值。"""
    xv = np.asarray(xv, dtype=float)
    if xv.size == 0 or not math.isfinite(x):
        return float(x)
    j = int(np.searchsorted(xv, x))
    cand = [k for k in (j - 1, j) if 0 <= k < xv.size]
    k = min(cand, key=lambda k: abs(xv[k] - x))
    return float(xv[k])


def default_hpositions(lo: float, hi: float) -> List[float]:
    """水平游標剛打開時的位置：座標區 y 視圖中央 ± 高度的 1/4（y1 在下、y2 在上）。"""
    lo, hi = sorted((float(lo), float(hi)))
    c, h = (lo + hi) / 2.0, hi - lo
    return [c - h / 4.0, c + h / 4.0]


def _hkey(text: str):
    t = str(text).strip()
    try:
        return int(t)
    except ValueError:
        return t


def parse_hpositions(text) -> Dict[Any, List[float]]:
    """設定檔裡的水平游標位置（"1:0.5,1.2;2:-1,1"＝panel 1 的 y1、y2；panel 2 的 …）→ {鍵: [y1, y2]}；壞掉的項目略過。"""
    out: Dict[Any, List[float]] = {}
    if isinstance(text, dict):
        items = [(k, v) for k, v in text.items()]
    else:
        items = []
        for part in str(text or "").split(";"):
            if ":" in part:
                k, v = part.split(":", 1)
                items.append((k, v))
    for k, v in items:
        ys = parse_positions(v)
        if len(ys) == 2 and str(k).strip() != "":
            out[_hkey(k)] = ys
    return out


def format_hpositions(d: Dict[Any, Sequence[float]]) -> str:
    return ";".join(f"{k}:{format_positions(v)}" for k, v in d.items() if len(v) >= 2)


def is_hhandle(h) -> bool:
    """這個把手是不是水平游標（("h", 鍵, i)）。"""
    return isinstance(h, tuple) and len(h) == 3 and h[0] == "h"


def drag_positions(xs: Sequence[float], i: int, new_x: float, lock: bool = False) -> List[float]:
    """第 i 條游標拖到 new_x 之後的全部位置；lock＝鎖定間距（其他游標跟著平移同樣的量）。"""
    xs = [float(v) for v in xs]
    if not (0 <= i < len(xs)):
        return xs
    d = float(new_x) - xs[i]
    if lock:
        return [v + d for v in xs]
    xs[i] = float(new_x)
    return xs


class DataCursors:
    """一組量測游標（模型＋artist＋拖曳）。on_move(xs) 拖曳中每次移動、on_release(xs) 放開（或 Esc 取消）時呼叫；
    snap(x)→x 由 host 提供（例如吸附到選取訊號的樣本），snap_enabled 開著才用。"""

    def __init__(self, canvas, *, on_move: Optional[Callable[[List[float]], None]] = None,
                 on_release: Optional[Callable[[List[float]], None]] = None,
                 snap: Optional[Callable[[float], float]] = None,
                 step_fn: Optional[Callable[[float, int], Optional[float]]] = None):
        self.canvas = canvas
        self.mode = "none"
        self.xs: List[float] = []
        self.lock = False
        self.snap_enabled = False
        self.snap = snap
        self.on_move = on_move
        self.on_release = on_release
        self.axes: list = []
        self.lines: List[list] = []        # 每條游標在每個座標區的 Line2D
        self.labels: List[Any] = []        # 每條游標的編號（最上面那個座標區的頂端）
        self._style: dict = {}
        self._drag: Optional[dict] = None
        self._bg = None
        self.step_fn = step_fn             # (x, n) → 第 n 個相鄰樣本的 x（Snap 開時鍵盤一次一個樣本）；None＝退回像素
        self.h_on = False                  # 水平游標（Screen Cursors → Horizontal）
        self.ys: Dict[Any, List[float]] = {}   # 每個座標區鍵的 [y1, y2]（左軸資料 y）
        self.hkeys: List[Any] = []         # attach 時每個座標區的鍵（None＝不放水平游標）
        self.hlines: Dict[Any, list] = {}
        self.hlabels: Dict[Any, list] = {}
        self.selected: Any = None          # 選取的游標把手（點一下；鍵盤微調的對象）
        self.last: Any = None              # 最近一次移動的把手（host 的 on_release 看這個分辨垂直／水平）

    # --- 狀態 -------------------------------------------------------------------
    @property
    def active(self) -> bool:
        return cursor_count(self.mode) > 0 and len(self.xs) >= cursor_count(self.mode) and bool(self.axes)

    @property
    def dragging(self) -> bool:
        return self._drag is not None

    @property
    def h_active(self) -> bool:
        return bool(self.h_on and self.hlines)

    def positions(self) -> List[float]:
        return list(self.xs[:cursor_count(self.mode)])

    def hpositions(self) -> Dict[Any, List[float]]:
        """目前有放水平游標的座標區：{鍵: [y1, y2]}（沒畫出來的鍵也留在 ys 裡，重畫回來還在原位）。"""
        return {k: list(v) for k, v in self.ys.items() if len(v) >= 2}

    def handles(self) -> list:
        """現在畫得出來的全部把手。"""
        out: list = list(range(len(self.positions()))) if self.active else []
        if self.h_on:
            out += [("h", k, i) for k in self.hlines for i in (0, 1)]
        return out

    def valid(self, h) -> bool:
        return h is not None and h in self.handles()

    def _hax(self, key):
        for ax, k in zip(self.axes, self.hkeys):
            if k is not None and k == key:
                return ax
        return None

    def set_horizontal(self, on: bool, draw: bool = True) -> None:
        """水平游標開／關；打開時沒有位置的座標區放到它的 y 視圖中央 ±1/4。"""
        self.h_on = bool(on)
        self._rebuild(draw)

    def set_hpositions(self, key, ys: Sequence[float], draw: bool = True) -> None:
        self.ys[key] = [float(v) for v in ys][:2]
        self._update_artists()
        if draw:
            self._blit()

    def center_horizontal(self, draw: bool = True) -> None:
        """水平游標移回各座標區目前的 y 視圖（中央 ±1/4）。"""
        for ax, k in zip(self.axes, self.hkeys):
            if k is not None:
                self.ys[k] = default_hpositions(*ax.get_ylim())
        self._update_artists()
        if draw:
            self._blit()

    def select(self, h, draw: bool = True) -> None:
        """選取游標（點一下）：線變粗；鍵盤 ←→（垂直）／↑↓（水平）微調它。None＝取消選取。"""
        h = h if self.valid(h) else None
        if h == self.selected:
            return
        self.selected = h
        self._style_selected()
        if draw:
            self._blit()

    def _style_selected(self) -> None:
        sel = self.selected
        for i, arts in enumerate(self.lines):
            for ln in arts:
                ln.set_linewidth(2.0 if sel == i else 1.0)
        for k, arts in self.hlines.items():
            for i, ln in enumerate(arts):
                ln.set_linewidth(2.0 if sel == ("h", k, i) else 1.0)

    def set_mode(self, mode: str, view=None, draw: bool = True) -> None:
        """換模式；view=(lo, hi)＝目前的 x 視圖：條數變了就照 MATLAB 放到看得到的地方（中央／中央 ±1/4）。"""
        mode = mode if mode in CURSOR_MODES else "none"
        n = cursor_count(mode)
        if n and (mode != self.mode or len(self.xs) < n):
            if view is not None:
                xs = default_positions(view[0], view[1], mode)
            else:
                xs = (self.xs + [0.0, 0.0])[:n]
            self.xs = [self._snapped(x) for x in xs]
        self.mode = mode
        self._rebuild(draw)

    def set_positions(self, xs: Sequence[float], draw: bool = True) -> None:
        self.xs = [float(v) for v in xs][:2]
        self._update_artists()
        if draw:
            self._blit()

    def resnap(self, draw: bool = True) -> None:
        """Snap to data 剛打開：現有游標吸到最近的樣本。"""
        if self.snap_enabled and self.snap is not None and self.xs:
            self.set_positions([self._snapped(x) for x in self.xs], draw)

    def _snapped(self, x: float) -> float:
        if self.snap_enabled and self.snap is not None:
            try:
                v = self.snap(float(x))
                if v is not None and math.isfinite(float(v)):
                    return float(v)
            except Exception:
                pass
        return float(x)

    # --- artist -------------------------------------------------------------------
    def attach(self, axes: Sequence[Any], style: Optional[dict] = None, draw: bool = False,
               hkeys: Optional[Sequence[Any]] = None) -> None:
        """重畫（fig.clear()）之後：在這些座標區重建游標的 artist（axes[0]＝最上面，放編號）。
        hkeys：每個座標區的水平游標鍵（例如 panel 編號；None＝這個座標區不放）；不給＝用 0、1、2…。"""
        self.forget()
        pairs = [(ax, (i if hkeys is None else (list(hkeys) + [None] * len(axes))[i])) for i, ax in enumerate(axes)]
        pairs = [(ax, k) for ax, k in pairs if ax is not None]
        self.axes = [ax for ax, _k in pairs]
        self.hkeys = [k for _ax, k in pairs]
        if style is not None:
            self._style = dict(style)
        self._rebuild(draw)

    def forget(self) -> None:
        """丟掉 artist（host 已經 fig.clear()，或要換一組座標區）；位置與模式保留。"""
        for arts in self.lines:
            for a in arts:
                self._remove(a)
        for a in self.labels:
            self._remove(a)
        for arts in list(self.hlines.values()) + list(self.hlabels.values()):
            for a in arts:
                self._remove(a)
        self.lines, self.labels = [], []
        self.hlines, self.hlabels = {}, {}
        self.axes = []
        self.hkeys = []
        self._drag = None
        self._bg = None

    @staticmethod
    def _remove(a) -> None:
        try:
            a.remove()
        except Exception:
            pass

    def _colors(self) -> tuple:
        st = self._style or {}
        fg = st.get("text_color", "black")
        face = st.get("axes_face", "white")
        return fg, face

    def _rebuild(self, draw: bool = True) -> None:
        from matplotlib.lines import Line2D
        from matplotlib.transforms import offset_copy
        from .draw import add_overlay
        for arts in self.lines:
            for a in arts:
                self._remove(a)
        for a in self.labels:
            self._remove(a)
        for arts in list(self.hlines.values()) + list(self.hlabels.values()):
            for a in arts:
                self._remove(a)
        self.lines, self.labels = [], []
        self.hlines, self.hlabels = {}, {}
        n = cursor_count(self.mode)
        if n and self.axes:
            fg, face = self._colors()
            for i in range(n):
                x = self.xs[i] if i < len(self.xs) else 0.0
                arts = []
                for ax in self.axes:
                    # 不用 axvline：它會把 x 算進 dataLim（自動縮放時把範圍撐開）；add_overlay 讓 matplotlib 3.10 的 relim 也跳過
                    ln = Line2D([x, x], [0, 1], transform=ax.get_xaxis_transform(), color=fg, lw=1.0, ls="--",
                                alpha=0.9, zorder=40, animated=True)
                    ln._pk_cursor = i
                    add_overlay(ax, ln)
                    arts.append(ln)
                self.lines.append(arts)
                top = self.axes[0]
                tr_ = offset_copy(top.get_xaxis_transform(), fig=top.figure, y=-3.0, units="points")   # 框不要被上緣切掉
                t = top.text(x, 1.0, CURSOR_LABELS[i], transform=tr_, ha="center", va="top",
                             fontsize=8, color=fg, zorder=41, clip_on=True, animated=True,
                             bbox=dict(boxstyle="square,pad=0.2", fc=face, ec=fg, lw=0.8))
                t.set_clip_path(top.patch)
                t._pk_cursor = i
                self.labels.append(t)
        if self.h_on and self.axes:
            fg, face = self._colors()
            for ax, key in zip(self.axes, self.hkeys):
                if key is None:
                    continue
                ys = self.ys.get(key) or []
                if len(ys) < 2:
                    ys = self.ys[key] = default_hpositions(*ax.get_ylim())
                lns, labs = [], []
                for i in (0, 1):
                    ln = Line2D([0, 1], [ys[i], ys[i]], transform=ax.get_yaxis_transform(), color=fg, lw=1.0, ls="--",
                                alpha=0.9, zorder=40, animated=True)
                    ln._pk_cursor = ("h", key, i)
                    add_overlay(ax, ln)
                    lns.append(ln)
                    tr_ = offset_copy(ax.get_yaxis_transform(), fig=ax.figure, x=-3.0, units="points")   # 右緣往內一點
                    t = ax.text(1.0, ys[i], CURSOR_LABELS[i], transform=tr_, ha="right", va="center",
                                fontsize=8, color=fg, zorder=41, clip_on=True, animated=True,
                                bbox=dict(boxstyle="square,pad=0.2", fc=face, ec=fg, lw=0.8))
                    t.set_clip_path(ax.patch)
                    t._pk_cursor = ("h", key, i)
                    labs.append(t)
                self.hlines[key] = lns
                self.hlabels[key] = labs
        if not self.valid(self.selected):
            self.selected = None
        self._style_selected()
        if draw:
            self.canvas.draw_idle()

    def _update_artists(self) -> None:
        for i, arts in enumerate(self.lines):
            if i >= len(self.xs):
                break
            x = self.xs[i]
            for ln in arts:
                ln.set_xdata([x, x])
            if i < len(self.labels):
                self.labels[i].set_x(x)
        for k, arts in self.hlines.items():
            ys = self.ys.get(k) or []
            for i, ln in enumerate(arts):
                if i < len(ys):
                    ln.set_ydata([ys[i], ys[i]])
                    if i < len(self.hlabels.get(k, [])):
                        self.hlabels[k][i].set_y(ys[i])

    def artists(self) -> list:
        out = [a for arts in self.lines for a in arts] + list(self.labels)
        for k in self.hlines:
            out += list(self.hlines[k]) + list(self.hlabels.get(k, []))
        return out

    def on_draw(self) -> None:
        """整張重畫之後（draw_event；savefig 不算）：存不含游標的背景，再把游標畫上去。"""
        c = self.canvas
        if not self.lines and not self.hlines:
            self._bg = None
            return
        try:
            self._bg = c.copy_from_bbox(c.figure.bbox)
        except Exception:
            self._bg = None
        self.draw_artists()

    def draw_artists(self) -> None:
        """把游標畫進目前的畫布緩衝區（不 blit）；host 自己的 blit 貼回背景後呼叫，游標才不會被蓋掉。"""
        for a in self.artists():
            try:
                if a.get_visible() and a.axes is not None:
                    a.axes.draw_artist(a)
            except Exception:
                pass

    # --- 判定 ------------------------------------------------------------------
    def _dpr(self) -> float:
        try:
            return float(getattr(self.canvas, "device_pixel_ratio", 1) or 1)
        except Exception:
            return 1.0

    def _ax_at(self, px: float, py: float):
        for ax in self.axes:
            try:
                if ax.bbox.contains(px, py):
                    return ax
            except Exception:
                continue
        return None

    def hit(self, event):
        """滑鼠（matplotlib 像素座標）在哪條游標上（線左右／上下 CURSOR_HIT_PX 像素內，或編號框上）→ 把手
        （垂直 0／1、水平 ("h", 鍵, i)；兩種都在範圍內取近的，一樣近取垂直）；都不是回 None。"""
        if not (self.active or self.h_active) or getattr(event, "x", None) is None or getattr(event, "y", None) is None:
            return None
        px, py = float(event.x), float(event.y)
        ax = self._ax_at(px, py)
        if ax is None:
            return None
        tol = CURSOR_HIT_PX * self._dpr()
        best, best_d = None, None
        r = None
        try:
            r = self.canvas.get_renderer() if hasattr(self.canvas, "get_renderer") else None
        except Exception:
            r = None
        for i, x in enumerate(self.positions() if self.active else []):
            try:
                cx = float(ax.transData.transform((x, 0.0))[0])
            except Exception:
                continue
            d = abs(cx - px)
            lab_hit = False
            if i < len(self.labels):
                try:
                    lab_hit = r is not None and self.labels[i].get_window_extent(r).contains(px, py)
                except Exception:
                    lab_hit = False
            if (d <= tol or lab_hit) and (best_d is None or d < best_d):
                best, best_d = i, (0.0 if lab_hit else d)
        if self.h_on:
            try:
                key = self.hkeys[self.axes.index(ax)]
            except (ValueError, IndexError):
                key = None
            if key is not None and key in self.hlines:
                for i, y in enumerate((self.ys.get(key) or [])[:2]):
                    try:
                        cy = float(ax.transData.transform((0.0, y))[1])
                    except Exception:
                        continue
                    d = abs(cy - py)
                    lab_hit = False
                    try:
                        lab_hit = r is not None and self.hlabels[key][i].get_window_extent(r).contains(px, py)
                    except Exception:
                        lab_hit = False
                    if (d <= tol or lab_hit) and (best_d is None or d < best_d):
                        best, best_d = ("h", key, i), (0.0 if lab_hit else d)
        return best

    def x_at(self, px: float) -> Optional[float]:
        """畫面 x 像素 → 資料 x（用第一個座標區；各 panel 共用 x 軸）。"""
        if not self.axes:
            return None
        ax = self.axes[0]
        try:
            return float(ax.transData.inverted().transform((float(px), float(ax.bbox.y0)))[0])
        except Exception:
            return None

    # --- 拖曳（blit）---------------------------------------------------------------
    def y_at(self, ax, py: float) -> Optional[float]:
        """畫面 y 像素 → 這個座標區的資料 y。"""
        try:
            return float(ax.transData.inverted().transform((float(ax.bbox.x0), float(py)))[1])
        except Exception:
            return None

    def begin_drag(self, i, px: float, py: Optional[float] = None) -> bool:
        if is_hhandle(i):
            _h, key, j = i
            ax = self._hax(key)
            if not self.h_on or ax is None or key not in self.hlines or py is None:
                return False
            y_mouse = self.y_at(ax, py)
            ys = self.ys[key]
            grab = 0.0 if y_mouse is None else ys[j] - y_mouse
            self._drag = {"i": i, "grab": grab, "xs0": list(self.xs), "ys0": list(ys)}
        else:
            if not self.active or not (0 <= int(i) < len(self.positions())):
                return False
            x_mouse = self.x_at(px)
            grab = 0.0 if x_mouse is None else self.xs[int(i)] - x_mouse     # 抓在線旁邊幾個像素：不要一抓就跳過去
            self._drag = {"i": int(i), "grab": grab, "xs0": list(self.xs)}
        self.last = self._drag["i"]
        if self._bg is None:                     # 還沒畫過（或 host 沒把 draw_event 轉來）：整張畫一次存背景
            try:
                self.canvas.draw()
                if self._bg is None:
                    self.on_draw()
            except Exception:
                self._bg = None
        return True

    def drag(self, px: float, py: Optional[float] = None) -> Optional[List[float]]:
        d = self._drag
        if d is None:
            return None
        if is_hhandle(d["i"]):
            _h, key, j = d["i"]
            ax = self._hax(key)
            y = self.y_at(ax, py) if (ax is not None and py is not None) else None
            if y is None:
                return None
            y += d["grab"]
            self._move_h(key, j, y)
            return self.positions()
        x = self.x_at(px)
        if x is None:
            return None
        x += d["grab"]
        try:
            lo, hi = sorted(self.axes[0].get_xlim())
            x = min(max(x, lo), hi)                                      # 拖不出看得到的範圍（MATLAB 也是）
        except Exception:
            pass
        x = self._snapped(x)
        self.xs = drag_positions(self.xs, d["i"], x, self.lock)
        self._update_artists()
        self._blit()
        if self.on_move is not None:
            self.on_move(self.positions())
        return self.positions()

    def _blit(self) -> None:
        c = self.canvas
        if self._bg is None or getattr(c, "_idle_draw_id", None):    # 沒有背景、或已經排了整張重畫：交給整張重畫
            c.draw_idle()
            return
        try:
            c.restore_region(self._bg)
            self.draw_artists()
            c.blit(c.figure.bbox)
        except Exception:
            c.draw_idle()

    def end_drag(self) -> Optional[List[float]]:
        d, self._drag = self._drag, None
        if d is None:
            return None
        self._blit()                             # 畫面已經是最後的位置；背景（不含游標）留著給下一次拖曳
        if self.on_release is not None:
            self.on_release(self.positions())
        return self.positions()

    def cancel_drag(self) -> None:
        d = self._drag
        if d is None:
            return
        self.xs = list(d["xs0"])
        if is_hhandle(d["i"]):
            self.ys[d["i"][1]] = list(d["ys0"])
        self._update_artists()
        self.end_drag()

    def _move_h(self, key, j: int, y: float) -> None:
        """水平游標 j 移到 y（夾在該座標區的 y 視圖內；鎖定間距時兩條一起動），blit、通知 host。"""
        ax = self._hax(key)
        try:
            lo, hi = sorted(ax.get_ylim())
            y = min(max(float(y), lo), hi)
        except Exception:
            pass
        self.ys[key] = drag_positions(self.ys.get(key) or [y, y], j, y, self.lock)
        self.last = ("h", key, j)
        self._update_artists()
        self._blit()
        if self.on_move is not None:
            self.on_move(self.positions())

    # --- 鍵盤微調 ----------------------------------------------------------------
    def step(self, h, n: int) -> bool:
        """把手 h 的游標移 n 步（鍵盤；n<0 往左／下）：垂直 Snap 開＝n 個樣本（step_fn；沒有就退回像素）、關＝n 個像素；
        水平＝n 個像素。夾在看得到的範圍內（拖曳也拖不出去），鎖定間距照樣兩條一起動。移了回 True，並呼叫 on_move／on_release。"""
        if not self.valid(h) or not n:
            return False
        dpr = self._dpr()
        if is_hhandle(h):
            _h, key, j = h
            ax = self._hax(key)
            ys = self.ys.get(key) or []
            if ax is None or len(ys) <= j:
                return False
            cy = float(ax.transData.transform((0.0, ys[j]))[1])
            y = self.y_at(ax, cy + n * dpr)
            if y is None:
                return False
            old = list(ys)
            self._move_h(key, j, y)
            moved = self.ys[key] != old
        else:
            i = int(h)
            x0 = self.xs[i]
            x = None
            if self.snap_enabled and self.step_fn is not None:
                try:
                    x = self.step_fn(x0, int(n))
                except Exception:
                    x = None
            try:
                lo, hi = sorted(self.axes[0].get_xlim())
            except Exception:
                lo, hi = -math.inf, math.inf
            if x is not None and not (lo <= float(x) <= hi):
                return False                    # 下一個樣本已經在看得到的範圍外：不動（拖曳也拖不出去）
            if x is None:                       # Snap 關（或 host 沒給 step_fn）：n 個像素
                ax = self.axes[0]
                cx = float(ax.transData.transform((x0, 0.0))[0])
                x = self.x_at(cx + n * dpr)
                if x is None:
                    return False
                x = min(max(float(x), lo), hi)
            old = list(self.xs)
            self.xs = drag_positions(self.xs, i, x, self.lock)
            self.last = i
            self._update_artists()
            self._blit()
            if self.on_move is not None:
                self.on_move(self.positions())
            moved = self.xs != old
        if moved and self.on_release is not None:
            self.on_release(self.positions())
        return moved
