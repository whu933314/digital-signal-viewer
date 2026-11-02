# Windows 手動檢查清單（v3.4，2026-10-22）

## 2026-10-21 已在一台 Windows 11 桌機上自動跑過的部分

環境：Windows 11 26200、Python 3.12.10（`C:\Users\<你>\AppData\Local\Programs\Python\Python312`）、numpy 2.4.4、matplotlib 3.10.9、Tk 8.6、Pillow 12.2；
專案複製到 `C:\Users\<你>\dsv_test\`（ssh 工作階段裡 Tk 視窗開得起來但不會真的顯示：1×1、未 mapped）。

- 第 1 步：`python signal_viewer.py --selftest > out.txt`、`python -m plotkit --selftest > out.txt` 都 exit 0、最後一行 `SELFTEST OK`；
  cp950 管線裡 `≈`／`≥` 變成 `\u2248`／`\u2265`，沒有中斷。`tk scaling` 1.333、96 px/in——那是當時 ssh 工作階段（沒有桌面、96 dpi）裡
  一般 Python 的數字；0.9.12 以前 DSV 本身也是 DPI-unaware。0.9.13 起 DSV 啟動時宣告 per-monitor DPI aware，有桌面時照螢幕的 DPI（見下一節）。
- 第 3～7、9 步的程式邏輯：`tests_gui_mac.py` 132/132、`tests_plotkit_gui_mac.py` 52/52（用 `set PYTHONIOENCODING=utf-8`、`TEMP` 指到測試目錄）。
  跑的時候發現 plotkit 清單的 ☑ 點擊用 `identify("region")`，視窗沒顯示時回 "nothing"，已改成只看欄與列；其餘沒有 Windows 專屬問題。
- 第 8 步（真的剪貼簿）：`pk.copy_figure_to_clipboard(fig)` → PowerShell 2.1 秒、`Clipboard.ContainsImage()` True、900×600，`%TEMP%` 沒留 `plotkit_clip_*`。
  貼進 Word／PowerPoint 要人看。
- 第 10 步：`pip install pyinstaller`（裝進使用者的 Python 3.12）→ `build_exe.bat` → `dist\SignalViewer.exe` 38.7 MB；`SignalViewer.exe --selftest` exit 0、全部 ok；
  `Start-Process` 啟動 GUI 後 20 秒：啟動器 7 MB ＋ 主程式 77 MB 都在、沒有錯誤 log。第一次啟動在 ssh 工作階段裡解壓縮超過 15 秒（Defender 掃描），之後較快。
- 還是要人用眼睛看的：第 4 步的真實滑鼠／觸控板滾輪與焦點行為、第 6 步圖例改名輸入框的位置、第 8 步貼進 Word、第 2 步視窗外觀與高 DPI。

## 2026-10-29（0.9.14）在使用者的 PC 有桌面驗過的高 DPI（W10）

環境：Windows 11、螢幕 1080×1920 直立、縮放 175%（有效 168 dpi）、工作區 1080×1836；有人登入桌面，用 `-LogonType Interactive` 的排程工作開真的視窗，
截圖用同一個 DPI-aware 行程（實體像素）。
- DSV（Python 與 exe）：`dpi_awareness=per-monitor-v2`、`tk scaling` 2.337、`winfo_fpixels('1i')` 168.3、介面倍數 1.753、字型 Microsoft JhengHei UI 21 px、
  圖 `device_pixel_ratio` 1.75（fig.dpi 175）；截圖裡字和線條是清楚的（不是點陣放大）。
- 主視窗 1026×1648（螢幕寬的 95%、高的 90%），最小 1026×1122；第一次出現後整個框放進工作區。
- 工具列：八個分頁鈕改成窄的才放得下（中文全部看得到；英文要左右捲動），首頁／訊號／量測／檢視四個分頁的內容比視窗寬 → 兩端 ◀ ▶ 捲動；
  0.9.13 那時「量測／檢視／匯出」分頁和「說明」區段直接被切掉、點不到。
- 分析視窗（頻譜 1026×1332、AM/PM/FM 與 GFSK 1026×1122、星座圖與眼圖 1026×1227、錯誤率比對 1026×806）、說明、診斷、偏好設定（縮到 1076 寬、確定鈕看得到）
  都整個在工作區裡；眼圖、星座圖、錯誤率比對的欄位列放不下就換行。0.9.13 那時這些視窗的寬高沒有照 DPI 放大（例如頻譜 1026×760，x 軸被切掉），
  星座圖／眼圖／錯誤率比對／偏好設定的右邊超出螢幕。
- 自動測試：`tests_gui_mac.py` 的 s63（合併時從 s57 改名，避免和別的 0.9.14 步驟撞號）、`tests_plotkit_gui_mac.py` 的 s98（窄工具列、欄位列換行的邏輯；Mac 上暫時打開驗）。

### 同一天驗過的 `--lang`／`DSV_LANG`（W11，2026-10-29 使用者決定：明確指定才蓋過還原的偏好；帶檔案參數時存成偏好，不帶時只管這一次）
Python（真的 `main()`，行程內讀語言）與 exe（截工具列分頁列和中／英參考圖比對）各跑 9 種情況，關閉（WM_CLOSE）後讀自動存檔的 `view.lang`，全部和決定一樣：
上次中文＋不帶參數 → 中文／存中文；上次中文＋`--lang en` → 英文／存中文；上次中文＋`--lang en 檔案` → 英文／存英文；上次中文＋`DSV_LANG=en`＋檔案 → 英文／存英文；
上次中文＋檔案 → 中文／存中文；上次英文＋檔案 → 英文／存英文；上次英文＋`--lang zh 檔案` → 中文／存中文；上次中文＋`DSV_LANG=en` → 英文／存中文；上次英文 → 英文／存英文
（檔案用「資料 夾 [1]\iq 中文.csv」：exe 也照 B2 先還原再加進來）。

### 同一天驗過的帶參數開啟＋來源檔案不在（W12）
上次的工作階段有 2 條訊號的來源檔案（「外接 碟 [1]\gone\iq.csv」）不在，再帶一個存在的檔（「args\clk 數位.txt」）開啟：Python（真的 `main()`，行程內讀狀態列）與
exe（狀態列截圖和 Python 那張比：差 0.0，和別的句子比 12.6）最後都是 B1 那句「2 條訊號的來源檔案不在（留在清單等檔案回來；詳見對話框）」，三條訊號都在（兩條佔位＋參數的檔），
提示視窗跳一次；關閉後自動存檔記著三條。0.9.13 第一輪 PC 看到的「啟動參數加入…」最後是修正前（f4e660e）的行為。兩種先後（提示先／啟動重畫先）在
`tests_gui_mac.py` s64（合併時從 s58 改名）不靠時間直接驗（突變 N80：拿掉 W12 的分支、或不管先後都排，都會失敗）。

### 2026-10-29／30 真的滑鼠在使用者的桌面上（0.9.14 第 7 項）
22:52 之後使用者在用這台 PC，23:05 起顯示改成 1920×1080 橫向 100%。真輸入（`SetCursorPos`／`mouse_event`，Tk 與 matplotlib 都照真的事件走）只在
使用者閒置 60～90 秒以上時做（`GetLastInputInfo`）；DSV 用 `tk scaling 2.333` 模擬 175%（圖的 device_pixel_ratio 1.75，W10 的座標換算全部走到）。
- 線上右鍵：沒有工具列模式、資料提示模式、平移模式 → 那條線的選單（有「刪除這條訊號」），清單只選那一條；放大模式 → 放大模式的選單。
- 資料提示模式點線 → 釘在預期的樣本；星座圖視窗點符號點 → 釘一個資料提示。
- 握把（座標區左邊的留白）把 P3 拖到最上面 → 順序 3、1、2；Ctrl+Z 回 1、2、3。
- 滾輪（panel 放不下、可以捲動時）：沒按鍵＝捲動不縮放；Shift＝只縮 x；Ctrl+Shift＝只縮 y；Ctrl＝兩軸；Alt＝不縮放；座標區外的留白＝捲動。和 README 一樣
  （上面第 4 步以前寫的「Ctrl+滾輪只縮 y」是錯的，已改）。
- 資料夾面板的 `hex\samples.txt` 拖到 P2 → 拖的時候狀態列「放開以加到 P2（…）」、放開加到 P2；拖到已經有同一個檔的圖上照規則略過。
- 水平資料游標：滑到線上 → 游標變 ↕；matplotlib 收到的座標（223, 197）和照圖算的（222.7, 196.8）一樣；按住往上拖 → 游標線跟到放開的位置。
- 原生的「匯入 CSV / MAT / WAV」對話框：關閉＝不加；選 `hex\samples.txt` 按開啟 → 加成新的 panel（用視窗訊息填檔名、按開啟，沒有送全域按鍵）。
- 沒有工具列模式：放大之後在空白處真的雙擊 → 回到原始視圖。
- 從另一個行程用 OLE 拖檔（pywin32 `DoDragDrop`、CF_HDROP，和檔案總管一樣）放進視窗：DSV 收到放下（那次拖的是已經畫著的檔，狀態列照規則寫「拖進來的檔案已經畫在 P2（已選取）」）；
  拖新檔到某張圖、到最後一張下面新增 panel 那兩次當時沒做完——照 2026-10-30 的決定這兩項需要真輸入，列為「沒測（使用者決定不用真輸入）」。
- 沒測到：exe 用真鍵盤改設定再關閉、重開（使用者決定不用真輸入；關閉→自動存檔→重開→還原那段用帶檔案參數開啟驗過，見下一節）、
  125%／150%／直立 175% 的實機畫面（不能改使用者的顯示設定；175% 只用行程內的 `tk scaling` 模擬）、注音等輸入法（不能切輸入法）、貼進 Word。
- 做過了（第 2、3 輪 Windows 驗證，2026-10-30～11-01）：`build_exe.bat onedir` 在 PC 上建置成功（rc 0、約 40 秒），`dist\SignalViewer\SignalViewer.exe` 單一行程、
  1.6～4.0 秒出視窗（單檔版 4～5 秒）；超過 260 字元的長路徑在這台 PC（`LongPathsEnabled=0`）打不開、提示說成「不認得或讀不了」／「檔案不在」，不掉資料
  （自動存檔照記、訊號留佔位；W14R2-4，1.0.0 還沒處理，留待之後的版本）。
- 事故紀錄：程式送的 Shift／Ctrl／Alt 作用到整個工作階段。這次有一次輸入被擋時 Shift 的放開沒送到，左 Shift 一直被當成按著（約 23:47～00:11，
  00:11 送放開、確認四個修飾鍵都放開）；微軟注音之下單獨按放 Shift 會切中／英。
- **2026-10-30 使用者決定：之後不再用程式送真的滑鼠／鍵盤輸入**（`SendInput`、`mouse_event`、`keybd_event`、`SetCursorPos`、pyautogui／pywinauto 的真輸入都不用）：
  改用行程內的 Tk 事件、視窗訊息；需要真輸入才能驗的項目列為「沒測（使用者決定不用真輸入）」。測試用的排程工作也不能在使用者的桌面上跳出主控台視窗。

## 原始清單

Mac 上只能做程式碼審查與推理，以下 10 步請在真的 Windows 10/11 上跑一次（專案放在例如 `C:\Users\<你>\digital-signal-viewer`）。
每步後面是預期結果；不符的請把畫面或訊息記下來。

1. **Selftest（主控台與管線）**
   ```
   cd C:\Users\<你>\digital-signal-viewer
   python signal_viewer.py --selftest        & echo %errorlevel%
   python -m plotkit --selftest              & echo %errorlevel%
   python signal_viewer.py --selftest > out.txt & echo %errorlevel%
   ```
   三個都要 `0`，前兩個最後一行 `SELFTEST OK`，`out.txt` 最後一行也是 `SELFTEST OK`（導到檔案時 cp950 編不出的字會變 `\u2248` 這種寫法，不會中斷）。
   另外記下 `python -c "import tkinter;r=tkinter.Tk();print(r.tk.call('tk','scaling'),r.winfo_fpixels('1i'));r.destroy()"` 的輸出
   （這行是沒宣告 DPI 的一般 Python：`1.333 96.0` = 系統沒把這個程式當成 DPI-aware；`2.0 144.0` 之類表示 DPI-aware）。
   DSV 本身（0.9.13 起，2026-10-29 使用者決定 W10）啟動時宣告 per-monitor DPI aware：在 DSV 裡按 `?` 看 `scaling`，175% 的螢幕應該是 2.33 左右（168 dpi）、
   字和線條清晰，主視窗的最小尺寸不超過螢幕。
2. **啟動與自動還原**：`python signal_viewer.py samples` → 視窗出現（小螢幕會自動縮到 95%；高 DPI 的螢幕起始大小照比例放大、不超過工作區的寬 95%／高 90%，整個框含標題列在工作區裡；右邊的圖剛好填滿畫布——0.9.13 在 175% 的螢幕上圖比畫布大 1.75 倍、只看得到上面一兩張，0.9.14 修正）、左側樹有 `digital/`、`hex/`、`sub dir [1]/`、`iq.csv`（可展開 adc i／adc q）；
   按 `?` → `tk 8.6.x`、`backend=TkAgg`、`frozen=False`、`scaling=…`；加入一條訊號後關閉 → `%USERPROFILE%\.signal_viewer_last.json` 存在；
   不帶參數再開 → 自動還原。
3. **CSV 匯入**：匯入 CSV… → `samples\iq.csv` → 對話框列出 adc i／adc q、建議平移 `-512`；「用估計值」→ `64M`、SPS 提示 `64`；加入 → 兩條在 panel 1，狀態列有 `P1: N 段差異`。
   把 CSV 複製到 `C:\Users\<你>\測試 資料夾\`（中文＋空白）再匯入一次 → 結果相同。
4. **滾輪**：先在「Plotted signals」清單點一列（清單有焦點），再把游標移到圖上不點：滾輪 → 兩軸放大，清單**不能**跟著捲；Shift+滾輪只縮 x；Ctrl+Shift+滾輪只縮 y；Ctrl+滾輪兩軸一起縮（明確要求縮放；以前這裡寫「Ctrl+滾輪只縮 y」是錯的，程式與 plotkit selftest 都是 Ctrl＋Shift 才只縮 y）；
   Alt+滾輪 → 右側畫布捲動、圖**不能**縮放；在分頁④選過「x 軸單位」後滾輪 → 單位**不能**跟著變；筆電觸控板兩指捲 → 逐步縮放不暴衝；
   空白處拖曳＝平移；雙擊空白／Home → 還原；工具列放大鏡（放大模式）開著時滾輪照樣縮放、一格 1.1 倍（MATLAB 的 zoom 模式也是）；
   工具列 🔍− 縮小鈕每按一下 1.5 倍、縮到全部顯示為止。
5. **資料提示**（預設開著；Shift＋點線條＝選取，不釘）：點線條 → 提示框三列：第一列訊號名稱 `iq:adc i`，再來 `X … us`、`Y …` 兩列（MATLAB 的 X／Y 兩列）；拖它；點一下再按 Delete → 消失；右鍵提示 → 刪除；F5 重畫後其餘提示仍在同一點；Ctrl+Z 可還原刪掉的提示。
6. **右鍵選單與圖例改名**：圖上線條右鍵 → 復原：<上一個動作>／重做、顏色…、線寬 ▸（0.5、1.0…12.0、自訂…）、線型 ▸、標記 ▸、標記大小 ▸（2、4…48、自訂…）、顯示／隱藏、Y 軸、重設樣式、複製訊號、插入垂直參考線（x = …）、插入文字…、還原視圖、只匯出這個 panel…、複製圖到剪貼簿；
   空白處右鍵 → 沒有樣式那段；清單右鍵 → 編輯名稱…／讀取格式／突波抑制／頻譜…；Esc 關選單。
   雙擊圖例文字 → 輸入框剛好蓋在文字上（偏到左上＝DPI 問題，回報 `?` 裡的 scaling），打字 Enter → 圖例與清單都改名；Esc 取消。
7. **Undo／Redo**：改顏色後，游標在圖上按 Ctrl+Z、游標在清單按 Ctrl+Z → 狀態列 `已復原：線色 …`；Ctrl+Y 與 Ctrl+Shift+Z → `已重做：線色 …`；↶／↷ 的提示寫 `復原：<動作> (Ctrl+Z)`、右鍵選單第一項 `復原：<動作>`；游標在 SPS 輸入框時 Ctrl+Z 只影響輸入框；↶／↷ 按鈕會隨之啟用／停用。
8. **複製圖到 Word**：按「複製圖到剪貼簿」→ 狀態列 `圖片已複製到剪貼簿`（約 2 秒內，不能閃出黑色命令視窗）→ Word／PowerPoint Ctrl+V 出現整張圖；這次複製的暫存檔 `%TEMP%\plotkit_clip_<這個 pid>_*.png` 不在（以前失敗留下的、關閉時提醒會列出的那些不算——2026-10-30 使用者決定留著）。
   失敗路徑：只改 PATH 已經做不出來（找不到 powershell 時 plotkit 會退回 `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe`，照樣複製成功——
   2026-10-30 第一輪驗證 W14-D1）；要驗失敗路徑就在 PATH 與 SystemRoot 都指到沒有 PowerShell 的資料夾的 cmd 裡啟動再複製 → 要看到
   `複製到剪貼簿失敗（…）；PNG 已存到 …` 而不是當掉；那個 PNG 一直留著（下一次複製也不刪），關閉 DSV 時「還有檔案沒處理」的提醒列出它的位置。
9. **圖片視窗存／開 JSON**：選兩條 → 複製到新圖片視窗 → 有 檔案／編輯／檢視／插入 選單；檔案 → 另存 JSON → `C:\Users\<你>\Documents\測試 圖.json`；檔案 → 新視窗 → 開啟 JSON → 線條、顏色、提示、風格、範圍都一樣；
   `python -m plotkit "C:\Users\<你>\Documents\測試 圖.json"` 可單獨開；視窗裡 Ctrl+S 存檔；主視窗 Ctrl+C 後到圖片視窗 Ctrl+V 可貼。
10. **打包**：`pip install pyinstaller pillow tkinterdnd2` → `build_exe.bat`（沒裝 tkinterdnd2 會警告，exe 就沒有拖放） → 每行 `[build_exe]` 正常顯示，最後 `[build_exe] done: dist\SignalViewer.exe`；雙擊 exe（第一次 10～20 秒、沒有主控台）→ 主視窗；
    「說明」→ README 有目錄（證明 `--add-data` 與 `_MEIPASS` 正常）；`?` → `frozen=True`、`plotkit 0.2.0`（證明 plotkit 有打包進去）；複製圖到剪貼簿正常、沒有視窗閃動；關閉後自動存檔有寫；
    `dist\SignalViewer.exe --selftest & echo %errorlevel%` → 不開視窗、`0`；`build_exe.bat onedir` → `dist\SignalViewer\SignalViewer.exe` 可跑、`dist\SignalViewer\_internal\README.md` 存在。
    關閉 onefile 的 exe：工作管理員／`Get-CimInstance Win32_Process -Filter "Name='SignalViewer.exe'"` 會看到兩個 SignalViewer.exe，`taskkill`（不加 `/F`）要送給子行程（ParentProcessId 是另一個的那個）；送給啟動器只回「成功」、程式照樣開著。2026-10-30 在使用者的 PC 實測（0.9.14 分支的 exe）：帶 `clk.txt` 開啟 → taskkill 子行程 → 1.3 秒內兩個都結束、自動存檔記著 clk.txt → 不帶參數重開 → 還原 → 一次 taskkill 兩個 PID → 2 秒內都結束、自動存檔再寫一次；每次啟動約 8～11 秒才出現視窗。

已在 Mac 上用程式碼審查確認過（不需要再測）：路徑與引號處理（含中文、空白、`'`）、PowerShell 參數（`-STA`、`CREATE_NO_WINDOW`、stdin/stdout/stderr 全部導走）、
字型 fallback（Windows 用 Arial＋Microsoft JhengHei）、Tk 綁定（Command／Button-2／Ctrl+點只在 macOS）、Alt 遮罩 0x20000、`event.modifiers` 名稱、PyInstaller 靜態匯入、所有 `open()` 都有指定編碼、Python 3.10～3.13 語法。

