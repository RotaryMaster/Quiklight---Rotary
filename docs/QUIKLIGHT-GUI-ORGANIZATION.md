# QuikLight MultiStrip — organized LEDs & Strips GUI (v0.3.4.9 UI patch)

**Status:** GUI-only experiment, Python syntax and structural checks passed; **not visually or physically validated** on the maintainer's Bazzite KDE.

## Motivation

At a normal desktop window size, the existing LEDs & Strips page combines every physical segment into a long three-row horizontal control area and separates segment settings from per-strip lighting, USB information and calibration. This makes options difficult to find and hard to use on narrower KDE windows.

## UI layout

- **Fita 1 / Fita 2** tabs; each displays per-strip lighting and only the relevant physical segments.
- Compact segment card shows **edge + physical LED range**, enabled toggle, Independent/Mirror/Off selector and **intensity 0–100%** slider.
- **Mirror source only appears for the Mirror selection**, not as an inert dropdown for Independent.
- **More options** expands existing source device, edge selection, LED count, reverse direction, reorder and remove controls.
- Per-strip static RGB/effect/palette fields are shown only when that lighting mode is selected.
- USB port history, binding confirmation, RGB gains and strip presets are retained in an expandable **USB, calibration and presets** section.
- Global RGB/gamma calibration and ready-made layout presets are accessible via collapsible sections.

## Safety

The package is an overlay of the exact GUI from v0.3.4.8/v0.3.4.9 with SHA-256 `f6961762638f146b5e35fdfb64b76c020288757d066375f090d32b7eb26fff4f`. The installer checks this original hash, backs up the GUI and updates **only** `~/.local/share/quiklight-gui-qt/quiklight_gui.py`. It does not stop or replace the Rust service, modify `config.toml`, change USB binding, startup, KDE/Gamescope settings, or immutable base files. No override is provided for an unrecognized current GUI.

The patch retains all 130 existing class methods and adds a UI disclosure helper; tested with Python AST and py_compile. **Qt runtime screenshot/testing remains pending because Qt/PySide6 was not available in the build environment.**

## Acceptance before stable classification

- [ ] GUI displays cleanly in 1360×768 and 1920×1080 layouts
- [ ] Two tabs and USB status show correct physical controller bindings
- [ ] Independente/Mirror/Off update in real time, including mirror source picker
- [ ] Segment intensity updates in real time and Off stays black
- [ ] Each per-strip static/dominant/palette/effect and brightness override remains functional
- [ ] All existing advanced options, presets, RGB calibration and layout presets preserved
- [ ] No regressions during controller reconnect, KDE login, Gamescope transitions
- [ ] Installer backup and rollback function correctly
- [ ] Windows GUI compatibility tested separately

No GitHub binary release is claimed. Linux v0.3.4.5 remains the last fully validated stable reference until the consolidated v0.3.4.9 is tested on the target hardware.
