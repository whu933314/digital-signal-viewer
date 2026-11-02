# -*- coding: utf-8 -*-
"""plotkit.interact — 掛在任何 Tk 內嵌 matplotlib 圖上的互動層（像 MATLAB 的預設互動）。

提供：滾輪縮放（以游標為中心）、左鍵在空白處拖曳平移、雙擊空白／Home 還原視圖、
釘住式資料提示（可拖、可刪、重畫後保留）、圖例文字雙擊就地改名、拖曳圖例移動位置（MATLAB 預設就能拖）、
點線條回呼、文字標註拖曳、右鍵回呼（含 MATLAB 圖例右鍵選單的「刪除」「位置」）。

host 實作 InteractorHost 的方法把「畫面上的線」「資料」「軸」告訴 Interactor；
Interactor 只持有資料提示與標註的模型（InteractorModel）與它們的 artist。
"""
from __future__ import annotations

import math
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .draw import LEGEND_ESCAPE, nearest_vertex, place_tip, point_in_view, relim, tip_offset_is_auto
from .draw import DEFAULT_TIP_FIELDS, fmt_matlab, format_tip_fields, parse_tip_fields
from .draw import (axes_at, data_coords, draw_annotation, draw_tip, format_tip_text, has_mod,
                   hit_test_lines, pan_limits, remove_artist, ruler_at, ruler_zones, wheel_notches, zoom_limits)
from .i18n import tr
from .menus import popup_menu
from . import keys as _keys
from .model import TIP_OFFSET_DEFAULT, Annotation, DataTip
from .styles import get_style

DRAG_THRESHOLD_PX = 10.0     # 拖曳門檻 10 px：按下後移 ≥10 px 才算拖，不到＝點一下
# 縮放常數（滾輪、放大模式的點擊與拖框、鍵盤縮放）
ZOOM_BASE = 1.1          # 滾輪縮放：每次事件放大倍數有上限 1.1（滑鼠一格就是 1.1 倍；觸控板的小數格按比例）
STEP_ZOOM = 1.5          # 放大模式裡單擊＝以該點為中心放大 1.5 倍（Shift＋單擊＝1/1.5）
DRAG_POINT_ZOOM = 1.2    # 放大模式裡拖了、但框的兩邊都不到 15 px → 以點為中心 1.2 倍
POINT_MODE_PX = 15       # 放大模式的框：框的一邊 < 15 px → 那個方向不縮
CLICK_PX = 10            # 拖曳門檻：按下後移不到 10 px 算 click（1.5 倍），10～15 px 算小拖（1.2 倍）
KEY_ZOOM = 1.1           # 鍵盤縮放倍率 1.1：＋／＝放大、−縮小（zoom 模式裡 ↑／↓ 也是），以座標區中心為準
# 鍵（matplotlib key_press_event.key，小寫；含修飾鍵如 "ctrl+left"）→ 圖上的動作名。Interactor.key_map 是它的複本，
# host 可以整個換掉（DSV 的快速鍵設定）。動作名：restore_view／zoom_in／zoom_out／pan_left／pan_right／pan_up／pan_down／delete／escape
DEFAULT_KEY_MAP = {"home": "restore_view", "+": "zoom_in", "=": "zoom_in", "plus": "zoom_in", "equal": "zoom_in",
                   "-": "zoom_out", "minus": "zoom_out", "left": "pan_left", "right": "pan_right", "up": "pan_up", "down": "pan_down",
                   "delete": "delete", "backspace": "delete", "escape": "escape"}
KEY_ACTIONS = ("restore_view", "zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", "delete", "escape")
KEY_PAN_PX = 5.0             # 方向鍵每按一下＝往該方向拖曳 5 像素
# 游標：(macOS aqua, 其他)。MATLAB R2025a 預設互動：在座標區拖曳平移時游標不變，
# 尺規上是手＋↔／↕（懸停尺規就顯示）。
# Tk 沒有手＋箭頭的游標，尺規用雙箭頭；座標區內的平移不換游標。
# 游標在可以放資料提示的線上＝crosshair（和 MATLAB 一樣）。
CURSORS = {"ruler_x": ("resizeleftright", "sb_h_double_arrow"), "ruler_y": ("resizeupdown", "sb_v_double_arrow"),
           "crosshair": ("crosshair", "crosshair"), "cursor_x": ("resizeleftright", "sb_h_double_arrow"),
           "cursor_y": ("resizeupdown", "sb_v_double_arrow")}
HOVER_LINGER_MS = 200      # 提示框 200 ms：游標在線上停 200 ms 才出現暫時的提示框

# 圖例右鍵選單的「位置」：MATLAB 圖例預設右鍵選單 Location 子選單的項目（Northeast／Northwest／Southeast／Southwest／Best；
# East Outside／Northeast Outside 要畫到座標區外面，plotkit 不支援，略過），對應 matplotlib 的 loc 名稱。
LEGEND_LOCS = (("右上", "upper right"), ("左上", "upper left"), ("右下", "lower right"), ("左下", "lower left"), ("最佳", "best"))

# macOS（Tk 8.6）的觸控板補償。Tk 8.6 把每個 NSScrollWheel 都變成 delta ≥ ±1 的 <MouseWheel>
# （|deltaY| < 1 也算 ±1，慣性階段照送，沒有 hasPreciseScrollingDeltas），觸控板一次滑動有幾十～上百個事件，
# 每個都當一格（1.1 倍）會一次縮放幾千～幾億倍。滑鼠一格仍是一格；連續、密集的事件改成「依時間計量＋衰減」。
MAC_WHEEL_GAP = 0.20            # 停超過這麼久（而且不是剛畫完圖）就算新的一串捲動
MAC_WHEEL_GAP_AFTER_DRAW = 0.06  # 圖剛畫完這麼短時間內到的事件＝重畫時排隊的，算同一串
MAC_WHEEL_GAP_BUSY = 0.50       # …但距上一個滾輪事件超過這麼久就不是排隊，是新的一串
MAC_WHEEL_STEP_DT = 0.07        # 同一串裡每個事件權重 = 間隔 / 0.07 s（最多 1）：縮放量跟時間成正比，不跟事件數
MAC_WHEEL_BUDGET_MAX = 0.30     # 時間額度上限：重畫期間排隊、一起到的事件分攤這段時間（滑鼠 10 格/秒不會被打折），但不累積成大跳
MAC_WHEEL_DENSE_N = 5           # 0.25 s 內 ≥ 5 個事件＝觸控板／慣性（滑鼠一格一格不會這麼密）
MAC_WHEEL_DENSE_WIN = 0.25
MAC_WHEEL_GRACE = 0.25          # 密集串：開始 0.25 s 後依時間衰減（慣性尾巴）
MAC_WHEEL_TAU = 0.30
MAC_WHEEL_CAP = 5.0             # 密集串累積格數的軟上限


IS_MAC = sys.platform == "darwin"


def _now() -> float:
    """單調時鐘（selftest 會換掉它來模擬 60 Hz 的觸控板事件）。"""
    return time.monotonic()


def is_context_click(event) -> bool:
    """右鍵；macOS 上 Control＋左鍵也算右鍵（觸控板常用；MATLAB 的 SelectionType 'alt' 也是這樣）。"""
    b = getattr(event, "button", None)
    return b == 3 or (IS_MAC and b == 1 and has_mod(event, "ctrl"))


def end_toolbar_zoom(toolbar) -> None:
    """結束（或取消）matplotlib 工具列放大模式正在拖的框：斷開拖曳 callback、移除框、重畫、_zoom_info=None。
    等同 matplotlib 3.11 的 NavigationToolbar2._cleanup_post_zoom；3.10 以前沒有這個方法，所以自己做（各版本行為一致）。
    _zoom_info 已經是 None 時只重畫。"""
    info = getattr(toolbar, "_zoom_info", None)
    canvas = getattr(toolbar, "canvas", None)
    if info is not None and canvas is not None:
        try:
            canvas.mpl_disconnect(info.cid)
        except Exception:
            pass
    try:
        toolbar.remove_rubberband()
    except Exception:
        pass
    try:
        toolbar._zoom_info = None
    except Exception:
        pass
    if canvas is not None:
        try:
            canvas.draw_idle()
        except Exception:
            pass


def _axis_is_linear(axis) -> bool:
    try:
        return axis.get_scale() == "linear"
    except Exception:
        return True


def scaled_zoom(axis, lims, c: float, scale: float) -> Tuple[float, float]:
    """在軸的尺度空間（linear／log／symlog…）以 c 為中心縮放；線性軸和 zoom_limits 完全一樣。"""
    if _axis_is_linear(axis):
        return zoom_limits(lims[0], lims[1], c, scale)
    try:
        tr = axis.get_transform()
        lo, hi, cc = tr.transform(np.array([lims[0], lims[1], c], dtype=float))
        nlo, nhi = zoom_limits(lo, hi, cc, scale)
        out = tr.inverted().transform(np.array([nlo, nhi], dtype=float))
        if np.all(np.isfinite(out)):
            return float(out[0]), float(out[1])
    except Exception:
        pass
    return tuple(lims)


def scaled_pan(axis, lims, dpix: float, size: float) -> Tuple[float, float]:
    """拖曳 dpix 像素（軸長 size 像素）後的新範圍；log 軸在尺度空間平移，線性軸和原本算法一樣。"""
    if _axis_is_linear(axis):
        d = (lims[1] - lims[0]) / max(size, 1) * dpix      # 先除再乘：±1e308 的範圍乘像素會溢位成 inf
        out = pan_limits(lims[0], lims[1], d)
        return out if all(math.isfinite(v) for v in out) else tuple(lims)
    try:
        tr = axis.get_transform()
        lo, hi = tr.transform(np.array(lims, dtype=float))
        d = (hi - lo) / max(size, 1) * dpix
        out = tr.inverted().transform(np.array(pan_limits(lo, hi, d), dtype=float))
        if np.all(np.isfinite(out)):
            return float(out[0]), float(out[1])
    except Exception:
        pass
    return tuple(lims)


MAX_DRAWABLE_LIM = 8e307     # matplotlib 3.10／3.11 實測：|範圍端點| ≥ 1e308 時刻度計算（MaxNLocator 的 arange）溢位，整張圖畫不出來


def drawable_limits(lims) -> bool:
    """新的座標範圍畫得出來：兩端有限且在 ±MAX_DRAWABLE_LIM 之內（平移／縮放推到這之外就不動，避免每次重畫都丟例外）。"""
    try:
        return all(math.isfinite(float(v)) and abs(float(v)) < MAX_DRAWABLE_LIM for v in lims)
    except (TypeError, ValueError):
        return False


def x_linked(a, b) -> bool:
    """兩個座標區的 x 是否同步：matplotlib sharex（含 twin），或 host 標了同一個 _pk_xlink（例如 DSV 的「連結時間」
    在 Symbol rate 不同的 panel 之間用換算同步，不是 sharex）。縮小等「每個座標區各縮一次」的動作靠它避免重複縮。"""
    try:
        if a.get_shared_x_axes().joined(a, b):
            return True
    except Exception:
        pass
    ga, gb = getattr(a, "_pk_xlink", None), getattr(b, "_pk_xlink", None)
    return ga is not None and ga == gb


def auto_limits(ax, which: str) -> Optional[Tuple[float, float]]:
    """matplotlib 自動縮放（autoscale_view，axes.autolimit_mode='data'）會給的範圍，不動 axes：
    dataLim（含 sharex／sharey 的兄弟）加 margins，log 軸在 log 空間加邊距；沒有資料就 None。
    這就是 MATLAB InteractionOptions.OuterXLimits／OuterYLimits 的預設值（自動範圍；手動設了 XLim 也不變）。"""
    try:
        axis = ax.xaxis if which == "x" else ax.yaxis
        grp = ax.get_shared_x_axes() if which == "x" else ax.get_shared_y_axes()
        shared = list(grp.get_siblings(ax)) or [ax]
        vals = [float(v) for a in shared for v in getattr(a.dataLim, "interval" + which) if np.isfinite(v)]
        if not vals:
            return None
        lo, hi = min(vals), max(vals)
        loc = axis.get_major_locator()
        lo, hi = loc.nonsingular(lo, hi)
        if axis.get_scale() == "log":
            minpos = min(float(getattr(a.dataLim, "minpos" + which)) for a in shared)
            if not np.isfinite(minpos) or minpos <= 0:
                return None
            lo, hi = (lo if lo > 0 else minpos), (hi if hi > 0 else minpos)
        margin = float(ax.margins()[0 if which == "x" else 1])
        tr_ = axis.get_transform()
        t0, t1 = tr_.transform(np.array([lo, hi], dtype=float))
        d = (t1 - t0) * margin
        if not np.isfinite(d):
            d = 0.0
        lo, hi = tr_.inverted().transform(np.array([t0 - d, t1 + d], dtype=float))
        lo, hi = loc.view_limits(lo, hi)
        if not (np.isfinite(lo) and np.isfinite(hi)) or lo == hi:
            return None
        return float(lo), float(hi)
    except Exception:
        return None


def within_limits(lims, bounds) -> bool:
    """lims 在 bounds 之內（照 MATLAB 縮放的界限判斷）（容差 1e-5 × bounds 的寬）。"""
    a = sorted((float(lims[0]), float(lims[1])))
    b = sorted((float(bounds[0]), float(bounds[1])))
    tol = abs(b[1] - b[0]) * 1e-5
    return b[0] <= a[0] + tol and b[1] + tol >= a[1]


