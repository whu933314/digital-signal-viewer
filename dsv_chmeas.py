# -*- coding: utf-8 -*-
"""通道量測（MATLAB Spectrum Analyzer 的 CHANNEL MEASUREMENTS 分頁、Type＝Occupied BW）：佔用頻寬、通道功率、頻率誤差——
純 numpy、和 GUI 分開。ACPR 是另一個模組（dsv_acpr）的事，這裡不做。

兩條路徑：
A. scope 路徑 scope_channel_measure()／scope_measure_welch()——DSV 頻譜視窗要顯示的數字。規則來自 2026-10-24 實際跑一次
   MATLAB R2025a spectrumAnalyzer 的 22 個 obw_* 擷取（scope_capture/out，分析在 scope_capture/ANALYSIS.md §2 與 rules.json
   O1–O7；selftest 用 tests/matlab_ref/scope/obw_chpower/scope_obw_captures.json 逐筆重算）。這是 DSV 要重現的對象。
B. 工具箱函式 obw()／obw_time()／powerbw()／powerbw_time()／bandpower()——Signal Processing Toolbox 的函式，
   由 tests/matlab_ref/obw_chpower/ 的 MATLAB 數值逐筆驗證（位元級），放著供比對與一般用途。

A. scope 實際的做法（擷取證明；18 個數值擷取通道功率 ≤ 1.1e-13 dB、OBW ≤ 1.7e-10 Hz、頻率誤差 ≤ 8.4e-11 Hz，4 個 NaN 擷取相符；
   /opt/anaconda3 的 numpy 1.26 是 1.0e-13／1.9e-10／9.8e-11，selftest 的上限取實測的 2 倍以上餘裕 2.2e-13／4e-10／2e-10，見 SCOPE_TOL_*）：
- 餵進量測的是「顯示的 normal trace」（開 Max-Hold 也一樣是 normal trace：obw_real_2s_maxhold_2calls 餵 xr、0.1·xr 兩次，
  通道功率 1.9978 dBm＝21.9978 − 20），只看 MeasurementChannel 那一欄。
- 顯示頻譜本身（dsv_spectrum.welch 可直接重現）：periodic Hann、NFFT＝max(1024, WindowLength)、power＝|X|²/(Σw)²、
  power-density＝|X|²/(fs·Σw²)、RBW＝ENBW＝fs·Σw²/(Σw)²（Hann 1.5·fs/L）、雙邊格＝MATLAB centered（偶數 NFFT 時 Nyquist 在 +fs/2、
  −fs/2 不在格上）、單邊格 0..fs/2（內部 bin ×2、DC 與 Nyquist 不加倍）。
- O1 PSD＝顯示功率 / RBW；power-density 模式顯示值本身就是 PSD。兩種模式的 Channel Power 都是積分後的 dBm（10·log10(∫)+30，
  ReferenceLoad 1）：obw_real_2s_psd_span1250_2000_P99 和 power 模式的擷取一樣是 21.99782303361157 dBm。
- O2 積分：PSD 視為分段常數，第 k 個 bin 蓋 [f_k − df/2, f_k + df/2]——**第一、最後一個 bin 也一樣**（邊界 f_first − df/2、
  f_last + df/2）；累積功率 C(f) 是這個階梯函數的精確積分（相鄰邊界之間線性）；總功率＝C(b) − C(a)。
  內部頻帶和 obw() 的累積內插完全相同，只在頻譜兩端不同：obw()（每格寬度規則）的端點邊界在 f_first／f_last。
  證明：obw_real_1s_startstop_0_5000_P99（單邊 [0 5000]）scope 25.784661511989 dBm／4237.047845900731 Hz／−369.536400699991 Hz，
  bin 邊界版 1e-11 內相符；obw() 邊界版給 25.788999787501／4239.269468256199／−370.801478181158（差 4.3e-3 dB／2.2 Hz／1.3 Hz，
  因為 scope 只把 DC bin 的一半算進 [0, 5000]）。selftest 兩種都算出來對照。
- O3 邊緣：f_lo＝C⁻¹(C(a) + (100−P)/200·tot)、f_hi＝C⁻¹(C(a) + (100+P)/200·tot)；Occupied BW＝f_hi − f_lo。
- O4 Frequency Error＝(f_lo + f_hi)/2 − CF；Span and Center 模式 CF＝Center Frequency，Start and Stop 模式 CF＝(Start + Stop)/2
  （obw_real_2s_startstop_500_3000_P99 −192.3556870933 Hz＝1557.644 − 1750 等 7 個 start/stop 擷取，≤ 8.4e-11 Hz）。
- O5 頻帶不在 [f_first, f_last] 之內（a < f_first 或 b > f_last）→ Channel Power、Occupied BW、Frequency Error 三個都 NaN，
  屬性照常接受、沒有錯誤也沒有警告、不裁切（4 個擷取；[−5000 5000] 在雙邊格上是 NaN，因為 f_first＝−4995.117；單邊 [0 5000]
  兩端都是 bin 所以有數字）。
- O7 第一次啟用時的 auto-span（寫進 ChannelMeasurements 設定）：中心＝顯示 x 軸範圍的中點、Span＝寬度/5、AdjacentBW＝寬度/10、
  ACPROffsets＝[4 7]·寬度/20（obw_real_1s_autospan_defaults 單邊 [0 5000]：2500／1000／500／[1000 1750]；雙邊 [−5000 5000] 給的
  0／2000／1000／[2000 3500] 正好是預設值）。「顯示範圍」是 scope 的 x 軸範圍（±fs/2 或 0..fs/2），不是 bin 格的第一、最後一點
  （用 −4995.1..5000 會得到 Span 1999.02）。scope_auto_span() 算這組數字，何時觸發由 GUI 決定（見未定）。
- 被排除的做法（分析殘差）：整格加總、邊緣取 bin 中心（OBW 差 0.5～19 Hz）；顯示功率直接加總不除 ENBW（+1.76 dB）；
  bandpower 的向外取整格（1e-4～4.8e-2 dB）；obw() 端點邊界（上述 4.3e-3 dB）。

B. 工具箱函式（MATLAB R2025a；程式是自己寫的，tests/matlab_ref/obw_chpower/ 是 MATLAB 算出的數值，selftest() 逐筆比對；
產生它們的腳本是 ref_obw_chpower.m（第一輪：數值）、ref_obw_r3.m（第三輪：邊界情況、錯誤訊息、分派，165 筆）、ref_obw_r4.m
（第四輪：single／整數／half 的資料與純量引數，63 筆）、ref_obw_r5.m（第五輪：Pxx／Sxx／F／X 的類別檢查，42 筆）與 ref_obw_r6.m
（第六輪：half 的屬性規則、「Instead its type was」的省略規則、空的非數值 FREQRANGE、每筆釘一條規則的數值案例、single 非整數 F 的
bandpower，159 筆），只呼叫 obw／powerbw／periodogram／pwelch／enbw／bandpower／validateattributes）：
- obw(Pxx, F, [RBW], FREQRANGE, P)（MATLAB 的 obw；照 MATLAB 的參數解析與每格寬度規則）：
  1. 每個 bin 的寬度＝相鄰頻率差；少掉的那一格寬度＝(F_end − F_1)/(N−1)，F_1＝0（單邊或未置中）時補在最後、否則（置中）補在最前。
  2. bin 功率＝Pxx × 寬度；累積功率 C＝[0, p_1, p_1+p_2, …]（N+1 個），對應邊界 B＝[F_1, 相鄰頻率的中點…, F_N]（N+1 個）：
     每個 bin 的功率視為在相鄰中點之間線性累積。
  3. 範圍 [a, b]（沒給就是 [F_1, F_N]）：P_lo＝C 在 a 的線性內插、P_hi＝C 在 b 的線性內插——取第一個 B_i ≥ 頻率的 i，在 i 與 i−1
     之間內插（i 是第一個時用第一、二個），tot＝P_hi − P_lo。
  4. 門檻 T_lo＝P_lo + (100−P)/200·tot、T_hi＝P_lo + (100+P)/200·tot；f_lo、f_hi＝反過來從 C 內插回頻率——取第一個 C_i ≥ 門檻的 i
     （i 是第一個時改用第二個），在 (C_{i−1}, B_{i−1})–(C_i, B_i) 之間線性內插；找不到 → NaN。
  5. bw＝f_hi − f_lo、pwr＝P/100·tot。功率譜形式 obw(Sxx, F, RBW, …)：先 Pxx＝Sxx/RBW 再照上面做（RBW 要 ≥ 平均 bin 間距）。
  6. 時域輸入 obw(x, fs)＝這裡的 obw_time()：矩形窗（和 MATLAB obw 一樣）、NFFT＝N 的 periodogram（實數 → 單邊、複數 → 置中；
     沒給 fs 就用 2π，單位 rad/sample；fs 是空的（含 ''）時是 2π 轉成 fs 的類別，見下面「空的 fs」），
     再照上面做。只有 1 個樣本（[1.0]、0-d 的 3.0）時 MATLAB 的 periodogram 丟 signal:computeperiodogram:NDMatrixUnsupported
     「The input must be a non-empty column vector or two-dimensional matrix.」（ref_obw_r3 實測；就算 FREQRANGE 超出範圍也是先丟它），
     這裡照丟；2 個樣本起可算（[1;2] 與 [1 2] 結果相同，實測）。
  浮點運算的寫法選成和 MATLAB 輸出位元一致的那一種（內插寫成 y₀ + (y₁ − y₀)·(x − x₀)/(x₁ − x₀)，步驟 3 的反向內插也一樣），
  所以在相同的 PSD 上結果位元級一致（selftest 用 1e-12 比）。矩陣輸入（N × 通道數）逐欄算；(1 × N) 的列向量和 MATLAB 一樣當成
  一個通道。
- powerbw（x dB 頻寬；MATLAB 的 powerbw）——另一種量測，不是 scope 的 Occupied BW，放著供比對：
  參考位準＝沒給範圍時 PSD 的最大值（單邊時 DC bin ×2；時域輸入且 N 為偶數時 Nyquist bin 也 ×2）、有範圍時範圍內 bin 的
  平均 PSD（Σ功率/Σ寬度）；再乘 10^(−|R|/10)，R 預設 10·log10(1/2)（約 3.01 dB）。從峰值（沒給範圍）或範圍中心兩側最近的 bin
  （有範圍）出發，往低頻找最後一個、往高頻找第一個 PSD ≤ 參考位準的 bin，在「頻率 對 log10(PSD)」上線性內插（PSD 先以 realmin
  墊底）；那一側沒有這種 bin 就用頻譜端點；找到的剛好是出發的 bin → NaN。參考位準是 0（全零頻譜）時 log10 給 −Inf，結果照 IEEE
  算成 NaN／±Inf，不丟錯（MATLAB 同樣不檢查）。功率＝兩緣之間用 obw 的累積功率內插（NaN 邊緣 → NaN）。powerbw_time() 是時域形式。
  PSD 含 NaN：MATLAB 不擋（validateattributes 的 nonnegative／positive 只找 < 0／≤ 0 的值，NaN 通過），max 與 max(Pxx, realmin)
  都忽略 NaN（NaN 的 bin 墊成 realmin），NaN 的 bin 不算「≤ 參考位準」；所以 powerbw([1;NaN;5;2;1], 0:10:40) 是
  (27.567854875858615, −0.0031469021983124373, 27.564707973660301, NaN)、整欄 NaN 時參考位準 NaN → 兩側都取端點，obw 則是全 NaN
  （ref_obw_r3 的 *_pxx_nan*／allnan／nanpeak 實測）。參考位準 Inf × 10^(−|R|/10)＝0（|R| 很大時下溢）＝NaN 也照 IEEE 算、不印警告。
- bandpower(Pxx, F, [range], 'psd')（MATLAB 的 bandpower）：沒範圍＝Σ Pxx×寬度（寬度規則同上）；有範圍時取「最後一個 F ≤ a」到「第一個 F ≥ b」
  的 bin，最後一格寬度算 0。驗證照 MATLAB bandpower 自己的順序（和 obw／powerbw 的參數解析不同）：Pxx＝double/single → 2d → finite → real
  （負值可以）；F＝numeric → vector → finite → real → increasing → 元素數＝Pxx 的列數（MATLAB:bandpower:incorrectNumel）；
  FREQRANGE＝numeric → vector → finite → real → 元素數 2 → increasing → 落在 F 內（signal:bandpower:FreqRangeOutOfBounds）；
  空的 F／FREQRANGE 不算向量（丟 expectedVector，實測）。只有一個元素的 F 可以過，結果和 MATLAB 一樣是 0/0＝NaN（bandpower(1, 0, 'psd')
  實測）。其他驗證之前先檢查字串引數：依引數順序（Pxx、F、FREQRANGE）看，是字串而不是 'psd'（不分大小寫）→
  signal:bandpower:IncorrectStringPsd；是 'psd' 的照樣往下傳、被類別檢查擋成 invalidType。bandpower(x)（時域）＝mean_square：字串 x
  （'psd' → FreqVectorMissing、其他含 '' → IncorrectStringPsd），X 驗 double/single → 2d → finite
  （名稱 X、第 1 個引數），逐欄算 mean(|x|²)（向量回 float、矩陣回每欄一個值）。空輸入（實測）：Python 的 1-D []（1-D 序列一律當
  列向量，即 MATLAB 的 zeros(1,0)，轉成 0×1）→ NaN；(0 × 2) → [NaN NaN]；(0 × 0)＝MATLAB 的 [] 與 (3 × 0) → 1×0 的空結果（shape (0,)）。
- 錯誤照 MATLAB 的識別碼與英文訊息丟 ChannelMeasureError（另附繁體中文 .zh）；第一輪 10 個、第三輪 99 個錯誤是 MATLAB 實測，
  其餘依 validateattributes 的固定句型與 MATLAB 的錯誤訊息原文，檢查順序照各函式
  validateattributes 的屬性順序：Pxx／Sxx＝類別（double/single）→ 2d → real → nonnegative；F＝類別（double/single；PSD 形式與功率譜形式
  都是）→ real → vector → finite → 長度要等於頻譜列數；RBW＝類別（numeric）→ real → finite → positive → scalar → ≥ 平均 bin 間距；
  FREQRANGE＝類別（numeric）→ real → finite → increasing → size 1×2；P＝類別（numeric）→ real → nonempty → positive → scalar → < 100；
  R＝類別（numeric）→ real → nonempty → finite → scalar → nonzero（識別碼 expectedNonZero，大寫 Z）；時域的 X＝類別（double/single）→
  2d → finite、Fs＝類別（numeric）→ real → finite → scalar → positive（識別碼裡的函式名是被呼叫的那個函式，所以 powerbw_time 的這些錯誤
  是 MATLAB:powerbw:*）。nonnegative／positive 不看 NaN（P＝NaN 過 positive、被 < 100 擋成 notLess；Pxx 含 NaN 照算）。
  非數值輸入丟 invalidType：{'numeric'} 印成「double, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64」；最後一行
  「Instead its type was <類別>.」char（''、'a'、'abc'）和**空的 cell**（{}、cell(0,2)、cell(1,0)；Python 的空 dtype=object 陣列）不印，
  非空的 cell 與空的 int16／logical／half／struct／datetime／string／duration 都印（ref_obw_r3 與 ref_obw_r6 的 v*／e* 實測）；類別名稱照
  Python 型別對應（str／bytes → char、bool → logical、參差不齊的序列與物件 → cell、dict → struct、函式 → function_handle、datetime64 →
  datetime、timedelta64 → duration、numpy 整數 dtype → 同名 int8…uint64、float16 → half；見下面「資料類別的規則」）。'<'／'>=' 句型的數字是 %g
  （0.333333、3.33333e-08、inf；實測），比較值是 NaN（F＝[1e308 −1e308 1e308] 的平均間距）時丟 MATLAB:validateattributes:badComparison。
- DSV 自己的防護（識別碼 dsv:chmeas:*）：任何一次要處理超過 2²⁴ 個元素的頻譜或訊號丟 TooLarge，不讓它跑到當掉；
  measure_welch／scope_measure_welch 的 kind 不是 'psd'／'power' 丟 InvalidKind、res 缺少要用的鍵（psd／power／f／rbw）丟 MissingKey；
  scope_band 的 mode 不是 'span'／'startstop' 丟 InvalidMode；scope_auto_span 的顯示範圍不是有限實數丟工具列的 start／stop 訊息、
  顛倒或相等丟 StartStopOrder（這些都是 API 用錯，沒有 MATLAB 對應，但一律是 ChannelMeasureError，不讓 KeyError／TypeError 漏出去）。

未定／自行決定（擷取沒有涵蓋、分析列為 unresolved 的部分；都照解出來的／預設行為做，不再多猜）：
- 頻帶邊緣落在 (f_first − df/2, f_first) 或 (f_last, f_last + df/2) 時 scope 給 NaN 還是數字沒有擷取（rules.json unresolved）；
  這裡照 O5 嚴格判「a < f_first 或 b > f_last → NaN」。
- auto-span 的觸發條件未解（obw_real_1s_autospan_defaults 有套用、acpr_cplx_2s_autospan_defaults 沒有）：模組只提供公式
  scope_auto_span()，GUI 自行決定何時呼叫（建議：啟用時頻帶不在顯示範圍內才套）。
- Start ≥ Stop：scope 的 UI 只擋 NaN，MATLAB 的量測結果沒有擷取；這裡丟 dsv:chmeas:StartStopOrder，GUI 應先擋。
- 頻帶內功率全為 0：C⁻¹ 的內插 0/0 → 邊緣 NaN、通道功率 10·log10(0)＝−Inf dBm，不丟錯（scope 行為未擷取）。
- 顯示 trace 若含 NaN／負值一律拒絕（dsv:chmeas:expectedNonnegative）；dsv_spectrum.welch 的輸出不會有這種值。
- 時域輸入的錯誤順序（實測）：X 的類別／2d／finite → Fs → 空訊號（[]、0×1、1×0、N×0 都是）MATLAB:periodogram:expectedNonempty
  「Expected X to be nonempty.」→ 1 個樣本 NDMatrixUnsupported → FREQRANGE（時域形式的訊息不帶引數編號：「Expected FREQRANGE to be
  of size 1x2, but it is of size 1x1.」）。
- 空的 fs（obw(x, [])／powerbw(x, [])）：MATLAB 不丟錯，結果等於把 2π 轉成 fs 的類別再轉 double（ref_obw_r3 的 obw_fs_*_empty 全部實測）：
  double 與複數 double 的空陣列＝2π（和沒給 fs 完全相同）；single 與複數 single＝single(2π)＝6.2831854820251465；half＝6.28125；
  整數類別（int8／uint8／uint16…）四捨五入成 6；logical＝true＝1（obw(xr, logical([])) bw 0.42428200676253724）；char（Python 的 ''，
  np.asarray('') 雖有 1 個元素但 MATLAB 的 '' 是空的）＝char(6)＝6（bw 2.5456920405752235）；cell／datetime／duration 的空陣列丟
  MATLAB:cast:UnsupportedPrototype「Unsupported data conversion from 'double' to '<類別>'.」。MATLAB 的 string／空 struct 在 Python 沒有對應。
- 分派（已知差異，ref_obw_r3 實測 MATLAB 那一邊）：MATLAB 的 obw／powerbw 靠引數形狀分派形式（MATLAB 的參數解析：第 2 個引數是空的
  或單一數值 → 時域形式 (x, fs)，否則它是 F；再看第 3 個引數是單一數值 → 功率譜形式、它是 RBW，否則是 FREQRANGE）。Python 這裡用
  obw()／obw_time() 兩個函式加 rbw 關鍵字，沒有歧義，所以 MATLAB 會改走別的形式的呼叫一律在任何驗證之前丟 DSV 自己的識別碼
  （不冒用 MATLAB 識別碼）：obw()／powerbw()／channel_measure() 的 F 是空的或只有一個元素 → dsv:chmeas:FTooShort（MATLAB 的
  obw(p5, []) 會把 p5 當時域訊號算出數值、obw(p5, 0) 丟 Fs 的 expectedPositive、obw(p5, 'a') 丟 Fs 的 invalidType）；rbw 不是單一數值
  （含 []）→ dsv:chmeas:RBWNotScalar（MATLAB 的 obw(p5, f5, [20 30], 99) 算出 [20 30] 範圍的佔用頻寬）；PSD 形式的 freqrange 只有一個
  元素 → dsv:chmeas:FreqRangeScalar（MATLAB 的 obw(p5, f5, 1000, 99) 把 1000 當 RBW、丟 FREQRANGE 的 size 1×2）；obw_time()／
  powerbw_time()／periodogram_psd() 的 fs 有兩個以上元素（含 'abc'、2 個元素的 cell）→ dsv:chmeas:FsNotScalar（MATLAB 的
  obw(xr, [1e4 2e4])／powerbw(xr, 'abc') 把它當 F、xr 當 Pxx，丟 Pxx 的 expectedNonnegative）。selftest 驗證 Python 呼叫丟這些識別碼、
  且 MATLAB 的結果由它實際走的那種形式的 Python 呼叫逐筆重現。單一數值的 fs（含 1 個字元的 'a'、True、複數）MATLAB 確實走時域，
  照 MATLAB 識別碼丟（實測）。
- channel_measure／frequency_error 的 center、powerbw 的 time_len、公開輔助函式 bin_widths／cumulative_power 的輸入都是 DSV 自己的引數
  （MATLAB 的 obw 沒有 center；time_len 對應 MATLAB 時域形式的樣本數判斷），不合格一律丟 ChannelMeasureError、不讓 TypeError／
  ValueError／IndexError 漏出去：center 要是有限實數純量，否則丟工具列的 center 訊息（和 scope 路徑同一個檢查；字串 '0'、NaN、
  [0 1] 都拒絕）；time_len 只能是 None 或非負整數純量（dsv:chmeas:InvalidTimeLen）；輔助函式丟 dsv:chmeas:invalidType／expectedReal／
  expected2D／expectedVector 或 dsv:chmeas:FreqVectorMismatch（scope 路徑的長度不符也是這個；訊息借 signal:psdparserange:FreqVectorMismatch 的），cumulative_power
  的 1-D 或 (1 × N) pxx 當一個通道（C 是 N+1 × 1）；frequency_error 的 flo／fhi 形狀不同丟 dsv:chmeas:ShapeMismatch。
  powerbw_time 的樣本數照 MATLAB 的規則算（向量看元素數、矩陣看列數）。
- 模組會丟的 MATLAB 識別碼與訊息句型（expectedScalar／Vector／2D／Nonempty／Finite／Real／Positive／Nonnegative／Increasing／NonZero、
  incorrectSize／incorrectNumel、notLess／notGreaterEqual、invalidType、badComparison、cast:UnsupportedPrototype 與 signal:* 的固定訊息）
  都在 ref_obw_r3（或第一輪的 errors）有 MATLAB 實測的樣本；其餘組合照同一個句型代入名稱與引數編號。
- 已知差異（資料類別，只有這一條；MATLAB 那一邊由 tests/matlab_ref/obw_chpower/ref_obw_r4.m 實測、存在 ref_obw_r4.json，selftest 7c 逐筆釘住）：
  single（np.float32／np.complex64）的頻譜或訊號（Pxx／Sxx／F／X，任何一個是 single 就算）：MATLAB 全程用單精度算、回傳 single；
  這裡一律先放寬成 double 再算、回傳 float64，結果＝MATLAB 對 double(single 資料) 的結果（ref_obw_r4 的 d_* 那一組，rtol 1e-12），
  和 MATLAB 的 single 結果差在單精度的捨入：s_obw_psd／s_obw_psd_pxxonly／s_obw_psd_fonly／s_obw_mat 最大相對差 7.74e-08
  （bw 39.45 對 MATLAB 39.449996948242188、flo 0.275 對 0.27500000596046448）、s_obw_time 1.87e-06（bw 4242.8200652533296 對
  4242.826171875）、s_obw_time_cplx 1.76e-05、s_pbw_psd 9.73e-08、s_pbw_time 7.05e-05、s_bp_time 1.12e-07、s_bp_time_cplx 6.06e-08；
  s_bp_psd（110）與 s_bp_psd_range（100）剛好相同（selftest 把這 12 個數釘死，變了就會失敗）。bandpower 的 F 是 single 時 MATLAB 也用
  單精度算、回傳 single：整數值的 F（ref_obw_r6 s3_bp_f_single_int）兩邊都是 110；非整數的 F＝single([0.1 10.1 20.1 30.1 40.1])
  （s1_bp_f_single_frac）MATLAB 的單精度結果剛好是 110，DSV 對 double(single(F)) 算出 109.99999847076833＝MATLAB 對 double(single(F)) 的
  結果（s2_bp_f_double_of_single_frac，位元級），和 MATLAB single 的 110 相對差 1.39e-08（selftest 7f 釘住這三個數）。DSV 頻譜視窗餵的都是
  double（dsv_spectrum.welch 的輸出），所以不重現單精度運算。只有純量引數是 single（P、R、RBW、FREQRANGE、Fs、bandpower 的 FREQRANGE）時
  MATLAB 回 double、數值＝double(single 值) 的呼叫（實測 s_obw_P／s_obw_P_frac／s4_bp_range_single_frac 等 10 筆，位元級相同），這裡也一樣，沒有差異。
- 資料類別的規則（不是差異；ref_obw_r4 的 i_*／h_* 10 筆＋ref_obw_r5 42 筆實測，selftest 7c／7e 釘住識別碼與完整訊息）：Pxx／Sxx／F／X
  只收 double／single（validateattributes 的 {'double','single'}）——numpy 的整數 ndarray／整數純量（int8…uint64）、float16（MATLAB 的
  half）與 bool（logical）丟 invalidType「Expected input number 1, Pxx, to be one of these types:\n\ndouble, single\n\nInstead its type
  was int16.」（類別名照 dtype：int16／uint8／…／half／logical；功率譜形式叫 Sxx），而且類別檢查先於其他一切——F、長度不符、負值、三維、
  P、R、Fs、空訊號、1 個樣本（ref_obw_r5 的 o_* 14 筆實測，例如 obw(int32([]), 1e4) 丟的是 X 的 invalidType 而不是 expectedNonempty）。
  Python 的 int／list／tuple 當 double：MATLAB 的數字字面值 [1;2;5;2;1] 本來就是 double（ref_obw_r5 class_of_literal／m_obw_literal 實測），
  Python 寫 [1, 2, 5, 2, 1] 對應的是它、不是 int64 陣列；只看最外層型別，所以 list 裡裝 numpy 整數純量也算字面值（MATLAB 的
  [int16(1) int16(2)] 是 int16，這一點沒有模仿、沒有實測）。numpy 的 column_stack([double, int16]) 升成 float64、MATLAB 的 [p5 int16(p5)]
  是 int16（class_of_mixed_concat 實測）——這是 numpy 與 MATLAB 串接規則的差異，不在這個模組裡。其餘引數（P、R、RBW、FREQRANGE、Fs、
  bandpower 的 F／FREQRANGE）的類別檢查是 {'numeric'}：整數類別一律收、回 double、數值和 double 的呼叫相同（實測 i_obw_P_int8、
  i_bp_f_int16 等 9 筆）；**half 只有 P、RBW、Fs 收**（h_obw_P_half、h_obw_fs_half、ref_obw_r6 的 a1–a11：回 double、數值同 double 的呼叫；
  不合格的 half 值照常丟 notLess／expectedPositive／notGreaterEqual），half 的 FREQRANGE（PSD／功率譜／時域形式都是，單一數值也是）、
  powerbw 的 R、bandpower 的 F／FREQRANGE 丟 half:error:FunctionNotDefinedForHalf「Function is not defined for half inputs.」——因為
  validateattributes 的 'increasing' 與 'nonzero' 屬性沒有 half 版（ref_obw_r6 的 va_half_* 直接量 validateattributes：finite／real／size／
  vector／scalar／positive／nonempty／nonnegative／<／>=／numel／2d 都過，increasing／nonzero 丟這個錯），所以排在它們前面的屬性照常先丟
  （half([500 Inf]) → expectedFinite、half([3 4]) 的 R → expectedScalar、half([]) 的 R → expectedNonempty、1×3 的 bandpower FREQRANGE →
  incorrectNumel、含 Inf／矩陣的 bandpower F → expectedFinite／expectedVector），排在後面的（size、超出範圍、遞減、P／R 的值）不會再到
  （ref_obw_r6 h1–h14／o1–o20 共 34 筆，selftest 7f 逐筆釘住）。Pxx／Sxx／F／X 的類別檢查仍先於一切（o7：int16 的 Pxx 配 half 範圍丟 Pxx 的
  invalidType）。DSV 自己的輔助函式（cumulative_power、to_dbm、frequency_error、scope 路徑的 trace）用同一條規則（識別碼 dsv:chmeas:invalidType）。
- 空的 FREQRANGE（MATLAB isempty）：數值／logical／char 的空陣列（[]、int16([])、logical([])、half([])、zeros(0,2,'int16')、''）＝沒給範圍；
  空的 cell／datetime／duration 在 MATLAB 轉成 double 時失敗——MATLAB:invalidConversion「Conversion to double from cell is not
  possible.」、MATLAB:datetime:InvalidNumericConversion、MATLAB:duration:InvalidNumericConversion（PSD／功率譜／時域形式、obw 與 powerbw 都是；
  ref_obw_r6 r1–r12 實測）。bandpower 的空 FREQRANGE 不一樣：{} 丟 invalidType（不印 Instead）、[] 丟 expectedVector。
- None 的規則（Python 的 None 沒有 MATLAB 對應，一律當「沒給」；selftest 7d）：有預設值的引數（percent、rolloff_db、freqrange、rbw、fs、
  center、time_len、df、kind、mode、start／stop／span、periodogram_psd 的 func）None＝預設值，和不給位元級相同；必要的陣列引數
  （Pxx／Sxx／F／X、trace／頻率格、flo／fhi、to_dbm 的功率）None 丟 dsv:chmeas:MissingInput「Expected input number 1, Pxx, to be an
  array, but it is None (not given).」（照 MATLAB 的順序先 Pxx 再 F），不再冒稱 MATLAB 的 cell。MATLAB 的 [] 是另一回事：P＝[] 丟
  expectedNonempty（ref_obw_r3 obw_P_empty）、FREQRANGE 與 fs 的 [] 是「沒給」（obw_range_char_empty／obw_fs_*_empty 實測），Python 要那種
  行為就寫 []。
- 工具箱函式回傳的功率是線性值（pxx × Hz 的單位，W 或 V²）；scope 路徑另外給 power_dbm（ReferenceLoad 1）。
- obw()／powerbw() 多餘的位置引數對應 MATLAB 的 UnrecognizedAdditionalArguments（用 *extra 接住），關鍵字打錯則是一般的 TypeError。
- scope 路徑的工具列輸入錯誤用 DSV 自己組的識別碼 shared_dspwebscopes:spectrumanalyzer:invalid<欄位>（percent、span、center、start、
  stop 五個欄位，見 _UI_IDS；前綴照擷取到的警告識別碼 shared_dspwebscopes:spectrumanalyzer:nonRelevantProperty 的格式）。
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

DEFAULT_PERCENT = 99.0                         # PercentOccupiedBW 預設
PERCENT_MIN, PERCENT_MAX = 0.01, 99.99         # 工具列 spinner 的範圍（obw 本身只要 0 < P < 100）
PERCENT_STEP = 0.5                             # 工具列 spinner 每格 0.5（大步 1）
DEFAULT_SPAN = 2000.0                          # Span (Hz)
DEFAULT_CENTER = 0.0                           # Center Frequency (Hz)
DEFAULT_START, DEFAULT_STOP = -1000.0, 1000.0  # Start／Stop Frequency (Hz)
DEFAULT_ROLLOFF_DB = 10.0 * math.log10(0.5)    # powerbw 預設 R（約 −3.01 dB）
MAX_ELEMENTS = 1 << 24                         # DSV 防護：一次處理的元素上限（頻譜 N×通道、時域樣本數）

UI_MESSAGES = {   # 工具列輸入錯誤（英文照 MATLAB Spectrum Analyzer 介面顯示的訊息；繁體中文照簡中翻）
    "percent": ("Enter percent occupied bandwidth as a finite real scalar between 0 and 100 exclusive.",
                "請輸入 0 到 100（不含兩端）之間的有限實數作為佔用頻寬百分比。"),
    "span": ("Enter span as a finite positive real scalar.", "請輸入有限的正實數作為跨度。"),
    "center": ("Enter center frequency as a finite real scalar.", "請輸入有限的實數作為中心頻率。"),
    "start": ("Enter start frequency as a finite real scalar.", "請輸入有限的實數作為開始頻率。"),
    "stop": ("Enter stop frequency as a finite real scalar.", "請輸入有限的實數作為停止頻率。"),
}
_UI_IDS = {   # 欄位 → 識別碼（DSV 自己組的；前綴照擷取到的 shared_dspwebscopes:spectrumanalyzer:nonRelevantProperty）
    "percent": "shared_dspwebscopes:spectrumanalyzer:invalidPercentOccupiedBW",
    "span": "shared_dspwebscopes:spectrumanalyzer:invalidSpan",
    "center": "shared_dspwebscopes:spectrumanalyzer:invalidCenterFrequency",
    "start": "shared_dspwebscopes:spectrumanalyzer:invalidStartFrequency",
    "stop": "shared_dspwebscopes:spectrumanalyzer:invalidStopFrequency",
}


class ChannelMeasureError(ValueError):
    """MATLAB 會丟的驗證錯誤：identifier＝MATLAB 的錯誤識別碼（DSV 自己的防護是 dsv:chmeas:*）、str()＝英文訊息、zh＝繁體中文。"""

    def __init__(self, identifier: str, message: str, zh: str):
        super().__init__(message)
        self.identifier = identifier
        self.message = message
        self.zh = zh


# validateattributes 的句型「Expected {what} to be {屬性}.」：{what}＝"P" 或 "input number 3, FREQRANGE,"（有編號時名字後面帶逗號）；
# {zh}＝對應的中文稱呼。鍵＝識別碼的尾巴（MATLAB:<函式>:expected<鍵>）
_VA = {
    "Positive": ("Expected {what} to be positive.", "{zh}必須是正數。"),
    "Nonnegative": ("Expected {what} to be nonnegative.", "{zh}必須是非負數。"),
    "Finite": ("Expected {what} to be finite.", "{zh}必須是有限值。"),
    "Real": ("Expected {what} to be real.", "{zh}必須是實數。"),
    "NonZero": ("Expected {what} to be nonzero.", "{zh}不可為 0。"),       # 識別碼是 expectedNonZero（大寫 Z，ref_obw_r3 powerbw_R_zero 實測）
    "Nonempty": ("Expected {what} to be nonempty.", "{zh}不可為空。"),
    "Scalar": ("Expected {what} to be a scalar.", "{zh}必須是純量。"),
    "Vector": ("Expected {what} to be a vector.", "{zh}必須是向量。"),
    "2D": ("Expected {what} to be two-dimensional.", "{zh}必須是二維的。"),
    "Increasing": ("Expected {what} to be strictly increasing.", "{zh}必須嚴格遞增。"),
}
_FIXED = {   # MATLAB 的錯誤訊息原文（obw、powerbw、bandpower）；periodogram 的那一個是 validateattributes 句型
    "signal:psdparserange:FreqRangeOutOfBounds": ("The frequency range must be within the range of F for the specified input.",
                                                 "頻率範圍必須落在 F 的範圍之內。"),
    "signal:bandpower:FreqRangeOutOfBounds": ("The frequency range must be within the range of F for the specified input.",
                                             "頻率範圍必須落在 F 的範圍之內。"),
    "signal:psdparserange:FreqVectorMismatch": ("F must be a vector of the same length as the spectrum estimate.",
                                               "F 必須是和頻譜估計同長度的向量。"),
    "signal:obw:UnrecognizedAdditionalArguments": ("Unrecognized input arguments after power percentage, P.",
                                                  "功率百分比 P 之後有無法辨識的輸入引數。"),
    "signal:powerbw:UnrecognizedAdditionalArguments": ("Unrecognized input arguments after dB reference, R.",
                                                      "dB 參考值 R 之後有無法辨識的輸入引數。"),
    "MATLAB:periodogram:expectedNonempty": ("Expected X to be nonempty.", "X 不可為空（沒有樣本就沒有頻譜）。"),
    "signal:computeperiodogram:NDMatrixUnsupported": ("The input must be a non-empty column vector or two-dimensional matrix.",
                                                      "輸入必須是非空的行向量或二維矩陣（只有 1 個樣本無法做 periodogram）。"),
    "signal:bandpower:IncorrectStringPsd": ("Unrecognized input option. 'psd' is the only supported input option.",
                                            "無法辨識的輸入選項，只支援 'psd'。"),
    "signal:bandpower:FreqVectorMissing": ("You must specify a frequency vector, F, when using the 'psd' option.",
                                           "使用 'psd' 選項時必須給頻率向量 F。"),
    "MATLAB:validateattributes:badComparison": ("Value for >= must be a real scalar.", "「>=」比較的值必須是實數純量（平均 bin 間距是 NaN）。"),
    # validateattributes 的 'increasing' 與 'nonzero' 屬性沒有 half 版（ref_obw_r6 的 va_half_* 實測：finite／real／size／vector／scalar／
    # positive／nonempty／nonnegative／<／>=／numel／2d 都有），所以 half 的 FREQRANGE、powerbw 的 R、bandpower 的 F／FREQRANGE 在走到那個
    # 屬性時丟這個錯（前面的屬性照常先檢查）；half 的 P、RBW、Fs 用不到那兩個屬性，照 double 算
    "half:error:FunctionNotDefinedForHalf": ("Function is not defined for half inputs.",
                                             "此函式不支援 half（半精度）輸入：validateattributes 的 increasing／nonzero 屬性沒有 half 版。"),
    # 空的 FREQRANGE 不是數值／logical／char 時，MATLAB 先把它轉成 double、在那裡失敗（ref_obw_r6 的 r1–r6 實測）
    "MATLAB:invalidConversion": ("Conversion to double from cell is not possible.", "空的 cell 無法轉成 double（空的 FREQRANGE 會先被 double()）。"),
    "MATLAB:datetime:InvalidNumericConversion": ("Undefined function 'double' for input arguments of type 'datetime'. To convert from "
                                                 "datetimes to numeric, first subtract off a datetime origin, then convert to numeric using "
                                                 "the SECONDS, MINUTES, HOURS, DAYS, or YEARS functions.",
                                                 "datetime 無法直接轉成 double（空的 FREQRANGE 會先被 double()）。"),
    "MATLAB:duration:InvalidNumericConversion": ("Undefined function 'double' for input arguments of type 'duration'. To convert from "
                                                 "durations to numeric, use the SECONDS, MINUTES, HOURS, DAYS, or YEARS functions.",
                                                 "duration 無法直接轉成 double（空的 FREQRANGE 會先被 double()）。"),
}
_DSV = {   # DSV 自己的防護與 API 檢查（沒有 MATLAB 對應）
    "TooLarge": ("Input has {n} elements, more than the DSV limit of {max} (2^24).", "輸入有 {n} 個元素，超過 DSV 的上限 {max}（2²⁴）。"),
    "InvalidKind": ("kind must be 'psd' or 'power', got {kind!r}.", "kind 只能是 'psd' 或 'power'，收到 {kind!r}。"),
    "RBWRequired": ("rbw (the ENBW in Hz) is required when kind='power'.", "kind='power' 時必須給 rbw（ENBW，Hz）。"),
    "GridTooShort": ("The displayed spectrum needs at least two bins (or an explicit df).", "顯示頻譜至少要兩個 bin（或明確給 df）。"),
    "NonuniformGrid": ("The displayed frequency grid must be uniformly spaced and increasing.", "顯示的頻率格必須等距且遞增。"),
    "StartStopOrder": ("Stop frequency must be greater than start frequency.", "停止頻率必須大於開始頻率。"),
    "InvalidMode": ("mode must be 'span' or 'startstop', got {mode!r}.", "mode 只能是 'span' 或 'startstop'，收到 {mode!r}。"),
    "MissingKey": ("The spectrum result dict has no {name!r} entry (expected the dict returned by dsv_spectrum.welch).",
                   "頻譜結果 dict 缺少 {name!r}（應該是 dsv_spectrum.welch 回傳的 dict）。"),
    "InvalidTimeLen": ("time_len must be None or a nonnegative integer scalar (the original signal length), got {val!r}.",
                       "time_len 只能是 None 或非負整數純量（原時域訊號的長度），收到 {val!r}。"),
    "ShapeMismatch": ("flo and fhi must have the same shape, got {a} and {b}.", "flo 與 fhi 的形狀必須相同，收到 {a} 與 {b}。"),
    "FreqVectorMismatch": ("F must be a vector of the same length as the spectrum estimate.", "F 必須是和頻譜估計同長度的向量。"),
    "MissingInput": ("Expected {what} to be an array, but it is None (not given).", "{zh}沒有給（None）；空陣列請用 []。"),
    # 下面四個是 Python 呼叫形式與 MATLAB 引數形狀分派的差異（MATLAB 用同樣的引數會改走另一種形式，見模組說明「分派」）
    "FTooShort": ("F must contain at least two frequencies (MATLAB would read an empty or scalar second argument as the sample "
                  "rate Fs and use the time-domain form; call {func}_time for that).",
                  "F 至少要有兩個頻率（MATLAB 會把空的或單一數值的第 2 個引數當成取樣率 Fs、改走時域形式；那種用法請呼叫 {func}_time）。"),
    "RBWNotScalar": ("rbw must be a scalar (MATLAB would read a non-scalar third argument as FREQRANGE and use the PSD form).",
                     "rbw 必須是單一數值（MATLAB 會把非單一數值的第 3 個引數當成 FREQRANGE、改走 PSD 形式）。"),
    "FreqRangeScalar": ("freqrange must have two elements (MATLAB would read a scalar third argument as RBW and use the "
                        "power-spectrum form).",
                        "freqrange 必須有兩個元素（MATLAB 會把單一數值的第 3 個引數當成 RBW、改走功率譜形式）。"),
    "FsNotScalar": ("fs must be empty or a scalar (MATLAB would read a non-scalar second argument as the frequency vector F "
                    "and use the PSD form; call {func}() for that).",
                    "fs 只能是空的或單一數值（MATLAB 會把非單一數值的第 2 個引數當成頻率向量 F、改走 PSD 形式；那種用法請呼叫 {func}()）。"),
    "InvalidFunc": ("func must be 'obw' or 'powerbw' (the MATLAB function whose name goes into the error identifiers), got {func!r}.",
                    "func 只能是 'obw' 或 'powerbw'（放進錯誤識別碼的 MATLAB 函式名），收到 {func!r}。"),
}


def _what(n: int, name: str) -> str:
    """validateattributes 有給引數編號時的稱呼："input number 3, RBW,"。"""
    return f"input number {n}, {name},"


def _va_error(func: str, attr: str, what: str, zh: str, prefix: str = "MATLAB") -> ChannelMeasureError:
    en, tw = _VA[attr]
    return ChannelMeasureError(f"{prefix}:{func}:expected{attr}", en.format(what=what), tw.format(zh=zh))


def _cmp_error(func: str, kind: str, what: str, zh: str, op: str, val: float) -> ChannelMeasureError:
    """validateattributes 的 '<'／'>=' 句型（kind＝notLess／notGreaterEqual）。數字是 C 的 %g（6 位有效數字、Inf 印小寫 inf）：
    ref_obw_r3 的 obw_rbw_fmt_* 實測 0.333333／33333.3／3.33333e-08／3.33333e+19／1.23457e+08／0.1／0.000666667／inf，和 Python 的 'g' 相同。"""
    v = format(val, "g")
    return ChannelMeasureError(f"MATLAB:{func}:{kind}", f"Expected {what} to be a scalar with value {op} {v}.", f"{zh}必須是{op} {v} 的純量。")


def _size_error(func: str, what: str, zh: str, want: str, actual: str) -> ChannelMeasureError:
    """validateattributes 的 'size' 句型（訊息原文照 MATLAB）。"""
    return ChannelMeasureError(f"MATLAB:{func}:incorrectSize", f"Expected {what} to be of size {want}, but it is of size {actual}.",
                               f"{zh}的大小必須是 {want}，實際是 {actual}。")


def _numel_error(func: str, what: str, zh: str, n: int) -> ChannelMeasureError:
    """validateattributes 的 'numel' 句型（expectedArrayEqual＋「number of elements」）。"""
    return ChannelMeasureError(f"MATLAB:{func}:incorrectNumel", f"Expected {what} to be an array with number of elements equal to {n}.",
                               f"{zh}的元素個數必須是 {n}。")


def _fixed_error(identifier: str) -> ChannelMeasureError:
    en, tw = _FIXED[identifier]
    return ChannelMeasureError(identifier, en, tw)


def _dsv_error(key: str, **kw) -> ChannelMeasureError:
    en, tw = _DSV[key]
    return ChannelMeasureError(f"dsv:chmeas:{key}", en.format(**kw), tw.format(**kw))


def _ui_error(key: str) -> ChannelMeasureError:
    en, tw = UI_MESSAGES[key]
    return ChannelMeasureError(_UI_IDS[key], en, tw)


def _shape_str(a: np.ndarray) -> str:
    """MATLAB 式的大小字串：Python 的 1-D 序列視為 1×n 的列向量。"""
    return f"1x{a.size}" if a.ndim <= 1 else "x".join(str(s) for s in a.shape)


_MATLAB_CLASS = {"U": "char", "S": "char", "b": "logical", "O": "cell", "M": "datetime", "m": "duration"}
# numpy 浮點／複數 dtype 在 MATLAB 的類別名（整數 dtype 的名字 int8…uint64 和 MATLAB 相同，直接用 dtype.name）
_FLOAT_CLASS = {"float16": "half", "float32": "single", "float64": "double", "complex64": "single", "complex128": "double"}
# validateattributes 把 {'numeric'} 展開成這串（ref_obw_r3 的 obw_P_char／obw_P_cell 等實測）
_NUMERIC_CLASSES = "double, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64"
_FLOAT_CLASSES = "double, single"


def _matlab_class(value, a: np.ndarray) -> str:
    """輸入在 MATLAB 對應的類別名稱：str／bytes → char、bool → logical、dict → struct、函式 → function_handle、
    datetime64 → datetime、timedelta64 → duration、float16 → half、float32／complex64 → single、float64／complex128 → double、
    整數 dtype → 同名（int16、uint8…）、其餘（參差不齊的序列、物件）→ cell。"""
    if isinstance(value, dict):
        return "struct"
    if callable(value) and not isinstance(value, np.ndarray):
        return "function_handle"
    return _MATLAB_CLASS.get(a.dtype.kind, _FLOAT_CLASS.get(a.dtype.name, a.dtype.name))


def _is_char(value) -> bool:
    """Python 的 str／bytes（含 numpy 的字串陣列）＝MATLAB 的 char。"""
    return isinstance(value, (str, bytes, np.str_, np.bytes_)) or (isinstance(value, np.ndarray) and value.dtype.kind in "US")


def _matlab_numel(a: np.ndarray) -> int:
    """MATLAB 的 numel：0-d 的字串是 char 列向量，元素數＝字元數（'' 是 0、'a' 是 1）；其餘＝陣列的元素數。"""
    if a.dtype.kind in "US" and a.ndim == 0:
        return len(a.item())
    return int(a.size)


def _matlab_isempty(value) -> bool:
    """MATLAB 的 isempty：None 不算（呼叫端各自當「沒給」處理）；'' 是空的（np.asarray('') 卻有 1 個元素）。"""
    return _matlab_numel(_to_array(value)) == 0


def _to_array(value) -> np.ndarray:
    """np.asarray，但參差不齊的巢狀序列（numpy 2 丟 ValueError「inhomogeneous shape」）改成 dtype=object 的陣列——MATLAB 會把這種東西
    當 cell，validateattributes 丟 invalidType（cell）；這樣 numpy 的 ValueError 不會漏出去。"""
    try:
        return np.asarray(value)
    except (ValueError, TypeError):
        try:
            return np.array(value, dtype=object)
        except (ValueError, TypeError):
            return np.array(None, dtype=object)


def _as_numeric(func: str, value, what: str, zh: str, classes: str = "numeric", prefix: str = "MATLAB") -> np.ndarray:
    """validateattributes 的類別檢查（在屬性之前）：不是數值（字串、bool、物件、參差不齊的序列……）→ invalidType 句型。回傳 _to_array(value)。
    classes＝"numeric"（P、R、RBW、FREQRANGE、Fs、bandpower 的 F：任何數值類別都收，整數／half 照 double 算，ref_obw_r4 的 i_*／h_* 純量實測）
    或 _FLOAT_CLASSES「double, single」（Pxx／Sxx／F／X）：這時 numpy 的整數 ndarray／整數純量與 float16 也丟 invalidType，類別名照 dtype
    （int16、uint8、…、half；ref_obw_r4 與 ref_obw_r5 共 52 筆實測）。Python 的 int／list／tuple 不算整數類別：MATLAB 的數字字面值
    [1;2;5;2;1] 是 double（ref_obw_r5 class_of_literal／m_obw_literal 實測），Python 寫 [1, 2, 5, 2, 1] 對應的就是它，所以當 double
    （只看最外層：list 裡裝 numpy 整數純量也當字面值）。None＝沒給 → dsv:chmeas:MissingInput（Python 的 None 沒有 MATLAB 對應，
    不再冒稱 cell；有預設值的引數由呼叫端先把 None 換成預設值，不會到這裡）。
    句型照 R2025a 實測（ref_obw_r3／ref_obw_r6）：{'numeric'} 印成 _NUMERIC_CLASSES 那一串；最後的「Instead its type was <類別>.」有兩種
    情況不印——char（'' 與 'abc' 都是：obw_P_char／obw_F_char／obw_X_char／e14）和**空的 cell**（{}、cell(0,2)、cell(1,0)：ref_obw_r6 的
    v1–v3、e1／e3–e5／e15–e20／e22；Python 這邊是空的 dtype=object 陣列）；非空的 cell（{1}、{1,2}、參差不齊的序列）和空的 int16／logical／
    half／struct／datetime／string／duration 都印（v4–v11、v15、e2／e6–e13）。"""
    if value is None:
        raise _dsv_error("MissingInput", what=what, zh=zh)
    a = _to_array(value)
    kind = a.dtype.kind
    bad = kind not in "iufc"
    if not bad and classes == _FLOAT_CLASSES:
        bad = (kind in "iu" or a.dtype == np.float16) and isinstance(value, (np.ndarray, np.generic))
    if bad:
        cls = _matlab_class(value, a)
        listed = _NUMERIC_CLASSES if classes == "numeric" else classes
        en = f"Expected {what} to be one of these types:\n\n{listed}"
        if cls != "char" and not (cls == "cell" and a.size == 0):     # char 與空的 cell 不印這一行（實測）
            en += f"\n\nInstead its type was {cls}."
        raise ChannelMeasureError(f"{prefix}:{func}:invalidType", en, f"{zh}必須是下列類別之一：{listed}；實際是 {cls}。")
    return a


def _is_half(value, a: np.ndarray) -> bool:
    """MATLAB 的 half＝numpy 的 float16 ndarray／純量（和 Pxx 的類別規則一樣只看最外層型別：list 裡裝 float16 純量是字面值、當 double）。"""
    return a.dtype == np.float16 and isinstance(value, (np.ndarray, np.generic))


def _half_error() -> ChannelMeasureError:
    """validateattributes 走到 'increasing'／'nonzero' 屬性時 half 丟的錯（ref_obw_r6 實測；前面的屬性先照常檢查、後面的不會再到）。"""
    return _fixed_error("half:error:FunctionNotDefinedForHalf")


def _empty_range_conversion(value) -> None:
    """空的 FREQRANGE（MATLAB isempty）在 MATLAB 會先被轉成 double：數值／logical／char 的空陣列沒事（＝沒給範圍），
    空的 cell／datetime／duration 在 double() 失敗（ref_obw_r6 的 r1–r12 實測：MATLAB:invalidConversion、
    MATLAB:datetime:InvalidNumericConversion、MATLAB:duration:InvalidNumericConversion）。"""
    k = _to_array(value).dtype.kind
    if k == "O":
        raise _fixed_error("MATLAB:invalidConversion")
    if k == "M":
        raise _fixed_error("MATLAB:datetime:InvalidNumericConversion")
    if k == "m":
        raise _fixed_error("MATLAB:duration:InvalidNumericConversion")


def _check_size(n: int) -> None:
    if n > MAX_ELEMENTS:
        raise _dsv_error("TooLarge", n=n, max=MAX_ELEMENTS)


# ---------------------------------------------------------------- 頻率格與累積功率（obw 的規則） ------------------------------------------
def _grid_array(f, allow_empty: bool) -> np.ndarray:
    """公開輔助函式（bin_widths／cumulative_power）的頻率格：要是實數數值的向量，否則丟 dsv:chmeas:invalidType／expectedReal／
    expectedVector（不讓 numpy 的 ValueError／UFuncTypeError／IndexError 漏出去）；回傳 1-D 的 float 陣列（已是 float64 時不複製）。"""
    what, zh = "the frequency grid", "頻率格"
    fa = _as_numeric("chmeas", f, what, zh, prefix="dsv")
    if np.iscomplexobj(fa):
        raise _va_error("chmeas", "Real", what, zh, prefix="dsv")
    if (fa.size == 0 and not allow_empty) or fa.ndim > 2 or (fa.ndim == 2 and min(fa.shape) != 1):
        raise _va_error("chmeas", "Vector", what, zh, prefix="dsv")
    return np.asarray(fa, dtype=float).ravel()


def bin_widths(f) -> np.ndarray:
    """每個 bin 的寬度（MATLAB 的每格寬度規則）：相鄰頻率差，少掉的那一格＝(f_end − f_0)/(N−1)，f_0＝0 時補在最後、否則補在最前。
    只有一個頻率時 0/0＝NaN（MATLAB 同樣算出 NaN）、空的格回空陣列。f 不是實數數值的向量（字串、複數、矩陣、參差不齊的序列）丟 dsv:chmeas:*。
    1e308 級的頻率相減會溢位成 ±Inf，照 IEEE 往下算、不印 numpy 警告。"""
    f = _grid_array(f, allow_empty=True)
    n = f.size
    if n < 2:
        return np.full(n, np.nan)
    with np.errstate(over="ignore", invalid="ignore"):
        d = np.diff(f)
        miss = (f[-1] - f[0]) / (n - 1)
    return np.concatenate([d, [miss]]) if f[0] == 0 else np.concatenate([[miss], d])


def cumulative_power(pxx, f) -> Tuple[np.ndarray, np.ndarray]:
    """(C, B)：C＝[0, 逐 bin 功率的累積]（N+1 × 通道數）、B＝[f_0, 相鄰頻率中點…, f_end]（N+1）。pxx 是 (N, 通道數)；1-D 或 (1 × N)
    的 pxx 當一個通道（C 是 N+1 × 1）。極大的 PSD（1e308 級）乘寬度會溢位成 Inf，和 MATLAB 一樣靜靜地往下算（結果 NaN），不印 numpy 警告。
    pxx 不是實數數值／超過二維丟 dsv:chmeas:*，長度和 f 不符丟 dsv:chmeas:FreqVectorMismatch（DSV 自己的輔助函式，訊息借 signal:psdparserange:FreqVectorMismatch 的）。"""
    what, zh = "the spectrum", "頻譜"
    p = _as_numeric("chmeas", pxx, what, zh, _FLOAT_CLASSES, prefix="dsv")
    if p.ndim > 2:
        raise _va_error("chmeas", "2D", what, zh, prefix="dsv")
    if np.iscomplexobj(p):
        raise _va_error("chmeas", "Real", what, zh, prefix="dsv")
    p = np.asarray(p, dtype=float)
    p = p.reshape(-1, 1) if p.ndim <= 1 or p.shape[0] == 1 else p
    f = _grid_array(f, allow_empty=False)
    if f.size != p.shape[0]:
        raise _dsv_error("FreqVectorMismatch")
    with np.errstate(over="ignore", invalid="ignore"):
        p = p * bin_widths(f)[:, None]
        c = np.vstack([np.zeros((1, p.shape[1])), np.cumsum(p, axis=0)])
        b = np.concatenate([[f[0]], (f[:-1] + f[1:]) / 2, [f[-1]]])  # 1e308 級的頻率相加會溢位成 Inf，不印警告
    return c, b


def _power_at(c: np.ndarray, b: np.ndarray, x) -> np.ndarray:
    """累積功率在頻率 x 的線性內插（每通道一個值；x 是一個數，或每通道各一個的陣列）：取第一個 B_i ≥ x 的 i，在 i 與 i−1 之間
    內插（i＝0 時用 0、1）；找不到（含 x＝NaN）→ NaN。"""
    nch = c.shape[1]
    xs = np.broadcast_to(np.asarray(x, dtype=float), (nch,))
    with np.errstate(invalid="ignore"):
        m = xs[None, :] <= b[:, None]
    found = m.any(axis=0)
    i = np.argmax(m, axis=0)
    first = i == 0
    j0 = np.where(first, 0, i)
    j1 = np.where(first, 1, i - 1)
    cols = np.arange(nch)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        y0, y1 = c[j0, cols], c[j1, cols]
        out = y0 + (y1 - y0) * (xs - b[j0]) / (b[j1] - b[j0])
    return np.where(found, out, np.nan)


def _freq_at(c: np.ndarray, b: np.ndarray, thresh: np.ndarray) -> np.ndarray:
    """反向內插：每個通道各自取第一個 C_i ≥ 門檻的 i（i＝0 時改成 1），在 (C_{i−1}, B_{i−1})–(C_i, B_i) 之間線性內插；找不到 → NaN。"""
    with np.errstate(invalid="ignore"):
        m = thresh[None, :] <= c
    found = m.any(axis=0)
    i = np.maximum(np.argmax(m, axis=0), 1)
    cols = np.arange(c.shape[1])
    x0, x1 = c[i - 1, cols], c[i, cols]
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        out = b[i - 1] + (b[i] - b[i - 1]) * (thresh - x0) / (x1 - x0)
    out[~found] = np.nan
    return out


# ---------------------------------------------------------------- 輸入驗證（照 MATLAB obw 參數檢查的順序與訊息） -----------------------
def _parse_spectrum(func: str, pxx, f, rbw: Optional[float]) -> Tuple[np.ndarray, np.ndarray, bool]:
    """回傳 (PSD (N × 通道數), f (N), 結果是否該壓成單一數值)。rbw 不是 None 時 pxx 是功率譜，換成 PSD＝pxx/rbw。
    順序照 MATLAB 的參數解析：頻譜（類別 → 2d → real → nonnegative；列向量轉成一個通道）→ F（類別 → real → vector → finite →
    長度相符）→ RBW（類別 → real → finite → positive → scalar → ≥ 平均 bin 間距）。F 的元素數 ≤ 1、rbw 非單一數值這兩種
    MATLAB 會改走別的形式，由呼叫端先用 _check_dispatch 擋掉。
    nonnegative／positive 照 validateattributes 的語意：只看「有沒有 < 0（≤ 0）的值」，NaN 不算違反——MATLAB 的
    obw([1;NaN;5;2;1], f) 不丟錯、算出全 NaN（ref_obw_r3 obw_pxx_nan）。"""
    name = "Pxx" if rbw is None else "Sxx"
    what1, zh1 = _what(1, name), f"第 1 個輸入 {name}"
    p = _as_numeric(func, pxx, what1, zh1, _FLOAT_CLASSES)
    if p.ndim > 2:
        raise _va_error(func, "2D", what1, zh1)
    if np.iscomplexobj(p):
        raise _va_error(func, "Real", what1, zh1)
    p = np.asarray(p, dtype=float)
    _check_size(p.size)
    one_d = p.ndim <= 1 or p.shape[0] == 1                             # 1-D 或 (1 × N) 列向量 → 一個通道、回傳單一數值
    p = p.reshape(-1, 1) if one_d else p
    if np.any(p < 0):                                                  # NaN 通過（validateattributes 只找 < 0 的值）
        raise _va_error(func, "Nonnegative", what1, zh1)
    what2, zh2 = _what(2, "F"), "第 2 個輸入 F"
    fa = _as_numeric(func, f, what2, zh2, _FLOAT_CLASSES)              # PSD 與功率譜形式的 F 都只收 double／single
    if np.iscomplexobj(fa):
        raise _va_error(func, "Real", what2, zh2)
    if fa.size == 0 or fa.ndim > 2 or (fa.ndim == 2 and min(fa.shape) != 1):
        raise _va_error(func, "Vector", what2, zh2)
    fv = np.asarray(fa, dtype=float).ravel()
    if not np.all(np.isfinite(fv)):
        raise _va_error(func, "Finite", what2, zh2)
    if fv.size != p.shape[0]:
        raise _fixed_error("signal:psdparserange:FreqVectorMismatch")
    if rbw is not None:
        what3, zh3 = _what(3, "RBW"), "第 3 個輸入 RBW"
        ra = _as_numeric(func, rbw, what3, zh3)
        if np.iscomplexobj(ra):
            raise _va_error(func, "Real", what3, zh3)
        ra = np.asarray(ra, dtype=float)
        if not np.all(np.isfinite(ra)):
            raise _va_error(func, "Finite", what3, zh3)
        if not np.all(ra > 0):
            raise _va_error(func, "Positive", what3, zh3)
        if ra.size != 1:
            raise _va_error(func, "Scalar", what3, zh3)
        r = float(ra.reshape(()))
        with np.errstate(over="ignore", invalid="ignore"):
            df = float(np.mean(np.diff(fv)))                           # RBW 至少要一個 bin 寬（1e308 級的格相減溢位 → Inf，不印警告）
        if math.isnan(df):                                             # 例如 F＝[1e308 −1e308 1e308]：diff 是 [−Inf Inf]、平均 NaN
            raise _fixed_error("MATLAB:validateattributes:badComparison")   # ref_obw_r3 obw_rbw_nan_df 實測
        if r < df:
            raise _cmp_error(func, "notGreaterEqual", what3, zh3, ">=", df)
        p = p / r
    return p, fv, one_d


def _parse_range(func: str, freqrange, f: np.ndarray, identifier: str = "signal:psdparserange:FreqRangeOutOfBounds",
                 what: Optional[str] = None, zh: Optional[str] = None) -> Tuple[float, float]:
    """FREQRANGE：None／空（含 ''，MATLAB 的 isempty：obw(Pxx, F, '', 99) 和不給範圍相同，ref_obw_r3 obw_range_char_empty）＝整個頻率格；
    否則照 MATLAB 參數解析的順序檢查：類別 → real → finite → strictly increasing → 大小 1×2 → 落在 [f_0, f_end] 內。
    what／zh＝訊息裡的稱呼（時域形式不帶引數編號）。PSD 形式的單一數值範圍由 _check_dispatch 先擋。
    空的 cell／datetime／duration 丟 double() 的轉換錯（_empty_range_conversion）；half 的範圍過了 real／finite 之後在 increasing 丟
    half:error:FunctionNotDefinedForHalf（ref_obw_r6 h1–h5／o1–o7：half([500 Inf]) 是 expectedFinite、half([30 10])／1×3／超出範圍／單一數值都是 half 錯）。"""
    if freqrange is None or _matlab_isempty(freqrange):
        if freqrange is not None:
            _empty_range_conversion(freqrange)
        return float(f[0]), float(f[-1])
    what = _what(3, "FREQRANGE") if what is None else what
    zh = "第 3 個輸入 FREQRANGE" if zh is None else zh
    r = _as_numeric(func, freqrange, what, zh)
    if np.iscomplexobj(r):
        raise _va_error(func, "Real", what, zh)
    rv = np.asarray(r, dtype=float).ravel()
    if not np.all(np.isfinite(rv)):
        raise _va_error(func, "Finite", what, zh)
    if _is_half(freqrange, r):                                         # validateattributes 'increasing' 沒有 half 版
        raise _half_error()
    with np.errstate(over="ignore"):
        increasing = bool(np.all(np.diff(rv) > 0))
    if not increasing:
        raise _va_error(func, "Increasing", what, zh)
    if rv.size != 2 or (r.ndim == 2 and r.shape != (1, 2)):
        raise _size_error(func, what, zh, "1x2", _shape_str(r))
    if rv[0] < f[0] or rv[1] > f[-1]:
        raise _fixed_error(identifier)
    return float(rv[0]), float(rv[1])


def _parse_percent(percent) -> float:
    """P（MATLAB 的 obw）：None＝沒給＝預設 99（和 powerbw 的 R＝None 一樣；MATLAB 的 [] 是另一回事：obw(Pxx, F, [], []) 丟
    expectedNonempty，Python 要寫 []，ref_obw_r3 obw_P_empty）；否則類別 → real → nonempty → positive → scalar → < 100。
    positive 只找 ≤ 0 的值，所以 NaN 通過、再被 < 100 擋下（MATLAB:obw:notLess；[NaN NaN] 是 expectedScalar；
    ref_obw_r3 obw_P_nan／obw_P_nan2 實測）。"""
    if percent is None:
        return DEFAULT_PERCENT
    a = _as_numeric("obw", percent, "P", "P")
    if np.iscomplexobj(a):
        raise _va_error("obw", "Real", "P", "P")
    a = np.asarray(a, dtype=float)
    if a.size == 0:
        raise _va_error("obw", "Nonempty", "P", "P")
    if np.any(a <= 0):
        raise _va_error("obw", "Positive", "P", "P")
    if a.size != 1:
        raise _va_error("obw", "Scalar", "P", "P")
    p = float(a.reshape(()))
    if not p < 100:
        raise _cmp_error("obw", "notLess", "P", "P", "<", 100)
    return p


def _parse_rolloff(rolloff_db) -> float:
    """R（MATLAB 的 powerbw）：None＝預設 10·log10(1/2)；否則類別 → real → nonempty → finite → scalar → nonzero，取 −|R|。
    half 的 R 過了前五個屬性之後在 nonzero 丟 half:error:FunctionNotDefinedForHalf（ref_obw_r6 h6–h8／o8–o12：half([3 4]) 是 expectedScalar、
    half(NaN)／half(Inf) 是 expectedFinite、half([]) 是 expectedNonempty、half(3)／half(0) 都是 half 錯）。"""
    if rolloff_db is None:
        return DEFAULT_ROLLOFF_DB
    a0 = _as_numeric("powerbw", rolloff_db, "R", "R")
    if np.iscomplexobj(a0):
        raise _va_error("powerbw", "Real", "R", "R")
    a = np.asarray(a0, dtype=float)
    if a.size == 0:
        raise _va_error("powerbw", "Nonempty", "R", "R")
    if not np.all(np.isfinite(a)):
        raise _va_error("powerbw", "Finite", "R", "R")
    if a.size != 1:
        raise _va_error("powerbw", "Scalar", "R", "R")
    if _is_half(rolloff_db, a0):                                       # validateattributes 'nonzero' 沒有 half 版
        raise _half_error()
    r = float(a.reshape(()))
    if r == 0:
        raise _va_error("powerbw", "NonZero", "R", "R")
    return -abs(r)


def _check_dispatch(func: str, f, rbw, freqrange) -> None:
    """PSD／功率譜形式的 Python 呼叫裡，MATLAB 用同樣的引數會改走別的形式的情況（MATLAB 靠引數形狀分派），
    在任何驗證之前丟 DSV 自己的錯誤（MATLAB 不會丟這些識別碼；它實際做什麼記在 ref_obw_r3 並由 selftest 驗證）：
    - F 是空的或只有一個元素 → MATLAB 把它當取樣率 Fs、走時域（obw(p5, []) 算出數值、obw(p5, 0) 丟 Fs expectedPositive）；
    - rbw 給了但不是單一數值 → MATLAB 把它當 FREQRANGE、走 PSD 形式（obw(p5, f5, [20 30], 99) 算出 [20 30] 的佔用頻寬）；
    - PSD 形式（rbw 沒給）的 freqrange 只有一個元素 → MATLAB 把它當 RBW、走功率譜形式（obw(p5, f5, 1000, 99) 丟 FREQRANGE 的 size 錯）。
    f＝None 不在這裡擋：交給 _parse_spectrum 照 MATLAB 的順序（先 Pxx 再 F）丟 dsv:chmeas:MissingInput。"""
    if f is not None and _matlab_numel(_to_array(f)) <= 1:
        raise _dsv_error("FTooShort", func=func)
    if rbw is not None and _matlab_numel(_to_array(rbw)) != 1:
        raise _dsv_error("RBWNotScalar")
    if rbw is None and freqrange is not None and _matlab_numel(_to_array(freqrange)) == 1:
        raise _dsv_error("FreqRangeScalar")


def _squeeze(one_d: bool, *arrs):
    return tuple(float(a[0]) if one_d else a for a in arrs)


# ---------------------------------------------------------------- 工具箱函式：obw／channel_power／channel_measure ---------------------------
def _obw_core(p: np.ndarray, f: np.ndarray, a: float, b: float, pct: float) -> Tuple[np.ndarray, ...]:
    """(bw, flo, fhi, pwr, tot)，每個都是「每通道一個值」。"""
    c, bd = cumulative_power(p, f)
    at_start = _power_at(c, bd, a)
    at_stop = _power_at(c, bd, b)
    with np.errstate(invalid="ignore", over="ignore"):
        tot = at_stop - at_start
        flo = _freq_at(c, bd, at_start + (100.0 - pct) / 200.0 * tot)
        fhi = _freq_at(c, bd, at_start + (100.0 + pct) / 200.0 * tot)
        return fhi - flo, flo, fhi, pct / 100.0 * tot, tot


def obw(pxx, f, percent: Optional[float] = DEFAULT_PERCENT, freqrange: Optional[Sequence[float]] = None, *extra, rbw: Optional[float] = None):
    """MATLAB obw：佔用頻寬。pxx＝PSD（rbw＝None）或每 bin 功率（rbw＝解析頻寬，MATLAB 的 obw(Sxx, F, RBW, …)），f＝頻率格（單邊、
    雙邊或置中都可）。回傳 (bw, flo, fhi, power)：power 是佔用頻帶內的功率（＝P/100 × 範圍內總功率）。1-D 輸入回傳 float、
    (N × 通道數) 回傳每通道一個值的陣列。MATLAB 會改走別的形式的引數形狀丟 dsv:chmeas:*（見 _check_dispatch）。"""
    _check_dispatch("obw", f, rbw, freqrange)
    p, fv, one_d = _parse_spectrum("obw", pxx, f, rbw)
    a, b = _parse_range("obw", freqrange, fv)
    if extra:
        raise _fixed_error("signal:obw:UnrecognizedAdditionalArguments")
    pct = _parse_percent(percent)
    bw, flo, fhi, pwr, _ = _obw_core(p, fv, a, b, pct)
    return _squeeze(one_d, bw, flo, fhi, pwr)


def obw_time(x, fs: Optional[float] = None, percent: Optional[float] = DEFAULT_PERCENT, freqrange: Optional[Sequence[float]] = None, *extra):
    """MATLAB obw(x, fs, FREQRANGE, P)（時域形式）：矩形窗、NFFT＝N 的 periodogram 再量。fs＝None 或空 → 2π
    （空陣列照類別 cast，見 periodogram_psd）。1 個樣本丟 signal:computeperiodogram:NDMatrixUnsupported（MATLAB 實測）。
    FREQRANGE 的訊息不帶引數編號（MATLAB 的訊息沒有編號；ref_obw_r3 obw_time_range_scalar 實測）。"""
    p, fv = periodogram_psd(x, fs)
    p2, fv, one_d = _parse_spectrum("obw", p, fv, None)
    a, b = _parse_range("obw", freqrange, fv, what="FREQRANGE", zh="FREQRANGE")
    if extra:
        raise _fixed_error("signal:obw:UnrecognizedAdditionalArguments")
    pct = _parse_percent(percent)
    bw, flo, fhi, pwr, _ = _obw_core(p2, fv, a, b, pct)
    return _squeeze(one_d, bw, flo, fhi, pwr)


def channel_power(pxx, f, f1: Optional[float] = None, f2: Optional[float] = None, rbw: Optional[float] = None):
    """量測範圍 [f1, f2]（None＝整個頻率格）內的總功率＝累積功率的線性內插 C(f2) − C(f1)（obw 的積分規則；邊緣的 bin 按比例計入）。
    線性單位（pxx × Hz）。"""
    _check_dispatch("obw", f, rbw, None)
    p, fv, one_d = _parse_spectrum("obw", pxx, f, rbw)
    rng = None if f1 is None and f2 is None else (fv[0] if f1 is None else f1, fv[-1] if f2 is None else f2)
    a, b = _parse_range("obw", rng, fv)
    c, bd = cumulative_power(p, fv)
    with np.errstate(invalid="ignore", over="ignore"):
        tot = _power_at(c, bd, b) - _power_at(c, bd, a)
    return _squeeze(one_d, tot)[0]


def _parse_center(center) -> float:
    """channel_measure／frequency_error 的 Center Frequency：有限實數純量，否則丟工具列的 center 訊息（和 scope 路徑同一個檢查；
    MATLAB 的 obw 沒有這個引數，見模組說明「未定」）。"""
    cf = _finite_real_scalar(center)
    if cf is None:
        raise _ui_error("center")
    return cf


def frequency_error(flo, fhi, center: float = 0.0):
    """Frequency Error＝佔用頻帶的中心 (flo + fhi)/2 − 通道的 Center Frequency。flo／fhi 是一個數（回 float）或每通道一個值的陣列
    （兩者形狀要相同，回陣列；NaN 的邊緣給 NaN）。center＝None＝沒給（0.0）；不是有限實數純量丟工具列的 center 訊息；
    flo／fhi 不是實數數值丟 dsv:chmeas:*、None 丟 dsv:chmeas:MissingInput。"""
    cf = _parse_center(0.0 if center is None else center)
    edges = []
    for name, v in (("flo", flo), ("fhi", fhi)):
        a = _as_numeric("chmeas", v, name, name, _FLOAT_CLASSES, prefix="dsv")
        if np.iscomplexobj(a):
            raise _va_error("chmeas", "Real", name, name, prefix="dsv")
        edges.append(np.asarray(a, dtype=float))
    lo, hi = edges
    if lo.shape != hi.shape:
        raise _dsv_error("ShapeMismatch", a=lo.shape, b=hi.shape)
    with np.errstate(invalid="ignore", over="ignore"):                  # ±Inf 的邊緣相加是 NaN、1e308 級的相加溢位，都不印警告
        out = (lo + hi) / 2 - cf
    return float(out) if out.ndim == 0 else out


def channel_measure(pxx, f, start: Optional[float] = None, stop: Optional[float] = None, percent: Optional[float] = DEFAULT_PERCENT,
                    center: Optional[float] = None, rbw: Optional[float] = None) -> Dict[str, Any]:
    """obw() 規則的面板列（工具箱版；DSV 頻譜視窗要用 scope_channel_measure）：量測範圍 [start, stop]（None＝頻率格的端點）、
    佔用百分比 percent、通道 Center Frequency center（None＝(start + stop)/2；否則要是有限實數純量，不合格丟工具列的 center 訊息）。
    回傳 dict：power（範圍內總功率，線性）、bw、flo、fhi、obw_power、obw_center、ferr、以及用到的 start／stop／center／percent。
    pxx 是 PSD，或 rbw 不是 None 時的每 bin 功率。"""
    _check_dispatch("obw", f, rbw, None)
    p, fv, one_d = _parse_spectrum("obw", pxx, f, rbw)
    rng = None if start is None and stop is None else (fv[0] if start is None else start, fv[-1] if stop is None else stop)
    a, b = _parse_range("obw", rng, fv)
    pct = _parse_percent(percent)
    cf = (a + b) / 2 if center is None else _parse_center(center)
    bw, flo, fhi, pwr, tot = _obw_core(p, fv, a, b, pct)
    with np.errstate(invalid="ignore", over="ignore"):
        mid = (flo + fhi) / 2
        bw, flo, fhi, pwr, tot, mid, ferr = _squeeze(one_d, bw, flo, fhi, pwr, tot, mid, mid - cf)
    return {"power": tot, "bw": bw, "flo": flo, "fhi": fhi, "obw_power": pwr, "obw_center": mid, "ferr": ferr,
            "start": a, "stop": b, "center": cf, "percent": pct}


def _check_kind(kind: str) -> str:
    if not isinstance(kind, str) or kind not in ("psd", "power"):      # 先驗 str：numpy 陣列的 `in` 會丟「truth value is ambiguous」
        raise _dsv_error("InvalidKind", kind=kind)
    return kind


def _res_get(res: Dict[str, Any], key: str):
    """dsv_spectrum.welch 結果 dict 的鍵；缺了、或 res 根本不是 dict（None、陣列、字串、數字）丟 dsv:chmeas:MissingKey
    （不讓 KeyError／TypeError／IndexError 漏出去）。"""
    try:
        return res[key]
    except (KeyError, TypeError, IndexError, ValueError):
        raise _dsv_error("MissingKey", name=key) from None


def measure_welch(res: Dict[str, Any], start: Optional[float] = None, stop: Optional[float] = None, percent: Optional[float] = DEFAULT_PERCENT,
                  center: Optional[float] = None, kind: str = "psd") -> Dict[str, Any]:
    """拿 dsv_spectrum.welch 的結果 dict 用 obw() 規則量：kind＝"psd" 用 res["psd"]；"power" 用 res["power"] 並以 res["rbw"] 換成 PSD
    （MATLAB 的 Sxx/RBW，數值和用 psd 一樣）。kind＝None＝沒給（"psd"）；其他 kind → dsv:chmeas:InvalidKind；res 缺鍵 → dsv:chmeas:MissingKey。"""
    kind = "psd" if kind is None else kind
    if _check_kind(kind) == "power":
        return channel_measure(_res_get(res, "power"), _res_get(res, "f"), start, stop, percent, center, rbw=_res_get(res, "rbw"))
    return channel_measure(_res_get(res, "psd"), _res_get(res, "f"), start, stop, percent, center)


def _empty_fs_value(value, a: np.ndarray) -> float:
    """MATLAB 對空的 fs：等於把 2π 轉成 fs 的類別再轉 double（ref_obw_r3 的 obw_fs_*_empty 全部實測）：
    double／複數 double＝2π；single／複數 single＝single(2π)＝6.2831854820251465；half＝6.28125；整數類別四捨五入成 6；
    logical＝true＝1；char（''）＝char(6)＝6；cell／struct／datetime／duration（string 在 Python 沒有對應）丟
    MATLAB:cast:UnsupportedPrototype「Unsupported data conversion from 'double' to '<類別>'.」。"""
    k = a.dtype.kind
    if k in "fc":
        return float(np.asarray(2.0 * math.pi, dtype=a.real.dtype))
    if k in "iuUS":
        return float(round(2.0 * math.pi))
    if k == "b":
        return 1.0
    cls = _matlab_class(value, a)
    raise ChannelMeasureError("MATLAB:cast:UnsupportedPrototype", f"Unsupported data conversion from 'double' to '{cls}'.",
                              f"無法把 double 轉成 {cls}（空的 fs 會被 cast 成它的類別）。")


def periodogram_psd(x, fs: Optional[float] = None, func: str = "obw") -> Tuple[np.ndarray, np.ndarray]:
    """obw／powerbw 對時域輸入算的 PSD：矩形窗、NFFT＝N 的 periodogram（實數 → 單邊、複數 → 置中），
    fs＝None 或空（MATLAB isempty，含 ''）時用 2π（rad/sample；空陣列照類別做 cast，見 _empty_fs_value）。
    func＝錯誤識別碼用的函式名（MATLAB 的 obw 錯誤是 MATLAB:obw:*、powerbw 是 MATLAB:powerbw:*）。
    回傳 (pxx (N_f × 通道數；1-D 或列向量輸入給 1-D), f)。用 dsv_spectrum.welch 算（selftest 證明它和 MATLAB periodogram 一致）。
    順序照 MATLAB：fs 非空且不是單一數值 → dsv:chmeas:FsNotScalar（MATLAB 會改走 PSD 形式，見 _check_dispatch）；X（類別 → 2d →
    finite）→ Fs（類別 → real → finite → scalar → positive）→ 空訊號 MATLAB:periodogram:expectedNonempty → 只有 1 個樣本
    signal:computeperiodogram:NDMatrixUnsupported（兩者 ref_obw_r3 實測，含 [], zeros(0,1), zeros(1,0), zeros(5,0), 3.0, [1.0]）。
    1e308 級的樣本在 FFT 溢位成 Inf，不印 numpy 警告。x＝None 丟 dsv:chmeas:MissingInput；func＝None＝沒給（'obw'）；
    func 不是 'obw'／'powerbw' 丟 dsv:chmeas:InvalidFunc（不讓別的字串混進 MATLAB 識別碼）。"""
    from dsv_spectrum import welch
    func = "obw" if func is None else func
    if not isinstance(func, str) or func not in ("obw", "powerbw"):   # 先驗 str：numpy 陣列的 `in` 會丟「truth value is ambiguous」
        raise _dsv_error("InvalidFunc", func=func)
    fs_arr = None if fs is None else _to_array(fs)
    if fs_arr is not None and _matlab_numel(fs_arr) > 1:
        raise _dsv_error("FsNotScalar", func=func)
    what1, zh1 = _what(1, "X"), "第 1 個輸入 X"
    xa = _as_numeric(func, x, what1, zh1, _FLOAT_CLASSES)
    if xa.ndim > 2:
        raise _va_error(func, "2D", what1, zh1)
    _check_size(xa.size)
    one_d = xa.ndim <= 1 or xa.shape[0] == 1
    xa = xa.reshape(-1, 1) if one_d else xa
    if not np.all(np.isfinite(xa)):
        raise _va_error(func, "Finite", what1, zh1)
    if fs_arr is None:
        fs_v = 2.0 * math.pi
    elif _matlab_numel(fs_arr) == 0:                                    # 空的 fs → 2π 轉成 fs 的類別，不丟錯（實測）
        fs_v = _empty_fs_value(fs, fs_arr)
    else:
        what2, zh2 = _what(2, "Fs"), "第 2 個輸入 Fs"
        fa = _as_numeric(func, fs, what2, zh2)
        if np.iscomplexobj(fa):
            raise _va_error(func, "Real", what2, zh2)
        fa = np.asarray(fa, dtype=float)
        if not np.all(np.isfinite(fa)):
            raise _va_error(func, "Finite", what2, zh2)
        if fa.size != 1:
            raise _va_error(func, "Scalar", what2, zh2)
        fs_v = float(fa.reshape(()))
        if not fs_v > 0:
            raise _va_error(func, "Positive", what2, zh2)
    n = xa.shape[0]
    if xa.size == 0:                                                    # MATLAB isempty：0 個樣本，或 N×0 的零通道矩陣
        raise _fixed_error("MATLAB:periodogram:expectedNonempty")
    if n == 1:                                                          # 只有 1 個樣本（實測）
        raise _fixed_error("signal:computeperiodogram:NDMatrixUnsupported")
    w = np.ones(n)
    with np.errstate(over="ignore", invalid="ignore"):
        cols = [welch(xa[:, k], fs_v, w, 0, n, "onesided") for k in range(xa.shape[1])]
    p = np.column_stack([r["psd"] for r in cols])
    return (p[:, 0] if one_d else p), cols[0]["f"]


# ---------------------------------------------------------------- 工具箱函式：powerbw -----------------------------------------------------
def _rolloff_edge(q: np.ndarray, fv: np.ndarray, level: np.ndarray, start, upper: bool) -> np.ndarray:
    """x dB 頻寬的一側邊緣（每通道一個值）。q＝比較用的 PSD (N × 通道數)、level＝每通道的參考位準、start＝出發的 bin（每通道一個，
    或所有通道共用一個；None＝這一側沒有可出發的 bin）。upper＝False 從 start 往低頻找「最後一個 PSD ≤ level 的 bin」，
    upper＝True 往高頻找「第一個 PSD ≤ level 的 bin」：
    - 這一側找不到 → 回該側的頻譜端點（f_0 或 f_end）；
    - 找到的就是 start 本身（出發點已經在參考位準以下）→ NaN；
    - 否則在它和靠出發點那側的鄰 bin 之間，以「頻率 對 log10(PSD)」線性內插出 PSD 剛好等於 level 的頻率。PSD 先以最小正規化浮點數
      墊底（MATLAB 的 max(Pxx, realmin) 忽略 NaN，所以 NaN 的 bin 墊成 realmin：用 np.fmax，ref_obw_r3 powerbw_pxx_nan 的
      flo＝−0.0031469021983124373 就是這樣外插出來的），level＝0 時 log10 是 −Inf、結果照 IEEE 算（NaN／±Inf），不丟錯也不印警告。
      NaN 的 bin 不算「≤ level」（比較是 false），level 是 NaN 時兩側都找不到 → 端點。
    全部向量化、沒有逐通道迴圈。"""
    n, nch = q.shape
    end_value = fv[-1] if upper else fv[0]
    if start is None:
        return np.full(nch, end_value)
    origin = np.broadcast_to(np.asarray(start, dtype=int), (nch,))
    rows = np.arange(n)[:, None]
    with np.errstate(invalid="ignore"):
        under = q <= level[None, :]
    if upper:
        hit = np.where(under & (rows >= origin[None, :]), rows, n).min(axis=0)
        missing = hit == n
    else:
        hit = np.where(under & (rows <= origin[None, :]), rows, -1).max(axis=0)
        missing = hit == -1
    out = np.full(nch, end_value)
    at_origin = ~missing & (hit == origin)
    interp = ~missing & ~at_origin
    if interp.any():
        cols = np.nonzero(interp)[0]
        j = hit[cols]
        k = j - 1 if upper else j + 1                                  # 靠出發點那側的鄰 bin（PSD 在參考位準之上）
        psd_floor = np.finfo(float).tiny                               # 最小正規化 double（MATLAB realmin），讓 log10 不吃到 0
        with np.errstate(all="ignore"):
            yj = np.log10(np.fmax(q[j, cols], psd_floor))
            yk = np.log10(np.fmax(q[k, cols], psd_floor))
            out[cols] = fv[j] + (fv[k] - fv[j]) * (np.log10(level[cols]) - yj) / (yk - yj)
    out[at_origin] = np.nan
    return out


def _powerbw_core(p: np.ndarray, fv: np.ndarray, rng: Optional[Tuple[float, float]], gain: float, time_len: Optional[int]):
    nch = p.shape[1]
    widths = bin_widths(fv)
    c, bd = cumulative_power(p, fv)
    # 比較用的 PSD：單邊格的 DC bin（以及時域輸入、偶數長度的 Nyquist bin）在單邊 PSD 裡沒有像其他 bin 那樣加倍，比位準時補回來
    q = p.copy()
    with np.errstate(over="ignore"):                                   # 1e308 級的 PSD 加倍會溢位成 Inf，照 IEEE 往下算
        if fv[0] == 0:
            q[0] *= 2
        if time_len is not None and int(time_len) % 2 == 0:
            q[-1] *= 2
    if rng is None:
        # 每通道的峰值 bin：MATLAB max(…,[],1) 忽略 NaN、取第一個最大值；整欄都是 NaN 時回 NaN 與第 1 個 bin
        with np.errstate(invalid="ignore"):
            peak = np.argmax(np.where(np.isnan(q), -np.inf, q), axis=0)
        with np.errstate(invalid="ignore", over="ignore"):             # Inf 峰值 × gain＝0（|R| 很大時 10^(−|R|/10) 下溢成 0）→ NaN，照 IEEE
            level = q[peak, np.arange(nch)] * gain
        start_down = start_up = peak
    else:
        a, b = rng
        inside = (a <= fv) & (fv <= b)
        with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
            level = (p * widths[:, None])[inside].sum(axis=0) / widths[inside].sum() * gain  # 範圍內的平均 PSD（用未加倍的 p）
        mid = (a + b) / 2
        below_mid = np.nonzero(fv < mid)[0]
        above_mid = np.nonzero(fv > mid)[0]
        start_down = int(above_mid[0]) if above_mid.size else None     # 往低頻找：從中心右邊最近的 bin 出發
        start_up = int(below_mid[-1]) if below_mid.size else None      # 往高頻找：從中心左邊最近的 bin 出發
    flo = _rolloff_edge(q, fv, level, start_down, upper=False)
    fhi = _rolloff_edge(q, fv, level, start_up, upper=True)
    with np.errstate(invalid="ignore", over="ignore"):
        pwr = _power_at(c, bd, fhi) - _power_at(c, bd, flo)
        return fhi - flo, flo, fhi, pwr


def _parse_time_len(time_len) -> Optional[int]:
    """powerbw 的 time_len（DSV 自己的關鍵字，沒有 MATLAB 對應）：None，或非負整數純量（整數值的 float 也可）；其餘丟 dsv:chmeas:InvalidTimeLen。"""
    if time_len is None:
        return None
    a = _to_array(time_len)
    if a.size == 1 and a.dtype.kind in "iuf":
        v = float(a.reshape(()))
        if math.isfinite(v) and v >= 0 and v == math.floor(v):
            return int(v)
    raise _dsv_error("InvalidTimeLen", val=time_len)


def powerbw(pxx, f, rolloff_db: Optional[float] = None, freqrange: Optional[Sequence[float]] = None, *extra,
            rbw: Optional[float] = None, time_len: Optional[int] = None):
    """MATLAB powerbw：下降 |rolloff_db| dB（預設 10·log10(1/2) ≈ 3.01）的頻寬。freqrange 給了就以範圍內的平均 PSD 當參考位準、
    從範圍中心兩側最近的 bin 往外找；沒給就從峰值往兩側找。time_len＝原時域訊號長度（MATLAB 時域輸入的 Nyquist bin 修正：偶數長度時
    最後一個 bin ×2；None 或非負整數，其餘丟 dsv:chmeas:InvalidTimeLen），PSD 輸入給 None（時域形式請用 powerbw_time）。
    回傳 (bw, flo, fhi, power)；全零頻譜（參考位準 0）給 NaN，不丟錯。PSD 裡的 NaN 和 MATLAB 一樣不擋（validateattributes 的
    nonnegative 不看 NaN）：峰值與 realmin 墊底都忽略 NaN、功率被 NaN 污染（ref_obw_r3 的 powerbw_pxx_* 逐筆比）。
    MATLAB 會改走別的形式的引數形狀丟 dsv:chmeas:*（見 _check_dispatch）。"""
    _check_dispatch("powerbw", f, rbw, freqrange)
    p, fv, one_d = _parse_spectrum("powerbw", pxx, f, rbw)
    has_range = freqrange is not None and not _matlab_isempty(freqrange)
    if freqrange is not None and not has_range:
        _empty_range_conversion(freqrange)                             # 空的 cell／datetime／duration 範圍：double() 的轉換錯（實測 r4）
    rng = _parse_range("powerbw", freqrange, fv) if has_range else None
    if extra:
        raise _fixed_error("signal:powerbw:UnrecognizedAdditionalArguments")
    gain = 10.0 ** (_parse_rolloff(rolloff_db) / 10.0)
    return _squeeze(one_d, *_powerbw_core(p, fv, rng, gain, _parse_time_len(time_len)))


def powerbw_time(x, fs: Optional[float] = None, rolloff_db: Optional[float] = None, freqrange: Optional[Sequence[float]] = None, *extra):
    """MATLAB powerbw(x, fs, FREQRANGE, R)（時域形式）：矩形窗 periodogram、偶數長度時 Nyquist bin 加倍比較。fs＝None 或空 → 2π
    （空陣列照類別 cast）。時域驗證錯誤的識別碼是 MATLAB:powerbw:*。只有 1 個樣本
    （含 0-d 的純量）丟 signal:computeperiodogram:NDMatrixUnsupported（ref_obw_r3 powerbw_1sample／powerbw_1sample_vec 實測）。"""
    p, fv = periodogram_psd(x, fs, "powerbw")
    xa = _to_array(x)                                                   # periodogram_psd 已驗證過：數值、≤ 2 維、至少 2 個樣本
    n = xa.shape[0] if xa.ndim == 2 and xa.shape[0] != 1 else xa.size   # 照 MATLAB：向量（列向量也是）看元素數、矩陣看列數
    p2, fv, one_d = _parse_spectrum("powerbw", p, fv, None)
    has_range = freqrange is not None and not _matlab_isempty(freqrange)
    if freqrange is not None and not has_range:
        _empty_range_conversion(freqrange)                             # 實測 r11
    rng = _parse_range("powerbw", freqrange, fv, what="FREQRANGE", zh="FREQRANGE") if has_range else None
    if extra:
        raise _fixed_error("signal:powerbw:UnrecognizedAdditionalArguments")
    gain = 10.0 ** (_parse_rolloff(rolloff_db) / 10.0)
    return _squeeze(one_d, *_powerbw_core(p2, fv, rng, gain, n))


# ---------------------------------------------------------------- 工具箱函式：bandpower -----------------------------------------------------
def _parse_bandpower(pxx, f, freqrange) -> Tuple[np.ndarray, np.ndarray, bool, Optional[Tuple[float, float]]]:
    """MATLAB bandpower 自己的驗證順序：Pxx（double/single → 2d → finite → real；列向量轉一欄）、F（numeric → vector → finite → real →
    increasing → numel＝Pxx 列數）、FREQRANGE（numeric → vector → finite → real → numel 2 → increasing → 落在 F 內）。
    half 的 F／FREQRANGE 在 increasing 丟 half:error:FunctionNotDefinedForHalf（ref_obw_r6 h9–h13／o14–o20：F 含 Inf 是 expectedFinite、
    F 是矩陣是 expectedVector、FREQRANGE 1×3 是 incorrectNumel；F 短了／遞減、FREQRANGE 超出／遞減都是 half 錯）。"""
    what1, zh1 = _what(1, "Pxx"), "第 1 個輸入 Pxx"
    p = _as_numeric("bandpower", pxx, what1, zh1, _FLOAT_CLASSES)
    if p.ndim > 2:
        raise _va_error("bandpower", "2D", what1, zh1)
    _check_size(p.size)
    if not np.all(np.isfinite(p)):
        raise _va_error("bandpower", "Finite", what1, zh1)
    if np.iscomplexobj(p):
        raise _va_error("bandpower", "Real", what1, zh1)
    one_d = p.ndim <= 1 or p.shape[0] == 1
    p = np.asarray(p, dtype=float)
    p = p.reshape(-1, 1) if one_d else p
    what2, zh2 = _what(2, "F"), "第 2 個輸入 F"
    fa = _as_numeric("bandpower", f, what2, zh2)
    if fa.size == 0 or fa.ndim > 2 or (fa.ndim == 2 and min(fa.shape) != 1):
        raise _va_error("bandpower", "Vector", what2, zh2)
    if not np.all(np.isfinite(fa)):
        raise _va_error("bandpower", "Finite", what2, zh2)
    if np.iscomplexobj(fa):
        raise _va_error("bandpower", "Real", what2, zh2)
    if _is_half(f, fa):                                                # validateattributes 'increasing' 沒有 half 版
        raise _half_error()
    fv = np.asarray(fa, dtype=float).ravel()
    with np.errstate(over="ignore"):
        increasing = bool(np.all(np.diff(fv) > 0))
    if not increasing:
        raise _va_error("bandpower", "Increasing", what2, zh2)
    if fv.size != p.shape[0]:
        raise _numel_error("bandpower", what2, zh2, p.shape[0])
    if freqrange is None:
        return p, fv, one_d, None
    what3, zh3 = _what(3, "FREQRANGE"), "第 3 個輸入 FREQRANGE"
    r = _as_numeric("bandpower", freqrange, what3, zh3)
    if r.size == 0 or r.ndim > 2 or (r.ndim == 2 and min(r.shape) != 1):
        raise _va_error("bandpower", "Vector", what3, zh3)
    if not np.all(np.isfinite(r)):
        raise _va_error("bandpower", "Finite", what3, zh3)
    if np.iscomplexobj(r):
        raise _va_error("bandpower", "Real", what3, zh3)
    rv = np.asarray(r, dtype=float).ravel()
    if rv.size != 2:
        raise _numel_error("bandpower", what3, zh3, 2)
    if _is_half(freqrange, r):                                         # validateattributes 'increasing' 沒有 half 版
        raise _half_error()
    if not rv[1] > rv[0]:
        raise _va_error("bandpower", "Increasing", what3, zh3)
    if rv[0] < fv[0] or rv[1] > fv[-1]:
        raise _fixed_error("signal:bandpower:FreqRangeOutOfBounds")
    return p, fv, one_d, (float(rv[0]), float(rv[1]))


def _bandpower_strings(*args) -> None:
    """MATLAB bandpower 的字串引數檢查（在其他驗證之前，依引數順序看）：是 char 而且不是 'psd'（不分大小寫）就丟 signal:bandpower:IncorrectStringPsd；
    是 'psd' 的照樣往下傳，之後的類別檢查會丟 invalidType（ref_obw_r3 的 bandpower_*_char／bandpower_*_psd 實測）。"""
    for v in args:
        if v is not None and _is_char(v):
            a = _to_array(v)
            text = a.item() if a.size == 1 else None
            if isinstance(text, bytes):
                text = text.decode("latin-1")
            if not (isinstance(text, str) and text.lower() == "psd"):
                raise _fixed_error("signal:bandpower:IncorrectStringPsd")


def bandpower(pxx, f, freqrange: Optional[Sequence[float]] = None):
    """MATLAB bandpower(Pxx, F, [FREQRANGE], 'psd')：沒範圍＝Σ Pxx×寬度（每格寬度規則；只有一個頻率時 0/0＝NaN）；
    有範圍＝「最後一個 F ≤ a」到「第一個 F ≥ b」的 bin，寬度＝相鄰頻率差、最後一格 0。驗證照 MATLAB bandpower：先檢查字串引數
    （_bandpower_strings），再 _parse_bandpower。只供和 channel_power 比對。"""
    _bandpower_strings(pxx, f, freqrange)
    p, fv, one_d, rng = _parse_bandpower(pxx, f, freqrange)
    with np.errstate(over="ignore", invalid="ignore"):
        if rng is None:
            return _squeeze(one_d, bin_widths(fv) @ p)[0]
        a, b = rng
        i1 = int(np.nonzero(fv <= a)[0][-1])
        i2 = int(np.nonzero(fv >= b)[0][0])
        w = np.concatenate([np.diff(fv), [0.0]])
        return _squeeze(one_d, w[i1:i2 + 1] @ p[i1:i2 + 1])[0]


def mean_square(x):
    """MATLAB bandpower(x)（沒有頻率範圍；時域形式）＝每欄的平均功率 real(mean(conj(x)·x, 1))。
    驗證照它：先檢查字串引數（字串 x：'psd' 不分大小寫 → signal:bandpower:FreqVectorMissing、其他 → IncorrectStringPsd），
    再 X＝double/single → 2d → finite（列向量先轉成一欄，和 MATLAB 一樣當一個通道）；識別碼 MATLAB:bandpower:*。
    向量回 float、(N × 通道) 回每欄一個值。空的輸入照 MATLAB（ref_obw_r3 bandpower_empty_*）：Python 的 1-D []（和其他 1-D 序列
    一樣當列向量，即 MATLAB 的 zeros(1,0)，轉成 0×1）＝NaN；(0 × 2)＝[NaN NaN]；(0 × 0)（MATLAB 的 []）與 (3 × 0) 是 1×0 的空結果
    （這裡回 shape (0,) 的陣列）。不印 numpy 警告。"""
    if _is_char(x):
        _bandpower_strings(x)
        raise _fixed_error("signal:bandpower:FreqVectorMissing")       # bandpower('psd')：psdbandpower 沒有 F
    what1, zh1 = _what(1, "X"), "第 1 個輸入 X"
    xa = _as_numeric("bandpower", x, what1, zh1, _FLOAT_CLASSES)
    if xa.ndim > 2:
        raise _va_error("bandpower", "2D", what1, zh1)
    _check_size(xa.size)
    if not np.all(np.isfinite(xa)):
        raise _va_error("bandpower", "Finite", what1, zh1)
    one_d = xa.ndim <= 1 or xa.shape[0] == 1
    xa = xa.reshape(-1, 1) if one_d else xa
    n, nch = xa.shape
    if n == 0:
        out = np.full(nch, np.nan)
    else:
        # 逐欄各自加總（不用 axis=0 的二維歸約：那個加總順序和一維不同，會差 1 ulp），所以每一欄的值和單獨丟那一欄進來完全相同。
        # 一律先放寬成 double／complex double 再算（single／complex64 不留在單精度，見模組說明「已知差異（資料類別）」）
        wide = complex if np.iscomplexobj(xa) else float
        with np.errstate(over="ignore"):                                 # 1e308 級的樣本平方會溢位成 Inf，照 IEEE 往下算
            out = np.array([float(np.mean(np.real(np.conj(col) * col))) if wide is complex else float(np.mean(col ** 2))
                            for col in (np.ascontiguousarray(c, dtype=wide) for c in xa.T)])
    return float(out[0]) if one_d else out


# ---------------------------------------------------------------- scope 路徑（DSV 頻譜視窗要顯示的數字） -------------------------------------
def to_dbm(p):
    """線性功率（W，ReferenceLoad 1）→ dBm＝10·log10(p)+30；0 → −Inf、負值／NaN → NaN，不印警告（scope 的顯示換算）。
    不是實數陣列丟 dsv:chmeas:invalidType／expectedReal。"""
    a = _as_numeric("chmeas", p, "the power", "功率", _FLOAT_CLASSES, prefix="dsv")
    if np.iscomplexobj(a):
        raise _va_error("chmeas", "Real", "the power", "功率", prefix="dsv")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 10.0 * np.log10(np.asarray(a, dtype=float)) + 30.0
    return float(out) if np.ndim(out) == 0 else out


def _finite_real_scalar(value) -> Optional[float]:
    """工具列欄位的值：有限實數純量才回 float，否則 None（NaN／Inf／複數／非數值／多個元素都算不合格）。"""
    try:
        a = np.asarray(value)
    except Exception:                                                  # noqa: BLE001
        return None
    if a.dtype.kind not in "iuf" or a.size != 1:
        return None
    v = float(a.reshape(()))
    return v if math.isfinite(v) else None


def scope_band(mode: str = "span", span: float = DEFAULT_SPAN, center: float = DEFAULT_CENTER,
               start: float = DEFAULT_START, stop: float = DEFAULT_STOP) -> Tuple[float, float, float]:
    """面板的 Frequency Options → 量測頻帶 (a, b, CF)：mode＝"span"（Span and Center Frequency：a＝CF − Span/2、b＝CF + Span/2、
    CF＝Center Frequency）或 "startstop"（Start and Stop Frequencies：a＝Start、b＝Stop、CF＝(Start + Stop)/2，擷取證明 O4）。
    欄位不合格丟 MATLAB Spectrum Analyzer 工具列的訊息（span 要是有限正實數、其餘有限實數）；Stop ≤ Start 丟 dsv:chmeas:StartStopOrder（未定）；
    mode 打錯丟 dsv:chmeas:InvalidMode。每個引數 None＝沒給＝用預設值。"""
    mode = "span" if mode is None else mode
    if not isinstance(mode, str):                                       # numpy 陣列的 == 會給陣列、`if` 丟「truth value is ambiguous」
        raise _dsv_error("InvalidMode", mode=mode)
    if mode == "span":
        s = _finite_real_scalar(DEFAULT_SPAN if span is None else span)
        if s is None or not s > 0:
            raise _ui_error("span")
        cf = _finite_real_scalar(DEFAULT_CENTER if center is None else center)
        if cf is None:
            raise _ui_error("center")
        return cf - s / 2, cf + s / 2, cf
    if mode == "startstop":
        a = _finite_real_scalar(DEFAULT_START if start is None else start)
        if a is None:
            raise _ui_error("start")
        b = _finite_real_scalar(DEFAULT_STOP if stop is None else stop)
        if b is None:
            raise _ui_error("stop")
        if not b > a:
            raise _dsv_error("StartStopOrder")
        return a, b, (a + b) / 2
    raise _dsv_error("InvalidMode", mode=mode)


def scope_auto_span(display_start: float, display_stop: float) -> Dict[str, Any]:
    """第一次啟用通道量測時 scope 寫進設定的 auto-span（擷取 O7，自動算頻帶的公式）：中心＝顯示範圍中點、Span＝寬度/5、
    AdjacentBW＝寬度/10、ACPROffsets＝[4 7]·寬度/20。「顯示範圍」是 scope 的 x 軸範圍（FrequencySpan full 時雙邊 [−fs/2, fs/2]、
    單邊 [0, fs/2]；scope_state 的 StartFrequency／StopFrequency），不是第一、最後一個 bin：單邊擷取 [0 5000] → 2500／1000／500／
    [1000 1750]，雙邊 [−5000 5000] → 0／2000／1000／[2000 3500]（用 bin 格 −4995.1..5000 會得到 1999.02，和擷取不符）。
    觸發時機未定（見模組說明），由 GUI 決定。顯示範圍不是有限實數丟工具列的 start／stop 訊息、stop ≤ start 丟 dsv:chmeas:StartStopOrder。"""
    a = _finite_real_scalar(display_start)
    if a is None:
        raise _ui_error("start")
    b = _finite_real_scalar(display_stop)
    if b is None:
        raise _ui_error("stop")
    if not b > a:
        raise _dsv_error("StartStopOrder")
    width = b - a
    cf = (a + b) / 2
    span = width / 5
    return {"center": cf, "span": span, "start": cf - span / 2, "stop": cf + span / 2,
            "adjacent_bw": width / 10, "acpr_offsets": [4 * width / 20, 7 * width / 20]}


def _parse_trace(trace, f, df: Optional[float]) -> Tuple[np.ndarray, np.ndarray, float, bool]:
    """顯示 trace（線性 W 或 W/Hz，1-D 或 N × 通道）與等距頻率格 → (trace (N × 通道), f (N), df, one_d)。識別碼 dsv:chmeas:*。"""
    what1, zh1 = "the displayed trace", "顯示的頻譜 trace"
    t = _as_numeric("chmeas", trace, what1, zh1, _FLOAT_CLASSES, prefix="dsv")
    if t.ndim > 2:
        raise _va_error("chmeas", "2D", what1, zh1, prefix="dsv")
    if np.iscomplexobj(t):
        raise _va_error("chmeas", "Real", what1, zh1, prefix="dsv")
    t = np.asarray(t, dtype=float)
    _check_size(t.size)
    one_d = t.ndim <= 1 or t.shape[0] == 1
    t = t.reshape(-1, 1) if one_d else t
    with np.errstate(invalid="ignore"):
        if not np.all(t >= 0):
            raise _va_error("chmeas", "Nonnegative", what1, zh1, prefix="dsv")
    what2, zh2 = "the frequency grid", "頻率格"
    fa = _as_numeric("chmeas", f, what2, zh2, prefix="dsv")
    if np.iscomplexobj(fa):
        raise _va_error("chmeas", "Real", what2, zh2, prefix="dsv")
    if fa.size == 0 or fa.ndim > 2 or (fa.ndim == 2 and min(fa.shape) != 1):
        raise _va_error("chmeas", "Vector", what2, zh2, prefix="dsv")
    fv = np.asarray(fa, dtype=float).ravel()
    if not np.all(np.isfinite(fv)):
        raise _va_error("chmeas", "Finite", what2, zh2, prefix="dsv")
    if fv.size != t.shape[0]:
        raise _dsv_error("FreqVectorMismatch")
    n = fv.size
    with np.errstate(over="ignore", invalid="ignore"):                  # 1e308 級的格相減會溢位成 Inf → 判成非等距，不印警告
        if df is None:
            if n < 2:
                raise _dsv_error("GridTooShort")
            df_v = float((fv[-1] - fv[0]) / (n - 1))
        else:
            d = _finite_real_scalar(df)
            if d is None or not d > 0:
                raise _dsv_error("NonuniformGrid")
            df_v = d
        if not (math.isfinite(df_v) and df_v > 0) or (n > 1 and not np.max(np.abs(np.diff(fv) - df_v)) <= 1e-6 * df_v):
            raise _dsv_error("NonuniformGrid")
    return t, fv, float(df_v), one_d


def _step_integral(c: np.ndarray, borders: np.ndarray, x: float) -> float:
    """分段常數 PSD 的累積功率 C(x)：c＝[0, 逐 bin 功率累積]（N+1）、borders＝bin 邊界（N+1）；相鄰邊界之間線性。"""
    i = int(np.searchsorted(borders, x, side="left"))
    i = min(max(i, 1), borders.size - 1)
    return c[i - 1] + (c[i] - c[i - 1]) * (x - borders[i - 1]) / (borders[i] - borders[i - 1])


def _step_inverse(c: np.ndarray, borders: np.ndarray, target: float) -> float:
    """C 的反函數：累積功率剛好等於 target 的頻率（第一個 c_i ≥ target 的 bin 內線性）。"""
    i = int(np.searchsorted(c, target, side="left"))
    i = min(max(i, 1), borders.size - 1)
    return borders[i - 1] + (borders[i] - borders[i - 1]) * (target - c[i - 1]) / (c[i] - c[i - 1])


def _scope_core(pxx: np.ndarray, f: np.ndarray, df: float, a: float, b: float, pct: float) -> Tuple[np.ndarray, ...]:
    """scope 的積分（O2／O3）：bin k 蓋 [f_k − df/2, f_k + df/2]（含兩端），總功率＝C(b) − C(a)，邊緣＝C⁻¹(C(a) + (100∓P)/200·tot)。
    回傳 (tot, flo, fhi)，每通道一個值。"""
    nch = pxx.shape[1]
    tot, flo, fhi = np.empty(nch), np.empty(nch), np.empty(nch)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        borders = np.concatenate([f - df / 2, [f[-1] + df / 2]])
        c_all = np.vstack([np.zeros((1, nch)), np.cumsum(pxx * df, axis=0)])
        for k in range(nch):
            c = c_all[:, k]
            lo = _step_integral(c, borders, a)
            tot[k] = _step_integral(c, borders, b) - lo
            flo[k] = _step_inverse(c, borders, lo + (100.0 - pct) / 200.0 * tot[k])
            fhi[k] = _step_inverse(c, borders, lo + (100.0 + pct) / 200.0 * tot[k])
    return tot, flo, fhi


def scope_channel_measure(trace, f, rbw: Optional[float] = None, start: float = DEFAULT_START, stop: float = DEFAULT_STOP,
                          percent: float = DEFAULT_PERCENT, center: Optional[float] = None, kind: str = "power",
                          df: Optional[float] = None) -> Dict[str, Any]:
    """MATLAB spectrumAnalyzer 的 Occupied BW 面板那一列，照擷取證明的規則（模組說明 A）。
    trace＝顯示的 normal trace（線性：kind＝"power" 是每 bin 功率 W，PSD＝trace/rbw；kind＝"psd" 已是 W/Hz）、f＝等距頻率格、
    rbw＝ENBW（Hz，kind＝"power" 必填）、[start, stop]＝量測頻帶（用 scope_band() 從 Span/CF 或 Start/Stop 算）、center＝Center
    Frequency（None＝(start+stop)/2）、df＝bin 間距（None＝從 f 算）。
    回傳 dict：power（W）、power_dbm、bw、flo、fhi、obw_center、ferr、inside（頻帶是否在 [f_first, f_last] 內；不在就全 NaN）、
    start／stop／center／percent／rbw／df。1-D trace 回 float、(N × 通道) 回每通道一個值。
    有預設值的引數（start／stop／percent／kind／center／df）None＝沒給＝預設值；trace／f＝None 丟 dsv:chmeas:MissingInput。"""
    kind = "power" if kind is None else kind
    _check_kind(kind)
    t, fv, df_v, one_d = _parse_trace(trace, f, df)
    pct = _finite_real_scalar(DEFAULT_PERCENT if percent is None else percent)
    if pct is None or not 0 < pct < 100:
        raise _ui_error("percent")
    a = _finite_real_scalar(DEFAULT_START if start is None else start)
    if a is None:
        raise _ui_error("start")
    b = _finite_real_scalar(DEFAULT_STOP if stop is None else stop)
    if b is None:
        raise _ui_error("stop")
    if not b > a:
        raise _dsv_error("StartStopOrder")
    cf = (a + b) / 2 if center is None else _finite_real_scalar(center)
    if cf is None:
        raise _ui_error("center")
    rbw_v = None
    if kind == "power":
        rbw_v = _finite_real_scalar(rbw)
        if rbw_v is None or not rbw_v > 0:
            raise _dsv_error("RBWRequired")
        pxx = t / rbw_v
    else:
        pxx = t
    nch = t.shape[1]
    inside = not (a < fv[0] or b > fv[-1])
    if inside:
        tot, flo, fhi = _scope_core(pxx, fv, df_v, a, b, pct)
    else:
        tot = flo = fhi = np.full(nch, np.nan)
    with np.errstate(invalid="ignore", over="ignore"):
        mid = (flo + fhi) / 2
        tot, bw, flo, fhi, mid, ferr = _squeeze(one_d, tot, fhi - flo, flo, fhi, mid, mid - cf)
    return {"power": tot, "power_dbm": to_dbm(tot), "bw": bw, "flo": flo, "fhi": fhi, "obw_center": mid, "ferr": ferr,
            "inside": inside, "start": a, "stop": b, "center": cf, "percent": pct, "rbw": rbw_v, "df": df_v}


def scope_measure_welch(res: Dict[str, Any], start: float = DEFAULT_START, stop: float = DEFAULT_STOP, percent: float = DEFAULT_PERCENT,
                        center: Optional[float] = None, kind: str = "power") -> Dict[str, Any]:
    """拿 dsv_spectrum.welch 的結果 dict（normal trace：res["power"] 或 res["psd"]、res["f"]、res["rbw"]）直接做 scope 量測。
    有 Max-Hold 時也要餵 normal trace（擷取 O6），所以這裡不看 res["max_power"]。res 缺鍵 → dsv:chmeas:MissingKey。
    kind＝None＝沒給（"power"）；start／stop／percent／center 的 None 由 scope_channel_measure 換成預設值。"""
    kind = "power" if kind is None else kind
    if _check_kind(kind) == "power":
        return scope_channel_measure(_res_get(res, "power"), _res_get(res, "f"), _res_get(res, "rbw"), start, stop, percent, center, "power")
    return scope_channel_measure(_res_get(res, "psd"), _res_get(res, "f"), None, start, stop, percent, center, "psd")


# ---------------------------------------------------------------- selftest -----------------------------------------------------------------
# 比對容差：MATLAB 存下的 PSD 餵進來 → 和 MATLAB 的運算順序相同，位元級一致（實測最大相對誤差 1.9e-15，報告 check_obw.py）；
# DSV 自己的 periodogram／welch（numpy pocketfft）對 MATLAB 的 FFT 實測最大相對誤差 4.6e-13（2048 點、含 PSD 很小的 bin），
# 所以 DSV 自算 PSD 的鏈路也用 1e-12（約 2 倍餘裕），不再用 1e-9。
TOL = 1e-12
# scope 擷取的殘差：分析報告的最大值（ANALYSIS.md §2.1／rules.json O2–O4）是 1.1e-13 dB／1.7e-10 Hz／8.4e-11 Hz（numpy 2、pocketfft＋
# Accelerate 的建置 venv），/opt/anaconda3 的 numpy 1.26（OpenBLAS 建置）量到 1.0e-13／1.9e-10／9.8e-11——那個 numpy 的
# dsv_spectrum.welch 對同一筆輸入連跑不是位元級可重現（40 次有 35 次不同、最大相對差 6.7e-16；OPENBLAS_NUM_THREADS=1 也一樣），
# 反向內插把它放大成 1e-10 Hz 級的邊緣位移。這些只是浮點捨入（擷取值是釘死的、不動），上限照規定取實測最大值的 2 倍以上餘裕：
# 2.2e-13 dB／4e-10 Hz／2e-10 Hz；selftest 印出實測殘差
SCOPE_TOL_CP_DB, SCOPE_TOL_BW_HZ, SCOPE_TOL_FE_HZ = 2.2e-13, 4e-10, 2e-10
# 頻譜模型（numpy）對擷取到的顯示值：ANALYSIS.md §1 的表，obw_real_* 2.1e-12 dB（精確值 2.1032064978498966e-12）、obw_cplx_* 9.5e-13 dB
# （每筆的精確值存在擷取檔 display.analysis_max_abs_dB_vs_model，selftest 逐筆用它當上限、不加餘裕；這個常數是整組的最大值）。
# 擷取檔 reference_compare 裡的 2.7e-13 dB 是 MATLAB 自己的 periodogram 對顯示值，不是這裡的 numpy 模型。
SCOPE_TOL_DISPLAY_DB = 2.1032064978498966e-12


def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/obw_chpower/ref_obw_chpower.json；ref_obw_chpower.m 產生），
    再拿 spectrumAnalyzer 實際擷取的 22 筆 obw_* 量測（tests/matlab_ref/scope/obw_chpower/scope_obw_captures.json）逐筆重算。"""
    import json
    import os
    import time as _time
    import warnings
    from dsv_spectrum import design_window, welch
    d = os.path.join(ref_dir, "obw_chpower")
    path = os.path.join(d, "ref_obw_chpower.json")
    if not os.path.isfile(path):
        check(True, "（沒有 tests/matlab_ref/obw_chpower：略過 MATLAB 通道量測比對）")
        return
    R = json.load(open(path, encoding="utf-8"))
    fs = float(R["fs"])
    xr = np.loadtxt(os.path.join(d, "in_x_real.txt"))
    xc = np.loadtxt(os.path.join(d, "in_x_cplx_re.txt")) + 1j * np.loadtxt(os.path.join(d, "in_x_cplx_im.txt"))
    x2 = np.loadtxt(os.path.join(d, "in_x_mat_col2.txt"))
    W = R["welch"]

    def arr(v):
        """參考值 → float 陣列：JSON 的 list／純量（None＝NaN），或 DSV 自己算出的 ndarray／純量（DSV 對 DSV 的比對）。"""
        v = v.tolist() if isinstance(v, np.ndarray) else v
        v = v if isinstance(v, list) else [v]
        return np.asarray([np.nan if x is None else x for x in v], dtype=float)

    stats = {"n": 0, "worst": 0.0}

    def close(got, ref, rtol=TOL):
        """逐值比：NaN 要兩邊都 NaN；其餘 |got − ref| ≤ rtol·|ref|。順便記最大相對誤差與比了幾個值。"""
        g, r = np.atleast_1d(np.asarray(got, dtype=float)), arr(ref)
        if g.shape != r.shape:
            return False
        stats["n"] += r.size
        nan_ok = np.isnan(g) == np.isnan(r)
        both = ~np.isnan(r) & ~np.isnan(g)
        gg, rr = g[both], r[both]
        with np.errstate(invalid="ignore", divide="ignore"):
            e = np.where(rr != 0, np.abs(gg - rr) / np.abs(rr), np.where(gg == 0, 0.0, np.inf))   # 參考值是 0 → 要剛好等於 0
        if e.size:
            stats["worst"] = max(stats["worst"], float(np.max(e)))
        return bool(nan_ok.all() and np.all(e <= rtol))

    def rng_of(s):
        return None if s == "[]" else tuple(float(t) for t in s.strip("[]").split())

    # 1) DSV 的 periodogram／welch 要和 MATLAB 餵給 obw 的 PSD 一樣（時域案例先經過這一步）：頻率格要完全相等、PSD／功率 1e-12
    N = xr.size
    pr, fr = periodogram_psd(xr, fs)
    pc, fc = periodogram_psd(xc, fs)
    hann = design_window("hann", 256)
    wr = welch(xr, fs, hann, 128, 256, "onesided")
    wc = welch(xc, fs, hann, 128, 256, "centered")
    wr2 = welch(xr, fs, hann, 128, 256, "centered")
    ok = (close(fr, R["periodogram_real"]["f"], 0) and close(pr, R["periodogram_real"]["pxx"])
          and close(fc, R["periodogram_cplx"]["f"], 0) and close(pc, R["periodogram_cplx"]["pxx"])
          and close(wr["f"], W["real_onesided"]["f"], 0) and close(wr["psd"], W["real_onesided"]["pxx"])
          and close(wc["f"], W["cplx_centered"]["f"], 0) and close(wc["psd"], W["cplx_centered"]["pxx"])
          and close(wr2["f"], W["real_centered"]["f"], 0) and close(wr2["psd"], W["real_centered"]["pxx"])
          and close(wr["f"], W["real_onesided_power"]["f"], 0) and close(wr["power"], W["real_onesided_power"]["sxx"])
          and close(wc["f"], W["cplx_centered_power"]["f"], 0) and close(wc["power"], W["cplx_centered_power"]["sxx"])
          and close(wr["rbw"], W["rbw"]))
    check(ok, f"PSD 來源 vs MATLAB：periodogram（矩形窗、NFFT＝{N}，實數單邊／複數置中）與 pwelch（Hann 256、重疊 128：單邊／置中 psd、"
              f"power、RBW {wr['rbw']:g} Hz）的頻率格完全相等、數值在 {TOL:g} 內和 obw 參考用的輸入一致（最大相對誤差 {stats['worst']:.1e}）")

    # 2) obw 時域輸入：obw_time（時域形式）與「periodogram_psd 再 obw」兩種寫法都要一致
    bad = []
    alt_worst = 0.0
    for case in R["obw_time"]:
        nm, a = case["name"], case["args"]
        if nm.startswith("mat"):
            xin, fs_in = np.column_stack([xr, x2]), fs
        elif "normfreq" in nm:
            xin, fs_in = xr, None
        else:
            xin, fs_in = (xr if nm.startswith("real") else xc), fs
        rg = rng_of(a[1]) if len(a) > 1 else None
        bw, flo, fhi, pwr = obw_time(xin, fs_in, case["P"], rg)
        p, f = periodogram_psd(xin, fs_in)
        alt = obw(p, f, case["P"], rg)
        tot = channel_power(p, f, *(rg or (None, None)))
        # obw_time 和「periodogram_psd 再 obw」是同一條鏈：兩次 welch 在 anaconda 的 numpy 1.26 上會差幾個 ulp（實測 6.7e-16，
        # 見 SCOPE_TOL 的註解），所以用 TOL 比而不是位元級；venv 的 numpy 是位元級相同（差 0.0），實測差印在訊息裡
        alt_same = all(close(u, v) for u, v in zip((bw, flo, fhi, pwr), alt))
        good = (close(bw, case["bw"]) and close(flo, case["flo"]) and close(fhi, case["fhi"]) and close(pwr, case["pwr"])
                and close(frequency_error(flo, fhi, 0.0), case["center"]) and close(tot, case["totpwr_from_pwr"]) and alt_same)
        if fs_in is None:                                              # 空的 fs 和沒給 fs 一樣是 2π
            good = good and all(close(u, v) for u, v in zip(obw_time(xin, [], case["P"], rg), (bw, flo, fhi, pwr))) \
                and all(close(u, v) for u, v in zip(obw_time(xin, np.zeros((0, 2)), case["P"], rg), (bw, flo, fhi, pwr)))
        with np.errstate(invalid="ignore", divide="ignore"):
            alt_worst = max(alt_worst, max(float(np.max(np.abs(np.asarray(u, dtype=float) - np.asarray(v, dtype=float)) / np.abs(np.asarray(v, dtype=float))))
                                           for u, v in zip((bw, flo, fhi, pwr), alt)))
        if not good:
            bad.append(f"{nm}@P{case['P']}: got {(bw, flo, fhi, pwr)} ref {(case['bw'], case['flo'], case['fhi'], case['pwr'])}")
    check(not bad, f"佔用頻寬 vs MATLAB obw(x, fs)（obw_time，時域 {len(R['obw_time'])} 組，rtol {TOL:g}：實數 P＝99／90／50／99.99／0.01／99.5、"
                   f"預設 P、rad/sample（fs 沒給與 fs＝[] 兩種寫法同值）、範圍 [500 3000]／[1000 1500]／格外 [1234.5 2345.6]、"
                   f"複數 I/Q 全頻／[−500 2500]／[400 1400]、兩欄矩陣）："
                   f"bw、flo、fhi、pwr、中心、範圍總功率逐筆一致，且和 periodogram_psd＋obw 同值（兩次 welch 的最大相對差 {alt_worst:.1e}；"
                   f"anaconda 的 numpy 1.26 連跑 welch 不是位元級可重現，容差 {TOL:g}）" + (f"（不一致：{bad}）" if bad else ""))

    # 3) obw PSD／功率譜輸入：MATLAB 存的 pwelch 輸入（位元級）與 DSV 自己的 welch 輸入，都用 1e-12
    src_m = {"real_onesided": (arr(W["real_onesided"]["pxx"]), arr(W["real_onesided"]["f"])),
             "cplx_centered": (arr(W["cplx_centered"]["pxx"]), arr(W["cplx_centered"]["f"])),
             "real_centered": (arr(W["real_centered"]["pxx"]), arr(W["real_centered"]["f"]))}
    pow_m = {"real_onesided": (arr(W["real_onesided_power"]["sxx"]), arr(W["real_onesided_power"]["f"])),
             "cplx_centered": (arr(W["cplx_centered_power"]["sxx"]), arr(W["cplx_centered_power"]["f"]))}
    src_d = {"real_onesided": (wr["psd"], wr["f"]), "cplx_centered": (wc["psd"], wc["f"]), "real_centered": (wr2["psd"], wr2["f"])}
    pow_d = {"real_onesided": (wr["power"], wr["f"]), "cplx_centered": (wc["power"], wc["f"])}

    def key_of(nm):
        return "real_onesided" if ("real_onesided" in nm or "matrix" in nm) else ("cplx_centered" if "cplx" in nm else "real_centered")

    for label, src, pw, rbw_v in (("MATLAB pwelch 輸入", src_m, pow_m, float(W["rbw"])), ("DSV welch 輸入", src_d, pow_d, wr["rbw"])):
        bad = []
        for case in R["obw_psd"]:
            nm, a = case["name"], case["args"]
            key = key_of(nm)
            if nm.startswith("power"):
                p, f = pw[key]
                rg = rng_of(a[2])
                bw, flo, fhi, pwr = obw(p, f, case["P"], rg, rbw=rbw_v)
                tot = channel_power(p, f, *(rg or (None, None)), rbw=rbw_v)
            else:
                p, f = src[key]
                if "matrix" in nm:
                    p = np.column_stack([p, 2 * p])
                rg = rng_of(a[1]) if len(a) > 1 else None
                bw, flo, fhi, pwr = obw(p, f, case["P"], rg)
                tot = channel_power(p, f, *(rg or (None, None)))
            good = (close(bw, case["bw"]) and close(flo, case["flo"]) and close(fhi, case["fhi"]) and close(pwr, case["pwr"])
                    and close(frequency_error(flo, fhi, 0.0), case["center"]) and close(tot, case["totpwr_from_pwr"]))
            if not good:
                bad.append(f"{nm}@P{case['P']}: got {(bw, flo, fhi, pwr)} ref {(case['bw'], case['flo'], case['fhi'], case['pwr'])}")
        check(not bad, f"佔用頻寬 vs MATLAB obw(Pxx, F)／obw(Sxx, F, RBW)（{label}，{len(R['obw_psd'])} 組，rtol {TOL:g}：單邊實數六種 P、兩引數、"
                       f"[500 3000]／格外 [777.7 2222.2]／[1000 1500]、置中複數全頻／[−500 2500]／格外、置中實數全頻／[0 fs/2]／[−1000 1000]／"
                       f"[1000 1500]、兩欄矩陣、功率譜＋RBW 三組）：bw、flo、fhi、pwr、中心、範圍總功率逐筆一致" + (f"（不一致：{bad}）" if bad else ""))

    # 4) channel_measure／measure_welch（obw 規則的面板列）——MATLAB 存的輸入（位元級）與 DSV welch 的結果 dict，含兩欄矩陣
    bad = []
    n_rows = 0
    for case in R["obw_psd"]:
        nm, a = case["name"], case["args"]
        key = key_of(nm)
        kind = "power" if nm.startswith("power") else "psd"
        rg = rng_of(a[2] if kind == "power" else a[1]) if len(a) > 1 else None
        p_m, f_m = (pow_m if kind == "power" else src_m)[key]
        res_d = {"real_onesided": wr, "cplx_centered": wc, "real_centered": wr2}[key]
        matrix = "matrix" in nm
        if matrix:
            p_m = np.column_stack([p_m, 2 * p_m])
            res_d = dict(res_d, psd=np.column_stack([res_d["psd"], 2 * res_d["psd"]]))
        for label, m in (("MATLAB", channel_measure(p_m, f_m, *(rg or (None, None)), percent=case["P"],
                                                     rbw=float(W["rbw"]) if kind == "power" else None)),
                         ("DSV", measure_welch(res_d, *(rg or (None, None)), percent=case["P"], kind=kind))):
            n_rows += 1
            ref_ferr = (arr(case["flo"]) + arr(case["fhi"])) / 2 - m["center"]
            good = (close(m["power"], case["totpwr_from_pwr"]) and close(m["bw"], case["bw"]) and close(m["flo"], case["flo"])
                    and close(m["fhi"], case["fhi"]) and close(m["obw_power"], case["pwr"])
                    and close(m["obw_center"], case["center"])
                    and bool(np.all(np.abs(np.atleast_1d(m["ferr"]) - ref_ferr) <= TOL * np.maximum(np.abs(arr(case["flo"])), np.abs(arr(case["fhi"])))))
                    and (isinstance(m["bw"], np.ndarray) and m["bw"].shape == (2,)) == matrix)
            if not good:
                bad.append(f"{nm}/{label}: {m}")
    m0 = measure_welch(wr2, -1000.0, 1000.0, 99.0)
    sym = abs(m0["ferr"]) < TOL and abs(m0["center"]) == 0.0
    m1 = measure_welch(wr, 1000.0, 1500.0, 50.0, center=1250.0)
    check(not bad and sym, f"面板量測 channel_measure／measure_welch（obw 規則；MATLAB 存的輸入與 DSV welch 結果、psd 與 power＋rbw 兩種來源，"
                           f"{n_rows} 列含兩欄矩陣，rtol {TOL:g}）：Channel Power＝範圍總功率、Occupied BW、佔用中心、Frequency Error＝中心 − "
                           f"Center Frequency 逐筆一致；置中實數 [−1000 1000] 的誤差 {m0['ferr']:.2e} Hz，[1000 1500] P50 中心 1250 → 誤差 "
                           f"{m1['ferr']:.4f} Hz" + (f"（不一致：{bad}）" if bad else ""))

    # 5) powerbw（x dB 頻寬）：含 NaN 案例；時域案例用 powerbw_time
    bad = []
    for case in R["powerbw"]:
        nm, a = case["name"], case["args"]
        tin = "_time_" in nm
        k0 = 2 if nm.startswith("pbw_power") else 1               # 功率譜形式的 args 多一個 RBW
        rg = rng_of(a[k0]) if len(a) > k0 else None
        rdb = float(a[k0 + 1]) if len(a) > k0 + 1 else None
        if tin:
            got = powerbw_time(xr if "real" in nm else xc, fs, rdb, rg)
        elif nm.startswith("pbw_power"):
            p, f = pow_m["real_onesided"]
            got = powerbw(p, f, rdb, rg, rbw=float(W["rbw"]))
        else:
            p, f = src_m["real_onesided" if "real" in nm else "cplx_centered"]
            got = powerbw(p, f, rdb, rg)
        refs = (case["bw"], case["flo"], case["fhi"], case["pwr"])
        if not all(close(g, r) for g, r in zip(got, refs)):
            bad.append(f"{nm}: got {got} ref {refs}")
    nan_case = next(c for c in R["powerbw"] if c["bw"] is None)
    check(not bad, f"x dB 頻寬 vs MATLAB powerbw（{len(R['powerbw'])} 組，rtol {TOL:g}：時域（powerbw_time）預設 3 dB／R＝10／範圍 [1000 1500] R＝3"
                   f"（MATLAB 給 NaN：{nan_case['name']}）、複數時域、PSD 預設／R＝20／範圍、置中複數、功率譜＋RBW）：bw、flo、fhi、pwr 逐筆一致"
                   + (f"（不一致：{bad}）" if bad else ""))

    # 6) bandpower／均方：另一種「通道功率」定義，以及 Parseval
    B = {c["name"]: c["value"] for c in R["bandpower"]}
    pxr, fxr = src_m["real_onesided"]
    pxc, fxc = src_m["cplx_centered"]
    ok = (close(bandpower(pxr, fxr, (500, 3000)), B["bandpower_psd_real_onesided_500_3000"])
          and close(bandpower(pxr, fxr), B["bandpower_psd_real_onesided_full"])
          and close(bandpower(pxc, fxc, (-500, 2500)), B["bandpower_psd_cplx_centered_m500_2500"])
          and close(mean_square(xr), B["bandpower_time_real"]) and close(mean_square(xr), B["meansq_time_real"])
          and close(mean_square(xc), B["meansq_time_cplx"])
          and close(channel_power(pxr, fxr), B["bandpower_psd_real_onesided_full"])
          and close(channel_power(pr, fr), mean_square(xr)) and close(channel_power(pc, fc), mean_square(xc)))
    ms2 = mean_square(np.column_stack([xr, x2]))                       # MATLAB bandpower：mean(conj(x).*x, 1) 逐欄 → 每欄一個值
    ok = ok and isinstance(ms2, np.ndarray) and ms2.shape == (2,) and ms2[0] == mean_square(xr) and ms2[1] == mean_square(x2) \
        and mean_square(xr[None, :]) == mean_square(xr) and isinstance(mean_square(xr), float)
    cp = channel_power(pxr, fxr, 500, 3000)
    check(ok, f"bandpower vs MATLAB（PSD 全頻／[500 3000]／置中 [−500 2500]、時域＝均方（向量 float、兩欄矩陣每欄一個、列向量當一欄），rtol {TOL:g}）一致；channel_power 全頻＝bandpower 全頻，"
              f"periodogram 全頻總功率＝mean|x|²（Parseval）；[500 3000] 的 channel_power {cp:.6f} 對 bandpower {B['bandpower_psd_real_onesided_500_3000']:.6f}"
              f"（整格 vs 比例計入的差異）")

    # 7) 錯誤：識別碼與英文訊息要和 MATLAB 一樣（10 組實測），加上沒有參考數值、依 MATLAB 訊息句型對應的錯誤
    sxr, fsr = pow_m["real_onesided"]
    calls = {"obw_P100": lambda: obw(pxr, fxr, 100), "obw_P0": lambda: obw(pxr, fxr, 0), "obw_Pneg": lambda: obw(pxr, fxr, -5),
             "obw_range_out_of_bounds": lambda: obw(pxr, fxr, 99, (-10, 3000)), "obw_range_decreasing": lambda: obw(pxr, fxr, 99, (3000, 500)),
             "obw_range_equal": lambda: obw(pxr, fxr, 99, (1000, 1000)), "obw_extra_arg": lambda: obw(pxr, fxr, 99, None, 1),
             "obw_negative_psd": lambda: obw(-pxr, fxr), "obw_rbw_too_small": lambda: obw(sxr, fsr, 99, None, rbw=1),
             "obw_time_range_out": lambda: obw_time(xr, fs, 99, (0, 6000))}
    bad = []
    for case in R["errors"]:
        try:
            calls[case["name"]]()
            bad.append(f"{case['name']}: 沒丟錯誤")
        except ChannelMeasureError as e:
            if e.identifier != case["id"] or str(e) != case["message"] or not e.zh:
                bad.append(f"{case['name']}: got {e.identifier!r} {str(e)!r} ref {case['id']!r} {case['message']!r}")
    # 識別碼與訊息由 MATLAB obw／powerbw／bandpower 參數檢查的 validateattributes 屬性順序與訊息句型決定；MATLAB 識別碼的這幾組
    # 多數也在 7b 用 ref_obw_r3 的實測值再比一次，DSV 識別碼（dsv:chmeas:*）是 DSV 自己的 API 檢查與分派差異
    f5 = np.arange(5) * 10.0
    p5 = np.array([1.0, 2.0, 5.0, 2.0, 1.0])
    big = {"shape": (1 << 12, (1 << 12) + 1)}                              # 2^24 + 4096 個元素：不配置、只做 shape 的假物件不行，用 broadcast 檢視
    pbig = np.broadcast_to(np.float64(1.0), big["shape"])                   # 零拷貝的 2^24+ 元素檢視
    derived = [
        # 分派差異（MATLAB 用同樣的引數會改走別的形式；MATLAB 那一邊的結果在 7b 用 ref_obw_r3 驗證）→ DSV 自己的識別碼
        ("obw 單一元素頻率格（分派）", lambda: obw([1.0], [0.0]), "dsv:chmeas:FTooShort",
         "F must contain at least two frequencies (MATLAB would read an empty or scalar second argument as the sample rate Fs and use "
         "the time-domain form; call obw_time for that)."),
        ("channel_measure 單一元素頻率格（分派）", lambda: channel_measure([1.0], [0.0]), "dsv:chmeas:FTooShort", None),
        ("powerbw 單一元素頻率格（分派）", lambda: powerbw([1.0], [0.0]), "dsv:chmeas:FTooShort", None),
        ("measure_welch 單一元素頻率格（分派）", lambda: measure_welch({"psd": [1.0], "f": [0.0]}), "dsv:chmeas:FTooShort", None),
        ("periodogram_psd 空訊號", lambda: periodogram_psd([], 1e4), "MATLAB:periodogram:expectedNonempty", "Expected X to be nonempty."),
        ("periodogram_psd 空矩陣", lambda: periodogram_psd(np.zeros((0, 2)), 1e4), "MATLAB:periodogram:expectedNonempty", None),
        ("obw P 不是純量", lambda: obw(pxr, fxr, [90, 99]), "MATLAB:obw:expectedScalar", "Expected P to be a scalar."),
        ("obw P 空", lambda: obw(pxr, fxr, []), "MATLAB:obw:expectedNonempty", "Expected P to be nonempty."),
        ("obw P 字串", lambda: obw(pxr, fxr, "99"), "MATLAB:obw:invalidType",
         "Expected P to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64"),
        ("obw 範圍三個元素", lambda: obw(pxr, fxr, 99, (0, 1000, 2000)), "MATLAB:obw:incorrectSize",
         "Expected input number 3, FREQRANGE, to be of size 1x2, but it is of size 1x3."),
        ("obw 範圍含 NaN", lambda: obw(pxr, fxr, 99, (float("nan"), 1)), "MATLAB:obw:expectedFinite", None),
        ("obw 範圍單一數值（PSD 形式，分派）", lambda: obw(pxr, fxr, 99, 1000.0), "dsv:chmeas:FreqRangeScalar",
         "freqrange must have two elements (MATLAB would read a scalar third argument as RBW and use the power-spectrum form)."),
        ("powerbw 範圍單一數值（PSD 形式，分派）", lambda: powerbw(pxr, fxr, 3, [1000.0]), "dsv:chmeas:FreqRangeScalar", None),
        ("obw 範圍單一數值（功率譜形式）", lambda: obw(sxr, fsr, 99, [1000.0], rbw=float(W["rbw"])), "MATLAB:obw:incorrectSize",
         "Expected input number 3, FREQRANGE, to be of size 1x2, but it is of size 1x1."),
        ("obw_time 範圍單一數值（時域形式不帶編號）", lambda: obw_time(xr, fs, 99, [1000.0]), "MATLAB:obw:incorrectSize",
         "Expected FREQRANGE to be of size 1x2, but it is of size 1x1."),
        ("obw F 長度不符", lambda: obw(pxr, fxr[:-1]), "signal:psdparserange:FreqVectorMismatch", None),
        ("obw F 空（分派）", lambda: obw(pxr, []), "dsv:chmeas:FTooShort", None),
        ("obw F 是 ''（分派：MATLAB 的 isempty）", lambda: obw(pxr, ""), "dsv:chmeas:FTooShort", None),
        ("obw F 是矩陣", lambda: obw(p5, np.zeros((5, 2))), "MATLAB:obw:expectedVector", "Expected input number 2, F, to be a vector."),
        ("obw F 字串（PSD 形式的 F 只收 double/single）", lambda: obw(pxr, "abc"), "MATLAB:obw:invalidType",
         "Expected input number 2, F, to be one of these types:\n\ndouble, single"),
        ("obw F 字串（功率譜形式也是）", lambda: obw(sxr, "abc", 99, None, rbw=float(W["rbw"])), "MATLAB:obw:invalidType",
         "Expected input number 2, F, to be one of these types:\n\ndouble, single"),
        ("powerbw F 字串", lambda: powerbw(pxr, "abc"), "MATLAB:powerbw:invalidType",
         "Expected input number 2, F, to be one of these types:\n\ndouble, single"),
        ("obw F bool", lambda: obw(pxr, np.ones(pxr.size, dtype=bool)), "MATLAB:obw:invalidType",
         "Expected input number 2, F, to be one of these types:\n\ndouble, single\n\nInstead its type was logical."),
        ("obw_time X 字串", lambda: obw_time("abc", fs), "MATLAB:obw:invalidType",
         "Expected input number 1, X, to be one of these types:\n\ndouble, single"),
        ("powerbw_time X 字串（識別碼用 powerbw）", lambda: powerbw_time("abc", fs), "MATLAB:powerbw:invalidType",
         "Expected input number 1, X, to be one of these types:\n\ndouble, single"),
        ("powerbw_time Fs 3 個字元（分派：MATLAB 當 F）", lambda: powerbw_time(xr, "abc"), "dsv:chmeas:FsNotScalar",
         "fs must be empty or a scalar (MATLAB would read a non-scalar second argument as the frequency vector F and use the PSD form; "
         "call powerbw() for that)."),
        ("powerbw_time Fs 1 個字元（numeric 清單、char 不印 Instead）", lambda: powerbw_time(xr, "a"), "MATLAB:powerbw:invalidType",
         "Expected input number 2, Fs, to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64"),
        ("powerbw_time Fs 負值", lambda: powerbw_time(xr, -1.0), "MATLAB:powerbw:expectedPositive", "Expected input number 2, Fs, to be positive."),
        ("powerbw_time X 含 Inf", lambda: powerbw_time(np.array([1.0, float("inf")]), fs), "MATLAB:powerbw:expectedFinite",
         "Expected input number 1, X, to be finite."),
        ("obw_time Fs 非純量（分派：MATLAB 當 F）", lambda: obw_time(xr, [1e4, 2e4]), "dsv:chmeas:FsNotScalar", None),
        ("periodogram_psd Fs 非純量（分派）", lambda: periodogram_psd(xr, np.array([[1e4, 2e4]])), "dsv:chmeas:FsNotScalar", None),
        ("obw_time Fs 複數", lambda: obw_time(xr, 1e4 + 1j), "MATLAB:obw:expectedReal", "Expected input number 2, Fs, to be real."),
        ("mean_square 字串（MATLAB bandpower 的字串引數檢查）", lambda: mean_square("abc"), "signal:bandpower:IncorrectStringPsd",
         "Unrecognized input option. 'psd' is the only supported input option."),
        ("mean_square numpy 字串陣列", lambda: mean_square(np.array(["a", "b"])), "signal:bandpower:IncorrectStringPsd", None),
        ("mean_square bytes 'PSD'", lambda: mean_square(b"PSD"), "signal:bandpower:FreqVectorMissing", None),
        ("mean_square 含 Inf", lambda: mean_square([1.0, float("inf")]), "MATLAB:bandpower:expectedFinite", "Expected input number 1, X, to be finite."),
        ("mean_square 三維", lambda: mean_square(np.zeros((2, 2, 2))), "MATLAB:bandpower:expected2D", "Expected input number 1, X, to be two-dimensional."),
        ("mean_square 超過 2^24 個元素（DSV 防護）", lambda: mean_square(pbig), "dsv:chmeas:TooLarge", None),
        ("scope_band mode 打錯", lambda: scope_band("foo"), "dsv:chmeas:InvalidMode", None),
        ("measure_welch 缺鍵", lambda: measure_welch({}), "dsv:chmeas:MissingKey", None),
        ("measure_welch 缺 rbw（kind power）", lambda: measure_welch({"power": pxr, "f": fxr}, kind="power"), "dsv:chmeas:MissingKey", None),
        ("scope_measure_welch 缺 rbw", lambda: scope_measure_welch({"power": pxr, "f": fxr}), "dsv:chmeas:MissingKey", None),
        ("scope_measure_welch 不是 dict", lambda: scope_measure_welch(None), "dsv:chmeas:MissingKey", None),
        ("scope_auto_span 顛倒", lambda: scope_auto_span(5000.0, 0.0), "dsv:chmeas:StartStopOrder", None),
        ("scope_auto_span 相等", lambda: scope_auto_span(1.0, 1.0), "dsv:chmeas:StartStopOrder", None),
        ("scope_auto_span NaN", lambda: scope_auto_span(float("nan"), 1.0), _UI_IDS["start"], UI_MESSAGES["start"][0]),
        ("scope_auto_span stop Inf", lambda: scope_auto_span(0.0, float("inf")), _UI_IDS["stop"], None),
        # 參差不齊的巢狀序列：numpy 2 的 np.asarray 丟 ValueError，這裡當 MATLAB 的 cell → invalidType（cell），不讓 numpy 的錯漏出去
        ("obw F 參差不齊（當 cell）", lambda: obw(pxr, [0, [1, 2]]), "MATLAB:obw:invalidType",
         "Expected input number 2, F, to be one of these types:\n\ndouble, single\n\nInstead its type was cell."),
        ("obw Pxx 參差不齊", lambda: obw([1, [2, 3]], fxr), "MATLAB:obw:invalidType",
         "Expected input number 1, Pxx, to be one of these types:\n\ndouble, single\n\nInstead its type was cell."),
        ("obw 範圍參差不齊", lambda: obw(pxr, fxr, 99, [0, [1]]), "MATLAB:obw:invalidType",
         "Expected input number 3, FREQRANGE, to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64\n\nInstead its type was cell."),
        ("obw P 參差不齊", lambda: obw(pxr, fxr, [99, [1]]), "MATLAB:obw:invalidType", None),
        ("obw_time X 參差不齊", lambda: obw_time([1, [2]], fs), "MATLAB:obw:invalidType", None),
        ("obw_time Fs 參差不齊（2 個元素的 cell，分派：MATLAB 當 F）", lambda: obw_time(xr, [1, [2]]), "dsv:chmeas:FsNotScalar", None),
        ("obw_time Fs 是 1 個元素的 cell", lambda: obw_time(xr, np.array([None], dtype=object)), "MATLAB:obw:invalidType",
         "Expected input number 2, Fs, to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64\n\nInstead its type was cell."),
        ("powerbw 範圍參差不齊", lambda: powerbw(pxr, fxr, 3, [0, [1]]), "MATLAB:powerbw:invalidType", None),
        ("powerbw_time 範圍參差不齊", lambda: powerbw_time(xr, fs, 3, [0, [1]]), "MATLAB:powerbw:invalidType",
         "Expected FREQRANGE to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64\n\nInstead its type was cell."),
        ("bandpower F 參差不齊", lambda: bandpower(p5, [0, [1]]), "MATLAB:bandpower:invalidType", None),
        ("mean_square 參差不齊", lambda: mean_square([1, [2]]), "MATLAB:bandpower:invalidType", None),
        ("scope trace 參差不齊", lambda: scope_channel_measure([1, [2]], [0.0, 1.0], 1.0, 0, 1), "dsv:chmeas:invalidType", None),
        ("scope 頻率格參差不齊", lambda: scope_channel_measure([1.0, 2.0], [0, [1]], 1.0, 0, 1), "dsv:chmeas:invalidType", None),
        ("to_dbm 字串", lambda: to_dbm("abc"), "dsv:chmeas:invalidType", None),
        ("to_dbm 複數", lambda: to_dbm(1 + 1j), "dsv:chmeas:expectedReal", None),
        ("obw Pxx 三維", lambda: obw(np.zeros((4, 2, 2)), fxr[:4]), "MATLAB:obw:expected2D", "Expected input number 1, Pxx, to be two-dimensional."),
        ("obw Pxx 字串", lambda: obw("1 2 3", fxr[:3]), "MATLAB:obw:invalidType",
         "Expected input number 1, Pxx, to be one of these types:\n\ndouble, single"),
        ("obw Pxx 複數", lambda: obw(pxr.astype(complex), fxr), "MATLAB:obw:expectedReal", "Expected input number 1, Pxx, to be real."),
        ("obw RBW 不是純量（分派：MATLAB 當 FREQRANGE）", lambda: obw(p5, f5, 99, None, rbw=[20, 30]), "dsv:chmeas:RBWNotScalar",
         "rbw must be a scalar (MATLAB would read a non-scalar third argument as FREQRANGE and use the PSD form)."),
        ("obw RBW 含 Inf 的向量（分派）", lambda: obw(p5, f5, 99, None, rbw=[20, float("inf")]), "dsv:chmeas:RBWNotScalar", None),
        ("powerbw RBW 空（分派）", lambda: powerbw(p5, f5, rbw=[]), "dsv:chmeas:RBWNotScalar", None),
        ("obw Pxx 超過 2^24 個元素（DSV 防護）", lambda: obw(pbig, np.arange(1 << 12) * 1.0), "dsv:chmeas:TooLarge", None),
        ("periodogram_psd 超過 2^24 個樣本（DSV 防護）", lambda: periodogram_psd(pbig, 1e4), "dsv:chmeas:TooLarge", None),
        ("powerbw R＝0（識別碼大寫 Z）", lambda: powerbw(pxr, fxr, 0), "MATLAB:powerbw:expectedNonZero", "Expected R to be nonzero."),
        ("powerbw R 不是純量", lambda: powerbw(pxr, fxr, [3, 6]), "MATLAB:powerbw:expectedScalar", "Expected R to be a scalar."),
        ("powerbw 多餘引數", lambda: powerbw(pxr, fxr, 3, None, 1), "signal:powerbw:UnrecognizedAdditionalArguments", None),
        ("powerbw_time 多餘引數", lambda: powerbw_time(xr, fs, 3, None, 1), "signal:powerbw:UnrecognizedAdditionalArguments", None),
        ("bandpower 範圍超出", lambda: bandpower(pxr, fxr, (0, 6000)), "signal:bandpower:FreqRangeOutOfBounds", None),
        ("bandpower Pxx 含 Inf（finite 在 real 之前）", lambda: bandpower([1, 2, float("inf"), 2, 1], f5), "MATLAB:bandpower:expectedFinite",
         "Expected input number 1, Pxx, to be finite."),
        ("bandpower Pxx 含 NaN", lambda: bandpower([1, 2, float("nan"), 2, 1], f5), "MATLAB:bandpower:expectedFinite", None),
        ("bandpower Pxx 複數", lambda: bandpower(p5.astype(complex), f5), "MATLAB:bandpower:expectedReal", None),
        ("bandpower F 遞減", lambda: bandpower(p5, f5[::-1]), "MATLAB:bandpower:expectedIncreasing",
         "Expected input number 2, F, to be strictly increasing."),
        ("bandpower F 長度不符（incorrectNumel）", lambda: bandpower(p5, f5[:-1]), "MATLAB:bandpower:incorrectNumel",
         "Expected input number 2, F, to be an array with number of elements equal to 5."),
        ("bandpower F 空", lambda: bandpower(p5, []), "MATLAB:bandpower:expectedVector", None),
        ("bandpower 範圍三個元素（numel 2）", lambda: bandpower(p5, f5, (0, 10, 20)), "MATLAB:bandpower:incorrectNumel",
         "Expected input number 3, FREQRANGE, to be an array with number of elements equal to 2."),
        ("bandpower 範圍相等（increasing）", lambda: bandpower(p5, f5, (10, 10)), "MATLAB:bandpower:expectedIncreasing", None),
        ("bandpower 範圍空（vector）", lambda: bandpower(p5, f5, []), "MATLAB:bandpower:expectedVector", None),
        ("measure_welch kind 打錯", lambda: measure_welch(wr, kind="bogus"), "dsv:chmeas:InvalidKind", None),
        ("scope_measure_welch kind 打錯", lambda: scope_measure_welch(wr, kind="max"), "dsv:chmeas:InvalidKind", None),
        # DSV 自己的引數（MATLAB 沒有）：channel_measure／frequency_error 的 center、powerbw 的 time_len、公開輔助函式的輸入
        ("channel_measure center 非純量", lambda: channel_measure(pxr, fxr, center=[0, 1]), _UI_IDS["center"], UI_MESSAGES["center"][0]),
        ("channel_measure center 字串", lambda: channel_measure(pxr, fxr, center="0"), _UI_IDS["center"], None),
        ("channel_measure center NaN", lambda: channel_measure(pxr, fxr, center=float("nan")), _UI_IDS["center"], None),
        ("channel_measure center Inf", lambda: channel_measure(pxr, fxr, center=float("inf")), _UI_IDS["center"], None),
        ("channel_measure center 複數", lambda: channel_measure(pxr, fxr, center=1j), _UI_IDS["center"], None),
        ("channel_measure center bool", lambda: channel_measure(pxr, fxr, center=True), _UI_IDS["center"], None),
        ("measure_welch center 字串", lambda: measure_welch(wr, center="1250"), _UI_IDS["center"], None),
        ("frequency_error center 字串", lambda: frequency_error(1.0, 2.0, "0"), _UI_IDS["center"], UI_MESSAGES["center"][0]),
        ("frequency_error center 非純量", lambda: frequency_error(1.0, 2.0, [0, 1]), _UI_IDS["center"], None),
        ("frequency_error flo 字串", lambda: frequency_error("1", 2.0), "dsv:chmeas:invalidType",
         "Expected flo to be one of these types:\n\ndouble, single"),
        ("frequency_error fhi 複數", lambda: frequency_error(1.0, 2.0 + 1j), "dsv:chmeas:expectedReal", "Expected fhi to be real."),
        ("frequency_error 形狀不符", lambda: frequency_error([1.0, 2.0], [1.0, 2.0, 3.0]), "dsv:chmeas:ShapeMismatch",
         "flo and fhi must have the same shape, got (2,) and (3,)."),
        ("powerbw time_len 字串", lambda: powerbw(p5, f5, time_len="abc"), "dsv:chmeas:InvalidTimeLen",
         "time_len must be None or a nonnegative integer scalar (the original signal length), got 'abc'."),
        ("powerbw time_len 非純量", lambda: powerbw(p5, f5, time_len=[1, 2]), "dsv:chmeas:InvalidTimeLen", None),
        ("powerbw time_len NaN", lambda: powerbw(p5, f5, time_len=float("nan")), "dsv:chmeas:InvalidTimeLen", None),
        ("powerbw time_len 負", lambda: powerbw(p5, f5, time_len=-1), "dsv:chmeas:InvalidTimeLen", None),
        ("powerbw time_len 非整數", lambda: powerbw(p5, f5, time_len=2.5), "dsv:chmeas:InvalidTimeLen", None),
        ("powerbw time_len bool", lambda: powerbw(p5, f5, time_len=True), "dsv:chmeas:InvalidTimeLen", None),
        ("bin_widths 字串", lambda: bin_widths("abc"), "dsv:chmeas:invalidType",
         "Expected the frequency grid to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64"),
        ("bin_widths bool", lambda: bin_widths([True, False]), "dsv:chmeas:invalidType",
         "Expected the frequency grid to be one of these types:\n\ndouble, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64\n\nInstead its type was logical."),
        ("bin_widths 複數", lambda: bin_widths([0.0, 1j]), "dsv:chmeas:expectedReal", "Expected the frequency grid to be real."),
        ("bin_widths 參差不齊", lambda: bin_widths([0, [1]]), "dsv:chmeas:invalidType", None),
        ("cumulative_power 字串", lambda: cumulative_power("abc", f5), "dsv:chmeas:invalidType",
         "Expected the spectrum to be one of these types:\n\ndouble, single"),
        ("cumulative_power 複數", lambda: cumulative_power(p5.astype(complex), f5), "dsv:chmeas:expectedReal", None),
        ("cumulative_power 三維", lambda: cumulative_power(np.zeros((5, 1, 1)), f5), "dsv:chmeas:expected2D", None),
        ("cumulative_power 長度不符（DSV 輔助函式）", lambda: cumulative_power(p5, f5[:-1]), "dsv:chmeas:FreqVectorMismatch", None),
        ("cumulative_power 格字串", lambda: cumulative_power(p5, "abc"), "dsv:chmeas:invalidType", None),
        ("powerbw_time 零通道矩陣（N×0 也是 isempty）", lambda: powerbw_time(np.zeros((5, 0)), fs), "MATLAB:periodogram:expectedNonempty", None),
        ("obw_time 零通道矩陣", lambda: obw_time(np.zeros((5, 0)), fs), "MATLAB:periodogram:expectedNonempty", None),
        ("cumulative_power 空的格", lambda: cumulative_power([], []), "dsv:chmeas:expectedVector", "Expected the frequency grid to be a vector."),
        ("cumulative_power 格是矩陣", lambda: cumulative_power(np.zeros((4, 2)), np.zeros((2, 2))), "dsv:chmeas:expectedVector", None),
        ("bin_widths 格是矩陣", lambda: bin_widths(np.zeros((2, 2))), "dsv:chmeas:expectedVector", None),
        ("measure_welch 給陣列不是 dict", lambda: measure_welch(pxr), "dsv:chmeas:MissingKey", None),
        ("scope_measure_welch 給 numpy 純量", lambda: scope_measure_welch(np.float32(99)), "dsv:chmeas:MissingKey", None),
        ("scope_measure_welch 給字串", lambda: scope_measure_welch("psd"), "dsv:chmeas:MissingKey", None),
        ("scope_band mode 是陣列", lambda: scope_band(p5), "dsv:chmeas:InvalidMode", None),
        ("scope_channel_measure kind 是陣列", lambda: scope_channel_measure(p5, f5, 10.0, 0, 40, kind=p5), "dsv:chmeas:InvalidKind", None),
        # periodogram_psd 的 func 只能是 'obw'／'powerbw'（放進 MATLAB 識別碼的函式名；別的字串、數字、陣列都不能混進識別碼）
        ("periodogram_psd func 別的字串", lambda: periodogram_psd(xr, fs, "bandpower"), "dsv:chmeas:InvalidFunc",
         "func must be 'obw' or 'powerbw' (the MATLAB function whose name goes into the error identifiers), got 'bandpower'."),
        ("periodogram_psd func 數字", lambda: periodogram_psd(xr, fs, 5), "dsv:chmeas:InvalidFunc", None),
        ("periodogram_psd func 陣列", lambda: periodogram_psd(xr, fs, p5), "dsv:chmeas:InvalidFunc", None),
        ("periodogram_psd func 空字串", lambda: periodogram_psd(xr, fs, ""), "dsv:chmeas:InvalidFunc", None),
    ]
    for label, fn, ident, msg in derived:
        try:
            fn()
            bad.append(f"{label}: 沒丟錯誤")
        except ChannelMeasureError as e:
            if e.identifier != ident or (msg is not None and str(e) != msg) or not e.zh:
                bad.append(f"{label}: got {e.identifier!r} {str(e)!r} want {ident!r} {msg!r}")
        except Exception as e:                                         # noqa: BLE001 —— 要抓的就是「不是 ChannelMeasureError」
            bad.append(f"{label}: 丟了 {type(e).__name__}: {e}")
    # bandpower 和 obw／powerbw 的參數檢查不同：負的 PSD 可以
    try:
        if bandpower(-p5, f5) != -bandpower(p5, f5):
            bad.append("bandpower 負的 PSD 應該算出負的功率")
    except Exception as e:                                             # noqa: BLE001
        bad.append(f"bandpower 負的 PSD 不該丟錯：{type(e).__name__}: {e}")
    check(not bad, f"錯誤 vs MATLAB（{len(R['errors'])} 組實測：P＝100／0／−5、範圍超出／遞減／相等、多餘引數、負的 PSD、RBW 太小、時域範圍超出）："
                   f"識別碼與英文訊息一致、附繁體中文；另 {len(derived)} 組依 MATLAB 的定義與第三輪實測的句型對應：分派差異改丟 DSV 識別碼（F 空／''／單一元素、"
                   f"rbw 非單一數值／空、PSD 形式的單一數值範圍、fs 兩個以上元素）、"
                   f"空訊號、P 非純量／空／字串（numeric 清單、char 不印 Instead）、範圍 1×3／NaN／單一數值（功率譜／時域兩種訊息）、F 長度不符／矩陣／字串（類別列"
                   f"「double, single」，PSD 與功率譜形式、powerbw）／bool、Pxx 三維／字串／複數、時域 X 字串／Inf 與 Fs 1 個字元／負值／複數"
                   f"（powerbw_time 帶 MATLAB:powerbw:*）、RBW 複數、2^24 元素防護（obw／periodogram／mean_square）、"
                   f"powerbw R＝0（expectedNonZero）／非純量／多餘引數、bandpower 照 MATLAB 的 bandpower（finite 先於 real、F increasing／incorrectNumel／空、範圍 numel 2／相等／空、"
                   f"負 PSD 可以）、mean_square 照 MATLAB 的 bandpower（字串 → IncorrectStringPsd、'PSD' → FreqVectorMissing、Inf／三維）、kind 打錯、scope_band mode 打錯、welch dict 缺鍵、"
                   f"scope_auto_span 顛倒／相等／NaN／Inf、參差不齊的巢狀序列當 cell（Pxx／F／範圍／P／X／Fs／trace／格，numpy 的 ValueError 不漏出）、"
                   f"to_dbm 字串／複數、DSV 自己的引數（channel_measure／measure_welch／frequency_error 的 center 非純量／字串／NaN／Inf／複數／bool → "
                   f"工具列 center 訊息、frequency_error 的 flo／fhi 字串／複數／形狀不符、powerbw 的 time_len 字串／非純量／NaN／負／非整數／bool、"
                   f"bin_widths／cumulative_power 字串／複數／三維／長度不符／參差不齊／空格／矩陣格、N×0 零通道時域矩陣、welch dict 給陣列／純量／字串、"
                   f"mode／kind 給陣列（None＝預設值，見 7d））" + (f"（不一致：{bad}）" if bad else ""))

    # 7b) 第三輪實測（tests/matlab_ref/obw_chpower/ref_obw_r3.json，ref_obw_r3.m 產生）：每一筆 MATLAB 呼叫都對到一個 Python 呼叫，
    #     數值逐筆比（rtol TOL，NaN／±Inf 要完全相同、輸出元素數要相同）、錯誤比識別碼與英文訊息；沒有 Python 對應的列在 no_python，
    #     而且要求 JSON 每一筆都被用到（不會有漏比的）。分派差異另外列在 dispatch：Python 這個呼叫丟 DSV 識別碼，
    #     MATLAB 同樣引數的結果由「它實際走的那種形式」的 Python 呼叫重現。
    r3_path = os.path.join(d, "ref_obw_r3.json")
    if not os.path.isfile(r3_path):
        check(False, f"找不到 {r3_path}")
    else:
        R3 = {c["name"]: c for c in json.load(open(r3_path, encoding="utf-8"))["cases"]}
        pn = np.array([1.0, np.nan, 5.0, 2.0, 1.0])
        fh = np.array([-1e308, -5e307, 0.0, 5e307, 1e308])
        col = lambda v: np.asarray(v, dtype=float).reshape(-1, 1)          # noqa: E731 —— MATLAB 的行向量
        two_pi_single = float(np.float32(2 * math.pi))
        same = {
            "obw_1sample_vec": lambda: obw_time([1.0], 1e4), "obw_1sample_scalar": lambda: obw_time(3.0, 1e4),
            "obw_1sample_nofs": lambda: obw_time(3.0), "powerbw_1sample": lambda: powerbw_time(3.0, 1e4),
            "powerbw_1sample_vec": lambda: powerbw_time([1.0], 1e4), "obw_1sample_badrange": lambda: obw_time(3.0, 1e4, 99, (0, 6000)),
            "obw_2sample_col": lambda: obw_time(col([1, 2]), 1e4), "obw_2sample_row": lambda: obw_time([1.0, 2.0], 1e4),
            "powerbw_2sample_col": lambda: powerbw_time(col([1, 2]), 1e4), "obw_3sample_row": lambda: obw_time([1.0, 3.0, 2.0], 1e4),
            "obw_3sample_col": lambda: obw_time(col([1, 3, 2]), 1e4),
            "obw_empty_00": lambda: obw_time(np.zeros((0, 0)), 1e4), "obw_empty_01": lambda: obw_time(np.zeros((0, 1)), 1e4),
            "obw_empty_10": lambda: obw_time(np.zeros((1, 0)), 1e4), "obw_empty_50": lambda: obw_time(np.zeros((5, 0)), 1e4),
            "powerbw_empty_00": lambda: powerbw_time(np.zeros((0, 0)), 1e4), "powerbw_empty_50": lambda: powerbw_time(np.zeros((5, 0)), 1e4),
            "obw_P_nan": lambda: obw(p5, f5, float("nan")), "obw_P_nan2": lambda: obw(p5, f5, [float("nan")] * 2),
            "obw_P_inf": lambda: obw(p5, f5, float("inf")), "powerbw_R_nan": lambda: powerbw(p5, f5, float("nan")),
            "powerbw_R_zero": lambda: powerbw(p5, f5, 0),
            "obw_pxx_nan": lambda: obw(pn, f5), "powerbw_pxx_nan": lambda: powerbw(pn, f5),
            "obw_pxx_nan_range": lambda: obw(pn, f5, 99, (10, 30)), "powerbw_pxx_nan_range": lambda: powerbw(pn, f5, None, (10, 30)),
            "powerbw_pxx_allnan": lambda: powerbw([np.nan] * 3, [0.0, 10.0, 20.0]),
            "powerbw_pxx_nanpeak": lambda: powerbw([1.0, 2.0, np.nan, 2.0, 1.0], f5),
            "powerbw_pxx_nan_twocol": lambda: powerbw(np.column_stack([pn, p5]), f5),
            "obw_pxx_inf": lambda: obw([1.0, np.inf, 5.0, 2.0, 1.0], f5), "powerbw_pxx_inf": lambda: powerbw([1.0, np.inf, 5.0, 2.0, 1.0], f5),
            "obw_sxx_nan_rbw": lambda: obw(pn, f5, 99, None, rbw=10), "powerbw_huge_R1e4": lambda: powerbw(np.full(5, 1e308), f5, 1e4),
            "powerbw_time_huge_R1e4": lambda: powerbw_time(np.arange(5) * 1e300, 3.0, 1e4), "bandpower_pxx_nan": lambda: bandpower(pn, f5),
            "obw_P_char": lambda: obw(p5, f5, "99"), "obw_P_cell": lambda: obw(p5, f5, [99, [1]]),
            "obw_range_cell": lambda: obw(p5, f5, 99, [0, [1]]), "obw_F_char": lambda: obw(p5, "abc"),
            "obw_F_logical": lambda: obw(p5, np.ones(5, dtype=bool)), "obw_X_char": lambda: obw_time("abc", 1e4),
            "powerbw_Fs_char1": lambda: powerbw_time(xr, "a"), "powerbw_Fs_logical1": lambda: powerbw_time(xr, True),
            "powerbw_time_range_cell": lambda: powerbw_time(xr, fs, 3, [0, [1]]),
            "obw_time_range_scalar": lambda: obw_time(xr, fs, 99, 1000.0), "obw_power_range_scalar": lambda: obw(p5, f5, 99, 1000.0, rbw=10),
            "obw_rbw_complex": lambda: obw(p5, f5, 99, None, rbw=20 + 1j), "obw_Fs_complex": lambda: obw_time(xr, 1e4 + 1j),
            "powerbw_Fs_neg": lambda: powerbw_time(xr, -1.0), "bandpower_F_cell": lambda: bandpower(p5, [0, [1, 2]]),
            "bandpower_X_logical": lambda: mean_square(np.ones(3, dtype=bool)), "bandpower_range_cell": lambda: bandpower(p5, f5, [0, [10]]),
            "obw_fs_double_empty": lambda: obw_time(xr, []), "obw_fs_logical_empty": lambda: obw_time(xr, np.array([], dtype=bool)),
            "obw_fs_char_empty": lambda: obw_time(xr, ""), "obw_fs_single_empty": lambda: obw_time(xr, np.array([], dtype=np.float32)),
            "obw_fs_int8_empty": lambda: obw_time(xr, np.array([], dtype=np.int8)),
            "obw_fs_uint16_empty": lambda: obw_time(xr, np.array([], dtype=np.uint16)),
            "obw_fs_uint8_empty": lambda: obw_time(xr, np.array([], dtype=np.uint8)),
            "obw_fs_complex_empty": lambda: obw_time(xr, np.array([], dtype=complex)),
            "obw_fs_csingle_empty": lambda: obw_time(xr, np.array([], dtype=np.complex64)),
            "obw_fs_cell_empty": lambda: obw_time(xr, np.array([], dtype=object)),
            "obw_fs_datetime_empty": lambda: obw_time(xr, np.array([], dtype="datetime64[s]")),
            "obw_fs_duration_empty": lambda: obw_time(xr, np.array([], dtype="timedelta64[s]")),
            "obw_fs_half_empty": lambda: obw_time(xr, np.array([], dtype=np.float16)),
            "obw_fs_6": lambda: obw_time(xr, 6), "obw_fs_1": lambda: obw_time(xr, 1), "obw_fs_single2pi": lambda: obw_time(xr, two_pi_single),
            "powerbw_fs_logical_empty": lambda: powerbw_time(xr, np.array([], dtype=bool)), "powerbw_fs_char_empty": lambda: powerbw_time(xr, ""),
            "bandpower_char": lambda: mean_square("abc"), "bandpower_char_psd": lambda: mean_square("psd"),
            "bandpower_char_PSD": lambda: mean_square("PSD"), "bandpower_char_empty": lambda: mean_square(""),
            "bandpower_pxx_char": lambda: bandpower("abc", f5), "bandpower_F_char": lambda: bandpower(p5, "abc"),
            "bandpower_range_char": lambda: bandpower(p5, f5, "abc"), "bandpower_F_psd": lambda: bandpower(p5, "psd"),
            "bandpower_pxx_psd": lambda: bandpower("psd", f5), "bandpower_range_psd": lambda: bandpower(p5, f5, "psd"),
            "bandpower_empty_00": lambda: mean_square(np.zeros((0, 0))), "bandpower_empty_10": lambda: mean_square([]),
            "bandpower_empty_01": lambda: mean_square(np.zeros((0, 1))), "bandpower_empty_02": lambda: mean_square(np.zeros((0, 2))),
            "bandpower_empty_30": lambda: mean_square(np.zeros((3, 0))), "bandpower_scalar": lambda: mean_square(3.0),
            "obw_P_logical": lambda: obw(p5, f5, True), "obw_P_datetime": lambda: obw(p5, f5, np.datetime64("2026-01-01")),
            "obw_P_duration": lambda: obw(p5, f5, np.timedelta64(1, "s")), "obw_P_struct": lambda: obw(p5, f5, {"a": 1}),
            "obw_P_char1": lambda: obw(p5, f5, "a"), "obw_P_char_empty": lambda: obw(p5, f5, ""),
            "obw_power_F_char": lambda: obw(p5, "abc", 99, None, rbw=10), "obw_pxx_char": lambda: obw("1 2 3", [0.0, 10.0, 20.0]),
            "obw_range_char_empty": lambda: obw(p5, f5, 99, ""),
            "obw_rbw_fmt_inf": lambda: obw([1.0, 2.0, 1.0], [-1e308, 0.0, 1e308], 99, None, rbw=1),
            "obw_rbw_nan_df": lambda: obw([1.0, 2.0, 1.0], [1e308, -1e308, 1e308], 99, None, rbw=1),
            "bandpower_F_empty": lambda: bandpower(p5, []), "bandpower_range_empty": lambda: bandpower(p5, f5, []),
            "obw_rbw_inf": lambda: obw(p5, f5, 99, None, rbw=float("inf")), "obw_rbw_neg": lambda: obw(p5, f5, 99, None, rbw=-1),
            "obw_rbw_nan": lambda: obw(p5, f5, 99, None, rbw=float("nan")), "bandpower_one_bin": lambda: bandpower([1.0], [0.0]),
            "obw_zero_psd": lambda: obw(np.zeros(5), f5), "powerbw_zero_psd": lambda: powerbw(np.zeros(5), f5),
            "powerbw_zero_col": lambda: powerbw(np.column_stack([p5, np.zeros(5)]), f5),
            "powerbw_zero_in_range": lambda: powerbw([1.0, 0.0, 0.0, 0.0, 1.0], f5, None, (10, 30)),
            "obw_huge_psd": lambda: obw(np.full(5, 1e308), f5), "powerbw_huge_psd": lambda: powerbw(np.full(5, 1e308), f5),
            "bandpower_huge_psd": lambda: bandpower(np.full(5, 1e308), f5), "bandpower_huge_time": lambda: mean_square([1e308, 1e308]),
            "obw_huge_grid": lambda: obw(p5, fh), "powerbw_huge_grid": lambda: powerbw(p5, fh), "bandpower_huge_grid": lambda: bandpower(p5, fh),
            "obw_huge_grid_range": lambda: obw(p5, fh, 99, (-5e307, 5e307)),
            "obw_P_vector": lambda: obw(p5, f5, [90, 99]), "obw_P_empty": lambda: obw(p5, f5, []),
            "obw_range_3": lambda: obw(p5, f5, 99, (0, 10, 20)), "obw_range_nan": lambda: obw(p5, f5, 99, (float("nan"), 1)),
            "obw_F_short": lambda: obw(p5, f5[:-1]), "obw_F_matrix": lambda: obw(p5, np.zeros((5, 2))),
            "powerbw_F_char": lambda: powerbw(p5, "abc"), "powerbw_X_char": lambda: powerbw_time("abc", 1e4),
            "powerbw_X_inf": lambda: powerbw_time([1.0, np.inf], 1e4), "bandpower_X_inf": lambda: mean_square([1.0, np.inf]),
            "bandpower_X_3d": lambda: mean_square(np.zeros((2, 2, 2))), "obw_F_cell": lambda: obw(p5, [0, [1, 2]]),
            "obw_pxx_cell": lambda: obw([1, [2, 3]], f5), "obw_X_cell": lambda: obw_time([1, [2]], 1e4),
            "powerbw_range_cell": lambda: powerbw(p5, f5, 3, [0, [1]]), "bandpower_X_cell": lambda: mean_square([1, [2]]),
            "obw_pxx_3d": lambda: obw(np.zeros((4, 2, 2)), f5[:4]), "obw_pxx_complex": lambda: obw(p5.astype(complex), f5),
            "powerbw_R_vector": lambda: powerbw(p5, f5, [3, 6]), "powerbw_extra": lambda: powerbw(p5, f5, 3, None, 1),
            "powerbw_time_extra": lambda: powerbw_time(xr, fs, 3, None, 1), "bandpower_range_out": lambda: bandpower(p5, f5, (0, 60)),
            "bandpower_pxx_inf": lambda: bandpower([1.0, 2.0, np.inf, 2.0, 1.0], f5),
            "bandpower_pxx_complex": lambda: bandpower(p5.astype(complex), f5), "bandpower_F_decreasing": lambda: bandpower(p5, f5[::-1]),
            "bandpower_F_short": lambda: bandpower(p5, f5[:-1]), "bandpower_range_3": lambda: bandpower(p5, f5, (0, 10, 20)),
            "bandpower_range_equal": lambda: bandpower(p5, f5, (10, 10)),
            "obw_Fs_cell1": lambda: obw_time(xr, np.array([None], dtype=object)),
            "bandpower_neg_psd": lambda: bandpower(-p5, f5), "bandpower_pos_psd": lambda: bandpower(p5, f5),
        }
        for k, dfk in enumerate([1 / 3, 1e5 / 3, 1e-7 / 3, 1e20 / 3, 123456789.123, 0.1, 2 / 3 * 1e-3], start=1):
            same[f"obw_rbw_fmt_{k}"] = (lambda dd: lambda: obw([1.0, 2.0, 1.0], np.arange(3) * dd, 99, None, rbw=dd / 2))(dfk)
        # 分派差異：(Python 呼叫, 它丟的 DSV 識別碼, MATLAB 實際走的形式在 Python 的寫法)
        dispatch = {
            "obw_fs_vector": (lambda: obw_time(xr, [1e4, 2e4]), "dsv:chmeas:FsNotScalar", lambda: obw(xr, [1e4, 2e4])),
            "powerbw_fs_char3": (lambda: powerbw_time(xr, "abc"), "dsv:chmeas:FsNotScalar", lambda: powerbw(xr, "abc")),
            "obw_fs_cell2": (lambda: obw_time(xr, [1, [2]]), "dsv:chmeas:FsNotScalar", lambda: obw(xr, [1, [2]])),
            "obw_pxx_F_empty": (lambda: obw(p5, []), "dsv:chmeas:FTooShort", lambda: obw_time(p5, [])),
            "obw_pxx_F_scalar": (lambda: obw(p5, 0.0), "dsv:chmeas:FTooShort", lambda: obw_time(p5, 0.0)),
            "obw_pxx_F_char1": (lambda: obw(p5, "a"), "dsv:chmeas:FTooShort", lambda: obw_time(p5, "a")),
            "obw_rbw_vector": (lambda: obw(p5, f5, 99, None, rbw=[20, 30]), "dsv:chmeas:RBWNotScalar", lambda: obw(p5, f5, 99, (20, 30))),
            "obw_rbw_empty": (lambda: obw(p5, f5, 99, None, rbw=[]), "dsv:chmeas:RBWNotScalar", lambda: obw(p5, f5, 99)),
            "obw_range_scalar_psd": (lambda: obw(p5, f5, 99, 1000.0), "dsv:chmeas:FreqRangeScalar", lambda: obw(p5, f5, freqrange=99, rbw=1000)),
        }
        no_python = {"obw_P_string": "MATLAB 的 string 類別（Python 的 str 是 char）",
                     "obw_fs_string_empty": "strings(0)：MATLAB 的 string 類別",
                     "obw_fs_struct_empty": "struct([])：Python 沒有空 struct 的對應"}

        def run(fn):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error")                     # numpy 警告也算失敗
                    out = fn()
                return True, (out if isinstance(out, tuple) else (out,)), None
            except ChannelMeasureError as e:
                return False, None, e
            except Exception as e:                                     # noqa: BLE001
                return False, None, e

        def matches(ref, fn):
            ok, out, err = run(fn)
            if not ref["ok"]:
                if ok:
                    return f"MATLAB 丟 {ref['id']}，DSV 算出 {out}"
                if not isinstance(err, ChannelMeasureError):
                    return f"丟了 {type(err).__name__}: {err}"
                if err.identifier != ref["id"] or str(err) != ref["message"] or not err.zh:
                    return f"got {err.identifier!r} {str(err)!r} ref {ref['id']!r} {ref['message']!r}"
                return None
            if not ok:
                return f"MATLAB 算出 {ref['vals']}，DSV 丟 {getattr(err, 'identifier', type(err).__name__)}: {err}"
            if len(out) != len(ref["vals"]):
                return f"輸出個數 {len(out)} ≠ {len(ref['vals'])}"
            for g, rv in zip(out, ref["vals"]):
                gv = np.atleast_1d(np.asarray(g, dtype=float)).ravel()
                r = np.array([float(t) for t in rv])
                if gv.size != r.size:
                    return f"元素數 {gv.size} ≠ {r.size}（{g!r} vs {rv}）"
                stats["n"] += r.size
                fin = np.isfinite(r)
                if not (np.array_equal(np.isnan(gv), np.isnan(r)) and np.array_equal(gv[np.isinf(r)], r[np.isinf(r)])
                        and np.array_equal(np.isinf(gv), np.isinf(r))):
                    return f"NaN／Inf 不同：{gv} vs {r}"
                rr, gg = r[fin], gv[fin]
                e = np.where(rr != 0, np.abs(gg - rr) / np.where(rr != 0, np.abs(rr), 1.0), np.abs(gg))
                if e.size:
                    stats["worst"] = max(stats["worst"], float(np.max(e)))
                if np.any(e > TOL):
                    return f"數值 {gv} vs {r}（相對差 {float(np.max(e)):.1e}）"
            return None

        bad3, n_val, n_err = [], 0, 0
        for nm, fn in same.items():
            ref = R3.get(nm)
            if ref is None:
                bad3.append(f"{nm}: JSON 沒有這一筆")
                continue
            n_val += ref["ok"]
            n_err += not ref["ok"]
            msg = matches(ref, fn)
            if msg:
                bad3.append(f"{nm}: {msg}")
        known = []
        for nm, (py, dsv_id, equiv) in dispatch.items():
            ref = R3[nm]
            ok, out, err = run(py)
            if ok or getattr(err, "identifier", None) != dsv_id or not getattr(err, "zh", ""):
                bad3.append(f"{nm}: Python 呼叫應丟 {dsv_id}，得到 {out if ok else err}")
            msg = matches(ref, equiv)
            if msg:
                bad3.append(f"{nm}（MATLAB 實際走的形式）: {msg}")
            known.append(f"{nm}→{dsv_id}（MATLAB：{ref['id'] if not ref['ok'] else '算出數值'}）")
        unused = sorted(set(R3) - set(same) - set(dispatch) - set(no_python))
        if unused:
            bad3.append(f"JSON 裡沒被比到的：{unused}")
        check(not bad3, f"第三輪 MATLAB 實測 vs DSV（ref_obw_r3.json {len(R3)} 筆：{n_val} 筆數值、{n_err} 筆錯誤逐筆一致，rtol {TOL:g}、NaN／Inf 完全相同、"
                        f"不印 numpy 警告）：1 個樣本的時域輸入丟 NDMatrixUnsupported（含 0-d、列／行向量、範圍超出時也先丟它）、2／3 個樣本可算、"
                        f"空的時域訊號（[]、0×1、1×0、5×0）丟 periodogram expectedNonempty、P＝NaN／Inf → notLess、[NaN NaN] → expectedScalar、"
                        f"R＝0 → expectedNonZero、Pxx 含 NaN 不擋（obw 全 NaN、powerbw 忽略 NaN 找峰值與 realmin 墊底，flo＝−0.0031469021983124373）、"
                        f"Inf 的 PSD、極大 PSD 與 1e308 級頻率格照 IEEE、invalidType 的 numeric 清單與「char 不印 Instead its type was」、"
                        f"logical／cell／datetime／duration／struct 的類別名、RBW 訊息的 %g 數字格式（0.333333…inf）與 NaN 間距的 badComparison、"
                        f"空的 fs 照類別 cast（logical 1、char 6、single／half／整數／複數，cell／datetime／duration 丟 cast:UnsupportedPrototype）、"
                        f"bandpower 的字串引數檢查（IncorrectStringPsd／FreqVectorMissing／'psd' 往下傳變 invalidType）與空輸入（[]、3×0 → 1×0；"
                        f"Python 的 1-D [] ＝ zeros(1,0) → NaN；0×2 → [NaN NaN]）；"
                        f"已知差異（分派，{len(dispatch)} 筆：Python 呼叫丟 DSV 識別碼、MATLAB 的結果由它實際走的形式重現）：{'；'.join(known)}；"
                        f"沒有 Python 對應而不比的 {len(no_python)} 筆：{'、'.join(f'{k}（{v}）' for k, v in no_python.items())}"
                        + (f"（不一致：{bad3}）" if bad3 else ""))

    # 7c) 第四輪實測（ref_obw_r4.json，ref_obw_r4.m 產生）：資料類別。
    #     same4＝MATLAB 和 DSV 應一致的（double 資料、single／整數／half 的純量引數）；
    #     single4＝已知差異 1：single 資料，DSV 放寬成 double 算 → 要等於 MATLAB 對 double(single 資料) 的 d_* 參考（rtol TOL），
    #       回傳 float64，且和 MATLAB single 結果的最大相對差（取 3 位有效數字）要剛好是模組說明寫的那個數；
    #     int4＝整數／half 資料：MATLAB 丟 invalidType（識別碼與完整英文訊息釘住），DSV 要丟一模一樣的；同一筆資料轉成 double 就能算。
    r4_path = os.path.join(d, "ref_obw_r4.json")
    if not (os.path.isfile(r4_path) and os.path.isfile(r3_path)):
        check(False, f"找不到 {r4_path}（或 ref_obw_r3.json）")
    else:
        R4 = {c["name"]: c for c in json.load(open(r4_path, encoding="utf-8"))["cases"]}
        s32, c64 = np.float32, np.complex64
        xs, xcs = xr.astype(s32), xc.astype(c64)
        P2 = np.column_stack([p5, 2 * p5 + 1])
        xi = np.round(1000 * xr)
        same4 = {
            "d_obw_psd": lambda: obw(p5, f5), "d_obw_P": lambda: obw(p5, f5, 90), "d_obw_range": lambda: obw(p5, f5, 99, (10, 30)),
            "d_obw_rbw": lambda: obw(p5, f5, 99, rbw=10), "d_obw_mat": lambda: obw(P2, f5),
            "d_obw_time": lambda: obw_time(xs.astype(float), 1e4), "d_obw_time_fs": lambda: obw_time(xr, 1e4),
            "d_obw_time_cplx": lambda: obw_time(xcs.astype(complex), 1e4), "d_pbw_psd": lambda: powerbw(p5, f5),
            "d_pbw_time": lambda: powerbw_time(xs.astype(float), 1e4), "d_pbw_R": lambda: powerbw(p5, f5, 3),
            "d_bp_psd": lambda: bandpower(p5, f5), "d_bp_psd_range": lambda: bandpower(p5, f5, (5, 35)),
            "d_bp_time": lambda: mean_square(xs.astype(float)), "d_bp_time_cplx": lambda: mean_square(xcs.astype(complex)),
            "s_obw_P": lambda: obw(p5, f5, s32(90)), "s_obw_range": lambda: obw(p5, f5, 99, np.array([10, 30], s32)),
            "s_obw_rbw": lambda: obw(p5, f5, 99, rbw=s32(10)), "s_obw_time_fs": lambda: obw_time(xr, s32(1e4)),
            "s_pbw_R": lambda: powerbw(p5, f5, s32(3)),
            "s_obw_P_frac": lambda: obw(p5, f5, s32(99.9)), "d_obw_P_frac": lambda: obw(p5, f5, float(s32(99.9))),
            "s_obw_range_frac": lambda: obw(p5, f5, 99, np.array([10.1, 30.3], s32)),
            "d_obw_range_frac": lambda: obw(p5, f5, 99, np.array([10.1, 30.3], s32).astype(float)),
            "s_obw_fs_frac": lambda: obw_time(xr, s32(1e4 / 3)), "d_obw_fs_frac": lambda: obw_time(xr, float(s32(1e4 / 3))),
            "s_pbw_R_frac": lambda: powerbw(p5, f5, s32(2.7)), "d_pbw_R_frac": lambda: powerbw(p5, f5, float(s32(2.7))),
            "s_obw_rbw_frac": lambda: obw(p5, f5, 99, rbw=s32(10.3)), "d_obw_rbw_frac": lambda: obw(p5, f5, 99, rbw=float(s32(10.3))),
            "i_bp_f_int16": lambda: bandpower(p5, f5.astype(np.int16)),
            "i_bp_range_int16": lambda: bandpower(p5, f5, np.array([5, 35], np.int16)),
            "i_obw_P_int8": lambda: obw(p5, f5, np.int8(90)), "i_obw_range_int16": lambda: obw(p5, f5, 99, np.array([10, 30], np.int16)),
            "i_obw_rbw_int16": lambda: obw(p5, f5, 99, rbw=np.int16(10)), "i_obw_fs_int16": lambda: obw_time(xr, np.int16(10000)),
            "i_pbw_fs_int32": lambda: powerbw_time(xr, np.int32(10000)), "i_pbw_R_int8": lambda: powerbw(p5, f5, np.int8(3)),
            "i_pbw_range_int16": lambda: powerbw(p5, f5, 3, np.array([10, 30], np.int16)),
            "h_obw_P_half": lambda: obw(p5, f5, np.float16(90)), "h_obw_fs_half": lambda: obw_time(xr, np.float16(1e4)),
        }
        # (single 資料的呼叫, 同一筆資料放寬成 double 的呼叫, MATLAB double 參考, 模組說明寫的最大相對差)
        single4 = {
            "s_obw_psd": (lambda: obw(p5.astype(s32), f5.astype(s32)), lambda: obw(p5, f5), "d_obw_psd", "7.74e-08"),
            "s_obw_psd_pxxonly": (lambda: obw(p5.astype(s32), f5), lambda: obw(p5, f5), "d_obw_psd", "7.74e-08"),
            "s_obw_psd_fonly": (lambda: obw(p5, f5.astype(s32)), lambda: obw(p5, f5), "d_obw_psd", "7.74e-08"),
            "s_obw_mat": (lambda: obw(P2.astype(s32), f5.astype(s32)), lambda: obw(P2, f5), "d_obw_mat", "7.74e-08"),
            "s_obw_time": (lambda: obw_time(xs, 1e4), lambda: obw_time(xs.astype(float), 1e4), "d_obw_time", "1.87e-06"),
            "s_obw_time_cplx": (lambda: obw_time(xcs, 1e4), lambda: obw_time(xcs.astype(complex), 1e4), "d_obw_time_cplx", "1.76e-05"),
            "s_pbw_psd": (lambda: powerbw(p5.astype(s32), f5.astype(s32)), lambda: powerbw(p5, f5), "d_pbw_psd", "9.73e-08"),
            "s_pbw_time": (lambda: powerbw_time(xs, 1e4), lambda: powerbw_time(xs.astype(float), 1e4), "d_pbw_time", "7.05e-05"),
            "s_bp_psd": (lambda: bandpower(p5.astype(s32), f5.astype(s32)), lambda: bandpower(p5, f5), "d_bp_psd", "0.00e+00"),
            "s_bp_psd_range": (lambda: bandpower(p5.astype(s32), f5.astype(s32), (5, 35)), lambda: bandpower(p5, f5, (5, 35)),
                               "d_bp_psd_range", "0.00e+00"),
            "s_bp_time": (lambda: mean_square(xs), lambda: mean_square(xs.astype(float)), "d_bp_time", "1.12e-07"),
            "s_bp_time_cplx": (lambda: mean_square(xcs), lambda: mean_square(xcs.astype(complex)), "d_bp_time_cplx", "6.06e-08"),
        }
        # (整數／half 資料的呼叫, 同一筆資料轉成 double 的呼叫, MATLAB 的識別碼, 引數編號, 名稱, MATLAB 類別名)
        int4 = {
            "i_obw_pxx_int16": (lambda: obw(p5.astype(np.int16), f5), lambda: obw(p5, f5), "MATLAB:obw:invalidType", 1, "Pxx", "int16"),
            "i_obw_pxx_uint8": (lambda: obw(p5.astype(np.uint8), f5), lambda: obw(p5, f5), "MATLAB:obw:invalidType", 1, "Pxx", "uint8"),
            "i_obw_f_int16": (lambda: obw(p5, f5.astype(np.int16)), lambda: obw(p5, f5), "MATLAB:obw:invalidType", 2, "F", "int16"),
            "i_obw_x_int32": (lambda: obw_time(xi.astype(np.int32), 1e4), lambda: obw_time(xi, 1e4), "MATLAB:obw:invalidType", 1, "X", "int32"),
            "i_pbw_pxx_int8": (lambda: powerbw(p5.astype(np.int8), f5), lambda: powerbw(p5, f5), "MATLAB:powerbw:invalidType", 1, "Pxx", "int8"),
            "i_pbw_f_uint16": (lambda: powerbw(p5, f5.astype(np.uint16)), lambda: powerbw(p5, f5), "MATLAB:powerbw:invalidType", 2, "F", "uint16"),
            "i_pbw_x_int16": (lambda: powerbw_time(xi.astype(np.int16), 1e4), lambda: powerbw_time(xi, 1e4), "MATLAB:powerbw:invalidType",
                              1, "X", "int16"),
            "i_bp_pxx_int16": (lambda: bandpower(p5.astype(np.int16), f5), lambda: bandpower(p5, f5), "MATLAB:bandpower:invalidType",
                               1, "Pxx", "int16"),
            "i_bp_x_int16": (lambda: mean_square(xi.astype(np.int16)), lambda: mean_square(xi), "MATLAB:bandpower:invalidType", 1, "X", "int16"),
            "h_obw_pxx_half": (lambda: obw(p5.astype(np.float16), f5), lambda: obw(p5, f5), "MATLAB:obw:invalidType", 1, "Pxx", "half"),
        }
        bad4, worst4 = [], {}
        for nm, fn in same4.items():
            ref = R4.get(nm)
            msg = "JSON 沒有這一筆" if ref is None else matches(ref, fn)
            if msg:
                bad4.append(f"{nm}: {msg}")
        for nm, (fs32, fwide, dref, doc) in single4.items():
            ref, rd = R4.get(nm), R4.get(dref)
            if ref is None or rd is None or not ref["ok"] or not all(c == "single" for c in ref["classes"]):
                bad4.append(f"{nm}: JSON 缺這一筆或 MATLAB 沒回 single（{ref and ref.get('classes')}）")
                continue
            ok, out, err = run(fs32)
            ok2, out2, err2 = run(fwide)
            if not (ok and ok2):
                bad4.append(f"{nm}: 丟了 {err or err2}")
                continue
            if not all(np.array_equal(np.asarray(u), np.asarray(v)) for u, v in zip(out, out2)):
                bad4.append(f"{nm}: single 資料的結果 {out} 和放寬成 double 的 {out2} 不是位元級相同")
            if not all(isinstance(v, float) or (isinstance(v, np.ndarray) and v.dtype == np.float64) for v in out):
                bad4.append(f"{nm}: 回傳型別不是 float64：{[type(v).__name__ for v in out]}")
            msg = matches(rd, fs32)
            if msg:
                bad4.append(f"{nm} 對 {dref}: {msg}")
            g = np.concatenate([np.atleast_1d(np.asarray(v, dtype=float)).ravel() for v in out])
            r = np.array([float(t) for v in ref["vals"] for t in v])
            rel = float(np.max(np.abs(g - r) / np.abs(r)))
            worst4[nm] = rel
            if f"{rel:.2e}" != doc:
                bad4.append(f"{nm}: 和 MATLAB single 的最大相對差 {rel:.3e}，模組說明寫 {doc}")
        for nm, (fint, fdbl, mid, k, name, cls) in int4.items():
            ref = R4.get(nm)
            want = f"Expected input number {k}, {name}, to be one of these types:\n\ndouble, single\n\nInstead its type was {cls}."
            if ref is None or ref["ok"] or ref["id"] != mid or ref["message"] != want:
                bad4.append(f"{nm}: MATLAB 那一邊不是 {mid}「{want}」：{ref}")
            msg = matches(ref, fint) if ref is not None else "JSON 沒有這一筆"   # DSV 要丟同一個識別碼、同一段訊息
            if msg:
                bad4.append(f"{nm}: {msg}")
            ok2, out2, err2 = run(fdbl)
            if not ok2:
                bad4.append(f"{nm}: 同一筆資料轉成 double 應該能算：{err2}")
        unused4 = sorted(set(R4) - set(same4) - set(single4) - set(int4))
        if unused4:
            bad4.append(f"JSON 裡沒被比到的：{unused4}")
        check(not bad4, f"第四輪 MATLAB 實測（ref_obw_r4.json {len(R4)} 筆，資料類別）：{len(same4)} 筆一致（rtol {TOL:g}；double 資料，"
                        f"single／整數的純量引數 P、R、RBW、FREQRANGE、Fs、bandpower 的 F，以及 half 的 P 與 Fs——MATLAB 回 double、"
                        f"等於 double(該值) 的呼叫；half 的 FREQRANGE／R／bandpower F 是 half 錯，見 7f）；已知差異（single 資料，{len(single4)} 筆）：DSV 放寬成 double、回傳 float64、"
                        f"等於 MATLAB 的 d_* 參考，和 MATLAB single 結果的最大相對差 "
                        f"{'、'.join(f'{k} {v:.2e}' for k, v in worst4.items())}；整數／half 資料（{len(int4)} 筆：int16／uint8／int8／uint16／int32 的 "
                        f"Pxx、F、X 與 half 的 Pxx）：DSV 和 MATLAB 一樣丟 invalidType「Expected input number 1, Pxx, to be one of these types: "
                        f"double, single … Instead its type was int16.」（識別碼與完整訊息逐筆相同），同一筆資料轉成 double 就能算"
                        + (f"（不一致：{bad4}）" if bad4 else ""))

    # 7d) None＝沒給（Python 的 None 沒有 MATLAB 對應）：有預設值的引數 None＝預設值，和不給位元級相同（percent＝None 預設 99，和 powerbw 的
    #     R＝None 一致；MATLAB 的 [] 仍是 expectedNonempty，ref_obw_r3 obw_P_empty，7b 已比）；必要的陣列引數 None 丟 dsv:chmeas:MissingInput，
    #     不再冒稱 MATLAB 的 cell。
    bad = []
    none_worst = [0.0]

    def same(u, v):
        """dict／tuple 逐值比，NaN 對 NaN 算相同（scope 路徑預設頻帶 [−1000 1000] 在單邊格上是全 NaN）；數值用 TOL 比而不是位元級——
        經過 welch 的鏈（obw_time／powerbw_time／periodogram_psd）在 anaconda 的 numpy 1.26 上連跑不是位元級可重現（見第 2 項），
        其餘純 numpy 的對照實測差 0.0；最大相對差記在 none_worst。"""
        if isinstance(u, dict):
            return isinstance(v, dict) and u.keys() == v.keys() and all(same(u[k], v[k]) for k in u)
        if isinstance(u, (tuple, list)):
            return isinstance(v, (tuple, list)) and len(u) == len(v) and all(same(a, b) for a, b in zip(u, v))
        if isinstance(u, (int, float, np.ndarray, np.generic)) and isinstance(v, (int, float, np.ndarray, np.generic)):
            a, b = np.asarray(u, dtype=float), np.asarray(v, dtype=float)
            if a.shape != b.shape:
                return False
            both = ~np.isnan(a) & ~np.isnan(b)
            with np.errstate(invalid="ignore", divide="ignore"):
                e = np.where(b[both] != 0, np.abs(a[both] - b[both]) / np.abs(b[both]), np.where(a[both] == 0, 0.0, np.inf))
            if e.size:
                none_worst[0] = max(none_worst[0], float(np.max(e)))
            return bool(np.all(np.isnan(a) == np.isnan(b)) and np.all(e <= TOL))
        return u == v

    try:
        res_d = {"psd": pxr, "f": fxr, "power": pxr * float(W["rbw"]), "rbw": float(W["rbw"])}
        pairs = [(obw(p5, f5, None), obw(p5, f5)), (obw(p5, f5, None, (10, 30)), obw(p5, f5, 99, (10, 30))),
                 (obw(p5, f5, None, rbw=10), obw(p5, f5, rbw=10)), (obw_time(xr, fs, None), obw_time(xr, fs)),
                 (powerbw(p5, f5, None), powerbw(p5, f5)),
                 (obw(p5, f5, None, None, rbw=None), obw(p5, f5)), (obw_time(xr, None, None, None), obw_time(xr)),
                 (powerbw(p5, f5, None, None, rbw=None, time_len=None), powerbw(p5, f5)), (powerbw_time(xr, None, None, None), powerbw_time(xr)),
                 (channel_power(p5, f5, None, None, None), channel_power(p5, f5)),
                 (frequency_error(1.0, 3.0, None), frequency_error(1.0, 3.0)),
                 (scope_band(None, None, None, None, None), scope_band()),
                 (scope_band("startstop", None, None, None, None), scope_band("startstop")),
                 (channel_measure(pxr, fxr, None, None, None, None, None), channel_measure(pxr, fxr)),
                 (channel_measure(pxr, fxr, 1000.0, 1500.0, None), channel_measure(pxr, fxr, 1000.0, 1500.0)),
                 (measure_welch(res_d, 1000.0, 1500.0, None), measure_welch(res_d, 1000.0, 1500.0)),
                 (measure_welch(res_d, None, None, None, None, None), measure_welch(res_d)),
                 (measure_welch(res_d, None, None, None, None, "power"), measure_welch(res_d, kind="power")),
                 (scope_measure_welch(res_d, 1000.0, 1500.0, None, None, None), scope_measure_welch(res_d, 1000.0, 1500.0)),
                 (scope_measure_welch(res_d, None, None, None, None, None), scope_measure_welch(res_d)),
                 (scope_channel_measure(res_d["power"], fxr, res_d["rbw"], None, None, None, None, None, None),
                  scope_channel_measure(res_d["power"], fxr, res_d["rbw"])),
                 (scope_channel_measure(res_d["psd"], fxr, None, 1000.0, 1500.0, None, None, "psd", None),
                  scope_channel_measure(res_d["psd"], fxr, kind="psd", start=1000.0, stop=1500.0)),
                 (periodogram_psd(xr, None, None), periodogram_psd(xr))]
        for u, v in pairs:
            if not same(u, v):
                bad.append(f"{u} ≠ {v}")
        if scope_measure_welch(res_d, None, None)["start"] != DEFAULT_START or scope_measure_welch(res_d, None, None)["stop"] != DEFAULT_STOP:
            bad.append("scope start／stop None 不是預設 −1000／1000")
    except Exception as e:                                             # noqa: BLE001
        bad.append(f"丟了 {type(e).__name__}: {e}")
    missing = [
        ("obw Pxx", lambda: obw(None, f5), "input number 1, Pxx,"), ("obw F", lambda: obw(p5, None), "input number 2, F,"),
        ("obw Sxx", lambda: obw(None, f5, 99, rbw=10), "input number 1, Sxx,"), ("obw 兩個都 None（先 Pxx）", lambda: obw(None, None), "input number 1, Pxx,"),
        ("obw_time X", lambda: obw_time(None, 1e4), "input number 1, X,"), ("powerbw Pxx", lambda: powerbw(None, f5), "input number 1, Pxx,"),
        ("powerbw F", lambda: powerbw(p5, None), "input number 2, F,"), ("powerbw_time X", lambda: powerbw_time(None), "input number 1, X,"),
        ("channel_power Pxx", lambda: channel_power(None, f5), "input number 1, Pxx,"),
        ("channel_measure F", lambda: channel_measure(p5, None), "input number 2, F,"),
        ("bandpower Pxx", lambda: bandpower(None, f5), "input number 1, Pxx,"), ("bandpower F", lambda: bandpower(p5, None), "input number 2, F,"),
        ("mean_square X", lambda: mean_square(None), "input number 1, X,"), ("periodogram_psd X", lambda: periodogram_psd(None, 1e4), "input number 1, X,"),
        ("cumulative_power pxx", lambda: cumulative_power(None, f5), "the spectrum"),
        ("cumulative_power f", lambda: cumulative_power(p5, None), "the frequency grid"),
        ("bin_widths", lambda: bin_widths(None), "the frequency grid"), ("to_dbm", lambda: to_dbm(None), "the power"),
        ("frequency_error flo", lambda: frequency_error(None, 1.0), "flo"), ("frequency_error fhi", lambda: frequency_error(1.0, None), "fhi"),
        ("scope trace", lambda: scope_channel_measure(None, f5, 10.0, 0, 40), "the displayed trace"),
        ("scope 格", lambda: scope_channel_measure(p5, None, 10.0, 0, 40), "the frequency grid"),
    ]
    for label, fn, what in missing:
        try:
            fn()
            bad.append(f"{label}＝None 沒丟錯誤")
        except ChannelMeasureError as e:
            if e.identifier != "dsv:chmeas:MissingInput" or str(e) != f"Expected {what} to be an array, but it is None (not given)." or not e.zh:
                bad.append(f"{label}＝None: got {e.identifier!r} {str(e)!r}")
        except Exception as e:                                         # noqa: BLE001
            bad.append(f"{label}＝None 丟了 {type(e).__name__}: {e}")
    check(not bad, f"None＝沒給：有預設值的引數（percent／R／freqrange／rbw／fs／center／time_len／df／kind／mode／start／stop／span／func）None＝預設值，"
                   f"{len(pairs)} 組呼叫（obw PSD／範圍／功率譜形式、obw_time、powerbw、powerbw_time、channel_power、channel_measure、measure_welch、"
                   f"frequency_error、scope_band、scope_channel_measure、scope_measure_welch、periodogram_psd）和不給同值（最大相對差 {none_worst[0]:.1e}，"
                   f"容差 {TOL:g}：經 welch 的鏈在 anaconda 的 numpy 1.26 上不是位元級可重現；percent＝None 預設 99，和 powerbw 的 R＝None 一致）；必要的陣列引數（Pxx／Sxx／F／X、trace／頻率格、flo／fhi、功率）None 丟 dsv:chmeas:MissingInput"
                   f"「Expected input number 1, Pxx, to be an array, but it is None (not given).」（{len(missing)} 個入口，照 MATLAB 的順序先 Pxx 再 F），"
                   f"不再冒稱 cell" + (f"（{bad}）" if bad else ""))

    # 7e) 第五輪實測（ref_obw_r5.json，ref_obw_r5.m 產生）：Pxx／Sxx／F／X 的類別檢查——其餘整數類別與 half／logical 的類別名、
    #     類別檢查先於一切（F、屬性、P、R、Fs、空訊號、1 個樣本）、MATLAB 的字面值是 double（Python 的 int 清單對應它）。
    r5_path = os.path.join(d, "ref_obw_r5.json")
    if not (os.path.isfile(r5_path) and os.path.isfile(r3_path)):
        check(False, f"找不到 {r5_path}（或 ref_obw_r3.json）")
    else:
        J5 = json.load(open(r5_path, encoding="utf-8"))
        R5 = {c["name"]: c for c in J5["cases"]}
        xi5 = np.round(1000 * xr)
        pn5 = np.array([1.0, np.nan, 5.0, 2.0, 1.0])
        i16, i32, i64, u8, u16, u32, u64, f16 = np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64, np.float16
        calls5 = {
            "i_obw_pxx_int32": lambda: obw(p5.astype(i32), f5), "i_obw_pxx_int64": lambda: obw(p5.astype(i64), f5),
            "i_obw_pxx_uint16": lambda: obw(p5.astype(u16), f5), "i_obw_pxx_uint32": lambda: obw(p5.astype(u32), f5),
            "i_obw_pxx_uint64": lambda: obw(p5.astype(u64), f5), "i_obw_sxx_int16": lambda: obw(p5.astype(i16), f5, 99, rbw=10),
            "i_obw_f_int64": lambda: obw(p5, f5.astype(i64)), "i_obw_f_uint8": lambda: obw(p5, f5.astype(u8)),
            "i_obw_sxx_f_int32": lambda: obw(p5, f5.astype(i32), 99, rbw=10),
            "h_obw_f_half": lambda: obw(p5, f5.astype(f16)), "h_obw_x_half": lambda: obw_time(xr.astype(f16), 1e4),
            "h_pbw_pxx_half": lambda: powerbw(p5.astype(f16), f5), "h_pbw_x_half": lambda: powerbw_time(xr.astype(f16), 1e4),
            "h_bp_pxx_half": lambda: bandpower(p5.astype(f16), f5), "h_bp_x_half": lambda: mean_square(xr.astype(f16)),
            "i_bp_x_uint8": lambda: mean_square(p5.astype(u8)), "i_bp_pxx_int64_range": lambda: bandpower(p5.astype(i64), f5, (5, 35)),
            "i_obw_x_int64_nofs": lambda: obw_time(xi5.astype(i64)),
            "i_pbw_x_uint16_fs_int16": lambda: powerbw_time((xi5 + 5000).astype(u16), i16(10000)),
            "l_obw_pxx_logical": lambda: obw(p5 > 0, f5), "l_obw_x_logical": lambda: obw_time(xr > 0, 1e4),
            "l_pbw_x_logical": lambda: powerbw_time(xr > 0, 1e4), "l_bp_x_logical": lambda: mean_square(xr > 0),
            "l_bp_pxx_logical": lambda: bandpower(p5 > 0, f5),
            "o_obw_both_int16": lambda: obw(p5.astype(i16), f5.astype(i16)),
            "o_obw_single_pxx_int16_f": lambda: obw(p5.astype(np.float32), f5.astype(i16)),
            "o_obw_int16_pxx_short_f": lambda: obw(p5.astype(i16), f5[:4]), "o_obw_int16_pxx_neg": lambda: obw((-p5).astype(i16), f5),
            "o_obw_int16_pxx_3d": lambda: obw(np.zeros((4, 2, 2), i16), f5[:4]), "o_obw_int16_pxx_bad_P": lambda: obw(p5.astype(i16), f5, 100),
            "o_obw_int16_pxx_P_int16": lambda: obw(p5.astype(i16), f5, i16(90)), "o_obw_int16_f_nan_pxx": lambda: obw(pn5, f5.astype(i16)),
            "o_pbw_int16_f_bad_R": lambda: powerbw(p5, f5.astype(i16), 0), "o_obw_x_int32_bad_fs": lambda: obw_time(xi5.astype(i32), -1),
            "o_obw_x_int32_1sample": lambda: obw_time(i32(3), 1e4), "o_obw_x_int32_empty": lambda: obw_time(np.zeros(0, i32), 1e4),
            "o_bp_int16_pxx_bad_f": lambda: bandpower(p5.astype(i16), f5[::-1]),
            "o_bp_x_int16_inf_shape": lambda: mean_square(np.zeros((2, 2, 2), i16)),
            # MATLAB 的 [p5 int16(p5)] 串接成 int16（class_of_mixed_concat）；numpy 的 column_stack 會升成 float64，所以用 astype 給同一個 int16 矩陣
            "m_obw_mat_double_int16": lambda: obw(np.column_stack([p5, p5]).astype(i16), f5),
            "m_obw_pxx_double_of_int16": lambda: obw(p5.astype(i16).astype(float), f5),
            "m_obw_literal": lambda: obw([1, 2, 5, 2, 1], [0, 10, 20, 30, 40]),          # Python 的 int 清單＝MATLAB 的 double 字面值
            "m_obw_x_int32_as_double": lambda: obw_time(xi5.astype(i32).astype(float), 1e4),
        }
        bad5 = []
        lits = (J5.get("class_of_literal"), J5.get("class_of_mixed_concat"), J5.get("class_of_logical_literal"))
        if lits != ("double", "int16", "logical"):
            bad5.append(f"MATLAB 的字面值類別不是預期的 double／int16／logical：{lits}")
        for nm, fn in calls5.items():
            ref = R5.get(nm)
            msg = "JSON 沒有這一筆" if ref is None else matches(ref, fn)
            if msg:
                bad5.append(f"{nm}: {msg}")
        unused5 = sorted(set(R5) - set(calls5))
        if unused5:
            bad5.append(f"JSON 裡沒被比到的：{unused5}")
        n_err5 = sum(1 for c in R5.values() if not c["ok"])
        # Python 的 int／list／tuple 當 double：和 float 陣列位元級相同；numpy 整數 ndarray／純量才是整數類別
        try:
            ref_d = obw(p5, f5)
            lit = [obw([1, 2, 5, 2, 1], [0, 10, 20, 30, 40]), obw((1, 2, 5, 2, 1), (0, 10, 20, 30, 40)), obw([[1], [2], [5], [2], [1]], f5),
                   obw([i16(1), i16(2), i16(5), i16(2), i16(1)], f5), obw(p5, [0, 10, 20, 30, 40])]
            if any(v != ref_d for v in lit):
                bad5.append(f"int 字面值的 obw {lit} ≠ float 的 {ref_d}")
            if (powerbw([1, 2, 5, 2, 1], [0, 10, 20, 30, 40]) != powerbw(p5, f5) or bandpower([1, 2, 5, 2, 1], [0, 10, 20, 30, 40]) != bandpower(p5, f5)
                    or mean_square([1, 2, 3]) != mean_square(np.array([1.0, 2.0, 3.0])) or obw_time([1, 3, 2], 1e4) != obw_time(np.array([1.0, 3.0, 2.0]), 1e4)
                    or channel_measure([1, 2, 5, 2, 1], [0, 10, 20, 30, 40]) != channel_measure(p5, f5) or to_dbm(1) != to_dbm(1.0)
                    or not np.array_equal(cumulative_power([1, 2, 5, 2, 1], [0, 10, 20, 30, 40])[0], cumulative_power(p5, f5)[0])):
                bad5.append("powerbw／bandpower／mean_square／obw_time／channel_measure／to_dbm／cumulative_power 的 int 字面值和 float 不同")
        except Exception as e:                                         # noqa: BLE001
            bad5.append(f"int 字面值丟了 {type(e).__name__}: {e}")
        # 同一條規則用在 channel_measure／channel_power、numpy 整數純量、DSV 自己的輔助函式（識別碼 dsv:chmeas:invalidType）
        for label, fn, ident, cls in [
            ("channel_measure Pxx int16", lambda: channel_measure(p5.astype(i16), f5), "MATLAB:obw:invalidType", "int16"),
            ("channel_power F uint8", lambda: channel_power(p5, f5.astype(u8)), "MATLAB:obw:invalidType", "uint8"),
            ("measure_welch psd int64", lambda: measure_welch({"psd": p5.astype(i64), "f": f5}), "MATLAB:obw:invalidType", "int64"),
            ("obw Pxx 是 numpy 整數純量", lambda: obw(i64(3), f5), "MATLAB:obw:invalidType", "int64"),
            ("obw Pxx 是 numpy half 純量", lambda: obw(f16(3), f5), "MATLAB:obw:invalidType", "half"),
            ("cumulative_power int32", lambda: cumulative_power(p5.astype(i32), f5), "dsv:chmeas:invalidType", "int32"),
            ("to_dbm uint16", lambda: to_dbm(np.array([1, 2], u16)), "dsv:chmeas:invalidType", "uint16"),
            ("frequency_error flo int64", lambda: frequency_error(i64(1), 2.0), "dsv:chmeas:invalidType", "int64"),
            ("scope trace half", lambda: scope_channel_measure(p5.astype(f16), f5, 10.0, 0, 40), "dsv:chmeas:invalidType", "half"),
        ]:
            try:
                fn()
                bad5.append(f"{label}: 沒丟錯誤")
            except ChannelMeasureError as e:
                if e.identifier != ident or not str(e).endswith(f"double, single\n\nInstead its type was {cls}.") or not e.zh:
                    bad5.append(f"{label}: got {e.identifier!r} {str(e)!r}")
            except Exception as e:                                     # noqa: BLE001
                bad5.append(f"{label}: 丟了 {type(e).__name__}: {e}")
        check(not bad5, f"第五輪 MATLAB 實測（ref_obw_r5.json {len(R5)} 筆，Pxx／Sxx／F／X 的類別檢查）：{n_err5} 筆 invalidType 的識別碼與完整訊息、"
                        f"{len(R5) - n_err5} 筆數值（rtol {TOL:g}）逐筆一致——int32／int64／uint16／uint32／uint64／half／logical 的類別名、功率譜形式叫 Sxx、"
                        f"類別檢查先於 F、長度、負值、三維、P、R、Fs、空訊號與 1 個樣本的檢查；MATLAB 的 [1;2;5;2;1] 是 double（class_of_literal），"
                        f"所以 Python 的 int／list／tuple（含裝 numpy 整數純量的 list）當 double、和 float 位元級相同；numpy 整數 ndarray／純量與 float16 "
                        f"才是 MATLAB 的整數類別／half（channel_measure／channel_power／measure_welch 與 DSV 輔助函式同一條規則）；MATLAB 的 [p5 int16(p5)] "
                        f"串接成 int16（numpy 會升成 float64，是串接規則的差異，不在這個模組）" + (f"（不一致：{bad5}）" if bad5 else ""))

    # 7f) 第六輪實測（ref_obw_r6.json，ref_obw_r6.m 產生）：half 的屬性規則（FREQRANGE／R／bandpower F／FREQRANGE 丟
    #     half:error:FunctionNotDefinedForHalf，P／RBW／Fs 收）、「Instead its type was」只有 char 與空 cell 不印、空的非數值 FREQRANGE 的
    #     double() 轉換錯、每筆釘一條規則的數值案例（非等距格的缺格寬度位置、範圍前全零的反向內插索引、交越點 PSD 為 0 的 realmin 墊底、
    #     含 DC bin 的 powerbw 範圍位準用未加倍的 PSD）、single 非整數 F 的 bandpower（已知差異 2）。
    #     va6＝MATLAB 那一邊直接量 validateattributes 的事實（Python 沒有對應，只釘 JSON）；calls6＝逐筆對照的 Python 呼叫；
    #     known6＝已知差異（DSV 要等於 MATLAB 的 double 版參考、和 single 版的相對差釘住）。JSON 每一筆都要被用到。
    r6_path = os.path.join(d, "ref_obw_r6.json")
    if not (os.path.isfile(r6_path) and os.path.isfile(r3_path)):
        check(False, f"找不到 {r6_path}（或 ref_obw_r3.json）")
    else:
        R6 = {c["name"]: c for c in json.load(open(r6_path, encoding="utf-8"))["cases"]}
        h16, s32, i16 = np.float16, np.float32, np.int16
        HALF = "half:error:FunctionNotDefinedForHalf"
        fnu, fneg = np.array([0.0, 5, 15, 30, 40]), np.array([-7.0, -2, 3, 9, 20])
        q2 = np.column_stack([p5, [5.0, 1, 1, 1, 2]])
        q6, fcen6 = np.array([4.0, 5, 1, 1, 1]), np.array([-20.0, -10, 0, 10, 20])
        ffrac = np.array([0.1, 10.1, 20.1, 30.1, 40.1])
        cell0 = np.array([], dtype=object)
        hv = lambda *v: np.array(v, dtype=h16)                             # noqa: E731 —— MATLAB 的 half([...])
        # validateattributes 直接量的事實：None＝該屬性對 half 有定義（沒丟錯）；否則＝丟的識別碼
        va6 = {"va_half_nonzero": HALF, "va_half_increasing": HALF, "va_half_scalar_increasing": HALF, "va_half_floatclass": "MATLAB:invalidType",
               "va_half_finite": None, "va_half_real": None, "va_half_size": None, "va_half_vector": None, "va_half_scalar": None,
               "va_half_positive": None, "va_half_nonempty": None, "va_half_nonnegative": None, "va_half_less": None, "va_half_ge": None,
               "va_half_numel": None, "va_half_numeric": None, "va_half_2d": None}
        # 「Instead its type was」那一行有沒有印（validateattributes 直接量）
        va6_instead = {"v1_va_cell_empty": False, "v2_va_cell_0x2": False, "v3_va_cell_1x0": False, "v4_va_cell_1elem": True, "v5_va_cell_2elem": True,
                       "v6_va_int16_empty": True, "v7_va_logical_empty": True, "v8_va_half_empty": True, "v9_va_struct_empty": True,
                       "v10_va_datetime_empty": True, "v11_va_duration_empty": True, "v12_va_char_empty": False, "v13_va_char_1": False,
                       "v14_va_string_empty": True, "v15_va_int16_0x2": True}
        calls6 = {
            # half 被拒（FREQRANGE 三種形式、Sxx 形式、R、bandpower 的 F／FREQRANGE；single 的 Pxx 配 half 範圍也是）
            "h1_obw_range_half": lambda: obw(p5, f5, 99, hv(10, 30)), "h2_obw_range_half_frac": lambda: obw(p5, f5, 99, hv(10.1, 30.3)),
            "h3_obw_time_range_half": lambda: obw_time(xr, 1e4, 99, hv(500, 3000)), "h4_pbw_range_half": lambda: powerbw(p5, f5, 3, hv(10, 30)),
            "h5_pbw_time_range_half": lambda: powerbw_time(xr, 1e4, 3, hv(1000, 1500)), "h6_pbw_R_half": lambda: powerbw(p5, f5, h16(3)),
            "h7_pbw_R_half_frac": lambda: powerbw(p5, f5, h16(2.7)), "h8_pbw_time_R_half": lambda: powerbw_time(xr, 1e4, h16(3)),
            "h9_bp_f_half": lambda: bandpower(p5, f5.astype(h16)), "h10_bp_range_half": lambda: bandpower(p5, f5, hv(5, 35)),
            "h11_bp_range_half_frac": lambda: bandpower(p5, f5, hv(5.3, 35.7)), "h12_obw_sxx_range_half": lambda: obw(p5, f5, 99, hv(10, 30), rbw=10),
            "h13_bp_f_half_with_range": lambda: bandpower(p5, f5.astype(h16), (5, 35)),
            "h14_obw_single_pxx_range_half": lambda: obw(p5.astype(s32), f5, 99, hv(10, 30)),
            # 順序：increasing／nonzero 前面的屬性先丟，後面的不會再到
            "o1_obw_time_range_half_inf": lambda: obw_time(xr, 1e4, 99, hv(500, np.inf)), "o2_obw_range_half_decreasing": lambda: obw(p5, f5, 99, hv(30, 10)),
            "o3_obw_range_half_1x3": lambda: obw(p5, f5, 99, hv(10, 30, 50)), "o4_obw_range_half_out": lambda: obw(p5, f5, 99, hv(10, 60)),
            "o5_obw_time_range_half_scalar": lambda: obw_time(xr, 1e4, 99, h16(1000)), "o6_obw_range_half_P_bad": lambda: obw(p5, f5, 100, hv(10, 30)),
            "o7_obw_int16_pxx_range_half": lambda: obw(p5.astype(i16), f5, 99, hv(10, 30)), "o8_pbw_R_half_vec": lambda: powerbw(p5, f5, hv(3, 4)),
            "o9_pbw_R_half_nan": lambda: powerbw(p5, f5, h16(np.nan)), "o10_pbw_R_half_inf": lambda: powerbw(p5, f5, h16(np.inf)),
            "o11_pbw_R_half_empty": lambda: powerbw(p5, f5, np.zeros(0, h16)), "o12_pbw_R_half_zero": lambda: powerbw(p5, f5, h16(0)),
            "o13_pbw_range_half_R_zero": lambda: powerbw(p5, f5, 0, hv(10, 30)), "o14_bp_range_half_1x3": lambda: bandpower(p5, f5, hv(5, 35, 40)),
            "o15_bp_range_half_out": lambda: bandpower(p5, f5, hv(5, 60)), "o16_bp_range_half_decreasing": lambda: bandpower(p5, f5, hv(35, 5)),
            "o17_bp_f_half_short": lambda: bandpower(p5, f5[:4].astype(h16)), "o18_bp_f_half_inf": lambda: bandpower(p5, hv(0, 10, 20, 30, np.inf)),
            "o19_bp_f_half_matrix": lambda: bandpower(p5, np.column_stack([f5, f5]).astype(h16)),
            "o20_bp_f_half_decreasing": lambda: bandpower(p5, f5[::-1].astype(h16)),
            # half 收：P、RBW、Fs（回 double、同 double 的呼叫；不合格的值照常丟）、空的 half 範圍＝沒給
            "a1_obw_rbw_half": lambda: obw(p5, f5, 99, rbw=h16(10)), "a2_obw_rbw_half_frac": lambda: obw(p5, f5, 99, rbw=h16(10.3)),
            "a3_obw_P_half": lambda: obw(p5, f5, h16(90)), "a4_obw_P_half_frac": lambda: obw(p5, f5, h16(99.9)),
            "a5_obw_fs_half": lambda: obw_time(xr, h16(1e4)), "a6_obw_fs_half_frac": lambda: obw_time(xr, h16(3333.3)),
            "a7_pbw_fs_half": lambda: powerbw_time(xr, h16(1e4)), "a8_obw_range_half_empty": lambda: obw(p5, f5, 99, np.zeros(0, h16)),
            "a9_obw_P_half_nan": lambda: obw(p5, f5, h16(np.nan)), "a10_obw_fs_half_zero": lambda: obw_time(xr, h16(0)),
            "a11_obw_rbw_half_small": lambda: obw(p5, f5, 99, rbw=h16(5)),
            # 「Instead its type was」：空 cell 不印（e1／e3–e5／e15–e20／e22）、char 不印（e14）、其餘都印
            "e1_obw_P_cell_empty": lambda: obw(p5, f5, cell0), "e2_obw_P_cell_1": lambda: obw(p5, f5, np.array([1], dtype=object)),
            "e3_obw_pxx_cell_empty": lambda: obw(cell0, f5), "e4_obw_pxx_cell_0x2": lambda: obw(np.empty((0, 2), dtype=object), f5),
            "e5_obw_pxx_cell_1x0": lambda: obw(np.empty((1, 0), dtype=object), f5), "e6_obw_pxx_cell_1": lambda: obw(np.array([1], dtype=object), f5),
            "e7_obw_pxx_int16_empty": lambda: obw(np.zeros(0, i16), f5), "e8_obw_pxx_logical_empty": lambda: obw(np.zeros(0, bool), f5),
            "e9_obw_pxx_half_empty": lambda: obw(np.zeros(0, h16), f5), "e10_obw_pxx_int16_0x3": lambda: obw(np.zeros((0, 3), i16), f5),
            "e11_obw_P_struct_empty": lambda: obw(p5, f5, {}), "e12_obw_P_datetime_empty": lambda: obw(p5, f5, np.array([], dtype="datetime64[s]")),
            "e13_obw_P_logical_empty": lambda: obw(p5, f5, np.zeros(0, bool)), "e14_obw_P_char_empty": lambda: obw(p5, f5, ""),
            "e15_pbw_R_cell_empty": lambda: powerbw(p5, f5, cell0), "e16_bp_range_cell_empty": lambda: bandpower(p5, f5, cell0),
            "e17_bp_pxx_cell_empty": lambda: bandpower(cell0, f5), "e18_bp_f_cell_empty": lambda: bandpower(p5, cell0),
            "e19_bp_x_cell_empty": lambda: mean_square(cell0), "e20_obw_x_cell_empty": lambda: obw_time(cell0, 1e4),
            "e21_pbw_time_range_cell_2": lambda: powerbw_time(xr, 1e4, 3, np.array([1, 2], dtype=object)),
            "e22_obw_sxx_cell_empty": lambda: obw(cell0, f5, 99, rbw=10), "e23_bp_pxx_cell_1": lambda: bandpower(np.array([1], dtype=object), f5),
            # 空的 FREQRANGE：cell／datetime／duration 丟 double() 的轉換錯，數值／logical／char 的空陣列＝沒給
            "r1_obw_range_cell_empty": lambda: obw(p5, f5, 99, cell0), "r2_obw_range_cell_0x2": lambda: obw(p5, f5, 99, np.empty((0, 2), dtype=object)),
            "r3_obw_time_range_cell_empty": lambda: obw_time(xr, 1e4, 99, cell0), "r4_pbw_range_cell_empty": lambda: powerbw(p5, f5, 3, cell0),
            "r5_obw_range_datetime_empty": lambda: obw(p5, f5, 99, np.array([], dtype="datetime64[s]")),
            "r6_obw_range_duration_empty": lambda: obw(p5, f5, 99, np.array([], dtype="timedelta64[s]")),
            "r7_obw_range_int16_empty": lambda: obw(p5, f5, 99, np.zeros(0, i16)), "r8_obw_range_logical_empty": lambda: obw(p5, f5, 99, np.zeros(0, bool)),
            "r9_obw_range_int16_0x2": lambda: obw(p5, f5, 99, np.zeros((0, 2), i16)), "r10_obw_range_char_empty": lambda: obw(p5, f5, 99, ""),
            "r11_pbw_time_range_cell_empty": lambda: powerbw_time(xr, 1e4, 3, cell0), "r12_obw_sxx_range_cell_empty": lambda: obw(p5, f5, 99, cell0, rbw=10),
            # 非等距格：缺格寬度補在最後（F_1＝0）或最前（F_1≠0），把它放反每一筆都會變
            "u1_obw_nu": lambda: obw(p5, fnu), "u2_pbw_nu": lambda: powerbw(p5, fnu), "u3_bp_nu": lambda: bandpower(p5, fnu),
            "u4_bp_nu_range": lambda: bandpower(p5, fnu, (5, 30)), "u5_bp_nu_range_mid": lambda: bandpower(p5, fnu, (7, 33)),
            "u6_obw_nu_range": lambda: obw(p5, fnu, 99, (5, 30)), "u7_obw_nu_range_mid": lambda: obw(p5, fnu, 90, (7, 33)),
            "u8_pbw_nu_range": lambda: powerbw(p5, fnu, 3, (5, 30)), "u9_pbw_nu_range_mid": lambda: powerbw(p5, fnu, 3, (7, 33)),
            "u10_obw_nu_sxx": lambda: obw(p5, fnu, 99, rbw=10), "u11_obw_neg": lambda: obw(p5, fneg), "u12_pbw_neg": lambda: powerbw(p5, fneg),
            "u13_bp_neg": lambda: bandpower(p5, fneg), "u14_obw_neg_range": lambda: obw(p5, fneg, 99, (-2, 9)),
            "u15_pbw_neg_range": lambda: powerbw(p5, fneg, 3, (-2, 9)), "u16_obw_nu_mat": lambda: obw(q2, fnu),
            "u17_pbw_nu_mat": lambda: powerbw(q2, fnu), "u18_bp_nu_mat": lambda: bandpower(q2, fnu),
            # 範圍起點之前全零：門檻＝0 落在 C 的第一個元素，反向內插的索引要從 0 改成 1（不改會用到 C_{-1}）
            "c1_obw_zero_head_range_0_20": lambda: obw([0.0, 0, 0, 0, 1], f5, 99, (0, 20)), "c2_obw_zero_head_range_0_25": lambda: obw([0.0, 0, 0, 0, 1], f5, 99, (0, 25)),
            "c3_obw_zero_head_range_0_30": lambda: obw([0.0, 0, 0, 0, 1], f5, 99, (0, 30)), "c4_obw_zero_head_full": lambda: obw([0.0, 0, 0, 0, 1], f5),
            "c5_obw_zero_tail_range_20_40": lambda: obw([1.0, 0, 0, 0, 0], f5, 99, (20, 40)), "c6_obw_zero_mid_range_10_30": lambda: obw([1.0, 0, 0, 0, 1], f5, 99, (10, 30)),
            "c7_pbw_zero_head_range_0_20": lambda: powerbw([0.0, 0, 0, 0, 1], f5, 3, (0, 20)), "c8_obw_zero_head_P50": lambda: obw([0.0, 0, 0, 0, 1], f5, 50, (0, 20)),
            # 交越點的 PSD 剛好是 0（或次正規數）：那個 bin 以 realmin 墊底再取 log10 才內插得出 19.990237444180657
            "z1_pbw_zero_sides": lambda: powerbw([0.0, 0, 5, 0, 0], f5), "z2_pbw_zero_sides_R10": lambda: powerbw([0.0, 1, 5, 1, 0], f5, 10),
            "z3_pbw_zero_sides_range": lambda: powerbw([0.0, 0, 5, 0, 0], f5, 3, (10, 30)), "z4_pbw_zero_range_mean": lambda: powerbw([5.0, 0, 0, 0, 5], f5, 3, (10, 30)),
            "z5_pbw_denormal_sides": lambda: powerbw([1e-320, 0, 5, 0, 1e-320], f5), "z6_obw_zero_sides": lambda: obw([0.0, 0, 5, 0, 0], f5),
            # DC bin 加倍：找峰值用加倍後的 PSD（d1 峰值在 DC）、有範圍時的參考位準用未加倍的（d5／t9：範圍含 DC bin）
            "d1_pbw_dc_peak_after_doubling": lambda: powerbw(q6, f5), "d2_pbw_no_dc_grid": lambda: powerbw(q6, f5 + 1),
            "d3_pbw_centered_dc_mid": lambda: powerbw([1.0, 1, 3, 5, 1], fcen6), "d4_pbw_centered_dc_mid2": lambda: powerbw([1.0, 4, 5, 1, 1], fcen6),
            "d5_pbw_dc_range_incl": lambda: powerbw(q6, f5, 3, (0, 20)), "d6_pbw_dc_sxx": lambda: powerbw(q6, f5, 3, rbw=10),
            "d7_pbw_negative_start_grid": lambda: powerbw(q6, f5 - 10), "t9_pbw_range_lowend": lambda: powerbw(p5, f5, 3, (0, 5)),
            "t10_pbw_range_highend": lambda: powerbw(p5, f5, 3, (35, 40)),
            # single 的 F：整數值兩邊都是 110；single 的 FREQRANGE 不影響結果類別（100）；double 的非整數 F 是 110
            "s3_bp_f_single_int": lambda: bandpower(p5, f5.astype(s32)), "s4_bp_range_single_frac": lambda: bandpower(p5, f5, np.array([5.3, 35.7], s32)),
            "s5_bp_range_double_of_single_frac": lambda: bandpower(p5, f5, np.array([5.3, 35.7], s32).astype(float)),
            "s6_bp_f_double_frac": lambda: bandpower(p5, ffrac), "s2_bp_f_double_of_single_frac": lambda: bandpower(p5, ffrac.astype(s32).astype(float)),
        }
        # 已知差異 2（single 非整數 F 的 bandpower）：(single 資料的呼叫, MATLAB double 版參考的名字, 和 MATLAB single 結果的最大相對差)
        known6 = {"s1_bp_f_single_frac": (lambda: bandpower(p5, ffrac.astype(s32)), "s2_bp_f_double_of_single_frac", "1.39e-08")}
        bad6, n_half, n_instead = [], 0, 0
        for nm, want in va6.items():
            ref = R6.get(nm)
            if ref is None or (want is None) != ref["ok"] or (want is not None and ref["id"] != want):
                bad6.append(f"{nm}: MATLAB 那一邊不是 {'通過' if want is None else want}：{ref}")
        for nm, printed in va6_instead.items():
            ref = R6.get(nm)
            if ref is None or ref["ok"] or ref["id"] != "MATLAB:invalidType" or ("Instead its type was" in ref["message"]) != printed:
                bad6.append(f"{nm}: MATLAB 那一邊的 Instead 行不是{'有' if printed else '沒有'}：{ref}")
        for nm, fn in calls6.items():
            ref = R6.get(nm)
            msg = "JSON 沒有這一筆" if ref is None else matches(ref, fn)
            if msg:
                bad6.append(f"{nm}: {msg}")
            elif ref["id"] == HALF:
                n_half += 1
            elif ref["id"].endswith(":invalidType") and "Instead its type was" not in ref["message"]:
                n_instead += 1
        worst6 = {}
        for nm, (fsingle, dref, doc) in known6.items():
            ref, rd = R6.get(nm), R6.get(dref)
            if ref is None or rd is None or not ref["ok"] or ref["classes"] != ["single"] or rd["classes"] != ["double"]:
                bad6.append(f"{nm}: JSON 缺這一筆或 MATLAB 的類別不對（{ref and ref.get('classes')}／{rd and rd.get('classes')}）")
                continue
            msg = matches(rd, fsingle)                                 # DSV 的結果＝MATLAB 對 double(single(F)) 的結果
            if msg:
                bad6.append(f"{nm} 對 {dref}: {msg}")
            ok6, out6, err6 = run(fsingle)
            if ok6:
                g, r = float(np.asarray(out6[0], dtype=float)), float(ref["vals"][0][0])
                worst6[nm] = abs(g - r) / abs(r)
                if f"{worst6[nm]:.2e}" != doc or not isinstance(out6[0], float):
                    bad6.append(f"{nm}: 和 MATLAB single 的 {r} 相對差 {worst6[nm]:.3e}（模組說明寫 {doc}）、型別 {type(out6[0]).__name__}")
        unused6 = sorted(set(R6) - set(calls6) - set(va6) - set(va6_instead) - set(known6))
        if unused6:
            bad6.append(f"JSON 裡沒被比到的：{unused6}")
        check(not bad6, f"第六輪 MATLAB 實測（ref_obw_r6.json {len(R6)} 筆）：validateattributes 對 half 的 {len(va6)} 個屬性（increasing／nonzero 丟 "
                        f"half:error:FunctionNotDefinedForHalf，其餘有定義）與 {len(va6_instead)} 個「Instead its type was」樣本（char 與空 cell 不印）釘住 MATLAB 那一邊；"
                        f"{len(calls6)} 筆 Python 呼叫逐筆一致（rtol {TOL:g}、NaN 相同、識別碼與完整訊息相同）：half 的 FREQRANGE（PSD／功率譜／時域、單一數值）、"
                        f"R、bandpower 的 F／FREQRANGE 共 {n_half} 筆丟 half 錯（前面的屬性 finite／scalar／nonempty／numel／vector 先丟、後面的不再到、"
                        f"Pxx 的類別檢查更先）、half 的 P／RBW／Fs 照 double 算、{n_instead} 筆空 cell／char 的 invalidType 不印 Instead、"
                        f"空的 cell／datetime／duration 範圍丟 double() 的轉換錯而 int16／logical／half／char 的空範圍＝沒給、"
                        f"非等距格 u1–u18（缺格寬度的位置）、範圍前全零 c1–c8（反向內插索引）、交越點 PSD＝0 的 z1–z6（realmin 墊底）、"
                        f"含 DC bin 的 powerbw 範圍 d1–d7／t9／t10（位準用未加倍的 PSD）；已知差異 2：bandpower(p5, single([0.1 10.1 20.1 30.1 40.1]))"
                        f" MATLAB 單精度算出 110（single），DSV 對 double(single(F)) 算出 109.99999847076833＝MATLAB 的 double 版（位元級），相對差 "
                        f"{'、'.join(f'{k} {v:.2e}' for k, v in worst6.items())}" + (f"（不一致：{bad6}）" if bad6 else ""))

    # 8) 退化輸入：全零頻譜、零通道、範圍內全零、列向量、極大 PSD、1 個樣本——不可丟錯、不可印 numpy 警告，結果照 MATLAB 的 IEEE 算法
    bad = []
    with warnings.catch_warnings():
        warnings.simplefilter("error")                                 # 任何 numpy 警告都當失敗
        try:
            z = powerbw(np.zeros(5), f5)
            if not all(math.isnan(v) for v in z):
                bad.append(f"全零 powerbw 不是全 NaN：{z}")
            zc = powerbw(np.column_stack([p5, np.zeros(5)]), f5)
            one = powerbw(p5, f5)
            if not (all(np.isnan(v[1]) for v in zc) and all(v[0] == o for v, o in zip(zc, one))):
                bad.append(f"零通道矩陣 powerbw：{zc} 對單欄 {one}")
            zr = powerbw(np.array([1.0, 0.0, 0.0, 0.0, 1.0]), f5, None, (10, 30))
            if not all(math.isnan(v) for v in zr):
                bad.append(f"範圍內全零 powerbw 不是全 NaN：{zr}")
            z1 = obw(np.zeros(5), f5)                                  # 照 MATLAB obw：邊緣內插 0/0 → NaN，pwr＝P/100·tot＝0
            if not (all(math.isnan(v) for v in z1[:3]) and z1[3] == 0.0):
                bad.append(f"全零 obw 應是 (NaN, NaN, NaN, 0)：{z1}")
            row = obw(pxr[None, :], fxr)
            col = obw(pxr, fxr)
            if row != col or not all(isinstance(v, float) for v in row):
                bad.append(f"列向量 PSD 的 obw {row} ≠ 行向量 {col}")
            prow = periodogram_psd(xr[None, :], fs)[0]
            if prow.shape != pr.shape or not close(prow, pr):          # 兩次 welch：TOL 比（anaconda 的 numpy 1.26 不是位元級可重現）
                bad.append("列向量時域訊號的 periodogram 和行向量不同")
            huge = obw(np.full(5, 1e308), f5)
            hp = channel_power(np.full(5, 1e308), f5)
            hb = bandpower(np.full(5, 1e308), f5)
            if not (all(math.isnan(v) for v in huge) and math.isnan(hp) and hb == math.inf):
                bad.append(f"極大 PSD：obw {huge}、channel_power {hp}、bandpower {hb}")
            pb_big = powerbw(np.full(5, 1e308), f5)                    # DC 加倍 → Inf 峰值、參考位準 Inf → 出發點就 ≤ 位準 → NaN
            if not all(math.isnan(v) for v in pb_big):
                bad.append(f"極大 PSD 的 powerbw 不是全 NaN：{pb_big}")
            pt_big, _ = periodogram_psd(np.full(8, 1e308), 1e4)        # FFT 溢位成 Inf，不印警告（MATLAB 同樣靜靜給 Inf）
            if not np.isinf(pt_big).any():
                bad.append(f"1e308 時域樣本的 periodogram 應溢位成 Inf：{pt_big}")
            if not math.isnan(mean_square([])):
                bad.append("mean_square([]) 應該是 NaN")
            ms0 = mean_square(np.zeros((0, 2)))                        # mean(zeros(0,2), 1)＝[NaN NaN]
            if not (ms0.shape == (2,) and np.isnan(ms0).all()):
                bad.append(f"mean_square(0×2) 應是 [NaN NaN]：{ms0}")
            if not math.isinf(mean_square([1e308, 1e308])):             # 平方溢位成 Inf，不印警告
                bad.append("mean_square(1e308) 應溢位成 Inf")
            # 公開輔助函式：1-D pxx 當一個通道（N+1 × 1，不是 N+1 × N 的廣播）、和 (N × 1) 位元級相同；time_len 的 int／float／numpy 整數同值
            c1, b1 = cumulative_power(p5, f5)
            c2, b2 = cumulative_power(p5[:, None], f5)
            c3, _ = cumulative_power(p5[None, :], f5)
            if not (c1.shape == (6, 1) and np.array_equal(c1, c2) and np.array_equal(c1, c3) and np.array_equal(b1, b2)
                    and np.array_equal(bin_widths(f5), np.full(5, 10.0)) and bin_widths([]).shape == (0,)):
                bad.append(f"cumulative_power 1-D／列向量：{c1.shape} vs {c2.shape}；bin_widths {bin_widths(f5)}")
            tl = powerbw_time(xr, fs)
            pb_n = powerbw(pr, fr, time_len=N)                         # 同一個 pr：int／float／numpy 整數的 time_len 位元級相同
            if not (pb_n == powerbw(pr, fr, time_len=float(N)) == powerbw(pr, fr, time_len=np.int64(N))
                    and powerbw(pr, fr, time_len=None) == powerbw(pr, fr) and all(close(u, v) for u, v in zip(tl, pb_n))):
                bad.append("powerbw 的 time_len 用 int／float／numpy 整數應該同值、且等於 powerbw_time")
            fe = frequency_error(np.array([1.0, 3.0]), np.array([3.0, 5.0]), 2)
            if not (isinstance(fe, np.ndarray) and np.array_equal(fe, [0.0, 2.0]) and frequency_error(1.0, 3.0, np.float32(2)) == 0.0
                    and math.isnan(frequency_error(float("nan"), 3.0)) and math.isnan(frequency_error(float("inf"), float("-inf")))
                    and isinstance(frequency_error(1.0, 3.0), float)):
                bad.append(f"frequency_error 陣列／NaN／±Inf：{fe}")
            # 1e308 級的頻率格（有限、遞增）：相鄰相加／相減溢位成 ±Inf，照 IEEE 往下算（結果 NaN／Inf）、不丟錯也不印警告
            fhuge = np.array([-1e308, -5e307, 0.0, 5e307, 1e308])
            hf = [obw(p5, fhuge), channel_power(p5, fhuge), powerbw(p5, fhuge), channel_measure(p5, fhuge)["ferr"], bandpower(p5, fhuge),
                  cumulative_power(p5, fhuge)[1], bin_widths(fhuge), frequency_error(1e308, 1e308), obw(p5, fhuge, 99, (-5e307, 5e307))]
            if not all(np.all(np.isnan(v) | np.isinf(v) | np.isfinite(v)) for v in hf):   # 只要算得出來（不丟錯、不印警告）
                bad.append(f"1e308 級的頻率格：{hf}")
            try:
                scope_channel_measure(p5, fhuge, 10.0, 0, 1)
                bad.append("1e308 級的格（間距溢位）應判成 NonuniformGrid")
            except ChannelMeasureError as e:
                if e.identifier != "dsv:chmeas:NonuniformGrid":
                    bad.append(f"1e308 級的格：{e.identifier}")
            cm = channel_measure(pxr, fxr, 1000.0, 1500.0, 50.0, center=np.float32(1250))
            cm_ref = channel_measure(pxr, fxr, 1000.0, 1500.0, 50.0, center=1250.0)
            if not (cm["center"] == 1250.0 and cm["ferr"] == cm_ref["ferr"] and channel_measure(pxr, fxr, 1000.0, 1500.0, 50.0, center=1250)["ferr"] == cm_ref["ferr"]):
                bad.append(f"channel_measure 的 center 接受 numpy／int 純量：{cm['center']} {cm['ferr']} vs {cm_ref['ferr']}")
            # 空的 fs（→ 2π 轉成 fs 的類別）：double 空＝沒給 fs；single／int 空照 cast 的四捨五入；格的最後一點＝fs/2（N 偶數、單邊）
            pt0 = powerbw_time(xr, None)
            if not (all(close(u, v) for u, v in zip(powerbw_time(xr, []), pt0)) and all(close(u, v) for u, v in zip(powerbw_time(xr, np.array([])), pt0))):
                bad.append("powerbw_time(x, []) 應和 powerbw_time(x) 同值")
            f_single = periodogram_psd(xr, np.array([], dtype=np.float32))[1]
            f_half = periodogram_psd(xr, np.array([], dtype=np.float16))[1]
            f_int = periodogram_psd(xr, np.array([], dtype=np.int32))[1]
            f_dbl = periodogram_psd(xr, [])[1]
            if not (f_dbl[-1] == math.pi and f_single[-1] == float(np.float32(2 * math.pi)) / 2 and f_half[-1] == 6.28125 / 2 and f_int[-1] == 3.0):
                bad.append(f"空 fs 的 cast 規則：double {f_dbl[-1]!r}（應 π）、single {f_single[-1]!r}（應 {float(np.float32(2 * math.pi)) / 2!r}）、"
                           f"half {f_half[-1]!r}（應 3.140625）、int {f_int[-1]!r}（應 3.0）")
        except Exception as e:                                         # noqa: BLE001
            bad.append(f"丟了 {type(e).__name__}: {e}")
    check(not bad, "退化輸入（MATLAB 的數值在 7b 逐筆比，這裡驗 DSV 自己的形狀與不印警告）：全零頻譜的 powerbw 給 NaN（參考位準 0 → log10 −Inf，"
                   "照 MATLAB 不丟錯）、obw 給 (NaN, NaN, NaN, 0)、矩陣裡的零通道只影響該欄、"
                   "範圍內全零 → NaN、(1 × N) 列向量和行向量結果相同（PSD 與時域都是）、1e308 的 PSD／時域樣本溢位成 Inf／NaN 而不印 numpy 警告、"
                   "mean_square([])＝NaN、mean_square(0×2)＝[NaN NaN]、mean_square(1e308)＝Inf、cumulative_power 的 1-D／列向量 pxx 當一個通道（N+1 × 1）、"
                   "powerbw 的 time_len int／float／numpy 整數同值、frequency_error 陣列／NaN／±Inf 邊緣與 numpy 純量 center、"
                   "1e308 級的頻率格（相加／相減溢位）照 IEEE 算、不印警告、scope 路徑判成 NonuniformGrid、"
                   "空的 fs＝2π（double）／single(2π)＝6.2831854820251465／half 6.28125／整數 6（2π 轉成 fs 的類別）"
                   + (f"（{bad}）" if bad else ""))

    # ---- scope 路徑：22 個 spectrumAnalyzer 擷取，從研究訊號重建顯示頻譜再量 ----
    sp = os.path.join(ref_dir, "scope", "obw_chpower", "scope_obw_captures.json")
    if not os.path.isfile(sp):
        check(False, f"找不到 scope 擷取資料 {sp}")
    else:
        S = json.load(open(sp, encoding="utf-8"))
        caps = S["captures"]
        spectra: Dict[str, Dict[str, Any]] = {}
        grid_bad, disp_bad = [], []
        disp_worst, rbw_worst, n_disp = 0.0, 0.0, 0
        for c in caps:
            sg, sc = c["signal"], c["scope"]
            x = (xc if sg["is_complex"] else xr) * sg["call_scales"][-1]      # 最後一次呼叫的訊號（normal trace 就是它的頻譜）
            assert float(sg["fs"]) == fs and sg["n_samples"] == N
            L = int(sc["window_length"])
            res = welch(x, fs, design_window("hann", L), 0, max(1024, L), "centered" if sc["two_sided"] else "onesided")
            spectra[c["name"]] = res
            dsp = c["display"]
            rbw_worst = max(rbw_worst, abs(res["rbw"] - dsp["rbw_hann_periodic_Hz"]) / dsp["rbw_hann_periodic_Hz"])
            if not dsp["fresh"]:
                continue                                               # stale：_S.txt 是上一個擷取的 trace（分析 §0），不能拿來比
            f = res["f"]
            if not (f.size == dsp["nbins"] and f[0] == dsp["f_first"] and f[-1] == dsp["f_last"] and (f[1] - f[0]) == dsp["df_Hz"]):
                grid_bad.append(f"{c['name']}: 格點 {f.size}/{f[0]}/{f[-1]}/{f[1] - f[0]} ≠ 擷取 {dsp['nbins']}/{dsp['f_first']}/{dsp['f_last']}/{dsp['df_Hz']}")
            tr = res["psd"] if sc["spectrum_type"] == "power-density" else res["power"]
            sdb = to_dbm(tr)
            e = max(abs(float(sdb[i]) - v) for i, v in zip(dsp["sample_idx"], dsp["sample_dBm"]))
            es = abs(float(np.sum(tr)) - dsp["sum_linear_W"]) / dsp["sum_linear_W"]
            n_disp += len(dsp["sample_idx"])
            disp_worst = max(disp_worst, e)
            # 上限＝分析對整條 trace 的殘差（每筆自己的，只是浮點捨入）的 2 倍餘裕：venv 的 numpy 剛好抽到那個最差的 bin（差＝上限），
            # 別的 numpy／FFT 多 1 ulp 就會超過；擷取的 dBm 值本身釘死不動
            if e > 2 * min(SCOPE_TOL_DISPLAY_DB, dsp["analysis_max_abs_dB_vs_model"]) or es > TOL:
                disp_bad.append(f"{c['name']}: 抽樣 bin 最大差 {e:.1e} dB（分析整條 trace 的最大 {dsp['analysis_max_abs_dB_vs_model']:.1e}）、"
                                f"線性總和相對差 {es:.1e}")
        n_fresh = sum(1 for c in caps if c["display"]["fresh"])
        stale = [c["name"] for c in caps if not c["display"]["fresh"]]
        check(not grid_bad and not disp_bad and rbw_worst <= TOL,
              f"scope 顯示頻譜模型 vs spectrumAnalyzer 擷取（{len(caps)} 筆 obw_*：periodic Hann、WindowLength＝NFFT＝{N}、power＝|X|²/(Σw)²、"
              f"power-density＝|X|²/(fs·Σw²)、雙邊 centered 格 Nyquist 在 +fs/2、單邊內部 bin ×2）：{n_fresh} 筆新鮮顯示的格點（bin 數、df、"
              f"f_first、f_last）完全相等、{n_disp} 個抽樣 bin 的 dBm 值最大差 {disp_worst:.1e} dB（上限＝分析對整條 trace 的殘差的 2 倍，逐筆；"
              f"整組 {SCOPE_TOL_DISPLAY_DB:g}）、線性總和 {TOL:g} 內；"
              f"RBW＝ENBW {spectra[caps[0]['name']]['rbw']:.8g} Hz 對擷取 {caps[0]['display']['rbw_hann_periodic_Hz']:.15g}（相對差 {rbw_worst:.1e}）；"
              f"stale 顯示（{', '.join(stale)}：_S.txt 是上一筆的 trace，分析 §0）只用模型不比顯示值"
              + (f"（不一致：{grid_bad + disp_bad}）" if grid_bad or disp_bad else ""))

        # 量測：18 筆數值 ＋ 4 筆 NaN，殘差上限＝分析報告的最大值
        bad = []
        worst = {"cp": 0.0, "bw": 0.0, "fe": 0.0}
        n_num = n_nan = 0
        lines = []
        for c in caps:
            res = spectra[c["name"]]
            sc, mc = c["scope"], c["measurement_config"]
            psd_mode = sc["spectrum_type"] == "power-density"
            if mc["FrequencySpan"] == "span-and-center-frequency":
                a, b, cf = scope_band("span", mc["Span"], mc["CenterFrequency"])
            else:
                a, b, cf = scope_band("startstop", start=mc["StartFrequency"], stop=mc["StopFrequency"])
            m = scope_measure_welch(res, a, b, mc["PercentOccupiedBW"], cf, "psd" if psd_mode else "power")
            ref = c["measurements"]["ChannelMeasurements"]
            if ref["ChannelPower"] is None:
                n_nan += 1
                if not (ref["OccupiedBW"] is None and ref["FrequencyError"] is None):
                    bad.append(f"{c['name']}: 擷取只有部分 NaN {ref}")
                if not (math.isnan(m["power_dbm"]) and math.isnan(m["bw"]) and math.isnan(m["ferr"]) and math.isnan(m["power"]) and not m["inside"]):
                    bad.append(f"{c['name']}: 頻帶 [{a}, {b}] 在格 [{res['f'][0]}, {res['f'][-1]}] 外，scope 給 NaN，DSV 給 {m}")
                lines.append(f"{c['name']} [{a:g} {b:g}] → NaN（f_first {res['f'][0]:.10g}）")
                continue
            n_num += 1
            e_cp = abs(m["power_dbm"] - ref["ChannelPower"])
            e_bw = abs(m["bw"] - ref["OccupiedBW"])
            e_fe = abs(m["ferr"] - ref["FrequencyError"])
            worst["cp"], worst["bw"], worst["fe"] = max(worst["cp"], e_cp), max(worst["bw"], e_bw), max(worst["fe"], e_fe)
            if not (e_cp <= SCOPE_TOL_CP_DB and e_bw <= SCOPE_TOL_BW_HZ and e_fe <= SCOPE_TOL_FE_HZ and m["inside"]):
                bad.append(f"{c['name']}: DSV {m['power_dbm']!r}/{m['bw']!r}/{m['ferr']!r} scope {ref['ChannelPower']!r}/{ref['OccupiedBW']!r}/"
                           f"{ref['FrequencyError']!r} 差 {e_cp:.1e} dB／{e_bw:.1e} Hz／{e_fe:.1e} Hz")
            lines.append(f"{c['name']} [{a:g} {b:g}] P{mc['PercentOccupiedBW']:g}: {e_cp:.1e} dB／{e_bw:.1e} Hz／{e_fe:.1e} Hz")
        check(not bad, f"scope 量測 vs spectrumAnalyzer 擷取（{n_num} 筆數值＋{n_nan} 筆 NaN；PSD＝顯示功率/ENBW、bin 蓋 [f−df/2, f+df/2] 含兩端、"
                       f"C(b)−C(a) 積分到 dBm、邊緣 (100∓P)/200、FE 參考 CF 或 (Start+Stop)/2、格外 → 全 NaN、Max-Hold 時用 normal trace、"
                       f"power-density 模式一樣積分到 dBm）：Channel Power 最大差 {worst['cp']:.1e} dB（上限 {SCOPE_TOL_CP_DB:g}）、Occupied BW "
                       f"{worst['bw']:.1e} Hz（{SCOPE_TOL_BW_HZ:g}）、Frequency Error {worst['fe']:.1e} Hz（{SCOPE_TOL_FE_HZ:g}）——和分析報告的殘差相同"
                       + (f"（不一致：{bad}）" if bad else ""))

        # 端點邊界的證明：[0 5000] 單邊——scope 的 bin 邊界版 vs obw() 的 f_first／f_last 邊界版
        pf = S["end_border_proof"]
        res = spectra[pf["capture"]]
        ms = scope_measure_welch(res, 0.0, 5000.0, 99.0, 2500.0, "power")
        bw_o, flo_o, fhi_o, _ = obw(res["power"], res["f"], 99.0, (0.0, 5000.0), rbw=res["rbw"])
        cp_o = to_dbm(channel_power(res["power"], res["f"], 0.0, 5000.0, rbw=res["rbw"]))
        fe_o = frequency_error(flo_o, fhi_o, 2500.0)
        sc_ref, ob_ref = pf["scope"], pf["obw_borders_at_f_first_f_last"]
        # 參考值是分析報告的 12 位小數（四捨五入誤差 ≤ 5e-13）；實測差 1.4e-14 dB／1.5e-11 Hz／7.4e-12 Hz（scope 側，＝模型對 scope 的殘差）與
        # 4.2e-13／0.0／4.5e-13（obw 側，只有四捨五入），上限 1e-10 放不了任何真正的差異（上面那一組已用全精度擷取值比到 1.1e-13／1.7e-10／8.4e-11）
        PROOF_TOL = 1e-10
        ok = (abs(ms["power_dbm"] - sc_ref["ChannelPower_dBm"]) < PROOF_TOL and abs(ms["bw"] - sc_ref["OccupiedBW_Hz"]) < PROOF_TOL
              and abs(ms["ferr"] - sc_ref["FrequencyError_Hz"]) < PROOF_TOL
              and abs(cp_o - ob_ref["ChannelPower_dBm"]) < PROOF_TOL and abs(bw_o - ob_ref["OccupiedBW_Hz"]) < PROOF_TOL
              and abs(fe_o - ob_ref["FrequencyError_Hz"]) < PROOF_TOL)
        # 內部頻帶兩者相同（obw 與 scope 只在頻譜兩端不同）：實測位元級相同（差 0.0），所以直接用相等
        res_i = spectra["obw_real_2s_startstop_offgrid_P99"]
        mi = scope_measure_welch(res_i, 1234.5, 2345.6, 99.0, None, "power")
        bw_i, flo_i, fhi_i, _ = obw(res_i["power"], res_i["f"], 99.0, (1234.5, 2345.6), rbw=res_i["rbw"])
        cp_i = channel_power(res_i["power"], res_i["f"], 1234.5, 2345.6, rbw=res_i["rbw"])
        same_inner = mi["power"] == cp_i and mi["bw"] == bw_i and mi["flo"] == flo_i and mi["fhi"] == fhi_i
        check(ok and same_inner,
              f"scope 與 obw() 的差別只在頻譜兩端：單邊 [0 5000]（{pf['capture']}）scope 的 bin 邊界版 {ms['power_dbm']:.12f} dBm／{ms['bw']:.12f} Hz／"
              f"{ms['ferr']:.12f} Hz（擷取 {sc_ref['ChannelPower_dBm']}／{sc_ref['OccupiedBW_Hz']}／{sc_ref['FrequencyError_Hz']}），"
              f"obw() 的 f_first／f_last 邊界版 {cp_o:.12f}／{bw_o:.12f}／{fe_o:.12f}（分析 {ob_ref['ChannelPower_dBm']}／{ob_ref['OccupiedBW_Hz']}／"
              f"{ob_ref['FrequencyError_Hz']}；差 {cp_o - ms['power_dbm']:.2e} dB、{bw_o - ms['bw']:.3f} Hz、{fe_o - ms['ferr']:.3f} Hz，"
              f"因為 scope 只把 DC bin 的一半算進去）；內部頻帶 [1234.5 2345.6] 兩者位元級相同（通道功率差 {mi['power'] - cp_i:.1e}、OBW 差 {mi['bw'] - bw_i:.1e} Hz）")

        # 行為：power-density 與 power 模式同一個數字；Max-Hold 開著時 normal trace（max-hold trace 會高 20 dB）；auto-span 公式
        m_psd = scope_measure_welch(spectra["obw_real_2s_psd_span1250_2000_P99"], 250.0, 2250.0, 99.0, 1250.0, "psd")
        m_pow = scope_measure_welch(spectra["obw_real_2s_span1250_2000_P99"], 250.0, 2250.0, 99.0, 1250.0, "power")
        # power-density 模式（psd＝|X|²/(fs·Σw²)）與 power 模式（power/ENBW）積分出來的數字在 venv 的 numpy 上位元級相同（差 0.0）；
        # 兩筆是各自跑的 welch，anaconda 的 numpy 1.26 不是位元級可重現，所以用 scope 的殘差上限比、把差印出來
        mode_diff = (abs(m_psd["power_dbm"] - m_pow["power_dbm"]), abs(m_psd["bw"] - m_pow["bw"]), abs(m_psd["ferr"] - m_pow["ferr"]))
        same_mode = (mode_diff[0] <= SCOPE_TOL_CP_DB and mode_diff[1] <= SCOPE_TOL_BW_HZ and mode_diff[2] <= SCOPE_TOL_FE_HZ
                     and abs(m_psd["power"] - m_pow["power"]) <= TOL * abs(m_pow["power"]))
        res_mh = spectra["obw_real_2s_maxhold_2calls"]                 # normal trace＝0.1·xr 的頻譜
        res_full = spectra["obw_real_2s_span1250_2000_P99"]            # xr 的頻譜＝第一次呼叫（max-hold trace 會停在這裡）
        m_norm = scope_measure_welch(res_mh, 250.0, 2250.0, 99.0, 1250.0, "power")
        hold_trace = np.maximum(res_full["power"], res_mh["power"])    # max-hold trace＝逐 bin 最大；0.1·xr 的功率每個 bin 都小，所以就是 xr 的 trace
        m_hold = scope_channel_measure(hold_trace, res_mh["f"], res_mh["rbw"], 250.0, 2250.0, 99.0, 1250.0)
        ref_mh = next(c for c in caps if c["name"] == "obw_real_2s_maxhold_2calls")["measurements"]["ChannelMeasurements"]
        # 擷取值對模型的殘差 ≤ SCOPE_TOL_CP_DB；「高 20 dB」比的是兩個擷取值（xr 與 0.1·xr 各自的殘差），上限取兩倍（實測差 0.0）
        maxhold_ok = (abs(m_norm["power_dbm"] - ref_mh["ChannelPower"]) <= SCOPE_TOL_CP_DB and np.array_equal(hold_trace, res_full["power"])
                      and m_hold["power_dbm"] == m_pow["power_dbm"] and abs(m_hold["power_dbm"] - ref_mh["ChannelPower"] - 20.0) <= 2 * SCOPE_TOL_CP_DB)
        cfg1 = next(c for c in caps if c["name"] == "obw_real_1s_autospan_defaults")["measurement_config"]
        cfg2 = next(c for c in caps if c["name"] == "obw_real_2s_autospan_defaults")["measurement_config"]
        auto_ok = True
        for cfg, lim in ((cfg1, (0.0, fs / 2)), (cfg2, (-fs / 2, fs / 2))):     # 顯示 x 軸範圍（scope_state Start／StopFrequency）
            a_ = scope_auto_span(*lim)
            auto_ok &= (a_["center"] == cfg["CenterFrequency"] and a_["span"] == cfg["Span"] and a_["start"] == cfg["StartFrequency"]
                        and a_["stop"] == cfg["StopFrequency"] and a_["adjacent_bw"] == cfg["AdjacentBW"] and a_["acpr_offsets"] == cfg["ACPROffsets"])
        a1 = scope_auto_span(0.0, fs / 2)
        check(same_mode and maxhold_ok and auto_ok,
              f"scope 行為：power-density 模式的 Channel Power 一樣是積分 dBm（{m_psd['power_dbm']:.10f} 對 power 模式 {m_pow['power_dbm']:.10f}，"
              f"差 {mode_diff[0]:.1e} dB／{mode_diff[1]:.1e} Hz／{mode_diff[2]:.1e} Hz）；Max-Hold 開著時餵 normal trace（0.1·xr：{m_norm['power_dbm']:.10f} dBm＝擷取 {ref_mh['ChannelPower']:.10f}，差 "
              f"{abs(m_norm['power_dbm'] - ref_mh['ChannelPower']):.1e}；用 max-hold trace（＝xr 的 trace）會是 {m_hold['power_dbm']:.10f}，"
              f"高 20 dB，差 {abs(m_hold['power_dbm'] - ref_mh['ChannelPower'] - 20.0):.1e}）；auto-span 公式（顯示 x 軸範圍的 中點／寬度/5／寬度/10／[4 7]·寬度/20）重現單邊與雙邊"
              f"啟用時寫入的設定（單邊：CF {a1['center']:g}、Span {a1['span']:g}、[{a1['start']:g} {a1['stop']:g}]、AdjBW {a1['adjacent_bw']:g}、"
              f"offsets {a1['acpr_offsets']}；雙邊＝預設值 0／2000／1000／[2000 3500]）")

        # scope 路徑的輸入檢查：工具列訊息（照 MATLAB 介面顯示的訊息）、格點、trace
        res = spectra["obw_real_2s_span1250_2000_P99"]
        probes = [
            ("percent 0", lambda: scope_measure_welch(res, 250, 2250, 0), _UI_IDS["percent"], UI_MESSAGES["percent"][0]),
            ("percent 100", lambda: scope_measure_welch(res, 250, 2250, 100), _UI_IDS["percent"], None),
            ("percent NaN", lambda: scope_measure_welch(res, 250, 2250, float("nan")), _UI_IDS["percent"], None),
            ("percent 字串", lambda: scope_measure_welch(res, 250, 2250, "99"), _UI_IDS["percent"], None),
            ("span 0", lambda: scope_band("span", 0, 1250), _UI_IDS["span"], UI_MESSAGES["span"][0]),
            ("span Inf", lambda: scope_band("span", float("inf"), 1250), _UI_IDS["span"], None),
            ("center NaN", lambda: scope_band("span", 2000, float("nan")), _UI_IDS["center"], UI_MESSAGES["center"][0]),
            ("start NaN", lambda: scope_band("startstop", start=float("nan"), stop=3000), _UI_IDS["start"], UI_MESSAGES["start"][0]),
            ("stop 複數", lambda: scope_band("startstop", start=500, stop=3000 + 1j), _UI_IDS["stop"], UI_MESSAGES["stop"][0]),
            ("stop ≤ start", lambda: scope_band("startstop", start=3000, stop=500), "dsv:chmeas:StartStopOrder", None),
            ("stop ≤ start（量測）", lambda: scope_measure_welch(res, 3000, 500), "dsv:chmeas:StartStopOrder", None),
            ("kind power 沒給 rbw", lambda: scope_channel_measure(res["power"], res["f"], None, 250, 2250), "dsv:chmeas:RBWRequired", None),
            ("非等距格", lambda: scope_channel_measure(res["power"], res["f"] ** 2, res["rbw"], 250, 2250), "dsv:chmeas:NonuniformGrid", None),
            ("只有一個 bin", lambda: scope_channel_measure([1.0], [0.0], 7.3, 0, 0.5), "dsv:chmeas:GridTooShort", None),
            ("trace 含負值", lambda: scope_channel_measure(-res["power"], res["f"], res["rbw"], 250, 2250), "dsv:chmeas:expectedNonnegative", None),
            ("trace 複數", lambda: scope_channel_measure(res["power"].astype(complex), res["f"], res["rbw"], 250, 2250), "dsv:chmeas:expectedReal", None),
            ("trace 字串", lambda: scope_channel_measure("abc", res["f"], res["rbw"], 250, 2250), "dsv:chmeas:invalidType", None),
            ("trace 與格長度不符", lambda: scope_channel_measure(res["power"][:-1], res["f"], res["rbw"], 250, 2250),
             "dsv:chmeas:FreqVectorMismatch", None),
            ("trace 超過 2^24 元素", lambda: scope_channel_measure(pbig, np.arange(1 << 12) * 1.0, 7.3, 0, 10), "dsv:chmeas:TooLarge", None),
        ]
        bad = []
        for label, fn, ident, msg in probes:
            try:
                fn()
                bad.append(f"{label}: 沒丟錯誤")
            except ChannelMeasureError as e:
                if e.identifier != ident or (msg is not None and str(e) != msg) or not e.zh:
                    bad.append(f"{label}: got {e.identifier!r} {str(e)!r} want {ident!r}")
            except Exception as e:                                     # noqa: BLE001
                bad.append(f"{label}: 丟了 {type(e).__name__}: {e}")
        # 合格的邊界值要能算：P＝0.01／99.99（spinner 範圍）、頻帶剛好等於格的兩端（含 DC 與 Nyquist bin）、df 明確給、兩欄 trace
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                e1 = scope_measure_welch(res, 250, 2250, PERCENT_MIN)
                e2 = scope_measure_welch(res, 250, 2250, PERCENT_MAX)
                e3 = scope_measure_welch(res, float(res["f"][0]), float(res["f"][-1]), 99.0)
                e4 = scope_channel_measure(res["power"], res["f"], res["rbw"], 250, 2250, 99.0, df=fs / N)
                e5 = scope_channel_measure(np.column_stack([res["power"], 2 * res["power"]]), res["f"], res["rbw"], 250, 2250, 99.0)
                e6 = scope_channel_measure(np.zeros(8), np.arange(8) * 10.0, 15.0, 10, 50)            # 頻帶內全零：−Inf dBm、邊緣 NaN，不丟錯
            edge_ok = (0 < e1["bw"] < e2["bw"] < 2000 and e3["inside"] and math.isfinite(e3["power_dbm"])
                       and e4["power"] == m_pow["power"] and e5["bw"].shape == (2,) and abs(e5["power"][1] - 2 * e5["power"][0]) <= TOL * e5["power"][1]
                       and e6["power_dbm"] == -math.inf and math.isnan(e6["bw"]))
            if not edge_ok:
                bad.append(f"邊界值：P 0.01 bw {e1['bw']}、P 99.99 bw {e2['bw']}、整格 {e3['power_dbm']}、df 明確 {e4['power']} vs {m_pow['power']}、兩欄 {e5['bw']}、全零 {e6}")
        except Exception as e:                                         # noqa: BLE001
            bad.append(f"邊界值丟了 {type(e).__name__}: {e}")
        check(not bad, f"scope 路徑輸入檢查（{len(probes)} 組）：工具列訊息照 MATLAB 介面顯示的訊息（percent 0／100／NaN／字串、span 0／Inf、center NaN、"
                       f"start NaN、stop 複數）、Stop ≤ Start、kind power 沒 rbw、非等距格、單一 bin、trace 負值／複數／字串／長度不符／2^24 防護；"
                       f"合格邊界值可算：P＝{PERCENT_MIN}／{PERCENT_MAX}、頻帶＝整個格（含 DC 與 Nyquist bin）、明確 df、兩欄 trace、全零頻帶 → −Inf dBm／NaN 邊緣"
                       + (f"（{bad}）" if bad else ""))

    # 9) 效能：1e6 個 bin 的置中 PSD、1e6 點的時域鏈、scope 路徑
    n = 1_000_000
    fbig = (np.arange(n) - (n // 2 - 1)) * (fs / n)
    pbig_g = np.exp(-0.5 * ((fbig - 900.0) / 300.0) ** 2) + 1e-6
    t0 = _time.time()
    mb = channel_measure(pbig_g, fbig, -500.0, 2500.0, 99.0)
    ob = obw(pbig_g, fbig, 99.0)
    pb = powerbw(pbig_g, fbig)
    sb = scope_channel_measure(pbig_g, fbig, 1.5 * fs / n, -500.0, 2500.0, 99.0)
    t1 = _time.time() - t0
    t0 = _time.time()
    ot = obw_time(np.cos(2 * np.pi * 1250.0 * np.arange(n) / fs) + 0.01 * np.sin(np.arange(n)), fs, 99.0)
    t2 = _time.time() - t0
    gauss_ok = (abs(ob[1] - (900 - 2.5758 * 300)) < 5 and abs(ob[2] - (900 + 2.5758 * 300)) < 5 and abs(pb[0] - 2 * 300 * math.sqrt(2 * math.log(2))) < 2
                and abs(sb["bw"] - mb["bw"]) < 1e-6)                   # 內部頻帶 [−500 2500]：scope 規則和 obw 規則一致
    check(t1 < 2.0 and t2 < 3.0 and gauss_ok and ot[0] < 20,
          f"效能：1e6 bin 置中 PSD 的 channel_measure＋obw＋powerbw＋scope_channel_measure {t1:.2f}s（高斯譜 σ＝300 Hz：99% 邊 {ob[1]:.0f}～{ob[2]:.0f} Hz、"
          f"3 dB 頻寬 {pb[0]:.0f} Hz、scope 路徑 OBW {sb['bw']:.3f}）；1e6 點時域 obw_time {t2:.2f}s（1250 Hz 單音 99% 頻寬 {ot[0]:.3f} Hz）；通道功率 {mb['power']:.4g}")
    check(True, f"通道量測 vs MATLAB：共比對 {stats['n']} 個數值，最大相對誤差 {stats['worst']:.2e}（容差 {TOL:g}）")
