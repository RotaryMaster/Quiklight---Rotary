# QuikLight v0.3.5.2 — Automation, exceptions and built-in Simracing telemetry

**Date:** 21 November 2026 · **Status:** experimental source/GUI overlay, not installed or validated on the maintainer's hardware. The user confirms **v0.3.5.1 works well on Bazzite KDE**, but the intermittent white LED flash is still unresolved.

## Prior design source — Tuya Ambient Light / LumaSync

The user's private LumaSync `develop` project already has practical precedents:
- `src/backend/ta_auto.py`: detects games from process lists/Steam and media via **Linux MPRIS** or **Windows GSMTC**, chooses configured presets, supports start/stop delays, restores the previous config or active preset on exit.
- `src/backend/ta_history.py` and `docs/HISTORICO_EXCECOES.md`: keeps up to **120** candidate detection events before exclusion, with dedupe, app/category/time, no screenshot, URL or command-line persistence.
- `src/gui-v5/qml/pages/AutomationPage.qml` and `ExceptionsPage.qml`: detection toggles, category choices, presets, delays and manually managed exceptions; browser-domain filtering is documented separately.

The new **QuikLight** design borrows those established behaviors, but is not a copy of Tuya account controls. Version v0.3.5.2's initial prototype detects **processes and optional schedules**, not complete MPRIS/GSMTC playback metadata; full media-playing detection is a follow-up.

## Implemented in the staged prototype

- New Qt menus **Exceções** and **Automações** with a per-rule editor and persistent private settings.
- Triggers: application/process, weekday+time range (including windows crossing midnight), or known simracing game process.
- Actions for exception and automation: **None/ignore automation**, **Off**, **Static RGB**, **Load preset**, **MODO REV Simracing**.
- Scope: all strips, Strip 1 only, Strip 2 only. Hardware offsets and USB associations unchanged.
- Separate action when an app closes/schedule ends: **restore previous**, **apply Padrão preset**, **off**, **keep last**, or **next eligible rule**; configurable activation/release delays and numeric priorities. **Exceptions win equal priorities**.
- Saved preset name is selectable, and preset color/mode/brightness can be edited from the rule editor with a private backup; complex presets remain editable in the existing Presets page.
- Persistent process/game candidate history (maximum 120 entries, app/category/time; no screenshots, page URLs, full process arguments or browsing history).
- **Disabled by default.** A local standard-library Python worker publishes an expiring JSON action file. Rust consumes it without modifying `config.toml` or restarting the USB service. If the worker stops, the override expires and normal output returns.
- The optional Linux worker runs as **one additional `systemd --user` service**. Existing `quiklight.service`, its Gamescope/session-guard drop-ins, XDG tray autostart and Bazzite's immutable system are not changed. It must be tested across KDE → Gamescope, Gamescope → KDE and direct Gaming Mode boot.

## Built-in simracing: source formats staged in Rust

**No SimHub or separate telemetry application is necessary for these UDP sources**, but the user must enable Data Out in each game and direct packets to the local host. Rust binds only loopback (`127.0.0.1`), validates packet layout and expires stale telemetry at ~650 ms; the per-segment REV light automatically falls back to **audio-derived RPM** if fresh real telemetry is unavailable.

| Game(s) | Direct source | Target OS | State |
| --- | --- | --- | --- |
| EA SPORTS F1 24 / F1 25 | Official UDP 2024/2025 CarTelemetry packet 6: `engineRPM` and `revLightsPercent`; port **20777** | Linux Proton, Windows | Parser and unit tests staged; game tests pending |
| F1 25 **2026 Season Pack format** | UDP format 2026 is different | Linux, Windows | Not implemented; do not enable as 2025 format |
| Forza Motorsport 7 / Forza Motorsport (2023) / Forza Horizon 4–5 | In-game **Data Out** Sled or Dash; `EngineMaxRpm` offset 8, `CurrentEngineRpm` offset 16; port **5300** | Linux Proton, Windows | Parser and unit tests staged; game tests pending |
| BeamNG.drive | **OutGauge** UDP `rpm`; port **4444** chosen in game; normalizes using `QUIKLIGHT_BEAMNG_REDLINE_RPM` (default **7500**, configurable) | Linux Proton, Windows | Parser staged, live tests pending |
| ACC, Assetto Corsa, iRacing, AMS2, Le Mans Ultimate | Mostly shared-memory / game-specific sources | Linux Proton, Windows | **Not integrated**. A built-in Proton bridge/native shared-memory adapter is a separate, unverified implementation step |

