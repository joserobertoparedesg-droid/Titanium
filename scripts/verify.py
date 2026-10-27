#!/usr/bin/env python3
"""Control de calidad del video final.

1. Sincronía: vuelve a transcribir el MP4 renderizado y compara el inicio de cada palabra
   real con el momento en que aparece en los subtítulos.
2. Integridad: compara el texto escuchado en el render con el texto editado (palabras cortadas
   o perdidas bajan la similitud).
3. Voz vs. música: margen en dB entre la voz y la música bajo la voz.
4. Formato: resolución, fps, duración, sonoridad integrada.
5. Hoja de contacto con fotogramas para revisar la legibilidad.

Uso: python3 scripts/verify.py <projects/NOMBRE> <video.mp4>
"""
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from build_edit import norm  # noqa: E402
from transcribe import DEFAULT_MODEL, PROMPT, load_audio  # noqa: E402


def lufs(path, start=None, dur=None):
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if start is not None:
        cmd += ["-ss", str(start), "-t", str(dur)]
    cmd += ["-i", str(path), "-af", "ebur128", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(m[-1]) if m else float("nan")


def main(project: Path, video: Path):
    from faster_whisper import WhisperModel

    edit = json.loads((project / "edit.json").read_text())
    fps = edit["fps"]
    report = {"video": str(video)}

    info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-print_format", "json",
                                               "-show_streams", "-show_format", str(video)]))
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    report["formato"] = f"{v['width']}x{v['height']} @ {v['r_frame_rate']} fps, {float(info['format']['duration']):.2f}s"
    report["sonoridad_integrada_LUFS"] = lufs(video)

    # 1-2. Re-transcripción del render
    model = WhisperModel(DEFAULT_MODEL, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(load_audio(video), language="es", word_timestamps=True, vad_filter=True,
                               initial_prompt=PROMPT, beam_size=5, condition_on_previous_text=False)
    heard = [w for s in segs for w in (s.words or [])]
    cap_words = [w for c in edit["captions"] for w in c["words"]]
    a = [norm(w["text"]).replace(" ", "") for w in cap_words]
    b = [norm(w.word).replace(" ", "") for w in heard]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    offsets = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            offsets.append(cap_words[blk.a + k]["start"] - heard[blk.b + k].start)
    off = np.abs(np.array(offsets)) if offsets else np.array([np.nan])
    report["sincronia"] = {
        "palabras_emparejadas": f"{len(offsets)}/{len(cap_words)}",
        "desfase_medio_ms": round(float(np.mean(off)) * 1000),
        "desfase_p95_ms": round(float(np.percentile(off, 95)) * 1000),
        "desfase_max_ms": round(float(np.max(off)) * 1000),
    }
    edited_text = " ".join(s["text"] for s in edit["segments"])
    heard_text = " ".join(w.word.strip() for w in heard)
    report["integridad_texto"] = {
        "similitud_editado_vs_escuchado": round(difflib.SequenceMatcher(
            None, norm(edited_text).replace(" %", "%"), norm(heard_text).replace(" %", "%")).ratio(), 3),
        "escuchado": heard_text,
    }

    # 3. Margen voz/música: voz normalizada a -16 LUFS en la ingesta; música atenuada con ducking.
    music_src = Path("public") / edit["music"]["src"]
    m_lufs = lufs(music_src)
    duck_db = 20 * np.log10(edit["music"]["duckVolume"])
    report["voz_vs_musica"] = {
        "voz_LUFS": -16.0,
        "musica_bajo_voz_LUFS": round(m_lufs + duck_db, 1),
        "margen_dB": round(-16.0 - (m_lufs + duck_db), 1),
        "criterio": "> 15 dB = voz claramente inteligible",
    }

    # 4-5. Hoja de contacto
    sheet = video.with_suffix(".contact.jpg")
    total = float(info["format"]["duration"])
    n = 8
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"fps={n / total},scale=270:-1,tile={n}x1", "-frames:v", "1", str(sheet)], check=True)
    report["hoja_de_contacto"] = str(sheet)

    ok = (report["sincronia"]["desfase_p95_ms"] <= 200
          and report["integridad_texto"]["similitud_editado_vs_escuchado"] >= 0.9
          and report["voz_vs_musica"]["margen_dB"] >= 15)
    report["resultado"] = "OK" if ok else "REVISAR"
    out = video.with_suffix(".qa.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
