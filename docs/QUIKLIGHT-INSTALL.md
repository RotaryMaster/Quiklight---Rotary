# Installation and downloads

**Supported interface languages:** English · Português (Brasil) · Español.

## Current platform versions

| Platform | Current verified state | How to get it |
| --- | --- | --- |
| Bazzite KDE / Linux | v0.3.4.5, installed and confirmed functional by maintainer | Current local patch/build; complete public GitHub release pending |
| Windows | Experimental branches; no v0.3.4.5 MultiStrip release validated | [Windows branches](https://github.com/RotaryMaster/rotaryopersonal/branches); build/release instructions pending hardware verification |

See [project repository](https://github.com/RotaryMaster/rotaryopersonal), [branches](https://github.com/RotaryMaster/rotaryopersonal/branches) and [releases](https://github.com/RotaryMaster/rotaryopersonal/releases). Do not download the old v25 installer expecting it to contain v0.3.4.5.

## Bazzite KDE — protect existing working installation

The v0.3.4.5 user install uses:

- Rust backend: `~/.local/bin/quiklight`
- Qt interface: `~/.local/share/quiklight-gui-qt/quiklight_gui.py`
- PySide6 Python: `~/.local/share/quiklight-gui-qt/venv-py315/bin/python`
- Config: `~/.local/share/quiklight-rust/config.toml`
- LED daemon: `~/.config/systemd/user/quiklight.service`
- KDE tray startup: `~/.config/autostart/quiklight-gui.desktop`

After confirming v0.3.4.5 is **already installed and working**, the startup consolidation helper can audit and standardize the **user-scoped** entry points without rewriting the executable or live config. Run in the directory with `consolidar_estavel.py` and the original v0.3.4.5 ZIP:

```bash
python3 consolidar_estavel.py --audit
python3 consolidar_estavel.py --activate
systemctl --user is-active quiklight.service
systemctl --user is-enabled quiklight.service
```

The audit checks GUI source integrity, optional compiled backend identity, segment layout and existing service startup path; it refuses unknown duplicate startup entries rather than deleting them. Activation creates a rollback snapshot, enables the **existing user service**, configures a single KDE GUI autostart, and opens the GUI if needed. Does **not** modify the immutable OS base. Follow the rollback command printed by the helper if needed.

For a fresh installation, **do not use this helper as an installer**. The complete reproducible v0.3.4.5 source distribution and accompanying Qt helper modules must first be published, then verified with `cargo check --locked`, `cargo test --locked`, `cargo build --release --locked`, and installed after reviewing service/startup configs.

## Windows

Windows is in scope. Windows capture implementation and GUI paths exist, and older Windows branches are available. However, **no Windows MultiStrip v0.3.4.5 stable package or one-click installer is confirmed**. Required before Windows release: build with Rust toolchain, provision Qt/PySide6, test monitor switching/capture, USB HID interface selection, controller fault isolation, real-time LED updates, autorun and shutdown, and backup/rollback on actual hardware.

## Security and licensing

Do not upload private `config.toml`, system journals, unique USB IDs, usernames, access keys or vendor firmware artifacts. Preserve upstream attributions and licenses. Review any executable before redistribution.
