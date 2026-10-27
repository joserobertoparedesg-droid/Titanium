import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { Brand } from "../types";

// Cierre: fondo vinotinto que sube como cortina y llamada a la acción en beige.
export const Cta: React.FC<{ text: string; sub?: string; brand: Brand }> = ({ text, sub, brand }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const curtain = spring({ frame, fps, config: { damping: 20, stiffness: 120 } });
  const txt = spring({ frame: frame - 8, fps, config: { damping: 15, stiffness: 160 } });
  const subIn = spring({ frame: frame - 18, fps, config: { damping: 18 } });
  const pulse = 1 + 0.025 * Math.sin(Math.max(0, frame - 30) / 6);

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `linear-gradient(170deg, ${brand.wine} 0%, ${brand.wineDark} 100%)`,
          transform: `translateY(${interpolate(curtain, [0, 1], [100, 0])}%)`,
        }}
      />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 90 }}>
        <div
          style={{
            width: interpolate(txt, [0, 1], [0, 120]),
            height: 4,
            background: brand.beige,
            borderRadius: 2,
            marginBottom: 40,
          }}
        />
        <div
          style={{
            fontFamily: brand.font,
            fontWeight: 800,
            fontSize: 86,
            lineHeight: 1.1,
            color: brand.beigeLight,
            textAlign: "center",
            opacity: txt,
            transform: `translateY(${interpolate(txt, [0, 1], [40, 0])}px) scale(${pulse})`,
          }}
        >
          {text}
        </div>
        {sub ? (
          <div
            style={{
              marginTop: 46,
              fontFamily: brand.font,
              fontWeight: 600,
              fontSize: 38,
              color: brand.wineDark,
              background: brand.beige,
              borderRadius: 999,
              padding: "16px 40px",
              opacity: subIn,
              transform: `translateY(${interpolate(subIn, [0, 1], [24, 0])}px)`,
            }}
          >
            {sub}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
