# -*- coding: utf-8 -*-
"""訊號清理（MATLAB Signal Analyzer 的 PREPROCESS ▸ CLEAN：Smooth／Detrend）——純 numpy、向量化，和 GUI 分開。

定義照 MATLAB R2025a 的 smoothdata 與 detrend。Signal Analyzer 的 Smooth 面板輸出等於
smoothdata(x, method[, W][, "SmoothingFactor", f], "SamplePoints", t[, "Degree", d])，Detrend 面板等於 detrend(x, 0)／
detrend(x, 1)／detrend(x, 1, ix)（研究報告在 R2025a 的 Signal Analyzer 實測 166＋22 組，逐點相同）。
程式是自己寫的（行為照 MATLAB R2025a 的公開文件與實測輸出對照）；tests/matlab_ref/smooth_detrend/ 的 reference.json（研究報告）、
uniform_axis.json（第三輪審查者）、uniform_axis2.json／zero_weight.json／zero_weight2.json／error_ids.json（第四輪）是 MATLAB R2025a 算出的參考數值，
selftest() 逐筆比對；有同名 .m 的在該資料夾執行即可重產。補充參考資料 near_singular_ref.json 缺檔時 selftest 略過這一項。
這個工具沒有 Spectrum Analyzer 的實測擷取（scope_capture 只有 ACPR／失真／頻譜遮罩／OBW 四類），所以沒有 scope/ 參考資料。

時間軸：
- 樣本模式 t＝None → 取樣點 0..N−1、視窗以樣本數計（UI 只准正整數）。
- 時間模式 t＝t0 + n/fs（time_vector()；和 MATLAB 的 t0 + n/fs 逐位元相同）→ 視窗以秒計、不換算成樣本。
  t 是不是「完全等距」（max(Δt) == min(Δt) 浮點完全相等；is_exactly_uniform）決定結果照哪一種算法
  （這個分法和 MATLAB R2025a 的實測輸出一致）：
  - 不是 →「取樣點」路徑：視窗成員由時間決定，邊界剛好落在樣本上時由 t 的捨入決定（例如 100 Hz、0.08 s 的窗和「8 個樣本」有
    42/200 點不同）。
  - 是 → 結果等同把 W 換算成樣本 ws＝W/(t₂−t₁)、改在整數軸上算（DSV 稱「等距快速路徑」，見 smoothdata 第二點）。ws 是整數時結果和
    取樣點法則相同；ws 非整數且 fix(ws) 為偶數時不同。第一、二輪誤以為 t0 + n/fs 永遠不是完全等距、永遠走取樣點路徑——不對。
  - 哪些 DSV 時間軸完全等距（第四輪用 MATLAB 實測 313 條，uniform_axis2.json；這是純 IEEE 的性質，DSV 和 MATLAB 的 t 逐位元相同所以判斷也相同）：
    dsv_preprocess 用的 time_vector(N, sps·符號率, x0/符號率) 在預設符號率 1e6（以及 2e6）下，N＝1000／65536、sps 1～64、offset 0／3／0.5
    沒有一條完全等距（全部走取樣點路徑）；(x0 + n/sps)/符號率 也一樣。符號率 1（以符號為單位的軸 x0 + n/sps）在 sps＝1／2／4／8／16／64 時
    全部完全等距，sps＝3／10 不是。fs＝1024、8192、2²⁰、4、0.5、1/3（t0＝100）也是；0.37+n/100、n/1000、n/8e6、n/1e6 不是；
    N＝2 只有一個 Δt，一定完全等距（N＝3 的 0.37+n/100 也剛好是）。

smoothdata：
- 視窗成員 S_i ＝ { j : t_j ≥ t_i − W/2 且 t_j − t_i < W/2 }（半開；整數 W 在樣本軸上就是奇數置中、偶數「前 W/2、後 W/2−1」）。
  邊界剛好落在樣本上時，MATLAB 的結果等同左邊用「t_j 和 t_i − W/2 比」、右邊用「差值 t_j − t_i 和 W/2 比」——兩種比法的捨入
  不同；用同一種比法比兩邊，0.08／0.18／0.36 s 這些 tie 案例會錯幾十點（_window_bounds；實測）。
  兩端只用存在的樣本（shrink）；movmean／movmedian／gaussian 直接在 S_i 上算。
- 等距快速路徑（t＝None，或 t 完全等距；gaussian 與局部迴歸）：ws＝W/(t₂−t₁)（同一個浮點除法），
  ws < 2 → 原樣傳回；否則窗長 L＝fix(ws)（截斷，不是四捨五入），在整數軸上用「整數窗 L 的取樣點法則」算：L 奇數置中、
  L 偶數「前 L/2、後 L/2−1」，兩端借窗同上。這和 ws 非整數的取樣點法則不同：取樣點法則的窗是 {|d| ≤ ws/2} 共 2·floor(ws/2)+1 點
  （對稱、奇數），fix(ws) 為奇數時兩者一樣，fix(ws) 為偶數時少了最後面那一點——gaussian、sgolay 全部點不同，lowess／loess
  只有兩端 L 點不同（內部對稱窗最遠點的 tricube 權重本來就是 0），movmean／movmedian 照取樣點法則（實測）、不受影響。
  - gaussian：有沒有 NaN 都走這條；L＝min(fix(ws), 2N)；σ＝ws/5 用「沒截斷的」ws（例如 ws＝8.5：8 個 tap −4..+3，σ＝1.7 個樣本）。
  - lowess／loess／rlowess／rloess／sgolay：只在沒有 NaN 要排除時走（有 NaN → 取樣點路徑、t 和 W 都不換算）；L＝min(fix(ws), N)；
    sgolay 的 Degree 檢查仍用取樣點法則的最大點數 wl（換算前的視窗點數），L 個點配 d ≥ L 的次數 → 內插（＝x）。
    穩健重擬合（5 次）不用 L：和 MATLAB 輸出一致的算法是用「沒截斷的 ws」在整數軸上照
    取樣點法則重擬合（_local_regression 的 w_robust）。
  - 參考：uniform_axis.json（審查者的 uniform_axis_probe.m，第四輪重跑一次逐位元相同）：t＝n/2、n、n/4 配 ws＝8.5／7.5 與 0.37 + n/100 配
    0.085 s，8 種方法全部一致。uniform_axis2.json（第四輪，427 組＋96 組短軸）：n/1024 上 ws＝1.5～450.5 共 18 種（偶數 fix 的分數窗
    2.5／4.2／4.5／4.8／6.3／8.5／10.3／20.5／150.5／250.5／450.5、ws<2、N<fix(ws)<2N、>2N）、0.25+n/4、0.375+n/8、100+3n（非 2 的冪次間隔）、
    含 NaN、複數、自動視窗、sgolay 次數上限、視窗 1e30／1e308、N＝2／3，全部一致（y 1e-12、winsz、警告、錯誤代號）。
  - ws＝W/Δt 溢位成 Inf（W＝1e308 配 Δt＝2⁻¹⁰）：第一次擬合 fix(Inf) 夾到 N 可算，但 rlowess／rloess 的穩健重擬合拿到 Inf 的窗，MATLAB 丟
    MATLAB:smoothdata:wrongWindowLength（實測），DSV 照丟；其他方法照常。
- 自動視窗（SmoothingFactor f，τ＝1−f）：
  - 完全等距（樣本模式）：a＝x−mean、P＝|FFT_{2N}(a)|²/(2N)（複數時 P[k] 與 P[2N−k] 平均）、取前 N 個、
    c＝cumsum(P/ΣP)、ρ＝第一個 c>τ 的 1-based 索引、k＝ceil(√((0.44294·2N/max(ρ−1,1))²+1))；τ＝0→N、τ＝1→1；找不到→1。
    W＝k·Δt。
  - 不完全等距（時間模式）：τ＝0→t_N−t_1；τ＝1→min(Δt)/2；否則把 x 用 pchip 內插到 linspace(t_1, t_N, N)，
    用上面的法則算出 k，W＝k·(t_N−t_1)/(N−1)。NaN 先用 pchip 補（fillmissing）。結果 0→realmin、Inf→realmax。
- movmean／movmedian：視窗內的平均／中位數；NaN 不算（整窗都是 NaN→NaN）；複數的中位數照 MATLAB 的排序
  （先 |z| 再 angle）取中間，偶數個取中間兩個的平均。
- gaussian：y_i＝Σ g_ij x_j／Σ g_ij，g＝exp(−(t_j−t_i)²/(2σ²))，σ＝W/5（等距快速路徑：窗改成 fix(ws) 個 tap、σ＝ws/5 個樣本，見上）。
- lowess／loess／rlowess／rloess／sgolay（局部迴歸）：
  - 次數：lowess／rlowess 1、loess／rloess 2、sgolay 預設 2（可給）。
  - 兩端不縮小而是「借窗」：iL＝最後一個 S_i 含樣本 0 的 i，i<iL 用 S_iL；iR＝第一個 S_i 含樣本 N−1 的 i，i>iR 用 S_iR；
    多項式仍在 t_i 評估。
  - 權重：lowess／loess 用 tricube w_j＝(1−(|t_j−t_i|/dmax)³)³，dmax＝max|t_j−t_i|（最遠那點權重 0）；sgolay 全 1。
  - 加權最小平方多項式（變數 t_j−t_i），y_i＝在 t_i 的擬合值（＝常數項）。非零權重少於「次數+1」時次數降為「非零權重數−1」。
    解法：每個視窗的設計矩陣用映到 [−1,1] 的 Chebyshev 基底、批次 Householder QR（numpy.linalg.qr）；中心點權重 ≥ 0.5 時
    取投影 (QQᵀb)_i／√w_i（次數 10＝窗−1 的內插案例精度到 1e-15），否則用係數在 d＝0 的值。
  - 窗內權重全 0 但不全是 NaN（中心是離群值、鄰點的穩健權重也是 0；或含 NaN 時非 NaN 的只剩 tricube 0 的兩端）：MATLAB 改用等權重擬合
    窗內所有非 NaN 的點（zero_weight.json 實測：rlowess 窗 5 在離群值 i＝170 回五點平均 3.4545；第三輪之前 DSV 回 0，uniform_axis2.json 的
    rlowess ws 4～5.5、rloess 6.3～9.5 因此差到 0.63）。tricube 的 dmax 取整個窗（含 NaN 的位置；zero_weight2.json 的端點／內部 NaN 45 組一致）。
  - rlowess／rloess：先做非穩健擬合，再做 5 次：r＝|x−y|、u＝min(r/(6·max(thr, median r)), 1)、thr＝max|x|·√eps、
    ρ＝(1−u²)²（NaN→0），用 tricube·ρ 重擬合，每次 r 都用最新的 y。
  - 所有窗都只有一點（2·min(Δt) > W）→ 原樣傳回。
- sgolay 的 Degree 檢查：wl＝max_i |S_i|；d ≥ wl 時：自動視窗→d＝wl−1（有給 Degree 就回 sgDegreeWarning）；
  指定視窗→有給 Degree 就錯 MATLAB:smoothdata:degreeTooLarge（Signal Analyzer 對話框的「次數太大」訊息），沒給就 d＝wl−1。

detrend：
- constant：x − mean(x)。linear：沒有斷點。piecewiselinear：斷點 → 0-based 樣本索引（樣本模式直接是樣本號；
  時間模式取最接近絕對時間的樣本 argmin_j |t_j − b|，超出範圍→第一／最後一個）。
- bp＝unique([0, bp])，多於 1 個時只留 0 ≤ bp < N−1（最後一個樣本或之後的斷點不算）。
  a＝n/(N−1)，迴歸矩陣 [max(a − bp_k/(N−1), 0) …, 1]，最小平方擬合後相減（連續的分段線性）。複數實虛部一起解。
- Polynomial：R2025a 的面板沒有這個選項（下拉選單沒有），
  所以不做，呼叫會丟 CleanError。
- app 不接受含 NaN／Inf 的訊號（check_finite()）、Detrend 不接受非均勻取樣（check_uniform()）；若 NaN 進到 detrend，
  MATLAB 沒加 'omitnan' → 全部變 NaN。

輸入檢查（全部丟 CleanError，不會冒出 numpy 自己的 ValueError／TypeError／RuntimeWarning）：
- 訊號 x：字串、物件、非數值 → badArray／InvalidFirstInput（下面的錯誤代號）；多於一個非單一維度（真正的二維）→ notVector；(N,1)／(1,N) 當成向量；
  bool／整數當成數值（轉 float）；複數訊號照 MATLAB 支援。smooth／auto_window 拒絕 ±Inf（dsv:smoothdata:infiniteInput，見「未定」）。
- 參數 window／factor／degree 必須是實數純量（字串、複數、多元素都拒絕；bool 只有 window／factor 當 0／1）；Degree 只有 sgolay 能給；
  斷點必須是實數向量；取樣點 t 必須是實數向量、同長度、有限、遞增、唯一，而且跨度 t_N − t_1 不溢位
  （dsv:smoothdata:samplePointsSpanOverflow／dsv:detrend:timeVectorSpanOverflow，否則視窗邊界 t ± W/2 與距離都是 Inf）。
- 錯誤代號（第四輪用 MATLAB R2025a 實測 43 種輸入，error_ids.json；英文訊息照 MATLAB）：視窗 0／負數／多元素 → invalidWinsize、NaN／Inf →
  needsFiniteWindows、複數 → noComplexWindows；SmoothingFactor 範圍外／NaN／字串／多元素 → invalidSmoothingFactor、複數 → noComplex；Degree
  負數／非整數／true／多元素 → negativeDegree、NaN／Inf → needsFinites、複數 → noComplex、配非 sgolay → degreeNoSgolay、太大 → degreeTooLarge；
  方法 → invalidMethod；SamplePoints 長度 → MATLAB:samplePoints:SamplePointsLength、NaN／Inf → SamplePointsNonFinite、遞減 → SamplePointsSorted、
  重複 → SamplePointsDuplicate、複數 → SamplePointsComplex、字串／bool／矩陣 → SamplePointsInvalidDatatype；非數值訊號 → MATLAB:smoothdata:badArray、
  detrend 的 MATLAB:detrend:InvalidFirstInput。視窗與 SmoothingFactor 的 true 當 1（MATLAB 可算）。第三輪之前有 9 個代號是猜的、和 MATLAB 不同。
  DSV 自己的決定（MATLAB 接受但 DSV 拒絕）：樣本模式的非整數窗（面板規則 smoothWindowDurationErrorSamples）、Inf 訊號（dsv:smoothdata:infiniteInput）、
  矩陣訊號（dsv:*:notVector）、兩元素 [kb kf] 視窗與字串視窗（invalidWinsize；MATLAB 把字串當 NaN 旗標 → invalidNanflag）、整數陣列的 SamplePoints
  （MATLAB 只收 double／single；DSV 照 float 用）。detrend 的時間軸檢查是 dsv:detrend:timeVector*（Signal Analyzer 的 Detrend 輸出和不帶時間軸的 detrend(x, …) 相同，實測 22 組）。
- 工作量上限（DSV 自訂，避免卡住；都在配置任何大陣列之前就拒絕，dsv:clean:tooMuchWork）：
  - movmedian／gaussian：所有視窗合計樣本數 Σ|S_i| > MAX_WINDOW_ELEMENTS（2²⁷；實測 1.3e8 要 1～3.5 s）。
  - 逐窗局部迴歸（時間模式的全部、樣本模式的穩健重擬合與兩端借窗）：Σ|S_i|·(16 + (次數+1)²)·擬合次數 > MAX_REGRESSION_UNITS（2³¹）。
    只算 Σ|S_i| 低估了批次 QR 的 (次數+1)² 成本：第一輪 N＝1000、窗 1000、次數 400 要 22 s、次數 999 跑不完、N＝2e4／窗 2000／次數 20 要 25 s；
    實測這個模型每秒 2.7e8～1.5e9 單位（Apple Silicon Mac、numpy 2.4.6／Accelerate），上限最壞約 8 s，1e6 點、50 樣本窗的 sgolay（1.25e9）仍可算。
  - detrend 分段設計矩陣 N×(斷點數+1) > MAX_DESIGN_ELEMENTS（2²⁴）→ dsv:detrend:tooManyBreakpoints；只有真的有斷點才算（沒有斷點的
    linear 用閉合式 _detrend_linear，O(N)、不配置設計矩陣，1e7 點 0.1 s；第二輪 N > 2²³ 的 detrend(x,'linear') 會被誤拒）。時間斷點→樣本
    （breakpoint_indices）用 searchsorted＋二分搜尋，O(K·log N)、不配置距離表、沒有上限（第三輪 N > 2²⁴ 的時間模式連超出尾端、會被忽略的
    斷點都被誤拒）。
  - movmean 是 O(N) 的累加和，沒有上限；每批處理的元素數由 _CHUNK（2²¹）控制記憶體。
- 樣本軸的共用設計矩陣（_uniform_local_fit；t＝None、t 恰等於 0..N−1，以及完全等距 t 的等距快速路徑第一次擬合）：內部視窗 iL..iR 的
  距離 j−i 與權重完全相同，所以非穩健的
  lowess／loess／sgolay 只做一次 QR 得到濾波係數 h（投影矩陣 QQᵀ 的中心列 × √w），y＝相關（N·W ≤ 2²⁶ 直接內積，否則 FFT，先減平均）；
  兩端借窗的 sgolay 共用同一個多項式（取投影的對應列），lowess／loess 兩端（tricube 隨 t_i 變）與含 NaN 的視窗走一般路徑。
  N＝1000、窗 1000、次數 999 現在 0.13 s；1e5 點、窗 1300 的 lowess 0.09 s（之前 4.7 s）。和一般路徑的差 ≤ 1e-13 相對（selftest 直接比）。
  穩健重擬合的權重隨樣本變，沒有共用矩陣，仍是逐窗（受上限保護：1e5 點、窗 1300 的 rloess 會被拒絕，第一輪要 45 s）。
- 尺度：smooth／auto_window／detrend 先把 x 乘 2^−e（e 由 max|x| 的指數決定，_scale_exponent）再算、結果乘回 2^e。2 的冪次縮放是精確的，
  而且所有步驟都是 x 的一次齊次式，正常範圍的結果逐位元不變（selftest 檢查 smooth(x·2^±600) 與 2^±600·smooth(x) 逐位元相同），
  1e308 等級或次正規的訊號則不再溢位／失去精度（審查者的探測有 59/507 個這類呼叫冒 numpy RuntimeWarning）。

未定／自行決定（報告列為 open question 或沒有參考資料的部分）：
- 時間軸一律用 t0 + n/fs（報告驗證的預設），不用「round(W·fs) 個樣本」的近似；完全等距時用等距快速路徑（ws＝W/Δt、fix；結果和 MATLAB 的實測輸出一致）。
- 樣本模式只接受整數視窗（UI 的規則）：非整數視窗在完全等距時 MATLAB 的結果等同 fix() 截斷、和時間窗法則不同，所以拒絕。
- 含 NaN 的訊號在完全等距軸上：局部迴歸改走取樣點路徑（有 NaN 要排除時不走等距路徑，和 MATLAB 的實測輸出一致）、gaussian 仍走等距路徑；
  movmean／movmedian 照取樣點法則用原本的 t（100+3n 的整數 ws 邊界 tie 也一致）——第四輪都有 MATLAB 數字（uniform_axis2.json）。
- NaN：smoothdata 預設 'omitnan'——movmean／movmedian／gaussian 把 NaN 排除（整窗 NaN→NaN）、局部迴歸把 NaN 樣本權重設 0、
  自動視窗先用 pchip 補 NaN。第四輪的 NaN 案例（uniform_axis2.json、zero_weight.json、zero_weight2.json）在樣本軸與完全等距軸上全部一致；
  app 本來就擋掉 NaN。窗內全是 NaN → NaN。
- 時間斷點剛好在兩個樣本正中間時取前一個（DSV 的決定；MATLAB 這種情況沒測過）。
- 二維輸入拒絕而不是沿第一維逐欄處理（MATLAB 的 smoothdata／detrend 對矩陣會逐欄做；DSV 一次只處理一條訊號）。
- detrend 的時間軸只用來把時間斷點對到樣本（Signal Analyzer 的 Detrend 輸出和不帶時間軸的 detrend(x, …) 相同，實測 22 組），所以它的檢查用 dsv:detrend:timeVector* 代號。
- time_vector(n, fs, t0)：n 非負整數、fs 有限且 > 0、t0 有限、t0 + (n−1)/fs 有限，否則 dsv:clean:invalidTimeVector（之前 fs＝0 會回 NaN／Inf
  並冒 numpy 除零警告，fs＝1e-308 會溢位）。
- check_uniform（Detrend 面板的「非均勻取樣」判斷，MATLAB app 的門檻沒有參考資料）：|Δt_i − (t_N−t_1)/(N−1)| ≤ max(1e-9·Δt̄, 16·eps·max|t|)。
  第二項是 t0 + n/fs 本身的捨入（每個 Δt 的誤差上限約 3·eps·max|t|）；第一輪只用相對 1e-9，會把 time_vector(65536, 8e6, 2.0)（相對偏差 3.6e-9）、
  time_vector(1000, 1e9, 1e6)（0.11）這些 DSV 自己產生的均勻軸誤判成非均勻。
- ±Inf 的訊號：MATLAB smoothdata 會讓 Inf 照 IEEE 傳播（Inf／NaN），但各方法的結果沒有參考資料，而且 app 本來就擋（check_finite），
  所以 smooth／auto_window 直接拒絕（dsv:smoothdata:infiniteInput）；NaN 仍照 'omitnan'。detrend 含 Inf／NaN → 全 NaN（MATLAB 的行為）。
- 時間軸極端值照 IEEE 的極限處理、不冒警告：t ± W/2 溢位成 ±Inf（視窗涵蓋全部）；高斯 d² 溢位 → 權重 0、σ 次正規（2σ²＝0）→ 只有中心點權重 1；
  W/2 捨到 0（W＝最小次正規數）→ 視窗只含 t_i；斷點距離溢位 → Inf，argmin 照常；pchip 權重/割線溢位 → 切線 0（和 MATLAB 同一公式的 IEEE 結果相同）；
  linspace 的 (n−1)·(b−a) 溢位時改先除再乘（照先乘再除的算式會得到 Inf）。
- 參考資料無法分辨的常數（審查者的測試強度備註）：自動視窗的 0.44294 改成 0.4429、分段去趨勢的 bp < N−1 改成 ≤ N−1，233 組仍全部一致
  （前者差在 ceil 的量化、後者最後一個樣本的 hinge 欄全 0 不影響最小平方）。這兩個常數取自 MATLAB 的定義，不是從資料擬出來的。
- _pchip 的切線規則（Fritsch–Carlson 1980、Moler 的端點公式）和 _heuristic_window 的自動視窗法則（含 0.44294）是公開的／必要的定義，
  程式結構與變數名稱是自己的（第二輪重寫過 _pchip），數值和 MATLAB 的 pchip／smoothdata 逐位元相同（45 組自動視窗一致）。
- 局部迴歸的權重下限 WEIGHT_FLOOR＝1e-30（相對窗內最大權重）：MATLAB 沒有這條（它在 S125 算出 1e25），是 DSV 為了結果不隨 BLAS 變
  而加的；只在非零權重剛好等於次數+1 且其中一個是 ~1e-41 的退化窗才看得出差別（見下面「已知差異」；兩種 numpy／BLAS 下釘住的數字都成立）。

已知差異（selftest 用「已知差異」檢查釘住下面的數字，其他全部一致）：
- S125（rloess、時間模式 0.075 s＝7 個樣本、訊號 A 有離群值 i＝36／119／170）：MATLAB 自己的輸出在索引 118／119／120／169／170 是
  −7.6895e22／3.3702e24／5.6419e20／1.5027e22／1.0522e25 的垃圾值（|x| ≤ 6.66；Signal Analyzer 和 smoothdata 直接呼叫相同，maxdiff 0）。
  原因：時間模式裡 |t_j−t_i|/dmax 在對稱窗的另一端不是剛好 1，tricube 權重是 ~8.69e-41 而不是 0（140/200 個窗如此）；中心點又是
  離群值（穩健權重 0），非零權重剛好 3 個＝次數+1，MATLAB 的結果在這種近乎奇異的系統上爆掉。垃圾殘差改變了 median(r) 的
  排名 → 之後每一輪的穩健權重全變 → 其他 195 點差到 0.233（i＝168），200 點只有 i＝172 一致。
  沒有權重下限時本模組的 QR 在那些窗算出的也是捨入值，只是幅度正常——而且隨 BLAS 不同（Accelerate／numpy 2.4.6：i＝169／170 是
  2.977／2.823；OpenBLAS／numpy 1.26.4：3.044／2.570）。所以局部迴歸把相對窗內最大權重 < WEIGHT_FLOOR（1e-30；√w ≈ 1e-15 已低於雙精度
  解析度，這種列對任何雙精度最小平方都沒有資訊）的權重當 0：那些窗的非零權重降到 2 個、次數降為 1，結果 1.633／1.454／1.164／2.956／2.829
  （|y| ≤ 4.20）在兩種 BLAS 上到 1e-15 一致。這不影響其他 232 組（1e-41 的權重對正常的最小平方解只差 ~1e-44；同訊號同窗的非穩健 loess
  S087 仍 2.7e-15 一致，樣本模式的 rloess 7／5（S116／S166，兩端權重剛好是 0）完全一致）。無法以 1e-12 重現 MATLAB 的捨入垃圾。
- 第四輪的同類案例（zero_weight.json／zero_weight2.json，17 組，全部在不是完全等距的 0.37+n/100 軸、loess／rloess／rlowess）：rloess 0.04～0.05 s
  左端 4 點（i＝3：MATLAB −0.10115、DSV 0.52960）、0.07／0.075 s 6 點到 1.94e24；含 NaN 的窗 loess 到 1.59e24、rloess 到 6.5e25、rlowess 1 點差
  0.444、rloess 0.05 s 7 點差 0.824、0.1 s 2 點差 3.3e-12。MATLAB 在這些近奇異的窗輸出捨入垃圾（zero_weight*.json 的數字）；
  t 只差 1 ulp（(37+n)/100，46 點）時 MATLAB 自己的 rloess 0.07 s 差到
  4.08e24（163 點；DSV 差 1.64，1 點），lowess／loess／rlowess 兩種 t 都一致；同樣的訊號與窗在樣本軸、n/1024 上全部一致。每組的點數、位置、
  DSV 值（rel 1e-12）與 MATLAB 值都釘住。
"""
from __future__ import annotations

