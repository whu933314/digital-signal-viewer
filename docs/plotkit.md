# plotkit 使用說明（v0.2.0）

像 pyplot 一樣用的互動繪圖套件。只需要 Python 3.10+、numpy、matplotlib ≥ 3.7（介面用內建的 tkinter）。
把 `plotkit/` 資料夾放到你的程式旁邊（或在專案資料夾 `pip install -e .`）就能 `import plotkit as pk`。

## 最短範例
```python
import numpy as np
import plotkit as pk

t = np.linspace(0, 1e-3, 2001)
w = pk.figure(title="demo")                           # 開一個視窗（風格跟介面主題）；title 是「視窗」標題，圖的標題用 w.set_title()
w.plot(t * 1e6, np.sin(2 * np.pi * 5e3 * t), label="I")
w.plot(t * 1e6, np.cos(2 * np.pi * 5e3 * t), label="Q", ls="--", color="#dd5400")
w.step(np.arange(0, 1000, 50.0), (np.arange(20) % 2).astype(float), label="clk", yaxis="right")
w.set_title("I/Q 與 clk"); w.xlabel("t [us]"); w.ylabel("amplitude"); w.ylabel("level", side="right")
w.xline(250, "sync"); w.yline(0.5); w.text(600, 0.8, "注意這裡", color="#dd5400")
w.save_json("demo.json")                               # 之後 pk.open_json("demo.json") 可重開
pk.show()                                              # 進入事件迴圈（所有視窗關掉才返回）
```
完整範例：`examples/plotkit_demo.py`；命令列：`python -m plotkit --demo`、`python -m plotkit 圖.json`、`python -m plotkit --selftest`
（加 `--lang en` 或設環境變數 `PLOTKIT_LANG=en` 是英文介面；讀不了的檔只印一行原因，其餘照開）。

### 給 pyplot 使用者的提醒
- `plot(x, y, label)`：第三個位置參數是 **label**，不收 `"r--"` 這種格式字串（會直接丟 ValueError）；顏色／線型／標記用 `color=`、`ls=`、`marker=`。
- 短名稱 `lw / ls / ms / color`；長名稱 `linewidth / linestyle / markersize / c` 也接受，會自動轉換。
- `pk.figure(title=…)` 與 `w.title()` 是 Tk **視窗**標題；圖上的標題是 `w.set_title(s)`（別名 `w.title_text`）。
- `w.xlim(a, b)` 或 `w.xlim((a, b))` 都可以；`w.xlim()` 讀目前範圍；`w.xlim("auto")` 回到自動範圍；`w.ylim(..., side="right")` 是右軸。
- `size=(寬, 高)` 英吋，不是 `figsize`；`xline/yline` 對應 `axvline/axhline`；`legend(on, loc)` 第一個參數是開關。
- 視窗內的互動改動（改色、改名、刪線…）都能 Ctrl+Z 復原；程式碼呼叫 `w.undo()` / `w.redo()` 也一樣。

## 視窗裡可以做什麼
- **點線條**＝釘資料提示（預設，跟 MATLAB 一樣）；**Shift + 點線條**＝選取（再 Shift + 點加選／取消），點空白取消；
  關掉「資料提示」後點線條就是選取；清單面板也可選（多選）。選取的線會加粗。
- **樣式**：雙擊線條（資料提示關著時）開顏色選擇器；右鍵（macOS 也可 Control+按一下）選單有 顏色／線寬／線型／標記／標記大小／顯示隱藏／左軸右軸／改名／x、y 位移／重設樣式／刪除。
- **圖例**：雙擊圖例文字就地改名（Enter 確定、Esc 取消）；雙擊圖例框裡文字以外的地方不動作（MATLAB 也只處理文字）。
  按住圖例拖曳＝移動圖例（和 MATLAB 預設的一樣；不平移、Esc 取消、可拖到座標區外），位置存成圖例左下角的 axes 座標 `(x, y)`
  進 `FigureState.legend_loc`（JSON 存成 list、讀回轉 tuple），可復原；host 收到 `on_legend_move(ax, loc)`。
  圖例上右鍵＝圖例選單（`Interactor.legend_menu_items(hit)`：刪除圖例 → `on_legend_delete(ax)`、圖例位置 ▸ 右上／左上／右下／左下／最佳 → `on_legend_loc(ax, loc)`），
  不夾帶線條樣式與插入參考線。`Interactor.legend_hit(event)` 回傳游標下的圖例（整張圖每個 axes 都看）。
- **線條右鍵**：線寬 ▸ `styles.LINE_WIDTHS`（0.5、1 … 12）、標記大小 ▸ `styles.MARKER_SIZES`（2 … 48），兩個都另有「自訂…」對話框；
  線型 `styles.LINESTYLES`（`-` `--` `:` `-.` `None`）、標記 `styles.MARKERS`（MATLAB 的 14 種與順序）——都照 MATLAB 線條右鍵選單。
  `widgets.fill_menu(menu, items)` 把 `menu_items()` 的清單放進 tk.Menu（`None`＝分隔線、`(label, [(子項, 回呼), …])`＝子選單）。
