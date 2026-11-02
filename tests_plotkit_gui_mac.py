# -*- coding: utf-8 -*-
"""plotkit GUI 自動測試（真的 Tk 視窗，用 after() 逐步操作）。

macOS 請用有 Tk 8.6 的 Python：HOME=/tmp/pk_home /opt/anaconda3/bin/python3 tests_plotkit_gui_mac.py
設 PLOTKIT_TEST_CLIPBOARD=1 才會真的動系統剪貼簿（複製圖片走 osascript）；Tk 的文字剪貼簿在安靜模式下一律留在行程裡
（tests_common），複製資料提示的檢查不設也照跑。
"""
import os
import sys
import time
import tempfile
import traceback
from types import SimpleNamespace

# 卡住時印出所在位置並結束：看最下面的 install_stall_watchdog（0.9.14 R3C-6：以前這裡是整個行程一次的
# faulthandler.dump_traceback_later(45, exit=True)，負載高時整套正常跑也超過 45 秒，它印 traceback 時卡住、行程不結束）

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plotkit as pk  # noqa: E402
from matplotlib.backend_bases import KeyEvent, MouseButton, MouseEvent  # noqa: E402

for _s in (sys.stdout, sys.stderr):           # Windows 導到檔案時是 cp950：不能編碼的字用跳脫寫法，不要中斷
    if _s is not None and hasattr(_s, "reconfigure"):
        try:
            _s.reconfigure(errors="backslashreplace")
        except Exception:
            pass
OUT = tempfile.mkdtemp(prefix="pk_gui_")
_TMP = os.path.join(OUT, "tmp")                 # 暫存資料夾也用自己的：複製圖的暫存檔不留在系統共用的暫存資料夾（第 2 輪修正；同 tests_gui_mac.py）
os.makedirs(_TMP, exist_ok=True)
os.environ["TMPDIR"] = os.environ["TEMP"] = os.environ["TMP"] = _TMP
tempfile.tempdir = _TMP
results = []


def check(cond, msg):
    results.append((bool(cond), msg))
    print(("ok   " if cond else "FAIL ") + msg)


class _MB:
    def __getattr__(self, name):
        def f(*a, **k):
            print(f"[messagebox.{name}] {a[:2]}")
            return True if name.startswith("ask") else None
        return f


pk.dialogs.messagebox = _MB()
pk.dialogs.colorchooser = SimpleNamespace(askcolor=lambda **k: ((255, 0, 0), "#ff0000"))
pk.dialogs.simpledialog = SimpleNamespace(askfloat=lambda *a, **k: 3.0, askstring=lambda *a, **k: "renamed")
menus = []
menu_objs = []      # 最後彈出的 tk.Menu 物件（看子選單內容、實際 invoke 用）
_orig_popup = pk.dialogs.tk.Menu.tk_popup


def _fake_popup(self, x, y, entry=None):
    menu_objs[:] = [self]
    labels = []
    try:
        for i in range(self.index("end") + 1):
            if self.type(i) in ("command", "cascade", "checkbutton"):
                labels.append(self.entrycget(i, "label"))
    except Exception:
        pass
    menus.append(labels)


pk.dialogs.tk.Menu.tk_popup = _fake_popup
pk.menus.POPUP_MENU_RELEASE_MS = 10000  # 0.9.13 W1：假 tk_popup 只記錄、彈完馬上讀內容與 invoke；10 秒夠用，又不會像 None 那樣在 Windows 把選單代號用完（s99 驗證銷毀）

from tests_common import install_quiet, tk_key, has_desktop, clipboard_isolated   # 安靜模式：測試視窗透明、不搶前景（DSV_TEST_SHOW=1 才顯示）
install_quiet()
root = pk.ensure_root()
t = np.linspace(0, 1e-3, 2001)
w = pk.figure(title="test 1", style="matlab")
sI = w.plot(t * 1e6, np.sin(2 * np.pi * 5e3 * t), label="I")
sQ = w.plot(t * 1e6, np.cos(2 * np.pi * 5e3 * t), label="Q", ls="--")
sC = w.step(np.arange(0, 1000, 50.0), (np.arange(20) % 2).astype(float), label="clk", yaxis="right", color="#3baa32")
steps = []


def step(fn):
    steps.append(fn)
    return fn


def press_release(pc, x, y, button=1, modifiers=None, dbl=False):
    ev = MouseEvent("button_press_event", pc.canvas, x, y, button=button, dblclick=dbl, modifiers=modifiers)
    pc.ia.on_press(ev)
    if not dbl and button == 1:
        pc.ia.on_release(MouseEvent("button_release_event", pc.canvas, x, y, button=button, modifiers=modifiers))
    return ev


def tk_click(canvas, px, py, shift=False):
    """用 Tk 事件點一下（走 FigureCanvasTk → matplotlib → Interactor 的真實路徑）；px, py 是 matplotlib 像素座標（原點左下）。"""
    wdg = canvas.get_tk_widget()
    h = canvas.get_width_height(physical=True)[1]
    x, y = int(round(px)), int(round(h - py))
    st = 0x1 if shift else 0
    t = int(time.monotonic() * 1000) & 0x7fffffff          # 給事件真實的時間戳：不然 Tk 把連續兩次合成事件都當成雙擊
    wdg.event_generate("<ButtonPress-1>", x=x, y=y, state=st, when="now", time=t)
    wdg.event_generate("<ButtonRelease-1>", x=x, y=y, state=st | 0x100, when="now", time=t)


@step
def s1_basic():
    pc = w.pc
    check(len(w.series()) == 3 and w.series()[0].uid == 1 and pk.windows() == [w] and pk.active_window() is w,
          "figure/plot/step：3 條、uid 從 1、視窗登錄")
    check(pc.info.ax_right is not None and len(pc.fig.axes) == 2, "右軸 twin 建立")
    check(pc.info.lines[sI.uid].get_color() == "#1171be" and pc.info.lines[sI.uid].get_linewidth() == 0.5, "matlab 風格色與線寬")
    rows = pc.list_panel.tree.get_children()
    check(len(rows) == 3 and pc.list_panel.tree.item(rows[2], "values")[2] == "右", "清單 3 列、軸欄")
    w.xlabel("t [us]")
    w.ylabel("amp")
    w.ylabel("level", side="right")
    check(pc.info.ax_left.get_xlabel() == "t [us]" and pc.info.ax_right.get_ylabel() == "level", "x/y 標籤（含右軸）")
    check(pc.undo_stack.can_undo and "y 標籤" in pc.undo_stack.peek_desc(), "每個改動都進 undo")


@step
def s1b_matlab_click():
    """跟 MATLAB R2025a 一樣：資料提示預設開著，點線＝釘提示；Shift＋點＝選取；框選放大模式開著時暫停、關掉後恢復。"""
    pc = w.pc
    check(pc.v_tips.get() and pc.ia.tips_enabled, "預設開著資料提示（點線就釘，跟 MATLAB 一樣）")
    if not has_desktop(w):
        check(True, "（無桌面工作階段：Tk 事件的點擊測試略過）")
        return
    pc.canvas.draw()
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    px, py = ax.transData.transform((xd[400], yd[400]))
    n0 = len(pc.state.tips)
    tk_click(pc.canvas, px, py)
    check(len(pc.state.tips) == n0 + 1 and pc.state.tips[-1].uid == sI.uid and pc.selected == set(),
          f"Tk 點線 → 釘資料提示、不選取（tips {n0}→{len(pc.state.tips)}、selected={pc.selected}）")
    qx, qy = ax.transData.transform((xd[1400], yd[1400]))   # 換一個點：同一點連點兩下 Tk 會當成雙擊
    tk_click(pc.canvas, qx, qy, shift=True)
    check(pc.selected == {sI.uid} and len(pc.state.tips) == n0 + 1, f"Tk Shift＋點線 → 選取、不多釘（selected={pc.selected}）")
    n_series = len(pc.state.series)
    tk_click(pc.canvas, px, py)                      # 同一點再點：選取既有的提示 → 線的選取要取消（選取互斥）
    check(pc.selected == set() and pc.ia.selected_tip is not None and len(pc.state.tips) == n0 + 1,
          f"點提示 → 線的選取取消、提示被選取（selected={pc.selected}, tip={pc.ia.selected_tip}）")
    wdg = pc.canvas.get_tk_widget()
    tk_key(wdg, "Delete"); w.update()
    check(len(pc.state.tips) == n0 and len(pc.state.series) == n_series, f"Delete → 只刪提示（tips {len(pc.state.tips)}、series {len(pc.state.series)}）")
    tk_key(wdg, "Delete"); w.update()
    check(len(pc.state.series) == n_series, f"再按 Delete → 沒有選取的東西，線不會被刪（series {len(pc.state.series)}）")
    pc.plot_toolbar._zoom()
    check(not pc.v_tips.get() and not pc.ia.tips_enabled, "開框選放大 → 資料提示暫停")
    pc.plot_toolbar._zoom()
    check(pc.v_tips.get() and pc.ia.tips_enabled, "關掉框選放大 → 資料提示自動恢復")
    pc.ia.clear_tips()
    pc.select(set())


@step
def s2_list_and_pick():
    pc = w.pc
    tree = pc.list_panel.tree
    iid = f"u{sQ.uid}"
    tree.see(iid)
    w.update_idletasks()
    w.update()
    bb = tree.bbox(iid, "#1")
    for _ in range(10):                      # Windows 的 Tk 要等視窗真的畫出來，bbox 才有值
        if bb:
            break
        time.sleep(0.1)
        w.update()
        bb = tree.bbox(iid, "#1")
    bx, by, bw, bh = bb
    pc.list_panel._on_click(SimpleNamespace(x=bx + bw // 2, y=by + bh // 2))
    check(sQ.visible is False and tree.item(iid, "values")[0] == "☐" and sQ.uid not in pc.info.lines, "清單點 ☑ → 隱藏，不畫")
    texts = [x.get_text() for x in pc.info.legend.get_texts()]
    check(texts == ["I", "clk"], f"隱藏後圖例排除（{texts}）")
    pc.toggle_visible([sQ.uid])
    check(sQ.visible and sQ.uid in pc.info.lines, "再點 → 顯示")
    pc.canvas.draw()
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    px, py = ax.transData.transform((xd[500], yd[500]))
    pc.v_tips.set(False)                     # 這一段測「資料提示關掉時：點線＝選取、雙擊改色」
    pc._on_tips_toggle()
    press_release(pc, px, py)
    check(pc.selected == {sI.uid} and pc.list_panel.selected_uids() == {sI.uid}, "圖上點線 → 選取、清單同步")
    check(ln.get_linewidth() == 0.5 * 2.5, f"選取加粗 {ln.get_linewidth()}")
    lq = pc.info.lines[sQ.uid]
    xq, yq = lq.get_xdata(), lq.get_ydata()
    qx, qy = ax.transData.transform((xq[700], yq[700]))
    press_release(pc, qx, qy, modifiers={"shift"})
    check(pc.selected == {sI.uid, sQ.uid}, "Shift 點線 → 加選")
    press_release(pc, px, py, dbl=True)
    check(sI.color == "#ff0000" and pc.info.lines[sI.uid].get_color() == "#ff0000", "雙擊線 → 顏色對話框（patch）→ 改色")
    ax = pc.info.ax_left                              # 改色會整張重畫，axes 是新的
    ex, ey = ax.transData.transform((470.0, 0.0))      # I=0.81、Q=-0.59、clk 在右軸 0/1：三條都不在這點
    hit = pc.ia.hit_test(MouseEvent("button_press_event", pc.canvas, ex, ey, button=1))
    press_release(pc, ex, ey)
    check(pc.selected == set(), f"點空白 → 取消選取（hit={hit.kind} {hit.id}）")
    pc.select({sQ.uid})
    pc.edit_linewidth()
    pc.set_marker("o")
    check(sQ.lw == 3.0 and sQ.marker == "o" and pc.info.lines[sQ.uid].get_marker() == "o", "線寬／標記對話框與套用")
    pc.set_yaxis({sQ.uid}, "right")
    check(sQ.yaxis == "right" and pc.info.lines[sQ.uid].axes is pc.info.ax_right, "改到右軸")
    pc.set_yaxis({sQ.uid}, "left")


@step
def s3_context_and_legend():
    pc = w.pc
    pc.canvas.draw()
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    px, py = ax.transData.transform((xd[300], yd[300]))
    menus.clear()
    press_release(pc, px, py, button=3)
    check(menus and "顏色…" in menus[-1] and any(s.startswith("插入垂直參考線") for s in menus[-1]) and "複製到新視窗" in menus[-1],
          f"右鍵線條選單（{len(menus[-1]) if menus else 0} 項）")
    leg = pc.info.legend
    r = pc.canvas.get_renderer()
    bb = leg.get_texts()[0].get_window_extent(r)
    cx, cy = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
    hit = pc.ia.hit_test(MouseEvent("button_press_event", pc.canvas, cx, cy, button=1))
    check(hit.kind == "legend" and hit.id == pc.info.legend_uids[0], f"hit_test：圖例文字（{hit.kind}, {hit.id}）")
    press_release(pc, cx, cy, dbl=True)
    ed = pc._editor
    check(ed is not None and ed.entry.winfo_exists(), "雙擊圖例 → 就地編輯 Entry")
    ed.entry.delete(0, "end")
    ed.entry.insert(0, "I renamed")
    ed._commit()
    uid0 = pc.info.legend_uids[0]
    check(pc.state.find(uid0).label == "I renamed" and pc.info.legend.get_texts()[0].get_text() == "I renamed", "圖例改名套用")


@step
def s3b_legend_drag_and_menu():
    """跟 MATLAB 一樣：拖曳圖例＝移動圖例（不是平移）；圖例右鍵有「刪除圖例」「圖例位置」（MATLAB 圖例選單的 Delete／Location）。"""
    pc = w.pc
    pc.canvas.draw()
    ax = pc.info.ax_left
    leg = pc.info.legend
    r = pc.canvas.get_renderer()
    lb = leg.get_window_extent(r)
    tb = leg.get_texts()[0].get_window_extent(r)
    hx, hy = (lb.x0 + tb.x0) / 2, (tb.y0 + tb.y1) / 2       # 圖例框裡、文字左邊（線段樣本那一帶）
    xl0 = ax.get_xlim()
    axbb0 = tuple(ax.bbox.bounds)
    pc.ia.on_press(MouseEvent("button_press_event", pc.canvas, hx, hy, button=1))
    pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, hx - 90, hy - 60))
    pc.ia.on_release(MouseEvent("button_release_event", pc.canvas, hx - 90, hy - 60, button=1))
    pc.canvas.draw()
    lb1 = pc.info.legend.get_window_extent(pc.canvas.get_renderer())
    xl1 = pc.info.ax_left.get_xlim()                 # redraw 會換新的 axes 物件：看新的
    check(isinstance(pc.state.legend_loc, tuple) and abs(xl1[0] - xl0[0]) < 1e-9 and abs(xl1[1] - xl0[1]) < 1e-9
          and abs((lb1.x0 - lb.x0) + 90) < 3 and abs((lb1.y0 - lb.y0) + 60) < 3,
          f"拖曳圖例 → 圖例移動 (-90,-60)、不平移（Δ=({lb1.x0 - lb.x0:.0f},{lb1.y0 - lb.y0:.0f})，xlim {xl0}→{xl1}，loc={pc.state.legend_loc}）")
    check(tuple(pc.info.ax_left.bbox.bounds) == axbb0, "圖例移動後 axes 大小不變（constrained layout 不為圖例縮小 axes）")
    pc.undo()
    check(pc.state.legend_loc == "upper right", "undo 圖例移動")
    pc.canvas.draw()
    tb = pc.info.legend.get_texts()[0].get_window_extent(pc.canvas.get_renderer())
    menus.clear()
    press_release(pc, (tb.x0 + tb.x1) / 2, (tb.y0 + tb.y1) / 2, button=3)
    check(menus and "刪除圖例" in menus[-1] and "圖例位置" in menus[-1] and "顏色…" not in menus[-1],
          f"右鍵圖例：刪除圖例／圖例位置（MATLAB 的 Delete／Location），不是線條樣式（{menus[-1] if menus else []}）")
    pc.on_legend_loc(pc.info.ax_left, "lower left")
    pc.canvas.draw()
    lb2 = pc.info.legend.get_window_extent(pc.canvas.get_renderer())
    check(pc.state.legend_loc == "lower left" and lb2.x0 < lb.x0 and lb2.y0 < lb.y0, "圖例位置 → 左下")
    pc.on_legend_delete(pc.info.ax_left)
    check(not pc.state.legend and pc.info.legend is None, "刪除圖例 → 圖例關掉")
    pc.undo()
    pc.undo()
    check(pc.state.legend and pc.state.legend_loc == "upper right", "undo ×2 → 圖例回右上")


