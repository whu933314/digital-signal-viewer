# -*- coding: utf-8 -*-
"""前處理（MATLAB Signal Analyzer R2025a 的 PREPROCESS 分頁）——DSV 的黏合層：參數面板的欄位、預設值、驗證訊息，以及把
參數交給已經對過 MATLAB 的計算模組（dsv_filter／dsv_clean／dsv_convert；這裡不改它們的數學）。純 Python＋numpy，不碰 Tk，
signal_viewer.py 的「前處理」分頁與衍生訊號（Signal.derive＝pp_*、Signal.pp＝參數）用它。

對照 MATLAB（字串來源：MATLAB Signal Analyzer 前處理介面顯示的英文與簡中訊息；
欄位順序、預設值、驗證規則：研究報告 b34/reports.json 對照 Signal Analyzer 網頁介面的結果）：
- 圖庫 FILTER／CLEAN／CONVERT → 區段「濾波器」（低通／高通／帶通／帶阻）、「清理」（平滑／去趨勢）、「轉換」（重取樣／包絡）。
  MATLAB 另有 Denoise（要 Wavelet Toolbox）、Fill Missing、CUSTOM FUNCTIONS，DSV 沒做。
- 每個函式一個 Function Parameters 面板：欄位、預設值、單位清單、驗證訊息照 MATLAB（寬鬆解析也照做：取開頭的數字，「40abc」＝40）。
- DSV 的訊號一律有時間資訊（fs＝SPS × symbol rate，均勻取樣；t＝t0 + n/fs，t0＝起點 x0／symbol rate），所以面板永遠是 MATLAB
  「均勻時間訊號」的版本：濾波用 Hz（不提供 ×π rad/sample）、平滑／去趨勢的單位是 ps…年（沒有「樣本」）、重取樣不出現
  INTERPOLATION 區（那是非均勻訊號才有的）、包絡的單位是「樣本」＋ps…年。
- 結果是衍生訊號（使用者 2026-10-24 決定 A2+A3）：MATLAB 覆寫選取的訊號，DSV 改成新增一條、保留原訊號、存參數、來源改了自動重算。
- 濾波只做 FIR（A4）：訊號太短時 dsv_filter 丟 SignalTooShortForFIR，面板顯示它的繁體中文訊息（含需要的長度）。

DSV 自己決定的（MATLAB 沒有對應或無法確定；README「前處理」一節也列出）：
- 平滑的視窗持續時間驗證：研究時判斷 MATLAB 在時間模式也顯示「基於採樣的…必須為正整數」（樣本版訊息，看起來是 MATLAB 的問題），
  DSV 用同一欄位的時間版訊息「以時間為單位的視窗持續時間長度必須為正數值純量」。包絡 Peak 的訊息照它自己的單位選（研究時判斷 MATLAB
  這裡看的是 Window Length 的單位，看起來也是 MATLAB 的問題）。
- 頻率單位 cycles/year 用 365 天（dsv_convert.FREQ_UNIT_HZ，Resample 面板的換算；濾波面板的換算研究沒有記錄，用同一個）；
  平滑／去趨勢的「年」＝365.2425 天（dsv_clean.TIME_UNITS），包絡的「年」＝365 天（dsv_convert.TIME_UNIT_S），各照研究報告。
- 套用後的警告／錯誤對話框：MATLAB 只對 ForcedAllpassDesign／ForcedAllstopDesign 兩種濾波警告跳對話框（LpHp／BpBs 兩種字句），
  DSV 照做；平滑的次數調整警告、重取樣 Auto 不處理均勻訊號也照 MATLAB 用警告。前綴「所選訊號／部分所選訊號」：全部訊號都有
  這個訊息＝所選，否則＝部分。
- 文字欄位的 placeholder（placeholder_text）：研究記錄的通帶頻率／阻帶衰減／取樣因子「輸入值」、分段斷點「指定逗號分隔值」；
  下／上通帶頻率照通帶頻率；包絡的三個文字欄位研究沒記錄 → 不顯示。
- 包絡方法 Peak 的英文：「峰值」這個鍵在量測分頁已譯成「Peaks」，英文介面改查「峰值（包絡方法）」→「Peak」（MATLAB 的英文）。
- 設定檔讀回來的參數先用面板同一套規則再驗一次（check_params）：手改壞的檔案在狀態列看到 MATLAB 的欄位訊息（例如缺 fpass →
  「通帶頻率必須為正純量」），不是 Python 的例外文字。數值欄存的必須是數字（手改成字串、bool、NaN 的當空白 → 那個欄位的訊息），
  次數／N 必須是整數（2.5 →「次數必須設為正整數。」、「以樣本為單位的視窗長度必須為正整數」），不會等到計算模組才用它的原文報錯。
- 工具提示：研究報告有記錄的欄位用 MATLAB 的文字（阻帶衰減的提示就是標籤「阻帶衰減(dB)」）；沒記錄的（重取樣的頻率單位／重取樣方法、
  平滑的持續時間單位、帶通／帶阻的下／上通帶頻率）用標籤本身，不自己編。面板「說明」鈕的提示「前處理訊號說明」是 DSV 自己的（研究沒記錄）。
- 「清理」區段的順序是 平滑、去趨勢（使用者決定的措辭「清理（平滑／去趨勢）」）；MATLAB 的圖庫是 Detrend 在 Smooth 前面。
- 來源沒有資料的結果（來源自己算不出來——例如接在 lowpass(太短的訊號) 後面的包絡——或是空的訊號）不算成功：compute 丟 PreprocessError
  （emptySource），清單 Fmt 顯示 error、狀態列說明來源的問題（MATLAB 沒有對應：它覆寫訊號，沒有連鎖）。
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

import dsv_clean
import dsv_convert
import dsv_filter
from plotkit.i18n import get_language, tr

FUNCS = ("lowpass", "highpass", "bandpass", "bandstop", "smooth", "detrend", "resample", "envelope")
FILTERS = ("lowpass", "highpass", "bandpass", "bandstop")
KINDS = ("pp_lowpass", "pp_highpass", "pp_bandpass", "pp_bandstop", "pp_smooth", "pp_detrend", "pp_resample",
         "pp_envelope_upper", "pp_envelope_lower")
GALLERY = (("filter", FILTERS), ("clean", ("smooth", "detrend")), ("convert", ("resample", "envelope")))
ICONS = {"lowpass": "pp_lowpass", "highpass": "pp_highpass", "bandpass": "pp_bandpass", "bandstop": "pp_bandstop",
         "smooth": "pp_smooth", "detrend": "pp_detrend", "resample": "pp_resample", "envelope": "pp_envelope"}
# 衍生訊號的名稱（像 MATLAB 產生的程式碼的函式名）與清單 Fmt 欄的標籤
_FN_NAME = {"pp_lowpass": "lowpass", "pp_highpass": "highpass", "pp_bandpass": "bandpass", "pp_bandstop": "bandstop",
            "pp_smooth": "smoothdata", "pp_detrend": "detrend", "pp_resample": "resample",
            "pp_envelope_upper": "upperEnvelope", "pp_envelope_lower": "lowerEnvelope"}

# 單位（MATLAB 的順序；值 → 倍率）
FREQ_UNITS = ("cyclesperyear", "cyclesperday", "cyclesperhour", "cyclesperminute", "mHz", "Hz", "kHz", "MHz", "GHz", "THz")
TIME_UNITS = ("ps", "ns", "us", "ms", "s", "minutes", "hours", "days", "years")
ENV_UNITS = ("samples",) + TIME_UNITS
SMOOTH_METHODS = dsv_clean.METHODS                  # movmean, movmedian, gaussian, lowess, loess, rlowess, rloess, sgolay
DETREND_METHODS = dsv_clean.DETREND_METHODS          # constant, linear, piecewiselinear
ENV_METHODS = dsv_convert.ENVELOPE_METHODS           # hilbert, fir, rms, peak

STEEP_MIN, STEEP_MAX, STEEP_STEP = dsv_filter.STEEPNESS_MIN, dsv_filter.STEEPNESS_MAX, dsv_filter.STEEPNESS_STEP


class PreprocessError(Exception):
    """一條訊號沒有被處理：message 已是目前語言的文字；warning＝True 表示 MATLAB 用警告對話框（例如重取樣 Auto 不處理均勻訊號）。"""

    def __init__(self, message: str, warning: bool = False, ident: str = ""):
        super().__init__(message)
        self.message = message
        self.warning = warning
        self.ident = ident


# ---------------------------------------------------------------- 文字（每次呼叫才 tr()：語言在建 UI 前才設定）
def func_label(func: str) -> str:
    return {"lowpass": tr("低通"), "highpass": tr("高通"), "bandpass": tr("帶通"), "bandstop": tr("帶阻"), "smooth": tr("平滑"),
            "detrend": tr("去趨勢"), "resample": tr("重取樣"), "envelope": tr("包絡")}[func]


def func_tip(func: str) -> str:
    """圖庫按鈕的提示（MATLAB 的 preprocess*Desc），加一句 DSV 的用法。"""
    base = {"lowpass": tr("套用低通濾波器"), "highpass": tr("套用高通濾波器"), "bandpass": tr("套用帶通濾波器"), "bandstop": tr("套用帶阻濾波器"),
            "smooth": tr("平滑含雜訊的資料"), "detrend": tr("去除常數、線性或分段線性趨勢"),
            "resample": tr("均勻時更改取樣率，不均勻時進行內插"), "envelope": tr("將資料轉換為上包絡或下包絡")}[func]
    return base + "\n" + tr("開啟「函式參數」面板；按「套用」對「已繪訊號」選取的每條訊號各新增一條結果（衍生訊號，原訊號保留、來源改了自動重算）")


def section_label(key: str) -> str:
    return {"filter": tr("濾波器"), "clean": tr("清理"), "convert": tr("轉換")}[key]


def header_label(func: str) -> str:
    return {"lowpass": tr("低通參數"), "highpass": tr("高通參數"), "bandpass": tr("帶通參數"), "bandstop": tr("帶阻參數"),
            "smooth": tr("平滑參數"), "detrend": tr("去趨勢參數"), "resample": tr("重取樣參數"), "envelope": tr("包絡參數")}[func]


def apply_tip(func: str) -> str:
    return {"lowpass": tr("對訊號表中所選訊號套用低通濾波"), "highpass": tr("對訊號表中所選訊號套用高通濾波"),
            "bandpass": tr("對訊號表中所選訊號套用帶通濾波"), "bandstop": tr("對訊號表中所選訊號套用帶阻濾波"),
            "smooth": tr("對表中的所選訊號套用平滑處理"), "detrend": tr("對訊號表中的所選訊號套用去趨勢處理"),
            "resample": tr("對訊號表中的所選訊號套用重取樣"), "envelope": tr("對訊號表中的所選訊號套用包絡")}[func]


def restore_tip(func: str) -> str:
    return {"lowpass": tr("還原預設低通濾波器參數"), "highpass": tr("還原預設高通濾波器參數"), "bandpass": tr("還原預設帶通濾波器參數"),
            "bandstop": tr("還原預設帶阻濾波器參數"), "smooth": tr("還原預設平滑參數"), "detrend": tr("還原預設去趨勢參數"),
            "resample": tr("還原預設重取樣參數"), "envelope": tr("還原預設包絡參數")}[func]


def unit_label(u: str) -> str:
    lab = {"cyclesperyear": tr("週期/年"), "cyclesperday": tr("週期/天"), "cyclesperhour": tr("週期/小時"), "cyclesperminute": tr("週期/分鐘"),
           "minutes": tr("分鐘"), "hours": tr("小時"), "days": tr("天"), "years": tr("年"), "samples": tr("樣本"), "us": "μs"}
    return lab.get(u, u)


def _peak_label() -> str:
    """包絡方法 Peak（MATLAB en「Peak」、zh_CN「峰值」）。「峰值」這個鍵在量測分頁已經是 PEAKS 區段的「Peaks」（i18n_en_batch1），
    合併後的翻譯表一個鍵只能有一個英文，所以英文介面改查另一個鍵（i18n_en_batch4：「Peak」）；繁中仍顯示 MATLAB 的「峰值」。"""
    return tr("峰值") if _zh() else tr("峰值（包絡方法）")


def option_label(field_key: str, value: str) -> str:
    """下拉選單的項目文字。"""
    if field_key in ("units", "rate_units"):
        return unit_label(value)
    if field_key in ("dur_units", "bp_units", "wlen_units", "sep_units"):
        return unit_label(value)
    tab = {
        "steep_mode": {"single": tr("陡度"), "dual": tr("下頻帶陡度")},
        "method": {"movmean": tr("移動平均"), "movmedian": tr("移動中位數"), "gaussian": tr("高斯"), "lowess": tr("線性迴歸"),
                   "loess": tr("二次迴歸"), "rlowess": tr("穩健線性迴歸"), "rloess": tr("穩健二次迴歸"), "sgolay": "Savitzky-Golay",
                   "constant": tr("常數"), "linear": tr("線性"), "piecewiselinear": tr("分段線性")},
        "wintype": {"duration": tr("持續時間"), "smoothingfactor": tr("平滑因子")},
        "rmethod": {"samplerate": tr("取樣率"), "samplefactor": tr("取樣因子")},
        "output": {"upper": tr("上包絡"), "lower": tr("下包絡")},
        "emethod": {"hilbert": tr("希爾伯特"), "fir": "FIR", "rms": "RMS", "peak": _peak_label()},
    }
    return tab.get(field_key, {}).get(value, value)


def placeholder_text(func: str, key: str) -> str:
    """文字欄位空白時的灰色提示（MATLAB 的 placeholder；研究報告記錄的：通帶頻率與阻帶衰減「輸入值」（Enter Value）、重取樣的取樣因子
    「輸入值」、分段斷點「指定逗號分隔值」（Specify comma-separated values））。帶通／帶阻的下／上通帶頻率是同一種文字欄位，照通帶頻率；
    包絡的濾波器階數／視窗長度／最大值間隔研究沒有記錄 placeholder，DSV 不顯示（README「前處理」一節列出）。"""
    if key == "breakpoints":
        return tr("指定逗號分隔值")
    if key in ("fpass", "fpass1", "fpass2", "atten") or (func == "resample" and key == "factor"):
        return tr("輸入值")
    return ""


def pane_label(key: str) -> str:
    """面板裡的小標題（MATLAB 是大寫：FILTER SPECIFICATIONS、METHOD、WINDOW…；英文介面一樣轉大寫）。"""
    t = {"filter_specs": tr("濾波器設定"), "method": tr("方法"), "window": tr("視窗"), "resample_settings": tr("重取樣設定"),
         "envelope_settings": tr("包絡設定")}[key]
    return t.upper() if t.isascii() else t


def field_label(func: str, key: str, form: Optional[Dict[str, str]] = None) -> str:
    form = form or {}
    if key == "wlen_units":
        return tr("長度單位")
    if key == "sep_units":
        return tr("間隔單位")
    if key == "method":
        return tr("平滑方法") if func == "smooth" else tr("去趨勢方法")
    return {"units": tr("頻率單位"), "fpass": tr("通帶頻率"), "fpass1": tr("下通帶頻率"), "fpass2": tr("上通帶頻率"),
            "steepness": tr("陡度"), "steepness2": tr("上頻帶陡度"), "atten": tr("阻帶衰減(dB)"),
            "degree": tr("次數"), "wintype": tr("視窗類型"), "dur_units": tr("持續時間單位"), "window": tr("視窗持續時間"),
            "factor": tr("取樣因子") if func == "resample" else tr("平滑因子"),
            "bp_units": tr("斷點單位"), "breakpoints": tr("分段斷點"),
            "rmethod": tr("重取樣方法"), "rate_units": tr("頻率單位"), "rate": tr("取樣率"),
            "output": tr("包絡"), "emethod": tr("方法"), "order": tr("濾波器階數"), "wlen": tr("視窗長度"), "maxsep": tr("最大值間隔")}.get(key, key)


def field_tip(func: str, key: str, form: Optional[Dict[str, str]] = None) -> str:
    """欄位的工具提示：研究報告記錄到的 MATLAB 文字（阻帶衰減的提示＝標籤「阻帶衰減(dB)」、通帶頻率的提示＝「通帶頻率」）；
    沒記錄的（重取樣的頻率單位／重取樣方法、平滑的持續時間單位、下／上通帶頻率）用標籤本身，不自己編（README「前處理」一節列出）。"""
    form = form or {}
    if key == "steepness1":
        return tr("下過渡帶陡度") if form.get("steep_mode") == "dual" else tr("過渡帶陡度")
    if key == "steep_mode":
        return tr("為下過渡帶和上過渡帶指定同一個陡度值，或為下過渡帶和上過渡帶各指定一個值")
    if key == "method":
        return tr("選擇平滑方法") if func == "smooth" else tr("選擇去趨勢方法")
    if key == "factor":
        return tr("指定更改所選訊號取樣率所使用的因子") if func == "resample" else tr("視窗平滑因子")
    if key == "units" and func in FILTERS:
        return tr("通帶頻率單位")
    tips = {"steepness": tr("過渡帶陡度"), "steepness2": tr("上過渡帶陡度"),
            "degree": tr("選擇「Auto」作為 Savitzky-Golay 次數，或輸入值"), "wintype": tr("選擇如何控制視窗長度"),
            "window": tr("選擇「Auto」作為視窗持續時間，或輸入值"),
            "bp_units": tr("分段斷點單位。對於具有時間值的訊號，會使用最接近指定輸入時間的樣本索引作為分段斷點值"),
            "breakpoints": tr("為相鄰分段線性段之間的斷點指定逗號分隔值"),
            "rate": tr("選擇「Auto」作為目標取樣率，或輸入值"),
            "output": tr("選擇輸出包絡"), "emethod": tr("選擇包絡方法"),
            "wlen_units": tr("視窗長度單位。如果是時間單位，會使用有效的取樣率將指定的輸入時間轉換為樣本"),
            "sep_units": tr("局部最大值間隔單位。如果是時間單位，會使用有效的取樣率將指定的輸入時間轉換為樣本"),
            "order": tr("指定 FIR 濾波器階數以計算解析包絡"), "wlen": tr("指定滑動視窗長度"), "maxsep": tr("指定局部最大值間隔")}
    return tips.get(key) or field_label(func, key, form)      # 研究沒記錄提示的欄位（含阻帶衰減(dB)、通帶頻率）：提示＝標籤


# ---------------------------------------------------------------- 欄位規格
# 每個欄位：key、型態（combo＝唯讀下拉、edit＝可輸入的下拉（項目只有 Auto）、entry、spin）、選項、預設字串
def _f(key: str, kind: str, options: Sequence[str] = (), default: str = "", spin: Optional[Tuple[float, float, float]] = None) -> Dict[str, Any]:
    return {"key": key, "kind": kind, "options": tuple(options), "default": default, "spin": spin}


def form_spec(func: str) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """面板的區塊與欄位（照 MATLAB 面板的順序）。帶通／帶阻的第 4 列是「陡度／下頻帶陡度」下拉＋陡度 spinner（MATLAB 同一列）。"""
    steep = (STEEP_MIN, STEEP_MAX, STEEP_STEP)
    if func in ("lowpass", "highpass"):
        return [("filter_specs", [_f("units", "combo", FREQ_UNITS, "Hz"), _f("fpass", "entry"),
                                  _f("steepness", "spin", (), "0.85", steep), _f("atten", "entry", (), "60")])]
    if func in ("bandpass", "bandstop"):
        return [("filter_specs", [_f("units", "combo", FREQ_UNITS, "Hz"), _f("fpass1", "entry"), _f("fpass2", "entry"),
                                  _f("steep_mode", "combo", ("single", "dual"), "single"), _f("steepness1", "spin", (), "0.85", steep),
                                  _f("steepness2", "spin", (), "0.85", steep), _f("atten", "entry", (), "60")])]
    if func == "smooth":
        return [("method", [_f("method", "combo", SMOOTH_METHODS, "movmean"), _f("degree", "edit", ("Auto",), "Auto")]),
                ("window", [_f("wintype", "combo", ("duration", "smoothingfactor"), "duration"), _f("dur_units", "combo", TIME_UNITS, "s"),
                            _f("window", "edit", ("Auto",), "Auto"), _f("factor", "spin", (), "0.25", (0.0, 1.0, 0.05))])]
    if func == "detrend":
        return [("method", [_f("method", "combo", DETREND_METHODS, "linear"), _f("bp_units", "combo", TIME_UNITS, "s"),
                            _f("breakpoints", "entry")])]
    if func == "resample":
        return [("resample_settings", [_f("rmethod", "combo", ("samplerate", "samplefactor"), "samplerate"),
                                       _f("rate_units", "combo", FREQ_UNITS, "Hz"), _f("rate", "edit", ("Auto",), ""),
                                       _f("factor", "entry")])]
    if func == "envelope":
        return [("envelope_settings", [_f("output", "combo", ("upper", "lower"), "upper"), _f("emethod", "combo", ENV_METHODS, "hilbert"),
                                       _f("wlen_units", "combo", ENV_UNITS, "samples"), _f("sep_units", "combo", ENV_UNITS, "samples"),
                                       _f("order", "entry"), _f("wlen", "entry"), _f("maxsep", "entry")])]
    raise KeyError(func)


def fields(func: str) -> List[Dict[str, Any]]:
    return [f for _p, fl in form_spec(func) for f in fl]


def default_form(func: str) -> Dict[str, str]:
    """MATLAB 的預設：時間訊號的通帶頻率、重取樣的取樣率／因子、包絡的長度預設都是空白，要自己填。"""
    return {f["key"]: f["default"] for f in fields(func)}


def restore_defaults(func: str, form: Dict[str, str]) -> Dict[str, str]:
    """「還原預設值」。MATLAB 的 Detrend 只還原方法與單位，不清掉已輸入的斷點（報告：Restore Defaults resets only method and units）。"""
    new = default_form(func)
    if func == "detrend":
        new["breakpoints"] = form.get("breakpoints", "")
    return new


def visible(func: str, key: str, form: Dict[str, str]) -> bool:
    """欄位顯示規則（MATLAB 的 hide／show）。"""
    if func in ("bandpass", "bandstop") and key == "steepness2":
        return form.get("steep_mode") == "dual"
    if func == "smooth":
        if key == "degree":
            return form.get("method") == "sgolay"
        if key in ("dur_units", "window"):
            return form.get("wintype") == "duration"
        if key == "factor":
            return form.get("wintype") == "smoothingfactor"
    if func == "detrend" and key in ("bp_units", "breakpoints"):
        return form.get("method") == "piecewiselinear"
    if func == "resample":
        if key in ("rate_units", "rate"):
            return form.get("rmethod") != "samplefactor"
        if key == "factor":
            return form.get("rmethod") == "samplefactor"
    if func == "envelope":
        m = form.get("emethod")
        return {"wlen_units": m == "rms", "sep_units": m == "peak", "order": m == "fir", "wlen": m == "rms", "maxsep": m == "peak"}.get(key, True)
    return True


def unit_factor(key: str, unit: str) -> Optional[float]:
    """單位欄 → 換成 Hz／秒的倍率（samples 回 None）。"""
    if key in ("units", "rate_units"):
        return dsv_convert.FREQ_UNIT_HZ[unit]
    if key in ("dur_units", "bp_units"):
        return dsv_clean.TIME_UNITS[unit]
    return dsv_convert.TIME_UNIT_S[unit]


# 單位欄 → 它管的數值欄
UNIT_FIELDS = {"units": ("fpass", "fpass1", "fpass2"), "rate_units": ("rate",), "dur_units": ("window",), "bp_units": ("breakpoints",),
               "wlen_units": ("wlen",), "sep_units": ("maxsep",)}


def fmt_num(v: float) -> str:
    return "%.12g" % float(v)


def convert_units(func: str, unit_key: str, old: str, new: str, form: Dict[str, str]) -> Dict[str, str]:
    """換單位：MATLAB 存的是 Hz／秒，單位只影響顯示 → 把欄位的值換算成新單位重新顯示（Auto、空白、看不懂的照舊）。
    包絡的長度單位在「樣本」與時間單位之間切換時清空（MATLAB：Changing units between samples and time clears the value）。"""
    out = dict(form)
    if old == new:
        return out
    if unit_key in ("wlen_units", "sep_units") and ("samples" in (old, new)):
        for k in UNIT_FIELDS[unit_key]:
            out[k] = ""
        return out
    fo, fn = unit_factor(unit_key, old), unit_factor(unit_key, new)
    for k in UNIT_FIELDS.get(unit_key, ()):
        text = str(form.get(k, ""))
        if k == "breakpoints":
            parts = [p.strip() for p in text.split(",")]
            if not text.strip() or any(math.isnan(js_float(p)) for p in parts):
                continue
            out[k] = ", ".join(fmt_num(js_float(p) * fo / fn) for p in parts)
            continue
        v = js_float(text)
        if text.strip().lower() == "auto" or not math.isfinite(v):
            continue
        out[k] = fmt_num(v * fo / fn)
    return out


# ---------------------------------------------------------------- 解析與驗證（照 Signal Analyzer 介面的欄位與套用前的檢查）
_JSNUM = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def js_float(text) -> float:
    """寬鬆解析（和 JavaScript 的 parseFloat 同一種規則）：取開頭能解析的數字（「40abc」→ 40、「abc」→ NaN、空白 → NaN）。全形數字先 NFKC 正規化。"""
    s = unicodedata.normalize("NFKC", str(text if text is not None else "")).strip()
    m = _JSNUM.match(s)
    if m:
        return float(m.group(0))
    if re.match(r"^[+-]?Infinity", s):
        return -math.inf if s.startswith("-") else math.inf
    return math.nan


def _is_auto(text) -> bool:
    return str(text or "").strip().lower() == "auto"


def _pos(text) -> Optional[float]:
    v = js_float(text)
    return v if (math.isfinite(v) and v > 0) else None


def _pos_int(text) -> Optional[int]:
    v = js_float(text)
    return int(v) if (math.isfinite(v) and v > 0 and v == math.floor(v)) else None


def validate(func: str, form: Dict[str, str]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """面板的字串 → (參數 dict, 欄位錯誤 {欄位: 訊息})。參數的頻率存 Hz、時間存秒（MATLAB 也這樣存；單位只為了重新顯示）。
    只檢查看得到的欄位（MATLAB 隱藏的欄位不驗證）。有錯誤時參數 dict 不完整，不能拿去算。"""
    form = dict(default_form(func), **{k: v for k, v in (form or {}).items() if v is not None})
    err: Dict[str, str] = {}
    p: Dict[str, Any] = {}
    if func in FILTERS:
        p["units"] = form["units"] if form["units"] in FREQ_UNITS else "Hz"
        f = dsv_convert.FREQ_UNIT_HZ[p["units"]]
        keys = ("fpass",) if func in ("lowpass", "highpass") else ("fpass1", "fpass2")
        for k in keys:
            v = _pos(form[k])
            if v is None:
                err[k] = tr("通帶頻率必須為正純量")
            else:
                p[k] = v * f
        if len(keys) == 2 and not err and not p["fpass1"] < p["fpass2"]:
            err["fpass2"] = tr("下通帶頻率必須小於上通帶頻率")
        skeys = ("steepness",) if len(keys) == 1 else (("steepness1", "steepness2") if form["steep_mode"] == "dual" else ("steepness1",))
        if len(keys) == 2:
            p["steep_mode"] = "dual" if form["steep_mode"] == "dual" else "single"
        for k in skeys:
            v = js_float(form[k])
            if not (math.isfinite(v) and 0.5 <= v < 1):
                err[k] = tr("陡度必須為 [0.5,1) 範圍內的數值純量")
            else:
                p[k] = v
        v = js_float(form["atten"])
        if not (math.isfinite(v) and v >= 10):
            err["atten"] = tr("阻帶衰減必須為大於或等於 10 dB 的正數值純量")
        else:
            p["atten"] = v
    elif func == "smooth":
        p["method"] = form["method"] if form["method"] in SMOOTH_METHODS else "movmean"
        p["wintype"] = "smoothingfactor" if form["wintype"] == "smoothingfactor" else "duration"
        p["dur_units"] = form["dur_units"] if form["dur_units"] in TIME_UNITS else "s"
        p["degree"] = None
        if p["method"] == "sgolay" and not _is_auto(form["degree"]):
            d = _pos_int(form["degree"])
            if d is None:
                err["degree"] = tr("次數必須設為正整數。")
            p["degree"] = d
        p["window"] = None
        p["factor"] = dsv_clean.DEFAULT_FACTOR
        if p["wintype"] == "duration":
            if not _is_auto(form["window"]):
                w = _pos(form["window"])
                if w is None:
                    err["window"] = tr("以時間為單位的視窗持續時間長度必須為正數值純量")
                else:
                    p["window"] = w * dsv_clean.TIME_UNITS[p["dur_units"]]
        else:
            v = js_float(form["factor"])
            if not (math.isfinite(v) and 0 <= v <= 1):
                err["factor"] = tr("平滑因子必須為介於 0 和 1 之間的數值純量")
            else:
                p["factor"] = v
    elif func == "detrend":
        p["method"] = form["method"] if form["method"] in DETREND_METHODS else "linear"
        p["bp_units"] = form["bp_units"] if form["bp_units"] in TIME_UNITS else "s"
        p["breakpoints"] = None
        if p["method"] == "piecewiselinear":
            text = str(form["breakpoints"] or "")
            parts = [s.strip() for s in text.split(",")]
            if text.strip() and all(parts):                     # 有空的一段（「40,,60」、結尾逗號）→ MATLAB 當沒有斷點（＝線性），不是錯誤
                vals = [js_float(s) for s in parts]
                if any(math.isnan(v) for v in vals):
                    err["breakpoints"] = tr("以時間為單位的分段斷點必須為數值")
                else:
                    f = dsv_clean.TIME_UNITS[p["bp_units"]]
                    p["breakpoints"] = [v * f for v in vals]
    elif func == "resample":
        p["rmethod"] = "samplefactor" if form["rmethod"] == "samplefactor" else "samplerate"
        p["rate_units"] = form["rate_units"] if form["rate_units"] in FREQ_UNITS else "Hz"
        p["rate"] = None
        p["factor"] = None
        if p["rmethod"] == "samplerate":
            if _is_auto(form["rate"]):
                p["rate"] = "auto"
            else:
                v = _pos(form["rate"])
                if v is None:
                    err["rate"] = tr("值必須為正純量")
                else:
                    p["rate"] = v * dsv_convert.FREQ_UNIT_HZ[p["rate_units"]]
        else:
            v = _pos(form["factor"])
            if v is None:
                err["factor"] = tr("值必須為正純量")
            p["factor"] = v
    elif func == "envelope":
        p["output"] = "lower" if form["output"] == "lower" else "upper"
        p["emethod"] = form["emethod"] if form["emethod"] in ENV_METHODS else "hilbert"
        p["wlen_units"] = form["wlen_units"] if form["wlen_units"] in ENV_UNITS else "samples"
        p["sep_units"] = form["sep_units"] if form["sep_units"] in ENV_UNITS else "samples"
        p["n"] = None
        p["seconds"] = None
        m = p["emethod"]
        if m == "fir":
            n = _pos_int(form["order"])
            if n is None:
                err["order"] = tr("濾波器階數必須為正整數")
            p["n"] = n
        elif m in ("rms", "peak"):
            k, uk = ("wlen", "wlen_units") if m == "rms" else ("maxsep", "sep_units")
            if p[uk] == "samples":
                n = _pos_int(form[k])
                if n is None:
                    err[k] = tr("以樣本為單位的視窗長度必須為正整數") if m == "rms" else tr("以樣本為單位的最大值間隔必須為正整數")
                p["n"] = n
            else:
                v = _pos(form[k])
                if v is None:
                    err[k] = tr("以時間為單位的視窗長度必須為正數值純量") if m == "rms" else tr("以時間為單位的最大值間隔必須為正數值純量")
                else:
                    p["seconds"] = v * dsv_convert.TIME_UNIT_S[p[uk]]
    else:
        raise KeyError(func)
    return p, err


def _num_text(v, f: float = 1.0, integer: bool = False) -> str:
    """存的參數 → 面板文字。只有數字才顯示：手改成字串、bool、NaN／Inf 的當空白（validate 接著顯示那個欄位的 MATLAB 訊息）；
    整數欄（次數、N）照原值顯示，2.5 不截成 2（validate 才會說「必須為正整數」）。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        return ""
    if integer:
        return str(int(v)) if float(v) == math.floor(v) else fmt_num(v)
    return fmt_num(float(v) / f)


