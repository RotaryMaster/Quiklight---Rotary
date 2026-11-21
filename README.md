# QuikLight — RotaryMaster fork

**Supported UI languages:** 🇺🇸 English · 🇧🇷 Português (Brasil) · 🇪🇸 Español. The interface has selectable translations; coverage may vary by page.

**Target operating systems:** **Linux (Bazzite KDE / Wayland)** and **Windows**. Both are part of the project's intended scope, but they do **not** currently have identical validated feature coverage.

> **Stable reference, verified by maintainer on Bazzite KDE:** **MultiStrip v0.3.5.0** (21 November 2026). The maintainer confirmed the consolidated two-controller setup, native USB reconnect, per-strip lighting and per-segment lighting are functioning. This is **not** a verified Windows release, nor proof of compatibility with every HID controller.
>
> **Windows latest verified version:** **not yet established for the v0.3.4.x MultiStrip series**. Windows support has code paths and dedicated experimental branches; build, setup and actual hardware behavior require separate validation. Do not treat v0.3.4.5 Linux as a Windows release.

## Overview and origins

QuikLight is an ambient LED lighting application inspired by and developed from the upstream **quiklight-x11** project. This is the **RotaryMaster fork**, evolving the Rust capture/HID engine and Qt/PySide6 GUI. It targets screen-responsive RGB lighting, audio reactive effects, multiple LED strips, and cross-platform operation. Please preserve relevant upstream attribution and license notices when distributing derived files.

