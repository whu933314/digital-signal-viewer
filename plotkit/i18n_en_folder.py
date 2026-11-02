# -*- coding: utf-8 -*-
"""English catalog part: folder — the Current Folder panel (MATLAB R2025a Current Folder: Name / Size / Date Modified / Type,
Open, Show in Finder, Open Current Folder in Finder, Copy Path, Rename, Details) and the plot panel × / selection.
Keys are the Traditional Chinese source strings, byte for byte.  Wording follows MATLAB's own Current Folder browser messages.
"""
CATALOG = {
    # --- columns, sorting ---
    "名稱": "Name",
    "大小": "Size",
    "修改日期": "Date Modified",
    "類型": "Type",
    "資料夾": "Folder",
    "{ext} 檔案": "{ext} File",
    "檔案": "File",
    "顯示": "Show",
    "排序方式": "Sort By",
    "遞增": "Ascending",
    "遞減": "Descending",
    # --- address bar ---
    "返回（上一個資料夾）": "Back (previous folder)",
    "前進": "Forward",
    "目前資料夾；下拉＝最近去過的資料夾，Enter 前往": "Current folder; the drop-down lists recent folders, Enter to go there",
    "（項目太多，只列出前 {n} 個）": " (too many items; only the first {n} are listed)",
    # --- context menu ---
    "開啟": "Open",
    "以系統預設程式開啟": "Open Outside DSV",
    "在 Finder 中顯示": "Show in Finder",
    "在 Finder 開啟目前資料夾": "Open Current Folder in Finder",
    "在檔案總管中顯示": "Show in Explorer",
    "在檔案總管開啟目前資料夾": "Open Current Folder in Explorer",
    "複製路徑": "Copy Path",
    "重新命名…": "Rename…",
    "重新命名": "Rename",
    "新名稱：": "New name:",
    "用系統預設程式開啟 {name}": "Opened {name} with the system default app",
    "已複製路徑：{path}": "Path copied: {path}",
    "先在資料夾面板選一個檔案或資料夾": "Select a file or folder in the Folder panel first",
    "{name} 正被已繪訊號使用（{n} 條）：先移除那些訊號再改名。": "{name} is used by {n} plotted signal(s): remove those signals before renaming.",
    "名稱不能是空白。": "The file name cannot be blank.",
    "名稱不能含有這些字元：{chars}": "These characters are invalid in a file name: {chars}",
    "沒有開「顯示隱藏的檔案與資料夾」時，不能改成隱藏的名稱（. 開頭）。":
        "The file name cannot be renamed to a hidden file name while \"Show hidden files and folders\" is off.",
    "已經有同名的檔案。": "A file by this name already exists.",
    "已經有同名的資料夾。": "A folder by this name already exists.",
    "無法重新命名「{name}」。\n{err}": "Unable to rename '{name}'.\n{err}",
    "已重新命名：{old} → {new}": "Renamed: {old} → {new}",
    "資料夾面板不會刪除磁碟上的檔案（要刪檔請用 Finder／檔案總管）":
        "The Folder panel does not delete files on disk (use Finder / Explorer to delete files)",
    # --- details ---
    "詳細資料": "Details",
    "選一個檔案或資料夾來看詳細資料": "Select a file or folder to view details",
    "已選取 {n} 個項目": "{n} items selected",
    "欄位：{col}\n檔案：{name}": "Column: {col}\nFile: {name}",
    "資料夾｜{n} 個項目": "Folder | {n} items",
    "修改日期：{t}": "Date Modified: {t}",
    "{type}｜{size}": "{type} | {size}",
    "{n} 個資料欄：{names}": "{n} data columns: {names}",
    "時間欄：{name}": "Time column: {name}",
    "讀不到欄位：{err}": "Cannot read the columns: {err}",
    "這種檔案不能畫圖；雙擊用系統預設程式開啟": "This file type cannot be plotted; double-click opens it in the system default app",
    # --- preferences ---
    "顯示隱藏的檔案與資料夾": "Show hidden files and folders",
    "資料夾內容改變時自動重新整理": "Refresh automatically when the folder contents change",
    # --- plot panel × and selection ---
    "刪除 P{p}（可復原）": "Delete P{p} (undoable)",
    "已選取 P{p}：Delete 刪除這個 panel、拖曳換順序、右鍵更多（Esc 取消）":
        "P{p} selected: Delete removes this panel, drag to reorder, right-click for more (Esc to cancel)",
    "刪除選取的訊號／panel": "Delete Selected Signals / Panel",
}
