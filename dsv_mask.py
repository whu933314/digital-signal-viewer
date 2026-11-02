# -*- coding: utf-8 -*-
"""頻譜模板測試（MATLAB Spectrum Analyzer 的 SPECTRAL MASK 分頁、SpectralMaskConfiguration、getSpectralMaskStatus）——純 numpy，和 GUI 分開。

依據（MATLAB R2025a；程式是自己寫的，selftest() 逐筆比對兩組參考資料）：
- tests/matlab_ref/scope/spectral_mask/：**分析器本體實測**（scope_capture.m 開著 spectrumAnalyzer 跑 23 組模板設定、88 次 sa() 呼叫，
  其中 84 次有開模板；每次呼叫後 getSpectralMaskStatus 的全部欄位、顯示頻譜、輸入訊號）。規則的解讀在
  b34/scope_capture/ANALYSIS_mask.md／rules_mask.json（analyze_mask.py 離線重算，84/84 次通過／失敗與失敗通道都對上）。
  DSV 頻譜視窗要重現的是分析器，所以這份是主要依據；下面標「實測」的規則都由它確認。
- tests/matlab_ref/spectral_mask/：屬性、預設值、設定時的錯誤（probe_config.json：MATLAB 實跑 8 個屬性的預設值、33 組設定案例的
  錯誤 ID 與訊息，英文一字不差）；spectral_mask_ref.json＋sm_in_A/B.txt 是研究階段用 pwelch 頻譜（MATLAB 真實數值）加上
  研究階段推定的規則自己算的 17 組案例（遮罩結果不是 MATLAB 的輸出）——其中
  「純量模板只蓋目前 x 軸範圍」已被實測推翻（見下），其餘規則實測一致。
- UI 文字（分頁、面板 7 欄、狀態字、模板色塊）：MATLAB Spectrum Analyzer 介面顯示的英文與簡中文字。

分析器實測的頻譜（模板測的就是這張；scope_spectra()）：
- Welch、Hann periodic 視窗（長度 WindowLength）、OverlapPercent 0、NFFT＝max(1024, WindowLength)（FFTLengthSource auto；
  資料點見下面「NFFT 的資料點」）、'power'：|FFT(w·x)|²/(Σw)²，單邊內部 bin ×2，dBm＝10·log10(P)＋30（ReferenceLoad 1）。
- NFFT 的資料點（R2025a spectrumAnalyzer 實測，tests/matlab_ref/scope/ 四份擷取；selftest 逐筆用顯示頻率格的 bin 數與首末頻率核對）：
  顯示頻譜數值也對上模型的（fresh）：WindowLength 1000→1024（本模板 21 次擷取＋distortion dist_toi_doc_2s）、2048→2048
  （obw_chpower 21 次、distortion 7 次）、4000→4000（本模板 W4000 2 次）、8192→8192（acpr 19 次）；顯示數值是落後的舊資料、
  但頻率格和該次設定的一致的 13 次，依「上一次擷取」分兩類（同一個 scope 物件、release() 之間；上一次擷取**顯示的格**和
  **上一次設定該有的格**都和這次的不同，才排除了沿用）：
  · 獨立 8 次——1024→1024 2 次（distortion dist_h_noiseless_1s_N6、acpr acpr_cplx_welch1024_psd_default_none）、1000→1024
    （dist_toi_doc_1s：513 個單邊 bin）、1999→1999（dist_h_odd_1s_N6：1000 個單邊 bin、末端 23987.9939969985 Hz＝999·48000/1999）、
    2000→2000（dist_h_alias_1s_N6）、2048→2048（dist_h_maxhold_2calls）、4096→4096（dist_h_noisy_1s_N6）、8192→8192
    （acpr_real_1s_auto1side_none：4097 個單邊 bin）；
  · 只是一致 5 次（上一次的格相同，沿用排除不了）——1024→1024 的 acpr_cplx_welch1024_psd_three_pairs_none（上一次
    acpr_cplx_welch1024_psd_default_none 是同一個 1024 bin 雙邊 fs＝1e4 的格；顯示數值兩次不同，但格分不出來）、2048 的
    dist_h_bin_1s_N6／dist_toi_unequal_1s／dist_toi_lowimd_dc_1s、8192 的 acpr_cplx_2s_psd_default_none。
  所以 1024→1024 的獨立證據是 2 次＋1 次一致（不是 3 次）。共 8 種 WindowLength；頻率格就是上一次擷取顯示的格的 3 次
  （dist_h_offbin_1s_N6、dist_h_lowf_1s_N6、dist_toi_bin_1s）和沒有顯示資料的 1 次（obw_real_2s_psd_span1250_2000_P99）不算。
  擷取順序（上一次擷取是誰）：tests/matlab_ref/scope/spectral_mask/run_order.json（scope_capture.m 兩份進度紀錄 run.log／run2.log：
  第 1 次 1–72、第 2 次接續 73–88，各自一個 scope 物件）；selftest 不寫死名單，由它逐筆算出新／獨立／一致／沿用，再和這裡的
  數字比（acpr 擷取自帶的 run_index／previous_capture_in_run 也和它核對）。
  出處：b34/scope_capture/ANALYSIS.md 第 0、1 節（落後顯示的說明）與 rules.json S2。
- 頻率格：單邊 k·fs/NFFT、k＝0..NFFT/2；雙邊 k＝−(NFFT/2−1)..NFFT/2（Nyquist 放正的那端、沒有 −fs/2）；再加 scope 的
  FrequencyOffset（getSpectrumData 的 FrequencyVector 已含偏移，模板也是對這個「顯示頻率」比）。
- AveragingMethod 'running'、SpectralAverages N **不是**最後 N 段的平均，而是 release() 以來所有段週期圖的正規化指數平均：
  λ＝(N−1)/(N+1)，S_n＝Σλ^(n−i)·P_i / Σλ^(n−i)（N＝4 → λ＝0.6；N＝1 → 單一週期圖）。每次呼叫（≥ 1 個視窗的樣本）只產生一張
  顯示頻譜；88 張實測頻譜用這個模型重建，最大差 7.03e-13 dB（WL 1000：資料集 B 第 2 次呼叫＝8 段；資料集 A 最大在第 2 次呼叫＝8 段
  4.05e-13，第 3／4 次＝12／16 段是 1.28e-13／1.21e-13）／6.14e-12 dB（WL 4000、N＝1 的單一週期圖）。
  WL 4000 的殘差明寫（第五輪審查；numpy 2.4.6 pocketfft、arm64 量的）：4 次呼叫各 2.4300561562995426e-12／6.139089236967266e-12／
  2.9558577807620168e-12／4.249045559845399e-12 dB，最大在第 2 次呼叫 bin 2000（500 Hz）通道 2，一個 −41.25 dBm、比峰值 36.54 dBm 低 78 dB
  的 bin：功率相對差 1.41e-12＝6365 ulp（其他三次最大的 bin 也都是 −53～−59 dBm 的低位準 bin，5.6e-13～9.8e-13＝2524～4403 ulp；
  FFT 的絕對捨入誤差跟整段能量走，所以低位準 bin 的相對差大）。它不是模型誤差：MATLAB 自己 fft(w.*x) 算的同一個週期圖
  （tests/matlab_ref/spectral_mask/w4000_fft_ref.m 實跑 R2025a → w4000_fft_ref.json、w4000_fft_call{1..4}.txt）和分析器顯示值也只差到
  4.36e-12／5.77e-12／1.75e-12／3.88e-12 dB，4002 個 bin 位元相同的只有 1445／1344／1489／1876 個（分析器的 FFT 路徑 ≠ fft()）；DSV 對
  fft() 的差 3.25e-12／5.36e-12／1.96e-12／3.14e-12。
  selftest 的 TOL＝FFT 捨入＋視窗預算（第六、七輪審查；以前是 numpy 2.4.6 量到的最大值往上取兩位有效數字 7.1e-13／6.2e-12，餘裕只有 10%／1%，
  同一台機器換 numpy 1.26.4（pocketfft C 版）就量到 6.39e-13／6.71e-12 而 FAIL——TOL 本來就是在量 FFT 實作的捨入，不是模型）：
  · 視窗（第六輪審查指出）：DSV 的 Hann periodic 是 dsv_spectrum.design_window 的 0.5−0.5·cos(2πn/L) 雙精度值，和 MATLAB R2025a hann(L,'periodic')
    的雙精度值（tests/matlab_ref/spectral_mask/hann_periodic_ref.m 實跑 → hann_periodic_{1000,4000}.txt、hann_periodic_ref.json）**不是位元相同**：
    1000 點有 337 個、4000 點有 1393 個不同，最大差 4.44e-16／6.11e-16（相對 1.7e-14／6.2e-14；兩端接近 0 的值差到 128／512 ulp）；MATLAB 的
    w(2:end) 嚴格對稱、numpy 公式算的不是；兩者的精確和（fsum）都是 500／2000，MATLAB 自己的 sum() 印 500／2000.0000000000002。這個差距讓精確
    模型值每個 bin 最多移動 Δ_win＝3.51e-13 dB（WL 1000，資料集 B 第 2 次 bin 638）／4.13e-12 dB（WL 4000 第 2 次呼叫 bin 768 通道 2，比峰值低
    85 dB）——WL 4000 時它比任何實作的 FFT 捨入都大。所以第六輪寫的「分析器顯示值離精確值 5.31e-12、都是 FFT 捨入、分析器的 FFT 離精確值最遠」
    不對：那個 5.31e-12 是對 **DSV 視窗**的精確值量的（bin 768，正是 Δ_win 最大的 bin），其中 4.13e-12 是視窗差；分析器對**自己視窗**的精確值
    最大只差 3.72e-12（bin 2000），比 numpy 1.26.4 的 3.89e-12 還小。
  · 精確值：10 張不同的顯示頻譜各自的模型值用 mpmath 40 位算兩次（exact_periodogram.py → fft_rounding_ref.json；數學真值，不是 MATLAB 量的；
    λ 用 double 的 0.6，和所有實作一樣）：一次用 MATLAB 視窗（分析器與 w4000_fft_ref.m 的 fft() 用的）、一次用 DSV 視窗（DSV 用的）。每個雙精度
    實作對**自己視窗**的精確值的最大誤差：分析器顯示值 δ_scope＝5.68e-13（WL 1000，資料集 B 第 2 次 bin 102，比峰值低 67 dB）／3.72e-12（WL 4000
    第 2 次呼叫 bin 2000 通道 2，比峰值低 78 dB）；MATLAB fft() 3.58e-12（第 1 次呼叫 bin 192 通道 2）；DSV numpy 2.4.6 4.05e-13／2.25e-12、
    numpy 1.26.4 3.34e-13／3.89e-12（採樣，arm64）。
  · 預算：|DSV−scope| ≤ |DSV−精確(DSV 視窗)|＋|精確(DSV 視窗)−精確(MATLAB 視窗)|＋|精確(MATLAB 視窗)−scope| ≤ δ_dsv＋Δ_win＋δ_scope＝B
    （三角不等式；採樣的實作一定滿足，exact_periodogram.py 會 assert）：B＝1.32e-12（WL 1000）／1.17e-11（WL 4000）。TOL＝2B 往上取兩位有效
    數字＝**2.7e-12／2.4e-11**——對 B 有 2 倍餘裕（留給別的 numpy／FFT 實作的捨入），對量到的 DSV−scope 殘差（7.03e-13／6.71e-12）是 3.8／3.6 倍，
    仍比任何模型差異（視窗、縮放、λ、NFFT 錯一個就 ≥ 1e-3 dB）小 8 個數量級。selftest 釘死檔案算得出來的數字（分析器顯示值、fft() 在各自最差
    bin 對自己視窗精確值的差，位元相同；MATLAB 視窗檔的 sha256、sum、前 4 個值、對稱性；Δ_win 最差 bin 的兩個精確值差到 2 ulp 內；fft() 對
    scope 的逐次差也照舊釘死），JSON 的 δ_scope／Δ_win／δ_dsv／B／TOL 要互相一致且等於程式裡的 TOL，採樣的 |DSV−scope| ≤ B；DSV 端的誤差印出來
    並要求 ≤ TOL（對 scope 的 88 張、在釘住的 bin 對 DSV 視窗的精確值）；本機視窗對 MATLAB 視窗的差也印出來（numpy 的 cos 可能因平台差 1 ulp，
    本機視窗是否和參考的 DSV 視窗位元相同用 sha256 報告；差 ≤ 2e-15 即可，量到 6.1e-16）。
- 平均的歷史會被 release() 清掉（每組設定的第 k 次呼叫頻譜位元相同），但測試計數不會（見下）。

模板測試規則：
- 模板值：實數純量，或 N×2 矩陣（N ≥ 2；第 1 欄頻率 Hz、第 2 欄位準 dBr，相對於參考位準）。頻率欄不能有 NaN、必須非遞減；
  位準可以是 NaN、頻率可以是 ±Inf、頻率可以重複（垂直階梯）。
- 【實測／修正】測試跑在算出來的整張頻譜的每個 bin 上，和顯示的 x 軸範圍無關（FrequencySpan 設 120–480 Hz 時 94–101 Hz 的
  音調仍讓測試失敗；getSpectrumData 也回傳整個 Nyquist 範圍）；純量模板＝所有 bin 的同一個常數（dBr）。研究階段推定的「純量模板只蓋
  目前 x 軸範圍」被 8/8 次呼叫推翻，只留在 scalar_over_xlim=True 旗標後面，**不是分析器的行為**（互動縮放沒測過，見未定）。
- 【實測】矩陣模板：斷點 F＝頻率＋MaskFrequencyOffset、P＝位準；F(i) 和前一個原始值相等時加 realmin（2.2250738585072014e-308）。
  每個顯示頻率 x：x < F(1) 或 x > F(n) → 限值 NaN（不測；partial_range 200–300 Hz 的案例確認）；否則取第一個 x ≤ F(j) 的
  j ≥ 2，a＝F(j−1)、b＝F(j)，斜率 s＝(P(j)−P(j−1))/(b−a)，s 是 NaN 當 0，限值＝P(j−1)＋(x−a)·s。
  → 位準線性內插（sloped 案例一致）；NaN 位準的那段不測（nan_segment 案例）；左斷點 −Inf 的那段算出 (x+Inf)·0＝NaN 所以
    **不測**（[-Inf -30; Inf -30] 和 [-Inf -30; 500 -30] 全過、對照組 [0 -30; 500 -30] 全失敗 +57 dB；把 ±Inf 當軸界的作法 8/8 不符，
    只留在 inf_as_axis_limits=True 後面，也不是分析器的行為）。
- 【實測】模板位準是 dBr：參考位準加到限值上，純量模板也加（20 dBr＋ref 10 → 30 dBm）。參考＝CustomReferenceLevel，或
  spectrum-peak＝**所選通道**這次頻譜所有 bin 的最大值，同一個值給所有通道、每次更新重算（per-channel 峰值 4/10 不符）。
- 【實測】通道失敗＝任一 bin S > 上限＋ref 或 S < 下限＋ref；測試通過＝沒有通道失敗；FailingChannels＝失敗通道（1 起算；MATLAB 一個
  通道給純量、多個給列向量、通過給 1×0 空陣列）。嚴格／封閉比較無法分辨（沒有 bin 剛好等於限值，最接近 0.0001 dB）→ 保留推定的嚴格比較。
- 【實測】一次測試＝一張顯示頻譜（＝一次 ≥ 1 視窗的呼叫）；NumTotalTests += 1、NumPassedTests += 通過；
  SuccessRate＝NumPassedTests / NumTotalTests × 100（先除再乘，double 不取整：11/40 → 27.500000000000004、2/3 → 66.66666666666666）。
- 【實測】FailingMasks 只有兩種字串：通過 ''、失敗 'Upper and lower'（不管開哪個模板、哪個失敗；文件寫的 none/upper/lower/
  upper-and-lower 從未出現）。
- 【實測】計數器跨 release() 與所有設定變更（模板、EnabledMasks 含 none、參考模式、WindowLength、FrequencySpan、FrequencyOffset、
  實數→複數）持續累加；reset(sa) 也**不**清（14/56 reset 前後相同）；只有新建 scope 物件才從 0 開始，第一次測試前
  getSpectralMaskStatus 回傳 []（這裡 status＝None）。EnabledMasks＝none：不測、計數凍結、回傳上一次的狀態（含它的 SimulationTime）。
  → MaskTester.clear() 是 DSV 自己的「換新物件」；reset()／release() 照 MATLAB 不動計數。
- 【實測】複數雙邊頻譜（負頻率斷點）同一套規則。
- 面板（MATLAB 介面）：一列 7 欄——Success Rate (%)、Passed Tests、Total Tests、Current Status、Upper Mask Status、Lower Mask Status、
  Failing Channel(s)；沒開的模板顯示「--」；狀態字 Passing／Failing；還沒有資料時 [NaN, NaN, NaN, "", "", "", ""]；none 時面板關掉。
- 色塊（MATLAB 介面）：alpha 0.4、無邊線，通過綠（淺色 #008013／深色 #3ac831）、失敗紅（淺色 #b7312c／深色 #ff453a）；上模板從限值線往上填到
  max(y 軸上限, 最大位準)，下模板往下填到 min(y 軸下限, 最小位準)；純量模板畫滿目前 x 軸範圍（測試仍是整張頻譜）；矩陣模板的
  ±Inf 頻率畫在軸的兩端再加 MaskFrequencyOffset；有 NaN 位準時遠邊就是 y 軸上限（下模板＝下限），NaN 那幾點也畫在那裡（只要有
  NaN 位準，最大位準就是 NaN，遠邊退回 y 軸上限；下模板同樣用最小位準與 y 軸下限）；spectrum-peak 時色塊每次更新重畫在 位準＋峰值。

未定／自行決定（實測分不出來或沒測到的，照推定的規則／預設行為做並標明）：
- 剛好落在垂直階梯頻率的 bin 取左段（左連續）、嚴格 > / <：WL-1000 格沒有 bin 在 90／110 Hz，WL-4000 的 90／110 Hz bin 離兩個候選
  限值都很遠，右連續／封閉比較 84/84 同結果 → 照推定的規則。
- spectrum-peak 的 NaN 處理照推定的規則（從第 1 個 bin 起只在「目前 < 下一個」時更新 → 第 1 個 bin 是 NaN 就一直是 NaN，其他 NaN 略過）；
  實測頻譜沒有 NaN。峰值取「所有 bin」還是「有模板的 bin」實測分不開（模板都蓋滿整個範圍）→ 所有 bin。
- 純量模板在**互動**縮放（工具列拖 x 軸）後會不會跟著動只測了 FrequencySpan 屬性那條路（不跟）；scalar_over_xlim=True 保留推定的
  行為備用，預設 False。左斷點有限、右斷點 +Inf 的矩陣模板沒測到（照推定的規則：右 +Inf 給左邊的位準）。
- SimulationTime 照實測值推：每次呼叫 t_k＝t_{k−1}＋n_k/fs、release 後 t_0＝−1/fs（getSpectrumData 的 SimulationTime 88 次呼叫全部
  吻合：3.999、7.9990000000000006、11.999、15.999，但只有 n＝4000 一種呼叫長度）；由呼叫端給（simulation_time() 可算），none 時狀態
  沿用上一次的（實測 mask_A_none：頻譜時間走到 3.999…15.999、狀態仍是 15.999）。
- NFFT＝max(1024, WindowLength) 有 8 種 WindowLength 的資料點（見上），除了 1000 都 ≥ 1024，所以「< 1024 時補到 1024」只有
  L＝1000 一個點（其他 < 1024 的長度沒測）；呼叫不足一個視窗的樣本怎麼緩衝沒測到（scope_spectra() 直接捨去尾數）。
- scope_spectra() 一串呼叫（＝兩次 release() 之間）中途改通道數或實數↔複數：MATLAB 的 scope 這樣做會怎樣沒探過（本輪不能開
  scope）；DSV 丟 inputSpecChanged。舊版（c004e7d）實測：averages > 1 時實數→複數、2→3 通道漏出 numpy 的 broadcast
  ValueError，1→2 通道把通道 1 的平均歷史悄悄 broadcast 給通道 2，2→1 通道把單通道的段 broadcast 進兩個通道的歷史、輸出
  仍是 2 通道；averages＝1 時實數→複數讓前面的單邊頻譜（513 bin）配上最後的雙邊頻率格（1024）。要換就開新的一串（＝release()）。
  0 個通道的呼叫 → shapeMismatch（以前漏出 np.stack 的錯誤）。
- MaskTester.limits() 一次算完所有通道（向量化；以前每個通道跑一次 mask_limits：審查量到 10^6 通道 × 16 bin 53 秒，這裡用舊版
  實測 10^5 通道 × 16 bin 3.1 秒；f 空時 nch 10^9 是無上限迴圈）：通道數 × max(bin 數, 1) 超過 2^24 → tooLarge（f 空也算 1，所以 nch 10^9 會被擋）；foffset 全部相同時只算一列
  再複製。scalar_over_xlim／inf_as_axis_limits（非分析器行為）在沒給 xlim、各通道 foffset 不同時，x 軸範圍取**所有通道**顯示頻率
  的最小／最大（分析器只有一條共用的 x 軸；以前是每個通道各自的範圍）。xlim 不論旗標開不開都檢查（badAxisLimits）：兩個**有限且遞增**
  的實數——第五輪審查：以前 ±Inf 和反向（[500 0]）都收，scalar_over_xlim／inf_as_axis_limits 時限值全 NaN、測試悄悄通過；沒給 xlim 時
  由 f 推的範圍只用有限的 bin。
- MaskTester.test() 的 time（SimulationTime）必須是 None 或有限實數純量（badScalarArgument，存成 float）、replace_last 必須是
  bool（badFlag）、xlim／foffset 在 none 或沒有 bin 而不測時也照樣檢查。scope_spectra() 的 two_sided 也必須是 bool（badFlag）。
- foffset（＝scope 的 FrequencyOffset；limits()／test() 純量或每通道一個，scope_spectra() 一個值）照 R2025a spectrumAnalyzer 設
  sa.FrequencyOffset 的實測（第五輪審查 probe_r5_offset.m，scope 物件沒顯示；tests/matlab_ref/spectral_mask/probe_r5_offset.json 15 組，
  selftest 逐筆比 ID 與文字）：NaN／Inf／-Inf／[0 NaN]／[0 -Inf] → MATLAB:expectedFinite「Expected FrequencyOffset to be finite.」（和
  validateattributes 'finite' 樣板 finite_template.json、MaskFrequencyOffset 實測的「Expected MaskFrequencyOffset to be finite.」同一個
  樣板）；'abc' → MATLAB:invalidType「Expected FrequencyOffset to be one of these types:\\n\\ndouble」（scope 只收 double，不是屬性那串
  10 種型別；char 沒有「Instead its type was …」那行）、true → 同一段再加「\\n\\nInstead its type was logical.」；0+1i → MATLAB:expectedReal；
  [] → MATLAB:expectedVector「Expected FrequencyOffset to be a vector.」；[1;2]／[1 2 3]／±1e308 接受（scope 收任何長度的向量）。
  第七輪審查再加 13 組（probe_r6_review.m／.json，同樣 scope 物件沒顯示）：[1 2;3 4]（二維矩陣）→ MATLAB:expectedVector（以前 ravel 後當 4 個值收）；
  [true false] → invalidType 加「Instead its type was logical.」；[1 2]'／1／-0／0.5 接受；[NaN NaN] → expectedFinite；MATLAB 的型別訊息只列 double
  一種，其他型別一律印「Instead its type was <class>.」（實測 logical／single／int32／uint8／string／cell）。
  已知差異（DSV 自行決定）：single／int32／uint8（純量或陣列）scope 丟 invalidType（「Instead its type was single／int32／uint8.」），DSV 收 numpy 的
  float32／int32／uint8 等數值純量與陣列（呼叫端方便，MATLAB 文字記在 selftest 的訊息裡）；Python 的 str 當 MATLAB 的 char（'abc' 的文字，沒有
  「Instead」那行；MATLAB 的 string 型別 "abc" 會多印「Instead its type was string.」，Python 沒有對應型別）；cell（{5}）Python 沒有；None／bytes 這類
  MATLAB 沒有的型別給沒有「Instead」那行的文字；zeros(1,0)／zeros(0,1)：MATLAB 接受賦值（讀回 zeros(1,0)），但 PropertyChanged listener 立刻
  丟「Index exceeds array bounds」的警告（找不到那個通道的偏移）——沒有可用的 MATLAB 行為可對應，DSV 把它們當
  MATLAB 的向量形狀（不丟 expectedVector），有通道時走個數檢查 → badFrequencyOffset（0 個值）、scope_spectra() → badScalarArgument，0 個通道時收；
  0×0 的 []、一維空（Python 的 []／np.zeros(0)，當 MATLAB 的 []）、(0,5) 這類沒探過的空形狀 → expectedVector，只有 0 個通道時收（MATLAB 沒有 0 通道）；
  三維以上的陣列沒探過 → expectedVector；多個值但不等於通道數 → DSV 的 badFrequencyOffset；scope_spectra() 多個值 → badScalarArgument（一條頻率格
  只配一個偏移）；形狀錯和 NaN 同時出現時哪個先報沒探過（DSV 先報形狀）。以前 NaN／Inf 的偏移直接進限值計算，限值全 NaN → 測試悄悄通過；第六輪前
  'abc' 的文字是屬性的 10 種型別那串（ID 對、文字不對），scope_spectra() 的 'abc' 是 DSV 的 badScalarArgument。
- panel_row()：status 必須是 None 或 dict（badStatus）；tested 必須是 bool；IsCurrentlyPassing bool、upper_status／lower_status
  bool 或 None、NumPassedTests／NumTotalTests 非負整數且 NumPassedTests ≤ NumTotalTests（第五輪：以前 3 > 2 照印）、SuccessRate 實數純量
  （NaN 可）、FailingChannels 通道清單，型別不對都是 badStatus（以前是原生 AttributeError／KeyError）；labels 必須是 None 或字串的
  list／tuple（badLabels），不論 status 是 None、沒測或有測都先檢查（以前只在有測的路上檢查，panel_row(None, labels=5) 悄悄回空列）。
  success_rate(passed, total) 同樣 passed > total → badCounts（以前 success_rate(3, 2) 回 150.0）。
- failing_channels_matlab()／FailingChannels：list／tuple／一維陣列，元素是 1..2^24 的整數值（1.0 可、1.5／'a'／True／Inf／1e300 不收，
  [1, True] 的 True 也不收；上限＝MAX_ELEMENTS，通道 × bin ≤ 2^24 所以通道號碼不會更大——第五輪：以前 [1e300] 回 301 位數的 int），
  長度不超過 2^24 → badFailingChannels（以前 ['a'] 漏出 int() 的 ValueError、0-d 陣列 np.array(5)
  漏出 len() 的 TypeError——panel_row 的 FailingChannels＝np.array(1) 也是；現在先看 ndim）。
- MaskTester.test() 的 foffset 在 0 個通道（spectra 形狀 (0, nbins)）時也檢查（純量或空；'abc' → MATLAB:invalidType）。
- DSV 自己的呼叫端檢查（MATLAB 的對應訊息沒探過，用 DSV:spectralMask:* 的 ID；全部是 MaskError，不漏 numpy／Python 的原生錯誤）：
  scope_spectra()／simulation_time() 的 fs 必須是有限正數（badSampleRate；bool／字串 '1000' 不收）；scope_spectra() 的 nfft < WindowLength
  丟 fftLengthTooShort（MATLAB 不接受 FFTLength < WindowLength）；MaskTester.limits()／test() 的 foffset 必須是純量或每通道一個值
  （badFrequencyOffset；每個值有限 → 否則 MATLAB:expectedFinite，見上）、f 必須是一維（shapeMismatch）；mask_test() 的限值陣列要是
  (通道, bin) 或 (bin,)（shapeMismatch）；
  整數參數（window_length、averages、nfft、nch、n_samples、passed／total）要是整數值（badIntegerArgument：1000.5 不截斷、'a'／None／bool 不收）；
  純量參數（ref、prev）要是實數純量（badScalarArgument；scope_spectra() 的 foffset 型別照 scope 的 FrequencyOffset（見上），多個值才是
  badScalarArgument）；xlim／ylim 要是兩個有限、遞增的實數（badAxisLimits）；mfo 參數就是
  MaskFrequencyOffset，走 validate_offset（MATLAB 的 ID）；calls 要是 list／tuple 的數值陣列（badCalls）；MaskConfig(bogus=1) →
  unknownProperty（MATLAB 對不存在屬性的 ID 沒探過）；panel_row 缺欄位 → badStatus；MaskTester 的 config 不是 MaskConfig → badConfig。
- 極端值不警告（IEEE 行為）：垂直階梯在 0 Hz（[0 a; 0 b; …]，b−a＝realmin）斜率溢位成 Inf、0·Inf＝NaN → 該 bin 不測；重複的 ±Inf 頻率
  （[Inf a; Inf b]）照 MATLAB 接受、限值全 NaN；1e308＋1e308 的限值／斷點／色塊 y 成 Inf；斷點跨度超過 realmax（[-1e308 a; 1e308 b]，
  diff＝Inf 非遞減）照 MATLAB 接受、斜率 1/Inf＝0 → 整段常數 a。scope_spectra()：|x| ≳ 1e155 的樣本 |FFT|² 溢位成 Inf dBm、Inf 樣本
  給 NaN 頻譜，都不警告（welch 包在 errstate 裡，signal_viewer 的頻譜路徑同樣做法）；N＝1（λ＝0）時每次直接取該段週期圖，不算 0·前一段
  （前一段的 Inf／NaN 不會以 0·Inf＝NaN 留下來）；N > 1 時 Inf／NaN 會留在指數平均裡直到 release（IEEE，MATLAB 沒探過）。
- 沒有 bin 的頻譜（f 長度 0；MATLAB 不會產生）：不測、計數凍結、回傳上一次狀態（tested=False，和 none 一樣）。全 NaN 的頻譜照 IEEE：
  NaN 的比較為假 → 沒有 bin 失敗 → 算一次通過的測試（MATLAB 的 scope 不會顯示 NaN 頻譜，沒探過）。
- 工具列的參考位準與頻率偏移欄位照 MATLAB 工具列欄位的寬鬆解析（toolstrip_parse_float：
  文字剛好是 'Inf'／'inf'／'-Inf'／'-inf' → ±Infinity，其他和 JavaScript 的 parseFloat 同一種規則——略過開頭的空白、取最長的數字前綴：'12abc' → 12、
  '1e999' → Infinity、'Infinity' 可以，空字串、只有空白、看不懂的 → NaN）。參考位準（parse_reference_level）：文字是空字串 → 什麼都
  不做（回 None：設定不變，呼叫端把欄位還原）；頻譜峰值以外的文字解析成 NaN → invalidReferenceLevel，否則 custom，±Inf 也收
  （欄位的錯誤文字雖然寫 finite，欄位本身不檢查有限；屬性 CustomReferenceLevel 照 MATLAB 實測也接受 Inf）。頻率偏移（parse_offset）：
  解析成 NaN（空字串也是）→ invalidMaskFrequencyOffset。±Inf 的偏移欄位本身不擋，之後 MATLAB 怎麼處理
  沒探過：DSV 自行決定照欄位的錯誤文字（finite real scalar）也擋成 invalidMaskFrequencyOffset（屬性 MaskFrequencyOffset 實測也要求有限，
  丟 expectedFinite）。以上是 parse_reference_level／parse_offset 預設（num=None）的行為＝MATLAB 的工具列；頻譜視窗（signal_viewer）
  傳 num＝DSV 的單一數字規則（parse_spec_number：2k、1.5M 這種 SI 字首，'12abc'、'1..2' 是錯；使用者 2026-10-25 決定頻譜視窗的數字欄位
  都用它，不照工具列的寬鬆解析），空字串＝不改、頻譜峰值的文字、錯誤的 identifier 與訊息不變。
- 「取代上一筆」計數（推測的規則，MATLAB 的公開 API 碰不到）：test(..., replace_last=True) 時 passed＝passed−上一次結果
  （passed > 0 才扣）＋這次、total＝max(total, 1)。
- 第 8 個屬性 Enabled（預設 false，文件沒寫）：擷取時 Enabled 永遠和 EnabledMasks≠none 一起設 true、none 時一起 false，分不出它
  單獨的作用 → MaskConfig 帶著它、測不測只看 EnabledMasks；它的錯誤訊息 MATLAB 沒探過，用 DSV 自己的 ID。
- 模板文字的語法只接受數字（含 Inf／-Inf／NaN）和 [f l; f l; …] 矩陣（逗號或空白分隔、分號或換行分列），不像 MATLAB 會評估
  工作區表達式（MATLAB 的上限／下限欄位先做寬鬆解析：開頭是數字就當純量——'12abc' → 12、不加括號的 '0 -17; 90 -17' → 0——
  看不懂才在工作區求值；DSV 不照做：'12abc' 是語法錯，不加括號的矩陣照矩陣收）；語法／形狀錯誤給工具列的
  invalidUpperMask／invalidLowerMask 文字（MATLAB 的 invalidLowerMask 英文原文寫的也是 "upper mask"，是 MathWorks 的筆誤，英文照抄、
  繁中寫對），頻率欄的檢查給屬性的 invalidMaskFrequencyData 文字。parse_mask 的 num＝每個數字的解析（預設 _num：十進位數字與
  Inf／-Inf／NaN）；頻譜視窗傳 DSV 的單一數字規則（另外收 2k、1.5M 這種 SI 字首，矩陣裡的每個數字也是）。
- SelectedChannel 超過通道數：MATLAB 在這種情況的行為沒有實測；這裡只在 spectrum-peak 真的要用到那個
  通道時丟錯（shared_dspwebscopes:spectrumanalyzer:invalidMaskChannelNumber）。f／spectra 不是數值或是複數 → MATLAB:invalidType／expectedReal；形狀不合、bin 數 × 通道數超過 2^24 → DSV 自己的 ID
  （避免無上限的配置）。
- 繁中用詞（message_zh、PANEL_COLUMNS_ZH、STATUS_WORDS）和頻譜視窗一樣用台灣用語：頻譜遮罩／上遮罩／下遮罩／參考位準／頻譜峰值／
  通道／頻率偏移／純量／成功率／通過／失敗（MATLAB 簡中介面是 频谱模板／上模板／下模板／参考电平／标量）；句型照簡中轉，例如「有至少兩列的
  兩欄矩陣」＝zh_CN 的「有至少两行的两列矩阵」（行→列、列→欄）。工具列欄位的錯誤（invalidUpperMask／invalidLowerMask／
  invalidReferenceLevel／invalidMaskFrequencyOffset）和頻譜視窗的 MASK_MESSAGES 一字不差；屬性訊息 invalidMaskData／invalidMaskFrequencyData
  zh_CN 沒有翻（還是英文），繁中是 DSV 自己寫的、主詞用上遮罩／下遮罩。說明文字（docstring）裡的「模板」指的就是 MATLAB 的 mask。
"""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

