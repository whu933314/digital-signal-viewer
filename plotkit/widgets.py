# -*- coding: utf-8 -*-
"""plotkit.widgets — Tk 元件：PlotCanvas（可內嵌的互動圖）、FigureWindow（獨立視窗）、清單面板、就地編輯、快捷鍵、視窗登錄。"""
from __future__ import annotations

import os
import re
import sys
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
from matplotlib.figure import Figure

from . import dialogs as D
from . import theme as T
from .clipboard import copy_figure_to_clipboard, figure_to_png_bytes, save_png
from . import clipboard as _clip
from . import keys as _keys
from .dialogs import HAVE_TK, tk, ttk
from .draw import RenderInfo, auto_color, draw_state, format_tip_text, parse_tip_fields, restyle_line, view_of
from .i18n import tr
from .interact import Hit, Interactor, InteractorHost, InteractorModel
from .menus import popup_menu
from .model import CLIPBOARD, Annotation, FigureState, Series, load_json, save_json
from .styles import LINE_WIDTHS, LINESTYLES, MARKER_SIZES, MARKERS, STYLES, get_style, style_name
from .undo import UndoStack, redo_label, sync_undo_ui, undo_label

if HAVE_TK:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
else:  # pragma: no cover
    FigureCanvasTkAgg = NavigationToolbar2Tk = None  # type: ignore

IS_MAC = sys.platform == "darwin"
UNDO_LIMIT = 100
TIME_UNITS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "µs": 1e-6, "ns": 1e-9}     # 貼上時可以互相換算的 x 單位



BASE_STYLE_CHOICES = ("default", "matlab", "matlab-dark")     # 0.9.14 起圖片視窗「繪圖風格」下拉的三個


def style_choices(current: Optional[str] = None) -> Tuple[str, ...]:
    """圖片視窗「繪圖風格」下拉的選項：0.9.14 的三個（default／matlab／matlab-dark），加上目前介面主題的繪圖風格與這張圖現在用的風格
    （1.0.0 第 1 輪 R1：外觀主題的六個風格不全部列出來——MATLAB 兩個主題裡這個下拉和 0.9.14 一模一樣，外觀主題裡多它自己的那一個）。"""
    out = [n for n in BASE_STYLE_CHOICES if n in STYLES]
    th = T.current()
    for n in ((th.t.get("plot_style") if th is not None else None), current):
        if isinstance(n, str) and n in STYLES and n not in out:
            out.append(n)
    return tuple(out)


def fit_style_combo(cb, values) -> None:
    """圖片視窗的風格下拉：選項＝values；寬度 0.9.14 的三個時照舊 11，多了外觀主題的風格時放得下最長的名稱。"""
    cb.configure(values=tuple(values),
                 width=11 if set(values) <= set(BASE_STYLE_CHOICES) else _fit_chars(cb, values, 11))


