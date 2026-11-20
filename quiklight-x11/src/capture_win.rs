//! Windows screen capture through `scrap`, with CPU-side downsampling to RGBx.
//! Desktop capture depends on the active Windows display and its permissions.
//! Windows gaming/DRM-protected content and performance are not yet validated.
//! This module shares the detection model with the Linux implementation.

use anyhow::{anyhow, bail, Result};
use std::cell::{Cell, RefCell};
use std::io::Read;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use crate::config::Config;

/// Detecção automática de barras pretas (letterbox / pillarbox).
///
/// Cada borda é varrida de fora para dentro até achar a primeira linha (ou coluna) em que a
/// IMAGEM CHEGA ÀS PONTAS. Legenda, letras e objetos no centro nunca chegam às pontas, então
/// não enganam. Cena escura ou tela preta com texto = sem resposta confiável: a barra atual
/// fica congelada. Imagem aparecendo dentro da barra: volta rápido ao normal. Barra nova só
/// vale depois de ficar estável.
#[derive(Default)]
struct BarState {
    cur: [usize; 2],              // barra confirmada: [topo/baixo, esquerda/direita]
    cand: [usize; 2],             // valor candidato em teste
    since: [Option<Instant>; 2],  // desde quando o candidato se repete
    last: [Option<Instant>; 2],   // última leitura do candidato
    sm: [f32; 4],                 // suavizado: [esq, topo, dir, baixo]
}

/// Leitura de um eixo em um frame.
#[derive(Clone, Copy)]
enum Obs {
    Unknown,     // nada confiável (cena escura, letras no centro, lados discordam): congela
    Bar(usize),  // barra de n linhas/colunas
}

impl BarState {
    fn feed(&mut self, i: usize, obs: Obs, now: Instant, add_ms: u64, rel_ms: u64) {
        let n = match obs {
            Obs::Bar(n) => n,
            Obs::Unknown => return,
        };
        let cur = self.cur[i];
        if n.abs_diff(cur) <= 1 {
            self.since[i] = None;
            return;
        }
        // Imagem aparecendo na barra libera rápido; barra nova só depois de ficar estável
        let need = if n < cur { rel_ms } else { add_ms };
        let same = self.since[i].is_some()
            && self.cand[i].abs_diff(n) <= 2
            && (self.cand[i] < cur) == (n < cur)
            && self.last[i]
                .map_or(false, |t| now.duration_since(t) < Duration::from_millis(700));
        if !same {
            self.cand[i] = n;
            self.since[i] = Some(now);
        }
        self.last[i] = Some(now);
        if let Some(s) = self.since[i] {
            if now.duration_since(s) >= Duration::from_millis(need) {
                self.cur[i] = n;
                self.since[i] = None;
            }
        }
    }
}

/// A linha é "conteúdo" se tem imagem nas pontas (~8% de cada lado) e cobertura mínima (25%).
/// `bright(p)`: o pixel p da linha é mais claro que o preto?
fn line_is_content(bright: &dyn Fn(usize) -> bool, len: usize) -> bool {
    if len < 8 { return false; }
    let z = (len * 8 / 100).max(3).min(len / 2);
    let need = (z / 4).max(2).min(z);
    let a = (0..z).filter(|&p| bright(p)).count();
    let b = ((len - z)..len).filter(|&p| bright(p)).count();
    let total = (0..len).filter(|&p| bright(p)).count();
    if (a >= need || b >= need) && total * 100 >= len * 25 { return true; }
    let lo = len / 6;
    let hi = len - lo;
    let n = hi - lo;
    let mut active = 0usize;
    let mut run = 0usize;
    let mut longest = 0usize;
    for p in lo..hi {
        if bright(p) { active += 1; run += 1; longest = longest.max(run); }
        else { run = 0; }
    }
    active * 100 >= n * 22 && total * 100 >= len * 12 && longest >= (len / 12).max(3)
}

/// Varre da borda para dentro. `bright(d, p)`: pixel p da linha d (contada a partir da borda).
/// Retorna a profundidade da primeira linha de conteúdo (2 seguidas, para ignorar fio/ruído)
/// ou None se não achou (cena escura, fade, só letras no centro).
fn scan_edge(bright: &dyn Fn(usize, usize) -> bool, len: usize, max_d: usize) -> Option<usize> {
    let content = |d: usize| -> bool { line_is_content(&|p| bright(d, p), len) };
    for d in 0..max_d {
        if content(d) && (d + 1 >= max_d || content(d + 1)) {
            return Some(d);
        }
    }
    None
}