REALMIN = 2.2250738585072014e-308           # MATLAB realmin（斷點頻率重複時加上去）
ENABLED_MASKS = ("none", "upper", "lower", "upper-and-lower")
REFERENCE_LEVELS = ("spectrum-peak", "custom")
DEFAULTS: Dict[str, Any] = {"EnabledMasks": "none", "UpperMask": math.inf, "LowerMask": -math.inf, "ReferenceLevel": "custom",
                            "CustomReferenceLevel": 0.0, "SelectedChannel": 1, "MaskFrequencyOffset": 0.0,
                            "Enabled": False}                           # MATLAB 驗證過（probe_config.json，8 個屬性）
FAILING_MASKS = ("", "Upper and lower")                                 # 實測：通過／失敗（唯二字串）
STATUS_FIELDS = ("IsCurrentlyPassing", "NumPassedTests", "NumTotalTests", "SuccessRate", "FailingMasks", "FailingChannels",
                 "SimulationTime")                                      # getSpectralMaskStatus 的欄位順序
MAX_ELEMENTS = 1 << 24                                                  # DSV 自己的上限：限值陣列 bin × 通道、NFFT
PANEL_COLUMNS = ("Success Rate (%)", "Passed Tests", "Total Tests", "Current Status", "Upper Mask Status", "Lower Mask Status",
                 "Failing Channel(s)")
PANEL_COLUMNS_ZH = ("成功率 (%)", "通過的測試數", "測試總數", "目前狀態", "上遮罩狀態", "下遮罩狀態", "失敗的通道")   # ＝頻譜視窗的面板
STATUS_WORDS = {"en": {True: "Passing", False: "Failing", None: "--"}, "zh": {True: "通過", False: "失敗", None: "--"}}
PANEL_EMPTY_ROW: Tuple[Any, ...] = (math.nan, math.nan, math.nan, "", "", "", "")   # 還沒有資料時
PATCH_ALPHA = 0.4
PATCH_COLORS = {"light": {"pass": "#008013", "fail": "#b7312c"}, "dark": {"pass": "#3ac831", "fail": "#ff453a"}}
PATCH_LABELS = {"upper": "Upper Mask", "lower": "Lower Mask"}
_NUMERIC_TYPES = "double, single, uint8, uint16, uint32, uint64, int8, int16, int32, int64"
_ID_SA = "shared_dspwebscopes:spectrumanalyzer:"
_ID_WS = "shared_dspwebscopes:dspwebscopes:"
_ID_DSV = "DSV:spectralMask:"


class MaskError(ValueError):
    """MATLAB 會丟的錯誤：identifier＝MATLAB 錯誤 ID（工具列欄位的錯誤用 shared_dspwebscopes:spectrumanalyzer:*、DSV 自己的檢查用 DSV:spectralMask:*）、
    str()＝英文訊息（MATLAB 探過的輸入一字不差；MATLAB 沒有的輸入型別——None 這類——的文字在各檢查處註明）、message_zh＝繁中。"""

    def __init__(self, identifier: str, message: str, message_zh: str):
        super().__init__(message)
        self.identifier = identifier
        self.message = message
        self.message_zh = message_zh


def _err_enum(prop: str, value: Any, members: Sequence[str]) -> MaskError:
    lst = "".join(f"\n    '{m}'" for m in members)
    return MaskError(_ID_WS + "invalidEnumValue",
                     f"{value} is not a valid value for the {prop} property. Value must be a member of this set: {lst}",
                     f"{value} 不是 {prop} 的有效值，必須是：" + "、".join(f"'{m}'" for m in members) + "。")


def _err_type(name: str) -> MaskError:
    return MaskError("MATLAB:invalidType", f"Expected {name} to be one of these types:\n\n{_NUMERIC_TYPES}", f"{name} 必須是數值。")


def _err_scalar(name: str) -> MaskError:
    return MaskError("MATLAB:expectedScalar", f"Expected {name} to be a scalar.", f"{name} 必須是純量。")


def _err_real(name: str) -> MaskError:
    return MaskError("MATLAB:expectedReal", f"Expected {name} to be real.", f"{name} 必須是實數。")


def _err_finite(name: str) -> MaskError:
    """validateattributes 的 'finite' 樣板（MaskFrequencyOffset 由 probe_config.json 實測；FrequencyOffset 由 probe_r5_offset.json 在 scope 上實測，
    finite_template.json 是同一個樣板）。"""
    return MaskError("MATLAB:expectedFinite", f"Expected {name} to be finite.", f"{name} 必須是有限值。")


_OFFSET_TYPE_MSG = "Expected FrequencyOffset to be one of these types:\n\ndouble"    # scope 的 FrequencyOffset 只收 double（probe_r5_offset／probe_r6_review 實測）


def _err_type_offset(value: Any) -> MaskError:
    """scope 的 FrequencyOffset 型別錯（MATLAB:invalidType；R2025a spectrumAnalyzer 實測 probe_r5_offset.json、probe_r6_review.json）：只列一種型別
    double；'abc'（char）只有第一段；true／[true false] 再加「\\n\\nInstead its type was logical.」（validateattributes 印 class(A)）。MATLAB 對
    single／int32／uint8／string／cell 也印「Instead its type was single／int32／uint8／string／cell.」，但 DSV 收 numpy 的非 double 數值型別
    （float32／int32／uint8 …，已知差異，呼叫端方便），Python 的 str 當 char（沒有那行；MATLAB 的 string 型別 Python 沒有），None／bytes／object
    這類 MATLAB 沒有的型別也只給第一段（DSV 自行決定）。"""
    is_logical = isinstance(value, (bool, np.bool_)) or (isinstance(value, np.ndarray) and value.dtype.kind == "b")
    return MaskError("MATLAB:invalidType", _OFFSET_TYPE_MSG + ("\n\nInstead its type was logical." if is_logical else ""),
                     "FrequencyOffset 必須是 double 數值" + ("（現在是邏輯值）。" if is_logical else "。"))


def _offset_values(value: Any) -> Tuple[np.ndarray, bool]:
    """scope 的 FrequencyOffset 值檢查（型別 → 實數 → 形狀；MATLAB 一次只報一個錯，多重缺陷的順序沒探過），回傳 (攤平的 float 陣列, 是不是
    MATLAB 的向量形狀)；有限（expectedFinite）與個數由呼叫端接著檢查。形狀照 R2025a 實測：[1 2;3 4]（二維矩陣）→ MATLAB:expectedVector
    「Expected FrequencyOffset to be a vector.」（probe_r6_review.json）、[]（0×0）→ expectedVector（probe_r5_offset.json）、zeros(1,0)／zeros(0,1)
    MATLAB 算向量、接受賦值（見 MaskTester._offsets）。numpy 對應：0-d 與非空一維 → 向量；二維要有一邊是 1（含 (1,0)／(0,1)）；三維以上或
    二維兩邊都不是 1 的**非空**陣列 → 這裡直接丟 expectedVector；0×0、一維空（Python 的 []）、(0,5) 這類 MATLAB 的 [] 或沒探過的空形狀回
    (空, False)，由呼叫端在有通道時丟 expectedVector（0 個通道時收，DSV 自行決定）。已知差異：numpy 的 float32／int／uint 純量與陣列照收
    （scope 只收 double：single／int32／uint8 丟 invalidType「Instead its type was single／int32／uint8.」）。"""
    if value is None or isinstance(value, (str, bytes, bool, np.bool_)):
        raise _err_type_offset(value)
    try:
        a = np.asarray(value)
    except Exception:
        raise _err_type_offset(value) from None
    if a.dtype.kind == "b":
        raise _err_type_offset(a)
    if a.dtype.kind == "c":
        raise _err_real("FrequencyOffset")
    if a.dtype.kind not in "iuf":
        raise _err_type_offset(value)
    if a.ndim <= 1:
        vec = a.ndim == 0 or a.size > 0
    elif a.ndim == 2:
        vec = 1 in a.shape
    else:
        vec = False
    if not vec and a.size > 0:                   # [1 2;3 4]：R2025a 實測 MATLAB:expectedVector
        raise _err_offset_vector()
    return a.astype(float, copy=False).ravel(), vec


def _err_offset_vector() -> MaskError:
    """[]（0×0）與 [1 2;3 4] → MATLAB:expectedVector（probe_r5_offset.json、probe_r6_review.json 實測）。"""
    return MaskError("MATLAB:expectedVector", "Expected FrequencyOffset to be a vector.", "FrequencyOffset 必須是向量（不能是 []，也不能是矩陣）。")


def _mask_word(name: str) -> str:
    """繁中訊息裡的遮罩名稱（頻譜視窗的用詞）：UpperMask → 上遮罩、LowerMask → 下遮罩，其他（mask_limits 預設的 'Mask'）→ 遮罩。"""
    n = str(name).lower()
    return "下遮罩" if n.startswith("lower") else ("上遮罩" if n.startswith("upper") else "遮罩")


def _toolstrip_mask_error(name: str) -> MaskError:
    # 工具列的 invalidUpperMask／invalidLowerMask：兩個的英文原文都寫 "upper mask"（MathWorks 筆誤，照抄）；繁中寫對。
    # 繁中照 zh_CN「以实数数值标量或有至少两行的两列矩阵形式输入上模板。」（行→列、列→欄；＝頻譜視窗的 MASK_MESSAGES）
    key = "invalidLowerMask" if name.lower().startswith("lower") else "invalidUpperMask"
    return MaskError(_ID_SA + key, "Enter upper mask as a real, numeric scalar or two-column matrix with at least two rows.",
                     f"以實數數值純量或有至少兩列的兩欄矩陣形式輸入{'下遮罩' if key == 'invalidLowerMask' else '上遮罩'}。")


def _enum_text(value: Any, prop: str, members: Sequence[str]) -> str:
    """字串列舉：不分大小寫、空白／底線可代替連字號；不是字串（None、數字、[]）或不在集合裡 → invalidEnumValue。"""
    if not isinstance(value, str):
        raise _err_enum(prop, "[]" if value is None else value, members)
    s = re.sub(r"[\s_]+", "-", value.strip().lower())
    if s not in members:
        raise _err_enum(prop, value, members)
    return s


def normalize_enabled(value: Any) -> str:
    """EnabledMasks：'Upper' → 'upper'、'upper and lower' → 'upper-and-lower'；其他（含 None／非字串）→ invalidEnumValue。"""
    return _enum_text(value, "EnabledMasks", ENABLED_MASKS)


def normalize_reference(value: Any) -> str:
    """ReferenceLevel：'Spectrum peak' → 'spectrum-peak'、'custom'；其他 → invalidEnumValue。"""
    return _enum_text(value, "ReferenceLevel", REFERENCE_LEVELS)


def _numeric_array(value: Any, name: str) -> np.ndarray:
    """MATLAB validateattributes 的型別／非空／實數檢查（順序：型別 → 非空 → 實數）。"""
    if value is None or isinstance(value, (str, bytes, bool)):
        raise _err_type(name)
    try:
        a = np.asarray(value)
    except Exception:
        raise _err_type(name) from None
    if a.dtype.kind not in "iufc":
        raise _err_type(name)
    if a.size == 0:
        raise MaskError("MATLAB:expectedNonempty", f"Expected {name} to be nonempty.", f"{name} 不能是空的。")
    if a.dtype.kind == "c":
        raise _err_real(name)
    return a.astype(float)


def _real_data(value: Any, name: str) -> np.ndarray:
    """f／spectra 這類資料陣列的檢查：數值（不含 logical／字串／None）且不是複數；回傳 float 陣列（空陣列可以）。"""
    if value is None or isinstance(value, (str, bytes, bool)):
        raise _err_type(name)
    try:
        a = np.asarray(value)
    except Exception:
        raise _err_type(name) from None
    if a.dtype.kind == "c":
        raise _err_real(name)
    if a.dtype.kind not in "iuf":
        raise _err_type(name)
    return a.astype(float, copy=False)


def _real_scalar(value: Any, name: str, finite: bool = False) -> float:
    """DSV 自己的呼叫端純量檢查（ref／foffset／prev 這類不是 MATLAB 屬性的參數）：實數純量——Python 數字、numpy 數值純量或 1 個元素的
    數值陣列；bool／字串／None／複數不收；finite=True 時 Inf／NaN 也不收 → DSV:spectralMask:badScalarArgument。"""
    v = math.nan
    ok = not (value is None or isinstance(value, (str, bytes, bool, np.bool_)))
    if ok:
        try:
            a = np.asarray(value)
            ok = a.dtype.kind in "iuf" and a.size == 1
            if ok:
                v = float(a.reshape(()))
        except Exception:
            ok = False
    if not ok or (finite and not math.isfinite(v)):
        want = "a finite real scalar" if finite else "a real scalar"
        raise MaskError(_ID_DSV + "badScalarArgument", f"{name} must be {want}; got {value!r}.",
                        f"{name} 必須是{'有限' if finite else ''}實數純量；現在是 {value!r}。")
    return v


def _int_scalar(value: Any, name: str, minimum: int = 0) -> int:
    """整數參數（window_length、averages、nfft、nch、n_samples、passed／total）：整數值的實數純量且 ≥ minimum；1000.5 不截斷、
    'a'／None／bool 不收 → DSV:spectralMask:badIntegerArgument。"""
    try:
        v = _real_scalar(value, name, finite=True)
    except MaskError:
        v = math.nan
    if not (math.isfinite(v) and v == math.floor(v) and v >= minimum):
        raise MaskError(_ID_DSV + "badIntegerArgument", f"{name} must be an integer >= {minimum}; got {value!r}.",
                        f"{name} 必須是 ≥ {minimum} 的整數；現在是 {value!r}。")
    return int(v)


def _pair(value: Any, name: str) -> Tuple[float, float]:
    """xlim／ylim：兩個有限且遞增的實數 → (lo, hi)；None／字串／長度不是 2／NaN／±Inf／lo ≥ hi → DSV:spectralMask:badAxisLimits。
    第五輪審查：以前 ±Inf 和反向的範圍都收——scalar_over_xlim／inf_as_axis_limits 時 [-Inf Inf] 或 [500 0] 讓限值全 NaN、測試悄悄通過，
    色塊的 ylim 含 ±Inf 讓多邊形帶 Inf。這是 DSV 自己的檢查（MATLAB 軸界的對應訊息沒探）。"""
    lo = hi = math.nan
    try:
        a = np.asarray(value)
        ok = a.dtype.kind in "iuf" and a.size == 2
    except Exception:
        ok = False
    if ok:
        lo, hi = (float(v) for v in a.ravel())
        ok = math.isfinite(lo) and math.isfinite(hi) and lo < hi
    if not ok:
        raise MaskError(_ID_DSV + "badAxisLimits", f"{name} must be two finite, increasing real numbers [lo, hi]; got {value!r}.",
                        f"{name} 必須是兩個有限且遞增的實數 [下, 上]；現在是 {value!r}。")
    return lo, hi


def validate_mask(value: Any, name: str = "UpperMask") -> Union[float, np.ndarray]:
    """UpperMask／LowerMask 的屬性檢查（MATLAB 驗證過的 33 組案例）：實數純量 → float；N×2（N ≥ 2）矩陣 → (N, 2) ndarray；
    形狀不對 → invalidMaskData；頻率欄有 NaN 或遞減 → invalidMaskFrequencyData；±Inf 頻率、NaN 位準、重複頻率都接受。"""
    a = _numeric_array(value, name)
    if a.size == 1:
        return float(a.reshape(()))
    if a.ndim != 2 or a.shape[1] != 2 or a.shape[0] < 2:
        raise MaskError(_ID_SA + "invalidMaskData",
                        f"The {name} property value must be a real, numeric scalar or two-column matrix with at least two rows.",
                        f"{_mask_word(name)}必須是實數數值純量，或有至少兩列的兩欄矩陣（頻率、位準）。")
    F = a[:, 0]
    # 重複的 ±Inf 頻率：Inf−Inf＝NaN、NaN < 0 為假；跨度超過 realmax（[-1e308 …; 1e308 …]）：diff 溢位成 Inf、Inf < 0 為假
    # → 兩種都照 MATLAB 的非遞減檢查接受，不要 numpy 警告（invalid 與 overflow 都關）
    with np.errstate(invalid="ignore", over="ignore"):
        decreasing = bool((np.diff(F) < 0).any())
    if np.isnan(F).any() or decreasing:
        raise MaskError(_ID_SA + "invalidMaskFrequencyData",
                        f"When the {name} property value is a matrix, the first column representing frequency values of the mask "
                        f"must be non-NaN and non-decreasing.",
                        f"{_mask_word(name)}是矩陣時，第一欄（頻率）不能有 NaN 且必須非遞減。")
    return a.copy()


def validate_reference_level(value: Any) -> float:
    """CustomReferenceLevel：實數純量，Inf 可以、NaN 不行（expectedNonNaN）、向量不行（expectedScalar）。"""
    a = _numeric_array(value, "CustomReferenceLevel")
    if a.size != 1:
        raise _err_scalar("CustomReferenceLevel")
    v = float(a.reshape(()))
    if math.isnan(v):
        raise MaskError("MATLAB:expectedNonNaN", "Expected CustomReferenceLevel to be non-NaN.", "CustomReferenceLevel 不能是 NaN。")
    return v


def validate_channel(value: Any) -> int:
    """SelectedChannel（1 起算）：純量、正（expectedPositive）、整數（expectedInteger）；0／−1 → positive、1.5 → integer。"""
    a = _numeric_array(value, "SelectedChannel")
    if a.size != 1:
        raise _err_scalar("SelectedChannel")
    v = float(a.reshape(()))
    if not v > 0:
        raise MaskError("MATLAB:expectedPositive", "Expected SelectedChannel to be positive.", "SelectedChannel 必須是正數。")
    if not (math.isfinite(v) and v == math.floor(v)):
        raise MaskError("MATLAB:expectedInteger", "Expected SelectedChannel to be integer-valued.", "SelectedChannel 必須是整數。")
    return int(v)


def validate_offset(value: Any) -> float:
    """MaskFrequencyOffset（Hz）：純量（expectedScalar）、有限（expectedFinite：Inf／NaN 都不行）。"""
    a = _numeric_array(value, "MaskFrequencyOffset")
    if a.size != 1:
        raise _err_scalar("MaskFrequencyOffset")
    v = float(a.reshape(()))
    if not math.isfinite(v):
        raise _err_finite("MaskFrequencyOffset")
    return v


def validate_enabled_flag(value: Any) -> bool:
    """Enabled（第 8 個屬性，文件沒寫；MATLAB 的錯誤訊息沒探過 → DSV 自己的 ID）：bool，或 0／1 的純量。"""
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    try:
        a = np.asarray(value)
        if a.dtype.kind in "iuf" and a.size == 1 and float(a.reshape(())) in (0.0, 1.0):
            return bool(float(a.reshape(())))
    except Exception:
        pass
    raise MaskError(_ID_DSV + "invalidEnabled", "Expected Enabled to be a logical scalar.", "Enabled 必須是邏輯純量（true／false）。")


_NUM_RE = re.compile(r"^[+-]?(?:inf|nan|(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?)$", re.I)


def _num(tok: str) -> float:
    t = tok.strip().lower()
    if not _NUM_RE.match(t):
        raise ValueError(tok)
    return float(t)


def parse_mask(text: str, name: str = "UpperMask", num: Optional[Callable[[str], float]] = None,
               level: Optional[Callable[[str], float]] = None, split: Optional[Callable[[str], Sequence[str]]] = None) -> Union[float, np.ndarray]:
    """工具列 Upper／Lower Limits 文字 → 模板值：一個數字（Inf、-Inf、NaN 可），或 [f l; f l; …]（中括號可省、逗號或空白分隔、
    分號或換行分列）。語法／形狀錯誤 → 工具列的 invalidUpperMask／invalidLowerMask；再經 validate_mask（頻率欄檢查）。
    num＝每個數字的解析：回傳 float、看不懂就丟 ValueError；預設 _num（十進位數字與 Inf／-Inf／NaN）。頻譜視窗傳 DSV 的單一數字規則
    （另外收 2k、1.5M 這種 SI 字首；見模組說明）。level＝位準（純量遮罩、矩陣第二欄）的解析，預設和 num 一樣；split＝一列切成數字的方式，
    預設逗號或空白——頻譜視窗傳收 dBr 單位字的解析與把單位字接回前一個數字的切法（使用者 2026-10-26 決定：位準可以寫 dBr）。"""
    conv = num or _num
    lconv = level or conv
    spl = split or (lambda r_: [t for t in re.split(r"[,\s]+", r_) if t])
    s = str(text).strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    rows = [r.strip() for r in re.split(r"[;\n]", s) if r.strip()]
    try:
        toks = [list(spl(r)) for r in rows]
        one = len(toks) == 1 and len(toks[0]) == 1                # 一個數字＝整個頻譜同一個位準
        vals = [[float((lconv if (one or j == 1) else conv)(t)) for j, t in enumerate(r)] for r in toks]
    except (ValueError, TypeError):                       # TypeError：num 回 None 也當看不懂
        raise _toolstrip_mask_error(name) from None
    if not vals:
        raise _toolstrip_mask_error(name)
    if len(vals) == 1 and len(vals[0]) == 1:
        return validate_mask(vals[0][0], name)
    if len(vals) < 2 or any(len(r) != 2 for r in vals):
        raise _toolstrip_mask_error(name)
    return validate_mask(np.array(vals, dtype=float), name)


# JavaScript 的 parseFloat（ECMAScript：TrimString(start) 去掉開頭的 WhiteSpace／LineTerminator，再取最長的 StrDecimalLiteral 前綴）
_JS_SPACE = ("\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
             "\u2028\u2029\u202f\u205f\u3000\ufeff")   # WhiteSpace（TAB VT FF 空白 U+00A0 U+FEFF 與 Zs 類）＋LineTerminator（LF CR U+2028 U+2029）
_JS_FLOAT = re.compile(r"[+-]?(?:Infinity|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)")


def js_parse_float(text: str) -> float:
    """JavaScript 的 parseFloat：略過開頭的空白與換行（TAB、VT、FF、空白、U+00A0、U+FEFF、Unicode Zs 類的空白、LF、CR、U+2028／U+2029），
    取最長的十進位數字前綴（只認 ASCII 數字；'Infinity' 大小寫要對；沒有數字分隔號 _），沒有前綴就是 NaN：'12abc' → 12、' -.5e-3x' → -0.0005、
    '1e' → 1、'1e999' → Infinity、'0x10' → 0、'Inf'／'inf'／'NaN'／''／'   ' → NaN。2026-10-25 用 node 對照過（selftest 的表）。"""
    m = _JS_FLOAT.match(str(text).lstrip(_JS_SPACE))
    if not m:
        return math.nan
    t = m.group(0)
    if t.lstrip("+-") == "Infinity":
        return -math.inf if t.startswith("-") else math.inf
    return float(t)


def toolstrip_parse_float(text: str) -> float:
    """工具列欄位的數字解析（MATLAB 工具列的參考位準、頻率偏移、上限／下限都用它）：
    文字剛好是 "Inf"／"inf" → Infinity、"-Inf"／"-inf" → −Infinity，其他照 JavaScript 的 parseFloat——要一字不差（前後有空白、'INF'、'+Inf' 都不算，
    走 JavaScript 的 parseFloat 得 NaN）。"""
    s = str(text)
    if s in ("Inf", "inf"):
        return math.inf
    if s in ("-Inf", "-inf"):
        return -math.inf
    return js_parse_float(s)


def parse_reference_level(text: str, num: Optional[Callable[[str], float]] = None) -> Optional[Tuple[str, Optional[float]]]:
    """工具列 Reference Level (dBr) 的可編輯下拉，照 MATLAB 工具列：文字是空字串 → None（什麼都不做：設定不變，呼叫端把欄位還原）；
    'Spectrum peak'／'spectrum-peak'／頻譜峰值（前後空白、大小寫不拘）→ ('spectrum-peak', None)；其他 → toolstrip_parse_float：NaN（看不懂、
    只有空白、'NaN'）→ invalidReferenceLevel，否則 ('custom', 值)——'12abc' → 12、'Inf'／'-inf'／'1e999' → ±Inf（欄位不檢查有限；
    屬性 CustomReferenceLevel 照 MATLAB 實測也接受 Inf；見模組說明）。num＝換掉數字的解析（回傳 float，看不懂回 NaN）：頻譜視窗傳 DSV 的
    單一數字規則（'12abc' 是錯、2k＝2000，±Inf 照收）。"""
    s = str(text)
    if s == "":
        return None
    st = s.strip()
    if re.sub(r"[\s_]+", "-", st.lower()) == "spectrum-peak" or st in ("頻譜峰值", "频谱峰值"):
        return "spectrum-peak", None
    v = float((num or toolstrip_parse_float)(s))
    if math.isnan(v):
        raise MaskError(_ID_SA + "invalidReferenceLevel", "Enter reference level as 'Spectrum peak' or as a finite real scalar.",
                        "以「頻譜峰值」或有限實數純量形式輸入參考位準。")
    return "custom", v


def parse_offset(text: str, num: Optional[Callable[[str], float]] = None) -> float:
    """工具列 Frequency Offset (Hz)，照 MATLAB 工具列：toolstrip_parse_float，NaN（空字串、只有空白、看不懂的）→ invalidMaskFrequencyOffset；
    '50abc' → 50、' -50' → −50。±Inf（'Inf'、'1e999'、'Infinity'）欄位本身不擋，之後 MATLAB 怎麼處理
    沒探過：DSV 自行決定照欄位的錯誤文字（finite real scalar）也擋成 invalidMaskFrequencyOffset（屬性 MaskFrequencyOffset 實測也要求有限）。
    num＝換掉數字的解析（回傳 float，看不懂回 NaN）：頻譜視窗傳 DSV 的單一數字規則（'50abc' 是錯、2k＝2000、500m＝0.5）。"""
    v = float((num or toolstrip_parse_float)(text))
    if not math.isfinite(v):
        raise MaskError(_ID_SA + "invalidMaskFrequencyOffset", "Enter spectral mask frequency offset as a finite real scalar.",
                        "以有限實數純量形式輸入頻譜遮罩頻率偏移。")
    return v


