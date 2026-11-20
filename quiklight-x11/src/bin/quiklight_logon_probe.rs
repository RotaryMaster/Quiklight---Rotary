//! Diagnostic-only DXGI/scrap probe for the Windows logon investigation.
//! Does not access or control USB devices. Never writes frames or screenshots.
//! Logs only access status and the aggregate RGB mean of the screen edges.
//! No privileges, services, registry entries or scheduled tasks are installed.
#[cfg(not(windows))]
fn main() {
    eprintln!("This diagnostic is only supported on Windows.");
}

#[cfg(windows)]
mod windows_probe {
    use std::env;
    use std::error::Error;
    use std::ffi::c_void;
    use std::fs::{File, OpenOptions};
    use std::io::{ErrorKind, Write};
    use std::path::PathBuf;
    use std::thread::sleep;
    use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
    use scrap::{Capturer, Display};

    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentProcessId() -> u32;
        fn ProcessIdToSessionId(process_id: u32, session_id: *mut u32) -> i32;
        fn WTSGetActiveConsoleSessionId() -> u32;
        fn GetLastError() -> u32;
    }
    #[link(name = "user32")]
    extern "system" {
        fn OpenInputDesktop(flags: u32, inherit: i32, desired_access: u32) -> *mut c_void;
        fn CloseDesktop(desktop: *mut c_void) -> i32;
    }

    fn session_info() -> String {
        unsafe {
            let pid = GetCurrentProcessId();
            let mut session = u32::MAX;
            let ok = ProcessIdToSessionId(pid, &mut session);
            let console = WTSGetActiveConsoleSessionId();
            format!(
                "pid={pid} process_session={} console_session={console}",
                if ok != 0 { session.to_string() } else { "unknown".into() }
            )
        }
    }

    fn desktop_access() -> String {
        // DESKTOP_READOBJECTS only; never request write, input or switch access.
        unsafe {
            let desktop = OpenInputDesktop(0, 0, 0x0001);
            if desktop.is_null() {
                format!("denied_or_unavailable(win32={})", GetLastError())
            } else {
                CloseDesktop(desktop);
                "ok".to_string()
            }
        }
    }

    fn edge_mean_rgb(frame: &[u8], width: usize, height: usize) -> Option<[u8; 3]> {
        if width == 0 || height == 0 || frame.len() < height.saturating_mul(4) {
            return None;
        }
        let stride = frame.len() / height;
        if stride < width.saturating_mul(4) {
            return None;
        }
        let mut sums = [0u64; 3];
        let mut n = 0u64;
        let sy = (height / 24).max(1);
        let sx = (width / 40).max(1);
        for y in (0..height).step_by(sy) {
            for x in (0..width).step_by(sx) {
                if x * 10 > width && x * 10 < width * 9
                    && y * 10 > height && y * 10 < height * 9 {
                    continue;
                }
                let i = y * stride + x * 4;
                if i + 2 >= frame.len() {
                    continue;
                }
                // DXGI scrap frame is BGRA.
                sums[0] += frame[i + 2] as u64;
                sums[1] += frame[i + 1] as u64;
                sums[2] += frame[i] as u64;
                n += 1;
            }
        }
        if n == 0 { return None; }
        Some([(sums[0] / n) as u8, (sums[1] / n) as u8, (sums[2] / n) as u8])
    }

    fn log_line(log: &mut File, msg: &str) -> Result<(), Box<dyn Error>> {
        let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
        writeln!(log, "unix={now} {msg}")?;
        log.flush()?;
        Ok(())
    }

    fn arguments() -> Result<(u64, PathBuf), Box<dyn Error>> {
        let mut seconds = 75u64;
        let mut path = env::temp_dir().join("quiklight-logon-probe.log");
        let mut args = env::args().skip(1);
        while let Some(arg) = args.next() {
            match arg.as_str() {
                "--seconds" => seconds = args.next().ok_or("missing --seconds value")?.parse()?,
                "--log" => path = PathBuf::from(args.next().ok_or("missing --log path")?),
                _ => return Err(format!("unknown argument: {arg}").into()),
            }
        }
        if !(5..=300).contains(&seconds) {
            return Err("--seconds must be between 5 and 300".into());
        }
        Ok((seconds, path))
    }

    pub fn run() -> Result<(), Box<dyn Error>> {
        let (seconds, path) = arguments()?;
        let mut log = OpenOptions::new().create(true).append(true).open(&path)?;
        log_line(&mut log, &format!(
            "START {} seconds={seconds} mode=read-only no-frames-saved",
            session_info()
        ))?;
        let start = Instant::now();
        let mut cap: Option<Capturer> = None;
        let mut tick = 0u64;

        while start.elapsed().as_secs() < seconds {
            let desktop = desktop_access();
            if cap.is_none() {
                match Display::primary().and_then(Capturer::new) {
                    Ok(c) => cap = Some(c),
                    Err(e) => {
                        log_line(&mut log, &format!("tick={tick} desktop={desktop} capture_init=error {:?}", e))?;
                        tick += 1;
                        sleep(Duration::from_secs(1));
                        continue;
                    }
                }
            }

            let mut recreate = false;
            let mut status = "unavailable".to_string();
            if let Some(c) = cap.as_mut() {
                let (width, height) = (c.width(), c.height());
                match c.frame() {
                    Ok(frame) => {
                        status = match edge_mean_rgb(&frame, width, height) {
                            Some([r, g, b]) => format!("frame=ok edge_mean_rgb={r},{g},{b}"),
                            None => "frame=invalid_dimensions".to_string(),
                        };
                    }
                    Err(e) if e.kind() == ErrorKind::WouldBlock => {
                        status = "frame=would_block".to_string();
                    }
                    Err(e) => {
                        status = format!("frame=error kind={:?} code={:?} msg={}", e.kind(), e.raw_os_error(), e);
                        recreate = true;
                    }
                }
            }
            if recreate {
                cap = None;
            }
            log_line(&mut log, &format!(
                "tick={tick} desktop={desktop} {status}"
            ))?;
            tick += 1;
            sleep(Duration::from_secs(1));
        }

        log_line(&mut log, "END")?;
        Ok(())
    }
}

#[cfg(windows)]
fn main() {
    if let Err(err) = windows_probe::run() {
        eprintln!("logon probe failed: {err}");
        std::process::exit(1);
    }
}
