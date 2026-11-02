# -*- coding: utf-8 -*-
"""英文介面的自動測試（Mac：用 /opt/anaconda3/bin/python3，HOME 指到暫存）：
整個 app 用 lang="en" 建起來，走過所有元件、分頁、次要視窗與一串動作後的狀態列，不能剩任何中文。"""
import glob
import os
import re
import shutil
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
# 輸出資料夾：沒指定 DSV_TEST_OUT 時每次執行用自己的暫存資料夾（和 tests_gui_mac.py 一樣用 mkdtemp）。以前固定是 $TMPDIR/dsv_i18n_test，
# 兩份同時跑（兩個 clone、別的 workflow）時互相 rmtree／copytree samples，copytree 丟 FileExistsError 假失敗，也可能刪掉另一份正在用的檔案。
# 自己建的資料夾全部通過就刪掉，有失敗時留著（最後印出路徑）
OWN_OUT = not os.environ.get("DSV_TEST_OUT")
OUT = os.environ.get("DSV_TEST_OUT") or tempfile.mkdtemp(prefix="dsv_i18n_")
_TMP = os.path.join(OUT, "tmp")                 # 暫存資料夾也用自己的：複製圖的暫存檔不留在系統共用的暫存資料夾（第 2 輪修正；同 tests_gui_mac.py）
os.makedirs(_TMP, exist_ok=True)
os.environ["TMPDIR"] = os.environ["TEMP"] = os.environ["TMP"] = _TMP
tempfile.tempdir = _TMP
os.makedirs(OUT, exist_ok=True)
# 資料夾面板用 samples 的複本（add_all_visible 會把資料夾裡看得到的檔全部讀進來，用複本避免動到 repo 裡的檔；本機才有的大型範例資料夾不複製）
SAMPLES = os.path.join(OUT, "samples")
shutil.rmtree(SAMPLES, ignore_errors=True)
shutil.copytree(os.path.join(HERE, "samples"), SAMPLES, ignore=shutil.ignore_patterns("e2e_all_modes_*"))
import signal_viewer as sv          # noqa: E402
import plotkit as pk                # noqa: E402
from plotkit.i18n import set_language, get_language, tr, LANGUAGES   # noqa: E402

sv.AUTOSAVE_PATH = os.path.join(OUT, "autosave.json")
sv.LOG_PATH = os.path.join(OUT, "signal_viewer.log")
sv.frozen_data_dir = lambda: os.path.join(OUT, "frozen")   # 改成獨立訊號的 .npy（U8）也寫到測試目錄
CJK = re.compile(r"[　-〿㐀-䶿一-鿿＀-￯]")
results = []


class _MB:
    def __getattr__(self, name):
        def f(*a, **k):
            print(f"[messagebox.{name}] {a[:2]}")
            return True if name.startswith("ask") else None
        return f


sv.messagebox = _MB()
pk.dialogs.messagebox = _MB()


def check(cond, msg):
    results.append((bool(cond), msg))
    print(("ok   " if cond else "FAIL ") + msg)


def cjk_in(w, path=""):
    """回傳 widget 樹裡所有含中文的文字 (path, option, text)。"""
    found = []
    try:
        cls = w.winfo_class()
    except Exception:
        return found
    name = f"{path}/{cls}"
    for opt in ("text", "title"):
        try:
            val = str(w.cget(opt))
            if val and CJK.search(val):
                found.append((name, opt, val))
        except Exception:
            pass
    tip = getattr(w, "_pk_tip", None)              # plotkit.theme.tooltip 留在元件上的 tooltip 文字
    if tip and CJK.search(str(tip)):
        found.append((name, "tooltip", str(tip)))
    if cls == "Treeview":
        try:
            for c in w["columns"] or ():
                h = w.heading(c, "text")
                if CJK.search(str(h)):
                    found.append((name, f"heading {c}", h))
            for iid in w.get_children(""):
                for v in list(w.item(iid, "values")) + [w.item(iid, "text")]:
                    if isinstance(v, str) and CJK.search(v):
                        found.append((name, f"row {iid}", v))
        except Exception:
            pass
    if cls == "Listbox":
        try:
            for i in range(w.size()):
                if CJK.search(w.get(i)):
                    found.append((name, f"item {i}", w.get(i)))
        except Exception:
            pass
    if cls == "Text":
        try:
            t = w.get("1.0", "end")
            m = CJK.search(t)
            if m:
                found.append((name, "text", t[max(0, m.start() - 20):m.start() + 40].replace("\n", " ")))
        except Exception:
            pass
    if cls == "Menu":
        try:
            n = w.index("end")
            for i in range(0, (n or -1) + 1):
                try:
                    lab = w.entrycget(i, "label")
                    if CJK.search(str(lab)):
                        found.append((name, f"entry {i}", lab))
                except Exception:
                    pass
        except Exception:
            pass
    for ch in w.winfo_children():
        found += cjk_in(ch, name)
    return found


def fig_cjk(fig):
    """圖上含中文的文字。使用者打的字（panel 的名稱、標題、y 單位、大標題：2026-10-26 新功能）不翻譯，照原樣畫，不算：
    DSV 把畫出來的那一段記在文字物件的 _dsv_user_shown／_dsv_user_fixed，扣掉之後剩下的（P 編號、單位、「右軸」…）不能有中文。"""
    out = []
    try:
        for t in fig.findobj(match=lambda a: hasattr(a, "get_text")):
            s_ = t.get_text()
            for u in list(getattr(t, "_dsv_user_shown", None) or []) + list(getattr(t, "_dsv_user_fixed", None) or []):
                if u:
                    s_ = s_.replace(u, "")
            if s_ and CJK.search(s_):
                out.append(s_)
    except Exception:
        pass
    return out


set_language("en")
from tests_common import install_quiet   # 安靜模式：測試視窗透明、不搶前景（DSV_TEST_SHOW=1 才顯示）
install_quiet()
app = sv.SignalViewer(root_dir=SAMPLES, autorestore=False, lang="en")
app.geometry("1500x900+40+40")
steps = []


def step(fn):
    steps.append(fn)
    return fn


@step
def s1_language():
    check(get_language() == "en" and app.v["lang"].get() == "en", "lang=en：語言設定與 view.lang")
    check(tr("偏好設定") == "Preferences" and "en" in LANGUAGES, "tr() 回英文")
    check(app.strip.tabs["home"].text == tr("首頁") and tr("首頁") == "Home", "toolstrip 分頁名稱是英文")


@step
def s2_main_window():
    app.expand_tree(True)
    app.add_all_visible()
    app.plot()
    for key in ("home", "signal", "preprocess", "analyze", "view"):
        app.strip.select(key)
        app.update()
    app.strip.select("home")
    left = cjk_in(app, "app") + [("app", "title", app.title())] * bool(CJK.search(app.title()))
    check(not left, f"主視窗沒有中文（剩 {len(left)}：{[x[2][:30] for x in left[:6]]}）")
    ft = fig_cjk(app.fig)
    check(not ft, f"主圖上沒有中文（{ft[:3]}）")
    check(not CJK.search(app.status_var.get()), f"狀態列英文：{app.status_var.get()[:80]}")


