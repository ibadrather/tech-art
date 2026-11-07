#!/usr/bin/env bash
# Render every out/svg/*.svg to out/png/*.png at 2x with headless Chrome (fonts are embedded in the SVGs).
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for svg in out/svg/*.svg; do
  name=$(basename "$svg" .svg)
  w=$(grep -o 'width="[0-9]*"' "$svg" | head -1 | tr -dc 0-9)
  h=$(grep -o 'height="[0-9]*"' "$svg" | head -1 | tr -dc 0-9)
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size="$w,$h" --screenshot="$PWD/out/png/$name.png" "file://$PWD/$svg" >/dev/null 2>&1
  echo "out/png/$name.png"
done
