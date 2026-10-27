import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Montserrat empaquetada localmente (public/fonts): el render no depende de internet.
const WEIGHTS = ["500", "600", "700", "800"];

export const fontsReady = Promise.all(
  WEIGHTS.map((weight) =>
    loadFont({
      family: "Montserrat",
      url: staticFile(`fonts/montserrat-latin-${weight}-normal.woff2`),
      weight,
    }),
  ),
);
