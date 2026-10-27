#!/usr/bin/env python3
"""Sintetiza música y efectos de sonido ORIGINALES (generados por código, sin muestras de
terceros): uso libre, sin problemas de derechos de autor.

- music/house-jazz.wav : house jazz elegante y tranquilo (~118 BPM), piano eléctrico con
  acordes de 9na/13va, bajo cálido, bombo suave, hi-hats, ligero "pumping".
- sfx/ding.wav, sfx/click.wav, sfx/whoosh.wav

Uso: python3 scripts/make_audio_assets.py <carpeta_public_media> [--seconds 60] [--seed 7]
"""
import argparse
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 44100


def lp(x, hz, order=2):
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.2, hold=None):
    hold = n / SR if hold is None else hold
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, 1.0)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / d, e)
    e = np.where((t >= a + d) & (t < hold), s, e)
    e = np.where(t >= hold, s * np.exp(-(t - hold) / max(r, 1e-3)), e)
    return e


def epiano(freq, dur, vel=1.0):
    """Piano eléctrico tipo Rhodes por FM simple + trémolo."""
    n = int(SR * (dur + 0.8))
    t = np.arange(n) / SR
    idx = 1.6 * np.exp(-t * 6) + 0.25
    mod = np.sin(2 * np.pi * freq * t) * idx
    tone = np.sin(2 * np.pi * freq * t + mod) + 0.12 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t * 18)
    e = env_adsr(n, a=0.004, d=0.6, s=0.35, r=0.35, hold=dur)
    trem = 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return tone * e * trem * vel


def bass(freq, dur, vel=1.0):
    n = int(SR * (dur + 0.1))
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t)
    x = np.tanh(1.6 * x)
    return lp(x * env_adsr(n, a=0.006, d=0.15, s=0.7, r=0.06, hold=dur) * vel, 900)


def kick():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t * 35)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) + 0.04 * lp(np.random.randn(n), 3000) * np.exp(-t * 80)


def hat(rng, open_=False):
    n = int(SR * (0.18 if open_ else 0.045))
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000, 4) * np.exp(-t * (18 if open_ else 90))


def rim(rng):
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 60)
    snap = bp(rng.standard_normal(n), 1500, 5000) * np.exp(-t * 45)
    return 0.4 * body + 0.6 * snap