- **清單面板**：☑ 切換顯示／隱藏（隱藏的線不畫、不進圖例，但保留）；雙擊名稱改名；名稱文字色＝線色。
- **縮放平移**：滾輪＝兩軸一起以游標為中心縮放（一格 1.1 倍，縮小到自動範圍為止，和 MATLAB 一樣；Ctrl／⌘+滾輪也是，給 host 畫布可捲動時用），
  Shift+滾輪只縮 x，Ctrl／⌘+Shift+滾輪只縮 y；+／− 鍵也是 1.1 倍；host 可用 `Interactor.wheel_filter`（回 False＝這個事件不縮放）把滾輪讓給自己的捲動；
  host 可覆寫 `InteractorHost.outer_limits(ax)` 指定縮小的外界（預設＝matplotlib 自動範圍）；左鍵在空白處拖曳＝平移（按下後移 ≥10 px 才算拖曳，`DRAG_THRESHOLD_PX`）；
  拖曳 x／y 尺規（刻度文字，`draw.ruler_zones()`）只沿該軸平移；方向鍵每按一下平移 5 像素（`KEY_PAN_PX`；工具列平移模式裡也是）。
  雙擊空白、Home 鍵、工具列 Home（`PlotToolbar.home_command`）或「還原視圖」按鈕＝回到第一次縮放／平移前的視圖（MATLAB 的 Restore View：
  自動縮放的軸重新自動縮放、設定過的範圍回到那個範圍；`Interactor.forget_home()` 讓下一次互動重新記）；還沒互動過時＝自動範圍。
  工具列的放大鏡／十字模式開著時，拖曳平移與資料提示暫停（模式關掉後自動恢復），滾輪照樣縮放；平移模式裡雙擊＝還原視圖、右鍵＝選單、右鍵拖曳不縮放。放大模式照 MATLAB：單擊＝以該點為中心放大 1.5 倍、
  Shift＋單擊＝縮小 1.5 倍、拖框＝縮到框內（框的一邊不到 15 px 就只縮另一個方向、兩邊都不到就以點為中心 1.2 倍）、雙擊＝還原、右鍵＝模式選單
  （縮小／還原／不限方向／只縮 x／只縮 y）、↑／↓ 鍵 1.1 倍、拖框時按 Esc＝取消；框是 1 px 藍色實線（#268cdd，`MatlabNav.draw_roi`），拖滿 10 px（`CLICK_PX`）才畫，一邊不到 15 px 畫成 15 px 寬的帶子（兩端短邊線＋中線）。這些像素門檻（拖曳 10 px、框 15 px、命中 ±2 px、方向鍵 5 px）都是邏輯像素：Windows／Linux 顯示縮放（`canvas.device_pixel_ratio`≠1）時乘上 dpr，兩種模式一致。
  游標照 MATLAB（`MatlabNav._update_cursor`）：放大模式 crosshair、平移模式張開的手（macOS `openhand`、其他平台 `hand2`）、模式關掉 arrow；
  `MatlabNav._wait_cursor_for_draw_cm` 是空的：重畫時不換等待游標。
  macOS 觸控板兩指上下滑也是縮放（倍率依滑動時間計算，不會失控）；Tk 8.6 不支援捏合手勢。
- **資料提示**：點線條會釘一個提示（名稱、x、y；「資料提示」預設開著），可多個；拖曳移動；點一下選取後按 Delete，或右鍵刪除／清除全部（提示框畫到座標區外面時也可以拖、右鍵）；
  選取中的提示按 →／↑ 移到下一個樣本、←／↓ 移到上一個（MATLAB datatip 的 increment；優先於方向鍵平移、可 undo；`Interactor.step_tip(tip_id, ±1)`）。
  重畫（改樣式、undo）後提示會留在同一個樣本點上。
  照 MATLAB R2025a：**游標移到線上**（命中＝線的 ±2 px＋線寬一半，`draw.PICK_TOL_PX`；點線釘提示也是同一個門檻）→ 游標 crosshair、最近頂點出現標記，
  停 200 ms（`interact.HOVER_LINGER_MS`）出現暫時的提示框；移開／按下／滾輪／工具列模式／離開畫布就收掉，點一下才釘（暫時的不進模型與 undo；
  `Interactor.hover_enabled=False` 可關，`Interactor.hover_tip` 是目前的暫時提示）。
  效能：暫時提示是 animated artist，換頂點／出框／收掉只 blit（貼回 draw_event 存的背景再畫 animated artist，host 的十字游標一起補畫），
  不整張重畫；長的線（≥ 2000 點、x 已排序、直角座標）命中判定只看游標左右 ±(2 px＋線寬) 的樣本（`draw._line_hit_fast`，結果與 Line2D.contains 相同），
  1e6 點全幅每個 motion 不到 1 ms。
  文字「名稱／X 值 單位／Y 值」（`format_tip_text`；數值 `draw.fmt_matlab`＝MATLAB auto 格式：6 位有效、|v| < 1e-4 或 ≥ 1e15 用指數）。
  外觀：方框、無連線、框底＝座標區底色、框線 #7d7d7d（選取中 #268cdd）、10 pt、資料點實心小圓（邊 #ffffdc）。
  位置像 MATLAB Location auto：`DataTip.offset` 的正負號＝貼在資料點的哪一角（預設 `model.TIP_OFFSET_DEFAULT`＝(5, 5) 右上），
  釘上與視圖改變（axes 的 xlim／ylim_changed）時 `draw.place_tip` 重選角落（上面放不下→下、右邊放不下→左）；拖過的（offset 大小不是預設）不重擺。
  資料點在 XLim／YLim 外時整個提示不畫、也點不到。
