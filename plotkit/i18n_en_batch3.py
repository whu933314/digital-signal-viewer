# -*- coding: utf-8 -*-
"""English catalog part: batch3 — the third batch of MATLAB tools in the spectrum window: CHANNEL MEASUREMENTS
(occupied bandwidth and ACPR, MATLAB R2025a spectrumAnalyzer). Toolstrip labels, descriptions and field errors are
MATLAB's own English strings (as shown in the MATLAB R2025a Spectrum Analyzer interface) where MATLAB has one.
Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    # CHANNEL MEASUREMENTS contextual tab: CHANNEL / CHANNEL MEASUREMENTS / FREQUENCY OPTIONS / ADJACENT CHANNELS
    "通道量測": "Channel Measurements",
    "通道選擇器": "Channel Selector",
    "選擇量測通道：清單是畫出來的每一條軌跡（先一般、再 Max-Hold、再 Min-Hold）；通道量測與失真量選到的那一條（峰值搜尋照舊列出全部訊號）":
        "Select the measurement channel: the list holds every plotted trace (normal traces first, then Max-Hold, then Min-Hold); "
        "channel measurements and distortion measure the selected one (Peak Finder still lists every signal)",
    "顯示通道量測（MATLAB Spectrum Analyzer 的 Channel Measurements）：佔用頻寬＝通道功率、佔用頻寬、頻率誤差；\nACPR＝相鄰通道對主通道的功率比（dBc）。量的是「通道選擇器」選的那條軌跡，下方面板列出數字、圖上用色塊標出頻帶":
        "Show channel measurements (MATLAB Spectrum Analyzer Channel Measurements): Occupied BW = channel power, occupied bandwidth "
        "and frequency error;\nACPR = power of the adjacent channels relative to the main channel (dBc). The trace selected in "
        "Channel Selector is measured; the panel below lists the numbers and the plot shades the bands",
    "選擇佔用頻寬或相鄰通道功率比量測": "Select occupied bandwidth or adjacent channel power ratio measurements",
    "佔用頻寬": "Occupied BW",
    "ACPR": "ACPR",
    "佔用頻寬 (%)": "Occupied BW (%)",
    "佔用頻寬百分比：頻帶內總功率的這麼多百分比所佔的頻寬（0～100，不含兩端；預設 99）；{enter}或按箭頭":
        "Percent occupied BW: the bandwidth that holds this percentage of the total power in the band (0 to 100, exclusive; "
        "default 99); {enter} or use the arrows",
    "頻率選項": "Frequency Options",
    "頻率跨度": "Frequency Span",
    "頻率跨度模式：跨度和中心頻率，或開始和停止頻率": "Frequency span mode: Span and Center Frequency, or Start and Stop Frequencies",
    "跨度和中心頻率": "Span and Center Frequency",
    "開始和停止頻率": "Start and Stop Frequencies",
    "跨度": "Span",
    "中心頻率": "Center Frequency",
    "開始頻率": "Start Frequency",
    "停止頻率": "Stop Frequency",
    "量測頻帶的頻率跨度：主通道＝中心頻率 ± 跨度/2；{enter}":
        "Frequency span of the measured band: main channel = center frequency ± span/2; {enter}",
    "量測頻帶的中心頻率（頻率誤差從它量）；{enter}": "Center frequency of the measured band (the frequency error is measured from it); {enter}",
    "量測頻帶的開始頻率；{enter}": "Start frequency of the measured band; {enter}",
    "量測頻帶的停止頻率（中心＝(開始 + 停止)/2）；{enter}": "Stop frequency of the measured band (center = (start + stop)/2); {enter}",
    "相鄰通道": "Adjacent Channels",
    "對組數": "Num Pairs",
    "指定相鄰通道對組的數量（1～64）；{enter}或按箭頭": "Specify the number of adjacent channel pairs (1 to 64); {enter} or use the arrows",
    "偏移量": "Offsets",
    "相對於主通道中心頻率指定相鄰通道頻率：例如 [2000 3500]，個數＝對組數（負的偏移量＝上下對調）；{enter}":
        "Specify the frequency of the adjacent channel relative to the center frequency of the main channel: e.g. [2000 3500], "
        "one per pair (a negative offset swaps lower and upper); {enter}",
    "相鄰頻寬": "Adjacent BW",
    "指定相鄰通道的跨度（每個相鄰通道的頻寬）；{enter}": "Specify the span of the adjacent channel (the bandwidth of each adjacent channel); {enter}",
    "濾波器形狀": "Filter Shape",
    "選擇要同時套用到主通道和相鄰通道的通道濾波器：無、RRC（根升餘弦）、高斯":
        "Select the channel filter to apply to both main and adjacent channels: None, RRC (root raised cosine), Gaussian",
    "RRC": "RRC",
    "滾降因子": "Roll-off Factor",
    "頻寬時間乘積": "BT Product",
    "指定以主通道頻寬（跨度）為準的 3 dB 頻寬符號時間乘積（BT，0～1）：功率權重 exp(−ln2·((f−fc)/(BT·跨度))²)":
        "Specify the 3-dB bandwidth-symbol time product with respect to the main channel bandwidth (span) (BT, 0 to 1): "
        "power weight exp(−ln2·((f−fc)/(BT·span))²)",
    "指定以主通道頻寬（跨度）為準的滾降因子（β，0～1）：RRC 的功率響應＝升餘弦，符號率＝跨度":
        "Specify the roll-off factor with respect to the main channel bandwidth (span) (β, 0 to 1): the RRC power response is a "
        "raised cosine with symbol rate = span",
    # the measurement panels below the plot (MATLAB's Occupied Bandwidth and ACPR panels)
    "通道功率 ({u})": "Channel Power ({u})",
    "佔用頻寬 ({u})": "Occupied Bandwidth ({u})",
    "頻率誤差 ({u})": "Frequency Error ({u})",
    "偏移量 ({u})": "Offset ({u})",
    "相對功率 ({u})": "Rel. Power ({u})",
    "下限（{rel}）": "Lower ({rel})",
    "上限（{rel}）": "Upper ({rel})",
    # status line and notes
    "通道量測（{name}）：頻帶 {a}～{b}，通道功率 {cp} {u}": "Channel measurements ({name}): band {a} to {b}, channel power {cp} {u}",
    "通道量測：{msg}": "Channel measurements: {msg}",
    "通道量測：{n} 個相鄰通道不在頻譜範圍內，那幾格留白（NaN；MATLAB 一樣）":
        "Channel measurements: {n} adjacent channel(s) outside the spectrum, left blank (NaN; as in MATLAB)",
    "通道量測：主通道 {a}～{b} 不在頻譜範圍內，每一對的比值都量不到（NaN，面板留白）":
        "Channel measurements: the main channel {a} to {b} is outside the spectrum, so none of the ratios can be measured (NaN, blank in the panel)",
    "通道量測：主通道量到的功率是 0，比值算不出來（相鄰通道也是 0 的格子 NaN 留白，其他寫 Infinity）":
        "Channel measurements: the main channel power is 0, so the ratios cannot be computed (NaN and blank where the adjacent channel "
        "is 0 as well, Infinity elsewhere)",
    "通道量測：{n} 個相鄰通道量到的功率是 0（濾波器權重或頻譜是 0），那幾格寫 -Infinity":
        "Channel measurements: {n} adjacent channel(s) measured 0 power (zero filter weight or zero spectrum), shown as -Infinity",
    "通道量測：通道選擇器選的「{name}」這次沒有畫出來，面板留白（選擇保留，畫出來就再量）":
        "Channel measurements: \"{name}\" selected in Channel Selector is not plotted this time; the panel is blank (the selection is "
        "kept and measured again once it is plotted)",
    "這次量不出來（內部檢查沒過，詳細內容寫在記錄檔）": "could not be measured this time (an internal check failed; details are in the log file)",
    "{name}：{msg}": "{name}: {msg}",
    "通道量測：要畫一般、最大值保持或最小值保持軌跡其中一條": "Channel measurements: plot the normal, max-hold or min-hold trace",
    "通道量測：頻帶 {a}～{b} 不在頻譜範圍內，量不到（NaN，面板留白；MATLAB 一樣）":
        "Channel measurements: the band {a} to {b} is outside the spectrum, nothing to measure (NaN, blank in the panel; as in MATLAB)",
    # toolstrip field errors (MATLAB Spectrum Analyzer error messages; the adjacent BW one is DSV's own, MATLAB reuses the center frequency text)
    "以 0 到 100（不包含兩者）之間的有限實數純量形式輸入頻寬佔用百分比。":
        "Enter percent occupied bandwidth as a finite real scalar between 0 and 100 exclusive.",
    "以有限正實數純量形式輸入跨度。": "Enter span as a finite positive real scalar.",
    "以有限實數純量形式輸入中心頻率。": "Enter center frequency as a finite real scalar.",
    "以有限實數純量形式輸入開始頻率。": "Enter start frequency as a finite real scalar.",
    "以有限實數純量形式輸入停止頻率。": "Enter stop frequency as a finite real scalar.",
    "以 1 到 64 之間的有限正實數純量形式輸入 ACPR 偏移量的數目。":
        "Enter number of ACPR offsets as a finite positive real scalar between 1 and 64.",
    "以長度等於指定的 ACPR 偏移量數目的有限正實數向量形式輸入 ACPR 偏移量。":
        "Enter ACPR offsets as a finite positive real vector with length equal to the specified number of ACPR Offsets.",
    "以有限正實數純量形式輸入相鄰頻寬。": "Enter adjacent channel bandwidth as a finite positive real scalar.",
    "以 0 和 1 之間的有限非負實數純量形式輸入濾波器係數。": "Enter filter coefficient as a finite nonnegative real scalar between 0 and 1.",
    # MEASUREMENTS › DISTORTION (section in the Measurements tab, the panels below the plot)
    "失真": "Distortion",
    "失真量測（MATLAB Spectrum Analyzer 的 Distortion）：諧波＝THD、SNR、SINAD、SFDR 與每個諧波的頻率與功率；\n互調＝兩個音、兩個三階互調積與 TOI。量「通道選擇器」選的那條軌跡，下方面板列出數字、圖上用 ▼ 標出":
        "Distortion measurements (MATLAB Spectrum Analyzer Distortion): Harmonic = THD, SNR, SINAD, SFDR and the frequency and power "
        "of each harmonic;\nIntermodulation = the two tones, the two third-order products and TOI. The trace selected in Channel "
        "Selector is measured; the panel below lists the numbers and the plot marks them with ▼",
    "失真類型：諧波（THD、SNR、SINAD、SFDR）或互調（TOI）": "Distortion type: Harmonic (THD, SNR, SINAD, SFDR) or Intermodulation (TOI)",
    "諧波": "Harmonic",
    "互調": "Intermodulation",
    "諧波數量": "Num Harmonics",
    "要列出幾個諧波（含基頻，2～99，預設 6；超過 Nyquist 的不列）；{enter}":
        "Number of harmonics to list (including the fundamental, 2 to 99, default 6; those above Nyquist are not listed); {enter}",
    "標示諧波": "Label Harmonics",
    "標示頻率": "Label Frequencies",
    "在 ▼ 上面寫 H1、H2…": "Write H1, H2… above the ▼",
    "在 ▼ 上面寫 F1、F2、2F1 - F2、2F2 - F1": "Write F1, F2, 2F1 - F2, 2F2 - F1 above the ▼",
    "諧波失真": "Harmonic Distortion",
    "互調失真": "Intermodulation Distortion",
    "頻率 ({u})": "Frequency ({u})",
    "振幅": "Magnitude",
    "功率": "Power",
    "功率密度": "Power Density",
    "RMS": "RMS",
    "失真：{msg}": "Distortion: {msg}",
    "失真：要畫一般、最大值保持或最小值保持軌跡其中一條": "Distortion: plot the normal, max-hold or min-hold trace",
    "失真：通道選擇器選的「{name}」這次沒有畫出來，面板留白（選擇保留，畫出來就再量）":
        "Distortion: \"{name}\" selected in Channel Selector is not plotted this time; the panel is blank (the selection is kept and "
        "measured again once it is plotted)",
    "失真：第 {k} 個以後的諧波超過 Nyquist，不列（MATLAB 一樣）":
        "Distortion: harmonics from number {k} on are above Nyquist and are not listed (as in MATLAB)",
    "失真：諧波與雜訊的裙邊佔了頻寬的 {p:.0f}%（> 70%），MATLAB 文件說這時 SNR／SINAD 不可靠":
        "Distortion: the tone skirts cover {p:.0f}% of the bandwidth (> 70%); MATLAB's documentation says SNR / SINAD are not reliable then",
    "以 2 到 99 之間的有限正實數純量形式輸入諧波的數目。": "Enter number of harmonics as a finite positive real scalar between 2 and 99.",
    # SPECTRAL MASK contextual tab and panel (MATLAB R2025a spectrumAnalyzer strings where MATLAB has them)
    "頻譜遮罩": "Spectral Mask",
    "上遮罩": "Upper Mask",
    "下遮罩": "Lower Mask",
    "顯示上遮罩：頻譜有任何一點高於「上限＋參考位準」就失敗（MATLAB 的 Show upper mask）":
        "Show upper mask: the test fails when any point of the spectrum is above upper limit + reference level (MATLAB Show upper mask)",
    "顯示下遮罩：頻譜有任何一點低於「下限＋參考位準」就失敗（MATLAB 的 Show lower mask）":
        "Show lower mask: the test fails when any point of the spectrum is below lower limit + reference level (MATLAB Show lower mask)",
    "上限": "Upper Limits",
    "下限": "Lower Limits",
    "指定{which}的限值：一個數字（整個頻譜同一個位準），或 [頻率 位準; 頻率 位準; …]：兩欄（頻率、位準）、至少兩列；頻率不能遞減（同一頻率寫兩次＝垂直階梯），中間線性內插，範圍外不測；最後一個頻率寫 +Inf＝延伸到右端，第一個頻率寫 -Inf 時那一段不測（MATLAB 實測；色塊仍畫到左端），要從左端開始測請寫有限的頻率（例如 0 或 -fs/2）。位準是相對參考位準的 dB；{enter}":
        "Specify limits for the {which}: one number (the same level over the whole spectrum) or [frequency level; frequency level; …]: "
        "two columns (frequency, level), at least two rows; frequencies must not decrease (a repeated frequency makes a vertical step), "
        "linear in between, not tested outside; a last frequency of +Inf extends to the right end, while a first frequency of -Inf leaves "
        "that first segment untested (measured in MATLAB; the patch is still drawn to the left edge), so to test from the left edge write "
        "a finite frequency such as 0 or -fs/2. Levels are dB relative to the reference level; {enter}",
    "參考位準 (dBr)": "Reference Level (dBr)",
    "頻譜峰值": "Spectrum peak",
    "指定參考位準：數字（dBr，遮罩的位準加上它；Inf／-Inf 也可以，清空＝不改），或下拉選「頻譜峰值」（用「通道」選的那一條這次頻譜的最大值）；{enter}":
        "Specify reference level: a number (dBr, added to the mask levels; Inf / -Inf also work, clearing the field changes nothing) or "
        "\"Spectrum peak\" from the list (the maximum of this spectrum of the channel selected in Channel); {enter}",
    "指定頻譜峰值參考位準用哪一條：編號照這個視窗的訊號順序 1、2、…（I/Q 複數時是那一對；這次算不出頻譜的訊號也佔一個號碼；參考位準是「頻譜峰值」時才能選）":
        "Specify channel for spectrum peak reference level: numbered 1, 2, … in the order of this window's signals (the pair when I/Q "
        "complex is on; a signal without a spectrum this time keeps its number; enabled when the reference level is \"Spectrum peak\")",
    "頻率偏移": "Frequency Offset",
    "指定遮罩的頻率偏移：加到遮罩矩陣的頻率上（數字遮罩不受影響）；{enter}":
        "Specify mask frequency offset: added to the frequencies of a mask matrix (a single-number mask is not affected); {enter}",
    "測試": "Test",
    "清除計數": "Clear Counts",
    "通過／總測試數歸零，再用目前的頻譜測一次（沒得測時只歸零；DSV 才有；MATLAB 要新建 scope 物件才會歸零）。\n每次重新計算頻譜算一次測試；改遮罩設定只重新判定這一次，不多算":
        "Reset the passed / total test counts and test the current spectrum once (only resets when nothing can be tested; DSV only; "
        "MATLAB resets only with a new scope object).\n"
        "Every spectrum recomputation is one test; changing the mask settings only re-evaluates that test without counting another",
    "成功率 (%)": "Success Rate (%)",
    "通過的測試數": "Passed Tests",
    "測試總數": "Total Tests",
    "目前狀態": "Current Status",
    "上遮罩狀態": "Upper Mask Status",
    "下遮罩狀態": "Lower Mask Status",
    "失敗的通道": "Failing Channel(s)",
    "通過": "Passing",
    "失敗": "Failing",
    "頻譜遮罩：{msg}": "Spectral mask: {msg}",
    "頻譜遮罩：計數已清除，用目前的頻譜重新測了一次": "Spectral mask: counts cleared, the current spectrum was tested again",
    "頻譜遮罩：計數已清除": "Spectral mask: counts cleared",
    "頻譜遮罩：要畫一般、最大值保持或最小值保持軌跡其中一條": "Spectral mask: plot the normal, max-hold or min-hold trace",
    "頻譜遮罩：選的通道 {n} 這次沒有頻譜，參考位準暫用通道 {m} 的頻譜峰值（選擇不變）":
        "Spectral mask: the selected channel {n} has no spectrum this time; the reference level uses the spectrum peak of channel {m} "
        "for now (the selection is kept)",
    "頻譜遮罩：選的通道 {n} 不在這個視窗（共 {k} 個通道），參考位準暫用通道 {m} 的頻譜峰值（選擇不變）":
        "Spectral mask: the selected channel {n} is not in this window ({k} in total); the reference level uses the spectrum peak of "
        "channel {m} for now (the selection is kept)",
    # 頻譜圖的通道（第二批的分頁；第三批審查時改成和遮罩的通道同一個規則：選擇不會被自動改掉）
    "頻譜圖：選的「{sel}」這次沒有頻譜，暫時畫「{name}」（選擇不變）":
        "Spectrogram: the selected \"{sel}\" has no spectrum this time; showing \"{name}\" for now (the selection is kept)",
    "以實數數值純量或有至少兩列的兩欄矩陣形式輸入上遮罩。":
        "Enter upper mask as a real, numeric scalar or two-column matrix with at least two rows.",
    "以實數數值純量或有至少兩列的兩欄矩陣形式輸入下遮罩。":
        "Enter lower mask as a real, numeric scalar or two-column matrix with at least two rows.",
    "以「頻譜峰值」或有限實數純量形式輸入參考位準。": "Enter reference level as 'Spectrum peak' or as a finite real scalar.",
    "以有限實數純量形式輸入頻譜遮罩頻率偏移。": "Enter spectral mask frequency offset as a finite real scalar.",
    # 數字欄位的單一規則收 SI 字首之後（第五輪）：10k 的衰減、1G 的 FFT 長度這種值不再讓重新計算丟例外或吃光記憶體；第六輪起是欄位的錯誤狀態
    # （打的字留著、不再改回預設值），頻譜圖 2^26 格的上限 FFT 長度 Auto 也一樣
    "衰減 {v} dB 太大，算不出視窗": "Attenuation {v} dB is too large to compute the window",
    "FFT 長度最多 2^24（16777216）點": "FFT length can be at most 2^24 (16777216) points",
    # 第七輪：頻率偏移再大 matplotlib 算不出頻率軸的刻度（以前每次重新計算都丟例外、壞值存進設定）
    "頻率偏移 {v} 太大，畫不出頻率軸（最多 ±1e+300）": "Frequency offset {v} is too large to draw the frequency axis (at most ±1e+300)",
    "頻譜圖要 {k} 段 × FFT 長度 {n} 格，太大，沒有畫：把 FFT 長度改小或改回 Auto":
        "The spectrogram would need {k} segments × FFT length {n} cells, which is too large, so it is not drawn: "
        "reduce the FFT length or set it to Auto",
    "頻譜圖要 {k} 段 × FFT 長度 {n} 格，太大，沒有畫：把重疊改小、縮小主圖的範圍或關掉重新指派":
        "The spectrogram would need {k} segments × FFT length {n} cells, which is too large, so it is not drawn: "
        "reduce the overlap, narrow the main plot range or turn off Reassign",
    # 第二批與峰值欄位不合格（第六輪，使用者 2026-10-26 決定和第三批的欄位同一個錯誤狀態）：MATLAB R2025a 的錯誤訊息原文
    # （Spectrum Analyzer 工具列的欄位、設定對話框的色彩範圍、Peak Finder 欄位）；
    # 時間用 symbol 的兩句是 DSV 自己的（MATLAB 只有秒）
    "以有限實數純量形式輸入頻率偏移。": "Enter frequency offset as a finite real scalar.",
    "以「Auto」或有限正實數純量形式輸入 RBW。": "Enter RBW as 'Auto' or as a finite positive real scalar.",
    "輸入的視窗長度應為大於 2 的有限正實數純量。": "Enter window length as a finite positive real scalar greater than 2.",
    "輸入的 FFT 長度應為大於或等於 {0} 的有限正實數純量。": "Enter FFT length as a finite positive real scalar greater than or equal to {0}.",
    "以大於或等於 45 的有限實數純量形式輸入旁波瓣衰減。": "Enter sidelobe attenuation as a finite real scalar greater than or equal to 45.",
    "以小於 100 的有限非負實數純量形式輸入重疊百分比。": "Enter overlap percentage as a finite nonnegative real scalar less than 100.",
    "以「Auto」或有限正實數純量形式輸入時間解析度。": "Enter time resolution 'Auto' or as a finite positive real scalar.",
    "輸入的時間解析度應為大於或等於 {0} 秒的有限正實數純量。":
        "Enter time resolution as a finite positive real scalar larger than or equal to {0} seconds.",
    "輸入的時間解析度應為大於或等於 {0} symbol 的有限正實數純量。":
        "Enter time resolution as a finite positive real scalar larger than or equal to {0} symbols.",
    "輸入的時間跨度應為「Auto」或有限實數正純量形式。": "Enter time span as 'Auto' or as a finite real positive scalar.",
    "輸入的時間跨度應為大於 {0} 秒的有限正實數純量。": "Enter time span as a finite real positive scalar larger than {0} seconds.",
    "輸入的時間跨度應為大於 {0} symbol 的有限正實數純量。": "Enter time span as a finite real positive scalar larger than {0} symbols.",
    "以有限正實數純量形式輸入參考負載。": "Enter reference load as a finite positive real scalar.",
    "以有限正實數純量形式輸入滿刻度。": "Enter full scale as a finite positive real scalar.",
    "輸入 [cmin cmax]，其中 cmin 和 cmax 是有限純量。": "Enter [cmin cmax], where cmin and cmax are finite scalars.",
    "以 1 到 99 之間的有限正實數純量形式輸入峰值數目。": "Enter number of peaks as a finite positive real scalar between 1 and 99.",
    "以非負實數純量形式輸入門檻值。": "Enter threshold as nonnegative real scalar.",
    "以實數純量形式輸入最小高度。": "Enter minimum height as a real scalar.",
    "以正整數純量形式輸入最小峰值距離。": "Enter minimum peak distance as a positive scalar integer.",
    # 第八輪（使用者 2026-10-26 決定）：滿刻度與 Min Distance 也有 DSV 的上限（極端值是欄位的錯誤狀態）
    "滿刻度 {v} 超出範圍，要在 1e-150 到 1e+150 之間": "Full scale {v} is out of range; it must be between 1e-150 and 1e+150",
    "最小峰值距離 {v} 太大：有限的值最多 2^53 − 1（9007199254740991），要只留最高的峰請寫 Inf":
        "Minimum peak distance {v} is too large: a finite value can be at most 2^53 − 1 (9007199254740991); enter Inf to keep only the highest peak",
    # 第八輪：灰掉或藏起來的欄位還是錯誤狀態時（主題的灰框蓋過紅框），說明列寫「欄位名稱：訊息（怎麼做才改得到）」
    "{name}：{msg}（{how}才改得到）": "{name}: {msg} ({how} to edit it)",
    "{feature}的{field}": "{feature} {field}",
    "{a}、{b}": "{a} and {b}",
    "切到「{mode}」模式": "switch to {mode} mode",
    "視窗選「{a}」或「{b}」": "select the {a} or {b} window",
    "打開「{view}」檢視": "turn on the {view} view",
    "打開「{a}」或「{b}」檢視": "turn on the {a} or {b} view",
    "按「{b}」": "click {b}",
    "類型切到「{t}」": "set Type to {t}",
    "濾波器形狀選「{a}」或「{b}」": "set Filter Shape to {a} or {b}",
    "頻率跨度切到「{m}」": "set Frequency Span to {m}",
    "頻譜類型換成 RMS 以外的類型": "set the spectrum type to something other than RMS",
    "頻譜單位換成線性以外的單位": "set the spectrum unit to something other than Linear",
    "衰減": "Attenuation",
    "時間解析度": "Time Resolution",
    "時間跨度": "Time Span",
    "參考負載": "Reference Load",
    "參考位準": "Reference Level",
}
