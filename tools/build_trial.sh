#!/bin/bash
# Digital Signal Viewer — 試用版打包（2026-11-01 外觀主題 example；使用者「先做example」）。
# 和 build_mac.sh 同一套 PyInstaller 參數（onedir、windowed、同樣的 add-data／hidden-import／exclude），但：
#   - 名稱 SignalViewer-trial → 改名成「dist/SignalViewer 試用版.app」，CFBundleName／CFBundleDisplayName「SignalViewer 試用版」、
#     CFBundleIdentifier com.dsv.signalviewer.trial（和正式版 SignalViewer.app 是兩個不同的 App）。
#   - CFBundleExecutable 換成一個小啟動器：HOME＝/Users/Shared/DSV-trial/home、TMPDIR＝/Users/Shared/DSV-trial/tmp，再 exec 真正的執行檔。
#     自動存檔（~/.signal_viewer_last.json）、版本備份、log、frozen 資料夾（~/Library/Application Support/SignalViewer）、matplotlib 快取
#     都在 import 時從 HOME 算出來 → 試用版和正式版的設定、自動存檔完全分開；複製失敗留下的暫存 PNG 也分開。
#     使用者裝在 ~/Library/Fonts 的字型（Noto Sans TC 等）用符號連結借給試用版的 HOME，圖上的中文字型和正式版一樣（只讀）。
#   - ad-hoc 簽章（codesign -s -），不用 .signing 鑰匙圈；不發布到 /Users/Shared/DSV-latest、不重開正在跑的 App（不呼叫 relaunch_mac.sh）。
# 用法：bash tools/build_trial.sh        （產出 dist/SignalViewer 試用版.app；複製到 /Users/Shared/DSV-trial/ 另外做）
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
PY=${PY:-$ROOT/.venv-build/bin/python}    # 正式版打包用的同一個 venv（repo 底下的 .venv-build；不在這裡 pip install，不動它）
"$PY" -c "import tkinter, numpy, matplotlib, PyInstaller, plotkit" || { echo "[build_trial] 缺 tkinter／numpy／matplotlib／PyInstaller／plotkit"; exit 1; }
for f in README.md README.en.md assets/SignalViewer.icns assets/SignalViewer-256.png; do [ -f "$f" ] || { echo "[build_trial] 缺 $f"; exit 1; }; done
NAME=SignalViewer-trial
LABEL="SignalViewer 試用版"
APP="dist/$LABEL.app"
rm -rf "build/trial" "dist/$NAME" "dist/$NAME.app" "$APP"
"$PY" -m PyInstaller --noconfirm --clean --onedir --windowed --name "$NAME" \
  --workpath "$ROOT/build/trial" --specpath "$ROOT/build/trial" --distpath "$ROOT/dist" \
  --add-data "$ROOT/README.md:." --add-data "$ROOT/README.en.md:." --add-data "$ROOT/assets/SignalViewer-256.png:assets" \
  --icon "$ROOT/assets/SignalViewer.icns" \
  --hidden-import plotkit --collect-submodules plotkit \
  --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module PySide2 --exclude-module PySide6 \
  --exclude-module IPython --exclude-module scipy --exclude-module pandas "$ROOT/signal_viewer.py"
rm -rf "dist/$NAME"                      # onedir 的中間資料夾（.app 裡已經有一份）
mv "dist/$NAME.app" "$APP"
PLIST="$APP/Contents/Info.plist"
VER=$(sed -n 's/^APP_VERSION = "\([^"]*\)".*/\1/p' signal_viewer.py)
for key in CFBundleShortVersionString CFBundleVersion; do plutil -replace "$key" -string "${VER:-0}" "$PLIST"; done
plutil -replace CFBundleName -string "$LABEL" "$PLIST"
plutil -replace CFBundleDisplayName -string "$LABEL" "$PLIST"
plutil -replace CFBundleIdentifier -string "com.dsv.signalviewer.trial" "$PLIST"
# 啟動器：Contents/MacOS/SignalViewer-trial-launch（真正的執行檔 SignalViewer-trial 不動）
LAUNCH="$APP/Contents/MacOS/$NAME-launch"
cat > "$LAUNCH" <<'EOS'
#!/bin/bash
# SignalViewer 試用版啟動器：設定、自動存檔、frozen、快取、暫存檔都放在 /Users/Shared/DSV-trial（和正式版分開），再執行真正的程式。
TRIAL=/Users/Shared/DSV-trial
H="$TRIAL/home"
mkdir -p "$H/Library" "$TRIAL/tmp"
chmod 700 "$H" "$TRIAL/tmp" 2>/dev/null
REAL_HOME=$(/usr/bin/dscl . -read "/Users/$(/usr/bin/id -un)" NFSHomeDirectory 2>/dev/null | /usr/bin/awk '{print $2}')
if [ -n "$REAL_HOME" ] && [ -d "$REAL_HOME/Library/Fonts" ] && [ ! -e "$H/Library/Fonts" ]; then
  ln -s "$REAL_HOME/Library/Fonts" "$H/Library/Fonts"      # 只借字型（matplotlib 找 ~/Library/Fonts）；試用版不會寫進去
fi
export HOME="$H"
export TMPDIR="$TRIAL/tmp/"
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/SignalViewer-trial" "$@"
EOS
chmod 755 "$LAUNCH"
plutil -replace CFBundleExecutable -string "$NAME-launch" "$PLIST"
codesign --force --deep -s - "$APP"
codesign --verify --deep "$APP" || { echo "[build_trial] 簽章驗證失敗"; exit 1; }
printf 'version=%s (trial)\ncommit=%s\nbuilt=%s\n' "$VER" "$(git rev-parse --short HEAD 2>/dev/null)$(git diff --quiet 2>/dev/null || echo +dirty)" \
  "$(date '+%Y-%m-%d %H:%M:%S')" > "dist/TRIAL_VERSION.txt"
echo "[build_trial] done: ${ROOT}/${APP}（v${VER}，ad-hoc 簽章；$(tr '\n' ' ' < dist/TRIAL_VERSION.txt)）"
