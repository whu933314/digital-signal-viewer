# -*- coding: utf-8 -*-
"""python -m plotkit --selftest | --demo | <file.json> [...]"""
from __future__ import annotations

import sys

from .i18n import tr


def demo() -> int:
    import numpy as np
    import plotkit as pk
    t = np.linspace(0.0, 1e-3, 2001)
    w = pk.figure(title=tr("plotkit 示範（滾輪縮放、拖曳平移、資料提示、右鍵選單）"), style="matlab")
    w.plot(t * 1e6, np.sin(2 * np.pi * 5e3 * t), label="I")
    w.plot(t * 1e6, np.cos(2 * np.pi * 5e3 * t), label="Q", ls="--")
    w.step(np.arange(0, 1000, 50.0), (np.arange(20) % 2).astype(float), label="clk", yaxis="right", color="#3baa32")
    w.xlabel("t [us]")
    w.ylabel("amplitude")
    w.ylabel("level", side="right")
    w.xline(250, "sync")
    w.text(600, 0.8, tr("注意這裡"))
    pk.show()
    return 0


def _safe_stdio() -> None:
    """stdout 是管線／檔案時 Windows 會用 cp950，中文與 ≈ 之類的字會丟 UnicodeEncodeError：改成不丟錯。"""
    for s in (sys.stdout, sys.stderr):
        if s is not None and hasattr(s, "reconfigure"):
            try:
                s.reconfigure(errors="backslashreplace")
            except Exception:
                pass


def _pop_lang(argv) -> None:
    """--lang xx／--lang=xx ＞ 環境變數 PLOTKIT_LANG ＞ DSV_LANG；沒指定就是預設（中文）。"""
    import os
    from .i18n import set_language
    lang = os.environ.get("PLOTKIT_LANG") or os.environ.get("DSV_LANG")
    for i, a in enumerate(list(argv)):
        if a.startswith("--lang="):
            lang = a.split("=", 1)[1]
            argv.remove(a)
            break
        if a == "--lang" and i + 1 < len(argv):
            lang = argv[i + 1]
            del argv[i:i + 2]
            break
    if lang:
        set_language(lang)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _safe_stdio()
    if "--selftest" in argv:                      # selftest 用中文字串比對：不吃 --lang／DSV_LANG
        from .i18n import set_language
        set_language("zh")
        from .selftest import selftest
        return 0 if selftest() else 1
    _pop_lang(argv)
    paths = [a for a in argv if not a.startswith("-")]
    if "--demo" in argv or paths:
        # 要開圖的視窗：Windows 先宣告高 DPI（和 DSV 一樣：2026-10-30 使用者決定；沒宣告時 125% 以上整個視窗被點陣放大、字是糊的），
        # 要在建第一個 Tk 視窗之前；macOS、Linux 什麼都不做
        from .theme import enable_windows_dpi_awareness
        enable_windows_dpi_awareness()
    if "--demo" in argv:
        return demo()
    if paths:
        import plotkit as pk
        opened = 0
        for p in paths:
            try:
                pk.open_json(p)
                opened += 1
            except Exception as e:                     # 不存在／不是 plotkit 的 JSON：說明哪個檔、為什麼，其餘照開
                print(tr("開啟失敗：{err}").format(err=f"{p}: {type(e).__name__}: {e}"), file=sys.stderr)
        if not opened:
            return 1
        pk.show()
        return 0
    print(tr("用法：python -m plotkit --selftest | --demo | <圖.json> [...]"))
    return 2


if __name__ == "__main__":
    sys.exit(main())
