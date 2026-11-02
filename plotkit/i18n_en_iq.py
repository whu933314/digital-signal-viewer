# -*- coding: utf-8 -*-
"""English catalog part: iq — the AM/PM/FM analysis window (Analyze → AM/PM Analysis…, FM Analysis…) and the merged
analysis-window section.  Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    "AM/PM 分析…": "AM/PM Analysis…",
    "FM 分析…": "FM Analysis…",
    "AM/PM 分析": "AM/PM Analysis",
    "FM 分析": "FM Analysis",
    "開 AM/PM 分析視窗：每組 I/Q 配對算幅度 |I+jQ| 與相位 ∠(I+jQ)（度，可展開）各一張子圖，x 軸秒。\n需要 I、Q 兩條訊號——選取 2 條，或讓名稱含 adc i／adc q 自動配對（沒有選取時從全部訊號找）。\n視窗裡「複製訊號」→ 主圖點 panel 按 ⌘V 貼成衍生訊號（跟著來源更新）":
        "Open the AM/PM analysis window: for each I/Q pair, magnitude |I+jQ| and phase ∠(I+jQ) (degrees, optionally unwrapped) in their own subplots, x axis in seconds.\n"
        "Needs an I and a Q signal: select 2, or name them adc i / adc q to pair automatically (with no selection, all signals are searched).\n"
        "\"Copy Signals\" in the window → click a panel in the main plot and press ⌘V to paste them as derived signals (they follow their sources)",
    "開 FM 分析視窗：每組 I/Q 配對算瞬時頻率（Hz）＝相鄰樣本的相位差 × fs/2π，fs = SPS × symbol rate；\n不混頻、不濾波（要 IF 與 Gaussian 濾波用 GFSK…）。需要 I、Q 兩條訊號；視窗裡也能勾 AM／PM。\n「複製訊號」→ 主圖點 panel 按 ⌘V 貼成衍生訊號（跟著來源與 symbol rate 更新）":
        "Open the FM analysis window: for each I/Q pair, the instantaneous frequency (Hz) = phase difference between neighbouring samples × fs/2π, fs = SPS × symbol rate;\n"
        "no mixing, no filtering (use GFSK… for IF and Gaussian filtering). Needs an I and a Q signal; AM / PM can be ticked in the window too.\n"
        "\"Copy Signals\" → click a panel in the main plot and press ⌘V to paste them as derived signals (they follow their sources and the symbol rate)",
    "{what}：沒有訊號。先在「資料夾」面板把檔案加進已繪訊號": "{what}: no signals. Add files from the Folder panel first",
    "{what0}：找不到 I/Q 配對（{what}）——請選取 I、Q 兩條訊號，或讓名稱含 adc i／adc q":
        "{what0}: no I/Q pair found ({what}) — select the I and Q signals, or name them adc i / adc q",
    "開啟 {what} 視窗": "Open {what} window",
    "已開啟 {what} 視窗：{n} 組 I/Q（{pairs}）": "Opened the {what} window: {n} I/Q pair(s) ({pairs})",
    "AM：幅度 |I + jQ|": "AM: magnitude |I + jQ|",
    "PM：相位 ∠(I + jQ)，度（−180..180；勾「相位展開」就連續）": "PM: phase ∠(I + jQ) in degrees (−180..180; tick \"Unwrap Phase\" for a continuous angle)",
    "FM：瞬時頻率（Hz）＝相鄰樣本的相位差 × fs / 2π，fs = SPS × symbol rate。\n不混頻、不濾波（要 IF 與 Gaussian 濾波用 GFSK 視窗）；第一個樣本沒有前一點，是空的":
        "FM: instantaneous frequency (Hz) = phase difference between neighbouring samples × fs / 2π, fs = SPS × symbol rate.\n"
        "No mixing, no filtering (use the GFSK window for IF and Gaussian filtering); the first sample has no predecessor and is empty",
    "PM 用 unwrap 展開成連續的角度（不在 ±180° 跳回）；複製出去的相位訊號也照這個": "Unwrap PM into a continuous angle (no jumps at ±180°); copied phase signals follow this too",
    "I/Q 順序：PM／FM 符號相反（上下顛倒）時改成 QI": "I/Q order: switch to QI when PM / FM come out with the opposite sign (upside down)",
    "用主圖「目前」的 x 範圍與訊號資料重新算一次：主圖縮放／平移、改 symbol rate、SPS 或突波抑制後按這裡；資料提示會清掉":
        "Recompute from the main plot's current x range and signal data: press after zooming / panning the main plot or changing the symbol rate, SPS or despike; data tips are cleared",
    "複製訊號": "Copy Signals",
    "把這裡的全部訊號當衍生訊號放進剪貼簿（⌘C／Ctrl+C 也可以）：到主圖點一個 panel 按 ⌘V 貼上，\n貼進去的跟著來源 I/Q 更新（改 shift／scale／突波抑制會重算）；在圖片視窗按 ⌘V 則是疊圖":
        "Put every signal shown here on the clipboard as derived signals (⌘C / Ctrl+C works too): click a panel in the main plot and press ⌘V to paste;\n"
        "the pasted signals follow their I/Q sources (shift / scale / despike changes recompute them); ⌘V in a figure window overlays them instead",
    "找不到 I/Q 配對：關掉這個視窗，在清單選取 I、Q 兩條訊號後再開": "No I/Q pair found: close this window, select the I and Q signals in the list and open it again",
    "勾選 AM／PM／FM 至少一項": "Tick at least one of AM / PM / FM",
    "樣本數 {n} 不足": "Not enough samples ({n})",
    "{label}   fs={fs}": "{label}   fs={fs}",
    "已算出 {n} 條（{kinds}）；分析範圍 {rng}；「複製訊號」或 ⌘C 把它們貼到主圖 panel":
        "Computed {n} signal(s) ({kinds}); analysis range {rng}; \"Copy Signals\" or ⌘C to paste them into a main-plot panel",
    "沒有可複製的訊號：先勾 AM／PM／FM 並算出來": "Nothing to copy: tick AM / PM / FM and compute first",
    "I/Q 分析視窗：複製 {n} 條衍生訊號": "I/Q analysis window: copied {n} derived signal(s)",
    "已複製 {n} 條訊號：到主圖點一個 panel 按 Ctrl+V（macOS ⌘V）貼成衍生訊號；在圖片視窗按 Ctrl+V 疊圖":
        "Copied {n} signal(s): click a panel in the main plot and press Ctrl+V (macOS ⌘V) to paste them as derived signals; Ctrl+V in a figure window overlays them",
    "複製這條訊號": "Copy This Signal",
    "複製全部訊號（{n} 條）": "Copy All Signals ({n})",
    "顯示": "Show",
    # --- copy / paste / drag between the window and the main plot (round 3) ---
    "複製": "Copy",
    "貼上到 P{p}": "Paste to P{p}",
    "放開以貼到 P{p}": "Release to paste into P{p}",
    "拖到主圖的某個 panel 上放開才會貼上": "Drop on a panel of the main plot to paste",
    "沒有放在主圖的 panel 上，取消拖曳": "Not dropped on a main-plot panel; drag cancelled",
    "已取消拖曳": "Drag cancelled",
    "I/Q 分析視窗：拖曳 {name} 到 P{p}": "I/Q analysis window: dragged {name} to P{p}",
    "剪貼簿是空的：先按「複製訊號」或在線上右鍵「複製」": "The clipboard is empty: press \"Copy Signals\" or right-click a line → Copy first",
    "貼上失敗：剪貼簿裡的訊號讀不回來（詳見 log）": "Paste failed: the signals on the clipboard could not be read back (see the log)",
    "把這裡的全部訊號當衍生訊號放進剪貼簿（⌘C／Ctrl+C 也可以；線上右鍵「複製」只複製那一條）：\n到主圖 panel 上右鍵「貼上」或按 ⌘V（在這個視窗按 ⌘V 也會貼到主圖目前的 panel）；也可以直接把線拖到主圖的 panel 上。\n貼進去的跟著來源 I/Q 更新（改 shift／scale／突波抑制會重算）；在圖片視窗按 ⌘V 則是疊圖":
        "Put every signal shown here on the clipboard as derived signals (⌘C / Ctrl+C works too; right-click a line → Copy copies just that one):\n"
        "right-click a main-plot panel → Paste, or press ⌘V (⌘V in this window also pastes into the main plot's current panel); you can also drag a line onto a main-plot panel.\n"
        "The pasted signals follow their I/Q sources (shift / scale / despike changes recompute them); ⌘V in a figure window overlays them instead",
    "已複製 {n} 條訊號：主圖 panel 上右鍵「貼上」或按 Ctrl+V（macOS ⌘V）貼成衍生訊號（在這裡按 ⌘V 也會貼到主圖）；圖片視窗按 Ctrl+V 疊圖":
        "Copied {n} signal(s): right-click a main-plot panel → Paste, or press Ctrl+V (macOS ⌘V) to paste them as derived signals (⌘V here pastes into the main plot too); Ctrl+V in a figure window overlays them",
    # --- toolbar: despike / compare / transitions moved to the Signal tab ---
    "參數…": "Parameters…",
    "容許誤差…": "Tolerance…",
    "打開「訊號屬性 → 突波抑制」：最長連續突波 k、最小偏差、門檻 × 雜訊 σ；目前修正了幾點看狀態列或那個分頁":
        "Open \"Signal Properties → Despike\": longest glitch k, minimum deviation, threshold × noise σ; the number of fixed points is in the status bar and on that tab",
    "打開「訊號屬性 → 檢視 / 差異」設定比對的容許誤差": "Open \"Signal Properties → View / Diff\" to set the comparison tolerance",
    "「訊號屬性 → {tab}」已打開（檢視 → 版面 可以再隱藏）": "\"Signal Properties → {tab}\" opened (View → Layout hides it again)",
    "把清單選取的訊號打開突波抑制：修掉單點／短暫跳到 0 或滿刻度的錯誤值，修正的點用 × 標示。\n沒有選取時套用到全部訊號；參數（k、門檻、最小偏差）按「參數…」":
        "Turn despiking on for the selected signals: removes single / short glitches to 0 or full scale and marks the fixed points with ×.\n"
        "With no selection it applies to all signals; the parameters (k, threshold, minimum deviation) are behind \"Parameters…\"",
    "同一張圖（panel）裡 2 條以上訊號值不同的地方畫半透明紅色區間，狀態列顯示每張圖的段數與比例。\n容許誤差按「容許誤差…」；關掉就不比、上一個／下一個差異也會變灰":
        "Where 2 or more signals in the same panel differ, a translucent red band is drawn and the status bar lists the segment count and ratio per panel.\n"
        "The tolerance is behind \"Tolerance…\"; when off nothing is compared and Previous / Next Difference are disabled",
}