- **標註**：右鍵空白處「插入垂直參考線／水平參考線／文字」（在游標位置），或選單「插入」；文字可拖曳；右鍵標註可編輯／刪除。
  點一下標註＝選取（`Interactor.selected_ann`／`select_annotation(id)`；文字框線變粗、參考線變粗），Delete 刪掉、Esc 取消、右鍵先選取；
  與資料提示、線條的選取互斥，Delete 順序＝選取的提示 → 選取的標註 → `host.on_delete_key()`（host 可覆寫 `on_annotation_selected`，預設轉 `on_tip_selected`）。
  預設外觀照 MATLAB R2025a：`Annotation` 預設 lw 0.5、ls "-"、alpha 0.7、字級＝風格的 `annotation_fontsize`（10）；
  xline 標籤轉 90°、ha right／va top、離線 2 px＋線寬一半、離上緣 5 px；yline 標籤靠右端 5 px、在線上方；
  線出了 XLim／YLim 時標籤不畫（`draw.ReflineLabel`），線在範圍內靠邊時標籤可以伸出座標區（MATLAB 也不裁切）。
- **Undo／Redo**：Ctrl+Z／Ctrl+Y（macOS ⌘Z／⌘Y 也可）或按鈕。縮放平移與選取不進 undo（和 MATLAB 一樣）。
- **跨視窗複製貼上**：Ctrl+C 複製選取的線（含樣式與資料），到另一個視窗 Ctrl+V 貼上；或右鍵「複製到新視窗」。Ctrl+W（macOS ⌘W）關閉視窗。
- **注音等非拉丁輸入法**（macOS，2026-10-27）：Tk 照目前的鍵盤配置把按鍵翻成字再找 keysym，注音之下 ⌘V 的 keysym 是 `??`、- 是 `??`（ㄦ），
  `<Command-v>` 這種綁定對不到。圖片視窗的 ⌘C／⌘V／⌘Z／⌘Y／⇧⌘Z／⌘A／⌘S／⌘W、圖上的 - 鍵、輸入框的 ⌘C／⌘V／⌘X／⌘A 都照按鍵的實體位置
  （ABC 配置）認，和 macOS 其他 App 一樣；ABC 之下什麼都不變、不會做兩次。注音的 3、7、` 鍵 Tk 給的是拉丁名字的 keysym（`caron`、`abovedot`、
  `periodcentered`），keysym 和虛擬鍵碼都對上時也照實體按鍵認成 3、7、`（`NAMED_ON_OTHER_KEYS`；別的配置在別的鍵上打出同一個字照舊）。
  邏輯在 `plotkit.keys`：`latin_keysym(event)`（拿來對快速鍵的 keysym）、
  `command_key(event)`（⌘／⌃＋字母、要照實體按鍵認時回那個字母）、`mpl_key(event)`（matplotlib 的 key 名）、
  `install_text_fallback(root)`（Tk 輸入框類別的 `<Mod1-Key>`／`<Control-Key>` 後備；開第一個圖片視窗時自動裝，PlotCanvas 嵌在自己的視窗裡時可以自己呼叫）。
- **圖工具列**：順序照 MATLAB 的座標區工具列（axtoolbar default：export → data tips → pan → zoom in → restore view）：
  存檔、複製圖片、複製向量圖（PDF）、資料提示、平移、放大｜Home（還原視圖）｜上一個／下一個視圖（matplotlib 多的）｜其餘 plotkit 自己的按鈕。
- **存檔**：檔案選單 另存 JSON（可重開，含資料、樣式、標註、資料提示、視圖範圍）、存成圖檔…（匯出對話框：格式、DPI、背景、寬高；plotkit.export）、複製圖片到系統剪貼簿、
  複製向量圖（PDF）到剪貼簿（MATLAB Export → Copy as vector graphic；macOS «class PDF »；Windows 的剪貼簿放不了向量圖，按鈕與選單項目停用、tooltip 說明——`clipboard.vector_copy_state()`／`vector_copy_tip()`）
  （Windows 用 PowerShell、macOS 用 osascript、Linux 需 xclip 或 wl-copy；失敗時狀態列會告訴你 PNG 存在哪）。

