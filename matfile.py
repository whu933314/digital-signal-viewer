# -*- coding: utf-8 -*-
"""讀 MATLAB .mat 檔（Level 5 格式：MATLAB -v6／-v7，含 -v7 的 zlib 壓縮），只用標準函式庫＋numpy，不需要 scipy。

    from matfile import read_mat, MatTable
    d = read_mat("x.mat")          # {變數名: ndarray | str | dict(struct) | list(cell) | None(不支援的型別)}
    t = MatTable("x.mat")          # 跟 signal_viewer.CsvTable 一樣的介面：names / data_columns() / values_fmt() / time_values() / estimate_rate() / start_time()

支援：double／single／int8…uint64／logical（→ float64）、複數（拆成 real(x)、imag(x) 兩欄）、1-D 與 2-D 陣列（2-D 拆成 x(:,1)、x(:,2)…）、
struct（遞迴，欄名 s.field）、cell（c{1}、c{2}…）、char（略過，不是訊號）、大小端。
不支援：-v7.3（HDF5）→ 丟 MatError 提示用 save(...,'-v7') 另存；sparse／物件／函式控制代碼 → 略過。
格式依 MathWorks《MAT-File Format》Level 5：128 位元組標頭（116 文字、8 subsys、2 版本、2 位元組序 'IM'），之後是資料元素（8 位元組 tag＝型別＋長度，
長度 ≤ 4 時用「小資料元素」把長度放在 tag 高 16 位元、資料放在同一個 8 位元組裡），每個元素補到 8 位元組邊界；miMATRIX 裡依序是 flags、dims、name、資料。
"""
from __future__ import annotations

import os
import struct
import zlib
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# 資料型別（mi*）
miINT8, miUINT8, miINT16, miUINT16, miINT32, miUINT32, miSINGLE, miDOUBLE = 1, 2, 3, 4, 5, 6, 7, 9
miINT64, miUINT64, miMATRIX, miCOMPRESSED, miUTF8, miUTF16, miUTF32 = 12, 13, 14, 15, 16, 17, 18
_DTYPES = {miINT8: "i1", miUINT8: "u1", miINT16: "i2", miUINT16: "u2", miINT32: "i4", miUINT32: "u4",
           miSINGLE: "f4", miDOUBLE: "f8", miINT64: "i8", miUINT64: "u8", miUTF8: "u1", miUTF16: "u2", miUTF32: "u4"}
# 陣列類別（mx*）
mxCELL, mxSTRUCT, mxOBJECT, mxCHAR, mxSPARSE = 1, 2, 3, 4, 5
mxDOUBLE, mxSINGLE, mxINT8, mxUINT8, mxINT16, mxUINT16, mxINT32, mxUINT32, mxINT64, mxUINT64 = 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
_NUMERIC = {mxDOUBLE, mxSINGLE, mxINT8, mxUINT8, mxINT16, mxUINT16, mxINT32, mxUINT32, mxINT64, mxUINT64}
FLAG_COMPLEX, FLAG_GLOBAL, FLAG_LOGICAL = 0x0800, 0x0400, 0x0200
MAX_SPLIT_COLUMNS = 64          # 2-D 陣列最多拆成這麼多欄（再多就只取前 64 欄）


class MatError(ValueError):
    pass


def _pad8(n: int) -> int:
    return (n + 7) & ~7


class _Reader:
    """一段 bytes 裡的資料元素讀取器。"""

    def __init__(self, buf: bytes, E: str):
        self.buf = buf
        self.E = E               # "<" 或 ">"
        self.pos = 0

    def at_end(self) -> bool:
        return self.pos + 8 > len(self.buf)

    def element(self) -> Tuple[int, bytes]:
        """讀下一個資料元素，回 (mi 型別, 原始資料 bytes)。"""
        buf, p = self.buf, self.pos
        (mtype,) = struct.unpack(self.E + "I", buf[p:p + 4])
        if mtype >> 16:                                  # 小資料元素：高 16 位元是長度、資料就在接下來的 4 位元組
            nbytes, mtype = mtype >> 16, mtype & 0xFFFF
            data = buf[p + 4:p + 4 + nbytes]
            self.pos = p + 8
        else:
            (nbytes,) = struct.unpack(self.E + "I", buf[p + 4:p + 8])
            data = buf[p + 8:p + 8 + nbytes]
            # miCOMPRESSED 元素是例外：MATLAB 把壓縮後的資料接著寫、不補到 8 位元組邊界（scipy 也這樣讀）
            self.pos = p + 8 + (nbytes if mtype == miCOMPRESSED else _pad8(nbytes))
        return mtype, data


def _as_array(mtype: int, data: bytes, E: str) -> np.ndarray:
    dt = _DTYPES.get(mtype)
    if dt is None:
        raise MatError(f"不支援的資料型別 mi{mtype}")
    return np.frombuffer(data, dtype=np.dtype(E + dt) if dt[0] in "iuf" and dt[1:] != "1" else np.dtype(dt))