**Upstream:** [Kevinsillo/quiklight-x11](https://github.com/Kevinsillo/quiklight-x11) · **Fork repository:** [RotaryMaster/rotaryopersonal](https://github.com/RotaryMaster/rotaryopersonal)

## Features: what each does

| Feature | Behavior |
| --- | --- |
| Screen ambient mode | Samples the screen edges and renders corresponding colors on the mapped LED segments. |
| Monitor selection | Chooses the screen to capture (KDE portal on Bazzite; Windows backend requires validation). |
| Top / right / bottom / left mapping | Assigns LED segments to the four edges, independently from their physical positions. |
| MultiStrip control | Maps multiple physical controllers, with independent logical and physical LED counts. |
| Segment position and direction | Supports explicit or automatic LED offsets and reverses segment color order. |
| Segment source: Independent | Each active segment samples its own assigned edge region. |
| Segment source: Mirror | Duplicates colors from another independent source segment; supports unequal LED counts by resampling. |
| Segment source: Off | Forces physical LEDs to black without deleting their hardware slots. |
| Physical strip enable and RGB gain | Enables/disables each strip and adjusts final RGB gains per controller. |
| Real-time configuration | Applies regular and structural configuration updates while the service runs; new physical USB devices can still require separate initialization. |
| Live LED preview | Displays actual final RGB output from the backend's QLV3 telemetry instead of inventing colors. |
| Black-bar detection | Auto-crops letterbox/pillarbox areas to sample the actual picture. |
| Screen capture insets | Moves the sampling boundary inward from any of the four edges. |
| Color sampling and Vivid mode | Offers average/vivid selection and color weighting. |
| Color fidelity and adaptive fidelity | Adjusts color accuracy, saturation, scene brightness and adaptive response. Experimental fidelity controls may remain opt-in. |
| White balance and gamma | Adjusts overall and per-channel RGB/gamma response. |
| Brightness, power limit, level | Limits output intensity and offers safety-oriented brightness/power settings. |
| Smoothing, slew, fade | Controls temporal transitions to reduce flicker and abrupt shifts. |
| Screen dominant and palette modes | Supports dominant scene color, selectable palette and additional color dynamics. |
| Static color | Applies a fixed RGB color across configured active LEDs. |
| Built-in effects | Breathing, pulsing, rainbow, fade, comet, aurora and fire; adjustable speed/minimum. |
| Music-reactive mode | Uses computer audio to drive brightness/color changes using bass, treble, volume or RPM-like response. |
| Music styles | Dim, boost, flash, saturation, complementary color, palette swap, split, volume, wave, VU meter, sparks, REV, hue spin, breathing, chase, center burst, confetti, heat, four-edge, heartbeat, echo, ping-pong. |
| Music meter and thresholds | Live five-band metering, adjustable thresholds, toggles and per-segment participation. |
| Configuration presets | Saves/loads lighting and hardware mappings. Separate music presets are also available. |
| GUI themes and language | Qt interface with appearance/language selection and a tray icon. |
| Metrics / logs / reports | Displays app/service metrics and supports log inspection, export and configuration backup. |
| Version history and rollback | Keeps previous version snapshots to restore earlier working binaries and GUI. |
| Autostart | KDE user service for LEDs plus XDG autostart of the Qt tray, and Windows startup logic under development. |
| Linux HID isolation | Attempts to prevent failure or timeout of one USB controller from stopping another. |
| Configuration validation | Rejects overlapping physical LED slots and invalid mapping/source combinations. |

## Compatibility and implementation matrix

**Legend:** ✅ implemented and maintainer-tested · 🟡 code exists or partial, **not fully validated** · ⏳ pending/not confirmed. This table is intentionally conservative; it does not claim feature parity without a Windows hardware test.

| Capability | Bazzite KDE / Linux v0.3.5.0 | Windows (experimental, version unverified) |
| --- | :---: | :---: |
| GUI (Qt/PySide6), themes, language | ✅ | 🟡 |
| Screen capture and monitor selection | ✅ (KDE portal) | 🟡 (Windows capture module) |
| Four-edge color sampling / black-bar auto-crop | ✅ | 🟡 |
| Accuracy / RGB / vivid / adaptive controls | ✅ | 🟡 |
| Static, dominant and built-in effects | ✅ | 🟡 |
| Music mode and 22 styles | ✅ | 🟡 |
| Two physical HID strips and 65 positions per strip | ✅ | ⏳ |
| Independent / mirror / off per segment | ✅ | 🟡 (code path, no hardware validation) |
| Config changes without Apply / HID restart | ✅ | 🟡 |
| Live physical QLV3 RGB preview | ✅ | 🟡 |
| Presets, backups and rollback | ✅ | 🟡 |
| Session autostart | ✅ (systemd user + KDE tray) | 🟡 |
| Controller failure isolation | ✅ on tested Linux setup | ⏳ hardware verification |
| Windows installer, startup/shutdown and USB mapping | N/A | ⏳ consolidated validation |
| Official tested downloadable release | ⏳ reproducible package publication | ⏳ |

**Current baseline by OS:** **Bazzite KDE: v0.3.5.0 stable (locally installed and user-confirmed). Windows: no version certified as stable for this MultiStrip series.** This repository contains older branches and installers that should not be confused with the current validated Linux baseline.

## Reference hardware arrangement

Two ROBOBLOQ USB HID devices (VID:PID `1A86:FE07`), 65 physical LEDs each:

| Physical LEDs (1-based) | Strip 1 | Strip 2 (bottom profile) |
| --- | --- | --- |
| 1–17 | Left edge | Left reserved / Off |
| 18–48 | Top edge | Bottom edge, 31 LEDs |
| 49–65 | Right edge | Right reserved / Off |

Every controller has its **own LED offsets**. Turning a section off never shrinks the physical strip. If the side sections on Strip 2 are intentionally enabled and set to **Independent**, they may have different colors from Strip 1 because the `edge_window` sampler partitions the same screen edge among enabled segments. Use **Mirror** to duplicate a chosen segment rather than resampling.

## Getting files and installing

### Linux — Bazzite KDE (tested target)

**Sources and available files:**
1. [This fork's repository](https://github.com/RotaryMaster/rotaryopersonal) and its [QuikLight branches](https://github.com/RotaryMaster/rotaryopersonal/branches) contain project history and older installers.
2. The **v0.3.4.5 local source/patch package** is derived from the previous v0.3.4.4 build. It is **not yet a complete standalone GitHub Release or one-command clean installation**; do not mistake an older `instalar-quiklight-v25.sh` for v0.3.4.5.
3. Check [GitHub Releases](https://github.com/RotaryMaster/rotaryopersonal/releases) for downloadable packages **when a verified build is published**. No v0.3.4.5 release is claimed here.

**Existing working v0.3.4.5 installation:** preserve the live configuration and installed binaries; audit first before consolidating startup. Default user paths:
```text
~/.local/bin/quiklight
~/.local/share/quiklight-gui-qt/quiklight_gui.py
~/.local/share/quiklight-gui-qt/venv-py315/bin/python
~/.local/share/quiklight-rust/config.toml
~/.config/systemd/user/quiklight.service
~/.config/autostart/quiklight-gui.desktop
```

The startup consolidation checks the current v0.3.4.5 GUI hash and compiled binary if available, makes reversible backups, and ensures **one canonical user service + one KDE tray autostart**. It must not edit the immutable OS base or replace an already-working binary just to change startup. If it finds unexpected legacy entries it **stops and asks for review**, rather than deleting them.

```bash
python3 consolidar_estavel.py --audit
python3 consolidar_estavel.py --activate
systemctl --user is-enabled quiklight.service
systemctl --user is-active quiklight.service
```

`--activate` is only for an **already installed, working v0.3.4.5**. It opens the GUI automatically when safe and prints a rollback command. A fresh installation requires assembling the full upstream Rust source and Qt helper modules, then building with `cargo check --locked`, `cargo test --locked`, `cargo build --release --locked`, provisioning PySide6, and reviewing the user service before enabling autostart. **Do not download random binaries or run an unverified installer.**

### Windows — planned/experimental target

The Windows implementation uses dedicated Windows Rust capture and USB paths and Qt/PySide6 GUI routines. Look in the [Windows development branches](https://github.com/RotaryMaster/rotaryopersonal/branches) (for example `quiklight-x11-windows`) for work in progress. **No tested MultiStrip v0.3.4.5 Windows package or verified single-click installer is published.** There is therefore no honest equivalent installation command yet. Before deploying: build on Windows with Rust/Cargo, verify Qt dependencies, test USB enumeration, HID timeouts, capture and autostart, then publish a signed or checksum-verified release.

## Development and testing

- Do not commit real `config.toml`, hardware serial numbers, local identifiers, user paths, secrets or raw support logs.
- Protect a working Linux installation with backup and rollback before changing binaries, Qt UI or service startup.
- Keep the Linux and Windows feature matrix updated **based on actual testing**, not only source code presence.
- Confirm that hotplug, failed USB controllers, startup and shutdown cannot cause restart loops.
- Preserve upstream license and copyright notices.

**USB unplug/replug recovery:** an optional, separate systemd user watcher is under physical test. It leaves the v0.3.4.5 stable backend unchanged and requests a service restart only after previously disconnected RGB controllers have reappeared. See [hotplug notes](docs/QUIKLIGHT-USB-HOTPLUG.md). This feature is **not yet confirmed stable**.\n\nMore detail: [Status](docs/QUIKLIGHT-STATUS.md) · [MultiStrip mapping](docs/QUIKLIGHT-MULTISTRIP.md) · [Changelog](docs/QUIKLIGHT-CHANGELOG.md) · [MultiStrip development tracker](https://github.com/RotaryMaster/rotaryopersonal/issues/1).

## Upcoming REV Simracing and diagnostics (experimental)

The maintained v0.3.5.0 installation is working on Bazzite KDE. The v0.3.5.1 experimental patch adds screen-color source to segment Music, smoother progressive **audio-derived** REV lights, original color-calibration resets, persistent Home alerts, system-tray notifications and a QLV3 white-flash diagnostic. Game RPM telemetry is **research-stage**, and physical white flashes remain **unresolved**. See [v0.3.5.1 development notes](docs/QUIKLIGHT-V0351-REV-FLASH.md). No Linux/Windows v0.3.5.1 stable release is claimed.
