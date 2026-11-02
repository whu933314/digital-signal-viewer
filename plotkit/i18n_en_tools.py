# -*- coding: utf-8 -*-
"""English catalog part: tools — the 2026-10 MATLAB tool-gap batches (measurements panel, transitions, Normalize Y, …).
Keys are the Traditional Chinese source strings, byte for byte.  Names follow MATLAB (Time Scope / Signal Analyzer / Logic Analyzer).
"""
CATALOG = {
    # --- batch A: measurements panel (Signal Statistics + Bilevel Measurements → Cycles) -------------------------
    "量測": "Measurements",
    "訊號統計": "Signal Statistics",
    "脈波（Cycles）": "Bilevel (Cycles)",
    "樣本數": "Samples",
    "最大值": "Max",
    "最小值": "Min",
    "峰對峰值": "Peak to Peak",
    "平均值": "Mean",
    "變異數": "Variance",
    "標準差": "Standard Deviation",
    "中位數": "Median",
    "均方值": "Mean Square",
    "+脈波數": "+ Pulses",
    "−脈波數": "− Pulses",
    "週期": "Period",
    "頻率": "Frequency",
    "脈寬": "Width",
    "工作週期": "Duty Cycle",
    "範圍": "Range",
    "目前 x 視圖": "Current x view",
    "項目…": "Items…",
    "全部項目": "All Items",
    "只列統計": "Statistics Only",
    "只列脈波": "Bilevel Only",
    "複製量測結果（TSV）到剪貼簿": "Copy the measurements (TSV) to the clipboard",
    "量測的 x 範圍。目前 x 視圖＝主圖現在看得到的範圍：縮放、平移後自動重算":
        "x range to measure. Current x view = what the main plot shows now; recomputed after zoom or pan",
    "勾選表格要列哪些量測（會存進設定檔）；在表格上按右鍵也可以":
        "Choose which measurements the table lists (saved in the settings); right-click the table works too",
    "把表格（含標題列）以 TSV 複製到剪貼簿，可直接貼進 Excel／文件（⌘C／Ctrl+C 也可以）":
        "Copy the table (with its header row) to the clipboard as TSV, ready to paste into Excel or a document (⌘C / Ctrl+C too)",
    "在「已繪訊號」選取訊號（或在圖上 Shift＋點線條），這裡會列出它在目前範圍內的量測":
        "Select signals in \"Plotted Signals\" (or Shift+click a line on the plot) to list their measurements over the current range",
    "還沒有圖：先按 PLOT / REFRESH": "Nothing plotted yet: press PLOT / REFRESH first",
    "範圍：x {a:.6g} .. {b:.6g} {unit}（{src}）": "Range: x {a:.6g} .. {b:.6g} {unit} ({src})",
    "；「{name}」目前不能用，改用目前 x 視圖": "; \"{name}\" is not available now, using the current x view",
    "；選了 {n} 條，只列前 {m} 條": "; {n} selected, only the first {m} are listed",
    "。脈波：狀態位準用直方圖找低／高位準，越過 10%→90% 才算一次轉態、位置取 50% 中位準":
        ". Bilevel: state levels from the histogram (low/high); a transition must cross 10% → 90%, timed at the 50% mid reference",
    "範圍\tx {a:.6g} .. {b:.6g} {unit}": "Range\tx {a:.6g} .. {b:.6g} {unit}",
    "量測：沒有可複製的結果（先選取訊號並畫圖）": "Measurements: nothing to copy (select signals and plot first)",
    "量測：至少要留一個項目": "Measurements: keep at least one item",
    "量測：複製失敗：{err}": "Measurements: copy failed: {err}",
    "已複製 {n} 項量測（{m} 條訊號，TSV）到剪貼簿": "Copied {n} measurements ({m} signals, TSV) to the clipboard",
    "開關「量測」面板（MATLAB Time Scope 的 Signal Statistics＋Bilevel Measurements）：\n列出選取訊號在目前 x 範圍內的最大／最小值（含位置）、峰對峰、平均、變異數、標準差、中位數、RMS、均方值，\n以及 +／−脈波數、週期、頻率、脈寬、工作週期；縮放、平移或改選取時自動重算":
        "Show / hide the Measurements panel (MATLAB Time Scope Signal Statistics + Bilevel Measurements):\n"
        "max / min (with position), peak to peak, mean, variance, standard deviation, median, RMS and mean square of the selected signals over the current x range,\n"
        "plus + / − pulses, period, frequency, width and duty cycle; recomputed after zoom, pan or a new selection",
    # --- batch A: previous / next transition --------------------------------------------------------------------
    "轉態": "Transitions",
    "上一個轉態": "Previous Transition",
    "下一個轉態": "Next Transition",
    "上一個／下一個轉態": "Previous / Next Transition",
    "把視圖（與十字游標）移到選取訊號在畫面中心左邊最近的一次值改變，縮放比例不變（快速鍵 [ ）。\n需要先在「已繪訊號」選取訊號（或在圖上 Shift＋點線條）":
        "Move the view (and the crosshair) to the nearest value change of the selected signals left of the view center, keeping the zoom (shortcut [ ).\n"
        "Select signals in \"Plotted Signals\" first (or Shift+click a line on the plot)",
    "把視圖（與十字游標）移到選取訊號在畫面中心右邊最近的一次值改變，縮放比例不變（快速鍵 ] ）。\n需要先在「已繪訊號」選取訊號（或在圖上 Shift＋點線條）":
        "Move the view (and the crosshair) to the nearest value change of the selected signals right of the view center, keeping the zoom (shortcut ] ).\n"
        "Select signals in \"Plotted Signals\" first (or Shift+click a line on the plot)",
    "轉態：還沒有圖，先按 PLOT / REFRESH": "Transitions: nothing plotted yet, press PLOT / REFRESH first",
    "所選訊號沒有轉態（整段的值都沒變）": "The selected signals have no transitions (the value never changes)",
    "沒有更多轉態（往後）：已經是最後一個，共 {n} 個": "No more transitions (forward): this is the last one of {n}",
    "沒有更多轉態（往前）：已經是第 1 個，共 {n} 個": "No more transitions (backward): this is the first of {n}",
    "跳到轉態 {i}/{n}": "Go to transition {i}/{n}",
    "轉態 {i}/{n}：x = {x:.6g} {unit}（{names}）": "Transition {i}/{n}: x = {x:.6g} {unit} ({names})",
    # --- batch A: Normalize Y -------------------------------------------------------------------------------------
    "每條線除以自己的峰值絕對值再畫（同一張圖裡大小差很多的訊號可以疊在一起比形狀）；\n只影響畫面：十字游標、資料提示、量測、匯出仍是原始值。可和「疊圖 y 位移」一起用":
        "Divide each line by its own peak absolute value before drawing (signals of very different size can be overlaid to compare shapes);\n"
        "display only: the crosshair, data tips, measurements and exports keep the original values. Works together with the stack y offset",
    "每條線除以自己的峰值絕對值（只影響畫面）；和疊圖 y 位移可以一起用":
        "Divide each line by its own peak absolute value (display only); works together with the stack y offset",
    # --- batch B: data cursors (Time Scope / Signal Analyzer "Data Cursors" + Cursor Measurements) --------------------
    "兩游標之間": "Between cursors",
    "游標量測": "Cursor Measurements",
    "游標": "Cursors",
    "資料游標": "Data Cursors",
    "資料游標 ▾": "Data Cursors ▾",
    "一條": "One",
    "兩條": "Two",
    "游標 1": "Cursor 1",
    "游標 2": "Cursor 2",
    "項目": "Item",
    "移到視圖": "Bring into View",
    "游標移到視圖": "Cursors into View",
    "游標移到目前視圖": "Bring Cursors into View",
    "鎖定游標間距": "Lock cursor spacing",
    "顯示「游標量測」面板": "Show the \"Cursor Measurements\" Panel",
    "複製游標讀數（TSV）到剪貼簿": "Copy the cursor readout (TSV) to the clipboard",
    "MATLAB Data Cursors：無／一條／兩條垂直游標（標 1、2）。打開時放在目前視圖的中央（兩條＝中央 ±1/4），\n用滑鼠拖曳游標線；位置存進設定檔":
        "MATLAB Data Cursors: None / One / Two vertical cursors (labelled 1, 2). Turned on, they go to the center of the current view "
        "(two = center ±1/4);\ndrag a cursor line with the mouse; positions are saved in the settings",
    "把游標移回目前看得到的範圍（中央；兩條＝中央 ±1/4）": "Move the cursors back into the visible range (center; two = center ±1/4)",
    "把游標移回目前看得到的範圍（中央；兩條＝中央 ±1/4）；游標關著時打開兩條":
        "Move the cursors back into the visible range (center; two = center ±1/4); turns on two cursors when they are off",
    "把游標讀數（含標題列）以 TSV 複製到剪貼簿（⌘C／Ctrl+C 也可以）":
        "Copy the cursor readout (with its header row) to the clipboard as TSV (⌘C / Ctrl+C too)",
    "拖曳時游標吸到最近的樣本（選取的訊號；沒選取時用第一條顯示的訊號）":
        "While dragging, the cursor snaps to the nearest sample (of the selected signal; the first shown signal when none is selected)",
    "Lock cursor spacing：拖一條游標時兩條一起移動，Δx 不變": "Lock cursor spacing: dragging one cursor moves both, Δx stays the same",
    "MATLAB Time Scope／Signal Analyzer 的 Data Cursors：無／一條／兩條垂直游標（標 1、2），\n貫穿所有 panel、可拖曳；「游標量測」面板列出 x1、x2、Δx、1/Δx 與各訊號在游標處的值和 Δy。\n量測面板的範圍可選「兩游標之間」":
        "Data Cursors of MATLAB Time Scope / Signal Analyzer: None / One / Two vertical cursors (labelled 1, 2)\n"
        "across all panels, draggable; the \"Cursor Measurements\" panel lists x1, x2, Δx, 1/Δx and each signal's value at the cursors and Δy.\n"
        "The Measurements panel can use the range \"Between cursors\"",
    "資料游標：關": "Data cursors: off",
    "資料游標：{n} 條（拖曳游標線移動；「游標量測」面板列出各訊號在游標處的值）":
        "Data cursors: {n} (drag a cursor line to move it; the \"Cursor Measurements\" panel lists each signal's value at the cursors)",
    "資料游標：開（加入訊號並畫圖後出現）": "Data cursors: on (they appear once signals are added and plotted)",
    "Snap to data：開（游標吸到最近的樣本）": "Snap to data: on (cursors snap to the nearest sample)",
    "Snap to data：關": "Snap to data: off",
    "鎖定游標間距：開（拖一條，兩條一起動）": "Lock cursor spacing: on (drag one, both move)",
    "鎖定游標間距：關": "Lock cursor spacing: off",
    "游標 1：x = {x1} {unit}": "Cursor 1: x = {x1} {unit}",
    "游標 1：x = {x1}、游標 2：x = {x2}、Δx = {dx} {unit}": "Cursor 1: x = {x1}, cursor 2: x = {x2}, Δx = {dx} {unit}",
    "資料游標關著：在上面選「一條」或「兩條」（分析 → 資料游標 也可以）":
        "Data cursors are off: choose \"One\" or \"Two\" above (or Analyze → Data Cursors)",
    "拖曳圖上的游標線移動（游標線左右幾個像素內就抓得到）": "Drag the cursor lines on the plot (they can be grabbed a few pixels either side)",
    "；1/Δx 用 symbol rate 換算成 Hz；量測面板的範圍可選「兩游標之間」":
        "; 1/Δx is converted to Hz with the symbol rate; the Measurements panel can use the range \"Between cursors\"",
    "游標量測：沒有可複製的讀數（先打開資料游標並畫圖）": "Cursor measurements: nothing to copy (turn on data cursors and plot first)",
    "游標量測：複製失敗：{err}": "Cursor measurements: copy failed: {err}",
    "已複製游標讀數（{n} 列，TSV）到剪貼簿": "Copied the cursor readout ({n} rows, TSV) to the clipboard",
    # --- batch B: data tips — export, Δ between tips, tip content ---------------------------------------------------
    "匯出資料提示…": "Export Data Tips…",
    "匯出資料提示": "Export Data Tips",
    "匯出提示…": "Export Tips…",
    "複製資料提示（TSV）": "Copy Data Tips (TSV)",
    "提示內容…": "Tip Content…",
    "提示內容": "Tip Content",
    "提示內容：{rows}": "Tip content: {rows}",
    "、": ", ",
    "資料提示要顯示的列（套用到全部提示）：": "Rows shown in data tips (applies to all tips):",
    "樣本索引（Index）": "Sample index (Index)",
    "樣本索引": "Sample index",
    "訊號名稱": "Signal",
    "文字檔（Tab 分隔）": "Text file (tab separated)",
    "沒有資料提示可匯出：先在線上點一下釘住提示": "No data tips to export: click a line first to pin a tip",
    "已匯出 {n} 個資料提示：{path}": "Exported {n} data tips: {path}",
    "已複製 {n} 個資料提示（TSV）到剪貼簿": "Copied {n} data tips (TSV) to the clipboard",
    "匯出失敗：{err}": "Export failed: {err}",
    "複製失敗：{err}": "Copy failed: {err}",
    "資料提示 #{b} − #{a}：Δx = {dx}{unit}、Δy = {dy}": "Data tip #{b} − #{a}: Δx = {dx}{unit}, Δy = {dy}",
    "把全部資料提示（訊號、panel、樣本索引、x、y）存成 TXT（Tab 分隔）或 CSV；右鍵提示框也有「複製資料提示（TSV）」":
        "Save all data tips (signal, panel, sample index, x, y) as TXT (tab separated) or CSV; right-clicking a tip also offers \"Copy Data Tips (TSV)\"",
    "把全部資料提示（訊號、panel、樣本索引、x、y）存成 TXT（Tab 分隔）或 CSV；\n右鍵提示框也有「複製資料提示（TSV）」。兩個以上提示時狀態列顯示選取的提示和前一個的 Δx／Δy":
        "Save all data tips (signal, panel, sample index, x, y) as TXT (tab separated) or CSV;\n"
        "right-clicking a tip also offers \"Copy Data Tips (TSV)\". With two or more tips the status bar shows Δx / Δy between the selected tip and the previous one",
    "選資料提示要顯示哪些列：名稱、X、Y、樣本索引、Panel（套用到全部提示，存進圖檔）":
        "Choose the rows data tips show: name, X, Y, sample index, panel (applies to all tips, saved in the figure file)",
    "選資料提示要顯示哪些列：名稱、X、Y、樣本索引、Panel（套用到全部提示，存進設定檔）":
        "Choose the rows data tips show: name, X, Y, sample index, panel (applies to all tips, saved in the settings)",
    # --- batch C: Plot Type, I/Q magnitude/phase, Spectrum Analyzer units, Constellation Diagram -------------------
    "繪圖類型": "Plot Type",
    "繪圖類型 ▾": "Plot Type ▾",
    "繪圖類型（Plot type）": "Plot type",
    "線條（line）": "Line",
    "階梯（stairs）": "Stairs",
    "針狀（stem）": "Stem",
    "繪圖類型 {name}": "Plot type {name}",
    "繪圖類型 {ptype}（{n} 條）": "Plot type {ptype} ({n} signals)",
    "繪圖類型已經是 {name}": "Plot type is already {name}",
    "已把 {n} 條訊號的繪圖類型改成 {name}": "Changed the plot type of {n} signal(s) to {name}",
    "（{k} 條超過 {max:,} 點，改用線條畫）": " ({k} over {max:,} points drawn as lines instead)",
    "（超過 {max:,} 點的不畫針頭）": " (stem heads omitted above {max:,} points)",
    "{n} 條針狀（stem）超過 {max:,} 點改用線條畫": "{n} stem signal(s) over {max:,} points drawn as lines",
    "MATLAB Time Scope 的 PlotType：選取訊號畫成 線條（line，樣本點連直線）／階梯（stairs，預設）／\n針狀（stem，每個樣本一根針＋空心圓頭）。每條訊號各自記住、存進設定檔，Ctrl+Z 可復原；\n右鍵選單與「訊號屬性 → 訊號參數」也可以改":
        "MATLAB Time Scope PlotType: draw the selected signals as Line (samples joined by straight lines) / Stairs (default) /\n"
        "Stem (one stem with a hollow circle per sample). Remembered per signal and saved in the settings; Ctrl+Z undoes it;\n"
        "also in the right-click menu and Signal Properties → Signal Parameters",
    "選取訊號的畫法（選了就套用）：線條＝樣本點連直線、階梯＝每個樣本保持到下一個（預設）、針狀＝stem；\n針狀超過 {max:,} 點改用線條畫（狀態列說明）":
        "How the selected signals are drawn (applies on selection): Line = samples joined by lines, Stairs = each sample held until the next (default), Stem;\n"
        "stem signals over {max:,} points are drawn as lines (the status bar says so)",
    "I/Q 幅度／相位": "I/Q Magnitude/Phase",
    "MATLAB Time Scope 的 PlotAsMagnitudePhase：把 I/Q 配對算成 |I+jQ| 與相位（度）兩條衍生訊號，\n各放一個新 panel（選取 I、Q 兩條，或名稱含 adc i／adc q 自動配對；沒有選取時從全部訊號找）。\n衍生訊號跟著來源更新（改 shift／scale／突波抑制會重算），可以像一般訊號一樣量測、做頻譜；Ctrl+Z 可復原":
        "MATLAB Time Scope PlotAsMagnitudePhase: turn an I/Q pair into two derived signals, |I+jQ| and phase (degrees),\n"
        "each in a new panel (select I and Q, or name them adc i / adc q to pair automatically; with no selection all signals are searched).\n"
        "Derived signals follow their sources (changing shift / scale / despike recomputes them) and can be measured or analyzed like any signal; Ctrl+Z undoes it",
    "I/Q 幅度／相位：沒有訊號。先在「資料夾」面板把檔案加進已繪訊號": "I/Q Magnitude/Phase: no signals. Add files from the Folder panel first",
    "I/Q 幅度／相位：找不到 I/Q 配對（{what}）——請選取 I、Q 兩條訊號，或讓名稱含 adc i／adc q":
        "I/Q Magnitude/Phase: no I/Q pair found ({what}) — select the I and Q signals, or name them adc i / adc q",
    "I/Q 幅度／相位：新增 {n} 條衍生訊號": "I/Q Magnitude/Phase: added {n} derived signals",
    "這些 I/Q 配對已經有幅度／相位訊號了": "These I/Q pairs already have magnitude/phase signals",
    "已新增 {n} 條衍生訊號（{pairs}）：|I+jQ| 與相位（度）各一個 panel（Ctrl+Z 可復原）":
        "Added {n} derived signals ({pairs}): |I+jQ| and phase (degrees), one panel each (Ctrl+Z to undo)",
    "{key}（來源訊號不見了）": "{key} (source signals are missing)",
    "相位展開": "Unwrap Phase",
    "相位不展開": "Wrap Phase",
    "相位用 unwrap 展開成連續的角度（不在 ±180° 跳回）：套用到選取的相位訊號（沒有選取＝全部相位訊號），\n之後新增的相位訊號也照這個設定":
        "Unwrap the phase into a continuous angle (no jumps at ±180°): applies to the selected phase signals (all phase signals when none are selected)\n"
        "and to phase signals added later",
    "相位展開：{state}（新增的相位訊號照這個設定）": "Unwrap phase: {state} (new phase signals use this setting)",
    "相位展開 {state}（{n} 條）": "Unwrap phase {state} ({n} signals)",
    "已把 {n} 條相位訊號改成{how}": "Changed {n} phase signal(s) to {how}",
    "展開（連續角度）": "unwrapped (continuous angle)",
    "−180°..180°": "−180°..180°",
    "開": "on",
    "關": "off",
    "全部": "All",
    # spectrum units
    "頻譜類型": "Spectrum type",
    "振幅（Magnitude）": "Magnitude",
    "功率（Power）": "Power",
    "功率密度（Power Density）": "Power Density",
    "Reference load (Ω)": "Reference load (Ω)",
    "MATLAB Spectrum Analyzer 的 Spectrum type：\n振幅（預設，和舊版相同）：單音振幅 A 讀 A；功率：單音讀 A²/2（每個 bin 的功率）；\n功率密度：除以 RBW（dB/Hz，白雜訊讀 2σ²/fs）；RMS：√功率（Vrms，單音讀 A/√2）":
        "MATLAB Spectrum Analyzer Spectrum type:\nMagnitude (default, same as before): a tone of amplitude A reads A; Power: a tone reads A²/2 (power per bin);\n"
        "Power Density: divided by the RBW (dB/Hz, white noise reads 2σ²/fs); RMS: √power (Vrms, a tone reads A/√2)",
    "dB＝相對（20·log10 振幅或 10·log10 功率；RMS 是 dBV）；\ndBFS＝相對滿刻度：振幅等於 Full scale 的單音讀 0 dBFS；\ndBm＝功率 / Reference load / 1 mW。只在勾 dB 時有用；關掉 dB 用線性（W、W/Hz、Vrms）":
        "dB = relative (20·log10 amplitude or 10·log10 power; dBV for RMS);\ndBFS = relative to full scale: a tone whose amplitude equals Full scale reads 0 dBFS;\n"
        "dBm = power / Reference load / 1 mW. Used only when dB is ticked; with dB off the scale is linear (W, W/Hz, Vrms)",
    "dBFS 的滿刻度（振幅）；空白＝自動：由資料猜 ADC 位元數（無號 offset binary → 2^(b−1)、有號整數 → 2^(b−1)、±1 浮點 → 1）。\n改了按 Enter":
        "Full scale (amplitude) for dBFS; empty = automatic: the ADC bit width is guessed from the data (unsigned offset binary → 2^(b−1), signed integers → 2^(b−1), ±1 floats → 1).\nPress Enter after editing",
    "dBm 與 W 的參考負載（Ω，預設 1）：功率 = V² / R；改了按 Enter": "Reference load for dBm and W (Ω, default 1): power = V² / R; press Enter after editing",
    "y 軸用 dB（單位選 dB／dBFS／dBm）；關掉用線性：振幅、W、W/Hz 或 Vrms（依頻譜類型）":
        "Logarithmic y axis (choose dB / dBFS / dBm under Units); off = linear: amplitude, W, W/Hz or Vrms (depending on the spectrum type)",
    "類型 {t}": "Type {t}",
    "單位 {u}": "Units {u}",
    "單位 線性": "Units linear",
    "Full scale = {v:g}（{how}）": "Full scale = {v:g} ({how})",
    "Reference load = {r:g} Ω": "Reference load = {r:g} Ω",
    "{b} bit 無號（中心 {half:g}）": "{b}-bit unsigned (center {half:g})",
    "{b} bit 有號": "{b}-bit signed",
    "浮點 ±1": "float ±1",
    "峰值": "peak",
    "手動": "manual",
    # constellation
    "星座圖": "Constellation Diagram",
    "星座圖…": "Constellation…",
    "星座圖 — {names}": "Constellation Diagram — {names}",
    "開啟星座圖視窗": "Open Constellation Diagram window",
    "已開啟星座圖視窗：{n} 組 I/Q（{pairs}）": "Opened the Constellation Diagram window: {n} I/Q pair(s) ({pairs})",
    "星座圖：沒有訊號。先在「資料夾」面板把檔案加進已繪訊號": "Constellation: no signals. Add files from the Folder panel first",
    "星座圖：找不到 I/Q 配對（{what}）——請選取 I、Q 兩條訊號，或讓名稱含 adc i／adc q":
        "Constellation: no I/Q pair found ({what}) — select the I and Q signals, or name them adc i / adc q",
    "開星座圖視窗（MATLAB Constellation Diagram／scatterplot）：I 對 Q 的散佈圖，每 Samples per symbol 取一點。\n需要 I、Q 兩條訊號——選取 2 條，或讓名稱含 adc i／adc q 自動配對（沒有選取時從全部訊號找）；\n可調 Offset、只畫最後 N 個符號、只用目前 x 範圍、等比例軸、參考星座（RMS EVM）":
        "Open the Constellation Diagram window (MATLAB Constellation Diagram / scatterplot): I versus Q, one point every Samples per symbol.\n"
        "Needs I and Q signals — select 2, or name them adc i / adc q to pair automatically (with no selection all signals are searched);\n"
        "Offset, last N symbols only, current x range only, equal axes and a reference constellation (RMS EVM) are adjustable",
    "每幾個樣本取一個符號點（MATLAB SamplesPerSymbol）；預設＝I 訊號的 SPS，1＝畫全部樣本（scatterplot）。\n可以是小數（四捨五入到最近的樣本）；改了按 Enter":
        "Take one symbol point every this many samples (MATLAB SamplesPerSymbol); default = the SPS of the I signal, 1 = plot every sample (scatterplot).\n"
        "May be fractional (rounded to the nearest sample); press Enter after editing",
    "第一個符號點的樣本位置（MATLAB SampleOffset，樣本數，0 ≤ offset < SPS 最常用）：\n眼圖張最開的那個取樣相位；改了按 Enter 或箭頭":
        "Sample position of the first symbol point (MATLAB SampleOffset, in samples, usually 0 ≤ offset < SPS):\nthe sampling phase where the eye is most open; press Enter or use the arrows",
    "顯示符號": "Symbols",
    "最後 N 個": "Last N",
    "Symbols to display：全部（上限 {max:,} 點）或只畫最後 N 個符號": "Symbols to display: all (up to {max:,} points) or only the last N symbols",
    "「最後 N 個」的 N（MATLAB SymbolsToDisplay，預設 256）；改了按 Enter 或箭頭": "N for \"Last N\" (MATLAB SymbolsToDisplay, default 256); press Enter or use the arrows",
    "用主圖「目前」的 x 範圍與訊號資料重新畫：主圖縮放／平移、改 SPS 或 shift 後按這裡；資料提示會清掉":
        "Redraw with the main plot's current x range and signal data: press after zooming / panning the main plot or changing SPS or shift; data tips are cleared",
    "只用目前 x 範圍": "Current x range only",
    "等比例軸": "Equal axes",
    "勾：只取主圖目前 x 範圍內的樣本（和頻譜／GFSK 視窗一樣）；不勾：整段資料":
        "Ticked: only samples inside the main plot's current x range (like the Spectrum / GFSK windows); unticked: the whole record",
    "I、Q 兩軸同一個比例（圓看起來是圓）": "Same scale on the I and Q axes (circles look round)",
    "畫格線與 I=0、Q=0 兩條軸線": "Draw grid lines and the I = 0, Q = 0 axes",
    "先扣掉分析範圍內 I、Q 各自的平均值（offset binary ADC 不用先平移也會置中）":
        "Subtract the mean of I and of Q over the analysis range first (offset-binary ADC data is centered without shifting)",
    "參考星座": "Reference",
    "疊上參考星座點（MATLAB ReferenceConstellation，自動縮放到量到的 RMS）並在狀態列算 RMS EVM":
        "Overlay reference constellation points (MATLAB ReferenceConstellation, scaled to the measured RMS) and show the RMS EVM in the status bar",
    "Samples per symbol 必須是 > 0 的數字": "Samples per symbol must be a number > 0",
    "找不到 I/Q 配對：關掉這個視窗，在清單選取 I、Q 兩條訊號後再按 星座圖…":
        "No I/Q pair found: close this window, select the I and Q signals in the list, then press Constellation… again",
    "{i} 與 {q} 的 SPS 不同，用樣本索引對齊": "{i} and {q} have different SPS; aligned by sample index",
    "{n:,} 個符號超過上限，只畫最後 {max:,} 個": "{n:,} symbols exceed the limit; only the last {max:,} are plotted",
    "{i}/{q}：分析範圍內沒有符號點": "{i}/{q}: no symbol points in the analysis range",
    "參考 {name}": "Reference {name}",
    "同相 I": "In-phase (I)",
    "正交 Q": "Quadrature (Q)",
    "Samples per symbol = {sps:g}，Offset = {off:g}，{n:,} 個符號": "Samples per symbol = {sps:g}, Offset = {off:g}, {n:,} symbols",
    "已畫 {n:,} 個符號點（{p} 組 I/Q）；分析範圍 {rng}": "Plotted {n:,} symbol points ({p} I/Q pair(s)); analysis range {rng}",
    "；RMS EVM = {evm:.2f}%（對 {name}）": "; RMS EVM = {evm:.2f}% (vs {name})",
    # --- 游標加強：放大／平移模式拖游標、水平游標（Screen Cursors → Horizontal）、鍵盤微調 ------------------------------
    "水平游標": "Horizontal Cursors",
    "MATLAB Time Scope 的 Screen Cursors → Horizontal：每個 panel 兩條水平游標（標 1、2，在右緣），可和垂直游標同時開；\n拖曳移動，點一下選取後 ↑／↓ 微調 1 像素（Shift ×10）；「游標量測」面板列出 y1、y2、Δy（左軸單位，有右軸另列右軸值）":
        "MATLAB Time Scope Screen Cursors → Horizontal: two horizontal cursors per panel (labelled 1, 2 at the right edge); can be on together with "
        "the vertical cursors;\ndrag to move, or click to select and nudge 1 pixel with ↑ / ↓ (Shift ×10); the \"Cursor Measurements\" panel lists "
        "y1, y2, Δy (left-axis units, plus right-axis values when there is a right axis)",
    "水平游標：開（每個 panel 兩條，拖曳或選取後按 ↑／↓ 移動）": "Horizontal cursors: on (two per panel; drag them, or select one and press ↑ / ↓)",
    "水平游標：關": "Horizontal cursors: off",
    "P{p} y": "P{p} y",
    "P{p} y 右軸": "P{p} y right axis",
    "P{p} 水平游標：y1 = {y1}、y2 = {y2}、Δy = {dy}": "P{p} horizontal cursors: y1 = {y1}, y2 = {y2}, Δy = {dy}",
    "；水平游標每個 panel 兩條（y＝左軸單位；Normalize Y／疊圖位移時另列各訊號的原始值）":
        "; horizontal cursors: two per panel (y in left-axis units; with Normalize Y / stack offset each signal's raw value is listed too)",
    "；點一下游標＝選取，方向鍵微調（Shift ×10）": "; click a cursor to select it, then nudge it with the arrow keys (Shift ×10)",
    "已選取游標 {n}：←／→ 微調（Snap 開＝一個樣本、關＝1 像素；Shift ×10）、Esc 取消選取":
        "Cursor {n} selected: ← / → nudge it (one sample with Snap on, 1 pixel with it off; Shift ×10), Esc deselects",
    "已選取水平游標 {n}：↑／↓ 微調 1 像素（Shift ×10）、Esc 取消選取": "Horizontal cursor {n} selected: ↑ / ↓ nudge it 1 pixel (Shift ×10), Esc deselects",
    # 面板組 review（2026-10-23）
    "把表格（含標題列）以 TSV 複製到剪貼簿，可直接貼進 Excel／文件（⌘C／Ctrl+C 也可以）；\n表格是空的（還沒選取訊號）時是灰的":
        "Copy the table (with its header row) to the clipboard as TSV, ready to paste into Excel or a document (⌘C / Ctrl+C too);\ngrayed out while the table is empty (no signal selected)",
    "把游標讀數（含標題列）以 TSV 複製到剪貼簿（⌘C／Ctrl+C 也可以）；\n資料游標關著或還沒有圖時是灰的":
        "Copy the cursor readout (with its header row) to the clipboard as TSV (⌘C / Ctrl+C too);\ngrayed out while data cursors are off or nothing is plotted",
    "已取消拖曳 panel": "Panel drag canceled",
    # --- 鍵盤稽核：鍵盤縮放／平移進 undo（MATLAB uiundo） -------------------------------------------------------
    "縮放／平移": "Zoom/Pan",
    # --- 邊界資料稽核 ---
    "{name}：範圍內有 {n} 個 NaN／Inf，略過": "{name}: {n} NaN/Inf value(s) in range, skipped",
    "{name}：數值太大，頻譜溢位（inf），略過": "{name}: values too large, spectrum overflowed (inf), skipped",
}

