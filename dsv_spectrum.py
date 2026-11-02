# -*- coding: utf-8 -*-
"""頻譜估計（MATLAB Spectrum Analyzer 的 ESTIMATION／SPECTRUM／SPECTROGRAM 設定）——純 numpy，和 GUI 分開。

依據（MATLAB R2025a；程式是自己寫的，tests/matlab_ref/spectrum_ref.json 是 MATLAB 算出的數值，selftest() 逐筆比對）：
- 視窗：DSP System Toolbox 的視窗規則——Hann／Hamming／Flat Top 用 periodic、Chebyshev＝chebwin(L, 衰減)、
  Kaiser 的 β 由旁波瓣衰減 A 換算（A > 50：0.1102(A−8.7)；21 ≤ A ≤ 50：0.5842(A−21)^0.4 + 0.07886(A−21)；A < 21：0）；
  Blackman-Harris 用 periodic（Signal Labeler 的同一組視窗清單）。
- NENBW（等效雜訊頻寬，bins）＝ L·Σw² / (Σw)²；RBW ＝ NENBW·fs / L。
- RBW → 視窗長度：DSP System Toolbox Spectrum Estimator 的做法——先用 L＝1000 的 NENBW 估 L＝ceil(NENBW·fs/RBW)，
  再用新 L 的 NENBW 反覆修正到不變；遇到循環就挑 RBW 誤差最小的那個 L。RBW Auto ＝ 頻寬 / 1024（雙邊 fs、單邊 fs/2）。
- Overlap (%) → 重疊樣本數：取最接近的整數（一樣近取小的），等於 L 時改成 L−1。
- Welch：每段 L 點、相鄰段重疊 noverlap 點，段數 ⌊(N−noverlap)/(L−noverlap)⌋；FFT 長度比 L 短時把加窗後的資料
  折疊相加（datawrap），比 L 長時補零。功率＝|X|²/(Σw)²、功率密度＝|X|²/(fs·Σw²)；平均＝所有段的平均（pwelch 'mean'），
  最大／最小值保持＝每個頻率在所有段裡的最大／最小值（pwelch 'maxhold'／'minhold'）。
- 單邊（只能用在實數）：取 0..fs/2，DC 與 Nyquist 以外 ×2。雙邊顯示用 MATLAB 的置中方式：NFFT 為偶數時頻率是
  −(N/2−1)..N/2 個 bin（Nyquist 放在正的那一端），奇數時 −(N−1)/2..(N−1)/2。
- 頻譜圖：每一段一條線（MATLAB spectrogram），時間＝段的中點；power 與 psd 的縮放和上面一樣。
  重新指派（reassigned）照 spectrogram 的作法：時間導數視窗用三次樣條（not-a-knot）微分、頻率導數視窗＝視窗×置中時間；
  每個點的能量搬到最接近的 (時間, 頻率) 格子；power 型態重新指派時的正規化是 NFFT·Σw²（和 MATLAB 一樣）。
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

WINDOWS = ("blackman-harris", "chebyshev", "flat-top", "hamming", "hann", "kaiser", "rectangular")   # spectrumAnalyzer 的 Window 值
WINDOW_TEXT = {"blackman-harris": "Blackman-Harris", "chebyshev": "Chebyshev", "flat-top": "Flat Top", "hamming": "Hamming",
               "hann": "Hann", "kaiser": "Kaiser", "rectangular": "Rectangular"}
OLD_WINDOW_NAMES = {"rect": "rectangular", "blackman": "blackman-harris"}   # 0.9.x 以前的設定值
ATTEN_WINDOWS = ("chebyshev", "kaiser")        # 用得到 Attenuation (dB) 的視窗
DEFAULT_ATTEN = 60.0                           # SidelobeAttenuation 預設（≥ 45）
MIN_ATTEN = 45.0
AUTO_INTERVALS = 1024                          # RBW Auto：頻寬裡放 1024 個 RBW
DEFAULT_WINDOW_LENGTH = 1024                   # WindowLength 預設
MIN_AUTO_NFFT = 1024                           # FFT 長度 Auto＝max(1024, 視窗長度)：2026-10-24 實際開分析器量到（視窗 1000 → FFT 1024；4000 → 4000），和 MATLAB 頻譜估計的 FFT 長度規則一致

_COSINE = {"hann": (0.5, 0.5), "hamming": (0.54, 0.46),
           "blackman-harris": (0.35875, 0.48829, 0.14128, 0.01168),
           "flat-top": (0.21557895, 0.41663158, 0.277263158, 0.083578947, 0.006947368)}


def window_name(name: Optional[str]) -> str:
    """設定檔裡的視窗名稱 → WINDOWS 裡的值（舊名稱 rect／blackman 也認得；不認得的當 hann）。"""
    n = str(name or "hann").strip().lower()
    n = OLD_WINDOW_NAMES.get(n, n)
    return n if n in WINDOWS else "hann"


def kaiser_beta(atten: float) -> float:
    """旁波瓣衰減（dB）→ Kaiser 視窗的 β。"""
    a = float(atten)
    if a > 50:
        return 0.1102 * (a - 8.7)
    if a < 21:
        return 0.0
    return 0.5842 * (a - 21) ** 0.4 + 0.07886 * (a - 21)


def _chebwin(L: int, atten: float) -> np.ndarray:
    """Dolph-Chebyshev 視窗（對稱、最大值 1）：在頻域取 L−1 階 Chebyshev 多項式的值，反 DFT 回時域。"""
    if L == 1:
        return np.ones(1)
    order = L - 1
    x0 = math.cosh(math.acosh(10.0 ** (abs(atten) / 20.0)) / order)
    x = x0 * np.cos(np.pi * np.arange(L) / L)
    p = np.empty(L)
    big = np.abs(x) > 1
    p[~big] = np.cos(order * np.arccos(x[~big]))
    xb = x[big]
    p[big] = np.cosh(order * np.arccosh(np.abs(xb))) * np.where(xb < 0, (-1.0) ** order, 1.0)
    if L % 2:
        w = np.real(np.fft.fft(p))
        h = (L + 1) // 2
        w = np.concatenate([w[h - 1:0:-1], w[:h]])
    else:
        w = np.real(np.fft.fft(p * np.exp(1j * np.pi / L * np.arange(L))))
        h = L // 2 + 1
        w = np.concatenate([w[h - 1:0:-1], w[1:h]])
    return w / np.max(w)


def design_window(name: str, L: int, atten: float = DEFAULT_ATTEN) -> np.ndarray:
    """長度 L 的視窗（periodic 的 generalized cosine、對稱的 Chebyshev／Kaiser、矩形）。"""
    L = int(L)
    if L < 1:
        return np.zeros(0)
    name = window_name(name)
    if name == "rectangular" or L == 1:
        return np.ones(L)
    if name == "chebyshev":
        return _chebwin(L, atten)
    if name == "kaiser":
        return np.kaiser(L, kaiser_beta(atten))
    ph = 2.0 * np.pi * np.arange(L) / L
    w = np.zeros(L)
    for k, a in enumerate(_COSINE[name]):
        w += (-1.0) ** k * a * np.cos(k * ph)
    return w


def nenbw(w) -> float:
    """等效雜訊頻寬（bins）＝ L·Σw² / (Σw)²：矩形 1、Hann 1.5。"""
    w = np.asarray(w, dtype=float)
    s = float(np.sum(w))
    return float(w.size * np.sum(w * w) / (s * s)) if s else math.inf


def auto_rbw(fs: float, two_sided: bool) -> float:
    """RBW Auto：頻寬（雙邊 fs、單邊 fs/2）裡放 1024 個 RBW。"""
    return (fs if two_sided else fs / 2.0) / AUTO_INTERVALS


def _nenbw_of(name: str, atten: float, L: int) -> float:
    return 1.0 if window_name(name) == "rectangular" else nenbw(design_window(name, L, atten))


def window_ok(name: str, atten: float, L: int = 1000) -> bool:
    """這個視窗與衰減做得出有限的視窗嗎（L 點）？Chebyshev 的 10^(衰減/20) 超過約 6165 dB 就超過浮點數上限（丟 OverflowError），
    約 6139 dB（L＝1000；L 越長越低一點，L ≥ 65536 時約 6138.6 dB）以上 FFT 的和溢位、視窗變 NaN；Kaiser 的 I0(β) 在約 6450 dB 以上溢位，
    視窗整條 NaN（這麼大的衰減 MATLAB 的 chebwin／kaiser 怎麼算沒有實測）。"""
    try:
        with np.errstate(all="ignore"):
            w = design_window(name, L, atten)
    except (OverflowError, ValueError, FloatingPointError):
        return False
    return bool(np.all(np.isfinite(w)))


def window_length_for_rbw(fs: float, rbw: float, name: str, atten: float = DEFAULT_ATTEN, max_len: Optional[int] = None) -> int:
    """給定 RBW 的視窗長度（DSP System Toolbox Spectrum Estimator 的反覆修正法）。max_len＝反覆修正時最多設計多長的視窗來算 NENBW：
    中間的 L 比它長時改用 max_len 點的 NENBW（Hann、Hamming 這些 periodic 視窗的 NENBW 和長度無關，Chebyshev／Kaiser 長了以後幾乎不變），
    結果只在那種時候是近似值——呼叫端用來在 L 遠大於資料點數時不必真的配置幾十億點的視窗（打 RBW 5u、時間解析度 1.5M 秒這種值時）。"""
    bins = fs / rbw
    cap = (lambda n: n) if max_len is None else (lambda n: min(n, max(1, int(max_len))))
    L = math.ceil(_nenbw_of(name, atten, cap(1000)) * bins)
    tried = [L]
    for _ in range(99):
        e = round(_nenbw_of(name, atten, cap(max(1, math.ceil(L)))) * 1e8) / 1e8
        Ln = math.ceil(e * bins)
        if Ln == L:
            break
        if Ln not in tried:
            tried.append(Ln)
            L = Ln
            continue
        L = min(tried, key=lambda n: abs(rbw - _nenbw_of(name, atten, cap(n)) * fs / n))
        break
    return max(1, int(L))


def overlap_samples(L: int, percent: float) -> int:
    """Overlap (%) → 重疊樣本數（最接近的整數，一樣近取小的；等於 L 時改成 L−1）。"""
    v = L * float(percent) / 100.0
    up, lo = math.ceil(v), math.floor(v)
    n = up if abs(up * 100.0 / L - percent) < abs(lo * 100.0 / L - percent) else lo
    return L - 1 if n >= L else max(0, int(n))


def num_segments(N: int, L: int, noverlap: int) -> int:
    return max(0, (int(N) - int(noverlap)) // (int(L) - int(noverlap))) if N >= L else 0


def _segments(x: np.ndarray, L: int, hop: int, K: int) -> np.ndarray:
    """K 段、每段 L 點（第 k 段從 k·hop 開始）的唯讀檢視（不複製）。"""
    st = x.strides[0]
    return np.lib.stride_tricks.as_strided(x, shape=(K, L), strides=(hop * st, st), writeable=False)


def _fft_rows(seg: np.ndarray, w: np.ndarray, nfft: int, detrend: bool, cplx: bool) -> np.ndarray:
    """每列加窗後做 nfft 點 FFT（nfft < L：先把加窗資料每 nfft 點折疊相加）。回傳複數 (K, nfft)。"""
    if detrend:
        seg = seg - seg.mean(axis=1, keepdims=True)
    y = seg * w
    L = y.shape[1]
    if nfft < L:
        nb = -(-L // nfft)
        pad = nb * nfft - L
        if pad:
            y = np.concatenate([y, np.zeros((y.shape[0], pad), dtype=y.dtype)], axis=1)
        y = y.reshape(y.shape[0], nb, nfft).sum(axis=1)
    return np.fft.fft(y, n=nfft, axis=1)


def freq_grid(nfft: int, fs: float, mode: str) -> np.ndarray:
    """頻率軸：onesided 0..fs/2；twosided 0..fs(1−1/N)；centered 用 MATLAB 的置中（偶數 N 時 Nyquist 在正的那一端）。"""
    df = fs / nfft
    if mode == "onesided":
        return np.arange(nfft // 2 + 1) * df
    if mode == "centered":
        lo = nfft // 2 - 1 if nfft % 2 == 0 else (nfft - 1) // 2
        return (np.arange(nfft) - lo) * df
    return np.arange(nfft) * df


def arrange(S: np.ndarray, nfft: int, mode: str) -> np.ndarray:
    """沿最後一軸把 0..N−1 的 bin 排成 onesided（取一半並 ×2）／centered／twosided。"""
    if mode == "onesided":
        h = nfft // 2 + 1
        out = S[..., :h].copy()
        hi = h - 1 if nfft % 2 == 0 else h
        out[..., 1:hi] *= 2.0
        return out
    if mode == "centered":
        return np.roll(S, nfft // 2 - 1 if nfft % 2 == 0 else (nfft - 1) // 2, axis=-1)
    return S


def welch(x, fs: float, w, noverlap: int, nfft: Optional[int] = None, mode: str = "onesided",
          detrend: bool = False, block: int = 1 << 22) -> Dict[str, Any]:
    """Welch 平均＋最大／最小值保持。回傳 dict：f、power、psd、max_power、min_power、max_psd、min_psd、nseg、L、nfft、
    nenbw、rbw（和 fs 同單位）；資料不夠一段時 nseg＝0、陣列都是空的。"""
    x = np.asarray(x)
    cplx = np.iscomplexobj(x)
    x = np.ascontiguousarray(x, dtype=complex if cplx else float)
    w = np.asarray(w, dtype=float)
    L = int(w.size)
    nfft = int(nfft or L)
    noverlap = int(noverlap)
    hop = L - noverlap
    K = num_segments(x.size, L, noverlap)
    e = nenbw(w)
    res: Dict[str, Any] = {"nseg": K, "L": L, "nfft": nfft, "nenbw": e, "rbw": e * fs / L, "hop": hop}
    if K == 0 or hop <= 0:
        z = np.zeros(0)
        res.update(f=z, power=z, psd=z, max_power=z, min_power=z, max_psd=z, min_psd=z, nseg=0)
        return res
    if mode == "onesided" and cplx:
        mode = "centered"
    acc = np.zeros(nfft)
    mx = np.full(nfft, -np.inf)
    mn = np.full(nfft, np.inf)
    rows = max(1, block // max(nfft, L))
    for k0 in range(0, K, rows):
        k1 = min(K, k0 + rows)
        seg = _segments(x[k0 * hop:], L, hop, k1 - k0)
        S = np.abs(_fft_rows(seg, w, nfft, detrend, cplx)) ** 2
        acc += S.sum(axis=0)
        np.maximum(mx, S.max(axis=0), out=mx)
        np.minimum(mn, S.min(axis=0), out=mn)
    s1 = float(np.sum(w)) ** 2
    s2 = float(np.sum(w * w)) * fs
    res["f"] = freq_grid(nfft, fs, mode)
    for key, S in (("", acc / K), ("max_", mx), ("min_", mn)):
        A = arrange(S, nfft, mode)
        res[key + "power"] = A / s1
        res[key + "psd"] = A / s2
    res["mode"] = mode
    return res


def _spline_slopes(y: np.ndarray) -> np.ndarray:
    """等間距（間距 1）三次樣條在節點的一階導數，端點用 not-a-knot（MATLAB spline 的預設）。"""
    n = y.size
    if n < 2:
        return np.zeros(n)
    d = np.diff(y)
    if n == 2:
        return np.array([d[0], d[0]])
    if n == 3:                                   # 三點的 not-a-knot 樣條就是拋物線
        return np.array([(-3 * y[0] + 4 * y[1] - y[2]) / 2, (y[2] - y[0]) / 2, (y[0] - 4 * y[1] + 3 * y[2]) / 2])
    a = np.ones(n)                               # 下對角（a[i] 乘 s[i−1]）
    b = np.full(n, 4.0)
    c = np.ones(n)                               # 上對角（c[i] 乘 s[i+1]）
    r = np.empty(n)
    r[1:-1] = 3.0 * (y[2:] - y[:-2])
    b[0], c[0], r[0] = 1.0, 2.0, (5.0 * d[0] + d[1]) / 2.0
    a[-1], b[-1], r[-1] = 2.0, 1.0, (d[-2] + 5.0 * d[-1]) / 2.0
    for i in range(1, n):                        # Thomas 演算法
        m = a[i] / b[i - 1]
        b[i] -= m * c[i - 1]
        r[i] -= m * r[i - 1]
    s = np.empty(n)
    s[-1] = r[-1] / b[-1]
    for i in range(n - 2, -1, -1):
        s[i] = (r[i] - c[i] * s[i + 1]) / b[i]
    return s


def spectrogram(x, fs: float, w, noverlap: int, nfft: Optional[int] = None, mode: str = "onesided",
                kind: str = "power", detrend: bool = False, reassign: bool = False) -> Dict[str, Any]:
    """頻譜圖：每段一條線。回傳 dict：f（nf）、t（K，段中點，從第 0 個樣本起算的秒數）、P（nf × K）、nseg、L、nfft、rbw；
    reassign＝True 時另有 fc、tc（每個點的能量重心）且 P 是重新指派後的結果。"""
    x = np.asarray(x)
    cplx = np.iscomplexobj(x)
    x = np.ascontiguousarray(x, dtype=complex if cplx else float)
    w = np.asarray(w, dtype=float)
    L = int(w.size)
    nfft = int(nfft or L)
    noverlap = int(noverlap)
    hop = L - noverlap
    K = num_segments(x.size, L, noverlap)
    e = nenbw(w)
    res: Dict[str, Any] = {"nseg": K, "L": L, "nfft": nfft, "nenbw": e, "rbw": e * fs / L, "hop": hop}
    if mode == "onesided" and cplx:
        mode = "centered"
    res["mode"] = mode
    if K == 0 or hop <= 0:
        res.update(f=np.zeros(0), t=np.zeros(0), P=np.zeros((0, 0)), nseg=0)
        return res
    seg = _segments(x, L, hop, K)
    Y = _fft_rows(seg, w, nfft, detrend, cplx)            # (K, nfft)
    t = (np.arange(K) * hop + L / 2.0) / fs
    fz = np.arange(nfft) * fs / nfft                      # 0..fs 的 bin 頻率
    if kind == "power":
        U = nfft * float(w @ w) if reassign else float(np.sum(w)) ** 2
    else:
        U = float(w @ w)
    S = (Y.real ** 2 + Y.imag ** 2) / U
    if reassign:
        with np.errstate(divide="ignore", invalid="ignore"):
            Yd = _fft_rows(seg, _spline_slopes(w) * (fs / (2 * np.pi)), nfft, detrend, cplx)
            fc = -np.imag(Yd / Y)
            Yt = _fft_rows(seg, w * ((1 - L) / 2.0 + np.arange(L)) / fs, nfft, detrend, cplx)
            tc = np.real(Yt / Y)
        fc[~np.isfinite(fc)] = 0.0
        tc[~np.isfinite(tc)] = 0.0
        fc = fc + fz
        tc = tc + t[:, None]
        if mode == "onesided":
            h = nfft // 2 + 1
            S, fc, tc, fz = S[:, :h], fc[:, :h], tc[:, :h], fz[:h]
            fc = np.mod(fc, fs)
            nf = h
            row = 1 + np.round((fc - fz[0]) * (nf - 1) / (fz[-1] - fz[0]))
        else:
            fc = np.mod(fc + fs / 2, fs) - fs / 2 if mode == "centered" else np.mod(fc, fs)
            nf = nfft
            row = 1 + np.mod(np.round((fc - fz[0]) * (nf - 1) / (fz[-1] - fz[0])), nf)
        col = 1 + np.round((tc - t[0]) * (K - 1) / (t[-1] - t[0])) if K > 1 else np.ones_like(tc)
        ok = (row >= 1) & (row <= nf) & (col >= 1) & (col <= K)
        R = np.zeros((K, nf))
        np.add.at(R, ((col[ok] - 1).astype(int), (row[ok] - 1).astype(int)), S[ok])
        S = R
        if mode == "onesided":
            hi = nf - 1 if nfft % 2 == 0 else nf
            S[:, 1:hi] *= 2.0
        elif mode == "centered":
            sh = nfft // 2 - 1 if nfft % 2 == 0 else (nfft - 1) // 2
            S = np.roll(S, sh, axis=1)
            fc = np.roll(fc, sh, axis=1)
            tc = np.roll(tc, sh, axis=1)
        res["fc"], res["tc"] = fc.T, tc.T
    else:
        S = arrange(S, nfft, mode)
    if kind == "psd":
        S = S / fs
    res["f"] = freq_grid(nfft, fs, mode)
    res["t"] = t
    res["P"] = S.T
    return res


def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/spectrum_ref.json；tools/matlab_ref/spectrum_ref.m 產生）。"""
    import json
    import os
    path = os.path.join(ref_dir, "spectrum_ref.json")
    if not os.path.isfile(path):
        check(True, "（沒有 tests/matlab_ref/spectrum_ref.json：略過 MATLAB 頻譜比對）")
        return
    R = json.load(open(path, encoding="utf-8"))
    xr = np.loadtxt(os.path.join(ref_dir, "spec_real.txt"))
    m = np.loadtxt(os.path.join(ref_dir, "spec_cplx.txt"))
    xc = m[:, 0] + 1j * m[:, 1]
    fs, fs2 = 1000.0, 2e6

    def arr(v):
        return np.asarray(v, dtype=float)

    def close(a, b, rtol=1e-9, atol=0.0):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        return a.shape == b.shape and np.allclose(a, b, rtol=rtol, atol=atol)

    names = {"rect": ("rectangular", None), "hann": ("hann", None), "hamming": ("hamming", None), "flattop": ("flat-top", None),
             "bh": ("blackman-harris", None), "cheb45": ("chebyshev", 45), "cheb60": ("chebyshev", 60), "cheb100": ("chebyshev", 100),
             "kaiser45": ("kaiser", 45), "kaiser60": ("kaiser", 60), "kaiser100": ("kaiser", 100)}
    bad = []
    for Lk, d in R["windows"].items():
        L = int(Lk[1:])
        for k, ref in d.items():
            nm, at = names[k]
            if not close(design_window(nm, L, at or DEFAULT_ATTEN), arr(ref), rtol=1e-12, atol=1e-13):
                bad.append(f"{k}@{L}")
    check(not bad, "視窗 vs MATLAB（hann／hamming／flattopwin／blackmanharris periodic、chebwin 45/60/100 dB、kaiser β(衰減)，L＝8/9/64）逐點一致"
          + (f"（不一致：{bad}）" if bad else ""))
    enb = {"rect": ("rectangular", 60), "hann": ("hann", 60), "hamming": ("hamming", 60), "flattop": ("flat-top", 60),
           "bh": ("blackman-harris", 60), "cheb60": ("chebyshev", 60), "kaiser60": ("kaiser", 60), "kaiser100": ("kaiser", 100)}
    bad = [f"{k}@{Lk}" for Lk, d in R["enbw"].items() for k, v in d.items()
           if not math.isclose(nenbw(design_window(enb[k][0], int(Lk[1:]), enb[k][1])), v, rel_tol=1e-9)]
    kb = R["kaiser_beta"]
    okb = all(math.isclose(kaiser_beta(float(k[1:])), v, rel_tol=1e-15, abs_tol=1e-15) for k, v in kb.items())
    check(not bad and okb, "NENBW vs MATLAB enbw（8 種視窗、L＝1000/1001）與 Kaiser β（衰減 20/21/30/50/51/60/100 dB）一致"
          + (f"（不一致：{bad}）" if bad or not okb else ""))
    P = R["pwelch"]
    hann256 = design_window("hann", 256)
    a = welch(xr, fs, hann256, 0, 256, "onesided")
    ok = (close(a["f"], arr(P["a_mean"]["f"])) and close(a["power"], arr(P["a_mean"]["p"])) and close(a["max_power"], arr(P["a_max"]))
          and close(a["min_power"], arr(P["a_min"])) and close(a["psd"], arr(P["a_psd"]["p"])) and a["nseg"] == 19)
    check(ok, f"Welch vs MATLAB pwelch（Hann 256、不重疊、單邊）：平均、max-hold、min-hold、power 與 psd 一致（{a['nseg']} 段）")
    b = welch(xr, fs, hann256, 128, 512, "centered")
    b2 = welch(xr, fs, hann256, 128, 512, "twosided")
    check(close(b["f"], arr(P["b"]["f"])) and close(b["power"], arr(P["b"]["p"])) and close(b2["f"], arr(P["b2"]["f"]))
          and close(b2["power"], arr(P["b2"]["p"])),
          "Welch vs pwelch（重疊 50%、NFFT 512 補零、置中／雙邊）：頻率軸（偶數 NFFT 的 Nyquist 在正端）與功率一致")
    c = welch(xc, fs2, design_window("kaiser", 300, 60), overlap_samples(300, 33), 128, "centered")
    d = welch(xc, fs2, design_window("chebyshev", 200, 80), 0, 200, "centered")
    ok = (close(c["f"], arr(P["c"]["f"])) and close(c["psd"], arr(P["c"]["p"])) and overlap_samples(300, 33) == 99
          and close(d["f"], arr(P["d"]["f"])) and close(d["power"], arr(P["d"]["p"])) and close(d["max_power"], arr(P["d_max"]))
          and close(d["min_power"], arr(P["d_min"])))
    check(ok, "Welch vs pwelch（複數 I/Q：Kaiser 300 點、重疊 33%→99 點、NFFT 128＜L 折疊；Chebyshev 80 dB 的 max／min-hold）一致")
    e = welch(xr, fs, design_window("flat-top", 511), 255, 511, "onesided")
    ec = welch(xr, fs, design_window("flat-top", 511), 255, 511, "centered")
    fb = welch(xr, fs, design_window("blackman-harris", 1000), 0, 1000, "onesided")
    fr = welch(xr, fs, np.ones(100), 50, 100, "onesided")
    g = welch(xr, fs, hann256, 0, 100, "onesided")
    ok = (close(e["f"], arr(P["e"]["f"])) and close(e["power"], arr(P["e"]["p"])) and close(ec["f"], arr(P["e_c"]["f"]))
          and close(ec["power"], arr(P["e_c"]["p"])) and close(fb["power"], arr(P["f_bh"]["p"])) and close(fr["psd"], arr(P["f_rect"]["p"]))
          and close(g["f"], arr(P["g_wrap"]["f"])) and close(g["power"], arr(P["g_wrap"]["p"])))
    check(ok, "Welch vs pwelch（Flat Top 511 奇數長度單邊／置中、Blackman-Harris 1000、矩形重疊 50% 的 psd、NFFT 100＜L 256 折疊）一致")
    S = R["spectrogram"]
    sg = spectrogram(xr, fs, design_window("hann", 128), 64, 128, "onesided", "power")
    sp = spectrogram(xr, fs, design_window("hann", 128), 64, 128, "onesided", "psd")
    sh = spectrogram(xc, fs2, design_window("kaiser", 100, 60), 50, 256, "centered", "psd")
    s2 = spectrogram(xr, fs, design_window("hann", 120), 0, 120, "centered", "power")
    ok = (close(sg["f"], arr(S["g"]["f"])) and close(sg["t"], arr(S["g"]["t"])) and close(sg["P"], arr(S["g"]["ps"]))
          and close(sp["P"], arr(S["g_psd"]["ps"])) and close(sh["f"], arr(S["h"]["f"])) and close(sh["t"], arr(S["h"]["t"]))
          and close(sh["P"], arr(S["h"]["ps"])) and close(s2["f"], arr(S["h2"]["f"])) and close(s2["P"], arr(S["h2"]["ps"])))
    check(ok, f"頻譜圖 vs MATLAB spectrogram（Hann 128 重疊 64 的 power／psd 單邊、複數 Kaiser 置中 psd、Hann 120 置中 power）："
              f"頻率、時間（段中點）與每一格一致（{sg['nseg']} 條線）")
    r = spectrogram(xr[:1000], fs, design_window("hann", 128), 96, 128, "onesided", "power", reassign=True)
    rc = spectrogram(xc[:1024], fs2, design_window("kaiser", 64, 60), 48, 64, "centered", "psd", reassign=True)
    ok = (close(r["P"], arr(S["r"]["ps"]), rtol=1e-7, atol=1e-15) and close(r["fc"], arr(S["r"]["fc"]), rtol=1e-7, atol=1e-6)
          and close(r["tc"], arr(S["r"]["tc"]), rtol=1e-7, atol=1e-9)
          and close(rc["P"], arr(S["rc"]["ps"]), rtol=1e-7, atol=1e-18) and close(rc["fc"], arr(S["rc"]["fc"]), rtol=1e-7, atol=1e-3)
          and close(rc["tc"], arr(S["rc"]["tc"]), rtol=1e-7, atol=1e-12))
    check(ok, "重新指派頻譜圖 vs MATLAB spectrogram(…,'reassigned')（實數單邊 power、複數置中 psd）：能量重心 fc／tc 與重新指派後的每一格一致")
    from dsv_measure import find_peaks
    db = 10 * np.log10(a["power"])
    v, i = find_peaks(db, num=3)
    v2, i2 = find_peaks(db, num=5, min_height=-60, min_dist=5, threshold=0.5)
    ok = (close(v, arr(R["peaks"]["v"])) and np.array_equal(i, arr(R["peaks"]["l"]).astype(int) - 1)
          and close(v2, arr(R["peaks2"]["v"])) and np.array_equal(i2, arr(R["peaks2"]["l"]).astype(int) - 1))
    check(ok, f"頻譜峰值 vs MATLAB findpeaks（dB 頻譜；預設 3 個、MinPeakHeight／MinPeakDistance／Threshold）一致：{np.round(v, 2).tolist()} dB")
    # RBW → 視窗長度（反覆修正、無條件進位）：結果是 RBW 不超過要求值的最短視窗；Hann 的 NENBW 剛好 1.5 → L＝1.5·fs/RBW
    L1 = window_length_for_rbw(1000.0, auto_rbw(1000.0, True), "hann")
    L2 = window_length_for_rbw(1000.0, auto_rbw(1000.0, False), "hann")
    L3 = window_length_for_rbw(1e6, 1e3, "rectangular")
    L4 = window_length_for_rbw(32e6, 31.25e3, "kaiser", 60)
    e4 = nenbw(design_window("kaiser", L4, 60)) * 32e6 / L4
    near = e4 <= 31.25e3 < nenbw(design_window("kaiser", L4 - 1, 60)) * 32e6 / (L4 - 1)
    check(L1 == 1536 and L2 == 3072 and L3 == 1000 and near and overlap_samples(1536, 50) == 768 and overlap_samples(10, 99.9) == 9
          and overlap_samples(3, 50) == 1,
          f"RBW → 視窗長度：Hann 雙邊 Auto（fs/1024）→ {L1}、單邊 → {L2}、矩形 RBW＝fs/1000 → {L3}、Kaiser 60 dB → {L4}（RBW {e4:.1f} Hz ≤ 31.25 kHz，"
          f"少一點就超過）；Overlap 50%→768、99.9%→L−1、1.5 點一樣近取小的")