## API 參考

### 模組層級
```python
pk.figure(title=None, *, style="default", size=(8.0, 5.0), dpi=100, master=None, wheel_axis="both") -> FigureWindow
pk.open_json(path, *, master=None, title=None) -> FigureWindow
pk.show(block=None)      # 自己建的根視窗才會 mainloop；在別人的 Tk 程式裡（或重入）只做 update()；block=False 立刻返回
pk.windows() -> list[FigureWindow]   # 只列 FigureWindow，不含內嵌的 PlotCanvas
pk.active_window() -> FigureWindow | None ; pk.close_all()
pk.CLIPBOARD             # 跨視窗剪貼簿：list[Series]
pk.STYLES                # {"default": {...}, "matlab": {...}}；pk.get_style(name_or_dict) 取得合併後的風格 dict
pk.HAVE_TK               # False 時 pk.figure() 會丟 RuntimeError，其餘無 GUI 功能照常
```

### FigureWindow（`pk.figure()` 回傳；是 `tk.Toplevel`）
```python
.plot(x, y=None, label=None, *, kind="line", color=None, lw=None, ls=None, marker="", ms=None, alpha=1.0,
      yaxis="left", xshift=0.0, yshift=0.0, xunit="", meta={}) -> Series     # y=None 時 x 當 y、x=0..n-1
.step(x, y, label=None, **同上) -> Series          # step 的 x 可以比 y 多一點（最後一段的結束位置）
.add_series([Series, ...], *, select=True, autoscale=True) -> list[Series]
.series() -> list[Series] ; .state -> FigureState
.xline(x, text="", *, color=None, lw=0.5, ls="-", alpha=0.7, fontsize=None) -> Annotation
.yline(y, text="", side="left", *, color=…, lw=…, ls=…, fontsize=…) -> Annotation
.text(x, y, s, side="left", *, color=…, fontsize=None, ha="left", va="bottom", boxed=True) -> Annotation
.set_title(s) / .title_text(s) ; .xlabel(s) ; .ylabel(s, side="left")
.xlim() -> (a, b) ; .xlim(a, b) ; .xlim((a, b)) ; .xlim("auto")        # ylim 同，多一個 side="left"|"right"
.grid(on=True) ; .legend(on=True, loc=None)      # loc 要是 matplotlib 認得的（"best", "upper right", …）
.set_style("matlab" | "default" | {"base": "matlab", "lw": 1.0, ...})   # 不合法的名稱直接丟 KeyError，狀態不變
.undo() ; .redo() ; .restore_view()
.save_json(path) ; .load_json(path) ; .savefig(path, dpi=None) ; .copy_to_clipboard() -> (ok: bool, msg: str)
.to_png_bytes() -> bytes ; .close()
.fig / .ax（左軸）/ .canvas / .plot_canvas（PlotCanvas，更細的操作見下）
```

### PlotCanvas（內嵌到你自己的 Tk 視窗；是 `ttk.Frame`，用 pack/grid 放）
```python
pc = pk.PlotCanvas(master, state=None, *, style=None, show_list=True, show_toolbar=True,
                   size=(8.0, 5.0), dpi=100, wheel_axis="both")
pc.plot(...) / pc.step(...) / pc.add_series([...]) / pc.series() / pc.state          # 和 FigureWindow 一樣
pc.set_title / set_xlabel / set_ylabel(s, side) / set_grid / set_legend / set_style / set_xlim / set_ylim
pc.select(uids, *, add=False) ; pc.selected (set[int]) ; pc.selected_series() ; pc.select_all()
pc.set_props(uids, desc="樣式", **fields)      # 任何 Series 欄位：color、lw、ls、marker、ms、alpha、visible、yaxis、label…
pc.rename(uid, label) ; pc.set_visible(uids, flag) ; pc.toggle_visible(uids) ; pc.set_yaxis(uids, "right") ; pc.set_shift(uids, "x", 5.0)
pc.remove_series(uids) ; pc.delete_selected() ; pc.clear()
pc.insert_xline_at(x, text="") ; pc.insert_yline_at(y, text="", axes_key="left") ; pc.insert_text_at(x, y, text=None)
pc.remove_annotation(ann_id) ; pc.ia  # plotkit.Interactor：pc.ia.tips_enabled、pc.ia.add_tip(uid, index)、pc.ia.clear_tips()
pc.undo() ; pc.redo() ; pc.undo_stack (UndoStack) ; pc.copy_selected() ; pc.paste(series=None) ; pc.copy_to_new_window()
pc.save_json(path) ; pc.load_json(path) ; pc.savefig(path, dpi=None) ; pc.png_bytes() ; pc.copy_image_to_clipboard() -> (ok, msg)
pc.copy_vector_to_clipboard() -> (ok, msg)   # PDF；pk.copy_figure_to_clipboard(fig, content="image"|"vector")
pc.restore_view() ; pc.redraw(autoscale=False, keep_view=True) ; pc.info (RenderInfo，見下) ; pc.fig ; pc.canvas
```