def submenu_labels(m, label):
    """tk.Menu m 裡名為 label 的子選單：回傳 (子選單, [項目標籤])；分隔線記成 "---"。"""
    for i in range(m.index("end") + 1):
        if m.type(i) == "cascade" and m.entrycget(i, "label") == label:
            sub = m.nametowidget(m.entrycget(i, "menu"))
            labs = []
            for j in range(sub.index("end") + 1):
                labs.append("---" if sub.type(j) == "separator" else sub.entrycget(j, "label"))
            return sub, labs
    return None, []


@step
def s3c_line_menu_matlab_values():
    """線條右鍵（先選取那條線）：線寬／標記大小是 MATLAB 線條選單的固定值，線型 solid／dash／dot／dash-dot／none，標記 14 種。"""
    pc = w.pc
    pc.canvas.draw()
    pc.select(set())
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    px, py = ax.transData.transform((xd[300], yd[300]))
    menus.clear()
    press_release(pc, px, py, button=3)
    check(pc.selected == {sI.uid}, "右鍵線條 → 先選取那條線")
    m = menu_objs[0] if menu_objs else None
    check(m is not None and "線寬" in menus[-1] and "標記大小" in menus[-1] and "線寬…" not in menus[-1], f"線條選單有 線寬 ▸／標記大小 ▸（{menus[-1] if menus else []}）")
    sub_w, lw_labels = submenu_labels(m, "線寬")
    check(lw_labels == ["0.5"] + [f"{v}.0" for v in range(1, 13)] + ["---", "自訂…"], f"線寬 ▸ 0.5、1.0 … 12.0、自訂…（{lw_labels}）")
    _sub, ms_labels = submenu_labels(m, "標記大小")
    check(ms_labels == ["2", "4", "5", "6", "7", "8", "10", "12", "18", "24", "48", "---", "自訂…"], f"標記大小 ▸ MATLAB 的 11 個值（{ms_labels}）")
    _sub, ls_labels = submenu_labels(m, "線型")
    check(ls_labels == ["solid  -", "dash  --", "dot  :", "dash-dot  -.", "none"], f"線型 ▸ solid／dash／dot／dash-dot／none（{ls_labels}）")
    _sub, mk_labels = submenu_labels(m, "標記")
    check(len(mk_labels) == 14 and mk_labels[0] == "無" and mk_labels[-1] == "六角星 h", f"標記 ▸ MATLAB 的 14 種（{mk_labels}）")
    sub_w.invoke(lw_labels.index("2.0"))
    check(pc.state.find(sI.uid).lw == 2.0, "線寬 ▸ 2.0 → 套用")
    pc.undo()
    check(pc.state.find(sI.uid).lw != 2.0, "undo 線寬")
    pc.select(set())


@step
def s4_wheel_pan_tips():
    pc = w.pc
    pc.canvas.draw()
    ax = pc.info.ax_left
    xl0 = ax.get_xlim()
    cx, cy = ax.transData.transform((500.0, 0.0))
    pc.ia.on_scroll(MouseEvent("scroll_event", pc.canvas, cx, cy, step=1))
    xl1 = ax.get_xlim()
    check((xl1[1] - xl1[0]) < (xl0[1] - xl0[0]) and pc.state.view["xlim"] is not None, "滾輪放大並記錄 view")
    ex, ey = ax.transData.transform((500.0, 0.5))
    pc.ia.on_press(MouseEvent("button_press_event", pc.canvas, ex, ey, button=1))
    pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, ex + 80, ey))
    pc.ia.on_release(MouseEvent("button_release_event", pc.canvas, ex + 80, ey, button=1))
    check(ax.get_xlim()[0] < xl1[0], "拖曳平移")
    pc.ia.on_key(KeyEvent("key_press_event", pc.canvas, "home", ex, ey))
    ax = pc.info.ax_left                      # 還原視圖會整張重畫，axes 是新的
    xl2 = ax.get_xlim()
    check(abs(xl2[0] - xl0[0]) < 1e-6 and abs(xl2[1] - xl0[1]) < 1e-6, f"Home 還原視圖（{xl2} vs {xl0}）")
    pc.v_tips.set(True)
    pc._on_tips_toggle()
    pc.canvas.draw()
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    px, py = ax.transData.transform((xd[1000], yd[1000]))
    press_release(pc, px, py)
    check(len(pc.state.tips) == 1 and pc.state.tips[0].index == 1000 and len(pc.ia.tip_artists) == 1, "資料提示模式：點線釘住")
    pc.set_props([sQ.uid], "色", color="#00aa00")
    check(len(pc.ia.tip_artists) == 1 and len(pc.state.tips) == 1, "改樣式重畫後資料提示仍在")
    pc.v_tips.set(False)
    pc._on_tips_toggle()
    pc.canvas.draw()
    ann, mk = pc.ia.tip_artists[pc.state.tips[0].id]
    bb = ann.get_bbox_patch().get_window_extent(pc.canvas.get_renderer())
    tx, ty = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
    off_default = pk.model.TIP_OFFSET_DEFAULT
    off_placed = pc.state.tips[0].offset                        # 釘上時框放哪一角（像 MATLAB LocationMode auto）就決定了
    check(abs(off_placed[0]) == off_default[0] and abs(off_placed[1]) == off_default[1], f"資料提示框貼在資料點的一角（offset={off_placed}）")
    pc.ia.on_press(MouseEvent("button_press_event", pc.canvas, tx, ty, button=1))
    pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, tx + 30, ty + 10))
    pc.ia.on_release(MouseEvent("button_release_event", pc.canvas, tx + 30, ty + 10, button=1))
    check(pc.state.tips[0].offset != off_placed, f"拖曳資料提示（offset={pc.state.tips[0].offset}）")
    before = len(pc.undo_stack)
    pc.undo()
    check(pc.state.tips[0].offset == off_placed and len(pc.undo_stack) == before - 1, "Ctrl+Z 還原資料提示位置")
    pc.redo()
    check(pc.state.tips[0].offset != off_placed, "Ctrl+Y 重做")


@step
def s4c_original_view_ruler():
    """MATLAB Restore View＝原始視圖：set_xlim(300, 600) → 滾輪 → Home 鍵／工具列 Home 回 300..600；twin 右軸的 y 尺規只動右軸。"""
    pc = w.pc
    pc.set_xlim(300, 600)
    pc.canvas.draw()
    ax = pc.info.ax_left
    cx, cy = ax.transData.transform((450.0, 0.0))
    pc.ia.on_scroll(MouseEvent("scroll_event", pc.canvas, cx, cy, step=1))
    zoomed = ax.get_xlim() != (300.0, 600.0)
    pc.ia.on_key(KeyEvent("key_press_event", pc.canvas, "home", cx, cy))
    xl = pc.info.ax_left.get_xlim()
    check(zoomed and abs(xl[0] - 300) < 1e-6 and abs(xl[1] - 600) < 1e-6, f"set_xlim(300, 600) → 滾輪 → Home 回 300..600（{xl}）")
    ax = pc.info.ax_left
    pc.ia.on_scroll(MouseEvent("scroll_event", pc.canvas, cx, cy, step=1))
    pc.plot_toolbar._home()
    xl = pc.info.ax_left.get_xlim()
    check(abs(xl[0] - 300) < 1e-6 and abs(xl[1] - 600) < 1e-6, f"工具列 Home 也回 300..600（{xl}）")
    pc.canvas.draw()
    axl, axr = pc.info.ax_left, pc.info.ax_right
    labs = [t for t in axr.yaxis.get_majorticklabels() if t.get_visible() and t.get_text()]
    bb = labs[len(labs) // 2].get_window_extent(pc.canvas.get_renderer())
    rx, ry = int((bb.x0 + bb.x1) / 2), int((axr.bbox.y0 + axr.bbox.y1) / 2)
    l0, r0, x0 = axl.get_ylim(), axr.get_ylim(), axl.get_xlim()
    hit = pc.ia.hit_test(MouseEvent("button_press_event", pc.canvas, rx, ry, button=1))
    pc.ia.on_press(MouseEvent("button_press_event", pc.canvas, rx, ry, button=1))
    pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, rx, ry + 40))
    pc.ia.on_release(MouseEvent("button_release_event", pc.canvas, rx, ry + 40, button=1))
    axl, axr = pc.info.ax_left, pc.info.ax_right
    check(hit.kind == "ruler" and hit.id == "y" and axr.get_ylim() != r0 and axl.get_ylim() == l0 and axl.get_xlim() == x0,
          f"拖曳右軸的 y 尺規只動右軸（MATLAB rulerPanInteraction；hit {hit.kind} {hit.id}）")
    pc.set_xlim()


