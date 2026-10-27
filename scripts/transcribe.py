#!/usr/bin/env python3
"""Transcribe cada clip normalizado con faster-whisper (modelo local, sin internet)
con marcas de tiempo por palabra. Escribe <clip>.words.json junto a cada clip.

Uso: python3 scripts/transcribe.py <carpeta_clips> [--model RUTA]
"""
import argparse
import json
import os
import subprocess
from pathlib import Path

import numpy as np

from faster_whisper import WhisperModel

DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "/home/user/vendor/whisper-small-ct2")
# Vocabulario que ayuda a escribir bien nombres locales y términos inmobiliarios.
PROMPT = ("Apartamento en venta en Mañongo, Naguanagua, Carabobo. Planta eléctrica al 100%, "
          "pozo de agua, habitaciones, baños, estacionamiento, vigilancia. Contáctame.")


def load_audio(path: Path) -> np.ndarray:
    """Audio mono 16 kHz float32 decodificado con FFmpeg (evita depender de PyAV)."""
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le",
                                   "-ac", "1", "-ar", "16000", "-"])
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def refine_onsets(audio: np.ndarray, words: list, sr: int = 16000) -> int:
    """Whisper suele adelantar el inicio de la primera palabra tras un silencio (~0.3 s).
    Se corrige buscando el arranque real de la voz por energía (ventanas de 10 ms)."""
    hop = sr // 100
    n = len(audio) // hop
    rms = np.sqrt(np.mean(audio[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    floor = np.percentile(db, 10)
    fixed = 0
    for i, w in enumerate(words):
        prev_end = words[i - 1]["end"] if i else 0.0
        if i and w["start"] - prev_end < 0.15:
            continue  # sólo inicios de frase
        a, b = int(w["start"] * 100), int(min(w["end"], w["start"] + 0.6) * 100)
        if b <= a:
            continue
        thr = max(floor + 12, db[a:b + 1].max() - 25)
        hit = np.nonzero(db[a:b + 1] > thr)[0]
        if len(hit):
            onset = round((a + hit[0]) / 100 - 0.03, 3)
            if onset > w["start"] + 0.04 and onset < w["end"] - 0.05:
                w["start"] = onset
                fixed += 1
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips_dir", type=Path)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    manifest = json.loads((args.clips_dir / "manifest.json").read_text())
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    for clip in manifest["clips"]:
        out = args.clips_dir / f"{clip['id']}.words.json"
        if out.exists() and not args.force:
            continue
        audio = load_audio(args.clips_dir / clip["file"])
        segments, info = model.transcribe(
            audio, language="es", word_timestamps=True,
            vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
            initial_prompt=PROMPT, beam_size=5, condition_on_previous_text=False)
        segs = []
        for s in segments:
            segs.append({
                "start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
                "avg_logprob": round(s.avg_logprob, 3), "no_speech_prob": round(s.no_speech_prob, 3),
                "words": [{"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3),
                           "prob": round(w.probability, 3)} for w in (s.words or [])],
            })
        refine_onsets(audio, [w for sg in segs for w in sg["words"]])
        out.write_text(json.dumps({"clip": clip["id"], "segments": segs}, indent=2, ensure_ascii=False))
        text = " ".join(s["text"] for s in segs) or "(sin voz)"
        print(f"  {clip['id']}: {text}")


if __name__ == "__main__":
    main()
