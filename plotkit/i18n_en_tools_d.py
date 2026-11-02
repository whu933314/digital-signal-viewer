# -*- coding: utf-8 -*-
"""English catalog part: tools_d — batch D of the 2026-10 MATLAB tool-gap work: digital bus display
(Logic Analyzer DisplayChannelFormat / DisplayChannelRadix; dsv_bus.py, plotkit/bus.py).
Keys are the Traditional Chinese source strings, byte for byte.
"""
CATALOG = {
    "數位顯示（Logic Analyzer）": "Digital Display (Logic Analyzer)",
    "格式": "Format",
    "顯示格式": "Display Format",
    "自動": "Auto",
    "類比": "Analog",
    "數位": "Digital",
    "進位制": "Radix",
    "十六進位（Hex）": "Hexadecimal",
    "二進位（Binary）": "Binary",
    "八進位（Octal）": "Octal",
    "有號十進位（Signed decimal）": "Signed decimal",
    "無號十進位（Unsigned decimal）": "Unsigned decimal",
    "位元寬度": "Bit Width",
    "位元寬度…": "Bit Width…",
    "位元寬度（1～64；0 或空白＝自動）：": "Bit width (1–64; 0 or empty = auto):",
    "位元寬度要是 0～64 的整數（0 或空白＝自動）": "Bit width must be an integer 0–64 (0 or empty = auto)",
    "位元寬度：{b}（{n} 條）": "Bit width: {b} ({n} signals)",
    "顯示格式：{fmt}（{n} 條；畫成匯流排的 {b} 條）": "Display format: {fmt} ({n} signals; {b} drawn as a bus)",
    "進位制：{radix}（{n} 條）": "Radix: {radix} ({n} signals)",
    "{what}（{n} 條）": "{what} ({n} signals)",
    "匯流排": "a bus",
    "線": "a line",
    "目前畫成{what}": "currently drawn as {what}",
    "自動 {n} 位元；目前畫成{what}": "auto {n} bits; currently drawn as {what}",
    "套用": "Apply",
    "類比＝階梯線（預設）；數位＝值不變的區段畫成六角框＋數值（只有 0／1 的訊號仍畫邏輯準位線）":
        "Analog = stair-step line (default); Digital = each run of constant value drawn as a hexagon box with its value (0/1-only signals stay logic-level lines)",
    "匯流排文字、十字游標、資料提示、量測與游標讀數都用這個進位制；自動＝讀數照舊（十進位）":
        "Used for bus values, crosshair, data tips, measurements and cursor readouts; Auto = readouts stay decimal",
    "空白或 0＝自動（HEX 字數 × 4 或數值範圍）；決定補零位數與有號值的二補數":
        "Empty or 0 = auto (HEX digits × 4 or the value range); sets zero padding and two's complement for signed values",
}
