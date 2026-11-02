# -*- coding: utf-8 -*-
"""English catalog part: i13 — user-reported item 13 (2026-10-26): copy and paste of signals with ⌘C/⌘V after clicking a panel.
Paste follows MATLAB plot edit's Paste: a copied line pastes another copy (numbered #2, #3…) into the target panel, also when that
panel already has one; a copy of a whole panel pasted back into that same panel becomes a new panel; one key press pastes once.
Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    # status bar after ⌘C when the list selection is a whole panel (clicked the panel's empty area or its handle)
    "已複製整張 P{p}（{n} 條訊號）：直接按 Ctrl+V（macOS ⌘V）貼成一張新的 panel；點別的 panel 再按 Ctrl+V 就貼進那張；在圖片視窗按 Ctrl+V 疊圖":
        "Copied the whole of P{p} ({n} signal(s)): press Ctrl+V (macOS ⌘V) now to paste it as a new panel; click another panel first "
        "and Ctrl+V pastes into that panel; Ctrl+V in a figure window overlays them",
    # status bar after clicking the panel whose whole copy is on the clipboard
    "目前 panel：P{p}（Ctrl+V／⌘V 把剪貼簿的整張 P{p} 貼成一張新的 panel）":
        "Current panel: P{p} (Ctrl+V/⌘V pastes the copy of the whole P{p} as a new panel)",
    "；Ctrl+V／⌘V 把剪貼簿的整張 P{p} 貼成一張新的 panel":
        "; Ctrl+V/⌘V pastes the copy of the whole P{p} as a new panel",
    # dragging an AM/PM/FM line onto a panel that already has the same pair (drag keeps skipping; paste does not)
    "P{p} 已經有這些訊號（同一組），沒有再加一份；要再貼一份請用 Ctrl+C／Ctrl+V（⌘C／⌘V）":
        "P{p} already has these signals (the same pair), so no other copy was added; to add another copy use Ctrl+C/Ctrl+V (⌘C/⌘V)",
    # status bar after a whole panel was pasted back into itself (MATLAB pastes a copied axes as a new axes)
    "已把整張 P{src} 的 {n} 條訊號貼成新的 P{p}（照 MATLAB 貼上座標區；要貼進別張先點那張再按 Ctrl+V）":
        "Pasted the {n} signal(s) of the whole P{src} as the new P{p} (like pasting axes in MATLAB; to paste into another panel, "
        "click it first and press Ctrl+V)",
    # plot / handle context menu: the clipboard holds a copy of this whole panel
    "貼上成新的 panel（整張 P{p} 的複本）":
        "Paste as a New Panel (Copy of the Whole P{p})",
}
