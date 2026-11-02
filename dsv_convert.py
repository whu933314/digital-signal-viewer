# -*- coding: utf-8 -*-
"""轉換（MATLAB Signal Analyzer 的 PREPROCESS › FUNCTIONS › CONVERT：Resample／Envelope）——純 numpy，和 GUI 分開。

依據（MATLAB R2025a；程式是自己寫的，tests/matlab_ref/resample_envelope/ 是 MATLAB 算出的數值，selftest() 逐筆比對）：
- 行為照 MATLAB Signal Analyzer 的實測輸出對照（Resample 與 Envelope 兩個動作）：
  重取樣的結果一律等同呼叫時間向量形式 [y,ty] = resample(x,tx,targetFs[,P,Q][,method])，均勻訊號也是；
  包絡等同呼叫 envelope(x)（Hilbert）、envelope(x,N,'analytic')（FIR）、envelope(x,N,'rms')、envelope(x,N,'peak')，上包絡取第 1 個輸出、下包絡第 2 個。
- 均勻訊號：targetFs ＝ 使用者輸入的 Sample Rate 或 Sample Factor × 目前 fs；內插法與臨界頻率被忽略；Sample Rate 選 Auto 時不處理
  （UnchangedUniformSignal）；targetFs/fs > 10000 → SignalLengthViolation；輸出長度 < 2 → InvalidResampledSignal。
- 非均勻訊號：Auto 的 targetFs ＝ 1/median(diff(t))（17 位有效數字和 app 一致）；內插法 linear／pchip／spline 傳給 resample；
  臨界頻率 cf 有填時 [P,Q] = rat(targetFs/cf, 0.01)（絕對容差 0.01，和 15 組 Signal Analyzer 實測輸出比對確認），P 算出 0 時 resample 直接丟
  「Expected P to be positive.」。
- resample(x,tx,fs[,p,q][,method])（MATLAB 的 resample）：
  1. 時間是 NaN 的樣本丟掉、依時間排序（穩定排序）；時間含 Inf → 錯誤；剩不到 2 點 → 錯誤。
  2. p、q：有給就用 rat(p/q, 1e-12) 約分；沒給就用平均取樣間隔 Δ = (t_end − t_1)/(N − 1)、[p,q] = rat(Δ·fs, 0.01)，p < 2 時改成
     p = 1、q = round(1/(Δ·fs))。
  3. 格點：步長 p/(q·fs)，用 MATLAB 的冒號運算 t_1 : 步長 : t_end 產生（見下方「未定」）。
  4. 把資料內插到格點：先丟掉 x 是 NaN 的樣本，時間相同的一串樣本合併成一個（x 取平均），再 interp1(…, method, 'extrap')。
  5. p = q = 1 → 輸出就是內插結果、濾波器 b = 1。否則設計抗混疊 FIR：K = max(p,q)、長度 L = 2·10·K + 1、截止 fc = 1/(2K)；
     firls(L−1, [0 2fc 2fc 1], [1 1 0 0]) 在零寬過渡帶時就是截斷的理想低通 h0[m] = sinc((m − (L−1)/2)/K)/K（MATLAB 比對差 0），
     乘上 kaiser(L, 5)，再正規化成 h = p·h/Σh；b 就是這個 h。
  6. 延遲與補零：半長 H = (L−1)/2，前面補 z = floor(q − mod(H, q)) 個零，delay = floor(ceil(H + z)/q)；
     後面補最少的零使 ceil(((Lx−1)p + 補零後長度)/q) − delay ≥ ceil(Lx·p/q)（Lx ＝ 格點數）。
  7. upfirdn：插 p−1 個零升取樣、和補零後的濾波器做完整卷積、從第 0 點起每 q 點取一點；輸出 y 取第 delay 點起共 ny = ceil(Lx·p/q) 點。
     這裡用多相實作：輸出第 m 點對應升取樣後的索引 n = m·q，只有 h 的第 r = n mod p 相（h[r::p]）會碰到它，所以每一相和 x 做一次短卷積，
     再用模運算（m·q ≡ r (mod p) 的解是等差數列 m0 + k·p/gcd(p,q)）以切片直接放到輸出，總成本 O(Ly + Lx·Lh)，不隨 p 平方成長。
  8. 輸出時間 ty = t_1 + (0:ny−1)/fs。
  resample(x,p,q) 用同一組濾波器、延遲、補零（Lx ＝ numel(x)），不內插。
- MATLAB rat(X, tol)：連分數用 round() 取整：C = [1 0; 0 1]，反覆 d = round(x)、x = x − d、
  C = [C·[d;1], C(:,1)]，直到 x = 0 或 |C11/C21 − X| ≤ max(tol, eps(X))，否則 x = 1/x；N = C11/sign(C21)、D = |C21|。
  預設 tol = 1e-6·|X|。容差是絕對值，所以 rat(8e-5, 0.01) = 0/1。
- interp1：linear 用相鄰兩點的直線（兩端外延同一條線）；pchip 用 Fritsch–Carlson 保形斜率（MATLAB「pchip」文件頁的
  Algorithms 一節、Fritsch & Carlson 1980、Moler《Numerical Computing with MATLAB》§3.4）：相鄰割線同號時節點斜率是兩條割線的
  加權調和平均，權重 2h₊+h₋（配左割線）與 h₊+2h₋（配右割線）；異號或有零時斜率 0；端點用最靠近的三個節點配拋物線取端點導數，
  和鄰近割線異號時設 0、相鄰兩割線異號且超過 3 倍鄰近割線時截到 3 倍。spline 用 not-a-knot 三次樣條（MATLAB「spline」文件：
  第三階導數在第 2 與第 n−1 個節點連續；2 點退化成直線、3 點是通過三點的拋物線）。兩者都用端點那段多項式外延。
- envelope(x[,n[,method]])（MATLAB 的 envelope）：
  - Hilbert／FIR／RMS 先扣掉平均 m，算出振幅 A 後 upper = m + A、lower = m − A。
  - Hilbert：A = |hilbert(xc)|；MATLAB 的 hilbert 用 FFT 做解析訊號：X = fft(xc)，乘上 h（h[0] = 1，偶數 N 時 h[1..N/2−1] = 2、h[N/2] = 1，
    奇數 N 時 h[1..(N−1)/2] = 2，其餘 0），再 ifft。
  - FIR（'analytic'，n 個 tap）：tt = k/2、k = (1−n)/2 … (n−1)/2，g = sinc(tt)·exp(iπ·tt)·kaiser(n, 8)，g = g/Σ real(g)；
    A = |conv(xc, g, 'same')|（取完整卷積從第 floor(n/2) 點起的 N 點）。
  - RMS（n 點）：A = sqrt(滑動平均(xc²))；n 奇數置中，偶數時視窗是「往前 n/2−1、往後 n/2」（MATLAB movrms 的慣例，
    和 movmean(x², [n/2−1 n/2]) 比對差 2e-16），兩端視窗縮短（shrink）。
  - Peak（n）：不扣平均。nx > n+1 時 findpeaks(x, 'MinPeakDistance', n) 找局部極大（平頂取第一點、端點不算；從最高的開始，
    距離 ≤ n 的較矮峰丟掉）；峰少於 2 個時節點 = [第 1 點; 峰; 第 nx 點]，否則就是那些峰；把 x 在節點的值用 not-a-knot 樣條
    （含外延）連成 upper。lower 對 −x 找峰，再用 x 在那些位置的值連樣條。nx < 2 時直接回傳 x。
  - 時間單位的視窗長度 → 樣本數：N = round(秒 × fs)（Signal Analyzer 實測 fs = 100：0.055 s → 6、0.054 s → 5、0.0249 s → 2）；N 為 0 時
    envelope 丟錯、訊號不處理。
- 未定／自行決定：
  - MATLAB 冒號運算 a:d:b 是 builtin：點數用容差 floor((b−a)/d + 3·eps·|(b−a)/d|) + 1（參考資料裡 (b−a)/d = 118.99999999999999
    得到 120 點）；前半（k < n//2）正向 a + k·d、後半從 a + (n−1)·d 往回減（p = q = 1 的參考案例 120 點裡 104 點和 MATLAB
    位元相同、其餘差 8e-16；只正向算只有 83 點相同），n 為奇數時中間那點歸後半（無法從資料判定）。超過 b 時最後一點截成 b。
  - 非均勻訊號的取樣率比上限不明（10002 倍仍能跑），所以 10000 的限制只套用在均勻訊號；臨界頻率相關的上限錯誤在實測中從未出現，不實作。
  - P 算出 0 時照 MATLAB 丟「Expected P to be positive.」（識別碼 MATLAB:resample:expectedPositive），不另造訊息。
  - envelope N = 0 的訊息「Expected input number 2, N, to be positive.」是 validateattributes 給了引數位置時的標準格式，參考資料
    只記到「有丟錯」，文字本身未經 MATLAB 驗證。
  - RMS 的滑動和：n ≤ 512 用直接卷積（和的誤差只和 n 有關），更長用累積和相減。
  - 時間戳記全部相同（平均間隔 Δ = 0）：照上面第 2 點的公式會得到 q = round(1/0) = Inf、格點步長 0、空格點，合併重複時間後
    只剩 1 點，屬於 signal:resample:TimeVectorSize 的情況；MATLAB 在這種輸入下先丟哪個錯沒有實測，這裡直接丟 TimeVectorSize（不會變成 Python 的
    OverflowError）。
  - 2-D 輸入：MATLAB 把每一欄當一個通道，DSV 一次只處理一個通道，所以 resample／envelope 只接受向量（含 1×N、N×1），其餘丟
    DSV:expectedVector。envelope 輸入空向量時回傳空向量（MATLAB envelope([],3,'analytic') 也是空）。
  - app_resample 的 Sample Rate／Sample Factor／Critical Frequency 不是正數（含空字串、非數字）時照 Signal Analyzer 介面套用前的檢查丟
    ValueMustBePositive／CriticalFrequencyMustBePositive；app_envelope 以秒指定視窗卻沒給 fs、或 output 不是 upper／lower，是 DSV 端的
    呼叫錯誤，丟一般 ValueError（MATLAB 沒有對應訊息）。
  - UI 字串（上限／下限 vs 上包絡／下包絡）與 Peak 錯誤訊息用哪個單位欄（研究時判斷 MATLAB 這裡看起來有問題）屬於 GUI，這裡不處理。
- selftest 容差：預設 rtol = 1e-12、atol = 1e-15（實測 188 組 MATLAB 數值：y、b、upper 最大相對差 2.3e-13，來自 FFT／卷積的加法順序；
  只有 lower 包絡裡兩個 |值| ≈ 3e-4、3e-5 的樣本相對差 1.3e-12／1.9e-12、絕對差 ≤ 4.4e-16，atol 就是給它們的）；ty（t_1 + k/fs）、
  格點首尾與步長、整數參數與 rat 結果要求位元相同。
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

from dsv_measure import find_peaks

EPS = float(np.finfo(float).eps)
INTERP_METHODS = ("linear", "pchip", "spline")                 # resample 的內插法（Signal Analyzer 的 Interpolation Method）
ENVELOPE_METHODS = ("hilbert", "fir", "rms", "peak")           # Signal Analyzer 的 Envelope › Method
RAT_TOL_CF = 0.01                                              # [P,Q] = rat(targetFs/cf, 0.01)
RAT_TOL_PQ = 1e-12                                             # 使用者給的 P、Q 的約分容差
MAX_RATE_RATIO = 10000.0                                       # 均勻訊號 targetFs/fs 的上限（SignalLengthViolation）
RESAMPLE_N, RESAMPLE_BETA = 10, 5.0                            # resample 預設的濾波器參數
FIR_ENVELOPE_BETA = 8.0                                        # envelope 'analytic' 的 Kaiser β
# Signal Analyzer 的單位清單（值 → 換成 Hz／秒 的倍率）
FREQ_UNIT_HZ = {"cyclesperyear": 1.0 / (3600 * 24 * 365), "cyclesperday": 1.0 / 86400, "cyclesperhour": 1.0 / 3600,
                "cyclesperminute": 1.0 / 60, "mHz": 1e-3, "Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12}
TIME_UNIT_S = {"samples": None, "ps": 1e-12, "ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0, "minutes": 60.0, "hours": 3600.0,
               "days": 86400.0, "years": 31536000.0}


class ConvertError(ValueError):
    """MATLAB／Signal Analyzer 的錯誤：ident（MATLAB 識別碼或 Signal Analyzer 對話框的訊息代碼）、en（MATLAB 英文訊息）、zh（繁體中文）。"""

    def __init__(self, ident: str, en: str, zh: str):
        super().__init__(en)
        self.ident, self.en, self.zh = ident, en, zh


# ident → (英文：MATLAB 顯示的訊息原文, 繁體中文)
MESSAGES: Dict[str, Tuple[str, str]] = {
    "MATLAB:resample:expectedPositive": ("Expected {name} to be positive.", "{name} 必須為正數。"),
    "MATLAB:resample:expectedInteger": ("Expected {name} to be integer-valued.", "{name} 必須為整數。"),
    "MATLAB:resample:expectedFinite": ("Expected {name} to be finite.", "{name} 必須為有限值。"),
    "signal:resample:TimeVectorSize": ("The vector of time instants must have at least two elements after all missing values have been removed.",
                                       "刪除所有缺失值後，時間向量至少要有兩個元素。"),
    "signal:resample:TimeVectorInf": ("The vector of time instants must not contain Inf.", "時間向量不能包含 Inf。"),
    "signal:resample:TimeVectorMismatch": ("The number of elements in Tx must match the number of elements in X when X is a vector.",
                                           "X 是向量時，Tx 的元素個數必須和 X 一樣。"),
    "signal:resample:NonUniformMissingQ": ("Sample rate, upsampling parameter P and downsampling parameter Q must be specified when the input is nonuniformly sampled.",
                                           "輸入為非均勻取樣時，必須同時指定取樣率、升取樣參數 P 與降取樣參數 Q。"),
    "signal:resample:MissingQ": ("Downsampling parameter Q must be specified along with upsampling parameter P.", "降取樣參數 Q 必須和升取樣參數 P 一起指定。"),
    "signal:resample:UnexpectedInterpolation": ("Interpolation method '{name}' is supported when time vector Tx is an input.",
                                                "內插法「{name}」只在有時間向量 Tx 時支援。"),
    "MATLAB:envelope:expectedPositive": ("Expected input number 2, N, to be positive.", "第 2 個輸入 N 必須為正數。"),
    "MATLAB:envelope:expectedInteger": ("Expected input number 2, N, to be integer-valued.", "第 2 個輸入 N 必須為整數。"),
    "MATLAB:envelope:expectedFinite": ("Expected input to be finite.", "輸入必須為有限值。"),
    "MATLAB:envelope:expectedReal": ("Expected input to be real.", "輸入必須為實數。"),
    "MATLAB:unrecognizedStringChoice": ("Expected {what} to match one of these values: {name}", "{what} 必須是這些值之一：{name}"),
    # DSV 自己的限制（MATLAB 把矩陣的每一欄當一個通道；DSV 一次處理一個通道）
    "DSV:expectedVector": ("Expected {name} to be a vector (one channel at a time).", "{name} 必須是向量（一次處理一個通道）。"),
    # Signal Analyzer 對話框的訊息代碼（對話框顯示的文字）
    "SignalLengthViolation": ("The ratio of desired sample rate to current sample rate exceeds limits. Specify a lower desired sample rate.",
                              "目標取樣率與目前取樣率的比率超過限制。請指定較低的目標取樣率。"),
    "InvalidResampledSignal": ("The desired sample rate results in a resampled signal of length one. Specify a higher desired sample rate.",
                               "目標取樣率會使重取樣後的訊號長度為 1。請指定較高的目標取樣率。"),
    "UnchangedUniformSignal": ("Uniformly sampled signals are not preprocessed when sample rate is auto computed.",
                               "自動計算取樣率時，不會前處理均勻取樣的訊號。"),
    "ValueMustBePositive": ("Value must be a positive scalar", "值必須為正純量"),
    "CriticalFrequencyMustBePositive": ("Critical frequency must be a positive scalar", "臨界頻率必須為正純量"),
    "envelopeComplexSignals": ("Unable to extract envelope of complex signals. Change signal table selection.", "無法提取複數訊號的包絡。請更改訊號表選擇。"),
}


def _err(ident: str, **fmt) -> ConvertError:
    en, zh = MESSAGES[ident]
    return ConvertError(ident, en.format(**fmt), zh.format(**fmt))


def matlab_round(v: float) -> float:
    """MATLAB round：四捨五入、.5 離開零。"""
    a = abs(float(v))
    f = math.floor(a)
    r = f + 1.0 if a - f >= 0.5 else float(f)
    return r if v >= 0 else -r


def matlab_rat(x: float, tol: Optional[float] = None) -> Tuple[int, int]:
    """MATLAB rat(X, tol) 的 [N, D]：round() 取整的連分數，停在 x 的小數部分變 0 或 |N/D − X| ≤ max(tol, eps(X))。tol 預設 1e-6·|X|。"""
    X = float(x)
    if not math.isfinite(X):
        return (0 if math.isnan(X) else int(math.copysign(1, X))), 0
    if tol is None:
        tol = 1e-6 * abs(X)
    limit = max(float(tol), float(np.spacing(abs(X))))
    n0, n1, d0, d1 = 1.0, 0.0, 0.0, 1.0            # 目前與前一個收斂分數的分子 n0、n1 和分母 d0、d1（起始值相當於單位矩陣）
    v = X
    while True:
        d = matlab_round(v)
        v = v - d
        n0, n1 = n0 * d + n1, n0
        d0, d1 = d0 * d + d1, d0
        if v == 0 or abs(n0 / d0 - X) <= limit:
            break
        v = 1.0 / v
    sgn = 1.0 if d0 > 0 else -1.0
    return int(n0 * sgn), int(abs(d0))


def matlab_colon(a: float, d: float, b: float) -> np.ndarray:
    """MATLAB 的 a:d:b（見模組說明「未定」：容差點數、前半正向後半從尾端往回、尾端截到 b）。"""
    a, d, b = float(a), float(d), float(b)
    if d == 0 or (d > 0 and a > b) or (d < 0 and a < b) or not all(map(math.isfinite, (a, d, b))):
        return np.zeros(0)
    r = (b - a) / d
    n = int(math.floor(r + 3.0 * EPS * abs(r))) + 1
    if n < 1:
        return np.zeros(0)
    last = a + (n - 1) * d
    if (d > 0 and last > b) or (d < 0 and last < b):
        last = b
    k = np.arange(n, dtype=float)
    half = n // 2
    out = np.empty(n)
    out[:half] = a + k[:half] * d
    out[half:] = last - (n - 1 - k[half:]) * d
    return out


def auto_fs(t) -> float:
    """非均勻訊號 Sample Rate 選 Auto 時的目標取樣率：1/median(diff(t))。"""
    t = np.asarray(t, dtype=float)
    return float(1.0 / np.median(np.diff(t)))


def critical_pq(fs: float, cf: float) -> Tuple[int, int]:
    """臨界頻率 cf → resample 的 [P,Q] = rat(fs/cf, 0.01)（cf ≳ 100·fs 時 P 會是 0，resample 會拒絕）。"""
    return matlab_rat(float(fs) / float(cf), RAT_TOL_CF)


def window_samples(seconds: float, fs: Optional[float]) -> int:
    """時間單位的視窗長度／峰值間隔 → 樣本數：round(秒 × fs)。fs 必須給（DSV：SPS × symbol rate）。"""
    if fs is None:
        raise ValueError("fs is required to convert a window length in seconds to samples（以秒指定視窗長度時必須給 fs）")
    return int(matlab_round(float(seconds) * float(fs)))


def _as_vector(x, name: str) -> np.ndarray:
    """接受 1-D、1×N、N×1（MATLAB 的 isvector），其餘丟 DSV:expectedVector；回傳 1-D 陣列（型別不變）。"""
    x = np.asarray(x)
    if x.ndim > 1 and not (x.ndim == 2 and min(x.shape) <= 1):
        raise _err("DSV:expectedVector", name=name)
    return x.reshape(-1)


# ---------------------------------------------------------------- interp1（linear／pchip／spline，含外延）
def _pchip_end_slope(h_near: float, h_far: float, sec_near: float, sec_far: float) -> float:
    """pchip 端點斜率（Fritsch–Carlson；Moler NCM §3.4）：最靠近端點的三個節點配一條拋物線、取它在端點的導數，
    再做保形限制——和鄰近割線 sec_near 反向就設 0；兩條割線反向而且導數超過 3·sec_near 就截在 3·sec_near。"""
    g = ((2.0 * h_near + h_far) * sec_near - h_near * sec_far) / (h_near + h_far)
    if np.sign(g) != np.sign(sec_near):
        return 0.0
    if np.sign(sec_near) != np.sign(sec_far) and abs(g) > 3.0 * abs(sec_near):
        return 3.0 * sec_near
    return float(g)


def _pchip_slopes(h: np.ndarray, sec: np.ndarray) -> np.ndarray:
    """保形分段三次（MATLAB pchip）的節點斜率。h：各段長度、sec：各段割線（Δx/h）。
    內部節點：左右割線同號時取兩條割線的加權調和平均（權重 2h₊+h₋ 配左割線、h₊+2h₋ 配右割線），否則（反向或有 0）斜率 0，
    這樣內插不會越過節點值（保形）。端點見 _pchip_end_slope。"""
    n = h.size + 1
    if n == 2:
        return np.array([sec[0], sec[0]])
    slope = np.zeros(n)
    left, right = sec[:-1], sec[1:]                              # 內部節點 1..n−2 的左、右割線
    h_left, h_right = h[:-1], h[1:]
    same = (np.sign(left) == np.sign(right)) & (left != 0)
    w_left = 2.0 * h_right[same] + h_left[same]
    w_right = h_right[same] + 2.0 * h_left[same]
    # 加權調和平均 (w_left + w_right) / (w_left/left + w_right/right)，寫成乘積形式避免兩次除法
    slope[1:-1][same] = (w_left + w_right) * left[same] * right[same] / (w_left * right[same] + w_right * left[same])
    slope[0] = _pchip_end_slope(h[0], h[1], sec[0], sec[1])
    slope[-1] = _pchip_end_slope(h[-1], h[-2], sec[-1], sec[-2])
    return slope


def _tridiag(a: np.ndarray, b: np.ndarray, c: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Thomas 演算法：a 下對角（乘 s[i−1]）、b 對角、c 上對角（乘 s[i+1]）。"""
    n = b.size
    bb, rr = b.tolist(), r.tolist()
    aa, cc = a.tolist(), c.tolist()
    for i in range(1, n):
        m = aa[i] / bb[i - 1]
        bb[i] -= m * cc[i - 1]
        rr[i] -= m * rr[i - 1]
    s = [0.0] * n
    s[-1] = rr[-1] / bb[-1]
    for i in range(n - 2, -1, -1):
        s[i] = (rr[i] - cc[i] * s[i + 1]) / bb[i]
    return np.asarray(s)