import math
import numbers
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple

import numpy as np

METHODS = ("movmean", "movmedian", "gaussian", "lowess", "loess", "rlowess", "rloess", "sgolay")
METHOD_TEXT = {"movmean": "移動平均", "movmedian": "移動中位數", "gaussian": "高斯", "lowess": "線性迴歸", "loess": "二次迴歸",
               "rlowess": "穩健線性迴歸", "rloess": "穩健二次迴歸", "sgolay": "Savitzky-Golay"}
DETREND_METHODS = ("constant", "linear", "piecewiselinear")
DETREND_TEXT = {"constant": "常數", "linear": "線性", "piecewiselinear": "分段線性"}
DEFAULT_FACTOR = 0.25                  # SmoothingFactor 預設（smoothdata 與 Smooth 面板）
DEFAULT_DEGREE = 2                     # sgolay Degree 預設
ROBUST_ITERATIONS = 5
TIME_UNITS = {"ps": 1e-12, "ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0, "minutes": 60.0, "hours": 3600.0,
              "days": 86400.0, "years": 365.2425 * 86400.0}      # Window Duration／Breakpoint Units → 秒
WARN_DEGREE_KEYWORD = "sgDegreeWarning"
WARN_DEGREE_TEXT = ("Degree has been adjusted to a smaller value. The specified value was larger than the automatically computed window length.",
                    "次數已調整為較小的值。指定的值大於自動計算的窗長度。")
# Signal Analyzer 面板的驗證訊息（英文、繁中），給 GUI 用；模組本身只檢查 MATLAB 函式層級的條件
UI_TEXT = {
    "smoothWindowDurationErrorSamples": ("Window duration length in samples must be a positive integer", "以樣本為單位的窗持續時間必須是正整數"),
    "smoothWindowDurationErrorTime": ("Window duration length in time units must be a positive numeric scalar", "以時間為單位的窗持續時間必須是正數值純量"),
    "smoothSmoothingFactorError": ("Smoothing factor must be a numeric scalar between 0 and 1", "平滑因子必須是介於 0 和 1 之間的數值純量"),
    "smoothDegreeError": ("Degree must be set to a numeric positive integer.", "次數必須設為正整數。"),
    "smoothDegreeLargerThanWindowLengthError": ("Degree must be less than the window duration.", "次數必須小於窗持續時間。"),
    "smoothDegreeTooLargeErrorMsg": ("Degree is too large. Degree must be less than the largest number of points in any signal window.",
                                     "次數太大。次數必須小於任一訊號窗中的最大點數。"),
    "detrendBreakpointErrorSamples": ("Piecewise breakpoints in samples must be a positive integer", "以樣本為單位的分段斷點必須是正整數"),
    "detrendBreakpointErrorTime": ("Piecewise breakpoints in time units must be a numeric value", "以時間為單位的分段斷點必須是數值"),
    "preprocessNotFiniteWarning": ("Unable to preprocess signals with missing or nonfinite values. Use Fill Missing to fill missing values.",
                                   "無法前處理含有缺失值或非有限值的訊號。請先用「填補缺失值」補上缺失值。"),
    "detrendNonUniformSignalsWarning": ("Unable to detrend nonuniformly sampled signals. Use the resample function to create a uniformly "
                                        "sampled signal or change signal table selection.",
                                        "無法對非均勻取樣的訊號去除趨勢。請用 resample 建立均勻取樣的訊號，或更改訊號表的選取。"),
}
_CHUNK = 1 << 21                        # 每批處理的元素數（視窗數 × 窗內樣本數 × 設計矩陣欄數），控制記憶體
MAX_WINDOW_ELEMENTS = 1 << 27           # movmedian／gaussian：所有視窗合計樣本數 Σ|S_i| 的上限（DSV 自訂，避免卡住；實測 1.3e8 約 1～3.5 s）
MAX_REGRESSION_UNITS = 1 << 31          # 逐窗局部迴歸的工作量上限：Σ|S_i|·(16+(次數+1)²)·擬合次數（見 _regression_units；實測 2.7e8～1.5e9 單位/s）
_REGRESSION_OVERHEAD = 16               # 每個視窗元素在 QR 之外的固定成本（取值、距離、tricube、開根號……），以 (次數+1)² 的 QR 成本為單位（實測校正）
_DIRECT_CORRELATE_MAX = 1 << 26         # 樣本軸濾波：N×W 不超過這個數就直接做內積（np.correlate），否則走 FFT
MAX_DESIGN_ELEMENTS = 1 << 24           # detrend 分段設計矩陣 N×(斷點數+1)／斷點距離表 N×斷點數 的上限（DSV 自訂）
WEIGHT_FLOOR = 1e-30                    # 局部迴歸：相對於窗內最大權重小於這個比例的權重當 0（√w 已低於雙精度解析度；見「已知差異」S125）
UNIFORM_DT_TOL_ULPS = 16.0              # check_uniform：Δt 的偏差容許 16·eps·max|t|（t0 + n/fs 的捨入誤差上限 ~3·eps·max|t|）或相對 1e-9


class CleanError(ValueError):
    """MATLAB／Signal Analyzer 會拒絕的輸入：identifier（MATLAB 的錯誤代號或 DSV 的 dsv:* 代號）、英文訊息、繁中訊息 zh。
    keyword＝Signal Analyzer 對話框的訊息代碼（「次數太大」那一則），GUI 可用它決定對話框文字。"""

    def __init__(self, identifier: str, message: str, zh: str, keyword: Optional[str] = None):
        super().__init__(message)
        self.identifier = identifier
        self.zh = zh
        self.keyword = keyword


def _err(identifier: str, message: str, zh: str, keyword: Optional[str] = None) -> CleanError:
    return CleanError(identifier, message, zh, keyword)


# ---------------------------------------------------------------- 輸入轉換與檢查
_BAD_SIGNAL = {   # MATLAB R2025a 對非數值第一個引數的錯誤（error_ids.m 實測：字串、cell）
    "smoothdata": ("MATLAB:smoothdata:badArray",
                   "Invalid data type. First argument must be a numeric or logical array, a table, or a timetable."),
    "detrend": ("MATLAB:detrend:InvalidFirstInput", "Invalid data type. First argument must be of type double, single, table, or timetable."),
}


def _as_signal(x, family: str) -> np.ndarray:
    """輸入訊號 → 一維 float／complex 陣列（bool／整數→float）。非數值 → MATLAB 的 badArray（smoothdata）／InvalidFirstInput（detrend）
    （R2025a 實測，error_ids.json）；真正的二維 → dsv:*:notVector（MATLAB 會逐欄處理，DSV 一次只處理一條訊號）。"""
    try:
        a = np.asarray(x)
    except Exception:
        a = np.zeros(0, dtype=object)
        a = a.astype(str)
    shown = a.dtype
    if a.dtype.kind == "O":
        vals = list(a.reshape(-1))
        if all(isinstance(v, numbers.Number) and not isinstance(v, bool) for v in vals):
            a = np.asarray(vals, dtype=complex).reshape(a.shape)
            if not np.any(a.imag):
                a = a.real
        else:
            a = a.astype(str)
    if a.dtype.kind not in "biufc":
        ident, en = _BAD_SIGNAL.get(family, (f"dsv:{family}:nonNumericInput", "Input signal must be numeric."))
        raise _err(ident, f"{en} (got dtype {shown})", f"輸入訊號必須是數值（收到的型別是 {shown}）。")
    if sum(1 for s in a.shape if s != 1) > 1:
        raise _err(f"dsv:{family}:notVector",
                   f"Input signal must be a vector; DSV processes one signal at a time (got shape {a.shape}).",
                   f"輸入訊號必須是向量；DSV 一次只處理一條訊號（收到的形狀是 {a.shape}）。")
    a = a.reshape(-1)
    return a.astype(complex if a.dtype.kind == "c" else float, copy=False)


def _real_scalar(v) -> Optional[float]:
    """實數純量（int／float／numpy 數值／單元素陣列）→ float；字串、複數、bool、None、多元素 → None（呼叫端丟對應的 CleanError）。"""
    if v is None or isinstance(v, (bool, str, bytes)):
        return None
    if isinstance(v, numbers.Real):                           # Python int／float／numpy 純量；超過 int64 的 Python int（10**30）照 float 處理
        try:
            return float(v)
        except OverflowError:                                 # 10**400 → Inf（和 1e400 一樣，呼叫端以「非有限」拒絕）
            return math.inf
    try:
        a = np.asarray(v)
    except Exception:
        return None
    if a.dtype.kind not in "iuf" or a.size != 1:
        return None
    return float(a.reshape(-1)[0])


def _scalar_parts(v, allow_bool: bool = False) -> Tuple[str, float]:
    """純量參數分類：('real', 值)、('complex', NaN)（複數型別）、('bad', NaN)（字串、None、多元素、非數值）。
    allow_bool：MATLAB 把 logical 當 0／1 的參數（視窗、SmoothingFactor：smoothdata(x,'movmean',true) 可算、false → invalidWinsize；
    Degree 的 true → negativeDegree，因為 MATLAB 檢查 isnumeric；R2025a 實測 error_ids.json）。超過 int64 的 Python int（10**30）照 float，
    10**400 → Inf。"""
    if isinstance(v, (bool, np.bool_)):
        return ("real", float(v)) if allow_bool else ("bad", math.nan)
    if v is None or isinstance(v, (str, bytes)):
        return "bad", math.nan
    if isinstance(v, numbers.Real):
        try:
            return "real", float(v)
        except OverflowError:
            return "real", math.inf
    if isinstance(v, numbers.Complex):
        return "complex", math.nan
    try:
        a = np.asarray(v)
    except Exception:
        return "bad", math.nan
    if a.size != 1:
        return "bad", math.nan
    k = a.dtype.kind
    if k == "b":
        return ("real", float(a.reshape(-1)[0])) if allow_bool else ("bad", math.nan)
    if k in "iuf":
        return "real", float(a.reshape(-1)[0])
    if k == "c":
        return "complex", math.nan
    return "bad", math.nan


def _check_window(window) -> float:
    """視窗長度（smoothdata 的 winsz 純量）。MATLAB R2025a 實測的錯誤（error_ids.json）：複數 → noComplexWindows、NaN／Inf →
    needsFiniteWindows、0／負數／多元素 → invalidWinsize（DSV 另外拒絕 MATLAB 接受的兩元素 [kb kf]：Signal Analyzer 只傳純量）。"""
    kind, w = _scalar_parts(window, allow_bool=True)
    if kind == "complex":
        raise _err("MATLAB:smoothdata:noComplexWindows", "Window length must be real.", "窗長度必須是實數。")
    if kind == "real" and not math.isfinite(w):
        raise _err("MATLAB:smoothdata:needsFiniteWindows", "Window length must be finite.", "窗長度必須是有限的數。")
    if kind == "bad" or not w > 0:
        raise _err("MATLAB:smoothdata:invalidWinsize",
                   "Window length must be a positive numeric or duration scalar or a 2-element numeric or duration vector "
                   "(DSV takes the scalar form only).", "窗長度必須是正的數值純量（DSV 不接受 [kb kf] 兩元素形式）。")
    return w


def _real_vector(v) -> Optional[np.ndarray]:
    """實數向量（list／tuple／陣列／純量）→ 一維 float；含字串、複數、bool、None → None。"""
    if v is None or isinstance(v, (bool, str, bytes)):
        return None
    try:
        a = np.asarray(v)
    except Exception:
        return None
    if a.dtype.kind == "O":
        vals = list(a.reshape(-1))
        if not all(isinstance(e, numbers.Real) and not isinstance(e, bool) for e in vals):
            return None
        a = np.asarray(vals, dtype=float)
    if a.dtype.kind not in "iuf":
        return None
    return a.reshape(-1).astype(float, copy=False)


_SP_TEXT = {
    "smoothdata": {   # 代號與英文訊息是 MATLAB R2025a 實測（error_ids.json）；span 是 DSV 自己的檢查
        "type": ("MATLAB:samplePoints:SamplePointsInvalidDatatype",
                 "'SamplePoints' value must be a vector of type double, single, duration, or datetime.", "SamplePoints 必須是數值向量。"),
        "complex": ("MATLAB:samplePoints:SamplePointsComplex", "'SamplePoints' value must be real.", "SamplePoints 必須是實數。"),
        "matrix": ("MATLAB:samplePoints:SamplePointsInvalidDatatype",
                   "'SamplePoints' value must be a vector of type double, single, duration, or datetime.", "SamplePoints 必須是向量。"),
        "length": ("MATLAB:samplePoints:SamplePointsLength",
                   "The sample points vector length must be {n}, the same as the size of the input data in the operating dimension.",
                   "SamplePoints 的長度必須是 {n}，和輸入資料的長度相同。"),
        "finite": ("MATLAB:samplePoints:SamplePointsNonFinite", "'SamplePoints' value must not contain Inf or NaN.", "SamplePoints 不能含 Inf 或 NaN。"),
        "sorted": ("MATLAB:samplePoints:SamplePointsSorted", "'SamplePoints' value must be sorted in ascending order.", "SamplePoints 必須遞增排序。"),
        "unique": ("MATLAB:samplePoints:SamplePointsDuplicate", "'SamplePoints' value contains duplicates.", "SamplePoints 的值有重複。"),
        "span": ("dsv:smoothdata:samplePointsSpanOverflow", "'SamplePoints' span (last minus first) overflows double precision; DSV does not "
                 "evaluate windows on such an axis.", "SamplePoints 的跨度（末減首）超過雙精度範圍；DSV 不在這種時間軸上算視窗。"),
    },
    "detrend": {
        "type": ("dsv:detrend:timeVectorNonNumeric", "Time vector must be a real numeric vector.", "時間軸必須是實數向量。"),
        "complex": ("dsv:detrend:timeVectorNonNumeric", "Time vector must be a real numeric vector.", "時間軸必須是實數向量。"),
        "matrix": ("dsv:detrend:timeVectorLength", "Time vector must be a vector.", "時間軸必須是向量。"),
        "length": ("dsv:detrend:timeVectorLength", "Time vector must be a vector of the same length as the input signal ({n}).",
                   "時間軸必須是和輸入訊號同長度的向量（{n}）。"),
        "finite": ("dsv:detrend:timeVectorNonFinite", "Time vector must not contain Inf or NaN.", "時間軸不能含 Inf 或 NaN。"),
        "sorted": ("dsv:detrend:timeVectorSorted", "Time vector must be sorted in ascending order.", "時間軸必須遞增排序。"),
        "unique": ("dsv:detrend:timeVectorDuplicate", "Time vector values must be unique.", "時間軸的值必須唯一。"),
        "span": ("dsv:detrend:timeVectorSpanOverflow", "Time vector span (last minus first) overflows double precision.",
                 "時間軸的跨度（末減首）超過雙精度範圍。"),
    },
}


def _as_times(t, family: str) -> np.ndarray:
    """取樣點／時間軸 → 一維 float 陣列；複數 → complex 錯誤；字串、bool、真正的二維 → type 錯誤（MATLAB 對 logical、字串與矩陣都回
    SamplePointsInvalidDatatype；DSV 另外接受整數陣列，MATLAB 只收 double／single／duration／datetime）。"""
    try:
        a = np.asarray(t)
    except Exception:
        a = np.zeros(0, dtype=str)
    if a.dtype.kind == "O":
        vals = list(a.reshape(-1))
        a = np.asarray(vals, dtype=float).reshape(a.shape) if all(isinstance(e, numbers.Real) and not isinstance(e, bool) for e in vals) \
            else a.astype(str)
    if a.dtype.kind == "c":
        raise _err(*_SP_TEXT[family]["complex"])
    if a.dtype.kind not in "iuf":
        raise _err(*_SP_TEXT[family]["type"])
    if sum(1 for s in a.shape if s != 1) > 1:
        raise _err(*_SP_TEXT[family]["matrix"])
    return a.reshape(-1).astype(float, copy=False)


def _check_sample_points(t: np.ndarray, n: Optional[int], family: str) -> None:
    """同長度（n＝None 不檢查）、有限、遞增、唯一。"""
    txt = _SP_TEXT[family]
    if n is not None and t.size != n:
        ident, en, zh = txt["length"]
        raise _err(ident, en.format(n=n), zh.format(n=n))
    if not np.all(np.isfinite(t)):
        raise _err(*txt["finite"])
    if t.size >= 2:
        if not math.isfinite(float(t[-1]) - float(t[0])):            # Python float 相減溢位安靜地變 Inf（不冒警告）
            raise _err(*txt["span"])
        d = np.diff(t)                                               # 跨度有限 → 相鄰差不會溢位
        if np.any(d < 0):
            raise _err(*txt["sorted"])
        if np.any(d == 0):
            raise _err(*txt["unique"])


def _check_work(lo: np.ndarray, hi: np.ndarray, label: str) -> None:
    """movmedian／gaussian 逐窗處理的工作量 Σ|S_i|（＝要做的元素運算數）超過 MAX_WINDOW_ELEMENTS 就拒絕，不要讓 GUI 卡住。"""
    total = int(np.sum(hi - lo))
    if total > MAX_WINDOW_ELEMENTS:
        n = int(lo.size)
        wmax = int(np.max(hi - lo))
        raise _err("dsv:clean:tooMuchWork",
                   f"{label}: the windows hold {total} samples in total (N={n}, largest window {wmax} samples), more than the DSV limit "
                   f"of {MAX_WINDOW_ELEMENTS}; use a shorter window.",
                   f"{label}：所有視窗合計 {total} 個樣本（N={n}、最大窗 {wmax} 個樣本），超過 DSV 的上限 {MAX_WINDOW_ELEMENTS}（避免計算卡住）；請縮短視窗。")


def _regression_units(total: int, degree: int, passes: int) -> int:
    """逐窗局部迴歸的工作量模型：每個視窗元素要做批次 QR（∝(次數+1)²）加上固定成本 _REGRESSION_OVERHEAD，乘上擬合次數
    （非穩健 1、穩健 1+ROBUST_ITERATIONS）。實測（Apple Silicon Mac、numpy 2.4.6／Accelerate）每秒 2.7e8～1.5e9 單位，
    所以 MAX_REGRESSION_UNITS＝2³¹ 最壞約 8 秒。只算 Σ|S_i| 時 N＝1000、窗 1000、次數 400 要 22 s 以上、次數 999 跑不完。"""
    return int(total) * (_REGRESSION_OVERHEAD + (int(degree) + 1) ** 2) * int(passes)


def _check_regression_work(lo: np.ndarray, hi: np.ndarray, degree: int, passes: int, label: str, units: Optional[int] = None) -> None:
    """逐窗局部迴歸（一般路徑）：_regression_units 超過 MAX_REGRESSION_UNITS 就拒絕（dsv:clean:tooMuchWork）。
    units 給了就用給的總工作量（第一次擬合與穩健重擬合的視窗不同時由呼叫端加總），lo／hi 只用來寫訊息。"""
    total = int(np.sum(hi - lo))
    if units is None:
        units = _regression_units(total, degree, passes)
    if units > MAX_REGRESSION_UNITS:
        n = int(lo.size)
        wmax = int(np.max(hi - lo)) if lo.size else 0
        raise _err("dsv:clean:tooMuchWork",
                   f"{label}: {n} windows holding {total} samples in total (largest window {wmax} samples) with polynomial degree {degree} and "
                   f"{passes} fit(s) need {units:.3g} work units, more than the DSV limit of {MAX_REGRESSION_UNITS} (about 8 s); "
                   f"use a shorter window, a lower degree, or samples mode (whose interior windows share one design matrix).",
                   f"{label}：{n} 個視窗合計 {total} 個樣本（最大窗 {wmax} 個樣本）、次數 {degree}、擬合 {passes} 次，工作量 {units:.3g} 單位，"
                   f"超過 DSV 的上限 {MAX_REGRESSION_UNITS}（約 8 秒，避免計算卡住）；請縮短視窗、降低次數，或改用樣本模式（內部視窗共用設計矩陣）。")


def _scale_exponent(x: np.ndarray) -> int:
    """x 的尺度指數 e：max|有限的實虛部| ∈ [2^(e−1), 2^e)。把 x 乘 2^−e 後再算，結果乘回 2^e——2 的冪次縮放在雙精度裡是精確的，
    smooth／detrend 的每一步（和、差、商、FFT、QR、中位數、穩健權重）都是 x 的一次齊次式，所以正常範圍的訊號結果逐位元不變，
    而 1e308 等級或次正規的訊號不會在中途溢位／失去精度（不冒 numpy 警告）。全 NaN／全 0 → 0。"""
    parts = [np.abs(x.real)]
    if np.iscomplexobj(x):
        parts.append(np.abs(x.imag))
    amax = 0.0
    for a in parts:
        a = a[np.isfinite(a)]
        if a.size:
            amax = max(amax, float(a.max()))
    return math.frexp(amax)[1] if amax > 0.0 else 0


def _ldexp(x: np.ndarray, e: int) -> np.ndarray:
    """x·2^e（複數分實虛部；e＝0 直接傳回；乘回去時真的超過 realmax 才會變 Inf，那是結果本身放不進雙精度）。"""
    if e == 0:
        return x
    with np.errstate(over="ignore"):
        if np.iscomplexobj(x):
            return np.ldexp(x.real, e) + 1j * np.ldexp(x.imag, e)
        return np.ldexp(x, e)


def time_vector(n, fs, t0=0.0) -> np.ndarray:
    """MATLAB 的 t0 + (0:N−1)'/fs（逐位元相同；DSV 的 fs＝SPS × symbol rate、t0＝第一個樣本的秒數）。
    n 非負整數、fs 有限且 > 0、t0 有限、最後一個時間 t0 + (n−1)/fs 有限（fs＝1e-308 這種會溢位的拒絕），否則 CleanError dsv:clean:invalidTimeVector。"""
    nv, fsv, t0v = _real_scalar(n), _real_scalar(fs), _real_scalar(t0)
    if nv is None or not (math.isfinite(nv) and nv >= 0 and nv == math.floor(nv)):
        raise _err("dsv:clean:invalidTimeVector", f"Number of samples must be a non-negative integer (got {n!r}).",
                   f"樣本數必須是非負整數（收到 {n!r}）。")
    if fsv is None or not (math.isfinite(fsv) and fsv > 0):
        raise _err("dsv:clean:invalidTimeVector", f"Sample rate must be a finite positive number (got {fs!r}).",
                   f"取樣率必須是有限的正數（收到 {fs!r}）。")
    if t0v is None or not math.isfinite(t0v):
        raise _err("dsv:clean:invalidTimeVector", f"Start time must be a finite number (got {t0!r}).", f"起始時間必須是有限的數（收到 {t0!r}）。")
    if nv >= 2 and not math.isfinite(t0v + (nv - 1) / fsv):          # Python float：溢位安靜地變 Inf，不冒例外或警告
        raise _err("dsv:clean:invalidTimeVector", f"Time axis overflows double precision (t0={t0v!r}, fs={fsv!r}, n={int(nv)}).",
                   f"時間軸超過雙精度範圍（t0={t0v!r}、fs={fsv!r}、n={int(nv)}）。")
    return t0v + np.arange(int(nv), dtype=float) / fsv


def is_exactly_uniform(t) -> bool:
    """「完全等距」的判斷：max(Δt) == min(Δt)（浮點完全相等）。t 要是有限、遞增、唯一的實數向量
    （和 smoothdata 的 SamplePoints 檢查相同，否則丟 CleanError；之前含 Inf 的 t 會冒 numpy 的 Inf−Inf 警告）。"""
    t = _as_times(t, "smoothdata")
    _check_sample_points(t, None, "smoothdata")
    if t.size < 2:
        return False
    d = np.diff(t)
    return bool(np.max(d) == np.min(d))


def _reject_inf(x: np.ndarray, family: str) -> None:
    """smooth／auto_window 不接受 ±Inf（實部或虛部）：MATLAB 的 smoothdata 會讓 Inf 照 IEEE 傳播成 Inf／NaN，但每種方法的結果
    沒有參考資料可對，而且 app 本來就擋掉非有限值（check_finite），DSV 自行決定在模組層也拒絕 Inf；NaN 照 'omitnan' 處理。"""
    if np.isinf(x).any():
        raise _err(f"dsv:{family}:infiniteInput",
                   "Input signal must not contain Inf or -Inf (NaN is omitted like smoothdata's default 'omitnan'; the Signal Analyzer "
                   "panel rejects both).", "輸入訊號不能含 Inf／−Inf（NaN 照 smoothdata 預設的 'omitnan' 排除；Signal Analyzer 面板兩者都擋）。")


def check_finite(x) -> None:
    """Signal Analyzer 的 Smooth／Detrend 不接受含 NaN／Inf 的訊號（preprocessNotFiniteWarning）。"""
    x = _as_signal(x, "clean")
    if not np.all(np.isfinite(x)):
        en, zh = UI_TEXT["preprocessNotFiniteWarning"]
        raise _err("preprocessNotFiniteWarning", en, zh)


def check_uniform(t) -> None:
    """Signal Analyzer 的 Detrend 不接受非均勻取樣（detrendNonUniformSignalsWarning）；t＝None（樣本模式）一定均勻。
    DSV 的判斷（MATLAB app 的門檻沒有參考資料）：每個 Δt 和「(t_N − t_1)/(N−1)」的差不超過 max(1e-9·Δt̄, UNIFORM_DT_TOL_ULPS·eps·max|t|)。
    第二項是浮點時間軸 t0 + n/fs 本身的捨入：每個 t 的誤差 ≤ ~eps·|t|，相鄰差的誤差 ≤ ~3·eps·max|t|——t0·fs 或 N 很大時這會超過 1e-9·Δt
    （例如 time_vector(1000, 1e9, t0=1e6) 的 Δt 相對偏差 0.11、time_vector(65536, 8e6, t0=2) 3.6e-9），只用相對 1e-9 會把 DSV 自己
    產生的均勻時間軸誤判成非均勻。非有限／遞減／重複的 t 丟 dsv:detrend:timeVector* 的 CleanError。"""
    if t is None:
        return
    t = _as_times(t, "detrend")
    _check_sample_points(t, None, "detrend")
    if t.size >= 3:
        d = np.diff(t)
        step = (float(t[-1]) - float(t[0])) / (t.size - 1)
        tol = max(1e-9 * abs(step), UNIFORM_DT_TOL_ULPS * float(np.finfo(float).eps) * float(np.max(np.abs(t))))
        if float(np.max(np.abs(d - step))) > tol:
            en, zh = UI_TEXT["detrendNonUniformSignalsWarning"]
            raise _err("detrendNonUniformSignalsWarning", en, zh)


