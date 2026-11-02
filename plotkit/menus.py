# -*- coding: utf-8 -*-
"""彈出選單（右鍵選單、工具列按鈕的下拉）：彈出之後把它銷毀（0.9.13 W1，2026-10-28 Windows 相容性檢查）。

每次右鍵都是新建的 tk.Menu（含子選單）。0.9.12 以前從不銷毀：macOS 只是多佔一點記憶體；Windows 的 Tk 選單代號是 16 位元，
每次右鍵約 12 個選單（44 項＋子選單），開到第 430 次左右就用完——TclError「No more menus can be allocated」，之後任何選單
（連 1 項的新選單）都開不了，只能重開程式（verify_win_0912.md W1）。
Windows 與 macOS 的 tk_popup 都等使用者點掉（或選了項目）才回來：Windows 的 TrackPopupMenu 是模態的、WM_COMMAND 在它回來前（或回來後
的下一個事件）送到；macOS 的 popUpMenuPositioningItem 也是模態的。所以 tk_popup 回來後再排程 POPUP_MENU_RELEASE_MS 毫秒銷毀就安全：
選了的項目的命令已經跑完（命令開了模態對話框時計時器會在對話框的事件迴圈裡到期，Tk 對正在跑命令的選單有 Tcl_Preserve 保護）。
X11 的 tk_popup 立刻回來、選單還開著，改在 <Unmap>（收起）時再排程銷毀。
POPUP_MENU_RELEASE_MS＝None 時不銷毀（＝0.9.12 的行為；測試用：測試把 tk.Menu.tk_popup 換成只記錄的假函式，之後還要讀選單內容、invoke）。
"""
from __future__ import annotations

from typing import Optional

from .dialogs import HAVE_TK, tk

POPUP_MENU_RELEASE_MS: Optional[int] = 1000   # 彈出選單收起後多久銷毀（ms）；None＝不銷毀
_RECENT: list = []                            # 最近彈過、計時器還沒到的選單：下一次彈出時先銷毀（同一時間最多一個右鍵的量）
_TIMERS: dict = {}                            # id(選單) → (root, after id)：銷毀計時器（掛在 root 上；提早銷毀時取消）


def popup_menu(m, x, y) -> None:
    """彈出 m（tk_popup）、放掉 grab，之後照上面的規則把 m（連同它的子選單）銷毀。呼叫端不要再用 m。
    彈出之前先把上一個彈過的選單銷毀（它一定已經收起：Windows／macOS 的 tk_popup 是模態的，使用者點掉才回得來）——短時間內連續右鍵也不會
    累積到計時器到期之前（沒有桌面的 Windows 工作階段桌面堆很小，2026-10-28 實測 164 次連點就用完）。"""
    ms = POPUP_MENU_RELEASE_MS
    ws = ""
    if ms is not None:
        release_recent(keep=m)
        _RECENT.append(m)
        try:
            ws = str(m.tk.call("tk", "windowingsystem"))
        except Exception:
            ws = ""
        if ws == "x11":
            try:
                m.bind("<Unmap>", lambda e, m=m, ms=ms: _destroy_later(m, ms), add="+")
            except Exception:
                pass
    try:
        m.tk_popup(int(x), int(y))
    finally:
        try:
            m.grab_release()
        except Exception:
            pass
        if ms is not None and ws != "x11":
            _destroy_later(m, ms)


def _destroy_later(m, ms) -> None:
    """ms 毫秒後銷毀 m。計時器掛在主視窗（root）上、不掛在選單自己身上：選單是分析視窗（眼圖、錯誤率比對、AM/PM/FM、頻譜…）的子元件，
    視窗在計時器到期前關掉時，Tkinter 會把掛在選單上的回呼命令一起刪掉、Tcl 的 after 事件還在，到期時留下「invalid command name」的
    Tk 背景錯誤（2026-10-29 第一輪回歸驗證：0.9.12 的 s38「關眼圖視窗沒有 Tk 背景錯誤」在 0.9.13 失敗）。到期時選單已經不在就什麼都不做
    （_destroy_quiet 先看 winfo_exists）；提早銷毀（release_recent、下一次彈出）時把計時器取消。"""
    try:
        root = m._root()
        aid = root.after(max(1, int(ms)), lambda m=m: _destroy_quiet(m))
    except Exception:
        return
    _TIMERS[id(m)] = (root, aid)


def _destroy_quiet(m) -> None:
    root, aid = _TIMERS.pop(id(m), (None, None))
    if root is not None and aid is not None:
        try:
            root.after_cancel(aid)                    # 計時器還沒到（提早銷毀）：取消，不留排著的事件；已經在跑的（就是它叫我們）取消也無害
        except Exception:
            pass
    try:
        if m.winfo_exists():
            m.destroy()
    except Exception:
        pass
    while m in _RECENT:
        _RECENT.remove(m)


def release_recent(keep=None) -> int:
    """把最近彈過（還沒被計時器銷毀）的選單現在就銷毀（keep＝這一個不動）。回傳銷毀的個數。"""
    n = 0
    for old in list(_RECENT):
        if old is not keep:
            _destroy_quiet(old)
            n += 1
    return n


def live_menus(widget) -> int:
    """widget 底下（含自己）現在還活著的 tk.Menu 個數（測試、診斷用：右鍵之後應該不會越來越多）。"""
    if not HAVE_TK:
        return 0
    n = 0
    stack = [widget]
    while stack:
        w = stack.pop()
        try:
            if isinstance(w, tk.Menu):
                n += 1
            stack.extend(w.winfo_children())
        except Exception:
            pass
    return n
