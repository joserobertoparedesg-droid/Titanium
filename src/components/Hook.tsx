import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand } from "../types";

// Gancho inicial: tarjeta beige con texto vinotinto, palabras escalonadas.
export const Hook: React.FC<{ text: string; brand: Brand; durationFrames: number }> = ({
  text,
  brand,
  durationFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");
  const enter = spring({ frame, fps, config: { damping: 16, stiffness: 140 } });
  const exit = interpolate(frame, [durationFrames - 8, durationFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const line = interpolate(frame, [6, 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: exit }}>
      <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(0,0,0,0.05), ${brand.wineDark}99)` }} />
      <div
        style={{
          background: brand.beigeLight,
          borderRadius: 28,
          padding: "46px 54px 50px",
          maxWidth: 900,
          transform: `translateY(${interpolate(enter, [0, 1], [60, 0])}px) scale(${interpolate(enter, [0, 1], [0.92, 1])})`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.35)",
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontFamily: brand.font,
            fontWeight: 600,
            fontSize: 30,
            letterSpacing: 8,
            color: brand.wine,
            marginBottom: 18,
            opacity: line,
          }}
        >
          EN VENTA
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", columnGap: 18 }}>
          {words.map((w, i) => {
            const s = spring({ frame: frame - 4 - i * 3, fps, config: { damping: 14, stiffness: 200 } });
            return (
              <span
                key={i}
                style={{
                  fontFamily: brand.font,
                  fontWeight: 800,
                  fontSize: 84,
                  lineHeight: 1.08,
                  color: brand.wine,
                  display: "inline-block",
                  opacity: s,
                  transform: `translateY(${interpolate(s, [0, 1], [30, 0])}px)`,
                }}
              >
                {w}
              </span>
            );
          })}
        </div>
        <div
          style={{
            height: 5,
            width: `${line * 160}px`,
            background: brand.wine,
            borderRadius: 3,
            margin: "26px auto 0",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