/// Junta as leituras dos dois lados do mesmo eixo.
fn axis_obs(a: Option<usize>, b: Option<usize>, cur: usize) -> Obs {
    let norm = |n: usize| if n < 2 { 0 } else { n };
    match (a, b) {
        (Some(x), Some(y)) => {
            let (mn, mx) = (x.min(y), x.max(y));
            if mx - mn <= mx / 4 + 1 {
                Obs::Bar(norm(mn)) // os dois lados concordam (barras reais são simétricas)
            } else if mn + 1 < cur {
                Obs::Bar(norm(mn)) // imagem apareceu dentro da barra
            } else {
                Obs::Unknown
            }
        }
        (Some(x), None) | (None, Some(x)) => {
            if x + 1 < cur {
                Obs::Bar(norm(x))
            } else {
                Obs::Unknown
            }
        }
        (None, None) => Obs::Unknown,
    }
}

/// Lê as barras de um frame RGBx. Retorna [topo/baixo, esquerda/direita].
/// `cur`: barras já confirmadas, usadas para medir as pontas só dentro da área da imagem.
fn sparse_center_obs(data: &[u8], cw: usize, ch: usize) -> Option<[Obs; 2]> {
    let threshold: u8 = 40;
    let mut active = 0usize;
    let (mut min_x, mut min_y) = (cw, ch);
    let (mut max_x, mut max_y) = (0usize, 0usize);
    for y in 0..ch {
        for x in 0..cw {
            let k = (y * cw + x) * 4;
            if data[k].max(data[k + 1]).max(data[k + 2]) > threshold {
                active += 1;
                min_x = min_x.min(x); max_x = max_x.max(x);
                min_y = min_y.min(y); max_y = max_y.max(y);
            }
        }
    }
    if active < (cw * ch / 300).max(8) || min_x >= cw || min_y >= ch { return None; }
    let bw = max_x - min_x + 1;
    let bh = max_y - min_y + 1;
    if bw * 8 < cw || bh * 10 < ch { return None; }
    let (left, right) = (min_x, cw - 1 - max_x);
    let (top, bottom) = (min_y, ch - 1 - max_y);
    if left.abs_diff(right) > cw / 6 + 1 || top.abs_diff(bottom) > ch / 6 + 1 { return None; }
    let vert = if top.min(bottom) >= 2 { Obs::Bar(top.min(bottom)) } else { Obs::Unknown };
    let horiz = if left.min(right) >= 2 { Obs::Bar(left.min(right)) } else { Obs::Unknown };
    if matches!(vert, Obs::Unknown) && matches!(horiz, Obs::Unknown) { None } else { Some([vert, horiz]) }
}

