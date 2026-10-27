#!/usr/bin/env bash
# Renderiza un proyecto y masteriza el audio.
# Uso: bash scripts/render.sh <nombre_proyecto> [salida.mp4]
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="${1:?Uso: render.sh <proyecto> [salida.mp4]}"
OUT="${2:-out/${NAME}.mp4}"
mkdir -p out
RAW="out/${NAME}.raw.mp4"
npx remotion render src/index.ts Reel "$RAW" --props="projects/${NAME}/edit.json" --log=error
# Masterización: -14 LUFS integrados (estándar de Instagram/TikTok), pico real -1 dBTP.
ffmpeg -v error -y -i "$RAW" -map 0:v -map 0:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11,aresample=48000" -c:a aac -b:a 192k -movflags +faststart "$OUT"
rm -f "$RAW"
echo "Render listo: $OUT"