class MaskConfig:
    """SpectralMaskConfiguration 的 8 個屬性（名稱照 MATLAB；Enabled 是文件沒寫的第 8 個），設定時照 MATLAB 檢查並正規化。"""

    __slots__ = ("_enabled", "_upper", "_lower", "_ref", "_cref", "_sel", "_mfo", "_on")

    def __init__(self, **kw: Any):
        self._enabled, self._ref, self._cref, self._sel, self._mfo, self._on = "none", "custom", 0.0, 1, 0.0, False
        self._upper: Union[float, np.ndarray] = math.inf
        self._lower: Union[float, np.ndarray] = -math.inf
        for k, v in kw.items():
            if k not in DEFAULTS:                # MATLAB 對不存在屬性的錯誤 ID 沒探過 → DSV 自己的 ID
                raise MaskError(_ID_DSV + "unknownProperty",
                                f"Unrecognized property '{k}' for SpectralMaskConfiguration; valid properties: {', '.join(DEFAULTS)}.",
                                f"SpectralMaskConfiguration 沒有 '{k}' 這個屬性；可用的屬性：{'、'.join(DEFAULTS)}。")
            setattr(self, k, v)

    EnabledMasks = property(lambda s: s._enabled, lambda s, v: setattr(s, "_enabled", normalize_enabled(v)))
    UpperMask = property(lambda s: s._upper, lambda s, v: setattr(s, "_upper", validate_mask(v, "UpperMask")))
    LowerMask = property(lambda s: s._lower, lambda s, v: setattr(s, "_lower", validate_mask(v, "LowerMask")))
    ReferenceLevel = property(lambda s: s._ref, lambda s, v: setattr(s, "_ref", normalize_reference(v)))
    CustomReferenceLevel = property(lambda s: s._cref, lambda s, v: setattr(s, "_cref", validate_reference_level(v)))
    SelectedChannel = property(lambda s: s._sel, lambda s, v: setattr(s, "_sel", validate_channel(v)))
    MaskFrequencyOffset = property(lambda s: s._mfo, lambda s, v: setattr(s, "_mfo", validate_offset(v)))
    Enabled = property(lambda s: s._on, lambda s, v: setattr(s, "_on", validate_enabled_flag(v)))

    @property
    def upper_on(self) -> bool:
        return self._enabled in ("upper", "upper-and-lower")

    @property
    def lower_on(self) -> bool:
        return self._enabled in ("lower", "upper-and-lower")

    def as_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in DEFAULTS}

    def copy(self) -> "MaskConfig":
        return MaskConfig(**self.as_dict())


def _xlim_pair(xlim, f=None) -> Tuple[float, float]:
    """x 軸範圍：有 xlim 就用它（兩個有限、遞增的實數）；沒有就取 f 裡有限值的最小／最大（NaN／±Inf 的 bin 不算，否則 ±Inf 的軸界讓限值全 NaN）；
    f 也沒有可用的值（None、空、沒有有限值）→ needXLimits（不要 np.nanmin 的 All-NaN 警告）。"""
    if xlim is not None:
        return _pair(xlim, "xlim")
    ff = np.asarray(f, dtype=float).ravel() if f is not None else np.zeros(0)
    ff = ff[np.isfinite(ff)]
    if ff.size == 0:
        raise MaskError(_ID_DSV + "needXLimits",
                        "A scalar mask limited to the x-axis (or ±Inf breakpoints taken as the axis ends) needs the axis limits (xlim); "
                        "f has no finite frequency to derive them from.",
                        "純量遮罩要限制在 x 軸範圍（或 ±Inf 斷點要當軸界）時需要 xlim；f 裡沒有有限的頻率可以推。")
    return float(ff.min()), float(ff.max())


def mask_breakpoints(mask, mfo: float = 0.0, xlim=None, inf_as_axis_limits: bool = False, f=None,
                     name: str = "Mask") -> Tuple[np.ndarray, np.ndarray]:
    """矩陣模板實際測試用的斷點表 (F, P)（實測）：F＝頻率＋MaskFrequencyOffset、P＝位準，F(i) 和前一個原始值相等就加 realmin
    （只在 0 Hz 有作用）。純量模板（只在 scalar_over_xlim 時會走到這裡）→ F＝[xlim₁, xlim₂]、P＝[m, m]，不加偏移。
    inf_as_axis_limits=True（**非分析器行為**，實測 8/8 不符）：先把 ±Inf 頻率換成 xlim 再加偏移。mfo 就是 MaskFrequencyOffset，
    照屬性檢查（有限實數純量，MATLAB 的 ID）。"""
    m = validate_mask(mask, name)
    mfo = validate_offset(mfo)
    if not isinstance(m, np.ndarray):
        lo, hi = _xlim_pair(xlim, f)
        return np.array([lo, hi]), np.array([m, m])
    Fi = m[:, 0].copy()
    if inf_as_axis_limits and np.isinf(Fi).any():
        lo, hi = _xlim_pair(xlim, f)
        Fi = np.where(Fi == -np.inf, lo, np.where(Fi == np.inf, hi, Fi))
    with np.errstate(over="ignore"):         # 極端值（1e308＋1e308 → Inf）照 IEEE 給 Inf，不要 numpy 警告
        Fo = Fi + mfo
    F = Fo.copy()
    same = Fo[1:] == Fo[:-1]
    F[1:][same] += REALMIN
    return F, m[:, 1].copy()


def mask_limits(mask, f, xlim=None, mfo: float = 0.0, inf_as_axis_limits: bool = False, scalar_over_xlim: bool = False,
                name: str = "Mask") -> np.ndarray:
    """每個顯示頻率 f 的模板限值（還沒加參考位準）。
    純量模板（實測）：所有 bin 都是那個常數，和 x 軸範圍無關；scalar_over_xlim=True（**非分析器行為**）才改成只蓋 xlim、外面 NaN。
    矩陣模板（實測）：範圍外 NaN；範圍內取第一個 x ≤ F(j) 的段 (j−1, j) 線性內插，斜率 NaN 當 0 → 垂直階梯處左連續、
    NaN 位準那段 NaN、左斷點 −Inf 那段 NaN（inf_as_axis_limits=False 時）。回傳和 f 同形狀。"""
    x = _real_data(f, "f")
    m = validate_mask(mask, name)
    mfo = validate_offset(mfo)
    if not isinstance(m, np.ndarray) and not scalar_over_xlim:
        return np.full(x.shape, m)
    F, P = mask_breakpoints(m, mfo, xlim, inf_as_axis_limits, x, name)
    lim = np.full(x.shape, np.nan)
    with np.errstate(invalid="ignore"):
        inside = (x >= F[0]) & (x <= F[-1])
    if not inside.any():
        return lim
    xi = x[inside]
    j = np.maximum(np.searchsorted(F, xi, side="left"), 1)
    a, b, pa, pb = F[j - 1], F[j], P[j - 1], P[j]
    # 垂直階梯在 0 Hz（[0 a; 0 b; …]）：b−a＝realmin → 斜率溢位成 Inf，0·Inf＝NaN → 那個 bin 不測（和推定的規則一致）；要把 overflow 也關掉
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        s = (pb - pa) / (b - a)
        s = np.where(np.isnan(s), 0.0, s)
        lim[inside] = pa + (xi - a) * s
    return lim


def spectrum_peak(S) -> float:
    """spectrum-peak 參考位準：所選通道這次頻譜所有 bin 的最大值（實測：同一個值給所有通道、每次更新重算）。
    NaN 的處理照推定的規則（未定）：從第 1 個 bin 起只在「目前 < 下一個」時更新 → 第 1 個 bin 是 NaN 就一直是 NaN，其他 NaN 略過；空陣列 NaN。"""
    v = _real_data(S, "spectra").ravel()
    if v.size == 0 or np.isnan(v[0]) or np.isnan(v).all():
        return math.nan
    return float(np.nanmax(v))


def _channel_list(channels: Any, name: str = "FailingChannels") -> List[int]:
    """通道清單（1 起算）：list／tuple／一維數值陣列，元素是 1..2^24 的整數值（1.0 可；1.5、'a'、True、NaN、Inf、1e300 不收，[1, True] 的 True
    也不收；上限＝MAX_ELEMENTS，因為限值陣列 通道 × bin ≤ 2^24，通道號碼不可能更大——第五輪審查：以前 [1e300] 回 301 位數的 int）、
    長度 ≤ 2^24 → List[int]；否則 DSV:spectralMask:badFailingChannels（不要漏 int()／len() 的 ValueError／TypeError：
    0-d 陣列 np.array(5) 沒有 len()，先看 ndim）。"""
    if isinstance(channels, np.ndarray):
        ok = channels.ndim == 1 and channels.size <= MAX_ELEMENTS
    elif isinstance(channels, (list, tuple)):
        ok = len(channels) <= MAX_ELEMENTS and not any(
            isinstance(v, (bool, np.bool_)) or (isinstance(v, np.ndarray) and v.dtype.kind == "b") for v in channels)
    else:
        ok = False
    a = np.zeros(0)
    if ok:
        try:
            a = np.asarray(channels)
        except Exception:
            ok = False
    if ok and a.size:
        ok = a.ndim == 1 and a.dtype.kind in "iuf"
        if ok:
            with np.errstate(invalid="ignore"):
                ok = bool((np.isfinite(a) & (a >= 1) & (a <= MAX_ELEMENTS) & (a == np.floor(a))).all())
    elif ok:
        ok = a.ndim == 1
    if not ok:
        raise MaskError(_ID_DSV + "badFailingChannels",
                        f"{name} must be a list of channel numbers (integers 1..{MAX_ELEMENTS}, at most {MAX_ELEMENTS} of them); got {channels!r:.80}.",
                        f"{name} 必須是通道號碼（1..{MAX_ELEMENTS} 的整數，最多 {MAX_ELEMENTS} 個）的清單；現在是 {channels!r:.80}。")
    return [int(v) for v in a.tolist()]


def failing_channels_matlab(channels: Sequence[int]) -> Any:
    """FailingChannels 的 MATLAB 形狀（實測）：一個通道 → 純量 int；多個 → list；沒有 → []（1×0）。
    channels 不是 ≥ 1 整數的清單（['a']、[1.5]、[True]、[1, True]、5、np.array(5)、'12'）→ badFailingChannels。"""
    ch = _channel_list(channels)
    return ch[0] if len(ch) == 1 else ch


def success_rate(passed: int, total: int) -> float:
    """SuccessRate（實測）：passed / total × 100，先除再乘（11/40 → 27.500000000000004、2/3 → 66.66666666666666）；total 0 → NaN；
    passed > total（分析器不可能產生）→ DSV:spectralMask:badCounts（第五輪審查：以前 success_rate(3, 2) 回 150.0）。"""
    p, t = _int_scalar(passed, "passed", 0), _int_scalar(total, "total", 0)
    if p > t:
        raise MaskError(_ID_DSV + "badCounts", f"passed ({p}) must not exceed total ({t}).", f"passed（{p}）不能大於 total（{t}）。")
    return p / t * 100.0 if t else math.nan


def _sample_rate(fs) -> float:
    """fs 必須是有限正數的實數純量（DSV 自己的檢查；MATLAB 的 SampleRate 也要求 positive finite，訊息沒探過 → DSV 自己的 ID）；
    bool（True 不是 1 Hz）、字串（'1000'）、None 都不收。"""
    try:
        v = _real_scalar(fs, "fs", finite=True)
    except MaskError:
        v = math.nan
    if not (math.isfinite(v) and v > 0):
        raise MaskError(_ID_DSV + "badSampleRate", f"Sample rate must be a finite positive scalar; got {fs!r}.",
                        f"取樣率必須是有限正數；現在是 {fs!r}。")
    return v


def simulation_time(prev: Optional[float], n_samples: int, fs: float) -> float:
    """SimulationTime：最後一個處理樣本的時間，每次呼叫 t＝t_prev＋n/fs，release 後 t_prev＝−1/fs（實測 getSpectrumData 的
    SimulationTime 88 次呼叫全部相同：4000 樣本 @ 1 kHz → 3.999、7.9990000000000006、11.999、15.999）。
    fs 不是有限正數 → badSampleRate；prev 不是 None 或有限實數 → badScalarArgument；n_samples 不是 ≥ 0 的整數（4000.7 不截斷）→ badIntegerArgument。"""
    fs = _sample_rate(fs)
    n = _int_scalar(n_samples, "n_samples", 0)
    t0 = -1.0 / fs if prev is None else _real_scalar(prev, "prev", finite=True)
    return t0 + n / fs


def mask_test(spectra, lim_up: Optional[np.ndarray], lim_lo: Optional[np.ndarray], ref: float) -> Dict[str, Any]:
    """一次測試（無狀態；實測）。spectra (nch, nbins) 的 dB 值；lim_up／lim_lo 是 (nch, nbins)（或 (nbins,)，每通道相同）的限值，
    None＝該模板沒開；形狀不合 → shapeMismatch。ref＝參考位準（實數純量；spectrum_peak 給的 NaN、CustomReferenceLevel 的 Inf 都可以）。
    上模板失敗＝任一 bin S > 限值＋ref、下模板失敗＝任一 bin S < 限值＋ref（嚴格、NaN 為假）。
    回傳 passing、upper_status／lower_status（沒有通道在該模板失敗；沒開也是 True）、failing_channels（1 起算）、
    n_fail_upper／n_fail_lower（每個通道失敗的 bin 數）、reference，以及每通道的 upper_max_excess＝max(S−(上限＋ref))、
    lower_min_margin＝min(S−(下限＋ref))（dB；> 0／< 0 就是失敗；該模板沒開、沒有 bin 或差值沒有一個有限 → NaN；和分析報告
    analyze_mask.py 的 upper_max_excess_dB／lower_min_margin_dB 同定義，selftest 對 84 次實測呼叫比）。"""
    S = np.atleast_2d(_real_data(spectra, "spectra"))
    if S.ndim != 2:
        raise MaskError(_ID_DSV + "shapeMismatch", f"spectra must be (channels, bins); got {S.shape}.",
                        f"spectra 必須是 (通道, bin)；現在是 {S.shape}。")
    nch, nb = S.shape
    r = _real_scalar(ref, "ref")

    def lim_array(lim, name):
        if lim is None:
            return None
        L = _real_data(lim, name)
        if L.ndim == 1 and L.size == nb:
            return np.broadcast_to(L, (nch, nb))
        if L.shape != (nch, nb):
            raise MaskError(_ID_DSV + "shapeMismatch", f"{name} must have shape {(nch, nb)} (channels, bins) or ({nb},); got {L.shape}.",
                            f"{name} 的形狀必須是 {(nch, nb)}（通道, bin）或 ({nb},)；現在是 {L.shape}。")
        return L

    LU, LL = lim_array(lim_up, "lim_up"), lim_array(lim_lo, "lim_lo")
    n_up = np.zeros(nch, dtype=int)
    n_lo = np.zeros(nch, dtype=int)
    ex_up = np.full(nch, np.nan)
    mg_lo = np.full(nch, np.nan)
    with np.errstate(invalid="ignore", over="ignore"):     # 限值＋ref 的極端值溢位成 ±Inf → 永遠不會失敗，不要 numpy 警告
        if LU is not None:
            lim = LU + r
            n_up = (S > lim).sum(axis=1)
            if nb:
                d = S - lim
                ex_up = np.where(np.isfinite(d).any(axis=1), np.where(np.isnan(d), -np.inf, d).max(axis=1), np.nan)
        if LL is not None:
            lim = LL + r
            n_lo = (S < lim).sum(axis=1)
            if nb:
                d = S - lim
                mg_lo = np.where(np.isfinite(d).any(axis=1), np.where(np.isnan(d), np.inf, d).min(axis=1), np.nan)
    fail_up, fail_lo = n_up > 0, n_lo > 0
    fail = fail_up | fail_lo
    return {"passing": bool(not fail.any()), "upper_status": bool(not fail_up.any()), "lower_status": bool(not fail_lo.any()),
            "failing_channels": (np.nonzero(fail)[0] + 1).tolist(), "n_fail_upper": n_up.tolist(), "n_fail_lower": n_lo.tolist(),
            "reference": r, "upper_max_excess": ex_up.tolist(), "lower_min_margin": mg_lo.tolist()}


def _failing_masks_doc(up_ok: bool, lo_ok: bool) -> str:
    return {(True, True): "none", (False, True): "upper", (True, False): "lower", (False, False): "upper-and-lower"}[(up_ok, lo_ok)]


class MaskTester:
    """推定的遮罩測試規則加上分析器實測的計數行為：設定（MaskConfig，可隨時換）＋計數器（passed、total）＋上一次狀態。
    每次 test() 是一次測試（分析器的一次顯示頻譜更新）。計數器跨設定變更、reset()、release() 都不清（實測），只有 clear()
    （DSV 的「換新 scope 物件」）清。scalar_over_xlim／inf_as_axis_limits 是**非分析器行為**的備用旗標（見模組說明）。"""

    def __init__(self, config: Optional[MaskConfig] = None, scalar_over_xlim: bool = False, inf_as_axis_limits: bool = False):
        self.config = config if config is not None else MaskConfig()
        self._cfg()
        self.scalar_over_xlim = scalar_over_xlim
        self.inf_as_axis_limits = inf_as_axis_limits
        self.passed = 0
        self.total = 0
        self.status: Optional[Dict[str, Any]] = None      # 上一次測試的狀態（getSpectralMaskStatus）；第一次測試前 None（MATLAB []）
        self._last_pass = False

    def _cfg(self) -> MaskConfig:
        """config 必須是 MaskConfig（可以隨時換一個；其他東西 → badConfig，不要之後漏 AttributeError）。"""
        c = self.config
        if not isinstance(c, MaskConfig):
            raise MaskError(_ID_DSV + "badConfig", f"MaskTester.config must be a MaskConfig; got {type(c).__name__}.",
                            f"MaskTester.config 必須是 MaskConfig；現在是 {type(c).__name__}。")
        return c

    def clear(self) -> None:
        """DSV 專用：計數器與狀態歸零（等於 MATLAB 新建一個 scope 物件）。"""
        self.passed, self.total, self.status, self._last_pass = 0, 0, None, False

    def reset(self) -> Optional[Dict[str, Any]]:
        """MATLAB reset(sa)：實測**不**清計數器、狀態也不變（14/56 前後相同）。回傳目前狀態。"""
        return self.status

    def release(self) -> Optional[Dict[str, Any]]:
        """MATLAB release(sa)：計數器不清（實測）；頻譜平均的歷史由頻譜那邊（scope_spectra 的新呼叫序列）重來。回傳目前狀態。"""
        return self.status

    @property
    def success_rate(self) -> float:
        return success_rate(self.passed, self.total)

    @property
    def last(self) -> Optional[Dict[str, Any]]:
        """舊名（第一輪）：＝status。"""
        return self.status

    def status_matlab(self) -> Optional[Dict[str, Any]]:
        """getSpectralMaskStatus 的 7 個欄位（FailingChannels 用 MATLAB 形狀）；第一次測試前 None（MATLAB 回傳 []）。"""
        st = self.status
        if st is None:
            return None
        out = {k: st[k] for k in STATUS_FIELDS}
        out["FailingChannels"] = failing_channels_matlab(st["FailingChannels"])
        return out

    def limits(self, f, xlim=None, nch: int = 1, foffset=0.0) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """每個通道、每個 bin 的上／下限值 (nch, nbins)（沒加參考位準；沒開的模板給 None）。f＝顯示頻率（bin 頻率，已含 scope 的
        FrequencyOffset；或給 foffset 純量／每通道一個加上去），xlim 只在 scalar_over_xlim／inf_as_axis_limits 時用到。
        f 必須是一維（shapeMismatch）；nch 必須是整數值（1.5／'a'／None → badIntegerArgument，不截斷）且 ≥ 1（noChannels）；
        nch × max(bin 數, 1) > 2^24 → tooLarge（f 空也擋，不跑無上限的工作）；xlim 不是 None 就要是兩個非 NaN 實數（badAxisLimits，
        不論旗標）。所有通道一次向量化算完：foffset 全部相同 → 算一列再複製；不同 → (nch, nbins) 的顯示頻率一次算。旗標開著又沒給
        xlim 時，x 軸範圍取所有通道顯示頻率的最小／最大（共用一條 x 軸；見模組說明）。"""
        f = _real_data(f, "f")
        if f.ndim != 1:
            raise MaskError(_ID_DSV + "shapeMismatch", f"f must be a 1-D vector of bin frequencies; got shape {f.shape}.",
                            f"f 必須是一維的 bin 頻率向量；現在的形狀是 {f.shape}。")
        nch = _int_scalar(nch, "nch", 0)
        if nch < 1:
            raise MaskError(_ID_DSV + "noChannels", "At least one channel is needed.", "至少要有一個通道。")
        if nch * max(f.size, 1) > MAX_ELEMENTS:   # f 空時也算一個元素：limits(np.zeros(0), None, 10**9) 以前是 10^9 次迴圈
            raise MaskError(_ID_DSV + "tooLarge", f"Mask limits would need {nch} x {f.size} elements (DSV limit {MAX_ELEMENTS}).",
                            f"遮罩限值需要 {nch} × {f.size} 個元素，超過 DSV 的上限 {MAX_ELEMENTS}。")
        if xlim is not None:
            xlim = _pair(xlim, "xlim")
        off = self._offsets(foffset, nch)
        c = self._cfg()
        same = bool((off == off[0]).all())       # 偏移都有限（_offsets 擋掉 NaN／Inf），全部相同就只算一列
        with np.errstate(over="ignore", invalid="ignore"):   # 1e308＋1e308、Inf＋(−Inf) 照 IEEE，不要 numpy 警告
            x = f + off[0] if same else f[None, :] + off[:, None]
        out: List[Optional[np.ndarray]] = []
        for mask, on, name in ((c.UpperMask, c.upper_on, "UpperMask"), (c.LowerMask, c.lower_on, "LowerMask")):
            if not on:
                out.append(None)
                continue
            L = mask_limits(mask, x, xlim, c.MaskFrequencyOffset, self.inf_as_axis_limits, self.scalar_over_xlim, name)
            out.append(np.repeat(L[None, :], nch, axis=0) if same else L)
        return out[0], out[1]

    @staticmethod
    def _offsets(foffset, nch: int) -> np.ndarray:
        """foffset＝scope 的 FrequencyOffset，ID 與英文文字照 R2025a spectrumAnalyzer 設 sa.FrequencyOffset 的實測（第五輪審查
        probe_r5_offset.m／.json，15 組，selftest 逐筆比；見模組說明）：型別（MATLAB:invalidType「Expected FrequencyOffset to be one of these
        types:\\n\\ndouble」，logical 再加「Instead its type was logical.」）、實數（expectedReal）、[] → expectedVector「Expected FrequencyOffset
        to be a vector.」（0 個通道時 DSV 照收，MATLAB 沒有 0 通道）、每個值有限（expectedFinite「Expected FrequencyOffset to be finite.」），
        而且是純量或每通道一個（DSV 自己的長度檢查 badFrequencyOffset，不要讓 numpy 的 broadcast 錯誤漏出去）→ (nch,) 陣列（唯讀 view）。
        已知差異：numpy float32／int32 純量照收（scope 丟 invalidType）。以前 NaN／Inf 的 foffset 直接進限值計算（限值全 NaN → 測試悄悄通過）；
        第六輪前型別錯的文字是屬性的 10 種型別那串（ID 對、文字不是 scope 的）。"""
        off, vec = _offset_values(foffset)
        if off.size == 0 and nch != 0 and not vec:    # MATLAB 的 []（0×0）→ expectedVector；zeros(1,0)／zeros(0,1) 是向量 → 下面 DSV 的個數檢查
            raise _err_offset_vector()
        if not np.isfinite(off).all():
            raise _err_finite("FrequencyOffset")
        if off.size not in (1, nch):                 # 含 zeros(1,0)／zeros(0,1) 配 ≥ 1 個通道（MATLAB 接受賦值但 listener 立刻出錯；第七輪審查）
            raise MaskError(_ID_DSV + "badFrequencyOffset",
                            f"foffset must be a scalar or one value per channel ({nch}); got {off.size} values.",
                            f"foffset 必須是純量或每個通道一個值（{nch} 個）；現在是 {off.size} 個。")
        return np.broadcast_to(off, (nch,))

    def test(self, f, spectra, xlim=None, foffset=0.0, time: Optional[float] = None, replace_last: bool = False) -> Dict[str, Any]:
        """一次測試並更新計數。spectra＝每個通道一條 dB 軌跡（(nch, nbins) 或 1-D）；f＝顯示頻率；time＝這次更新的 SimulationTime
        （呼叫端給，見 simulation_time()）。回傳狀態 dict（＝之後的 .status）：
        MATLAB 欄位 IsCurrentlyPassing、NumPassedTests、NumTotalTests、SuccessRate、FailingMasks（''／'Upper and lower'）、
        FailingChannels（list，1 起算）、SimulationTime；加上 tested、reference（這次用的參考位準 dB，畫色塊用）、passing、current_status、
        upper_status／lower_status（True／False，沒開是 None）、upper_enabled／lower_enabled、failing_masks_doc（文件用詞，分析器
        不會回傳）、event（MaskTestFailed）、n_fail_upper／n_fail_lower、upper_excess_dB／lower_margin_dB（每通道 max(S−上限−ref)／
        min(S−下限−ref)，沒開 NaN；見 mask_test）、passed／total／success_rate（別名）。
        EnabledMasks＝none（實測）：不測、計數凍結，回傳上一次的狀態（tested=False；還沒測過就只有 tested=False）；沒有 bin（f 長度 0，
        MATLAB 不會產生）也一樣不測（自行決定）。
        參數檢查（不測的時候也做，0 個通道也做）：time 是 None 或有限實數純量（badScalarArgument；存成 float）、xlim 是 None 或兩個
        非 NaN 實數（badAxisLimits）、foffset 照 scope 的 FrequencyOffset（MATLAB:invalidType／expectedReal／expectedVector／expectedFinite，
        見 _offsets）且是純量或每通道一個（badFrequencyOffset）、replace_last 是 bool（badFlag）。"""
        c = self._cfg()
        f = _real_data(f, "f")
        S = np.atleast_2d(_real_data(spectra, "spectra"))
        if f.ndim != 1 or S.ndim != 2 or S.shape[1] != f.size:
            raise MaskError(_ID_DSV + "shapeMismatch",
                            f"spectra must be (channels, bins) with bins = numel(f) = {f.size}; got {S.shape}.",
                            f"spectra 必須是 (通道, bin) 且 bin 數＝f 的長度 {f.size}；現在是 {S.shape}。")
        nch = S.shape[0]
        if xlim is not None:
            xlim = _pair(xlim, "xlim")
        if time is not None:
            time = _real_scalar(time, "time", finite=True)
        if not isinstance(replace_last, (bool, np.bool_)):
            raise MaskError(_ID_DSV + "badFlag", f"replace_last must be True or False; got {replace_last!r}.",
                            f"replace_last 必須是 True 或 False；現在是 {replace_last!r}。")
        replace_last = bool(replace_last)
        self._offsets(foffset, nch)              # 0 個通道也檢查（純量或空；'abc' → MATLAB:invalidType，scope 的文字）
        if not (c.upper_on or c.lower_on) or f.size == 0:
            out: Dict[str, Any] = dict(self.status) if self.status is not None else {}
            out["tested"] = False
            return out
        if c.ReferenceLevel == "spectrum-peak":
            if c.SelectedChannel > nch:
                raise MaskError(_ID_SA + "invalidMaskChannelNumber",
                                f"Mask selected channel must be less than or equal to the total number of input channels to the scope, {nch}.",
                                f"遮罩選取的通道必須小於或等於輸入通道數 {nch}。")
            ref = spectrum_peak(S[c.SelectedChannel - 1])
        else:
            ref = c.CustomReferenceLevel
        lim_up, lim_lo = self.limits(f, xlim, nch, foffset)
        r = mask_test(S, lim_up, lim_lo, ref)
        ok = r["passing"]
        if replace_last:
            prev = int(self._last_pass) if self.passed > 0 else 0
            self.passed = self.passed - prev + int(ok)
            self.total = max(self.total, 1)
        else:
            self.total += 1
            self.passed += int(ok)
        self._last_pass = ok
        st: Dict[str, Any] = {
            "IsCurrentlyPassing": ok, "NumPassedTests": self.passed, "NumTotalTests": self.total, "SuccessRate": self.success_rate,
            "FailingMasks": FAILING_MASKS[0 if ok else 1], "FailingChannels": r["failing_channels"], "SimulationTime": time,
            "tested": True, "reference": r["reference"], "passing": ok, "current_status": "passing" if ok else "failing",
            "upper_status": r["upper_status"] if c.upper_on else None, "lower_status": r["lower_status"] if c.lower_on else None,
            "upper_enabled": c.upper_on, "lower_enabled": c.lower_on,
            "failing_masks_doc": _failing_masks_doc(r["upper_status"], r["lower_status"]), "event": not ok,
            "n_fail_upper": r["n_fail_upper"], "n_fail_lower": r["n_fail_lower"],
            "upper_excess_dB": r["upper_max_excess"], "lower_margin_dB": r["lower_min_margin"],
            "failing_channels": r["failing_channels"], "passed": self.passed, "total": self.total, "success_rate": self.success_rate,
        }
        self.status = st
        return dict(st)


def panel_row(status: Optional[Dict[str, Any]], lang: str = "en", labels: Optional[Sequence[str]] = None) -> Tuple[Any, ...]:
    """面板那一列的 7 個值（PANEL_COLUMNS 順序）：成功率、通過數、總數、目前狀態、上遮罩狀態、下遮罩狀態（沒開「--」）、
    失敗的通道（逗號分隔的通道標籤；labels 沒給就用 1 起算的號碼）。status 是 None 或這次沒測（none）→ PANEL_EMPTY_ROW（面板關掉）；
    status 不是 None 或 dict、缺欄位、欄位型別不對（tested／IsCurrentlyPassing 不是 bool、upper_status／lower_status 不是 bool 或 None、
    NumPassedTests／NumTotalTests 不是非負整數、SuccessRate 不是實數純量、FailingChannels 不是 ≥ 1 整數的清單）→ badStatus；
    labels 不是 None 或字串的 list／tuple → badLabels（status 是 None 或沒測時也檢查）。"""
    def bad(why_en: str, why_zh: str) -> MaskError:
        return MaskError(_ID_DSV + "badStatus", f"status {why_en}; pass None or the dict returned by MaskTester.test().",
                         f"status {why_zh}；請傳 None 或 MaskTester.test() 回傳的 dict。")

    def is_bool(v: Any) -> bool:
        return isinstance(v, (bool, np.bool_))

    if labels is not None and not (isinstance(labels, (list, tuple)) and all(isinstance(s, str) for s in labels)):
        raise MaskError(_ID_DSV + "badLabels", f"labels must be None or a list of channel-name strings; got {labels!r:.60}.",
                        f"labels 必須是 None 或通道名稱字串的 list；現在是 {labels!r:.60}。")
    if status is None:
        return PANEL_EMPTY_ROW
    if not isinstance(status, dict):
        raise bad(f"is a {type(status).__name__}, not a dict", f"是 {type(status).__name__}，不是 dict")
    tested = status.get("tested", False)
    if not is_bool(tested):
        raise bad(f"field 'tested' must be a bool; got {tested!r:.40}", f"的 'tested' 必須是 bool；現在是 {tested!r:.40}")
    if not tested:
        return PANEL_EMPTY_ROW
    missing = [k for k in ("SuccessRate", "NumPassedTests", "NumTotalTests", "IsCurrentlyPassing", "upper_status", "lower_status")
               if k not in status]
    if missing:
        raise bad(f"is missing {missing}", f"缺少 {missing}")
    for k in ("IsCurrentlyPassing", "upper_status", "lower_status"):
        v = status[k]
        if not (is_bool(v) or (v is None and k != "IsCurrentlyPassing")):
            want = "a bool" if k == "IsCurrentlyPassing" else "a bool or None"
            raise bad(f"field '{k}' must be {want}; got {v!r:.40}", f"的 '{k}' 必須是 {'bool' if k == 'IsCurrentlyPassing' else 'bool 或 None'}；現在是 {v!r:.40}")
    counts = []
    for k in ("NumPassedTests", "NumTotalTests"):
        try:
            counts.append(_int_scalar(status[k], k, 0))
        except MaskError:
            raise bad(f"field '{k}' must be an integer >= 0; got {status[k]!r:.40}",
                      f"的 '{k}' 必須是 ≥ 0 的整數；現在是 {status[k]!r:.40}") from None
    if counts[0] > counts[1]:                    # 第五輪審查：以前 NumPassedTests 3 > NumTotalTests 2 照印
        raise bad(f"has NumPassedTests {counts[0]} > NumTotalTests {counts[1]}", f"的 NumPassedTests {counts[0]} 大於 NumTotalTests {counts[1]}")
    try:
        rate = _real_scalar(status["SuccessRate"], "SuccessRate")
    except MaskError:
        raise bad(f"field 'SuccessRate' must be a real scalar; got {status['SuccessRate']!r:.40}",
                  f"的 'SuccessRate' 必須是實數純量；現在是 {status['SuccessRate']!r:.40}") from None
    try:
        ch = _channel_list(status.get("FailingChannels", []))
    except MaskError as ex:
        raise bad(f"field 'FailingChannels' is invalid ({ex.message})", f"的 'FailingChannels' 不對（{ex.message_zh}）") from None
    w = STATUS_WORDS["zh" if str(lang).lower().startswith("zh") else "en"]
    names = [labels[i - 1] if labels is not None and i <= len(labels) else str(i) for i in ch]
    return (rate, counts[0], counts[1], w[bool(status["IsCurrentlyPassing"])],
            w[None if status["upper_status"] is None else bool(status["upper_status"])],
            w[None if status["lower_status"] is None else bool(status["lower_status"])], ", ".join(names))


