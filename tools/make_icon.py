# -*- coding: utf-8 -*-
"""產生 Digital Signal Viewer 的 App 圖示（純 Pillow 畫，不用任何外部圖檔）。

    .venv-build/bin/python tools/make_icon.py          # 寫到 assets/：SignalViewer.png（1024）、.icns（macOS）、.ico（Windows）

設計：深色圓角方塊（MATLAB 深色主題的 #212121 底、#121212 繪圖區），上面一條藍色（#268cdd，MATLAB 深色主題色序第一色）
的數位步階波形、後面一對橘／綠（#f57729／#49db40）的 I/Q 弦波，格線用 MATLAB 的 GridColor 白 25%。
先在 4 倍大小畫再縮小（LANCZOS），線條才平滑。.icns 用 macOS 內建的 iconutil 轉，沒有就只出 PNG／ICO。
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets")
BG, PLOT, GRID = (0x21, 0x21, 0x21), (0x12, 0x12, 0x12), (255, 255, 255, 64)
BLUE, ORANGE, GREEN = (0x26, 0x8c, 0xdd), (0xf5, 0x77, 0x29), (0x49, 0xdb, 0x40)


def _rounded(draw: ImageDraw.ImageDraw, box, r, fill, outline=None, width=0):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def render(size: int = 1024, ss: int = 4) -> Image.Image:
    S = size * ss
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = int(S * 0.08)                       # macOS 圖示四周留白
    r = int(S * 0.20)
    # 陰影 → 底板
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((m, m + S * 0.015, S - m, S - m + S * 0.015), radius=r, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(S * 0.012))
    img.alpha_composite(shadow)
    _rounded(d, (m, m, S - m, S - m), r, fill=BG + (255,))
    # 繪圖區（像 MATLAB 深色主題的 axes）
    px0, py0, px1, py1 = int(S * 0.19), int(S * 0.24), int(S * 0.86), int(S * 0.78)
    _rounded(d, (px0, py0, px1, py1), int(S * 0.02), fill=PLOT + (255,), outline=(0x7d, 0x7d, 0x7d, 255), width=max(1, S // 400))
    lw_grid = max(1, S // 500)
    for k in range(1, 5):                                           # 格線
        x = px0 + (px1 - px0) * k / 5
        d.line([(x, py0), (x, py1)], fill=GRID, width=lw_grid)
    for k in range(1, 3):
        y = py0 + (py1 - py0) * k / 3
        d.line([(px0, y), (px1, y)], fill=GRID, width=lw_grid)
    # 左側 y 軸刻度與下方 x 軸刻度（細、淡）
    tick = (0xa6, 0xa6, 0xa6, 255)
    for k in range(4):
        y = py0 + (py1 - py0) * k / 3
        d.line([(px0 - S * 0.02, y), (px0, y)], fill=tick, width=lw_grid * 2)
    for k in range(6):
        x = px0 + (px1 - px0) * k / 5
        d.line([(x, py1), (x, py1 + S * 0.02)], fill=tick, width=lw_grid * 2)
    # I/Q 弦波（後景，細一點、半透明）
    n = 400
    mid = (py0 + py1) / 2
    amp = (py1 - py0) * 0.27
    for color, phase in ((ORANGE, 0.0), (GREEN, math.pi / 2)):
        pts = []
        for i in range(n + 1):
            t = i / n
            x = px0 + (px1 - px0) * t
            y = mid + amp * math.sin(2 * math.pi * 2.0 * t + phase)
            pts.append((x, y))
        d.line(pts, fill=color + (170,), width=max(2, int(S * 0.010)), joint="curve")
    # 數位步階波形（前景，MATLAB 藍，粗、圓角）
    hi, lo = py0 + (py1 - py0) * 0.30, py0 + (py1 - py0) * 0.70
    bits = [0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0]
    segw = (px1 - px0) / len(bits)
    pts = []
    for i, b in enumerate(bits):
        y = hi if b else lo
        x0 = px0 + segw * i
        if pts and pts[-1][1] != y:
            pts.append((x0, pts[-1][1]))
            pts.append((x0, y))
        elif not pts:
            pts.append((x0, y))
        pts.append((x0 + segw, y))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(pts, fill=BLUE + (120,), width=int(S * 0.040), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(S * 0.008))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    d.line(pts, fill=BLUE + (255,), width=int(S * 0.022), joint="curve")
    # 一個資料提示小點（像 MATLAB 釘住的資料點）
    cx, cy = pts[6]
    rr = int(S * 0.018)
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(0xd9, 0xd9, 0xd9, 255), outline=BLUE + (255,), width=max(2, S // 300))
    return img.resize((size, size), Image.LANCZOS)


def write_all(out: str = OUT) -> dict:
    os.makedirs(out, exist_ok=True)
    big = render(1024)
    paths = {}
    png = os.path.join(out, "SignalViewer.png")
    big.save(png)
    paths["png"] = png
    small = os.path.join(out, "SignalViewer-256.png")
    big.resize((256, 256), Image.LANCZOS).save(small)
    paths["png256"] = small
    ico = os.path.join(out, "SignalViewer.ico")
    big.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    paths["ico"] = ico
    if shutil.which("iconutil"):
        tmp = tempfile.mkdtemp(prefix="dsv_icon_")
        iconset = os.path.join(tmp, "SignalViewer.iconset")
        os.makedirs(iconset)
        for pt in (16, 32, 128, 256, 512):
            big.resize((pt, pt), Image.LANCZOS).save(os.path.join(iconset, f"icon_{pt}x{pt}.png"))
            big.resize((pt * 2, pt * 2), Image.LANCZOS).save(os.path.join(iconset, f"icon_{pt}x{pt}@2x.png"))
        icns = os.path.join(out, "SignalViewer.icns")
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", icns], check=True)
        shutil.rmtree(tmp, ignore_errors=True)
        paths["icns"] = icns
    return paths


if __name__ == "__main__":
    for k, p in write_all().items():
        print(f"{k:6s} {p} ({os.path.getsize(p)} bytes)")
    sys.exit(0)
