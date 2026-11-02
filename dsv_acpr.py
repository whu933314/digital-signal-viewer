# -*- coding: utf-8 -*-
"""相鄰通道功率比 ACPR（MATLAB Spectrum Analyzer 的 CHANNEL MEASUREMENTS → Type = ACPR，以及 comm.ACPR）——純 numpy，和 GUI 分開。

依據（MATLAB R2025a；程式是自己寫的，所有數字都是 MATLAB 算出來再逐筆比對的）：

A. 分析器本身的規則（主要依據；DSV 的頻譜視窗要重現的是分析器，不只是工具箱函式）。2026-10-24 用 spectrumAnalyzer 實際跑了
   23 個 acpr_* 設定（scope_capture.m，getMeasurementsData／getSpectrumData），tests/matlab_ref/scope/acpr/acpr_scope_ref.json
   存每個 capture 實際用到的設定、分析器回報的全部數字、畫面抽樣與訊號檔名；規則的推定在 scope_capture/ANALYSIS.md §3、
   rules.json（A1–A7），selftest() 第 7 節逐筆重算：
   - 畫面頻譜：hann(L,'periodic')、NFFT = max(1024, 視窗長度)、power = |X|²/(Σw)²、power-density = |X|²/(fs·Σw²)，雙邊用 MATLAB
     centered（偶數 NFFT 時 Nyquist 在 +fs/2、沒有 −fs/2），單邊 0..fs/2（DC／Nyquist 以外 ×2）——就是 dsv_spectrum.welch 的輸出，
     19 個畫面新鮮的 capture 對到 ≤ 7.8e-11 dB。量測用的是 PSD：power 模式 = 畫面功率 / RBW（RBW = ENBW = fs·Σw²/(Σw)²），
     power-density 模式 = 畫面值本身；兩種模式的 ACPR 與 Channel Power 完全相同（A3）。
   - 積分（A1，和分析器的 Occupied BW 同一條）：PSD 視為分段常數，bin k 佔 [f_k − Δf/2, f_k + Δf/2]（第一與最後一個 bin 也是，
     所以格點外側各多半個 bin）；頻帶功率 = 這個階梯函數在 [f1, f2] 上的精確積分（兩端的 bin 按落在帶內的比例算）。
     'scope' 規則就是這條，這裡用「兩端部分 bin + 中間整 bin 直接相加」實作（不用累積和，避免相消誤差）：22 個可評估的 capture
     Channel Power／Lower／Upper 全部對到 ≤ 1.2e-13 dB（ANALYSIS.md 報的 Upper 6.6e-8 dB 是它自己累積和的相消誤差，不是分析器的）。
   - 頻帶：主通道 M = [CF − Span/2, CF + Span/2]，Start/Stop 模式 M = [Start, Stop] 且 c = (Start + Stop)/2（capture
     acpr_cplx_2s_startstop_m500_1500_none 證明偏移量從 (Start+Stop)/2 量）；第 k 對 L_k = [c − off_k ∓ AdjBW/2]、U_k = [c + off_k ∓ AdjBW/2]。
   - 比值（A2）：Lower_k／Upper_k = 10·log10(P(L_k)/P(M)) 純功率比，沒有 comm.ACPR 的 Span/AdjBW 正規化（default_none 差 3.01 dB、
     three_pairs 差 1.76 dB 被排除）；Channel Power = 10·log10(P(M)) + 30 dBm（power-density 模式也是 dBm）。
   - 頻帶沒有整個落在 [f_first, f_last] 內 → 只有那個頻帶是 NaN（A4；設定不報錯、不夾），其他頻帶與主通道照算
     （acpr_cplx_2s_beyond_range 的 upper2 [4300 5300]、單邊畫面 acpr_real_1s_2k_none 的 lower2 [−1000 0]）。
   - Filter Shape（A5–A7，9 個 capture ≤ 1.2e-13 dB）：把 PSD 乘上功率權重 W(f)（在 bin 中心取值）再用同一條積分規則、只在頻帶
     [f1, f2] 內積分；中心增益 1（不做能量正規化）；同一個以主通道 Span 為尺度的濾波器搬到每個相鄰頻帶的中心（不是用 AdjBW 當尺度）。
     RRC（Roll-off Factor β = FilterCoeff）：W = |H_RRC|² = 升餘弦響應，符元率 Rs = Span：|f − fc| ≤ (1−β)Rs/2 → 1；到 (1+β)Rs/2 →
     ½(1 + cos(π/(βRs)·(|f − fc| − (1−β)Rs/2)))；之外 0。β = 0 是磚牆 ≡ none（acpr_cplx_2s_default_rrc_0p0 = default_none）。
     Gaussian（BT Product = FilterCoeff）：W = exp(−ln2·((f − fc)/(BT·Span))²)（GMSK 高斯 |H|²，B = BT·Span、T = 1/Span）。
     被排除的假設（ANALYSIS.md §3.2）：|H| 振幅、RC²、Rs = Span/(1+β)、Rs = 2·Span、相鄰頻帶用 AdjBW 尺度、單位能量正規化、
     積分到整個濾波器支撐——最好的也差 0.69 dB。
   - Welch 畫面（WindowLength 1024、50%、SpectralAverages 15）：抓到的畫面是非同步的中間平均狀態，不是 15 段平均（差 17.5 dB），也不是
     λ=(N−1)/(N+1) 的指數平均或任何部分平均（work2/acpr/ema_test.py 量過 ≥ 9.5 dB）；acpr_cplx_welch1024_psd_default_none 的量測
     從它存下的畫面用同一條規則重算完全相同（0 / 0 / 1.4e-14 dB）；acpr_cplx_welch1024_psd_three_pairs_none 的畫面和量測是在不同
     平均狀態抓的（差 7.2 dB），無法評估，selftest 以「已知差異」固定住文件化的偏差數字。
B. comm.ACPR 與 bandpower（Signal Processing／Communications Toolbox；tests/matlab_ref/acpr/acpr_ref.json，acpr_ref.m 產生，
   只用 pwelch、bandpower、comm.ACPR、rcosdesign，沒有開 scope）：
   - 'bp' 規則 = bandpower(pxx, f, [f1 f2], 'psd') = comm.ACPR 的頻帶功率：i1 = 最後一個 f ≤ f1 的 bin、i2 = 第一個 f ≥ f2 的 bin
     （往外取），寬度 = f[i+1] − f[i]（最後一個 bin 0），Σ 寬度·pxx；頻帶先夾到 [f(1), f(end)]，夾完沒寬度 → NaN。
     注意這條在分析器的 default_none 上差 0.21 dB（inner-bin 0.039、梯形 2.0e-3），所以 GUI 不能用它，只給 comm.ACPR 對照。
   - 頻寬正規化（comm.ACPR 的輸出）：ACPR_k = (MainBW/AdjBW_k)·P_adj/P_main，dB = 純比值 + 10·log10(Span/AdjBW)；只在 acpr_bwnorm()
     與 comm_acpr() 做，分析器的 acpr() 不做。
   - comm.ACPR：PSD = Welch 平均 |FFT(w·x_seg)|²/(fs·Σw²)，
     視窗 symmetric（hann(L,'symmetric') 等），重疊 = ceil(L·pct/100)，段數 = floor((N − L)/hop) + 1；NFFT 由 FFTLength 決定：預設
     'Next power of 2' = max(256, 2^nextpow2(L))、'Same as segment length' = max(256, L)、'Custom' = 整數，三種 SpectralEstimation
     模式都套；格點置中雙邊；任何頻帶邊界 |f| > fs/2 → comm:system:ACPR:FrequencyValuesOutOfRange。
     MeasurementFilter：DC 置中的 FIR 係數 h[n] 乘 exp(j·π·(2·f_band/fs)·n) 搬到每個頻帶中心，x 各濾一次（因果、零初始狀態），
     主通道用主通道那條、第 k 對用第 k 條。這是 comm.ACPR 的時域做法，和分析器的 Filter Shape（頻域權重）不同。
   - Auto Span（MATLAB 打開量測時自動算頻帶）：x 軸範圍 ∩ Nyquist 範圍 = [xl1, xl2]，g = 寬度、D = 中點：CF = D、Span = g/5、
     Start/Stop = D ∓ g/10、AdjBW = g/10、Offsets = [4, 7]·g/20。雙邊 fs 1e4 → 0／2000／1000／[2000 3500]（＝文件預設）；單邊 → 2500／
     1000／500／[1000 1750]（capture acpr_real_1s_auto1side_none 的 meas_config 正是這組）。
   - 參數檢查（MATLAB 工具列的欄位，訊息是 MATLAB Spectrum Analyzer 介面顯示的訊息原文，中文由簡中轉繁體）：Num Pairs 不在 1..64 → invalidNumOffsets；
     Offsets 長度 ≠ Num Pairs 或含非有限值 → invalidACPROffsets（MATLAB 不檢查正負，負的只是上下對調）；Span 非有限正數 → invalidSpan；
     CF／Start／Stop 非有限 → invalidCenterFrequency／invalidStartFrequency／invalidStopFrequency；Filter 係數不在 [0, 1] →
     invalidFilterCoeff；給了 nyquist 範圍而主通道超出 → invalidSpanAndCenterFrequency。

未定／自行決定（分析器沒驗證到的，採用推定出來的／預設行為並說明）：
- 頻帶邊界落在 (f_first − Δf/2, f_first) 或 (f_last, f_last + Δf/2)（半個 bin 的灰色地帶）：沒有 capture 蓋到；這裡照 A4 的字面
  「不在 [f_first, f_last] 內就 NaN」。邊界剛好等於 f_first／f_last 可以算（單邊 [0, x] 只含半個 DC bin，和分析器 OBW 的 [0 5000] 一致）。
- Auto Span 的觸發時機：acpr_cplx_2s_autospan_defaults 開啟 ACPR 時沒有重算（留著前一個 capture 的 CF 1250），obw_real_1s_autospan_defaults
  有；觸發條件未解。auto_span() 只提供公式，GUI 何時套用自己決定。
- Welch 畫面狀態（見 A 最後一點）：不可重現，selftest 用存下的畫面。
- Gaussian 的 BT = 0（MATLAB 的欄位允許 0..1）：W 退化成只在 f = fc 的 bin 中心為 1、其餘 0（極限形式），沒有 capture；RRC β = 0 有 capture。
- 'scope' 規則要求均勻格點（Δf = (f_end − f_1)/(n − 1)，每個間距差 ≤ 1e-6·Δf，否則 ValueError）；dsv_spectrum 的格點一定均勻。
- 'bp'／'in'／'tz' 三條工具箱規則保留（有 MATLAB 參考值），rule 參數選用；預設 'scope'。
- 輸入檢查（DSV 自己的）：f 與 pxx 實數、1-D、同長度，f 有限且嚴格遞增，pxx 有限且 ≥ 0，否則 ValueError（這些是呼叫端 bug，不能悄悄
  回 NaN）；(n,1)／(1,n) 可以 squeeze 的照收；空的 PSD（welch 資料不夠一段）→ 全部 NaN 不報錯。Start/Stop 模式 Stop ≤ Start →
  ACPRError dsv:invalidStartStop；只給 start 或 stop 其中一個 → invalidStopFrequency／invalidStartFrequency（validate=False 也擋）。
  二維的 offsets → invalidACPROffsets（MATLAB 要的是向量）。
- Adjacent BW 非有限正數：MATLAB 會報錯但用的是中心頻率的訊息，這裡用自己的識別碼 invalidAdjacentBW。
- 工作量上限（DSV 自己的，防止當掉）：PSD 格點超過 2^24 個 bin、comm_acpr 的 NFFT 超過 2^24、量測濾波器卷積 N·M 超過 2^32 →
  ACPRError dsv:tooLarge（MAX_ELEMENTS）。
- comm_acpr 的參數檢查：comm.ACPR 用 validateattributes（泛用訊息），這裡用 dsv:comm:* 識別碼與自己的訊息；hop ≥ 1、L ≤ N、'Custom'
  NFFT ≥ L；(n,1) 欄向量 squeeze 後照收（MATLAB 要 column vector，訊息照抄）；整數陣列轉 float 照收（MATLAB 丟 InvalidInput，文件化差異）；
  其餘 InvalidInput 條件（長度 < 2、含 NaN／Inf、真的二維）照 MATLAB 丟。預設 FFTLength 補零到 2 的冪的路徑（L 不是 2 的冪）沒有
  MATLAB 數值（參考全是 L = 1024），規則照 comm.ACPR 的定義。
- 沒做：comm.ACPR 的 'Specify frequency resolution' 模式（含它的錯誤檢查）、MaxHold、NormalizedFrequency，
  Hann／Hamming／Blackman／矩形以外的 symmetric 視窗；分析器的 FrequencyOffset ≠ 0 與多通道（MeasurementChannel）沒有 capture。
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

import numpy as np

# spectrumAnalyzer ChannelMeasurements 的預設（＝文件 ChannelMeasurementsConfiguration）
DEFAULT_SPAN = 2000.0
DEFAULT_CENTER = 0.0
DEFAULT_START = -1000.0
DEFAULT_STOP = 1000.0
DEFAULT_ADJ_BW = 1000.0
DEFAULT_OFFSETS = (2000.0, 3500.0)
DEFAULT_NUM_OFFSETS = 2
MAX_NUM_OFFSETS = 64
DEFAULT_FILTER_COEFF = 0.5
FILTER_SHAPES = ("none", "rrc", "gaussian")
RULES = ("scope", "bp", "in", "tz")           # 'scope' = 分析器實測規則（預設）；其餘三條有 MATLAB 函式參考值
MATLAB_RULES = ("bp", "in", "tz")
DEFAULT_RULE = "scope"
POWER_UNITS = ("dBm", "dBW", "Watts")
DISPLAY_UNITS = ("dBm", "dBW", "Watts", "dBm/Hz", "dBW/Hz", "Watts/Hz")   # 分析器 SpectrumUnits 這裡能換算的（dBFS 要 full scale，不收）
COMM_WINDOWS = ("hann", "hamming", "blackman", "rectangular")     # comm.ACPR 清單裡這裡有做的（symmetric）
COMM_MIN_NFFT = 256
COMM_FFT_LENGTHS = ("nextpow2", "same")                            # comm.ACPR FFTLength：'Next power of 2'（預設）、'Same as segment length'；整數 = 'Custom'
SCOPE_MIN_NFFT = 1024                                              # 分析器 FFTLengthSource auto：NFFT = max(1024, 視窗長度)（實測規則 S2）
MAX_ELEMENTS = 1 << 24                                             # DSV 工作量上限（格點 bin 數、NFFT）
MAX_CONV_WORK = 1 << 32                                            # DSV 工作量上限（量測濾波器卷積 N·M）
GRID_RTOL = 1e-6                                                   # 'scope' 規則的格點均勻度容忍（相對 Δf）


class ACPRError(ValueError):
    """MATLAB 的錯誤對應到 Python：matlab_id 是 MATLAB 的識別碼（或工具列欄位錯誤的代號），str() 是英文原文，zh 是繁體中文。
    識別碼以 'dsv:' 開頭的是 DSV 自己加的檢查（MATLAB 沒有專屬訊息，或是用 validateattributes 的泛用訊息）。"""

    def __init__(self, matlab_id: str, en: str, zh: str):
        super().__init__(en)
        self.matlab_id = matlab_id
        self.en = en
        self.zh = zh


_ERRORS: Dict[str, Tuple[str, str]] = {
    # spectrumAnalyzer 工具列（英文照 MATLAB 介面顯示的訊息，中文由簡中轉繁體）
    "invalidNumOffsets": ("Enter number of ACPR offsets as a finite positive real scalar between 1 and 64.",
                          "請以 1 到 64 之間的有限正實數純量輸入 ACPR 偏移量的數目。"),
    "invalidACPROffsets": ("Enter ACPR offsets as a finite positive real vector with length equal to the specified number of ACPR Offsets.",
                           "請以長度等於指定 ACPR 偏移量數目的有限正實數向量輸入 ACPR 偏移量。"),
    "invalidSpan": ("Enter span as a finite positive real scalar.", "請以有限正實數純量輸入跨度。"),
    "invalidCenterFrequency": ("Enter center frequency as a finite real scalar.", "請以有限實數純量輸入中心頻率。"),
    "invalidStartFrequency": ("Enter start frequency as a finite real scalar.", "請以有限實數純量輸入開始頻率。"),
    "invalidStopFrequency": ("Enter stop frequency as a finite real scalar.", "請以有限實數純量輸入停止頻率。"),
    "invalidFilterCoeff": ("Enter filter coefficient as a finite nonnegative real scalar between 0 and 1.",
                           "請以 0 到 1 之間的有限非負實數純量輸入濾波器係數。"),
    "invalidSpanAndCenterFrequency": ("The interval [{0}, {1}] {2}Hz defined by the frequency span and center frequency exceeds the "
                                      "Nyquist frequency limits which equal [{3}, {4}] {5}Hz.",
                                      "頻率跨度與中心頻率定義的區間 [{0}, {1}] {2}Hz 超出 Nyquist 頻率範圍 [{3}, {4}] {5}Hz。"),
    # DSV 自己的（MATLAB 對 Adjacent BW 報錯時用的是 invalidCenterFrequency 的訊息；Start ≥ Stop MATLAB 不檢查；工作量上限）
    "invalidAdjacentBW": ("Enter adjacent channel bandwidth as a finite positive real scalar.", "請以有限正實數純量輸入相鄰頻寬。"),
    "dsv:invalidStartStop": ("Stop frequency must be greater than start frequency.", "停止頻率必須大於開始頻率。"),   # ＝dsv_chmeas StartStopOrder
    "dsv:tooLarge": ("The requested computation needs {0} elements ({1}), more than the DSV limit of {2}; reduce the FFT length, "
                     "window length or filter length.",
                     "這次計算需要 {0} 個元素（{1}），超過 DSV 的上限 {2}；請縮小 FFT 長度、視窗長度或濾波器長度。"),
    # comm.ACPR（英文照 MATLAB 的錯誤訊息；MATLAB 這部分只有英文，中文是自己翻的）
    "comm:system:ACPR:FrequencyValuesOutOfRange": (
        "The specified measurement bands are outside the Nyquist interval of [-SampleRate/2 SampleRate/2] when NormalizedFrequency "
        "is false, or [-1 1] when NormalizedFrequency is true.",
        "指定的量測頻帶超出 Nyquist 區間：NormalizedFrequency 為 false 時是 [-SampleRate/2 SampleRate/2]，為 true 時是 [-1 1]。"),
    "comm:system:ACPR:InvalidInput": ("The input must be a double or single precision, column vector with more than 1 element.",
                                      "輸入必須是 double 或 single 精度、元素多於 1 個的行向量（column vector）。"),
    "comm:system:ACPR:InvalidAdjacentMeasurementBandwidthLength": (
        "The AdjacentMeasurementBandwidth property must be a scalar or a row vector with a length equal to the AdjacentChannelOffset "
        "property vector length.",
        "AdjacentMeasurementBandwidth 必須是純量，或長度等於 AdjacentChannelOffset 向量長度的向量。"),
    # comm.ACPR 屬性檢查（MATLAB 用 validateattributes；MATLAB 訊息是泛用文字，這裡是 DSV 自己寫的）
    "dsv:comm:SampleRate": ("SampleRate must be a finite positive real scalar.", "SampleRate（取樣率）必須是有限正實數純量。"),
    "dsv:comm:MainChannelFrequency": ("MainChannelFrequency must be a finite real scalar.", "MainChannelFrequency（主通道頻率）必須是有限實數純量。"),
    "dsv:comm:MainMeasurementBandwidth": ("MainMeasurementBandwidth must be a finite positive real scalar.",
                                          "MainMeasurementBandwidth（主通道量測頻寬）必須是有限正實數純量。"),
    "dsv:comm:AdjacentChannelOffset": ("AdjacentChannelOffset must be a non-empty vector of finite real values.",
                                       "AdjacentChannelOffset（相鄰通道偏移）必須是非空的有限實數向量。"),
    "dsv:comm:AdjacentMeasurementBandwidth": ("AdjacentMeasurementBandwidth must contain finite positive real values.",
                                              "AdjacentMeasurementBandwidth（相鄰通道量測頻寬）必須是有限正實數。"),
    "dsv:comm:SegmentLength": ("SegmentLength must be a positive integer not larger than the input length ({0}).",
                               "SegmentLength（段長）必須是不大於輸入長度（{0}）的正整數。"),
    "dsv:comm:OverlapPercentage": ("OverlapPercentage must be in [0, 100) and leave a hop of at least one sample "
                                   "(ceil(SegmentLength*pct/100) < SegmentLength).",
                                   "OverlapPercentage（重疊百分比）必須在 [0, 100) 內，且 ceil(段長·pct/100) 必須小於段長（hop ≥ 1）。"),
    "dsv:comm:FFTLength": ("FFTLength must be 'nextpow2', 'same' or a positive integer not smaller than SegmentLength.",
                           "FFTLength 必須是 'nextpow2'、'same' 或不小於段長的正整數。"),
    "dsv:comm:MeasurementFilter": ("MeasurementFilter must be a non-empty vector of finite coefficients.",
                                   "MeasurementFilter（量測濾波器）必須是非空的有限係數向量。"),
}


def _err(matlab_id: str, *args) -> ACPRError:
    en, zh = _ERRORS[matlab_id]
    return ACPRError(matlab_id, en.format(*args), zh.format(*args))


def _finite_scalar(v) -> bool:
    if isinstance(v, (bool, np.bool_, str, bytes)):
        return False
    try:
        return bool(np.isfinite(float(v)))
    except (TypeError, ValueError):
        return False


def _squeeze_vector(a: np.ndarray) -> Optional[np.ndarray]:
    """(n,)／(n,1)／(1,n)／純量 → 1-D；真的二維 → None。"""
    if a.ndim > 1:
        a = np.squeeze(a)
        if a.ndim > 1:
            return None
    return np.atleast_1d(a)


def _as_vector(a: np.ndarray, name: str) -> np.ndarray:
    """實數 1-D 向量（(n,1)／(1,n) 這種可以 squeeze 的也收；真的二維 → ValueError）。"""
    a = np.asarray(a, dtype=float)
    v = _squeeze_vector(a)
    if v is None:
        raise ValueError(f"{name} must be a 1-D vector, got shape {a.shape} ／ {name} 必須是一維向量")
    return v.ravel()


def _check_grid(f) -> np.ndarray:
    """頻率格點 f：實數、1-D、有限、嚴格遞增、不超過 MAX_ELEMENTS 個 bin（否則 ValueError／ACPRError；複數不接受，不能悄悄丟掉虛部）。"""
    fa = np.asarray(f)
    if fa.size > MAX_ELEMENTS:                                     # 先看大小再 ravel（不複製就擋下來）
        raise _err("dsv:tooLarge", fa.size, "frequency grid bins", MAX_ELEMENTS)
    if np.iscomplexobj(fa):
        raise ValueError("frequency grid f must be real, not complex ／ 頻率格點 f 必須是實數")
    f = _as_vector(fa, "f")
    if not np.all(np.isfinite(f)):
        raise ValueError("frequency grid f must be finite ／ 頻率格點 f 必須是有限值")
    if f.size >= 2 and not np.all(np.diff(f) > 0):
        raise ValueError("frequency grid f must be strictly increasing ／ 頻率格點 f 必須嚴格遞增")
    return f


def _check_psd(f, pxx) -> Tuple[np.ndarray, np.ndarray]:
    """f 與 pxx 一起檢查：pxx 實數、1-D、有限、≥ 0、長度 = f 的長度（長度不同、NaN、負值都是呼叫端 bug → ValueError，不回 NaN）。"""
    f = _check_grid(f)
    pa = np.asarray(pxx)
    if np.iscomplexobj(pa):
        raise ValueError("pxx must be a real PSD, not complex ／ pxx 必須是實數 PSD")
    p = _as_vector(pa, "pxx")
    if p.size != f.size:
        raise ValueError(f"pxx and f must have the same length (got {p.size} and {f.size}) ／ pxx 與 f 長度必須相同")
    if not np.all(np.isfinite(p)):
        raise ValueError("pxx must be finite (no NaN/Inf) ／ pxx 必須是有限值")
    if p.size and np.any(p < 0.0):
        raise ValueError("pxx must be non-negative (a power spectral density) ／ pxx 不能是負值")
    return f, p


def _uniform_df(f: np.ndarray) -> float:
    """'scope' 規則的 Δf：(f_end − f_1)/(n − 1)；格點不均勻（任一間距和 Δf 差超過 GRID_RTOL·Δf）→ ValueError；n < 2 → NaN。"""
    if f.size < 2:
        return math.nan
    df = (float(f[-1]) - float(f[0])) / (f.size - 1)
    if float(np.max(np.abs(np.diff(f) - df))) > GRID_RTOL * df:
        raise ValueError("the 'scope' rule needs a uniform frequency grid ／ 'scope' 規則需要均勻的頻率格點")
    return df


def _offsets_vector(offsets) -> np.ndarray:
    """ACPR Offsets：實數向量（純量、(n,1)、(1,n) 也收）；複數、非數值、真的二維 → invalidACPROffsets。"""
    a = np.asarray(offsets)
    if a.dtype == bool or np.iscomplexobj(a) or not (a.size == 0 or np.issubdtype(a.dtype, np.number)):
        raise _err("invalidACPROffsets")
    v = _squeeze_vector(a.astype(float))
    if v is None:
        raise _err("invalidACPROffsets")
    return v.ravel()


def scope_nfft(window_length: int) -> int:
    """分析器 FFTLengthSource = auto 的 FFT 長度：max(1024, 視窗長度)（實測規則 S2：L 1000 → 1024 bins、1999 → 1999、8192 → 8192；
    scope_state 讀回的 FFTLength／RBW 是沒在用的屬性值）。超過 MAX_ELEMENTS → ACPRError dsv:tooLarge。"""
    if not _finite_scalar(window_length) or float(window_length) != int(window_length) or int(window_length) < 1:
        raise ValueError(f"window_length must be a positive integer, got {window_length!r} ／ 視窗長度必須是正整數")
    n = max(SCOPE_MIN_NFFT, int(window_length))
    if n > MAX_ELEMENTS:
        raise _err("dsv:tooLarge", n, "FFT length", MAX_ELEMENTS)
    return n


def filter_shape(shape: str, coeff: float = DEFAULT_FILTER_COEFF) -> str:
    """Filter Shape 的檢查：回傳正規化的名稱 'none'／'rrc'／'gaussian'（大小寫、None 都收）；係數不在 [0, 1] → invalidFilterCoeff。"""
    s = str(shape or "none").strip().lower()
    if s not in FILTER_SHAPES:
        raise ValueError(f"filter_shape must be one of {FILTER_SHAPES}, got {shape!r}")
    if not _finite_scalar(coeff) or not (0.0 <= float(coeff) <= 1.0):
        raise _err("invalidFilterCoeff")
    return s


def filter_weights(f, fc: float, shape: str = "none", coeff: float = DEFAULT_FILTER_COEFF, span: float = DEFAULT_SPAN) -> Optional[np.ndarray]:
    """分析器 Filter Shape 的功率權重 W(f)（規則 A5–A7；在給的頻率點取值，中心增益 1）。'none' → None（不用乘）。
    'rrc'：升餘弦功率響應 |H_RRC|²，符元率 Rs = span（主通道 Span）、滾降 β = coeff：|Δ| ≤ (1−β)Rs/2 → 1，到 (1+β)Rs/2 → 餘弦過渡，之外 0；
           β = 0 是 |Δ| ≤ Rs/2 的磚牆。
    'gaussian'：exp(−ln2·(Δ/(BT·span))²)，BT = coeff；BT = 0 退化成只有 Δ = 0 的點是 1（未定，見模組說明）。
    span 必須是有限正數（invalidSpan）。GUI 畫濾波器形狀時也用這支。"""
    s = filter_shape(shape, coeff)
    if s == "none":
        return None
    fa = np.asarray(f, dtype=float)
    if np.iscomplexobj(f):
        raise ValueError("f must be real ／ f 必須是實數")
    if not _finite_scalar(span) or not float(span) > 0.0:
        raise _err("invalidSpan")
    rs = float(span)
    d = np.abs(fa - float(fc))
    if s == "rrc":
        beta = float(coeff)
        flat_edge = (1.0 - beta) * rs / 2.0
        outer_edge = (1.0 + beta) * rs / 2.0
        w = np.zeros(fa.shape)
        w[d <= flat_edge] = 1.0
        if beta > 0.0:
            roll = (d > flat_edge) & (d <= outer_edge)
            w[roll] = 0.5 * (1.0 + np.cos((np.pi / (beta * rs)) * (d[roll] - flat_edge)))
        return w
    bw = float(coeff) * rs
    if bw == 0.0:
        return (d == 0.0).astype(float)
    with np.errstate(over="ignore"):                               # 離中心極遠的 bin：(Δ/B)² 溢位成 inf → exp(−inf) = 0，正確
        return np.exp(-math.log(2.0) * (d / bw) ** 2)


def validate_params(center: Optional[float] = DEFAULT_CENTER, span: Optional[float] = DEFAULT_SPAN, adj_bw: float = DEFAULT_ADJ_BW,
                    offsets: Sequence[float] = DEFAULT_OFFSETS, num_offsets: Optional[int] = None,
                    start: Optional[float] = None, stop: Optional[float] = None,
                    nyquist: Optional[Tuple[float, float]] = None) -> np.ndarray:
    """照 MATLAB 工具列欄位的規則檢查參數，回傳 offsets（float 1-D 陣列）。start 與 stop 都給 → Start/Stop 模式（不檢查 span／center；
    Stop ≤ Start → dsv:invalidStartStop，這條是 DSV 自己加的）。"""
    off = _offsets_vector(offsets)
    n = off.size if num_offsets is None else num_offsets
    if not _finite_scalar(n) or float(n) != int(n) or not (1 <= int(n) <= MAX_NUM_OFFSETS):
        raise _err("invalidNumOffsets")
    if off.size != int(n) or not np.all(np.isfinite(off)):
        raise _err("invalidACPROffsets")
    if start is not None or stop is not None:
        if not _finite_scalar(start):
            raise _err("invalidStartFrequency")
        if not _finite_scalar(stop):
            raise _err("invalidStopFrequency")
        lo, hi = float(start), float(stop)
        if not hi > lo:
            raise _err("dsv:invalidStartStop")
    else:
        if not _finite_scalar(span) or not float(span) > 0:
            raise _err("invalidSpan")
        if not _finite_scalar(center):
            raise _err("invalidCenterFrequency")
        lo, hi = float(center) - float(span) / 2.0, float(center) + float(span) / 2.0
    if not _finite_scalar(adj_bw) or not float(adj_bw) > 0:
        raise _err("invalidAdjacentBW")
    if nyquist is not None and (lo < nyquist[0] or hi > nyquist[1]):
        raise _err("invalidSpanAndCenterFrequency", f"{lo:g}", f"{hi:g}", "", f"{nyquist[0]:g}", f"{nyquist[1]:g}", "")
    return off


def bands(center: float = DEFAULT_CENTER, span: float = DEFAULT_SPAN, adj_bw: float = DEFAULT_ADJ_BW,
          offsets: Sequence[float] = DEFAULT_OFFSETS, start: Optional[float] = None, stop: Optional[float] = None) -> Dict[str, np.ndarray]:
    """主通道與每一對相鄰通道的頻帶（Hz）。回傳 dict：main (2,)、lower (n, 2)、upper (n, 2)、center。
    Span/CF 模式：main = [CF − Span/2, CF + Span/2]；Start/Stop 模式：main = [Start, Stop]、CF = (Start + Stop)/2（分析器實測 A1）。
    lower_k = CF − off_k ∓ AdjBW/2、upper_k = CF + off_k ∓ AdjBW/2。只給 start 或 stop 其中一個 → invalidStopFrequency／invalidStartFrequency；
    其餘純幾何，不檢查（檢查在 validate_params）。"""
    off = _offsets_vector(offsets)
    bw = float(adj_bw)
    if start is not None or stop is not None:
        if start is None:
            raise _err("invalidStartFrequency")
        if stop is None:
            raise _err("invalidStopFrequency")
        lo, hi = float(start), float(stop)
        c = (lo + hi) / 2.0
    else:
        c = float(center)
        lo, hi = c - float(span) / 2.0, c + float(span) / 2.0
    lower = np.column_stack([c - off - bw / 2.0, c - off + bw / 2.0])
    upper = np.column_stack([c + off - bw / 2.0, c + off + bw / 2.0])
    return {"main": np.array([lo, hi]), "lower": lower, "upper": upper, "center": c}


def _scope_power(f: np.ndarray, p: np.ndarray, df: float, a: float, b: float,
                 weight: Optional[Callable[[np.ndarray], np.ndarray]] = None) -> float:
    """分析器規則 A1：分段常數 PSD（bin k 佔 [f_k − Δf/2, f_k + Δf/2]）在 [a, b] 上的精確積分，兩端 bin 按比例、中間整 bin 直接相加。
    [a, b] 沒有整個落在 [f_1, f_end] 內（或 a ≥ b、格點少於 2 點）→ NaN。weight(f_slice) 給 Filter Shape 的權重（只在用到的 bin 上算）。"""
    if f.size < 2 or not math.isfinite(df) or a < f[0] or b > f[-1] or not a < b:
        return math.nan
    half = df / 2.0
    lower_edges = f - half
    n = f.size
    i1 = min(max(int(np.searchsorted(lower_edges, a, side="right")) - 1, 0), n - 1)
    i2 = min(max(int(np.searchsorted(lower_edges, b, side="right")) - 1, 0), n - 1)
    seg = p[i1:i2 + 1]
    if weight is not None:
        seg = seg * weight(f[i1:i2 + 1])
    if i1 == i2:
        return float(seg[0] * (b - a))
    head = seg[0] * (f[i1] + half - a)
    tail = seg[-1] * (b - (f[i2] - half))
    return float(head + tail + df * float(np.sum(seg[1:-1])))


def _band_power(f: np.ndarray, p: np.ndarray, aux, f1: float, f2: float, rule: str,
                weight: Optional[Callable[[np.ndarray], np.ndarray]] = None) -> Tuple[float, bool]:
    """band_power 的核心（f、p 已由 _check_psd 檢查過；aux = 'scope' 的 Δf／'bp' 的 widths = [diff(f), 0]，給 acpr() 在很多頻帶上重複用）。
    回傳 (功率, 頻帶是否有邊界在格點外)。空格點 → NaN。weight 是 Filter Shape 的權重函數（'scope' 只在帶內 bin 上算，其餘規則整條乘）。"""
    if f.size == 0:
        return math.nan, True
    f1, f2 = float(f1), float(f2)
    clipped = bool(f1 < f[0] or f1 > f[-1] or f2 < f[0] or f2 > f[-1])
    if rule == "scope":
        return _scope_power(f, p, float(aux), f1, f2, weight), clipped
    if weight is not None:
        p = p * weight(f)
    if rule == "in":
        if f.size < 2:
            return math.nan, clipped
        i1 = int(np.searchsorted(f, f1, side="left"))
        i2 = int(np.searchsorted(f, f2, side="right"))
        return float(np.sum(p[i1:i2]) * (f[1] - f[0])), clipped
    lo, hi = max(f1, f[0]), min(f2, f[-1])
    if not lo < hi:
        return math.nan, clipped
    if rule == "bp":
        i1 = int(np.searchsorted(f, lo, side="right")) - 1
        i2 = int(np.searchsorted(f, hi, side="left"))
        if aux is None:
            aux = np.append(np.diff(f), 0.0)
        return float(np.dot(aux[i1:i2 + 1], p[i1:i2 + 1])), clipped
    if rule == "tz":
        i1 = int(np.searchsorted(f, lo, side="right"))
        i2 = int(np.searchsorted(f, hi, side="left"))
        ff = np.concatenate([[lo], f[i1:i2], [hi]])
        v = np.interp(ff, f, p)
        return float(np.sum(np.diff(ff) * (v[1:] + v[:-1]) / 2.0)), clipped
    raise ValueError(f"rule must be one of {RULES}, got {rule!r}")


def _rule_aux(f: np.ndarray, rule: str):
    if not f.size:
        return None
    if rule == "scope":
        return _uniform_df(f)
    if rule == "bp":
        return np.append(np.diff(f), 0.0)
    return None


def band_power(f, pxx, f1: float, f2: float, rule: str = DEFAULT_RULE) -> Tuple[float, bool]:
    """頻帶 [f1, f2] 的功率（和 pxx·Δf 同單位，PSD 是 W/Hz 時就是 W），回傳 (功率, 是否有邊界超出格點)。
    'scope'：分析器規則——分段常數 PSD（bin 佔 [f_k − Δf/2, f_k + Δf/2]）的精確積分；頻帶沒有整個在 [f_1, f_end] 內 → NaN。
    'bp'：bandpower／comm.ACPR 規則——夾到 [f(1), f(end)]，i1 = 最後一個 f ≤ f1、i2 = 第一個 f ≥ f2，Σ 寬度·pxx（最後一個 bin 寬度 0），
          夾完沒寬度 → NaN。
    'in'：只加 f1 ≤ f ≤ f2 的 bin，乘 Δf = f(2) − f(1)；不夾，沒有 bin → 0。
    'tz'：夾到格點，f1、格點內的 f、f2 上線性內插後梯形積分；夾完沒寬度 → NaN。
    f／pxx 必須是實數 1-D、同長度、f 嚴格遞增、pxx 有限非負；f1、f2 必須有限且 f1 < f2（否則 ValueError）。"""
    if rule not in RULES:
        raise ValueError(f"rule must be one of {RULES}, got {rule!r}")
    if not (_finite_scalar(f1) and _finite_scalar(f2) and float(f1) < float(f2)):
        raise ValueError(f"band edges must be finite with f1 < f2 (got {f1!r}, {f2!r}) ／ 頻帶邊界必須有限且 f1 < f2")
    f, p = _check_psd(f, pxx)
    return _band_power(f, p, _rule_aux(f, rule), f1, f2, rule)


def power_in_units(P, units: str = "dBm"):
    """W → 'dBm'（10·log10(P) + 30）／'dBW'（10·log10(P)）／'Watts'（原值）。P ≤ 0 或 NaN 的 dB 值是 −Inf／NaN。"""
    P = np.asarray(P, dtype=float)
    u = str(units)
    if u.lower() == "watts":
        return P
    with np.errstate(divide="ignore", invalid="ignore"):
        db = 10.0 * np.log10(P)
    if u.lower() == "dbm":
        return db + 30.0
    if u.lower() == "dbw":
        return db
    raise ValueError(f"units must be one of {POWER_UNITS}, got {units!r}")


def psd_from_power(power, w, fs: float):
    """dsv_spectrum.welch 的 'power'（每 bin 功率，|X|²/(Σw)²）→ 'psd'（|X|²/(fs·Σw²)），用的是同一支視窗 w。
    有補零（NFFT > L）時仍然正確；不能用 power/NENBW 那種只在 NFFT = L 成立的換法。等於 power / RBW（RBW = fs·Σw²/(Σw)²）。"""
    w = np.asarray(w, dtype=float)
    s1 = float(np.sum(w)) ** 2
    s2 = float(np.sum(w * w)) * float(fs)
    return np.asarray(power, dtype=float) * (s1 / s2)


def psd_from_display(values, units: str = "dBm", rbw: Optional[float] = None) -> np.ndarray:
    """分析器畫面上的值 → 量測用的 PSD（W/Hz；分析器實測 A3／O1）：'dBm' → 10^((v−30)/10)/RBW、'dBW' → 10^(v/10)/RBW、'Watts' → v/RBW
    （power 模式要除 RBW = ENBW，dsv_spectrum.welch 的 rbw）；'dBm/Hz'／'dBW/Hz'／'Watts/Hz' 已經是密度，不除。
    power 模式沒給 rbw、或單位不在 DISPLAY_UNITS（dBFS 要 full scale）→ ValueError。"""
    v = np.asarray(values, dtype=float)
    u = str(units).strip()
    key = u.lower()
    if u not in DISPLAY_UNITS and key not in tuple(x.lower() for x in DISPLAY_UNITS):
        raise ValueError(f"units must be one of {DISPLAY_UNITS}, got {units!r}")
    density = key.endswith("/hz")
    base = key[:-3] if density else key
    if base == "dbm":
        lin = 10.0 ** ((v - 30.0) / 10.0)
    elif base == "dbw":
        lin = 10.0 ** (v / 10.0)
    else:
        lin = v
    if density:
        return lin
    if rbw is None or not _finite_scalar(rbw) or not float(rbw) > 0.0:
        raise ValueError("power-mode display values need the RBW (ENBW, Hz) to become a PSD ／ power 模式要給 RBW 才能換成 PSD")
    return lin / float(rbw)


def acpr(f, pxx, center: float = DEFAULT_CENTER, span: float = DEFAULT_SPAN, adj_bw: float = DEFAULT_ADJ_BW,
         offsets: Sequence[float] = DEFAULT_OFFSETS, *, start: Optional[float] = None, stop: Optional[float] = None,
         num_offsets: Optional[int] = None, shape: str = "none", coeff: float = DEFAULT_FILTER_COEFF,
         rule: str = DEFAULT_RULE, units: str = "dBm", nyquist: Optional[Tuple[float, float]] = None,
         validate: bool = True) -> Dict[str, Any]:
    """spectrumAnalyzer 的 ACPR 量測：PSD pxx（W/Hz，均勻遞增格點 f；power 模式的畫面先用 psd_from_display／psd_from_power 換成 PSD）
    上的主通道功率與每對相鄰通道的純功率比，預設用分析器實測規則 'scope'（含 Filter Shape 'none'／'rrc'／'gaussian' 的頻域權重）。
    回傳 dict：n、center、main_band (2,)、lower_bands／upper_bands (n, 2)、main_power／lower_power／upper_power（W）、
    lower_dBc／upper_dBc（10·log10(P_adj/P_main)）、main_clipped／lower_clipped／upper_clipped（頻帶有邊界在格點外）、
    channel_power（units 單位）、units、rule、shape、coeff、bwnorm_dB（這裡是 0；acpr_bwnorm 會填 10·log10(Span/AdjBW)）。
    沒有整個在格點內的頻帶 → 那個頻帶 NaN（'bp'／'tz' 則夾到格點、整個在外才 NaN）；空的 PSD → 全部 NaN。
    f／pxx 必須是實數 1-D、同長度、f 嚴格遞增、pxx 有限非負（否則 ValueError）；validate=True 時參數照 MATLAB 工具列欄位的規則檢查（ACPRError）；
    shape／coeff 一定會檢查（算權重需要）。"""
    shp = filter_shape(shape, coeff)
    if validate:
        off = validate_params(center, span, adj_bw, offsets, num_offsets, start, stop, nyquist)
    else:
        off = _offsets_vector(offsets)
    if rule not in RULES:
        raise ValueError(f"rule must be one of {RULES}, got {rule!r}")
    f, p = _check_psd(f, pxx)
    b = bands(center, span, adj_bw, off, start, stop)
    n = off.size
    aux = _rule_aux(f, rule)
    main_bw = float(b["main"][1] - b["main"][0])                  # Span（Start/Stop 模式 = Stop − Start）：濾波器的尺度

    def weight_at(fc: float) -> Optional[Callable[[np.ndarray], np.ndarray]]:
        if shp == "none":
            return None
        return lambda ff: filter_weights(ff, fc, shp, coeff, main_bw)

    main_p, main_c = _band_power(f, p, aux, b["main"][0], b["main"][1], rule, weight_at(b["center"]))
    lower_p = np.empty(n)
    upper_p = np.empty(n)
    lower_c = np.zeros(n, dtype=bool)
    upper_c = np.zeros(n, dtype=bool)
    for k in range(n):
        lower_p[k], lower_c[k] = _band_power(f, p, aux, b["lower"][k, 0], b["lower"][k, 1], rule, weight_at(b["center"] - off[k]))
        upper_p[k], upper_c[k] = _band_power(f, p, aux, b["upper"][k, 0], b["upper"][k, 1], rule, weight_at(b["center"] + off[k]))
    with np.errstate(divide="ignore", invalid="ignore"):
        lower_db = 10.0 * np.log10(lower_p / main_p)
        upper_db = 10.0 * np.log10(upper_p / main_p)
    return {"n": int(n), "center": b["center"], "main_band": b["main"], "lower_bands": b["lower"], "upper_bands": b["upper"],
            "offsets": off, "main_power": main_p, "lower_power": lower_p, "upper_power": upper_p,
            "lower_dBc": lower_db, "upper_dBc": upper_db, "main_clipped": main_c, "lower_clipped": lower_c, "upper_clipped": upper_c,
            "channel_power": float(power_in_units(main_p, units)), "units": units, "rule": rule, "shape": shp, "coeff": float(coeff),
            "bwnorm_dB": 0.0}


def acpr_bwnorm(f, pxx, center: float = DEFAULT_CENTER, span: float = DEFAULT_SPAN, adj_bw: float = DEFAULT_ADJ_BW,
                offsets: Sequence[float] = DEFAULT_OFFSETS, **kw) -> Dict[str, Any]:
    """comm.ACPR 式的頻寬正規化 ACPR：和 acpr() 一樣，但 lower_dBc／upper_dBc 加上 10·log10(Span/AdjBW)
    （ACPR = (MainBW/AdjBW)·P_adj/P_main），bwnorm_dB 記下加了多少；Start/Stop 模式的 Span = Stop − Start。
    分析器不做這個正規化（實測差 3.01 dB），GUI 的 ACPR 表要用 acpr()。
    主通道頻寬或 AdjBW 不是有限正數時丟 ValueError（validate=True 時 validate_params 會先擋下）。"""
    r = acpr(f, pxx, center, span, adj_bw, offsets, **kw)
    main_bw = float(r["main_band"][1] - r["main_band"][0])
    abw = float(adj_bw)
    if not (math.isfinite(main_bw) and main_bw > 0.0 and math.isfinite(abw) and abw > 0.0):
        raise ValueError(f"bandwidth normalisation needs a positive main-channel bandwidth and adjacent bandwidth "
                         f"(got {main_bw:g} and {abw:g}) ／ 頻寬正規化需要正的主通道頻寬與相鄰頻寬")
    norm = 10.0 * math.log10(main_bw / abw)
    r["lower_dBc"] = r["lower_dBc"] + norm
    r["upper_dBc"] = r["upper_dBc"] + norm
    r["bwnorm_dB"] = norm
    return r


def auto_span(xlim: Sequence[float], fs: Optional[float] = None, two_sided: bool = True, foffset: float = 0.0) -> Dict[str, Any]:
    """Auto Span（MATLAB 打開量測時自動算頻帶）：x 軸範圖 xlim（給 fs 時先和 Nyquist 範圍 [−fs/2+foffset（單邊 foffset）, fs/2+foffset]
    取交集），g = 寬度、D = 中點 → center D、span g/5、start／stop D ∓ g/10、adj_bw g/10、offsets [g/20·4, g/20·7]。
    分析器實測：單邊 0..5000 開啟量測時寫進設定物件的正是這組（2500／1000／500／[1000 1750]）；但開啟 ACPR 時不一定重算
    （acpr_cplx_2s_autospan_defaults 留著舊的 CF 1250），觸發時機未定。"""
    xl1, xl2 = float(xlim[0]), float(xlim[1])
    if fs is not None:
        lo = (-float(fs) / 2.0 if two_sided else 0.0) + float(foffset)
        hi = float(fs) / 2.0 + float(foffset)
        xl1, xl2 = max(xl1, lo), min(xl2, hi)
    g = xl2 - xl1
    D = (xl1 + xl2) / 2.0
    return {"xlim": (xl1, xl2), "center": D, "span": g / 5.0, "start": D - g / 10.0, "stop": D + g / 10.0, "adj_bw": g / 10.0,
            "offsets": np.array([g / 20.0 * 4.0, g / 20.0 * 7.0])}


def pad_offsets(offsets: Sequence[float], num_offsets: int) -> np.ndarray:
    """Num Pairs 變多時 MATLAB 補 0；變少時截掉後面的。num_offsets 必須是 ≥ 0 的整數（否則 ValueError）。"""
    off = _offsets_vector(offsets)
    if not _finite_scalar(num_offsets) or float(num_offsets) != int(num_offsets) or int(num_offsets) < 0:
        raise ValueError(f"num_offsets must be a non-negative integer, got {num_offsets!r} ／ 對數必須是非負整數")
    n = int(num_offsets)
    return np.concatenate([off, np.zeros(n - off.size)]) if n > off.size else off[:n]


def _symmetric_window(name: str, L: int) -> np.ndarray:
    """comm.ACPR 用的 symmetric 視窗（hann／hamming／blackman 的 'symmetric' 版、rectwin）。"""
    nm = str(name).strip().lower()
    if nm not in COMM_WINDOWS:
        raise NotImplementedError(f"comm.ACPR window {name!r} not implemented; available: {COMM_WINDOWS}")
    if nm == "rectangular" or L == 1:
        return np.ones(L)
    return {"hann": np.hanning, "hamming": np.hamming, "blackman": np.blackman}[nm](L)


def comm_fft_length(segment_length: int, fft_length: Union[str, int, None] = "nextpow2") -> int:
    """comm.ACPR 的 NFFT（FFTLength 屬性）：'nextpow2'（預設，'Next power of 2'）= max(256, 2^nextpow2(L))、
    'same'（'Same as segment length'）= max(256, L)、整數（'Custom'）= 該值（這裡要求 ≥ L，comm 對 NFFT < L 的行為沒驗證）。None = 預設。
    segment_length 必須是 ≥ 1 的整數（否則 ValueError）。"""
    if not _finite_scalar(segment_length) or float(segment_length) != int(segment_length) or int(segment_length) < 1:
        raise ValueError(f"segment_length must be a positive integer, got {segment_length!r} ／ 段長必須是正整數")
    L = int(segment_length)
    if fft_length is None:
        fft_length = "nextpow2"
    if isinstance(fft_length, str):
        key = fft_length.strip().lower().replace(" ", "")
        if key in ("nextpow2", "nextpowerof2"):
            return max(COMM_MIN_NFFT, 1 << (L - 1).bit_length())
        if key in ("same", "sameassegmentlength"):
            return max(COMM_MIN_NFFT, L)
        raise _err("dsv:comm:FFTLength")
    if not _finite_scalar(fft_length) or float(fft_length) != int(fft_length) or int(fft_length) < L:
        raise _err("dsv:comm:FFTLength")
    return int(fft_length)


def _real_values(v, matlab_id: str, positive: bool = False) -> np.ndarray:
    """comm_acpr 的屬性向量：實數（複數也不收）、有限、非空、1-D（純量、(n,1)、(1,n) 可以；真的二維不收）、positive=True 時全部 > 0；
    不合 → ACPRError(matlab_id)。"""
    a = np.asarray(v)
    if np.iscomplexobj(a) or a.dtype == bool or not (a.size == 0 or np.issubdtype(a.dtype, np.number)):
        raise _err(matlab_id)
    vec = _squeeze_vector(a.astype(float)) if a.size else np.zeros(0)
    if vec is None:
        raise _err(matlab_id)
    vec = vec.ravel()
    if vec.size == 0 or not np.all(np.isfinite(vec)) or (positive and not np.all(vec > 0)):
        raise _err(matlab_id)
    return vec


def comm_acpr(x, fs: float, main_freq: float = 0.0, main_bw: float = 50e3, offsets: Sequence[float] = (-100e3, 100e3),
              adj_bw=50e3, *, segment_length: Optional[int] = None, overlap_pct: float = 0.0, window: str = "hamming",
              nfft: Union[str, int, None] = "nextpow2", measurement_filter=None, units: str = "dBm") -> Dict[str, Any]:
    """comm.ACPR（Communications Toolbox）整個流程：x（1-D 或 (n,1)，實數或複數）→ Welch PSD（symmetric 視窗、重疊 ceil(L·pct/100)、置中）
    → 各頻帶功率（'bp' 規則）→ 頻寬正規化 ACPR。offsets 是有號的（comm 的 AdjacentChannelOffset），輸出順序照 offsets。
    segment_length=None ＝ comm 的 'Auto'（整段資料一段、Hamming、0% 重疊）。
    nfft ＝ comm 的 FFTLength：'nextpow2'（預設，和 comm.ACPR 一樣 = max(256, 2^nextpow2(L))）、'same'（max(256, L)）或整數（'Custom'，
    要 ≥ L）。注意 L 不是 2 的冪時預設會補零到下一個 2 的冪（例如 5000 點 → 8192），結果和 'same' 不同。
    measurement_filter：DC 置中 FIR 係數（例如 rcosdesign(β, span, sps, 'sqrt')，可為複數），移到每個頻帶（exp(1i·π·off·n)·h）後各濾一次。
    參數不合 → ACPRError（comm:system:ACPR:* 或 dsv:comm:*；NFFT > 2^24 或卷積 N·M > 2^32 → dsv:tooLarge；見模組說明）。
    回傳 dict：acpr（units='Watts' 是比值，否則 dBc）、main_power、adj_power（units 單位）、main_power_W／adj_power_W、f、psd（主通道那條）、
    bands (1+n, 2)、L、nfft、noverlap、nseg、units。"""
    xa = np.asarray(x)
    xv = _squeeze_vector(xa) if xa.ndim else None
    if (xv is None or xv.size < 2 or xa.dtype == bool or not np.issubdtype(xa.dtype, np.number)
            or not np.all(np.isfinite(xv))):
        raise _err("comm:system:ACPR:InvalidInput")
    x = xv.ravel()
    if not (_finite_scalar(fs) and float(fs) > 0.0):
        raise _err("dsv:comm:SampleRate")
    if not _finite_scalar(main_freq):
        raise _err("dsv:comm:MainChannelFrequency")
    if not (_finite_scalar(main_bw) and float(main_bw) > 0.0):
        raise _err("dsv:comm:MainMeasurementBandwidth")
    off = _real_values(offsets, "dsv:comm:AdjacentChannelOffset")
    abw_in = np.asarray(adj_bw)
    if abw_in.size != 1 and abw_in.size != off.size:
        raise _err("comm:system:ACPR:InvalidAdjacentMeasurementBandwidthLength")
    abw = _real_values(abw_in, "dsv:comm:AdjacentMeasurementBandwidth", positive=True)
    if abw.size == 1:
        abw = np.repeat(abw, off.size)
    fs = float(fs)
    main_bw = float(main_bw)
    centers = np.concatenate([[float(main_freq)], float(main_freq) + off])
    lo = np.concatenate([[float(main_freq) - main_bw / 2.0], float(main_freq) + off - abw / 2.0])
    hi = lo + np.concatenate([[main_bw], abw])
    if np.any(np.abs(hi) > fs / 2.0) or np.any(np.abs(lo) > fs / 2.0):
        raise _err("comm:system:ACPR:FrequencyValuesOutOfRange")
    N = x.size
    if segment_length is None:
        L = N                                                      # 'Auto'：段長 = 資料長度（照 MATLAB comm.ACPR）
    else:
        if (not _finite_scalar(segment_length) or float(segment_length) != int(segment_length)
                or not (1 <= int(segment_length) <= N)):
            raise _err("dsv:comm:SegmentLength", N)
        L = int(segment_length)
    if not _finite_scalar(overlap_pct) or not (0.0 <= float(overlap_pct) < 100.0):
        raise _err("dsv:comm:OverlapPercentage")
    nov = int(math.ceil(float(overlap_pct) / 100.0 * L))
    if nov >= L:                                                   # hop = L − nov 必須 ≥ 1（hop 要當除數）
        raise _err("dsv:comm:OverlapPercentage")
    nf = comm_fft_length(L, nfft)
    if nf > MAX_ELEMENTS:
        raise _err("dsv:tooLarge", nf, "FFT length", MAX_ELEMENTS)
    w = _symmetric_window(window, L)
    cplx = np.iscomplexobj(x)
    if measurement_filter is not None:
        ha = np.asarray(measurement_filter)
        hv = _squeeze_vector(ha) if ha.ndim else None
        if (hv is None or ha.dtype == bool or not np.issubdtype(ha.dtype, np.number) or hv.size == 0
                or not np.all(np.isfinite(hv))):
            raise _err("dsv:comm:MeasurementFilter")
        h = hv.ravel()
        M = h.size
        if N * M > MAX_CONV_WORK:
            raise _err("dsv:tooLarge", N * M, "measurement-filter convolution N*M", MAX_CONV_WORK)
        if M > 1:
            n = np.arange(M)
            norm_off = centers * 2.0 / fs                        # comm：[fc, fc+off]·2/Rs
            # 把濾波器移到每個頻帶：exp(1i·π·off·n)·h，再 filter(b, 1, x)（因果、零初始狀態、輸出 N 點）
            sig = [np.convolve(x, np.exp(1j * ((np.pi * o) * n)) * h)[:N] for o in norm_off]
        else:
            sig = [h[0] * x] * centers.size
        cplx = True
    else:
        sig = [x] * centers.size
    from dsv_spectrum import welch
    xd = complex if cplx else float
    psds = []
    f = None
    nseg = 0
    for k, s in enumerate(sig):
        if k == 0 or measurement_filter is not None:
            r = welch(np.asarray(s, dtype=xd), fs, w, nov, nf, "centered")
            if r["nseg"] == 0:                                     # 參數檢查過後不會發生，留著防呆
                raise ValueError("input shorter than one segment")
            f = r["f"]
            nseg = r["nseg"]
            psds.append(r["psd"])
        else:
            psds.append(psds[0])
    widths = np.append(np.diff(f), 0.0)
    P = np.empty(centers.size)
    for k in range(centers.size):
        a = max(lo[k], f[0])
        b = min(hi[k], f[-1])
        i1 = int(np.searchsorted(f, a, side="right")) - 1
        i2 = int(np.searchsorted(f, b, side="left"))
        P[k] = float(np.dot(widths[i1:i2 + 1], psds[k][i1:i2 + 1]))
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = main_bw / abw * (P[1:] / P[0])
        out_acpr = ratio if str(units).lower() == "watts" else 10.0 * np.log10(ratio)
    return {"acpr": out_acpr, "main_power": float(power_in_units(P[0], units)), "adj_power": power_in_units(P[1:], units),
            "main_power_W": P[0], "adj_power_W": P[1:], "f": f, "psd": psds[0], "bands": np.column_stack([lo, hi]),
            "L": L, "nfft": nf, "noverlap": nov, "nseg": int(nseg), "units": units}


def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對：
    (1–6) tests/matlab_ref/acpr/acpr_ref.json（acpr_ref.m：pwelch、bandpower、comm.ACPR，工具箱函式）；
    (7) tests/matlab_ref/scope/acpr/acpr_scope_ref.json（spectrumAnalyzer 本身 23 個 acpr_* capture 的 getMeasurementsData 數字；
        每個 capture 從訊號重建畫面頻譜（dsv_spectrum.welch）→ acpr(rule='scope') → 和分析器的 Channel Power／Lower／Upper 逐值比）。

    容差（全部遠小於 1e-9 的規定；數字是 2026-10-24 在 numpy 2.x／macOS arm64 量到的最大誤差，容差留 ≥ 100 倍餘裕）：
    - welch vs pwelch 的 psd：量到 ≤ 6.0e-13（Hann 1024 50%）→ rtol 1e-10；f 軸：量到 0 → rtol 1e-12 + atol 1e-9（DC bin 是 0）。
    - power→psd 換算（同陣列乘常數）：量到 2.2e-16 → rtol 1e-13。
    - 頻帶功率 W：用 JSON 的 PSD 時只差加總順序，量到 4.2e-16 → rtol 1e-13；用 welch 的 PSD 時量到 1.04e-13 → rtol 1e-10。
    - dB 值（dBc／dBm／dBW／bwnorm）用絕對容差（接近 0 dBc 的值 rtol 沒意義，參考裡最小 |dBc| = 0.0075）：JSON PSD 量到 1.4e-14 dB
      → atol 1e-12 dB；welch PSD 量到 4.7e-13 dB → atol 1e-10 dB（≈ 相對功率 2.3e-11）。
    - comm.ACPR 的 dB 值：量到 7.1e-14 dB → atol 1e-11 dB；bandpower 交叉檢查 W：量到 2.6e-16 → rtol 1e-13，dBm 量到 0 → atol 1e-12。
    - 分析器 capture：畫面抽樣（dBm／dBm/Hz）量到 4.7e-12 dB（整條畫面 7.8e-11）→ atol 1e-9 dB；Channel Power／Lower／Upper 量到 1.1e-13 dB
      （分析報告用累積和算的是 6.6e-8 dB，見模組說明）→ atol 1e-10 dB；已知差異（Welch three_pairs）：分析報告的偏差數字（含它自己累積和
      ≤ 6.6e-8 dB 的雜訊；量到差 5.8e-9）→ atol 1e-7 dB，同一偏差用本模組直接相加算的數字 → atol 1e-10 dB。"""
    import json
    import os
    import time as _time
    d = os.path.join(ref_dir, "acpr")
    if not os.path.isfile(os.path.join(d, "acpr_ref.json")):
        d = ref_dir
    path = os.path.join(d, "acpr_ref.json")
    if not os.path.isfile(path):
        check(True, "（沒有 tests/matlab_ref/acpr/acpr_ref.json：略過 MATLAB ACPR 比對）")
        return
    R = json.load(open(path, encoding="utf-8"))
    from dsv_spectrum import design_window, overlap_samples, welch
    fs = float(R["fs"])
    m = np.loadtxt(os.path.join(d, "acpr_sig_cplx.txt"))
    xc = m[:, 0] + 1j * m[:, 1]
    xr = np.loadtxt(os.path.join(d, "acpr_sig_real.txt"))
    TOL_PSD, TOL_F, TOL_P2PSD = 1e-10, 1e-12, 1e-13
    TOL_W_JSON, TOL_W_WELCH = 1e-13, 1e-10
    ATOL_DB_JSON, ATOL_DB_WELCH, ATOL_DB_COMM = 1e-12, 1e-10, 1e-11
    ATOL_SCOPE_DB, ATOL_DISP_DB, ATOL_KNOWN_DB = 1e-10, 1e-9, 1e-7

    def arr(v):
        v = v if isinstance(v, list) else [v]
        return np.asarray([np.nan if x is None else x for x in v], dtype=float)

    def close(a, b, rtol=1e-9, atol=0.0, nan_ok=False):
        """逐值比對：NaN 只和 NaN 相等（nan_ok），±Inf 要同號；其餘 |a−b| ≤ atol + rtol·|b|。"""
        a, b = np.atleast_1d(np.asarray(a, dtype=float)), np.atleast_1d(np.asarray(b, dtype=float))
        if a.shape != b.shape:
            return False
        na, nb = np.isnan(a), np.isnan(b)
        if np.any(na != nb) or (np.any(na) and not nan_ok):
            return False
        ia, ib = np.isinf(a), np.isinf(b)
        if np.any(ia != ib) or np.any(a[ia] != b[ib]):
            return False
        ok = ~(na | ia)
        return bool(np.all(np.abs(a[ok] - b[ok]) <= atol + rtol * np.abs(b[ok])))

    def worst(a, b):
        a, b = np.atleast_1d(np.asarray(a, dtype=float)), np.atleast_1d(np.asarray(b, dtype=float))
        with np.errstate(invalid="ignore", divide="ignore"):
            e = np.abs(a - b) / np.maximum(np.abs(b), 1e-300)
        e = np.where(np.isfinite(e), e, 0.0)
        return float(np.max(e)) if e.size else 0.0

    def absdiff(a, b):
        """dB 值的最大絕對差，NaN 對 NaN 算 0（NaN 樣式不同算 inf）。"""
        a, b = np.atleast_1d(np.asarray(a, dtype=float)), np.atleast_1d(np.asarray(b, dtype=float))
        if a.shape != b.shape or np.any(np.isnan(a) != np.isnan(b)):
            return math.inf
        ok = ~np.isnan(a)
        return float(np.max(np.abs(a[ok] - b[ok]))) if np.any(ok) else 0.0

    # 1. PSD：dsv_spectrum.welch 要重現 pwelch（頻率軸與 psd）。視窗／L／noverlap／nfft／range 全部讀 JSON 的 PSD metadata
    #    （acpr_ref.m 寫入的 win 字串：'hann periodic' = hann(L,'periodic')、'rectwin'）；鍵名 c_* 用複數訊號、r_* 用實數訊號。
    def win_from_meta(meta):
        nm, L = str(meta["win"]).strip().lower(), int(meta["L"])
        if nm == "hann periodic":
            return design_window("hann", L)
        if nm == "rectwin":
            return np.ones(L)
        raise NotImplementedError(f"selftest: unknown reference window {meta['win']!r}")

    wins = {k: win_from_meta(meta) for k, meta in R["psd"].items()}
    psd = {k: welch(xc if k.startswith("c_") else xr, fs, wins[k], int(meta["noverlap"]), int(meta["nfft"]), str(meta["range"]))
           for k, meta in R["psd"].items()}
    bad = []
    for k, r in psd.items():
        ref = R["psd"][k]
        if not (close(r["f"], arr(ref["f"]), rtol=TOL_F, atol=1e-9) and close(r["psd"], arr(ref["p"]), rtol=TOL_PSD)):
            bad.append(f"{k}（psd 最大相對誤差 {worst(r['psd'], arr(ref['p'])):.1e}）")
        if not close(psd_from_power(r["power"], wins[k], fs), r["psd"], rtol=TOL_P2PSD):
            bad.append(f"{k}:power→psd")
        if not (r["L"] == int(ref["L"]) and r["nfft"] == int(ref["nfft"]) and r["f"].size == len(ref["f"])):
            bad.append(f"{k}:meta")
    meta_txt = ", ".join("{}={}/{}/{}".format(k, R["psd"][k]["win"], R["psd"][k]["L"], R["psd"][k]["range"]) for k in psd)
    check(not bad, f"PSD vs MATLAB pwelch（{len(psd)} 組，設定讀 JSON metadata：{meta_txt}）"
                   f"頻率軸與 psd 一致（rtol {TOL_PSD:g}），power→psd 換算一致" + (f"（不一致：{bad}）" if bad else ""))

    # 2. 八個 plain case：頻帶、三種工具箱積分規則的頻帶功率、dBc、dBm／dBW、bwnorm、clipped 旗標；(a) 用 JSON 的 PSD、(b) 用 welch 的 PSD
    rule_fail = {"bp": [], "in": [], "tz": []}
    band_fail = []
    nan_cases = []
    nval = 0
    for c in R["cases"]:
        nm = c["name"]
        ref_f, ref_p = arr(R["psd"][c["psd"]]["f"]), arr(R["psd"][c["psd"]]["p"])
        b = bands(c["fc"], c["span"], c["adjBW"], c["offsets"])
        if not (close(b["main"], arr(c["main_band"]), rtol=1e-12) and close(b["lower"].ravel(), arr(c["lower_bands"]).ravel(), rtol=1e-12)
                and close(b["upper"].ravel(), arr(c["upper_bands"]).ravel(), rtol=1e-12)):
            band_fail.append(nm)
        for src, (ff, pp, tol_w, atol_db) in {"json": (ref_f, ref_p, TOL_W_JSON, ATOL_DB_JSON),
                                              "welch": (psd[c["psd"]]["f"], psd[c["psd"]]["psd"], TOL_W_WELCH, ATOL_DB_WELCH)}.items():
            for rule in MATLAB_RULES:
                r = acpr(ff, pp, c["fc"], c["span"], c["adjBW"], c["offsets"], rule=rule)
                rb = acpr_bwnorm(ff, pp, c["fc"], c["span"], c["adjBW"], c["offsets"], rule=rule)
                pairs = [("main", r["main_power"], c[f"{rule}_main"]), ("lower", r["lower_power"], c[f"{rule}_lower"]),
                         ("upper", r["upper_power"], c[f"{rule}_upper"]),
                         ("lower_dBc", r["lower_dBc"], c[f"{rule}_acpr_lower_dBc"]), ("upper_dBc", r["upper_dBc"], c[f"{rule}_acpr_upper_dBc"]),
                         ("main_dBm", r["channel_power"], c[f"{rule}_main_dBm"]),
                         ("main_dBW", power_in_units(r["main_power"], "dBW"), c[f"{rule}_main_dBW"]),
                         ("lower_bwnorm", rb["lower_dBc"], c[f"{rule}_acpr_lower_dBc_bwnorm"]),
                         ("upper_bwnorm", rb["upper_dBc"], c[f"{rule}_acpr_upper_dBc_bwnorm"])]
                for what, mine, ref in pairs:
                    refa = arr(ref)
                    nval += refa.size
                    if what.endswith(("dBc", "dBm", "dBW", "bwnorm")):
                        ok = close(mine, refa, rtol=0.0, atol=atol_db, nan_ok=True)
                    else:
                        ok = close(mine, refa, rtol=tol_w, atol=0.0, nan_ok=True)
                    if not ok:
                        a = np.atleast_1d(np.asarray(mine, dtype=float))
                        rule_fail[rule].append(f"{nm}/{src}/{what}: mine={a.tolist()} ref={refa.tolist()} (rel {worst(a, refa):.1e})")
            if src == "json":
                clip_ok = (np.array_equal(r["lower_clipped"], np.atleast_1d(np.asarray(c["lower_clipped"], dtype=bool)))
                           and np.array_equal(r["upper_clipped"], np.atleast_1d(np.asarray(c["upper_clipped"], dtype=bool))))
                if not clip_ok:
                    band_fail.append(f"{nm}:clipped")
                if np.any(np.isnan(r["lower_power"])) or np.any(np.isnan(r["upper_power"])):
                    nan_cases.append(nm)
    check(not band_fail, f"頻帶 vs MATLAB（{len(R['cases'])} 個 case：main／lower／upper 邊界與 clipped 旗標；Start/Stop 模式等價）"
          + (f"（不一致：{band_fail}）" if band_fail else ""))
    bs = bands(start=-1000.0, stop=1000.0, adj_bw=1000.0, offsets=(2000.0, 3500.0))
    bc = bands(0.0, 2000.0, 1000.0, (2000.0, 3500.0))
    check(np.array_equal(bs["main"], bc["main"]) and np.array_equal(bs["lower"], bc["lower"]) and np.array_equal(bs["upper"], bc["upper"]),
          "Start/Stop 模式（−1000..1000）與 Span/CF 模式（2000 @ 0）得到同樣的頻帶")
    for rule, label in (("bp", "bandpower／comm.ACPR 規則（往外取 bin、矩形法、最後一 bin 寬度 0、夾到格點）"),
                        ("in", "'in' 規則（只加帶內 bin × Δf，不夾）"), ("tz", "'tz' 規則（線性內插的梯形積分）")):
        fails = rule_fail[rule]
        tail = {"bp": "含 real_2k 整個在格點外的頻帶 → NaN", "tz": "含 real_2k 整個在格點外的頻帶 → NaN",
                "in": "real_2k 的 [−1000, 0] 不夾、只含 DC bin"}[rule]
        check(not fails, f"ACPR vs MATLAB，{label}：{len(R['cases'])} 個 case × (JSON PSD, welch PSD)，主通道功率 W／dBm／dBW、lower／upper dBc、"
                         f"bwnorm dBc 逐值一致（W rtol {TOL_W_JSON:g}／{TOL_W_WELCH:g}，dB atol {ATOL_DB_JSON:g}／{ATOL_DB_WELCH:g}；{tail}）"
              + (f"（不一致 {len(fails)} 筆，前 3：{fails[:3]}）" if fails else ""))
    # real_2k（單邊 PSD，格點 0..5000）下第 2 對 [−1000, 0] 整個在格點外：bp／tz → NaN（MATLAB JSON 是 null）、in → 只含 DC bin
    f1s, p1s = arr(R["psd"]["r_hann"]["f"]), arr(R["psd"]["r_hann"]["p"])
    c2 = [c for c in R["cases"] if c["name"] == "real_2k"][0]
    r_bp = acpr(f1s, p1s, c2["fc"], c2["span"], c2["adjBW"], c2["offsets"], rule="bp")
    r_tz = acpr(f1s, p1s, c2["fc"], c2["span"], c2["adjBW"], c2["offsets"], rule="tz")
    r_in = acpr(f1s, p1s, c2["fc"], c2["span"], c2["adjBW"], c2["offsets"], rule="in")
    r_sc = acpr(f1s, p1s, c2["fc"], c2["span"], c2["adjBW"], c2["offsets"], rule="scope")
    bp_pow, _ = band_power(f1s, p1s, -1000.0, 0.0, rule="bp")
    ok = (nan_cases == ["real_2k"] and c2["bp_lower"][1] is None and c2["tz_lower"][1] is None and math.isnan(bp_pow)
          and math.isnan(r_bp["lower_power"][1]) and math.isnan(r_bp["lower_dBc"][1]) and math.isnan(r_tz["lower_power"][1])
          and bool(r_bp["lower_clipped"][1]) and not r_bp["lower_clipped"][0] and not np.any(r_bp["upper_clipped"])
          and close(r_in["lower_power"][1], c2["in_lower"][1], rtol=1e-12) and np.isfinite(r_bp["upper_dBc"]).all()
          and math.isnan(r_sc["lower_dBc"][1]) and np.isfinite(r_sc["lower_dBc"][0]) and np.isfinite(r_sc["upper_dBc"]).all())
    check(ok, f"單邊頻譜的負頻率頻帶（real_2k 下第 2 對 [−1000, 0]）：bp／tz／scope 給 NaN（MATLAB null）、clipped=True；'in' 只含 DC bin "
              f"= {r_in['lower_power'][1]:.4e} W；其他頻帶正常；置中版（real_2k_cent）全部有值。NaN 的 case：{nan_cases}；共比對 {nval} 個值")

    # 3. comm.ACPR：整個流程（symmetric Hann、50% 重疊、FFTLength 'Same as segment length'、頻寬正規化、dBm），含時域 RRC 量測濾波器。
    #    acpr_ref.m 明確設 FFTLength = 'Same as segment length'，所以這裡傳 nfft="same"；L = 1024 是 2 的冪，預設 'nextpow2' 給同樣的 NFFT。
    bad = []
    ncomm = 0
    comm_kw = dict(segment_length=1024, overlap_pct=50.0, window="hann", nfft="same")
    for c in R["commACPR"]:
        off = np.atleast_1d(np.asarray(c["offsets"], dtype=float))
        signed = np.concatenate([-off[::-1], off])
        h = None
        if c["filter"] == "Property":
            h = _rcosdesign_sqrt(0.35, 8, 10)
        r = comm_acpr(xc, fs, c["fc"], c["span"], signed, c["adjBW"], measurement_filter=h, **comm_kw)
        rW = comm_acpr(xc, fs, c["fc"], c["span"], signed, c["adjBW"], measurement_filter=h, units="Watts", **comm_kw)
        ncomm += 4 * off.size * 2 + 1
        ok = (close(r["acpr"], arr(c["acpr_dBc_bwnorm"]), rtol=0.0, atol=ATOL_DB_COMM) and close(r["main_power"], arr(c["main_dBm"]), rtol=0.0, atol=ATOL_DB_COMM)
              and close(r["adj_power"], arr(c["adj_dBm"]), rtol=0.0, atol=ATOL_DB_COMM)
              and close(r["adj_power"] - r["main_power"], arr(c["acpr_dBc_raw"]), rtol=0.0, atol=ATOL_DB_COMM)
              and close(10 * np.log10(rW["acpr"]), arr(c["acpr_dBc_bwnorm"]), rtol=0.0, atol=ATOL_DB_COMM)
              and r["nfft"] == 1024 and r["L"] == 1024 and r["noverlap"] == 512 and r["nseg"] == 15)
        if not ok:
            bad.append(f"{c['name']}: acpr={r['acpr'].tolist()} ref={c['acpr_dBc_bwnorm']} main={r['main_power']} ref={c['main_dBm']} "
                       f"adj={r['adj_power'].tolist()} ref={c['adj_dBm']} nfft={r['nfft']}")
    chk = R["commACPR_check_bandpower"]
    r0 = comm_acpr(xc, fs, 0.0, 2000.0, (-2000.0, 2000.0), 1000.0, units="Watts", **comm_kw)
    r0d = comm_acpr(xc, fs, 0.0, 2000.0, (-2000.0, 2000.0), 1000.0, **comm_kw)
    ok0 = (close(r0["main_power_W"], chk["main"], rtol=1e-13) and close(r0["adj_power_W"], [chk["lo1"], chk["up1"]], rtol=1e-13)
           and close(r0d["main_power"], chk["main_dBm"], rtol=0.0, atol=1e-12)
           and close(r0d["adj_power"], [chk["lo1_dBm"], chk["up1_dBm"]], rtol=0.0, atol=1e-12))
    ncomm += 6
    # 預設 NFFT（'nextpow2'）在 L = 1024 下和參考相同——證明預設路徑在參考設定下也對；(n,1) 欄向量照收
    c0 = [c for c in R["commACPR"] if c["name"] == "default_cplx"][0]
    rdef = comm_acpr(xc, fs, c0["fc"], c0["span"], (-3500.0, -2000.0, 2000.0, 3500.0), c0["adjBW"], segment_length=1024, overlap_pct=50.0, window="hann")
    rcol = comm_acpr(xc.reshape(-1, 1), fs, c0["fc"], c0["span"], (-3500.0, -2000.0, 2000.0, 3500.0), c0["adjBW"], segment_length=1024, overlap_pct=50.0, window="hann")
    okd = rdef["nfft"] == 1024 and close(rdef["acpr"], arr(c0["acpr_dBc_bwnorm"]), rtol=0.0, atol=ATOL_DB_COMM) and np.array_equal(rcol["acpr"], rdef["acpr"])
    check(not bad and ok0 and okd, f"comm.ACPR vs MATLAB（default_cplx、three_pairs、qpsk_tight、rrc_filter＝rcosdesign(0.35,8,10,'sqrt') 時域量測濾波器；"
                                   f"{ncomm} 個值，dB atol {ATOL_DB_COMM:g}）：頻寬正規化 ACPR dBc、主通道 dBm、相鄰通道 dBm、raw dBc、Watts 版一致；"
                                   "L/NFFT/noverlap/段數 = 1024/1024/512/15；symmetric Hann + bandpower 交叉檢查 W 與 dBm 一致；"
                                   "預設 FFTLength（nextpow2）在 L=1024 下與參考相同；(n,1) 欄向量與 1-D 結果相同"
          + (f"（不一致：{bad}）" if bad or not ok0 or not okd else ""))
    # qpsk_tight：Span = AdjBW，所以 comm.ACPR 的正規化 = 純比值；default_cplx 的 bwnorm 與 plain 差 10·log10(2)
    c0p = [c for c in R["cases"] if c["name"] == "default_cplx"][0]
    check(close(arr(c0p["bp_acpr_lower_dBc_bwnorm"]) - arr(c0p["bp_acpr_lower_dBc"]), [10 * math.log10(2.0)] * 2, rtol=1e-12),
          "頻寬正規化：Span 2000／AdjBW 1000 → bwnorm 比純比值高 10·log10(2) = 3.0103 dB（Span = AdjBW 時相同）")
    # FFTLength 規則（照 comm.ACPR 的定義；參考 JSON 裡所有 comm case 都是 L = 1024 所以分不出來）
    r5s = comm_acpr(xc[:5000], fs, 0.0, 2000.0, (-3500.0, -2000.0, 2000.0, 3500.0), 1000.0, nfft="same")
    r5n = comm_acpr(xc[:5000], fs, 0.0, 2000.0, (-3500.0, -2000.0, 2000.0, 3500.0), 1000.0)
    okf = (comm_fft_length(1024) == 1024 and comm_fft_length(1024, "same") == 1024 and comm_fft_length(5000) == 8192
           and comm_fft_length(5000, "same") == 5000 and comm_fft_length(100) == 256 and comm_fft_length(100, "same") == 256
           and comm_fft_length(1000, "Next power of 2") == 1024 and comm_fft_length(1000, "Same as segment length") == 1000
           and comm_fft_length(1024, 4096) == 4096 and comm_fft_length(1, None) == 256
           and r5s["nfft"] == 5000 and r5s["L"] == 5000 and r5s["f"].size == 5000 and r5n["nfft"] == 8192 and r5n["f"].size == 8192
           and r5n["L"] == 5000 and np.all(np.abs(r5n["acpr"] - r5s["acpr"]) > 0.01))
    check(okf, f"comm.ACPR FFTLength 規則（照 MATLAB comm.ACPR 的定義，無 MATLAB 數值）：預設 'nextpow2' = max(256, 2^nextpow2(L))（1024→1024、5000→8192、"
               f"100→256）、'same' = max(256, L)、整數 = Custom；5000 點 'Auto' 用預設 NFFT 8192 與 'same' 5000 的 ACPR 相差 "
               f"{np.max(np.abs(r5n['acpr'] - r5s['acpr'])):.2f} dB（所以預設不能寫成 L）")

    # 4. Auto Span（MATLAB 打開量測時自動算頻帶）
    bad = []
    for key, two in (("twosided", True), ("onesided", False)):
        a = auto_span((-1e9, 1e9), fs, two)
        ref = R["auto_span"][key]
        if not (a["xlim"] == tuple(ref["xlim"]) and a["center"] == ref["center"] and a["span"] == ref["span"] and a["start"] == ref["start"]
                and a["stop"] == ref["stop"] and a["adj_bw"] == ref["adjBW"] and np.array_equal(a["offsets"], arr(ref["offsets"]))):
            bad.append(key)
    check(not bad and np.array_equal(pad_offsets((2000, 3500), 4), [2000, 3500, 0, 0]) and np.array_equal(pad_offsets((2000, 3500), 1), [2000]),
          "Auto Span vs MATLAB 的規則：雙邊 fs 1e4 → CF 0／Span 2000／AdjBW 1000／[2000 3500]（＝文件預設），單邊 → 2500／1000／500／[1000 1750]；"
          "Num Pairs 變多補 0" + (f"（不一致：{bad}）" if bad else ""))

    # 5. 錯誤對應（MATLAB 工具列欄位的規則與 comm.ACPR 的錯誤識別碼）
    f0, p0 = psd["c_hann"]["f"], psd["c_hann"]["psd"]

    def raises(mid, fn):
        try:
            fn()
        except ACPRError as e:
            return e.matlab_id == mid and isinstance(e, ValueError) and str(e) == e.en and bool(e.zh)
        except Exception:
            return False
        return False

    errs = [
        ("invalidNumOffsets", lambda: acpr(f0, p0, offsets=[1000] * 65)),
        ("invalidNumOffsets", lambda: acpr(f0, p0, offsets=[], num_offsets=0)),
        ("invalidNumOffsets", lambda: acpr(f0, p0, offsets=[1000], num_offsets=math.nan)),
        ("invalidACPROffsets", lambda: acpr(f0, p0, offsets=[1000, 2000, 3000], num_offsets=2)),
        ("invalidACPROffsets", lambda: acpr(f0, p0, offsets=[1000, math.inf])),
        ("invalidACPROffsets", lambda: acpr(f0, p0, offsets=[[2000, 3500], [1000, 1500]])),
        ("invalidACPROffsets", lambda: acpr(f0, p0, offsets=[2000, 3500 + 1j])),
        ("invalidACPROffsets", lambda: bands(offsets=np.ones((2, 2)))),
        ("invalidSpan", lambda: acpr(f0, p0, span=0)),
        ("invalidSpan", lambda: acpr(f0, p0, span=math.nan)),
        ("invalidSpan", lambda: filter_weights(f0, 0.0, "rrc", 0.5, span=0.0)),
        ("invalidCenterFrequency", lambda: acpr(f0, p0, center=math.inf)),
        ("invalidStartFrequency", lambda: acpr(f0, p0, start=math.nan, stop=1000)),
        ("invalidStartFrequency", lambda: acpr(f0, p0, stop=1000, validate=False)),
        ("invalidStopFrequency", lambda: acpr(f0, p0, start=-1000, stop=math.inf)),
        ("invalidStopFrequency", lambda: acpr(f0, p0, start=-1000, validate=False)),
        ("dsv:invalidStartStop", lambda: acpr(f0, p0, start=1000, stop=-1000)),
        ("dsv:invalidStartStop", lambda: acpr(f0, p0, start=0, stop=0)),
        ("dsv:invalidStartStop", lambda: acpr_bwnorm(f0, p0, start=1000, stop=-1000)),
        ("invalidAdjacentBW", lambda: acpr(f0, p0, adj_bw=-1)),
        ("invalidAdjacentBW", lambda: acpr_bwnorm(f0, p0, adj_bw=0)),
        ("invalidFilterCoeff", lambda: acpr(f0, p0, coeff=1.5)),
        ("invalidFilterCoeff", lambda: acpr(f0, p0, shape="gaussian", coeff=-0.1)),
        ("invalidFilterCoeff", lambda: filter_weights(f0, 0.0, "rrc", math.nan)),
        ("invalidSpanAndCenterFrequency", lambda: acpr(f0, p0, center=4500, span=2000, nyquist=(-5000, 5000))),
        ("dsv:tooLarge", lambda: acpr(np.broadcast_to(np.zeros(1), (MAX_ELEMENTS + 1,)), np.zeros(1))),
        ("dsv:tooLarge", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=1024, nfft=1 << 25)),
        ("dsv:tooLarge", lambda: scope_nfft((1 << 24) + 1)),
        ("dsv:tooLarge", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, measurement_filter=np.broadcast_to(np.ones(1), ((1 << 20) + 1,)))),
        ("comm:system:ACPR:FrequencyValuesOutOfRange", lambda: comm_acpr(xc, fs, 0, 2000, (-4000, 4000), 2001)),
        ("comm:system:ACPR:InvalidInput", lambda: comm_acpr(np.array([1.0]), fs)),
        ("comm:system:ACPR:InvalidInput", lambda: comm_acpr(np.array([1.0, math.nan, 2.0]), fs)),
        ("comm:system:ACPR:InvalidInput", lambda: comm_acpr(np.ones((4, 2)), fs)),
        ("comm:system:ACPR:InvalidAdjacentMeasurementBandwidthLength", lambda: comm_acpr(xc, fs, 0, 1000, (-2000, 2000), (500, 500, 500))),
        # comm.ACPR 屬性檢查（validateattributes；DSV 自己的訊息）
        ("dsv:comm:SampleRate", lambda: comm_acpr(xc, math.nan, 0, 2000, (-2000, 2000), 1000)),
        ("dsv:comm:SampleRate", lambda: comm_acpr(xc, 0.0, 0, 2000, (-2000, 2000), 1000)),
        ("dsv:comm:MainChannelFrequency", lambda: comm_acpr(xc, fs, math.inf, 2000, (-2000, 2000), 1000)),
        ("dsv:comm:MainMeasurementBandwidth", lambda: comm_acpr(xc, fs, 0, 0, (-2000, 2000), 1000)),
        ("dsv:comm:MainMeasurementBandwidth", lambda: comm_acpr(xc, fs, 0, -5, (-2000, 2000), 1000)),
        ("dsv:comm:AdjacentChannelOffset", lambda: comm_acpr(xc, fs, 0, 2000, (), 1000)),
        ("dsv:comm:AdjacentChannelOffset", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, math.nan), 1000)),
        ("dsv:comm:AdjacentChannelOffset", lambda: comm_acpr(xc, fs, 0, 2000, np.array([[-3000, 3000], [-2000, 2000]]), 1000)),
        ("dsv:comm:AdjacentMeasurementBandwidth", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), -1)),
        ("dsv:comm:AdjacentMeasurementBandwidth", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), (1000, 0))),
        ("dsv:comm:SegmentLength", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=0)),
        ("dsv:comm:SegmentLength", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=-5)),
        ("dsv:comm:SegmentLength", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=xc.size + 1)),
        ("dsv:comm:SegmentLength", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=100.5)),
        ("dsv:comm:OverlapPercentage", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=1024, overlap_pct=99.99)),
        ("dsv:comm:OverlapPercentage", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, overlap_pct=100)),
        ("dsv:comm:OverlapPercentage", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, overlap_pct=-1)),
        ("dsv:comm:FFTLength", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, segment_length=1024, nfft=512)),
        ("dsv:comm:FFTLength", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, nfft="bogus")),
        ("dsv:comm:MeasurementFilter", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, measurement_filter=[])),
        ("dsv:comm:MeasurementFilter", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, measurement_filter=[1.0, math.nan])),
        ("dsv:comm:MeasurementFilter", lambda: comm_acpr(xc, fs, 0, 2000, (-2000, 2000), 1000, measurement_filter=np.ones((3, 3)))),
    ]
    bad = [mid for mid, fn in errs if not raises(mid, fn)]
    # 呼叫端 bug（不是使用者輸入）→ 一般 ValueError，不能悄悄回 NaN 或丟掉虛部
    def raises_value_error(fn):
        try:
            fn()
        except ACPRError:
            return False
        except ValueError:
            return True
        except Exception:
            return False
        return False

    fl = np.linspace(-5000.0, 4990.234375, 1024)
    pl = np.ones(1024) * 1e-3
    api_errs = [
        ("pxx 短一個", lambda: acpr(fl, pl[:-1])),
        ("pxx 二維 (1024,2)", lambda: acpr(fl, np.column_stack([pl, pl]))),
        ("f 短一個", lambda: acpr(fl[:-1], pl)),
        ("pxx 複數", lambda: acpr(fl, pl + 1j)),
        ("f 複數", lambda: acpr(fl + 1j, pl)),
        ("pxx 含 NaN", lambda: acpr(fl, np.where(np.arange(1024) == 100, np.nan, pl))),
        ("pxx 含 Inf", lambda: acpr(fl, np.where(np.arange(1024) == 100, np.inf, pl))),
        ("pxx 負值", lambda: acpr(fl, np.where(np.arange(1024) == 100, -1e-3, pl))),
        ("band_power pxx 複數", lambda: band_power(fl, pl + 1j, -1000, 1000)),
        ("band_power 長度不同", lambda: band_power(fl, pl[:10], -1000, 1000)),
        ("band_power f1 ≥ f2", lambda: band_power(fl, pl, 1000, -1000)),
        ("band_power 邊界 NaN", lambda: band_power(fl, pl, math.nan, 1000)),
        ("f 不遞增", lambda: acpr(fl[::-1], pl)),
        ("f 含 NaN", lambda: acpr(np.where(np.arange(1024) == 5, np.nan, fl), pl)),
        ("f 不均勻（scope 規則）", lambda: acpr(np.concatenate([fl[:500], fl[500:] + 1.0]), pl)),
        ("rule 不認得", lambda: acpr(fl, pl, rule="xx")),
        ("shape 不認得", lambda: acpr(fl, pl, shape="butterworth")),
        ("acpr_bwnorm validate=False 且 start>stop", lambda: acpr_bwnorm(fl, pl, start=1000, stop=-1000, validate=False)),
        ("pad_offsets 負的對數", lambda: pad_offsets((1, 2), -1)),
        ("comm_fft_length(0)", lambda: comm_fft_length(0)),
        ("comm_fft_length(-5)", lambda: comm_fft_length(-5)),
        ("scope_nfft(0)", lambda: scope_nfft(0)),
        ("psd_from_display dBFS", lambda: psd_from_display([0.0], "dBFS", 1.0)),
        ("psd_from_display power 模式沒給 RBW", lambda: psd_from_display([0.0], "dBm")),
    ]
    bad_api = [nm for nm, fn in api_errs if not raises_value_error(fn)]
    # (1024,1) 這種可以 squeeze 的欄向量要收（MATLAB 的 column vector）
    r_col = acpr(fl.reshape(-1, 1), pl.reshape(-1, 1))
    r_row = acpr(fl, pl)
    col_ok = r_col["main_power"] == r_row["main_power"] and np.array_equal(r_col["lower_dBc"], r_row["lower_dBc"])
    # 空 PSD（welch 資料不夠一段）→ 全 NaN，不報錯；一個 bin 的 PSD 也是 NaN（Δf 未定義）
    r_empty = acpr(np.zeros(0), np.zeros(0))
    r_one = acpr(np.zeros(1), np.ones(1))
    empty_ok = (math.isnan(r_empty["main_power"]) and np.all(np.isnan(r_empty["lower_dBc"])) and r_empty["main_clipped"]
                and math.isnan(r_one["main_power"]) and np.all(np.isnan(r_one["upper_dBc"])))
    # 不均勻格點只擋 'scope'；'bp' 照算
    r_bp_nonuni = acpr(np.concatenate([fl[:500], fl[500:] + 1.0]), pl, rule="bp")
    e = _err("invalidSpan")
    check(not bad and not bad_api and col_ok and empty_ok and np.isfinite(r_bp_nonuni["main_power"]) and isinstance(e, ValueError)
          and e.zh.startswith("請以") and str(e) == _ERRORS["invalidSpan"][0],
          f"錯誤對應：{len(errs)} 個（工具列 invalid*、comm:system:ACPR:*、dsv:invalidStartStop、dsv:tooLarge、dsv:comm:* 屬性檢查；含二維 offsets、"
          f"只給 start 或 stop、2^24 以上的格點／NFFT／卷積）都丟 ACPRError（英文 + 繁體中文）；{len(api_errs)} 種呼叫端錯誤（f／pxx 長度不同、二維、複數、"
          f"pxx NaN／Inf／負值、f 不遞增／NaN／不均勻、頻帶邊界 f1 ≥ f2 或 NaN、rule／shape 不認得、bwnorm 頻寬 ≤ 0、pad_offsets 負數、comm_fft_length ≤ 0、"
          f"dBFS）丟 ValueError；(n,1) 欄向量照收；空 PSD／單點 PSD → NaN；不均勻格點 'bp' 照算"
          + (f"（沒丟或識別碼不對：{bad}）" if bad else "") + (f"（沒丟 ValueError：{bad_api}）" if bad_api else ""))
    # 負偏移量不報錯（MATLAB 只檢查長度），結果是上下對調；整數訊號 comm_acpr 照收（文件化的差異）
    rneg = acpr(f0, p0, 0, 2000, 1000, [-2000, 3500])
    rpos = acpr(f0, p0, 0, 2000, 1000, [2000, 3500])
    xint = (xc.real * 1000).astype(np.int64)
    rint = comm_acpr(xint, fs, 0, 2000, (-2000, 2000), 1000, **comm_kw)
    rflt = comm_acpr(xint.astype(float), fs, 0, 2000, (-2000, 2000), 1000, **comm_kw)
    check(rneg["lower_dBc"][0] == rpos["upper_dBc"][0] and rneg["upper_dBc"][0] == rpos["lower_dBc"][0] and rneg["lower_dBc"][1] == rpos["lower_dBc"][1]
          and np.array_equal(rint["acpr"], rflt["acpr"]),
          "負的偏移量不報錯（MATLAB 只檢查長度），第 1 對的 lower／upper 對調；comm_acpr 收整數陣列（轉 float 後與 float 輸入相同；MATLAB 會丟 InvalidInput，文件化差異）")

    # 6. 效能：1e6 bin 的 PSD 格點、64 對（工具列上限），none 與 RRC／Gaussian；comm.ACPR 跑 1e6 點複數訊號（含 3 條 81 階量測濾波器）
    rng = np.random.default_rng(0)
    nbig = 1_000_000
    fbig = (np.arange(nbig) - (nbig // 2 - 1)) * (1e6 / nbig)
    pbig = rng.random(nbig) * 1e-6 + 1.0 * np.exp(-0.5 * (fbig / 50e3) ** 2)
    off64 = 150e3 + np.arange(64) * 4e3
    t0 = _time.time()
    r1 = acpr(fbig, pbig, 0.0, 200e3, 3e3, off64)
    r2 = acpr_bwnorm(fbig, pbig, 0.0, 200e3, 3e3, off64, rule="bp")
    r1r = acpr(fbig, pbig, 0.0, 200e3, 3e3, off64, shape="rrc", coeff=0.35)
    r1g = acpr(fbig, pbig, 0.0, 200e3, 3e3, off64, shape="gaussian", coeff=0.3)
    dt1 = _time.time() - t0
    xbig = rng.standard_normal(nbig) + 1j * rng.standard_normal(nbig)
    t0 = _time.time()
    r3 = comm_acpr(xbig, 1e6, 0.0, 100e3, (-200e3, 200e3), 50e3, segment_length=1024, overlap_pct=50.0, window="hann")
    dt2 = _time.time() - t0
    t0 = _time.time()
    r4 = comm_acpr(xbig, 1e6, 0.0, 100e3, (-200e3, 200e3), 50e3, segment_length=1024, overlap_pct=50.0, window="hann",
                   measurement_filter=_rcosdesign_sqrt(0.35, 8, 10))
    dt3 = _time.time() - t0
    t0 = _time.time()
    r5 = comm_acpr(xbig, 1e6, 0.0, 100e3, (-200e3, 200e3), 50e3)          # 'Auto'：L = 1e6 → NFFT 2^20
    dt4 = _time.time() - t0
    ok = (r1["n"] == 64 and np.all(np.isfinite(r1["lower_dBc"])) and np.all(np.isfinite(r2["upper_dBc"])) and np.all(np.isfinite(r1r["upper_dBc"]))
          and np.all(np.isfinite(r1g["lower_dBc"])) and np.all(np.isfinite(r3["acpr"]))
          and np.all(np.isfinite(r4["acpr"])) and r5["nfft"] == 1 << 20 and np.all(np.isfinite(r5["acpr"]))
          and dt1 < 2.0 and dt2 < 3.0 and dt3 < 5.0 and dt4 < 3.0)
    check(ok, f"效能：1e6 bin PSD × 64 對 acpr（scope none／RRC／Gaussian）＋acpr_bwnorm {dt1:.3f}s；comm.ACPR 1e6 點複數（Hann 1024、50%）{dt2:.2f}s、"
              f"加 RRC 量測濾波器 {dt3:.2f}s、'Auto'（一段 1e6 點、NFFT 2^20）{dt4:.2f}s（白雜訊 ACPR ≈ 0 dBc：{r3['acpr'][0]:.3f}）")

    # 7. 分析器實測（spectrumAnalyzer R2025a 的 getMeasurementsData；tests/matlab_ref/scope/acpr/acpr_scope_ref.json，23 個 acpr_* capture）
    sdir = os.path.join(ref_dir, "scope", "acpr")
    spath = os.path.join(sdir, "acpr_scope_ref.json")
    if not os.path.isfile(spath):
        check(False, f"沒有 {spath}：分析器實測（23 個 acpr_* capture）無法比對")
        return
    SR = json.load(open(spath, encoding="utf-8"))
    sig = {"acpr_sig_cplx.txt": xc, "acpr_sig_real.txt": xr}
    disp_bad, disp_n, disp_worst = [], 0, 0.0
    res_none, res_filt = {}, {}
    nan_bands = []
    known = {}
    stale = []
    stored = {}
    for cap in SR["captures"]:
        name, sc, cfg, ms, dsp = cap["name"], cap["scope"], cap["config"], cap["measurements"], cap["display"]
        x = sig[cap["signal"]["file"]]
        L = int(sc["window_length"])
        nfft = scope_nfft(L)
        w = design_window("hann", L)
        nov = overlap_samples(L, float(sc["overlap_percent"]))
        mode = "centered" if sc["two_sided"] else "onesided"
        r = welch(x, fs, w, nov, nfft, mode)
        psd_mode = sc["spectrum_type"] == "power-density"
        shown = power_in_units(r["psd"] if psd_mode else r["power"], "dBm")    # 畫面值：dBm 或 dBm/Hz（ReferenceLoad 1）
        if dsp["fresh"]:
            smp = dsp["samples"]
            idx = np.asarray(smp["index"], dtype=int)
            e_disp = absdiff(shown[idx], arr(smp["value"]))
            disp_worst = max(disp_worst, e_disp)
            disp_n += idx.size
            if not (r["f"].size == dsp["nbins"] and close(r["f"][idx], arr(smp["f_Hz"]), rtol=0.0, atol=1e-9)
                    and abs(r["f"][0] - dsp["f_first_Hz"]) <= 1e-9 and abs(r["f"][-1] - dsp["f_last_Hz"]) <= 1e-9
                    and abs(fs / nfft - dsp["df_Hz"]) <= 1e-12 and abs(r["rbw"] - dsp["RBW_hann_periodic_Hz"]) <= 1e-12
                    and e_disp <= ATOL_DISP_DB):
                disp_bad.append(f"{name}（畫面抽樣最大差 {e_disp:.1e} dB，bins {r['f'].size}/{dsp['nbins']}）")
        else:
            stale.append(name)
        if "stored_spectrum" in dsp:                                   # Welch capture：量測只能從存下的畫面重算
            st = dsp["stored_spectrum"]
            f_use = np.loadtxt(os.path.join(sdir, st["f_file"]))
            s_use = np.loadtxt(os.path.join(sdir, st["S_file"]))
            p_use = psd_from_display(s_use, st["units"], r["rbw"])
            stored[name] = absdiff(shown, s_use) if shown.size == s_use.size else math.inf   # 15 段平均 vs 存下的畫面
        else:
            f_use, p_use = r["f"], r["psd"]
        kw = dict(adj_bw=cfg["AdjacentBW"], offsets=cfg["ACPROffsets"], num_offsets=cfg["NumOffsets"], shape=cfg["FilterShape"],
                  coeff=cfg["FilterCoeff"], rule="scope")
        if cfg["FrequencySpan"] == "span-and-center-frequency":
            res = acpr(f_use, p_use, cfg["CenterFrequency"], cfg["Span"], **kw)
        else:
            res = acpr(f_use, p_use, start=cfg["StartFrequency"], stop=cfg["StopFrequency"], **kw)
        ref_cp, ref_lo, ref_up = float(ms["ChannelPower"]), arr(ms["ACPRLower"]), arr(ms["ACPRUpper"])
        e = (abs(res["channel_power"] - ref_cp), absdiff(res["lower_dBc"], ref_lo), absdiff(res["upper_dBc"], ref_up))
        for k in range(res["n"]):
            if np.isnan(ref_lo[k]):
                nan_bands.append(f"{name} lower{k + 1} {res['lower_bands'][k].tolist()}")
            if np.isnan(ref_up[k]):
                nan_bands.append(f"{name} upper{k + 1} {res['upper_bands'][k].tolist()}")
        if cap["analysis"].get("not_assessable"):
            known[name] = (e, cap["analysis"]["known_difference"], res, ref_cp, ref_lo, ref_up)
        elif cfg["FilterShape"] == "none":
            res_none[name] = e
        else:
            res_filt[name] = (cfg["FilterShape"], cfg["FilterCoeff"], e)
    check(not disp_bad and disp_n > 0 and len(SR["captures"]) == 23,
          f"分析器畫面模型：{len(SR['captures']) - len(stale)} 個畫面新鮮的 capture，從訊號重建（periodic Hann、NFFT = max(1024, L)、"
          f"power |X|²/(Σw)²／density |X|²/(fs·Σw²)、置中雙邊 Nyquist 在 +fs/2、單邊 ×2）的 bin 數、Δf、f_first／f_last、RBW 與 {disp_n} 個畫面抽樣"
          f"（dBm／dBm/Hz）一致，最大差 {disp_worst:.1e} dB（atol {ATOL_DISP_DB:g}）；畫面過期的 capture（量測仍新鮮、用模型頻譜）：{stale}"
          + (f"（不一致：{disp_bad}）" if disp_bad else ""))
    bad = [f"{k}: CP {v[0]:.1e} L {v[1]:.1e} U {v[2]:.1e} dB" for k, v in res_none.items() if max(v) > ATOL_SCOPE_DB]
    wn = max(max(v) for v in res_none.values()) if res_none else math.inf
    auto_two = auto_span((-fs / 2, fs / 2), fs, True)
    cfg_auto = [c for c in SR["captures"] if c["name"] == "acpr_cplx_2s_autospan_defaults"][0]["config"]
    check(not bad and len(res_none) == 13 and len(nan_bands) == 4 and cfg_auto["CenterFrequency"] == 1250 and auto_two["center"] == 0.0,
          f"分析器 ACPR（Filter Shape none，{len(res_none)} 個可評估的 capture（14 個 none 減去無法評估的 Welch three_pairs；RRC β=0 算在濾波組），"
          f"含 Start/Stop、三對、邊界剛好在 bin 中心、單邊實數、power-density、"
          f"Welch 1024/50%/15 從存下的畫面、Auto Span 預設留著舊 CF 1250）：Channel Power dBm、Lower／Upper dBc 和 getMeasurementsData 逐值一致，"
          f"最大差 {wn:.1e} dB（atol {ATOL_SCOPE_DB:g}）；格點外的頻帶只有自己是 NaN（{len(nan_bands)} 個：{nan_bands}）；純功率比（無 Span/AdjBW 正規化）；"
          f"偏移量從 (Start+Stop)/2 量；autospan_defaults 的 CF 1250 ≠ 自動算頻帶公式的 {auto_two['center']:g}（開啟 ACPR 時沒重算，觸發未定）"
          + (f"（不一致：{bad}）" if bad else ""))
    bad = [f"{k} {v[0]} {v[1]}: CP {v[2][0]:.1e} L {v[2][1]:.1e} U {v[2][2]:.1e} dB" for k, v in res_filt.items() if max(v[2]) > ATOL_SCOPE_DB]
    wf = max(max(v[2]) for v in res_filt.values()) if res_filt else math.inf
    shapes = sorted({(v[0], v[1]) for v in res_filt.values()})
    check(not bad and len(res_filt) == 9,
          f"分析器 ACPR（Filter Shape RRC／Gaussian，{len(res_filt)} 個 capture：{shapes}）：PSD × 功率權重（RRC = 升餘弦 |H|²、Rs = Span、β；"
          f"Gaussian = exp(−ln2·(Δf/(BT·Span))²)），同一個 Span 尺度的濾波器搬到每個相鄰頻帶中心、只在頻帶內積分、中心增益 1：Channel Power／Lower／Upper "
          f"逐值一致，最大差 {wf:.1e} dB（atol {ATOL_SCOPE_DB:g}）" + (f"（不一致：{bad}）" if bad else ""))
    # 已知差異：Welch three_pairs 的畫面和量測在不同平均狀態；兩個 Welch 畫面都不是 15 段平均（文件化的數字要固定住）
    kd_bad = []
    for name, (e, kd, res, ref_cp, ref_lo, ref_up) in known.items():
        doc = (kd["ChannelPower_dB"], kd["ACPRLower_dB"], kd["ACPRUpper_dB"])
        if not all(abs(a - b) <= ATOL_KNOWN_DB for a, b in zip(e, doc)):
            kd_bad.append(f"{name}: 偏差 {e} ≠ 分析報告的 {doc}")
        ds = kd["direct_sum"]
        doc2 = (ds["ChannelPower_dB"], ds["ACPRLower_dB"], ds["ACPRUpper_dB"])
        if not all(abs(a - b) <= ATOL_SCOPE_DB for a, b in zip(e, doc2)):
            kd_bad.append(f"{name}: 偏差 {e} ≠ 直接相加的文件化數字 {doc2}")
        on_disp = ds["computed_on_display"]
        if not (abs(res["channel_power"] - on_disp["ChannelPower"]) <= ATOL_SCOPE_DB and close(res["lower_dBc"], on_disp["ACPRLower"], rtol=0.0, atol=ATOL_SCOPE_DB)
                and close(res["upper_dBc"], on_disp["ACPRUpper"], rtol=0.0, atol=ATOL_SCOPE_DB)):
            kd_bad.append(f"{name}: 用存下的畫面算出的值和文件化的不同")
        if abs(stored[name] - kd["display_vs_15_segment_pwelch_mean_dB"]) > 1e-6:
            kd_bad.append(f"{name}: 畫面 vs 15 段平均 {stored[name]:.6f} ≠ 文件化 {kd['display_vs_15_segment_pwelch_mean_dB']:.6f} dB")
    wd = [c for c in SR["captures"] if c["name"] == "acpr_cplx_welch1024_psd_default_none"][0]
    doc_wd = wd["display"]["vs_pwelch_hann_periodic_max_abs_dB"]
    if abs(stored["acpr_cplx_welch1024_psd_default_none"] - doc_wd) > 1e-6:
        kd_bad.append(f"welch default: 畫面 vs 15 段平均 {stored['acpr_cplx_welch1024_psd_default_none']:.6f} ≠ 文件化 {doc_wd:.6f} dB")
    kn = known.get("acpr_cplx_welch1024_psd_three_pairs_none")
    check(not kd_bad and kn is not None and len(known) == 1,
          f"已知差異（Welch 1024/50%/15 的畫面狀態未解）：acpr_cplx_welch1024_psd_three_pairs_none 的畫面和量測在不同平均狀態抓到，用存下的畫面算的 "
          f"Channel Power／Lower／Upper 和分析器差 {kn[0][0]:.4f}／{kn[0][1]:.4f}／{kn[0][2]:.4f} dB（分析報告 0.0359／7.2607／7.1224 固定到 {ATOL_KNOWN_DB:g}"
          f"（它自己累積和的雜訊）、直接相加的數字固定到 {ATOL_SCOPE_DB:g}），"
          f"算出 {kn[2]['channel_power']:.6f} dBm、{np.round(kn[2]['lower_dBc'], 6).tolist()}／{np.round(kn[2]['upper_dBc'], 6).tolist()} dBc，分析器 "
          f"{kn[3]:.6f}、{np.round(kn[4], 6).tolist()}／{np.round(kn[5], 6).tolist()}；兩個 Welch 畫面對 15 段 pwelch 平均差 "
          f"{stored['acpr_cplx_welch1024_psd_default_none']:.2f}／{stored['acpr_cplx_welch1024_psd_three_pairs_none']:.2f} dB（文件化 17.47／8.74；"
          f"λ=(N−1)/(N+1) 指數平均與任何部分平均也都 ≥ 9.5 dB）" + (f"（{kd_bad}）" if kd_bad else ""))
    # 被排除的規則在 default_none 上的偏差（分析報告：bandpower 0.21、inner 0.039、梯形 2.0e-3、bwnorm 3.01 dB）——證明 'scope' 不是隨便選的
    cap0 = [c for c in SR["captures"] if c["name"] == "acpr_cplx_2s_default_none"][0]
    r0 = welch(xc, fs, design_window("hann", 8192), 0, 8192, "centered")
    ref_lo0, ref_up0 = arr(cap0["measurements"]["ACPRLower"]), arr(cap0["measurements"]["ACPRUpper"])
    alt = {}
    for rule in MATLAB_RULES:
        ra = acpr(r0["f"], r0["psd"], 0.0, 2000.0, 1000.0, (2000.0, 3500.0), rule=rule)
        alt[rule] = max(abs(ra["channel_power"] - cap0["measurements"]["ChannelPower"]), absdiff(ra["lower_dBc"], ref_lo0), absdiff(ra["upper_dBc"], ref_up0))
    rbw0 = acpr_bwnorm(r0["f"], r0["psd"], 0.0, 2000.0, 1000.0, (2000.0, 3500.0))
    alt["bwnorm"] = max(absdiff(rbw0["lower_dBc"], ref_lo0), absdiff(rbw0["upper_dBc"], ref_up0))
    r_rrc0 = acpr(r0["f"], r0["psd"], 0.0, 2000.0, 1000.0, (2000.0, 3500.0), shape="rrc", coeff=0.0)
    r_non0 = acpr(r0["f"], r0["psd"], 0.0, 2000.0, 1000.0, (2000.0, 3500.0))
    r_pow0 = acpr(r0["f"], psd_from_display(power_in_units(r0["power"], "dBm"), "dBm", r0["rbw"]), 0.0, 2000.0, 1000.0, (2000.0, 3500.0))
    r_den0 = acpr(r0["f"], psd_from_display(power_in_units(r0["psd"], "dBm"), "dBm/Hz"), 0.0, 2000.0, 1000.0, (2000.0, 3500.0))
    check(alt["bp"] > 0.1 and alt["in"] > 0.01 and alt["tz"] > 1e-3 and abs(alt["bwnorm"] - 10 * math.log10(2.0)) < 1e-6
          and np.array_equal(r_rrc0["lower_dBc"], r_non0["lower_dBc"]) and np.array_equal(r_rrc0["upper_dBc"], r_non0["upper_dBc"])
          and r_rrc0["main_power"] == r_non0["main_power"]
          and close(r_pow0["lower_dBc"], r_non0["lower_dBc"], rtol=0.0, atol=1e-12) and close(r_den0["upper_dBc"], r_non0["upper_dBc"], rtol=0.0, atol=1e-12)
          and close(r_pow0["channel_power"], r_non0["channel_power"], rtol=0.0, atol=1e-12),
          f"分析器規則的證據（default_none）：工具箱規則對分析器的偏差 bandpower {alt['bp']:.3f}、inner {alt['in']:.4f}、梯形 {alt['tz']:.2e} dB，"
          f"comm 式頻寬正規化差 {alt['bwnorm']:.4f} dB（= 10·log10(2)）；RRC β=0 與 none 逐 bit 相同；畫面值 dBm/RBW 與 dBm/Hz 換成 PSD 後結果相同"
          f"（power 與 power-density 模式同一組數字）")
    # 'scope' 規則的單元性質：半個 bin 的兩端、整個 bin、單 bin 內、剛好在 f_first／f_last 可以算、Filter Shape 權重的形狀
    fg, pg = f0, p0                                                     # c_hann：1024 bins 置中、Δf = fs/1024
    dfg = fs / 1024
    full, _ = band_power(fg, pg, fg[0], fg[-1])
    one_bin, _ = band_power(fg, pg, fg[300] - dfg / 2, fg[300] + dfg / 2)
    in_bin, _ = band_power(fg, pg, fg[300] - dfg / 4, fg[300] + dfg / 4)
    two_half, _ = band_power(fg, pg, fg[300], fg[301])
    out_lo, c_lo = band_power(fg, pg, fg[0] - 1e-9, fg[5])
    out_hi, c_hi = band_power(fg, pg, fg[5], fg[-1] + 1e-9)
    w_rrc = filter_weights(fg, 0.0, "rrc", 0.35, 2000.0)
    w_gau = filter_weights(fg, 100.0, "gaussian", 0.3, 2000.0)
    w_bw = filter_weights(np.array([-1000.0, -999.0, 0.0, 999.0, 1000.0, 1000.5]), 0.0, "rrc", 0.0, 2000.0)
    w_g0 = filter_weights(np.array([-1.0, 0.0, 1.0]), 0.0, "gaussian", 0.0, 2000.0)
    edge = (1 - 0.35) * 1000.0
    w_edge = filter_weights(np.array([edge, (1 + 0.35) * 1000.0, 1000.0]), 0.0, "rrc", 0.35, 2000.0)
    ok = (close(full, float(np.sum(pg) * dfg - (pg[0] + pg[-1]) * dfg / 2), rtol=1e-12)
          and close(one_bin, pg[300] * dfg, rtol=1e-12) and close(in_bin, pg[300] * dfg / 2, rtol=1e-12)
          and close(two_half, (pg[300] + pg[301]) * dfg / 2, rtol=1e-12)
          and math.isnan(out_lo) and c_lo and math.isnan(out_hi) and c_hi
          and w_rrc[np.argmin(np.abs(fg))] == 1.0 and np.all(w_rrc[np.abs(fg) > 1350.0] == 0.0) and np.all(w_rrc[np.abs(fg) <= 650.0] == 1.0)
          and np.all((w_rrc >= 0.0) & (w_rrc <= 1.0)) and close(w_edge, [1.0, 0.0, 0.5], rtol=0.0, atol=1e-15)
          and close(w_gau[np.argmin(np.abs(fg - 100.0))], math.exp(-math.log(2) * ((fg[np.argmin(np.abs(fg - 100.0))] - 100.0) / 600.0) ** 2), rtol=1e-12)
          and close(w_gau[np.argmin(np.abs(fg - 700.0))], math.exp(-math.log(2) * ((fg[np.argmin(np.abs(fg - 700.0))] - 100.0) / 600.0) ** 2), rtol=1e-12)
          and np.array_equal(w_bw, [1.0, 1.0, 1.0, 1.0, 1.0, 0.0]) and np.array_equal(w_g0, [0.0, 1.0, 0.0])
          and filter_weights(fg, 0.0, "none") is None and filter_weights(fg, 0.0, None) is None)
    ok = ok and scope_nfft(1000) == 1024 and scope_nfft(1999) == 1999 and scope_nfft(8192) == 8192 and scope_nfft(1024) == 1024
    check(ok, "'scope' 規則的單元性質：NFFT auto = max(1024, L)（1000→1024、1999→1999、8192→8192）；整個格點 = Σp·Δf − 兩端各半個 bin；"
              "一個 bin 的區間 = p·Δf、bin 內一半 = p·Δf/2、兩個相鄰 bin 中心之間 = 各半個；"
              "邊界超出 f_first／f_last 一點點 → NaN 且 clipped；RRC 權重中心 1、|Δ| ≤ (1−β)Rs/2 為 1、(1+β)Rs/2 外為 0、過渡帶中點 0.5；"
              "Gaussian 權重 = exp(−ln2·(Δ/(BT·Span))²)；RRC β=0 磚牆 |Δ| ≤ Span/2；Gaussian BT=0 只在 Δ=0 為 1（未定的極限形式）")


def _rcosdesign_sqrt(beta: float, span: int, sps: int) -> np.ndarray:
    """MATLAB rcosdesign(beta, span, sps, 'sqrt')：根升餘弦 FIR（長度 span·sps + 1，單位能量），只給 selftest 做參考濾波器用；
    公式照 Signal Processing Toolbox 文件 rcosdesign 的 Algorithms（t = 符號時間，奇異點 t = 0 與 |t| = 1/(4β) 用極限值）。
    長度超過 MAX_ELEMENTS → ACPRError dsv:tooLarge。"""
    if span * sps + 1 > MAX_ELEMENTS:
        raise _err("dsv:tooLarge", span * sps + 1, "RRC filter taps", MAX_ELEMENTS)
    n = np.arange(-span * sps / 2.0, span * sps / 2.0 + 1) / sps          # 以符號為單位的時間
    h = np.empty(n.size)
    with np.errstate(divide="ignore", invalid="ignore"):
        num = np.sin(np.pi * n * (1 - beta)) + 4 * beta * n * np.cos(np.pi * n * (1 + beta))
        den = np.pi * n * (1 - (4 * beta * n) ** 2)
        h = num / den
    z = np.isclose(n, 0.0)
    h[z] = 1 - beta + 4 * beta / np.pi
    s = np.isclose(np.abs(n), 1.0 / (4 * beta)) if beta > 0 else np.zeros(n.size, dtype=bool)
    h[s] = beta / math.sqrt(2) * ((1 + 2 / np.pi) * math.sin(math.pi / (4 * beta)) + (1 - 2 / np.pi) * math.cos(math.pi / (4 * beta)))
    return h / math.sqrt(np.sum(h * h))
