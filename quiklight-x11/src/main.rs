#[cfg(unix)]
mod capture;
#[cfg(windows)]
#[path = "capture_win.rs"]
mod capture;
mod music;
#[cfg(unix)]
mod audio;
#[cfg(windows)]
#[path = "audio_win.rs"]
mod audio;
mod config;
mod device;
mod effects;
mod output;
mod protocol;
mod color_fidelity;

use anyhow::{anyhow, Result};
use clap::Parser;
use config::Config;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

/// Ambilight driver for the Robobloq Quiklight LED strip (Wayland / KDE).
///
/// With no options it runs the capture loop using the config file. The flags
/// below override the config for this run; add --save to persist them.
#[derive(Parser, Debug)]
#[command(name = "quiklight", version, about, long_about = None)]
struct Cli {
    /// Capture this monitor instead of the primary one
    /// (index or name from `--list-monitors`, e.g. `1` or `DP-4`)
    #[arg(short = 'm', long, value_name = "INDEX|NAME")]
    monitor: Option<String>,

    /// Target frames per second
    #[arg(short = 'f', long, value_name = "N", value_parser = clap::value_parser!(u32).range(1..=240))]
    fps: Option<u32>,

    /// Capture resolution as WxH (see `--list-resolutions` for presets)
    #[arg(short = 'r', long, value_name = "WxH", value_parser = parse_resolution)]
    resolution: Option<(usize, usize)>,

    /// Global brightness sent to the device (0-255)
    #[arg(short = 'b', long, value_name = "0-255")]
    brightness: Option<u8>,

    /// Temporal smoothing: 0.0 = off … 0.95 = very smooth
    #[arg(short = 's', long, value_name = "F", value_parser = parse_smoothing)]
    smoothing: Option<f32>,

    /// Saturation boost: 1.0 = none, 2.0 = vivid
    #[arg(long, value_name = "F")]
    saturation: Option<f32>,

    /// Gamma correction: 1.0 = linear, >1 darkens midtones
    #[arg(long, value_name = "F")]
    gamma: Option<f32>,

    /// Border thickness sampled at each edge, in capture pixels
    #[arg(long, value_name = "PX")]
    border: Option<usize>,

    /// Number of LEDs across the top edge
    #[arg(long, value_name = "N")]
    top: Option<usize>,

    /// Number of LEDs on the right edge
    #[arg(long, value_name = "N")]
    right: Option<usize>,

    /// Number of LEDs on the left edge
    #[arg(long, value_name = "N")]
    left: Option<usize>,

    /// Use this config file instead of the default
    #[arg(short = 'c', long, value_name = "FILE")]
    config: Option<PathBuf>,

    /// List detected monitors and exit
    #[arg(long)]
    list_monitors: bool,

    /// List capture-resolution presets for the selected monitor and exit
    #[arg(long)]
    list_resolutions: bool,

    /// Persist the resulting options to the config file, then keep running
    #[arg(long)]
    save: bool,

    /// Turn the LEDs off (send a single black frame) and exit
    #[arg(long)]
    off: bool,

    /// Send a static RGB color once and exit without screen capture (for pre-logon startup)
    #[arg(long, value_name = "R,G,B", value_parser = parse_boot_rgb)]
    boot_color: Option<(u8, u8, u8)>,
}

impl Cli {
    /// Apply the options that were actually passed on top of the loaded config.
    fn apply(&self, cfg: &mut Config) {
        // Se o número de LEDs foi passado na linha de comando, ignora os [[segment]]
        if self.top.is_some() || self.right.is_some() || self.left.is_some() {
            cfg.segment.clear();
        }
        if let Some(v) = &self.monitor {
            cfg.monitor = Some(v.clone());
        }
        if let Some(v) = self.fps {
            cfg.fps = v;
        }
        if let Some((w, h)) = self.resolution {
            cfg.cap_w = w;
            cfg.cap_h = h;
        }
        if let Some(v) = self.brightness {
            cfg.brightness = v;
        }
        if let Some(v) = self.smoothing {
            cfg.smoothing = v;
        }
        if let Some(v) = self.saturation {
            cfg.saturation = v;
        }
        if let Some(v) = self.gamma {
            cfg.gamma = v;
        }
        if let Some(v) = self.border {
            cfg.border = v;
        }
        if let Some(v) = self.top {
            cfg.top = v;
        }
        if let Some(v) = self.right {
            cfg.right = v;
        }
        if let Some(v) = self.left {
            cfg.left = v;
        }
    }
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // --list-monitors works without a config file
    if cli.list_monitors {
        println!("No Wayland a tela é escolhida na janela do KDE que aparece na primeira execução.");
        return Ok(());
    }