def form_from_params(func: str, p: Dict[str, Any]) -> Dict[str, str]:
    """參數 dict → 面板字串（照參數裡記的單位顯示）；用在從衍生訊號帶回參數，也是 check_params 驗設定檔參數的路徑
    （數值欄不是數字 → 空白 → 欄位訊息；整數欄照原值 → 2.5 被驗出來）。"""
    form = default_form(func)
    if func in FILTERS:
        u = p.get("units", "Hz")
        form["units"] = u
        f = dsv_convert.FREQ_UNIT_HZ.get(u, 1.0)
        for k in ("fpass", "fpass1", "fpass2"):
            if p.get(k) is not None and k in form:
                form[k] = _num_text(p[k], f)
        if "steep_mode" in form:
            form["steep_mode"] = p.get("steep_mode", "single")
        for k in ("steepness", "steepness1", "steepness2", "atten"):
            if p.get(k) is not None and k in form:
                form[k] = _num_text(p[k])
    elif func == "smooth":
        form.update(method=p.get("method", "movmean"), wintype=p.get("wintype", "duration"), dur_units=p.get("dur_units", "s"))
        form["degree"] = "Auto" if p.get("degree") is None else _num_text(p["degree"], integer=True)
        w = p.get("window")
        form["window"] = "Auto" if w is None else _num_text(w, dsv_clean.TIME_UNITS.get(form["dur_units"], 1.0))
        form["factor"] = _num_text(p.get("factor", dsv_clean.DEFAULT_FACTOR))
    elif func == "detrend":
        form.update(method=p.get("method", "linear"), bp_units=p.get("bp_units", "s"))
        bp = p.get("breakpoints")
        f = dsv_clean.TIME_UNITS.get(form["bp_units"], 1.0)
        form["breakpoints"] = "" if not bp else ", ".join(_num_text(b, f) or "NaN" for b in bp)   # NaN 斷點 → validate 說「必須為數值」
    elif func == "resample":
        form.update(rmethod=p.get("rmethod", "samplerate"), rate_units=p.get("rate_units", "Hz"))
        r = p.get("rate")
        form["rate"] = "Auto" if _is_auto(r) else ("" if r is None else _num_text(r, dsv_convert.FREQ_UNIT_HZ.get(form["rate_units"], 1.0)))
        form["factor"] = "" if p.get("factor") is None else _num_text(p["factor"])
    elif func == "envelope":
        form.update(output=p.get("output", "upper"), emethod=p.get("emethod", "hilbert"), wlen_units=p.get("wlen_units", "samples"),
                    sep_units=p.get("sep_units", "samples"))
        m = form["emethod"]
        if m == "fir" and p.get("n") is not None:
            form["order"] = _num_text(p["n"], integer=True)
        elif m in ("rms", "peak"):
            k, uk = ("wlen", "wlen_units") if m == "rms" else ("maxsep", "sep_units")
            if form[uk] == "samples":
                if p.get("n") is not None:
                    form[k] = _num_text(p["n"], integer=True)
            elif p.get("seconds") is not None:
                form[k] = _num_text(p["seconds"], dsv_convert.TIME_UNIT_S.get(form[uk], 1.0))
    return form


