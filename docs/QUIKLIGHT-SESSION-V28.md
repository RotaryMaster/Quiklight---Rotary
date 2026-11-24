# KDE ↔ Gamescope session recovery — v28 (2026-11-23)

Status: maintainer reports the Claude-provided v28 correction resolved the transition problem on Bazzite. This is a local functional report, not a clean-install release or Windows validation.

## Findings
- KDE portal permission wait previously blocked up to 300 seconds without checking whether KDE had exited.
- The old session guard depended on an existing capturer; asynchronous recovery could adopt the other compositor within the same process.
- Zombie kwin_wayland/gamescope processes could interfere with detection.
- The service had accumulated five drop-ins and pointed at a test binary.

## Implemented correction
- capture.rs: ignore zombie compositors via /proc/<pid>/stat; expose session_signature (0 absent, 1 KDE, 2 Gamescope) and capturer session_sig.
- Portal wait polls every 500 ms; cancel when KDE exits; retain 300-second total timeout.
- main.rs: retain startup compositor identity; check every second when capture is needed; on change or absence for 3 seconds, black out strips and exit with error. Prevent cross-compositor recovery adoption and gate new recovery on matching signature.
- Build isolated copy v0352-sessao-estavel-v28/rust in Distrobox dev; install to ~/.local/bin/quiklight after successful compilation and backup.
- Consolidate service overrides into 50-sessao-v28.conf; ExecStartPre waits for a live compositor, Restart=on-failure, RestartSec=1s, TimeoutStartSec=180s. Preserve old drop-ins as timestamped backup.
- Validate both KDE → Gaming and Gaming → KDE; LEDs must recover automatically. Keep capture/session regression tests in subsequent builds.

## Calibration discovery (2026-11-21)
Dark green content appearing reddish on the bottom LEDs was resolved by enabling individual calibration settings rather than global calibration alone. Check this before changing sampling/color algorithms. This does not establish that intermittent white flashes are fixed.

## Limitations and follow-up
The original script's rollback instructions restore drop-ins but do not explicitly restore the backed-up binary; full rollback must restore both. The helper checks compositor existence twice separated by two seconds, not continuous identity stability. Startup with signature zero, transitions during initial capture, repeated application and Windows compilation need regression checks. Do not claim automation/telemetry or Windows parity validated.

## Development workflow
Deliver versioned self-contained .sh patches with exact anchors, backups, compilation before installation, user-scoped changes, automatic log copying via wl-copy, and complete rollback. Preserve known-good session behavior and avoid stacking conflicting overrides.
