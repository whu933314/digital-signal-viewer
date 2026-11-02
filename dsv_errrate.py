# -*- coding: utf-8 -*-
"""誤碼數／誤碼率（MATLAB Communications Toolbox 的 biterr、symerr、comm.ErrorRate）——純 numpy，和 GUI 分開。

定義照 MATLAB R2025a 的文件（biterr、symerr、comm.ErrorRate System object；Simulink 的 Error Rate Calculation 方塊同一套語意），
程式是自己寫的；tests/matlab_ref/error_rate/ 的兩份 JSON（error_rate_ref.json 186 筆、er_ref.json 180 筆）是 MATLAB R2025a 算出的
輸入、輸出、錯誤識別碼與訊息，selftest() 逐筆比對（產生它們的 .m 腳本在 b34 研究資料夾：ref_error_rate.m、er_ref.m）。

biterr(x, y[, k][, flag]) → (number, ratio, individual)
- x、y：非負整數值（double／single／整數型別／logical），2-D、非空。每個元素展成 k 個無號位元（MSB 在前），逐位元比較。
  individual(i,j)＝該元素有幾個位元不同（等於 popcount(x XOR y) 限制在低 k 位）。
- k：預設 floor(log2(double(M)))+1，M 是兩個輸入的最大值（M＝0 → 1）；給定的 k 不能小於這個值（ShortWordLength）。注意是把 M 轉成
  double 再取 log2：M＝2^j−1 在 j ≥ 49 時 log2 的正確捨入結果剛好是整數 j，所以預設 k＝j+1（比位元長度多 1）；int64／uint64 的最大值轉
  double 會進位成 2^63／2^64，k＝64／65（biterr_word_length()）。有 logical 輸入時另一個只能是 0/1、k 只能是 1。
  字長上限（MATLAB 的 int2bit；biterr 把每個輸入各自用自己的 class 展成位元）：double 輸入 k ≤ 53、single 輸入 k ≤ 24，超過 →
  MATLAB:notLessEqual「Expected N to be a scalar with value <= 53.」（在 k／flag 的檢查之後才發生）；整數型別沒有上限，超過型別寬度的
  高位元補 0。所以 double 輸入 ≥ 2^53−22（log2 進位成 53）或 ≥ 2^53 一律是錯誤，不會算出錯的 popcount。
  k 與 flag 可以放第 3、4 個位置、順序任意；[] 表示沒給 k、'' 表示沒給 flag；同一種給兩次 → Syntax error。
- 形狀規則：一個是向量、另一個是矩陣時，向量和矩陣的每一列（列向量 1×n：預設 'row-wise'）或每一欄（欄向量 m×1：預設 'column-wise'）
  比；向量放第一或第二個都行。純量對欄向量＝row-wise 逐元素、純量對列向量＝column-wise、純量對矩陣 → 尺寸錯誤。
  其他情況預設 'overall'、尺寸必須相同。flag 只能把 row-wise／column-wise 的結果改成 'overall'，不能在 row／column 之間切換
  （ColFlagRowInput／RowFlagColInput）。flag 比對不分大小寫、任何唯一前綴都行（'r'、'OV'）。
- 回報：'overall' number＝Σ individual、ratio＝number/(m·n·k)；'row-wise' 每列的和、ratio＝number/(n·k)；'column-wise' 每欄的和、
  ratio＝number/(m·k)。m、n 是較大那個輸入（矩陣）的大小。

symerr(x, y[, flg]) → (number, ratio, individual)
- 數值型別（logical 不行）、2-D、非空；不要求整數，複數也可以。individual＝(x ≠ y)（logical）；NaN ≠ NaN 算錯、Inf ＝ Inf。
  有 Inf／NaN 時發 comm:symerr:InfOrNaN 警告。形狀與 flag 規則和 biterr 相同（k＝1）；flg 給了就一定要是合法字串（'' 也是錯）。

comm.ErrorRate（class ErrorRate；串流物件，每次呼叫累計）
- 輸入 tx、rx：欄向量或純量（其他形狀 → multChanNotSupport），長度相同除非其中一個是純量，實／複數要一致；型別限 double、single、
  int8/16/32、uint8/16/32、logical。double 對 single 時兩邊都轉成 single 再比（MATLAB comm.ErrorRate 的規則，第一次呼叫時決定）。
- ReceiveDelay（RD）：rx[n] 和 tx[n−RD] 比（n 跨訊框連續計數；前面補零的延遲緩衝。MATLAB 配 RD+1 長的環形緩衝，這裡只記「還剩幾個補零」
  加上實際收過的 tx 樣本，所以 RD 很大（1e12）也不配記憶體、結果相同）。ComputationDelay（CD）：串流最前面 RD+CD 個樣本不比（只倒數不比較）。Samples＝'Entire frame'（全部）／'Custom'（CustomSamples 的 1-based 訊框內位置，0 略過、重複只算一次）／
  'Input port'（每次呼叫多給一個 SEL 欄向量）。ResetInputPort＝True 時最後再多給 RST，RST 非零或 NaN 就把錯誤數與比較數歸零
  （不清延遲緩衝與倒數）。reset() 全部清掉（計數、緩衝、倒數）；release() 再加上解除輸入型別鎖定。
- 每次回傳 [rate, errors, compared]：rate＝errors/compared（compared＝0 → 0）。MATLAB 是 3×1 欄向量，這裡是長度 3 的一維陣列。
- R2025a 實測到、和文件不同的兩點都照實測：(a) Samples='Custom' 但 CustomSamples 是空的 → MATLAB:expectedVector 錯誤（文件說會比全部）；
  (b) tx、rx 都是純量（一個樣本一次呼叫）且 RD＝0 時，ComputationDelay 完全不生效、每個樣本都比（倒數器不會動）。
- 輸入引數個數要剛好（2 ＋ Input port ＋ ResetInputPort），少／多 → MATLAB:system:minNumInputs／maxNumInputs；
  呼叫之間改了某個輸入的型別（例如 RST 從 double 變 logical）→ MATLAB:system:inputSpecsChangedErrorD，要先 release()。

錯誤：全部丟 ErrRateError（ValueError 的子類）；.identifier 是 MATLAB 的識別碼、str(e)／.message 是 MATLAB 的英文訊息（逐字）、.zh 是繁體中文。
警告：warnings.warn(ErrRateWarning)，.identifier 同樣是 MATLAB 的識別碼。

DSV 自己加的（不是 MATLAB）：align_window()、error_rate()——把兩條長度、起點不同的符號序列對齊成比較視窗（見函式說明）；
biterr_word_length()——biterr 預設 k 的規則，給 error_rate() 與 GUI 顯示用；check_custom_samples()、custom_mask()——comm.ErrorRate 檢查
CustomSamples、選訊框位置的那一段（ErrorRate 自己也呼叫它們）單獨拿出來，給 GUI（錯誤率比對視窗）用。

未定／自行決定（報告列為開放問題、或 MATLAB 沒驗證到的）：
- Python 一維陣列當成 MATLAB 欄向量（n×1）；Python 的 int／float／bool／list 當成 double／logical（MATLAB 字面值的慣例），numpy 陣列照 dtype
  對應 MATLAB class（float32＝single、bool＝logical、int64＝int64…）。注意 np.array([1, 0]) 預設是 int64：biterr／symerr 接受，
  comm.ErrorRate 和 MATLAB 一樣拒絕（MATLAB:invalidType）——DSV 端請給 float 陣列，或走 error_rate()／align_window()。
- Python 的 '' 當成 MATLAB 的 char ''（biterr：沒給 flag）；MATLAB 的 string "" 在 Python 分不出來，不另外處理。
- 回傳形狀：'overall' 的 number／ratio 是 float，row-wise／column-wise 是一維陣列；individual 是 2-D，但較大那個輸入原本是一維時壓成一維
  （方便對回訊號位置）。
- Samples 只接受三個正式值（'cust' 這種縮寫 MATLAB 也拒絕；大小寫是否可混用沒驗證，這裡不接受）。
- ResetInputPort 給長度≠1 的字串 → IncompatibleSize（MATLAB 'yes' 驗證過）；長度 1 的字串 MATLAB 行為沒驗證，這裡丟 invalidType。
- CustomSamples 有給但 Samples 不是 'Custom' → 建構時發 MATLAB:system:nonRelevantProperty 警告（照最後狀態判斷，不看屬性順序）。
- 輸入型別鎖定只看 class（MATLAB 也鎖複數性等，沒驗證）。不同整數型別之間（如 int8 對 uint8）直接比數值。
- symerr 的 double 對 single：照 MATLAB 的型別合併規則先轉成 single 再比（0.1 ＝ single(0.1)）；參考資料只有 comm.ErrorRate 有這種案例。
- DSV 的 error_rate() 把 bool 輸入當成 0/1 的 double（MATLAB 的 logical 規則：symerr 拒絕、biterr 要求另一邊是 0/1、k＝1，在這裡不套用）。
- 第 4 個位置的 k 是 Inf → MATLAB:biterr:expectedFinite（訊息 "to be finite." 是 validateattributes 的標準字樣，沒實測）。
- int2bit 字長上限的錯誤（MATLAB:notLessEqual、"Expected N to be a scalar with value <= 53."／"<= 24."）是照 MATLAB int2bit 的參數檢查規則
  （純量、引數名 N）與 validateattributes 的訊息句型推定的，MATLAB 沒實測；參考資料最大只到
  k＝16，所以 selftest 用自己算的 popcount 驗這條規則，不是 MATLAB 數字。預設 k 用 libm 的 log2（selftest 驗證過 2^j−1、j＝1..64 和
  正確捨入一致）；int64／uint64 最大值轉 double 的捨入假設和 MATLAB 一樣是 round-to-nearest。
- align_window()／error_rate() 的 receive_delay、computation_delay 和 comm.ErrorRate 一樣只接受非負整數（負的 → MATLAB:expectedNonnegative、
  非整數 → expectedInteger；之前負的 computation_delay 會讓 numpy 負索引繞回去算出錯的結果）。rx 比 tx 早（負延遲）請用 tx_offset／rx_offset
  表示（tx_offset＝d 等於 rx 早 d 個符號），這樣參數定義域和 MATLAB 一致、GUI 可以用同一條驗證訊息。tx_offset／rx_offset 可以是負的，
  但要是整數值。
- embedded.fi（定點）輸入沒有 Python 對應，不支援。
- 中文用語（MATLAB 沒有繁中介面；簡中文件只有 biterr 的「误码数／误码率」）：誤碼數 number、誤碼率 ratio、符號錯誤數／符號錯誤率、
  錯誤率 rate、錯誤數 errors、比較數 compared、接收延遲 ReceiveDelay、計算延遲 ComputationDelay、整個訊框／自訂／輸入埠。
"""
from __future__ import annotations

