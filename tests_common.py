# -*- coding: utf-8 -*-
"""GUI 測試共用：安靜模式（預設開）——測試視窗看不見、點不到、不會把 Python 變成前景 App（從 tk.Tk() 第一刻起就不出現在 Dock）、
不搶鍵盤焦點、選單和原生對話框不會真的跳出來、不碰系統剪貼簿；使用者在旁邊工作不會被打斷，滑鼠也不會被看不見的測試視窗吃掉。
行程裡的事件（event_generate、winfo_containing、幾何、invoke／entrycget、剪貼簿的複製貼上）照常運作。

    DSV_TEST_SHOW=1 python tests_gui_mac.py      # 想看畫面時才關掉安靜模式
    DSV_QUIET_LOG=/某處/q.jsonl                   # 選用：把安靜模式攔下／補救的事情逐筆記下來（驗證用）

安靜模式保證什麼（macOS；第 5～7 點每個平台都有）——install_quiet() 要在建立任何視窗之前呼叫：
1. 不搶前景、不出現在 Dock：install_quiet 一開始（第一個 tk.Tk 之前）就把 NSApplication 的 setActivationPolicy: 換成
   不管要什麼都設 Prohibited（2），activateIgnoringOtherApps:／activate 換成只記數、不執行（ACTIVATION）。Tk 初始化時
   applicationDidFinishLaunching: 會先設 Regular（0）、再強制啟用，每次 map 頂層視窗（XMapWindow）和 focus -force（TkpChangeFocus）
   也會要求啟用——全部到不了 AppKit。以前要等 tk.Tk() 回來才設得到 Prohibited：每個測試行程在 tk.Tk() 裡有約 0.15 秒是 Regular
   （Dock 上的 App），整套 25 個測試行程每個都 2→0→2 閃一次（2026-10-26 LaunchServices 實測）。focus_force 另外換成 focus_set。
2. 看不見、點不到：install_quiet 一開始就用 objc runtime 把 NSWindow 排上螢幕的 method
   （makeKeyAndOrderFront:、orderFront:、orderFrontRegardless、orderWindow:relativeTo:、addChildWindow:ordered:）包一層，
   排上去之前先 alpha 0、setIgnoresMouseEvents:YES；setAlphaValue:／setIgnoresMouseEvents: 也包住，不管誰傳什麼都變成 0／YES。
   這樣 Tk 初始化時就被 TkpInit 排上螢幕的根視窗（那一刻 alpha 1：以前每個測試行程一開始都有一個不透明的空白視窗被排上去，
   直到安靜模式設 alpha 0 為止）、tooltip（overrideredirect 視窗會出現在每個 Space，連使用者的全螢幕 App 上面都有）、
   Tcl 自己建的 toplevel 都一樣——Tk 會開的視窗類別（TKWindow、TKPanel、TKDrawerWindow、NSPanel）都經過這一層。
   AppKit 裡自己實作這些 method 的類別（NSFontPanel、開檔／存檔面板、NSColorPanel…，可能不經過這一層）只有原生對話框和
   tk fontchooser 會開：那些在 Tcl 層就擋下（第 5 點），不會建立。
   setIgnoresMouseEvents:YES＝WindowServer 的 hit-test 直接穿過去：真的滑鼠點擊、滾輪、移動都落到底下使用者的視窗。
3. Tk 那一層也一致（第二道）：每個頂層視窗的 MacWindowStyle 屬性都帶 ignoreClicks（＋noActivates）、-alpha 0——
   tk.Tk／tk.Toplevel 包住 __init__，Tcl 的 toplevel 指令掛 execution trace（ttk 下拉選單的 popdown、tk_dialog 也涵蓋）。
   Tk 會把屬性整組換掉的兩條路都有 trace 補回來：MacWindowStyle style 被重設（例如 popdown 改成 help 類別），
   wm overrideredirect 切換（libtk 的 ApplyContainerOverrideChanges 把 document 類別換成 simple 類別的預設屬性，tooltip 就是這樣）。
   例外：transient 的視窗第一次 map 時，Tk（同一個 ApplyContainerOverrideChanges）把 noActivates 拿掉，發生在 update 裡、
   trace 補不到——ignoreClicks、alpha 0、點不到都還在；少了 noActivates 只是那個視窗可以變成這個行程的 key window，
   行程永遠是 Prohibited、啟用全部擋下（第 1 點），搶不到使用者的焦點。
   安全網：每建一個視窗、改一次樣式、overrideredirect／transient／deiconify／state 之後再掃一遍 [NSApp windows]，
   還收得到滑鼠或 alpha 不是 0 的直接改掉，記在 FIXED_WINDOWS。
   （不用定時器：測試裡有「閒置的 mainloop 收到 SIGTERM」這種檢查，定時跑 Python 會把產品的毛病蓋掉。）
4. 選單不會真的彈出：macOS 的 Tk 所有彈出（tk_popup、Menu.post、menubutton、tk_optionMenu…）最後都走
   -[NSMenu popUpMenuPositioningItem:atLocation:inView:]（原生選單：layer 101、看得見，而且會卡住事件迴圈直到點掉）。
   這個 method 換成「記一筆、回傳 NO」：-postcommand 照跑、entrycget／invoke 照常，只是不顯示（NATIVE_MENU_BLOCKED 計數）。
   每個 menu 元件的 post／postcascade 另外用 trace 記在 MENU_POSTS（menu、x、y、entry），測試可以檢查「會彈出什麼」。
   換不掉（menu_guard_ok() 是 False）時改用 Tcl：tk::PostOverPoint 只記錄、Menu.post 只記錄，一樣不顯示。
   （tests_gui_mac.py／tests_plotkit_gui_mac.py 自己把 tk.Menu.tk_popup 換成記錄用的假函式，那條路本來就不進 Tcl。）
5. 原生對話框（tk_messageBox、tk_getOpenFile、tk_getSaveFile、tk_chooseDirectory、tk_chooseColor、tk fontchooser show）不會開：
   測試該自己換掉 messagebox／filedialog；漏掉的話這裡擋下、回傳「取消」，記在 BLOCKED_DIALOGS。
6. 測試沒預期的擋下會讓測試失敗（第二輪，2026-10-26）：第 4、5 點擋下的東西，以前的安靜模式會真的跳出來（使用者看得到、
   也一定會被發現），擋下之後變成默默走「取消」那條路——所以沒包在 expect_blocked() 裡的擋下都記在 UNEXPECTED，
   quiet_problems() 會列出來，三組 GUI 測試跑完全部步驟都會檢查。測試故意的（例如自我檢查）包在 with expect_blocked(): 裡。
7. 不碰系統剪貼簿（第二輪，2026-10-26）：Tcl 的 clipboard 指令和 selection 的 CLIPBOARD 換成行程內的剪貼簿（CLIPBOARD，
   整個行程共用）。clipboard clear／append／get、Entry／Text 的 <<Copy>>／<<Cut>>／<<Paste>>、tkinter 的 clipboard_*／
   selection_get(selection="CLIPBOARD") 都照常，只是不寫 NSPasteboard（以前 Tk 的 clipboard clear 會呼叫 declareTypes:owner:、
   把使用者剛複製的東西清掉，換成測試資料）；也不讀使用者的剪貼簿（沒複製過就 get＝跟空的剪貼簿一樣丟錯）。
   PRIMARY 等其他 selection 照原本的。plotkit 複製圖片走 osascript，不在這裡：測試一律換掉（PLOTKIT_TEST_CLIPBOARD=1 才真的動）。
8. 結束前（atexit）把換掉的 objc method 換回去，Python 收尾後 Tk 的 C 程式不會跑進已經不在的 callback；
   還有沒預期的擋下時在 stderr 印出來（子行程沒有跑完全部步驟的檢查）。
quiet_problems()：現在有沒有破功——沒裝、擋板沒換好（NSWindow／NSMenu／NSApplication）、activationPolicy 不是 Prohibited、
剪貼簿沒接到行程內的版本、有看得見的視窗收得到滑鼠／alpha 不是 0／在選單層、有沒預期的擋下。三組 GUI 測試跑完全部步驟都會檢查。

為什麼（2026-10-26 使用者回報：測試在跑時點不動自己的 DSV）：以前只有 alpha 0＋noActivates＋Prohibited，測試視窗還是
真的視窗——開在使用者正在看的桌面（Space）、被 lift 疊到使用者的 DSV 前面，WindowServer 照樣把點擊送給它們：
CGWindowList 取樣 12 秒內 3 個 alpha 0 的測試視窗（1500×928、1600×968）蓋住使用者 DSV 視窗約 100% 的面積，
SLSFindWindowAndOwner 在那些點回傳的都是隱形的測試視窗。原生彈出選單也沒擋到：一個測試行程的選單視窗
（layer 101、alpha 1）在螢幕上停了至少 3.5 秒。
2026-10-26 修正後實測：一個安靜視窗在已知位置（已 lift、在看得到的桌面最上層），hit-test 打到底下的桌面視窗；
同一個視窗拿掉 ignoreClicks 的對照組打到測試視窗；行程裡的 winfo_containing／event_generate 照常。
2026-10-26 整套五組測試（SUITES: ALL OK）跑的時候每秒取樣一次：499 次（約 560 秒）、python 視窗 981 筆（92 個視窗）。
其中 55 個視窗、410 筆排在使用者正在看的桌面上（使用者全螢幕 iTerm2 的 Space）：中心點 hit-test 全部落到底下的 iTerm2，
打到測試視窗 0 筆；看得見（在螢幕上且 alpha>0）0 筆；選單層 0 筆。使用者的 DSV 視窗整段都在看不到的 Space（48 點的檢查沒有機會做；搶走 0 點）。
2026-10-26 第二輪（同日驗證回報：啟用、剪貼簿、沒預期的擋下）修正後整套五組（SUITES: ALL OK）：LaunchServices 看到的 25 個 python 測試行程
登記時都是 Prohibited、之後 activationPolicy 變化 0 次（修正前每個都 2→0→2）、python 變成前景或擁有選單列 0 次；
25 個行程裡 Tk 在 tk.Tk() 裡要的 Regular 都被改成 2，擋下的強制啟用共 152 次。系統剪貼簿的 changeCount 整段沒變
（修正前同一套測試改了 3 次），測試的複製貼上 21 次都在行程裡。每秒取樣 549 次、python 視窗 1071 筆（91 個），
1037 筆排在使用者正在看的桌面上：hit-test 打到測試視窗 0、看得見 0、選單層 0；最前面的使用者視窗（iTerm2）
48 點 × 616 次全部落到它自己。
2026-10-22 實測（Prohibited）：zoom.us 在前景時跑整套測試、故意 lift+focus_force+grab，前景 App 不變；event_generate／winfo_containing／focus_get 照常
（只用 noActivates＋alpha 0 不夠：對話框／grab 還是會把 python 叫到前景，lsappinfo 取樣 7 次有 3 次是 python。）
"""
from __future__ import annotations

