#!/usr/bin/env python3
"""Construye edit.json para un reel de FOTOS (sin voz) a partir de un guion visual.

Los cortes caen en los tiempos de la música (bpm del storyboard), cada foto lleva un
movimiento de cámara suave, las etiquetas de cada ambiente aparecen como subtítulos
dinámicos con "click", y la información clave lleva ding + acercamiento + cortina.

Uso: python3 scripts/build_photo_edit.py <carpeta_clips> <projects/NOMBRE>
Lee   projects/NOMBRE/storyboard.json
"""
import json
import shutil
import sys
from pathlib import Path

FPS = 30
ROOT = Path(__file__).resolve().parent.parent


def main(clips_dir: Path, project: Path):
    sb = json.loads((project / "storyboard.json").read_text())
    manifest = {c["id"]: c for c in json.loads((clips_dir / "manifest.json").read_text())["clips"]}
    name = project.name
    beat = 60 / sb["bpm"]
    frame_at = lambda b: round(b * beat * FPS)

    scenes = [{**sb["intro"], "role": "intro"}] + sb["scenes"] + [{**sb["outro"], "role": "outro"}]
    segs, caps, sfx, zooms, transitions = [], [], [], [], []
    b = 0
    for i, sc in enumerate(scenes):
        clip = manifest[sc["clip"]]
        start, end = frame_at(b), frame_at(b + sc["beats"])
        segs.append({"clip": clip["id"], "kind": "image", "src": f"media/clips/{name}/{clip['file']}",
                     "inFrame": 0, "outFrame": end - start, "startFrame": start, "durationFrames": end - start,
                     "text": sc.get("label", ""), "motion": i % 4})
        if sc.get("label"):
            t0 = start / FPS + 0.2
            words = sc["label"].split()
            caps.append({"start": round(t0, 3), "end": round(end / FPS - 0.12, 3), "text": sc["label"],
                         "key": bool(sc.get("key")),
                         "keyWords": list(range(len(words))) if sc.get("key") else [],
                         "words": [{"text": w, "start": round(t0 + k * 0.14, 3), "end": round(t0 + k * 0.14 + 0.3, 3)}
                                   for k, w in enumerate(words)]})
            sfx.append({"src": "media/sfx/click.wav", "frame": round(t0 * FPS) - 1, "volume": 0.3})
            if sc.get("key"):
                sfx.append({"src": "media/sfx/ding.wav", "frame": round((t0 + 0.15) * FPS), "volume": 0.4})
                zooms.append({"frame": start + 6, "durationFrames": end - start - 16})
                transitions.append({"frame": start, "type": "wipe"})
                sfx.append({"src": "media/sfx/whoosh.wav", "frame": max(0, start - 8), "volume": 0.3})
        b += sc["beats"]

    total = frame_at(b)
    outro_start = segs[-1]["startFrame"]
    edit = {
        "fps": FPS, "width": 1080, "height": 1920, "durationInFrames": total,
        "brand": sb.get("brand", {}),
        "hook": {"text": sb["hook"], "startFrame": 0, "endFrame": segs[0]["durationFrames"],
                 "position": sb.get("hookPosition", "center"), "eyebrow": sb.get("hookEyebrow", "EN VENTA")},
        "cta": {"text": sb["cta"], "sub": sb.get("ctaSub", ""), "startFrame": outro_start + 4, "endFrame": total},
        "segments": segs, "overlays": [], "zooms": zooms, "transitions": transitions,
        "captions": caps, "sfx": sorted(sfx, key=lambda s: s["frame"]),
        "music": {"src": "media/music/house-jazz.wav", "volume": sb.get("musicVolume", 0.5),
                  "duckVolume": sb.get("musicVolume", 0.5), "speech": []},
        "log": [f"{k}: excluido ({v})" for k, v in sb.get("excluded", {}).items()],
    }
    dst = ROOT / "public" / "media" / "clips" / name
    dst.mkdir(parents=True, exist_ok=True)
    for s in segs:
        shutil.copy2(clips_dir / manifest[s["clip"]]["file"], dst / manifest[s["clip"]]["file"])
    (project / "edit.json").write_text(json.dumps(edit, indent=2, ensure_ascii=False))
    print(f"Duración: {total / FPS:.1f}s | escenas: {len(segs)} | etiquetas: {len(caps)} | "
          f"clave: {len(zooms)} | 1 tiempo = {beat:.3f}s")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
