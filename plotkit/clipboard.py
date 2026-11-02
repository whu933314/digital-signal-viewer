# -*- coding: utf-8 -*-
"""plotkit.clipboard — 圖片輸出與複製到系統剪貼簿。

Windows 用 PowerShell（System.Windows.Forms.Clipboard.SetImage）、macOS 用 osascript（只用 Standard Additions，
不會跳自動化授權）、Linux 用 xclip 或 wl-copy。永遠不丟例外，回傳 (ok, 訊息)；失敗時訊息含 PNG 路徑。

兩種內容（跟 MATLAB R2025a 座標區工具列 Export 的「Copy as image」「Copy as vector graphic」一樣）：
image＝PNG（150 dpi；copygraphics 的 Resolution 預設也是 150），vector＝PDF（MATLAB 在 macOS 上 copygraphics
ContentType='vector' 放進剪貼簿的就是 «class PDF »，-batch 後 `clipboard info` 實測）。Windows 沒有 EMF 可產生
（.NET 剪貼簿也沒有 PDF 向量格式）：向量複製的按鈕與選單項目在 Windows 上停用（vector_copy_state／vector_copy_tip），
tooltip 說明改用存檔；程式直接呼叫時回報不支援，不產生暫存 PDF。
"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple

from .i18n import tr

_counter = 0
CLIP_TIMEOUT_S = 20            # PowerShell／osascript／wl-copy 最多等幾秒（超過就結束它、回報失敗；測試可以改短）
_CLIP_RE = re.compile(r"^plotkit_clip_(\d+)_(\d+)\.(png|pdf)$")


def figure_to_png_bytes(fig, dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    return buf.getvalue()


def save_png(fig, path: str, dpi: int = 150) -> str:
    fig.savefig(path, format="png", dpi=dpi, facecolor=fig.get_facecolor())
    return path


def save_pdf(fig, path: str) -> str:
    fig.savefig(path, format="pdf", facecolor=fig.get_facecolor())
    return path


def temp_path(ext: str = "png") -> str:
    global _counter
    _counter += 1
    return os.path.join(tempfile.gettempdir(), f"plotkit_clip_{os.getpid()}_{_counter}.{ext}")


def temp_png_path() -> str:
    return temp_path("png")


def _pid_alive(pid: int, file_mtime: Optional[float] = None) -> bool:
    """這個 pid 的行程還在跑嗎（Windows：OpenProcess＋GetExitCodeProcess；其他：kill(pid, 0)）。不確定時當成還在（不刪它的檔）。
    file_mtime＝那個行程留下的檔的修改時間：Windows 的 pid 會被重複使用——行程在、但它是在檔案寫好之後才建立的（GetProcessTimes 的建立時間比檔案晚），
    就不是留下檔案的那個行程（它已經不在了）→ 回 False（第二輪 Windows 驗證 W14R2-2：以前這種 PNG 被當成還在跑的行程的、關閉時的提醒漏列）。"""
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform.startswith("win"):
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            k32.OpenProcess.restype = wintypes.HANDLE
            k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            h = k32.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ctypes.get_last_error() == 5               # ERROR_ACCESS_DENIED：行程在、只是不給看
            try:
                code = wintypes.DWORD()
                if not k32.GetExitCodeProcess(h, ctypes.byref(code)):
                    return True
                if code.value != 259:                              # STILL_ACTIVE
                    return False
                if file_mtime is not None:
                    created = _win_process_start_time(k32, h)
                    if created is not None and created > float(file_mtime) + 2.0:
                        return False                               # pid 被重複使用：這個行程比檔案晚建立，留下檔案的那個已經不在
                return True
            finally:
                k32.CloseHandle(h)
        except Exception:
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except Exception:
        return True
    return True


def _win_process_start_time(k32, handle) -> Optional[float]:
    """Windows：行程的建立時間（Unix 秒，UTC）；拿不到回 None。GetProcessTimes 的 FILETIME＝1601-01-01 起的 100 ns。"""
    try:
        import ctypes
        from ctypes import wintypes
        ft = (wintypes.FILETIME * 4)()
        if not k32.GetProcessTimes(handle, ctypes.byref(ft[0]), ctypes.byref(ft[1]), ctypes.byref(ft[2]), ctypes.byref(ft[3])):
            return None
        ticks = (int(ft[0].dwHighDateTime) << 32) | int(ft[0].dwLowDateTime)
        return ticks / 1e7 - 11644473600.0
    except Exception:
        return None


def leftover_clip_files(folder: Optional[str] = None, own_pid: Optional[int] = None) -> List[str]:
    """暫存資料夾裡複製失敗留下的 plotkit_clip_<pid>_<n>.png／.pdf（完整路徑，照檔名排）：這個行程自己的與「留下它的行程已經不在」的。
    複製成功的暫存檔在剪貼簿工具結束之後就刪了，所以留下來的就是失敗時訊息寫「PNG 已存到 …」給使用者用的那份（或程式當掉時留下的）。
    還在跑的別的行程的不算（它的剪貼簿工具可能還在讀；它關閉時自己會提醒）。只列出、一個都不刪——2026-10-30 使用者決定 W13：
    「留著，但每次關閉時都要說哪裡有東西未處理」（DSV 關閉時的提醒用它；0.9.14 第一版在下一次複製前把以前的行程留下的刪掉，第一輪驗證 R14-REG-1 撤掉）。"""
    folder = folder or tempfile.gettempdir()
    own = int(own_pid or os.getpid())
    out: List[str] = []
    try:
        names = os.listdir(folder)
    except OSError:
        return out
    for name in sorted(names):
        m = _CLIP_RE.match(name)
        if not m:
            continue
        pid = int(m.group(1))
        p = os.path.join(folder, name)
        if not os.path.isfile(p):
            continue
        if pid != own:
            try:
                mtime: Optional[float] = os.path.getmtime(p)
            except OSError:
                mtime = None
            if _pid_alive(pid, mtime):
                continue
        out.append(p)
    return out


_MIME = {"png": "image/png", "pdf": "application/pdf"}
_MAC_CLASS = {"png": "«class PNGf»", "pdf": "«class PDF »"}      # 'PDF ' 四碼含尾端空白


def clipboard_command_for(platform: str, png_path: str, kind: str = "png") -> Optional[List[str]]:
    """各平台把 PNG（kind="png"）或 PDF（kind="pdf"）放進剪貼簿的指令（純函式，方便測試引號處理）。
    找不到工具、或 Windows 要放 PDF（.NET 剪貼簿沒有向量格式可用）回傳 None。"""
    if platform.startswith("win"):
        if kind != "png":
            return None
        exe = (shutil.which("powershell") or shutil.which("pwsh")
               or os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe"))
        p = png_path.replace("'", "''")
        script = ("Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
                  f"$img = [System.Drawing.Image]::FromFile('{p}'); "
                  "[System.Windows.Forms.Clipboard]::SetImage($img); $img.Dispose()")
        return [exe, "-NoProfile", "-NonInteractive", "-STA", "-ExecutionPolicy", "Bypass", "-Command", script]
    if platform == "darwin":
        p = png_path.replace("\\", "\\\\").replace('"', '\\"')
        return ["osascript", "-e", f'set the clipboard to (read (POSIX file "{p}") as {_MAC_CLASS[kind]})']
    if shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard", "-t", _MIME[kind], "-i", png_path]
    if shutil.which("wl-copy"):
        return ["wl-copy", "--type", _MIME[kind]]
    return None


def clipboard_image_supported() -> bool:
    return clipboard_command_for(sys.platform, "x.png") is not None


def clipboard_vector_supported() -> bool:
    return clipboard_command_for(sys.platform, "x.pdf", "pdf") is not None


def vector_copy_state() -> str:
    """「複製向量圖」按鈕／選單項目的 state：這個系統放不了向量圖（Windows、沒有 xclip／wl-copy 的 Linux）就停用。"""
    return "normal" if clipboard_vector_supported() else "disabled"


def vector_copy_tip(tip: str) -> str:
    """「複製向量圖」的 tooltip：不支援時補一句原因與替代做法（MATLAB 的慣例：不適用的按鈕變灰、tooltip 說明）。"""
    if clipboard_vector_supported():
        return tip
    return tip + tr("（這個系統的剪貼簿放不了向量圖：請改用複製圖片或存檔）")


def copy_png_to_clipboard(png_path: str) -> Tuple[bool, str]:
    return _copy_file_to_clipboard(png_path, "png")


def copy_pdf_to_clipboard(pdf_path: str) -> Tuple[bool, str]:
    return _copy_file_to_clipboard(pdf_path, "pdf")


def _copy_file_to_clipboard(png_path: str, kind: str) -> Tuple[bool, str]:
    cmd = clipboard_command_for(sys.platform, png_path, kind)
    if cmd is None:
        if kind == "pdf":
            return False, tr("這個系統不支援把向量圖放進剪貼簿；PDF 已存到 {path}").format(path=png_path)
        return False, tr("這個系統沒有可用的剪貼簿工具（Linux 請裝 xclip 或 wl-clipboard）；PNG 已存到 {path}").format(path=png_path)
    done = tr("向量圖（PDF）已複製到剪貼簿") if kind == "pdf" else tr("圖片已複製到剪貼簿")
    failed = tr("複製到剪貼簿失敗（{err}）；PDF 已存到 {path}") if kind == "pdf" else tr("複製到剪貼簿失敗（{err}）；PNG 已存到 {path}")
    try:
        kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.PIPE}
        if sys.platform.startswith("win"):
            kw["creationflags"] = 0x08000000          # CREATE_NO_WINDOW：--windowed 的 exe 不會閃黑視窗
        if cmd[0] == "wl-copy":
            with open(png_path, "rb") as f:
                kw["stdin"] = f
                r = subprocess.run(cmd, timeout=CLIP_TIMEOUT_S, **kw)
        elif cmd[0] == "xclip":
            subprocess.Popen(cmd, **kw)               # xclip 會留在背景提供剪貼簿內容，不能等它結束
            return True, done
        else:
            r = subprocess.run(cmd, timeout=CLIP_TIMEOUT_S, **kw)     # 等它結束（逾時就結束它）：之後才能刪暫存檔
        if r.returncode != 0:
            enc = "oem" if sys.platform.startswith("win") else "utf-8"    # PowerShell 的 stderr 是 OEM 字碼頁
            err = (r.stderr or b"").decode(enc, "replace").strip()
            return False, failed.format(err=err[:120] or "rc=" + str(r.returncode), path=png_path)
        return True, done
    except Exception as e:
        return False, failed.format(err=e, path=png_path)


def copy_figure_to_clipboard(fig, dpi: int = 150, keep_file: bool = False, content: str = "image") -> Tuple[bool, str]:
    """把整張圖放進系統剪貼簿：content="image"＝PNG（dpi 預設 150）、"vector"＝PDF（MATLAB 的 Copy as vector graphic）。
    暫存檔：成功時等 PowerShell／osascript 結束之後刪掉；失敗（含逾時被結束）時留著——訊息寫「PNG 已存到 …」給使用者用，
    之後的複製也不刪它（2026-10-30 使用者決定 W13：留著；DSV 每次關閉時提醒它在哪裡，leftover_clip_files）。"""
    if content == "vector":
        if not clipboard_vector_supported():           # 不產生用不到的暫存 PDF（按鈕平常已停用；這裡是程式直接呼叫）
            return False, tr("這個系統的剪貼簿放不了向量圖：請改用複製圖片或存檔")
        path = temp_path("pdf")
        try:
            save_pdf(fig, path)
        except Exception as e:
            return False, tr("產生 PDF 失敗：{err}").format(err=e)
        ok, msg = copy_pdf_to_clipboard(path)
    else:
        path = temp_png_path()
        try:
            save_png(fig, path, dpi=dpi)
        except Exception as e:
            return False, tr("產生 PNG 失敗：{err}").format(err=e)
        ok, msg = copy_png_to_clipboard(path)
    if ok and not keep_file and not sys.platform.startswith("linux"):
        try:
            os.remove(path)
        except OSError:
            pass
    return ok, msg