# --- 限制修正（2026-10-23）：I/Q 衍生訊號時間軸、星座圖時序／相位修正 --------------------------------------------
CATALOG.update({
    "衍生訊號時間軸跟著來源 I：{names}": "Derived signals follow the time base of source I: {names}",
    "I/Q 時間軸不一致：{q} 的 SPS／offset 和 {i} 不同（幅度／相位照 {i} 的時間軸、按樣本索引配對）":
        "I/Q time base mismatch: the SPS/offset of {q} differs from {i} (magnitude/phase use the time base of {i}, paired by sample index)",
    "時序／相位修正": "Timing/phase correction",
    "算 EVM 前先做簡單的同步（要選參考星座；預設關＝照上面的 Offset、不旋轉）：\n時序＝0 ≤ offset < SPS 每個取樣相位都試算，挑 EVM 最小的；相位＝參考星座的最小平方相位旋轉。\n修正後的點畫在圖上，狀態列標示「已做時序／相位修正」":
        "Simple synchronization before computing the EVM (needs a reference constellation; off by default = use the Offset above, no rotation):\nTiming = try every sampling phase 0 ≤ offset < SPS and pick the lowest EVM; phase = least-squares rotation onto the reference constellation.\nThe corrected points are plotted and the status bar says \"timing/phase corrected\"",
    "時序／相位修正要先選參考星座": "Timing/phase correction needs a reference constellation",
    "；已做時序／相位修正（offset {offs}、相位 {phs}）": "; timing/phase corrected (offset {offs}, phase {phs})",
})