### 資料模型（不需要 Tk）
```python
pk.Series(label, x, y, kind="line", uid=0, color=None, lw=None, ls=None, marker="", ms=None, alpha=1.0,
          visible=True, yaxis="left", xshift=0.0, yshift=0.0, xunit="", meta={})
    # label 是第一個位置參數；x、y 轉成唯讀 float64 陣列；kind="line" 要等長，kind="step" 允許 len(x)==len(y)+1
    # .n、.plot_xy()、.vertex(i)、.copy(**changes)、.to_dict()、Series.from_dict(d)
pk.Annotation(kind="text"|"xline"|"yline", id=0, value=0.0, x=0.0, y=0.0, text="", color=None, lw=0.5,
              ls="-", alpha=0.7, fontsize=None, axes_key="left", ha="left", va="bottom", boxed=True, visible=True)
    # xline/yline 用 value；text 用 x、y；axes_key "left"/"right"（DSV 用 "P1"/"P1R"）
pk.DataTip(uid, index, id=0, offset=(15.0, 15.0), axes_key=None, text=None)   # offset 是文字框相對頂點的偏移（點）
pk.FigureState(title="", xlabel="", ylabel="", ylabel_right="", style="default", grid=True, legend=True,
               legend_loc="upper right", xunit="", series=[], annotations=[], tips=[], view={...})
    # 直接用 series=[...] 建也可以：沒給或重複的 uid／id 會自動補；或用 .add_series(s) / .add_annotation(a) / .add_tip(t)
    # .find(uid)、.visible_series()、.remove_series(uids)（連帶刪該線的 tips）、.snapshot() / .restore(snap)（undo 用，陣列共用）
pk.save_json(state, path) ; pk.load_json(path) -> FigureState ; pk.state_to_dict(state) ; pk.state_from_dict(d)
pk.UndoStack(limit=100): push(state, desc, tag=None, coalesce_window=2.0) / undo(current) / redo(current) / can_undo / can_redo
```

### 無 GUI 出圖（Agg）
`draw_state` 只畫線、軸、圖例、風格；**標註與資料提示要另外畫**（視窗裡是 Interactor 在重畫後補上的）：
```python
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
st = pk.load_json("demo.json")
fig = Figure(figsize=(8, 5), dpi=100); FigureCanvasAgg(fig)
info = pk.draw_state(fig, st, selected=(), view=None, autoscale=False)   # RenderInfo
for a in st.annotations:
    pk.draw_annotation(info.axes_for(a.axes_key), a, info.style)
for tip in st.tips:
    s = st.find(tip.uid)
    if s and s.visible:
        x, y = s.vertex(tip.index)
        pk.draw_tip(info.axes_for(s.yaxis), tip, x, y, pk.format_tip_text(s.label, x, y, s.xunit), info.style)
fig.savefig("demo.png")
```
`RenderInfo` 欄位：`ax_left`、`ax_right`（沒有右軸時 None）、`axes_for("left"|"right")`、`all_axes()`、`lines`（uid → Line2D）、
`legend`、`legend_uids`（圖例每一項對應的 uid）、`style`（合併後的風格 dict）。

### 把互動掛到自己的 matplotlib 圖上
`pk.Interactor(canvas, host, toolbar=None, model=None, wheel_axis="both")` 不依賴 PlotCanvas：實作 `pk.InteractorHost` 的幾個方法
（`lines_in(ax)`、`series_data(uid) -> (x_vertices, y_vertices, label, axes)`、`axes_for_key(key)`、`legend_entries(ax)`、`on_pick`、`on_context`、
`on_rename`、`before_model_change`／`on_model_change`…）就能在任何 Tk 內嵌的 matplotlib 圖上得到滾輪縮放、拖曳平移、資料提示、圖例改名、標註。
DSV 的主畫面就是這樣掛的（`signal_viewer.py` 的 `DsvHost`）。重畫（`fig.clear()`）後呼叫 `ia.reset(); ia.rebuild()` 把提示與標註畫回來。