def _decode_chars(mtype: int, data: bytes, E: str) -> str:
    if mtype == miUTF8:
        return data.decode("utf-8", "replace")
    if mtype in (miUINT16, miUTF16):
        return data.decode("utf-16-le" if E == "<" else "utf-16-be", "replace")
    if mtype == miUTF32:
        return data.decode("utf-32-le" if E == "<" else "utf-32-be", "replace")
    return bytes(_as_array(mtype, data, E).astype("u1")).decode("latin-1", "replace")


def _parse_matrix(buf: bytes, E: str) -> Tuple[str, Any]:
    """解一個 miMATRIX 的內容，回 (變數名, 值)。值：ndarray（數值／logical；複數為 complex128）、str、dict、list 或 None（不支援）。"""
    r = _Reader(buf, E)
    mt, fl = r.element()
    flags = _as_array(mt, fl, E).astype("u4")
    cls, fbits = int(flags[0] & 0xFF), int(flags[0] & 0xFF00)
    mt, dd = r.element()
    dims = [int(x) for x in _as_array(mt, dd, E)]
    mt, nm = r.element()
    name = bytes(nm).decode("utf-8", "replace").strip("\x00") if nm else ""
    n = int(np.prod(dims)) if dims else 0
    if cls in _NUMERIC:
        mt, re_ = r.element()
        real = _as_array(mt, re_, E)
        if fbits & FLAG_COMPLEX and not r.at_end():
            mt, im_ = r.element()
            imag = _as_array(mt, im_, E)
            val = real.astype("f8") + 1j * imag.astype("f8")
        elif fbits & FLAG_LOGICAL:
            val = (real != 0).astype("f8")
        else:
            val = real.astype("f8") if real.dtype.kind in "iub" and real.dtype.itemsize < 8 else real
        try:
            val = val.reshape(dims, order="F") if n == val.size else val
        except Exception:
            pass
        return name, val
    if cls == mxCHAR:
        mt, ch = r.element()
        s = _decode_chars(mt, ch, E)
        if len(dims) == 2 and dims[0] > 1 and dims[1] > 0 and len(s) == n:   # 多列字元陣列是 column-major
            s = "\n".join("".join(s[c * dims[0] + rr] for c in range(dims[1])) for rr in range(dims[0]))
        return name, s
    if cls == mxSTRUCT:
        mt, fl_ = r.element()
        (flen,) = _as_array(mt, fl_, E).astype("i4")[:1] if fl_ else (32,)
        mt, fn = r.element()
        nf = len(fn) // int(flen) if flen else 0
        fields = [bytes(fn[i * flen:(i + 1) * flen]).decode("utf-8", "replace").strip("\x00") for i in range(nf)]
        items: List[Dict[str, Any]] = []
        for _ in range(max(1, n)):
            d: Dict[str, Any] = {}
            for f in fields:
                if r.at_end():
                    break
                mt, sub = r.element()
                d[f] = _parse_matrix(sub, E)[1] if mt == miMATRIX and sub else None
            items.append(d)
        return name, items[0] if n == 1 else items
    if cls == mxCELL:
        cells: List[Any] = []
        for _ in range(n):
            if r.at_end():
                break
            mt, sub = r.element()
            cells.append(_parse_matrix(sub, E)[1] if mt == miMATRIX and sub else None)
        return name, cells
    return name, None                                    # sparse／object／function handle：略過


def read_mat(path: str) -> Dict[str, Any]:
    """讀整個 .mat，回 {變數名: 值}。-v7.3 或不是 .mat 會丟 MatError。"""
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 128:
        raise MatError("不是 MATLAB .mat 檔（檔案太短）")
    head = data[:116]
    if b"MATLAB 7.3" in head or data[124:126] in (b"\x00\x02", b"\x02\x00"):
        raise MatError("這是 MATLAB -v7.3（HDF5）格式，還不支援；請在 MATLAB 用 save(filename, ..., '-v7') 另存")
    endian = data[126:128]
    if endian == b"IM":
        E = "<"
    elif endian == b"MI":
        E = ">"
    else:
        raise MatError("不是 MATLAB Level 5 .mat 檔（可能是很舊的 -v4 格式）")
    out: Dict[str, Any] = {}
    r = _Reader(data, E)
    r.pos = 128
    while not r.at_end():
        mtype, payload = r.element()
        if mtype == miCOMPRESSED:
            try:
                payload = zlib.decompress(payload)
            except zlib.error as e:
                raise MatError(f"解壓縮失敗：{e}")
            sub = _Reader(payload, E)
            mtype, payload = sub.element()
        if mtype == miMATRIX and payload:
            name, val = _parse_matrix(payload, E)
            if name:
                out[name] = val
    return out


