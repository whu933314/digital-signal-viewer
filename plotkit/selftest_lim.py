# -*- coding: utf-8 -*-
"""plotkit.selftest_lim — 限制修正批次的 Agg 檢查（由 plotkit.selftest 呼叫）：
Series.disp="digital"（DSV 數位匯流排貼到圖片視窗）畫成六角框＋數值、JSON／undo 快照保留、點選框內命中。"""
from __future__ import annotations

import json

import numpy as np
from matplotlib.backend_bases import MouseEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def run(check) -> None:
    from . import draw, model
    from .model import FigureState, Series
    y = np.repeat([1.0, 5.0, 171.0, 3.0], 10)
    x = np.arange(41) * 0.5                                  # step：N+1 個 x
    sb = Series("bus", x, y, kind="step", uid=1, disp="digital", radix="hex", bits=8)
    sa = Series("ana", x[:-1], np.sin(np.arange(40.0)) * 50 + 80, uid=2)
    check(sb.is_bus and not sa.is_bus and Series("z", [0, 1], [0, 1], disp="bogus", radix="zz", bits="x").disp == "analog"
          and Series("z", [0, 1], [0, 1], radix="zz").radix == "" and Series("z", [0, 1], [0, 1], bits=99).bits == 64,
          "Series：disp／radix／bits 欄位，不認得的值退回預設")
    fig = Figure(figsize=(6, 3), dpi=100)
    FigureCanvasAgg(fig)
    info = draw.draw_state(fig, FigureState(series=[sb]), autoscale=True)
    fig.canvas.draw()
    b = info.bus.get(1)
    check(b is not None and b["center"] == 0.0 and abs(b["half"] - 0.4) < 1e-12
          and [t for _x, t in b["art"].labels()] == ["01", "05", "AB", "03"] and len(info.ax_left.get_yticks()) == 0
          and info.lines[1] is b["art"].top,
          f"draw_state：只有匯流排＝一條一列、框內寫 hex 數值、不畫 y 刻度（{b and b['art'].labels()}）")
    info2 = draw.draw_state(fig, FigureState(series=[sb, sa]), autoscale=True)
    fig.canvas.draw()
    b2 = info2.bus[1]
    check(abs(b2["center"] - 86.0) < 1e-9 and abs(b2["half"] - 85.0) < 1e-9 and len(info2.ax_left.get_yticks()) > 0
          and 2 not in info2.bus and info2.lines[2].get_drawstyle() == "default",
          "和類比線混在一起：框＝自己的值範圍（1..171）、保留 y 刻度；類比線照舊")
    # 點框內（中心上下都算）→ 命中 hit 線
    ax = info2.ax_left
    px, py = ax.transData.transform((7.0, 86.0 + 60.0))
    hit = draw.hit_test_lines([b2["hit"], info2.lines[2]], MouseEvent("button_press_event", fig.canvas, px, py, button=1))
    check(hit is b2["hit"], "點匯流排框內（不在上緣）→ 命中（看不見的 hit 線寬＝框高）")
    sel = draw.draw_state(fig, FigureState(series=[sb]), selected=[1], autoscale=True)
    fig.canvas.draw()
    check(sel.lines[1].get_linewidth() > info.lines[1].get_linewidth() and sel.bus[1]["art"].bottom.get_linewidth() == sel.lines[1].get_linewidth(),
          "選取的匯流排加粗（下緣跟著上緣）")
    st = FigureState(series=[sb, sa])
    st2 = model.state_from_dict(json.loads(json.dumps(model.state_to_dict(st))))
    s2 = st2.series[0]
    check(s2.disp == "digital" and s2.radix == "hex" and s2.bits == 8 and st2.series[1].disp == "analog",
          "JSON 存讀：disp／radix／bits 保留")
    snap = st.snapshot()
    st.series = []
    st.restore(snap)
    old = model.state_to_dict(FigureState(series=[sa]))
    for k in ("disp", "radix", "bits"):
        old["series"][0].pop(k, None)
    check(st.series[0].is_bus and st.series[0].radix == "hex" and model.state_from_dict(old).series[0].disp == "analog"
          and sb.copy(label="c").is_bus,
          "undo 快照／copy 保留匯流排設定；舊圖檔沒有這些欄位＝類比")
    sd = Series("dec", x, y, kind="step", uid=3, disp="digital")
    info3 = draw.draw_state(fig, FigureState(series=[sd]), autoscale=True)
    fig.canvas.draw()
    check([t for _x, t in info3.bus[3]["art"].labels()] == ["1", "5", "171", "3"], "沒選進位制：框內十進位")