    let config_path = cli.config.clone().unwrap_or_else(default_config_path);
    let mut cfg = Config::load(&config_path);
    cli.apply(&mut cfg);

    // Both one-shot commands work before Windows logon and never capture the screen.
    if cli.off {
        return turn_off(&cfg);
    }
    if let Some(rgb) = cli.boot_color {
        return turn_on_once(&cfg, rgb);
    }

    if cli.save {
        cfg.save(&config_path)?;
        eprintln!("Saved config → {}", config_path.display());
    }

    if cli.list_resolutions {
        println!("No Wayland a captura é reduzida direto para o tamanho cap_w x cap_h.");
        println!("Use qualquer valor, por exemplo:  quiklight --resolution 80x45");
        return Ok(());
    }

    run(&cfg, &config_path)
}

/// Marcado quando o sistema pede para o programa parar (systemctl stop, desligar, etc.).
static STOP: AtomicBool = AtomicBool::new(false);

#[cfg(unix)]
extern "C" fn on_stop(_sig: libc::c_int) {
    STOP.store(true, Ordering::SeqCst);
}

#[cfg(unix)]
fn install_stop_handler() {
    unsafe {
        libc::signal(libc::SIGTERM, on_stop as libc::sighandler_t);
        libc::signal(libc::SIGINT, on_stop as libc::sighandler_t);
    }
}

#[cfg(windows)]
fn install_stop_handler() {}

/// Apaga todas as fitas. Repete o quadro preto algumas vezes, com uma pausa curta,
/// para garantir que a fita realmente apague antes do programa sair.
fn blackout(devs: &mut [device::Dev], msg_ids: &mut [u8], counts: &[usize]) {
    for _ in 0..3 {
        for (i, d) in devs.iter_mut().enumerate() {
            if counts[i] == 0 {
                continue;
            }
            let black = vec![(0u8, 0u8, 0u8); counts[i]];
            let _ = protocol::send_frame(d, msg_ids[i], &black);
            msg_ids[i] = msg_ids[i].wrapping_add(1);
        }
        std::thread::sleep(Duration::from_millis(40));
    }
    eprintln!("Fitas apagadas ao encerrar.");
}

fn file_mtime(p: &PathBuf) -> Option<std::time::SystemTime> {
    std::fs::metadata(p).ok()?.modified().ok()
}