import contextlib
import os
import re
import sys
import tkinter as tk

QUIET = not os.environ.get("DSV_TEST_SHOW")
MENU_POSTS: list = []           # 安靜模式記下的 menu post／postcascade：{"menu", "how", "x", "y", "entry", "expected"}
NATIVE_MENU_BLOCKED = [0]       # 擋下的原生 NSMenu 彈出次數
BLOCKED_DIALOGS: list = []      # 擋下的原生對話框：{"cmd", "args", "expected"}
UNEXPECTED: list = []           # 沒包在 expect_blocked() 裡的擋下（kind＝dialog／menu_post／native_menu）：quiet_problems() 會列出來
FIXED_WINDOWS: list = []        # 安全網改過的 NSWindow：{"num", "cls", "level", "visible", "mouse", "alpha"}
ORDER_FIXES: list = []          # 排上螢幕那一刻還看得見／收得到滑鼠、被當場改掉的視窗：{"sel", "cls", "num", "alpha", "mouse"}
FORCED_SETS = {"setIgnoresMouseEvents:": 0, "setAlphaValue:": 0}   # 有人要把視窗設成收滑鼠／看得見，被改成點不到／alpha 0 的次數
# NSApplication 的啟用：requests＝每次 setActivationPolicy: 要的值（一律改成 2）和是不是在 tk.Tk() 的初始化裡；
# blocked＝擋下（沒執行）的 activateIgnoringOtherApps:／activate 次數
ACTIVATION = {"requests": [], "blocked": {"activateIgnoringOtherApps:": 0, "activate": 0}}
CLIPBOARD: dict = {}            # 安靜模式的行程內剪貼簿：{type: 文字}（整個行程共用，跟系統剪貼簿一樣跨 interpreter）
CLIPBOARD_STATE = {"owned": False, "ops": 0, "interps": 0, "hooked": 0}
_installed = False
_OBJC = None
_POPUP_IMP = None               # 換掉 NSMenu 彈出的 ctypes callback（要一直留著，不然被回收就當掉）
_MENU_GUARD = [False]
_ORDER_GUARD = [False]
_ACT_GUARD = [False]
_ACT_IMPS: dict = {}            # 換上去的 NSApplication method → 我們的 IMP（換回去之前不重複換）
_EXPECT = [0]                   # expect_blocked() 的層數：> 0 時擋下的東西是測試故意的
_IN_TK_INIT = [0]               # 正在 tk.Tk() 的初始化裡（Tk 在這裡面要 Regular、強制啟用）
_SWIZZLED: list = []            # (Method, 原本的 IMP, callback)：結束前換回去
_LOG = os.environ.get("DSV_QUIET_LOG")


def _qlog(**k) -> None:
    """DSV_QUIET_LOG 有設才寫：一行一筆 JSON（行程 pid、時間、事件）。"""
    if not _LOG:
        return
    try:
        import json
        import time
        k.setdefault("pid", os.getpid())
        k.setdefault("t", round(time.time(), 3))
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")
    except Exception:
        pass


@contextlib.contextmanager
def expect_blocked():
    """with expect_blocked(): …——裡面被安靜模式擋下的原生對話框、選單彈出是測試故意的（例如自我檢查），不算 quiet_problems()。
    沒包在這裡面的擋下都記在 UNEXPECTED：以前的安靜模式會真的跳出來（一定會被發現），擋下之後變成默默走「取消」，所以要讓測試失敗。"""
    _EXPECT[0] += 1
    try:
        yield
    finally:
        _EXPECT[0] -= 1


def take_unexpected(start: int = 0) -> list:
    """把 UNEXPECTED[start:] 拿走並回傳（自我檢查故意觸發、確認抓得到之後用；之前的不動）。"""
    got = UNEXPECTED[start:]
    del UNEXPECTED[start:]
    return got


def _note_block(kind: str, rec: dict) -> bool:
    """記一筆擋下：在 expect_blocked() 裡＝測試故意的；不然記到 UNEXPECTED。回傳是不是故意的。"""
    expected = _EXPECT[0] > 0
    rec["expected"] = expected
    if not expected:
        UNEXPECTED.append(dict(rec, kind=kind))
    return expected


class _ObjC:
    """純 ctypes 的 Objective-C 呼叫（不需要 pyobjc）。objc_msgSend 每種參數／回傳型別各轉一個函式指標（arm64 不能當 variadic 呼叫）。"""

    def __init__(self):
        import ctypes
        import ctypes.util
        c = ctypes
        lib = c.cdll.LoadLibrary(c.util.find_library("objc"))
        P = c.c_void_p
        for name, res, args in (("objc_getClass", P, [c.c_char_p]), ("sel_registerName", P, [c.c_char_p]),
                                ("class_getInstanceMethod", P, [P, P]), ("class_getMethodImplementation", P, [P, P]),
                                ("method_setImplementation", P, [P, P]), ("object_getClassName", c.c_char_p, [P]),
                                ("objc_autoreleasePoolPush", P, []), ("objc_autoreleasePoolPop", None, [P])):
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = res, args
        self.lib = lib

        def f(res, *args):
            return c.CFUNCTYPE(res, P, P, *args)(("objc_msgSend", lib))
        self.id = f(P)                      # -(id)sel
        self.id_u = f(P, c.c_ulong)         # -(id)sel:(NSUInteger)
        self.u = f(c.c_ulong)               # -(NSUInteger)sel
        self.l = f(c.c_long)                # -(NSInteger)sel
        self.b = f(c.c_bool)                # -(BOOL)sel
        self.d = f(c.c_double)              # -(double)sel
        self.v_b = f(None, c.c_bool)        # -(void)sel:(BOOL)
        self.v_d = f(None, c.c_double)      # -(void)sel:(double)
        self.b_l = f(c.c_bool, c.c_long)    # -(BOOL)sel:(NSInteger)
        self._sels = {}
        self._appkit = None

    def sel(self, name: str):
        s = self._sels.get(name)
        if s is None:
            s = self._sels[name] = self.lib.sel_registerName(name.encode())
        return s

    def cls(self, name: str):
        return self.lib.objc_getClass(name.encode())

    def app(self):
        """AppKit 的全域變數 NSApp；還沒有就回 None。不能用 [NSApplication sharedApplication]：Tk 還沒建 NSApp 時，
        那會先建一個普通的 NSApplication，之後 Tk 以為它是自己的 TKApplication，一呼叫 macOSVersion 就整個行程當掉（2026-10-26 實測）。"""
        import ctypes
        try:
            if self._appkit is None:
                self._appkit = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")
            return ctypes.c_void_p.in_dll(self._appkit, "NSApp").value
        except Exception:
            return None

    def windows(self):
        """[NSApp windows] 的每個 NSWindow 指標（呼叫端要包在 autorelease pool 裡）。"""
        app = self.app()
        arr = self.id(app, self.sel("windows")) if app else None
        return [self.id_u(arr, self.sel("objectAtIndex:"), i) for i in range(self.u(arr, self.sel("count")) if arr else 0)]


def _objc():
    global _OBJC
    if _OBJC is None:
        _OBJC = False
        if sys.platform == "darwin":
            try:
                _OBJC = _ObjC()
            except Exception:
                _OBJC = False
    return _OBJC or None


def _prohibit_activation() -> bool:
    """[NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited]。要在 Tk 建好 NSApp 之後呼叫。"""
    o = _objc()
    if o is None:
        return False
    try:
        app = o.app()
        return bool(app) and bool(o.b_l(app, o.sel("setActivationPolicy:"), 2))
    except Exception:
        return False


def window_report() -> list:
    """這個行程每個 NSWindow 的狀態（不修改）：num、cls、level、visible、ignores（點不到）、alpha。不是 macOS 回空串列。"""
    o = _objc()
    if o is None:
        return []
    out = []
    pool = o.lib.objc_autoreleasePoolPush()
    try:
        for w in o.windows():
            out.append({"num": o.l(w, o.sel("windowNumber")), "cls": (o.lib.object_getClassName(w) or b"?").decode(),
                        "level": o.l(w, o.sel("level")), "visible": bool(o.b(w, o.sel("isVisible"))),
                        "ignores": bool(o.b(w, o.sel("ignoresMouseEvents"))), "alpha": round(o.d(w, o.sel("alphaValue")), 3)})
    finally:
        o.lib.objc_autoreleasePoolPop(pool)
    return out


