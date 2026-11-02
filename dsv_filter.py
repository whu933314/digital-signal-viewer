# -*- coding: utf-8 -*-
"""濾波（MATLAB Signal Analyzer 的 PREPROCESS › FUNCTIONS › FILTER：Lowpass／Highpass／Bandpass／Bandstop）——純 numpy，和 GUI 分開。只做 FIR。

依據（MATLAB R2025a Signal Processing Toolbox。行為照公開文件與實測輸出對照，程式是自己寫的；
tests/matlab_ref/filters/ 是 MATLAB 算出的數值（研究用 make_filters_ref.m／run_app_equiv.m 產生），selftest() 把 128 個濾波案例、
20 個錯誤案例、12 組程式碼產生器字串、18 組 Signal Analyzer 實測案例逐筆比對）：
- Signal Analyzer 的 Apply 輸出等於公開函式 lowpass／highpass／bandpass／bandstop 的結果（它產生的 MATLAB 程式碼就是這些呼叫；研究時用實測輸出驗證，17 組設定差 0）：
  以樣本為單位的訊號 → lowpass(x, Wn, 'Steepness', s, 'StopbandAttenuation', A)（Wn 以 ×π rad/sample 計，Nyquist = 1）；
  均勻取樣的時間訊號 → lowpass(x, Fpass, Fs, ...)，Fs 是訊號的平均取樣率。產生的程式碼不帶 ImpulseResponse（即 'auto'）。
  帶通／帶阻的「Steepness」單一模式傳純量 s1（不是函式預設的 [0.85 0.85]，兩者設計不同）、雙模式傳 [s1 s2]。app_call() 做這個對應。
- 參數檢查照 MATLAB 的順序：資料（型別→有限）、Fs（非空、實數、有限、純量、正）、Wpass（同上；帶通／帶阻要 2 個嚴格遞增）、
  沒給 Fs 時 Wpass 必須 < 1、StopbandAttenuation ≥ 10、Steepness（低通／高通純量 ∈ [0.5, 1)；帶通／帶阻純量或 2 元素 ∈ [0.5, 1]）。
  錯誤丟 FilterError（identifier 是 MATLAB 的識別字；訊息英文照 MATLAB、message_zh 是繁體中文）。
- 過渡帶寬度 T(s) = 0.99 − 0.98·s（頻率都先正規化到 Nyquist = 1；lowpass／bandpass／bandstop 文件「More About › Steepness」）：
  低通 Ws = Wp + T·(1 − Wp)；高通 Ws = Wp − T·Wp；
  帶通 Tw1 = T1·Wp1、Tw2 = T2·(1 − Wp2)，Ws = [Wp1 − Tw1, Wp2 + Tw2]；
  帶阻 c = (Wp1 + Wp2)/2、Tw1 = T1·(c − Wp1)、Tw2 = T2·(Wp2 − c)，Ws = [Wp1 + Tw1, Wp2 − Tw2]；
  帶通／帶阻給純量陡度時兩邊都用 min(Tw1, Tw2)。
- 特例：低通 L ≤ 3 或 Wp ≥ 1 → 全通（係數 [1]）；高通 Wp ≥ 1 → 全阻（[0]），否則 L ≤ 3 → 全通；帶通／帶阻 L ≤ 6 → 全通
  （警告 AllPassBecauseSignalIsTooShort 的樣本數照發出警告的函式：低通／高通寫 3、帶通／帶阻寫 6）；
  帶通 Wp2 ≥ 1 → 結果等同 highpass(Wp1, Steepness(1))（警告 ForcedHighpassDesign；ImpulseResponse 用 'auto'）；帶阻 Wp2 ≥ 1 → 等同 lowpass。
  全通／全阻的 digitalFilter 沒有設計規格：MATLAB 回報 SampleRate 2（即使給了 Fs）、ImpulseResponse 'ect'，info['spec'] 照報。
- 所需 FIR 階數 N_req ＝ kaiserord 的估計（Kaiser 的經驗式）：每個過渡帶 L_k = (A − 7.95)/(2π·2.285·Δf) + 1，
  A = −20·log10(δ_min)，δ 取過渡帶兩側較小的偏差（通帶 δp = (10^(Ap/20) − 1)/(10^(Ap/20) + 1)，Ap = 0.1 dB 內部固定；
  阻帶 δs = 10^(−As/20)），Δf 以 cycles/sample 計；取最大的 L_k，N = ceil(L) − 1；N 奇數且最後一帶是通帶時再 + 1。
  FIR／IIR 切換用的 N_req 以「給定單位」的帶界和 Fs 照 kaiserord 估計；濾波器設計用正規化帶界。兩條都照做（捨入會差；切換點和
  MATLAB 的實測輸出一致，見 selftest）。
- FIR／IIR 的選擇（ImpulseResponse 參數）：'auto' 且 L ≤ 2·N_req → MATLAB 改走最小階橢圓 IIR＋filtfilt；'fir' 且 L ≤ 2·N_req →
  錯誤 SignalLengthForFIR；'iir' → 一律 IIR。
  **DSV 的決定（使用者 2026-10-24 拍板：只做 FIR）**：'auto' 且 L ≤ 2·N_req → 丟 FilterError('dsv:filter:SignalTooShortForFIR')，
  訊息說明訊號有幾個樣本、所需階數、至少要 2·N_req + 1 個樣本（英文＋繁體中文；e.length／e.required_order／e.min_length 給 UI 用）；
  'iir' → FilterError('dsv:filter:IIRNotImplemented')；'fir' 太短 → MATLAB 自己的 SignalLengthForFIR（識別字與英文訊息照 MATLAB）。
  128 個參考案例裡 MATLAB 走 IIR 的 64 個（含 6 個強制 'iir'）DSV 都拒絕；它們的 MATLAB 輸出留在參考檔裡沒有被比對（見「已知差異」）。
- FIR 設計 ＝ designfilt(..., 'DesignMethod', 'kaiserwin', 'MinOrder', 'even')：
  (a) 帶通／帶阻先把較寬的過渡帶縮成和較窄的一樣（兩邊同寬，窄的那邊保留原來的邊界；兩邊一樣寬就都不動）再算 kaiserord，
      所以雙陡度在 FIR 時只有較陡的那邊有作用；
  (b) N 奇數 → N + 1；β 由整體最小偏差的 A 換算（A > 50：0.1102(A − 8.7)；21 ≤ A ≤ 50：0.5842(A − 21)^0.4 + 0.07886(A − 21)；A < 21：0）；
  (c) b = fir1(N, Wn, type, kaiser(N + 1, β))：理想磚牆響應（截止在每個過渡帶的中點 Wn）的 sinc 乘 Kaiser 窗，再正規化增益——
      低通／帶阻在 DC 為 1、高通在 Nyquist 為 1、帶通在通帶中心為 1；
  (d) 規格檢查：每個阻帶取 4096 個等距頻率、每個通帶 1024 個量 |H|，要 −20·log10(max|H_stop|) > As 且 20·log10(max/min |H_pass|) < Ap
      才算達標；沒達標就 N + 2（保持偶數）重做，最多做 10 個設計；都沒達標就用第一次的設計。量測的帶界用縮窄前的原始規格。
- FIR 濾波：y = filter(b, 1, [x; zeros(N/2)]) 取第 N/2 + 1 個樣本起（線性相位的群延遲補償，長度不變）；複數訊號直接濾（係數是實數）。
- single（float32）輸入用 double 計算、回傳 double（MATLAB 會轉回 single）。
- 2 維輸入：(1, n) 當列向量（MATLAB isrow），其他照欄逐欄濾（MATLAB 的矩陣輸入）。

已知差異（selftest 用「已知差異」那條 check 把它們釘住）：
- 64 個 MATLAB 走 IIR 的案例（23 個截短階數＋35 個最小階橢圓＋6 個強制 'iir'）：MATLAB 有輸出，DSV 丟 SignalTooShortForFIR／IIRNotImplemented。
  比對的只有切換判斷（L ≤ 2·N_req）、訊息裡的數字、以及與設計法無關的規格欄位（PassbandFrequency、StopbandFrequency、SampleRate、
  StopbandAttenuation、PassbandRipple）；MATLAB 的 IIR 階數照 ref_iir_vs_ellip.json 列出。
- highpass_045（L = 4）：MATLAB 走 IIR 後在 filtfilt 丟 signal:filtfilt:InvalidDimensionsDataShortForFiltOrder；DSV 丟 dsv:filter:SignalTooShortForFIR。
- app_equiv.json 的 18 組 Signal Analyzer 實測案例裡有 7 組 300 點訊號在 MATLAB 走 IIR（2·N_req ≥ 300）：DSV 丟 SignalTooShortForFIR。

未定／自行決定：
- 階數上限 MAX_FIR_ORDER = 2²⁰ taps（DSV 自訂防呆；MATLAB 沒有上限）：N_req 超過就丟 FilterError('dsv:filter:FilterOrderTooLarge')，
  不配置幾百 MB 的係數。design(length=None)（UI 預覽，當無限長）和給了超長訊號的 filter_signal 都受這條保護；過渡帶寬度在雙精度下為 0 也算。
- StopbandAttenuation 大到線性阻帶偏差 10^(−A/20) 下溢成 0（A > 6165 dB）→ FilterError('dsv:filter:StopbandAttenuationTooLarge')；
  MATLAB 在這裡會算出 Inf／NaN 然後在 kaiserord 裡報錯。
- 非數值的參數（字串、None、bool）→ FilterError('MATLAB:<fn>:invalidType')，訊息照 validateattributes 的格式寫（這條沒有參考資料可對）；
  複數參數 → MATLAB:<fn>:expectedReal。ImpulseResponse 不是 'auto'／'fir'／'iir' → FilterError('dsv:filter:InvalidImpulseResponse')。
- |H| 的計算全部向量化（審查要求拿掉 Python 逐係數的 Horner 迴圈）：等距頻率格點（規格檢查的 linspace、freqz 的 k/256）用 Bluestein chirp-z
  （一條 FFT 卷積），任意格點用分塊 DFT。兩者的相位都先對 2π 取餘數再算（係數拆成三段各 12 位元，和 < 2⁴¹ 的整數相乘不捨入），
  所以精度不隨階數變差：對「相位取餘數的逐項＋math.fsum 補償加總」參考值，chirp-z 的誤差 ≤ 5e-13 × Σ|b|（≤ 3001 taps；65537 taps 抽 48 點
  也是 4.5e-13，全 4096 點最大 ~3e-12：FFT 捨入 ∝ √(N+M)），和 Horner 同級（Horner 的相位漂移 ∝ N·eps，65537 taps 也是 ~3e-12）；
  分塊 DFT ~1e-15 但 O(N·F)。
  不取餘數直接乘相位的 chirp-z 在 65537 taps 的 −104 dB 阻帶會差到 3e-6 相對。|H|@256 和 MATLAB freqz 差 ≤ 1e-14；
  128 個參考案例的設計決策（每次規格檢查的裕度 ≥ 2.7e-4 dB）和 Horner 完全相同。
- 卷積：N·L ≤ 2×10⁷ 用 np.convolve（和 MATLAB filter 一樣的直接算法），更大用分段 overlap-add FFT（FFT 長度最多 2²¹，記憶體有界），
  兩者差 ≤ 1e-15 相對。參考案例的階數 ≤ 450、L ≤ 1000，都走直接卷積。
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

KINDS = ("lowpass", "highpass", "bandpass", "bandstop")
IMPULSE = ("auto", "fir", "iir")
DEFAULT_STEEPNESS = 0.85
STEEPNESS_MIN, STEEPNESS_MAX, STEEPNESS_STEP = 0.5, 0.9999, 0.05      # Signal Analyzer 的 Steepness spinner
DEFAULT_ATTEN = 60.0
MIN_ATTEN = 10.0
PASSBAND_RIPPLE = 0.1                                               # 內部固定的 Apass（dB）
DEFAULT_WN = {"lowpass": 0.5, "highpass": 0.5, "bandpass": (0.25, 0.75), "bandstop": (0.25, 0.75)}   # samples 模式的預設通帶
MAX_REDESIGN = 10                                                   # 規格檢查最多做幾個設計
MAX_FIR_ORDER = 1 << 20                                             # 所需階數的上限（DSV 自訂防呆；MATLAB 沒有）
ALLPASS_MIN_LENGTH = {"lowpass": 3, "highpass": 3, "bandpass": 6, "bandstop": 6}    # L ≤ 這個數 → 全通
SPEC_STOP_POINTS, SPEC_PASS_POINTS = 4096, 1024                     # 規格檢查每個阻帶／通帶量幾點
_DIRECT_CONV_MAX_OPS = 2e7                                          # N·L 超過這個就用 overlap-add FFT 卷積
_OLA_MAX_FFT = 1 << 21                                              # overlap-add 的 FFT 長度上限（記憶體有界）
_EXACT_PRODUCT_MAX = 2.0 ** 41                                      # 相位分段法要求的整數上限（12 + 41 ≤ 53 位元）

# Signal Analyzer 面板的字串（英文照 MATLAB 介面顯示的文字、繁體中文由簡中轉）；UI 用，計算不用
UI_TEXT = {
    "lowpass": ("Lowpass", "低通"), "highpass": ("Highpass", "高通"), "bandpass": ("Bandpass", "帶通"), "bandstop": ("Bandstop", "帶阻"),
    "filter": ("FILTER", "濾波器"), "params": ("Function Parameters", "函式參數"), "specs": ("FILTER SPECIFICATIONS", "濾波器設定"),
    "units": ("Frequency Units", "頻率單位"), "fpass": ("Passband Frequency", "通帶頻率"),
    "fpass1": ("Lower Passband Frequency", "下通帶頻率"), "fpass2": ("Upper Passband Frequency", "上通帶頻率"),
    "steepness": ("Steepness", "陡度"), "steepness1": ("Lower Band Steepness", "下頻帶陡度"), "steepness2": ("Upper Band Steepness", "上頻帶陡度"),
    "atten": ("Stopband Attenuation(dB)", "阻帶衰減(dB)"), "apply": ("Apply", "套用"), "defaults": ("Restore Defaults", "還原預設值"),
    "err_wn": ("Passband frequency must be a numeric scalar in the (0,1) range", "通帶頻率必須為 (0,1) 範圍內的數值純量"),
    "err_fpass": ("Passband frequency must be a positive scalar", "通帶頻率必須為正純量"),
    "err_order": ("Lower passband frequency must be smaller than upper passband frequency", "下通帶頻率必須小於上通帶頻率"),
    "err_steep": ("Steepness must be a numeric scalar in the [0.5,1) range", "陡度必須為 [0.5,1) 範圍內的數值純量"),
    "err_atten": ("Stopband attenuation must be a numeric positive scalar greater than or equal to 10 dB", "阻帶衰減必須為大於或等於 10 dB 的正數值純量"),
}

# 警告（MATLAB 的識別字尾 → 英文、繁體中文；英文照 MATLAB 的警告訊息，繁體中文由簡中轉）
WARNINGS = {
    "ForcedAllpassDesign": ("Specified passband frequency is beyond the Nyquist range so signal has been filtered with an allpass filter.",
                            "指定的通帶頻率超出 Nyquist 範圍，所以用全通濾波器處理了訊號。"),
    "ForcedAllstopDesign": ("Specified passband frequency is beyond the Nyquist range so signal has been filtered with an allstop filter.",
                            "指定的通帶頻率超出 Nyquist 範圍，所以用全阻濾波器處理了訊號。"),
    "ForcedLowpassDesign": ("Specified passband frequency is beyond the Nyquist range so signal has been filtered with a lowpass filter.",
                            "指定的通帶頻率超出 Nyquist 範圍，所以改用低通濾波器處理了訊號。"),
    "ForcedHighpassDesign": ("Specified passband frequency is beyond the Nyquist range so signal has been filtered with a highpass filter.",
                             "指定的通帶頻率超出 Nyquist 範圍，所以改用高通濾波器處理了訊號。"),
    "AllPassBecauseSignalIsTooShort": ("Signals less than {n} samples long are filtered with an allpass filter.",
                                       "長度不超過 {n} 個樣本的訊號用全通濾波器處理。"),
}
WARNING_PREFIX = "signal:internal:filteringfcns:"

_MSG = {   # FilterError 的訊息：識別字尾 → (英文, 繁體中文)
    "InvalidInputDataType": ("Input data must be a vector or a matrix with double or single precision, or a timetable.",
                             "輸入資料必須是雙精度或單精度浮點數的向量或矩陣。"),
    "InvalidVectorOrMatrixType": ("Input data must be a finite, nonsparse, double or single precision vector or matrix.",
                                  "輸入資料必須是有限（沒有 NaN／Inf）的雙精度或單精度向量或矩陣。"),
    "InvalidNormalizedWpassValue": ("Normalized passband frequency values must be in the (0,1) interval. Use a value in the (0,1) interval or specify a sample rate.",
                                    "正規化通帶頻率必須在 (0,1) 區間內。請用 (0,1) 區間內的值，或指定取樣率。"),
    "InvalidSteepness": ("Steepness must be a scalar or a two element vector with values in the range [0.5,1).",
                         "陡度必須是純量或 2 元素向量，值在 [0.5,1) 範圍內。"),
    "SignalLengthForFIR": ("Signal length must be greater than twice the required FIR filter order (RequiredOrder = {n}).\n"
                           "Relax the steepness and stopband attenuation values to reduce the required filter order or increase the signal length.",
                           "訊號長度必須大於所需 FIR 濾波器階數的兩倍（RequiredOrder = {n}）。\n請放寬陡度與阻帶衰減值以降低所需的濾波器階數，或增加訊號長度。"),
    # DSV 自己的
    "SignalTooShortForFIR": ("The signal has {L} samples, but the FIR filter for these settings needs order {n}, so at least {need} samples "
                             "(more than twice the order) are required. Relax the steepness and stopband attenuation values to reduce the required "
                             "order, or use a longer signal. (MATLAB would switch to a minimum-order IIR filter here; DSV designs FIR filters only.)",
                             "訊號只有 {L} 個樣本，這組設定的 FIR 濾波器需要 {n} 階，至少要 {need} 個樣本（多於階數的兩倍）。"
                             "請放寬陡度與阻帶衰減值以降低所需階數，或用更長的訊號。（MATLAB 在這裡會改用最小階 IIR 濾波器；DSV 只做 FIR。）"),
    "IIRNotImplemented": ("ImpulseResponse 'iir' is not available: DSV designs FIR filters only (use 'auto' or 'fir').",
                          "ImpulseResponse 'iir' 不支援：DSV 只做 FIR 濾波器（請用 'auto' 或 'fir'）。"),
    "FilterOrderTooLarge": ("The required FIR filter order ({n}) exceeds the DSV limit of {max}. Relax the steepness and stopband attenuation "
                            "values, or move the passband frequency away from 0 and Nyquist. (MATLAB has no such limit.)",
                            "所需的 FIR 濾波器階數（{n}）超過 DSV 的上限 {max}。請放寬陡度與阻帶衰減值，或讓通帶頻率離 0 與 Nyquist 遠一點。"
                            "（MATLAB 沒有這個上限。）"),
    "StopbandAttenuationTooLarge": ("StopbandAttenuation {v} dB is too large to design a filter in double precision.",
                                    "阻帶衰減 {v} dB 太大，雙精度算不出濾波器。"),
    "InvalidImpulseResponse": ("ImpulseResponse must be 'auto', 'fir' or 'iir'.", "ImpulseResponse 必須是 'auto'、'fir' 或 'iir'。"),
    "InvalidKind": ("Filter kind must be lowpass, highpass, bandpass or bandstop.", "濾波器種類必須是 lowpass、highpass、bandpass 或 bandstop。"),
    # validateattributes 風格（識別字 MATLAB:<函式>:<尾>）
    "invalidType": ("Expected {name} to be one of these types:\n\nnumeric\n\nInstead its type was {t}.", "{name} 必須是數值型別，給的是 {t}。"),
    "expectedPositive": ("Expected {name} to be positive.", "{name} 必須為正數。"),
    "expectedFinite": ("Expected {name} to be finite.", "{name} 必須是有限值。"),
    "expectedReal": ("Expected {name} to be real.", "{name} 必須是實數。"),
    "expectedNonempty": ("Expected {name} to be nonempty.", "{name} 不可為空。"),
    "expectedScalar": ("Expected {name} to be a scalar.", "{name} 必須是純量。"),
    "expectedVector": ("Expected {name} to be a vector.", "{name} 必須是向量。"),
    "expectedIncreasing": ("Expected {name} to be strictly increasing.", "{name} 必須嚴格遞增。"),
    "incorrectNumel": ("Expected {name} to be an array with number of elements equal to {n}.", "{name} 必須是 {n} 個元素的陣列。"),
    "notGreaterEqual": ("Expected {name} to be a scalar with value >= {v}.", "{name} 必須是 ≥ {v} 的純量。"),
    "notLess": ("Expected {name} to be a scalar with value < {v}.", "{name} 必須是 < {v} 的純量。"),
}


class FilterError(ValueError):
    """參數或訊號不合規格。identifier＝MATLAB 的錯誤識別字（DSV 自己加的用 dsv:filter:…）；str(e)＝英文訊息；message_zh＝繁體中文。
    details＝訊息裡用到的數字（SignalTooShortForFIR 另有 length／required_order／min_length 屬性給 UI 用）。"""

    def __init__(self, identifier: str, **fmt: Any):
        key = identifier.rsplit(":", 1)[-1]
        en, zh = _MSG[key]
        en, zh = en.format(**fmt), zh.format(**fmt)
        super().__init__(en)
        self.identifier = identifier
        self.message = en
        self.message_zh = zh
        self.details = dict(fmt)
        self.length = fmt.get("L")
        self.required_order = fmt.get("n")
        self.min_length = fmt.get("need")


def _err(key: str, **fmt: Any) -> FilterError:
    return FilterError(WARNING_PREFIX + key, **fmt)


def _dsv_err(key: str, **fmt: Any) -> FilterError:
    return FilterError("dsv:filter:" + key, **fmt)


def _attr_err(func: str, key: str, **fmt: Any) -> FilterError:
    return FilterError(f"MATLAB:{func}:{key}", **fmt)


def _g(v: float) -> str:
    """數字照 MATLAB 的簡短寫法（0.5、1、10、123.4）。"""
    return "%.15g" % float(v)


def warning_text(keyword: str, zh: bool = False, kind: str = "lowpass") -> str:
    """警告關鍵字（例如 ForcedAllpassDesign）→ 訊息文字。AllPassBecauseSignalIsTooShort 的樣本數看發出警告的函式：低通／高通 3、帶通／帶阻 6。"""
    en, tw = WARNINGS[keyword]
    return (tw if zh else en).format(n=ALLPASS_MIN_LENGTH.get(kind, 3))


# ---------------------------------------------------------------- 基本公式
def kaiser_beta(atten: float) -> float:
    """阻帶衰減 A（dB）→ Kaiser 窗 β（和 dsv_spectrum.kaiser_beta 同一條公式）。"""
    a = float(atten)
    if a > 50:
        return 0.1102 * (a - 8.7)
    if a < 21:
        return 0.0
    return 0.5842 * (a - 21) ** 0.4 + 0.07886 * (a - 21)


def _pow10(x: float) -> float:
    """10^x，溢位時回 inf（不丟 OverflowError）。"""
    with np.errstate(over="ignore"):
        return float(np.power(10.0, float(x)))


def linear_dev(db: float, band: str) -> float:
    """dB → 線性偏差：通帶 (10^(A/20) − 1)/(10^(A/20) + 1)（漣波 ±A dB），阻帶 10^(−A/20)（太大時下溢成 0，呼叫端要檢查）。"""
    r = _pow10(float(db) / 20.0)
    if band == "pass":
        return (r - 1.0) / (r + 1.0)
    return 0.0 if r == math.inf else 1.0 / r


def transition_width(steepness: float) -> float:
    """Steepness s → 過渡帶占可用頻寬的比例 T(s) = 0.99 − 0.98·s。"""
    return -0.98 * float(steepness) + 0.99


def kaiser_fir_order(edges: Sequence[float], gains: Sequence[float], devs: Sequence[float], fs: float = 2.0) -> Tuple[int, np.ndarray, float, str]:
    """Kaiser 窗 FIR 的階數估計（MATLAB kaiserord 的定義，自己的寫法）。
    edges：每個過渡帶的兩個邊界（單位同 fs，照頻率排）、gains：各帶的增益（0 或 1）、devs：各帶允許的偏差
    → (階數 N, 截止頻率 Wn＝各過渡帶中點（Nyquist = 1）, β, 型態 'low'／'high'／'bandpass'／'stop')。
    每個過渡帶看兩側較小的偏差 δ：A = −20·log10(δ)，Kaiser 經驗式 L = (A − 7.95)/(2π·2.285·Δf) + 1（Δf 以 cycles/sample 計）；
    取最長的那個過渡帶，N = ceil(L) − 1；最後一帶是通帶（高通／帶阻）而 N 是奇數就 + 1。β 用整體最小偏差的 A 算。
    過渡帶寬度在雙精度下為 0、或 N 超過 MAX_FIR_ORDER → FilterError('dsv:filter:FilterOrderTooLarge')（DSV 防呆）。"""
    f = np.asarray(edges, dtype=float).ravel() / float(fs)
    g = np.asarray(gains, dtype=float).ravel()
    d = np.asarray(devs, dtype=float).ravel()
    if g.size < 2 or f.size != 2 * (g.size - 1) or d.size != g.size:
        raise ValueError("kaiser_fir_order: need 2 edges per transition band and one deviation per band")
    if np.any(d <= 0):
        raise ValueError("kaiser_fir_order: deviations must be positive")
    lo, hi = f[0::2], f[1::2]
    width = np.abs(hi - lo)
    worst = np.minimum(d[:-1], d[1:])                               # 每個過渡帶兩側較嚴的偏差
    if np.any(width == 0):
        raise _dsv_err("FilterOrderTooLarge", n="inf", max=MAX_FIR_ORDER)
    length = (-20.0 * np.log10(worst) - 7.95) / (2.0 * math.pi * 2.285 * width) + 1.0
    longest = float(np.max(length))
    if not math.isfinite(longest) or longest > 1e15:
        raise _dsv_err("FilterOrderTooLarge", n="inf", max=MAX_FIR_ORDER)
    N = int(math.ceil(longest)) - 1
    if N % 2 == 1 and g[-1] != 0:
        N += 1
    beta = kaiser_beta(-20.0 * math.log10(float(np.min(d))))
    if g.size == 2:
        ftype = "high" if g[0] == 0 else "low"
    else:
        ftype = "bandpass" if g[0] == 0 else "stop"
    return N, lo + hi, beta, ftype


def fir1_kaiser(N: int, Wn, ftype: str, beta: float) -> np.ndarray:
    """MATLAB fir1(N, Wn, type, kaiser(N+1, β))（預設 'scale'）：磚牆理想響應的 sinc（截止 Wn，Nyquist = 1）乘 Kaiser 窗，
    再正規化——'low'／'stop' 讓 DC 增益為 1、'high' 讓 Nyquist 為 1、'bandpass' 讓通帶中心 (Wn1 + Wn2)/2 為 1。N 要是偶數。"""
    N = int(N)
    Wn = np.atleast_1d(np.asarray(Wn, dtype=float))
    m = np.arange(N + 1) - N / 2.0
    delta = (m == 0).astype(float)
    lp = [w * np.sinc(w * m) for w in Wn]
    t = ftype.lower()
    if t == "low":
        h = lp[0]
    elif t == "high":
        h = delta - lp[0]
    elif t in ("bandpass", "dc-0"):
        h = lp[1] - lp[0]
    elif t == "stop":
        h = delta - (lp[1] - lp[0])
    else:
        raise ValueError(f"fir1_kaiser: unsupported type {ftype!r}")
    b = h * np.kaiser(N + 1, float(beta))
    if t in ("low", "stop"):
        return b / np.sum(b)
    f0 = 1.0 if t == "high" else float(Wn[:2].mean())
    return b / abs(np.sum(b * np.exp(-1j * np.pi * np.arange(N + 1) * f0)))


# ---------------------------------------------------------------- 頻率響應（向量化：chirp-z／分塊 DFT，相位先對 2π 取餘數）
def _exp_neg_jpi(c, q) -> np.ndarray:
    """e^(−jπ·c·q)，c 任意浮點、q 是整數值的浮點（|q| < 2⁴¹）。c 拆成三段各 12 個有效位元：前三段和 q 的乘積都 ≤ 53 位元（不捨入），
    各自 fmod 2 之後相加，剩下的尾數乘 q 很小；所以相位對 2 的餘數準到 ~1e-16，不管 c·q 多大（直接乘會在 c·q ~ 1e7 時差到 1e-9）。"""
    c = np.asarray(c, dtype=float)
    q = np.asarray(q, dtype=float)
    if float(np.max(np.abs(q), initial=0.0)) >= _EXACT_PRODUCT_MAX:
        return np.exp(-1j * np.pi * (c * q))
    phase = 0.0
    rest = c
    for _ in range(3):
        mant, ex = np.frexp(rest)
        part = np.ldexp(np.floor(np.ldexp(mant, 12)), ex - 12)
        phase = phase + np.fmod(part * q, 2.0)
        rest = rest - part
    return np.exp(-1j * np.pi * (phase + rest * q))


def _chirpz(b: np.ndarray, f0: float, df: float, M: int) -> np.ndarray:
    """H_k = Σ_n b[n]·e^(−jπ(f0 + k·df)n)，k = 0..M−1（Bluestein：nk = (n² + k² − (k−n)²)/2，變成一條 FFT 線性卷積）。
    FFT 長度 ≥ N + M − 1 就夠（只需要卷積輸出的第 N−1..N+M−2 項不被繞回）。"""
    N = b.size
    n = np.arange(N, dtype=float)
    half = df / 2.0
    a = b * _exp_neg_jpi(f0, n) * _exp_neg_jpi(half, n * n)
    lag = np.arange(-(N - 1), M, dtype=float)                       # k − n 的範圍
    kern = np.conj(_exp_neg_jpi(half, lag * lag))
    size = 1 << (N + M - 2).bit_length()
    conv = np.fft.ifft(np.fft.fft(a, size) * np.fft.fft(kern, size))[N - 1:N - 1 + M]
    k = np.arange(M, dtype=float)
    return _exp_neg_jpi(half, k * k) * conv


def _block_dft(b: np.ndarray, f: np.ndarray, block: int = 256) -> np.ndarray:
    """H(f) = Σ_n b[n]·e^(−jπfn)，任意頻率：係數分塊，每塊一個 (F × block) 的指數矩陣乘係數（記憶體有界、全向量化）。"""
    H = np.zeros(f.shape, dtype=complex)
    for s in range(0, b.size, block):
        n = np.arange(s, min(s + block, b.size), dtype=float)
        H += _exp_neg_jpi(f[:, None], n[None, :]) @ b[s:s + block]
    return H


def freq_response(b, f) -> np.ndarray:
    """FIR 係數 b 在正規化頻率 f（Nyquist = 1）的複數響應 H = Σ b[n]·e^(−jπfn)。
    f 等距（linspace／arange，容許 1e-12 的捨入）→ chirp-z；否則分塊 DFT。兩者都向量化、相位先對 2π 取餘數（見模組說明）。"""
    b = np.asarray(b, dtype=float).ravel()
    f = np.asarray(f, dtype=float).ravel()
    if b.size == 0 or f.size == 0:
        return np.zeros(f.shape, dtype=complex)
    if f.size >= 2:
        df = (f[-1] - f[0]) / (f.size - 1)
        if np.max(np.abs(f - (f[0] + df * np.arange(f.size)))) <= 1e-12:
            return _chirpz(b, float(f[0]), float(df), f.size)
    return _block_dft(b, f)


def _spec_met(b: np.ndarray, stopbands, passbands, astop, apass) -> bool:
    """規格檢查：每個阻帶 4096 點 max|H| 要低於 −As dB（嚴格）、每個通帶 1024 點的 max/min 要小於 Ap dB（嚴格）。"""
    with np.errstate(divide="ignore"):
        for (fa, fb), a in zip(stopbands, astop):
            h = np.abs(freq_response(b, np.linspace(fa, fb, SPEC_STOP_POINTS)))
            if -20.0 * np.log10(np.max(h)) <= a:
                return False
        for (fa, fb), a in zip(passbands, apass):
            h = np.abs(freq_response(b, np.linspace(fa, fb, SPEC_PASS_POINTS)))
            if 20.0 * np.log10(np.max(h)) - 20.0 * np.log10(np.min(h)) >= a:
                return False
    return True


def _equalise_transitions(wp: np.ndarray, ws: np.ndarray) -> np.ndarray:
    """帶通／帶阻的 designfilt 先把兩個過渡帶弄成一樣寬：寬度 = |Ws − Wp|，寬的那邊把阻帶邊界往通帶挪到窄的寬度；
    窄的那邊（和兩邊一樣寬時的兩邊）保留原來的阻帶邊界。"""
    side = np.sign(ws - wp)                                         # 阻帶在通帶邊界的哪一側（帶通 [−1, +1]、帶阻 [+1, −1]）
    width = side * (ws - wp)
    edge = ws.copy()
    if width[0] != width[1]:
        wide = 0 if width[0] > width[1] else 1
        edge[wide] = wp[wide] + side[wide] * width[1 - wide]
    return edge


def kaiser_min_fir(kind: str, wp, ws, atten: float) -> Dict[str, Any]:
    """designfilt 'kaiserwin' + 'MinOrder' 'even'：正規化通帶 wp／阻帶 ws（Nyquist = 1）→ dict(b, order, Wn, beta, ftype, redesigns, spec_met)。
    帶通／帶阻先 _equalise_transitions；kaiser_fir_order 定階（奇數 + 1）；fir1；規格沒達標就試 N + 2、N + 4、…，
    最多 MAX_REDESIGN 個設計，第一個達標的採用；都沒達標就回到第一個。量測帶界用縮窄前的規格。"""
    dp, ds = linear_dev(PASSBAND_RIPPLE, "pass"), linear_dev(atten, "stop")
    wp = np.atleast_1d(np.asarray(wp, dtype=float))
    ws = np.atleast_1d(np.asarray(ws, dtype=float))
    ap = [PASSBAND_RIPPLE]
    if kind == "lowpass":
        edges, gains, devs = [wp[0], ws[0]], [1, 0], [dp, ds]
        stop, pas, As = [(ws[0], 1.0)], [(0.0, wp[0])], [atten]
    elif kind == "highpass":
        edges, gains, devs = [ws[0], wp[0]], [0, 1], [ds, dp]
        stop, pas, As = [(0.0, ws[0])], [(wp[0], 1.0)], [atten]
    elif kind == "bandpass":
        e = _equalise_transitions(wp, ws)
        edges, gains, devs = [e[0], wp[0], wp[1], e[1]], [0, 1, 0], [ds, dp, ds]
        stop, pas, As = [(0.0, ws[0]), (ws[1], 1.0)], [(wp[0], wp[1])], [atten, atten]
    elif kind == "bandstop":
        e = _equalise_transitions(wp, ws)
        edges, gains, devs = [wp[0], e[0], e[1], wp[1]], [1, 0, 1], [dp, ds, dp]
        stop, pas, As, ap = [(ws[0], ws[1])], [(0.0, wp[0]), (wp[1], 1.0)], [atten], [PASSBAND_RIPPLE, PASSBAND_RIPPLE]
    else:
        raise _dsv_err("InvalidKind")
    N0, Wn, beta, ftype = kaiser_fir_order(edges, gains, devs, 2.0)
    N0 += N0 % 2                                                    # MinOrder 'even'
    designs: List[Tuple[int, np.ndarray]] = []
    for order in range(N0, N0 + 2 * MAX_REDESIGN, 2):
        b = fir1_kaiser(order, Wn, ftype, beta)
        designs.append((order, b))
        if _spec_met(b, stop, pas, As, ap):
            return {"b": b, "order": order, "Wn": Wn, "beta": beta, "ftype": ftype, "redesigns": len(designs) - 1, "spec_met": True}
    order, b = designs[0]
    return {"b": b, "order": order, "Wn": Wn, "beta": beta, "ftype": ftype, "redesigns": len(designs) - 1, "spec_met": False}


# ---------------------------------------------------------------- 卷積
def _overlap_add(x: np.ndarray, b: np.ndarray, nfft: Optional[int] = None) -> np.ndarray:
    """x（實數或複數）和實數 b 的完整線性卷積，分段 overlap-add FFT：每段長 nfft − N，FFT 長度 nfft（預設 ≥ 2(N+1) 的 2 的冪，
    上限 _OLA_MAX_FFT，但不超過一次做完所需），記憶體和段數成反比、有界。"""
    N = b.size - 1
    L = x.size
    if nfft is None:
        whole = 1 << max(1, (L + N - 1).bit_length())
        nfft = max(1 << (2 * (N + 1) - 1).bit_length(), min(_OLA_MAX_FFT, whole))
    seg = nfft - N
    if seg < 1:
        raise ValueError("_overlap_add: nfft must exceed the filter order")
    cplx = np.iscomplexobj(x)
    out = np.zeros(L + N, dtype=complex if cplx else float)
    B = np.fft.fft(b, nfft) if cplx else np.fft.rfft(b, nfft)
    for s in range(0, L, seg):
        xs = x[s:s + seg]
        if cplx:
            y = np.fft.ifft(np.fft.fft(xs, nfft) * B)
        else:
            y = np.fft.irfft(np.fft.rfft(xs, nfft) * B, nfft)
        out[s:s + xs.size + N] += y[:xs.size + N]
    return out


def apply_fir(x, b) -> np.ndarray:
    """filter(b, 1, [x; zeros(N/2)]) 再丟掉前 N/2 個：長度不變的延遲補償濾波（b 的階數 N 要是偶數）。沿第 0 軸；複數可。
    N·L ≤ 2×10⁷ 用 np.convolve（直接算法），更大用 overlap-add FFT（差 ≤ 1e-15 相對）。"""
    b = np.asarray(b, dtype=float).ravel()
    x = np.asarray(x)
    N = b.size - 1
    if x.ndim == 1:
        if N == 0:
            return x * b[0]
        full = np.convolve(x, b) if N * x.size <= _DIRECT_CONV_MAX_OPS else _overlap_add(x, b)
        return full[N // 2:N // 2 + x.size]
    out = np.empty(x.shape, dtype=np.result_type(x.dtype, float))
    for k in range(x.shape[1]):
        out[:, k] = apply_fir(x[:, k], b)
    return out


# ---------------------------------------------------------------- 參數檢查
def _type_name(v) -> str:
    if isinstance(v, str):
        return "char"
    if isinstance(v, bool) or (isinstance(v, np.ndarray) and v.dtype.kind == "b"):
        return "logical"
    if v is None:
        return "none"
    return type(v).__name__


def _numeric_array(func: str, name: str, v) -> np.ndarray:
    """validateattributes(..., {'numeric'}, {'nonempty','real','finite'}) 共同的前半：非數值 → invalidType、空 → expectedNonempty、
    複數 → expectedReal、NaN／Inf → expectedFinite；回傳 float 陣列（形狀保留）。"""
    try:
        a = np.asarray(v)
    except Exception:  # noqa: BLE001
        raise _attr_err(func, "invalidType", name=name, t=_type_name(v)) from None
    if a.dtype.kind not in "iufc":
        raise _attr_err(func, "invalidType", name=name, t=_type_name(v))
    if a.size == 0:
        raise _attr_err(func, "expectedNonempty", name=name)
    if a.dtype.kind == "c":
        raise _attr_err(func, "expectedReal", name=name)
    a = a.astype(float)
    if not np.all(np.isfinite(a)):
        raise _attr_err(func, "expectedFinite", name=name)
    return a


def _check_attr(func: str, name: str, v, scalar: bool) -> np.ndarray:
    """validateattributes(..., {'numeric'}, {'nonempty','real','finite','scalar'|'vector','positive'})，照 MATLAB 的順序。"""
    a = _numeric_array(func, name, v)
    if scalar:
        if a.size != 1:
            raise _attr_err(func, "expectedScalar", name=name)
    elif a.ndim > 1 and min(a.shape) != 1:
        raise _attr_err(func, "expectedVector", name=name)
    a = a.ravel()
    if not np.all(a > 0):
        raise _attr_err(func, "expectedPositive", name=name)
    return a


def validate(kind: str, wpass, fs: Optional[float], steepness, atten: float, impulse: str = "auto") -> Dict[str, Any]:
    """參數檢查＋換算（照 MATLAB lowpass 等的參數檢查）。回傳 opts：wpass（給定單位）、fs（None 或 Fs）、
    fs_eff（沒給 Fs 就是 2）、normalized、wp_norm、steepness（陣列）、tw（T(s) 陣列）、atten、dp／ds、impulse。"""
    if kind not in KINDS:
        raise _dsv_err("InvalidKind")
    normalized = fs is None
    fs_eff = 2.0
    if not normalized:
        fs_eff = float(_check_attr(kind, "Fs", fs, True)[0])
    name = "Wpass" if normalized else "Fpass"
    wp = _check_attr(kind, name, wpass, kind in ("lowpass", "highpass"))
    if kind in ("bandpass", "bandstop"):
        if wp.size >= 2 and not np.all(np.diff(wp) > 0):
            raise _attr_err(kind, "expectedIncreasing", name=name)
        if wp.size != 2:
            raise _attr_err(kind, "incorrectNumel", name=name, n=2)
    if normalized and np.any(wp >= 1):
        raise _err("InvalidNormalizedWpassValue")
    wp_norm = wp / (fs_eff / 2.0)
    at = _numeric_array(kind, "StopbandAttenuation", atten).ravel()
    if at.size != 1:
        raise _attr_err(kind, "expectedScalar", name="StopbandAttenuation")
    if float(at[0]) < MIN_ATTEN:
        raise _attr_err(kind, "notGreaterEqual", name="StopbandAttenuation", v=_g(MIN_ATTEN))
    atten = float(at[0])
    ds = linear_dev(atten, "stop")
    if ds == 0.0:
        raise _dsv_err("StopbandAttenuationTooLarge", v=_g(atten))
    if steepness is None:
        steepness = DEFAULT_STEEPNESS if kind in ("lowpass", "highpass") else (DEFAULT_STEEPNESS, DEFAULT_STEEPNESS)
    st = _numeric_array(kind, "Steepness", steepness).ravel()
    if kind in ("lowpass", "highpass"):
        if st.size != 1:
            raise _attr_err(kind, "expectedScalar", name="Steepness")
        if st[0] < STEEPNESS_MIN:
            raise _attr_err(kind, "notGreaterEqual", name="Steepness", v=_g(STEEPNESS_MIN))
        if st[0] >= 1:
            raise _attr_err(kind, "notLess", name="Steepness", v="1")
    elif st.size > 2 or np.any(st < STEEPNESS_MIN) or np.any(st > 1):
        raise _err("InvalidSteepness")
    if impulse not in IMPULSE:
        raise _dsv_err("InvalidImpulseResponse")
    return {"kind": kind, "wpass": wp, "fs": None if normalized else fs_eff, "fs_eff": fs_eff, "normalized": normalized,
            "wp_norm": wp_norm, "steepness": st, "tw": -0.98 * st + 0.99, "atten": atten,
            "dp": linear_dev(PASSBAND_RIPPLE, "pass"), "ds": ds, "impulse": impulse}


def _as_signal(x) -> Tuple[np.ndarray, int, str]:
    """輸入 → (array, 訊號長度 L, 形狀 'vec'／'row'／'cols')；非浮點 → InvalidInputDataType，NaN／Inf 或 >2 維 → InvalidVectorOrMatrixType。"""
    try:
        a = np.asarray(x)
    except Exception:  # noqa: BLE001
        raise _err("InvalidInputDataType") from None
    if a.dtype.kind not in "fc":
        raise _err("InvalidInputDataType")
    if a.ndim > 2 or not np.all(np.isfinite(a)):
        raise _err("InvalidVectorOrMatrixType")
    if a.ndim == 2 and a.shape[0] == 1:
        return a, a.shape[1], "row"
    if a.ndim == 2:
        return a, a.shape[0], "cols"
    return a.ravel(), a.size, "vec"


# ---------------------------------------------------------------- 設計
def stopband_edges(kind: str, wp_norm, tw) -> np.ndarray:
    """正規化通帶 → 正規化阻帶邊界（模組說明的公式；帶通／帶阻純量陡度時兩邊都用 min(Tw1, Tw2)）。"""
    wp = np.atleast_1d(np.asarray(wp_norm, dtype=float))
    tw = np.atleast_1d(np.asarray(tw, dtype=float))
    if kind == "lowpass":
        return np.array([wp[0] + tw[0] * (1.0 - wp[0])])
    if kind == "highpass":
        return np.array([wp[0] - tw[0] * wp[0]])
    if kind == "bandpass":
        tw1, tw2 = tw[0] * wp[0], tw[-1] * (1.0 - wp[1])
        if tw.size == 1:
            tw1 = tw2 = min(tw1, tw2)
        return np.array([wp[0] - tw1, wp[1] + tw2])
    c = wp[0] / 2.0 + wp[1] / 2.0
    tw1, tw2 = tw[0] * (c - wp[0]), tw[-1] * (wp[1] - c)
    if tw.size == 1:
        tw1 = tw2 = min(tw1, tw2)
    return np.array([wp[0] + tw1, wp[1] - tw2])


def required_fir_order(kind: str, wpass, wstop, fs_eff: float, atten: float) -> int:
    """所需 FIR 階數 N_req：用帶界（給定單位）和 Fs 照 kaiserord 估計的階數（FIR／IIR 切換用的量）。"""
    dp, ds = linear_dev(PASSBAND_RIPPLE, "pass"), linear_dev(atten, "stop")
    wp = np.atleast_1d(np.asarray(wpass, dtype=float))
    ws = np.atleast_1d(np.asarray(wstop, dtype=float))
    if kind == "lowpass":
        F, G, D = [wp[0], ws[0]], [1, 0], [dp, ds]
    elif kind == "highpass":
        F, G, D = [ws[0], wp[0]], [0, 1], [ds, dp]
    elif kind == "bandpass":
        F, G, D = [ws[0], wp[0], wp[1], ws[1]], [0, 1, 0], [ds, dp, ds]
    else:
        F, G, D = [wp[0], ws[0], ws[1], wp[1]], [1, 0, 1], [dp, ds, dp]
    return kaiser_fir_order(F, G, D, fs_eff)[0]


def _info(opts: Dict[str, Any], response: str, b: np.ndarray, ws_norm, nreq: Optional[int]) -> Dict[str, Any]:
    fs = opts["fs_eff"]
    return {"kind": opts["kind"], "response": response, "is_fir": True, "order": int(b.size - 1), "b": b, "coefficients": b,
            "wpass": opts["wpass"], "wstop": None if ws_norm is None else ws_norm * (fs / 2.0), "fs": opts["fs"],
            "wpass_norm": opts["wp_norm"], "wstop_norm": ws_norm, "steepness": opts["steepness"], "atten": opts["atten"],
            "impulse": opts["impulse"], "required_order": nreq, "min_length": None if nreq is None else 2 * nreq + 1,
            "warnings": [], "warning_text": [], "spec": {}}


def _warn(info: Dict[str, Any], keyword: str, kind: str) -> None:
    info["warnings"].append(keyword)
    info["warning_text"].append((warning_text(keyword, False, kind), warning_text(keyword, True, kind)))


def _trivial(opts: Dict[str, Any], response: str, warn: str) -> Dict[str, Any]:
    """全通（[1]）或全阻（[0]）：MATLAB 的 digitalFilter 沒有設計規格，回報 SampleRate 2、ImpulseResponse 'ect'。"""
    info = _info(opts, response, np.array([1.0 if response == "allpass" else 0.0]), None, None)
    _warn(info, warn, opts["kind"])
    info["spec"] = {"FrequencyResponse": response, "SampleRate": 2.0, "ImpulseResponse": "ect"}
    return info


def _spec(opts: Dict[str, Any], kind: str, wstop) -> Dict[str, Any]:
    """照 digitalFilter 的屬性列出 FIR 設計的規格（給定單位）。"""
    wp, at = opts["wpass"], opts["atten"]
    sp: Dict[str, Any] = {"FrequencyResponse": kind, "DesignMethod": "kaiserwin", "ImpulseResponse": "fir", "SampleRate": opts["fs_eff"]}
    if kind in ("lowpass", "highpass"):
        sp.update(PassbandFrequency=float(wp[0]), StopbandFrequency=float(wstop[0]), PassbandRipple=PASSBAND_RIPPLE, StopbandAttenuation=at)
    elif kind == "bandpass":
        sp.update(PassbandFrequency1=float(wp[0]), PassbandFrequency2=float(wp[1]), StopbandFrequency1=float(wstop[0]),
                  StopbandFrequency2=float(wstop[1]), PassbandRipple=PASSBAND_RIPPLE, StopbandAttenuation1=at, StopbandAttenuation2=at)
    else:
        sp.update(PassbandFrequency1=float(wp[0]), PassbandFrequency2=float(wp[1]), StopbandFrequency1=float(wstop[0]),
                  StopbandFrequency2=float(wstop[1]), PassbandRipple1=PASSBAND_RIPPLE, PassbandRipple2=PASSBAND_RIPPLE, StopbandAttenuation=at)
    return sp


def _design_core(opts: Dict[str, Any], L: Optional[int]) -> Dict[str, Any]:
    kind, wp, fs = opts["kind"], opts["wp_norm"], opts["fs_eff"]
    short = L is not None and L <= ALLPASS_MIN_LENGTH[kind]
    if kind == "lowpass":
        if short or wp[0] >= 1:
            return _trivial(opts, "allpass", "AllPassBecauseSignalIsTooShort" if short else "ForcedAllpassDesign")
    elif kind == "highpass":
        if wp[0] >= 1:
            return _trivial(opts, "allstop", "ForcedAllstopDesign")
        if short:
            return _trivial(opts, "allpass", "AllPassBecauseSignalIsTooShort")
    elif short:
        return _trivial(opts, "allpass", "AllPassBecauseSignalIsTooShort")
    ws = stopband_edges(kind, wp, opts["tw"])
    wstop = ws * (fs / 2.0)
    nreq = required_fir_order(kind, opts["wpass"], wstop, fs, opts["atten"])
    imp = opts["impulse"]
    if imp == "iir":
        raise _dsv_err("IIRNotImplemented")
    if L is not None and L <= 2 * nreq:                               # MATLAB：'fir' → 錯誤；'auto' → 改走 IIR。DSV 只做 FIR → 拒絕
        if imp == "fir":
            raise _err("SignalLengthForFIR", n=nreq)
        raise _dsv_err("SignalTooShortForFIR", L=L, n=nreq, need=2 * nreq + 1)
    if nreq > MAX_FIR_ORDER:
        raise _dsv_err("FilterOrderTooLarge", n=nreq, max=MAX_FIR_ORDER)
    d = kaiser_min_fir(kind, opts["wpass"] / (fs / 2.0), wstop / (fs / 2.0), opts["atten"])
    info = _info(opts, kind, d["b"], ws, nreq)
    info.update(Wn=d["Wn"], beta=d["beta"], redesigns=d["redesigns"], spec_met=d["spec_met"])
    info["spec"] = _spec(opts, kind, wstop)
    return info


def design(kind: str, wpass, fs: Optional[float] = None, length: Optional[int] = None, steepness=None, atten: float = DEFAULT_ATTEN,
           impulse: str = "auto") -> Dict[str, Any]:
    """設計（不濾波）。length＝訊號長度 L（決定全通特例與「太短」的拒絕；None 當無限長 → 一律 FIR，階數超過 MAX_FIR_ORDER 丟錯）。
    回傳 info dict：response（lowpass／highpass／bandpass／bandstop／allpass／allstop）、is_fir（永遠 True）、order、b／coefficients（FIR 係數，
    ＝MATLAB digitalFilter.Coefficients）、wstop（給定單位）、wpass_norm／wstop_norm、required_order（所需 FIR 階數 N_req）、min_length（2·N_req + 1）、
    Wn／beta／redesigns／spec_met、warnings（關鍵字清單，最後一個是 MATLAB lastwarn 會給的）、warning_text（對應的 (英文, 繁體中文)）、
    spec（照 digitalFilter 的屬性）。"""
    opts = validate(kind, wpass, fs, steepness, atten, impulse)
    L = None if length is None else int(length)
    if kind in ("bandpass", "bandstop") and opts["wp_norm"][1] >= 1:
        # MATLAB：結果等同帶通 → highpass(Wp1, Steepness(1))、帶阻 → lowpass(Wp1, Steepness(1))；ImpulseResponse 用 'auto'
        sub = "highpass" if kind == "bandpass" else "lowpass"
        warn = "ForcedHighpassDesign" if kind == "bandpass" else "ForcedLowpassDesign"
        info = design(sub, float(opts["wpass"][0]), fs, L, float(opts["steepness"][0]), atten, "auto")
        if opts["wp_norm"][0] < 1:
            text = (warning_text(warn, False, kind), warning_text(warn, True, kind))
            if kind == "bandpass":                                 # 帶通的 ForcedHighpassDesign 排在 highpass 本身的警告前面；帶阻的排在後面
                info["warnings"], info["warning_text"] = [warn] + info["warnings"], [text] + info["warning_text"]
            else:
                info["warnings"].append(warn)
                info["warning_text"].append(text)
        info["kind"] = kind
        return info
    return _design_core(opts, L)


def filter_signal(kind: str, x, wpass, fs: Optional[float] = None, steepness=None, atten: float = DEFAULT_ATTEN,
                  impulse: str = "auto") -> Tuple[np.ndarray, Dict[str, Any]]:
    """MATLAB lowpass／highpass／bandpass／bandstop(x, Wpass[, Fs], 'Steepness', s, 'StopbandAttenuation', A[, 'ImpulseResponse', r])。
    x 實數或複數（1 維；(1, n) 當列向量；2 維照欄）。回傳 (y, info)，y 和 x 同長度。訊號太短（L ≤ 2·N_req）→ FilterError（見模組說明）。"""
    a, L, shape = _as_signal(x)                       # MATLAB 先檢查資料（型別、有限），再檢查參數
    opts = validate(kind, wpass, fs, steepness, atten, impulse)
    info = design(kind, opts["wpass"], fs, L, opts["steepness"], atten, impulse)
    data = a[0] if shape == "row" else a
    y = apply_fir(data, info["b"])
    if shape == "row":
        y = y[None, :]
    info["length"] = L
    return y, info


def lowpass(x, wpass, fs: Optional[float] = None, steepness: float = DEFAULT_STEEPNESS, atten: float = DEFAULT_ATTEN,
            impulse: str = "auto") -> Tuple[np.ndarray, Dict[str, Any]]:
    """MATLAB lowpass：通帶 wpass（沒給 fs 時是 ×π rad/sample、要 < 1；給 fs 時是 Hz）。回傳 (y, info)。"""
    return filter_signal("lowpass", x, wpass, fs, steepness, atten, impulse)


def highpass(x, wpass, fs: Optional[float] = None, steepness: float = DEFAULT_STEEPNESS, atten: float = DEFAULT_ATTEN,
             impulse: str = "auto") -> Tuple[np.ndarray, Dict[str, Any]]:
    """MATLAB highpass。"""
    return filter_signal("highpass", x, wpass, fs, steepness, atten, impulse)


def bandpass(x, wpass, fs: Optional[float] = None, steepness=None, atten: float = DEFAULT_ATTEN,
             impulse: str = "auto") -> Tuple[np.ndarray, Dict[str, Any]]:
    """MATLAB bandpass：wpass＝[低, 高]；steepness 純量（Signal Analyzer 單一模式）或 [s1, s2]（雙模式）；None＝函式預設 [0.85 0.85]。"""
    return filter_signal("bandpass", x, wpass, fs, steepness, atten, impulse)


def bandstop(x, wpass, fs: Optional[float] = None, steepness=None, atten: float = DEFAULT_ATTEN,
             impulse: str = "auto") -> Tuple[np.ndarray, Dict[str, Any]]:
    """MATLAB bandstop（參數同 bandpass）。"""
    return filter_signal("bandstop", x, wpass, fs, steepness, atten, impulse)


def app_call(kind: str, p: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Signal Analyzer 的 Function Parameters 面板欄位（DSV 用的鍵：timeMode 'samples'／'uniform'、passbandFrequencyNormalized[1/2]、
    passbandFrequency[1/2]（已是 Hz，頻率單位只影響顯示）、steepness 或 steepnessMode 'single'／'dual' + steepness1／steepness2、
    stopbandAttenuation）→ (filter_signal 的參數 dict, Signal Analyzer 產生的 MATLAB 程式碼裡的呼叫字串)。單一模式傳純量 s1。"""
    uniform = p.get("timeMode") == "uniform"
    at = float(p.get("stopbandAttenuation", DEFAULT_ATTEN))
    if kind in ("lowpass", "highpass"):
        w = float(p["passbandFrequency"] if uniform else p["passbandFrequencyNormalized"])
        st = float(p.get("steepness", DEFAULT_STEEPNESS))
        wtxt, stxt = _g(w), _g(st)
    else:
        w = [float(p["passbandFrequency1"] if uniform else p["passbandFrequencyNormalized1"]),
             float(p["passbandFrequency2"] if uniform else p["passbandFrequencyNormalized2"])]
        s1 = float(p.get("steepness1", DEFAULT_STEEPNESS))
        s2 = float(p.get("steepness2", DEFAULT_STEEPNESS))
        dual = p.get("steepnessMode", "single") == "dual"
        st = [s1, s2] if dual else s1
        wtxt = "[%s %s]" % (_g(w[0]), _g(w[1]))
        stxt = ("[%s %s]" % (_g(s1), _g(s2))) if dual else _g(s1)
    args = {"kind": kind, "wpass": w, "fs": "Fs" if uniform else None, "steepness": st, "atten": at}
    call = "%s(x,%s%s,'Steepness',%s,'StopbandAttenuation',%s)" % (kind, wtxt, ",Fs" if uniform else "", stxt, _g(at))
    return args, call


