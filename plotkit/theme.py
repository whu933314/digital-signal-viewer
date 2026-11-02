# -*- coding: utf-8 -*-
"""plotkit.theme — 照 MATLAB R2025a 量出來的介面主題（dark／light）與版面元件；1.0.0 起多六個外觀主題
（Sony 風黑銀／深藍黑、Apple 風淺色／深色／深色·石墨橘／深色·純黑綠：只換色票與圓角，版面、尺寸、字型全部沿用 MATLAB 的量測值；色票與設計理由見
audit/2026-11-01-skins/proposals.md，顏色是借品牌外觀的感覺、不是任何品牌的素材）。

數值來源與量測方法見 docs/matlab-ui-spec.md（每個顏色都對得到 MATLAB R2025a 介面的樣式值或 uifigure 的實測像素）。
程式裡不再用主題名稱判斷深淺（Theme.dark＝視窗底色的亮度），分頁列的字色、主要按鈕按下的顏色、圓角都是每個主題自己的值。

用法::

    import plotkit.theme as T
    th = T.apply(root, "dark")          # 建 ttk 主題、設字型、設 tk 傳統元件的顏色；可重複呼叫切換
    strip = T.Toolstrip(root); tab = strip.add_tab("首頁"); sec = tab.section("檔案")
    sec.button("匯入…", icon="import", command=fn, big=True)
    panel = T.Panel(root, "資料夾"); ttk.Treeview(panel.body).pack(...)
    bar = T.PlotToolbar(root, canvas)   # 取代 matplotlib 的 NavigationToolbar2Tk 外觀（功能照舊）

元件只用 tkinter／ttk 與 Pillow（matplotlib 自帶），Windows／macOS／Linux 都一樣的外觀（不跟系統主題）。
同一個 Tk interpreter 裡每個主題只建一次（Theme 物件與它的圖片活到行程結束；ttk 的圖片元素才不會失效）；
第二個 tk.Tk() 會在自己的 interpreter 再建一套。
"""
from __future__ import annotations

import sys
import weakref
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import icons as I
from .i18n import tr
from .menus import popup_menu

try:
    import tkinter as tk
    from tkinter import ttk
    import tkinter.font as tkfont
    HAVE_TK = True
except Exception:                     # pragma: no cover
    tk = ttk = tkfont = None
    HAVE_TK = False

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform.startswith("win")

# Windows 高 DPI（2026-10-29 使用者決定 W10）：程式宣告 per-monitor DPI aware 之後，175% 的直立 1080 px 螢幕只有 617 點寬，
# 視窗的寬度跟著螢幕縮（放得進螢幕），工具列的分頁列、分頁內容、分析視窗的欄位列就放不下——以前右邊的「量測／檢視／匯出」
# 分頁、「說明」區段、欄位列後半段直接被切掉、點不到。開著時：分頁列放不下就改用窄分頁鈕、還放不下就左右捲動；分頁內容比
# 工具列寬時兩端出現 ◀ ▶ 捲動鈕（滾輪也可以）；flow_row() 登記的欄位列放不下就換行。放得下的時候和以前一模一樣。
# 只在 Windows 開：macOS 的主視窗最小 1000 點寬、照舊（不受影響）。測試可以暫時打開它，在 Mac 上驗這段程式。
NARROW_LAYOUT = IS_WIN

# ---------------------------------------------------------------------------
# 色票（docs/matlab-ui-spec.md 第 1 節；鍵名 = 語意）
# ---------------------------------------------------------------------------
TOKENS: Dict[str, Dict[str, str]] = {
    "dark": {
        "bg": "#212121", "bg2": "#333333", "bg3": "#000000", "input": "#121212", "stripe": "#121212",
        "hover": "#333333", "selected": "#616161", "selected_focus": "#0b2f5c", "list_hover": "#7d7d7d",
        "toggle_on": "#000000", "toolbar_on": "#0b2f5c",
        "strip": "#004073", "strip_hover": "#268cdd", "strip_selected": "#1171be", "panel_header_sel": "#1171be",
        "qab_hover": "#0b2f5c", "qab_active": "#00243e",
        "scroll": "#616161", "scroll_hover": "#7d7d7d", "scroll_active": "#888888",
        "border": "#7d7d7d", "border2": "#616161", "border3": "#a6a6a6", "focus": "#268cdd", "border_hover": "#bfbfbf",
        "text": "#d9d9d9", "text2": "#888888", "text3": "#ffffff", "text_selected": "#e6e6e6",
        "error": "#ff7a74", "warning": "#edb120", "success": "#94ef84", "link": "#54b6ff",
        "tab": "#333333", "tab_selected": "#212121",
        "icon_fg": "#d9d9d9", "icon_fg2": "#888888", "icon_fill": "#333333",
        "accent": "#268cdd", "orange": "#f57729", "green": "#49db40", "red": "#ff7a74",
        "strip_text": "#ffffff", "strip_text_disabled": "#9ec5e8", "strip_icon_fill": "#1a4f85", "strip_icon_fg2": "#c9e7ff", "primary_pressed": "#0b2f5c", "primary_hover": "#268cdd",
        "plot_style": "matlab-dark",
    },
    "light": {
        "bg": "#f5f5f5", "bg2": "#e6e6e6", "bg3": "#ffffff", "input": "#ffffff", "stripe": "#f5f5f5",
        "hover": "#ffffff", "selected": "#bfbfbf", "selected_focus": "#b4deff", "list_hover": "#d9d9d9",
        "toggle_on": "#d9d9d9", "toolbar_on": "#b4deff",
        "strip": "#004073", "strip_hover": "#268cdd", "strip_selected": "#1171be", "panel_header_sel": "#004073",
        "qab_hover": "#0b2f5c", "qab_active": "#00243e",
        "scroll": "#bfbfbf", "scroll_hover": "#a6a6a6", "scroll_active": "#888888",
        "border": "#7d7d7d", "border2": "#bfbfbf", "border3": "#616161", "focus": "#268cdd", "border_hover": "#333333",
        "text": "#212121", "text2": "#616161", "text3": "#ffffff", "text_selected": "#212121",
        "error": "#b7312c", "warning": "#edb120", "success": "#008013", "link": "#1171be",
        "tab": "#e6e6e6", "tab_selected": "#f5f5f5",
        "icon_fg": "#616161", "icon_fg2": "#888888", "icon_fill": "#d9d9d9",
        "accent": "#1171be", "orange": "#dd5400", "green": "#3baa32", "red": "#b7312c",
        "strip_text": "#ffffff", "strip_text_disabled": "#9ec5e8", "strip_icon_fill": "#1a4f85", "strip_icon_fg2": "#c9e7ff", "primary_pressed": "#0b2f5c", "primary_hover": "#268cdd",
        "plot_style": "matlab",
    },
    # Sony 風（黑銀）：α 相機機身的霧面暖黑＋石墨銀邊線，唯一的彩色是 α 橘（只給焦點、選取、主要按鈕）
    "sony_black": {
        "bg": "#1c1b19", "bg2": "#2b2a27", "bg3": "#0c0c0b", "input": "#121110", "stripe": "#121110",
        "hover": "#2e2d2a", "selected": "#4b4946", "selected_focus": "#663008", "list_hover": "#5a5855",
        "toggle_on": "#0c0c0b", "toolbar_on": "#663008",
        "strip": "#393833", "strip_hover": "#55534e", "strip_selected": "#c2560a", "panel_header_sel": "#c2560a",
        "qab_hover": "#55534e", "qab_active": "#1c1b19",
        "scroll": "#4b4946", "scroll_hover": "#5e5c58", "scroll_active": "#7a7872",
        "border": "#7a7872", "border2": "#504e49", "border3": "#a39f98", "focus": "#f27a1a", "border_hover": "#c4c1ba",
        "text": "#dcdad5", "text2": "#95928c", "text3": "#ffffff", "text_selected": "#f2f0eb",
        "error": "#ff7a74", "warning": "#edb120", "success": "#94ef84", "link": "#f5a35a",
        "tab": "#2b2a27", "tab_selected": "#1c1b19",
        "icon_fg": "#dcdad5", "icon_fg2": "#95928c", "icon_fill": "#2b2a27",
        "accent": "#f27a1a", "orange": "#e9b44c", "green": "#49db40", "red": "#ff7a74",
        "strip_text": "#ffffff", "strip_text_disabled": "#95928c", "strip_icon_fill": "#55534e", "strip_icon_fg2": "#c4c1ba", "primary_pressed": "#883c07", "primary_hover": "#55534e",
        "plot_style": "sony-black",
    },
    # Sony 風（深藍黑）：PlayStation 系統介面的藍黑底＋冷白字，PlayStation 藍當主要動作、電藍當焦點與指示線
    "sony_blue": {
        "bg": "#0f1621", "bg2": "#202a3a", "bg3": "#070b12", "input": "#0a0f17", "stripe": "#111a26",
        "hover": "#283346", "selected": "#2e3a4f", "selected_focus": "#0a4f9c", "list_hover": "#3a4760",
        "toggle_on": "#050912", "toolbar_on": "#0a3d7c",
        "strip": "#0b2f6b", "strip_hover": "#1f7fe0", "strip_selected": "#0070d1", "panel_header_sel": "#0070d1",
        "qab_hover": "#164a9e", "qab_active": "#071f4a",
        "scroll": "#2e3a4f", "scroll_hover": "#3a4760", "scroll_active": "#4a5873",
        "border": "#56657f", "border2": "#2f3b52", "border3": "#6b7a93", "focus": "#2e8cff", "border_hover": "#8ea2c2",
        "text": "#e6ecf5", "text2": "#8a97ad", "text3": "#ffffff", "text_selected": "#f2f6fc",
        "error": "#ff6e6e", "warning": "#f0b429", "success": "#62d98a", "link": "#5ea8ff",
        "tab": "#202a3a", "tab_selected": "#0f1621",
        "icon_fg": "#e6ecf5", "icon_fg2": "#8a97ad", "icon_fill": "#202a3a",
        "accent": "#2e8cff", "orange": "#ff8a3d", "green": "#4fd96a", "red": "#ff6e6e",
        "strip_text": "#ffffff", "strip_text_disabled": "#8a97ad", "strip_icon_fill": "#164a9e", "strip_icon_fg2": "#c5d0e0", "primary_pressed": "#004e92", "primary_hover": "#1f7fe0",
        "plot_style": "sony-blue",
    },
    # Apple 風（淺色）：macOS 淺色外觀的 #ececec 視窗底、白色內容區、macOS「紫色」強調色（淺色模式系統紫 #af52de）；分頁列是淺灰的分段控制（深色字）。
    # 1.0.0 使用者「全部都做上去」（少一點藍）：原本的系統藍全部換紫——帶白字的面（主要按鈕、被選面板、分頁列的 contextual 分頁）用無障礙版的深紫
    # #8944ab（白字 6.0:1），hover #9850bd（5.0:1）、按下 #6e3689；選取列用淡紫（字 #1d1d1f 在上面 ≥11:1）
    "apple_light": {
        "bg": "#ececec", "bg2": "#dcdce1", "bg3": "#ffffff", "input": "#ffffff", "stripe": "#f5f5f7",
        "hover": "#f7f7f9", "selected": "#efdcf8", "selected_focus": "#e7cbf5", "list_hover": "#e5e5ea",
        "toggle_on": "#d1d1d6", "toolbar_on": "#e7cbf5",
        "strip": "#d1d1d6", "strip_hover": "#e0e0e5", "strip_selected": "#8944ab", "panel_header_sel": "#8944ab",
        "qab_hover": "#c7c7cc", "qab_active": "#aeaeb2",
        "scroll": "#c7c7cc", "scroll_hover": "#aeaeb2", "scroll_active": "#8e8e93",
        "border": "#aeaeb2", "border2": "#d2d2d7", "border3": "#8e8e93", "focus": "#af52de", "border_hover": "#8e8e93",
        "text": "#1d1d1f", "text2": "#636366", "text3": "#ffffff", "text_selected": "#1d1d1f",      # text2：1.0.0 B4 對比 ≥4.5:1（#6e6e73 在 #ececec 上只有 4.29）
        "error": "#d70015", "warning": "#c93400", "success": "#248a3d", "link": "#8944ab",
        "tab": "#dcdce1", "tab_selected": "#ececec",
        "icon_fg": "#3a3a3c", "icon_fg2": "#8e8e93", "icon_fill": "#d1d1d6",
        "accent": "#af52de", "orange": "#ff9500", "green": "#34c759", "red": "#ff3b30",
        "strip_text": "#1d1d1f", "strip_text_disabled": "#6e6e73", "strip_icon_fill": "#ececec", "strip_icon_fg2": "#8e8e93", "primary_pressed": "#6e3689", "primary_hover": "#9850bd",
        "plot_style": "apple-light",
    },
    # Apple 風（深色）：macOS 深色外觀的 #1e1e1e 底、石墨灰分頁列，藍色只給選到／正在操作的東西（HIG 深色系統色）
    "apple_dark": {
        "bg": "#1e1e1e", "bg2": "#2b2b2b", "bg3": "#262626", "input": "#181818", "stripe": "#1c1c1e",
        "hover": "#303033", "selected": "#3b3b3d", "selected_focus": "#5b2a78", "list_hover": "#48484a",
        "toggle_on": "#48484a", "toolbar_on": "#4a2363",
        "strip": "#2b2b2b", "strip_hover": "#6e3a8f", "strip_selected": "#8e3cc0", "panel_header_sel": "#7d3aa8",
        "qab_hover": "#3a3a3c", "qab_active": "#48484a",
        "scroll": "#48484a", "scroll_hover": "#636366", "scroll_active": "#8e8e93",
        "border": "#545458", "border2": "#3a3a3c", "border3": "#8e8e93", "focus": "#bf5af2", "border_hover": "#aeaeb2",
        "text": "#f5f5f7", "text2": "#98989d", "text3": "#ffffff", "text_selected": "#ffffff",
        "error": "#ff453a", "warning": "#ffd60a", "success": "#30d158", "link": "#da8fff",
        "tab": "#2b2b2b", "tab_selected": "#1e1e1e",
        "icon_fg": "#e5e5ea", "icon_fg2": "#98989d", "icon_fill": "#3a3a3c",
        "accent": "#bf5af2", "orange": "#ff9f0a", "green": "#30d158", "red": "#ff453a",
        "strip_text": "#ffffff", "strip_text_disabled": "#6e6e73", "strip_icon_fill": "#3a3a3c", "strip_icon_fg2": "#98989d", "primary_pressed": "#6e2f96", "primary_hover": "#9a4bc7",
        "plot_style": "apple-dark",
    },
}
# 1.0.0 使用者「全部都做上去」：試用時看過的兩個 Apple 深色變體也留成主題選項（Apple 深色本身維持紫）。兩個都從 apple_dark 複製、只覆蓋下面幾個鍵。
# 石墨橘：選取／被選面板／分頁 hover 改成石墨灰（#636366 上白字 6.0:1），強調色＝macOS 深色系統橘 #ff9f0a。
TOKENS["apple_dark_graphite"] = {
    **TOKENS["apple_dark"],
    "selected_focus": "#5a5a5e", "toolbar_on": "#48484a", "strip_hover": "#48484a", "strip_selected": "#636366", "panel_header_sel": "#636366",
    "focus": "#ff9f0a", "accent": "#ff9f0a", "link": "#ffb340", "primary_hover": "#7c7c80", "primary_pressed": "#48484a",
    "plot_style": "apple-dark-graphite",
}
# 純黑綠：watchOS 那種純黑底＋系統綠 #30d158 強調色（和「成功」狀態色同一個綠）。帶白字的綠面 #248a3d 白字只有 4.40:1，
# 稍微壓暗成 #24883d（4.50:1）。
TOKENS["apple_dark_black"] = {
    **TOKENS["apple_dark"],
    "bg": "#000000", "bg2": "#1c1c1e", "bg3": "#000000", "input": "#1c1c1e", "stripe": "#0e0e0f",
    "hover": "#2c2c2e", "selected": "#2c2c2e", "list_hover": "#3a3a3c", "toggle_on": "#2c2c2e",
    "strip": "#1c1c1e", "tab": "#1c1c1e", "tab_selected": "#000000", "border": "#3a3a3c", "border2": "#2c2c2e",      # 分頁列 #1c1c1e：選中的分頁＝#000000 內容區，看得出選了哪個（1.0.0 W100R1-1）
    "text": "#ffffff", "icon_fill": "#2c2c2e", "strip_icon_fill": "#2c2c2e",
    "selected_focus": "#1d5f2f", "toolbar_on": "#174d26", "strip_hover": "#2c2c2e", "strip_selected": "#24883d", "panel_header_sel": "#24883d",
    "focus": "#30d158", "accent": "#30d158", "link": "#4cd964", "primary_hover": "#2a9d47", "primary_pressed": "#1d6f33",
    "plot_style": "apple-dark-black",
}
THEMES = tuple(TOKENS)
DEFAULT_THEME = "dark"                 # 使用者的 MATLAB 桌面主題（settings → MATLABTheme = Dark）
# 按鈕／輸入框／工具鈕圓角（px）：MATLAB 的兩個主題 3；Sony 黑銀收到 1（α 機身的稜線）、Apple 5（Sonoma 控制項）；沒列的用 PX["radius"]
RADIUS_PX: Dict[str, int] = {"dark": 3, "light": 3, "sony_black": 1, "sony_blue": 3, "apple_light": 5, "apple_dark": 5,
                             "apple_dark_graphite": 5, "apple_dark_black": 5}


def theme_label(name: str) -> str:
    """主題在介面上的名稱（目前語言；偏好設定 ▸ 外觀 ▸ 主題、檢視 ▸ 外觀 的下拉用）。沒有這個主題就回名稱本身。"""
    labels = {"dark": tr("深色"), "light": tr("淺色"), "sony_black": tr("Sony 風（黑銀）"), "sony_blue": tr("Sony 風（深藍黑）"),
              "apple_light": tr("Apple 風（淺色）"), "apple_dark": tr("Apple 風（深色）"),
              "apple_dark_graphite": tr("Apple 風（深色·石墨橘）"), "apple_dark_black": tr("Apple 風（深色·純黑綠）")}
    return labels.get(name, name)


def theme_labels() -> Tuple[str, ...]:
    """所有主題的介面名稱，順序＝THEMES（下拉選單的選項）。"""
    return tuple(theme_label(n) for n in THEMES)


def theme_from_label(label: str, default: str = DEFAULT_THEME) -> str:
    """介面名稱 → 主題名；對不到（例如語言換了）回 default（不合法的 default 回 DEFAULT_THEME）。"""
    for n in THEMES:
        if theme_label(n) == label:
            return n
    return default if default in TOKENS else DEFAULT_THEME

# 尺寸（px，依 docs 第 2 節）
PX = {"font": 12, "font_small": 11, "font_title": 13, "tab_h": 28, "panel_title_h": 23, "row_h": 22,
      "btn_h": 23, "big_btn_h": 72, "pad": 10, "radius": 3, "check": 14, "scroll_w": 12, "scroll_inset": 2, "sash": 6}
UI_FONT_PX_RANGE = (9, 16)       # 偏好設定 → 字型 的「介面字級」（MATLAB Settings ▸ Fonts）；預設 PX["font"]
_FONT_DELTA = 0                  # 介面字級 − 12：所有命名字型與表格列高一起加


def set_ui_font_px(n) -> int:
    """介面字級（9～16 px，預設 12）：重設所有命名字型（已建的元件立刻跟著變）與 Treeview 列高。回傳實際用的字級。"""
    global _FONT_DELTA
    try:
        n = int(round(float(n)))
    except Exception:
        n = PX["font"]
    n = max(UI_FONT_PX_RANGE[0], min(UI_FONT_PX_RANGE[1], n))
    th = _CURRENT
    if n - PX["font"] == _FONT_DELTA and th is not None and th.fonts:
        return n                       # 沒變：不重設字型（重設會讓所有元件重新排版）
    _FONT_DELTA = n - PX["font"]
    if th is not None:
        try:
            th._make_fonts()
        except Exception:
            pass
    return n


def ui_font_px() -> int:
    return PX["font"] + _FONT_DELTA


