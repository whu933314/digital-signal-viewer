# MATLAB R2025a 介面量測規格（plotkit 主題與 DSV 版面的依據）

量測日期 2026-10-21／22，環境：macOS 上的 MATLAB R2025a（25.1.0.2943329）。
標 `[probe]`／`[figprobe]`／`[shot]` 的數值是實際量到的；**沒有標來源的是 MATLAB 介面的樣式值（沒有逐一量測）**。來源標記：

- `[probe]`：`matlab -batch` 跑 `uifigure` 建出 Current Folder／Workspace／按鈕／分頁／表格等元件，
  `exportapp` 輸出 PNG 後逐像素取色，並 dump 每個元件的 BackgroundColor／FontName／FontSize 等屬性
  （量測輸出：`props.txt`、`uifig_dark.png`、`uifig_light.png`，不在倉庫裡）。
- `[figprobe]`：`figure(Theme=...)` 實際量 axes／legend／ColorOrder（`props2.txt`）。
- `[shot]`：使用者桌面的 4K 截圖裡真的開著的 MATLAB 圖形視窗（桌面截圖，不在倉庫裡）。
- `[setting]`：`settings().matlab.appearance.MATLABTheme.ActiveValue`。

## 0. 使用者的 MATLAB 目前是什麼樣子 `[setting]`

- 桌面主題：**Dark**。圖形主題：auto（跟著桌面 → 圖也是深色）。
- 所以 plotkit／DSV 預設主題 = `dark`，另提供 `light`，兩套數值都在下面。

## 1. 色票（MATLAB 介面的樣式值；有 `[probe]` 的是逐像素驗證過的）

灰階：#fff、#f5f5f5、#e6e6e6、#d9d9d9、#bfbfbf、#a6a6a6、#888、#7d7d7d、#616161、#4c4c4c、#333、#212121、#121212、#000。
藍：#004073（工具列分頁底）、#268cdd（焦點／hover）、#1171be、#0b2f5c。

| 用途 | dark | light |
|---|---|---|
| 主底色（視窗／面板底） | #212121 | #f5f5f5 |
| 次底色（狀態列、次要底） | #333333 | #e6e6e6 |
| 面板標題列底 | #000000 | #ffffff |
| 輸入底色（輸入框、樹、表格底） | #121212 | #ffffff |
| hover 底色 | #333333 | #ffffff |
| 清單選取（無焦點） | #616161 | #bfbfbf |
| 清單選取（有焦點） | #0b2f5c | #b4deff |
| 清單 hover | #7d7d7d | #d9d9d9 |
| 按下／開啟狀態的按鈕 | #000000 | #d9d9d9 |
| 工具列分頁列 | #004073 | #004073 |
| 工具列分頁 hover | #268cdd | #268cdd |
| 被選面板標題 | #1171be | #004073 |
| 捲軸滑塊（平常／hover／拖曳中） | #616161 / #7d7d7d / #888 | #bfbfbf / #a6a6a6 / #888 |
| 主框線（按鈕、輸入框、面板框） | #7d7d7d | #7d7d7d |
| 分隔線（含面板標題底線） | #616161 | #bfbfbf |
| 焦點框線 | #268cdd | #268cdd |
| hover 框線 | #bfbfbf | #333333 |
| 主文字 | #d9d9d9 | #212121 |
| 次要文字（section 標題） | #888888 | #616161 |
| 深底上的白字 | #ffffff | #ffffff |
| 錯誤／警告／成功 | #ff7a74 / #edb120 / #94ef84 | #b7312c / #edb120 / #008013 |

`[probe]` 逐像素驗證（dark）：視窗底 #212121、樹／輸入框底 #121212、樹選取列 #616161、分頁列底 #333333、
選中分頁 #212121（= 分頁本體，跟主底色同色；2026-10-22 複驗，之前寫的 #4c4c4c 只是反鋸齒像素）、
表格列交錯 #121212／#212121、表頭 #212121、表格格線與分頁群組框 #616161（分隔線色）、面板框 #7d7d7d、文字 #d9d9d9（= 0.851）。
light 對應：分頁列 #e6e6e6、選中分頁 #f5f5f5、格線 #bfbfbf。
light：視窗底 #f5f5f5（0.9608）、輸入框白、文字 #212121（0.1294）、面板框 #7d7d7d（0.4902）。

## 2. 字型與尺寸

- 元件字型 `[probe]`：Helvetica 12（uifigure 每個元件 FontSize = 12，FontWeight normal）。
  桌面介面用系統字型（macOS 系統字型、Windows Segoe UI；簡中 Microsoft YaHei）；元件字 12px、行高 16px。
  → Tk：用系統字型（mac `.AppleSystemUIFont`、Windows `Microsoft JhengHei UI`／Segoe UI），大小固定 **12 px**（Tk 負數字級）。