## v3.4 介面（MATLAB 主題）要在 Windows 看的
11. 深色主題下字型是 Microsoft JhengHei UI 12px（Tk 的預設家族），工具列大按鈕的中文兩行不會被截。
12. 高 DPI（125%／150%／175%）：0.9.13 起啟動時宣告 per-monitor DPI aware（`enable_windows_dpi_awareness`），Tk 的 scaling、圖示與圓角按鈕（依 `winfo_fpixels('1i')`）
    跟著螢幕放大，字與線條應該清晰；主視窗最小尺寸不超過螢幕，每個視窗第一次出現時整個放進工作區。視窗比工具列窄時：分頁鈕變窄（還放不下就左右捲動）、
    分頁內容兩端有 ◀ ▶ 捲動鈕、分析視窗的欄位列換行（175% 已在 2026-10-29 實機驗過，見上面）。125%／150% 沒有實機驗過（不能改使用者的顯示設定）；
    若還是模糊，記下「說明 → 診斷」裡的 scaling 與 DPI 宣告結果回報。
13. 「檢視 → 主題 → 淺色」切換後：所有視窗（含已開的說明／頻譜）顏色跟著換、圖重畫成淺色風格。
    1.0.0 起主題有八個（深色、淺色、Sony 風黑銀／深藍黑、Apple 風淺色／深色／深色·石墨橘／深色·純黑綠）：**八個主題各切一次**，看顏色、圓角、
    分頁列上看得出選中哪個分頁、下拉清單的顏色（換主題前打開過的清單留舊色是已知問題，見 README）；在 125%／150%／175% 實機縮放下看圓角是否清楚
    （Sony 黑銀 1 px、Apple 四個 5 px、其餘 3 px）。自動測試已在 PC 100%／175% 驗過八個主題的色票、圓角與切換不出錯，實機縮放的清晰度要人看。
