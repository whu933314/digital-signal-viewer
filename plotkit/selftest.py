# -*- coding: utf-8 -*-
"""plotkit.selftest — 不開 GUI 的核心檢查（Agg）。全部通過印 SELFTEST OK。"""
from __future__ import annotations

import io
import json
import math
import re
import os
import subprocess
import sys
import tempfile
import types
import time
from typing import List

import numpy as np
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from . import clipboard, draw, model, styles, undo
from .interact import DRAG_THRESHOLD_PX, Hit, Interactor, InteractorHost, InteractorModel
from .model import Annotation, DataTip, FigureState, Series


class _RecHost(InteractorHost):
    """把 draw_state 的結果提供給 Interactor，並記錄所有回呼。"""

    def __init__(self, state: FigureState, fig):
        self.state = state
        self.fig = fig
        self.info = draw.draw_state(fig, state)
        self.calls: List[tuple] = []
        self.restore_handled = False

    def redraw(self):
        self.info = draw.draw_state(self.fig, self.state)

    def style(self):
        return styles.get_style(self.state.style)

    def lines_in(self, ax):
        return [(uid, ln) for uid, ln in self.info.lines.items() if ln.axes is ax]

    def series_data(self, uid):
        s = self.state.find(uid)
        if s is None or not s.visible:
            return None
        return s.x[:s.n] + s.xshift, s.y + s.yshift, s.label, self.info.axes_for(s.yaxis)

    def axes_for_key(self, key):
        return self.info.axes_for("right" if key == "right" else "left")

    def axes_key_for(self, ax):
        return self.info.key_for(ax)

    def legend_entries(self, ax):
        return list(self.info.legend_uids)

    def on_restore_view(self):
        self.calls.append(("restore",))
        return self.restore_handled

    def on_pick(self, uid, event, hit):
        self.calls.append(("pick", uid, hit.index))

    def on_click_empty(self, event):
        self.calls.append(("empty",))

    def on_context(self, hit, event):
        self.calls.append(("context", hit.kind, hit.id))

    def on_rename(self, uid, label):
        self.calls.append(("rename", uid, label))

    def before_model_change(self, what, tag=None):
        self.calls.append(("before", what, tag))

    def on_model_change(self, what):
        self.calls.append(("after", what))

    def on_view_change(self, ax):
        self.calls.append(("view",))

    def on_delete_key(self):
        self.calls.append(("delete_key",))

    def on_legend_move(self, ax, loc):
        self.calls.append(("legend_move", tuple(loc)))

    def on_legend_loc(self, ax, loc):
        self.calls.append(("legend_loc", loc))

    def on_legend_delete(self, ax):
        self.calls.append(("legend_delete",))


class _ToolbarStub:
    mode = ""

    def push_current(self):
        pass


class _NavStub(_ToolbarStub):
    """有 nav stack 的工具列替身（像 matplotlib NavigationToolbar2：_nav_stack() 空的時候回 None）。"""

    def __init__(self):
        self.pushes = 0

    def _nav_stack(self):
        return None if self.pushes == 0 else True

    def push_current(self):
        self.pushes += 1


def _w13_clip_temp_checks(check, fig) -> None:
    """0.9.14 W13（Windows 相容性檢查 0.9.13 第一輪：GUI 套件跑完 %TEMP% 留一個 plotkit_clip_*.png）：複製圖的暫存檔——
    (1) 成功：剪貼簿工具（PowerShell／osascript）跑的整段時間檔案都在，結束之後才刪（正被讀的檔不會被刪）；
    (2) 失敗、(3) 逾時被結束：檔案留著、訊息寫出它的路徑（0.9.13 起的行為：「PNG 已存到 …」給使用者用）；
    (4) leftover_clip_files：列出這個行程自己的與「留下它的行程已經不在」的 plotkit_clip_*（關閉時提醒用），還在跑的行程的、別的檔名不列，
        一個都不刪；
    (5) 之後的複製（任何平台）都不刪以前的行程複製失敗留下的 PNG（2026-10-30 使用者決定 W13「留著，但每次關閉時都要說哪裡有東西未處理」；
        0.9.14 第一版在 Windows 每次複製前刪掉它們——第一輪驗證 R14-REG-1）。剪貼簿工具換成本機的 python（不動系統剪貼簿）。"""
    py = sys.executable
    own = os.getpid()
    live = subprocess.Popen([py, "-c", "import time; time.sleep(60)"])
    dead = None
    for _ in range(3):                                      # 拿一個已經結束的行程的 pid（剛好被別的行程重用就換一個）
        p_ = subprocess.Popen([py, "-c", "pass"])
        p_.wait()
        if not clipboard._pid_alive(p_.pid) and p_.pid != live.pid:
            dead = p_.pid
            break
    tmpd = tempfile.gettempdir()
    marker = os.path.join(tmpd, f"pk_w13_marker_{own}.txt")
    seen = {}
    orig_cmd, orig_to = clipboard.clipboard_command_for, clipboard.CLIP_TIMEOUT_S
    script = ("import os,sys,time;p=sys.argv[1];a=os.path.exists(p);time.sleep(0.4);b=os.path.exists(p);"
              "open(sys.argv[2],'w').write(str(a)+' '+str(b));sys.exit(int(sys.argv[3]))")

    def fake(rc=0, sleep=None):
        def cmd(platform, path, kind="png"):
            seen["path"] = path
            if sleep:
                return [py, "-c", f"import time; time.sleep({sleep})"]
            return [py, "-c", script, path, marker, str(rc)]
        return cmd
    try:
        d = tempfile.mkdtemp(prefix="pk_w13_")
        names = {"dead": f"plotkit_clip_{dead}_1.png", "own": f"plotkit_clip_{own}_7.png", "live": f"plotkit_clip_{live.pid}_1.pdf",
                 "odd": "plotkit_clip_x.png", "foreign": "notes.png", "tail": f"plotkit_clip_{dead}_2.png.bak"}
        for n_ in names.values():
            with open(os.path.join(d, n_), "wb") as f_:
                f_.write(b"x")
        listed = [os.path.basename(p_) for p_ in clipboard.leftover_clip_files(d)]
        left = sorted(os.listdir(d))
        check(dead is not None and listed == sorted([names["dead"], names["own"]]) and left == sorted(names.values())
              and all(os.path.dirname(p_) == d for p_ in clipboard.leftover_clip_files(d)),
              f"W13 leftover_clip_files：列出這個行程自己的與留下它的行程已經不在的 plotkit_clip_*（{listed}；還在跑的行程的、別的檔名、"
              f"多了副檔名的都不列），一個都不刪（{left}）")
        for n_ in left:
            os.remove(os.path.join(d, n_))
        os.rmdir(d)
        clipboard.clipboard_command_for = fake(0)
        ok1, msg1 = clipboard.copy_figure_to_clipboard(fig)
        with open(marker, encoding="utf-8") as f_:
            during = f_.read()
        p1 = seen.get("path", "")
        deleted1 = not os.path.exists(p1)
        check(ok1 and during == "True True" and deleted1 == (not sys.platform.startswith("linux")),
              f"W13 成功：剪貼簿工具跑的整段時間暫存檔都在（{during}），工具結束之後才刪（{deleted1}；Linux 的 xclip 要留著）")
        clipboard.clipboard_command_for = fake(3)
        ok2, msg2 = clipboard.copy_figure_to_clipboard(fig)
        p2 = seen.get("path", "")
        kept2 = os.path.exists(p2)
        check(not ok2 and kept2 and p2 in msg2, f"W13 失敗：暫存檔留著、訊息寫出它的路徑（0.9.13 的「PNG 已存到 …」；{msg2[-60:]!r}）")
        if kept2:
            os.remove(p2)
        clipboard.CLIP_TIMEOUT_S = 1
        clipboard.clipboard_command_for = fake(sleep=8)
        t0 = time.time()
        ok3, msg3 = clipboard.copy_figure_to_clipboard(fig)
        dt3 = time.time() - t0
        p3 = seen.get("path", "")
        kept3 = os.path.exists(p3)
        check(not ok3 and dt3 < 6 and kept3 and p3 in msg3,
              f"W13 逾時：剪貼簿工具被結束（{dt3:.1f} s）、暫存檔留著、訊息寫出路徑（{msg3[:40]!r}）")
        if kept3:
            os.remove(p3)
        clipboard.CLIP_TIMEOUT_S = orig_to
        stale = os.path.join(tmpd, f"plotkit_clip_{dead}_9.png")
        with open(stale, "wb") as f_:
            f_.write(b"x")
        clipboard.clipboard_command_for = fake(0)
        kept4 = []
        sys_real, alive_real = clipboard.sys, clipboard._pid_alive
        try:
            # Windows 的那條路（clipboard 模組看到的 sys.platform＝win32；在 macOS／Linux 上剪貼簿工具會因為 creationflags 失敗、留下這次的 PNG——
            # 這裡只看複製前後以前的那個檔還在不在）。macOS／Linux 上行程在不在照這個平台的方法看（Windows 的 OpenProcess 在這裡叫不到）
            clipboard.sys = types.SimpleNamespace(platform="win32")
            if not sys.platform.startswith("win"):
                def _alive(pid, *_a, _own=os.getpid(), **_k):      # 產品現在多傳檔案的修改時間（W14R2-2）
                    if pid == _own:
                        return True
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        return False
                    except Exception:
                        return True
                    return True
                clipboard._pid_alive = _alive
            _ok_w, msg_w = clipboard.copy_figure_to_clipboard(fig)
            kept4.append(os.path.exists(stale))
        finally:
            clipboard.sys, clipboard._pid_alive = sys_real, alive_real
        mine_w = msg_w.split("PNG 已存到 ", 1)[-1].strip() if "PNG 已存到 " in msg_w else ""
        if mine_w and os.path.isfile(mine_w) and not sys.platform.startswith("win"):
            os.remove(mine_w)
        ok4, _m4 = clipboard.copy_figure_to_clipboard(fig)
        kept4.append(ok4 and os.path.exists(stale))
        if sys.platform.startswith("win"):
            # W14R2-2（第二輪 Windows 驗證）：pid 被 Windows 重複使用——檔名裡的 pid 現在是別的行程（這裡用父行程：它比檔案晚建立？不一定，所以把檔案的
            # 修改時間改成兩年前，一定早於父行程建立）→ 留下檔案的那個行程已經不在，要列；修改時間比父行程新（父行程還在跑）→ 不列
            reuse = os.path.join(tmpd, f"plotkit_clip_{os.getppid()}_7.png")
            with open(reuse, "wb") as f_:
                f_.write(b"x")
            os.utime(reuse, (time.time() - 2 * 365 * 86400, time.time() - 2 * 365 * 86400))
            listed_old = reuse in clipboard.leftover_clip_files(tmpd)
            os.utime(reuse, None)
            listed_new = reuse in clipboard.leftover_clip_files(tmpd)
            check(listed_old and not listed_new,
                  f"W14R2-2 Windows：檔名裡的 pid 被重複使用（行程比檔案晚建立）→ 當成留下檔案的行程已經不在、列出（{listed_old}）；"
                  f"檔案比那個行程新 → 它的、不列（{not listed_new}）")
            os.remove(reuse)
        check(all(kept4) and stale in clipboard.leftover_clip_files(tmpd),
              f"W13：之後的複製不刪以前的行程複製失敗留下的 PNG（Windows 的路徑、{sys.platform}：{kept4}），關閉時提醒列得出它（使用者 2026-10-30 決定：留著）")
        if os.path.exists(stale):
            os.remove(stale)
    finally:
        clipboard.clipboard_command_for, clipboard.CLIP_TIMEOUT_S = orig_cmd, orig_to
        live.kill()
        live.wait()
        if os.path.exists(marker):
            os.remove(marker)


def _dpi_main_checks(check) -> None:
    """2026-10-30 使用者決定：單獨執行 plotkit（python -m plotkit）也宣告高 DPI，和 DSV 一樣（Windows；Mac 不受影響）。
    (1) __main__.main 要開圖（--demo、圖.json）時，建第一個 Tk 視窗之前叫 theme.enable_windows_dpi_awareness（--selftest 不叫，和 DSV 一樣）；
    (2) 真的子行程（python -m plotkit 圖.json；開圖換成量完行程的 DPI awareness 就停，不開任何視窗）：Windows 是 per-monitor
        （GetProcessDpiAwareness＝2，宣告的結果 per-monitor-v2／per-monitor），macOS／Linux 什麼都不宣告。0.9.14 第一版沒有宣告（第一輪驗證 C14-7、W14-4）。"""
    from . import __main__ as pkmain
    from . import theme
    from .i18n import get_language, set_language
    calls: List[str] = []
    orig, lang0 = getattr(theme, "enable_windows_dpi_awareness", None), get_language()
    theme.enable_windows_dpi_awareness = lambda: calls.append("dpi") or ""
    rc = None
    try:
        import contextlib
        with contextlib.redirect_stderr(io.StringIO()):
            rc = pkmain.main([os.path.join(tempfile.gettempdir(), "pk_no_such_figure_%d.json" % os.getpid())])
    finally:
        if orig is not None:
            theme.enable_windows_dpi_awareness = orig
        set_language(lang0)
    check(rc == 1 and calls == ["dpi"], f"python -m plotkit 圖.json：開圖之前宣告高 DPI（{calls}；找不到圖 rc {rc}）")
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = ("import sys, json\n"
            f"sys.path.insert(0, {pkg_parent!r})\n"
            "import plotkit, plotkit.theme as T, plotkit.__main__ as m\n"
            "def _oj(path, **k):\n"
            "    aware = None\n"
            "    if sys.platform.startswith('win'):\n"
            "        import ctypes\n"
            "        v = ctypes.c_int(-1)\n"
            "        ctypes.windll.shcore.GetProcessDpiAwareness(None, ctypes.byref(v))\n"
            "        aware = v.value\n"
            "    print('DPI ' + json.dumps({'aware': aware, 'decl': list(T.WINDOWS_DPI_AWARENESS)}))\n"
            "    raise RuntimeError('stop before any window')\n"
            "plotkit.open_json = _oj\n"
            "sys.exit(m.main(['x.json']))\n")
    try:
        env = dict(os.environ)
        env.pop("PLOTKIT_LANG", None)
        env.pop("DSV_LANG", None)
        # encoding 寫明 UTF-8（子行程 PYTHONIOENCODING=utf-8 時 stderr 的中文在 cp950 的 Windows 以前讓讀取執行緒印 UnicodeDecodeError；第二輪測試強度驗證）
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                           cwd=pkg_parent, env=env)
        got = next((json.loads(ln[4:]) for ln in r.stdout.splitlines() if ln.startswith("DPI ")), {})
    except Exception as e:
        r, got = None, {"err": repr(e)}
    if sys.platform.startswith("win"):
        ok = got.get("aware") == 2 and str((got.get("decl") or [""])[0]).startswith("per-monitor")
    else:
        ok = got.get("aware") is None and got.get("decl") == []
    check(ok and r is not None and r.returncode == 1,
          f"python -m plotkit 圖.json（真的子行程）：{sys.platform} 的 DPI 宣告（Windows 要 per-monitor，其他平台不宣告）：{got}")


