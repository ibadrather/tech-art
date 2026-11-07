#!/usr/bin/env bash
# Render SVGs to PNG at 2x with headless Chrome (fonts are embedded in the SVGs).
#   ./src/render.sh                 every SVG under out/ -> a PNG beside it
#   ./src/render.sh out/robots      only the SVGs under out/robots
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
render() {  # svg png
  local w h
  w=$(grep -o 'width="[0-9]*"' "$1" | head -1 | tr -dc 0-9)
  h=$(grep -o 'height="[0-9]*"' "$1" | head -1 | tr -dc 0-9)
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size="$w,$h" --screenshot="$PWD/$2" "file://$PWD/$1" >/dev/null 2>&1
  echo "$2"
}
[ $# -eq 0 ] && set -- out
find "$@" -name '*.svg' | sort | while read -r svg; do render "$svg" "${svg%.svg}.png"; done