def _spline_slopes(t: np.ndarray, x: np.ndarray) -> np.ndarray:
    """not-a-knot 三次樣條（MATLAB spline 預設）的節點斜率，節點可不等距。2 點 → 直線；3 點 → 通過三點的拋物線。"""
    n = t.size
    h = np.diff(t)
    delta = np.diff(x) / h
    if n == 2:
        return np.array([delta[0], delta[0]])
    if n == 3:
        c = (delta[1] - delta[0]) / (t[2] - t[0])
        return np.array([delta[0] - c * h[0], delta[0] + c * h[0], delta[0] + c * (h[0] + 2.0 * h[1])])
    a = np.zeros(n)
    b = np.zeros(n)
    c = np.zeros(n)
    r = np.zeros(n)
    a[1:-1] = h[1:]
    b[1:-1] = 2.0 * (h[:-1] + h[1:])
    c[1:-1] = h[:-1]
    r[1:-1] = 3.0 * (h[1:] * delta[:-1] + h[:-1] * delta[1:])
    # 兩端：第三階導數在第 2／第 n−1 個節點連續（頭兩段、尾兩段各是同一條三次式），和內部式子消去後只剩相鄰兩個斜率
    b[0], c[0] = h[1], h[0] + h[1]
    r[0] = ((3.0 * h[0] + 2.0 * h[1]) * h[1] * delta[0] + h[0] ** 2 * delta[1]) / (h[0] + h[1])
    a[-1], b[-1] = h[-2] + h[-1], h[-2]
    r[-1] = (h[-1] ** 2 * delta[-2] + (3.0 * h[-1] + 2.0 * h[-2]) * h[-2] * delta[-1]) / (h[-2] + h[-1])
    return _tridiag(a, b, c, r)


