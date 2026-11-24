# Stage02 GUI P03.1–P05

- P03.1: user confirmed global dynamic effect selection works without preselecting effect mode. Commit b04869cb0e68238837b0d9492dca3f6b8b2e5ea7.
- P04: guarded mode consistency and CPU rollback integration patch published at 2b0b7a97710cbc8ca907e421d234a045a58d57cb. Complete regression checklist not yet confirmed.
- P05: hue selection bars under ten global palette fields, complementary QColorDialog, HEX synchronization, commit on mouse release, no new timer. User confirmed functionality. Commit ff865cad647b4002ba2ed6920c3cf7781229162a.
- CPU: user noticed spikes to 5.7%; process attribution and measurement denominator unknown. Profile Rust driver, Stage02 Python GUI, exception daemon and compositor separately with GUI closed, visible, live preview and tray. Preserve P01, capture quality and session switching.
