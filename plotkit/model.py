# -*- coding: utf-8 -*-
"""plotkit.model — 資料模型（Series／Annotation／DataTip／FigureState）與 JSON 存讀。

不需要 Tk，也不需要 matplotlib 的畫布，可以在 headless 環境使用與測試。
"""
from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from .i18n import tr
from .styles import LINESTYLES, MARKERS, STYLES

FORMAT_NAME = "plotkit-figure"
FORMAT_VERSION = 1
CLIPBOARD: List["Series"] = []        # 程式內部的訊號剪貼簿（跨視窗、跨程式模組共用同一個 list）


# ---------------------------------------------------------------------------
# 陣列編碼：等差 → {"start","step","n"}；整數值 → int list；其他 → float list
# ---------------------------------------------------------------------------
def encode_array(a: np.ndarray) -> Any:
    a = np.asarray(a, dtype=float)
    n = int(a.size)
    if n == 0:
        return []
    if n >= 3:
        step = (a[-1] - a[0]) / (n - 1)
        cand = a[0] + np.arange(n) * step
        if np.array_equal(cand, a):
            return {"start": float(a[0]), "step": float(step), "n": n}
    if np.all(np.isfinite(a)) and np.all(a == np.rint(a)) and np.all(np.abs(a) < 2 ** 53):
        return [int(v) for v in a.tolist()]
    return a.tolist()


