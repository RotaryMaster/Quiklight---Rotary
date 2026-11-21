# QuikLight — platform status (21 November 2026)

## Stable baseline

**Bazzite KDE / Linux: v0.3.4.5 — maintainer-confirmed working.** Two physical ROBOBLOQ HID controllers (VID:PID 1A86:FE07), 65 physical LED positions each, bottom 31 active on Strip 2, real-time changes and per-segment **Independent / Mirror / Off** settings. Maintainer-confirmed in their setup, not a universal hardware certification.

**Windows: latest MultiStrip version validated as stable: none confirmed.** Windows is a first-class project target, but dedicated compilation, capture/HID, startup/shutdown and real hardware validation remain to be completed. Do not present Linux v0.3.4.5 as a tested Windows release.

## Previous milestones

- v0.3.4.1: initial physical offsets / QLV3 telemetry. Second controller timeout caused global restart loop.
- v0.3.4.2: bottom profile, 17 reserved + 31 bottom + 17 reserved.
- v0.3.4.3: HID controller isolation. Maintainer confirmed two-strip operation.
- v0.3.4.4: live structural settings without Apply. Maintainer confirmed operation.
- v0.3.4.5: Independent / Mirror / Off per-segment source. Maintainer confirmed this version works on Bazzite KDE.

## Outstanding before publishing a release

- Consolidate complete buildable sources, dependency helper modules and license notices.
- Run clean reproducible Cargo checks/tests and ensure Linux installation package, rollback and autostart have a deterministic source-of-truth.
- Validate every matrix item on Windows and create its platform installer.
- Review USB HID failure cases, session logout/shutdown, duplicate KDE startup entries, and hotplug.
- Sanitize configs, file paths, IDs and logs before public upload.

**Publication note:** documentation on GitHub describes an installed local baseline. A downloadable v0.3.4.5 GitHub Release is **not** claimed.

See [README](../README.md) · [mapping](QUIKLIGHT-MULTISTRIP.md) · [installation](QUIKLIGHT-INSTALL.md).

## Updated maintainer validation (21 November 2026)

The maintainer subsequently confirmed **v0.3.5.0 fully working on their Bazzite KDE hardware**. This supersedes the earlier v0.3.4.5 stable baseline. The v0.3.5.1 REV/alerts/diagnostics work is experimental and not yet tested on the hardware; see [development notes](QUIKLIGHT-V0351-REV-FLASH.md). Windows v0.3.5.x remains unvalidated.


## Maintainer-confirmed v0.3.5.1 operation (21 November 2026)

The maintainer reports **QuikLight v0.3.5.1 is working well on Bazzite KDE** with the new REV/GUI features. This advances the **working Linux installation baseline** to v0.3.5.1. **Exception: intermittent physical white LED flashes remain unresolved** (at least one observed after install); it would be incorrect to claim that the flash issue is fixed or that this build has been tested on Windows.

**KDE Plasma/Wayland and Gamescope Gaming Mode are explicit Linux deployment targets.** The installed `quiklight.service` user unit has existing `10-fast-gamescope.conf` and `20-session-guard.conf` drop-ins. Keep their behavior, boot order, portal capture and session transitions intact when changing the UI/backend. Do not imply Gaming Mode is newly implemented in v0.3.5.1, only that compatibility has been part of the project; test transition behavior again after future changes.

[Feature status and automation planning](QUIKLIGHT-V0352-AUTOMATIONS-SIMRACING.md).