def activation_report() -> dict:
    """NSApplication 的啟用狀態（不修改）：guard（擋板換好了）、policy（[NSApp activationPolicy]）、running_policy（LaunchServices 看到的，
    [NSRunningApplication currentApplication]）、requests／blocked（見 ACTIVATION）。NSApp 還沒有（或不是 macOS）時 policy 是 None。"""
    rep = {"guard": _ACT_GUARD[0], "policy": None, "running_policy": None,
           "requests": [dict(r) for r in ACTIVATION["requests"]], "blocked": dict(ACTIVATION["blocked"])}
    o = _objc()
    if o is None:
        return rep
    pool = o.lib.objc_autoreleasePoolPush()
    try:
        app = o.app()
        if app:
            rep["policy"] = o.l(app, o.sel("activationPolicy"))
            ra = o.id(o.cls("NSRunningApplication"), o.sel("currentApplication"))
            if ra:
                rep["running_policy"] = o.l(ra, o.sel("activationPolicy"))
    except Exception:
        pass
    finally:
        o.lib.objc_autoreleasePoolPop(pool)
    return rep


def general_pasteboard_change_count():
    """系統剪貼簿（[NSPasteboard generalPasteboard]）的 changeCount，只讀、不改內容；不是 macOS 回 None。
    安靜模式的剪貼簿在行程裡：測試複製貼上不會讓它變（使用者自己複製東西才會變）。"""
    o = _objc()
    if o is None:
        return None
    pool = o.lib.objc_autoreleasePoolPush()
    try:
        pb = o.id(o.cls("NSPasteboard"), o.sel("generalPasteboard"))
        return o.l(pb, o.sel("changeCount")) if pb else None
    except Exception:
        return None
    finally:
        o.lib.objc_autoreleasePoolPop(pool)


def clipboard_isolated() -> bool:
    """安靜模式的行程內剪貼簿已經接上每個 Tk interpreter（clipboard／selection CLIPBOARD 不碰系統剪貼簿）。"""
    return bool(QUIET and _installed and CLIPBOARD_STATE["interps"] and CLIPBOARD_STATE["hooked"] == CLIPBOARD_STATE["interps"])


def _describe_unexpected(rec: dict) -> str:
    k = rec.get("kind")
    if k == "dialog":
        return f"沒換掉的原生對話框被擋下、自動回答「取消」：{rec.get('cmd')} {str(rec.get('args'))[:80]}"
    if k == "menu_post":
        return f"選單 {rec.get('menu')} 被 {rec.get('how')}（以前會真的彈出）"
    return "原生選單被擋下（以前會真的彈出、卡住事件迴圈直到點掉）"


def quiet_problems() -> list:
    """安靜模式現在有沒有破功（給測試檢查用）。每個平台：沒裝、有沒預期的擋下（UNEXPECTED：測試沒換掉的原生對話框、
    沒包在 expect_blocked() 裡的選單彈出）、剪貼簿沒接到行程內的版本。macOS 另外：NSWindow／NSMenu／NSApplication 的擋板沒換好、
    activationPolicy 不是 Prohibited（2）、有看得見的 NSWindow 收得到滑鼠／alpha 不是 0／在選單層（101）。
    DSV_TEST_SHOW=1（不是安靜模式）回空串列。"""
    if not QUIET:
        return []
    out = []
    if not _installed:
        out.append("沒有呼叫 install_quiet")
    out += [_describe_unexpected(r) for r in UNEXPECTED[:5]]
    if len(UNEXPECTED) > 5:
        out.append(f"……沒預期的擋下共 {len(UNEXPECTED)} 筆")
    if CLIPBOARD_STATE["hooked"] < CLIPBOARD_STATE["interps"]:
        out.append(f"剪貼簿沒接到行程內的版本（{CLIPBOARD_STATE['hooked']}／{CLIPBOARD_STATE['interps']} 個 interpreter）：會動到系統剪貼簿")
    if sys.platform != "darwin":
        return out
    if not menu_guard_ok():
        out.append("原生選單的擋板沒換好")
    if not _ORDER_GUARD[0]:
        out.append("NSWindow 排上螢幕的擋板沒換好")
    act = activation_report()
    if not act["guard"]:
        out.append("NSApplication 啟用（setActivationPolicy:／activateIgnoringOtherApps:）的擋板沒換好")
    if act["policy"] is not None and act["policy"] != 2:
        out.append(f"activationPolicy 是 {act['policy']}（不是 Prohibited 2：會出現在 Dock、可以被啟用）")
    for w in window_report():
        if w["visible"] and (not w["ignores"] or w["alpha"] > 0 or w["level"] >= 101):
            out.append(f"視窗 {w['num']} {w['cls']} level {w['level']}：ignores {w['ignores']}、alpha {w['alpha']}")
    return out


def sweep_windows(*_a) -> int:
    """安全網：這個行程每個還收得到滑鼠（ignoresMouseEvents 是 NO）或 alpha 不是 0 的 NSWindow 直接改掉；回傳改了幾個。
    經過 Tk 建的視窗在顯示前就已經點不到、看不見（見 _TCL_HOOKS），這裡抓的是漏網的（原生面板之類）。"""
    if not QUIET:
        return 0
    o = _objc()
    if o is None:
        return 0
    fixed = 0
    try:
        pool = o.lib.objc_autoreleasePoolPush()
        try:
            for w in o.windows():
                mouse = not o.b(w, o.sel("ignoresMouseEvents"))
                alpha = o.d(w, o.sel("alphaValue")) > 0.0
                if not (mouse or alpha):
                    continue
                if mouse:
                    o.v_b(w, o.sel("setIgnoresMouseEvents:"), True)
                if alpha:
                    o.v_d(w, o.sel("setAlphaValue:"), 0.0)
                fixed += 1
                rec = {"num": o.l(w, o.sel("windowNumber")), "cls": (o.lib.object_getClassName(w) or b"?").decode(),
                       "level": o.l(w, o.sel("level")), "visible": bool(o.b(w, o.sel("isVisible"))), "mouse": mouse, "alpha": alpha}
                FIXED_WINDOWS.append(rec)
                _qlog(ev="sweep_fix", **rec)
        finally:
            o.lib.objc_autoreleasePoolPop(pool)
    except Exception:
        pass
    return fixed


def _swizzle(o, cls_name: str, sel_name: str, imp) -> int:
    """把 cls_name 的 sel_name 換成 imp（ctypes 函式指標的位址）；回傳原本的 IMP（0＝類別或 method 不存在）。"""
    c = o.cls(cls_name)
    if not c:
        return 0
    m = o.lib.class_getInstanceMethod(c, o.sel(sel_name))
    if not m:
        return 0
    return o.lib.method_setImplementation(m, imp) or 0


def _restore_swizzles() -> None:
    """結束前把換掉的 method 換回去：Python 收尾之後 Tk 的 C 程式如果還排視窗，就不會跑進已經不在的 ctypes callback。"""
    o = _objc()
    while _SWIZZLED:
        m, orig, _cb = _SWIZZLED.pop()
        try:
            if o is not None and orig:
                o.lib.method_setImplementation(m, orig)
        except Exception:
            pass
    _MENU_GUARD[0] = _ORDER_GUARD[0] = _ACT_GUARD[0] = False
    _ACT_IMPS.clear()


def _at_exit() -> None:
    """atexit：還有沒預期的擋下就在 stderr 印出來（子行程沒有跑完全部步驟的 quiet_problems() 檢查），再把 objc method 換回去。"""
    try:
        if UNEXPECTED:
            print(f"[安靜模式] 這個行程有 {len(UNEXPECTED)} 筆沒預期的擋下：" + "；".join(_describe_unexpected(r) for r in UNEXPECTED[:3]),
                  file=sys.stderr)
    except Exception:
        pass
    _restore_swizzles()


def _native_popup_blocked(_self, _cmd, _item) -> bool:
    """換掉 -[NSMenu popUpMenuPositioningItem:atLocation:inView:]：不顯示，回 NO（＝使用者沒選就關掉）。
    只讀前三個參數：NSPoint（浮點暫存器）和 view 不讀，ABI 上沒問題。"""
    NATIVE_MENU_BLOCKED[0] += 1
    try:
        expected = _note_block("native_menu", {})
        _qlog(ev="native_menu_blocked", expected=expected)
    except Exception:
        pass
    return False


def _install_menu_guard() -> bool:
    """整個行程換一次 NSMenu 的彈出 method（Tk 的 TKMenu 沒有自己實作，繼承這一個；有的話也一起換）。"""
    global _POPUP_IMP
    o = _objc()
    if o is None:
        return False
    try:
        import ctypes
        name = "popUpMenuPositioningItem:atLocation:inView:"
        sel = o.sel(name)
        if _POPUP_IMP is None:
            _POPUP_IMP = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(_native_popup_blocked)
        imp = ctypes.cast(_POPUP_IMP, ctypes.c_void_p).value
        ok = bool(o.cls("NSMenu"))
        for cn in ("NSMenu", "TKMenu"):
            c = o.cls(cn)
            if not c:
                continue
            if o.lib.class_getMethodImplementation(c, sel) != imp:
                m = o.lib.class_getInstanceMethod(c, sel)
                orig = _swizzle(o, cn, name, imp)
                if orig:
                    _SWIZZLED.append((m, orig, _POPUP_IMP))
            ok = ok and o.lib.class_getMethodImplementation(c, sel) == imp
        return ok
    except Exception:
        return False


