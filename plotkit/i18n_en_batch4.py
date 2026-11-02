# -*- coding: utf-8 -*-
"""English catalog part: batch 4 of the 2026-10 MATLAB tools. Keys are the Traditional Chinese source strings, byte for byte.

Preprocess section: the 「前處理」 toolstrip tab modelled on MATLAB Signal Analyzer's PREPROCESS tab (FILTER / CLEAN / CONVERT gallery,
Function Parameters panel). English text follows the messages MATLAB R2025a's Signal Analyzer shows for preprocessing
wherever MATLAB has the string; the rest are DSV's own messages.

Eye diagram section (第四批 T4): the 「眼圖…」 analysis window modelled on MATLAB Communications Toolbox eyediagram(x, n, period, offset).
Axes titles and labels are MATLAB eyediagram's own English ('Eye Diagram ', 'Eye Diagram for In-Phase Signal', 'Eye Diagram for Quadrature
Signal', 'Time', 'Amplitude'); argument names follow the eyediagram documentation (n = number of samples per trace, period, offset);
the input-check messages come from dsv_eye (MATLAB's comm:eyediagram:* text). The rest are DSV's own messages.

Error rate section (第四批 T5): the 「錯誤率比對…」 window modelled on MATLAB Communications Toolbox biterr / symerr / comm.ErrorRate.
Output and property names follow the MATLAB documentation (Number of bit errors, Bit error rate, Number of symbol errors, Symbol error
rate, ReceiveDelay = Receive delay, ComputationDelay = Computation delay, Samples = Samples to consider with 'Entire frame' / 'Custom',
CustomSamples = Selected samples from frame); the field and data errors shown in the window are MATLAB's own English messages from
dsv_errrate (MATLAB:expectedNonnegative, MATLAB:expectedVector, comm:system:sampsElemExceedInWidth, MATLAB:biterr:expectedInteger …),
so they are not in this catalog. The rest are DSV's own messages.
"""
CATALOG = {
    # ---------------------------------------------------------------- 前處理（PREPROCESS）
    # 分頁、圖庫區段與項目（MATLAB 前處理分頁）
    "前處理": "Preprocess",
    "濾波器": "Filter",
    "清理": "Clean",
    "轉換": "Convert",
    "低通": "Lowpass",
    "高通": "Highpass",
    "帶通": "Bandpass",
    "帶阻": "Bandstop",
    "平滑": "Smooth",
    "去趨勢": "Detrend",
    "重取樣": "Resample",
    "包絡": "Envelope",
    "套用低通濾波器": "Apply a lowpass filter",
    "套用高通濾波器": "Apply a highpass filter",
    "套用帶通濾波器": "Apply a bandpass filter",
    "套用帶阻濾波器": "Apply a bandstop filter",
    "平滑含雜訊的資料": "Smooth noisy data",
    "去除常數、線性或分段線性趨勢": "Remove constant, linear, or piecewise linear trends",
    "均勻時更改取樣率，不均勻時進行內插": "Change sample rate when uniform or interpolate when nonuniform",
    "將資料轉換為上包絡或下包絡": "Convert data to upper or lower envelope",
    "開啟「函式參數」面板；按「套用」對「已繪訊號」選取的每條訊號各新增一條結果（衍生訊號，原訊號保留、來源改了自動重算）":
        "Opens the Function Parameters panel; Apply adds one result per signal selected in Plotted Signals "
        "(a derived signal: the original is kept, and the result is recomputed when its source changes)",
    # 函式參數面板（MATLAB 前處理面板與各函式顯示的文字）
    "函式參數": "Function Parameters",
    "低通參數": "Lowpass Parameters",
    "高通參數": "Highpass Parameters",
    "帶通參數": "Bandpass Parameters",
    "帶阻參數": "Bandstop Parameters",
    "平滑參數": "Smooth Parameters",
    "去趨勢參數": "Detrend Parameters",
    "重取樣參數": "Resample Parameters",
    "包絡參數": "Envelope Parameters",
    "還原預設值": "Restore Defaults",
    "前處理訊號說明": "Preprocess Signal Help",
    "對訊號表中所選訊號套用低通濾波": "Apply lowpass filtering to signals selected in signals table",
    "對訊號表中所選訊號套用高通濾波": "Apply highpass filtering to signals selected in signals table",
    "對訊號表中所選訊號套用帶通濾波": "Apply bandpass filtering to signals selected in signals table",
    "對訊號表中所選訊號套用帶阻濾波": "Apply bandstop filtering to signals selected in signals table",
    "對表中的所選訊號套用平滑處理": "Apply smoothing to signals selected in table",
    "對訊號表中的所選訊號套用去趨勢處理": "Apply detrend to signals selected in signals table",
    "對訊號表中的所選訊號套用重取樣": "Apply resample to signals selected in signals table",
    "對訊號表中的所選訊號套用包絡": "Apply envelope to signals selected in signals table",
    "還原預設低通濾波器參數": "Restore default lowpass filter parameters",
    "還原預設高通濾波器參數": "Restore default highpass filter parameters",
    "還原預設帶通濾波器參數": "Restore default bandpass filter parameters",
    "還原預設帶阻濾波器參數": "Restore default bandstop filter parameters",
    "還原預設平滑參數": "Restore default smooth parameters",
    "還原預設去趨勢參數": "Restore default detrend parameters",
    "還原預設重取樣參數": "Restore default resample parameters",
    "還原預設包絡參數": "Restore default envelope parameters",
    # 濾波器（MATLAB 介面顯示的訊息）
    "濾波器設定": "Filter Specifications",
    "頻率單位": "Frequency Units",
    "通帶頻率單位": "Passband frequency units",
    "通帶頻率": "Passband Frequency",
    "下通帶頻率": "Lower Passband Frequency",
    "上通帶頻率": "Upper Passband Frequency",
    "陡度": "Steepness",
    "過渡帶陡度": "Transition band steepness",
    "下頻帶陡度": "Lower Band Steepness",
    "上頻帶陡度": "Upper Band Steepness",
    "下過渡帶陡度": "Lower transition band steepness",
    "上過渡帶陡度": "Upper transition band steepness",
    "為下過渡帶和上過渡帶指定同一個陡度值，或為下過渡帶和上過渡帶各指定一個值":
        "Specify one steepness value for lower and upper transition bands, or two values, one for each band",
    "阻帶衰減(dB)": "Stopband Attenuation(dB)",            # label and tooltip (the research recorded the tooltip as the label)
    "通帶頻率必須為正純量": "Passband frequency must be a positive scalar",
    "下通帶頻率必須小於上通帶頻率": "Lower passband frequency must be smaller than upper passband frequency",
    "陡度必須為 [0.5,1) 範圍內的數值純量": "Steepness must be a numeric scalar in the [0.5,1) range",
    "阻帶衰減必須為大於或等於 10 dB 的正數值純量": "Stopband attenuation must be a numeric positive scalar greater than or equal to 10 dB",
    "由於指定的通帶頻率超過 Nyquist 極限，因此使用了全通濾波器。":
        "An allpass filter was used because the specified passband frequency exceeds the Nyquist limit.",
    "由於指定的通帶頻率超過 Nyquist 極限，因此使用了全阻濾波器。":
        "An allstop filter was used because the specified passband frequency exceeds the Nyquist limit.",
    "由於指定的上下通帶頻率超過 Nyquist 極限，因此使用了全通濾波器。":
        "An allpass filter was used because the specified passband frequencies exceed the Nyquist limit.",
    "由於指定的上下通帶頻率超過 Nyquist 極限，因此使用了全阻濾波器。":
        "An allstop filter was used because the specified passband frequencies exceed the Nyquist limit.",
    # 單位（MATLAB Signal Analyzer 工具列的 cycles/* 與時間單位）
    "週期/年": "cycles/year",
    "週期/天": "cycles/day",
    "週期/小時": "cycles/hour",
    "週期/分鐘": "cycles/minute",
    "分鐘": "minutes",
    "小時": "hours",
    "天": "days",
    "年": "years",
    "樣本": "samples",
    # 平滑（MATLAB 介面顯示的訊息）
    "方法": "Method",
    "平滑方法": "Smoothing Method",
    "選擇平滑方法": "Select smoothing method",
    "移動平均": "Moving mean",
    "移動中位數": "Moving median",
    "高斯": "Gaussian",
    "線性迴歸": "Linear regression",
    "二次迴歸": "Quadratic regression",
    "穩健線性迴歸": "Robust linear regression",
    "穩健二次迴歸": "Robust quadratic regression",
    "次數": "Degree",
    "選擇「Auto」作為 Savitzky-Golay 次數，或輸入值": "Select Savitzky-Golay degree as 'Auto' or type a value",
    "視窗類型": "Window Type",
    "選擇如何控制視窗長度": "Select how to control window length",
    "持續時間": "Duration",
    "平滑因子": "Smoothing Factor",
    "持續時間單位": "Duration Units",
    "視窗持續時間": "Window Duration",
    "選擇「Auto」作為視窗持續時間，或輸入值": "Select window duration as 'Auto' or type a value",
    "視窗平滑因子": "Window smoothing factor",
    "以時間為單位的視窗持續時間長度必須為正數值純量": "Window duration length in time units must be a positive numeric scalar",
    "平滑因子必須為介於 0 和 1 之間的數值純量": "Smoothing factor must be a numeric scalar between 0 and 1",
    "次數必須設為正整數。": "Degree must be set to a numeric positive integer.",
    "次數太大。次數必須小於任一訊號視窗中的最大點數。": "Degree is too large. Degree must be less than the largest number of points in any signal window.",
    "次數已調整為較小的值。指定的值大於自動計算的視窗長度。":
        "Degree has been adjusted to a smaller value. The specified value was larger than the automatically computed window length.",
    # 去趨勢（MATLAB 介面顯示的訊息）
    "去趨勢方法": "Detrend Method",
    "選擇去趨勢方法": "Select detrend method",
    "常數": "Constant",
    "分段線性": "Piecewise Linear",
    "斷點單位": "Breakpoint Units",
    "分段斷點單位。對於具有時間值的訊號，會使用最接近指定輸入時間的樣本索引作為分段斷點值":
        "Piecewise breakpoint units. For signals with time values, a sample index nearest to the specified input time is used for the piecewise breakpoint value",
    "分段斷點": "Piecewise Breakpoints",
    "為相鄰分段線性段之間的斷點指定逗號分隔值": "Specify comma-separated values for breakpoints between adjacent piecewise linear segments",
    "以時間為單位的分段斷點必須為數值": "Piecewise breakpoints in time units must be a numeric value",
    # 重取樣（MATLAB 介面顯示的訊息）
    "重取樣設定": "Resample Settings",
    "重取樣方法": "Resampling Method",
    "取樣因子": "Sample Factor",
    "選擇「Auto」作為目標取樣率，或輸入值": "Select desired sample rate as 'Auto' or type a value",
    "指定更改所選訊號取樣率所使用的因子": "Specify the factor by which the sample rate of selected signal is changed",
    "值必須為正純量": "Value must be a positive scalar",
    "目標取樣率與目前取樣率的比率超過限制。請指定較低的目標取樣率。":
        "The ratio of desired sample rate to current sample rate exceeds limits. Specify a lower desired sample rate.",
    "目標取樣率導致重取樣後的訊號長度為 1。請指定較高的目標取樣率。":
        "The desired sample rate results in a resampled signal of length one. Specify a higher desired sample rate.",
    "自動計算取樣率時，不會前處理均勻取樣的訊號。": "Uniformly sampled signals are not preprocessed when sample rate is auto computed.",
    # 包絡（MATLAB 介面顯示的訊息）
    "包絡設定": "Envelope Settings",
    "選擇輸出包絡": "Select output envelope",
    "上包絡": "Upper",
    "下包絡": "Lower",
    "選擇包絡方法": "Select envelope method",
    "希爾伯特": "Hilbert",
    "峰值（包絡方法）": "Peak",            # MATLAB envelope method "Peak"; the plain key 「峰值」 is the measurement tab's PEAKS section ("Peaks", batch1)
    "長度單位": "Length Units",
    "間隔單位": "Separation Units",
    "視窗長度單位。如果是時間單位，會使用有效的取樣率將指定的輸入時間轉換為樣本":
        "Window length units. For time units, the specified input time will be converted to samples using the effective sample rate",
    "局部最大值間隔單位。如果是時間單位，會使用有效的取樣率將指定的輸入時間轉換為樣本":
        "Local maxima separation units. For time units, the specified input time will be converted to samples using the effective sample rate",
    "濾波器階數": "Filter Order",
    "指定 FIR 濾波器階數以計算解析包絡": "Specify FIR filter order to compute the analytic envelope",
    "指定滑動視窗長度": "Specify sliding window length",
    "最大值間隔": "Maxima Separation",
    "指定局部最大值間隔": "Specify local maxima separation",
    "濾波器階數必須為正整數": "Filter order must be a positive integer",
    "以樣本為單位的視窗長度必須為正整數": "Window length in samples must be a positive integer",
    "以時間為單位的視窗長度必須為正數值純量": "Window length in time units must be a positive numeric scalar",
    "以樣本為單位的最大值間隔必須為正整數": "Maxima separation in samples must be a positive integer",
    "以時間為單位的最大值間隔必須為正數值純量": "Maxima separation in time units must be a positive numeric scalar",
    # 文字欄位的 placeholder（MATLAB "Enter Value" / "Specify comma-separated values"）
    "輸入值": "Enter Value",
    "指定逗號分隔值": "Specify comma-separated values",
    # 設定檔讀回來的參數不合法（DSV 自己的訊息；欄位訊息本身是 MATLAB 的）
    "參數不合法：{msgs}": "Invalid parameters: {msgs}",      # the separator 「；」 is already in i18n_en_dsv1
    "前處理參數不合法（設定檔可能被改過）；請移除這條結果後重新套用":
        "Invalid preprocessing parameters (the settings file may have been edited); remove this result and apply again",
    "前處理參數不合法（{detail}）；請移除這條結果後重新套用":
        "Invalid preprocessing parameters ({detail}); remove this result and apply again",
    # 套用後的對話框（MATLAB 介面顯示的訊息）
    "無法前處理具有缺失值或非有限值的訊號。請使用「填補缺失值」來填補缺失值。":
        "Unable to preprocess signals with missing or nonfinite values. Use Fill Missing to fill missing values.",
    "由於出現了以下錯誤，所選訊號未被處理：": "Selected signals have not been processed due to the following errors:",
    "由於出現了以下錯誤，部分所選訊號未被處理：": "Some selected signals have not been processed due to the following errors:",
    "所選訊號已處理，但出現以下警告：": "Selected signals have been processed with the following warnings:",
    "部分所選訊號已處理，但出現以下警告：": "Some selected signals have been processed with the following warnings:",
    # DSV 自己的訊息（MATLAB 沒有對應：衍生訊號、選取、狀態列）
    "參數有誤：請修正紅字的欄位": "Invalid parameters: correct the fields marked in red",
    "請先在「已繪訊號」選取要前處理的訊號": "Select the signals to preprocess in Plotted Signals first",
    "套用到：沒有選取——請先在「已繪訊號」選取訊號": "Apply to: nothing selected - select signals in Plotted Signals first",
    "套用到 {n} 條選取的訊號：{names}": "Apply to the {n} selected signal(s): {names}",
    "{func}：參數有誤，沒有套用": "{func}: invalid parameters, not applied",
    "{func}：在「函式參數」面板設定參數後按「套用」（套用到「已繪訊號」選取的訊號，各新增一條結果）":
        "{func}: set the parameters in the Function Parameters panel and press Apply (applies to the signals selected in Plotted Signals, one new result each)",
    "{func}：已新增 {n} 條衍生訊號（{names}；原訊號保留、來源改了自動重算；Ctrl+Z 可復原）":
        "{func}: added {n} derived signal(s) ({names}; originals kept, recomputed when the source changes; Ctrl+Z to undo)",
    "{func}：已還原預設參數": "{func}: default parameters restored",
    "{func}：沒有新增訊號": "{func}: no signal added",
    "{func}：請先在「已繪訊號」選取要前處理的訊號（MATLAB 也是套用到訊號表裡選取的訊號）":
        "{func}: select the signals to preprocess in Plotted Signals first (MATLAB also applies to the signals selected in the signal table)",
    "{func}：選取的訊號已經有相同參數的結果，沒有新增": "{func}: the selected signals already have a result with the same parameters; nothing added",
    "（{n} 條已經有相同參數的結果，略過）": " ({n} already had a result with the same parameters and were skipped)",
    "前處理：{func}": "Preprocess: {func}",
    "前處理：{func}，新增 {n} 條衍生訊號": "Preprocess: {func}, added {n} derived signal(s)",
    "前處理：開啟「{func}」參數": "Preprocess: open {func} parameters",
    "前處理結果算不出來（{n} 條）：{name}：{msg}": "Preprocessing result could not be computed ({n}): {name}: {msg}",
    "{name}：{func}，來源 {src}；參數：{params}": "{name}: {func} of {src}; parameters: {params}",
    "；算不出來：{msg}": "; could not be computed: {msg}",
    "（來源訊號不見了）": "(source signal missing)",
    # 來源沒有資料（來源自己是算不出來的結果、它的來源不見了、空的訊號）：DSV 自己的訊息（MATLAB 覆寫訊號、沒有連鎖）
    "來源訊號沒有資料，無法前處理": "The source signal has no data; nothing to preprocess",
    "來源 {name} 沒有資料：{msg}": "Source {name} has no data: {msg}",
    "來源 {name} 沒有資料（它的來源訊號不見了）": "Source {name} has no data (its own source signal is missing)",
    "來源 {name} 沒有資料（空的訊號），無法前處理": "Source {name} has no data (empty signal); nothing to preprocess",

    # ---------------------------------------------------------------- 眼圖（第四批 T4：MATLAB eyediagram）
    # 分析分頁、清單與 panel 右鍵、快速鍵動作
    "眼圖": "Eye Diagram",
    "眼圖…": "Eye Diagram…",
    "眼圖（P{p}）…": "Eye Diagram (P{p})…",
    "眼圖（選取的 {n} 條）…": "Eye Diagram ({n} selected)…",
    "／": "/",                                       # 標題裡分隔 panel（「清單選取（P1／P2）」）
    "開眼圖視窗（MATLAB eyediagram）：訊號每 n 個樣本切成一條軌跡疊在一起，看眼睛張開多少；\nn 預設 2 × 每符號樣本數（一條軌跡兩個符號），週期、取樣偏移照 MATLAB。只畫圖、不量眼高眼寬（MATLAB R2025a 也沒有可呼叫的量測）。\n畫清單選取的訊號：1 條＝一張，2 條＝當成 I/Q 畫同相、正交兩張；沒有選取就畫「目前 panel」（點 panel 選定，圖上有框；\n有 I/Q 配對就畫那一對）。panel 右鍵也有「眼圖（P1）」；視窗標題寫出畫的是哪個 panel、哪幾條":
        "Open the eye diagram window (MATLAB eyediagram): the signal is cut into traces of n samples that are overlaid to show how open the eye is;\n"
        "n defaults to 2 × samples per symbol (two symbols per trace); period and offset work as in MATLAB. Plot only, no eye height / width "
        "measurement (MATLAB R2025a has no callable eye measurement either).\nPlots the signals selected in the list: 1 signal = one plot, 2 signals = "
        "treated as I/Q with in-phase and quadrature plots; with no selection it plots the current panel (click a panel to make it current; it gets a frame;\n"
        "an I/Q pair in that panel is plotted as the pair). A panel's right-click menu has Eye Diagram (P1) too; the window title shows which panel and "
        "signals are plotted",
    "開啟眼圖視窗（{where}）": "Open eye diagram window ({where})",
    "已開啟眼圖視窗：{where}，I＝{i}、Q＝{q}": "Eye diagram window opened: {where}, I = {i}, Q = {q}",
    "已開啟眼圖視窗：{where}，{name}": "Eye diagram window opened: {where}, {name}",
    "眼圖：P{p} 沒有顯示中的訊號": "Eye diagram: P{p} has no visible signals",
    "眼圖：清單選了 {n} 條訊號——{msg}MATLAB eyediagram 一次畫 1 欄（一張眼圖）或 2 欄（同相、正交兩張）：在清單只選 1 條或 2 條，或取消選取改畫目前 panel":
        "Eye diagram: {n} signals are selected in the list — {msg} MATLAB eyediagram plots 1 column (one eye diagram) or 2 columns (in-phase and "
        "quadrature): select only 1 or 2 signals in the list, or clear the selection to plot the current panel",
    "眼圖：P{p} 有 {n} 條訊號、找不到 I/Q 配對（P{p} 有：{names}）——{msg}MATLAB eyediagram 一次畫 1 欄（一張眼圖）或 2 欄（同相、正交兩張）：在清單選 1 條或 2 條再按「眼圖…」":
        "Eye diagram: P{p} has {n} signals and no I/Q pair (P{p} has: {names}) — {msg} MATLAB eyediagram plots 1 column (one eye diagram) or "
        "2 columns (in-phase and quadrature): select 1 or 2 signals in the list, then click Eye Diagram…",
    # 視窗：標題、欄位與提示（eyediagram 的引數 n／period／offset）
    "{base} — {where}：{name}": "{base} — {where}: {name}",
    "每條軌跡的樣本數": "Samples per trace",
    "取樣偏移": "Offset",
    "n（MATLAB eyediagram 的 N）：每條軌跡畫幾個樣本，整數 > 1；預設＝2 × 每符號樣本數（SPS），一條軌跡兩個符號。\n空白或沒改過＝自動（跟著訊號的 SPS）；改了按 Enter":
        "n (N in MATLAB eyediagram): the number of samples plotted in each trace, an integer > 1; default = 2 × samples per symbol (SPS), two symbols "
        "per trace.\nEmpty or unchanged = automatic (follows the signal's SPS); press Enter after changing it",
    "週期（MATLAB PERIOD，正數，預設 1）：一條軌跡在時間軸上的長度——x 軸從 −period/2 到 period/2（奇數 n 照 MATLAB 是\n−(n+1)/(2n)·period 到 (n−1)/(2n)·period）。想用 symbol 當單位就填 n ÷ SPS（n＝2 × SPS 時填 2），用秒就填 n ÷ fs；\n可以寫 SI 字首（2u＝2e-6）；改了按 Enter":
        "Period (MATLAB PERIOD, a positive number, default 1): the length of one trace on the time axis — the x axis runs from −period/2 to period/2 "
        "(for odd n, as in MATLAB,\n−(n+1)/(2n)·period to (n−1)/(2n)·period). To use symbols as the unit enter n ÷ SPS (2 when n = 2 × SPS); for "
        "seconds enter n ÷ fs;\nSI prefixes are accepted (2u = 2e-6); press Enter after changing it",
    "取樣偏移（MATLAB OFFSET，樣本數，整數 0 ≤ offset < n，預設 0）：從 0 算第 offset 個樣本落在 t = 0，之後每 n 個樣本一條軌跡；\n調它讓眼睛張最開的地方在中央。改了按 Enter，或按箭頭":
        "Offset (MATLAB OFFSET, in samples, an integer 0 ≤ offset < n, default 0): sample number offset (counting from 0) falls at t = 0, and a new "
        "trace starts every n samples;\nadjust it to put the widest eye opening in the center. Press Enter after changing it, or use the arrows",
    "勾：只取主圖目前 x 範圍內的樣本（和頻譜／星座圖視窗一樣；訊號所在 panel 的範圍）；不勾：整段資料":
        "On: use only the samples in the main plot's current x range (like the spectrum / constellation windows; the range of the signal's panel); "
        "off: the whole data",
    # 圖（MATLAB eyediagram 寫死的英文）
    "同相訊號的眼圖": "Eye Diagram for In-Phase Signal",
    "正交訊號的眼圖": "Eye Diagram for Quadrature Signal",
    "時間": "Time",
    "振幅（眼圖）": "Amplitude",                       # 「振幅」在頻譜視窗是 Magnitude（i18n_en_batch3），眼圖的 y 軸用這個鍵
    # 狀態列與說明列
    "已畫 {ntr:,} 條軌跡（{m:,} 個樣本）：n = {n}、週期 = {period}、取樣偏移 = {offset}；分析範圍 {rng}":
        "Plotted {ntr:,} traces ({m:,} samples): n = {n}, period = {period}, offset = {offset}; analysis range {rng}",
    "圖用的是 n = {n}、週期 = {period}、取樣偏移 = {offset}（不合格的欄位沿用上一次合格的值）":
        "Plotted with n = {n}, period = {period}, offset = {offset} (invalid fields keep their last valid value)",
    "眼圖沒有畫：{msg}": "Eye diagram not plotted: {msg}",
    # 線條樣式（右鍵；DSV 的樣式選單取代 MATLAB 的 plotstring）
    "眼圖線條的{what}：{value}": "Eye diagram line {what}: {value}",
    "眼圖線條：已重設成自動樣式": "Eye diagram line: reset to the automatic style",
    "眼圖線色": "Eye Diagram Line Color",
    "線型是「無」又沒有標記，看不到線": "the line style is none and there is no marker, so nothing is visible",
    # ---------------------------------------------------------------- 錯誤率比對（第四批 T5：MATLAB biterr／symerr／comm.ErrorRate）
    # 訊號分頁「比對」區的按鈕、清單與 panel 右鍵、快速鍵動作
    "錯誤率比對": "Error Rate",
    "錯誤率比對…": "Error Rate…",
    "錯誤率比對（P{p}）…": "Error Rate (P{p})…",
    "錯誤率比對（選取的 {n} 條）…": "Error Rate ({n} selected)…",
    "開錯誤率比對視窗（MATLAB biterr／symerr／comm.ErrorRate）：TX、RX 兩條數位格式的訊號每個 symbol 取中點一個值比較，\n算誤碼數／誤碼率（k 自動）、符號錯誤數／符號錯誤率、比較的樣本數；接收延遲、計算延遲、自訂樣本位置照 MATLAB。\n預設 TX／RX＝清單選取（沒有選取＝目前 panel）裡排在上面的兩條，視窗裡的下拉可以改；有錯的符號在主圖畫成紅色區段。\npanel 右鍵也有「錯誤率比對（P1）」":
        "Open the error rate window (MATLAB biterr / symerr / comm.ErrorRate): two digital-format signals, TX and RX, are compared with one value "
        "taken at the middle of each symbol,\ngiving the number of bit errors / bit error rate (k automatic), the number of symbol errors / symbol "
        "error rate and the number of samples compared; receive delay, computation delay and custom samples work as in MATLAB.\nTX / RX default to "
        "the top two of the list selection (no selection = the current panel) and can be changed in the window's drop-downs; erroneous symbols are "
        "marked in red on the main plot.\nA panel's right-click menu has Error Rate (P1) too",
    "開啟錯誤率比對（{where}）": "Open error rate ({where})",
    "已開啟錯誤率比對：{where}，TX＝{tx}、RX＝{rx}": "Error rate opened: {where}, TX = {tx}, RX = {rx}",
    "錯誤率比對要兩條訊號（TX、RX）：清單裡只有 1 條（{name}）": "Error rate needs two signals (TX and RX): the list has only one ({name})",
    "錯誤率比對：P{p} 沒有顯示中的訊號": "Error rate: P{p} has no visible signals",
    # 視窗：標題、TX／RX 下拉、欄位與提示（comm.ErrorRate 的 ReceiveDelay／ComputationDelay／Samples／CustomSamples）
    "{base} — TX＝{tx}（P{tp}）、RX＝{rx}（P{rp}）": "{base} — TX = {tx} (P{tp}), RX = {rx} (P{rp})",
    "#{i} P{p}：{name}": "#{i} P{p}: {name}",
    "（類比）": " (analog)",
    "（已經不在清單裡）": "(no longer in the list)",
    "TX（傳送端、當參考）：清單裡的任何一條訊號；預設＝清單選取（沒有選取＝目前 panel）裡排在上面的那條。\n類比格式的訊號後面標「類比」——錯誤率比對只收數位格式的訊號":
        "TX (transmitted, the reference): any signal in the list; default = the top one of the list selection (no selection = the current panel).\n"
        "Signals in analog format are marked analog — the error rate takes digital-format signals only",
    "RX（接收端、要檢查的）：預設＝TX 的下一條。位置 k 的 RX 符號和位置 k − 接收延遲 的 TX 符號比":
        "RX (received, the one checked): default = the signal after TX. The RX symbol at position k is compared with the TX symbol at position "
        "k − receive delay",
    "接收延遲": "Receive delay",
    "計算延遲": "Computation delay",
    "比較樣本": "Samples to consider",
    "整個訊框": "Entire frame",
    "自訂": "Custom",
    "自訂樣本位置": "Selected samples from frame",
    "接收延遲（MATLAB comm.ErrorRate 的 ReceiveDelay，符號數，非負整數，預設 0）：RX 比 TX 晚幾個符號——\n位置 k 的 RX 對位置 k − 接收延遲 的 TX。改了按 Enter，或按箭頭":
        "Receive delay (ReceiveDelay of MATLAB comm.ErrorRate, in symbols, a nonnegative integer, default 0): how many symbols RX lags behind TX —\n"
        "RX at position k is compared with TX at position k − receive delay. Press Enter after changing it, or use the arrows",
    "計算延遲（MATLAB ComputationDelay，符號數，非負整數，預設 0）：最前面幾個對得上的符號不比（例如還沒同步的前導）。\n改了按 Enter，或按箭頭":
        "Computation delay (MATLAB ComputationDelay, in symbols, a nonnegative integer, default 0): the first symbols that line up are not "
        "compared (for example a preamble before synchronization).\nPress Enter after changing it, or use the arrows",
    "比較樣本（MATLAB Samples）：整個訊框＝每個對得上的符號都比（預設）；自訂＝只比「自訂樣本位置」列出的 RX 符號":
        "Samples to consider (MATLAB Samples): Entire frame = compare every symbol that lines up (default); Custom = compare only the RX symbols "
        "listed in Selected samples from frame",
    "自訂樣本位置（MATLAB CustomSamples）：要比 RX 的第幾個符號（1 起算；0 略過、重複只算一次），例如 1 3 5、1:2:99、[1:100 200]；\n選「自訂」時空白是錯誤（MATLAB R2025a 實際的行為）。比較樣本是「整個訊框」時用不到（灰）。改了按 Enter":
        "Selected samples from frame (MATLAB CustomSamples): which RX symbols to compare (counting from 1; 0 is skipped, duplicates count once), "
        "for example 1 3 5, 1:2:99, [1:100 200];\nempty is an error when Custom is selected (what MATLAB R2025a actually does). Not used (grayed) "
        "when Samples to consider is Entire frame. Press Enter after changing it",
    "用主圖現在的訊號資料重新比較（主圖的訊號改了 Offset、SPS、資料或顯示格式時也會自動重算）":
        "Compare again with the main plot's current signal data (it is also recomputed automatically when a signal's Offset, SPS, data or display "
        "format changes)",
    "改成數位格式": "Make Digital",
    "把 TX／RX 裡類比格式的那幾條改成數位格式（和清單／圖上右鍵「顯示格式」→「數位」一樣，主視窗按 Ctrl+Z 可以復原）；\n不是只有 0／1 的值在主圖會畫成匯流排（六角框＋數值）":
        "Switch the analog-format signals among TX / RX to digital format (the same as right-click Display Format → Digital in the list or on the "
        "plot; Ctrl+Z in the main window undoes it);\nsignals with values other than 0 / 1 are drawn as a bus (hexagons with values) on the main plot",
    # 結果（biterr／symerr／comm.ErrorRate 的輸出）
    "結果": "Results",
    "比較的樣本數": "Number of samples compared",
    "符號錯誤數": "Number of symbol errors",
    "符號錯誤率": "Symbol error rate",
    "誤碼數": "Number of bit errors",
    "誤碼率": "Bit error rate",
    "每個符號的位元數 k": "Bits per symbol k",
    "比較的位元數": "Number of bits compared",
    "{k}（自動）": "{k} (automatic)",
    "上一個錯誤": "Previous Error",
    "下一個錯誤": "Next Error",
    "主圖跳到 RX 那張圖裡畫面中心左邊最近的一段錯誤並放大（和「上一個差異」同一套規則）；全部顯示時＝最後一段":
        "Jump the main plot to the nearest error segment left of the view center in the RX plot and zoom in (the same rules as Previous "
        "Difference); with the full view = the last segment",
    "主圖跳到 RX 那張圖裡畫面中心右邊最近的一段錯誤並放大（和「下一個差異」同一套規則）；全部顯示時＝第 1 段":
        "Jump the main plot to the nearest error segment right of the view center in the RX plot and zoom in (the same rules as Next Difference); "
        "with the full view = the first segment",
    "有錯的符號在主圖畫成半透明紅色區段（和「標示差異區間」同一種畫法）":
        "Erroneous symbols are drawn as translucent red segments on the main plot (the same drawing as Highlight Differences)",
    # 說明列與狀態列
    "TX／RX": "TX/RX",
    "{which}「{name}」": "{which} {name}",
    "{names}是類比格式：錯誤率比對只收數位格式的訊號（0/1 或匯流排的值，每個 symbol 取中點一個值直接比）。按「改成數位格式」，或在清單／圖上右鍵 →「顯示格式」→「數位」":
        "{names}: analog format. The error rate takes digital-format signals only (0/1 or bus values; one value at the middle of each symbol is "
        "compared directly). Click Make Digital, or right-click in the list or on the plot → Display Format → Digital",
    "{which} 已經不在清單裡（被移除了），或還沒選：在上面的下拉另選一條":
        "{which} is no longer in the list (removed) or not chosen yet: pick another one in the drop-down above",
    "{names}沒有任何符號（資料是空的，或比半個 symbol 還短）": "{names}: no symbols (the data is empty or shorter than half a symbol)",
    "{name} 有 {n} 個符號（{m} 個樣本 ÷ SPS {sps}），超過錯誤率比對的上限 {max} 個":
        "{name} has {n} symbols ({m} samples ÷ SPS {sps}), more than the error rate limit of {max}",
    "{name} 的 Offset 太大（x 起點 {x0}），對不到 symbol 的格子": "The Offset of {name} is too large (x start {x0}) to line up with the symbol grid",
    "冒號運算產生的元素太多（上限 {max} 個）": "The colon operator produces too many elements (the limit is {max})",
    "RX「{name}」只有 {n} 個符號：自訂樣本位置要在 0～{n} 之間": "RX {name} has only {n} symbols: selected samples must be between 0 and {n}",
    "TX {ntx} 個符號（x {a}..{b} symbol）、RX {nrx} 個符號（x {c}..{d} symbol）":
        "TX {ntx} symbols (x {a}..{b} symbol), RX {nrx} symbols (x {c}..{d} symbol)",
    "；比較了 RX 的第 {j0}～{j1} 個符號（x {s}..{e} symbol）": "; compared RX symbols {j0} to {j1} (x {s}..{e} symbol)",
    "符號錯誤（symerr）：{msg}": "Symbol errors (symerr): {msg}",
    "誤碼數／誤碼率（biterr，X＝TX、Y＝RX）算不出來：{msg}": "Number of bit errors / bit error rate (biterr, X = TX, Y = RX) not computed: {msg}",
    "沒有比較任何符號：接收延遲 {rd}、計算延遲 {cd} 之後，TX 和 RX 沒有對得上的符號（{rng}）":
        "No symbols compared: after receive delay {rd} and computation delay {cd}, no TX and RX symbols line up ({rng})",
    "沒有比較任何符號：自訂樣本位置都不在可以比的範圍（RX 的第 {j0}～{j1} 個符號）":
        "No symbols compared: none of the selected samples is in the comparable range (RX symbols {j0} to {j1})",
    "結果用的是 接收延遲 = {rd}、計算延遲 = {cd}、比較樣本 = {samples}（不合格的欄位沿用上一次合格的值）":
        "Results use receive delay = {rd}, computation delay = {cd}, samples to consider = {samples} (invalid fields keep their last valid value)",
    "比較了 {n} 個符號：符號錯誤 {se} 個（符號錯誤率 {sr}）、誤碼 {be} 個（誤碼率 {br}，每個符號 {k} 位元）":
        "Compared {n} symbols: {se} symbol errors (symbol error rate {sr}), {be} bit errors (bit error rate {br}, {k} bits per symbol)",
    "比較了 {n} 個符號：符號錯誤 {se} 個（符號錯誤率 {sr}）；誤碼率算不出來（見上面的說明）":
        "Compared {n} symbols: {se} symbol errors (symbol error rate {sr}); the bit error rate could not be computed (see the message above)",
    "沒有錯誤區段：錯誤率比對沒有找到有錯的符號": "No error segments: the error rate comparison found no erroneous symbols",
    "沒有更多錯誤（往後）：已經是最後一段，共 {n} 段": "No more errors (forward): this is the last of {n} segments",
    "沒有更多錯誤（往前）：已經是第 1 段，共 {n} 段": "No more errors (backward): this is the first of {n} segments",
    "跳到錯誤 {i}/{n}": "Jump to error {i}/{n}",
    "錯誤 {i}/{n}：P{p}，x {a:.6g}..{b:.6g} {unit}（寬 {w:.6g}）": "Error {i}/{n}: P{p}, x {a:.6g}..{b:.6g} {unit} (width {w:.6g})",
}
