# -*- coding: utf-8 -*-
"""雙位準量測與峰值搜尋（MATLAB Time Scope 的 Bilevel Measurements／Peak Finder）——純 numpy、向量化，和 GUI 分開。

定義照 MATLAB R2025a Signal Processing Toolbox 的文件（statelevels、risetime、falltime、slewrate、overshoot、undershoot、
settlingtime、midcross、pulsewidth、pulseperiod、dutycycle、findpeaks），程式是自己寫的；tests/matlab_ref/ 的測試訊號與
MATLAB 算出的數值由 selftest() 逐筆比對（tools/matlab_ref/ 有產生它們的 .m 腳本）。

時間：樣本 i 的時刻 t = x0 + i·dx（DSV 用 symbol；換成秒要除以 symbol rate）。
- 狀態位準：直方圖 100 格（最小～最大），下半與上半各取樣本最多的那一格的「中心」。
- 轉態：訊號離開一個狀態的容差帶（|y − 狀態| ≤ tol% × 振幅）、接著進入另一個狀態的容差帶；runt 脈波（沒進到另一個狀態）不算。
- 參考位準交越用相鄰樣本線性內插；上升時間＝第一次越過下參考位準 → 最後一次越過上參考位準（下降相反）。
- 過衝／下衝（post）：從進入最終狀態容差帶的時刻起、長 3 × 轉態時間（遇到下一個轉態或資料尾就截斷）的區段，
  最高點高於最終狀態多少（overshoot）、最低點低於最終狀態多少（undershoot），% of 振幅（可為負）。
  前衝（pre）：到最後離開起始狀態容差帶的時刻為止、往前同樣長的區段，相對於起始狀態。
- 穩定時間：中位準交越時刻起算，到訊號進入並一直留在最終狀態容差帶內為止，觀察 d 長度；資料不夠長、或 d 內開始下一個轉態 → NaN。
  視窗包含 t ≥ 交越＋d 的第一個樣本（MATLAB 比對結果）。
- Time Scope 面板顯示的是這些逐轉態數值的平均（MathWorks「Scope Bilevel Measurements」文件），次數是總數。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DEFAULT_TOL = 2.0                     # State Level Tol. (%)
DEFAULT_REF = (10.0, 50.0, 90.0)      # Lower／Mid／Upper Ref. Level (%)
DEFAULT_SETTLE_SEEK_S = 0.02          # Settle Seek (s)（Time Scope 預設；使用者 2026-10-23 選照 MATLAB）
SEEK_FACTOR = 3.0                     # overshoot／undershoot 的 SeekFactor 預設
PEAK_DEFAULTS = {"num": 3, "min_height": -math.inf, "min_dist": 1, "threshold": 0.0, "label": False}   # Time Scope PeakFinder 預設


def state_levels(y, nbins: int = 100) -> Tuple[float, float]:
    """MATLAB statelevels（histogram mode）：值域 [min, max] 分 nbins 格，下半、上半各取樣本最多那一格的中心。全部同值 → (v, v)。"""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return math.nan, math.nan
    lo, hi = float(np.min(y)), float(np.max(y))
    if not hi > lo:
        return lo, hi
    counts, edges = np.histogram(y, bins=nbins, range=(lo, hi))
    half = nbins // 2
    out = []
    for a, b in ((0, half), (half, nbins)):
        k = a + int(np.argmax(counts[a:b]))
        out.append(float((edges[k] + edges[k + 1]) / 2.0))
    return out[0], out[1]


def _events(y: np.ndarray, t: np.ndarray, level: float) -> Tuple[np.ndarray, np.ndarray]:
    """越過 level 的事件：(pos, time)。剛好等於 level 的樣本 k → pos=k、time=t[k]；相鄰兩點分在兩側 → pos=k+0.5、線性內插。依 pos 排序。"""
    d = y - level
    with np.errstate(invalid="ignore"):
        exact = np.nonzero(d == 0)[0]
        sc = np.nonzero(d[:-1] * d[1:] < 0)[0]
    f = d[sc] / (d[sc] - d[sc + 1])
    pos = np.concatenate([exact.astype(float), sc + 0.5])
    tm = np.concatenate([t[exact], t[sc] + f * (t[sc + 1] - t[sc])])
    order = np.argsort(pos, kind="stable")
    return pos[order], tm[order]


def _first_last_in(pos: np.ndarray, tm: np.ndarray, i0: np.ndarray, i1: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """每個 [i0, i1] 視窗裡第一個與最後一個事件的時刻（沒有就 NaN）。"""
    a = np.searchsorted(pos, i0, side="left")
    b = np.searchsorted(pos, i1, side="right") - 1
    ok = a <= b
    first = np.full(i0.size, np.nan)
    last = np.full(i0.size, np.nan)
    first[ok] = tm[a[ok]]
    last[ok] = tm[b[ok]]
    return first, last


def _cross_between(y: np.ndarray, t: np.ndarray, level, i: np.ndarray, j: np.ndarray) -> np.ndarray:
    """樣本 i→j 之間越過 level 的內插時刻（向量）；沒越過（或兩點一樣）就給 t[j]。"""
    a = y[i] - level
    b = y[j] - level
    den = a - b
    with np.errstate(invalid="ignore", divide="ignore"):
        f = np.where(den != 0, a / den, 1.0)
    f = np.where((f >= 0) & (f <= 1), f, 1.0)
    return t[i] + f * (t[j] - t[i])


def transitions(y, low: float, high: float, tol: float = DEFAULT_TOL) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(polarity ±1, i_start＝最後一個在起始狀態容差帶的樣本, i_end＝第一個在最終狀態容差帶的樣本)，依時間排序。"""
    y = np.asarray(y, dtype=float)
    amp = high - low
    empty = (np.zeros(0, int), np.zeros(0, int), np.zeros(0, int))
    if y.size < 2 or not amp > 0:
        return empty
    band = tol / 100.0 * amp
    st = np.full(y.size, -1, dtype=np.int8)
    with np.errstate(invalid="ignore"):
        st[np.abs(y - low) <= band] = 0
        st[np.abs(y - high) <= band] = 1
    idx = np.nonzero(st >= 0)[0]
    if idx.size < 2:
        return empty
    s = st[idx]
    ch = np.nonzero(s[1:] != s[:-1])[0]
    i0 = idx[ch]
    i1 = idx[ch + 1]
    pol = np.where(s[ch + 1] == 1, 1, -1)
    return pol, i0, i1