## JSON 格式（version 1）
```json
{"format": "plotkit-figure", "version": 1, "plotkit": "0.2.0", "saved": "2026-10-21T18:30:00",
 "title": "", "xlabel": "", "ylabel": "", "ylabel_right": "", "xunit": "us", "style": "matlab",
 "grid": true, "legend": true, "legend_loc": "upper right",
 "view": {"xlim": [0, 10], "ylim": [-1.1, 1.1], "ylim_right": null},
 "series": [{"uid": 1, "label": "I", "kind": "line", "x": {"start": 0, "step": 0.5, "n": 2001}, "y": [...],
             "color": "#ff0000", "lw": null, "ls": "--", "marker": "", "ms": null, "alpha": 1,
             "visible": true, "yaxis": "left", "xshift": 0, "yshift": 0, "xunit": "us", "meta": {}}],
 "annotations": [{"kind": "xline", "id": 1, "value": 250, "x": 0, "y": 0, "text": "sync", "color": "#444444",
                  "lw": 0.5, "ls": "-", "alpha": 0.7, "fontsize": null, "axes_key": "left", "ha": "left", "va": "bottom",
                  "boxed": true, "visible": true}],
 "tips": [{"uid": 1, "index": 1000, "id": 1, "offset": [5, 5], "axes_key": null, "text": null}],
 "next_uid": 2, "next_ann_id": 2, "next_tip_id": 2}
```
`uid`／`id` 要唯一且 ≥ 1（讀檔時不唯一會自動重編）。等差的 x 會存成 `{"start","step","n"}`、整數值存成整數；NaN 會原樣輸出（Python 的 json 可讀）。
`view` 裡 `null` 表示自動範圍；視窗存檔時會寫目前的實際範圍。

## 風格
- 預設跟介面主題：深色主題 → `matlab-dark`、淺色 → `matlab`，1.0.0 的六個外觀主題各用自己配好的風格（`sony-black`、`sony-blue`、`apple-light`、`apple-dark`、
  `apple-dark-graphite`、`apple-dark-black`；主題色票的 `plot_style`，`T.plot_style_name()` 回傳目前的）（`pk.figure(style=None)`）。明確給 `style=` 就用指定的。
- 圖片視窗工具列的「繪圖風格」下拉（`widgets.style_choices()`）：0.9.14 的三個（`default`／`matlab`／`matlab-dark`）＋目前介面主題的風格＋這張圖現在用的風格；
  只有三個時寬 11（和 0.9.14 一樣），多了才放寬到放得下最長的名稱；換主題後（重畫時、打開下拉時）跟著更新。
- `default`：matplotlib tab10 色序、線寬 1.0、四邊框、刻度朝外、格線透明度 0.3。
- `matlab`（2026-10-21 對照 MATLAB R2025a 出廠預設）：7 色序 `#1171be #dd5400 #edb120 #8516d1 #3baa32 #2fbeef #d1048b`、線寬 0.5、
  只畫左下兩軸、刻度朝內、格線實線透明度 0.15、Helvetica／Arial（中文自動 fallback）、標題粗體 1.1 倍、圖例 9 pt 有框、figure 底色 #f5f5f5。
- `matlab-dark`（`figure(Theme="dark")` 實測）：色序 `#268cdd #f57729 #ffe864 #c05cfb #49db40 #6cf4ff #f267c5`、figure #212121、
  座標區 #121212、文字 #d9d9d9、白色格線透明度 0.25、圖例底 #121212 框 #d9d9d9、四邊框。
- 自訂：`{"base": "matlab", "lw": 1.0, "grid": {"alpha": 0.3}}`。可覆寫的鍵：`colors`（色序 list）、`lw`、`ms`、`box`（四邊框）、`tick_dir`（"in"/"out"）、
  `grid` {ls, alpha, color, lw}、`fonts`（字型 fallback 清單）、`fontsize`、`title` {weight, scale}、`label` {scale}、
  `legend` {fontsize, frameon, loc, fancybox, framealpha, edgecolor, facecolor, textcolor}、`fig_face`、`axes_face`、`axes_edge`、`axes_lw`、
  `text_color`、`selected_lw_scale`、`tip` {fc, ec, ec_selected, lw, fontsize, text, marker_face, marker_edge, ms}、`annotation_color`、`annotation_box`、`annotation_fontsize`、`spike_color`。
  風格只套在線條與軸上，不改 matplotlib 的 rcParams，所以兩個視窗可以各用各的風格。