@step
def s3_actions():
    msgs = []

    def grab(label):
        msgs.append((label, app.status_var.get()))

    sigs = app.signals
    app.sig_tree.selection_set([f"s{sigs[0].uid}"])
    app.set_despike(True); grab("despike on")
    app.undo_action(); grab("undo")
    app.redo_action(); grab("redo")
    app.merge_panels(); grab("merge")
    app.split_panels(); grab("split")
    app.sort_by_name(); grab("sort")
    app.v_tips.set(True); app._on_tips_toggle(); grab("tips on")
    app.v_tips.set(False); app._on_tips_toggle()
    app.v["wheel_zoom"].set(False); app._on_wheel_zoom_toggle(); grab("wheel off")
    app.v["wheel_zoom"].set(True); app._on_wheel_zoom_toggle()
    app.copy_signals(); grab("copy")
    w = app.copy_to_new_window(); grab("copy to window")
    app.toggle_visible([sigs[0]]); grab("hide")
    app.toggle_visible([sigs[0]]); grab("show")
    # 批次 A：量測面板、轉態、Normalize Y（狀態列、表格、面板資訊都要英文）
    app.v_panel["meas"].set(True); app._toggle_panel("meas"); grab("meas panel on")
    app.sig_tree.selection_set([f"s{sigs[0].uid}"]); app.update(); app._on_list_select()
    app.update_measurements()
    app.copy_measurements(); grab("copy measurements")
    app.goto_transition(1); grab("next transition")
    app.goto_transition(-1); grab("previous transition")
    app.v["normalize"].set(True); app._on_view_toggle("normalize"); grab("normalize on")
    app.v["normalize"].set(False); app._on_view_toggle("normalize")
    app.v_meas_row["max"].set(False); app._on_meas_row_toggle("max")
    left_m = cjk_in(app.meas_panel, "meas") + [("meas", "info", app.meas_info.get())] * bool(CJK.search(app.meas_info.get()))
    check(not left_m and app.meas_tree.item("g_stats", "text") == "Signal Statistics",
          f"量測面板（表格、範圍、說明）是英文（剩 {[x[2][:30] for x in left_m[:4]]}）")
    app.set_meas_rows(sv.MEAS_ROW_KEYS)
    app.v_panel["meas"].set(False); app._toggle_panel("meas"); grab("meas panel off")
    # 批次 B：資料游標（游標量測面板、狀態列）、資料提示（Δ、匯出、提示內容）
    app.set_dcursor_mode("two"); grab("data cursors on")
    app.v["dcursor_snap"].set(True); app._on_dcursor_snap(); grab("snap on")
    app.v["dcursor_lock"].set(True); app._on_dcursor_lock(); grab("lock on")
    app.center_dcursors(); grab("cursors into view")
    app.v["meas_range"].set("cursors")
    app.copy_cursor_readout(); grab("copy cursor readout")
    left_c = cjk_in(app.cursor_panel, "cursors") + [("cursors", "info", app.dcursor_info.get())] * bool(CJK.search(app.dcursor_info.get()))
    check(not left_c and app.dcursor_tree.heading("c1", "text") == "Cursor 1" and app.dcursor_mode_label.get() == "Two"
          and "Between cursors" in app.meas_range_cb.cget("values"),
          f"游標量測面板、量測範圍「兩游標之間」是英文（剩 {[x[2][:30] for x in left_c[:4]]}）")
    m = app._dcursor_menu()
    ml = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) != "separator"]
    check(not [x for x in ml if CJK.search(x)], f"資料游標選單是英文（{ml}）")
    m.destroy()
    app.v["meas_range"].set("view")
    app.v["dcursor_snap"].set(False); app._on_dcursor_snap()
    app.v["dcursor_lock"].set(False); app._on_dcursor_lock()
    app.set_dcursor_mode("none"); grab("data cursors off")
    app.v_tips.set(True); app._on_tips_toggle()
    tsig = next(s for s in sigs if sv.np.isfinite(s.get_data()).any())   # samples 裡的 README.txt 也被讀成訊號（整份文字＝NaN），提示要釘在有數值的訊號上
    t1 = app.ia.add_tip(tsig.uid, 5); grab("tip 1")
    t2 = app.ia.add_tip(tsig.uid, 9); grab("tip delta")
    app.ia.copy_tips(); grab("copy tips")
    app.ia.export_tips(os.path.join(OUT, "tips.txt")); grab("export tips")
    ann = app.ia.tip_artists[t1.id][0]
    il = [it[0] for it in app.ia.menu_items(pk.Hit("tip", ann.axes, ann, t1.id)) if it]
    dlg = app.tip_fields_dialog()
    left_d = cjk_in(dlg, "tipfields") + [("tipfields", "title", dlg.title())] * bool(CJK.search(dlg.title()))
    dlg.vars["index"].set(True); dlg.ok(); grab("tip fields")
    check(not left_d and not [x for x in il if CJK.search(x)] and "Index" in app.ia.tip_artists[t1.id][0].get_text(),
          f"提示內容對話框、提示框右鍵選單是英文（{il}；剩 {[x[2][:30] for x in left_d[:3]]}）")
    head, _rows = app.ia.tips_table()
    check(not [h for h in head if CJK.search(h)], f"匯出資料提示的標題列是英文（{head}）")
    app.ia.set_tip_fields(pk.DEFAULT_TIP_FIELDS)
    app.ia.clear_tips()
    app.v_tips.set(False); app._on_tips_toggle()
    # 批次 C：繪圖類型、I/Q 幅度／相位（狀態列、選單、清單、圖上都要英文）
    app.sig_tree.selection_set([f"s{sigs[0].uid}"]); app.update(); app._on_list_select()
    app.set_plot_type("stem"); grab("plot type stem")
    pm = app._ptype_menu()
    pl = [pm.entrycget(i, "label") for i in range(pm.index("end") + 1) if pm.type(i) == "radiobutton"]
    pm.destroy()
    check(pl == ["Line", "Stairs", "Stem"] and app.p_ptype.get() == "Stem", f"繪圖類型選單與訊號參數是英文（{pl} {app.p_ptype.get()}）")
    app.set_plot_type("stairs"); grab("plot type stairs")
    app.sig_tree.selection_set([f"s{s_.uid}" for s_ in sigs[-2:]]); app.update(); app._on_list_select()
    der = app.add_iq_magphase(); grab("iq magnitude/phase")
    app.sig_tree.selection_set([f"s{s_.uid}" for s_ in der]); app.update(); app._on_list_select()
    app.v["iq_unwrap"].set(True); app._on_iq_unwrap(); grab("unwrap phase")
    app.v["iq_unwrap"].set(False); app._on_iq_unwrap(); grab("wrap phase")
    left_l = cjk_in(app.sig_tree, "list")
    check(len(der) == 2 and not left_l and not fig_cjk(app.fig), f"衍生訊號的清單列與圖上沒有中文（{[x[2][:30] for x in left_l[:3]]}）")
    app.remove_selected(); grab("remove derived")
    # 批次 E（第四批）：前處理 → 去趨勢／低通 套用到選取的訊號（狀態列、清單列、面板文字、選到結果時的參數摘要都要英文）
    fsig = next(s for s in sigs if sv.np.isfinite(s.get_data()).all() and len(s.get_data()) > 10)   # 要全部有限（MATLAB 不處理有 NaN 的訊號）
    app.sig_tree.selection_set([f"s{fsig.uid}"]); app.update(); app._on_list_select()
    pw = app.open_preprocess("detrend"); grab("open detrend")
    res = pw.apply(); grab("apply detrend")
    pw.set_function("lowpass"); pw.set_form(dict(sv.dsv_preprocess.default_form("lowpass"), fpass="")); pw._relayout()
    pw.apply(); grab("apply lowpass (empty passband)")
    pp_err = [v.get() for v in pw.errs.values() if v.get()] + [pw.v_msg.get(), pw.v_target.get(), str(pw.header.cget("text"))]
    left_p = cjk_in(pw, "preprocess") + [("preprocess", "text", x) for x in pp_err if CJK.search(x)]
    if res["new"]:
        app.sig_tree.selection_set([f"s{res['new'][0].uid}"]); app.update(); app._on_list_select(); grab("select derived (params summary)")
        left_p += [("preprocess", "list", x[2]) for x in cjk_in(app.sig_tree, "list")]
    check(res["new"] and not left_p and pw.errs["fpass"].get() == "Passband frequency must be a positive scalar",
          f"前處理面板（標題、欄位、驗證訊息、套用到）、結果的清單列與參數摘要都是英文（剩 {[x[2][:30] for x in left_p[:4]]}）")
    ph_lp = [str(l_.cget("text")) for l_ in pw.placeholders.values()]          # 低通：通帶頻率／阻帶衰減的 placeholder（MATLAB "Enter Value"）
    pw.set_function("envelope"); pw.set_form(dict(sv.dsv_preprocess.default_form("envelope"), emethod="peak")); pw._relayout(); grab("envelope peak")
    env_vals = list(app.tk.splitlist(pw.inputs["emethod"].cget("values")))
    check(pw.vars["emethod"].get() == "Peak" and "Peak" in env_vals and "Peaks" not in env_vals and ph_lp == ["Enter Value", "Enter Value"]
          and not cjk_in(pw, "envelope"),
          f"包絡方法用 MATLAB 的「Peak」（不是量測分頁 PEAKS 區段的「Peaks」）；低通的 placeholder「Enter Value」（{env_vals} {ph_lp}）")
    pw.destroy()
    app.sig_tree.selection_set([f"s{fsig.uid}"]); app.update(); app._on_list_select()
    app.undo_action(); grab("undo preprocess")
    app.sig_tree.selection_set([f"s{sigs[0].uid}"]); app.update(); app._on_list_select()
    app.set_marker("o"); grab("marker")
    app.reset_style(); grab("reset style")
    app.set_yaxis("right"); grab("right axis"); app.set_yaxis("left")
    app.add_annotation("xline", 1, 10.0, 0.0, "left"); grab("xline")
    for i in range(3):
        app.undo_action()
    grab("undo ×3")
    while app.undo.can_undo:
        app.undo_action()
    app.undo_action(); grab("nothing to undo")
    sv.filedialog.asksaveasfilename = lambda **k: os.path.join(OUT, "export.txt")
    sv.filedialog.askopenfilename = lambda **k: os.path.join(OUT, "settings.json")
    app.export_txt(); grab("export txt")
    app.save_settings(os.path.join(OUT, "settings.json")); grab("save settings")
    app.load_settings(os.path.join(OUT, "settings.json")); grab("load settings")
    bad = [(l, m) for l, m in msgs if CJK.search(m)]
    check(not bad, f"一串動作後的狀態列都是英文（{len(msgs)} 則；有中文：{bad[:4]}）")
    diag = [ln for ln in app.diag_text().splitlines() if CJK.search(ln) and "samples" not in ln]
    check(not diag, f"診斷文字沒有中文（{diag[:3]}）")
    if w is not None:
        left = cjk_in(w, "figwin")
        check(not left and not fig_cjk(w.pc.fig), f"圖片視窗沒有中文（{[x[2][:30] for x in left[:4]]}）")
        w.close()