fn detect_bars(data: &[u8], cw: usize, ch: usize, cur: [usize; 2]) -> [Obs; 2] {
    if cw < 8 || ch < 8 || data.len() < cw * ch * 4 {
        return [Obs::Unknown; 2];
    }
    let peak = |x: usize, y: usize| -> u32 {
        let o = (y * cw + x) * 4;
        data[o].max(data[o + 1]).max(data[o + 2]) as u32
    };
    // Nível de preto do vídeo (costuma ser 16-25, não 0), medido nas bordas
    let level = |a: u32, b: u32| -> u32 {
        if a.min(b) <= 30 && a.abs_diff(b) <= 10 {
            (a.min(b) + 12).clamp(14, 36)
        } else {
            14
        }
    };
    let vscan = |x0: usize, x1: usize| -> Obs {
        let n = x1 - x0;
        if n < 8 {
            return Obs::Unknown;
        }
        let tm = (x0..x1).map(|x| peak(x, 0)).sum::<u32>() / n as u32;
        let bm = (x0..x1).map(|x| peak(x, ch - 1)).sum::<u32>() / n as u32;
        let tv = level(tm, bm);
        let mv = ch * 2 / 5;
        let t = scan_edge(&|d, p| peak(x0 + p, d) > tv, n, mv);
        let b = scan_edge(&|d, p| peak(x0 + p, ch - 1 - d) > tv, n, mv);
        axis_obs(t, b, cur[0])
    };
    let hscan = |y0: usize, y1: usize| -> Obs {
        let n = y1 - y0;
        if n < 8 {
            return Obs::Unknown;
        }
        let lm = (y0..y1).map(|y| peak(0, y)).sum::<u32>() / n as u32;
        let rm = (y0..y1).map(|y| peak(cw - 1, y)).sum::<u32>() / n as u32;
        let th = level(lm, rm);
        let mh = cw * 2 / 5;
        let l = scan_edge(&|d, p| peak(d, y0 + p) > th, n, mh);
        let r = scan_edge(&|d, p| peak(cw - 1 - d, y0 + p) > th, n, mh);
        axis_obs(l, r, cur[1])
    };
    let nb = |o: Obs| -> usize {
        match o {
            Obs::Bar(n) => n,
            Obs::Unknown => 0,
        }
    };
    // 1ª passada: frame inteiro. 2ª: mede as pontas só dentro da área sem as barras do outro eixo.
    let v1 = vscan(0, cw);
    let h1 = hscan(0, ch);
    let xm = cur[1].max(nb(h1)).min(cw * 2 / 5);
    let ym = cur[0].max(nb(v1)).min(ch * 2 / 5);
    let v = if xm == 0 { v1 } else { vscan(xm, cw - xm) };
    let h = if ym == 0 { h1 } else { hscan(ym, ch - ym) };
    // Skip the 2D fallback when both axes were already determined.
    if matches!(v, Obs::Unknown) || matches!(h, Obs::Unknown) {
        if let Some(center) = sparse_center_obs(data, cw, ch) {
            let vert = if matches!(v, Obs::Unknown) { center[0] } else { v };
            let horiz = if matches!(h, Obs::Unknown) { center[1] } else { h };
            return [vert, horiz];
        }
    }
    [v, h]
}

/// Memória do modo cor dominante (evita oscilar entre duas cores parecidas).
#[derive(Default)]
pub struct DomState {
    bucket: Option<usize>,
    color: [f32; 3],
    init: bool,
}

pub struct Capturer {
    latest: Arc<Mutex<Option<Vec<u8>>>>,
    alive: Arc<AtomicBool>,
    cw: usize,
    ch: usize,
    last_check: Cell<Instant>,
    bars: RefCell<BarState>,
}