fn run(cfg0: &Config, config_path: &PathBuf) -> Result<()> {
    let mut cfg = cfg0.clone();
    eprintln!(
        "AutoCrop startup: config={} auto_crop={} crop_speed={}",
        config_path.display(), cfg.auto_crop, cfg.crop_speed
    );
    let mut mode = cfg.mode.to_lowercase();
    let needs_capture = !matches!(mode.as_str(), "static" | "effect");
    let capturer = if needs_capture {
        Some(capture::Capturer::new(&cfg)?)
    } else {
        None
    };
    let counts = cfg.leds_per_device();
    let mut devs = device::open_devices(counts.len(), true)?;
    let mut msg_ids: Vec<u8> = Vec::new();
    for (i, d) in devs.iter_mut().enumerate() {
        if counts[i] == 0 {
            msg_ids.push(0);
            continue;
        }
        // O brilho de hardware fica no máximo; o brilho real é feito por software
        msg_ids.push(protocol::init(d, 255, counts[i])?);
    }

    let mut prev: Vec<Vec<(u8, u8, u8)>> =
        counts.iter().map(|&n| vec![(0u8, 0u8, 0u8); n]).collect();
    let mut prevf: Vec<Vec<[f32; 3]>> = counts.iter().map(|&n| vec![[0.0f32; 3]; n]).collect();
    let mut dom = capture::DomState::default();
    let mut zst: Vec<capture::DomState> = (0..4).map(|_| capture::DomState::default()).collect();
    let mut stage = output::Stage::new(&counts, cfg.slew);
    let beat = audio::Beat::new();
    let mut music = music::Music::new();

    eprintln!(
        "Quiklight v{} (fidelidade adaptativa experimental) — modo {} | {} LEDs em {} fita(s) | fps={} nivel={}% potencia={}% slew={} acuracia={} adaptativa={} intensidade={}%",
        env!("CARGO_PKG_VERSION"),
        mode,
        cfg.leds(),
        counts.len(),
        cfg.fps,
        cfg.level,
        cfg.power_limit,
        cfg.slew,
        cfg.accuracy,
        cfg.adaptive_fidelity_enabled,
        cfg.adaptive_fidelity_strength()
    );

    // Daqui em diante, um pedido de parada apaga as fitas antes de sair
    install_stop_handler();
    let start = Instant::now();
    let mut last = start;
    let mut mtime = file_mtime(config_path);
    let mut last_check = start;
    let mut last_warn = start;
    let mut last_live = start;

    loop {
        if STOP.load(Ordering::SeqCst) {
            blackout(&mut devs, &mut msg_ids, &counts);
            return Ok(());
        }

        // Recarrega a configuração na hora quando o arquivo muda (atualização em tempo real)
        if last_check.elapsed() > Duration::from_millis(250) {
            last_check = Instant::now();
            let mt = file_mtime(config_path);
            if mt != mtime {
                mtime = mt;
                let new = match Config::try_load(config_path) {
                    Ok(value) => value,
                    Err(error) => {
                        // A configuração anterior permanece aplicada; nunca substitua
                        // silenciosamente os ajustes do usuário pelos padrões.
                        eprintln!("{error}; mantendo configuração anterior");
                        continue;
                    }
                };
                let new_mode = new.mode.to_lowercase();
                let new_needs = !matches!(new_mode.as_str(), "static" | "effect");
                if new_needs != needs_capture
                    || new.leds_per_device() != counts
                    || new.cap_w != cfg.cap_w
                    || new.cap_h != cfg.cap_h
                    || new.capture_limit != cfg.capture_limit
                    || (needs_capture && new.fps != cfg.fps)
                {
                    return Err(anyhow!("A configuração mudou de forma estrutural; reiniciando"));
                }
                cfg = new;
                mode = new_mode;
                stage.set_slew(cfg.slew);
                eprintln!(
                    "Configuração recarregada: modo {} nivel={}% potencia={}% acuracia={} auto_crop={} crop_speed={} adaptativa={} intensidade={}%",
                    mode, cfg.level, cfg.power_limit, cfg.accuracy, cfg.auto_crop, cfg.crop_speed,
                    cfg.adaptive_fidelity_enabled, cfg.adaptive_fidelity_strength()
                );
            }
        }

        let fps = if needs_capture { cfg.fps } else { cfg.fps.min(30) };
        let interval = Duration::from_secs_f64(1.0 / fps.max(1) as f64);
        let t0 = Instant::now();
        let gap = t0.duration_since(last);
        if gap > interval * 3 + Duration::from_millis(40) && last_warn.elapsed() > Duration::from_secs(2) {
            last_warn = Instant::now();
            eprintln!("Atraso de quadro: {} ms", gap.as_millis());
        }
        let dt = gap.as_secs_f32().clamp(0.001, 0.1);
        last = t0;
        let t = start.elapsed().as_secs_f32();

        let targets: Result<Vec<Vec<[f32; 3]>>> = match mode.as_str() {
            "static" => Ok(effects::static_frame(&counts, &cfg)),
            "effect" => Ok(effects::effect_frame(&counts, &cfg, t)),
            "dominant_lr" | "dominant_4" => {
                let nz = if mode == "dominant_4" { 4 } else { 2 };
                capturer
                    .as_ref()
                    .unwrap()
                    .grab_zones(&cfg, &mut zst[..nz])
                    .map(|z| effects::zones_frame(&counts, &cfg, &z))
            }
            "dominant" => capturer
                .as_ref()
                .unwrap()
                .grab_dominant(&cfg, &mut dom)
                .map(|c| counts.iter().map(|&n| vec![c; n]).collect()),
            "palette" => capturer.as_ref().unwrap().grab(&cfg).map(|frames| {
                let f: Vec<Vec<[f32; 3]>> = frames
                    .iter()
                    .map(|row| row.iter().map(|&(r, g, b)| [r as f32, g as f32, b as f32]).collect())
                    .collect();
                let mapped = effects::solid_frame(&cfg, &f);
                let a = if cfg.fade_time > 0.0 { (-dt / cfg.fade_time).exp() } else { 0.0 };
                effects::smooth_f(&mut prevf, mapped, a)
            }),
            _ => capturer.as_ref().unwrap().grab(&cfg).map(|frames| {
                let mut v: Vec<Vec<[f32; 3]>> = Vec::new();
                for i in 0..counts.len() {
                    v.push(frames[i].iter().map(|&(r, g, b)| [r as f32, g as f32, b as f32]).collect());
                }
                let a = if cfg.fade_time > 0.0 { (-dt / cfg.fade_time).exp() } else { 0.0 };
                effects::smooth_f(&mut prevf, v, a)
            }),
        };
        let targets = match targets {
            Ok(t) => t,
            Err(e) => {
                if STOP.load(Ordering::SeqCst) {
                    blackout(&mut devs, &mut msg_ids, &counts);
                    return Ok(());
                }
                return Err(e);
            }
        };

        let mut bytes = stage.step(&targets, dt, cfg.level, cfg.power_limit);

        // Modo música: aplica o estilo escolhido sobre o quadro final (só nos modos dinâmicos)
        let music_on = cfg.music && needs_capture;
        beat.set_enabled(music_on);
        if music_on {
            music.apply(&mut bytes, &cfg, &beat, t);
        }

        // Visualização ao vivo: só grava quando a janela pede (arquivo .want atualizado há < 5 s)
        if last_live.elapsed() > Duration::from_millis(100) {
            last_live = Instant::now();
            if let Some(dir) = std::env::var_os("XDG_RUNTIME_DIR").or_else(|| std::env::var_os("TEMP")) {
                let dir = std::path::PathBuf::from(dir);
                if cfg.music && needs_capture {
                    let afresh = std::fs::metadata(dir.join("quiklight-audio.want"))
                        .ok()
                        .and_then(|m| m.modified().ok())
                        .and_then(|x| x.elapsed().ok())
                        .map(|e| e.as_secs() < 5)
                        .unwrap_or(false);
                    if afresh {
                        let txt = format!("{:.3} {:.3} {:.3} {:.3} {:.3}\n", beat.level(), beat.treble(), beat.volume(), beat.rpm(), music.drive);
                        let tmp = dir.join("quiklight-audio.tmp");
                        if std::fs::write(&tmp, txt).is_ok() {
                            let _ = std::fs::rename(&tmp, dir.join("quiklight-audio.txt"));
                        }
                    }
                }
                let fresh = std::fs::metadata(dir.join("quiklight-live.want"))
                    .ok()
                    .and_then(|m| m.modified().ok())
                    .and_then(|t| t.elapsed().ok())
                    .map(|e| e.as_secs() < 5)
                    .unwrap_or(false);
                if fresh {
                    let mut buf: Vec<u8> = Vec::new();
                    for row in &bytes {
                        for &(r, g, b) in row {
                            buf.push(r);
                            buf.push(g);
                            buf.push(b);
                        }
                    }
                    let tmp = dir.join("quiklight-live.tmp");
                    if std::fs::write(&tmp, &buf).is_ok() {
                        let _ = std::fs::rename(&tmp, dir.join("quiklight-live.bin"));
                    }
                }
            }
        }
        for i in 0..counts.len() {
            if counts[i] == 0 {
                continue;
            }
            if let Err(e) = protocol::send_frame(&mut devs[i], msg_ids[i], &bytes[i]) {
                eprintln!("Erro ao enviar quadro para a fita {}: {}", i + 1, e);
                return Err(e);
            }
            msg_ids[i] = msg_ids[i].wrapping_add(1);
        }

        let elapsed = t0.elapsed();
        if elapsed < interval {
            std::thread::sleep(interval - elapsed);
        }
    }
}

