import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Captions } from "./components/Captions";
import { Cta } from "./components/Cta";
import { Hook } from "./components/Hook";
import { WIPE_FRAMES, Wipe } from "./components/Wipe";
import { fontsReady } from "./fonts";
import { DEFAULT_BRAND, type EditProps } from "./types";

const AUDIO_FADE = 3; // frames de micro-fundido en cada corte de voz (evita "clics" sin comerse sílabas)
const ZOOM_IN = 8;
const ZOOM_OUT = 12;
const ZOOM_AMOUNT = 0.12;

const zoomAt = (frame: number, zooms: EditProps["zooms"]) =>
  zooms.reduce((acc, z) => {
    const local = frame - z.frame;
    if (local < 0 || local > z.durationFrames + ZOOM_OUT) return acc;
    const up = interpolate(local, [0, ZOOM_IN], [0, 1], {
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    const down = interpolate(local, [z.durationFrames, z.durationFrames + ZOOM_OUT], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.inOut(Easing.cubic),
    });
    return acc + ZOOM_AMOUNT * Math.min(up, down);
  }, 0);

const musicVolume = (t: number, total: number, m: EditProps["music"]) => {
  // "Ducking": la música baja mientras hay voz y sube suavemente en las pausas.
  const RAMP = 0.3;
  let dist = Infinity;
  for (const [a, b] of m.speech) {
    if (t >= a && t <= b) {
      dist = 0;
      break;
    }
    dist = Math.min(dist, t < a ? a - t : t - b);
  }
  const k = Math.min(1, dist / RAMP);
  const v = m.duckVolume + (m.volume - m.duckVolume) * k;
  const fadeIn = Math.min(1, t / 0.6);
  const fadeOut = Math.min(1, Math.max(0, (total - t) / 1.5));
  return v * fadeIn * fadeOut;
};

export const Reel: React.FC<EditProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const brand = { ...DEFAULT_BRAND, ...props.brand };
  const [handle] = useState(() => delayRender("Cargando Montserrat"));
  useEffect(() => {
    fontsReady.then(() => continueRender(handle)).catch((e) => {
      console.error(e);
      continueRender(handle);
    });
  }, [handle]);

  const scale = 1 + zoomAt(frame, props.zooms);
  const hookEnd = props.hook.endFrame / fps;
  const ctaStart = props.cta.startFrame / fps;
  const progress = frame / durationInFrames;

  return (
    <AbsoluteFill style={{ backgroundColor: brand.wineDark }}>
      {/* Capa de video principal (A-roll) con acercamientos en la información clave */}
      <AbsoluteFill style={{ transform: `scale(${scale})` }}>
        {props.segments.map((s, i) => (
          <Sequence key={i} from={s.startFrame} durationInFrames={s.durationFrames} name={`${s.clip} · ${s.text.slice(0, 24)}`}>
            {s.kind === "image" ? (
              <Photo src={s.src} duration={s.durationFrames} motion={s.motion ?? i} />
            ) : (
              <SegmentVideo src={s.src} trimBefore={s.inFrame} duration={s.durationFrames} />
            )}
          </Sequence>
        ))}
      </AbsoluteFill>

      {/* B-roll sobre la voz (sin audio), con Ken Burns suave */}
      {props.overlays.map((o, i) => (
        <Sequence key={`o${i}`} from={o.startFrame} durationInFrames={o.durationFrames} name={`B-roll ${o.clip}`}>
          <BRoll src={o.src} kind={o.kind} trimBefore={o.inFrame} duration={o.durationFrames} />
        </Sequence>
      ))}

      {/* Viñeta sutil para legibilidad del texto */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, rgba(0,0,0,0.0) 35%, rgba(0,0,0,0.38) 100%), linear-gradient(180deg, rgba(0,0,0,0) 30%, rgba(0,0,0,0.18) 50%, rgba(0,0,0,0) 70%)",
        }}
      />

      <Captions captions={props.captions} brand={brand} hideBefore={hookEnd} hideAfter={ctaStart} />

      {props.transitions.map((tr, i) => (
        <Sequence key={`t${i}`} from={tr.frame - WIPE_FRAMES / 2} durationInFrames={WIPE_FRAMES} name="Transición">
          <Wipe brand={brand} />
        </Sequence>
      ))}

      <Sequence from={props.hook.startFrame} durationInFrames={props.hook.endFrame - props.hook.startFrame} name="Gancho">
        <Hook text={props.hook.text} brand={brand} position={props.hook.position} eyebrow={props.hook.eyebrow} durationFrames={props.hook.endFrame - props.hook.startFrame} />
      </Sequence>

      <Sequence from={props.cta.startFrame} name="Llamada a la acción">
        <Cta text={props.cta.text} sub={props.cta.sub} brand={brand} />
      </Sequence>

      {/* Barra de progreso minimalista */}
      <AbsoluteFill>
        <div style={{ position: "absolute", top: 0, left: 0, height: 8, width: `${progress * 100}%`, background: brand.beige, opacity: 0.85 }} />
      </AbsoluteFill>

      {/* Audio: música con ducking + efectos */}
      <Audio
        src={staticFile(props.music.src)}
        loop
        volume={(f) => musicVolume(f / fps, durationInFrames / fps, props.music)}
      />
      {props.sfx.map((s, i) => (
        <Sequence key={`s${i}`} from={s.frame} durationInFrames={Math.round(fps * 1.3)} name="SFX">
          <Audio src={staticFile(s.src)} volume={s.volume} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const SegmentVideo: React.FC<{ src: string; trimBefore: number; duration: number }> = ({ src, trimBefore, duration }) => {
  const frame = useCurrentFrame();
  const push = interpolate(frame, [0, duration], [1, 1.035]);
  return (
    <AbsoluteFill style={{ transform: `scale(${push})` }}>
      <OffthreadVideo
        src={staticFile(src)}
        trimBefore={trimBefore}
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
        volume={(f) =>
          Math.min(1, interpolate(f, [0, AUDIO_FADE], [0, 1], { extrapolateRight: "clamp" }),
            interpolate(f, [duration - AUDIO_FADE, duration], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))
        }
      />
    </AbsoluteFill>
  );
};

// Foto con movimiento de cámara suave (acercar/alejar + desplazamiento lateral alterno).
const Photo: React.FC<{ src: string; duration: number; motion: number }> = ({ src, duration, motion }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, duration], [0, 1], { easing: Easing.inOut(Easing.sin) });
  const zoomIn = motion % 2 === 0;
  const scale = zoomIn ? 1.0 + 0.09 * p : 1.09 - 0.09 * p;
  const dx = (motion % 4 < 2 ? 1 : -1) * interpolate(p, [0, 1], [-18, 18]);
  return (
    <AbsoluteFill style={{ transform: `scale(${scale}) translateX(${dx}px)` }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    </AbsoluteFill>
  );
};

const BRoll: React.FC<{ src: string; kind?: "video" | "image"; trimBefore: number; duration: number }> = ({
  src,
  kind,
  trimBefore,
  duration,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 6, duration - 6, duration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [0, duration], [1.12, 1.0]);
  return (
    <AbsoluteFill style={{ opacity, transform: `scale(${scale})` }}>
      {kind === "image" ? (
        <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : (
        <OffthreadVideo src={staticFile(src)} trimBefore={trimBefore} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      )}
    </AbsoluteFill>
  );
};
