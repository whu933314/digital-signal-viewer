# -*- coding: utf-8 -*-
"""plotkit.selftest_e — 批次 E 的 Agg 檢查（由 plotkit.selftest 呼叫）：匯出（格式、DPI、背景、尺寸、只匯出一個座標區）、
復原／重做的動作名稱、方向限制（滾輪、拖曳、方向鍵、＋／−）、縮小鈕、圖字級。"""
from __future__ import annotations

import io
import math
import os
import tempfile

import numpy as np
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def _motion_event(canvas, x, y) -> MouseEvent:
    """左鍵按著的 motion_notify_event。MouseEvent 的 buttons 參數 matplotlib 3.10 才有（3.8／3.9 沒有），舊版就事後補上屬性。"""
    try:
        return MouseEvent("motion_notify_event", canvas, x, y, button=1, buttons=[1])
    except TypeError:
        ev = MouseEvent("motion_notify_event", canvas, x, y, button=1)
        ev.buttons = frozenset([1])
        return ev


def run(check) -> None:
    from . import export as E
    from . import styles, undo
    from .interact import Interactor, InteractorModel, nav_dims_allow
    from .model import FigureState, Series
    from .selftest import _NavStub, _RecHost

    def close(a, b, tol=1e-9):
        return a is not None and math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)

    # --- 匯出：純函式 -------------------------------------------------------------------------------
    fmts = [e for e, _d in E.export_formats()]
    check(fmts[:6] == ["png", "jpg", "tif", "pdf", "eps", "svg"] and not {"pgf", "raw", "rgba", "jpeg", "tiff"} & set(fmts),
          f"export_formats：常用的在前（PNG／JPEG／TIFF／PDF／EPS／SVG）、別名與 PGF／raw 不列（{fmts}）")
    check(E.is_vector("pdf") and E.is_vector(".SVG") and E.is_vector("eps") and not E.is_vector("png") and not E.is_vector("jpg"),
          "is_vector：PDF／SVG／EPS 是向量（Content type 自動）")
    check(E.size_to_inches(2.54, 5.08, "cm", 150) == (1.0, 2.0) and E.size_to_inches(300, 150, "px", 150) == (2.0, 1.0)
          and E.inches_to_size(1.0, 2.0, "pt", 100) == (72.0, 144.0) and E.pixel_size(6.0, 4.0, 150) == (900, 600),
          "尺寸換算：cm／px／pt ↔ 英吋，像素＝英吋 × DPI")
    fig = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(fig)
    fig.set_facecolor("#212121")
    check(E.background_kw("white", fig)["facecolor"] == "white" and E.background_kw("transparent", fig) == {"transparent": True}
          and E.background_kw("theme", fig)["facecolor"] == fig.get_facecolor(), "background_kw：主題色／白／透明")
    a1 = fig.add_subplot(2, 1, 1)
    a2 = fig.add_subplot(2, 1, 2, sharex=a1)
    a1r = a1.twinx()
    for a in (a1, a2, a1r):
        a.plot(np.arange(10.0), np.arange(10.0) ** 0.5)
    a1.set_title("P1")
    check(E.axes_group(fig, a1) == [a1, a1r] and E.axes_group(fig, a2) == [a2], "axes_group：座標區＋疊在同位置的右軸")
    out = tempfile.mkdtemp(prefix="pk_export_")
    try:
        from PIL import Image
    except Exception:            # pragma: no cover
        Image = None
    p_full = E.export_figure(fig, os.path.join(out, "full.png"), dpi=50)
    p_sz = E.export_figure(fig, os.path.join(out, "size.png"), dpi=100, size_in=(3.0, 2.0))
    sz_back = tuple(fig.get_size_inches())
    p_ax = E.export_figure(fig, os.path.join(out, "ax.png"), dpi=50, axes=[a2])
    vis = [a.get_visible() for a in fig.axes]
    if Image is not None:
        w_full, h_full = Image.open(p_full).size
        w_sz, h_sz = Image.open(p_sz).size
        w_ax, h_ax = Image.open(p_ax).size
        check((w_full, h_full) == (300, 200) and (w_sz, h_sz) == (300, 200) and sz_back == (6.0, 4.0),
              f"export_figure：DPI 決定像素（6×4 in × 50 = 300×200）、寬高 3×2 in × 100 dpi、存完圖的大小還原（{(w_sz, h_sz)} {sz_back}）")
        check(h_ax < h_full * 0.7 and w_ax <= w_full + 2 and all(vis),
              f"export_figure axes=：只存那個座標區（tight bbox，高 {h_ax} < 全圖 {h_full}）、其他座標區存完恢復顯示")
        p_tr = E.export_figure(fig, os.path.join(out, "tr.png"), dpi=30, background="transparent")
        p_wh = E.export_figure(fig, os.path.join(out, "wh.png"), dpi=30, background="white")
        p_th = E.export_figure(fig, os.path.join(out, "th.png"), dpi=30, background="theme")
        c_tr = Image.open(p_tr).convert("RGBA").getpixel((0, 0))
        c_wh = Image.open(p_wh).convert("RGBA").getpixel((0, 0))
        c_th = Image.open(p_th).convert("RGBA").getpixel((0, 0))
        check(c_tr[3] == 0 and c_wh[:3] == (255, 255, 255) and c_th[:3] == (0x21, 0x21, 0x21),
              f"export_figure 背景：透明（alpha 0）／白／主題色（{c_tr} {c_wh} {c_th}）")
        p_jpg = E.export_figure(fig, os.path.join(out, "a.jpg"), dpi=30, background="transparent")
        check(Image.open(p_jpg).format == "JPEG", "JPEG 選透明也存得出來（沒有 alpha 的格式）")
    for fmt, magic in (("pdf", b"%PDF"), ("svg", b"<?xml"), ("eps", b"%!PS")):
        buf = io.BytesIO()
        E.export_figure(fig, buf, fmt=fmt, dpi=150, axes=[a1])
        check(buf.getvalue()[:5].startswith(magic), f"export_figure：{fmt.upper()}（向量）只存一個座標區也存得出來")
    check(E.ext_of("/a/b.PNG") == "png" and E.ext_of("x") == "", "ext_of")

    # --- 復原／重做的動作名稱 ------------------------------------------------------------------------
    us = undo.UndoStack()
    check(undo.undo_label(us) == "復原" and undo.redo_label(us) == "重做", "沒有可復原的動作：只寫「復原」「重做」")
    us.push({"a": 1}, "線色 #ff0000")
    check(undo.undo_label(us) == "復原：線色 #ff0000" and undo.redo_label(us) == "重做", "undo_label：「復原：<動作>」")
    us.undo({"a": 2})
    check(undo.undo_label(us) == "復原" and undo.redo_label(us) == "重做：線色 #ff0000", "redo_label：復原之後「重做：<動作>」")

    class _W:
        def __init__(self):
            self.st = None
            self._tooltip = type("T", (), {"text": ""})()

        def state(self, s):
            self.st = s
    wu, wr = _W(), _W()
    undo.sync_undo_ui(us, [wu], [wr], ("Ctrl+Z", "Ctrl+Y"))
    check(wu.st == ["disabled"] and wr.st == ["!disabled"] and wu._pk_tip == "復原 (Ctrl+Z)"
          and wr._tooltip.text == "重做：線色 #ff0000 (Ctrl+Y)", f"sync_undo_ui：停用狀態與提示文字（{wu._pk_tip} / {wr._pk_tip}）")

    # --- 方向限制與縮小鈕 ----------------------------------------------------------------------------
    check(nav_dims_allow("both", "y") == "y" and nav_dims_allow("x", "both") == "x" and nav_dims_allow("x", "y") == ""
          and nav_dims_allow("y", "y") == "y", "nav_dims_allow：方向限制和動作的軸取交集")
    st = FigureState()
    st.add_series(Series("sa", np.arange(100.0), np.sin(np.arange(100.0) / 10) * 10))
    fig2 = Figure(figsize=(8, 5), dpi=100)
    FigureCanvasAgg(fig2)
    host = _RecHost(st, fig2)
    tb = _NavStub()
    tb.zoom_constraint = None
    ia = Interactor(fig2.canvas, host, toolbar=tb, model=InteractorModel(st.tips, st.annotations))
    fig2.canvas.draw()
    ax = host.info.ax_left
    cx, cy = ax.transData.transform((50.0, 0.0))
    statuses = []
    host.status = statuses.append
    dims_seen = []
    host.on_nav_dims = dims_seen.append
    check(ia.set_nav_dims("x") == "x" and tb.zoom_constraint == "x" and ia.nav_dims() == "x" and dims_seen == ["x"]
          and "只水平" in statuses[-1], "set_nav_dims：寫進工具列的 zoom_constraint、通知 host、狀態列說明")
    y0, x0 = ax.get_ylim(), ax.get_xlim()
    ia.on_scroll(MouseEvent("scroll_event", fig2.canvas, cx, cy, step=1))
    x1 = ax.get_xlim()
    check(ax.get_ylim() == y0 and close((x0[1] - x0[0]) / (x1[1] - x1[0]), 1.1), "只水平：滾輪只縮 x（MATLAB LimitsDimensions 也管滾輪）")
    ia.on_scroll(MouseEvent("scroll_event", fig2.canvas, cx, cy, step=1, modifiers={"ctrl", "shift"}))
    check(ax.get_xlim() == x1 and ax.get_ylim() == y0, "只水平：Ctrl＋Shift＋滾輪（只縮 y）→ 不動")
    ia.on_press(MouseEvent("button_press_event", fig2.canvas, cx, cy + 30, button=1))
    ia.on_motion(_motion_event(fig2.canvas, cx + 40, cy + 70))
    ia.on_release(MouseEvent("button_release_event", fig2.canvas, cx + 40, cy + 70, button=1))
    x2 = ax.get_xlim()
    check(ax.get_ylim() == y0 and x2 != x1, f"只水平：斜著拖曳平移只動 x（{x1} → {x2}）")
    ia.on_key(KeyEvent("key_press_event", fig2.canvas, "up", cx, cy))
    check(ax.get_ylim() == y0 and ax.get_xlim() == x2, "只水平：↑ 鍵平移（只動 y）→ 不動")
    ia.on_key(KeyEvent("key_press_event", fig2.canvas, "+", cx, cy))
    x3 = ax.get_xlim()
    check(ax.get_ylim() == y0 and close((x2[1] - x2[0]) / (x3[1] - x3[0]), 1.1), "只水平：＋ 鍵放大 1.1 只縮 x（MATLAB 的 zoom 快速鍵）")
    ax.set_xlim(30, 50)
    ia.zoom_out()
    x4 = ax.get_xlim()
    check(ax.get_ylim() == y0 and close(x4[0], 25, 1e-6) and close(x4[1], 55, 1e-6), f"縮小鈕：以中心縮小 1.5 倍、方向限制照樣管（{x4}）")
    ia.set_nav_dims("both", notify=False)
    ia.restore_view()
    xh, yh = ax.get_xlim(), ax.get_ylim()
    ia.zoom_out()
    check(close(ax.get_xlim()[0], xh[0]) and close(ax.get_xlim()[1], xh[1]) and close(ax.get_ylim()[0], yh[0]),
          "縮小鈕：已在自動範圍 → 不再縮（和 MATLAB 一樣）")
    # 兩個 sharex 座標區：x 只縮一次、y 各自以自己的中心
    fig3 = Figure(figsize=(6, 6), dpi=100)
    FigureCanvasAgg(fig3)
    b1 = fig3.add_subplot(2, 1, 1)
    b2 = fig3.add_subplot(2, 1, 2, sharex=b1)
    b1.plot(np.arange(100.0), np.arange(100.0))
    b2.plot(np.arange(100.0), -np.arange(100.0))
    tb3 = _NavStub()
    tb3.zoom_constraint = None
    from .interact import InteractorHost
    ia3 = Interactor(fig3.canvas, InteractorHost(), toolbar=tb3)
    fig3.canvas.draw()
    b1.set_xlim(40, 60); b1.set_ylim(40, 60); b2.set_ylim(-60, -40)
    ia3.zoom_out()
    check(close(b1.get_xlim()[0], 35) and close(b1.get_xlim()[1], 65) and close(b1.get_ylim()[0], 35)
          and close(b2.get_ylim()[0], -65) and close(b2.get_ylim()[1], -35),
          f"縮小鈕：sharex 的 x 只縮一次（20→30）、每個座標區的 y 以自己的中心縮（{b1.get_xlim()} {b2.get_ylim()}）")

    # --- 圖字級 -------------------------------------------------------------------------------------
    base = styles.get_style("matlab")
    styles.set_plot_fontsize(14)
    big = styles.get_style("matlab")
    styles.set_plot_fontsize(None)
    back = styles.get_style("matlab")
    check(big["fontsize"] == 14 and close(big["legend"]["fontsize"], base["legend"]["fontsize"] * 1.4)
          and close(big["tip"]["fontsize"], 14) and back["fontsize"] == base["fontsize"] == 10.0,
          "set_plot_fontsize：基本字級與圖例／提示／標註按比例；None＝風格預設 10 pt")
    styles.set_plot_fontsize(99)
    check(styles.plot_fontsize() == styles.PLOT_FONT_PT_RANGE[1], "set_plot_fontsize：超出範圍夾到 20 pt")
    styles.set_plot_fontsize(None)