References:
- [EA F1 25 UDP Specification (official)](https://forums.ea.com/blog/f1-games-game-info-hub-en/f1%c2%ae-25-udp-specification/12187347)
- [Forza Motorsport Data Out Documentation (official)](https://support.forza.net/hc/en-us/articles/21742934024211-Forza-Motorsport-Data-Out-Documentation)
- [BeamNG OutGauge protocol](https://docs.beamng.com/modding/protocols/)
- [F1 25 2026 Season Pack telemetry parser](https://github.com/simracingstudio/f1-2026-telemetry)
- [simbridge](https://github.com/Carlos-Diaz-07/simbridge) — study the Windows shared-memory relay under Proton before implementing another bridge
- [sim-teleport](https://github.com/t-hovestadt/sim-teleport), [OpenRacing](https://github.com/EffortlessMetrics/OpenRacing) — source adapters and testing caveats.

## Gamescope and Windows

Linux KDE/Gamescope support is a requirement, not just a label: the existing app has KDE portal capture, Gaming Mode context and user-service drop-ins. A **separate user worker** must never force-start `quiklight.service` after the user stops it, and must not alter the existing `10-fast-gamescope.conf` and `20-session-guard.conf` guards.

Windows is a first-class target. The pure Python rule engine uses `tasklist` for process detection, and the Rust UDP receiver is standard-library cross-platform. The **Windows installer and actual Windows capture/USB and Task Scheduler integration remain to be validated**. Current first-run Bazzite installer is Linux-only; do not claim Windows automation parity.

## Test, install and rollback plan

1. Keep the working v0.3.5.1 runtime untouched. Run `python3 verificar.py` (Python syntax and rule tests).
2. Run `python3 preparar.py --audit` against the exact known v0.3.5.1 Rust source. It compares `main.rs`, `config.rs`, `segment_override.rs`, `device.rs`, `hid_workers.rs`, `multi_strip.rs` and `output.rs` hashes.
3. Only after `AUDIT OK`, run `python3 preparar.py --prepare`, which stages sources in a **new** project folder and runs `cargo check --locked`, `cargo test --locked`, `cargo build --release --locked`.
4. If `BUILD OK`, run `python3 instalar.py --audit` to inspect installed binary, GUI and bound USB identities. Installation requires the user to close GUI/tray, type `SIM`, and creates a snapshot of working binary/GUI/config/bindings. Rollback command is printed.
5. An installed `quiklight-automation.service` starts alongside the user's normal session but **rules remain disabled** until the GUI toggle is enabled. No controller or scene change when idle.
6. Test override, app launch/exit, overnight schedule, rule conflict, individual strips, native/Proton sim game UDP, stale-data fallback, tray and app closed, login, KDE/Gamescope switching and rollback. Only then consider a stable release.

**Current tests:** pure-Python rules, priorities, schedule wraparound, state restoration, preset backup editing and validation passed. Qt runtime and Rust compilation are **not runnable in the assistant container**; no claims of hardware success. v0.3.5.1 remains the safe installed baseline.

## Outstanding known issue

A brief **white LED flash** was still observed after v0.3.5.1 was installed. Preserve QLV3 diagnostic capture and HID logs; do **not** mask with an unverified brightness filter. Treat this separately from automation and telemetry.

[Main README](../README.md) · [Status](QUIKLIGHT-STATUS.md) · [v0.3.5.1 findings](QUIKLIGHT-V0351-REV-FLASH.md).
