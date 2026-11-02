# 計劃：DSV v3.3 ＋ 可重用繪圖函式庫 plotkit（2026-10-21）

## 目標
1. 把 2026-10-21 對照 MATLAB R2025a 列出的「小」「中」兩組落差做進 DSV。
2. 把互動繪圖的功能抽成獨立的單檔函式庫 `plotkit.py`，之後任何 Python 程式只要
   `import plotkit as pk` 就能用同一套功能畫圖（像 matplotlib 的 `pyplot` 用法）。
3. DSV 改用 plotkit：圖片視窗直接用 `plotkit.FigureWindow`，主視窗的多 panel 圖用
   `plotkit.Interactor` 掛上同一套互動（滾輪縮放、拖曳平移、資料提示、圖例改名、標註）。
4. 寫完後用多個 agent 平行檢查：規格對照、跑測試與邊界案例、以第三方使用者身分試用 API、
   Windows 相容性審查；發現的問題修完再跑一次全部測試。

## 要做的功能（MATLAB → plotkit → DSV）
小：
- MATLAB 風格開關：7 色序 `#1171be #dd5400 #edb120 #8516d1 #3baa32 #2fbeef #d1048b`、線寬 0.5、
  Box off（只留左下軸）、刻度朝內、格線實線透明度 0.15、Helvetica／Arial（中文 fallback 保留）、標題粗體 1.1 倍、
  圖例有框 9 pt、figure 底色 #f5f5f5、axes 白。
- 雙擊圖例文字就地改名。
- 訊號清單「顯示／隱藏」勾選（隱藏的不畫、不比差異，但留在清單）。
- 每條線的 marker 樣式與大小。
中：
- 釘住式資料提示（data tips）：資料提示模式開著時點線條就釘一個，可多個、可拖、右鍵或 Delete 刪除；重畫後保留。
- 滾輪縮放（以游標為中心；DSV 預設只縮 x，Shift 縮 y，Ctrl 兩軸）、左鍵在空白處拖曳平移、
  雙擊空白處或 Home 鍵還原視圖。
- xline／yline 參考線與文字標註（右鍵插入、可編輯、文字可拖），存進設定檔。
- 雙 y 軸：每條訊號可指定畫在左軸或右軸。
- Undo／Redo（Ctrl+Z／Ctrl+Y）：樣式、清單、參數、標註等所有改動。
- 圖片視窗存成 JSON 可重開（含資料、樣式、標註、資料提示、視圖範圍）。
- 複製整張圖到系統剪貼簿（Windows 用 PowerShell、macOS 用 osascript、Linux 用 xclip；失敗時提示 PNG 路徑）。

## 檔案
- `plotkit.py`（新，單檔，只用 tkinter／numpy／matplotlib）
  - 資料模型：`Series`（label、x、y、kind line/step、color、lw、ls、marker、ms、alpha、visible、yaxis、xshift、yshift、meta）、
    `Annotation`（xline／yline／text）、`DataTip`（series uid＋index＋偏移）、`FigureState`（標題、軸標籤、範圍、grid、legend、style、以上三種清單）。
  - 樣式：`STYLES["default"]`、`STYLES["matlab"]`，`apply_style(fig, axes, name)`。
  - 無 GUI 也能用的部分：JSON 存讀、`UndoStack`、`draw_state(ax, state)`（headless 可測）、`hit_test_lines`、`nearest_index`、`figure_to_png_bytes`。
  - `Interactor(canvas, get_axes, …)`：掛在任何 Tk 內嵌的 matplotlib 圖上，提供滾輪縮放、拖曳平移、還原視圖、資料提示、
    圖例雙擊改名、點線條回呼、文字標註拖曳。
  - `PlotCanvas(master)`：單張圖（可雙 y 軸）＋左側訊號清單（顯示勾選）＋工具列＋右鍵選單＋undo／redo＋複製貼上＋JSON。
  - `FigureWindow`：視窗（選單列：檔案／編輯／檢視／插入／工具）包一個 PlotCanvas。
  - 函式式 API：`pk.figure(title=…, style=…)` → 視窗物件，`.plot(x, y, label=…)`、`.step(…)`、`.xline()`、`.yline()`、`.text()`、
    `.xlabel()`、`.ylabel()`、`.title()`、`.xlim()`、`.ylim()`、`.legend()`、`.grid()`、`.save_json()`、`.savefig()`；`pk.show()` 進入事件迴圈；
    `pk.open_json(path)` 重開。沒有 Tk 時仍可 import 並跑 `python plotkit.py --selftest`。
- `signal_viewer.py` → v3.3：`import plotkit`；Signal 加 marker／ms／visible／yaxis，lw 改成「未設定＝依風格」；
  render 支援隱藏、右軸（twinx）、marker、MATLAB 風格；主視窗掛 Interactor；清單加「顯示」欄；
  標註與資料提示存進設定 JSON；Undo／Redo；複製圖到剪貼簿；圖片視窗改用 plotkit.FigureWindow。