def menu_guard_ok() -> bool:
    """原生選單彈出已經換成「記一筆、不顯示」（安靜模式、macOS、換成功）。"""
    if not (QUIET and _installed) or _POPUP_IMP is None:
        return False
    o = _objc()
    if o is None:
        return False
    import ctypes
    imp = ctypes.cast(_POPUP_IMP, ctypes.c_void_p).value
    sel = o.sel("popUpMenuPositioningItem:atLocation:inView:")
    return all(o.lib.class_getMethodImplementation(o.cls(n), sel) == imp for n in ("NSMenu", "TKMenu") if o.cls(n))


# 把視窗排上螢幕的 method（libtk 用到的全部：XMapWindow、TkpInit、raise、focus、deiconify、transient…）。
# 2026-10-26 實測：根視窗在 tk.Tk() 初始化時就被 TkpInit 的 makeKeyAndOrderFront: 排上螢幕，那一刻 alpha 是 1、收得到滑鼠
# （包住 tk.Tk.__init__ 的安靜模式要等 Tk 初始化完才設得到）——每個測試行程一開始，主螢幕目前的桌面上會有一個空白視窗
# 停到 alpha 設成 0 為止。這裡在「排上去之前」就先設 alpha 0、不收滑鼠，任何路徑排上去的視窗都一樣。
_ORDER_SELS = (("makeKeyAndOrderFront:", ("p",), 0), ("orderFront:", ("p",), 0), ("orderFrontRegardless", (), 0),
               ("orderWindow:relativeTo:", ("l", "l"), 0), ("addChildWindow:ordered:", ("p", "l"), 1))


def _quiet_nswindow(o, w, sel_name: str) -> None:
    """NSWindow w 要排上螢幕了：還看得見或收得到滑鼠就當場改掉，記在 ORDER_FIXES。"""
    try:
        mouse = not o.b(w, o.sel("ignoresMouseEvents"))
        alpha = o.d(w, o.sel("alphaValue"))
        if mouse:
            o.v_b(w, o.sel("setIgnoresMouseEvents:"), True)
        if alpha > 0.0:
            o.v_d(w, o.sel("setAlphaValue:"), 0.0)
        if mouse or alpha > 0.0:
            rec = {"sel": sel_name, "cls": (o.lib.object_getClassName(w) or b"?").decode(), "num": o.l(w, o.sel("windowNumber")),
                   "alpha": round(alpha, 3), "mouse": mouse}
            ORDER_FIXES.append(rec)
            _qlog(ev="order_fix", **rec)
    except Exception:
        pass


def _install_order_guard() -> bool:
    """NSWindow 的排上螢幕 method 全部包一層：先 _quiet_nswindow，再呼叫原本的。
    另外 setIgnoresMouseEvents:／setAlphaValue: 不管傳什麼都改成 YES／0：Tk 在 wm overrideredirect 這類地方會先把屬性整組換掉、
    呼叫 setIgnoresMouseEvents:NO，Tcl 的 trace 要等那個指令跑完才補得回來——中間那一下也不給它收滑鼠。
    Tk 的 TKWindow／TKPanel／TKDrawerWindow 和 NSPanel 都沒有自己實作這些（2026-10-26 查過），換 NSWindow 的就涵蓋全部；
    哪天有子類別自己實作，回傳 False 並記在 DSV_QUIET_LOG。"""
    o = _objc()
    if o is None:
        return False
    try:
        import ctypes
        P = ctypes.c_void_p
        kinds = {"p": P, "l": ctypes.c_long, "b": ctypes.c_bool, "d": ctypes.c_double}
        ok = True

        def order_wrapper(box, name, win_arg):
            def wrapper(self_, cmd, *args):
                try:
                    _quiet_nswindow(o, args[0] if win_arg else self_, name)
                    if win_arg:
                        _quiet_nswindow(o, self_, name)
                except Exception:
                    pass
                box["orig"](self_, cmd, *args)
            return wrapper

        def setter_wrapper(box, name, forced):
            def wrapper(self_, cmd, value):
                if value != forced:
                    FORCED_SETS[name] += 1
                box["orig"](self_, cmd, forced)
            return wrapper

        plan = [(name, argk, lambda box, n=name, wa=wa: order_wrapper(box, n, wa)) for name, argk, wa in _ORDER_SELS]
        plan += [("setIgnoresMouseEvents:", ("b",), lambda box: setter_wrapper(box, "setIgnoresMouseEvents:", True)),
                 ("setAlphaValue:", ("d",), lambda box: setter_wrapper(box, "setAlphaValue:", 0.0))]
        for name, argk, make in plan:
            T = ctypes.CFUNCTYPE(None, P, P, *[kinds[k] for k in argk])
            box = {}
            cb = T(make(box))
            imp = ctypes.cast(cb, P).value
            m = o.lib.class_getInstanceMethod(o.cls("NSWindow"), o.sel(name))
            orig = _swizzle(o, "NSWindow", name, imp)
            if not orig:
                ok = False
                continue
            box["orig"] = T(orig)
            _SWIZZLED.append((m, orig, cb))
            for sub in ("TKWindow", "TKPanel", "TKDrawerWindow", "NSPanel"):
                c = o.cls(sub)
                if c and o.lib.class_getMethodImplementation(c, o.sel(name)) != imp:
                    ok = False
                    _qlog(ev="order_guard_subclass_override", cls=sub, sel=name)
        return ok
    except Exception:
        return False


def _install_activation_guard() -> bool:
    """NSApplication 的啟用（第二輪，2026-10-26）：要在第一個 tk.Tk 之前換——Tk 在 tk.Tk() 裡（applicationDidFinishLaunching:）
    會先 setActivationPolicy:0（Regular：Dock 上的 App）、再 activateIgnoringOtherApps:YES，以前要等 tk.Tk() 回來才設得到 2，
    中間約 0.15 秒這個行程是 Dock 上看得到的 App（libtk 8.6.13 反組譯：applicationDidFinishLaunching: 0xd8604／0xd8618；
    XMapWindow 每次 map 頂層視窗、TkpChangeFocus（focus -force）也會呼叫 activateIgnoringOtherApps:）。
    setActivationPolicy: 不管要什麼都設 2；activateIgnoringOtherApps:／activate（macOS 14 起才有）只記數、不執行。
    Tk 的 TKApplication 沒有自己實作這三個（換 NSApplication 的就涵蓋）；哪天有，回傳 False 並記在 DSV_QUIET_LOG。"""
    o = _objc()
    if o is None:
        return False
    try:
        import ctypes
        P = ctypes.c_void_p
        ok = True

        def policy_wrapper(box):
            def wrapper(self_, cmd, policy):
                try:
                    ACTIVATION["requests"].append({"policy": int(policy), "in_tk_init": _IN_TK_INIT[0] > 0})
                    if int(policy) != 2:
                        _qlog(ev="activation_policy_coerced", requested=int(policy), in_tk_init=_IN_TK_INIT[0] > 0)
                except Exception:
                    pass
                return box["orig"](self_, cmd, 2)
            return wrapper

        def activate_wrapper(name):
            def wrapper(self_, cmd, *_a):
                try:
                    ACTIVATION["blocked"][name] += 1
                    _qlog(ev="activation_blocked", sel=name, in_tk_init=_IN_TK_INIT[0] > 0)
                except Exception:
                    pass
            return wrapper

        plan = [("setActivationPolicy:", ctypes.CFUNCTYPE(ctypes.c_bool, P, P, ctypes.c_long), policy_wrapper, True),
                ("activateIgnoringOtherApps:", ctypes.CFUNCTYPE(None, P, P, ctypes.c_bool),
                 lambda box: activate_wrapper("activateIgnoringOtherApps:"), True),
                ("activate", ctypes.CFUNCTYPE(None, P, P), lambda box: activate_wrapper("activate"), False)]
        for name, T, make, required in plan:
            if name in _ACT_IMPS:                 # 已經換過（_setup_interp 的保險再呼叫一次時）：不要包第二層
                imp = _ACT_IMPS[name]
            else:
                m = o.lib.class_getInstanceMethod(o.cls("NSApplication"), o.sel(name))
                if not m:
                    ok = ok and not required      # activate：macOS 13 以前沒有這個 method，沒有就不用換
                    continue
                box = {}
                cb = T(make(box))
                imp = ctypes.cast(cb, P).value
                orig = _swizzle(o, "NSApplication", name, imp)
                if not orig:
                    ok = False
                    continue
                box["orig"] = T(orig)
                _SWIZZLED.append((m, orig, cb))
                _ACT_IMPS[name] = imp
            for cn in ("NSApplication", "TKApplication"):
                c = o.cls(cn)
                if c and o.lib.class_getMethodImplementation(c, o.sel(name)) != imp:
                    ok = False
                    _qlog(ev="activation_guard_subclass_override", cls=cn, sel=name)
        return ok
    except Exception:
        return False


def _record_post(menu, how, *args) -> None:
    """Tcl trace 呼叫：某個 menu 元件要 post／postcascade。"""
    try:
        def num(v):
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return v
        rec = {"menu": str(menu), "how": str(how)}
        if how == "post":
            rec.update(x=num(args[0]) if args else None, y=num(args[1]) if len(args) > 1 else None,
                       entry=(args[2] if len(args) > 2 and str(args[2]) != "" else None))
        else:
            rec["entry"] = args[0] if args and str(args[0]) != "" else None
        _note_block("menu_post", rec)
        MENU_POSTS.append(rec)
        _qlog(ev="menu_post", **rec)
    except Exception:
        pass
    sweep_windows()