@step
def s4_windows():
    wins = []
    try:
        wins.append(("Help", sv.HelpWindow(app)))
        wins.append(("Diag", sv.DiagWindow(app)))
        d = sv.PreferencesDialog(app); d.grab_release(); wins.append(("Prefs", d))
        csvs = glob.glob(os.path.join(SAMPLES, "**", "*.csv"), recursive=True)
        c = sv.CsvImportDialog(app, csvs[0], sv.get_csv_table(csvs[0])); c.grab_release(); wins.append(("CSV", c))
        if not app.signals:                 # s3 最後把 undo 全部復原掉了：重新加入，頻譜／GFSK／星座圖視窗才真的會開
            app.add_all_visible()
            app.plot()
        iqs = [s_ for s_ in app.signals if s_.column in ("adc i", "adc q")][:2] or app.signals[-2:]
        app.sig_tree.selection_set([f"s{s_.uid}" for s_ in iqs])
        app.open_spectrum()
        app.open_gfsk()
        app.open_constellation()
        app.open_eye()                     # 第四批 T4：眼圖視窗（選了 I、Q 兩條 → 同相、正交兩張）
        app.open_errrate()                 # 第四批 T5：錯誤率比對視窗（選了兩條 → TX、RX；類比格式先提示）
        for fn_ in ("bandpass", "smooth", "resample", "envelope"):      # 第四批：前處理「函式參數」面板（每個函式換一次內容）
            pw_ = app.open_preprocess(fn_)
        pw_.set_form(dict(sv.dsv_preprocess.default_form("envelope"), emethod="peak")); pw_._relayout()
        wins.append(("Preprocess", pw_))
    except Exception:
        traceback.print_exc()
        check(False, "次要視窗開啟時例外")
    app.update()
    tops = [c for c in app.winfo_children() if c.winfo_class() == "Toplevel"]
    left = []
    for t in tops:
        left += cjk_in(t, f"top[{t.title()}]")
        if CJK.search(str(t.title())):
            left.append((t.title(), "title", t.title()))
        f = getattr(t, "fig", None)
        if f is not None:
            left += [("fig", "text", x) for x in fig_cjk(f)]
    check(len(tops) >= 5, f"開了 {len(tops)} 個次要視窗（說明／診斷／偏好／CSV／頻譜／GFSK／星座圖）")
    sw = next((t for t in tops if isinstance(t, sv.SpectrumWindow)), None)
    cw = next((t for t in tops if isinstance(t, sv.ConstellationWindow)), None)
    if sw is not None:
        sw.v_unit.set("dBFS"); sw.set_spectrum_type("power")
        left += [("spectrum", "info", sw.v_info.get())] * bool(CJK.search(sw.v_info.get()))
        left += [("spectrum", "fig", x) for x in fig_cjk(sw.fig)]
        sw.v_unit.set("dBm"); sw.v_db.set(False); sw.set_spectrum_type("psd")
        left += [("spectrum", "info", sw.v_info.get())] * bool(CJK.search(sw.v_info.get()))
    if cw is not None:
        cw.v_ref_label.set("QPSK"); cw.compute()
        for txt in (cw.v_status.get(), cw.v_msg.get(), cw.title()):
            left += [("constellation", "text", txt)] * bool(CJK.search(txt))
        left += [("constellation", "fig", x) for x in fig_cjk(cw.fig)]
    check(sw is not None and cw is not None and "NENBW" in sw.v_info.get(), "頻譜視窗（類型／單位資訊列）與星座圖視窗都開了")
    if sw is not None:                       # 第三批：英文的下拉選單與表格第一欄放得下、說明列沒有全形標點、同一種錯誤同一句英文
        import tkinter.font as tkfont

        def combos(w_):
            out = [w_] if w_.winfo_class() == "TCombobox" else []
            for ch in w_.winfo_children():
                out += combos(ch)
            return out
        want_vars = {str(v) for v in (sw.v_cm_type_label, sw.v_cm_mode_label, sw.v_cm_shape_label, sw.v_dist_type_label, sw.v_mask_ref,
                                      sw.v_layout_label, sw.v_res_label)}
        skip = {str(c) for c in (sw.cb_mchannel, sw.cb_mchannel_m, sw.cb_channel)}     # 項目是訊號名稱（使用者的資料；遮罩的通道是號碼 1、2、…，照樣檢查）
        clipped, seen = [], set()
        for cb in combos(sw):
            vals = cb.cget("values")
            if str(cb) in skip or not vals:
                continue
            seen.add(str(cb.cget("textvariable")))
            fn = tkfont.nametofont(str(cb.cget("font")) or "TkTextFont")
            need = max(fn.measure(str(v)) for v in vals)
            if int(cb.cget("width")) * fn.measure("0") < need:
                clipped.append((vals, int(cb.cget("width")), need))
        check(not clipped and want_vars <= seen,
              f"英文介面：頻譜視窗每一個固定選項的下拉選單都放得下最長的選項（第二批的版面 Horizontal、解析方式 Window Length，第三批的 "
              f"Span and Center Frequency、Intermodulation…；不再截成 Vertic…、Window Lengt…）（{clipped or 'all fit'}）")
        sw.v_hz.set(False); sw.v_unit.set("dBm"); sw.v_db.set(True); sw.set_spectrum_type("psd"); sw.set_distortion(type="harmonic", on=True); app.update()
        lab = sw.harm_tree.item("power", "text")
        import plotkit.theme as _T
        need = _T.current().font("default").measure(lab)
        check(lab == "Power Density (dBm/(cycles/symbol))" and int(sw.harm_tree.column("#0", "width")) >= need,
              f"英文介面：諧波失真面板第一欄放得下最長的列名「{lab}」（{sw.harm_tree.column('#0', 'width')} px ≥ {need} px）")
        sw.v_hz.set(True); sw.set_spectrum_type("power"); sw.set_distortion(on=False)
        sw.set_chmeas(on=True, mode="startstop", start=3000, stop=2000); app.update()
        m_obw = sw.v_msg.get()
        sw.set_chmeas(type="acpr"); app.update()
        m_acpr = sw.v_msg.get()
        check("Stop frequency must be greater than start frequency." in m_obw and "Stop frequency must be greater than start frequency." in m_acpr
              and sw.chmeas_table()["channel"] != "- -" and not CJK.search(m_obw + m_acpr),
              f"英文介面：開始 ≥ 停止時佔用頻寬與 ACPR 是同一句英文，面板第一欄照樣寫通道名稱（{m_acpr[:70]}）")
        sw.set_chmeas(on=False, type="obw", mode="span")
        # 第三批 T3：遮罩欄位的錯誤真的經過 _on_mask_field，英文介面顯示 MATLAB 的英文（下遮罩寫 lower，不照抄 MATLAB 的筆誤 upper）；
        # 提示、說明列、狀態列都是同一句，改回合格的值後狀態列換回去
        en_fields = (("upper", "abc", "Enter upper mask as a real, numeric scalar or two-column matrix with at least two rows."),
                     ("lower", "[1 2]", "Enter lower mask as a real, numeric scalar or two-column matrix with at least two rows."),
                     ("ref", "xyz", "Enter reference level as 'Spectrum peak' or as a finite real scalar."),
                     ("offset", "", "Enter spectral mask frequency offset as a finite real scalar."),
                     ("upper", "[100 -10; 50 -10]", "When the UpperMask property value is a matrix, the first column representing frequency values "
                                                    "of the mask must be non-NaN and non-decreasing."),
                     ("lower", "[NaN -10; 50 -10]", "When the LowerMask property value is a matrix, the first column representing frequency values "
                                                    "of the mask must be non-NaN and non-decreasing."))
        en_bad = []
        for key, txt, want in en_fields:
            var = {"upper": sw.v_mask_upper, "lower": sw.v_mask_lower, "ref": sw.v_mask_ref, "offset": sw.v_mask_offset}[key]
            wdg = {"upper": sw.e_mask_upper, "lower": sw.e_mask_lower, "ref": sw.cb_mask_ref, "offset": sw.e_mask_offset}[key]
            before, s0 = var.get(), sw.v_status.get()
            var.set(txt); sw._on_mask_field(key); app.update()
            tip, msg, stat = wdg._pk_tip, sw.v_msg.get(), sw.v_status.get()
            var.set(before); sw._on_mask_field(key); app.update()
            if not (tip == want and want in msg and stat == "Spectral mask: " + want and not CJK.search(tip + msg + stat)
                    and sw.v_status.get() == s0):
                en_bad.append((key, txt, tip[:40], stat[:40]))
        u0_, l0_ = sw.v_mask_upper.get(), sw.v_mask_lower.get()      # 兩個欄位同時錯：先改好後打錯的那個，狀態列換成還錯著的那個（英文）
        s0_ = sw.v_status.get()
        sw.v_mask_upper.set("[1 2 3]"); sw._on_mask_field("upper"); sw.v_mask_lower.set("abc"); sw._on_mask_field("lower")
        sw.v_mask_lower.set(l0_); sw._on_mask_field("lower"); app.update()
        st_two = sw.v_status.get()
        sw.v_mask_upper.set(u0_); sw._on_mask_field("upper"); app.update()
        st_two_ok = (st_two == "Spectral mask: " + en_fields[0][2] and sw.v_status.get() == s0_)
        sw.set_mask(upper=-200, upper_on=True); sw.v_normal.set(False); sw.v_maxhold.set(False); sw.v_minhold.set(False); sw.compute(); app.update()
        m_nt = sw.v_msg.get()
        sw.btn_mask_clear.invoke(); app.update()
        s_clr = sw.v_status.get()
        sw.v_normal.set(True); sw.compute(); app.update()
        sw.set_mask(ref="spectrum-peak", channel=5); app.update()
        m_fb = sw.v_msg.get()
        sw.btn_mask_clear.invoke(); app.update()
        s_clr2 = sw.v_status.get()
        sw.set_mask(ref=0, channel=0, upper="Inf", upper_on=False); app.update()
        check(not en_bad and st_two_ok and "Spectral mask: plot the normal, max-hold or min-hold trace" in m_nt and s_clr == "Spectral mask: counts cleared"
              and "Spectral mask: the selected channel 6 is not in this window (2 in total); the reference level uses the spectrum peak of channel 1 "
                  "for now (the selection is kept)" in m_fb and s_clr2 == "Spectral mask: counts cleared, the current spectrum was tested again"
              and not CJK.search(m_nt + s_clr + m_fb + s_clr2 + st_two),
              f"英文介面的頻譜遮罩：欄位錯誤（上限、下限、參考位準、頻率偏移、頻率欄 NaN／遞減）的提示、說明列、狀態列都是 MATLAB 的英文，改好後狀態列換回去"
              f"（兩個欄位都錯時先改好後打錯的那個，狀態列換成還錯著的上限）；沒有軌跡、清除計數（沒重測／有重測）、選的通道不在這個視窗時暫用別條的說明"
              f"也是英文（{en_bad or 'fields ok'}、{st_two_ok}、{m_nt[:50]!r}、{s_clr!r}、{m_fb[:50]!r}）")
        # 頻譜視窗數字欄位的單一規則（使用者 2026-10-25 決定；第四輪）在英文介面也一樣：參考位準 12abc、頻率偏移 50abc（以前照工具列 parseFloat 收成
        # 12、50）、矩陣裡的 12abc、諧波數量 0x10（以前當 16）是錯，提示／說明列／狀態列寫 MATLAB 的英文；0.002k、500m、250m 這種 SI 字首照收
        si_en = []
        for key, txt, want in (("ref", "12abc", "Enter reference level as 'Spectrum peak' or as a finite real scalar."),
                               ("offset", "50abc", "Enter spectral mask frequency offset as a finite real scalar."),
                               ("upper", "[0 -17; 12abc -17]", "Enter upper mask as a real, numeric scalar or two-column matrix with at least two rows.")):
            var = {"upper": sw.v_mask_upper, "ref": sw.v_mask_ref, "offset": sw.v_mask_offset}[key]
            wdg = {"upper": sw.e_mask_upper, "ref": sw.cb_mask_ref, "offset": sw.e_mask_offset}[key]
            before = var.get()
            var.set(txt); sw._on_mask_field(key); app.update()
            tip, msg, stat, inv = wdg._pk_tip, sw.v_msg.get(), sw.v_status.get(), wdg.instate(["invalid"])
            var.set(before); sw._on_mask_field(key); app.update()
            if not (inv and tip == want and want in msg and stat == "Spectral mask: " + want and not CJK.search(tip + msg + stat)):
                si_en.append((key, txt, inv, tip[:40], stat[:40]))
        sw.set_mask(ref="0.002k", offset="500m"); app.update()
        acc = (sw._mask_vals["ref"], sw._mask_vals["offset"], sw.cb_mask_ref.instate(["invalid"]), sw.e_mask_offset.instate(["invalid"]))
        sw.set_mask(ref=0, offset=0); app.update()
        sw.set_distortion(nharm="0x10"); app.update()
        nh = (sw.e_dist_nharm.instate(["invalid"]), sw.e_dist_nharm._pk_tip, sw.v_status.get())
        sw.set_distortion(nharm="6"); app.update()
        sw.set_chmeas(coeff="250m"); app.update()
        co = (sw._cm_vals["coeff"], sw.sp_cm_coeff.instate(["invalid"]))
        sw.set_chmeas(coeff="0.5"); app.update()
        nh_want = "Enter number of harmonics as a finite positive real scalar between 2 and 99."
        check(not si_en and acc == (("custom", 2.0), 0.5, False, False) and nh == (True, nh_want, "Distortion: " + nh_want) and co == (0.25, False),
              f"英文介面：頻譜視窗數字欄位的單一規則——參考位準 12abc、頻率偏移 50abc、矩陣裡的 12abc、諧波數量 0x10 是錯，提示／說明列／狀態列寫 MATLAB 的"
              f"英文；參考位準 0.002k＝2、頻率偏移 500m＝0.5、係數 250m＝0.25 照收（{si_en or 'fields ok'}、{acc}、{nh[0]}、{co}）")
        sw.v_res.set("window-length"); sw.v_wlen.set("100000000"); sw.compute(); app.update()
        m_err = sw.v_msg.get()
        check(m_err and "：" not in m_err and not CJK.search(m_err) and ": Only " in m_err,
              f"英文介面：頻譜算不出來的說明「名稱: 原因」用半形冒號（{m_err[:70]}）")
        sw.v_res.set("rbw"); sw.v_wlen.set("1024"); sw.compute(); app.update()
        # 第五輪：收 SI 字首之後打得出來的超大值——衰減 10k（算不出視窗，改回 60）、Chebyshev 6139 dB 在 2048 點算不出來（說明列寫那條訊號）、
        # FFT 長度超過上限 2^24、頻譜圖太大（打的 FFT 長度比 Auto 長、段數 × FFT 長度超過上限）的說明也是英文
        def msg_after():
            try:
                sw.compute(); app.update()
            except Exception as ex_:                             # noqa: BLE001 —— 舊版：衰減 10k 丟 OverflowError
                return f"例外 {type(ex_).__name__}"
            return sw.v_msg.get()
        sw.v_window.set("chebyshev"); sw.v_atten.set("10k")
        m_att = msg_after()
        s_att = sw.v_status.get()
        sw.v_res.set("window-length"); sw.v_wlen.set("2048"); sw.v_atten.set("6139")    # L＝1000 算得出來、2048 點是 NaN
        m_att2 = msg_after()
        sw.v_res.set("rbw"); sw.v_wlen.set("1024"); sw.v_window.set("hann"); sw.v_atten.set("60")
        sw.v_nfft.set("16777217")                                # 剛好超過上限 2^24（舊版真的算一段 16777217 點的 FFT，不是 1G 那種 16 GB）
        m_fft = msg_after()
        s_fft = sw.v_status.get()
        cells0 = getattr(sv, "SPEC_MAX_SG_CELLS", None)     # 只看說明的語言：把上限調小，不必真的算一張很大的頻譜圖（真的上限在 GUI 測試 s30）
        sv.SPEC_MAX_SG_CELLS = 1000
        try:
            sw.v_show_sg.set(True); sw.v_nfft.set("4096"); sw.compute(); app.update()
            m_sg = sw.v_msg.get()
            sw.v_nfft.set("Auto"); sw.compute(); app.update()   # 第六輪：FFT 長度 Auto 也有上限（使用者 2026-10-26 決定），建議的改法不同
            m_sg_auto = sw.v_msg.get()
        finally:
            if cells0 is None:
                del sv.SPEC_MAX_SG_CELLS
            else:
                sv.SPEC_MAX_SG_CELLS = cells0
        sw.v_show_sg.set(False); sw.v_nfft.set("Auto"); sw.compute(); app.update()
        check("Attenuation 10000 dB is too large to compute the window" in m_att and "reset to 60" not in m_att
              and s_att == "Window Options: Attenuation 10000 dB is too large to compute the window"
              and ": Attenuation 6139 dB is too large to compute the window" in m_att2 and "reset to 60" not in m_att2
              and "FFT length can be at most 2^24 (16777216) points" in m_fft and "reset to Auto" not in m_fft
              and s_fft == "Frequency Resolution: FFT length can be at most 2^24 (16777216) points"
              and "segments × FFT length 4096 cells, which is too large, so it is not drawn: reduce the FFT length or set it to Auto" in m_sg
              and re.search(r"segments × FFT length \d+ cells, which is too large, so it is not drawn: reduce the overlap, narrow the main plot range "
                            r"or turn off Reassign", m_sg_auto)
              and not CJK.search(m_att + m_att2 + m_fft + m_sg + m_sg_auto + s_att + s_fft),
              f"英文介面：衰減太大算不出視窗（欄位的錯誤狀態／說明列寫那條訊號）、FFT 長度上限（欄位的錯誤狀態，狀態列「區段: 訊息」）、頻譜圖太大（打的 FFT 長度"
              f"比 Auto 長、FFT 長度 Auto 兩種改法）的說明是英文（{m_att[:60]!r}、{s_att[:60]!r}、{m_att2[:60]!r}、{m_fft[:60]!r}、{m_sg[:90]!r}、"
              f"{m_sg_auto[:90]!r}）")
        # 第六輪（使用者 2026-10-26 決定）：第二批與峰值欄位的錯誤是 MATLAB 的錯誤訊息（英文原文），狀態列前面寫區段名稱（英文）
        fe_en = []
        for var_, txt_, back_, want_ in ((sw.v_atten, "30", "60", "Window Options: Enter sidelobe attenuation as a finite real scalar greater than or equal to 45."),
                                         (sw.v_rload, "0", "1", "Scale: Enter reference load as a finite positive real scalar."),
                                         (sw.v_foffset, "abc", "0", "Bandwidth: Enter frequency offset as a finite real scalar."),
                                         (sw.v_wlen, "2", "1024", "Frequency Resolution: Enter window length as a finite positive real scalar greater than 2."),
                                         (sw.v_overlap, "100", "0", "Window Options: Enter overlap percentage as a finite nonnegative real scalar less than 100."),
                                         (sw.v_clim, "abc", "-80, 20", "Configuration: Enter [cmin cmax], where cmin and cmax are finite scalars.")):
            var_.set(txt_); sw.compute(); app.update()
            st_, msg_ = sw.v_status.get(), sw.v_msg.get()
            var_.set(back_); sw.compute(); app.update()
            if not (st_ == want_ and want_.split(": ", 1)[1] in msg_ and not CJK.search(st_ + msg_)):
                fe_en.append((txt_, st_[:70]))
        sw.v_pk_num.set("0"); sw._on_peak_params(); app.update()
        pk_en = sw.v_status.get()
        sw.v_pk_num.set("3"); sw._on_peak_params(); app.update()
        sw.v_rbw.set("10k"); sw.v_tres.set("10us"); sw.compute(); app.update()
        tr_en = sw.v_status.get()
        sw.v_rbw.set("Auto"); sw.v_tres.set("Auto"); sw.compute(); app.update()
        check(not fe_en and pk_en == "Peaks: Enter number of peaks as a finite positive real scalar between 1 and 99."
              and tr_en == "Time Options: Enter time resolution as a finite positive real scalar larger than or equal to 0.0001 seconds.",
              f"英文介面：第二批與峰值欄位的錯誤（衰減、參考負載、頻寬的偏移、視窗長度 2、重疊、色彩範圍、Num Peaks、時間解析度 < 1/RBW）的狀態列與說明列是 MATLAB 的"
              f"英文錯誤訊息，前面寫區段名稱（{fe_en or 'fields ok'}、{pk_en[:60]!r}、{tr_en[:60]!r}）")
        # 第八輪（使用者 2026-10-26 決定）：灰掉或藏起來的欄位在說明列寫「欄位名稱：訊息（怎麼做才改得到）」、滿刻度與 Min Distance 的上限、Threshold 收 dB、
        # 說明列的大整數用科學記號——英文介面都是英文
        r8 = {}
        nt_ = lambda: sw.v_msg.get().split("; ")                 # noqa: E731
        sw.v_res_label.set(tr("視窗長度")); sw._on_res(); sw.v_wlen.set("2"); sw.compute(); app.update()
        sw.v_res_label.set("RBW"); sw._on_res(); app.update()
        r8["wlen"] = "Window Length: Enter window length as a finite positive real scalar greater than 2. (switch to Window Length mode to edit it)" in nt_()
        sw.v_wlen.set("1024"); sw.compute()
        sw.v_clim.set("abc"); sw.compute(); app.update()
        r8["clim"] = "Color Limits: Enter [cmin cmax], where cmin and cmax are finite scalars. (click Settings… to edit it)" in nt_()
        sw.v_clim.set("-80, 20"); sw.compute()
        sw.set_chmeas(on=True, type="acpr", shape="rrc"); sw.set_chmeas(coeff="2"); sw.set_chmeas(shape="none"); app.update()
        r8["cm"] = ("Channel Measurements Roll-off Factor: Enter filter coefficient as a finite nonnegative real scalar between 0 and 1. "
                    "(set Filter Shape to RRC or Gaussian to edit it)") in nt_()
        sw.set_chmeas(shape="rrc"); sw.set_chmeas(coeff="0.5", shape="none", type="obw", on=False); app.update()
        sw.set_distortion(nharm="0"); sw.set_distortion(type="intermod"); app.update()
        r8["dist"] = ("Distortion Num Harmonics: Enter number of harmonics as a finite positive real scalar between 2 and 99. "
                      "(set Type to Harmonic to edit it)") in nt_()
        sw.set_distortion(type="harmonic"); sw.set_distortion(nharm="6"); app.update()
        sw.set_mask(offset="x"); sw.set_spectrum_type("rms"); app.update()
        r8["mask"] = ("Spectral Mask Frequency Offset: Enter spectral mask frequency offset as a finite real scalar. "
                      "(set the spectrum type to something other than RMS to edit it)") in nt_()
        sw.set_spectrum_type("power"); sw.set_mask(offset="0"); app.update()
        sw.v_unit.set("dBFS"); sw.v_db.set(True); sw.v_fullscale.set("1e155"); sw.compute(); app.update()
        r8["fullscale"] = sw.v_status.get() == "Scale: Full scale 1e+155 is out of range; it must be between 1e-150 and 1e+150"
        sw.v_fullscale.set("Auto"); sw.v_unit.set("dB"); sw.compute()
        sw.v_pk_mindist.set("1e19"); sw._on_peak_params("pk_mindist"); app.update()
        r8["mindist"] = sw.v_status.get() == ("Peaks: Minimum peak distance 10000000000000000000 is too large: a finite value can be at most 2^53 − 1 "
                                              "(9007199254740991); enter Inf to keep only the highest peak")
        sw.v_pk_mindist.set("1"); sw._on_peak_params("pk_mindist")
        sw.v_unit.set("dBm"); sw.compute(); sw.v_pk_thr.set("3 dB"); sw._on_peak_params("pk_thr"); app.update()
        r8["threshold dB"] = (sw.peak_params()[0]["threshold"] == 3.0, "pk_thr" not in sw._fld_errs)
        sw.v_pk_thr.set("0"); sw._on_peak_params("pk_thr"); sw.v_unit.set("dB"); sw.compute()
        sw.v_res_label.set(tr("視窗長度")); sw._on_res(); sw.v_wlen.set("1e300"); sw.compute(); app.update()
        r8["1e+300"] = "fewer than one window (1e+300 samples)" in sw.v_msg.get()
        sw.v_wlen.set("1024"); sw.v_res_label.set("RBW"); sw._on_res(); app.update()
        r8_msgs = sw.v_msg.get() + sw.v_status.get()
        want8 = {"wlen": True, "clim": True, "cm": True, "dist": True, "mask": True, "fullscale": True, "mindist": True, "threshold dB": (True, True),
                 "1e+300": True}
        check(r8 == want8 and not CJK.search(r8_msgs),
              f"英文介面（第八輪）：灰掉或藏起來的欄位的說明列「Window Length: … (switch to Window Length mode to edit it)」、色彩範圍、通道量測的係數、失真的"
              f"諧波數量、頻譜遮罩的頻率偏移；滿刻度與 Min Distance 的上限訊息（狀態列「Scale: …」「Peaks: …」）、Threshold 在 dBm 時收 3 dB、說明列寫 "
              f"1e+300（{ {k_: v_ for k_, v_ in r8.items() if want8.get(k_) != v_} or 'all ok'}）")
        # 第九輪：第八輪沒測到的提示在英文介面也要對——衰減（Hann）、時間解析度與時間跨度（關掉頻譜圖）、遮罩的參考位準（RMS）與下限（線性）用真的操作；
        # 參考負載（兩個檢視都關：介面上到不了，直接改兩個檢視的變數）、通道量測的跨度（開始／停止模式）與停止頻率（跨度模式；程式呼叫 set_chmeas 才會）
        r9 = {}
        sw.v_window_label.set("Kaiser"); sw._on_window(); sw.v_atten.set("30"); sw._fld_enter("atten")
        sw.v_window_label.set("Hann"); sw._on_window(); app.update()
        r9["atten"] = ("Attenuation: Enter sidelobe attenuation as a finite real scalar greater than or equal to 45. (select the Chebyshev or Kaiser "
                       "window to edit it)") in nt_()
        sw.v_window_label.set("Kaiser"); sw._on_window(); sw.v_atten.set("60"); sw._fld_enter("atten")
        sw.v_window_label.set("Hann"); sw._on_window(); app.update()
        sw.set_view("both"); sw.v_tres.set("0"); sw._fld_enter("tres"); sw.v_tspan.set("-1"); sw._fld_enter("tspan")
        sw.btn_view_sg.invoke(); app.update()                       # 關掉頻譜圖：時間選項的分頁藏起來
        r9["tres"] = "Time Resolution: Enter time resolution 'Auto' or as a finite positive real scalar. (turn on the Spectrogram view to edit it)" in nt_()
        r9["tspan"] = "Time Span: Enter time span as 'Auto' or as a finite real positive scalar. (turn on the Spectrogram view to edit it)" in nt_()
        sw.btn_view_sg.invoke(); sw.v_tres.set("Auto"); sw._fld_enter("tres"); sw.v_tspan.set("Auto"); sw._fld_enter("tspan")
        sw.set_view("spectrum"); app.update()
        sw.v_rload.set("0"); sw._fld_enter("rload")
        sw.v_show_spec.set(False); sw.v_show_sg.set(False); sw._set_msg(); app.update()
        r9["rload"] = ("Reference Load: Enter reference load as a finite positive real scalar. (turn on the Spectrum or Spectrogram view to "
                       "edit it)") in nt_()
        sw.set_view("spectrum"); sw.v_rload.set("1"); sw._fld_enter("rload"); app.update()
        sw.set_mask(ref="zz"); sw.set_spectrum_type("rms"); app.update()
        r9["mask ref"] = ("Spectral Mask Reference Level: Enter reference level as 'Spectrum peak' or as a finite real scalar. (set the spectrum type "
                          "to something other than RMS to edit it)") in nt_()
        sw.set_spectrum_type("power"); sw.set_mask(ref="0"); app.update()
        sw.set_mask(lower="abc"); sw.v_unit_label.set(tr("線性")); sw._on_unit(); app.update()
        r9["mask lower"] = ("Spectral Mask Lower Limits: Enter lower mask as a real, numeric scalar or two-column matrix with at least two rows. "
                            "(set the spectrum unit to something other than Linear to edit it)") in nt_()
        sw.v_unit_label.set("dB"); sw._on_unit(); sw.set_mask(lower="-Inf"); app.update()
        sw.set_chmeas(on=True, mode="startstop"); sw.set_chmeas(span="0"); app.update()
        r9["cm span"] = ("Channel Measurements Span: " + tr(sv.CM_MESSAGES["span"]) + " (set Frequency Span to Span and Center Frequency to edit it)") in nt_()
        sw.set_chmeas(mode="span"); sw.set_chmeas(stop="x"); app.update()
        r9["cm stop"] = ("Channel Measurements Stop Frequency: " + tr(sv.CM_MESSAGES["stop"])
                         + " (set Frequency Span to Start and Stop Frequencies to edit it)") in nt_()
        sw.set_chmeas(mode="startstop"); sw.set_chmeas(mode="span", on=False); app.update()
        r9["all fixed"] = (sw.v_msg.get() == "" or "to edit it" not in sw.v_msg.get(), not sw._fld_errs and not sw._cm_errs and not sw._mask_errs)
        r9_msgs = sw.v_msg.get() + sw.v_status.get()
        want9 = {"atten": True, "tres": True, "tspan": True, "rload": True, "mask ref": True, "mask lower": True, "cm span": True, "cm stop": True,
                 "all fixed": (True, True)}
        check(r9 == want9 and not CJK.search(r9_msgs) and not CJK.search(tr(sv.CM_MESSAGES["span"]) + tr(sv.CM_MESSAGES["stop"])),
              f"英文介面（第九輪）：衰減（Hann）「Attenuation: … (select the Chebyshev or Kaiser window to edit it)」、時間解析度與時間跨度（關掉頻譜圖）、"
              f"參考負載（兩個檢視都關）、遮罩的參考位準（RMS）「Spectral Mask Reference Level: …」與下限（線性）「… (set the spectrum unit to something "
              f"other than Linear to edit it)」、通道量測的跨度（開始／停止模式）與停止頻率（跨度模式）的說明列都是英文全文"
              f"（{ {k_: v_ for k_, v_ in r9.items() if want9.get(k_) != v_} or 'all ok'}）")
    check(not left, f"次要視窗沒有中文（剩 {len(left)}：{[x[2][:30] for x in left[:8]]}）")
    help_win = next((t for t in tops if isinstance(t, sv.HelpWindow)), None)
    if help_win is not None:
        check(sv.find_readme("en") is not None and sv.find_readme("en").endswith("README.en.md"), "英文說明用 README.en.md")
    prefs = next((t for t in tops if isinstance(t, sv.PreferencesDialog)), None)
    if prefs is not None:
        prefs.vars["lang"].set(LANGUAGES["zh"])
        changed = prefs._apply()
        check(changed and app.v["lang"].get() == "zh", "偏好設定改語言 → view.lang 改了、回報需要重開")
        app.v["lang"].set("en")
    for t in tops:
        try:
            t.destroy()
        except Exception:
            pass


