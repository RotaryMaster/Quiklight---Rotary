# QuikLight — stable USB identities and intermittent white flashes

**Status: experimental v0.3.4.6 patch, uncompiled on Bazzite / not hardware-validated.** Do not change the stable v0.3.4.5 classification before confirmation.

## Observed issue

After USB detach/reinsert, the actual lit left and right sections may appear on the wrong physical strip. Both ROBOBLOQ 1A86:FE07 controllers share the same VID/PID, duplicate serial, and identical 34-byte RGB input0 report descriptors. The previous Linux `open_devices(n, strict)` sorted currently connected devices; a temporarily absent device can shift the mapping of logical device index to physical controller. This is a **credible cause**, not yet proven by correlated debug logs.

## Experimental fix — physical-port enrollment

- Save exactly one `HID_PHYS` port prefix for each logical strip in `~/.config/quiklight/strip-usb-ports.txt`, e.g. `usb-0000:02:00.0-6.2`, `usb-0000:02:00.0-6.3`.
- Select only RGB `input0` and the vendor-defined 64-byte HID descriptor. Never use `hidrawN` or the duplicated serial for persistent identity.
- If the configured physical port is missing, report that the bound strip is absent and **do not substitute another physically present controller**.
- Keep all `segment` and `strip` settings untouched, as well as the GUI, KDE autostart, Gamescope integration and Windows code.
- Use the existing user-space hotplug observer to restart after all expected controllers have returned. Native in-process reconnect remains future work.

A port binding becomes invalid when the user moves a controller to another physical USB port/hub. Safe arbitrary-port identity cannot be guaranteed from the exposed duplicate identifiers.

## White flash: diagnosis rather than guesswork

The v0.3.4.5 QLV3 telemetry is derived from the calculated output frame queued toward HID, **not an acknowledgement from the controller**. Correlate physical white flashes (especially on dark/gray scenes) against software RGB-white counts, timestamps, USB reset events and HID worker initialization/failure logs. The explicit `protocol::init` initialization frame is black, not white. A flash whose software RGB values remained dark may involve USB writes/firmware/controller/power, but this is not conclusive without instrumentation.

## Required checks

- [ ] Clean `cargo check --locked`, `cargo test --locked`, `cargo build --release --locked` on copied v0.3.4.5 Rust project
- [ ] Confirm the physical port enrollment is correct before activation
- [ ] Verify each physical USB port maps consistently across reconnect
- [ ] Confirm no unintended side LEDs light on disabled sections
- [ ] Verify the watcher sees all registered controllers before restart
- [ ] Compare QLV3 RGB telemetry and service/kernel logs with physical white flashes
- [ ] Preserve backup, rollback and reliable GUI/autostart/Gamescope entry points
- [ ] Port feature to Windows only after a proper physical identity strategy there

Ref: [Linux kernel hidraw docs](https://docs.kernel.org/hid/hidraw.html), [systemd persistent hidraw rules](https://sources.debian.org/src/systemd/262-1/rules.d/60-persistent-hidraw.rules).
