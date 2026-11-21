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