@step
def s5_settings_roundtrip():
    d = app.dump_settings()
    check(d["view"]["lang"] == "en", "設定檔記錄 lang=en")
    import json
    p = os.path.join(OUT, "a.json")
    json.dump(d, open(p, "w", encoding="utf-8"))
    check(sv.peek_language(["--lang", "zh"]) == "zh" and sv.peek_language(["--lang=en"]) == "en", "peek_language：命令列優先")
    os.environ["DSV_LANG"] = "zh"
    check(sv.peek_language([]) == "zh", "peek_language：環境變數")
    del os.environ["DSV_LANG"]
    sv.AUTOSAVE_PATH = p
    check(sv.peek_language([]) == "en", "peek_language：自動存檔裡的 view.lang")


@step
def s6_bus_display():
    """批次 D：數位顯示（格式／進位制／位元寬度）的右鍵選單、屬性區、狀態列是英文。"""
    added = None
    if not app.signals:
        added = app.add_text_signal(os.path.join(SAMPLES, "hex", "samples.txt"))
        app.refresh_list(); app.plot()
    s0 = app.signals[0]
    app.sig_tree.selection_set([f"s{s0.uid}"]); app._on_list_select()
    m = sv.tk.Menu(app, tearoff=0)
    app._add_bus_menu_items(m)
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1)]
    for i in (0, 1):
        sub = app.nametowidget(m.entrycget(i, "menu"))
        labels += [sub.entrycget(j, "label") for j in range(sub.index("end") + 1)]
    m.destroy()
    msgs = []
    old = (s0.disp, s0.radix, s0.bits)
    app.set_bus_format("digital"); msgs.append(app.status_var.get())
    app.set_bus_radix("bin"); msgs.append(app.status_var.get())
    app.p_bus_bits.set("99"); app.apply_bus_bits(); msgs.append(app.status_var.get())
    app.set_bus_bits(4); msgs.append(app.status_var.get())
    info = app.p_bus_info.get()
    props = [app.p_bus_disp.get(), app.p_bus_radix.get(), info]
    app.set_bus_format(old[0]); app.set_bus_radix(old[1]); app.set_bus_bits(old[2])
    if added is not None:
        app.remove_selected()
    bad = [x for x in labels + msgs + props if CJK.search(x)]
    check(not bad and "Hexadecimal" in labels and "Bit Width…" in labels and props[1] == "Binary",
          f"數位顯示：選單、狀態列、屬性區是英文（{labels[:3]}…；剩 {bad[:3]}）")