def mask_polyline(mask, kind: str, xlim, ylim, mfo: float = 0.0, ref: float = 0.0) -> Dict[str, Any]:
    """畫色塊用的折線（MATLAB 介面的畫法）：純量 → 畫滿 xlim、不加偏移（測試仍是整張頻譜）；矩陣 → ±Inf 頻率放到 xlim 兩端再加
    MaskFrequencyOffset；y＝位準＋ref（spectrum-peak 時 ref＝峰值）；上模板的遠邊 edge＝max(ylim₂, 最大 y)、下模板＝min(ylim₁, 最小 y)，
    但只要有一個 y 是 NaN，edge 就是 ylim₂（下模板 ylim₁），NaN 那幾點也畫在 edge
    （有 NaN 時最大位準是 NaN，遠邊退回軸界；下模板用最小位準與 ylim₁）。
    ±Inf 位準（例如預設的 Inf 上模板）這裡夾到 edge／對面的軸界（自行決定，讓 matplotlib 畫得出來；MATLAB 的遠邊會是 ±Inf）。
    回傳 x、y（已夾）、y_raw、edge、polygon（(2n, 2)：沿線去、沿 edge 回）。
    kind 只能是 'upper'／'lower'（badMaskKind）；xlim／ylim 兩個非 NaN 實數（badAxisLimits）；mfo 照 MaskFrequencyOffset 檢查；ref 實數純量。"""
    if not isinstance(kind, str) or kind.lower() not in ("upper", "lower"):
        raise MaskError(_ID_DSV + "badMaskKind", f"kind must be 'upper' or 'lower'; got {kind!r}.", f"kind 必須是 'upper' 或 'lower'；現在是 {kind!r}。")
    kind = kind.lower()
    m = validate_mask(mask, PATCH_LABELS[kind].replace(" ", ""))
    lo, hi = _pair(xlim, "xlim")
    ylo, yhi = _pair(ylim, "ylim")
    mfo = validate_offset(mfo)
    ref = _real_scalar(ref, "ref")
    if not isinstance(m, np.ndarray):
        x = np.array([lo, hi])
        y = np.full(2, m)
    else:
        with np.errstate(over="ignore"):
            x = np.where(m[:, 0] == -np.inf, lo, np.where(m[:, 0] == np.inf, hi, m[:, 0])) + mfo
        y = m[:, 1].copy()
    with np.errstate(invalid="ignore", over="ignore"):
        y_raw = y + ref
    fin = y_raw[np.isfinite(y_raw)]
    plain = fin.size > 0 and not np.isnan(y_raw).any()      # 有 NaN 時最大／最小位準是 NaN → 遠邊用軸界
    if kind == "upper":
        edge = max(yhi, float(fin.max())) if plain else yhi
        far = ylo
        yy = np.where(np.isnan(y_raw) | (y_raw == np.inf), edge, np.where(y_raw == -np.inf, far, y_raw))
    else:
        edge = min(ylo, float(fin.min())) if plain else ylo
        far = yhi
        yy = np.where(np.isnan(y_raw) | (y_raw == -np.inf), edge, np.where(y_raw == np.inf, far, y_raw))
    poly = np.concatenate([np.column_stack([x, yy]), np.column_stack([x[::-1], np.full(x.size, edge)])])
    return {"x": x, "y": yy, "y_raw": y_raw, "edge": edge, "polygon": poly, "label": PATCH_LABELS[kind]}


def nfft_auto(window_length: int) -> int:
    """FFTLengthSource auto 的 NFFT＝max(1024, WindowLength)（實測 8 種 WindowLength：1000→1024、1024、1999、2000、2048、4000、
    4096、8192 都＝自己；見模組說明「NFFT 的資料點」，selftest 逐筆核對擷取的頻率格）。"""
    return max(1024, _int_scalar(window_length, "window_length", 1))


def scope_spectra(calls: Sequence[Any], fs: float, window_length: int, averages: int = 1, two_sided: bool = False,
                  nfft: Optional[int] = None, foffset: float = 0.0) -> Tuple[np.ndarray, List[Optional[np.ndarray]]]:
    """分析器實測的頻譜模型（模板測的那張；dBm、ReferenceLoad 1、Hann periodic、OverlapPercent 0、'power'）。
    calls＝一串輸入呼叫，每個是 (n, nch)（或 1-D）的實數或複數陣列，像 MATLAB 連續呼叫 sa(x) 一樣；回傳 (f, [S_k])：
    f＝顯示頻率（含 foffset＝scope 的 FrequencyOffset），S_k＝第 k 次呼叫後的顯示頻譜 (nbins, nch)，用 release() 以來所有段
    週期圖的正規化指數平均（λ＝(N−1)/(N+1)，N＝averages）；呼叫不足一個視窗 → None（沒有新頻譜）；多出的尾數捨去（未定）。
    單邊只給實數訊號；複數或 two_sided → 雙邊置中（Nyquist 在正的那端）。NFFT 預設 nfft_auto()；超過 MAX_ELEMENTS 丟錯。
    參數檢查（DSV 自己的 ID）：fs 有限正數（badSampleRate；bool／字串不收）、window_length／averages ≥ 1 且 nfft ≥ 1 的整數值
    （badIntegerArgument）、foffset 照 scope 的 FrequencyOffset 實測（型別 MATLAB:invalidType、複數 expectedReal、[] expectedVector、
    NaN／±Inf expectedFinite；見 MaskTester._offsets）而且只能一個值（多個 → DSV 的 badScalarArgument：一條頻率格只配一個偏移）、
    two_sided 是 bool（badFlag）、calls 是 list／tuple 且每個都是
    數值陣列（badCalls）、每次呼叫 ≥ 1 個通道（shapeMismatch）；通道數與實數／複數由第一次呼叫定下，之後的呼叫不同 →
    inputSpecChanged（不論 averages；MATLAB 對應行為沒探過，見模組說明）。
    極端樣本不警告：|x| ≳ 1e155 的 |FFT|² 溢位成 Inf dBm、Inf 樣本給 NaN 頻譜（IEEE；welch 包在 errstate 裡）；N＝1（λ＝0）每次直接取
    該段週期圖（不算 0·前一段，前一段的 Inf／NaN 不會留下來）。"""
    import dsv_spectrum as SP
    fs = _sample_rate(fs)
    L = _int_scalar(window_length, "window_length", 1)
    N = _int_scalar(averages, "averages", 1)
    off, vec = _offset_values(foffset)           # scope 的 FrequencyOffset：型別／實數／形狀／有限照實測（見 MaskTester._offsets）
    if off.size == 0 and not vec:                # []（0×0）→ expectedVector；zeros(1,0)／zeros(0,1)（MATLAB 的向量）→ 下面的個數檢查
        raise _err_offset_vector()
    if not np.isfinite(off).all():
        raise _err_finite("FrequencyOffset")
    if off.size != 1:                            # DSV：一條頻率格只配一個偏移（scope 收每通道一個，但這裡只回一條 f）
        raise MaskError(_ID_DSV + "badScalarArgument", f"foffset must be one real value (one frequency grid); got {off.size} values.",
                        f"foffset 必須是一個實數（只有一條頻率格）；現在是 {off.size} 個值。")
    foffset = float(off[0])
    if not isinstance(two_sided, (bool, np.bool_)):
        raise MaskError(_ID_DSV + "badFlag", f"two_sided must be True or False; got {two_sided!r}.",
                        f"two_sided 必須是 True 或 False；現在是 {two_sided!r}。")
    nfft = nfft_auto(L) if nfft is None else _int_scalar(nfft, "nfft", 1)
    if nfft < L:                                 # MATLAB 不接受 FFTLength < WindowLength（它的訊息沒探過 → DSV 自己的 ID）
        raise MaskError(_ID_DSV + "fftLengthTooShort", f"FFTLength {nfft} must be >= WindowLength {L}.",
                        f"FFTLength {nfft} 必須 ≥ WindowLength {L}。")
    if nfft > MAX_ELEMENTS:
        raise MaskError(_ID_DSV + "tooLarge", f"NFFT {nfft} exceeds the DSV limit {MAX_ELEMENTS}.", f"NFFT {nfft} 超過 DSV 的上限 {MAX_ELEMENTS}。")
    if not isinstance(calls, (list, tuple)):
        raise MaskError(_ID_DSV + "badCalls", f"calls must be a list or tuple of (samples, channels) arrays, one per input call; got {type(calls).__name__}.",
                        f"calls 必須是 list／tuple，每個元素是一次呼叫的 (樣本, 通道) 陣列；現在是 {type(calls).__name__}。")
    w = SP.design_window("hann", L)
    lam = (N - 1.0) / (N + 1.0)
    num: Optional[np.ndarray] = None
    den = 0.0
    out: List[Optional[np.ndarray]] = []
    mode = "centered" if two_sided else "onesided"
    spec: Optional[Tuple[int, bool]] = None      # (通道數, 複數?)：第一次呼叫定下，之後每次都要一樣
    for k, x in enumerate(calls):
        try:
            x = np.asarray(x)
        except Exception:
            x = np.zeros(0, dtype=object)
        if x.dtype.kind not in "iufc":
            raise MaskError(_ID_DSV + "badCalls", f"call {k + 1} is not a numeric array.", f"第 {k + 1} 次呼叫的資料不是數值陣列。")
        if x.ndim == 1:
            x = x[:, None]
        if x.ndim != 2 or x.shape[1] < 1:
            raise MaskError(_ID_DSV + "shapeMismatch", f"Each call must be (samples, channels) with at least one channel; call {k + 1} is {x.shape}.",
                            f"每次呼叫的資料必須是 (樣本, 通道) 且至少一個通道；第 {k + 1} 次呼叫是 {x.shape}。")
        n, nch = x.shape
        cur = (nch, bool(np.iscomplexobj(x)))
        if spec is None:                         # 第一次呼叫決定這一串的通道數與實數／複數（複數 → 雙邊置中）
            spec = cur
            if cur[1]:
                mode = "centered"
        elif cur != spec:                        # 中途改：MATLAB 沒探過 → DSV 擋下（以前 numpy broadcast 錯誤或悄悄混用平均歷史）
            def desc(s, zh=False):
                return (f"{s[0]} 個通道、{'複數' if s[1] else '實數'}" if zh else
                        f"{s[0]} channel{'s' if s[0] != 1 else ''}, {'complex' if s[1] else 'real'}")
            raise MaskError(_ID_DSV + "inputSpecChanged",
                            f"Call {k + 1} has {desc(cur)} but call 1 had {desc(spec)}; the number of channels and the complexity cannot "
                            f"change within one sequence of calls — start a new scope_spectra() sequence (MATLAB release()) instead.",
                            f"第 {k + 1} 次呼叫是 {desc(cur, True)}，第 1 次是 {desc(spec, True)}；同一串呼叫中不能改通道數或實數／複數——"
                            f"請開新的一串 scope_spectra()（等於 MATLAB 的 release()）。")
        if nch * nfft > MAX_ELEMENTS:
            raise MaskError(_ID_DSV + "tooLarge", f"{nch} channels x NFFT {nfft} exceeds the DSV limit {MAX_ELEMENTS}.",
                            f"{nch} 通道 × NFFT {nfft} 超過 DSV 的上限 {MAX_ELEMENTS}。")
        nseg = n // L
        if nseg == 0:
            out.append(None)
            continue
        # 極端樣本（|x| ≳ 1e155 → |FFT|² 溢位；Inf 樣本 → FFT 裡 0·Inf）照 IEEE 給 Inf／NaN，不要 numpy 警告（signal_viewer 的頻譜路徑同樣做法）
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            for i in range(nseg):
                P = np.stack([SP.welch(x[i * L:(i + 1) * L, ch], fs, w, 0, nfft, mode)["power"] for ch in range(nch)], axis=1)
                if num is None or lam == 0.0:    # N＝1 → λ＝0：就是這一段的週期圖（不算 0·num，免得前一段的 Inf／NaN 以 0·Inf＝NaN 留下來）
                    num, den = P, 1.0
                else:
                    num = lam * num + P
                    den = lam * den + 1.0
            out.append(10.0 * np.log10(num / den) + 30.0)
    f = SP.freq_grid(nfft, fs, mode) + foffset
    return f, out


# ----------------------------------------------------------------------------------------------------------------------
def selftest(check, ref_dir: str) -> None:
    """逐筆比對兩組參考資料：tests/matlab_ref/spectral_mask/（屬性 33 組 MATLAB 實跑；17 組推定規則案例）與
    tests/matlab_ref/scope/spectral_mask/（分析器實測：88 次呼叫的頻譜重建與全部狀態欄位）。"""
    _selftest_function_level(check, ref_dir)
    _selftest_scope(check, ref_dir)


def _same(a, b) -> Tuple[bool, str]:
    """值對值完全相同（形狀、NaN 位置、±Inf、數值位元相同）；回傳 (ok, 第一個不同處)。參考 JSON 帶 17 位有效數字，位元相同是
    該用的標準（第一輪用 rtol 1e-9 審查時被指出沒有理由）。"""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape:
        return False, f"形狀 {a.shape} vs {b.shape}"
    na, nb_ = np.isnan(a), np.isnan(b)
    bad = (na != nb_) | (~na & ~nb_ & (a != b))
    if bad.any():
        i = tuple(int(k) for k in np.argwhere(bad)[0])
        return False, f"第 {i} 個：{a[i]!r} vs 參考 {b[i]!r}（共 {int(bad.sum())} 個不同）"
    return True, ""