def decode_array(obj: Any) -> np.ndarray:
    if isinstance(obj, dict) and "n" in obj:
        n = int(obj["n"])
        return float(obj.get("start", 0.0)) + np.arange(n) * float(obj.get("step", 1.0))
    return np.asarray(obj, dtype=float)


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------
@dataclass
class Series:
    """一條線。kind="step" 時 x 可以是 N 或 N+1 個點（N+1：最後一個 x 是最後一段的結束位置）。"""
    label: str
    x: np.ndarray
    y: np.ndarray
    kind: str = "line"                 # "line" | "step"
    uid: int = 0
    color: Optional[str] = None        # None → 依風格色序
    lw: Optional[float] = None         # None → 風格預設線寬
    ls: Optional[str] = None           # None → "-"
    marker: str = ""
    ms: Optional[float] = None
    alpha: float = 1.0
    visible: bool = True
    yaxis: str = "left"                # "left" | "right"
    xshift: float = 0.0
    yshift: float = 0.0
    xunit: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    disp: str = "analog"               # "digital"＝畫成匯流排（六角框＋數值，plotkit.bus；DSV 數位訊號貼過來時）
    radix: str = ""                    # 匯流排文字的進位制 ""＝十進位／hex／bin／oct／sdec／udec
    bits: int = 0                      # 位元寬度（0＝依值）

    def __post_init__(self):
        # 已經是唯讀 float64 陣列就直接共用（undo 快照、複製貼上不複製資料）；其他輸入複製一份
        self.x = self._as_readonly(self.x)
        self.y = self._as_readonly(self.y)
        n = len(self.y)
        if self.kind not in ("line", "step"):
            raise ValueError(tr("kind 必須是 line 或 step：{kind}").format(kind=repr(self.kind)))
        if self.kind == "step":
            if len(self.x) not in (n, n + 1):
                raise ValueError(tr("step 的 x 長度要是 {n} 或 {n1}，現在是 {nx}").format(n=n, n1=n + 1, nx=len(self.x)))
        elif len(self.x) != n:
            raise ValueError(tr("x、y 長度不同：{nx} vs {ny}").format(nx=len(self.x), ny=n))
        if self.ls not in (None,) + tuple(LINESTYLES):
            self.ls = None
        if self.marker not in MARKERS:
            self.marker = ""
        if self.yaxis not in ("left", "right"):
            self.yaxis = "left"
        if self.disp not in ("analog", "digital"):
            self.disp = "analog"
        if self.radix not in ("", "hex", "bin", "oct", "sdec", "udec"):
            self.radix = ""
        try:
            self.bits = max(0, min(64, int(self.bits or 0)))
        except (TypeError, ValueError):
            self.bits = 0
        self.label = str(self.label)
        self._x_sorted = bool(len(self.x) < 2 or np.all(np.diff(self.x) >= 0))

    @staticmethod
    def _as_readonly(a) -> np.ndarray:
        if isinstance(a, np.ndarray) and a.dtype == np.float64 and a.ndim == 1 and not a.flags.writeable:
            return a
        arr = np.array(a, dtype=float).reshape(-1)
        arr.flags.writeable = False
        return arr

    @property
    def n(self) -> int:
        return int(len(self.y))

    @property
    def x_sorted(self) -> bool:
        return self._x_sorted

    def plot_xy(self) -> Tuple[np.ndarray, np.ndarray]:
        """實際畫的 (x, y)：套用位移；step 且 x 多一點時把 y 補最後一個值。"""
        y = self.y
        if len(y) == 0:
            return self.x[:0] + self.xshift, y + self.yshift
        if self.kind == "step" and len(self.x) == len(y) + 1:
            y = np.append(y, y[-1])
        return self.x + self.xshift, y + self.yshift

    def vertex(self, i: int) -> Tuple[float, float]:
        """第 i 個樣本點（0..n-1）畫出來的位置。"""
        i = int(max(0, min(self.n - 1, i)))
        return float(self.x[i] + self.xshift), float(self.y[i] + self.yshift)

    def copy(self, **changes) -> "Series":
        d = self.to_fields()
        d.update(changes)
        return Series(**d)

    def to_fields(self) -> dict:
        return {"label": self.label, "x": self.x, "y": self.y, "kind": self.kind, "uid": self.uid,
                "color": self.color, "lw": self.lw, "ls": self.ls, "marker": self.marker, "ms": self.ms,
                "alpha": self.alpha, "visible": self.visible, "yaxis": self.yaxis, "xshift": self.xshift,
                "yshift": self.yshift, "xunit": self.xunit, "meta": dict(self.meta),
                "disp": self.disp, "radix": self.radix, "bits": self.bits}

    @property
    def is_bus(self) -> bool:
        return self.disp == "digital"

    def to_dict(self) -> dict:
        d = self.to_fields()
        d["x"] = encode_array(self.x)
        d["y"] = encode_array(self.y)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Series":
        d = dict(d)
        d["x"] = decode_array(d.get("x", []))
        d["y"] = decode_array(d.get("y", []))
        known = {"label", "x", "y", "kind", "uid", "color", "lw", "ls", "marker", "ms", "alpha",
                 "visible", "yaxis", "xshift", "yshift", "xunit", "meta", "disp", "radix", "bits"}
        kw = {k: v for k, v in d.items() if k in known}
        kw.setdefault("label", "")
        if kw.get("meta") is None:
            kw["meta"] = {}
        s = cls(**kw)
        s.uid = int(s.uid or 0)
        s.lw = None if s.lw in (None, "", 0) else float(s.lw)
        s.ms = None if s.ms in (None, "", 0) else float(s.ms)
        s.alpha = float(s.alpha if s.alpha is not None else 1.0)
        s.xshift = float(s.xshift or 0.0)
        s.yshift = float(s.yshift or 0.0)
        s.visible = bool(s.visible)
        return s


def from_dsv_snapshot(d: dict) -> Series:
    """把 DSV v3.2 的剪貼簿 dict（label/x/y/color/lw/ls/xunit/xshift/yshift）轉成 Series。"""
    return Series(label=d.get("label", ""), x=d["x"], y=d["y"], kind="step", color=d.get("color"),
                  lw=d.get("lw"), ls=d.get("ls"), xunit=d.get("xunit", ""), xshift=float(d.get("xshift", 0.0)),
                  yshift=float(d.get("yshift", 0.0)))