@step
def s7_axis_names():
    """2026-10-26 新功能（decisions_u26.md 第 3 項）：panel 的名稱與標題、整張圖的大標題——右鍵選單、對話框、狀態列、復原都是英文；
    使用者打的字（這裡故意用中文）不翻譯、照原樣畫；圖上扣掉使用者打的字之後沒有中文（P 編號、單位、「右軸」都是英文）。"""
    added = []
    if len(app.panel_order()) < 1:
        added.append(app.add_text_signal(os.path.join(SAMPLES, "hex", "samples.txt")))
        app.refresh_list(); app.plot()
    p = app.panel_order()[0]
    m = sv.tk.Menu(app, tearoff=0)
    app._add_panel_analysis_items(m, p)
    labels = [m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) != "separator"]
    sub = None
    for i in range(m.index("end") + 1):
        if m.type(i) == "cascade" and m.entrycget(i, "label") == tr("座標（P{p}）").format(p=p):
            sub = app.nametowidget(m.entrycget(i, "menu"))
    sub_labels = [sub.entrycget(j, "label") for j in range(sub.index("end") + 1) if sub.type(j) != "separator"] if sub else []
    check(sub is not None and sub_labels[-5:] == ["Title…", "Subtitle…", "X-Axis Name…", "Y-Axis Name…", "Right Axis Name…"]
          and "Figure Title…" in labels and not [x for x in labels + sub_labels if CJK.search(x)],
          f"右鍵選單：Axes (P{p}) 裡的 Title…／Subtitle…／X-Axis Name…／Y-Axis Name…／Right Axis Name…（大小寫一致）、外面的 Figure Title… 都是英文（{sub_labels[-5:]}）")
    asked, answers = [], ["中文標題", "副標 $V_{in}$", "時間", "電壓", "右邊", "整張圖"]
    orig = sv.ask_string

    def fake(parent, title, prompt, initial=""):
        asked.append((title, prompt, initial))
        return answers.pop(0) if answers else None
    sv.ask_string = fake
    msgs = []
    try:
        for key in ("title", "subtitle", "xname", "yname", "yname_right"):
            app.ask_panel_name(key, p); app.update()
            msgs.append(app.status_var.get())
        app.ask_figure_title(); app.update()
        msgs.append(app.status_var.get())
        app.set_panel_name("yname", "$x^$", p); app.update()
        msgs.append(app.status_var.get())
        app.undo_action(); app.update()
        msgs.append(app.status_var.get())
        app.redo_action(); app.update()
        msgs.append(app.status_var.get())
        app.undo_action(); app.update()
    finally:
        sv.ask_string = orig
    user = ["中文標題", "副標 $V_{in}$", "時間", "電壓", "右邊", "整張圖"]

    def strip_user(x):
        for u in user:
            x = x.replace(u, "")
        return x
    left_d = [x for t_, pr_, _i in asked for x in (t_, pr_) if CJK.search(x)]
    left_s = [x for x in msgs if CJK.search(strip_user(x))]
    check(len(asked) == 6 and not left_d and asked[0][0] == f"Title of P{p}" and "blank" in asked[0][1],
          f"對話框的標題與提示是英文（{[a[0] for a in asked]}；剩 {left_d[:2]}）")
    check(not left_s and msgs[0].startswith(f"P{p} Title: 中文標題") and "not valid math" in msgs[6] and msgs[7].startswith("Undone:"),
          f"狀態列（含不合法數學式的提醒、復原、重做）是英文，使用者打的字照原樣（{msgs[0][:40]}；{msgs[6][-50:]}；剩 {left_s[:2]}）")
    info = app.render_info
    arts = (info.get("title_artists") or {}).get(p) or {}
    ax = info["axes"][info["panels"].index(p)]
    check(arts.get("title") is not None and arts["title"].get_text() == "中文標題" and ax.get_ylabel().startswith(f"≡ P{p} 電壓")
          and ax.get_xlabel().startswith("時間 [") and info.get("figure_title_artist") is not None
          and info["figure_title_artist"].get_text() == "整張圖", "使用者打的字不翻譯（標題、y／x 軸名稱、大標題照原樣）")
    ft = fig_cjk(app.fig)
    check(not ft, f"英文介面：圖上扣掉使用者打的字之後沒有中文（{ft[:3]}）")
    for key in sv.PANEL_NAME_KEYS:
        app.set_panel_name(key, "", p)
    app.set_figure_title("")
    for s_ in added:
        if s_ is not None and s_ in app.signals:
            app.sig_tree.selection_set([f"s{s_.uid}"]); app._on_list_select(); app.remove_selected()
    app.update()