# ---------------------------------------------------------------- 衍生訊號
def kind_of(func: str, params: Dict[str, Any]) -> str:
    if func == "envelope":
        return "pp_envelope_lower" if params.get("output") == "lower" else "pp_envelope_upper"
    return "pp_" + func


def func_of(kind: str) -> str:
    return "envelope" if kind.startswith("pp_envelope") else kind[3:]


def derived_name(kind: str, src_name: str) -> str:
    """衍生訊號的名稱：照 MATLAB 函式名寫成 lowpass(名稱)、smoothdata(名稱)、upperEnvelope(名稱)…（資料名稱，不翻譯）。"""
    return f"{_FN_NAME.get(kind, kind)}({src_name})"


def detected_label(kind: str) -> str:
    """清單 Fmt 欄顯示的種類。"""
    return _FN_NAME.get(kind, kind)


def params_summary(kind: str, p: Dict[str, Any]) -> str:
    """一條衍生訊號的參數摘要（選取它時顯示在狀態列）：照面板的欄位順序「標籤 值 單位」，只列那個方法看得到的欄位，
    數值照存的顯示單位（和重新打開面板看到的一樣）。"""
    func = func_of(kind)
    form = form_from_params(func, p or {})
    unit_of = {"fpass": "units", "fpass1": "units", "fpass2": "units", "rate": "rate_units", "window": "dur_units",
               "breakpoints": "bp_units", "wlen": "wlen_units", "maxsep": "sep_units"}
    parts: List[str] = []
    for f in fields(func):
        k = f["key"]
        if k in UNIT_FIELDS or k == "steep_mode" or not visible(func, k, form):
            continue
        val = str(form.get(k, ""))
        if k in unit_of:
            if val and not _is_auto(val):
                val = f"{val} {unit_label(form[unit_of[k]])}"
            elif not val:
                val = "—"
        elif k in ("method", "wintype", "rmethod", "output", "emethod"):
            val = option_label(k, val)
        elif k == "atten":
            val = f"{val} dB"
        label = option_label("steep_mode", form.get("steep_mode", "single")) if k == "steepness1" else field_label(func, k, form)
        parts.append(f"{label} {val}")
    return tr("、").join(parts)


