//! Modo música: aplica o estilo escolhido sobre os quadros já prontos (RGB final).
use crate::audio::Beat;
use crate::config::Config;

type Px = (u8, u8, u8);

pub struct Music {
    idx: usize,
    wave_t0: f32,
    armed: bool,
    last_beat: f32,
    frame: u32,
    /// O que está movendo a luz agora (0..1), mostrado no medidor da janela
    pub drive: f32,
    ref_rpm: f32,
    shift_t: f32,
    last_t: f32,
    phase: f32,
    chase: f32,
    burst_t0: f32,
    hb_t0: f32,
    echo: f32,
    flip: bool,
}

fn scale(p: Px, g: f32) -> Px {
    ((p.0 as f32 * g) as u8, (p.1 as f32 * g) as u8, (p.2 as f32 * g) as u8)
}

fn mix(p: Px, to: (f32, f32, f32), w: f32) -> Px {
    let w = w.clamp(0.0, 1.0);
    let f = |a: u8, b: f32| (a as f32 + (b - a as f32) * w).clamp(0.0, 255.0) as u8;
    (f(p.0, to.0), f(p.1, to.1), f(p.2, to.2))
}

fn lum(p: Px) -> f32 {
    0.299 * p.0 as f32 + 0.587 * p.1 as f32 + 0.114 * p.2 as f32
}

fn all(bytes: &mut Vec<Vec<Px>>, mut f: impl FnMut(Px) -> Px) {
    for row in bytes.iter_mut() {
        for p in row.iter_mut() {
            *p = f(*p);
        }
    }
}

/// Percorre todos os LEDs com (fita, índice, posição 0..1 na fita, cor).
fn each(bytes: &mut Vec<Vec<Px>>, mut f: impl FnMut(usize, usize, f32, Px) -> Px) {
    for (d, row) in bytes.iter_mut().enumerate() {
        let n = row.len().max(2);
        for (i, p) in row.iter_mut().enumerate() {
            let pos = i as f32 / (n - 1) as f32;
            *p = f(d, i, pos, *p);
        }
    }
}

/// Entrada mínima / saída máxima: abaixo da mínima = 0, acima da máxima = 1.
fn rngf(v: f32, lo: f32, hi: f32) -> f32 {
    let lo = lo.clamp(0.0, 0.95);
    let hi = hi.clamp(lo + 0.05, 1.0);
    ((v - lo) / (hi - lo)).clamp(0.0, 1.0)
}

fn parse_hex(s: &str) -> Option<(f32, f32, f32)> {
    let h = s.trim().trim_start_matches('#');
    if h.len() != 6 {
        return None;
    }
    let v = u32::from_str_radix(h, 16).ok()?;
    Some((((v >> 16) & 255) as f32, ((v >> 8) & 255) as f32, (v & 255) as f32))
}

fn palette_colors(cfg: &Config) -> Vec<(f32, f32, f32)> {
    let mut v: Vec<(f32, f32, f32)> = cfg.palette.iter().filter_map(|s| parse_hex(s)).collect();
    if v.is_empty() {
        v = vec![
            (255.0, 0.0, 60.0),
            (255.0, 160.0, 0.0),
            (40.0, 220.0, 80.0),
            (0.0, 160.0, 255.0),
            (170.0, 60.0, 255.0),
            (255.0, 255.0, 255.0),
        ];
    }
    v
}

fn hash(a: u32, b: u32) -> u32 {
    let mut x = a.wrapping_mul(2654435761) ^ b.wrapping_mul(40503).wrapping_add(0x9E3779B9);
    x ^= x >> 13;
    x = x.wrapping_mul(0x85EBCA6B);
    x ^= x >> 16;
    x
}