import math
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

FLAGS = ("overall", "row-wise", "column-wise")                 # biterr／symerr 的 flag
SAMPLES_SET = ("Entire frame", "Custom", "Input port")          # comm.ErrorRate 的 Samples
ERRORRATE_TYPES = ("double", "single", "int8", "int16", "int32", "uint8", "uint16", "uint32", "logical", "embedded.fi")
BITERR_TYPES = ("double", "single", "uint8", "uint16", "uint32", "uint64", "int8", "int16", "int32", "int64", "logical")
SYMERR_TYPES = BITERR_TYPES[:-1]
TEXT_ZH = {"number": "誤碼數", "ratio": "誤碼率", "sym_number": "符號錯誤數", "sym_ratio": "符號錯誤率", "rate": "錯誤率", "errors": "錯誤數",
           "compared": "比較數", "ReceiveDelay": "接收延遲", "ComputationDelay": "計算延遲", "Samples": "比較樣本",
           "Entire frame": "整個訊框", "Custom": "自訂", "Input port": "輸入埠", "CustomSamples": "自訂樣本位置"}


class ErrRateError(ValueError):
    """MATLAB 的錯誤：identifier（如 comm:biterr:ShortWordLength）、message（英文原文）、zh（繁體中文）。"""

    def __init__(self, identifier: str, message: str, zh: str):
        super().__init__(message)
        self.identifier = identifier
        self.message = message
        self.zh = zh

    def text(self, lang: str = "zh") -> str:
        return self.zh if lang.startswith("zh") else self.message


class ErrRateWarning(UserWarning):
    """MATLAB 的警告（comm:symerr:InfOrNaN、MATLAB:system:nonRelevantProperty）。"""

    def __init__(self, identifier: str, message: str, zh: str):
        super().__init__(message)
        self.identifier = identifier
        self.message = message
        self.zh = zh


_FIXED = {
    "MATLAB:narginchk:notEnoughInputs": ("Not enough input arguments.", "輸入引數不足。"),
    "MATLAB:narginchk:tooManyInputs": ("Too many input arguments.", "輸入引數太多。"),
    "comm:biterr:MismatchedInputDims1": ("Input row vector must contain as many elements as there are columns in the input matrix.",
                                         "輸入的列向量元素個數必須等於輸入矩陣的欄數。"),
    "comm:biterr:MismatchedInputDims2": ("Input column vector must contain as many elements as there are rows in the input matrix.",
                                         "輸入的欄向量元素個數必須等於輸入矩陣的列數。"),
    "comm:biterr:MismatchedInputDims3": ("Input matrices must be the same size.", "兩個輸入矩陣的大小必須相同。"),
    "comm:biterr:ColFlagRowInput": ("A column-wise comparison is not possible with a row vector input.", "輸入是列向量時不能做逐欄（column-wise）比較。"),
    "comm:biterr:RowFlagColInput": ("A row-wise comparison is not possible with a column vector input.", "輸入是欄向量時不能做逐列（row-wise）比較。"),
    "comm:biterr:NonBinaryWithLogical": ("When one of the inputs is logical, the other input must be binary valued.",
                                         "其中一個輸入是 logical 時，另一個輸入的值只能是 0 或 1。"),
    "comm:biterr:InvalidNumBitsWithLogical": ("When one of the inputs is logical, number of bits, K, must be 1.",
                                              "其中一個輸入是 logical 時，位元數 K 必須是 1。"),
    "comm:biterr:ShortWordLength": ("The specified word length is too short for the matrix elements.", "指定的字長 K 不夠表示矩陣裡的元素。"),
    "comm:biterr:InvalidFlag1": ("Only character vector, string scalar, and numeric arguments are accepted.", "只接受字元向量、字串純量或數值引數。"),
    "comm:biterr:InvalidArgsPassed": ("Syntax error.", "語法錯誤（K 或 FLAG 給了兩次）。"),
    "comm:symerr:InvalidInputSize1": ("Input row vector must contain as many elements as there are columns in the input matrix.",
                                      "輸入的列向量元素個數必須等於輸入矩陣的欄數。"),
    "comm:symerr:InvalidInputSize2": ("Input column vector must contain as many elements as there are rows in the input matrix.",
                                      "輸入的欄向量元素個數必須等於輸入矩陣的列數。"),
    "comm:symerr:DifferentSizeInputs": ("Input matrices must be the same size.", "兩個輸入矩陣的大小必須相同。"),
    "comm:symerr:RowInputColumnwiseComparison": ("A column-wise comparison is not possible with a row vector input.",
                                                 "輸入是列向量時不能做逐欄（column-wise）比較。"),
    "comm:symerr:ColumnInputRowwiseComparison": ("A row-wise comparison is not possible with a column vector input.",
                                                 "輸入是欄向量時不能做逐列（row-wise）比較。"),
    "comm:system:txRxLengthsDiffer": ("The Tx and Rx inputs must have the same length.", "Tx 與 Rx 輸入的長度必須相同。"),
    "dspshared:system:multChanNotSupport": ("Multichannel operation is not supported.", "不支援多通道：輸入必須是欄向量或純量。"),
    "comm:system:sampsElemExceedInWidth": ("The elements of the Samples property must be smaller than or equal to the input length.",
                                           "CustomSamples 的元素必須小於或等於輸入長度。"),
    "comm:system:sampsWidthExceedInWidth": ("Samples to consider input, SEL, values must be non-negative integers less than or equal to the "
                                            "number of rows of the input.", "SEL 輸入的值必須是非負整數且不超過輸入的列數。"),
    "MATLAB:validation:IncompatibleSize": ("Error setting property 'ResetInputPort' of class 'comm.ErrorRate'. Value must be a scalar.",
                                           "設定 comm.ErrorRate 的 ResetInputPort 屬性失敗：值必須是純量。"),
    "MATLAB:system:invalidComplexityNeedReal": ("Complexity mismatch with input 2; expected real, got complex.", "第 2 個輸入應該是實數，卻是複數。"),
    "MATLAB:system:invalidComplexityNeedComplex": ("Complexity mismatch with input 2; expected complex, got real.", "第 2 個輸入應該是複數，卻是實數。"),
}
_ATTR = {"nonempty": ("expectedNonempty", "nonempty", "非空"), "2d": ("expected2D", "two-dimensional", "是二維"),
         "real": ("expectedReal", "real", "是實數"), "nonnegative": ("expectedNonnegative", "nonnegative", "非負"),
         "integer": ("expectedInteger", "integer-valued", "是整數值"), "scalar": ("expectedScalar", "a scalar", "是純量"),
         "positive": ("expectedPositive", "positive", "是正數"), "nonnan": ("expectedNonNaN", "non-NaN", "不能是 NaN"),
         "finite": ("expectedFinite", "finite", "是有限值"), "vector": ("expectedVector", "a vector", "是向量"),
         "column": ("expectedColumn", "a column vector", "是欄向量")}
_RELEASE_LINK = ('<a href="matlab:helpview(fullfile(docroot, \'matlab\',\'ref\',\'matlab.system.releasesystemobject.html\'))">release()</a>')
_DTYPE_CLASS = {"float64": "double", "float32": "single", "float16": "half", "complex128": "double", "complex64": "single", "bool": "logical",
                "int8": "int8", "int16": "int16", "int32": "int32", "int64": "int64", "uint8": "uint8", "uint16": "uint16", "uint32": "uint32",
                "uint64": "uint64"}
_POP8 = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)      # 每個 byte 的 1 位元數


def _fail(identifier: str, **fmt) -> None:
    en, zh = _FIXED[identifier]
    raise ErrRateError(identifier, en.format(**fmt), zh.format(**fmt))


def _attr_fail(fn: Optional[str], pos: Optional[int], name: str, attr: str, cls: str = "", types: str = "") -> None:
    """validateattributes 風格的錯誤。fn 有給 → MATLAB:{fn}:expectedX（biterr／symerr）；沒給 → MATLAB:expectedX（System object）。"""
    who = f"input number {pos}, {name}," if pos else name
    who_zh = f"第 {pos} 個輸入 {name}" if pos else name
    if attr == "invalidType":
        ident = f"MATLAB:{fn}:invalidType" if fn else "MATLAB:invalidType"
        msg = f"Expected {who} to be one of these types:\n\n{types}"
        zh = f"{who_zh} 必須是下列型別之一：{types}"
        if cls != "char":                                            # MATLAB 對 char 輸入不加這一行
            msg += f"\n\nInstead its type was {cls}."
            zh += f"；實際型別是 {cls}"
        raise ErrRateError(ident, msg, zh + "。")
    suffix, text, zh_text = _ATTR[attr]
    ident = f"MATLAB:{fn}:{suffix}" if fn else f"MATLAB:{suffix}"
    raise ErrRateError(ident, f"Expected {who} to be {text}.", f"{who_zh} 必須{zh_text}。")


def _warn(identifier: str, message: str, zh: str) -> None:
    warnings.warn(ErrRateWarning(identifier, message, zh), stacklevel=3)