def normalize_params(kind: str, p) -> Dict[str, Any]:
    """設定檔讀回來的參數：只留看得懂的鍵、型別轉好（手改壞的就丟掉，算的時候會用預設或報錯）。"""
    if not isinstance(p, dict):
        return {}
    func = func_of(kind) if kind in KINDS else ""
    allowed = {"lowpass": ("units", "fpass", "steepness", "atten"), "highpass": ("units", "fpass", "steepness", "atten"),
               "bandpass": ("units", "fpass1", "fpass2", "steep_mode", "steepness1", "steepness2", "atten"),
               "bandstop": ("units", "fpass1", "fpass2", "steep_mode", "steepness1", "steepness2", "atten"),
               "smooth": ("method", "degree", "wintype", "dur_units", "window", "factor"),
               "detrend": ("method", "bp_units", "breakpoints"), "resample": ("rmethod", "rate_units", "rate", "factor"),
               "envelope": ("output", "emethod", "wlen_units", "sep_units", "n", "seconds")}.get(func, ())
    out: Dict[str, Any] = {}
    for k in allowed:
        if k not in p:
            continue
        v = p[k]
        if k == "breakpoints":
            if isinstance(v, (list, tuple)):
                try:
                    out[k] = [float(b) for b in v]
                except (TypeError, ValueError):
                    pass
            elif v is None:
                out[k] = None
        elif isinstance(v, bool):
            continue
        elif isinstance(v, (int, float)) or v is None:
            out[k] = v
        elif isinstance(v, str):
            out[k] = v
    if func == "envelope":
        out["output"] = "lower" if kind == "pp_envelope_lower" else "upper"
    return out