def _hex(c: str) -> Tuple[int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def mix(c1: str, c2: str, t: float) -> str:
    """c1 與 c2 線性混色（t=0 → c1）。"""
    a, b = _hex(c1), _hex(c2)
    return "#%02x%02x%02x" % tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def is_dark(c: str) -> bool:
    r, g, b = _hex(c)
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128


# ---------------------------------------------------------------------------
# Theme 物件
# ---------------------------------------------------------------------------
_CURRENT: Optional["Theme"] = None
_THEMES: Dict[Tuple[int, str], "Theme"] = {}          # (interpreter, name) → Theme（活到行程結束）
_ELEMENTS: Dict[int, set] = {}                         # interpreter → 已建的 ttk 圖片元素名
_ELEMENT_SPECS: Dict[Tuple[int, str], list] = {}       # (interpreter, 元素名) → [(狀態, PhotoImage)…]：ttk 依序比對、第一個符合的狀態用它的圖
_LISTENERS: "weakref.WeakSet" = weakref.WeakSet() if HAVE_TK else set()     # 物件要有 .on_theme(theme)
_ICON_WIDGETS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary() if HAVE_TK else {}


def _interp(root) -> int:
    try:
        return int(root.tk.interpaddr())
    except Exception:
        return id(root)


class Theme:
    def __init__(self, root, name: str):
        if name not in TOKENS:
            raise KeyError(f"沒有這個主題：{name!r}（可用：{', '.join(TOKENS)}）")
        self.root = root
        self.name = name
        self.t = dict(TOKENS[name])
        self.fonts: Dict[str, Any] = {}
        self.images: List[Any] = []            # 圖片元素用的 PhotoImage；Theme 活著它們就活著
        self.style = ttk.Style(root)
        self._scale = self._compute_scale()
        self._built = False
        self.interp = _interp(root)
        self.font_family = ""
        self.font_px = PX["font"]
        self.dark = is_dark(self.t["bg"])          # 深色主題（視窗底色暗）：選單底、按下的字色、tooltip 底、圖示的「白」都看這個，不看名稱
        self.radius = RADIUS_PX.get(name, PX["radius"])

    # --- 尺寸與字型 -----------------------------------------------------------
    def _compute_scale(self) -> float:
        if IS_MAC:
            return 1.0                       # mac 的 Tk 以點為單位，MATLAB 的 12px 就是 12pt
        try:
            return max(0.75, float(self.root.winfo_fpixels("1i")) / 96.0)
        except Exception:
            return 1.0

    @property
    def scale(self) -> float:
        return self._scale

    def px(self, n: float) -> int:
        return max(1, int(round(n * self._scale)))

    def c(self, key: str) -> str:
        return self.t[key]

    def __getitem__(self, key: str) -> str:
        return self.t[key]

    def font(self, role: str = "default"):
        return self.fonts.get(role) or self.fonts["default"]

    def element_specs(self, elname: str) -> List[Tuple[Tuple[str, ...], Any]]:
        """這個主題的圖片元素（例如 "field"＝TEntry／TCombobox／TSpinbox 的框）建立時的狀態對應：[((), 預設圖), (("disabled",), 圖)…]，
        順序就是 ttk 比對的順序（第一個符合的狀態用它的圖：invalid 排在 focus 前面，打錯字、游標還在欄位裡時也是紅框）。沒有 Pillow
        （沒建圖片元素）時是空的。"""
        return list(_ELEMENT_SPECS.get((self.interp, f"Pk{self.name.title()}.{elname}"), []))

    def icon_palette(self, on_strip: bool = False) -> Dict[str, str]:
        t = self.t
        if on_strip:
            if is_dark(t["strip"]):              # 深色分頁列（MATLAB 的藍、Sony 的石墨／藍黑、Apple 深色的石墨）：白色筆畫＋粉彩語意色
                return {"fg": t["strip_text"], "fg2": t["strip_icon_fg2"], "fill": t["strip_icon_fill"], "accent": t["strip_text"],
                        "orange": "#ffd19e", "green": "#cbffbe", "red": "#ffcbcb", "white": t["strip"]}      # 白底上的字用分頁列的底色
            return {"fg": t["strip_text"], "fg2": t["strip_icon_fg2"], "fill": t["strip_icon_fill"], "accent": t["accent"],
                    "orange": t["orange"], "green": t["green"], "red": t["red"], "white": t["bg3"]}      # 淺色分頁列（Apple 淺色）：和一般圖示同一套
        return {"fg": t["icon_fg"], "fg2": t["icon_fg2"], "fill": t["icon_fill"], "accent": t["accent"],
                "orange": t["orange"], "green": t["green"], "red": t["red"],
                "white": "#f5f5f5" if self.dark else t["bg3"]}

    def icon(self, name: str, size: int = 16, *, on_strip: bool = False):
        """主題配色的圖示（PhotoImage）；on_strip=True 是放在工具列分頁列上的版本（深色分頁列＝白色筆畫）。沒有 Pillow 回 None。"""
        return I.get_icon(name, self.px(size), self.icon_palette(on_strip), master=self.root)

    def bind_icon(self, widget, name: str, size: int = 16, *, on_strip: bool = False) -> bool:
        """讓 widget 的 image 跟著主題切換；回傳是否真的有圖（沒有 Pillow 時 False，呼叫端要留文字）。"""
        img = self.icon(name, size, on_strip=on_strip)
        if img is not None:
            try:
                widget.configure(image=img)
            except Exception:
                return False
        _ICON_WIDGETS[widget] = (name, size, on_strip)
        return img is not None

    # --- 字型 ----------------------------------------------------------------
    def _make_fonts(self) -> None:
        base = tkfont.nametofont("TkDefaultFont")
        family = base.actual("family")
        if IS_WIN and family.lower().startswith("microsoft sans"):
            family = "Segoe UI"
        mono = "Menlo" if IS_MAC else ("Consolas" if IS_WIN else "DejaVu Sans Mono")
        fd = _FONT_DELTA
        size = -self.px(PX["font"] + fd)
        spec = {
            "default": dict(family=family, size=size),
            "bold": dict(family=family, size=size, weight="bold"),
            "small": dict(family=family, size=-self.px(PX["font_small"] + fd)),
            "small_bold": dict(family=family, size=-self.px(PX["font_small"] + fd), weight="bold"),
            "title": dict(family=family, size=-self.px(PX["font_title"] + fd)),
            "title_bold": dict(family=family, size=-self.px(PX["font_title"] + fd), weight="bold"),
            "mono": dict(family=mono, size=size),
            "big": dict(family=family, size=-self.px(16), weight="bold"),
        }
        for role, kw in spec.items():
            name = "Pk" + role.title().replace("_", "")
            f = self.fonts.get(role)
            if f is not None:                   # 第二次以後（activate、改介面字級）：改原本那個物件，不要換成新的包裝物件——
                try:                            # 原本的物件被回收時（delete_font）會把 Tk 的命名字型刪掉，用它的元件就退回系統字型
                    f.configure(**kw)
                    continue
                except Exception:
                    pass
            try:
                f = tkfont.nametofont(name)
                f.configure(**kw)
            except Exception:
                f = tkfont.Font(root=self.root, name=name, **kw)
                f.delete_font = False           # 命名字型給所有主題物件與元件共用，活到行程結束；Python 物件回收時不刪
            self.fonts[role] = f
        # Tk 內建的命名字型也統一（Treeview、Menu、Entry 預設都吃這些）
        for n in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkTooltipFont"):
            try:
                tkfont.nametofont(n).configure(family=family, size=size)
            except Exception:
                pass
        try:
            tkfont.nametofont("TkFixedFont").configure(family=mono, size=size)
        except Exception:
            pass
        self.font_family = family
        self.font_px = -size
        if self._built:
            try:
                self.style.configure("Treeview", rowheight=self.px(PX["row_h"] + fd))
            except Exception:
                pass

    # --- 圖片元素（圓角按鈕、輸入框、核取方塊、捲軸、滑桿、箭頭） ---------------------------
    def _img(self, w: int, h: int, fill: Optional[str], outline: Optional[str], radius: int = 0,
             draw: Optional[Callable] = None, inset: int = 0):
        """用 Pillow 畫 9-slice 用的小圖（4 倍超取樣）；沒有 Pillow 或畫不出來時回 None。inset＝四邊留透明邊（像 CSS 的透明 border）。"""
        if not I.HAVE_PIL:
            return None
        try:
            from PIL import Image, ImageDraw, ImageTk
            k = I.SS
            im = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            box = [inset * k, inset * k, (w - inset) * k - 1, (h - inset) * k - 1]
            if fill or outline:
                if radius > 0 and hasattr(d, "rounded_rectangle"):
                    d.rounded_rectangle(box, radius=radius * k, fill=fill, outline=outline, width=k if outline else 0)
                else:
                    d.rectangle(box, fill=fill, outline=outline, width=k if outline else 0)
            if draw:
                draw(d, k)
            im = im.resize((w, h), Image.LANCZOS)
            img = ImageTk.PhotoImage(im, master=self.root)
        except Exception:
            return None
        self.images.append(img)
        return img

    def _check_img(self, checked: bool, kind: str, fg: str, bg: str, border: str):
        s = self.px(PX["check"])
        gap = self.px(6)

        def draw(d, k):
            x1 = s * k - 1
            if kind == "radio":
                d.ellipse([0, 0, x1, x1], fill=bg, outline=border, width=k)
                if checked:
                    m = int(s * k * 0.28)
                    d.ellipse([m, m, x1 - m, x1 - m], fill=fg)
            else:
                d.rectangle([0, 0, x1, x1], fill=bg, outline=border, width=k)
                if checked:
                    pts = [(0.22 * s * k, 0.52 * s * k), (0.42 * s * k, 0.72 * s * k), (0.78 * s * k, 0.28 * s * k)]
                    d.line(pts, fill=fg, width=int(1.6 * k), joint="curve")
        return self._img(s + gap, s, None, None, 0, draw)

    def _arrow_img(self, direction: str, color: str, size: int = 12):
        s = self.px(size)

        def draw(d, k):
            w = s * k
            cx, cy = w / 2, w / 2
            a = w * 0.22
            if direction == "down":
                pts = [(cx - a, cy - a * 0.5), (cx, cy + a * 0.5), (cx + a, cy - a * 0.5)]
            elif direction == "up":
                pts = [(cx - a, cy + a * 0.5), (cx, cy - a * 0.5), (cx + a, cy + a * 0.5)]
            elif direction == "right":
                pts = [(cx - a * 0.5, cy - a), (cx + a * 0.5, cy), (cx - a * 0.5, cy + a)]
            else:
                pts = [(cx + a * 0.5, cy - a), (cx - a * 0.5, cy), (cx + a * 0.5, cy + a)]
            d.line(pts, fill=color, width=int(1.4 * k), joint="curve")
        return self._img(s, s, None, None, 0, draw)

    def _tri_img(self, direction: str, color: str, size: int = 10):
        """樹的展開指示（MATLAB 是小實心三角）。"""
        s = self.px(size)
        w_ = self.px(14)

        def draw(d, k):
            w = s * k
            ox = (w_ * k - w) / 2
            if direction == "down":
                pts = [(ox + w * 0.15, w * 0.3), (ox + w * 0.85, w * 0.3), (ox + w * 0.5, w * 0.75)]
            else:
                pts = [(ox + w * 0.3, w * 0.15), (ox + w * 0.75, w * 0.5), (ox + w * 0.3, w * 0.85)]
            d.polygon(pts, fill=color)
        return self._img(w_, s, None, None, 0, draw)

    # --- 建 ttk 主題（每個 Theme 物件只做一次） -------------------------------------------
    def build(self) -> None:
        if self._built:
            return
        t = self.t
        st = self.style
        name = f"plotkit-{self.name}"
        px = self.px
        self._make_fonts()
        f_def, f_bold, f_small, f_title = self.fonts["default"], self.fonts["bold"], self.fonts["small"], self.fonts["title"]
        if name not in st.theme_names():
            st.theme_create(name, parent="clam")
        st.theme_use(name)
        pfx = f"Pk{self.name.title()}."
        elements = _ELEMENTS.setdefault(self.interp, set())
        r = self.radius                     # 每個主題各自的圓角（RADIUS_PX）

        def el(elname: str, specs: Sequence[Tuple[Tuple[str, ...], Any]], border, sticky: str = "nswe",
               padding: Optional[Tuple[int, ...]] = None, **extra):
            full = pfx + elname
            if full in elements:
                return full
            default = specs[0][1]
            if default is None:
                return None
            flat = [(" ".join(s), img) for s, img in specs[1:] if img is not None]
            kw = dict(border=border, sticky=sticky, padding=padding if padding is not None else (0, 0, 0, 0))
            kw.update(extra)
            try:
                st.element_create(full, "image", default, *flat, **kw)
            except tk.TclError:
                return None
            elements.add(full)
            _ELEMENT_SPECS[(self.interp, full)] = [(tuple(s), img) for s, img in specs if img is not None]
            return full

        W, H = px(24), px(24)
        rr = px(r)
        b_norm = self._img(W, H, t["bg"], t["border"], rr)
        b_hover = self._img(W, H, t["hover"], t["border_hover"], rr)
        b_press = self._img(W, H, t["toggle_on"], t["border_hover"], rr)
        b_dis = self._img(W, H, t["bg"], t["border2"], rr)
        b_focus = self._img(W, H, t["bg"], t["focus"], rr)
        b_on = self._img(W, H, t["toggle_on"], t["border"], rr)
        btn = el("button", [((), b_norm), (("disabled",), b_dis), (("pressed",), b_press), (("selected",), b_on),
                             (("active",), b_hover), (("focus",), b_focus)], border=px(5))
        p_norm = self._img(W, H, t["strip_selected"], t["strip_selected"], rr)
        p_hover = self._img(W, H, t["strip_hover"], t["strip_hover"], rr)
        p_press = self._img(W, H, t["primary_pressed"], t["primary_pressed"], rr)
        p_dis = self._img(W, H, t["bg2"], t["border2"], rr)
        pbtn = el("primary", [((), p_norm), (("disabled",), p_dis), (("pressed",), p_press), (("active",), p_hover)],
                  border=px(5))
        tl_norm = self._img(W, H, None, None, rr)
        tl_hover = self._img(W, H, t["hover"], t["border"], rr)
        tl_press = self._img(W, H, t["toggle_on"], t["border"], rr)
        tl_toggle = self._img(W, H, t["toggle_on"], t["border"], rr)          # toolstrip 開關按下的底色
        tl_axes = self._img(W, H, t["toolbar_on"], t["border"], rr)          # 圖的工具列開關按下的底色
        tool = el("tool", [((), tl_norm), (("disabled",), tl_norm), (("pressed",), tl_press),
                            (("selected", "active"), tl_toggle), (("selected",), tl_toggle), (("active",), tl_hover)], border=px(5))
        axestool = el("axestool", [((), tl_norm), (("disabled",), tl_norm), (("pressed",), tl_press),
                                    (("selected", "active"), tl_axes), (("selected",), tl_axes), (("active",), tl_hover)], border=px(5))
        q_norm = self._img(W, H, None, None, rr)
        q_hover = self._img(W, H, t["qab_hover"], t["qab_hover"], rr)
        q_press = self._img(W, H, t["qab_active"], t["qab_active"], rr)
        qab = el("qab", [((), q_norm), (("disabled",), q_norm), (("pressed",), q_press), (("active",), q_hover)], border=px(5))
        f_norm = self._img(W, H, t["input"], t["border"], rr)
        f_focus = self._img(W, H, t["input"], t["focus"], rr)
        f_ro = self._img(W, H, t["bg"], t["border"], rr)
        f_ro_hover = self._img(W, H, t["hover"], t["border_hover"], rr)
        f_dis = self._img(W, H, t["bg2"], t["border2"], rr)
        f_err = self._img(W, H, mix(t["input"], t["error"], 0.12), t["error"], rr)   # 欄位的錯誤狀態（ttk invalid；MATLAB 欄位的錯誤狀態）
        field = el("field", [((), f_norm), (("disabled",), f_dis), (("invalid",), f_err), (("focus",), f_focus),
                              (("readonly", "active"), f_ro_hover), (("readonly",), f_ro)], border=px(5))
        bc = t["border3"]                                     # 核取方塊框色（實測）
        c_off = self._check_img(False, "check", t["text"], t["input"], bc)
        c_on = self._check_img(True, "check", t["text"], t["input"], bc)
        c_off_d = self._check_img(False, "check", t["text2"], t["bg2"], t["border2"])
        c_on_d = self._check_img(True, "check", t["text2"], t["bg2"], t["border2"])
        c_off_a = self._check_img(False, "check", t["text"], t["input"], t["focus"])
        c_on_a = self._check_img(True, "check", t["text"], t["input"], t["focus"])
        check = el("check", [((), c_off), (("disabled", "selected"), c_on_d), (("disabled",), c_off_d),
                              (("selected", "active"), c_on_a), (("selected",), c_on), (("active",), c_off_a)],
                   border=0, sticky="")
        r_off = self._check_img(False, "radio", t["text"], t["input"], bc)
        r_on = self._check_img(True, "radio", t["text"], t["input"], bc)
        r_off_d = self._check_img(False, "radio", t["text2"], t["bg2"], t["border2"])
        r_on_d = self._check_img(True, "radio", t["text2"], t["bg2"], t["border2"])
        r_on_a = self._check_img(True, "radio", t["text"], t["input"], t["focus"])
        r_off_a = self._check_img(False, "radio", t["text"], t["input"], t["focus"])
        radio = el("radio", [((), r_off), (("disabled", "selected"), r_on_d), (("disabled",), r_off_d),
                              (("selected", "active"), r_on_a), (("selected",), r_on), (("active",), r_off_a)],
                   border=0, sticky="")
        # 捲軸照 MATLAB 桌面的捲軸樣式：寬 12px、軌道＝面板底色、
        # 滑塊＝捲軸滑塊色、四邊 2px 透明邊（和底色同色）、圓角 6px → 看得到的是 8px 寬的圓角長條；
        # hover／按住換對應的 hover／拖曳中顏色。元素名最後一段必須是 trough／thumb：ttk::scrollbar 用
        # Ttk_FindElement(layout, "thumb") 依 first/last 擺滑塊，找不到就讓滑塊填滿整條（2026-10-23 之前取名 vthumb 就是這樣，
        # 捲動時看不出位置）。
        sw = px(PX["scroll_w"])
        ins = px(PX["scroll_inset"])
        rad = px(6)
        vtrough = el("Vertical.Scrollbar.trough", [((), self._img(sw, px(24), t["bg"], None, 0))], border=px(4), sticky="ns")
        vthumb = el("Vertical.Scrollbar.thumb",
                    [((), self._img(sw, px(24), t["scroll"], None, rad, inset=ins)),
                     (("pressed",), self._img(sw, px(24), t["scroll_active"], None, rad, inset=ins)),
                     (("active",), self._img(sw, px(24), t["scroll_hover"], None, rad, inset=ins))], border=px(8), sticky="nswe")
        htrough = el("Horizontal.Scrollbar.trough", [((), self._img(px(24), sw, t["bg"], None, 0))], border=px(4), sticky="we")
        hthumb = el("Horizontal.Scrollbar.thumb",
                    [((), self._img(px(24), sw, t["scroll"], None, rad, inset=ins)),
                     (("pressed",), self._img(px(24), sw, t["scroll_active"], None, rad, inset=ins)),
                     (("active",), self._img(px(24), sw, t["scroll_hover"], None, rad, inset=ins))], border=px(8), sticky="nswe")
        down = el("downarrow", [((), self._arrow_img("down", t["text"])), (("disabled",), self._arrow_img("down", t["text2"]))],
                  border=0, sticky="")
        up = el("uparrow", [((), self._arrow_img("up", t["text"], 10)), (("disabled",), self._arrow_img("up", t["text2"], 10))],
                border=0, sticky="")
        down_s = el("downarrow_s", [((), self._arrow_img("down", t["text"], 10)), (("disabled",), self._arrow_img("down", t["text2"], 10))],
                    border=0, sticky="")
        # 元素名最後一段必須是 trough／slider：ttk::scale 用 Ttk_FindElement(layout, "slider") 依值擺放滑塊，
        # 叫 sslider 會找不到 → 滑塊永遠畫在最左邊、拖了也不動（值有變）
        s_tr = el("Scale.trough", [((), self._img(px(24), px(4), t["border2"], None, px(2)))], border=px(3), sticky="we")
        s_sl = el("Scale.slider", [((), self._img(px(14), px(14), t["text2"], None, px(7))),
                              (("pressed",), self._img(px(14), px(14), t["text"], None, px(7))),
                              (("active",), self._img(px(14), px(14), t["text"], None, px(7)))], border=0, sticky="")
        tri = el("treeind", [((), self._tri_img("right", t["text"])), (("user2",), self._img(px(14), px(10), None, None, 0)),
                             (("user1",), self._tri_img("down", t["text"]))], border=0, sticky="w")

        # --- 基本 ---------------------------------------------------------------
        st.configure(".", background=t["bg"], foreground=t["text"], font=f_def, bordercolor=t["border"],
                     darkcolor=t["bg"], lightcolor=t["bg"], troughcolor=t["bg2"], fieldbackground=t["input"],
                     selectbackground=t["selected_focus"], selectforeground=t["text"], insertcolor=t["text"],
                     focuscolor=t["focus"], arrowcolor=t["text"], arrowsize=px(12))
        st.map(".", foreground=[("disabled", t["text2"])])
        st.configure("TFrame", background=t["bg"])
        st.configure("TLabel", background=t["bg"], foreground=t["text"], padding=0)
        st.configure("Hint.TLabel", foreground=t["text2"])
        st.configure("Warn.TLabel", foreground=t["error"], font=f_bold)
        st.configure("Error.TLabel", foreground=t["error"])
        st.configure("Title.TLabel", font=f_title)
        st.configure("Bold.TLabel", font=f_bold)
        st.configure("Small.TLabel", font=f_small, foreground=t["text2"])
        st.configure("Status.TLabel", background=t["bg2"], foreground=t["text"], padding=(px(6), px(3)))
        st.configure("Input.TFrame", background=t["input"])
        st.configure("Bg2.TFrame", background=t["bg2"])
        st.configure("Bg2.TLabel", background=t["bg2"])
        st.configure("Border.TFrame", background=t["border"])
        st.configure("Border2.TFrame", background=t["border2"])
        # --- 按鈕 ---------------------------------------------------------------
        if btn:
            st.layout("TButton", [(btn, {"sticky": "nswe", "children": [
                ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
        st.configure("TButton", padding=(px(10), px(3)), anchor="center", background=t["bg"], foreground=t["text"],
                     bordercolor=t["border"], lightcolor=t["bg"], darkcolor=t["bg"], relief="flat", shiftrelief=0, width=0)
        st.map("TButton", background=[("disabled", t["bg"]), ("pressed", t["toggle_on"]), ("selected", t["toggle_on"]),
                                      ("active", t["hover"])],
               foreground=[("disabled", t["text2"]), ("pressed", t["text3"] if self.dark else t["text"])],
               bordercolor=[("active", t["border_hover"])], lightcolor=[("active", t["hover"])], darkcolor=[("active", t["hover"])])
        if pbtn:
            st.layout("Primary.TButton", [(pbtn, {"sticky": "nswe", "children": [
                ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
        st.configure("Primary.TButton", background=t["strip_selected"], foreground=t["text3"], font=f_bold, padding=(px(14), px(4)))
        st.map("Primary.TButton", background=[("disabled", t["bg2"]), ("pressed", t["primary_pressed"]), ("active", t["primary_hover"])],
               foreground=[("disabled", t["text2"])])

        def tool_layout(e, w):
            return [(e, {"sticky": "nswe", "children": [
                (f"{w}.padding", {"sticky": "nswe", "children": [(f"{w}.label", {"sticky": "nswe"})]})]})]

        if tool:
            st.layout("Tool.TButton", tool_layout(tool, "Button"))
            st.layout("Tool.TCheckbutton", tool_layout(tool, "Checkbutton"))
        if axestool:
            st.layout("AxesTool.TCheckbutton", tool_layout(axestool, "Checkbutton"))
        for s_, on in (("Tool.TButton", t["toggle_on"]), ("Tool.TCheckbutton", t["toggle_on"]), ("AxesTool.TCheckbutton", t["toolbar_on"])):
            st.configure(s_, background=t["bg"], padding=(px(6), px(3)), anchor="center", justify="center")
            st.map(s_, background=[("disabled", t["bg"]), ("pressed", t["toggle_on"]), ("selected", on), ("active", t["hover"])],
                   foreground=[("disabled", t["text2"]), ("pressed", t["text3"] if self.dark else t["text"]),
                               ("selected", t["text3"] if (self.dark and s_ != "AxesTool.TCheckbutton") else t["text"])])
        st.configure("Big.Tool.TButton", padding=(px(8), px(6)), font=f_small, anchor="center", justify="center")
        st.configure("Big.Tool.TCheckbutton", padding=(px(8), px(6)), font=f_small, anchor="center", justify="center")
        st.configure("Small.Tool.TButton", anchor="w", padding=(px(6), px(3)))
        st.configure("Small.Tool.TCheckbutton", anchor="w", padding=(px(6), px(3)))
        if qab:
            st.layout("Qab.TButton", tool_layout(qab, "Button"))
        st.configure("Qab.TButton", background=t["strip"], foreground=t["strip_text"], padding=(px(6), px(4)))
        st.map("Qab.TButton", background=[("disabled", t["strip"]), ("pressed", t["qab_active"]), ("active", t["qab_hover"])],
               foreground=[("disabled", t["strip_text_disabled"])])
        st.configure("TMenubutton", padding=(px(8), px(3)), background=t["bg"], foreground=t["text"], arrowcolor=t["text"])
        st.map("TMenubutton", background=[("active", t["hover"])])
        # --- 工具列分頁列（選中的分頁 = 主底色 + 主文字色；hover 另一色） ----
        st.configure("Strip.TFrame", background=t["strip"])
        st.configure("Strip.TLabel", background=t["strip"], foreground=t["strip_text"])
        tab_layout = [("Radiobutton.padding", {"sticky": "nswe", "children": [("Radiobutton.label", {"sticky": "nswe"})]})]
        st.layout("StripTab.TRadiobutton", tab_layout)
        st.configure("StripTab.TRadiobutton", background=t["strip"], foreground=t["strip_text"], font=f_small,
                     padding=(px(8), px(7)), anchor="center", width=11)
        st.map("StripTab.TRadiobutton", background=[("selected", t["bg"]), ("active", t["strip_hover"])],
               foreground=[("selected", t["text"]), ("disabled", t["strip_text_disabled"])])
        st.layout("Contextual.StripTab.TRadiobutton", tab_layout)          # 圖形視窗那種 contextual tab（底 #1171be）
        st.configure("Contextual.StripTab.TRadiobutton", background=t["strip_selected"], foreground=t["text3"], font=f_small,
                     padding=(px(8), px(7)), anchor="center", width=11)
        st.map("Contextual.StripTab.TRadiobutton", background=[("selected", t["bg"]), ("active", t["primary_hover"])],
               foreground=[("selected", t["text"])])
        # Windows 高 DPI（W10，NARROW_LAYOUT）：視窗比分頁列窄時改用的窄分頁鈕（字的寬度＋小邊距，不留 11 個字的固定寬）、
        # 工具列內容比視窗寬時兩端的捲動鈕。只是多定義幾個樣式；macOS 不會用到
        for s_, bg_, fg_, act_ in (("Compact.StripTab.TRadiobutton", t["strip"], t["strip_text"], t["strip_hover"]),
                                   ("Compact.Contextual.StripTab.TRadiobutton", t["strip_selected"], t["text3"], t["primary_hover"])):
            st.layout(s_, tab_layout)
            st.configure(s_, background=bg_, foreground=fg_, font=f_small, padding=(px(6), px(7)), anchor="center", width=0)
            st.map(s_, background=[("selected", t["bg"]), ("active", act_)],
                   foreground=[("selected", t["text"]), ("disabled", t["strip_text_disabled"])])
        for s_, bg_, fg_, on_, act_ in (("StripArrow.TButton", t["bg2"], t["text"], t["selected"], t["hover"]),
                                        ("StripArrowTab.TButton", t["strip"], t["strip_text"], t["qab_active"], t["strip_hover"])):
            if tool:
                st.layout(s_, tool_layout(tool, "Button"))
            st.configure(s_, background=bg_, foreground=fg_, padding=(0, 0), anchor="center", font=f_small, width=0)
            st.map(s_, background=[("pressed", on_), ("active", act_)])
        st.configure("Section.TLabel", font=f_small, foreground=t["text2"], anchor="center", padding=(px(3), 0))
        st.configure("StripBody.TFrame", background=t["bg"])
        # --- 面板 ---------------------------------------------------------------
        st.configure("PanelTitle.TFrame", background=t["bg3"])
        st.configure("PanelTitle.TLabel", background=t["bg3"], foreground=t["text"], font=f_title, padding=(px(6), 0))
        st.configure("PanelTitleSel.TFrame", background=t["panel_header_sel"])
        st.configure("PanelTitleSel.TLabel", background=t["panel_header_sel"], foreground=t["text3"], font=f_title, padding=(px(6), 0))
        if tool:
            st.layout("PanelTool.TButton", tool_layout(tool, "Button"))
            st.layout("PanelToolSel.TButton", tool_layout(tool, "Button"))
        st.configure("PanelTool.TButton", background=t["bg3"], padding=(px(5), px(3)))
        st.map("PanelTool.TButton", background=[("active", t["hover"]), ("pressed", t["toggle_on"])])
        st.configure("PanelToolSel.TButton", background=t["panel_header_sel"], foreground=t["text3"], padding=(px(5), px(3)))
        st.map("PanelToolSel.TButton", background=[("active", t["primary_hover"]), ("pressed", t["qab_active"])])
        st.configure("TLabelframe", background=t["bg"], bordercolor=t["border"], lightcolor=t["bg"], darkcolor=t["bg"],
                     borderwidth=1, relief="solid", padding=(px(8), px(6)))
        st.configure("TLabelframe.Label", background=t["bg"], foreground=t["text"], font=f_def)
        # --- 輸入 ---------------------------------------------------------------
        if field:
            st.layout("TEntry", [(field, {"sticky": "nswe", "children": [
                ("Entry.padding", {"sticky": "nswe", "children": [("Entry.textarea", {"sticky": "nswe"})]})]})])
            st.layout("TCombobox", [(field, {"sticky": "nswe", "children": [
                (down or "Combobox.downarrow", {"side": "right", "sticky": ""}),
                ("Combobox.padding", {"expand": "1", "sticky": "nswe", "children": [("Combobox.textarea", {"sticky": "nswe"})]})]})])
            st.layout("TSpinbox", [(field, {"sticky": "nswe", "children": [
                ("null", {"side": "right", "children": [
                    (up or "Spinbox.uparrow", {"side": "top", "sticky": "e"}), (down_s or "Spinbox.downarrow", {"side": "bottom", "sticky": "e"})]}),
                ("Spinbox.padding", {"sticky": "nswe", "children": [("Spinbox.textarea", {"sticky": "nswe"})]})]})])
        for s_ in ("TEntry", "TCombobox", "TSpinbox"):
            st.configure(s_, fieldbackground=t["input"], foreground=t["text"], insertcolor=t["text"], padding=(px(5), px(3)),
                         bordercolor=t["border"], lightcolor=t["input"], darkcolor=t["input"], arrowcolor=t["text"],
                         selectbackground=t["selected_focus"], selectforeground=t["text"], background=t["bg"])
            st.map(s_, fieldbackground=[("readonly", t["bg"]), ("disabled", t["bg2"]), ("invalid", mix(t["input"], t["error"], 0.12))],
                   foreground=[("disabled", t["text2"])], selectbackground=[("!focus", t["selected"])],
                   background=[("readonly", "active", t["hover"])], arrowcolor=[("disabled", t["text2"])],
                   bordercolor=[("invalid", t["error"])], lightcolor=[("invalid", t["error"])], darkcolor=[("invalid", t["error"])])
        st.configure("TCombobox", padding=(px(5), px(3), px(2), px(3)))
        # --- 核取／單選 -----------------------------------------------------------
        if check:
            st.layout("TCheckbutton", [("Checkbutton.padding", {"sticky": "nswe", "children": [
                (check, {"side": "left", "sticky": ""}), ("Checkbutton.label", {"side": "left", "sticky": "nswe"})]})])
        if radio:
            st.layout("TRadiobutton", [("Radiobutton.padding", {"sticky": "nswe", "children": [
                (radio, {"side": "left", "sticky": ""}), ("Radiobutton.label", {"side": "left", "sticky": "nswe"})]})])
        for s_ in ("TCheckbutton", "TRadiobutton"):
            st.configure(s_, background=t["bg"], foreground=t["text"], padding=(px(2), px(2)), indicatorcolor=t["input"],
                         indicatormargin=(0, 0, px(6), 0))
            st.map(s_, background=[("active", t["bg"])], foreground=[("disabled", t["text2"])],
                   indicatorcolor=[("selected", t["text"])])
        # --- 分頁群組（實測：分頁列 = bg2、選中分頁 = bg、框 = border2） -------------------------
        st.configure("TNotebook", background=t["bg"], bordercolor=t["border2"], lightcolor=t["bg"], darkcolor=t["bg"],
                     tabmargins=(0, 0, 0, 0), borderwidth=1, tabposition="nw")
        st.layout("TNotebook.Tab", [("Notebook.tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [("Notebook.label", {"side": "top", "sticky": ""})]})]})])
        st.configure("TNotebook.Tab", background=t["tab"], foreground=t["text"], padding=(px(12), px(2)), bordercolor=t["border2"],
                     lightcolor=t["tab"], darkcolor=t["tab"], font=f_def, focuscolor=t["tab"])
        st.map("TNotebook.Tab", background=[("selected", t["tab_selected"]), ("active", t["hover"])],
               lightcolor=[("selected", t["tab_selected"])], darkcolor=[("selected", t["tab_selected"])],
               foreground=[("disabled", t["text2"])], expand=[("selected", (0, 0, 0, 0))])
        # --- 樹／表格 -------------------------------------------------------------
        st.configure("Treeview", background=t["input"], fieldbackground=t["input"], foreground=t["text"], rowheight=px(PX["row_h"]),
                     bordercolor=t["border2"], lightcolor=t["input"], darkcolor=t["input"], borderwidth=0, relief="flat", font=f_def)
        st.map("Treeview", background=[("selected", t["selected"])], foreground=[("selected", t["text_selected"])])
        st.configure("Treeview.Heading", background=t["bg"], foreground=t["text"], font=f_bold, relief="flat", padding=(px(4), px(3)),
                     bordercolor=t["border2"], lightcolor=t["bg"], darkcolor=t["bg"])
        st.map("Treeview.Heading", background=[("active", t["hover"]), ("pressed", t["bg2"])], relief=[("pressed", "flat")])
        st.layout("Treeview.Item", [("Treeitem.padding", {"sticky": "nswe", "children": [
            (tri or "Treeitem.indicator", {"side": "left", "sticky": ""}), ("Treeitem.image", {"side": "left", "sticky": ""}),
            ("Treeitem.text", {"side": "left", "sticky": ""})]})])
        st.configure("Treeview.Item", indicatorsize=px(10), indicatormargins=(px(4), px(2), px(6), px(2)))
        st.configure("Treeview", indent=px(18))
        # --- 捲軸（圖片元素才有寬度；clam 的寬度是靠箭頭撐的）／滑桿／分隔 ----------------------------
        if vtrough and vthumb:
            st.layout("Vertical.TScrollbar", [(vtrough, {"sticky": "ns", "children": [(vthumb, {"expand": "1", "sticky": "nswe"})]})])
        if htrough and hthumb:
            st.layout("Horizontal.TScrollbar", [(htrough, {"sticky": "we", "children": [(hthumb, {"expand": "1", "sticky": "nswe"})]})])
        for s_ in ("Vertical.TScrollbar", "Horizontal.TScrollbar", "TScrollbar"):
            st.configure(s_, background=t["scroll"], troughcolor=t["bg"], bordercolor=t["bg"], lightcolor=t["scroll"],
                         darkcolor=t["scroll"], arrowsize=sw, gripcount=0, width=sw, relief="flat", borderwidth=0)
            st.map(s_, background=[("pressed", t["scroll_active"]), ("active", t["scroll_hover"])],
                   lightcolor=[("pressed", t["scroll_active"]), ("active", t["scroll_hover"])],
                   darkcolor=[("pressed", t["scroll_active"]), ("active", t["scroll_hover"])])
        if s_tr and s_sl:
            st.layout("Horizontal.TScale", [(s_tr, {"sticky": "we", "children": [(s_sl, {"side": "left", "sticky": ""})]})])
        st.configure("Horizontal.TScale", background=t["text2"], troughcolor=t["border2"], bordercolor=t["border2"],
                     lightcolor=t["text2"], darkcolor=t["text2"], sliderlength=px(14), sliderthickness=px(14), borderwidth=0)
        st.map("Horizontal.TScale", background=[("active", t["text"])], lightcolor=[("active", t["text"])], darkcolor=[("active", t["text"])])
        st.configure("TSeparator", background=t["border2"])
        st.configure("TPanedwindow", background=t["bg"])
        st.configure("Sash", sashthickness=px(PX["sash"]), gripcount=0, background=t["bg"], bordercolor=t["bg"],
                     lightcolor=t["bg"], darkcolor=t["bg"], sashpad=0, handlesize=0)
        st.configure("TProgressbar", background=t["accent"], troughcolor=t["bg2"], bordercolor=t["bg2"], lightcolor=t["accent"], darkcolor=t["accent"])
        self._built = True

    # --- 啟用（每次切換都做：theme_use、字型、option database、根視窗底色） -----------------
    def activate(self) -> None:
        t = self.t
        self.build()
        try:
            self.style.theme_use(f"plotkit-{self.name}")
        except Exception:
            pass
        self._make_fonts()
        f_def = self.fonts["default"]
        px = self.px
        od = self.root.option_add
        od("*TCombobox*Listbox.background", t["input"])
        od("*TCombobox*Listbox.foreground", t["text"])
        od("*TCombobox*Listbox.selectBackground", t["selected_focus"])
        od("*TCombobox*Listbox.selectForeground", t["text"])
        od("*TCombobox*Listbox.font", f_def)
        od("*TCombobox*Listbox.borderWidth", 1)
        od("*TCombobox*Listbox.relief", "solid")
        for cls in ("Text", "Listbox", "Entry", "Spinbox"):
            od(f"*{cls}.background", t["input"])
            od(f"*{cls}.foreground", t["text"])
            od(f"*{cls}.selectBackground", t["selected_focus"])
            od(f"*{cls}.selectForeground", t["text"])
            od(f"*{cls}.highlightThickness", 0)
            od(f"*{cls}.borderWidth", 0)
            od(f"*{cls}.relief", "flat")
        for cls in ("Text", "Entry", "Spinbox"):
            od(f"*{cls}.insertBackground", t["text"])
            od(f"*{cls}.inactiveSelectBackground", t["selected"])
        od("*Listbox.selectBorderWidth", 0)
        od("*Listbox.activeStyle", "none")
        od("*Text.padX", px(8))
        od("*Text.padY", px(6))
        for cls in ("Frame", "Toplevel", "Label", "Canvas", "Checkbutton", "Radiobutton", "Scale", "Message", "LabelFrame"):
            od(f"*{cls}.background", t["bg"])
        for cls in ("Label", "Checkbutton", "Radiobutton", "Message", "LabelFrame", "Scale"):
            od(f"*{cls}.foreground", t["text"])
        od("*Canvas.highlightThickness", 0)
        od("*Button.background", t["bg"])
        od("*Button.foreground", t["text"])
        od("*Button.activeBackground", t["hover"])
        od("*Button.activeForeground", t["text"])
        od("*Button.highlightThickness", 0)
        od("*Button.relief", "flat")
        od("*Menu.background", self.menu_bg)
        od("*Menu.foreground", t["text"])
        od("*Menu.activeBackground", t["selected_focus"])
        od("*Menu.activeForeground", self.menu_active_fg)
        od("*Menu.disabledForeground", t["text2"])
        od("*Menu.selectColor", t["text"])
        od("*Menu.borderWidth", 1)
        od("*Menu.activeBorderWidth", 0)
        od("*Menu.relief", "solid")
        od("*Menu.tearOff", 0)
        od("*Menu.font", f_def)
        od("*Scrollbar.background", t["scroll"])
        od("*Scrollbar.troughColor", t["bg"])
        try:
            self.root.configure(background=t["bg"])
        except Exception:
            pass

    @property
    def menu_bg(self) -> str:
        return self.t["bg2"] if self.dark else self.t["bg3"]

    @property
    def menu_active_fg(self) -> str:
        return self.t["text3"] if self.dark else self.t["text"]

    def restyle_tree(self, widget) -> None:
        """把已經建好的傳統 tk 元件重新上色（切換主題時用）。"""
        t = self.t
        try:
            cls = widget.winfo_class()
        except Exception:
            return
        opts: Dict[str, Any] = {}
        if cls in ("Text", "Entry", "Spinbox"):
            opts = dict(background=t["input"], foreground=t["text"], insertbackground=t["text"],
                        selectbackground=t["selected_focus"], selectforeground=t["text"])
        elif cls == "Listbox":
            opts = dict(background=t["input"], foreground=t["text"], selectbackground=t["selected_focus"],
                        selectforeground=t["text"])
        elif cls in ("Frame", "Toplevel", "Canvas", "Tk"):
            opts = dict(background=t["bg"])
        elif cls in ("Label", "Checkbutton", "Radiobutton", "Message"):
            opts = dict(background=t["bg"], foreground=t["text"])
        elif cls == "Button":
            opts = dict(background=t["bg"], foreground=t["text"], activebackground=t["hover"])
        elif cls == "Menu":
            opts = dict(background=self.menu_bg, foreground=t["text"], activebackground=t["selected_focus"],
                        activeforeground=self.menu_active_fg)
        if opts:
            try:
                widget.configure(**opts)
            except Exception:
                pass
        try:
            children = widget.winfo_children()
        except Exception:
            return
        for ch in children:
            self.restyle_tree(ch)


def get_theme(root, name: str) -> Theme:
    """這個 interpreter 的某個主題（沒有就建）。"""
    key = (_interp(root), name)
    th = _THEMES.get(key)
    if th is None:
        th = Theme(root, name)
        th.build()
        _THEMES[key] = th
    return th


def apply(root=None, name: str = DEFAULT_THEME) -> Theme:
    """啟用主題（第一次會建）。回傳 Theme；之後用 current() 取得。可重複呼叫切換。"""
    global _CURRENT
    if not HAVE_TK:
        raise RuntimeError("沒有 tkinter")
    if root is None:
        root = tk._get_default_root("apply theme")
    try:
        root = root.winfo_toplevel()
    except Exception:
        pass
    th = get_theme(root, name)
    th.activate()
    _CURRENT = th
    install_keep_on_screen(root)                 # Windows 高 DPI（W10）：新視窗整個放進工作區；macOS 不做任何事
    # 既有元件重新上色＋圖示換色
    try:
        th.restyle_tree(root)
    except Exception:
        pass
    for w, (iname, size, on_strip) in list(_ICON_WIDGETS.items()):
        try:
            if w.winfo_exists():
                img = th.icon(iname, size, on_strip=on_strip)
                if img is not None:
                    w.configure(image=img)
        except Exception:
            pass
    for obj in list(_LISTENERS):
        try:
            obj.on_theme(th)
        except Exception:
            pass
    return th


def current() -> Optional[Theme]:
    return _CURRENT


def ensure(root=None) -> Theme:
    """目前的主題；還沒有（或 root 是另一個 interpreter）就用預設主題建。"""
    if _CURRENT is not None:
        if root is None or _interp(root) == _CURRENT.interp:
            return _CURRENT
        return apply(root, _CURRENT.name)
    return apply(root, DEFAULT_THEME)


def listen(obj) -> None:
    """obj.on_theme(theme) 會在切換主題時被叫。"""
    _LISTENERS.add(obj)


def color(key: str, default: Optional[str] = None) -> str:
    th = _CURRENT
    if th is None:
        return TOKENS[DEFAULT_THEME].get(key, default or "#000000")
    return th.t.get(key, default or "#000000")


def plot_style_name() -> str:
    return color("plot_style", "matlab-dark")


# ---------------------------------------------------------------------------
# 工具提示
# ---------------------------------------------------------------------------
class Tooltip:
    """滑鼠停 600 ms 後在元件下方顯示；離開、按下、視窗縮小或失焦就收；不會超出螢幕。元件被刪掉（關視窗）時也取消排著的顯示：
    <Destroy> 在 Tcl 刪元件的當下觸發、Python 還沒刪掉這個元件的 Tcl 指令，取消得到——不然停在元件上 600 ms 內關窗，時間到時找不到
    已刪掉的 …_show 指令，會跳 Tk 的背景錯誤對話框。"""

    def __init__(self, widget, text: str, delay: int = 600):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._job = None
        self._win = None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<ButtonPress>", self._leave, add="+")
        widget.bind("<Destroy>", self._leave, add="+")
        try:
            top = widget.winfo_toplevel()
            top.bind("<Unmap>", self._leave, add="+")
            top.bind("<FocusOut>", self._leave, add="+")
        except Exception:
            pass

    def _enter(self, e=None):
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _leave(self, e=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None

    def _show(self):
        self._job = None
        if self._win is not None or not self.text:
            return
        try:
            if not self.widget.winfo_viewable():
                return
            th = current()
            bg = th["bg3"] if th and not th.dark else (th["bg2"] if th else "#333333")
            fg = th["text"] if th else "#d9d9d9"
            bd = th["border"] if th else "#7d7d7d"
            w = tk.Toplevel(self.widget)
            w.wm_overrideredirect(True)
            w.configure(background=bd)
            lbl = tk.Label(w, text=self.text, background=bg, foreground=fg, justify="left",
                           font=th.font("default") if th else None, padx=6, pady=3)
            lbl.pack(padx=1, pady=1)
            w.update_idletasks()
            x = self.widget.winfo_rootx() + 8
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            sw, sh = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()
            ww, wh = w.winfo_reqwidth(), w.winfo_reqheight()
            x = max(0, min(x, sw - ww - 4))
            if y + wh > sh - 4:
                y = self.widget.winfo_rooty() - wh - 4
            w.wm_geometry(f"+{x}+{y}")
            self._win = w
        except Exception:
            self._win = None

    def _hide(self):
        if self._win is not None:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None


def tooltip(widget, text: Optional[str]):
    """掛一個 tooltip；物件放在 widget._tooltip、文字放在 widget._pk_tip（測試和診斷可以讀到）。沒有文字就不掛。"""
    if not text:
        return None
    tip = Tooltip(widget, text)
    try:
        widget._tooltip = tip
        widget._pk_tip = text
    except Exception:
        pass
    return tip


# ---------------------------------------------------------------------------
# 面板（MATLAB 的 Current Folder／Workspace 那種：23px 標題列＋1px 框＋可收合）
# ---------------------------------------------------------------------------
class Panel(tk.Frame if HAVE_TK else object):
    """`.body` 是放內容的 ttk.Frame；標題列右邊可以放小工具按鈕；點標題列會變成「被選面板」（藍底白字）。"""

    def __init__(self, master, title: str, *, collapsible: bool = True, tools: Sequence[Tuple[str, str, Callable]] = (),
                 selectable: bool = True, **kw):
        th = ensure(master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else None)
        tk.Frame.__init__(self, master, background=th["border"], highlightthickness=0, borderwidth=0, **kw)
        self.th = th
        self.title_var = tk.StringVar(value=title)
        self._collapsed = False
        self._selected = False
        self._selectable = selectable
        self._collapsible = collapsible
        self._tools: List[Tuple[Any, str]] = []
        self.on_double: Optional[Callable[[], None]] = None     # 雙擊標題列（Dock 用來最大化；沒設就是收合／展開）
        self._menu_btn = None
        self._menu_cb: Optional[Callable[[Any], None]] = None
        self._inner = ttk.Frame(self)
        self._inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.header = ttk.Frame(self._inner, style="PanelTitle.TFrame", height=th.px(PX["panel_title_h"]))
        self.header.pack(side="top", fill="x")
        self.header.pack_propagate(False)
        self.label = ttk.Label(self.header, textvariable=self.title_var, style="PanelTitle.TLabel", anchor="w")
        self.label.pack(side="left", fill="y")
        self._hline = ttk.Frame(self._inner, style="Border2.TFrame", height=1)
        self._hline.pack(side="top", fill="x")
        self.body = ttk.Frame(self._inner)
        self.body.pack(side="top", fill="both", expand=True)
        self._collapse_btn = None
        if collapsible:
            self._collapse_btn = ttk.Button(self.header, style="PanelTool.TButton", command=self.toggle, takefocus=0)
            if not th.bind_icon(self._collapse_btn, "expand", 12):
                self._collapse_btn.configure(text="⌄")
            self._collapse_btn.pack(side="right", padx=(0, th.px(4)))
            tooltip(self._collapse_btn, tr("收合／展開"))
        for icon_name, tip, cmd in tools:
            self.add_tool(icon_name, tip, cmd)
        for w in (self.header, self.label):
            w.bind("<Button-1>", lambda e: self.select(True), add="+")
            w.bind("<Double-Button-1>", lambda e: self._dbl(), add="+")
        listen(self)

    def _dbl(self) -> None:
        if self.on_double is not None:
            self.on_double()
        elif self._collapsible:
            self.toggle()

    def set_menu(self, callback: Callable[[Any], None]) -> None:
        """標題列加一個 ▾ 選單鈕（像 MATLAB 面板的 ▾），右鍵（macOS 也可 Control＋點）標題列也會叫 callback(event)。"""
        self._menu_cb = callback
        if self._menu_btn is None:
            self._menu_btn = ttk.Button(self.header, style="PanelTool.TButton", command=lambda: callback(None), takefocus=0)
            if not self.th.bind_icon(self._menu_btn, "menu", 12):
                self._menu_btn.configure(text="▾")
            self._menu_btn.pack(side="right", padx=(0, self.th.px(2)))
            tooltip(self._menu_btn, tr("面板選單；拖曳標題列可以把面板搬到別欄"))
            self._tools.append((self._menu_btn, "menu"))
            for w in (self.header, self.label):
                w.bind("<Button-3>", lambda e: callback(e), add="+")
                if IS_MAC:
                    w.bind("<Button-2>", lambda e: callback(e), add="+")
                    w.bind("<Control-Button-1>", lambda e: callback(e), add="+")

    def add_tool(self, icon_name: str, tip: str, command: Callable):
        b = ttk.Button(self.header, style="PanelTool.TButton", command=command, takefocus=0)
        if not self.th.bind_icon(b, icon_name, 14):
            b.configure(text=(tip or icon_name)[:2])
        b.pack(side="right", padx=(0, self.th.px(2)))
        tooltip(b, tip)
        self._tools.append((b, icon_name))
        return b

    def set_title(self, title: str) -> None:
        self.title_var.set(title)

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def collapse(self, flag: bool = True) -> None:
        if flag == self._collapsed:
            return
        self._collapsed = flag
        if flag:
            self.body.pack_forget()
            self._hline.pack_forget()
        else:
            self._hline.pack(side="top", fill="x")
            self.body.pack(side="top", fill="both", expand=True)
        if self._collapse_btn is not None:
            self.th.bind_icon(self._collapse_btn, "collapse" if flag else "expand", 12)
        self.event_generate("<<PanelToggle>>")

    def toggle(self) -> None:
        if self._collapsible:
            self.collapse(not self._collapsed)

    def select(self, flag: bool = True) -> None:
        if not self._selectable:
            return
        if flag:
            top = self.winfo_toplevel()
            for p in _panels_in(top):
                if p is not self and p._selected:
                    p.select(False)
        self._selected = flag
        self.header.configure(style="PanelTitleSel.TFrame" if flag else "PanelTitle.TFrame")
        self.label.configure(style="PanelTitleSel.TLabel" if flag else "PanelTitle.TLabel")
        for b, _ in self._tools:
            b.configure(style="PanelToolSel.TButton" if flag else "PanelTool.TButton")
        if self._collapse_btn is not None:
            self._collapse_btn.configure(style="PanelToolSel.TButton" if flag else "PanelTool.TButton")

    def on_theme(self, th: Theme) -> None:
        self.th = th
        try:
            self.configure(background=th["border"])
            self.header.configure(height=th.px(PX["panel_title_h"]))
        except Exception:
            pass


class _DockColumn(ttk.PanedWindow if HAVE_TK else object):
    """Dock 的一欄（直式 PanedWindow）。sashpos(i, 新位置) 不是 Dock 自己在重排（_rebuild／_fit_collapsed／_keep_fixed_room／_apply_sashes）時叫的，
    就當成使用者自己設的分隔線（Dock._user_sash；W14R2-3）——滑鼠拖的另外由 <ButtonPress-1>／<ButtonRelease-1> 認（ttk 的拖曳在 Tcl 層直接改，不經過這裡）。"""

    def __init__(self, dock, column: str, **kw):
        ttk.PanedWindow.__init__(self, dock, **kw)
        self._dock, self._column = dock, column

    def sashpos(self, index, newpos=None):
        r = ttk.PanedWindow.sashpos(self, index, newpos)
        if newpos is not None and not getattr(self._dock, "_auto_sash", 0):
            self._dock._user_sash[self._column] = True
        return r


class Dock(ttk.Frame if HAVE_TK else object):
    """MATLAB 桌面式可調版面：三欄（left／center／right），每欄一個直式 PanedWindow。面板可以移到任一欄、上下排序、
    收合、最大化（雙擊標題列）、隱藏；欄寬與欄內的分隔線可以拖；layout()／apply() 存讀（DSV 記在自動存檔）。
    面板與欄都建成 Dock 的直接子元件：ttk PanedWindow 接受同層的面板當 pane，所以面板可以在欄之間搬。"""

    COLUMNS = ("left", "center", "right")

    def __init__(self, master, *, col_weights: Tuple[int, int, int] = (0, 1, 0), **kw):
        ttk.Frame.__init__(self, master, **kw)
        self.th = ensure(master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else None)
        self.h = ttk.PanedWindow(self, orient="horizontal")
        self.h.pack(fill="both", expand=True)
        self._center_job = None
        self._fixed_job = None
        if NARROW_LAYOUT:                        # Windows（W10）：視窗變窄時中欄（圖）不被擠到 0（_keep_center_room）
            self.h.bind("<Configure>", self._keep_center_room_later, add="+")
        self._user_sash: Dict[str, bool] = {}    # 使用者自己拖過（或存檔還原）分隔線的欄（W14R2-3）：視窗大小改變時不套最小高度，下一次重排才重新檢查
        self._auto_sash = 0                      # >0＝Dock 自己在設分隔線（_DockColumn.sashpos 不算成使用者的）
        self._sash_before: Optional[Tuple[str, List[int]]] = None
        self.cols: Dict[str, Any] = {c: _DockColumn(self, c, orient="vertical") for c in self.COLUMNS}
        for c, col in self.cols.items():         # 滑鼠拖分隔線（ttk 在 Tcl 層改位置）：按下、放開時比對位置，變了就是使用者拖的
            col.bind("<ButtonPress-1>", lambda e, c=c: self._sash_press(c), add="+")
            col.bind("<ButtonRelease-1>", lambda e, c=c: self._sash_release(c), add="+")
        if NARROW_LAYOUT:                        # Windows（W10）：中欄的圖不被同欄的面板（量測）擠到 unmap（_keep_fixed_room）
            self.cols["center"].bind("<Configure>", self._keep_fixed_room_later, add="+")
        self.col_weight = dict(zip(self.COLUMNS, col_weights))
        self.panels: Dict[str, Panel] = {}
        self.order: Dict[str, List[str]] = {c: [] for c in self.COLUMNS}
        self.home: Dict[str, str] = {}
        self.weights: Dict[str, int] = {}
        self.fixed: set = set()
        self.hidden: set = set()
        self.default_hidden: set = set()     # 預設隱藏的面板（add(hidden=True)）：舊版存的版面裡沒有它時也維持隱藏
        self.max_key: Optional[str] = None
        self._max_saved: Optional[dict] = None
        self._default: Optional[dict] = None
        self._pending_sash: Optional[dict] = None
        self.on_change: Optional[Callable[[], None]] = None
        self._drag: Optional[dict] = None
        self._ind = None
        self._quiet_toggle = False               # apply() 一次設好多個面板的收合：不要每個都重排
        self._auto_widened: Dict[str, Tuple[int, int]] = {}   # 為了放得下新顯示的面板而自動加寬的欄：{欄: (原寬, 加寬後)}，面板再隱藏就還原
        try:
            self.winfo_toplevel().bind("<Escape>", lambda e: self._drag_cancel(), add="+")
        except Exception:
            pass

    # --- 使用者自己拖的分隔線（W14R2-3；2026-10-31 15:3x 使用者決定：使用者自己拖的分隔線位置不動，只有版面自己擠壓時才保留最小高度）----------
    def _sash_positions(self, c: str) -> List[int]:
        try:
            col = self.cols[c]
            return [int(ttk.PanedWindow.sashpos(col, i)) for i in range(len(col.panes()) - 1)]
        except Exception:
            return []

    def _sash_press(self, c: str) -> None:
        self._sash_before = (c, self._sash_positions(c))

    def _sash_release(self, c: str) -> None:
        before, self._sash_before = self._sash_before, None
        if before and before[0] == c and before[1] != self._sash_positions(c):
            self._user_sash[c] = True

    def user_moved_sash(self, c: str = "center") -> bool:
        """這一欄的分隔線現在是不是使用者自己設的（拖過、或從存檔還原的）——下一次重排（_rebuild）之前都算。"""
        return bool(self._user_sash.get(c))

    # --- 註冊 ------------------------------------------------------------------
    def add(self, key: str, panel: Panel, column: str = "center", *, weight: int = 0, fixed: bool = False, menu: bool = True,
            hidden: bool = False) -> None:
        self.panels[key] = panel
        if hidden and not fixed:
            self.hidden.add(key)
            self.default_hidden.add(key)
        self.home[key] = column
        self.weights[key] = int(weight)
        if fixed:
            self.fixed.add(key)
        self.order[column].append(key)
        if menu:
            panel.set_menu(lambda e=None, k=key: self.post_menu(k, e))
            panel.on_double = lambda k=key: self.toggle_max(k)
        if not fixed:
            self._bind_drag(key, panel)
        panel.bind("<<PanelToggle>>", lambda e, k=key: self._on_panel_toggle(k), add="+")
        self._rebuild()

    def _on_panel_toggle(self, key: str) -> None:
        """面板收合／展開：收合的面板只留標題列高度、空出來的高度給同欄其他面板（像 MATLAB 把面板縮到標題列）；
        展開時重新分配。ttk PanedWindow 不會因為 pane 的 reqheight 變小就縮 pane，所以要重排＋設分隔線。"""
        if self._quiet_toggle or key in self.hidden or self.column_of(key) is None:
            return
        self._rebuild()

    def _fit_collapsed(self) -> None:
        """把收合的面板的 pane 高度壓到它的標題列（reqheight）：上面的面板往下推、最後一個收合就把上一條分隔線往下推。"""
        self._auto_sash += 1
        try:
            self.update_idletasks()
            for c in self.visible_columns():
                col = self.cols[c]
                panes = [self.nametowidget(str(p)) for p in col.panes()]
                n = len(panes)
                if n < 2:
                    continue
                H = col.winfo_height()
                for i, p in enumerate(panes):
                    if not getattr(p, "collapsed", False):
                        continue
                    h = p.winfo_reqheight()
                    if i < n - 1:
                        top = p.winfo_rooty() - col.winfo_rooty()
                        col.sashpos(i, max(0, top) + h)
                    else:
                        thick = max(0, (p.winfo_rooty() - col.winfo_rooty()) - col.sashpos(i - 1))   # 分隔線本身的厚度
                        col.sashpos(i - 1, H - h - thick)
        except Exception:
            pass
        finally:
            self._auto_sash -= 1

    def freeze_default(self) -> None:
        """現在的版面當作「預設版面」（恢復預設時用）。"""
        self._default = self.layout()
        self._default["sash"] = {}

    # --- 查詢 ------------------------------------------------------------------
    def column_of(self, key: str) -> Optional[str]:
        for c in self.COLUMNS:
            if key in self.order[c]:
                return c
        return None

    def visible_columns(self) -> List[str]:
        return [c for c in self.COLUMNS if any(k not in self.hidden for k in self.order[c])]

    # --- 操作 ------------------------------------------------------------------
    def move(self, key: str, column: str, index: Optional[int] = None) -> None:
        if key in self.fixed or column not in self.COLUMNS or key not in self.panels:
            return
        self.restore_max()                           # 最大化中改版面：先還原，不然還原時會被最大化前的版面蓋掉
        cur = self.column_of(key)
        if cur is not None:
            self.order[cur].remove(key)
        lst = self.order[column]
        if index is None:
            index = len(lst)
        index = max(0, min(index, len(lst)))
        if column == "center" and index == 0 and lst and lst[0] in self.fixed:
            index = 1                                # 圖固定在中欄最上面
        lst.insert(index, key)
        self._rebuild()

    def move_before(self, key: str, column: str, before: Optional[str]) -> None:
        """把面板放到 column 欄、before 這個面板的前面（None＝該欄最後）。"""
        if key in self.fixed or column not in self.COLUMNS or key not in self.panels:
            return
        self.restore_max()
        cur = self.column_of(key)
        if cur is not None:
            self.order[cur].remove(key)
        lst = self.order[column]
        idx = lst.index(before) if (before in lst and before != key) else len(lst)
        if column == "center" and idx == 0 and lst and lst[0] in self.fixed:
            idx = 1
        lst.insert(idx, key)
        self._rebuild()

    def _neighbor(self, key: str, delta: int) -> Optional[str]:
        """同一欄裡、跳過隱藏面板的上一個／下一個面板（固定面板不能跨過）；沒有就 None。"""
        c = self.column_of(key)
        if c is None or key in self.fixed:
            return None
        vis = [k for k in self.order[c] if k not in self.hidden or k == key]
        j = vis.index(key) + delta
        if j < 0 or j >= len(vis) or vis[j] in self.fixed:
            return None
        return vis[j]

    def shift(self, key: str, delta: int) -> None:
        """上移／下移一格（以看得到的面板為準：隱藏的面板不算一格，不然按了畫面沒變）。"""
        if self.max_key is not None:
            self.restore_max()
        other = self._neighbor(key, delta)
        if other is None:
            return
        lst = self.order[self.column_of(key)]
        lst.remove(key)
        j = lst.index(other)
        lst.insert(j if delta < 0 else j + 1, key)
        self._rebuild()

    def hide(self, key: str, flag: bool = True) -> None:
        if key in self.fixed or key not in self.panels:
            return
        if flag and self.max_key is not None:
            self.restore_max()                       # 最大化中隱藏（含隱藏最大化的那個）：先還原，不然整個 Dock 變空的
        if flag:
            self.hidden.add(key)
        else:
            self.hidden.discard(key)
        self._rebuild()

    def maximize(self, key: str) -> None:
        if key not in self.panels:
            return
        if self._max_saved is None:
            self._max_saved = self.layout()
        self.max_key = key
        self.hidden = {k for k in self.panels if k != key}
        self._rebuild()

    def restore_max(self) -> None:
        if self._max_saved is None:
            return
        saved, self._max_saved, self.max_key = self._max_saved, None, None
        self.apply(saved)

    def toggle_max(self, key: str) -> None:
        if self.max_key == key:
            self.restore_max()
        else:
            self.maximize(key)

    def reset(self) -> None:
        if self._default:
            self.apply(self._default)

    # --- 版面存讀 --------------------------------------------------------------
    def layout(self) -> dict:
        d = {"columns": {c: list(self.order[c]) for c in self.COLUMNS}, "hidden": sorted(self.hidden),
             "collapsed": [k for k, p in self.panels.items() if p.collapsed], "max": self.max_key, "sash": self._sashes()}
        if self._max_saved is not None:
            d["before_max"] = {k: v for k, v in self._max_saved.items() if k != "before_max"}
        return d

    def _sashes(self) -> dict:
        out: Dict[str, Any] = {}
        try:
            out["scale"] = self._ui_scale()          # 存檔時的 DPI 倍數（W14R3-1）：還原時倍數相同就照存的位置、不同才檢查最小高度
            out["h_cols"] = self.visible_columns()
            out["h"] = [int(self.h.sashpos(i)) for i in range(len(self.h.panes()) - 1)]
            for c, col in self.cols.items():
                out[c] = [int(col.sashpos(i)) for i in range(len(col.panes()) - 1)]
        except Exception:
            pass
        return out

    def apply(self, d: Optional[dict]) -> None:
        if not isinstance(d, dict):
            return
        cols = d.get("columns") or {}
        new: Dict[str, List[str]] = {c: [] for c in self.COLUMNS}
        seen: set = set()
        for c in self.COLUMNS:
            for k in (cols.get(c) or []):
                if k in self.panels and k not in seen:
                    new[c].append(k)
                    seen.add(k)
        unseen = set()
        for k in self.panels:
            if k not in seen:
                new[self.home.get(k, "center")].append(k)
                unseen.add(k)
        for k in self.fixed:
            for c in self.COLUMNS:
                if k in new[c]:
                    new[c].remove(k)
            new["center"].insert(0, k)
        self.order = new
        self.hidden = {k for k in (d.get("hidden") or []) if k in self.panels and k not in self.fixed}
        self.hidden |= unseen & self.default_hidden      # 存檔時還沒有這個面板（舊版版面）→ 照它的預設（隱藏）
        self.max_key, self._max_saved = None, None
        collapsed = set(d.get("collapsed") or [])
        self._quiet_toggle = True
        try:
            for k, p in self.panels.items():
                try:
                    p.collapse(k in collapsed)
                except Exception:
                    pass
        finally:
            self._quiet_toggle = False
        self._rebuild()
        mk, bm = d.get("max"), d.get("before_max")
        if mk in self.panels and isinstance(bm, dict):
            self._max_saved = bm
            self.max_key = mk
            self.hidden = {k for k in self.panels if k != mk}
            self._rebuild()
        self._pending_sash = d.get("sash") or None
        self._auto_widened.clear()                      # 套用版面＝使用者的欄寬，不再算「為新面板自動加寬」
        if self._pending_sash:
            self.after_idle(self._apply_sashes)

    def set_widths(self, left: Optional[int] = None, right: Optional[int] = None) -> None:
        """預設欄寬（像素）：左欄從左邊算、右欄從右邊算；沒有那一欄就略過。"""
        self._auto_widened.clear()
        try:
            vis = self.visible_columns()
            w = self.h.winfo_width()
            n = len(vis)
            if n < 2 or w < 50:
                return
            if left is not None and vis[0] == "left":
                self.h.sashpos(0, int(left))
            if right is not None and vis[-1] == "right":
                self.h.sashpos(n - 2, int(w - right))
        except Exception:
            pass

    def _apply_sashes(self, tries: int = 0) -> None:
        """套用存下的分隔線位置。ttk PanedWindow 在 pane 重新加入後要等它自己排版過才吃得下 sashpos，
        所以設完讀回來比對，不對就隔 100 ms 再試（最多 10 次）。"""
        s = self._pending_sash
        if not s:
            return
        if (self.h.winfo_width() < 50 or self.h.winfo_height() < 50) and tries < 30:
            self.after(100, lambda: self._apply_sashes(tries + 1))
            return
        ok = True
        applied: List[str] = []
        self._auto_sash += 1
        try:
            self.update_idletasks()
            if list(s.get("h_cols") or []) == self.visible_columns():
                for i, v in enumerate(s.get("h") or []):
                    if i < len(self.h.panes()) - 1:
                        self.h.sashpos(i, int(v))
                        ok = ok and abs(int(self.h.sashpos(i)) - int(v)) <= 2
            for c, col in self.cols.items():
                for i, v in enumerate(s.get(c) or []):
                    if i < len(col.panes()) - 1:
                        col.sashpos(i, int(v))
                        ok = ok and abs(int(col.sashpos(i)) - int(v)) <= 2
                        applied.append(c)
        except Exception:
            ok = False
        finally:
            self._auto_sash -= 1
        if not ok and tries < 10:
            self.after(100, lambda: self._apply_sashes(tries + 1))
            return
        self._pending_sash = None
        if NARROW_LAYOUT and "center" in applied and not self._same_scale(s.get("scale")):
            # 存檔記的 DPI 倍數和現在不同（或存檔沒記倍數：0.9.13 留的）＝ DPI 造成的擠壓：套用後檢查一次最小高度（現在一次、量測面板換好行之後再一次）；
            # 倍數相同就照存的位置還原、不推回（2026-11-01 12:0x 主 session 照建議，W14R3-1：使用者 100% 存 70 px、100% 重開仍 70 px，0.9.13 也是這樣）
            self._keep_fixed_room(relayout=True)
            try:
                self._root().after(300, lambda: self._keep_fixed_room(relayout=True))
            except Exception:
                pass
        for c in applied:
            self._user_sash[c] = True                # 存檔還原的分隔線＝使用者設的：之後視窗大小改變照它（0.9.13）、下一次重排才重新檢查

    def _ui_scale(self) -> float:
        """介面倍數（Theme.scale：Windows＝DPI／96，Mac 1.0）；沒有 Theme 時 1.0。"""
        try:
            return round(float(self.th.scale), 4) if self.th is not None else 1.0
        except Exception:
            return 1.0

    def _same_scale(self, saved) -> bool:
        """版面存檔記的 DPI 倍數（Dock.layout()["sash"]["scale"]）和現在一樣嗎（W14R3-1）；沒記（0.9.13 以前的存檔）、不是數字＝不一樣（照舊檢查一次）。"""
        try:
            return saved is not None and not isinstance(saved, bool) and abs(float(saved) - self._ui_scale()) <= 0.01
        except (TypeError, ValueError):
            return False

    def _nudge(self) -> None:
        """ttk PanedWindow 只在收到 <Configure> 時重算 pane 位置：pane 拿掉再加回去而大小沒變時不會重排
        （新加的 pane 會留在位置 0、沒 map）。排版後補一個 <Configure> 讓它重算。"""
        try:
            self.update_idletasks()
            for pw in [self.h] + [self.cols[c] for c in self.visible_columns()]:
                pw.event_generate("<Configure>", width=pw.winfo_width(), height=pw.winfo_height(), when="now")
        except Exception:
            pass

    # --- 重排 ------------------------------------------------------------------
    NEW_PANE_SHARE = 0.45        # 新顯示的面板最多拿欄高的這個比例（其餘面板照原本的比例分剩下的）
    MIN_PANE_H = 60              # 既有面板重分配後至少留這麼高（像素）
    MAX_COL_SHARE = 0.45         # 自動加寬的欄最多到視窗寬的這個比例

    def _geometry_snapshot(self) -> Optional[dict]:
        """重排前記下現在的幾何：可見欄、橫向分隔線、每欄各 pane 的高度（照 pane 實際清單，不看 hidden 集合）。"""
        try:
            if self.h.winfo_width() < 50 or self.h.winfo_height() < 50 or not self.winfo_ismapped():
                return None                      # 視窗沒顯示（最小化、還沒 map、無桌面）：量到的不是真的版面，不還原
            names = {str(p): k for k, p in self.panels.items()}
            snap: Dict[str, Any] = {"cols": self.visible_columns(), "W": self.h.winfo_width(),
                                    "h": [int(self.h.sashpos(i)) for i in range(len(self.h.panes()) - 1)], "panes": {}}
            for c, col in self.cols.items():
                keys = [names.get(str(p)) for p in col.panes()]
                snap["panes"][c] = {k: self.panels[k].winfo_height() for k in keys if k in self.panels and self.panels[k].winfo_ismapped()}
            return snap
        except Exception:
            return None

    def _col_width(self, c: str) -> int:
        vis = self.visible_columns()
        n = len(vis)
        W = self.h.winfo_width()
        if n < 2:
            return W
        if c == vis[0]:
            return int(self.h.sashpos(0))
        if c == vis[-1]:
            return W - int(self.h.sashpos(n - 2))
        return int(self.h.sashpos(vis.index(c))) - int(self.h.sashpos(vis.index(c) - 1))

    def _set_col_width(self, c: str, w: int) -> None:
        vis = self.visible_columns()
        n = len(vis)
        W = self.h.winfo_width()
        if n < 2:
            return
        if c == vis[0]:
            self.h.sashpos(0, int(w))
        elif c == vis[-1]:
            self.h.sashpos(n - 2, int(W - w))

    def _restore_geometry(self, prev: Optional[dict]) -> None:
        """ttk PanedWindow 把 pane 拿掉再加回去會全部照 reqwidth／reqheight 重排（左欄跳到 532、已繪訊號被壓到 49 px）。
        這裡把重排前的幾何接回來：欄沒變就還原橫向分隔線；欄裡多了一個面板就讓它拿最多 45% 的欄高、其餘照原比例；
        少了一個面板就把高度照原比例還給剩下的；新面板比欄寬時把欄加寬（左／右欄），面板再隱藏就把欄寬還原。"""
        if not prev:
            return
        self._auto_sash += 1
        try:
            self.update_idletasks()
            vis = self.visible_columns()
            W = self.h.winfo_width()
            same_cols = vis == prev["cols"] and len(prev["h"]) == len(self.h.panes()) - 1
            if same_cols:
                for i, v in enumerate(prev["h"]):
                    self.h.sashpos(i, int(v))
            for c in vis:
                if c not in prev["panes"] or c not in prev["cols"]:
                    continue
                ph: Dict[str, int] = prev["panes"][c]
                if not ph:
                    continue                     # 這欄原本沒有量到任何面板（都沒 map）：交給 ttk 預設
                now = [k for k in self.order[c] if k not in self.hidden]
                new_keys = [k for k in now if k not in ph]
                gone = [k for k in ph if k not in now]
                if c != "center" and same_cols and len(vis) >= 2:
                    # 欄寬：以重排前的為準（prev["h"]），新面板比欄寬才加寬；它再被隱藏就還原
                    i = vis.index(c)
                    cur = int(prev["h"][0]) if i == 0 else (int(prev["W"]) - int(prev["h"][-1]) if i == len(vis) - 1 else None)
                    if cur is not None:
                        if new_keys:
                            need = max(self.panels[k].winfo_reqwidth() for k in new_keys)
                            if need > cur + 4:
                                target = min(need, int(W * self.MAX_COL_SHARE))
                                if target > cur:
                                    self._set_col_width(c, target)
                                    self._auto_widened[c] = (cur, target)
                        elif gone and c in self._auto_widened:
                            cur0, target = self._auto_widened.pop(c)
                            if abs(cur - target) <= 6:
                                self._set_col_width(c, cur0)
                if not new_keys and not gone:
                    continue
                col = self.cols[c]
                n = len(now)
                if n < 2:
                    continue
                self.update_idletasks()
                H = col.winfo_height()
                panes = [self.panels[k] for k in now]
                thick = max(0, (panes[1].winfo_rooty() - col.winfo_rooty()) - int(col.sashpos(0)))
                avail = H - thick * (n - 1)
                if avail < self.MIN_PANE_H * n:
                    continue
                hs: Dict[str, float] = {}
                for k in new_keys:
                    p = self.panels[k]
                    want = p.winfo_reqheight() if not getattr(p, "collapsed", False) else p.winfo_reqheight()
                    hs[k] = min(want, avail * self.NEW_PANE_SHARE)
                rem = avail - sum(hs.values())
                old = [k for k in now if k in ph]
                tot = sum(ph[k] for k in old) or 1
                for k in old:
                    hs[k] = max(self.MIN_PANE_H, rem * ph[k] / tot)
                scale = avail / max(1.0, sum(hs.values()))
                y = 0.0
                for i, k in enumerate(now[:-1]):
                    y += hs[k] * scale
                    col.sashpos(i, int(round(y)))
                    y += thick
        except Exception:
            pass
        finally:
            self._auto_sash -= 1

    CENTER_MIN_SHARE = 0.45      # NARROW_LAYOUT（Windows）：中欄（圖）至少留 Dock 寬的這個比例

    def _keep_center_room(self, event=None) -> None:
        """NARROW_LAYOUT（Windows，W10）：欄變多（例如資料游標的讀數面板第一次出現在右欄）時 ttk PanedWindow 照 reqwidth 重排，
        視窗窄的時候（175% 直立螢幕 Dock 只有 990 px）左欄拿走 926 px、中欄（圖）剩不到 15 px，ttk 把中欄的 pane 整個 unmap——
        圖不見、關掉讀數也回不來（0.9.14 在使用者的 PC 上量到；0.9.13 也一樣）。視窗變窄時中欄（weight 1）也是先被縮。
        中欄比 Dock 寬的 45% 窄時，左右欄照它們要的寬度（reqwidth）比例分剩下的，中欄至少留 45%。Mac 不做（照舊）。"""
        if not NARROW_LAYOUT:
            return
        try:
            vis = self.visible_columns()
            if "center" not in vis or len(vis) < 2:
                return
            W = self.h.winfo_width()
            if W < 100:
                return
            n = len(vis)
            edges = [0] + [int(self.h.sashpos(i)) for i in range(n - 1)] + [W]
            width = {c: edges[i + 1] - edges[i] for i, c in enumerate(vis)}
            need = int(W * self.CENTER_MIN_SHARE)
            if width["center"] >= need:
                return
            sides = [c for c in vis if c != "center"]
            req = {c: max(1, self.cols[c].winfo_reqwidth()) for c in sides}
            room = max(0, W - need)
            tot = float(sum(req.values()))
            new = {c: min(req[c], int(room * req[c] / tot)) for c in sides}
            if vis[0] == "left":
                self.h.sashpos(0, new["left"])
            if vis[-1] == "right":
                self.h.sashpos(n - 2, W - new["right"])
        except Exception:
            pass

    CENTER_FIXED_MIN_PX = 160    # NARROW_LAYOUT（Windows）：中欄最上面的固定面板（圖）至少留這麼高（照 DPI 放大；不超過欄高的一半）

    def _keep_fixed_room(self, event=None, relayout: bool = False) -> None:
        """NARROW_LAYOUT（Windows，W10）：中欄最上面的固定面板（圖）被同一欄的面板（量測）擠得比 CENTER_FIXED_MIN_PX（照 DPI 放大；不超過欄高的一半）
        還矮、或整個被 ttk unmap 時，把分隔線往下推：圖至少留這麼高，其他面板照原本的高度比例分剩下的（量測表照樣可以捲動）。
        第一輪 Windows 驗證 W14-2：1920×1080、175%（模擬）時量測面板開著再打開兩條資料游標——右欄出現、重排時中欄先被擠窄，量測面板的工具列換行、
        要的高度變大，ttk 照要的高度分，圖只剩 1 px 被 unmap（圖不見），關掉游標也回不來。
        什麼時候檢查（W14R2-3，2026-10-31 15:3x 使用者決定「使用者自己拖的分隔線位置不動，只有版面自己擠壓時才保留最小高度」）：重排（relayout=True：
        _rebuild——面板出現、消失、收合、資料游標的讀數面板出現；存檔還原的分隔線套用後的那一次）一定檢查；中欄大小改變（視窗大小改變，<Configure>）
        只在使用者沒有自己拖過分隔線時檢查——拖過（或存檔還原的）就照 0.9.13 保留他拖的位置（ttk 照比例縮），下一次重排才重新檢查。
        第一輪修正（d2c04fa）在任何大小改變都推回 160 px，第二輪驗證 7a／16a／4i：100% 時使用者拉到 90 px、一改視窗大小就被推回。Mac 不做（照舊）。"""
        if not NARROW_LAYOUT:
            return
        if not relayout and self._user_sash.get("center"):
            return
        self._auto_sash += 1
        try:
            if not self.winfo_exists() or "center" not in self.visible_columns():
                return
            col = self.cols["center"]
            panes = [self.nametowidget(str(p)) for p in col.panes()]
            n = len(panes)
            if n < 2 or not any(panes[0] is self.panels.get(k) for k in self.fixed):
                return
            H = int(col.winfo_height())
            if H < 100 or not col.winfo_ismapped():
                return
            px = self.th.px if self.th is not None else (lambda v: int(round(v)))
            need = min(int(px(self.CENTER_FIXED_MIN_PX)), H // 2)
            pos = [int(col.sashpos(i)) for i in range(n - 1)]
            if pos[0] >= need and panes[0].winfo_ismapped():
                return
            thick = max(0, (panes[1].winfo_rooty() - col.winfo_rooty()) - pos[0]) if panes[1].winfo_ismapped() else 0
            ends = pos + [H]
            hs = [max(1, ends[i] - (pos[i - 1] + thick)) for i in range(1, n)]       # 其他面板現在的高度
            avail = H - need - thick * (n - 1)
            if avail < n - 1:
                return
            scale = min(1.0, avail / float(sum(hs)))
            new = [need]
            for h in hs[:-1]:
                new.append(new[-1] + thick + max(1, int(h * scale)))
            for i in reversed(range(n - 1)):                     # 由下往上設：每一條都只往下移（見說明），ttk 的前後順序限制不會擋到
                col.sashpos(i, new[i])
        except Exception:
            pass
        finally:
            self._auto_sash -= 1

    def _keep_fixed_room_later(self, event=None, relayout: bool = False) -> None:
        if not NARROW_LAYOUT or getattr(self, "_fixed_job", None) is not None:
            return
        def run():
            self._fixed_job = None
            self._keep_fixed_room(relayout=relayout)
        try:
            self._fixed_job = self._root().after_idle(run)
        except Exception:
            self._fixed_job = None

    def _keep_center_room_later(self, event=None) -> None:
        if not NARROW_LAYOUT or getattr(self, "_center_job", None) is not None:
            return
        def run():
            self._center_job = None
            self._keep_center_room()
        try:
            self._center_job = self._root().after_idle(run)
        except Exception:
            self._center_job = None

    def _rebuild(self) -> None:
        prev = self._geometry_snapshot()
        self._user_sash.clear()                  # 重排（版面自己變了）：使用者之前拖的位置不再算，重排後重新檢查（W14R2-3）
        self._auto_sash += 1
        try:
            self._rebuild_inner(prev)
        finally:
            self._auto_sash -= 1
        if NARROW_LAYOUT:                        # Windows：圖不被同欄的面板擠掉（W14-2）——現在看一次，欄寬定下來、量測面板換好行之後再看一次
            self._keep_fixed_room(relayout=True)
            # 晚一點的兩次不帶 relayout：重排之後才套用的存檔分隔線（_apply_sashes：同 DPI 倍數照存的位置還原，W14R3-1）、或使用者這 300 ms 內
            # 自己拖的，照它；旗標在上面剛清掉，沒有人在這期間設分隔線時和帶 relayout 一樣會檢查
            self._keep_fixed_room_later()
            try:
                self._root().after(300, lambda: self._keep_fixed_room())
            except Exception:
                pass
        if self.on_change is not None:
            try:
                self.on_change()
            except Exception:
                pass

    def _rebuild_inner(self, prev) -> None:
        for col in self.cols.values():
            for p in list(col.panes()):
                try:
                    col.forget(p)
                except Exception:
                    pass
        for p in list(self.h.panes()):
            try:
                self.h.forget(p)
            except Exception:
                pass
        for c in self.COLUMNS:
            vis = [k for k in self.order[c] if k not in self.hidden]
            if not vis:
                continue
            col = self.cols[c]
            wts = {k: (0 if self.panels[k].collapsed else self.weights.get(k, 0)) for k in vis}   # 收合的不分剩下的高度
            if sum(wts.values()) == 0:
                grow = [k for k in vis if not self.panels[k].collapsed] or vis
                wts[grow[-1]] = 1                    # 全部 0 時最後一個（展開的）吃掉剩下的高度
            for k in vis:
                col.add(self.panels[k], weight=wts[k])
            self.h.add(col, weight=self.col_weight[c])
        self._nudge()
        self._restore_geometry(prev)
        self._fit_collapsed()
        self._keep_center_room()

    # --- 用滑鼠把面板拖到別欄（像 MATLAB 拖面板標題列）------------------------------------
    def _bind_drag(self, key: str, panel: Panel) -> None:
        for w in (panel.header, panel.label):
            w.bind("<ButtonPress-1>", lambda e, k=key: self._drag_press(k, e), add="+")
            w.bind("<B1-Motion>", lambda e, k=key: self._drag_motion(k, e), add="+")
            w.bind("<ButtonRelease-1>", lambda e, k=key: self._drag_release(k, e), add="+")

    def _drag_press(self, key: str, e) -> None:
        self._drag = None
        if key in self.fixed or self.max_key is not None:
            return
        self._drag = {"key": key, "x": e.x_root, "y": e.y_root, "on": False, "target": None}

    def _drag_motion(self, key: str, e) -> None:
        d = self._drag
        if not d or d["key"] != key:
            return
        if not d["on"]:
            if abs(e.x_root - d["x"]) < 5 and abs(e.y_root - d["y"]) < 5:
                return                           # 還沒拖超過門檻：當作點一下
            d["on"] = True
            try:
                self.winfo_toplevel().configure(cursor="closedhand" if IS_MAC else "fleur")
            except Exception:
                pass
        t = self._drop_target(e.x_root, e.y_root)
        if t != d["target"]:
            d["target"] = t
            self._show_indicator(t)

    def _drag_release(self, key: str, e) -> None:
        d, self._drag = self._drag, None
        if not d or not d["on"]:
            return
        self._drag_end()
        if d["target"] is not None:
            col, before = d["target"]
            self.move_before(key, col, before)

    def _drag_cancel(self) -> None:
        d, self._drag = self._drag, None
        if d and d["on"]:
            self._drag_end()

    def _drag_end(self) -> None:
        try:
            self.winfo_toplevel().configure(cursor="")
        except Exception:
            pass
        self._hide_indicator()

    def _drop_target(self, xr: int, yr: int):
        """滑鼠（螢幕座標）對應的放置位置：(欄, 要插在哪個面板前面或 None＝最後)；在 Dock 外面回 None。
        左／右欄目前是空的（沒顯示）時，靠近 Dock 左／右邊緣就算放進那一欄。"""
        X0, Y0, W, H = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width(), self.winfo_height()
        x, y = xr - X0, yr - Y0
        if x < 0 or x > W or y < 0 or y > H:
            return None
        vis = self.visible_columns()
        edge = max(40, int(W * 0.12))
        col = None
        if "left" not in vis and x < edge:
            col = "left"
        elif "right" not in vis and x > W - edge:
            col = "right"
        else:
            for c in vis:
                cw = self.cols[c]
                cx0 = cw.winfo_rootx() - X0
                if cx0 <= x <= cx0 + cw.winfo_width():
                    col = c
                    break
            if col is None:
                col = vis[0] if x < (self.cols[vis[0]].winfo_rootx() - X0) else vis[-1]
        dragging = self._drag["key"] if self._drag else None
        before = None
        for k in self.order[col]:
            if k in self.hidden or k == dragging or k in self.fixed:
                continue
            p = self.panels[k]
            if y < (p.winfo_rooty() - Y0) + p.winfo_height() / 2:
                before = k
                break
        return (col, before)

    def _show_indicator(self, t) -> None:
        if t is None:
            self._hide_indicator()
            return
        if self._ind is None:
            self._ind = tk.Frame(self, background=self.th["focus"], highlightthickness=0)
        col, before = t
        X0, Y0, W, H = self.winfo_rootx(), self.winfo_rooty(), self.winfo_width(), self.winfo_height()
        thick = max(3, self.th.px(3))
        if col not in self.visible_columns():
            self._ind.place(x=0 if col == "left" else W - thick, y=0, width=thick, height=H)      # 空欄：邊緣一條直線
        else:
            cw = self.cols[col]
            cx, cwidth = cw.winfo_rootx() - X0, cw.winfo_width()
            dragging = self._drag["key"] if self._drag else None
            if before is not None:
                p = self.panels[before]
                y = p.winfo_rooty() - Y0 - thick // 2
            else:
                keys = [k for k in self.order[col] if k not in self.hidden and k != dragging]
                if keys:
                    p = self.panels[keys[-1]]
                    y = p.winfo_rooty() - Y0 + p.winfo_height() - thick
                else:
                    y = H - thick
            self._ind.place(x=cx, y=max(0, y), width=cwidth, height=thick)
        self._ind.lift()

    def _hide_indicator(self) -> None:
        if self._ind is not None:
            self._ind.place_forget()

    # --- 面板選單 --------------------------------------------------------------
    def post_menu(self, key: str, event=None) -> None:
        panel = self.panels.get(key)
        if panel is None:
            return
        c = self.column_of(key)
        m = tk.Menu(self, tearoff=0)
        names = {"left": tr("移到左欄"), "center": tr("移到中欄（圖下方）"), "right": tr("移到右欄")}
        for col in self.COLUMNS:
            m.add_command(label=names[col], state="disabled" if (col == c or key in self.fixed) else "normal",
                          command=lambda col=col: self.move(key, col))
        m.add_separator()
        m.add_command(label=tr("上移"), command=lambda: self.shift(key, -1),
                      state="normal" if self._neighbor(key, -1) is not None else "disabled")
        m.add_command(label=tr("下移"), command=lambda: self.shift(key, 1),
                      state="normal" if self._neighbor(key, 1) is not None else "disabled")
        m.add_separator()
        m.add_command(label=tr("還原大小") if self.max_key == key else tr("最大化"), command=lambda: self.toggle_max(key))
        if panel._collapsible:
            m.add_command(label=tr("展開") if panel.collapsed else tr("收合"), command=panel.toggle)
        if key not in self.fixed:
            m.add_command(label=tr("隱藏面板"), command=lambda: self.hide(key))
        m.add_separator()
        m.add_command(label=tr("恢復預設版面"), command=self.reset)
        if event is not None and hasattr(event, "x_root"):
            x, y = int(event.x_root), int(event.y_root)
        else:
            b = panel._menu_btn or panel.header
            x, y = b.winfo_rootx(), b.winfo_rooty() + b.winfo_height()
        popup_menu(m, x, y)                      # 0.9.13 W1：彈出後銷毀（Windows 的選單代號有限）


def _panels_in(widget) -> List[Panel]:
    out = []
    stack = [widget]
    while stack:
        w = stack.pop()
        if isinstance(w, Panel):
            out.append(w)
        try:
            stack.extend(w.winfo_children())
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Toolstrip（分頁列＋section＋大小按鈕＋快速存取列）
# ---------------------------------------------------------------------------
class Section(ttk.Frame if HAVE_TK else object):
    """一個 section：上面是按鈕區（可多欄），下面是小字大寫標題，右邊 1px 分隔線。"""

    def __init__(self, master, title: str, th: Theme):
        super().__init__(master)
        self.th = th
        self.title = title
        self.area = ttk.Frame(self)
        self.area.pack(side="top", fill="both", expand=True, padx=(th.px(4), th.px(4)), pady=(th.px(3), 0))
        self.caption = ttk.Label(self, text=title.upper() if title.isascii() else title, style="Section.TLabel", anchor="center")
        self.caption.pack(side="bottom", fill="x", pady=(0, th.px(2)))
        self._cols: List[Any] = []

    def column(self):
        """新開一欄（小按鈕由上而下疊，最多三列）。"""
        col = ttk.Frame(self.area)
        col.pack(side="left", anchor="n", padx=(0, self.th.px(2)))
        self._cols.append(col)
        return col

    def _parent(self, col):
        if col is None:
            return self.area
        return col

    def button(self, text: str, *, icon: Optional[str] = None, command: Optional[Callable] = None, big: bool = False,
               tip: Optional[str] = None, col=None, width: Optional[int] = None, state: str = "normal", style: Optional[str] = None):
        th = self.th
        parent = self._parent(col)
        st = style or ("Big.Tool.TButton" if big else "Small.Tool.TButton")
        b = ttk.Button(parent, text=text, style=st, command=command, takefocus=0, state=state,
                       compound=("top" if big else "left") if icon else "none")
        if icon:
            th.bind_icon(b, icon, 24 if big else 16)
        if width:
            b.configure(width=width)
        if big:
            b.pack(side="left", anchor="n", padx=th.px(1), fill="y")
        else:
            b.pack(side="top", anchor="w", fill="x", pady=0)
        tooltip(b, tip)
        return b

    def toggle(self, text: str, variable, *, icon: Optional[str] = None, command: Optional[Callable] = None,
               big: bool = False, tip: Optional[str] = None, col=None, width: Optional[int] = None):
        th = self.th
        parent = self._parent(col)
        b = ttk.Checkbutton(parent, text=text, variable=variable, command=command, takefocus=0,
                            style="Big.Tool.TCheckbutton" if big else "Small.Tool.TCheckbutton",
                            compound=("top" if big else "left") if icon else "none")
        if icon:
            th.bind_icon(b, icon, 24 if big else 16)
        if width:
            b.configure(width=width)
        if big:
            b.pack(side="left", anchor="n", padx=th.px(1), fill="y")
        else:
            b.pack(side="top", anchor="w", fill="x")
        tooltip(b, tip)
        return b

    def widget(self, w, *, col=None, big: bool = False, pady=0):
        """放一個自己建好的元件（parent 要是 section.area 或某個 column）。"""
        if big:
            w.pack(side="left", anchor="n", padx=self.th.px(2), fill="y")
        else:
            w.pack(side="top", anchor="w", pady=pady)
        return w


class ToolTab(ttk.Frame if HAVE_TK else object):
    def __init__(self, master, key: str, text: str, th: Theme):
        super().__init__(master, style="StripBody.TFrame")
        self.key = key
        self.text = text
        self.th = th
        self.sections: List[Section] = []

    def section(self, title: str) -> Section:
        if self.sections:
            ttk.Separator(self, orient="vertical").pack(side="left", fill="y", pady=(self.th.px(8), self.th.px(4)))
        s = Section(self, title, self.th)
        s.pack(side="left", fill="y", padx=(self.th.px(2), self.th.px(2)))
        self.sections.append(s)
        return s


class Toolstrip(ttk.Frame if HAVE_TK else object):
    """上：藍色分頁列（左分頁、右快速存取）；下：目前分頁的 section；最底 1px 線。內容高度依實際需要（fit()）。"""

    def __init__(self, master, *, on_change: Optional[Callable[[str], None]] = None, body_height: Optional[int] = None):
        th = ensure(master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else None)
        super().__init__(master)
        self.th = th
        self.on_change = on_change
        self.tabs: Dict[str, ToolTab] = {}
        self._order: List[str] = []
        self.var = tk.StringVar(value="")
        self.row = ttk.Frame(self, style="Strip.TFrame", height=th.px(PX["tab_h"]))
        self.row.pack(side="top", fill="x")
        self.row.pack_propagate(False)
        self.qab = ttk.Frame(self.row, style="Strip.TFrame")
        self.qab.pack(side="right", fill="y", padx=(0, th.px(6)))
        self._tabrow = ttk.Frame(self.row, style="Strip.TFrame")
        self._tabrow.pack(side="left", fill="y")
        self._body_height = body_height
        self.body = ttk.Frame(self, style="StripBody.TFrame", height=th.px(body_height or (PX["big_btn_h"] + 20)))
        self.body.pack(side="top", fill="x")
        self.body.pack_propagate(False)
        self._line = ttk.Frame(self, style="Border.TFrame", height=1)
        self._line.pack(side="top", fill="x")
        self._current: Optional[ToolTab] = None
        self._buttons: Dict[str, Any] = {}
        self._collapsed = False
        self._fit_job = None
        # Windows 高 DPI（W10）：視窗比工具列窄時的狀態（NARROW_LAYOUT 關著時都不用）
        self._nw: Dict[str, Any] = {"job": None, "compact": False, "normal_w": {}, "tab_scroll": False, "tab_off": 0,
                                    "tab_seen": None, "body_tab": None, "body_off": 0, "arrows": {}, "wheel": set()}
        if NARROW_LAYOUT:
            self.bind("<Configure>", self._narrow_schedule, add="+")
        listen(self)

    def add_tab(self, text: str, key: Optional[str] = None, *, contextual: bool = False) -> ToolTab:
        key = key or text
        tab = ToolTab(self.body, key, text, self.th)
        self.tabs[key] = tab
        self._order.append(key)
        label = text.upper() if text.isascii() else text
        rb = ttk.Radiobutton(self._tabrow, text=label, value=key, variable=self.var,
                             style="Contextual.StripTab.TRadiobutton" if contextual else "StripTab.TRadiobutton",
                             command=lambda k=key: self.select(k), takefocus=0)
        rb.pack(side="left", fill="y")
        rb.bind("<Double-Button-1>", lambda e: self.collapse(not self._collapsed), add="+")
        self._buttons[key] = rb
        if self._current is None:
            self.select(key)
        self._schedule_fit()
        if NARROW_LAYOUT:
            self._narrow_schedule()
        return tab

    def select(self, key: str) -> None:
        tab = self.tabs.get(key)
        if tab is None:
            return
        if self._current is not None and self._current is not tab:
            self._current.pack_forget()
            if NARROW_LAYOUT:                        # 捲動中的分頁是 place 的：換分頁時也收起來，新的分頁從最左邊開始
                self._current.place_forget()
                self._nw["body_tab"] = None
                self._nw["body_off"] = 0
        self._current = tab
        self.var.set(key)
        if not self._collapsed:
            tab.pack(fill="both", expand=True)
        if NARROW_LAYOUT:
            self._narrow_apply()
        if self.on_change:
            self.on_change(key)

    def set_tab_visible(self, key: str, visible: bool) -> None:
        """情境分頁（MATLAB 的 contextual tab）：只在對應的東西存在時出現；藏起目前分頁就切到第一個看得到的分頁。"""
        rb = self._buttons.get(key)
        if rb is None or bool(rb.winfo_manager()) == bool(visible):
            return
        if visible:
            after = None
            for k in self._order[:self._order.index(key)]:
                if self._buttons[k].winfo_manager():
                    after = self._buttons[k]
            if after is not None:
                rb.pack(side="left", fill="y", after=after)
            else:
                first = next((self._buttons[k] for k in self._order if self._buttons[k].winfo_manager()), None)
                rb.pack(side="left", fill="y", before=first) if first is not None else rb.pack(side="left", fill="y")
        else:
            rb.pack_forget()
            if self.current == key:
                nxt = next((k for k in self._order if self._buttons[k].winfo_manager()), None)
                if nxt is not None:
                    self.select(nxt)
        if NARROW_LAYOUT:
            self._narrow_schedule()

    def tab_visible(self, key: str) -> bool:
        rb = self._buttons.get(key)
        return bool(rb is not None and rb.winfo_manager())

    @property
    def current(self) -> Optional[str]:
        return self._current.key if self._current else None

    def collapse(self, flag: bool = True) -> None:
        """像 MATLAB 一樣可以只留分頁列（雙擊分頁切換）。"""
        self._collapsed = flag
        if flag:
            self.body.pack_forget()
        else:
            self.body.pack(side="top", fill="x", after=self.row)
            if self._current is not None:
                self._current.pack(fill="both", expand=True)
        if NARROW_LAYOUT:
            self._narrow_schedule()

    # --- Windows 高 DPI：視窗比工具列窄（2026-10-29 使用者決定 W10；NARROW_LAYOUT）-----------------------------------------
    def _narrow_schedule(self, event=None) -> None:
        if not NARROW_LAYOUT or self._nw["job"] is not None:
            return
        try:                                      # 掛在主視窗：工具列先被銷毀時排著的回呼不會變成「invalid command name」背景錯誤
            self._nw["job"] = self._root().after_idle(self._narrow_apply)
        except Exception:
            self._nw["job"] = None

    @staticmethod
    def _tab_style(rb, compact: bool) -> str:
        base = str(rb.cget("style"))
        if base.startswith("Compact."):
            base = base[len("Compact."):]
        return ("Compact." + base) if compact else base

    def narrow_state(self) -> Dict[str, Any]:
        """目前的窄視窗狀態（測試、診斷看）：compact＝窄分頁鈕、tab_scroll／tab_off＝分頁列捲動、body_scroll／body_off＝內容捲動。"""
        nw = self._nw
        return {"compact": nw["compact"], "tab_scroll": nw["tab_scroll"], "tab_off": nw["tab_off"],
                "body_scroll": nw["body_tab"] is not None, "body_off": nw["body_off"]}

    def _narrow_apply(self) -> None:
        """視窗比工具列窄：(1) 原本的分頁鈕（每個 11 個字寬）＋快速存取放不下 → 改用窄分頁鈕（字的寬度＋小邊距）；
        (2) 窄分頁鈕也放不下 → 分頁列左右捲動（兩端 ◀ ▶，選到的分頁一定捲進來）；(3) 目前分頁的內容比工具列寬 → 內容左右捲動
        （兩端 ◀ ▶、滾輪）。放得下時全部恢復原狀（和以前一模一樣）。"""
        nw = self._nw
        nw["job"] = None
        if not NARROW_LAYOUT:
            return
        try:
            if not self.winfo_exists():
                return
            W = self.winfo_width()
            if W <= 1:
                return
            px = self.th.px
            qab_w = self.qab.winfo_reqwidth() + px(6)
            vis = [self._buttons[k] for k in self._order if self._buttons[k].winfo_manager()]
            for b in vis:
                if not str(b.cget("style")).startswith("Compact.") and str(b) not in nw["normal_w"]:
                    nw["normal_w"][str(b)] = b.winfo_reqwidth()
            normal_need = sum(nw["normal_w"].get(str(b), b.winfo_reqwidth()) for b in vis) + qab_w
            compact = normal_need > W
            if compact != nw["compact"]:
                for b in self._buttons.values():
                    b.configure(style=self._tab_style(b, compact))
                nw["compact"] = compact
                self.update_idletasks()
            self._narrow_tabrow(W, qab_w, sum(b.winfo_reqwidth() for b in vis))
            self._narrow_body(W)
        except tk.TclError:
            pass

    def _narrow_arrow(self, name: str, parent, text: str, style: str, cmd: Callable, tip: str):
        b = self._nw["arrows"].get(name)
        if b is None:
            b = ttk.Button(parent, text=text, style=style, command=cmd, takefocus=0)
            tooltip(b, tip)
            if name.startswith("body"):
                b.bind("<MouseWheel>", self._narrow_wheel, add="+")
            self._nw["arrows"][name] = b
        return b

    def _narrow_hide(self, *names: str) -> None:
        for n in names:
            b = self._nw["arrows"].get(n)
            if b is not None and b.winfo_manager():
                b.place_forget()

    def _narrow_tabrow(self, W: int, qab_w: int, need: int) -> None:
        nw = self._nw
        avail = W - qab_w
        if need <= avail:
            if nw["tab_scroll"]:
                self._tabrow.place_forget()
                self._tabrow.pack(side="left", fill="y")
                nw["tab_scroll"], nw["tab_off"] = False, 0
            self._narrow_hide("tab_l", "tab_r")
            return
        a = self.th.px(18)
        view = max(1, avail - 2 * a)                     # 兩個捲動鈕中間看得到的寬度
        max_off = max(0, need - view)
        off = min(max(int(nw["tab_off"]), 0), max_off)
        sel = self._buttons.get(self.current or "")
        if sel is not None and sel.winfo_manager() and nw["tab_seen"] != self.current:
            x0, w0 = sel.winfo_x(), sel.winfo_reqwidth()     # 選到的分頁（換分頁、快速鍵、程式選的）一定捲進來
            if x0 < off:
                off = x0
            elif x0 + w0 > off + view:
                off = min(max_off, x0 + w0 - view)
            nw["tab_seen"] = self.current
        nw["tab_off"] = off
        if not nw["tab_scroll"]:
            self._tabrow.pack_forget()
            nw["tab_scroll"] = True
        self._tabrow.place(x=a - off, y=0, relheight=1.0, width=need)
        self._tabrow.lower(self.qab)                     # 捲到快速存取底下的部分被它蓋住
        for name, x, txt, d, on in (("tab_l", 0, "◀", -1, off > 0), ("tab_r", avail - a, "▶", 1, off < max_off)):
            b = self._narrow_arrow(name, self.row, txt, "StripArrowTab.TButton", lambda d=d: self._narrow_scroll("tab", d),
                                   tr("捲動分頁列（視窗太窄，放不下全部分頁）"))
            b.configure(state="normal" if on else "disabled")
            b.place(x=x, y=0, width=a, relheight=1.0)
            b.lift()

    def _narrow_body(self, W: int) -> None:
        nw = self._nw
        tab = self._current
        need = tab.winfo_reqwidth() if tab is not None else 0
        if tab is None or self._collapsed or need <= W:
            t = nw["body_tab"]
            if t is not None:
                t.place_forget()
                nw["body_tab"] = None
                if t is self._current and not self._collapsed:
                    t.pack(fill="both", expand=True)
            nw["body_off"] = 0
            self._narrow_hide("body_l", "body_r")
            return
        a = self.th.px(18)
        max_off = need - W + 2 * a                      # 最右邊的區段可以整個捲到兩個捲動鈕中間
        off = min(max(int(nw["body_off"]), 0), max_off)
        nw["body_off"] = off
        if nw["body_tab"] is not tab:
            if nw["body_tab"] is not None:
                nw["body_tab"].place_forget()
            tab.pack_forget()
            nw["body_tab"] = tab
            self._narrow_wheel_bind(tab)
        tab.place(x=a - off, y=0, relheight=1.0, width=need)
        for name, x, txt, d, on in (("body_l", 0, "◀", -1, off > 0), ("body_r", W - a, "▶", 1, off < max_off)):
            b = self._narrow_arrow(name, self.body, txt, "StripArrow.TButton", lambda d=d: self._narrow_scroll("body", d),
                                   tr("捲動工具列（視窗太窄，放不下這個分頁的全部按鈕；滾輪也可以）"))
            b.configure(state="normal" if on else "disabled")
            b.place(x=x, y=0, width=a, relheight=1.0)
            b.lift()

    def _narrow_scroll(self, what: str, d: int, step: Optional[int] = None) -> None:
        """◀ ▶（d＝−1／+1）：捲大約六成的寬度；滾輪給 step。"""
        nw = self._nw
        try:
            W = self.winfo_width()
            step = int(step or max(self.th.px(40), W * 0.6))
            if what == "tab":
                nw["tab_off"] = int(nw["tab_off"]) + d * step
                nw["tab_seen"] = self.current            # 手動捲：不要再把選到的分頁捲回來
            else:
                nw["body_off"] = int(nw["body_off"]) + d * step
            self._narrow_apply()
        except tk.TclError:
            pass

    _NO_WHEEL = {"TEntry", "TCombobox", "TSpinbox", "Entry", "Spinbox", "Text", "Listbox", "TScale", "Scale", "Treeview"}

    def _narrow_wheel_bind(self, w) -> None:
        """內容捲動中：滾輪在分頁上（按鈕、標籤、區段；輸入欄位與下拉選單除外——它們自己用滾輪）也左右捲。"""
        stack = [w, self.body]
        while stack:
            c = stack.pop()
            try:
                if str(c) not in self._nw["wheel"] and c.winfo_class() not in self._NO_WHEEL:
                    c.bind("<MouseWheel>", self._narrow_wheel, add="+")
                    self._nw["wheel"].add(str(c))
                if c is not self.body:
                    stack.extend(c.winfo_children())
            except tk.TclError:
                pass

    def _narrow_wheel(self, e):
        if self._nw["body_tab"] is None:
            return None
        self._narrow_scroll("body", -1 if int(getattr(e, "delta", 0) or 0) > 0 else 1, step=self.th.px(60))
        return "break"

    def _schedule_fit(self) -> None:
        if self._fit_job is not None:
            return
        try:
            self._fit_job = self.after_idle(self.fit)
        except Exception:
            self._fit_job = None

    def fit(self) -> None:
        """內容高度 = 最高的那個分頁的需求高度（字型不同、Windows 行高不同時才不會把 section 標題切掉）。"""
        self._fit_job = None
        if self._body_height:
            return
        try:
            self.update_idletasks()
            need = max([t.winfo_reqheight() for t in self.tabs.values()] + [self.th.px(PX["big_btn_h"] + 20)])
            self.body.configure(height=need + 2)
        except Exception:
            pass

    def qab_button(self, icon_name: str, tip: str, command: Callable, *, text: str = ""):
        b = ttk.Button(self.qab, text=text, style="Qab.TButton", command=command, takefocus=0,
                       compound="left" if text else "none")
        if not self.th.bind_icon(b, icon_name, 16, on_strip=True) and not text:
            b.configure(text=tip.split(" ")[0][:4] if tip else icon_name)
        b.pack(side="left", padx=self.th.px(1), pady=self.th.px(3))
        tooltip(b, tip)
        return b

    def qab_separator(self):
        s = ttk.Frame(self.qab, style="Strip.TFrame", width=self.th.px(8))
        s.pack(side="left", fill="y")
        return s

    def on_theme(self, th: Theme) -> None:
        self.th = th
        for tab in self.tabs.values():
            tab.th = th
            for sec in tab.sections:
                sec.th = th
        try:
            self.row.configure(height=th.px(PX["tab_h"]))
        except Exception:
            pass
        self._schedule_fit()
        if NARROW_LAYOUT:                                # 字型、主題換了：分頁鈕原本的寬度重量
            self._nw["normal_w"].clear()
            if self._nw["compact"]:
                for b in self._buttons.values():
                    b.configure(style=self._tab_style(b, False))
                self._nw["compact"] = False
            self._narrow_schedule()


class _FlowRow:
    """flow_row 的實作：一排 pack(side="left") 的欄位比它所在的寬度寬時，改用 place 排成幾行（每行照原本的順序與間距、
    垂直置中）並設 frame 的高度；寬度夠了就照原本的 pack 選項、原本的順序排回去（和以前一模一樣）。"""

    def __init__(self, frame):
        self.f = frame
        self.items: Optional[List[Tuple[Any, Dict[str, Any]]]] = None
        self.wrapped = False
        self.lines = 1
        self._job = None
        self._last: Optional[Tuple[int, int]] = None
        frame.bind("<Configure>", self._schedule, add="+")

    def _schedule(self, event=None) -> None:
        if self._job is None:
            try:
                self._job = self.f._root().after_idle(self.apply)     # 掛在主視窗（視窗先關掉也不會有背景錯誤；apply 自己看 winfo_exists）
            except Exception:
                self._job = None

    def _pad(self, v) -> Tuple[int, int]:
        """pack_info 的 padx／pady：數字、(左, 右) tuple 或 Tcl 的 "8 2" 字串都可能。"""
        try:
            items = list(v) if isinstance(v, (tuple, list)) else self.f.tk.splitlist(str(v))
            p = [int(float(str(x))) for x in items]
        except Exception:
            p = [0]
        return (p[0], p[-1]) if p else (0, 0)

    def apply(self) -> None:
        self._job = None
        f = self.f
        try:
            if not f.winfo_exists():
                return
            if self.items is None:
                self.items = [(c, dict(c.pack_info())) for c in f.pack_slaves()]
            W = f.winfo_width()
            if W <= 1:
                return
            sizes = []
            for c, info in self.items:
                l_, r_ = self._pad(info.get("padx", 0))
                t_, b_ = self._pad(info.get("pady", 0))
                sizes.append((c, l_, r_, t_, b_, c.winfo_reqwidth(), c.winfo_reqheight()))
            need = sum(l_ + w_ + r_ for _c, l_, r_, _t, _b, w_, _h in sizes)
            if need <= W:
                if self.wrapped:
                    for c, _info in self.items:
                        c.place_forget()
                    for c, info in self.items:
                        c.pack(**info)
                    f.configure(height=0, width=0)
                    self.wrapped, self.lines, self._last = False, 1, None
                return
            rows: List[List[Any]] = [[]]
            x = 0
            for s in sizes:
                w_full = s[1] + s[5] + s[2]
                if x > 0 and x + w_full > W:
                    rows.append([])
                    x = 0
                rows[-1].append((x, s))
                x += w_full
            key = (W, len(rows))
            if self.wrapped and self._last == key:
                return
            grow = (not self.wrapped) or len(rows) > self.lines
            y = 0
            for row in rows:
                lh = max(t_ + h_ + b_ for _x, (_c, _l, _r, t_, b_, _w, h_) in row)
                for x0, (c, l_, _r, t_, b_, _w, h_) in row:
                    if not self.wrapped:
                        c.pack_forget()
                    c.place(x=x0 + l_, y=y + t_ + max(0, (lh - t_ - b_ - h_) // 2))
                y += lh
            f.configure(height=y, width=1)
            self.wrapped, self.lines, self._last = True, len(rows), key
            if grow:
                self._grow()
        except tk.TclError:
            pass

    def _grow(self) -> None:
        """換行之後視窗要的高度變大：視窗跟著加高（最多工作區的 90%），下面的結果、按鈕、狀態列才不會被擠掉。"""
        try:
            top = self.f.winfo_toplevel()
            top.update_idletasks()
            rh, h = top.winfo_reqheight(), top.winfo_height()
            if h > 1 and rh > h:
                l, t, r, b = work_area(top)
                top.geometry(f"{top.winfo_width()}x{min(rh, int((b - t) * 0.9))}")
        except Exception:
            pass


def flow_row(frame) -> Optional[_FlowRow]:
    """一排 pack(side="left") 的欄位（分析視窗上方的參數列）：NARROW_LAYOUT（Windows 高 DPI，W10）時視窗比它窄就換行，
    放得下時和以前一樣排成一排。macOS 不做任何事（回傳 None）。"""
    if not NARROW_LAYOUT or frame is None:
        return None
    fr = getattr(frame, "_pk_flow", None)
    if fr is None:
        fr = _FlowRow(frame)
        frame._pk_flow = fr
    fr._schedule()
    return fr


def work_area(w=None) -> Tuple[int, int, int, int]:
    """主螢幕的工作區 (left, top, right, bottom)：Windows 扣掉工作列（宣告 DPI aware 之後是實體像素）；拿不到、或不是 Windows 時
    用整個螢幕。"""
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes
            r = wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0) and r.right > r.left and r.bottom > r.top:
                return int(r.left), int(r.top), int(r.right), int(r.bottom)       # SPI_GETWORKAREA
        except Exception:
            pass
    try:
        return 0, 0, int(w.winfo_screenwidth()), int(w.winfo_screenheight())
    except Exception:
        return 0, 0, 1920, 1080


def window_size(w, width: int, height: int) -> Tuple[int, int]:
    """新視窗的起始大小（照 macOS 的點寫）。NARROW_LAYOUT（Windows 高 DPI，W10）：宣告 DPI aware 之後 Tk 的寬高是實體像素 →
    照螢幕的縮放放大（和介面的字一樣），而且不超過工作區（寬 95%、高 90%）——以前 175% 的螢幕上分析視窗只有內容的一半大、
    x 軸被切掉。macOS 原樣回傳（不受影響）。"""
    if not NARROW_LAYOUT:
        return int(width), int(height)
    th = current()
    px = th.px if th is not None else (lambda n: int(round(n)))
    l, t, r, b = work_area(w)
    return min(px(width), int((r - l) * 0.95)), min(px(height), int((b - t) * 0.9))


_KEEP_ON_SCREEN: set = set()


WINDOWS_DPI_AWARENESS: List[str] = []    # enable_windows_dpi_awareness 宣告的結果（DSV 的診斷視窗、log、測試看；DSV 與單獨跑的 plotkit 共用）


def enable_windows_dpi_awareness() -> str:
    """Windows：宣告這個行程是 per-monitor DPI aware（2026-10-29 使用者決定 W10，高 DPI 支援；2026-10-30 使用者決定：單獨執行
    `python -m plotkit` 也宣告，和 DSV 一樣）。沒宣告時 Windows 把整個視窗用點陣放大（175% 的螢幕上字和線條是糊的、程式看到的螢幕
    只剩 617 px 寬）；宣告之後 Tk 的 scaling 跟著螢幕的 DPI（介面的字與尺寸照比例放大）、matplotlib 照 Tk 的 scaling 設 device pixel ratio，
    畫面清晰。要在建第一個 Tk 視窗之前叫（DSV 的 main()、SignalViewer 建立之前；plotkit 的 __main__.main() 開圖之前）；之後再叫、
    或已經宣告過（exe 的 manifest、別的程式碼）都不改變什麼。Mac、Linux 什麼都不做。
    依序試 per-monitor v2（Windows 10 1703 起）、per-monitor（8.1 起）、system aware；回傳用了哪一種（"" ＝不是 Windows）。"""
    if not IS_WIN:
        return ""
    if WINDOWS_DPI_AWARENESS:
        return WINDOWS_DPI_AWARENESS[0]
    how = "unchanged"
    try:
        import ctypes
        user32 = ctypes.windll.user32
        try:
            f = user32.SetProcessDpiAwarenessContext
            f.restype = ctypes.c_int
            f.argtypes = [ctypes.c_void_p]
            if f(ctypes.c_void_p(-4)):                   # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                how = "per-monitor-v2"
        except (AttributeError, OSError):
            pass
        if how == "unchanged":
            try:
                if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:     # PROCESS_PER_MONITOR_DPI_AWARE；S_OK
                    how = "per-monitor"
            except (AttributeError, OSError):
                pass
        if how == "unchanged":
            try:
                if user32.SetProcessDPIAware():
                    how = "system"
            except (AttributeError, OSError):
                pass
    except Exception as e:
        how = f"failed: {e}"
    WINDOWS_DPI_AWARENESS.append(how)
    return how


def _dpi_aware_thread() -> bool:
    """Windows：這個執行緒是 DPI aware（DSV 啟動時宣告的；座標都是實體像素）。沒宣告的行程（例如單獨跑 plotkit）座標被 Windows
    虛擬化成 96 DPI 的邏輯像素。"""
    try:
        import ctypes
        u32 = ctypes.windll.user32
        f = u32.GetThreadDpiAwarenessContext
        f.restype = ctypes.c_void_p
        g = u32.GetAwarenessFromDpiAwarenessContext
        g.argtypes = [ctypes.c_void_p]
        return int(g(f())) != 0
    except Exception:
        return False


def _frame_rects(w):
    """Windows：頂層視窗外框（含看不見的縮放邊；Tk 的 +x+y 指的就是它）與看得見的框的 RECT。看得見的框用 DWM 量
    （EXTENDED_FRAME_BOUNDS 一律是實體像素，所以只在 DPI aware 的行程用；沒宣告的行程用外框，和 Tk、工作區同一套邏輯座標）。"""
    import ctypes
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    hwnd = u32.GetAncestor(int(w.winfo_id()), 2)          # GA_ROOT
    outer, vis = wintypes.RECT(), wintypes.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(outer))
    try:
        if not _dpi_aware_thread() or ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(vis), ctypes.sizeof(vis)) != 0:
            vis = outer
    except Exception:
        vis = outer
    return (outer.left, outer.top, outer.right, outer.bottom), (vis.left, vis.top, vis.right, vis.bottom)


def fit_on_screen(w) -> Optional[Tuple[int, int, int, int]]:
    """NARROW_LAYOUT（Windows，W10）：頂層視窗看得見的框（含標題列）整個放進工作區——比工作區大就縮、超出就往回移。
    回傳調整後的 (寬, 高, x, y)（Tk 的 geometry），沒有動回 None。"""
    if not (NARROW_LAYOUT and IS_WIN):
        return None
    try:
        if not w.winfo_exists() or not w.winfo_ismapped():
            return None
        outer, vis = _frame_rects(w)
        l, t, r, b = work_area(w)
        cw, ch = w.winfo_width(), w.winfo_height()
        vw, vh = vis[2] - vis[0], vis[3] - vis[1]
        nw_, nh_ = cw - max(0, vw - (r - l)), ch - max(0, vh - (b - t))
        vw2, vh2 = vw - (cw - nw_), vh - (ch - nh_)
        vx = min(max(vis[0], l), r - vw2)
        vy = min(max(vis[1], t), b - vh2)
        if (nw_, nh_) == (cw, ch) and (vx, vy) == (vis[0], vis[1]):
            return None
        x, y = outer[0] + (vx - vis[0]), outer[1] + (vy - vis[1])
        w.geometry(f"{max(1, nw_)}x{max(1, nh_)}+{x}+{y}")
        return max(1, nw_), max(1, nh_), x, y
    except Exception:
        return None


def _keep_on_screen_map(event) -> None:
    w = event.widget
    try:
        if not isinstance(w, tk.Toplevel) or getattr(w, "_pk_fit_done", False) or w.wm_overrideredirect():
            return
        w._pk_fit_done = True

        def fit(w=w):
            try:
                if w.winfo_exists():
                    fit_on_screen(w)
            except Exception:
                pass
        # 掛在主視窗、不掛在這個視窗：開了馬上關（400 ms 內）時，掛在它身上的回呼已經被 Tkinter 刪掉，計時器到了會變成
        # 「invalid command name …<lambda>」的 Tk 背景錯誤（0.9.14 在 PC 上的 s55／W1 檢查抓到）
        root = w._root()
        root.after_idle(fit)
        root.after(400, fit)                            # 剛顯示時 Windows 還在排它的位置，晚一點再確認一次（放得下就什麼都不做）
    except Exception:
        pass


def install_keep_on_screen(root) -> None:
    """NARROW_LAYOUT（Windows，W10）：這個 interpreter 的每個頂層視窗（分析視窗、說明、偏好設定、對話框…）第一次出現時整個框放進
    工作區（fit_on_screen）。tooltip 之類 overrideredirect 的視窗不管。macOS 不裝（不受影響）。"""
    if not (NARROW_LAYOUT and IS_WIN) or root is None:
        return
    try:
        key = _interp(root)
        if key in _KEEP_ON_SCREEN:
            return
        root.bind_class("Toplevel", "<Map>", _keep_on_screen_map, add="+")
        _KEEP_ON_SCREEN.add(key)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 圖的工具列：包住 matplotlib 的 NavigationToolbar2Tk（它不顯示，只借功能）
# ---------------------------------------------------------------------------
def make_nav(canvas, window):
    """NavigationToolbar2Tk 的子類：「框選放大」改成 MATLAB R2025a 放大模式的行為（見 MatlabNav）。"""
    import math
    from contextlib import contextmanager
    import numpy as _np
    from matplotlib.backend_bases import MouseButton, _Mode
    from matplotlib.backend_tools import Cursors
    from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
    from .interact import CLICK_PX, DRAG_POINT_ZOOM, POINT_MODE_PX, STEP_ZOOM, end_toolbar_zoom, is_context_click

    class MatlabNav(NavigationToolbar2Tk):
        """放大模式照 MATLAB R2025a：
        左鍵單擊＝以該點為中心放大 1.5 倍、Shift＋單擊＝縮小 1.5 倍；拖框＝縮到框內，框的一邊不到 15 px 就只縮另一個方向、
        兩邊都不到 15 px → 以點為中心 1.2 倍；雙擊＝還原視圖；右鍵＝模式選單（不是縮小）；滾輪照常縮放。
        平移模式：左鍵拖曳交給 matplotlib；右鍵（選單）與雙擊（還原視圖）不開始平移，交給 Interactor（MATLAB pan）。
        兩種模式裡按在量測游標線旁 4 px（Interactor.cursor_grab）都不放大／平移：游標照樣可拖、可點選（和預設模式一樣）。
        框是 1 px 實線（#268cdd＝主題的 focus 色），細長時畫成 15 px 寬、中間一條線的帶（和 MATLAB 一樣）；
        要拖滿 10 px（MATLAB 的拖曳門檻）才畫。
        游標（照 MATLAB R2025a）：平移模式＝張開的手（macOS 用 Tk 原生 openhand，其他平台 hand2）、
        放大模式＝十字（crosshair）、模式關掉 → arrow；拖曳中不換游標。重畫時不換等待游標（MATLAB 互動沒有 wait 游標）。
        縮放的數學、外界、on_view_change 都在 plotkit.Interactor（attach_interactor）。"""
        ROI_COLOR = "#268cdd"

        def __init__(self, canvas, window):
            super().__init__(canvas, window, pack_toolbar=False)
            self.interactor = None
            self.zoom_constraint = None          # None｜"x"｜"y"：模式選單的 Unconstrained／Horizontal／Vertical Zoom
            self._zoom_moved = 0.0
            self._roi_ids = []
            try:
                self._aqua = str(canvas.get_tk_widget().tk.call("tk", "windowingsystem")) == "aqua"
            except Exception:
                self._aqua = sys.platform == "darwin"

        def attach_interactor(self, ia) -> None:
            self.interactor = ia

        # --- 游標 --------------------------------------------------------------
        @contextmanager
        def _wait_cursor_for_draw_cm(self):
            """matplotlib 預設：距上次畫圖超過 1 秒的那次重畫先把游標換成 watch 再換回（滾輪第一格、PLOT、重新計算都會閃一下）；
            MATLAB 重畫時游標不變（等待游標只用在表格）。"""
            yield

        def _cursor_name(self, cursor) -> Optional[str]:
            """照 MATLAB 的游標：平移模式＝張開的手、放大模式＝十字（crosshair）；其他交給 matplotlib 的對照表。"""
            if cursor == Cursors.MOVE:
                return "openhand" if self._aqua else "hand2"
            if cursor == Cursors.SELECT_REGION:
                return "crosshair"
            if cursor == Cursors.POINTER:
                return "arrow"
            return None

        def _update_cursor(self, event):
            want = Cursors.POINTER
            if self.mode and event.inaxes and event.inaxes.get_navigate():
                want = Cursors.SELECT_REGION if self.mode == _Mode.ZOOM else Cursors.MOVE
            if want == self._last_cursor:
                return
            name = self._cursor_name(want)
            try:
                if name:
                    self.canvas.get_tk_widget().configure(cursor=name)
                else:
                    self.canvas.set_cursor(want)
            except Exception:
                try:
                    self.canvas.set_cursor(want)
                except Exception:
                    pass
            self._last_cursor = want

        def _cleanup_post_zoom(self):
            """matplotlib 3.11 才有這個方法（3.10 的 release_zoom 自己寫在裡面）；這裡自己定義，3.10／3.11 都走同一份
            （3.11 的 release_zoom／drag_zoom 呼叫到的也是這個）。"""
            end_toolbar_zoom(self)

        def press_zoom(self, event):
            if event.x is None or event.y is None:
                return
            ia = self.interactor
            if ia is None:
                return super().press_zoom(event)
            if event.button == MouseButton.RIGHT or is_context_click(event):
                ia.zoom_mode_context(event)
                return
            if event.button != MouseButton.LEFT:
                return
            if ia.cursor_grab(event):            # 量測游標線旁 4 px：交給 Interactor 拖／選游標，不放大（雙擊也不還原）
                return
            if getattr(event, "dblclick", False):
                if self._zoom_info is not None:
                    self._cleanup_post_zoom()
                if event.inaxes is not None:     # MATLAB zoom 的 'open'：雙擊座標區才還原；座標區外（DSV 的 panel 握把：雙擊＝收合）不動
                    ia.restore_view()
                return
            super().press_zoom(event)
            self._zoom_moved = 0.0

        def press_pan(self, event):
            """平移模式：MATLAB pan 的 'alt'（右鍵、macOS Control＋點）＝選單、'open'（雙擊）＝還原視圖，都由 Interactor 處理
            （_on_press_blocked）；這裡只要不讓 matplotlib 把右鍵拖曳變成縮放、雙擊的第二下不再開始一次平移。"""
            if self.interactor is not None and (event.button == MouseButton.RIGHT or is_context_click(event)
                                                or getattr(event, "dblclick", False) or self.interactor.cursor_grab(event)):
                return                           # 量測游標線旁 4 px：交給 Interactor 拖／選游標，不平移
            super().press_pan(event)

        def drag_pan(self, event):
            """平移模式拖曳：方向限制（模式選單的水平／垂直；MATLAB LimitsDimensions）開著時只動那個軸
            （matplotlib 的 Axes.drag_pan 認 key "x"／"y"）。"""
            info = self._pan_info
            cons = self.zoom_constraint
            if cons not in ("x", "y") or info is None or getattr(event, "buttons", {info.button}) != {info.button}:
                return super().drag_pan(event)
            for ax in info.axes:
                keep = ax.get_ylim() if cons == "x" else ax.get_xlim()
                ax.drag_pan(info.button, cons, event.x, event.y)
                (ax.set_ylim if cons == "x" else ax.set_xlim)(keep)      # 被鎖住的軸一點都不動（matplotlib 會有浮點誤差）
            self.canvas.draw_idle()

        def drag_zoom(self, event):
            info = self._zoom_info
            if info is None:
                return
            if self.interactor is None:
                return super().drag_zoom(event)
            btns = getattr(event, "buttons", None)         # 舊版 matplotlib 的 MouseEvent 可能沒有 buttons
            if btns is not None and btns != {getattr(info, "button", MouseButton.LEFT)}:   # matplotlib < 3.11 的 _ZoomInfo 沒有 button（只會是左鍵）
                self._cleanup_post_zoom()
                return
            x0, y0 = info.start_xy
            self._zoom_moved = max(self._zoom_moved, math.hypot(event.x - x0, event.y - y0))
            if self._zoom_moved < self._px(CLICK_PX):        # 還不算拖曳（<10 邏輯 px）：MATLAB 這時還沒畫 ROI
                self.remove_rubberband()
                return
            ax = info.axes[0]
            (x1, y1), (x2, y2) = _np.clip([info.start_xy, [event.x, event.y]], ax.bbox.min, ax.bbox.max)
            self.draw_roi(x1, y1, x2, y2)

        def release_zoom(self, event):
            info = self._zoom_info
            ia = self.interactor
            if info is None:
                return
            if ia is None or event.x is None or event.y is None:
                return super().release_zoom(event)
            x0, y0 = info.start_xy
            x1, y1 = float(event.x), float(event.y)
            cons = self.zoom_constraint
            dx = 0.0 if cons == "y" else abs(x1 - x0)
            dy = 0.0 if cons == "x" else abs(y1 - y0)
            band = self._px(POINT_MODE_PX)
            small_x, small_y = dx < band, dy < band
            dims = "xy" if cons not in ("x", "y") else cons
            shift = "shift" in {str(m).lower() for m in (getattr(event, "modifiers", None) or ())}
            try:
                if small_x and small_y:
                    click = self._zoom_moved < self._px(CLICK_PX)
                    f = STEP_ZOOM if click else DRAG_POINT_ZOOM
                    px, py = (x0, y0) if click else (x1, y1)
                    ia.zoom_step(info.axes, px, py, (1.0 / f) if shift else f, "both" if dims == "xy" else dims)
                else:
                    d = dims.replace("x", "") if small_x else dims
                    d = d.replace("y", "") if small_y else d
                    ia.zoom_box(info.axes, (x0, y0), (x1, y1), d)
            finally:
                self._cleanup_post_zoom()                 # 出錯也要清掉 _zoom_info，不然滾輪／鍵盤縮放會一直被擋住

        def draw_roi(self, x0, y0, x1, y1):
            """MATLAB 放大模式的框：1 px 實線框；一邊 < 15 px 時那個方向畫成 15 px 寬的帶（那兩邊不畫）＋中間一條線。"""
            self.remove_rubberband()
            tkc = self.canvas._tkcanvas
            h = self.canvas.get_width_height(physical=True)[1]
            cons = self.zoom_constraint
            if cons == "y":
                x1 = x0
            elif cons == "x":
                y1 = y0
            w_, h_ = abs(x1 - x0), abs(y1 - y0)
            X0, X1 = min(x0, x1), max(x0, x1)
            Y0, Y1 = h - max(y0, y1), h - min(y0, y1)
            c = color("focus", self.ROI_COLOR)          # 主題的焦點色（MATLAB 兩個主題＝#268cdd；Sony／Apple 用各自的強調色）
            ids = []
            band = int(round(self._px(POINT_MODE_PX)))        # 15 邏輯 px（顯示縮放時換成實體像素）
            if h_ < band < w_:                                # 短而寬：15 px 高的水平帶，貼在起點的 y
                cy = h - y0
                Y0, Y1 = cy - band // 2, cy + band - band // 2
                ids += [tkc.create_line(X0, Y0, X0, Y1, fill=c), tkc.create_line(X1, Y0, X1, Y1, fill=c),
                        tkc.create_line(X0, cy, X1, cy, fill=c)]
            elif w_ < band < h_:                              # 窄而高：15 px 寬的垂直帶，貼在起點的 x
                cx = x0
                X0, X1 = cx - band // 2, cx + band - band // 2
                ids += [tkc.create_line(X0, Y0, X1, Y0, fill=c), tkc.create_line(X0, Y1, X1, Y1, fill=c),
                        tkc.create_line(cx, Y0, cx, Y1, fill=c)]
            else:
                ids.append(tkc.create_rectangle(X0, Y0, X1, Y1, outline=c))
            self._roi_ids = ids

        def _px(self, n):
            """MATLAB 的 10／15 px 是邏輯像素；Windows／Linux 顯示縮放（device_pixel_ratio≠1）時事件座標是實體像素，
            要乘上 dpr，和預設模式的拖曳門檻（DRAG_THRESHOLD_PX×dpr）一致。macOS TkAgg 的 dpr 永遠是 1。"""
            return n * float(getattr(self.canvas, "device_pixel_ratio", 1) or 1)

        def remove_rubberband(self):
            super().remove_rubberband()
            for i in self._roi_ids:
                try:
                    self.canvas._tkcanvas.delete(i)
                except Exception:
                    pass
            self._roi_ids = []

    return MatlabNav(canvas, window)


class PlotToolbar(ttk.Frame if HAVE_TK else object):
    """home／back／forward／pan／zoom／save 用主題圖示；右邊顯示 matplotlib 的座標訊息。

    `.nav` 是 NavigationToolbar2Tk（給 Interactor 看 mode 用）。可以用 add_button / add_toggle / add_separator 加自己的工具。
    """

    # 預設順序照 MATLAB R2025a 的 axes toolbar（左→右：export、data tips、pan、zoom in、restore view，中間沒有分隔線）：
    # save＝export、(owner 用 before="pan" 插入 tips、before="tips" 插入複製影像)、pan、zoom、home＝restore view；
    # back／forward 是 matplotlib 多出來的，放最後
    def __init__(self, master, canvas, *, items: Sequence[str] = ("save", "pan", "zoom", "zoomout", "|", "home", "|", "back", "forward"),
                 message: bool = True):
        th = ensure(master.winfo_toplevel() if hasattr(master, "winfo_toplevel") else None)
        super().__init__(master)
        self.th = th
        self.canvas = canvas
        self.nav = make_nav(canvas, self)      # NavigationToolbar2Tk 子類（MATLAB 放大模式）；不 pack：只用它的功能
        self.home_command: Optional[Callable[[], None]] = None   # Home 鈕：host 設成 Interactor.restore_view（原始視圖），沒設就用 nav.home
        self.save_command: Optional[Callable[[], Any]] = None    # 存檔鈕：host 可換（DSV 先藏十字游標）；沒設＝plotkit.export 的匯出對話框
        self.msg_var = tk.StringVar(value="")
        self.nav.set_message = self._set_message                                 # 座標訊息改顯示在我們的標籤
        self.v_pan = tk.BooleanVar(value=False)
        self.v_zoom = tk.BooleanVar(value=False)
        self.on_mode: Optional[Callable[[str], None]] = None     # 平移／框選放大開關時通知（開＝模式名、關＝""；資料提示要讓位／恢復）
        self.left = ttk.Frame(self)
        self.left.pack(side="left", fill="y", padx=(th.px(4), 0))
        if message:
            # 固定寬度：座標訊息隨滑鼠移動一直改字，寬度一變就整串重新排版（<Configure> 一路傳到 PanedWindow、
            # matplotlib 畫布 resize → 整張重畫）
            self.msg = ttk.Label(self, textvariable=self.msg_var, style="Hint.TLabel", anchor="e", font=th.font("mono"), width=36)
            self.msg.pack(side="right", fill="y", padx=(0, th.px(8)))
        self.buttons: Dict[str, Any] = {}
        for it in items:
            if it == "|":
                self.add_separator()
            elif it == "home":
                self.add_button("home", "home", tr("還原視圖 (Home)"), self._home)
            elif it == "back":
                self.add_button("back", "back", tr("上一個視圖"), self.nav.back)
            elif it == "forward":
                self.add_button("forward", "forward", tr("下一個視圖"), self.nav.forward)
            elif it == "pan":
                self.add_toggle("pan", "pan", tr("平移模式（左鍵拖曳平移、方向鍵平移、雙擊還原視圖、右鍵選單）"), self.v_pan, self._pan)
            elif it == "zoom":
                self.add_toggle("zoom", "zoom", tr("放大模式（點＝放大 1.5 倍、拖框、Shift＋點＝縮小、雙擊＝還原）"), self.v_zoom, self._zoom)
            elif it == "zoomout":           # MATLAB axes toolbar 的 Zoom out（批次 E）：以座標區中心縮小 1.5 倍
                self.add_button("zoomout", "zoom_out", tr("縮小（以座標區中心縮小 1.5 倍；方向照放大／平移模式右鍵的方向限制）"),
                                self._zoom_out)
            elif it == "save":
                self.add_button("save", "save", tr("存成圖檔…（格式、DPI、背景、尺寸）"), self._save)
        try:
            canvas.get_tk_widget().configure(background=th["bg"])
        except Exception:
            pass
        listen(self)

    def _set_message(self, s: str) -> None:
        try:
            self.msg_var.set(str(s))
        except Exception:
            pass

    @staticmethod
    def _fallback_text(key: str, tip: str) -> str:
        return (tip.split("（")[0].split(" (")[0].split("：")[0] if tip else key)[:6]

    def _pack_kw(self, before: Optional[str]) -> dict:
        """before＝既有按鈕的 key：插在它前面（例如 before="pan" 把資料提示放在 MATLAB 的位置）。"""
        w = self.buttons.get(before) if before else None
        return {"before": w} if w is not None else {}

    def add_button(self, key: str, icon_name: Optional[str], tip: str, command: Callable, *, text: str = "",
                   before: Optional[str] = None):
        b = ttk.Button(self.left, text=text, style="Tool.TButton", command=command, takefocus=0,
                       compound="left" if (text and icon_name) else "none")
        if not (icon_name and self.th.bind_icon(b, icon_name, 16)) and not text:
            b.configure(text=self._fallback_text(key, tip))
        b.pack(side="left", padx=self.th.px(1), pady=self.th.px(2), **self._pack_kw(before))
        tooltip(b, tip)
        self.buttons[key] = b
        return b

    def add_toggle(self, key: str, icon_name: Optional[str], tip: str, variable, command: Callable, *, text: str = "",
                   before: Optional[str] = None):
        b = ttk.Checkbutton(self.left, text=text, style="AxesTool.TCheckbutton", variable=variable, command=command, takefocus=0,
                            compound="left" if (text and icon_name) else "none")
        if not (icon_name and self.th.bind_icon(b, icon_name, 16)) and not text:
            b.configure(text=self._fallback_text(key, tip))
        b.pack(side="left", padx=self.th.px(1), pady=self.th.px(2), **self._pack_kw(before))
        tooltip(b, tip)
        self.buttons[key] = b
        return b

    def add_separator(self, *, before: Optional[str] = None):
        s = ttk.Separator(self.left, orient="vertical")
        s.pack(side="left", fill="y", padx=self.th.px(4), pady=self.th.px(5), **self._pack_kw(before))
        return s

    def _home(self):
        (self.home_command or self.nav.home)()

    def _save(self):
        if self.save_command is not None:
            return self.save_command()
        from .export import export_dialog
        return export_dialog(self, self.canvas.figure)

    def _zoom_out(self):
        ia = getattr(self.nav, "interactor", None)
        if ia is not None:
            ia.zoom_out()

    def _pan(self):
        self.nav.pan()
        self.sync()
        self._notify_mode()

    def _zoom(self):
        self.nav.zoom()
        self.sync()
        self._notify_mode()

    def _notify_mode(self) -> None:
        if self.on_mode is not None:
            self.on_mode(self.mode)

    def clear_mode(self) -> None:
        """關掉 matplotlib 的平移／框選放大模式（開資料提示模式時用：兩者互斥，像 MATLAB 的互動模式）。"""
        mode = self.mode
        if mode == "pan/zoom":
            self.nav.pan()
        elif mode == "zoom rect":
            self.nav.zoom()
        self.sync()

    def set_mode(self, mode: str) -> None:
        """直接設定模式："pan"／"zoom"／""（關掉）。跟按工具列按鈕一樣會通知 on_mode（DSV 啟動時預設開平移模式用）。"""
        want = {"pan": "pan/zoom", "zoom": "zoom rect"}.get(mode or "", "")
        if self.mode == want:
            return
        if not want:
            self.clear_mode()
            self._notify_mode()
            return
        if want == "pan/zoom":
            self.nav.pan()                     # matplotlib：另一個模式開著時 pan() 直接切成平移
        else:
            self.nav.zoom()
        self.sync()
        self._notify_mode()

    def sync(self) -> None:
        mode = str(getattr(self.nav, "mode", "") or "")
        self.v_pan.set(mode == "pan/zoom")
        self.v_zoom.set(mode == "zoom rect")

    @property
    def mode(self) -> str:
        return str(getattr(self.nav, "mode", "") or "")

    def on_theme(self, th: Theme) -> None:
        self.th = th
        try:
            self.canvas.get_tk_widget().configure(background=th["bg"])
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def placeholder(entry, text: str, variable=None) -> None:
    """Entry 空白時顯示灰色提示文字（MATLAB 的搜尋框那樣）。有 textvariable 的 Entry 不要用（提示字會寫進變數）。"""
    state = {"showing": False}

    def th():
        return current() or ensure(entry.winfo_toplevel())

    def show():
        if state["showing"]:
            return
        if (variable.get() if variable is not None else entry.get()) == "":
            state["showing"] = True
            entry.configure(foreground=th()["text2"])
            entry.insert(0, text)

    def hide(e=None):
        if state["showing"]:
            state["showing"] = False
            entry.delete(0, "end")
            entry.configure(foreground=th()["text"])

    def maybe(e=None):
        try:
            if entry.focus_get() is entry:
                return
        except Exception:
            pass
        show()

    entry.bind("<FocusIn>", hide, add="+")
    entry.bind("<FocusOut>", maybe, add="+")
    entry._pk_placeholder = state
    entry.after_idle(maybe)


def is_placeholder_shown(entry) -> bool:
    st = getattr(entry, "_pk_placeholder", None)
    return bool(st and st.get("showing"))


def hline(master, *, style: str = "Border2.TFrame"):
    f = ttk.Frame(master, style=style, height=1)
    return f


def status_bar(master, variable):
    """最底下的狀態列（底色＝次底色）。"""
    return ttk.Label(master, textvariable=variable, style="Status.TLabel", anchor="w")
