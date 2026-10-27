import { Config } from "@remotion/cli/config";
import fs from "node:fs";

// remotion.media (descarga del navegador de Remotion) no es accesible desde este entorno:
// se usa el chrome-headless-shell que trae Playwright si existe.
const HEADLESS = "/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell";
const browser = process.env.REMOTION_BROWSER ?? (fs.existsSync(HEADLESS) ? HEADLESS : null);
if (browser) Config.setBrowserExecutable(browser);

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setCodec("h264");
Config.setCrf(18);
Config.setPixelFormat("yuv420p");
Config.setOverwriteOutput(true);
Config.setConcurrency(4);