/// Send one static frame and exit, leaving the LEDs at that color.
/// Can run in Windows Session 0 before a user logs on; no GUI, DXGI, sound or Qt.
/// The regular interactive Quiklight process takes over after user logon.
/// Uses the same known-working device enumeration/init/frame protocol as --off.
fn turn_on_once(cfg: &Config, rgb: (u8, u8, u8)) -> Result<()> {
    let counts = cfg.leds_per_device();
    let mut devs = device::open_devices(counts.len(), true)?;
    for (i, d) in devs.iter_mut().enumerate() {
        if counts[i] == 0 {
            continue;
        }
        let mut id = protocol::init(d, 255, counts[i])?;
        let frame = vec![rgb; counts[i]];
        for _ in 0..3 {
            protocol::send_frame(d, id, &frame)?;
            id = id.wrapping_add(1);
            std::thread::sleep(Duration::from_millis(40));
        }
    }
    eprintln!("Boot LED color applied: {},{},{}", rgb.0, rgb.1, rgb.2);
    Ok(())
}

/// Send a single all-black frame to every strip and exit (used as the service's ExecStop).
/// Does not capture the screen, so it works even when no display is available.
fn turn_off(cfg: &Config) -> Result<()> {
    let counts = cfg.leds_per_device();
    let mut devs = device::open_devices(counts.len(), false)?;
    for (i, d) in devs.iter_mut().enumerate() {
        if counts[i] == 0 {
            continue;
        }
        let msg_id = protocol::init(d, 255, counts[i])?;
        let black = vec![(0u8, 0u8, 0u8); counts[i]];
        let mut id = msg_id;
        for _ in 0..3 {
            protocol::send_frame(d, id, &black)?;
            id = id.wrapping_add(1);
            std::thread::sleep(Duration::from_millis(40));
        }
    }
    eprintln!("LEDs off.");
    Ok(())
}