class _MV:
    """Python 值 → MATLAB 觀點：kind＝'num'（a 是 ≥2-D ndarray、cls 是 MATLAB class）／'char'（text）／'cell'（其他容器）。"""
    __slots__ = ("a", "cls", "text", "kind", "vec1d")

    def __init__(self, kind: str, a=None, cls: str = "", text: str = "", vec1d: bool = False):
        self.kind, self.a, self.cls, self.text, self.vec1d = kind, a, cls, text, vec1d


def _mv(v) -> _MV:
    if isinstance(v, _MV):
        return v
    if isinstance(v, str):
        return _MV("char", cls="char", text=v)
    if v is None:
        return _MV("num", np.zeros((0, 0)), "double")                  # MATLAB 的 []
    if isinstance(v, (np.ndarray, np.generic)):
        a = np.asarray(v)
    elif isinstance(v, bool):
        a = np.asarray(v, dtype=bool)
    elif isinstance(v, (int, float, complex)):
        a = np.asarray(v, dtype=complex if isinstance(v, complex) else float)
    else:
        try:
            a = np.asarray(v)
        except Exception:                                              # noqa: BLE001
            return _MV("cell", cls="cell")
        if a.dtype.kind in "iu":
            a = a.astype(float)                                        # Python 整數字面值 → double
        elif a.dtype.kind not in "bfc":
            return _MV("cell", cls="cell")
    if a.dtype.kind not in "bfciu":
        return _MV("cell", cls="cell")
    cls = _DTYPE_CLASS.get(a.dtype.name, a.dtype.name)
    vec1d = a.ndim == 1
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(-1, 1)
    return _MV("num", a, cls, vec1d=vec1d)


def _is_int_valued(a: np.ndarray) -> bool:
    if a.dtype.kind in "biu":
        return True
    with np.errstate(invalid="ignore"):
        return bool(np.all(np.isfinite(a)) and np.all(a == np.round(a)))


def _check_xy(v, fn: str, pos: int, name: str, types: Sequence[str], integer: bool) -> _MV:
    """biterr／symerr 的 X、Y：型別 → 非空 → 2-D →（biterr）實數 → 非負 → 整數值。"""
    m = _mv(v)
    if m.kind != "num" or m.cls not in types:
        _attr_fail(fn, pos, name, "invalidType", m.cls, ", ".join(types))
    a = m.a
    if a.size == 0:
        _attr_fail(fn, pos, name, "nonempty")
    if a.ndim != 2:
        _attr_fail(fn, pos, name, "2d")
    if integer:
        if np.iscomplexobj(a):
            _attr_fail(fn, pos, name, "real")
        if a.dtype.kind != "b":
            with np.errstate(invalid="ignore"):
                if np.any(a < 0):
                    _attr_fail(fn, pos, name, "nonnegative")
            if not _is_int_valued(a):
                _attr_fail(fn, pos, name, "integer")
    return m


def _layout(x: _MV, y: _MV, ids: Tuple[str, str, str]) -> Tuple[str, _MV, _MV, int, int]:
    """形狀規則：回傳 (預設模式, 矩陣, 向量那一個, 矩陣列數 m, 矩陣欄數 n)。
    兩個輸入裡「向量」去和「矩陣」的每一列（向量是 1×n：row-wise）或每一欄（向量是 m×1：column-wise）比；向量放第一或第二個都行，
    所以先決定誰是矩陣：第一個在某一維是 1、第二個在同一維 > 1 → 第二個才是矩陣。其他情況是 overall，尺寸要一樣。"""
    mat, oth = x, y
    if (x.a.shape[0] == 1 and y.a.shape[0] > 1) or (x.a.shape[1] == 1 and y.a.shape[1] > 1):
        mat, oth = y, x
    rows, cols = mat.a.shape
    vec_rows, vec_cols = oth.a.shape
    if vec_rows == 1 and rows > 1:                                 # 列向量 對 矩陣的每一列：欄數要一樣
        if cols != vec_cols:
            _fail(ids[0])
        return "row-wise", mat, oth, rows, cols
    if vec_cols == 1 and cols > 1:                                 # 欄向量 對 矩陣的每一欄：列數要一樣
        if rows != vec_rows:
            _fail(ids[1])
        return "column-wise", mat, oth, rows, cols
    if (rows, cols) != (vec_rows, vec_cols):
        _fail(ids[2])
    return "overall", mat, oth, rows, cols


def _match_flag(v, fn: str, pos: int, name: str) -> str:
    """validatestring：不分大小寫、唯一前綴。"""
    m = _mv(v)
    head = f"Expected input number {pos}, {name}, to match one of these values:\n\n'overall', 'row-wise', 'column-wise'\n\n"
    head_zh = f"第 {pos} 個輸入 {name} 必須是 'overall'、'row-wise'、'column-wise' 之一"
    if m.kind == "char":
        s = m.text.lower()
        hits = [f for f in FLAGS if s and f.startswith(s)]
        if len(hits) == 1:
            return hits[0]
        raise ErrRateError(f"MATLAB:{fn}:unrecognizedStringChoice", head + f"The input, '{m.text}', did not match any of the valid values.",
                           head_zh + f"；給的是 '{m.text}'。")
    raise ErrRateError(f"MATLAB:{fn}:unrecognizedStringChoice", head + "The input did not match any of the valid values.", head_zh + "；給的不是字串。")


def _check_mode_flag(mode: str, flag: str, ids: Tuple[str, str]) -> None:
    if mode == "row-wise" and flag == "column-wise":
        _fail(ids[0])
    if mode == "column-wise" and flag == "row-wise":
        _fail(ids[1])


def _report(ind: np.ndarray, flag: str, m: int, n: int, k: int):
    if flag == "overall":
        num = float(ind.sum())
        return num, num / (m * n * k)
    if flag == "row-wise":
        num = ind.sum(axis=1).astype(float)
        return num, num / (n * k)
    num = ind.sum(axis=0).astype(float)
    return num, num / (m * k)


def _squeeze_ind(ind: np.ndarray, mat: _MV) -> np.ndarray:
    return ind[:, 0] if (mat.vec1d and ind.shape[1] == 1) else ind


def _k_value(v: _MV, pos: int) -> int:
    """K 的 validateattributes：第 3 個位置 scalar→real→positive→integer；第 4 個位置先多檢查 nonnan、finite。"""
    a = v.a
    if a.size != 1:
        _attr_fail("biterr", pos, "K", "scalar")
    val = a.flat[0]
    if pos == 4:
        if not np.iscomplexobj(a) and np.isnan(val):
            _attr_fail("biterr", pos, "K", "nonnan")
        if not np.iscomplexobj(a) and not np.isfinite(val):
            _attr_fail("biterr", pos, "K", "finite")
    if np.iscomplexobj(a):
        _attr_fail("biterr", pos, "K", "real")
    val = float(val)
    if not val > 0:
        _attr_fail("biterr", pos, "K", "positive")
    if not (math.isfinite(val) and val == round(val)):
        _attr_fail("biterr", pos, "K", "integer")
    return int(val)


_INT2BIT_MAX_BITS = {"double": 53, "single": 24}                 # MATLAB int2bit：浮點輸入的字長上限（整數型別沒有上限、補 0）


def biterr_word_length(*arrays) -> int:
    """MATLAB biterr 的預設字長 K（num_bits＝floor(log2(double(M)))+1，M 是所有輸入的最大值；M＝0 → 1）。
    先把 M 轉成 double 再取 log2：M＝2^j−1 在 j ≥ 49 時 log2 的正確捨入結果就是整數 j，所以 K＝j+1，比位元長度多 1；int64／uint64 的最大值
    轉 double 會進位成 2^63／2^64，K＝64／65。這裡用 libm 的 log2（selftest 驗證過 j＝1..64 這些邊界值和正確捨入一致）。
    輸入要先驗證過是非負實數值；空陣列當 0。"""
    big = 0.0
    for a in arrays:
        a = np.asarray(a)
        if a.size:
            big = max(big, float(a.max()))                         # 各自在原型別取 max 再轉 double（和 MATLAB 的 double(max(...)) 一樣）
    return int(math.floor(math.log2(big))) + 1 if big > 0 else 1


