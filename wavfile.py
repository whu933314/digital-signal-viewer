# -*- coding: utf-8 -*-
"""WAV（RIFF PCM／IEEE float）與 NumPy .npy／.npz 當成「表格」：和 CsvTable／matfile.MatTable 同介面，
讓資料夾樹、匯入對話框、直接加入、拖放都走同一條路。純 numpy，不需要 scipy。

- WAV：每個聲道一欄（ch1、ch2…；單聲道就 ch1），取樣率＝檔頭的 sampleRate（estimate_rate 回傳 Hz → SPS）；
  PCM 8（無號）／16／24／32 位元與 IEEE float 32／64；WAVE_FORMAT_EXTENSIBLE 看子格式。值保持原始整數（不正規化），像 FPGA 擷取檔。
- .npy：1-D → 一欄「a」；2-D → 每欄一欄（col1…，若 shape[0] < shape[1] 當成每列一個訊號）；.npz：每個陣列一欄（多維依同樣規則展開成 名稱.col1…）。
  dtype 複數拆成 real()/imag()，像 .mat。
"""
from __future__ import annotations

import os
import struct
from typing import Dict, List, Optional, Tuple

import numpy as np

WAV_EXTS = (".wav", ".wave")
NPY_EXTS = (".npy", ".npz")


class WavError(ValueError):
    pass


def read_wav(path: str) -> Tuple[float, Dict[str, np.ndarray]]:
    """回傳 (取樣率 Hz, {"ch1": array, ...})。"""
    with open(path, "rb") as f:
        head = f.read(12)
        if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            raise WavError("不是 RIFF/WAVE 檔")
        fmt = None
        data = None
        while True:
            h = f.read(8)
            if len(h) < 8:
                break
            cid, size = h[:4], struct.unpack("<I", h[4:])[0]
            if cid == b"fmt ":
                body = f.read(size)
                if len(body) < 16:
                    raise WavError("fmt 區塊不完整")
                tag, nch, rate, _brate, _align, bits = struct.unpack("<HHIIHH", body[:16])
                if tag == 0xFFFE and len(body) >= 26:          # WAVE_FORMAT_EXTENSIBLE：子格式 GUID 的前 2 bytes
                    tag = struct.unpack("<H", body[24:26])[0]
                fmt = (tag, nch, rate, bits)
            elif cid == b"data":
                data = f.read(size)
            else:
                f.seek(size, os.SEEK_CUR)
            if size % 2:                                       # RIFF 區塊以 2 bytes 對齊
                f.seek(1, os.SEEK_CUR)
            if fmt is not None and data is not None:
                break
    if fmt is None or data is None:
        raise WavError("缺 fmt 或 data 區塊")
    tag, nch, rate, bits = fmt
    if nch < 1:
        raise WavError("聲道數為 0")
    if tag == 1:                                                # PCM
        if bits == 8:
            a = np.frombuffer(data, dtype=np.uint8).astype(np.float64)
        elif bits == 16:
            a = np.frombuffer(data, dtype="<i2").astype(np.float64)
        elif bits == 24:
            raw = np.frombuffer(data, dtype=np.uint8)
            raw = raw[: len(raw) - len(raw) % 3].reshape(-1, 3).astype(np.int32)
            v = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
            a = np.where(v & 0x800000, v - 0x1000000, v).astype(np.float64)
        elif bits == 32:
            a = np.frombuffer(data, dtype="<i4").astype(np.float64)
        else:
            raise WavError(f"不支援的 PCM 位元數 {bits}")
    elif tag == 3:                                              # IEEE float
        if bits == 32:
            a = np.frombuffer(data, dtype="<f4").astype(np.float64)
        elif bits == 64:
            a = np.frombuffer(data, dtype="<f8")
        else:
            raise WavError(f"不支援的 float 位元數 {bits}")
    else:
        raise WavError(f"不支援的 WAV 格式代碼 {tag}（只支援 PCM 與 IEEE float）")
    a = a[: len(a) - len(a) % nch].reshape(-1, nch)
    cols = {f"ch{i + 1}": np.ascontiguousarray(a[:, i]) for i in range(nch)}
    return float(rate), cols


def _expand(name: str, arr) -> List[Tuple[str, np.ndarray]]:
    a = np.asarray(arr)
    out: List[Tuple[str, np.ndarray]] = []
    if np.iscomplexobj(a):
        out += _expand(f"real({name})", a.real)
        out += _expand(f"imag({name})", a.imag)
        return out
    if a.dtype.kind not in "biuf":
        return out
    a = a.astype(np.float64)
    if a.ndim == 0:
        return [(name, a.reshape(1))]
    if a.ndim == 1:
        return [(name, a)]
    if a.ndim == 2:
        if a.shape[0] < a.shape[1]:                             # 列比欄少：每列一個訊號
            a = a.T
        return [(f"{name}.col{j + 1}", np.ascontiguousarray(a[:, j])) for j in range(a.shape[1])]
    return [(name, a.reshape(-1))]


def read_npy(path: str) -> Dict[str, np.ndarray]:
    cols: Dict[str, np.ndarray] = {}
    if path.lower().endswith(".npz"):
        with np.load(path, allow_pickle=False) as z:
            for k in z.files:
                for n, a in _expand(k, z[k]):
                    cols[n] = a
    else:
        base = os.path.splitext(os.path.basename(path))[0]
        for n, a in _expand(base, np.load(path, allow_pickle=False)):
            cols[n] = a
    if not cols:
        raise WavError("沒有數值陣列")
    return cols