- 工具列分頁文字：11px、**全大寫**、白字、分頁最小寬 90px、左右 padding 8px、分頁列高 **28px**、圓角 2px（只有上緣）。
- Section 標題：11px、全大寫、次要文字色、置中、行高 14px；section 之間 1px 分隔線（分隔線色，上緣留 8px）。
- 工具列內容高：標準版 = 直式大按鈕 72px ＋ section 標題 14px ＋ 內距（plotkit 依實際需求量、至少 92px；分頁列 28px 另計）；
  compact 版是 52px（整條 81px），桌面預設不是 compact。橫式小按鈕 22px；按鈕底透明、hover 時底 hover 底色＋1px 主框線、圓角 3px。
  **選中的分頁**：底＝主底色、字＝主文字色（也就是分頁和內容區連成一片，不是藍色）；
  hover 是 #268cdd；#1171be 是圖形視窗那種 contextual 分頁的底色。
  開關型按鈕按下 = dark #000／light #d9d9d9；圖上的 axes toolbar 開關按下是另一組顏色（#0b2f5c／#b4deff）。
- 面板標題列：高 **23px**、底＝面板標題列底色、下緣 1px 分隔線色、字 13px、左 padding 6px；被選面板：底＝被選面板標題色、白字。
- 狀態列：底＝次底色、字＝主文字色。
- 版面間距 `[probe]`：`uigridlayout` 預設 Padding 10、RowSpacing 10、ColumnSpacing 10。
- 按鈕 `[probe]`：高 23px、1px 框 #7d7d7d、圓角約 3px、底 = 視窗底（dark #212121／light #f5f5f5）、字＝主文字色；
  StateButton 開啟時底 dark 黑／light #d9d9d9。
- 輸入框 `[probe]`：高 22～23px、底＝輸入底色、1px 框＝主框線 #7d7d7d（dark 的 exportapp 渲染裡框線幾乎看不出來；focus 變藍 #268cdd）。
- 樹 `[probe]`：底＝輸入底色、列高約 22px、縮排 18px、展開箭頭 ▾、選取列 #616161 整列。
- 表格 `[probe]`：表頭粗體、底＝主底色、1px 格線＝分隔線色（dark #616161／light #bfbfbf）；資料列交錯輸入底色／主底色；最左欄列號灰字（次要文字色）；選取列文字 dark #e6e6e6／light #212121。
- 分頁群組 `[probe]`：分頁列底＝次底色（dark #333／light #e6e6e6）、選中分頁＝主底色（dark #212121／light #f5f5f5，與內容區同色、沒有接縫）、文字＝主文字色、1px 框＝分隔線色（dark #616161／light #bfbfbf）。
- 核取方塊 `[probe]`：14px 方框、1px 框（dark #a6a6a6／light #616161）、勾為主文字色、字 12px。
- 面板 `[probe]`：BorderType line、1px #7d7d7d、標題 lefttop、字 12px。

## 3. 圖形視窗 `[shot]` `[figprobe]`

- R2025a 的圖形視窗：原生標題列 → **藍色工具列分頁列**（FIGURE／FORMAT／TOOLS／LAYOUT，大寫白字；四個分頁都是 contextual tab 的 #1171be，快速存取區是 #004073；螢幕截圖量到 #3062b3／#193666 是 Display P3 色域轉換後的值）
  → 右側快速存取（💾、↶、↷、?）→ 圖本體。工具列預設收起，只看到分頁列（28px）。
- 圖：dark 時 figure.Color #212121、axes.Color #121212、XColor／YColor／title／label #d9d9d9、
  GridColor 白、GridAlpha 0.25、legend 底 #121212、字與框 #d9d9d9、框線 0.5。
  light 時 figure #f5f5f5、axes 白、文字 #212121、GridColor #212121 alpha 0.15、legend 白底黑框。
- 共同：Helvetica 10、title 粗體 ×1.1、label ×1.1、legend 9（框線 0.5）、線寬 0.5、TickDir in、**Box on**（兩個主題都是四邊框）、TickLength [0.01 0.025]。
  plotkit 的字型清單把 Arial 放在 Helvetica 前面：macOS 的 Helvetica.ttc 讓 matplotlib 拿不到粗體面，標題會不粗。
- ColorOrder（dark，與 light 不同！）：#268cdd #f57729 #ffe864 #c05cfb #49db40 #6cf4ff #f267c5
  （light：#1171be #dd5400 #edb120 #8516d1 #3baa32 #2fbeef #d1048b）。

## 4. 設計邏輯（照 MATLAB 桌面的配置）

1. 最上面一條 **toolstrip**：分頁列（HOME／PLOTS／APPS 那種大寫分頁）＋分頁內容分成 **section**，每個 section 底下一行小字標題
   （FILE／VARIABLE／CODE…），主要動作用「圖示在上、文字在下」的大按鈕，次要動作用三列小按鈕；分頁列右側是快速存取列（存檔、復原、重做、說明）。
2. 工具列下面是 **位址列**（目前資料夾路徑、上一層、瀏覽、重新掃描），下緣 1px 線。
3. 主區域是 **面板**：左 Current Folder（檔案樹＋搜尋）、中 文件（圖）、右 Workspace（表格：Name／Value…），每個面板有 23px 標題列，可收合；面板之間可拖曳。
4. 最底一條 **狀態列**。
5. 元件一律 12px、扁平、1px 框、3px 圓角；間距 10px；沒有陰影、沒有漸層。

DSV 對應：toolstrip 四個分頁「首頁／訊號／分析／檢視」；左面板「資料夾」= 加入訊號的檔案樹；中面板「圖」；
右面板「已繪訊號」（= Workspace 表格）＋「訊號屬性」分頁（參數／突波抑制／檢視與差異）；狀態列不變。
