#[cfg(unix)]
mod platform {
use anyhow::{bail, Result};
use std::collections::BTreeMap;
use std::fs;
use std::path::PathBuf;

const VENDOR_ID: u32 = 0x1A86;
const PRODUCT_ID: u32 = 0xFE07;

/// Uma entrada por fita (dispositivo USB físico), ordenada pela porta USB.
fn find_hidraws() -> Result<Vec<PathBuf>> {
    let target = format!("0003:{:08X}:{:08X}", VENDOR_ID, PRODUCT_ID);
    let mut by_usb: BTreeMap<PathBuf, PathBuf> = BTreeMap::new();

    for entry in fs::read_dir("/sys/bus/hid/devices")? {
        let dev = entry?.path();
        let Ok(content) = fs::read_to_string(dev.join("uevent")) else {
            continue;
        };
        if !content.to_uppercase().contains(&target) {
            continue;
        }

        // Pasta do dispositivo USB (dois níveis acima da interface HID)
        let usb = fs::canonicalize(&dev)
            .ok()
            .and_then(|p| p.parent().and_then(|x| x.parent()).map(|x| x.to_path_buf()))
            .unwrap_or_else(|| dev.clone());

        if let Ok(iter) = fs::read_dir(dev.join("hidraw")) {
            for he in iter.flatten() {
                let name = he.file_name().to_string_lossy().to_string();
                if name.starts_with("hidraw") {
                    let path = PathBuf::from(format!("/dev/{}", name));
                    by_usb
                        .entry(usb.clone())
                        .and_modify(|e| {
                            if path < *e {
                                *e = path.clone();
                            }
                        })
                        .or_insert(path);
                }
            }
        }
    }

    if by_usb.is_empty() {
        bail!(
            "Quiklight device not found (VID=0x{:04X}, PID=0x{:04X}).\n\
            Check that the USB cable is plugged in and the udev rule is installed.",
            VENDOR_ID,
            PRODUCT_ID
        );
    }
    Ok(by_usb.into_values().collect())
}

/// Abre as primeiras `n` fitas. Com `strict`, falha se houver menos de `n`.
pub fn open_devices(n: usize, strict: bool) -> Result<Vec<fs::File>> {
    let paths = find_hidraws()?;
    if strict && paths.len() < n {
        bail!(
            "A configuração usa {} fita(s), mas só {} foi/foram encontrada(s) no USB.",
            n,
            paths.len()
        );
    }
    let mut out = Vec::new();
    for (i, p) in paths.into_iter().take(n).enumerate() {
        eprintln!("Fita {}: {}", i + 1, p.display());
        out.push(fs::OpenOptions::new().read(true).write(true).open(&p)?);
    }
    Ok(out)
}

    pub type Dev = fs::File;
}

#[cfg(windows)]
mod platform {
    use anyhow::{anyhow, bail, Result};

    pub struct Dev(hidapi::HidDevice);

    impl std::io::Write for Dev {
        fn write(&mut self, buf: &[u8]) -> std::io::Result<usize> {
            self.0
                .write(buf)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))
        }
        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }

    /// Abre as primeiras `n` fitas. Com `strict`, falha se houver menos de `n`.
    pub fn open_devices(n: usize, strict: bool) -> Result<Vec<Dev>> {
        let api = hidapi::HidApi::new().map_err(|e| anyhow!("HID: {e}"))?;
        let mut infos: Vec<_> = api
            .device_list()
            .filter(|d| d.vendor_id() == 0x1A86 && d.product_id() == 0xFE07)
            .collect();
        if infos.is_empty() {
            bail!("Quiklight device not found (VID=0x1A86, PID=0xFE07).");
        }
        infos.sort_by(|a, b| a.path().cmp(b.path()));
        let mut seen: Vec<String> = Vec::new();
        let mut paths = Vec::new();
        for d in infos {
            let key = d.serial_number().unwrap_or("").to_string();
            if !key.is_empty() && seen.contains(&key) {
                continue;
            }
            seen.push(key);
            paths.push(d.path().to_owned());
        }
        if strict && paths.len() < n {
            bail!("A configuração usa {} fita(s), mas só {} foi/foram encontrada(s) no USB.", n, paths.len());
        }
        let mut devs = Vec::new();
        for p in paths.into_iter().take(n) {
            let dev = api.open_path(&p).map_err(|e| anyhow!("{e}"))?;
            devs.push(Dev(dev));
        }
        Box::leak(Box::new(api));
        Ok(devs)
    }
}

pub use platform::{open_devices, Dev};
