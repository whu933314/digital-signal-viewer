# -*- coding: utf-8 -*-
"""English catalog part: batch 2 of the 2026-10-23 MATLAB tools — the spectrum window rebuilt as MATLAB's Spectrum Analyzer
(Scope / Estimation / Measurements tabs, contextual Spectrum / Spectrogram tabs), RBW / window length / FFT length / window /
attenuation / overlap, two-sided spectrum, normal / max-hold / min-hold traces, spectrogram, spectrum peak finder.
Keys are the Traditional Chinese source strings, byte for byte. Names follow the strings MATLAB R2025a
shows in the Spectrum Analyzer interface.
"""
CATALOG = {
    # 分頁與區段（MATLAB 的 SCOPE／ESTIMATION／SPECTRUM／SPECTROGRAM 與各 section）
    "示波器": "Scope",
    "估計": "Estimation",
    "頻譜圖": "Spectrogram",
    "檢視": "Views",
    "頻寬": "Bandwidth",
    "設定": "Configuration",
    "資料": "Data",
    "頻率解析度": "Frequency Resolution",
    "視窗選項": "Window Options",
    "軌跡選項": "Trace Options",
    "刻度": "Scale",
    "通道": "Channel",
    "時間選項": "Time Options",
    # 標籤
    "取樣率 (Hz)": "Sample Rate (Hz)",
    "偏移 (Hz)": "Offset (Hz)",
    "設定…": "Settings…",
    "色彩列": "Colorbar",
    "版面配置": "Layout",
    "垂直": "Vertical",
    "水平": "Horizontal",
    "估計方法": "Estimation Method",
    "解析度方法": "Resolution Method",
    "RBW": "RBW",
    "視窗長度": "Window Length",
    "FFT 長度": "FFT Length",
    "視窗": "Window",
    "衰減 (dB)": "Attenuation (dB)",
    "重疊 (%)": "Overlap (%)",
    "雙邊頻譜": "Two-Sided Spectrum",
    "一般軌跡": "Normal Trace",
    "最大值保持軌跡": "Max-Hold Trace",
    "最小值保持軌跡": "Min-Hold Trace",
    "頻率刻度": "Frequency Scale",
    "線性": "Linear",
    "對數": "Log",
    "參考負載 (Ω)": "Reference Load (Ω)",
    "頻譜單位": "Spectrum Unit",
    "滿刻度": "Full Scale",
    "時間解析度 (s)": "Time Resolution (s)",
    "時間解析度 (symbol)": "Time Resolution (symbol)",
    "時間跨度 (s)": "Time Span (s)",
    "時間跨度 (symbol)": "Time Span (symbol)",
    "重新指派": "Reassign",
    "頻譜設定": "Spectrum Settings",
    "色彩範圍": "Color Limits",
    "色彩圖": "Color Map",
    "依資料自動": "Scale to Data",
    "值": "Value",
    # 資訊列、標題
    "Window = {w}，RBW {rbw}，{navg} 段平均": "Window = {w}, RBW {rbw}, {navg} averages",
    "視窗長度 = {v}": "Window Length = {v}",
    "重疊 = {v}%": "Overlap = {v}%",
    "時間解析度 = {v}（{n} 條線、線距 {d}{k}{r}）": "Time Resolution = {v} ({n} lines, spacing {d}{k}{r})",
    "，每條 {k} 段": ", {k} segments per line",
    "，重新指派": ", reassigned",
    # 說明（tooltip）
    "改了按 Enter 重算": "press Enter to recompute",
    "檢視訊號的頻譜（MATLAB Spectrum Analyzer 的 Spectrum 檢視）": "View the frequency spectrum of the signals (MATLAB Spectrum Analyzer Spectrum view)",
    "檢視一條訊號的頻譜圖：橫軸頻率、縱軸時間，顏色是功率（MATLAB 的 Spectrogram 檢視）；\n兩個都開＝頻譜和頻譜圖一起看":
        "View the spectrogram of one signal: frequency across, time up, colour is power (MATLAB Spectrogram view);\nturn both on to see the spectrum and the spectrogram together",
    "MATLAB Spectrum Analyzer 的 Spectrum type：\n振幅（DSV 預設）：單音振幅 A 讀 A；功率：單音讀 A²/2（每個 bin 的功率）；\n功率密度：除以 RBW（dB/Hz，白雜訊讀 2σ²/fs）；RMS：√功率（Vrms，單音讀 A/√2）":
        "MATLAB Spectrum Analyzer Spectrum type:\nMagnitude (DSV default): a tone of amplitude A reads A; Power: a tone reads A²/2 (power per bin);\nPower Density: divided by RBW (dB/Hz, white noise reads 2σ²/fs); RMS: √power (Vrms, a tone reads A/√2)",
    "輸入訊號的取樣率（繼承自訊號：SPS × symbol rate，到主畫面改）": "Sample rate of the input signals (inherited: SPS × symbol rate; change it in the main window)",
    "頻率偏移（Hz）：加到頻率軸上，例如基頻 I/Q 加上載波頻率；{enter}": "Frequency offset (Hz) added to the frequency axis, e.g. the carrier frequency for baseband I/Q; {enter}",
    "頻譜圖的色彩範圍與色彩圖（MATLAB 的 Settings）": "Spectrogram color limits and colormap (MATLAB Settings)",
    "顯示圖例（訊號名稱；MATLAB 預設關）": "Show the legend (signal names; off by default in MATLAB)",
    "頻譜圖旁邊顯示色彩列": "Show the colorbar next to the spectrogram",
    "頻譜和頻譜圖一起看時：垂直＝頻譜在上、頻譜圖在下；水平＝左右並排": "When both views are shown: Vertical stacks the spectrum above the spectrogram; Horizontal puts them side by side",
    "每一段算頻譜前先扣掉平均值，不然 0 Hz 會有一根很大的直流（DSV 才有；MATLAB 不扣）":
        "Subtract each segment's mean before the FFT, otherwise 0 Hz shows a large DC spike (DSV only; MATLAB does not)",
    "頻率用 Hz、時間用秒（＝cycles/symbol × symbol rate）；關掉用 cycles/symbol 與 symbol":
        "Frequency in Hz and time in seconds (= cycles/symbol × symbol rate); off: cycles/symbol and symbols",
    "把這個視窗裡的前 2 條訊號當 I、Q 組成複數 I + jQ（雙邊頻譜；兩條的 SPS 要相同）":
        "Combine the first 2 signals of this window into the complex I + jQ (two-sided spectrum; both need the same SPS)",
    "頻譜估計方法：Welch（MATLAB 另有 Filter bank，DSV 沒有做）": "Spectrum estimation method: Welch (MATLAB also has Filter bank, which DSV does not implement)",
    "頻率解析度怎麼決定：RBW＝給解析頻寬，視窗長度自動算；視窗長度＝直接給每段幾點":
        "How the frequency resolution is set: RBW = give the resolution bandwidth and the window length follows; Window length = samples per segment",
    "解析頻寬（Hz）；Auto＝頻寬裡放 1024 個 RBW（雙邊 fs/1024、單邊 fs/2048）。可寫 10k、1.5M；{enter}":
        "Resolution bandwidth (Hz); Auto = 1024 RBW intervals over the span (two-sided fs/1024, one-sided fs/2048). You can type 10k or 1.5M; {enter}",
    "每段的樣本數（解析度方法選「視窗長度」時用）；{enter}": "Samples per segment (used when Resolution Method is Window length); {enter}",
    "FFT 點數；Auto＝視窗長度，最少 1024（MATLAB 分析器實測）。比視窗短時把加窗後的資料折疊相加，比視窗長時補零；{enter}":
        "Number of FFT points; Auto = window length, at least 1024 (measured on the MATLAB analyzer). Shorter than the window: the windowed data is wrapped; longer: zero-padded; {enter}",
    "算頻譜用的視窗：Hann（預設）、Hamming、Flat Top（振幅最準）、Blackman-Harris、Chebyshev 與 Kaiser（旁波瓣衰減可調）、Rectangular（不加窗）":
        "Window for the spectral estimate: Hann (default), Hamming, Flat Top (most accurate amplitude), Blackman-Harris, Chebyshev and Kaiser "
        "(adjustable sidelobe attenuation), Rectangular (no window)",
    "視窗的旁波瓣衰減（dB，≥ 45；Chebyshev 與 Kaiser 才用得到）；{enter}": "Window sidelobe attenuation (dB, ≥ 45; Chebyshev and Kaiser only); {enter}",
    "相鄰兩段重疊的百分比（0～100，不含 100；MATLAB 預設 0）；{enter}或按箭頭": "Overlap between neighbouring segments in percent (0 to below 100; MATLAB default 0); {enter} or use the arrows",
    "Peak Finder：在目前看得到的頻率範圍內找最高的 Num Peaks 個峰（MATLAB findpeaks），下方面板列出值與頻率，圖上用 ▼ 標出":
        "Peak Finder: find the Num Peaks highest peaks in the visible frequency range (MATLAB findpeaks); the panel below lists value and frequency, ▼ marks them",
    "最多列出幾個峰（1～99）；{enter}": "Maximum number of peaks to show (1 to 99); {enter}",
    "峰值要比左右鄰點都高至少這麼多（≥ 0；y 軸是 dB 類時單位是 dB，線性時和 y 軸同單位）；{enter}":
        "Minimum height difference between a peak and its neighbours (≥ 0; in dB when the y axis is in dB units, otherwise in y-axis units); {enter}",
    "比這個高的才算峰（空白＝不限）；{enter}": "Level above which peaks are detected (blank = no limit); {enter}",
    "相鄰峰之間至少隔幾個頻率點（≥ 1 的整數；Inf＝只留最高的峰）；{enter}":
        "Minimum number of frequency bins between adjacent peaks (an integer ≥ 1; Inf = only the highest peak); {enter}",
    "在 ▼ 上面寫 P1、P2…": "Write P1, P2, … above the ▼ markers",
    "顯示雙邊頻譜（−fs/2～fs/2，MATLAB 預設）；關掉＝單邊 0～fs/2（只能用在實數訊號，振幅是雙邊的兩倍）":
        "Show the two-sided spectrum (−fs/2 to fs/2, MATLAB default); off = one-sided 0 to fs/2 (real signals only; amplitudes are twice the two-sided ones)",
    "範圍內所有段的平均頻譜": "Average spectrum of all segments in the range",
    "每個頻率在所有段裡的最大值（同顏色、透明度 0.7）": "Maximum over all segments at each frequency (same colour, opacity 0.7)",
    "每個頻率在所有段裡的最小值（同顏色、透明度 0.5）": "Minimum over all segments at each frequency (same colour, opacity 0.5)",
    "頻譜圖畫哪一條訊號": "Signal shown in the spectrogram",
    "每一條頻譜圖線的時間解析度；Auto＝1/RBW。RBW 是 Auto 時，指定的時間解析度會決定 RBW（＝1/時間解析度）；\n兩個都指定時要 ≥ 1/RBW，幾段合成一條線。可寫 1ms、20us；{enter}":
        "Time resolution of each spectrogram line; Auto = 1/RBW. With RBW on Auto, a specified time resolution sets RBW (= 1/time resolution);\n"
        "with both specified it must be ≥ 1/RBW and several segments are combined into one line. You can type 1ms or 20us; {enter}",
    "頻譜圖顯示的時間長度（最後這麼長）；Auto＝整個分析範圍。要至少是一次更新所需時間的 2 倍；{enter}":
        "Time span shown in the spectrogram (the last part of the range); Auto = the whole analysis range. Must be at least twice the duration of one update; {enter}",
    "顯示雙邊頻譜（−fs/2～fs/2）；關掉＝單邊（只能用在實數訊號）": "Show the two-sided spectrum (−fs/2 to fs/2); off = one-sided (real signals only)",
    "把每一格的能量搬到它的時間與頻率重心，讓頻譜圖更銳利（MATLAB Signal Analyzer 的 Reassign；spectrogram(…,'reassigned')）":
        "Move each cell's energy to its centre of gravity in time and frequency for a sharper spectrogram (MATLAB Signal Analyzer Reassign; spectrogram(…,'reassigned'))",
    "頻率軸線性或對數；對數只能用在單邊頻譜（MATLAB：Log-scale is only valid for one-sided spectrum displays）":
        "Linear or logarithmic frequency axis; log scale is only valid for one-sided spectrum displays (MATLAB)",
    "dBm 與 W 的參考負載（Ω，預設 1）：功率 = V² / R；{enter}": "Reference load for dBm and W (Ω, default 1): power = V² / R; {enter}",
    "dB＝相對（20·log10 振幅或 10·log10 功率；RMS 是 dBV）；\ndBFS＝相對滿刻度：振幅等於滿刻度的單音讀 0 dBFS；\ndBm＝功率 / 參考負載 / 1 mW；線性＝振幅、W、W/Hz 或 Vrms（依頻譜類型）":
        "dB = relative (20·log10 amplitude or 10·log10 power; RMS is dBV);\ndBFS = relative to full scale: a tone with amplitude equal to Full Scale reads 0 dBFS;\n"
        "dBm = power / reference load / 1 mW; Linear = amplitude, W, W/Hz or Vrms (by spectrum type)",
    "dBFS 的滿刻度（振幅）；Auto＝由資料猜 ADC 位元數（無號 offset binary → 2^(b−1)、有號整數 → 2^(b−1)、±1 浮點 → 1）；{enter}":
        "Full scale for dBFS (amplitude); Auto = guess the ADC bits from the data (unsigned offset binary → 2^(b−1), signed integers → 2^(b−1), ±1 float → 1); {enter}",
    "色彩列的最小與最大值 [cmin cmax]（和頻譜單位相同；MATLAB 預設 [-80 20]）": "Colorbar minimum and maximum [cmin cmax] (spectrum units; MATLAB default [-80 20])",
    "用目前頻譜圖的資料決定色彩範圍（最大值往下 100 dB；MATLAB Signal Analyzer 的 Scale Color）":
        "Set the color limits from the current spectrogram data (maximum down to 100 dB below; MATLAB Signal Analyzer Scale Color)",
    "頻譜圖的色彩對照表（MATLAB 預設 jet）": "Spectrogram colormap (MATLAB default jet)",
    # 訊息
    "RBW 太大：頻寬／RBW 要大於 2（頻寬 {span}、RBW {rbw}）": "RBW too large: span / RBW must be greater than 2 (span {span}, RBW {rbw})",
    "範圍內只有 {n} 點，不夠一段視窗（{L} 點）：把主圖範圍放大，或加大 RBW／縮短視窗長度":
        "Only {n} samples in the range, fewer than one window ({L} samples): widen the main plot range, or increase RBW / shorten the window",
    "{name}：範圍內不到一段": "{name}: less than one segment in the range",
    "{name}：範圍只有 {n} 點，比 RBW Auto 要的視窗短，改用整段當一個視窗":
        "{name}: only {n} samples in the range, shorter than the window RBW Auto needs; using the whole range as one window",
    "對數頻率刻度只能用在單邊頻譜：改用線性（關掉「雙邊頻譜」才能用對數）":
        "The log frequency scale is only valid for a one-sided spectrum: using linear (turn off Two-Sided Spectrum to use log)",
}