# --- 貼到圖片視窗、文字欄（2026-10-23） ---
CATALOG.update({
    "剪貼簿是空的：先選訊號按「複製訊號」（Ctrl+C）": "The clipboard is empty: select signals and press Copy Signals (Ctrl+C) first",
    "已把 {n} 條訊號貼到新的「{title}」": "Pasted {n} signal(s) into a new \"{title}\"",
    "已把 {n} 條訊號貼到「{title}」": "Pasted {n} signal(s) into \"{title}\"",
    "{name}：整欄沒有數值（當成 NaN，不畫線）": "{name}: the column has no numeric values (treated as NaN, not drawn)",
})

# --- 首頁重新分類、拿掉 PLOT/REFRESH、panel 握把與刪除（2026-10-23） ---
CATALOG.update({
    "工作階段": "Session",
    "重新讀取根資料夾的檔案清單，並重新載入已繪訊號中被改寫過的檔案後重畫（檔案有新增、刪除、改名或重新擷取覆蓋時按；位址列按 Enter 也一樣）":
        "Re-read the file list of the root folder and reload plotted signals whose files were overwritten, then redraw (press after files were added, deleted, renamed or re-captured; Enter in the address bar does the same)",
    "；重新讀取 {k} 個改過的檔案並重畫": "; reloaded {k} changed file(s) and redrew",
    "選根資料夾": "Choose the root folder",
    "重新掃描根資料夾，並重新載入被改寫過的檔案（Enter 也一樣）": "Rescan the root folder and reload overwritten files (Enter does the same)",
    "加入選取的：把資料夾面板裡選取的檔案或 CSV 欄位加進已繪訊號並重畫（雙擊檔案或按 Enter 也可以）":
        "Add Selected: add the files or CSV columns selected in the Folder panel to Plotted Signals and redraw (double-click or Enter also works)",
    "加入全部顯示的：把資料夾面板目前列出的檔案全部加進已繪訊號（有搜尋條件時只加顯示的；CSV 直接加所有欄位）":
        "Add All Shown: add every file currently listed in the Folder panel (only the shown ones when a search filter is active; CSV adds all columns)",
    "項目…：勾選表格要列哪些量測（會存進設定檔）；在表格上按右鍵也可以": "Rows…: choose which measurements the table lists (saved in settings); right-click the table also works",
    "尚無訊號：在左側「資料夾」面板選檔案，按「加入選取的」": "No signals yet: pick files in the Folder panel on the left and press Add Selected",
    "刪除這個 panel": "Delete this panel",
    "上移 panel": "Move panel up",
    "下移 panel": "Move panel down",
    "P{p} 沒有訊號": "P{p} has no signals",
    "刪除 panel": "Delete panel",
    "刪除 P{p}（{n} 條訊號）？": "Delete P{p} ({n} signal(s))?",
    "刪除 P{p}": "Delete P{p}",
    "刪除 P{p}（{n} 條訊號）": "Deleted P{p} ({n} signal(s))",
    "已刪除 P{p}：{n} 條訊號（Ctrl+Z 可復原）": "Deleted P{p}: {n} signal(s) (Ctrl+Z undoes)",
})

