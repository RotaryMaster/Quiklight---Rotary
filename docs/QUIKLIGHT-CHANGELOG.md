
## v0.3.5.0 — maintainer-confirmed functional on Bazzite KDE (2026-11-21)
- Consolidated physical USB port identity/reconnection, per-strip lighting/power, per-segment Independent/Mirror/Off and local lighting modes including Music.
- All functions reported working by the maintainer on their two-strip setup. Windows not yet validated.

## v0.3.5.1 — experimental source overlay (not stable)
- REV Simracing naming and per-segment progressive audio-based RPM bar, screen/solid color selector, original calibration controls, Home error notifications, tray naming and white-flash logging.
- Full RPM telemetry/game adapters and the root cause of intermittent white flashes remain pending.

# QuikLight MultiStrip — changelog

## v0.3.4.5 — stable on Bazzite KDE (maintainer-confirmed, 2026-11-21)
- Per-segment source: Independent samples the screen edge; Mirror copies an independent source segment's RGB; Off outputs black without changing physical slots.
- Works with v0.3.4.4 real-time configuration in the maintainer's two-controller setup.
- Windows status remains experimental / **not hardware-validated**. Not a published GitHub Release.

## v0.3.4.4 — real-time baseline
- Live application of structural mapping and capture changes.
- Two physical strips verified.

## v0.3.4.3 — independent HID operations
- Addressed global service restart caused by second controller HID timeout.
- Two-strip hardware operation confirmed in maintainer's setup.

## v0.3.4.2 — bottom profile
- Creates a second 65-position strip: 17 reserved, 31 mapped to bottom edge, 17 reserved.
- Startup timeout found in original device initialization.

## v0.3.4.1 — initial MultiStrip
- Physical LED offsets and QLV3 physical RGB telemetry.
- Failed initialization of one device previously ended the entire process.

These are locally tested development revisions, **not equivalent to Windows compatibility certification** or published GitHub Releases.

## v28 session fix — 2026-11-23 (local maintainer-confirmed correction)
- Ignore zombie compositors, interrupt portal waiting on KDE exit, pin process to startup compositor, prevent cross-session capture adoption and force systemd restart with blackout.
- Consolidate session drop-ins and wait for live compositor before restart.
- Document individual calibration correction for dark green rendered red on lower LEDs.
- [Technical details and rollback caveats](QUIKLIGHT-SESSION-V28.md). No standalone release or Windows certification claimed.
