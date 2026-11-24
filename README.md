# QuikLight — RotaryMaster fork

**Supported interface languages:** English · Português (Brasil) · Español *(translation coverage can differ by screen)*.

**Platforms:** Linux (**Bazzite KDE Plasma / Wayland**, including **Gamescope Gaming Mode**) and **Windows**. The project targets both systems; compatibility is not identical or equally validated.

> **Current working Linux baseline: v0.3.5.1**, confirmed by the maintainer on Bazzite KDE on **21 November 2026**, using two ROBOBLOQ 65-LED controllers. **Known issue: intermittent physical white flashes are not resolved** (at least one observed after installation). This is an installed and working local build, **not** a published reproducible GitHub Release.
>
> **Windows current stable MultiStrip release: not confirmed.** Dedicated capture, HID and GUI paths exist, but v0.3.5.x and related Gamescope features have not been validated on Windows. Never infer Windows feature parity from Linux success.
>
> **Next version: v0.3.5.2 (EXPERIMENTAL)**: Tuya/LumaSync-style automation and exceptions plus native UDP simracing telemetry. Python logic tests passed; Rust build, GUI integration and real gameplay testing are **pending**.

## Overview and origin

A Rust/PySide6 ambient RGB lighting driver derived from [Kevinsillo/quiklight-x11](https://github.com/Kevinsillo/quiklight-x11) and related upstream projects. This fork develops four-edge screen capture, adaptive fidelity, audio-reactive lighting, per-strip and per-segment modes, native LED USB HID handling, user-service installation and future Windows feature parity. Preserve upstream attributions and license notices.

## Main features

| Feature | What it does |
| --- | --- |
| Screen / border capture | Samples four screen edges and maps colors to actual LEDs |
| KDE portal and monitor selection | Captures a selected monitor through PipeWire / portal; restore tokens reduce reprompts |
| Gamescope support | Existing Linux environment/session detection and Gamescope-specific service drop-ins, including `10-fast-gamescope.conf` and `20-session-guard.conf`; Game Mode transitions must be retested after upgrades |
| Hardware mapping | Manages two (or more, subject to hardware testing) physical HID controllers; positions, direction and active/off sections |
| USB identity and reconnect | Binds each physical strip to its selected USB port; per-controller worker can retry after a reconnect |
| Per-segment source | Independent, Mirror another segment, or Off |
| Per-strip lighting | Inherit global, static, dominant, regional dominant, palette and effects |
| Per-segment lighting | Inherit strip, static, dominant, regional dominant, palette, effect, or Music |
| Per-segment intensity | Attenuate a mapped section independently from global and strip output limits |
| Per-strip brightness/power | Independent software brightness and power limiting, still subject to safety constraints |
| Music modes | 22 audio-reactive styles, band sensitivity, screen/static source, with **MODO REV Simracing** as an audio-based approximation |
| Dynamic color fidelity | Adaptive brightness for light/dark scenes, RGB/gamma/neutral handling |
| Black-bar detection | Letterbox and pillarbox exclusion, adaptive screen insets |
| Calibration | Color and white-balance profiles, neutral reset and original upstream defaults |
| Real-time config | Live changes without an Apply click or full service restart where supported |
| Preview & metrics | QLV3 physical RGB preview, performance information and service status |
| Home alerts | Persistent recent errors and optional system notifications |
| Presets and rollback | User-editable presets, version snapshots, backup/restore |
| Startup and shutdown | Existing KDE session/systemd user service and GUI tray; Windows paths under development |

## Compatibility matrix

✅ Maintainer reported working on the target hardware · ◐ Code/integration exists, needs specific retest · ☐ Not yet validated/implemented on this platform.

| Capability | Bazzite KDE v0.3.5.1 | Bazzite Gamescope | Windows v0.3.5.x |
| --- | :---: | :---: | :---: |
| Qt GUI and presets | ✅ | ◐ user session dependent | ◐ |
| KDE/Wayland monitor capture and Portal | ✅ | ◐ specialized capture path | N/A |
| Gamescope environment detection / transition guards | ◐ | ◐ | N/A |
| Windows capture backend | N/A | N/A | ◐ |
| Physical USB mapping, independent strips | ✅ | ◐ | ☐ |
| Per-segment sources, modes and dimming | ✅ | ◐ | ◐ |
| Audio music, REV with audio estimate | ✅ | ◐ | ◐ |
| Automatic recovery of bound USB strips | ✅ user reported functions working | ◐ | ☐ |
| Real-time settings & QLV3 | ✅ | ◐ | ◐ |
| Home alerts and calibration reset | ✅ | ◐ | ◐ |
| Automated exceptions, app/schedule rules | ☐ v0.3.5.2 prepared | ☐ testing required | ☐ testing required |
| Native F1/Forza/BeamNG UDP RPM | ☐ v0.3.5.2 prepared | ☐ testing required | ☐ testing required |
| Verified standalone installer/Release | ☐ | ☐ | ☐ |

**The Linux runtime engine is tested; Gamescope boot and KDE ⇄ Gaming Mode transitions were supported earlier but are not yet specifically revalidated for v0.3.5.1.** Session drop-ins are preserved by later experimental installers.

## Reference hardware

Two ROBOBLOQ USB HID controllers (VID:PID `1A86:FE07`), each with **65 physical positions**.

| LEDs (1-based, per device) | Strip 1 | Strip 2 (bottom layout) |
| --- | --- | --- |
| 1–17 | Left | Optional left / Off |
| 18–48 | Top | Bottom (31 LEDs) |
| 49–65 | Right | Optional right / Off |

The hardware may report duplicate serial strings; **never bind strip identity to `hidrawN` or duplicated serials**. The user's actual bound physical ports can be changed; examples in docs are **not** universal defaults.

## Getting files and installation

### Linux — Bazzite KDE

1. Browse this [fork](https://github.com/RotaryMaster/rotaryopersonal) and [development branches](https://github.com/RotaryMaster/rotaryopersonal/branches).
2. Check [Releases](https://github.com/RotaryMaster/rotaryopersonal/releases) when a complete build is eventually published; **there is no claimed full v0.3.5.1 or v0.3.5.2 GitHub Release**.
3. The v0.3.5.x **source overlay packages** were distributed in the project's ChatGPT development conversation and build against previously staged Rust/Qt sources; they are **not standalone clean installers**. Old v25 or v0.3.4.x scripts are **not** substitutes for the newest release.
4. When you already have the verified current installation, preserve its user-scoped paths:

```text
~/.local/bin/quiklight
~/.local/share/quiklight-gui-qt/quiklight_gui.py
~/.local/share/quiklight-gui-qt/venv-py315/bin/python
~/.local/share/quiklight-rust/config.toml
~/.config/systemd/user/quiklight.service
~/.config/systemd/user/quiklight.service.d/ (existing Gamescope/session guards)
```

Check rather than replace:

```bash
systemctl --user show quiklight.service -p ExecStart -p FragmentPath -p DropInPaths
systemctl --user is-active quiklight.service
systemctl --user is-enabled quiklight.service
```

A clean first-time installer must still be consolidated, include full Rust and Qt helper sources, provision dependencies and a checksummed download, then be tested with USB hardware. **Never blindly run an old installer on the working configuration.**

### Windows

Windows is an explicit development platform. Earlier branches implement Windows capture, GUI and service/task handling but **v0.3.5.x has not been certified on physical MultiStrip hardware**. See the [Windows development branches](https://github.com/RotaryMaster/rotaryopersonal/branches). No tested v0.3.5.x Windows installer is claimed; building requires Rust/Cargo, Qt/PySide6 and validated USB/HID mappings.

## Automation and exceptions — v0.3.5.2 experimental

Design based on the maintainer's Tuya Ambient Light/LumaSync workflow: per-application process detection, optional schedules and weekdays, start/stop delays, editable rules/presets, history and manual exceptions. Exceptions can ignore, turn off or apply static/preset illumination. On an app's exit the rule can restore previous lighting, use the Default preset, turn off, keep the last state or proceed to the next eligible rule.

- All rules are off by default; the helper **does not change the existing `config.toml`**.
- A separate local user-session worker publishes expiring temporary overrides to the Rust backend, so stopping the helper returns to the base configuration.
- The existing service, HID mapping, KDE desktop entry, Gamescope drop-ins and immutable OS image remain untouched by preparation.
- History keeps up to 120 detections (app/category/time), without screenshots, URLs, window titles, command arguments or browsing history.

**Built-in Simracing telemetry candidate:** F1 24 / F1 25 (UDP formats 2024/2025; F1 25's *2026 Season Pack format not supported yet*); Forza Motorsport / Motorsport 7 / Horizon 4-5 by Sled/Dash; BeamNG OutGauge with user-adjustable max RPM. Planned UDP ports: 20777 (F1), 5300 (Forza), 4444 (BeamNG); games must be configured to send UDP locally. The Rust receiver uses no SimHub or extra installation. Games relying on Proton/Windows shared-memory APIs (ACC, Assetto Corsa, iRacing, AMS2, etc.) require another adapter and **are not yet supported natively by this experimental patch**.

See [Automation/Simracing technical plan](docs/QUIKLIGHT-V0352-AUTOMATIONS-SIMRACING.md).

## Known issues

- **Intermittent white LED flash**: still reproducible, especially while typing on a dark webpage. Not proven to be capture, USB framing, controller firmware or power. QLV3 only shows prepared RGB, not a HID acknowledgement; continue trace correlation rather than adding speculative filters.
- Windows feature parity and direct Gamescope startup still need current-version physical regression tests.


- **Strip 2 HID timeout / stuck yellow** (21 Nov 2026): the controller remains enumerated on its bound USB port but repeat HID initializations fail `ETIMEDOUT (110)` approximately every five seconds; restarting the process cannot guarantee recovery. Not proven caused by clicking Reverse. **Do not install automation/Simracing over this faulty hardware state** until a controlled per-strip power-cycle and log comparison. See [issue #2](https://github.com/RotaryMaster/rotaryopersonal/issues/2).

## Documentation

[Platform status](docs/QUIKLIGHT-STATUS.md) · [Installation](docs/QUIKLIGHT-INSTALL.md) · [History](docs/QUIKLIGHT-CHANGELOG.md) · [USB identity and flashes](docs/QUIKLIGHT-USB-IDENTITY-FLASH.md) · [v0.3.5.1 REV and diagnostics](docs/QUIKLIGHT-V0351-REV-FLASH.md) · [Issue tracker](https://github.com/RotaryMaster/rotaryopersonal/issues/1).

This is a community fork. Preserve upstream copyright/license attribution, avoid publishing private configs/IDs and use reversible, explicit installs only.

## Session recovery update — 23 November 2026

The maintainer reports the v28 patch resolved KDE ↔ Gamescope switching on Bazzite. It replaces the legacy stacked session drop-ins with `50-sessao-v28.conf` and forces complete process restart on compositor change. See [v28 session recovery and calibration findings](docs/QUIKLIGHT-SESSION-V28.md). This is a local fix, not a standalone release or Windows validation. Earlier session-drop-in descriptions above are historical for pre-v28 installations.