def _record_dialog(cmd, argl) -> None:
    """Tcl 呼叫：擋下一個原生對話框（不在 expect_blocked() 裡的記到 UNEXPECTED，quiet_problems() 會列出來）。"""
    try:
        rec = {"cmd": str(cmd), "args": str(argl)[:300]}
        expected = _note_block("dialog", rec)
        BLOCKED_DIALOGS.append(rec)
        _qlog(ev="dialog_blocked", **rec)
        if not expected:
            print(f"[安靜模式] 擋下沒換掉的原生對話框、回答「取消」：{rec['cmd']} {rec['args'][:120]}"
                  "（quiet_problems() 會列出來；測試故意的請包在 tests_common.expect_blocked() 裡）", file=sys.stderr)
    except Exception:
        pass


def _clip_store(op, *a):
    """安靜模式的行程內剪貼簿（Tcl 的 ::clipboard／::selection 呼叫，見 _TCL_HOOKS）：
    clear＝清空並擁有；drop＝清空、不擁有（selection clear）；append type 文字＝附加（還沒擁有就先清空）；
    get type＝回傳 (找到 0/1, 文字)，STRING 和 UTF8_STRING 互通（Tk 的 STRING handler 也會順便提供 UTF8_STRING）。
    不碰 NSPasteboard。不丟例外：Tcl 呼叫的 Python 指令丟例外，_tkinter 會留到 mainloop 才冒出來。"""
    try:
        CLIPBOARD_STATE["ops"] += 1
        if op == "get":
            typ = str(a[0]) if a else "STRING"
            keys = [typ] + ([k for k in ("STRING", "UTF8_STRING") if k != typ] if typ in ("STRING", "UTF8_STRING") else [])
            if CLIPBOARD_STATE["owned"]:
                for k in keys:
                    if k in CLIPBOARD:
                        return ("1", CLIPBOARD[k])
            return ("0", "")
        if op in ("clear", "drop"):
            CLIPBOARD.clear()
            CLIPBOARD_STATE["owned"] = op == "clear"
        elif op == "append" and len(a) >= 2:
            if not CLIPBOARD_STATE["owned"]:
                CLIPBOARD.clear()
                CLIPBOARD_STATE["owned"] = True
            typ = str(a[0])
            CLIPBOARD[typ] = CLIPBOARD.get(typ, "") + str(a[1])
        _qlog(ev="clipboard", op=str(op), size=sum(len(v) for v in CLIPBOARD.values()))
    except Exception:
        pass
    return ""


# 每個 Tcl interpreter 一份（tk.Tk 建好後 eval）。trace 的回呼自己 catch：回呼丟錯會變成被 trace 的指令丟錯。
_TCL_HOOKS = r"""
namespace eval ::dsvq { variable busy 0 }
# 頂層視窗 w：MacWindowStyle 屬性補上 noActivates＋ignoreClicks（WindowServer 的點擊穿過去），alpha 0。
proc ::dsvq::fix {w} {
    variable busy
    if {$busy} return
    set busy 1
    catch {
        if {[winfo exists $w] && [winfo toplevel $w] eq $w} {
            if {[tk windowingsystem] eq "aqua"} {
                set cur [::tk::unsupported::MacWindowStyle style $w]
                set attrs [lindex $cur 1]
                set add {}
                foreach a {noActivates ignoreClicks} {
                    if {$a ni $attrs} { lappend add $a }
                }
                if {[llength $add]} {
                    ::tk::unsupported::MacWindowStyle style $w [lindex $cur 0] [concat $attrs $add]
                }
            }
            wm attributes $w -alpha 0.0
        }
    }
    set busy 0
}
proc ::dsvq::on_toplevel {cmd code result op} {
    if {$code == 0} { ::dsvq::fix $result; catch {::dsvq::sweep} }
}
proc ::dsvq::on_style {cmd code result op} {
    if {$code == 0 && [lindex $cmd 1] eq "style" && [llength $cmd] > 3} { ::dsvq::fix [lindex $cmd 2]; catch {::dsvq::sweep} }
}
proc ::dsvq::on_wm {cmd code result op} {
    if {$code == 0 && [lindex $cmd 1] in {overrideredirect transient deiconify state manage forget}} {
        ::dsvq::fix [lindex $cmd 2]; catch {::dsvq::sweep}
    }
}
proc ::dsvq::on_menu {cmd code result op} {
    if {$code == 0} { catch {trace add execution $result enter ::dsvq::on_menu_cmd} }
}
proc ::dsvq::on_menu_cmd {cmd op} {
    if {[lindex $cmd 1] in {post postcascade}} {
        catch {::dsvq::menu_post [lindex $cmd 0] [lindex $cmd 1] {*}[lrange $cmd 2 end]}
    }
}
trace add execution ::toplevel leave ::dsvq::on_toplevel
trace add execution ::wm leave ::dsvq::on_wm
trace add execution ::menu leave ::dsvq::on_menu
if {[info commands ::tk::unsupported::MacWindowStyle] ne ""} {
    trace add execution ::tk::unsupported::MacWindowStyle leave ::dsvq::on_style
}
# 原生對話框：記下來、不開，回傳「取消」。
proc ::dsvq::dialog {cmd argl} {
    catch {::dsvq::dialog_blocked $cmd $argl}
    if {$cmd ne "tk_messageBox"} { return "" }
    set type ok
    foreach {k v} $argl { if {$k eq "-type"} { set type $v } }
    switch -- $type {
        ok { return ok }
        yesno { return no }
        abortretryignore { return abort }
        default { return cancel }
    }
}
namespace eval ::dsvq {
    foreach c {tk_messageBox tk_getOpenFile tk_getSaveFile tk_chooseDirectory tk_chooseColor} {
        if {[info commands ::dsvq::orig_$c] eq "" && [info commands ::$c] ne ""} { rename ::$c ::dsvq::orig_$c }
        proc ::$c {args} "[list ::dsvq::dialog $c] \$args"
    }
    unset c
}
# tk fontchooser show 會開 NSFontPanel（它自己實作 orderFront: 這些，NSWindow 那層不一定攔得到）：一樣擋下、記下來。
# tk fontchooser 是用名字呼叫 ::tk::fontchooser（2026-10-26 實測），configure／hide 照常。
if {[info commands ::tk::fontchooser] ne "" && [info procs ::tk::fontchooser] eq ""} {
    if {[info commands ::dsvq::orig_fontchooser] eq ""} { rename ::tk::fontchooser ::dsvq::orig_fontchooser }
    proc ::tk::fontchooser {args} {
        set sub [lindex $args 0]
        if {$sub ne "" && [string first $sub show] == 0} {
            ::dsvq::dialog "tk fontchooser" $args
            return
        }
        uplevel 1 [list ::dsvq::orig_fontchooser {*}$args]
    }
}
# 剪貼簿（第二輪）：clipboard 指令和 selection 的 CLIPBOARD 換成行程內的剪貼簿（::dsvq::clip_store，Python 端、整個行程共用），
# 不碰系統剪貼簿：以前 Tk 的 clipboard clear 會 declareTypes:owner:（把使用者剛複製的東西清掉）、append 會 addTypes:owner:。
# 參數、縮寫、錯誤訊息照 Tk 8.6 的 clipboard／selection；PRIMARY 等其他 selection、selection handle 交給原本的指令。
proc ::dsvq::idx {given choices what} {
    if {$given in $choices} { return $given }
    set m {}
    if {$given ne ""} {
        foreach c $choices { if {[string first $given $c] == 0} { lappend m $c } }
    }
    if {[llength $m] == 1} { return [lindex $m 0] }
    set n [llength $choices]
    if {$n == 1} {
        set must [lindex $choices 0]
    } elseif {$n == 2} {
        set must "[lindex $choices 0] or [lindex $choices 1]"
    } else {
        set must "[join [lrange $choices 0 end-1] {, }], or [lindex $choices end]"
    }
    return -code error "[expr {[llength $m] > 1 ? {ambiguous} : {bad}}] $what \"$given\": must be $must"
}
proc ::dsvq::win {w} {
    if {![winfo exists $w]} { return -code error "bad window path name \"$w\"" }
}
if {[info commands ::clipboard] ne "" && [info procs ::clipboard] eq "" && [info commands ::dsvq::orig_clipboard] eq ""} {
    rename ::clipboard ::dsvq::orig_clipboard
}
proc ::clipboard {args} {
    if {![llength $args]} { return -code error "wrong # args: should be \"clipboard option ?arg ...?\"" }
    set sub [::dsvq::idx [lindex $args 0] {append clear get} option]
    set rest [lrange $args 1 end]
    set n [llength $rest]
    set w .
    set type STRING
    switch -- $sub {
        clear {
            if {$n == 2} {
                ::dsvq::idx [lindex $rest 0] {-displayof} option
                set w [lindex $rest 1]
            } elseif {$n != 0} {
                return -code error "wrong # args: should be \"clipboard clear ?-displayof window?\""
            }
            ::dsvq::win $w
            ::dsvq::clip_store clear
            return
        }
        append {
            set i 0
            while {$i < $n - 1} {
                set a [lindex $rest $i]
                if {[string index $a 0] ne "-"} break
                if {$a eq "--"} { incr i; break }
                set o [::dsvq::idx $a {-displayof -format -type} option]
                incr i
                switch -- $o {
                    -displayof { set w [lindex $rest $i] }
                    -type { set type [lindex $rest $i] }
                }
                incr i
            }
            if {$n - $i != 1} {
                return -code error "wrong # args: should be \"clipboard append ?-option value ...? data\""
            }
            ::dsvq::win $w
            ::dsvq::clip_store append $type [lindex $rest $i]
            return
        }
        get {
            for {set i 0} {$i < $n} {incr i} {
                set a [lindex $rest $i]
                if {[string index $a 0] ne "-"} {
                    return -code error "wrong # args: should be \"clipboard get ?-option value ...?\""
                }
                set o [::dsvq::idx $a {-displayof -type} option]
                incr i
                if {$i >= $n} { return -code error "value for \"$a\" missing" }
                switch -- $o {
                    -displayof { set w [lindex $rest $i] }
                    -type { set type [lindex $rest $i] }
                }
            }
            ::dsvq::win $w
            lassign [::dsvq::clip_store get $type] found data
            if {!$found} { return -code error "CLIPBOARD selection doesn't exist or form \"$type\" not defined" }
            return $data
        }
    }
}
if {[info commands ::selection] ne "" && [info procs ::selection] eq "" && [info commands ::dsvq::orig_selection] eq ""} {
    rename ::selection ::dsvq::orig_selection
}
proc ::selection {args} {
    if {[llength $args] && ![catch {::dsvq::idx [lindex $args 0] {clear get handle own} option} sub] && $sub ne "handle"} {
        set rest [lrange $args 1 end]
        set sel PRIMARY
        set type STRING
        set w .
        set i 0
        while {$i < [llength $rest] - 1} {
            set a [lindex $rest $i]
            if {[string index $a 0] ne "-" || [catch {::dsvq::idx $a {-command -displayof -selection -type} option} o]} break
            set v [lindex $rest [expr {$i + 1}]]
            switch -- $o {
                -selection { set sel $v }
                -type { set type $v }
                -displayof { set w $v }
            }
            incr i 2
        }
        if {$sel eq "CLIPBOARD"} {
            set left [lrange $rest $i end]
            switch -- $sub {
                get { return [::clipboard get -displayof $w -type $type] }
                clear { ::dsvq::win $w; ::dsvq::clip_store drop; return }
                own {
                    if {[llength $left] == 1} { ::dsvq::win [lindex $left 0]; ::dsvq::clip_store clear }
                    return
                }
            }
        }
    }
    uplevel 1 [list ::dsvq::orig_selection {*}$args]
}
"""