@step
def s8_mode_menus_clear():
    """2026-10-27 使用者第二、三次選單：平移／放大模式的右鍵選單（MATLAB 的模式選單＋最下面的「座標（P1）」與「整張圖的大標題…」）、
    清空連整張圖的大標題一起清的狀態列——英文介面都是英文（真的滑鼠右鍵事件走主圖全部的 callback）。"""
    from matplotlib.backend_bases import MouseEvent
    added = []
    if len(app.panel_order()) < 1:
        added.append(app.add_text_signal(os.path.join(SAMPLES, "hex", "samples.txt")))
        app.refresh_list(); app.plot()
    app.update()
    p = app.panel_order()[0]
    info = app.render_info
    ax = info["axes"][info["panels"].index(p)]
    app.canvas.draw()
    spot = None
    for fy in (0.985, 0.95, 0.5, 0.03):                    # 座標區裡真的空白的一點（不在線、圖例上）
        for fx in (0.37, 0.12, 0.62, 0.25):
            x, y = ax.bbox.x0 + fx * ax.bbox.width, ax.bbox.y0 + fy * ax.bbox.height
            if spot is None and app.ia.hit_test(MouseEvent("button_press_event", app.canvas, x, y, button=3)).kind == "empty":
                spot = (x, y)
    spot = spot or (ax.bbox.x0 + 0.37 * ax.bbox.width, ax.bbox.y0 + 0.985 * ax.bbox.height)
    got = []
    orig_popup = sv.tk.Menu.tk_popup

    def cap(self, x_, y_, entry=None):
        got.append([self.entrycget(i, "label") for i in range(self.index("end") + 1) if self.type(i) != "separator"])
    tb = app.plot_toolbar
    mode0 = {"pan/zoom": "pan", "zoom rect": "zoom"}.get(str(getattr(tb, "mode", "") or ""), "")
    sv.tk.Menu.tk_popup = cap
    try:
        for mode in ("pan", "zoom"):
            tb.set_mode(mode); app.update()
            MouseEvent("button_press_event", app.canvas, *spot, button=3)._process()
            MouseEvent("button_release_event", app.canvas, *spot, button=3)._process()
            app.update()
    finally:
        sv.tk.Menu.tk_popup = orig_popup
        tb.set_mode(mode0); app.update()
    tail = [tr("座標（P{p}）").format(p=p), tr("整張圖的大標題…")]
    pan_ref = [tr(x_) for x_ in ("還原視圖", "不限方向平移", "只平移 x（水平）", "只平移 y（垂直）")] + tail
    zoom_ref = [tr(x_) for x_ in ("縮小        Shift＋點", "還原視圖", "不限方向縮放", "只縮 x（水平）", "只縮 y（垂直）")] + tail
    check(len(got) == 2 and got[0] == pan_ref and got[1] == zoom_ref and tail[0] == f"Axes (P{p})"
          and not [x_ for g_ in got for x_ in g_ if CJK.search(x_)],
          f"平移／放大模式的右鍵選單：MATLAB 的模式選單＋最下面的 Axes (P{p})、Figure Title… 都是英文（{got}）")
    app.set_figure_title("Figure X"); app.update()
    n = len(app.signals)
    conf0 = app.v["confirm_clear"].get()
    app.v["confirm_clear"].set(False)
    try:
        app.clear_all(); app.update()
        st = app.status_var.get()
        app.undo_action(); app.update()
    finally:
        app.v["confirm_clear"].set(conf0)
    check(st == f"Cleared {n} signals and the figure title (Ctrl+Z undoes)" and len(app.signals) == n and app.figure_title == "Figure X",
          f"清空連整張圖的大標題一起清：狀態列是英文（{st}），⌘Z 一起回來")
    app.set_figure_title(""); app.update()
    for s_ in added:
        if s_ is not None and s_ in app.signals:
            app.sig_tree.selection_set([f"s{s_.uid}"]); app._on_list_select(); app.remove_selected()
    app.update()


