# -*- coding: utf-8 -*-
"""plotkit 範例：像 pyplot 一樣畫圖，視窗裡有全部互動功能。

執行：python examples/plotkit_demo.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import plotkit as pk  # noqa: E402

t = np.linspace(0.0, 1e-3, 2001)
w = pk.figure(title="GFSK 示範", style="matlab")
w.plot(t * 1e6, np.sin(2 * np.pi * 5e3 * t), label="I")
w.plot(t * 1e6, np.cos(2 * np.pi * 5e3 * t), label="Q", ls="--")
w.step(np.arange(0, 1000, 50.0), (np.arange(20) % 2).astype(float), label="clk", yaxis="right", color="#3baa32")
w.xlabel("t [us]")
w.ylabel("amplitude")
w.ylabel("level", side="right")
w.xline(250, "sync")
w.text(600, 0.8, "注意這裡", color="#dd5400")
w.grid(True)
w.legend(True, "upper right")

import tempfile  # noqa: E402

path = os.path.join(tempfile.gettempdir(), "plotkit_demo.json")
w.save_json(path)                      # 存成 JSON（資料、樣式、標註、資料提示、視圖範圍）
print("已存到", path)
w2 = pk.open_json(path)                # 重開一份，改成 default 風格
w2.set_style("default")

pk.show()   # 進入事件迴圈：滾輪縮放、拖曳平移、雙擊空白還原、「資料提示」按鈕、右鍵選單、Ctrl+Z/Y、Ctrl+C/V 跨視窗