# NSMenu 的 method 換不掉時的退路：Tcl 的 tk_popup／menubutton 都經過 tk::PostOverPoint，改成只記錄不 post。
_TCL_MENU_FALLBACK = r"""
proc ::tk::PostOverPoint {menu x y {entry {}}} {
    catch {::dsvq::menu_post $menu post $x $y $entry}
    if {$entry ne "" && [$menu type $entry] ni {separator tearoff} && [$menu entrycget $entry -state] ne "disabled"} {
        $menu activate $entry
    }
}
"""


def _setup_interp(root) -> None:
    """每個新的 Tk interpreter：Prohibited（第二道；第一道是 _install_activation_guard）、換 NSMenu 彈出（行程一次）、
    掛 Tcl trace、原生對話框的擋板、行程內的剪貼簿。"""
    try:
        if not root.tk.call("info", "commands", "::toplevel"):
            return                        # Tk(useTk=False)：只有 Tcl，沒有視窗
    except Exception:
        return
    _prohibit_activation()                # NSApp 這時候才存在
    if not _MENU_GUARD[0]:                # 保險：install_quiet 時 AppKit 還沒載入的話這裡再換一次
        _MENU_GUARD[0] = _install_menu_guard()
    if not _ACT_GUARD[0] and sys.platform == "darwin":
        _ACT_GUARD[0] = _install_activation_guard()    # 同上的保險（這時候 Tk 已經要過 Regular，之後的才擋得到）
    CLIPBOARD_STATE["interps"] += 1
    try:
        root.tk.eval("namespace eval ::dsvq {}")
        root.tk.createcommand("::dsvq::sweep", sweep_windows)
        root.tk.createcommand("::dsvq::menu_post", _record_post)
        root.tk.createcommand("::dsvq::dialog_blocked", _record_dialog)
        root.tk.createcommand("::dsvq::clip_store", _clip_store)
        root.tk.eval(_TCL_HOOKS)
        if not _MENU_GUARD[0]:
            root.tk.eval(_TCL_MENU_FALLBACK)
            _patch_menu_post()
        if root.tk.call("info", "procs", "::clipboard") and root.tk.call("info", "procs", "::selection"):
            CLIPBOARD_STATE["hooked"] += 1
    except Exception as e:
        print(f"[安靜模式] Tcl 掛勾失敗：{e}", file=sys.stderr)
    _qlog(ev="interp", menu_guard=_MENU_GUARD[0], order_guard=_ORDER_GUARD[0], act_guard=_ACT_GUARD[0],
          clipboard=CLIPBOARD_STATE["hooked"] == CLIPBOARD_STATE["interps"])


def _patch_menu_post() -> None:
    """退路：Python 的 Menu.post 只記錄（原生選單換不掉時才用）。"""
    if getattr(tk.Menu.post, "_dsvq", False):
        return

    def post(self, x, y):
        _record_post(self._w, "post", x, y)
    post._dsvq = True
    tk.Menu.post = post


def make_quiet(win) -> None:
    """把一個（還沒顯示的）Tk／Toplevel 變成看不見、點不到、不啟用 App。"""
    if not QUIET:
        return
    if sys.platform == "darwin":
        try:
            win.tk.call("::tk::unsupported::MacWindowStyle", "style", win._w, "document", ("noActivates", "ignoreClicks"))
        except Exception:
            pass
    try:
        win.attributes("-alpha", 0.0)
    except Exception:
        pass


def install_quiet() -> None:
    """在建立任何視窗之前呼叫一次：之後所有 tk.Tk／tk.Toplevel（和 Tcl 建的 toplevel、menu、原生對話框、剪貼簿）都自動安靜。"""
    global _installed
    if _installed or not QUIET:
        return
    _installed = True
    import atexit
    if sys.platform == "darwin":
        _ACT_GUARD[0] = _install_activation_guard()   # 要在第一個 tk.Tk 之前：Tk 在 tk.Tk() 裡就會設 Regular、強制啟用
        _ORDER_GUARD[0] = _install_order_guard()      # 要在第一個 tk.Tk 之前：根視窗在 Tk 初始化時就會被排上螢幕
        _MENU_GUARD[0] = _install_menu_guard()
        _qlog(ev="install", act_guard=_ACT_GUARD[0], order_guard=_ORDER_GUARD[0], menu_guard=_MENU_GUARD[0])
    atexit.register(_at_exit)
    for cls in (tk.Tk, tk.Toplevel):
        orig = cls.__init__

        def _init(self, *a, _orig=orig, _is_root=(cls is tk.Tk), **k):
            if _is_root:
                _IN_TK_INIT[0] += 1
            try:
                _orig(self, *a, **k)
            finally:
                if _is_root:
                    _IN_TK_INIT[0] -= 1
            if _is_root:
                _setup_interp(self)
            make_quiet(self)
            sweep_windows()
        cls.__init__ = _init
    # focus_force 會把 App 叫到前景（搶走使用者正在打字的視窗）；安靜模式下改成 focus_set
    tk.Misc.focus_force = tk.Misc.focus_set


_TIS = None


def _tis():
    """HIToolbox／CoreFoundation（唯讀的鍵盤配置查詢：TISCopyCurrentKeyboardLayoutInputSource、UCKeyTranslate）；不是 macOS 回 None。"""
    global _TIS
    if _TIS is None:
        _TIS = False
        if sys.platform == "darwin":
            try:
                import ctypes as c
                hi = c.cdll.LoadLibrary("/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework/HIToolbox")
                cf = c.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
                P = c.c_void_p
                hi.TISCopyCurrentKeyboardLayoutInputSource.restype = P
                hi.TISGetInputSourceProperty.restype = P
                hi.TISGetInputSourceProperty.argtypes = [P, P]
                hi.LMGetKbdType.restype = c.c_uint8
                hi.UCKeyTranslate.argtypes = [P, c.c_uint16, c.c_uint16, c.c_uint32, c.c_uint32, c.c_uint32,
                                              c.POINTER(c.c_uint32), c.c_ulong, c.POINTER(c.c_ulong), c.POINTER(c.c_uint16)]
                hi.UCKeyTranslate.restype = c.c_int32
                cf.CFDataGetBytePtr.restype = P
                cf.CFDataGetBytePtr.argtypes = [P]
                cf.CFRelease.argtypes = [P]
                cf.CFStringGetCString.argtypes = [P, c.c_char_p, c.c_long, c.c_uint32]
                _TIS = (c, hi, cf)
            except Exception:
                _TIS = False
    return _TIS or None


def keyboard_layout_id() -> str:
    """使用者目前的鍵盤配置（唯讀，例如 com.apple.keylayout.ZhuyinBopomofo）；查不到回 "?"。絕對不改輸入法。"""
    t = _tis()
    if t is None:
        return "?"
    c, hi, cf = t
    lay = hi.TISCopyCurrentKeyboardLayoutInputSource()
    if not lay:
        return "?"
    try:
        buf = c.create_string_buffer(256)
        cf.CFStringGetCString(hi.TISGetInputSourceProperty(lay, c.c_void_p.in_dll(hi, "kTISPropertyInputSourceID").value), buf, 256, 0x08000100)
        return buf.value.decode() or "?"
    finally:
        cf.CFRelease(lay)