# ---------------------------------------------------------------- pchip（自動視窗用）
def _end_tangent(gap_near: float, gap_far: float, sec_near: float, sec_far: float) -> float:
    """pchip 端點切線（Fritsch–Carlson／Moler 的三點公式，公開文獻）：用最靠近端點的兩段割線 sec_near、sec_far 與區間寬
    gap_near、gap_far 做二次外插 ((2·gap_near + gap_far)·sec_near − gap_near·sec_far)/(gap_near + gap_far)；
    和 sec_near 異號 → 0（保形）；兩段割線異號且外插值超過 3·sec_near → 限制在 3·sec_near。"""
    est = ((2.0 * gap_near + gap_far) * sec_near - gap_near * sec_far) / (gap_near + gap_far)
    if np.sign(est) != np.sign(sec_near):
        return 0.0
    if np.sign(sec_near) != np.sign(sec_far) and abs(est) > abs(3.0 * sec_near):
        return 3.0 * sec_near
    return float(est)


def _pchip(xs: np.ndarray, ys: np.ndarray, xq: np.ndarray) -> np.ndarray:
    """MATLAB pchip／interp1(...,'pchip')：形狀保持的分段三次 Hermite 內插（Fritsch & Carlson 1980 的切線規則，和 SciPy
    PchipInterpolator 相同）：內點兩側割線同號時切線取「以 (2·右寬＋左寬)、(右寬＋2·左寬) 加權的調和平均」，異號或有零時 0；
    端點用 _end_tangent 的三點公式。範圍外的查詢點用端點那段的三次式外插。複數分實虛部。xs 遞增且唯一。"""
    if np.iscomplexobj(ys):
        return _pchip(xs, ys.real, xq) + 1j * _pchip(xs, ys.imag, xq)
    n = xs.size
    if n == 1:
        return np.full(xq.shape, float(ys[0]))
    gap = np.diff(xs)                                        # 每段的寬
    secant = np.diff(ys) / gap                               # 每段的割線斜率
    if n == 2:
        tangent = np.repeat(secant[:1], 2)                   # 兩點：直線
    else:
        gl, gr = gap[:-1], gap[1:]                           # 內點左、右段的寬
        sl, sr = secant[:-1], secant[1:]                     # 內點左、右段的割線
        wl = 2.0 * gr + gl                                   # 加權調和平均的權重（靠近短段的割線權重大）
        wr = gr + 2.0 * gl
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):   # 割線為 0／異號的位置算出 Inf／NaN，但下面不採用；
            harmonic = (wl + wr) / (wl / sl + wr / sr)                        # 權重/割線溢位（段寬 1e306、割線 1e-306）→ 切線 0，和同一公式的 IEEE 結果一樣
        tangent = np.zeros(n)
        tangent[1:-1] = np.where(np.sign(sl) * np.sign(sr) > 0, harmonic, 0.0)
        tangent[0] = _end_tangent(gap[0], gap[1], secant[0], secant[1])
        tangent[-1] = _end_tangent(gap[-1], gap[-2], secant[-1], secant[-2])
    seg = np.clip(np.searchsorted(xs, xq, side="right") - 1, 0, n - 2)   # 每個查詢點所在的段（範圍外→端點那段）
    u = xq - xs[seg]
    width = gap[seg]
    sec = secant[seg]
    t0, t1 = tangent[seg], tangent[seg + 1]
    with np.errstate(over="ignore"):                         # 段寬 > 1e154 時 width² 溢位成 Inf → 三次項係數 0（正確的極限）
        cubic = (t0 + t1 - 2.0 * sec) / (width * width)
        quad = (3.0 * sec - 2.0 * t0 - t1) / width
    return ((cubic * u + quad) * u + t0) * u + ys[seg]       # Hermite 三次式的 Horner 形式


def _fill_nan_pchip(t: np.ndarray, x: np.ndarray) -> np.ndarray:
    """fillmissing(x,'pchip','SamplePoints',t,'EndValues','extrap')：用非 NaN 的點做 pchip，補 NaN 的位置（含外插）。"""
    bad = np.isnan(x)
    if not bad.any():
        return x
    good = ~bad
    if not good.any():
        return x
    out = x.copy()
    out[bad] = _pchip(t[good], x[good], t[bad])
    return out