def flatten_signals(variables: Dict[str, Any]) -> List[Tuple[str, np.ndarray]]:
    """把變數攤平成 (欄名, 1-D float64) 的清單：複數拆 real()/imag()、2-D 拆 x(:,k)、struct 遞迴 s.f、cell c{k}；字串與不支援的略過。"""
    out: List[Tuple[str, np.ndarray]] = []

    def add(name: str, v: Any) -> None:
        if isinstance(v, dict):
            for k, sub in v.items():
                add(f"{name}.{k}", sub)
            return
        if isinstance(v, list):
            if v and all(isinstance(x, dict) for x in v):          # struct 陣列
                for i, sub in enumerate(v, 1):
                    add(f"{name}({i})", sub)
            else:
                for i, sub in enumerate(v, 1):
                    add(f"{name}{{{i}}}", sub)
            return
        if not isinstance(v, np.ndarray) or v.size == 0:
            return
        if np.iscomplexobj(v):
            add(f"real({name})", np.ascontiguousarray(v.real))
            add(f"imag({name})", np.ascontiguousarray(v.imag))
            return
        a = np.asarray(v, dtype="f8")
        if a.ndim <= 1 or a.size == max(a.shape):                   # 向量（含 1×N、N×1）
            out.append((name, a.reshape(-1)))
            return
        if a.ndim == 2:
            if a.shape[1] <= MAX_SPLIT_COLUMNS or a.shape[1] <= a.shape[0]:
                for k in range(min(a.shape[1], MAX_SPLIT_COLUMNS)):
                    out.append((f"{name}(:,{k + 1})", np.ascontiguousarray(a[:, k])))
            else:
                for k in range(min(a.shape[0], MAX_SPLIT_COLUMNS)):
                    out.append((f"{name}({k + 1},:)", np.ascontiguousarray(a[k, :])))
            return
        out.append((name, a.reshape(-1, order="F")))             # 3-D 以上：攤平
    for k, v in variables.items():
        add(k, v)
    return out


_TIME_NAMES = ("t", "time", "timestamp", "times", "tt", "t_s", "time_s")


class MatTable:
    """一個 .mat 檔當成「表格」：和 CsvTable 一樣的介面，讓 DSV 的資料夾樹、匯入對話框、Signal 讀取共用同一條路。
    時間欄：名叫 t／time／timestamp…（或 struct 裡的 .t／.time）且單調遞增的向量，單位視為秒。"""

    def __init__(self, path: str):
        self.path = path
        self.has_header = True
        self.delimiter = None
        self.rows: List[List[str]] = []
        cols = flatten_signals(read_mat(path))
        self.names: List[str] = [n for n, _ in cols]
        self._cols: Dict[str, np.ndarray] = {n: a for n, a in cols}
        self.time_col: Optional[int] = self._detect_time_col()

    def _detect_time_col(self) -> Optional[int]:
        for i, n in enumerate(self.names):
            leaf = n.split(".")[-1].split("(")[0].split("{")[0].strip().lower()
            if leaf in _TIME_NAMES or leaf.startswith("time"):
                a = self._cols[n]
                if len(a) >= 2 and np.all(np.diff(a) > 0):
                    return i
        return None

    @property
    def nrows(self) -> int:
        return max((len(a) for a in self._cols.values()), default=0)

    def data_columns(self) -> List[str]:
        return [n for i, n in enumerate(self.names) if i != self.time_col]

    def col_index(self, name: str) -> int:
        if name in self.names:
            return self.names.index(name)
        low = [n.lower() for n in self.names]
        if name.lower() in low:
            return low.index(name.lower())
        raise KeyError(f"MAT 檔沒有變數 {name!r}")

    def values_fmt(self, name: str, fmt: str = "AUTO") -> Tuple[np.ndarray, str]:
        return self._cols[self.names[self.col_index(name)]], "DEC"    # .mat 的值已經是數字，讀取格式不適用

    def values(self, name: str, fmt: str = "AUTO") -> np.ndarray:
        return self.values_fmt(name, fmt)[0]

    def time_values(self) -> Optional[np.ndarray]:
        if self.time_col is None:
            return None
        return self._cols[self.names[self.time_col]]

    def estimate_rate(self) -> Optional[float]:
        t = self.time_values()
        if t is None or len(t) < 2:
            return None
        fin = t[np.isfinite(t)]
        if len(fin) < 2 or fin[-1] <= fin[0]:
            return None
        return (len(fin) - 1) / float(fin[-1] - fin[0])

    def start_time(self) -> Optional[float]:
        t = self.time_values()
        if t is None or len(t) == 0 or not np.isfinite(t[0]):
            return None
        return float(t[0])


def mat_header(path: str) -> Tuple[List[str], Optional[int]]:
    """(欄名清單, 時間欄索引)——資料夾樹展開用。.mat 沒有「只讀標頭」這回事，整檔讀一次（有快取在 signal_viewer）。"""
    t = MatTable(path)
    return list(t.names), t.time_col


def is_mat_file(name: str) -> bool:
    return name.lower().endswith(".mat")


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        try:
            tb = MatTable(p)
            print(f"{os.path.basename(p)}: {len(tb.names)} columns, time_col={tb.time_col}, rate={tb.estimate_rate()}")
            for n in tb.names:
                a = tb.values(n)
                print(f"  {n}: n={len(a)} min={a.min():.6g} max={a.max():.6g}")
        except MatError as e:
            print(f"{os.path.basename(p)}: {e}")
