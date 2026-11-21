# QuikLight v0.3.5.0 — individual lighting mode per LED segment

**Status:** experimental source overlay; **not a validated stable release**. Python source syntax, segment-normalization preservation and ZIP-integrity checks passed; Rust compilation and physical USB/LED testing on Bazzite KDE are pending. Windows is an intended target but untested.

## Baseline

Patch is **based on v0.3.4.9 consolidated Rust sources**. The preparer audits source hashes including its native USB identity and HID reconnection workers. It overlays only `main.rs`, `config.rs`, `multi_strip.rs` and new `segment_override.rs`. It leaves `device.rs`, `hid_workers.rs`, monitor/capture, protocol, systemd, KDE boot, Gamescope and USB bindings unchanged.

## Hierarchy and per-segment selectors

`Global mode -> Per-strip mode -> Per-segment mode -> Per-segment attenuation -> Hardware mapping`

Each segment retains the independent **physical source** selector `independent | mirror | off`. Mirror and Off always win. For an Independent segment, `lighting_mode` defaults to `inherit`; optional overrides are `static`, `dominant`, `dominant_lr`, `dominant_4`, `palette`, `effect`, `music`.

New segment TOML fields: `lighting_mode`, `static_r/g/b`, `effect`, `effect_speed`, `effect_min`, `palette`, `music_band`, `music_style`, `music_sens`. Existing `intensity` (0..100) remains post-mirror in the final physical output. Older configurations inherit strip lighting by default. GUI keeps new fields through normalization and writes them to configuration/presets. `quiklight --save` was extended to persist these fields too.

Segment music initially supports independent **Dim/Boost**, band (bass/treble/volume/RPM) and sensitivity. The 22 global music effects remain unchanged but are not yet offered as 22 independent per-segment effects. Mixed scene-derived modes reuse the existing color-fidelity-aware capture path. A second capture can be needed when global mode is non-screen and a segment needs screen colors.

## Test stages

1. Extract the private conversation ZIP `QuikLight-v0350-Modos-Por-Trecho-EXPERIMENTAL.zip` to Downloads; no GitHub Release is claimed.
2. Run `python3 verificar.py` and `python3 preparar.py --audit` against `~/Projetos/QuikLight-MultiStrip-Builds/v0349-consolidado/rust`.
3. Run `python3 preparar.py --prepare` to do `cargo check --locked`, `cargo test --locked`, `cargo build --release --locked` in a **new isolated directory**.
4. Only after BUILD OK: `python3 instalar.py --audit`; review all hashes, USB bindings, known installed GUI and systemd ExecStart. Installer requires explicit confirmation, backup, rollback and leaves systemd/boot/Gamescope files untouched.
5. Validate physical static/dominant/effects/palette/music per segment, inheritance, mirror/off priority, segment intensity, real-time config, both USB ports, detach/reattach, KDE↔Gamescope, capture fidelity and white-flash observations.
6. Update status and promote to stable **only** after user confirmation.

[README](../README.md) · [v0.3.4.9 consolidation](QUIKLIGHT-V0349-CONSOLIDATION.md) · [GUI organization](QUIKLIGHT-GUI-ORGANIZATION.md).