def copy_params(p: Dict[str, Any]) -> Dict[str, Any]:
    """參數 dict 的副本（清單值也複製）：快照、設定檔、貼上不會共用同一個 list。"""
    return {k: (list(v) if isinstance(v, (list, tuple)) else v) for k, v in (p or {}).items()}


def rate_ratio(kind: str, params: Dict[str, Any], fs: float) -> float:
    """新取樣率／原取樣率（重取樣：Sample Rate＝目標 Hz／fs、Sample Factor＝因子；其他＝1）。參數不合法回 1（資料算不出來會另外報錯）。
    DSV 的時間軸：新 SPS＝SPS × 比值（symbol rate 不變）。"""
    if kind != "pp_resample":
        return 1.0
    try:
        if params.get("rmethod") == "samplefactor":
            r = float(params.get("factor"))
        else:
            rate = params.get("rate")
            if rate in (None, "auto"):
                return 1.0
            r = float(rate) / float(fs)
    except (TypeError, ValueError, ZeroDivisionError):
        return 1.0
    return r if (math.isfinite(r) and r > 0) else 1.0


# ---------------------------------------------------------------- 計算（交給已驗證的模組）
def _zh() -> bool:
    return get_language() == "zh"


def _filter_msg(e: "dsv_filter.FilterError") -> str:
    return e.message_zh if _zh() else e.message


