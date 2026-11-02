# -*- coding: utf-8 -*-
"""English catalog part: axnames — the 2026-10-26 feature: every panel's x-axis and y-axis can be named and every panel can have
a title and a subtitle (like MATLAB title / subtitle / xlabel / ylabel), the right axis can be named and the whole figure can have
a title (MATLAB sgtitle). Text the user types is never translated. Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    # right-click menu → Axes (P1) → names and titles; the figure title item sits outside Axes (P1) (it belongs to no panel)
    "副標題…": "Subtitle…",
    "x 軸名稱…": "X-Axis Name…",          # menu items in title case, like Title… / Subtitle… / Figure Title… (the nouns below stay lower case)
    "y 軸名稱…": "Y-Axis Name…",
    "右軸名稱…": "Right Axis Name…",
    "整張圖的大標題…": "Figure Title…",
    # what is being named (status line, undo / redo descriptions, dialog titles)
    "副標題": "Subtitle",
    "x 軸名稱": "x-axis name",
    "y 軸名稱": "y-axis name",
    "右軸名稱": "Right axis name",
    "整張圖的大標題": "Figure Title",
    "P{p} 的{what}": "{what} of P{p}",
    # dialog prompts (blank = remove; the unit and the P number are added automatically)
    "標題（在這個 panel 上面；空白＝不顯示）：": "Title (above this panel; blank = none):",
    "副標題（在標題下面、不加粗；空白＝不顯示）：": "Subtitle (under the title, not bold; blank = none):",
    "x 軸名稱（例如 時間；單位自動接在後面；空白＝x）：": "x-axis name (e.g. Time; the unit is added after it; blank = x):",
    "y 軸名稱（例如 電壓；P 編號與單位自動加上；空白＝只有 P{p}）：":
        "y-axis name (e.g. Voltage; the P number and the unit are added; blank = just P{p}):",
    "右軸名稱（空白＝右軸）：": "Right axis name (blank = Right Axis):",
    "大標題（在所有 panel 最上面；空白＝不顯示）：": "Figure title (above all panels; blank = none):",
    # status line after a change (Ctrl+Z undoes it)
    "P{p} 的{what}：{v}（Ctrl+Z 可復原）": "P{p} {what}: {v} (Ctrl+Z to undo)",
    "P{p} 的{what}沒有改變": "P{p} {what} is unchanged",
    "整張圖的大標題：{v}": "Figure title: {v}",
    "整張圖的大標題：{v}（Ctrl+Z 可復原）": "Figure title: {v} (Ctrl+Z to undo)",
    "整張圖的大標題沒有改變": "The figure title is unchanged",
    "；$…$ 不是合法的數學式，照打的字顯示": "; the $…$ part is not valid math, so the text is shown as typed",
    "；太長，只留前 {n} 個字": "; too long, only the first {n} characters are kept",
    "；P{p} 現在沒有右軸，有訊號放到右軸時才顯示": "; P{p} has no right axis now, the name shows once a signal is on the right axis",
    "；P{p} 收合著，展開後才顯示": "; P{p} is collapsed, it shows once the panel is expanded",
    # 2026-10-27 (the user's menu decisions): Clear also removes the figure title, like MATLAB clf (Ctrl+Z brings it back)
    "已清空 {n} 條訊號和整張圖的大標題（Ctrl+Z 可復原）": "Cleared {n} signals and the figure title (Ctrl+Z undoes)",
}
