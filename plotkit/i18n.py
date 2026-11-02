# -*- coding: utf-8 -*-
"""plotkit.i18n — 介面語言。原始碼裡的字串是繁體中文（也是翻譯表的鍵），`tr()` 依目前語言回傳翻譯。

用法::

    from plotkit.i18n import tr, set_language
    set_language("en")                 # "zh"（預設）或 "en"；也接受 "en_US"、"English"、"繁體中文"
    ttk.Button(root, text=tr("匯入 CSV…"))
    status.set(tr("{n} 條訊號").format(n=3))    # 有參數的字串：先 tr() 再 .format()

翻譯表在 plotkit/i18n_<code>.py（`CATALOG` dict，中文 → 該語言）；沒有的鍵回傳中文原文。
切換語言不會重畫已建好的視窗：DSV 存下偏好後重開程式才會全面換語言（跟 MATLAB 一樣）。
"""
from __future__ import annotations

import importlib
import re
from typing import Dict, Iterable, List, Optional

LANGUAGES: Dict[str, str] = {"zh": "繁體中文", "en": "English"}
DEFAULT_LANGUAGE = "zh"
_lang = DEFAULT_LANGUAGE
_catalogs: Dict[str, Dict[str, str]] = {}
_ALIASES = {"zh": "zh", "zh_tw": "zh", "zh-tw": "zh", "zh_hant": "zh", "繁體中文": "zh", "中文": "zh", "chinese": "zh",
            "en": "en", "en_us": "en", "en-us": "en", "en_gb": "en", "english": "en"}


def normalize(code: Optional[str]) -> str:
    if not code:
        return DEFAULT_LANGUAGE
    key = str(code).strip().lower().replace("-", "_")
    if key in _ALIASES:
        return _ALIASES[key]
    base = key.split("_")[0].split(".")[0]
    return _ALIASES.get(base, DEFAULT_LANGUAGE)


def _pyinstaller_hints() -> None:  # pragma: no cover - 不會被呼叫
    """翻譯表是用 importlib 動態載入的；這幾行 import 讓 PyInstaller 的靜態分析一定把它們打包進去
    （沒有 --collect-submodules plotkit 時也一樣），否則打包後選了 English 介面仍是中文。"""
    from . import i18n_en, i18n_en_core, i18n_en_dsv1, i18n_en_dsv2, i18n_en_dsv3, i18n_en_plotkit, i18n_en_keys, i18n_en_folder, i18n_en_iq, i18n_en_tools, i18n_en_tools_d, i18n_en_tools_e, i18n_en_batch1, i18n_en_batch2, i18n_en_batch3, i18n_en_batch4, i18n_en_fix1, i18n_en_fix2, i18n_en_fix3, i18n_en_i13, i18n_en_axnames, i18n_en_0913x, i18n_en_0914p, i18n_en_0915s  # noqa: F401


def catalog(code: str) -> Dict[str, str]:
    code = normalize(code)
    if code == "zh":
        return {}
    if code not in _catalogs:
        try:
            mod = importlib.import_module(f"plotkit.i18n_{code}")
            _catalogs[code] = dict(getattr(mod, "CATALOG", {}))
        except Exception as e:                   # 不讓程式掛掉，但要留下線索（打包漏了翻譯表時介面會變回中文）
            _catalogs[code] = {}
            try:
                import sys
                if sys.stderr is not None:           # --windowed 的打包版 stderr 可能是 None
                    print(f"plotkit.i18n: 載入 {code} 翻譯表失敗：{type(e).__name__}: {e}", file=sys.stderr)
            except Exception:
                pass
    return _catalogs[code]


def set_language(code: Optional[str]) -> str:
    """設定目前語言；回傳正規化後的代碼。"""
    global _lang
    _lang = normalize(code)
    catalog(_lang)
    return _lang


def get_language() -> str:
    return _lang


def language_name(code: Optional[str] = None) -> str:
    return LANGUAGES.get(normalize(code or _lang), str(code))


def tr(s: str) -> str:
    """翻譯一個字串（鍵 = 中文原文）；目前語言是中文或沒有翻譯時回傳原文。"""
    if _lang == "zh" or not s:
        return s
    return _catalogs.get(_lang, {}).get(s, s)


# --- 給 selftest 用：找出原始碼裡有 tr() 但翻譯表沒有的鍵 ---------------------------------------
_TR_RE = re.compile(r"""\btr\(\s*(?P<q>"""r'"""|\'\'\'|"|\')(?P<s>.*?)(?P=q)\s*\)', re.S)


def _literal(src_quote: str, body: str) -> str:
    import ast
    try:
        return ast.literal_eval(src_quote + body + src_quote)
    except Exception:
        return body


def tr_keys_in_source(paths: Iterable[str]) -> List[str]:
    """掃描 .py 檔，回傳所有 tr("…") 的字面值（只抓單純字串字面值）。"""
    out: List[str] = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                src = f.read()
        except Exception:
            continue
        for m in _TR_RE.finditer(src):
            out.append(_literal(m.group("q"), m.group("s")))
    return out


def missing_keys(code: str, paths: Iterable[str]) -> List[str]:
    cat = catalog(code)
    return sorted({k for k in tr_keys_in_source(paths) if k not in cat})


def placeholder_mismatches(code: str) -> List[str]:
    """翻譯裡 {名稱} 佔位符和原文不一致的鍵。"""
    cat = catalog(code)
    bad = []
    for k, v in cat.items():
        if set(re.findall(r"\{[^{}]*\}", k)) != set(re.findall(r"\{[^{}]*\}", v)):
            bad.append(k)
    return sorted(bad)
