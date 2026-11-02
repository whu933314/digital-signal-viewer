# -*- coding: utf-8 -*-
"""English catalog part: dsv1 — signal_viewer.py from the top of the file up to class HelpWindow
(module helpers, render(), CsvImportDialog, SpectrumWindow, GfskWindow). Keys are the Traditional Chinese source strings."""
CATALOG = {
    # --- module helpers / data layer ---
    "CSV 沒有欄位 {name!r}": "CSV has no column {name!r}",

    # --- render() ---
    "尚無訊號：在左側「資料夾」面板選檔案，按「加入選取的」，再按 PLOT / REFRESH":
        "No signals yet: pick files in the Folder panel on the left, click \"Add Selected\", then PLOT / REFRESH",
    "所有訊號都已隱藏：在清單的「顯示」欄勾回來": "All signals are hidden: tick them back on in the Show column of the list",
    "P{p}": "P{p}",
    " [{n} spike fixed]": " [{n} spike fixed]",
    "右軸": "Right Axis",

    # --- CsvImportDialog ---
    "匯入 CSV：{name}": "Import CSV: {name}",
    "匯入 CSV": "Import CSV",
    "加入": "Add",
    "欄位名": "Column",
    "套用平移/縮放": "Apply Shift/Scale",
    "突波抑制": "Despike",
    "最小": "Min",
    "最大": "Max",
    "中位數": "Median",
    "建議平移": "Suggested Shift",
    "1. 選欄位": "1. Select Columns",
    "不同值超過 2 種的欄位視為類比欄位，預設勾選平移/縮放與突波抑制。點格子可切換。":
        "Columns with more than 2 distinct values are treated as analog and get shift/scale and despike ticked by default. Click a cell to toggle.",
    "2. 數值與取樣率": "2. Values and Sample Rate",
    "用建議值": "Use Suggested",
    "顯示值 = (原始值 + shift) × scale": "displayed = (raw + shift) × scale",
    "用估計值": "Use Estimate",
    "讀取格式": "Read format",
    "3. 突波抑制參數": "3. Despike Parameters",
    "最長連續突波 k": "Max spike run k",
    "門檻 × 雜訊": "Threshold × noise",
    "最小偏差": "Min deviation",
    "4. 其他選項": "4. Other Options",
    "勾選的欄位合併畫在同一張圖": "Plot ticked columns in one panel",
    "用 Time 欄的起始時間當 offset": "Use the Time column's start time as offset",
    "取消": "Cancel",
    "勾選的欄位沒有可用的建議值。": "None of the ticked columns has a suggested value.",
    "取樣率": "Sample Rate",
    "沒有時間欄或無法估計取樣率。": "No time column, or the sample rate could not be estimated.",
    "（時間欄估計 {est}）": "(time column estimate {est})",
    "→ 空白則用預設 SPS {sps:g}  {hint}": "→ leave blank to use the default SPS {sps:g}  {hint}",
    "請至少勾選一個欄位。": "Tick at least one column.",
    "shift / scale 必須是數字，scale 不可為 0。": "shift / scale must be numbers, and scale cannot be 0.",
    "Sample rate 無法解析：{text}": "Cannot parse sample rate: {text}",
    "突波抑制參數必須是數字。": "Despike parameters must be numbers.",
    "SPS 必須 > 0。": "SPS must be > 0.",
    "加入 CSV 欄位 {key}": "Add CSV column {key}",
    "更新 CSV 欄位 {key}": "Update CSV column {key}",

    # --- SpectrumWindow ---
    "頻譜 — {names}": "Spectrum — {names}",
    "Welch 段數": "Welch segments",
    "去 DC": "Remove DC",
    "分開畫": "Separate panels",
    "頻率用 Hz": "Frequency in Hz",
    "I/Q 複數": "I/Q complex",
    "重新計算": "Recompute",
    "FFT 視窗函數（選了就重算）：hann 通用；rect 不加窗，頻率解析度最高但旁波瓣大":
        "FFT window function (recomputes on change): hann is the general choice; rect applies no window — best frequency resolution but large sidelobes",
    "Welch 平均：把資料切成幾段（1～64）各自算頻譜再平均\n段數越多越平滑、頻率解析度越低；改了按 Enter 或箭頭重算":
        "Welch averaging: split the data into segments (1–64), take each segment's spectrum and average\n"
        "More segments = smoother but coarser frequency resolution; press Enter or the arrows after changing",
    "y 軸用 dB（20·log10）；關掉用線性振幅": "y axis in dB (20·log10); off = linear amplitude",
    "x 軸用對數頻率（只畫 f > 0 的部分）": "Logarithmic frequency axis (only f > 0 is drawn)",
    "算頻譜前先扣掉平均值，不然 0 Hz 會有一根很大的直流": "Subtract the mean before the FFT, otherwise a large DC line appears at 0 Hz",
    "每條訊號各自一張子圖；關掉全部疊在同一張": "One subplot per signal; off = all overlaid in one",
    "x 軸用 Hz（＝cycles/symbol × symbol rate）；關掉用 cycles/symbol": "x axis in Hz (= cycles/symbol × symbol rate); off = cycles/symbol",
    "把這個視窗裡的前 2 條訊號當 I、Q 組成複數 I + jQ 算雙邊頻譜（兩條的 SPS 要相同）":
        "Treat the first 2 signals in this window as I and Q, form I + jQ and compute a two-sided spectrum (both need the same SPS)",
    "用主圖「目前」的 x 範圍與訊號資料重新算一次：主圖縮放／平移、改 symbol rate 或突波抑制後按這裡；資料提示會清掉":
        "Recompute with the main plot's current x range and signal data: click after zooming / panning the main plot or changing symbol rate or despiking; data tips are cleared",
    "x {x0:.6g}..{x1:.6g} symbol": "x {x0:.6g}..{x1:.6g} symbol",
    "全部範圍": "full range",
    "分析範圍＝主圖目前的 x 範圍（{rng}）：在主圖調整範圍（「全部顯示」＝整段資料）後按「重新計算」":
        "Analysis range = the main plot's current x range ({rng}): adjust the range in the main plot (Show All = the whole data), then click Recompute",
    "已計算 {n} 條頻譜；分析範圍 {rng}（＝主圖目前的 x 範圍，主圖縮放後按「重新計算」）":
        "Computed {n} spectra; analysis range {rng} (= the main plot's current x range; click Recompute after zooming the main plot)",
    "I/Q 複數需要至少 2 條訊號": "I/Q complex needs at least 2 signals",
    "I/Q 複數：{a} 與 {b} 的 SPS 不同，略過": "I/Q complex: {a} and {b} have different SPS, skipped",
    "樣本數 {n} < 8": "{n} samples < 8",
    "{name}：樣本數 {n} < 8，略過": "{name}: {n} samples < 8, skipped",
    "沒有資料": "No data",
    "log f 只畫 f > 0 的部分": "log f plots only f > 0",
    "x {x0:.6g}..{x1:.6g} symbol，": "x {x0:.6g}..{x1:.6g} symbol, ",
    "{rng}window={window}，Welch {nseg} 段，symbol rate {sr}": "{rng}window={window}, Welch {nseg} segments, symbol rate {sr}",
    "；": "; ",

    # --- GfskWindow ---
    "GFSK 分析 — {names}": "GFSK Analysis — {names}",
    "GFSK 分析": "GFSK Analysis",
    "中頻（IF）：先把 I/Q 往下混頻到 0 Hz 再鑑頻；可寫 1.77778M、500k 這種寫法，改了按 Enter 重算":
        "Intermediate frequency: the I/Q is mixed down to 0 Hz before discrimination; forms like 1.77778M, 500k; press Enter after changing",
    "混頻後 Gaussian 濾波器的 3 dB 頻寬（BLE 1M 約 500k）；改了按 Enter 重算":
        "3 dB bandwidth of the Gaussian filter after mixing (about 500k for BLE 1M); press Enter after changing",
    "I/Q 順序：鑑頻結果上下顛倒（頻率符號相反）時改成 QI":
        "I/Q order: switch to QI when the discriminator output is upside down (frequency sign inverted)",
    "Gaussian 濾波器的 taps 數（5～129，強制奇數）：越多越陡、暫態越長；改了按 Enter 或箭頭重算":
        "Number of Gaussian filter taps (5–129, forced odd): more = sharper but longer transient; press Enter or the arrows after changing",
    "用主圖「目前」的 x 範圍與訊號資料重新算一次：主圖縮放／平移、改 symbol rate 或 SPS 後按這裡；資料提示會清掉":
        "Recompute with the main plot's current x range and signal data: click after zooming / panning the main plot or changing symbol rate or SPS; data tips are cleared",
    "找不到 I/Q 配對：關掉這個視窗，在清單選取 I、Q 兩條訊號後再按 GFSK…":
        "No I/Q pair found: close this window, select the I and Q signals in the list and click GFSK… again",
    "已計算 {n} 組 I/Q 的鑑頻輸出；分析範圍 {rng}（＝主圖目前的 x 範圍，主圖縮放後按「重新計算」）":
        "Computed the discriminator output of {n} I/Q pairs; analysis range {rng} (= the main plot's current x range; click Recompute after zooming the main plot)",
    "IF 頻率": "IF frequency",
    "3dB 頻寬": "3 dB bandwidth",
    "I/Q 順序": "I/Q order",
    "IF 頻率 / 3dB 頻寬 無法解析（可用 1.77778M、500k 這種寫法）":
        "Cannot parse IF frequency / 3 dB bandwidth (use forms like 1.77778M, 500k)",
    "找不到 I/Q 配對：請讓訊號名稱含 adc i / adc q（或 in_i / in_q、i / q），\n或只選取 2 條訊號。":
        "No I/Q pair found: name the signals with adc i / adc q (or in_i / in_q, i / q),\nor select exactly 2 signals.",
    "{i} 與 {q} 的 SPS 不同，用 {i} 的 fs": "{i} and {q} have different SPS; using the fs of {i}",
    "樣本數 {n} 不足（需要 > taps={taps}）": "Not enough samples ({n}; need > taps={taps})",
    "{i} / {q}   fs={fs}  IF={fc}  BW={bw}  taps={taps}  順序={order}": "{i} / {q}   fs={fs}  IF={fc}  BW={bw}  taps={taps}  order={order}",
    "t [s]（從分析範圍起點算）": "t [s] (from the start of the analysis range)",
    "全部放進視窗": "Fit all in window",
    "版面": "Layout",
    "已收合：{n} 條訊號（{names}）": "Collapsed: {n} signal(s) ({names})",
    "重排 panel": "Reorder panels",
    "重排 panel：{order}": "Reorder panels: {order}",
    "panel 順序：{order}（Ctrl+Z 可復原）": "Panel order: {order} (Ctrl+Z undoes)",
    "P{p} 已經在最上面": "P{p} is already at the top",
    "P{p} 已經在最下面": "P{p} is already at the bottom",
    "P{p} 已收合（雙擊矮列或它左邊的標題區可展開；右鍵標題區也有「展開」）": "P{p} collapsed (double-click the thin bar or the title area to its left to expand it; the title area's right-click menu has \"Expand\" too)",
    "P{p} 已展開": "P{p} expanded",
    "隱藏 P{p}": "Hide P{p}",
    "隱藏 P{p} 的 {n} 條訊號": "Hide the {n} signal(s) of P{p}",
    "已隱藏 P{p} 的 {n} 條訊號（清單的「顯示」欄可勾回來；Ctrl+Z 可復原）": "Hid the {n} signal(s) of P{p} (tick them again in the list's Show column; Ctrl+Z undoes)",
    "隱藏這張圖的訊號": "Hide This Panel's Signals",
    "拖曳換上下順序；雙擊收合／展開": "Drag to reorder panels; double-click to collapse / expand",
    "panel 選單：上移、下移、收合、隱藏、貼上": "Panel menu: move up / down, collapse, hide, paste",
    "展開 P{p}": "Expand P{p}",
    "收合 P{p}（只留標題列）": "Collapse P{p} (title bar only)",
    "（{n} 條，已收合）": " ({n} signals, collapsed)",
    "預設版面": "Default Layout",
    "回到 MATLAB 桌面式的三欄版面；每個面板的 ▾ 或右鍵標題列可以搬到別欄、排序、最大化、隱藏":
        "Back to the MATLAB-desktop three-column layout; each panel's ▾ (or right-click on its title bar) can move it to another column, reorder, maximize or hide it",
    "只看圖": "Plot Only",
    "圖最大化（雙擊面板標題列也可以）；再按一次還原": "Maximize the plot (double-clicking a panel title bar also works); press again to restore",
    "顯示／隱藏這個面板": "Show / hide this panel",
    "畫布放得下時滾輪縮放；放不下時滾輪捲動、⌘/Ctrl+滾輪才縮放。Shift 只縮 x、⌘/Ctrl+Shift 只縮 y、Option/Alt 捲動":
        "When the plot fits, the wheel zooms; when it does not, the wheel scrolls and ⌘/Ctrl+wheel zooms. Shift zooms x only, ⌘/Ctrl+Shift zooms y only, Option/Alt scrolls",
    "把所有 panel 塞進可見高度（每張至少 0.5 in），不用捲動；關掉就照左邊的高度、超出時可捲動":
        "Fit every panel into the visible height (at least 0.5 in each) so nothing needs scrolling; when off, panels use the height on the left and the plot scrolls when taller than the window",
}
