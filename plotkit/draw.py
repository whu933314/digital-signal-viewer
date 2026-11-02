# -*- coding: utf-8 -*-
"""plotkit.draw — 把 FigureState 畫到 matplotlib Figure 上（headless 可用），以及幾何／點選判定工具。

風格只套在 artist 上（不改 rcParams）。標註與資料提示的 artist 由 Interactor.rebuild() 透過
draw_annotation / draw_tip 建立，這裡的 draw_state 只負責線、圖例、軸與風格。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from matplotlib.text import Text
from matplotlib.transforms import offset_copy

from .model import TIP_OFFSET_DEFAULT, Annotation, DataTip, FigureState, Series
from .styles import auto_color, get_style, resolved_fonts, text_kw


# ---------------------------------------------------------------------------
# 不參與自動縮放的疊加 artist（游標線）＋相容各版 matplotlib 的 relim
# ---------------------------------------------------------------------------
def add_overlay(ax, artist):
    """ax.add_artist：疊在座標區上、不算進自動縮放的 artist（十字游標、資料游標的直線）。
    matplotlib 3.11 起 add_artist 加的本來就不算（Artist._in_autoscale 預設 False，只有 add_line／add_patch 會開），
    3.10 以前的 Axes.relim 卻把每條 Line2D 都算進 dataLim（x 軸座標的游標線會把 x 範圍往左撐）；
    所以做記號，relim() 在舊版會跳過它們，兩邊行為一致。"""
    artist._pk_no_autoscale = True
    return ax.add_artist(artist)


def relim(ax, visible_only: bool = False) -> None:
    """ax.relim()，但 add_overlay 加的 artist 不算（＝matplotlib 3.11 的行為；舊版自己跳過）。"""
    from matplotlib.artist import Artist
    children = getattr(ax, "_children", None)
    if hasattr(Artist, "_get_in_autoscale") or not isinstance(children, list):
        ax.relim(visible_only=visible_only)
        return
    skipped = [(i, a) for i, a in enumerate(children) if getattr(a, "_pk_no_autoscale", False)]
    for i, _a in reversed(skipped):
        del children[i]
    try:
        ax.relim(visible_only=visible_only)
    finally:
        for i, a in skipped:
            children.insert(i, a)


MAX_MARKER_POINTS = 50_000     # 超過就不畫 marker（markevery 會關掉 matplotlib 的 subslicing，太慢）
PICK_RADIUS_PT = 5.0           # nearest_vertex 找候選頂點的範圍（點）
# 點到線的判定：線的筆劃落在游標 ±2 px 內就算點到（點到線的容許範圍約 ±2 px）
PICK_TOL_PX = 2.0
TIP_GAP_PT = 1.5               # 資料提示框的角離資料點約 2 px（R2025a exportgraphics 實測）


@dataclass
class RenderInfo:
    ax_left: Any = None
    ax_right: Any = None
    lines: Dict[int, Any] = field(default_factory=dict)      # uid → Line2D
    legend: Any = None
    legend_uids: List[int] = field(default_factory=list)
    style: Dict[str, Any] = field(default_factory=dict)
    bus: Dict[int, Dict[str, Any]] = field(default_factory=dict)   # uid → 匯流排（Series.disp="digital"）：art／hit／center／half

    def axes_for(self, yaxis: str):
        """"right" 但沒有右軸時回 None（標註會被略過、不會畫錯軸）。"""
        return self.ax_right if yaxis == "right" else self.ax_left

    def all_axes(self) -> list:
        return [a for a in (self.ax_left, self.ax_right) if a is not None]

    def key_for(self, ax) -> str:
        return "right" if ax is self.ax_right else "left"


# ---------------------------------------------------------------------------
# 數字與文字
# ---------------------------------------------------------------------------
def fmt_num(v) -> str:
    if v is None:
        return ""
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return str(v)
    if not math.isfinite(fv):
        return str(fv)
    if fv == int(fv) and abs(fv) < 1e15:
        return str(int(fv))
    return f"{fv:.6g}"


def fmt_matlab(v) -> str:
    """MATLAB R2025a 資料提示的 'auto' 數值格式（datatip(...).Content 實測）：6 位有效數字；|v| < 1e-4、或四捨五入後 ≥ 1e15
    用指數（1.23457e-05、1e+15），其餘定點、不留尾零（1234567.89 → 1234570、32123456 → 32123500、0.0009463000877 → 0.0009463）。"""
    if v is None:
        return ""
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return str(v)
    if math.isnan(fv):
        return "NaN"
    if math.isinf(fv):
        return "Inf" if fv > 0 else "-Inf"
    if fv == 0:
        return "0"
    s = f"{fv:.6g}"
    if "e" in s:
        mant, exp = s.split("e")
        e = int(exp)
        if -4 <= e < 15:                                   # %g 會用指數的 1e6～1e15 之間：MATLAB 仍用定點
            return f"{round(fv, 5 - e):.0f}"
        return f"{mant}e{exp[0]}{abs(e):02d}"
    return s


def format_tip_text(label: str, x: float, y: float, xunit: str = "") -> str:
    """資料提示文字：第一列線的名稱（DSV 擴充；MATLAB 不顯示 DisplayName），再來像 MATLAB 的「X 值」「Y 值」兩列
    （標籤固定是 X／Y、不用軸標籤；數值用 MATLAB 的 'auto' 格式）。xunit 接在 X 值後面（DSV 擴充）。"""
    unit = f" {xunit}" if xunit else ""
    return f"{label}\nX {fmt_matlab(x)}{unit}\nY {fmt_matlab(y)}"


# 資料提示可以顯示的列（「提示內容…」；R2025a 的 Modify Data Tips／DataTipTemplate.DataTipRows）。順序固定：名稱、X、Y、樣本索引、panel。
TIP_FIELDS = ("name", "x", "y", "index", "panel")
DEFAULT_TIP_FIELDS = ("name", "x", "y")          # 預設＝原本的外觀（format_tip_text）


def parse_tip_fields(value) -> Tuple[str, ...]:
    """設定值（"name,x,y" 或 list）→ 依 TIP_FIELDS 順序的 tuple；不認得的略過，空的＝預設。"""
    if isinstance(value, (list, tuple, set)):
        items = {str(v).strip() for v in value}
    else:
        items = {v.strip() for v in str(value or "").split(",")}
    out = tuple(k for k in TIP_FIELDS if k in items)
    return out or DEFAULT_TIP_FIELDS


def format_tip_fields(rec: Dict[str, Any], fields: Sequence[str] = DEFAULT_TIP_FIELDS) -> str:
    """依勾選的列組資料提示文字。rec＝InteractorHost.tip_record()：name／x（顯示單位）／y／index（0 起算）／panel／xunit。
    X／Y 的寫法跟 format_tip_text 完全一樣（MATLAB 'auto' 格式）；樣本索引照 MATLAB 從 1 起算（Index 列）。"""
    fields = parse_tip_fields(fields)
    unit = f" {rec.get('xunit')}" if rec.get("xunit") else ""
    lines = []
    for k in fields:
        if k == "name":
            lines.append(str(rec.get("name", "")))
        elif k == "x":
            lines.append(f"X {fmt_matlab(rec.get('x'))}{unit}")
        elif k == "y":
            lines.append(f"Y {rec.get('y_text') or fmt_matlab(rec.get('y'))}")   # y_text：宿主給的進位制文字（DSV 匯流排）
        elif k == "index" and rec.get("index") is not None:
            lines.append(f"Index {int(rec['index']) + 1}")
        elif k == "panel" and rec.get("panel") not in (None, ""):
            lines.append(f"Panel {rec['panel']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 線
# ---------------------------------------------------------------------------
def series_line_kwargs(s: Series, style: Dict[str, Any], k: int, selected: bool = False) -> dict:
    color = s.color or auto_color(style, k)
    lw = float(s.lw) if s.lw else float(style.get("lw", 1.0))
    if selected:
        lw *= float(style.get("selected_lw_scale", 2.5))
    marker = s.marker if (s.marker and s.n <= MAX_MARKER_POINTS) else ""
    kw: Dict[str, Any] = {"color": color, "lw": lw, "ls": s.ls or "-", "alpha": float(s.alpha),
                          "label": s.label, "marker": marker or "None",
                          "ms": float(s.ms) if s.ms else float(style.get("ms", 4.0)),
                          "zorder": 3 if selected else 2}
    if s.kind == "step":
        kw["drawstyle"] = "steps-post"
        if marker and len(s.x) == s.n + 1:
            kw["markevery"] = slice(0, -1)        # 補出來的最後一點不畫 marker
    return kw


def draw_series(ax, s: Series, style: Dict[str, Any], k: int, selected: bool = False):
    x, y = s.plot_xy()
    ln, = ax.plot(x, y, **series_line_kwargs(s, style, k, selected))
    ln._pk_uid = s.uid
    return ln


BUS_FONTSIZE = 8.0


def draw_bus_series(ax, s: Series, style: Dict[str, Any], k: int, selected: bool = False,
                    band: Optional[Tuple[float, float]] = None):
    """Series.disp="digital"：畫成匯流排（plotkit.bus：值不變的區段畫六角框、框中寫數值）。
    回傳 (上緣 Line2D＝圖例／選取／改色的對象, {"art", "hit", "center", "half"})；band＝(中心, 半高)，None＝依自己的值範圍。
    x 視為等間隔（第一個樣本起點、間距＝x[1]−x[0]）。"""
    from matplotlib.lines import Line2D
    from . import bus as pbus
    n = s.n
    xs = np.asarray(s.x, dtype=float) + s.xshift
    x0 = float(xs[0])
    dx = float(xs[1] - xs[0]) if len(xs) > 1 else 1.0
    c, h = band if band is not None else pbus.band_from_values(np.asarray(s.y, dtype=float) + s.yshift)
    kw = series_line_kwargs(s, style, k, selected)
    for key in ("drawstyle", "markevery"):
        kw.pop(key, None)
    kw["marker"] = "None"
    ln, = ax.plot([x0, x0 + n * dx], [c + h, c + h], **kw)
    ln._pk_uid = s.uid
    hit = Line2D(xs[:n], np.full(n, c), visible=False, lw=1.0)
    ax.add_line(hit)
    hit._pk_uid = s.uid
    ext = Line2D([x0, x0 + n * dx], [c - h, c + h], visible=False)        # 自動範圍／還原視圖要含整個框
    ax.add_line(ext)
    art = pbus.HitBusArtist(ax, ln, x0, dx, np.asarray(s.y, dtype=float), c, h,
                            pbus.text_fn_for(s.radix, s.bits, fmt_num), fontsize=BUS_FONTSIZE, hit_line=hit)
    return ln, {"art": art, "hit": hit, "center": float(c), "half": float(h)}


def bus_bands(series: Sequence[Series], has_right: bool) -> Tuple[Dict[int, Tuple[float, float]], set]:
    """每一側（left／right）的線都是匯流排時一條一列（plotkit.bus.band_rows，由上而下），回 ({uid: band}, 只有匯流排的側)。
    和類比線混在一起的匯流排不在這裡（框＝自己的值範圍）。"""
    from . import bus as pbus
    out: Dict[int, Tuple[float, float]] = {}
    pure: set = set()
    for side in ("left", "right"):
        members = [s for s in series if s.visible and s.n and ("right" if (s.yaxis == "right" and has_right) else "left") == side]
        if members and all(s.is_bus for s in members):
            pure.add(side)
            for s, band in zip(members, pbus.band_rows(len(members))):
                out[s.uid] = band
    return out, pure


def restyle_line(ln, s: Series, style: Dict[str, Any], k: int, selected: bool = False) -> None:
    """不重畫資料，只更新既有 Line2D 的樣式。"""
    kw = series_line_kwargs(s, style, k, selected)
    ln.set_color(kw["color"])
    ln.set_linewidth(kw["lw"])
    ln.set_linestyle(kw["ls"])
    ln.set_alpha(kw["alpha"])
    ln.set_label(kw["label"])
    ln.set_marker(kw["marker"])
    ln.set_markersize(kw["ms"])
    ln.set_markevery(kw.get("markevery"))
    ln.set_zorder(kw["zorder"])
    ln.set_visible(s.visible)


LEGEND_ESCAPE = "\u200b"      # 零寬空白：matplotlib 會把「_」開頭的 label 從圖例剔除，前面加這個字就不會


def legend_label(label) -> str:
    """給 ax.legend() 用的文字：None → ""；「_」開頭的加零寬空白（顯示不變），圖例項目與 uid 才會一一對應。"""
    s = "" if label is None else str(label)
    return LEGEND_ESCAPE + s if s.startswith("_") else s


def build_legend(ax_top, handles: Sequence[Any], labels: Sequence[str], style: Dict[str, Any],
                 loc: Optional[str] = None):
    lg = dict(style.get("legend", {}))
    default_loc = lg.pop("loc", "upper right")
    loc = loc or default_loc
    lg.pop("fontsize", None)
    lg.pop("textcolor", None)
    frame_lw = lg.pop("lw", None)
    leg = ax_top.legend(list(handles), [legend_label(l) for l in labels], loc=loc, prop=text_kw(style, "legend"), **lg)
    leg.set_zorder(20)
    if isinstance(loc, (tuple, list)):      # 拖曳過的圖例可能在座標區外：不讓 constrained／tight layout 為它縮小 axes
        leg.set_in_layout(False)
    if frame_lw is not None:
        leg.get_frame().set_linewidth(float(frame_lw))
    tc = style.get("legend", {}).get("textcolor") or style.get("text_color")
    if tc:
        for txt in leg.get_texts():
            txt.set_color(tc)
    return leg


# ---------------------------------------------------------------------------
# 風格
# ---------------------------------------------------------------------------
def apply_style(fig, axes: Sequence[Any], style: Dict[str, Any], grid: bool = True) -> None:
    """把風格套到 fig 與 axes（含 twin，靠 ax._pk_role == "right" 辨認）。可重複呼叫。"""
    fam = resolved_fonts(style)
    fs = float(style.get("fontsize", 10.0))
    fig.set_facecolor(style.get("fig_face", "white"))
    g = style.get("grid", {})
    tc = style.get("text_color") or style.get("axes_edge", "black")
    for ax in axes:
        role = getattr(ax, "_pk_role", "left")
        ax.set_facecolor(style.get("axes_face", "white") if role == "left" else "none")
        for sp in ax.spines.values():
            sp.set_linewidth(float(style.get("axes_lw", 0.8)))
            sp.set_edgecolor(style.get("axes_edge", "black"))
            sp.set_visible(True)
        if role == "right":
            for name in ("top", "left", "bottom"):
                ax.spines[name].set_visible(False)
        elif not style.get("box", True):
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
        tp = {"direction": style.get("tick_dir", "out"), "labelsize": fs, "color": style.get("axes_edge", "black"),
              "labelcolor": tc}
        try:
            ax.tick_params(labelfontfamily=fam, **tp)
        except (TypeError, AttributeError):          # matplotlib < 3.7
            ax.tick_params(**tp)
            for lab in ax.get_xticklabels() + ax.get_yticklabels():
                lab.set_fontfamily(fam)
        try:
            ax.xaxis.get_offset_text().set_color(tc)
            ax.yaxis.get_offset_text().set_color(tc)
        except Exception:
            pass
        if role == "left":
            ax.tick_params(top=False, right=False)
            if grid:
                ax.grid(True, ls=g.get("ls", "-"), alpha=float(g.get("alpha", 0.3)),
                        color=g.get("color", "#b0b0b0"), lw=float(g.get("lw", 0.8)))
            else:          # matplotlib ≥ 3.5：grid(False, 加線型參數) 會「打開」格線，關的時候不能帶參數
                ax.grid(False)
            ax.set_axisbelow(True)
        else:
            ax.grid(False)
        t = style.get("title", {})
        ax.title.set_fontfamily(fam)
        ax.title.set_fontsize(fs * float(t.get("scale", 1.0)))
        ax.title.set_fontweight(t.get("weight", "normal"))
        ax.title.set_color(tc)
        for lab in (ax.xaxis.label, ax.yaxis.label):
            lab.set_fontfamily(fam)
            lab.set_fontsize(fs * float(style.get("label", {}).get("scale", 1.0)))
            lab.set_color(tc)
        leg = ax.get_legend()
        if leg is not None:
            lg = style.get("legend", {})
            for txt in leg.get_texts():
                txt.set_fontfamily(fam)
                txt.set_fontsize(float(lg.get("fontsize", fs)))
                txt.set_color(lg.get("textcolor") or tc)
            frame = leg.get_frame()
            frame.set_visible(bool(lg.get("frameon", True)))
            if "edgecolor" in lg:
                frame.set_edgecolor(lg["edgecolor"])
            if "facecolor" in lg:
                frame.set_facecolor(lg["facecolor"])
            if "framealpha" in lg:
                frame.set_alpha(float(lg["framealpha"]))
            if "lw" in lg:
                frame.set_linewidth(float(lg["lw"]))


# ---------------------------------------------------------------------------
# 標註與資料提示的 artist
# ---------------------------------------------------------------------------
REFLINE_LABEL_PAD_ALONG = 5.0    # MATLAB ConstantLine 標籤離座標區邊緣的像素
REFLINE_LABEL_PAD_ACROSS = 2.0   # 標籤離線的像素，再加線寬的一半


class ReflineLabel(Text):
    """參考線的標籤。線跑到座標軸範圍外時整個不畫：MATLAB R2025a 的 ConstantLine 出了 XLim／YLim 就連標籤一起消失
    （-batch exportgraphics 實測：xline(5) 配 XLim=[10 20]、xline(10.3) 配 XLim=[1 10] 都看不到線和標籤）；線在範圍內時
    標籤不裁切（靠邊時可以伸出座標區外，MATLAB 一樣）。matplotlib 的 axvline 自己會被裁掉，標籤要在 draw 時自己判斷。"""
    _pk_kind = "xline"
    _pk_value = 0.0

    def draw(self, renderer):
        ax = self.axes
        if ax is not None:
            lim = ax.get_xlim() if self._pk_kind == "xline" else ax.get_ylim()
            lo, hi = min(lim), max(lim)
            if not (lo <= float(self._pk_value) <= hi):
                return
        super().draw(renderer)


def _refline_label(ax, kind: str, value: float, x: float, y: float, text: str, **kw):
    t = ReflineLabel(x, y, text=text, **kw)
    t._pk_kind = kind
    t._pk_value = float(value)
    ax.add_artist(t)
    t.set_clip_on(False)        # 跟 ax.text 一樣不裁切：線在範圍內、靠邊時標籤可以伸出座標區（MATLAB edge_labels 實測）
    return t


def draw_annotation(ax, a: Annotation, style: Dict[str, Any]):
    """畫一個標註，回傳主要 artist（xline/yline 的文字掛在 artist._pk_label）。

    參考線的標籤照 MATLAB R2025a ConstantLine 的預設擺：LabelHorizontalAlignment='right'、LabelVerticalAlignment='top'、
    LabelOrientation='aligned'（-batch 實測）。xline 的標籤沿著線轉 90°、掛在線的右側、從座標區上緣往下排；
    yline 的標籤水平、靠右端、在線的上方。間距照 MATLAB R2025a 的 ConstantLine 標籤（
    沿線方向 5 px、垂直方向 2 px，再加線寬一半；aligned → 90°）。
    """
    color = a.color or style.get("annotation_color", "#444444")
    fam = resolved_fonts(style)
    # 字級：MATLAB 的 xline 標籤與 text 都是 FontSize 10（跟座標軸同字級）；風格的 annotation_fontsize 三套都是 10
    fs = float(a.fontsize or style.get("annotation_fontsize", style.get("fontsize", 10.0)))
    alpha = getattr(a, "alpha", 1.0)
    alpha = 1.0 if alpha is None else float(alpha)
    half_lw_px = float(a.lw) / 2.0 * float(ax.figure.dpi) / 72.0
    if a.kind == "xline":
        art = ax.axvline(a.value, color=color, lw=a.lw, ls=a.ls, alpha=alpha, zorder=4, visible=a.visible)
        if a.text:
            trans = offset_copy(ax.get_xaxis_transform(), fig=ax.figure, x=REFLINE_LABEL_PAD_ACROSS + half_lw_px,
                                y=-REFLINE_LABEL_PAD_ALONG, units="dots")
            art._pk_label = _refline_label(ax, "xline", a.value, a.value, 1.0, a.text, transform=trans, rotation=90,
                                           rotation_mode="anchor", ha="right", va="top", color=color, fontfamily=fam,
                                           fontsize=fs, zorder=5, visible=a.visible)
    elif a.kind == "yline":
        art = ax.axhline(a.value, color=color, lw=a.lw, ls=a.ls, alpha=alpha, zorder=4, visible=a.visible)
        if a.text:
            trans = offset_copy(ax.get_yaxis_transform(), fig=ax.figure, x=-REFLINE_LABEL_PAD_ALONG,
                                y=REFLINE_LABEL_PAD_ACROSS + half_lw_px, units="dots")
            art._pk_label = _refline_label(ax, "yline", a.value, 1.0, a.value, a.text, transform=trans, ha="right",
                                           va="bottom", color=color, fontfamily=fam, fontsize=fs, zorder=5, visible=a.visible)
    else:
        bbox = dict(boxstyle="round,pad=0.3", fc=style.get("annotation_box", "white"), ec=color, alpha=0.9) if a.boxed else None
        art = ax.text(a.x, a.y, a.text, ha=a.ha, va=a.va, color=color, fontfamily=fam, fontsize=fs, zorder=6,
                      bbox=bbox, visible=a.visible)
    art._pk_ann_id = a.id
    return art


TIP_BOX_PAD = 0.35             # 框內留白（字高的倍數）


def tip_anchor(offset) -> Tuple[str, str]:
    """offset 的正負號 → 文字框貼在資料點的哪一角（ha, va）：(+,+) 右上 northeast、(+,−) 右下 southeast、
    (−,+) 左上 northwest、(−,−) 左下 southwest（MATLAB DataTip.Location 的四種）。"""
    dx, dy = offset
    return ("left" if dx >= 0 else "right"), ("bottom" if dy >= 0 else "top")


def draw_tip(ax, tip: DataTip, x: float, y: float, text: str, style: Dict[str, Any]):
    """畫資料提示（照 MATLAB R2025a）：方框貼在資料點的一角、沒有連線、框底＝座標區底色、資料點是實心小圓。
    offset 以點為單位、正負號決定角落。回傳 (annotation, marker)。"""
    tp = style.get("tip", {})
    ha, va = tip_anchor(tip.offset)
    ann = ax.annotate(text, xy=(x, y), xytext=tuple(tip.offset), textcoords="offset points", ha=ha, va=va,
                      fontfamily=resolved_fonts(style), fontsize=float(tp.get("fontsize", 10)),
                      color=tp.get("text", style.get("text_color", "black")),
                      bbox=dict(boxstyle=f"square,pad={TIP_BOX_PAD}", fc=tp.get("fc", style.get("axes_face", "white")),
                                ec=tp.get("ec", "#7d7d7d"), lw=float(tp.get("lw", 1.0))),
                      zorder=50, annotation_clip=False)
    mk, = ax.plot([x], [y], marker="o", mfc=tp.get("marker_face", style.get("text_color", "black")),
                  mec=tp.get("marker_edge", "#ffffdc"), mew=1.0, ms=float(tp.get("ms", 5.0)), ls="", zorder=49,
                  scalex=False, scaley=False)          # 不要觸發自動縮放：否則第一次釘提示時視圖會跳
    ann._pk_tip_id = tip.id
    mk._pk_tip_id = tip.id
    return ann, mk


def place_tip(tip: DataTip, ann, renderer) -> None:
    """像 MATLAB 的 LocationMode='auto'（R2025a 實測：頂端的點 southeast、底端與中間 northeast、靠右 northwest）：
    框放在資料點的右上；上面放不下就放下面，右邊放不下就放左邊。改 tip.offset 的正負號並更新 artist。"""
    ax = ann.axes
    if ax is None or renderer is None:
        return
    try:
        bb = ann.get_window_extent(renderer)
        dpi = float(ax.figure.dpi)
        pad = TIP_BOX_PAD * ann.get_fontsize() * dpi / 72.0
        w, h = bb.width + 2 * pad, bb.height + 2 * pad
        px, py = ax.transData.transform(ann.xy)
    except Exception:
        return
    gap = (abs(tip.offset[0]) - pad * 72.0 / dpi) * dpi / 72.0
    axbb = ax.bbox
    sx = 1.0 if px + gap + w <= axbb.x1 else -1.0
    sy = 1.0 if py + gap + h <= axbb.y1 else -1.0
    tip.offset = (sx * abs(tip.offset[0]), sy * abs(tip.offset[1]))
    ha, va = tip_anchor(tip.offset)
    ann.xyann = tip.offset
    ann.set_horizontalalignment(ha)
    ann.set_verticalalignment(va)


def tip_offset_is_auto(offset) -> bool:
    """offset 的大小還是預設值（place_tip 只改正負號）＝自動擺放（像 MATLAB 的 LocationMode 'auto'）；拖曳過的就是手動（'manual'），視圖改變時不重擺。"""
    try:
        return (abs(abs(float(offset[0])) - TIP_OFFSET_DEFAULT[0]) < 1e-9 and
                abs(abs(float(offset[1])) - TIP_OFFSET_DEFAULT[1]) < 1e-9)
    except Exception:
        return False


def point_in_view(ax, x: float, y: float) -> bool:
    """資料點在座標範圍（XLim／YLim）內？MATLAB R2025a：資料點在範圍外時整個資料提示不畫（exportgraphics 實測）。"""
    try:
        x0, x1 = sorted(ax.get_xlim())
        y0, y1 = sorted(ax.get_ylim())
    except Exception:
        return True
    return bool(x0 <= x <= x1 and y0 <= y <= y1)


def remove_artist(art) -> None:
    for a in (getattr(art, "_pk_label", None), art):
        if a is None:
            continue
        try:
            a.remove()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 整張圖
# ---------------------------------------------------------------------------
def draw_state(fig, state: FigureState, *, selected: Sequence[int] = (), view: Optional[dict] = None,
               autoscale: bool = False) -> RenderInfo:
    """清掉 fig，依 state 畫線、圖例、軸標籤、風格與視圖範圍。"""
    style = get_style(state.style)
    fig.clear()
    ax = fig.add_subplot(111)
    ax._pk_role = "left"
    ax_r = None
    if state.has_right_axis():
        ax_r = ax.twinx()
        ax_r._pk_role = "right"
    info = RenderInfo(ax, ax_r, style=style)
    sel = set(selected)
    handles = []
    bands, bus_pure = bus_bands(state.series, ax_r is not None)
    for k, s in enumerate(state.series):
        if not s.visible or s.n == 0:
            continue
        tgt = ax_r if (s.yaxis == "right" and ax_r is not None) else ax
        if s.is_bus:
            ln, extra = draw_bus_series(tgt, s, style, k, selected=s.uid in sel, band=bands.get(s.uid))
            info.bus[s.uid] = extra
        else:
            ln = draw_series(tgt, s, style, k, selected=s.uid in sel)
        info.lines[s.uid] = ln
        handles.append(ln)
    if state.legend and handles:
        info.legend = build_legend(ax_r or ax, handles, [h.get_label() for h in handles], style, state.legend_loc)
        info.legend_uids = [h._pk_uid for h in handles]
    ax.set_title(state.title or "", **text_kw(style, "title"))
    xlabel = state.xlabel or (f"x [{state.xunit}]" if state.xunit else "")
    ax.set_xlabel(xlabel, **text_kw(style, "label"))
    ax.set_ylabel(state.ylabel or "", **text_kw(style, "label"))
    if ax_r is not None:
        ax_r.set_ylabel(state.ylabel_right or "", **text_kw(style, "label"))
    apply_style(fig, info.all_axes(), style, grid=state.grid)
    if ax_r is not None and not any(h.axes is ax for h in handles):      # 只有右軸有線：左軸的刻度沒意義，藏起來
        ax.tick_params(axis="y", which="both", left=False, labelleft=False)
    if "left" in bus_pure:                 # 只有匯流排的軸：一條一列，列的位置沒有數值意義 → 不要 y 刻度（和 DSV 主圖一樣）
        ax.set_yticks([])
    if "right" in bus_pure and ax_r is not None:
        ax_r.set_yticks([])
    v = dict(state.view)
    if view:
        v.update(view)
    if not autoscale and v.get("xlim"):
        ax.set_xlim(*v["xlim"])
    if not autoscale and v.get("ylim"):
        ax.set_ylim(*v["ylim"])
    if ax_r is not None and not autoscale and v.get("ylim_right"):
        ax_r.set_ylim(*v["ylim_right"])
    if autoscale or not handles:
        relim(ax)
        ax.autoscale_view()
        if ax_r is not None:
            relim(ax_r)
            ax_r.autoscale_view()
    for a in info.all_axes():          # 強制把（延遲計算的）自動範圍算好，transData 才正確（事件判定會用到）
        a.get_xlim()
        a.get_ylim()
    return info


def view_of(info: RenderInfo) -> dict:
    """目前的視圖範圍（給 state.view 用）。"""
    v = {"xlim": None, "ylim": None, "ylim_right": None}
    if info.ax_left is not None:
        v["xlim"] = [float(a) for a in info.ax_left.get_xlim()]
        v["ylim"] = [float(a) for a in info.ax_left.get_ylim()]
    if info.ax_right is not None:
        v["ylim_right"] = [float(a) for a in info.ax_right.get_ylim()]
    return v


# ---------------------------------------------------------------------------
# 幾何／點選
# ---------------------------------------------------------------------------
def axes_at(fig, event) -> list:
    """包含滑鼠位置的所有 axes（twin 會一起回來；順序＝fig.axes 的順序，host 在前）。"""
    out = []
    for ax in fig.get_axes():
        try:
            if ax.get_visible() and ax.bbox.contains(event.x, event.y):
                out.append(ax)
        except Exception:
            continue
    return out


def data_coords(ax, event) -> Tuple[float, float]:
    x, y = ax.transData.inverted().transform((event.x, event.y))
    return float(x), float(y)


FAST_HIT_MIN_POINTS = 2000      # 點數超過這個、x 已排序的線：只看游標附近那一段（hover 每個 motion 都要判定）


def _line_x_sorted(ln, xy) -> bool:
    """線的 x（matplotlib 轉換後的 _xy）是否非遞減；同一份資料只算一次（set_data 會換新的 _xy）。"""
    c = getattr(ln, "_pk_xsorted", None)
    if c is not None and c[0] is xy:
        return c[1]
    x = xy[:, 0]
    with np.errstate(invalid="ignore"):
        flag = bool(len(x) > 1 and np.all(np.diff(x) >= 0))
    try:
        ln._pk_xsorted = (xy, flag)
    except Exception:
        pass
    return flag


def _line_hit_fast(ln, event, tol_px: float):
    """長的線（x 已排序、直角座標）只看游標左右 ±tol 像素內的樣本：回傳 (命中?, 最近頂點的像素距離)；
    不適用（點數少、x 沒排序、非直角座標）回傳 None，改走 Line2D.contains。
    判定與 Line2D.contains 相同（有線型＝筆劃各段 segment_hits，沒線型＝頂點；steps 先轉成階梯路徑）；
    最近頂點距離與「整個視圖內的頂點取最小」相同（視窗外的頂點 x 方向就比目前最小值遠，不用看）。"""
    from matplotlib import cbook
    from matplotlib.lines import segment_hits
    try:
        xy = ln.get_xydata()
    except Exception:
        return None
    n = len(xy)
    ax = ln.axes
    if n < FAST_HIT_MIN_POINTS or ax is None or xy.ndim != 2:
        return None
    tr = ln.get_transform()
    if not getattr(tr, "is_separable", False) or not _line_x_sorted(ln, xy):
        return None
    ds = ln.get_drawstyle() or "default"
    step = cbook.STEP_LOOKUP_MAP.get(ds) if ds != "default" else None
    if ds != "default" and step is None:
        return None
    xs = xy[:, 0]
    inv = tr.inverted()
    ex, ey = float(event.x), float(event.y)

    def window(r_px: float) -> Tuple[int, int]:
        xa = inv.transform((ex - r_px, ey))[0]
        xb = inv.transform((ex + r_px, ey))[0]
        lo, hi = (xa, xb) if xa <= xb else (xb, xa)
        if not (np.isfinite(lo) and np.isfinite(hi)):
            raise ValueError("window")
        return max(0, int(np.searchsorted(xs, lo, "left")) - 2), min(n, int(np.searchsorted(xs, hi, "right")) + 2)

    try:
        with np.errstate(all="ignore"):
            i0, i1 = window(tol_px + 1.0)
            if i1 - i0 > 50000:                   # 一個像素塞了大量樣本：視窗本身就很大，交回 contains（結果一樣）
                return None
            sx, sy = xs[i0:i1], xy[i0:i1, 1]
            if step is not None:
                px = tr.transform(np.column_stack(step(sx, sy)))
            else:
                px = tr.transform(xy[i0:i1])
            if ln.get_linestyle() in ("None", "none", " ", "", None):
                ok = bool(np.any((px[:, 0] - ex) ** 2 + (px[:, 1] - ey) ** 2 <= tol_px ** 2))
            else:
                ok = len(segment_hits(ex, ey, px[:, 0], px[:, 1], tol_px)) > 0
            if not ok:
                return False, float("inf")
            # 最近頂點（只算視圖內，同舊的寫法：視圖左右各多一點）
            v0, v1 = sorted(ax.get_xlim())
            j0 = max(0, int(np.searchsorted(xs, v0)) - 1)
            j1 = min(n, int(np.searchsorted(xs, v1)) + 1)
            r = tol_px + 1.0
            for _ in range(4):
                a, b = window(r)
                a, b = max(a, j0), min(b, j1)
                if b <= a:
                    d = float("nan")
                else:
                    pv = tr.transform(xy[a:b])
                    d = float(np.nanmin(np.hypot(pv[:, 0] - ex, pv[:, 1] - ey))) if len(pv) else float("nan")
                if not np.isfinite(d):
                    return None                   # 附近全是 NaN：交回慢的完整算法
                if d <= r:
                    return True, d
                r = d + 1.0                       # 視窗外的頂點 x 方向就超過 r，視窗放大到 d 就一定找到最小值
            return None
    except Exception:
        return None


def hit_test_lines(lines, event):
    """滑鼠點到哪條線：線的筆劃在游標 ±PICK_TOL_PX（2 邏輯 px；顯示縮放時乘 device_pixel_ratio）內就算；
    幾條都在範圍內時取頂點離游標最近的那條。長的線只看游標附近（_line_hit_fast），hover 每個 motion 都會呼叫。"""
    best, best_d = None, None
    for ln in lines:
        fig = ln.figure
        dpi = float(fig.dpi) if fig is not None else 72.0
        # PICK_TOL_PX 是邏輯像素：Windows／Linux 顯示縮放時事件座標是實體像素，乘 device_pixel_ratio（線寬那半已隨 dpi 放大）
        dpr = float(getattr(getattr(fig, "canvas", None), "device_pixel_ratio", 1) or 1) if fig is not None else 1.0
        tol_px = PICK_TOL_PX * dpr + 0.5 * float(ln.get_linewidth() or 0.0) * dpi / 72.0
        fast = _line_hit_fast(ln, event, tol_px)
        if fast is not None:
            ok, d = fast
            if ok and (best is None or d < best_d):
                best, best_d = ln, d
            continue
        old = ln.get_pickradius()
        try:
            ln.set_pickradius(tol_px * 72.0 / dpi)        # Line2D.contains 的 pickradius 以點計
            ok, _ = ln.contains(event)
        except Exception:
            ok = False
        finally:
            try:
                ln.set_pickradius(old)
            except Exception:
                pass
        if not ok:
            continue
        ax = ln.axes
        xd = np.asarray(ln.get_xdata(orig=True), dtype=float)
        yd = np.asarray(ln.get_ydata(orig=True), dtype=float)
        if len(xd) == 0 or ax is None:
            continue
        x0, x1 = sorted(ax.get_xlim())
        if len(xd) > 1 and np.all(np.diff(xd) >= 0):
            i0 = max(0, int(np.searchsorted(xd, x0)) - 1)
            i1 = min(len(xd), int(np.searchsorted(xd, x1)) + 1)
        else:
            i0, i1 = 0, len(xd)
        seg = np.column_stack([xd[i0:i1], yd[i0:i1]])
        if len(seg) == 0:
            continue
        px = ax.transData.transform(seg)
        d = float(np.nanmin(np.hypot(px[:, 0] - event.x, px[:, 1] - event.y)))
        if best is None or d < best_d:
            best, best_d = ln, d
    return best


def nearest_vertex(xv: np.ndarray, yv: np.ndarray, ax, px: float, py: float, x_sorted: Optional[bool] = None) -> int:
    """離像素點 (px, py) 最近的「有限值」頂點索引；整條都沒有有限值回傳 -1。x 單調時先只比附近幾個點。"""
    n = len(yv)
    if n == 0:
        return -1
    if x_sorted is None:
        x_sorted = bool(n > 8 and np.all(np.diff(xv) >= 0))
    idx = None
    if x_sorted and n > 8:
        # 候選範圍 = 游標左右 R 像素內的樣本（密到一個像素好幾個樣本時 ±3 個不夠）；太多就等距取樣
        inv = ax.transData.inverted()
        r_px = PICK_RADIUS_PT * float(ax.figure.dpi) / 72.0 + 2.0
        xa = inv.transform((px - r_px, py))[0]
        xb = inv.transform((px + r_px, py))[0]
        lo = int(np.searchsorted(xv, min(xa, xb))) - 1
        hi = int(np.searchsorted(xv, max(xa, xb))) + 2
        lo, hi = max(0, lo), min(n, hi)
        if hi - lo < 7:
            i0 = int(np.searchsorted(xv, inv.transform((px, py))[0]))
            lo, hi = max(0, i0 - 3), min(n, i0 + 4)
        step = max(1, (hi - lo) // 5000)
        idx = np.arange(lo, hi, step)
    if idx is None:
        idx = np.arange(n)
    for cand in (idx, None):
        if cand is None:                                   # 附近都是 NaN／inf：整條找有限值的點
            cand = np.flatnonzero(np.isfinite(xv) & np.isfinite(yv))
            if len(cand) == 0:
                return -1
        pts = ax.transData.transform(np.column_stack([xv[cand], yv[cand]]))
        d = np.hypot(pts[:, 0] - px, pts[:, 1] - py)
        if np.any(np.isfinite(d)):
            return int(cand[int(np.nanargmin(d))])
    return -1


def nearest_index(s: Series, ax, px: float, py: float) -> int:
    """離像素點 (px, py) 最近的樣本索引（0..n-1）；沒有有限值的點回傳 -1。"""
    n = s.n
    if n == 0:
        return -1
    return nearest_vertex(s.x[:n] + s.xshift, s.y + s.yshift, ax, px, py, x_sorted=s.x_sorted)


def ruler_zones(fig, renderer) -> List[Tuple[Any, str, Any]]:
    """每個 axes 的尺規區 [(ax, 'x'|'y', Bbox)]：軸線到刻度文字外緣之間（MATLAB 的 ruler＝軸線、刻度、刻度文字；不含軸標籤）。
    MATLAB 的 rulerPanInteraction：拖曳尺規只沿該軸平移。sharex 上面的 panel 沒有刻度文字就沒有 x 尺規區；
    twin 右軸的刻度文字在右邊＝右軸的 y 尺規。"""
    from matplotlib.transforms import Bbox
    zones: List[Tuple[Any, str, Any]] = []
    for ax in fig.get_axes():
        if not ax.get_visible():
            continue
        bb = ax.bbox
        for axis, which in ((ax.xaxis, "x"), (ax.yaxis, "y")):
            if not axis.get_visible():
                continue
            try:
                labels = [t for t in axis.get_majorticklabels() if t.get_visible() and t.get_text()]
                boxes = [t.get_window_extent(renderer) for t in labels]
            except Exception:
                continue
            boxes = [b for b in boxes if b.width > 0 and b.height > 0]
            if which == "x":
                below = [b for b in boxes if (b.y0 + b.y1) / 2 < bb.y0]
                above = [b for b in boxes if (b.y0 + b.y1) / 2 > bb.y1]
                if below:
                    zones.append((ax, "x", Bbox.from_extents(bb.x0, min(b.y0 for b in below), bb.x1, bb.y0)))
                if above:
                    zones.append((ax, "x", Bbox.from_extents(bb.x0, bb.y1, bb.x1, max(b.y1 for b in above))))
            else:
                left = [b for b in boxes if (b.x0 + b.x1) / 2 < bb.x0]
                right = [b for b in boxes if (b.x0 + b.x1) / 2 > bb.x1]
                if left:
                    zones.append((ax, "y", Bbox.from_extents(min(b.x0 for b in left), bb.y0, bb.x0, bb.y1)))
                if right:
                    zones.append((ax, "y", Bbox.from_extents(bb.x1, bb.y0, max(b.x1 for b in right), bb.y1)))
    return zones


def ruler_at(zones, x: float, y: float) -> Optional[Tuple[Any, str]]:
    """像素點 (x, y) 落在哪個尺規區：回 (ax, 'x'|'y') 或 None。"""
    for ax, which, bb in zones:
        if bb.x0 <= x <= bb.x1 and bb.y0 <= y <= bb.y1:
            return ax, which
    return None


def zoom_limits(lo: float, hi: float, c: float, scale: float) -> Tuple[float, float]:
    """以 c 為中心把 [lo, hi] 縮放 scale 倍（<1 放大）。"""
    return c - (c - lo) * scale, c + (hi - c) * scale


def pan_limits(lo: float, hi: float, d: float) -> Tuple[float, float]:
    """滑鼠往正方向拖 d（資料單位）→ 視窗往負方向移。"""
    return lo - d, hi - d


def wheel_notches(event) -> float:
    """滾輪格數（可為小數，由 Interactor 累加）：macOS TkAgg 每格 step=±1/120 → ±1；
    Windows 滑鼠每格 ±1、精準觸控板一次只有 ±0.1 左右（累加到 1 才算一格）；限制 ±3。"""
    import sys as _sys
    step = float(getattr(event, "step", 0) or 0)
    if step == 0 or not np.isfinite(step):
        return 0.0
    if _sys.platform == "darwin" and abs(step) < 1:
        step *= 120
    return max(-3.0, min(3.0, step))


def has_mod(event, name: str) -> bool:
    """修飾鍵是否按著：先看 event.modifiers（可靠），再看 event.key（合成事件用）。"""
    name = name.lower()
    mods = getattr(event, "modifiers", None)
    if mods:
        if name in {str(m).lower() for m in mods}:
            return True
    key = getattr(event, "key", None) or ""
    return name in str(key).lower().split("+")