def bound_limits(new, bounds) -> Tuple[float, float]:
    """新範圍的每一邊各自夾在外界之內（照 MATLAB 縮放的界限，DataAspectRatioMode auto）。"""
    lo, hi = float(new[0]), float(new[1])
    rev = lo > hi
    if rev:
        lo, hi = hi, lo
    b0, b1 = sorted((float(bounds[0]), float(bounds[1])))
    tol = abs(hi - lo) * 1e-5
    if lo - b0 <= tol:
        lo = b0
    if b1 - hi <= tol:
        hi = b1
    return (hi, lo) if rev else (lo, hi)


def axes_center_px(ax) -> Tuple[float, float]:
    bb = ax.bbox
    return (bb.x0 + bb.x1) / 2.0, (bb.y0 + bb.y1) / 2.0


@dataclass
class Hit:
    kind: str = "outside"        # tip | text | legend | legend_box | cursor | refline | line | empty | ruler | outside
    ax: Any = None
    artist: Any = None
    id: Any = None               # line → uid；tip → tip id；text/refline → annotation id；legend → uid；ruler → 'x'／'y'；cursor → 0／1（垂直）或 ("h", 鍵, 0／1)（水平）
    index: Optional[int] = None  # line → 最近的樣本索引
    legend_index: Optional[int] = None


class InteractorModel:
    """資料提示與標註的清單；可以直接傳入 FigureState／DSV 的 list，大家共用同一個物件。"""

    def __init__(self, tips: Optional[List[DataTip]] = None, annotations: Optional[List[Annotation]] = None):
        self.tips: List[DataTip] = tips if tips is not None else []
        self.annotations: List[Annotation] = annotations if annotations is not None else []

    def next_tip_id(self) -> int:
        return max([t.id for t in self.tips], default=0) + 1

    def next_ann_id(self) -> int:
        return max([a.id for a in self.annotations], default=0) + 1

    def find_tip(self, tip_id: int) -> Optional[DataTip]:
        return next((t for t in self.tips if t.id == tip_id), None)

    def find_ann(self, ann_id: int) -> Optional[Annotation]:
        return next((a for a in self.annotations if a.id == ann_id), None)


class InteractorHost:
    """Interactor 需要 host 提供的資訊與回呼；全部有預設實作（no-op），只覆寫需要的。"""

    def style(self) -> dict:
        return get_style("default")

    def lines_in(self, ax) -> List[Tuple[int, Any]]:
        """這個 axes 上可點選的線：[(uid, Line2D), ...]。"""
        return []

    def series_data(self, uid: int):
        """回傳 (x_vertices, y_vertices, label, axes)，頂點是畫出來的位置（已含位移）；沒有這條線回 None。"""
        return None

    def axes_for_key(self, key):
        return None

    def axes_key_for(self, ax):
        return None

    def legend_entries(self, ax) -> List[int]:
        """這個 axes 的圖例每一項對應的 uid（順序同 legend.get_texts()）。"""
        return []

    def tip_text(self, uid: int, index: int, x: float, y: float) -> str:
        data = self.series_data(uid)
        label = data[2] if data else str(uid)
        return format_tip_text(label, x, y)

    def display_x(self, ax, x: float) -> float:
        """資料 x → 畫面上顯示的 x（右鍵選單標籤用；例如 DSV 內部用 symbol、畫面用 us）。"""
        return x

    def tip_record(self, uid: int, index: int, x: float, y: float) -> dict:
        """一個資料提示的內容（「提示內容…」的列、匯出資料提示、提示間的 Δ 都用它）：
        name、x（顯示單位）、y（顯示的值）、index（樣本索引，0 起算）、panel（座標區的名字）、xunit。"""
        data = self.series_data(uid)
        ax = data[3] if data else None
        key = self.axes_key_for(ax) if ax is not None else None
        return {"name": data[2] if data else str(uid), "x": self.display_x(ax, x), "y": y, "index": int(index),
                "panel": "" if key is None else str(key), "xunit": ""}

    def on_tip_fields(self, fields: Tuple[str, ...]) -> None:
        """「提示內容…」改了要顯示的列（host 存進設定檔／圖檔）；Interactor 已經套用到全部提示。"""
        pass

    def home_view(self, ax):
        """回 ((x0,x1),(y0,y1)) 或 None（None = relim + autoscale）。"""
        return None

    def outer_limits(self, ax):
        """縮放的外界（MATLAB InteractionOptions.OuterXLimits／OuterYLimits；和 MATLAB 預設一樣，縮小到此為止）。
        回 ((x0,x1) 或 None, (y0,y1) 或 None)，None＝用 matplotlib 的自動範圍（auto_limits）；整個回 None 也一樣。"""
        return None

    def on_restore_view(self) -> bool:
        """回 True 表示 host 自己處理了還原視圖。"""
        return False

    def on_pick(self, uid: int, event, hit: Hit) -> None:
        pass

    def on_click_empty(self, event) -> None:
        pass

    def on_double_click(self, hit: Hit, event) -> bool:
        return False

    def on_context(self, hit: Hit, event) -> None:
        pass

    def on_rename(self, uid: int, label: str) -> None:
        pass

    def on_legend_move(self, ax, loc) -> None:
        """圖例被拖到新位置：loc = 圖例左下角在 axes 座標的 (x, y)（MATLAB 不用開 plot edit 就能拖圖例）。"""
        pass

    def on_legend_loc(self, ax, loc: str) -> None:
        """右鍵選單選了圖例位置（matplotlib 的 loc 名稱，例如 "upper right"）。"""
        pass

    def on_legend_delete(self, ax) -> None:
        """右鍵選單「刪除圖例」（MATLAB 圖例右鍵選單的 Delete）。"""
        pass

    def on_edit_text(self, ann_id: int, text: str) -> None:
        pass

    def on_edit_annotation(self, ann_id: int) -> None:
        pass

    def on_insert(self, kind: str, ax, x: float, y: float) -> None:
        pass

    def before_model_change(self, what: str, tag: Optional[str] = None) -> None:
        """模型（提示／標註）要改之前（undo 推入點）。"""
        pass

    def on_model_change(self, what: str) -> None:
        pass

    def on_model_cancel(self, what: str) -> None:
        """拖曳被 Esc 取消：before_model_change 已經推過的 undo 可以拿掉。"""
        pass

    def on_view_change(self, ax) -> None:
        pass

    def before_view_change(self, tag: str) -> None:
        """鍵盤縮放／平移要改視圖「之前」（undo 推入點）。MATLAB R2025a：鍵盤 pan／zoom（預設互動與 pan／zoom 模式）
        放開按鍵時把改動前的範圍放進圖形視窗的 undo（和 MATLAB 一樣），Ctrl+Z 復原的是視圖。同一個 tag 連按（按住不放）算一筆。"""
        pass

    def on_delete_key(self) -> None:
        pass

    def on_tip_selected(self, tip_id: int) -> None:
        """一個資料提示被選取（點到或剛釘上）：host 應取消線條的選取，讓 Delete 只刪「目前選取的那一種」（像 MATLAB 的選取互斥）。"""
        pass

    def on_annotation_selected(self, ann_id: int) -> None:
        """一個標註（文字／參考線）被點選：host 應取消線條的選取（同上，選取互斥）。預設跟 on_tip_selected 一樣。"""
        self.on_tip_selected(ann_id)

    def begin_inline_edit(self, bbox_px, text: str, on_commit: Callable[[Optional[str]], None]) -> bool:
        return False

    def status(self, msg: str) -> None:
        pass

    def on_nav_dims(self, dims: str) -> None:
        """縮放／平移的方向限制改了（"both"／"x"／"y"；放大／平移模式右鍵選單）：host 可以存進設定。"""
        pass

    def mode_menu_extra(self, menu, axes, event) -> None:
        """平移／放大模式的右鍵選單（MATLAB 的模式選單）彈出前：host 可以在最下面再加項目（MATLAB 的項目照留在上面）。
        axes＝滑鼠下的座標區（twin 一起，host 在前）。預設不加（plotkit 的圖片視窗、分析視窗照舊只有 MATLAB 的模式選單）。"""
        pass

    def export_options(self, ax) -> dict:
        """「只匯出這個 panel…」對話框的額外參數（plotkit.export.ExportDialog 的 kw：initialfile、initialdir、before、on_saved…）。"""
        return {}


def nav_dims_allow(dims: str, axis: str) -> str:
    """方向限制（both／x／y）和這次動作要動的軸（both／x／y）取交集；沒有交集回 ""（不動）。"""
    if dims not in ("x", "y"):
        return axis
    if axis in ("both", "xy", None):
        return dims
    return axis if axis == dims else ""


def _nearest_vertex(xv: np.ndarray, yv: np.ndarray, ax, px: float, py: float) -> int:
    """最近的有限值頂點（沒有就 -1）；實作在 draw.nearest_vertex。"""
    return nearest_vertex(xv, yv, ax, px, py)