# ---------------------------------------------------------------- selftest
def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/filters；研究用 make_filters_ref.m／run_app_equiv.m 產生）。"""
    import gzip
    import json
    import os
    import re
    import time as _time
    d = os.path.join(ref_dir, "filters")
    if not os.path.isdir(d):
        check(True, "（沒有 tests/matlab_ref/filters：略過 MATLAB 濾波比對）")
        return

    def load(name):
        p = os.path.join(d, name)
        if os.path.exists(p + ".gz"):
            with gzip.open(p + ".gz", "rt", encoding="utf-8") as fh:
                return json.load(fh)
        return json.load(open(p, encoding="utf-8"))

    sigs: Dict[str, np.ndarray] = {}

    def sig(name):
        if name not in sigs:
            v = np.loadtxt(os.path.join(d, "signals", name + ".txt"))
            sigs[name] = (v[:, 0] + 1j * v[:, 1]) if (v.ndim == 2 and v.shape[1] == 2) else v.ravel()
        return sigs[name]

    def arr(v):
        return np.asarray(v, dtype=float)

    def close(a, b, rtol=1e-9, atol_rel=1e-13):
        """逐值 rtol 1e-9；atol 只給「參考值最大值 × 1e-13」當零值（零交越樣本、係數尾端、阻帶輸出）的底
        （實測：係數 4.4e-15、輸出 8.3e-15 × max|y|、|H|@256 9.2e-15）。NaN／Inf 一律不過。"""
        a, b = np.asarray(a), np.asarray(b)
        if a.shape != b.shape or not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
            return False
        scale = float(np.max(np.abs(b))) if b.size else 1.0
        return bool(np.allclose(a, b, rtol=rtol, atol=atol_rel * max(scale, 1e-300)))

    def worst(a, b):
        a, b = np.asarray(a, dtype=complex).ravel(), np.asarray(b, dtype=complex).ravel()
        e = np.abs(a - b)
        k = int(np.argmax(e)) if e.size else 0
        return (float(e[k]) if e.size else 0.0), k

    def refy(c):
        y = arr(c["y_re"])
        return y + 1j * arr(c["y_im"]) if c.get("y_im") else y

    def case_args(c):
        """case 的 call → (kind, x, wpass, fs, kwargs)。"""
        nv = c.get("nv") or {}
        kw = dict(steepness=nv.get("Steepness"), atten=float(nv.get("StopbandAttenuation", DEFAULT_ATTEN)),
                  impulse=str(nv.get("ImpulseResponse", "auto")))
        if kw["steepness"] is None and c["func"] in ("lowpass", "highpass"):
            kw["steepness"] = DEFAULT_STEEPNESS
        fs = None if c["fs"] in (None, [], "") else float(c["fs"])
        x = sig(c["signal"])
        if c["signal"].startswith("row"):
            x = x[None, :]
        return c["func"], x, c["wpass"], fs, kw

    def run(c):
        """照 case 的 call 跑：回傳 (y, info) 或 FilterError。"""
        kind, x, wp, fs, kw = case_args(c)
        try:
            return filter_signal(kind, x, wp, fs, **kw)
        except FilterError as e:
            return e

    def spec_mismatch(mine: Dict[str, Any], ref: Dict[str, Any], keys) -> List[str]:
        out = []
        for key in keys:
            val, got = ref[key], mine.get(key)
            if isinstance(val, str):
                ok = got == val
            else:
                ok = got is not None and not isinstance(got, str) and math.isclose(float(got), float(val), rel_tol=1e-9, abs_tol=0.0)
            if not ok:
                out.append(f"spec.{key} {got!r} vs MATLAB {val!r}")
        return out

    grid = np.arange(256) / 256.0
    n_cases = 0
    errs = {"coef": 0.0, "y": 0.0, "H": 0.0}
    refused: Dict[str, Tuple[str, int]] = {}          # MATLAB 走 IIR、DSV 拒絕的案例 → (DSV 識別字, MATLAB 的 IIR 階數)
    matlab_errors: Dict[str, Tuple[str, str]] = {}    # MATLAB 自己丟錯的案例 → (MATLAB 識別字, DSV 識別字)
    n_spec_iir = 0
    method_specific = {"DesignMethod", "ImpulseResponse", "FilterOrder"}
    for fn, label in (("lowpass", "低通"), ("highpass", "高通"), ("bandpass", "帶通"), ("bandstop", "帶阻")):
        R = load(f"ref_{fn}.json")
        bad: List[str] = []
        n_fir = n_trivial = n_iir = n_forced = n_warn = 0
        for c in R["cases"]:
            n_cases += 1
            r = run(c)
            cid = c["id"]
            kind, x, wp, fs, kw = case_args(c)
            L = np.asarray(x).shape[-1] if np.asarray(x).ndim == 2 and np.asarray(x).shape[0] == 1 else np.asarray(x).shape[0]
            if not c["ok"]:                                   # MATLAB 自己也丟錯誤（highpass_045：IIR 路徑的 filtfilt 資料太短）
                if not isinstance(r, FilterError):
                    bad.append(f"{cid}: MATLAB 錯誤 {c['error_id']} 但 DSV 沒丟錯誤")
                else:
                    matlab_errors[cid] = (c["error_id"], r.identifier)
                continue
            if not c["is_fir"]:                               # MATLAB 走 IIR：DSV 一定拒絕；比對切換判斷、訊息數字、與設計法無關的規格欄位
                if not isinstance(r, FilterError):
                    bad.append(f"{cid}: MATLAB 走 IIR（階數 {c['order']}）但 DSV 沒拒絕（FIR 階數 {r[1]['order']}）")
                    continue
                refused[cid] = (r.identifier, int(c["order"]))
                if kw["impulse"] == "iir":
                    n_forced += 1
                    if r.identifier != "dsv:filter:IIRNotImplemented":
                        bad.append(f"{cid}: 強制 'iir' 應丟 IIRNotImplemented，得到 {r.identifier}")
                else:
                    n_iir += 1
                    if r.identifier != "dsv:filter:SignalTooShortForFIR":
                        bad.append(f"{cid}: 應丟 SignalTooShortForFIR，得到 {r.identifier}")
                    elif not (r.length == L and r.min_length == 2 * r.required_order + 1 and L <= 2 * r.required_order
                              and str(L) in r.message and str(r.min_length) in r.message and str(r.min_length) in r.message_zh):
                        bad.append(f"{cid}: 太短訊息的數字不對（L={L}, required={r.required_order}, min={r.min_length}）")
                try:
                    preview = design(kind, wp, fs, None, kw["steepness"], kw["atten"], "auto")
                    if kind in ("bandpass", "bandstop") and c["spec"]["FrequencyResponse"] in ("lowpass", "highpass"):
                        preview = None                        # 轉成高通／低通的案例不在 IIR 集合裡，保險起見
                except FilterError as e:
                    preview = None
                    bad.append(f"{cid}: design(length=None) 丟 {e.identifier}")
                if preview is not None:
                    keys = sorted((set(c["spec"]) & set(preview["spec"])) - method_specific)
                    n_spec_iir += len(keys)
                    bad += [f"{cid}: {m}" for m in spec_mismatch(preview["spec"], c["spec"], keys)]
                    if c["spec"].get("StopbandFrequency") is not None or c["spec"].get("StopbandFrequency1") is not None:
                        if not any(k.startswith("StopbandFrequency") for k in keys):
                            bad.append(f"{cid}: 沒比到 StopbandFrequency")
                continue
            if isinstance(r, FilterError):
                bad.append(f"{cid}: DSV 丟 {r.identifier}（MATLAB 正常，FIR order {c['order']}）")
                continue
            y, info = r
            sp = c.get("spec") or {}
            if info["order"] != c["order"]:
                bad.append(f"{cid}: order {info['order']} vs MATLAB {c['order']}")
                continue
            if c["order"] == 0:
                n_trivial += 1
            else:
                n_fir += 1
            b_ref = np.atleast_1d(arr(c["coefficients"])).ravel()
            if b_ref.size != info["b"].size:
                bad.append(f"{cid}: 係數個數 {info['b'].size} vs {b_ref.size}")
                continue
            e, k = worst(info["b"], b_ref)
            errs["coef"] = max(errs["coef"], e)
            if not close(info["b"], b_ref):
                bad.append(f"{cid}: 係數不一致 max|Δ|={e:.3g} @ {k}")
            y_ref = refy(c)
            yy = np.asarray(y).ravel()
            e, k = worst(yy, y_ref)
            y_scale = max(float(np.max(np.abs(y_ref))), 1e-300)
            errs["y"] = max(errs["y"], e / y_scale)
            if yy.size != y_ref.size or not close(yy, y_ref):
                bad.append(f"{cid}: 輸出不一致 max|Δ|={e:.3g} @ {k}（相對輸出最大值 {e / y_scale:.2g}）")
            if list(np.asarray(y).shape) != c["y_size"] and not (np.asarray(y).ndim == 1 and c["y_size"][1] == 1):
                bad.append(f"{cid}: 形狀 {np.asarray(y).shape} vs {c['y_size']}")
            if np.iscomplexobj(y) != bool(c.get("y_im")):
                bad.append(f"{cid}: 複數性不一致")
            H = np.abs(freq_response(info["b"], grid))
            H_ref = arr(c["freqz_absH"])
            e, k = worst(H, H_ref)
            errs["H"] = max(errs["H"], e)
            if not close(H, H_ref):
                bad.append(f"{cid}: |H| 不一致 max|Δ|={e:.3g} @ {k}")
            # 警告：識別字＋英文訊息（lastwarn）＋中文要有
            wid, wmsg = c.get("warn_id") or "", c.get("warn_msg") or ""
            if info["warnings"]:
                last, (last_en, last_zh) = WARNING_PREFIX + info["warnings"][-1], info["warning_text"][-1]
            else:
                last, last_en, last_zh = "", "", ""
            if wid != last or wmsg != last_en:
                bad.append(f"{cid}: 警告 {last!r} {last_en!r} vs MATLAB {wid!r} {wmsg!r}")
            elif wid:
                n_warn += 1
                if not last_zh:
                    bad.append(f"{cid}: 警告沒有中文")
            # 規格：MATLAB digitalFilter 的每個屬性都要有、都要一樣，也不能多
            if info["spec"].get("ImpulseResponse") != c["impulse_response"]:
                bad.append(f"{cid}: ImpulseResponse {info['spec'].get('ImpulseResponse')!r} vs {c['impulse_response']!r}")
            bad += [f"{cid}: {m}" for m in spec_mismatch(info["spec"], sp, sorted(sp))]
            extra = set(info["spec"]) - set(sp)
            if extra:
                bad.append(f"{cid}: spec 多了 {sorted(extra)}")
        n_err = sum(1 for c in R["cases"] if not c["ok"])
        check(not bad, f"{label} vs MATLAB {fn}（{len(R['cases'])} 案例：{n_fir} 個 FIR＋{n_trivial} 個全通／全阻逐值一致（rtol 1e-9、零值底 1e-13×max）"
                       f"——係數、輸出、形狀、複數性、|H|@256、警告識別字＋訊息＋中文、ImpulseResponse、每個規格屬性，{n_warn} 個警告；"
                       f"MATLAB 走 IIR 的 {n_iir} 個 auto 案例 DSV 丟 SignalTooShortForFIR（L、所需階數、最少樣本數都對）、{n_forced} 個強制 'iir' 丟 "
                       f"IIRNotImplemented，與設計法無關的規格欄位一致；{n_err} 個 MATLAB 錯誤案例 DSV 也丟錯）" + (f"（不一致：{bad}）" if bad else ""))
    check(errs["coef"] < 1e-13 and errs["y"] < 1e-12 and errs["H"] < 1e-12,
          f"FIR 數值誤差上限：係數 {errs['coef']:.2g}、輸出 {errs['y']:.2g}（相對最大值）、|H|@256（chirp-z）{errs['H']:.2g}（都遠小於 rtol 1e-9）")
    # 已知差異：釘住 64 個 IIR 案例的拒絕方式與 MATLAB 的 IIR 階數、highpass_045 的識別字差
    E = load("ref_iir_vs_ellip.json")
    e_orders = {c["id"]: int(c["order"]) for c in E["cases"]}
    forced_ids = {"lowpass_029", "highpass_060", "bandpass_094", "bandpass_095", "bandstop_127", "bandstop_128"}
    want_refused = {cid: ("dsv:filter:IIRNotImplemented" if cid in forced_ids else "dsv:filter:SignalTooShortForFIR", o) for cid, o in e_orders.items()}
    kd_ok = (refused == want_refused and len(refused) == 64 and sum(1 for v in refused.values() if v[0].endswith("IIRNotImplemented")) == 6
             and matlab_errors == {"highpass_045": ("signal:filtfilt:InvalidDimensionsDataShortForFiltOrder", "dsv:filter:SignalTooShortForFIR")})
    check(kd_ok, f"已知差異（使用者決定只做 FIR）：MATLAB 走 IIR 的 {len(refused)} 個案例（＝ref_iir_vs_ellip.json 的 {len(e_orders)} 個，MATLAB 自己量到 "
                 f"|H| 和 ellip() 差 ≤ {max(c['max_abs_diff_H'] for c in E['cases']):.2g}；階數 {min(e_orders.values())}～{max(e_orders.values())}）"
                 f"DSV 全部拒絕——58 個 auto 丟 SignalTooShortForFIR、6 個強制 'iir' 丟 IIRNotImplemented，MATLAB 的 IIR 輸出沒有被比對；"
                 f"{n_spec_iir} 個與設計法無關的規格欄位（Passband／StopbandFrequency、SampleRate、StopbandAttenuation、PassbandRipple）一致；"
                 f"highpass_045（L=4）MATLAB 丟 signal:filtfilt:InvalidDimensionsDataShortForFiltOrder、DSV 丟 dsv:filter:SignalTooShortForFIR"
                 + ("" if kd_ok else f"（實際：refused={refused}，errors={matlab_errors}）"))
    # FIR／IIR 切換門檻：每個 auto 非全通案例的 L ≤ 2·N_req 要和 MATLAB 的 is_fir 相反
    thr_ok = []
    for fn in KINDS:
        for c in load(f"ref_{fn}.json")["cases"]:
            if not c["ok"] or c["order"] == 0:
                continue
            nv = c.get("nv") or {}
            if nv.get("ImpulseResponse") in ("fir", "iir"):
                continue
            fs = None if c["fs"] in (None, [], "") else float(c["fs"])
            st = nv.get("Steepness", DEFAULT_STEEPNESS if fn in ("lowpass", "highpass") else None)
            kind, wp = fn, c["wpass"]
            if fn in ("bandpass", "bandstop") and c["spec"]["FrequencyResponse"] in ("lowpass", "highpass"):
                kind, wp, st = c["spec"]["FrequencyResponse"], c["wpass"][0], (st if np.ndim(st) == 0 else st[0])
            o = validate(kind, wp, fs, st, float(nv.get("StopbandAttenuation", DEFAULT_ATTEN)))
            ws = stopband_edges(kind, o["wp_norm"], o["tw"]) * (o["fs_eff"] / 2.0)
            nreq = required_fir_order(kind, o["wpass"], ws, o["fs_eff"], o["atten"])
            thr_ok.append((len(sig(c["signal"])) <= 2 * nreq) == (not c["is_fir"]))
    check(all(thr_ok) and len(thr_ok) == 109,
          f"FIR／IIR 切換門檻 L ≤ 2·N_req 對 {len(thr_ok)} 個 auto 非全通案例（全部 {n_cases} 個）都和 MATLAB 的選擇一致")
    # 錯誤案例（make_filters_ref.m 的 20 組；順序一樣）
    xr = sig("long_real")
    cases = [("lowpass", xr, (1,), {}), ("lowpass", xr, (1.2,), {}), ("lowpass", xr, (0,), {}), ("lowpass", xr, (-0.1,), {}),
             ("lowpass", xr, (100, 0), {}), ("lowpass", xr, (0.3,), {"steepness": 1}), ("lowpass", xr, (0.3,), {"steepness": 0.4}),
             ("lowpass", xr, (0.3,), {"atten": 5}), ("lowpass", xr, (0.3,), {"impulse": "fir"}), ("lowpass", xr[:20], (0.3,), {"impulse": "fir"}),
             ("bandpass", xr, ([0.5, 0.2],), {}), ("bandpass", xr, ([0.2, 1],), {}), ("bandpass", xr, (0.2,), {}),
             ("bandpass", xr, ([0.2, 0.5],), {"steepness": [0.5, 0.6, 0.7]}), ("bandpass", xr, ([0.2, 0.5],), {"steepness": 1.1}),
             ("bandpass", xr, ([0.2, 0.5],), {"steepness": 0.4}), ("bandstop", xr, ([0.2, 0.5],), {"atten": 9.99}),
             ("lowpass", np.where(np.arange(xr.size) == 10, np.nan, xr), (0.3,), {}),
             ("highpass", np.where(np.arange(xr.size) == 10, np.inf, xr), (0.3,), {}),
             ("lowpass", np.round(100 * xr).astype(np.int16), (0.3,), {})]
    ER = load("ref_errors.json")["cases"]
    bad = []
    for (kind, x, args, kw), c in zip(cases, ER):
        try:
            filter_signal(kind, x, args[0], args[1] if len(args) > 1 else None, **kw)
            got, msg = "", ""
        except FilterError as e:
            got, msg = e.identifier, e.message
        if got != (c["error_id"] or "") or (got and msg != c["error_msg"]):
            bad.append(f"{c['call']}: {got!r} {msg!r} vs {c['error_id']!r} {c['error_msg']!r}")
    check(len(cases) == len(ER) == 20 and not bad,
          f"錯誤案例 vs MATLAB（{len(ER)} 組：Wpass 範圍／正數／遞增／個數、Fs、Steepness、StopbandAttenuation、SignalLengthForFIR(RequiredOrder=66)、"
          f"NaN／Inf、int16）識別字與英文訊息一致" + (f"（不一致：{bad}）" if bad else ""))
    # Signal Analyzer 的參數對應（app_equiv.json：程式碼產生器輸出 12 組；Signal Analyzer 實測 18 組的呼叫、警告／對話框訊息代碼、形狀）
    A = load("app_equiv.json")
    bad = []
    for g in A["generated_code"]:
        kind = g["filter"].replace("filter", "")
        _, call = app_call(kind, g["ui_parameters"])
        want = g["code"].strip().removeprefix("y = ").rstrip(";")
        if call != want:
            bad.append(f"{call} vs {want}")
    rng = np.random.default_rng(7)
    n = 300
    t = np.arange(n) / 1000.0
    xr3 = np.sin(2 * np.pi * 50 * t) + 0.5 * np.sin(2 * np.pi * 300 * t) + 0.1 * rng.standard_normal(n)
    xc3 = xr3 + 1j * (np.cos(2 * np.pi * 120 * t) + 0.1 * rng.standard_normal(n))

    def P(tm, wn, f, st, at):
        return {"timeMode": tm, "passbandFrequencyNormalized": wn, "passbandFrequency": f, "passbandFrequencyUnits": "Hz", "steepness": st, "stopbandAttenuation": at}

    def PB(tm, wn, f, sm, s1, s2, at):
        return {"timeMode": tm, "passbandFrequencyNormalized1": wn[0], "passbandFrequencyNormalized2": wn[1], "passbandFrequency1": f[0],
                "passbandFrequency2": f[1], "passbandFrequencyUnits": "Hz", "steepnessMode": sm, "steepness1": s1, "steepness2": s2, "stopbandAttenuation": at}
    app = [("lowpass", P("samples", 0.3, "", 0.85, 60), xr3), ("lowpass", P("uniform", 0.5, 150, 0.9, 40), xr3), ("lowpass", P("uniform", 0.5, 150, 0.85, 60), xc3),
           ("highpass", P("uniform", 0.5, 200, 0.75, 70), xr3), ("highpass", P("uniform", 0.5, 200, 0.85, 60), xr3),
           ("lowpass", P("uniform", 0.5, 600, 0.85, 60), xr3), ("highpass", P("uniform", 0.5, 600, 0.85, 60), xr3),
           ("lowpass", P("samples", 0.3, "", 0.85, 60), xr3[:3]), ("lowpass", P("samples", 0.3, "", 0.85, 60), xr3[:40]),
           ("lowpass", P("samples", 0.3, "", 0.85, 60), xr3[None, :]),
           ("bandpass", PB("uniform", [.25, .75], [40, 120], "single", 0.85, 0.6, 60), xr3), ("bandpass", PB("uniform", [.25, .75], [40, 120], "single", 0.7, 0.95, 60), xr3),
           ("bandpass", PB("uniform", [.25, .75], [40, 120], "dual", 0.7, 0.95, 50), xr3), ("bandstop", PB("samples", [.2, .6], [0, 0], "dual", 0.6, 0.8, 60), xc3),
           ("bandstop", PB("uniform", [.25, .75], [40, 120], "single", 0.7, 0.95, 60), xr3),
           ("bandpass", PB("uniform", [.25, .75], [100, 700], "single", 0.85, 0.85, 60), xr3), ("bandstop", PB("uniform", [.25, .75], [600, 700], "single", 0.85, 0.85, 60), xr3),
           ("lowpass", P("samples", 0.3, "", 0.85, 60), np.where(np.arange(n) == 10, np.nan, xr3))]
    # 300 點的 app 訊號在 MATLAB 走 IIR（2·N_req ≥ 300）的 7 組：DSV 拒絕（已知差異）
    iir_app = {"lp short 40 (iir)", "bp single s1=0.85 s2=0.6", "bp single s1=0.7 s2=0.95", "bp dual", "bs dual samples complex", "bs single s1=0.7",
               "bp upper over nyq"}
    if len(app) != len(A["app_cases"]):
        bad.append(f"Signal Analyzer 實測案例數 {len(A['app_cases'])} vs 硬編碼 {len(app)}")
    refused_app = set()
    for (kind, p, x), c in zip(app, A["app_cases"]):
        args, call = app_call(kind, p)
        fs = 1000.0 if args["fs"] == "Fs" else None
        try:
            y, info = filter_signal(kind, x, args["wpass"], fs, args["steepness"], args["atten"])
            got_warn = (WARNING_PREFIX + info["warnings"][-1]) if info["warnings"] else ""
            got_err = ""
            if np.asarray(y).shape != np.asarray(x).shape:
                bad.append(f"{c['name']}: 形狀 {np.asarray(y).shape}")
        except FilterError as e:
            got_warn, got_err = "", e.identifier
        if c["ok"]:
            if got_err == "dsv:filter:SignalTooShortForFIR" and c["name"] in iir_app:
                refused_app.add(c["name"])
            elif got_err:
                bad.append(f"{c['name']}: DSV 丟 {got_err}")
            elif got_warn != (c.get("warning_id") or ""):
                bad.append(f"{c['name']}: 警告 {got_warn!r} vs {c.get('warning_id')!r}")
            elif c.get("dialog_key") and not got_warn.endswith(c["dialog_key"]):
                bad.append(f"{c['name']}: 訊息代碼 {c['dialog_key']}")
            if c.get("max_abs_diff_vs_call") != 0 or c.get("time_unchanged") is not True or set(c.get("output_fields") or []) != {"Data", "Time"}:
                bad.append(f"{c['name']}: 研究資料說 app 和函式呼叫有差（max_abs_diff {c.get('max_abs_diff_vs_call')}）")
        elif got_err != c.get("error_id", ""):
            bad.append(f"{c['name']}: {got_err!r} vs {c.get('error_id')!r}")
        # compared_call（研究者手寫，預設值省略）要和 app_call 的呼叫一致：兩邊都去掉預設的 Steepness 0.85／StopbandAttenuation 60 再比

        def norm(s):
            return s.replace(",'Steepness',0.85", "").replace(",'StopbandAttenuation',60", "")
        if norm(call) != norm(c["compared_call"]):
            bad.append(f"{c['name']}: {call} vs {c['compared_call']}")
    if refused_app != iir_app:
        bad.append(f"拒絕的 app 案例 {sorted(refused_app)} vs 預期 {sorted(iir_app)}")
    check(not bad, f"Signal Analyzer 參數對應 vs MATLAB app（程式碼產生器 {len(A['generated_code'])} 組字串一致；Signal Analyzer 實測 {len(A['app_cases'])} 組的"
                   f"呼叫、警告／對話框訊息代碼、輸出形狀一致，其中 MATLAB 走 IIR 的 {len(refused_app)} 組 300 點訊號 DSV 丟 SignalTooShortForFIR（已知差異）；"
                   f"app 輸出＝函式呼叫（差 0、Time 不變）" + (f"（不一致：{bad}）" if bad else ""))
    # 文字與 DSV 自己的防呆
    msgs = []
    ok_txt = all(warning_text(k, False, kd) and warning_text(k, True, kd) for k in WARNINGS for kd in KINDS)
    ok_txt = ok_txt and "3 samples" in warning_text("AllPassBecauseSignalIsTooShort", False, "lowpass") \
        and "6 samples" in warning_text("AllPassBecauseSignalIsTooShort", False, "bandstop") and "6 個" in warning_text("AllPassBecauseSignalIsTooShort", True, "bandpass")
    try:
        lowpass(xr[:40], 0.3)
        msgs.append("lowpass(40 點) 沒丟錯誤")
    except FilterError as e:
        m = re.search(r"has (\d+) samples.*needs order (\d+).*at least (\d+) samples", e.message)
        if not (e.identifier == "dsv:filter:SignalTooShortForFIR" and m and m.groups() == ("40", "66", "133") and e.length == 40
                and e.required_order == 66 and e.min_length == 133 and "40 個樣本" in e.message_zh and "66 階" in e.message_zh and "133 個樣本" in e.message_zh):
            msgs.append(f"太短訊息：{e.identifier} {e.message!r} {e.message_zh!r}")
    probes = [("design(highpass 0.5 Hz @ 1 MHz, length=None)", lambda: design("highpass", 0.5, 1e6), "dsv:filter:FilterOrderTooLarge"),
              ("design(bandpass [1 2] Hz @ 1 MHz, length=None)", lambda: design("bandpass", [1, 2], 1e6), "dsv:filter:FilterOrderTooLarge"),
              ("design(highpass 1e-9, length=None)", lambda: design("highpass", 1e-9), "dsv:filter:FilterOrderTooLarge"),
              ("design(lowpass 1-1e-9, length=None)", lambda: design("lowpass", 1 - 1e-9), "dsv:filter:FilterOrderTooLarge"),
              ("design(lowpass 1-1e-16: 過渡帶寬 0)", lambda: design("lowpass", 1 - 1.2e-16), "dsv:filter:FilterOrderTooLarge"),
              ("design(highpass 0.5 Hz @ 1 MHz, length=1e9)", lambda: design("highpass", 0.5, 1e6, 10 ** 9), "dsv:filter:FilterOrderTooLarge"),
              ("design(highpass 0.5 Hz @ 1 MHz, length=1000)", lambda: design("highpass", 0.5, 1e6, 1000), "dsv:filter:SignalTooShortForFIR"),
              ("lowpass atten 6200", lambda: lowpass(xr, 0.3, atten=6200), "dsv:filter:StopbandAttenuationTooLarge"),
              ("lowpass atten 1e4", lambda: lowpass(xr, 0.3, atten=1e4), "dsv:filter:StopbandAttenuationTooLarge"),
              ("lowpass impulse 'iir'", lambda: lowpass(xr, 0.3, impulse="iir"), "dsv:filter:IIRNotImplemented"),
              ("lowpass(20 點) impulse 'fir'", lambda: lowpass(xr[:20], 0.3, impulse="fir"), WARNING_PREFIX + "SignalLengthForFIR"),
              ("complex atten", lambda: lowpass(xr, 0.3, atten=60 + 1j), "MATLAB:lowpass:expectedReal"),
              ("complex steepness", lambda: lowpass(xr, 0.3, steepness=0.8 + 0.5j), "MATLAB:lowpass:expectedReal"),
              ("complex array steepness", lambda: bandpass(xr, [0.2, 0.5], steepness=np.array([0.8 + 0.5j])), "MATLAB:bandpass:expectedReal"),
              ("complex wpass", lambda: lowpass(xr, 0.3 + 0.1j), "MATLAB:lowpass:expectedReal"),
              ("complex fs", lambda: lowpass(xr, 100, fs=1000 + 1j), "MATLAB:lowpass:expectedReal"),
              ("string wpass", lambda: lowpass(xr, "0.3"), "MATLAB:lowpass:invalidType"),
              ("string steepness", lambda: lowpass(xr, 0.3, steepness="0.9"), "MATLAB:lowpass:invalidType"),
              ("None steepness (bandpass)", lambda: lowpass(xr, 0.3, steepness=[None]), "MATLAB:lowpass:invalidType"),
              ("bool atten", lambda: lowpass(xr, 0.3, atten=True), "MATLAB:lowpass:invalidType"),
              ("empty fs", lambda: lowpass(xr, 100, fs=np.array([])), "MATLAB:lowpass:expectedNonempty"),
              ("2-D wpass", lambda: bandpass(xr, [[0.2, 0.5], [0.3, 0.6]]), "MATLAB:bandpass:expectedVector"),
              ("impulse 'x'", lambda: lowpass(xr, 0.3, impulse="x"), "dsv:filter:InvalidImpulseResponse"),
              ("bad kind", lambda: filter_signal("notch", xr, 0.3), "dsv:filter:InvalidKind"),
              ("3-D signal", lambda: lowpass(np.zeros((4, 4, 4)), 0.3), WARNING_PREFIX + "InvalidVectorOrMatrixType"),
              ("ragged list signal", lambda: lowpass([[1.0, 2.0], [3.0]], 0.3), WARNING_PREFIX + "InvalidInputDataType"),
              ("bool signal", lambda: lowpass(np.ones(100, dtype=bool), 0.3), WARNING_PREFIX + "InvalidInputDataType")]
    t0 = _time.time()
    for name, f, want in probes:
        try:
            f()
            msgs.append(f"{name}: 沒丟錯誤")
        except FilterError as e:
            if e.identifier != want or not e.message or not e.message_zh:
                msgs.append(f"{name}: {e.identifier} vs {want}")
        except Exception as e:  # noqa: BLE001
            msgs.append(f"{name}: {type(e).__name__} {e}")
    dt_probe = _time.time() - t0
    check(ok_txt and not msgs and dt_probe < 2.0,
          f"訊息與防呆：{len(WARNINGS)} 種警告都有英文與繁體中文、全通警告的樣本數照函式（3／6）；lowpass(40 點, 0.3) 丟 SignalTooShortForFIR 且訊息給 L=40、"
          f"所需階數 66、至少 133 個樣本（英文＋中文）；{len(probes)} 個壞參數都丟指定的 FilterError（階數上限 2²⁰ 含 length=None／超長訊號／過渡帶寬 0、"
          f"阻帶衰減太大、'iir'、MATLAB 的 SignalLengthForFIR、複數／字串／bool／None／2-D 參數、3-D／不規則／bool 訊號），共 {dt_probe:.2f}s"
          + (f"（{msgs}）" if msgs else ""))
    # 數值捷徑：chirp-z／分塊 DFT／Horner 對「相位取餘數的逐項＋補償加總（math.fsum）」參考值、overlap-add vs 直接卷積、形狀
    def horner(b, f):
        z = np.exp(-1j * np.pi * np.asarray(f, dtype=float))
        H = np.zeros(z.shape, dtype=complex)
        for c in np.asarray(b)[::-1]:
            H = H * z + c
        return H

    def exact_ref(b, f):
        n = np.arange(b.size, dtype=float)
        out = np.empty(f.size, dtype=complex)
        for i, fi in enumerate(f):
            term = b * _exp_neg_jpi(fi, n)
            out[i] = math.fsum(term.real) + 1j * math.fsum(term.imag)
        return out
    worst = {"chirp-z": 0.0, "block-DFT": 0.0, "Horner": 0.0}
    dt_cz = 0.0
    for taps in (71, 451, 3001, (1 << 16) + 1):                      # 65537 taps：Horner 要幾秒，chirp-z 幾毫秒；相位取餘數讓精度不掉
        bb = fir1_kaiser(taps - 1, 0.3, "low", 5.0) if taps > 3001 else rng.standard_normal(taps) * np.hanning(taps)
        scale = float(np.sum(np.abs(bb)))                            # 加總的自然尺度 Σ|b|（阻帶的 |H| 可以只有 1e-6，相對它沒意義）
        for fa, fb, m in ((0.3123, 0.7, 4096), (0.0, 0.29, 1024), (0.0, 255 / 256, 256)):
            fgrid = np.linspace(fa, fb, m)
            pick = np.linspace(0, m - 1, 48).astype(int)
            ref = exact_ref(bb, fgrid[pick])
            t0 = _time.time()
            H_cz = freq_response(bb, fgrid)
            dt_cz = max(dt_cz, _time.time() - t0)
            hor = horner(bb, fgrid)[pick] if (taps <= 3001 or m == 1024) else None   # 65537 taps 的 Horner 只量一個格點（它慢）
            for name, H in (("chirp-z", H_cz[pick]), ("block-DFT", _block_dft(bb, fgrid[pick])), ("Horner", hor)):
                if H is not None:
                    worst[name] = max(worst[name], float(np.max(np.abs(H - ref))) / scale)
    worst_big = worst["chirp-z"]
    xl = rng.standard_normal(60000) + 1j * rng.standard_normal(60000)
    b600 = fir1_kaiser(600, 0.3, "low", 5.0)
    y_dir = np.convolve(xl, b600)
    e_ola = max(float(np.max(np.abs(_overlap_add(xl, b600) - y_dir))), float(np.max(np.abs(_overlap_add(xl, b600, 2048) - y_dir))),
                float(np.max(np.abs(_overlap_add(xl.real, b600, 1024) - y_dir.real)))) / float(np.max(np.abs(y_dir)))
    y_fft = apply_fir(xl, b600)                                      # N·L = 3.6e7 > 2e7 → overlap-add
    e_fft = float(np.max(np.abs(y_fft - y_dir[300:300 + xl.size]))) / float(np.max(np.abs(y_dir)))
    x200 = sig("short_real_200")
    Y2, i2 = lowpass(np.column_stack([x200, 2 * x200]), 0.3)
    y1, _ = lowpass(x200, 0.3)
    yrow, _ = lowpass(x200[None, :], 0.3)
    y32, _ = lowpass(x200.astype(np.float32), 0.3)
    ok_shape = (Y2.shape == (200, 2) and np.array_equal(Y2[:, 0], y1) and np.allclose(Y2[:, 1], 2 * y1, rtol=1e-12, atol=0)
                and yrow.shape == (1, 200) and np.array_equal(yrow[0], y1) and y32.dtype == np.float64 and np.max(np.abs(y32 - y1)) < 1e-6)
    check(worst_big < 2e-11 and worst["block-DFT"] < 1e-13 and worst["Horner"] < 2e-11 and e_ola < 1e-13 and e_fft < 1e-13 and ok_shape,
          f"數值捷徑：71／451／3001／65537 taps 在三種等距格點（4096／1024／256 點）的 |H| 對補償加總參考值的誤差（÷Σ|b|）：chirp-z {worst_big:.2g}、"
          f"Horner {worst['Horner']:.2g}（兩者在 65537 taps 都是 ~1e-12：FFT 捨入 ∝ √(N+M)、Horner 的相位漂移 ∝ N·eps）、分塊 DFT {worst['block-DFT']:.2g}；"
          f"65537 taps 的 4096 點 chirp-z 最慢 {dt_cz * 1e3:.0f} ms；"
          f"60000 點複數 × 601 taps 的 overlap-add（自動／2048／1024 點 FFT、多段）vs 直接卷積 {e_ola:.2g}，apply_fir 走 FFT 路徑 {e_fft:.2g}；"
          f"2 欄矩陣、列向量、float32 輸入的形狀與逐欄結果正確")
    # 效能（機器相關）
    x6 = rng.standard_normal(1_000_000)
    t0 = _time.time()
    y1, i1 = lowpass(x6, 0.3)
    y2, i2 = bandstop(x6, [100, 250], 1000.0, [0.6, 0.9])
    y3, i3 = highpass(x6 + 1j * x6[::-1], 200.0, 1000.0, 0.95, 80)
    dt = _time.time() - t0
    t0 = _time.time()
    y5, i5 = highpass(x6, 100.0, 1e6)                              # MATLAB 也會設計這麼大的 FIR（階數 ~2.3e5）：chirp-z 規格檢查＋overlap-add 卷積
    dt_big = _time.time() - t0
    check(dt < 5.0 and dt_big < 15.0 and y1.size == y2.size == y3.size == y5.size == 1_000_000 and i1["order"] == 70 and i2["order"] == 448
          and i3["order"] == 426 and i5["order"] > 200000,
          f"效能（機器相關）：1e6 點 lowpass（階數 {i1['order']}）＋ bandstop 雙陡度（{i2['order']}）＋ 複數 highpass 0.95/80 dB（{i3['order']}）共 {dt:.2f}s；"
          f"1e6 點 100 Hz @ 1 MHz 高通 FIR（階數 {i5['order']}，{i5['redesigns']} 次重設計）{dt_big:.2f}s")