def bilevel(y, x0: float = 0.0, dx: float = 1.0, tol: float = DEFAULT_TOL, ref: Sequence[float] = DEFAULT_REF,
            levels: Optional[Tuple[float, float]] = None, settle_d: Optional[float] = None,
            seek_factor: float = SEEK_FACTOR) -> Dict[str, Any]:
    """逐轉態的雙位準量測。settle_d＝Settle Seek（和 x 同單位）；None 就不算穩定時間。
    回傳 dict：low、high、ref_lo／ref_mid／ref_hi（位準）與同長度陣列 pol、t_lo、t_hi、t_mid、dur、slew、over、under、pre_over、pre_under、settle。"""
    y = np.asarray(y, dtype=float)
    n = y.size
    low, high = levels if levels is not None else state_levels(y)
    out: Dict[str, Any] = {"low": low, "high": high}
    names = ("pol", "t_lo", "t_hi", "t_mid", "dur", "slew", "over", "under", "pre_over", "pre_under", "settle")
    amp = high - low if (np.isfinite(low) and np.isfinite(high)) else math.nan
    if n < 2 or not amp > 0:
        out.update({k: np.zeros(0) for k in names})
        out.update(ref_lo=math.nan, ref_mid=math.nan, ref_hi=math.nan)
        return out
    r_lo, r_mid, r_hi = (low + float(r) / 100.0 * amp for r in ref)
    out.update(ref_lo=r_lo, ref_mid=r_mid, ref_hi=r_hi)
    pol, i0, i1 = transitions(y, low, high, tol)
    m = pol.size
    if m == 0:
        out.update({k: np.zeros(0) for k in names})
        return out
    t = x0 + np.arange(n) * dx
    p_lo, e_lo = _events(y, t, r_lo)
    p_hi, e_hi = _events(y, t, r_hi)
    p_md, e_md = _events(y, t, r_mid)
    lo_first, lo_last = _first_last_in(p_lo, e_lo, i0, i1)
    hi_first, hi_last = _first_last_in(p_hi, e_hi, i0, i1)
    t_mid, _ = _first_last_in(p_md, e_md, i0, i1)
    rising = pol > 0
    t_lo = np.where(rising, lo_first, lo_last)
    t_hi = np.where(rising, hi_last, hi_first)
    dur = np.abs(t_hi - t_lo)
    with np.errstate(invalid="ignore", divide="ignore"):
        slew = np.where(rising, 1.0, -1.0) * (r_hi - r_lo) / dur
    band = tol / 100.0 * amp
    final = np.where(rising, high, low)
    init = np.where(rising, low, high)
    b_init = np.where(rising, low + band, high - band)
    b_final = np.where(rising, high - band, low + band)
    ext = _cross_between(y, t, b_init, i0, np.minimum(i0 + 1, n - 1))       # 最後離開起始狀態的時刻
    ent = _cross_between(y, t, b_final, np.maximum(i1 - 1, 0), i1)          # 進入最終狀態的時刻
    # post 區段 [ent, min(ent + seek×dur, 下一個轉態的 ext, 資料尾)]
    post_end = ent + seek_factor * dur
    nxt = np.append(ext[1:], np.inf)
    post_end = np.minimum(np.minimum(post_end, nxt), t[-1])
    pa = np.searchsorted(t, ent, side="left")
    pb = np.searchsorted(t, post_end, side="right") - 1
    # pre 區段 [max(ext − seek×dur, 上一個轉態的 ent, 資料頭), ext]
    pre_start = ext - seek_factor * dur
    prv = np.insert(ent[:-1], 0, -np.inf)
    pre_start = np.maximum(np.maximum(pre_start, prv), t[0])
    qa = np.searchsorted(t, pre_start, side="left")
    qb = np.searchsorted(t, ext, side="right") - 1
    ymax_post, ymin_post = _seg_maxmin(y, pa, pb)
    ymax_pre, ymin_pre = _seg_maxmin(y, qa, qb)
    with np.errstate(invalid="ignore"):
        over = (ymax_post - final) / amp * 100.0
        under = (final - ymin_post) / amp * 100.0
        pre_over = (ymax_pre - init) / amp * 100.0
        pre_under = (init - ymin_pre) / amp * 100.0
    settle = np.full(m, np.nan)
    if settle_d is not None and settle_d > 0 and np.isfinite(settle_d):
        settle = _settling(y, t, t_mid, rising, high, low, band, ext, float(settle_d))
    out.update(pol=pol.astype(float), t_lo=t_lo, t_hi=t_hi, t_mid=t_mid, dur=dur, slew=slew, over=over, under=under,
               pre_over=pre_over, pre_under=pre_under, settle=settle)
    return out