def keyboard_layout_chars(virt: int, shift: bool = False, option: bool = False, cmd: bool = False, ctrl: bool = False) -> str:
    """目前的鍵盤配置下這顆實體按鍵（虛擬鍵碼）打出的字（唯讀 UCKeyTranslate；真的按鍵的 NSEvent characters 就是這個）。
    注音：0x09（V）→ ㄒ、0x21（[）→ 「、按 ⌘ → v。不是 macOS 或查不到回 ""。"""
    t = _tis()
    if t is None:
        return ""
    c, hi, cf = t
    lay = hi.TISCopyCurrentKeyboardLayoutInputSource()
    if not lay:
        return ""
    try:
        data = hi.TISGetInputSourceProperty(lay, c.c_void_p.in_dll(hi, "kTISPropertyUnicodeKeyLayoutData").value)
        if not data:
            return ""
        mods = (2 if shift else 0) | (8 if option else 0) | (1 if cmd else 0) | (16 if ctrl else 0)
        dead, n, buf = c.c_uint32(0), c.c_ulong(0), (c.c_uint16 * 8)()
        err = hi.UCKeyTranslate(cf.CFDataGetBytePtr(data), virt, 0, mods, hi.LMGetKbdType(), 1, c.byref(dead), 8, c.byref(n), buf)
        return "".join(chr(buf[i]) for i in range(n.value)) if err == 0 else ""
    finally:
        cf.CFRelease(lay)


def has_desktop(win) -> bool:
    """視窗真的有被 map 出來（有桌面）。Windows 用 ssh 跑時沒有桌面工作階段：視窗 1×1、never mapped，
    Tk 的 event_generate 滑鼠／鍵盤事件送不到，這種環境只能跑直接呼叫的測試，Tk 事件的檢查要略過。"""
    try:
        win.update()
        return bool(win.winfo_ismapped()) and win.winfo_width() > 1
    except Exception:
        return False


_SUBST = {"%#": "0", "%b": "??", "%f": "??", "%h": "??", "%k": "??", "%s": "0", "%t": "0", "%w": "??", "%x": "0", "%y": "0",
          "%E": "0", "%T": "2", "%X": "0", "%Y": "0", "%D": "??"}


def _tcl_word(v) -> str:
    """一個值變成 Tcl 腳本裡的一個字（Tk 代換 % 欄位時也會加引號）：空字串＝{}、特殊字元前面加反斜線（[ ] { } $ " \\ ; 空白）。"""
    v = str(v)
    if v == "":
        return "{}"
    out = []
    for ch in v:
        if ch in '[]{}$"\\; \t\n\r':
            out.append("\\" + {"\t": "t", "\n": "n", "\r": "r"}.get(ch, ch))
        else:
            out.append(ch)
    return "".join(out)


def _key_seqs(pre: str, mods: str, keysym: str, kind: str = "Key") -> tuple:
    """tk_key 在每一層 bindtag 依序找的事件樣式（Tk 選最精確的那個）：完整的 <Command-Key-v>、只寫修飾鍵的 <Command-Key>
    （多個修飾鍵時再試各別的一個）、最後是一般的 <Key>。"""
    seqs = [f"<{pre}{kind}-{keysym}>"]
    if mods:
        parts = mods.split("-")
        seqs.append(f"<{pre}{kind}>")
        if len(parts) > 1:
            seqs.extend(f"<{m}-{kind}>" for m in parts)
    seqs.append(f"<{kind}>")
    return tuple(seqs)


def tk_key(widget, keysym: str, char: str = "", mods: str = "", keycode=None) -> None:
    """對 widget 送一個按鍵。有前景焦點時用真的 event_generate；安靜模式下 App 沒有焦點、Tk 會把 KeyPress 丟掉，
    所以照 Tk 的 bindtags 順序（widget → class → toplevel → all）自己找出 <Key-xxx>／<Key> 的綁定腳本，代入 % 欄位後執行，
    腳本回 break 就停（和 Tk 的 dispatch 一樣）。這樣 matplotlib 畫布的 <Key>（→ Interactor.on_key）和 toplevel 的 <Delete> 都會走到。
    keycode：%k（預設 "??"）。macOS 的 Tk 是 虛擬鍵碼 << 24 | 字元；非拉丁輸入法（注音）之下 ⌘V 的 keysym 是 "??"、只有 keycode 認得出是哪顆鍵，
    要模擬那種按鍵就給 keysym="??" 和真的 keycode（2026-10-26 第 13 項：以前 %k 一律是 "??"，模擬不了使用者的注音輸入法）。"""
    pre = f"{mods}-" if mods else ""            # mods＝"Control"／"Command"…：組合鍵（只找 <Control-Key-w> 這種完整的綁定）
    if not QUIET and widget.focus_get() is not None and keycode is None:
        widget.event_generate(f"<{pre}Key-{keysym}>", when="now")
        return
    top = widget.winfo_toplevel()
    # %s＝修飾鍵狀態位元（和真的事件一樣）：Shift 1、Control 4、Command（mac）8、Option（mac）16、Alt（Windows）0x20000
    bits = {"Shift": 1, "Control": 4, "Command": 8, "Option": 16 if sys.platform == "darwin" else 0x20000,
            "Alt": 16 if sys.platform == "darwin" else 0x20000, "Mod": 8 if sys.platform == "darwin" else 4}
    state = 0
    for m in (mods.split("-") if mods else []):
        state |= bits.get(m, 0)
    fields = dict(_SUBST, **{"%W": widget._w, "%K": keysym, "%A": char, "%N": "0", "%s": str(state)})
    if keycode is not None:
        fields["%k"] = str(int(keycode))
    # 和 Tk 的 % 代換一樣：每個值照 Tcl list 元素的規則加引號（空字元＝{}、「[」＝\[、注音的「ㄦ」照原樣），一次代換完（值裡的 % 不會再被換）
    # （2026-10-27 注音：以前直接把字元貼進腳本，[ 這種字元會讓 Tcl 腳本語法錯誤）
    quoted = {k: _tcl_word(v) for k, v in fields.items()}
    quoted["%%"] = "%"

    def _expand(script: str) -> str:
        return re.sub(r"%[%#a-zA-Z]", lambda m: quoted.get(m.group(0), m.group(0)), script)

    def _run(seqs) -> None:
        for tag in widget.bindtags():
            if tag == widget._w:
                get = widget.bind
            elif tag == "all":
                get = widget.bind_all
            elif tag == top._w:
                get = top.bind
            else:
                get = lambda seq=None, _c=tag: widget.bind_class(_c, seq)
            script = ""
            for seq in seqs:
                try:
                    script = get(seq)
                except Exception:
                    script = ""
                if script:
                    break
            if not script:
                continue
            script = _expand(script)
            # 用 catch 取得回傳碼：在 Tk 事件處理中（after 回呼裡）直接 eval 時，綁定回傳的 break（碼 3）不會變成錯誤，
            # 以前會被當成正常結束而繼續往下一層 bindtag 傳（真的 Tk 會停在這裡）
            rc = int(widget.tk.call("catch", script, "::_tk_key_res"))
            if rc == 3:                                   # TCL_BREAK：停止，跟 Tk 的 dispatch 一樣
                return
            if rc == 1:
                raise tk.TclError(str(widget.tk.getvar("::_tk_key_res")))
    # 每一層 bindtag 照 Tk 選最精確的一個綁定：<Command-Key-v> → 只寫修飾鍵的 <Command-Key>（輸入框類別的 <Mod1-Key>／<Control-Key>，
    # 注音的 ⌘V 走的就是它）→ 一般的 <Key>（組合鍵也會走到 <Key> 分派器）
    _run(_key_seqs(pre, mods, keysym))
    # 真的鍵盤接著會送 KeyRelease：matplotlib 畫布靠它清掉 canvas._key，不然之後的滑鼠事件都帶著 "ctrl+z"（Control＋左鍵變成右鍵）
    try:
        alive = bool(widget.winfo_exists())
    except Exception:
        alive = False
    if alive:                                   # 按鍵可能把視窗關了（⌘W）：沒有元件就不送放開
        _run(_key_seqs(pre, mods, keysym, "KeyRelease"))


# --- 原生拖放（macOS）：tests/fakednd.m 編成 dylib，模擬從 Finder 拖檔案進來 ----------------------------------------
_FAKEDND = None


def fake_dnd_lib(out_dir: str):
    """編譯 tests/fakednd.m（第一次呼叫時）並載入；不是 macOS、沒有 clang、編譯失敗回傳 None（測試改直接呼叫拖放處理函式）。"""
    global _FAKEDND
    if _FAKEDND is not None:
        return _FAKEDND or None
    _FAKEDND = False
    if sys.platform != "darwin":
        return None
    import ctypes
    import shutil
    import subprocess
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "fakednd.m")
    cc = shutil.which("clang")
    if not cc or not os.path.isfile(src):
        return None
    lib = os.path.join(out_dir, "libfakednd.dylib")
    r = subprocess.run([cc, "-fobjc-arc", "-dynamiclib", "-framework", "AppKit", "-o", lib, src], capture_output=True, text=True)
    if r.returncode != 0 or not os.path.isfile(lib):
        print("fakednd 編譯失敗：", (r.stderr or "")[:300])
        return None
    L = ctypes.cdll.LoadLibrary(lib)
    L.dsv_fake_drop.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int, ctypes.c_int]
    L.dsv_fake_drop_state.argtypes = [ctypes.POINTER(ctypes.c_long), ctypes.c_char_p, ctypes.c_int]
    _FAKEDND = L
    return L