def _hermite_eval(t: np.ndarray, x: np.ndarray, s: np.ndarray, tq: np.ndarray) -> np.ndarray:
    """分段三次 Hermite（節點值 x、斜率 s）在 tq 的值；tq 超出範圍用端點那段外延。"""
    i = np.clip(np.searchsorted(t, tq, side="right") - 1, 0, t.size - 2)
    h = t[i + 1] - t[i]
    u = tq - t[i]
    delta = (x[i + 1] - x[i]) / h
    c2 = (3.0 * delta - 2.0 * s[i] - s[i + 1]) / h
    c3 = (s[i] + s[i + 1] - 2.0 * delta) / (h * h)
    return ((c3 * u + c2) * u + s[i]) * u + x[i]


def interp1(t, x, tq, method: str = "linear") -> np.ndarray:
    """MATLAB interp1(t, x, tq, method, 'extrap')：t 嚴格遞增；linear／pchip／spline，超出範圍用端點那段外延。複數 x 實虛部分開。"""
    t = np.asarray(t, dtype=float)
    tq = np.asarray(tq, dtype=float)
    x = np.asarray(x)
    if np.iscomplexobj(x):
        return interp1(t, x.real, tq, method) + 1j * interp1(t, x.imag, tq, method)
    x = x.astype(float)
    if t.size < 2:
        raise _err("signal:resample:TimeVectorSize")
    if method == "linear":
        i = np.clip(np.searchsorted(t, tq, side="right") - 1, 0, t.size - 2)
        return x[i] + (tq - t[i]) * ((x[i + 1] - x[i]) / (t[i + 1] - t[i]))
    if method == "pchip":
        h = np.diff(t)
        s = _pchip_slopes(h, np.diff(x) / h)
    elif method == "spline":
        s = _spline_slopes(t, x)
    else:
        raise _err("MATLAB:unrecognizedStringChoice", what="method", name="'linear', 'pchip', 'spline'")
    return _hermite_eval(t, x, s, tq)


def _interp_method(method: Optional[str]) -> str:
    """MATLAB validatestring：不分大小寫、可只打前幾個字。"""
    m = str(method or "linear").strip().lower()
    hits = [k for k in INTERP_METHODS if k.startswith(m)] if m else []
    if len(hits) != 1:
        raise _err("MATLAB:unrecognizedStringChoice", what="method", name="'linear', 'pchip', 'spline'")
    return hits[0]


# ---------------------------------------------------------------- resample
def _check_pq(v, name: str) -> int:
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise _err("MATLAB:resample:expectedFinite", name=name)
    if not math.isfinite(f):
        raise _err("MATLAB:resample:expectedFinite", name=name)
    if f != math.floor(f):
        raise _err("MATLAB:resample:expectedInteger", name=name)
    if f <= 0:
        raise _err("MATLAB:resample:expectedPositive", name=name)
    return int(f)


def resample_filter(p: int, q: int, n: int = RESAMPLE_N, beta: float = RESAMPLE_BETA) -> np.ndarray:
    """resample 的抗混疊 FIR（長度 2nK+1、K = max(p,q)）：截斷理想低通 sinc(m/K)/K × kaiser(L, β)，正規化成 p·h/Σh。n ≤ 0 → ones(p)。"""
    p, q = int(p), int(q)
    K = max(p, q)
    if n <= 0:
        return np.ones(p)
    L = 2 * n * K + 1
    m = np.arange(L, dtype=float) - (L - 1) / 2.0
    h = np.sinc(m / K) / K * np.kaiser(L, beta)
    return p * h / np.sum(h)