fn default_config_path() -> PathBuf {
    dirs::data_dir()
        .unwrap_or_default()
        .join("quiklight-rust/config.toml")
}

/// Parse an explicit RGB triplet, without guessing a brightness level.
fn parse_boot_rgb(s: &str) -> Result<(u8, u8, u8), String> {
    let parts: Vec<&str> = s.split(',').collect();
    if parts.len() != 3 {
        return Err("expected RGB values as R,G,B (0-255 each)".to_string());
    }
    let parse = |v: &str| {
        v.trim().parse::<u8>()
            .map_err(|_| format!("invalid RGB channel '{v}' (use 0-255)"))
    };
    Ok((parse(parts[0])?, parse(parts[1])?, parse(parts[2])?))
}

fn parse_resolution(s: &str) -> Result<(usize, usize), String> {
    let (w, h) = s
        .split_once(|c| c == 'x' || c == 'X')
        .ok_or_else(|| format!("expected WxH, got '{s}'"))?;
    let w = w
        .trim()
        .parse::<usize>()
        .map_err(|_| format!("invalid width in '{s}'"))?;
    let h = h
        .trim()
        .parse::<usize>()
        .map_err(|_| format!("invalid height in '{s}'"))?;
    if w == 0 || h == 0 {
        return Err("width and height must be > 0".into());
    }
    Ok((w, h))
}

fn parse_smoothing(s: &str) -> Result<f32, String> {
    let v: f32 = s.parse().map_err(|_| format!("'{s}' isn't a number"))?;
    if (0.0..=0.95).contains(&v) {
        Ok(v)
    } else {
        Err("smoothing must be between 0.0 and 0.95".into())
    }
}
