# -*- coding: utf-8 -*-
"""plotkit.styles — 繪圖風格預設（default／matlab／matlab-dark，1.0.0 起加外觀主題的 sony-black／sony-blue／apple-light／apple-dark／
apple-dark-graphite／apple-dark-black）與字型解析。

風格只在畫圖時逐個 artist 套用（不改 rcParams），所以兩個視窗可以各用各的風格。
matlab 風格的數值是 2026-10-21 在 MATLAB R2025a 實測的出廠預設。
"""
from __future__ import annotations

import copy
from functools import lru_cache
from typing import Any, Dict, List, Union

from .i18n import tr

PALETTE_DEFAULT = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                   "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
PALETTE_MATLAB = ["#1171be", "#dd5400", "#edb120", "#8516d1", "#3baa32", "#2fbeef", "#d1048b"]
# R2025a 深色主題的 ColorOrder（figure(Theme="dark") 實測，與淺色不同）
PALETTE_MATLAB_DARK = ["#268cdd", "#f57729", "#ffe864", "#c05cfb", "#49db40", "#6cf4ff", "#f267c5"]
FONT_CJK = ["Microsoft JhengHei", "Microsoft YaHei", "PingFang TC", "Heiti TC",
            "Noto Sans CJK TC", "Noto Sans TC", "Arial Unicode MS"]
LINESTYLES = ("-", "--", ":", "-.", "None")                      # MATLAB 線條選單 Line Style：solid／dash／dot／dash-dot／none
MARKERS = ("", "+", "o", "*", ".", "x", "s", "d", "v", "^", ">", "<", "p", "h")   # MATLAB 線條選單 Marker 的 14 項（順序相同）
LINE_WIDTHS = (0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)        # MATLAB 線條選單 Line Width（[.5, 1:12]）
MARKER_SIZES = (2, 4, 5, 6, 7, 8, 10, 12, 18, 24, 48)              # MATLAB 線條選單 Marker Size

