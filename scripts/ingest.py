#!/usr/bin/env python3
"""Normaliza los clips de entrada para editarlos en Remotion.

- Video: 1080x1920 (9:16), 30 fps CFR, H.264, keyframe cada 0.5 s (búsqueda rápida).
  Los clips horizontales se recortan al centro; respeta la rotación de los móviles.
- Audio de voz: pasa-altos 80 Hz, reducción de ruido suave, compresión ligera y
  normalización de sonoridad por clip (-16 LUFS) para que todas las tomas suenen parejo.

Uso: python3 scripts/ingest.py <carpeta_entrada> <carpeta_salida>
Escribe <salida>/manifest.json con la lista de clips (orden natural: clip 2 < clip 10).
"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".3gp"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
W, H, FPS = 1080, 1920, 30
VOICE_CHAIN = ("highpass=f=80,afftdn=nr=10:nf=-45,"
               "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:makeup=2,"
               "loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000")


def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.stem)]


def slug(p: Path) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", p.stem.lower()).strip("-")
    m = re.fullmatch(r"(.*?)-?(\d+)", s)
    return f"{m.group(1) or 'clip'}-{int(m.group(2)):02d}" if m else s


def probe(path: Path) -> dict:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    return json.loads(out)


def process_image(src: Path, out_dir: Path) -> dict:
    """Foto -> JPEG vertical 1350x2400 (margen extra para acercamientos sin perder nitidez).
    Respeta la rotación EXIF. Si la foto es cuadrada u horizontal (p. ej. una portada con texto),
    se encaja completa sobre una versión desenfocada de sí misma para no recortar el contenido."""
    from PIL import Image, ImageFilter, ImageOps
    W2, H2 = 1350, 2400
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    cover = ImageOps.fit(im, (W2, H2), Image.LANCZOS)
    if im.width / im.height > 0.85:
        bg = cover.filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.55))
        fg = ImageOps.contain(im, (W2, H2), Image.LANCZOS)
        bg.paste(fg, ((W2 - fg.width) // 2, (H2 - fg.height) // 2))
        cover, fit = bg, "contain"
    else:
        fit = "cover"
    dst = out_dir / f"{slug(src)}.jpg"
    cover.save(dst, quality=90)
    return {"id": dst.stem, "source": src.name, "file": dst.name, "kind": "image", "fit": fit,
            "duration": 0, "orig_size": f"{im.width}x{im.height}", "has_audio": False}


def process(src: Path, out_dir: Path) -> dict:
    if src.suffix.lower() in IMAGE_EXT:
        return process_image(src, out_dir)
    info = probe(src)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise RuntimeError(f"{src.name}: no tiene pista de video")
    dst = out_dir / f"{slug(src)}.mp4"
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
          f"crop={W}:{H},setsar=1,fps={FPS},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src)]
    if a is None:  # clip mudo: añade pista silenciosa para simplificar el montaje
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest"]
    cmd += ["-map", "0:v:0", "-map", "0:a:0" if a else "1:a:0", "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-g", "15", "-keyint_min", "15",
            "-c:a", "aac", "-b:a", "192k", "-ac", "2"]
    if a is not None:
        cmd += ["-af", VOICE_CHAIN]
    cmd += ["-movflags", "+faststart", str(dst)]
    subprocess.run(cmd, check=True)
    dur = float(probe(dst)["format"]["duration"])
    return {
        "id": dst.stem,
        "kind": "video",
        "source": src.name,
        "file": dst.name,
        "duration": round(dur, 3),
        "orig_size": f"{v.get('width')}x{v.get('height')}",
        "has_audio": a is not None,
    }


def main(in_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted((p for p in in_dir.iterdir() if p.suffix.lower() in VIDEO_EXT | IMAGE_EXT), key=natural_key)
    if not files:
        sys.exit(f"No hay videos en {in_dir}")
    with ThreadPoolExecutor(max_workers=2) as ex:
        clips = list(ex.map(lambda p: process(p, out_dir), files))
    for c in clips:
        print(f"  {c['source']:<24} -> {c['file']:<14} {c['duration']:6.2f}s  ({c['orig_size']})")
    (out_dir / "manifest.json").write_text(json.dumps({"clips": clips}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
