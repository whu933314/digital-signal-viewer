# -*- coding: utf-8 -*-
"""眼圖（MATLAB Communications Toolbox 的 eyediagram(x, n, period, offset)）——純 numpy、向量化，和 GUI 分開。
只畫眼圖、不做眼圖量測（使用者決定；R2025a 也沒有任何可呼叫的眼圖量測函式）。

定義照 MATLAB R2025a 的 eyediagram（行為照公開文件與實測輸出對照，程式是自己寫的；文件
www.mathworks.com/help/comm/ref/eyediagram.html）。tests/matlab_ref/eye_diagram/ 是 MATLAB 畫出來的線資料（用 findobj 讀回
每個 axes 的 XData／YData／XLim／YLim）、1479 筆斜坡掃描與錯誤訊息，selftest() 逐筆比對；產生它們的腳本是 eye_ref.m、
eye_sweep.m、eye_ylim.m（研究目錄）。eye_ylim.json＋eye_inputs.txt 是較早一版參考資料（45 個輸入、44 筆 MATLAB 自動範圍與
YLim；第 45 筆 len_1 在 MATLAB 出錯，見下），自動範圍只和資料的最小／最大值有關，所以 44 筆都能重建來比。
spectrumAnalyzer 的實測擷取（scope_capture，88 筆）只涵蓋頻譜量測（OBW／通道功率／ACPR／失真／頻譜遮罩），沒有眼圖——
eyediagram 是獨立的 figure、不在任何 scope 裡，所以本模組沒有 scope 擷取資料可比，dsv_spectrum 的視窗／Welch 也用不到。

MATLAB 的作法（L 個樣本、k 從 0 起算、n＝每條 trace 的樣本數）：
- 相位：t_k = rem(k/n, 1)。θ = rem(offset/n + 0.5, 1) + eps^(2/3)，t_k > θ 的減 1（右半折到左邊）；之後若 max(t) ≤ 0 就全部加 1
  （只在偶數 n、offset = n/2、L ≤ n 時發生，決定樣本 0 落在 +period/2 還是 −period/2）。
- 右緣樣本 e_j = r + j·n，r = rem(offset + floor(n/2), n)。只要 e_j < L−1，就在它後面插一個 NaN、再把樣本 e_j 重畫一次，
  時間是 t_{e_j+1} − 1/n：所以每條完整的 trace 有 n+1 點、左右都到邊；第一條可能不完整（甚至只有一點）；最後一條不會只剩那個重複點。
- 平移：h = n/2 − 1、m = rem(offset + h, n) − h，t ← rem(t − m/n, 1)（樣本 offset 落在 t = 0；rem 保留符號、NaN 還是 NaN）；再 ×period。
- 整個眼圖是「一條」被 NaN 切開的折線（MATLAB 每個 axes 只畫一個 line 物件）。複數輸入 → [Re Im] 兩欄：同相（In-Phase）在上、
  正交（Quadrature）在下，兩個 axes 共用同一組 t 與 x／y 範圍；兩欄實數矩陣一樣處理（即使虛部全 0 的複數也算兩欄）。
- x 範圍 = [min t, max t]：偶數 n 是 ±period/2；奇數 n 是 [−(n+1)/(2n), (n−1)/(2n)]·period（不對稱——文件寫 ±period/2，實測的線資料不是，
  照實測：eye_ref.json／eye_sweep.json 的奇數 n）。資料不滿一條 trace 時只到資料所在。
- y 範圍：y_m = 1.05·max|x|；a = MATLAB 畫完後自己的自動（tick 對齊）範圍（兩個 axes 取聯集）；YLim = [min(−y_m, aLo), max(y_m, aHi)]。
- MATLAB 自動範圍（YLimitMethod 'tickaligned'）是內建的，規則從 eye_ref.json 的 31 個 axes 與 eye_ylim.json 的 44 筆
  （8 種斜坡長度、BPSK／QPSK／DC 等）反推：step 從 1、2、5 × 10^k 裡挑最小、且「包住資料的刻度數 ≤ 11」的那個（axes 高 293／342 px
  時都是 11：11 個刻度接受、12 個拒絕；沒看到 2.5 × 10^k）；下限 = floor(min/step)·step、上限 = 下限 + 格數·step（5 組不同的值連
  浮點數最後一位都和 MATLAB 一樣，例如 −1.1 + 9·0.1 = −0.20000000000000007）；資料全部同值 c → [c−1, c+1]（只驗過 c = 0；|c| 極大時的
  pad 見「未定／自行決定」）。
  自動範圍的刻度值（auto_ticks）＝linspace(下限, 上限, 格數+1)：eye_ylim.json 存了 MATLAB 自動 axes 的 YTick（48 個 axes）：46 個用 DSV
  自己的範圍算出來連浮點最後一位都相同（只有 len_lt_n 的 −0.4:0.2:1 能分辨公式——MATLAB 給 −0.20000000000000004、−5.55e-17、
  0.19999999999999996，不是 a + k·step 也不是 k·step）；第 47 個是「貼齊資料」的那個 axes（範圍本身是已知差異，但拿 MATLAB 自己的範圍
  [−2, 1] 套 linspace 也和它的 7 個刻度相同）；第 48 個是常數資料（虛部全 0 → [−1, 1]），MATLAB 給 −1:0.5:1 五個刻度，規則判定不了（見下）。

本模組只給資料：折線（t、Y）、範圍、自動範圍的刻度（auto_ticks）、trace 索引與 MATLAB 寫死的英文文字（axes_meta）。線條外觀（Color／
LineStyle／Marker／LineWidth／MarkerSize、plotstring 的解析）、eyediagram 設完 YLim 之後 MATLAB 重算的刻度（eye_ref.json 的 xtick／
ytick：手動範圍的刻度規則，而且 x 軸的刻度預算和 y 軸明顯不同——XLim ±0.5 只給 3 個 0.5 的刻度，11 個 0.1 的刻度照 y 軸規則是允許的）、
figure／axes 的顏色、位置、legend 可見性都屬於 GUI 層（plotkit／signal_viewer），eye_ref.json 裡這些屬性不在本模組比對；plotstring 案例只比線資料。
eye_ylim.json 每筆另有 predicted（eye_ylim.m 用 max|x|（鍵 maxAll）與 MATLAB 的自動範圍套同一條規則算出的 double）、match、YLimitMethod：selftest
驗證 DSV 的結果和 predicted 逐位相同、44 筆 match 全是 true、48 個 axes 全是 'tickaligned'（它們是參考資料的自我一致性，不是另一組獨立數據）。

未定／自行決定：
- MATLAB 自動範圍的已知例外：資料只超過刻度一點點時（舊參考 complex_zero_imag：max 1.0006655、step 0.5、超過 0.13% step）MATLAB
  把上限放在資料值而不是下一格；但超過 7.55% step（complex_row_n6_off5 的下限 −0.407548 → −0.5）就進位。門檻無法從資料判定
  （可能和像素有關），所以沒有實作；selftest 用「已知差異」檢查釘住兩邊的確切數字。它永遠改不了 eyediagram 最後的 YLim：貼齊的
  上限等於某個資料值、|值| ≤ max|x| < 1.05·max|x|，ylim_rule 一定選 1.05·max|x|，所以 DSV 顯示的範圍不受影響。
- 刻度上限 11 也可能隨 axes 高度變（MATLAB 的兩個 subplot 各只有 184 px 高），用 max_ticks 參數調。舊參考唯一的常數資料 axes
  （complex_zero_imag 虛部全 0、184 px）MATLAB 的刻度是 −1:0.5:1 五個，而不是 ≤ 11 規則會選的 0.2 × 11 個——這和「184 px 的預算
  < 11」一致（max_ticks ≤ 10 就會得到同樣的 5 個），但也可能是常數資料另有規則，一例分不出來；所以 auto_ticks 對沒有格點的情形
  （常數、非有限、溢位）只回傳兩個端點，selftest 用「已知差異」釘住 MATLAB 的 5 個刻度。範圍本身（[−1, 1]）兩邊相同。
- 自動範圍的浮點處理：資料離刻度不到 SNAP_ULP＝16 ulp（相對）就算在刻度上（例：0.9/0.1 = 9.000000000000002 → 刻度 9、不是 10；
  0.3/0.1 = 2.9999999999999996 → 刻度 3），其餘純 floor／ceil；回傳的範圍一定包住資料（最多差那 16 ulp）、下限 < 上限、至少一格、
  刻度數 ≤ max_ticks；資料範圍不到 32 ulp 視為常數 → [lo−1, hi+1]（|c| ≥ 2^52 時 c±1 == c，改用 32 ulp 的 pad 讓範圍不塌掉；
  第三輪：|c| 離 realmax 不到 64 ulp 時 c + pad 會溢位成 Inf——以前就這樣回傳、eye_traces 的 ylim 也跟著變 Inf，違反下面「ylim 永遠有限」
  的保證——現在溢位的那一端就用 c 本身，例：c = realmax → [realmax − 64 ulp, realmax]；另一端正常加 pad，所以下限 < 上限仍成立；
  常數 c ≠ 0 的 MATLAB 行為未驗證，但 eyediagram 的 YLim 反正被 ±1.05|c| 蓋過）。MATLAB 對「剛好在十進位刻度上」的資料怎麼處理
  沒有參考資料（參考案例裡沒有這種值），這是 DSV 自己的決定。第一輪的 1e-12 相對容差對近常數資料會給出顛倒／包不住的範圍，已改掉。
  第二輪：貼齊容差另外不得超過 step/4（snap_tol）——資料範圍只有幾十個 ulp 時（|x| ≈ 1e-30 或 1e30、範圍 40～200 ulp）step 本身只有
  幾個 ulp，16 ulp 的容差會把界限挪進資料裡一整格（例：[1.242805512410504e-30, 1.2428055124105257e-30] 以前給進資料 11 ulp 的界限，
  現在 step 5e-45、進 5 ulp、上限 step/4 = 7 ulp）；參考案例的 step 都遠大於 64 ulp，結果不變。MATLAB 在這種量級的行為未驗證。
- 整數類別的輸入（int16）：MATLAB 把 x 留在 int16 裡算，所以（a）插進去的 NaN 分隔變成 0（int16 沒有 NaN）；（b）y 範圍 1.05·max|x| 也是
  int16 運算、四捨五入成整數（int16_input：1.05·110 = 115.5 → 116，但自動範圍 ±150 蓋過，所以看不出差別；若 max|x| = 143 會是 int16(150.15)
  = 150 而 DSV 給 150.15——這是從 int16 運算推論的，未實測）；（c）axis 的向量 [min t, max t, YLim] 和 int16 的 YLim 併在一起變成 int16，
  所以 XLim 取整：int16_input 的 MATLAB XLim 是 [−1, 1]（±0.5 進位成 ±1），不是 ±0.5。DSV 一律轉 double（研究報告建議不要照抄）：
  XLim (−0.5, 0.5)、分隔是 NaN、y 範圍不取整；selftest 用「已知差異」釘住 int16_input 兩邊的確切數字（XLim 與 YData 的 3 個分隔）。
- period 必須是有限正數（MATLAB 只擋 ≤ 0，NaN／Inf 會放過）；n、offset 必須是有限整數。n 另外必須 < 2^53（dsv:eyediagram:NTooLarge，
  DSV 自訂）：再大的 double 全都是「整數」、檢查沒有意義，而且 ≥ 2^63 時 numpy 的 int64 索引運算會丟裸的 OverflowError（第二輪審查）；
  MATLAB 對 n = 1e19 不會出錯（全程 double）。超過 int64 的 Python 整數（2**64）也走同一條路（以前 numpy 把它變成 object dtype、碰巧得到 InvalidN）。
- period 太小（×period 之後所有時間值下溢成同一個數，例：period = 5e-324；L ≥ 2 時 t 至少有兩個不同值，所以 xlim 相等只可能是下溢）
  → dsv:eyediagram:PeriodUnderflow（DSV 自訂）。MATLAB 這時會在 axis() 裡因為上下限相等出錯（識別碼未驗證）。period 只是次正規（1e-323
  以上）不擋，但時間值被量化成 5e-324 的倍數，沒有實用價值。
- trace_grid(n, period) 也用 validate_args 檢查（以前不檢查：trace_grid(0) 會有裸的 RuntimeWarning、trace_grid(1) 回 [−1, 0]）。
- 輸入的維度：MATLAB 第 2 維之後的尾端單一維度不存在，所以 (L,1,1)、(1,L,1)、(L,1,1,1) 就是 L×1／1×L，和 1 維一樣處理（確定）。
  真正的 N 維（(1,1,L)、(8,1,2)、(1,2,4)…）照 [r, c] = size(x) 的語意：第 2 維起併成欄（欄優先順序）、r = 1 就攤成一欄（x(:) 的順序）、
  併完超過兩欄 → invalidSizeX。這部分沒有 MATLAB 參考資料（第二輪審查依 MATLAB 定義的描述，未實測），是 DSV 的決定。DSV 一律先併欄（未實測）。
- 太少引數（MATLAB:narginchk:notEnoughInputs）就是 Python 的 TypeError；figure handle 相關的錯誤／警告（invalidHandle2／3）DSV 沒有對應物。
  eye_ref.json 的 reuse 群組（同一個 figure handle 畫實數→複數→實數）只驗證「重畫的線資料和單獨畫一樣」（和 real_defaults／
  complex_defaults 逐點相同）；clf／重畫、Tag 檢查等 figure 語意沒有 DSV 對應物，不比。
- 純量參數：MATLAB 的 8 和 [8] 是同一個東西（isscalar），所以 n／period／offset 接受 Python 數字、numpy 0 維或只有一個元素的陣列；
  [8 8] 之類多元素才算非純量（InvalidN／NonPositivePeriod／InvalidOffset）。
- 非數值輸入（字串、None、dict、不規則巢狀 list、datetime…）→ dsv:eyediagram:NonNumericX（DSV 自訂；MATLAB 的 char 會被當成數字
  畫出來、cell 會出錯，都不值得照抄）；bool 當 0／1（MATLAB 的 logical 也能畫）。
- 單一樣本（L = 1）：t 只有一個點、x 範圍會是 [0, 0]。舊研究的 len_1 案例 MATLAB 出錯（有輸入檔、但 eye_ylim.json 沒有它的結果＝
  eyediagram 回傳了錯誤，識別碼／訊息沒留下來、也不能重跑 MATLAB）；DSV 丟 dsv:eyediagram:SingleSample（DSV 自訂訊息）。
- 資料含 NaN／±Inf：DSV 的 maxall、auto_ylim、ylim 只看有限值（所以 ylim 永遠有限；ylim_rule 自己也擋非有限的引數，見其說明），Y 裡的
  NaN／±Inf 原樣留給 GUI（MATLAB 的 plot 在那裡斷線）。NaN：MATLAB 的 max 本來就略過 NaN，兩邊相同。±Inf：MATLAB 的 max(abs(x)) 會得到 Inf、YLim 變 [−Inf, Inf]，
  而 axis／ylim 的文件寫 ±Inf 代表「該邊自動」（mathworks.com/help/matlab/ref/axis.html：'For partially automatic limits, use inf or
  -inf for the limits you want the axes to choose automatically'；ylim.html 同義），所以 MATLAB 最可能顯示有限資料的 tick 對齊自動範圍、
  不套 1.05·max|x|（例：[1, Inf, 3, −9]×4 → [−10, 4]），DSV 則照有限值走 1.05 規則給 (−10, 9.45)——刻意的差異，MATLAB 端沒有實測。
  沒有任何有限值時 y 範圍退回 [−1, 1]（MATLAB 未驗證）。
- 極大的值（|x| 接近 realmax ≈ 1.8e308）：資料範圍 hi − lo 或 tick 對齊的上限會溢位成 Inf，這時自動範圍直接回傳資料範圍 [lo, hi]；
  常數資料的 pad 溢位時那一端用 c 本身（第三輪，見上）；1.05·max|x| 溢位時改用 max|x| 本身——目的是 ylim 永遠有限、不丟 OverflowError，
  MATLAB 在這種輸入的行為未驗證。
- 配置上限（DSV 自訂保護，MATLAB 沒有）：trace_grid 的 n+1 點、trace_matrix 的 ntraces × (n+1) × C 超過 MAX_ELEMENTS＝2^24 就丟
  dsv:eyediagram:TooLarge，不會先配 8 GB 再死。eye_traces 本身只配置 O(L)（折線最多 3L 點，和輸入成正比，eyediagram 也一樣），不設上限。
- trace_grid 的公式時間 (j + floor(n/2) − n)/n·period 和折線 t 的差：|Δt| ≤ eps·period·(L/(2n) + 3)（k/n 的捨入 ≤ (L/n)·eps/2，其餘
  幾個 ulp；n 是 2 的冪時完全相等）。實測：26 個參考案例最大 2.75 eps·period（complex_row_n6_off5）、1479 筆掃描最大 2.0、
  L＝1e6／n＝7 是 56174（上界的 0.79 倍）。這是 MATLAB 自己的浮點雜訊（折線 t 和 MATLAB 逐位相同），不是誤差。
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

import numpy as np

LIM_FACT = 1.05                                   # y 範圍的放大倍數（eyediagram 實測 YLim 的 1.05·max|x|）
MAX_TICKS = 11                                    # MATLAB tickaligned：包住資料的刻度數上限（從資料反推）
DEFAULT_PERIOD = 1.0                              # eyediagram 的 period 預設
DEFAULT_OFFSET = 0                                # eyediagram 的 offset 預設
EPS = float(np.finfo(float).eps)
EPS23 = EPS ** (2.0 / 3.0)                        # 折回右半時的容差 eps^(2/3)
SNAP_ULP = 16                                     # 自動範圍：資料離刻度不到這麼多 ulp 就算在刻度上（見「未定／自行決定」）
SNAP_STEP_DIV = 4                                 # 貼齊容差另外不得超過 step / 4（極小的資料範圍：step 只有幾個 ulp 時）
MAX_ELEMENTS = 1 << 24                            # trace_grid／trace_matrix 的配置上限（DSV 自訂保護）
N_MAX = 2.0 ** 53                                 # n 的上限（DSV 自訂：double 能精確表示的整數到此為止；MATLAB 不檢查）
TITLES = {"real": "Eye Diagram ", "inphase": "Eye Diagram for In-Phase Signal", "quadrature": "Eye Diagram for Quadrature Signal"}
XLABEL, YLABEL = "Time", "Amplitude"              # MATLAB eyediagram 寫死的英文標籤
LEGEND = ("In-phase", "Quadrature")               # eyediagram 每個 axes 藏起來的 legend 文字

# 錯誤識別碼 → (英文訊息, 繁中訊息)；comm:eyediagram:* 是 MATLAB 的（訊息逐字相同），dsv:eyediagram:* 是 DSV 自訂的（MATLAB 沒有對應）
ERRORS = {
    "comm:eyediagram:EmptyX": ("Input variable X is empty.", "輸入變數 X 是空的。"),
    "comm:eyediagram:NonPositivePeriod": ("PERIOD must be a positive number.", "PERIOD 必須是正數。"),
    "comm:eyediagram:InvalidN": ("N must be an integer greater than 1.", "N 必須是大於 1 的整數。"),
    "comm:eyediagram:InvalidOffset": ("OFFSET must be an integer in the range 0 <= OFFSET < N.", "OFFSET 必須是 0 <= OFFSET < N 範圍內的整數。"),
    "comm:eyediagram:invalidSizeX": ("Number of columns in the input data, X, cannot exceed 2.", "輸入資料 X 的欄數不能超過 2。"),
    "dsv:eyediagram:NonNumericX": ("Input variable X must be a numeric (real or complex) array.", "輸入變數 X 必須是數值（實數或複數）陣列。"),
    "dsv:eyediagram:SingleSample": ("Input variable X must have at least 2 samples; one sample gives an empty time range.",
                                    "輸入變數 X 至少要有 2 個樣本；只有一個樣本時時間範圍是空的。"),
    "dsv:eyediagram:TooLarge": (f"Requested trace grid or trace matrix would exceed {MAX_ELEMENTS} elements.",
                                f"要求的 trace 時間格點或 trace 矩陣超過 {MAX_ELEMENTS} 個元素。"),
    "dsv:eyediagram:NTooLarge": ("N must be less than 2^53 (DSV limit; larger values are not exact integers in double precision).",
                                 "N 必須小於 2^53（DSV 的上限；更大的值在 double 裡已不是精確的整數）。"),
    "dsv:eyediagram:PeriodUnderflow": ("PERIOD is too small: every time value underflows to the same number, the time range is empty.",
                                       "PERIOD 太小：所有時間值都下溢成同一個數，時間範圍是空的。"),
}


class EyeDiagramError(ValueError):
    """eyediagram 的輸入錯誤：identifier＝識別碼、str(e)＝英文訊息、zh＝繁中訊息；detail（選用）附在兩種訊息後面。"""

    def __init__(self, identifier: str, detail: str = ""):
        en, zh = ERRORS[identifier]
        if detail:
            en, zh = f"{en} ({detail})", f"{zh}（{detail}）"
        super().__init__(en)
        self.identifier = identifier
        self.en = en
        self.zh = zh


def _scalar(v) -> Optional[float]:
    """純量（Python 數字、numpy 0 維或只有一個元素的陣列——MATLAB 的 isscalar）→ float；不是純量或轉不成數字 → None。"""
    try:
        a = np.asarray(v)
        if a.size != 1:
            return None
        item = a.reshape(()).item()
        if a.dtype.kind in "biuf":
            return float(item)
        if a.dtype.kind == "O" and isinstance(item, (int, float)):      # 超過 int64 的 Python 整數（例：2**64）會變 object dtype
            return float(item)
        return None
    except (TypeError, ValueError, OverflowError):
        return None


def validate_args(n, period=DEFAULT_PERIOD, offset=DEFAULT_OFFSET) -> Tuple[int, float, int]:
    """照 MATLAB 的順序檢查 period（有限正數）、n（整數 > 1）、offset（整數、0 ≤ offset < n），回傳 (n, period, offset)。
    DSV 另外要求 n < 2^53（dsv:eyediagram:NTooLarge）：再大的 double 全是「整數」、int64 索引運算也會溢位（見「未定／自行決定」）。"""
    p = _scalar(period)
    if p is None or not math.isfinite(p) or p <= 0:
        raise EyeDiagramError("comm:eyediagram:NonPositivePeriod")
    nv = _scalar(n)
    if nv is None or not math.isfinite(nv) or nv != math.floor(nv) or nv <= 1:
        raise EyeDiagramError("comm:eyediagram:InvalidN")
    if nv >= N_MAX:
        raise EyeDiagramError("dsv:eyediagram:NTooLarge", f"n = {nv:.17g}")
    ov = _scalar(offset)
    if ov is None or not math.isfinite(ov) or ov != math.floor(ov) or ov < 0 or ov >= nv:
        raise EyeDiagramError("comm:eyediagram:InvalidOffset")
    return int(nv), p, int(ov)


def _numeric_array(x) -> np.ndarray:
    """輸入 → numpy 數值陣列（bool／整數／浮點／複數）；空的 → EmptyX；字串、object、不規則巢狀 list… → NonNumericX。"""
    try:
        a = np.asarray(x)
    except (TypeError, ValueError):                              # 不規則的巢狀 list 等
        raise EyeDiagramError("dsv:eyediagram:NonNumericX") from None
    if a.size == 0:
        raise EyeDiagramError("comm:eyediagram:EmptyX")
    if a.dtype.kind not in "biufc":
        raise EyeDiagramError("dsv:eyediagram:NonNumericX")
    return a


def as_columns(x) -> np.ndarray:
    """輸入 → (L, C) 的 float 陣列：列向量／1 維 → 一欄；複數 → [Re Im] 兩欄；空的、非數值或超過兩欄就丟 EyeDiagramError。
    維度照 MATLAB 的 size 語意：第 2 維之後的尾端單一維度不存在（(L,1,1) 就是 L×1、(1,L,1) 就是 1×L）；還是 N 維的話照
    [r, c] = size(x) 把後面的維度併進欄（c = 第 2 維起的乘積，欄優先順序）；第一維是 1（列向量、(1,1,L)…）就攤成一欄（x(:) 的順序）。
    N 維的處理沒有 MATLAB 參考資料，見「未定／自行決定」。"""
    a = _numeric_array(x)
    shape = a.shape
    while len(shape) > 2 and shape[-1] == 1:                      # MATLAB 自動去掉尾端的單一維度
        shape = shape[:-1]
    a = a.reshape(shape)
    if a.ndim <= 1 or a.shape[0] == 1:
        a = a.reshape(-1, 1, order="F")                            # 列向量／(1, p, q…) → 一欄，x(:) 的欄優先順序
    elif a.ndim > 2:
        a = a.reshape(a.shape[0], -1, order="F")                   # [r, c] = size(x)：第 2 維起併成欄
    if np.iscomplexobj(a):
        a = np.hstack([a.real, a.imag])
    if a.shape[1] > 2:
        raise EyeDiagramError("comm:eyediagram:invalidSizeX")
    return np.ascontiguousarray(a, dtype=float)


def snap_tol(x: float, tick: float, step: float) -> float:
    """自動範圍的「算在刻度上」容差：SNAP_ULP ulp（相對於 x／tick 較大者），但不超過 step / SNAP_STEP_DIV——
    資料範圍只有幾十個 ulp 時 step 本身只有幾個 ulp，16 ulp 的容差會把界限挪進資料裡一整格（第二輪審查的 1e-30 例子）。"""
    return min(SNAP_ULP * EPS * max(abs(x), abs(tick)), abs(step) / SNAP_STEP_DIV)


def _on_tick(x: float, tick: float, step: float) -> bool:
    """x 和刻度值 tick 只差浮點雜訊（≤ snap_tol）。"""
    return abs(x - tick) <= snap_tol(x, tick, step)


def _fit_grid(lo: float, hi: float, max_ticks: int) -> Optional[Tuple[float, float, float, int]]:
    """lo < hi 都有限：1、2、5 × 10^k 裡最小、且包住資料的刻度數 ≤ max_ticks 的 step → (下限, 上限, step, 格數)；
    算不出有限的範圍（格數·step 溢位）→ None。"""
    rng = hi - lo
    if not math.isfinite(rng):                                   # 有限資料但範圍溢位（例如 ±1e308）：沒有刻度可對齊
        return None
    e = math.floor(math.log10(rng)) - 1
    for _ in range(12):
        for m in (1.0, 2.0, 5.0):
            step = m * 10.0 ** e
            if step <= 0.0:                                      # 次正規範圍的資料：10^e 下溢成 0，換下一個 step
                continue
            klo = math.floor(lo / step)
            if _on_tick(lo, (klo + 1) * step, step):             # lo 其實就在下一格刻度上（0.3/0.1 = 2.9999…）
                klo += 1
            a = klo * step
            if a > lo and not _on_tick(lo, a, step):             # 乘回去略大於 lo：退一格
                klo -= 1
                a = klo * step
            khi = math.ceil(hi / step)
            if _on_tick(hi, (khi - 1) * step, step):             # hi 其實就在上一格刻度上（0.9/0.1 = 9.000…2）
                khi -= 1
            nint = khi - klo
            b = a + nint * step                                  # 照 MATLAB 用「下限 + 格數·step」（浮點最後一位才會一樣）
            if b < hi and not _on_tick(hi, b, step):
                nint += 1
                b = a + nint * step
            if nint < 1 or b <= a or (a > lo and not _on_tick(lo, a, step)) or (b < hi and not _on_tick(hi, b, step)):
                continue                                         # step 比資料的 ulp 還小、包不住：換大一點的 step
            if nint + 1 <= max_ticks:
                if not (math.isfinite(a) and math.isfinite(b)):
                    return None                                  # 格數·step 溢位（例如 10 × 2e307）
                return a, b, step, nint
        e += 1
    return None                                                  # 理論上到不了（step ≥ 10·rng 時最多 2 格）


def auto_fit(lo: float, hi: float, max_ticks: int = MAX_TICKS) -> Tuple[float, float, float, int]:
    """auto_limits 的完整結果 (下限, 上限, step, 格數)：有刻度格點時 step > 0、格數 ≥ 1、上限 = 下限 + 格數·step；
    常數資料、非有限、溢位這些沒有格點的情形 step = NaN、格數 = 0（範圍見 auto_limits）。"""
    lo, hi = float(lo), float(hi)
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return -1.0, 1.0, math.nan, 0
    if hi < lo:
        lo, hi = hi, lo
    rng = hi - lo
    if rng <= 2 * SNAP_ULP * EPS * max(abs(lo), abs(hi)):         # 常數（或只差浮點雜訊）
        pad = 1.0
        if lo - pad == lo or hi + pad == hi:                     # |c| ≥ 2^52：c ± 1 == c，改用 32 ulp 讓範圍不塌掉（MATLAB 未驗證）
            pad = 2 * SNAP_ULP * EPS * max(abs(lo), abs(hi))
        a, b = lo - pad, hi + pad
        if not math.isfinite(a):                                 # |c| 離 realmax 不到 64 ulp：pad 溢位，那一端就用資料值本身（第三輪）
            a = lo
        if not math.isfinite(b):
            b = hi
        return a, b, math.nan, 0
    fit = _fit_grid(lo, hi, max_ticks)
    return fit if fit is not None else (lo, hi, math.nan, 0)


def auto_limits(lo: float, hi: float, max_ticks: int = MAX_TICKS) -> Tuple[float, float]:
    """MATLAB 自動（tick 對齊）的軸範圍：資料 [lo, hi] → 1、2、5 × 10^k 裡最小、且包住資料的刻度數 ≤ max_ticks 的 step，
    範圍 = [floor(lo/step)·step, 下限 + 格數·step]。保證：下限 ≤ lo、上限 ≥ hi（資料離刻度不到 snap_tol 時算在刻度上：最多差
    min(SNAP_ULP ulp, step/4)）、下限 < 上限、至少一格。lo == hi 或兩者差不到 2·SNAP_ULP ulp → [lo−1, hi+1]（±1 低於浮點解析度時改 pad 32 ulp；
    pad 讓那一端溢位時——|c| 離 realmax 不到 64 ulp——該端就用資料值本身，結果仍有限）。沒有有限值 → [−1, 1]。
    hi − lo 或算出的上限溢位成 Inf（|資料| 接近 realmax）→ 直接回傳 [lo, hi]（見模組說明「未定／自行決定」）。"""
    a, b, _, _ = auto_fit(lo, hi, max_ticks)
    return a, b


def auto_ticks(lo: float, hi: float, max_ticks: int = MAX_TICKS) -> np.ndarray:
    """MATLAB 自動範圍的刻度值：linspace(下限, 上限, 格數+1)——舊參考 eye_ylim.json 的 47 個 axes 連浮點最後一位都和 MATLAB 的 YTick
    相同（只有 len_lt_n 的 −0.4:0.2:1 能分辨公式：MATLAB 給 −0.20000000000000004、−5.55e-17、0.19999999999999996…，就是 linspace）。
    沒有格點的情形（常數資料、非有限、溢位）只回傳兩個端點 [下限, 上限]：常數資料 MATLAB 的刻度規則無法從唯一的一例判定
    （見「未定／自行決定」與 selftest 的已知差異）。"""
    a, b, _, nint = auto_fit(lo, hi, max_ticks)
    if nint < 1:
        return np.array([a, b])
    return np.linspace(a, b, nint + 1)


def ylim_rule(maxall: float, auto_lo: float, auto_hi: float, lim_fact: float = LIM_FACT) -> Tuple[float, float]:
    """eyediagram 的 y 範圍：[min(−1.05·max|x|, 自動下限), max(1.05·max|x|, 自動上限)]；maxall = max|x| ≥ 0。
    回傳一定有限（第三輪：以前 maxall = Inf 回 (−Inf, Inf)、NaN 回 (NaN, NaN)）：1.05·max|x| 溢位成 Inf 時改用 max|x| 本身；
    maxall 本身非有限（NaN／±Inf）就不套這一項、只回自動範圍——MATLAB 的 YLim 文件把 ±Inf 當「該邊自動」；eye_traces 只看有限值，
    只在完全沒有有限值時傳 NaN 進來（那時每欄的自動範圍都是 ±1 → (−1, 1)）；自動範圍那一邊非有限時只用 ∓1.05·max|x|；
    全都非有限 → [−1, 1]（MATLAB 未驗證；見「未定／自行決定」）。"""
    maxall, lo, hi = float(maxall), float(auto_lo), float(auto_hi)
    if math.isfinite(maxall):
        ym = lim_fact * maxall
        if not math.isfinite(ym):
            ym = maxall
        lo = min(-ym, lo) if math.isfinite(lo) else -ym
        hi = max(ym, hi) if math.isfinite(hi) else ym
    else:
        lo = lo if math.isfinite(lo) else -1.0
        hi = hi if math.isfinite(hi) else 1.0
    return lo, hi


def eye_traces(x, n, period=DEFAULT_PERIOD, offset=DEFAULT_OFFSET, max_ticks: int = MAX_TICKS) -> Dict[str, Any]:
    """眼圖折線（和 MATLAB eyediagram 畫出來的 line 一樣，含 NaN 分隔與邊界樣本重畫）。
    回傳 dict：t（M）、Y（M × C；第 c 欄就是第 c 個 axes 的 YData）、ncol（1 或 2）、complex、ntraces、
    xlim、ylim（eyediagram 規則）、auto_ylim（C × 2，每欄的 MATLAB 自動範圍）、maxall、n、period、offset、
    col（每個點在 trace 裡的位置 0..n，NaN 處是 −1）、seg（每個點屬於第幾條 trace）。
    檢查順序照 MATLAB：EmptyX／NonNumericX → period → n → offset → 欄數 → （DSV）單一樣本。
    只配置 O(L) 的記憶體（和 n 無關）；完整 trace 的 n+1 個時間點用 trace_grid(n, period) 另外算。"""
    a = _numeric_array(x)
    n, period, offset = validate_args(n, period, offset)
    Y = as_columns(a)
    L, C = Y.shape
    if L < 2:
        raise EyeDiagramError("dsv:eyediagram:SingleSample")
    nf = float(n)
    k = np.arange(L, dtype=float)
    t = np.fmod(k / nf, 1.0)
    thr = math.fmod(offset / nf + 0.5, 1.0) + EPS23
    t[t > thr] -= 1.0
    if t.max() <= 0:
        t = t + 1.0
    r = int(math.fmod(offset + math.floor(nf / 2), nf))          # 第一個右緣樣本（0 起算）
    nb = (L - 2 - r) // n + 1 if L - 2 >= r else 0                 # 要插分隔的右緣樣本數（e_j ≤ L−2）
    B = r + n * np.arange(nb)
    ki = np.arange(L)
    before = np.clip((ki - 1 - r) // n + 1, 0, nb)                 # 樣本 k 前面有幾個分隔
    idx = ki + 2 * before
    M = L + 2 * nb
    T = np.empty(M)
    Yo = np.empty((M, C))
    col = np.empty(M, dtype=np.int64)
    seg = np.empty(M, dtype=np.int64)
    T[idx] = t
    Yo[idx] = Y
    col[idx] = n - np.mod(r - ki, n)                               # 右緣樣本 = n、往左遞減
    seg[idx] = before
    if nb:
        pe = B + 2 * np.arange(nb)
        T[pe + 1] = np.nan
        Yo[pe + 1] = np.nan
        col[pe + 1] = -1
        seg[pe + 1] = np.arange(nb)
        T[pe + 2] = t[B + 1] - 1.0 / nf
        Yo[pe + 2] = Y[B]
        col[pe + 2] = 0
        seg[pe + 2] = np.arange(nb) + 1
    h = nf / 2.0 - 1.0
    m = math.fmod(offset + h, nf) - h
    with np.errstate(invalid="ignore"):
        T = np.fmod(T - m / nf, 1.0) * period
    xlim = (float(np.nanmin(T)), float(np.nanmax(T)))
    if xlim[0] == xlim[1]:                                         # L ≥ 2 時 t 至少有兩個不同值，相等只可能是 period 太小、×period 下溢
        raise EyeDiagramError("dsv:eyediagram:PeriodUnderflow", f"period = {period:.3g}, n = {n}")
    fin = np.isfinite(Y)                                           # 只看有限值（NaN／±Inf 的處理見「未定／自行決定」）
    maxall = float(np.max(np.abs(Y[fin]))) if fin.any() else math.nan
    auto = np.empty((C, 2))
    for c in range(C):
        yc = Y[fin[:, c], c]
        auto[c] = auto_limits(yc.min(), yc.max(), max_ticks) if yc.size else (-1.0, 1.0)
    ylim = ylim_rule(maxall, auto[:, 0].min(), auto[:, 1].max())      # 沒有任何有限值時 maxall = NaN、每欄 auto = ±1 → (−1, 1)
    return {"t": T, "Y": Yo, "ncol": C, "complex": C == 2, "ntraces": nb + 1, "xlim": xlim,
            "ylim": ylim, "auto_ylim": auto, "maxall": maxall, "n": n, "period": period, "offset": offset,
            "col": col, "seg": seg}


def trace_grid(n: int, period: float = DEFAULT_PERIOD) -> np.ndarray:
    """一條完整 trace 的 n+1 個時間點（位置 0..n）：(j + floor(n/2) − n)/n · period，位置 0 是上一條重畫的最後一個樣本。
    偶數 n：−period/2 … +period/2；奇數 n：−(n+1)/(2n)·period … (n−1)/(2n)·period。和折線的 t 差 ≤ eps·period·(L/(2n) + 3)
    （見模組說明）。n、period 用 validate_args 檢查（InvalidN／NonPositivePeriod／NTooLarge）；n + 1 > MAX_ELEMENTS → dsv:eyediagram:TooLarge。"""
    n, period, _ = validate_args(n, period)
    if n + 1 > MAX_ELEMENTS:
        raise EyeDiagramError("dsv:eyediagram:TooLarge", f"trace_grid: n + 1 = {n + 1}")
    return (np.arange(n + 1) + (n // 2 - n)) / float(n) * float(period)


def trace_matrix(res: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    """eye_traces 的結果 → (tgrid (n+1), Y3 (ntraces × (n+1) × C))：每條 trace 一列、第 0 欄是上一條的最後一個樣本（重畫的那點），
    不完整的 trace 補 NaN。tgrid = trace_grid(n, period)。記憶體 O(ntraces·(n+1))；超過 MAX_ELEMENTS → dsv:eyediagram:TooLarge。"""
    ntr, n1, C = int(res["ntraces"]), int(res["n"]) + 1, int(res["ncol"])
    if ntr * n1 * C > MAX_ELEMENTS:
        raise EyeDiagramError("dsv:eyediagram:TooLarge", f"trace_matrix: {ntr} × {n1} × {C} = {ntr * n1 * C}")
    col, seg = res["col"], res["seg"]
    ok = col >= 0
    Y3 = np.full((ntr, n1, C), np.nan)
    Y3[seg[ok], col[ok]] = res["Y"][ok]
    return trace_grid(res["n"], res["period"]), Y3


def axes_meta(ncol: int) -> Tuple[Dict[str, str], ...]:
    """每個 axes 的 MATLAB 文字（MATLAB eyediagram 寫死的英文）：一欄 → 一個 axes（title 'Eye Diagram '，legend 'In-phase'）；
    兩欄 → 同相在上、正交在下。每項 dict：title、xlabel、ylabel、legend（eyediagram 把 legend 設成不可見）。"""
    if ncol == 1:
        keys = ("real",)
    elif ncol == 2:
        keys = ("inphase", "quadrature")
    else:
        raise EyeDiagramError("comm:eyediagram:invalidSizeX")
    return tuple({"title": TITLES[k], "xlabel": XLABEL, "ylabel": YLABEL, "legend": LEGEND[i]} for i, k in enumerate(keys))


def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 畫的眼圖線資料逐筆比對（tests/matlab_ref/eye_diagram；eye_ref.m／eye_sweep.m／eye_ylim.m 產生）。"""
    import json
    import os
    import sys
    import time as _time
    d = os.path.join(ref_dir, "eye_diagram")
    if not os.path.isfile(os.path.join(d, "eye_ref.json")):
        check(True, "（沒有 tests/matlab_ref/eye_diagram：略過 MATLAB 眼圖比對）")
        return

    def arr(v):
        return np.asarray([np.nan if a is None else a for a in np.atleast_1d(v)], dtype=float)

    def exact(a, b):
        """逐點完全相等（NaN 位置也要一樣；多維就攤平）；回傳 (ok, 第一個不同的攤平索引, mine, ref)。"""
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        if a.shape != b.shape:
            return False, -1, a.shape, b.shape
        a, b = a.ravel(), b.ravel()
        bad = np.nonzero(~((a == b) | (np.isnan(a) & np.isnan(b))))[0]
        if bad.size:
            i = int(bad[0])
            return False, i, a[i], b[i]
        return True, -1, None, None

    def same(a, b):
        return exact(a, b)[0]

    def grid_dev(res, L):
        """trace_grid 公式 vs 折線 t：最大 |Δt| 以 eps·period 為單位，和模組說明的上界 L/(2n) + 3 一起回傳。"""
        tg = trace_grid(res["n"], res["period"])
        pts = res["col"] >= 0
        dev = float(np.max(np.abs(tg[res["col"][pts]] - res["t"][pts]))) / (EPS * res["period"])
        return dev, L / (2.0 * res["n"]) + 3.0

    def load_input(path):
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        a = np.loadtxt([ln for ln in txt.splitlines() if ln and not ln.startswith("#")], ndmin=2)
        if "complex input" in txt:
            return a[:, 0] + 1j * a[:, 1]
        return a[:, 0] if a.shape[1] == 1 else a

    def load_old_inputs(path):
        """eye_inputs.txt（舊參考的 45 個輸入）：每筆 3 行——'# name size=RxC complex=0/1'、're …'、'im …'（x(:) 的欄優先順序）。"""
        out = {}
        with open(path, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        for i in range(0, len(lines), 3):
            parts = lines[i].lstrip("#").split()
            kv = dict(p.split("=") for p in parts[1:])
            rows, cols = (int(v) for v in kv["size"].split("x"))
            re_v = np.array(lines[i + 1].split()[1:], dtype=float)
            im_v = np.array(lines[i + 2].split()[1:], dtype=float)
            v = re_v + 1j * im_v if kv["complex"] == "1" else re_v
            if kv["complex"] != "1" and im_v.any():
                raise ValueError(f"{parts[0]}: 實數輸入的虛部不是 0")
            out[parts[0]] = v.reshape((rows, cols), order="F")
        return out

    def nums(args):
        return [float(a.split("(")[1].rstrip(")")) for a in args if "(" in a]

    cnt = [0, 0]                                                           # MATLAB 參考項目：比對筆數、相符筆數（已知差異算不符）

    def tally(ok, k=1):
        cnt[0] += k
        cnt[1] += k if ok else 0
        return ok

    R = json.load(open(os.path.join(d, "eye_ref.json"), encoding="utf-8"))
    auto_ref = {a["name"]: np.atleast_2d(np.asarray(a["auto_ylim"], dtype=float)) for a in R["auto_ylim"]}
    bad_tr, bad_xl, bad_yl, bad_auto, bad_final, bad_mat, bad_lbl = [], [], [], [], [], [], []
    naxes = 0
    results = {}
    worst_grid = (0.0, "", 0.0)
    int16_rec = {}                                                         # int16_input 的已知差異（XLim 取整、NaN 分隔變 0）：下面用專門的檢查釘住數字
    for c in R["cases"]:
        name = c["name"]
        x = load_input(os.path.join(d, c["input_file"]))
        if c["input_is_complex"] and not np.iscomplexobj(x):
            x = x.astype(complex)
        a = nums(c["args"])
        res = eye_traces(x, a[0], a[1] if len(a) > 1 else DEFAULT_PERIOD, a[2] if len(a) > 2 else DEFAULT_OFFSET)
        results[name] = res
        axes = c["axes"] if isinstance(c["axes"], list) else [c["axes"]]
        is_int = c["input_class"] == "int16"
        if res["ncol"] != len(axes):
            bad_tr.append(f"{name}: {res['ncol']} 欄 vs MATLAB {len(axes)} 個 axes")
            continue
        meta = axes_meta(res["ncol"])
        for i, ax in enumerate(axes):
            naxes += 1
            ln = ax["lines"] if isinstance(ax["lines"], dict) else ax["lines"][0]
            okx, ix, mx, rx = exact(res["t"], arr(ln["XData"]))
            oky, iy, my, ry = exact(res["Y"][:, i], arr(ln["YData"]))
            tally(okx and oky)                                           # int16 的 YData 一定不符（NaN 分隔 vs 0）：算已知差異、另外釘住
            if is_int:
                int16_rec.update(name=name, okx=okx, y_dsv=res["Y"][:, i], y_ml=arr(ln["YData"]), ydata_class=ln["ydata_class"],
                                 xlim_dsv=res["xlim"], xlim_ml=ax["xlim"], ylim_dsv=res["ylim"], ylim_ml=ax["ylim"], maxall=res["maxall"],
                                 x_in=as_columns(x), auto_dsv=res["auto_ylim"][i], auto_ml=auto_ref[name][i])
            else:
                if not okx:
                    bad_tr.append(f"{name}[{i}] XData@{ix}: {mx} vs {rx}")
                if not oky:
                    bad_tr.append(f"{name}[{i}] YData@{iy}: {my} vs {ry}")
            got = (meta[i]["title"], meta[i]["xlabel"], meta[i]["ylabel"], [meta[i]["legend"]], "off")
            ref = (ax["title"], ax["xlabel"], ax["ylabel"], ax["legend"]["string"], ax["legend"]["visible"])
            if not tally(got == ref):
                bad_lbl.append(f"{name}[{i}]: {got} vs {ref}")
        ax0 = axes[0]
        if is_int:
            tally(False)                                                 # int16 的 XLim 取整（MATLAB [−1, 1] vs DSV ±0.5）：已知差異，下面釘住
        elif not tally(same(res["xlim"], ax0["xlim"])):
            bad_xl.append(f"{name}: {res['xlim']} vs {ax0['xlim']}")
        ref_auto = auto_ref[name]
        yl = ylim_rule(res["maxall"], ref_auto[:, 0].min(), ref_auto[:, 1].max())
        if not tally(same(yl, ax0["ylim"])):
            bad_yl.append(f"{name}: {yl} vs {ax0['ylim']}")
        for i in range(res["ncol"]):
            if not tally(same(res["auto_ylim"][i], ref_auto[i])):
                bad_auto.append(f"{name}[{i}]: {res['auto_ylim'][i].tolist()} vs {ref_auto[i].tolist()}")
        if not tally(same(res["ylim"], ax0["ylim"])):
            bad_final.append(f"{name}: {res['ylim']} vs {ax0['ylim']}")
        tg, Y3 = trace_matrix(res)
        pts = res["col"] >= 0
        back = Y3[res["seg"][pts], res["col"][pts]]                   # 矩陣裡對應每個折線點的值
        dev, bnd = grid_dev(res, as_columns(x).shape[0])
        if dev > worst_grid[0]:
            worst_grid = (dev, name, bnd)
        if not (np.array_equal(back, res["Y"][pts]) and np.sum(np.isfinite(Y3[:, :, 0])) == np.sum(np.isfinite(res["Y"][:, 0]))
                and Y3.shape == (res["ntraces"], res["n"] + 1, res["ncol"]) and tg.shape == (res["n"] + 1,) and dev <= bnd):
            bad_mat.append(f"{name}（Δt {dev:.2f} eps·period，上界 {bnd:.2f}）")
    n_cases = len(R["cases"])
    check(not bad_tr, f"眼圖折線 vs MATLAB eyediagram（{n_cases - 1} 案例、{naxes - 1} 個 axes：n＝2～8、offset 0～n−1、奇數 n、L＜n、L＝n、列向量、"
                      f"複數／兩欄／虛部全 0、int8 參數、3 個 plotstring 案例只比線資料）：XData／YData 逐點完全相等（含 NaN 位置）；"
                      f"int16 案例的 YData 是已知差異、另外釘住；線條外觀／刻度／figure 顏色屬於 GUI 層，不比"
          + (f"（不一致 {len(bad_tr)}：{bad_tr[:3]}）" if bad_tr else ""))
    check(not bad_xl, f"x 範圍 vs MATLAB（{n_cases - 1} 案例；偶數 n ±period/2、奇數 n 不對稱、短資料只到資料；int16 的 XLim 取整是已知差異、另外釘住）：完全相等"
          + (f"（不一致：{bad_xl[:3]}）" if bad_xl else ""))
    check(not bad_yl, f"y 範圍規則 max(1.05·max|x|, MATLAB 自動範圍) vs eyediagram 的 YLim（{n_cases} 案例，用 MATLAB 自己的自動範圍）：完全相等"
          + (f"（不一致：{bad_yl[:3]}）" if bad_yl else ""))
    check(not bad_auto, f"tick 對齊自動範圍 vs MATLAB auto_ylim（{naxes} 個 axes：step 0.05／0.1／0.2／0.5／50、常數 0 → ±1）：完全相等（含浮點最後位）"
          + (f"（不一致：{bad_auto[:3]}）" if bad_auto else ""))
    check(not bad_final, f"eye_traces 算出的 ylim vs eyediagram 的 YLim（{n_cases} 案例，自動範圍也自己算）：完全相等" + (f"（不一致：{bad_final[:3]}）" if bad_final else ""))
    check(not bad_lbl, f"axes 文字 vs MATLAB（{naxes} 個 axes）：title 'Eye Diagram '（尾端有空白）／'… for In-Phase Signal'／'… for Quadrature Signal'、"
                       f"xlabel 'Time'、ylabel 'Amplitude'、legend 'In-phase'／'Quadrature' 且不可見" + (f"（不一致：{bad_lbl[:3]}）" if bad_lbl else ""))
    # 已知差異：int16 輸入——MATLAB 把 x 留在 int16 裡算（NaN 分隔 → 0、axis 向量併成 int16 → XLim 取整），DSV 一律轉 double（研究報告建議不要照抄）
    r16 = int16_rec
    if r16:
        sep_dsv = np.flatnonzero(np.isnan(r16["y_dsv"]))                     # DSV 的分隔位置（NaN）
        sep_ml = np.flatnonzero(r16["y_ml"] == 0)                            # MATLAB 的 0（輸入沒有 0，所以 0 只可能是分隔）
        others = np.ones(r16["y_dsv"].size, dtype=bool)
        others[sep_dsv] = False
        ym16 = LIM_FACT * r16["maxall"]
        ym16_int = math.floor(abs(ym16) + 0.5)                               # MATLAB int16(115.5)：四捨五入、.5 往遠離 0 進位 → 116
        ok16 = (r16["name"] == "int16_input" and r16["okx"] and r16["ydata_class"] == "int16" and not (r16["x_in"] == 0).any()
                and sep_dsv.tolist() == sep_ml.tolist() == [5, 15, 25] and r16["y_dsv"].size == 30
                and np.array_equal(r16["y_dsv"][others], r16["y_ml"][others]) and not np.isnan(r16["y_ml"]).any()
                and r16["xlim_dsv"] == (-0.5, 0.5) and list(r16["xlim_ml"]) == [-1, 1]
                and r16["maxall"] == 110.0 and ym16 == 115.5 and ym16_int == 116
                and r16["ylim_dsv"] == (-150.0, 150.0) and list(r16["ylim_ml"]) == [-150, 150]
                and tuple(r16["auto_dsv"]) == (-150.0, 150.0) and r16["auto_ml"].tolist() == [-150.0, 150.0] and ym16_int < 150)
    else:
        ok16 = False
    check(ok16, f"已知差異：int16 輸入（int16_input，24 點、n＝8）——MATLAB 的 YData 是 int16，3 個 NaN 分隔變成 0（位置 {sep_ml.tolist() if r16 else '?'}；"
                f"輸入沒有 0，其餘 27 點完全相等、XData 30 點含 NaN 完全相等）而 DSV 是 NaN；MATLAB 的 XLim 是 {list(r16['xlim_ml']) if r16 else '?'}"
                f"（axis 向量和 int16 的 YLim 併在一起變 int16、±0.5 進位）而 DSV 是 {r16['xlim_dsv'] if r16 else '?'}；"
                f"YLim 兩邊都是 {r16['ylim_dsv'] if r16 else '?'}（MATLAB 的 1.05·max|x| 也是 int16 運算：1.05·{r16['maxall'] if r16 else '?'} = {ym16 if r16 else '?'} → "
                f"int16 {ym16_int if r16 else '?'}，被自動範圍 ±150 蓋過所以看不出取整；若 max|x| = 143 會是 int16(150.15) = 150 vs DSV 150.15，推論、未實測）")
    # reuse 群組：同一個 figure handle 畫實數（step1）→ 複數（step2）→ 實數（step3）；只驗線資料與範圍和單獨畫（real_defaults／complex_defaults）相同
    bad_reuse = []
    for step, src in (("step1", "real_defaults"), ("step2", "complex_defaults"), ("step3", "real_defaults")):
        fig = R["reuse"][step]
        axes = fig["axes"] if isinstance(fig["axes"], list) else [fig["axes"]]
        res = results[src]
        if res["ncol"] != len(axes):
            bad_reuse.append(f"{step}: {res['ncol']} 欄 vs {len(axes)} 個 axes")
            continue
        for i, ax in enumerate(axes):
            ln = ax["lines"] if isinstance(ax["lines"], dict) else ax["lines"][0]
            if not tally(same(res["t"], arr(ln["XData"])) and same(res["Y"][:, i], arr(ln["YData"])) and same(res["xlim"], ax["xlim"])
                         and same(res["ylim"], ax["ylim"]) and ax["title"] == axes_meta(res["ncol"])[i]["title"]):
                bad_reuse.append(f"{step}[{i}] vs {src}")
    check(not bad_reuse, "eye_ref.json reuse（同一 figure 畫實數→複數→實數，3 步、4 個 axes）：線資料／XLim／YLim／title 和單獨畫完全相等；"
                         "figure 重用本身（clf 重畫、Tag 檢查、invalidHandle2 錯誤／invalidHandle3 警告）沒有 DSV 對應物，不比"
          + (f"（不一致：{bad_reuse}）" if bad_reuse else ""))
    # 斜坡掃描：x = 1..L，n ∈ {2..8,10,12,16}、每個 offset、L = 2..2n+1 與 5n+3；同時量 trace_grid 公式 vs 折線 t
    S = json.load(open(os.path.join(d, "eye_sweep.json"), encoding="utf-8"))
    bad_sw = []
    nsw = 0
    worst_sw = (0.0, "", 0.0)
    for s in S:
        if s.get("err"):
            continue
        nsw += 1
        res = eye_traces(np.arange(1, s["L"] + 1, dtype=float), s["n"], 1.0, s["offset"])
        okx, ix, mx, rx = exact(res["t"], arr(s["XData"]))
        oky, iy, my, ry = exact(res["Y"][:, 0], arr(s["YData"]))
        okl = res["xlim"] == tuple(float(v) for v in s["XLim"])
        if not tally(okx and oky and okl):
            bad_sw.append(f"n={s['n']} off={s['offset']} L={s['L']}: " + ("" if okx else f"X@{ix} {mx} vs {rx} ") + ("" if oky else f"Y@{iy} {my} vs {ry} ")
                          + ("" if okl else f"xlim {res['xlim']} vs {s['XLim']}"))
        dev, bnd = grid_dev(res, s["L"])
        if dev > worst_sw[0]:
            worst_sw = (dev, f"n={s['n']} off={s['offset']} L={s['L']}", bnd)
        if dev > bnd:
            bad_mat.append(f"sweep n={s['n']} off={s['offset']} L={s['L']}（Δt {dev:.2f} eps·period，上界 {bnd:.2f}）")
    check(not bad_sw, f"斜坡掃描 vs MATLAB（{nsw} 筆：XData／YData 逐點完全相等、XLim 相等）" + (f"（不一致 {len(bad_sw)}：{bad_sw[:3]}）" if bad_sw else ""))
    # 長訊號：k/n 的捨入誤差讓 trace_grid 公式和折線 t 的差隨 L/n 變大（DSV 的折線 t 和 MATLAB 逐位相同，所以 MATLAB 的折線也有同樣的差）
    long_res = eye_traces(np.sin(np.arange(1_000_000) * 0.3), 7, 1.0, 3)
    dev_long, bnd_long = grid_dev(long_res, 1_000_000)
    if dev_long > bnd_long:
        bad_mat.append(f"L=1e6 n=7（Δt {dev_long:.0f} eps·period，上界 {bnd_long:.0f}）")
    check(not bad_mat, f"trace_matrix（每條 trace 一列、n+1 點）和折線互相一致（{n_cases} 案例＋{nsw} 筆掃描＋L＝1e6）；trace_grid 公式 vs 折線 t 的差 ≤ "
                       f"eps·period·(L/(2n)+3)：實測參考案例最大 {worst_grid[0]:.2f} eps·period（{worst_grid[1]}，上界 {worst_grid[2]:.2f}）、"
                       f"掃描最大 {worst_sw[0]:.2f}（{worst_sw[1]}，上界 {worst_sw[2]:.2f}）、L＝1e6／n＝7 {dev_long:.0f}（上界 {bnd_long:.0f}）"
          + (f"（不一致：{bad_mat[:3]}）" if bad_mat else ""))
    # eye_ylim.json：MATLAB 自動範圍 → eyediagram YLim 的合成規則；全部 44 筆的資料從 eye_inputs.txt 重建，比自動範圍與 maxAll
    Yl = json.load(open(os.path.join(d, "eye_ylim.json"), encoding="utf-8"))
    old_in = load_old_inputs(os.path.join(d, "eye_inputs.txt"))
    bad_rule, bad_old, bad_tick, const_ticks, int8_note = [], [], [], [], ""
    nrule = n_old_axes = n_old_cases = n_ticks = 0
    old_groups = set()
    snap_name = "complex_zero_imag"
    meta_ok = all(e["match"] is True for e in Yl) and len(Yl) == 44           # eye_ylim.m 自己的一致性欄位：match 全 true、YLimitMethod 全 tickaligned
    for e in Yl:
        au = e["auto"] if isinstance(e["auto"], list) else [e["auto"]]
        meta_ok = meta_ok and all(a["YLimitMethod"] == "tickaligned" for a in au)
        lo = min(float(a["YLim"][0]) for a in au)
        hi = max(float(a["YLim"][1]) for a in au)
        got = ylim_rule(e["maxAll"], lo, hi)
        if e["name"] == "int_types_n_offset":
            # 舊參考這筆 eyediagram 回報的 YLim 是 single（axis 向量裡混了 single 的 period）：存的 1.67040586 正好是 double 結果 1.6704058318525692
            # 轉 single 後印 9 位有效數字（double 本身印 9 位是 1.67040583，不同）；predicted 是 eye_ylim.m 用 double 算的同一條規則，必須逐位相同
            s9 = [float(f"{np.float32(v):.9g}") for v in got]
            int8_note = (f"整數類別參數那筆 MATLAB 的 YLim 是 single（{e['eyediagram'][1]}）＝DSV 的 {got[1]!r} 轉 single 印 9 位有效數字"
                         f"（double 印 9 位是 {got[1]:.9g}），且和 predicted {e['predicted'][1]!r} 逐位相同")
            if not tally(same(got, e["predicted"]) and s9 == [float(v) for v in e["eyediagram"]] and f"{got[1]:.9g}" != f"{np.float32(got[1]):.9g}"):
                bad_rule.append(f"{e['name']}: {got} vs predicted {e['predicted']}、single {e['eyediagram']}（{s9}）")
        else:
            nrule += 1
            if not tally(same(got, e["eyediagram"]) and same(got, e["predicted"])):
                bad_rule.append(f"{e['name']}: {got} vs {e['eyediagram']}（predicted {e['predicted']}）")
        cols = as_columns(old_in[e["name"]])                               # 自動範圍只看每欄的 min／max，n／period／offset 不影響
        n_old_cases += 1
        old_groups.add(e["name"].split("_")[0])
        if cols.shape[1] != len(au):
            bad_old.append(f"{e['name']}: {cols.shape[1]} 欄 vs {len(au)} 個 axes")
            continue
        if not tally(float(np.max(np.abs(cols))) == float(e["maxAll"])):
            bad_old.append(f"{e['name']}: maxAll {float(np.max(np.abs(cols)))!r} vs {e['maxAll']!r}")
        for i, a in enumerate(au):
            if e["name"] == snap_name and i == 0:
                continue                                                 # 「貼齊資料」例外：下面的已知差異檢查釘住數字
            n_old_axes += 1
            lo_i, hi_i = float(cols[:, i].min()), float(cols[:, i].max())
            mine = auto_limits(lo_i, hi_i)
            if not tally(same(mine, a["YLim"])):
                bad_old.append(f"{e['name']}[{i}]: 資料 [{lo_i:.6g}, {hi_i:.6g}] → {mine} vs {a['YLim']}")
            if lo_i == hi_i:                                             # 常數資料：MATLAB 的刻度規則判定不了，下面的已知差異檢查釘住數字
                const_ticks.append((e["name"], i, a["YTick"], auto_ticks(lo_i, hi_i).tolist()))
                continue
            n_ticks += 1
            if not tally(same(auto_ticks(lo_i, hi_i), a["YTick"])):
                bad_tick.append(f"{e['name']}[{i}]: {auto_ticks(lo_i, hi_i).tolist()} vs {a['YTick']}")
    check(not bad_rule and meta_ok, f"y 範圍合成規則 vs eyediagram（舊參考 eye_ylim.json {nrule} 筆，BPSK／QPSK／DC／斜坡）：和 eyediagram 的 YLim 與 "
                                    f"eye_ylim.m 的 predicted 都完全相等；{int8_note}；參考資料自我一致：{len(Yl)} 筆 match 全 true、YLimitMethod 全 tickaligned"
          + (f"（不一致：{bad_rule[:3]}）" if bad_rule else "") + ("" if meta_ok else "（match／YLimitMethod 欄位不一致）"))
    check(not bad_old, f"tick 對齊自動範圍 vs MATLAB（舊參考全部 {n_old_cases} 案例、{n_old_axes} 個 axes 的資料從 eye_inputs.txt 重建："
                       f"{'／'.join(sorted(old_groups))}；斜坡 [1,8]→[1,8]、[1,11]→[1,11]、[1,14]→[0,14]、[1,23]→[0,25]、[1,26]→[0,30]、"
                       f"DC [0.0791,3.22]→[0,3.5]、虛部全 0 → [−1,1]）：完全相等；maxAll 44 筆完全相等" + (f"（不一致：{bad_old[:3]}）" if bad_old else ""))
    check(not bad_tick, f"自動範圍的刻度值 auto_ticks = linspace(下限, 上限, 格數+1) vs MATLAB 自動 axes 的 YTick（舊參考 {n_ticks} 個 axes，step 0.5／1／2／5／0.2；"
                        f"len_lt_n 的 −0.4:0.2:1 是唯一能分辨公式的：MATLAB 給 −0.20000000000000004／−5.55e-17／0.19999999999999996，a + k·step 與 k·step 都不符）："
                        f"完全相等（含浮點最後位）" + (f"（不一致：{bad_tick[:3]}）" if bad_tick else ""))
    # 已知差異：常數資料的自動刻度——唯一一例（184 px 的 subplot）MATLAB 給 5 個刻度，≤ 11 規則會給 11 個；一例分不出原因，auto_ticks 只回端點
    ct = const_ticks[0] if len(const_ticks) == 1 else None
    f11, f10 = auto_fit(-1.0, 1.0, 11), auto_fit(-1.0, 1.0, 10)
    ticks10 = np.linspace(f10[0], f10[1], f10[3] + 1).tolist()
    ok_ct = (ct is not None and ct[0] == snap_name and ct[1] == 1 and ct[2] == [-1, -0.5, 0, 0.5, 1] and ct[3] == [-1.0, 1.0]
             and f11 == (-1.0, 1.0, 0.2, 10) and f10 == (-1.0, 1.0, 0.5, 4) and ticks10 == ct[2])
    tally(False)
    check(ok_ct, f"已知差異：常數資料的自動刻度——舊 complex_zero_imag 正交欄（虛部全 0、184 px 高的 subplot）MATLAB 範圍 [−1, 1]、YTick "
                 f"{ct[2] if ct else const_ticks}（5 個、step 0.5）；DSV 範圍相同，但 ≤ 11 個刻度的規則對 [−1, 1] 會選 step {f11[2]}（{f11[3] + 1} 個），"
                 f"max_ticks = 10 才得到同樣的 5 個 {ticks10}；一例分不出「184 px 的預算 < 11」和「常數資料另有規則」，"
                 f"所以 auto_ticks 對常數資料只回傳端點 {ct[3] if ct else ''}（刻度規則未實作）")
    # 已知差異：MATLAB 自動範圍的「貼齊資料」例外（門檻未知，未實作）——釘住 MATLAB 與 DSV 兩邊的確切數字，讓差異看得見
    snap = [e for e in Yl if e["name"] == snap_name]
    if snap:
        e = snap[0]
        au = e["auto"][0]["YLim"]
        cols = as_columns(old_in[snap_name])
        lo, hi = float(cols[:, 0].min()), float(cols[:, 0].max())
        mine = auto_limits(lo, hi)
        final_matlab = ylim_rule(e["maxAll"], min(au[0], -1.0), max(au[1], 1.0))          # 第二個 axes（虛部全 0）是 [−1, 1]
        final_mine = ylim_rule(e["maxAll"], min(mine[0], -1.0), max(mine[1], 1.0))
        au_t, mine_t = e["auto"][0]["YTick"], auto_ticks(lo, hi).tolist()
        ok_snap = (lo == -1.5908626970024469 and hi == 1.0006655482642264 and au == [-2, 1.0006655482642264] and mine == (-2.0, 1.5)
                   and final_matlab == final_mine == tuple(e["eyediagram"]) == (-2.0, 1.6704058318525692)
                   and au_t == [-2, -1.5, -1, -0.5, 0, 0.5, 1] and mine_t == [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5]
                   and np.linspace(-2.0, 1.0, 7).tolist() == au_t)                         # 拿 MATLAB 自己的範圍套 linspace 也等於它的刻度
        tally(False)
        check(ok_snap, f"已知差異：MATLAB 自動範圍「貼齊資料」例外——舊 complex_zero_imag 同相欄資料 [{lo!r}, {hi!r}]，MATLAB 自動範圍 {au}"
                       f"（上限停在資料值，只超過刻度 1.0 的 0.13% step；刻度 {au_t} = linspace(−2, 1, 7)），DSV 純 tick 對齊給 {mine}（刻度 {mine_t}）；"
                       f"門檻無法從資料判定（0.13% 貼齊、7.55% 進位之間），未實作。eyediagram 最後的 YLim 兩邊都是 {final_mine}（1.05·max|x| 蓋過），顯示不受影響")
    # 單一樣本：舊參考 len_1 有輸入檔但 MATLAB 沒有結果（eyediagram 出錯，訊息沒留下來）；DSV 丟 SingleSample
    x1 = old_in["len_1"]
    try:
        eye_traces(x1, 8)
        ok_one, msg_one = False, "沒有錯誤"
    except EyeDiagramError as ex:
        ok_one, msg_one = ex.identifier == "dsv:eyediagram:SingleSample" and bool(ex.zh), f"{ex.identifier}: {ex}"
    try:
        eye_traces(np.array([[0.5 + 0.25j]]), 8)
        ok_one = False
    except EyeDiagramError as ex:
        ok_one = ok_one and ex.identifier == "dsv:eyediagram:SingleSample"
    check(ok_one and "len_1" not in {e["name"] for e in Yl} and x1.shape == (1, 1),
          f"單一樣本（舊參考 len_1 = {x1.ravel().tolist()}；MATLAB 出錯、eye_ylim.json 沒有它）→ DSV {msg_one}；複數單一樣本也一樣；"
          f"L = 2 起才有折線（xlim 才不會是 [0, 0]）")
    # 純量參數：MATLAB 的 8 和 [8] 一樣（isscalar）；一元素陣列／numpy 純量都接受，多元素才是錯
    xr = load_input(os.path.join(d, "inputs/real_defaults.txt"))
    try:
        ok_sc = (validate_args(np.array([8])) == (8, 1.0, 0) and validate_args(np.int8(8), np.array([[2.0]]), np.float32(3)) == (8, 2.0, 3)
                 and validate_args([8], (0.5,), np.array([3])) == (8, 0.5, 3))
        r1, r2 = eye_traces(xr, np.array([8]), np.array([1.0]), [0]), results["real_defaults"]
        ok_sc = ok_sc and same(r1["t"], r2["t"]) and same(r1["Y"], r2["Y"]) and r1["ylim"] == r2["ylim"]
        for bad_n in ([8, 8], np.array([[8], [8]]), "8", None):
            try:
                validate_args(bad_n)
                ok_sc = False
            except EyeDiagramError as ex:
                ok_sc = ok_sc and ex.identifier == "comm:eyediagram:InvalidN"
    except EyeDiagramError as ex:
        ok_sc = False
        print("  純量參數：", ex.identifier, ex)
    check(ok_sc, "純量參數照 MATLAB isscalar：n／period／offset 接受一元素陣列（[8]、[[2.0]]、(0.5,)）與 numpy 純量（int8、float32），"
                 "結果和純 Python 數字完全相同；[8 8]、2×1、字串、None → InvalidN")
    # auto_limits 的契約：包住資料（最多差 SNAP_ULP ulp）、下限 < 上限、至少一格、刻度數 ≤ 11；第二輪審查的 4 個近常數反例 + 十進位刻度 + 亂數
    rng_ = np.random.default_rng(20261024)
    pairs = [(1.0, 1.0 + 1.5e-12), (0.1, 0.1 + 1e-13), (100.0, 100.0 + 2e-10), (1e6, 1e6 + 3e-6),           # 審查反例（以前顛倒／包不住）
             (0.3, 0.9), (0.3, 0.7), (-0.3, 0.3), (0.1, 0.3), (-1.1, -0.2), (0.0, 0.9), (1.0, 1.0 + EPS), (0.3, 0.3 + 5.5e-17),
             (-5e-324, 5e-324), (1e-300, 3e-300), (1e15, 1e15 + 7.0), (-2.5e-7, 1e-9),
             (0.0, 0.0), (5.0, 5.0), (7.9e218, 7.9e218), (2.0 ** 53, 2.0 ** 53), (-2.0 ** 60, -2.0 ** 60), (1e20, 1e20 + 2e4)]   # 常數：c±1 == c 時也不能塌
    rmax = sys.float_info.max                                                 # Python float：溢位成 inf 不會像 numpy 純量那樣發 RuntimeWarning
    urm = math.ulp(rmax)
    pairs += [(rmax, rmax), (-rmax, -rmax), (rmax - 60 * urm, rmax - 60 * urm), (rmax - 64 * urm, rmax - 64 * urm),        # 第三輪：常數在 realmax 附近
              (rmax - 10 * urm, rmax), (-rmax, -rmax + 10 * urm), (0.9 * rmax, rmax), (-rmax, rmax), (-rmax, 0.0), (rmax - 1e300, rmax)]
    for _ in range(3000):
        mag = 10.0 ** rng_.uniform(-12, 12)
        lo_ = rng_.uniform(-1, 1) * mag
        span = mag * 10.0 ** rng_.uniform(-15, 1)
        pairs.append((lo_, lo_ + span))
    for _ in range(500):                                                      # 十進位「剛好在刻度上」的資料
        step_ = [1.0, 2.0, 5.0][rng_.integers(3)] * 10.0 ** rng_.integers(-6, 6)
        k0 = int(rng_.integers(-50, 50))
        pairs.append((k0 * step_, (k0 + int(rng_.integers(1, 10))) * step_))
    n_reg = len(pairs)
    pairs.append((1.242805512410504e-30, 1.2428055124105257e-30))             # 第二輪審查的例子：以前界限進資料 11 ulp（step 2e-45 ≈ 7 ulp）
    for mag in (1e-30, 1e30, 1e-300, 3e300, 1e-310, 7e-30):                   # 極端量級、範圍只有 33～400 ulp：10^e 不精確、step 只有幾個 ulp
        for _ in range(60):
            lo_ = float(mag * (1.0 + rng_.uniform(-0.5, 0.5)))
            pairs.append((lo_, lo_ + int(rng_.integers(33, 400)) * math.ulp(lo_)))
    bad_c = []
    examples = {}
    worst_in = (0.0, None)                                                    # 界限進到資料裡最多幾個 eps·|x|（契約的單位；≤ SNAP_ULP 才對）
    for lo_, hi_ in pairs:
        a_, b_, st_, ni_ = auto_fit(lo_, hi_)
        if ni_ >= 1:                                                          # 有格點：容差 = snap_tol（≤ 16 ulp 且 ≤ step/4），上限 = 下限 + 格數·step
            tol_lo, tol_hi = snap_tol(lo_, a_, st_), snap_tol(hi_, b_, st_)
            tk = auto_ticks(lo_, hi_)
            ok_ = (a_ <= lo_ + tol_lo and b_ >= hi_ - tol_hi and ni_ + 1 <= MAX_TICKS and b_ == a_ + ni_ * st_
                   and tk.size == ni_ + 1 and tk[0] == a_ and tk[-1] == b_)
        else:                                                                 # 常數／溢位：沒有格點，必須正好包住
            ok_ = a_ <= lo_ and b_ >= hi_
        if not (math.isfinite(a_) and math.isfinite(b_) and a_ < b_ and ok_):
            bad_c.append(f"[{lo_!r}, {hi_!r}] → ({a_!r}, {b_!r}, step {st_!r})")
        if (lo_, hi_) in ((1.0, 1.0 + 1.5e-12), (1e6, 1e6 + 3e-6), (0.3, 0.9), (-0.3, 0.3), (1.242805512410504e-30, 1.2428055124105257e-30)):
            examples[(lo_, hi_)] = (a_, b_)
        u_ = max(EPS * max(abs(lo_), abs(hi_)), math.ulp(max(abs(lo_), abs(hi_))))   # 契約的單位 eps·|x|（次正規時用 ulp；np.spacing(realmax) 會溢位）
        inside = max((a_ - lo_) / u_, (hi_ - b_) / u_)
        if inside > worst_in[0]:
            worst_in = (inside, (lo_, hi_, a_, b_, st_))
    check(not bad_c and worst_in[0] <= SNAP_ULP,
          f"auto_limits 契約（{len(pairs)} 組：審查的 4 個近常數反例、realmax 附近 10 組（常數 ±realmax、realmax − 60／64 ulp、近常數、±realmax 全幅）、"
          f"十進位刻度上的資料 500 組、亂數 3000 組（量級 1e-12～1e12、範圍 1e-15～10 倍）、"
          f"極端量級 {len(pairs) - n_reg} 組（|x| ≈ 1e-30／1e30／1e-300／3e300／次正規 1e-310，範圍 33～400 ulp））：有限、下限 < 上限、"
          f"包住資料（最多差 snap_tol = min({SNAP_ULP} eps·|x|, step/{SNAP_STEP_DIV})）、上限 = 下限 + 格數·step、刻度數 ≤ {MAX_TICKS}、"
          f"auto_ticks 兩端 = 範圍；界限進資料最多 {worst_in[0]:.2f} eps·|x|（{worst_in[1]}）；例：{ {k: v for k, v in examples.items()} }"
          + (f"（違反 {len(bad_c)}：{bad_c[:3]}）" if bad_c else ""))
    # NaN／±Inf：只看有限值（刻意和 MATLAB 的 max(abs(x)) = Inf 不同，見「未定／自行決定」）；Y 裡的值原樣保留
    xi = np.array([1.0, np.inf, 3.0, -9.0] * 4)
    ri = eye_traces(xi, 4)
    xn = np.array([1.0, np.nan, 3.0, -9.0] * 4)
    rn = eye_traces(xn, 4)
    ok_inf = (ri["maxall"] == 9.0 and ri["ylim"] == (-10.0, 9.450000000000001) and tuple(ri["auto_ylim"][0]) == (-10.0, 4.0)
              and np.isposinf(ri["Y"][:, 0]).sum() == 4 and rn["maxall"] == 9.0 and rn["ylim"] == ri["ylim"]
              and np.isnan(rn["Y"][:, 0]).sum() == 4 + (rn["ntraces"] - 1) and all(math.isfinite(v) for v in ri["xlim"] + ri["ylim"]))
    try:
        ra = eye_traces(np.array([np.nan, np.inf, -np.inf, np.nan]), 2)
        ok_inf = ok_inf and ra["ylim"] == (-1.0, 1.0) and math.isnan(ra["maxall"])
    except (EyeDiagramError, FloatingPointError) as ex:
        ok_inf, ra = False, {"ylim": f"例外 {ex}"}
    check(ok_inf, f"NaN／±Inf：[1, Inf, 3, −9]×4 → maxall {ri['maxall']}、auto {ri['auto_ylim'][0].tolist()}、ylim {ri['ylim']}、Y 保留 4 個 Inf"
                  f"（刻意不同：MATLAB 的 max(abs(x)) 會是 Inf → YLim [−Inf, Inf]，axis／ylim 文件說 ±Inf 是「該邊自動」，所以 MATLAB 最可能顯示"
                  f"有限資料的自動範圍 {ri['auto_ylim'][0].tolist()}、不套 1.05 倍；MATLAB 端未實測）；NaN 版本同樣的範圍（MATLAB 的 max 也略過 NaN）；"
                  f"全部非有限 → ylim {ra['ylim']}、maxall NaN")
    # 極大的值：hi − lo、格數·step、1.05·max|x| 溢位時不丟 OverflowError，範圍保持有限且包住資料（MATLAB 未驗證，見「未定／自行決定」）
    try:
        big = eye_traces(np.array([1e308, -1e308] * 8), 4)             # hi − lo 溢位；1.05·1e308 = 1.05e308 還是有限
        big2 = eye_traces(np.array([1.75e308, -1.75e308] * 8), 4)      # 1.05·1.75e308 > realmax → 改用 max|x|
        a1 = auto_limits(-8.9e307, 8.9e307)                            # 2e307 × 10 格 → 上限溢位
        a2 = auto_limits(-1e308, 1e308)                                # hi − lo 溢位
        a3 = auto_limits(0.0, 5e-324)                                  # 次正規：10^e 下溢成 0
        # 第三輪：常數資料離 realmax 不到 64 ulp（pad 溢位）——以前 ylim／auto_limits／auto_ticks 回 inf
        c60, c64 = rmax - 60 * urm, rmax - 64 * urm                      # 審查量到的門檻：c + pad 在 realmax − 60 ulp 還溢位、− 64 ulp 就不溢位
        cst = eye_traces(np.array([rmax] * 4), 2)
        cst_neg = eye_traces(np.array([-rmax] * 4), 2)
        a4, a5, a6, a7 = auto_limits(rmax, rmax), auto_limits(-rmax, -rmax), auto_limits(c60, c60), auto_limits(c64, c64)
        t4 = auto_ticks(rmax, rmax)
        vals = [*big["ylim"], *big["xlim"], *big["auto_ylim"].ravel(), *big2["ylim"], *big2["auto_ylim"].ravel(), *a1, *a2, *a3,
                *cst["ylim"], *cst_neg["ylim"], *cst["auto_ylim"].ravel(), *a4, *a5, *a6, *a7, *t4]
        ok_big = (all(math.isfinite(v) for v in vals) and big["ylim"] == (-1.05e308, 1.05e308) and big2["ylim"] == (-1.75e308, 1.75e308)
                  and a1 == (-8.9e307, 8.9e307) and a2 == (-1e308, 1e308) and a3[0] <= 0.0 < 5e-324 <= a3[1]
                  and ylim_rule(1.75e308, -1.0, 1.0) == (-1.75e308, 1.75e308)
                  and cst["ylim"] == cst_neg["ylim"] == (-rmax, rmax) and cst["maxall"] == rmax
                  and a4 == (c64, rmax) and a5 == (-rmax, -c64) and a6[0] < c60 == a6[1] and a7[0] < c64 and a7[1] == rmax
                  and not math.isfinite(c60 + 32 * EPS * c60) and c64 + 32 * EPS * c64 == rmax         # 門檻本身：60 ulp 溢位、64 ulp 剛好不
                  and t4.tolist() == [c64, rmax] and 63.9 < 32 * EPS * rmax / urm < 64.0)              # pad = 32·eps·realmax ≈ 64 ulp
        msg = (f"±1e308 → ylim {big['ylim']}、±1.75e308 → ylim {big2['ylim']}、auto_limits(±8.9e307) → {a1}、(±1e308) → {a2}、(0, 5e-324) → {a3}；"
               f"常數 realmax → ylim {cst['ylim']}、auto_limits(realmax, realmax) → {a4}（= [realmax − 64 ulp, realmax]，pad 溢位的那端用 c）、"
               f"(−realmax) → {a5}、realmax − 60 ulp → 上限 = c 本身 {a6[1]!r}、realmax − 64 ulp → 上限 = realmax（pad 剛好不溢位）、"
               f"auto_ticks(realmax) → {t4.tolist()}")
    except (OverflowError, ZeroDivisionError, ValueError) as ex:
        ok_big, msg = False, f"例外 {type(ex).__name__}: {ex}"
    check(ok_big, f"極大／極小的值不丟 OverflowError、範圍有限且包住資料（溢位時退回資料範圍、常數的 pad 溢位時用資料值、1.05 倍改用 max|x|）：{msg}")
    # ylim_rule 自己擋非有限的引數（第三輪：以前 ylim_rule(inf, −1, 1) 回 (−inf, inf)、(nan, −1, 1) 回 (nan, nan)）
    yr = {(math.inf, -1.0, 1.0): (-1.0, 1.0), (math.nan, -1.0, 1.0): (-1.0, 1.0), (-math.inf, -2.0, 3.0): (-2.0, 3.0),
          (9.0, math.nan, math.nan): (-9.450000000000001, 9.450000000000001), (9.0, -math.inf, math.inf): (-9.450000000000001, 9.450000000000001),
          (9.0, -10.0, math.inf): (-10.0, 9.450000000000001), (math.nan, math.nan, math.inf): (-1.0, 1.0), (rmax, -1.0, 1.0): (-rmax, rmax),
          (0.0, -1.0, 1.0): (-1.0, 1.0), (2.0, -1.0, 1.0): (-2.1, 2.1)}
    bad_yr = [(k, ylim_rule(*k)) for k, v in yr.items() if ylim_rule(*k) != v]
    check(not bad_yr, f"ylim_rule 回傳一定有限：maxall 非有限（Inf／NaN）→ 只回自動範圍、自動範圍非有限的那邊只用 ±1.05·max|x|、全非有限 → (−1, 1)、"
                      f"maxall = realmax → ±realmax；{len(yr)} 組" + (f"（不一致：{bad_yr}）" if bad_yr else ""))
    # 錯誤訊息：MATLAB 識別碼與訊息 → EyeDiagramError
    E = {e["name"]: e for e in R["errors"]}
    trials = {"empty_x": lambda: eye_traces([], 8), "n_equal_1": lambda: eye_traces(xr, 1), "n_noninteger": lambda: eye_traces(xr, 2.5),
              "n_vector": lambda: eye_traces(xr, [8, 8]), "period_zero": lambda: eye_traces(xr, 8, 0), "period_negative": lambda: eye_traces(xr, 8, -1),
              "offset_eq_n": lambda: eye_traces(xr, 8, 1, 8), "offset_negative": lambda: eye_traces(xr, 8, 1, -1), "offset_frac": lambda: eye_traces(xr, 8, 1, 0.5),
              "three_columns": lambda: eye_traces(np.column_stack([xr, xr, xr]), 8)}
    bad_err = []
    for name, fn in trials.items():
        try:
            fn()
            tally(False)
            bad_err.append(f"{name}: 沒有錯誤")
        except EyeDiagramError as ex:
            if not tally(ex.identifier == E[name]["id"] and str(ex) == E[name]["msg"] and bool(ex.zh)):
                bad_err.append(f"{name}: {ex.identifier} '{ex}' vs {E[name]['id']} '{E[name]['msg']}'")
    try:
        eye_traces(xr)                                                  # type: ignore[call-arg]
        tally(False)
        bad_err.append("too_few_args: 沒有錯誤")
    except TypeError:
        tally(True)
    try:
        eye_traces(xr.astype(complex).reshape(-1, 1).repeat(2, axis=1), 8)   # 複數兩欄 → [Re Im] 四欄
        bad_err.append("complex_two_columns: 沒有錯誤")
    except EyeDiagramError as ex:
        if ex.identifier != "comm:eyediagram:invalidSizeX":
            bad_err.append(f"complex_two_columns: {ex.identifier}")
    # DSV 自訂：非數值輸入 → NonNumericX（不是 numpy 的裸 ValueError／TypeError，也不悄悄把 None 變 NaN）；bool 當 0／1
    non_numeric = {"字串": "abc", "字串 list": ["1", "2", "3"], "含 None": [1, None, 3], "dict": {"a": 1}, "不規則巢狀": [[1, 2], [3]],
                   "datetime64": np.array(["2026-10-24", "2026-10-25"], dtype="datetime64[D]"), "object 陣列": np.array([1, 2, 3], dtype=object)}
    for name, bad_x in non_numeric.items():
        try:
            eye_traces(bad_x, 2)
            bad_err.append(f"{name}: 沒有錯誤")
        except EyeDiagramError as ex:
            if ex.identifier != "dsv:eyediagram:NonNumericX" or not ex.zh:
                bad_err.append(f"{name}: {ex.identifier}")
        except Exception as ex:                                         # noqa: BLE001 —— 要抓的就是「不是 EyeDiagramError」
            bad_err.append(f"{name}: {type(ex).__name__} {ex}")
    rb = eye_traces(np.array([True, False, True, True]), 2)             # 折線 [1, 0, NaN, 0（重畫）, 1, 1]
    if not (same(rb["Y"][:, 0], [1.0, 0.0, np.nan, 0.0, 1.0, 1.0]) and rb["maxall"] == 1.0):
        bad_err.append(f"bool: {rb['Y'].ravel().tolist()}")
    # DSV 自訂：配置上限 2^24 → TooLarge（trace_grid 的 n+1、trace_matrix 的 ntraces × (n+1) × C）；差一個就還可以
    for name, fn in {"trace_grid(2^24)": lambda: trace_grid(MAX_ELEMENTS),
                     "trace_matrix 125000×134218": lambda: trace_matrix({"ntraces": 125_000, "n": 134_217, "ncol": 1, "period": 1.0,
                                                                        "col": np.zeros(1, np.int64), "seg": np.zeros(1, np.int64), "Y": np.zeros((1, 1))})}.items():
        try:
            fn()
            bad_err.append(f"{name}: 沒有錯誤")
        except EyeDiagramError as ex:
            if ex.identifier != "dsv:eyediagram:TooLarge" or str(MAX_ELEMENTS) not in str(ex) or not ex.zh:
                bad_err.append(f"{name}: {ex.identifier} '{ex}'")
    if trace_grid(MAX_ELEMENTS - 1).shape != (MAX_ELEMENTS,):
        bad_err.append("trace_grid(2^24 − 1) 應該可以")
    # DSV 自訂：n ≥ 2^53 → NTooLarge（第二輪審查：以前 n ≥ 2^63 從 np.mod 丟裸的 OverflowError、2**64 碰巧是 InvalidN）；2^53 − 2 還可以
    for bad_n in (1e19, 2.0 ** 63, 2.0 ** 63 - 1024, 2 ** 64, 2.0 ** 53, np.int64(2 ** 62), 1e300):
        try:
            eye_traces(xr, bad_n)
            bad_err.append(f"n={bad_n!r}: 沒有錯誤")
        except EyeDiagramError as ex:
            if ex.identifier != "dsv:eyediagram:NTooLarge" or "2^53" not in str(ex) or not ex.zh:
                bad_err.append(f"n={bad_n!r}: {ex.identifier} '{ex}'")
        except Exception as ex:                                         # noqa: BLE001 —— 要抓的就是裸的 OverflowError
            bad_err.append(f"n={bad_n!r}: {type(ex).__name__} {ex}")
    rn = eye_traces(np.arange(8.0), 2.0 ** 53 - 2)
    if not (rn["ntraces"] == 1 and rn["n"] == 2 ** 53 - 2 and rn["t"].size == 8 and math.isfinite(rn["xlim"][1])):
        bad_err.append(f"n = 2^53 − 2 應該可以：{rn['ntraces']} {rn['xlim']}")
    # trace_grid 用 validate_args 檢查（第二輪審查：以前 trace_grid(0) 裸 RuntimeWarning＋NaN、(1) 回 [−1, 0]、(−1) 回空陣列、'8' 被接受）
    for bad_n in (0, 1, -1, 2.5, "8", None, np.nan, np.inf, [8, 8]):
        try:
            trace_grid(bad_n)
            bad_err.append(f"trace_grid({bad_n!r}): 沒有錯誤")
        except EyeDiagramError as ex:
            if ex.identifier != "comm:eyediagram:InvalidN":
                bad_err.append(f"trace_grid({bad_n!r}): {ex.identifier}")
        except Exception as ex:                                         # noqa: BLE001
            bad_err.append(f"trace_grid({bad_n!r}): {type(ex).__name__} {ex}")
    for bad_p in (0, -1, np.nan, np.inf, [1, 2]):
        try:
            trace_grid(8, bad_p)
            bad_err.append(f"trace_grid(8, {bad_p!r}): 沒有錯誤")
        except EyeDiagramError as ex:
            if ex.identifier != "comm:eyediagram:NonPositivePeriod":
                bad_err.append(f"trace_grid(8, {bad_p!r}): {ex.identifier}")
    if not (same(trace_grid(8), (np.arange(9) - 4) / 8.0) and same(trace_grid(np.array([5]), np.float32(0.5)), (np.arange(6) - 3) / 5.0 * 0.5)):
        bad_err.append(f"trace_grid(8)／(5, 0.5) 的值：{trace_grid(8).tolist()} {trace_grid(5, 0.5).tolist()}")
    # DSV 自訂：period 下溢（×period 之後所有時間值相同）→ PeriodUnderflow；1e-323 還有兩個不同值（但已量化成 5e-324 的倍數）
    for args_ in ((np.arange(8.0), 4, 5e-324), (np.arange(2.0), 2, 5e-324)):
        try:
            eye_traces(*args_)
            bad_err.append(f"period {args_[2]!r}: 沒有錯誤")
        except EyeDiagramError as ex:
            if ex.identifier != "dsv:eyediagram:PeriodUnderflow" or not ex.zh:
                bad_err.append(f"period {args_[2]!r}: {ex.identifier}")
    ru = eye_traces(np.arange(8.0), 4, 1e-323)
    if ru["xlim"] != (-5e-324, 5e-324):
        bad_err.append(f"period 1e-323: xlim {ru['xlim']}")
    skipped = [e["name"] for e in R["errors"] if e["name"] not in trials and e["name"] != "too_few_args"]
    check(not bad_err, f"錯誤 vs MATLAB（{len(trials)} 筆：EmptyX、InvalidN×3、NonPositivePeriod×2、InvalidOffset×3、invalidSizeX；識別碼與英文訊息一致、"
                       f"附繁中；太少引數＝TypeError；figure handle 的 {skipped} 不適用）＋DSV 自訂：非數值輸入 {len(non_numeric)} 種 → "
                       f"dsv:eyediagram:NonNumericX、bool 當 0／1、配置超過 2^24 → dsv:eyediagram:TooLarge（trace_grid／trace_matrix）、"
                       f"n ≥ 2^53（1e19、2^63、2**64、1e300…7 種）→ dsv:eyediagram:NTooLarge 而 2^53−2 可以、trace_grid 的 n／period 9＋5 種壞值 → "
                       f"InvalidN／NonPositivePeriod（值照公式）、period 5e-324 → dsv:eyediagram:PeriodUnderflow 而 1e-323 → xlim {ru['xlim']}"
          + (f"（不一致：{bad_err}）" if bad_err else ""))
    # 維度：尾端單一維度 = MATLAB 的 L×1／1×L；真正 N 維照 [r, c] = size(x) 併欄（沒有 MATLAB 參考，見「未定／自行決定」）
    base = eye_traces(np.arange(8.0), 2)
    nd_ok = True
    for s in ((8, 1, 1), (1, 8, 1), (1, 1, 8), (8, 1, 1, 1), (1, 1, 1, 8)):
        rs = eye_traces(np.arange(8.0).reshape(s), 2)
        nd_ok = nd_ok and same(rs["t"], base["t"]) and same(rs["Y"], base["Y"]) and rs["ylim"] == base["ylim"]
    nd_ok = nd_ok and same(as_columns(np.arange(16.0).reshape(8, 1, 2)), np.arange(16.0).reshape(8, 2))
    nd_ok = nd_ok and as_columns(np.arange(8.0).reshape(1, 2, 4)).ravel().tolist() == [0, 4, 1, 5, 2, 6, 3, 7]
    for bad_x in (np.arange(8.0).reshape(2, 2, 2), np.arange(32.0).reshape(8, 2, 2), np.arange(16.0).reshape(8, 1, 2).astype(complex)):
        try:
            eye_traces(bad_x, 2)
            nd_ok = False
        except EyeDiagramError as ex:
            nd_ok = nd_ok and ex.identifier == "comm:eyediagram:invalidSizeX"
    check(nd_ok, "輸入維度（第二輪審查）：(8,1,1)／(1,8,1)／(1,1,8)／(8,1,1,1)／(1,1,1,8) 的 t／Y／ylim 和 1 維完全相同（MATLAB 尾端單一維度不存在、r = 1 攤成一欄）；"
                 "(8,1,2) 併成兩欄 = (8,2)；(1,2,4) 攤成欄優先順序 [0,4,1,5,2,6,3,7]；(2,2,2)／(8,2,2)／複數 (8,1,2) → invalidSizeX"
                 "（以前這些全部 invalidSizeX；真正 N 維的部分沒有 MATLAB 參考）")
    # 大資料：1e6 點、n＝8，向量化要夠快
    big = np.sin(np.arange(1_000_000) * 0.3) + 0.01 * np.arange(1_000_000) / 1e6
    t0 = _time.perf_counter()
    res = eye_traces(big, 8, 1.0, 3)
    tg, Y3 = trace_matrix(res)
    dt = _time.perf_counter() - t0
    check(res["t"].size == 1_000_000 + 2 * (res["ntraces"] - 1) and res["ntraces"] == 125_000 and Y3.shape == (125_000, 9, 1) and tg.shape == (9,)
          and dt < 2.0, f"眼圖：1e6 點、n＝8、offset 3 → {res['ntraces']} 條 trace、折線 {res['t'].size} 點、trace_matrix {Y3.shape}，{dt:.2f}s")
    # n 遠大於 L：eye_traces 只配置 O(L)（以前會配 n+1 個 tgrid，n＝1e7 就 80 MB）
    import tracemalloc
    was = tracemalloc.is_tracing()
    if not was:
        tracemalloc.start()
    tracemalloc.reset_peak()
    t0 = _time.perf_counter()
    res = eye_traces(np.arange(10.0), 10_000_000)
    dt = _time.perf_counter() - t0
    peak = tracemalloc.get_traced_memory()[1]
    if not was:
        tracemalloc.stop()
    biggest = max(v.size for v in res.values() if isinstance(v, np.ndarray))
    check(res["t"].size == 10 and res["ntraces"] == 1 and biggest <= 20 and peak < 1_000_000 and trace_grid(10_000_000).shape == (10_000_001,),
          f"n＝1e7、L＝10：eye_traces 最大陣列 {biggest} 個元素、峰值記憶體 {peak / 1e3:.0f} KB、{dt * 1e3:.1f} ms；trace_grid 才會配 n+1 點")
    # 統計：MATLAB 參考項目逐筆計數（折線／標籤 per axes、xlim／ylim per 案例、auto per axes、reuse per axes、掃描 per 筆、舊參考 rule／auto／maxAll／刻度、錯誤）
    known = 4                                                              # 已知差異：貼齊資料的自動範圍（1 axes）、常數資料的刻度（1 axes）、int16 的 YData（1 axes）與 XLim（1 案例）
    check(cnt[0] - cnt[1] == known, f"比對統計：MATLAB 參考項目共 {cnt[0]} 筆、相符 {cnt[1]} 筆、不符 {cnt[0] - cnt[1]} 筆（＝ {known} 筆已知差異：complex_zero_imag "
                                    f"同相欄的貼齊自動範圍、正交欄的常數刻度、int16_input 的 YData（NaN 分隔 vs 0）與 XLim（±0.5 vs ±1））；"
                                    f"內部一致性（trace_matrix、契約、維度、效能）另計，不在這個數字裡")