def place(buf, x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= buf.shape[1]:
        return
    x = x[: buf.shape[1] - i]
    buf[0, i:i + len(x)] += x * gain * np.sqrt(0.5 * (1 - pan))
    buf[1, i:i + len(x)] += x * gain * np.sqrt(0.5 * (1 + pan))


def make_music(seconds: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    bpm = 118
    beat = 60 / bpm
    bar = 4 * beat
    # ii-V-I-vi en Re mayor con tensiones: Em9 - A13 - Dmaj9 - Bm11
    chords = [
        (52, [55, 59, 62, 66]),   # Em9: G B D F#
        (45, [55, 59, 61, 66]),   # A13: G B C# F#
        (50, [54, 57, 61, 64]),   # Dmaj9: F# A C# E
        (47, [54, 57, 62, 64]),   # Bm11: F# A D E
    ]
    n = int(SR * (seconds + 2))
    drums = np.zeros((2, n))
    keys = np.zeros((2, n))
    low = np.zeros((2, n))
    pad = np.zeros((2, n))
    k = kick()
    bars = int(seconds / bar) + 1
    for b in range(bars):
        t0 = b * bar
        root, notes = chords[b % 4]
        intro = b < 2
        # Batería: bombo en negras (desde el compás 2), rim en 2 y 4, hats a contratiempo.
        for q in range(4):
            tq = t0 + q * beat
            if not intro:
                place(drums, k, tq, 0.55)
            place(drums, hat(rng, open_=(q % 2 == 1)), tq + beat / 2, 0.10 + 0.03 * rng.random(), 0.25)
            for s16 in (0.25, 0.75):
                place(drums, hat(rng), tq + beat * s16, 0.035, -0.3)
            if q in (1, 3) and not intro:
                place(drums, rim(rng), tq, 0.10, -0.15)
        # Piano eléctrico: patrón sincopado típico de house con voicings abiertos.
        for off, length, vel in ((0.0, 0.9, 0.9), (1.5, 0.4, 0.6), (2.5, 1.3, 0.75)):
            for j, nt in enumerate(notes):
                place(keys, epiano(midi(nt), length * beat, vel * (0.9 - 0.08 * j)),
                      t0 + off * beat + j * 0.006, 0.11, (-0.35 + 0.23 * j))
        # Bajo: tónica sincopada + aproximación cromática al acorde siguiente.
        nxt = chords[(b + 1) % 4][0]
        for off, length, nt in ((0.0, 0.7, root), (1.5, 0.4, root + 12), (2.0, 0.7, root),
                                (3.5, 0.4, nxt + (1 if nxt < root else -1))):
            if not intro:
                place(low, bass(midi(nt - 12), length * beat), t0 + off * beat, 0.38)
        # Pad cálido muy bajo.
        tt = np.arange(int(SR * bar)) / SR
        p = sum(np.sin(2 * np.pi * midi(nt) * tt * (1 + 0.002 * (j - 1.5))) for j, nt in enumerate(notes))
        p = lp(p * env_adsr(len(tt), a=0.8, d=0.5, s=0.8, r=0.6, hold=bar - 0.4), 1600)
        place(pad, p, t0, 0.022, 0.0)

    # "Pumping" sutil (sidechain) para dar movimiento.
    t = np.arange(n) / SR
    ph = (t % beat) / beat
    pump = 1 - 0.32 * np.exp(-ph * 9) * (t > 2 * bar)
    mix = drums + (keys + pad) * pump + low * (0.6 + 0.4 * pump)
    mix = lp(mix, 9000)
    # Filtro que se abre en la introducción + fade in/out.
    fade_in = np.clip(t / 1.5, 0, 1)
    fade_out = np.clip((seconds - t) / 3.0, 0, 1)
    mix *= fade_in * fade_out
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    mix /= np.max(np.abs(mix)) + 1e-9
    return (mix * 0.89)[:, : int(SR * seconds)]


def make_ding():
    n = int(SR * 1.2)
    t = np.arange(n) / SR
    f = 1318.5  # Mi6
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t * 4.5)
         + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 9)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 16))
    x *= np.clip(t / 0.002, 0, 1)
    return np.stack([x, x]) / np.max(np.abs(x)) * 0.8


def make_click(rng):
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    x = bp(rng.standard_normal(n), 1800, 6500, 2) * np.exp(-t * 260)
    x += 0.5 * np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 400)
    x2 = np.zeros(n)
    d = int(SR * 0.018)  # segundo "tic" del botón al soltar
    x2[d:] = 0.45 * x[: n - d]
    y = x + x2
    return np.stack([y, y]) / np.max(np.abs(y)) * 0.7


def make_whoosh(rng):
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    hop = 512
    for i in range(0, n, hop):  # barrido de filtro pasa-banda 300 Hz -> 4 kHz
        c = 300 * (4000 / 300) ** (i / n)
        seg = bp(noise[max(0, i - 2048): i + hop], c * 0.7, min(c * 1.4, 20000))
        out[i:i + hop] = seg[-len(out[i:i + hop]):]
    e = np.sin(np.pi * np.clip(t / 0.6, 0, 1)) ** 2
    y = out * e
    return np.stack([y * 0.9, y]) / np.max(np.abs(y)) * 0.6


def save(path: Path, x: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, SR, (np.clip(x.T, -1, 1) * 32767).astype(np.int16))
    print(f"  {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    save(a.out / "music" / "house-jazz.wav", make_music(a.seconds, a.seed))
    save(a.out / "sfx" / "ding.wav", make_ding())
    save(a.out / "sfx" / "click.wav", make_click(rng))
    save(a.out / "sfx" / "whoosh.wav", make_whoosh(rng))


if __name__ == "__main__":
    main()