/// Gira o matiz da cor (graus), mantendo o brilho.
fn hue_shift(p: Px, deg: f32) -> Px {
    let a = deg.to_radians();
    let (c, s) = (a.cos(), a.sin());
    let (r, g, b) = (p.0 as f32, p.1 as f32, p.2 as f32);
    let nr = r * (0.213 + c * 0.787 - s * 0.213) + g * (0.715 - c * 0.715 - s * 0.715) + b * (0.072 - c * 0.072 + s * 0.928);
    let ng = r * (0.213 - c * 0.213 + s * 0.143) + g * (0.715 + c * 0.285 + s * 0.140) + b * (0.072 - c * 0.072 - s * 0.283);
    let nb = r * (0.213 - c * 0.213 - s * 0.787) + g * (0.715 - c * 0.715 + s * 0.715) + b * (0.072 + c * 0.928 + s * 0.072);
    (nr.clamp(0.0, 255.0) as u8, ng.clamp(0.0, 255.0) as u8, nb.clamp(0.0, 255.0) as u8)
}

/// Termômetro: azul (baixo) -> ciano -> verde -> amarelo -> vermelho (alto).
fn heat(v: f32) -> (f32, f32, f32) {
    const S: [(f32, f32, f32); 5] = [
        (0.0, 80.0, 255.0),
        (0.0, 220.0, 255.0),
        (40.0, 230.0, 60.0),
        (255.0, 230.0, 0.0),
        (255.0, 40.0, 0.0),
    ];
    let x = v.clamp(0.0, 1.0) * 4.0;
    let i = (x as usize).min(3);
    let f = x - i as f32;
    let (a, b) = (S[i], S[i + 1]);
    (a.0 + (b.0 - a.0) * f, a.1 + (b.1 - a.1) * f, a.2 + (b.2 - a.2) * f)
}

impl Music {
    pub fn new() -> Self {
        Music {
            idx: 0,
            wave_t0: -10.0,
            armed: true,
            last_beat: -10.0,
            frame: 0,
            drive: 0.0,
            ref_rpm: 0.0,
            shift_t: -10.0,
            last_t: 0.0,
            phase: 0.0,
            chase: 0.0,
            burst_t0: -10.0,
            hb_t0: -10.0,
            echo: 0.0,
            flip: false,
        }
    }