def _linspace(a: float, b: float, n: int) -> np.ndarray:
    """MATLAB linspace 的算法（a + (0:n−1)·(b−a)/(n−1)，先乘再除；a＝−b 時用對稱式；頭尾設成 a、b）。
    自行決定：(n−1)·(b−a) 溢位（跨度 > realmax/(n−1)，照先乘再除的算式會得到 Inf）時改成先除再乘。"""
    n1 = n - 1
    if a == -b and n > 2:
        y = np.arange(-n1, n1 + 1, 2, dtype=float) * (b / n1)
        if n1 % 2 == 0:
            y[n1 // 2] = 0.0
    else:
        k = np.arange(n, dtype=float)
        with np.errstate(over="ignore"):
            y = a + (k * (b - a)) / n1
        if not np.all(np.isfinite(y)):
            y = a + k * ((b - a) / n1)
    y[0] = a
    y[-1] = b
    return y


# ---------------------------------------------------------------- 自動視窗
def _heuristic_window(a: np.ndarray, tau: float) -> int:
    """自動視窗的樣本域法則（a 已補 NaN）：FFT 能量累積到 τ 的 bin 數 → 移動平均寬度（整數）。"""
    n = a.size
    if tau == 0:
        return n
    if tau == 1:
        return 1
    a = a - np.mean(a)
    P = np.abs(np.fft.fft(a, 2 * n)) ** 2 / (2 * n)
    if np.iscomplexobj(a):
        P[1:] = 0.5 * (P[1:] + P[1:][::-1])
    P = P[:n]
    s = np.sum(P)
    with np.errstate(invalid="ignore", divide="ignore"):
        c = np.cumsum(P / s)
    idx = np.flatnonzero(c > tau)
    if idx.size == 0:
        return 1
    rho = int(idx[0]) + 1
    return int(math.ceil(math.sqrt((0.44294 * 2 * n / max(rho - 1, 1)) ** 2 + 1)))


def _clip_window(w: float) -> float:
    if w == 0:
        return float(np.finfo(float).tiny)
    if not math.isfinite(w):
        return float(np.finfo(float).max)
    return w


def _check_factor(factor) -> float:
    """SmoothingFactor：複數 → MATLAB:smoothdata:noComplex；不是 0～1 的實數純量（含 NaN、字串、多元素）→ invalidSmoothingFactor；
    logical 當 0／1（R2025a 實測 error_ids.json）。"""
    kind, f = _scalar_parts(factor, allow_bool=True)
    if kind == "complex":
        raise _err("MATLAB:smoothdata:noComplex", "'SmoothingFactor' value must be real.", "SmoothingFactor 必須是實數。")
    if kind == "bad" or not (0.0 <= f <= 1.0):
        raise _err("MATLAB:smoothdata:invalidSmoothingFactor", "'SmoothingFactor' value must be a numeric scalar between 0 and 1.",
                   "SmoothingFactor 必須是 0 到 1 之間的數值純量。")
    return f


def auto_window(x, t=None, factor: float = DEFAULT_FACTOR):
    """smoothdata 的自動視窗（SmoothingFactor factor）。t＝None：樣本模式，回整數樣本數；否則回和 t 同單位的寬度。
    x 先做 2 的冪次縮放（FFT 能量法則是尺度不變的；1e154 以上的訊號 |FFT|² 會溢位、1e-160 以下會變 0，縮放後結果逐位元不變）。"""
    x = _as_signal(x, "smoothdata")
    _reject_inf(x, "smoothdata")
    x = _ldexp(x, -_scale_exponent(x))
    n = x.size
    tau = 1.0 - _check_factor(factor)
    if t is not None:
        t = _as_times(t, "smoothdata")
        _check_sample_points(t, n, "smoothdata")
    if n < 2:
        return 1 if t is None else 1.0
    if t is None:
        return _heuristic_window(_fill_nan_pchip(np.arange(n, dtype=float), x), tau)
    # 下面的乘除用 Python float：溢位安靜地變 Inf／0（再由 _clip_window 換成 realmax／realmin），不冒 numpy 警告
    if is_exactly_uniform(t):
        k = _heuristic_window(_fill_nan_pchip(t, x), tau)
        return _clip_window(k * (float(t[1]) - float(t[0])))
    if tau == 0:
        return _clip_window(float(t[-1]) - float(t[0]))
    if tau == 1:
        return _clip_window(float(np.min(np.diff(t))) / 2.0)
    xi = _pchip(t, _fill_nan_pchip(t, x), _linspace(float(t[0]), float(t[-1]), n))
    k = _heuristic_window(xi, tau)
    return _clip_window(k * ((float(t[-1]) - float(t[0])) / (n - 1)))


# ---------------------------------------------------------------- 視窗工具
def _window_bounds(t: np.ndarray, w: float) -> Tuple[np.ndarray, np.ndarray]:
    """每個 i 的半開視窗在排序好的 t 裡的索引範圍 [lo, hi)：j 屬於 S_i ⇔ t_j ≥ t_i − W/2 且 t_j − t_i < W/2。
    左邊界比「t_j 和 t_i − W/2」、右邊界比「差值 t_j − t_i 和 W/2」——兩種比法的捨入不同，這樣才和 MATLAB 的結果一致
    （100 Hz、0.08／0.18／0.36 s 這些邊界剛好落在樣本上的案例逐點驗證過；用同一種比法比兩邊都會錯幾十點）。"""
    half = w / 2.0
    n = t.size
    if half == 0.0:                                         # W 是最小的次正規數時 W/2 捨到 0：|t_j − t_i| < W/2 只有 t_i 自己（t 唯一）
        return np.arange(n), np.arange(n) + 1
    with np.errstate(over="ignore"):                        # t ± W/2 可能溢位成 ±Inf（例如 W＝realmax）：searchsorted 照常給 0／n
        lo = np.searchsorted(t, t - half, side="left")
        hi = np.searchsorted(t, t + half, side="left")
        for _ in range(8):                                  # 修正右邊界到「t_j − t_i < W/2」的判斷（差一個 ulp 時才會動）
            up = (hi < n) & ((t[np.minimum(hi, n - 1)] - t) < half)
            dn = (hi > 0) & ((t[np.maximum(hi - 1, 0)] - t) >= half)
            if not (up.any() or dn.any()):
                break
            hi = hi + up.astype(int) - dn.astype(int)
    return lo, hi


def max_window_points(t, w: float) -> int:
    """最大的視窗樣本數 wl＝max_i |S_i|（MATLAB 檢查 sgolay 次數時用的視窗點數）。"""
    t = _as_times(t, "smoothdata")
    if t.size == 0:
        return 0
    wv = _check_window(w)
    lo, hi = _window_bounds(t, wv)
    return int(np.max(hi - lo))


def _groups(cnt: np.ndarray) -> Iterator[Tuple[int, np.ndarray]]:
    """依視窗樣本數分組：yield (樣本數, 有這個樣本數的視窗索引)。"""
    order = np.argsort(cnt, kind="stable")
    cs = cnt[order]
    cut = np.flatnonzero(np.diff(cs)) + 1
    starts = np.concatenate([[0], cut])
    ends = np.concatenate([cut, [cs.size]])
    for a, b in zip(starts, ends):
        yield int(cs[a]), order[a:b]


def _chunks(rows: np.ndarray, m: int) -> Iterator[np.ndarray]:
    step = max(1, _CHUNK // max(m, 1))
    for a in range(0, rows.size, step):
        yield rows[a:a + step]


# ---------------------------------------------------------------- 各平滑法
def _movmean(x: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    nan = np.isnan(x)
    xz = np.where(nan, 0, x)
    if nan.any():
        cv = np.concatenate([[0], np.cumsum(~nan)])
        nv = cv[hi] - cv[lo]
    else:
        nv = hi - lo
    if np.max(hi - lo) <= 256:                            # 短窗：每窗直接相加（準確）
        idx = np.ravel(np.column_stack([lo, hi]))
        s = np.add.reduceat(np.append(xz, 0), idx)[::2]
    else:                                                 # 長窗：去掉平均後的累加和（O(N)）
        m = np.sum(xz) / max(int(np.sum(~nan)), 1)
        cs = np.concatenate([[0], np.cumsum(xz - np.where(nan, 0, m))])
        s = (cs[hi] - cs[lo]) + m * nv
    with np.errstate(invalid="ignore", divide="ignore"):
        y = s / nv
    y[nv == 0] = np.nan
    return y


def _median_rows(block: np.ndarray) -> np.ndarray:
    """每列的中位數（MATLAB median）：NaN 不算；複數先依 |z| 再依 angle 排序；偶數個取中間兩個的平均。"""
    r, m = block.shape
    if np.iscomplexobj(block):
        with np.errstate(invalid="ignore"):
            o1 = np.argsort(np.angle(block), axis=1, kind="stable")
            mag = np.take_along_axis(np.abs(block), o1, axis=1)
        o2 = np.argsort(mag, axis=1, kind="stable")
        srt = np.take_along_axis(block, np.take_along_axis(o1, o2, axis=1), axis=1)
    else:
        srt = np.sort(block, axis=1)                      # NaN 排在最後
    nv = m - np.count_nonzero(np.isnan(block), axis=1)
    rr = np.arange(r)
    half = nv // 2
    a = srt[rr, np.clip(half - 1, 0, m - 1)]
    b = srt[rr, np.clip(half, 0, m - 1)]
    med = np.where(nv % 2 == 1, b, (a + b) / 2.0)
    med[nv == 0] = np.nan
    return med


def _movmedian(x: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    y = np.empty(x.size, dtype=x.dtype)
    for m, rows in _groups(hi - lo):
        for ch in _chunks(rows, m):
            idx = lo[ch, None] + np.arange(m)
            y[ch] = _median_rows(x[idx])
    return y


def _gaussian(x: np.ndarray, t: np.ndarray, lo: np.ndarray, hi: np.ndarray, w: float) -> np.ndarray:
    sig = w / 5.0
    two_s2 = 2.0 * sig * sig
    y = np.empty(x.size, dtype=x.dtype)
    for m, rows in _groups(hi - lo):
        for ch in _chunks(rows, m):
            idx = lo[ch, None] + np.arange(m)
            d = t[idx] - t[ch, None]                          # |d| ≤ 時間軸跨度（已檢查有限）
            with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
                e = (d * d) / two_s2                          # |d| > 1e154 → d² 溢位 → e＝Inf → g＝0（正確的極限）
                bad_e = ~np.isfinite(e) | (d == 0)            # d＝0：0/0（σ 次正規時 2σ²＝0）→ 指數 0；d²、2σ² 都溢位 → Inf/Inf → 改算 (d/σ)²/2
                if bad_e.any():
                    alt = (d / sig) ** 2 / 2.0
                    e = np.where(bad_e, np.where(d == 0, 0.0, alt), e)
            g = np.exp(-e)
            xb = x[idx]
            bad = np.isnan(xb)
            if bad.any():
                g = np.where(bad, 0.0, g)
                xb = np.where(bad, 0, xb)
            den = g.sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                v = (g * xb).sum(axis=1) / den
            v[den == 0] = np.nan
            y[ch] = v
    return y


def _cheb(v: np.ndarray, p: int) -> np.ndarray:
    """Chebyshev 多項式 T_0..T_p 在 v 的值（最後一軸）。"""
    out = np.empty(v.shape + (p + 1,))
    out[..., 0] = 1.0
    if p >= 1:
        out[..., 1] = v
    for k in range(2, p + 1):
        out[..., k] = 2.0 * v * out[..., k - 1] - out[..., k - 2]
    return out


def _cheb_coord(d: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """把每個視窗（最後一軸）的距離 d 線性映到 [−1, 1]：v＝(d − 中點)/半寬，並回中心 d＝0 對應的 v0。
    寫成 (d − mid)/(span/2) 而不是 (2d − (dmin+dmax))/span：兩者對正常範圍逐位元相同（差一個精確的 2 倍），但 2·d 在 |d| > 0.9e308 會溢位。
    d 一定含 0（中心點），所以 dmin ≤ 0 ≤ dmax、|dmin + dmax| ≤ span，不會溢位。"""
    dmin, dmax = d.min(axis=-1, keepdims=True), d.max(axis=-1, keepdims=True)
    half = (dmax - dmin) / 2.0
    half = np.where(half == 0, 1.0, half)
    mid = dmin / 2.0 + dmax / 2.0
    v = (d - mid) / half
    v0 = (-mid / half)[..., 0]
    return v, v0


def _lsq_at_center(d: np.ndarray, wt: np.ndarray, xb: np.ndarray, p: int, c_idx: np.ndarray) -> np.ndarray:
    """每列一個加權最小平方多項式（次數 p、變數 d），回在 d＝0（中心點，列內位置 c_idx）的擬合值。
    基底用視窗範圍映到 [−1, 1] 的 Chebyshev 多項式（條件數小，次數 10 也穩），批次 Householder QR；
    中心點權重 ≥ 0.5 時取投影 (Q Qᵀ b)_c／√w_c（精度到 eps），否則用係數在 d＝0 的值。數學上和單項式基底的常數項相同。"""
    r = d.shape[0]
    sw = np.sqrt(wt)
    v, v0 = _cheb_coord(d)
    A = sw[:, :, None] * _cheb(v, p)
    b = sw * xb
    Q, R = np.linalg.qr(A)
    qtb = np.einsum("rmk,rm->rk", Q, b)
    c = np.linalg.solve(R, qtb[..., None])[..., 0]
    val = np.einsum("rk,rk->r", _cheb(v0[:, None], p)[:, 0, :], c)
    rows = np.arange(r)
    swc = sw[rows, c_idx]
    use = swc >= 0.5
    if use.any():
        val[use] = np.einsum("rk,rk->r", Q[rows[use], c_idx[use], :], qtb[use]) / swc[use]
    return val


def _tricube(d: np.ndarray) -> np.ndarray:
    """lowess／loess 的 tricube 權重 (1 − (|d|/max|d|)³)³（最後一軸是一個視窗；最遠的點權重 0；全 0 距離 → 全 1）。"""
    ad = np.abs(d)
    dmax = ad.max(axis=-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        q = ad / dmax
    q = np.where(dmax == 0, 0.0, q)
    q3 = 1.0 - q * q * q
    return q3 * q3 * q3


def _floor_weights(wt: np.ndarray) -> np.ndarray:
    """相對於窗內最大權重小於 WEIGHT_FLOOR 的權重當 0：√w ≈ 1e-15 以下的列在雙精度的最小平方裡沒有資訊，留著只會讓
    近乎奇異的系統算出隨 BLAS 而異的捨入值（見模組說明「已知差異」S125：MATLAB 在那裡算出 1e25）。"""
    wmax = wt.max(axis=-1, keepdims=True)
    return np.where(wt < WEIGHT_FLOOR * wmax, 0.0, wt)


def _local_fit(x: np.ndarray, t: np.ndarray, lo: np.ndarray, hi: np.ndarray, p: int, weighted: bool,
               rw: Optional[np.ndarray], out: np.ndarray, rows: Optional[np.ndarray] = None) -> None:
    """一般（逐窗）路徑：對 rows 裡的每個 i（預設全部）在視窗 [lo_i, hi_i) 做加權最小平方多項式，把 t_i 的擬合值寫進 out[i]。"""
    sel_rows = np.arange(x.size) if rows is None else np.asarray(rows, dtype=int)
    if sel_rows.size == 0:
        return
    cnt = hi[sel_rows] - lo[sel_rows]
    for m, sub in _groups(cnt):
        for ch in _chunks(sel_rows[sub], m * (p + 1)):     # 每批的設計矩陣 ≤ _CHUNK 個元素
            idx = lo[ch, None] + np.arange(m)
            d = t[idx] - t[ch, None]                          # |d| ≤ 時間軸跨度（已檢查有限）
            xb = x[idx]
            wt = _tricube(d) if weighted else np.ones_like(d)
            if rw is not None:
                wt = wt * rw[idx]
            bad = np.isnan(xb)
            if bad.any():
                wt = np.where(bad, 0.0, wt)
                xb = np.where(bad, 0, xb)
            wt = _floor_weights(wt)
            nnz = np.count_nonzero(wt > 0, axis=1)
            dead = (nnz == 0) & ~bad.all(axis=1)
            if dead.any():                                    # 權重全 0（中心是離群值、鄰點穩健權重也 0；或非 NaN 的只剩 tricube 0 的兩端）：
                wt[dead] = (~bad[dead]).astype(float)         # MATLAB 改用等權重擬合窗內所有非 NaN 的點（zero_weight.json 實測）
                nnz = np.count_nonzero(wt > 0, axis=1)
            peff = np.minimum(p, nnz - 1)
            c_idx = ch - lo[ch]                               # 中心點（t_i 自己）在窗內的位置
            for pe in np.unique(peff):
                sel = peff == pe
                if pe < 0:
                    v = np.zeros(int(sel.sum()), dtype=x.dtype)
                    v[bad[sel].all(axis=1)] = np.nan
                    out[ch[sel]] = v
                else:
                    out[ch[sel]] = _lsq_at_center(d[sel], wt[sel], xb[sel], int(pe), c_idx[sel])


def _correlate_valid(x: np.ndarray, h: np.ndarray) -> np.ndarray:
    """y_s ＝ Σ_k h_k·x_{s+k}（s＝0..N−W；h 實數）。N·W ≤ _DIRECT_CORRELATE_MAX 直接做內積（np.correlate），否則 FFT：
    先減掉 x 的平均再加回 mean·Σh，讓 FFT 的捨入誤差（~eps·log₂L·Σ|h|·max|x−mean|）跟著訊號的起伏而不是直流偏移。"""
    n, m = x.size, h.size
    if n * m <= _DIRECT_CORRELATE_MAX:
        return np.correlate(x, h, mode="valid")              # h 實數 → np.correlate 的共軛對它沒影響
    mu = np.mean(x)
    L = 1 << int(n + m - 1).bit_length()
    X = np.fft.fft(x - mu, L)
    H = np.fft.fft(h[::-1], L)
    full = np.fft.ifft(X * H)[m - 1:n]
    if not np.iscomplexobj(x):
        full = full.real
    return full + mu * float(np.sum(h))


def _shared_filter(d: np.ndarray, wt: np.ndarray, p: int, c: int) -> np.ndarray:
    """樣本軸內部視窗共用的濾波係數 h（y_i＝Σ_j h_j·x_{lo_i+j}）：和 _lsq_at_center 相同的 Chebyshev 基底 QR，取投影矩陣 Q·Qᵀ 的
    第 c 列（中心點）再配上 √w 的縮放——即一般路徑在每個內部視窗算的同一個加權最小平方擬合值，只是把 x 無關的部分算一次。"""
    if p + 1 >= d.size:                      # 次數 ≥ 點數−1：多項式剛好內插全部點，投影矩陣是單位矩陣 → y_i＝x_i（精確；MATLAB 也回 x）
        h = np.zeros(d.size)                 # 省掉 W×W 的 QR（numpy 1.26 對 1000×1000 要 6 秒；結果一樣）
        h[c] = 1.0
        return h
    sw = np.sqrt(wt)
    v, _ = _cheb_coord(d)
    Q, _ = np.linalg.qr(sw[:, None] * _cheb(v, p))
    h = (Q @ Q[c]) * sw / sw[c]
    return h


def _uniform_local_fit(x: np.ndarray, lo: np.ndarray, hi: np.ndarray, iL: int, iR: int, p: int, weighted: bool,
                       label: str) -> np.ndarray:
    """樣本軸（t_j − t_i ＝ j − i，正好等距）、非穩健的局部迴歸：內部視窗 iL..iR 的距離與權重完全相同 → 一次 QR 得到濾波係數，
    y＝相關（O(N·W) 或 FFT）；兩端「借窗」的 i<iL／i>iR：sgolay（全 1 權重）共用同一個多項式，取投影列即可；lowess／loess 的
    tricube 權重隨 t_i 變，照一般批次路徑算（≤ 2·W 個視窗，受工作量上限保護）。含 NaN 的視窗（'omitnan' 把權重設 0）也走一般路徑。
    整數窗 W 的取樣點法則就是 MATLAB 等距快速路徑的定義（濾波係數＋兩端借窗；模組說明），所以這同時是樣本模式的加速和完全等距
    時間軸的 fix(ws) 第一次擬合；數值和一般路徑到 ~1e-16 一致。"""
    n = x.size
    t = np.arange(n, dtype=float)
    y = np.empty(n, dtype=x.dtype)
    nan = np.isnan(x)
    cnan = np.concatenate([[0], np.cumsum(nan)])
    has_nan = (cnan[hi] - cnan[lo]) > 0                       # 視窗內含 NaN
    general: list = []
    inner = np.arange(iL, iR + 1) if iR >= iL else np.zeros(0, dtype=int)
    if inner.size:
        m = int(hi[iL] - lo[iL])
        c = int(iL - lo[iL])
        if not (np.all(hi[inner] - lo[inner] == m) and np.all(inner - lo[inner] == c)):
            general.append(inner)                             # 不該發生（樣本軸的視窗平移不變）；保險起見全走一般路徑
        else:
            d = np.arange(m, dtype=float) - c
            wt = _floor_weights(_tricube(d) if weighted else np.ones(m))
            pe = min(p, int(np.count_nonzero(wt > 0)) - 1)
            if pe < 0:
                y[inner] = 0.0
            else:
                h = _shared_filter(d, wt, pe, c)
                y[inner] = _correlate_valid(np.where(nan, 0, x), h)
            general.append(inner[has_nan[inner]])
    for side, span in (("L", np.arange(0, iL)), ("R", np.arange(iR + 1, n))):
        if span.size == 0:
            continue
        if weighted or has_nan[span].any():
            general.append(span)
            continue
        ref = iL if side == "L" else iR                        # 借用的視窗
        a, b = int(lo[ref]), int(hi[ref])
        tw = t[a:b] - t[ref]
        pe = min(p, b - a - 1)
        if pe < 0:
            y[span] = 0.0
            continue
        v, _ = _cheb_coord(tw)
        Q, _ = np.linalg.qr(_cheb(v, pe))
        qtb = Q.T @ x[a:b]
        y[span] = Q[span - a] @ qtb                            # 多項式在 t_i（窗內第 i−a 個點）的值＝投影的那一列
    if general:
        rows = np.unique(np.concatenate(general))
        _check_regression_work(lo[rows], hi[rows], p, 1, label)
        _local_fit(x, t, lo, hi, p, weighted, None, y, rows)
    return y


def _borrowed_bounds(t: np.ndarray, w: float) -> Tuple[np.ndarray, np.ndarray, int, int]:
    """局部迴歸的視窗 [lo, hi) 加上兩端借窗：iL＝最後一個含樣本 0 的視窗、iR＝第一個含樣本 N−1 的視窗；i<iL 用 S_iL、i>iR 用 S_iR。"""
    n = t.size
    lo, hi = _window_bounds(t, w)
    iL = int(np.flatnonzero(lo == 0)[-1])
    iR = int(np.flatnonzero(hi == n)[0])
    lo2, hi2 = lo.copy(), hi.copy()
    lo2[:iL], hi2[:iL] = lo[iL], hi[iL]
    lo2[iR + 1:], hi2[iR + 1:] = lo[iR], hi[iR]
    return lo2, hi2, iL, iR


def _local_regression(x: np.ndarray, t: np.ndarray, w: float, p: int, weighted: bool, robust: bool, label: str,
                      uniform: bool, w_robust: Optional[float] = None) -> np.ndarray:
    """lowess／loess／rlowess／rloess／sgolay：視窗、兩端借窗、工作量檢查，非穩健擬合（樣本軸走 _uniform_local_fit），穩健再做
    ROBUST_ITERATIONS 次逐窗重擬合（權重隨樣本變，沒有共用的設計矩陣）。
    w_robust：穩健重擬合用的視窗（預設和 w 相同）。和 MATLAB 輸出一致的等距快速路徑：第一次擬合用 fix() 截斷的整數窗 L，穩健重擬合卻用沒截斷的
    ws＝W/Δt 在整數軸上照取樣點法則算，所以兩者要分開給。"""
    n = x.size
    if 2.0 * float(np.min(np.diff(t))) > w:
        return x.copy()
    lo2, hi2, iL, iR = _borrowed_bounds(t, w)
    lo3, hi3 = lo2, hi2
    if robust and w_robust is not None and w_robust != w:
        lo3, hi3, _, _ = _borrowed_bounds(t, w_robust)
    units = 0 if uniform else _regression_units(int(np.sum(hi2 - lo2)), p, 1)
    if robust:
        units += _regression_units(int(np.sum(hi3 - lo3)), p, ROBUST_ITERATIONS)
    if units > MAX_REGRESSION_UNITS:                          # 先拒絕，不要做完第一次擬合才發現
        _check_regression_work(lo3, hi3, p, (ROBUST_ITERATIONS if robust else 0) + (0 if uniform else 1), label, units)
    if uniform:
        y = _uniform_local_fit(x, lo2, hi2, iL, iR, p, weighted, label)
    else:
        y = np.empty(n, dtype=x.dtype)
        _local_fit(x, t, lo2, hi2, p, weighted, None, y)
    if robust:
        ax = np.abs(x)
        ax = ax[~np.isnan(ax)]                             # 全 NaN 時 thr＝0（不用 nanmax，避免 All-NaN 警告）
        thr = (float(ax.max()) if ax.size else 0.0) * math.sqrt(np.finfo(float).eps)
        for _ in range(ROBUST_ITERATIONS):
            r = np.abs(x - y)
            med = float(np.nanmedian(r)) if np.any(~np.isnan(r)) else 0.0
            with np.errstate(invalid="ignore", divide="ignore"):
                u = np.minimum(r / (6.0 * max(thr, med)), 1.0)
            u[np.isnan(u)] = 0.0
            rw = (1.0 - u * u) ** 2
            y = np.empty(n, dtype=x.dtype)
            _local_fit(x, t, lo3, hi3, p, True, rw, y)
    return y


def _uniform_window_samples(w: float, t: np.ndarray) -> float:
    """MATLAB 等距快速路徑的「換算成樣本的窗」ws＝winsz/(t(2)−t(1))（同一個浮點除法；W 很大、Δt 很小時溢位成 Inf，fix(Inf) 之後被
    min(…, N) 夾住，所以照 IEEE 讓它變 Inf 即可）。"""
    with np.errstate(over="ignore"):
        return float(w) / (float(t[1]) - float(t[0]))


def _fixed_length(ws: float, cap: int) -> int:
    """min(fix(ws), cap)：ws ≥ 2 才會呼叫（ws < 2 已原樣傳回）；ws＝Inf → cap。"""
    return cap if ws >= cap else int(math.floor(ws))


# ---------------------------------------------------------------- smoothdata
def smooth(x, method: str = "movmean", window=None, t=None, factor: float = DEFAULT_FACTOR,
           degree: Optional[int] = None) -> Dict[str, Any]:
    """MATLAB smoothdata(x, method[, window][, 'SmoothingFactor', factor], 'SamplePoints', t[, 'Degree', degree])。
    t＝None → 樣本模式（取樣點 0..N−1、window 是整數樣本數）；否則 window 和 t 同單位。window＝None → 自動視窗。
    回傳 dict：y（和 x 同長度；複數進複數出）、winsz（實際用的視窗）、auto（視窗是不是自動選的）、degree（sgolay 實際用的次數，
    其他方法 None）、warning（None 或 'sgDegreeWarning'：Degree 被自動視窗壓低）。
    錯誤丟 CleanError（identifier 是 MATLAB 的，例如 MATLAB:smoothdata:degreeTooLarge；keyword 是 Signal Analyzer 對話框的訊息代碼）。
    x 含 ±Inf → dsv:smoothdata:infiniteInput；Degree 配非 sgolay → MATLAB:smoothdata:degreeNoSgolay；完全等距軸上 W/Δt 溢位成 Inf 的
    rlowess／rloess → MATLAB:smoothdata:wrongWindowLength；逐窗工作量超過上限 → dsv:clean:tooMuchWork（其他代號見模組說明，MATLAB 實測）。
    t 完全等距（is_exactly_uniform）時走等距快速路徑（結果和 MATLAB 一致）：ws＝W/(t₂−t₁)、窗長 fix(ws)、在整數軸上算（gaussian 一律；局部迴歸只在
    沒有 NaN 時，穩健重擬合用沒截斷的 ws），movmean／movmedian 照取樣點法則（模組說明）。樣本模式（t＝None）與等距路徑的非穩健局部迴歸
    走共用設計矩陣的快速路徑（_uniform_local_fit）；x 先做 2 的冪次縮放（_scale_exponent）。"""
    x = _as_signal(x, "smoothdata")
    _reject_inf(x, "smoothdata")
    n = x.size
    method = str(method).strip().lower()
    if method not in METHODS:
        raise _err("MATLAB:smoothdata:invalidMethod",
                   "Smoothing method must be 'movmean', 'movmedian', 'gaussian', 'lowess', 'loess', 'rlowess', 'rloess', or 'sgolay'.",
                   "平滑方法必須是 movmean、movmedian、gaussian、lowess、loess、rlowess、rloess 或 sgolay。")
    factor = _check_factor(factor)
    if degree is not None:
        kind, dg = _scalar_parts(degree)                       # 代號與訊息都是 R2025a 實測（error_ids.json）
        if kind == "complex":
            raise _err("MATLAB:smoothdata:noComplex", "'Degree' value must be real.", "Degree 必須是實數。")
        if kind == "real" and not math.isfinite(dg):
            raise _err("MATLAB:smoothdata:needsFinites", "'Degree' value must be finite.", "Degree 必須是有限的數。")
        if kind == "bad" or not (dg >= 0 and dg == math.floor(dg)):
            raise _err("MATLAB:smoothdata:negativeDegree", "'Degree' value must be a positive integer.", "Degree 必須是非負整數。")
        if method != "sgolay":
            raise _err("MATLAB:smoothdata:degreeNoSgolay", "'Degree' value is only supported when the method is 'sgolay'.",
                       "只有 sgolay 方法可以指定 Degree。")
        degree = int(dg)
    wv: Optional[float] = None
    if window is not None:
        wv = _check_window(window)
        if t is None and wv != math.floor(wv):
            en, zh = UI_TEXT["smoothWindowDurationErrorSamples"]
            raise _err("smoothWindowDurationErrorSamples", en, zh)
    if t is None:
        tt = np.arange(n, dtype=float)
    else:
        tt = _as_times(t, "smoothdata")
        _check_sample_points(tt, n, "smoothdata")
    res: Dict[str, Any] = {"auto": window is None, "degree": None, "warning": None}
    if n < 2:
        res.update(y=x.copy(), winsz=(1 if t is None else 1.0) if wv is None else (int(wv) if t is None else wv))
        return res
    # MATLAB 的等距快速路徑：t＝None，或 t 完全等距（max(Δt)==min(Δt)；例如 DSV 原生的 x0 + n/sps、sps 為 2 的冪次）。
    # 這時 gaussian 與沒有 NaN 的局部迴歸把 W 換算成樣本 ws＝W/(t₂−t₁)、窗長 fix(ws)，在整數軸 0..N−1 上算（見模組說明）。
    axis_uniform = t is None or is_exactly_uniform(tt)
    taxis = tt if t is None else np.arange(n, dtype=float)
    uniform = bool(np.array_equal(tt, taxis))               # t 本身就是 0..N−1（t_j − t_i＝j − i 精確）→ 取樣點路徑也能共用設計矩陣
    scale = _scale_exponent(x)                                # 2 的冪次縮放：結果逐位元不變、極端尺度不溢位（見 _scale_exponent）
    x = _ldexp(x, -scale)
    winsz = auto_window(x, None if t is None else tt, factor) if wv is None else (int(wv) if t is None else float(wv))
    res["winsz"] = winsz
    w = float(winsz)
    ws = w if t is None else (_uniform_window_samples(w, tt) if axis_uniform else w)   # 等距路徑的樣本窗（t＝None 時就是 W）
    label = METHOD_TEXT.get(method, method)
    if method == "sgolay":
        wl = max_window_points(tt, w)
        d = DEFAULT_DEGREE if degree is None else degree
        if d >= wl:
            if window is None:
                d = wl - 1
                if degree is not None:
                    res["warning"] = WARN_DEGREE_KEYWORD
            elif degree is not None:
                en, zh = UI_TEXT["smoothDegreeTooLargeErrorMsg"]
                raise _err("MATLAB:smoothdata:degreeTooLarge",
                           f"'Degree' value must be less than the largest number of points in any window ({wl}).",
                           f"Degree 必須小於任一視窗裡的最大點數（{wl}）。{zh}", keyword="sgDegreeError")
            else:
                d = wl - 1
        res["degree"] = d
    if method in ("movmean", "movmedian"):
        lo, hi = _window_bounds(tt, w)
        if method == "movmedian":
            _check_work(lo, hi, label)
        y = _movmean(x, lo, hi) if method == "movmean" else _movmedian(x, lo, hi)
    elif method == "gaussian":
        if axis_uniform:                                      # gaussian 的等距路徑（有沒有 NaN 都走）：L＝min(fix(ws), 2N) 個 tap、σ＝ws/5
            if ws < 2:
                y = x.copy()
            else:
                lo, hi = _window_bounds(taxis, float(_fixed_length(ws, 2 * n)))
                _check_work(lo, hi, label)
                y = _gaussian(x, taxis, lo, hi, ws)
        elif 2.0 * float(np.min(np.diff(tt))) > w:
            y = x.copy()
        else:
            lo, hi = _window_bounds(tt, w)
            _check_work(lo, hi, label)
            y = _gaussian(x, tt, lo, hi, w)
    else:
        p = res["degree"] if method == "sgolay" else (1 if method in ("lowess", "rlowess") else 2)
        weighted = method != "sgolay"
        robust = method.startswith("r")
        if axis_uniform and not np.isnan(x).any():            # 局部迴歸的等距路徑（有 NaN 要排除時改走取樣點路徑、t 不換算，和 MATLAB 一致）
            if ws < 2:
                y = x.copy()
            elif robust and not math.isfinite(ws):            # W/Δt 溢位成 Inf：第一次擬合 fix(Inf)→N 可算，但穩健重擬合拿到 Inf 的窗
                raise _err("MATLAB:smoothdata:wrongWindowLength",   # （MATLAB R2025a 實測：W＝1e308、realmax 配 t＝n/1024，uniform_axis2.json）
                           "Window length must be a finite, positive, real scalar or 2-element vector of finite, nonnegative, real scalars.",
                           f"窗長度必須是有限的正實數純量（W／Δt＝{w!r}／{float(tt[1]) - float(tt[0])!r} 溢位成 Inf，穩健方法的重擬合無法使用）。")
            else:
                y = _local_regression(x, taxis, float(_fixed_length(ws, n)), p, weighted, robust, label, True, ws)
        else:
            y = _local_regression(x, tt, w, p, weighted, robust, label, uniform)
    res["y"] = _ldexp(y, scale)
    return res


# ---------------------------------------------------------------- detrend
def _check_design(n: int, k: int) -> None:
    if n * (k + 1) > MAX_DESIGN_ELEMENTS:
        raise _err("dsv:detrend:tooManyBreakpoints",
                   f"Piecewise detrend needs an N×(breakpoints+1) matrix of {n}×{k + 1} = {n * (k + 1)} elements, more than the DSV limit of "
                   f"{MAX_DESIGN_ELEMENTS}; use fewer breakpoints or a shorter signal.",
                   f"分段去趨勢需要 N×(斷點數+1)＝{n}×{k + 1}＝{n * (k + 1)} 個元素的矩陣，超過 DSV 的上限 {MAX_DESIGN_ELEMENTS}；請減少斷點或縮短訊號。")


def breakpoint_indices(t, breakpoints) -> np.ndarray:
    """時間斷點（絕對時間，和 t 同單位）→ 最接近的樣本索引 argmin_j |t_j − b|（0-based；範圍外→第一／最後一個；一樣近取前一個）。
    t 遞增，所以 |t_j − b| 在 b 左邊（b − t_j，捨入是單調的）不增、右邊（t_j − b）不減：最小值在 k−1 或 k（k＝第一個 t_k ≥ b），
    一樣近時取前一個；左邊若有好幾個樣本的距離捨入成同一個值，argmin 取最前面那個，用二分搜尋找（O(K·log N)，不配置 N×K 距離表，
    所以沒有 N 的上限——之前 N > 2²⁴ 的時間模式連「超出尾端、會被忽略」的斷點都被誤拒成 tooManyBreakpoints）。"""
    t = _as_times(t, "detrend")
    _check_sample_points(t, None, "detrend")
    bp = _real_vector(breakpoints)
    if bp is None or not np.all(np.isfinite(bp)):
        en, zh = UI_TEXT["detrendBreakpointErrorTime"]
        raise _err("detrendBreakpointErrorTime", en, zh)
    if bp.size == 0:
        return np.zeros(0, dtype=int)
    n = t.size
    if n == 0:
        ident, en, zh = _SP_TEXT["detrend"]["length"]
        raise _err(ident, en.format(n="at least 1"), zh.format(n="至少 1"))
    k = np.searchsorted(t, bp, side="left")                   # 第一個 t_k ≥ b（n＝全部都比 b 小）
    kl = np.maximum(k - 1, 0)
    kr = np.minimum(k, n - 1)
    with np.errstate(over="ignore"):                          # 斷點和時間軸差超過 realmax 時距離是 Inf（和 argmin 用的 |t_j − b| 相同的 IEEE 結果）
        dl = bp - t[kl]
        dr = t[kr] - bp
        left = (k > 0) & ((k == n) | (dl <= dr))
        lo = np.zeros(bp.size, dtype=np.int64)
        hi = kl.astype(np.int64)
        while True:                                           # 左邊：第一個 b − t_j ≤ dl 的 j（b − t_j 對 j 不增）
            act = left & (lo < hi)
            if not act.any():
                break
            mid = (lo + hi) // 2
            ok = (bp - t[mid]) <= dl
            hi = np.where(act & ok, mid, hi)
            lo = np.where(act & ~ok, mid + 1, lo)
    return np.where(left, lo, kr).astype(int)


def _detrend_linear(x: np.ndarray) -> np.ndarray:
    """detrend(x, 1)（沒有斷點）：對 a＝n/(N−1) 的最小平方直線，用閉合式（O(N)、不配置 N×2 設計矩陣，所以沒有上限）：
    ā＝1/2、Σ(a−ā)²＝N(N+1)/(12(N−1))（精確值），斜率＝Σ(a−ā)(x−x̄)/Σ(a−ā)²，趨勢＝x̄ + 斜率·(a−ā)。
    和 MATLAB 的 QR 最小平方解只差捨入（參考資料 D 組逐點一致）；複數的實虛部一起算（線性運算）。"""
    n = x.size
    a = np.arange(n, dtype=float) / float(n - 1) - 0.5
    xm = np.mean(x)
    slope = np.sum(a * (x - xm)) / (n * (n + 1.0) / (12.0 * (n - 1.0)))
    return x - (xm + slope * a)


def _detrend_piecewise(x: np.ndarray, idx0: np.ndarray) -> np.ndarray:
    """detrend(x, 1, ix)：連續的分段線性趨勢（斷點 0-based 索引），最小平方擬合後相減。
    有效斷點只剩 0（沒給、全被忽略）→ _detrend_linear（不受 MAX_DESIGN_ELEMENTS 限制；之前 N > 2²³ 的 detrend(x,'linear') 會被誤拒成
    tooManyBreakpoints）；真的有斷點才檢查 N×(斷點數+1) 的設計矩陣大小。"""
    n = x.size
    if n < 2:
        return np.zeros_like(x)
    bp = np.unique(np.concatenate([[0.0], np.asarray(idx0, dtype=float)]))
    if bp.size > 1:
        bp = bp[(bp >= 0) & (bp < n - 1)]
    if bp.size <= 1:
        return _detrend_linear(x)
    _check_design(n, int(bp.size))
    scale = float(n - 1)
    a = np.arange(n, dtype=float) / scale
    W = np.column_stack([np.maximum(a[:, None] - bp[None, :] / scale, 0.0), np.ones(n)])
    if np.iscomplexobj(x):
        B = np.column_stack([x.real, x.imag])
    else:
        B = x[:, None]
    p = np.linalg.lstsq(W, B, rcond=None)[0]
    fit = W @ p
    if np.iscomplexobj(x):
        return x - (fit[:, 0] + 1j * fit[:, 1])
    return x - fit[:, 0]


def detrend(x, method: str = "linear", breakpoints: Optional[Sequence[float]] = None, t=None) -> np.ndarray:
    """MATLAB detrend：'constant'＝x − mean、'linear'＝detrend(x,1)、'piecewiselinear'＝detrend(x,1,ix)。
    breakpoints：t＝None → 0-based 樣本號（非負整數）；t 給了 → 絕對時間（和 t 同單位），取最接近的樣本。
    'polynomial' 不做（R2025a 面板沒有）→ CleanError。NaN／Inf 會讓整個輸出變 NaN（MATLAB 沒加 'omitnan'）。"""
    x = _as_signal(x, "detrend")
    m = str(method).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    if m == "piecewise":
        m = "piecewiselinear"
    if m == "polynomial":
        raise _err("dsv:detrend:polynomialNotOffered",
                   "Polynomial detrending is not offered by the Signal Analyzer R2025a Detrend panel (MATLAB returns the data unchanged).",
                   "Signal Analyzer R2025a 的 Detrend 面板沒有多項式去趨勢（MATLAB 會把資料原樣傳回），所以不提供。")
    if m not in DETREND_METHODS:
        raise _err("dsv:detrend:invalidMethod", "Detrend method must be 'constant', 'linear', or 'piecewiselinear'.",
                   "去趨勢方法必須是 constant、linear 或 piecewiselinear。")
    idx0 = np.zeros(0, dtype=int)
    if m == "piecewiselinear" and breakpoints is not None:
        bp = _real_vector(breakpoints)
        if t is None:
            if bp is None or not np.all(np.isfinite(bp) & (bp >= 0) & (bp == np.floor(bp))):
                en, zh = UI_TEXT["detrendBreakpointErrorSamples"]
                raise _err("detrendBreakpointErrorSamples", en, zh)
            idx0 = bp[bp < x.size].astype(int)                # ≥ N 的斷點本來就不算（最後一個樣本之後）；先丟掉才不會在 1e300 轉 int 時冒警告
        else:
            if bp is None or not np.all(np.isfinite(bp)):
                en, zh = UI_TEXT["detrendBreakpointErrorTime"]
                raise _err("detrendBreakpointErrorTime", en, zh)
            tt = _as_times(t, "detrend")
            _check_sample_points(tt, x.size, "detrend")
            if bp.size:
                idx0 = breakpoint_indices(tt, bp)
    if x.size == 0:
        return x.copy()
    if not np.all(np.isfinite(x)):
        return np.full(x.shape, np.nan + (1j * np.nan if np.iscomplexobj(x) else 0.0), dtype=x.dtype)
    scale = _scale_exponent(x)                                # 2 的冪次縮放：平均與最小平方都是 x 的一次齊次式，結果逐位元不變
    x = _ldexp(x, -scale)
    if m == "constant":
        return _ldexp(x - np.mean(x), scale)
    return _ldexp(_detrend_piecewise(x, idx0), scale)


# ---------------------------------------------------------------- selftest
def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/smooth_detrend/reference.json；研究目錄的 make_reference.m 產生：
    每組同時跑 Signal Analyzer 與對應的 smoothdata／detrend 呼叫，兩者 maxdiff 0）。
    S125 是 MATLAB 自己的數值垃圾（見模組說明「已知差異」），單獨用一個檢查釘住它的數字；其他 232 組都要一致。"""
    import json
    import os
    import time as _time
    import warnings
    path = os.path.join(ref_dir, "smooth_detrend", "reference.json")
    if not os.path.isfile(path):
        check(True, "（沒有 tests/matlab_ref/smooth_detrend/reference.json：略過 MATLAB 平滑／去趨勢比對）")
        return
    with open(path, encoding="utf-8") as fh:
        R = json.load(fh)

    def arr(v):
        return np.asarray(v, dtype=float)

    sig: Dict[str, Tuple[np.ndarray, np.ndarray, str]] = {}
    for s in R["signals"]:
        xr, xi = arr(s["x_re"]), arr(s["x_im"])
        sig[s["name"]] = (arr(s["t"]), xr + 1j * xi if np.any(xi != 0) else xr, s["mode"])

    def ref_y(c):
        return arr(c["app_re"]) + 1j * arr(c["app_im"])

    def diff_info(y, ref, x):
        # rtol 1e-12；atol 取輸入幅度的 1e-12（接近 0 的輸出，例如相鄰斷點 D13 的去趨勢殘差 ~1e-12 相對 1e-13，只剩捨入雜訊）。
        # 第二輪的 1e-9／1e-11 比模組實際達到的鬆（審查者量到全部 ≤ 3.1e-15），第三輪收緊；之後只能再收緊、不能放鬆
        y, ref = np.asarray(y, dtype=complex), np.asarray(ref, dtype=complex)
        if y.shape != ref.shape:
            return False, f"shape {y.shape} vs {ref.shape}"
        ok = np.allclose(y, ref, rtol=1e-12, atol=1e-12 * float(np.max(np.abs(x))), equal_nan=True)
        if ok:
            return True, ""
        e = np.abs(y - ref)
        e[np.isnan(e)] = np.inf
        i = int(np.argmax(e))
        return False, f"i={i} mine={y[i]:.17g} matlab={ref[i]:.17g} |diff|={e[i]:.3g}"

    # 時間軸
    tA, _, _ = sig["A_time"]
    tS, _, _ = sig["A_samples"]
    ok = (np.array_equal(time_vector(200, 100.0, 0.37), tA) and np.array_equal(np.arange(200.0), tS)
          and not is_exactly_uniform(tA) and is_exactly_uniform(tS) and not is_exactly_uniform(sig["A_nonuniform"][0]))
    check(ok, "時間軸 vs MATLAB：time_vector(200, fs=100, t0=0.37) 和 MATLAB 的 t0 + n/fs 逐位元相同；它不是「完全等距」（走取樣點路徑），"
              "樣本軸 0..N−1 是")

    # 平滑：依方法分組；S125（rloess、A_time、0.075 s）拿出來當「已知差異」單獨檢查
    groups: Dict[str, list] = {m: [] for m in METHODS}
    groups["sgolay Degree 變化"] = []
    groups["錯誤"] = []
    known: Dict[int, dict] = {}
    for k, c in enumerate(R["smooth"]):
        if c["app_ok"] == 0:
            groups["錯誤"].append((k, c))
        elif c["method"] == "rloess" and c["signal"] == "A_time" and c["window"] == 0.075:
            known[k] = c
        elif c["method"] == "sgolay" and (c["degree"] != "Auto" or k >= 152):
            groups["sgolay Degree 變化"].append((k, c))
        else:
            groups[c["method"]].append((k, c))

    def run_case(c):
        t, x, mode = sig[c["signal"]]
        window = None if (c["window"] == "Auto" or c["windowSpecType"] != "duration") else c["window"]
        factor = c["smoothingFactor"] if c["windowSpecType"] == "smoothingfactor" else DEFAULT_FACTOR
        degree = None if c["degree"] == "Auto" else int(c["degree"])
        return smooth(x, c["method"], window, None if mode == "samples" else t, factor, degree)

    matched: Dict[str, int] = {}
    for name, cases in groups.items():
        if name == "錯誤":
            continue
        bad = []
        for k, c in cases:
            try:
                r = run_case(c)
            except CleanError as e:
                bad.append(f"S{k + 1:03d}（{c['note']}）丟了 {e.identifier}")
                continue
            ok, info = diff_info(r["y"], ref_y(c), sig[c["signal"]][1])
            wref = c["direct_winsz"]
            okw = float(r["winsz"]) == float(wref)                        # 164 組全部逐位元相同（k·Δt 和 MATLAB 同一個乘法）
            warn = c["app_exception"] or None
            okd = (r["warning"] or None) == warn
            if not (ok and okw and okd):
                bad.append(f"S{k + 1:03d}（{c['note']}）" + ("" if ok else f" y：{info}") + ("" if okw else f" winsz {r['winsz']}≠{wref}")
                           + ("" if okd else f" warning {r['warning']}≠{warn}"))
        matched[name] = len(cases) - len(bad)
        label = METHOD_TEXT.get(name, name)
        kinds = "樣本模式 Auto／7／8／1／400、SmoothingFactor 0.1／0.6／0／1；時間模式 Auto／0.075／0.08（邊界 tie）／0.25 s、SF 0.4；非均勻 Auto／0.09 s／SF 0.7；複數 9、複數時間 Auto" \
            if name in METHODS else "degree 1／3／5（偶數窗）／10＝窗−1、Auto 窗與 SF 窗的 degree 壓低（sgDegreeWarning）、時間 0.11 s degree 3、Auto 窗 degree 4、非均勻 degree 4、窗 3／2 的 Auto degree"
        if name == "rloess":
            kinds = kinds.replace("時間模式 Auto／0.075／0.08", "時間模式 Auto／0.08") + "；另含 S166 窗 5（兩端秩虧）；時間模式 0.075 s 的 S125 是 MATLAB 數值垃圾，列在下一項「已知差異」"
        check(not bad, f"平滑 vs MATLAB smoothdata（{label}，{len(cases)} 組：{kinds}）：y、winsz、warning 逐筆一致"
                       + (f"（不一致 {len(bad)}：{'；'.join(bad[:3])}）" if bad else ""))

    # 已知差異 S125：MATLAB 自己在 1e-41 的 tricube 權重樞軸上算出 1e22～1e25 的垃圾；下面釘住文件記載的每個數字
    facts = []
    if len(known) != 1:
        facts.append(f"參考資料裡 rloess／A_time／0.075 s 的案例數 {len(known)}≠1")
    else:
        (k125, c125), = known.items()
        t, x, _ = sig["A_time"]
        x = x.real
        ref = ref_y(c125).real
        y = smooth(x, "rloess", 0.075, t)["y"].real
        garbage = [118, 119, 120, 169, 170]
        matlab_vals = [-7.6895145423134498e+22, 3.3701949769860527e+24, 5.6418766024446417e+20, 1.5026662865173247e+22, 1.0521674216435359e+25]
        dsv_vals = [1.6327987001071513, 1.4543722047079106, 1.1636528976830822, 2.9556896313841241, 2.8287908936760857]
        if not (k125 == 124 and c125["maxdiff"] == 0 and not np.any(arr(c125["app_im"]))):
            facts.append(f"S{k125 + 1} 不是 S125 或 app≠smoothdata（maxdiff {c125['maxdiff']}）")
        big = np.flatnonzero(np.abs(ref) > 1e18).tolist()
        if big != garbage:
            facts.append(f"MATLAB 垃圾索引 {big}≠{garbage}")
        for i, mv, dv in zip(garbage, matlab_vals, dsv_vals):
            if not math.isclose(float(ref[i]), mv, rel_tol=1e-12):
                facts.append(f"MATLAB y[{i}]={ref[i]:.17g}≠{mv:.17g}")
            if not math.isclose(float(y[i]), dv, rel_tol=1e-12):
                facts.append(f"DSV y[{i}]={y[i]:.17g}≠{dv:.17g}")
        if not (np.all(np.isfinite(y)) and math.isclose(float(np.max(np.abs(y))), 4.20036223331149, rel_tol=1e-12)
                and math.isclose(float(np.max(np.abs(x))), 6.656228595814383, rel_tol=1e-12)):
            facts.append(f"DSV 輸出應全部有限、max|y|=4.20036（{np.max(np.abs(y)):.17g}）、max|x|=6.6562")
        same = np.flatnonzero(np.isclose(y, ref, rtol=1e-12, atol=1e-12 * float(np.max(np.abs(x))))).tolist()
        if same != [172]:
            facts.append(f"1e-12 一致的索引 {same}≠[172]")
        other = np.setdiff1d(np.arange(x.size), garbage)
        e = np.abs(y[other] - ref[other])
        if not (math.isclose(float(e.max()), 0.23306532753627085, rel_tol=1e-12) and int(other[int(np.argmax(e))]) == 168):
            facts.append(f"非垃圾點最大差 {e.max():.17g}@{other[int(np.argmax(e))]}≠0.2330653275@168")
        lo, hi = _window_bounds(t, 0.075)
        tiny = 0
        far170 = None
        for i in range(x.size):
            d = t[lo[i]:hi[i]] - t[i]
            q = np.abs(d) / np.abs(d).max()
            wt = (1.0 - q ** 3) ** 3
            tiny += int(np.any((wt > 0) & (wt < 1e-30)))
            if i == 170:
                far170 = (list(range(lo[i] - i, hi[i] - i)), float(wt[0]))
        if not (tiny == 140 and far170[0] == [-3, -2, -1, 0, 1, 2, 3] and math.isclose(far170[1], 8.692593614333116e-41, rel_tol=1e-12)):
            facts.append(f"根因：tiny 權重窗數 {tiny}≠140、i=170 窗 {far170}")
        outl = np.flatnonzero(np.abs(x - smooth(x, "movmedian", 7)["y"].real) > 3).tolist()
        if outl != [36, 119, 170]:
            facts.append(f"離群值索引 {outl}≠[36, 119, 170]")
        s087 = [c for c in R["smooth"] if c["method"] == "loess" and c["signal"] == "A_time" and c["window"] == 0.075]
        e087 = float(np.max(np.abs(smooth(x, "loess", 0.075, t)["y"].real - arr(s087[0]["app_re"])))) if len(s087) == 1 else math.inf
        if not e087 <= 1e-14:
            facts.append(f"同窗非穩健 loess（S087）差 {e087:.3g} > 1e-14")
        if matched.get("rloess") != 19 or len(groups["rloess"]) != 19:
            facts.append(f"其他 rloess 一致數 {matched.get('rloess')}/{len(groups['rloess'])}≠19/19")
    check(not facts, "已知差異 S125（rloess、時間模式 0.075 s＝7 樣本、訊號 A 離群值 i=36/119/170）：MATLAB 自己（app＝smoothdata，maxdiff 0）在 "
                     "i=118/119/120/169/170 輸出 −7.69e22／3.37e24／5.64e20／1.50e22／1.05e25（|x|≤6.66）＝1e-41 tricube 權重樞軸上的數值垃圾；"
                     "DSV 把相對窗內最大權重 < 1e-30 的權重當 0（WEIGHT_FLOOR），那些窗降為 2 點、次數 1，得到有限且不隨 BLAS 變的 "
                     "1.633／1.454／1.164／2.956／2.829（|y|≤4.20）；垃圾殘差改變 median(r) 排名 → 其他 195 點差到 0.233（i=168）、只有 i=172 一致；"
                     "根因重現：140/200 個窗最遠點 tricube ≈8.69e-41 而非 0（i=170 窗偏移 −3..3）；同窗非穩健 loess S087 ≤1e-14、"
                     "其他 19 組 rloess（含樣本模式 S116／S166）逐筆一致——無法以 1e-12 重現 MATLAB 的捨入垃圾，照實列為已知差異"
                     + (f"（文件記載的數字對不上：{facts}）" if facts else ""))

    bad = []
    for k, c in groups["錯誤"]:
        try:
            run_case(c)
            bad.append(f"S{k + 1:03d} 沒丟錯誤")
        except CleanError as e:
            if not (e.identifier == c["direct_error"] and e.keyword == c["app_exception"] and e.zh):
                bad.append(f"S{k + 1:03d} {e.identifier}/{e.keyword}≠{c['direct_error']}/{c['app_exception']}")
    check(not bad, f"平滑錯誤 vs MATLAB（{len(groups['錯誤'])} 組：sgolay 指定窗 5 與 0.05 s 配 degree 6）：丟 CleanError，identifier "
                   f"MATLAB:smoothdata:degreeTooLarge、對話框訊息代碼一致、附繁中訊息" + (f"（不一致：{bad}）" if bad else ""))

    # 自動視窗表
    bad = []
    for a in R["auto_window"]:
        t, x, mode = sig[a["signal"]]
        w = auto_window(x, None if mode == "samples" else t, a["smoothingFactor"])
        if float(w) != float(a["winsz"]):                                 # 45 組全部逐位元相同
            bad.append(f"{a['signal']} f={a['smoothingFactor']}: {w}≠{a['winsz']}")
    check(not bad, f"自動視窗 vs MATLAB smoothdata 的 winsz（{len(R['auto_window'])} 組：SmoothingFactor 0／0.05／0.1／0.25／0.4／0.6／0.7／0.9／1 × "
                   f"樣本／時間／非均勻／複數樣本／複數時間；FFT 能量法則＋pchip 重取樣＋linspace）一致" + (f"（不一致：{bad[:4]}）" if bad else ""))

    # 去趨勢
    dgroups = {"常數／線性（時間與樣本模式、分段但無斷點）": [], "分段線性（樣本斷點）": [], "分段線性（時間斷點）": [], "複數": [], "polynomial": []}
    for k, c in enumerate(R["detrend"]):
        if c["method"] == "polynomial":
            dgroups["polynomial"].append((k, c))
        elif c["signal"].startswith("DC"):
            dgroups["複數"].append((k, c))
        elif c["method"] != "piecewiselinear" or not c["breakpoints"]:
            dgroups["常數／線性（時間與樣本模式、分段但無斷點）"].append((k, c))
        elif c["signal"].endswith("time"):
            dgroups["分段線性（時間斷點）"].append((k, c))
        else:
            dgroups["分段線性（樣本斷點）"].append((k, c))
    notes = {"分段線性（樣本斷點）": "1 個、3 個、未排序、重複、斷點 0、最後一個樣本（忽略）、超出尾端（忽略）、相鄰 1,2",
             "分段線性（時間斷點）": "絕對時間 1.37 s（含 t0 0.37）、3 個、非格點→最近樣本、起點前→樣本 0、終點後→最後（忽略）、負值",
             "複數": "linear 與分段 60,130（實虛部一起解）", "常數／線性（時間與樣本模式、分段但無斷點）": "detrend(x,0)、detrend(x,1)"}
    for name, cases in dgroups.items():
        bad = []
        for k, c in cases:
            t, x, mode = sig[c["signal"]]
            bp = c["breakpoints"]
            bp = [] if bp in ([], None) else (bp if isinstance(bp, list) else [bp])
            if name == "polynomial":
                try:
                    detrend(x, "polynomial")
                    bad.append(f"D{k + 1:02d} 沒丟錯誤")
                except CleanError:
                    pass
                ok, info = diff_info(x, ref_y(c), x)
                if not ok:
                    bad.append(f"D{k + 1:02d} app 輸出不等於輸入：{info}")
                continue
            y = detrend(x, c["method"], bp or None, None if mode == "samples" else t)
            ok, info = diff_info(y, ref_y(c), x)
            if not ok:
                bad.append(f"D{k + 1:02d}（{c['note']}）{info}")
            if bp and mode != "samples":
                ix = breakpoint_indices(t, bp) + 1
                ref_ix = np.atleast_1d(np.asarray(c["index_breakpoints_1based"], dtype=int))
                if not np.array_equal(ix, ref_ix):
                    bad.append(f"D{k + 1:02d} 斷點索引 {ix.tolist()}≠{ref_ix.tolist()}")
        if name == "polynomial":
            msg = f"去趨勢 Polynomial（{len(cases)} 組，R2025a 面板沒有）：Signal Analyzer 把資料原樣傳回；detrend(…,'polynomial') 丟 CleanError"
        else:
            msg = f"去趨勢 vs MATLAB detrend（{name}，{len(cases)} 組：{notes[name]}）逐點一致"
        check(not bad, msg + (f"（不一致：{bad[:3]}）" if bad else ""))

    # 定義層級的邊界行為（沒有 MATLAB 參考資料；照 smoothdata／detrend 文件：'omitnan'、N＜2 原樣、窗比訊號長＝全域、錯誤輸入）
    bad = []
    v = np.array([1.0, np.nan, 3.0])
    for m_, want in (("movmean", [1.0, 2.0, 3.0]), ("movmedian", [1.0, 2.0, 3.0]), ("gaussian", [1.0, 2.0, 3.0])):
        got = smooth(v, m_, 3)["y"]
        if not np.allclose(got, want, rtol=1e-12, atol=1e-12):
            bad.append(f"{m_} NaN 排除 {got.tolist()}")
    if not np.isnan(smooth(np.array([np.nan, np.nan, 1.0]), "movmean", 2)["y"][0]):
        bad.append("整窗 NaN 應為 NaN")
    one = smooth(np.array([2.5]), "lowess")
    if not (one["y"].tolist() == [2.5] and one["winsz"] == 1):
        bad.append("N＝1 應原樣傳回")
    tt3 = time_vector(50, 10.0, 1.0)
    xx3 = np.arange(50.0)
    if not np.allclose(smooth(xx3, "movmean", 100.0, tt3)["y"], xx3.mean(), rtol=1e-12):
        bad.append("窗比訊號長時 movmean 應為全域平均")
    if not np.allclose(smooth(xx3, "loess", 0.5, tt3)["y"], xx3, rtol=1e-12, atol=1e-12):
        bad.append("直線的 loess 應還是直線")
    if auto_window(np.ones(100)) != 1 or auto_window(np.ones(100), np.arange(100.0) * 0.5) != 0.5:
        bad.append("常數訊號的自動視窗應為 1 個樣本")
    if not np.allclose(detrend(2.0 * xx3 + 1.0), 0.0, atol=1e-12) or not np.all(np.isnan(detrend(v))):
        bad.append("detrend：直線應歸零、含 NaN 應全 NaN")
    for kw in (dict(method="foo"), dict(factor=1.5), dict(window=0), dict(window=2.5), dict(method="sgolay", degree=-1)):
        try:
            smooth(xx3, **kw)
            bad.append(f"smooth{kw} 沒丟錯誤")
        except CleanError:
            pass
    for kw in (dict(method="piecewiselinear", breakpoints=[-1]), dict(method="polynomial"), dict(method="piecewiselinear", breakpoints=[1.5])):
        try:
            detrend(xx3, **kw)
            bad.append(f"detrend{kw} 沒丟錯誤")
        except CleanError:
            pass
    for fn, arg in ((check_finite, v), (check_uniform, sig["A_nonuniform"][0])):
        try:
            fn(arg)
            bad.append(f"{fn.__name__} 沒丟錯誤")
        except CleanError as e:
            if not (e.zh and str(e)):
                bad.append(f"{fn.__name__} 訊息不完整")
    check(not bad, "定義層級邊界：NaN 以 'omitnan' 排除（整窗 NaN→NaN）、N＝1 原樣、窗比訊號長→全域平均、直線的 loess／detrend 不變／歸零、"
                   "常數訊號自動視窗 1、錯誤輸入（方法、因子、窗 0／非整數、負次數、負斷點、polynomial、NaN 訊號、非均勻 detrend）都丟 CleanError"
                   + (f"（問題：{bad}）" if bad else ""))

    # 輸入檢查：非數值／複數／二維 → CleanError（不是 numpy 的 ValueError／TypeError）；全 NaN 的穩健迴歸不冒 RuntimeWarning；
    # detrend 時間軸用 dsv:detrend: 代號；time_vector 參數檢查；工作量上限很快就拒絕
    bad = []
    x7 = np.arange(7.0)
    t7 = time_vector(7, 10.0)
    cases_err = [
        ("smooth x 字串", lambda: smooth(np.array(["a", "b", "c"]), "movmean", 3), "MATLAB:smoothdata:badArray"),
        ("smooth x 物件含 None", lambda: smooth(np.array([1, None, 3], dtype=object), "movmean", 3), "MATLAB:smoothdata:badArray"),
        ("smooth x 二維", lambda: smooth(np.arange(6.0).reshape(3, 2), "movmean", 3), "dsv:smoothdata:notVector"),
        ("smooth window 'abc'", lambda: smooth(x7, "movmean", "abc"), "MATLAB:smoothdata:invalidWinsize"),
        ("smooth window 複數", lambda: smooth(x7, "movmean", 3 + 1j), "MATLAB:smoothdata:noComplexWindows"),
        ("smooth window [3,4]", lambda: smooth(x7, "movmean", [3, 4]), "MATLAB:smoothdata:invalidWinsize"),
        ("smooth window False", lambda: smooth(x7, "movmean", False), "MATLAB:smoothdata:invalidWinsize"),
        ("smooth window NaN", lambda: smooth(x7, "movmean", math.nan), "MATLAB:smoothdata:needsFiniteWindows"),
        ("smooth window Inf", lambda: smooth(x7, "rlowess", math.inf), "MATLAB:smoothdata:needsFiniteWindows"),
        ("smooth window 0", lambda: smooth(x7, "movmean", 0), "MATLAB:smoothdata:invalidWinsize"),
        ("smooth window [3,4,5]", lambda: smooth(x7, "movmean", [3, 4, 5]), "MATLAB:smoothdata:invalidWinsize"),
        ("smooth factor 'abc'", lambda: smooth(x7, "movmean", None, None, "abc"), "MATLAB:smoothdata:invalidSmoothingFactor"),
        ("smooth factor 複數", lambda: smooth(x7, "movmean", None, None, 0.5j), "MATLAB:smoothdata:noComplex"),
        ("smooth factor 1.5", lambda: smooth(x7, "movmean", None, None, 1.5), "MATLAB:smoothdata:invalidSmoothingFactor"),
        ("smooth factor NaN", lambda: smooth(x7, "movmean", None, None, math.nan), "MATLAB:smoothdata:invalidSmoothingFactor"),
        ("smooth factor [0.1,0.2]", lambda: smooth(x7, "movmean", None, None, [0.1, 0.2]), "MATLAB:smoothdata:invalidSmoothingFactor"),
        ("smooth degree NaN", lambda: smooth(x7, "sgolay", 5, None, 0.25, math.nan), "MATLAB:smoothdata:needsFinites"),
        ("smooth degree Inf", lambda: smooth(x7, "sgolay", 5, None, 0.25, math.inf), "MATLAB:smoothdata:needsFinites"),
        ("smooth degree 複數", lambda: smooth(x7, "sgolay", 5, None, 0.25, 2j), "MATLAB:smoothdata:noComplex"),
        ("smooth degree True", lambda: smooth(x7, "sgolay", 5, None, 0.25, True), "MATLAB:smoothdata:negativeDegree"),
        ("smooth degree [1,2]", lambda: smooth(x7, "sgolay", 5, None, 0.25, [1, 2]), "MATLAB:smoothdata:negativeDegree"),
        ("smooth degree −1", lambda: smooth(x7, "sgolay", 5, None, 0.25, -1), "MATLAB:smoothdata:negativeDegree"),
        ("smooth method foo", lambda: smooth(x7, "foo"), "MATLAB:smoothdata:invalidMethod"),
        ("smooth degree 'abc'", lambda: smooth(x7, "sgolay", 5, None, 0.25, "abc"), "MATLAB:smoothdata:negativeDegree"),
        ("smooth degree 2.5", lambda: smooth(x7, "sgolay", 5, None, 0.25, 2.5), "MATLAB:smoothdata:negativeDegree"),
        ("smooth t 字串", lambda: smooth(x7, "movmean", 0.3, np.array(list("abcdefg"))), "MATLAB:samplePoints:SamplePointsInvalidDatatype"),
        ("smooth t 複數", lambda: smooth(x7, "movmean", 0.3, t7 + 1j), "MATLAB:samplePoints:SamplePointsComplex"),
        ("smooth t 二維", lambda: smooth(x7, "movmean", 0.3, np.arange(14.0).reshape(7, 2)), "MATLAB:samplePoints:SamplePointsInvalidDatatype"),
        ("smooth t 長度不符", lambda: smooth(x7, "movmean", 0.3, t7[:5]), "MATLAB:samplePoints:SamplePointsLength"),
        ("smooth t 含 NaN", lambda: smooth(x7, "movmean", 0.3, np.r_[t7[:6], np.nan]), "MATLAB:samplePoints:SamplePointsNonFinite"),
        ("smooth t 遞減", lambda: smooth(x7, "movmean", 0.3, t7[::-1]), "MATLAB:samplePoints:SamplePointsSorted"),
        ("smooth t 重複", lambda: smooth(x7, "movmean", 0.3, np.r_[t7[:6], t7[5]]), "MATLAB:samplePoints:SamplePointsDuplicate"),
        ("smooth t 含 Inf", lambda: smooth(x7, "movmean", 0.3, np.r_[t7[:6], np.inf]), "MATLAB:samplePoints:SamplePointsNonFinite"),
        ("smooth t bool", lambda: smooth(x7, "movmean", 0.3, np.ones(7, dtype=bool)), "MATLAB:samplePoints:SamplePointsInvalidDatatype"),
        ("auto_window x 字串", lambda: auto_window(np.array(["a", "b"])), "MATLAB:smoothdata:badArray"),
        ("auto_window x 二維", lambda: auto_window(np.arange(6.0).reshape(3, 2)), "dsv:smoothdata:notVector"),
        ("max_window_points t 二維", lambda: max_window_points(np.arange(14.0).reshape(7, 2), 0.3), "MATLAB:samplePoints:SamplePointsInvalidDatatype"),
        ("is_exactly_uniform 字串", lambda: is_exactly_uniform(np.array(["a", "b"])), "MATLAB:samplePoints:SamplePointsInvalidDatatype"),
        ("check_finite 字串", lambda: check_finite(np.array(["a"])), "dsv:clean:nonNumericInput"),
        ("check_uniform 二維", lambda: check_uniform(np.arange(14.0).reshape(7, 2)), "dsv:detrend:timeVectorLength"),
        ("detrend x 二維", lambda: detrend(np.arange(6.0).reshape(3, 2)), "dsv:detrend:notVector"),
        ("detrend x 字串", lambda: detrend(np.array(["a", "b"])), "MATLAB:detrend:InvalidFirstInput"),
        ("detrend 斷點 'a'（樣本）", lambda: detrend(x7, "piecewiselinear", ["a"]), "detrendBreakpointErrorSamples"),
        ("detrend 斷點 'a'（時間）", lambda: detrend(x7, "piecewiselinear", ["a"], t7), "detrendBreakpointErrorTime"),
        ("detrend 斷點複數", lambda: detrend(x7, "piecewiselinear", [1 + 1j]), "detrendBreakpointErrorSamples"),
        ("detrend 斷點 NaN（時間）", lambda: detrend(x7, "piecewiselinear", [np.nan], t7), "detrendBreakpointErrorTime"),
        ("detrend t 長度不符", lambda: detrend(x7, "piecewiselinear", [0.3], t7[:5]), "dsv:detrend:timeVectorLength"),
        ("detrend t 複數", lambda: detrend(x7, "piecewiselinear", [0.3], t7.astype(complex)), "dsv:detrend:timeVectorNonNumeric"),
        ("detrend t 遞減", lambda: detrend(x7, "piecewiselinear", [0.3], t7[::-1]), "dsv:detrend:timeVectorSorted"),
        ("detrend t 重複", lambda: detrend(x7, "piecewiselinear", [0.3], np.r_[t7[:6], t7[5]]), "dsv:detrend:timeVectorDuplicate"),
        ("detrend t 含 Inf", lambda: detrend(x7, "piecewiselinear", [0.3], np.r_[t7[:6], np.inf]), "dsv:detrend:timeVectorNonFinite"),
        ("breakpoint_indices t 遞減", lambda: breakpoint_indices(t7[::-1], [0.3]), "dsv:detrend:timeVectorSorted"),
        ("breakpoint_indices 斷點字串", lambda: breakpoint_indices(t7, "0.3"), "detrendBreakpointErrorTime"),
        ("breakpoint_indices 斷點物件含字串", lambda: breakpoint_indices(t7, np.array([0.3, "a"], dtype=object)), "detrendBreakpointErrorTime"),
        ("breakpoint_indices t 物件含 None", lambda: breakpoint_indices(np.array([0.0, None, 0.2], dtype=object), [0.1]), "dsv:detrend:timeVectorNonNumeric"),
        ("time_vector fs=0", lambda: time_vector(5, 0.0), "dsv:clean:invalidTimeVector"),
        ("time_vector fs<0", lambda: time_vector(5, -1.0), "dsv:clean:invalidTimeVector"),
        ("time_vector fs=NaN", lambda: time_vector(5, float("nan")), "dsv:clean:invalidTimeVector"),
        ("time_vector n=-1", lambda: time_vector(-1, 1.0), "dsv:clean:invalidTimeVector"),
        ("time_vector n=2.5", lambda: time_vector(2.5, 1.0), "dsv:clean:invalidTimeVector"),
        ("time_vector t0=Inf", lambda: time_vector(5, 1.0, math.inf), "dsv:clean:invalidTimeVector"),
        # 第二輪：Inf 訊號、Degree 配非 sgolay、時間軸跨度溢位、time_vector 溢位
        ("smooth x 含 Inf", lambda: smooth(np.array([1.0, np.inf, 3.0]), "movmean", 3), "dsv:smoothdata:infiniteInput"),
        ("smooth x 複數含 Inf", lambda: smooth(np.array([1.0, 1j * np.inf, 3.0]), "movmean", 3), "dsv:smoothdata:infiniteInput"),
        ("auto_window x 含 −Inf", lambda: auto_window(np.array([1.0, -np.inf, 3.0])), "dsv:smoothdata:infiniteInput"),
        ("smooth degree 配 movmean", lambda: smooth(x7, "movmean", 3, degree=4), "MATLAB:smoothdata:degreeNoSgolay"),
        ("smooth degree 配 loess（時間）", lambda: smooth(x7, "loess", 0.3, t7, degree=2), "MATLAB:smoothdata:degreeNoSgolay"),
        ("smooth t 跨度溢位", lambda: smooth(np.array([1.0, 2.0, 3.0]), "movmean", 1e308, np.array([-1e308, 0.0, 1e308])),
         "dsv:smoothdata:samplePointsSpanOverflow"),
        ("auto_window t 跨度溢位", lambda: auto_window(np.array([1.0, 2.0, 3.0]), np.array([-1e308, 0.0, 1e308])), "dsv:smoothdata:samplePointsSpanOverflow"),
        ("is_exactly_uniform 含 Inf", lambda: is_exactly_uniform(np.array([0.0, 1.0, np.inf])), "MATLAB:samplePoints:SamplePointsNonFinite"),
        ("is_exactly_uniform 跨度溢位", lambda: is_exactly_uniform(np.array([-1e308, 0.0, 1e308])), "dsv:smoothdata:samplePointsSpanOverflow"),
        ("detrend t 跨度溢位", lambda: detrend(np.array([1.0, 2.0, 3.0]), "piecewiselinear", [0.0], np.array([-1e308, 0.0, 1e308])),
         "dsv:detrend:timeVectorSpanOverflow"),
        ("breakpoint_indices t 跨度溢位", lambda: breakpoint_indices(np.array([-1e308, 1e308]), [1e308]), "dsv:detrend:timeVectorSpanOverflow"),
        ("check_uniform t 跨度溢位", lambda: check_uniform(np.array([-1e308, 0.0, 1e308])), "dsv:detrend:timeVectorSpanOverflow"),
        ("check_uniform 含 Inf", lambda: check_uniform(np.array([0.0, 1.0, np.inf])), "dsv:detrend:timeVectorNonFinite"),
        ("time_vector fs=1e-308（溢位）", lambda: time_vector(5, 1e-308), "dsv:clean:invalidTimeVector"),
        ("time_vector t0=1e308 fs=1e-308（溢位）", lambda: time_vector(3, 1e-308, 1e308), "dsv:clean:invalidTimeVector"),
    ]
    for label_, fn, ident in cases_err:
        try:
            fn()
            bad.append(f"{label_} 沒丟錯誤")
        except CleanError as e:
            if e.identifier != ident or not (e.zh and str(e)):
                bad.append(f"{label_} → {e.identifier}（應為 {ident}）")
        except Exception as e:                            # numpy 自己的錯誤不算
            bad.append(f"{label_} → {type(e).__name__}: {e}")
    # 可接受的形狀／型別：(N,1)、(1,N)、list、int、bool 都當成向量
    for label_, arg in (("(N,1)", np.arange(6.0).reshape(6, 1)), ("(1,N)", np.arange(6.0).reshape(1, 6)), ("list", [0, 1, 2, 3, 4, 5]),
                        ("int", np.arange(6)), ("bool", np.array([0, 1, 0, 1, 0, 1], dtype=bool))):
        yv = smooth(arg, "movmean", 3)["y"]
        want = smooth(np.asarray(arg, dtype=float).reshape(-1), "movmean", 3)["y"]
        if not (yv.shape == (6,) and np.array_equal(yv, want) and detrend(arg).shape == (6,)):
            bad.append(f"{label_} 應視為向量")
    if np.iscomplexobj(smooth(np.array([1, 2, 3], dtype=object), "movmean", 3)["y"]):
        bad.append("整數物件陣列不該變複數")
    if not (np.array_equal(breakpoint_indices(np.array([0.0, 0.1, 0.2], dtype=object), np.array([0.09, 2], dtype=object)), [1, 2])
            and np.array_equal(detrend(x7, "piecewiselinear", np.array([2, 4], dtype=object)), detrend(x7, "piecewiselinear", [2, 4]))):
        bad.append("數值物件陣列的斷點／時間軸應可用")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        nan7 = np.full(7, np.nan)
        res_nan = [smooth(nan7, "rloess", 3)["y"], smooth(nan7, "rlowess", 0.3, t7)["y"], smooth(nan7, "movmean")["y"],
                   smooth(np.array([1.0, np.nan, 3.0, 4.0, np.nan, 6.0, 7.0]), "rloess", 3)["y"]]
        _ = auto_window(np.array([1.0, 2.0, 3.0]), np.array([-0.85e308, 0.0, 0.85e308]), 1.0)
    if caught:
        bad.append(f"冒出警告：{[str(c.message) for c in caught]}")
    if not (all(np.all(np.isnan(r)) for r in res_nan[:3]) and np.all(np.isfinite(res_nan[3]))):
        bad.append("全 NaN 的 rloess／rlowess／movmean Auto 應回全 NaN；部分 NaN 的 rloess 應回有限值")
    # 工作量上限：N=2e5、窗＝N 的 movmedian／gaussian／lowess／rloess（Σ|S_i|＝4e10）要立刻拒絕；樣本模式的 sgolay 窗＝N 走共用設計矩陣
    # （兩端共用同一個多項式）可算；時間模式（一般路徑）的 lowess／rloess／sgolay 窗＝N 拒絕；detrend 1e6 點配 20 個斷點（N×21 > 2²⁴）
    t0_ = _time.time()
    for m_ in ("movmedian", "gaussian", "lowess", "rloess"):
        try:
            smooth(np.zeros(200_000), m_, 200_000)
            bad.append(f"{m_} 窗＝N＝2e5 沒拒絕")
        except CleanError as e:
            if e.identifier != "dsv:clean:tooMuchWork":
                bad.append(f"{m_} 窗＝N → {e.identifier}")
    ysg = smooth(np.ones(200_000) + np.arange(200_000.0) / 1e5, "sgolay", 200_000)["y"]
    if not (ysg.shape == (200_000,) and np.allclose(ysg, np.ones(200_000) + np.arange(200_000.0) / 1e5, rtol=0, atol=1e-12)):
        bad.append("樣本模式 sgolay 窗＝N＝2e5（共用多項式）應可算且對直線不變")
    if smooth(np.zeros(200_000), "movmean", 200_000)["y"].shape != (200_000,):
        bad.append("movmean 窗＝N＝2e5 應可算（O(N)）")
    t2e5 = time_vector(200_000, 1000.0)
    for m_ in ("lowess", "rloess", "sgolay"):
        try:
            smooth(np.zeros(200_000), m_, 200.0, t2e5)
            bad.append(f"時間模式 {m_} 窗＝N＝2e5 沒拒絕")
        except CleanError as e:
            if e.identifier != "dsv:clean:tooMuchWork":
                bad.append(f"時間模式 {m_} 窗＝N → {e.identifier}")
    for label_, fn in (("detrend 20 斷點×1e6", lambda: detrend(np.zeros(1_000_000), "piecewiselinear", list(range(10, 1_000_000, 50_000)))),
                       ("detrend 20 時間斷點×1e6", lambda: detrend(np.zeros(1_000_000), "piecewiselinear", list(range(10, 1_000_000, 50_000)),
                                                                 np.arange(1_000_000.0)))):
        try:
            fn()
            bad.append(f"{label_} 沒拒絕")
        except CleanError as e:
            if e.identifier != "dsv:detrend:tooManyBreakpoints":
                bad.append(f"{label_} → {e.identifier}")
    guard_t = _time.time() - t0_
    if guard_t > 3.0:
        bad.append(f"上限檢查花了 {guard_t:.1f} s（應在配置前就拒絕）")
    if detrend(np.zeros(100_000), "piecewiselinear", list(range(10, 100_000, 1000))).shape != (100_000,):
        bad.append("1e5 點配 100 個斷點（N×101 < 2²⁴）應可算")
    # breakpoint_indices 不配置距離表（searchsorted＋二分搜尋，O(K·log N)）：1e6 點 20 個斷點、3e7 點都可算，和 argmin|t−b| 逐個相同
    # （含一樣近取前一個、捨入造成的相同距離、超出範圍、距離溢位）；第三輪之前 N×K > 2²⁴ 就拒絕，N > 2²⁴ 的時間模式連超出尾端的斷點都被誤拒
    tb_ = np.arange(1_000_000.0)
    if not np.array_equal(breakpoint_indices(tb_, list(range(10, 1_000_000, 50_000))), np.arange(10, 1_000_000, 50_000)):
        bad.append("breakpoint_indices 1e6 點 20 個整數斷點")
    rngb = np.random.default_rng(3)
    for kind_ in range(5):
        for _ in range(60):
            nb_ = int(rngb.integers(1, 40))
            if kind_ == 0:
                tv_ = np.sort(rngb.choice(1000, nb_, replace=False)).astype(float) * 0.5
            elif kind_ == 1:
                tv_ = 1e16 + np.arange(nb_) * 2.0                    # 間隔＝1 ulp：b − t_j 會捨入成相同的值
            elif kind_ == 2:
                tv_ = np.cumsum(rngb.uniform(0.1, 1.0, nb_))
            elif kind_ == 3:
                tv_ = np.arange(nb_) * 1e-300
            else:
                tv_ = np.unique(np.round(rngb.normal(0.0, 1e300, nb_), -290))
            q_ = np.concatenate([tv_, (tv_[:-1] + tv_[1:]) / 2.0, rngb.uniform(tv_[0] - 5, tv_[-1] + 5, 5),
                                 [1e308, -1e308, 1e300], tv_ + 1e16, tv_ - 3e16])
            q_ = q_[np.isfinite(q_)]
            with np.errstate(over="ignore"):
                want_ = np.argmin(np.abs(tv_[:, None] - q_[None, :]), axis=0)
            if not np.array_equal(breakpoint_indices(tv_, q_), want_):
                bad.append(f"breakpoint_indices vs argmin（第 {kind_} 類 N={tv_.size}）")
                break
    n24 = (1 << 24) + 8
    z24 = np.sin(np.arange(n24) / 1e5)
    t0_ = _time.time()
    ok24 = (np.array_equal(detrend(z24, "piecewiselinear", [1e9], np.arange(n24, dtype=float)), detrend(z24))
            and breakpoint_indices(np.arange(30_000_000.0), [5.5, 1e9, -3.0]).tolist() == [5, 29_999_999, 0])
    t24 = _time.time() - t0_
    if not (ok24 and t24 < 5.0):
        bad.append(f"N＝2²⁴+8 的時間模式超出尾端斷點（忽略）應等於 linear、3e7 點的 breakpoint_indices 應可算（{t24:.2f} s）")
    del z24
    check(not bad, f"輸入檢查（{len(cases_err)} 種）：字串／複數／二維／bool／多元素的訊號、窗、因子、次數、取樣點、斷點、時間軸都丟 CleanError（含代號）；"
                   "(N,1)／(1,N)／list／int／bool 訊號當成向量；detrend 時間軸用 dsv:detrend:timeVector* 代號；time_vector 檢查 n／fs／t0；"
                   "全 NaN 的 rloess／rlowess 不冒 RuntimeWarning；Inf 訊號、Degree 配非 sgolay、時間軸跨度溢位、time_vector 溢位都丟 CleanError；"
                   "工作量上限：窗＝N＝2e5 的 movmedian／gaussian／lowess／rloess、時間模式的 lowess／rloess／sgolay 與 20 斷點×1e6 的 detrend（樣本／時間）立刻拒絕"
                   f"（{guard_t:.2f} s）、樣本模式 sgolay 窗＝N、movmean 窗＝N 與 100 斷點×1e5 可算；breakpoint_indices 不受 N 限制（300 組隨機／捨入／溢位案例＝argmin，"
                   f"N＝2²⁴+8 超出尾端的時間斷點＝linear、3e7 點 {t24:.2f} s）" + (f"（問題：{bad}）" if bad else ""))

    # 第二輪審查 1（HANG）：工作量模型 Σ|S_i|·(16+(次數+1)²)·擬合次數，與樣本軸共用設計矩陣——審查者量到卡住／幾十秒的案例要在幾秒內算完
    # 或立刻拒絕；共用設計矩陣的結果要和一般（逐窗）路徑一致；FFT 相關要和直接內積一致
    bad = []
    rng2 = np.random.default_rng(11)
    x1k = rng2.standard_normal(1000)
    x2e4 = rng2.standard_normal(20_000)
    x1e5 = rng2.standard_normal(100_000)
    tm: Dict[str, float] = {}
    for label_, xv, m_, W, dg in (("sgolay N=1000 窗 1000 次數 999", x1k, "sgolay", 1000, 999), ("sgolay N=1000 窗 1000 次數 400", x1k, "sgolay", 1000, 400),
                                  ("sgolay N=2e4 窗 2000 次數 50", x2e4, "sgolay", 2000, 50), ("sgolay N=2e4 窗 2000 次數 20", x2e4, "sgolay", 2000, 20),
                                  ("sgolay N=1e5 窗 1000 次數 30", x1e5, "sgolay", 1000, 30), ("lowess N=1e5 窗 1300", x1e5, "lowess", 1300, None),
                                  ("loess N=1e5 窗 1300", x1e5, "loess", 1300, None), ("rloess N=2e4 窗 300", x2e4, "rloess", 300, None)):
        t0_ = _time.time()
        r = smooth(xv, m_, W, degree=dg)
        tm[label_] = _time.time() - t0_
        # 時間門檻只是「沒有卡住」的粗界（第一輪 22 s～跑不完）；實測 numpy 2.4／Accelerate 0.1～2.4 s、numpy 1.26／OpenBLAS 最慢 3.2 s（1000×1000 QR）
        if not (r["y"].shape == xv.shape and np.all(np.isfinite(r["y"])) and tm[label_] < 12.0):
            bad.append(f"{label_}：{tm[label_]:.2f} s 或結果非有限")
    if not np.allclose(smooth(x1k, "sgolay", 1000, degree=999)["y"], x1k, rtol=0, atol=1e-12):
        bad.append("sgolay 次數 999＝窗−1（1000 點內插）應回傳 x 本身")
    t1k, t2e4, t1e5 = time_vector(1000, 1000.0, 0.37), time_vector(20_000, 1000.0), time_vector(100_000, 1000.0)
    t0_ = _time.time()
    for label_, fn in (("時間模式 sgolay N=1000 窗 1 s 次數 999", lambda: smooth(x1k, "sgolay", 1.0, t1k, degree=999)),
                       ("時間模式 sgolay N=1000 窗 1 s 次數 400", lambda: smooth(x1k, "sgolay", 1.0, t1k, degree=400)),
                       ("時間模式 sgolay N=2e4 窗 2 s 次數 20", lambda: smooth(x2e4, "sgolay", 2.0, t2e4, degree=20)),
                       ("時間模式 sgolay N=1e5 窗 1 s 次數 30", lambda: smooth(x1e5, "sgolay", 1.0, t1e5, degree=30)),
                       ("時間模式 rloess N=1e5 窗 1.3 s", lambda: smooth(x1e5, "rloess", 1.3, t1e5)),
                       ("時間模式 lowess N=1e5 窗 1.3 s", lambda: smooth(x1e5, "lowess", 1.3, t1e5)),
                       ("樣本模式 rloess N=1e5 窗 1300（穩健重擬合仍逐窗）", lambda: smooth(x1e5, "rloess", 1300))):
        try:
            fn()
            bad.append(f"{label_} 沒拒絕")
        except CleanError as e:
            if e.identifier != "dsv:clean:tooMuchWork":
                bad.append(f"{label_} → {e.identifier}")
    reject_t = _time.time() - t0_
    if reject_t > 1.0:
        bad.append(f"拒絕花了 {reject_t:.2f} s（應在配置前）")
    if not (_regression_units(50_000_000, 2, 1) <= MAX_REGRESSION_UNITS < _regression_units(39_000_000, 20, 1)
            and _regression_units(130_000_000, 2, 6) > MAX_REGRESSION_UNITS and _regression_units(5_000_000, 2, 6) <= MAX_REGRESSION_UNITS):
        bad.append("工作量模型：1e6 點 50 樣本窗的 sgolay 要接受、2e4 點 2000 窗次數 20 與 1e5 點 1300 窗的 rloess 要拒絕、1e5 點 50 窗的 rloess 要接受")
    # 共用設計矩陣 vs 一般路徑（同一個加權最小平方，不同的計算順序）
    xg = np.cumsum(rng2.standard_normal(600)) + 5.0
    xgn = xg.copy()
    xgn[[3, 300, 598]] = np.nan
    tg = np.arange(600.0)
    worst = 0.0
    for m_, p_, wgt in (("lowess", 1, True), ("loess", 2, True), ("sgolay", 2, False), ("sgolay", 5, False)):
        for W in (7, 8, 51, 200, 599, 600, 1200):
            for xv in (xg, xgn, xg + 1j * xg[::-1]):
                fast = smooth(xv, m_, W, degree=(p_ if m_ == "sgolay" else None))["y"]
                gen = _local_regression(xv, tg, float(W), p_, wgt, False, m_, False)
                if not np.array_equal(np.isnan(fast), np.isnan(gen)):
                    bad.append(f"{m_} 窗 {W}：NaN 位置不同")
                    continue
                ok_ = ~np.isnan(fast)
                e = float(np.max(np.abs(fast[ok_] - gen[ok_])) / np.max(np.abs(gen[ok_])))     # 相對於該組輸出的幅度（接近 0 的點不放大）
                worst = max(worst, e)
                if e > 1e-12:
                    bad.append(f"{m_} 窗 {W}：共用設計矩陣 vs 一般路徑相對差 {e:.3g}")
    hcorr = rng2.standard_normal(1000)
    xcorr = rng2.standard_normal(70_000) + 1e3                 # N·W＝7e7 > 2²⁶ → FFT；直接內積當參考
    e_fft = float(np.max(np.abs(_correlate_valid(xcorr, hcorr) - np.correlate(xcorr, hcorr, mode="valid"))))
    # 上限＝16·eps·log₂L·Σ|h|·max|x−mean|（_correlate_valid 說明裡的捨入模型；L＝2¹⁷）＝2.3e-10；實測 4.7e-11（numpy 2.4.6）、
    # 9.5e-11（numpy 1.26.4 的 pocketfft）。第三輪之前是 1e-9·1e3·√1000＝3.2e-5，比實際鬆 5～6 個數量級
    fft_bound = 16.0 * float(np.finfo(float).eps) * 17 * float(np.sum(np.abs(hcorr))) * float(np.max(np.abs(xcorr - np.mean(xcorr))))
    if e_fft > fft_bound:
        bad.append(f"FFT 相關 vs 直接內積 {e_fft:.3g} > {fft_bound:.3g}")
    check(not bad, "第二輪審查（HANG）：樣本模式共用設計矩陣——" + "、".join(f"{k} {v:.2f}s" for k, v in tm.items())
                   + "（第一輪 22 s～跑不完）；sgolay 次數 999＝窗−1 回傳 x；時間模式（逐窗）的同類案例與樣本模式 rloess 1e5×1300 以工作量模型"
                   f"Σ|S_i|·(16+(p+1)²)·次數 > 2³¹ 立刻拒絕（{reject_t:.2f} s）；共用設計矩陣 vs 一般路徑 ≤ 1e-12（實際 {worst:.2g}，含 NaN、複數、"
                   f"窗 7～1200）；FFT 相關 vs 直接內積 {e_fft:.2g}（上限 16·eps·log₂L·Σ|h|·max|x−x̄|＝{fft_bound:.2g}）" + (f"（問題：{bad}）" if bad else ""))

    # 第二輪審查 2：RuntimeWarning 掃描——1e308 等級／次正規／±Inf／NaN＋1e308 的訊號、極端時間軸、次正規視窗；2 的冪次縮放的齊次性
    bad = []
    n50 = 50
    xs50 = np.sin(np.arange(n50) / 3.0) + 0.3
    t50 = time_vector(n50, 100.0, 0.37)
    big = 1e308
    hugeset = {"1e308·sin": xs50 * big, "±1e308 階梯": np.r_[np.full(25, big), np.full(25, -big)], "1e308 常數": np.full(n50, big),
               "1e308 複數": (xs50 + 1j * np.cos(np.arange(n50) / 5.0)) * big, "NaN＋1e308": np.r_[xs50[:10] * big, np.nan, xs50[11:] * big],
               "次正規 1e-310": xs50 * 1e-310}
    realmax = float(np.finfo(float).max)
    t_half = np.array([-0.85e308, 0.0, 0.85e308])
    x3_ = np.array([1.0, 2.0, 3.0])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for name_, s_ in hugeset.items():
            for m_ in METHODS:
                for args in ((7,), (300,), (None,), (0.07, t50), (None, t50)):
                    yv = smooth(s_, m_, *args)["y"]
                    if not np.all(np.isfinite(yv) | np.isnan(s_)):
                        bad.append(f"{name_} {m_} {args}：結果有 Inf／多出 NaN")
            for w_ in (auto_window(s_), auto_window(s_, t50)):
                if not (math.isfinite(float(w_)) and float(w_) > 0):
                    bad.append(f"{name_} auto_window {w_}")
            for yv in (detrend(s_), detrend(s_, "constant"), detrend(s_, "piecewiselinear", [10, 20]), detrend(s_, "piecewiselinear", [0.5, 0.8], t50)):
                if not (np.all(np.isfinite(yv)) or np.any(np.isnan(s_))):
                    bad.append(f"{name_} detrend 結果非有限")
        # 齊次性：1e308·sin 的結果＝1e308·(sin 的結果) 到捨入；2 的冪次更要逐位元相同
        for m_ in METHODS:
            for args in ((7,), (None,), (0.07, t50)):
                a = smooth(xs50 * big, m_, *args)["y"]
                b = smooth(xs50, m_, *args)["y"] * big
                if not np.allclose(a, b, rtol=1e-12, atol=0.0):
                    bad.append(f"{m_} {args}：1e308 倍的結果相對差 {np.max(np.abs(a - b) / np.abs(b)):.3g}")
        if not np.allclose(detrend(xs50 * big, "piecewiselinear", [10, 20]), detrend(xs50, "piecewiselinear", [10, 20]) * big, rtol=1e-12, atol=1e-12 * big):
            bad.append("detrend 1e308 倍不齊次")
        tA_, xA_, _ = sig["A_time"]
        xC_ = sig["C_complex_samples"][1]
        for k_ in (1020, -1000, 37):
            for xv, tv, w_ in ((xA_, None, 7), (xA_, tA_, 0.075), (xA_, None, None), (xA_, tA_, None), (xC_, None, 9), (xC_, None, None)):
                for m_ in METHODS:
                    y0 = smooth(xv, m_, w_, tv)["y"]
                    y1 = smooth(_ldexp(xv, k_), m_, w_, tv)["y"]
                    if not np.array_equal(y1, _ldexp(y0, k_)):
                        bad.append(f"{m_} 窗 {w_} ×2^{k_}：結果不是逐位元相同（{np.max(np.abs(y1 - _ldexp(y0, k_))):.3g}）")
            for meth_, bp_ in (("linear", None), ("constant", None), ("piecewiselinear", [20, 60])):
                if not np.array_equal(detrend(_ldexp(xA_, k_), meth_, bp_), _ldexp(detrend(xA_, meth_, bp_), k_)):
                    bad.append(f"detrend {meth_} ×2^{k_} 不是逐位元相同")
        # 極端時間軸與視窗（都是 IEEE 極限，不冒警告）
        for m_ in METHODS:
            for args in ((realmax, t_half), (None, t_half, 1.0), (None, t_half, 0.0), (None, t_half, 0.5)):
                yv = smooth(x3_, m_, *args)["y"]
                if not np.all(np.isfinite(yv)):
                    bad.append(f"{m_} t=±0.85e308 {args[0]}：{yv}")
            yv = smooth(x3_, m_, 5e-324, np.array([0.0, 5e-324, 1e-323]))["y"]      # W/2 捨到 0 → 每個視窗只有自己
            if not np.array_equal(yv, x3_):
                bad.append(f"{m_} 次正規視窗：{yv}≠x")
            yv = smooth(xs50, m_, 1e-199, np.arange(n50) * 1e-200)["y"]              # σ²、d² 都在次正規／零的邊緣
            if not np.all(np.isfinite(yv)):
                bad.append(f"{m_} t 1e-200 窗 1e-199 非有限")
            yv = smooth(xs50, m_, None, np.arange(n50) * 1e306)["y"]                 # 跨度 4.9e307：linspace 的 (n−1)·(b−a) 溢位 → 先除再乘
            if not np.all(np.isfinite(yv)):
                bad.append(f"{m_} t 跨度 4.9e307 自動視窗非有限")
        if not (np.array_equal(breakpoint_indices(t_half, [-0.85e308, 0.85e308, 0.0]), [0, 2, 1])
                and np.array_equal(detrend(xs50, "piecewiselinear", [1e300]), detrend(xs50))
                and np.array_equal(detrend(xs50, "piecewiselinear", [1e300], t50), detrend(xs50))):
            bad.append("斷點 ±0.85e308／1e300（超出尾端→忽略）")
        check_uniform(t_half)
        if max_window_points(t_half, realmax) != 3 or not is_exactly_uniform(t_half):
            bad.append("t=±0.85e308、W=realmax 的視窗應含 3 點且完全等距")
    if caught:
        bad.append(f"冒出警告：{sorted(set(str(c.message) for c in caught))}")
    check(not bad, f"第二輪審查（RuntimeWarning／極端尺度）：{len(hugeset)} 種 1e308／次正規／NaN＋1e308 訊號 × 8 方法 × 5 種視窗、auto_window、detrend 全部有限且"
                   "不冒警告；1e308 倍的結果＝1e308×原結果（1e-12）；×2^1020／2^−1000／2^37 的 smooth（8 方法、樣本／時間／自動／複數）與 detrend 逐位元齊次；"
                   "t=±0.85e308 配 W=realmax／自動視窗、次正規視窗（W/2→0）、t 1e-200、跨度 4.9e307（linspace 溢位改先除再乘）、斷點 ±0.85e308／1e300 都是 IEEE 極限、無警告"
                   + (f"（問題：{bad[:6]}）" if bad else ""))

    # 第二輪審查 3：check_uniform 不能把 DSV 自己產生的均勻時間軸（t0 + n/fs 的捨入）誤判成非均勻
    bad = []
    for n_, fs_, t0__ in ((65536, 8e6, 2.0), (262144, 1e6, 50.0), (10_000_000, 1e6, 0.0), (1000, 1e9, 1e6), (200, 100.0, 0.37), (3, 1e-3, 1e9), (100, 1.0, 0.0)):
        try:
            check_uniform(time_vector(n_, fs_, t0__))
        except CleanError as e:
            bad.append(f"time_vector({n_}, {fs_:g}, {t0__:g}) 被判成非均勻（{e.identifier}）")
    tA_ = sig["A_time"][0]
    jitter = tA_ + 1e-6 * 0.01 * rng2.standard_normal(tA_.size)
    for label_, tv in (("A_nonuniform", sig["A_nonuniform"][0]), ("少一個樣本", np.delete(tA_, 100)), ("1e-6 相對抖動", np.sort(jitter)),
                       ("cumsum 隨機 Δt", np.cumsum(rng2.uniform(0.9, 1.1, 300)))):
        try:
            check_uniform(tv)
            bad.append(f"{label_} 應判成非均勻")
        except CleanError as e:
            if e.identifier != "detrendNonUniformSignalsWarning":
                bad.append(f"{label_} → {e.identifier}")
    check(not bad, "第二輪審查（check_uniform）：time_vector(65536, 8e6, 2)、(262144, 1e6, 50)、(1e7, 1e6, 0)、(1000, 1e9, 1e6)（第一輪相對 1e-9 全部誤判）"
                   "與參考時間軸都判成均勻（容許 max(1e-9·Δt, 16·eps·max|t|)）；A_nonuniform、少一個樣本、1e-6 相對抖動、隨機 Δt 判成非均勻"
                   + (f"（問題：{bad}）" if bad else ""))

    # 審查列出的未執行分支（沒有 MATLAB 參考資料，用定義或暴力算法比對）：長窗 movmean 的累加和、局部迴歸的 NaN／零權重、
    # _fill_nan_pchip、_linspace 對稱式、_pchip N≤2 與端點斜率、自動視窗的 realmin／realmax
    bad = []
    rng = np.random.default_rng(7)
    nL = 1200
    xL = 1.0e6 + np.sin(2 * np.pi * np.arange(nL) / 97.0) + 0.3 * rng.standard_normal(nL)
    xL[[5, 600, 601, 1190]] = np.nan

    def brute_movmean(xv, W):
        out = np.empty(xv.size)
        for i in range(xv.size):
            seg = xv[max(0, i - W // 2):min(xv.size, i + (W - 1) // 2 + 1)]
            seg = seg[~np.isnan(seg)]
            out[i] = seg.mean() if seg.size else np.nan
        return out

    for W in (256, 257, 300, 301, 1500):
        got = smooth(xL, "movmean", W)["y"]
        want = brute_movmean(xL, W)
        if not np.allclose(got, want, rtol=1e-12, atol=0.0, equal_nan=True):
            bad.append(f"movmean 窗 {W}（偏移 1e6、含 NaN）vs 暴力 {np.nanmax(np.abs(got - want)):.3g}")
    xg = 1.0e6 + np.arange(40.0)
    xg[10:25] = np.nan                                         # 15 個 NaN、窗 5 → 中間的窗全 NaN
    got = smooth(xg, "movmean", 5)["y"]
    if not (np.all(np.isnan(got[12:23])) and np.allclose(got[:10], brute_movmean(xg, 5)[:10], rtol=1e-12)):
        bad.append("短窗 movmean 整窗 NaN 應為 NaN")

    def brute_local(xv, W, p, weighted):
        N = xv.size
        half = W / 2.0
        jj = np.arange(N)
        sets = [jj[(jj >= i - half) & (jj - i < half)] for i in range(N)]
        iL = max(i for i in range(N) if 0 in sets[i])
        iR = min(i for i in range(N) if N - 1 in sets[i])
        out = np.empty(N)
        for i in range(N):
            S = sets[iL] if i < iL else (sets[iR] if i > iR else sets[i])
            d = (S - i).astype(float)
            if weighted:
                q = np.abs(d) / np.abs(d).max()
                wgt = (1.0 - q ** 3) ** 3
            else:
                wgt = np.ones(d.size)
            xs = xv[S]
            nanm = np.isnan(xs)
            wgt = np.where(nanm, 0.0, wgt)
            xs = np.where(nanm, 0.0, xs)
            nnz = int(np.count_nonzero(wgt > 0))
            if nnz == 0:
                if nanm.all():
                    out[i] = np.nan
                    continue
                wgt = (~nanm).astype(float)                    # MATLAB：權重全 0 → 窗內非 NaN 的點等權重（zero_weight.json）
                nnz = int(np.count_nonzero(wgt > 0))
            pe = min(p, nnz - 1)
            V = np.vander(d, pe + 1, increasing=True)
            sw = np.sqrt(wgt)
            out[i] = np.linalg.lstsq(sw[:, None] * V, sw * xs, rcond=None)[0][0]
        return out

    xr = np.cos(np.arange(60.0) / 7.0) + 0.1 * rng.standard_normal(60)
    xr[[20, 21, 22]] = np.nan                                  # i=21 的窗 5：中間三點 NaN、兩端 tricube 0 → 權重全 0 → 兩端等權重
    xr[40:47] = np.nan                                         # i=42..44 的窗全 NaN → NaN
    for m_, p_, wgt_ in (("lowess", 1, True), ("loess", 2, True), ("sgolay", 2, False)):
        got = smooth(xr, m_, 5)["y"]
        want = brute_local(xr, 5, p_, wgt_)
        if not np.allclose(got, want, rtol=1e-12, atol=1e-12, equal_nan=True):
            e = np.abs(got - want)
            bad.append(f"{m_} 窗 5 含 NaN vs 暴力加權最小平方：{np.nanmax(e):.3g}@{int(np.nanargmax(e))}")
        if not (np.all(np.isnan(got[42:45])) and not np.any(np.isnan(got[:40])) and not np.any(np.isnan(got[47:]))):
            bad.append(f"{m_}：全 NaN 窗應為 NaN、其他有限")
    mid21 = (xr[19] + xr[23]) / 2.0                            # 兩點、次數降為 1 → 直線在中點＝平均
    for m_ in ("lowess", "loess"):
        if not math.isclose(float(smooth(xr, m_, 5)["y"][21]), mid21, rel_tol=1e-12, abs_tol=1e-15):
            bad.append(f"{m_}：權重全 0 的窗應改用等權重（MATLAB 規則；第三輪之前回 0）")
    # _fill_nan_pchip：線性資料補 NaN（含兩端外插）應回直線、非 NaN 不動、全 NaN 不動、單調資料補在鄰點之間
    tf = np.arange(12.0)
    line = 0.5 * tf - 3.0
    xf = line.copy()
    xf[[0, 4, 5, 11]] = np.nan
    f = _fill_nan_pchip(tf, xf)
    if not (np.allclose(f, line, rtol=0, atol=1e-12) and np.array_equal(f[~np.isnan(xf)], xf[~np.isnan(xf)])):
        bad.append(f"_fill_nan_pchip 線性資料應回直線：{np.max(np.abs(f - line)):.3g}")
    if not np.all(np.isnan(_fill_nan_pchip(tf, np.full(12, np.nan)))):
        bad.append("_fill_nan_pchip 全 NaN 應原樣")
    xq2 = tf ** 2
    xq2[5] = np.nan
    f2 = _fill_nan_pchip(tf, xq2)
    if not (16.0 < f2[5] < 36.0 and auto_window(xq2) == auto_window(f2)):
        bad.append("_fill_nan_pchip 單調資料應補在鄰點之間、自動視窗等於補好的訊號")
    # _linspace：a＝−b 的對稱式（反對稱、中點剛好 0、頭尾精確）與一般式
    ls = _linspace(-1.0, 1.0, 5)
    ls2 = _linspace(-2.5, 2.5, 8)
    ls3 = _linspace(-3.0, 3.0, 7)
    ls4 = _linspace(0.37, 2.36, 200)
    if not (ls.tolist() == [-1.0, -0.5, 0.0, 0.5, 1.0] and np.array_equal(ls2, -ls2[::-1]) and ls2[0] == -2.5 and ls2[-1] == 2.5
            and ls3[3] == 0.0 and np.array_equal(ls3, -ls3[::-1]) and ls4[0] == 0.37 and ls4[-1] == 2.36 and ls4.size == 200
            and np.allclose(np.diff(ls4), (2.36 - 0.37) / 199, rtol=1e-12)):
        bad.append("_linspace 對稱式／一般式")
    # _pchip：N＝1 常數、N＝2 直線（含外插）、端點斜率：三點公式異號→0、異號且超過 3 倍→3·δ、內點差分異號→0、通過資料點
    xs3 = np.array([0.0, 1.0, 2.0])
    eps_ = 1e-7

    def slope(xs, ys, at, side=0):
        if side == 0:
            return float((_pchip(xs, ys, np.array([at + eps_])) - _pchip(xs, ys, np.array([at - eps_])))[0] / (2 * eps_))
        return float((_pchip(xs, ys, np.array([at + side * eps_]))[0] - _pchip(xs, ys, np.array([at]))[0]) / (side * eps_))

    p1 = _pchip(np.array([1.0]), np.array([7.0]), np.array([0.0, 1.0, 2.0]))
    p2 = _pchip(np.array([0.0, 2.0]), np.array([1.0, 5.0]), np.array([-1.0, 0.5, 1.0, 3.0]))
    if not (p1.tolist() == [7.0, 7.0, 7.0] and np.allclose(p2, 1.0 + 2.0 * np.array([-1.0, 0.5, 1.0, 3.0]), rtol=0, atol=1e-12)):
        bad.append("_pchip N＝1 常數／N＝2 直線")
    s_zero = slope(xs3, np.array([0.0, 1.0, 5.0]), 0.0, +1)        # e＝(3·1−4)/2＝−0.5 和 δ₀＝1 異號 → 0
    s_clamp = slope(xs3, np.array([0.0, 1.0, -4.0]), 0.0, +1)      # e＝(3·1+5)/2＝4 > 3·δ₀ 且 δ 異號 → 3
    s_mid = slope(xs3, np.array([0.0, 1.0, 0.0]), 1.0)             # 內點兩側差分異號 → 0
    s_end = slope(xs3, np.array([0.0, 1.0, 5.0]), 2.0, -1)         # 右端 e＝(3·4−1)/2＝5.5（同號、未超 3 倍）→ 5.5
    # 切線本身逐位元檢查（_end_tangent：三點公式 −0.5 異號→0、4 超過 3·δ₀→3、5.5 不變）；有限差分（步長 1e-7，截斷誤差 ≤ 步長·|f''| ≈ 4e-7，
    # 實測 ≤ 3.0e-7）確認 _pchip 真的用了這些切線。第三輪之前容許 1e-5
    if not (_end_tangent(1.0, 1.0, 1.0, 4.0) == 0.0 and _end_tangent(1.0, 1.0, 1.0, -5.0) == 3.0 and _end_tangent(1.0, 1.0, 4.0, 1.0) == 5.5):
        bad.append("_end_tangent 三點公式 0／3／5.5")
    if not (abs(s_zero) < 1e-6 and abs(s_clamp - 3.0) < 1e-6 and abs(s_mid) < 1e-6 and abs(s_end - 5.5) < 1e-6):
        bad.append(f"_pchip 端點／內點斜率：{s_zero:.3g}（應 0）、{s_clamp:.6g}（應 3）、{s_mid:.3g}（應 0）、{s_end:.6g}（應 5.5）")
    xs6 = np.array([0.0, 0.5, 1.5, 2.0, 3.5, 4.0])
    ys6 = np.array([1.0, 3.0, 2.5, 2.5, -1.0, 0.0])
    if not np.allclose(_pchip(xs6, ys6, xs6), ys6, rtol=0, atol=1e-12):
        bad.append("_pchip 應通過資料點")
    # 自動視窗的 realmin／realmax 夾限：τ＝0、完全等距 Δt＝0.85e308（跨度 1.7e308 仍有限）→ k＝N＝3 → 2.55e308＝Inf → realmax；
    # τ＝1、min(Δt)＝5e-324 → /2＝0 → realmin。（跨度本身溢位的 t＝±1e308 現在被 samplePointsSpanOverflow 拒絕，見輸入檢查）
    w_max = auto_window(np.array([1.0, 2.0, 3.0]), np.array([-0.85e308, 0.0, 0.85e308]), 1.0)
    w_min = auto_window(np.array([1.0, 2.0, 3.0]), np.array([0.0, 5e-324, 1.0]), 0.0)
    if not (w_max == float(np.finfo(float).max) and w_min == float(np.finfo(float).tiny)):
        bad.append(f"自動視窗夾限 {w_max!r}／{w_min!r}")
    check(not bad, "審查列出的分支：長窗 movmean（256／257／300／301／1500，偏移 1e6、含 NaN）vs 逐窗暴力 1e-12；lowess／loess／sgolay 窗 5 含 NaN "
                   "vs 暴力加權最小平方（NaN 權重 0、次數降低、全 NaN 窗→NaN、權重全 0→非 NaN 點等權重）1e-12；_fill_nan_pchip 線性外插／全 NaN／單調；"
                   "_linspace 對稱式；_pchip N＝1／2、端點斜率 0／3δ／內點 0／通過資料點；自動視窗 realmax／realmin"
                   + (f"（問題：{bad}）" if bad else ""))

    # 第三輪審查 1（CORRECTNESS）：完全等距的時間軸——MATLAB 的等距快速路徑（ws＝W/Δt、fix(ws)、整數軸、穩健重擬合用沒截斷的 ws）vs
    # 審查者用 MATLAB R2025a 實跑的 uniform_axis.json（uniform_axis_probe.m：N＝200、x＝sin(n/7)+0.1cos(n/3)+0.02n；t＝n/2、n、n/4 配
    # ws 8.5（偶數 fix）／7.5（奇數 fix）、0.37+n/100 配 0.085 s＝取樣點路徑的 8.5 個樣本）。第二輪一律用取樣點法則，8.5 的 6 種方法都錯。
    bad = []
    path_u = os.path.join(ref_dir, "smooth_detrend", "uniform_axis.json")
    worst_u = 0.0
    n_u = 0
    if not os.path.isfile(path_u):
        bad.append("缺 tests/matlab_ref/smooth_detrend/uniform_axis.json（審查者的 MATLAB 實跑資料）")
    else:
        with open(path_u, encoding="utf-8") as fh:
            U = json.load(fh)
        xu = arr(U["x"])
        nu = np.arange(200.0)
        axes_u = {"t_fs2": (2.0, 0.0, 8.5), "t_fs2b": (2.0, 0.0, 7.5), "t_fs1": (1.0, 0.0, 8.5), "t_fs1b": (1.0, 0.0, 7.5),
                  "t_fs4": (4.0, 0.0, 8.5), "t_fs100": (100.0, 0.37, 8.5)}
        if not (xu.size == 200 and float(np.max(np.abs(xu - (np.sin(nu / 7) + 0.1 * np.cos(nu / 3) + 0.02 * nu)))) < 1e-14):
            bad.append("x 不是 sin(n/7)+0.1cos(n/3)+0.02n")
        for name_, (fs_, t0_, ws_) in axes_u.items():
            c = U[name_]
            tu, W_ = arr(c["t"]), float(c["W"])
            if not np.array_equal(tu, time_vector(200, fs_, t0_)):
                bad.append(f"{name_}：t 和 time_vector(200, {fs_:g}, {t0_:g}) 不同")
            if is_exactly_uniform(tu) != (name_ != "t_fs100"):
                bad.append(f"{name_}：is_exactly_uniform 應為 {name_ != 't_fs100'}")
            if name_ != "t_fs100" and _uniform_window_samples(W_, tu) != ws_:
                bad.append(f"{name_}：ws={_uniform_window_samples(W_, tu)!r}≠{ws_}")
            for m_ in METHODS:
                n_u += 1
                r = smooth(xu, m_, W_, tu)
                ref = arr(c[m_])
                ok, info = diff_info(r["y"], ref, xu)
                worst_u = max(worst_u, float(np.max(np.abs(r["y"] - ref))))
                if not (ok and r["winsz"] == W_):
                    bad.append(f"{name_} {m_}（ws={ws_}）：{info} winsz={r['winsz']}")
        # MATLAB 自己兩條路的差（t_fs1 等距 vs t_fs100 取樣點，同樣 8.5 個樣本）＝審查者報的數字：gaussian 1.12e-2（196 點）、sgolay 5.75e-3
        # （200）、lowess 7.24e-3（兩端 8 點）、loess 2.40e-3（8）、rlowess 2.87e-6（37）、rloess 0.526（200）、movmean／movmedian 一致；
        # 第二輪的做法（取樣點法則、不 fix）在整數軸上算 8.5 → 和 t_fs100 一致到 1e-13、和等距路徑差這些數字
        facts_u = {"gaussian": (0.011220847227134234, 196), "lowess": (0.0072365449743272553, 8), "loess": (0.0023996735644851164, 8),
                   "rlowess": (2.8676531831917096e-06, 37), "rloess": (0.52596551158673233, 200), "sgolay": (0.0057493062898759106, 200)}
        for m_ in METHODS:
            e = np.abs(arr(U["t_fs1"][m_]) - arr(U["t_fs100"][m_]))
            cnt_ = int(np.count_nonzero(e > 1e-12))
            if m_ in facts_u:
                v_, want_ = facts_u[m_]
                if not (math.isclose(float(e.max()), v_, rel_tol=1e-12) and cnt_ == want_):
                    bad.append(f"MATLAB 等距 vs 取樣點 {m_}：max {e.max():.17g}／{cnt_} 點 ≠ {v_}／{want_}")
            elif float(e.max()) > 1e-14:
                bad.append(f"MATLAB 等距 vs 取樣點 {m_} 應一致（{e.max():.3g}）")
            if m_ == "gaussian":
                lo_, hi_ = _window_bounds(nu, 8.5)
                ysp = _gaussian(xu, nu, lo_, hi_, 8.5)
            elif m_ in ("movmean", "movmedian"):
                lo_, hi_ = _window_bounds(nu, 8.5)
                ysp = _movmean(xu, lo_, hi_) if m_ == "movmean" else _movmedian(xu, lo_, hi_)
            else:
                ysp = _local_regression(xu, nu, 8.5, 1 if m_ in ("lowess", "rlowess") else 2, m_ != "sgolay", m_.startswith("r"), m_, False)
            e2 = float(np.max(np.abs(ysp - arr(U["t_fs100"][m_]))))
            if e2 > 1e-13:
                bad.append(f"取樣點法則（整數軸、8.5）{m_} vs MATLAB t_fs100：{e2:.3g}")
    check(not bad, f"第三輪審查（完全等距時間軸）vs MATLAB R2025a 實跑 uniform_axis.json（{n_u} 組＝8 方法 × t＝n/2、n、n/4 配 ws 8.5／7.5 與 "
                   f"0.37+n/100 配 0.085 s；t 與 time_vector 逐位元相同、is_exactly_uniform 判斷正確、ws＝W/Δt 精確）：y 全部一致（最大 |diff| "
                   f"{worst_u:.2g}，rtol 1e-12）；MATLAB 自己等距 vs 取樣點兩條路在 8.5 差 gaussian 1.12e-2／sgolay 5.75e-3／lowess 7.24e-3（兩端 8 點）／"
                   "loess 2.40e-3／rlowess 2.87e-6／rloess 0.526，movmean／movmedian 一致；第二輪的取樣點法則重現取樣點那條（≤1e-13）"
                   + (f"（問題：{bad[:6]}）" if bad else ""))

    # 第四輪審查（CORRECTNESS／COVERAGE）：完全等距時間軸、權重全 0 的窗、錯誤代號——全部對 MATLAB R2025a 實測
    # （tests/matlab_ref/smooth_detrend/ 的 uniform_axis2.m／zero_weight.m／zero_weight2.m／error_ids.m 與同名 .json；開發版另有
    #  near_singular_ref.json 的補充檢查，缺檔時略過這一項）
    import struct as _struct

    def load_ref(name_):
        p_ = os.path.join(ref_dir, "smooth_detrend", name_)
        if not os.path.isfile(p_):
            return None
        with open(p_, encoding="utf-8") as fh_:
            return json.load(fh_)

    def arrn(v):                                               # jsonencode 把 NaN 寫成 null
        return np.asarray([math.nan if e is None else e for e in (v if isinstance(v, list) else [v])], dtype=float)

    def hexd(h):
        return _struct.unpack(">d", bytes.fromhex(h))[0]

    def nanmax_abs(v):
        a_ = np.abs(np.asarray(v))
        a_ = a_[~np.isnan(a_)]
        return float(a_.max()) if a_.size else 0.0

    def diff_pin(y, ref, xs):
        # (和 MATLAB 差超過 1e-12·max|x| 的點數, 最大差的位置)
        e_ = np.abs(np.asarray(y, dtype=complex) - np.asarray(ref, dtype=complex))
        e_[np.isnan(e_)] = 0.0
        return int(np.count_nonzero(e_ > 1e-12 * nanmax_abs(xs))), int(np.argmax(e_))

    U2, ZW, ZW2, NS, EI = (load_ref(n_) for n_ in ("uniform_axis2.json", "zero_weight.json", "zero_weight2.json", "near_singular_ref.json", "error_ids.json"))
    missing = [n_ for n_, v_ in (("uniform_axis2.json", U2), ("zero_weight.json", ZW), ("zero_weight2.json", ZW2),
                                 ("error_ids.json", EI)) if v_ is None]
    if missing:
        check(False, f"第四輪審查：缺 MATLAB 參考資料 {missing}")
        return

    # (1) 哪些 DSV 時間軸是 smoothdata 眼中的「完全等距」：313 條時間軸逐位元重建（t₁、t_N、max／min Δt 的十六進位與位元總和）
    bad = []
    for a in U2["axes"]:
        N_ = int(a["N"])
        if a["form"] == "dsv_b":                               # 符號軸 x0 + n/sps 再除以符號率
            tv = (a["offset"] / a["sps"] + np.arange(N_, dtype=float) / a["sps"]) / a["sr"]
        elif a["form"] == "dsv_a":                             # time_vector(N, sps·符號率, x0/符號率)：dsv_preprocess 的做法
            tv = time_vector(N_, a["sps"] * a["sr"], (a["offset"] / a["sps"]) / a["sr"])
        else:
            tv = time_vector(N_, a["fs"], a["t0"])
        u_ = tv.view(np.uint64)
        dtv = np.diff(tv)
        if not (tv[0] == hexd(a["t1_hex"]) and tv[-1] == hexd(a["tend_hex"]) and dtv.max() == hexd(a["dtmax_hex"])
                and dtv.min() == hexd(a["dtmin_hex"]) and float(np.sum((u_ & np.uint64(0xFFFFFFFF)).astype(float))) == a["lo32_sum"]
                and float(np.sum((u_ >> np.uint64(32)).astype(float))) == a["hi32_sum"]):
            bad.append(f"{a['label']}：時間軸和 MATLAB 不是逐位元相同")
        if is_exactly_uniform(tv) != bool(a["uniform"]):
            bad.append(f"{a['label']}：is_exactly_uniform≠MATLAB（{a['uniform']}）")
    uni = [a for a in U2["axes"] if a["uniform"]]
    sec_uni = [a["label"] for a in uni if a["form"] != "plain" and a["sr"] != 1]
    sym_uni = sorted({a["sps"] for a in uni if a["form"] != "plain" and a["sr"] == 1})
    sym_all = [a for a in U2["axes"] if a["form"] != "plain" and a["sr"] == 1]
    plain_uni = [(int(a["N"]), a["fs"], a["t0"]) for a in uni if a["form"] == "plain"]
    if not (len(U2["axes"]) == 313 and len(uni) == 87 and not sec_uni and sym_uni == [1, 2, 4, 8, 16, 64]
            and all(bool(a["uniform"]) == (a["sps"] in (1, 2, 4, 8, 16, 64)) for a in sym_all)
            and (200, 100, 0.37) not in plain_uni and (1000, 1024, 0) in plain_uni and (1000, 1000, 0) not in plain_uni
            and (2, 100, 0.37) in plain_uni and (3, 100, 0.37) in plain_uni and (65536, 8e6, 0) not in plain_uni):
        bad.append(f"MATLAB 的完全等距表和記載不同（{len(uni)}／{len(U2['axes'])}、秒軸 {sec_uni[:3]}、符號軸 sps {sym_uni}）")
    check(not bad, f"第四輪審查（哪些時間軸完全等距）vs MATLAB R2025a（uniform_axis2.json，{len(U2['axes'])} 條時間軸）：t0 + n/fs、"
                   "time_vector(N, sps·符號率, x0/符號率)、(x0 + n/sps)/符號率 三種寫法都和 MATLAB 逐位元相同，is_exactly_uniform（max(diff(t))==min(diff(t))）"
                   f"的判斷和 MATLAB 一致（{len(uni)} 條是）；DSV 預設符號率 1e6／2e6 的秒軸（N 1000／65536、sps 1～64、offset 0／3／0.5）"
                   "沒有一條完全等距（走取樣點路徑），符號率 1 的符號軸在 sps＝1／2／4／8／16／64 時全部完全等距、sps 3／10 不是；"
                   "fs＝1024、8192、2²⁰、4、0.5、1/3（t0＝100）與 N＝2／3 的 100 Hz 軸也是完全等距，0.37+n/100、n/1000、n/8e6 不是"
                   + (f"（問題：{bad[:4]}）" if bad else ""))

    # (2) smoothdata 在完全等距軸上（等距快速路徑）：427 組 × 8 方法
    TU = {k_: arrn(v_) for k_, v_ in U2["axes_smooth"].items()}
    SIG2 = {"x": arrn(U2["x"]), "xn": arrn(U2["xn"]), "xc": arrn(U2["xc_re"]) + 1j * arrn(U2["xc_im"])}
    texts2 = {"fraction": "t＝n/1024 上 ws＝W/Δt＝1.5／2.5／3.5／4.2／4.5／4.8／5.5／6.3／7／8／8.5／9.5／10.3／11.7／20.5／150.5／250.5／450.5（偶數 fix 的分數窗、ws<2、"
                          "N<fix(ws)<2N、>2N）",
              "other_axis": "t＝0.25+n/4、0.375+n/8（DSV 符號軸）、100+3n（非 2 的冪次間隔，含整數 ws 的邊界 tie）配 ws 2.5／4.5／8／8.5／10.3／11.7",
              "nan": "含 NaN（gaussian 仍走等距路徑、局部迴歸改走取樣點路徑）ws 4.5／8／8.5", "complex": "複數 ws 4.5／8.5",
              "auto": "自動視窗 SmoothingFactor 0.25／0.1／0.6 在 n/1024 與 100+3n 上", "sgolay_degree": "sgolay Degree 上限（ws 8.5／4.5／2.5／10.3 配 1～9、"
              "自動視窗配 60 與 SF 0.05 配 9 → degreeAutoClash、degreeTooLarge）", "huge": "視窗 1e30（樣本模式有／無 SamplePoints、n/1024、0.37+n/100）與 1e308"
              "（n/1024：ws 溢位成 Inf，rlowess／rloess 丟 wrongWindowLength）"}
    for grp in ("fraction", "other_axis", "nan", "complex", "auto", "sgolay_degree", "huge"):
        bad = []
        cases_ = [c for c in U2["cases"] if c["group"] == grp]
        worst2 = 0.0
        for c in cases_:
            tv = None if c["axis"] == "samples" else TU[c["axis"]]
            W_ = None if c["W"] in ([], None) else c["W"]
            tag = f"{c['axis']} {c['signal']} {c['method']} ws={c['ws']} d={c['degree']}"
            if tv is not None:
                if is_exactly_uniform(tv) != bool(c["uniform"]):
                    bad.append(f"{tag}：is_exactly_uniform")
                ws_ref = math.inf if c["ws"] is None else c["ws"]          # jsonencode 把 Inf（1e308/2⁻¹⁰ 溢位）寫成 null
                if W_ is not None and c["uniform"] and _uniform_window_samples(W_, tv) != ws_ref:
                    bad.append(f"{tag}：ws={_uniform_window_samples(W_, tv)!r}≠MATLAB {ws_ref!r}")
            try:
                r = smooth(SIG2[c["signal"]], c["method"], W_, tv, DEFAULT_FACTOR if c["sf"] in ([], None) else c["sf"],
                           None if c["degree"] in ([], None) else int(c["degree"]))
            except CleanError as e:
                if not (c["err"] and e.identifier == c["err"] and e.zh):
                    bad.append(f"{tag}：丟了 {e.identifier}（MATLAB {c['err'] or '可算'}）")
                elif c["err"] == "MATLAB:smoothdata:degreeTooLarge" and e.keyword != "sgDegreeError":
                    bad.append(f"{tag}：keyword {e.keyword}")
                continue
            if c["err"]:
                bad.append(f"{tag}：沒丟 {c['err']}")
                continue
            ref = arrn(c["y_re"]) + 1j * arrn(c["y_im"])
            ok, info = diff_info(r["y"], ref, SIG2["x"] if c["signal"] == "xn" else SIG2[c["signal"]])
            worst2 = max(worst2, nanmax_abs(np.asarray(r["y"], dtype=complex) - ref) / nanmax_abs(SIG2[c["signal"]]))
            okw = float(r["winsz"]) == float(c["winsz"])
            okd = (r["warning"] == WARN_DEGREE_KEYWORD) == (c["warn"] == "MATLAB:smoothdata:degreeAutoClash") and (c["warn"] in ("", "MATLAB:smoothdata:degreeAutoClash"))
            if not (ok and okw and okd):
                bad.append(f"{tag}：" + ("" if ok else info) + ("" if okw else f" winsz {r['winsz']}≠{c['winsz']}") + ("" if okd else f" warning {r['warning']}≠{c['warn']}"))
        check(not bad, f"第四輪審查（完全等距軸，{grp}，{len(cases_)} 組）vs MATLAB R2025a smoothdata（uniform_axis2.json）：{texts2[grp]}——y（rtol／atol 1e-12，"
                       f"實際最大相對差 {worst2:.2g}）、winsz、警告、錯誤代號逐筆一致" + (f"（不一致 {len(bad)}：{bad[:3]}）" if bad else ""))
    bad = []
    for s_ in U2["small"]:
        try:
            r = smooth(arrn(s_["x"]), s_["method"], s_["W"], arrn(s_["t"]))
        except CleanError as e:
            bad.append(f"N={len(s_['x'])} {s_['method']} W={s_['W']}：{e.identifier}")
            continue
        if s_["err"] or not (np.allclose(r["y"], arrn(s_["y"]), rtol=1e-12, atol=1e-12 * nanmax_abs(arrn(s_["x"])))
                             and float(r["winsz"]) == float(s_["winsz"]) and is_exactly_uniform(arrn(s_["t"])) == bool(s_["uniform"])):
            bad.append(f"N={len(s_['x'])} {s_['method']} W={s_['W']}：{r['y']}≠{s_['y']}")
    check(not bad, f"第四輪審查（N＝2／3 的短時間軸，{len(U2['small'])} 組）vs MATLAB：[0.37 0.38]（只有一個 Δt，永遠完全等距）、[0.37 0.38 0.39]、[0 0.25 0.5] "
                   "配 ws 1.5／2.5／3／4.5 × 8 方法，y 與 winsz 一致" + (f"（不一致：{bad[:3]}）" if bad else ""))

    # (3) 權重全 0 的窗與 Inf 的穩健窗（zero_weight.json）：MATLAB 改用等權重；時間軸（非完全等距）的差異是 MATLAB 的結果在
    # ~1e-41 tricube 權重的近奇異系統上的捨入垃圾（同 S125），逐一釘住
    xz = arrn(ZW["x"])
    t100 = time_vector(200, 100.0, 0.37)
    axz = {"none": None, "fs1024": np.arange(200.0) / 1024, "fs100": t100}
    known_z = {   # (集合, 方法, 軸／訊號, W) → (差超過 1e-12·max|x| 的點數, 最大差位置, DSV 在該點, MATLAB 在該點)
        ("robust", "rloess", "fs100", 0.04): (4, 3, 0.529602085579866, -0.10114757168794641),
        ("robust", "rloess", "fs100", 0.045): (4, 3, 0.529602085579866, -0.10114757168794641),
        ("robust", "rloess", "fs100", 0.05): (4, 3, 0.529602085579866, -0.10114757168794641),
        ("robust", "rloess", "fs100", 0.07): (6, 127, 1.8949601962208285, 1.9413151872852265e+24),
        ("nanwin", "loess", "xr1", 0.06): (1, 20, -0.9783578012065842, -4.019790199016797e+23),
        ("nanwin", "loess", "xr2", 0.1): (1, 20, 9.966666397476029, -1.589517163233133e+24),
        ("nanwin", "rlowess", "xr2", 0.1): (1, 20, -0.6555554658253437, -1.0999999102697888),
        ("nanwin", "rloess", "xr1", 0.05): (7, 3, 0.9095603516741666, 0.08556786671454364),
        ("nanwin", "rloess", "xr1", 0.06): (30, 28, -0.7547324039052341, -2.2588738111091844e+23),
        ("nanwin", "rloess", "xr2", 0.09): (2, 27, -0.7900217004209383, 6.514917949831008e+25),
        ("nanwin", "rloess", "xr2", 0.1): (2, 0, 1.0292996585950476, 1.0292996585983196),
        ("round", "rloess", "t1", 0.045): (4, 3, 0.529602085579866, -0.10114757168794641),
        ("round", "rloess", "t2", 0.045): (4, 3, 0.529602085579866, -0.10114757168794641),
        ("round", "rloess", "t1", 0.07): (6, 127, 1.8949601962208285, 1.9413151872852265e+24),
        ("round", "rloess", "t1", 0.075): (6, 127, 1.8949601962208285, 1.9413151872852265e+24),
        ("round", "rloess", "t2", 0.07): (165, 32, -0.3577884533408018, -4.075158265599536e+24),
        ("round", "rloess", "t2", 0.075): (165, 32, -0.3577884533408018, -4.075158265599536e+24),
    }
    seen_k = set()
    bad, facts = [], []
    n_match = 0

    def judge(key_, y, ref, xs):
        nonlocal n_match
        cnt_, i_ = diff_pin(y, ref, xs)
        same_nan = np.array_equal(np.isnan(np.asarray(y, dtype=complex)), np.isnan(np.asarray(ref, dtype=complex)))
        if key_ in known_z:
            seen_k.add(key_)
            kc, ki, kd, km = known_z[key_]
            if not (same_nan and cnt_ == kc and i_ == ki and math.isclose(float(np.real(y[i_])), kd, rel_tol=1e-12) and float(np.real(ref[i_])) == km):
                facts.append(f"{key_}：{cnt_} 點、i={i_}、DSV {np.real(y[i_])!r}、MATLAB {np.real(ref[i_])!r}≠記載 {known_z[key_]}")
        elif same_nan and cnt_ == 0:
            n_match += 1
        else:
            bad.append(f"{key_}：{cnt_} 點不同（i={i_}：{np.real(y[i_])!r} vs {np.real(ref[i_])!r}）")

    for c in ZW["robust"]:
        judge(("robust", c["method"], c["axis"], round(c["W"], 6)), smooth(xz, c["method"], c["W"], axz[c["axis"]])["y"], arrn(c["y"]), xz)
    t60 = time_vector(60, 100.0, 0.37)
    for c in ZW["nanwin"]:
        xs_ = arrn(ZW[c["sig"]])
        judge(("nanwin", c["method"], c["sig"], round(c["W"], 6)) if c["sp"] else ("nanwin-samples", c["method"], c["sig"], c["W"]),
              smooth(xs_, c["method"], c["W"], t60 if c["sp"] else None)["y"], arrn(c["y"]), xs_)
    xq_ = arrn(ZW["xq"])
    for c in ZW["robust_nan"]:
        judge(("robust_nan", c["method"], "xq", c["W"]), smooth(xq_, c["method"], c["W"])["y"], arrn(c["y"]), xq_)
    for c in ZW2["dmax"]:
        xs_ = arrn(c["x"])
        judge(("dmax", c["method"], c["case"], c["W"]), smooth(xs_, c["method"], c["W"])["y"], arrn(c["y"]), xs_)
    x2_ = arrn(ZW2["x"])
    t2_ = arrn(ZW2["t2"])
    if not (np.array_equal(t2_, (37.0 + np.arange(200.0)) / 100.0) and int(np.count_nonzero(t2_ != t100)) == 46):
        facts.append("t2＝(37+n)/100 應和 0.37+n/100 在 46 點差 1 ulp")
    R2 = {}
    for c in ZW2["rounding"]:
        y_ = smooth(x2_, c["method"], c["W"], t100 if c["axis"] == "t1" else t2_)["y"]
        R2[(c["axis"], c["method"], c["W"])] = (y_, arrn(c["y"]))
        judge(("round", c["method"], c["axis"], round(c["W"], 6)), y_, arrn(c["y"]), x2_)
    em_ = np.abs(R2[("t1", "rloess", 0.07)][1] - R2[("t2", "rloess", 0.07)][1])
    ed_ = np.abs(R2[("t1", "rloess", 0.07)][0] - R2[("t2", "rloess", 0.07)][0])
    if not (float(em_.max()) == 4.075158265599536e+24 and int(np.argmax(em_)) == 32 and int(np.count_nonzero(em_ > 1e-12 * 6.25)) == 163
            and math.isclose(float(ed_.max()), 1.6390526410946602, rel_tol=1e-12) and int(np.count_nonzero(ed_ > 1e-12 * 6.25)) == 1):
        facts.append(f"rloess 0.07 s 兩種捨入的 t：MATLAB 自己差 {em_.max():.4g}（163 點）、DSV 差 {ed_.max():.4g}（1 點）≠記載")
    for m_ in ("lowess", "loess", "rlowess"):
        for W_ in (0.045, 0.07, 0.075):
            if float(np.max(np.abs(R2[("t1", m_, W_)][1] - R2[("t2", m_, W_)][1]))) > 1e-12 * 6.25:
                facts.append(f"MATLAB {m_} {W_} 兩種捨入的 t 應一致")
    if set(known_z) - seen_k:
        facts.append(f"記載的已知差異沒有出現：{sorted(set(known_z) - seen_k)}")
    # 補充檢查（near_singular_ref.json；缺檔時略過這一項）：近奇異窗的數字
    if NS is not None:
        xi_ = arrn(NS["x"])
        lo_i, hi_i, _, _ = _borrowed_bounds(t100, 0.045)
        yi_ = np.empty(200)
        _local_fit(xi_, t100, lo_i, hi_i, 2, True, arrn(NS["rw"]), yi_)
        d3 = t100[0:5] - t100[2]
        w3 = _tricube(d3)
        if not (math.isclose(float(arrn(NS["time_rw"])[2]), 214359296.11085677, rel_tol=1e-12) and float(arrn(NS["integer_rw"])[2]) == float(xi_[2])
                and math.isclose(float(yi_[2]), float(xi_[2]), rel_tol=1e-12) and math.isclose(float(w3[4]), 5.7731717737991426e-43, rel_tol=1e-12)
                and math.isclose(float(arrn(NS["w_window3"])[4]), float(w3[4]), rel_tol=1e-12) and w3[0] == 0.0
                and np.allclose(_local_regression(xi_, t100, 0.045, 2, True, False, "loess", False), arrn(NS["time_none"]), rtol=1e-12, atol=1e-12 * 6.25)):
            facts.append(f"補充檢查：MATLAB 時間軸 {arrn(NS['time_rw'])[2]!r}、整數軸 {arrn(NS['integer_rw'])[2]!r}、DSV {yi_[2]!r}、x {xi_[2]!r}、w {w3.tolist()}")
    errs_ = {(e_["method"], math.inf if e_["W"] is None else e_["W"]): e_["id"] for e_ in ZW["inf_window"]}   # jsonencode 把 Inf 寫成 null
    for (m_, W_), id_ in errs_.items():
        try:
            smooth(xz, m_, W_, None if not math.isfinite(W_) else axz["fs1024"])
            if id_:
                bad.append(f"{m_} W={W_} 沒丟 {id_}")
        except CleanError as e:
            if e.identifier != id_:
                bad.append(f"{m_} W={W_} → {e.identifier}（MATLAB {id_ or '可算'}）")
    check(not bad, f"第四輪審查（權重全 0 的窗）vs MATLAB R2025a（zero_weight.json／zero_weight2.json）：中心是離群值且鄰點穩健權重也 0、或非 NaN 的點只剩 "
                   "tricube 0 的兩端時，MATLAB 改用等權重擬合窗內所有非 NaN 的點（第三輪之前 DSV 回 0；uniform_axis2.json 的 rlowess ws 4～5.5、rloess 6.3～9.5 "
                   f"因此差到 0.63）；樣本模式、n/1024、含 NaN（tricube 的 dmax 算整個窗）與穩健＋NaN 的 {n_match} 組逐筆一致；W＝1e308／realmax 配 n/1024 的 "
                   "rlowess／rloess 丟 MATLAB:smoothdata:wrongWindowLength、其他方法可算，W＝Inf 丟 needsFiniteWindows" + (f"（不一致：{bad[:4]}）" if bad else ""))
    check(not facts, f"已知差異（{len(known_z)} 組，都在不是完全等距的 0.37+n/100 時間軸、局部迴歸 loess／rloess／rlowess）：MATLAB 的輸出在近奇異的窗是捨入垃圾——"
                     "rloess 0.07 s 到 1.94e24、NaN 窗的 loess 到 1.59e24、rloess 到 6.5e25，0.045 s 的 rloess 左端 4 點（i=3：MATLAB −0.1011、DSV 0.5296）；"
                     "根因同 S125：時間軸上 |d|/dmax 在另一端不是剛好 1，tricube 是 ~1e-41 而不是 0，非零權重剛好次數+1，MATLAB 在這種近奇異的窗輸出捨入垃圾"
                     + ("" if NS is not None else "（補充檢查的參考資料不在，略過那一項）") + "；而且 t 只差 1 ulp（(37+n)/100，46 點）時 MATLAB 自己的 "
                     "rloess 0.07 s 差到 4.08e24（163 點；DSV 差 1.64，1 點），lowess／loess／rlowess 兩種 t 都一致；同樣的訊號與窗在樣本軸、n/1024 上全部一致。"
                     "DSV 的 WEIGHT_FLOOR 把 <1e-30 的權重當 0，結果有限、不隨 BLAS 變；每組的點數、位置、DSV 值（rel 1e-12）、MATLAB 值逐一釘住"
                     + (f"（文件記載的數字對不上：{facts[:4]}）" if facts else ""))

    # (4) 錯誤代號（error_ids.json）：MATLAB 實測的 identifier；MATLAB 接受但 DSV 依面板規則拒絕的 4 種列為決定
    bad = []
    x20 = np.sin(np.arange(20.0) / 3.0)
    t20 = np.arange(20.0) / 10.0
    calls = {
        "window 0": lambda: smooth(x20, "movmean", 0), "window -1": lambda: smooth(x20, "movmean", -1),
        "window NaN": lambda: smooth(x20, "movmean", math.nan), "window Inf": lambda: smooth(x20, "movmean", math.inf),
        "window Inf rlowess": lambda: smooth(x20, "rlowess", math.inf), "window 1e30": lambda: smooth(x20, "movmean", 1e30),
        "window complex": lambda: smooth(x20, "movmean", 3 + 1j), "window [3 4 5]": lambda: smooth(x20, "movmean", [3, 4, 5]),
        "window true": lambda: smooth(x20, "movmean", True), "window 2.5 samples": lambda: smooth(x20, "movmean", 2.5),
        "factor 1.5": lambda: smooth(x20, "movmean", None, None, 1.5), "factor -0.1": lambda: smooth(x20, "movmean", None, None, -0.1),
        "factor NaN": lambda: smooth(x20, "movmean", None, None, math.nan), "factor complex": lambda: smooth(x20, "movmean", None, None, 0.5j),
        "degree -1": lambda: smooth(x20, "sgolay", 5, None, 0.25, -1), "degree 2.5": lambda: smooth(x20, "sgolay", 5, None, 0.25, 2.5),
        "degree NaN": lambda: smooth(x20, "sgolay", 5, None, 0.25, math.nan), "degree Inf": lambda: smooth(x20, "sgolay", 5, None, 0.25, math.inf),
        "degree complex": lambda: smooth(x20, "sgolay", 5, None, 0.25, 2j), "degree with movmean": lambda: smooth(x20, "movmean", 5, degree=2),
        "degree with loess": lambda: smooth(x20, "loess", 5, degree=2), "degree 6 window 5": lambda: smooth(x20, "sgolay", 5, degree=6),
        "method foo": lambda: smooth(x20, "foo"), "sp length": lambda: smooth(x20, "movmean", 0.3, t20[:5]),
        "sp NaN": lambda: smooth(x20, "movmean", 0.3, np.r_[t20[:19], math.nan]), "sp Inf": lambda: smooth(x20, "movmean", 0.3, np.r_[t20[:19], math.inf]),
        "sp decreasing": lambda: smooth(x20, "movmean", 0.3, t20[::-1]), "sp duplicate": lambda: smooth(x20, "movmean", 0.3, np.r_[t20[:19], t20[18]]),
        "sp complex": lambda: smooth(x20, "movmean", 0.3, t20 + 1j), "x string": lambda: smooth(np.array(["a", "b", "c"]), "movmean", 3),
        "x Inf movmean": lambda: smooth(np.array([1.0, math.inf, 3.0]), "movmean", 3), "window false": lambda: smooth(x20, "movmean", False),
        "factor true": lambda: smooth(x20, "movmean", None, None, True), "factor [0.1 0.2]": lambda: smooth(x20, "movmean", None, None, [0.1, 0.2]),
        "factor string": lambda: smooth(x20, "movmean", None, None, "a"), "degree true": lambda: smooth(x20, "sgolay", 5, None, 0.25, True),
        "degree [1 2]": lambda: smooth(x20, "sgolay", 5, None, 0.25, [1, 2]), "window string": lambda: smooth(x20, "movmean", "abc"),
        "sp string": lambda: smooth(x20, "movmean", 0.3, np.array([repr(v) for v in t20])),
        "sp matrix": lambda: smooth(x20, "movmean", 0.3, np.column_stack([t20, t20])),
        "x matrix": lambda: smooth(np.column_stack([x20, x20]), "movmean", 3), "detrend x string": lambda: detrend(np.array(["a", "b", "c"])),
        "detrend x cell": lambda: detrend(np.array([1, "a", None], dtype=object)),
    }
    decided = {"window 2.5 samples": "smoothWindowDurationErrorSamples", "x Inf movmean": "dsv:smoothdata:infiniteInput",
               "x matrix": "dsv:smoothdata:notVector", "window string": "MATLAB:smoothdata:invalidWinsize"}
    if sorted(calls) != sorted(e_["case"] for e_ in EI):
        bad.append("error_ids.json 的案例和這裡的對照表不同")
    for e_ in EI:
        want_id = decided.get(e_["case"], e_["id"])
        try:
            calls[e_["case"]]()
            got_id, msg_ = "", ""
        except CleanError as ce:
            got_id, msg_ = ce.identifier, str(ce)
            if not ce.zh:
                bad.append(f"{e_['case']}：沒有繁中訊息")
        if got_id != want_id:
            bad.append(f"{e_['case']}：{got_id or '可算'}（應為 {want_id or '可算'}）")
        elif e_["id"] and e_["case"] not in decided and not msg_.startswith(e_["msg"].rstrip(".")):
            bad.append(f"{e_['case']}：英文訊息「{msg_}」和 MATLAB「{e_['msg']}」不同")
    if not (np.array_equal(smooth(x20, "movmean", True)["y"], smooth(x20, "movmean", 1)["y"])
            and np.array_equal(smooth(x20, "movmean", None, None, True)["y"], smooth(x20, "movmean", None, None, 1.0)["y"])):
        bad.append("視窗／SmoothingFactor 的 True 應等於 1（MATLAB 把 logical 當數值）")
    check(not bad, f"第四輪審查（錯誤代號）vs MATLAB R2025a（error_ids.json，{len(EI)} 種輸入）：noComplexWindows／needsFiniteWindows／invalidWinsize、"
                   "noComplex／invalidSmoothingFactor、needsFinites／negativeDegree／degreeNoSgolay／degreeTooLarge、invalidMethod、MATLAB:samplePoints:"
                   "SamplePointsLength／NonFinite／Sorted／Duplicate／Complex／InvalidDatatype、badArray、detrend 的 InvalidFirstInput 和英文訊息都和 MATLAB 相同；"
                   "true 當 1；DSV 自己的決定：樣本模式非整數窗（面板規則）、Inf 訊號、矩陣訊號、字串視窗（MATLAB 把它當成 NaN 旗標 → invalidNanflag）"
                   + (f"（問題：{bad[:5]}）" if bad else ""))

    bad = []
    # detrend：沒有斷點的 linear 不受 MAX_DESIGN_ELEMENTS 限制（1e7 點，第二輪誤拒成 tooManyBreakpoints）；真的有斷點才檢查 N×(斷點數+1)
    z7 = np.sin(np.arange(10_000_000) / 1e4) + 0.1
    t0_ = _time.time()
    yl = detrend(z7)
    tl = _time.time() - t0_
    if not (yl.shape == z7.shape and np.all(np.isfinite(yl)) and tl < 5.0):
        bad.append(f"detrend 1e7 linear：{tl:.2f} s 或非有限")
    if not (detrend(z7, "constant").shape == z7.shape and np.array_equal(detrend(z7, "piecewiselinear", [z7.size - 1]), yl)
            and np.array_equal(detrend(z7, "piecewiselinear"), yl)):
        bad.append("detrend 1e7 constant／斷點＝最後一個樣本（忽略）／piecewise 無斷點 應可算且等於 linear")
    try:
        detrend(z7, "piecewiselinear", [5_000_000])
        bad.append("1 個斷點×1e7（N×3 > 2²⁴）沒拒絕")
    except CleanError as e:
        if e.identifier != "dsv:detrend:tooManyBreakpoints":
            bad.append(f"1 個斷點×1e7 → {e.identifier}")
    del z7, yl
    rng3 = np.random.default_rng(5)
    xs5 = rng3.standard_normal(500) + 3.0 + 0.01 * np.arange(500)
    xc5 = xs5 + 1j * (rng3.standard_normal(500) - 2.0)
    W5 = np.column_stack([np.arange(500.0) / 499, np.ones(500)])
    for xv in (xs5, xc5):
        want_ls = xv - W5 @ np.linalg.lstsq(W5, xv, rcond=None)[0]
        if float(np.max(np.abs(detrend(xv) - want_ls))) > 1e-12:
            bad.append(f"閉合式 linear detrend vs lstsq：{np.max(np.abs(detrend(xv) - want_ls)):.3g}")
    if not np.allclose(detrend(np.array([1.0, 4.0])), 0.0, atol=1e-15):
        bad.append("N＝2 的 linear detrend 應為 0")
    # 超過 int64 的 Python int 視窗照 float 處理（10**30＝1e30，MATLAB 的 1e30 可算：uniform_axis2.json huge 組；10**400＝Inf → needsFiniteWindows）
    x7b = np.arange(7.0)
    if not np.array_equal(smooth(x7b, "movmean", 10 ** 30)["y"], smooth(x7b, "movmean", 1e30)["y"]):
        bad.append("視窗 10**30 應和 1e30 相同")
    try:
        smooth(x7b, "movmean", 10 ** 400)
        bad.append("視窗 10**400 沒拒絕")
    except CleanError as e:
        if e.identifier != "MATLAB:smoothdata:needsFiniteWindows":
            bad.append(f"視窗 10**400 → {e.identifier}")
    check(not bad, f"detrend 與大數視窗：detrend 1e7 點 linear {tl:.2f} s（沒有斷點不受 2²⁴ 上限，第二輪誤拒）、constant／斷點＝最後一個樣本（忽略）／piecewise 無斷點＝linear、"
                   "1 個真正的斷點×1e7（N×3 > 2²⁴）拒絕、閉合式＝lstsq（1e-12，含複數）、N＝2 歸零；Python int 視窗 10**30＝1e30（MATLAB 1e30 可算）、10**400 → needsFiniteWindows"
                   + (f"（問題：{bad[:6]}）" if bad else ""))

    # 大資料：1e5／1e6 點、50 個樣本寬的時間窗（走取樣點路徑）
    n = 1_000_000
    fs = 1000.0
    tt = time_vector(n, fs, 0.37)
    rng = np.random.default_rng(0)
    xx = np.sin(2 * np.pi * 3.0 * np.arange(n) / fs) + 0.1 * rng.standard_normal(n)
    w = 50 / fs
    times: Dict[str, float] = {}
    for name, m, x_, t_ in (("movmean 1e6", "movmean", xx, tt), ("movmedian 1e6", "movmedian", xx, tt), ("gaussian 1e6", "gaussian", xx, tt),
                            ("lowess 1e5", "lowess", xx[:100_000], tt[:100_000]), ("lowess 1e6", "lowess", xx, tt),
                            ("sgolay 1e6", "sgolay", xx, tt), ("rloess 1e5", "rloess", xx[:100_000], tt[:100_000])):
        t0 = _time.time()
        r = smooth(x_, m, w, t_)
        times[name] = _time.time() - t0
        if not (r["y"].shape == x_.shape and np.all(np.isfinite(r["y"]))):
            times[name] = math.inf
    t0 = _time.time()
    yd = detrend(xx, "piecewiselinear", [0.37 + 100.0, 0.37 + 500.0], tt)
    times["detrend 1e6"] = _time.time() - t0
    rm = smooth(xx, "movmean", w, tt)["y"]
    ok = (times["movmean 1e6"] < 2.0 and times["lowess 1e5"] < 5.0 and times["lowess 1e6"] < 30.0 and yd.shape == xx.shape
          and np.abs(rm[1000:-1000] - np.sin(2 * np.pi * 3.0 * np.arange(n) / fs)[1000:-1000]).max() < 0.2)
    check(ok, "效能（時間模式 50 樣本窗）：" + "、".join(f"{k} {v:.2f}s" for k, v in times.items())
              + "；movmean 1e6 < 2 s、lowess 1e5 < 5 s，結果有限且接近原弦波")
