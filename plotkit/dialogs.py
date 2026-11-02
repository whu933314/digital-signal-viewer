# -*- coding: utf-8 -*-
"""plotkit.dialogs — tkinter 匯入與對話框包裝。

沒有 tkinter（headless）時用 stub 物件代替，讓整個套件仍然可以 import、跑 selftest。
測試時可以整個替換：``plotkit.dialogs.messagebox = 假物件``。
"""
from __future__ import annotations

from typing import Optional

from .i18n import tr

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
    HAVE_TK = True
except Exception:  # pragma: no cover - headless 環境
    HAVE_TK = False

    class _StubWidget:
        """tkinter 不可用時的替身：可以當基底類別，但不能真的建立。"""

        def __init__(self, *args, **kwargs):
            raise RuntimeError(tr("tkinter 不可用（headless 環境），只能用 plotkit 的無 GUI 功能"))

    class _StubModule:
        def __getattr__(self, name):
            return _StubWidget

    tk = ttk = colorchooser = filedialog = messagebox = simpledialog = _StubModule()  # type: ignore


def ask_color(parent, title: str, initial: Optional[str] = None) -> Optional[str]:
    """顏色選擇器；取消回傳 None，否則 '#rrggbb'。"""
    try:
        _rgb, hexcolor = colorchooser.askcolor(color=initial or "#1f77b4", parent=parent, title=title)
    except Exception:
        return None
    return hexcolor or None


def ask_float(parent, title: str, prompt: str, initial: Optional[float] = None,
              minvalue: Optional[float] = None, maxvalue: Optional[float] = None) -> Optional[float]:
    kw = {"parent": parent}
    if initial is not None:
        kw["initialvalue"] = initial
    if minvalue is not None:
        kw["minvalue"] = minvalue
    if maxvalue is not None:
        kw["maxvalue"] = maxvalue
    return simpledialog.askfloat(title, prompt, **kw)


def ask_string(parent, title: str, prompt: str, initial: str = "") -> Optional[str]:
    return simpledialog.askstring(title, prompt, initialvalue=initial, parent=parent)


def info(parent, title: str, msg: str) -> None:
    messagebox.showinfo(title, msg, parent=parent)


def warn(parent, title: str, msg: str) -> None:
    messagebox.showwarning(title, msg, parent=parent)


def error(parent, title: str, msg: str) -> None:
    messagebox.showerror(title, msg, parent=parent)


def ask_yes_no(parent, title: str, msg: str) -> bool:
    return bool(messagebox.askyesno(title, msg, parent=parent))


def ask_save_path(parent, title: str, initialfile: str, filetypes) -> Optional[str]:
    """另存新檔對話框；取消回傳 None。副檔名照選的類型（沒打副檔名時補第一個類型的）。"""
    try:
        p = filedialog.asksaveasfilename(parent=parent, title=title, initialfile=initialfile,
                                         defaultextension=".txt", filetypes=list(filetypes))
    except Exception:
        return None
    return p or None


# 「提示內容…」的勾選項目：(欄位鍵, 顯示文字)；鍵同 draw.TIP_FIELDS
TIP_FIELD_LABELS = (("name", "名稱"), ("x", "X"), ("y", "Y"), ("index", "樣本索引（Index）"), ("panel", "Panel"))


class TipFieldsDialog(tk.Toplevel if HAVE_TK else object):
    """資料提示要顯示哪些列（R2025a 的 Modify Data Tips／DataTipTemplate.DataTipRows）：名稱、X、Y、樣本索引、Panel。
    按「確定」呼叫 on_ok(tuple)；全部取消勾選＝預設（名稱／X／Y）。不搶焦點、不設 grab。"""

    def __init__(self, parent, current, on_ok):
        top = parent.winfo_toplevel() if parent is not None else None
        super().__init__(top)
        self.title(tr("提示內容"))
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
        self.on_ok = on_ok
        cur = set(current or ())
        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=tr("資料提示要顯示的列（套用到全部提示）：")).pack(side="top", anchor="w", pady=(0, 6))
        self.vars = {}
        for key, label in TIP_FIELD_LABELS:
            v = tk.BooleanVar(value=key in cur)
            self.vars[key] = v
            ttk.Checkbutton(body, text=tr(label), variable=v).pack(side="top", anchor="w")
        bar = ttk.Frame(body)
        bar.pack(side="top", fill="x", pady=(10, 0))
        ttk.Button(bar, text=tr("取消"), command=self.destroy).pack(side="right")
        ttk.Button(bar, text=tr("確定"), command=self.ok).pack(side="right", padx=(0, 6))
        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def selected(self):
        return tuple(k for k, _l in TIP_FIELD_LABELS if self.vars[k].get())

    def ok(self):
        fields = self.selected()
        try:
            self.on_ok(fields)
        finally:
            self.destroy()