# --- 複製／剪下的對象可以是資料提示所在的訊號（2026-10-23） ---
CATALOG.update({
    "「{what}」要先在「已繪訊號」清單選取訊號（或在圖上點線條釘資料提示、Shift＋點線條選取）":
        "\"{what}\" needs a signal: select one in Plotted Signals (or click a line to pin a data tip, or Shift-click a line to select it)",
})

# --- 分頁重新分類、右鍵顏色、WAV／NPY、拖放（2026-10-23） ---
CATALOG.update({
    "順序": "Order", "圖片視窗": "Figure Windows", "分析視窗": "Analysis Windows", "比對": "Compare", "互動": "Interaction",
    "顏色": "Color",
    "已把 {n} 條訊號的線色改成 {color}（Ctrl+Z 可復原）": "Line color of {n} signal(s) set to {color} (Ctrl+Z undoes)",
    "匯入 CSV / MAT / WAV": "Import CSV / MAT / WAV", "可讀的資料檔": "Readable data files", "文字": "Text",
    "拖放加入": "Drop files", "拖放加入 {n} 條訊號": "Dropped files: added {n} signal(s)",
    "拖進來的檔案都已在已繪訊號裡": "The dropped files are already in Plotted Signals",
    "根資料夾改成 {path}": "root folder set to {path}",
    "{n} 個檔案不認得或讀不了：{names}": "{n} file(s) not recognised or unreadable: {names}",
})