@step
def s4b_matlab_zoom_mode():
    """放大模式照 MATLAB：單擊 1.5 倍、Shift＋單擊縮小、細長框只縮一個方向、小拖 1.2 倍、右鍵模式選單、雙擊還原；滾輪一格 1.1、縮小有外界。"""
    pc = w.pc
    pc.restore_view(); w.update()
    ax = pc.info.ax_left
    home, yhome = ax.get_xlim(), ax.get_ylim()
    cx, cy = ax.transData.transform((500.0, 0.0))
    pc.ia.on_scroll(MouseEvent("scroll_event", pc.canvas, cx, cy, step=1))
    xl1 = ax.get_xlim()
    check(abs((home[1] - home[0]) / (xl1[1] - xl1[0]) - 1.1) < 1e-6, "滾輪一格 = 1.1 倍（MATLAB 滾輪縮放的上限）")
    for _k in range(6):
        pc.ia.on_scroll(MouseEvent("scroll_event", pc.canvas, cx, cy, step=-1))
    check(abs(ax.get_xlim()[0] - home[0]) < 1e-9 and abs(ax.get_xlim()[1] - home[1]) < 1e-9 and abs(ax.get_ylim()[1] - yhome[1]) < 1e-9,
          f"滾輪縮小到自動範圍為止（{ax.get_xlim()} vs {home}）")
    if not has_desktop(w):
        check(True, "（無桌面工作階段：放大模式的 Tk 事件測試略過）")
        return
    pc.v_tips.set(True); pc._on_tips_toggle()
    pc.plot_toolbar._zoom(); w.update()
    tk_click(pc.canvas, cx, cy)
    xs = ax.get_xlim()
    px1 = (home[1] - home[0]) / ax.bbox.width                 # Tk 事件的座標是整數像素：以點為中心的誤差 < 1 px
    check(abs((home[1] - home[0]) / (xs[1] - xs[0]) - 1.5) < 1e-6 and abs(ax.transData.inverted().transform((cx, cy))[0] - 500.0) < px1,
          f"放大模式單擊 → 以該點為中心放大 1.5 倍（{xs}）")
    time.sleep(0.6); w.update()                                # 同一點再點一下要隔 500 ms 以上，不然 Tk 當雙擊（＝還原視圖）
    cx2, cy2 = ax.transData.transform((500.0, 0.0))            # constrained layout 會因刻度文字變寬而移動座標區：用同一個資料點再點
    tk_click(pc.canvas, cx2, cy2, shift=True)
    py1 = (yhome[1] - yhome[0]) / ax.bbox.height
    check(abs(ax.get_xlim()[0] - home[0]) < px1 and abs(ax.get_xlim()[1] - home[1]) < px1          # Tk 事件是整數像素：差 < 1 px
          and abs(ax.get_ylim()[0] - yhome[0]) < py1 and abs(ax.get_ylim()[1] - yhome[1]) < py1,
          f"Shift＋單擊 → 縮小 1.5 倍（回到自動範圍，受外界夾住；{ax.get_xlim()} vs {home}）")
    pc.restore_view(); w.update()
    ax = pc.info.ax_left
    wdg = pc.canvas.get_tk_widget()
    h = pc.canvas.get_width_height(physical=True)[1]

    def tk_drag(x0, y0, x1, y1, btn=1):
        X0, Y0, X1, Y1 = int(x0), int(h - y0), int(x1), int(h - y1)
        mask = {1: 0x100, 2: 0x200, 3: 0x400}[btn]
        t = int(time.monotonic() * 1000) & 0x7fffffff
        wdg.event_generate(f"<ButtonPress-{btn}>", x=X0, y=Y0, when="now", time=t)
        for k in range(1, 6):
            wdg.event_generate("<Motion>", x=X0 + (X1 - X0) * k // 5, y=Y0 + (Y1 - Y0) * k // 5, state=mask, when="now", time=t + k * 20)
        wdg.event_generate(f"<ButtonRelease-{btn}>", x=X1, y=Y1, state=mask, when="now", time=t + 150)
        w.update()
    bb = ax.bbox
    x0, y0 = bb.x0 + bb.width * 0.3, bb.y0 + bb.height * 0.5
    dx_ = min(150.0, bb.width * 0.6)          # 0.9.14 W（F2）：座標區比 250 px 窄時（Windows 175% 沒宣告 DPI 的行程）框照比例縮短、留在座標區裡；Mac 照舊 150
    da, db = ax.transData.inverted().transform((x0, y0))[0], ax.transData.inverted().transform((x0 + dx_, y0))[0]
    tk_drag(x0, y0, x0 + dx_, y0 + 6)
    xb = ax.get_xlim()
    check(abs(xb[0] - da) < px1 and abs(xb[1] - db) < px1 and ax.get_ylim() == yhome,              # 框的角落是整數像素：差 < 1 px
          f"拖 {dx_:.0f}×6 的細長框 → 只縮 x、y 不動（{xb} vs {(da, db)}）")
    pc.restore_view(); w.update()
    ax = pc.info.ax_left
    x0, y0 = ax.bbox.x0 + ax.bbox.width * 0.5, ax.bbox.y0 + ax.bbox.height * 0.5
    tk_drag(x0, y0, x0 + 12, y0 + 12)
    check(abs((home[1] - home[0]) / (ax.get_xlim()[1] - ax.get_xlim()[0]) - 1.2) < 1e-6, "拖 12×12（兩邊都不到 15 px）→ 以點為中心放大 1.2 倍")
    xr = ax.get_xlim()
    menus.clear()
    tk_drag(x0, y0, x0 + 120, y0 + 80, btn=2 if sys.platform == "darwin" else 3)   # 右鍵（aqua 是 Button-2）：模式選單，不是縮小
    check(ax.get_xlim() == xr and menus and len(menus[-1]) == 5 and menus[-1][0].startswith("縮小"),
          f"放大模式右鍵 → MATLAB 模式選單（{menus[-1] if menus else None}）、不縮放")
    X, Y = int(x0), int(h - y0)
    time.sleep(0.6); w.update()
    t = int(time.monotonic() * 1000) & 0x7fffffff
    for _k in range(2):                                        # 兩個 50 ms 內的 ButtonPress-1：Tk 合成 Double → 還原視圖
        wdg.event_generate("<ButtonPress-1>", x=X, y=Y, when="now", time=t + _k * 50)
        wdg.event_generate("<ButtonRelease-1>", x=X, y=Y, state=0x100, when="now", time=t + _k * 50)
    w.update()
    ax = pc.info.ax_left
    check(abs(ax.get_xlim()[0] - home[0]) < 1e-9 and abs(ax.get_xlim()[1] - home[1]) < 1e-9, "放大模式雙擊 → 還原視圖")
    check(str(pc.toolbar.mode) == "zoom rect", "雙擊還原後仍在放大模式")
    pc.plot_toolbar._zoom(); w.update()
    check(str(pc.toolbar.mode) == "" and pc.v_tips.get(), "關掉放大模式 → 資料提示恢復")



@step
def s4b2_zoom_mode_dpr():
    """顯示縮放（Windows 150%：device_pixel_ratio=1.5）時放大模式的 10／15 px 門檻是邏輯像素（乘 dpr），和預設模式拖曳門檻一致；
    直接呼叫 MatlabNav 的方法（不靠 Tk 事件，無桌面也跑）。"""
    pc = w.pc
    c = pc.canvas
    nav = pc.toolbar
    c._set_device_pixel_ratio(1.5); c.draw(); w.update()
    try:
        pc.plot_toolbar._zoom(); w.update()

        def run(dx, dy):
            pc.restore_view(); c.draw(); w.update()
            ax = pc.info.ax_left
            xl, yl = ax.get_xlim(), ax.get_ylim()
            cx, cy = ax.bbox.x0 + ax.bbox.width / 2, ax.bbox.y0 + ax.bbox.height / 2
            nav.press_zoom(MouseEvent("button_press_event", c, cx, cy, button=MouseButton.LEFT))
            nav.drag_zoom(MouseEvent("motion_notify_event", c, cx + dx, cy + dy, buttons={MouseButton.LEFT}))
            roi = len(nav._roi_ids)
            nav.release_zoom(MouseEvent("button_release_event", c, cx + dx, cy + dy, button=MouseButton.LEFT))
            x2, y2 = ax.get_xlim(), ax.get_ylim()
            return (xl[1] - xl[0]) / (x2[1] - x2[0]), (yl[1] - yl[0]) / (y2[1] - y2[0]), roi
        rx, ry, roi = run(12, 0)                                 # 12 實體 px＝8 邏輯 px：還是單擊
        check(abs(rx - 1.5) < 1e-6 and abs(ry - 1.5) < 1e-6 and roi == 0, f"dpr 1.5：拖 12 實體 px（8 邏輯 px）＝單擊 1.5 倍、不畫框（{rx:.3f} {ry:.3f}）")
        rx, ry, roi = run(20, 0)                                 # 20 實體 px＝13.3 邏輯 px：兩邊都 <15 → 1.2 倍
        check(abs(rx - 1.2) < 1e-6 and abs(ry - 1.2) < 1e-6 and roi == 1,      # ≥10 邏輯 px 已開始畫框，放開時兩邊 <15 → 1.2 倍
              f"dpr 1.5：拖 20 實體 px（13.3 邏輯 px）＝以點為中心 1.2 倍（{rx:.3f} {ry:.3f} roi={roi}）")
        rx, ry, roi = run(90, 15)                                # 高 15 實體 px＝10 邏輯 px <15：只縮 x，拖曳中畫 22 px 帶子
        check(rx > 3 and abs(ry - 1.0) < 1e-9 and roi == 3, f"dpr 1.5：拖 90×15 實體 px → 只縮 x、畫帶子（{rx:.2f} {ry:.3f} roi={roi}）")
        rx, ry, roi = run(60, 60)                                # 40×40 邏輯 px：框選
        check(rx > 3 and ry > 3 and roi == 1, f"dpr 1.5：拖 60×60 實體 px → 框選（{rx:.2f} {ry:.2f}）")
        pc.plot_toolbar._zoom(); w.update()
    finally:
        c._set_device_pixel_ratio(1.0); pc.restore_view(); c.draw(); w.update()
    check(str(pc.toolbar.mode) == "" and c.device_pixel_ratio == 1.0, "dpr 還原 1、放大模式關掉")


def toolbar_order(pt):
    """工具列實際的左→右順序（pack_slaves；winfo_children 是建立順序，不能用）：按鈕回 key、分隔線回 "|"。"""
    keys = {str(b): k for k, b in pt.buttons.items()}
    return [keys.get(str(c), "|" if c.winfo_class() == "TSeparator" else "?") for c in pt.left.pack_slaves()]


@step
def s4d_toolbar_order_keys():
    """MATLAB axes 工具列的順序、放大模式拖框時 Esc 取消、Ctrl＋W／⌘W 關閉圖形視窗。"""
    pc = w.pc
    order = toolbar_order(pc.plot_toolbar)
    check(order[:12] == ["save", "clip", "clipvec", "tips", "pan", "zoom", "zoomout", "|", "home", "|", "back", "forward"]
          and "fit" not in order and "undo" in order,
          f"工具列順序照 MATLAB axtoolbar：存檔／複製影像／複製向量圖 → 資料提示 → 平移 → 放大 → 還原視圖（{order}）")
    pc.restore_view(); w.update()
    ax = pc.info.ax_left
    xl0 = ax.get_xlim()
    nav = pc.toolbar
    pc.plot_toolbar._zoom(); w.update()
    bb = ax.bbox
    x0, y0 = bb.x0 + bb.width * 0.3, bb.y0 + bb.height * 0.3
    nav.press_zoom(MouseEvent("button_press_event", pc.canvas, x0, y0, button=1))
    nav.drag_zoom(MouseEvent("motion_notify_event", pc.canvas, x0 + 120, y0 + 80, buttons=[1]))
    dragging = nav._zoom_info is not None
    pc.ia.on_key(KeyEvent("key_press_event", pc.canvas, "escape", x0 + 120, y0 + 80))
    nav.release_zoom(MouseEvent("button_release_event", pc.canvas, x0 + 120, y0 + 80, button=1))
    check(dragging and nav._zoom_info is None and ax.get_xlim() == xl0,
          "放大模式拖框中按 Esc → 取消，放開也不縮放（MATLAB 的 zoom：Esc 取消）")
    pc.plot_toolbar._zoom(); w.update()
    check(str(pc.toolbar.mode) == "", "關掉放大模式")
    for mod in (["Control"] + (["Command"] if sys.platform == "darwin" else [])):
        w3 = pk.figure(title=f"close {mod}")
        w3.plot(np.arange(5.0), np.arange(5.0), label="x")
        w3.update()
        tk_key(w3, "w", mods=mod)
        root.update()
        check(w3 not in pk.windows() and not w3.winfo_exists(), f"{mod}＋W 關閉圖形視窗（MATLAB File > Close）")


@step
def s4d2_keyboard_view_undo():
    """MATLAB：鍵盤縮放／平移進圖形視窗的 undo；Ctrl+Z 復原視圖、不刪線。"""
    pc = w.pc
    pc.restore_view(); w.update(); pc.canvas.draw(); w.update()
    n = len(pc.state.series)
    xl0 = tuple(pc.info.ax_left.get_xlim())
    cw = pc.canvas.get_tk_widget()
    tk_key(cw, "plus", char="+"); tk_key(cw, "plus", char="+"); w.update()
    xl1 = tuple(pc.info.ax_left.get_xlim())
    tk_key(w, "z", mods="Control"); w.update()
    check(xl1 != xl0 and tuple(pc.info.ax_left.get_xlim()) == xl0 and len(pc.state.series) == n,
          f"＋＋ 放大 → Ctrl+Z 復原視圖、線還在（{len(pc.state.series)} 條）")
    tk_key(w, "y", mods="Control"); w.update()
    check(tuple(pc.info.ax_left.get_xlim()) == xl1, "Ctrl+Y 重做放大")
    pc.restore_view(); w.update()


@step
def szy_zhuyin_figure_keys():
    """注音等非拉丁輸入法（2026-10-27 使用者第二次選單「全部都修」）：Tk 給 ⌘V 的 keysym 是 "??"、- 是 "??"（字 ㄦ），
    圖片視窗的 <Command-v> 這些綁定都對不到。照實體按鍵認：⌘A／⌘C／⌘V／⌘Z／⌘Y／⌘S／⌘W 和 - 鍵都和 ABC 一樣、每按一次只做一次；
    視窗裡的輸入框（類別綁定）⌘V 照樣貼字。keysym／keycode 是在使用者的注音輸入法之下用真的按鍵量的（plotkit/keys.py）。"""
    if sys.platform != "darwin":
        check(True, "（不是 macOS：注音輸入法的實體按鍵對照只在 macOS，略過）")
        return
    pc = w.pc
    cw = pc.canvas.get_tk_widget()
    zy = {"c": 0x08000063, "v": 0x09000076, "z": 0x0600007A, "y": 0x10000079, "a": 0x00000061, "s": 0x01000073, "w": 0x0D000077}

    def zk(widget, k):
        tk_key(widget, "??", char=k, mods="Command", keycode=zy[k])
        root.update()

    sel0 = set(pc.selected)
    pc.restore_view(); w.update()
    pc.select(set()); w.update()
    zk(cw, "a")
    check(len(pc.selected) == len(pc.state.series) > 0, f"注音的 ⌘A（keysym ??、keycode 0x00000061）全選（{len(pc.selected)}／{len(pc.state.series)}）")
    pk.CLIPBOARD[:] = []
    pc.select({sI.uid}); w.update()
    zk(cw, "c")
    check(len(pk.CLIPBOARD) == 1 and pk.CLIPBOARD[0].label == sI.label, f"注音的 ⌘C 複製選取的 1 條（{[x.label for x in pk.CLIPBOARD]}）")
    n0 = len(pc.state.series)
    zk(cw, "v")
    n1 = len(pc.state.series)
    tk_key(cw, "v", char="v", mods="Command"); root.update()       # ABC 的 ⌘V（拉丁 keysym）：<Command-v> 接下，<Key> 後備不會再貼一次
    n2 = len(pc.state.series)
    zk(cw, "z")
    n3 = len(pc.state.series)
    zk(cw, "y")
    n4 = len(pc.state.series)
    zk(cw, "z")
    n5 = len(pc.state.series)
    tk_key(cw, "??", char="Z", mods="Shift-Command", keycode=0x0640005A); root.update()     # 注音的 ⇧⌘Z（重做；照實體按鍵認成大寫 Z）
    n6 = len(pc.state.series)
    check(n1 == n0 + 1 and n2 == n0 + 2 and n3 == n0 + 1 and n4 == n0 + 2 and n5 == n0 + 1 and n6 == n0 + 2,
          f"注音的 ⌘V 貼一條、ABC 的 ⌘V 也只貼一條（{n0}→{n1}→{n2}）、注音的 ⌘Z 只拿掉一條（{n3}）、⌘Y 只放回一條（{n4}）、再 ⌘Z（{n5}）、"
          f"⇧⌘Z 只重做一條（{n6}，不是復原）")
    zk(cw, "z"); zk(cw, "z")
    check(len(pc.state.series) == n0, f"再 ⌘Z 兩次 → 回到貼上前的 {n0} 條")
    saved = []
    fd0 = pk.dialogs.filedialog
    pk.dialogs.filedialog = SimpleNamespace(asksaveasfilename=lambda **k: saved.append(k.get("title")) or "",
                                            askopenfilename=lambda **k: "")
    try:
        zk(cw, "s")
    finally:
        pk.dialogs.filedialog = fd0
    check(len(saved) == 1, f"注音的 ⌘S 開一次「另存 JSON」（{saved}）")
    ax = pc.info.ax_left
    tk_key(cw, "plus", char="+"); tk_key(cw, "plus", char="+"); root.update()     # 先放大（原始視圖不能再縮小，MATLAB 一樣）
    xa = ax.get_xlim()
    tk_key(cw, "??", char="ㄦ", keycode=0x1B003126); root.update()     # 注音的 - 鍵（沒按 ⌘；字 ㄦ）
    xb = ax.get_xlim()
    r = (xb[1] - xb[0]) / (xa[1] - xa[0])
    check(abs(r - 1.1) < 0.02, f"注音的 - 鍵（keysym ??、字 ㄦ）照實體按鍵認成 −：縮小一次（×{r:.3f}）")
    pc.restore_view(); w.update()
    e = pk.dialogs.ttk.Entry(w)                         # 圖片視窗裡的輸入框（類別綁定由 plotkit 裝上：注音的 ⌘V 照樣貼字）
    root.clipboard_clear(); root.clipboard_append("貼上的字")
    zk(e, "v")
    check(e.get() == "貼上的字", f"圖片視窗裡的輸入框：注音的 ⌘V 貼上剪貼簿的字（「{e.get()}」）")
    n5 = len(pc.state.series)
    zk(cw, "v")
    n6 = len(pc.state.series)
    zk(e, "z")
    check(n6 == n5 + 1 and len(pc.state.series) == n6, f"焦點在輸入框時注音的 ⌘Z 留給輸入框，不復原圖（{n5}→{n6}→{len(pc.state.series)}）")
    zk(cw, "z")
    e.destroy()
    # 輸入框類別的後備把 <<Paste>> 送給輸入框之後，這一次按鍵就停了：上一層（頂層視窗）只看到 <<Paste>>、不會再看到這個按鍵——
    # 和 ABC 一樣（ABC 之下頂層視窗那一層 <<Paste>> 比 <Key> 精確，只執行 <<Paste>>）；不然同一次按鍵會在上一層再做一次
    t = pk.dialogs.tk.Toplevel(root)
    e2 = pk.dialogs.ttk.Entry(t)
    e2.pack()
    seen = {"paste": 0, "key": 0}
    t.bind("<<Paste>>", lambda ev: seen.__setitem__("paste", seen["paste"] + 1), add="+")
    t.bind("<Key>", lambda ev: seen.__setitem__("key", seen["key"] + 1), add="+")
    t.update()
    zk(e2, "v")
    check(seen == {"paste": 1, "key": 0} and e2.get() == "貼上的字",
          f"輸入框裡注音的 ⌘V：輸入框貼一次、上一層只收到一次 <<Paste>>、沒有再收到按鍵（和 ABC 一樣；{seen}）")
    t.destroy()
    w5 = pk.figure(title="close zhuyin")
    w5.plot(np.arange(5.0), np.arange(5.0), label="x")
    w5.update()
    zk(w5.pc.canvas.get_tk_widget(), "w")
    check(w5 not in pk.windows() and not w5.winfo_exists(), "注音的 ⌘W（keysym ??）關閉圖片視窗")
    if w5.winfo_exists():
        w5.close()                                      # 沒關掉時收拾好，後面的步驟才不受影響
    pc.select(sel0); pc.restore_view(); w.update()


@step
def s4e_hover_tips():
    """MATLAB dataTipInteraction：游標到線上 → 頂點標記＋crosshair，停 200 ms 出暫時提示框（不進模型／undo），移開收掉；
    提示文字「名稱／X 值／Y 值」；點在視圖外不畫。"""
    pc = w.pc
    pc.restore_view(); w.update()
    pc.v_tips.set(True); pc._on_tips_toggle()
    pc.canvas.draw()
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    hx, hy = ax.transData.transform((xd[700], yd[700]))
    n_tips, n_undo = len(pc.state.tips), len(pc.undo_stack)
    pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, hx, hy))
    h = pc.ia.hover_tip
    check(h is not None and h["uid"] == sI.uid and h["mk"].get_visible() and not h["ann"].get_visible()
          and len(pc.state.tips) == n_tips and len(pc.undo_stack) == n_undo, "hover：線上 → 頂點標記、框等 200 ms、不進模型／undo")
    pc.ia._hover_linger()
    txt = h["ann"].get_text().splitlines()
    check(h["ann"].get_visible() and txt[0].startswith("I") and txt[1].startswith("X ") and txt[2].startswith("Y "),
          f"hover：暫時提示框文字（{txt}）")
    pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, hx, ax.bbox.y1 - 2))
    check(pc.ia.hover_tip is None, "hover：離開線 → 收掉")
    tip = pc.ia.add_tip(sI.uid, 700)
    t_ann, t_mk = pc.ia.tip_artists[tip.id]
    xl0 = ax.get_xlim()
    ax.set_xlim(xd[1200], xd[1800])
    hid = not t_ann.get_visible() and not t_mk.get_visible()
    ax.set_xlim(*xl0)
    check(hid and t_ann.get_visible(), "資料點在 XLim 外 → 提示不畫、回來再畫")
    pc.ia.remove_tip(tip.id)
    pc.canvas.draw()
    if not has_desktop(w):
        check(True, "（無桌面工作階段：hover 的 Tk <Motion> 測試略過）")
        return
    wdg = pc.canvas.get_tk_widget()
    H = pc.canvas.get_width_height(physical=True)[1]
    w.update()
    wdg.event_generate("<Motion>", x=int(round(hx)), y=int(round(H - hy)), when="now")
    w.update()
    cur0 = str(wdg.cget("cursor"))
    h = pc.ia.hover_tip
    t_end = time.monotonic() + 1.5
    while h is not None and not h["ann"].get_visible() and time.monotonic() < t_end:
        time.sleep(0.02)
        w.update()
    shown = h is not None and h["ann"].get_visible()
    check(h is not None and cur0 == "crosshair" and shown, f"Tk <Motion> 到線上 → crosshair、200 ms 後出框（cursor={cur0!r} shown={shown}）")
    wdg.event_generate("<Motion>", x=int(round(hx)), y=int(round(H - (ax.bbox.y1 - 2))), when="now")
    w.update()
    check(pc.ia.hover_tip is None and str(wdg.cget("cursor")) != "crosshair", "Tk <Motion> 離開線 → 收掉、游標還原")


