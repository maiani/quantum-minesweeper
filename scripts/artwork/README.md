# Artwork generators

`generate.py` is the editable source for the game mark and derived icon set.
Run `pixi run icons` after changing it; `--check` verifies that every tracked
SVG and PNG still matches the source.

Store-only outputs live under `artwork/mobile/`; PWA-consumed outputs stay under
`src/qminesweeper/static/icons/` so the wheel and browser bundle do not carry
unused native resources.

- `app-icon.svg` and `app-icon-1024.png`: opaque, mask-safe mobile
  master suitable for an iOS asset catalog.
- `play-store-icon-512.png`: full-square Google Play listing artwork.
- `android/{foreground,background,monochrome}.{svg,png}`: separate 108 dp
  adaptive-icon layers, rasterized at 4x where applicable.
- `icon-maskable-{192,512}.png`: maskable PWA icons referenced by the manifest.
- `apple-touch-icon-180.png`: iOS Home Screen web-app icon.
- `mask-preview.{svg,png}`: circle, squircle, and rounded-square crop checks.

Platform tooling may copy these files into Android or Xcode projects later. Do
not introduce platform-owned masks, rounded corners, or shadows into the source:
the operating system supplies those treatments.