class Interactor:
    def __init__(self, canvas, host: InteractorHost, *, toolbar=None, model: Optional[InteractorModel] = None,
                 wheel_axis: str = "both", drag_threshold: float = DRAG_THRESHOLD_PX, zoom_base: float = ZOOM_BASE,
                 allow_pan: bool = True, allow_wheel: bool = True, enable_keys: bool = True):
        self.canvas = canvas
        self.host = host
        self.toolbar = toolbar
        self.model = model if model is not None else InteractorModel()
        self.wheel_axis = wheel_axis
        self.wheel_enabled = bool(allow_wheel)
        self.wheel_filter: Optional[Callable[[Any], bool]] = None   # host 可以逐事件決定這個滾輪要不要縮放（例如畫布放不下時改成捲動）
        self._wheel_draw_t = -1e9                   # macOS 觸控板補償：上一次畫完圖的時間、最近的滾輪事件時間、
        self._wheel_times: deque = deque(maxlen=32)   # 每個縮放方向（both／x／y）各自目前這一串
        self._wheel_streams: Dict[str, dict] = {}
        self.allow_pan = bool(allow_pan)
        self.enable_keys = bool(enable_keys)
        self.key_map: Dict[str, str] = dict(DEFAULT_KEY_MAP)
        self.drag_threshold = float(drag_threshold)
        self.zoom_base = float(zoom_base)
        self.ruler_axes: Tuple[str, ...] = ("x", "y")   # 哪些軸的尺規區有效（拖尺規只沿該軸平移）
        self.tips_enabled = False
        self.hover_enabled = True                   # 游標移到線上：先出現資料點標記，停 200 ms 再出現暫時的提示框
        self.selected_tip: Optional[int] = None
        self.selected_ann: Optional[int] = None      # 點選的標註（文字／參考線）：Delete 刪它、Esc 取消（像 MATLAB plot edit 的選取）
        self.tip_artists: Dict[int, Tuple[Any, Any]] = {}
        self.ann_artists: Dict[int, Any] = {}
        self._htip: Optional[dict] = None           # 暫時的資料提示（hover）：{"uid","index","ann","mk"}；不進模型、不進 undo
        self._hover_timer = None
        self._hover_bg = None                       # 暫時提示用的背景（draw_event 時存；換頂點只 blit，不整張重畫）
        self._sd_memo: Optional[dict] = None        # 同一個 motion 內 host.series_data 只取一次（DSV 每次都新建整條陣列）
        self._press: Optional[dict] = None
        self._drag: Optional[dict] = None
        self._bg = None
        self._blit_artists: list = []
        self._drawn = False
        self._cids: list = []
        self._home_view: Dict[Any, dict] = {}       # 第一次互動前的視圖（和 MATLAB 一樣）；還原視圖回到這裡
        self._last_axes: list = []                  # 最後一次按下的 axes（方向鍵平移的對象）
        self._ruler_cache: Optional[list] = None    # 尺規區（每次重畫後重算）
        self._cursor_kind: Optional[str] = None
        self._cursor_saved = ""
        self._cursor_value = ""                     # 我們設上去的游標名稱：還原時只有畫布游標還是它才還原（host 可能已經換成自己的）
        self._zoom_cons_var = None                  # 放大模式選單的 Unconstrained／Horizontal／Vertical Zoom
        self.cursors = None                         # plotkit.cursors.DataCursors（量測游標）：線左右幾個像素內優先抓游標
        self.tip_fields: Tuple[str, ...] = DEFAULT_TIP_FIELDS   # 資料提示顯示哪些列（「提示內容…」）
        if toolbar is not None and hasattr(toolbar, "attach_interactor"):
            toolbar.attach_interactor(self)         # theme.MatlabNav：放大模式的點擊／拖框由它分類，縮放的數學在這裡
        self.connect()

    # --- 連線 ------------------------------------------------------------------
    def connect(self) -> None:
        if self._cids:
            return
        c = self.canvas.mpl_connect
        self._cids = [c("button_press_event", self.on_press), c("button_release_event", self.on_release),
                      c("motion_notify_event", self.on_motion), c("scroll_event", self.on_scroll),
                      c("key_press_event", self.on_key), c("draw_event", self._on_draw),
                      c("figure_leave_event", self._on_leave), c("close_event", self._on_canvas_close)]

    def _on_canvas_close(self, event=None) -> None:
        """畫布被關掉（關視窗）：停掉暫時資料提示的 200 ms 計時器。Tk 後端的 close_event 在 Tcl 刪畫布元件的當下送出（matplotlib 綁在
        視窗的 <Destroy>），那時 Python 還沒刪掉這個元件的 Tcl 指令，取消得到——不停的話，游標停在線上 200 ms 內按 ⌘W 關窗，時間到時
        找不到已刪掉的「…_on_timer」指令，會跳 Tk 的背景錯誤對話框。"""
        self._hover_timer_stop()

    def disconnect(self) -> None:
        self._hover_timer_stop()
        for cid in self._cids:
            try:
                self.canvas.mpl_disconnect(cid)
            except Exception:
                pass
        self._cids = []

    @property
    def dragging(self) -> bool:
        return self._drag is not None

    def blocked(self) -> bool:
        """matplotlib 工具列的縮放／平移模式開著，或畫布被鎖住時，什麼都不做。"""
        tb = self.toolbar
        if tb is not None and getattr(tb, "mode", ""):
            return True
        wl = getattr(self.canvas, "widgetlock", None)
        return bool(wl is not None and wl.locked())

    def _wheel_blocked(self) -> bool:
        """滾輪（與 ＋／− 鍵）縮放在工具列的放大／平移模式裡照樣有效（MATLAB：zoom 模式開著滾輪仍縮放，模式只是多了點擊／拖框），
        只有正在拖框／拖曳平移、或畫布被工具列以外的東西鎖住時才不動。"""
        tb = self.toolbar
        if tb is not None and (getattr(tb, "_zoom_info", None) is not None or getattr(tb, "_pan_info", None) is not None):
            return True
        wl = getattr(self.canvas, "widgetlock", None)
        if wl is not None and wl.locked():
            try:
                return not (tb is not None and wl.isowner(tb))
            except Exception:
                return True
        return False

    def _renderer(self):
        if not self._drawn:
            self.canvas.draw()
            self._drawn = True
        get = getattr(self.canvas, "get_renderer", None)
        return get() if get else getattr(self.canvas, "renderer", None)

    def _on_draw(self, event) -> None:
        self._drawn = True
        self._wheel_draw_t = _now()
        self._ruler_cache = None
        self._hover_bg = None
        c = self.canvas
        if getattr(event, "canvas", c) is not c or c.is_saving():
            return                                  # savefig（可能換成 PDF canvas）：不存背景，animated 的暫時提示 savefig 自己會畫
        if self.tips_enabled and self.hover_enabled and getattr(c, "supports_blit", False):
            try:
                self._hover_bg = c.copy_from_bbox(c.figure.bbox)    # 不含 animated 的 artist（暫時提示、host 的十字游標）
            except Exception:
                self._hover_bg = None
        if self.cursors is not None:                # 量測游標（animated）：先存它拖曳用的背景，再畫上去（暫時提示之前）
            try:
                self.cursors.on_draw()
            except Exception:
                pass
        h = self._htip
        if h is not None:                           # 暫時提示是 animated：整張重畫時自己補畫上去（TkAgg 畫完才 blit 到螢幕）
            for a in self._animated_artists():
                if a is h["mk"] or a is h["ann"]:
                    try:
                        a.axes.draw_artist(a)
                    except Exception:
                        pass

    def _toolbar_mode(self) -> str:
        return str(getattr(self.toolbar, "mode", "") or "")

    # --- 游標 ------------------------------------------------------------------
    def _set_cursor(self, kind: Optional[str]) -> None:
        """尺規上（懸停／拖曳）換游標（MATLAB：手＋↔／↕）、線上（可放資料提示）
        換 crosshair；None＝還原。同一種游標再呼叫一次時，畫布游標若已被換掉就補回來：工具列（theme.MatlabNav._update_cursor）
        或沒有 MatlabNav 的 matplotlib 工具列（閒置 >1 s 後重畫的 _wait_cursor_for_draw_cm）會把游標設回 toolbar._last_cursor。"""
        get = getattr(self.canvas, "get_tk_widget", None)
        w = get() if get else None
        if kind == self._cursor_kind:
            if kind is not None and w is not None:
                try:
                    if str(w.cget("cursor") or "") != self._cursor_value:
                        w.configure(cursor=self._cursor_value)
                except Exception:
                    pass
            return
        if w is not None:
            try:
                cur = str(w.cget("cursor") or "")
                if kind is None:
                    if cur == self._cursor_value:       # host 在這之間換了自己的游標（例如 DSV 標題區的手）就不要蓋掉
                        w.configure(cursor=self._cursor_saved)
                else:
                    if self._cursor_kind is None or cur != self._cursor_value:
                        self._cursor_saved = cur
                    aqua = str(w.tk.call("tk", "windowingsystem")) == "aqua"
                    self._cursor_value = CURSORS[kind][0 if aqua else 1]
                    w.configure(cursor=self._cursor_value)
            except Exception:
                pass
        self._cursor_kind = kind

    # --- 尺規 ------------------------------------------------------------------
    def _ruler_zones(self) -> list:
        if self._ruler_cache is None:
            try:
                self._ruler_cache = ruler_zones(self.canvas.figure, self._renderer())
            except Exception:
                self._ruler_cache = []
        return self._ruler_cache

    def ruler_hit(self, event) -> Optional[Hit]:
        """座標區外、刻度文字與軸線之間＝尺規（MATLAB rulerPanInteraction：拖曳只沿該軸平移）；host 自己的留白區
        （例如 DSV 的 panel 標題區）要避開這裡時也用它。"""
        if getattr(event, "x", None) is None or getattr(event, "y", None) is None:
            return None
        found = ruler_at(self._ruler_zones(), event.x, event.y)
        if found is None or found[1] not in self.ruler_axes:     # 宿主可以把某一軸的尺規讓出來（DSV 主視窗：y 尺規＝panel 握把）
            return None
        return Hit("ruler", found[0], None, found[1])

    # --- 原始視圖（MATLAB 還原視圖用的那個視圖）-------------------------------------
    def _ax_key(self, ax):
        try:
            k = self.host.axes_key_for(ax)
        except Exception:
            k = None
        return ("k", str(k)) if k is not None else ("id", id(ax))

    def _ensure_home(self) -> None:
        """第一次互動前記下每個 axes 的視圖（範圍與是否自動縮放）（和 MATLAB 一樣）：
        Restore View 回到這裡（自動縮放的軸重新依目前資料自動縮放）。
        host 換成新的視圖（新資料、全部顯示、x 範圍…）時呼叫 forget_home()，下一次互動重新記。"""
        for ax in self.canvas.figure.get_axes():
            key = self._ax_key(ax)
            if key not in self._home_view:
                self._home_view[key] = {"xlim": tuple(float(v) for v in ax.get_xlim()),
                                        "ylim": tuple(float(v) for v in ax.get_ylim()),
                                        "xauto": bool(ax.get_autoscalex_on()), "yauto": bool(ax.get_autoscaley_on())}

    def forget_home(self) -> None:
        self._home_view.clear()

    def has_home(self) -> bool:
        return bool(self._home_view)

    @staticmethod
    def _apply_home(ax, hv: dict) -> None:
        if hv["xauto"]:
            ax.set_autoscalex_on(True)
        else:
            ax.set_xlim(*hv["xlim"])
        if hv["yauto"]:
            ax.set_autoscaley_on(True)
        else:
            ax.set_ylim(*hv["ylim"])
        if hv["xauto"] or hv["yauto"]:
            relim(ax)                                   # 游標線（add_overlay）不算；matplotlib 3.10／3.11 一樣
            ax.autoscale_view(scalex=hv["xauto"], scaley=hv["yauto"])

    def _on_leave(self, event) -> None:
        if self._drag is not None:
            self.on_release(event)
        self._press = None
        self._hover_clear()

    # --- 判定 ------------------------------------------------------------------
    def _hit_floating(self, event) -> Optional[Hit]:
        """資料提示框與文字標註：它們可以畫在座標區外面（annotation_clip=False；釘在峰值的提示框常在上緣之外）。"""
        r = self._renderer()
        for tid, (ann, _mk) in self.tip_artists.items():
            if not ann.get_visible():                        # 資料點在視圖外、沒畫出來的提示不能被點到
                continue
            try:
                patch = ann.get_bbox_patch()
                bb = patch.get_window_extent(r) if patch is not None else ann.get_window_extent(r)
                if bb.contains(event.x, event.y):
                    return Hit("tip", ann.axes, ann, tid)
            except Exception:
                continue
        for aid, art in self.ann_artists.items():
            a = self.model.find_ann(aid)
            if a is None or a.kind != "text":
                continue
            try:
                ok, _ = art.contains(event)
            except Exception:
                ok = False
            if ok:
                return Hit("text", art.axes, art, aid)
        return None

    def legend_hit(self, event) -> Optional[Hit]:
        """游標在哪個圖例上：文字＝Hit("legend")、框內其他地方＝Hit("legend_box")；都不是回 None。
        圖例可能被拖到座標區外面（MATLAB 也可以），所以看整張圖每個 axes 的圖例，不只游標下的 axes。"""
        fig = self.canvas.figure
        r = self._renderer()
        for ax in fig.get_axes():
            leg = ax.get_legend()
            if leg is None or not leg.get_visible():
                continue
            try:
                bb = leg.get_window_extent(r)
            except Exception:
                continue
            if bb.contains(event.x, event.y):
                for i, t in enumerate(leg.get_texts()):
                    try:
                        inside = t.get_window_extent(r).contains(event.x, event.y)
                    except Exception:
                        inside = False
                    if inside:
                        uids = self.host.legend_entries(ax)
                        return Hit("legend", ax, t, uids[i] if i < len(uids) else None, legend_index=i)
                return Hit("legend_box", ax, leg)
        return None

    def hit_test(self, event) -> Hit:
        fig = self.canvas.figure
        axes = axes_at(fig, event)
        floating = self._hit_floating(event)
        if floating is not None:
            return floating
        leg_hit = self.legend_hit(event)
        if leg_hit is not None:
            return leg_hit
        if not axes:
            return self.ruler_hit(event) or Hit("outside")
        ci = self._cursor_hit(event)
        if ci is not None:                          # 量測游標：線左右幾個像素內優先（MATLAB Time Scope 的游標也是）
            return Hit("cursor", axes[0], None, ci)
        for aid, art in self.ann_artists.items():
            a = self.model.find_ann(aid)
            if a is None or a.kind == "text":
                continue
            try:
                ok, _ = art.contains(event)
            except Exception:
                ok = False
            if ok:
                return Hit("refline", art.axes, art, aid)
        lines, owner = [], {}
        for ax in axes:
            for uid, ln in self.host.lines_in(ax):
                lines.append(ln)
                owner[id(ln)] = uid
        ln = hit_test_lines(lines, event)
        if ln is not None:
            uid = owner[id(ln)]
            return Hit("line", ln.axes, ln, uid, index=self._nearest(uid, event))
        return Hit("empty", axes[0])

    @staticmethod
    def _cursor_kind_of(handle) -> str:
        """游標把手 → 懸停／拖曳時的滑鼠游標（垂直 ↔、水平 ↕）。"""
        return "cursor_y" if isinstance(handle, tuple) else "cursor_x"

    def _nav_owns_cursor_grab(self) -> bool:
        """工具列的放大／平移模式（theme.MatlabNav，attach 了本 Interactor）開著而且沒在拖：游標線旁邊照樣抓游標
        （MatlabNav.press_zoom／press_pan 看到游標就不開始放大／平移）。一般的 matplotlib 工具列不讓（它的按下照樣會平移）。"""
        tb = self.toolbar
        if tb is None or getattr(tb, "interactor", None) is not self or self._toolbar_mode() not in ("pan/zoom", "zoom rect"):
            return False
        return getattr(tb, "_zoom_info", None) is None and getattr(tb, "_pan_info", None) is None

    def cursor_grab(self, event) -> bool:
        """MatlabNav 在放大／平移模式按下時問：這一下是不是落在量測游標上（左鍵、不是右鍵選單）→ 是就交給游標拖曳／選取。"""
        if self.cursors is None or getattr(event, "button", None) != 1 or is_context_click(event):
            return False
        return self._cursor_hit(event) is not None

    def _cursor_hit(self, event):
        c = self.cursors
        if c is None or getattr(event, "x", None) is None:
            return None
        try:
            return c.hit(event)
        except Exception:
            return None

    def _series(self, uid: int):
        m = self._sd_memo
        if m is not None and uid in m:
            return m[uid]
        d = self.host.series_data(uid)
        if m is not None:
            m[uid] = d
        return d

    def _nearest(self, uid: int, event) -> Optional[int]:
        data = self._series(uid)
        if not data:
            return None
        xv, yv, _label, ax = data
        xv = np.asarray(xv, float)
        m = getattr(self, "_xsorted_memo", None)               # x 是否已排序：同一個陣列只檢查一次（百萬點 np.diff 每個 motion 要幾 ms）
        if m is None or m[0] is not xv:
            n = len(xv)
            m = self._xsorted_memo = (xv, bool(n > 8 and np.all(np.diff(xv) >= 0)))
        return nearest_vertex(xv, np.asarray(yv, float), ax, event.x, event.y, x_sorted=m[1])

    # --- 滑鼠 ------------------------------------------------------------------
    def on_press(self, event) -> None:
        if self._drag is not None:
            return
        self._hover_clear()                         # 按下就收掉暫時的資料提示（點一下才釘住）
        if self.blocked():
            self._on_press_blocked(event)
            return
        hit = self.hit_test(event)
        if event.inaxes is None and hit.kind not in ("tip", "text", "ruler", "legend", "legend_box"):    # 座標區外只處理提示框／文字標註／尺規／圖例
            return
        if event.inaxes is not None:
            self._last_axes = axes_at(self.canvas.figure, event)
        if is_context_click(event):
            self._press = None
            if hit.kind in ("text", "refline") and hit.id in self.ann_artists:   # 右鍵也先選取它（MATLAB plot edit 一樣）
                self.select_annotation(hit.id)
            if hit.kind != "ruler":                 # MATLAB pan：點在尺規上不出選單
                self.host.on_context(hit, event)
            return
        if getattr(event, "dblclick", False) and event.button == 1:
            self._press = None
            if hit.kind != "ruler":
                self._on_double(hit, event)
            return
        self._press = {"x": event.x, "y": event.y, "hit": hit, "button": event.button,
                       "axes": axes_at(self.canvas.figure, event), "t": time.time(),
                       "shift": has_mod(event, "shift")}

    def _on_press_blocked(self, event) -> None:
        """工具列的平移／框選放大模式開著：跟 MATLAB 的 pan／zoom 模式一樣，雙擊＝還原視圖、右鍵＝選單
        （MATLAB pan／zoom 的 SelectionType 'open'／'alt'）；拖曳本身交給 matplotlib，先記下原始視圖。"""
        mode = self._toolbar_mode()
        if mode not in ("pan/zoom", "zoom rect") or event.inaxes is None:
            return
        if self._nav_owns_cursor_grab() and self.cursor_grab(event):
            # 放大／平移模式裡游標線旁邊（4 px）照樣優先：拖游標、點一下選取；不放大、不平移，雙擊也不還原視圖
            if not getattr(event, "dblclick", False):
                self._last_axes = axes_at(self.canvas.figure, event)
                self._press = {"x": event.x, "y": event.y, "hit": Hit("cursor", event.inaxes, None, self._cursor_hit(event)),
                               "button": event.button, "axes": self._last_axes, "t": time.time(), "shift": has_mod(event, "shift")}
            return
        if mode == "zoom rect" and getattr(self.toolbar, "interactor", None) is self:
            return          # theme.MatlabNav 自己處理放大模式的右鍵（模式選單）、雙擊（還原）與點擊／拖框（zoom_step／zoom_box 會記原始視圖）
        if is_context_click(event):
            hit = self.hit_test(event)
            if mode == "pan/zoom" and getattr(self.toolbar, "interactor", None) is self and hit.kind != "line":
                self.pan_mode_context(event)    # MATLAB 平移模式的右鍵＝模式選單（還原視圖＋方向限制）
            else:
                self.host.on_context(hit, event)   # 線上右鍵：訊號自己的選單（平移是預設模式，刪除這條訊號、顏色…都要拿得到）
        elif getattr(event, "dblclick", False) and event.button == 1:
            self.restore_view()
        elif event.button == 1:
            self._ensure_home()

    def _on_double(self, hit: Hit, event) -> None:
        if hit.kind == "legend" and hit.legend_index is not None:
            self._inline_rename(hit)
        elif hit.kind == "text":
            self._inline_edit_text(hit)
        elif hit.kind == "empty":
            self.restore_view()
        elif hit.kind in ("legend_box", "cursor"):   # 圖例框非文字處雙擊：MATLAB 預設 ItemHitFcn 只處理 label 區，不動作；游標上雙擊也不還原視圖
            return
        elif hit.kind == "line" and self.tips_enabled:
            return
        else:
            self.host.on_double_click(hit, event)

    def on_motion(self, event) -> None:
        if self._drag is not None:
            self._drag_update(event)
            return
        p = self._press
        if not p:
            self._hover(event)
            return
        dist = math.hypot(event.x - p["x"], event.y - p["y"])
        thr = 0.0 if p["hit"].kind == "cursor" else self.drag_threshold     # 游標一按住就跟著滑鼠走（不用拖滿 10 px）
        if dist < thr * float(getattr(self.canvas, "device_pixel_ratio", 1) or 1) or dist == 0:
            return
        self._drag_start(event)
        if self._drag is not None:
            self._drag_update(event)

    def _hover(self, event) -> None:
        """沒按鍵時：游標在尺規上就換成該軸的平移游標（MATLAB 在尺規上顯示左右／上下平移的游標）；
        在線上就換 crosshair 並顯示暫時的資料提示（_hover_tip；MATLAB 預設互動的 dataTipInteraction）。"""
        want = None
        if self.blocked() and getattr(event, "inaxes", None) is not None and self._nav_owns_cursor_grab():
            h = self._cursor_hit(event)             # 放大／平移模式：游標線上照樣換成 ↔／↕（可以拖）
            if h is not None:
                want = self._cursor_kind_of(h)
        elif not self.blocked() and getattr(event, "x", None) is not None:
            if getattr(event, "inaxes", None) is None:
                if self.allow_pan:
                    found = ruler_at(self._ruler_zones(), event.x, event.y)
                    if found is not None and found[1] in self.ruler_axes:
                        want = "ruler_x" if found[1] == "x" else "ruler_y"
            elif self._cursor_hit(event) is not None:
                want = self._cursor_kind_of(self._cursor_hit(event))    # 游標上：↔（垂直）／↕（水平）可以拖，不出暫時提示
            elif self._hover_tip(event):
                want = "crosshair"
        if want != "crosshair":
            self._hover_clear()
        self._set_cursor(want)

    def _drag_start(self, event) -> None:
        p = self._press
        hit = p["hit"]
        if hit.kind == "tip" and hit.id in self.tip_artists:
            tip = self.model.find_tip(hit.id)
            ann, _mk = self.tip_artists[hit.id]
            self.host.before_model_change("tip_move", tag="tip_drag")
            self._drag = {"kind": "tip", "tip": tip, "ann": ann, "x0": p["x"], "y0": p["y"], "off0": tuple(tip.offset)}
            self._blit_begin([ann])
        elif hit.kind == "text":
            ann = self.model.find_ann(hit.id)
            self.host.before_model_change("ann_move", tag="ann_drag")
            self._drag = {"kind": "text", "ann": ann, "art": hit.artist}
            self._blit_begin([hit.artist])
        elif hit.kind == "cursor":
            c = self.cursors
            if p["button"] != 1 or c is None or not c.begin_drag(hit.id, p["x"], p["y"]):
                self._press = None
                return
            self._drag = {"kind": "cursor", "i": hit.id}
            self._set_cursor(self._cursor_kind_of(hit.id))
        elif hit.kind == "ruler" and p["button"] == 1 and self.allow_pan:        # 拖曳尺規：只沿該軸平移（rulerPanInteraction）
            if not nav_dims_allow(self.nav_dims(), hit.id):      # 方向限制把這個軸鎖住了（MATLAB 各互動都 AND LimitsDimensions）
                self._press = None
                return
            self._ensure_nav_home()
            self._drag = {"kind": "pan", "axes": [hit.ax], "constrain": hit.id, "x0": p["x"], "y0": p["y"],
                          "lims": {id(hit.ax): (hit.ax.get_xlim(), hit.ax.get_ylim())}}
            self._set_cursor("ruler_x" if hit.id == "x" else "ruler_y")
        elif hit.kind in ("legend", "legend_box") and p["button"] == 1:
            leg = hit.ax.get_legend() if hit.ax is not None else None      # 拖圖例＝移動圖例（MATLAB 預設的圖例拖曳），不是平移
            if leg is None:
                self._press = None
                return
            bb = leg.get_window_extent(self._renderer())
            axbb = hit.ax.bbox
            leg.set_in_layout(False)        # 拖到座標區外時不要讓 constrained layout 把 axes 縮小（位置會跟著跑）
            self._drag = {"kind": "legend", "leg": leg, "ax": hit.ax, "x0": p["x"], "y0": p["y"],
                          "bb0": (float(bb.x0), float(bb.y0)), "loc0": getattr(leg, "_loc", None),
                          "axbb0": (float(axbb.x0), float(axbb.y0), float(axbb.width), float(axbb.height))}
        elif hit.kind in ("empty", "line", "refline") and p["button"] in (1, 2) and self.allow_pan:
            axes = p["axes"] or axes_at(self.canvas.figure, event)
            self._ensure_nav_home()
            dims = self.nav_dims()
            self._drag = {"kind": "pan", "axes": axes, "constrain": dims if dims in ("x", "y") else None, "x0": p["x"], "y0": p["y"],
                          "lims": {id(ax): (ax.get_xlim(), ax.get_ylim()) for ax in axes}}
        else:
            self._press = None

    def _drag_update(self, event) -> None:
        d = self._drag
        if d["kind"] == "tip":
            dpi = float(self.canvas.figure.dpi)
            off = (d["off0"][0] + (event.x - d["x0"]) * 72.0 / dpi, d["off0"][1] + (event.y - d["y0"]) * 72.0 / dpi)
            d["tip"].offset = off
            d["ann"].xyann = off
            self._blit_draw()
        elif d["kind"] == "text":
            x, y = data_coords(d["art"].axes, event)
            d["art"].set_position((x, y))
            self._blit_draw()
        elif d["kind"] == "legend":
            d["leg"].set_loc(self._legend_loc_at(d, event.x, event.y))
            self.canvas.draw_idle()
        elif d["kind"] == "cursor":
            if self.cursors is not None and event.x is not None:
                self.cursors.drag(event.x, event.y)
        else:
            con = d.get("constrain")
            for ax in d["axes"]:
                xl0, yl0 = d["lims"][id(ax)]
                bb = ax.bbox
                if con != "y":
                    nx = scaled_pan(ax.xaxis, xl0, event.x - d["x0"], bb.width)
                    if drawable_limits(nx):
                        ax.set_xlim(*nx)
                if con != "x":
                    ny = scaled_pan(ax.yaxis, yl0, event.y - d["y0"], bb.height)
                    if drawable_limits(ny):
                        ax.set_ylim(*ny)
            self.canvas.draw_idle()

    def on_release(self, event) -> None:
        if self._drag is not None:
            d, self._drag, self._press = self._drag, None, None
            if d["kind"] == "tip":
                self._blit_end()
                self.host.on_model_change("tip_move")
            elif d["kind"] == "text":
                x, y = d["art"].get_position()
                d["ann"].x, d["ann"].y = float(x), float(y)
                self.select_annotation(d["ann"].id, draw=False)     # 拖完仍是選取狀態
                self._blit_end()
                self.host.on_model_change("ann_move")
            elif d["kind"] == "cursor":
                if self.cursors is not None:
                    self.cursors.end_drag()
                    self.select_cursor(d["i"], announce=False)   # 拖過的游標＝選取（之後方向鍵微調它）；狀態列留給放開時的讀數
                self._hover(event)
            elif d["kind"] == "legend":
                loc = self._legend_loc_at(d, event.x, event.y)
                d["leg"].set_loc(loc)
                self.canvas.draw_idle()
                self.host.on_legend_move(d["ax"], loc)
            else:
                self._hover(event)                  # 放開時還在尺規上就維持尺規游標，否則還原
                for ax in d["axes"]:
                    self.host.on_view_change(ax)
                self._push_toolbar()
                self.canvas.draw_idle()
            return
        p, self._press = self._press, None
        if not p or p["button"] != 1:
            return
        hit = p["hit"]
        if hit.kind == "cursor":
            self.select_cursor(hit.id)                  # 點一下游標＝選取：←→（垂直）／↑↓（水平）微調，Esc 取消
        elif hit.kind == "tip":
            self.select_tip(hit.id)
        elif hit.kind in ("text", "refline") and hit.id in self.ann_artists:
            self.select_annotation(hit.id)               # 點標註＝選取（MATLAB plot edit 模式點物件一樣），Delete 就刪它
        elif hit.kind == "line":
            if self.tips_enabled and not p.get("shift"):    # 跟 MATLAB 一樣點線＝釘資料提示；Shift＋點＝選取
                idx = hit.index or 0
                dup = next((t for t in self.model.tips if t.uid == hit.id and t.index == idx), None)
                if dup is not None and dup.id in self.tip_artists:   # 同一個樣本已經有提示：選取它，不要疊一個一樣的
                    self.select_tip(dup.id)
                else:
                    self.add_tip(hit.id, idx)
            else:
                self.select_annotation(None, draw=False)   # 選取互斥：選了線就取消標註的選取
                self.select_cursor(None)
                self.host.on_pick(hit.id, event, hit)
        elif hit.kind == "empty":
            self.select_cursor(None)
            if self.selected_tip is not None:
                self.selected_tip = None
                self._highlight_tip()
            if self.selected_ann is not None:
                self.select_annotation(None)
            self.host.on_click_empty(event)

    def _legend_loc_at(self, d: dict, x: float, y: float) -> Tuple[float, float]:
        """拖曳中的圖例左下角（axes 座標，0..1 在座標區內）：原本的框加上滑鼠位移；用拖曳開始時的 axes 框算，中途重畫也不會飄。"""
        ax0, ay0, aw, ah = d["axbb0"]
        lx = d["bb0"][0] + (x - d["x0"])
        ly = d["bb0"][1] + (y - d["y0"])
        return (float((lx - ax0) / max(aw, 1.0)), float((ly - ay0) / max(ah, 1.0)))

    def _cancel_drag(self) -> None:
        d, self._drag, self._press = self._drag, None, None
        self._set_cursor(None)
        if d and d["kind"] == "cursor":
            if self.cursors is not None:
                self.cursors.cancel_drag()
            return
        if d and d["kind"] == "legend":
            if d["loc0"] is not None:
                d["leg"].set_loc(d["loc0"])
            self.canvas.draw_idle()
            return
        if d and d["kind"] in ("tip", "text"):
            if d["kind"] == "tip":
                d["tip"].offset = d["off0"]
                d["ann"].xyann = d["off0"]
            else:
                d["art"].set_position((d["ann"].x, d["ann"].y))
            self._blit_end()
            self.host.on_model_cancel("tip_move" if d["kind"] == "tip" else "ann_move")

    # --- blit ------------------------------------------------------------------
    def _blit_begin(self, artists: list) -> None:
        for a in artists:
            a.set_animated(True)
        self.canvas.draw()
        try:
            self._bg = self.canvas.copy_from_bbox(self.canvas.figure.bbox)
        except Exception:
            self._bg = None
        self._blit_artists = list(artists)

    def _blit_draw(self) -> None:
        if self._bg is None:
            self.canvas.draw_idle()
            return
        self.canvas.restore_region(self._bg)
        for a in self._blit_artists:
            a.axes.draw_artist(a)
        self.canvas.blit(self.canvas.figure.bbox)

    def _blit_end(self) -> None:
        for a in self._blit_artists:
            a.set_animated(False)
        self._bg = None
        self._blit_artists = []
        self.canvas.draw_idle()

    # --- 滾輪與鍵盤 ---------------------------------------------------------------
    def on_scroll(self, event) -> None:
        self._hover_clear()                         # 滾輪就收掉暫時的資料提示（MATLAB：hover 以外的手勢都會收掉它）
        if self._wheel_blocked() or not self.wheel_enabled or event.inaxes is None:
            return
        if has_mod(event, "alt"):                   # Alt／Option+滾輪留給 host（例如捲動畫布）
            return
        if self.wheel_filter is not None and not self.wheel_filter(event):
            return
        axis = self.wheel_axis
        ctrl = has_mod(event, "ctrl") or has_mod(event, "control") or has_mod(event, "cmd") or has_mod(event, "super")
        if has_mod(event, "shift"):
            axis = "y" if ctrl else "x"             # Shift 只縮 x；Ctrl／⌘＋Shift 只縮 y；Ctrl／⌘ 單獨＝明確要求縮放（兩軸）
        axis = nav_dims_allow(self.nav_dims(), axis)   # 方向限制（MATLAB 的 LimitsDimensions 也作用於滾輪）
        if not axis:
            return
        if sys.platform == "darwin" and getattr(event, "guiEvent", None) is not None:
            n = self._mac_wheel_notches(event, axis)     # 真的 Tk 事件：滑鼠一格＝1，觸控板一串依時間計量（可為小數）
        else:
            n = wheel_notches(event)                # Windows 精準觸控板的小數格直接按比例縮放
        n = max(-1.0, min(1.0, n))                  # 每個滾輪事件最多 1.1 倍，滾動量再大也一樣
        if abs(n) < 1e-3:
            return
        axes = axes_at(self.canvas.figure, event)
        if not axes:
            return
        self._ensure_nav_home()
        self.zoom(axes, event.x, event.y, self.zoom_base ** (-n), axis)
        self._after_view_change(axes)

    def _mac_wheel_notches(self, event, key: str = "both") -> float:
        """macOS Tk 8.6：這個滾輪事件算幾格（可為小數）。一串的第一個事件照 delta 算（滑鼠一格＝1 格）；
        同一串後面的事件依「距上個事件的時間」計量，密集的串（觸控板、慣性）再依時間衰減並有軟上限。
        key＝縮放方向：斜著滑時 Tk 會交錯送 deltaY 與（加 Shift 的）deltaX 事件，正負號可能相反，要分開算。"""
        n = max(-1.0, min(1.0, wheel_notches(event)))   # 一個事件最多算一格（每個事件最多 1.1 倍）
        if n == 0:
            return 0.0
        now = _now()
        self._wheel_times.append(now)
        sign = 1 if n > 0 else -1
        ws = self._wheel_streams.get(key)
        dt = now - ws["last"] if ws is not None else float("inf")
        just_drawn = now - self._wheel_draw_t <= MAC_WHEEL_GAP_AFTER_DRAW and dt <= MAC_WHEEL_GAP_BUSY
        if ws is None or ws["sign"] != sign or (dt > MAC_WHEEL_GAP and not just_drawn):
            self._wheel_streams[key] = {"sign": sign, "t0": now, "last": now, "extra": 0.0, "dense": False, "budget": 0.0}
            return float(n)
        ws["last"] = now
        ws["budget"] = min(ws.get("budget", 0.0) + dt, MAC_WHEEL_BUDGET_MAX)   # 經過的時間先存進額度，每個事件最多領一格
        w = min(1.0, ws["budget"] / MAC_WHEEL_STEP_DT)
        ws["budget"] -= w * MAC_WHEEL_STEP_DT
        recent = sum(1 for t in self._wheel_times if now - t <= MAC_WHEEL_DENSE_WIN)
        dense = recent >= MAC_WHEEL_DENSE_N or (ws["dense"] and just_drawn)
        ws["dense"] = dense
        if dense:
            w *= math.exp(-max(0.0, now - ws["t0"] - MAC_WHEEL_GRACE) / MAC_WHEEL_TAU) * math.exp(-ws["extra"] / MAC_WHEEL_CAP)
            ws["extra"] += abs(n) * w
        return n * w

    def _ensure_nav_home(self) -> None:
        """工具列的 Home／上一個視圖靠 matplotlib 的 nav stack；第一次改視圖前先把目前視圖推進去（matplotlib 自己的
        平移／框選也是這樣），否則 Home 只回到「第一次縮放之後」的視圖。同時記下 MATLAB 的「原始視圖」（_ensure_home）：
        所有改視圖的互動（滾輪、拖曳、尺規、方向鍵、放大模式的點擊／拖框、＋／−）都經過這裡。"""
        self._ensure_home()
        tb = self.toolbar
        stack = getattr(tb, "_nav_stack", None)
        if tb is None or stack is None or not hasattr(tb, "push_current"):
            return
        try:
            if stack() is None:
                tb.push_current()
        except Exception:
            pass

    def zoom(self, axes: list, px: float, py: float, scale: float, axis: str = "both") -> None:
        """以像素點 (px, py) 為中心縮放；scale < 1 放大。x 只在第一個 axes 設（sharex／twin 會跟著）。
        縮小夾在外界之內（和 MATLAB 一樣縮小到原始的自動範圍為止；目前範圍已經超出外界就不夾）。"""
        for k, ax in enumerate(axes):
            nx = ny = None
            if k == 0 and axis in ("both", "x", "xy"):
                cx = ax.transData.inverted().transform((px, py))[0]
                nx = scaled_zoom(ax.xaxis, ax.get_xlim(), cx, scale)
            if axis in ("both", "y", "xy"):
                cy = ax.transData.inverted().transform((px, py))[1]
                ny = scaled_zoom(ax.yaxis, ax.get_ylim(), cy, scale)
            nx, ny = self._bounded(ax, nx, ny)
            if nx is not None:
                ax.set_xlim(*nx)
            if ny is not None:
                ax.set_ylim(*ny)

    def outer_limits(self, ax) -> Tuple[Optional[Tuple[float, float]], Optional[Tuple[float, float]]]:
        """縮放的外界：host 指定的優先，沒有就用 matplotlib 的自動範圍（MATLAB OuterXLimits／OuterYLimits 預設＝自動範圍）。"""
        ox = oy = None
        try:
            r = self.host.outer_limits(ax)
            if r:
                ox, oy = r
        except Exception:
            ox = oy = None
        if ox is None:
            ox = auto_limits(ax, "x")
        if oy is None:
            oy = auto_limits(ax, "y")
        return ox, oy

    def _bounded(self, ax, nx, ny):
        """照 MATLAB 縮放的界限：x、y 目前都在外界之內才夾（任一超出就整個不夾，例如平移出去之後）。"""
        ox, oy = self.outer_limits(ax)
        if (ox is not None and not within_limits(ax.get_xlim(), ox)) or (oy is not None and not within_limits(ax.get_ylim(), oy)):
            return nx, ny
        if nx is not None and ox is not None:
            nx = bound_limits(nx, ox)
        if ny is not None and oy is not None:
            ny = bound_limits(ny, oy)
        return nx, ny

    def _after_view_change(self, axes: list) -> None:
        for ax in axes:
            self.host.on_view_change(ax)
        self._push_toolbar()
        self.canvas.draw_idle()

    def set_xlim(self, ax, lo: float, hi: float, draw: bool = True) -> None:
        """程式改 x 範圍（例如 DSV 的「上一個／下一個轉態」）：和滾輪、拖曳一樣先記原始視圖與 nav stack，
        改完推進「上一個／下一個視圖」、通知 host.on_view_change；draw=False 時由呼叫端自己畫。"""
        self._ensure_nav_home()
        ax.set_xlim(float(lo), float(hi))
        self.host.on_view_change(ax)
        self._push_toolbar()
        if draw:
            self.canvas.draw_idle()

    def zoom_step(self, axes: list, px: float, py: float, factor: float, axis: str = "both") -> None:
        """放大模式的單擊／鍵盤：以像素點 (px, py) 為中心縮放 factor 倍（>1 放大；和 MATLAB 一樣）。"""
        if not axes or not factor or factor <= 0:
            return
        self._ensure_nav_home()
        self.zoom(axes, px, py, 1.0 / float(factor), axis)
        self._after_view_change(axes)

    def zoom_box(self, axes: list, p0, p1, dims: str = "xy") -> None:
        """放大模式拖框：x／y 各自縮到框的範圍（dims 沒有的方向不動；和 MATLAB 的放大模式一樣）。"""
        if not axes or not dims:
            return
        self._ensure_nav_home()
        for k, ax in enumerate(axes):
            inv = ax.transData.inverted()
            x0, y0 = inv.transform(p0)
            x1, y1 = inv.transform(p1)
            nx = ny = None
            if k == 0 and "x" in dims and x0 != x1:
                nx = (min(x0, x1), max(x0, x1))
                if ax.get_xlim()[0] > ax.get_xlim()[1]:
                    nx = (nx[1], nx[0])
            if "y" in dims and y0 != y1:
                ny = (min(y0, y1), max(y0, y1))
                if ax.get_ylim()[0] > ax.get_ylim()[1]:
                    ny = (ny[1], ny[0])
            nx, ny = self._bounded(ax, nx, ny)
            if nx is not None:
                ax.set_xlim(*nx)
            if ny is not None:
                ax.set_ylim(*ny)
        self._after_view_change(axes)

    def zoom_constraint(self) -> str:
        """放大模式選單的方向限制（None／"x"／"y"）→ zoom() 的 axis 參數。"""
        c = getattr(self.toolbar, "zoom_constraint", None)
        return c if c in ("x", "y") else "both"

    def nav_dims(self) -> str:
        """縮放／平移的方向限制（"both"／"x"／"y"）。MATLAB 的模式選單 Horizontal／Vertical Zoom（Pan）設的是
        ax.InteractionOptions.LimitsDimensions：放大模式的點／框、滾輪、＋／−／↑↓ 鍵、拖曳平移、平移模式都受限，離開模式後仍保留。"""
        return self.zoom_constraint()

    def set_nav_dims(self, dims: Optional[str], notify: bool = True) -> str:
        """設定方向限制（"both"／None＝不限制、"x"＝只水平、"y"＝只垂直），回傳實際的值。"""
        d = dims if dims in ("x", "y") else "both"
        tb = self.toolbar
        if tb is not None:
            try:
                tb.zoom_constraint = d if d in ("x", "y") else None
            except Exception:
                pass
        if notify:
            self.host.status({"x": tr("縮放／平移方向：只水平（x）——滾輪、拖曳、放大模式與方向鍵都只動 x"),
                              "y": tr("縮放／平移方向：只垂直（y）——滾輪、拖曳、放大模式與方向鍵都只動 y")}.get(
                                  d, tr("縮放／平移方向：不限制")))
            try:
                self.host.on_nav_dims(d)
            except Exception:
                pass
        return d

    def zoom_out(self, axes: Optional[list] = None, factor: float = STEP_ZOOM) -> None:
        """工具列「縮小」（MATLAB axes toolbar 的 Zoom out／模式選單的 Zoom Out：以中心縮成 2/3）：
        每個座標區以自己的中心縮小 factor 倍；sharex／twin 的 x 只縮一次；受方向限制與外界（縮小到原始範圍為止）限制。"""
        fig = self.canvas.figure
        if axes is None:
            axes = [ax for ax in fig.get_axes() if ax.get_visible() and ax.get_navigate()]
        if not axes or not factor or factor <= 0:
            return
        dims = self.nav_dims()
        self._ensure_nav_home()
        done_x: list = []
        for ax in axes:
            shared = any(x_linked(ax, b) for b in done_x)
            axis = nav_dims_allow(dims, "y" if shared else "both")
            if axis:
                self.zoom([ax], *axes_center_px(ax), float(factor), axis)
            done_x.append(ax)
        self._after_view_change(axes)

    def zoom_mode_context(self, event) -> None:
        """放大模式裡右鍵：MATLAB 的模式選單——Zoom Out（Shift-Click）、Restore View、Unconstrained／Horizontal／Vertical Zoom
        （R2025a zoom(fig,'on') 後右鍵選單的項目）。縮小以座標區中心為準（和 MATLAB zoom 一樣）。"""
        import tkinter as tk
        tb = self.toolbar
        axes = axes_at(self.canvas.figure, event)
        if not axes:                                # 座標區外（panel 之間、留白）：MATLAB 的模式選單掛在 axes 上，這裡不彈
            return
        w = self.canvas.get_tk_widget()
        g = getattr(event, "guiEvent", None)
        x, y = (g.x_root, g.y_root) if (g is not None and hasattr(g, "x_root")) else w.winfo_pointerxy()
        if self._zoom_cons_var is None:
            self._zoom_cons_var = tk.StringVar(master=w)
        self._zoom_cons_var.set(getattr(tb, "zoom_constraint", None) or "none")

        def zoom_out():
            if axes:
                self.zoom_step(axes, *axes_center_px(axes[0]), 1.0 / STEP_ZOOM, self.zoom_constraint())

        def set_cons():
            self.set_nav_dims(self._zoom_cons_var.get())
        m = tk.Menu(w, tearoff=0)
        m.add_command(label=tr("縮小        Shift＋點"), command=zoom_out)
        m.add_command(label=tr("還原視圖"), command=self.restore_view)
        m.add_separator()                       # MATLAB 模式選單：Restore View 之後一條分隔線，再來三個方向
        for label, val in ((tr("不限方向縮放"), "none"), (tr("只縮 x（水平）"), "x"), (tr("只縮 y（垂直）"), "y")):
            m.add_checkbutton(label=label, variable=self._zoom_cons_var, onvalue=val, offvalue="none", command=set_cons)
        self._mode_menu_extra(m, axes, event)
        popup_menu(m, int(x), int(y))           # 0.9.13 W1：彈出後銷毀（Windows 的選單代號有限）

    def pan_mode_context(self, event) -> None:
        """平移模式裡右鍵：MATLAB 的模式選單——Restore View｜Unconstrained／Horizontal／Vertical Pan
        （R2025a pan(f,'on') 後的右鍵選單；設的是和放大模式同一個 LimitsDimensions）。"""
        import tkinter as tk
        w = self.canvas.get_tk_widget()
        g = getattr(event, "guiEvent", None)
        x, y = (g.x_root, g.y_root) if (g is not None and hasattr(g, "x_root")) else w.winfo_pointerxy()
        if self._zoom_cons_var is None:
            self._zoom_cons_var = tk.StringVar(master=w)
        self._zoom_cons_var.set(self.nav_dims() if self.nav_dims() in ("x", "y") else "none")
        m = tk.Menu(w, tearoff=0)
        m.add_command(label=tr("還原視圖"), command=self.restore_view)
        m.add_separator()
        for label, val in ((tr("不限方向平移"), "none"), (tr("只平移 x（水平）"), "x"), (tr("只平移 y（垂直）"), "y")):
            m.add_checkbutton(label=label, variable=self._zoom_cons_var, onvalue=val, offvalue="none",
                              command=lambda: self.set_nav_dims(self._zoom_cons_var.get()))
        self._mode_menu_extra(m, axes_at(self.canvas.figure, event), event)
        popup_menu(m, int(x), int(y))           # 0.9.13 W1：彈出後銷毀（Windows 的選單代號有限）

    def _mode_menu_extra(self, m, axes, event) -> None:
        """平移／放大模式選單的 MATLAB 項目之後，讓 host 在最下面加自己的項目（host.mode_menu_extra；DSV：「座標（P1）」與「整張圖的大標題…」，
        2026-10-27 使用者決定）。host 出錯不能讓 MATLAB 的模式選單出不來：寫到 stderr，選單照樣彈出。"""
        if not axes:
            return
        try:
            self.host.mode_menu_extra(m, list(axes), event)
        except Exception as e:                  # noqa: BLE001
            print(f"plotkit: mode_menu_extra 失敗: {e!r}", file=sys.stderr)

    def export_axes_dialog(self, ax):
        """panel 右鍵「只匯出這個 panel…」：只存這個座標區（含 twin 右軸、刻度、標籤、圖例）的匯出對話框。"""
        from .export import export_dialog
        kw = {}
        try:
            kw = dict(self.host.export_options(ax) or {})
        except Exception:
            kw = {}
        kw.setdefault("status", self.host.status)
        return export_dialog(self.canvas.get_tk_widget(), self.canvas.figure, axes=[ax], **kw)

    def _push_toolbar(self) -> None:
        tb = self.toolbar
        if tb is not None and hasattr(tb, "push_current"):
            try:
                tb.push_current()
            except Exception:
                pass

    def on_key(self, event) -> None:
        if not self.enable_keys:
            return
        k = (getattr(event, "key", None) or "").lower()
        if self._cursor_key(k):                 # 選取中的量測游標：自己方向的鍵優先（垂直 ←→、水平 ↑↓；Shift ×10）
            return
        name = self.key_map.get(k)
        if name is None:
            # 注音等非拉丁輸入法之下 - 鍵的 key 是 "ㄦ"（Tk 照目前的鍵盤配置翻字）：照實體按鍵認（plotkit.keys；ABC 之下不會走到這裡）
            alt = _keys.mpl_key(getattr(event, "guiEvent", None))
            if alt is not None and alt.lower() != k:
                name = self.key_map.get(alt.lower())
        if self._toolbar_mode() == "zoom rect" and name in ("pan_up", "pan_down"):
            name = "zoom_in" if name == "pan_up" else "zoom_out"   # zoom 模式裡 ↑／↓ 是縮放不是平移（和 MATLAB 一樣）
        if name is not None:
            self.run_key_action(name, event)

    def run_key_action(self, name: str, event=None) -> bool:
        """執行圖上的鍵盤動作（on_key 查完 key_map 後呼叫；host 的快速鍵系統沒焦點在畫布時也可以直接叫）。
        回傳有沒有做事。"""
        if name not in KEY_ACTIONS:
            return False
        mode = self._toolbar_mode()
        if name == "escape" and self._drag is not None and self._drag.get("kind") == "cursor":
            self._cancel_drag()                 # 放大／平移模式裡拖游標也能 Esc 取消
            return True
        # ＋／＝放大、−縮小各 1.1 倍，以座標區中心為準
        if name in ("zoom_in", "zoom_out"):
            if self._wheel_blocked():
                return True
            axes = (axes_at(self.canvas.figure, event) if event is not None else None) or self.canvas.figure.get_axes()[:1]
            if axes:
                self.host.before_view_change("view_key")      # MATLAB：鍵盤縮放進 undo（放開按鍵才記一筆）
                self.zoom_step(axes, *axes_center_px(axes[0]), KEY_ZOOM if name == "zoom_in" else 1 / KEY_ZOOM, self.nav_dims())
            return True
        if name == "escape" and mode == "zoom rect" and getattr(self.toolbar, "_zoom_info", None) is not None:
            self._cancel_toolbar_zoom()         # MATLAB zoom 模式按 Esc：取消正在拖的框
            return True
        pan_dir = {"pan_left": "left", "pan_right": "right", "pan_up": "up", "pan_down": "down"}.get(name)
        if self.blocked():
            if pan_dir and mode == "pan/zoom" and not self._wheel_blocked():
                self.key_pan(pan_dir, event)    # MATLAB pan 模式方向鍵也平移
            elif name == "escape" and self.cursors is not None and self.cursors.selected is not None:
                self.select_cursor(None)
            return True
        if name == "restore_view":
            self.restore_view()
        elif pan_dir:
            if self.selected_tip is not None and self.model.find_tip(self.selected_tip) is not None:
                # 選取中的資料提示優先（R2025a -batch 實量：
                # 線條上 →／↑＝下一個頂點、←／↓＝上一個）；到頭了就不動，不改成平移
                self.step_tip(self.selected_tip, 1 if pan_dir in ("right", "up") else -1)
            else:
                self.key_pan(pan_dir, event)
        elif name == "delete":
            if self.selected_tip is not None:
                self.remove_tip(self.selected_tip)
            elif self.selected_ann is not None:           # 選取的標註：Delete 刪掉（MATLAB plot edit：選物件按 Delete）
                self.remove_annotation(self.selected_ann)
            else:
                self.host.on_delete_key()
        elif name == "escape":
            if self._drag is not None:
                self._cancel_drag()
            elif self.selected_tip is not None:
                self.selected_tip = None
                self._highlight_tip()
            elif self.selected_ann is not None:
                self.select_annotation(None)
            elif self.cursors is not None and self.cursors.selected is not None:
                self.select_cursor(None)
        return True

    def _cursor_key(self, k: str) -> bool:
        """方向鍵微調選取中的量測游標（垂直：←→ 一個樣本〔Snap 開〕或 1 像素〔Snap 關〕；水平：↑↓ 1 像素；Shift ×10）。
        優先順序：拖曳中的東西 → 選取中游標「自己方向」的鍵（這裡）→ 放大模式 ↑↓ 縮放／平移模式平移 → 選取的資料提示 → 平移 5 px。
        游標和資料提示、標註的選取互斥，所以不會兩個都在選取中。處理了回 True。"""
        c = self.cursors
        if c is None or c.selected is None or self._drag is not None:
            return False
        shift = k.startswith("shift+")
        base = k[6:] if shift else k
        if base not in ("left", "right", "up", "down"):
            return False
        h = c.selected
        if not c.valid(h):
            c.selected = None
            return False
        horiz = isinstance(h, tuple)
        if horiz != (base in ("up", "down")):
            return False                        # 不是這條游標的方向：照原本的方向鍵行為
        tb = self.toolbar
        if tb is not None and (getattr(tb, "_zoom_info", None) is not None or getattr(tb, "_pan_info", None) is not None):
            return True                         # 工具列正在拖框／平移：先不動
        n = (1 if base in ("right", "up") else -1) * (10 if shift else 1)
        c.step(h, n)
        return True

    def select_cursor(self, handle, draw: bool = True, announce: bool = True) -> None:
        """選取量測游標（None＝取消）。和資料提示、標註的選取互斥（MATLAB 一次只有一個目前物件）。"""
        c = self.cursors
        if c is None:
            return
        if handle is not None:
            if self.selected_tip is not None:
                self.selected_tip = None
                self._highlight_tip(draw=False)
            if self.selected_ann is not None:
                self.select_annotation(None, draw=False)
        c.select(handle, draw=draw)
        if announce and handle is not None and c.selected is not None:
            self.host.status(tr("已選取游標 {n}：←／→ 微調（Snap 開＝一個樣本、關＝1 像素；Shift ×10）、Esc 取消選取").format(n=int(handle) + 1) if not isinstance(handle, tuple)
                             else tr("已選取水平游標 {n}：↑／↓ 微調 1 像素（Shift ×10）、Esc 取消選取").format(n=int(handle[2]) + 1))

    def key_pan(self, key: str, event=None) -> None:
        """方向鍵平移（每按一下 5 像素）：
        每按一下等於往該方向拖曳 5 像素。對象＝游標所在的 axes，否則最後按過的 axes，否則全部。"""
        fig = self.canvas.figure
        axes = axes_at(fig, event) if (event is not None and getattr(event, "inaxes", None) is not None) else []
        if not axes:
            axes = [ax for ax in self._last_axes if ax in fig.axes] or [ax for ax in fig.get_axes() if ax.get_visible()]
        if not axes:
            return
        step = KEY_PAN_PX * float(getattr(self.canvas, "device_pixel_ratio", 1) or 1)
        dx = {"left": -step, "right": step}.get(key, 0.0)
        dy = {"up": step, "down": -step}.get(key, 0.0)
        dims = self.nav_dims()
        if dims == "x":
            dy = 0.0
        elif dims == "y":
            dx = 0.0
        if not dx and not dy:
            return
        self.host.before_view_change("view_key")          # MATLAB：鍵盤平移也進 undo
        self._ensure_nav_home()
        targets = {id(ax): (scaled_pan(ax.xaxis, ax.get_xlim(), dx, ax.bbox.width),      # 先算完再設：sharex／twin 的 x 只移一次
                            scaled_pan(ax.yaxis, ax.get_ylim(), dy, ax.bbox.height)) for ax in axes}
        for ax in axes:
            if dx:
                ax.set_xlim(*targets[id(ax)][0])
            if dy:
                ax.set_ylim(*targets[id(ax)][1])
        self._after_view_change(axes)

    def _cancel_toolbar_zoom(self) -> None:
        """取消放大模式正在拖的框（MatlabNav.release_zoom 看到 _zoom_info 是 None 就不縮放）。"""
        end_toolbar_zoom(self.toolbar)          # 斷開拖曳的 callback、移除框（MatlabNav 的藍框一起移除）、_zoom_info=None；matplotlib 3.10／3.11 一樣
        self.canvas.draw_idle()

    def step_tip(self, tip_id: int, delta: int) -> bool:
        """把資料提示移到相鄰的樣本（MATLAB 資料提示選取時的 ←／→／↑／↓）。可復原（tip_move）。"""
        tip = self.model.find_tip(tip_id)
        data = self.host.series_data(tip.uid) if tip is not None else None
        if data is None:
            return False
        xv, yv = np.asarray(data[0], float), np.asarray(data[1], float)
        n, step = len(yv), (1 if delta > 0 else -1)
        new = int(tip.index) + int(delta)
        while 0 <= new < n and not (np.isfinite(xv[new]) and np.isfinite(yv[new])):
            new += step                         # NaN／inf 的點跳過（annotate 的箭頭指到非有限值會讓整張圖畫不出來）
        if not (0 <= new < n) or new == tip.index:
            return False                        # 到頭了：不動
        self.host.before_model_change("tip_move", tag="tip_key")
        tip.index = new
        self._remove_tip_artists(tip.id)
        self._draw_tip(tip)
        self._highlight_tip(draw=False)
        self.host.on_model_change("tip_move")
        msg = self.tip_delta_text(tip.id)
        if msg:
            self.host.status(msg)
        self.canvas.draw_idle()
        return True

    def restore_view(self, axes: Optional[list] = None) -> None:
        """還原視圖＝回到第一次互動前記下的視圖（和 MATLAB 一樣：手動範圍回到那個範圍、
        自動縮放的軸依目前資料重新自動縮放）；沒記過（還沒互動過）就交給 host.home_view／自動縮放。"""
        self._wheel_streams.clear()
        if self.host.on_restore_view():
            return
        for ax in (axes or self.canvas.figure.get_axes()):
            hv0 = self._home_view.get(self._ax_key(ax))
            if hv0 is not None:
                self._apply_home(ax, hv0)
            else:
                hv = self.host.home_view(ax)
                if hv:
                    ax.set_xlim(*hv[0])
                    ax.set_ylim(*hv[1])
                else:
                    ax.set_autoscale_on(True)       # set_xlim 會把自動縮放關掉，要先打開
                    relim(ax)
                    ax.autoscale_view()
            self.host.on_view_change(ax)
        self._push_toolbar()
        self.canvas.draw_idle()

    # --- 暫時的資料提示（游標移到線上）-------------------------------------------------
    def _hover_tip(self, event) -> bool:
        """像 MATLAB 的 dataTipInteraction：游標在線上（±2 px＋線寬一半，同點擊的判定）就在最近的頂點放標記，停 200 ms 再出現
        提示框（內容、外觀、放的角落都跟釘住的一樣）；不進模型、不進 undo。回傳游標是否在可以放提示的線上。
        資料提示關著、工具列模式開著、游標在提示框／文字／圖例／參考線上時不做（由 _hover 收掉）。"""
        if not (self.tips_enabled and self.hover_enabled):
            return False
        self._sd_memo = {}
        try:
            hit = self.hit_test(event)
            if hit.kind != "line" or hit.id is None or hit.index is None or hit.index < 0:
                return False
            self._hover_set(int(hit.id), int(hit.index))
        finally:
            self._sd_memo = None
        return self._htip is not None

    def _hover_set(self, uid: int, idx: int) -> None:
        h = self._htip
        if h is not None and h["uid"] == uid and h["index"] == idx:
            if self._foreign_animated():                         # host 的 blit（例如 DSV 十字游標）每個 motion 都會蓋掉標記：補畫
                self._hover_blit()
            return
        self._hover_clear(draw=False, cursor=False)             # 換到另一個頂點：框先收掉，200 ms 後再出現
        data = self._series(uid)
        if not data:
            return
        xv, yv, _label, ax = data
        if ax is None or not (0 <= idx < len(yv)):
            return
        x, y = float(xv[idx]), float(yv[idx])
        if not (np.isfinite(x) and np.isfinite(y)):
            return
        tmp = DataTip(uid=int(uid), index=int(idx), id=-1)
        ann, mk = draw_tip(ax, tmp, x, y, self._tip_text(uid, idx, x, y), self.host.style())
        place_tip(tmp, ann, self._renderer())                    # 先量框再藏：看不見的 Annotation 量出來是 Bbox.unit()
        ann.set_visible(False)                                   # 停 200 ms 後才顯示（linger）
        for a in (ann, mk):
            a.set_animated(True)                                 # 換頂點只 blit 標記（大檔全幅整張重畫要好幾百 ms）
        self._htip = {"uid": uid, "index": idx, "ann": ann, "mk": mk}
        self._hover_timer_start()
        self._hover_blit()

    def _hover_linger(self) -> None:
        h = self._htip
        self._hover_timer = None
        if h is None:
            return
        if self._press is not None or self._drag is not None or self.blocked():
            self._hover_clear()
            return
        h["ann"].set_visible(True)
        if self._cursor_kind == "crosshair":
            self._set_cursor("crosshair")        # 補回被 matplotlib 等待游標換掉的 crosshair
        self._hover_blit()

    def _hover_clear(self, draw: bool = True, cursor: bool = True) -> None:
        """收掉暫時的資料提示（移開、按下、滾輪、換模式、離開畫布、重畫）；cursor＝順便把 crosshair 游標還原。"""
        self._hover_timer_stop()
        h, self._htip = self._htip, None
        if cursor and self._cursor_kind == "crosshair":
            self._set_cursor(None)
        if h is None:
            return
        for a in (h["ann"], h["mk"]):
            remove_artist(a)
        if draw:
            self._hover_blit()

    def _foreign_animated(self) -> bool:
        """圖上有別人的 animated artist（host 的十字游標等）正在顯示。"""
        h = self._htip
        mine = (h["ann"], h["mk"]) if h is not None else ()
        return any(a not in mine for a in self._animated_artists())

    def _animated_artists(self) -> list:
        """圖上顯示中的 animated artist，照 zorder（同 zorder 照加入順序）＝ blit 與整張重畫時的畫法順序。"""
        out = []
        for ax in self.canvas.figure.get_axes():
            for a in ax.get_children():
                try:
                    if a.get_animated() and a.get_visible():
                        out.append(a)
                except Exception:
                    continue
        return sorted(out, key=lambda a: a.get_zorder())

    def _hover_blit(self) -> None:
        """只重畫暫時提示：貼回 draw_event 存的背景，再畫所有顯示中的 animated artist（暫時提示，以及 host 的十字游標，
        免得被我們的背景蓋掉）。沒有背景、或已經排了整張重畫（draw_idle 還沒跑）就交給整張重畫（_on_draw 會補畫暫時提示）。"""
        c = self.canvas
        if self._hover_bg is None or getattr(c, "_idle_draw_id", None):
            c.draw_idle()
            return
        try:
            c.restore_region(self._hover_bg)
            for a in self._animated_artists():
                a.axes.draw_artist(a)
            c.blit(c.figure.bbox)
        except Exception:
            c.draw_idle()

    @property
    def hover_tip(self) -> Optional[dict]:
        """目前的暫時資料提示（測試／host 用）：{"uid","index","ann","mk"} 或 None。"""
        return self._htip

    def _hover_timer_start(self) -> None:
        self._hover_timer_stop()
        try:
            t = self.canvas.new_timer(interval=HOVER_LINGER_MS)
            t.single_shot = True
            t.add_callback(self._hover_linger)
            t.start()
            self._hover_timer = t
        except Exception:
            self._hover_timer = None

    def _hover_timer_stop(self) -> None:
        t, self._hover_timer = self._hover_timer, None
        if t is not None:
            try:
                t.stop()
            except Exception:
                pass

    # --- 資料提示 ----------------------------------------------------------------
    def add_tip(self, uid: int, index: int, offset: Tuple[float, float] = TIP_OFFSET_DEFAULT) -> Optional[DataTip]:
        data = self.host.series_data(uid)
        if data is None or index is None or int(index) < 0:
            return None
        xv, yv = np.asarray(data[0], float), np.asarray(data[1], float)
        n = len(yv)
        if n == 0:
            return None
        i = min(max(0, int(index)), n - 1)
        if not (np.isfinite(xv[i]) and np.isfinite(yv[i])):     # NaN／inf 的點：annotate 的箭頭會讓整張圖畫不出來
            self.host.status(tr("這個點的值不是有限數值，不能釘資料提示"))
            return None
        self.host.before_model_change("tip_add")
        self._hover_clear(draw=False)
        tip = DataTip(uid=int(uid), index=i, id=self.model.next_tip_id(), offset=tuple(offset))
        self.model.tips.append(tip)
        if self._draw_tip(tip):
            place_tip(tip, self.tip_artists[tip.id][0], self._renderer())    # 框放哪一角（像 MATLAB LocationMode auto）
        self.select_annotation(None, draw=False)            # 選取互斥：釘了提示就取消標註的選取
        self.selected_tip = tip.id
        self.host.on_tip_selected(tip.id)
        self._highlight_tip(draw=False)
        self.host.on_model_change("tip_add")
        self.host.status(self.tip_delta_text(tip.id) or tr("資料提示 #{id}：拖曳可移動，Delete 或右鍵刪除").format(id=tip.id))
        self.canvas.draw_idle()
        return tip

    def remove_tip(self, tip_id: int) -> None:
        tip = self.model.find_tip(tip_id)
        if tip is None:
            return
        self.host.before_model_change("tip_remove")
        self._remove_tip_artists(tip_id)
        self.model.tips.remove(tip)
        if self.selected_tip == tip_id:
            self.selected_tip = None
        self.host.on_model_change("tip_remove")
        self.canvas.draw_idle()

    def clear_tips(self) -> None:
        if not self.model.tips:
            return
        self.host.before_model_change("tip_clear")
        for tid in list(self.tip_artists):
            self._remove_tip_artists(tid)
        self.model.tips.clear()
        self.selected_tip = None
        self.host.on_model_change("tip_clear")
        self.canvas.draw_idle()

    def _remove_tip_artists(self, tip_id: int) -> None:
        arts = self.tip_artists.pop(tip_id, None)
        if arts:
            for a in arts:
                remove_artist(a)

    def _draw_tip(self, tip: DataTip) -> bool:
        data = self.host.series_data(tip.uid)
        if not data:
            return False
        xv, yv, _label, ax = data
        n = len(yv)
        if n == 0 or ax is None:
            return False
        i = min(max(0, int(tip.index)), n - 1)
        tip.index = i
        x, y = float(xv[i]), float(yv[i])
        if not (np.isfinite(x) and np.isfinite(y)):          # 資料改了之後落在 NaN／inf：留在模型裡但不畫
            return False
        text = tip.text or self._tip_text(tip.uid, i, x, y)
        self.tip_artists[tip.id] = draw_tip(ax, tip, x, y, text, self.host.style())
        self._connect_limits(ax)
        self._sync_tip_view(tip)
        return True

    # --- 提示內容、匯出、提示間的 Δ ------------------------------------------------------
    def _tip_text(self, uid: int, index: int, x: float, y: float) -> str:
        """提示框文字：預設列（名稱／X／Y）照 host.tip_text（原本的 MATLAB 外觀）；勾了別的列就照 tip_record 組。"""
        fields = parse_tip_fields(self.tip_fields)
        if fields == DEFAULT_TIP_FIELDS:
            return self.host.tip_text(uid, index, x, y)
        return format_tip_fields(self.host.tip_record(uid, index, x, y), fields)

    def set_tip_fields(self, fields, notify: bool = True) -> Tuple[str, ...]:
        """「提示內容…」：設定資料提示顯示哪些列（TIP_FIELDS 的子集合），套用到現有與之後的提示（含暫時提示）。"""
        new = parse_tip_fields(fields)
        changed = new != tuple(self.tip_fields)
        self.tip_fields = new
        if changed:
            self.refresh_tips()
        if notify:
            self.host.on_tip_fields(new)
        return new

    def refresh_tips(self, draw: bool = True) -> None:
        """重畫全部資料提示的文字（位置、offset、選取不變）。"""
        self._hover_clear(draw=False)
        for tid in list(self.tip_artists):
            self._remove_tip_artists(tid)
        for tip in list(self.model.tips):
            if self._draw_tip(tip) and tip_offset_is_auto(tip.offset):
                place_tip(tip, self.tip_artists[tip.id][0], self._renderer_if_drawn())
        self._highlight_tip(draw=False)
        if draw:
            self.canvas.draw_idle()

    def tip_records(self) -> List[dict]:
        """全部資料提示的內容（照提示編號排序）：tip_record() 再加 id；畫不出來（訊號沒了、NaN）的略過。"""
        out = []
        for tip in sorted(self.model.tips, key=lambda t: t.id):
            data = self.host.series_data(tip.uid)
            if not data:
                continue
            xv, yv = data[0], data[1]
            n = len(yv)
            if n == 0:
                continue
            i = min(max(0, int(tip.index)), n - 1)
            rec = dict(self.host.tip_record(tip.uid, i, float(xv[i]), float(yv[i])))
            rec["id"] = tip.id
            out.append(rec)
        return out

    def tips_table(self) -> Tuple[List[str], List[List[str]]]:
        """匯出資料提示的表格（MATLAB Export Cursor Data）：#、訊號、panel、樣本索引（1 起算）、x、y。"""
        recs = self.tip_records()
        units = {r.get("xunit") for r in recs if r.get("xunit")}
        xh = "x" + (f" ({units.pop()})" if len(units) == 1 else "")
        header = ["#", tr("訊號名稱"), "Panel", tr("樣本索引"), xh, "y"]
        rows = [[str(r["id"]), str(r.get("name", "")), str(r.get("panel", "")), str(int(r["index"]) + 1),
                 f"{float(r['x']):.10g}", f"{float(r['y']):.10g}"] for r in recs]
        return header, rows

    def tips_text(self, sep: str = "\t") -> str:
        header, rows = self.tips_table()
        if sep == ",":
            def q(v: str) -> str:
                return '"' + v.replace('"', '""') + '"' if any(ch in v for ch in ',"\n') else v
            return "\n".join(",".join(q(v) for v in r) for r in [header] + rows) + "\n"
        return "\n".join(sep.join(r) for r in [header] + rows) + "\n"

    def export_tips(self, path: str) -> int:
        """把全部資料提示寫成文字檔：.csv 用逗號，其他（.txt／.tsv）用 Tab。回傳寫了幾個提示。"""
        sep = "," if str(path).lower().endswith(".csv") else "\t"
        _h, rows = self.tips_table()
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.tips_text(sep))
        self.host.status(tr("已匯出 {n} 個資料提示：{path}").format(n=len(rows), path=path))
        return len(rows)

    def _tk_widget(self):
        get = getattr(self.canvas, "get_tk_widget", None)
        return get() if get else None

    def copy_tips(self) -> Optional[str]:
        """全部資料提示以 TSV（含標題列）放進剪貼簿；回傳文字（沒有提示或沒有 Tk 時 None）。"""
        _h, rows = self.tips_table()
        if not rows:
            self.host.status(tr("沒有資料提示可匯出：先在線上點一下釘住提示"))
            return None
        text = self.tips_text("\t")
        w = self._tk_widget()
        if w is None:
            return None
        try:
            w.clipboard_clear()
            w.clipboard_append(text)
        except Exception as e:
            self.host.status(tr("複製失敗：{err}").format(err=e))
            return None
        self.host.status(tr("已複製 {n} 個資料提示（TSV）到剪貼簿").format(n=len(rows)))
        return text

    def export_tips_dialog(self) -> Optional[str]:
        """「匯出資料提示…」：選檔名（TXT＝Tab 分隔、CSV＝逗號）寫檔；回傳路徑（取消或沒有提示時 None）。"""
        _h, rows = self.tips_table()
        if not rows:
            self.host.status(tr("沒有資料提示可匯出：先在線上點一下釘住提示"))
            return None
        from . import dialogs
        path = dialogs.ask_save_path(self._tk_widget(), tr("匯出資料提示"), "datatips.txt",
                                     [(tr("文字檔（Tab 分隔）"), "*.txt"), ("CSV", "*.csv"), (tr("所有檔案"), "*")])
        if not path:
            return None
        try:
            self.export_tips(path)
        except OSError as e:
            self.host.status(tr("匯出失敗：{err}").format(err=e))
            return None
        return path

    def tip_fields_dialog(self):
        """「提示內容…」對話框（勾選名稱／X／Y／樣本索引／Panel）；按確定就 set_tip_fields。回傳對話框（測試用）。"""
        from . import dialogs
        return dialogs.TipFieldsDialog(self._tk_widget(), self.tip_fields, lambda f: self.set_tip_fields(f))

    def tip_delta(self, tip_id: Optional[int] = None) -> Optional[dict]:
        """兩個以上提示時的 Δ（示波器游標的習慣）：選取的提示和前一個（編號較小的最近一個；它是第一個就和下一個）；
        沒指定就用目前選取的、沒選取就用最新的兩個。回傳 {"a": 前, "b": 後, "dx", "dy"}（b − a，顯示單位）或 None。"""
        recs = self.tip_records()
        if len(recs) < 2:
            return None
        ids = [r["id"] for r in recs]
        tid = tip_id if tip_id is not None else self.selected_tip
        if tid not in ids:
            tid = ids[-1]
        k = ids.index(tid)
        a, b = (recs[k - 1], recs[k]) if k > 0 else (recs[k], recs[k + 1])
        return {"a": a, "b": b, "dx": float(b["x"]) - float(a["x"]), "dy": float(b["y"]) - float(a["y"])}

    def tip_delta_text(self, tip_id: Optional[int] = None) -> str:
        d = self.tip_delta(tip_id)
        if d is None:
            return ""
        unit = d["b"].get("xunit") or ""
        unit = f" {unit}" if unit and unit == (d["a"].get("xunit") or "") else ""
        txt = tr("資料提示 #{b} − #{a}：Δx = {dx}{unit}、Δy = {dy}").format(
            a=d["a"]["id"], b=d["b"]["id"], dx=fmt_matlab(d["dx"]), unit=unit, dy=fmt_matlab(d["dy"]))
        return txt

    # --- 視圖改變（像 MATLAB R2025a）：資料點在 XLim／YLim 外就不畫；LocationMode 'auto' 的提示重算放哪一角 ---------------
    def _connect_limits(self, ax) -> None:
        """在 axes 的 xlim_changed／ylim_changed 掛回呼（滾輪、拖曳平移、工具列縮放、Home、程式設限都會觸發）。"""
        cids = getattr(ax, "_pk_tip_lim_cids", None)
        if cids is None:
            cids = {}
            try:
                ax._pk_tip_lim_cids = cids
            except Exception:
                return
        if id(self) in cids:
            return
        try:
            cids[id(self)] = (ax.callbacks.connect("xlim_changed", self._on_limits_changed),
                              ax.callbacks.connect("ylim_changed", self._on_limits_changed))
        except Exception:
            pass

    def _on_limits_changed(self, ax) -> None:
        for tid, (ann, _mk) in list(self.tip_artists.items()):
            if ann.axes is ax:
                tip = self.model.find_tip(tid)
                if tip is not None:
                    self._sync_tip_view(tip)

    def _sync_tip_view(self, tip: DataTip) -> None:
        arts = self.tip_artists.get(tip.id)
        if not arts:
            return
        ann, mk = arts
        ax = ann.axes
        if ax is None:
            return
        inside = point_in_view(ax, float(ann.xy[0]), float(ann.xy[1]))
        ann.set_visible(inside)
        mk.set_visible(inside)
        if inside and tip_offset_is_auto(tip.offset):
            place_tip(tip, ann, self._renderer_if_drawn())     # 不在這裡強制畫圖（回呼可能在畫圖途中觸發）

    def _renderer_if_drawn(self):
        if not self._drawn:
            return None
        get = getattr(self.canvas, "get_renderer", None)
        return get() if get else getattr(self.canvas, "renderer", None)

    def select_tip(self, tip_id: Optional[int], draw: bool = True) -> None:
        """選取（或 None＝取消選取）一個資料提示並更新外觀；選取時通知 host 取消線條的選取（也取消標註的選取）。"""
        self.selected_tip = tip_id
        if tip_id is not None and self.selected_ann is not None:
            self.select_annotation(None, draw=False)
        if tip_id is not None and self.cursors is not None and self.cursors.selected is not None:
            self.cursors.select(None)
        self._highlight_tip(draw)
        if tip_id is not None:
            self.host.on_tip_selected(tip_id)
            msg = self.tip_delta_text(tip_id)
            if msg:
                self.host.status(msg)

    def select_annotation(self, ann_id: Optional[int], draw: bool = True) -> None:
        """選取一個標註（None＝取消選取）。跟 MATLAB plot edit 模式點選物件一樣：之後 Delete 就刪它、Esc 取消選取；
        選取時取消資料提示與線條的選取（選取互斥）。"""
        if ann_id is not None and self.model.find_ann(ann_id) is None:
            ann_id = None
        changed = ann_id != self.selected_ann
        self.selected_ann = ann_id
        if ann_id is not None and self.selected_tip is not None:
            self.selected_tip = None
            self._highlight_tip(draw=False)
        if ann_id is not None and self.cursors is not None and self.cursors.selected is not None:
            self.cursors.select(None)
        if changed:
            self._highlight_ann(draw=draw)
        if ann_id is not None:
            self.host.on_annotation_selected(ann_id)
            self.host.status(tr("已選取標註 #{id}：Delete 刪除、Esc 取消選取、右鍵更多").format(id=ann_id))

    def _highlight_ann(self, draw: bool = True) -> None:
        """被選取的標註加粗（文字：外框變粗／沒框的畫虛線框；參考線：線變粗），像 MATLAB 的選取把手。"""
        for aid, art in self.ann_artists.items():
            a = self.model.find_ann(aid)
            if a is None:
                continue
            sel = aid == self.selected_ann
            try:
                if a.kind == "text":
                    patch = art.get_bbox_patch()
                    if a.boxed and patch is not None:
                        patch.set_linewidth(1.8 if sel else 1.0)
                    elif sel:
                        art.set_bbox(dict(boxstyle="square,pad=0.2", fc="none", ec=art.get_color(), lw=0.8, ls="--"))
                    else:
                        art.set_bbox(None)
                else:
                    art.set_linewidth(max(float(a.lw) * 3.0, 1.5) if sel else float(a.lw))
            except Exception:
                pass
        if draw:
            self.canvas.draw_idle()

    def deselect_tip(self, draw: bool = True) -> None:
        if self.selected_tip is not None:
            self.select_tip(None, draw)

    def _highlight_tip(self, draw: bool = True) -> None:
        """目前選取的提示框線用藍色（MATLAB R2025a 實測：目前的資料提示框線 #268cdd，其他 #7d7d7d）。"""
        tp = self.host.style().get("tip", {})
        ec, ec_sel = tp.get("ec", "#7d7d7d"), tp.get("ec_selected", "#268cdd")
        for tid, (ann, _mk) in self.tip_artists.items():
            patch = ann.get_bbox_patch()
            if patch is not None:
                patch.set_edgecolor(ec_sel if tid == self.selected_tip else ec)
        if draw:
            self.canvas.draw_idle()

    # --- 標註 ----------------------------------------------------------------------
    def add_annotation(self, ann: Annotation) -> Annotation:
        self.host.before_model_change("ann_add")
        if not ann.id or self.model.find_ann(ann.id) is not None:
            ann.id = self.model.next_ann_id()
        self.model.annotations.append(ann)
        self._draw_ann(ann)
        self.host.on_model_change("ann_add")
        self.canvas.draw_idle()
        return ann

    def update_annotation(self, ann_id: int, **fields) -> None:
        ann = self.model.find_ann(ann_id)
        if ann is None:
            return
        self.host.before_model_change("ann_edit")
        for k, v in fields.items():
            if hasattr(ann, k):
                setattr(ann, k, v)
        art = self.ann_artists.pop(ann_id, None)
        if art is not None:
            remove_artist(art)
        self._draw_ann(ann)
        self._highlight_ann(draw=False)
        self.host.on_model_change("ann_edit")
        self.canvas.draw_idle()

    def remove_annotation(self, ann_id: int) -> None:
        ann = self.model.find_ann(ann_id)
        if ann is None:
            return
        self.host.before_model_change("ann_remove")
        art = self.ann_artists.pop(ann_id, None)
        if art is not None:
            remove_artist(art)
        self.model.annotations.remove(ann)
        if self.selected_ann == ann_id:
            self.selected_ann = None
        self.host.on_model_change("ann_remove")
        self.canvas.draw_idle()

    def _draw_ann(self, ann: Annotation) -> bool:
        ax = self.host.axes_for_key(ann.axes_key)
        if ax is None:
            return False
        self.ann_artists[ann.id] = draw_annotation(ax, ann, self.host.style())
        return True

    # --- 重建 ----------------------------------------------------------------------
    def reset(self) -> None:
        """host 已經 fig.clear()：忘掉所有 artist（它們已經不存在）。"""
        self.tip_artists.clear()
        self.ann_artists.clear()
        self._wheel_streams.clear()
        self._hover_timer_stop()
        self._htip = None
        self._hover_bg = None
        self._drag = None
        self._press = None
        self._bg = None
        self._blit_artists = []
        self._ruler_cache = None
        self._last_axes = []
        self._set_cursor(None)
        if self.cursors is not None:
            self.cursors.forget()                   # 游標的 artist 跟著 fig.clear() 沒了；位置留著，host 重畫後 attach()
        for key in [k for k in self._home_view if k[0] == "id"]:   # 沒有 host key 的 axes 已經不存在（id 可能被新物件重用）
            del self._home_view[key]

    def rebuild(self) -> Tuple[int, int]:
        """依模型重畫全部資料提示與標註；回傳 (畫出的提示數, 畫出的標註數)。畫不出來的保留在模型裡。"""
        self._hover_clear(draw=False)
        for tid in list(self.tip_artists):
            self._remove_tip_artists(tid)
        for aid, art in list(self.ann_artists.items()):
            remove_artist(art)
        self.ann_artists.clear()
        n_tip = sum(1 for tip in list(self.model.tips) if self._draw_tip(tip))
        n_ann = sum(1 for ann in self.model.annotations if self._draw_ann(ann))
        self._highlight_tip(draw=False)
        if self.selected_ann is not None and self.model.find_ann(self.selected_ann) is None:
            self.selected_ann = None
        self._highlight_ann(draw=False)
        return n_tip, n_ann

    # --- 就地編輯 ----------------------------------------------------------------
    def _bbox_of(self, artist):
        try:
            return artist.get_window_extent(self._renderer())
        except Exception:
            return None

    def _inline_rename(self, hit: Hit) -> None:
        uid, t = hit.id, hit.artist
        old = t.get_text().replace(LEGEND_ESCAPE, "")      # 圖例文字可能加了零寬空白（「_」開頭的 label）

        def commit(new: Optional[str]) -> None:
            if new is not None and new.strip() and new.strip() != old:
                self.host.on_rename(uid, new.strip())

        bb = self._bbox_of(t)
        if bb is None or not self.host.begin_inline_edit(bb, old, commit):
            self.host.on_double_click(hit, None)

    def _inline_edit_text(self, hit: Hit) -> None:
        ann_id, art = hit.id, hit.artist
        old = art.get_text()

        def commit(new: Optional[str]) -> None:
            if new is not None and new.strip() and new.strip() != old:
                self.host.on_edit_text(ann_id, new.strip())

        bb = self._bbox_of(art)
        if bb is None or not self.host.begin_inline_edit(bb, old, commit):
            self.host.on_edit_annotation(ann_id)

    # --- 右鍵選單項目（host 把它們加進自己的選單）---------------------------------------
    def legend_menu_items(self, hit: Hit) -> List[Optional[Tuple[str, Any]]]:
        """圖例右鍵：MATLAB 圖例預設右鍵選單裡 DSV 做得到的兩項——Delete、Location（子選單用 (label, [(子項, 回呼), …]) 表示）。"""
        if hit.kind not in ("legend", "legend_box") or hit.ax is None:
            return []
        ax = hit.ax
        subs = [(tr(name), (lambda loc=loc: self.host.on_legend_loc(ax, loc))) for name, loc in LEGEND_LOCS]
        return [(tr("刪除圖例"), lambda: self.host.on_legend_delete(ax)), (tr("圖例位置"), subs), None]

    def menu_items(self, hit: Hit, event=None) -> List[Optional[Tuple[str, Any]]]:
        items: List[Optional[Tuple[str, Any]]] = list(self.legend_menu_items(hit))
        if hit.kind == "tip":
            items.append((tr("刪除這個資料提示"), lambda tid=hit.id: self.remove_tip(tid)))
            items.append((tr("匯出資料提示…"), self.export_tips_dialog))
            items.append((tr("複製資料提示（TSV）"), self.copy_tips))
            items.append((tr("提示內容…"), self.tip_fields_dialog))
            items.append(None)
        if hit.kind in ("text", "refline"):
            items.append((tr("編輯標註…"), lambda aid=hit.id: self.host.on_edit_annotation(aid)))
            items.append((tr("刪除標註"), lambda aid=hit.id: self.remove_annotation(aid)))
        if hit.kind in ("empty", "line", "refline") and event is not None and hit.ax is not None:   # 圖例上＝只有圖例自己的項目（MATLAB 圖例選單）
            x, y = data_coords(hit.ax, event)
            ax = hit.ax
            items.append((tr("插入垂直參考線（x = {x:.6g}）").format(x=self.host.display_x(ax, x)),
                          lambda: self.host.on_insert("xline", ax, x, y)))
            items.append((tr("插入水平參考線（y = {y:.6g}）").format(y=y), lambda: self.host.on_insert("yline", ax, x, y)))
            items.append((tr("插入文字…"), lambda: self.host.on_insert("text", ax, x, y)))
            items.append(None)
            items.append((tr("還原視圖 (Home)"), self.restore_view))
            items.append((tr("只匯出這個 panel…"), lambda: self.export_axes_dialog(ax)))
        if self.model.tips:
            items.append((tr("清除全部資料提示"), self.clear_tips))
        while items and items[-1] is None:          # 結尾不留分隔線（host 會自己再加一條）
            items.pop()
        return items