@step
def s5_annotations_undo():
    pc = w.pc
    w.xline(250.0, "sync")
    w.yline(0.5, "half")
    w.text(600.0, 0.8, "note")
    check(len(pc.state.annotations) == 3 and len(pc.ia.ann_artists) == 3, "xline / yline / text 標註")
    n0 = len(pc.state.annotations)
    pc.ia.remove_annotation(pc.state.annotations[0].id)
    check(len(pc.state.annotations) == n0 - 1, "刪除標註")
    pc.undo()
    check(len(pc.state.annotations) == n0 and len(pc.ia.ann_artists) == n0, "undo 還原標註（重畫後 artist 也回來）")
    # 選取的標註：焦點不在畫布時的 Delete（pc.delete_key）也照「提示 → 標註 → 線」的順序；選線會取消標註選取
    aid = pc.state.annotations[0].id
    n_ser = len(pc.state.series)
    pc.ia.select_annotation(aid)
    pc.delete_key()
    check(len(pc.state.annotations) == n0 - 1 and len(pc.state.series) == n_ser and pc.ia.selected_ann is None,
          "選取標註後 Delete（畫布外）→ 只刪標註、訊號不動")
    pc.undo()
    check(len(pc.state.annotations) == n0, "undo 復活標註")
    pc.ia.select_annotation(pc.state.annotations[0].id)
    pc.select({sI.uid})
    check(pc.ia.selected_ann is None, "選線 → 取消標註的選取（選取互斥）")
    pc.select(set())
    pc.rename(sQ.uid, "Q2")
    pc.undo()
    check(pc.state.find(sQ.uid).label == "Q", "undo 改名")        # undo/redo 之後是新的 Series 物件，要用 uid 查
    pc.redo()
    check(pc.state.find(sQ.uid).label == "Q2", "redo 改名")
    pc.select({sC.uid})
    pc.delete_selected()
    check(len(pc.state.series) == 2 and pc.info.ax_right is None, "刪除右軸訊號後 twin 消失")
    pc.undo()
    check(len(pc.state.series) == 3 and pc.info.ax_right is not None, "undo 刪除 → 右軸回來")
    w2 = pk.figure(title="test 2")
    check(pk.active_window() is w2 and len(pk.windows()) == 2, "第二個視窗成為 active")
    pc.select({sI.uid, sQ.uid})
    pc.copy_selected()
    check(len(pk.CLIPBOARD) == 2 and pk.CLIPBOARD[0].color == "#ff0000", "Ctrl+C 複製 2 條（含樣式）")
    w2.pc.paste()
    check(len(w2.series()) == 2 and w2.series()[0].uid == 1 and w2.series()[0].label == "I renamed", "Ctrl+V 貼到第二視窗（uid 重編）")
    w3 = w2.pc.copy_to_new_window()
    check(w3 is not None and len(w3.series()) == 2 and len(pk.windows()) == 3, "複製到新視窗")
    w3.close()
    check(len(pk.windows()) == 2 and pk.active_window() in (w, w2), "關閉視窗後登錄移除")
    w2.close()


@step
def s6_json_png_clipboard():
    pc = w.pc
    p = os.path.join(OUT, "fig.json")
    w.xlim(10, 20)                                   # 存檔前先縮放：open_json 要保留存檔時的視圖，不是自動範圍
    w.save_json(p)
    w4 = pk.open_json(p)
    s4 = w4.series()
    check(len(s4) == 3 and s4[0].label == "I renamed" and s4[0].color == "#ff0000" and len(w4.state.tips) == 1
          and len(w4.state.annotations) == 3 and w4.state.style == "matlab",
          f"save_json → open_json 還原內容（n={len(s4)} label={s4[0].label if s4 else None} color={s4[0].color if s4 else None} "
          f"tips={len(w4.state.tips)} anns={len(w4.state.annotations)} style={w4.state.style}）")
    vx = w4.state.view["xlim"]
    check(vx is not None and abs(vx[0] - 10) < 1e-6 and abs(vx[1] - 20) < 1e-6
          and abs(w4.pc.info.ax_left.get_xlim()[0] - 10) < 1e-6, f"open_json 保留存檔時的視圖範圍（xlim={vx}）")
    w4.close()
    w.restore_view()
    png = os.path.join(OUT, "fig.png")
    w.savefig(png)
    check(os.path.getsize(png) > 1000, "savefig PNG")
    check(w.to_png_bytes()[:4] == b"\x89PNG", "to_png_bytes")
    if os.environ.get("PLOTKIT_TEST_CLIPBOARD") == "1":
        ok, msg = w.copy_to_clipboard()
        check(ok, f"複製到系統剪貼簿（{msg}）")
    else:
        captured = {}
        orig = pk.clipboard.copy_png_to_clipboard
        pk.clipboard.copy_png_to_clipboard = lambda path: captured.setdefault("size", os.path.getsize(path)) and (True, "fake")
        ok, msg = w.copy_to_clipboard()
        pk.clipboard.copy_png_to_clipboard = orig
        check(ok and captured.get("size", 0) > 1000, "複製圖片：產生 PNG 並交給剪貼簿函式（已 patch）")
        capv = {}
        origv = pk.clipboard.copy_pdf_to_clipboard

        def fake_pdf(path):
            with open(path, "rb") as fh:
                capv["head"] = fh.read(5)
            return True, "fake pdf"
        pk.clipboard.copy_pdf_to_clipboard = fake_pdf
        if pk.clipboard.clipboard_vector_supported():
            try:
                pc.plot_toolbar.buttons["clipvec"].invoke()
            finally:
                pk.clipboard.copy_pdf_to_clipboard = origv
            check(capv.get("head") == b"%PDF-", "工具列「複製向量圖（PDF）」：產生 PDF 交給剪貼簿函式（MATLAB Copy as vector graphic）")
        else:
            pk.clipboard.copy_pdf_to_clipboard = origv
            check(True, "（這個系統的剪貼簿放不了向量圖：工具列「複製向量圖」的 invoke 測試略過，下面檢查它是停用的）")
    mb = w.nametowidget(w.cget("menu"))
    fmenu = mb.nametowidget(mb.entrycget(0, "menu"))
    flabels = [fmenu.entrycget(i, "label") for i in range(fmenu.index("end") + 1) if fmenu.type(i) == "command"]
    check("複製向量圖（PDF）到剪貼簿" in flabels, f"檔案選單有「複製向量圖（PDF）到剪貼簿」（{flabels}）")

    def _vec_states(win):
        fm = win.nametowidget(win.nametowidget(win.cget("menu")).entrycget(0, "menu"))
        i = [j for j in range(fm.index("end") + 1) if fm.type(j) == "command"
             and fm.entrycget(j, "label") == "複製向量圖（PDF）到剪貼簿"][0]
        b = win.pc.plot_toolbar.buttons["clipvec"]
        return str(fm.entrycget(i, "state")), bool(b.instate(["disabled"])), str(getattr(b, "_pk_tip", ""))
    vsup = pk.clipboard.clipboard_vector_supported()
    st_m, dis_b, _tip = _vec_states(w)
    check(st_m == ("normal" if vsup else "disabled") and dis_b == (not vsup),
          f"「複製向量圖」跟著平台啟用／停用（{sys.platform}：選單 {st_m}、按鈕 disabled={dis_b}）")
    orig_sup = pk.clipboard.clipboard_vector_supported
    pk.clipboard.clipboard_vector_supported = lambda: False            # 模擬 Windows：剪貼簿放不了向量圖
    try:
        wv = pk.figure("vec-off")
        wv.plot(np.arange(5), np.arange(5))
        st_m, dis_b, tip_b = _vec_states(wv)
        ok_call, msg_call = wv.pc.copy_vector_to_clipboard()
        wv.close()
    finally:
        pk.clipboard.clipboard_vector_supported = orig_sup
    check(st_m == "disabled" and dis_b and "放不了向量圖" in tip_b and not ok_call,
          f"剪貼簿放不了向量圖（Windows）：工具列按鈕與檔案選單停用、tooltip 說明（{tip_b}）；直接呼叫回報不支援（{msg_call}）")
    emb_root = pk.dialogs.tk.Toplevel(root)
    pc2 = pk.PlotCanvas(emb_root, show_list=False)
    pc2.plot(np.arange(10), np.arange(10) ** 2, label="emb", linewidth=2, linestyle=":")
    check(len(pc2.state.series) == 1 and pc2.info.lines and pc2.state.series[0].lw == 2 and pc2.state.series[0].ls == ":",
          "PlotCanvas 內嵌於自己的 Toplevel；linewidth/linestyle 別名")
    style_before = pc2.state.style
    try:
        pc2.set_style("bogus")
        check(False, "無效風格要丟錯")
    except KeyError:
        check(pc2.state.style == style_before and pc2.info.lines, "無效風格先丟錯、狀態不變、仍可重畫")
    try:
        pc2.set_legend(True, "nowhere")
        check(False, "無效 legend loc 要丟錯")
    except ValueError:
        check(pc2.state.legend_loc == "upper right", "無效 legend loc 先丟錯、狀態不變")
    try:
        pc2.plot(np.arange(3), np.arange(3), "r--")
        check(False, "pyplot 格式字串要丟錯")
    except ValueError:
        check(True, "plot(x, y, 'r--') 會提示改用 color/ls/marker")
    pc2.set_xlim((2, 5))
    check(tuple(pc2.state.view["xlim"]) == (2.0, 5.0), "xlim((a, b)) tuple 寫法")
    st_bad = pk.FigureState(series=[pk.Series("a", [0, 1], [0, 1]), pk.Series("b", [0, 1], [1, 0])])
    pbad = os.path.join(OUT, "uid0.json")
    pk.save_json(st_bad, pbad)
    w5 = pk.open_json(pbad)
    check(len(w5.series()) == 2 and [s.uid for s in w5.series()] == [1, 2], "沒給 uid 的 FigureState 存檔再開不會撞 iid")
    w5.close()
    emb_root.destroy()
    pk.show(block=False)
    check(True, "show(block=False) 會返回")