impl Capturer {
    pub fn new(cfg: &Config) -> Result<Self> {
        let (cw, ch) = (cfg.cap_w, cfg.cap_h);
        let latest: Arc<Mutex<Option<Vec<u8>>>> = Arc::new(Mutex::new(None));
        let alive = Arc::new(AtomicBool::new(true));
        let idx: Option<usize> = cfg.monitor.as_ref().and_then(|m| m.trim().parse::<usize>().ok());
        {
            let latest = Arc::clone(&latest);
            let alive = Arc::clone(&alive);
            thread::spawn(move || {
                // Distinguish temporary DXGI access loss from worker termination.
                // If this thread unexpectedly exits, the rest of the backend can
                // still detect a real failure through health().
                struct WorkerGuard(Arc<AtomicBool>);
                impl Drop for WorkerGuard {
                    fn drop(&mut self) {
                        self.0.store(false, Ordering::SeqCst);
                    }
                }
                let _guard = WorkerGuard(Arc::clone(&alive));
                let mut cap: Option<scrap::Capturer> = None;
                let mut last_notice = Instant::now() - Duration::from_secs(20);
                loop {
                    if cap.is_none() {
                        // A desktop switch (Win+L / UAC / unlock) invalidates DXGI
                        // duplication. The normal user cannot capture Winlogon;
                        // wait and retry without terminating the LED backend.
                        let display = match idx {
                            Some(i) => scrap::Display::all().ok()
                                .and_then(|v| v.into_iter().nth(i)),
                            None => scrap::Display::primary().ok(),
                        };
                        cap = display.and_then(|d| scrap::Capturer::new(d).ok());
                        if cap.is_none() {
                            if last_notice.elapsed() >= Duration::from_secs(15) {
                                eprintln!("Captura Windows temporariamente indisponível; tentando novamente após desbloqueio.");
                                last_notice = Instant::now();
                            }
                            thread::sleep(Duration::from_millis(900));
                            continue;
                        }
                        eprintln!("Captura Windows conectada/reconectada.");
                    }

                    let mut reconnect = false;
                    if let Some(c) = cap.as_mut() {
                        let (w, h) = (c.width(), c.height());
                        match c.frame() {
                            Ok(frame) if w > 0 && h > 0 => {
                                let stride = frame.len() / h;
                                if stride < w.saturating_mul(4) {
                                    reconnect = true;
                                } else {
                                    let mut out = vec![0u8; cw * ch * 4];
                                    for y in 0..ch {
                                        for x in 0..cw {
                                            let (mut rs, mut gs, mut bs) = (0u32, 0u32, 0u32);
                                            for (ox, oy) in [(1usize, 1usize), (3, 1), (1, 3), (3, 3)] {
                                                let sx = ((x * 4 + ox) * w / (cw * 4)).min(w - 1);
                                                let sy = ((y * 4 + oy) * h / (ch * 4)).min(h - 1);
                                                let o = sy * stride + sx * 4;
                                                if o + 2 >= frame.len() {
                                                    reconnect = true;
                                                    break;
                                                }
                                                bs += frame[o] as u32;
                                                gs += frame[o + 1] as u32;
                                                rs += frame[o + 2] as u32;
                                            }
                                            if reconnect {
                                                break;
                                            }
                                            let d = (y * cw + x) * 4;
                                            out[d] = (rs / 4) as u8;
                                            out[d + 1] = (gs / 4) as u8;
                                            out[d + 2] = (bs / 4) as u8;
                                            out[d + 3] = 255;
                                        }
                                        if reconnect {
                                            break;
                                        }
                                    }
                                    if !reconnect {
                                        if let Ok(mut g) = latest.lock() {
                                            *g = Some(out);
                                        }
                                    }
                                }
                            }
                            Ok(_) => reconnect = true,
                            Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => {
                                thread::sleep(Duration::from_millis(3));
                            }
                            Err(e) => {
                                if last_notice.elapsed() >= Duration::from_secs(3) {
                                    eprintln!("Captura Windows perdida: {e}; aguardando reconexão.");
                                    last_notice = Instant::now();
                                }
                                reconnect = true;
                            }
                        }
                    }
                    if reconnect {
                        // Releasing the old capturer before acquiring a new one
                        // follows the DXGI duplication contract.
                        cap = None;
                        thread::sleep(Duration::from_millis(500));
                    }
                }
            });
        }
        eprintln!("Captura Windows iniciada ({cw}x{ch})");
        Ok(Self {
            latest,
            alive,
            cw,
            ch,
            last_check: Cell::new(Instant::now()),
            bars: RefCell::new(BarState::default()),
        })
    }