class WavTable:
    """WAV／.npy／.npz 的表格介面（同 CsvTable／MatTable）：names、time_col（永遠 None）、values、estimate_rate（WAV＝取樣率）。"""

    def __init__(self, path: str):
        self.path = path
        self.has_header = True
        self.delimiter = None
        self.rows: List[List[str]] = []
        self.time_col: Optional[int] = None
        self._rate: Optional[float] = None
        if path.lower().endswith(WAV_EXTS):
            self._rate, self._cols = read_wav(path)
        else:
            self._cols = read_npy(path)
        self.names: List[str] = list(self._cols.keys())

    @property
    def nrows(self) -> int:
        return max((len(a) for a in self._cols.values()), default=0)

    def data_columns(self) -> List[str]:
        return list(self.names)

    def col_index(self, name: str) -> int:
        if name in self.names:
            return self.names.index(name)
        low = [n.lower() for n in self.names]
        if name.lower() in low:
            return low.index(name.lower())
        raise KeyError(f"檔案沒有欄位 {name!r}")

    def values_fmt(self, name: str, fmt: str = "AUTO") -> Tuple[np.ndarray, str]:
        return self._cols[self.names[self.col_index(name)]], "DEC"

    def values(self, name: str, fmt: str = "AUTO") -> np.ndarray:
        return self.values_fmt(name, fmt)[0]

    def time_values(self) -> Optional[np.ndarray]:
        return None

    def estimate_rate(self) -> Optional[float]:
        return self._rate

    def start_time(self) -> Optional[float]:
        return None


def is_wav_file(name: str) -> bool:
    return name.lower().endswith(WAV_EXTS)


def is_npy_file(name: str) -> bool:
    return name.lower().endswith(NPY_EXTS)


def selftest(check) -> None:
    """signal_viewer.py --selftest 呼叫：寫幾個小 WAV／npy 再讀回來。"""
    import tempfile
    import wave
    d = tempfile.mkdtemp(prefix="dsv_wav_")
    # 16-bit 立體聲（標準 wave 模組寫）
    p16 = os.path.join(d, "s16.wav")
    with wave.open(p16, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(48000)
        frames = np.column_stack([np.arange(100, dtype="<i2") * 10, -np.arange(100, dtype="<i2")]).astype("<i2")
        wf.writeframes(frames.tobytes())
    t = WavTable(p16)
    check(t.names == ["ch1", "ch2"] and t.estimate_rate() == 48000.0 and t.nrows == 100 and t.values("ch1")[5] == 50.0 and t.values("ch2")[7] == -7.0
          and t.time_col is None and t.data_columns() == ["ch1", "ch2"], "WAV 16-bit 立體聲：ch1／ch2、取樣率 48000、值不正規化")
    # 24-bit 與 float32 自己寫 RIFF
    def write_riff(path, tag, bits, nch, rate, payload):
        fmt = struct.pack("<HHIIHH", tag, nch, rate, rate * nch * bits // 8, nch * bits // 8, bits)
        body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(payload)) + payload
        with open(path, "wb") as f:
            f.write(b"RIFF" + struct.pack("<I", len(body)) + body)
    v24 = np.array([0, 1, -1, 8388607, -8388608], dtype=np.int64)
    raw = b"".join(int(x).to_bytes(3, "little", signed=True) for x in v24)
    p24 = os.path.join(d, "s24.wav"); write_riff(p24, 1, 24, 1, 32000, raw)
    t = WavTable(p24)
    check(list(t.values("ch1")) == [0.0, 1.0, -1.0, 8388607.0, -8388608.0] and t.estimate_rate() == 32000.0, "WAV 24-bit：有號值正確")
    pf = os.path.join(d, "f32.wav"); write_riff(pf, 3, 32, 1, 1000, np.array([0.5, -0.25, 1.0], dtype="<f4").tobytes())
    t = WavTable(pf)
    check(np.allclose(t.values("ch1"), [0.5, -0.25, 1.0]), "WAV IEEE float32")
    bad = os.path.join(d, "bad.wav")
    with open(bad, "wb") as f:
        f.write(b"RIFX" + b"\0" * 20)
    try:
        WavTable(bad); ok = False
    except WavError:
        ok = True
    check(ok, "不是 WAV：WavError")
    # npy／npz
    pn = os.path.join(d, "a.npy"); np.save(pn, np.arange(5.0))
    t = WavTable(pn)
    check(t.names == ["a"] and list(t.values("a")) == [0.0, 1.0, 2.0, 3.0, 4.0] and t.estimate_rate() is None, ".npy 1-D → 一欄（檔名）")
    pz = os.path.join(d, "b.npz"); np.savez(pz, m=np.arange(6.0).reshape(3, 2), c=np.array([1 + 2j, 3 - 1j]))
    t = WavTable(pz)
    check(t.names == ["m.col1", "m.col2", "real(c)", "imag(c)"] and list(t.values("m.col2")) == [1.0, 3.0, 5.0] and list(t.values("imag(c)")) == [2.0, -1.0],
          ".npz：2-D 每欄一欄、複數拆 real/imag")
    check(is_wav_file("X.WAV") and is_npy_file("a.npz") and not is_wav_file("a.csv"), "副檔名判斷")