STYLES: Dict[str, Dict[str, Any]] = {
    "default": {
        "name": "default",
        "colors": list(PALETTE_DEFAULT),
        "lw": 1.0, "ms": 4.0,
        "box": True, "tick_dir": "out",
        "grid": {"ls": "-", "alpha": 0.3, "color": "#b0b0b0", "lw": 0.8},
        "fonts": FONT_CJK + ["DejaVu Sans"],
        "fontsize": 10.0,
        "title": {"weight": "normal", "scale": 1.0},
        "label": {"scale": 1.0},
        "legend": {"fontsize": 8, "frameon": True, "loc": "upper right"},
        "fig_face": "white", "axes_face": "white", "axes_edge": "black", "axes_lw": 0.8,
        "text_color": "black", "selected_lw_scale": 2.5,
        # 資料提示：照 MATLAB R2025a 實測（exportgraphics 量色）：框底＝座標區底色、框線 #7d7d7d、目前的提示框線 #268cdd、
        # 字 10 pt、資料點是實心小圓（邊 #ffffdc）、沒有連線
        "tip": {"fc": "white", "ec": "#7d7d7d", "ec_selected": "#268cdd", "lw": 1.0, "fontsize": 10, "text": "black",
                "marker_face": "#212121", "marker_edge": "#ffffdc", "ms": 5.0},
        "annotation_color": "#444444", "annotation_box": "white", "annotation_fontsize": 10,
    },
    "matlab": {
        "name": "matlab",
        "colors": list(PALETTE_MATLAB),
        "lw": 0.5, "ms": 6.0,
        "box": True, "tick_dir": "in",                   # R2025a 實測 axes.Box = on（兩個主題都是）
        "grid": {"ls": "-", "alpha": 0.15, "color": "#212121", "lw": 0.5},
        "fonts": ["Arial", "Helvetica"] + FONT_CJK + ["DejaVu Sans"],   # Arial 在前：macOS 的 Helvetica.ttc 讓 matplotlib 拿不到粗體
        "fontsize": 10.0,
        "title": {"weight": "bold", "scale": 1.1},
        "label": {"scale": 1.1},
        "legend": {"fontsize": 9, "frameon": True, "loc": "upper right", "fancybox": False, "lw": 0.5,
                   "framealpha": 1.0, "edgecolor": "#212121", "facecolor": "white", "textcolor": "#212121"},
        "fig_face": "#f5f5f5", "axes_face": "white", "axes_edge": "#212121", "axes_lw": 0.5,
        "text_color": "#212121", "selected_lw_scale": 2.5,
        "tip": {"fc": "white", "ec": "#7d7d7d", "ec_selected": "#268cdd", "lw": 1.0, "fontsize": 10, "text": "#212121",
                "marker_face": "#212121", "marker_edge": "#ffffdc", "ms": 5.0},      # figure(Theme="light") 實測
        "annotation_color": "#212121", "annotation_box": "white", "annotation_fontsize": 10,
    },
    # figure(Theme="dark") 實測：figure #212121、axes #121212、文字 #d9d9d9、格線白 alpha 0.25、legend 底 #121212
    "matlab-dark": {
        "name": "matlab-dark",
        "colors": list(PALETTE_MATLAB_DARK),
        "lw": 0.5, "ms": 6.0,
        "box": True, "tick_dir": "in",
        "grid": {"ls": "-", "alpha": 0.25, "color": "#ffffff", "lw": 0.5},
        "fonts": ["Arial", "Helvetica"] + FONT_CJK + ["DejaVu Sans"],
        "fontsize": 10.0,
        "title": {"weight": "bold", "scale": 1.1},
        "label": {"scale": 1.1},
        "legend": {"fontsize": 9, "frameon": True, "loc": "upper right", "fancybox": False, "lw": 0.5,
                   "framealpha": 1.0, "edgecolor": "#d9d9d9", "facecolor": "#121212", "textcolor": "#d9d9d9"},
        "fig_face": "#212121", "axes_face": "#121212", "axes_edge": "#d9d9d9", "axes_lw": 0.5,
        "text_color": "#d9d9d9", "selected_lw_scale": 2.5,
        "tip": {"fc": "#121212", "ec": "#7d7d7d", "ec_selected": "#268cdd", "lw": 1.0, "fontsize": 10, "text": "#d9d9d9",
                "marker_face": "#121212", "marker_edge": "#ffffdc", "ms": 5.0},      # figure(Theme="dark") 實測
        "annotation_color": "#d9d9d9", "annotation_box": "#212121", "annotation_fontsize": 10,
    },
}


def _derived(base: str, name: str, **over) -> Dict[str, Any]:
    """從 matlab／matlab-dark（或已經建好的外觀風格，例如 apple-dark）複製一份再覆蓋幾個「面」的顏色（1.0.0 外觀主題的繪圖風格；字型、線寬、刻度方向、Box 全部照 MATLAB 不動）。
    over 裡的 dict（grid／legend／tip）是逐鍵覆蓋，不是整個換掉。"""
    st = copy.deepcopy(STYLES[base])
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(st.get(k), dict):
            st[k].update(v)
        else:
            st[k] = v
    st["name"] = name
    return st


# 外觀主題的繪圖風格（audit/2026-11-01-skins/proposals.md 的 plot_* 建議）：figure 底＝視窗底色（圖和視窗無縫）、座標區底＝輸入框底色，
# 刻度／軸名／標題／圖例字＝主題的文字色，格線照 matlab-dark 的白 α0.25（Apple 淺色改成不透明髮絲 #d2d2d7），資料提示的選中框線＝主題的強調色。
# Sony 黑銀：第 1 條線＝α 橘（1.0.0 使用者「全部都做上去」：少一點藍），其餘取 R2025a 深色 ColorOrder——拿掉第二個橘色 #f57729，
# 和橘色互補的青色提到第 2 條，藍色 #268cdd 放最後（七色在 #121110 座標區底上對比 5.3～15.3:1）。Sony 深藍黑：提案的 PlayStation 線色
# （藍色系是它的身分，維持）；Apple 淺色：第 1 條＝無障礙版系統紫 #8944ab，其餘照 HIG 無障礙系統色、系統藍放最後；Apple 深色三個：第 1 條＝強調色。
STYLES["sony-black"] = _derived(
    "matlab-dark", "sony-black", colors=["#f27a1a", "#6cf4ff", "#ffe864", "#c05cfb", "#49db40", "#f267c5", "#268cdd"],
    fig_face="#1c1b19", axes_face="#121110", axes_edge="#dcdad5", text_color="#dcdad5",
    legend={"edgecolor": "#dcdad5", "facecolor": "#121110", "textcolor": "#dcdad5"},
    tip={"fc": "#121110", "ec_selected": "#f27a1a", "text": "#dcdad5", "marker_face": "#121110"},
    annotation_color="#dcdad5", annotation_box="#1c1b19")