@step
def s6b_matlab_feedback():
    """跟 MATLAB R2025a 一樣的互動回饋：工具列模式的游標（平移＝張開的手、放大＝crosshair、關掉＝箭頭）、
    框選矩形（1 px #268cdd 實線、短邊 <15 px 畫 15 px 帶子、拖不到 10 px 不畫）、重畫不閃等待游標。"""
    pc = w.pc
    tb, cv = pc.plot_toolbar, pc.canvas
    wd = cv.get_tk_widget()
    calls = []
    orig = cv.set_cursor
    cv.set_cursor = lambda c: (calls.append(c), orig(c))
    time.sleep(1.1)
    pc.redraw()
    cv.draw()
    root.update()
    cv.set_cursor = orig
    check(not calls, f"隔 1 秒後重畫不會閃等待游標（set_cursor 呼叫 {calls}）")
    if not has_desktop(w):
        check(True, "（無桌面工作階段：游標與框選矩形的 Tk 事件測試略過）")
        return
    aqua = str(root.tk.call("tk", "windowingsystem")) == "aqua"
    pc.restore_view()
    cv.draw()
    root.update()

    def ev(seq, x, y, **kw):
        wd.event_generate(seq, x=x, y=y, rootx=wd.winfo_rootx() + x, rooty=wd.winfo_rooty() + y, when="now", **kw)

    def center():
        ax = pc.info.ax_left
        bb = ax.bbox
        h = cv.get_width_height(physical=True)[1]
        return ax, int((bb.x0 + bb.x1) / 2), int(h - (bb.y0 + bb.y1) / 2)

    items = []

    def grab():
        items[:] = [(wd.type(i), wd.itemcget(i, "outline" if wd.type(i) == "rectangle" else "fill")) for i in wd.find_all() if wd.type(i) != "image"]

    def drag(x0, y0, x1, y1, mid=None, state=0):
        ev("<ButtonPress-1>", x0, y0, state=state)
        root.update()
        for i in (1, 2, 3):
            ev("<Motion>", x0 + (x1 - x0) * i // 3, y0 + (y1 - y0) * i // 3, state=state | 0x100)
            root.update()
            if i == 2 and mid:
                mid()
        ev("<ButtonRelease-1>", x1, y1, state=state | 0x100)
        root.update()

    ax, cx, cy = center()
    tb._zoom()
    root.update()
    ev("<Motion>", cx, cy)
    root.update()
    check(wd.cget("cursor") == "crosshair", f"放大模式的游標＝crosshair（MATLAB 放大模式；{wd.cget('cursor')}）")
    xl0, yl0 = ax.get_xlim(), ax.get_ylim()
    # 0.9.14 W（F2）：框的大小照座標區縮（Windows 175% 沒宣告 DPI 的行程裡座標區只有約 200 px 寬，±100／±150 px 的框拖出座標區外）；
    # Mac 的座標區 737×447 px，min 之後仍是 ±100、±60、±150（和以前一樣）
    bw_, bh_ = ax.bbox.width, ax.bbox.height
    hx, hy, fx = int(min(100, 0.4 * bw_)), int(min(60, 0.4 * bh_)), int(min(150, 0.22 * bw_))
    drag(cx - hx, cy - hy, cx + hx, cy + hy, mid=grab)
    check(items == [("rectangle", "#268cdd")], f"框選矩形：一個 1 px #268cdd 實線框、沒有黑白虛線（{items}）")
    xl1, yl1 = ax.get_xlim(), ax.get_ylim()
    check(xl1[1] - xl1[0] < 0.5 * (xl0[1] - xl0[0]) and yl1[1] - yl1[0] < 0.5 * (yl0[1] - yl0[0])
          and not [i for i in wd.find_all() if wd.type(i) != "image"], "框選後兩軸都縮進去、矩形清掉")
    pc.restore_view()
    cv.draw()
    root.update()
    ax, cx, cy = center()
    xl0, yl0 = ax.get_xlim(), ax.get_ylim()
    drag(cx - fx, cy, cx + fx, cy + 6, mid=grab)
    check([t for t, _ in items] == ["line", "line", "line"] and all(c == "#268cdd" for _, c in items),
          f"扁的框（高 6 px < 15）→ 15 px 的帶子：兩端短邊線＋中線（{items}）")
    check(ax.get_ylim() == yl0 and ax.get_xlim()[1] - ax.get_xlim()[0] < 0.5 * (xl0[1] - xl0[0]), "扁的框放開只縮 x、y 不動（MATLAB 的約束）")
    pc.restore_view()
    cv.draw()
    root.update()
    ax, cx, cy = center()
    time.sleep(0.6)                                         # 跟上一次放開隔開，不被 Tk 當成雙擊
    drag(cx + 40, cy + 30, cx + 43, cy + 33, mid=grab)
    check(items == [], f"沒拖到 10 px 不畫 ROI（MATLAB 拖滿門檻才出現；{items}）")
    pc.restore_view()
    cv.draw()
    root.update()
    tb._zoom()
    root.update()
    ty = int(cv.get_width_height(physical=True)[1] - ax.bbox.y1) + 4      # 座標區上緣（沒有線：線上的游標是 hover 的 crosshair）
    tb._pan()
    root.update()
    ev("<Motion>", cx + 1, ty)
    root.update()
    check(wd.cget("cursor") == ("openhand" if aqua else "hand2"), f"平移模式的游標＝張開的手（MATLAB 平移模式；{wd.cget('cursor')}）")
    tb._pan()
    root.update()
    ev("<Motion>", cx + 2, ty)
    root.update()
    check(wd.cget("cursor") == "arrow", f"模式關掉 → 箭頭（{wd.cget('cursor')}）")
    pc.restore_view()
    cv.draw()
    root.update()


@step
def s7_datatips_export_fields():
    """批次 B（工具缺口 5）：FigureWindow 的資料提示——匯出（TXT／CSV）、複製 TSV、兩個以上提示的 Δx／Δy、提示內容（存進圖檔、可復原）。"""
    w3 = pk.figure(title="tips")
    pc = w3.pc
    a = pc.plot(np.arange(100.0), np.arange(100.0) * 2, label="ramp")
    b = pc.plot(np.arange(100.0), np.full(100, 7.0), label="flat", yaxis="right")
    pc.canvas.draw()
    t1 = pc.ia.add_tip(a.uid, 10)
    check(pc.v_status.get().startswith("資料提示 #"), "一個提示：狀態列照舊")
    t2 = pc.ia.add_tip(b.uid, 40)
    check(pc.v_status.get() == f"資料提示 #{t2.id} − #{t1.id}：Δx = 30、Δy = -13", f"兩個提示：狀態列 Δx／Δy（{pc.v_status.get()}）")
    pc.ia.select_tip(t1.id)
    check(pc.v_status.get().startswith(f"資料提示 #{t2.id} − #{t1.id}"), "選第一個 → 和下一個比")
    mb = w3.nametowidget(w3["menu"])
    view_menu = None
    for i in range(mb.index("end") + 1):
        if mb.type(i) == "cascade" and mb.entrycget(i, "label") == "檢視":
            view_menu = w3.nametowidget(mb.entrycget(i, "menu"))
    labels = [view_menu.entrycget(i, "label") for i in range(view_menu.index("end") + 1) if view_menu.type(i) == "command"]
    check({"匯出資料提示…", "複製資料提示（TSV）", "提示內容…"} <= set(labels), f"選單 檢視：匯出資料提示…／複製資料提示（TSV）／提示內容…（{labels}）")
    texts = []
    stack = [w3.strip]
    while stack:
        x = stack.pop()
        stack.extend(x.winfo_children())
        if x.winfo_class() == "TButton":
            texts.append(str(x.cget("text")))
    check("匯出提示…" in texts and "提示內容…" in texts, "FIGURE 工具列 檢視：匯出提示…、提示內容…")
    ann = pc.ia.tip_artists[t1.id][0]
    bb = ann.get_bbox_patch().get_window_extent(pc.canvas.get_renderer())
    menus.clear()
    press_release(pc, (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2, button=3)
    check(menus and "匯出資料提示…" in menus[-1] and "提示內容…" in menus[-1], f"提示框右鍵：匯出資料提示…／提示內容…（{menus[-1] if menus else None}）")
    head, rows = pc.ia.tips_table()
    check(rows == [[str(t1.id), "ramp", "左軸", "11", "10", "20"], [str(t2.id), "flat", "右軸", "41", "40", "7"]],
          f"tips_table：訊號、軸、樣本索引（1 起算）、x、y（{rows}）")
    pth = os.path.join(OUT, "tips.txt")
    orig = pk.dialogs.ask_save_path
    pk.dialogs.ask_save_path = lambda *a, **k: pth
    try:
        got = pc.ia.export_tips_dialog()
    finally:
        pk.dialogs.ask_save_path = orig
    lines = open(pth, encoding="utf-8").read().splitlines()
    check(got == pth and lines[0].split("\t")[:2] == ["#", "訊號名稱"] and lines[2].split("\t")[1] == "flat" and "已匯出 2 個" in pc.v_status.get(),
          "匯出資料提示…：TXT（Tab 分隔）")
    check(pc.ia.tips_text().splitlines()[1].split("\t")[1] == "ramp", "複製資料提示的 TSV 內容")
    if os.environ.get("PLOTKIT_TEST_CLIPBOARD") == "1" or clipboard_isolated():   # 安靜模式的剪貼簿在行程裡：不動系統剪貼簿
        txt = pc.ia.copy_tips()
        check(txt is not None and root.clipboard_get() == txt, "複製資料提示（TSV）到剪貼簿")
    n_undo = len(pc.undo_stack)
    dlg = pc.ia.tip_fields_dialog()
    check(dlg.selected() == ("name", "x", "y") and dlg.winfo_exists(), "提示內容…：對話框勾選＝目前的列")
    dlg.vars["index"].set(True); dlg.vars["panel"].set(True)
    dlg.ok(); root.update()
    t_txt = pc.ia.tip_artists[t2.id][0].get_text()
    check(pc.state.tip_fields == ["name", "x", "y", "index", "panel"] and t_txt.endswith("\nIndex 41\nPanel 右軸")
          and len(pc.undo_stack) == n_undo + 1 and "提示內容" in pc.undo_stack.peek_desc(),
          f"確定 → 圖檔的 tip_fields、提示文字跟著換、可復原（{t_txt.splitlines()}）")
    jp = os.path.join(OUT, "tips.json")
    pc.save_json(jp)
    check(pk.load_json(jp).tip_fields == ["name", "x", "y", "index", "panel"], "存成 JSON 再讀：提示內容還在")
    pc.undo(); root.update()
    check(pc.state.tip_fields == ["name", "x", "y"] and "Index" not in pc.ia.tip_artists[t2.id][0].get_text(), "復原 → 回到名稱／X／Y")
    w3.close()


@step
def s20_tools_e_export_zoom_undo():
    """批次 E（工具缺口 2–4）：FigureWindow 的匯出對話框（檔案選單／FIGURE 分頁／工具列存檔鈕、只匯出這個 panel）、
    工具列只有一顆還原視圖＋縮小鈕、平移模式右鍵＝MATLAB 模式選單與方向限制、復原／重做寫動作名稱。"""
    import plotkit.export  # noqa: F401
    w4 = pk.figure(title="export e")
    pc = w4.pc
    pc.plot(np.arange(100.0), np.sin(np.arange(100.0) / 8), label="s")
    pc.plot(np.arange(100.0), np.arange(100.0), label="r", yaxis="right")
    w4.update(); pc.canvas.draw()
    order = toolbar_order(pc.plot_toolbar)
    check(order.count("home") == 1 and "fit" not in order and order[order.index("zoom") + 1] == "zoomout",
          f"工具列：還原視圖只有一顆（Home）、放大後面是縮小（{order}）")
    mb = w4.nametowidget(w4["menu"])
    menus_by = {mb.entrycget(i, "label"): w4.nametowidget(mb.entrycget(i, "menu")) for i in range(mb.index("end") + 1)
                if mb.type(i) == "cascade"}
    fm, em = menus_by["檔案"], menus_by["編輯"]
    flabels = [fm.entrycget(i, "label") for i in range(fm.index("end") + 1) if fm.type(i) == "command"]
    check("存成圖檔…" in flabels and "存成 PNG…" not in flabels, f"檔案選單：存成圖檔…（{flabels}）")
    # 復原／重做
    pc.undo_stack.clear(); pc._update_undo_ui()
    check(em.entrycget(0, "state") == "disabled" and em.entrycget(0, "label") == "復原  (Ctrl+Z)", "編輯選單：沒有可復原的 → 停用")
    pc.set_title("hello"); root.update()
    desc = pc.undo_stack.peek_desc()
    check(em.entrycget(0, "label") == f"復原：{desc}  (Ctrl+Z)" and em.entrycget(0, "state") == "normal"
          and pc.btn_undo._pk_tip == f"復原：{desc} (Ctrl+Z)" and pc._undo_extra and pc._undo_extra[0]._pk_tip == f"復原：{desc} (Ctrl+Z)",
          f"改標題後：編輯選單、工具列與 FIGURE 分頁的復原都寫「復原：{desc}」（{em.entrycget(0, 'label')}）")
    pc.undo(); root.update()
    check(pc.v_status.get() == f"已復原：{desc}" and em.entrycget(1, "label") == f"重做：{desc}  (Ctrl+Y)"
          and pc.btn_redo._pk_tip == f"重做：{desc} (Ctrl+Y)" and em.entrycget(0, "state") == "disabled",
          f"復原後：狀態列、重做寫動作名稱（{pc.v_status.get()}）")
    pc.redo(); root.update()
    check(pc.v_status.get() == f"已重做：{desc}", "重做後：狀態列「已重做：…」")
    # 匯出
    path = os.path.join(OUT, "fig_e.svg")
    asks = []
    orig = pk.export.ask_export_path
    pk.export.ask_export_path = lambda *a, **k: (asks.append(a), path)[1]
    try:
        dlg = pc.savefig_dialog(); root.update()
        exts = [e for e, _d in dlg.formats]
        dlg.v_format.set(dlg._fmt_labels[exts.index("svg")]); dlg._refresh()
        got = dlg.export()
    finally:
        pk.export.ask_export_path = orig
    check(got == path and os.path.getsize(path) > 1000 and open(path, encoding="utf-8").read(200).lstrip().startswith("<?xml")
          and asks[0][2] == "export e.svg" and pc.v_status.get() == f"已存圖 {path}",
          f"存成圖檔…：選 SVG、檔名預設＝視窗標題、存好寫狀態列（{asks[0][2] if asks else None}）")
    pk.export.DEFAULTS.update({"format": "png"})
    d2 = pc.plot_toolbar._save(); root.update()
    check(isinstance(d2, pk.export.ExportDialog), "工具列存檔鈕 → 匯出對話框")
    d2.destroy()
    ax = pc.info.ax_left
    cx, cy = pk.interact.axes_center_px(ax)
    menus.clear()
    press_release(pc, cx, cy, button=3)
    check(menus and "只匯出這個 panel…" in menus[-1], f"圖上右鍵：只匯出這個 panel…（{menus[-1][-4:] if menus else None}）")
    d3 = pc.ia.export_axes_dialog(ax)
    p3 = os.path.join(OUT, "fig_e_panel.png")
    d3.v_dpi.set("60")
    check(d3.export(p3) == p3 and os.path.getsize(p3) > 500 and d3.axes == [ax], "只匯出這個 panel：存得出來")
    # 縮小鈕、平移模式右鍵＝模式選單、方向限制管平移模式拖曳
    pc.restore_view(); w4.update()
    ax = pc.info.ax_left                       # 還原視圖可能重畫（座標區重建）：重新拿
    cx, cy = pk.interact.axes_center_px(ax)
    pc.ia.zoom_step([ax], cx, cy, 2.0)
    xz = ax.get_xlim()
    pc.plot_toolbar.buttons["zoomout"].invoke(); w4.update()
    xo = ax.get_xlim()
    check(abs((xo[1] - xo[0]) / (xz[1] - xz[0]) - 1.5) < 1e-6, f"縮小鈕：以中心縮小 1.5 倍（{xz} → {xo}）")
    nav = pc.toolbar
    pc.plot_toolbar._pan(); w4.update()
    try:
        menus.clear()
        # 空白處右鍵才是模式選單：座標區中心剛好在 r 線（右軸的斜線）上，2026-10-24 起平移模式裡線上右鍵改成線的選單（刪除這條訊號…）
        bb = ax.bbox
        ex, ey = bb.x0 + 0.25 * bb.width, bb.y0 + 0.8 * bb.height          # x≈25：sin≈0.02（在中間）、斜線在 25% 高 → 這點是空白
        pc.ia.on_press(MouseEvent("button_press_event", pc.canvas, ex, ey, button=3))
        pan_menu = menus[-1] if menus else None
        mobj = menu_objs[0] if menu_objs else None
        if mobj is not None:
            mobj.invoke(3)                     # 只平移 x（水平）
        st_after = pc.v_status.get()
        ax = pc.info.ax_left
        y0, x0 = ax.get_ylim(), ax.get_xlim()
        nav.press_pan(MouseEvent("button_press_event", pc.canvas, cx, cy, button=1))
        nav.drag_pan(MouseEvent("motion_notify_event", pc.canvas, cx + 30, cy + 30, button=1, buttons=[1]))
        nav.release_pan(MouseEvent("button_release_event", pc.canvas, cx + 30, cy + 30, button=1))
    finally:
        pc.plot_toolbar._pan(); w4.update()
    check(pan_menu == ["還原視圖", "不限方向平移", "只平移 x（水平）", "只平移 y（垂直）"], f"平移模式右鍵＝MATLAB 模式選單（{pan_menu}）")
    check(nav.zoom_constraint == "x" and ax.get_ylim() == y0 and ax.get_xlim() != x0 and "只水平" in st_after,
          "選「只平移 x」→ 平移模式拖曳只動 x、狀態列說明")
    ax = pc.info.ax_left
    y1 = ax.get_ylim()
    pc.ia.on_scroll(MouseEvent("scroll_event", pc.canvas, cx, cy, step=1))
    check(ax.get_ylim() == y1, "離開平移模式後方向限制仍在：滾輪只縮 x（MATLAB LimitsDimensions 會留著）")
    pc.ia.set_nav_dims("both")
    w4.close()


def s_theme():
    """主題與版面元件：視窗有 toolstrip、工具列包著 matplotlib、預設風格跟主題、切換主題。"""
    import plotkit.theme as T
    th = T.current()
    check(th is not None and th.name in T.TOKENS, "有主題（自己建的根視窗會套 dark）")
    w = pk.figure(title="theme test")
    check(w.state.style == T.plot_style_name() and hasattr(w, "strip") and "figure" in w.strip.tabs, "pk.figure()：風格跟主題、有 FIGURE 工具列")
    pc = w.pc
    check(pc.plot_toolbar is not None and pc.toolbar is pc.plot_toolbar.nav and pc.list_panel.tree.winfo_exists(), "PlotToolbar 包著 NavigationToolbar2Tk、清單面板仍在")
    pc.plot(np.arange(5), np.arange(5) ** 2, label="t")
    tb = pc.plot_toolbar
    tb._pan()
    check(str(pc.toolbar.mode) == "pan/zoom" and tb.v_pan.get(), "工具列平移切換")
    tb._pan()
    check(str(pc.toolbar.mode) == "" and not tb.v_pan.get(), "再按關掉")
    import tkinter.font as tkfont
    pk_fonts = ("PkDefault", "PkBold", "PkSmall", "PkSmallBold", "PkTitle", "PkTitleBold", "PkMono", "PkBig")

    def font_state():
        names = set(tkfont.names(root))
        return (all(n in names for n in pk_fonts) and tkfont.Font(root, font="PkBold").actual("weight") == "bold"
                and tkfont.Font(root, font="PkDefault").actual("weight") == "normal"
                and tkfont.Font(root, font="PkMono").actual("family") != tkfont.Font(root, font="PkDefault").actual("family"))
    f_start = font_state()

    def field_frames(th_):
        """欄位的錯誤狀態（ttk invalid）畫的框：TEntry／TSpinbox／TCombobox 的 layout 用 field 圖片元素；invalid 那張圖的邊框像素≈主題的
        error 色（比 focus、border 色都近）；ttk 取第一個符合的狀態，invalid 要排在 focus 前面（打完字游標還在欄位裡時也紅），disabled 要排在
        invalid 前面（灰掉的欄位還是錯誤狀態時維持灰框，DSV 使用者 2026-10-26 決定；第九輪補：以前對調了也照過）。"""
        st0 = pk.dialogs.ttk.Style(root)
        fname = f"Pk{th_.name.title()}.field"
        specs = th_.element_specs("field")
        states = [s_ for s_, _i in specs]
        img = dict(specs).get(("invalid",))
        near = False
        if img is not None:
            v_ = root.tk.call(str(img), "get", img.width() // 2, 0)
            px_ = tuple(int(c) for c in (v_.split() if isinstance(v_, str) else v_))[:3]
            dist = lambda c: max(abs(a - int(c[1 + 2 * i:3 + 2 * i], 16)) for i, a in enumerate(px_))     # noqa: E731
            near = dist(th_["error"]) <= 24 and dist(th_["error"]) < min(dist(th_["focus"]), dist(th_["border"]))
        return (all(st0.layout(s_)[0][0] == fname for s_ in ("TEntry", "TSpinbox", "TCombobox")), near,
                ("invalid",) in states and ("focus",) in states and states.index(("invalid",)) < states.index(("focus",)),
                ("disabled",) in states and ("invalid",) in states and states.index(("disabled",)) < states.index(("invalid",)))
    fr = {th.name: field_frames(th)}
    other = "light" if th.name == "dark" else "dark"
    T.apply(root, other)
    fr[other] = field_frames(T.current())
    check(T.current().name == other and str(pk.dialogs.ttk.Style(root).theme_use()) == f"plotkit-{other}", "切換主題：ttk 主題跟著換")
    f_switch = font_state()
    T.apply(root, th.name)
    check(T.current().name == th.name, "切回原主題")
    # 1.0.0 外觀主題：八個主題都建得起來、ttk 主題跟著換、圓角各自的值、欄位錯誤狀態照樣紅框、深淺判斷照視窗底色、選單底色照深淺
    fr6 = {}
    for n_ in T.THEMES:
        T.apply(root, n_)
        c_ = T.current()
        fr6[n_] = (c_.name == n_, str(pk.dialogs.ttk.Style(root).theme_use()) == f"plotkit-{n_}", c_.radius == T.RADIUS_PX[n_],
                   field_frames(c_) == (True, True, True, True), c_.dark == T.is_dark(T.TOKENS[n_]["bg"]),
                   c_.menu_bg == (c_["bg2"] if c_.dark else c_["bg3"]), c_.icon_palette(True)["fg"] == c_["strip_text"],
                   c_.icon("home", 16) is not None and c_.icon("home", 16, on_strip=True) is not None)
    T.apply(root, th.name)
    check(len(fr6) == 8 and all(all(v_) for v_ in fr6.values()) and T.current().name == th.name,
          f"八個主題（dark／light／Sony 黑銀／Sony 深藍黑／Apple 淺色／Apple 深色／Apple 深色·石墨橘／Apple 深色·純黑綠）各自建得起來：ttk 主題、圓角、欄位紅框、深淺、選單底、分頁列圖示（{fr6}）")
    import gc
    gc.collect()
    f_back = font_state()
    T.set_ui_font_px(13); T.set_ui_font_px(12)
    w3 = pk.figure(title="font test")
    lb = pk.dialogs.ttk.Label(w3, text="Harmonic Distortion", style="Bold.TLabel")
    ln = pk.dialogs.ttk.Label(w3, text="Harmonic Distortion")
    w3.update_idletasks()
    wider = lb.winfo_reqwidth() > ln.winfo_reqwidth()
    w3.close()
    check(f_start and f_switch and f_back and font_state() and wider,
          f"命名字型 PkDefault／PkBold／PkSmall／PkMono…一直都在（啟動後、切換主題、切回來、gc、改介面字級、開新視窗），PkBold 是粗體、PkMono 是等寬字"
          f"（以前第二次 _make_fonts 換掉物件時舊物件被回收、把 Tk 的命名字型刪掉；{f_start}、{f_switch}、{f_back}、Bold.TLabel 比較寬 {wider}）")
    check(all(v_ == (True, True, True, True) for v_ in fr.values()) and len(fr) == 2,
          f"欄位的錯誤狀態（ttk invalid；MATLAB 欄位的錯誤狀態）在淺色、深色主題都畫紅框：field 圖片元素的 invalid 圖邊框＝error 色，"
          f"而且排在 focus 前面；disabled 排在 invalid 前面（灰掉的欄位還是錯誤狀態時維持灰框）（{fr}）")
    w2 = pk.figure(title="style explicit", style="default")
    check(w2.state.style == "default", "明確給 style 就用它")
    w.close(); w2.close()
    check(w not in pk.windows() and w2 not in pk.windows(), "關閉後登錄清空")


steps.append(s_theme)


def s_theme_skins():
    """1.0.0 深度審查第 1 輪（測試強度、行為 B5）：
    (1) MATLAB 兩個主題（dark／light）和 0.9.14 一模一樣——在獨立行程裡倒出整份快照（ttk 樣式 configure／map／layout、元素圖片怎麼畫、option database、
        選單／tooltip／圖示配色、繪圖風格），和從 20a4492 倒出的金樣 tests/theme_golden_0914.json 比（只容許 6 個新色票鍵）；
    (2) 八個主題「看深淺不看名稱」（is_dark）的分支與 token 化的顏色真的用上了：按下／選中的字色、選單選中字色、tooltip 底、圖示的白、分頁列字色與停用字、
        主要按鈕 hover／按下（含按下那張圖的像素）、contextual 分頁、被選面板工具鈕、分頁列圖示配色；選中與沒選中的分頁底色不同；
    (3) 圓角真的畫進元素圖片（Sony 黑銀 1 < MATLAB／Sony 深藍黑 3 < Apple 5）；(4) 框選放大的框線＝主題的 focus 色；
    (5) 圖片視窗的「繪圖風格」下拉：MATLAB 兩個主題和 0.9.14 一樣三個、寬 11；外觀主題多它自己的風格、放得下（R1）；
        開著的圖換主題、手動選過風格再換主題、圖用的風格不是目前主題的（第 2 輪補）；
    (6) 六個外觀繪圖風格整份和試用版定案的值一樣（tests/plot_styles_100.json，第 2 輪補）；
    (7) 六個外觀主題的介面色票整份和試用版定案的值一樣（tests/theme_tokens_100.json，第 3 輪補）。"""
    import subprocess
    import tkinter.font as tkfont
    import plotkit.theme as T
    ttk_ = pk.dialogs.ttk
    th0 = T.current().name
    # (1) 金樣
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "theme_golden.py"), "compare"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, env=env,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        out_, rc_ = (r.stdout or "") + (r.stderr or "")[-600:], r.returncode
    except Exception as e:
        out_, rc_ = f"{type(e).__name__}: {e}", -1
    gl = [l_ for l_ in out_.splitlines() if l_.startswith("GOLDEN")]
    check(rc_ == 0 and gl and gl[-1].startswith("GOLDEN OK") and "沒比" not in gl[-1],
          f"MATLAB 深色／淺色主題和 0.9.14（20a4492）的金樣完全一樣：ttk 樣式、元素圖片、option database、選單／tooltip／圖示配色、繪圖風格"
          f"（{(gl[-1] if gl else out_[-300:]).strip()}；{' | '.join(l_.strip() for l_ in out_.splitlines() if l_.startswith('  /'))[:400]}）")

    def smap(style, opt):
        return {" ".join(map(str, x_[:-1])): str(x_[-1]) for x_ in ttk_.Style(root).map(style, opt)}

    def scfg(style, opt):
        return str(ttk_.Style(root).configure(style, opt))
    top = pk.dialogs.tk.Toplevel(root)
    top.geometry("420x320")
    lbl = ttk_.Label(top, text="tip")
    lbl.pack()
    root.update()
    bad = {}
    for n_ in T.THEMES:
        th = T.apply(root, n_)
        root.update()
        t_ = th.t
        dark = T.is_dark(t_["bg"])
        w_ = t_["text3"] if dark else t_["text"]
        tip = T.Tooltip(lbl, "x")
        tip._show()
        root.update()
        kids = tip._win.winfo_children() if getattr(tip, "_win", None) else []
        tip_bg = str(kids[0].cget("background")) if kids else None
        tip._hide()
        if T.is_dark(t_["strip"]):
            want_s = {"fg": t_["strip_text"], "fg2": t_["strip_icon_fg2"], "fill": t_["strip_icon_fill"], "accent": t_["strip_text"],
                      "orange": "#ffd19e", "green": "#cbffbe", "red": "#ffcbcb", "white": t_["strip"]}
        else:
            want_s = {"fg": t_["strip_text"], "fg2": t_["strip_icon_fg2"], "fill": t_["strip_icon_fill"], "accent": t_["accent"],
                      "orange": t_["orange"], "green": t_["green"], "red": t_["red"], "white": t_["bg3"]}
        pm = smap("Primary.TButton", "background")
        spec = dict(T._ELEMENT_SPECS.get((th.interp, f"Pk{n_.title()}.primary"), []))
        pim = spec.get(("pressed",))
        pix_ok = False
        if pim is not None:
            g_ = root.tk.call(str(pim), "get", int(pim.width()) // 2, int(pim.height()) // 2)
            rgb = tuple(int(v_) for v_ in (g_ if isinstance(g_, tuple) else str(g_).split()))[:3]
            want = tuple(int(t_["primary_pressed"][i_:i_ + 2], 16) for i_ in (1, 3, 5))
            pix_ok = max(abs(a_ - b_) for a_, b_ in zip(rgb, want)) <= 2
        conds = {
            "TButton 按下字色": smap("TButton", "foreground").get("pressed") == w_,
            "Tool 選中字色": smap("Tool.TButton", "foreground").get("selected") == w_ and smap("Tool.TCheckbutton", "foreground").get("selected") == w_
            and smap("AxesTool.TCheckbutton", "foreground").get("selected") == t_["text"],
            "選單選中字色": th.menu_active_fg == w_ and th.menu_bg == (t_["bg2"] if dark else t_["bg3"]),
            "tooltip 底": tip_bg == (t_["bg2"] if dark else t_["bg3"]),
            "一般圖示的白": th.icon_palette(False)["white"] == ("#f5f5f5" if dark else t_["bg3"]),
            "分頁列圖示配色": th.icon_palette(True) == want_s,
            "Primary 按下／hover／字色": pm.get("pressed") == t_["primary_pressed"] and pm.get("active") == t_["primary_hover"]
            and scfg("Primary.TButton", "foreground") == t_["text3"],
            "Primary 按下的圖": pix_ok,
            "分頁鈕字色／停用字": all(scfg(s_, "foreground") == t_["strip_text"] and smap(s_, "foreground").get("disabled") == t_["strip_text_disabled"]
                              for s_ in ("StripTab.TRadiobutton", "Compact.StripTab.TRadiobutton", "Qab.TButton")),
            "分頁列標籤／捲動鈕字色": scfg("Strip.TLabel", "foreground") == t_["strip_text"] and scfg("StripArrowTab.TButton", "foreground") == t_["strip_text"],
            "contextual 分頁": all(smap(s_, "background").get("active") == t_["primary_hover"] and scfg(s_, "foreground") == t_["text3"]
                                 for s_ in ("Contextual.StripTab.TRadiobutton", "Compact.Contextual.StripTab.TRadiobutton")),
            "被選面板工具鈕 hover": smap("PanelToolSel.TButton", "background").get("active") == t_["primary_hover"],
            "選中的分頁看得出來": all(smap(s_, "background").get("selected") != scfg(s_, "background")
                                for s_ in ("StripTab.TRadiobutton", "Compact.StripTab.TRadiobutton", "Contextual.StripTab.TRadiobutton",
                                           "Compact.Contextual.StripTab.TRadiobutton")),
        }
        if not all(conds.values()):
            bad[n_] = [k_ for k_, v_ in conds.items() if not v_]
    check(not bad, f"八個主題：按下／選中字色、選單、tooltip 底、圖示的白看深淺不看名稱；分頁列字色／停用字、主要按鈕 hover／按下（含圖片像素）、"
                   f"contextual 分頁、被選面板工具鈕用主題自己的 token；選中與沒選中的分頁底色不同（不對的：{bad}）")
    try:
        r2 = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "theme_golden.py"), "radii"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, env=env,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        rad_out, rad_rc = (r2.stdout or "") + (r2.stderr or "")[-400:], r2.returncode
    except Exception as e:
        rad_out, rad_rc = f"{type(e).__name__}: {e}", -1
    rl = [l_ for l_ in rad_out.splitlines() if l_.startswith("RADII")]
    try:
        import json as _json
        rj = _json.loads(rl[-1].split(" ", 2)[2]) if rl else {}
    except Exception:
        rj = {}
    check(rad_rc == 0 and rl and rl[-1].startswith("RADII OK") and rj.get("sony_black", {}).get("mode") == 1 and rj.get("apple_dark", {}).get("mode") == 5
          and rj.get("sony_black", {}).get("fields") == [1] and rj.get("apple_light", {}).get("fields") == [5]
          and rj.get("sony_black", {}).get("all24") == [1] and rj.get("apple_dark", {}).get("all24") == [5]
          and all(v_.get("n24", 0) >= 20 for v_ in rj.values()) and len(rj) == len(T.THEMES),
          f"圓角真的畫進元素圖片：每個主題建按鈕／欄位／分頁圖片時最常用的圓角、欄位（輸入框／下拉）與一般按鈕的每一張圖片，"
          f"以及按鈕大小的每一張元素圖片（主要按鈕、工具鈕、快速存取鈕也算，第 3 輪 N25～N27）都＝RADIUS_PX"
          f"（Sony 黑銀 1、MATLAB／Sony 深藍黑 3、Apple 5；"
          f"{(rl[-1] if rl else rad_out[-300:]).strip()}）")
    # (4) 框選放大的框線
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    fr = ttk_.Frame(top)
    fr.pack(fill="both", expand=True)
    fig = Figure(figsize=(3, 2))
    fig.add_subplot(111)
    cv = FigureCanvasTkAgg(fig, master=fr)
    cv.get_tk_widget().pack(fill="both", expand=True)
    nav = T.make_nav(cv, fr)
    root.update()
    roi = {}
    for n_ in ("dark", "light", "sony_black", "apple_light", "apple_dark_black"):
        T.apply(root, n_)
        root.update()
        nav.draw_roi(10, 10, 120, 90)
        tkc = cv.get_tk_widget()
        roi[n_] = sorted({tkc.itemcget(i_, "outline" if tkc.type(i_) == "rectangle" else "fill") for i_ in nav._roi_ids})
        nav.remove_rubberband()
    check(roi == {n_: [T.TOKENS[n_]["focus"]] for n_ in roi} and roi["dark"] == roi["light"] == ["#268cdd"],
          f"框選放大的框線＝主題的 focus 色（MATLAB 兩個主題 #268cdd 照舊；{roi}）")
    top.destroy()
    # (5) 圖片視窗的繪圖風格下拉
    got = {}
    for n_ in ("dark", "light", "sony_black", "apple_dark_graphite"):
        T.apply(root, n_)
        root.update()
        wf = pk.figure(title=f"style combo {n_}")
        root.update()
        cb = getattr(wf.pc, "style_combo", None)
        vals = tuple(cb.cget("values")) if cb is not None else ()
        f_ = tkfont.nametofont(str(cb.cget("font")) or "TkTextFont") if cb is not None else None
        fits = cb is not None and int(cb.cget("width")) * f_.measure("0") >= max(f_.measure(v_) for v_ in vals)
        got[n_] = (vals, int(cb.cget("width")) if cb is not None else None, fits)
        wf.close()
    base3 = ("default", "matlab", "matlab-dark")
    check(got["dark"][:2] == (base3, 11) and got["light"][:2] == (base3, 11)
          and got["sony_black"][0] == base3 + ("sony-black",) and got["apple_dark_graphite"][0] == base3 + ("apple-dark-graphite",)
          and got["sony_black"][2] and got["apple_dark_graphite"][2],
          f"圖片視窗「繪圖風格」下拉：深色／淺色主題和 0.9.14 一樣三個、寬 11；外觀主題多它自己的風格、放得下最長的名稱（{got}）")

    # (5b) 1.0.0 第 2 輪（測試強度：突變 N12～N16 存活）：R1 決定的其他情況——「目前主題的風格」和「這張圖的風格」不同時、開著的圖換主題時
    def _cb_state(cb_):
        vals_ = tuple(cb_.cget("values"))
        f2_ = tkfont.nametofont(str(cb_.cget("font")) or "TkTextFont")
        return vals_, int(cb_.cget("width")), int(cb_.cget("width")) * f2_.measure("0") >= max(f2_.measure(v_) for v_ in vals_ + (cb_.get(),))

    def _post(cb_):                                      # 打開下拉前 Tk 會跑的 postcommand（不真的打開，免得跳出清單）
        pc_ = str(cb_.cget("postcommand"))
        if pc_:
            root.tk.eval(pc_)
    r1 = {}
    T.apply(root, "dark")
    root.update()
    wf = pk.figure(title="style combo P1")
    root.update()
    cb = wf.pc.style_combo
    T.apply(root, "apple_dark_graphite")                  # P1：開著的圖（風格跟著主題）換主題：不打開下拉，選項與寬度就跟著（redraw 時更新）
    root.update()
    v1 = _cb_state(cb)
    r1["P1 開著的圖換到石墨橘"] = (wf.pc.v_style.get() == "apple-dark-graphite" and v1[0] == base3 + ("apple-dark-graphite",) and v1[2],
                              (wf.pc.v_style.get(),) + v1)
    wf.pc.set_style("matlab")                            # P2：這張圖自己選了 matlab，再換主題：打開下拉（postcommand）時多新主題的風格
    root.update()
    T.apply(root, "sony_black")
    root.update()
    _post(cb)
    v2 = _cb_state(cb)
    r1["P2 選 matlab 後換 Sony 黑銀再打開下拉"] = (wf.pc.v_style.get() == "matlab" and v2[0] == base3 + ("sony-black",), (wf.pc.v_style.get(),) + v2)
    wf.close()
    root.update()
    T.apply(root, "dark")                                 # P3：深色主題、圖用 apple-light：多這張圖自己的風格、放得下
    root.update()
    wf = pk.figure(title="style combo P3", style="apple-light")
    root.update()
    _post(wf.pc.style_combo)
    v3 = _cb_state(wf.pc.style_combo)
    r1["P3 深色主題、圖用 apple-light"] = (v3[0] == base3 + ("apple-light",) and v3[2], v3)
    wf.close()
    root.update()
    T.apply(root, "sony_black")                           # P4：Sony 黑銀主題、圖用 matlab：選得回主題自己的 sony-black
    root.update()
    wf = pk.figure(title="style combo P4", style="matlab")
    root.update()
    _post(wf.pc.style_combo)
    v4 = _cb_state(wf.pc.style_combo)
    r1["P4 Sony 黑銀主題、圖用 matlab"] = (v4[0] == base3 + ("sony-black",), v4)
    wf.close()
    root.update()
    check(all(ok_ for ok_, _ in r1.values()),
          f"圖片視窗「繪圖風格」下拉（R1）：開著的圖換主題後選項與寬度跟著、手動選過風格再換主題時打開下拉多新主題的風格、"
          f"圖用的風格不是主題的也列得出來（不對的：{ {k_: i_ for k_, (ok_, i_) in r1.items() if not ok_} }）")
    # (6) 1.0.0 第 2 輪（測試強度 S03～S06 存活）：六個外觀繪圖風格整份＝tests/plot_styles_100.json（使用者 2026-11-01 看過的試用版 918268c 的數值）
    import json as _json
    import plotkit.styles as _S
    gold_ = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "plot_styles_100.json"), encoding="utf-8"))["styles"]
    diff_ = {n_: sorted(k_ for k_ in set(g_) | set(_S.STYLES.get(n_, {}))
                        if _json.loads(_json.dumps(_S.STYLES.get(n_, {}).get(k_), default=str)) != g_.get(k_))
             for n_, g_ in gold_.items()}
    diff_ = {n_: v_ for n_, v_ in diff_.items() if v_}
    check(len(gold_) == 6 and not diff_, f"六個外觀繪圖風格（sony-black／sony-blue／apple-light／apple-dark／apple-dark-graphite／apple-dark-black）"
                                         f"每個鍵都和試用版定案的值一樣（不一樣的鍵：{diff_}）")
    # (7) 1.0.0 第 3 輪（測試強度 K01～K06 存活）：六個外觀主題的介面色票整份＝tests/theme_tokens_100.json（使用者 2026-11-01 看過的試用版 918268c 的值
    # ＋決定過的兩處：apple_light text2〔21:1x B4〕、apple_dark_black strip〔21:4x W100R1-1〕）。逐鍵比主題自己的值——不是「apple_dark＋覆蓋值」，
    # 所以 apple_dark 改了，兩個 Apple 深色變體也抓得到
    tgold_ = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "theme_tokens_100.json"), encoding="utf-8"))["tokens"]
    tdiff_ = {n_: sorted(k_ for k_ in set(g_) | set(T.TOKENS.get(n_, {})) if T.TOKENS.get(n_, {}).get(k_) != g_.get(k_)) for n_, g_ in tgold_.items()}
    tdiff_ = {n_: v_ for n_, v_ in tdiff_.items() if v_}
    check(sorted(tgold_) == sorted(n_ for n_ in T.THEMES if n_ not in ("dark", "light")) and all(len(g_) >= 45 for g_ in tgold_.values()) and not tdiff_,
          f"六個外觀主題（Sony 黑銀／深藍黑、Apple 淺色／深色／石墨橘／純黑綠）的介面色票每個鍵都和試用版定案的值一樣"
          f"（不一樣的鍵：{tdiff_}）")
    T.apply(root, th0)
    root.update()
    check(T.current().name == th0, f"還原主題 {th0}")


