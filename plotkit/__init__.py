# -*- coding: utf-8 -*-
"""plotkit — 像 pyplot 一樣用的互動繪圖套件（tkinter + numpy + matplotlib）。

    import plotkit as pk
    w = pk.figure(title="demo", style="matlab")
    w.plot(x, y, label="I")
    w.step(n, bits, label="clk", yaxis="right")
    w.xline(250, "sync"); w.text(600, 0.8, "注意")
    w.save_json("demo.json")
    pk.show()

互動（照 MATLAB R2025a）：點線條釘資料提示（可拖、Delete 刪；「資料提示」預設開、可關）、Shift＋點選取（多選）、
右鍵選單（顏色／線寬／線型／標記／顯示隱藏／左右軸／改名／位移）、雙擊圖例文字改名、
滾輪縮放（Shift 只縮 x、Ctrl 只縮 y）、左鍵拖曳平移、雙擊空白或 Home 還原、插入參考線與文字、Ctrl+Z／Y 復原重做、
Ctrl+C／V 跨視窗複製貼上、JSON 存讀、複製圖片到系統剪貼簿。沒有 tkinter 時仍可 import（無 GUI 功能）。
"""
from __future__ import annotations

__version__ = "0.2.0"

from .i18n import set_language, get_language, tr  # noqa: E402  （i18n 不依賴任何東西；下面的 ImportError 訊息要用）

import matplotlib as _mpl  # noqa: E402

_v = tuple(int(p) for p in _mpl.__version__.split(".")[:2] if p.isdigit())
if _v < (3, 7):
    raise ImportError(tr("plotkit 需要 matplotlib 3.7 以上，目前是 {version}").format(version=_mpl.__version__))

from . import clipboard, cursors, dialogs, draw, i18n, icons, interact, keys, lod, menus, model, styles, theme, undo, widgets  # noqa: E402,F401
from .clipboard import clipboard_command_for, copy_figure_to_clipboard, copy_png_to_clipboard, figure_to_png_bytes  # noqa: E402
from .dialogs import HAVE_TK  # noqa: E402
from .draw import (DEFAULT_TIP_FIELDS, TIP_FIELDS, RenderInfo, apply_style, axes_at, data_coords, draw_annotation,  # noqa: E402
                   draw_state, draw_tip, format_tip_fields, format_tip_text, hit_test_lines, nearest_index, pan_limits,
                   parse_tip_fields, view_of, wheel_notches, zoom_limits)
from .cursors import CURSOR_MODES, DataCursors  # noqa: E402
from .interact import Hit, Interactor, InteractorHost, InteractorModel  # noqa: E402
from .model import (CLIPBOARD, Annotation, DataTip, FigureState, Series, decode_array, encode_array,  # noqa: E402
                    from_dsv_snapshot, load_json, save_json, state_from_dict, state_to_dict)
from .styles import FONT_CJK, LINE_WIDTHS, LINESTYLES, MARKER_SIZES, MARKERS, STYLES, auto_color, get_style, resolve_fonts  # noqa: E402
from .undo import UndoStack  # noqa: E402
from .widgets import FigureWindow, PlotCanvas, active_window, close_all, ensure_root, show, windows  # noqa: E402

# 一次性 rc：中文 fallback 字型與負號（和 DSV 相同；風格本身不改 rcParams）
try:
    _mpl.rcParams["font.family"] = "sans-serif"
    _mpl.rcParams["font.sans-serif"] = resolve_fonts(["Microsoft JhengHei", "Microsoft YaHei", "PingFang TC", "Heiti TC",
                                                      "Noto Sans CJK TC", "Noto Sans TC", "Arial Unicode MS", "Arial", "Helvetica"])
    _mpl.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


def figure(title=None, *, style=None, size=(8.0, 5.0), dpi=100, master=None, wheel_axis="both") -> FigureWindow:
    """開一個互動圖視窗（沒有 Tk 根視窗時自動建立隱藏的根視窗；最後呼叫 pk.show()）。"""
    return FigureWindow(master, title=title, style=style, size=size, dpi=dpi, wheel_axis=wheel_axis)


def open_json(path: str, *, master=None, title=None) -> FigureWindow:
    """重開用 save_json 存的圖。"""
    import os
    st = load_json(path)
    return FigureWindow(master, title=title or os.path.basename(path), state=st)


__all__ = [
    "__version__", "HAVE_TK", "CLIPBOARD", "Series", "Annotation", "DataTip", "FigureState",
    "encode_array", "decode_array", "from_dsv_snapshot", "save_json", "load_json", "state_to_dict", "state_from_dict",
    "STYLES", "get_style", "resolve_fonts", "auto_color", "FONT_CJK", "LINESTYLES", "MARKERS", "LINE_WIDTHS", "MARKER_SIZES",
    "RenderInfo", "draw_state", "apply_style", "draw_annotation", "draw_tip", "format_tip_text", "view_of",
    "TIP_FIELDS", "DEFAULT_TIP_FIELDS", "parse_tip_fields", "format_tip_fields", "DataCursors", "CURSOR_MODES",
    "hit_test_lines", "nearest_index", "axes_at", "data_coords", "zoom_limits", "pan_limits", "wheel_notches",
    "UndoStack", "Interactor", "InteractorHost", "InteractorModel", "Hit",
    "copy_figure_to_clipboard", "copy_png_to_clipboard", "figure_to_png_bytes", "clipboard_command_for",
    "PlotCanvas", "FigureWindow", "figure", "open_json", "show", "windows", "active_window", "close_all", "ensure_root",
]
