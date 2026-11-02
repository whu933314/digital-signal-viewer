# -*- coding: utf-8 -*-
"""English catalog part: fix2 — the 2026-10-25 user-reported items 8 and 9: every panel has its own x axis, x unit,
symbol rate and y unit with MATLAB Signal Analyzer's "Link Time" per panel (on by default), and the I/Q analyses
(AM/PM/FM, Constellation, GFSK) work on the current panel (click a panel to make it current; it gets a frame).
Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    # current panel and its Axes settings (toolstrip "Axes" section, Signal Properties → View / Diff, panel right-click)
    "目前 P{p}": "Current P{p}",
    "目前 panel：—": "Current panel: —",
    "目前 panel：P{p}（AM/PM/FM、星座圖、GFSK、眼圖、錯誤率比對與「座標」的設定都對這張）":
        "Current panel: P{p} (AM/PM/FM, Constellation, GFSK, Eye Diagram, Error Rate and the Axes settings apply to it)",
    "y 軸單位": "y-axis unit",
    "連結時間": "Link Time",
    "連結時間（目前 panel）": "Link Time (current panel)",
    "連結時間（和其他連結的 panel 一起縮放平移）": "Link Time (zoom and pan together with the other linked panels)",
    "這一區改的是「目前 panel」（點 panel 選定，圖上有框）：x 軸單位、Symbol rate、y 軸單位、連結時間每個 panel 各自設。\npanel 右鍵 → 座標 也可以改，還有「x 單位與 Symbol rate 套用到所有 panel」；新 panel 沿用目前 panel 的 x 單位與 Symbol rate":
        "This section edits the current panel (click a panel to make it current; it gets a frame): x-axis unit, symbol rate, "
        "y-axis unit and Link Time are set per panel.\nA panel's right-click → Axes changes them too and has \"Apply X Unit and "
        "Symbol Rate to All Panels\"; a new panel takes the current panel's x unit and symbol rate",
    "連結時間（MATLAB Signal Analyzer 的 Link Time，預設勾）：勾著的 panel 一起縮放平移、同一段時間"
    "（Symbol rate 不同的會換算）；取消就只有這個 panel 自己縮放平移（Ctrl+U／⌘U）":
        "Link Time (MATLAB Signal Analyzer's Link Time, on by default): linked panels zoom and pan together over the same time span "
        "(different symbol rates are converted); turn it off and only this panel zooms and pans (Ctrl+U / ⌘U)",
    "座標（P{p}）": "Axes (P{p})",
    "x 軸單位：{u}": "x-axis unit: {u}",
    "Symbol rate…（目前 {r}）": "Symbol rate… (now {r})",
    "y 軸單位…（目前 {u}）": "y-axis unit… (now {u})",
    "x 單位與 Symbol rate 套用到所有 panel": "Apply X Unit and Symbol Rate to All Panels",
    "P{p} 的 Symbol rate": "Symbol rate of P{p}",
    "Symbol rate（例如 1M、2e6）：": "Symbol rate (e.g. 1M, 2e6):",
    "Symbol rate 要是正數（例如 1M、2e6）：{text}": "The symbol rate must be a positive number (e.g. 1M, 2e6): {text}",
    "P{p} 的 y 軸單位": "y-axis unit of P{p}",
    "y 軸單位（例如 V、LSB；空白＝不標）：": "y-axis unit (e.g. V, LSB; blank = none):",
    "P{p} {what}：{v}": "P{p} {what}: {v}",
    "P{p} 的{what}：{v}": "P{p} {what}: {v}",
    "（空白）": "(blank)",
    "（跟其他連結的 panel 一起縮放平移）": " (zooms and pans with the other linked panels)",
    "（這個 panel 自己縮放平移）": " (this panel zooms and pans on its own)",
    "沒有 panel：先加入訊號": "No panel: add signals first",
    "x 單位與 Symbol rate 套用到所有 panel：{u}、{r}": "X unit and symbol rate applied to all panels: {u}, {r}",
    "所有 panel 的 x 軸單位＝{u}、Symbol rate＝{r}（照 P{p}）": "All panels: x-axis unit = {u}, symbol rate = {r} (from P{p})",
    "x 範圍 {a:g}..{b:g}（P{p}）": "x range {a:g}..{b:g} (P{p})",
    "fs={fs}（{n} 條，SPS 照各自 panel 的 Symbol rate）": "fs={fs} ({n} signals, SPS from each panel's symbol rate)",
    "範圍：每條訊號用它所在 panel 的範圍（{src}；各 panel 的 x 不同步）":
        "Range: each signal uses its own panel's range ({src}; the panels' x axes are not linked)",
    # I/Q analyses on the current panel (item 9)
    "{what}：圖上沒有 panel（訊號都隱藏了？）": "{what}: there is no panel on the plot (are all signals hidden?)",
    "沒有一般訊號": "no regular signals",
    "{what}：P{p} 找不到 I/Q 配對（P{p} 有：{names}）——點有 I、Q 兩條的 panel（目前 panel 有框），"
    "或在清單選 I、Q 兩條":
        "{what}: no I/Q pair in P{p} (P{p} has: {names}) — click a panel that has both I and Q (the current panel has a frame), "
        "or select I and Q in the list",
    "清單選取（{where}）": "list selection ({where})",
    "{base} — {where}：I＝{i}、Q＝{q}": "{base} — {where}: I = {i}, Q = {q}",
    "GFSK 分析": "GFSK Analysis",
    "開啟 GFSK 視窗（{where}）": "Open GFSK window ({where})",
    "已開啟 GFSK 視窗：{where}，I＝{i}、Q＝{q}": "GFSK window opened: {where}, I = {i}, Q = {q}",
    "開啟 {what} 視窗（{where}）": "Open {what} window ({where})",
    "已開啟 {what}：{where}，I＝{i}、Q＝{q}": "{what} opened: {where}, I = {i}, Q = {q}",
    "開啟星座圖視窗（{where}）": "Open constellation window ({where})",
    "已開啟星座圖視窗：{where}，I＝{i}、Q＝{q}": "Constellation window opened: {where}, I = {i}, Q = {q}",
    "選取的兩條": "the 2 selected",
    "{base}（{where}）…": "{base} ({where})…",
    "AM/PM/FM 分析（P{p}）…": "AM/PM/FM Analysis (P{p})…",
    "星座圖（P{p}）…": "Constellation (P{p})…",
    "GFSK（P{p}）…": "GFSK (P{p})…",
    "開 GFSK 鑑頻視窗：分析「目前 panel」（點 panel 選定，圖上有框）裡的 I、Q 兩條（名稱含 adc i／adc q、i／q 自動配對），\n"
    "或在清單選 I、Q 兩條；panel 右鍵也有「GFSK（P1）」；fs = SPS × 那個 panel 的 symbol rate，x 軸秒、y 軸 Hz":
        "Open the GFSK discriminator window: analyzes the I and Q of the current panel (click a panel to make it current; it gets a frame; "
        "names like adc i / adc q or i / q pair automatically),\nor the I and Q you select in the list; a panel's right-click menu has "
        "\"GFSK (P1)\" too; fs = SPS × that panel's symbol rate, x in seconds, y in Hz",
    "開星座圖視窗（MATLAB Constellation Diagram／scatterplot）：I 對 Q 的散佈圖，每 Samples per symbol 取一點。\n"
    "分析「目前 panel」（點 panel 選定，圖上有框）裡的 I、Q 兩條，或在清單選 I、Q 兩條；panel 右鍵也有「星座圖（P1）」；\n"
    "可調 Offset、只畫最後 N 個符號、只用目前 x 範圍、等比例軸、參考星座（RMS EVM）":
        "Open the Constellation Diagram window (MATLAB Constellation Diagram / scatterplot): I versus Q, one point every Samples per symbol.\n"
        "Analyzes the I and Q of the current panel (click a panel to make it current; it gets a frame), or the I and Q you select in the list; "
        "a panel's right-click menu has \"Constellation (P1)\" too;\nOffset, last N symbols only, current x range only, equal axes and a "
        "reference constellation (RMS EVM) are adjustable",
    "開 AM/PM/FM 分析視窗：每組 I/Q 配對算 AM＝幅度 |I+jQ|、PM＝相位 ∠(I+jQ)（度，可展開）、\n"
    "FM＝瞬時頻率（Hz）＝相鄰樣本的相位差 × fs/2π，fs = SPS × symbol rate（不混頻、不濾波；要 IF 與 Gaussian 濾波用 GFSK…）。\n"
    "視窗裡勾要看的項目，各一張子圖、x 軸秒。分析「目前 panel」（點 panel 選定，圖上有框）裡的 I、Q 兩條，或在清單選 I、Q 兩條；\n"
    "panel 右鍵也有「AM/PM/FM 分析（P1）」。視窗標題寫出分析的是哪個 panel、哪兩條。\n"
    "「複製訊號」→ 主圖點 panel 按 ⌘V，或直接把線拖到主圖，貼成跟著來源更新的衍生訊號":
        "Open the AM/PM/FM analysis window: for each I/Q pair, AM = magnitude |I+jQ|, PM = phase ∠(I+jQ) (degrees, optionally unwrapped),\n"
        "FM = instantaneous frequency (Hz) = phase difference between neighbouring samples × fs/2π, fs = SPS × symbol rate (no mixing, "
        "no filtering; use GFSK… for IF and Gaussian filtering).\nTick what to show in the window, one subplot each, x axis in seconds. "
        "Analyzes the I and Q of the current panel (click a panel to make it current; it gets a frame), or the I and Q you select in the list;\n"
        "a panel's right-click menu has \"AM/PM/FM Analysis (P1)\" too. The window title says which panel and which two signals.\n"
        "\"Copy Signals\" → click a panel in the main plot and press ⌘V, or drag a line straight onto the main plot, to paste derived "
        "signals that follow their sources",
}