- `README.md`、`docs/plotkit.md`（函式庫使用說明＋範例）、`examples/plotkit_demo.py`。
- 測試：`python plotkit.py --selftest`、`tests_plotkit_gui_mac.py`、`python signal_viewer.py --selftest`、`tests_gui_mac.py`（擴充）。
- `build_exe.bat` 不用改：PyInstaller 會自動帶入 import 的 `plotkit.py`（exe 旁不需要再放）。

## 順序
1. plotkit 資料模型／樣式／JSON／undo／headless 繪圖 → selftest。
2. plotkit Interactor → PlotCanvas → FigureWindow → 函式式 API → GUI 測試。
3. DSV 整合（Signal 欄位、render、清單、Interactor、標註、資料提示、undo、剪貼簿、圖片視窗）→ selftest／GUI 測試。
4. 文件與範例。
5. 多 agent 檢查（4 個平行）→ 修正 → 全部測試再跑一次。

## 驗收
- 上述每個功能都有自動測試覆蓋（Mac 上用 anaconda python 跑 Tk 8.6）。
- 既有 61＋17 項 DSV 測試仍全過；v3.2 的設定檔能被 v3.3 讀。
- 範例腳本 `examples/plotkit_demo.py` 用 plotkit 畫圖，不依賴 DSV。

## 實作結果（2026-10-21）
- 與原計劃不同的決定（使用者選的）：plotkit 是多檔套件 `plotkit/`（dialogs、styles、model、undo、draw、clipboard、interact、widgets、selftest、`__main__`），不是單檔；
  DSV 主畫面滾輪預設兩軸一起縮（Shift 只縮 x、Ctrl 只縮 y）；資料提示用開關模式。
- 自行決定：差異比對只在同一側（左軸優先）的可見訊號之間做；標註與資料提示的 artist 由 `Interactor.rebuild()` 統一重建，`render()` 不畫它們；
  風格只改 artist 不動 rcParams（頻譜／GFSK 視窗維持預設風格）；被移除的訊號留在 50 筆的墓園讓 undo 復活同一個物件。
- 測試（2026-10-21 修正後實測）：`python -m plotkit --selftest` 72 項、`tests_plotkit_gui_mac.py` 52 項、`python signal_viewer.py --selftest` 68 項（部分 check 在迴圈裡，印出的 ok 行數）、
  `tests_gui_mac.py` 132 項，全部通過（macOS，anaconda Python 3.11／Tk 8.6.13；Apple Python 3.9 的兩個 selftest 也過；`PYTHONIOENCODING=cp950` 模擬 Windows 管線也過）。
- 多 agent 檢查（2026-10-21）：規格對照 0 P0／3 P1／2 P2／16 P3，第三方試用文件評 C+（已依建議重寫 docs/plotkit.md 並修 2 個 bug），Windows 相容 0 P0／1 P1／4 P2／10 P3；
  P1、P2 全部修掉，P3 修了大部分（未做：Windows DPI-aware 宣告、剪貼簿改背景執行緒、圖上點擊的重複 hit test、FigureWindow 的 Alt 鍵碰到選單列）。
  每個修正都補了自動測試（Alt+滾輪、觸控板累加、NaN 的 fmt_num、open_json 保留視圖、匯出前藏十字游標、cp950 讀檔、migrate_settings 不改輸入、discard_last）。
  測試＋邊界 agent：0 P0／P1、3 P2（NaN／inf 點的資料提示讓整張圖畫不出來、「_」開頭的名稱圖例對應錯位、大訊號取樣比對漏掉單點差異）、17 P3，
  P2 全修、P3 修了 JSON 容錯／開檔錯誤對話框／plot 格式字串只擋位置參數／右軸獨占藏左刻度／ystack 分側／DataTip offset／wheel NaN 等，都有自動測試。
  Windows 端的 10 步手動檢查在 `docs/windows-checklist.md`。
- Windows 實測（2026-10-21，使用者的 Windows 11 桌機，Python 3.12.10／numpy 2.4.4／matplotlib 3.10.9／Tk 8.6）：兩個 selftest（cp950 管線）、
  `tests_gui_mac.py` 132/132、`tests_plotkit_gui_mac.py` 52/52、真實剪貼簿（PowerShell 2.1 秒、900×600）、`build_exe.bat` → 38.7 MB exe、
  frozen selftest、GUI 啟動（啟動器＋77 MB 子程序）全部通過；只改了 plotkit 清單點擊不再用 `identify("region")`。結果記在 `docs/windows-checklist.md`。
- macOS 打包：`build_mac.sh`（專案內 `.venv-build/`，不用 anaconda 的 site-packages 因為有過時的 `pathlib` 套件）→ `dist/SignalViewer.app`。
- 跑測試的注意事項：Apple 的 `/usr/bin/python3` 只在使用者 site-packages 找得到 numpy／matplotlib，兩個 `--selftest` 要用真正的 `HOME` 跑（或加 `PYTHONUSERBASE`）；
  GUI 測試才改 `HOME`。plotkit 的 JSON 用 Python 的 `allow_nan`，NaN／inf 會寫成 `NaN`／`Infinity`（不是嚴格 JSON，Python 的 `json` 讀得回來，其他語言的嚴格解析器可能拒收）。