def selftest() -> bool:
    fails: List[str] = []

    def check(cond, msg):
        print(("ok   " if cond else "FAIL ") + msg)
        if not cond:
            fails.append(msg)

    def close(a, b, rel=1e-9, abs_=1e-9):
        return a is not None and math.isclose(float(a), float(b), rel_tol=rel, abs_tol=abs_)

    from . import bus as _bus
    _bus.selftest(check)                       # 數位匯流排顯示（六角框＋數值）、進位制格式
    from . import lod as _lod
    _lod.selftest(check)                       # 大資料線條的顯示降採樣（M4）
    from . import keys as _keys
    _keys.selftest(check)                      # 注音等非拉丁輸入法之下照實體按鍵認的快速鍵

    # --- Series ---------------------------------------------------------------------
    s = Series("a", [0, 1, 2], [1, 2, 3])
    check(s.n == 3 and not s.x.flags.writeable and s.x_sorted, "Series：陣列唯讀、x 單調")
    st = Series("st", [0, 1, 2, 3], [5, 6, 7], kind="step")
    x, y = st.plot_xy()
    check(len(x) == 4 and len(y) == 4 and y[-1] == 7 and st.vertex(2) == (2.0, 7.0), "Series step：x N+1 時補 y[-1]，頂點只到 n-1")
    st2 = Series("st2", [0, 1, 2], [5, 6, 7], kind="step", xshift=1.5)
    check(len(st2.plot_xy()[0]) == 3 and st2.vertex(0) == (1.5, 5.0), "Series step：x N 不補、位移生效")
    try:
        Series("bad", [0, 1], [1, 2, 3])
        check(False, "Series：長度不符要丟 ValueError")
    except ValueError:
        check(True, "Series：長度不符丟 ValueError")
    check(Series("m", [0], [0], marker="zz", ls="**", yaxis="up").marker == "" and
          Series("m", [0], [0], ls="**").ls is None, "Series：無效 marker/ls/yaxis 退回預設")

    # --- encode / decode ------------------------------------------------------------
    u = np.arange(0, 100) * 0.25 + 3
    e = model.encode_array(u)
    check(isinstance(e, dict) and e["n"] == 100 and np.array_equal(model.decode_array(e), u), "encode_array：等差 → 緊湊格式且精確")
    e2 = model.encode_array(np.array([1.0, 5.0, 2.0]))
    check(e2 == [1, 5, 2] and all(isinstance(v, int) for v in e2), "encode_array：整數值 → int list")
    e3 = model.encode_array(np.array([0.5, float("nan"), 2.25]))
    back = json.loads(json.dumps(e3))
    check(len(e3) == 3 and np.isnan(model.decode_array(back)[1]) and back[2] == 2.25, "encode_array：含 NaN 經 JSON 往返")

    # --- FigureState / JSON --------------------------------------------------------------
    fs = FigureState(title="T", xunit="us", style="matlab")
    a = fs.add_series(Series("A", np.linspace(0, 1, 50), np.sin(np.linspace(0, 6, 50)), color="#ff0000", lw=2.0))
    b = fs.add_series(Series("B", np.arange(11), np.arange(10) % 2, kind="step", yaxis="right"))
    fs.add_annotation(Annotation(kind="xline", value=0.3, text="sync"))
    fs.add_tip(DataTip(uid=a.uid, index=7, offset=(10, -20)))
    check(a.uid == 1 and b.uid == 2 and fs.next_uid == 3, "FigureState：uid 自動編號")
    snap = fs.snapshot()
    fs2 = FigureState()
    fs2.restore(snap)
    check(len(fs2.series) == 2 and fs2.series[0].x is a.x and fs2.tips[0].index == 7 and fs2.annotations[0].text == "sync",
          "snapshot/restore：陣列共用、提示與標註還原")
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "fig.json")
        model.save_json(fs, p)
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
        check(raw["format"] == model.FORMAT_NAME and raw["version"] == model.FORMAT_VERSION and "plotkit" in raw,
              "save_json：有 format / version")
        fs3 = model.load_json(p)
        check(fs3.title == "T" and fs3.style == "matlab" and len(fs3.series) == 2 and fs3.series[1].kind == "step"
              and np.allclose(fs3.series[0].y, a.y) and fs3.series[0].lw == 2.0 and fs3.tips[0].uid == a.uid,
              "load_json：內容一致")
        raw["version"] = 99
        d, warn = model.migrate_dict(raw)
        check(warn is not None and len(model.state_from_dict(raw).series) == 2, "migrate_dict：較新版本仍讀取並警告")
    fs0 = FigureState(series=[Series("p", [0, 1], [0, 1]), Series("q", [0, 1], [1, 2]), Series("r", [0], [0], uid=1)],
                      annotations=[Annotation(kind="xline", value=1), Annotation(kind="xline", value=2)])
    check([s.uid for s in fs0.series] == [2, 3, 1] and [a.id for a in fs0.annotations] == [1, 2] and fs0.next_uid == 4,
          f"FigureState(series=[...])：沒給的 uid 自動補、有給的保留（{[s.uid for s in fs0.series]}）")
    dsv = model.from_dsv_snapshot({"label": "L", "x": [0, 1, 2], "y": [3, 4], "color": "#00ff00", "lw": 1.0, "ls": "--",
                                   "xunit": "us", "xshift": 0.0, "yshift": 0.0})
    check(dsv.kind == "step" and dsv.n == 2 and dsv.color == "#00ff00", "from_dsv_snapshot")

    # --- styles ------------------------------------------------------------------------
    m = styles.get_style("matlab")
    check(m["colors"][0] == "#1171be" and m["lw"] == 0.5 and m["box"] is True and m["tick_dir"] == "in", "get_style('matlab')（R2025a 實測 Box=on）")
    c = styles.get_style({"base": "matlab", "lw": 1.5, "grid": {"alpha": 0.5}})
    check(c["lw"] == 1.5 and c["grid"]["alpha"] == 0.5 and c["grid"]["ls"] == "-" and c["colors"][0] == "#1171be", "get_style：dict 覆寫")
    rf = styles.resolve_fonts(["NoSuchFont-XYZ", "DejaVu Sans"])
    check(rf == ["DejaVu Sans"], f"resolve_fonts 去掉不存在的字型（{rf}）")

    # --- draw_state (Agg) ------------------------------------------------------------------
    fig = Figure(figsize=(8, 5), dpi=100)
    FigureCanvasAgg(fig)
    fs.series[0].visible = True
    hidden = fs.add_series(Series("H", np.arange(5), np.arange(5), visible=False))
    info = draw.draw_state(fig, fs, selected=[a.uid])
    fig.canvas.draw()
    check(set(info.lines) == {a.uid, b.uid} and info.ax_right is not None and len(fig.axes) == 2, "draw_state：隱藏不畫、右軸建立")
    texts = [t.get_text() for t in info.legend.get_texts()]
    check(texts == ["A", "B"] and info.legend_uids == [a.uid, b.uid] and info.legend.axes is info.ax_right,
          f"draw_state：圖例排除隱藏、順序正確、放在上層 axes（{texts}）")
    la = info.lines[a.uid]
    check(close(la.get_linewidth(), 2.0 * 2.5) and la.get_color() == "#ff0000", "draw_state：選取線加粗、自訂色")
    check(info.lines[b.uid].get_color() == "#dd5400" and close(info.lines[b.uid].get_linewidth(), 0.5),
          "draw_state：matlab 自動色依序號（含隱藏）、線寬 0.5")
    ax = info.ax_left
    check(ax.spines["top"].get_visible() and ax.spines["left"].get_visible()
          and info.ax_right.spines["right"].get_visible() and not info.ax_right.spines["left"].get_visible(),
          "matlab 風格：主軸四邊框（Box on）、twin 只留右")
    fsb = model.FigureState(style={"base": "matlab", "box": False})
    fsb.add_series(model.Series("b", np.arange(5.0), np.arange(5.0)))
    infob = draw.draw_state(Figure(figsize=(4, 3)), fsb)
    check(not infob.ax_left.spines["top"].get_visible() and not infob.ax_left.spines["right"].get_visible(), "box=False 時只留左下")
    try:
        tdir = ax.xaxis.get_tick_params()["direction"]
    except Exception:
        tdir = "in"
    check(tdir == "in" and ax.title.get_fontweight() == "bold" and fig.get_facecolor()[:3] != (1.0, 1.0, 1.0),
          "matlab 風格：刻度朝內、標題粗體、figure 底色")
    fs.style = "default"
    info2 = draw.draw_state(fig, fs)
    check(info2.lines[a.uid].get_color() == "#ff0000" and info2.lines[b.uid].get_color() == styles.PALETTE_DEFAULT[1]
          and close(info2.lines[b.uid].get_linewidth(), 1.0), "default 風格：tab10、線寬 1.0")
    fs.series[1].marker = "o"
    fs.series[1].ms = 7.0
    info3 = draw.draw_state(fig, fs)
    lb = info3.lines[b.uid]
    check(lb.get_marker() == "o" and lb.get_markersize() == 7.0 and lb.get_markevery() == slice(0, -1), "marker 與 markevery")
    big = fs.add_series(Series("big", np.arange(60001), np.zeros(60001), marker="o"))
    info4 = draw.draw_state(fig, fs)
    check(info4.lines[big.uid].get_marker() == "None", "超過 MAX_MARKER_POINTS 不畫 marker")
    fs.remove_series([big.uid, hidden.uid])
    fs.series[1].marker = ""

    # --- 幾何 -------------------------------------------------------------------------
    fig2 = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(fig2)
    ax2 = fig2.add_subplot(111)
    l0, = ax2.step([0, 1, 2, 3], [0, 0, 0, 0], where="post")
    l1, = ax2.step([0, 1, 2, 3], [10, 10, 10, 10], where="post")
    ax2.set_xlim(0, 3)
    ax2.set_ylim(-1, 11)
    fig2.canvas.draw()
    px, py = ax2.transData.transform((1.5, 10.0))
    check(draw.hit_test_lines([l0, l1], MouseEvent("button_press_event", fig2.canvas, px, py, button=1)) is l1, "hit_test_lines：點到 y=10 的線")
    px, py = ax2.transData.transform((1.5, 5.0))
    check(draw.hit_test_lines([l0, l1], MouseEvent("button_press_event", fig2.canvas, px, py, button=1)) is None, "hit_test_lines：中間 → None")
    xs = np.arange(100000.0)
    lbig, = ax2.plot(xs, np.sin(xs / 50))
    ax2.set_xlim(0, 100000)
    ax2.set_ylim(-2, 2)
    fig2.canvas.draw()
    px, py = ax2.transData.transform((50000, math.sin(1000)))
    t0 = time.time()
    hit = draw.hit_test_lines([lbig], MouseEvent("button_press_event", fig2.canvas, px, py, button=1))
    dt = time.time() - t0
    check(hit is lbig and dt < 0.5, f"hit_test_lines：1e5 點 {dt * 1000:.0f} ms")
    lbig.remove()
    # 長的線只看游標附近（hover 每個 motion 都要判定）：結果要跟 Line2D.contains／整個視圖找最近頂點完全一樣
    rng = np.random.default_rng(7)
    n_bad, n_cmp, n_hit = 0, 0, 0
    for ci, (ds, ls) in enumerate([("default", "-"), ("steps-post", "-"), ("steps-mid", "-"), ("default", "None")]):
        xq = np.cumsum(rng.uniform(0.2, 1.0, 20000))
        yq = np.cumsum(rng.normal(0, 1, 20000))
        lq, = ax2.plot(xq, yq, drawstyle=ds, linestyle=ls, marker="o" if ls == "None" else None, lw=1.5)
        ax2.set_xlim(xq[-1], xq[0]) if ci == 2 else ax2.set_xlim(xq[0], xq[-1])
        ax2.set_ylim(float(np.min(yq)), float(np.max(yq)))
        fig2.canvas.draw()
        tq = draw.PICK_TOL_PX + 0.5 * lq.get_linewidth() * fig2.dpi / 72.0
        for k in range(60):
            i = int(rng.integers(0, len(xq)))
            qx, qy = ax2.transData.transform((xq[i], yq[i]))
            evq = MouseEvent("motion_notify_event", fig2.canvas, qx + rng.normal(0, 3), qy + rng.normal(0, 3))
            fast = draw._line_hit_fast(lq, evq, tq)
            old_r = lq.get_pickradius()
            lq.set_pickradius(tq * 72.0 / fig2.dpi)
            ok_ref = lq.contains(evq)[0]
            lq.set_pickradius(old_r)
            if fast is None:
                n_bad += 1
                continue
            n_cmp += 1
            n_hit += int(ok_ref)
            if fast[0] != ok_ref:
                n_bad += 1
            elif ok_ref:
                pq = ax2.transData.transform(np.column_stack([xq, yq]))
                if abs(float(np.nanmin(np.hypot(pq[:, 0] - evq.x, pq[:, 1] - evq.y))) - fast[1]) > 1e-6:
                    n_bad += 1
        lq.remove()
    check(n_bad == 0 and n_hit > 20, f"hit_test_lines 快速路徑＝Line2D.contains（含 steps、反轉 x、只有標記；比了 {n_cmp} 次、命中 {n_hit}、不同 {n_bad}）")
    xs6 = np.arange(1e6)
    l6, = ax2.plot(xs6, np.sin(xs6 / 300))
    ax2.set_xlim(0, 1e6)
    ax2.set_ylim(-2, 2)
    fig2.canvas.draw()
    ev6 = MouseEvent("motion_notify_event", fig2.canvas, *ax2.transData.transform((5e5, 0.0)))
    t0 = time.perf_counter()
    for _ in range(10):
        draw.hit_test_lines([l6], ev6)
    dt6 = (time.perf_counter() - t0) / 10
    check(dt6 < 0.01, f"hit_test_lines：1e6 點全幅每次 {dt6 * 1000:.2f} ms（hover 每個 motion 都要判定；舊的整條轉換約 30 ms）")
    l6.remove()
    sser = Series("s", [0, 1, 2, 3, 4], [0, 10, 0, 10, 0], kind="step")
    ax2.set_xlim(0, 4)
    fig2.canvas.draw()
    px, py = ax2.transData.transform((1.4, 10))
    check(draw.nearest_index(sser, ax2, px, py) == 1, "nearest_index：step 平台上 → 該段的起點")
    px, py = ax2.transData.transform((3.9, 10))
    check(draw.nearest_index(sser, ax2, px, py) == 3, "nearest_index：靠近下一個頂點前仍是同段")
    ax3 = ax2.twinx()
    ax3.set_ylim(0, 100)
    fig2.canvas.draw()
    px, py = ax2.transData.transform((2.0, 1.0))
    ev = MouseEvent("button_press_event", fig2.canvas, px, py, button=1)
    got = draw.axes_at(fig2, ev)
    check(got == [ax2, ax3] and close(draw.data_coords(ax2, ev)[1], 1.0, abs_=1e-6)
          and abs(draw.data_coords(ax3, ev)[1] - 1.0) > 1, "axes_at / data_coords：twin 兩個都回、y 不同")
    check(draw.zoom_limits(0, 10, 2, 0.5) == (1.0, 6.0) and draw.pan_limits(0, 10, 3) == (-3, 7), "zoom_limits / pan_limits")
    from . import interact as _ia
    _fig0 = Figure(); _ax0 = _fig0.add_subplot(111)
    _sp = _ia.scaled_pan(_ax0.xaxis, (-8e307, 8e307), 40.0, 800.0)
    check(all(math.isfinite(v) for v in _sp) and _sp[0] < -8e307 and _sp[1] < 8e307, f"scaled_pan：±8e307 的範圍平移不溢位（{_sp}）")
    check(_ia.scaled_pan(_ax0.xaxis, (-1e308, 1e308), 40.0, 800.0) == (-1e308, 1e308), "scaled_pan：範圍本身已溢位時原樣回傳")

    class _E:
        def __init__(self, step=0, modifiers=None, key=None):
            self.step, self.modifiers, self.key = step, modifiers, key

    mac_tick = draw.wheel_notches(_E(1 / 120))
    check(draw.wheel_notches(_E(1)) == 1 and draw.wheel_notches(_E(-7)) == -3 and draw.wheel_notches(_E(0)) == 0
          and (mac_tick == 1 if sys.platform == "darwin" else 0 < mac_tick < 1),
          f"wheel_notches：滑鼠 ±1、限制 ±3、macOS 1/120 → 1、觸控板小數累加（{mac_tick:g}）")
    check(draw.has_mod(_E(modifiers={"shift"}), "shift") and draw.has_mod(_E(key="shift+a"), "shift")
          and not draw.has_mod(_E(), "shift"), "has_mod：modifiers 優先、key 備援")

    # --- Interactor (Agg) ----------------------------------------------------------------
    st3 = FigureState()
    sa = st3.add_series(Series("sa", np.arange(100.0), np.sin(np.arange(100.0) / 10) * 10))
    sb = st3.add_series(Series("sb", np.arange(11.0), (np.arange(10) % 2) * 50.0, kind="step", yaxis="right"))
    fig3 = Figure(figsize=(8, 5), dpi=100)
    FigureCanvasAgg(fig3)
    host = _RecHost(st3, fig3)
    ia = Interactor(fig3.canvas, host, toolbar=_ToolbarStub(), model=InteractorModel(st3.tips, st3.annotations))
    fig3.canvas.draw()
    axl = host.info.ax_left
    xl0 = axl.get_xlim()
    yl0 = axl.get_ylim()
    cx, cy = axl.transData.transform((50.0, 0.0))
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1))
    xl1 = axl.get_xlim()
    yl1 = axl.get_ylim()
    check((xl1[1] - xl1[0]) < (xl0[1] - xl0[0]) and (yl1[1] - yl1[0]) < (yl0[1] - yl0[0]) and ("view",) in host.calls,
          "Interactor：滾輪兩軸一起放大，有 on_view_change")
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1, modifiers={"shift"}))
    xl2, yl2 = axl.get_xlim(), axl.get_ylim()
    check((xl2[1] - xl2[0]) < (xl1[1] - xl1[0]) and close(yl2[0], yl1[0]) and close(yl2[1], yl1[1]), "Interactor：Shift+滾輪只縮 x")
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1, modifiers={"ctrl", "shift"}))
    xl3, yl3 = axl.get_xlim(), axl.get_ylim()
    check(close(xl3[0], xl2[0]) and (yl3[1] - yl3[0]) < (yl2[1] - yl2[0]), "Interactor：Ctrl+Shift+滾輪只縮 y")
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1, modifiers={"ctrl"}))
    xl4, yl4 = axl.get_xlim(), axl.get_ylim()
    check((xl4[1] - xl4[0]) < (xl3[1] - xl3[0]) and (yl4[1] - yl4[0]) < (yl3[1] - yl3[0]), "Interactor：Ctrl／⌘+滾輪＝兩軸縮放（明確要求縮放）")
    ia.wheel_filter = lambda ev: False
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1))
    check(axl.get_xlim() == xl4, "Interactor：wheel_filter 回 False 時不縮放（host 要拿去捲動）")
    ia.wheel_filter = None
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1, modifiers={"alt"}))
    check(axl.get_xlim() == xl4 and axl.get_ylim() == yl4, "Interactor：Alt+滾輪不縮放（留給 host 捲動畫布）")
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=2.5))
    xl3c = axl.get_xlim()
    check(close((xl4[1] - xl4[0]) / (xl3c[1] - xl3c[0]), 1.1), "Interactor：一個滾輪事件最多 1.1 倍（MATLAB 的滾輪縮放；step=2.5 也只算一格）")
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=0.5))
    xl3d = axl.get_xlim()
    exp_half = 1.1 if sys.platform == "darwin" else 1.1 ** 0.5      # macOS 的 Tk 沒有小數格（wheel_notches 把 <1 的 step 當整格）
    check(close((xl3c[1] - xl3c[0]) / (xl3d[1] - xl3d[0]), exp_half), f"Interactor：精準觸控板的小數格按比例縮放（0.5 格 → {exp_half:.4f}）")
    from . import interact as _itm
    ia.restore_view()
    xh, yh = axl.get_xlim(), axl.get_ylim()
    for _k in range(6):
        ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=-1))
    check(close(axl.get_xlim()[0], xh[0]) and close(axl.get_xlim()[1], xh[1]) and close(axl.get_ylim()[0], yh[0]) and close(axl.get_ylim()[1], yh[1]),
          f"Interactor：縮小到自動範圍為止（和 MATLAB 一樣；{axl.get_xlim()} vs {xh}）")
    oa = _itm.auto_limits(axl, "x")
    check(oa is not None and close(oa[0], xh[0]) and close(oa[1], xh[1]), f"auto_limits ＝ autoscale 給的範圍（{oa} vs {xh}）")
    ia.zoom_step([axl], cx, cy, 1.5)
    xs = axl.get_xlim()
    check(close((xh[1] - xh[0]) / (xs[1] - xs[0]), 1.5) and close(axl.transData.inverted().transform((cx, cy))[0], 50.0, abs_=1e-6),
          "zoom_step：以該點為中心放大 1.5 倍（放大模式單擊）")
    ia.zoom_step([axl], cx, cy, 1 / 1.5)
    check(close(axl.get_xlim()[0], xh[0]) and close(axl.get_xlim()[1], xh[1]), "zoom_step 1/1.5：縮回自動範圍（Shift＋單擊）")
    wa, wb = axl.transData.inverted().transform((cx - 50, cy))[0], axl.transData.inverted().transform((cx + 50, cy))[0]
    ia.zoom_box([axl], (cx - 50, cy - 40), (cx + 50, cy + 40), "x")
    xb = axl.get_xlim()
    check(close(xb[0], wa) and close(xb[1], wb) and close(axl.get_ylim()[0], yh[0]) and close(axl.get_ylim()[1], yh[1]),
          "zoom_box：只縮 x 到框的範圍、y 不動（細長框）")
    axl.set_xlim(xh[0] - 100, xh[1] + 100)        # 平移／設定到外界之外後：縮小不再被夾（照 MATLAB：已經超出外界就不夾）
    xo = axl.get_xlim()
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=-1))
    check((axl.get_xlim()[1] - axl.get_xlim()[0]) > (xo[1] - xo[0]) * 1.05, "目前範圍已超出外界 → 縮小不夾")
    ia.restore_view()
    if sys.platform == "darwin":
        # macOS Tk 8.6：每個 NSScrollWheel（含觸控板慣性）都變成 delta ≥ ±1 的 <MouseWheel>；真的 GUI 事件（有 guiEvent）
        # 一串 60 Hz、1 秒的觸控板事件不能再當 60 格（1.1**60 ≈ 304 倍），滑鼠隔開的一格仍是 1 格
        from . import interact as _it
        clock = [1000.0]
        _orig_now = _it._now
        _it._now = lambda: clock[0]
        try:
            ia._wheel_streams.clear()
            ia._wheel_draw_t = -1e9
            xa = axl.get_xlim()
            ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1 / 120, guiEvent=object()))
            xb = axl.get_xlim()
            check(close((xa[1] - xa[0]) / (xb[1] - xb[0]), 1.1), "macOS 滾輪：隔開的一格（真的 GUI 事件）＝ 1.1 倍（MATLAB）")
            clock[0] += 1.0
            for _k in range(60):
                clock[0] += 1 / 60
                ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1 / 120, guiEvent=object()))
            xc = axl.get_xlim()
            r60 = (xb[1] - xb[0]) / (xc[1] - xc[0])
            check(1.2 < r60 < 2.8, f"macOS 觸控板：1 秒 60 個 ±1 事件的總倍率有界（{r60:.2f} 倍，舊版 {1.1 ** 60:.0f} 倍）")
            ia.restore_view()
            ya = axl.get_ylim()
            for _k in range(30):                    # 斜著滑：deltaY 事件與加了 Shift、正負號相反的 deltaX 事件交錯
                clock[0] += 1 / 60
                ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1 / 120, guiEvent=object()))
                ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=-1 / 120, modifiers={"shift"}, guiEvent=object()))
            yb = axl.get_ylim()
            ry = (ya[1] - ya[0]) / (yb[1] - yb[0])
            check(1.15 < ry < 2.8, f"macOS 觸控板斜滑（deltaX 反號、交錯）：y 倍率仍有界（{ry:.2f} 倍）")
            ia.restore_view()
            ia._wheel_streams.clear()
            clock[0] += 1.0
            xa = axl.get_xlim()
            for _k in range(5):                     # 滑鼠 10 格/秒，但每次重畫後兩格一起到（排隊）：仍要算 10 格
                clock[0] += 0.2
                ia._wheel_draw_t = clock[0] - 0.01
                for _j in range(2):
                    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1 / 120, guiEvent=object()))
            xd = axl.get_xlim()
            rq = (xa[1] - xa[0]) / (xd[1] - xd[0])
            check(2.3 < rq < 2.9, f"macOS 滑鼠：重畫後成批到達的滾輪事件不打折（10 格 → {rq:.2f} 倍，應約 {1.1 ** 10:.2f}）")
            ia.restore_view()
            tbs = _NavStub()
            ia2 = Interactor(fig3.canvas, host, toolbar=tbs, model=InteractorModel(st3.tips, st3.annotations))
            clock[0] += 1.0
            ia2.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1 / 120, guiEvent=object()))
            check(tbs.pushes == 2, f"第一次滾輪縮放前先把原始視圖推進 nav stack（Home 回得去；push {tbs.pushes} 次）")
            ia2.disconnect()
        finally:
            _it._now = _orig_now
        ia.restore_view()
    check(isinstance(draw.fmt_num(float("nan")), str) and isinstance(draw.fmt_num(float("inf")), str)
          and isinstance(draw.format_tip_text("a", float("nan"), float("nan")), str), "fmt_num／format_tip_text：NaN、inf 不丟例外")
    ia.restore_view()
    check(close(axl.get_xlim()[0], xl0[0], abs_=1e-6) and close(axl.get_xlim()[1], xl0[1], abs_=1e-6), "restore_view：回到自動範圍")
    # 平移：空白處按下、拖、放開
    ex, ey = axl.transData.transform((15.0, -3.0))   # 左軸與右軸（twin）都沒有線經過的空白處
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ex, ey, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, ex + 60, ey))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, ex + 60, ey, button=1))
    xl4 = axl.get_xlim()
    check(xl4[0] < xl0[0] and close(xl4[1] - xl4[0], xl0[1] - xl0[0], rel=1e-6) and host.calls[-1] == ("view",),
          "Interactor：左鍵拖曳平移 x 範圍往左移")
    ia.restore_view()
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ex, ey, button=1))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, ex, ey, button=1))
    check(host.calls[-1] == ("empty",), "Interactor：按下放開沒移動 → on_click_empty")
    # 點線
    lx, ly = axl.transData.transform((30.0, float(sa.y[30])))
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, lx, ly, button=1))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, lx, ly, button=1))
    check(host.calls[-1] == ("pick", sa.uid, 30), f"Interactor：點線條 → on_pick(uid, index)（{host.calls[-1]}）")
    hit = ia.hit_test(MouseEvent("button_press_event", fig3.canvas, lx, ly, button=1))
    check(hit.kind == "line" and hit.id == sa.uid, "hit_test：line")
    # 右軸的線（event.inaxes 是 twin）
    rx, ry = host.info.ax_right.transData.transform((1.5, 50.0))
    ev = MouseEvent("button_press_event", fig3.canvas, rx, ry, button=1)
    check(ev.inaxes is host.info.ax_right and ia.hit_test(ev).id == sb.uid, "hit_test：twin 上的線也找得到")
    # 資料提示
    ia.tips_enabled = True
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, lx, ly, button=1))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, lx, ly, button=1))
    check(len(st3.tips) == 1 and st3.tips[0].uid == sa.uid and st3.tips[0].index == 30 and len(ia.tip_artists) == 1
          and ("before", "tip_add", None) in host.calls and ("after", "tip_add") in host.calls, "Interactor：tips 模式點線 → 釘提示＋undo 回呼")
    fig3.canvas.draw()
    ann, mk = ia.tip_artists[st3.tips[0].id]
    check("sa" in ann.get_text() and "\nX 30\n" in ann.get_text() and "\nY " in ann.get_text(),
          f"資料提示文字：名稱＋X／Y 兩列（{ann.get_text()!r}）")
    bb = ann.get_bbox_patch().get_window_extent(fig3.canvas.get_renderer())
    tx, ty = (bb.x0 + bb.x1) / 2, (bb.y0 + bb.y1) / 2
    check(ia.hit_test(MouseEvent("button_press_event", fig3.canvas, tx, ty, button=1)).kind == "tip", "hit_test：tip 優先")
    off0 = st3.tips[0].offset
    check(abs(off0[0]) == model.TIP_OFFSET_DEFAULT[0] and abs(off0[1]) == model.TIP_OFFSET_DEFAULT[1], f"釘上時框貼在資料點的一角（offset={off0}）")
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, tx, ty, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, tx + 40, ty + 20))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, tx + 40, ty + 20, button=1))
    off = st3.tips[0].offset
    check(close(off[0], off0[0] + 40 * 72 / 100, abs_=1e-6) and close(off[1], off0[1] + 20 * 72 / 100, abs_=1e-6)
          and host.calls[-1] == ("after", "tip_move"), f"資料提示拖曳：offset 以點計（{off}）")
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, rx, ry, button=3))
    check(host.calls[-1] == ("context", "line", sb.uid), "右鍵 → on_context(hit)")
    items = ia.menu_items(Hit("empty", axl), MouseEvent("button_press_event", fig3.canvas, ex, ey, button=3))
    check(any(it and it[0].startswith("插入垂直參考線") for it in items) and any(it and it[0] == "清除全部資料提示" for it in items),
          "menu_items：插入參考線與清除提示")
    # 圖例（MATLAB 預設互動）：拖曳＝移動圖例（不平移）、Esc 取消、雙擊框非文字處不動作、
    # 右鍵＝圖例自己的選單（Delete／Location，不夾插入參考線）、拖到座標區外仍點得到
    fig3.canvas.draw()
    leg3 = host.info.legend
    r3 = fig3.canvas.get_renderer()
    lb3 = leg3.get_window_extent(r3)
    tb3 = leg3.get_texts()[0].get_window_extent(r3)
    bx, by = (lb3.x0 + tb3.x0) / 2, (tb3.y0 + tb3.y1) / 2           # 框裡、文字左邊（線段樣本那一帶）
    txc, tyc = (tb3.x0 + tb3.x1) / 2, (tb3.y0 + tb3.y1) / 2
    check(ia.hit_test(MouseEvent("button_press_event", fig3.canvas, bx, by, button=1)).kind == "legend_box"
          and ia.hit_test(MouseEvent("button_press_event", fig3.canvas, txc, tyc, button=1)).kind == "legend",
          "hit_test：圖例框／圖例文字")
    ia.zoom([axl], cx, cy, 0.5)
    xl_z = axl.get_xlim()
    ncalls = len(host.calls)
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, bx, by, button=1, dblclick=True))
    check(axl.get_xlim() == xl_z and ("restore",) not in host.calls[ncalls:], "雙擊圖例框非文字處：不動作（不還原視圖）")
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, bx, by, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, bx - 80, by - 50))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, bx - 80, by - 50, button=1))
    fig3.canvas.draw()
    lb4 = leg3.get_window_extent(fig3.canvas.get_renderer())
    check(host.calls[-1][0] == "legend_move" and isinstance(host.calls[-1][1], tuple) and axl.get_xlim() == xl_z
          and abs((lb4.x0 - lb3.x0) + 80) < 2 and abs((lb4.y0 - lb3.y0) + 50) < 2,
          f"拖曳圖例 → 移動 (-80,-50)、不平移（Δ=({lb4.x0 - lb3.x0:.0f},{lb4.y0 - lb3.y0:.0f})，{host.calls[-1]}）")
    loc4 = leg3._loc
    bx4, by4 = bx - 80, by - 50
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, bx4, by4, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, bx4 + 40, by4))
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "escape", bx4 + 40, by4))
    check(ia._drag is None and leg3._loc == loc4, "拖曳圖例中按 Esc → 取消、回到原位")
    axbb = host.info.ax_right.bbox
    ox = axbb.x1 + 20 - (lb4.x0 - bx4)                               # 把圖例左緣拖到座標區右邊外面
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, bx4, by4, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, ox, by4))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, ox, by4, button=1))
    fig3.canvas.draw()
    lb5 = leg3.get_window_extent(fig3.canvas.get_renderer())
    ev5 = MouseEvent("button_press_event", fig3.canvas, (lb5.x0 + lb5.x1) / 2, (lb5.y0 + lb5.y1) / 2, button=3)
    h5 = ia.hit_test(ev5)
    check(lb5.x0 > axbb.x1 and ev5.inaxes is None and h5.kind in ("legend", "legend_box"),
          f"圖例拖到座標區外仍點得到（{h5.kind}）")
    ia.on_press(ev5)
    check(host.calls[-1][:2] == ("context", h5.kind), "座標區外的圖例右鍵 → on_context")
    li = ia.menu_items(Hit("legend_box", host.info.ax_right, leg3), ev5)
    check(li and li[0][0] == "刪除圖例" and li[1][0] == "圖例位置" and [a for a, _ in li[1][1]] == ["右上", "左上", "右下", "左下", "最佳"]
          and not any(it and it[0].startswith("插入") for it in li) and li[-1] is not None,
          "圖例右鍵選單：刪除圖例／圖例位置 ▸ 5 項（MATLAB Delete／Location），沒有插入參考線、結尾沒有分隔線")
    li[1][1][3][1]()
    li[0][1]()
    check(host.calls[-2:] == [("legend_loc", "lower left"), ("legend_delete",)], "圖例選單回呼：on_legend_loc／on_legend_delete")
    leg3.set_loc("upper right")
    ia.restore_view()
    # 重畫後重建
    host.redraw()
    ia.reset()
    n_tip, n_ann = ia.rebuild()
    check(n_tip == 1 and len(ia.tip_artists) == 1, "rebuild：fig.clear 後資料提示重建")
    fig3.canvas.draw()
    axl = host.info.ax_left                           # fig.clear 之後 axes 是新的
    ex, ey = axl.transData.transform((15.0, -3.0))
    cx, cy = axl.transData.transform((50.0, 0.0))
    ia.tips_enabled = False
    ia.add_annotation(Annotation(kind="xline", value=20.0, text="x20"))
    ia.add_annotation(Annotation(kind="text", x=60.0, y=5.0, text="note"))
    check(len(st3.annotations) == 2 and len(ia.ann_artists) == 2, "add_annotation：xline 與 text")
    fig3.canvas.draw()
    tart = ia.ann_artists[st3.annotations[1].id]
    bbt = tart.get_window_extent(fig3.canvas.get_renderer())
    tcx, tcy = (bbt.x0 + bbt.x1) / 2, (bbt.y0 + bbt.y1) / 2
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, tcx, tcy, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, tcx + 30, tcy - 30))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, tcx + 30, tcy - 30, button=1))
    check(st3.annotations[1].x > 60.0 and st3.annotations[1].y < 5.0 and host.calls[-1] == ("after", "ann_move"), "文字標註拖曳更新座標")
    check(ia.selected_ann == st3.annotations[1].id, "拖完的文字標註是選取狀態（像 MATLAB plot edit）")
    ia.selected_tip = st3.tips[0].id
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "delete", lx, ly))
    check(len(st3.tips) == 0 and not ia.tip_artists, "Delete 鍵刪除選取的資料提示")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "delete", lx, ly))
    check(len(st3.annotations) == 1 and ia.selected_ann is None and host.calls[-1] == ("after", "ann_remove"),
          "沒有選取提示時 Delete → 刪掉選取的標註")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "delete", lx, ly))
    check(host.calls[-1] == ("delete_key",), "沒有選取提示／標註時 Delete → host.on_delete_key")
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, tcx, tcy, button=3))      # 右鍵在（已不存在的）文字位置：不選取
    ia.select_annotation(st3.annotations[0].id)
    check(ia.selected_ann == st3.annotations[0].id and ia.ann_artists[st3.annotations[0].id].get_linewidth() > 1.0, "select_annotation：參考線加粗")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "escape", lx, ly))
    check(ia.selected_ann is None and ia.ann_artists[st3.annotations[0].id].get_linewidth() == st3.annotations[0].lw, "Esc 取消標註選取、線寬還原")
    # 點選參考線＝選取（不平移）、右鍵先選取、與資料提示選取互斥、Delete 只刪目前選的那一種
    xid = st3.annotations[0].id
    xpx, ypx = axl.transData.transform((20.0, sum(axl.get_ylim()) / 2))
    xl_before = axl.get_xlim()
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, xpx, ypx, button=1))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, xpx, ypx, button=1))
    check(ia.selected_ann == xid and axl.get_xlim() == xl_before, "點參考線＝選取它、視圖不動（MATLAB plot edit 點物件）")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "escape", lx, ly))
    n_ctx = sum(1 for c in host.calls if c[0] == "context")
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, xpx, ypx, button=3))
    check(ia.selected_ann == xid and sum(1 for c in host.calls if c[0] == "context") == n_ctx + 1, "右鍵參考線：先選取再出選單")
    tip_x = ia.add_tip(sa.uid, 30)
    check(tip_x is not None and ia.selected_tip == tip_x.id and ia.selected_ann is None, "釘資料提示 → 取消標註的選取（選取互斥）")
    ia.select_annotation(xid)
    check(ia.selected_ann == xid and ia.selected_tip is None, "選標註 → 取消資料提示的選取")
    ia.select_tip(tip_x.id)
    check(ia.selected_tip == tip_x.id and ia.selected_ann is None, "select_tip → 取消標註的選取")
    ia.select_annotation(xid)
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "delete", lx, ly))
    check(len(st3.annotations) == 0 and len(st3.tips) == 1, "Delete 只刪選取的標註，資料提示留著")
    ia.remove_tip(tip_x.id)
    ia.add_annotation(Annotation(kind="xline", value=20.0, text="x20"))
    host.restore_handled = True
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ex, ey, button=1, dblclick=True))
    check(host.calls[-1] == ("restore",), "雙擊空白 → 還原視圖（host 接手）")
    ia.toolbar.mode = "zoom rect"
    before = axl.get_xlim()
    ia.on_scroll(MouseEvent("scroll_event", fig3.canvas, cx, cy, step=1))
    mid = axl.get_xlim()
    check(mid != before and close((before[1] - before[0]) / (mid[1] - mid[0]), 1.1), "工具列放大模式開著時滾輪照樣縮放（MATLAB zoom 模式下滾輪仍有效）")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "up", cx, cy))
    up = axl.get_xlim()
    check(close((mid[1] - mid[0]) / (up[1] - up[0]), 1.1), "放大模式裡 ↑ 鍵放大 1.1 倍（MATLAB 的 zoom 快速鍵）")
    ia.toolbar.mode = ""
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "up", cx, cy))
    check(axl.get_xlim() == up, "沒開模式時 ↑ 不縮放")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "-", cx, cy))
    check(close((axl.get_xlim()[1] - axl.get_xlim()[0]) / (up[1] - up[0]), 1.1), "− 鍵縮小 1.1 倍（MATLAB R2024a 起的預設鍵盤縮放）")
    # 注音輸入法之下 - 鍵：Tk 給 keysym "??"、字 ㄦ（2026-10-27 用真的按鍵量的），matplotlib 的 key 是 "ㄦ"：照實體按鍵認成 -（只有 macOS）
    zh = type("TkEv", (), {"keysym": "??", "keycode": 0x1B003126, "state": 0, "char": "ㄦ"})()
    w_before = axl.get_xlim()[1] - axl.get_xlim()[0]
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "ㄦ", cx, cy, guiEvent=zh))
    ratio = (axl.get_xlim()[1] - axl.get_xlim()[0]) / w_before
    check(ratio > 1.05 if sys.platform == "darwin" else close(ratio, 1.0, rel=1e-6),
          f"注音的 - 鍵（key 'ㄦ'、keysym ??、keycode 0x1B003126）{'照實體按鍵認成 −、縮小' if sys.platform == 'darwin' else '：不是 macOS 不換'}（寬度 ×{ratio:.3f}）")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "ㄦ", cx, cy))
    check(close((axl.get_xlim()[1] - axl.get_xlim()[0]) / w_before, ratio, rel=1e-6), "沒有 Tk 事件（guiEvent）的 'ㄦ' 照舊不做事")
    fig3.canvas.callbacks.process("scroll_event", MouseEvent("scroll_event", fig3.canvas, cx, cy, step=-1))
    check(axl.get_xlim() != up and axl.get_xlim() != mid, "mpl_connect 有接上（callbacks.process 也會觸發）")
    ia.remove_annotation(st3.annotations[0].id)
    check(len(st3.annotations) == 0 and not ia.ann_artists, "remove_annotation")

    # --- MATLAB 的平移／還原視圖細節：方向鍵、尺規、工具列模式裡雙擊／右鍵、原始視圖 ---------------------------
    host.restore_handled = False
    ia.restore_view()
    xr0, yr0 = axl.get_xlim(), axl.get_ylim()
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "left", cx, cy))
    xr1 = axl.get_xlim()
    d_expect = 5.0 * (xr0[1] - xr0[0]) / axl.bbox.width
    check(close(xr1[0] - xr0[0], d_expect, rel=1e-6) and close(xr1[1] - xr0[1], d_expect, rel=1e-6) and axl.get_ylim() == yr0,
          f"方向鍵 ←：等於往左拖 5 像素、y 不動（MATLAB 的 pan 方向鍵 5 像素；移 {xr1[0] - xr0[0]:.4g}，應 {d_expect:.4g}）")
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "up", cx, cy))
    check(axl.get_xlim() == xr1 and axl.get_ylim()[0] < yr0[0], "方向鍵 ↑：只動 y（往上拖 5 像素）")
    ia.restore_view()
    check(close(axl.get_xlim()[0], xr0[0], abs_=1e-6) and close(axl.get_ylim()[0], yr0[0], abs_=1e-6),
          "方向鍵之後 restore_view 回到第一次互動前的視圖")
    labs = [t for t in axl.xaxis.get_majorticklabels() if t.get_visible() and t.get_text()]
    tb = labs[0].get_window_extent(fig3.canvas.get_renderer())
    rx, ry = (axl.bbox.x0 + axl.bbox.x1) / 2, (tb.y0 + tb.y1) / 2
    hit_r = ia.hit_test(MouseEvent("button_press_event", fig3.canvas, rx, ry, button=1))
    check(hit_r.kind == "ruler" and hit_r.id == "x" and hit_r.ax is axl, f"hit_test：x 刻度文字區＝尺規（{hit_r.kind} {hit_r.id}）")
    yb = axl.get_ylim()
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, rx, ry, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, rx - 60, ry))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, rx - 60, ry, button=1))
    check(axl.get_xlim()[0] > xr0[0] and axl.get_ylim() == yb and host.calls[-1] == ("view",),
          "拖曳 x 尺規：只沿 x 平移（MATLAB rulerPanInteraction）")
    ia.restore_view()
    host.restore_handled = True
    n_restore = sum(1 for c in host.calls if c == ("restore",))
    ia.toolbar.mode = "pan/zoom"
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ex, ey, button=1, dblclick=True))
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ex, ey, button=3))
    check(sum(1 for c in host.calls if c == ("restore",)) == n_restore + 1 and host.calls[-1][0] == "context",
          "工具列平移模式開著：雙擊＝還原視圖、右鍵＝選單（MATLAB pan 模式的 'open'／'alt'）")
    ia.toolbar.mode = ""
    host.restore_handled = False
    ia.restore_view()
    xt0 = axl.get_xlim()
    ix, iy = int(ex), int(ey)                     # MouseEvent 的 x／y 會取整數：用整數像素才量得準
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ix, iy, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, ix + 9, iy))
    t9 = axl.get_xlim() == xt0 and not ia.dragging
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, ix + 10, iy))
    t10 = axl.get_xlim() != xt0 and ia.dragging
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, ix + 10, iy, button=1))
    check(DRAG_THRESHOLD_PX == 10.0 and t9 and t10, f"拖曳門檻 10 px（MATLAB 的拖曳門檻）：9 px 不算拖、10 px 才平移（{t9} {t10}）")
    ia.restore_view()
    labs_y = [t for t in axl.yaxis.get_majorticklabels() if t.get_visible() and t.get_text()]
    tby = labs_y[len(labs_y) // 2].get_window_extent(fig3.canvas.get_renderer())
    ryx, ryy = (tby.x0 + tby.x1) / 2, (axl.bbox.y0 + axl.bbox.y1) / 2
    xb, yb = axl.get_xlim(), axl.get_ylim()
    ia.on_press(MouseEvent("button_press_event", fig3.canvas, ryx, ryy, button=1))
    ia.on_motion(MouseEvent("motion_notify_event", fig3.canvas, ryx + 40, ryy + 30))
    ia.on_release(MouseEvent("button_release_event", fig3.canvas, ryx + 40, ryy + 30, button=1))
    check(axl.get_xlim() == xb and axl.get_ylim() != yb, "拖曳 y 尺規（y 刻度文字）：只沿 y 平移")
    ia.restore_view()

    # --- 資料提示選取時的方向鍵（MATLAB 的資料提示方向鍵）：→／↑ +1、←／↓ −1，優先於平移 ---
    tip_k = ia.add_tip(sa.uid, 10)
    xk, yk = axl.get_xlim(), axl.get_ylim()
    seq = []
    for key in ("right", "up", "left", "down", "down"):
        ia.on_key(KeyEvent("key_press_event", fig3.canvas, key, cx, cy))
        seq.append(tip_k.index)
    check(tip_k is not None and ia.selected_tip == tip_k.id and seq == [11, 12, 11, 10, 9]
          and axl.get_xlim() == xk and axl.get_ylim() == yk,
          f"選取的資料提示：→／↑＝下一個樣本、←／↓＝上一個，視圖不平移（{seq}）")
    check(("before", "tip_move", "tip_key") in host.calls and host.calls[-1] == ("after", "tip_move"),
          "方向鍵移動資料提示可復原（before_model_change tip_move）")
    tip_k.index = 0
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "left", cx, cy))
    check(tip_k.index == 0 and axl.get_xlim() == xk, "資料提示在第一個樣本時 ← 不動、也不改成平移")
    ia.deselect_tip()
    ia.on_key(KeyEvent("key_press_event", fig3.canvas, "left", cx, cy))
    check(tip_k.index == 0 and axl.get_xlim() != xk, "沒有選取提示時方向鍵照常平移")
    ia.remove_tip(tip_k.id)
    ia.restore_view()

    # --- NaN／inf 頂點、「_」開頭的 label、JSON 容錯（測試 agent 找到的問題）-------------------
    import warnings as _w
    st7 = FigureState()
    y7 = np.sin(np.arange(100.0) / 10) * 10
    y7[40:60] = np.nan
    y7[70] = np.inf
    s7 = st7.add_series(Series("_under", np.arange(100.0), y7))
    s7b = st7.add_series(Series("plain", np.arange(100.0), -np.nan_to_num(y7, posinf=0.0)))
    fig7 = Figure(figsize=(8, 5), dpi=100)
    FigureCanvasAgg(fig7)
    with _w.catch_warnings(record=True) as rec7:
        _w.simplefilter("always")
        host7 = _RecHost(st7, fig7)
    texts7 = [t.get_text() for t in host7.info.legend.get_texts()]
    check(len(texts7) == 2 and texts7[0] == draw.LEGEND_ESCAPE + "_under" and host7.info.legend_uids == [s7.uid, s7b.uid]
          and not any("underscore" in str(w.message) for w in rec7),
          f"legend：「_」開頭的 label 不被 matplotlib 剔除、uid 對應正確（{[t.replace(draw.LEGEND_ESCAPE, '') for t in texts7]}）")
    ia7 = Interactor(fig7.canvas, host7, toolbar=_ToolbarStub(), model=InteractorModel(st7.tips, st7.annotations))
    fig7.canvas.draw()
    axl7 = host7.info.ax_left
    check(ia7.add_tip(s7.uid, 45) is None and ia7.add_tip(s7.uid, 70) is None and len(st7.tips) == 0,
          "add_tip：NaN／inf 的點不釘（釘了整張圖會畫不出來）")
    t7 = ia7.add_tip(s7.uid, 10)
    px45, py45 = axl7.transData.transform((45.0, 0.0))
    i_near = draw.nearest_index(s7, axl7, px45, py45)
    fin7 = np.flatnonzero(np.isfinite(y7))
    pts7 = axl7.transData.transform(np.column_stack([np.arange(100.0)[fin7], y7[fin7]]))
    i_expect = int(fin7[int(np.argmin(np.hypot(pts7[:, 0] - px45, pts7[:, 1] - py45)))])
    check(t7 is not None and i_near == i_expect and np.isfinite(y7[i_near]) and not (40 <= i_near < 60),
          f"nearest_index：NaN 洞裡 → 像素距離最近的有限值點（{i_near}）")
    all_nan = Series("nan", np.arange(5.0), np.full(5, np.nan))
    check(draw.nearest_index(all_nan, axl7, px45, py45) == -1
          and ia7._nearest(s7b.uid, MouseEvent("button_press_event", fig7.canvas, px45, py45)) is not None,
          "nearest_index：整條都是 NaN → -1")
    fig7.canvas.draw()
    check(clipboard.figure_to_png_bytes(fig7)[:8] == b"\x89PNG\r\n\x1a\n", "有資料提示的圖（含 NaN／inf 的線）可以畫、可以存 PNG")
    d_bad, warn_bad = model.migrate_dict({"series": None, "annotations": None, "tips": None, "version": "abc",
                                          "style": "nope", "view": 3})
    check(d_bad["series"] == [] and d_bad["tips"] == [] and d_bad["version"] == model.FORMAT_VERSION
          and d_bad["style"] == "default" and isinstance(d_bad["view"], dict) and bool(warn_bad),
          "migrate_dict：null 清單、看不懂的版本、不存在的風格都能收")
    try:
        model.state_from_dict([1, 2])
        check(False, "state_from_dict：頂層不是物件要丟 ValueError")
    except ValueError:
        check(True, "state_from_dict：頂層不是物件 → ValueError")
    check(DataTip.from_dict({"offset": [5]}).offset == model.TIP_OFFSET_DEFAULT, "DataTip.from_dict：offset 長度不對 → 預設")
    e_step = Series("e", np.array([0.0]), np.zeros(0), kind="step")
    check(tuple(len(a) for a in e_step.plot_xy()) == (0, 0), "plot_xy：step 只有 1 個 x、沒有 y → 空")
    check(draw.wheel_notches(_E(float("nan"))) == 0, "wheel_notches：NaN → 0")
    check(draw.RenderInfo(ax_left=axl7).axes_for("right") is None, "RenderInfo.axes_for：沒有右軸 → None")
    st8 = FigureState()
    st8.add_series(Series("r", np.arange(10.0), np.arange(10.0) * 5, yaxis="right"))
    fig8 = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(fig8)
    info8 = draw.draw_state(fig8, st8)
    fig8.canvas.draw()
    check(info8.ax_right is not None and not any(t.get_visible() for t in info8.ax_left.get_yticklabels()),
          "draw_state：只有右軸有線 → 左軸刻度藏起來")

    # --- UndoStack ------------------------------------------------------------------------
    us = undo.UndoStack(limit=3)
    for i in range(5):
        us.push({"v": i}, f"step {i}", now=100.0 + i * 10)
    check(len(us) == 3 and us.peek_desc() == "step 4", "UndoStack：上限 3、最後描述")
    cur = {"v": 5}
    back = us.undo(cur)
    check(back == {"v": 4} and us.can_redo and us.redo({"v": 4}) == cur, "UndoStack：undo / redo")
    us.clear()
    us.push({"v": 0}, "slider", tag="slider", now=200.0)
    pushed = us.push({"v": 1}, "slider", tag="slider", now=201.0)
    pushed2 = us.push({"v": 2}, "slider", tag="slider", now=210.0)
    check(len(us) == 2 and pushed is False and pushed2 is True, "UndoStack：同 tag 2 秒內合併")
    check(us.discard_last() is True and len(us) == 1 and us.peek_desc() == "slider"
          and us.discard_last() is True and len(us) == 0 and us.discard_last() is False, "UndoStack：discard_last（Esc 取消拖曳用）")
    us.push({"v": "a"}, "a", now=300.0)
    us.push({"v": "b"}, "b", now=310.0)
    us.undo({"v": "c"})
    check(us.states() == [{"v": "a"}, {"v": "c"}] and us.can_redo, "UndoStack.states()：復原的在前、重做的在後（宿主查快照還用到什麼）")
    us.clear()
    check(us.states() == [], "UndoStack.states()：清空後沒有")
    arr = np.arange(3.0)
    st4 = FigureState()
    st4.add_series(Series("z", arr, arr))
    sn = st4.snapshot()
    check(sn["series"][0]["x"] is st4.series[0].x, "snapshot 共用陣列（不複製）")

    # --- clipboard ---------------------------------------------------------------------
    png = clipboard.figure_to_png_bytes(fig2)
    # --- 主題（docs/matlab-ui-spec.md 量到的值）與圖示 ---------------------------------------
    from . import theme as T, icons as I
    td, tl = T.TOKENS["dark"], T.TOKENS["light"]
    check(set(td) == set(tl) and len(td) > 30, "主題：dark／light 鍵集合一致")
    check(td["bg"] == "#212121" and td["input"] == "#121212" and td["text"] == "#d9d9d9" and td["border"] == "#7d7d7d"
          and td["strip"] == "#004073" and td["selected"] == "#616161" and td["tab"] == "#333333" and td["tab_selected"] == "#212121"
          and td["border3"] == "#a6a6a6", "主題 dark：uifigure 實測值（底 #212121、輸入 #121212、字 #d9d9d9、分頁 #333/#212121）")
    check(tl["bg"] == "#f5f5f5" and tl["input"] == "#ffffff" and tl["text"] == "#212121" and tl["selected"] == "#bfbfbf"
          and tl["strip"] == "#004073" and tl["tab"] == "#e6e6e6" and tl["tab_selected"] == "#f5f5f5", "主題 light：uifigure 實測值（底 #f5f5f5、字 #212121、分頁 #e6e6e6/#f5f5f5）")
    check(all(re.fullmatch(r"#[0-9a-f]{6}", v) for k, v in td.items() if k != "plot_style")
          and all(re.fullmatch(r"#[0-9a-f]{6}", v) for k, v in tl.items() if k != "plot_style"), "主題：所有色票都是 #rrggbb")
    check(td["plot_style"] in styles.STYLES and tl["plot_style"] in styles.STYLES, "主題：plot_style 指到存在的繪圖風格")
    # --- 1.0.0 外觀主題（Sony 風黑銀／深藍黑、Apple 風淺色／深色／深色·石墨橘／深色·純黑綠；audit/2026-11-01-skins/proposals.md） ------
    import copy as _copy
    _MATLAB_BEFORE, _MATLAB_DARK_BEFORE = _copy.deepcopy(styles.STYLES["matlab"]), _copy.deepcopy(styles.STYLES["matlab-dark"])
    for _n in ("sony-black", "sony-blue", "apple-light", "apple-dark", "apple-dark-graphite", "apple-dark-black"):          # 讀新風格、改它的副本，再比對 matlab／matlab-dark 沒被牽動
        _tmp = styles.get_style(_n); _tmp["colors"][0] = "#000000"; _tmp["grid"]["alpha"] = 0.0; _tmp["tip"]["fc"] = "#000000"
    names6 = ("dark", "light", "sony_black", "sony_blue", "apple_light", "apple_dark", "apple_dark_graphite", "apple_dark_black")    # 1.0.0 起八個
    check(tuple(T.THEMES) == names6 and all(set(T.TOKENS[n_]) == set(td) for n_ in names6),
          f"主題：八個主題（{', '.join(T.THEMES)}）的鍵集合都和 dark 一樣（{len(td)} 個鍵）")
    check(all(re.fullmatch(r"#[0-9a-f]{6}", v) for n_ in names6 for k, v in T.TOKENS[n_].items() if k != "plot_style"),
          "主題：八個主題的色票都是 #rrggbb")
    check([T.TOKENS[n_]["plot_style"] for n_ in names6] == ["matlab-dark", "matlab", "sony-black", "sony-blue", "apple-light", "apple-dark",
                                                            "apple-dark-graphite", "apple-dark-black"]
          and all(T.TOKENS[n_]["plot_style"] in styles.STYLES for n_ in names6), "主題：八個 plot_style 各指到存在的繪圖風格")
    check(T.RADIUS_PX == {"dark": 3, "light": 3, "sony_black": 1, "sony_blue": 3, "apple_light": 5, "apple_dark": 5,
                          "apple_dark_graphite": 5, "apple_dark_black": 5} and T.PX["radius"] == 3,
          "主題：圓角各自的值（MATLAB 3、Sony 黑銀 1、Sony 深藍黑 3、Apple 四個 5）；PX['radius'] 仍是 3")
    check(all(T.is_dark(T.TOKENS[n_]["bg"]) for n_ in ("dark", "sony_black", "sony_blue", "apple_dark", "apple_dark_graphite", "apple_dark_black"))
          and not any(T.is_dark(T.TOKENS[n_]["bg"]) for n_ in ("light", "apple_light")), "主題：深淺由視窗底色判斷（六深、兩淺）")
    # 「全部都做上去」（2026-11-01 19:4x，少一點藍）：Apple 淺色的強調色換 macOS 紫、沒有藍色鍵；兩個 Apple 深色變體＝apple_dark＋指定的覆蓋值
    _blue_ = ("#007aff", "#0a60ff", "#b3d7ff", "#d5e5fa", "#2773ff", "#0852d9")
    _al = T.TOKENS["apple_light"]
    check(_al["accent"] == _al["focus"] == "#af52de" and _al["strip_selected"] == _al["panel_header_sel"] == _al["link"] == "#8944ab"
          and _al["selected_focus"] == _al["toolbar_on"] == "#e7cbf5" and _al["selected"] == "#efdcf8"
          and _al["primary_hover"] == "#9850bd" and _al["primary_pressed"] == "#6e3689" and not set(_al.values()) & set(_blue_),
          "主題 apple_light：強調色＝macOS 淺色系統紫 #af52de、帶白字的面＝#8944ab、選取列淡紫；沒有留下系統藍的值")

    def _cr(a_, b_):                     # WCAG 對比
        def _l(h_):
            c_ = [int(h_[i_:i_ + 2], 16) / 255 for i_ in (1, 3, 5)]
            c_ = [x_ / 12.92 if x_ <= 0.04045 else ((x_ + 0.055) / 1.055) ** 2.4 for x_ in c_]
            return 0.2126 * c_[0] + 0.7152 * c_[1] + 0.0722 * c_[2]
        la_, lb_ = sorted((_l(a_), _l(b_)), reverse=True)
        return (la_ + 0.05) / (lb_ + 0.05)
    _white_on = {n_: min(_cr("#ffffff", T.TOKENS[n_][k_]) for k_ in ("strip_selected", "panel_header_sel"))
                 for n_ in ("apple_light", "apple_dark_graphite", "apple_dark_black")}
    _sel_txt = min(_cr(_al["text_selected"], _al[k_]) for k_ in ("selected", "selected_focus", "toolbar_on"))
    check(all(v_ >= 4.5 for v_ in _white_on.values()) and _sel_txt >= 7.0,
          f"對比：主要按鈕／被選面板的白字 ≥ 4.5:1（{ {k_: round(v_, 2) for k_, v_ in _white_on.items()} }）、Apple 淺色選取列的字 ≥ 7:1（{_sel_txt:.1f}）")
    _t2_ = {n_: round(_cr(T.TOKENS[n_]["text2"], T.TOKENS[n_]["bg"]), 2) for n_ in ("apple_light",)}
    check(_al["text2"] == "#636366" and _t2_["apple_light"] >= 4.5,
          f"對比（1.0.0 第 1 輪 B4）：Apple 淺色的次要字 text2 #636366 在視窗底 #ececec 上 ≥ 4.5:1（{_t2_}；以前 #6e6e73 只有 4.29）")
    _tabs_ = {n_: (T.TOKENS[n_]["bg"], T.TOKENS[n_]["strip"], T.TOKENS[n_]["strip_selected"]) for n_ in names6}
    check(all(b_ != s_ and b_ != c_ for b_, s_, c_ in _tabs_.values()) and T.TOKENS["apple_dark_black"]["strip"] == "#1c1c1e",
          f"主題：每個主題選中的分頁（＝內容區底 bg）和沒選中的分頁（strip／contextual 的 strip_selected）底色不同——看得出選了哪個分頁"
          f"（1.0.0 W100R1-1：純黑綠的分頁列以前是 #000000＝內容區；{ {k_: v_ for k_, v_ in _tabs_.items() if k_.startswith('apple_dark')} }）")
    _ad = T.TOKENS["apple_dark"]
    _gr_over = {"selected_focus": "#5a5a5e", "toolbar_on": "#48484a", "strip_hover": "#48484a", "strip_selected": "#636366", "panel_header_sel": "#636366",
                "focus": "#ff9f0a", "accent": "#ff9f0a", "link": "#ffb340", "primary_hover": "#7c7c80", "primary_pressed": "#48484a",
                "plot_style": "apple-dark-graphite"}
    _bk_over = {"bg": "#000000", "bg2": "#1c1c1e", "bg3": "#000000", "input": "#1c1c1e", "stripe": "#0e0e0f", "hover": "#2c2c2e", "selected": "#2c2c2e",
                "list_hover": "#3a3a3c", "toggle_on": "#2c2c2e", "strip": "#1c1c1e", "tab": "#1c1c1e", "tab_selected": "#000000", "border": "#3a3a3c",
                "border2": "#2c2c2e", "text": "#ffffff", "icon_fill": "#2c2c2e", "strip_icon_fill": "#2c2c2e", "selected_focus": "#1d5f2f",
                "toolbar_on": "#174d26", "strip_hover": "#2c2c2e", "strip_selected": "#24883d", "panel_header_sel": "#24883d", "focus": "#30d158",
                "accent": "#30d158", "link": "#4cd964", "primary_hover": "#2a9d47", "primary_pressed": "#1d6f33", "plot_style": "apple-dark-black"}
    check(T.TOKENS["apple_dark_graphite"] == {**_ad, **_gr_over} and T.TOKENS["apple_dark_black"] == {**_ad, **_bk_over}
          and _ad["accent"] == "#bf5af2" and T.TOKENS["apple_dark_black"]["accent"] == T.TOKENS["apple_dark_black"]["success"],
          "主題：Apple 深色·石墨橘／純黑綠＝apple_dark＋指定的覆蓋值（純黑綠的綠面 #248a3d 白字 4.40:1 → 壓暗成 #24883d）；Apple 深色本身仍是紫；純黑綠的強調色＝成功色")
    check(not T.is_dark(T.TOKENS["apple_light"]["strip"]) and all(T.is_dark(T.TOKENS[n_]["strip"]) for n_ in names6 if n_ != "apple_light")
          and T.TOKENS["apple_light"]["strip_text"] == T.TOKENS["apple_light"]["text"]
          and all(T.TOKENS[n_]["strip_text"] == "#ffffff" for n_ in names6 if n_ != "apple_light"),
          "主題：分頁列的字色跟分頁列深淺（Apple 淺色的淺灰分頁列用深色字，其餘白字）")
    check(td["strip_text"] == "#ffffff" and td["strip_text_disabled"] == "#9ec5e8" and td["strip_icon_fill"] == "#1a4f85"
          and td["strip_icon_fg2"] == "#c9e7ff" and td["primary_pressed"] == "#0b2f5c" and td["primary_hover"] == "#268cdd"
          and all(tl[k] == td[k] for k in ("strip_text", "strip_text_disabled", "strip_icon_fill", "strip_icon_fg2", "primary_pressed", "primary_hover")),
          "主題 dark／light：分頁列字色、停用字、分頁列圖示、主要按鈕按下／hover 的新鍵＝以前寫死的字面值（一個都沒變）")
    labels6 = ("深色", "淺色", "Sony 風（黑銀）", "Sony 風（深藍黑）", "Apple 風（淺色）", "Apple 風（深色）", "Apple 風（深色·石墨橘）", "Apple 風（深色·純黑綠）")
    check(T.theme_labels() == labels6 and all(T.theme_from_label(T.theme_label(n_)) == n_ for n_ in names6)
          and T.theme_from_label("沒有這個", "light") == "light" and T.theme_from_label("沒有這個", "bogus") == "dark" and T.theme_label("bogus") == "bogus",
          "主題：名稱↔介面名稱對照（八個；對不到回 default、不合法的 default 回 dark）")
    for n_ in ("sony_black", "sony_blue", "apple_light", "apple_dark", "apple_dark_graphite", "apple_dark_black"):
        tk_ = T.TOKENS[n_]
        st_ = styles.get_style(tk_["plot_style"])
        base_ = styles.STYLES["matlab" if n_ == "apple_light" else "matlab-dark"]
        # 座標區底：提案的 plot_axes_face——三個主題＝輸入框底；Apple 深色（和石墨橘）是 #141414（比 input #181818 再深一階，對應 MATLAB #121212
        # 在 #212121 底下）；純黑綠是純黑 #000000（圖例底 #1c1c1e＝輸入框底）
        want_ax_ = {"apple_dark": "#141414", "apple_dark_graphite": "#141414", "apple_dark_black": "#000000"}.get(n_, tk_["input"].replace("#ffffff", "white"))
        want_lg_ = tk_["input"] if n_ == "apple_dark_black" else want_ax_
        check(st_["name"] == tk_["plot_style"] and st_["fig_face"] == tk_["bg"] and st_["axes_face"] == want_ax_
              and st_["tip"]["ec_selected"] == tk_["accent"] and st_["tip"]["fc"] == st_["axes_face"] and st_["legend"]["facecolor"] == want_lg_
              and st_["lw"] == base_["lw"] and st_["box"] == base_["box"] and st_["tick_dir"] == base_["tick_dir"] and st_["fonts"] == base_["fonts"]
              and st_["title"] == base_["title"] and st_["grid"]["lw"] == base_["grid"]["lw"],
              f"繪圖風格 {tk_['plot_style']}：figure 底＝視窗底、座標區底＝提案的 plot_axes_face（{want_ax_}）、選中提示框線＝強調色；線寬／Box／刻度方向／字型照 MATLAB")
    _sb_ = styles.STYLES["sony-black"]["colors"]
    _md_ = styles.PALETTE_MATLAB_DARK
    check(_sb_[0] == "#f27a1a" == styles.STYLES["sony-black"]["tip"]["ec_selected"] and len(_sb_) == 7 and len(set(_sb_)) == 7
          and set(_sb_[1:]) == set(_md_) - {"#f57729"} and _sb_[-1] == "#268cdd" and min(_cr(c_, "#121110") for c_ in _sb_) >= 4.5
          and styles.STYLES["sony-blue"]["colors"][0] == "#2e8cff" and len(styles.STYLES["sony-blue"]["colors"]) == 7
          and styles.STYLES["apple-dark"]["colors"][0] == "#bf5af2"
          and styles.STYLES["apple-light"]["colors"] == ["#8944ab", "#c93400", "#248a3d", "#d30f45", "#008299", "#3634a3", "#7f6545", "#007aff"]
          and styles.STYLES["apple-light"]["grid"] == {"ls": "-", "alpha": 1.0, "color": "#d2d2d7", "lw": 0.5}
          and styles.STYLES["apple-dark-graphite"]["colors"] == ["#ff9f0a", "#e5e5ea", "#30d158", "#ff375f", "#bf5af2", "#ffd60a", "#64d2ff"]
          and styles.STYLES["apple-dark-black"]["colors"] == ["#30d158", "#ff9f0a", "#ff375f", "#ffd60a", "#bf5af2", "#64d2ff", "#ac8e68"]
          and styles.STYLES["apple-dark-black"]["fig_face"] == "#000000" and styles.STYLES["apple-dark-black"]["legend"]["facecolor"] == "#1c1c1e",
          "繪圖風格：第 1 條線——Sony 黑銀 α 橘（其餘取 R2025a 深色 ColorOrder、沒有第二個橘、藍放最後、在 #121110 上 ≥4.5:1）、Sony 深藍黑 PlayStation 藍、"
          "Apple 淺色無障礙系統紫（系統藍放最後）、Apple 深色紫、石墨橘系統橘、純黑綠系統綠；Apple 淺色格線不透明髮絲")
    check(styles.get_style("matlab") == _MATLAB_BEFORE and styles.get_style("matlab-dark") == _MATLAB_DARK_BEFORE,
          "繪圖風格：加了六個新風格後 matlab／matlab-dark 的內容沒變（新風格是 deepcopy，不是共用 dict）")
    fig9s = Figure(figsize=(4, 3)); st9s = model.FigureState(style="sony-blue")
    st9s.add_series(model.Series("a", np.arange(10.0), np.arange(10.0)))
    info9s = draw.draw_state(fig9s, st9s)
    check(tuple(round(c, 3) for c in fig9s.get_facecolor()[:3]) == (0.059, 0.086, 0.129)
          and info9s.ax_left.title.get_color() == "#e6ecf5" and info9s.ax_left.get_lines()[0].get_color() == "#2e8cff",
          "draw_state(sony-blue)：圖底 #0f1621、標題 #e6ecf5、第 1 條線 PlayStation 電藍")
    check(T.mix("#000000", "#ffffff", 0.5) == "#808080" and T.is_dark("#212121") and not T.is_dark("#f5f5f5"), "theme.mix / is_dark")
    md = styles.get_style("matlab-dark")
    check(md["fig_face"] == "#212121" and md["axes_face"] == "#121212" and md["text_color"] == "#d9d9d9"
          and md["colors"][0] == "#268cdd" and md["grid"]["alpha"] == 0.25 and md["legend"]["facecolor"] == "#121212",
          "matlab-dark 風格：figure(Theme='dark') 實測值")
    fig9 = Figure(figsize=(4, 3)); st9 = model.FigureState(style="matlab-dark")
    st9.add_series(model.Series("a", np.arange(10.0), np.arange(10.0)))
    info9 = draw.draw_state(fig9, st9)
    check(tuple(round(c, 3) for c in fig9.get_facecolor()[:3]) == (0.129, 0.129, 0.129)
          and info9.ax_left.title.get_color() == "#d9d9d9" and info9.legend.get_texts()[0].get_color() == "#d9d9d9",
          "draw_state(matlab-dark)：圖底、標題、圖例文字顏色")
    check(len(I.names()) >= 40 and "home" in I.names() and "datatip" in I.names(), f"圖示清單（{len(I.names())} 個）")
    check({"measure", "trans_prev", "trans_next", "normalize"} <= set(I.names()), "圖示：量測、上一個／下一個轉態、Normalize Y")
    check({"constellation", "iq_magphase", "plot_type"} <= set(I.names()) and all(I.render(n_, 16) is not None or not I.HAVE_PIL
                                                                                 for n_ in ("constellation", "iq_magphase", "plot_type")),
          "圖示：星座圖、I/Q 幅度／相位、繪圖類型")
    check({"dcursors", "dcursor_center", "tip_export", "tip_fields"} <= set(I.names()), "圖示：資料游標、游標移到視圖、匯出提示、提示內容")
    figd = Figure(figsize=(4, 3), dpi=100); FigureCanvasAgg(figd); axd = figd.add_subplot(111)
    xd = np.arange(6000.0); yd = np.sin(xd / 50.0); axd.plot(xd, yd); axd.set_xlim(0, 6000); figd.canvas.draw()
    pxd, pyd = axd.transData.transform((xd[1000], yd[1000]))
    nv = draw.nearest_vertex(xd, yd, axd, pxd, pyd, x_sorted=True)
    pts_all = axd.transData.transform(np.column_stack([xd, yd]))
    best = int(np.argmin(np.hypot(pts_all[:, 0] - pxd, pts_all[:, 1] - pyd)))
    check(nv == best, f"nearest_vertex：一個像素 ~15 個樣本時仍是像素最近的頂點（{nv} vs {best}）")
    if I.HAVE_PIL:
        pngs = [I.png_bytes(n, 16) for n in I.names()]
        check(all(b[:8] == b"\x89PNG\r\n\x1a\n" for b in pngs), "所有圖示都能畫成 16px PNG")
        im = I.render("home", 24, {"fg": "#ff0000"})
        check(im.size == (24, 24) and im.getbbox() is not None, "圖示可換色、24px 非空")
    else:
        check(I.render("home") is None and I.get_icon("home") is None, "沒有 Pillow：圖示回 None（按鈕退回純文字）")
    # --- i18n -------------------------------------------------------------------------
    from . import i18n
    import glob as _glob
    prev_lang = i18n.get_language()
    try:
        check(i18n.normalize("en-US") == "en" and i18n.normalize("zh_TW") == "zh" and i18n.normalize("English") == "en"
              and i18n.normalize(None) == "zh" and i18n.normalize("fr") == "zh", "i18n.normalize：別名與未知語言")
        i18n.set_language("en")
        check(i18n.get_language() == "en" and i18n.tr("偏好設定") == "Preferences" and i18n.tr("") == "", "i18n.tr：英文翻譯")
        check(i18n.tr("這個鍵不存在 xyz") == "這個鍵不存在 xyz", "i18n.tr：沒有翻譯回原文")
        i18n.set_language("zh")
        check(i18n.tr("偏好設定") == "偏好設定", "i18n：切回中文")
        here = os.path.dirname(os.path.abspath(__file__))
        srcs = [p_ for p_ in _glob.glob(os.path.join(here, "*.py"))
                if os.path.basename(p_) not in ("selftest.py",) and not os.path.basename(p_).startswith("i18n")]
        srcs.append(os.path.join(os.path.dirname(here), "signal_viewer.py"))
        srcs += sorted(_glob.glob(os.path.join(os.path.dirname(here), "dsv_*.py")))   # DSV 的模組（例如 dsv_preprocess 的面板文字）也有 tr()
        miss = i18n.missing_keys("en", srcs)
        check(not miss, f"i18n：原始碼裡每個 tr() 的鍵都有英文（缺 {len(miss)}：{miss[:5]}）")
        bad = i18n.placeholder_mismatches("en")
        check(not bad, f"i18n：英文翻譯的 {{佔位符}} 與原文一致（錯 {len(bad)}：{bad[:5]}）")
        cat = i18n.catalog("en")
        cjk = [k for k, v in cat.items() if re.search(r"[\u4e00-\u9fff]", v)]
        check(not cjk, f"i18n：英文翻譯裡沒有中文（{len(cjk)}：{cjk[:5]}）")
        # 1.0.0 第 3 輪（測試強度 R08／R09；決定檔 11-02 00:4x DS2「英文 tr 與 README B3 段同步」）：B3／U13 問句三個分支（這版留的備份、
        # 最後一次工作留的備份、比它新的備份）的「舊版不認得的設定」都列外觀主題——英文也是，不只 GUI 測試走到的那一個分支
        ds2_ = {k: v for k, v in cat.items() if "外觀主題（Sony／Apple 風）" in k}
        ds2_bad = [k[:24] for k, v in ds2_.items() if "the Sony / Apple interface theme" not in v]
        check(len(ds2_) == 3 and not ds2_bad,
              f"i18n：舊版開過的問句三個分支的英文都列 the Sony / Apple interface theme（{len(ds2_)} 條；缺的 {ds2_bad}）")
        # 每個英文翻譯檔都要在 i18n_en 的合併清單（不在＝那批字串永遠是中文）和 _pyinstaller_hints（不在＝打包後選 English 仍是中文）裡；
        # 兩個分支各加一個翻譯檔、合併時清單衝突，最容易漏掉一邊（2026-10-27 合併 0.9.9 進第三批：batch3／batch4 與 fix3）
        import inspect as _inspect
        parts_files = sorted(os.path.basename(p_)[len("i18n_en_"):-3] for p_ in _glob.glob(os.path.join(here, "i18n_en_*.py")))
        with open(os.path.join(here, "i18n_en.py"), encoding="utf-8") as f_:
            en_src = f_.read()
        m_parts = re.search(r"for _part in \(([^)]*)\)", en_src)
        merged = re.findall(r'"([A-Za-z0-9_]+)"', m_parts.group(1)) if m_parts else []
        hinted = set(re.findall(r"\bi18n_en(?:_[A-Za-z0-9_]+)?\b", _inspect.getsource(i18n._pyinstaller_hints)))
        miss_parts = [p_ for p_ in parts_files if p_ not in merged]
        miss_hint = [f"i18n_en_{p_}" for p_ in parts_files if f"i18n_en_{p_}" not in hinted] + ([] if "i18n_en" in hinted else ["i18n_en"])
        check(bool(parts_files) and not miss_parts and not miss_hint and len(merged) == len(set(merged)),
              f"i18n：每個英文翻譯檔（{len(parts_files)} 個）都在 i18n_en 的合併清單與 _pyinstaller_hints 裡（缺 {miss_parts} {miss_hint}）")
    finally:
        i18n.set_language(prev_lang)
    check(png[:8] == b"\x89PNG\r\n\x1a\n", "figure_to_png_bytes：PNG 檔頭")
    win = clipboard.clipboard_command_for("win32", r"C:\tmp\it's.png")
    check(win is not None and "-STA" in win and "it''s.png" in win[-1] and "SetImage" in win[-1], "clipboard_command_for：Windows PowerShell 與引號")
    mac = clipboard.clipboard_command_for("darwin", '/tmp/a"b.png')
    check(mac[0] == "osascript" and "PNGf" in mac[2] and '\\"' in mac[2] and "tell application" not in mac[2],
          "clipboard_command_for：macOS osascript 不用 tell application")
    # MATLAB 座標區工具列 Export：Copy as image（PNG）／Copy as vector graphic（PDF；macOS 剪貼簿類別 «class PDF »）
    macv = clipboard.clipboard_command_for("darwin", "/tmp/a.pdf", "pdf")
    check(macv[0] == "osascript" and "«class PDF »" in macv[2] and "tell application" not in macv[2],
          "clipboard_command_for(pdf)：macOS 放 «class PDF »")
    check(clipboard.clipboard_command_for("win32", r"C:\tmp\a.pdf", "pdf") is None,
          "clipboard_command_for(pdf)：Windows 沒有向量格式 → None（向量複製停用）")
    _cap = {}
    _orig_pdf = clipboard.copy_pdf_to_clipboard

    def _fake_pdf(path):
        with open(path, "rb") as fh:
            _cap["head"] = fh.read(5)
        return True, "fake pdf"
    clipboard.copy_pdf_to_clipboard = _fake_pdf
    _orig_sup = clipboard.clipboard_vector_supported
    clipboard.clipboard_vector_supported = lambda: True      # 測產生 PDF 的流程本身（Windows 平常不支援、會提早回傳）
    try:
        okv, msgv = clipboard.copy_figure_to_clipboard(fig2, content="vector")
    finally:
        clipboard.copy_pdf_to_clipboard = _orig_pdf
        clipboard.clipboard_vector_supported = _orig_sup
    check(okv and _cap.get("head") == b"%PDF-", "copy_figure_to_clipboard(content='vector')：產生 PDF 再放剪貼簿")
    # 剪貼簿放不了向量圖的系統（Windows）：按鈕／選單停用、tooltip 說明，程式直接呼叫也不留暫存 PDF
    _orig_sup = clipboard.clipboard_vector_supported
    _n_tmp0 = len([f for f in os.listdir(tempfile.gettempdir()) if f.startswith(f"plotkit_clip_{os.getpid()}_")])
    clipboard.clipboard_vector_supported = lambda: False
    try:
        okw, msgw = clipboard.copy_figure_to_clipboard(fig2, content="vector")
        st_w, tip_w = clipboard.vector_copy_state(), clipboard.vector_copy_tip("T")
    finally:
        clipboard.clipboard_vector_supported = _orig_sup
    _n_tmp1 = len([f for f in os.listdir(tempfile.gettempdir()) if f.startswith(f"plotkit_clip_{os.getpid()}_")])
    check(not okw and st_w == "disabled" and tip_w.startswith("T") and len(tip_w) > 1 and _n_tmp1 == _n_tmp0,
          f"不支援向量剪貼簿：按鈕／選單 disabled、tooltip 補說明、不產生暫存 PDF（{msgw}）")
    check(clipboard.vector_copy_state() == ("normal" if clipboard.clipboard_vector_supported() else "disabled"),
          f"vector_copy_state 跟著平台（{sys.platform}：{clipboard.vector_copy_state()}）")
    _w13_clip_temp_checks(check, fig2)                       # 0.9.14 Windows W13：複製圖的暫存檔（agent W 加的一段）

    # --- 參考線／文字標註照 MATLAB R2025a（Agg）：xline 標籤轉 90° 掛線右側、離上緣 5 px；yline 標籤靠右端在線上方；
    #     線預設 '-'、0.5、alpha 0.7；字 10 pt；線出了範圍標籤一起不畫 -------------------------------------------
    a0 = Annotation(kind="xline", value=1.0)
    check(a0.lw == 0.5 and a0.ls == "-" and a0.alpha == 0.7 and "alpha" in a0.to_dict(), "Annotation 預設：線寬 0.5、'-'、alpha 0.7（MATLAB ConstantLine）")
    old = {k: v for k, v in a0.to_dict().items() if k != "alpha"}
    check(Annotation.from_dict(old).alpha == 1.0 and Annotation.from_dict(dict(old, alpha=None)).alpha == 1.0
          and Annotation.from_dict(a0.to_dict()).alpha == 0.7,
          "Annotation.from_dict：舊檔沒有 alpha 鍵＝當時的不透明 1.0（新插入的才是 0.7）")
    figr = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(figr)
    axr = figr.add_axes((0.1, 0.1, 0.8, 0.8))
    axr.set_xlim(0, 10)
    axr.set_ylim(0, 10)
    stl = styles.get_style("matlab")
    artx = draw.draw_annotation(axr, Annotation(kind="xline", value=5.0, text="xlab", color="#ff0000"), stl)
    arty = draw.draw_annotation(axr, Annotation(kind="yline", value=5.0, text="ylab", color="#ff0000"), stl)
    tx, ty = artx._pk_label, arty._pk_label
    check(tx.get_rotation() == 90 and tx.get_ha() == "right" and tx.get_va() == "top" and tx.get_fontsize() == 10
          and artx.get_alpha() == 0.7 and artx.get_linestyle() == "-" and artx.get_linewidth() == 0.5,
          "xline：標籤轉 90°、ha right／va top、10 pt；線 '-'、0.5、alpha 0.7")
    check(ty.get_rotation() == 0 and ty.get_ha() == "right" and ty.get_va() == "bottom" and ty.get_fontsize() == 10,
          "yline：標籤水平、ha right／va bottom、10 pt")
    figr.canvas.draw()
    rr = figr.canvas.get_renderer()
    bx, by = tx.get_window_extent(rr), ty.get_window_extent(rr)
    lx5 = axr.transData.transform((5.0, 5.0))
    gap_line = 2.0 + 0.5 / 2 * 100 / 72
    check(abs((bx.x0 - lx5[0]) - gap_line) < 1.0 and abs((axr.bbox.y1 - bx.y1) - 5.0) < 1.0,
          f"xline 標籤：離線 2 px＋線寬一半、離上緣 5 px（{bx.x0 - lx5[0]:.2f}、{axr.bbox.y1 - bx.y1:.2f}）")
    check(abs((axr.bbox.x1 - by.x1) - 5.0) < 1.0 and abs((by.y0 - lx5[1]) - gap_line) < 1.0,
          f"yline 標籤：離右緣 5 px、在線上方 2 px＋線寬一半（{axr.bbox.x1 - by.x1:.2f}、{by.y0 - lx5[1]:.2f}）")

    def _red_px():
        figr.canvas.draw()
        buf = np.asarray(figr.canvas.buffer_rgba())
        return int(np.sum((buf[..., 0] > 200) & (buf[..., 1] < 80) & (buf[..., 2] < 80)))
    check(_red_px() > 50, "參考線在範圍內：線與標籤都畫")
    axr.set_xlim(10, 20)
    axr.set_ylim(10, 20)
    check(_red_px() == 0, "參考線出了 XLim／YLim：線和標籤都不畫（MATLAB 實測，標籤不會浮在座標區外）")
    axr.set_xlim(0, 5.0)
    axr.set_ylim(0, 10)
    figr.canvas.draw()
    bx2 = tx.get_window_extent(figr.canvas.get_renderer())
    check(tx.get_visible() and bx2.x0 > axr.bbox.x1 - 1, "線在邊上（範圍內）：標籤照畫、可以伸出座標區（MATLAB 不裁切）")
    figt = Figure(dpi=100)
    FigureCanvasAgg(figt)
    axt = figt.add_subplot(111)
    tt = draw.draw_annotation(axt, Annotation(kind="text", x=0.5, y=0.5, text="t"), stl)
    check(tt.get_fontsize() == 10, "文字標註預設 10 pt（MATLAB text FontSize 10）")

    # --- 資料提示照 MATLAB R2025a（Agg）：數值格式、命中門檻、hover 暫時提示、外觀、放哪一角、視圖改變 ---------------
    from matplotlib.colors import to_hex as _hex
    fm_cases = {32123456: "32123500", 1234567.89: "1234570", 2 ** 31: "2147480000", 123456789012345: "123457000000000",
                0.0009463000877: "0.0009463", 1 / 3: "0.333333", 1.23456789e-05: "1.23457e-05", 9.9e-05: "9.9e-05",
                1e-06: "1e-06", 999999999999999.9: "1e+15", 0.0001234: "0.0001234", 999999.95: "1000000",
                123456.4999: "123456", 1.000001: "1", -0.0: "0", 1e-100: "1e-100", 1e+100: "1e+100",
                float("nan"): "NaN", 2.5: "2.5", -7: "-7"}
    bad_fm = [(v, draw.fmt_matlab(v), want) for v, want in fm_cases.items() if draw.fmt_matlab(v) != want]
    check(not bad_fm, f"fmt_matlab：MATLAB 'auto' 格式（6 位有效、<1e-4 或 ≥1e15 用指數）（錯：{bad_fm[:4]}）")
    check(draw.format_tip_text("I", 625, 0.5, "us") == "I\nX 625 us\nY 0.5", "format_tip_text：名稱＋「X 值 單位」「Y 值」")
    st4 = FigureState()
    sh = st4.add_series(Series("h", np.arange(50.0), np.full(50, 5.0)))
    fig4 = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(fig4)
    host4 = _RecHost(st4, fig4)
    ax4 = host4.info.ax_left
    ax4.set_xlim(0, 49)
    ax4.set_ylim(0, 10)
    ia4 = Interactor(fig4.canvas, host4, toolbar=_ToolbarStub(), model=InteractorModel(st4.tips, st4.annotations))
    fig4.canvas.draw()
    ln4 = host4.info.lines[sh.uid]
    tol4 = draw.PICK_TOL_PX + 0.5 * ln4.get_linewidth() * 100 / 72.0
    hx, hy = ax4.transData.transform((20.0, 5.0))

    def _mv(x, y):
        ia4.on_motion(MouseEvent("motion_notify_event", fig4.canvas, x, y))

    def _hits(dy):
        return ia4.hit_test(MouseEvent("button_press_event", fig4.canvas, hx, hy + dy, button=1)).kind == "line"
    check(draw.PICK_TOL_PX == 2.0 and _hits(0) and _hits(2) and _hits(-2) and not _hits(math.ceil(tol4) + 1) and not _hits(6),
          f"命中門檻：線 ±2 px＋線寬一半（{tol4:.2f} px；舊的 pickradius 5 點≈7 px 不再算）")
    # 顯示縮放（Windows 150%：device_pixel_ratio=1.5）：±2 px 是邏輯像素 → 事件的實體像素要乘 dpr（線寬那半已隨 dpi 放大）
    fig5 = Figure(figsize=(6, 4), dpi=100)
    FigureCanvasAgg(fig5)
    ax5 = fig5.add_subplot()
    ln5, = ax5.plot(np.arange(50.0), np.full(50, 5.0), lw=1.0)
    ax5.set_xlim(0, 49)
    ax5.set_ylim(0, 10)
    fig5.canvas._set_device_pixel_ratio(1.5)
    fig5.canvas.draw()
    half5 = 0.5 * ln5.get_linewidth() * fig5.dpi / 72.0
    tol5 = draw.PICK_TOL_PX * 1.5 + half5
    hx5, hy5 = ax5.transData.transform((20.0, 5.0))
    k5 = math.floor(tol5)                                  # MouseEvent 的座標是整數像素：tol 4.04 → 4 px 命中、5 px 不中

    def _hits5(dy):
        return draw.hit_test_lines([ln5], MouseEvent("button_press_event", fig5.canvas, hx5, hy5 + dy, button=1)) is ln5
    check(fig5.dpi == 150 and float(hy5).is_integer() and _hits5(k5) and _hits5(-k5) and not _hits5(k5 + 1)
          and k5 > draw.PICK_TOL_PX + half5,
          f"命中門檻在 dpr 1.5：±2 邏輯 px＝±3 實體 px＋線寬一半（{tol5:.2f} 實體 px），和預設模式拖曳門檻一樣乘 dpr")
    ia4.tips_enabled = True
    n_calls = len(host4.calls)
    _mv(hx, hy + 1)
    h = ia4.hover_tip
    check(h is not None and h["index"] == 20 and h["mk"].get_visible() and not h["ann"].get_visible()
          and not st4.tips and not ia4.tip_artists and len(host4.calls) == n_calls,
          "hover：游標到線上 → 頂點標記、框還沒出現（200 ms linger）、不進模型／undo")
    ia4._hover_linger()
    check(h["ann"].get_visible() and h["ann"].get_text() == host4.tip_text(sh.uid, 20, 20.0, 5.0),
          f"hover：停 200 ms → 暫時提示框（內容同釘住的：{h['ann'].get_text()!r}）")
    n_draw4 = []
    cid4 = fig4.canvas.mpl_connect("draw_event", lambda e: n_draw4.append(1))
    _mv(ax4.transData.transform((21.0, 5.0))[0], hy)
    h2 = ia4.hover_tip
    check(h2 is not None and h2["index"] == 21 and not h2["ann"].get_visible() and h["ann"] not in ax4.texts,
          "hover：移到隔壁頂點 → 標記跟著換、框先收掉再 linger")
    check(not n_draw4 and h2["mk"].get_animated() and h2["ann"].get_animated(),
          "hover：換頂點只 blit 暫時提示（animated），不整張重畫（大檔全幅整張重畫要好幾百 ms）")
    fig4.canvas.mpl_disconnect(cid4)
    _mv(hx, hy + 30)
    check(ia4.hover_tip is None and h2["ann"] not in ax4.texts and h2["mk"] not in ax4.lines, "hover：離開線 → 收掉")
    _mv(hx, hy)
    ia4.on_scroll(MouseEvent("scroll_event", fig4.canvas, hx, hy + 30, step=1))
    check(ia4.hover_tip is None, "hover：滾輪 → 收掉")
    ia4.restore_view()
    ax4.set_xlim(0, 49)
    ax4.set_ylim(0, 10)
    fig4.canvas.draw()
    ia4.toolbar.mode = "pan/zoom"
    _mv(hx, hy)
    check(ia4.hover_tip is None, "hover：工具列模式開著不出")
    ia4.toolbar.mode = ""
    ia4.tips_enabled = False
    _mv(hx, hy)
    check(ia4.hover_tip is None, "hover：資料提示關著不出")
    ia4.tips_enabled = True
    _mv(hx, hy)
    ia4.on_press(MouseEvent("button_press_event", fig4.canvas, hx, hy, button=1))
    check(ia4.hover_tip is None, "hover：按下 → 收掉")
    ia4.on_release(MouseEvent("button_release_event", fig4.canvas, hx, hy, button=1))
    check(len(st4.tips) == 1 and st4.tips[0].index == 20, "hover 後點一下才釘住")
    t_a = st4.tips[0]
    ann_a, mk_a = ia4.tip_artists[t_a.id]
    bp = ann_a.get_bbox_patch()
    check(type(bp.get_boxstyle()).__name__ == "Square" and ann_a.arrow_patch is None and ann_a.get_fontsize() == 10
          and _hex(bp.get_facecolor()) == _hex(styles.get_style(st4.style)["axes_face"]) and close(bp.get_linewidth(), 1.0)
          and _hex(mk_a.get_markeredgecolor()) == "#ffffdc" and mk_a.get_markersize() == 5.0,
          "資料提示外觀：方框、沒有連線、10 pt、框底＝座標區底色、實心點邊 #ffffdc")
    check(styles.get_style("matlab-dark")["tip"]["fc"] == styles.get_style("matlab-dark")["axes_face"] == "#121212",
          "深色主題：提示框底＝座標區底色 #121212")
    check(t_a.offset == model.TIP_OFFSET_DEFAULT, f"Location auto：中間的點 → 右上（offset={t_a.offset}）")
    ex4, ey4 = ax4.transData.transform((47.0, 5.0))
    ia4.on_press(MouseEvent("button_press_event", fig4.canvas, ex4, ey4, button=1))
    ia4.on_release(MouseEvent("button_release_event", fig4.canvas, ex4, ey4, button=1))
    t_b = st4.tips[-1]
    check(len(st4.tips) == 2 and t_b.index == 47 and t_b.offset[0] < 0 < t_b.offset[1],
          f"Location auto：靠右的點 → 左上 northwest（offset={t_b.offset}）")
    ann_b = ia4.tip_artists[t_b.id][0]
    check(_hex(ann_b.get_bbox_patch().get_edgecolor()) == "#268cdd" and _hex(bp.get_edgecolor()) == "#7d7d7d",
          "選取＝框線藍 #268cdd、其他 #7d7d7d")
    t_b.offset = (20.0, 12.0)                       # 拖過的＝手動（LocationMode manual），視圖改變不重擺
    ann_b.xyann = t_b.offset
    ax4.set_ylim(0, 5.05)
    check(t_a.offset[0] > 0 > t_a.offset[1] and t_b.offset == (20.0, 12.0),
          f"視圖改變：點貼近上緣 → 自動的改右下 southeast（{t_a.offset}）、手動的不動")
    ax4.set_ylim(0, 10)
    check(t_a.offset == model.TIP_OFFSET_DEFAULT, "視圖還原 → 回右上")
    ax4.set_xlim(25, 49)
    fig4.canvas.draw()
    bba = ann_a.get_bbox_patch().get_window_extent(fig4.canvas.get_renderer())
    check(not ann_a.get_visible() and not mk_a.get_visible()
          and ia4._hit_floating(MouseEvent("button_press_event", fig4.canvas, (bba.x0 + bba.x1) / 2, (bba.y0 + bba.y1) / 2)) is None,
          "資料點在 XLim 外 → 整個提示不畫、也點不到")
    ax4.set_xlim(0, 49)
    check(ann_a.get_visible() and mk_a.get_visible(), "回到範圍內 → 再畫")

    # --- Interactor.set_xlim：程式改 x 範圍（DSV 的上一個／下一個轉態）也進 nav stack、記原始視圖、通知 host -----------------
    st10 = FigureState()
    st10.add_series(Series("t", np.arange(100.0), np.arange(100.0) % 7))
    fig10 = Figure(figsize=(5, 3), dpi=100)
    FigureCanvasAgg(fig10)
    host10 = _RecHost(st10, fig10)
    ax10 = host10.info.ax_left
    ax10.set_xlim(0, 99)
    nav10 = _NavStub()
    ia10 = Interactor(fig10.canvas, host10, toolbar=nav10, model=InteractorModel(st10.tips, st10.annotations))
    fig10.canvas.draw()
    ia10.set_xlim(ax10, 40.0, 60.0, draw=False)
    check(tuple(ax10.get_xlim()) == (40.0, 60.0) and nav10.pushes == 2 and ("view",) in host10.calls and ia10.has_home(),
          f"Interactor.set_xlim：x 範圍改成 40..60、nav stack 推了前後兩筆（{nav10.pushes}）、host.on_view_change、記下原始視圖")

    # --- 量測游標（批次 B，組 7：Time Scope／Signal Analyzer 的 Data Cursors）---------------------------------------------
    from . import cursors as C
    check(C.cursor_count("none") == 0 and C.cursor_count("one") == 1 and C.cursor_count("two") == 2 and C.cursor_count("zz") == 0,
          "cursor_count：none／one／two")
    check(C.default_positions(0, 100, "one") == [50.0] and C.default_positions(100, 0, "two") == [25.0, 75.0]
          and C.default_positions(0, 1, "none") == [], "default_positions：一條＝中央、兩條＝中央 ±1/4（範圍順序不拘）")
    check(C.parse_positions("1.5, x, 3") == [1.5, 3.0] and C.parse_positions("nan,inf") == [] and C.parse_positions([2, "4"]) == [2.0, 4.0]
          and C.parse_positions(C.format_positions([0.1, 1e-9])) == [0.1, 1e-9], "parse／format_positions：壞值略過、往返精確")
    check(C.snap_to_grid(3.4, 1.0, 0.5, 10) == 3.5 and C.snap_to_grid(-9, 1.0, 0.5, 10) == 1.0 and C.snap_to_grid(99, 1.0, 0.5, 10) == 5.5
          and C.snap_to_samples([0, 1, 4, 9], 2.4) == 1.0 and C.snap_to_samples([0, 1, 4, 9], 2.6) == 4.0,
          "snap_to_grid／snap_to_samples：最近的樣本，超出範圍夾到頭尾")
    check(C.drag_positions([10, 20], 0, 12) == [12.0, 20.0] and C.drag_positions([10, 20], 1, 25, lock=True) == [15.0, 25.0],
          "drag_positions：只動一條／鎖定間距兩條一起動")
    st11 = FigureState()
    st11.add_series(Series("ramp", np.arange(200.0), np.arange(200.0)))
    st11.add_series(Series("flat", np.arange(200.0), np.full(200, 100.0)))
    fig11 = Figure(figsize=(6, 3), dpi=100)
    FigureCanvasAgg(fig11)
    host11 = _RecHost(st11, fig11)
    ax11 = host11.info.ax_left
    ax11.set_xlim(0, 199)
    ia11 = Interactor(fig11.canvas, host11, model=InteractorModel(st11.tips, st11.annotations))
    ia11.tips_enabled = True
    moves, rels = [], []
    dc = C.DataCursors(fig11.canvas, on_move=moves.append, on_release=rels.append)
    ia11.cursors = dc
    dc.set_mode("two", view=ax11.get_xlim(), draw=False)
    dc.attach([ax11], styles.get_style("default"))
    fig11.canvas.draw()
    check(dc.active and dc.positions() == [49.75, 149.25] and len(dc.lines) == 2 and len(dc.labels) == 2
          and [t.get_text() for t in dc.labels] == ["1", "2"], f"DataCursors：兩條、標 1／2、放在視圖中央 ±1/4（{dc.positions()}）")
    xl_before = ax11.get_xlim()
    cx = float(ax11.transData.transform((dc.xs[0], 0))[0])
    cy = float(ax11.transData.transform((dc.xs[0], 100.0))[1])       # 「flat」那條線也在這裡：游標優先
    ev = MouseEvent("button_press_event", fig11.canvas, cx + 2, cy, button=1)
    hit = ia11.hit_test(ev)
    far = ia11.hit_test(MouseEvent("button_press_event", fig11.canvas, cx + 15, cy, button=1))
    check(hit.kind == "cursor" and hit.id == 0 and far.kind == "line", f"hit_test：游標線 ±4 px 內優先於線條（{hit.kind}；遠一點＝{far.kind}）")
    ia11.on_press(ev)
    ia11.on_motion(MouseEvent("motion_notify_event", fig11.canvas, cx + 5, cy))      # 不用拖滿 10 px
    check(ia11.dragging and dc.dragging and moves, "按住游標：一動就開始拖（不等 10 px 門檻）")
    cx2 = float(ax11.transData.transform((100.0, 0))[0])
    ia11.on_motion(MouseEvent("motion_notify_event", fig11.canvas, cx2 + 2, cy))
    ia11.on_release(MouseEvent("button_release_event", fig11.canvas, cx2 + 2, cy, button=1))
    check(abs(dc.xs[0] - 100.0) < 0.6 and dc.xs[1] == 149.25 and rels and not st11.tips and ax11.get_xlim() == xl_before
          and dc.lines[0][0].get_animated(), f"拖曳游標 1 到 x≈100：沒平移、沒釘提示、放開後回呼（{dc.xs}）")
    n_draw = []
    cid_d = fig11.canvas.mpl_connect("draw_event", lambda e: n_draw.append(1))
    c0 = float(ax11.transData.transform((dc.xs[0], 0))[0])
    ia11.on_press(MouseEvent("button_press_event", fig11.canvas, c0, cy, button=1))
    for k in range(5):
        ia11.on_motion(MouseEvent("motion_notify_event", fig11.canvas, c0 + 3 * (k + 1), cy))
    ia11.on_release(MouseEvent("button_release_event", fig11.canvas, c0 + 15, cy, button=1))
    fig11.canvas.mpl_disconnect(cid_d)
    check(not n_draw and dc._bg is not None, f"游標 artist 是 animated、背景在重畫時存好：拖曳全程不整張重畫（{len(n_draw)} 次）")
    buf = io.BytesIO()
    fig11.savefig(buf, format="png")
    check(len(buf.getvalue()) > 0 and dc.lines[0][0].get_visible(), "savefig 照樣畫出游標（animated 只在螢幕上另外畫）")
    dc.lock = True
    p0 = list(dc.xs)
    c1 = float(ax11.transData.transform((dc.xs[1], 0))[0])
    ia11.on_press(MouseEvent("button_press_event", fig11.canvas, c1, cy, button=1))
    c1b = float(ax11.transData.transform((dc.xs[1] - 20, 0))[0])
    ia11.on_motion(MouseEvent("motion_notify_event", fig11.canvas, c1b, cy))
    ia11.on_release(MouseEvent("button_release_event", fig11.canvas, c1b, cy, button=1))
    check(abs((dc.xs[1] - dc.xs[0]) - (p0[1] - p0[0])) < 1e-9 and abs(dc.xs[1] - (p0[1] - 20)) < 0.6,
          f"鎖定間距：拖游標 2，兩條一起動、Δx 不變（{p0} → {dc.xs}）")
    dc.lock = False
    dc.snap = lambda x: float(round(x / 10.0) * 10.0)
    dc.snap_enabled = True
    c0 = float(ax11.transData.transform((dc.xs[0], 0))[0])
    ia11.on_press(MouseEvent("button_press_event", fig11.canvas, c0, cy, button=1))
    c0b = float(ax11.transData.transform((63.0, 0))[0])
    ia11.on_motion(MouseEvent("motion_notify_event", fig11.canvas, c0b, cy))
    p_snap = list(dc.xs)
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "escape", c0b, cy))
    check(p_snap[0] == 60.0 and not dc.dragging and abs(dc.xs[0] - (p0[0] - 20)) < 0.6,
          f"Snap to data：拖到 63 → 吸到 60；Esc 取消回到原位（{p_snap} → {dc.xs}）")
    xl_d = ax11.get_xlim()
    c0 = float(ax11.transData.transform((dc.xs[0], 0))[0])
    ia11.on_press(MouseEvent("button_press_event", fig11.canvas, c0, cy, button=1, dblclick=True))
    ia11.on_release(MouseEvent("button_release_event", fig11.canvas, c0, cy, button=1))
    check(("restore",) not in host11.calls and ax11.get_xlim() == xl_d, "游標上雙擊：不還原視圖")
    keep = list(dc.xs)
    ia11.reset()
    fig11.clear()
    host11.redraw()
    check(not dc.active and dc.xs == keep, "fig.clear()＋Interactor.reset：artist 丟掉、位置保留")
    dc.attach([host11.info.ax_left], styles.get_style("default"))
    fig11.canvas.draw()
    check(dc.active and dc.lines[0][0].axes is host11.info.ax_left and list(dc.lines[1][0].get_xdata()) == [keep[1], keep[1]],
          "attach：重畫後在新的座標區重建游標")
    dc.set_mode("none", draw=False)
    check(not dc.active and not dc.lines and ia11.hit_test(MouseEvent("button_press_event", fig11.canvas, c0, cy, button=1)).kind != "cursor",
          "模式 none：游標拿掉、抓不到")
    # --- 水平游標（Screen Cursors → Horizontal）、選取＋鍵盤微調（游標加強）---
    check(C.default_hpositions(0, 100) == [25.0, 75.0] and C.parse_hpositions("1:0.5,1.25;x;2:3") == {1: [0.5, 1.25]}
          and C.parse_hpositions(C.format_hpositions({1: [0.1, 2.0], "a": [3.0, 4.0]})) == {1: [0.1, 2.0], "a": [3.0, 4.0]}
          and C.is_hhandle(("h", 1, 0)) and not C.is_hhandle(0), "default／parse／format_hpositions：中央 ±1/4、壞項略過、往返精確")
    ax11 = host11.info.ax_left
    ax11.set_ylim(0, 200)
    dc.set_mode("two", view=ax11.get_xlim(), draw=False)
    dc.set_horizontal(True, draw=False)
    fig11.canvas.draw()
    hk = dc.hkeys[0]
    check(dc.h_active and dc.ys[hk] == [50.0, 150.0] and len(dc.hlines[hk]) == 2 and [t.get_text() for t in dc.hlabels[hk]] == ["1", "2"],
          f"水平游標：每個座標區兩條、放在 y 視圖中央 ±1/4、標 1／2（{dc.ys}）")
    hx = float(ax11.transData.transform((20.0, 0))[0])
    hy = float(ax11.transData.transform((0, 50.0))[1])
    hh = ia11.hit_test(MouseEvent("motion_notify_event", fig11.canvas, hx, hy + 3))
    check(hh.kind == "cursor" and hh.id == ("h", hk, 0), f"水平游標線 ±4 px → cursor、把手 (\"h\", 鍵, 0)（{hh.kind} {hh.id}）")
    rels.clear()
    ia11.on_press(MouseEvent("button_press_event", fig11.canvas, hx, hy + 3, button=1))
    hy2 = float(ax11.transData.transform((0, 100.0))[1])
    ia11.on_motion(MouseEvent("motion_notify_event", fig11.canvas, hx, hy2 + 3))
    ia11.on_release(MouseEvent("button_release_event", fig11.canvas, hx, hy2 + 3, button=1))
    check(abs(dc.ys[hk][0] - 100.0) < 1.0 and dc.ys[hk][1] == 150.0 and rels and dc.selected == ("h", hk, 0)
          and ia11._cursor_kind in ("cursor_y", None), f"拖水平游標 1 到 y≈100、放開回呼、拖過的游標＝選取（{dc.ys[hk]}）")
    y_before = list(dc.ys[hk])
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "up", hx, hy2))
    dpy = float(ax11.transData.transform((0, dc.ys[hk][0]))[1]) - float(ax11.transData.transform((0, y_before[0]))[1])
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "shift+down", hx, hy2))
    dpy2 = float(ax11.transData.transform((0, dc.ys[hk][0]))[1]) - float(ax11.transData.transform((0, y_before[0]))[1])
    xl_k = ax11.get_xlim()
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "left", hx, hy2))     # 水平游標選取中：← 不是它的方向 → 照舊平移
    check(abs(dpy - 1.0) < 1e-6 and abs(dpy2 + 9.0) < 1e-6 and ax11.get_xlim() != xl_k and dc.ys[hk][1] == 150.0,
          f"↑＝上移 1 像素、Shift＋↓＝下移 10 像素；← 照樣平移（{dpy:.3f}、{dpy2:.3f} px）")
    ax11.set_xlim(*xl_k)
    ia11.select_cursor(0)
    dc.snap_enabled = False
    x_b = dc.xs[0]
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "right", hx, hy2))
    dpx = float(ax11.transData.transform((dc.xs[0], 0))[0]) - float(ax11.transData.transform((x_b, 0))[0])
    dc.snap_enabled = True
    dc.step_fn = lambda x, n: float(round(x) + n)
    x_exp = float(round(dc.xs[0]) + 10)
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "shift+right", hx, hy2))
    x_s = dc.xs[0]
    ia11.on_key(KeyEvent("key_press_event", fig11.canvas, "escape", hx, hy2))
    check(abs(dpx - 1.0) < 1e-6 and x_s == x_exp and dc.selected is None and ax11.get_xlim() == xl_k,
          f"垂直游標選取中：→ 移 1 像素（Snap 關）、Shift＋→ 移 10 個樣本（Snap 開，step_fn）；Esc 取消選取（{dpx:.3f} px、{x_s}）")
    check(dc.selected is None and not [l for l in dc.hlines[hk] if l.get_linewidth() != 1.0], "取消選取：線寬回 1")
    dc.snap_enabled = False
    dc.snap = None
    dc.step_fn = None
    dc.set_horizontal(False, draw=False)
    dc.set_mode("none", draw=False)
    check(not dc.h_active and not dc.hlines and ia11.hit_test(MouseEvent("motion_notify_event", fig11.canvas, hx, hy2)).kind != "cursor",
          "水平游標關：拿掉、抓不到")

    # --- 資料提示：提示內容、匯出、Δ（批次 B，組 5）---------------------------------------------------------------------
    check(draw.parse_tip_fields("y,name,zz") == ("name", "y") and draw.parse_tip_fields("") == draw.DEFAULT_TIP_FIELDS
          and draw.parse_tip_fields(["panel", "index"]) == ("index", "panel"), "parse_tip_fields：固定順序、不認得略過、空＝預設")
    rec = {"name": "sig", "x": 1.5, "y": 0.000012345, "index": 9, "panel": "P2", "xunit": "us"}
    check(draw.format_tip_fields(rec) == draw.format_tip_text("sig", 1.5, 0.000012345, "us")
          and draw.format_tip_fields(rec, ("x", "index", "panel")) == "X 1.5 us\nIndex 10\nPanel P2",
          "format_tip_fields：預設列＝原本的 format_tip_text；Index 從 1 起算、Panel 列")
    ia11.host = host11
    t1 = ia11.add_tip(1, 10)
    fig11.canvas.draw()
    txt_default = ia11.tip_artists[t1.id][0].get_text()
    check(txt_default == host11.tip_text(1, 10, 10.0, 10.0), "預設提示內容不變（MATLAB 外觀）")
    t2 = ia11.add_tip(2, 30)
    d = ia11.tip_delta()
    check(d is not None and d["a"]["id"] == t1.id and d["b"]["id"] == t2.id and d["dx"] == 20.0 and d["dy"] == 90.0
          and "Δx = 20" in ia11.tip_delta_text() and "Δy = 90" in ia11.tip_delta_text(),
          f"兩個提示：Δ＝最新的和前一個（{ia11.tip_delta_text()}）")
    ia11.select_tip(t1.id)
    d1 = ia11.tip_delta()
    check(d1["a"]["id"] == t1.id and d1["b"]["id"] == t2.id, "選取的是第一個 → 和下一個比")
    ia11.set_tip_fields(("y", "index"))
    check(ia11.tip_artists[t1.id][0].get_text() == "Y 10\nIndex 11" and ia11.tip_artists[t2.id][0].get_text() == "Y 100\nIndex 31",
          "set_tip_fields：現有提示的文字跟著換")
    t3 = ia11.add_tip(1, 50)
    check(ia11.tip_artists[t3.id][0].get_text() == "Y 50\nIndex 51", "之後新釘的提示也照勾選的列")
    head, rows = ia11.tips_table()
    check(head[0] == "#" and head[3] and len(rows) == 3 and rows[1] == [str(t2.id), "flat", "left", "31", "30", "100"],
          f"tips_table：#、訊號、panel、樣本索引（1 起算）、x、y（{rows[1]}）")
    with tempfile.TemporaryDirectory() as tmp:
        pt, pc = os.path.join(tmp, "tips.txt"), os.path.join(tmp, "tips.csv")
        n_t, n_c = ia11.export_tips(pt), ia11.export_tips(pc)
        lt = open(pt, encoding="utf-8").read().splitlines()
        lc = open(pc, encoding="utf-8").read().splitlines()
    check(n_t == 3 and n_c == 3 and len(lt) == 4 and lt[2].split("\t")[1] == "flat" and lc[2].split(",")[1] == "flat",
          "export_tips：TXT＝Tab、CSV＝逗號，標題列＋每個提示一列")
    ia11.set_tip_fields(draw.DEFAULT_TIP_FIELDS)
    check(ia11.tip_artists[t1.id][0].get_text() == txt_default, "改回預設列 → 文字回到原本")
    st12 = FigureState()
    check(st12.tip_fields == ["name", "x", "y"], "FigureState.tip_fields 預設名稱／X／Y")
    st12.tip_fields = ["x", "panel"]
    st13 = model.state_from_dict(json.loads(json.dumps(model.state_to_dict(st12))))
    old = model.state_to_dict(st12)
    old.pop("tip_fields")
    check(st13.tip_fields == ["x", "panel"] and model.state_from_dict(old).tip_fields == ["name", "x", "y"],
          "tip_fields 存進圖檔（JSON 往返）；舊檔沒有＝預設")

    from . import selftest_e        # 批次 E：匯出、復原名稱、方向限制、縮小鈕、圖字級
    selftest_e.run(check)
    from . import selftest_lim      # 限制修正：數位匯流排貼到圖片視窗也畫成匯流排
    selftest_lim.run(check)

    _dpi_main_checks(check)                                # 2026-10-30：單獨執行 python -m plotkit 也宣告高 DPI（Windows）

    # --- headless import（tkinter 被擋掉）------------------------------------------------------
    pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    code = (f"import sys; sys.path.insert(0, {pkg_parent!r}); sys.modules['tkinter']=None; "
            "import plotkit; print('HAVE_TK', plotkit.HAVE_TK)")
    try:
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, cwd=pkg_parent)
        check(r.returncode == 0 and "HAVE_TK False" in r.stdout, f"沒有 tkinter 也能 import（{r.stdout.strip()[-40:]} {r.stderr.strip()[-80:]}）")
    except Exception as e:
        check(False, f"headless import 子程序失敗：{e}")

    print("SELFTEST OK" if not fails else f"SELFTEST FAILED ({len(fails)} 項)")
    return not fails


if __name__ == "__main__":
    sys.exit(0 if selftest() else 1)