14. 右鍵選單（tk.Menu）在 Windows 會吃 option database 的深色；macOS 是原生選單不受影響。

## 英文介面（v3.4）
15. `python signal_viewer.py --lang en`（或偏好設定 → 一般 → 語言 → English 後重開）：工具列、面板、對話框、狀態列、說明視窗（README.en.md）都是英文，沒有殘留中文。
16. 英文字型在 Windows 是 Microsoft JhengHei UI／Segoe UI 12px；大按鈕兩行英文不會被截。

## 只有 Windows 才看得到、要人看的（2026-10-23 補）
17. **尺規游標**：滑鼠移到刻度數字與軸線之間 → x 尺規 `sb_h_double_arrow`（↔）、y 尺規 `sb_v_double_arrow`（↕）（macOS 是 resizeleftright／resizeupdown）；
    拖曳只沿那個軸平移。資料游標（分析 → 資料游標）的線上也是 ↔。座標區內拖曳平移游標不變（MATLAB 也不變）。
18. **複製向量圖停用**：首頁「複製向量圖」、圖片視窗工具列與 FIGURE 分頁的複製向量圖、右鍵「複製向量圖（PDF）到剪貼簿」在 Windows 都是灰的，
    提示寫要改用「存成圖檔…」存 PDF／SVG／EPS（Windows 剪貼簿沒有 PDF 向量格式）。
