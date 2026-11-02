# -*- coding: utf-8 -*-
"""大資料線條的顯示降採樣（像 MATLAB 對大量資料線條的 LOD）：畫的時候只畫「目前看得到的範圍」每個像素欄的
第一點／最小／最大／最後一點（M4），畫出來和整條畫一樣（每欄的垂直範圍、欄與欄的連接都保留），點數從百萬降到幾千。

只影響畫面：線條本身的資料（get_xdata／get_ydata、點選判定、資料提示、relim）仍是完整的；匯出時依匯出的 dpi 重算。
用法：enable(line) —— 點數超過 LOD_MIN、x 已排序、沒有 marker 的線才會換成 LodLine（其他維持原樣）。
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

import numpy as np
from matplotlib.lines import Line2D

LOD_MIN = 20_000            # 點數超過才降採樣
COLS_PER_PX = 2             # 每個像素切幾欄（2 欄：反鋸齒邊緣也和整條畫一樣）
DENSE_PER_COL = 32          # 每欄平均超過這麼多點才降採樣（不夠密時整條畫也快，而且反鋸齒的深淺和整條畫完全一樣）


class LodLine(Line2D):
    """畫的時候把看得到的範圍降成 M4 子集，交給一條不在 axes 裡的代理 Line2D 畫（樣式用 update_from 複製）。"""

    def _lod_arrays(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        xo, yo = self.get_xdata(orig=True), self.get_ydata(orig=True)
        c = getattr(self, "_lod_src", None)
        if c is not None and c[0] is xo and c[1] is yo:
            return c[2]
        x = np.asarray(xo, dtype=float)
        y = np.asarray(yo, dtype=float)
        ok = (x.ndim == 1 and len(x) == len(y) and len(x) > LOD_MIN
              and bool(np.all(np.diff(x) >= 0)))              # NaN 的 x 也會讓這裡 False → 不降採樣
        arrs = (x, y) if ok else None
        self._lod_src = (xo, yo, arrs)
        self._lod_cache = None
        return arrs

    def _lod_subset(self, renderer):
        ax = self.axes
        if (ax is None or self.get_marker() not in (None, "", "None", " ") or ax.name != "rectilinear"
                or ax.get_xscale() != "linear" or self.get_transform() != ax.transData):
            return None
        arrs = self._lod_arrays()
        if arrs is None:
            return None
        x, y = arrs
        lo, hi = ax.get_xbound()
        width = float(ax.bbox.width)                    # 依目前的 figure dpi（匯出時是匯出的 dpi）
        if not (hi > lo) or not math.isfinite(width) or width < 1:
            return None
        ncols = int(math.ceil(width)) * COLS_PER_PX
        key = (lo, hi, ncols)
        c = getattr(self, "_lod_cache", None)
        if c is not None and c[0] == key:
            return c[1]
        i0 = max(0, int(np.searchsorted(x, lo, "left")) - 1)
        i1 = min(len(x), int(np.searchsorted(x, hi, "right")) + 1)
        if i1 - i0 <= DENSE_PER_COL * ncols:
            sub = None                                   # 看得到的點不多：交給 matplotlib（它自己會只畫看得到的那段；整條畫也快）
        else:
            xs, ys = x[i0:i1], y[i0:i1]
            m = len(xs)
            edges = lo + (hi - lo) * (np.arange(1, ncols) / ncols)     # 欄界：只做 ncols 次二分搜尋，不逐點算欄號
            cuts = np.searchsorted(xs, edges, "left")
            starts = np.unique(np.concatenate(([0, 1, m - 1], cuts)))   # 視圖外左右各一點自成一欄（線要連到邊上）
            starts = starts[(starts >= 0) & (starts < m)]
            ends = np.append(starts[1:], m) - 1
            with np.errstate(invalid="ignore"):
                ymin = np.fmin.reduceat(ys, starts)
                ymax = np.fmax.reduceat(ys, starts)
            mid = (starts + ends) // 2
            k = len(starts)
            sx = np.empty(4 * k)
            sy = np.empty(4 * k)
            sx[0::4], sy[0::4] = xs[starts], ys[starts]
            sx[1::4], sy[1::4] = xs[mid], ymin
            sx[2::4], sy[2::4] = xs[mid], ymax
            sx[3::4], sy[3::4] = xs[ends], ys[ends]
            sub = (sx, sy)
        self._lod_cache = (key, sub)
        return sub

    def draw(self, renderer):
        if not self.get_visible():
            return
        try:
            sub = self._lod_subset(renderer)
        except Exception:
            sub = None
        if sub is None:
            return super().draw(renderer)
        p = getattr(self, "_lod_proxy", None)
        if p is None:
            p = self._lod_proxy = Line2D([], [])
        p.update_from(self)
        p.axes = self.axes
        p.set_figure(self.figure)
        p.set_transform(self.get_transform())
        p.set_clip_box(self.get_clip_box())
        p.set_clip_path(self.get_clip_path())
        p.set_data(*sub)
        p.draw(renderer)
        self.stale = False


def enable(line) -> bool:
    """點數夠多的 Line2D 換成 LodLine（就地換類別，artist 本身與它在 axes 裡的位置不變）。回傳有沒有換。"""
    if type(line) is not Line2D:
        return isinstance(line, LodLine)
    try:
        n = len(line.get_xdata(orig=True))
    except Exception:
        return False
    if n <= LOD_MIN or line.get_marker() not in (None, "", "None", " "):
        return False
    line.__class__ = LodLine
    return True


def selftest(check) -> None:
    """M4 子集：每欄的最小／最大都保留、線條資料不變、不夠密時不降採樣、點選判定仍用完整資料。"""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    rng = np.random.default_rng(5)
    n = 300_000
    x = np.arange(n) / 8.0
    y = rng.normal(0, 1, n)
    y[1234] = 9.0                                      # 單一突波一定要畫得出來
    fig = Figure(figsize=(6, 3), dpi=100)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ln, = ax.step(x, y, where="post")
    small, = ax.plot(x[:1000], y[:1000])
    check(enable(ln) and isinstance(ln, LodLine) and not enable(small) and type(small) is Line2D,
          "lod.enable：大資料線換成 LodLine，小的不換")
    fig.canvas.draw()
    sub = ln._lod_subset(fig.canvas.get_renderer())
    check(sub is not None and len(sub[0]) < 20_000 and float(np.max(sub[1])) == 9.0 and float(np.min(sub[1])) == float(y.min())
          and np.all(np.diff(sub[0]) >= 0), f"lod：全幅降成 {0 if sub is None else len(sub[0])} 點，突波與最小值保留、x 仍排序")
    check(len(ln.get_xdata()) == n and ln.get_ydata()[1234] == 9.0, "lod：線條本身的資料仍是完整的（點選、資料提示、relim 用）")
    ax.set_xlim(100, 200)                              # 800 點：不夠密，整段交給 matplotlib
    fig.canvas.draw()
    check(ln._lod_subset(fig.canvas.get_renderer()) is None, "lod：放大到不夠密時不降採樣")
    ax.set_xlim(0, x[-1])
    w0 = len(sub[0])
    fig.set_dpi(300)                                    # 匯出高 dpi：欄數跟著變多
    fig.canvas.draw()
    sub3 = ln._lod_subset(fig.canvas.get_renderer())
    check(sub3 is not None and len(sub3[0]) > 2 * w0, "lod：高 dpi（匯出）依像素寬重算，點數跟著變多")