def _selftest_function_level(check, ref_dir: str) -> None:
    import json
    import os
    import time as _time
    import dsv_spectrum as SP
    d = os.path.join(ref_dir, "spectral_mask")
    path = os.path.join(d, "spectral_mask_ref.json")
    if not os.path.isdir(ref_dir):               # 整個 tests/matlab_ref 都沒有（打包後的 app）才略過；有目錄卻缺參考檔就是 FAIL（第六輪審查）
        check(True, "（沒有 tests/matlab_ref：略過頻譜模板比對）")
        return
    if not os.path.isfile(path):
        check(False, f"沒有 {path}（頻譜模板的參考檔）")
        return
    with open(path, encoding="utf-8") as fh:
        R = json.load(fh)

    def read_input(fn):
        with open(fn, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().split("\n") if ln.strip()]
        nb, nch, nu = (int(v) for v in lines[0].split())
        f = np.array(lines[1].split(), dtype=float)
        rows = [np.array(ln.split(), dtype=float) for ln in lines[2:2 + nu * nch]]
        spec = np.array(rows).reshape(nu, nch, nb)
        return f, spec

    def arr1(v):
        return np.atleast_1d(np.asarray(v, dtype=float))

    def lim_ref(v, nch):
        L = np.asarray(v, dtype=float)
        return (L[:, None] if L.ndim == 1 else L).T if L.size else np.zeros((nch, 0))

    def make_config(cfg):
        return MaskConfig(EnabledMasks=cfg["EnabledMasks"], UpperMask=cfg["UpperMask"], LowerMask=cfg["LowerMask"],
                          ReferenceLevel=cfg["ReferenceLevel"], CustomReferenceLevel=cfg["CustomReferenceLevel"],
                          SelectedChannel=cfg["SelectedChannel"], MaskFrequencyOffset=cfg["MaskFrequencyOffset"])

    def compare_update(st, u):
        """一筆更新記錄 vs 參考（SuccessRate 另外處理）；回傳不同處清單。"""
        e: List[str] = []
        okr, why = _same([st["reference"]], [u["reference"]])
        if not okr:
            e.append("參考位準 " + why)
        if st["IsCurrentlyPassing"] != bool(u["IsCurrentlyPassing"]) or st["current_status"] != u["currentStatus"]:
            e.append(f"狀態 {st['current_status']} vs {u['currentStatus']}")
        for key, rk in (("upper_status", "upperMaskStatus"), ("lower_status", "lowerMaskStatus")):
            word = "passing" if st[key] in (True, None) else "failing"
            if word != u[rk]:
                e.append(f"{rk} {word} vs {u[rk]}")
        if st["NumPassedTests"] != u["NumPassedTests"] or st["NumTotalTests"] != u["NumTotalTests"]:
            e.append(f"計數 {st['NumPassedTests']}/{st['NumTotalTests']} vs {u['NumPassedTests']}/{u['NumTotalTests']}")
        if st["FailingChannels"] != arr1(u["FailingChannels"]).astype(int).tolist():
            e.append(f"失敗通道 {st['FailingChannels']} vs {u['FailingChannels']}")
        if st["FailingMasks"] != u["FailingMasks_inferred"] or st["event"] != bool(u["MaskTestFailed_event"]):
            e.append("FailingMasks／事件")
        if st["n_fail_upper"] != arr1(u["numUpperFailBins"]).astype(int).tolist() or \
                st["n_fail_lower"] != arr1(u["numLowerFailBins"]).astype(int).tolist():
            e.append(f"失敗 bin 數 {st['n_fail_upper']}/{st['n_fail_lower']} vs {u['numUpperFailBins']}/{u['numLowerFailBins']}")
        return e

    inputs = {k: read_input(os.path.join(d, v["file"])) for k, v in R["datasets"].items()}
    n_cmp = n_ok = n_exact = 0
    sr_diff: List[Tuple[str, int, int, int, float, float]] = []   # 已知差異：研究參考的 SuccessRate 用 100*P/T，分析器用 P/T*100
    sr_bad: List[str] = []
    scope_rule_diff: Dict[str, List[str]] = {}   # 分析器規則 vs 研究參考（解碍規則）的差異
    for case in R["cases"]:
        cfg = case["config"]
        f, spec = inputs[cfg["dataset"]]
        nu, nch, nb = spec.shape
        xlim = cfg["FrequencyLimits"]
        foff = cfg["ScopeFrequencyOffset"]
        # (1) 推定的規則（純量模板只蓋 xlim）：參考 JSON 就是這套規則算的 → 限值位元相同、每筆更新一致
        t = MaskTester(make_config(cfg), scalar_over_xlim=True)
        bad: List[str] = []
        lu, ll = t.limits(f, xlim, nch, foff)
        for nm, mine, ref in (("上限", lu, lim_ref(case["upperLimit_noRef"], nch)), ("下限", ll, lim_ref(case["lowerLimit_noRef"], nch))):
            mine = np.full((nch, nb), np.nan) if mine is None else mine
            ok, why = _same(mine, ref)
            n_cmp += 1
            n_ok += ok
            n_exact += ok
            if not ok:
                bad.append(f"{nm}限值 {why}")
        for u in case["updates"]:
            st = t.test(f, spec[u["update"] - 1], xlim, foff)
            n_cmp += 1
            if not u["tested"]:
                if st["tested"] or t.total != 0 or t.status is not None:
                    bad.append(f"更新 {u['update']}：none 卻測了")
                else:
                    n_ok += 1
                continue
            e = compare_update(st, u)
            p, tt = st["NumPassedTests"], st["NumTotalTests"]
            if st["SuccessRate"] != u["SuccessRate"]:
                if st["SuccessRate"] == p / tt * 100.0 and u["SuccessRate"] == 100.0 * p / tt:
                    sr_diff.append((cfg["name"], u["update"], p, tt, st["SuccessRate"], u["SuccessRate"]))
                else:
                    sr_bad.append(f"{cfg['name']} 更新 {u['update']}：{st['SuccessRate']!r} vs {u['SuccessRate']!r}")
                    e.append("成功率")
            if e:
                bad.append(f"更新 {u['update']}：" + "；".join(e))
            else:
                n_ok += 1
        # (2) 分析器規則（預設）：和參考只差在純量模板的範圍（A_scalar_xlim 的狀態、B_twosided 下限在 xlim 外那個 bin）
        t2 = MaskTester(make_config(cfg))
        lu2, ll2 = t2.limits(f, xlim, nch, foff)
        diffs: List[str] = []
        for nm, mine, mine2 in (("上限", lu, lu2), ("下限", ll, ll2)):
            if (mine is None) != (mine2 is None) or (mine is not None and not _same(mine, mine2)[0]):
                if mine is None:
                    nd = -1
                else:
                    na, nb2 = np.isnan(mine), np.isnan(mine2)
                    nd = int(((na != nb2) | (~na & ~nb2 & (mine != mine2))).sum())
                diffs.append(f"{nm}限值 {nd} 個 bin 不同（推定規則只蓋 xlim {xlim}，分析器全部 bin）")
        for u in case["updates"]:
            st2 = t2.test(f, spec[u["update"] - 1], xlim, foff)
            if u["tested"]:
                e2 = compare_update(st2, u)
                e2 = [x for x in e2 if not x.startswith("計數")]      # 計數差是前面更新狀態差的後果，不重複列
                if e2:
                    diffs.append(f"更新 {u['update']}：" + "；".join(e2))
        if diffs:
            scope_rule_diff[cfg["name"]] = diffs
        up = cfg["UpperMask"]
        desc = (f"{cfg['EnabledMasks']}、上 {'矩陣' + str(len(up)) + '點' if isinstance(up, list) else up}、下 "
                f"{'矩陣' if isinstance(cfg['LowerMask'], list) else cfg['LowerMask']}、ref {cfg['ReferenceLevel']}"
                f"{'' if cfg['ReferenceLevel'] != 'custom' else ' ' + str(cfg['CustomReferenceLevel'])}"
                f"{'、偏移 ' + str(cfg['MaskFrequencyOffset']) + ' Hz' if cfg['MaskFrequencyOffset'] else ''}、xlim {xlim}")
        check(not bad, f"頻譜模板 {cfg['name']}（{nch} 通道 × {nu} 次更新；{desc}；推定規則 scalar_over_xlim=True）：限值逐 bin 位元相同、"
                       f"參考位準、通過／失敗、上下模板狀態、計數、失敗通道、失敗 bin 數一致" + (f"（不一致：{'；'.join(bad)}）" if bad else ""))
    check(n_exact == 2 * len(R["cases"]), f"頻譜模板限值：{len(R['cases'])} 組案例 × 上下限 {n_exact}/{2 * len(R['cases'])} 組位元完全相同"
                                         f"（共 {n_cmp} 筆比對、{n_ok} 筆一致）")
    # 已知差異 1：SuccessRate 的運算順序（研究參考 .m 用 100*npass/ntot；分析器實測是 P/T*100，差 1 ulp 只在 2/3 出現）——
    # 逐筆斷言 P/T＝2/3 和兩個字面值 66.66666666666666（P/T×100）／66.66666666666667（100·P/T）
    sr_txt = [f"{n} 更新 {u}（{p}/{t}）：分析器 P/T×100＝{a!r}，研究參考 100·P/T＝{b!r}" for n, u, p, t, a, b in sr_diff]
    ok_sr = (not sr_bad and len(sr_diff) == 3
             and all(p == 2 and t == 3 and a == 66.66666666666666 and b == 66.66666666666667 for _, _, p, t, a, b in sr_diff))
    check(ok_sr, f"已知差異：SuccessRate 研究參考用 100·P/T、分析器實測用 P/T×100——只在 P/T＝2/3 的 {len(sr_diff)} 筆更新差 1 ulp"
                 f"（逐筆斷言值就是 66.66666666666666 vs 66.66666666666667），其餘全部相同" + (f"（{sr_bad}）" if sr_bad else "")
                 + "：" + "；".join(sr_txt[:2]) + (" …" if len(sr_txt) > 2 else ""))
    # 已知差異 2：純量模板的範圍——研究參考照推定的「只蓋 xlim」，分析器實測是整張頻譜（8/8 次呼叫推翻這條推定）
    exp_keys = {"A_scalar_xlim", "B_twosided"}
    ok_sx = (set(scope_rule_diff) == exp_keys
             and len(scope_rule_diff.get("A_scalar_xlim", [])) == 5
             and scope_rule_diff["A_scalar_xlim"][0] == "上限限值 280 個 bin 不同（推定規則只蓋 xlim [120, 480]，分析器全部 bin）"
             and all("狀態 failing vs passing" in s and "失敗通道 [1, 2] vs []" in s and "失敗 bin 數 [5, 5]/[0, 0] vs [0, 0]/[0, 0]" in s
                     for s in scope_rule_diff["A_scalar_xlim"][1:])
             and scope_rule_diff.get("B_twosided") == ["下限限值 1 個 bin 不同（推定規則只蓋 xlim [-500, 499]，分析器全部 bin）"])
    check(ok_sx, "已知差異：純量模板研究參考只蓋 xlim（推定），分析器實測是整張頻譜的每個 bin ——A_scalar_xlim（−12 dBm、xlim 120–480）：上限在 2 通道 × 140 個"
                 "範圍外 bin 由 NaN 變 −12，4 次更新研究說通過、分析器規則下 94–101 Hz 的音調（每通道 5 個 bin，27–36 dBm）讓兩個通道都失敗"
                 "（mask_A_scalar_m12_xlim_* 實測 8/8 失敗）；B_twosided 下限 −60 在 500 Hz 那 1 個 bin 研究給 NaN、分析器規則給 −60（狀態不變）"
                 + ("" if ok_sx else f"（實際差異：{scope_rule_diff}）"))

    # 屬性設定 vs MATLAB 實跑（probe_config.json）
    with open(os.path.join(d, "probe_config.json"), encoding="utf-8") as fh:
        P = json.load(fh)

    def literal(txt):
        """mat2str 輸出 → Python 值：'x'／"x" → str；[] → 空；[a b;c d] → ndarray；a+bi → complex；true／false → bool；數字（Inf、NaN）→ float。"""
        s = txt.strip()
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            return s[1:-1]
        if s in ("true", "false"):
            return s == "true"
        if s == "[]":
            return np.zeros(0)
        if s.startswith("["):
            return np.array([[literal(t) for t in r.split()] for r in s[1:-1].split(";")])
        m = re.match(r"^([+-]?[\d.]+(?:e[+-]?\d+)?)([+-][\d.]+(?:e[+-]?\d+)?)i$", s, re.I)
        if m:
            return complex(float(m.group(1)), float(m.group(2)))
        return float(s)

    def equal_value(a, b):
        if isinstance(a, str) or isinstance(b, str):
            return a == b
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        return a.shape == b.shape and bool(np.array_equal(a, b, equal_nan=True))

    groups: Dict[str, List[str]] = {}
    counts: Dict[str, int] = {}
    for r in P["cfg_cases"]:
        prop = r["prop"]
        counts[prop] = counts.get(prop, 0) + 1
        groups.setdefault(prop, [])
        val = literal(r["value"])
        try:
            c = MaskConfig()
            setattr(c, prop, val)
            got = getattr(c, prop)
            if not r["ok"]:
                groups[prop].append(f"{r['value']} 應該要錯（{r['id']}）卻接受了")
            else:
                exp = literal(r["after"])
                if isinstance(exp, np.ndarray) and exp.size == 1:
                    exp = float(exp.reshape(()))
                if not equal_value(got, exp):
                    groups[prop].append(f"{r['value']} → {got!r}，MATLAB 給 {r['after']}")
        except MaskError as ex:
            if r["ok"]:
                groups[prop].append(f"{r['value']} 應該接受卻錯了：{ex.identifier}")
            elif ex.identifier != r["id"] or ex.message != r["msg"]:
                groups[prop].append(f"{r['value']}：{ex.identifier} / {ex.message!r} vs MATLAB {r['id']} / {r['msg']!r}")
            elif not ex.message_zh:
                groups[prop].append(f"{r['value']}：沒有繁中訊息")
    n_cmp += sum(counts.values())
    n_ok += sum(counts.values()) - sum(len(v) for v in groups.values())
    for prop, bad in groups.items():
        check(not bad, f"頻譜模板屬性 {prop} vs MATLAB（{counts[prop]} 組設定：接受／正規化值／錯誤 ID 與訊息）一致"
                       + (f"（不一致：{'；'.join(bad)}）" if bad else ""))
    def err_msg(fn):
        try:
            fn()
        except MaskError as ex:
            return ex.message
        return None

    c0 = MaskConfig()
    defaults_ok = (P["cfg_class"] == "SpectralMaskConfiguration" and P["spec_class"] == "SpectralMaskConfiguration"
                   and all(P["cfg_def_" + k] == getattr(c0, k) for k in ("EnabledMasks", "ReferenceLevel", "CustomReferenceLevel",
                                                                          "SelectedChannel", "MaskFrequencyOffset", "Enabled"))
                   and P["cfg_def_UpperMask"] is None and P["cfg_def_LowerMask"] is None and c0.UpperMask == math.inf and c0.LowerMask == -math.inf
                   and "MaskTestFailed" in P["cfg_events"] and list(DEFAULTS) == P["cfg_props"] == P["spec_props"]
                   # 第二次探測（spectrumAnalyzer 上的 SpectralMask 物件，spec_*）：預設值、事件、三個錯誤訊息直接比
                   and all(P["spec_def_" + k] == P["cfg_def_" + k] for k in DEFAULTS) and P["spec_events"] == P["cfg_events"]
                   and P["spec_enum_err"] == err_msg(lambda: normalize_enabled("bogus"))
                   and P["spec_mask_err"] == err_msg(lambda: validate_mask([1, 2, 3]))
                   and P["spec_freq_err"] == err_msg(lambda: validate_mask([[2, 1], [1, 2]])))
    check(defaults_ok, "頻譜模板預設值 vs MATLAB SpectralMaskConfiguration（＝SpectralMaskSpecification）：none、Inf／−Inf（JSON 寫成 null）、"
                       "custom 0、通道 1、偏移 0、Enabled false；8 個屬性名稱與順序；MaskTestFailed 事件；scope 上的 SpectralMask 物件（spec_*）"
                       "的預設值、事件、invalidEnumValue／invalidMaskData／invalidMaskFrequencyData 訊息一字不差")

    # 輸入檢查（審查指出的：複數／非數值的 f、spectra 要丟 MaskError，不是 numpy 警告；None 不能變成 'none'；未驗證的模板不能 IndexError）
    def _tester_with_bad_config(ff, SS):
        t_ = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12))
        t_.config = "x"                      # config 是普通屬性，可以隨時換；換成不是 MaskConfig 的東西要在 test() 被擋
        return t_.test(ff, SS)

    bad = []
    f, spec = inputs["A"]
    tt = MaskTester(MaskConfig(EnabledMasks="upper-and-lower", UpperMask=[[0, -17], [500, -17]], LowerMask=-60))
    for what, fn in (("複數 spectra", lambda: tt.test(f, np.zeros((2, f.size), complex) - 50 + 1j)),
                     ("複數 list spectra", lambda: tt.test(f, [[-50 + 1j] * f.size])),
                     ("複數 f", lambda: tt.test(f.astype(complex), spec[0])),
                     ("字串 f", lambda: tt.test("abc", spec[0])),
                     ("bool spectra", lambda: tt.test(f, np.ones((2, f.size), bool))),
                     ("形狀不合", lambda: tt.test(f, spec[0][:, :10])),
                     ("None → EnabledMasks", lambda: MaskConfig(EnabledMasks=None)),
                     ("數字 → EnabledMasks", lambda: MaskConfig(EnabledMasks=3)),
                     ("[] → ReferenceLevel", lambda: MaskConfig(ReferenceLevel=[])),
                     ("1-D 模板 → mask_limits", lambda: mask_limits([1, 2, 3], [0.0, 1.0])),
                     ("1-D 模板 → mask_polyline", lambda: mask_polyline([1, 2, 3], "upper", [0, 1], [-1, 1])),
                     ("Enabled 'yes'", lambda: MaskConfig(Enabled="yes")),
                     ("太大", lambda: MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-1)).limits(np.zeros(MAX_ELEMENTS // 2 + 1), None, 3)),
                     ("foffset 3 個值給 2 通道 → limits", lambda: tt.limits(f, None, 2, [0.0, 1.0, 2.0])),
                     ("foffset 3 個值給 2 通道 → test", lambda: tt.test(f, spec[0], foffset=[0.0, 1.0, 2.0])),
                     ("foffset 字串", lambda: tt.limits(f, None, 2, "abc")),
                     ("fs 0 → simulation_time", lambda: simulation_time(None, 4000, 0)),
                     ("fs 0 → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 0, 1000)),
                     ("fs NaN → scope_spectra", lambda: scope_spectra([np.zeros(1000)], math.nan, 1000)),
                     ("fs 負 → scope_spectra", lambda: scope_spectra([np.zeros(1000)], -1000, 1000)),
                     ("NFFT 512 < WindowLength 1000", lambda: scope_spectra([np.zeros(1000)], 1000, 1000, nfft=512)),
                     ("NFFT > 2^24", lambda: scope_spectra([np.zeros(1000)], 1000, 1000, nfft=MAX_ELEMENTS + 1)),
                     # 第二輪審查指出的：以前漏出 numpy／Python 原生錯誤或悄悄截斷的呼叫端參數
                     ("2-D f → limits", lambda: tt.limits(np.zeros((2, f.size)), None, 2)),
                     ("nch 1.5 → limits", lambda: tt.limits(f, None, 1.5)),
                     ("nch 'a' → limits", lambda: tt.limits(f, None, "a")),
                     ("nch None → limits", lambda: tt.limits(f, None, None)),
                     ("nch 0 → limits", lambda: tt.limits(f, None, 0)),
                     ("lim (3,5) vs S (2,5) → mask_test", lambda: mask_test(np.zeros((2, 5)), np.zeros((3, 5)), None, 0.0)),
                     ("lim 1-D 長度 4 vs 5 bin → mask_test", lambda: mask_test(np.zeros((2, 5)), None, np.zeros(4), 0.0)),
                     ("ref '0' → mask_test", lambda: mask_test(np.zeros((2, 5)), np.zeros((2, 5)), None, "0")),
                     ("ref None → mask_test", lambda: mask_test(np.zeros((2, 5)), np.zeros((2, 5)), None, None)),
                     ("mfo 'abc' → mask_limits", lambda: mask_limits([[0, 1], [4, 2]], f, mfo="abc")),
                     ("mfo None → mask_limits", lambda: mask_limits([[0, 1], [4, 2]], f, mfo=None)),
                     ("mfo Inf → mask_breakpoints", lambda: mask_breakpoints([[0, 1], [4, 2]], mfo=math.inf)),
                     ("window_length 'a' → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 1000, "a")),
                     ("window_length 1000.5 → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 1000, 1000.5)),
                     ("averages 0 → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 1000, 1000, 0)),
                     ("nfft 1024.5 → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 1000, 1000, nfft=1024.5)),
                     ("foffset 'a' → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 1000, 1000, foffset="a")),
                     ("foffset Inf → scope_spectra", lambda: scope_spectra([np.zeros(1000)], 1000, 1000, foffset=math.inf)),
                     ("calls None → scope_spectra", lambda: scope_spectra(None, 1000, 1000)),
                     ("calls 字串元素 → scope_spectra", lambda: scope_spectra(["abc"], 1000, 1000)),
                     ("calls 一個 2-D 陣列（不是 list）→ scope_spectra", lambda: scope_spectra(np.zeros((1000, 2)), 1000, 1000)),
                     ("fs True → scope_spectra", lambda: scope_spectra([np.zeros(1000)], True, 1000)),
                     ("fs '1000' → scope_spectra", lambda: scope_spectra([np.zeros(1000)], "1000", 1000)),
                     ("fs [1000 2000] → simulation_time", lambda: simulation_time(None, 4000, [1000, 2000])),
                     ("prev 'x' → simulation_time", lambda: simulation_time("x", 4000, 1000)),
                     ("n_samples 'x' → simulation_time", lambda: simulation_time(None, "x", 1000)),
                     ("n_samples 4000.7 → simulation_time", lambda: simulation_time(None, 4000.7, 1000)),
                     ("mfo 'a' → mask_polyline", lambda: mask_polyline([[0, 1], [4, 2]], "upper", [0, 4], [-1, 1], mfo="a")),
                     ("xlim None → mask_polyline", lambda: mask_polyline([[0, 1], [4, 2]], "upper", None, [-1, 1])),
                     ("ylim 3 個值 → mask_polyline", lambda: mask_polyline([[0, 1], [4, 2]], "upper", [0, 4], [-1, 0, 1])),
                     ("xlim 含 NaN → mask_polyline", lambda: mask_polyline(-12, "lower", [0, math.nan], [-1, 1])),
                     ("kind 'side' → mask_polyline", lambda: mask_polyline([[0, 1], [4, 2]], "side", [0, 4], [-1, 1])),
                     ("ref None → mask_polyline", lambda: mask_polyline(-12, "upper", [0, 4], [-1, 1], ref=None)),
                     ("xlim 'ab' → scalar_over_xlim limits", lambda: MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-1), scalar_over_xlim=True).limits(f, "ab")),
                     ("inf_as_axis_limits、全 NaN f、沒 xlim → limits",
                      lambda: MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=[[-math.inf, -30], [math.inf, -30]]),
                                         inf_as_axis_limits=True).limits(np.full(5, math.nan), None, 1)),
                     ("MaskConfig(bogus=1)", lambda: MaskConfig(bogus=1)),
                     ("MaskTester('x')", lambda: MaskTester("x")),
                     ("config 換成字串後 test", lambda: _tester_with_bad_config(f, spec[0])),
                     ("panel_row 缺欄位", lambda: panel_row({"tested": True})),
                     ("success_rate('a', 2)", lambda: success_rate("a", 2)),
                     ("nfft_auto('a')", lambda: nfft_auto("a")),
                     ("NaN → parse_reference_level", lambda: parse_reference_level("NaN")),
                     ("' Inf'（前面有空白）→ parse_reference_level", lambda: parse_reference_level(" Inf")),
                     ("'   '（只有空白）→ parse_reference_level", lambda: parse_reference_level("   ")),
                     ("'' → parse_offset", lambda: parse_offset("")),
                     ("Inf → parse_offset", lambda: parse_offset("Inf"))):
        try:
            fn()
            bad.append(what + "（沒錯）")
        except MaskError as ex:
            if not (ex.identifier and ex.message and ex.message_zh):
                bad.append(what + "（訊息不完整）")
        except Exception as ex:   # noqa: BLE001 — 其他例外就是沒守住
            bad.append(f"{what}（{type(ex).__name__}）")
    if tt.total != 0 or tt.status is not None:
        bad.append("錯誤的輸入動到計數")
    check(not bad, "輸入檢查：複數／非數值／logical 的 f 與 spectra、形狀不合、None／數字當列舉、未驗證的模板、Enabled 非邏輯、超過 2^24 元素、"
                   "foffset 長度／型別不合、fs 0／NaN／負／True／'1000'、NFFT < WindowLength、2-D f、nch 1.5／'a'／None／0、mask_test 限值形狀不合、"
                   "ref／mfo／foffset／prev／xlim／ylim／kind／calls／window_length／n_samples 型別或值不對（1000.5、4000.7 不截斷）、"
                   "MaskConfig 不存在的屬性、config 不是 MaskConfig、panel_row 缺欄位、參考位準欄位 NaN／' Inf'／只有空白、頻率偏移欄位空字串／Inf → 都是 MaskError"
                   "（MATLAB ID 或 DSV:spectralMask:*＋英文＋繁中），計數不動" + (f"（不一致：{bad}）" if bad else ""))
    # 第三輪審查：每個項目都要丟指定 ID 的 MaskError（英文＋繁中），不能漏原生錯誤、不能悄悄接受
    good_st = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12)).test(f, spec[0], time=3.999)

    def st_with(**kw):
        s_ = dict(good_st)
        s_.update(kw)
        return s_

    t_none = MaskTester(MaskConfig(EnabledMasks="none"))
    x2 = np.zeros((1000, 2))
    x1 = np.zeros(1000)
    xc = np.zeros(1000, complex)
    ts_x = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-10), scalar_over_xlim=True)
    ti_x = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=[[-math.inf, -30], [math.inf, -30]]), inf_as_axis_limits=True)
    r3_cases = (
        ("scope_spectra averages 4：2 → 1 通道", "inputSpecChanged", lambda: scope_spectra([x2, x1], 1000, 1000, 4)),
        ("scope_spectra averages 4：2 → 3 通道", "inputSpecChanged", lambda: scope_spectra([x2, np.zeros((1000, 3))], 1000, 1000, 4)),
        ("scope_spectra averages 4：1 → 2 通道（以前悄悄 broadcast 通道 1 的歷史）", "inputSpecChanged", lambda: scope_spectra([x1, x2], 1000, 1000, 4)),
        ("scope_spectra averages 1：1 → 2 通道", "inputSpecChanged", lambda: scope_spectra([x1, x2], 1000, 1000, 1)),
        ("scope_spectra averages 4：實數 → 複數", "inputSpecChanged", lambda: scope_spectra([x1, xc], 1000, 1000, 4)),
        ("scope_spectra averages 1：實數 → 複數（以前單邊頻譜配雙邊頻率格）", "inputSpecChanged", lambda: scope_spectra([x1, xc], 1000, 1000, 1)),
        ("scope_spectra 複數 → 實數", "inputSpecChanged", lambda: scope_spectra([xc, x1], 1000, 1000, 4)),
        ("scope_spectra 先短呼叫（不足一個視窗）再改通道", "inputSpecChanged", lambda: scope_spectra([np.zeros(10), x2], 1000, 1000, 4)),
        ("scope_spectra 0 個通道", "shapeMismatch", lambda: scope_spectra([np.zeros((1000, 0))], 1000, 1000)),
        ("scope_spectra two_sided 'yes'", "badFlag", lambda: scope_spectra([x1], 1000, 1000, two_sided="yes")),
        ("limits(np.zeros(0), None, 10**9)", "tooLarge", lambda: tt.limits(np.zeros(0), None, 10 ** 9)),
        ("limits xlim 'ab'（旗標關）", "badAxisLimits", lambda: tt.limits(f, "ab", 2)),
        ("limits xlim [0, NaN]（旗標關）", "badAxisLimits", lambda: tt.limits(f, [0, math.nan], 2)),
        ("panel_row('x')", "badStatus", lambda: panel_row("x")),
        ("panel_row([1])", "badStatus", lambda: panel_row([1])),
        ("panel_row({'tested': 'yes'})", "badStatus", lambda: panel_row({"tested": "yes"})),
        ("panel_row IsCurrentlyPassing 'yes'", "badStatus", lambda: panel_row(st_with(IsCurrentlyPassing="yes"))),
        ("panel_row IsCurrentlyPassing None", "badStatus", lambda: panel_row(st_with(IsCurrentlyPassing=None))),
        ("panel_row upper_status 'x'", "badStatus", lambda: panel_row(st_with(upper_status="x"))),
        ("panel_row lower_status 0", "badStatus", lambda: panel_row(st_with(lower_status=0))),
        ("panel_row NumPassedTests 'a'", "badStatus", lambda: panel_row(st_with(NumPassedTests="a"))),
        ("panel_row NumTotalTests −1", "badStatus", lambda: panel_row(st_with(NumTotalTests=-1))),
        ("panel_row SuccessRate 'a'", "badStatus", lambda: panel_row(st_with(SuccessRate="a"))),
        ("panel_row FailingChannels ['a']", "badStatus", lambda: panel_row(st_with(FailingChannels=["a"]))),
        ("panel_row FailingChannels 5", "badStatus", lambda: panel_row(st_with(FailingChannels=5))),
        ("panel_row labels 5", "badLabels", lambda: panel_row(good_st, labels=5)),
        ("panel_row labels [1, 2]", "badLabels", lambda: panel_row(good_st, labels=[1, 2])),
        ("failing_channels_matlab(['a'])", "badFailingChannels", lambda: failing_channels_matlab(["a"])),
        ("failing_channels_matlab([1.5])", "badFailingChannels", lambda: failing_channels_matlab([1.5])),
        ("failing_channels_matlab([True])", "badFailingChannels", lambda: failing_channels_matlab([True])),
        ("failing_channels_matlab([0])", "badFailingChannels", lambda: failing_channels_matlab([0])),
        ("failing_channels_matlab([NaN])", "badFailingChannels", lambda: failing_channels_matlab([math.nan])),
        ("failing_channels_matlab(5)", "badFailingChannels", lambda: failing_channels_matlab(5)),
        ("failing_channels_matlab('12')", "badFailingChannels", lambda: failing_channels_matlab("12")),
        ("failing_channels_matlab([[1, 2]])", "badFailingChannels", lambda: failing_channels_matlab([[1, 2]])),
        ("failing_channels_matlab(np.array(5))（0-d，以前 len() 的 TypeError）", "badFailingChannels", lambda: failing_channels_matlab(np.array(5))),
        ("failing_channels_matlab(np.array([[1]]))", "badFailingChannels", lambda: failing_channels_matlab(np.array([[1]]))),
        ("failing_channels_matlab([1, True])（以前 asarray 把 True 變 1）", "badFailingChannels", lambda: failing_channels_matlab([1, True])),
        ("panel_row FailingChannels np.array(1)（0-d）", "badStatus", lambda: panel_row(st_with(FailingChannels=np.array(1)))),
        ("panel_row(None, labels=5)", "badLabels", lambda: panel_row(None, labels=5)),
        ("panel_row 沒測的 status、labels [1]", "badLabels", lambda: panel_row(st_with(tested=False), labels=[1])),
        ("panel_row({'tested': False}, labels=5)", "badLabels", lambda: panel_row({"tested": False}, labels=5)),
        ("test time 'x'", "badScalarArgument", lambda: tt.test(f, spec[0], time="x")),
        ("test time Inf", "badScalarArgument", lambda: tt.test(f, spec[0], time=math.inf)),
        ("test time [1, 2]", "badScalarArgument", lambda: tt.test(f, spec[0], time=[1.0, 2.0])),
        ("test xlim 'ab'（旗標關）", "badAxisLimits", lambda: tt.test(f, spec[0], xlim="ab")),
        ("test xlim 3 個值（旗標關）", "badAxisLimits", lambda: tt.test(f, spec[0], xlim=[0, 1, 2])),
        ("test replace_last 'yes'", "badFlag", lambda: tt.test(f, spec[0], replace_last="yes")),
        ("none 設定的 test 也檢查 xlim", "badAxisLimits", lambda: t_none.test(f, spec[0], xlim="ab")),
        ("none 設定的 test 也檢查 time", "badScalarArgument", lambda: t_none.test(f, spec[0], time="x")),
        ("none 設定的 test 也檢查 foffset", "badFrequencyOffset", lambda: t_none.test(f, spec[0], foffset=[1.0, 2.0, 3.0])),
        ("none、0 個通道的 test 也檢查 foffset 長度", "badFrequencyOffset", lambda: t_none.test(f, np.zeros((0, f.size)), foffset=[1.0, 2.0])),
        # 第五輪審查：xlim／ylim 要有限且遞增（以前 [-Inf Inf]／[500 0] 讓 scalar_over_xlim／inf_as_axis_limits 的限值全 NaN、悄悄通過）
        ("mask_limits(-10, f, [-Inf, Inf], scalar_over_xlim=True)（以前限值全 NaN）", "badAxisLimits",
         lambda: mask_limits(-10.0, f, [-math.inf, math.inf], scalar_over_xlim=True)),
        ("mask_limits(-10, f, [500, 0], scalar_over_xlim=True)（以前反向 → 全 NaN → 通過）", "badAxisLimits",
         lambda: mask_limits(-10.0, f, [500, 0], scalar_over_xlim=True)),
        ("scalar_over_xlim 的 limits xlim [-Inf, Inf]", "badAxisLimits", lambda: ts_x.limits(f, [-math.inf, math.inf], 2)),
        ("scalar_over_xlim 的 test xlim [500, 0]", "badAxisLimits", lambda: ts_x.test(f, spec[0], xlim=[500, 0])),
        ("inf_as_axis_limits 的 limits xlim [0, Inf]", "badAxisLimits", lambda: ti_x.limits(f, [0, math.inf], 2)),
        ("limits xlim [0, 0]（相等）", "badAxisLimits", lambda: tt.limits(f, [0, 0], 2)),
        ("test xlim [-Inf, Inf]（旗標關也擋）", "badAxisLimits", lambda: tt.test(f, spec[0], xlim=[-math.inf, math.inf])),
        ("test xlim [500, 0]（旗標關也擋）", "badAxisLimits", lambda: tt.test(f, spec[0], xlim=[500, 0])),
        ("mask_breakpoints 純量、xlim [Inf, -Inf]", "badAxisLimits", lambda: mask_breakpoints(-12, xlim=[math.inf, -math.inf])),
        ("mask_polyline ylim [20, -80]（反向）", "badAxisLimits", lambda: mask_polyline(-12, "upper", [0, 500], [20, -80])),
        ("mask_polyline ylim [-80, Inf]", "badAxisLimits", lambda: mask_polyline(-12, "upper", [0, 500], [-80, math.inf])),
        ("mask_polyline xlim [-Inf, 500]", "badAxisLimits", lambda: mask_polyline([[0, 1], [4, 2]], "lower", [-math.inf, 500], [-80, 20])),
        # 第五輪審查：通道號碼有上限 2^24（以前 [1e300] 回 301 位數的 int）；NumPassedTests ≤ NumTotalTests；success_rate 同樣
        ("failing_channels_matlab([1e300])（以前回 301 位數的 int）", "badFailingChannels", lambda: failing_channels_matlab([1e300])),
        ("failing_channels_matlab([2^24 + 1])", "badFailingChannels", lambda: failing_channels_matlab([MAX_ELEMENTS + 1])),
        ("failing_channels_matlab([Inf])", "badFailingChannels", lambda: failing_channels_matlab([math.inf])),
        ("failing_channels_matlab(np.array([1, 2**60]))", "badFailingChannels", lambda: failing_channels_matlab(np.array([1, 2 ** 60]))),
        ("panel_row FailingChannels [1e300]", "badStatus", lambda: panel_row(st_with(FailingChannels=[1e300]))),
        ("panel_row NumPassedTests 3 > NumTotalTests 2（以前照印）", "badStatus", lambda: panel_row(st_with(NumPassedTests=3, NumTotalTests=2))),
        ("panel_row NumPassedTests 1 > NumTotalTests 0", "badStatus", lambda: panel_row(st_with(NumPassedTests=1, NumTotalTests=0))),
        ("success_rate(3, 2)（以前回 150.0）", "badCounts", lambda: success_rate(3, 2)),
    )
    r3_matlab_cases = (       # 用 MATLAB ID 的（不是 DSV:spectralMask:*）
        ("none、0 個通道的 test 也檢查 foffset 'abc'（以前 nch＝0 不檢查）", "MATLAB:invalidType",
         lambda: t_none.test(f, np.zeros((0, f.size)), foffset="abc")),
        # 第五輪審查：foffset（scope 的 FrequencyOffset）NaN／±Inf／[0 NaN] → MATLAB:expectedFinite（R2025a sa.FrequencyOffset 實測 ID；
        # 以前直接進限值計算、限值全 NaN、測試悄悄通過）
        ("limits foffset NaN", "MATLAB:expectedFinite", lambda: tt.limits(f, None, 2, math.nan)),
        ("limits foffset Inf", "MATLAB:expectedFinite", lambda: tt.limits(f, None, 2, math.inf)),
        ("limits foffset [0, NaN]（每通道一個）", "MATLAB:expectedFinite", lambda: tt.limits(f, None, 2, [0.0, math.nan])),
        ("limits foffset [0, -Inf]", "MATLAB:expectedFinite", lambda: tt.limits(f, None, 2, np.array([0.0, -math.inf]))),
        ("test foffset -Inf", "MATLAB:expectedFinite", lambda: tt.test(f, spec[0], foffset=-math.inf)),
        ("test foffset NaN", "MATLAB:expectedFinite", lambda: tt.test(f, spec[0], foffset=math.nan)),
        ("test foffset [0, NaN]", "MATLAB:expectedFinite", lambda: tt.test(f, spec[0], foffset=[0.0, math.nan])),
        ("none 設定的 test 也檢查 foffset NaN", "MATLAB:expectedFinite", lambda: t_none.test(f, spec[0], foffset=math.nan)),
        ("none、0 個通道的 test 也檢查 foffset Inf", "MATLAB:expectedFinite", lambda: t_none.test(f, np.zeros((0, f.size)), foffset=math.inf)),
        ("scope_spectra foffset NaN", "MATLAB:expectedFinite", lambda: scope_spectra([x1], 1000, 1000, foffset=math.nan)),
        ("scope_spectra foffset Inf（以前 badScalarArgument）", "MATLAB:expectedFinite", lambda: scope_spectra([x1], 1000, 1000, foffset=math.inf)),
    )
    bad3: List[str] = []
    for what, ident, fn in [(w, _ID_DSV + i, g) for w, i, g in r3_cases] + list(r3_matlab_cases):
        try:
            fn()
            bad3.append(what + "（沒錯）")
        except MaskError as ex:
            if ex.identifier != ident or not (ex.message and ex.message_zh):
                bad3.append(f"{what}（{ex.identifier}）")
        except Exception as ex:   # noqa: BLE001 — 其他例外就是沒守住
            bad3.append(f"{what}（{type(ex).__name__}: {ex}）")
    t0 = _time.time()
    try:
        tt.limits(np.zeros(0), None, 10 ** 9)
    except MaskError:
        pass
    dt_empty = _time.time() - t0
    if any(t_.total != 0 or t_.status is not None for t_ in (tt, t_none, ts_x, ti_x)):
        bad3.append("錯誤的輸入動到計數")
    check(not bad3 and dt_empty < 0.1,
          f"第三輪審查的輸入檢查：{len(r3_cases) + len(r3_matlab_cases)} 種錯誤輸入都丟指定 ID 的 MaskError（英文＋繁中）——scope_spectra 中途改通道數／實數↔複數"
          f"（averages 1 與 4、短呼叫後再改）→ inputSpecChanged、0 通道、two_sided 非 bool；limits f 空 × 10^9 通道 → tooLarge"
          f"（{dt_empty * 1e3:.1f} ms）、xlim 在旗標關時也檢查；panel_row 非 dict／欄位型別不對 → badStatus、labels → badLabels；"
          f"failing_channels_matlab(['a']、np.array(5)、[1, True] 等) → badFailingChannels（panel_row 的 0-d FailingChannels → badStatus）；"
          f"labels 在 status None／沒測時也檢查；test 的 time／xlim／replace_last／foffset（含 none 不測、0 個通道時）；"
          f"第五輪：xlim／ylim ±Inf／反向／相等（含 scalar_over_xlim、inf_as_axis_limits、mask_limits、mask_breakpoints、mask_polyline）→ badAxisLimits、"
          f"通道號碼 1e300／2^24+1／Inf → badFailingChannels（panel_row → badStatus）、NumPassedTests > NumTotalTests → badStatus、success_rate(3, 2) → badCounts、"
          f"foffset NaN／±Inf／[0 NaN]（limits／test／none／0 通道／scope_spectra）→ MATLAB:expectedFinite；計數不動"
          + (f"（不一致：{bad3}）" if bad3 else ""))
    # 第四輪審查：合法的邊界輸入照常接受（0-d 修正沒有擋掉一維陣列、labels 提前檢查沒有擋掉合法 labels、0 通道的合法 foffset）
    t_none0 = MaskTester(MaskConfig(EnabledMasks="none"))
    good4 = (failing_channels_matlab(np.array([2, 3])) == [2, 3] and failing_channels_matlab(np.array([2.0])) == 2
             and failing_channels_matlab(np.zeros(0)) == [] and failing_channels_matlab((1, 4)) == [1, 4]
             and panel_row(None, labels=["a"]) == PANEL_EMPTY_ROW and panel_row(st_with(tested=False), labels=("a", "b")) == PANEL_EMPTY_ROW
             and panel_row(st_with(FailingChannels=np.array([1])), labels=["L"])[6] == "L"
             and t_none0.test(f, np.zeros((0, f.size)), foffset=0.0) == {"tested": False}
             and t_none0.test(f, np.zeros((0, f.size)), foffset=np.zeros(0)) == {"tested": False} and t_none0.total == 0)
    check(good4, "第四輪審查的合法邊界輸入照常接受：failing_channels_matlab 一維陣列／[2.0]／空／tuple；panel_row(None 或沒測, labels 合法) "
                 "→ 空列；FailingChannels np.array([1]) 配 labels；none、0 個通道的 test 用 foffset 0.0／空陣列 → tested False、計數不動")
    # 第五輪審查：foffset（scope 的 FrequencyOffset）對 MATLAB validateattributes 'finite' 樣板（finite_template.json，R2025a 實跑）逐筆比：
    # NaN／Inf／-Inf／[0 NaN] → MATLAB:expectedFinite「Expected FrequencyOffset to be finite.」一字不差；[0 10]／0 接受
    ft_path = os.path.join(d, "finite_template.json")
    bad5: List[str] = []
    n_ft = 0
    if os.path.isfile(ft_path):
        with open(ft_path, encoding="utf-8") as fh:
            FT = json.load(fh)
        for r in FT["cases"]:
            n_ft += 1
            val = literal(r["value"])
            try:
                got = tt._offsets(val, 2)
                if not r["ok"]:
                    bad5.append(f"{r['value']} 應該要錯（{r['id']}）卻接受了")
                elif got.shape != (2,) or not np.array_equal(got, np.broadcast_to(np.asarray(val, dtype=float).ravel(), (2,))):
                    bad5.append(f"{r['value']} → {got!r}")
            except MaskError as ex:
                if r["ok"]:
                    bad5.append(f"{r['value']} 應該接受卻錯了：{ex.identifier}")
                elif ex.identifier != r["id"] or ex.message != r["msg"] or not ex.message_zh:
                    bad5.append(f"{r['value']}：{ex.identifier} / {ex.message!r} vs MATLAB {r['id']} / {r['msg']!r}")
        # 同一個樣板也是 MaskFrequencyOffset 實測訊息的樣板（probe_config.json：Expected MaskFrequencyOffset to be finite.）
        msg_mfo = next((r["msg"] for r in P["cfg_cases"] if r["prop"] == "MaskFrequencyOffset" and r["id"] == "MATLAB:expectedFinite"), None)
        if msg_mfo != FT["cases"][0]["msg"].replace("FrequencyOffset", "MaskFrequencyOffset") or not FT["matlab_version"].startswith("25.1"):
            bad5.append(f"樣板不一致：{msg_mfo!r} vs {FT['cases'][0]['msg']!r}（{FT['matlab_version']}）")
    else:
        bad5.append("沒有 finite_template.json")
    check(not bad5, f"第五輪審查：foffset（scope 的 FrequencyOffset）vs MATLAB R2025a validateattributes 'finite' 樣板 finite_template.json {n_ft} 組"
                    "（NaN／Inf／-Inf／[0 NaN] → MATLAB:expectedFinite「Expected FrequencyOffset to be finite.」一字不差；[0 10]／0 接受；"
                    "和 MaskFrequencyOffset 實測訊息同一個樣板）——ID 是審查 probe_r4_offset.m 在 spectrumAnalyzer 上設 sa.FrequencyOffset 實測的，"
                    "以前 NaN／Inf 偏移讓限值全 NaN、測試悄悄通過" + (f"（不一致：{bad5}）" if bad5 else ""))
    # 第六輪審查：foffset 的 ID 與英文文字對 R2025a spectrumAnalyzer 設 sa.FrequencyOffset 的實測（probe_r5_offset.m／.json，15 組；scope 物件
    # 沒顯示）逐筆比：'abc' → invalidType 只有「double」一種型別、true 再加「Instead its type was logical.」、[] → expectedVector、0+1i → expectedReal、
    # NaN／Inf／-Inf／[0 NaN]／[0 -Inf] → expectedFinite 一字不差；[1;2]／[1 2 3]／±1e308 接受。已知差異：single(5)／int32(5) scope 拒收、DSV 收 numpy 純量。
    # scope_spectra() 同一個屬性：純量案例同樣的 ID 與文字；向量案例 → DSV 的 badScalarArgument（一條頻率格只配一個偏移）。
    pr_path = os.path.join(d, "probe_r5_offset.json")
    bad6: List[str] = []
    known6: List[str] = []
    n_pr = n_pr_ss = 0
    if os.path.isfile(pr_path):
        with open(pr_path, encoding="utf-8") as fh:
            PR = json.load(fh)
        x_ss = np.zeros(1000)
        for r in PR["cases"]:
            n_pr += 1
            m_typ = re.search(r"Instead its type was (\w+)\.", r["msg"])
            typ = m_typ.group(1) if m_typ else None
            val = literal(r["value"])
            if typ in ("single", "int32"):
                val = (np.float32 if typ == "single" else np.int32)(val)
            arr = np.asarray(val)
            n = int(arr.size) if arr.dtype.kind in "iuf" and arr.size > 1 else 2
            try:
                got = tt._offsets(val, n)
                if r["ok"]:
                    if got.shape != (n,) or not np.array_equal(got, np.broadcast_to(arr.astype(float).ravel(), (n,))):
                        bad6.append(f"{r['value']} → {got!r}")
                elif typ in ("single", "int32"):
                    known6.append(f"{typ}({r['value']})：scope {r['id']}「{m_typ.group(0)}」，DSV 收 numpy {arr.dtype}")
                else:
                    bad6.append(f"{r['value']} 應該要錯（{r['id']}）卻接受了")
            except MaskError as ex:
                if r["ok"]:
                    bad6.append(f"{r['value']} 應該接受卻錯了：{ex.identifier}")
                elif ex.identifier != r["id"] or ex.message != r["msg"] or not ex.message_zh:
                    bad6.append(f"{r['value']}：{ex.identifier} / {ex.message!r} vs scope {r['id']} / {r['msg']!r}")
            if typ in ("single", "int32"):
                continue
            n_pr_ss += 1
            try:
                scope_spectra([x_ss], 1000.0, 1000, foffset=val)
                if not r["ok"] or n != 2:
                    bad6.append(f"scope_spectra foffset {r['value']} 應該要錯卻接受了")
            except MaskError as ex:
                if r["ok"]:
                    if not (n > 1 and ex.identifier == _ID_DSV + "badScalarArgument"):
                        bad6.append(f"scope_spectra foffset {r['value']}：{ex.identifier}（向量應該是 DSV 的 badScalarArgument）")
                elif ex.identifier != r["id"] or ex.message != r["msg"]:
                    bad6.append(f"scope_spectra foffset {r['value']}：{ex.identifier} / {ex.message!r} vs scope {r['id']} / {r['msg']!r}")
        if not PR["matlab_version"].startswith("25.1") or len(known6) != 2 or n_pr != 15:
            bad6.append(f"版本 {PR['matlab_version']}、{n_pr} 組、已知差異 {len(known6)} 個（應 15 組、2 個）")
        # 和屬性那串 10 種型別的文字（probe_config.json 的 UpperMask 'a'）不同：scope 只列 double
        msg_prop = next((c["msg"] for c in P["cfg_cases"] if c["id"] == "MATLAB:invalidType"), "")
        if not (msg_prop.endswith(_NUMERIC_TYPES) and _OFFSET_TYPE_MSG.endswith("\n\ndouble") and _NUMERIC_TYPES != "double"):
            bad6.append(f"型別清單：屬性 {msg_prop!r} vs scope {_OFFSET_TYPE_MSG!r}")
    else:
        bad6.append("沒有 probe_r5_offset.json")
    check(not bad6, f"第六輪審查：foffset（scope 的 FrequencyOffset）vs R2025a spectrumAnalyzer 設 sa.FrequencyOffset 的實測 probe_r5_offset.json {n_pr} 組"
                    "（'abc' → MATLAB:invalidType 只列 double、true 再加「Instead its type was logical.」、[] → expectedVector、0+1i → expectedReal、"
                    f"NaN／Inf／-Inf／[0 NaN]／[0 -Inf] → expectedFinite，ID 與英文一字不差；[1;2]／[1 2 3]／±1e308 接受）；scope_spectra() {n_pr_ss} 組"
                    "同樣（向量 → DSV badScalarArgument）；已知差異（DSV 自行決定）：" + "；".join(known6)
                    + "；第六輪前 'abc' 給的是屬性的 10 種型別那串" + (f"（不一致：{bad6}）" if bad6 else ""))
    # 第七輪審查：FrequencyOffset 的形狀與更多型別（probe_r6_review.m／.json，13 組，R2025a spectrumAnalyzer 物件沒顯示）：[1 2;3 4] → expectedVector、
    # [true false] → invalidType「Instead its type was logical.」、[1 2]'／1／-0／0.5 接受、[NaN NaN] → expectedFinite，ID 與英文一字不差。
    # 已知差異（見模組說明）：zeros(1,0)／zeros(0,1) MATLAB 接受（listener 警告）→ DSV 有通道 badFrequencyOffset、0 通道收、scope_spectra badScalarArgument；
    # "abc"（string）MATLAB 多印「Instead its type was string.」，Python str 當 char；uint8(3)／single([1 2]) MATLAB 拒收、DSV 收 numpy 型別；{5}（cell）Python 沒有。
    pr6_path = os.path.join(d, "probe_r6_review.json")
    bad7: List[str] = []
    known7: List[str] = []
    n7 = 0
    x_ss = np.zeros(1000)                        # probe_r5 的區塊沒跑到（檔案缺）時這裡也要有
    PY6 = {"[1 2;3 4]": np.array([[1.0, 2.0], [3.0, 4.0]]), "[true false]": np.array([True, False]), "zeros(1,0)": np.zeros((1, 0)),
           "zeros(0,1)": np.zeros((0, 1)), '"abc"': "abc", "{5}": None, "uint8(3)": np.uint8(3), "single([1 2])": np.array([1, 2], dtype=np.float32),
           "[1 2]'": np.array([[1.0], [2.0]]), "1": 1.0, "-0": -0.0, "0.5": 0.5, "[NaN NaN]": np.array([math.nan, math.nan])}

    def ids_of(fn_list):
        out = []
        for fn_ in fn_list:
            try:
                r_ = fn_()
                out.append(r_.shape if isinstance(r_, np.ndarray) else "accepted")
            except MaskError as ex_:
                out.append(ex_.identifier)
        return out

    if os.path.isfile(pr6_path):
        with open(pr6_path, encoding="utf-8") as fh:
            PR6 = json.load(fh)
        for r in PR6["cases"]:
            n7 += 1
            v = r["value"]
            if v not in PY6:
                bad7.append(f"{v}：selftest 沒有對應的 Python 值")
                continue
            val = PY6[v]
            m_typ = re.search(r"Instead its type was (\w+)\.", r["msg"])
            typ = m_typ.group(1) if m_typ else None
            if v == "{5}":
                if r["id"] == "MATLAB:invalidType" and typ == "cell":
                    known7.append(f"{v}：scope {r['id']}「{m_typ.group(0)}」，Python 沒有 cell 型別（不適用）")
                else:
                    bad7.append(f"{v}：MATLAB {r['id']} / {r['msg']!r}")
                continue
            if typ in ("uint8", "single"):
                arr_ = np.asarray(val)
                n_ = int(arr_.size) if arr_.size > 1 else 2
                res = ids_of([lambda: tt._offsets(val, n_)])
                if r["id"] == "MATLAB:invalidType" and r["msg"] == _OFFSET_TYPE_MSG + f"\n\nInstead its type was {typ}." and res == [(n_,)]:
                    known7.append(f"{v}：scope {r['id']}「{m_typ.group(0)}」，DSV 收 numpy {arr_.dtype}")
                else:
                    bad7.append(f"{v}：MATLAB {r['id']} / {r['msg']!r}，DSV {res}")
                continue
            if v in ("zeros(1,0)", "zeros(0,1)"):
                res = ids_of([lambda: tt._offsets(val, 1), lambda: tt._offsets(val, 2), lambda: tt._offsets(val, 0),
                              lambda: scope_spectra([x_ss], 1000.0, 1000, foffset=val)])
                if r["ok"] and r["msg"] == v and res == [_ID_DSV + "badFrequencyOffset", _ID_DSV + "badFrequencyOffset", (0,), _ID_DSV + "badScalarArgument"]:
                    known7.append(f"{v}：MATLAB 接受（讀回 {r['msg']}，PropertyChanged listener 警告 Index exceeds array bounds）→ DSV 有通道 badFrequencyOffset、"
                                  "0 通道收、scope_spectra badScalarArgument")
                else:
                    bad7.append(f"{v}：MATLAB ok={r['ok']} {r['msg']!r}，DSV {res}")
                continue
            if v == '"abc"':
                res = ids_of([lambda: tt._offsets(val, 2), lambda: scope_spectra([x_ss], 1000.0, 1000, foffset=val)])
                try:
                    tt._offsets(val, 2)
                    msg_dsv = ""
                except MaskError as ex:
                    msg_dsv = ex.message
                if res == ["MATLAB:invalidType"] * 2 and r["id"] == "MATLAB:invalidType" and msg_dsv == _OFFSET_TYPE_MSG and typ == "string" \
                        and r["msg"] == _OFFSET_TYPE_MSG + "\n\nInstead its type was string.":
                    known7.append(f"{v}（MATLAB string）：scope 多一行「{m_typ.group(0)}」，Python str 當 char（probe_r5 'abc' 的文字）")
                else:
                    bad7.append(f"{v}：{res} / {msg_dsv!r} vs {r['id']} / {r['msg']!r}")
                continue
            arr = np.asarray(val)
            n = int(arr.size) if arr.size > 1 else 2
            try:
                got = tt._offsets(val, n)
                if not r["ok"]:
                    bad7.append(f"{v} 應該要錯（{r['id']}）卻接受了")
                else:
                    want = np.asarray(literal(r["msg"]), dtype=float).ravel()       # mat2str 讀回的值（[1;2]、1、0、0.5）
                    if got.shape != (n,) or not np.array_equal(np.broadcast_to(want, (n,)), got) or not np.array_equal(arr.astype(float).ravel(), want):
                        bad7.append(f"{v} → {got!r} vs MATLAB 讀回 {r['msg']!r}")
            except MaskError as ex:
                if r["ok"]:
                    bad7.append(f"{v} 應該接受卻錯了：{ex.identifier}")
                elif ex.identifier != r["id"] or ex.message != r["msg"] or not ex.message_zh:
                    bad7.append(f"{v}：{ex.identifier} / {ex.message!r} vs scope {r['id']} / {r['msg']!r}")
            if not r["ok"]:                      # scope_spectra() 同一條路：同樣的 ID 與文字
                try:
                    scope_spectra([x_ss], 1000.0, 1000, foffset=val)
                    bad7.append(f"scope_spectra foffset {v} 應該要錯")
                except MaskError as ex:
                    if ex.identifier != r["id"] or ex.message != r["msg"]:
                        bad7.append(f"scope_spectra foffset {v}：{ex.identifier} / {ex.message!r}")
        # 沒探過的形狀照 DSV 的決定：0×0／一維空／(0,5)／三維 → expectedVector（0 通道時 0×0 與一維空收）；limits() 走同一條路；(2,1)／(1,2) 是向量
        shape_res = ids_of([lambda: tt._offsets(np.zeros((0, 0)), 2), lambda: tt._offsets(np.zeros(0), 2), lambda: tt._offsets([], 1),
                            lambda: tt._offsets(np.zeros((0, 5)), 2), lambda: tt._offsets(np.zeros((1, 1, 2)), 2),
                            lambda: tt._offsets(np.zeros((0, 0)), 0), lambda: tt._offsets(np.zeros(0), 0),
                            lambda: ts_x.limits(f, None, 2, foffset=PY6["[1 2;3 4]"]), lambda: scope_spectra([x_ss], 1000.0, 1000, foffset=np.zeros((1, 1, 2))),
                            lambda: tt._offsets(np.zeros((2, 1)), 2), lambda: tt._offsets(np.zeros((1, 2)), 2)])
        if shape_res != ["MATLAB:expectedVector"] * 5 + [(0,), (0,)] + ["MATLAB:expectedVector"] * 2 + [(2,), (2,)]:
            bad7.append(f"沒探過的形狀：{shape_res}")
        if not PR6["matlab_version"].startswith("25.1") or n7 != 13 or len(known7) != 6:
            bad7.append(f"版本 {PR6['matlab_version']}、{n7} 組、已知差異 {len(known7)} 個（應 13 組、6 個）")
    else:
        bad7.append("沒有 probe_r6_review.json")
    check(not bad7, f"第七輪審查：foffset（scope 的 FrequencyOffset）形狀與型別 vs R2025a spectrumAnalyzer 實測 probe_r6_review.json {n7} 組——"
                    "[1 2;3 4] → MATLAB:expectedVector（以前 ravel 後當 4 個值收）、[true false] → invalidType「Instead its type was logical.」、"
                    "[1 2]'／1／-0／0.5 接受、[NaN NaN] → expectedFinite，ID 與英文一字不差（scope_spectra 同）；沒探過的形狀 0×0／一維空／(0,5)／三維 → "
                    "expectedVector（0 通道時 0×0／一維空收）、(2,1)／(1,2) 是向量；已知差異（DSV 自行決定）：" + "；".join(known7)
                    + (f"（不一致：{bad7}）" if bad7 else ""))
    # 第五輪審查的合法邊界：通道號碼到 2^24、xlim 大但有限、passed＝total、foffset 每通道一個（有限）、f 含 Inf 時 x 軸範圍由有限的 bin 推
    lu_inf, _ = ts_x.limits(np.r_[f, math.inf], None, 1)
    t_ok5 = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12))
    good5 = (failing_channels_matlab([MAX_ELEMENTS]) == MAX_ELEMENTS and failing_channels_matlab([1, MAX_ELEMENTS]) == [1, MAX_ELEMENTS]
             and _pair((0, 1e308), "xlim") == (0.0, 1e308) and _pair(np.array([-3, 2]), "ylim") == (-3.0, 2.0)
             and panel_row(st_with(NumPassedTests=2, NumTotalTests=2, SuccessRate=100.0))[1:3] == (2, 2)
             and success_rate(2, 2) == 100.0 and math.isnan(success_rate(0, 0))
             and tt.limits(f, None, 2, [0.0, 10.0])[0].shape == (2, f.size) and t_ok5.test(f, spec[0], foffset=np.float32(5))["tested"]
             and lu_inf.shape == (1, f.size + 1) and bool(np.all(lu_inf[0, :-1] == -10.0)) and math.isnan(lu_inf[0, -1])
             and ts_x.total == 0 and tt.total == 0)
    check(good5, "第五輪審查的合法邊界輸入照常接受：通道號碼 2^24、xlim (0, 1e308)、整數 ylim、NumPassedTests＝NumTotalTests、success_rate(2, 2)／(0, 0)、"
                 "foffset 每通道一個有限值／np.float32；scalar_over_xlim 沒給 xlim 而 f 含 Inf → 範圍由有限的 bin 推（Inf 那個 bin 限值 NaN）"
                 + ("" if good5 else f"（lu_inf={lu_inf[0, -3:]}）"))
    # 第三輪審查：修好的行為——向量化 limits 和以前的逐通道結果位元相同、同 spec 的呼叫照舊、time 存成 float、panel_row 正規化
    cfg_m = MaskConfig(EnabledMasks="upper-and-lower", UpperMask=[[-math.inf, -17], [90, -17], [90, math.nan], [110, 30], [200, -5], [math.inf, -17]],
                       LowerMask=[[0, -80], [250, -60], [250, -70], [500, -75]], MaskFrequencyOffset=10)
    offs = np.array([0.0, 37.5, -12.25])
    bad_l: List[str] = []
    for flags in ((False, False), (True, False), (False, True), (True, True)):
        tm = MaskTester(cfg_m, scalar_over_xlim=flags[0], inf_as_axis_limits=flags[1])
        for xl in ((0.0, 500.0), None):
            for off_ in (offs, 25.0, np.array([5.0, 5.0, 5.0])):
                lu_, ll_ = tm.limits(f, xl, 3, off_)
                ob = np.broadcast_to(np.asarray(off_, dtype=float).ravel(), (3,))
                # 參考：以前的逐通道迴圈；沒給 xlim 時 x 軸範圍＝所有通道顯示頻率的最小／最大（共用 x 軸，見模組說明）
                xs = [f + ob[ch] for ch in range(3)]
                xl_ref = xl if xl is not None else (min(float(v.min()) for v in xs), max(float(v.max()) for v in xs))
                if bool((ob == ob[0]).all()) and xl is None:
                    xl_ref = (float(xs[0].min()), float(xs[0].max()))
                for nm, mine_, mask_ in (("上", lu_, cfg_m.UpperMask), ("下", ll_, cfg_m.LowerMask)):
                    ref_ = np.vstack([mask_limits(mask_, xs[ch], xl_ref, 10, flags[1], flags[0]) for ch in range(3)])
                    ok_, why_ = _same(mine_, ref_)
                    if not ok_:
                        bad_l.append(f"旗標 {flags} xlim {xl} 偏移 {off_}：{nm}限 {why_}")
    ts_ = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12), scalar_over_xlim=True)
    lu_s, _ = ts_.limits(f, None, 2, [0.0, 100.0])          # 共用 x 軸＝[0, 600]：兩個通道的每個 bin 都在範圍內 → 全部 −12
    big_cfg = MaskConfig(EnabledMasks="upper-and-lower", UpperMask=[[0, -40], [5, 0], [10, -40]], LowerMask=-90)
    fb16 = np.arange(16.0)
    t0 = _time.time()
    lu_b, ll_b = MaskTester(big_cfg).limits(fb16, None, 10 ** 6, 0.0)
    dt_b1 = _time.time() - t0
    offs_b = np.arange(10 ** 6) * 1e-3
    t0 = _time.time()
    lu_b2, _ = MaskTester(big_cfg).limits(fb16, None, 10 ** 6, offs_b)
    dt_b2 = _time.time() - t0
    big_ok = (lu_b.shape == (10 ** 6, 16) and ll_b.shape == (10 ** 6, 16) and _same(lu_b[-1], mask_limits(big_cfg.UpperMask, fb16))[0]
              and np.all(ll_b == -90.0) and _same(lu_b2[1234], mask_limits(big_cfg.UpperMask, fb16 + offs_b[1234]))[0]
              and int(np.isfinite(lu_b2[1234]).sum()) == 9 and int(np.isfinite(lu_b[-1]).sum()) == 11)
    del lu_b, ll_b, lu_b2, offs_b
    # 同 spec 的多次呼叫照舊；換 spec 就開新的一串
    fA, SA = scope_spectra([x2, x2 + 1.0, np.zeros(10, float)[:, None].repeat(2, 1)], 1000, 1000, 4)
    fC, SC = scope_spectra([xc, xc + 1j], 1000, 1000, 1)
    fR, SR = scope_spectra([x1], 1000, 1000, 1)
    spec_ok = (len(SA) == 3 and SA[0].shape == (513, 2) and SA[2] is None and fC.size == 1024 and SC[1].shape == (1024, 1)
               and fR.size == 513 and SR[0].shape == (513, 1))
    tf = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12))
    st_f1 = tf.test(f, spec[0], time=np.float64(3.999))
    st_f2 = tf.test(f, spec[0], time=4000)
    st_f3 = tf.test(f, spec[0], replace_last=np.bool_(True))
    time_ok = (type(st_f1["SimulationTime"]) is float and st_f1["SimulationTime"] == 3.999 and type(st_f2["SimulationTime"]) is float
               and st_f2["SimulationTime"] == 4000.0 and st_f3["SimulationTime"] is None and st_f3["NumTotalTests"] == 2)
    row_np = panel_row(st_with(IsCurrentlyPassing=np.bool_(False), upper_status=np.bool_(False), NumPassedTests=np.int64(0),
                               NumTotalTests=np.int64(1), SuccessRate=np.float64(0.0), FailingChannels=np.array([1, 2])),
                       "zh", labels=["左", "右"])
    row_ok = (row_np == (0.0, 0, 1, "失敗", "失敗", "--", "左, 右") and panel_row({}) == PANEL_EMPTY_ROW
              and panel_row({"tested": False}) == PANEL_EMPTY_ROW and panel_row(st_with(FailingChannels=[3]), labels=["a"])[6] == "3"
              and failing_channels_matlab([1.0, 2]) == [1, 2] and failing_channels_matlab(np.array([3])) == 3
              and failing_channels_matlab([]) == [] and failing_channels_matlab(()) == [])
    check(not bad_l and np.all(lu_s == -12.0) and big_ok and dt_b1 < 3.0 and dt_b2 < 3.0 and spec_ok and time_ok and row_ok,
          f"第三輪審查的行為：向量化 limits 和逐通道 mask_limits 位元相同（4 種旗標組合 × xlim 給／不給 × 偏移各通道不同／純量／全部相同，"
          f"上下模板各 24 組）；旗標開、沒給 xlim、偏移不同時 x 軸＝所有通道的範圍；10^6 通道 × 16 bin：純量偏移 {dt_b1:.2f}s、"
          f"每通道不同偏移 {dt_b2:.2f}s（舊版逐通道迴圈：同一組模板 10^5 通道 × 16 bin 實測 3.1 s、f 空 × 10^5 通道 2.6 s；審查量到 10^6 通道 53 s）；scope_spectra 同通道數／同實複數的連續呼叫照舊、新的一串可以換；test 的 time 存成 float"
          f"（np.float64、int 都轉）；panel_row 收 numpy bool／整數並正規化、labels 超出範圍用號碼；failing_channels_matlab 收 1.0、ndarray、空"
          + (f"（不一致：{bad_l[:3]}）" if bad_l else "")
          + ("" if big_ok and spec_ok and time_ok and row_ok else f"（big {big_ok}、spec {spec_ok}、time {time_ok}、row {row_ok} {row_np}）"))
    # 自行決定（沒有 MATLAB 參考值）：沒有 bin 的頻譜不測、計數凍結；全 NaN 的頻譜照 IEEE 通過（比較為假）、差值全 NaN；numpy 純量型別當參數可以
    t0b = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12))
    s0b = t0b.test(np.zeros(0), np.zeros((2, 0)))
    s_nan = MaskTester(MaskConfig(EnabledMasks="upper-and-lower", UpperMask=-12, LowerMask=-200)).test(f, np.full((2, f.size), np.nan))
    f_np, S_np = scope_spectra([np.zeros(1000)], np.float64(1000.0), np.int64(1000), np.int32(1), foffset=np.float32(0))
    ok_dec = (s0b == {"tested": False} and t0b.total == 0 and t0b.status is None
              and s_nan["tested"] and s_nan["IsCurrentlyPassing"] and s_nan["n_fail_upper"] == [0, 0] and s_nan["n_fail_lower"] == [0, 0]
              and all(math.isnan(v) for v in s_nan["upper_excess_dB"] + s_nan["lower_margin_dB"])
              and f_np.size == 513 and len(S_np) == 1 and S_np[0].shape == (513, 1)
              and MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12)).limits(f, None, np.int64(2))[0].shape == (2, f.size)
              and simulation_time(None, np.int64(4000), np.float64(1000.0)) == 3.999 and nfft_auto(np.int64(4000)) == 4000)
    check(ok_dec, "自行決定：沒有 bin 的頻譜（f 長度 0）不測、計數凍結、回傳 {tested: False}；全 NaN 頻譜照 IEEE 通過（S > 限值為假）、"
                  "upper_excess_dB／lower_margin_dB 全 NaN；numpy 純量（float64／int64／int32／float32）當 fs／window_length／averages／"
                  "foffset／nch／n_samples 可以" + ("" if ok_dec else f"（s0b={s0b}、s_nan 通過={s_nan.get('IsCurrentlyPassing')}）"))
    # 極端但合法的輸入：不能有 numpy RuntimeWarning（selftest 以 -W error::RuntimeWarning 跑；這裡另外用 catch_warnings 記錄），數值照 IEEE
    import warnings
    with warnings.catch_warnings(record=True) as wlog:
        warnings.simplefilter("always")
        m0 = parse_mask("[0 -17; 0 30; 500 -17]")                 # 垂直階梯在 0 Hz：第 2 個斷點加 realmin
        F0, P0 = mask_breakpoints(m0)
        l0 = mask_limits(m0, f)
        s0 = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=m0)).test(f, spec[0])
        slope0 = (P0[2] - P0[1]) / (F0[2] - F0[1])
        inf_hi = validate_mask([[math.inf, 1], [math.inf, 2]])
        inf_lo = validate_mask([[-math.inf, 1], [-math.inf, 2]], "LowerMask")
        l_hi, l_lo = mask_limits(inf_hi, f), mask_limits(inf_lo, f)
        r_big = mask_test(np.zeros((1, 3)), np.full((1, 3), 1e308), np.full((1, 3), -1e308), 1e308)
        F_big, _ = mask_breakpoints([[0, 1], [1e308, 2]], mfo=1e308)
        p_big = mask_polyline([[0, 1e308], [500, 1e308]], "upper", [0, 500], [-80, 20], ref=1e308)
        # 第二輪審查：斷點跨度超過 realmax（diff 溢位成 Inf，非遞減 → MATLAB 接受）走過 parse_mask／MaskConfig／mask_limits／test 都不能警告
        m_span = parse_mask("[-1e308 1; 1e308 2]")
        m_span2 = MaskConfig(UpperMask=[[-8.99e307, 1], [8.99e307, 2]]).UpperMask
        l_span = mask_limits(m_span, f)
        s_span = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=m_span)).test(f, spec[0])
        # 第二輪審查：scope_spectra 的極端樣本（welch 裡的 |FFT|² 溢位、Inf 樣本的 0·Inf）不能漏出 numpy 警告
        _, S_huge = scope_spectra([np.full(1000, 1e160)], 1000.0, 1000)
        x_inf = np.zeros(1000)
        x_inf[3] = math.inf
        _, S_inf1 = scope_spectra([x_inf, np.ones(1000)], 1000.0, 1000, 1)    # N＝1：下一次呼叫直接取該段週期圖，Inf／NaN 不留
        _, S_inf4 = scope_spectra([x_inf, np.ones(1000)], 1000.0, 1000, 4)    # N＝4：NaN 留在指數平均裡（IEEE）
        with np.errstate(divide="ignore"):                                    # 全 1 訊號的 Hann 週期圖：非 DC bin 功率 0 → −Inf dBm（合法）
            ones_dB = 10.0 * np.log10(SP.welch(np.ones(1000), 1000.0, SP.design_window("hann", 1000), 0, 1024, "onesided")["power"]) + 30.0
    ok_ext = (F0.tolist() == [0.0, REALMIN, 500.0] and P0.tolist() == [-17.0, 30.0, -17.0]
              and math.isnan(l0[0]) and int(np.isnan(l0).sum()) == 1 and np.array_equal(l0[1:], 30.0 + (f[1:] - REALMIN) * slope0)
              and l0[-1] == -17.0 and s0["tested"] and not s0["IsCurrentlyPassing"] and s0["FailingChannels"] == [1, 2]
              and inf_hi.shape == (2, 2) and inf_lo.shape == (2, 2) and np.isnan(l_hi).all() and np.isnan(l_lo).all()
              and r_big["passing"] and r_big["n_fail_upper"] == [0] and r_big["n_fail_lower"] == [0]
              and F_big.tolist() == [1e308, math.inf] and np.all(p_big["y"] == 20.0) and np.all(np.isinf(p_big["y_raw"]))
              and m_span.shape == (2, 2) and m_span2.shape == (2, 2) and np.all(l_span == 1.0) and s_span["tested"] and not s_span["IsCurrentlyPassing"]
              and S_huge[0][0, 0] == math.inf and not np.isnan(S_huge[0]).any()
              and np.isnan(S_inf1[0]).any() and not np.isnan(S_inf1[1]).any() and np.array_equal(S_inf1[1][:, 0], ones_dB)
              and np.isnan(S_inf4[1]).any()
              and not wlog)
    check(ok_ext, f"極端值不警告：[0 -17; 0 30; 500 -17]（斷點 F＝[0, realmin, 500]）→ 0 Hz 那 1 個 bin 的斜率 47/realmin 溢位、限值 NaN 不測，"
                  f"其餘 bin 是 30→−17 的斜線（500 Hz 給 −17.0，位元相同；音調 94–101 Hz 超過 → 兩通道失敗）；[Inf a; Inf b]／[-Inf a; -Inf b] 照 MATLAB "
                  f"接受、限值全 NaN；1e308＋1e308 的限值／斷點／色塊成 Inf；[-1e308 1; 1e308 2]（diff 溢位成 Inf）parse_mask／MaskConfig 接受、"
                  f"斜率 1/Inf＝0 → 限值全 1、測試照跑；scope_spectra 1e160 樣本 → DC Inf dBm、Inf 樣本 → NaN 頻譜，N＝1 的下一次呼叫＝該段週期圖"
                  f"（位元相同）、N＝4 留 NaN；numpy 警告 {len(wlog)} 個"
                  + ("" if ok_ext else f"（{[str(w.message) for w in wlog]}；l0[:3]={l0[:3]}、s0={s0.get('FailingChannels')}）"))

    # 自行決定的部分（沒有 MATLAB 參考值，只檢查自我一致）
    t2 = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=[[-math.inf, -30], [math.inf, -30]]), inf_as_axis_limits=True)
    lu2, _ = t2.limits(f, [0, 500], 2)
    s2 = t2.test(f, spec[0], [0, 500])
    t3 = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=[[-math.inf, -30], [math.inf, -30]]))
    s3 = t3.test(f, spec[0], [0, 500])
    check(np.all(lu2 == -30) and not s2["IsCurrentlyPassing"] and s2["FailingChannels"] == [1, 2] and s3["IsCurrentlyPassing"]
          and np.isnan(t3.limits(f, [0, 500], 2)[0]).all(),
          "−Inf／Inf 斷點：預設照實測（整段 NaN 不測 → 通過；mask_A_inf_freq_ends）；inf_as_axis_limits=True（非分析器行為）時 ±Inf 當 x 軸範圍"
          "（限值 −30 → 兩個通道都失敗）")
    pu = mask_polyline([[-math.inf, -17], [90, -17], [90, math.nan], [110, 30], [math.inf, -17]], "upper", [0, 500], [-80, 20], mfo=10, ref=5)
    ps = mask_polyline(-12, "lower", [120, 480], [-80, 20])
    pi_ = mask_polyline(math.inf, "upper", [0, 500], [-80, 20])
    # 有 NaN 位準（照 MATLAB 介面的畫法算出的預期值：[0 50;100 NaN;200 -10;500 -10]、xlim [0,500]、
    # ylim [-80,0] → x [0,100,200,500,500,0]、y [50,0,-10,-10,0,0]）——遠邊是軸界，不是最大的有限位準；沒有 NaN 時照舊 max／min
    pn = mask_polyline([[0, 50], [100, math.nan], [200, -10], [500, -10]], "upper", [0, 500], [-80, 0])
    pn0 = mask_polyline([[0, 50], [100, -20], [200, -10], [500, -10]], "upper", [0, 500], [-80, 0])
    pl_ = mask_polyline([[0, -150], [100, math.nan], [200, -60], [500, -60]], "lower", [0, 500], [-80, 0])
    pl0 = mask_polyline([[0, -150], [100, -70], [200, -60], [500, -60]], "lower", [0, 500], [-80, 0])
    # 純量模板不加 MaskFrequencyOffset（MATLAB 的純量模板畫滿 x 範圍，只有矩陣模板的頻率加偏移）
    psu = mask_polyline(-12, "upper", [0, 500], [-80, 20], mfo=50)
    psl = mask_polyline(-12, "lower", [0, 500], [-80, 20], mfo=50)
    # 最後一列 +Inf 的位準（README：測試用前一列的位準，+Inf 那一列的位準只影響色塊）：寫死的預期值，不和 MaskTester 自己比
    m_inf = [[0, -30], [100, -30], [math.inf, -50]]
    lim_inf = mask_limits(m_inf, [50, 200, 400])
    poly_inf = mask_polyline(m_inf, "upper", [0, 500], [-80, 20])
    check(np.array_equal(pu["x"], [10, 100, 100, 120, 510]) and np.array_equal(pu["y"], [-12, -12, 20, 35, -12]) and pu["edge"] == 20
          and pu["polygon"].shape == (10, 2) and np.array_equal(ps["x"], [120, 480]) and ps["edge"] == -80 and np.all(ps["y"] == -12)
          and np.all(pi_["y"] == 20) and pi_["edge"] == 20
          and np.array_equal(pn["y"], [50, 0, -10, -10]) and pn["edge"] == 0
          and np.array_equal(pn["polygon"], [[0, 50], [100, 0], [200, -10], [500, -10], [500, 0], [200, 0], [100, 0], [0, 0]])
          and pn0["edge"] == 50 and np.array_equal(pl_["y"], [-150, -80, -60, -60]) and pl_["edge"] == -80 and pl0["edge"] == -150
          and np.array_equal(psu["x"], [0, 500]) and np.array_equal(psl["x"], [0, 500])
          and np.array_equal(lim_inf, [-30.0, -30.0, -30.0]) and np.array_equal(poly_inf["x"], [0, 100, 500])
          and np.array_equal(poly_inf["y"], [-30, -30, -50]) and poly_inf["y"][-1] == -50,
          "色塊折線：±Inf 頻率放到 x 軸兩端再加偏移、y＝位準＋ref、上模板遠邊＝max(y 上限, 最大位準)（下模板 min）、有 NaN 位準時遠邊＝y 軸的界"
          "（最大／最小位準遇到 NaN 得 NaN → 遠邊退回軸界），NaN 那點也畫在遠邊、純量畫滿 xlim 而且不加頻率偏移（偏移 50 時"
          "上／下純量的 x 仍是 [0, 500]）、Inf 位準夾到邊；[0 -30; 100 -30; Inf -50]：測試在 100 Hz 以後用前一列的 -30（50／200／400 Hz 的限值"
          f"{lim_inf.tolist()}），色塊的右端照 +Inf 那一列畫到 -50（{poly_inf['y'].tolist()}）")
    bad = []
    for txt, want in (("Inf", math.inf), ("-Inf", -math.inf), (" nan ", math.nan), ("[0 -17; 90 -17; 90 30]", 3), ("0,-17\n90,-17", 2), ("1e3", 1000.0),
                      ("0 -17; 90 -17", [[0.0, -17.0], [90.0, -17.0]])):   # 中括號可省（README「和 MATLAB 不同的地方」：不加括號的矩陣照收）
        try:
            v = parse_mask(txt)
        except MaskError as ex:
            bad.append(f"{txt}（{ex.identifier}）")
            continue
        if isinstance(want, list):
            if not (isinstance(v, np.ndarray) and v.tolist() == want):
                bad.append(txt)
        elif isinstance(want, int):
            if not (isinstance(v, np.ndarray) and v.shape == (want, 2)):
                bad.append(txt)
        elif not (isinstance(v, float) and (v == want or (math.isnan(v) and math.isnan(want)))):
            bad.append(txt)
    zh_fmt_lo = "以實數數值純量或有至少兩列的兩欄矩陣形式輸入下遮罩。"           # zh_CN「有至少两行的两列矩阵」行→列、列→欄
    zh_freq_lo = "下遮罩是矩陣時，第一欄（頻率）不能有 NaN 且必須非遞減。"
    for txt, ident, zh in (("[1 2 3]", "invalidLowerMask", zh_fmt_lo), ("abc", "invalidLowerMask", zh_fmt_lo), ("", "invalidLowerMask", zh_fmt_lo),
                           ("[0 1]", "invalidLowerMask", zh_fmt_lo), ("[0 -10 5; 100 -10 5]", "invalidLowerMask", zh_fmt_lo),
                           ("12abc", "invalidLowerMask", zh_fmt_lo),             # README：上限／下限「12abc」是錯（MATLAB 的欄位寬鬆解析當 12）
                           ("[2 1; 1 2]", "invalidMaskFrequencyData", zh_freq_lo), ("[0 1; NaN 2]", "invalidMaskFrequencyData", zh_freq_lo)):
        try:
            parse_mask(txt, "LowerMask")
            bad.append(txt + "（沒錯）")
        except MaskError as ex:
            if not ex.identifier.endswith(ident) or ex.message_zh != zh:
                bad.append(f"{txt}（{ex.identifier}：{ex.message_zh}）")
    for txt, ident, zh in (("[1 2 3]", "invalidUpperMask", "以實數數值純量或有至少兩列的兩欄矩陣形式輸入上遮罩。"),
                           ("12abc", "invalidUpperMask", "以實數數值純量或有至少兩列的兩欄矩陣形式輸入上遮罩。"),
                           ("[100 -10; 50 -10]", "invalidMaskFrequencyData", "上遮罩是矩陣時，第一欄（頻率）不能有 NaN 且必須非遞減。")):
        try:
            parse_mask(txt)
            bad.append(txt + " upper（沒錯）")
        except MaskError as ex:
            if not ex.identifier.endswith(ident) or ex.message_zh != zh or "UpperMask" in ex.message_zh:
                bad.append(f"{txt} upper（{ex.identifier}：{ex.message_zh}）")
    # 參考位準／頻率偏移欄位＝MATLAB 工具列欄位的寬鬆解析（toolstrip_parse_float）：空字串的參考位準＝不改（None）；Inf／-inf／1e999 收成 ±Inf；
    # '12abc' → 12；NaN（看不懂、只有空白、'NaN'、前面有空白的 ' Inf'）→ 工具列的錯誤；頻率偏移空字串 → 錯，±Inf 照欄位文字擋（DSV 自行決定）
    for fn, txt, ident, zh in ((parse_reference_level, "abc", "invalidReferenceLevel", "以「頻譜峰值」或有限實數純量形式輸入參考位準。"),
                               (parse_reference_level, "NaN", "invalidReferenceLevel", "以「頻譜峰值」或有限實數純量形式輸入參考位準。"),
                               (parse_reference_level, "   ", "invalidReferenceLevel", "以「頻譜峰值」或有限實數純量形式輸入參考位準。"),
                               (parse_reference_level, " Inf", "invalidReferenceLevel", "以「頻譜峰值」或有限實數純量形式輸入參考位準。"),
                               (parse_offset, "", "invalidMaskFrequencyOffset", "以有限實數純量形式輸入頻譜遮罩頻率偏移。"),
                               (parse_offset, "Inf", "invalidMaskFrequencyOffset", "以有限實數純量形式輸入頻譜遮罩頻率偏移。"),
                               (parse_offset, "1e999", "invalidMaskFrequencyOffset", "以有限實數純量形式輸入頻譜遮罩頻率偏移。"),
                               (parse_offset, "x50", "invalidMaskFrequencyOffset", "以有限實數純量形式輸入頻譜遮罩頻率偏移。")):
        try:
            fn(txt)
            bad.append(f"{fn.__name__}({txt!r})（沒錯）")
        except MaskError as ex:
            if not ex.identifier.endswith(ident) or ex.message_zh != zh:
                bad.append(f"{fn.__name__}({txt!r})（{ex.identifier}：{ex.message_zh}）")
    def pv(fn, txt):                                        # 值；丟錯就回 ("error", ID)，不讓 selftest 自己當掉
        try:
            return fn(txt)
        except MaskError as ex:
            return "error", ex.identifier
    pr = lambda t: pv(parse_reference_level, t)              # noqa: E731
    ok = (pr("Spectrum peak") == ("spectrum-peak", None) and pr("頻譜峰值") == ("spectrum-peak", None)
          and pr(" spectrum-peak ") == ("spectrum-peak", None) and pr("") is None
          and pr("-3.5") == ("custom", -3.5) and pr("12abc") == ("custom", 12.0)
          and pr("Inf") == ("custom", math.inf) and pr("-inf") == ("custom", -math.inf)
          and pr("1e999") == ("custom", math.inf) and pr("Infinity") == ("custom", math.inf)
          and pv(parse_offset, "-10") == -10.0 and pv(parse_offset, " 50abc") == 50.0 and pv(parse_offset, "-.5e2") == -50.0)
    if not ok:
        bad.append(f"參考位準／頻率偏移的值：{[pr(t) for t in ('', '12abc', 'Inf', '-inf', '1e999')]}、"
                   f"{[pv(parse_offset, t) for t in ('-10', ' 50abc', '-.5e2')]}")
    # JavaScript 標準 parseFloat 與工具列欄位的解析：2026-10-25 用 Node.js v26 算出標準 parseFloat 的值，以及再加上「文字剛好是
    # Inf／inf／-Inf／-inf → ±Infinity」這一條的值，逐一照抄
    js_cases = (("", "NaN", "NaN"), ("   ", "NaN", "NaN"), ("\t5", 5.0, 5.0), ("\n-3.5e2x", -350.0, -350.0), ("\u00a012", 12.0, 12.0),
                ("\ufeff7", 7.0, 7.0), ("\u20281.5", 1.5, 1.5), ("\u30009", 9.0, 9.0), ("\u180e4", "NaN", "NaN"), ("\x1c5", "NaN", "NaN"),
                ("\x855", "NaN", "NaN"), ("\u200b5", "NaN", "NaN"), ("12abc", 12.0, 12.0), ("+-1", "NaN", "NaN"), (".5", 0.5, 0.5),
                ("5.", 5.0, 5.0), (".", "NaN", "NaN"), ("-.5e-3x", -0.0005, -0.0005), ("1e", 1.0, 1.0), ("1e+", 1.0, 1.0),
                ("1e999", "Inf", "Inf"), ("-1e999", "-Inf", "-Inf"), ("1e-400", 0.0, 0.0), ("0x10", 0.0, 0.0), ("1_000", 1.0, 1.0),
                ("Infinity", "Inf", "Inf"), ("-Infinity", "-Inf", "-Inf"), ("infinity", "NaN", "NaN"), ("Infinityx", "Inf", "Inf"),
                ("Inf", "NaN", "Inf"), ("inf", "NaN", "Inf"), ("-Inf", "NaN", "-Inf"), ("-inf", "NaN", "-Inf"), (" Inf", "NaN", "NaN"),
                ("Inf ", "NaN", "NaN"), ("INF", "NaN", "NaN"), ("+Inf", "NaN", "NaN"), ("NaN", "NaN", "NaN"), ("-0", "-0", "-0"),
                ("1.2.3", 1.2, 1.2), ("3,5", 3.0, 3.0), ("\uff11\uff12", "NaN", "NaN"), ("\u0663", "NaN", "NaN"), ("1/2", 1.0, 1.0),
                ("  -7  ", -7.0, -7.0), ("e5", "NaN", "NaN"), ("--1", "NaN", "NaN"), ("9007199254740993", 9007199254740992.0, 9007199254740992.0))

    def js_same(v, want):
        if want == "NaN":
            return math.isnan(v)
        if want in ("Inf", "-Inf"):
            return v == (math.inf if want == "Inf" else -math.inf)
        if want == "-0":
            return v == 0.0 and math.copysign(1.0, v) < 0
        return v == want
    js_bad = [c for c, jp, jt in js_cases if not (js_same(js_parse_float(c), jp) and js_same(toolstrip_parse_float(c), jt))]
    check(not js_bad, f"JavaScript parseFloat（js_parse_float）與工具列欄位的解析（toolstrip_parse_float）：{len(js_cases)} 個輸入和 Node.js 一樣——"
                      "開頭的 ECMAScript 空白（含 U+00A0、U+FEFF、U+2028、U+3000；U+180E、U+001C、U+0085、U+200B 不算）、最長數字前綴、"
                      "只認 ASCII 數字、'Infinity' 大小寫要對、溢位成 Infinity；工具列版只多認一字不差的 Inf／inf／-Inf／-inf"
                      + (f"（不一致：{js_bad}）" if js_bad else ""))
    # num：呼叫端換掉數字的解析（頻譜視窗傳 DSV 的單一數字規則：SI 字首、不完整的數字是錯）。這裡用一個只多認 k 字首的替身，確認三個函式都改用它、
    # 空字串＝不改與錯誤的 identifier 不變（真正的規則在 signal_viewer 的 selftest 與 GUI 測試）
    def k_num(tok):
        t_ = str(tok).strip()
        return float(t_[:-1]) * 1e3 if t_.endswith("k") and len(t_) > 1 else _num(t_)

    def k_float(tok):
        try:
            return k_num(tok)
        except ValueError:
            return math.nan
    pk_ = lambda t_: pv(lambda s_: parse_reference_level(s_, num=k_float), t_)      # noqa: E731
    po_ = lambda t_: pv(lambda s_: parse_offset(s_, num=k_float), t_)               # noqa: E731
    pm_ = lambda t_: pv(lambda s_: parse_mask(s_, "LowerMask", num=k_num), t_)      # noqa: E731
    m2k = pm_("[0 -17; 2k -17]")
    num_res = (pk_("2k"), pk_("12abc"), pk_(""), pk_("Spectrum peak"), po_("0.5k"), po_("50abc"), po_("Inf"), pm_("[0 -17; 12abc -17]"), pm_("2k"))
    check(isinstance(m2k, np.ndarray) and m2k.tolist() == [[0.0, -17.0], [2000.0, -17.0]]
          and num_res == (("custom", 2000.0), ("error", _ID_SA + "invalidReferenceLevel"), None, ("spectrum-peak", None), 500.0,
                          ("error", _ID_SA + "invalidMaskFrequencyOffset"), ("error", _ID_SA + "invalidMaskFrequencyOffset"),
                          ("error", _ID_SA + "invalidLowerMask"), 2000.0),
          f"num（呼叫端的數字解析，頻譜視窗傳 DSV 的單一規則）：parse_mask／parse_reference_level／parse_offset 都改用它——2k、0.5k 照它換算，"
          f"12abc、50abc 照它是錯；空字串的參考位準照樣不改、頻譜峰值照樣認得、錯誤的 identifier 不變（{m2k if not isinstance(m2k, np.ndarray) else 'matrix ok'}、"
          f"{num_res}）")
    row = panel_row(t3.status)
    row_zh = panel_row(t3.status, "zh")
    tn = MaskTester(MaskConfig(EnabledMasks="none"))
    sn = tn.test(f, spec[0], [0, 500])
    ok_panel = (row[3] == "Passing" and row[4] == "Passing" and row[5] == "--" and row[6] == "" and row[0] == 100.0
                and row_zh[3] == "通過" and panel_row(None) == PANEL_EMPTY_ROW and panel_row(sn) == PANEL_EMPTY_ROW
                and sn == {"tested": False} and tn.status is None and tn.status_matlab() is None)
    check(not bad and ok and ok_panel, "模板文字解析（Inf／-Inf／NaN、矩陣、逗號／換行、1e3；形狀與語法錯 → 工具列訊息、頻率欄錯 → 屬性訊息）、"
                                      "參考位準／頻率偏移欄位、面板 7 欄（沒開「--」、none → 空列、沒測過 status None）" + (f"（不一致：{bad}）" if bad else ""))
    # 計數器語意：設定變更／reset／release 不清，clear 才清；none 凍結並回傳上一次的狀態
    t4 = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12))
    t4.test(f, spec[0], time=3.999)
    t4.config = MaskConfig(EnabledMasks="upper-and-lower", UpperMask=100, LowerMask=-200)
    t4.release()
    s4b = t4.test(f, spec[1], time=7.999)
    t4.reset()
    t4.config.EnabledMasks = "none"
    s4c = t4.test(f, spec[2], time=11.999)
    keep = (t4.passed, t4.total, t4.status_matlab())
    t4.clear()
    ok4 = (s4b["NumPassedTests"] == 1 and s4b["NumTotalTests"] == 2 and s4b["SuccessRate"] == 50.0
           and s4c["tested"] is False and s4c["NumTotalTests"] == 2 and s4c["SimulationTime"] == 7.999 and keep == (1, 2, t4.status_matlab() or keep[2])
           and t4.passed == 0 and t4.total == 0 and t4.status is None
           and keep[2] == {"IsCurrentlyPassing": True, "NumPassedTests": 1, "NumTotalTests": 2, "SuccessRate": 50.0, "FailingMasks": "",
                           "FailingChannels": [], "SimulationTime": 7.999})
    check(ok4, "計數器語意（實測）：換設定、release()、reset() 都不清計數；none 時不測、計數凍結、回傳上一次狀態（含 SimulationTime）；"
               "clear() 才歸零；status_matlab() 的 7 欄")
    # 取代上一筆（推測的規則、MATLAB 的公開 API 碰不到）：失敗→通過時 passed 1/1
    t5 = MaskTester(MaskConfig(EnabledMasks="upper", UpperMask=-12))
    t5.test(f, spec[0])
    r5 = t5.test(f, spec[0] - 100.0, replace_last=True)
    check(r5["NumPassedTests"] == 1 and r5["NumTotalTests"] == 1 and r5["IsCurrentlyPassing"],
          f"replace_last（未定）：失敗後重測成通過 → {r5['NumPassedTests']}/{r5['NumTotalTests']}（不另加一次）")
    # 效能：1e6 個 bin、2 通道、矩陣上模板＋純量下模板、spectrum-peak（雜訊底 −75±5 dB 低於 −40 dBr＋峰值 −20 的限值 −60）
    n = 1_000_000
    fb = np.arange(n) * 1e-3
    Sb = np.vstack([-75 + 5 * np.sin(fb * 7.0), -73 + 5 * np.cos(fb * 3.0)])
    Sb[0, 123456] = -20.0
    big = MaskTester(MaskConfig(EnabledMasks="upper-and-lower", UpperMask=[[0, -40], [100, -40], [100, 0.5], [200, 0.5], [200, -40], [1000, -40]],
                                LowerMask=-90, ReferenceLevel="spectrum-peak", SelectedChannel=1))
    t0 = _time.time()
    rb = big.test(fb, Sb)
    dt = _time.time() - t0
    check(rb["IsCurrentlyPassing"] and rb["reference"] == -20.0 and dt < 2.0, f"效能：1e6 bin × 2 通道的模板測試 {dt:.3f}s（峰值參考 −20 dB、通過）")