## v3.4（2026-10-22）：介面照 MATLAB R2025a 的設計重做
- 使用者要求：「左邊欄位這些選項做得像 MATLAB 的設計美感和設計邏輯」「整個 app 的美感和邏輯都要跟 MATLAB 接近」「不要猜測」。
- 做法：真的去量 MATLAB——`matlab -batch` 建 uifigure（Current Folder／Workspace／按鈕／分頁／表格）`exportapp` 出圖逐像素取色、dump 屬性；
  對照 MATLAB 介面的樣式值（主題色、toolstrip／面板標題／狀態列尺寸）；`figure(Theme=...)` 量 axes／legend／ColorOrder；
  桌面截圖裡的 MATLAB 圖形視窗。全部寫在 `docs/matlab-ui-spec.md`。使用者的 MATLAB 桌面主題是 **Dark** → 預設深色。
- 新模組 `plotkit/theme.py`（色票 TOKENS、ttk 主題 plotkit-dark／light、圓角按鈕與輸入框（Pillow 畫的 9-slice 圖片元素）、
  `Panel`、`Toolstrip`／`Section`、`PlotToolbar`（包 NavigationToolbar2Tk）、`Tooltip`、`status_bar`、`placeholder`）、
  `plotkit/icons.py`（約 60 個單線條圖示，Pillow 4× 超取樣）。`styles.py` 加 `matlab-dark`（實測值）、`draw.py` 文字／圖例／提示顏色跟風格。
- plotkit 視窗：`FigureWindow` 多了藍色 FIGURE 工具列（檔案／編輯／檢視／插入 section ＋ 快速存取），清單變 Panel，圖工具列換成 `PlotToolbar`；
  `pk.figure()` 風格預設跟主題。
- DSV：toolstrip 四分頁（首頁／訊號／分析／檢視）＋ 位址列 ＋ 三欄面板（資料夾／圖／已繪訊號＋訊號屬性）＋ 狀態列；
  設定檔 view 多 `theme`（dark／light），`style` 預設 `matlab-dark`；頻譜／GFSK／說明／診斷視窗也套主題。
- 測試：plotkit selftest 多 13 項（色票、matlab-dark、圖示）、plotkit GUI 多 10 項、DSV GUI 多 19 項（主題切換、面板、工具列 mode 同步）。
  視覺檢查：`screencapture -l <windowid>`（CGWindowList 找視窗）抓自己的視窗比對 MATLAB 的 exportapp 截圖。
- 2026-10-22 多 agent 檢查（5 視角 ＋ 逐項反證，19 個 agent）確認 13 項並已修：切換主題兩次後 ttk 圖片元素失效（Theme 物件改成每個 interpreter 快取、活到行程結束）、
  第二個 tk.Tk() 沒主題（元素集合改成每 interpreter）、捲軸 1px（捲軸改圖片元素）、分頁選中色（實測是主底色，不是 #4c4c4c／#1171be）、
  toolstrip 開關色（toolstrip 按下的顏色，而不是 axes toolbar 按下的顏色）、核取方塊框色（實測）、matlab 風格 Box=on、macOS 粗體標題（Arial 先）、
  舊設定檔升級（v6：theme 預設 dark、style 跟主題）、密集訊號的資料提示釘錯樣本（nearest_vertex 改用像素半徑找候選）、視窗大小依 DPI、
  三欄比例、說明視窗字級、Listbox 換色、面板不可收合時雙擊不收、Spectrum／GFSK／FigureWindow 跟著主題重畫、工具列高度自動 fit、
  QAB 多一顆 PLOT、位址列多「上一層」。未做：retina 上圖示 1x（Tk 限制）、對話框尺寸未依 DPI、表頭沒有直線分隔。
- 2026-10-22 英文介面：新模組 `plotkit/i18n.py`（`tr()`、`set_language()`，鍵 = 中文原文），翻譯表 `plotkit/i18n_en.py` 合併 core／plotkit／dsv1／dsv2／dsv3 五個 part（約 480 個鍵）；
  偏好設定對話框（首頁 → 環境 → 偏好設定：一般／外觀／繪圖／資料夾，語言改了存進 view.lang、重開程式套用，跟 MATLAB 一樣）；
  啟動語言 `--lang en` ＞ `DSV_LANG` ＞ 自動存檔的 view.lang ＞ 中文；英文說明用 README.en.md（build 腳本 --add-data）。
  5 個翻譯 agent（signal_viewer.py 三段、plotkit、README）＋ 2 個驗證 agent（功能：全部測試＋英文介面掃描 0 殘留；品質：術語統一、US 拼法、鍵衝突）。
  新測試 `tests_i18n_mac.py`（英文建 app、走遍元件／分頁／次要視窗／一串動作，不能剩中文）16 項；plotkit selftest 多 7 項（translation 覆蓋率、佔位符一致）。
