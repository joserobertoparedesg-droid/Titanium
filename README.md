# Titanium · Editor de reels inmobiliarios (Remotion + FFmpeg)

Flujo reutilizable que convierte clips crudos del móvil en un reel vertical 9:16 (1080×1920, 30 fps)
con la identidad de marca: **Montserrat**, **vinotinto y beige**, estilo minimalista, elegante y dinámico.

## Qué hace (automático)

| Paso | Script | Detalle |
|---|---|---|
| 1. Normalizar | `scripts/ingest.py` | 1080×1920, 30 fps CFR, recorte al centro de clips horizontales; voz con pasa-altos, reducción de ruido, compresión y -16 LUFS por clip |
| 2. Transcribir | `scripts/transcribe.py` | Whisper *small* local (sin internet), marcas de tiempo por palabra + corrección del inicio de frase por energía |
| 3. Editar | `scripts/build_edit.py` | Detecta tomas repetidas y se queda con la mejor; elimina silencios largos y conserva pausas naturales (≤0,6 s) con márgenes que **no cortan palabras**; gancho primero y llamada a la acción al final; subtítulos de 2-4 palabras; marca la información clave |
| 4. Música/SFX | `scripts/make_audio_assets.py` | House jazz elegante y efectos (ding, click, whoosh) **sintetizados por código: originales, sin derechos de terceros** |
| 5. Render | `scripts/render.sh` | Remotion + masterización FFmpeg a -14 LUFS (Instagram/TikTok) |
| 6. Control de calidad | `scripts/verify.py` | Re-transcribe el video final y mide el desfase de los subtítulos, la integridad del texto, el margen voz/música y genera una hoja de contacto |

En el video: tarjeta de **gancho** al inicio, **subtítulos dinámicos centrados** (palabra activa resaltada,
datos clave en píldora vinotinto), **click** al aparecer cada subtítulo y **ding** en información clave,
**acercamientos** y **cortinas vinotinto/beige** cuando aparece información clave del apartamento, inserciones de
**B-roll** (clips sin voz), música con *ducking* (baja bajo la voz) y **cierre** con la llamada a la acción.

## Uso

```bash
npm install                                  # una vez
cp -r projects/prueba projects/manongo       # plantilla de configuración
#   edita projects/manongo/config.json (gancho, CTA, correcciones, exclusiones...)
#   copia los clips en media/input/  (clip 1.mp4 ... clip 28.mp4)
bash scripts/pipeline.sh manongo media/input # => out/manongo.mp4 + out/manongo.qa.json
```

### Ajustes sin repetir todo
- **Texto, orden o clips**: edita `projects/<p>/config.json` (`exclude`, `order`, `corrections`, `keyTerms`,
  `maxPause`, `musicVolume`, `musicDuckVolume`...) y vuelve a correr `python3 scripts/build_edit.py media/work/<p> projects/<p>` + `bash scripts/render.sh <p>`.
- **Retoque fino**: `projects/<p>/edit.json` es el proyecto editable (cortes por frame, subtítulos, zooms,
  transiciones, SFX). Cámbialo y ejecuta solo `bash scripts/render.sh <p>`.
- **Vista previa interactiva**: `npx remotion studio --props=projects/<p>/edit.json`.
- **Diseño** (tamaños, colores, animaciones): `src/components/*.tsx`.

## Notas del entorno
- El navegador de Remotion se toma de Playwright (`/opt/pw-browsers/...`), porque `remotion.media` no es accesible
  aquí; se puede forzar otro con `REMOTION_BROWSER=/ruta/chrome`.
- Modelo Whisper: `WHISPER_MODEL=/ruta/modelo-ct2` (por defecto `/home/user/vendor/whisper-small-ct2`).
- `scripts/make_test_media.py` genera clips de prueba (voz sintética) para validar el flujo.
