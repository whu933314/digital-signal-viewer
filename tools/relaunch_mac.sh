#!/bin/bash
# 更新後重啟正在跑的 Digital Signal Viewer（macOS）：對 SignalViewer.app 的行程送 SIGTERM（程式會先自動存檔再關），
# 等它結束後用 open 重開同一個 .app（路徑不在了就開 /Users/Shared/DSV-latest 的）。沒有在跑就什麼都不做。
#   bash tools/relaunch_mac.sh            → 只重啟正在跑的
#   bash tools/relaunch_mac.sh --always   → 沒在跑也開（開 /Users/Shared/DSV-latest 或 dist 的）
PUB=/Users/Shared/DSV-latest/SignalViewer.app
DIST="$(cd "$(dirname "$0")/.." && pwd)/dist/SignalViewer.app"
pids=$(pgrep -f "SignalViewer\.app/Contents/MacOS/SignalViewer" || true)
apps=()
for pid in $pids; do
  exe=$(ps -o command= -p "$pid" | sed 's/ .*//')
  app="${exe%/Contents/MacOS/*}"
  apps+=("$app")
done
if [ -z "$pids" ]; then
  if [ "$1" = "--always" ]; then
    target="$PUB"; [ -d "$target" ] || target="$DIST"
    open -n "$target" && echo "[relaunch] 沒有在跑的 SignalViewer：已開啟 ${target}"
  else
    echo "[relaunch] 沒有在跑的 SignalViewer，不重啟"
  fi
  exit 0
fi
echo "[relaunch] 結束 pid ${pids}（SIGTERM → 程式自動存檔後關閉）"
kill -TERM $pids 2>/dev/null
# 最多等 60 秒：App 在背景、螢幕睡著時 macOS App Nap 會延後舊版的計時器（0.9.4 以前的版本要等下一個 Tk 事件才處理 SIGTERM）
for i in $(seq 1 240); do
  sleep 0.25
  alive=0
  for pid in $pids; do kill -0 "$pid" 2>/dev/null && alive=1; done
  [ $alive = 0 ] && break
  [ "$i" = 60 ] && echo "[relaunch] 15 秒還沒結束（可能在 App Nap），再等最多 45 秒…"
done
for pid in $pids; do
  if kill -0 "$pid" 2>/dev/null; then echo "[relaunch] pid $pid 60 秒內沒結束，強制結束（自動存檔可能沒寫到）"; kill -KILL "$pid" 2>/dev/null; fi
done
sleep 0.5
opened=""
for app in "${apps[@]}"; do
  target="$app"
  [ -d "$target" ] || target="$PUB"
  [ -d "$target" ] || target="$DIST"
  case " $opened " in *" $target "*) continue;; esac
  opened="$opened $target"
  open -n "$target" && echo "[relaunch] 已重新開啟 ${target}（$(sed -n 's/^version=//p' "$(dirname "$target")/VERSION.txt" 2>/dev/null || plutil -extract CFBundleShortVersionString raw "$target/Contents/Info.plist" 2>/dev/null)）"
done