def pad_filter(h: np.ndarray, p: int, q: int, Lx: int) -> Tuple[np.ndarray, int]:
    """前後補零的濾波器與延遲（模組說明第 6 點）：回傳 (補零後的 h, delay)。"""
    h = np.asarray(h, dtype=float).ravel()
    L = h.size
    half_len = (L - 1) / 2.0
    n_begin = int(math.floor(q - np.mod(half_len, q)))
    delay = int(math.floor(math.ceil(half_len + n_begin) / q))
    len_h = L + n_begin
    target = -(-(Lx * p) // q)                                   # ceil(Lx·p/q)
    A = (Lx - 1) * p + len_h
    n_end = 0
    if -(-A // q) - delay < target:
        n_end = (target + delay - 1) * q + 1 - A
    assert n_end >= 0 and -(-(A + n_end) // q) - delay >= target
    return np.concatenate([np.zeros(n_begin), h, np.zeros(n_end)]), delay


def upfirdn(x, h, p: int, q: int) -> np.ndarray:
    """MATLAB upfirdn(x,h,p,q)：插 p−1 個零升取樣 → 完整卷積 → 從第 0 點起每 q 點取一點；長度 Ly = ceil(((Lx−1)p + Lh)/q)。
    多相實作（模組說明第 7 點）：輸出第 m 點是升取樣索引 n = m·q 的濾波值，只有第 r = n mod p 相的 tap h[r::p] 會用到，
    所以 y[m] = conv(x, h[r::p])[(n − r)/p]。對每一相 r，滿足 m·q ≡ r (mod p) 的 m 是等差數列 m0 + k·p′（p′ = p/gcd(p,q)），
    對應的卷積索引也是等差數列（公差 q′ = q/gcd），兩邊都用切片，成本 O(Ly + Lx·Lh)。"""
    x = np.asarray(x)
    if np.iscomplexobj(x):
        return upfirdn(x.real, h, p, q) + 1j * upfirdn(x.imag, h, p, q)
    x = x.astype(float).ravel()
    h = np.asarray(h, dtype=float).ravel()
    p, q = int(p), int(q)
    if p < 1 or q < 1:
        raise ValueError("p and q must be positive integers（p、q 必須為正整數）")
    Lx, Lh = x.size, h.size
    Ly = -(-((Lx - 1) * p + Lh) // q)
    if Lx == 0 or Lh == 0:
        return np.zeros(max(Ly, 0))
    if p == 1:
        if q == 1:
            return np.convolve(x, h)
        # 純降取樣：只算要留下的每 q 點。y[m] = Σ_k h[k]·x[m·q − k]，把 k 寫成 r + q·j 後每個 r 是一次短卷積：
        # x 前面補 q−1 個零成 xp，z_r = xp[(q−1−r)::q]（即 x[i·q − r]），y = Σ_r conv(z_r, h[r::q])；成本 Lx·Lh/q
        xp = np.concatenate([np.zeros(q - 1), x])
        y = np.zeros(Ly)
        for r in range(q):
            hr = h[r::q]
            if hr.size == 0:
                continue
            c = np.convolve(xp[q - 1 - r::q], hr)
            n = min(c.size, Ly)
            y[:n] += c[:n]
        return y
    g = math.gcd(p, q)
    pr, qr = p // g, q // g
    inv_q = pow(qr, -1, pr) if pr > 1 else 0                    # q′ 在 mod p′ 下的反元素
    y = np.zeros(Ly)
    for r in range(0, p, g):                                    # m·q ≡ r (mod p) 有解 ⇔ gcd(p,q) | r
        hr = h[r::p]
        if hr.size == 0:
            continue
        m0 = ((r // g) * inv_q) % pr                            # 最小的 m ≥ 0，使 m·q ≡ r (mod p)
        if m0 >= Ly:
            continue
        c = np.convolve(x, hr)                                  # 這一相的輸出 c[j]，j = (m·q − r)/p
        j0 = (m0 * q - r) // p                                  # 整除（m0·q − r 是 p 的倍數、≥ 0）
        if j0 >= c.size:
            continue
        kmax = min((Ly - 1 - m0) // pr, (c.size - 1 - j0) // qr)   # 之後的 j 超出 c 的部分對應零，y 已是零
        y[m0:m0 + kmax * pr + 1:pr] = c[j0:j0 + kmax * qr + 1:qr]
    return y


def resample_pq(x, p: int, q: int) -> Tuple[np.ndarray, np.ndarray]:
    """MATLAB [y,b] = resample(x,p,q)：抗混疊 FIR + 多相 upfirdn，輸出 ceil(Lx·p/q) 點、已補償群延遲。p = q 時直接回傳 x、b = 1。"""
    x = _as_vector(x, "X")
    x = x.astype(complex if np.iscomplexobj(x) else float)
    p = _check_pq(p, "P")
    q = _check_pq(q, "Q")
    p, q = matlab_rat(p / q, RAT_TOL_PQ)
    if p == 1 and q == 1:
        return x.copy(), np.ones(1)
    b = resample_filter(p, q)
    hpad, delay = pad_filter(b, p, q, x.size)
    ny = -(-(x.size * p) // q)
    y = upfirdn(x, hpad, p, q)[delay:delay + ny]
    return y, b


def _interp_clean(t: np.ndarray, x: np.ndarray, tq: np.ndarray, method: str) -> np.ndarray:
    """resample 對非等距輸入的內插（和實測一致）：丟掉 x 為 NaN 的樣本、時間相同的一串合併成平均，再 interp1(…, 'extrap')。"""
    keep = ~np.isnan(x) if not np.iscomplexobj(x) else ~(np.isnan(x.real) | np.isnan(x.imag))
    t1, x1 = t[keep], x[keep]
    if t1.size and np.any(np.diff(t1) == 0):
        starts = np.concatenate([[0], np.nonzero(np.diff(t1) != 0)[0] + 1])
        counts = np.diff(np.append(starts, t1.size))
        x1 = np.add.reduceat(x1, starts) / counts
        t1 = t1[starts]
    if t1.size < 2:
        raise _err("signal:resample:TimeVectorSize")
    return interp1(t1, x1, tq, method)


def resample_t(x, t, fs: float, p: Optional[int] = None, q: Optional[int] = None, method: Optional[str] = None) -> Dict[str, Any]:
    """MATLAB [y,ty,b] = resample(x,tx,fs[,p,q][,method])（Signal Analyzer 的輸出和這個形式相同）。
    回傳 dict：y、ty、b、p、q（實際用的）、grid（內插格點）、grid_step、filter_delay、filter_len、filter_padded_len、ny、fs、method。"""
    x = _as_vector(x, "X")
    x = x.astype(complex if np.iscomplexobj(x) else float)
    t = _as_vector(t, "Tx").astype(float)
    if x.size != t.size:
        raise _err("signal:resample:TimeVectorMismatch")
    fs = float(fs)
    if not math.isfinite(fs):
        raise _err("MATLAB:resample:expectedFinite", name="Fs")
    if fs <= 0:
        raise _err("MATLAB:resample:expectedPositive", name="Fs")
    method = _interp_method(method)
    keep = ~np.isnan(t)
    t, x = t[keep], x[keep]
    if t.size > 1 and np.any(np.diff(t) < 0):
        order = np.argsort(t, kind="stable")
        t, x = t[order], x[order]
    if np.any(np.isinf(t)):
        raise _err("signal:resample:TimeVectorInf")
    if t.size < 2:
        raise _err("signal:resample:TimeVectorSize")
    if p is not None or q is not None:
        if p is None or q is None:
            raise _err("signal:resample:NonUniformMissingQ")
        pp = _check_pq(p, "P")
        qq = _check_pq(q, "Q")
        pp, qq = matlab_rat(pp / qq, RAT_TOL_PQ)
    else:
        ts_avg = (t[-1] - t[0]) / (t.size - 1)
        ratio = ts_avg * fs                                     # 平均取樣間隔 × 目標 fs
        if not ratio > 0:
            # 時間戳記全部相同：合併重複時間後只剩 1 點（模組說明「未定」；MATLAB 這裡會得到 q = Inf、空格點）
            raise _err("signal:resample:TimeVectorSize")
        pp, qq = matlab_rat(ratio, RAT_TOL_CF)
        if pp < 2:
            pp, qq = 1, int(matlab_round(1.0 / ratio))
    step = pp / (qq * fs)
    grid = matlab_colon(t[0], step, t[-1])
    xg = _interp_clean(t, x, grid, method)
    Lx = grid.size
    if pp == 1 and qq == 1:
        y, b, hpad, delay = xg, np.ones(1), np.ones(1), 0
    else:
        b = resample_filter(pp, qq)
        hpad, delay = pad_filter(b, pp, qq, Lx)
        ny = -(-(Lx * pp) // qq)
        y = upfirdn(xg, hpad, pp, qq)[delay:delay + ny]
    ty = t[0] + np.arange(y.size) / fs
    return {"y": y, "ty": ty, "b": b, "p": pp, "q": qq, "grid": grid, "grid_step": step, "filter_delay": delay,
            "filter_len": int(b.size), "filter_padded_len": int(hpad.size), "ny": int(y.size), "fs": fs, "method": method}


# ---------------------------------------------------------------- envelope
def hilbert(x) -> np.ndarray:
    """MATLAB hilbert(x)：FFT 解析訊號（正頻率 ×2、DC 與 Nyquist ×1、負頻率歸零）。"""
    x = np.asarray(x, dtype=float).ravel()
    N = x.size
    if N == 0:
        return np.zeros(0, dtype=complex)
    X = np.fft.fft(x)
    h = np.zeros(N)
    h[0] = 1.0
    if N % 2 == 0:
        h[1:N // 2] = 2.0
        h[N // 2] = 1.0
    else:
        h[1:(N + 1) // 2] = 2.0
    return np.fft.ifft(X * h)


def fir_hilbert_filter(n: int) -> np.ndarray:
    """envelope 'analytic' 的 n-tap 複數濾波器：sinc(k/2)·exp(iπk/2)·kaiser(n, 8)，k = (1−n)/2 … (n−1)/2，除以實部和。"""
    n = int(n)
    tt = (np.arange(n, dtype=float) - (n - 1) / 2.0) / 2.0
    g = np.sinc(tt) * np.exp(1j * np.pi * tt) * np.kaiser(n, FIR_ENVELOPE_BETA)
    return g / np.sum(g.real)


def movrms(x, n: int) -> np.ndarray:
    """sqrt(滑動平均(x²))，n 點視窗：奇數置中，偶數「往前 n/2−1、往後 n/2」，兩端視窗縮短（MATLAB movrms／movmean 'shrink'）。"""
    x = np.asarray(x, dtype=float).ravel()
    n = int(n)
    if n < 1:
        raise ValueError("window length n must be a positive integer（視窗長度 n 必須為正整數）")
    N = x.size
    if N == 0:
        return np.zeros(0)
    kb = (n - 1) // 2 if n % 2 else n // 2 - 1
    kf = n - 1 - kb
    i = np.arange(N)
    lo = np.maximum(i - kb, 0)
    hi = np.minimum(i + kf, N - 1)
    x2 = x * x
    if n <= 512:
        s = np.convolve(x2, np.ones(n))[kf:kf + N]
    else:
        cs = np.concatenate([[0.0], np.cumsum(x2)])
        s = cs[hi + 1] - cs[lo]
    return np.sqrt(np.maximum(s, 0.0) / (hi - lo + 1))


def _envelope_method(method: Optional[str]) -> str:
    m = str(method or "hilbert").strip().lower()
    alias = {"analytic": "fir", "peaks": "peak"}
    m = alias.get(m, m)
    if m not in ENVELOPE_METHODS:
        raise _err("MATLAB:unrecognizedStringChoice", what="method", name="'analytic', 'rms', 'peaks'")
    return m


def _env_peak(x: np.ndarray, n: int) -> Tuple[np.ndarray, np.ndarray]:
    nx = x.size
    if nx < 2:
        return x.copy(), x.copy()
    pos = np.arange(nx, dtype=float)

    def through(v: np.ndarray) -> np.ndarray:
        if nx > n + 1:
            _, ipk = find_peaks(v, min_dist=n, sort_desc=False)
        else:
            ipk = np.zeros(0, dtype=int)
        locs = np.concatenate([[0], ipk, [nx - 1]]) if ipk.size < 2 else ipk
        return interp1(pos[locs], x[locs], pos, "spline")

    return through(x), through(-x)


def envelope(x, n: Optional[int] = None, method: str = "hilbert") -> Tuple[np.ndarray, np.ndarray]:
    """MATLAB [upper, lower] = envelope(x[,n,method])：method hilbert（＝envelope(x)，忽略 n）、fir／analytic、rms、peak／peaks。
    空向量 → 兩個空向量。"""
    x = _as_vector(x, "X")
    if np.iscomplexobj(x):
        raise _err("MATLAB:envelope:expectedReal")
    x = x.astype(float)
    if not np.all(np.isfinite(x)):
        raise _err("MATLAB:envelope:expectedFinite")
    method = _envelope_method(method)
    if method != "hilbert":
        try:
            f = float(n)
        except (TypeError, ValueError):
            raise _err("MATLAB:envelope:expectedPositive")
        if not math.isfinite(f) or f != math.floor(f):
            raise _err("MATLAB:envelope:expectedInteger")
        if f <= 0:
            raise _err("MATLAB:envelope:expectedPositive")
        n = int(f)
    N = x.size
    if N == 0:
        return np.zeros(0), np.zeros(0)
    if method == "peak":
        return _env_peak(x, n)
    m = float(np.mean(x))
    xc = x - m
    if method == "hilbert":
        A = np.abs(hilbert(xc))
    elif method == "fir":
        g = fir_hilbert_filter(n)
        A = np.abs(np.convolve(xc, g)[n // 2:n // 2 + N])
    else:
        A = movrms(xc, n)
    return m + A, m - A


# ---------------------------------------------------------------- Signal Analyzer 的規則
def _is_auto(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip().lower() == "auto")


def _positive_scalar(v, ident: str) -> float:
    """Signal Analyzer 介面套用前的檢查（要是 > 0 的數字）：空字串、非數字、≤ 0、NaN／Inf 都丟 ident 對應的錯誤。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise _err(ident)
    if not (f > 0) or not math.isfinite(f):
        raise _err(ident)
    return f


def app_resample(x, t, fs: Optional[float] = None, rate="auto", factor: Optional[float] = None, uniform: bool = True,
                 method: str = "linear", cf="auto") -> Dict[str, Any]:
    """Signal Analyzer 的 Resample：均勻訊號 targetFs ＝ rate（Hz）或 factor × fs（Auto → UnchangedUniformSignal、
    比值 > 10000 → SignalLengthViolation、內插法與 cf 忽略）；非均勻訊號 Auto → 1/median(diff(t))、cf 有填 → [P,Q] = rat(fs/cf, 0.01)。
    rate／factor 不是正數 → ValueMustBePositive、cf 不是正數 → CriticalFrequencyMustBePositive（UI 的驗證文字）。
    輸出長度 < 2 → InvalidResampledSignal。回傳 resample_t 的 dict 加 target_fs、call（實際傳給 resample 的 (fs, p, q, method)）。"""
    t = _as_vector(t, "Tx").astype(float)
    if uniform:
        if factor is None and _is_auto(rate):
            raise _err("UnchangedUniformSignal")
        if fs is None:
            fs = (t.size - 1) / (t[-1] - t[0])
        target = _positive_scalar(factor, "ValueMustBePositive") * float(fs) if factor is not None else _positive_scalar(rate, "ValueMustBePositive")
        if target / float(fs) > MAX_RATE_RATIO:
            raise _err("SignalLengthViolation")
        p = q = None
        meth = None
    else:
        target = auto_fs(t) if _is_auto(rate) else _positive_scalar(rate, "ValueMustBePositive")
        if not (target > 0) or not math.isfinite(target):
            raise _err("ValueMustBePositive")
        meth = _interp_method(method)
        if _is_auto(cf):
            p = q = None
        else:
            p, q = critical_pq(target, _positive_scalar(cf, "CriticalFrequencyMustBePositive"))
    res = resample_t(x, t, target, p, q, meth)
    if res["ny"] < 2:
        raise _err("InvalidResampledSignal")
    res["target_fs"] = target
    res["call"] = (target, p, q, meth)
    return res


def app_envelope(x, method: str = "hilbert", output: str = "upper", n: Optional[int] = None,
                 seconds: Optional[float] = None, fs: Optional[float] = None) -> Dict[str, Any]:
    """Signal Analyzer 的 Envelope：時間單位的長度先換成秒再 N = round(秒 × fs)（seconds 有給就必須給 fs）；
    output 是 'upper' 或 'lower'。回傳 dict：y（upper 或 lower）、n、call。"""
    method = _envelope_method(method)
    out = str(output).strip().lower()
    if out not in ("upper", "lower"):
        raise _err("MATLAB:unrecognizedStringChoice", what="output", name="'upper', 'lower'")
    if np.iscomplexobj(np.asarray(x)):
        raise _err("envelopeComplexSignals")
    if method != "hilbert" and seconds is not None:
        n = window_samples(seconds, fs)
    upper, lower = envelope(x, None if method == "hilbert" else n, method)
    y = upper if out == "upper" else lower
    return {"y": y, "n": None if method == "hilbert" else int(n), "call": (method, None if method == "hilbert" else int(n))}


# ---------------------------------------------------------------- selftest
def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/resample_envelope/ref_resample_envelope.json；
    研究腳本 ref_resample_envelope.m 產生，含 Signal Analyzer 的 26 次實測）。
    容差見模組說明末段：預設 rtol 1e-12、atol 1e-15；ty、格點首尾／步長、整數參數、rat 結果要求位元相同。"""
    import json
    import os
    import time as _time
    d = os.path.join(ref_dir, "resample_envelope")
    path = os.path.join(d, "ref_resample_envelope.json")
    if not os.path.isfile(path):
        check(True, "（沒有 tests/matlab_ref/resample_envelope：略過 MATLAB 重取樣／包絡比對）")
        return
    R = json.load(open(path, encoding="utf-8"))
    sig = {k: np.loadtxt(os.path.join(d, f"inputs_{k}.txt")) for k in ("xU", "tU", "xN", "tN", "tD", "e1", "e2", "e3")}
    # 實測（2026-10-24）：y／b／upper 最大相對差 2.3e-13；lower 兩個 |值| ≈ 3e-4、3e-5 的樣本相對差 1.9e-12、絕對差 ≤ 4.4e-16
    RTOL, ATOL = 1e-12, 1e-15

    def arr(v):
        if v is None or (isinstance(v, list) and len(v) == 0):
            return np.zeros(0)
        return np.atleast_1d(np.asarray(v, dtype=float))

    def relerr(a, b) -> float:
        """有限值的最大相對差（參考值為 0 時用絕對差）；形狀不同 → inf。"""
        a, b = np.asarray(a, dtype=float).ravel(), np.asarray(b, dtype=float).ravel()
        if a.shape != b.shape:
            return math.inf
        fa = np.isfinite(a) & np.isfinite(b)
        if not np.any(fa):
            return 0.0
        diff = np.abs(a[fa] - b[fa])
        den = np.abs(b[fa])
        rel = np.where(den > 0, diff / np.where(den > 0, den, 1.0), diff)
        return float(np.max(rel))

    def worst(a, b):
        a, b = np.asarray(a, dtype=float).ravel(), np.asarray(b, dtype=float).ravel()
        if a.shape != b.shape:
            return f"shape {a.shape} vs {b.shape}"
        if a.size == 0:
            return "empty"
        with np.errstate(invalid="ignore", divide="ignore"):
            rel = np.abs(a - b) / np.abs(b)
        rel[~np.isfinite(rel)] = np.abs(a - b)[~np.isfinite(rel)]
        i = int(np.argmax(rel))
        return f"i={i} mine={a[i]!r} matlab={b[i]!r} rel={rel[i]:.3g}"

    def close(a, b, rtol=RTOL, atol=ATOL):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        if a.shape != b.shape:
            return False
        fa, fb = np.isfinite(a), np.isfinite(b)
        if not np.array_equal(fa, fb) or not np.array_equal(a[~fa], b[~fb], equal_nan=True):
            return False
        return bool(np.allclose(a[fa], b[fa], rtol=rtol, atol=atol))

    def exact(a, b):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        return a.shape == b.shape and bool(np.array_equal(a, b, equal_nan=True))

    def report(bad, n, msg, mr=None):
        check(not bad, msg + f"（{n} 組" + (f"，最大相對差 {mr:.1e}" if mr is not None else "") + "）" + (f"（不一致：{bad}）" if bad else ""))

    def raises(fn, ident):
        """fn() 必須丟 ConvertError 且 ident 相同（ident=None：任何 ValueError 但不是 ConvertError）；回傳問題描述或 None。"""
        try:
            fn()
        except ConvertError as ex:
            if ident is None:
                return f"丟了 ConvertError {ex.ident}，應為一般 ValueError"
            return None if ex.ident == ident else f"丟了 {ex.ident}，應為 {ident}"
        except ValueError as ex:
            return None if ident is None else f"丟了 {type(ex).__name__}: {ex}，應為 {ident}"
        except Exception as ex:                                   # noqa: BLE001 — 任何其他例外都算失敗
            return f"丟了 {type(ex).__name__}: {ex}，應為 {ident or 'ValueError'}"
        return f"沒丟（應為 {ident or 'ValueError'}）"

    # --- rat(X, 0.01)
    bad = []
    for c in R["rat_tol001"]:
        N, D = matlab_rat(c["x"], c["tol"])
        if (N, D) != (int(c["N"]), int(c["D"])):
            bad.append(f"{c['x']}→{N}/{D}≠{c['N']}/{c['D']}")
    ok_def = matlab_rat(math.pi) == (355, 113) and matlab_rat(0.75) == (3, 4) and matlab_rat(-0.4, 0.01) == (-2, 5)
    report(bad if ok_def else bad + ["default tol"], len(R["rat_tol001"]), "rat(X, 0.01) vs MATLAB（0/1、80/79、17/7…連分數 round 取整、絕對容差）：N、D 完全相同")
    # --- 抗混疊濾波器：kaiser(L,5) 與 sinc 閉合式
    bad, mr = [], 0.0
    for c in R["filter_design_check"]:
        K, L = int(c["pqmax"]), int(c["L"])
        mr = max(mr, relerr(np.kaiser(L, 5.0), arr(c["kaiser5"])))
        if not close(np.kaiser(L, 5.0), arr(c["kaiser5"])):
            bad.append(f"kaiser@{L}:{worst(np.kaiser(L, 5.0), arr(c['kaiser5']))}")
        if c["max_abs_diff_firls_vs_sinc"] != 0 or L != 2 * 10 * K + 1:
            bad.append(f"firls≠sinc@{K}")
        h = resample_filter(K, 1)
        if not (h.size == L and abs(h.sum() - K) < 1e-12 * K):
            bad.append(f"norm@{K}")
    report(bad, len(R["filter_design_check"]), "重取樣濾波器 vs MATLAB：kaiser(L,5) 逐點一致、firls 零寬過渡＝sinc 閉合式（差 0）、Σh = p", mr)
    # --- upfirdn 多相實作 vs 定義（插零、完整卷積、每 q 點取一點），含 gcd(p,q) > 1 與 p = 1 的純降取樣路徑
    rng = np.random.default_rng(20261024)

    def upfirdn_def(x, h, p, q):
        xu = np.zeros((x.size - 1) * p + 1)
        xu[::p] = x
        return np.convolve(xu, h)[::q]

    bad, n_up = [], 0
    for p, q in ((1, 1), (1, 3), (3, 2), (2, 3), (4, 6), (6, 4), (6, 9), (8, 8), (147, 160), (160, 147), (10, 4), (1, 7)):
        for Lx, Lh in ((1, 1), (5, 1), (13, 7), (7, 100), (120, 2 * 10 * max(p, q) + 1)):
            n_up += 1
            x, h = rng.standard_normal(Lx), rng.standard_normal(Lh)
            a, b = upfirdn(x, h, p, q), upfirdn_def(x, h, p, q)
            if not close(a, b, rtol=1e-12, atol=1e-12):
                bad.append(f"p/q={p}/{q} Lx={Lx} Lh={Lh}: {worst(a, b)}")
    report(bad, n_up, "upfirdn 多相（模運算切片）vs 直接定義：p/q = 1/1、1/3、3/2、2/3、4/6、6/4、6/9、8/8、147/160、160/147、10/4、1/7 × 5 種長度一致")
    # --- resample(x,p,q)
    bad, mr = [], 0.0
    for c in R["resample_pq"]:
        y, b = resample_pq(sig["xU"], c["p"], c["q"])
        mr = max(mr, relerr(y, arr(c["y"])), relerr(b, arr(c["b"])))
        if not close(y, arr(c["y"])):
            bad.append(f"{c['name']} y:{worst(y, arr(c['y']))}")
        if not close(b, arr(c["b"])):
            bad.append(f"{c['name']} b:{worst(b, arr(c['b']))}")
    report(bad, len(R["resample_pq"]), "resample(x,p,q) vs MATLAB（3/2、2/3、1/4、5/1、147/160、1/1、7/3）：y 與濾波器 b 逐點一致", mr)

    # --- resample(x,tx,fs[,p,q][,method])
    def tx_case(c):
        t = sig["tU"] if c["x"] == "xU" else (sig["tD"] if c["name"].startswith("nudup") else sig["tN"])
        x = sig["xU"] if c["x"] == "xU" else sig["xN"]
        p = int(c["p_arg"]) if not isinstance(c["p_arg"], list) else None
        q = int(c["q_arg"]) if not isinstance(c["q_arg"], list) else None
        return resample_t(x, t, c["fs_target"], p, q, c["method"] or None)

    groups = {"uni": [], "nu": [], "cf": [], "dup": []}
    for c in R["resample_tx"]:
        key = "uni" if c["x"] == "xU" else ("dup" if c["name"].startswith("nudup") else ("cf" if "_cf" in c["name"] else "nu"))
        groups[key].append(c)
    labels = {"uni": "均勻訊號 resample(x,t,fs)（250/30/37/44.1/100/1000/7/63.5/50 Hz、因子 2.5／0.3）",
              "nu": "非均勻訊號 resample(x,t,fs,method)（Auto＝1/median(dt)、80、23 Hz × linear／pchip／spline）",
              "cf": "臨界頻率 resample(x,t,fs,P,Q,method)（[P,Q]=rat(fs/cf,0.01)：cf 200/30/500/120/33/161/250、Auto+200）",
              "dup": "重複時間戳記（合併取平均）resample(x,t,50,linear／spline)"}
    for key, cases in groups.items():
        bad, mr = [], 0.0
        for c in cases:
            r = tx_case(c)
            g = r["grid"]
            probs = []
            mr = max(mr, relerr(r["y"], arr(c["y"])), relerr(r["b"], arr(c["b"])))
            if not close(r["y"], arr(c["y"])):
                probs.append("y:" + worst(r["y"], arr(c["y"])))
            if not exact(r["ty"], arr(c["ty"])):
                probs.append("ty 不是位元相同:" + worst(r["ty"], arr(c["ty"])))
            if not close(r["b"], arr(c["b"])):
                probs.append("b:" + worst(r["b"], arr(c["b"])))
            ints = (r["p"], r["q"], g.size, r["filter_delay"], r["filter_len"], r["filter_padded_len"], r["ny"])
            ref_ints = tuple(int(c[k]) for k in ("p_used", "q_used", "grid_len", "filter_delay", "filter_len", "filter_padded_len", "ny"))
            if ints != ref_ints:
                probs.append(f"p,q,grid_len,delay,L,Lpad,ny {ints}≠{ref_ints}")
            if not (g[0] == c["grid_first"] and g[-1] == c["grid_last"] and r["grid_step"] == c["grid_step"]):
                probs.append(f"grid first/last/step {g[0]!r},{g[-1]!r},{r['grid_step']!r}≠{c['grid_first']!r},{c['grid_last']!r},{c['grid_step']!r}")
            if key == "cf":
                cf = float(c["name"].split("_cf")[1].split("_")[0])
                if critical_pq(c["fs_target"], cf) != (int(c["p_arg"]), int(c["q_arg"])):
                    probs.append(f"rat(fs/cf)≠{c['p_arg']}/{c['q_arg']}")
            if probs:
                bad.append(f"{c['name']}: " + "; ".join(probs))
        report(bad, len(cases), f"{labels[key]} vs MATLAB：y、b 逐點一致，ty、格點首尾／步長位元相同，推得的 p/q、格點數、延遲、濾波器長度、ny 相同", mr)
    af = R["nonuniform_auto_fs"]
    a_fs = auto_fs(sig["tN"])
    check(a_fs == af["value"] and abs(a_fs - af["mean_based"]) > 0.1 and abs(a_fs - af["span_based"]) > 0.1,
          f"非均勻 Auto 取樣率 = 1/median(diff(t)) = {af['value']!r}（和 app 17 位一致；1/mean(dt) = {af['mean_based']:.6f} 與 (N−1)/跨度 = {af['span_based']:.6f} 都不是）")

    # --- envelope
    env = {"hilbert": [], "fir": [], "rms": [], "peak": []}
    for c in R["envelope"]:
        env[c["method"]].append(c)
    desc = {"hilbert": "Hilbert（FFT 解析訊號）", "fir": "FIR 'analytic'（n = 1/2/3/10/30/31/64/N−1/N/N+7）",
            "rms": "RMS（n = 1/2/3/4/5/10/11/50/N/N+5，偶數視窗往後多一點、兩端縮短）",
            "peak": "Peak（findpeaks MinPeakDistance n = 1/2/5/6/30/N−2/N−1/N+5 + not-a-knot 樣條）"}
    for key, cases in env.items():
        bad, mr = [], 0.0
        for c in cases:
            n = None if isinstance(c["n"], list) else int(c["n"])
            u, l = envelope(sig[c["sig"]], n, key)
            mr = max(mr, relerr(u, arr(c["upper"])), relerr(l, arr(c["lower"])))
            if not close(u, arr(c["upper"])):
                bad.append(f"{c['sig']} n={n} upper:{worst(u, arr(c['upper']))}")
            if not close(l, arr(c["lower"])):
                bad.append(f"{c['sig']} n={n} lower:{worst(l, arr(c['lower']))}")
        report(bad, len(cases), f"包絡 {desc[key]} vs MATLAB envelope（e1 衰減餘弦 200 點、e2 雜訊 151 點、e3 AM 256 點）：upper／lower 逐點一致", mr)
    bad, mr = [], 0.0
    for c in R["fir_hilbert_filter"]:
        g = fir_hilbert_filter(int(c["n"]))
        mr = max(mr, relerr(g.real, arr(c["re"])), relerr(g.imag, arr(c["im"])))
        if not (close(g.real, arr(c["re"]), atol=1e-16) and close(g.imag, arr(c["im"]), atol=1e-16)):
            bad.append(f"n={c['n']}:{worst(g.real, arr(c['re']))}/{worst(g.imag, arr(c['im']))}")
    # movrms 的偶數視窗慣例：MATLAB 的 movrms 和 movmean(x², [n/2−1 n/2]) 差 ≤ 2e-16，和相反慣例 [n/2 n/2−1] 差 0.08～1.46
    for c in R["movrms_convention"]:
        if not (c["maxdiff_back_n2m1_fwd_n2"] < 1e-14 and (int(c["n"]) % 2 or c["maxdiff_back_n2_fwd_n2m1"] > 0.01)):
            bad.append(f"movrms convention n={c['n']}")
    x2 = sig["e2"] - np.mean(sig["e2"])

    def movrms_def(x, n):
        kb = (n - 1) // 2 if n % 2 else n // 2 - 1
        out = np.empty(x.size)
        for i in range(x.size):
            lo, hi = max(i - kb, 0), min(i + (n - 1 - kb), x.size - 1)
            out[i] = math.sqrt(np.mean(x[lo:hi + 1] ** 2))
        return out

    for n in (1, 2, 4, 10, 600):
        if not close(movrms(x2, n), movrms_def(x2, n)):
            bad.append(f"movrms n={n} ≠ 逐點定義")
    report(bad, len(R["fir_hilbert_filter"]) + len(R["movrms_convention"]),
           "FIR Hilbert 濾波器複數 tap（n = 1/2/10/31）與 movrms 偶數視窗慣例 [n/2−1, n/2]（MATLAB 比對差 ≤ 2e-16、相反慣例差 > 0.01；"
           "卷積與累積和路徑都等於逐點定義）", mr)

    # --- Signal Analyzer 的 26 次實測
    def ident_of(run):
        if run["dialog_key"] and not isinstance(run["dialog_key"], list):
            return run["dialog_key"]
        if "Expected P to be positive" in str(run["error"]):
            return "MATLAB:resample:expectedPositive"
        if run["name"].startswith("env"):
            return "MATLAB:envelope:expectedPositive"
        return "?"

    def find_tx(xname, fs, p, q, meth):
        for c in R["resample_tx"]:
            cp = None if isinstance(c["p_arg"], list) else int(c["p_arg"])
            cq = None if isinstance(c["q_arg"], list) else int(c["q_arg"])
            if c["x"] == xname and c["fs_target"] == fs and (cp, cq) == (p, q) and (c["method"] or None) == meth and not c["name"].startswith("nudup"):
                return c
        return None

    bad_r, bad_e, n_r, n_e = [], [], 0, 0
    for run in R["app_runs"]:
        s = run["ui_settings"]
        name = run["name"]
        ok = run["ok"] is True
        want = None if ok else ident_of(run)
        if ok and run["data_equals_direct_call"] is not True:
            # 參考資料本身的前提：Signal Analyzer 的輸出和直接呼叫 resample／envelope 位元相同，所以下面可以拿直接呼叫的參考值比
            (bad_e if name.startswith("env") else bad_r).append(f"{name}: 參考資料 data_equals_direct_call={run['data_equals_direct_call']!r}")
        try:
            if name.startswith("env"):
                n_e += 1
                units = s["windowLengthTimeUnits"] if s["method"] == "rms" else s["maximaSeparationTimeUnits"]
                val = s["windowLength"] if s["method"] == "rms" else (s["maximaSeparation"] if s["method"] == "peak" else s["filterOrder"])
                kw = dict(method=s["method"], output=s["outputType"])
                if s["method"] in ("rms", "peak") and units != "samples":
                    kw.update(seconds=float(val), fs=100.0)          # 參考資料裡的值已是秒（單位換算在介面上做），units 只是標籤
                elif s["method"] != "hilbert":
                    kw.update(n=int(val))
                r = app_envelope(sig["e1"], **kw)
                if not ok:
                    bad_e.append(f"{name}: 應丟 {want}")
                    continue
                call = run["equivalent_call"][0]["args"]
                exp_n = int(call[1]) if len(call) > 1 else None
                probs = []
                if r["n"] != exp_n or r["y"].size != run["data_len"]:
                    probs.append(f"N {r['n']}≠{exp_n} 或長度 {r['y'].size}≠{run['data_len']}")
                rp = run["ui_display"]
                fmt = rp.get("formattedWindowLength", rp.get("formattedMaximaSeparation")) if isinstance(rp, dict) else None
                if fmt is not None and fmt != r["n"]:
                    probs.append(f"formatted {fmt}≠{r['n']}")
                ref = [c for c in R["envelope"] if c["sig"] == "e1" and c["method"] == s["method"]
                       and ((isinstance(c["n"], list) and exp_n is None) or (not isinstance(c["n"], list) and int(c["n"]) == exp_n))]
                if ref and not close(r["y"], arr(ref[0][s["outputType"]])):
                    probs.append("值:" + worst(r["y"], arr(ref[0][s["outputType"]])))
                if probs:
                    bad_e.append(f"{name}: " + "; ".join(probs))
            else:
                n_r += 1
                uni = s["timeMode"] == "uniform"
                x, t = (sig["xU"], sig["tU"]) if uni else (sig["xN"], sig["tN"])
                rate = s["sampleRate"] if s["sampleRateType"] == "specifysamplerate" else None
                factor = s["sampleFactor"] if s["sampleRateType"] == "specifysamplefactor" else None
                r = app_resample(x, t, fs=100.0 if uni else None, rate="auto" if rate == "Auto" else rate, factor=factor, uniform=uni,
                                 method=s["interpolationMethod"], cf=s["criticalFrequency"])
                if not ok:
                    bad_r.append(f"{name}: 應丟 {want}")
                    continue
                call = run["equivalent_call"][0]["args"][2:]
                fs_c = float(call[0])
                meth_c = call[-1] if isinstance(call[-1], str) else None
                nums = [v for v in call[1:] if not isinstance(v, str)]
                pq_c = (int(nums[0]), int(nums[1])) if nums else (None, None)
                probs = []
                if r["call"] != (fs_c, pq_c[0], pq_c[1], meth_c):
                    probs.append(f"呼叫 {r['call']}≠{(fs_c, pq_c[0], pq_c[1], meth_c)}")
                if r["ny"] != run["data_len"]:
                    probs.append(f"長度 {r['ny']}≠{run['data_len']}")
                ref = find_tx("xU" if uni else "xN", fs_c, pq_c[0], pq_c[1], meth_c)
                if ref is not None and not (close(r["y"], arr(ref["y"])) and exact(r["ty"], arr(ref["ty"]))):
                    probs.append("值:" + worst(r["y"], arr(ref["y"])))
                if probs:
                    bad_r.append(f"{name}: " + "; ".join(probs))
        except ConvertError as e:
            if ok or e.ident != want:
                (bad_e if name.startswith("env") else bad_r).append(f"{name}: 丟了 {e.ident}（{e.en}），應為 {want or 'ok'}")
    report(bad_r, n_r, "Signal Analyzer Resample 實測 vs 重現（均勻 250/37/Auto→不處理/因子 2.5、0.3/忽略內插與 cf/ts 模式；"
                       "非均勻 Auto linear／spline、80 pchip、cf 200、cf 33 spline、Auto+cf 200、cf 1e6→P=0 錯誤、0.01 Hz→長度 1 錯誤）：呼叫引數、長度、值、例外一致")
    report(bad_e, n_e, "Signal Analyzer Envelope 實測 vs 重現（Hilbert 上／下、FIR 30／31、RMS 10、0.055 ms→6（參考資料的 units 欄位是 ms 但值已是秒）、"
                       "0.054 s→5、0.0249 s→2、Peak 5、0.055 s→6、0.004 ms→0 錯誤）：N、長度、值、例外一致")
    # --- 錯誤對應與邊界輸入
    e = _err("MATLAB:resample:expectedPositive", name="P")
    bad = []
    if e.en != "Expected P to be positive." or not e.zh:
        bad.append("P")
    for ident in MESSAGES:
        en, zh = MESSAGES[ident]
        if not (en and zh):
            bad.append(ident)
    t8 = np.arange(8) / 100.0
    x8 = np.arange(8.0)
    cases = [
        ("時間點不足", lambda: resample_t([1.0, 2.0, 3.0], [0.0, np.nan, np.nan], 10.0), "signal:resample:TimeVectorSize"),
        ("時間戳記全相同", lambda: resample_t(x8, np.zeros(8), 250.0), "signal:resample:TimeVectorSize"),
        ("時間戳記全相同＋P,Q", lambda: resample_t(x8, np.zeros(8), 250.0, 2, 1), "signal:resample:TimeVectorSize"),
        ("P=0", lambda: resample_t(sig["xN"], sig["tN"], 80.0, 0, 1), "MATLAB:resample:expectedPositive"),
        ("時間含 Inf", lambda: resample_t(x8, np.r_[t8[:-1], np.inf], 100.0), "signal:resample:TimeVectorInf"),
        ("x、t 長度不同", lambda: resample_t(x8, t8[:-1], 100.0), "signal:resample:TimeVectorMismatch"),
        ("Sample Rate 空字串", lambda: app_resample(x8, t8, fs=100.0, rate="", uniform=True), "ValueMustBePositive"),
        ("Sample Rate 非數字", lambda: app_resample(x8, t8, fs=100.0, rate="abc", uniform=True), "ValueMustBePositive"),
        ("Sample Rate ≤ 0", lambda: app_resample(x8, t8, fs=100.0, rate=-5, uniform=True), "ValueMustBePositive"),
        ("Sample Factor 非數字", lambda: app_resample(x8, t8, fs=100.0, factor="x", uniform=True), "ValueMustBePositive"),
        ("非均勻 Sample Rate 空字串", lambda: app_resample(sig["xN"], sig["tN"], rate="", uniform=False), "ValueMustBePositive"),
        ("cf 非數字", lambda: app_resample(sig["xN"], sig["tN"], rate=80.0, uniform=False, cf="abc"), "CriticalFrequencyMustBePositive"),
        ("cf = 0", lambda: app_resample(sig["xN"], sig["tN"], rate=80.0, uniform=False, cf=0), "CriticalFrequencyMustBePositive"),
        ("均勻 Auto", lambda: app_resample(x8, t8, fs=100.0, rate="Auto", uniform=True), "UnchangedUniformSignal"),
        ("比值 > 10000", lambda: app_resample(x8, t8, fs=100.0, rate=100.0 * 10000.0001, uniform=True), "SignalLengthViolation"),
        ("輸出長度 1", lambda: app_resample(sig["xU"], sig["tU"], fs=100.0, rate=0.5, uniform=True), "InvalidResampledSignal"),
        ("2-D x（resample）", lambda: resample_t(np.ones((4, 2)), t8, 100.0), "DSV:expectedVector"),
        ("2-D x（resample_pq）", lambda: resample_pq(np.ones((4, 2)), 2, 1), "DSV:expectedVector"),
        ("2-D x（envelope）", lambda: envelope(np.ones((4, 2))), "DSV:expectedVector"),
        ("envelope N=0", lambda: envelope(x8, 0, "rms"), "MATLAB:envelope:expectedPositive"),
        ("envelope N 非整數", lambda: envelope(x8, 2.5, "rms"), "MATLAB:envelope:expectedInteger"),
        ("envelope 複數", lambda: envelope(x8 + 1j), "MATLAB:envelope:expectedReal"),
        ("envelope 含 NaN", lambda: envelope(np.r_[x8, np.nan], 3, "rms"), "MATLAB:envelope:expectedFinite"),
        ("envelope 未知 method", lambda: envelope(x8, 3, "bogus"), "MATLAB:unrecognizedStringChoice"),
        ("app_envelope 複數", lambda: app_envelope(x8 + 1j), "envelopeComplexSignals"),
        ("app_envelope output 錯", lambda: app_envelope(x8, output="bogus"), "MATLAB:unrecognizedStringChoice"),
        ("app_envelope 秒但沒 fs", lambda: app_envelope(x8, method="rms", seconds=0.05), None),
        ("movrms n=0", lambda: movrms(x8, 0), None),
        ("upfirdn p=0", lambda: upfirdn(x8, [1.0], 0, 1), None),
    ]
    for label, fn, ident in cases:
        prob = raises(fn, ident)
        if prob:
            bad.append(f"{label}: {prob}")
    try:
        empties = [envelope(np.zeros(0), 3, m) for m in ("fir", "rms", "peak")] + [envelope(np.zeros(0))]
        if not all(u.size == 0 and l.size == 0 for u, l in empties):
            bad.append("envelope(空) 不是空")
        u, l = envelope(sig["e1"].reshape(1, -1), 5, "rms")                 # 1×N 列向量照 MATLAB isvector 接受
        if not (u.shape == (200,) and close(u, envelope(sig["e1"], 5, "rms")[0])):
            bad.append("envelope(1×N) 形狀")
        rr = resample_t(sig["xU"].reshape(-1, 1), sig["tU"].reshape(1, -1), 250.0)
        if rr["ny"] != 300:
            bad.append("resample_t(N×1, 1×N) 長度")
        if not (app_resample(x8, t8, fs=100.0, rate="auto", factor=2.0, uniform=True)["target_fs"] == 200.0
                and app_envelope(x8, method="rms", seconds=0.05, fs=100.0)["n"] == 5 and window_samples(0.055, 100.0) == 6
                and app_envelope(x8, output="LOWER")["y"].shape == (8,)):
            bad.append("合法呼叫結果")
    except Exception as ex:                                                 # noqa: BLE001
        bad.append(f"合法呼叫丟錯 {type(ex).__name__}: {ex}")
    check(not bad, f"錯誤對應與邊界輸入（{len(cases)} 種）：P=0 → 'Expected P to be positive.'、時間點不足／全相同 → TimeVectorSize、"
                   "Inf／長度不符、UI 的 Sample Rate／Factor／cf 驗證、2-D 輸入、envelope 的 N／複數／NaN、空向量回空、1×N 與 N×1 接受；"
                   "每個 ident 都有英文與繁中訊息" + (f"（{bad}）" if bad else ""))
    # --- 參考資料沒有的路徑，用自我一致性驗證（沒有 MATLAB 參考資料；檢查順序照 MATLAB resample 的定義）
    bad = []
    tn, xn = sig["tN"], sig["xN"]
    perm = np.random.default_rng(7).permutation(tn.size)
    a = resample_t(xn, tn, 80.0, method="spline")
    b = resample_t(xn[perm], tn[perm], 80.0, method="spline")                      # 未排序的時間：穩定排序後一樣
    if not (exact(a["y"], b["y"]) and exact(a["ty"], b["ty"])):
        bad.append("未排序時間 ≠ 排序後")
    c = resample_t(np.r_[xn, 1.0, 2.0], np.r_[tn, np.nan, np.nan], 80.0, method="pchip")   # NaN 時間的樣本整個丟掉
    if not exact(c["y"], resample_t(xn, tn, 80.0, method="pchip")["y"]):
        bad.append("NaN 時間")
    k = 30
    xg = xn.copy()
    xg[k] = np.nan                                                                  # x 為 NaN 的樣本只在內插時丟掉（格點仍用原 t）
    xf = xn.copy()
    xf[k] = xn[k - 1] + (xn[k + 1] - xn[k - 1]) * (tn[k] - tn[k - 1]) / (tn[k + 1] - tn[k - 1])   # 補成鄰點直線上的值
    d1, d2 = resample_t(xg, tn, 80.0, method="linear"), resample_t(xf, tn, 80.0, method="linear")
    if not (d1["ny"] == d2["ny"] and exact(d1["ty"], d2["ty"]) and exact(d1["grid"], d2["grid"]) and np.all(np.isfinite(d1["y"]))
            and close(d1["y"], d2["y"], atol=1e-14)):
        bad.append("x 含 NaN:" + worst(d1["y"], d2["y"]))
    check(not bad, "無 MATLAB 參考值的路徑（自我一致）：未排序時間排序後結果位元相同、NaN 時間的樣本整個丟掉、x 為 NaN 的樣本只在內插時丟掉"
                   "（linear 下等於把它補成鄰點直線上的值，格點與 ty 不變）" + (f"（{bad}）" if bad else ""))
    # --- 大資料：1e6 點，與 Signal Analyzer 允許的最大比值 10000（p = 10000 的多相路徑）；時間上限 20 s 只是「沒有卡死」的保險
    N = 1_000_000
    fs0 = 1000.0
    tt = np.arange(N) / fs0
    xx = np.sin(2 * np.pi * 50 * tt) * (1 + 0.5 * np.sin(2 * np.pi * 0.5 * tt)) + 0.1
    t0 = _time.time()
    r1 = app_resample(xx, tt, fs=fs0, rate=2500.0, uniform=True)                 # p=5, q=2
    t_res = _time.time() - t0
    t0 = _time.time()
    r2 = resample_t(xx, tt, 441.0)                                              # 441/1000 → rat(0.441,0.01)=4/9
    t_res2 = _time.time() - t0
    t0 = _time.time()
    r3 = resample_t(xx, tt, 1.0)                                                # 1/1000：純降取樣路徑（q = 1000）
    t_res3 = _time.time() - t0
    t0 = _time.time()
    r4 = app_resample(xx[:2000], tt[:2000], fs=fs0, rate=fs0 * 10000, uniform=True)   # 比值 10000：p = 10000（2000 點 → 2e7 點）
    t_res4 = _time.time() - t0
    t0 = _time.time()
    u1, _ = envelope(xx)
    u2, _ = envelope(xx, 50, "rms")
    u3, _ = envelope(xx, 30, "fir")
    t_env = _time.time() - t0
    t0 = _time.time()
    u4, _ = envelope(xx, 5, "peak")
    t_pk = _time.time() - t0
    total = t_res + t_res2 + t_res3 + t_res4 + t_env + t_pk
    ok = (r1["ny"] == 2_500_000 and r1["p"] == 5 and r1["q"] == 2 and r2["ny"] == 441_000 and (r2["p"], r2["q"]) == (4, 9)
          and r3["ny"] == 1000 and (r3["p"], r3["q"]) == (1, 1000) and r4["ny"] == 20_000_000 and (r4["p"], r4["q"]) == (10000, 1)
          and np.all(np.isfinite(r3["y"])) and np.all(np.isfinite(r4["y"]))
          and abs(np.max(np.abs(r4["y"][20000:-20000])) - np.max(np.abs(xx[:2000]))) < 0.01            # 升取樣後峰值 ≈ 原訊號峰值 1.6
          and u1.size == N and u2.size == N and u3.size == N and u4.size == N and np.all(np.isfinite(u1)) and np.all(np.isfinite(u4))
          and abs(np.max(u1[1000:-1000]) - 1.6) < 0.05 and total < 20.0)
    check(ok, f"1e6 點：resample 1000→2500 Hz（5/2）{t_res:.2f}s、→441 Hz（4/9）{t_res2:.2f}s、→1 Hz（1/1000 純降取樣）{t_res3:.2f}s；"
              f"2000 點 × 比值 10000（p=10000 → 2e7 點）{t_res4:.2f}s；包絡 Hilbert＋RMS 50＋FIR 30 共 {t_env:.2f}s、"
              f"Peak 5（{N // 20} 個峰的樣條）{t_pk:.2f}s；合計 {total:.2f}s（上限 20 s）")
