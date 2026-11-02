# -*- coding: utf-8 -*-
"""English catalog part: fix3 — the 2026-10-25 user-reported items 10–12: clicking a panel selects all of its signals in the
Plotted Signals list, every panel shows its own x tick labels and x-axis label, and the panner shows only the current panel.
Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    # Plotted Signals list: the hint under the table (clicking a panel / a line; 2026-10-25 decisions U1 and U2)
    "點 ☑ 切換顯示；雙擊格子改值；右鍵更多。圖上：點 panel 空白＝選它的全部訊號（沒有工具列模式＝取消選取）、點線條＝只選那一條（資料提示模式＝釘提示）、Shift＋點加選、滾輪縮放、拖曳平移、雙擊空白還原、雙擊圖例改名；Ctrl+Z/Y 復原重做":
        "Click ☑ to toggle visibility; double-click a cell to edit; right-click for more. In the figure: click an empty area of a panel "
        "to select all its signals (with no toolbar mode: clear the selection), click a line to select only that line "
        "(data tip mode: pin a data tip), Shift+click to add, wheel to zoom, drag to pan, "
        "double-click an empty area to reset the view, double-click a legend entry to rename; Ctrl+Z/Y to undo/redo",
    # status bar after clicking a panel (the list follows it)
    "目前 panel：P{p}，清單選取它的 {n} 條訊號（AM/PM/FM、星座圖、GFSK、眼圖、錯誤率比對、平移器與「座標」都對這張）":
        "Current panel: P{p}; its {n} signal(s) are selected in the list (AM/PM/FM, Constellation, GFSK, Eye Diagram, Error Rate, the panner and the Axes settings apply to it)",
    # Ctrl+X / ⌘X when the list selection came from clicking a panel: the whole panel would go, so it asks first
    # (Preferences → "confirm before clearing"), like Delete does
    "剪下 P{p}（{n} 條訊號）？":
        "Cut P{p} ({n} signal(s))?",
    # tooltip of "Fit all panels in the window": each panel's axes is at least 0.5 in and tall enough for its legend
    "把所有 panel 塞進可見高度、不用捲動；每張圖（座標區）至少 0.5 in、而且放得下圖例，塞不下才捲動。關掉就照左邊的高度、超出時可捲動":
        "Fit all panels into the visible height without scrolling; each panel's axes stays at least 0.5 in tall and tall enough for its legend, "
        "and the plot scrolls only when they do not fit. When off, the height on the left is used and the plot scrolls if needed",
    # panner toolbar button: it shows the current panel only (item 12)
    "視圖平移器（MATLAB Signal Analyzer 的 Panner）：主圖下方畫出目前 panel 顯示中訊號的整段，縮放窗＝目前 panel 的 x 範圍；點別張 panel 就換成那張。\n在平移器上點住拖曳＝建立縮放窗；拖縮放窗的邊＝調整寬度；拖中間＝沿著訊號滑動（連結時間的 panel 跟著）。\n每條訊號各自縮放到同樣高度（DSV 的做法，大小差很多的訊號也看得到）":
        "View panner (MATLAB Signal Analyzer Panner): a strip under the plot shows the current panel's displayed signals over their entire duration; "
        "the zoom window is the current panel's x range. Click another panel to switch to it.\n"
        "Click the panner and drag to create a zoom window; drag its edges to resize it; drag its middle to slide it along the signal "
        "(panels with Link Time follow).\n"
        "Each signal is scaled to the same height (a DSV choice, so signals of very different size all stay visible)",
    # ---- round 3 (2026-10-25 decisions U1–U8, F1–F15) ---------------------------------------------------------------
    # status bar after Save as Image… when the chosen size made the export fall back to the 0.9.8 x-axis labelling (D20)
    "圖已存成 {path}。{hint}": "Figure saved to {path}. {hint}",
    "這個大小放不下每張 panel 的 x 軸標籤，這次匯出只在最下面標；要每張都標請加大高度":
        "This size cannot fit x-axis labels on every panel, so this export labels only the bottom panel; "
        "make it taller to label every panel",
    "這個大小放不下每張 panel 的 x 軸標籤，這次匯出連結時間而且單位一樣的只在最下面那張標；要每張都標請加大高度":
        "This size cannot fit x-axis labels on every panel, so this export labels linked panels with the same units only "
        "on the bottom one of each run; make it taller to label every panel",
    "這個大小太矮：圖例、x 軸標籤、標題可能壓到下一張，請加大高度":
        "This size is too short: legends, x-axis labels and titles may overlap the next panel; make it taller",
    # ---- round 4 (2026-10-25 review) ------------------------------------------------------------------------------
    # Save as Image…: the export fell back to the 0.9.8 labelling AND is still too short (both are said)
    "這個大小放不下每張 panel 的 x 軸標籤，這次匯出只在最下面標；而且還是太矮，圖例、x 軸標籤、標題可能壓到下一張，請加大高度":
        "This size cannot fit x-axis labels on every panel, so this export labels only the bottom panel; "
        "it is still too short, so legends, x-axis labels and titles may overlap the next panel; make it taller",
    "這個大小放不下每張 panel 的 x 軸標籤，這次匯出連結時間而且單位一樣的只在最下面那張標；而且還是太矮，圖例、x 軸標籤、標題可能壓到下一張，請加大高度":
        "This size cannot fit x-axis labels on every panel, so this export labels linked panels with the same units only "
        "on the bottom one of each run; it is still too short, so legends, x-axis labels and titles may overlap the next panel; make it taller",
    # paste: a derived signal whose sources no longer exist becomes an independent signal with the data it had when copied
    "（{k} 條衍生訊號的來源已經不在，用複製那時的資料改成獨立訊號）":
        " ({k} derived signal(s) whose sources no longer exist became independent signals with the data they had when copied)",
    # Ctrl+X / ⌘X while the Folder panel file tree has keyboard focus: keys belong to that widget, no signal is cut
    "資料夾面板不會剪下磁碟上的檔案；要剪下訊號請先點主圖或「已繪訊號」清單":
        "The Folder panel does not cut files on disk; to cut signals, click the plot or the Plotted Signals list first",
    # status bar after clicking a panel when the signal clipboard is not empty (appended to the "Current panel: P2, …" line)
    "；Ctrl+V／⌘V 貼上剪貼簿的 {n} 條訊號": "; Ctrl+V / ⌘V pastes the {n} signal(s) on the clipboard",
    # status bar after deleting / cutting signals whose derived signals live in other panels (U8)
    "；{where} 的 {n} 條衍生訊號留著，改成獨立訊號（保留現在的資料）":
        "; the {n} derived signal(s) in {where} stay as independent signals (their current data is kept)",
    # 0.9.13 B4 (user decision 2026-10-28): Preprocess results that could not be computed go with their source (status bar / confirmation)
    "；{where} 的 {n} 條算不出結果的前處理一起移除":
        "; the {n} Preprocess result(s) in {where} that could not be computed were removed with it",
    "{where} 的 {n} 條算不出結果的前處理結果會一起移除":
        "The {n} Preprocess result(s) in {where} that could not be computed will be removed with it",
    # 0.9.13 B2 (user decision 2026-10-28): files / folders given as start-up arguments are added by the drag-and-drop rule after the restore
    "啟動參數加入": "Add start-up arguments",
    "啟動參數加入 {n} 條訊號到 {panels}": "Start-up arguments: added {n} signal(s) to {panels}",
    "啟動參數的檔案已經畫在 {panels}（已選取）": "The files given as start-up arguments are already plotted in {panels} (selected)",
    "啟動參數的檔案都讀不了": "None of the files given as start-up arguments could be read",
    # Measurements panel: nothing selected → it measures all signals (U6)
    "；沒有選取：量測全部 {n} 條": "; nothing selected: measuring all {n} signal(s)",
    "；沒有選取：量測全部 {n} 條，只列前 {m} 條": "; nothing selected: measuring all {n} signals, only the first {m} are listed",
    "開關「量測」面板（MATLAB Time Scope 的 Signal Statistics＋Bilevel Measurements）：\n列出選取的訊號（沒有選取時全部，最多 8 條）在目前 x 範圍內的最大／最小值（含位置）、峰對峰、平均、變異數、標準差、中位數、RMS、均方值，\n以及 +／−脈波數、週期、頻率、脈寬、工作週期；縮放、平移或改選取時自動重算":
        "Show / hide the Measurements panel (MATLAB Time Scope Signal Statistics + Bilevel Measurements):\n"
        "max / min (with position), peak to peak, mean, variance, standard deviation, median, RMS and mean square of the selected signals "
        "(all signals when nothing is selected, up to 8) over the current x range,\n"
        "plus + / − pulses, period, frequency, width and duty cycle; recomputed after zoom, pan or a new selection",
    # ---- round 7 (2026-10-25 decision U10) -------------------------------------------------------------------------
    # A deletion or cut would turn derived signals in other panels into independent signals (U8), but their data cannot be
    # saved in the frozen folder (read-only folder, full disk, a file in the way, any OSError): the whole operation is
    # cancelled and an error dialog says which derived signals, the folder and the reason.
    # dialog titles
    "刪除已取消": "Deletion cancelled",
    "移除已取消": "Removal cancelled",
    "剪下已取消": "Cut cancelled",
    # what was being done ({what} below)
    "刪除「{name}」": "Delete “{name}”",
    "移除「{name}」": "Remove “{name}”",
    "剪下「{name}」": "Cut “{name}”",
    "刪除 P{p}（共 {n} 條訊號）": "Delete P{p} ({n} signal(s))",
    "剪下 P{p}（{n} 條訊號）": "Cut P{p} ({n} signal(s))",
    # dialog text
    "{what}：已取消，什麼都沒有移除，復原記錄也沒變。": "{what}: cancelled. Nothing was removed and the undo history is unchanged.",
    "下面 {n} 條衍生訊號的來源要被刪掉，它們要改成獨立訊號（保留現在的資料），但資料存不進 frozen 資料夾：":
        "The sources of the {n} derived signal(s) below would be deleted, so they would become independent signals keeping their "
        "current data, but that data could not be saved in the frozen folder:",
    "P{p}：{name}": "P{p}: {name}",
    "{row}——{reason}": "{row} — {reason}",
    "……還有 {k} 條": "… and {k} more",
    "資料夾：{path}": "Folder: {path}",
    "原因：{reason}": "Reason: {reason}",
    "請讓這個資料夾可以寫入（權限、磁碟空間、擋住的同名檔案）之後再試一次。":
        "Make this folder writable (permissions, free disk space, a file with the same name in the way) and try again.",
    # status bar and the action history (diagnostics)
    "{what}：已取消，{n} 條衍生訊號的資料存不進 frozen 資料夾，什麼都沒有移除":
        "{what}: cancelled; the data of {n} derived signal(s) could not be saved in the frozen folder, so nothing was removed",
    "{what}：已取消（衍生訊號的資料存不進 frozen 資料夾）": "{what}: cancelled (the data of derived signals could not be saved in the frozen folder)",
    # reasons; the operating system's own message follows in parentheses
    "{desc}（{raw}）": "{desc} ({raw})",
    "存進去的資料讀回來不一樣": "the data read back differs from what was saved",
    "有同名的檔案或資料夾擋住": "a file or folder with the same name is in the way",
    "沒有寫入權限": "no permission to write",
    "磁碟是唯讀的": "the disk is read-only",
    "磁碟空間不足": "not enough disk space",
    "超過磁碟配額": "disk quota exceeded",
    # ---- round 8 (2026-10-26) ----------------------------------------------------------------------------------------
    # a real write failure past the file-size limit (EFBIG) now carries its errno instead of numpy's internal message
    "檔案超過大小上限": "the file exceeds the size limit",
    "請讓這個資料夾可以寫入（權限、磁碟空間、擋住的同名檔案）之後再匯入一次。":
        "Make this folder writable (permissions, free disk space, a file with the same name in the way) and import again.",
    # ---- round 9 (2026-10-26 decisions U11–U14) ----------------------------------------------------------------------
    # U11 — pasting needs to turn derived signals whose sources were deleted into independent signals, but their data cannot be
    # saved in the frozen folder (or this window cannot register there): the whole paste is cancelled
    "貼上已取消": "Paste cancelled",
    "貼上到 P{p}（共 {n} 條訊號）": "Paste into P{p} ({n} signal(s))",
    "{what}：已取消，什麼都沒有貼上，剪貼簿和復原記錄也沒變。":
        "{what}: cancelled. Nothing was pasted; the clipboard and the undo history are unchanged.",
    "下面 {n} 條衍生訊號的來源已經不在，要用複製那時的資料改成獨立訊號，但資料存不進 frozen 資料夾：":
        "The sources of the {n} derived signal(s) below no longer exist, so they would be pasted as independent signals with the "
        "data they had when copied, but that data could not be saved in the frozen folder:",
    "{what}：已取消，{n} 條衍生訊號的資料存不進 frozen 資料夾，什麼都沒有貼上":
        "{what}: cancelled; the data of {n} derived signal(s) could not be saved in the frozen folder, so nothing was pasted",
    # U14 — 匯入設定 (Import Settings) of a file that carries independent signals' data: checked first, the whole import is
    # cancelled when the data cannot be saved in the frozen folder
    "匯入已取消": "Import cancelled",
    "匯入設定：已取消，目前的工作階段沒有改變（訊號、版面、設定都照舊）。":
        "Import Settings: cancelled. The current session is unchanged (signals, layout and settings stay as they were).",
    "設定檔：{path}": "Settings file: {path}",
    "下面 {n} 條獨立訊號的資料在設定檔裡，要先存進 frozen 資料夾，但存不進去：":
        "The data of the {n} independent signal(s) below is in the settings file and has to be saved in the frozen folder first, "
        "but it could not be saved:",
    "匯入設定：已取消（獨立訊號的資料存不進 frozen 資料夾）":
        "Import Settings: cancelled (the data of independent signals could not be saved in the frozen folder)",
    "匯入設定：已取消，{n} 條獨立訊號的資料存不進 frozen 資料夾，目前的工作階段沒有改變":
        "Import Settings: cancelled; the data of {n} independent signal(s) could not be saved in the frozen folder, "
        "the current session is unchanged",
    # U12 — the autosave cannot be written while closing: close anyway (the previous autosave stays intact) or don't close yet
    "自動存檔寫不進去": "Autosave could not be written",
    "自動存檔寫不進去：這次工作階段的變更（訊號、版面、設定）還沒存到。":
        "The autosave could not be written: the changes of this session (signals, layout, settings) have not been saved.",
    "自動存檔寫不進去：這次改的偏好設定（語言、主題、檢視設定）還沒存到。":
        "The autosave could not be written: the preferences changed in this session (language, theme, view settings) have not "
        "been saved.",
    "自動存檔：{path}": "Autosave: {path}",
    "照樣關閉：這次的變更不存；上一次的自動存檔保持原樣（下次開啟還原的是它）。":
        "Close Anyway: the changes are not saved; the previous autosave stays as it is (the next start restores it).",
    "先不關：回到 DSV，清出空間或修好權限之後再關閉一次（也可以先用「匯出設定」存到別的地方）。":
        "Don't Close: go back to DSV, free some space or fix the permissions, then close again (you can also save the session "
        "elsewhere with Export Settings first).",
    "照樣關閉": "Close Anyway",
    "先不關": "Don't Close",
    "關閉：自動存檔寫不進去，先不關": "Close: the autosave could not be written, not closed",
    "沒有關閉：自動存檔寫不進去（{reason}）。清出空間或修好權限之後再關閉一次":
        "Not closed: the autosave could not be written ({reason}). Free some space or fix the permissions, then close again",
    # U13 — the autosave exists but cannot be read at startup: tell the user, keep a backup copy, start empty
    "上次的工作階段讀不回來": "Last session could not be restored",
    "上次的自動存檔讀不回來（檔案壞掉或被截斷），這次從空的開始。":
        "The autosave of the last session could not be read (the file is damaged or truncated), so DSV starts empty this time.",
    "不是完整的 JSON（{raw}）": "not complete JSON ({raw})",
    "原本的檔另存了一份：{path}": "A copy of the file was kept: {path}",
    "另存備份失敗（{reason}）：原本的檔留在原處，DSV 不會蓋掉它；讓那個資料夾可以寫入之後再關閉或重新開啟 DSV，會再試一次。":
        "The backup copy could not be made ({reason}): the file stays where it is and DSV will not overwrite it; make that folder "
        "writable, then close or restart DSV to try again.",
    "上次的自動存檔讀不回來，這次從空的開始（詳見對話框）":
        "The autosave of the last session could not be read, so DSV starts empty this time (see the dialog)",
    "自動存檔讀不了：從空的開始": "Autosave could not be read: started empty",
    # ---- round 10 (2026-10-26 decisions U15, U16 and the round-9 verifier findings) ----------------------------------
    # U15 — while ANY autosave backup (<name>.bad*.json next to the autosave) exists, the frozen clean-up deletes nothing
    # (round 11: the notice also says to import first and check that the signals are back before deleting the backups)
    "只要自動存檔旁邊還有任何一份備份（{pattern}），frozen 資料夾裡的獨立訊號資料檔就一個都不會被自動清掉（不管有沒有人用到）。要找回上次的訊號，可以把備份修好之後用「匯入設定」開啟它——請先匯入、確認訊號都回來了再刪備份（備份一刪掉，只有它用到的獨立訊號資料就會被清掉；搬到別的資料夾、或改成不符合上面樣式的名字，也一樣不算備份）。不需要了就把這些備份都刪掉，之後才會照常自動清掉沒人用到的檔。":
        "As long as any backup ({pattern}) exists next to the autosave, no independent signal's data file in the frozen folder is "
        "cleaned up automatically (whether anything uses it or not). To get the last signals back, repair the backup and open it "
        "with Import Settings — import it first and check that the signals are back before you delete the backups (once the "
        "backups are deleted, data files used only by them are cleaned up; a backup moved to another folder or renamed so that it "
        "no longer matches the pattern above does not count either). When you no longer need the backups, delete all of them — "
        "only then does the automatic clean-up of unused files resume.",
    "這個讀不了的自動存檔還在原處的期間、以及備份做好之後只要還有任何一份備份（{pattern}），frozen 資料夾裡的獨立訊號資料檔一個都不會被自動清掉；要找回上次的訊號，請先用「匯入設定」開啟修好的備份、確認訊號都回來了再刪備份（備份一刪掉，只有它用到的獨立訊號資料就會被清掉）。不需要了就把備份刪掉，之後才會照常自動清掉沒人用到的檔。":
        "While this unreadable autosave stays where it is, and after the backup is made as long as any backup ({pattern}) exists, "
        "no independent signal's data file in the frozen folder is cleaned up automatically. To get the last signals back, open "
        "the repaired backup with Import Settings first and check that the signals are back before you delete the backups (once "
        "the backups are deleted, data files used only by them are cleaned up). When you no longer need the backups, delete "
        "them — only then does the automatic clean-up of unused files resume.",
    # the autosave cannot be READ (no read permission): say so, and describe the rename to the backup correctly
    "沒有讀取權限": "no permission to read",
    "上次的自動存檔讀不回來，這次從空的開始。": "The autosave of the last session could not be read, so DSV starts empty this time.",
    "原本的檔讀不了、沒辦法複製，所以整個改名成備份（原本的位置現在沒有自動存檔）：{path}":
        "The file could not be read or copied, so it was renamed to the backup (there is no autosave at the original place now): "
        "{path}",
    "這份備份的權限和原本的檔一樣，現在還是讀不了：要用「匯入設定」開啟它之前，先修好它的權限（讓你的帳號可以讀取）。":
        "The backup keeps the permissions of the original file, so it still cannot be read: before opening it with Import "
        "Settings, fix its permissions (let your account read it).",
    # U16 — no silent pasting of empty signals: a derived signal whose sources are gone and whose data is not in the clipboard
    "下面 {n} 條衍生訊號的來源已經不在，剪貼簿裡也沒有它們的資料，沒辦法改成獨立訊號：":
        "The sources of the {n} derived signal(s) below no longer exist and the clipboard does not hold their data, so they "
        "cannot be pasted as independent signals:",
    "請先復原（Ctrl+Z）讓來源回來再貼，或在來源還在的時候重新複製一次。":
        "Undo (Ctrl+Z) to bring the sources back before pasting, or copy the signals again while their sources exist.",
    "{what}：已取消（衍生訊號的來源不在、也沒有資料）":
        "{what}: cancelled (the derived signals' sources no longer exist and their data is not available)",
    "{what}：已取消，{n} 條衍生訊號的來源不在、剪貼簿裡也沒有資料，什麼都沒有貼上":
        "{what}: cancelled; the sources of {n} derived signal(s) no longer exist and the clipboard holds no data for them, so "
        "nothing was pasted",
    # ---- round 11 (2026-10-26 round-10 verifier findings) -------------------------------------------------------------
    # U13 also covers an autosave whose JSON parses but cannot be restored (wrong structure) — say what is wrong
    '設定檔的 "{key}" 不是整數': 'the settings file\'s "{key}" is not an integer',
    '設定檔的 "{key}" 不是 JSON 物件': 'the settings file\'s "{key}" is not a JSON object',
    '設定檔的 "{key}" 不是清單': 'the settings file\'s "{key}" is not a list',
    '設定檔的 "{key}" 不是文字': 'the settings file\'s "{key}" is not a string',
    "內容套用不了（{raw}）": "its content could not be applied ({raw})",
    "設定檔帶的獨立訊號資料存不進 frozen 資料夾":
        "the independent signals' data carried in the settings file could not be saved in the frozen folder",
    # U13 for an autosave that is a symbolic link whose target is missing (an external or network disk not connected):
    # the link itself is renamed to the backup, the target file is never touched
    "捷徑指的檔不在": "the file the link points to is missing",
    "自動存檔是捷徑（symlink），它指的檔現在不在（外接磁碟或網路磁碟沒接上？）：{target}":
        "The autosave is a symbolic link and the file it points to is missing now (an external or network disk not connected?): "
        "{target}",
    "捷徑整個改名成備份（還是指著那個檔，那個檔一個位元組都不動；原本的位置現在沒有自動存檔，這次關閉時在那裡寫一份新的）：{path}":
        "The link itself was renamed to the backup (it still points to that file, and that file is not touched; there is no "
        "autosave at the original place now, and a new one is written there when you close DSV): {path}",
    "那個檔回來之後（磁碟接上），用「匯入設定」開啟這份備份就能找回上次的訊號。":
        "When that file is back (the disk connected), open this backup with Import Settings to get the last signals back.",
    # (b) the autosave / exported settings folder cannot be written although the file itself can: name the folder
    "不能寫入的資料夾：{path}（先在這個資料夾寫好暫存檔才換上去，所以檔案本身可以寫也一樣寫不進去）":
        "Folder that cannot be written: {path} (a temporary file is written in this folder first and then put in place, so it "
        "fails even when the file itself is writable)",
    "設定沒有匯出：{path}": "The settings were not exported: {path}",
    "已經有的那個檔一個位元組都沒動。": "The existing file was not changed at all.",
    # ---- round 12 (2026-10-26 final verifier findings) ----------------------------------------------------------------
    # U13 / U15 for an autosave that is readable but some of its signals cannot be restored (a field of the wrong type, a missing
    # field, a missing file, missing sources) while they use independent signals' data files: the others are restored, the
    # autosave is backed up (no frozen clean-up while the backup exists) and a notice lists what was not restored
    "上次的工作階段有訊號沒還原": "Some signals of the last session were not restored",
    "上次的自動存檔裡有 {n} 條訊號還原不了，其他的照常還原了：":
        "{n} signal(s) in the autosave of the last session could not be restored; the others were restored as usual:",
    "找不到檔案：{path}": "file not found: {path}",
    "欄位不對（{raw}）": "a field is not valid ({raw})",
    '設定檔少了 "{key}"': 'the settings file lacks "{key}"',
    '設定檔的 "{key}" 不是數字': 'the settings file\'s "{key}" is not a number',
    "來源訊號不見了": "its source signals are missing",
    "沒還原的訊號裡有獨立訊號（資料只存在 frozen 資料夾的檔裡），這次關閉時寫的自動存檔不會再記著它們，所以原本的自動存檔另存了一份：{path}":
        "Some of the signals that were not restored are independent signals (their data exists only in files in the frozen "
        "folder). The autosave written when you close DSV this time will no longer record them, so a copy of the original "
        "autosave was kept: {path}",
    "沒還原的訊號裡有獨立訊號（資料只存在 frozen 資料夾的檔裡），原本的自動存檔要先另存一份備份，但另存失敗（{reason}）。這次關閉時會先再試一次備份，還是不行就不蓋掉原本的自動存檔、問你要不要照樣關閉（照樣關閉＝這次的變更不存）。讓那個資料夾可以寫入之後再關閉，就會先做好備份再存。":
        "Some of the signals that were not restored are independent signals (their data exists only in files in the frozen "
        "folder), so a backup copy of the original autosave has to be made first, but it could not be made ({reason}). When you "
        "close DSV this time it tries the backup again; if that still fails, the original autosave is not overwritten and DSV "
        "asks whether to close anyway (Close Anyway = this session's changes are not saved). Make that folder writable before "
        "closing, and the backup is made before saving.",
    "備份做好之前，這次開著的期間 frozen 資料夾裡的獨立訊號資料檔一個都不會被自動清掉；備份做好之後，只要還有任何一份備份（{pattern}）也一個都不清。要找回這幾條訊號，請先用「匯入設定」開啟修好的備份、確認訊號都回來了再刪備份（備份一刪掉，只有它用到的獨立訊號資料就會被清掉）。不需要了就把備份刪掉，之後才會照常自動清掉沒人用到的檔。":
        "Until the backup is made, no independent signal's data file in the frozen folder is cleaned up automatically while DSV "
        "stays open; after the backup is made, none is cleaned up as long as any backup ({pattern}) exists. To get these signals "
        "back, open the repaired backup with Import Settings first and check that the signals are back before you delete the "
        "backups (once the backups are deleted, data files used only by them are cleaned up). When you no longer need the "
        "backups, delete them — only then does the automatic clean-up of unused files resume.",
    "上次的自動存檔有 {n} 條訊號沒還原（詳見對話框）":
        "{n} signal(s) of the last session's autosave were not restored (see the dialog)",
    "自動存檔有訊號沒還原：另存備份": "Autosave had signals that could not be restored: backup kept",
    "自動存檔有訊號沒還原：另存備份失敗": "Autosave had signals that could not be restored: the backup could not be made",
}