# ---------------------------------------------------------------------------
# Annotation / DataTip
# ---------------------------------------------------------------------------
@dataclass
class Annotation:
    """xline（垂直參考線，value=x）、yline（水平參考線，value=y）、text（文字，x,y）。"""
    kind: str = "text"
    id: int = 0
    value: float = 0.0
    x: float = 0.0
    y: float = 0.0
    text: str = ""
    color: Optional[str] = None        # None → 風格的 annotation_color
    lw: float = 0.5                    # MATLAB R2025a ConstantLine 預設：LineWidth 0.5、LineStyle '-'、Alpha 0.7（-batch 實測）
    ls: str = "-"
    alpha: float = 0.7
    fontsize: Optional[float] = None   # None → 風格的 fontsize（MATLAB 的 xline 標籤與 text 都是 FontSize 10，跟座標軸同字級）
    axes_key: Any = "left"             # 任意可 JSON 的值；plotkit 用 "left"/"right"，DSV 用 "P1"/"P1R"
    ha: str = "left"
    va: str = "bottom"
    boxed: bool = True
    visible: bool = True

    def __post_init__(self):
        if self.kind not in ("xline", "yline", "text"):
            raise ValueError(tr("kind 必須是 xline / yline / text：{kind}").format(kind=repr(self.kind)))

    def to_dict(self) -> dict:
        return {"kind": self.kind, "id": self.id, "value": self.value, "x": self.x, "y": self.y, "text": self.text,
                "color": self.color, "lw": self.lw, "ls": self.ls, "alpha": self.alpha, "fontsize": self.fontsize,
                "axes_key": self.axes_key, "ha": self.ha, "va": self.va, "boxed": self.boxed, "visible": self.visible}

    @classmethod
    def from_dict(cls, d: dict) -> "Annotation":
        known = {f for f in cls.__dataclass_fields__}
        kw = {k: v for k, v in d.items() if k in known}
        kw.setdefault("alpha", 1.0)        # 舊存檔沒有 alpha 鍵＝當時畫的是不透明（0.7 只給新插入的參考線）
        a = cls(**kw)
        a.id = int(a.id or 0)
        a.value = float(a.value or 0.0)
        a.x = float(a.x or 0.0)
        a.y = float(a.y or 0.0)
        a.alpha = 1.0 if a.alpha is None else float(a.alpha)
        return a


TIP_OFFSET_DEFAULT = (5.0, 5.0)     # 文字錨點離資料點的偏移（點）；正負號＝框貼在點的哪一角（見 draw.tip_anchor）


