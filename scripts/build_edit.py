#!/usr/bin/env python3
"""Construye la decisión de edición (edit.json) que Remotion renderiza.

A partir de los clips normalizados + transcripciones por palabra:
  1. Aplica el diccionario de correcciones (nombres propios, términos).
  2. Detecta tomas repetidas (retakes) y conserva la mejor (mayor confianza; si empatan, la última).
  3. Separa clips con voz (A-roll) de clips sin voz (B-roll).
  4. Recorta silencios: elimina los silencios largos y conserva pausas naturales cortas,
     con márgenes antes/después de cada frase para NO cortar palabras.
  5. Ordena: el clip que dice el gancho va primero; el de la llamada a la acción, al final.
  6. Genera subtítulos dinámicos (2-3 palabras), marca la información clave y programa
     acercamientos, transiciones, inserciones de B-roll y efectos de sonido.

Uso: python3 scripts/build_edit.py <carpeta_clips> <projects/NOMBRE>
Lee   projects/NOMBRE/config.json  (ver projects/README.md)
Crea  projects/NOMBRE/edit.json y copia los clips a public/media/clips/NOMBRE/
"""
import difflib
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

FPS = 30
ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "targetSeconds": 45,
    "maxPause": 0.6,          # pausas internas más largas se recortan a 'keepPause'
    "keepPause": 0.25,
    "padBefore": 0.12,        # aire antes de la primera palabra de una frase
    "padAfter": 0.20,         # aire después de la última palabra (evita cortar sílabas)
    "hookSeconds": 3.0,
    "ctaSeconds": 3.0,
    "maxWordsPerCaption": 4,
    "maxCharsPerCaption": 22,
    "retakeSimilarity": 0.72,
    "musicVolume": 0.20,
    "musicDuckVolume": 0.06,
    "clickVolume": 0.22,
    "dingVolume": 0.30,
    "corrections": {},
    "keyTerms": [
        "planta", "pozo", "agua", "100%", "habitaci", "cuarto", "baño", "metros", "m2", "m²",
        "estacionamiento", "puesto", "vigilancia", "seguridad", "piscina", "balcón", "terraza",
        "vista", "cocina", "precio", "$", "dólares", "mil", "ascensor", "parque", "gimnasio",
        "maletero", "lavandero", "mañongo", "naguanagua",
    ],
    "exclude": [],
    "order": [],
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9%$ ]+", " ", s).strip()


def apply_corrections(words, corrections):
    """Reemplaza secuencias de palabras ('del agua a agua' -> 'de Naguanagua') repartiendo tiempos."""
    for wrong, right in corrections.items():
        pat = norm(wrong).split()
        if not pat:
            continue
        i = 0
        while i <= len(words) - len(pat):
            if [norm(w["text"]) for w in words[i:i + len(pat)]] == pat:
                span = words[i:i + len(pat)]
                trail = re.search(r"[.,;:!?…]+$", span[-1]["text"])
                new = right.split()
                t0, t1 = span[0]["start"], span[-1]["end"]
                step = (t1 - t0) / len(new)
                rep = [{"text": t, "start": round(t0 + k * step, 3), "end": round(t0 + (k + 1) * step, 3),
                        "prob": min(w["prob"] for w in span)} for k, t in enumerate(new)]
                if trail:
                    rep[-1]["text"] += trail.group(0)
                words[i:i + len(pat)] = rep
                i += len(rep)
            else:
                i += 1
    return words


def phrases(words, max_pause):
    out, cur = [], [words[0]]
    for w in words[1:]:
        if w["start"] - cur[-1]["end"] > max_pause:
            out.append(cur)
            cur = []
        cur.append(w)
    out.append(cur)
    return out


STOPWORDS = {"de", "del", "en", "y", "a", "al", "la", "el", "los", "las", "con", "para", "tu", "un",
             "una", "que", "por", "su", "mi", "o", "e", "lo", "le", "te", "se", "este", "esta",
             "estos", "estas", "sus", "muy"}


