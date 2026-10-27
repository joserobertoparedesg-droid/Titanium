#!/usr/bin/env python3
"""Genera clips de PRUEBA (voz sintética + imágenes generadas) para validar el flujo
completo cuando aún no están disponibles los clips reales.

Incluye a propósito: silencios al inicio/final, una pausa larga interna, una toma repetida
(retake), clips sin voz (b-roll) y un clip horizontal 16:9 para probar el recorte a 9:16.

Uso: python3 scripts/make_test_media.py media/input
"""
import subprocess
import sys
import tempfile
from pathlib import Path

FONT = "/usr/share/fonts/truetype/montserrat/Montserrat-SemiBold.ttf"

# (nombre, texto hablado o None para b-roll, color A, color B, orientación, etiqueta)
CLIPS = [
    ("clip 1", "Planta cien por ciento y pozo de agua en Mañongo.", "0x5a1621", "0x2a0a10", "v", "FACHADA"),
    ("clip 2", "Hoy te muestro este apartamento,   en una de las mejores zonas de Naguanagua.", "0x3b2a20", "0x7a5c44", "v", "TOMA 1"),
    ("clip 3", "Hoy te muestro este apartamento en una de las mejores zonas de Naguanagua.", "0x3b2a20", "0x8c6b4f", "v", "TOMA 2"),
    ("clip 4", "Tiene tres habitaciones, dos baños y un amplio balcón con vista a la montaña.", "0x6d1a2a", "0xc9b28f", "v", "SALA"),
    ("clip 5", None, "0x1d3b2a", "0x9fbf8f", "h", "B-ROLL BALCÓN"),
    ("clip 6", "Cuenta con planta eléctrica al cien por ciento y pozo de agua propio.", "0x2a2a2a", "0x6d1a2a", "v", "ÁREAS COMUNES"),
    ("clip 7", None, "0x20304a", "0xb0c4de", "v", "B-ROLL POZO"),
    ("clip 8", "Además, puesto de estacionamiento techado y vigilancia las veinticuatro horas.", "0x4a3b2a", "0xe8dcc4", "v", "ESTACIONAMIENTO"),
    ("clip 9", "Contáctame para agendar tu visita.", "0x6d1a2a", "0xe8dcc4", "v", "CIERRE"),
    ("clip 10", None, "0x3a1018", "0xd8c3a0", "h", "B-ROLL COCINA"),
]


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, text, c0, c1, orient, label in CLIPS:
            w, h = (1080, 1920) if orient == "v" else (1920, 1080)
            audio_inputs = []
            if text:
                speech = tmp / f"{name}.wav"
                run(["espeak-ng", "-v", "es-419", "-s", "150", "-p", "45", "-w", str(speech), text])
                # 1.2 s de silencio antes y 1.0 s después (tomas reales con "aire").
                padded = tmp / f"{name}_pad.wav"
                run(["ffmpeg", "-y", "-i", str(speech), "-af",
                     "adelay=1200|1200,apad=pad_dur=1.0,aresample=48000", "-ac", "2", str(padded)])
                dur = float(subprocess.check_output([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "csv=p=0", str(padded)]).decode().strip())
                audio_inputs = ["-i", str(padded)]
            else:
                dur = 4.0
            fs = 64 if orient == "v" else 56
            vf = (
                f"drawbox=x=0:y=ih*0.82:w=iw:h=ih*0.18:color=black@0.15:t=fill,"
                f"drawtext=fontfile={FONT}:text='{label}':fontcolor=white@0.85:fontsize={fs}:"
                f"x=(w-text_w)/2:y=h*0.12,"
                f"drawtext=fontfile={FONT}:text='{name.upper()} · PRUEBA':fontcolor=white@0.6:"
                f"fontsize={fs // 2}:x=(w-text_w)/2:y=h*0.12+{fs + 20}"
            )
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i",
                   f"gradients=s={w}x{h}:c0={c0}:c1={c1}:x0=0:y0=0:x1={w}:y1={h}:speed=0.02:d={dur}:r=30",
                   *audio_inputs, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-pix_fmt", "yuv420p"]
            if audio_inputs:
                cmd += ["-c:a", "aac", "-b:a", "160k", "-shortest"]
            else:
                # b-roll con ruido ambiente muy bajo (sin voz)
                cmd = cmd[:6] + ["-f", "lavfi", "-i", f"anoisesrc=d={dur}:c=pink:a=0.003:r=48000"] + cmd[6:]
                cmd += ["-c:a", "aac", "-b:a", "96k", "-ac", "2", "-shortest"]
            cmd += ["-t", f"{dur:.3f}", str(out_dir / f"{name}.mp4")]
            run(cmd)
            print(f"  {name}.mp4  {dur:5.2f}s  {'voz' if text else 'b-roll'}  {w}x{h}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "media/input"))