def _selftest_nfft_points(check, ref_dir: str, C: Dict[str, Any]) -> None:
    """NFFT＝max(1024, WindowLength) 的全部實測資料點：tests/matlab_ref/scope/ 的 distortion、obw_chpower、acpr 擷取（各自的模組
    在用；這裡只讀顯示頻率格的 bin 數與首末頻率）加上本模板的 captures.json。不寫死哪幾次是獨立的：用 run_order.json（擷取順序、
    哪一次 run）找出每次擷取在同一個 scope 物件上的「上一次擷取」，逐筆分類——
    新（display.fresh）→ 格必須＝nfft_auto(L) 的格；不新但格＝自己設定的格 → 上一次擷取顯示的格和上一次設定的格都不同才算「獨立」，
    否則只是「一致」；格≠自己設定 → 必須＝上一次擷取顯示的格（「沿用」，不算資料點）；沒有顯示資料 → 略過。
    分類結果和模組說明的數字（新 48、獨立 8、一致 5、沿用 3、無顯示 1）逐項比。"""
    import json
    import os
    import dsv_spectrum as SP
    base = os.path.join(ref_dir, "scope")
    files = {"distortion": "scope_distortion.json", "obw_chpower": "scope_obw_captures.json", "acpr": "acpr_scope_ref.json"}
    order_fn = os.path.join(base, "spectral_mask", "run_order.json")
    missing = [p for p in [os.path.join(base, k, v) for k, v in files.items()] + [order_fn] if not os.path.isfile(p)]
    if missing:                                  # 參考檔缺了就是 FAIL，不悄悄略過（第六輪審查）
        check(False, f"NFFT 資料點核對缺參考檔：{missing}")
        return
    with open(order_fn, encoding="utf-8") as fh:
        order = json.load(fh)["captures"]
    bad: List[str] = []
    rows: Dict[str, Tuple[int, bool, float, Dict[str, Any]]] = {}     # 名稱 → (L, 雙邊, fs, display)
    acpr_links: List[Tuple[str, int, Optional[str]]] = []
    for key, fn in files.items():
        with open(os.path.join(base, key, fn), encoding="utf-8") as fh:
            D = json.load(fh)
        for c in D["captures"]:
            sc = c["config"] if key == "distortion" else c["scope"]
            fs = D["fs"] if key == "acpr" else c["signal"]["fs"]
            rows[c["name"]] = (int(sc["window_length"]), bool(sc["two_sided"]), float(fs), c["display"])
            if key == "acpr":
                acpr_links.append((c["name"], int(c["run_index"]), c["display"].get("previous_capture_in_run")))

    def own_grid(name):
        L, two, fs, _ = rows[name]
        g = SP.freq_grid(nfft_auto(L), fs, "centered" if two else "onesided")
        return (int(g.size), float(g[0]), float(g[-1]))

    def shown_grid(name):
        dp = rows[name][3]
        if dp.get("nbins") is None:
            return None
        return (int(dp["nbins"]), float(dp.get("f_first_Hz", dp.get("f_first"))), float(dp.get("f_last_Hz", dp.get("f_last"))))

    names = [c["name"] for c in order]
    idx = {c["name"]: k for k, c in enumerate(order)}
    if len(order) != 88 or len(set(names)) != 88 or [c["index"] for c in order] != list(range(1, 89)):
        bad.append("run_order.json 不是 1..88 各一次")
    prev: Dict[str, Optional[str]] = {}
    for k, c in enumerate(order):
        prev[c["name"]] = order[k - 1]["name"] if k and order[k - 1]["run"] == c["run"] else None
    for name, ri, pv in acpr_links:          # acpr 擷取自帶的順序和 run_order.json 要一致
        if name not in idx or order[idx[name]]["index"] != ri or prev.get(name) != pv:
            bad.append(f"{name}：run_index {ri}／previous {pv} 和 run_order.json 不一致")
    missing = sorted(set(rows) - set(names))
    if missing:
        bad.append(f"run_order.json 缺 {missing}")
    cls: Dict[str, Dict[str, List[str]]] = {k: {} for k in ("fresh", "independent", "consistent")}
    reused: List[str] = []
    no_display: List[str] = []
    for name in names:
        if name not in rows:
            continue
        L, two, fs, dp = rows[name]
        shown, mine = shown_grid(name), own_grid(name)
        p = prev[name]
        if shown is None:
            no_display.append(name)
        elif dp.get("fresh") is True:
            cls["fresh"].setdefault(str(L), []).append(name)
            if shown != mine:
                bad.append(f"{name}（新）：顯示 {shown} vs NFFT {nfft_auto(L)} 的 {mine}")
        elif shown == mine:
            dep = p is not None and p in rows and (shown_grid(p) == mine or own_grid(p) == mine)
            cls["consistent" if dep else "independent"].setdefault(str(L), []).append(name)
        else:
            reused.append(name)
            if p is None or p not in rows or shown_grid(p) != shown:
                bad.append(f"{name}：格 {shown} 既不是自己的 {mine}，也不是上一次擷取 {p} 顯示的")
    count = {k: {L: len(v) for L, v in sorted(d.items(), key=lambda t: int(t[0]))} for k, d in cls.items()}
    mask_L: Dict[str, int] = {}
    for cap in C["captures"]:
        L = int(cap["window_length"])
        mask_L[str(L)] = mask_L.get(str(L), 0) + 1
        if nfft_auto(L) != cap["nfft"]:
            bad.append(f"{cap['name']}：nfft {cap['nfft']} vs {nfft_auto(L)}")
    want = {"fresh": {"1000": 1, "2048": 28, "8192": 19},
            "independent": {"1000": 1, "1024": 2, "1999": 1, "2000": 1, "2048": 1, "4096": 1, "8192": 1},
            "consistent": {"1024": 1, "2048": 3, "8192": 1}}
    want_names = {"independent/1024": ["acpr_cplx_welch1024_psd_default_none", "dist_h_noiseless_1s_N6"],
                  "consistent/1024": ["acpr_cplx_welch1024_psd_three_pairs_none"]}
    got_names = {"independent/1024": sorted(cls["independent"].get("1024", [])), "consistent/1024": sorted(cls["consistent"].get("1024", []))}
    ok = (not bad and count == want and got_names == want_names and mask_L == {"1000": 21, "4000": 2}
          and sorted(reused) == ["dist_h_lowf_1s_N6", "dist_h_offbin_1s_N6", "dist_toi_bin_1s"]
          and no_display == ["obw_real_2s_psd_span1250_2000_P99"])
    allL = sorted({int(L) for d in count.values() for L in d} | {int(L) for L in mask_L})
    n_f, n_i, n_c = (sum(count[k].values()) for k in ("fresh", "independent", "consistent"))
    check(ok, f"NFFT＝max(1024, WindowLength) 的實測資料點：{len(allL)} 種 WindowLength {allL} 都對上——顯示是新的：distortion／obw／acpr "
              f"{n_f} 次（L→次數 {count['fresh']}）＋本模板 {sum(mask_L.values())} 次 {mask_L}；顯示落後但格是自己設定的、"
              f"上一次擷取（run_order.json）的格不同的獨立 {n_i} 次 {count['independent']}，上一次的格相同、只是一致的 {n_c} 次 "
              f"{count['consistent']}（L 1024：獨立 {got_names['independent/1024']}、一致 {got_names['consistent/1024']}）；"
              f"格＝上一次擷取顯示的格（沿用、不算）{len(reused)} 次 {sorted(reused)}；沒有顯示 {len(no_display)} 次；"
              f"acpr 的 run_index／previous_capture_in_run 和 run_order.json 一致"
              + (f"（不一致：{bad[:4]}）" if bad else "") + ("" if ok else f"（得到 {count}、{got_names}、沿用 {reused}、無顯示 {no_display}、mask {mask_L}）"))


