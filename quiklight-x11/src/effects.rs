//! Modos de cor estática, efeitos e zonas. Tudo usa curvas contínuas e suaves (nada de piscar).
use crate::config::Config;
use std::f32::consts::TAU;

fn hsv(h: f32, s: f32, v: f32) -> [f32; 3] {
    let h = h.rem_euclid(1.0) * 6.0;
    let i = h.floor();
    let f = h - i;
    let p = v * (1.0 - s);
    let q = v * (1.0 - s * f);
    let t = v * (1.0 - s * (1.0 - f));
    let (r, g, b) = match (i as i32) % 6 {
        0 => (v, t, p),
        1 => (q, v, p),
        2 => (p, v, t),
        3 => (p, q, v),
        4 => (t, p, v),
        _ => (v, p, q),
    };
    [r * 255.0, g * 255.0, b * 255.0]
}

fn scale(c: [f32; 3], f: f32) -> [f32; 3] {
    [c[0] * f, c[1] * f, c[2] * f]
}

fn lerp3(a: [f32; 3], b: [f32; 3], f: f32) -> [f32; 3] {
    [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f]
}

fn smoothstep(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

/// Pico suave e periódico (curva gaussiana) em torno de `center`.
fn bump(phase: f32, center: f32, width: f32) -> f32 {
    let mut d = (phase - center).abs();
    if d > 0.5 {
        d = 1.0 - d;
    }
    (-(d / width).powi(2)).exp()
}

fn parse_hex(s: &str) -> Option<[f32; 3]> {
    let s = s.trim().trim_start_matches('#');
    if s.len() != 6 {
        return None;
    }
    let v = u32::from_str_radix(s, 16).ok()?;
    Some([((v >> 16) & 255) as f32, ((v >> 8) & 255) as f32, (v & 255) as f32])
}

fn hash01(seed: u32) -> f32 {
    let mut x = seed.wrapping_mul(0x9E37_79B1) ^ 0x85EB_CA6B;
    x ^= x >> 15;
    x = x.wrapping_mul(0x2C1B_3C6D);
    x ^= x >> 12;
    x = x.wrapping_mul(0x297A_2D39);
    x ^= x >> 15;
    x as f32 / u32::MAX as f32
}

/// Cor aleatória de um slot vazio. Muda devagar (a cada ~40 s), com transição suave.
fn random_color(slot: usize, t: f32) -> [f32; 3] {
    const EPOCH: f32 = 40.0;
    let e = (t / EPOCH).floor();
    let f = smoothstep((t / EPOCH - e - 0.75) / 0.25);
    let pick = |ep: f32| -> [f32; 3] {
        let s = (slot as u32)
            .wrapping_mul(7919)
            .wrapping_add((ep as i64 as u32).wrapping_mul(104_729));
        hsv(hash01(s), 0.7 + 0.3 * hash01(s ^ 0xABCD), 1.0)
    };
    lerp3(pick(e), pick(e + 1.0), f)
}

fn base_color(cfg: &Config) -> [f32; 3] {
    [cfg.static_r as f32, cfg.static_g as f32, cfg.static_b as f32]
}

/// Paleta efetiva: slots preenchidos + (opcionalmente) aleatórios nos vazios.
fn palette(cfg: &Config, t: f32) -> Vec<[f32; 3]> {
    let mut v = Vec::new();
    for i in 0..10 {
        match cfg.palette.get(i).and_then(|s| parse_hex(s)) {
            Some(c) => v.push(c),
            None => {
                if cfg.palette_random {
                    v.push(random_color(i, t));
                }
            }
        }
    }
    if v.is_empty() {
        v.push(base_color(cfg));
    }
    v
}

/// Cor na posição `pos` da paleta (cíclica). Com `ease`, a transição é suavizada.
fn pal_at(p: &[[f32; 3]], pos: f32, ease: bool) -> [f32; 3] {
    let n = p.len();
    if n == 1 {
        return p[0];
    }
    let x = pos.rem_euclid(n as f32);
    let i = (x.floor() as usize) % n;
    let mut f = x - x.floor();
    if ease {
        f = smoothstep(f);
    }
    lerp3(p[i], p[(i + 1) % n], f)
}

/// Mesma cor em todos os LEDs.
pub fn static_frame(counts: &[usize], cfg: &Config) -> Vec<Vec<[f32; 3]>> {
    let c = base_color(cfg);
    counts.iter().map(|&n| vec![c; n]).collect()
}

/// Efeitos animados. `t` = segundos desde o início.
pub fn effect_frame(counts: &[usize], cfg: &Config, t: f32) -> Vec<Vec<[f32; 3]>> {
    let speed = cfg.effect_speed.clamp(1.0, 10.0);
    let minb = (cfg.effect_min / 100.0).clamp(0.0, 0.95);
    // Período mínimo de 2 s na respiração e no pulso: nunca pisca rápido
    let period = (14.0 / speed).max(2.0);
    let cycle = (t / period).floor();
    let phase = (t / period).fract();
    let pal = palette(cfg, t);
    let n_pal = pal.len() as f32;
    // Cor da respiração/pulso: troca de cor suavemente no fim de cada ciclo
    let cycle_pos = cycle + smoothstep((phase - 0.8) / 0.2);
    let cycle_color = pal_at(&pal, cycle_pos, false);
    let effect = cfg.effect.as_str();

    counts
        .iter()
        .map(|&n| {
            (0..n)
                .map(|i| {
                    let p = if n > 1 { i as f32 / (n - 1) as f32 } else { 0.0 };
                    match effect {
                        "pulsing" => {
                            let v = bump(phase, 0.25, 0.12).max(0.6 * bump(phase, 0.5, 0.12));
                            scale(cycle_color, minb + (1.0 - minb) * v)
                        }
                        "rainbow" => hsv(p - t * 0.02 * speed, 1.0, 1.0),
                        "fade" => pal_at(&pal, t * 0.02 * speed, true),
                        "comet" => {
                            let pos = t * 0.05 * speed;
                            let pass = pos.floor();
                            let head = pos.fract();
                            let mut s = p - head;
                            if s > 0.5 {
                                s -= 1.0;
                            } else if s < -0.5 {
                                s += 1.0;
                            }
                            let idx = if s > 0.0 || p <= head { pass } else { pass - 1.0 };
                            let color = pal[(idx as i64).rem_euclid(pal.len() as i64) as usize];
                            let v = if s > 0.0 {
                                (-(s / 0.03).powi(2)).exp()
                            } else {
                                (s / 0.12).exp()
                            };
                            scale(color, 0.04 + 0.96 * v)
                        }
                        "aurora" => {
                            let pos = p * (n_pal * 0.5).max(1.5) + t * 0.03 * speed;
                            let b = (TAU * (p * 1.1 - t * 0.04 * speed)).sin() * 0.5 + 0.5;
                            scale(pal_at(&pal, pos, true), 0.3 + 0.7 * b * b)
                        }
                        "fire" => {
                            let r = 0.3 + 0.07 * speed;
                            let f = 0.55
                                + 0.22 * (TAU * (0.45 * r * t + p * 3.0)).sin()
                                + 0.15 * (TAU * (0.8 * r * t + p * 5.7)).sin()
                                + 0.08 * (TAU * (0.2 * r * t + p * 11.0)).sin();
                            let v = f.clamp(0.25, 1.0);
                            hsv(0.02 + 0.05 * v, 1.0, v)
                        }
                        _ => {
                            // breathing
                            let x = 0.5 - 0.5 * (TAU * phase).cos();
                            scale(cycle_color, minb + (1.0 - minb) * smoothstep(x))
                        }
                    }
                })
                .collect()
        })
        .collect()
}

/// Distribui as cores das zonas pelos LEDs.
/// "dominant_lr": 2 zonas (esquerda/direita; topo e baixo são divididos ao meio).
/// "dominant_4": 4 zonas (esquerda, direita, topo, baixo), cada lado com a sua cor.
pub fn zones_frame(counts: &[usize], cfg: &Config, zones: &[[f32; 3]]) -> Vec<Vec<[f32; 3]>> {
    let mut out: Vec<Vec<[f32; 3]>> = counts.iter().map(|&n| Vec::with_capacity(n)).collect();
    let four = cfg.mode.to_lowercase() == "dominant_4";
    for s in cfg.segments() {
        let n = s.leds;
        for i in 0..n {
            let j = if s.reverse { n - 1 - i } else { i };
            let frac = j as f32 / n as f32;
            let z = if four {
                match s.edge.as_str() {
                    "left" => 0,
                    "right" => 1,
                    "top" => 2,
                    _ => 3,
                }
            } else {
                match s.edge.as_str() {
                    "left" => 0,
                    "right" => 1,
                    _ => {
                        if frac < 0.5 {
                            0
                        } else {
                            1
                        }
                    }
                }
            };
            out[s.device].push(zones[z.min(zones.len() - 1)]);
        }
    }
    out
}

fn hsv_of(c: [f32; 3]) -> (f32, f32, f32) {
    let (r, g, b) = (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0);
    let mx = r.max(g).max(b);
    let mn = r.min(g).min(b);
    let d = mx - mn;
    let s = if mx > 0.0 { d / mx } else { 0.0 };
    let h = if d < 1e-4 {
        0.0
    } else if mx == r {
        ((g - b) / d).rem_euclid(6.0) / 6.0
    } else if mx == g {
        ((b - r) / d + 2.0) / 6.0
    } else {
        ((r - g) / d + 4.0) / 6.0
    };
    (h, s, mx)
}

/// Cores selecionadas: cada LED mostra a cor selecionada mais próxima (em matiz) da cor da tela,
/// com o brilho seguindo a tela. Com uma só cor selecionada, tudo aparece nela.
pub fn solid_frame(cfg: &Config, leds: &[Vec<[f32; 3]>]) -> Vec<Vec<[f32; 3]>> {
    let mut pal: Vec<[f32; 3]> = (0..10)
        .filter_map(|i| cfg.palette.get(i).and_then(|s| parse_hex(s)))
        .collect();
    if pal.is_empty() {
        pal.push(base_color(cfg));
    }
    let info: Vec<(f32, [f32; 3])> = pal
        .iter()
        .map(|c| {
            let (h, _, _) = hsv_of(*c);
            let m = c[0].max(c[1]).max(c[2]).max(1.0);
            (h, [c[0] * 255.0 / m, c[1] * 255.0 / m, c[2] * 255.0 / m])
        })
        .collect();
    leds.iter()
        .map(|row| {
            row.iter()
                .map(|p| {
                    let (h, s, v) = hsv_of(*p);
                    let mut best = 0usize;
                    if s >= 0.12 {
                        let mut bd = f32::MAX;
                        for (i, (ph, _)) in info.iter().enumerate() {
                            let mut d = (h - ph).abs();
                            if d > 0.5 {
                                d = 1.0 - d;
                            }
                            if d < bd {
                                bd = d;
                                best = i;
                            }
                        }
                    }
                    scale(info[best].1, v)
                })
                .collect()
        })
        .collect()
}

/// Suavização exponencial entre quadros. `a` = peso do quadro anterior (0 = sem suavização).
pub fn smooth_f(prev: &mut Vec<Vec<[f32; 3]>>, cur: Vec<Vec<[f32; 3]>>, a: f32) -> Vec<Vec<[f32; 3]>> {
    for (d, row) in cur.iter().enumerate() {
        while prev.len() <= d {
            prev.push(Vec::new());
        }
        while prev[d].len() < row.len() {
            prev[d].push([0.0; 3]);
        }
        for (i, p) in row.iter().enumerate() {
            for c in 0..3 {
                prev[d][i][c] = a * prev[d][i][c] + (1.0 - a) * p[c];
            }
        }
    }
    prev.clone()
}
