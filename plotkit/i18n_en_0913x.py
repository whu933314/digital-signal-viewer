# -*- coding: utf-8 -*-
"""English catalog part — 0.9.13 B1（來源檔案不在的佔位訊號）與 B3（這版寫的自動存檔備份、被舊版改寫過的提示；0.9.14 起每個版本各留一份備份）。
Keys are the Traditional Chinese source strings in signal_viewer.py."""

CATALOG = {
    # --- B1：來源檔案暫時不在 → 佔位訊號 ---
    "檔案不在": "file missing",
    "等來源的檔案": "waiting for source file",
    "重新載入檔案不在的訊號": "Reload Signals with Missing Files",
    "沒有檔案不在的訊號": "No signal has a missing file",
    "重新載入 {n} 條檔案不在的訊號": "Reload {n} signals with missing files",
    "已重新載入 {n} 條訊號（檔案回來了）：{names}": "Reloaded {n} signals (the files are back): {names}",
    "檔案回來了：已重新載入 {n} 條訊號（{names}）": "Files are back: reloaded {n} signals ({names})",
    "{k} 條訊號的檔案還是不在：{names}": "the files of {k} signals are still missing: {names}",
    "{k} 條訊號的檔案在卻讀不了：{names}（{reason}）": "the files of {k} signals exist but cannot be read: {names} ({reason})",
    "；檔案回來了，重新載入 {k} 條訊號": "; the files are back, reloaded {k} signals",
    "；來源的檔案不在，等檔案回來再算": "; the source file is missing, it is computed once the file is back",
    "（{k} 條的檔案不在）": " ({k} with missing files)",
    "（{k} 條的檔案不在，沒有匯出）": " ({k} with missing files were not exported)",
    "沒有訊號可匯出：{k} 條的檔案不在": "Nothing to export: the files of {k} signals are missing",
    "沒有訊號可匯出：{k} 條的檔案讀不了": "Nothing to export: the files of {k} signals cannot be read",
    "沒有訊號可匯出：{n} 條的檔案不在、{k} 條的檔案讀不了": "Nothing to export: the files of {n} signals are missing and {k} cannot be read",
    "（{k} 條的檔案讀不了，沒有匯出）": " ({k} with unreadable files were not exported)",
    "（{n} 條的檔案不在、{k} 條的檔案讀不了，沒有匯出）": " ({n} with missing files and {k} with unreadable files were not exported)",
    "；來源的檔案讀不了，等檔案修好再算": "; the source file cannot be read, it is computed once the file is fixed",
    "有訊號的來源檔案不在": "Source files are missing",
    "{n} 條訊號的來源檔案不在（留在清單等檔案回來；詳見對話框）":
        "The source files of {n} signals are missing (kept in the list until the files are back; see the dialog)",
    "開啟：{n} 條訊號的來源檔案不在（留在清單等檔案回來）": "Start: the source files of {n} signals are missing (kept in the list)",
    "{row}——{path}": "{row} — {path}",
    "上次的工作階段有 {n} 條訊號的來源檔案現在不在（外接磁碟沒接上？檔案搬走了？）。它們留在「已繪訊號」清單裡（灰字、Fmt 欄寫「檔案不在」）但不畫；以它們為來源的衍生訊號（I/Q 幅度／相位／FM、前處理結果）、所有參數和 panel 的設定也都留著等資料，自動存檔照樣記著它們：":
        "The source files of {n} signals of the last session are missing right now (external disk not connected? file moved?). They stay in the "
        "Plotted Signals list (greyed out, Fmt column \"file missing\") but are not drawn; the derived signals built on them (I/Q magnitude / phase / FM, "
        "Preprocess results), all their parameters and the panel settings are kept, waiting for the data, and the autosave keeps recording them:",
    "檔案回來之後會自動讀進來（「資料夾內容改變時自動重新整理」開著時每隔幾秒看一次；下次開啟也會再試），也可以在「已繪訊號」清單按右鍵「重新載入檔案不在的訊號」。":
        "Once the files are back they are loaded automatically (checked every few seconds while \"Refresh automatically when the folder changes\" is on; "
        "the next start tries again too); you can also right-click the Plotted Signals list and choose \"Reload Signals with Missing Files\".",
    "找不到檔案的訊號先留在清單（灰字、不畫；以它們為來源的衍生訊號和參數也都留著），檔案回來會自動讀進來，也可以在清單按右鍵「重新載入檔案不在的訊號」：\n":
        "Signals whose files cannot be found stay in the list (greyed out, not drawn; the derived signals built on them and their parameters are kept too); "
        "they are loaded automatically once the files are back, or right-click the list and choose \"Reload Signals with Missing Files\":\n",
    # --- B3：這版寫的自動存檔備份、被舊版改寫過 ---
    "上次的自動存檔被舊版改寫過": "The autosave was rewritten by an older version",
    "現在的自動存檔是 {old} 版寫的（{when_old}）": "The current autosave was written by version {old} ({when_old})",
    "現在的自動存檔沒有版本號（很舊的版本寫的；{when_old}）": "The current autosave has no version number (written by a very old version; {when_old})",
    "，這版留的備份是 {new} 版寫的（{when_new}）：中間用舊版開過又關掉。舊版不認得的設定（前處理結果與參數、每張 panel 的軸名稱／標題、眼圖與錯誤率比對的預設、外觀主題（Sony／Apple 風）…）可能已經被它丟掉。":
        ", while the backup kept by this version was written by version {new} ({when_new}): an older version was opened and closed in between. "
        "Settings the old version does not know (Preprocess results and parameters, each panel's axis names / titles, the Eye Diagram and Error Rate "
        "defaults, the Sony / Apple interface theme…) may have been dropped by it.",
    "備份：{path}": "Backup: {path}",
    "用備份還原：還原這版留的備份（舊版開過之後做的改動不在裡面）。":
        "Restore the Backup: restores the backup kept by this version (changes made after the old version was opened are not in it).",
    "用現在的檔：照舊還原現在的自動存檔（被舊版丟掉的設定不會回來）。":
        "Use the Current File: restores the current autosave as usual (the settings dropped by the old version do not come back).",
    "不管選哪一個，這次關閉時自動存檔和備份都會被這版重寫。選「用現在的檔」時，現在這份備份會先自動另存一份在同一個資料夾（{pattern}；之後可以用「匯入設定」開啟它，那份還在的期間 frozen 資料夾裡的獨立訊號資料檔一個都不清），不用自己複製。":
        "Either way, closing this time rewrites both the autosave and the backup with this version. With Use the Current File, the current backup is first "
        "saved as a copy in the same folder automatically ({pattern}; it can be opened later with Import Settings, and while it exists no "
        "independent-signal data file in the frozen folder is cleaned up) — no need to copy it yourself.",
    # --- 0.9.14（2026-10-29 18:1x 使用者決定）：每個版本各留一份自己的備份 <名稱>.backup-<版本>.json，留最近 3 個版本；問的不是這版自己的備份時 ---
    "，比它新的備份是 {new} 版留的（{when_new}；這版沒有自己的備份可用）：中間用舊版開過又關掉。舊版不認得的設定（前處理結果與參數、每張 panel 的軸名稱／標題、眼圖與錯誤率比對的預設、外觀主題（Sony／Apple 風）…）可能已經被它丟掉。":
        ", while the newer backup was kept by version {new} ({when_new}; this version has no usable backup of its own): an older version was opened "
        "and closed in between. Settings the old version does not know (Preprocess results and parameters, each panel's axis names / titles, the Eye "
        "Diagram and Error Rate defaults, the Sony / Apple interface theme…) may have been dropped by it.",
    "用備份還原：還原 {new} 版留的這份備份（舊版開過之後做的改動不在裡面）。":
        "Restore the Backup: restores this backup kept by version {new} (changes made after the old version was opened are not in it).",
    "不管選哪一個，這次關閉時這版會重寫自動存檔、寫一份這版自己的備份（{new} 版留的這份不改寫）。選「用現在的檔」時，這份備份也會先自動另存一份在同一個資料夾（{pattern}；之後可以用「匯入設定」開啟它，那份還在的期間 frozen 資料夾裡的獨立訊號資料檔一個都不清），不用自己複製。":
        "Either way, closing this time rewrites the autosave and writes this version's own backup (this backup kept by version {new} is not rewritten). "
        "With Use the Current File, this backup is also first saved as a copy in the same folder automatically ({pattern}; it can be opened later with "
        "Import Settings, and while it exists no independent-signal data file in the frozen folder is cleaned up) — no need to copy it yourself.",
    "其他也比現在的自動存檔新的備份（這版不改寫它們；要用的話，用「匯入設定」開啟）：":
        "Other backups that are also newer than the current autosave (this version does not rewrite them; to use one, open it with Import Settings):",
    "{ver} 版留的（{when}）：{path}": "kept by version {ver} ({when}): {path}",
    "{ver} 版留的備份讀不了（{reason}），改還原現在的自動存檔":
        "The backup kept by version {ver} cannot be read ({reason}); restoring the current autosave instead",
    "{ver} 版留的備份套用不了（{raw}），改還原現在的自動存檔":
        "The backup kept by version {ver} could not be applied ({raw}); restoring the current autosave instead",
    "自動存檔讀不了：用 {ver} 版留的備份還原": "Autosave unreadable: restored the backup kept by version {ver}",
    "上次的自動存檔讀不回來（另存在 {bad}）；已用 {ver} 版留的備份還原（{path}）":
        "The autosave could not be read (saved as {bad}); restored the last session from the backup kept by version {ver} ({path})",
    "上次的自動存檔讀不回來（另存備份失敗，原本的檔留在原處）；已用 {ver} 版留的備份還原（{path}）":
        "The autosave could not be read (backing it up failed, the file stays where it is); restored the last session from the backup kept by "
        "version {ver} ({path})",
    "用 {ver} 版留的備份還原上次的工作階段": "Restored the last session from the backup kept by version {ver}",
    "已用 {ver} 版留的備份還原上次的工作階段（{path}）；這次關閉時會重寫自動存檔、寫一份這版自己的備份":
        "Restored the last session from the backup kept by version {ver} ({path}); closing rewrites the autosave and writes this version's own backup",
    "用備份還原：照 {new} 版留的這份備份還原上次的工作階段（這版沒有自己的備份可用；這版不改寫這份備份，關閉時另外寫一份這版自己的）。":
        "Restore the Backup: restore the last session from this backup kept by version {new} (this version has no usable backup of its own; this "
        "version does not rewrite this backup and writes its own when closing).",
    "從空的開始：這次從空的開始（備份檔照舊留著：這版不改寫它；這次關閉時重寫自動存檔、寫一份這版自己的備份）。":
        "Start Empty: start with an empty session this time (the backup file stays: this version does not rewrite it; closing this time rewrites the "
        "autosave and writes this version's own backup).",
    "{new} 版留的備份（{when_new}）讀得了：{path}": "The backup kept by version {new} ({when_new}) can be read: {path}",
    "其他讀得了的備份（這版不改寫它們；要用的話，用「匯入設定」開啟）：":
        "Other readable backups (this version does not rewrite them; to use one, open it with Import Settings):",
    # --- 0.9.14（2026-10-29 22:1x 使用者決定）：B3／U13 問「最後一次工作」的那份（存檔時間最新）；這版自己的（比較早寫的）另外寫出來、重寫之前先另存 ---
    "檔案的修改時間 {time}": "file modified {time}",
    "，最後一次工作留的備份是 {new} 版寫的（{when_new}；比這版自己的備份（{when_own}）新）：中間用舊版開過又關掉。舊版不認得的設定（前處理結果與參數、每張 panel 的軸名稱／標題、眼圖與錯誤率比對的預設、外觀主題（Sony／Apple 風）…）可能已經被它丟掉。":
        ", while the backup from the most recent work was written by version {new} ({when_new}; newer than this version's own backup from {when_own}): "
        "an older version was opened and closed in between. Settings the old version does not know (Preprocess results and parameters, each panel's "
        "axis names / titles, the Eye Diagram and Error Rate defaults, the Sony / Apple interface theme…) may have been dropped by it.",
    "用備份還原：還原 {new} 版留的這份備份（舊版開過之後做的改動不在裡面；{new} 版不認得、只有這版才有的設定可能不在裡面）。":
        "Restore the Backup: restores this backup kept by version {new} (changes made after the old version was opened are not in it; settings only "
        "this version has, which version {new} does not know, may be missing from it).",
    "不管選哪一個，這次關閉時這版會重寫自動存檔和這版自己的備份（{new} 版留的這份不改寫）。這版自己的備份重寫之前會先自動另存一份在同一個資料夾（{pattern}）；選「用現在的檔」時，{new} 版留的這份也會先另存一份。之後可以用「匯入設定」開啟它們，那些檔還在的期間 frozen 資料夾裡的獨立訊號資料檔一個都不清，不用自己複製。":
        "Either way, closing this time rewrites the autosave and this version's own backup (this backup kept by version {new} is not rewritten). This "
        "version's own backup is first saved as a copy in the same folder automatically ({pattern}); with Use the Current File, this backup kept by "
        "version {new} is copied as well. They can be opened later with Import Settings, and while those copies exist no independent-signal data file "
        "in the frozen folder is cleaned up — no need to copy anything yourself.",
    "這版自己的備份（{ver} 版，{when}）：{path}": "This version's own backup (version {ver}, {when}): {path}",
    "用備份還原：照 {new} 版留的這份備份還原上次的工作階段（它比這版自己的備份新；{new} 版不認得、只有這版才有的設定可能不在裡面。這版不改寫這份備份）。":
        "Restore the Backup: restore the last session from this backup kept by version {new} (it is newer than this version's own backup; settings only "
        "this version has, which version {new} does not know, may be missing from it. This version does not rewrite this backup).",
    "從空的開始：這次從空的開始（{new} 版留的這份備份照舊留著，這版不改寫它）。":
        "Start Empty: start with an empty session this time (this backup kept by version {new} stays as it is; this version does not rewrite it).",
    "不管選哪一個，這次關閉時這版會重寫自動存檔和這版自己的備份；這版自己的備份重寫之前會先自動另存一份在同一個資料夾（{pattern}），之後可以用「匯入設定」開啟它，那份還在的期間 frozen 資料夾裡的獨立訊號資料檔一個都不清，不用自己複製。":
        "Either way, closing this time rewrites the autosave and this version's own backup; this version's own backup is first saved as a copy in the "
        "same folder automatically ({pattern}); it can be opened later with Import Settings, and while it exists no independent-signal data file in the "
        "frozen folder is cleaned up — no need to copy it yourself.",
    "開啟時：這版自己的舊備份另存一份": "At start-up: saved a copy of this version's old backup",
    "開啟時：這版自己的舊備份另存失敗": "At start-up: saving a copy of this version's old backup failed",
    "這版自己的備份（{when}）不是這次還原的那份，這次關閉時會被重寫：它現在的內容已先另存在：{path}":
        "This version's own backup ({when}) is not the one restored this time and will be rewritten when closing: its current content was first saved as: {path}",
    "這版自己的備份（{when}）不是這次還原的那份，重寫之前要先另存一份，但另存失敗（{reason}）：這次不重寫它（照舊留在原處：{path}），它用到的獨立訊號資料檔也不會被清掉；這次開著的期間，每次寫自動存檔之前都會再試一次另存。":
        "This version's own backup ({when}) is not the one restored this time and has to be copied before it is rewritten, but that failed ({reason}): "
        "this time it is not rewritten (it stays where it is: {path}) and the independent-signal data files it uses are not cleaned up; while DSV stays "
        "open, the copy is tried again before every autosave.",
    "這版自己的舊備份已另存在 {path}（詳見對話框）": "This version's old backup was saved as {path} (see the dialog)",
    "這版自己的舊備份另存失敗，這次不重寫它（詳見對話框）": "Saving a copy of this version's old backup failed, it is not rewritten this time (see the dialog)",
    # --- R2-D2（2026-10-29 13:0x 使用者決定）：B3 選「用現在的檔」→ 舊備份自動另存一份（U15 認得的 .bad*.json）---
    "自動存檔被舊版改寫過：舊備份另存一份": "Autosave rewritten by an older version: saved a copy of the old backup",
    "自動存檔被舊版改寫過：舊備份另存失敗": "Autosave rewritten by an older version: saving a copy of the old backup failed",
    "選了「用現在的檔」：被舊版改寫之前的那份備份（{ver} 版寫的，{when}）已另存在：{path}":
        "Use the Current File was chosen: the backup from before the older version rewrote the autosave (written by version {ver}, {when}) was saved as: {path}",
    "要找回裡面的工作階段（舊版丟掉的前處理結果與參數、每張 panel 的軸名稱／標題…），用「匯入設定」開啟它。只要自動存檔旁邊還有任何一份備份（{pattern}），frozen 資料夾裡的獨立訊號資料檔就一個都不會被自動清掉（不管有沒有人用到）——請先匯入、確認訊號都回來了再刪它（一刪掉，只有它用到的獨立訊號資料就會被清掉；搬到別的資料夾、或改成不符合上面樣式的名字，也一樣不算備份）。不需要了就把這些備份都刪掉，之後才會照常自動清掉沒人用到的檔。":
        "To get that session back (the Preprocess results and parameters, each panel's axis names / titles… the old version dropped), open it with "
        "Import Settings. As long as any backup ({pattern}) sits next to the autosave, no independent-signal data file in the frozen folder is cleaned up "
        "automatically (whether used or not) — import it first and check that the signals are back before deleting it (once it is deleted, the "
        "independent-signal data only it uses is cleaned up; moving it to another folder or renaming it so it no longer matches the pattern above counts "
        "as deleting it too). When you no longer need the backups, delete them all; after that, unused files are cleaned up automatically again.",
    "舊備份已另存一份": "A copy of the old backup was saved",
    "舊備份另存失敗": "Saving a copy of the old backup failed",
    "用現在的檔：舊備份已另存在 {path}（詳見對話框）": "Used the current file: the old backup was saved as {path} (see the dialog)",
    "用現在的檔：舊備份另存失敗，這次不重寫它（詳見對話框）": "Used the current file: saving a copy of the old backup failed, it is not rewritten this time (see the dialog)",
    "選了「用現在的檔」：被舊版改寫之前的那份備份要先另存一份，但另存失敗（{reason}）：這次不重寫那份備份（照舊留在原處：{path}），它用到的獨立訊號資料檔也不會被清掉；這次開著的期間，每次寫自動存檔之前都會再試一次另存。":
        "Use the Current File was chosen: the backup from before the older version rewrote the autosave has to be copied first, but that failed "
        "({reason}): this time that backup is not rewritten (it stays where it is: {path}) and the independent-signal data files it uses are not cleaned "
        "up; while DSV stays open, the copy is tried again before every autosave.",
    # --- C6 × U13（第三輪驗證 R3-1／R3-D1／R3C-2）：備份是比這版新的版本寫的時，問句照實說「這版不會改寫它」---
    "用備份還原：照這份備份還原上次的工作階段（它是比這版新的 {new} 版寫的，這版不認得的設定會略過；這版不會改寫這份備份）。":
        "Restore the Backup: restore the last session from this backup (it was written by version {new}, newer than this one; settings this version "
        "does not know are skipped; this version does not rewrite this backup).",
    "上次的自動存檔讀不回來（另存在 {bad}）；已用比這版新的 {new} 版寫的備份還原（{path}；這版不會改寫它）":
        "The autosave could not be read (saved as {bad}); restored the last session from the backup written by version {new}, newer than this one "
        "({path}; this version does not rewrite it)",
    "上次的自動存檔讀不回來（另存備份失敗，原本的檔留在原處）；已用比這版新的 {new} 版寫的備份還原（{path}；這版不會改寫它）":
        "The autosave could not be read (backing it up failed, the file stays where it is); restored the last session from the backup written by "
        "version {new}, newer than this one ({path}; this version does not rewrite it)",
    "從空的開始：這次從空的開始（備份檔照舊留著：它是比這版新的 {new} 版寫的，這版不會改寫它；這次關閉時只重寫自動存檔）。":
        "Start Empty: start with an empty session this time (the backup file stays: it was written by version {new}, newer than this one, and this "
        "version does not rewrite it; closing this time rewrites only the autosave).",
    "用備份還原": "Restore the Backup",
    "用現在的檔": "Use the Current File",
    "自動存檔被舊版改寫過：用備份還原": "Autosave rewritten by an older version: restore the backup",
    "自動存檔被舊版改寫過：用現在的檔": "Autosave rewritten by an older version: use the current file",
    "用這版留的備份還原上次的工作階段": "Restored the last session from this version's backup",
    "已用這版留的備份還原上次的工作階段（{path}）；這次關閉時會重寫自動存檔和備份":
        "Restored the last session from this version's backup ({path}); closing rewrites the autosave and the backup",
    "這版留的備份讀不了（{reason}），改還原現在的自動存檔": "This version's backup cannot be read ({reason}); restoring the current autosave instead",
    "這版留的備份套用不了（{raw}），改還原現在的自動存檔": "This version's backup could not be applied ({raw}); restoring the current autosave instead",
    # --- B1×B4（2026-10-28 使用者決定）：刪掉佔位來源時等資料的 I/Q 衍生訊號一起移除 ---
    "；{where} 的 {n} 條等資料的 I/Q 衍生訊號一起移除": "; the {n} I/Q derived signal(s) in {where} waiting for data were removed with it",
    "{where} 的 {n} 條等資料的 I/Q 衍生訊號會一起移除": "The {n} I/Q derived signal(s) in {where} waiting for data will be removed with it",
    # --- B1 重載時機（2026-10-28 使用者決定）：檔案回來後再拖進來／帶參數啟動指定 → 立刻重新載入 ---
    "拖進來的檔案回來了：已重新載入 {n} 條訊號（{names}）": "The dropped file is back: reloaded {n} signals ({names})",
    "啟動參數的檔案回來了：已重新載入 {n} 條訊號（{names}）": "The start-up argument's file is back: reloaded {n} signals ({names})",
    # --- 0.9.13 深度審查第一輪的修正（2026-10-29 使用者決定）：開啟時來源檔案在卻讀不了 → 一樣留佔位 ---
    "讀不了": "unreadable",
    "（{k} 條的檔案讀不了）": " ({k} with unreadable files)",
    "檔案在卻讀不了的訊號也先留在清單（灰字、Fmt 欄寫「讀不了」、不畫；以它們為來源的衍生訊號和參數也都留著），把檔案修好之後在清單按右鍵「重新載入檔案不在的訊號」就讀進來：\n":
        "Signals whose files exist but cannot be read are kept in the list too (greyed out, Fmt column \"unreadable\", not drawn; the derived signals built on "
        "them and all parameters are kept); after fixing the file, right-click the list and choose \"Reload Signals with Missing Files\":\n",
    "{key}（{path}）：{reason}": "{key} ({path}): {reason}",
    "上次的工作階段有 {n} 條訊號的來源檔案在、但讀不了（欄位名稱改了？沒有讀取權限？格式不對？）。它們一樣留在「已繪訊號」清單裡（灰字、Fmt 欄寫「讀不了」）但不畫；以它們為來源的衍生訊號、所有參數和 panel 的設定也都留著，自動存檔照樣記著它們：":
        "The source files of {n} signals of the last session exist but cannot be read (column renamed? no read permission? wrong format?). They stay in "
        "the Plotted Signals list too (greyed out, Fmt column \"unreadable\") but are not drawn; the derived signals built on them, all parameters and the "
        "panel settings are kept, and the autosave keeps recording them:",
    "{row}——{path}：{reason}": "{row} — {path}: {reason}",
    "把檔案修好之後，在「已繪訊號」清單按右鍵「重新載入檔案不在的訊號」（或把那個檔再拖進視窗）就會讀進來；「資料夾內容改變時自動重新整理」開著時，檔案一改過也會自動再試。":
        "After fixing the file, right-click the Plotted Signals list and choose \"Reload Signals with Missing Files\" (or drop the file into the window "
        "again) to load it; with \"Refresh automatically when the folder changes\" on, a changed file is also retried automatically.",
    "開啟：{n} 條訊號的來源檔案在卻讀不了（留在清單等修好）": "Start: the source files of {n} signals cannot be read (kept in the list until fixed)",
    "有訊號的來源檔案不在或讀不了": "Source files are missing or unreadable",
    "{n} 條訊號的來源檔案不在、{k} 條在卻讀不了（留在清單；詳見對話框）":
        "The source files of {n} signals are missing and {k} cannot be read (kept in the list; see the dialog)",
    "有訊號的來源檔案讀不了": "Source files cannot be read",
    "{k} 條訊號的來源檔案在卻讀不了（留在清單等修好；詳見對話框）":
        "The source files of {k} signals exist but cannot be read (kept in the list until fixed; see the dialog)",
    # --- 自動存檔讀不了（U13）而這版留的備份讀得了 → 問「用備份還原／從空的開始」（2026-10-29 使用者決定）---
    "上次的自動存檔讀不回來": "The autosave cannot be read",
    "從空的開始": "Start Empty",
    "上次的自動存檔讀不回來（檔案壞掉或被截斷）。": "The autosave cannot be read (the file is damaged or truncated).",
    "上次的自動存檔讀不回來。": "The autosave cannot be read.",
    "這版留的備份是 {new} 版寫的（{when_new}），讀得了：{path}": "The backup kept by this version was written by version {new} ({when_new}) and can be read: {path}",
    "用備份還原：照這版留的備份還原上次的工作階段（這版上次寫自動存檔時一起寫的那一份）。":
        "Restore the Backup: restore the last session from this version's backup (written together with the last autosave of this version).",
    "從空的開始：這次從空的開始（備份檔照舊留著；這次關閉時自動存檔和備份都會被這次的工作階段重寫——要留著它，請先把備份檔複製到別的地方，之後可以用「匯入設定」開啟）。":
        "Start Empty: start with an empty session this time (the backup file stays; closing this time rewrites the autosave and the backup with this "
        "session — to keep it, copy the backup file somewhere else first; it can be opened later with Import Settings).",
    "自動存檔讀不了：用這版留的備份還原": "Autosave unreadable: restored this version's backup",
    "上次的自動存檔讀不回來（另存在 {bad}）；已用這版留的備份還原（{path}）":
        "The autosave could not be read (saved as {bad}); restored the last session from this version's backup ({path})",
    "上次的自動存檔讀不回來（另存備份失敗，原本的檔留在原處）；已用這版留的備份還原（{path}）":
        "The autosave could not be read (backing it up failed, the file stays where it is); restored the last session from this version's backup ({path})",
    "上次的自動存檔讀不回來，選了從空的開始（讀不回來的檔：{path}）": "The autosave could not be read; started empty as chosen (the unreadable file: {path})",
    # --- 這版留的備份讀不了（照 U13 另存 .bad、U15 擋住清理）---
    "這版留的自動存檔備份讀不了：另存備份": "This version's autosave backup is unreadable: backed it up",
    "這版留的自動存檔備份讀不了：另存備份失敗": "This version's autosave backup is unreadable: backing it up failed",
    "這版留的自動存檔備份讀不回來（{reason}）：{path}": "The autosave backup kept by this version cannot be read ({reason}): {path}",
    "它另存了一份：{path}（這次關閉時備份會照常重寫）": "A copy of it was saved: {path} (the backup is rewritten as usual when closing this time)",
    "另存一份失敗（{reason}）：這次不重寫這份備份、frozen 資料夾裡的獨立訊號資料檔也一個都不清；讓那個資料夾可以寫入之後再開啟 DSV，會再試一次。":
        "Saving a copy failed ({reason}): this time the backup is not rewritten and no independent-signal data file in the frozen folder is cleaned up; "
        "make that folder writable and open DSV again to retry.",
    "這版留的自動存檔備份讀不回來": "This version's autosave backup cannot be read",
    "這版留的自動存檔備份讀不回來（詳見對話框）": "This version's autosave backup cannot be read (see the dialog)",
}