STYLES["sony-blue"] = _derived(
    "matlab-dark", "sony-blue", colors=["#2e8cff", "#ff8a3d", "#ffd84d", "#c56cff", "#4fd96a", "#5ce6ff", "#ff6ec7"],
    fig_face="#0f1621", axes_face="#0a0f17", axes_edge="#c5d0e0", text_color="#e6ecf5",
    legend={"edgecolor": "#e6ecf5", "facecolor": "#0a0f17", "textcolor": "#e6ecf5"},
    tip={"fc": "#0a0f17", "ec_selected": "#2e8cff", "text": "#e6ecf5", "marker_face": "#0a0f17"},
    annotation_color="#e6ecf5", annotation_box="#0f1621")
STYLES["apple-light"] = _derived(
    "matlab", "apple-light", colors=["#8944ab", "#c93400", "#248a3d", "#d30f45", "#008299", "#3634a3", "#7f6545", "#007aff"],
    grid={"alpha": 1.0, "color": "#d2d2d7"},
    fig_face="#ececec", axes_face="white", axes_edge="#8e8e93", text_color="#1d1d1f",
    legend={"edgecolor": "#d2d2d7", "facecolor": "white", "textcolor": "#1d1d1f"},
    tip={"fc": "white", "ec": "#aeaeb2", "ec_selected": "#af52de", "text": "#1d1d1f", "marker_face": "#1d1d1f"},
    annotation_color="#1d1d1f", annotation_box="white")
STYLES["apple-dark"] = _derived(
    "matlab-dark", "apple-dark", colors=["#bf5af2", "#ff9f0a", "#30d158", "#ffd60a", "#ff375f", "#64d2ff", "#ac8e68"],
    fig_face="#1e1e1e", axes_face="#141414", axes_edge="#98989d", text_color="#e5e5ea",
    legend={"edgecolor": "#98989d", "facecolor": "#141414", "textcolor": "#e5e5ea"},
    tip={"fc": "#141414", "ec": "#545458", "ec_selected": "#bf5af2", "text": "#e5e5ea", "marker_face": "#141414"},
    annotation_color="#e5e5ea", annotation_box="#1e1e1e")
STYLES["apple-dark-graphite"] = _derived(          # Apple 深色·石墨橘：面和 apple-dark 一樣，線色第 1 條系統橘、第 2 條銀白（不是藍）
    "apple-dark", "apple-dark-graphite", colors=["#ff9f0a", "#e5e5ea", "#30d158", "#ff375f", "#bf5af2", "#ffd60a", "#64d2ff"],
    tip={"ec_selected": "#ff9f0a"})
STYLES["apple-dark-black"] = _derived(             # Apple 深色·純黑綠：圖底、座標區底都是純黑，圖例底 #1c1c1e
    "apple-dark", "apple-dark-black", colors=["#30d158", "#ff9f0a", "#ff375f", "#ffd60a", "#bf5af2", "#64d2ff", "#ac8e68"],
    fig_face="#000000", axes_face="#000000", legend={"facecolor": "#1c1c1e"},
    tip={"fc": "#000000", "ec_selected": "#30d158", "marker_face": "#000000"}, annotation_box="#000000")


PLOT_FONT_PT_RANGE = (6.0, 20.0)      # 偏好設定 → 字型 的「圖字級」（pt）；None＝風格預設（10 pt）
_PLOT_FONT_PT = None


