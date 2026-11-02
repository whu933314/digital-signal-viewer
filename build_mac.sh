#!/bin/bash
# Digital Signal Viewer — macOS 打包（PyInstaller）；版本取自 signal_viewer.py 的 APP_VERSION。產出 dist/SignalViewer.app（可直接雙擊）。
#   bash build_mac.sh            → --onedir --windowed：dist/SignalViewer.app（啟動快，建議）
#   bash build_mac.sh onefile    → --onefile --windowed：dist/SignalViewer.app（單檔，第一次啟動要解壓縮，較慢）
# 需要一個有 tkinter（Tk 8.6）的 Python；預設用 anaconda 的（Apple 內建的 Tk 8.5 在 macOS 26 會當掉）。
# numpy／matplotlib／PyInstaller 都裝在專案裡的 .venv-build/（不用 anaconda 的 site-packages：裡面有過時的 pathlib 套件，PyInstaller 會拒絕），
# 不碰系統或 anaconda 本身。
set -e
cd "$(dirname "$0")"
PY=${PY:-/opt/anaconda3/bin/python3}
MODE=${1:-onedir}
case "$MODE" in onedir|onefile) ;; *) echo "[build_mac] 用法：bash build_mac.sh [onedir|onefile]"; exit 1;; esac
if [ ! -x .venv-build/bin/python ]; then
  echo "[build_mac] 建立 .venv-build（$PY）"
  "$PY" -m venv .venv-build
fi
# 版本鎖定（2026-10-22 實測可用；matplotlib 3.10+ 在 macOS 第一次建字型快取會跑 system_profiler，程式已改用固定快取資料夾）
.venv-build/bin/python -m pip install --quiet --upgrade pip "numpy==2.4.6" "matplotlib==3.11.2" "pyinstaller==6.22.3" "tkinterdnd2==0.6.4"
.venv-build/bin/python -c "import tkinter, numpy, matplotlib, plotkit" || { echo "[build_mac] 缺 tkinter／numpy／matplotlib／plotkit"; exit 1; }
for f in README.md README.en.md assets/SignalViewer.icns assets/SignalViewer-256.png; do [ -f "$f" ] || { echo "[build_mac] 缺 $f（說明視窗／圖示用；圖示用 tools/make_icon.py 產生）"; exit 1; }; done
rm -rf build dist
.venv-build/bin/python -m PyInstaller --noconfirm --clean "--$MODE" --windowed --name SignalViewer \
  --add-data "README.md:." --add-data "README.en.md:." --add-data "assets/SignalViewer-256.png:assets" --icon assets/SignalViewer.icns \
  --hidden-import plotkit --collect-submodules plotkit \
  --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 \
  --exclude-module IPython --exclude-module scipy --exclude-module pandas signal_viewer.py
VER=$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' signal_viewer.py)     # 只取引號裡的（後面有註解）
for key in CFBundleShortVersionString CFBundleVersion; do
  plutil -replace "$key" -string "${VER:-0}" dist/SignalViewer.app/Contents/Info.plist   # PyInstaller 預設寫 0.0.0
done
# 簽章：改過 Info.plist 之後要重簽（否則簽章失效）。有 .signing/（tools/make_signing_keychain.sh 建的專用鑰匙圈＋自簽憑證）就用它，
# designated requirement＝identifier＋憑證 leaf → 每次重新打包 macOS 都認得是同一個 App，不會再重問「文件」等權限；沒有就退回 ad-hoc。
APP=dist/SignalViewer.app
KC="$(pwd)/.signing/dsv-signing.keychain-db"
if [ -f "$KC" ] && [ -f .signing/kc.pass ] && [ -f .signing/cert.pem ]; then
  HASH=$(openssl x509 -in .signing/cert.pem -noout -fingerprint -sha1 | sed 's/.*=//; s/://g')
  ORIG_KCS=$(security list-keychains -d user | tr -d '"' | xargs)
  restore_kcs() { security list-keychains -d user -s $ORIG_KCS; }
  trap restore_kcs EXIT
  security list-keychains -d user -s $ORIG_KCS "$KC"          # codesign 只在搜尋清單裡找身分；簽完立刻還原
  security unlock-keychain -p "$(cat .signing/kc.pass)" "$KC"
  codesign --force --deep -s "$HASH" "$APP"
  restore_kcs; trap - EXIT
  echo "[build_mac] signed with DSV Local Code Signing ($HASH)"
else
  codesign --force --deep -s - "$APP"
  echo "[build_mac] ad-hoc signed（要固定簽章請先跑 tools/make_signing_keychain.sh）"
fi
codesign --verify --deep "$APP" || { echo "[build_mac] 簽章驗證失敗"; exit 1; }
# 發佈給其他 Mac 拿最新版：/Users/Shared/DSV-latest 存在才做（本機慣例，不存在就略過）
PUB=/Users/Shared/DSV-latest
if [ -d "$PUB" ]; then
  rm -rf "$PUB/SignalViewer.app.new"
  ditto "$APP" "$PUB/SignalViewer.app.new"
  rm -rf "$PUB/SignalViewer.app" && mv "$PUB/SignalViewer.app.new" "$PUB/SignalViewer.app"
  printf 'version=%s\ncommit=%s\nbuilt=%s\n' "$VER" "$(git rev-parse --short HEAD 2>/dev/null)$(git diff --quiet 2>/dev/null || echo +dirty)" "$(date '+%Y-%m-%d %H:%M:%S')" > "$PUB/VERSION.txt"
  echo "[build_mac] published to ${PUB}（$(tr '\n' ' ' < "$PUB/VERSION.txt")）"
fi
echo "[build_mac] done: $(pwd)/dist/SignalViewer.app（v${VER}）"
# 使用者要求（2026-10-23）：每次更新好自動重啟正在跑的 app（沒在跑就不動；NO_RELAUNCH=1 可略過）
[ -n "$NO_RELAUNCH" ] || bash tools/relaunch_mac.sh