    pub fn apply(&mut self, bytes: &mut Vec<Vec<Px>>, cfg: &Config, beat: &Beat, t: f32) {
        let sens = cfg.music_sens.clamp(0.3, 4.0);
        // cada faixa tem a sua entrada mínima e saída máxima
        let lb = if cfg.music_on_bass { rngf(beat.level() * sens, cfg.music_in_bass, cfg.music_out_bass) } else { 0.0 };
        let lt = if cfg.music_on_treble { rngf(beat.treble() * sens, cfg.music_in_treble, cfg.music_out_treble) } else { 0.0 };
        let vol = if cfg.music_on_vol { rngf(beat.volume() * sens, cfg.music_in_vol, cfg.music_out_vol) } else { 0.0 };
        let rpm = if cfg.music_on_rpm { rngf(beat.rpm(), cfg.music_in_rpm, cfg.music_out_rpm) } else { 0.0 };
        let lv = match cfg.music_band.as_str() {
            "treble" => lt,
            "both" => lb.max(lt),
            _ => lb,
        };
        let minv = (cfg.music_min / 100.0).clamp(0.0, 1.0);
        let depth = 1.0 - minv;
        let style = cfg.music_style.as_str();
        self.drive = match style {
            "vol" | "vu" | "breath" | "heat" | "chase" => vol,
            "rev" => rpm,
            "quad" => lb.max(lt).max(vol),
            _ => lv,
        };
        let dt = (t - self.last_t).clamp(0.0, 0.1);
        self.last_t = t;
        self.frame = self.frame.wrapping_add(1);

        // Trechos que NÃO reagem ao som voltam ao quadro original no final
        let orig = if cfg.segments().iter().any(|s| !s.music) { Some((*bytes).clone()) } else { None };

        // Batida forte detectada (borda de subida, com intervalo mínimo entre batidas)
        let mut hit = false;
        if lv > 0.6 && self.armed && t - self.last_beat > 0.15 {
            hit = true;
            self.armed = false;
            self.last_beat = t;
        }
        if lv < 0.3 {
            self.armed = true;
        }

        match style {
            "boost" => {
                let g = minv + depth * lv;
                all(bytes, |p| scale(p, g));
            }
            "flash" => {
                let m = lv * depth;
                all(bytes, |p| mix(p, (255.0, 255.0, 255.0), m));
            }
            "sat" => {
                let k = 1.0 + 2.0 * lv * depth;
                all(bytes, |p| {
                    let l = lum(p);
                    let f = |c: u8| (l + (c as f32 - l) * k).clamp(0.0, 255.0) as u8;
                    (f(p.0), f(p.1), f(p.2))
                });
            }
            "comp" => {
                let m = lv * depth;
                all(bytes, |p| mix(p, (255.0 - p.0 as f32, 255.0 - p.1 as f32, 255.0 - p.2 as f32), m));
            }
            "pal" => {
                if hit {
                    self.idx = self.idx.wrapping_add(1);
                }
                let pal = palette_colors(cfg);
                let c = pal[self.idx % pal.len()];
                let w = 0.2 + 0.8 * depth;
                all(bytes, |p| {
                    let l = lum(p) / 255.0;
                    mix(p, (c.0 * l, c.1 * l, c.2 * l), w)
                });
            }
            "split" => {
                let segs = cfg.segments();
                for (d, row) in bytes.iter_mut().enumerate() {
                    let mut off = 0usize;
                    for s in segs.iter().filter(|s| s.device == d) {
                        let l = if s.edge == "top" { lt } else { lb };
                        let g = 1.0 - l * depth;
                        let end = (off + s.leds).min(row.len());
                        for i in off..end {
                            row[i] = scale(row[i], g);
                        }
                        off += s.leds;
                    }
                }
            }
            "quad" => {
                let segs = cfg.segments();
                let both = lb.max(lt);
                for (d, row) in bytes.iter_mut().enumerate() {
                    let mut off = 0usize;
                    for s in segs.iter().filter(|s| s.device == d) {
                        let l = match s.edge.as_str() {
                            "left" => lb,
                            "right" => lt,
                            "top" => vol,
                            _ => both,
                        };
                        let g = 1.0 - l * depth;
                        let end = (off + s.leds).min(row.len());
                        for i in off..end {
                            row[i] = scale(row[i], g);
                        }
                        off += s.leds;
                    }
                }
            }
            "vol" => {
                let g = minv + depth * vol;
                all(bytes, |p| scale(p, g));
            }
            "wave" => {
                if hit {
                    self.wave_t0 = t;
                }
                let front = (t - self.wave_t0) * 1.5;
                each(bytes, |_, _, pos, p| {
                    let bump = (1.0 - (pos - front).abs() / 0.15).max(0.0);
                    if bump > 0.0 {
                        mix(p, (255.0, 255.0, 255.0), bump * depth)
                    } else {
                        p
                    }
                });
            }
            "vu" => {
                for row in bytes.iter_mut() {
                    let half = (row.len() as f32 / 2.0).max(1.0);
                    for (i, p) in row.iter_mut().enumerate() {
                        let d = ((i as f32 + 0.5) - half).abs() / half;
                        let k = ((vol - d) * 8.0 + 0.5).clamp(0.0, 1.0);
                        *p = scale(*p, minv + depth * k);
                    }
                }
            }
            "rev" => {
                // REV sound: brilho sobe com o giro do motor, avermelha perto do limite e
                // dá um clarão na troca de marcha (queda rápida do giro)
                let r = rpm;
                self.ref_rpm = r.max(self.ref_rpm - 1.5 * dt);
                if self.ref_rpm - r > 0.3 && t - self.shift_t > 0.4 {
                    self.shift_t = t;
                    self.ref_rpm = r;
                }
                let flash = (1.0 - (t - self.shift_t) / 0.25).clamp(0.0, 1.0) * 0.7 * depth;
                let red = ((r - 0.75) / 0.25).clamp(0.0, 1.0) * depth;
                let g = minv + depth * r;
                all(bytes, |p| {
                    let q = mix(scale(p, g), (255.0, 30.0, 0.0), red);
                    mix(q, (255.0, 255.0, 255.0), flash)
                });
            }
            "spark" => {
                let amt = lv * depth * 0.35;
                let fr = self.frame / 2;
                each(bytes, |d, i, _, p| {
                    let h = hash(i as u32 + (d as u32) * 1000, fr);
                    if ((h % 1000) as f32 / 1000.0) < amt {
                        mix(p, (255.0, 255.0, 255.0), 0.9)
                    } else {
                        p
                    }
                });
            }
            "hue" => {
                let deg = lv * depth * 140.0;
                all(bytes, |p| hue_shift(p, deg));
            }
            "breath" => {
                self.phase = (self.phase + dt * (0.4 + vol * 3.0)) % 1.0;
                let k = 0.5 + 0.5 * (self.phase * 6.283_185_3).sin();
                let g = minv + depth * k;
                all(bytes, |p| scale(p, g));
            }
            "chase" => {
                self.chase = (self.chase + dt * (0.25 + vol * 1.2 + lv * 1.5)) % 1.0;
                let c = self.chase;
                each(bytes, |_, _, pos, p| {
                    let mut d = (pos - c).abs();
                    if d > 0.5 {
                        d = 1.0 - d;
                    }
                    let b = (1.0 - d / 0.12).max(0.0);
                    mix(p, (255.0, 255.0, 255.0), b * depth)
                });
            }
            "center" => {
                if hit {
                    self.burst_t0 = t;
                }
                let front = (t - self.burst_t0) * 2.0;
                each(bytes, |_, _, pos, p| {
                    let dist = (pos - 0.5).abs() * 2.0;
                    let bump = (1.0 - (dist - front).abs() / 0.2).max(0.0);
                    mix(p, (255.0, 255.0, 255.0), bump * depth)
                });
            }
            "confetti" => {
                let pal = palette_colors(cfg);
                let amt = lv * depth * 0.4;
                let fr = self.frame / 3;
                each(bytes, |d, i, _, p| {
                    let h = hash(i as u32 + (d as u32) * 1000, fr);
                    if ((h % 1000) as f32 / 1000.0) < amt {
                        let c = pal[((h >> 10) as usize) % pal.len()];
                        mix(p, c, 0.9)
                    } else {
                        p
                    }
                });
            }
            "heat" => {
                let c = heat(vol);
                let w = 0.2 + 0.7 * depth;
                all(bytes, |p| {
                    let l = lum(p) / 255.0;
                    mix(p, (c.0 * l, c.1 * l, c.2 * l), w)
                });
            }
            "heartbeat" => {
                if hit {
                    self.hb_t0 = t;
                }
                let d1 = (t - self.hb_t0).max(0.0);
                let e1 = (-d1 * 14.0).exp();
                let d2 = t - self.hb_t0 - 0.22;
                let e2 = if d2 > 0.0 { 0.7 * (-d2 * 14.0).exp() } else { 0.0 };
                let g = 1.0 - e1.max(e2) * depth;
                all(bytes, |p| scale(p, g));
            }
            "echo" => {
                self.echo = lv.max(self.echo - dt * 0.7);
                let g = 1.0 - self.echo * depth;
                all(bytes, |p| scale(p, g));
            }
            "pingpong" => {
                if hit {
                    self.flip = !self.flip;
                }
                let flip = self.flip;
                each(bytes, |_, _, pos, p| {
                    let on = (pos < 0.5) == flip;
                    scale(p, if on { 1.0 } else { minv })
                });
            }
            _ => {
                // "dim": escurece na batida e volta ao normal
                let g = 1.0 - lv * depth;
                all(bytes, |p| scale(p, g));
            }
        }

        if let Some(orig) = orig {
            let segs = cfg.segments();
            for (d, row) in bytes.iter_mut().enumerate() {
                let mut off = 0usize;
                for s in segs.iter().filter(|s| s.device == d) {
                    if !s.music {
                        let end = (off + s.leds).min(row.len());
                        for i in off..end {
                            row[i] = orig[d][i];
                        }
                    }
                    off += s.leds;
                }
            }
        }
    }
}
