# -*- coding: utf-8 -*-
"""plotkit.undo — 快照式 Undo／Redo 堆疊。

每次改動前把「改動前的狀態」push 進來；undo 時給它「現在的狀態」，它回傳要還原成的狀態並把現在的放進 redo。
同一個 tag 在 coalesce_window 秒內的連續 push 會合併（滑桿、拖曳），避免一次拖曳產生幾十筆。
"""
from __future__ import annotations

import time
from typing import Any, List, Optional, Sequence, Tuple

from .i18n import tr


class UndoStack:
    def __init__(self, limit: int = 100):
        self.limit = int(max(1, limit))
        self._undo: List[dict] = []     # 每筆 {"state", "desc", "tag", "t"}
        self._redo: List[dict] = []

    def __len__(self) -> int:
        return len(self._undo)

    @property
    def last_tag(self) -> Optional[str]:
        return self._undo[-1]["tag"] if self._undo else None

    @property
    def last_time(self) -> float:
        return self._undo[-1]["t"] if self._undo else 0.0

    def push(self, state: Any, desc: str = "", tag: Optional[str] = None, coalesce_window: float = 2.0,
             now: Optional[float] = None) -> bool:
        """放入改動前的狀態。同 tag 在時間窗內會合併（不 push），回傳是否真的放入。"""
        now = time.time() if now is None else now
        if tag and self._undo and self._undo[-1]["tag"] == tag and now - self._undo[-1]["t"] < coalesce_window:
            self._undo[-1]["t"] = now
            self._redo.clear()
            return False
        self._undo.append({"state": state, "desc": desc, "tag": tag, "t": now})
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        self._redo.clear()
        return True

    def undo(self, current: Any) -> Optional[Any]:
        if not self._undo:
            return None
        entry = self._undo.pop()
        self._redo.append({"state": current, "desc": entry["desc"], "tag": None, "t": time.time()})
        return entry["state"]

    def redo(self, current: Any) -> Optional[Any]:
        if not self._redo:
            return None
        entry = self._redo.pop()
        self._undo.append({"state": current, "desc": entry["desc"], "tag": None, "t": time.time()})
        return entry["state"]

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def peek_desc(self) -> str:
        return self._undo[-1]["desc"] if self._undo else ""

    def peek_redo_desc(self) -> str:
        return self._redo[-1]["desc"] if self._redo else ""

    def discard_last(self) -> bool:
        """拿掉最後一筆（例如拖曳被 Esc 取消時）。"""
        if not self._undo:
            return False
        self._undo.pop()
        return True

    def states(self) -> List[Any]:
        """堆疊裡全部的狀態（復原的在前、重做的在後）：宿主要知道快照還用到哪些外部資源（例如 DSV 的凍結資料檔）時用。"""
        return [e["state"] for e in self._undo] + [e["state"] for e in self._redo]

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()


# --- 介面文字：MATLAB 的 Edit 選單寫「Undo: Pan」（MATLAB 介面顯示的格式「Undo: {0}」）-------------------------
def undo_label(stack: UndoStack) -> str:
    """「復原：<動作>」；沒有可復原的動作＝「復原」（選單／按鈕同時停用）。"""
    d = stack.peek_desc()
    return tr("復原：{desc}").format(desc=d) if d else tr("復原")


def redo_label(stack: UndoStack) -> str:
    d = stack.peek_redo_desc()
    return tr("重做：{desc}").format(desc=d) if d else tr("重做")


def _with_accel(text: str, accel: str) -> str:
    return f"{text} ({accel})" if accel else text


def set_tip(widget, text: str) -> None:
    """改 plotkit.theme.tooltip 掛的提示文字（沒掛過就掛一個）。"""
    tip = getattr(widget, "_tooltip", None)
    if tip is not None:
        tip.text = text
        try:
            widget._pk_tip = text
        except Exception:
            pass
        return
    try:
        from .theme import tooltip
        tooltip(widget, text)
    except Exception:
        pass


def sync_undo_ui(stack: UndoStack, undo_widgets: Sequence = (), redo_widgets: Sequence = (),
                 accel: Tuple[str, str] = ("", ""), menus: Sequence = ()) -> Tuple[str, str]:
    """按鈕：依堆疊啟用／停用，提示改成「復原：<動作> (快速鍵)」；menus＝[(tk.Menu, 復原項 index, 重做項 index)]：
    標籤改成「復原：<動作>」並同步停用。回傳 (復原文字, 重做文字)。"""
    u, r = undo_label(stack), redo_label(stack)
    for widgets, ok, text, acc in ((undo_widgets, stack.can_undo, u, accel[0]), (redo_widgets, stack.can_redo, r, accel[1])):
        for w in widgets:
            try:
                w.state(["!disabled"] if ok else ["disabled"])
            except Exception:
                pass
            set_tip(w, _with_accel(text, acc))
    for item in menus:
        m, iu, ir = item[0], item[1], item[2]
        acc_u = item[3] if len(item) > 3 else ""
        acc_r = item[4] if len(item) > 4 else ""
        for idx, ok, text, acc in ((iu, stack.can_undo, u, acc_u), (ir, stack.can_redo, r, acc_r)):
            try:
                m.entryconfigure(idx, label=(f"{text}  ({acc})" if acc else text), state="normal" if ok else "disabled")
            except Exception:
                pass
    return u, r
