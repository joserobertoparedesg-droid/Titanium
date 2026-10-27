export type Brand = {
  font: string;
  wine: string;
  wineDark: string;
  beige: string;
  beigeLight: string;
};

export type Word = { text: string; start: number; end: number };

export type Caption = {
  start: number;
  end: number;
  text: string;
  key: boolean;
  keyWords: number[];
  words: Word[];
};

export type Segment = {
  clip: string;
  src: string;
  inFrame: number;
  outFrame: number;
  startFrame: number;
  durationFrames: number;
  text: string;
};

export type Overlay = {
  clip: string;
  src: string;
  startFrame: number;
  durationFrames: number;
  inFrame: number;
};

export type EditProps = {
  fps: number;
  width: number;
  height: number;
  durationInFrames: number;
  brand: Partial<Brand>;
  hook: { text: string; startFrame: number; endFrame: number };
  cta: { text: string; sub?: string; startFrame: number; endFrame: number };
  segments: Segment[];
  overlays: Overlay[];
  zooms: { frame: number; durationFrames: number }[];
  transitions: { frame: number; type: "wipe" }[];
  captions: Caption[];
  sfx: { src: string; frame: number; volume: number }[];
  music: { src: string; volume: number; duckVolume: number; speech: [number, number][] };
  log?: string[];
};

export const DEFAULT_BRAND: Brand = {
  font: "Montserrat",
  wine: "#6B1E2E",
  wineDark: "#3E0F19",
  beige: "#E8DCC4",
  beigeLight: "#F7F1E6",
};