def _seg_maxmin(y: np.ndarray, a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """每段 y[a..b]（含 b）的最大與最小；空段 NaN。"""
    m = a.size
    mx = np.full(m, np.nan)
    mn = np.full(m, np.nan)
    ok = (a <= b) & (a >= 0) & (b < y.size)
    if not ok.any():
        return mx, mn
    aa, bb = a[ok], b[ok] + 1
    ye = np.append(y, np.nan)                       # 末端哨兵：段尾 = len(y) 時 reduceat 仍合法
    idx = np.ravel(np.column_stack([aa, bb]))
    with np.errstate(invalid="ignore"):
        mx[ok] = np.maximum.reduceat(ye, idx)[::2]
        mn[ok] = np.minimum.reduceat(ye, idx)[::2]
    return mx, mn


def _settling(y, t, t_mid, rising, high, low, band, ext, d) -> np.ndarray:
    n = y.size
    m = t_mid.size
    res = np.full(m, np.nan)
    idx = np.arange(n)
    with np.errstate(invalid="ignore"):
        out_hi = ~(np.abs(y - high) <= band)
        out_lo = ~(np.abs(y - low) <= band)
    last_hi = np.maximum.accumulate(np.where(out_hi, idx, -1))
    last_lo = np.maximum.accumulate(np.where(out_lo, idx, -1))
    t_end = t_mid + d
    with np.errstate(invalid="ignore"):
        j_end = np.searchsorted(t, np.where(np.isfinite(t_end), t_end, np.inf), side="left")
    nxt = np.append(ext[1:], np.inf)
    ok = np.isfinite(t_mid) & (j_end < n) & ~(nxt < t_end)
    k = np.nonzero(ok)[0]
    if k.size == 0:
        return res
    je = j_end[k]
    j = np.where(rising[k], last_hi[je], last_lo[je])
    good = (j >= 0) & (j < je)                         # 視窗尾還在帶外（或從來沒離開過）→ NaN
    k, j = k[good], j[good]
    final = np.where(rising[k], high, low)
    lvl = np.where(y[j] > final, final + band, final - band)
    ts = _cross_between(y, t, lvl, j, j + 1)
    res[k] = ts - t_mid[k]
    return res


def cycles(pol: np.ndarray, t_mid: np.ndarray) -> Dict[str, np.ndarray]:
    """MATLAB pulsewidth／pulseperiod／dutycycle（正、負極性）。正脈波＝上升接下降，寬度＝兩個中位準交越的時間差；
    正週期＝相鄰兩次上升的中位準交越間隔；duty＝第 i 個寬度 ÷ 第 i 個週期（取兩者都有的前幾個）。"""
    pol = np.asarray(pol)
    tm = np.asarray(t_mid, dtype=float)
    out: Dict[str, np.ndarray] = {}
    for sgn, key in ((1, "pos"), (-1, "neg")):
        k = np.nonzero((pol[:-1] == sgn) & (pol[1:] == -sgn))[0] if pol.size >= 2 else np.zeros(0, int)
        w = tm[k + 1] - tm[k]
        starts = tm[pol == sgn]
        p = np.diff(starts) if starts.size >= 2 else np.zeros(0)
        mm = min(w.size, p.size)
        with np.errstate(invalid="ignore", divide="ignore"):
            d = w[:mm] / p[:mm]
        out["w" + key], out["p" + key], out["d" + key] = w, p, d
    return out


def _mean(a) -> Optional[float]:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return float(np.mean(a)) if a.size else None


def summary(b: Dict[str, Any]) -> Dict[str, Any]:
    """Time Scope 面板的值：次數是總數，其他是逐轉態（逐脈波）數值的平均（NaN 不算）。時間單位＝x 單位。"""
    pol = np.asarray(b.get("pol", np.zeros(0)))
    r = pol > 0
    f = pol < 0
    res: Dict[str, Any] = {"low": b.get("low"), "high": b.get("high"), "pedges": int(r.sum()), "nedges": int(f.sum())}
    for name, key, mask in (("rise", "dur", r), ("fall", "dur", f), ("pslew", "slew", r), ("nslew", "slew", f),
                            # Time Scope：+ Transitions 的 Preshoot＝轉態前最低的異常（低於起始狀態）、Overshoot／Undershoot＝轉態後最高／最低；
                            # − Transitions 的 Preshoot＝轉態前最高的異常（高於起始狀態）
                            ("ppre", "pre_under", r), ("pover", "over", r), ("punder", "under", r), ("psettle", "settle", r),
                            ("npre", "pre_over", f), ("nover", "over", f), ("nunder", "under", f), ("nsettle", "settle", f)):
        arr = np.asarray(b.get(key, np.zeros(0)), dtype=float)
        res[name] = _mean(arr[mask]) if arr.size == pol.size else None
    cy = cycles(pol, np.asarray(b.get("t_mid", np.zeros(0)), dtype=float))
    res["npos"], res["nneg"] = int(cy["wpos"].size), int(cy["wneg"].size)
    per = _mean(cy["ppos"])
    res["period"] = per
    res["freq"] = (1.0 / per) if per else None
    res["width"] = _mean(cy["wpos"])
    res["nwidth"] = _mean(cy["wneg"])
    dp, dn = _mean(cy["dpos"]), _mean(cy["dneg"])
    res["duty"] = dp * 100.0 if dp is not None else None
    res["nduty"] = dn * 100.0 if dn is not None else None
    res["edges"] = int(pol.size)
    return res


def find_peaks(y, num: Optional[int] = None, min_height: float = -math.inf, min_dist: float = 0, threshold: float = 0.0,
               sort_desc: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """MATLAB findpeaks（索引單位）：局部極大，平頂取第一個樣本、端點不算；MinPeakHeight 要「大於」；Threshold > 0 時
    只留比左右鄰點都高至少 Threshold 的尖峰（平頂不算）；MinPeakDistance：從最高的開始，距離 ≤ min_dist 的較矮峰丟掉；
    依高度遞減（同高照位置）排序，取前 num 個。回傳 (值, 索引)。NaN 當成 −∞。"""
    y = np.asarray(y, dtype=float)
    yy = np.where(np.isfinite(y), y, -np.inf)
    n = yy.size
    if n < 3:
        return np.zeros(0), np.zeros(0, dtype=int)
    if threshold and threshold > 0:
        with np.errstate(invalid="ignore"):
            cand = np.nonzero(np.minimum(yy[1:-1] - yy[:-2], yy[1:-1] - yy[2:]) >= threshold)[0] + 1
    else:
        start = np.concatenate([[0], np.nonzero(yy[1:] != yy[:-1])[0] + 1])       # 每段等值的第一個樣本
        u = yy[start]
        if u.size >= 3:
            pk = np.nonzero((u[1:-1] > u[:-2]) & (u[1:-1] > u[2:]))[0] + 1
            cand = start[pk]
        else:
            cand = np.zeros(0, dtype=int)
    cand = cand[np.isfinite(yy[cand])]
    cand = cand[yy[cand] > min_height]
    if cand.size and min_dist and min_dist > 1:
        # 距離 ≥ 點數（含 Inf）＝只留最高的：先夾成 n——很大的 Python int（第七輪頻譜視窗的 Min Distance 收 1e19、1e300；第八輪起欄位最多
        # 2^53 − 1，程式呼叫照樣可能更大）直接減會在 searchsorted 換成 C long 時丟 OverflowError（比點數大的距離效果和 Inf 一樣）
        md = n if min_dist >= n else min_dist
        order = cand[np.argsort(-yy[cand], kind="stable")]
        srt = np.sort(cand)
        removed = np.zeros(n, dtype=bool)
        keep: List[int] = []
        for i in order:
            if removed[i]:
                continue
            keep.append(int(i))
            a = np.searchsorted(srt, i - md, side="left")
            b = np.searchsorted(srt, i + md, side="right")
            removed[srt[a:b]] = True
        cand = np.sort(np.asarray(keep, dtype=int))
    if sort_desc and cand.size:
        cand = cand[np.argsort(-yy[cand], kind="stable")]
    if num is not None:
        cand = cand[:int(num)]
    return y[cand], cand


def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref；tools/matlab_ref/*.m 產生）。"""
    import json
    import os
    if not os.path.isdir(ref_dir):
        check(True, "（沒有 tests/matlab_ref：略過 MATLAB 雙位準／峰值比對）")
        return

    def arr(v):
        if v is None:
            return np.zeros(0)
        v = v if isinstance(v, list) else [v]
        return np.asarray([np.nan if x is None else x for x in v], dtype=float)

    R = json.load(open(os.path.join(ref_dir, "bilevel_ref.json"), encoding="utf-8"))
    C = json.load(open(os.path.join(ref_dir, "cycles_ref.json"), encoding="utf-8"))
    fs = 1000.0
    for nm in "ABCD":
        y = np.loadtxt(os.path.join(ref_dir, f"bilevel_{nm}.txt"))
        r = R[nm]
        lv = state_levels(y)
        b = bilevel(y, 0.0, 1.0 / fs, settle_d=0.02)
        rr = b["pol"] > 0
        ok_lv = np.allclose(lv, arr(r["levels"]), atol=1e-12)
        bad = []
        for key, mine, sel in (("rise", b["dur"], rr), ("fall", b["dur"], ~rr), ("slew", b["slew"], None), ("over", b["over"], None),
                               ("under", b["under"], None), ("pre_over", b["pre_over"], None), ("pre_under", b["pre_under"], None),
                               ("settle", b["settle"], None), ("midcross", b["t_mid"], None)):
            mm = mine[sel] if sel is not None else mine
            ref = arr(r[key])
            if not (mm.shape == ref.shape and np.allclose(mm, ref, rtol=1e-9, atol=1e-9, equal_nan=True)):
                bad.append(key)
        cy = cycles(b["pol"], b["t_mid"])
        for key in ("wpos", "ppos", "dpos", "wneg", "pneg", "dneg"):
            ref = arr(C[nm][key])
            if not (cy[key].shape == ref.shape and np.allclose(cy[key], ref, rtol=1e-9, atol=1e-9)):
                bad.append(key)
        check(ok_lv and not bad, f"雙位準 vs MATLAB（訊號 {nm}，{len(b['pol'])} 個轉態）：statelevels、risetime、falltime、slewrate、"
                                f"overshoot、undershoot、preshoot、settlingtime、midcross、pulsewidth／period／dutycycle 逐筆一致"
                                + (f"（不一致：{bad}）" if bad or not ok_lv else ""))
    y = np.loadtxt(os.path.join(ref_dir, "bilevel_D01.txt"))
    D = json.load(open(os.path.join(ref_dir, "digital_ref.json"), encoding="utf-8"))
    b = bilevel(y, 0.0, 1.0, settle_d=2.0)
    b1 = bilevel(y, 0.0, 1.0, settle_d=1.0)
    cy = cycles(b["pol"], b["t_mid"])
    rr = b["pol"] > 0
    good = (np.allclose(state_levels(y), [0.005, 0.995]) and np.allclose(b["t_mid"], arr(D["mid"]))
            and np.allclose(b["settle"], arr(D["settle_d2"]), equal_nan=True) and np.allclose(b1["settle"], arr(D["settle_d1"]), equal_nan=True)
            and np.allclose(b["over"], arr(D["over"])) and np.allclose(b["under"], arr(D["under"]))
            and np.allclose(b["pre_over"], arr(D["pre_over"])) and np.allclose(b["pre_under"], arr(D["pre_under"]))
            and np.allclose(b["dur"][rr], arr(D["rise"])) and np.allclose(b["slew"], arr(D["slew"])))
    c01 = C["D01"]
    good = good and all(np.allclose(cy[k], arr(c01[k])) for k in ("wpos", "ppos", "dpos", "wneg", "pneg", "dneg"))
    check(good, "雙位準 vs MATLAB（理想 0/1 階梯）：狀態位準 0.005／0.995、中位準內插、穩定時間 0.4752、過衝 ±0.505%、脈寬／週期／duty 一致")
    yp = np.loadtxt(os.path.join(ref_dir, "peaks_input.txt"))
    pl = np.loadtxt(os.path.join(ref_dir, "peaks_plateau.txt"))
    cases = {"default3": (yp, dict(num=3)), "dist50": (yp, dict(num=5, min_dist=50)), "thr005": (yp, dict(num=5, threshold=0.05)),
             "minh105": (yp, dict(num=99, min_height=1.05)), "combo": (yp, dict(num=4, min_height=0.5, min_dist=100, threshold=0.01)),
             "plateau": (pl, dict(sort_desc=False)), "plateau_thr1": (pl, dict(threshold=1, sort_desc=False)), "plateau_d3": (pl, dict(min_dist=3))}
    bad = []
    for k, (yy, kw) in cases.items():
        v, i = find_peaks(yy, **kw)
        mv, mi = arr(C["peaks"][k]["v"]), arr(C["peaks"][k]["l"]) - 1
        if not (v.shape == mv.shape and np.allclose(v, mv) and np.array_equal(i, mi.astype(int))):
            bad.append(k)
    check(not bad, f"峰值搜尋 vs MATLAB findpeaks（NPeaks、MinPeakHeight、MinPeakDistance、Threshold、平頂、排序）8 組一致" + (f"（不一致：{bad}）" if bad else ""))
    # 大資料：1e6 點、每 4 個樣本換一次值的時脈，向量化要夠快
    import time as _time
    clk = np.tile([0.0, 0.0, 1.0, 1.0], 250_000)
    t0 = _time.time()
    bb = bilevel(clk, 0.0, 1.0, settle_d=1.0)
    s = summary(bb)
    pv, pi = find_peaks(clk + np.sin(np.arange(clk.size) * 0.01) * 0.01, num=3)
    dt = _time.time() - t0
    check(s["pedges"] == 250_000 and s["nedges"] == 249_999 and abs(s["period"] - 4.0) < 1e-9 and abs(s["duty"] - 50.0) < 1e-9 and dt < 2.0,
          f"雙位準＋峰值：1e6 點時脈（從低開始、停在高：上升 250000、下降 249999 次）{dt:.2f}s、週期 4、duty 50%")