def biterr(*args, k=None, flag=None) -> Tuple[Any, Any, np.ndarray]:
    """MATLAB biterr(x, y[, k][, flag])：回傳 (number, ratio, individual)。k、flag 也可以用關鍵字給（會接在位置引數後面）。
    'overall' 的 number／ratio 是 float；'row-wise'／'column-wise' 是一維陣列（每列／每欄）；individual 是不同位元數（double）。
    double 輸入的 k > 53、single 輸入的 k > 24 → ErrRateError MATLAB:notLessEqual（int2bit 的上限，見模組說明）。"""
    args = list(args)
    if k is not None:
        args.append(k)
    if flag is not None:
        args.append(flag)
    if len(args) < 2:
        _fail("MATLAB:narginchk:notEnoughInputs")
    if len(args) > 4:
        _fail("MATLAB:narginchk:tooManyInputs")
    x = _check_xy(args[0], "biterr", 1, "X", BITERR_TYPES, True)
    y = _check_xy(args[1], "biterr", 2, "Y", BITERR_TYPES, True)
    mode, mat, oth, m, n = _layout(x, y, ("comm:biterr:MismatchedInputDims1", "comm:biterr:MismatchedInputDims2", "comm:biterr:MismatchedInputDims3"))
    nbits = biterr_word_length(x.a, y.a)
    has_logical = x.cls == "logical" or y.cls == "logical"
    if has_logical and nbits != 1:
        _fail("comm:biterr:NonBinaryWithLogical")
    rep = mode
    k_given = flag_given = False
    for pos, v in enumerate(args[2:], start=3):
        mv = _mv(v)
        if mv.kind == "num":
            if pos == 4 and k_given:
                _fail("comm:biterr:InvalidArgsPassed")
            if mv.a.size == 0:
                continue
            kk = _k_value(mv, pos)
            if has_logical and kk != 1:
                _fail("comm:biterr:InvalidNumBitsWithLogical")
            if kk < nbits:
                _fail("comm:biterr:ShortWordLength")
            nbits, k_given = kk, True
        else:
            if pos == 4 and flag_given:
                _fail("comm:biterr:InvalidArgsPassed")
            if mv.kind != "char":
                _fail("comm:biterr:InvalidFlag1")
            if mv.text == "":
                continue
            rep = _match_flag(mv, "biterr", pos, "FLAG")
            flag_given = True
            _check_mode_flag(mode, rep, ("comm:biterr:ColFlagRowInput", "comm:biterr:RowFlagColInput"))
    # int2bit 的字長上限：biterr 把 X、Y 各自用自己的 class 展成 k 個位元（先 X 再 Y），double 最多 53、single 最多 24，超過就是
    # validateattributes 的 '<=' 錯誤；整數型別用 min(k, 型別寬度) 個位元、高位補 0、不報錯；logical 不展開（k 一定是 1）。
    for v in (x, y):
        lim = _INT2BIT_MAX_BITS.get(v.cls)
        if lim is not None and nbits > lim:
            raise ErrRateError("MATLAB:notLessEqual", f"Expected N to be a scalar with value <= {lim}.",
                               f"字長 K＝{nbits} 超過 {v.cls} 輸入可以展開的位元數上限 {lim}（int2bit 的 N 必須 ≤ {lim}）。")
    # 不同的位元：兩邊都是非負整數值且 < 2^k，不用遮罩。經過上限檢查，double／single 的值 < 2^53、整數型別最多 64 位元，轉 uint64 都不失真
    # （沒有這條檢查時 ≥ 2^64 的 double 轉 uint64 會飽和成全 1，數出 64 個錯的位元）。
    xa = np.ascontiguousarray(mat.a.astype(np.uint64) ^ oth.a.astype(np.uint64))
    ind = _POP8[xa.view(np.uint8).reshape(xa.shape + (8,))].sum(axis=-1).astype(float)
    num, rat = _report(ind, rep, m, n, nbits)
    return num, rat, _squeeze_ind(ind, mat)


def symerr(*args, flag=None) -> Tuple[Any, Any, np.ndarray]:
    """MATLAB symerr(x, y[, flg])：回傳 (number, ratio, individual)。individual 是 bool（x ≠ y；NaN ≠ NaN）。"""
    args = list(args)
    if flag is not None:
        args.append(flag)
    if len(args) < 2:
        _fail("MATLAB:narginchk:notEnoughInputs")
    if len(args) > 3:
        _fail("MATLAB:narginchk:tooManyInputs")
    x = _check_xy(args[0], "symerr", 1, "X", SYMERR_TYPES, False)
    y = _check_xy(args[1], "symerr", 2, "Y", SYMERR_TYPES, False)
    if not (np.all(np.isfinite(x.a)) and np.all(np.isfinite(y.a))):
        _warn("comm:symerr:InfOrNaN", 'Inputs contain an "Inf" or "NaN", results may not be reliable.', "輸入含有 Inf 或 NaN，結果可能不可靠。")
    mode, mat, oth, m, n = _layout(x, y, ("comm:symerr:InvalidInputSize1", "comm:symerr:InvalidInputSize2", "comm:symerr:DifferentSizeInputs"))
    rep = mode
    if len(args) == 3:
        rep = _match_flag(args[2], "symerr", 3, "FLG")
        _check_mode_flag(mode, rep, ("comm:symerr:RowInputColumnwiseComparison", "comm:symerr:ColumnInputRowwiseComparison"))
    ma, oa = mat.a, oth.a
    if {x.cls, y.cls} == {"double", "single"}:                 # MATLAB 的 double 對 single 比較：先轉成 single（語言規則，參考資料沒有這種案例）
        ct = np.complex64 if (np.iscomplexobj(ma) or np.iscomplexobj(oa)) else np.float32
        ma, oa = ma.astype(ct), oa.astype(ct)
    with np.errstate(invalid="ignore"):
        ind = ma != oa
    num, rat = _report(ind, rep, m, n, 1)
    return num, rat, _squeeze_ind(ind, mat)


class ErrorRate:
    """comm.ErrorRate：obj(tx, rx[, sel][, rst]) → np.array([rate, errors, compared])，跨呼叫累計。屬性名稱用 snake_case 或 MATLAB 名稱都可以。"""

    def __init__(self, receive_delay=0, computation_delay=0, samples: str = "Entire frame", custom_samples=None, reset_input_port=False, **kw):
        alias = {"ReceiveDelay": "receive_delay", "ComputationDelay": "computation_delay", "Samples": "samples", "CustomSamples": "custom_samples",
                 "ResetInputPort": "reset_input_port"}
        vals = {"receive_delay": receive_delay, "computation_delay": computation_delay, "samples": samples, "custom_samples": custom_samples,
                "reset_input_port": reset_input_port}
        for key, v in kw.items():
            if key not in alias:
                raise TypeError(f"ErrorRate: unknown property {key!r}")
            vals[alias[key]] = v
        self.receive_delay = self._delay(vals["receive_delay"], "ReceiveDelay")
        self.computation_delay = self._delay(vals["computation_delay"], "ComputationDelay")
        s = vals["samples"]
        if not isinstance(s, str) or s not in SAMPLES_SET:
            raise ErrRateError("MATLAB:system:StringSet:InvalidValue",
                               f'"{s}" is not a valid value for the Samples property. Valid values are: "Entire frame" | "Custom" | "Input port".',
                               f"Samples 不能是 \"{s}\"；只能是 \"Entire frame\"、\"Custom\" 或 \"Input port\"。")
        self.samples = s
        self._custom = None if vals["custom_samples"] is None else _mv(vals["custom_samples"])
        if self._custom is not None and s != "Custom":
            _warn("MATLAB:system:nonRelevantProperty", "The CustomSamples property is not relevant in this configuration of the System object.",
                  "這個設定下 CustomSamples 屬性沒有作用（Samples 不是 'Custom'）。")
        self.reset_input_port = self._reset_flag(vals["reset_input_port"])
        self._classes: Optional[List[str]] = None            # 第一次呼叫後鎖定的輸入 class
        self._cast_single = False
        self.reset()

    @staticmethod
    def _delay(v, name: str) -> int:
        m = _mv(v)
        if m.kind != "num" or m.cls != "double":
            _attr_fail(None, None, name, "invalidType", m.cls, "double")
        a = m.a
        if np.iscomplexobj(a):
            _attr_fail(None, None, name, "real")
        with np.errstate(invalid="ignore"):
            if np.any(a < 0):
                _attr_fail(None, None, name, "nonnegative")
        if not _is_int_valued(a):
            _attr_fail(None, None, name, "integer")
        if a.size != 1:
            _attr_fail(None, None, name, "scalar")
        return int(a.flat[0])

    @staticmethod
    def _reset_flag(v) -> bool:
        m = _mv(v)
        if (m.kind == "char" and len(m.text) != 1) or (m.kind == "num" and m.a.size != 1) or m.kind == "cell":
            _fail("MATLAB:validation:IncompatibleSize")
        if m.kind != "num":
            _attr_fail(None, None, "ResetInputPort", "invalidType", m.cls, "numeric, logical")
        if np.iscomplexobj(m.a):
            _attr_fail(None, None, "ResetInputPort", "real")
        return bool(m.a.flat[0])

    def reset(self) -> None:
        """MATLAB reset()：計數、延遲緩衝、起始倒數全部清掉（輸入型別鎖定保留）。"""
        self.errors = 0
        self.compared = 0
        # 延遲緩衝＝最近 RD 個 tx，前面補零：拆成「還有幾個補零」＋「實際收過的樣本」，_tail_zeros + len(_tail) ＝ RD 恆成立，
        # 這樣 RD 很大時也不用配 RD 長的陣列（MATLAB 配 RD+1 的環形緩衝，結果一樣）。
        self._tail_zeros = self.receive_delay
        self._tail = np.zeros(0)
        self._started = 0                                      # 起始倒數已消耗的樣本數（≤ RD+CD）

    def release(self) -> None:
        """MATLAB release()：reset() 再解除輸入型別鎖定與 single 轉型設定。"""
        self.reset()
        self._classes = None
        self._cast_single = False

    def _num_inputs(self) -> int:
        return 2 + (self.samples == "Input port") + bool(self.reset_input_port)

    def _validate_custom(self) -> None:
        check_custom_samples(self._custom)

    @staticmethod
    def _mask(idx: np.ndarray, n: int, ident: str) -> np.ndarray:
        if not (np.all(idx <= n) and np.all(idx >= 0)):
            _fail(ident)
        use = np.zeros(n, dtype=bool)
        use[(idx[idx != 0] - 1).astype(int)] = True
        return use

    def __call__(self, tx, rx, *extra) -> np.ndarray:
        need, got = self._num_inputs(), 2 + len(extra)
        if got < need:
            raise ErrRateError("MATLAB:system:minNumInputs", f"Not enough input arguments. Expected {need} (in addition to System object), got {got}.",
                               f"輸入引數不足：需要 {need} 個，只給了 {got} 個。")
        if got > need:
            raise ErrRateError("MATLAB:system:maxNumInputs", f"Too many input arguments. Expected {need} (in addition to System object), got {got}.",
                               f"輸入引數太多：需要 {need} 個，給了 {got} 個。")
        t, r = _mv(tx), _mv(rx)
        ex = [_mv(e) for e in extra]
        classes = [t.cls, r.cls] + [e.cls for e in ex]
        if self._classes is not None:
            for i, (a, b) in enumerate(zip(classes, self._classes), start=1):
                if a != b:
                    raise ErrRateError("MATLAB:system:inputSpecsChangedErrorD",
                                       f"Changing the data type on input {i} of System object comm.ErrorRate is not allowed without first calling the "
                                       f"{_RELEASE_LINK} method.", f"呼叫之間不能改變第 {i} 個輸入的資料型別；要先呼叫 release()。")
        else:
            if self.samples == "Custom":
                self._validate_custom()
        for v, name in ((t, "Transmitted data vector, TX"), (r, "Received data vector, RX")):
            if v.kind != "num" or v.cls not in ERRORRATE_TYPES:
                _attr_fail(None, None, name, "invalidType", v.cls, ", ".join(ERRORRATE_TYPES))
        if t.a.size and r.a.size and not (t.a.ndim == 2 and r.a.ndim == 2 and t.a.shape[1] == 1 and r.a.shape[1] == 1):
            _fail("dspshared:system:multChanNotSupport")
        tc, rc = np.iscomplexobj(t.a), np.iscomplexobj(r.a)
        if not tc and rc:
            _fail("MATLAB:system:invalidComplexityNeedReal")
        if tc and not rc:
            _fail("MATLAB:system:invalidComplexityNeedComplex")
        ltx = max(t.a.shape) if t.a.size else 0
        lrx = max(r.a.shape) if r.a.size else 0
        if ltx != 1 and lrx != 1 and ltx != lrx:
            _fail("comm:system:txRxLengthsDiffer")
        n = max(ltx, lrx)
        sel = rst = None
        if self.samples == "Input port":
            sel = ex[0]
            if self.reset_input_port:
                rst = self._check_rst(ex[1])
            if sel.kind != "num" or sel.cls != "double":
                _attr_fail(None, None, "SEL", "invalidType", sel.cls, "double")
            if np.iscomplexobj(sel.a):
                _attr_fail(None, None, "SEL", "real")
            if not _is_int_valued(sel.a):
                _attr_fail(None, None, "SEL", "integer")
            if not (sel.a.ndim == 2 and sel.a.shape[1] == 1):
                _attr_fail(None, None, "SEL", "column")
        elif self.reset_input_port:
            rst = self._check_rst(ex[0])
        use = None
        if self.samples == "Custom":
            use = self._mask(self._custom.a.ravel(order="F").astype(float), n, "comm:system:sampsElemExceedInWidth")
        if self._classes is None:                                  # 第一次呼叫：記下型別
            self._classes = classes
            self._cast_single = {t.cls, r.cls} == {"double", "single"}
        if rst is not None and (np.isnan(rst) or rst != 0):
            self.errors = 0
            self.compared = 0
        if sel is not None:
            use = self._mask(sel.a.ravel().astype(float), n, "comm:system:sampsWidthExceedInWidth")
        if use is None:
            use = np.ones(n, dtype=bool)
        if n and t.a.size and r.a.size:
            self._core(t.a.ravel(order="F"), r.a.ravel(order="F"), ltx, lrx, n, use)
        rate = self.errors / self.compared if self.compared else 0.0
        return np.array([rate, float(self.errors), float(self.compared)])

    step = __call__

    @staticmethod
    def _check_rst(v: _MV) -> float:
        if v.kind != "num" or v.cls not in ("double", "logical"):
            _attr_fail(None, None, "RST", "invalidType", v.cls, "double, logical")
        if np.iscomplexobj(v.a):
            _attr_fail(None, None, "RST", "real")
        if v.a.size != 1:
            _attr_fail(None, None, "RST", "scalar")
        return float(v.a.flat[0])

    def _core(self, tv: np.ndarray, rv: np.ndarray, ltx: int, lrx: int, n: int, use: np.ndarray) -> None:
        if self._cast_single:
            tv, rv = tv.astype(np.float32), rv.astype(np.float32)
        dt = complex if (np.iscomplexobj(tv) or np.iscomplexobj(rv)) else float
        tv, rv = tv.astype(dt), rv.astype(dt)
        if ltx == 1 and lrx == 1 and self.receive_delay == 0:
            # R2025a 的純量路徑：RD＝0 時立刻比較、起始倒數器不動 → ComputationDelay 無效
            if use[0]:
                self.compared += 1
                self.errors += int(tv[0] != rv[0])
            return
        txv = np.full(n, tv[0], dtype=dt) if ltx == 1 else tv
        rxv = np.full(n, rv[0], dtype=dt) if lrx == 1 else rv
        # 緩衝裡的串流＝ [補零 × _tail_zeros, _tail, 這一訊框]；前 n 個是第 i 個樣本要對的 tx[i − RD]，最後 RD 個留到下一訊框
        z = min(self._tail_zeros, n)                               # 這一訊框裡還對到補零的樣本數
        hist = np.concatenate([self._tail.astype(dt), txv])
        delayed = np.concatenate([np.zeros(z, dtype=dt), hist[:n - z]])
        self._tail_zeros -= z
        self._tail = hist[n - z:]                                  # 長度 len(_tail)+z，加上剩下的補零仍是 RD
        total = self.receive_delay + self.computation_delay
        skip = min(n, total - self._started)
        self._started += skip
        sel = use.copy()
        sel[:skip] = False
        with np.errstate(invalid="ignore"):
            self.errors += int(np.count_nonzero(delayed[sel] != rxv[sel]))
        self.compared += int(np.count_nonzero(sel))


