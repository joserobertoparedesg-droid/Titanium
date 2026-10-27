import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand, Caption } from "../types";

// Subtítulos dinámicos centrados: entran con un pequeño "pop", la palabra que se está
// diciendo se resalta, y las palabras de información clave van en una píldora vinotinto.
export const Captions: React.FC<{
  captions: Caption[];
  brand: Brand;
  hideBefore: number;
  hideAfter: number;
}> = ({ captions, brand, hideBefore, hideAfter }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const cap = captions.find((c) => t >= c.start && t < c.end);
  if (!cap || t < hideBefore || t >= hideAfter) return null;

  const inF = frame - Math.round(cap.start * fps);
  const pop = spring({ frame: inF, fps, config: { damping: 14, stiffness: 220, mass: 0.6 } });
  const y = interpolate(pop, [0, 1], [26, 0]);
  const scale = interpolate(pop, [0, 1], [0.86, 1]);

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: "0 90px" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignItems: "center",
          columnGap: 16,
          rowGap: 8,
          maxWidth: 860,
          padding: "14px 26px 18px",
          borderRadius: 22,
          background: "rgba(30, 8, 14, 0.42)",
          backdropFilter: "blur(6px)",
          transform: `translateY(${y}px) scale(${scale})`,
          opacity: Math.min(1, pop * 1.4),
        }}
      >
        {cap.words.map((w, i) => {
          const spoken = t >= w.start - 0.04;
          const active = t >= w.start - 0.04 && t < w.end + 0.05;
          const isKey = cap.keyWords.includes(i);
          const wf = frame - Math.round(w.start * fps);
          const wPop = isKey ? spring({ frame: wf, fps, config: { damping: 12, stiffness: 260 } }) : 1;
          return (
            <span
              key={i}
              style={{
                fontFamily: brand.font,
                fontWeight: isKey ? 800 : 700,
                fontSize: isKey ? 66 : 60,
                lineHeight: 1.12,
                letterSpacing: isKey ? 0.5 : 0,
                color: isKey ? brand.beigeLight : active ? brand.beige : "#FFFFFF",
                opacity: spoken ? 1 : 0.72,
                padding: isKey ? "4px 18px 8px" : "0",
                borderRadius: 14,
                background: isKey ? brand.wine : "transparent",
                boxShadow: isKey ? "0 10px 30px rgba(0,0,0,0.35)" : "none",
                transform: `scale(${isKey ? interpolate(wPop, [0, 1], [0.8, 1]) : active ? 1.06 : 1})`,
                textShadow: isKey ? "none" : "0 3px 14px rgba(0,0,0,0.65), 0 1px 3px rgba(0,0,0,0.6)",
                WebkitTextStroke: isKey ? "0" : "1.5px rgba(0,0,0,0.25)",
                display: "inline-block",
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
