#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生「突波抑制」測試用的樣本（samples/glitch/）：FPGA dump 常見的單點／短暫跳到 0 或滿刻度的錯誤值。
    python3 tools/make_glitch_samples.py            → 寫 samples/glitch/adc_sine_glitch.txt、bus_dump_glitch.txt、README.txt
突波的位置與長度列在 README.txt 與各檔案檔頭的註解，signal_viewer.py --selftest 也用同一組資料驗證 despike 真的修掉它們。"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# (起點樣本索引, 長度, 錯誤值)：單點與 2 點的用預設 k=2 就會修；3 點的比 k 長，k=2 時整段不動（不會修一半），k 改成 3 才會修
ADC_GLITCHES = [(300, 1, 0), (650, 1, 1023), (1000, 2, 0), (1400, 2, 1023), (1700, 3, 0)]
BUS_GLITCHES = [(83, 1, 0x8000), (210, 1, 0x0000), (337, 2, 0xFFFF)]      # (樣本索引, 長度, 錯誤值)；匯流排每 8 個樣本換一次值


def adc_sine(n: int = 2000, bits: int = 10, cycles: float = 6.0, noise: float = 1.5, seed: int = 1):
    """10-bit ADC 取樣的正弦波（offset binary 0..1023）＋一點雜訊；回傳 (乾淨值, 加了突波的值, 突波 mask)。"""
    rng = np.random.default_rng(seed)
    full = 2 ** bits - 1
    t = np.arange(n)
    clean = np.round((full / 2) + (full / 2 - 40) * np.sin(2 * np.pi * cycles * t / n) + rng.normal(0, noise, n))
    clean = np.clip(clean, 0, full)
    bad = clean.copy()
    mask = np.zeros(n, dtype=bool)
    for s, L, v in ADC_GLITCHES:
        bad[s:s + L] = v
        mask[s:s + L] = True
    return clean, bad, mask


def bus_dump(n: int = 400, hold: int = 8, seed: int = 2):
    """16-bit 匯流排 dump：每 hold 個樣本換一個值（遞增計數加一點跳動）；回傳 (乾淨值, 加了突波的值, mask)。"""
    rng = np.random.default_rng(seed)
    vals = (0x0100 + np.cumsum(rng.integers(1, 5, size=n // hold + 1)) * 0x10) & 0xFFFF
    clean = np.repeat(vals, hold)[:n].astype(float)
    bad = clean.copy()
    mask = np.zeros(n, dtype=bool)
    for s, L, v in BUS_GLITCHES:
        bad[s:s + L] = v
        mask[s:s + L] = True
    return clean, bad, mask


def write_all(out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    clean, bad, mask = adc_sine()
    with open(os.path.join(out_dir, "adc_sine_glitch.txt"), "w", encoding="utf-8") as f:
        f.write("# 10-bit ADC sine (0..1023) with FPGA-dump glitches; 突波抑制 test\n")
        f.write("# glitches (sample index, length, value): " + ", ".join(f"{s},{L},{v}" for s, L, v in ADC_GLITCHES) + "\n")
        f.write("# default k=2 fixes the 1- and 2-sample glitches and leaves the 3-sample one at 1700 untouched; set k=3 to fix it too\n")
        f.write("\n".join(str(int(v)) for v in bad) + "\n")
    with open(os.path.join(out_dir, "adc_sine_clean.txt"), "w", encoding="utf-8") as f:
        f.write("# same sine without glitches (compare: put both in one panel and enable 標示差異區間)\n")
        f.write("\n".join(str(int(v)) for v in clean) + "\n")
    clean_b, bad_b, mask_b = bus_dump()
    with open(os.path.join(out_dir, "bus_dump_glitch.txt"), "w", encoding="utf-8") as f:
        f.write("# 16-bit bus dump (HEX), value held 8 samples; single/2-sample glitches at " +
                ", ".join(f"{s} (len {L}, {v:04X})" for s, L, v in BUS_GLITCHES) + "\n")
        f.write("\n".join(f"{int(v):04X}" for v in bad_b) + "\n")
    with open(os.path.join(out_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write("突波抑制（despike）測試訊號\n\n"
                "adc_sine_glitch.txt：10-bit ADC 正弦波（0..1023，2000 點）加入 FPGA dump 常見的突波：\n"
                + "".join(f"  - 樣本 {s} 起連續 {L} 點跳到 {v}\n" for s, L, v in ADC_GLITCHES) +
                "  預設參數（k=2、最小偏差 20、門檻 8σ）會修掉 1 點與 2 點的突波；樣本 1700 的 3 點突波比 k 長，k=2 時整段不動（不會修一半），把 k 改成 3 才會修。\n"
                "adc_sine_clean.txt：同一條沒有突波的正弦波，可以和上面放同一個 panel、勾「標示差異區間」看修正前後的差別。\n"
                "bus_dump_glitch.txt：16-bit 匯流排 dump（HEX，每 8 個樣本換一個值），有單點／2 點的錯誤值；正常的換值邊緣不會被當成突波：\n"
                + "".join(f"  - 樣本 {s} 起 {L} 點變成 {v:04X}\n" for s, L, v in BUS_GLITCHES) +
                "用法：加入訊號 → 訊號分頁「開啟突波抑制」→ 勾「圖上標示修正的點」，被修掉的點會用紅色 × 標出，狀態列顯示修正點數。\n")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "samples", "glitch")
    write_all(out)
    print("written", out)