@step
def s9_eye_diagram():
    """第四批 T4：眼圖視窗的英文介面。座標區標題與標籤是 MATLAB eyediagram 自己的英文、欄位錯誤與資料錯誤是 MATLAB 的訊息
    （預期值取自 tests/matlab_ref/eye_diagram/eye_ref.json，不是受測的程式）；選單、狀態列、說明列沒有中文。"""
    import json
    R = json.load(open(os.path.join(HERE, "tests", "matlab_ref", "eye_diagram", "eye_ref.json"), encoding="utf-8"))
    ERR = {e["name"]: e for e in R["errors"]}
    ax_c = next(c for c in R["cases"] if c["name"] == "complex_defaults")["axes"]
    ax_r = next(c for c in R["cases"] if c["name"] == "real_defaults")["axes"]
    if not app.signals:
        app.add_all_visible()
        app.plot()
    iqs = [s_ for s_ in app.signals if s_.column in ("adc i", "adc q")][:2] or app.signals[-2:]
    texts = []
    app.sig_tree.selection_set([f"s{s_.uid}" for s_ in iqs]); app._on_list_select(); app.update()
    w = app.open_eye(); app.update()
    texts += [app.status_var.get(), w.title() if w else ""]
    heads = [(ax.get_title(), ax.get_xlabel(), ax.get_ylabel()) for ax in w.fig.axes] if w else []
    check(w is not None and heads == [(a["title"].strip(), a["xlabel"], a["ylabel"]) for a in ax_c] and w.title().startswith("Eye Diagram — ")
          and app.status_var.get().startswith("Eye diagram window opened: "),
          f"英文介面：I/Q 兩張的標題與 x／y 標籤＝MATLAB eyediagram 的 Eye Diagram for In-Phase／Quadrature Signal、Time、Amplitude（{heads}）")
    top_labels = [str(x.cget("text")) for x in w._fields["n"].master.winfo_children() if isinstance(x, sv.ttk.Label)] if w else []
    texts += top_labels
    check(top_labels == ["Samples per trace", "Period", "Offset"],
          f"英文介面：眼圖欄位列的標籤（從元件讀）正好是 Samples per trace／Period／Offset（{top_labels}）")
    bad_err = []
    if w is not None:
        w.v_xrange.set(False)
        for case, key, txt in (("n_equal_1", "n", "1"), ("period_negative", "period", "-1"), ("offset_frac", "offset", "1.5")):
            fv = {"n": w.v_n, "period": w.v_period, "offset": w.v_offset}[key]
            before = fv.get()
            fv.set(txt); w.compute(); app.update()
            want = ERR[case]["msg"]
            lab = {"n": "Samples per trace", "period": "Period", "offset": "Offset"}[key]
            got = (w.v_status.get(), w._fields[key]._pk_tip, w.v_msg.get())
            texts += list(got)
            if not (got[0] == f"{lab}: {want}" and got[1] == want and want in got[2]):
                bad_err.append((case, got[0][:60]))
            fv.set(before); w.compute(); app.update()
        labels = []
        from types import SimpleNamespace as NS
        sv.tk.Menu.tk_popup, old_popup = (lambda self_, x, y, entry=None: labels.extend(
            self_.entrycget(i, "label") for i in range(self_.index("end") + 1) if self_.type(i) != "separator")), sv.tk.Menu.tk_popup
        try:
            ln = next(iter(w.lines.values()))
            w.context_menu(pk.interact.Hit("line", ln.axes, ln, 1, 0), NS(guiEvent=None))
        finally:
            sv.tk.Menu.tk_popup = old_popup
        texts += labels
        w.set_line_style("ls", "None"); texts.append(w.v_status.get())
        w.reset_line_style(); texts.append(w.v_status.get())
        check(not bad_err and labels[:6] == ["Color", "Line Width", "Line Style", "Marker", "Marker Size", "Reset Style"],
              f"英文介面：欄位錯誤的狀態列「欄位: 訊息」、提示、說明列是 MATLAB 的原文（N must be an integer greater than 1. 等）；樣式選單是英文"
              f"（{bad_err or 'fields ok'}、{labels[:6]}）")
        x_hi = max(len(s_.get_data()) / s_.sps for s_ in app.signals) + 5000.0
        app.plot(keep=True, xlim=(x_hi, x_hi + 10.0)); app.update()
        w.v_xrange.set(True); w.compute(); app.update()
        texts += [w.v_msg.get(), w.v_status.get()] + [t.get_text() for t in w.fig.texts]
        check(ERR["empty_x"]["msg"] in w.v_msg.get() and "Analysis range" in w.v_msg.get(),
              f"英文介面：範圍裡沒有樣本＝MATLAB 的「{ERR['empty_x']['msg']}」和怎麼調整範圍（{w.v_msg.get()[:70]}）")
        app.show_all_x(); app.update()
        w.destroy(); app.update()
    one = iqs[:1]
    app.sig_tree.selection_set([f"s{s_.uid}" for s_ in one]); app._on_list_select(); app.update()
    w1 = app.open_eye(); app.update()
    head1 = [(ax.get_title(), ax.get_xlabel(), ax.get_ylabel()) for ax in w1.fig.axes] if w1 else []
    texts += [app.status_var.get(), w1.title() if w1 else "", w1.v_status.get() if w1 else ""]
    check(head1 == [(ax_r["title"].strip(), ax_r["xlabel"], ax_r["ylabel"])], f"英文介面：一條訊號＝一張「{ax_r['title'].strip()}」（MATLAB 的標題）（{head1}）")
    if w1 is not None:
        w1.destroy(); app.update()
    three = app.signals[:3]
    app.sig_tree.selection_set([f"s{s_.uid}" for s_ in three]); app._on_list_select(); app.update()
    res3 = app.open_eye(); app.update()
    texts.append(app.status_var.get())
    check(len(three) < 3 or (res3 is None and ERR["three_columns"]["msg"] in app.status_var.get()),
          f"英文介面：選 3 條＝MATLAB 的「{ERR['three_columns']['msg']}」（{app.status_var.get()[:80]}）")
    app.sig_tree.selection_set([]); app._on_list_select()
    # 狀態列那兩句（使用者 10-28 決定：跟著選的、沒有跟著選的都列出 Eye Diagram、Error Rate）走真的路徑，不只查翻譯表：
    # 平移模式真的點 panel 空白（跟著選那句）→ 清單改選（換回沒有跟著選的那句）
    from matplotlib.backend_bases import MouseEvent
    ps = app.panel_order()
    p_a = next((s_.panel for s_ in iqs if s_.panel in ps), ps[0])
    p_b = next((p_ for p_ in ps if p_ != p_a), p_a)
    info = app.render_info
    ax_a = info["axes"][info["panels"].index(p_a)]
    app.canvas.draw()
    spot = None
    for fy in (0.985, 0.95, 0.5, 0.03):                    # 座標區裡真的空白的一點（不在線、圖例上）
        for fx in (0.37, 0.12, 0.62, 0.25):
            x, y = ax_a.bbox.x0 + fx * ax_a.bbox.width, ax_a.bbox.y0 + fy * ax_a.bbox.height
            if spot is None and app.ia.hit_test(MouseEvent("button_press_event", app.canvas, x, y, button=1)).kind == "empty":
                spot = (x, y)
    tb = app.plot_toolbar
    mode0 = {"pan/zoom": "pan", "zoom rect": "zoom"}.get(str(getattr(tb, "mode", "") or ""), "")
    clip0, app._sig_clip = app._sig_clip, []               # 剪貼簿有東西時這句換成 ⌘V 的提示：先拿開
    st_follow = st_plain = ""
    try:
        app._set_current_panel(p_b, announce=False); tb.set_mode("pan"); app.update()
        if spot is not None:
            MouseEvent("button_press_event", app.canvas, *spot, button=1)._process()
            MouseEvent("button_release_event", app.canvas, *spot, button=1)._process()
            app.update()
            st_follow = app.status_var.get()
            app.sig_tree.selection_set([]); app._on_list_select(); app.update()
            st_plain = app.status_var.get()
    finally:
        app._sig_clip = clip0
        tb.set_mode(mode0); app.update()
    n_a = len([s_ for s_ in app.signals if s_.panel == p_a and s_.visible])
    texts += [st_follow, st_plain]
    check(spot is not None
          and st_follow == f"Current panel: P{p_a}; its {n_a} signal(s) are selected in the list (AM/PM/FM, Constellation, GFSK, Eye Diagram, Error Rate, "
                           "the panner and the Axes settings apply to it)"
          and st_plain == f"Current panel: P{p_a} (AM/PM/FM, Constellation, GFSK, Eye Diagram, Error Rate and the Axes settings apply to it)",
          f"英文介面（真的點 P{p_a}、再改清單選取）：跟著選那句與沒有跟著選那句都列出 Eye Diagram、Error Rate（使用者 10-28 決定）"
          f"（{st_follow[:60]}／{st_plain[:60]}）")
    bad = [t for t in texts if CJK.search(str(t))]
    check(not bad, f"英文介面：眼圖的標題、狀態列、說明列、提示、選單都沒有中文（{bad[:3]}）")


@step
def s10_error_rate():
    """第四批 T5：錯誤率比對視窗的英文介面。欄位錯誤、自訂樣本位置超出範圍、biterr 的錯誤、symerr 的警告是 MATLAB 的英文原文
    （預期值取自 tests/matlab_ref/error_rate 的參考資料，不是受測的程式）；標題、元件、提示、下拉、狀態列、說明列沒有中文。"""
    import json
    import numpy as np
    C = {}
    for fname in ("error_rate_ref.json", "er_ref.json"):
        R = json.load(open(os.path.join(HERE, "tests", "matlab_ref", "error_rate", fname), encoding="utf-8"))
        C.update({c["name"]: c for c in R["cases"]})

    def ml_err(name):
        c = C[name]
        return c.get("err_msg") if "err_msg" in c else (c.get("error") or {}).get("message", "")

    def ml_warn(name):
        c = C[name]
        return c.get("warn_msg") if "warn_msg" in c else (c.get("warning") or {}).get("message", "")
    d = os.path.join(OUT, "er_i18n")
    os.makedirs(d, exist_ok=True)

    def mk(name, vals, sps=4):
        p = os.path.join(d, name + ".txt")
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(repr(float(v)) for v in np.repeat(np.asarray(vals, dtype=float), sps)) + "\n")
        s_ = app.add_text_signal(p)
        s_.sps = float(sps)
        return s_
    added = [mk("er_tx", [1, 0, 1, 1, 0, 0, 1, 0, 1, 1]), mk("er_rx", [1, 1, 1, 1, 0, 0, 1, 0, 1, 0]),
             mk("er_neg", [1, 0, -1, 1, 0, 0, 1, 0, 1, 1]), mk("er_nan", [1, 0, 1, float("nan"), 0, 0, 1, 0, 1, 1])]
    tx, rx, neg, nanv = added

    def row(s_):
        return next(i for i, x in enumerate(app.signals) if x is s_)
    app.refresh_list(); app.plot(); app.update()
    texts = []
    app.sig_tree.selection_set([f"s{tx.uid}", f"s{rx.uid}"]); app._on_list_select(); app.update()
    w = app.open_errrate(); app.update()
    texts += [app.status_var.get(), w.title() if w else ""]
    ok_open = w is not None and w.title().startswith("Error Rate — TX = ") and app.status_var.get().startswith("Error rate opened: ")
    analog_msg = w.v_msg.get() if w else ""
    vals = list(w.cb_tx.cget("values")) if w else []
    texts += [analog_msg] + vals
    check(ok_open and "analog format" in analog_msg and "Make Digital" in analog_msg and any(v.endswith(" (analog)") for v in vals)
          and str(w.btn_digital.cget("text")) == "Make Digital",
          f"英文介面：標題「Error Rate — TX = …」、類比格式的提示與「Make Digital」、下拉標 (analog)（{analog_msg[:70]}）")
    bad = []
    if w is not None:
        w.btn_digital.invoke(); app.update()
        texts += [w.v_status.get(), w.v_info.get()] + [v.get() for v in w.v_res.values()]
        res_ok = w.result.get("n") == 10 and w.v_status.get().startswith("Compared 10 symbols: 2 symbol errors")
        res_labels = [str(x.cget("text")) for x in w._res_frame.winfo_children() if isinstance(x, sv.ttk.Label) and not str(x.cget("textvariable"))]
        row_labels = [str(x.cget("text")) for x in w._fields["rd"].master.winfo_children() if isinstance(x, sv.ttk.Label)]
        texts += res_labels + row_labels + [str(w._res_frame.cget("text"))]
        check(res_labels == ["Number of samples compared", "Number of symbol errors", "Symbol error rate", "Number of bit errors", "Bit error rate",
                             "Bits per symbol k", "Number of bits compared"]
              and row_labels == ["Receive delay", "Computation delay", "Samples to consider", "Selected samples from frame"]
              and str(w._res_frame.cget("text")) == "Results",
              f"英文介面：錯誤率結果列與欄位列的標籤（從元件讀）正好是這組英文（{res_labels[:3]}…、{row_labels}）")
        # 欄位錯誤＝MATLAB 的原文（狀態列「欄位名稱: 訊息」、提示＝訊息）
        for key, txt, case, lab in (("rd", "-1", "rd_negative_ERR", "Receive delay"), ("rd", "1.5", "rd_frac_ERR", "Receive delay"),
                                    ("cd", "-2", "cd_negative_ERR", "Computation delay"), ("cd", "[1 2]", "cd_vector_ERR", "Computation delay")):
            var = w.v_rd if key == "rd" else w.v_cd
            var.set(txt); w.compute(); app.update()
            want = ml_err(case)
            got = (w.v_status.get(), getattr(w._fields[key], "_pk_tip", ""), w.v_msg.get())
            texts += list(got)
            if not (got[0] == f"{lab}: {want}" and got[1] == want and want in got[2]):
                bad.append((case, got[0][:70]))
            var.set("0"); w.compute(); app.update()
        w.v_samples.set("Custom"); w.v_custom.set(""); w.compute(); app.update()
        got = w.v_status.get()
        texts += [got, w.v_msg.get(), str(w.cb_samples.cget("values"))]
        if got != "Selected samples from frame: " + ml_err("custom_empty_ERR"):
            bad.append(("custom_empty_ERR", got[:70]))
        w.v_custom.set("[1 11]"); w.compute(); app.update()
        got = w.v_status.get()
        texts += [got, w.v_msg.get()]
        if got != "Selected samples from frame: " + ml_err("custom_gt_frame_ERR") or "has only 10 symbols" not in w.v_msg.get():
            bad.append(("custom_gt_frame_ERR", got[:70]))
        w.v_samples.set("Entire frame"); w.v_custom.set(""); w.compute(); app.update()
        check(res_ok and not bad, f"英文介面：結果與狀態列「Compared 10 symbols: …」；接收延遲／計算延遲／自訂樣本位置的錯誤＝MATLAB comm.ErrorRate 的原文"
                                  f"（Expected ReceiveDelay to be nonnegative. 等；{bad or 'fields ok'}）")
        # biterr 的錯誤（TX 有負數＝X）、symerr 的警告（RX 有 NaN）＝MATLAB 的原文
        app.set_bus_format("digital", [neg, nanv]); app.update()
        w.cb_tx.current(row(neg)); w.cb_tx.event_generate("<<ComboboxSelected>>"); app.update()
        m_neg = w.v_msg.get()
        w.cb_tx.current(row(tx)); w.cb_tx.event_generate("<<ComboboxSelected>>")
        w.cb_rx.current(row(nanv)); w.cb_rx.event_generate("<<ComboboxSelected>>"); app.update()
        m_nan = w.v_msg.get()
        texts += [m_neg, m_nan, w.v_status.get()]
        check(ml_err("negative_ERR") in m_neg and "(biterr, X = TX, Y = RX)" in m_neg and ml_warn("nan_warn") in m_nan
              and "Symbol errors (symerr)" in m_nan,
              f"英文介面：biterr 的錯誤「{ml_err('negative_ERR')}」、symerr 的警告「{ml_warn('nan_warn')}」是 MATLAB 的原文（{m_neg[:60]}…）")
        w.cb_rx.current(row(rx)); w.cb_rx.event_generate("<<ComboboxSelected>>"); app.update()
        app.show_all_x(); app.update()
        w.goto(1); app.update()
        texts += [w.v_status.get(), app.status_var.get()]
        nav_ok = w.v_status.get().startswith("Error 1/")
        left = cjk_in(w, "errrate")
        texts += [str(b_.cget("text")) for b_ in (w.btn_prev, w.btn_next)]
        cjk_t = [t for t in texts if CJK.search(str(t))]
        check(nav_ok and not left and not cjk_t, f"英文介面：錯誤率比對的元件、提示、下拉、狀態列、說明列、上一個／下一個錯誤都沒有中文"
                                                 f"（{w.v_status.get()[:30]}；元件 {left[:3]}；文字 {cjk_t[:3]}）")
        # 0.9.13 D14：RX 從清單移除（線上右鍵「刪除這條訊號」走的 remove_signal_by_uid）→ 下拉「(no longer in the list)」、說明列與狀態列是英文；
        # 對已經不在清單裡的訊號再按一次 → 主視窗狀態列「This signal is no longer in the list」
        app.remove_signal_by_uid(rx.uid); app.update()
        gone_txt = (w.v_rx.get(), w.v_msg.get(), w.v_status.get())
        app.undo_action(); app.update()
        app.remove_signal_by_uid(10 ** 9); app.update()
        st_gone = app.status_var.get()
        texts += list(gone_txt) + [st_gone]
        check(gone_txt[0] == "(no longer in the list)" and gone_txt[1] == gone_txt[2] == "RX is no longer in the list (removed) or not chosen yet: pick another one in the drop-down above"
              and st_gone == "This signal is no longer in the list" and w.result.get("n") == 10 and not CJK.search(" ".join(gone_txt) + st_gone),
              f"英文介面：RX 被移除 → 下拉「(no longer in the list)」、說明列／狀態列「RX is no longer in the list …」；⌘Z 回來又算 10 個；"
              f"對不在清單裡的訊號按「刪除這條訊號」→「This signal is no longer in the list」（0.9.13 D14）（{gone_txt[1][:50]}／{st_gone}）")
        w.destroy(); app.update()
    app.signals[:] = [x for x in app.signals if all(x is not a for a in added)]
    app.sig_tree.selection_set([]); app.refresh_list(); app.plot(); app.update()