def check_custom_samples(custom) -> np.ndarray:
    """comm.ErrorRate 的 CustomSamples 檢查（Samples＝'Custom' 時第一次呼叫做的那一段；ErrorRate 自己也用這個函式）：型別 double → 實數 → 非負 →
    整數值 → 向量（非空）。沒給（None）或空的 → MATLAB:expectedVector「Expected CustomSamples to be a vector.」（R2025a 的實際行為；文件說會比全部）。
    回傳攤平（欄優先）的 float 陣列。DSV 的錯誤率比對視窗（第四批 T5）也用這條檢查。"""
    c = custom if isinstance(custom, _MV) else _mv(custom)
    if c.kind != "num" or c.cls != "double":
        _attr_fail(None, None, "CustomSamples", "invalidType", c.cls, "double")
    if np.iscomplexobj(c.a):
        _attr_fail(None, None, "CustomSamples", "real")
    with np.errstate(invalid="ignore"):
        if np.any(c.a < 0):
            _attr_fail(None, None, "CustomSamples", "nonnegative")
    if not _is_int_valued(c.a):
        _attr_fail(None, None, "CustomSamples", "integer")
    if not (c.a.ndim == 2 and c.a.size >= 1 and min(c.a.shape) == 1):
        _attr_fail(None, None, "CustomSamples", "vector")
    return c.a.ravel(order="F").astype(float)


def custom_mask(custom, n: int) -> np.ndarray:
    """CustomSamples（check_custom_samples 檢查過的 1 起算位置）→ 長度 n 的 bool 遮罩，和 comm.ErrorRate 每個訊框的做法一樣：0 略過、重複只算一次；
    有任何位置 > n → comm:system:sampsElemExceedInWidth「The elements of the Samples property must be smaller than or equal to the input length.」。"""
    return ErrorRate._mask(np.asarray(custom, dtype=float).ravel(), int(n), "comm:system:sampsElemExceedInWidth")


def _int_arg(v, name: str, nonnegative: bool) -> int:
    """align_window()／error_rate() 的整數參數：純量、實數、整數值（Python／numpy 的整數、整數值浮點都可以），nonnegative 時還要 ≥ 0。
    錯誤用 comm.ErrorRate 設定 ReceiveDelay／ComputationDelay 時同樣的識別碼與訊息（MATLAB:expectedNonnegative「Expected ReceiveDelay to be
    nonnegative.」…），GUI 可以共用。"""
    m = _mv(v)
    if m.kind != "num" or m.a.size != 1:
        _attr_fail(None, None, name, "scalar")
    if np.iscomplexobj(m.a):
        _attr_fail(None, None, name, "real")
    val = float(m.a.flat[0])
    if nonnegative and val < 0:
        _attr_fail(None, None, name, "nonnegative")
    if not (math.isfinite(val) and val == round(val)):
        _attr_fail(None, None, name, "integer")
    return int(val)


def align_window(tx, rx, receive_delay: int = 0, computation_delay: int = 0, tx_offset: int = 0, rx_offset: int = 0) -> Dict[str, Any]:
    """DSV 自己加的（不是 MATLAB）：把兩條長度、起點不同的符號序列對齊成 comm.ErrorRate 的比較視窗。
    tx[i] 在位置 tx_offset+i、rx[j] 在位置 rx_offset+j（單位＝符號）；位置 p 的 rx 對位置 p−receive_delay 的 tx，兩邊都存在的位置才比，
    再跳過最前面 computation_delay 個。回傳 dict：tx、rx（等長的對齊片段）、tx_index、rx_index（對回原陣列的索引）、start（第一個比較位置）、n。
    tx、rx 等長、offset 都是 0 時，n＝len−RD−CD、rx[p] 對 tx[p−RD]，和 comm.ErrorRate 一個訊框的結果一樣。
    receive_delay、computation_delay 和 comm.ErrorRate 一樣只能是非負整數（負的丟 ErrRateError MATLAB:expectedNonnegative；之前負的
    computation_delay 會讓索引變負、numpy 從尾端繞回來算出錯的視窗）；rx 比 tx 早的情況用 tx_offset／rx_offset 表示（兩者可以是負的，要是整數）。"""
    tx = np.asarray(tx).ravel()
    rx = np.asarray(rx).ravel()
    rd = _int_arg(receive_delay, "ReceiveDelay", True)
    cd = _int_arg(computation_delay, "ComputationDelay", True)
    to = _int_arg(tx_offset, "tx_offset", False)
    ro = _int_arg(rx_offset, "rx_offset", False)
    p0 = max(ro, to + rd) + cd                                         # 第一個兩邊都有、且過了 CD 的位置
    p1 = min(ro + rx.size, to + tx.size + rd)                          # 最後一個都有的位置 + 1
    n = max(0, p1 - p0)
    ri = np.arange(p0 - ro, p0 - ro + n)                               # 都是 ≥ 0 的索引（p0 ≥ ro、p0 ≥ to+rd）
    ti = ri + ro - rd - to
    return {"tx": tx[ti], "rx": rx[ri], "tx_index": ti, "rx_index": ri, "start": p0, "n": n}