def _clean_msg(e: "dsv_clean.CleanError") -> str:
    if getattr(e, "keyword", None) == "sgDegreeError":
        return tr("次數太大。次數必須小於任一訊號視窗中的最大點數。")
    return e.zh if _zh() else str(e)


def _convert_msg(e: "dsv_convert.ConvertError") -> str:
    app = {"SignalLengthViolation": tr("目標取樣率與目前取樣率的比率超過限制。請指定較低的目標取樣率。"),
           "InvalidResampledSignal": tr("目標取樣率導致重取樣後的訊號長度為 1。請指定較高的目標取樣率。"),
           "UnchangedUniformSignal": tr("自動計算取樣率時，不會前處理均勻取樣的訊號。"),
           "ValueMustBePositive": tr("值必須為正純量")}
    if e.ident in app:
        return app[e.ident]
    return e.zh if _zh() else e.en


def not_finite_message() -> str:
    """MATLAB 的「無法前處理含有缺失值…」訊息（DSV 沒有「填補缺失值」，訊息照 MATLAB 原文；「預處理」改成台灣用語「前處理」、功能名稱用台灣用語「填補缺失值」，
    2026-10-27 使用者決定）。"""
    return tr("無法前處理具有缺失值或非有限值的訊號。請使用「填補缺失值」來填補缺失值。")