## 介面主題與版面元件（`plotkit.theme`，v0.2）
照 MATLAB R2025a 量出來的介面（量測方法與每個數值的來源：`docs/matlab-ui-spec.md`）。視窗、按鈕、輸入框、樹、表格、分頁、捲軸、
選單、工具提示全部走這套，Windows／macOS／Linux 外觀一樣（不跟系統主題）。需要 Pillow（matplotlib 的相依套件）才有圖示與圓角；沒有時退回純文字按鈕。
1.0.0 起 `T.THEMES` 有八個主題：MATLAB 的 `dark`／`light`（數值和 0.9.14 一樣）與六個外觀主題 `sony_black`、`sony_blue`、`apple_light`、`apple_dark`、
`apple_dark_graphite`、`apple_dark_black`（只換色票與圓角）。每個主題的圓角在 `T.RADIUS_PX`（Sony 黑銀 1、MATLAB 與 Sony 深藍黑 3、Apple 5）；
介面上顯示的名稱用 `T.theme_label(name)`／`T.theme_labels()`，反查用 `T.theme_from_label(label)`；深淺分支一律看 `T.is_dark(色)`，不看主題名稱。
```python
import plotkit.theme as T
th = T.apply(root, "dark")            # 或 "light"、1.0.0 的外觀主題（T.THEMES 八個）；可重複呼叫切換（既有元件會重新上色）
th["bg"], th["text"], th.px(10)       # 色票（docs 第 1 節的語意名）、依 DPI 換算的像素
strip = T.Toolstrip(root); strip.pack(fill="x")
tab = strip.add_tab("首頁"); sec = tab.section("檔案")
sec.button("匯入…", icon="import", command=fn, big=True)         # 大按鈕：圖示在上
col = sec.column(); sec.button("匯出設定", icon="export", command=fn, col=col)   # 小按鈕：一欄最多三列
sec.toggle("自動還原", tk_var, icon="refresh", col=col)           # 開關（底色＝MATLAB 圖上工具列開關按下的顏色）
strip.qab_button("save", "存檔", fn)                             # 右上快速存取
panel = T.Panel(root, "資料夾", tools=[("expand", "展開全部", fn)])   # 23px 標題列＋1px 框，可收合、可被選
ttk.Treeview(panel.body).pack(fill="both", expand=True)
bar = T.PlotToolbar(root, canvas)      # 取代 NavigationToolbar2Tk 的外觀；bar.nav 是原本的工具列物件（home/pan/zoom/save 照用）
bar.add_toggle("tips", "datatip", "資料提示", tk_var, fn, before="pan")   # before＝插在某個既有按鈕前面（預設接在最後）
bar.add_button("clip", "clipboard", "複製", fn, before="tips"); bar.add_separator(before=None)
T.status_bar(root, tk_var).pack(side="bottom", fill="x")
T.tooltip(widget, "說明文字"); T.placeholder(entry, "搜尋")
```
- 色票鍵：`bg bg2 bg3 input stripe hover selected selected_focus list_hover toggle_on toolbar_on strip strip_hover strip_selected
  panel_header_sel scroll scroll_hover scroll_active border border2 focus border_hover text text2 text3 error warning success link
  tab tab_selected icon_fg icon_fg2 icon_fill accent orange green red plot_style`。
- ttk 樣式：`TButton`（圓角 3px、1px 框）、`Primary.TButton`（藍底白字）、`Tool.TButton`／`Tool.TCheckbutton`（工具列：透明、hover 才有框）、
  `Qab.TButton`、`StripTab.TRadiobutton`、`Section.TLabel`、`PanelTitle.TLabel`、`Status.TLabel`、`Hint.TLabel`、`Small.TLabel`、`Warn.TLabel`、
  `Error.TLabel`、`Bold.TLabel`、`Title.TLabel`。
- 圖示：`plotkit.icons`，`I.names()` 列清單，`th.icon("home", 16)` 取主題配色的 PhotoImage，`th.bind_icon(widget, "home")` 讓它跟著主題換色。
- `T.listen(obj)`：切換主題時呼叫 `obj.on_theme(theme)`；`T.plot_style_name()` 是目前主題對應的繪圖風格名。
- 窄視窗（0.9.14，DSV 的 Windows 高 DPI W10）：`T.NARROW_LAYOUT`（Windows 才是 True）開著時，`Toolstrip` 放不下就改用窄分頁鈕
  （`Compact.StripTab.TRadiobutton`）、還放不下就分頁列左右捲動；分頁內容比工具列寬時兩端出現 ◀ ▶（`StripArrow.TButton`、滾輪也可以），
  `strip.narrow_state()` 看目前狀態；`T.flow_row(frame)`：一排 `pack(side="left")` 的欄位放不下就換行；`T.window_size(win, w, h)`：新視窗的起始大小
  （Windows 照 DPI 放大、不超過工作區 `T.work_area()` 的 95%／90%；macOS 原樣回傳）；`T.apply()` 在 Windows 會裝 `install_keep_on_screen`——
  每個頂層視窗第一次出現時整個框放進工作區（`T.fit_on_screen(win)`）；`Dock`：中欄（圖）至少留 Dock 寬的 45%（`Dock.CENTER_MIN_SHARE`；右欄第一次出現、或視窗變窄時，左右欄照它們要的寬度比例分剩下的——以前 175% 的窄視窗裡資料游標的讀數一出現，圖那一欄就被擠成 0、整個看不到）；中欄最上面的固定面板（圖）
  至少留 `Dock.CENTER_FIXED_MIN_PX`（160 px，照 DPI 放大、不超過欄高一半；重排與中欄大小改變時檢查——1920×1080、175% 時量測面板換行變高，以前把圖擠到 unmap）。macOS 不開，和以前完全一樣。
  高 DPI 的宣告在 `T.enable_windows_dpi_awareness()`（Windows：per-monitor v2 → per-monitor → system，回傳用了哪一種、記在 `T.WINDOWS_DPI_AWARENESS`；macOS、Linux 回 ""）：
  DSV 啟動時叫它；單獨跑 `python -m plotkit 圖.json`、`--demo` 也在開圖之前叫（2026-10-30 使用者決定，和 DSV 一樣；以前不宣告，Windows 高 DPI 時這種單獨開的視窗由系統點陣放大、字會糊）。