def merge_symbols(words):
    """Whisper separa '%' o '$' como palabras: se unen a la palabra vecina ('100' + '%' -> '100%')."""
    out = []
    for w in words:
        if out and not re.search(r"[0-9A-Za-zÀ-ÿ]", w["text"]):
            out[-1] = {**out[-1], "text": out[-1]["text"] + w["text"], "end": w["end"]}
        else:
            out.append(dict(w))
    return out


def chunk_captions(words, max_words, max_chars):
    """Bloques de 2-3 palabras; corta en puntuación o pausas y nunca termina en 'de', 'en', 'y'..."""
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        text = " ".join(x["text"] for x in cur)
        punct = re.search(r"[.,;:!?]$", w["text"])
        if not nxt:
            chunks.append(cur)
        elif punct or nxt["start"] - w["end"] > 0.3:
            chunks.append(cur)
            cur = []
        elif len(cur) >= max_words or len(text) + 1 + len(nxt["text"]) > max_chars:
            carry = []
            while len(cur) > 1 and norm(cur[-1]["text"]) in STOPWORDS:
                carry.insert(0, cur.pop())
            chunks.append(cur)
            cur = carry
    # Une bloques de una sola palabra corta ("en", "una") con el siguiente bloque.
    out = []
    i = 0
    while i < len(chunks):
        c = chunks[i]
        if len(c) == 1 and (norm(c[0]["text"]) in STOPWORDS or len(c[0]["text"]) <= 3) \
                and not re.search(r"[.,;:!?]$", c[0]["text"]) and i + 1 < len(chunks):
            chunks[i + 1] = c + chunks[i + 1]
        else:
            out.append(c)
        i += 1
    return out


def is_key(text, terms):
    """Coincidencia al inicio de palabra ('habitaci' -> 'habitaciones'), sin falsos positivos internos."""
    toks = norm(text).split()
    for term in terms:
        t = norm(term)
        if not t or (len(t) < 2 and t not in "$%"):
            continue
        if len(t) <= 3 and any(tok == t or tok.rstrip("%$") == t for tok in toks):
            return True
        if len(t) > 3 and any(tok.startswith(t) for tok in toks) or (" " in t and t in " ".join(toks)):
            return True
    return False