steps.append(s_theme_skins)


def s_tooltip_destroy():
    """Tooltip：滑鼠停在元件上（600 ms 後才顯示提示）就把視窗關掉——元件的 <Destroy> 先取消排著的顯示；以前時間到時找不到已刪掉的
    「…_show」Tcl 指令，跳 Tk 的背景錯誤對話框。"""
    import plotkit.theme as T
    root.tk.eval("set ::pk_tt_bg {}; proc ::pk_tt_bgrec {msg opts} {lappend ::pk_tt_bg $msg}")
    old_h = root.tk.call("interp", "bgerror", "")
    root.tk.call("interp", "bgerror", "", "::pk_tt_bgrec")
    try:
        top = pk.dialogs.tk.Toplevel(root)
        ent = pk.dialogs.ttk.Entry(top)
        ent.pack()
        tip = T.tooltip(ent, "tip")
        root.update()
        tip._enter()                                       # ＝滑鼠進到元件上
        pending = tip._job is not None
        top.destroy()
        root.update(); time.sleep(tip.delay / 1000.0 + 0.15); root.update()
        bg = str(root.tk.eval("set ::pk_tt_bg"))
    finally:
        root.tk.call("interp", "bgerror", "", old_h)
    check(pending and tip._job is None and bg == "",
          f"提示排著（滑鼠剛停到元件上）就關視窗：<Destroy> 取消排著的顯示，時間到時不跳 Tk 的背景錯誤（{pending}、{bg[:80]!r}）")


