# -*- coding: utf-8 -*-
"""plotkit.icons — 工具列用的單線條圖示（照 MATLAB 圖示風格：1px 線、淺灰底、少量藍／橘強調色）。

用 Pillow（matplotlib 的相依套件，一定裝得到）在 4 倍解析度畫好再縮小，所以邊緣是反鋸齒的；
顏色由主題給（深色主題淺灰線、淺色主題深灰線）。沒有 Pillow 時 get_icon() 回 None，呼叫端就退回純文字按鈕。
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageTk
    HAVE_PIL = True
except Exception:                     # pragma: no cover
    Image = ImageDraw = ImageTk = None
    HAVE_PIL = False

SS = 4                                # 超取樣倍率

Palette = Dict[str, str]
DEFAULT_PALETTE: Palette = {"fg": "#d9d9d9", "fg2": "#888888", "fill": "#333333", "accent": "#268cdd",
                            "orange": "#f57729", "green": "#49db40", "red": "#ff7a74", "white": "#ffffff"}


class _D:
    """把 16 單位座標畫到 size×SS 的 RGBA 影像上。"""

    def __init__(self, size: int, pal: Palette):
        self.k = size * SS / 16.0
        self.im = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.pal = pal

    def c(self, name: Optional[str]):
        if name is None:
            return None
        return self.pal.get(name, name)

    def p(self, x, y):
        return (x * self.k, y * self.k)

    def line(self, pts, color="fg", w=1.2):
        xy = [self.p(x, y) for x, y in pts]
        self.d.line(xy, fill=self.c(color), width=max(1, int(round(w * self.k))), joint="curve")

    def rect(self, x0, y0, x1, y1, fill=None, outline="fg", w=1.2, r=0.0):
        wi = max(1, int(round(w * self.k))) if outline else 0
        box = [self.p(x0, y0), self.p(x1, y1)]
        if r > 0:
            self.d.rounded_rectangle(box, radius=r * self.k, fill=self.c(fill), outline=self.c(outline), width=wi)
        else:
            self.d.rectangle(box, fill=self.c(fill), outline=self.c(outline), width=wi)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline="fg", w=1.2):
        wi = max(1, int(round(w * self.k))) if outline else 0
        self.d.ellipse([self.p(x0, y0), self.p(x1, y1)], fill=self.c(fill), outline=self.c(outline), width=wi)

    def poly(self, pts, fill="fg", outline=None, w=1.0):
        self.d.polygon([self.p(x, y) for x, y in pts], fill=self.c(fill), outline=self.c(outline),
                       width=max(1, int(round(w * self.k))) if outline else 0)

    def arc(self, x0, y0, x1, y1, a0, a1, color="fg", w=1.2):
        self.d.arc([self.p(x0, y0), self.p(x1, y1)], a0, a1, fill=self.c(color), width=max(1, int(round(w * self.k))))

    def arrow(self, x0, y0, x1, y1, color="fg", w=1.2, head=2.6):
        self.line([(x0, y0), (x1, y1)], color, w)
        ang = math.atan2(y1 - y0, x1 - x0)
        for s in (-1, 1):
            a = ang + math.pi + s * 0.5
            self.line([(x1, y1), (x1 + head * math.cos(a), y1 + head * math.sin(a))], color, w)

    def wave(self, x0, x1, yc, amp, periods=1.5, color="accent", w=1.2, n=40):
        pts = []
        for i in range(n + 1):
            t = i / n
            pts.append((x0 + (x1 - x0) * t, yc - amp * math.sin(2 * math.pi * periods * t)))
        self.line(pts, color, w)

    def square(self, x0, x1, ylo, yhi, color="accent", w=1.2, steps=4):
        pts = []
        dx = (x1 - x0) / steps
        y = yhi
        for i in range(steps):
            pts += [(x0 + i * dx, y), (x0 + (i + 1) * dx, y)]
            y = ylo if y == yhi else yhi
        self.line(pts, color, w)


_ICONS: Dict[str, Callable[[_D], None]] = {}


def icon(name):
    def deco(fn):
        _ICONS[name] = fn
        return fn
    return deco


# --- 檔案／資料夾 ---------------------------------------------------------------
@icon("folder")
def _folder(d):
    d.poly([(1.5, 4), (6, 4), (7.5, 5.5), (14.5, 5.5), (14.5, 13.5), (1.5, 13.5)], fill="fill", outline="fg")
    d.line([(1.5, 7), (14.5, 7)], "fg", 1.0)


@icon("folder_open")
def _folder_open(d):
    d.poly([(1.5, 4), (6, 4), (7.5, 5.5), (13.5, 5.5), (13.5, 7.5), (3.5, 7.5), (1.5, 13.5)], fill="fill", outline="fg")
    d.poly([(3.5, 7.5), (15, 7.5), (13, 13.5), (1.5, 13.5)], fill="fill", outline="fg")


@icon("refresh")
def _refresh(d):
    d.arc(2.5, 2.5, 13.5, 13.5, 300, 240, "fg", 1.4)
    d.poly([(13.8, 2.5), (14.2, 7.5), (9.5, 6.2)], fill="fg")


@icon("import")
def _import(d):
    d.rect(3.5, 1.5, 12.5, 14.5, fill="fill", outline="fg", r=0.8)
    d.arrow(8, 4, 8, 11, "accent", 1.4)
    d.line([(5.5, 12.2), (10.5, 12.2)], "accent", 1.4)


@icon("export")
def _export(d):
    d.rect(3.5, 1.5, 12.5, 14.5, fill="fill", outline="fg", r=0.8)
    d.arrow(8, 11.5, 8, 4.3, "accent", 1.4)
    d.line([(5.5, 12.8), (10.5, 12.8)], "accent", 1.4)


@icon("csv")
def _csv(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill="fill", outline="fg", r=0.6)
    for y in (6.2, 9.8):
        d.line([(2.5, y), (13.5, y)], "fg", 0.9)
    for x in (6.2, 9.8):
        d.line([(x, 2.5), (x, 13.5)], "fg", 0.9)


@icon("save")
def _save(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill="fill", outline="fg", r=0.8)
    d.rect(5, 2.5, 11, 6.5, fill="fg2", outline=None)
    d.rect(4.5, 9, 11.5, 13.5, fill="white", outline="fg", w=1.0)


@icon("open")
def _open(d):
    _folder_open(d)


@icon("settings_in")
def _settings_in(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill="fill", outline="fg", r=0.8)
    d.arrow(11.5, 8, 5.5, 8, "accent", 1.4)


@icon("settings_out")
def _settings_out(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill="fill", outline="fg", r=0.8)
    d.arrow(5, 8, 11.5, 8, "accent", 1.4)


@icon("txt")
def _txt(d):
    d.rect(3.5, 1.5, 12.5, 14.5, fill="fill", outline="fg", r=0.8)
    for y in (5, 7.5, 10, 12.5):
        d.line([(5.5, y), (10.5, y)], "fg", 0.9)


@icon("file")
def _file(d):
    d.poly([(3.5, 1.5), (9.5, 1.5), (12.5, 4.5), (12.5, 14.5), (3.5, 14.5)], fill="fill", outline="fg")
    d.line([(9.5, 1.5), (9.5, 4.5), (12.5, 4.5)], "fg", 0.9)


@icon("wave_file")
def _wave_file(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill="fill", outline="fg", r=0.6)
    d.line([(3.5, 8), (5, 5), (6.5, 11), (8, 5), (9.5, 11), (11, 5), (12.5, 8)], "accent", 1.1)


# --- 導覽／編輯 ---------------------------------------------------------------
@icon("home")
def _home(d):
    d.poly([(8, 2), (14.5, 8), (12.5, 8), (12.5, 14), (3.5, 14), (3.5, 8), (1.5, 8)], fill="fill", outline="fg")
    d.rect(6.8, 10, 9.2, 14, fill="fg2", outline=None)


@icon("back")
def _back(d):
    d.arrow(13, 8, 3, 8, "fg", 1.5, 3.2)


@icon("forward")
def _forward(d):
    d.arrow(3, 8, 13, 8, "fg", 1.5, 3.2)


@icon("undo")
def _undo(d):
    d.arc(4, 4, 14, 14, 200, 90, "fg", 1.4)
    d.poly([(2, 7.5), (7.5, 4.3), (7.2, 9.6)], fill="fg")


@icon("redo")
def _redo(d):
    d.arc(2, 4, 12, 14, 90, 340, "fg", 1.4)
    d.poly([(14, 7.5), (8.5, 4.3), (8.8, 9.6)], fill="fg")


@icon("up")
def _up(d):
    d.arrow(8, 13.5, 8, 3, "fg", 1.5, 3.2)


@icon("down")
def _down(d):
    d.arrow(8, 2.5, 8, 13, "fg", 1.5, 3.2)


@icon("sort")
def _sort(d):
    for i, w in enumerate((10, 7.5, 5)):
        y = 4 + i * 3.6
        d.line([(3, y), (3 + w, y)], "fg", 1.4)
    d.arrow(13.5, 3, 13.5, 13, "accent", 1.2, 2.2)


@icon("remove")
def _remove(d):
    d.line([(4, 4), (12, 12)], "fg", 1.5)
    d.line([(12, 4), (4, 12)], "fg", 1.5)


@icon("clear")
def _clear(d):
    d.rect(4, 4.5, 12, 14, fill="fill", outline="fg", r=0.6)
    d.line([(2.5, 4.5), (13.5, 4.5)], "fg", 1.3)
    d.line([(6.3, 2.5), (9.7, 2.5)], "fg", 1.3)
    for x in (6.5, 8, 9.5):
        d.line([(x, 7), (x, 12)], "fg", 0.9)


@icon("select_all")
def _select_all(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill="fill", outline="fg", r=0.6)
    d.line([(4.5, 8.2), (7, 10.8), (11.8, 5.2)], "accent", 1.6)


@icon("merge")
def _merge(d):
    d.rect(2, 2.5, 14, 13.5, fill=None, outline="fg", r=0.4)
    d.wave(3, 13, 8, 3.2, 1.5, "accent", 1.2)
    d.square(3, 13, 10.5, 5.5, "orange", 1.2, 4)


@icon("split")
def _split(d):
    d.rect(2, 1.5, 14, 7, fill=None, outline="fg", r=0.4)
    d.rect(2, 9, 14, 14.5, fill=None, outline="fg", r=0.4)
    d.wave(3, 13, 4.25, 1.6, 1.5, "accent", 1.2)
    d.square(3, 13, 13, 10.5, "orange", 1.2, 4)


@icon("plot")
def _plot(d):
    d.line([(2.5, 2.5), (2.5, 13.5), (14, 13.5)], "fg", 1.2)
    d.wave(3.5, 13.5, 8, 3.5, 1.5, "accent", 1.5)


@icon("run")
def _run(d):
    d.poly([(4, 2.5), (13.5, 8), (4, 13.5)], fill="green")


@icon("fit")
def _fit(d):
    d.rect(2, 2, 14, 14, fill=None, outline="fg", r=0.4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = 8 + sx * 3.8, 8 + sy * 3.8
            d.line([(cx, cy), (cx - sx * 2.4, cy)], "accent", 1.3)
            d.line([(cx, cy), (cx, cy - sy * 2.4)], "accent", 1.3)


@icon("zoom")
def _zoom(d):
    d.ellipse(2, 2, 10.5, 10.5, fill="fill", outline="fg", w=1.3)
    d.line([(9.5, 9.5), (14, 14)], "fg", 2.0)
    d.line([(4.5, 6.2), (8, 6.2)], "accent", 1.3)
    d.line([(6.2, 4.5), (6.2, 8)], "accent", 1.3)


@icon("zoom_out")
def _zoom_out(d):
    d.ellipse(2, 2, 10.5, 10.5, fill="fill", outline="fg", w=1.3)
    d.line([(9.5, 9.5), (14, 14)], "fg", 2.0)
    d.line([(4.5, 6.2), (8, 6.2)], "accent", 1.3)


@icon("pan")
def _pan(d):
    d.arrow(8, 8, 8, 1.8, "fg", 1.2, 2.2)
    d.arrow(8, 8, 8, 14.2, "fg", 1.2, 2.2)
    d.arrow(8, 8, 1.8, 8, "fg", 1.2, 2.2)
    d.arrow(8, 8, 14.2, 8, "fg", 1.2, 2.2)


@icon("datatip")
def _datatip(d):
    d.wave(1.5, 14.5, 10, 3, 1.0, "accent", 1.2)
    d.rect(6.5, 1.5, 14.5, 6.5, fill="white", outline="fg", w=1.0, r=0.6)
    d.line([(8, 6.5), (6.5, 8.8)], "fg", 1.0)
    d.ellipse(5.3, 7.6, 7.7, 10),


@icon("cursor")
def _cursor(d):
    d.line([(8, 1.5), (8, 14.5)], "fg", 1.0)
    d.line([(1.5, 8), (14.5, 8)], "fg", 1.0)
    d.ellipse(5.5, 5.5, 10.5, 10.5, fill=None, outline="accent", w=1.2)


@icon("dcursors")
def _dcursors(d):
    d.square(1.5, 14.5, 13, 8.5, "accent", 1.1, 3)
    for x in (5, 11):
        for y0 in (5.5, 8.5, 11.5):
            d.line([(x, y0), (x, y0 + 1.8)], "orange", 1.1)
        d.rect(x - 1.8, 1, x + 1.8, 4.6, fill="white", outline="fg", w=0.9, r=0.3)


@icon("dcursor_center")
def _dcursor_center(d):
    d.rect(1.5, 2.5, 14.5, 13.5, fill="fill", outline="fg", w=1.0, r=0.4)
    for x in (5.5, 10.5):
        d.line([(x, 4), (x, 12)], "orange", 1.2)
    d.arrow(2.5, 8, 4.8, 8, "accent", 1.0, 1.6)
    d.arrow(13.5, 8, 11.2, 8, "accent", 1.0, 1.6)


@icon("tip_export")
def _tip_export(d):
    d.rect(1.5, 1.5, 10.5, 7.5, fill="white", outline="fg", w=1.0, r=0.6)
    d.line([(3, 3.6), (9, 3.6)], "fg2", 0.9)
    d.line([(3, 5.6), (7.5, 5.6)], "fg2", 0.9)
    d.rect(5.5, 9, 14.5, 14.5, fill="fill", outline="fg", w=1.0, r=0.5)
    d.arrow(10, 13.5, 10, 9.8, "accent", 1.3, 2.0)


@icon("tip_fields")
def _tip_fields(d):
    d.rect(1.5, 1.5, 14.5, 14.5, fill="white", outline="fg", w=1.0, r=0.6)
    for y in (4.5, 8, 11.5):
        d.rect(3.2, y - 1.2, 5.6, y + 1.2, fill="accent", outline=None)
        d.line([(7, y), (13, y)], "fg2", 1.0)


@icon("color")
def _color(d):
    d.ellipse(2, 2, 14, 14, fill="fill", outline="fg", w=1.2)
    d.ellipse(4.2, 4.5, 7.2, 7.5, fill="accent", outline=None)
    d.ellipse(8.8, 4.2, 11.8, 7.2, fill="orange", outline=None)
    d.ellipse(5.2, 9, 8.2, 12),
    d.ellipse(5.2, 9, 8.2, 12, fill="green", outline=None)
    d.ellipse(9.3, 8.8, 12.3, 11.8, fill="red", outline=None)


@icon("copy")
def _copy(d):
    d.rect(1.5, 1.5, 9.5, 9.5, fill="fg2", outline="fg", w=1.0, r=0.6)
    d.rect(5.5, 5.5, 14.5, 14.5, fill="white", outline="fg", w=1.0, r=0.6)


@icon("paste")
def _paste(d):
    d.rect(2.5, 3, 11.5, 14.5, fill="fill", outline="fg", w=1.0, r=0.6)
    d.rect(5, 1.5, 9, 4.5, fill="fg2", outline="fg", w=0.9, r=0.4)
    d.rect(7.5, 7.5, 14.5, 14.5, fill="white", outline="fg", w=1.0, r=0.6)


@icon("new_window")
def _new_window(d):
    d.rect(1.5, 2.5, 14.5, 13.5, fill="fill", outline="fg", w=1.0, r=0.6)
    d.rect(1.5, 2.5, 14.5, 5, fill="fg2", outline="fg", w=1.0)
    d.line([(8, 7), (8, 12)], "accent", 1.4)
    d.line([(5.5, 9.5), (10.5, 9.5)], "accent", 1.4)


@icon("copy_window")
def _copy_window(d):
    d.rect(1.5, 1.5, 10.5, 9.5, fill="fg2", outline="fg", w=1.0, r=0.5)
    d.rect(5.5, 6, 14.5, 14.5, fill="fill", outline="fg", w=1.0, r=0.5)
    d.rect(5.5, 6, 14.5, 8, fill="fg2", outline="fg", w=1.0)
    d.wave(6.5, 13.5, 11.5, 1.5, 1.0, "accent", 1.1)


@icon("clipboard")
def _clipboard(d):
    d.rect(3, 3, 13, 14.5, fill="fill", outline="fg", w=1.0, r=0.6)
    d.rect(6, 1.5, 10, 4.5, fill="fg2", outline="fg", w=0.9, r=0.4)
    d.wave(4.5, 11.5, 9.5, 1.8, 1.0, "accent", 1.1)


@icon("spectrum")
def _spectrum(d):
    d.line([(2, 13.5), (14.5, 13.5)], "fg", 1.0)
    for x, h in ((3.5, 3), (5.5, 7), (7.5, 11), (9.5, 6), (11.5, 4), (13.5, 2)):
        d.line([(x, 13.5), (x, 13.5 - h)], "accent", 1.5)


@icon("gfsk")
def _gfsk(d):
    pts = []
    for i in range(41):
        t = i / 40
        f = 2.0 + 2.5 * (0.5 + 0.5 * math.sin(2 * math.pi * t))
        pts.append((1.5 + 13 * t, 8 - 4 * math.sin(2 * math.pi * f * t)))
    d.line(pts, "accent", 1.2)


@icon("despike")
def _despike(d):
    d.square(1.5, 14.5, 11, 5, "accent", 1.2, 4)
    d.line([(8, 5), (8, 1.5)], "red", 1.2)
    d.line([(6.5, 1.5), (9.5, 4)], "fg", 1.0)
    d.line([(9.5, 1.5), (6.5, 4)], "fg", 1.0)


@icon("diff")
def _diff(d):
    d.square(1.5, 14.5, 6, 3, "accent", 1.1, 4)
    d.square(1.5, 14.5, 13, 10, "orange", 1.1, 4)
    d.rect(5.5, 2, 9.5, 14, fill=None, outline="red", w=1.0)


@icon("prev")
def _prev(d):
    d.poly([(11, 3), (11, 13), (4, 8)], fill="fg")


@icon("next")
def _next(d):
    d.poly([(5, 3), (5, 13), (12, 8)], fill="fg")


@icon("grid")
def _grid(d):
    d.rect(2, 2, 14, 14, fill=None, outline="fg", w=1.0)
    for v in (6, 10):
        d.line([(2, v), (14, v)], "fg2", 0.9)
        d.line([(v, 2), (v, 14)], "fg2", 0.9)


@icon("legend")
def _legend(d):
    d.rect(1.5, 2.5, 14.5, 13.5, fill="fill", outline="fg", w=1.0, r=0.4)
    for y, col in ((5.5, "accent"), (8, "orange"), (10.5, "green")):
        d.line([(3.5, y), (7, y)], col, 1.4)
        d.line([(8.5, y), (12.5, y)], "fg", 1.0)


@icon("marker")
def _marker(d):
    d.wave(1.5, 14.5, 8, 3.5, 1.0, "fg2", 1.0, 40)
    for t in (0.1, 0.3, 0.5, 0.7, 0.9):
        x = 1.5 + 13 * t
        y = 8 - 3.5 * math.sin(2 * math.pi * 1.0 * t)
        d.ellipse(x - 1.4, y - 1.4, x + 1.4, y + 1.4, fill="accent", outline=None)


@icon("search")
def _search(d):
    d.ellipse(2, 2, 10, 10, fill=None, outline="fg", w=1.3)
    d.line([(9.2, 9.2), (14, 14)], "fg", 2.0)


@icon("expand")
def _expand(d):
    d.line([(2.5, 5), (8, 10.5), (13.5, 5)], "fg", 1.6)


@icon("collapse")
def _collapse(d):
    d.line([(5, 2.5), (10.5, 8), (5, 13.5)], "fg", 1.6)


@icon("menu")
def _menu(d):
    d.poly([(4, 6), (12, 6), (8, 10.5)], fill="fg")          # 面板選單 ▾


@icon("layout")
def _layout(d):
    d.rect(1.5, 2.5, 14.5, 13.5, fill=None, outline="fg", w=1.2, r=0.8)
    d.line([(5.5, 2.5), (5.5, 13.5)], "fg", 1.1)
    d.line([(10.5, 2.5), (10.5, 13.5)], "fg", 1.1)
    d.line([(10.5, 8), (14.5, 8)], "fg", 1.1)


@icon("maximize")
def _maximize(d):
    d.rect(2.5, 2.5, 13.5, 13.5, fill=None, outline="fg", w=1.3, r=0.6)
    d.line([(2.5, 5.2), (13.5, 5.2)], "fg", 1.6)


@icon("restore")
def _restore(d):
    d.rect(2, 5, 10.5, 13.5, fill="fill", outline="fg", w=1.2, r=0.5)
    d.line([(5.5, 5), (5.5, 2.5), (14, 2.5), (14, 11), (10.5, 11)], "fg", 1.2)


@icon("add")
def _add(d):
    d.line([(8, 2.5), (8, 13.5)], "fg", 1.6)
    d.line([(2.5, 8), (13.5, 8)], "fg", 1.6)


@icon("add_all")
def _add_all(d):
    d.line([(6, 2.5), (6, 9.5)], "fg", 1.5)
    d.line([(2.5, 6), (9.5, 6)], "fg", 1.5)
    d.line([(11, 8), (11, 14)], "accent", 1.5)
    d.line([(8, 11), (14, 11)], "accent", 1.5)


@icon("help")
def _help(d):
    d.ellipse(1.5, 1.5, 14.5, 14.5, fill="accent", outline=None)
    d.arc(5, 3.5, 11, 9.5, 190, 60, "white", 1.6)
    d.line([(8, 8.6), (8, 10.6)], "white", 1.6)
    d.ellipse(7, 11.8, 9, 13.8, fill="white", outline=None)


@icon("info")
def _info(d):
    d.ellipse(1.5, 1.5, 14.5, 14.5, fill=None, outline="fg", w=1.2)
    d.line([(8, 7), (8, 12)], "fg", 1.6)
    d.ellipse(7, 3.8, 9, 5.8, fill="fg", outline=None)


@icon("theme")
def _theme(d):
    d.ellipse(2, 2, 14, 14, fill=None, outline="fg", w=1.2)
    d.d.pieslice([d.p(2, 2), d.p(14, 14)], 90, 270, fill=d.c("fg"))


@icon("text")
def _text(d):
    d.line([(3, 3.5), (13, 3.5)], "fg", 1.5)
    d.line([(8, 3.5), (8, 13.5)], "fg", 1.5)
    d.line([(5.5, 13.5), (10.5, 13.5)], "fg", 1.2)


@icon("xline")
def _xline(d):
    d.line([(2, 13.5), (14, 13.5)], "fg", 1.0)
    d.line([(2, 2), (2, 13.5)], "fg", 1.0)
    d.wave(2.5, 14, 8, 2.5, 1.0, "fg2", 1.0)
    d.line([(9, 2), (9, 13.5)], "accent", 1.4)


@icon("yline")
def _yline(d):
    d.line([(2, 13.5), (14, 13.5)], "fg", 1.0)
    d.line([(2, 2), (2, 13.5)], "fg", 1.0)
    d.wave(2.5, 14, 8, 2.5, 1.0, "fg2", 1.0)
    d.line([(2, 6), (14, 6)], "accent", 1.4)


@icon("style")
def _style(d):
    d.line([(2, 13.5), (14, 13.5)], "fg", 1.0)
    d.line([(2, 2), (2, 13.5)], "fg", 1.0)
    d.wave(2.5, 14, 8, 3, 1.0, "accent", 1.6)


@icon("wheel")
def _wheel(d):
    d.rect(5, 1.5, 11, 14.5, fill="fill", outline="fg", w=1.2, r=3)
    d.line([(8, 4), (8, 7)], "accent", 1.4)


@icon("range")
def _range(d):
    d.line([(2, 8), (14, 8)], "fg", 1.2)
    d.line([(2, 4.5), (2, 11.5)], "fg", 1.4)
    d.line([(14, 4.5), (14, 11.5)], "fg", 1.4)
    d.poly([(5, 8), (7.5, 5.5), (7.5, 10.5)], fill="accent")
    d.poly([(11, 8), (8.5, 5.5), (8.5, 10.5)], fill="accent")


@icon("panner")
def _panner(d):
    """平移器：整段訊號的小圖＋縮放窗（MATLAB Signal Analyzer 的 Panner）。"""
    d.rect(1.5, 4.5, 14.5, 11.5, fill="fill", outline="fg", w=1.0, r=0.4)
    d.wave(2.5, 13.5, 8, 2.0, 2.5, "fg2", 1.0)
    d.rect(6, 3, 10.5, 13, fill=None, outline="accent", w=1.6, r=0.3)


@icon("roi")
def _roi(d):
    """擷取訊號：框起一段、往下拉出來（MATLAB Extract Signals）。"""
    d.wave(1.5, 14.5, 5.5, 2.5, 1.5, "fg2", 1.0)
    d.rect(5, 1.5, 10.5, 9.5, fill=None, outline="accent", w=1.4, r=0.3)
    d.arrow(7.75, 9.5, 7.75, 14.6, "accent", 1.4, head=2.2)


@icon("spectrogram")
def _spectrogram(d):
    """頻譜圖：時間 × 頻率的色塊（MATLAB Spectrum Analyzer 的 Spectrogram 檢視）。"""
    d.rect(1.5, 1.5, 14.5, 14.5, fill="fill", outline="fg", w=1.0, r=0.4)
    for i, row in enumerate(((0, 1, 2, 1), (0, 2, 3, 1), (1, 3, 2, 0), (0, 1, 3, 2))):
        for j, c in enumerate(row):
            d.rect(3 + j * 2.6, 3 + i * 2.6, 5.3 + j * 2.6, 5.3 + i * 2.6, fill=("fg2", "accent", "orange", "red")[c], outline=None)


@icon("colorbar")
def _colorbar(d):
    """色彩列：直條漸層＋刻度（MATLAB 的 Colorbar 按鈕）。"""
    for i, c in enumerate(("red", "orange", "green", "accent", "fg2")):
        d.rect(4, 1.5 + i * 2.6, 9, 4.1 + i * 2.6, fill=c, outline=None)
    d.rect(4, 1.5, 9, 14.5, fill=None, outline="fg", w=0.9)
    for y in (3, 8, 13):
        d.line([(9.5, y), (12, y)], "fg", 1.0)


@icon("peak_freq")
def _peak_freq(d):
    """頻譜峰值搜尋：頻譜線＋最高點上的 ▼（MATLAB 的 Peak Finder）。"""
    d.line([(1.5, 14), (4, 12.5), (6, 13), (8, 6), (10, 12.5), (12, 11), (14.5, 13)], "accent", 1.2)
    d.poly([(6.3, 1.8), (9.7, 1.8), (8, 4.6)], fill="orange")


@icon("chmeas")
def _chmeas(d):
    """通道量測：頻譜上一個通道的色塊＋佔用頻寬兩個邊緣（MATLAB Spectrum Analyzer 的 Channel Measurements）。"""
    d.rect(4.5, 2, 11.5, 14, fill="fill", outline=None)
    d.line([(1.5, 13.5), (3.5, 13), (5.5, 7), (8, 4.5), (10.5, 7), (12.5, 13), (14.5, 13.5)], "accent", 1.2)
    d.line([(5.6, 2), (5.6, 14)], "orange", 1.0)
    d.line([(10.4, 2), (10.4, 14)], "orange", 1.0)


@icon("distortion")
def _distortion(d):
    """失真：基頻和一串遞減的諧波，諧波上面有 ▼（MATLAB Spectrum Analyzer 的 Distortion）。"""
    d.line([(1.5, 14), (14.5, 14)], "fg", 1.0)
    for x, h in ((3, 11), (6.5, 6.5), (10, 4.5), (13.5, 3)):
        d.line([(x, 14), (x, 14 - h)], "accent", 1.5)
    for x, h in ((6.5, 6.5), (10, 4.5), (13.5, 3)):
        y = 14 - h - 0.5
        d.poly([(x - 1.4, y - 2.4), (x + 1.4, y - 2.4), (x, y)], fill="orange")


@icon("mask_upper")
def _mask_upper(d):
    """上遮罩：頻譜線上方的遮罩區（MATLAB Spectrum Analyzer 的 Show upper mask）。"""
    d.poly([(1.5, 1.5), (14.5, 1.5), (14.5, 7), (10.5, 7), (10.5, 3.5), (5.5, 3.5), (5.5, 7), (1.5, 7)], fill="green")
    d.line([(1.5, 13), (4, 12.5), (6, 11), (8, 5.5), (10, 11), (12, 12.5), (14.5, 13)], "accent", 1.2)


@icon("mask_lower")
def _mask_lower(d):
    """下遮罩：頻譜線下方的遮罩區（MATLAB Spectrum Analyzer 的 Show lower mask）。"""
    d.poly([(1.5, 14.5), (14.5, 14.5), (14.5, 12), (10.5, 12), (10.5, 9), (5.5, 9), (5.5, 12), (1.5, 12)], fill="green")
    d.line([(1.5, 10), (4, 9.5), (6, 8), (8, 2.5), (10, 8), (12, 9.5), (14.5, 10)], "accent", 1.2)


@icon("stack")
def _stack(d):
    d.square(1.5, 14.5, 5.5, 2.5, "accent", 1.1, 4)
    d.square(1.5, 14.5, 9.5, 6.5, "orange", 1.1, 4)
    d.square(1.5, 14.5, 13.5, 10.5, "green", 1.1, 4)


@icon("measure")
def _measure(d):
    d.rect(1.5, 1.5, 14.5, 14.5, fill="fill", outline="fg", w=1.0, r=0.4)
    d.square(3.5, 12.5, 7, 3.5, "accent", 1.1, 3)
    d.line([(3.5, 10), (12.5, 10)], "fg2", 1.0)
    d.line([(3.5, 12.5), (10, 12.5)], "fg2", 1.0)


@icon("trans_next")
def _trans_next(d):
    d.line([(1.5, 13), (9, 13), (9, 3), (14.5, 3)], "accent", 1.2)
    d.line([(9, 1.5), (9, 14.5)], "orange", 0.8)
    d.poly([(2.5, 5.5), (2.5, 10.5), (6.5, 8)], fill="fg")


@icon("trans_prev")
def _trans_prev(d):
    d.line([(1.5, 3), (7, 3), (7, 13), (14.5, 13)], "accent", 1.2)
    d.line([(7, 1.5), (7, 14.5)], "orange", 0.8)
    d.poly([(13.5, 5.5), (13.5, 10.5), (9.5, 8)], fill="fg")


@icon("normalize")
def _normalize(d):
    d.line([(1.5, 2.5), (14.5, 2.5)], "fg2", 0.8)
    d.line([(1.5, 13.5), (14.5, 13.5)], "fg2", 0.8)
    d.wave(1.5, 14.5, 8, 5.5, 1.5, "accent", 1.2)
    d.wave(1.5, 14.5, 8, 5.5, 1.0, "orange", 1.0)


@icon("constellation")
def _constellation(d):
    d.line([(8, 1.5), (8, 14.5)], "fg2", 0.8)
    d.line([(1.5, 8), (14.5, 8)], "fg2", 0.8)
    for cx, cy in ((4.5, 4.5), (11.5, 4.5), (4.5, 11.5), (11.5, 11.5)):
        for dx, dy in ((-0.9, 0.3), (0.6, -0.7), (0.2, 0.9)):
            d.ellipse(cx + dx - 0.75, cy + dy - 0.75, cx + dx + 0.75, cy + dy + 0.75, fill="accent", outline=None)


@icon("eye")
def _eye(d):
    """眼圖：上下兩條平的軌跡（1→1、0→0），兩條轉態軌跡（0→1→0、1→0→1）在兩邊交叉、中間張開成眼睛。"""
    d.line([(1.5, 3), (14.5, 3)], "fg2", 0.8)
    d.line([(1.5, 13), (14.5, 13)], "fg2", 0.8)
    for s in (-1.0, 1.0):
        pts = []
        for i in range(41):
            x = 1.5 + 13.0 * i / 40
            pts.append((x, 8 - s * 5.0 * math.sin(math.pi * (x - 3.5) / 9.0)))
        d.line(pts, "accent", 1.2)


@icon("errrate")
def _errrate(d):
    """錯誤率比對：上一列 TX、下一列 RX 的位元格（1＝填色），RX 有一格和 TX 不同（紅底紅框）。"""
    tx = (1, 0, 1, 1)
    rx = (1, 0, 0, 1)
    for i, (a, b) in enumerate(zip(tx, rx)):
        x0 = 1.2 + i * 3.5
        d.rect(x0, 2.5, x0 + 2.7, 6.5, fill="accent" if a else None, outline="fg2", w=0.8)
        bad = a != b
        d.rect(x0, 9.5, x0 + 2.7, 13.5, fill="red" if bad else ("orange" if b else None), outline="red" if bad else "fg2",
               w=1.1 if bad else 0.8)


@icon("fm")
def _fm(d):
    pts = []
    for i in range(49):
        t = i / 48
        pts.append((1.5 + 13 * t, 8 - 4.5 * math.sin(2 * math.pi * (1.0 * t + 2.5 * t * t))))   # 頻率隨時間上升（chirp）
    d.line(pts, "accent", 1.2)
    d.line([(1.5, 14.5), (14.5, 14.5)], "fg2", 0.8)


@icon("iq_magphase")
def _iq_magphase(d):
    d.line([(1.5, 3.5), (5, 3.5), (5, 2), (8.5, 2), (8.5, 3.5), (14.5, 3.5)], "accent", 1.1)
    d.wave(1.5, 14.5, 8.5, 2.0, 1.0, "orange", 1.1)
    d.line([(1.5, 14.5), (14.5, 10.5)], "green", 1.1)


@icon("plot_type")
def _plot_type(d):
    d.line([(1.5, 5), (4, 2.5), (6.5, 5)], "accent", 1.2)
    d.line([(8.5, 5.5), (11, 5.5), (11, 2.5), (14.5, 2.5)], "orange", 1.2)
    d.line([(1.5, 14), (14.5, 14)], "fg2", 0.8)
    for x, h in ((3, 4), (6.5, 6.5), (10, 3), (13.5, 5)):
        d.line([(x, 14), (x, 14 - h)], "green", 1.1)
        d.ellipse(x - 1, 14 - h - 1, x + 1, 14 - h + 1, fill=None, outline="green", w=0.9)


@icon("diag")
def _diag(d):
    d.rect(2, 3, 14, 13, fill="fill", outline="fg", w=1.0, r=0.4)
    d.line([(4, 10.5), (6, 7), (8, 9.5), (10, 5.5), (12, 8.5)], "green", 1.3)


@icon("axis_right")
def _axis_right(d):
    d.line([(2, 2), (2, 13.5), (14, 13.5), (14, 2)], "fg", 1.0)
    d.wave(2.5, 13.5, 8, 3, 1.0, "accent", 1.2)
    d.line([(12, 4), (14, 2), (16, 4)], "orange", 1.2)


@icon("visible")
def _visible(d):
    d.arc(1, 2.5, 15, 13.5, 200, 340, "fg", 1.2)
    d.arc(1, 2.5, 15, 13.5, 20, 160, "fg", 1.2)
    d.ellipse(5.5, 5.5, 10.5, 10.5, fill="fill", outline="fg", w=1.2)
    d.ellipse(7, 7, 9, 9, fill="accent", outline=None)


@icon("blank")
def _blank(d):
    pass


@icon("expand_all")
def _expand_all(d):
    d.line([(3, 3), (8, 7.5), (13, 3)], "fg", 1.5)
    d.line([(3, 9), (8, 13.5), (13, 9)], "fg", 1.5)


@icon("collapse_all")
def _collapse_all(d):
    d.line([(4, 2.5), (8.5, 6.5), (4, 10.5)], "fg", 1.5)
    d.line([(8, 5.5), (12.5, 9.5), (8, 13.5)], "fg", 1.5)


@icon("up_folder")
def _up_folder(d):
    d.poly([(1.5, 5), (6, 5), (7.5, 6.5), (14.5, 6.5), (14.5, 14), (1.5, 14)], fill="fill", outline="fg")
    d.arrow(11, 12.5, 11, 8, "accent", 1.4, 2.2)


@icon("prefs")
def _prefs(d):
    import math as _m
    for i in range(8):
        a = i * _m.pi / 4
        d.line([(8 + 4.2 * _m.cos(a), 8 + 4.2 * _m.sin(a)), (8 + 6.8 * _m.cos(a), 8 + 6.8 * _m.sin(a))], "fg", 2.2)
    d.ellipse(3, 3, 13, 13, fill="fill", outline="fg", w=1.3)
    d.ellipse(6, 6, 10, 10, fill="white", outline="fg", w=1.0)


@icon("language")
def _language(d):
    d.ellipse(1.5, 1.5, 14.5, 14.5, fill=None, outline="fg", w=1.2)
    d.line([(1.5, 8), (14.5, 8)], "fg", 1.0)
    d.arc(4.5, 1.5, 11.5, 14.5, 0, 360, "fg", 1.0)
    d.line([(8, 1.5), (8, 14.5)], "fg2", 0.9)


# --- 前處理（MATLAB Signal Analyzer PREPROCESS 圖庫：濾波器的頻率響應、平滑、去趨勢、重取樣、包絡）--------------------
def _resp_axes(d):
    d.line([(1.5, 2), (1.5, 14), (14.5, 14)], "fg2", 0.8)


def _resp(d, gain):
    """畫 |H(f)|：gain(t) 是 0..1 頻率位置 t 的增益（1＝通帶在上）。"""
    pts = [(2 + 12 * i / 40, 13.5 - 9.5 * gain(i / 40)) for i in range(41)]
    d.line(pts, "accent", 1.4)


def _step(t, a, b):
    """a→b 之間平滑地從 0 升到 1（過渡帶）。"""
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    u = (t - a) / (b - a)
    return u * u * (3 - 2 * u)


@icon("pp_lowpass")
def _pp_lowpass(d):
    _resp_axes(d)
    _resp(d, lambda t: 1.0 - _step(t, 0.4, 0.6))


@icon("pp_highpass")
def _pp_highpass(d):
    _resp_axes(d)
    _resp(d, lambda t: _step(t, 0.4, 0.6))


@icon("pp_bandpass")
def _pp_bandpass(d):
    _resp_axes(d)
    _resp(d, lambda t: _step(t, 0.2, 0.38) * (1.0 - _step(t, 0.62, 0.8)))


@icon("pp_bandstop")
def _pp_bandstop(d):
    _resp_axes(d)
    _resp(d, lambda t: 1.0 - _step(t, 0.25, 0.42) * (1.0 - _step(t, 0.58, 0.75)))


@icon("pp_smooth")
def _pp_smooth(d):
    pts = [(1.5 + 13 * i / 26, 8 - 3.5 * math.sin(2 * math.pi * i / 26) + (1.6 if i % 2 else -1.6)) for i in range(27)]
    d.line(pts, "fg2", 0.8)
    d.wave(1.5, 14.5, 8, 3.5, 1.0, "accent", 1.4)


@icon("pp_detrend")
def _pp_detrend(d):
    pts = [(1.5 + 13 * i / 40, 12.5 - 7 * i / 40 - 1.8 * math.sin(2 * math.pi * 2 * i / 40)) for i in range(41)]
    d.line(pts, "fg2", 0.9)
    d.line([(1.5, 12.5), (14.5, 5.5)], "orange", 0.9)
    d.wave(1.5, 14.5, 9, 1.8, 2.0, "accent", 1.3)


@icon("pp_resample")
def _pp_resample(d):
    d.wave(1.5, 14.5, 8, 4.5, 1.0, "fg2", 0.8)
    for i in range(7):
        x = 2 + 12 * i / 6
        y = 8 - 4.5 * math.sin(2 * math.pi * (x - 1.5) / 13)
        d.ellipse(x - 1.1, y - 1.1, x + 1.1, y + 1.1, fill="accent", outline=None)


@icon("pp_envelope")
def _pp_envelope(d):
    pts = []
    for i in range(61):
        t = i / 60
        a = 1.5 + 4.5 * math.sin(math.pi * t)
        pts.append((1.5 + 13 * t, 8 - a * math.sin(2 * math.pi * 5 * t)))
    d.line(pts, "fg2", 0.8)
    d.line([(1.5 + 13 * i / 30, 8 - 1.5 - 4.5 * math.sin(math.pi * i / 30)) for i in range(31)], "accent", 1.3)
    d.line([(1.5 + 13 * i / 30, 8 + 1.5 + 4.5 * math.sin(math.pi * i / 30)) for i in range(31)], "orange", 1.3)


_CACHE: Dict[Tuple[str, int, Tuple[Tuple[str, str], ...], str], object] = {}


def names():
    return sorted(_ICONS)


def render(name: str, size: int = 16, palette: Optional[Palette] = None):
    """回 PIL.Image（RGBA）。找不到名稱回 None。"""
    if not HAVE_PIL or name not in _ICONS:
        return None
    pal = dict(DEFAULT_PALETTE)
    if palette:
        pal.update(palette)
    d = _D(size, pal)
    _ICONS[name](d)
    return d.im.resize((size, size), Image.LANCZOS)


def get_icon(name: str, size: int = 16, palette: Optional[Palette] = None, master=None):
    """回 tk 可用的 PhotoImage（會快取，同一個 Tk 行程內重複使用）；沒有 Pillow 或沒有這個圖示回 None。"""
    if not HAVE_PIL:
        return None
    pal = tuple(sorted((palette or {}).items()))
    key = (name, int(size), pal, str(master) if master is not None else "")
    img = _CACHE.get(key)
    if img is not None:
        return img
    im = render(name, size, palette)
    if im is None:
        return None
    try:
        img = ImageTk.PhotoImage(im, master=master)
    except Exception:
        return None
    _CACHE[key] = img
    return img


def clear_cache() -> None:
    _CACHE.clear()


def png_bytes(name: str, size: int = 16, palette: Optional[Palette] = None) -> bytes:
    import io
    im = render(name, size, palette)
    if im is None:
        return b""
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()