def main(clips_dir: Path, project: Path):
    cfg = {**DEFAULTS, **json.loads((project / "config.json").read_text())}
    manifest = json.loads((clips_dir / "manifest.json").read_text())
    name = project.name
    log = []

    a_roll, b_roll = [], []
    for c in manifest["clips"]:
        if c["id"] in cfg["exclude"]:
            log.append(f"{c['id']}: excluido manualmente")
            continue
        tr_path = clips_dir / f"{c['id']}.words.json"
        tr = json.loads(tr_path.read_text()) if tr_path.exists() else {"segments": []}
        words = [w for s in tr["segments"] if s["no_speech_prob"] < 0.6 for w in s["words"] if w["text"]]
        words = merge_symbols(apply_corrections(words, cfg["corrections"]))
        if len(words) < 2:
            b_roll.append(c)
            continue
        c = {**c, "words": words, "text": " ".join(w["text"] for w in words),
             "conf": sum(w["prob"] for w in words) / len(words)}
        a_roll.append(c)

    # 2. Tomas repetidas: si dos clips dicen casi lo mismo, se queda la de mayor confianza.
    keep = []
    for c in a_roll:
        dup = next((k for k in keep if difflib.SequenceMatcher(None, norm(k["text"]), norm(c["text"])).ratio()
                    >= cfg["retakeSimilarity"]), None)
        if dup is None:
            keep.append(c)
            continue
        better = c if c["conf"] >= dup["conf"] - 0.02 else dup
        worse = dup if better is c else c
        log.append(f"toma repetida: {worse['id']} descartado, se usa {better['id']} "
                   f"(confianza {worse['conf']:.2f} vs {better['conf']:.2f})")
        if better is c:
            keep[keep.index(dup)] = c
    a_roll = keep

    # 5. Orden: manual si se indica; si no, gancho primero y CTA al final.
    if cfg["order"]:
        pos = {cid: i for i, cid in enumerate(cfg["order"])}
        a_roll.sort(key=lambda c: pos.get(c["id"], 999))
    else:
        hook_n, cta_n = norm(cfg["hook"]), norm(cfg["cta"])
        hook_clip = max(a_roll, key=lambda c: difflib.SequenceMatcher(None, norm(c["text"]), hook_n).ratio())
        if difflib.SequenceMatcher(None, norm(hook_clip["text"]), hook_n).ratio() > 0.5:
            a_roll.remove(hook_clip)
            a_roll.insert(0, hook_clip)
            log.append(f"gancho: {hook_clip['id']} va primero")
        cta_clip = max(a_roll, key=lambda c: difflib.SequenceMatcher(None, norm(c["text"]), cta_n).ratio())
        if cta_clip is not a_roll[0] and difflib.SequenceMatcher(None, norm(cta_clip["text"]), cta_n).ratio() > 0.5:
            a_roll.remove(cta_clip)
            a_roll.append(cta_clip)
            log.append(f"llamada a la acción: {cta_clip['id']} va al final")

    # 4. Segmentos sin silencios largos, con márgenes que protegen las palabras.
    def build(max_pause):
        segs, caps, t = [], [], 0.0
        for c in a_roll:
            for ph in phrases(c["words"], max_pause):
                a = max(0.0, ph[0]["start"] - cfg["padBefore"])
                b = min(c["duration"] - 0.05, ph[-1]["end"] + cfg["padAfter"])
                fi, fo = round(a * FPS), round(b * FPS)
                start_f = round(t * FPS)
                segs.append({"clip": c["id"], "src": f"media/clips/{name}/{c['file']}",
                             "inFrame": fi, "outFrame": fo, "startFrame": start_f,
                             "durationFrames": fo - fi, "text": " ".join(w["text"] for w in ph)})
                off = start_f / FPS - fi / FPS
                for ch in chunk_captions(ph, cfg["maxWordsPerCaption"], cfg["maxCharsPerCaption"]):
                    caps.append({"words": [{"text": w["text"], "start": round(w["start"] + off, 3),
                                            "end": round(w["end"] + off, 3)} for w in ch]})
                t = (start_f + fo - fi) / FPS
        return segs, caps, t

    max_pause = cfg["maxPause"]
    segs, caps, speech_end = build(max_pause)
    budget = cfg["targetSeconds"] - cfg["ctaSeconds"] * 0.3
    while speech_end > budget and max_pause > 0.3:
        max_pause = round(max_pause - 0.1, 2)
        segs, caps, speech_end = build(max_pause)
    if speech_end > budget:
        log.append(f"AVISO: el contenido hablado dura {speech_end:.1f}s, más que el objetivo "
                   f"({cfg['targetSeconds']}s). No se cortaron frases para conservar el sentido; "
                   f"usa 'exclude' en config.json para quitar clips.")

    # 6. Subtítulos: tiempos de aparición/desaparición sin parpadeos.
    for i, cap in enumerate(caps):
        cap["start"] = cap["words"][0]["start"]
        nxt = caps[i + 1]["words"][0]["start"] if i + 1 < len(caps) else None
        end = cap["words"][-1]["end"] + 0.15
        if nxt is not None and nxt - end < 0.35:
            end = nxt
        cap["end"] = round(max(end, cap["start"] + 0.45) if nxt is None else min(max(end, cap["start"] + 0.45), nxt), 3)
        cap["text"] = " ".join(w["text"] for w in cap["words"])
        cap["key"] = is_key(cap["text"], cfg["keyTerms"])
        cap["keyWords"] = [j for j, w in enumerate(cap["words"]) if is_key(w["text"], cfg["keyTerms"])]

    cta_start = speech_end - 0.6
    total_frames = round((speech_end + cfg["ctaSeconds"]) * FPS)
    hook_end = min(cfg["hookSeconds"], speech_end)

    # SFX: click suave al aparecer cada subtítulo; ding en información clave (máx. uno cada 2.5 s).
    sfx, last, last_ding = [], -9.0, -9.0
    for cap in caps:
        if cap["start"] < hook_end or cap["start"] >= cta_start:
            continue
        ding = cap["keyWords"] and cap["start"] - last_ding >= 2.5
        if ding or cap["start"] - last >= 0.5:
            sfx.append({"src": f"media/sfx/{'ding' if ding else 'click'}.wav",
                        "frame": max(0, round(cap["start"] * FPS) - 1),
                        "volume": cfg["dingVolume"] if ding else cfg["clickVolume"]})
            last = cap["start"]
            last_ding = cap["start"] if ding else last_ding

    # Acercamientos (punch-in) en información clave, máx. uno cada 2.5 s.
    zooms, last = [], -9.0
    for cap in caps:
        if cap["key"] and hook_end <= cap["start"] < cta_start and cap["start"] - last > 2.5:
            zooms.append({"frame": round(cap["start"] * FPS), "durationFrames": round(max(1.2, cap["end"] - cap["start"] + 0.6) * FPS)})
            last = cap["start"]

    # Transiciones (cortina vinotinto + whoosh) al cambiar de clip cuando entra información clave.
    transitions = []
    for prev, seg in zip(segs, segs[1:]):
        if seg["clip"] != prev["clip"] and is_key(seg["text"], cfg["keyTerms"]) and seg["startFrame"] / FPS < cta_start:
            transitions.append({"frame": seg["startFrame"], "type": "wipe"})
            sfx.append({"src": "media/sfx/whoosh.wav", "frame": max(0, seg["startFrame"] - 8), "volume": 0.25})

    # Inserciones de B-roll sobre la voz en momentos clave (cada B-roll se usa una vez).
    overlays, pool, busy_until = [], list(b_roll), hook_end
    for cap in caps:
        if not pool or not cap["key"] or cap["start"] < busy_until or cap["start"] > cta_start - 1.5:
            continue
        br = pool.pop(0)
        dur = min(br["duration"] - 0.2, 2.4, cta_start - cap["start"])
        overlays.append({"src": f"media/clips/{name}/{br['file']}", "clip": br["id"],
                         "startFrame": round(cap["start"] * FPS), "durationFrames": round(dur * FPS),
                         "inFrame": round(0.1 * FPS)})
        busy_until = cap["start"] + dur + 2.0
        log.append(f"b-roll {br['id']} sobre \"{cap['text']}\"")

    speech = []
    for cap in caps:
        if speech and cap["start"] - speech[-1][1] < 0.4:
            speech[-1][1] = cap["end"]
        else:
            speech.append([cap["start"], cap["end"]])

    edit = {
        "fps": FPS, "width": 1080, "height": 1920, "durationInFrames": total_frames,
        "brand": cfg.get("brand", {}),
        "hook": {"text": cfg["hook"], "startFrame": 0, "endFrame": round(hook_end * FPS)},
        "cta": {"text": cfg["cta"], "sub": cfg.get("ctaSub", ""), "startFrame": round(cta_start * FPS),
                "endFrame": total_frames},
        "segments": segs, "overlays": overlays, "zooms": zooms, "transitions": transitions,
        "captions": [{k: c[k] for k in ("start", "end", "text", "key", "keyWords", "words")} for c in caps],
        "sfx": sorted(sfx, key=lambda s: s["frame"]),
        "music": {"src": "media/music/house-jazz.wav", "volume": cfg["musicVolume"],
                  "duckVolume": cfg["musicDuckVolume"], "speech": [[round(a, 3), round(b, 3)] for a, b in speech]},
        "log": log,
    }

    dst = ROOT / "public" / "media" / "clips" / name
    dst.mkdir(parents=True, exist_ok=True)
    used = {s["clip"] for s in segs} | {o["clip"] for o in overlays}
    for c in manifest["clips"]:
        if c["id"] in used:
            shutil.copy2(clips_dir / c["file"], dst / c["file"])
    (project / "edit.json").write_text(json.dumps(edit, indent=2, ensure_ascii=False))

    print(f"Duración: {total_frames / FPS:.1f}s  |  segmentos: {len(segs)}  |  subtítulos: {len(caps)}  |  "
          f"b-roll: {len(overlays)}  |  acercamientos: {len(zooms)}  |  transiciones: {len(transitions)}  |  "
          f"pausa máx.: {max_pause}s")
    for line in log:
        print("  -", line)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
