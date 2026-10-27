Cada carpeta es un proyecto: `config.json` (instrucciones) + `edit.json` (edición generada y editable).
Claves de `config.json`: `hook`, `cta`, `ctaSub`, `targetSeconds`, `corrections` {"texto mal": "texto bien"},
`keyTerms` [lista], `exclude` [ids de clip], `order` [ids], `maxPause`, `keepPause`, `padBefore`, `padAfter`,
`musicVolume`, `musicDuckVolume`, `clickVolume`, `dingVolume`, `brand` {font, wine, wineDark, beige, beigeLight}.
Los valores por defecto están en `DEFAULTS` dentro de `scripts/build_edit.py`.
