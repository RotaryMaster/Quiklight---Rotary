# USB reconnect recovery — Bazzite KDE (test candidate)

**Status:** a dedicated user-session hotplug monitor has been prepared and passed simulated state tests, **not yet physically validated**. The confirmed stable runtime remains **QuikLight MultiStrip v0.3.4.5**. Do not claim this monitor is part of the stable release until the maintainer confirms an unplug/replug test.

## Why it is needed

The v0.3.4.5 HID worker exits when its file descriptor fails; it does not reopen after the USB controller is detached and later reinserted. Re-enumeration in the backend also occurs on configuration changes, not on arbitrary USB device arrival.

## Recovery strategy (additive, no OS base changes)

- A separate `quiklight-usb-watch.service` runs inside **systemd --user** and starts with the KDE user session (`default.target`).
- It reads `/sys/class/hidraw` and detects only the **1A86:FE07 input0 RGB interface** by descriptor, not the input1 keyboard interface, unstable `hidrawN`, or the duplicated device serial number.
- Enroll the **physical hub ports** (e.g. 6.2 and 6.3) while both controllers are present and the current service is active.
- It requests a restart of the existing `quiklight.service` **only after** a previously missing controller has reappeared and **all enrolled ports have been stable for 2.5 s**.
- No restart when both were present at monitor startup, when they are merely unplugged, or when the QuikLight service has been manually stopped.
- It does not change the original service unit, backend binary, GUI, active `config.toml`, KDE autostart, Gamescope integration, USB firmware or udev rules.
- Rollback removes only the new monitor files and unit.
- This is **service-level** recovery and causes a brief lighting/capture interruption on actual reconnection. A future native in-process per-controller reconnect routine would avoid full service restarts.

## Installation from testing package

The test package is delivered with the conversation. The repository does **not** yet contain a release artifact for this patch. Unzip, enter `quiklight-hotplug-v0345`, then run:

```bash
python3 -m unittest -v test_hotplug.py
python3 instalar_hotplug.py --audit
python3 instalar_hotplug.py --install
```

Inspect using `journalctl --user -fu quiklight-usb-watch.service` and `journalctl --user -fu quiklight.service`.

## Outstanding verification

- [ ] With both strips working, unplug only Strip 2: Strip 1 stays working
- [ ] Reconnect Strip 2 after several minutes: one restart, both strips return
- [ ] Disconnect and reconnect both: no restart before both return
- [ ] KDE relogin and Bazzite Gaming Mode / Gamescope changes alone trigger no restart
- [ ] Manual stop of `quiklight.service` is respected
- [ ] Rollback removes watcher, existing service and GUI remain unchanged
- [ ] Document outcome and consider native worker-level reconnection once tested

References: [kernel hidraw documentation](https://docs.kernel.org/hid/hidraw.html), [udev](https://www.freedesktop.org/software/systemd/man/latest/udev.html).