def error_rate(tx, rx, receive_delay: int = 0, computation_delay: int = 0, tx_offset: int = 0, rx_offset: int = 0, bits: bool = False,
               k: Optional[int] = None) -> Dict[str, Any]:
    """DSV 自己加的：align_window() 之後用 symerr（bits=False，符號錯誤率）或 biterr（bits=True，k 位元／符號）算
    rate、errors、compared（位元模式時 compared＝n·k），positions＝有錯的 rx 索引（畫差異區間用），k＝實際用的位元數。輸入不合 MATLAB 規定
    （負數、非整數…）時丟 ErrRateError，由呼叫端決定要不要先門檻化。"""
    w = align_window(tx, rx, receive_delay, computation_delay, tx_offset, rx_offset)
    out: Dict[str, Any] = dict(w)
    out.update(rate=0.0, errors=0.0, compared=0.0, positions=np.zeros(0, dtype=int), k=1)
    if w["n"] == 0:
        return out
    for key in ("tx", "rx"):                                           # DSV 的 0/1 數位訊號可能是 bool：當 double 0/1（biterr／symerr 的 logical 規則不套用）
        if w[key].dtype == bool:
            w[key] = w[key].astype(float)
    if bits:
        num, rat, ind = biterr(w["tx"], w["rx"]) if k is None else biterr(w["tx"], w["rx"], int(k))
        kk = int(k) if k is not None else biterr_word_length(w["tx"], w["rx"])   # biterr 已驗證過是非負整數、同一條預設 k 規則
        out.update(rate=float(rat), errors=float(num), compared=float(w["n"] * kk), k=kk)
    else:
        num, rat, ind = symerr(w["tx"], w["rx"])
        out.update(rate=float(rat), errors=float(num), compared=float(w["n"]))
    out["positions"] = w["rx_index"][np.asarray(ind).ravel() != 0]
    return out


# ----------------------------------------------------------------------------------------------------------------------- selftest
_NP = {"double": np.float64, "single": np.float32, "logical": np.bool_, "int8": np.int8, "int16": np.int16, "int32": np.int32, "int64": np.int64,
       "uint8": np.uint8, "uint16": np.uint16, "uint32": np.uint32, "uint64": np.uint64}


def _lst(v) -> list:
    """jsonencode 會把單一元素的陣列寫成純量：一律還原成 list。"""
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _dec(e):
    """兩種參考 JSON 的編碼 → Python 值（numpy 陣列照 MATLAB class 給 dtype、char／string → str、cell → list）。
    er_ref.json：re／im 是 %.17g 字串；error_rate_ref.json：data 是數字（NaN/Inf 寫成 null，posinf／neginf 記位置）或複數的 re／im。"""
    if e is None:
        return None
    c = e["class"]
    if c in ("char", "string"):
        return e["text"]
    if c == "cell":
        return [_dec(i) for i in _lst(e.get("items"))] if e.get("items") is not None else ["cell"]
    size = tuple(int(s) for s in _lst(e["size"]))
    if "data" in e:
        a = np.array([np.nan if v is None else float(v) for v in _lst(e["data"])], dtype=float)
        for i in _lst(e.get("posinf")):
            a[int(i) - 1] = np.inf
        for i in _lst(e.get("neginf")):
            a[int(i) - 1] = -np.inf
    else:
        a = np.array([float(v) for v in _lst(e.get("re"))], dtype=float)
        im = _lst(e.get("im"))
        if im:
            a = a + 1j * np.array([float(v) for v in im])
    a = a.reshape(size, order="F") if a.size == int(np.prod(size)) else np.zeros(size)
    if np.iscomplexobj(a):
        return a.astype(np.complex64 if c == "single" else np.complex128)
    return a.astype(_NP[c]) if c in _NP else a


_CLS_NP = {"double": "float64", "single": "float32", "logical": "bool"}       # MATLAB class ↔ 模組輸出的 dtype（Python float → float64）


def _same(ref_e, got, rtol: float = 1e-12) -> Tuple[bool, bool, str]:
    """got（float／一維／二維）對 MATLAB 的值（class、大小 + column-major）：(形狀相容且數值一致, 位元完全相同, 第一個不同處的說明)。"""
    a = np.asarray(_dec(ref_e))
    g = np.asarray(got)
    want = _CLS_NP.get(ref_e.get("class"))
    if want is not None and g.dtype.name != want:
        return False, False, f"class {g.dtype.name} vs MATLAB {ref_e['class']}"
    g = g.astype(complex) if np.iscomplexobj(g) else g.astype(float)
    size = a.shape
    if g.ndim == 2:
        shape_ok, flat = g.shape == size, g.ravel(order="F")
    elif g.ndim == 1:
        shape_ok, flat = size in ((g.size, 1), (1, g.size)), g
    else:
        shape_ok, flat = size == (1, 1), g.reshape(1)
    r = a.ravel(order="F").astype(flat.dtype)
    if not shape_ok or flat.size != r.size:
        return False, False, f"shape {g.shape} vs MATLAB {size}"
    exact = bool(np.array_equal(flat, r, equal_nan=True))
    close = bool(np.allclose(flat, r, rtol=rtol, atol=0.0, equal_nan=True))
    if close:
        return True, exact, ""
    with np.errstate(invalid="ignore"):
        bad = np.nonzero(~(np.isclose(flat, r, rtol=rtol, atol=0.0, equal_nan=True)))[0]
    i = int(bad[0])
    return False, False, f"[{i}] got {flat[i]!r} vs MATLAB {r[i]!r}（{bad.size} 處）"


def _expect(c) -> Tuple[bool, str, str, List[Tuple[str, str]]]:
    """(ok, 錯誤識別碼, 錯誤訊息, [(警告識別碼, 警告訊息)])——兩種 JSON 的欄位名稱不同。
    number_1out_equal／number_nargout1_same（nargout 語意）和 meta.disp_default（物件顯示）沒有 Python 對應，不比。"""
    if "err_id" in c:
        ok, eid, emsg, wid, wmsg = bool(c["ok"]), c.get("err_id") or "", c.get("err_msg") or "", c.get("warn_id") or "", c.get("warn_msg") or ""
    else:
        er, wr = c.get("error") or {}, c.get("warning") or {}
        ok, eid, emsg = bool(c["ok"]), er.get("identifier") or "", er.get("message") or ""
        wid, wmsg = wr.get("identifier") or "", wr.get("message") or ""
    return ok, eid, emsg, ([(wid, wmsg)] if wid else [])


def _warned(w) -> List[Tuple[str, str]]:
    """catch_warnings 收到的 ErrRateWarning → 排序後的 (識別碼, 訊息)（識別碼和訊息都要和 MATLAB 一樣）。"""
    return sorted({(x.message.identifier, x.message.message) for x in w if isinstance(x.message, ErrRateWarning)})


class _Tally:
    def __init__(self):
        self.total = self.matched = self.exact = 0
        self.bad: List[str] = []
        self.groups: Dict[str, List[Any]] = {}                        # group → [總數, 一致數, 不一致說明]

    def add(self, group: str, name: str, ok: bool, exact: bool, why: str = "") -> None:
        g = self.groups.setdefault(group, [0, 0, []])
        g[0] += 1
        g[1] += ok
        self.total += 1
        self.matched += ok
        self.exact += exact and ok
        if not ok:
            self.bad.append(f"{name}: {why}")
            g[2].append(f"{name}: {why}")


def _run_fn_case(c, tally: _Tally, tag: str) -> None:
    fn = biterr if c["func"] == "biterr" else symerr
    args = [_dec(a) for a in _lst(c["args"])]
    ok_ref, eid, emsg, warn_ref = _expect(c)
    res = err = None
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            res = fn(*args)
        except ErrRateError as e:
            err = e
    warned = _warned(w)
    group = f"{c['func']} {'值' if ok_ref else '錯誤'}"
    name = f"{tag}:{c['name']}"
    if not ok_ref:
        if err is None:
            tally.add(group, name, False, False, f"沒有丟錯誤（MATLAB {eid}），得到 number={res[0]!r}")
        elif err.identifier != eid or err.message != emsg:
            tally.add(group, name, False, False, f"識別碼／訊息不同：got {err.identifier} {err.message!r} vs {eid} {emsg!r}")
        else:
            tally.add(group, name, True, True)
        return
    if err is not None:
        tally.add(group, name, False, False, f"不該有錯誤卻丟出 {err.identifier}")
        return
    exact_all = True
    for key, got in zip(("number", "ratio", "individual"), res):
        ok, exact, why = _same(c[key], got)
        exact_all = exact_all and exact
        if not ok:
            tally.add(group, name, False, False, f"{key} {why}")
            return
    if warned != warn_ref:
        tally.add(group, name, False, False, f"警告 {warned} vs MATLAB {warn_ref}")
        return
    tally.add(group, name, True, exact_all)