def set_plot_fontsize(pt) -> None:
    """全部圖的基本字級（刻度、軸標籤、標題、圖例、資料提示、文字標註按同一比例縮放）；None／0＝風格預設。"""
    global _PLOT_FONT_PT
    try:
        v = float(pt) if pt not in (None, "") else 0.0
    except Exception:
        v = 0.0
    _PLOT_FONT_PT = max(PLOT_FONT_PT_RANGE[0], min(PLOT_FONT_PT_RANGE[1], v)) if v > 0 else None


def plot_fontsize() -> float:
    return float(_PLOT_FONT_PT) if _PLOT_FONT_PT else 10.0


def _font_override(st: Dict[str, Any]) -> Dict[str, Any]:
    pt = _PLOT_FONT_PT
    base = float(st.get("fontsize", 10.0) or 10.0)
    if not pt or abs(pt - base) < 1e-9:
        return st
    k = pt / base
    st["fontsize"] = pt
    for sub in ("legend", "tip"):
        d = st.get(sub)
        if isinstance(d, dict) and "fontsize" in d:
            d["fontsize"] = float(d["fontsize"]) * k
    if "annotation_fontsize" in st:
        st["annotation_fontsize"] = float(st["annotation_fontsize"]) * k
    return st


@lru_cache(maxsize=1)
def available_font_names() -> frozenset:
    """系統裡 matplotlib 找得到的字型家族名稱（第一次呼叫會掃描字型，之後快取）。"""
    try:
        from matplotlib import font_manager
        return frozenset(f.name for f in font_manager.fontManager.ttflist)
    except Exception:
        return frozenset()


def resolve_fonts(preferred: List[str]) -> List[str]:
    """只留下有安裝的字型，最後一定補 DejaVu Sans（matplotlib 自帶），避免 findfont 警告。"""
    avail = available_font_names()
    out = [f for f in preferred if f in avail and f != "DejaVu Sans"]
    out.append("DejaVu Sans")
    return out


def get_style(spec: Union[str, Dict[str, Any], None]) -> Dict[str, Any]:
    """取得風格 dict 的副本。spec 可以是名稱，或 {"base": "matlab", "lw": 1.0, ...} 這種覆寫。"""
    if spec is None:
        spec = "default"
    if isinstance(spec, str):
        if spec not in STYLES:
            raise KeyError(tr("沒有這個風格：{name}（可用：{available}）").format(name=repr(spec), available=", ".join(STYLES)))
        return _font_override(copy.deepcopy(STYLES[spec]))
    if isinstance(spec, dict):
        base = copy.deepcopy(STYLES.get(str(spec.get("base", "default")), STYLES["default"]))
        for k, v in spec.items():
            if k == "base":
                continue
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                base[k].update(v)
            else:
                base[k] = copy.deepcopy(v)
        base["name"] = str(spec.get("name", spec.get("base", "custom")))
        return _font_override(base)
    raise TypeError("style 必須是字串或 dict")


def style_name(style: Dict[str, Any]) -> str:
    return str(style.get("name", "default"))


def auto_color(style: Dict[str, Any], k: int) -> str:
    colors = style.get("colors") or PALETTE_DEFAULT
    return colors[int(k) % len(colors)]


def resolved_fonts(style: Dict[str, Any]) -> List[str]:
    return resolve_fonts(list(style.get("fonts") or FONT_CJK + ["DejaVu Sans"]))


def text_kw(style: Dict[str, Any], role: str = "text") -> Dict[str, Any]:
    """給 set_title / set_xlabel / text 用的字型參數。role: title / label / tick / legend / text。"""
    fs = float(style.get("fontsize", 10.0))
    fam = resolved_fonts(style)
    if role == "title":
        t = style.get("title", {})
        return {"fontfamily": fam, "fontsize": fs * float(t.get("scale", 1.0)), "fontweight": t.get("weight", "normal")}
    if role == "label":
        return {"fontfamily": fam, "fontsize": fs * float(style.get("label", {}).get("scale", 1.0))}
    if role == "legend":
        return {"family": fam, "size": float(style.get("legend", {}).get("fontsize", fs))}
    if role == "tip":
        return {"fontfamily": fam, "fontsize": float(style.get("tip", {}).get("fontsize", 10))}
    return {"fontfamily": fam, "fontsize": fs}
