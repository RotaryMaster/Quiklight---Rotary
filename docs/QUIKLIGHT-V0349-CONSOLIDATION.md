# QuikLight MultiStrip v0.3.4.9 — consolidated experimental build

**Status (21 Nov 2026): prepared source-overlay ZIP, Python syntax and archive validation passed. Rust compilation and real USB hotplug tests are still pending; Linux v0.3.4.5 remains the validated installed baseline.**

## Scope

The v0.3.4.8 source build already completed `cargo check --locked`, `cargo test --locked` (16 tests passed) and `cargo build --release --locked` on the maintainer's Bazzite KDE. However, it retained the old `device.rs` using USB discovery order, so it was not safe to install as a complete replacement.

The v0.3.4.9 overlay combines:
- v0.3.4.5 independent/mirror/off, physical offsets and live mapping
- v0.3.4.6 GUI physical USB port panel and manual rebind
- v0.3.4.7 modes and brightness/power override by physical strip
- v0.3.4.8 intensity adjustment by segment, and its previously passing unit tests
- new Linux HID device binding by `HID_PHYS` and **in-process worker retry/re-initialization** after disconnect/replug

The hardware binding is the existing user-approved `~/.config/quiklight/strip-usb-ports.txt`, ordered:
1. `usb-0000:02:00.0-6.2` = physical Strip 1
2. `usb-0000:02:00.0-6.1` = physical Strip 2

A disconnected controller remains reserved in its logical slot. The other worker remains alive; no full QuikLight service restart is required for reconnect. This means the separate `quiklight-usb-watch.service` is **not required for this experimental native recovery** (and was absent in the maintainer's audit). Existing systemd user units, KDE autostart, Gamescope drop-ins and `config.toml` are not edited by the build.

## Safety checks

- Build helper only accepts the exact audited `v0348-per-segment/rust` source hashes: main `94c2bbc5`, config `6f513aea`, device `6b3a0472`, output `27e160a3`, multi_strip `41946ea1`.
- It copies to `v0349-consolidado/rust` and overlays only `device.rs` and `hid_workers.rs`.
- Commands: `python3 preparar.py --audit`, then `python3 preparar.py --prepare` (Cargo check/test/release).
- Separate `instalar.py --audit` requires exact previously reported working backend/GUI hashes and confirmed USB bindings.
- Only a user-confirmed installation backs up Rust binary, GUI, config and ports; it does not modify any autostart, systemd unit or Gamescope configuration.
- Rollback restores the snapshot and restarts the existing user service.
- The new overlay has **not** been compiled in the assistant environment (Rust toolchain absent), and must not be advertised as stable or a published GitHub Release.

## Remaining validation

- [ ] Successful Rust check/test/release on Bazzite
- [ ] Confirm no startup loop if USB Strip 2 is absent
- [ ] Unplug/replug Strip 2: Strip 1 must stay on and Strip 2 must recover without `systemctl restart`
- [ ] Unplug/replug Strip 1: Strip 2 must retain its mapping
- [ ] Confirm red USB status, manual binding adjustment and GUI real-time modes
- [ ] Check graphics capture/KDE/Gamescope and power-related white flashes separately
- [ ] Windows build/identity strategy remains unverified

[Main README](../README.md) · [USB identity and flash findings](QUIKLIGHT-USB-IDENTITY-FLASH.md) · [Per-strip lighting](QUIKLIGHT-PER-STRIP-LIGHTING.md).

## Audit correction v0.3.4.9r1 (21 November 2026)

The original `preparar.py` accidentally used two **pre-v0.3.4.8** hashes: `config.rs` from v0.3.4.7 (`047b1ca2…`) and `multi_strip.rs` from v0.3.4.5 (`8bfc19d0…`). The exact source hashes for the built v0.3.4.8 are `config.rs` `6f513aea17e6ea190c36ae971f8cc13e6edf4896b70122d6d23fad45b05a9c49` and `multi_strip.rs` `41946ea19d09f3df6637bd2436215108df8df1769da17a6b689afda0b26f3b7f`. The revised standalone ZIP corrects only the hash audit and documentation; it preserves HID worker, GUI, installer, startup and Gamescope code. Audit was tested offline against the exact exported patch sources; Rust build and physical hardware tests remain pending.
