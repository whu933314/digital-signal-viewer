# -*- coding: utf-8 -*-
"""English catalog part — 0.9.14 P-5（開著時來源檔案消失、又有衍生訊號：改讀取格式時留成佔位）；
22:5x 的決定：開著時檔案出問題的其他情況（沒有衍生訊號、檔案在卻讀不了、重畫時才發現）也留佔位、擷取訊號（ROI）來源檔案不在或讀不了時不擷取；
0.9.14 深度審查修正：關閉時提醒還有檔案沒處理、自動存檔讀不了時問到的別的版本的備份選「從空的開始」先另存一份（F-U13P）（2026-10-30 使用者決定）。
Keys are the Traditional Chinese source strings in signal_viewer.py."""

CATALOG = {
    "{n} 條訊號的檔案不在了，留在清單當佔位：{names}": "The files of {n} signals are gone, kept in the list as placeholders: {names}",
    "{n} 條訊號的檔案不在了（{names}）：先留在清單當佔位（灰字、不畫；以它們為來源的衍生訊號和參數都留著），檔案回來會自動讀進來，也可以在清單按右鍵「重新載入檔案不在的訊號」":
        "The files of {n} signals are gone ({names}): they stay in the list as placeholders (greyed out, not drawn; the derived signals built on them "
        "and all parameters are kept). They are loaded automatically once the files are back, or right-click the list and choose "
        "\"Reload Signals with Missing Files\"",
    "（{k} 條的檔案已經不在，貼上的是佔位，檔案回來會自動讀進來）":
        " ({k} files are already gone: pasted as placeholders, loaded automatically once the files are back)",
    "{n} 條訊號的檔案讀不了，留在清單當佔位：{names}": "The files of {n} signals cannot be read, kept in the list as placeholders: {names}",
    "{n} 條訊號的檔案在卻讀不了（{names}；{reason}）：先留在清單當佔位（灰字、Fmt 欄寫「讀不了」、不畫；以它們為來源的衍生訊號和參數都留著），檔案修好會自動讀進來，也可以在清單按右鍵「重新載入檔案不在的訊號」":
        "The files of {n} signals are there but cannot be read ({names}; {reason}): they stay in the list as placeholders (greyed out, "
        "Fmt shows \"unreadable\", not drawn; the derived signals built on them and all parameters are kept). They are loaded automatically "
        "once the files are fixed, or right-click the list and choose \"Reload Signals with Missing Files\"",
    "{k} 條的來源檔案不在，不能擷取（檔案回來再試）：{names}":
        "The source files of {k} signals are gone, cannot extract (try again when the files are back): {names}",
    "{k} 條的來源檔案讀不了，不能擷取（檔案修好再試）：{names}（{reason}）":
        "The source files of {k} signals cannot be read, cannot extract (try again when the files are fixed): {names} ({reason})",
    # 關閉時提醒還有檔案沒處理（2026-10-30 使用者決定 00:5x、09:1x）
    "還有檔案沒處理": "Some files still need your attention",
    "關閉之前提醒一下：下面這些檔還在，DSV 不會自己刪掉它們（處理掉之後就不再提醒）。":
        "Before closing, a reminder: the files below are still there and DSV will not delete them for you (once you have dealt with them, "
        "this reminder stops).",
    "複製圖到剪貼簿失敗時存下的圖（可以直接開來用；不需要了就刪掉）：":
        "Images saved when copying the figure to the clipboard failed (you can open and use them directly; delete them when no longer needed):",
    "另存的舊備份、讀不了的自動存檔另存的備份（{pattern}；可以用「匯入設定」開啟，確認裡面的訊號之後再刪）。這些檔還在的期間，frozen 資料夾裡的獨立訊號資料檔一個都不會被自動清掉：":
        "Old backups saved aside and backups of unreadable autosaves ({pattern}; open them with \"Import Settings\" and check the signals in them "
        "before deleting). While these files exist, none of the standalone signal data files in the frozen folder is cleaned up automatically:",
    "讀不了的版本備份（有它在，frozen 資料夾裡沒人用到的獨立訊號資料檔就不會被自動清掉；修好或刪掉它之後才照常清）：":
        "Version backups that cannot be read (while they exist, unused standalone signal data files in the frozen folder are not cleaned up "
        "automatically; cleaning resumes once they are fixed or deleted):",
    "自動存檔已經存好了；這個提示 {sec} 秒後會自己關掉，DSV 接著關閉。":
        "The autosave has already been written; this notice closes by itself after {sec} seconds and DSV then closes.",
    "這次的變更沒有存（自動存檔寫不進去，你選了照樣關閉）；這個提示 {sec} 秒後會自己關掉，DSV 接著關閉。":
        "This session's changes were not saved (the autosave could not be written and you chose to close anyway); this notice closes by itself "
        "after {sec} seconds and DSV then closes.",
    # F-U13P（2026-10-30 09:3x 使用者決定）：自動存檔讀不了、問的是別的版本留的備份、選「從空的開始」→ 那份先另存一份
    "選「從空的開始」時，{new} 版留的這份備份會先自動另存一份在同一個資料夾（{pattern}；之後可以用「匯入設定」開啟它，那份還在的期間 frozen 資料夾裡的獨立訊號資料檔一個都不清，每次關閉 DSV 時都會提醒它還在），不用自己複製。":
        "With Start Empty, this backup kept by version {new} is first copied automatically into the same folder ({pattern}; you can open the copy "
        "with \"Import Settings\" later; while it exists no standalone signal data file in the frozen folder is cleaned up, and every time you close "
        "DSV you are reminded that it is still there), so there is no need to copy it yourself.",
    "自動存檔讀不了：問到的備份另存一份": "Autosave unreadable: the backup asked about was copied aside",
    "自動存檔讀不了：問到的備份另存失敗": "Autosave unreadable: copying aside the backup asked about failed",
    "選了「從空的開始」：問到的那份備份（{ver} 版寫的，{when}）已另存在：{path}":
        "You chose Start Empty: the backup asked about (written by version {ver}, {when}) has been copied to: {path}",
    "要找回裡面的工作階段，用「匯入設定」開啟它。只要自動存檔旁邊還有任何一份備份（{pattern}），frozen 資料夾裡的獨立訊號資料檔就一個都不會被自動清掉（不管有沒有人用到）——請先匯入、確認訊號都回來了再刪它（一刪掉，只有它用到的獨立訊號資料就會被清掉；搬到別的資料夾、或改成不符合上面樣式的名字，也一樣不算備份）。不需要了就把這些備份都刪掉，之後才會照常自動清掉沒人用到的檔。":
        "To get the session in it back, open it with \"Import Settings\". As long as any backup remains next to the autosave ({pattern}), no "
        "standalone signal data file in the frozen folder is cleaned up automatically (used or not) — import it first and check that the signals "
        "are back before deleting it (once it is deleted, the standalone signal data only it uses is cleaned up; moving it to another folder or "
        "renaming it so it no longer matches the pattern above also stops it counting as a backup). When you no longer need these backups, delete "
        "them all; only then are unused files cleaned up automatically again.",
    "問到的備份已另存一份": "The backup asked about was copied aside",
    "問到的 {ver} 版備份已另存在 {path}（詳見對話框）": "The version {ver} backup asked about was copied to {path} (see the dialog)",
    "選了「從空的開始」：問到的那份備份（{ver} 版寫的，{when}）要先另存一份，但另存失敗（{reason}）：它照舊留在原處（{path}），這次開著的期間不會被刪掉；每次寫自動存檔之前都會再試一次另存。":
        "You chose Start Empty: the backup asked about (written by version {ver}, {when}) had to be copied aside first, but copying failed "
        "({reason}): it stays where it is ({path}) and is not deleted while DSV stays open; each time the autosave is written, copying it is tried again.",
    "問到的備份另存失敗": "Copying aside the backup asked about failed",
    "問到的 {ver} 版備份另存失敗，這次開著的期間不刪它（詳見對話框）":
        "Copying aside the version {ver} backup asked about failed; it is not deleted while DSV stays open (see the dialog)",
    # 第 2 輪修正（2026-10-30 14:xx、10-31 15:3x 使用者決定）：關閉時的提醒（C1 也跳、每類最多列 12 個、④ 另存還欠著的備份）、F-R2D2N 另存失敗記在磁碟、下次開啟先補做
    "（詳見對話框）": " (see the dialog)",
    "……還有 {k} 個（都在這個資料夾裡：{folder}）": "… and {k} more (all in this folder: {folder})",
    "另存還欠著的備份（上次另存失敗、這次再試也失敗：另存成功之前 DSV 不重寫、不刪它；讓它所在的資料夾可以寫入之後再開啟 DSV 會再試）：":
        "Backups whose copy aside is still owed (copying failed last time and failed again this time: DSV neither rewrites nor deletes them until "
        "the copy succeeds; make their folder writable and start DSV again to retry):",
    "開啟時的問句還開著就關閉了：這次什麼都沒存（自動存檔、備份、凍結檔都不動，上次的工作階段下次開啟照樣還原）；這個提示 {sec} 秒後會自己關掉，DSV 接著關閉。":
        "DSV was closed while the start-up question was still open: nothing was saved this time (the autosave, the backups and the frozen files are "
        "untouched; the last session is restored as usual next time); this notice closes by itself after {sec} seconds and DSV then closes.",
    "開啟時：欠的備份另存已補上": "At start-up: the owed backup copy was made",
    "開啟時：欠的備份另存還是失敗": "At start-up: the owed backup copy failed again",
    "上次開著時另存失敗、欠著的備份這次補上了：{path}（原本那份：{src}）":
        "The backup copy that failed last time and was still owed has now been made: {path} (the original: {src})",
    "上次欠的另存這次還是失敗（{reason}）：那份照舊不動（不重寫、不刪），讓它所在的資料夾可以寫入之後再開啟 DSV 會再試：{path}":
        "The copy owed since last time failed again ({reason}): that backup stays untouched (neither rewritten nor deleted); make its folder "
        "writable and start DSV again to retry: {path}",
    "欠的備份另存還是失敗": "The owed backup copy failed again",
    "上次欠的備份另存還是失敗，這次不動它（詳見對話框）": "The backup copy owed since last time failed again; it is left untouched this time (see the dialog)",
    "欠的備份另存已補上": "The owed backup copy was made",
    "上次欠的備份另存已補上：{path}（詳見對話框）": "The backup copy owed since last time was made: {path} (see the dialog)",
    # matfile.py 的固定訊息（英文介面讀到 -v7.3 的 .mat 時錯誤視窗內文以前是中文；第二輪 Windows 驗證的觀察）
    "這是 MATLAB -v7.3（HDF5）格式，還不支援；請在 MATLAB 用 save(filename, ..., '-v7') 另存":
        "This is a MATLAB -v7.3 (HDF5) file, which is not supported yet; please re-save it in MATLAB with save(filename, ..., '-v7')",
}