# --- 7 個分頁、參數列放到工具列、預設版面（2026-10-23） ---
CATALOG.update({
    "參數": "Parameters", "線條": "Lines", "數位顯示": "Digital Display", "座標": "Axes", "縮放": "Zoom", "圖檔": "Image File",
    "→ SPS": "→ SPS",
    "版面已經是預設版面（左：資料夾、已繪訊號｜右：圖）": "The layout is already the default (left: Folder, Plotted Signals | right: plot)",
    "已恢復預設版面（左：資料夾、已繪訊號｜右：圖）": "Default layout restored (left: Folder, Plotted Signals | right: plot)",
})

CATALOG.update({
    "和「訊號屬性」面板是同一個設定；改好後按 Enter 或「套用」": "Same setting as the Signal Properties panel; press Enter or Apply after editing",
    "選了就套用": "applies when selected", "套用（在輸入格按 Enter 也一樣）": "Apply (Enter in the entry does the same)",
    "切換後立刻重畫": "redraws immediately", "拖曳，放開就套用": "drag; applies on release",
})

CATALOG.update({
    "重畫時保留 x 範圍：開（改設定重畫時不會動目前的 x 縮放）": "Keep x range on redraw: on (redraws after setting changes keep the current x zoom)",
    "改設定或重新掃描重畫時保留目前的 x 縮放範圍；關掉則每次重畫都回到全部顯示": "Keep the current x zoom when a setting change or Rescan redraws; off = every redraw returns to Show All",
    "回到預設版面（左欄 資料夾、已繪訊號；右邊整個是圖；訊號屬性隱藏）；每個面板的 ▾ 或右鍵標題列可以搬到別欄、排序、最大化、隱藏":
        "Back to the default layout (left: Folder, Plotted Signals; the plot fills the rest; Signal Properties hidden); each panel's ▾ or title-bar right-click moves it to another column, reorders, maximizes or hides it",
    "還沒有圖：先加入訊號": "No plot yet: add signals first", "轉態：還沒有圖，先加入訊號": "Transitions: no plot yet, add signals first",
})