@step
def s11_drop_status_join():
    """第三輪行為驗證：英文介面拖放的狀態列 panel 清單用 tr("、")（", "）——0.9.13 一樣是「Dropped 2 signals into P2、P3」（不是回歸，P3 小改）。"""
    d = os.path.join(OUT, "drop_join")
    os.makedirs(d, exist_ok=True)
    paths = []
    for nm in ("ja.csv", "jb.csv"):
        p = os.path.join(d, nm)
        with open(p, "w", encoding="utf-8") as f:
            f.write("v\n" + "\n".join(str(k % 5) for k in range(64)) + "\n")
        paths.append(p)
    before = list(app.signals)
    app.add_dropped_paths(paths); app.update()
    st = app.status_var.get()
    new = [s for s in app.signals if all(s is not a for a in before)]
    check(len(new) == 2 and re.search(r"Dropped 2 signals into P\d+, P\d+", st) and "、" not in st and not CJK.search(st),
          f"英文介面：拖放兩個檔到兩張新 panel → 狀態列用英文逗號接 panel（{st[:80]}）（2f3a248：「P2、P3」）")
    app.signals[:] = [x for x in app.signals if all(x is not a for a in new)]
    app.sig_tree.selection_set([]); app.refresh_list(); app.plot(); app.update()


@step
def s12_theme_names():
    """1.0.0 外觀主題：英文介面的主題下拉（檢視 ▸ 外觀、偏好設定 ▸ 外觀）顯示英文名稱 Dark／Light／Sony (black)／Sony (deep blue)／
    Apple (light)／Apple (dark)／Apple (dark, graphite)／Apple (dark, black)；切到 Sony (deep blue) 的狀態列是英文；切回 Dark。"""
    import plotkit.theme as _T
    want = ("Dark", "Light", "Sony (black)", "Sony (deep blue)", "Apple (light)", "Apple (dark)", "Apple (dark, graphite)", "Apple (dark, black)")

    def walk(w):
        yield w
        for c in w.winfo_children():
            yield from walk(c)
    cbs = [w for w in walk(app.strip.tabs["view"]) if w.winfo_class() == "TCombobox" and str(w.cget("textvariable")) == str(app.v_theme_label)]
    cb = cbs[0] if cbs else None
    check(cb is not None and tuple(cb.cget("values")) == want and _T.theme_labels() == want and app.v_theme_label.get() == "Dark",
          f"英文介面：檢視 ▸ 外觀 ▸ 主題 下拉＝{want}（{cb.cget('values') if cb else None}）")
    tip_ = str(getattr(cb, "_pk_tip", "")) if cb is not None else ""          # 1.0.0 第 3 輪（決定檔 11-02 04:2x／04:3x，B3R3-1）
    check(tip_ == "Interface theme: Dark / Light (MATLAB), Sony, Apple; the plot style follows the theme (MATLAB style for Dark / Light)"
          and "MATLAB plot style" not in tip_,
          f"英文介面：主題下拉的工具提示說 the plot style follows the theme（深色／淺色是 MATLAB 風格），不說 the MATLAB plot style（{tip_}）")
    theme0, style0 = app.v["theme"].get(), app.v["style"].get()
    try:
        cb.set("Sony (deep blue)"); cb.event_generate("<<ComboboxSelected>>"); app.update()
        st = app.status_var.get()
        check(_T.current().name == "sony_blue" and st.startswith('Switched to the "Sony (deep blue)" theme') and not CJK.search(st)
              and (style0 == "default" or st.endswith(" (the plot style follows)")) and "MATLAB" not in st      # 1.0.0 第 2 輪 B2R2-1
              and not cjk_in(app.strip.tabs["view"], "view"),
              f"英文介面：切到 Sony (deep blue)：狀態列英文「{st[:60]}」、檢視分頁沒有中文")
        d = sv.PreferencesDialog(app); d.grab_release(); app.update()
        try:
            pcb = [w for w in walk(d) if w.winfo_class() == "TCombobox" and str(w.cget("textvariable")) == str(d.vars["theme"])]
            left = cjk_in(d, "prefs")
            check(pcb and tuple(pcb[0].cget("values")) == want and d.vars["theme"].get() == "Sony (deep blue)" and not left,
                  f"英文介面：偏好設定 ▸ 外觀 ▸ 主題 下拉英文、目前＝Sony (deep blue)、對話框沒有中文（{left[:3]}）")
            d.vars["theme"].set("Apple (light)"); d._apply(); app.update()
            check(_T.current().name == "apple_light" and app.v_theme_label.get() == "Apple (light)", "英文介面：偏好設定套用 Apple (light)")
        finally:
            d.destroy(); app.update()
    finally:
        app.v["theme"].set(theme0); app.update()
        if app.v["style"].get() != style0:
            app.v["style"].set(style0); app.plot(keep=True); app.update()
    check(_T.current().name == theme0 and app.v_theme_label.get() == "Dark", "英文介面：切回 Dark")


def run(i=0):
    if i >= len(steps):
        import tests_common as _tc
        _qp = _tc.quiet_problems()               # 安靜模式（2026-10-26 使用者回報點不動自己的 DSV；第二輪：沒預期的擋下、啟用、剪貼簿）
        check(not _qp, f"安靜模式：跑完全部步驟沒有沒換掉的原生對話框、沒預期的選單彈出，還是 Prohibited、剪貼簿在行程裡，"
                       f"看得見的視窗都點不到、alpha 0、不在選單層，擋板都在（{_qp[:3]}）")
        _DONE[0] = True
        app.destroy()
        return
    _PROG.begin(i)
    try:
        steps[i]()
    except Exception:
        traceback.print_exc()
        check(False, f"步驟 {steps[i].__name__} 例外")
    _PROG.end(i)
    app.after(300, lambda: run(i + 1))


import tests_common as _tcp                     # noqa: E402
_DONE = [False]
_PROG = _tcp.StepProgress([fn.__name__ for fn in steps], results, env_name=None)
_tcp.install_term_report(_PROG)                 # timeout 的 SIGTERM：寫出停在哪一步再結束（不經過 Tk 的訊號處理，不死鎖；0.9.14 R3C-6）
app.after(800, run)
app.mainloop()
# 每一步都跑到了、整套跑到最後（某一步把主視窗關掉時以前照樣「全部通過」；第二輪測試強度驗證 3）
_ran = {n_ for n_, _t, _k in _PROG.times}
_miss = [fn.__name__ for fn in steps if fn.__name__ not in _ran]
check(_DONE[0] and not _miss, f"這次要跑的 {len(steps)} 步每一步都跑到了、整套跑到最後（沒有哪一步把主視窗關掉）：沒跑到 {len(_miss)} 步 {_miss[:6]}；跑到最後 {_DONE[0]}")
bad = [m for ok, m in results if not ok]
print(_PROG.summary())
print(f"\nI18N GUI TEST: {len(results) - len(bad)}/{len(results)} 通過")
if OWN_OUT and not bad:
    shutil.rmtree(OUT, ignore_errors=True)
elif OWN_OUT:
    print(f"（輸出留在 {OUT}）")
sys.exit(1 if bad else 0)
