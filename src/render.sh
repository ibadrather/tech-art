#!/usr/bin/env bash
# Render SVGs to PNG at 2x with headless Chrome (fonts are embedded in the SVGs).
#   ./src/render.sh                 out/svg/*.svg -> out/png/*.png
#   ./src/render.sh out/robots      every SVG under out/robots -> a PNG beside it
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
if [ $# -eq 0 ]; then
  for svg in out/svg/*.svg; do render "$svg" "out/png/$(basename "$svg" .svg).png"; done
else
  find "$@" -name '*.svg' | sort | while read -r svg; do render "$svg" "${svg%.svg}.png"; done
fi
