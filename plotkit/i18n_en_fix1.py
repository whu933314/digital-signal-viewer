# -*- coding: utf-8 -*-
"""English catalog part: fix1 — the 2026-10-24 user-reported fixes (Pan as the default plot-toolbar mode, the merged
AM/PM/FM analysis window, constellation "First N" / "Last N", drop targets for all three drag sources, "Delete this signal"
in the line context menu).  Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    # merged AM/PM/FM window (one toolstrip button, one list item, one action)
    "AM/PM/FM 分析": "AM/PM/FM Analysis",
    "AM/PM/FM 分析…": "AM/PM/FM Analysis…",
    "勾要看的項目（AM／PM／FM 任意組合，各一張子圖）；下次開這個視窗沿用":
        "Tick what to show (any combination of AM / PM / FM, one subplot each); remembered for the next time this window opens",
    "開 AM/PM/FM 分析視窗：每組 I/Q 配對算 AM＝幅度 |I+jQ|、PM＝相位 ∠(I+jQ)（度，可展開）、\nFM＝瞬時頻率（Hz）＝相鄰樣本的相位差 × fs/2π，fs = SPS × symbol rate（不混頻、不濾波；要 IF 與 Gaussian 濾波用 GFSK…）。\n視窗裡勾要看的項目，各一張子圖、x 軸秒。需要 I、Q 兩條訊號——選取 2 條，或讓名稱含 adc i／adc q 自動配對（沒有選取時從全部訊號找）。\n「複製訊號」→ 主圖點 panel 按 ⌘V，或直接把線拖到主圖，貼成跟著來源更新的衍生訊號":
        "Open the AM/PM/FM analysis window: for each I/Q pair, AM = magnitude |I+jQ|, PM = phase ∠(I+jQ) (degrees, optionally unwrapped),\n"
        "FM = instantaneous frequency (Hz) = phase difference between neighbouring samples × fs/2π, fs = SPS × symbol rate (no mixing, no filtering; use GFSK… for IF and Gaussian filtering).\n"
        "Tick what to show in the window, one subplot each, x axis in seconds. Needs an I and a Q signal: select 2, or name them adc i / adc q to pair automatically (with no selection, all signals are searched).\n"
        "\"Copy Signals\" → click a panel in the main plot and press ⌘V, or drag a line straight onto the main plot, to paste derived signals that follow their sources",
    # constellation: Symbols = All / Last N / First N, N greyed when All
    "前 N 個": "First N",
    "Symbols to display：全部（上限 {max:,} 點）、只畫最後 N 個或前 N 個符號（N 在右邊的數字格）":
        "Symbols to display: all (up to {max:,} points), only the last N or only the first N symbols (N in the box to the right)",
    "「最後 N 個」「前 N 個」的 N（MATLAB SymbolsToDisplay，預設 256）；改了按 Enter、箭頭或「重新計算」；「全部」時用不到（灰）":
        "N for \"Last N\" / \"First N\" (MATLAB SymbolsToDisplay, default 256); press Enter, use the arrows or \"Recompute\"; unused (greyed) for \"All\"",
    "用主圖「目前」的 x 範圍與訊號資料重新畫：主圖縮放／平移、改 SPS、Offset、N 或 shift 後按這裡；標題的符號數跟著變、資料提示會清掉":
        "Redraw from the main plot's current x range and signal data: press after zooming / panning the main plot or changing SPS, Offset, N or shift; the symbol count in the title follows, data tips are cleared",
    # line context menu
    "刪除這條訊號（{name}）": "Delete this signal ({name})",
    "這條訊號已經不在清單裡": "This signal is no longer in the list",
    # drop targets (files from Finder, the Folder panel, lines from the I/Q window)
    "放開以加到 P{p}（放在最後一張圖下面的空白＝新增 panel）": "Release to add to P{p} (the blank area below the last panel = new panel)",
    "放開以新增 P{p}（放在某張圖上＝加進那張圖）": "Release to create P{p} (drop on a panel = add to that panel)",
    "拖到主圖的某張圖上（貼進那張圖）或最後一張圖下面的空白（新增 panel）放開才會貼上":
        "Release over a panel of the main plot (paste into it) or over the blank area below the last panel (new panel) to paste",
    "拖到圖上放開：放在某張圖＝加進那張圖、最後一張圖下面的空白＝新增 panel（放在別處＝取消）":
        "Release over the plot: on a panel = add to that panel, on the blank area below the last panel = new panel (anywhere else = cancel)",
    "拖曳加入": "Drag to add",
    "拖曳加入 {n} 條訊號到 {panels}（Ctrl+Z 可復原）": "Dragged {n} signal(s) into {panels} (Ctrl+Z undoes)",
    "拖過來的檔案已經畫在 {panels}（已選取）": "The dragged files are already plotted in {panels} (selected)",
    "沒有放在圖上，取消拖曳": "Not released over the plot; drag cancelled",
}