def empty_source_message(src_name: str, src_error: Optional[str] = None, src_missing: bool = False) -> str:
    """來源沒有資料時的訊息（DSV 自己的；MATLAB 覆寫訊號、沒有連鎖，研究沒有對應文字）：來源自己是算不出來的前處理結果就把它的原因
    接在後面；來源的來源不見了也說明；其他（空檔）＝空的訊號。"""
    if src_error:
        return tr("來源 {name} 沒有資料：{msg}").format(name=src_name, msg=src_error)
    if src_missing:
        return tr("來源 {name} 沒有資料（它的來源訊號不見了）").format(name=src_name)
    return tr("來源 {name} 沒有資料（空的訊號），無法前處理").format(name=src_name)


def filter_warning_text(func: str, keyword: str) -> Optional[str]:
    """MATLAB 套用後的警告對話框只處理 ForcedAllpassDesign／ForcedAllstopDesign（LpHp／BpBs 各一種字句）。"""
    if keyword not in ("ForcedAllpassDesign", "ForcedAllstopDesign"):
        return None
    allpass = keyword == "ForcedAllpassDesign"
    if func in ("lowpass", "highpass"):
        return tr("由於指定的通帶頻率超過 Nyquist 極限，因此使用了全通濾波器。") if allpass else tr("由於指定的通帶頻率超過 Nyquist 極限，因此使用了全阻濾波器。")
    return tr("由於指定的上下通帶頻率超過 Nyquist 極限，因此使用了全通濾波器。") if allpass else tr("由於指定的上下通帶頻率超過 Nyquist 極限，因此使用了全阻濾波器。")


def check_params(kind: str, params: Dict[str, Any]) -> Dict[str, str]:
    """衍生訊號存的參數（設定檔讀回來的，可能被手改過）用面板同一套規則再驗一次：參數 → 面板文字 → validate；
    回傳 {欄位: MATLAB 的訊息}（空＝合法）。缺鍵＝那個欄位空白（例如沒有 fpass →「通帶頻率必須為正純量」），型別壞到換不成文字＝整體不合法。"""
    func = func_of(kind) if kind in KINDS else ""
    if not func:
        return {"*": tr("前處理參數不合法（設定檔可能被改過）；請移除這條結果後重新套用")}
    try:
        form = form_from_params(func, params or {})
    except (TypeError, ValueError, KeyError, OverflowError):
        return {"*": tr("前處理參數不合法（設定檔可能被改過）；請移除這條結果後重新套用")}
    if func == "envelope":
        form["output"] = "lower" if kind == "pp_envelope_lower" else "upper"
    _p, err = validate(func, form)
    return err


