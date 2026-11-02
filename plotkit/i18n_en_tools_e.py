# -*- coding: utf-8 -*-
"""English catalog part: tools_e — tool-gap batch E (Settings pages and Help button, Export To… dialog,
Zoom out button and zoom/pan direction limits, Undo/Redo with the action name).  Keys are the Traditional Chinese
source strings, byte for byte.  Names follow MATLAB R2025a (Settings, Export To…, axes toolbar, Edit ▸ Undo: <action>).
"""
CATALOG = {
    # --- export dialog (plotkit.export) ---------------------------------------------------------------------
    "{ext}（{desc}）": "{ext} ({desc})",
    "主題色": "Theme color",
    "白色": "White",
    "透明": "Transparent",
    "格式": "Format",
    "解析度 (DPI)": "Resolution (DPI)",
    "背景": "Background",
    "寬度": "Width",
    "高度": "Height",
    "目前大小": "Current Size",
    "內容類型：向量（線條與文字可任意放大；DPI 只影響內嵌的點陣部分）":
        "Content type: vector (lines and text scale without loss; DPI only affects embedded raster parts)",
    "內容類型：影像（點陣；像素數＝寬度 × DPI）": "Content type: image (raster; pixels = width × DPI)",
    "只匯出這個 panel": "Export This Panel Only",
    "只匯出這個 panel…": "Export This Panel Only…",
    "只匯出這個 panel（含刻度、標籤與圖例），其他 panel 不會出現；寬高是整張圖的大小。":
        "Only this panel (with its ticks, labels and legend) is exported; other panels are left out. "
        "Width and height are the size of the whole figure.",
    "寬高或 DPI 不對：DPI 要在 {lo}～{hi}，寬高要是正數（0.2～200 英吋）":
        "Invalid size or DPI: DPI must be {lo}–{hi}; width and height must be positive (0.2–200 in)",
    "輸出 {w:.2f} × {h:.2f} 英吋（向量）": "Output {w:.2f} × {h:.2f} in (vector)",
    "輸出 {w} × {h} 像素": "Output {w} × {h} pixels",
    "（裁切前）": " (before cropping)",
    "存成圖檔…（格式、DPI、背景、尺寸）": "Save Figure As… (format, DPI, background, size)",
    "存成 PNG／JPEG／TIFF／PDF／EPS／SVG…：可選 DPI、背景、寬高":
        "Save as PNG / JPEG / TIFF / PDF / EPS / SVG…: choose DPI, background, width and height",
    "匯出對話框：格式（PNG／JPEG／TIFF／PDF／EPS／SVG…）、DPI、背景、寬高（十字游標不會印進去）；\n只存一個 panel：圖上右鍵「只匯出這個 panel…」":
        "Export dialog: format (PNG / JPEG / TIFF / PDF / EPS / SVG…), DPI, background, width and height "
        "(the crosshair is not included);\nto save a single panel, right-click it and choose \"Export This Panel Only…\"",
    # --- zoom out, direction limits (plotkit.theme / plotkit.interact) ----------------------------------------
    "縮小（以座標區中心縮小 1.5 倍；方向照放大／平移模式右鍵的方向限制）":
        "Zoom out (1.5× around the axes center; follows the direction limit set in the zoom/pan mode right-click menu)",
    "縮放／平移方向：只水平（x）——滾輪、拖曳、放大模式與方向鍵都只動 x":
        "Zoom/pan direction: horizontal only (x) — wheel, drag, zoom mode and arrow keys change x only",
    "縮放／平移方向：只垂直（y）——滾輪、拖曳、放大模式與方向鍵都只動 y":
        "Zoom/pan direction: vertical only (y) — wheel, drag, zoom mode and arrow keys change y only",
    "縮放／平移方向：不限制": "Zoom/pan direction: unconstrained",
    "不限方向平移": "Unconstrained Pan",
    "只平移 x（水平）": "Horizontal Pan",
    "只平移 y（垂直）": "Vertical Pan",
    # --- undo / redo with the action name (MATLAB "Undo: Pan") ------------------------------------------------
    "復原：{desc}": "Undo: {desc}",
    "重做：{desc}": "Redo: {desc}",
    "已復原：{desc}": "Undone: {desc}",
    "已重做：{desc}": "Redone: {desc}",
    # --- preferences (Settings) pages and Help button ----------------------------------------------------------
    "字型": "Fonts",
    "確認對話框": "Confirmation Dialogs",
    "偏好設定、匯出圖檔": "Preferences, Figure Export",
    "縮放／平移方向": "Zoom/pan direction",
    "不限制": "Unconstrained",
    "只水平（x）": "Horizontal (x)",
    "只垂直（y）": "Vertical (y)",
    "介面字級 (px)": "UI font size (px)",
    "圖字級 (pt)": "Plot font size (pt)",
    "介面字級：工具列、面板、表格、選單（預設 12 px，照 MATLAB R2025a 量的）。圖字級：刻度、軸標籤、標題、圖例、資料提示與文字標註一起縮放（預設 10 pt）。":
        "UI font size: toolstrip, panels, tables and menus (default 12 px, measured from MATLAB R2025a). "
        "Plot font size: tick labels, axis labels, titles, legends, data tips and text annotations scale together (default 10 pt).",
    "還原預設字級": "Restore Default Font Sizes",
    "預設 DPI": "Default DPI",
    "預設背景": "Default background",
    "「存成圖檔…」與 panel 右鍵「只匯出這個 panel…」對話框一開始用這裡的 DPI 與背景（MATLAB Export To… 的 Resolution／Background）。複製圖到剪貼簿固定 150 DPI。":
        "\"Save Figure As…\" and the panel right-click \"Export This Panel Only…\" dialogs start with this DPI and background "
        "(MATLAB Export To… Resolution / Background). Copying the figure to the clipboard always uses 150 DPI.",
    "清空全部訊號前先確認": "Confirm before clearing all signals",
    "關掉後按「清空」直接移除（仍可 Ctrl+Z／⌘Z 復原）。": "When off, Clear removes all signals at once (still undoable with Ctrl+Z / ⌘Z).",
}