def _ceil_2sig(v: float) -> float:
    """往上取到兩位有效數字（TOL＝2δ 的取法；用十進位字串建值，和程式裡寫的常數位元相同）。"""
    e = math.floor(math.log10(v))
    scale = float(f"1e{e - 1}")
    return float(f"{math.ceil(v / scale)}e{e - 1}")


def _selftest_fft_budget(check, fft_dir: str, C: Dict[str, Any], W: Optional[Dict[str, Any]], TOL: Dict[int, float],
                         stored: Dict[str, np.ndarray], spectra_by_capture: Dict[str, Tuple[np.ndarray, List[np.ndarray]]],
                         worst: Dict[int, float]) -> None:
    """FFT 捨入＋視窗預算（第六、七輪審查）：tests/matlab_ref/spectral_mask/fft_rounding_ref.json——10 張不同的顯示頻譜各自的精確模型值
    （mpmath 40 位，exact_periodogram.py；數學真值，不是 MATLAB 量的）用兩組視窗雙精度值各算一次（MATLAB hann(L,'periodic') 的 hann_periodic_{L}.txt
    ＝分析器與 MATLAB fft() 用的；dsv_spectrum.design_window 的＝DSV 用的），每個實作對**自己視窗**的精確值量最大誤差。
    釘死（位元相同、平台無關）：MATLAB 視窗檔（sha256、hann_periodic_ref.json 的 sum／前 4 個值／對稱）、分析器顯示值與 MATLAB fft() 在各自最差 bin
    對精確值的差、視窗差 Δ_win 在最差 bin 的兩個精確值（差到 2 ulp 內）；JSON 的 δ_scope／δ_fft／Δ_win／δ_dsv（採樣）／B＝δ_scope＋Δ_win＋δ_dsv／
    TOL＝2B 往上取兩位有效數字必須互相一致且等於程式裡的 TOL，採樣的 |DSV−scope| ≤ B（三角不等式）。
    本機（印出來、要求 ≤ TOL）：DSV 在所有釘住的 bin 對 DSV 視窗精確值的差、DSV−scope 的最大差（擷取迴圈量的）；本機視窗對 MATLAB 視窗的差
    （個數、最大差、ulp）與它是否和參考的 DSV 視窗位元相同（sha256；numpy 的 cos 可能因平台差 1 ulp），最大差 ≤ WIN_TOL＝2e-15（同一個公式的兩組
    雙精度值的差，量到 6.1e-16，3 倍餘裕）。"""
    import hashlib
    import json
    import os
    import dsv_spectrum as SP
    WIN_TOL = 2e-15
    fr_json = os.path.join(fft_dir, "fft_rounding_ref.json")
    hr_json = os.path.join(fft_dir, "hann_periodic_ref.json")
    missing = [p for p in (fr_json, hr_json) if not os.path.isfile(p)]
    if missing:
        check(False, f"沒有 {missing}（FFT 捨入＋視窗預算的參考檔）")
        return
    with open(fr_json, encoding="utf-8") as fh:
        FR = json.load(fh)
    with open(hr_json, encoding="utf-8") as fh:
        HR = json.load(fh)
    if not all(k in FR for k in ("summary", "windows", "spectra")) or "diff" not in FR["windows"]:
        check(False, f"{fr_json} 不是第七輪的格式（缺 summary／windows）")
        return
    bad: List[str] = []
    # (1) 視窗：MATLAB 檔釘死；本機 DSV 視窗對它的差印出來
    win_txt: List[str] = []
    hann_rows = {int(r["L"]): r for r in HR["windows"]}
    for L in (1000, 4000):
        wd = FR["windows"]["diff"].get(str(L))
        row = hann_rows.get(L)
        if wd is None or row is None:
            bad.append(f"視窗 {L}：JSON 沒有這個長度")
            continue
        fn = os.path.join(fft_dir, row["file"])
        if not os.path.isfile(fn):
            bad.append(f"沒有 {fn}（MATLAB hann({L},'periodic') 的檔）")
            continue
        with open(fn, "rb") as fh:
            raw = fh.read()
        wm = np.loadtxt(fn)
        w_dsv = SP.design_window("hann", L)
        sha_m = hashlib.sha256(raw).hexdigest()
        sha_d = hashlib.sha256("\n".join(f"{v:.17g}" for v in w_dsv).encode()).hexdigest()
        same_ref = sha_d == wd["sha256_dsvwin_17g"]
        if not (wm.shape == w_dsv.shape == (L,) and sha_m == wd["sha256_mwin_file"] and float(row["sum"]) == float(wd["matlab_sum_reported"])
                and np.array_equal(wm[:4], np.asarray(row["first_values"], dtype=float)) and bool(row["symmetric_w2_to_end"])
                and np.array_equal(wm[1:], wm[1:][::-1]) and wd["symmetric_2_to_end_mwin"] is True and int(wd["n_values"]) == L
                and HR["matlab_version"].startswith("25.1")):
            bad.append(f"視窗 {L}：MATLAB 檔和 hann_periodic_ref.json／fft_rounding_ref.json 不一致")
        diff = np.abs(wm - w_dsv)
        n_diff = int((wm != w_dsv).sum())
        mx = float(diff.max())
        ulp = float(np.max(diff / np.spacing(np.maximum(np.abs(wm), np.abs(w_dsv)).clip(min=np.finfo(float).tiny))))
        if same_ref and not (n_diff == int(wd["n_differ"]) and mx == float(wd["max_abs_diff"]) and ulp == float(wd["max_ulp_diff"])):
            bad.append(f"視窗 {L}：本機和參考的 DSV 視窗位元相同，但差的統計 {n_diff}／{mx!r}／{ulp!r} vs JSON {wd['n_differ']}／{wd['max_abs_diff']!r}／{wd['max_ulp_diff']!r}")
        if mx > WIN_TOL:
            bad.append(f"視窗 {L}：本機 DSV 視窗對 MATLAB 的最大差 {mx:.3g} > {WIN_TOL}")
        win_txt.append(f"L {L}：{n_diff}/{L} 個值不同、最大差 {mx:.3g}（{ulp:.0f} ulp；JSON {wd['n_differ']}／{float(wd['max_abs_diff']):.3g}／"
                       f"{float(wd['max_ulp_diff']):.0f}）、本機視窗{'＝' if same_ref else '≠'}參考的 DSV 視窗、MATLAB sum() {row['sum']!r}")
    # (2) 每張頻譜：釘住的 bin、視窗效應、各實作的最差 bin
    fft_files = {c["scope_spectrum_file"]: c["fft_file"] for c in W["calls"]} if W else {}
    S_sum = FR["summary"]
    got: Dict[int, Dict[str, Any]] = {L: {"scope": 0.0, "matlab_fft": None, "window": 0.0, "dsv": {}} for L in (1000, 4000)}
    dsv_worst: Dict[int, float] = {}
    n_file = n_pin = n_win = 0
    top: Dict[Tuple[str, int], Tuple[float, str]] = {}
    for s in FR["spectra"]:
        L = int(s["window_length"])
        rel = s["file"]
        hits = [(cap, cc) for cap in C["captures"] for cc in cap["calls"] if cc["spectrum_identical_to"] == rel]
        if not hits or rel not in stored or L not in got:
            bad.append(f"{rel} 不在 captures.json")
            continue
        cap, cc = hits[0]
        D = spectra_by_capture[cap["name"]][1][int(cc["k"]) - 1]
        sc = stored[rel]
        if not (D.shape == sc.shape == (int(s["nbins"]), int(s["nch"])) and int(cc["k"]) == int(s["k"])
                and int(cap["window_length"]) == L and int(cap["spectral_averages"]) == int(s["averages"])):
            bad.append(f"{rel} 形狀／設定 {D.shape} vs ({s['nbins']}, {s['nch']})、第 {cc['k']} 次 vs {s['k']}")
            continue
        ex_m = {(int(p["bin"]), int(p["ch"])): float(p["exact_dBm_mwin"]) for p in s["pinned_bins"]}
        ex_d = {(int(p["bin"]), int(p["ch"])): float(p["exact_dBm_dsvwin"]) for p in s["pinned_bins"]}
        we = s["window_effect"]
        kw = (int(we["bin"]), int(we["ch"]))
        if kw not in ex_m:
            bad.append(f"{rel}：視窗效應的 bin {kw} 沒釘精確值")
        else:
            dd = abs(ex_m[kw] - ex_d[kw])
            if abs(dd - float(we["max_abs_diff_dB"])) > 2 * float(np.spacing(max(abs(ex_m[kw]), abs(ex_d[kw])))):
                bad.append(f"{rel}：視窗效應 {dd!r} vs JSON {we['max_abs_diff_dB']!r}（差 > 2 ulp）")
            n_win += 1
        got[L]["window"] = max(got[L]["window"], float(we["max_abs_diff_dB"]))
        base = os.path.basename(rel)
        for name, r in s["impl"].items():
            key = (int(r["bin"]), int(r["ch"]))
            dmax = float(r["max_abs_diff_dB"])
            own = r["reference_window"]
            ex = ex_m if own == "mwin" else ex_d
            if key not in ex or float(r["exact_dBm_at_bin"]) != ex[key]:
                bad.append(f"{rel} {name}：最差 bin {key} 沒釘精確值")
                continue
            lvl = f"{dmax:.3g}（{base} bin {r['bin']} 通道 {r['ch']}，比峰值低 {-float(r['level_rel_peak_dB']):.0f} dB）"
            if name in ("scope", "matlab_fft"):
                if own != "mwin":
                    bad.append(f"{rel} {name} 的參考視窗是 {own}")
                if name == "scope":
                    S = sc
                    got[L]["scope"] = max(got[L]["scope"], dmax)
                else:
                    fn = fft_files.get(base)
                    if fn is None or not os.path.isfile(os.path.join(fft_dir, fn)):
                        bad.append(f"{rel}：w4000_fft_ref.json 沒有對應的 fft 檔（或檔案不在）")
                        continue
                    S = np.loadtxt(os.path.join(fft_dir, fn))
                    S = S[:, None] if S.ndim == 1 else S
                    got[L]["matlab_fft"] = max(got[L]["matlab_fft"] or 0.0, dmax)
                n_file += 1
                v = float(S[key[0], key[1] - 1])
                if v != float(r["impl_dBm"]) or abs(v - ex[key]) != dmax:
                    bad.append(f"{rel} {name}：檔案 {v!r}、差 {abs(v - ex[key])!r} vs JSON {r['impl_dBm']!r}、{dmax!r}")
            else:
                if own != "dsvwin":
                    bad.append(f"{rel} {name} 的參考視窗是 {own}")
                got[L]["dsv"][name] = max(got[L]["dsv"].get(name, 0.0), dmax)
            if dmax >= top.get((name, L), (-1.0, ""))[0]:
                top[(name, L)] = (dmax, lvl)
        for (b, ch), e in ex_d.items():
            n_pin += 1
            dd = abs(float(D[b, ch - 1]) - e)
            dsv_worst[L] = max(dsv_worst.get(L, 0.0), dd)
            if dd > TOL[L]:
                bad.append(f"{rel} DSV bin {b} 通道 {ch} 對精確值差 {dd:.3g} > TOL {TOL[L]:.3g}")
    # (3) 總表一致：δ 各項＝各列最大、B＝δ_scope＋Δ_win＋δ_dsv、TOL＝2B 取兩位有效數字＝程式裡的常數、採樣的 |DSV−scope| ≤ B、本機 ≤ TOL
    summ: List[str] = []
    for L in (1000, 4000):
        sm_ = S_sum.get(str(L))
        g = got[L]
        if sm_ is None:
            bad.append(f"WL {L}：JSON 沒有 summary")
            continue
        d_dsv = max(g["dsv"].values(), default=math.nan)
        B = float(sm_["delta_scope_dB"]) + float(sm_["delta_window_dB"]) + float(sm_["delta_dsv_dB"])
        vs_scope = {k: float(v) for k, v in sm_["max_abs_diff_vs_scope_dB"].items()}
        samp = max(vs_scope.values(), default=math.nan)
        ok_L = (float(sm_["delta_scope_dB"]) == g["scope"] and (sm_["delta_matlab_fft_dB"] is None) == (g["matlab_fft"] is None)
                and (g["matlab_fft"] is None or float(sm_["delta_matlab_fft_dB"]) == g["matlab_fft"])
                and float(sm_["delta_window_dB"]) == g["window"] and float(sm_["delta_dsv_dB"]) == d_dsv
                and {k: float(v) for k, v in sm_["delta_dsv_by_impl_dB"].items()} == g["dsv"]
                and float(sm_["bound_dB"]) == B and float(sm_["tol_dB"]) == _ceil_2sig(2 * B) == TOL[L]
                and vs_scope and samp <= B and worst.get(L, math.inf) <= TOL[L] and dsv_worst.get(L, math.inf) <= TOL[L])
        if not ok_L:
            bad.append(f"WL {L}：summary {sm_} vs 各列 {g}、B {B!r}、2B 取兩位 {_ceil_2sig(2 * B)!r}、TOL {TOL[L]!r}、本機 DSV−scope {worst.get(L)!r}、"
                       f"本機對精確值 {dsv_worst.get(L)!r}")
        summ.append(f"WL {L}：δ_scope {float(sm_['delta_scope_dB']):.3g}＋Δ_win {float(sm_['delta_window_dB']):.3g}＋δ_dsv {float(sm_['delta_dsv_dB']):.3g}"
                    f"＝B {B:.3g} → TOL {TOL[L]!r}（採樣的 |DSV−scope| 最大 {samp:.3g}，TOL 是它的 {TOL[L] / samp:.1f} 倍；本機 DSV−scope "
                    f"{worst.get(L, 0):.3g}（TOL 的 1/{TOL[L] / max(worst.get(L, 0), 1e-300):.1f}）、本機在釘住的 bin 對精確值 {dsv_worst.get(L, 0):.3g}）")

    def tp(name, L):
        t = top.get((name, L))
        return t[1] if t else "—"

    def dw(L):
        sm_ = S_sum.get(str(L))
        return f"{float(sm_['delta_window_dB']):.3g}" if sm_ else "—"

    dsv_names = sorted({n for (n, _) in top if n.startswith("dsv_")})
    sampled = "、".join(f"{n[4:].replace('_', ' ')} {top.get((n, 1000), (math.nan,))[0]:.3g}／{top.get((n, 4000), (math.nan,))[0]:.3g}" for n in dsv_names)
    check(not bad, f"FFT 捨入＋視窗預算（TOL {TOL[1000]!r}／{TOL[4000]!r}＝2B 往上取兩位有效數字，B＝δ_scope＋Δ_win＋δ_dsv）：{len(FR['spectra'])} 張顯示頻譜的"
                   f"精確模型值（exact_periodogram.py，mpmath {FR['precision_digits']} 位；數學真值，不是 MATLAB 量的）用 MATLAB hann(L,'periodic') 與 DSV 兩組"
                   f"視窗雙精度值各算一次——視窗差（{'；'.join(win_txt)}）讓精確值最多移 Δ_win {dw(1000)}／{dw(4000)} dB；各實作對自己視窗精確值的最大誤差："
                   f"分析器顯示值 WL 1000 {tp('scope', 1000)}、WL 4000 {tp('scope', 4000)}；MATLAB fft() {tp('matlab_fft', 4000)}；採樣的 DSV（WL 1000／4000）"
                   f"{sampled}；{'；'.join(summ)}；MATLAB 端 {n_file} 筆最差 bin 的差和 JSON 位元相同、{n_win} 個視窗效應 bin 的兩個精確值差到 2 ulp 內；"
                   f"本機 DSV 在 {n_pin} 個釘住的 bin 對精確值的差 ≤ TOL" + (f"（不一致：{bad[:4]}{' …' if len(bad) > 4 else ''}）" if bad else ""))


