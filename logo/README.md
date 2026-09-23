# Logo

`make_logo.py` is the source of the logo; every file that carries it is
generated. After changing it:

```bash
python logo/make_logo.py
```

That rewrites the SVGs and the Android adaptive icon. The PNGs are then
rasterised from `simorgh-icon.svg` (any renderer that keeps the rounded
corners transparent will do; headless Chrome with
`--default-background-color=00000000` is what was used):

- a 1024px PNG, passed to `npx tauri icon <png>` from `gui/`, which
  regenerates `gui/src-tauri/icons/` (delete the `android/` and `ios/`
  folders it also creates -- the Android app has its own icons);
- 48, 72, 96, 144 and 192px PNGs, copied to
  `android/app/src/main/res/mipmap-{mdpi,hdpi,xhdpi,xxhdpi,xxxhdpi}/ic_launcher.png`.
  These only show on Android 7.x; newer versions use the adaptive icon.

Gold `#e2b766` on `#0f0d0a`.