def _run_er_case(c, tally: _Tally, tag: str) -> None:
    name = f"{tag}:{c['name']}"
    ok_ref, eid, emsg, warn_ref = _expect(c)
    props = [_dec(p) for p in _lst(c.get("props"))]
    kw = {props[i]: props[i + 1] for i in range(0, len(props), 2)}
    frames = _lst(c.get("frames"))
    if frames and isinstance(frames[0], dict):
        frames = [frames]
    ys_ref = _lst(c.get("y"))
    reset_after = c.get("reset_after_frame")
    got: List[np.ndarray] = []
    err = None
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            obj = ErrorRate(**kw)
            for i, f in enumerate(frames):
                got.append(obj(*[_dec(a) for a in _lst(f)]))
                if reset_after == i + 1:
                    obj.reset()
        except ErrRateError as e:
            err = e
    warned = _warned(w)
    group = f"comm.ErrorRate {'值' if ok_ref else '錯誤'}"
    if len(got) != len(ys_ref):
        tally.add(group, name, False, False, f"回傳 {len(got)} 個 y，MATLAB {len(ys_ref)} 個" + (f"（錯誤 {err.identifier}）" if err else ""))
        return
    exact_all = True
    for i, (y_ref, y) in enumerate(zip(ys_ref, got)):
        ok, exact, why = _same(y_ref, y)
        exact_all = exact_all and exact
        if not ok:
            tally.add(group, name, False, False, f"y{i + 1} {why}")
            return
    if ok_ref:
        if err is not None:
            tally.add(group, name, False, False, f"不該有錯誤卻丟出 {err.identifier}")
            return
    else:
        if err is None:
            tally.add(group, name, False, False, f"沒有丟錯誤（MATLAB {eid}）")
            return
        if err.identifier != eid or err.message != emsg:
            tally.add(group, name, False, False, f"識別碼／訊息不同：got {err.identifier} {err.message!r} vs {eid} {emsg!r}")
            return
    if warned != warn_ref:
        tally.add(group, name, False, False, f"警告 {warned} vs MATLAB {warn_ref}")
        return
    tally.add(group, name, True, exact_all)


def _run_reset_case(c, tally: _Tally, tag: str) -> None:
    tx, rx = _dec(c["tx"]), _dec(c["rx"])
    obj = ErrorRate(receive_delay=1, computation_delay=1)              # er_ref.m 的 erreset()：RD＝1、CD＝1
    y1 = obj(tx, rx)
    y2 = obj(tx, rx)
    obj.reset()
    y3 = obj(tx, rx)
    obj.release()
    y4 = obj(tx, rx)
    exact_all = True
    for key, y in (("y1", y1), ("y2", y2), ("y3_after_reset", y3), ("y4_after_release", y4)):
        ok, exact, why = _same(c[key], y)
        exact_all = exact_all and exact
        if not ok:
            tally.add("comm.ErrorRate reset()/release()", f"{tag}:{c['name']}", False, False, f"{key} {why}")
            return
    tally.add("comm.ErrorRate reset()/release()", f"{tag}:{c['name']}", True, exact_all)


def _er_whole_stream(c) -> Optional[Tuple[np.ndarray, np.ndarray, int, int, np.ndarray]]:
    """Entire frame、沒有 reset 埠、tx／rx 都是向量的 comm.ErrorRate 參考案例 → (tx 全串, rx 全串, RD, CD, 最後的 y)。"""
    if not c.get("ok") or c.get("reset_after_frame"):
        return None
    props = [_dec(p) for p in _lst(c.get("props"))]
    kw = {props[i]: props[i + 1] for i in range(0, len(props), 2)}
    if any(k not in ("ReceiveDelay", "ComputationDelay") for k in kw):
        return None
    frames = _lst(c.get("frames"))
    if not frames:
        return None
    if isinstance(frames[0], dict):
        frames = [frames]
    txs, rxs = [], []
    for f in frames:
        t, r = (_dec(a) for a in _lst(f)[:2])
        if t.size != r.size or t.size <= 1:
            return None
        txs.append(t.ravel(order="F"))
        rxs.append(r.ravel(order="F"))
    rd = int(np.asarray(kw.get("ReceiveDelay", 0)).flat[0])
    cd = int(np.asarray(kw.get("ComputationDelay", 0)).flat[0])
    return np.concatenate(txs), np.concatenate(rxs), rd, cd, np.asarray(_dec(_lst(c["y"])[-1])).ravel(order="F")