    /// Devolve as cores de cada fita (índice = número da fita).
    pub fn grab(&self, cfg: &Config) -> Result<Vec<Vec<(u8, u8, u8)>>> {
        // A cada 2 s confere se o ambiente mudou (Desktop <-> Gaming)
        if !self.alive.load(Ordering::SeqCst) {
            bail!(
                "A captura do Windows foi encerrada. Verifique a disponibilidade da tela e as permissões de captura."
            );
        }

        let segs = cfg.segments();
        let counts = cfg.leds_per_device();

        let data = match self.latest.lock().ok().and_then(|g| g.clone()) {
            Some(d) => d,
            None => {
                // ainda sem imagem: tudo apagado
                return Ok(counts.iter().map(|&n| vec![(0, 0, 0); n]).collect());
            }
        };

        let cw = self.cw;
        let ch = self.ch;

        // Área de captura (retângulo) dentro da tela, em pixels da captura
        let pct = |v: f32| v.clamp(0.0, 45.0) / 100.0;
        let rx0 = (pct(cfg.inset_left) * cw as f32) as usize;
        let ry0 = (pct(cfg.inset_top) * ch as f32) as usize;
        let rx1 = (cw - (pct(cfg.inset_right) * cw as f32) as usize)
            .max(rx0 + 2)
            .min(cw);
        let ry1 = (ch - (pct(cfg.inset_bottom) * ch as f32) as usize)
            .max(ry0 + 2)
            .min(ch);
        let (rx0, ry0, rx1, ry1) = self.apply_bars(&data, cfg, (rx0, ry0, rx1, ry1));
        let th = cfg.border.max(1);
        let vivid = cfg.color_mode.eq_ignore_ascii_case("vivid");
        let neutral_floor = if cfg.accuracy { 0.25 } else { 0.03 };

        let pixel = |py: usize, px: usize| -> (u8, u8, u8) {
            let off = (py * cw + px) * 4;
            (data[off], data[off + 1], data[off + 2]) // RGBx
        };

        let avg = |x0: usize, x1: usize, y0: usize, y1: usize| -> (u8, u8, u8) {
            let (mut rs, mut gs, mut bs, mut ws) = (0f32, 0f32, 0f32, 0f32);
            for py in y0..y1.min(ch) {
                for px in x0..x1.min(cw) {
                    let (r, g, b) = pixel(py, px);
                    let (rf, gf, bf) = (r as f32, g as f32, b as f32);
                    let w = if vivid {
                        let mx = rf.max(gf).max(bf);
                        let mn = rf.min(gf).min(bf);
                        let s = if mx > 0.0 { (mx - mn) / mx } else { 0.0 };
                        crate::color_fidelity::vivid_weight(
                            neutral_floor + s * (mx / 255.0), cfg.adaptive_fidelity_strength(),
                        )
                    } else {
                        1.0
                    };
                    rs += rf * w;
                    gs += gf * w;
                    bs += bf * w;
                    ws += w;
                }
            }
            if ws <= 0.0 {
                return (0, 0, 0);
            }
            ((rs / ws) as u8, (gs / ws) as u8, (bs / ws) as u8)
        };

        let mut out: Vec<Vec<(u8, u8, u8)>> =
            counts.iter().map(|&n| Vec::with_capacity(n)).collect();

        for s in &segs {
            let n = s.leds;
            if n == 0 {
                continue;
            }
            for i in 0..n {
                let j = if s.reverse { n - 1 - i } else { i };
                let (x0, x1, y0, y1) = match s.edge.as_str() {
                    "left" => {
                        let y0 = ry0 + j * (ry1 - ry0) / n;
                        let y1 = (ry0 + (j + 1) * (ry1 - ry0) / n).max(y0 + 1);
                        (rx0, (rx0 + th).min(rx1), y0, y1)
                    }
                    "right" => {
                        let y0 = ry0 + j * (ry1 - ry0) / n;
                        let y1 = (ry0 + (j + 1) * (ry1 - ry0) / n).max(y0 + 1);
                        (rx1.saturating_sub(th).max(rx0), rx1, y0, y1)
                    }
                    "bottom" => {
                        let x0 = rx0 + j * (rx1 - rx0) / n;
                        let x1 = (rx0 + (j + 1) * (rx1 - rx0) / n).max(x0 + 1);
                        (x0, x1, ry1.saturating_sub(th).max(ry0), ry1)
                    }
                    _ => {
                        // top
                        let x0 = rx0 + j * (rx1 - rx0) / n;
                        let x1 = (rx0 + (j + 1) * (rx1 - rx0) / n).max(x0 + 1);
                        (x0, x1, ry0, (ry0 + th).min(ry1))
                    }
                };
                let (r, g, b) = avg(x0, x1, y0, y1);
                out[s.device].push(process(r, g, b, cfg));
            }
        }

        Ok(out)
    }

    fn health(&self) -> Result<()> {
        if !self.alive.load(Ordering::SeqCst) {
            bail!("A captura do Windows foi encerrada. Verifique a disponibilidade da tela e as permissões de captura.");
        }
        Ok(())
    }

    /// Barras pretas atuais (suavizadas) em pixels da captura.
    fn bars_px(&self, data: &[u8], speed: f32) -> [usize; 4] {
        let mut st = self.bars.borrow_mut();
        let now = Instant::now();
        let sp = speed.clamp(1.0, 10.0);
        let add_ms = (2400.0 / sp) as u64;
        let rel_ms = (add_ms / 5).max(80);
        let obs = detect_bars(data, self.cw, self.ch, st.cur);
        for i in 0..2 {
            st.feed(i, obs[i], now, add_ms, rel_ms);
        }
        // Diagnóstico leve, apenas no Windows e somente com auto_crop ligado.
        // Não altera o detector e não registra imagens nem configurações privadas.
        if self.last_check.get().elapsed() >= Duration::from_secs(2) {
            self.last_check.set(now);
            let fmt = |o: Obs| -> String {
                match o {
                    Obs::Unknown => "?".to_string(),
                    Obs::Bar(n) => n.to_string(),
                }
            };
            eprintln!(
                "AutoCrop Win: observado vertical={} horizontal={} | confirmado vertical={} horizontal={}",
                fmt(obs[0]), fmt(obs[1]), st.cur[0], st.cur[1]
            );
        }
        let tgt = [st.cur[1], st.cur[0], st.cur[1], st.cur[0]]; // [esq, topo, dir, baixo]
        for i in 0..4 {
            let d = tgt[i] as f32 - st.sm[i];
            st.sm[i] += d * (0.05 + 0.04 * sp);
        }
        [st.sm[0].round() as usize, st.sm[1].round() as usize, st.sm[2].round() as usize, st.sm[3].round() as usize]
    }