def compute(kind: str, params: Dict[str, Any], x, fs: float, t0: float = 0.0) -> Dict[str, Any]:
    """算一條衍生訊號。x＝來源的資料（shift／scale／突波抑制之後）、fs＝來源的取樣率（SPS × symbol rate，Hz）、
    t0＝來源第一個樣本的時間（秒）。回傳 dict：y、ratio（新取樣率／原取樣率）、warnings（目前語言的文字）、info（模組的細節）。
    沒處理 → PreprocessError（訊息是目前語言；warning＝True 是 MATLAB 用警告的情況）。
    參數先照面板的規則驗過（check_params）：手改壞的設定檔得到 MATLAB 的欄位訊息，不是 Python 的例外文字。"""
    func = func_of(kind)
    bad = check_params(kind, params)
    if bad:
        raise PreprocessError(tr("參數不合法：{msgs}").format(msgs=tr("；").join(bad.values())), ident="dsv:preprocess:badParams")
    x = np.asarray(x, dtype=float)
    if x.size == 0:                                            # 來源沒有資料（來源自己算不出來、空檔）：不是正常的空結果（模組對空輸入會回空的）
        raise PreprocessError(tr("來源訊號沒有資料，無法前處理"), ident="dsv:preprocess:emptySource")
    if not np.all(np.isfinite(x)):
        raise PreprocessError(not_finite_message(), ident="preprocessNotFiniteWarning")
    warns: List[str] = []
    ratio = 1.0
    try:
        if func in FILTERS:
            if func in ("lowpass", "highpass"):
                wp: Any = float(params["fpass"])
                st: Any = float(params["steepness"])
            else:
                wp = [float(params["fpass1"]), float(params["fpass2"])]
                st = ([float(params["steepness1"]), float(params["steepness2"])] if params.get("steep_mode") == "dual"
                      else float(params["steepness1"]))        # Signal Analyzer 的單一模式傳標量（不是函式預設的 [0.85 0.85]）
            y, info = dsv_filter.filter_signal(func, x, wp, float(fs), st, float(params["atten"]))
            for kw in info.get("warnings") or []:
                w = filter_warning_text(func, kw)
                if w and w not in warns:
                    warns.append(w)
        elif func == "smooth":
            t = dsv_clean.time_vector(x.size, float(fs), float(t0))
            win = params.get("window") if params.get("wintype", "duration") == "duration" else None
            fac = float(params.get("factor", dsv_clean.DEFAULT_FACTOR)) if params.get("wintype") == "smoothingfactor" else dsv_clean.DEFAULT_FACTOR
            deg = params.get("degree") if params.get("method") == "sgolay" else None
            deg = None if deg is None else int(deg)              # check_params 已確認是整數值（3.0 也算）；模組要 int
            r = dsv_clean.smooth(x, params.get("method", "movmean"), win, t, fac, deg)
            y, info = np.real(r["y"]), r
            if r.get("warning") == dsv_clean.WARN_DEGREE_KEYWORD:
                warns.append(tr("次數已調整為較小的值。指定的值大於自動計算的視窗長度。"))
        elif func == "detrend":
            t = dsv_clean.time_vector(x.size, float(fs), float(t0))
            m = params.get("method", "linear")
            bp = params.get("breakpoints") if m == "piecewiselinear" else None
            y, info = np.real(dsv_clean.detrend(x, m, bp, t)), {}
        elif func == "resample":
            t = dsv_clean.time_vector(x.size, float(fs), float(t0))
            if params.get("rmethod") == "samplefactor":
                r = dsv_convert.app_resample(x, t, fs=float(fs), rate=None, factor=params.get("factor"), uniform=True)
            else:
                rate = params.get("rate")
                r = dsv_convert.app_resample(x, t, fs=float(fs), rate="auto" if (rate is None or _is_auto(rate)) else rate, factor=None, uniform=True)
            y, info = np.real(r["y"]), r
            ratio = float(r["target_fs"]) / float(fs)
        elif func == "envelope":
            m = params.get("emethod", "hilbert")
            out = "lower" if kind == "pp_envelope_lower" else "upper"
            n_ = params.get("n")
            r = dsv_convert.app_envelope(x, m, out, n=None if n_ is None else int(n_), seconds=params.get("seconds"),
                                         fs=float(fs) if params.get("seconds") is not None else None)
            y, info = np.real(r["y"]), r
        else:
            raise KeyError(kind)
    except dsv_filter.FilterError as e:
        raise PreprocessError(_filter_msg(e), ident=e.identifier)
    except dsv_clean.CleanError as e:
        raise PreprocessError(_clean_msg(e), ident=e.identifier)
    except dsv_convert.ConvertError as e:
        raise PreprocessError(_convert_msg(e), warning=e.ident == "UnchangedUniformSignal", ident=e.ident)
    except (KeyError, TypeError, ValueError) as e:            # check_params 沒攔到的參數問題（不該發生）：一律當錯誤，不讓整個重畫失敗
        raise PreprocessError(tr("前處理參數不合法（{detail}）；請移除這條結果後重新套用").format(detail=f"{type(e).__name__}: {e}"),
                              ident="dsv:preprocess:badParams")
    return {"y": np.asarray(y, dtype=float), "ratio": ratio, "warnings": warns, "info": info}


def dialog_text(errors: Sequence[Tuple[str, str]], warnings: Sequence[Tuple[str, str]], n_selected: int) -> Tuple[str, str]:
    """套用後的對話框（MATLAB 對話框的前綴，每行「- 」開頭）→ (錯誤文字, 警告文字)；沒有就是空字串。
    errors／warnings：[(訊號名稱, 訊息)]。全部選取的訊號都出錯＝「所選訊號」，否則「部分所選訊號」。"""
    def block(items, all_text, some_text):
        if not items:
            return ""
        names = {n for n, _m in items}
        head = all_text if len(names) >= n_selected else some_text
        return head + "\n\n" + "\n".join(f"- {n}: {m}" for n, m in items)
    e = block(errors, tr("由於出現了以下錯誤，所選訊號未被處理："), tr("由於出現了以下錯誤，部分所選訊號未被處理："))
    w = block(warnings, tr("所選訊號已處理，但出現以下警告："), tr("部分所選訊號已處理，但出現以下警告："))
    return e, w
