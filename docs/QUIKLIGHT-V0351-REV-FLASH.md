# QuikLight v0.3.5.1 — REV Simracing, desktop alerts and white-flash diagnostics

**Status, 2026-11-21:** QuikLight v0.3.5.0 is the most recent **maintainer-confirmed functional Linux/Bazzite KDE installation**. v0.3.5.1 is an **experimental source overlay** delivered in the project conversation. Python syntax, QLV3 parser and ZIP integrity were checked; Rust compilation, desktop display, physical LED testing and Windows are **not yet validated**. No binary release has been published.

## Changes staged for testing

- Rename the existing `music_style="rev"` UI item to **MODO REV Simracing**; preserve the underlying TOML key and all global music styles.
- Per-segment music supports **Solid RGB** or **Screen RGB** (new `music_color_source=static|screen`, default `static`), preserving other physical segment modes and offsets. Dynamic source works when the global mode is static: the existing capturer is activated as needed.
- Per-segment REV uses the existing **audio-derived** estimated RPM (not game telemetry), smooths short spikes and produces a progressive LED bar: solid source = green/amber/red; screen source = retain capture colors. No intentional full-white gear-shift pulse. Its aggregate RGB levels cannot exceed the already limited Stage input.
- A persistent **Recent Alerts** panel on Home, rate-limited desktop tray notifications (if supported), and existing service logs on KDE/Windows. The global REV algorithm is not silently changed because the original `music.rs` was not available in the reviewed source overlay.
- Original color calibration defaults restored via dedicated action: saturation 1.4, gamma 1.2, contrast 1.0, gain R/G/B 1.0 and channel gammas 1.0. A neutral-white default selectable profile and reset command. Baseline confirmed against [upstream source](https://github.com/Kevinsillo/quiklight-x11/blob/main/src/config.rs) / [sample config](https://github.com/Kevinsillo/quiklight-x11/blob/main/config.toml). Only calibration resets; physical segment maps are preserved.
- App name/window/tray tooltip **Quicklight GUI**, tray menu **Sair** only. Existing Quit behavior and KDE/Gamescope startup commands remain unchanged.
- Read-only `diagnostico_flash.py` to correlate QLV3 software RGB frames with manually timestamped physical flashes and service logs. It does not write HID data or modify the base OS.

## Simulation telemetry — reuse existing tools

### Best candidates

- **[SimHub](https://www.simhubdash.com/supported-games/)** (Windows): large supported-game list; can be a future source through a documented adapter. Confirm available export protocol and licensing before integration.
- **[simbridge](https://github.com/Carlos-Diaz-07/simbridge)** (Linux Proton): Windows shim inside game's prefix sends shared-memory telemetry over UDP to a native Linux process. ACC is marked tested; other game adapters may be untested. Don't assume broad reliable coverage.
- **[OpenRacing](https://github.com/EffortlessMetrics/OpenRacing)** (Rust, cross-platform): researched adapter set for many games; its documentation explicitly distinguishes scaffolding from end-to-end tested adapters.
- **[RaceHUD](https://github.com/Pasblinn/racehud)** (Rust, Linux + Windows): shows shift lights and RPM for AMS2/Le Mans Ultimate, useful reference for light thresholds and UDP formats.
- **[racetelemetry](https://github.com/vitalvas/racetelemetry)**: source/sink pipeline, normalized telemetry output; inspect individual games and supported source types.

### Proposed protocol (not yet implemented)

Introduce a **separate optional input adapter** rather than coupling the HID Rust driver to each game: `{game, rpm, max_rpm, gear, shift_indicator, timestamp}` received via loopback UDP or shared-memory adapter. Validate units and data freshness (e.g. expiry after 500 ms), automatically fall back to audio if data stops, and only then apply a platform-independent progressive REV LED renderer. Never claim an audio FFT is real engine RPM. Existing modes, static/screen color source, per-segment brightness, and Gamescope should be unaffected.

## White flashes: unresolved

The user reports recurrent **brief white flashes, especially while typing on a dark ChatGPT page**, and a more noticeable issue with two controllers. This predates MultiStrip. Possible mechanisms to **test, not assume**:

- GUI capture/edge sampler briefly receiving bright frame/cursor/text or an incorrect RGB sample
- Global music style `flash` intentionally pulsing white
- HID frame writes, controller firmware or USB disconnect/reinitialize transition
- Electrical power/signal integrity, made more visible when both strips run

The QLV3 packet reports prepared physical RGB before successful USB acknowledgement. If software reports a bright frame in temporal proximity to the flash, investigate capture/style/sampling. If software remains dark but hardware flashes, prioritize HID/write pacing, controller reset/firmware and electrical measurements. Even this evidence is not definitive: QLV3 is sampled ~10Hz and may miss brief transitions.

### Pending verification

- [ ] `python3 verificar.py`, `python3 preparar.py --audit`, `python3 preparar.py --prepare` — on Bazzite
- [ ] `cargo check --locked`, `cargo test --locked`, `cargo build --release --locked`
- [ ] Installer audit and GUI close, then opt-in install with backup and rollback
- [ ] Physical behavior in per-segment Solid/Screen + REV, FPS stability and USB port binding
- [ ] Calibrate only selected group, confirm no physical map changes
- [ ] Home persistent alerts/tray notifications and icon labels
- [ ] Correlate at least 3 physical white flashes using QLV3 CSV + journal
- [ ] Validate Windows separately before matching compatibility claims

**Never replace v0.3.5.0 stable automatically**. Preserve systemd user units, preexisting fast-Gamescope/session-guard drop-ins, all USB bindings and the immutable system.