19. **偏好設定 → 字型**：介面字級 9～16 在 100%／125%／150% 顯示縮放下，Segoe UI／Microsoft JhengHei UI 的工具列大按鈕、表格列（列高跟著變）、選單都不截字；
    圖字級改了主圖、頻譜、圖片視窗都跟著變。偏好設定左下「說明」→ 說明視窗跳到「偏好設定、匯出圖檔…」那節。
20. **存成圖檔…**：Windows 存檔對話框的副檔名跟著格式（PNG／JPEG／TIFF／PDF／EPS／SVG）；透明背景的 PNG 貼進 Word／PowerPoint 是透明的；
    寬高單位 cm 存出來的 PDF 在 Acrobat 量起來是那個大小。panel 右鍵「只匯出這個 panel…」只有那一張。
21. **平移模式右鍵**（Windows 是 Button-3）：出現 MATLAB 模式選單「還原視圖｜不限方向平移／只平移 x（水平）／只平移 y（垂直）」；選「只平移 x」後
    滾輪、拖曳都只動 x，狀態列寫目前方向。放大模式右鍵選單在「還原視圖」後面有分隔線。
22. **拖放**：從檔案總管把 .csv／.wav／.txt 拖進主視窗任何位置 → 直接加入並畫圖；拖資料夾 → 變成根資料夾。右鍵訊號 → 顏色 → 點色塊直接換色。
