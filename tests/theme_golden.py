# -*- coding: utf-8 -*-
"""MATLAB 兩個主題（dark／light）的金樣：「深色／淺色兩個 MATLAB 主題不動」（audit 決定檔 decisions_skins.md；1.0.0 深度審查第 1 輪
B5／測試強度：以前只檢查約 10 個色票值，把 dark 的 Primary 按鈕字色、tooltip 底色、圖示的白、分頁鈕的停用字改掉五套照樣全過）。

快照的內容（每個主題）：
- 色票 TOKENS（比對時只容許 1.0.0 新增的 6 個鍵：strip_text…primary_hover——它們在 dark／light 等於以前寫死的值，另外由 selftest 檢查）；
- ttk 樣式資料庫：每個樣式的 configure／map／layout；
- 元素圖片：每個 Pk<主題>.<元素> 的狀態順序，與每張圖「怎麼畫的」（Theme._img 的寬、高、填色、框色、圓角、內縮，畫筆函式的參數）——
  畫圖的程式沒改，輸入一樣＝像素一樣；不直接比像素，所以 Mac 與 Windows（Pillow 版本不同）用同一份金樣；
- option database（傳統 tk 元件、下拉清單、選單的顏色與字型）；選單底色／選中字色；Tooltip 真的顯示一次的底色；圖示配色（一般與分頁列）；
- 繪圖風格 default／matlab／matlab-dark。

用法（一律安靜模式、在獨立行程裡跑——要在主題第一次建立之前裝好 Theme._img 的紀錄器）：
  python tests/theme_golden.py snapshot <out.json> [--repo <舊版程式的資料夾>]
  python tests/theme_golden.py compare [<金樣.json>]       # 倒出目前程式的快照、和金樣比；印 GOLDEN OK 或 GOLDEN DIFF 與差異
  python tests/theme_golden.py radii                       # 八個主題建元素圖片時真的用了各自的圓角（RADIUS_PX）：RADII OK
                                                           # （欄位、一般按鈕，以及按鈕大小的每一張元素圖片：主要按鈕、工具鈕、快速存取鈕…）
金樣 tests/theme_golden_0914.json＝從 0.9.14（20a4492，main）倒出：
  python tests/theme_golden.py snapshot tests/theme_golden_0914.json --repo <20a4492 的 git archive>
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GOLDEN = os.path.join(HERE, "theme_golden_0914.json")
NEW_TOKEN_KEYS = {"strip_text", "strip_text_disabled", "strip_icon_fill", "strip_icon_fg2", "primary_pressed", "primary_hover"}   # 1.0.0 新增
THEMES = ("dark", "light")
STYLE_NAMES_RE = r'"([A-Za-z.]+\.T[A-Za-z]+|T[A-Z][a-z]+(?:\.[A-Za-z]+)?)"'


def _norm(v):
    """Tcl 物件、tuple 一律變成字串／list，JSON 往返後比得起來。"""
    if isinstance(v, (list, tuple)):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _norm(x) for k, x in v.items()}
    if isinstance(v, (bool, int, float)) or v is None:
        return v
    return str(v)


def _draw_sig(fn):
    """畫筆函式（_check_img／_arrow_img／_tri_img 的 draw）帶進去的參數：顏色、方向、勾選與否、大小。"""
    if fn is None:
        return None
    out = {}
    for name, cell in zip(fn.__code__.co_freevars, fn.__closure__ or ()):
        try:
            v = cell.cell_contents
        except ValueError:
            continue
        if isinstance(v, (str, int, float, bool)):
            out[name] = v
    return out


def snapshot(repo=None):
    sys.path.insert(0, REPO)
    from tests_common import install_quiet
    install_quiet()
    if repo:
        sys.path.insert(0, os.path.abspath(repo))
    import tkinter as tk
    from tkinter import ttk
    import plotkit.theme as T
    import plotkit.styles as S
    src_dir = os.path.dirname(os.path.abspath(T.__file__))
    sigs = {}
    _img0 = T.Theme._img

    def _img_spy(self, w, h, fill, outline, radius=0, draw=None, inset=0):
        img = _img0(self, w, h, fill, outline, radius, draw, inset)
        if img is not None:
            sigs[str(img)] = {"w": w, "h": h, "fill": fill, "outline": outline, "radius": radius, "inset": inset, "draw": _draw_sig(draw)}
        return img
    T.Theme._img = _img_spy
    odb = []
    _oa0 = tk.Misc.option_add

    def _oa_spy(self, pattern, value, priority=None):
        odb.append([str(pattern), str(value), None if priority is None else str(priority)])
        return _oa0(self, pattern, value, priority)
    tk.Misc.option_add = _oa_spy
    names = set(re.findall(STYLE_NAMES_RE, open(os.path.join(src_dir, "theme.py"), encoding="utf-8").read()))
    if os.path.exists(GOLDEN):
        try:
            names |= set(json.load(open(GOLDEN, encoding="utf-8"))["dark"]["styles"])
        except Exception:
            pass
    root = tk.Tk()
    root.geometry("300x200")
    lbl = ttk.Label(root, text="tip")
    lbl.pack()
    root.update()
    res = {"meta": {"src": src_dir, "scale": None}}
    for name in THEMES:
        del odb[:]
        th = T.apply(root, name)
        root.update()
        res["meta"]["scale"] = th.scale
        st = ttk.Style(root)
        styles = {}
        for s in sorted(names):
            d = {}
            try:
                d["configure"] = _norm(st.configure(s) or {})
                d["map"] = _norm(st.map(s) or {})
            except Exception as e:                       # 樣式不存在（另一版才有）
                d["error"] = type(e).__name__
            try:
                d["layout"] = _norm(st.layout(s))
            except Exception:
                d["layout"] = None
            styles[s] = d
        elements = {}
        for (interp, el), specs in T._ELEMENT_SPECS.items():
            if interp == th.interp and el.startswith(f"Pk{name.title()}."):
                elements[el] = [[list(map(str, s_)), sigs.get(str(im), {"unknown": f"{im.width()}x{im.height()}"})] for s_, im in specs]
        tip = T.Tooltip(lbl, "x")
        tip._show()
        root.update()
        kids = tip._win.winfo_children() if getattr(tip, "_win", None) else []
        tip_bg = str(kids[0].cget("background")) if kids else None
        tip._hide()
        root.update()
        res[name] = {
            "tokens": dict(T.TOKENS[name]),
            "styles": styles,
            "elements": elements,
            "option_db": list(odb),
            "menu_bg": th.menu_bg, "menu_active_fg": th.menu_active_fg,
            "tooltip_bg": tip_bg,
            "icon_palette": th.icon_palette(False), "icon_palette_strip": th.icon_palette(True),
            "radius": getattr(th, "radius", T.PX["radius"]),
            "dark": getattr(th, "dark", name == "dark"),
            "root_bg": str(root.cget("background")),
        }
    res["plot_styles"] = _norm({k: S.STYLES[k] for k in ("default", "matlab", "matlab-dark")})
    T.apply(root, "dark")
    root.update()
    root.destroy()
    T.Theme._img = _img0
    tk.Misc.option_add = _oa0
    return res


def diff(gold, new):
    """金樣 vs 目前：回傳差異的路徑清單（tokens 只容許多出 NEW_TOKEN_KEYS；樣式只比金樣裡有的；縮放不同時不比尺寸相關的樣式與元素）。"""
    out = []

    def walk(a, b, p):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in sorted(set(a) | set(b)):
                walk(a.get(k, "<沒有>"), b.get(k, "<沒有>"), f"{p}/{k}")
        elif a != b:
            out.append(f"{p}: 金樣 {str(a)[:120]} ≠ 目前 {str(b)[:120]}")
    same_scale = gold["meta"].get("scale") == new["meta"].get("scale")
    for name in THEMES:
        g, n = gold[name], new[name]
        nt = dict(n["tokens"])
        extra = set(nt) - set(g["tokens"])
        if extra - NEW_TOKEN_KEYS:
            out.append(f"/{name}/tokens: 多出沒預期的鍵 {sorted(extra - NEW_TOKEN_KEYS)}")
        for k in extra:
            nt.pop(k)
        walk(g["tokens"], nt, f"/{name}/tokens")
        for key in ("menu_bg", "menu_active_fg", "tooltip_bg", "icon_palette", "icon_palette_strip", "radius", "dark", "root_bg", "option_db"):
            if key == "option_db" and not same_scale:
                walk([x for x in g[key] if not x[0].endswith(("padX", "padY"))], [x for x in n[key] if not x[0].endswith(("padX", "padY"))], f"/{name}/{key}")
            else:
                walk(g[key], n[key], f"/{name}/{key}")
        if same_scale:
            walk(g["styles"], {k: n["styles"].get(k, "<沒有>") for k in g["styles"]}, f"/{name}/styles")
            walk(g["elements"], n["elements"], f"/{name}/elements")
    walk(gold["plot_styles"], new["plot_styles"], "/plot_styles")
    return out, same_scale


def radii():
    """八個主題建元素圖片時用的圓角（Theme._img 的 radius 參數）：最常出現的值、欄位與一般按鈕每一張圖的圓角，以及按鈕大小（px(24)）的每一張元素圖片
    （主要按鈕、工具鈕、快速存取鈕也算）的圓角——圓角真的畫進圖片，不只是 Theme.radius 屬性。"""
    sys.path.insert(0, REPO)
    from tests_common import install_quiet
    install_quiet()
    from collections import Counter
    import tkinter as tk
    import plotkit.theme as T
    used = {}
    _img0 = T.Theme._img

    def _img_spy(self, w, h, fill, outline, radius=0, draw=None, inset=0):
        if fill or outline:                            # 有填色或框的面（按鈕、欄位、分頁…）；捲軸、勾選框是另外的固定圓角
            used.setdefault(self.name, []).append((fill, outline, radius, w, h))
        return _img0(self, w, h, fill, outline, radius, draw, inset)
    T.Theme._img = _img_spy
    root = tk.Tk()
    out = {}
    for n in T.THEMES:
        th = T.apply(root, n)
        root.update()
        t, rec = th.t, used.get(n, [])
        s24 = th.px(24)
        # 1.0.0 第 2 輪（突變 N19）：不只看眾數——欄位（填 input、框 border／focus）與一般按鈕（填 bg、框 border／border2／focus）的每一張圖都要是主題的圓角
        # 1.0.0 第 3 輪（突變 N25～N27）：按鈕大小（px(24)×px(24)）、有填色或框的每一張元素圖片——一般按鈕、主要按鈕、工具鈕、快速存取鈕、欄位——
        # 圓角都要是主題的（all24），而且張數 ≥ 20（n24；目前每個主題 22 張），不是只看填 bg／input 的兩類
        out[n] = {"mode": Counter(r for _, _, r, _, _ in rec).most_common(1)[0][0] if rec else None, "want": th.px(T.RADIUS_PX[n]),
                  "fields": sorted({r for f, o, r, _, _ in rec if f == t["input"] and o in (t["border"], t["focus"])}),
                  "buttons": sorted({r for f, o, r, _, _ in rec if f == t["bg"] and o in (t["border"], t["border2"], t["focus"])}),
                  "all24": sorted({r for _, _, r, w, h in rec if w == s24 and h == s24}),
                  "n24": sum(1 for _, _, _, w, h in rec if w == s24 and h == s24),
                  "bad24": sorted({(f, o, r) for f, o, r, w, h in rec if w == s24 and h == s24 and r != th.px(T.RADIUS_PX[n])})[:4]}
    T.apply(root, "dark")
    root.destroy()
    return out


def main(argv):
    if argv and argv[0] == "radii":
        out = radii()
        ok = all(v["mode"] == v["want"] and v["fields"] == [v["want"]] and v["buttons"] == [v["want"]]
                 and v["all24"] == [v["want"]] and v["n24"] >= 20 for v in out.values())
        print(f"RADII {'OK' if ok else 'DIFF'} {json.dumps(out, ensure_ascii=False, sort_keys=True)}")
        return 0 if ok else 1
    if len(argv) >= 2 and argv[0] == "snapshot":
        repo = argv[argv.index("--repo") + 1] if "--repo" in argv else None
        res = snapshot(repo)
        with open(argv[1], "w", encoding="utf-8") as f:
            json.dump(res if repo is None else {**res, "meta": {**res["meta"], "src": "0.9.14 (20a4492)"}},
                      f, ensure_ascii=False, indent=1, sort_keys=True)
        print("SNAPSHOT", argv[1], {n: (len(res[n]["styles"]), len(res[n]["elements"]), len(res[n]["option_db"])) for n in THEMES})
        return 0
    if argv and argv[0] == "compare":
        gold = json.load(open(argv[1] if len(argv) > 1 else GOLDEN, encoding="utf-8"))
        new = json.loads(json.dumps(snapshot(), ensure_ascii=False))
        out, same_scale = diff(gold, new)
        counts = {n: (len(gold[n]["styles"]), len(gold[n]["elements"]), len(gold[n]["option_db"])) for n in THEMES}
        print(f"GOLDEN {'OK' if not out else 'DIFF'} 比了 {counts}（樣式、元素、option）；縮放 {new['meta']['scale']}"
              f"{'' if same_scale else '（和金樣不同：尺寸相關的樣式與元素沒比）'}；差異 {len(out)} 處")
        for line in out[:40]:
            print("  " + line)
        return 0 if not out else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