@dataclass
class DataTip:
    """釘住的資料提示：指向某條線（uid）的第 index 個樣本，offset 是文字錨點相對頂點的偏移（點）；
    offset 的正負號決定框在資料點的哪一角（像 MATLAB 的 Location：右上 northeast＝(+,+)、右下 southeast＝(+,−)…）。"""
    uid: int
    index: int
    id: int = 0
    offset: Tuple[float, float] = TIP_OFFSET_DEFAULT
    axes_key: Any = None
    text: Optional[str] = None

    def to_dict(self) -> dict:
        return {"uid": self.uid, "index": self.index, "id": self.id, "offset": [float(self.offset[0]), float(self.offset[1])],
                "axes_key": self.axes_key, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> "DataTip":
        off = d.get("offset")
        try:
            off = (float(off[0]), float(off[1]))
        except Exception:                                   # 缺、長度不對、不是數字 → 預設
            off = TIP_OFFSET_DEFAULT
        return cls(uid=int(d.get("uid", 0)), index=int(d.get("index", 0)), id=int(d.get("id", 0)),
                   offset=off, axes_key=d.get("axes_key"), text=d.get("text"))


# ---------------------------------------------------------------------------
# FigureState
# ---------------------------------------------------------------------------
def _default_view() -> Dict[str, Any]:
    return {"xlim": None, "ylim": None, "ylim_right": None}


@dataclass
class FigureState:
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    ylabel_right: str = ""
    style: Any = "default"             # 風格名稱或 dict
    grid: bool = True
    legend: bool = True
    legend_loc: str = "upper right"
    xunit: str = ""
    series: List[Series] = field(default_factory=list)
    annotations: List[Annotation] = field(default_factory=list)
    tips: List[DataTip] = field(default_factory=list)
    view: Dict[str, Any] = field(default_factory=_default_view)
    tip_fields: List[str] = field(default_factory=lambda: ["name", "x", "y"])   # 資料提示顯示的列（「提示內容…」）
    next_uid: int = 1
    next_ann_id: int = 1
    next_tip_id: int = 1

    def __post_init__(self):
        self.normalize_ids()

    def normalize_ids(self) -> None:
        """沒給或重複的 uid／id 自動補上（FigureState(series=[...]) 直接建、或讀到壞檔時）。"""
        def fix(items, attr, nxt):
            used, dup = set(), []
            for it in items:
                v = getattr(it, attr)
                if v and v not in used:
                    used.add(v)
                else:
                    dup.append(it)                   # 沒給（0）或和前面重複
            cur = max(used | {int(nxt) - 1}, default=0)
            for it in dup:
                cur += 1
                while cur in used:
                    cur += 1
                setattr(it, attr, cur)
                used.add(cur)
            return max(used, default=0) + 1

        self.next_uid = fix(self.series, "uid", self.next_uid)
        self.next_ann_id = fix(self.annotations, "id", self.next_ann_id)
        self.next_tip_id = fix(self.tips, "id", self.next_tip_id)

    # --- 查詢 ---
    def find(self, uid: int) -> Optional[Series]:
        return next((s for s in self.series if s.uid == uid), None)

    def visible_series(self) -> List[Series]:
        return [s for s in self.series if s.visible]

    def has_right_axis(self) -> bool:
        return any(s.visible and s.yaxis == "right" for s in self.series)

    def index_of(self, uid: int) -> int:
        return next((i for i, s in enumerate(self.series) if s.uid == uid), -1)

    # --- 修改 ---
    def add_series(self, s: Series) -> Series:
        if not s.uid or self.find(s.uid) is not None:
            s.uid = self.next_uid
        self.next_uid = max(self.next_uid, s.uid + 1)
        self.series.append(s)
        return s

    def remove_series(self, uids: Iterable[int]) -> None:
        uids = set(uids)
        self.series = [s for s in self.series if s.uid not in uids]
        self.tips[:] = [t for t in self.tips if t.uid not in uids]     # 原地改：Interactor 持有同一個 list

    def add_annotation(self, a: Annotation) -> Annotation:
        if not a.id or any(x.id == a.id for x in self.annotations):
            a.id = self.next_ann_id
        self.next_ann_id = max(self.next_ann_id, a.id + 1)
        self.annotations.append(a)
        return a

    def add_tip(self, t: DataTip) -> DataTip:
        if not t.id or any(x.id == t.id for x in self.tips):
            t.id = self.next_tip_id
        self.next_tip_id = max(self.next_tip_id, t.id + 1)
        self.tips.append(t)
        return t

    # --- 快照（給 undo 用，陣列共用不複製）---
    def snapshot(self) -> dict:
        return {"title": self.title, "xlabel": self.xlabel, "ylabel": self.ylabel, "ylabel_right": self.ylabel_right,
                "style": self.style if isinstance(self.style, str) else dict(self.style),
                "grid": self.grid, "legend": self.legend, "legend_loc": self.legend_loc, "xunit": self.xunit,
                "series": [s.to_fields() for s in self.series],
                "annotations": [a.to_dict() for a in self.annotations],
                "tips": [t.to_dict() for t in self.tips],
                "view": dict(self.view), "tip_fields": list(self.tip_fields), "next_uid": self.next_uid,
                "next_ann_id": self.next_ann_id, "next_tip_id": self.next_tip_id}

    def restore(self, snap: dict) -> None:
        self.title = snap.get("title", "")
        self.xlabel = snap.get("xlabel", "")
        self.ylabel = snap.get("ylabel", "")
        self.ylabel_right = snap.get("ylabel_right", "")
        self.style = snap.get("style", "default")
        self.grid = bool(snap.get("grid", True))
        self.legend = bool(snap.get("legend", True))
        self.legend_loc = snap.get("legend_loc", "upper right")
        if isinstance(self.legend_loc, list):            # JSON 存不了 tuple：拖曳圖例存的 (x, y) 讀回來是 list
            self.legend_loc = tuple(float(v) for v in self.legend_loc[:2])
        self.xunit = snap.get("xunit", "")
        self.series = [Series(**d) if isinstance(d.get("x"), np.ndarray) else Series.from_dict(d) for d in snap.get("series", [])]
        # 清掉舊的 list 內容再放回去：Interactor 可能持有同一個 list 物件
        self.annotations[:] = [Annotation.from_dict(d) for d in snap.get("annotations", [])]
        self.tips[:] = [DataTip.from_dict(d) for d in snap.get("tips", [])]
        self.view = dict(snap.get("view") or _default_view())
        tf = snap.get("tip_fields")                       # 舊檔沒有：預設（名稱／X／Y）
        self.tip_fields = [str(k) for k in tf] if isinstance(tf, list) and tf else ["name", "x", "y"]
        self.next_uid = int(snap.get("next_uid", 1))
        self.next_ann_id = int(snap.get("next_ann_id", 1))
        self.next_tip_id = int(snap.get("next_tip_id", 1))
        self.normalize_ids()

    def copy(self) -> "FigureState":
        st = FigureState()
        st.restore(self.snapshot())
        return st


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------
def state_to_dict(state: FigureState) -> dict:
    from . import __version__
    d = state.snapshot()
    d["series"] = [s.to_dict() for s in state.series]
    d.update({"format": FORMAT_NAME, "version": FORMAT_VERSION, "plotkit": __version__,
              "saved": time.strftime("%Y-%m-%dT%H:%M:%S")})
    return d


def migrate_dict(d: dict) -> Tuple[dict, Optional[str]]:
    """把舊／新版本的 dict 調整成目前格式；回傳 (dict, 警告或 None)。"""
    if not isinstance(d, dict):
        raise ValueError(tr("JSON 內容不是物件"))
    warning = None
    ver = d.get("version")
    try:
        ver_i = 1 if ver is None else int(ver)
    except (TypeError, ValueError):
        warning = tr("檔案版本欄位 {ver} 看不懂，當作 {supported}").format(ver=repr(ver), supported=FORMAT_VERSION)
        ver_i = FORMAT_VERSION
    d["version"] = ver_i
    if ver_i > FORMAT_VERSION:
        warning = tr("檔案格式版本 {ver} 比 plotkit 支援的 {supported} 新，盡量讀取").format(ver=ver_i, supported=FORMAT_VERSION)
    if d.get("format") not in (None, FORMAT_NAME):
        warning = tr("檔案格式 {fmt} 不是 {expected}，盡量讀取").format(fmt=repr(d.get("format")), expected=FORMAT_NAME)
    for k in ("series", "annotations", "tips"):                 # null 或不是清單 → 空清單
        if not isinstance(d.get(k), list):
            d[k] = []
    if not isinstance(d.get("view"), dict):
        d["view"] = _default_view()
    st = d.get("style")
    if isinstance(st, str) and st not in STYLES:
        warning = tr("沒有 {name} 這個風格，改用 default").format(name=repr(st))
        d["style"] = "default"
    return d, warning


def state_from_dict(d: dict) -> FigureState:
    if not isinstance(d, dict):
        raise ValueError(tr("JSON 內容不是物件"))
    d, _warn = migrate_dict(dict(d))
    st = FigureState()
    st.restore(d)
    return st


def save_json(state: FigureState, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state_to_dict(state), f, ensure_ascii=False, separators=(",", ":"), allow_nan=True)


def load_json(path: str) -> FigureState:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return state_from_dict(d)


def file_summary(path: str) -> str:
    st = load_json(path)
    return tr("{name}：{n_series} 條線、{n_ann} 個標註、{n_tips} 個資料提示").format(
        name=os.path.basename(path), n_series=len(st.series), n_ann=len(st.annotations), n_tips=len(st.tips))