def _fit_chars(widget, values, minimum: int) -> int:
    """下拉的寬度（字數，ttk 以「0」的寬為單位）：至少 minimum，放得下最長的選項。"""
    try:
        import tkinter.font as tkfont
        f = tkfont.nametofont(str(widget.cget("font")) or "TkTextFont")
        zero = max(1, f.measure("0"))
        need = max(-(-f.measure(str(v)) // zero) for v in values) + 1
    except Exception:
        need = max(len(str(v)) for v in values) + 1
    return max(minimum, need)

class _TrDict(dict):
    """值在取用時才經過 tr()：語言是 import 之後才設定的，模組層的 dict 不能先翻好（DSV 也直接用 MARKER_NAMES.get）。"""

    def __getitem__(self, key):
        return tr(dict.__getitem__(self, key))

    def get(self, key, default=None):
        return tr(dict.__getitem__(self, key)) if key in self else default

    def values(self):
        return [tr(v) for v in dict.values(self)]

    def items(self):
        return [(k, tr(v)) for k, v in dict.items(self)]


MARKER_NAMES = _TrDict({"": "無", ".": "點 .", "o": "圓 o", "x": "叉 x", "+": "加 +", "s": "方 s", "^": "三角 ^",
                        "v": "倒三角 v", "d": "菱形 d", "*": "星 *", ">": "右三角 >", "<": "左三角 <",
                        "p": "五角星 p", "h": "六角星 h"})
LINESTYLE_NAMES = {"-": "solid  -", "--": "dash  --", ":": "dot  :", "-.": "dash-dot  -.", "None": "none"}   # MATLAB 線條選單的叫法

# --- 視窗登錄與根視窗 --------------------------------------------------------------
_WINDOWS: List["FigureWindow"] = []
_ACTIVE: Optional["FigureWindow"] = None
_ROOT = None
_OWN_ROOT = False
_IN_SHOW = False


def ensure_root():
    """找到可用的 Tk 根視窗；沒有就自己建一個（隱藏）。"""
    global _ROOT, _OWN_ROOT
    if not HAVE_TK:
        raise RuntimeError("tkinter 不可用，無法開視窗（headless 只能用 plotkit 的無 GUI 功能）")
    root = getattr(tk, "_default_root", None)
    if root is not None:
        try:
            if root.winfo_exists():
                return root
        except Exception:
            pass
    if _ROOT is not None:
        try:
            if _ROOT.winfo_exists():
                return _ROOT
        except Exception:
            pass
    _ROOT = tk.Tk()
    _ROOT.withdraw()
    _OWN_ROOT = True
    try:
        T.ensure(_ROOT)                    # 自己建的根視窗：套 MATLAB 主題（預設 dark）
    except Exception:
        pass
    return _ROOT


def windows() -> List["FigureWindow"]:
    return [w for w in _WINDOWS if _alive(w)]


def active_window() -> Optional["FigureWindow"]:
    if _ACTIVE is not None and _alive(_ACTIVE):
        return _ACTIVE
    ws = windows()
    return ws[-1] if ws else None


def close_all() -> None:
    for w in list(_WINDOWS):
        try:
            w.close()
        except Exception:
            pass


def show(block: Optional[bool] = None) -> None:
    """進入事件迴圈。自己建的根視窗才會 mainloop；在別人的 Tk app 裡（或重入）只 update()。"""
    global _IN_SHOW
    root = ensure_root()
    if block is None:
        block = _OWN_ROOT
    if not block or _IN_SHOW or not windows():
        root.update()
        return
    _IN_SHOW = True
    try:
        root.mainloop()
    finally:
        _IN_SHOW = False


def _alive(w) -> bool:
    try:
        return bool(w.winfo_exists())
    except Exception:
        return False


def _set_active(w) -> None:
    global _ACTIVE
    _ACTIVE = w


def _unregister(w) -> None:
    global _ACTIVE
    if w in _WINDOWS:
        _WINDOWS.remove(w)
    if _ACTIVE is w:
        _ACTIVE = None


def _is_entry(widget) -> bool:
    try:
        return widget.winfo_class() in ("Entry", "TEntry", "Text", "TCombobox", "Spinbox", "TSpinbox")
    except Exception:
        return False


def bind_shortcuts(toplevel, pc: "PlotCanvas", close: Optional[Callable[[], Any]] = None) -> None:
    """Ctrl（macOS 另加 Command）+ z/y/Shift-Z/c/v/s/a 與 Delete；close 不是 None 時 Ctrl／⌘＋W 關閉。輸入框有焦點時放行（W 除外）。
    注音等非拉丁輸入法之下這些鍵的 keysym 是 "??"：另外綁一個 <Key> 照按鍵的實體位置認（plotkit.keys，2026-10-27 第二次選單「全部都修」）。"""
    def wrap(fn):
        def handler(e):
            if _is_entry(e.widget):
                return None
            fn()
            return "break"
        return handler

    table = {"z": pc.undo, "y": pc.redo, "Z": pc.redo, "c": pc.copy_selected, "v": pc.paste,
             "s": pc.save_json_dialog, "a": pc.select_all}
    mods = ["Control"] + (["Command"] if IS_MAC else [])
    for mod in mods:
        for key, fn in table.items():
            seq = f"<{mod}-Shift-{key}>" if key == "Z" else f"<{mod}-{key}>"
            try:
                toplevel.bind(seq, wrap(fn))
                if key == "z":
                    toplevel.bind(f"<{mod}-Z>", wrap(fn))       # CapsLock 開著時 keysym 是大寫 Z
            except Exception:
                pass
    # macOS 的 Tk 預設 Edit 選單會先接走 ⌘Z／⌘⇧Z／⌘C／⌘V／⌘A，元件收到的是虛擬事件；Windows／Linux 的 Ctrl 組合也會對應到同名虛擬事件
    for ev, fn in (("<<Undo>>", pc.undo), ("<<Redo>>", pc.redo), ("<<Copy>>", pc.copy_selected), ("<<Paste>>", pc.paste), ("<<SelectAll>>", pc.select_all)):
        try:
            toplevel.bind(ev, wrap(fn), add="+")
        except Exception:
            pass
    canvas_w = str(pc.canvas.get_tk_widget())

    def wrap_del(fn):
        def handler(e):
            if _is_entry(e.widget):
                return None
            if str(e.widget) == canvas_w and pc.ia.enable_keys and not pc.ia.blocked():
                return None                       # 畫布上的 Delete 已由 Interactor.on_key 處理（不然會連選取的線一起刪）
            fn()
            return "break"
        return handler

    for seq in ("<Delete>", "<BackSpace>"):
        toplevel.bind(seq, wrap_del(pc.delete_key))
    if close is not None:
        for mod in mods:
            toplevel.bind(f"<{mod}-w>", lambda e: (close(), "break")[1])     # MATLAB 圖形視窗 File > Close 的快速鍵 Ctrl+W

    def on_key(e):
        """注音之下 ⌘Z／⌘C／⌘V／⌘W… 的 keysym 是 "??"，上面的 <Command-z> 這些都對不到：照實體按鍵換回字母，做同一件事。
        ABC 之下 <Command-z> 比 <Key> 精確，Tk 只會執行那一個，不會走到這裡（不會做兩次）。"""
        k = _keys.command_key(e)
        if k is None:
            return None
        if k == "w":
            if close is None:
                return None
            close()
            return "break"
        fn = table.get(k)
        if fn is None:
            return None
        return wrap(fn)(e)

    toplevel.bind("<Key>", on_key, add="+")
    _keys.install_text_fallback(toplevel)          # 輸入框（標題…、圖例改名）的 ⌘C／⌘V／⌘X／⌘A 也照實體按鍵認


def fill_menu(menu, items) -> None:
    """把 Interactor.menu_items() 的清單放進 tk.Menu：None＝分隔線，(label, [(子項, 回呼), …])＝子選單。"""
    for it in items:
        if it is None:
            menu.add_separator()
        elif isinstance(it[1], (list, tuple)):
            sub = tk.Menu(menu, tearoff=0)
            for lab, cb in it[1]:
                sub.add_command(label=lab, command=cb)
            menu.add_cascade(label=it[0], menu=sub)
        else:
            menu.add_command(label=it[0], command=it[1])


# --- 就地編輯 -----------------------------------------------------------------------
class InlineEditor:
    """在 matplotlib 畫布上覆蓋一個 Entry，對準某個文字的 bbox（display 座標）。"""

    def __init__(self, canvas, bbox, text: str, on_commit: Callable[[Optional[str]], None]):
        widget = canvas.get_tk_widget()
        # TkAgg 的事件／renderer 座標就是 Tk 畫布像素（Windows 高 DPI 時 figure.dpi 已被放大），不用再除 device_pixel_ratio
        fig_h = canvas.figure.bbox.height
        x = bbox.x0
        y = fig_h - bbox.y1
        w = max(bbox.width + 24, 80)
        h = max(bbox.height + 6, 22)
        self.entry = ttk.Entry(widget)
        self.entry.insert(0, text)
        self.entry.place(x=x, y=y, width=w, height=h)
        self.entry.focus_set()
        self.entry.select_range(0, "end")
        self._done = False
        self._on_commit = on_commit
        self.entry.bind("<Return>", self._commit)
        self.entry.bind("<KP_Enter>", self._commit)
        self.entry.bind("<Escape>", self._cancel)
        self.entry.bind("<FocusOut>", self._commit)

    def _commit(self, e=None):
        if self._done:
            return
        self._done = True
        val = self.entry.get()
        self.entry.destroy()
        self._on_commit(val)

    def _cancel(self, e=None):
        if self._done:
            return
        self._done = True
        self.entry.destroy()
        self._on_commit(None)


# --- 清單面板 -------------------------------------------------------------------------
class SeriesListPanel(T.Panel):
    """左側「訊號」面板（MATLAB Workspace 那種：標題列＋表格）。"""
    COLS = ("vis", "name", "axis")
    HEADS = ("顯示", "名稱", "軸")

    def __init__(self, master, pc: "PlotCanvas"):
        super().__init__(master, tr("訊號"), collapsible=False, selectable=False)
        self.pc = pc
        self._syncing = False
        self._fix_style()
        th = T.ensure(self.winfo_toplevel())
        tf = ttk.Frame(self.body)
        tf.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tf, columns=self.COLS, show="headings", selectmode="extended", height=12)
        for c, h, w in zip(self.COLS, self.HEADS, (th.px(44), th.px(170), th.px(40))):
            self.tree.heading(c, text=tr(h))
            self.tree.column(c, width=w, minwidth=30, anchor="w" if c == "name" else "center", stretch=(c == "name"))
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.tag_configure("hidden", foreground=th["text2"])
        ttk.Label(self.body, text=tr("點 ☑ 切換顯示；雙擊名稱改名"), style="Small.TLabel").pack(anchor="w", padx=th.px(6), pady=(th.px(2), th.px(3)))
        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Button-3>", self._on_context)
        if IS_MAC:
            self.tree.bind("<Button-2>", self._on_context)
            self.tree.bind("<Control-Button-1>", self._on_context)

    def _fix_style(self):
        try:
            style = ttk.Style(self)

            def fixed_map(option):
                return [elm for elm in style.map("Treeview", query_opt=option) if elm[:2] != ("!disabled", "!selected")]

            style.map("Treeview", foreground=fixed_map("foreground"), background=fixed_map("background"))
        except Exception:
            pass

    def on_theme(self, th) -> None:
        super().on_theme(th)
        try:
            self.tree.tag_configure("hidden", foreground=th["text2"])
        except Exception:
            pass

    def refresh(self, state: FigureState, colors: Dict[int, str]) -> None:
        self._syncing = True
        try:
            t = self.tree
            yview = t.yview()
            t.delete(*t.get_children())
            for s in state.series:
                tags = ("hidden",) if not s.visible else ()
                color = colors.get(s.uid)
                if s.visible and color:
                    t.tag_configure(f"c{s.uid}", foreground=color)
                    tags = (f"c{s.uid}",)
                t.insert("", "end", iid=f"u{s.uid}", tags=tags,
                         values=("☑" if s.visible else "☐", s.label, tr("右") if s.yaxis == "right" else tr("左")))
            self.select(self.pc.selected)
            try:
                t.yview_moveto(yview[0])
            except Exception:
                pass
        finally:
            self._syncing = False

    def selected_uids(self) -> Set[int]:
        out = set()
        for iid in self.tree.selection():
            try:
                out.add(int(iid[1:]))
            except ValueError:
                pass
        return out

    def select(self, uids: Iterable[int]) -> None:
        want = [f"u{u}" for u in uids if self.tree.exists(f"u{u}")]
        if set(self.tree.selection()) == set(want):
            return                                   # 不重設：selection_set 每次都會再發 <<TreeviewSelect>>
        self._syncing = True
        try:
            self.tree.selection_set(want)
            if want:
                self.tree.see(want[-1])
        finally:
            self._syncing = False

    def _uid_at(self, y) -> Optional[int]:
        row = self.tree.identify_row(y)
        if not row:
            return None
        try:
            return int(row[1:])
        except ValueError:
            return None

    def _on_click(self, event):
        # 不用 identify("region")：視窗還沒真的顯示（例如遠端工作階段）時它回 "nothing"；欄＋列就能認出是哪一格
        if self.tree.identify_column(event.x) == "#1":
            uid = self._uid_at(event.y)             # 標題列／空白處 → None
            if uid is not None:
                self.pc.toggle_visible([uid])
            return "break"

    def _on_double(self, event):
        if self.tree.identify_column(event.x) == "#1":
            return "break"
        uid = self._uid_at(event.y)
        if uid is None:
            return
        s = self.pc.state.find(uid)
        bbox = self.tree.bbox(f"u{uid}", "#2")
        if s is None or not bbox:
            self.pc.edit_label([uid])
            return "break"
        x, y, w, h = bbox
        entry = ttk.Entry(self.tree)
        entry.insert(0, s.label)
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()
        entry.select_range(0, "end")
        done = {"v": False}

        def commit(e=None):
            if done["v"]:
                return
            done["v"] = True
            val = entry.get().strip()
            entry.destroy()
            if val and val != s.label:
                self.pc.rename(uid, val)

        def cancel(e=None):
            done["v"] = True
            entry.destroy()

        entry.bind("<Return>", commit)
        entry.bind("<KP_Enter>", commit)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", commit)
        return "break"

    def _on_select(self, event=None):
        if self._syncing:
            return
        uids = self.selected_uids()
        if uids == set(self.pc.selected):
            return                                   # 虛擬事件是排隊送來的，和目前狀態一樣就不要再繞一圈
        self.pc.select(uids, from_list=True)

    def _on_context(self, event):
        uid = self._uid_at(event.y)
        if uid is not None and uid not in self.selected_uids():
            self.tree.selection_set(f"u{uid}")
            self.pc.select({uid}, from_list=True)       # <<TreeviewSelect>> 是排隊送的：先同步，選單才有樣式項目
        self.pc.context_menu(Hit("list"), None, x_root=event.x_root, y_root=event.y_root)
        return "break"


# --- PlotCanvas -----------------------------------------------------------------------
class PlotCanvas(ttk.Frame, InteractorHost):
    """單張互動圖（可雙 y 軸）＋訊號清單＋工具列。所有改動經 mutate() 進 undo。"""

    def __init__(self, master, state: Optional[FigureState] = None, *, style=None, show_list: bool = True,
                 show_toolbar: bool = True, size: Tuple[float, float] = (8.0, 5.0), dpi: int = 100,
                 wheel_axis: str = "both"):
        ttk.Frame.__init__(self, master)
        th = T.ensure(self.winfo_toplevel())
        self.state = state if state is not None else FigureState(style=T.plot_style_name())
        self._style_follows_theme = state is None and style is None        # 沒指定風格 → 切主題時跟著換
        if style is not None:
            self.state.style = style
        self.selected: Set[int] = set()
        self.undo_stack = UndoStack(UNDO_LIMIT)
        self._undo_extra: List[Any] = []            # 視窗的工具列分頁上另外的復原／重做鈕、編輯選單（FigureWindow 登記；提示寫動作名稱）
        self._redo_extra: List[Any] = []
        self._undo_menus: List[tuple] = []
        self.info = RenderInfo()
        self._drawn_once = False
        self._editor = None
        self.v_tips = tk.BooleanVar(value=True)     # 預設跟 MATLAB 一樣：點線條就釘資料提示（Shift＋點＝選取）
        self._tips_resume = False                   # 平移／框選放大模式結束後要不要把資料提示開回來
        self.v_grid = tk.BooleanVar(value=bool(self.state.grid))
        self.v_legend = tk.BooleanVar(value=bool(self.state.legend))
        self.v_style = tk.StringVar(value=style_name(get_style(self.state.style)))
        self.v_status = tk.StringVar(value="")
        self.on_series_changed: Optional[Callable[[], None]] = None

        T.status_bar(self, self.v_status).pack(side="bottom", fill="x")
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=th.px(6), pady=(th.px(6), th.px(6)))
        self.list_panel = SeriesListPanel(paned, self)
        if show_list:
            paned.add(self.list_panel, weight=0)
        self.plot_panel = T.Panel(paned, tr("圖"), collapsible=False, selectable=False)
        paned.add(self.plot_panel, weight=1)
        right = self.plot_panel.body
        bar = ttk.Frame(right)
        bar.pack(side="top", fill="x")
        self.fig = Figure(figsize=size, dpi=dpi, layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.toolbar = None
        self.plot_toolbar = None
        if show_toolbar:
            self.plot_toolbar = T.PlotToolbar(bar, self.canvas)
            self.plot_toolbar.pack(side="left", fill="x", expand=True)
            self.toolbar = self.plot_toolbar.nav
            self.plot_toolbar.on_mode = self._on_nav_mode
            tb = self.plot_toolbar
            # 照 MATLAB axes toolbar 的順序：export（存檔、複製影像）→ data tips → pan → zoom → restore view；其餘是 plotkit 自己的
            tb.add_toggle("tips", "datatip", tr("資料提示模式：點線條釘住資料提示"), self.v_tips, self._on_tips_toggle, before="pan")
            tb.add_button("clip", "clipboard", tr("複製圖片到系統剪貼簿"), self.copy_image_to_clipboard, before="tips")
            # MATLAB Export 下拉的三項：Save as（save 鈕）／Copy as image（clip）／Copy as vector graphic（clipvec）
            bv = tb.add_button("clipvec", "export", _clip.vector_copy_tip(tr("複製向量圖（PDF）到系統剪貼簿")),
                               self.copy_vector_to_clipboard, before="tips")
            bv.state(["!disabled"] if _clip.vector_copy_state() == "normal" else ["disabled"])   # Windows：剪貼簿放不了向量圖
            tb.add_separator()           # 還原視圖就是上面的 Home 鈕（home_command＝restore_view），不再放第二顆
            self.btn_undo = tb.add_button("undo", "undo", tr("復原 (Ctrl+Z)"), self.undo)
            self.btn_redo = tb.add_button("redo", "redo", tr("重做 (Ctrl+Y)"), self.redo)
            tb.add_separator()
            tb.add_toggle("grid", "grid", tr("格線"), self.v_grid, lambda: self.set_grid(self.v_grid.get()))
            tb.add_toggle("legend", "legend", tr("圖例"), self.v_legend, lambda: self.set_legend(self.v_legend.get()))
            cb = ttk.Combobox(tb.left, textvariable=self.v_style, values=BASE_STYLE_CHOICES, width=11, state="readonly")
            self.style_combo = cb
            self._refresh_style_choices()
            cb.configure(postcommand=self._refresh_style_choices)       # 換了介面主題之後再打開：選項跟著目前的主題
            cb.pack(side="left", padx=th.px(4))
            cb.bind("<<ComboboxSelected>>", lambda e: self.set_style(self.v_style.get()))
            T.tooltip(cb, tr("繪圖風格"))
        else:
            self.btn_undo = ttk.Button(bar, text=tr("復原"), command=self.undo)
            self.btn_redo = ttk.Button(bar, text=tr("重做"), command=self.redo)
        self.ia = Interactor(self.canvas, self, toolbar=self.toolbar,
                             model=InteractorModel(self.state.tips, self.state.annotations), wheel_axis=wheel_axis)
        self.ia.tips_enabled = bool(self.v_tips.get())
        if self.plot_toolbar is not None:
            self.plot_toolbar.home_command = self.restore_view      # 工具列 Home 與 Home 鍵／雙擊同一個「原始視圖」
        try:
            self.canvas.get_tk_widget().configure(background=th["bg"])
        except Exception:
            pass
        T.listen(self)
        self.canvas.get_tk_widget().bind("<Enter>", self._on_canvas_enter)
        has_view = any(self.state.view.get(k) for k in ("xlim", "ylim", "ylim_right"))
        self.redraw(keep_view=False, autoscale=not has_view)       # open_json / state= 要保留存檔時的視圖範圍
        self._update_undo_ui()

    def on_theme(self, th) -> None:
        """切換介面主題：沒指定過風格的圖跟著換成主題的繪圖風格。"""
        try:
            self.canvas.get_tk_widget().configure(background=th["bg"])
        except Exception:
            pass
        if self._style_follows_theme and self.state.style != th["plot_style"]:
            self.state.style = th["plot_style"]
            self.redraw()

    def _on_canvas_enter(self, event=None) -> None:
        """Windows 的 Tk 把滾輪送給「有焦點」的元件：游標進到圖上就把焦點給畫布（正在打字除外）。"""
        if not sys.platform.startswith("win"):
            return
        try:
            f = self.focus_get()
            if f is not None and _is_entry(f):
                return
        except Exception:
            pass
        try:
            self.canvas.get_tk_widget().focus_set()
        except Exception:
            pass

    # --- 畫 ----------------------------------------------------------------------
    def _style(self) -> dict:
        return get_style(self.state.style)

    def _colors(self) -> Dict[int, str]:
        st = self._style()
        out = {}
        for k, s in enumerate(self.state.series):
            ln = self.info.lines.get(s.uid)
            out[s.uid] = ln.get_color() if ln is not None else (s.color or auto_color(st, k))
        return out

    def redraw(self, *, autoscale: bool = False, keep_view: bool = True) -> None:
        view = view_of(self.info) if (keep_view and self._drawn_once and not autoscale) else None
        if view is None:
            self.ia.forget_home()          # 新的視圖（自動縮放／設定範圍）＝新的原始視圖（MATLAB 新 plot 會清掉 stored view）
        self.ia.reset()
        self.info = draw_state(self.fig, self.state, selected=self.selected, view=view, autoscale=autoscale)
        self.ia.tip_fields = parse_tip_fields(self.state.tip_fields)     # 開圖檔／復原後跟著圖檔的「提示內容」
        self.ia.rebuild()
        self._drawn_once = True
        self.state.view = view_of(self.info)
        self.v_grid.set(bool(self.state.grid))
        self.v_legend.set(bool(self.state.legend))
        self.v_style.set(style_name(self._style()))
        if getattr(self, "style_combo", None) is not None:
            self._refresh_style_choices()
        self.list_panel.refresh(self.state, self._colors())
        self.canvas.draw_idle()
        if self.on_series_changed:
            self.on_series_changed()

    def highlight(self, sync_list: bool = True) -> None:
        st = self._style()
        for k, s in enumerate(self.state.series):
            ln = self.info.lines.get(s.uid)
            if ln is not None:
                restyle_line(ln, s, st, k, selected=s.uid in self.selected)
        if sync_list:
            self.list_panel.select(self.selected)
        self.canvas.draw_idle()

    @contextmanager
    def mutate(self, desc: str, tag: Optional[str] = None, *, autoscale: bool = False, keep_view: bool = True):
        before = self.state.snapshot()
        try:
            yield
        except Exception:
            self.state.restore(before)                             # 改到一半出錯：退回原狀，不留半套
            self.redraw(keep_view=keep_view)
            raise
        self.undo_stack.push(before, desc, tag)
        self.redraw(autoscale=autoscale, keep_view=keep_view)
        self._update_undo_ui()
        self.status(desc)

    def _update_undo_ui(self) -> None:
        """復原／重做：依堆疊啟用／停用，提示與選單寫「復原：<動作>」（MATLAB Edit 選單的 Undo: Pan）。"""
        try:
            sync_undo_ui(self.undo_stack, [self.btn_undo] + list(self._undo_extra), [self.btn_redo] + list(self._redo_extra),
                         ("Ctrl+Z", "Ctrl+Y"), self._undo_menus)
        except Exception:
            pass

    # --- InteractorHost ----------------------------------------------------------------
    def style(self) -> dict:
        return self._style()

    def lines_in(self, ax) -> List[Tuple[int, Any]]:
        bus = self.info.bus                # 匯流排：點框內任何地方都算（看不見的 hit 線）
        return [(uid, bus[uid]["hit"] if uid in bus else ln) for uid, ln in self.info.lines.items() if ln.axes is ax]

    def series_data(self, uid: int):
        s = self.state.find(uid)
        if s is None or not s.visible or s.n == 0:
            return None
        ax = self.info.axes_for(s.yaxis)
        if ax is None:
            return None
        b = self.info.bus.get(uid)
        if b is not None:                  # 匯流排：提示釘在樣本、y＝框中心（提示文字寫樣本值）
            return s.x[:s.n] + s.xshift, np.full(s.n, b["center"]), s.label, ax
        return s.x[:s.n] + s.xshift, s.y + s.yshift, s.label, ax

    def _bus_value(self, s, uid: int, index: int, y: float):
        """匯流排的提示：y＝樣本值（不是框中心），y_text＝進位制文字（沒選進位制 None）。"""
        if s is None or uid not in self.info.bus or not (0 <= int(index) < s.n):
            return y, None
        from . import bus as pbus
        v = float(s.y[int(index)])
        return v, (pbus.format_value(v, s.radix, s.bits, prefix=True) if s.radix else None)

    def axes_for_key(self, key):
        return self.info.axes_for("right" if key == "right" else "left")

    def axes_key_for(self, ax):
        return self.info.key_for(ax)

    def legend_entries(self, ax) -> List[int]:
        return list(self.info.legend_uids) if (self.info.legend is not None and self.info.legend.axes is ax) else []

    def tip_text(self, uid: int, index: int, x: float, y: float) -> str:
        s = self.state.find(uid)
        y, yt = self._bus_value(s, uid, index, y)
        text = format_tip_text(s.label if s else str(uid), x, y, (s.xunit if s else "") or self.state.xunit)
        return text.rsplit("\n", 1)[0] + f"\nY {yt}" if yt else text

    def tip_record(self, uid: int, index: int, x: float, y: float) -> dict:
        s = self.state.find(uid)
        side = s.yaxis if s is not None else "left"
        y, yt = self._bus_value(s, uid, index, y)
        return {"name": s.label if s else str(uid), "x": x, "y": y, "index": int(index),
                "panel": tr("右軸") if side == "right" else tr("左軸"), "xunit": ((s.xunit if s else "") or self.state.xunit),
                "y_text": yt}

    def on_tip_fields(self, fields) -> None:
        """「提示內容…」：存進圖檔（FigureState.tip_fields，可復原）。"""
        if list(fields) == list(self.state.tip_fields):
            return
        with self.mutate(tr("提示內容")):
            self.state.tip_fields = list(fields)

    def on_restore_view(self) -> bool:
        self.status(tr("還原視圖"))
        if self.ia.has_home():             # 第一次互動前的視圖（MATLAB Restore View）：Interactor 自己回去
            return False
        self.redraw(autoscale=True)        # 還沒互動過：回到自動範圍
        return True

    def on_pick(self, uid: int, event, hit: Hit) -> None:
        from .draw import has_mod
        if has_mod(event, "shift"):
            self.select({uid} ^ self.selected if uid in self.selected else self.selected | {uid})
        else:
            self.select({uid})
        s = self.state.find(uid)
        if s:
            self.status((tr("已選取：{name}（右鍵更多、Ctrl+C 複製）") if self.ia.tips_enabled else
                         tr("已選取：{name}（雙擊改顏色、右鍵更多、Ctrl+C 複製）")).format(name=s.label))

    def on_click_empty(self, event) -> None:
        if self.selected:
            self.select(set())

    def on_double_click(self, hit: Hit, event) -> bool:
        if hit.kind == "line":
            self.select({hit.id})
            self.edit_color()
            return True
        if hit.kind == "legend" and hit.id is not None:
            self.edit_label([hit.id])
            return True
        return False

    def on_context(self, hit: Hit, event) -> None:
        g = getattr(event, "guiEvent", None)
        if g is not None and hasattr(g, "x_root"):
            self.context_menu(hit, event, x_root=g.x_root, y_root=g.y_root)
        else:
            x, y = self.winfo_pointerxy()
            self.context_menu(hit, event, x_root=x, y_root=y)

    def on_rename(self, uid: int, label: str) -> None:
        self.rename(uid, label)

    def on_edit_text(self, ann_id: int, text: str) -> None:
        self.ia.update_annotation(ann_id, text=text)

    def on_edit_annotation(self, ann_id: int) -> None:
        a = next((x for x in self.state.annotations if x.id == ann_id), None)
        if a is None:
            return
        if a.kind == "text":
            v = D.ask_string(self, tr("編輯文字"), tr("文字："), a.text)
            if v is not None and v.strip():
                self.ia.update_annotation(ann_id, text=v.strip())
        else:
            v = D.ask_float(self, tr("編輯參考線"), tr("x 位置：") if a.kind == "xline" else tr("y 位置："), a.value)
            if v is None:
                return
            t = D.ask_string(self, tr("編輯參考線"), tr("標籤（可空白）："), a.text)
            self.ia.update_annotation(ann_id, value=float(v), text=(t or "").strip())

    def on_insert(self, kind: str, ax, x: float, y: float) -> None:
        key = self.info.key_for(ax)
        if kind == "xline":
            self.insert_xline_at(x)
        elif kind == "yline":
            self.insert_yline_at(y, axes_key=key)
        else:
            self.insert_text_at(x, y, axes_key=key)

    def before_model_change(self, what: str, tag: Optional[str] = None) -> None:
        self._last_push_new = self.undo_stack.push(
            self.state.snapshot(), {"tip_add": tr("新增資料提示"), "tip_remove": tr("刪除資料提示"),
                                    "tip_clear": tr("清除資料提示"), "tip_move": tr("移動資料提示"),
                                    "ann_add": tr("插入標註"), "ann_edit": tr("編輯標註"),
                                    "ann_remove": tr("刪除標註"), "ann_move": tr("移動標註")}.get(what, what), tag)

    def on_model_change(self, what: str) -> None:
        self._update_undo_ui()

    def on_model_cancel(self, what: str) -> None:
        if getattr(self, "_last_push_new", False):                 # Esc 取消拖曳：拿掉剛推進去的那筆（被 2 秒合併的不動）
            self.undo_stack.discard_last()
            self._last_push_new = False
        self._update_undo_ui()

    def on_view_change(self, ax) -> None:
        self.state.view = view_of(self.info)

    def before_view_change(self, tag: str) -> None:
        """鍵盤縮放／平移之前：推一筆「視圖」undo（MATLAB 圖形視窗 Ctrl+Z 復原鍵盤縮放平移）。"""
        snap = self.state.snapshot()
        snap["_view_undo"] = True
        self.undo_stack.push(snap, tr("縮放／平移"), tag)
        self._update_undo_ui()

    def _apply_snapshot_view(self, view: dict) -> None:
        """只套用視圖範圍（視圖 undo／redo），不重畫資料。"""
        ax, axr = self.info.ax_left, self.info.ax_right
        if ax is not None and view.get("xlim"):
            ax.set_xlim(*view["xlim"])
        if ax is not None and view.get("ylim"):
            ax.set_ylim(*view["ylim"])
        if axr is not None and view.get("ylim_right"):
            axr.set_ylim(*view["ylim_right"])
        self.state.view = view_of(self.info)
        self.ia._push_toolbar()                  # 上一個／下一個視圖跟著記
        self.canvas.draw_idle()

    def on_delete_key(self) -> None:
        self.delete_selected()

    def on_legend_move(self, ax, loc) -> None:
        self.set_legend(True, loc=tuple(loc))

    def on_legend_loc(self, ax, loc: str) -> None:
        self.set_legend(True, loc=loc)

    def on_legend_delete(self, ax) -> None:
        self.set_legend(False)

    def begin_inline_edit(self, bbox, text: str, on_commit) -> bool:
        self._editor = InlineEditor(self.canvas, bbox, text, on_commit)
        return True

    def status(self, msg: str) -> None:
        self.v_status.set(msg)

    def _tips_off(self) -> None:
        if self.v_tips.get():
            self.v_tips.set(False)
            self._on_tips_toggle()

    def _on_nav_mode(self, mode: str) -> None:
        """工具列的平移／框選放大開著時資料提示暫停，關掉後恢復（MATLAB 的互動模式也是這樣）。"""
        if mode:
            resume = bool(self.v_tips.get()) or self._tips_resume
            self._tips_off()
            self._tips_resume = resume
        elif self._tips_resume:
            self.v_tips.set(True)
            self._on_tips_toggle()

    def _on_tips_toggle(self) -> None:
        self._tips_resume = False
        self.ia.tips_enabled = bool(self.v_tips.get())
        if self.ia.tips_enabled and self.plot_toolbar is not None:
            self.plot_toolbar.clear_mode()                 # 平移／框選放大開著時點擊會被吃掉
        self.status(tr("資料提示模式：點線條釘住；拖曳移動、Delete 刪除") if self.ia.tips_enabled else "")

    # --- 訊號 ----------------------------------------------------------------------
    def add_series(self, series: Iterable[Series], *, select: bool = True, autoscale: bool = True) -> List[Series]:
        items = list(series)
        if not items:
            return []
        with self.mutate(tr("加入 {n} 條").format(n=len(items)), autoscale=autoscale):
            if not self.state.xunit:                   # 線都同一個 x 單位（例如 DSV 複製過來的 us）→ x 軸標籤顯示 x [us]
                units = {s.xunit for s in list(self.state.series) + items if s.xunit}
                if len(units) == 1:
                    self.state.xunit = units.pop()
            for s in items:
                self.state.add_series(s)
            if select:
                self.selected = {s.uid for s in items}
        return items

    _KW_ALIASES = {"linewidth": "lw", "linestyle": "ls", "markersize": "ms", "c": "color", "name": "label"}

    def plot(self, x, y=None, *args, label: Optional[str] = None, kind: str = "line", **kw) -> Series:
        if args:                                              # 第三個位置參數＝label（pyplot 的格式字串不收）
            if len(args) > 1:
                raise TypeError("plot() 最多三個位置參數：x, y, label")
            if label is not None:
                raise TypeError("label 給了兩次（位置參數與 label=）")
            label = args[0]
            if isinstance(label, str) and label and set(label) <= set("rgbcmykw-.:,o+*xsd^v<>|_ ") and len(label) <= 4:
                raise ValueError(f"第三個參數是 label，不是 pyplot 的格式字串 {label!r}；請用 color=…, ls=…, marker=…"
                                 f"（真的要叫這個名字請寫 label={label!r}）")
        if y is None:
            y = np.asarray(x, dtype=float)
            x = np.arange(len(y))
        for long, short in self._KW_ALIASES.items():          # 接受 pyplot 的長名稱
            if long in kw:
                kw.setdefault(short, kw.pop(long))
        if label is not None and "label" in kw:
            kw.pop("label")
        s = Series(label if label is not None else kw.pop("label", f"series {len(self.state.series) + 1}"), x, y, kind=kind, **kw)
        self.add_series([s], select=False)
        return s

    def step(self, x, y, *args, **kw) -> Series:
        return self.plot(x, y, *args, kind="step", **kw)

    def series(self) -> List[Series]:
        return list(self.state.series)

    def remove_series(self, uids: Iterable[int]) -> None:
        uids = set(uids)
        if not uids:
            return
        with self.mutate(tr("刪除 {n} 條").format(n=len(uids))):
            self.state.remove_series(uids)
            self.selected -= uids

    def delete_selected(self) -> None:
        self.remove_series(set(self.selected))

    def delete_key(self) -> None:
        """焦點不在畫布上時的 Delete：跟 Interactor.on_key 同順序——選取的提示 → 選取的標註 → 選取的線。"""
        if self.ia.selected_tip is not None:
            self.ia.remove_tip(self.ia.selected_tip)
        elif getattr(self.ia, "selected_ann", None) is not None:
            self.ia.remove_annotation(self.ia.selected_ann)
        else:
            self.delete_selected()

    def clear(self) -> None:
        with self.mutate(tr("清空")):
            self.state.series = []
            self.state.tips[:] = []
            self.selected = set()

    def set_props(self, uids: Iterable[int], desc: Optional[str] = None, **props) -> None:
        uids = set(uids)
        with self.mutate(tr("樣式") if desc is None else desc):
            for s in self.state.series:
                if s.uid in uids:
                    for k, v in props.items():
                        setattr(s, k, v)

    def rename(self, uid: int, label: str) -> None:
        self.set_props([uid], tr("改名 {name}").format(name=label), label=str(label))

    def set_visible(self, uids: Iterable[int], flag: bool) -> None:
        self.set_props(uids, tr("顯示") if flag else tr("隱藏"), visible=bool(flag))

    def toggle_visible(self, uids: Iterable[int]) -> None:
        uids = set(uids)
        with self.mutate(tr("顯示／隱藏")):
            for s in self.state.series:
                if s.uid in uids:
                    s.visible = not s.visible

    def set_yaxis(self, uids: Iterable[int], side: str) -> None:
        self.set_props(uids, tr("右軸") if side == "right" else tr("左軸"), yaxis=side)

    def set_shift(self, uids: Iterable[int], axis: str, value: float) -> None:
        self.set_props(uids, tr("{axis} 位移 {v:g}").format(axis=axis, v=value), **{f"{axis}shift": float(value)})

    def select(self, uids: Iterable[int], *, add: bool = False, from_list: bool = False) -> None:
        new = set(uids)
        self.selected = (self.selected | new) if add else new
        ia = getattr(self, "ia", None)
        if self.selected and ia is not None and ia.selected_tip is not None:
            ia.deselect_tip(draw=False)              # 選取互斥：選了線就取消提示的選取（Delete 只刪目前選的那一種）
        if self.selected and ia is not None and getattr(ia, "selected_ann", None) is not None:
            ia.select_annotation(None, draw=False)   # …也取消標註的選取
        self.highlight(sync_list=not from_list)

    def on_tip_selected(self, tip_id: int) -> None:
        if self.selected:
            self.select(set())

    def select_all(self) -> None:
        self.select({s.uid for s in self.state.series})

    def selected_series(self) -> List[Series]:
        return [s for s in self.state.series if s.uid in self.selected]

    def targets(self) -> List[Series]:
        sel = self.selected_series()
        if not sel:
            D.info(self, "plotkit", tr("請先在清單選取訊號，或在圖上 Shift＋點線條。"))
        return sel

    # --- 樣式對話框 -----------------------------------------------------------------
    def edit_color(self) -> None:
        sel = self.targets()
        if not sel:
            return
        cur = self._colors().get(sel[0].uid) or "#1f77b4"
        hx = D.ask_color(self, tr("線色：{name}").format(name=sel[0].label), cur)
        if hx:
            self.set_props([s.uid for s in sel], tr("線色 {color}").format(color=hx), color=hx)

    def set_linewidth(self, v: float) -> None:
        sel = self.targets()
        if sel:
            self.set_props([s.uid for s in sel], tr("線寬 {v:g}").format(v=v), lw=float(v))

    def edit_linewidth(self) -> None:
        sel = self.targets()
        if not sel:
            return
        v = D.ask_float(self, tr("線寬"), tr("線寬（點）："), sel[0].lw or self._style()["lw"], 0.1, 20.0)
        if v is not None:
            self.set_props([s.uid for s in sel], tr("線寬 {v:g}").format(v=v), lw=float(v))

    def set_linestyle(self, ls: Optional[str]) -> None:
        sel = self.targets()
        if sel:
            self.set_props([s.uid for s in sel], tr("線型 {ls}").format(ls=ls or "-"), ls=ls)

    def set_marker(self, m: str) -> None:
        sel = self.targets()
        if sel:
            self.set_props([s.uid for s in sel], tr("標記 {marker}").format(marker=MARKER_NAMES.get(m, m)), marker=m)

    def set_markersize(self, v: float) -> None:
        sel = self.targets()
        if sel:
            self.set_props([s.uid for s in sel], tr("標記大小 {v:g}").format(v=v), ms=float(v))

    def edit_markersize(self) -> None:
        sel = self.targets()
        if not sel:
            return
        v = D.ask_float(self, tr("標記大小"), tr("標記大小（點）："), sel[0].ms or self._style()["ms"], 1.0, 30.0)
        if v is not None:
            self.set_props([s.uid for s in sel], tr("標記大小 {v:g}").format(v=v), ms=float(v))

    def edit_label(self, uids: Optional[Iterable[int]] = None) -> None:
        sel = [s for s in self.state.series if s.uid in set(uids)] if uids else self.targets()
        if not sel:
            return
        v = D.ask_string(self, tr("改名"), tr("顯示名稱："), sel[0].label)
        if v is not None and v.strip():
            self.set_props([s.uid for s in sel], tr("改名 {name}").format(name=v.strip()), label=v.strip())

    def edit_shift(self, axis: str) -> None:
        sel = self.targets()
        if not sel:
            return
        cur = getattr(sel[0], f"{axis}shift", 0.0)
        v = D.ask_float(self, tr("{axis} 位移").format(axis=axis), tr("{axis} 位移量：").format(axis=axis), cur)
        if v is not None:
            self.set_shift([s.uid for s in sel], axis, float(v))

    def reset_style(self) -> None:
        sel = self.targets()
        if sel:
            self.set_props([s.uid for s in sel], tr("重設樣式"), color=None, lw=None, ls=None, marker="", ms=None, alpha=1.0)

    # --- 標註 -----------------------------------------------------------------------
    def insert_xline_at(self, x: float, text: str = "", **kw) -> Annotation:
        return self.ia.add_annotation(Annotation(kind="xline", value=float(x), text=text, axes_key="left", **kw))

    def insert_yline_at(self, y: float, text: str = "", axes_key: str = "left", **kw) -> Annotation:
        return self.ia.add_annotation(Annotation(kind="yline", value=float(y), text=text, axes_key=axes_key, **kw))

    def insert_text_at(self, x: float, y: float, text: Optional[str] = None, axes_key: str = "left", **kw) -> Optional[Annotation]:
        if text is None:
            text = D.ask_string(self, tr("插入文字"), tr("文字："), "")
            if text is None or not text.strip():
                return None
        return self.ia.add_annotation(Annotation(kind="text", x=float(x), y=float(y), text=text.strip(), axes_key=axes_key, **kw))

    def remove_annotation(self, ann_id: int) -> None:
        self.ia.remove_annotation(ann_id)

    def add_annotation(self, ann: Annotation) -> Annotation:
        return self.ia.add_annotation(ann)

    def update_annotation(self, ann_id: int, **fields) -> None:
        self.ia.update_annotation(ann_id, **fields)

    # --- 圖的屬性 ---------------------------------------------------------------------
    def set_title(self, s: str) -> None:
        with self.mutate(tr("標題")):
            self.state.title = str(s)

    def set_xlabel(self, s: str) -> None:
        with self.mutate(tr("x 標籤")):
            self.state.xlabel = str(s)

    def set_ylabel(self, s: str, side: str = "left") -> None:
        with self.mutate(tr("y 標籤")):
            if side == "right":
                self.state.ylabel_right = str(s)
            else:
                self.state.ylabel = str(s)

    def set_grid(self, on: bool) -> None:
        with self.mutate("Grid"):
            self.state.grid = bool(on)

    def set_legend(self, on: bool, loc=None) -> None:
        """loc：matplotlib 的位置名稱，或圖例左下角的 (x, y)（axes 座標，拖曳圖例會存這種）。"""
        if loc:
            from matplotlib.legend import Legend
            if isinstance(loc, (tuple, list)):
                if len(loc) != 2:
                    raise ValueError(f"legend loc 不合法：{loc!r}")
                loc = (float(loc[0]), float(loc[1]))
            elif loc not in Legend.codes:
                raise ValueError(f"legend loc 不合法：{loc!r}（可用：{', '.join(Legend.codes)}）")   # 先驗證，不動狀態
        with self.mutate("Legend"):
            self.state.legend = bool(on)
            if loc:
                self.state.legend_loc = loc

    def _refresh_style_choices(self) -> None:
        """風格下拉的選項與寬度跟著目前的介面主題與這張圖的風格（style_choices）。"""
        cb = getattr(self, "style_combo", None)
        try:
            if cb is not None and cb.winfo_exists():
                fit_style_combo(cb, style_choices(self.v_style.get()))
        except Exception:
            pass

    def set_style(self, spec) -> None:
        self._style_follows_theme = False
        get_style(spec)                                           # 不合法的風格先在這裡丟錯，不改狀態
        with self.mutate(tr("風格 {name}").format(name=spec if isinstance(spec, str) else "custom")):
            self.state.style = spec

    @staticmethod
    def _pair(a, b):
        if isinstance(a, (tuple, list)) and b is None and len(a) == 2:    # 也接受 xlim((a, b))
            a, b = a
        return a, b

    def set_xlim(self, a=None, b=None) -> None:
        a, b = self._pair(a, b)
        self.state.view["xlim"] = None if a is None else [float(a), float(b)]
        self.redraw(keep_view=False, autoscale=a is None)

    def set_ylim(self, a=None, b=None, side: str = "left") -> None:
        a, b = self._pair(a, b)
        key = "ylim_right" if side == "right" else "ylim"
        self.state.view[key] = None if a is None else [float(a), float(b)]
        self.redraw(keep_view=False, autoscale=a is None)

    def restore_view(self) -> None:
        self.ia.restore_view()

    # --- undo / 剪貼簿 / 檔案 ------------------------------------------------------------
    def undo(self) -> None:
        desc = self.undo_stack.peek_desc()
        cur = self.state.snapshot()
        snap = self.undo_stack.undo(cur)
        if snap is None:
            self.status(tr("沒有可復原的動作"))
            return
        if snap.get("_view_undo"):
            cur["_view_undo"] = True                 # 重做時也只動視圖
        self.state.restore(snap)
        self.selected &= {s.uid for s in self.state.series}
        self.redraw()
        if snap.get("_view_undo"):
            self._apply_snapshot_view(snap.get("view") or {})
        self._update_undo_ui()
        self.status(tr("已復原：{desc}").format(desc=desc) if desc else tr("已復原"))

    def redo(self) -> None:
        desc = self.undo_stack.peek_redo_desc()
        cur = self.state.snapshot()
        snap = self.undo_stack.redo(cur)
        if snap is None:
            self.status(tr("沒有可重做的動作"))
            return
        if snap.get("_view_undo"):
            cur["_view_undo"] = True
        self.state.restore(snap)
        self.selected &= {s.uid for s in self.state.series}
        self.redraw()
        if snap.get("_view_undo"):
            self._apply_snapshot_view(snap.get("view") or {})
        self._update_undo_ui()
        self.status(tr("已重做：{desc}").format(desc=desc) if desc else tr("已重做"))

    def copy_selected(self) -> None:
        sel = self.targets()
        if not sel:
            return
        CLIPBOARD[:] = [s.copy() for s in sel]
        self.status(tr("已複製 {n} 條，到別的視窗按 Ctrl+V（macOS ⌘V）貼上").format(n=len(sel)))

    def _match_xunit(self, items: List[Series]) -> Tuple[List[Series], str]:
        """貼上的線和這張圖的 x 單位不同時：時間單位（s／ms／us／ns）照比例換算；換不了（例如 symbol）就保留並提醒。"""
        unit = self.state.xunit or next((s.xunit for s in self.state.series if s.xunit), "")
        if not unit:
            return items, ""
        out, notes = [], []
        for s in items:
            a, b = TIME_UNITS.get(s.xunit), TIME_UNITS.get(unit)
            if not s.xunit or s.xunit == unit:
                out.append(s)
            elif a and b:
                k = a / b
                out.append(s.copy(x=s.x * k, xshift=s.xshift * k, xunit=unit))
                notes.append(tr("{name}：x 從 {a} 換算成 {b}").format(name=s.label, a=s.xunit, b=unit))
            else:
                out.append(s)
                notes.append(tr("注意：{name} 的 x 單位是 {a}，這張圖是 {b}（無法換算）").format(name=s.label, a=s.xunit, b=unit))
        return out, tr("；").join(notes)

    def paste(self, series: Optional[Sequence[Series]] = None) -> List[Series]:
        src = list(series) if series is not None else list(CLIPBOARD)
        if not src:
            self.status(tr("剪貼簿是空的：先選訊號按 Ctrl+C"))
            return []
        copies, note = self._match_xunit([s.copy(uid=0) for s in src])
        self.add_series(copies, select=True)
        msg = tr("貼上 {n} 條，共 {total} 條").format(n=len(copies), total=len(self.state.series))
        self.status(msg + (tr("；") + note if note else ""))
        return copies

    def copy_to_new_window(self) -> Optional["FigureWindow"]:
        sel = self.targets()
        if not sel:
            return None
        CLIPBOARD[:] = [s.copy() for s in sel]
        return FigureWindow(None, series=CLIPBOARD, style=None if self._style_follows_theme else self.state.style)

    def save_json(self, path: str) -> None:
        save_json(self.state, path)
        self.status(tr("已存到 {path}").format(path=path))

    def load_json(self, path: str) -> None:
        try:
            st = load_json(path)
        except Exception as e:                                  # 壞掉／不是 plotkit 的 JSON：對話框說明，視窗不動
            self.status(tr("開啟失敗：{err}").format(err=e))
            try:
                D.messagebox.showerror(tr("開啟 JSON"), tr("讀不了 {path}：\n{err}").format(path=path, err=f"{type(e).__name__}: {e}"),
                                       parent=self)
            except Exception:
                pass
            return
        self.state = st
        self.selected = set()
        self.undo_stack.clear()
        self._style_follows_theme = False            # 檔案裡存了風格，切主題不要蓋掉
        self.ia.model = InteractorModel(self.state.tips, self.state.annotations)
        self.redraw(keep_view=False)
        self._update_undo_ui()
        self.status(tr("已開啟 {path}").format(path=path))

    def save_json_dialog(self) -> None:
        p = D.filedialog.asksaveasfilename(parent=self, title=tr("另存 JSON"), defaultextension=".json",
                                           filetypes=[("plotkit JSON", "*.json")])
        if p:
            self.save_json(p)

    def open_json_dialog(self) -> None:
        p = D.filedialog.askopenfilename(parent=self, title=tr("開啟 JSON"),
                                         filetypes=[("plotkit JSON", "*.json"), (tr("所有檔案"), "*.*")])
        if p:
            self.load_json(p)

    def savefig(self, path: str, dpi: Optional[int] = None) -> None:
        save_png(self.fig, path, dpi=dpi or 150)
        self.status(tr("已存圖 {path}").format(path=path))

    def savefig_dialog(self):
        """「存成圖檔…」：匯出對話框（格式、DPI、背景、尺寸；plotkit.export）。"""
        from .export import export_dialog
        return export_dialog(self, self.fig, **self.export_options(None))

    def export_options(self, ax) -> dict:
        """InteractorHost：匯出對話框的檔名預設用視窗標題、存好後寫狀態列。"""
        try:
            name = re.sub(r'[\\/:*?"<>|]+', "_", str(self.winfo_toplevel().title())).strip() or "figure"
        except Exception:
            name = "figure"
        return {"initialfile": name, "on_saved": lambda p: self.status(tr("已存圖 {path}").format(path=p))}

    def png_bytes(self) -> bytes:
        return figure_to_png_bytes(self.fig)

    def copy_image_to_clipboard(self) -> Tuple[bool, str]:
        ok, msg = copy_figure_to_clipboard(self.fig)
        self.status(msg)
        return ok, msg

    def copy_vector_to_clipboard(self) -> Tuple[bool, str]:
        """跟 MATLAB 座標區工具列 Export → Copy as vector graphic 一樣：向量圖（PDF）放進系統剪貼簿。"""
        ok, msg = copy_figure_to_clipboard(self.fig, content="vector")
        self.status(msg)
        return ok, msg

    # --- 右鍵選單 -----------------------------------------------------------------------
    def context_menu(self, hit: Hit, event, *, x_root: int, y_root: int) -> None:
        if hit.kind == "line" and hit.id is not None and hit.id not in self.selected:
            self.select({hit.id})
        m = tk.Menu(self, tearoff=0)
        if self.selected and hit.kind not in ("legend", "legend_box"):     # 圖例上右鍵＝圖例自己的選單（MATLAB 也是）
            m.add_command(label=tr("顏色…"), command=self.edit_color)
            subw = tk.Menu(m, tearoff=0)                              # MATLAB 線條選單：Line Width 0.5、1.0 … 12.0（固定選項）
            for lw in LINE_WIDTHS:
                subw.add_command(label=f"{lw:.1f}", command=lambda lw=lw: self.set_linewidth(float(lw)))
            subw.add_separator()
            subw.add_command(label=tr("自訂…"), command=self.edit_linewidth)
            m.add_cascade(label=tr("線寬"), menu=subw)
            sub = tk.Menu(m, tearoff=0)
            for ls in LINESTYLES:
                sub.add_command(label=LINESTYLE_NAMES.get(ls, ls), command=lambda ls=ls: self.set_linestyle(ls))
            m.add_cascade(label=tr("線型"), menu=sub)
            sub2 = tk.Menu(m, tearoff=0)
            for mk in MARKERS:
                sub2.add_command(label=MARKER_NAMES.get(mk, mk), command=lambda mk=mk: self.set_marker(mk))
            m.add_cascade(label=tr("標記"), menu=sub2)
            subs = tk.Menu(m, tearoff=0)                              # MATLAB 線條選單：Marker Size 2 4 5 6 7 8 10 12 18 24 48
            for ms in MARKER_SIZES:
                subs.add_command(label=f"{ms:d}", command=lambda ms=ms: self.set_markersize(float(ms)))
            subs.add_separator()
            subs.add_command(label=tr("自訂…"), command=self.edit_markersize)
            m.add_cascade(label=tr("標記大小"), menu=subs)
            m.add_command(label=tr("顯示／隱藏"), command=lambda: self.toggle_visible(set(self.selected)))
            sub3 = tk.Menu(m, tearoff=0)
            sub3.add_command(label=tr("左軸"), command=lambda: self.set_yaxis(set(self.selected), "left"))
            sub3.add_command(label=tr("右軸"), command=lambda: self.set_yaxis(set(self.selected), "right"))
            m.add_cascade(label=tr("Y 軸"), menu=sub3)
            m.add_command(label=tr("改名…"), command=self.edit_label)
            m.add_command(label=tr("x 位移…"), command=lambda: self.edit_shift("x"))
            m.add_command(label=tr("y 位移…"), command=lambda: self.edit_shift("y"))
            m.add_command(label=tr("重設樣式"), command=self.reset_style)
            m.add_command(label=tr("刪除"), command=self.delete_selected)
            m.add_separator()
        items = self.ia.menu_items(hit, event) if hit.kind != "list" else []
        if items:
            fill_menu(m, items)
            m.add_separator()
        m.add_command(label=undo_label(self.undo_stack), command=self.undo, state="normal" if self.undo_stack.can_undo else "disabled")
        m.add_command(label=redo_label(self.undo_stack), command=self.redo, state="normal" if self.undo_stack.can_redo else "disabled")
        m.add_separator()
        m.add_command(label=tr("複製 (Ctrl+C)"), command=self.copy_selected)
        m.add_command(label=tr("貼上 (Ctrl+V)"), command=self.paste)
        m.add_command(label=tr("複製到新視窗"), command=self.copy_to_new_window)
        m.add_separator()
        m.add_command(label=tr("複製圖片到剪貼簿"), command=self.copy_image_to_clipboard)
        m.add_command(label=tr("複製向量圖（PDF）到剪貼簿"), command=self.copy_vector_to_clipboard, state=_clip.vector_copy_state())
        popup_menu(m, int(x_root), int(y_root))  # 0.9.13 W1：彈出後銷毀（Windows 的選單代號有限）


# --- FigureWindow ---------------------------------------------------------------------
class FigureWindow(tk.Toplevel):
    """獨立視窗：選單列＋PlotCanvas。pk.figure() 回傳的就是它。"""

    _count = 0

    def __init__(self, master=None, *, title: Optional[str] = None, style=None, state: Optional[FigureState] = None,
                 series: Optional[Sequence[Series]] = None, size: Tuple[float, float] = (8.0, 5.0), dpi: int = 100,
                 on_close: Optional[Callable[[], None]] = None, wheel_axis: str = "both"):
        root = master if master is not None else ensure_root()
        super().__init__(root)
        th = T.ensure(root)
        try:
            self.configure(background=th["bg"])
        except Exception:
            pass
        FigureWindow._count += 1
        self.title(title or tr("圖 {n}").format(n=FigureWindow._count))
        self.geometry("%dx%d" % T.window_size(self, int(size[0] * dpi) + 300, int(size[1] * dpi) + 190))   # Windows 高 DPI（W10）照 DPI 放大
        self._on_close_cb = on_close
        self.pc = PlotCanvas(self, state=state, style=style, size=size, dpi=dpi, wheel_axis=wheel_axis)
        self._build_menu()
        self.strip = self._build_strip()
        self.strip.pack(side="top", fill="x")
        self.pc._update_undo_ui()                   # 選單、工具列分頁的復原／重做也登記好了：一起同步
        self.pc.pack(fill="both", expand=True)
        self._fit_width(int(size[0] * dpi) + 300, int(size[1] * dpi) + 190)   # 英文標籤比中文長，工具列按鈕會被切掉
        bind_shortcuts(self, self.pc, close=self.close)     # 含 Ctrl／⌘＋W 關閉（MATLAB 圖形視窗 File > Close）
        self.bind("<FocusIn>", lambda e: _set_active(self))
        self.protocol("WM_DELETE_WINDOW", self.close)
        _WINDOWS.append(self)
        _set_active(self)
        if series:
            self.pc.add_series([s.copy(uid=0) for s in series], select=True)

    def _fit_width(self, w0: int, h0: int) -> None:
        """工具列需要的寬度超過預設寬（例如英文介面）時把視窗加寬，最多到螢幕寬的 95%。"""
        try:
            self.update_idletasks()
            need = max([t.winfo_reqwidth() for t in self.strip.tabs.values()] + [self.strip.winfo_reqwidth()]) + 8
            if T.NARROW_LAYOUT:                      # Windows 高 DPI（W10）：照 DPI 放大、最多工作區的 95%；還放不下由工具列自己捲動
                ww, hh = T.window_size(self, w0, h0)
                if need > ww:
                    l_, _t, r_, _b = T.work_area(self)
                    self.geometry(f"{min(need, int((r_ - l_) * 0.95))}x{hh}")
                return
            if need > w0:
                self.geometry(f"{min(need, int(self.winfo_screenwidth() * 0.95))}x{h0}")
        except Exception:
            pass

    def _build_menu(self) -> None:
        pc = self.pc
        bar = tk.Menu(self)
        f = tk.Menu(bar, tearoff=0)
        f.add_command(label=tr("開啟 JSON…"), command=pc.open_json_dialog)
        f.add_command(label=tr("另存 JSON…  (Ctrl+S)"), command=pc.save_json_dialog)
        f.add_command(label=tr("存成圖檔…"), command=pc.savefig_dialog)
        f.add_command(label=tr("複製圖片到剪貼簿"), command=pc.copy_image_to_clipboard)
        f.add_command(label=tr("複製向量圖（PDF）到剪貼簿"), command=pc.copy_vector_to_clipboard, state=_clip.vector_copy_state())
        f.add_separator()
        f.add_command(label=tr("新視窗"), command=lambda: FigureWindow(None, style=None if pc._style_follows_theme else pc.state.style))
        f.add_command(label=tr("關閉  (Ctrl+W)"), command=self.close)
        bar.add_cascade(label=tr("檔案"), menu=f)
        e = tk.Menu(bar, tearoff=0)
        e.add_command(label=tr("復原  (Ctrl+Z)"), command=pc.undo)
        e.add_command(label=tr("重做  (Ctrl+Y)"), command=pc.redo)
        pc._undo_menus.append((e, 0, 1, "Ctrl+Z", "Ctrl+Y"))     # 標籤跟著寫「復原：<動作>」
        e.add_separator()
        e.add_command(label=tr("複製  (Ctrl+C)"), command=pc.copy_selected)
        e.add_command(label=tr("貼上  (Ctrl+V)"), command=pc.paste)
        e.add_command(label=tr("複製到新視窗"), command=pc.copy_to_new_window)
        e.add_command(label=tr("全選  (Ctrl+A)"), command=pc.select_all)
        e.add_command(label=tr("刪除  (Delete)"), command=pc.delete_selected)
        bar.add_cascade(label=tr("編輯"), menu=e)
        v = tk.Menu(bar, tearoff=0)
        v.add_checkbutton(label="Grid", variable=pc.v_grid, command=lambda: pc.set_grid(pc.v_grid.get()))
        v.add_checkbutton(label="Legend", variable=pc.v_legend, command=lambda: pc.set_legend(pc.v_legend.get()))
        v.add_checkbutton(label=tr("資料提示模式"), variable=pc.v_tips, command=pc._on_tips_toggle)
        v.add_command(label=tr("匯出資料提示…"), command=pc.ia.export_tips_dialog)
        v.add_command(label=tr("複製資料提示（TSV）"), command=pc.ia.copy_tips)
        v.add_command(label=tr("提示內容…"), command=pc.ia.tip_fields_dialog)
        v.add_command(label=tr("還原視圖  (Home)"), command=pc.restore_view)
        sub = tk.Menu(v, tearoff=0)
        for name in STYLES:
            sub.add_command(label=name, command=lambda n=name: pc.set_style(n))
        v.add_cascade(label=tr("風格"), menu=sub)
        v.add_separator()
        v.add_command(label=tr("標題…"), command=lambda: self._ask_set(tr("標題"), pc.state.title, pc.set_title))
        v.add_command(label=tr("x 標籤…"), command=lambda: self._ask_set(tr("x 標籤"), pc.state.xlabel, pc.set_xlabel))
        v.add_command(label=tr("y 標籤…"), command=lambda: self._ask_set(tr("y 標籤"), pc.state.ylabel, pc.set_ylabel))
        v.add_command(label=tr("右 y 標籤…"), command=lambda: self._ask_set(tr("右 y 標籤"), pc.state.ylabel_right,
                                                                          lambda s: pc.set_ylabel(s, "right")))
        bar.add_cascade(label=tr("檢視"), menu=v)
        i = tk.Menu(bar, tearoff=0)
        i.add_command(label=tr("垂直參考線…"), command=lambda: self._ask_line("xline"))
        i.add_command(label=tr("水平參考線…"), command=lambda: self._ask_line("yline"))
        i.add_command(label=tr("文字…"), command=self._ask_text)
        bar.add_cascade(label=tr("插入"), menu=i)
        self.config(menu=bar)

    def _build_strip(self) -> T.Toolstrip:
        """MATLAB 圖形視窗那條藍色工具列：FIGURE 分頁＋右側快速存取。"""
        pc = self.pc
        strip = T.Toolstrip(self)
        tab = strip.add_tab(tr("圖"), "figure", contextual=True)        # MATLAB 圖形視窗的 FIGURE 是 contextual tab（藍）
        s = tab.section(tr("檔案"))
        s.button(tr("開啟 JSON"), icon="open", command=pc.open_json_dialog, big=True, tip=tr("開啟 plotkit 圖檔（.json）"))
        s.button(tr("另存 JSON"), icon="save", command=pc.save_json_dialog, big=True, tip=tr("存成 plotkit 圖檔（Ctrl+S）"))
        col = s.column()
        s.button(tr("存成圖檔…"), icon="export", command=pc.savefig_dialog, col=col,
                 tip=tr("存成 PNG／JPEG／TIFF／PDF／EPS／SVG…：可選 DPI、背景、寬高"))
        s.button(tr("複製圖片"), icon="clipboard", command=pc.copy_image_to_clipboard, col=col, tip=tr("複製到系統剪貼簿"))
        s.button(tr("新視窗"), icon="new_window", command=lambda: FigureWindow(None, style=None if pc._style_follows_theme else pc.state.style), col=col)
        col = s.column()
        s.button(tr("複製向量圖"), icon="export", command=pc.copy_vector_to_clipboard, col=col, state=_clip.vector_copy_state(),
                 tip=_clip.vector_copy_tip(tr("PDF 放進系統剪貼簿（MATLAB 座標區工具列的 Copy as vector graphic）")))
        s = tab.section(tr("編輯"))
        col = s.column()
        pc._undo_extra.append(s.button(tr("復原"), icon="undo", command=pc.undo, col=col, tip="Ctrl+Z"))
        pc._redo_extra.append(s.button(tr("重做"), icon="redo", command=pc.redo, col=col, tip="Ctrl+Y"))
        s.button(tr("全選"), icon="select_all", command=pc.select_all, col=col, tip="Ctrl+A")
        col = s.column()
        s.button(tr("複製訊號"), icon="copy", command=pc.copy_selected, col=col, tip="Ctrl+C")
        s.button(tr("貼上"), icon="paste", command=pc.paste, col=col, tip="Ctrl+V")
        s.button(tr("刪除"), icon="remove", command=pc.delete_selected, col=col, tip="Delete")
        s.button(tr("複製到新視窗"), icon="copy_window", command=pc.copy_to_new_window, big=True)
        s = tab.section(tr("檢視"))
        s.toggle(tr("資料提示"), pc.v_tips, icon="datatip", command=pc._on_tips_toggle, big=True)
        s.button(tr("還原視圖"), icon="fit", command=pc.restore_view, big=True, tip=tr("Home／雙擊空白"))
        col = s.column()
        s.toggle(tr("格線"), pc.v_grid, icon="grid", command=lambda: pc.set_grid(pc.v_grid.get()), col=col)
        s.toggle(tr("圖例"), pc.v_legend, icon="legend", command=lambda: pc.set_legend(pc.v_legend.get()), col=col)
        s.button(tr("標題／標籤…"), icon="text", command=self._ask_labels, col=col)
        col = s.column()
        s.button(tr("匯出提示…"), icon="tip_export", command=pc.ia.export_tips_dialog, col=col,
                 tip=tr("把全部資料提示（訊號、panel、樣本索引、x、y）存成 TXT（Tab 分隔）或 CSV；右鍵提示框也有「複製資料提示（TSV）」"))
        s.button(tr("提示內容…"), icon="tip_fields", command=pc.ia.tip_fields_dialog, col=col,
                 tip=tr("選資料提示要顯示哪些列：名稱、X、Y、樣本索引、Panel（套用到全部提示，存進圖檔）"))
        s = tab.section(tr("插入"))
        s.button(tr("垂直線"), icon="xline", command=lambda: self._ask_line("xline"), big=True)
        s.button(tr("水平線"), icon="yline", command=lambda: self._ask_line("yline"), big=True)
        s.button(tr("文字"), icon="text", command=self._ask_text, big=True)
        strip.qab_button("save", tr("另存 JSON (Ctrl+S)"), pc.save_json_dialog)
        strip.qab_button("undo", tr("復原 (Ctrl+Z)"), pc.undo)
        strip.qab_button("redo", tr("重做 (Ctrl+Y)"), pc.redo)
        return strip

    def _ask_labels(self) -> None:
        pc = self.pc
        self._ask_set(tr("標題"), pc.state.title, pc.set_title)
        self._ask_set(tr("x 標籤"), pc.state.xlabel, pc.set_xlabel)
        self._ask_set(tr("y 標籤"), pc.state.ylabel, pc.set_ylabel)

    def _ask_set(self, title: str, cur: str, setter: Callable[[str], None]) -> None:
        v = D.ask_string(self, title, tr("{title}：").format(title=title), cur or "")
        if v is not None:
            setter(v)

    def _ask_line(self, kind: str) -> None:
        v = D.ask_float(self, tr("參考線"), tr("x 位置：") if kind == "xline" else tr("y 位置："), 0.0)
        if v is None:
            return
        t = D.ask_string(self, tr("參考線"), tr("標籤（可空白）："), "") or ""
        if kind == "xline":
            self.pc.insert_xline_at(v, t)
        else:
            self.pc.insert_yline_at(v, t)

    def _ask_text(self) -> None:
        ax = self.pc.info.ax_left
        if ax is None:
            return
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        self.pc.insert_text_at((x0 + x1) / 2, (y0 + y1) / 2)

    # --- 轉送 API ----------------------------------------------------------------------
    @property
    def state(self) -> FigureState:
        return self.pc.state

    @property
    def fig(self):
        return self.pc.fig

    @property
    def ax(self):
        return self.pc.info.ax_left

    @property
    def canvas(self):
        return self.pc.canvas

    @property
    def plot_canvas(self) -> PlotCanvas:
        return self.pc

    def plot(self, x, y=None, *args, **kw) -> Series:
        return self.pc.plot(x, y, *args, **kw)

    def step(self, x, y, *args, **kw) -> Series:
        return self.pc.step(x, y, *args, **kw)

    def add_series(self, series: Iterable[Series], **kw) -> List[Series]:
        return self.pc.add_series(series, **kw)

    def series(self) -> List[Series]:
        return self.pc.series()

    def xline(self, x: float, text: str = "", **kw) -> Annotation:
        return self.pc.insert_xline_at(x, text, **kw)

    def yline(self, y: float, text: str = "", side: str = "left", **kw) -> Annotation:
        return self.pc.insert_yline_at(y, text, axes_key=side, **kw)

    def text(self, x: float, y: float, s: str, side: str = "left", **kw) -> Optional[Annotation]:
        return self.pc.insert_text_at(x, y, s, axes_key=side, **kw)

    def xlabel(self, s: str) -> None:
        self.pc.set_xlabel(s)

    def ylabel(self, s: str, side: str = "left") -> None:
        self.pc.set_ylabel(s, side)

    def title_text(self, s: str) -> None:
        """圖的標題（.title() 是 Tk 視窗標題，別搞混）。"""
        self.pc.set_title(s)

    set_title = title_text

    def xlim(self, a=None, b=None):
        """xlim() 讀目前範圍；xlim(a, b) 或 xlim((a, b)) 設定；xlim("auto") 回自動範圍。"""
        if a is None and b is None:
            return tuple(self.pc.state.view.get("xlim") or self.ax.get_xlim())
        if a == "auto":
            self.pc.set_xlim(None, None)
            return None
        self.pc.set_xlim(a, b)

    def ylim(self, a=None, b=None, side: str = "left"):
        if a is None and b is None:
            key = "ylim_right" if side == "right" else "ylim"
            return tuple(self.pc.state.view.get(key) or (self.pc.info.axes_for(side) or self.ax).get_ylim())
        if a == "auto":
            self.pc.set_ylim(None, None, side)
            return None
        self.pc.set_ylim(a, b, side)

    def restore_view(self) -> None:
        self.pc.restore_view()

    def undo(self) -> None:
        self.pc.undo()

    def redo(self) -> None:
        self.pc.redo()

    def grid(self, on: bool = True) -> None:
        self.pc.set_grid(on)

    def legend(self, on: bool = True, loc: Optional[str] = None) -> None:
        self.pc.set_legend(on, loc)

    def set_style(self, spec) -> None:
        self.pc.set_style(spec)

    def save_json(self, path: str) -> None:
        self.pc.save_json(path)

    def load_json(self, path: str) -> None:
        self.pc.load_json(path)

    def savefig(self, path: str, dpi: Optional[int] = None) -> None:
        self.pc.savefig(path, dpi)

    def copy_to_clipboard(self) -> Tuple[bool, str]:
        return self.pc.copy_image_to_clipboard()

    def to_png_bytes(self) -> bytes:
        return self.pc.png_bytes()

    def close(self) -> None:
        _unregister(self)
        if self._on_close_cb:
            try:
                self._on_close_cb()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        if _OWN_ROOT and _IN_SHOW and not windows() and _ROOT is not None:
            try:
                _ROOT.quit()
            except Exception:
                pass