def _selftest_scope(check, ref_dir: str) -> None:
    """分析器實測（tests/matlab_ref/scope/spectral_mask/captures.json）：
    (a) 從輸入訊號用 scope_spectra() 重建 88 張顯示頻譜，和存下的 10 張（88 張依 sha256 只有這 10 張不同）逐 bin 比；
    (b) 兩個 scope 物件（run 1 七組、run 2 十六組設定）各用一個 MaskTester 連跑，每次呼叫的 7 個狀態欄位、每組設定前後的狀態、
        reset 檢查，全部和分析器完全相同；參考位準與失敗 bin 數再和「從實測頻譜算出」的數字比。"""
    import json
    import os
    d = os.path.join(ref_dir, "scope", "spectral_mask")
    path = os.path.join(d, "captures.json")
    if not os.path.isdir(ref_dir):               # 整個 tests/matlab_ref 都沒有才略過；有目錄卻缺參考檔就是 FAIL（第六輪審查）
        check(True, "（沒有 tests/matlab_ref：略過分析器實測比對）")
        return
    if not os.path.isfile(path):
        check(False, f"沒有 {path}（分析器實測的參考檔）")
        return
    import dsv_spectrum as SP
    with open(path, encoding="utf-8") as fh:
        C = json.load(fh)
    fs = float(C["fs"])
    need = [os.path.join(d, "signals", fn) for info in C["signals"].values() for fn in info["files"]]
    need += [os.path.join(d, rel) for rel in list(C["stored_spectra"]) + list(C["stored_grids"])]
    missing = [p for p in need if not os.path.isfile(p)]
    if missing:                                  # 參考檔缺了就是 FAIL（不要漏出 OSError、也不要悄悄略過）
        check(False, f"captures.json 引用的 {len(missing)} 個檔案不在：{missing[:3]}")
        return
    sig: Dict[str, List[np.ndarray]] = {}
    for ds, info in C["signals"].items():
        arrs = []
        for fn in info["files"]:
            m = np.loadtxt(os.path.join(d, "signals", fn))
            arrs.append((m[:, 0] + 1j * m[:, 1])[:, None] if info["complex"] else m)
        sig[ds] = arrs
    stored: Dict[str, np.ndarray] = {}
    for rel in C["stored_spectra"]:
        S = np.loadtxt(os.path.join(d, rel))
        stored[rel] = S[:, None] if S.ndim == 1 else S
    grids = {rel: np.loadtxt(os.path.join(d, rel)) for rel in C["stored_grids"]}
    # TOL＝FFT 捨入＋視窗預算（第六、七輪審查；見模組說明與下面的「FFT 捨入＋視窗預算」檢查）：B＝δ_scope（分析器顯示值對 MATLAB 視窗精確值的
    # 最大誤差 5.68e-13／3.72e-12）＋Δ_win（DSV 與 MATLAB 兩組 Hann 雙精度值的差讓精確值移動的最大量 3.51e-13／4.13e-12）＋δ_dsv（採樣的 numpy
    # 2.4.6／1.26.4 對 DSV 視窗精確值的最大誤差 4.05e-13／3.89e-12）＝1.32e-12／1.17e-11；TOL＝2B 往上取兩位有效數字（對 B 2 倍餘裕；對量到的
    # DSV−scope 殘差 7.03e-13／6.71e-12 是 3.8／3.6 倍）。以前 7.1e-13／6.2e-12 是 numpy 2.4.6 量到的最大值取兩位有效數字（餘裕 10%／1%），
    # numpy 1.26.4 量到 6.39e-13／6.71e-12 就 FAIL；第六輪的 1.2e-12／1.1e-11＝2δ（δ＝對 DSV 視窗精確值的最大誤差 5.54e-13／5.31e-12）把視窗差
    # 算成了 FFT 捨入、對殘差也只有 1.7／1.6 倍。
    TOL = {1000: 2.7e-12, 4000: 2.4e-11}
    worst: Dict[int, float] = {}              # 本機 DSV−scope 最大差（numpy 2.4.6：7.03e-13／6.14e-12，1.26.4：6.39e-13／6.71e-12；
    #                                           A 的 WL 1000 最大在第 2 次呼叫＝8 段，不是 16 段）
    worst_call: Dict[Tuple[str, int, int], float] = {}     # (資料集, WL, 第幾次呼叫) → 最大差
    n_spec = n_spec_ok = 0
    grid_bad: List[str] = []
    spectra_by_capture: Dict[str, Tuple[np.ndarray, List[np.ndarray]]] = {}
    for cap in C["captures"]:
        L, N, two = cap["window_length"], cap["spectral_averages"], cap["two_sided"]
        foff = float(cap["scope_props_requested"].get("FrequencyOffset", 0))
        f, Ss = scope_spectra(sig[cap["dataset"]], fs, L, N, two, foffset=foff)
        assert all(S is not None for S in Ss)
        spectra_by_capture[cap["name"]] = (f, Ss)
        g = grids[cap["frequency_grid_file"]]
        if not (len(f) == cap["nbins"] and np.array_equal(f, g) and nfft_auto(L) == cap["nfft"]
                and np.array_equal(SP.freq_grid(cap["nfft"], fs, "centered" if two else "onesided") + foff, g)):
            grid_bad.append(cap["name"])
        for c, S in zip(cap["calls"], Ss):
            ref = stored[c["spectrum_identical_to"]]
            n_spec += 1
            r = float(np.max(np.abs(S - ref)))
            worst[L] = max(worst.get(L, 0.0), r)
            key = (cap["dataset"], L, int(c["k"]))
            worst_call[key] = max(worst_call.get(key, 0.0), r)
            n_spec_ok += r <= TOL[L]

    def per_call(ds, L):
        """「第 k 次呼叫＝k×段數 段 差值」的清單，最大的那次標出來（審查指出：A 的最大在第 2 次呼叫，不是 16 段）。"""
        seg = 4000 // L
        items = sorted((k, v) for (d_, l_, k), v in worst_call.items() if d_ == ds and l_ == L)
        kmax = max(items, key=lambda kv: kv[1])[0] if items else 0
        return "、".join(f"第 {k} 次＝{k * seg} 段 {v:.3g}{'（最大）' if k == kmax else ''}" for k, v in items)

    check(n_spec_ok == n_spec == 88 and not grid_bad,
          f"分析器頻譜模型（Hann periodic、NFFT＝max(1024, WL)、'power' dBm、running 平均＝λ＝(N−1)/(N+1) 的指數平均）：{n_spec_ok}/{n_spec} 張"
          f"實測顯示頻譜從輸入訊號重建，最大差 WL 1000：{worst.get(1000, 0):.3g} dB（≤ TOL {TOL[1000]!r}＝FFT 捨入＋視窗預算；numpy 2.4.6 量到 7.03e-13、"
          f"1.26.4 6.39e-13；分析報告 7.03e-13；資料集 A {per_call('A', 1000)}；資料集 B {per_call('B', 1000)}）、WL 4000（N＝1 單一週期圖）："
          f"{worst.get(4000, 0):.3g} dB（≤ {TOL[4000]!r}；numpy 2.4.6 量到 6.14e-12、1.26.4 6.71e-12；分析報告 6.14e-12；{per_call('A', 4000)}）；"
          f"4 種頻率格（單邊 513、4000 點 2001、雙邊 1024、含 FrequencyOffset 1000）位元相同"
          + (f"（頻率格不符：{grid_bad}）" if grid_bad else ""))
    # 已知差異（第五輪審查：量到的殘差要明寫）：WL 4000（N＝1 單一週期圖）的分析器顯示值連 MATLAB 自己 fft(w.*x) 算的週期圖都不是位元相同
    # （tests/matlab_ref/spectral_mask/w4000_fft_ref.m 實跑，w4000_fft_ref.json 記每次呼叫的最大差與位元相同 bin 數、w4000_fft_call{k}.txt 是
    # 那 4 張 %.17g 頻譜），所以 DSV 的殘差是 FFT 捨入（加上兩組 Hann 雙精度值的差）、不是模型誤差；TOL[4000]＝2.4e-11 是 FFT 捨入＋視窗預算（下一項）。
    # MATLAB 端的數字（fft() 對 scope 的最大差、位元相同 bin 數）逐次呼叫釘死（檔案算的，和平台無關）；DSV 端的數字（numpy pocketfft）印出來、≤ TOL。
    fft_dir = os.path.join(ref_dir, "spectral_mask")
    fft_json = os.path.join(fft_dir, "w4000_fft_ref.json")
    W: Optional[Dict[str, Any]] = None
    if os.path.isfile(fft_json):
        with open(fft_json, encoding="utf-8") as fh:
            W = json.load(fh)
        _, S4 = scope_spectra(sig["A"], fs, 4000, 1, False)
        rows4: List[str] = []
        bad4: List[str] = []
        worst_ml = worst_dsv_ml = 0.0
        pinned_ml = {1: ("4.36e-12", 1445), 2: ("5.77e-12", 1344), 3: ("1.75e-12", 1489), 4: ("3.88e-12", 1876)}   # MATLAB 端實測（R2025a）
        for c in W["calls"]:
            k = int(c["k"])
            if k not in pinned_ml or k > len(S4):
                bad4.append(f"呼叫 {k}：JSON 多出來的呼叫")
                continue
            D = S4[k - 1]
            p_ml, p_sc = os.path.join(fft_dir, c["fft_file"]), os.path.join(d, "spectra", c["scope_spectrum_file"])
            if not (os.path.isfile(p_ml) and os.path.isfile(p_sc)):     # 參考檔缺了就是 FAIL，不要漏出 OSError 也不要悄悄略過
                bad4.append(f"呼叫 {k}：沒有 {c['fft_file']}／{c['scope_spectrum_file']}")
                continue
            ml = np.loadtxt(p_ml)
            sc = np.loadtxt(p_sc)
            a, b, cc = float(np.max(np.abs(D - sc))), float(np.max(np.abs(ml - sc))), float(np.max(np.abs(D - ml)))
            n_ms, n_ds, n_dm = int((ml == sc).sum()), int((D == sc).sum()), int((D == ml).sum())
            worst_ml, worst_dsv_ml = max(worst_ml, b), max(worst_dsv_ml, cc)
            if not (b == float(c["max_abs_diff_dB"]) and n_ms == int(c["bit_identical_bins"]) == pinned_ml[k][1] and f"{b:.3g}" == pinned_ml[k][0]
                    and ml.shape == sc.shape == D.shape == (2001, 2) and int(c["numel"]) == 4002
                    and a == worst_call[("A", 4000, k)] and a <= TOL[4000] and cc <= TOL[4000]):
                bad4.append(f"呼叫 {k}：fft()−scope {b!r}（JSON {c['max_abs_diff_dB']!r}、釘 {pinned_ml[k][0]}）、位元相同 {n_ms}（JSON {c['bit_identical_bins']}、"
                            f"釘 {pinned_ml[k][1]}）、DSV−scope {a!r}（擷取迴圈 {worst_call.get(('A', 4000, k))!r}）、DSV−fft() {cc!r}")
            rows4.append(f"第 {k} 次：scope−fft() {b:.3g}（{n_ms}/4002 bin 位元相同）、DSV−scope {a:.4g}（{n_ds} 相同）、DSV−fft() {cc:.3g}（{n_dm} 相同）")
        ok4 = not bad4 and len(rows4) == 4 and W["matlab_version"].startswith("25.1") and len(W["calls"]) == 4 and W["nfft"] == 4000
        check(ok4, f"已知差異：WL 4000 的分析器顯示頻譜和 MATLAB 自己 fft(w.*x) 的週期圖也不是位元相同（w4000_fft_ref.m 實跑 {W['matlab_version']}；"
                   f"最大 {worst_ml:.4g} dB、4002 個 bin 最少只有 1344 個相同）→ DSV 重建殘差（最大 {worst.get(4000, 0)!r} dB）是 FFT 捨入（＋兩組 Hann "
                   f"雙精度值的差）不是模型誤差（DSV 對 fft() 最大 {worst_dsv_ml:.4g}）；TOL {TOL[4000]!r}＝FFT 捨入＋視窗預算（下一項）；MATLAB 端數字"
                   "逐次呼叫釘死且和 JSON 位元相同：" + "；".join(rows4) + (f"（不一致：{bad4}）" if bad4 else ""))
    else:
        check(False, f"沒有 {fft_json}（WL 4000 殘差拆解的參考檔）")
    _selftest_fft_budget(check, fft_dir, C, W, TOL, stored, spectra_by_capture, worst)
    _selftest_nfft_points(check, ref_dir, C)

    def mstat(st):
        """分析器 JSON 的狀態 → 可比較的 tuple（FailingChannels 用 MATLAB 形狀：純量／列向量／[]）。"""
        if st == [] or st is None:
            return None
        fc = st["FailingChannels"]
        fc = [int(v) for v in fc] if isinstance(fc, list) else int(fc)
        return (bool(st["IsCurrentlyPassing"]), int(st["NumPassedTests"]), int(st["NumTotalTests"]), float(st["SuccessRate"]),
                st["FailingMasks"], fc, float(st["SimulationTime"]))

    def mine(t):
        st = t.status_matlab()
        return None if st is None else (st["IsCurrentlyPassing"], st["NumPassedTests"], st["NumTotalTests"], float(st["SuccessRate"]),
                                        st["FailingMasks"], st["FailingChannels"], float(st["SimulationTime"]))

    n_calls = n_calls_ok = n_edge = n_edge_ok = 0
    n_tested = n_none = n_time_ok = 0
    n_margin = n_margin_ok = 0                 # 每通道 upper_max_excess_dB／lower_min_margin_dB（審查指出以前沒比）
    margin_worst: Dict[int, float] = {}
    bad: List[str] = []
    ref_worst = 0.0
    for sess in C["sessions"]:
        t = MaskTester()
        for name in sess["captures"]:
            cap = next(c for c in C["captures"] if c["name"] == name)
            L = int(cap["window_length"])
            f, Ss = spectra_by_capture[name]
            t.config = MaskConfig(**cap["mask_config"])
            t.release()
            n_edge += 1
            if mine(t) == mstat(cap["mask_status_before_calls"]):
                n_edge_ok += 1
            else:
                bad.append(f"{name} 設定前狀態 {mine(t)} vs {mstat(cap['mask_status_before_calls'])}")
            tm = None
            for c, S in zip(cap["calls"], Ss):
                tm = simulation_time(tm, c["n_samples"], fs)
                st = t.test(f, S.T, time=tm)
                n_calls += 1
                got, want = mine(t), mstat(c["mask_status"])
                e = []
                if got != want:
                    e.append(f"狀態 {got} vs 分析器 {want}")
                if tm == float(c["spectrum_simulation_time"]):      # getSpectrumData 的 SimulationTime（none 的 4 次呼叫也有）
                    n_time_ok += 1
                else:
                    e.append(f"頻譜時間 {tm!r} vs 分析器 {c['spectrum_simulation_time']!r}")
                fc = c["from_captured_spectrum"]
                if cap["mask_config"]["EnabledMasks"] == "none":
                    n_none += 1
                    if st["tested"]:
                        e.append("none 卻測了")
                else:
                    n_tested += 1
                    if not st["tested"]:
                        e.append("沒測")
                    else:
                        dr = abs(st["reference"] - fc["reference_dBm"])
                        ref_worst = max(ref_worst, dr)
                        if dr > 1e-14:           # 實測 7.1e-15＝27 dBm 的 2 ulp（峰值 bin 的重建差）；custom 參考是位元相同（審查：1e-12 太鬆）
                            e.append(f"參考位準 {st['reference']!r} vs 實測頻譜峰值 {fc['reference_dBm']!r}")
                        for m in fc["per_channel"]:
                            ch = m["ch"] - 1
                            if st["n_fail_upper"][ch] != m["n_upper_fail_bins"] or st["n_fail_lower"][ch] != m["n_lower_fail_bins"]:
                                e.append(f"ch{m['ch']} 失敗 bin 數 {st['n_fail_upper'][ch]}/{st['n_fail_lower'][ch]} vs {m['n_upper_fail_bins']}/{m['n_lower_fail_bins']}")
                            # 每通道 max(S−上限−ref)／min(S−下限−ref)：從重建頻譜算 vs 分析器實測頻譜算（analyze_mask.py），差 ≤ 該 WL 的頻譜殘差；
                            # 模板沒開／差值沒有一個有限 → 兩邊都要是 NaN（JSON 裡是 NaN 或 null）
                            for mk, sk in (("upper_max_excess_dB", "upper_excess_dB"), ("lower_min_margin_dB", "lower_margin_dB")):
                                want_m, got_m = m[mk], st[sk][ch]
                                n_margin += 1
                                if want_m is None or (isinstance(want_m, float) and math.isnan(want_m)):
                                    if math.isnan(got_m):
                                        n_margin_ok += 1
                                    else:
                                        e.append(f"ch{m['ch']} {mk} {got_m!r} vs 實測 NaN")
                                else:
                                    dm = abs(got_m - float(want_m))
                                    margin_worst[L] = max(margin_worst.get(L, 0.0), dm)
                                    if dm <= TOL[L]:
                                        n_margin_ok += 1
                                    else:
                                        e.append(f"ch{m['ch']} {mk} {got_m!r} vs 實測頻譜算的 {want_m!r}（差 {dm:.2g} > {TOL[L]}）")
                if e:
                    bad.append(f"{name} 呼叫 {c['k']}：" + "；".join(e))
                else:
                    n_calls_ok += 1
            n_edge += 1
            if mine(t) == mstat(cap["mask_status_final"]):
                n_edge_ok += 1
            else:
                bad.append(f"{name} 設定後狀態 {mine(t)} vs {mstat(cap['mask_status_final'])}")
        if sess["run"] == 2:
            rc = C["mask_status_reset_check"]
            before = mine(t)
            t.reset()
            n_edge += 1
            if before == mstat(rc["before_reset"]) == mstat(rc["after_reset"]) == mine(t):
                n_edge_ok += 1
            else:
                bad.append(f"reset 檢查 {before} / {mine(t)} vs {mstat(rc['before_reset'])} / {mstat(rc['after_reset'])}")
    check(n_calls_ok == n_calls == 88 and n_tested == 84 and n_none == 4 and n_time_ok == 88 and n_margin_ok == n_margin == 328,
          f"分析器實測狀態：{n_calls_ok}/{n_calls} 次呼叫（{n_tested} 次有開模板＋{n_none} 次 none）的 IsCurrentlyPassing、NumPassedTests、NumTotalTests、"
          f"SuccessRate、FailingMasks、FailingChannels（純量／列向量／[]）、SimulationTime 全部相同（2 個 scope 物件、23 組設定連跑，計數跨 release／"
          f"設定變更累加）；simulation_time() 和 getSpectrumData 的 SimulationTime {n_time_ok}/{n_calls} 次相同（含 none 的 4 次）；"
          f"spectrum-peak 參考位準和實測頻譜峰值最大差 {ref_worst:.2g} dB（≤ 1e-14＝27 dBm 的 2.8 ulp）；每通道失敗 bin 數和實測頻譜算的相同；"
          f"每通道 max(S−上限−ref)／min(S−下限−ref) {n_margin_ok}/{n_margin} 個（84 次 × 通道 × 上下）和實測頻譜算的差 ≤ 頻譜殘差"
          f"（WL 1000 最大 {margin_worst.get(1000, 0):.2g}、WL 4000 最大 {margin_worst.get(4000, 0):.2g} dB；沒開／全 NaN 的 NaN 位置相同）"
          + (f"（不一致：{bad[:4]}{' …' if len(bad) > 4 else ''}）" if bad else ""))
    check(n_edge_ok == n_edge == 47,
          f"分析器實測計數器：{n_edge_ok}/{n_edge} 個邊界狀態相同——23 組設定前（含第一次測試前 []→None、none 後凍結）、23 組設定後、"
          f"reset(sa) 前後 14/56 不變" + (f"（不一致：{[b for b in bad if '狀態' in b and '呼叫' not in b][:3]}）" if n_edge_ok != n_edge else ""))