def selftest(check, ref_dir: str) -> None:
    """拿 MATLAB R2025a 算的參考值逐筆比對（tests/matlab_ref/error_rate/*.json；研究資料夾的 ref_error_rate.m／er_ref.m 產生）。"""
    import json
    import os
    import time as _time
    d = os.path.join(ref_dir, "error_rate")
    files = [f for f in ("error_rate_ref.json", "er_ref.json") if os.path.isfile(os.path.join(d, f))]
    if files:
        tally = _Tally()
        for fname in files:
            tag = fname.split("_ref")[0]
            R = json.load(open(os.path.join(d, fname), encoding="utf-8"))
            for c in R["cases"]:
                if c["func"] in ("biterr", "symerr"):
                    _run_fn_case(c, tally, tag)
                elif c["func"] == "comm.ErrorRate":
                    _run_er_case(c, tally, tag)
                else:
                    _run_reset_case(c, tally, tag)
        for group in ("biterr 值", "biterr 錯誤", "symerr 值", "symerr 錯誤", "comm.ErrorRate 值", "comm.ErrorRate 錯誤", "comm.ErrorRate reset()/release()"):
            n, ok, bad = tally.groups.get(group, [0, 0, []])
            check(ok == n, f"{group} vs MATLAB R2025a：{ok}/{n} 筆逐筆一致（{'、'.join(files)}）" + (f"；不一致：{bad[:6]}" if ok != n else ""))
        check(tally.matched == tally.total, f"誤碼率 vs MATLAB R2025a 合計：{tally.matched}/{tally.total} 筆一致（{tally.exact} 筆位元完全相同、"
                                            f"rtol 1e-12；輸出 class、錯誤與警告的識別碼和訊息逐字比對）" + (f"；不一致：{tally.bad[:10]}" if tally.bad else ""))
        # DSV 的 align_window／error_rate：對 comm.ErrorRate 的「整串」案例，結果要等於 MATLAB 最後一個 y
        n_ok = n_all = 0
        bad = []
        for fname in files:
            R = json.load(open(os.path.join(d, fname), encoding="utf-8"))
            for c in R["cases"]:
                if c["func"] != "comm.ErrorRate":
                    continue
                s = _er_whole_stream(c)
                if s is None:
                    continue
                tx, rx, rd, cd, y = s
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")                    # er_nan 的 Inf/NaN 警告
                    r = error_rate(tx, rx, rd, cd)
                n_all += 1
                if r["errors"] == y[1] and r["compared"] == y[2] and r["rate"] == y[0]:
                    n_ok += 1
                else:
                    bad.append(f"{c['name']}: {[r['rate'], r['errors'], r['compared']]} vs {y.tolist()}")
        check(n_all >= 20 and n_ok == n_all, f"DSV align_window＋symerr 對 comm.ErrorRate 整串案例（Entire frame、RD／CD）：{n_ok}/{n_all} 筆的 "
                                            f"[rate, errors, compared] 等於 MATLAB 最後一個 y" + (f"；不一致：{bad[:5]}" if bad else ""))
    else:
        check(True, "（沒有 tests/matlab_ref/error_rate：略過 MATLAB 誤碼率比對）")
    # 文件範例（biterr／symerr 的 doc 例子）＋ Python 介面：一維陣列、關鍵字 k／flag、中文訊息
    A = np.array([[1, 2, 3], [1, 2, 2]])
    B = np.array([[1, 2, 0], [3, 2, 2]])
    n1, r1, i1 = biterr(A, B)
    n2, r2, i2 = biterr(A, B, k=3, flag="column-wise")
    n3, r3, i3 = symerr(A, B)
    n4, r4, i4 = biterr([1, 0, 1, 1], [1, 1, 1, 0])
    try:
        biterr([1, -1], [1, 1])
        zh = ""
    except ErrRateError as e:
        zh = e.zh if e.identifier == "MATLAB:biterr:expectedNonnegative" else ""
    # ratio 都是 number/(整數) 的一次除法，和 1/6、1/3 這些字面值一樣是同一個有理數的正確捨入 → 精確相等，不用容差
    check(n1 == 3 and r1 == 0.25 and i1.shape == (2, 3) and np.array_equal(n2, [1, 0, 2]) and np.array_equal(r2, [1 / 6, 0, 1 / 3])
          and n3 == 2 and r3 == 1 / 3 and i3.dtype == bool and n4 == 2 and r4 == 0.5 and i4.shape == (4,) and i4.tolist() == [0, 1, 0, 1]
          and zh.startswith("第 1 個輸入 X 必須非負"),
          f"biterr／symerr 文件範例：N={n1:g} R={r1:g}；k=3 column-wise N={n2.tolist()}；symerr N={n3:g}；一維輸入 individual 一維；中文訊息「{zh}」")
    # int2bit 的字長上限與預設 k 的 log2 規則（照 MATLAB biterr／int2bit 的定義；參考資料最大只到 k=16、1023，MATLAB 沒實測這些）。
    # 預期的 number 是 Python 大整數算的 popcount，不是 MATLAB 數字；ratio＝number/k 一次除法，精確比
    def _err(fn, *a, **kw):
        try:
            fn(*a, **kw)
        except ErrRateError as e:
            return e.identifier, e.message
        return None, None
    lim53 = ("MATLAB:notLessEqual", "Expected N to be a scalar with value <= 53.")
    lim24 = ("MATLAB:notLessEqual", "Expected N to be a scalar with value <= 24.")
    d = lambda *v: np.array(v, dtype=float)                            # noqa: E731
    errs = (_err(biterr, d(2.0 ** 64), d(0)) == lim53, _err(biterr, d(1e20, 0), d(0, 0)) == lim53,        # 以前轉 uint64 飽和 → 64 個錯位元
            _err(biterr, d(2.0 ** 53), d(0)) == lim53, _err(biterr, d(2.0 ** 53 - 1), d(0)) == lim53,    # 2^53−1 的 log2 進位 → k＝54
            _err(biterr, [3, 0], [0, 0], 54) == lim53, _err(biterr, np.float32(2 ** 30), np.float32(0)) == lim24,
            _err(biterr, d(2.0 ** 30), np.float32(0)) == lim24,                                           # X double 可以、Y single 不行
            _err(biterr, d(2.0 ** 60), d(0), 3)[0] == "comm:biterr:ShortWordLength")                      # k 的檢查在上限之前
    n53, r53, _ = biterr(d(2.0 ** 53 - 23), d(0))                     # 2^53−23 的 log2 不進位 → k＝53，剛好可以
    n49, r49, _ = biterr(d(2.0 ** 49 - 1), d(0))                      # log2 進位 → k＝50、ratio 49/50（bit_length 會給 1.0）
    n48, r48, _ = biterr(d(2.0 ** 48 - 1), d(0))                      # 不進位 → k＝48
    n64, r64, _ = biterr(np.array([2 ** 64 - 1], dtype=np.uint64), np.array([0], dtype=np.uint64))    # double(max) 進位成 2^64 → k＝65
    n63, r63, _ = biterr(np.array([2 ** 63 - 1], dtype=np.int64), np.array([0], dtype=np.int64))      # → k＝64
    n8, r8, _ = biterr(np.array([255], dtype=np.uint8), np.array([0], dtype=np.uint8), 10)             # 整數型別 k 可以超過寬度、補 0
    k_rule = all(biterr_word_length(d(2.0 ** j - 1)) == (j if j < 49 else j + 1) for j in range(1, 54)) and biterr_word_length(d(0)) == 1
    rng = np.random.default_rng(11)
    xv = rng.integers(0, 2 ** 53 - 22, 2000)                           # 最大 2^53−23：k＝53、double 轉 uint64 不失真
    yv = rng.integers(0, 2 ** 53 - 22, 2000)
    nbig, rbig, ibig = biterr(xv.astype(float), yv.astype(float))
    pop = np.array([bin(int(a) ^ int(b)).count("1") for a, b in zip(xv, yv)], dtype=float)
    check(all(errs) and (n53, r53) == (bin(2 ** 53 - 23).count("1"), bin(2 ** 53 - 23).count("1") / 53) and (n49, r49) == (49, 49 / 50)
          and (n48, r48) == (48, 1.0) and (n64, r64) == (64, 64 / 65) and (n63, r63) == (63, 63 / 64) and (n8, r8) == (8, 0.8) and k_rule
          and np.array_equal(ibig, pop) and nbig == pop.sum() and rbig == pop.sum() / (2000 * 53),
          f"biterr 字長：double>53／single>24 位元 → MATLAB:notLessEqual {sum(errs)}/{len(errs)} 種；2^53−23 → k=53 N={n53:g}；2^49−1 → k=50 "
          f"R={r49:g}；uint64 最大值 k=65 R={r64:.4f}；int64 k=64；uint8 k=10 R={r8:g}；2000 個 <2^53 的 double popcount 和 Python 大整數一致")
    # align_window／error_rate：負的或非整數的延遲要擋掉（之前負 CD 會讓 numpy 負索引繞回去），rx 比 tx 早用 offset 表示
    ten = np.arange(10.0)
    neg = (_err(align_window, ten, ten, computation_delay=-3) == ("MATLAB:expectedNonnegative", "Expected ComputationDelay to be nonnegative."),
           _err(error_rate, ten, ten, receive_delay=-1) == ("MATLAB:expectedNonnegative", "Expected ReceiveDelay to be nonnegative."),
           _err(align_window, ten, ten, receive_delay=1.5) == ("MATLAB:expectedInteger", "Expected ReceiveDelay to be integer-valued."),
           _err(align_window, ten, ten, tx_offset=0.5) == ("MATLAB:expectedInteger", "Expected tx_offset to be integer-valued."),
           _err(align_window, ten, ten, computation_delay=np.nan) == ("MATLAB:expectedInteger", "Expected ComputationDelay to be integer-valued."))
    cd3 = error_rate(ten, ten, computation_delay=3)
    lead = align_window(ten, ten, tx_offset=3)                         # rx 比 tx 早 3 個符號：rx[3..9] 對 tx[0..6]
    lead2 = align_window(ten, ten, rx_offset=-3)                       # 同一件事用負的 rx_offset 表示
    check(all(neg) and cd3["compared"] == 7 and cd3["rx_index"][0] == 3 and cd3["tx_index"][0] == 3 and lead["n"] == 7
          and lead["tx_index"].tolist() == list(range(7)) and lead["rx_index"].tolist() == list(range(3, 10))
          and lead2["tx_index"].tolist() == lead["tx_index"].tolist() and lead2["rx_index"].tolist() == lead["rx_index"].tolist(),
          f"align_window／error_rate 參數檢查：負的 RD／CD、非整數、NaN → MATLAB:expectedNonnegative／expectedInteger {sum(neg)}/{len(neg)} 種；"
          f"CD=3 比 {cd3['compared']:g} 個；rx 早 3 個用 tx_offset=3 或 rx_offset=−3 都得到 tx[0..6] 對 rx[3..9]")
    # comm.ErrorRate 的延遲緩衝不配 RD 長的陣列：RD=1e12 也能建、能跑；訊框長度不一、RD 跨好幾個訊框時結果要等於整串一次算
    t0 = _time.time()
    huge = ErrorRate(receive_delay=10 ** 12)
    yh = huge(np.arange(3.0), np.arange(3.0))
    huge2 = ErrorRate(receive_delay=10 ** 9, computation_delay=10 ** 9)
    yh2 = huge2(np.arange(3.0), np.arange(3.0))
    dt_huge = _time.time() - t0
    stx = rng.integers(0, 4, 60).astype(float)
    srx = np.concatenate([np.zeros(7), stx[:-7]])
    srx[[20, 33, 41]] = (srx[[20, 33, 41]] + 1) % 4
    stream = ErrorRate(receive_delay=7, computation_delay=2)
    pos = 0
    for size in (2, 3, 1, 5, 4, 9, 6, 2, 8, 7, 3, 10):               # 60 個樣本，訊框長度不一（第 1 個訊框整個還在補零段）
        ys = stream(stx[pos:pos + size], srx[pos:pos + size])
        pos += size
    whole = error_rate(stx, srx, receive_delay=7, computation_delay=2)
    check(yh.tolist() == [0, 0, 0] and yh2.tolist() == [0, 0, 0] and dt_huge < 0.5 and pos == 60 and ys[1] == 3 and ys[2] == 60 - 9
          and ys.tolist() == [whole["rate"], whole["errors"], whole["compared"]] and stream._tail.size == 7 and stream._tail_zeros == 0,
          f"comm.ErrorRate 延遲緩衝：RD=1e12／RD=CD=1e9 建構＋一個訊框 {dt_huge * 1e3:.1f} ms、不配記憶體；RD=7 分 12 個不等長訊框 → "
          f"[{ys[0]:.4f}, {ys[1]:g}, {ys[2]:g}] 等於整串一次算")
    # DSV 的對齊視窗：起點、長度、延遲都不同
    tx = np.arange(100) % 4
    rx = np.full(90, 7.0)
    rx[6:] = tx[:84]                                                   # rx[j]＝tx[j−6]（位置：tx 從 5 起、rx 從 2 起、RD＝3）
    flips = np.array([20, 30, 40, 50]) + 6
    rx[flips] = (rx[flips] + 1) % 4
    w = align_window(tx, rx, receive_delay=3, tx_offset=5, rx_offset=2)
    r0 = error_rate(tx, rx, receive_delay=3, tx_offset=5, rx_offset=2)
    r10 = error_rate(tx, rx, receive_delay=3, computation_delay=10, tx_offset=5, rx_offset=2)
    rb = error_rate(tx, rx, receive_delay=3, tx_offset=5, rx_offset=2, bits=True)
    check(w["n"] == 84 and w["start"] == 8 and w["rx_index"][0] == 6 and w["tx_index"][0] == 0 and r0["errors"] == 4 and r0["compared"] == 84
          and r0["positions"].tolist() == flips.tolist() and r10["compared"] == 74 and r10["errors"] == 4 and r10["rx_index"][0] == 16
          and rb["k"] == 2 and rb["compared"] == 168 and rb["errors"] == 4,
          f"align_window／error_rate（tx 起點 5、rx 起點 2、RD 3）：視窗 {w['n']} 個、從 rx[6] 起；4 個錯在 rx{flips.tolist()}；CD 10 → 74 個；"
          f"位元模式 k=2、168 位元、{rb['errors']:g} 錯")
    # 大資料：1e6 個 8 位元符號
    rng = np.random.default_rng(3)
    big_tx = rng.integers(0, 256, 1_000_000).astype(np.uint8)
    big_rx = big_tx.copy()
    pos = rng.choice(big_tx.size, 1000, replace=False)
    big_rx[pos] ^= rng.integers(1, 256, 1000).astype(np.uint8)
    t0 = _time.time()
    nb, rbit, ib = biterr(big_tx, big_rx)
    ns, rsym, isym = symerr(big_tx, big_rx)
    er = ErrorRate(receive_delay=3, computation_delay=5)
    for s in range(0, big_tx.size, 100_000):
        y = er(big_tx[s:s + 100_000].astype(float), np.concatenate([np.zeros(3), big_tx[:-3].astype(float)])[s:s + 100_000])
    rr = error_rate(big_tx, big_rx, bits=True)
    dt = _time.time() - t0
    # 1000/1e6 與 nb/8e6 都是同一個有理數的正確捨入 → 精確相等
    check(ns == 1000 and rsym == 1e-3 and nb == rr["errors"] and rbit == nb / 8e6 and rr["k"] == 8 and y[2] == 1_000_000 - 8
          and y[1] == 0 and int(np.count_nonzero(ib)) == 1000 and dt < 3.0,
          f"1e6 個 uint8 符號：biterr {nb:g} 位元錯（{rbit:.3e}）、symerr 1000 錯、comm.ErrorRate RD 3＋CD 5 分 10 訊框比了 {y[2]:g} 個、"
          f"error_rate 位元模式；共 {dt:.2f}s")
