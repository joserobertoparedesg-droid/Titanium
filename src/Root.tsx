import React from "react";
import { Composition, type CalculateMetadataFunction } from "remotion";
import sample from "../projects/prueba/edit.json";
import { Reel } from "./Reel";
import type { EditProps } from "./types";

// La duración, tamaño y fps salen del edit.json que se pase con --props.
const calculateMetadata: CalculateMetadataFunction<EditProps> = ({ props }) => ({
  durationInFrames: props.durationInFrames,
  fps: props.fps,
  width: props.width,
  height: props.height,
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Reel"
    component={Reel}
    durationInFrames={sample.durationInFrames}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={sample as unknown as EditProps}
    calculateMetadata={calculateMetadata}
  />
);