    fn apply_bars(&self, data: &[u8], cfg: &Config, r: (usize, usize, usize, usize)) -> (usize, usize, usize, usize) {
        if !cfg.auto_crop {
            return r;
        }
        let b = self.bars_px(data, cfg.crop_speed);
        let (x0, y0, x1, y1) = r;
        let nx0 = x0.max(b[0]);
        let ny0 = y0.max(b[1]);
        let nx1 = x1.min(self.cw.saturating_sub(b[2]));
        let ny1 = y1.min(self.ch.saturating_sub(b[3]));
        if nx1 < nx0 + 4 || ny1 < ny0 + 4 {
            return r;
        }
        (nx0, ny0, nx1, ny1)
    }

    fn region(&self, cfg: &Config) -> (usize, usize, usize, usize) {
        let (cw, ch) = (self.cw, self.ch);
        let pct = |v: f32| v.clamp(0.0, 45.0) / 100.0;
        let rx0 = (pct(cfg.inset_left) * cw as f32) as usize;
        let ry0 = (pct(cfg.inset_top) * ch as f32) as usize;
        let rx1 = (cw - (pct(cfg.inset_right) * cw as f32) as usize).max(rx0 + 2).min(cw);
        let ry1 = (ch - (pct(cfg.inset_bottom) * ch as f32) as usize).max(ry0 + 2).min(ch);
        (rx0, ry0, rx1, ry1)
    }

    /// Cor dominante da área de captura (uma só cor para todos os LEDs), 0..255.
    pub fn grab_dominant(&self, cfg: &Config, st: &mut DomState) -> Result<[f32; 3]> {
        self.health()?;
        let data = match self.latest.lock().ok().and_then(|g| g.clone()) {
            Some(d) => d,
            None => return Ok([0.0; 3]),
        };
        let rect = self.apply_bars(&data, cfg, self.region(cfg));
        Ok(dominant_core(&data, self.cw, rect, cfg, st))
    }

    /// Cores dominantes por zona. 2 estados = esquerda/direita; 4 = esquerda, direita, topo, baixo.
    pub fn grab_zones(&self, cfg: &Config, sts: &mut [DomState]) -> Result<Vec<[f32; 3]>> {
        self.health()?;
        let data = match self.latest.lock().ok().and_then(|g| g.clone()) {
            Some(d) => d,
            None => return Ok(vec![[0.0; 3]; sts.len()]),
        };
        let cw = self.cw;
        let (x0, y0, x1, y1) = self.apply_bars(&data, cfg, self.region(cfg));
        let mut out = Vec::new();
        if sts.len() == 2 {
            let mid = (x0 + x1) / 2;
            out.push(dominant_core(&data, cw, (x0, y0, mid, y1), cfg, &mut sts[0]));
            out.push(dominant_core(&data, cw, (mid, y0, x1, y1), cfg, &mut sts[1]));
        } else {
            let depth = cfg.zone_depth.clamp(10.0, 50.0) / 100.0;
            let dw = (((x1 - x0) as f32 * depth) as usize).max(2);
            let dh = (((y1 - y0) as f32 * depth) as usize).max(2);
            out.push(dominant_core(&data, cw, (x0, y0, x0 + dw, y1), cfg, &mut sts[0]));
            out.push(dominant_core(&data, cw, (x1 - dw, y0, x1, y1), cfg, &mut sts[1]));
            out.push(dominant_core(&data, cw, (x0, y0, x1, y0 + dh), cfg, &mut sts[2]));
            out.push(dominant_core(&data, cw, (x0, y1 - dh, x1, y1), cfg, &mut sts[3]));
        }
        Ok(out)
    }
}

