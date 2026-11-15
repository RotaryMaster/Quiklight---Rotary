//! Etapa final: brilho por software, limite de potência, limite de variação (evita clarões)
//! e dithering temporal (fades suaves em brilho baixo).

pub struct Stage {
    cur: Vec<Vec<[f32; 3]>>,
    err: Vec<Vec<[f32; 3]>>,
    slew: f32,
}

impl Stage {
    pub fn new(counts: &[usize], slew: f32) -> Self {
        Self {
            cur: counts.iter().map(|&n| vec![[0.0f32; 3]; n]).collect(),
            err: counts.iter().map(|&n| vec![[0.0f32; 3]; n]).collect(),
            slew,
        }
    }

    pub fn set_slew(&mut self, slew: f32) {
        self.slew = slew;
    }

    /// `target` em 0..255 (float). `level` = brilho em % (acima de 100 realça sem mudar o tom).
    /// `power_limit` = % máximo do brilho médio da fita (100 = sem limite).
    pub fn step(&mut self, target: &[Vec<[f32; 3]>], dt: f32, level: f32, power_limit: f32) -> Vec<Vec<(u8, u8, u8)>> {
        let lv = (level / 100.0).max(0.0);
        let mut scaled: Vec<Vec<[f32; 3]>> = target
            .iter()
            .map(|row| {
                row.iter()
                    .map(|p| {
                        let m = p[0].max(p[1]).max(p[2]);
                        let s = if m * lv > 255.0 { 255.0 / m.max(0.001) } else { lv };
                        [p[0] * s, p[1] * s, p[2] * s]
                    })
                    .collect()
            })
            .collect();
        if power_limit > 0.0 && power_limit < 100.0 {
            let lim = power_limit / 100.0;
            for row in scaled.iter_mut() {
                let n = row.len().max(1) as f32;
                let sum: f32 = row.iter().map(|p| p[0] + p[1] + p[2]).sum();
                let avg = sum / (3.0 * 255.0 * n);
                if avg > lim {
                    let k = lim / avg;
                    for p in row.iter_mut() {
                        for c in 0..3 {
                            p[c] *= k;
                        }
                    }
                }
            }
        }

        let max_delta = if self.slew > 0.0 { self.slew * 255.0 * dt } else { f32::MAX };
        let mut out = Vec::with_capacity(self.cur.len());
        for d in 0..self.cur.len() {
            let mut row = Vec::with_capacity(self.cur[d].len());
            for i in 0..self.cur[d].len() {
                let mut px = [0u8; 3];
                for c in 0..3 {
                    let tgt = scaled.get(d).and_then(|v| v.get(i)).map(|p| p[c]).unwrap_or(0.0);
                    let cur = &mut self.cur[d][i][c];
                    let diff = tgt - *cur;
                    *cur += diff.clamp(-max_delta, max_delta);
                    let v = *cur + self.err[d][i][c];
                    let q = v.round().clamp(0.0, 255.0);
                    self.err[d][i][c] = (v - q).clamp(-0.5, 0.5);
                    px[c] = q as u8;
                }
                row.push((px[0], px[1], px[2]));
            }
            out.push(row);
        }
        out
    }
}