steps.append(s_tooltip_destroy)


def s_hover_destroy():
    """暫時資料提示（hover）：游標停在線上，200 ms 後才出現提示框——計時器排著時就關視窗（⌘W／關閉鈕），Interactor 在畫布的 close_event
    停掉計時器；以前時間到時找不到已刪掉的「…_on_timer」Tcl 指令，跳 Tk 的背景錯誤對話框。"""
    root.tk.eval("set ::pk_hv_bg {}; proc ::pk_hv_bgrec {msg opts} {lappend ::pk_hv_bg $msg}")
    old_h = root.tk.call("interp", "bgerror", "")
    root.tk.call("interp", "bgerror", "", "::pk_hv_bgrec")
    pending, after, bg = False, None, "?"
    try:
        wh = pk.figure(title="hover close")
        sh = wh.plot(np.arange(100.0), np.sin(np.arange(100) / 10.0), label="h")
        pc = wh.pc
        pc.v_tips.set(True); pc._on_tips_toggle()
        wh.update(); pc.canvas.draw(); wh.update()
        ax = pc.info.ax_left
        ln = pc.info.lines[sh.uid]
        hx, hy = ax.transData.transform((ln.get_xdata()[40], ln.get_ydata()[40]))
        pc.ia.on_motion(MouseEvent("motion_notify_event", pc.canvas, hx, hy))
        pending = pc.ia._hover_timer is not None and pc.ia.hover_tip is not None
        wh.close()
        root.update(); time.sleep(0.35); root.update()
        after = pc.ia._hover_timer
        bg = str(root.tk.eval("set ::pk_hv_bg"))
    finally:
        root.tk.call("interp", "bgerror", "", old_h)
    check(pending and after is None and bg == "",
          f"游標停在線上（暫時提示框的 200 ms 計時器排著）就關視窗：Interactor 在畫布的 close_event 停掉計時器，時間到時不跳 Tk 的背景錯誤"
          f"（{pending}、{after}、{bg[:80]!r}）")


steps.append(s_hover_destroy)


def s_lim_bus_series():
    """限制修正：Series.disp="digital"（DSV 數位匯流排複製過來）在圖片視窗畫成匯流排框：點框內選取、提示釘在框中心且用進位制、
    貼上／複製到新視窗／undo／存檔保留。"""
    from matplotlib.backend_bases import MouseEvent
    yv = np.repeat([0x12, 0xAB, 0x03], 20).astype(float)
    sb = pk.Series("bus8", np.arange(61) * 2.0, yv, kind="step", disp="digital", radix="hex", bits=8)
    wb = pk.figure(title="bus test")
    try:
        pc = wb.pc
        pc.paste([sb])
        wb.update()
        pc.canvas.draw()
        s = pc.state.series[0]
        b = pc.info.bus.get(s.uid)
        labs = [t for _x, t in b["art"].labels()] if b else []
        check(s.is_bus and b is not None and labs == ["12", "AB", "03"] and len(pc.info.ax_left.get_yticks()) == 0,
              f"貼上匯流排 Series → 畫成框＋hex 數值、只有匯流排的軸不畫 y 刻度（{labs}）")
        pc.select(set())
        ax = pc.info.ax_left
        px, py = ax.transData.transform((50.0, b["center"] - 0.25))       # 框內、靠下緣（不在上緣那條線上）
        press_release(pc, px, py, modifiers={"shift"})
        check(pc.selected == {s.uid} and not pc.state.tips, f"Shift＋點匯流排框內（不在上緣線上）→ 選取（{pc.selected}）")
        tip = pc.ia.add_tip(s.uid, 25)
        wb.update()
        ann = pc.ia.tip_artists[tip.id][0]
        check(abs(ann.xy[1] - b["center"]) < 1e-9 and ann.get_text().endswith("Y 0xAB"),
              f"資料提示釘在框中心、Y 用進位制（{ann.get_text().splitlines()[-1]}）")
        snap_n = len(pc.undo_stack)
        p = os.path.join(tempfile.mkdtemp(prefix="pk_bus_"), "bus.json")
        pc.save_json(p)
        st = pk.load_json(p)
        check(st.series[0].disp == "digital" and st.series[0].radix == "hex" and st.series[0].bits == 8 and len(pc.undo_stack) == snap_n,
              "存成圖檔 JSON → 讀回來仍是匯流排（hex、8 位元）")
        pc.select({s.uid})
        w2 = pc.copy_to_new_window()
        wb.update()
        ok2 = w2 is not None and w2.pc.state.series and w2.pc.state.series[0].is_bus and w2.pc.state.series[0].uid in w2.pc.info.bus
        check(bool(ok2), "圖片視窗「複製到新視窗」：匯流排設定跟著")
        if w2 is not None:
            w2.close()
    finally:
        wb.close()


steps.append(s_lim_bus_series)