## 語言（plotkit.i18n）
介面字串在原始碼裡是繁體中文（這些中文就是翻譯表的鍵），`plotkit.i18n.tr()` 依目前語言回傳翻譯；套件層級直接用 `pk.tr` / `pk.set_language` / `pk.get_language`。
```python
import plotkit as pk
pk.set_language("en")             # "zh"（預設）或 "en"；也接受 "en_US"、"English"、"繁體中文"；回傳正規化後的代碼
pk.get_language()                 # -> "en"
pk.tr("匯入 CSV…")                # -> "Import CSV…"；目前是中文或沒有翻譯時回傳原文
pk.tr("{n} 條訊號").format(n=3)   # 有參數的字串：先 tr() 再 .format()（鍵裡的 {名稱} 佔位符要原樣保留）
w = pk.figure(title="demo")       # 在 set_language 之後建立的視窗（選單、右鍵選單、清單、對話框、狀態列、工具提示）都是英文
```
- 切換語言不會重畫已經建好的視窗，只影響之後建立的；要整個程式換語言請在建視窗前呼叫。DSV 是把偏好存進設定檔（`view.lang`）再重開程式（跟 MATLAB 一樣）；
  也可以用 `python signal_viewer.py --lang en` 或環境變數 `DSV_LANG=en`。
- 翻譯表是 `plotkit/i18n_<code>.py` 裡的 `CATALOG` dict（中文 → 該語言），`catalog()` 第一次用到時才 import。英文表 `plotkit/i18n_en.py` 是由
  好幾個部分模組 `plotkit/i18n_en_<部分>.py` 合併的，**以 `plotkit/i18n_en.py` 裡 `for _part in (…)` 的清單為準**（後面的部分會覆蓋前面同鍵的值）。
  1.0.0 的 23 個部分（0.9.14 的 22 個＋`0915s`，外觀主題）：`core`（偏好設定／啟動）、`plotkit`（plotkit 的視窗、主題、互動、對話框、剪貼簿、模型）、
  `dsv1`／`dsv2`／`dsv3`（`signal_viewer.py`，依原始碼順序）、`tools`／`tools_d`／`tools_e`（2026-10 的工具批次）、`keys`（鍵盤快速鍵）、
  `folder`（資料夾面板）、`iq`（AM/PM/FM 視窗）、`batch1`／`batch2`／`batch3`／`batch4`（第一～四批）、`fix1`／`fix2`／`fix3`（第 10～12 項的修正輪）、
  `i13`（第 13 項）、`axnames`（軸名稱與標題）、`0913x`（0.9.13 的 B1、B3；0.9.14 每個版本各自的備份、問「最後一次工作」那份）、`0914p`（0.9.14 開著時檔案出問題留佔位、擷取不擷取、關閉時提醒還有檔案沒處理）、`0915s`（1.0.0 的外觀主題名稱與狀態列）。每個部分檔都要同時列在 `i18n_en.py` 的清單和 `plotkit/i18n.py` 的
  `_pyinstaller_hints()`（打包時才會收進去）；`python -m plotkit --selftest` 會核對兩邊都沒漏。
- **新增一種語言**：建一個 `plotkit/i18n_<code>.py`，內容是 `CATALOG = {"中文原文": "翻譯", ...}`（鍵要和原始碼裡的字串完全一致，含標點、空白與「…」；
  `{名稱}` 佔位符要和原文一樣），然後把代碼加進 `plotkit/i18n.py` 的 `LANGUAGES`（例如 `"ja": "日本語"`），需要的別名加到 `_ALIASES`。
  DSV 的偏好設定下拉選單會自動列出 `LANGUAGES` 裡的語言；沒有翻譯的鍵會顯示中文原文，不會壞。
- 檢查工具：`plotkit.i18n.missing_keys(code, [檔案…])` 列出原始碼裡有 `tr("…")` 但翻譯表沒有的鍵（只抓單純字串字面值）；
  `placeholder_mismatches(code)` 列出佔位符和原文不一致的鍵。`python -m plotkit --selftest` 會對英文表跑這兩項檢查，並確認英文翻譯裡沒有中文。

## 沒有 tkinter 的環境
`import plotkit` 仍可用：資料模型、JSON、`draw_state`／`draw_annotation`／`draw_tip`（搭配 Agg 出 PNG）、`Interactor` 都不需要 Tk；
`pk.figure()` 會丟 RuntimeError。`python -m plotkit --selftest` 就是在 Agg 上跑的。

## 已知限制
- marker 在超過 50,000 點的線上不會畫（會讓 matplotlib 變很慢）。
- 文字標註與資料提示的「拖曳」用 blit，超大圖（數百萬點）第一下會慢一點。
- 風格的字型以系統有安裝的為準：Windows 用 Microsoft JhengHei／Arial，macOS 用 PingFang／Heiti／Helvetica。
- 資料提示只能釘在樣本點上（不內插）。
