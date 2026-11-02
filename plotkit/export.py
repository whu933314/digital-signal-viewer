# -*- coding: utf-8 -*-
"""plotkit.export — 「存成圖檔…」的匯出對話框（照 MATLAB 圖形視窗 Export To…／exportgraphics 的選項）。

- 格式：canvas.get_supported_filetypes() 列得出來的（PNG、JPEG、TIFF、PDF、EPS、SVG…；需要 LaTeX 的 PGF、raw 不列）
- 解析度 (DPI)：預設 150（＝複製圖到剪貼簿、MATLAB copygraphics／exportgraphics 的 Resolution 預設）
- 背景：主題色（＝畫面上的圖底色）／白色／透明（MATLAB BackgroundColor 'current'／'white'／'none'）
- 內容類型：PDF／EPS／PS／SVG 自動是向量（MATLAB ContentType 'vector'），其他是影像
- 寬度／高度＋單位（in／cm／mm／pt／px）：暫時改 figure 大小再存，存完還原（畫面不動）
- 只匯出一個座標區（panel 右鍵「只匯出這個 panel…」）：其他座標區暫時隱藏，bbox＝這個座標區（含 twin 右軸）的 tight bbox

純函式（export_formats、is_vector、size_to_inches、inches_to_size、export_figure…）不需要 Tk，selftest 用 Agg 測。
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .i18n import tr
from . import dialogs as D

EXPORT_DPI_DEFAULT = 150
DPI_MIN, DPI_MAX = 36, 1200
# 背景：(鍵, 顯示文字)
BACKGROUNDS = (("theme", "主題色"), ("white", "白色"), ("transparent", "透明"))
SIZE_UNITS = ("in", "cm", "mm", "pt", "px")
_PER_INCH = {"in": 1.0, "cm": 2.54, "mm": 25.4, "pt": 72.0}
VECTOR_FORMATS = frozenset(("pdf", "eps", "ps", "svg", "svgz", "pgf"))
_PREFERRED = ("png", "jpg", "tif", "pdf", "eps", "svg", "ps", "svgz", "gif", "webp", "avif")
_EXCLUDE = frozenset(("pgf", "raw", "rgba", "jpeg", "tiff"))     # pgf 要 LaTeX；raw 不是圖檔；jpeg／tiff 是 jpg／tif 的別名
PANEL_PAD_IN = 0.1                    # 只匯出一個 panel 時 tight bbox 外加的留白（英吋）

# 上次用的選項（同一個程式裡各視窗共用；DSV 的偏好設定 → 匯出 會改 dpi／background）
DEFAULTS: Dict[str, Any] = {"format": "png", "dpi": EXPORT_DPI_DEFAULT, "background": "theme", "unit": "in"}


def export_formats(canvas=None) -> List[Tuple[str, str]]:
    """[(副檔名, 說明)]：常用的在前（PNG、JPEG、TIFF、PDF、EPS、SVG），別名與存不出來的格式不列。"""
    try:
        if canvas is None:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure
            canvas = FigureCanvasAgg(Figure())
        ft = dict(canvas.get_supported_filetypes())
    except Exception:
        ft = {"png": "Portable Network Graphics", "pdf": "Portable Document Format", "svg": "Scalable Vector Graphics"}
    alias = {"jpeg": "jpg", "tiff": "tif"}
    skip = {e for e in _EXCLUDE if alias.get(e) in ft or e not in alias}      # 別名只在正名不存在時才列
    exts = [e for e in _PREFERRED if e in ft] + sorted(e for e in ft if e not in _PREFERRED)
    return [(e, str(ft[e])) for e in exts if e not in skip]


def format_label(ext: str, desc: str) -> str:
    return tr("{ext}（{desc}）").format(ext=ext.upper(), desc=desc)


def is_vector(fmt: str) -> bool:
    return str(fmt).lower().lstrip(".") in VECTOR_FORMATS


def content_note(fmt: str) -> str:
    """MATLAB 的 Content type：向量格式自動是 vector。"""
    if is_vector(fmt):
        return tr("內容類型：向量（線條與文字可任意放大；DPI 只影響內嵌的點陣部分）")
    return tr("內容類型：影像（點陣；像素數＝寬度 × DPI）")


def size_to_inches(w: float, h: float, unit: str, dpi: float) -> Tuple[float, float]:
    """(寬, 高, 單位) → 英吋。px 用 dpi 換算。"""
    if unit == "px":
        return float(w) / float(dpi), float(h) / float(dpi)
    k = _PER_INCH.get(unit, 1.0)
    return float(w) / k, float(h) / k


def inches_to_size(wi: float, hi: float, unit: str, dpi: float) -> Tuple[float, float]:
    if unit == "px":
        return float(wi) * float(dpi), float(hi) * float(dpi)
    k = _PER_INCH.get(unit, 1.0)
    return float(wi) * k, float(hi) * k


RASTER_FORMATS = ("png", "jpg", "jpeg", "tif", "tiff", "webp", "gif", "bmp", "avif", "raw", "rgba")


def pixel_size(wi: float, hi: float, dpi: float) -> Tuple[int, int]:
    return int(round(float(wi) * float(dpi))), int(round(float(hi) * float(dpi)))


def fmt_size(v: float, unit: str) -> str:
    return f"{v:.0f}" if unit in ("px", "pt") else f"{v:.3g}" if v < 10 else f"{v:.4g}"


def background_kw(background: str, fig) -> Dict[str, Any]:
    """savefig 的背景參數：theme＝圖目前的底色、white＝白、transparent＝透明（座標區底色也透明，MATLAB 'none' 只清 figure 底）。"""
    if background == "white":
        return {"facecolor": "white", "transparent": False}
    if background == "transparent":
        return {"transparent": True}
    return {"facecolor": fig.get_facecolor(), "transparent": False}


def axes_group(fig, ax) -> list:
    """ax 和疊在同一位置的 twin 座標區（DSV 的右軸 P<n>R、plotkit 的右軸）。"""
    try:
        pos = ax.get_position().bounds
    except Exception:
        return [ax]
    out = [ax]
    for a in fig.axes:
        if a is ax:
            continue
        try:
            if all(abs(p - q) < 1e-9 for p, q in zip(a.get_position().bounds, pos)):
                out.append(a)
        except Exception:
            pass
    return out


def axes_bbox_inches(fig, axes: Sequence, pad: float = PANEL_PAD_IN):
    """座標區（含刻度、軸標籤、標題、圖例）的 tight bbox，英吋，外加 pad。"""
    from matplotlib.transforms import Bbox
    r = fig.canvas.get_renderer()
    boxes = []
    for a in axes:
        try:
            bb = a.get_tightbbox(r)
        except Exception:
            bb = None
        if bb is not None and bb.width > 0 and bb.height > 0:
            boxes.append(bb)
    if not boxes:
        boxes = [axes[0].bbox]
    return Bbox.union(boxes).transformed(fig.dpi_scale_trans.inverted()).padded(pad)


def ext_of(path: str) -> str:
    return os.path.splitext(str(path))[1].lower().lstrip(".")


def export_figure(fig, path: str, *, fmt: Optional[str] = None, dpi: float = EXPORT_DPI_DEFAULT, background: str = "theme",
                  size_in: Optional[Tuple[float, float]] = None, axes: Optional[Sequence] = None,
                  pad: float = PANEL_PAD_IN) -> str:
    """存圖。size_in＝(寬, 高) 英吋：暫時改 figure 大小（forward=False，不動視窗）；axes＝只匯出這些座標區（其他暫時隱藏）。
    匯出期間 fig._pk_exporting＝True：圖的版面引擎（例如 DSV 的 PanelLayout）據此用匯出的規則排（存檔前算裁切框的那次排版也一樣）。
    結束後一定還原大小與可見性，並排一次重畫。回傳 path。"""
    fmt = (fmt or ext_of(path) or "png").lower().lstrip(".")
    old_size = fig.get_size_inches().copy()
    hidden = []
    had_flag = getattr(fig, "_pk_exporting", None)
    try:
        fig._pk_exporting = True
        w_in, h_in = (float(size_in[0]), float(size_in[1])) if size_in else (float(old_size[0]), float(old_size[1]))
        if fmt in RASTER_FORMATS and not axes:
            # matplotlib 的點陣輸出把 寬×DPI 無條件捨去（239.9999 → 239）；對話框顯示的是四捨五入的像素數 → 讓兩者一致
            pw, ph = pixel_size(w_in, h_in, dpi)
            w_in, h_in = (pw + 1e-3) / float(dpi), (ph + 1e-3) / float(dpi)
        if size_in or (fmt in RASTER_FORMATS and not axes):
            fig.set_size_inches(w_in, h_in, forward=False)
        kw: Dict[str, Any] = dict(format=fmt, dpi=float(dpi), **background_kw(background, fig))
        if axes:
            group = []
            for a in axes:
                for g in axes_group(fig, a):
                    if g not in group:
                        group.append(g)
            for a in fig.axes:
                if a not in group and a.get_visible():
                    a.set_visible(False)
                    hidden.append(a)
            # 先藏好其他座標區、再照匯出的大小排版（savefig 畫圖時才會排）：版面引擎看得到這次只匯出哪幾張（DSV：匯出的那張一定標 x 軸），
            # 裁切框才對得上 savefig 畫出來的座標區
            eng = fig.get_layout_engine() if hasattr(fig, "get_layout_engine") else None
            if eng is not None:
                try:
                    eng.execute(fig)
                except Exception:
                    pass
            kw["bbox_inches"] = axes_bbox_inches(fig, group, pad)
        fig.savefig(path, **kw)
    finally:
        for a in hidden:
            a.set_visible(True)
        if size_in or (fmt in RASTER_FORMATS and not axes):
            fig.set_size_inches(old_size[0], old_size[1], forward=False)
        if had_flag is None:
            try:
                del fig._pk_exporting
            except AttributeError:
                pass
        else:
            fig._pk_exporting = had_flag
        try:
            fig.canvas.draw_idle()
        except Exception:
            pass
    return path


def ask_export_path(parent, title: str, initialfile: str, filetypes, ext: str, initialdir: Optional[str] = None) -> Optional[str]:
    """另存新檔對話框（測試可整個換掉）。取消回 None；沒打副檔名就補 ext。"""
    kw = dict(parent=parent, title=title, initialfile=initialfile, defaultextension="." + ext, filetypes=list(filetypes))
    if initialdir:
        kw["initialdir"] = initialdir
    try:
        p = D.filedialog.asksaveasfilename(**kw)
    except Exception:
        return None
    if not p:
        return None
    if not ext_of(p):
        p = p + "." + ext
    return p


class ExportDialog(D.tk.Toplevel if D.HAVE_TK else object):
    """「存成圖檔…」：格式、DPI、背景、內容類型、寬高與單位；按「匯出…」再選檔名。
    axes＝只匯出這些座標區（panel 右鍵）；before()＝存檔前呼叫（DSV 藏十字游標）；on_saved(path)＝存好之後（狀態列）。
    非 modal、不設 grab、不搶焦點。"""

    def __init__(self, parent, fig, *, axes: Optional[Sequence] = None, title: Optional[str] = None,
                 initialfile: str = "figure", initialdir: Optional[str] = None,
                 before: Optional[Callable[[], None]] = None, on_saved: Optional[Callable[[str], None]] = None,
                 status: Optional[Callable[[str], None]] = None):
        top = parent.winfo_toplevel() if parent is not None else None
        super().__init__(top)
        ttk, tk = D.ttk, D.tk
        self.fig = fig
        self.axes = list(axes) if axes else None
        self.before = before
        self.on_saved = on_saved
        self.status = status
        self.initialfile = os.path.splitext(initialfile)[0] or "figure"
        self.initialdir = initialdir
        self.saved_path: Optional[str] = None
        self.title(title or (tr("只匯出這個 panel") if self.axes else tr("存成圖檔")))
        self.resizable(False, False)
        try:
            from . import theme as _T
            th = _T.current()
            if th is not None:
                self.configure(background=th["bg"])
        except Exception:
            pass
        if top is not None:
            try:
                self.transient(top)
            except Exception:
                pass
        self.formats = export_formats(getattr(fig, "canvas", None))
        self._fmt_labels = [format_label(e, d) for e, d in self.formats]
        want = DEFAULTS.get("format", "png")
        idx = next((i for i, (e, _d) in enumerate(self.formats) if e == want), 0)
        self.v_format = tk.StringVar(master=self, value=self._fmt_labels[idx] if self._fmt_labels else "")
        self.v_dpi = tk.StringVar(master=self, value=str(int(DEFAULTS.get("dpi", EXPORT_DPI_DEFAULT))))
        bg_key = DEFAULTS.get("background", "theme")
        self._bg_labels = [tr(lbl) for _k, lbl in BACKGROUNDS]
        self.v_bg = tk.StringVar(master=self, value=next((tr(l) for k, l in BACKGROUNDS if k == bg_key), self._bg_labels[0]))
        self.v_unit = tk.StringVar(master=self, value=DEFAULTS.get("unit", "in") if DEFAULTS.get("unit") in SIZE_UNITS else "in")
        self._unit_prev = self.v_unit.get()
        wi, hi = (float(v) for v in fig.get_size_inches())
        self._size0 = (wi, hi)
        w, h = inches_to_size(wi, hi, self.v_unit.get(), self._dpi_or_default())
        self.v_w = tk.StringVar(master=self, value=fmt_size(w, self.v_unit.get()))
        self.v_h = tk.StringVar(master=self, value=fmt_size(h, self.v_unit.get()))
        self.v_content = tk.StringVar(master=self, value="")
        self.v_pixels = tk.StringVar(master=self, value="")
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        r = 0

        def label(text, row):
            ttk.Label(body, text=text).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
        label(tr("格式"), r)
        self.cb_format = ttk.Combobox(body, textvariable=self.v_format, values=self._fmt_labels, state="readonly", width=34)
        self.cb_format.grid(row=r, column=1, columnspan=3, sticky="we", pady=3)
        self.cb_format.bind("<<ComboboxSelected>>", lambda e: self._refresh())
        r += 1
        ttk.Label(body, textvariable=self.v_content, style="Hint.TLabel", wraplength=360, justify="left").grid(
            row=r, column=1, columnspan=3, sticky="w", pady=(0, 4))
        r += 1
        label(tr("解析度 (DPI)"), r)
        self.sp_dpi = ttk.Spinbox(body, textvariable=self.v_dpi, from_=DPI_MIN, to=DPI_MAX, increment=50, width=8,
                                  command=self._refresh)
        self.sp_dpi.grid(row=r, column=1, sticky="w", pady=3)
        self.sp_dpi.bind("<KeyRelease>", lambda e: self._refresh())
        r += 1
        label(tr("背景"), r)
        ttk.Combobox(body, textvariable=self.v_bg, values=self._bg_labels, state="readonly", width=12).grid(row=r, column=1, sticky="w", pady=3)
        r += 1
        label(tr("寬度"), r)
        self.e_w = ttk.Entry(body, textvariable=self.v_w, width=9)
        self.e_w.grid(row=r, column=1, sticky="w", pady=3)
        ttk.Label(body, text=tr("高度")).grid(row=r, column=2, sticky="e", padx=(8, 4))
        self.e_h = ttk.Entry(body, textvariable=self.v_h, width=9)
        self.e_h.grid(row=r, column=3, sticky="w", pady=3)
        r += 1
        label(tr("單位"), r)
        self.cb_unit = ttk.Combobox(body, textvariable=self.v_unit, values=SIZE_UNITS, state="readonly", width=6)
        self.cb_unit.grid(row=r, column=1, sticky="w", pady=3)
        self.cb_unit.bind("<<ComboboxSelected>>", lambda e: self._on_unit())
        self.btn_reset_size = ttk.Button(body, text=tr("目前大小"), command=self.reset_size)
        self.btn_reset_size.grid(row=r, column=2, columnspan=2, sticky="e", pady=3)
        for e in (self.e_w, self.e_h):
            e.bind("<KeyRelease>", lambda ev: self._refresh())
        r += 1
        ttk.Label(body, textvariable=self.v_pixels, style="Hint.TLabel", wraplength=360, justify="left").grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(6, 0))
        r += 1
        if self.axes:
            ttk.Label(body, text=tr("只匯出這個 panel（含刻度、標籤與圖例），其他 panel 不會出現；寬高是整張圖的大小。"),
                      style="Hint.TLabel", wraplength=360, justify="left").grid(row=r, column=0, columnspan=4, sticky="w", pady=(4, 0))
            r += 1
        bar = ttk.Frame(body)
        bar.grid(row=r, column=0, columnspan=4, sticky="we", pady=(12, 0))
        ttk.Button(bar, text=tr("取消"), command=self.destroy).pack(side="right")
        self.btn_export = ttk.Button(bar, text=tr("匯出…"), style="Primary.TButton", command=self.export)
        self.btn_export.pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda e: self.export())
        self.bind("<Escape>", lambda e: self.destroy())
        self._refresh()

    # --- 讀欄位 ---------------------------------------------------------------
    def fmt(self) -> str:
        lbl = self.v_format.get()
        for (e, _d), l in zip(self.formats, self._fmt_labels):
            if l == lbl:
                return e
        return self.formats[0][0] if self.formats else "png"

    def background(self) -> str:
        lbl = self.v_bg.get()
        return next((k for k, l in BACKGROUNDS if tr(l) == lbl), "theme")

    def _dpi_or_default(self) -> float:
        try:
            v = float(self.v_dpi.get())
        except Exception:
            return float(DEFAULTS.get("dpi", EXPORT_DPI_DEFAULT))
        return v if v > 0 else float(EXPORT_DPI_DEFAULT)

    def dpi(self) -> Optional[float]:
        try:
            v = float(self.v_dpi.get())
        except Exception:
            return None
        return v if DPI_MIN <= v <= DPI_MAX else None

    def size_in(self) -> Optional[Tuple[float, float]]:
        try:
            w, h = float(self.v_w.get()), float(self.v_h.get())
        except Exception:
            return None
        if w <= 0 or h <= 0:
            return None
        wi, hi = size_to_inches(w, h, self.v_unit.get(), self._dpi_or_default())
        if not (0.2 <= wi <= 200 and 0.2 <= hi <= 200):
            return None
        return wi, hi

    def options(self) -> Dict[str, Any]:
        return {"format": self.fmt(), "dpi": self.dpi(), "background": self.background(), "size_in": self.size_in(),
                "unit": self.v_unit.get(), "axes": self.axes}

    # --- 互動 -----------------------------------------------------------------
    def _on_unit(self) -> None:
        old, new = self._unit_prev, self.v_unit.get()
        dpi = self._dpi_or_default()
        try:
            wi, hi = size_to_inches(float(self.v_w.get()), float(self.v_h.get()), old, dpi)
        except Exception:
            wi, hi = self._size0
        w, h = inches_to_size(wi, hi, new, dpi)
        self.v_w.set(fmt_size(w, new))
        self.v_h.set(fmt_size(h, new))
        self._unit_prev = new
        self._refresh()

    def reset_size(self) -> None:
        w, h = inches_to_size(self._size0[0], self._size0[1], self.v_unit.get(), self._dpi_or_default())
        self.v_w.set(fmt_size(w, self.v_unit.get()))
        self.v_h.set(fmt_size(h, self.v_unit.get()))
        self._refresh()

    def _refresh(self) -> None:
        fmt = self.fmt()
        self.v_content.set(content_note(fmt))
        sz, dpi = self.size_in(), self.dpi()
        if sz is None or dpi is None:
            self.v_pixels.set(tr("寬高或 DPI 不對：DPI 要在 {lo}～{hi}，寬高要是正數（0.2～200 英吋）").format(lo=DPI_MIN, hi=DPI_MAX))
            return
        if is_vector(fmt):
            self.v_pixels.set(tr("輸出 {w:.2f} × {h:.2f} 英吋（向量）").format(w=sz[0], h=sz[1]))
        else:
            pw, ph = pixel_size(sz[0], sz[1], dpi)
            self.v_pixels.set(tr("輸出 {w} × {h} 像素").format(w=pw, h=ph) + ("" if not self.axes else tr("（裁切前）")))

    def export(self, path: Optional[str] = None) -> Optional[str]:
        """按「匯出…」：檢查欄位 → 選檔名（path 給了就不問）→ 存檔。成功回傳路徑並關閉對話框；取消或失敗回 None。"""
        o = self.options()
        if o["dpi"] is None or o["size_in"] is None:
            D.warn(self, tr("存成圖檔"), self.v_pixels.get())
            return None
        fmt = o["format"]
        if path is None:
            desc = dict(self.formats).get(fmt, fmt)
            path = ask_export_path(self, tr("存成圖檔"), f"{self.initialfile}.{fmt}",
                                   [(format_label(fmt, desc), f"*.{fmt}"), (tr("所有檔案"), "*.*")], fmt, self.initialdir)
            if not path:
                return None
        if ext_of(path) != fmt and ext_of(path) in dict(self.formats):
            fmt = ext_of(path)                     # 使用者在檔名打了別的副檔名：照副檔名存
        size = o["size_in"]
        same = abs(size[0] - self._size0[0]) < 1e-6 and abs(size[1] - self._size0[1]) < 1e-6
        if self.before is not None:
            try:
                self.before()
            except Exception:
                pass
        try:
            export_figure(self.fig, path, fmt=fmt, dpi=o["dpi"], background=o["background"],
                          size_in=None if same else size, axes=self.axes)
        except Exception as e:
            D.error(self, tr("存成圖檔"), tr("存檔失敗：{err}").format(err=e))
            return None
        DEFAULTS.update({"format": fmt, "dpi": int(round(o["dpi"])), "background": o["background"], "unit": o["unit"]})
        self.saved_path = path
        if self.on_saved is not None:
            self.on_saved(path)
        elif self.status is not None:
            self.status(tr("圖已存成 {path}").format(path=path))
        self.destroy()
        return path


def export_dialog(parent, fig, **kw) -> Optional["ExportDialog"]:
    """開匯出對話框（沒有 Tk 時回 None）。kw 見 ExportDialog。"""
    if not D.HAVE_TK:
        return None
    return ExportDialog(parent, fig, **kw)