/// Cor dominante de um retângulo (pixels da captura, RGBx). Devolve 0..255.
fn dominant_core(
    data: &[u8],
    cw: usize,
    rect: (usize, usize, usize, usize),
    cfg: &Config,
    st: &mut DomState,
) -> [f32; 3] {
    let (rx0, ry0, rx1, ry1) = rect;
    const NB: usize = 24;
    let mut wsum = [0f32; NB];
    let mut rs = [0f32; NB];
    let mut gs = [0f32; NB];
    let mut bs = [0f32; NB];
    let mut cnt = [0u32; NB];
    let (mut vsum, mut n) = (0f32, 0f32);
    let (mut ar, mut ag, mut ab) = (0f32, 0f32, 0f32);
    let mut neutral_cnt = 0f32;
    // 0 = só a área conta; 1 = cores vibrantes têm muito mais peso
    let q = cfg.dom_vibrance.clamp(0.0, 1.0);

    for py in ry0..ry1 {
        for px in rx0..rx1 {
            let off = (py * cw + px) * 4;
            let r = data[off] as f32 / 255.0;
            let g = data[off + 1] as f32 / 255.0;
            let bl = data[off + 2] as f32 / 255.0;
            let mx = r.max(g).max(bl);
            let mn = r.min(g).min(bl);
            let d = mx - mn;
            vsum += mx;
            n += 1.0;
            ar += r;
            ag += g;
            ab += bl;
            if mx >= 0.2 && d < 0.08 {
                neutral_cnt += 1.0;
            }
            if mx < 0.08 || d < 0.05 {
                continue; // ignora preto, cinza e branco
            }
            let h6 = if mx == r {
                ((g - bl) / d).rem_euclid(6.0)
            } else if mx == g {
                (bl - r) / d + 2.0
            } else {
                (r - g) / d + 4.0
            };
            let k = (((h6 / 6.0) * NB as f32) as usize).min(NB - 1);
            // Peso: área (com redução para tons quase cinza) + preferência por vibrantes
            let w = (1.0 - q) * (d / 0.15).min(1.0) + q * d;
            wsum[k] += w;
            rs[k] += r * w;
            gs[k] += g * w;
            bs[k] += bl * w;
            cnt[k] += 1;
        }
    }

    let n = n.max(1.0);
    let mean_v = vsum / n;
    let mut best = 0usize;
    for i in 1..NB {
        if wsum[i] > wsum[best] {
            best = i;
        }
    }
    // Histerese: só troca de cor se a nova for bem mais forte
    let mut pick = best;
    if let Some(pb) = st.bucket {
        if pb != best && wsum[best] < wsum[pb] * 1.25 {
            pick = pb;
        }
    }

    // Neutro (branco/transparente) que ocupa mais área que a cor escolhida vence
    let neutral_share = neutral_cnt / n;
    let cover_pick = cnt[pick] as f32 / n;
    let neutral_wins = cfg.accuracy && neutral_share > 0.3 && neutral_share > cover_pick * 1.5;

    let target: [f32; 3];
    if !neutral_wins && wsum[pick] > 0.003 * n {
        st.bucket = Some(pick);
        let w = wsum[pick];
        let avg = [rs[pick] / w, gs[pick] / w, bs[pick] / w];
        let coverage = cnt[pick] as f32 / n;
        let m = avg[0].max(avg[1]).max(avg[2]).max(0.001);
        let k = (0.10 + mean_v * 1.2 + coverage * 1.5).clamp(0.0, 1.0);
        let s = cfg.dom_scene.clamp(0.0, 1.0);
        let level = (1.0 - s) + s * k;
        let fid = cfg.dom_fidelity.clamp(0.0, 1.0);
        let mut c = [0f32; 3];
        for i in 0..3 {
            let scene_col = avg[i] / m * level;
            c[i] = scene_col * (1.0 - fid) + avg[i] * fid;
        }
        target = process_f(c[0], c[1], c[2], cfg);
    } else {
        // cena sem cor forte: usa a média da área
        st.bucket = None;
        target = process_f(ar / n, ag / n, ab / n, cfg);
    }

    let a = cfg.dom_smooth.clamp(0.0, 0.995).powf(60.0 / cfg.fps.max(1) as f32);
    if !st.init {
        st.color = target;
        st.init = true;
    } else {
        for i in 0..3 {
            st.color[i] = a * st.color[i] + (1.0 - a) * target[i];
        }
    }
    st.color
}