# ---------------------------------------------------------------------------------------------------------------------
# 0.9.14 Windows 高 DPI（W10）：窄視窗的工具列與欄位列（agent W；這一段只加不改）
# ---------------------------------------------------------------------------------------------------------------------
@step
def s98_w10_narrow_layout():
    """0.9.14 W10（2026-10-29 使用者決定 Windows 高 DPI 支援）：視窗比工具列窄時（175% 的直立 1080 px 螢幕只有 617 點寬）——
    分頁鈕放不下改窄分頁鈕、還放不下分頁列左右捲動（選到的分頁捲進來）；分頁內容比工具列寬時兩端 ◀ ▶ 捲動（滾輪也可以）；
    欄位列（flow_row）放不下就換行、放得下就照原本的 pack 排回去。macOS 不開（NARROW_LAYOUT 關、window_size 原樣回傳——
    Mac 不受影響）；這裡暫時打開它驗邏輯，結束時還原。寬度都照量到的需求算（DPI 不同時一樣成立）；工具列和欄位列放在
    指定寬度的容器裡（place），不受螢幕寬度限制。"""
    T = pk.theme
    orig = T.NARROW_LAYOUT
    if sys.platform == "darwin":
        check(orig is False and T.window_size(root, 1120, 760) == (1120, 760) and T.flow_row(None) is None,
              f"macOS：NARROW_LAYOUT 關（{orig}）、新視窗起始大小照舊（{T.window_size(root, 1120, 760)}）——Mac 不受影響")
    else:
        check(orig is (sys.platform.startswith("win")), f"NARROW_LAYOUT 只在 Windows 開（{sys.platform}：{orig}）")
    T.NARROW_LAYOUT = True
    top = pk.dialogs.tk.Toplevel(root)
    try:
        top.geometry("600x400")
        holder = pk.dialogs.ttk.Frame(top, width=100, height=300)
        holder.pack_propagate(False)
        holder.place(x=0, y=0)
        strip = T.Toolstrip(holder)
        strip.pack(side="top", fill="x")
        keys = []
        for i in range(8):
            tab = strip.add_tab(f"分頁{i + 1}", key=f"t{i}")
            keys.append(f"t{i}")
            for j in range(9 if i in (1, 5) else 2):
                sec = tab.section(f"區段{j}")
                sec.button(f"很長的按鈕文字 {i}-{j}", big=True)
        holder2 = pk.dialogs.ttk.Frame(top, width=100, height=200)
        holder2.pack_propagate(False)
        holder2.place(x=0, y=300)
        rowf = pk.dialogs.ttk.Frame(holder2)
        rowf.pack(side="top", fill="x")
        kids = []
        for j in range(7):
            b = pk.dialogs.ttk.Button(rowf, text=f"欄位按鈕 {j}")
            b.pack(side="left", padx=(8, 2) if j else 0)
            kids.append(b)
        fr = T.flow_row(rowf)
        top.update()

        def set_w(w_):
            holder.configure(width=int(w_))
            holder2.configure(width=int(w_))
            for _ in range(6):
                top.update()
        th = strip.th
        qab_w = strip.qab.winfo_reqwidth() + th.px(6)
        row_need = sum(b.winfo_reqwidth() for b in strip._buttons.values()) + qab_w
        w_wide = max([row_need] + [t.winfo_reqwidth() for t in strip.tabs.values()] + [rowf.winfo_reqwidth()]) + th.px(40)
        set_w(w_wide)
        packed_x = [c.winfo_x() for c in kids]
        wide = strip.narrow_state()
        need1 = strip.tabs["t1"].winfo_reqwidth()
        check(not wide["compact"] and not wide["tab_scroll"] and not wide["body_scroll"] and fr is not None and not fr.wrapped
              and [c.winfo_manager() for c in kids] == ["pack"] * 7,
              f"放得下（{w_wide} px）：和以前一樣（原本的分頁鈕、不捲動、欄位一排 pack）：{wide}")
        w_mid = int(row_need * 0.8)
        set_w(w_mid)
        st = strip.narrow_state()
        styles = {str(b.cget("style")) for b in strip._buttons.values()}
        check(st["compact"] and styles == {"Compact.StripTab.TRadiobutton"} and w_mid < need1,
              f"窄（{w_mid} px＜分頁鈕原本要的 {row_need}）：分頁鈕改窄的（{st}、{styles}）")
        strip.select("t1")
        top.update()
        st = strip.narrow_state()
        arr = strip._nw["arrows"]
        check(st["body_scroll"] and strip.tabs["t1"].winfo_manager() == "place" and arr["body_l"].winfo_manager() == "place"
              and arr["body_r"].winfo_manager() == "place" and str(arr["body_l"].cget("state")) == "disabled"
              and str(arr["body_r"].cget("state")) == "normal",
              f"分頁內容（{need1} px）比工具列寬：內容改成可捲動、兩端 ◀ ▶，最左邊時 ◀ 停用（{st}）")
        strip._narrow_scroll("body", 1)
        o1 = strip.narrow_state()["body_off"]
        for _ in range(60):
            strip._narrow_scroll("body", 1)
        top.update()
        o2 = strip.narrow_state()["body_off"]
        a = th.px(18)
        W = strip.winfo_width()
        x_end = strip.tabs["t1"].winfo_x() + need1
        check(0 < o1 < o2 and o2 == need1 - W + 2 * a and str(arr["body_r"].cget("state")) == "disabled"
              and str(arr["body_l"].cget("state")) == "normal" and x_end <= W - a,
              f"▶ 一次捲六成寬（{o1}）、捲到底停在最後一個區段整個露出來（{o2}＝{need1}−{W}+2×{a}；右緣 {x_end} ≤ {W - a}）、▶ 停用")
        ev = SimpleNamespace(delta=120)
        strip._narrow_wheel(ev)
        o3 = strip.narrow_state()["body_off"]
        check(o3 == o2 - th.px(60), f"滾輪往上＝往左捲 {th.px(60)} px（{o2} → {o3}）")
        strip.select("t0")
        top.update()
        st0 = strip.narrow_state()
        check(st0["body_off"] == 0 and strip.tabs["t1"].winfo_manager() == "", f"換分頁：上一個分頁收起來、新分頁從最左邊開始（{st0}）")
        line1 = [c for c in kids if c.winfo_y() == kids[0].winfo_y()]
        check(fr.wrapped and fr.lines >= 2 and all(c.winfo_manager() == "place" for c in kids)
              and all(c.winfo_x() + c.winfo_width() <= rowf.winfo_width() for c in kids)
              and 2 <= len(line1) < len(kids) and [c.winfo_x() for c in line1] == packed_x[:len(line1)],
              f"欄位列放不下：換成 {fr.lines} 行、每個欄位都在列的寬度裡、第一行的位置和間距和 pack 時一樣（{[c.winfo_x() for c in line1]}"
              f"＝{packed_x[:len(line1)]}；寬 {rowf.winfo_width()}）")
        compact_need = sum(b.winfo_reqwidth() for b in strip._buttons.values()) + qab_w
        w_narrow = max(qab_w + 4 * a, int(compact_need * 0.6))
        set_w(w_narrow)
        strip.select("t7")
        top.update()
        st7 = strip.narrow_state()
        b7 = strip._buttons["t7"]
        avail = strip.winfo_width() - qab_w
        left = strip._tabrow.winfo_x() + b7.winfo_x()
        check(st7["tab_scroll"] and st7["tab_off"] > 0 and a <= left and left + b7.winfo_width() <= avail - a
              and arr["tab_l"].winfo_manager() == "place" and arr["tab_r"].winfo_manager() == "place",
              f"更窄（{w_narrow} px＜窄分頁鈕要的 {compact_need}）：分頁列可捲動、選到最後一個分頁時它整個捲進來（左緣 {left}、寬 {b7.winfo_width()}、"
              f"可見 {a}～{avail - a}；{st7}）")
        set_w(w_wide)
        back = strip.narrow_state()
        styles = {str(b.cget("style")) for b in strip._buttons.values()}
        check(not back["compact"] and not back["tab_scroll"] and not back["body_scroll"] and styles == {"StripTab.TRadiobutton"}
              and strip._tabrow.winfo_manager() == "pack" and strip.tabs["t7"].winfo_manager() == "pack"
              and all(b.winfo_manager() == "" for b in arr.values()),
              f"再放寬（{w_wide} px）：全部恢復原狀（原本的分頁鈕、分頁列與內容都是 pack、捲動鈕收起來）：{back}")
        check(not fr.wrapped and [c.winfo_manager() for c in kids] == ["pack"] * 7 and list(rowf.pack_slaves()) == kids
              and [c.winfo_x() for c in kids] == packed_x,
              "欄位列放得下：照原本的 pack 選項與順序排回去（位置和一開始一樣）")
        ww, hh = T.window_size(top, 100, 80)
        check((ww, hh) == (th.px(100), th.px(80)), f"window_size：照介面倍數放大（{(ww, hh)}＝px(100)、px(80)）")
        l_, t_, r_, b_ = T.work_area(top)
        big = T.window_size(top, 100000, 100000)
        check(big == (int((r_ - l_) * 0.95), int((b_ - t_) * 0.9)), f"window_size：不超過工作區的 95%／90%（{big}，工作區 {(l_, t_, r_, b_)}）")
        # T14-8 (b)（0.9.14 第一輪測試強度，突變 D08）：Mac 的介面倍數永遠是 1、PC 平常 100%——「照 DPI 放大」在那兩種設定下分不出來；
        # 暫時把介面倍數設成 1.75（模擬 175%），分析視窗起始大小要跟著放大（不超過工作區）
        cur_ = T.current()
        sc0_ = cur_._scale
        try:
            cur_._scale = 1.75
            w175 = T.window_size(top, 100, 80)
        finally:
            cur_._scale = sc0_
        check(w175 == (min(175, int((r_ - l_) * 0.95)), min(140, int((b_ - t_) * 0.9))),
              f"window_size：介面倍數 1.75（模擬 175%）時照倍數放大（{w175}；突變 D08 不放大）")
        # Dock：右欄第一次出現（DSV 的資料游標讀數）時 ttk 照 reqwidth 重排，窄視窗（PC 175% 直立）左欄拿走幾乎全部、中欄（圖）剩 0 被 unmap
        # ——中欄至少留 Dock 寬的 45%（_keep_center_room），左右欄照它們要的寬度比例分剩下的；關掉右欄的面板照舊
        holder3 = pk.dialogs.ttk.Frame(top, width=th.px(560), height=th.px(300))
        holder3.pack_propagate(False)
        holder3.place(x=0, y=0)
        dk = T.Dock(holder3)
        dk.pack(fill="both", expand=True)
        pans = {}
        for key, col, wt, hid, wreq in (("folder", "left", 1, False, 300), ("plot", "center", 1, False, 120),
                                        ("cursors", "right", 1, True, 220)):
            pn = T.Panel(dk, key)
            pk.dialogs.ttk.Frame(pn.body, width=th.px(wreq), height=th.px(60)).pack()
            dk.add(key, pn, col, weight=wt, fixed=(key == "plot"), hidden=hid)
            pans[key] = pn
        top.update()
        def col_w():
            vis = dk.visible_columns(); W_ = dk.h.winfo_width()
            e_ = [0] + [int(dk.h.sashpos(i)) for i in range(len(vis) - 1)] + [W_]
            return {c: e_[i + 1] - e_[i] for i, c in enumerate(vis)}, W_
        w0, W0 = col_w()
        dk.hide("cursors", False); top.update()
        w1, W1 = col_w()
        dk.hide("cursors", True); top.update()
        w2, _W2 = col_w()
        check(set(w1) == {"left", "center", "right"} and w1["center"] >= int(W1 * 0.45) - 2 and pans["plot"].winfo_ismapped()
              and w1["left"] > 0 and w1["right"] > 0 and set(w2) == {"left", "center"} and pans["plot"].winfo_ismapped(),
              f"Dock（窄）：右欄的面板出現時中欄（圖）至少留 45%、還看得到（{w0} → {w1}，Dock 寬 {W1}）；關掉右欄後照舊兩欄（{w2}）")
        holder3.destroy()
    finally:
        T.NARROW_LAYOUT = orig
        top.destroy()
        root.update()


@step
def s99_popup_menus_released():
    """0.9.13 W1（Windows 相容性）：plotkit 的三個彈出站點——線條／空白右鍵（widgets 的選單）、放大模式與平移模式選單（interact）——彈出之後銷毀：
    POPUP_MENU_RELEASE_MS 設 1 ms，事件迴圈跑過後彈過的選單都不在了、活著的 tk.Menu 數回到彈出前；None（測試模式）時留著（0.9.12 的行為）。"""
    pc = w.pc
    pc.canvas.draw()
    pc.select(set())
    ax = pc.info.ax_left
    ln = pc.info.lines[sI.uid]
    xd, yd = ln.get_xdata(), ln.get_ydata()
    px, py = ax.transData.transform((xd[300], yd[300]))
    popped = []
    orig = pk.dialogs.tk.Menu.tk_popup

    def rec(self, x, y, entry=None):
        popped.append(self)
    pk.dialogs.tk.Menu.tk_popup = rec
    pk.menus.POPUP_MENU_RELEASE_MS = 1
    n_base = pk.menus.live_menus(w)
    alive, kept, immediate, n_mid, n_after, n_first = ["?"], False, False, -1, -1, -1
    try:
        press_release(pc, px, py, button=3)                      # 線條右鍵（widgets）
        cx, cy = pk.interact.axes_center_px(ax)
        pc.ia.zoom_mode_context(MouseEvent("button_press_event", pc.canvas, cx, cy, button=3))
        pc.ia.pan_mode_context(MouseEvent("button_press_event", pc.canvas, cx, cy, button=3))
        n_mid = pk.menus.live_menus(w)
        n_first = len(popped)
        t0 = time.time()
        while time.time() - t0 < 3.0 and any(m.winfo_exists() for m in popped):
            w.update()
            time.sleep(0.01)
        alive = [m for m in popped if m.winfo_exists()]
        n_after = pk.menus.live_menus(w)
        pk.menus.POPUP_MENU_RELEASE_MS = 10000                   # 上一個在下一次彈出時就銷毀（不等計時器）
        press_release(pc, px, py, button=3)
        press_release(pc, px, py, button=3)
        immediate = len(popped) == 5 and not popped[3].winfo_exists() and popped[4].winfo_exists()
        pk.menus.release_recent()
        immediate = immediate and not popped[4].winfo_exists()
        pk.menus.POPUP_MENU_RELEASE_MS = None
        press_release(pc, px, py, button=3)
        w.update(); time.sleep(0.03); w.update()
        kept = len(popped) == 6 and popped[-1].winfo_exists()
        try:
            popped[-1].destroy()
        except Exception:
            pass
    finally:
        pk.menus.POPUP_MENU_RELEASE_MS = None
        pk.dialogs.tk.Menu.tk_popup = orig
        pc.select(set())
    check(n_first == 3 and not alive and n_mid > n_base and n_after <= n_base,
          f"W1 plotkit 三個站點彈出後都銷毀（彈 {n_first} 次、還活著 {len(alive)}；tk.Menu {n_base} → {n_mid} → {n_after}）")
    check(immediate, "W1 plotkit：連續右鍵時上一個選單在下一次彈出時就銷毀、release_recent() 銷毀最後一個")
    check(kept, "W1 plotkit：POPUP_MENU_RELEASE_MS＝None 時留著（0.9.12 的行為）")


def run(i=0):
    if i >= len(steps):
        import tests_common as _tc
        _qp = _tc.quiet_problems()               # 安靜模式（2026-10-26 使用者回報點不動自己的 DSV；第二輪：沒預期的擋下、啟用、剪貼簿）
        check(not _qp, f"安靜模式：跑完全部步驟沒有沒換掉的原生對話框、沒預期的選單彈出，還是 Prohibited、剪貼簿在行程裡，"
                       f"看得見的視窗都點不到、alpha 0、不在選單層，擋板都在（{_qp[:3]}）")
        _DONE[0] = True
        w.close()
        root.after(100, root.quit)
        return
    _PROG.begin(i)
    try:
        steps[i]()
    except Exception:
        traceback.print_exc()
        check(False, f"步驟 {steps[i].__name__} 例外")
    _PROG.end(i)
    root.after(200, lambda: run(i + 1))


def _overall_timeout():
    """整套的時限到了還沒跑完：以前只印一行、默默結束事件迴圈——沒跑到的步驟的檢查項目就少了，套件照樣「全部通過」。
    現在記成一項沒過、寫出停在哪一步與沒跑完的步驟（0.9.14 R3C-6）。"""
    if _DONE[0]:
        return
    print(_PROG.report("WATCHDOG：整套超過 150 秒"), flush=True)
    check(False, "WATCHDOG：整套超過 150 秒還沒跑完（沒跑到的步驟見上面那段）")
    root.quit()


import tests_common as _tcp                     # noqa: E402
_DONE = [False]
_PROG = _tcp.StepProgress([fn.__name__ for fn in steps], results, env_name=None)
_tcp.install_term_report(_PROG)                 # timeout 的 SIGTERM：寫出停在哪一步再結束（不經過 Tk 的訊號處理，不死鎖）
_WATCH = _tcp.install_stall_watchdog(_PROG, 60.0)   # 60 秒都沒有進度（新的一步、新的檢查項目）＝卡住：寫出位置、乾淨地結束
root.after(500, run)
root.after(150000, _overall_timeout)
root.mainloop()
_WATCH.set()
# 每一步都跑到了、整套跑到最後：某一步結束事件迴圈（root.quit）或關掉視窗時，後面的步驟默默不跑、結果照樣「全部通過」（第二輪測試強度驗證 3：
# plotkit GUI 與 i18n 兩套以前沒有這個總檢查；DSV GUI 在 T14-7 加過）
_ran = {n_ for n_, _t, _k in _PROG.times}
_miss = [fn.__name__ for fn in steps if fn.__name__ not in _ran]
check(_DONE[0] and not _miss, f"這次要跑的 {len(steps)} 步每一步都跑到了、整套跑到最後（沒有哪一步提早結束事件迴圈）：沒跑到 {len(_miss)} 步 {_miss[:6]}；跑到最後 {_DONE[0]}")
bad = [m for ok, m in results if not ok]
print(_PROG.summary())
print(f"\nPLOTKIT GUI TEST: {len(results) - len(bad)}/{len(results)} 通過")
sys.exit(1 if bad else 0)