def native_drop(app, x_root, y_root, paths, leave=False, timeout: float = 5.0, settle: float = 0.15):
    """在螢幕座標 (x_root, y_root) 放下 paths（leave＝True：拖過去再離開、不放；leave＝"hover"：只拖過去停著）。要先呼叫 fake_dnd_lib。
    回傳 (ops, err)：ops＝[draggingEntered, draggingUpdated, prepare, perform] 的回傳值（接受＝1 copy）。"""
    import ctypes
    import time
    L = _FAKEDND
    arr = (ctypes.c_char_p * len(paths))(*[str(p).encode("utf-8") for p in paths])
    L.dsv_fake_drop(float(x_root), float(y_root), arr, len(paths), 2 if leave == "hover" else (1 if leave else 0))
    ops = (ctypes.c_long * 5)()
    err = ctypes.create_string_buffer(256)
    t0 = time.time()
    while time.time() - t0 < timeout:
        app.update()
        if L.dsv_fake_drop_state(ops, err, 256) == 2:
            break
        time.sleep(0.01)
    t1 = time.time()
    while time.time() - t1 < settle:                 # 放下後真正的加入排在 after(1)
        app.update()
        time.sleep(0.01)
    return list(ops)[:4], err.value.decode("utf-8", "replace")


# --- 測試工具在高負載下（0.9.14 R3C-6）：每步計時、結束訊號寫出進度再結束、卡住時的看門狗 -------------------------------------
# 以前（verify_0913_r3_consistency.md R3C-6）：(1) plotkit GUI 用 faulthandler.dump_traceback_later(45, exit=True) 當整個行程的看門狗——負載高時
# 整套正常跑也超過 45 秒，看門狗在別的執行緒正在跑時印 traceback 卡住、行程不結束（套件只好等 30 分鐘的 timeout）；(2) timeout 的 SIGTERM 碰上
# Tk 自己的訊號處理（macOS 的 TkMacOSXSignalHandler 在訊號處理裡叫 Tcl_Exit）正在畫圖時死鎖，log 也看不出停在哪一步；(3) DSV GUI 沒有每一步的
# 時間，超過時限時不知道從哪裡用 DSV_TEST_ONLY 接著跑。這幾個只改測試工具，任何檢查都不動。

class StepProgress:
    """步驟式測試（after() 一步一步跑）的進度：每一步開始／結束時呼叫 begin(i)／end(i)，end 印一行「【步驟時間】步驟名稱 秒數（這一步幾項，累計幾項）」；
    結束訊號或看門狗用 report() 寫出停在哪一步、已跑幾項、失敗幾項、沒跑完的步驟和接著跑的 DSV_TEST_ONLY。results＝測試的 [(ok, msg)] 清單。"""

    def __init__(self, names, results, env_name: Optional[str] = "DSV_TEST_ONLY", prereq: Optional[dict] = None):
        """prereq＝{步驟名稱: [單獨接著跑時要一起跑的前面步驟]}（例如 s9 檢查的是 sq～s8 一路建起來的訊號）：report() 會把它們併進接著跑的那行。"""
        import time
        self.names = list(names)
        self.results = results
        self.env_name = env_name
        self.prereq = dict(prereq or {})
        self.i = -1
        self.t0 = self.t_step = self.t_beat = time.monotonic()
        self.n_step = 0
        self.n_beat = 0
        self.times = []                               # [(步驟名稱, 秒數, 這一步的檢查項目數)]

    def _now(self) -> float:
        import time
        return time.monotonic()

    def begin(self, i: int) -> None:
        self.i = i
        self.t_step = self.t_beat = self._now()
        self.n_step = self.n_beat = len(self.results)

    def end(self, i: int) -> None:
        now = self._now()
        dt, k = now - self.t_step, len(self.results) - self.n_step
        name = self.names[i] if 0 <= i < len(self.names) else f"#{i}"
        self.times.append((name, dt, k))
        self.t_beat, self.n_beat = now, len(self.results)
        print(f"【步驟時間】{name} {dt:.1f} s（這一步 {k} 項，累計 {len(self.results)} 項，開始後 {(now - self.t0) / 60:.1f} 分）", flush=True)

    def idle_s(self) -> float:
        """多久沒有進度了（新的一步、新的檢查項目都算進度）。"""
        if len(self.results) != self.n_beat:
            self.n_beat, self.t_beat = len(self.results), self._now()
        return self._now() - self.t_beat

    def report(self, why: str) -> str:
        now = self._now()
        n = len(self.results)
        bad = sum(1 for ok, _m in self.results if not ok)
        cur = self.names[self.i] if 0 <= self.i < len(self.names) else "（還沒開始第一步）"
        rest = self.names[max(self.i, 0):]
        lines = [f"{why}：停在 {cur}（第 {self.i + 1}/{len(self.names)} 步，這一步已經 {now - self.t_step:.0f} s，開始後 {(now - self.t0) / 60:.1f} 分）；"
                 f"已跑 {n} 項，其中沒過 {bad} 項"]
        if rest and self.env_name:
            lines.append(f"還沒跑完的步驟（含停住的這一步）可以接著跑：{self.env_name}={','.join(rest)}")
            pre = []
            for r in rest:
                for p in self.prereq.get(r, ()):
                    if p not in rest and p not in pre:
                        pre.append(p)
            if pre:
                who = "、".join(r for r in rest if self.prereq.get(r))
                lines.append(f"（{who} 檢查的是前面步驟一路建起來的狀態：單獨接著跑會假失敗，要連同前面那 {len(pre)} 步一起跑——"
                             f"{self.env_name}={','.join(pre + rest)}）")
        elif rest:
            lines.append(f"還沒跑完的步驟（含停住的這一步）：{','.join(rest)}")
        return "\n".join(lines)

    def summary(self, top: int = 12) -> str:
        if not self.times:
            return ""
        tot = sum(t for _n, t, _k in self.times)
        rows = sorted(self.times, key=lambda r: -r[1])[:top]
        return (f"【步驟時間】全部 {len(self.times)} 步 {tot / 60:.1f} 分；最久的 {len(rows)} 步：" + "、".join(f"{n} {t:.0f}s" for n, t, _k in rows))


def install_term_report(progress: "StepProgress", code: int = 143) -> bool:
    """測試行程收到 SIGTERM（run311.sh 的 timeout 時限到了、或有人 kill）：寫出 progress.report()（停在哪一步、已跑幾項、接著跑的
    DSV_TEST_ONLY）和每個執行緒的位置，然後 os._exit(code)——不經過 Tk 的訊號處理（macOS 的 TkMacOSXSignalHandler 在訊號處理裡叫
    Tcl_Exit，碰上正在畫圖時死鎖：0.9.13 第三輪 R3C-6，行程 0% CPU 卡住，只能 SIGKILL）。要在建好 Tk 的根視窗之後呼叫（Tk 初始化時會裝自己的處理）。
    Python 的處理在主執行緒下一次跑 Python 時執行（步驟之間的 after() 一直有）。回傳有沒有裝上。"""
    import faulthandler
    import signal

    def _h(signum, _frame):
        try:
            sys.stdout.write("\n" + progress.report(f"TERM：收到結束訊號 {signum}") + "\n")
            sys.stdout.flush()
        except Exception:
            pass
        try:
            faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
            sys.stderr.flush()
        except Exception:
            pass
        os._exit(code)
    try:
        signal.signal(signal.SIGTERM, _h)
        return True
    except (ValueError, OSError, AttributeError):
        return False


def install_stall_watchdog(progress: "StepProgress", limit_s: float, code: int = 3):
    """卡住的看門狗：limit_s 秒都沒有進度（新的一步、新的檢查項目）就寫出 progress.report() 與每個執行緒的位置，os._exit(code)（不等 Tk、
    不經過直譯器收尾，不會卡在結束）。取代整個行程一次的 faulthandler.dump_traceback_later：負載高時整套正常跑也會超過它的時限，
    它在別的執行緒正在跑時印 traceback 卡住、行程也不結束（0.9.13 第三輪 R3C-6）。回傳 threading.Event，set() 就停止（整套跑完時呼叫）。"""
    import faulthandler
    import threading
    stop = threading.Event()

    def _watch():
        while not stop.wait(1.0):
            if progress.idle_s() > limit_s:
                try:
                    sys.stdout.write("\n" + progress.report(f"WATCHDOG：{limit_s:.0f} 秒都沒有進度") + "\n")
                    sys.stdout.flush()
                    faulthandler.dump_traceback(file=sys.stderr, all_threads=True)
                    sys.stderr.flush()
                finally:
                    os._exit(code)
    threading.Thread(target=_watch, name="test-stall-watchdog", daemon=True).start()
    return stop


def when_started(app, fn, settle_ms: int = 300, cap_s: float = 20.0, poll_ms: int = 50) -> None:
    """子行程的 DSV 啟動完了再呼叫 fn（取代固定的 after(1500, …)：0.9.14 R3C-6，拿掉純等待）。「啟動完了」＝還原（含 B3／U13 的問句）、
    啟動參數做完（_restore_done）、啟動的第一次重畫做完（_startup_plot_done）、開啟時排著的提示已經跳出來（_autosave_notice_text 用掉了），
    再多等 settle_ms——產品啟動時排的計時器都不超過 300 ms（啟動重畫 150、提示 300、量測的防抖 150；自動重新整理 3 秒本來就在 1.5 秒之外），
    所以 fn 看到的狀態和以前等滿 1.5 秒一樣；負載高、1.5 秒還沒啟動完時會等到真的啟動完（最多 cap_s 秒，到了照樣呼叫，讓測試寫出看到的狀態）。"""
    import time
    t0 = time.monotonic()

    def _ready() -> bool:
        return (bool(getattr(app, "_restore_done", False)) and bool(getattr(app, "_startup_plot_done", False))
                and not getattr(app, "_autosave_notice_text", None))

    def _poll() -> None:
        try:
            if not app.winfo_exists():
                return
            if _ready() or time.monotonic() - t0 > cap_s:
                app.after(settle_ms, fn)
            else:
                app.after(poll_ms, _poll)
        except tk.TclError:
            pass
    app.after(poll_ms, _poll)