impl Drop for Capturer {
    fn drop(&mut self) {
    }
}

pub fn smooth(current: &[(u8, u8, u8)], prev: &[(u8, u8, u8)], factor: f32) -> Vec<(u8, u8, u8)> {
    current
        .iter()
        .zip(prev.iter())
        .map(|(&(r, g, b), &(pr, pg, pb))| {
            (
                (factor * pr as f32 + (1.0 - factor) * r as f32) as u8,
                (factor * pg as f32 + (1.0 - factor) * g as f32) as u8,
                (factor * pb as f32 + (1.0 - factor) * b as f32) as u8,
            )
        })
        .collect()
}

/// Processamento de cor em float (entrada 0..1, saída 0..255).
/// Sem "acurácia": tratamento clássico. Com "acurácia": proteção de neutros,
/// balanço de branco e gamma por canal.
pub fn process_f(r: f32, g: f32, b: f32, cfg: &Config) -> [f32; 3] {
    let (mut rf, mut gf, mut bf) = (r, g, b);
    let acc = cfg.accuracy;
    let adjustment = crate::color_fidelity::adjustment(
        r, g, b, cfg.adaptive_fidelity_strength(),
        cfg.adaptive_light_strength(), cfg.adaptive_dark_strength(), cfg.saturation,
    );

    // Proteção de neutros: branco, cinza e transparente não ganham tinta
    if acc {
        let d = rf.max(gf).max(bf) - rf.min(gf).min(bf);
        const THR: f32 = 0.15;
        if d < THR {
            let x = (d / THR).clamp(0.0, 1.0);
            let f = x * x * (3.0 - 2.0 * x);
            let lum = (rf + gf + bf) / 3.0;
            rf = lum + (rf - lum) * f;
            gf = lum + (gf - lum) * f;
            bf = lum + (bf - lum) * f;
        }
    }

    // Saturação
    let mx = rf.max(gf).max(bf);
    let mn = rf.min(gf).min(bf);
    if mx > 0.0 {
        let sat = (mx - mn) / mx;
        if sat > 0.0 {
            let scale = (sat * adjustment.saturation_multiplier).min(1.0) / sat;
            rf = (mx - (mx - rf) * scale).max(0.0);
            gf = (mx - (mx - gf) * scale).max(0.0);
            bf = (mx - (mx - bf) * scale).max(0.0);
        }
    }

    // Contraste (em torno do meio)
    let c = cfg.contrast;
    if (c - 1.0).abs() > 0.001 {
        for v in [&mut rf, &mut gf, &mut bf] {
            *v = ((*v - 0.5) * c + 0.5).clamp(0.0, 1.0);
        }
    }

    let gm = cfg.gamma.max(0.1);
    if acc {
        // Balanço de branco (ganho por canal) e gamma por canal: maior = mais profundo
        rf = (rf * cfg.gain_r).clamp(0.0, 1.0);
        gf = (gf * cfg.gain_g).clamp(0.0, 1.0);
        bf = (bf * cfg.gain_b).clamp(0.0, 1.0);
        [
            (rf.powf(gm * cfg.gamma_r.max(0.1)) * 255.0 * adjustment.output_scale).min(255.0),
            (gf.powf(gm * cfg.gamma_g.max(0.1)) * 255.0 * adjustment.output_scale).min(255.0),
            (bf.powf(gm * cfg.gamma_b.max(0.1)) * 255.0 * adjustment.output_scale).min(255.0),
        ]
    } else {
        // Clássico: maior = tons médios mais claros
        let inv = 1.0 / gm;
        [
            (rf.powf(inv) * 255.0 * adjustment.output_scale).min(255.0),
            (gf.powf(inv) * 255.0 * adjustment.output_scale).min(255.0),
            (bf.powf(inv) * 255.0 * adjustment.output_scale).min(255.0),
        ]
    }
}

fn process(r: u8, g: u8, b: u8, cfg: &Config) -> (u8, u8, u8) {
    let o = process_f(r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0, cfg);
    (o[0] as u8, o[1] as u8, o[2] as u8)
}
