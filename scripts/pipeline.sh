#!/usr/bin/env bash
# Flujo completo: clips crudos -> video final verificado.
# Uso: bash scripts/pipeline.sh <proyecto> <carpeta_clips_crudos>
#   ej.: bash scripts/pipeline.sh manongo media/input
# Requiere projects/<proyecto>/config.json (copia projects/prueba/config.json como plantilla).
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="${1:?Uso: pipeline.sh <proyecto> <carpeta_clips>}"
IN="${2:?Falta la carpeta de clips}"
WORK="media/work/${NAME}"

echo "== 1/6 Normalizando clips (FFmpeg)";        python3 scripts/ingest.py "$IN" "$WORK"
echo "== 2/6 Transcribiendo (Whisper local)";     python3 scripts/transcribe.py "$WORK"
echo "== 3/6 Construyendo la edición";            python3 scripts/build_edit.py "$WORK" "projects/${NAME}"
SECS=$(python3 -c "import json;e=json.load(open('projects/${NAME}/edit.json'));print(int(e['durationInFrames']/e['fps'])+4)")
echo "== 4/6 Generando música y efectos (${SECS}s)"; python3 scripts/make_audio_assets.py public/media --seconds "$SECS"
echo "== 5/6 Renderizando (Remotion)";            bash scripts/render.sh "$NAME"
echo "== 6/6 Control de calidad";                 python3 scripts/verify.py "projects/${NAME}" "out/${NAME}.mp4"
