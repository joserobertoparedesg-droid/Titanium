import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import type { Brand } from "../types";

// Transición "cortina": dos franjas (vinotinto + beige) cruzan la pantalla y tapan el corte.
// Dura 14 frames centrados en el corte, así el audio sigue continuo y no se corta ninguna palabra.
export const WIPE_FRAMES = 14;

export const Wipe: React.FC<{ brand: Brand }> = ({ brand }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, WIPE_FRAMES], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  const pos = (lag: number) => interpolate(p, [0 + lag, 1], [110, -160], { extrapolateLeft: "clamp" });
  return (
    <AbsoluteFill style={{ overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          left: "-20%",
          width: "140%",
          height: "70%",
          top: `${pos(0.08)}%`,
          background: brand.beige,
          transform: "skewY(-8deg)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: "-20%",
          width: "140%",
          height: "60%",
          top: `${pos(0)}%`,
          background: brand.wine,
          transform: "skewY(-8deg)",
        }}
      />
    </AbsoluteFill>
  );
};
