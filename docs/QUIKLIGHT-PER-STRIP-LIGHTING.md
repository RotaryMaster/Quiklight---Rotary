# Per-strip lighting: v0.3.4.7 (experimental)

The baseline **v0.3.4.5 remains the maintainer-validated stable release on Bazzite KDE**. The v0.3.4.6 USB port binding/GUI changes are separate work. This document tracks an *uncompiled* source patch for v0.3.4.7; no Windows/Linux runtime validation or GitHub Release is claimed.

## Goals

- Keep per-**segment** source modes `independent`, `mirror`, `off` (mirror and off override the strip's selected lighting mode).
- Add per-**strip** lighting `inherit` (default), `static`, `dominant`, `dominant_lr`, `dominant_4`, `palette`, `effect`. No redundant per-strip edge-color mode: global screen mode remains available via `inherit`.
- A separate static RGB picker, effect name/speed/minimum, and up-to-10-color palette for each strip.
- `level_override`: bypass global software brightness and RGB-average power limit for only that strip, while keeping normal smoothing, rate limiting and temporal dithering. The power limit is **not** an electrical USB current measurement.
- Screen-derived per-strip modes must reuse the existing capture and adaptive color-fidelity path. Where the global source is static/effect, the capture portal might have to initialize for a strip using dominant/palette.
- Preserve physical LED indices, USB port bindings, QLV3 telemetry, KDE/Gamescope boot logic, and rollback.

## Proposed implementation

- Extend serde/TOML `StripProfile` with lighting and power fields, with defaults preserving older configs.
- Add `strip_override.rs` to produce per-strip logical RGB targets **before** output smoothing and HID physical mapping.
- Introduce per-device `output::Stage::step_by_strip` and retain the original `step` wrapper.
- Add a Qt group to the LEDs/Strips card; ensure saved presets and normalization preserve the new fields.
- Overlay only on an exact verified base; never replace HID `device.rs`, boot units, or Windows-specific code blindly.

## Validation checklist

- [ ] Rust `cargo check --locked`
- [ ] Rust `cargo test --locked`
- [ ] Rust `cargo build --release --locked`
- [ ] GUI installed in Bazzite and tested with two physical controllers
- [ ] Inherit reproduces v0.3.4.5 exactly
- [ ] Static/dominant/zones/palette/effect individually verified
- [ ] Per-device brightness and power limits independent from global values
- [ ] Per-segment mirror/off still have priority and preserve physical offsets
- [ ] Adaptive color fidelity remains active for screen-derived modes
- [ ] Hardware USB disconnect/reconnect, KDE ↔ Gamescope, boot and rollback tested
- [ ] Windows compile and real hardware validation completed before Windows release

**Source availability:** an experimental package was provided in the conversation; the complete reproducible QuikLight Rust project and external Qt helper modules are not yet published as a self-contained GitHub Release.

## v0.3.4.8 experimental extension — brightness per segment

Adds `intensity` (0–100%, default 100) to each `[[segment]]`, exposed through a slider in the existing LEDs/Strips segment card. It attenuates the final physical RGB frame *after* Independent/Mirror/Off mapping, so mirrored destination segments can be dimmed separately. Applied after global/per-strip brightness and power-limiting, therefore it **does not increase** output above existing limits. Existing scene color fidelity, smoothing and USB mapping remain in place. The GUI normalization and TOML saving preserve this field, including in presets. Unlike per-strip level overrides, this is a reduction-only control.

**Status:** patch prepared and Python syntax/structural checks passed; Rust compilation and physical device validation are outstanding. No stable-version promotion. The overlay must be built against the exact reviewed v0.3.4.7 sources, otherwise it aborts rather than rewriting current USB fixes. Windows is a target but unverified for this patch.
