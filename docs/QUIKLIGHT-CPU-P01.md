# v28 CPU P01 — 2026-11-23

## Finding
In main.rs, MonitorWatch evaluated capture::kde_session_active() before the two-second polling gate, scanning /proc on each rendering iteration (up to 60/s). Move the time gate before detection, and advance last_poll even outside KDE. Keep the independent v28 compositor guard and recovery logic unchanged.

```diff
 if needs_capture
-    && capture::kde_session_active()
     && monitor_watch.last_poll.elapsed() >= Duration::from_secs(2)
 {
     monitor_watch.last_poll = Instant::now();
-    if monitor_watch.observe(kde_monitor_signature(), Instant::now()) {
+    if capture::kde_session_active()
+        && monitor_watch.observe(kde_monitor_signature(), Instant::now())
+    {
```

## Measured result (maintainer logs)
12-second samples, 16 logical CPUs. Driver 16.41% → 1.58% of one logical CPU (90.37% relative reduction); main thread 15.91% → 1.08% (93.21%). 33/33 Rust unit tests passed; release build successful (Cargo version 0.29.0). KDE portal capture initialized at 80x45, 60 configured FPS; two HID controllers initialized, 130 physical LED positions. Auto Crop and accuracy remained enabled. The patch changed only the MonitorWatch block and installed only the binary, preserving v28 service drop-ins.

## Status
P01 installed, physical regression pending: both strips and color response, KDE → Gaming → KDE, monitor topology change. No new Windows or standalone release validation. Do not infer measured delivered frame rate from configuration. Keep the original v28 binary/source and generated rollback script. Future optimization should preserve rendering semantics and measure before/after; do not lower quality to hide waste.
