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
