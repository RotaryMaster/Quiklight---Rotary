//! Modo música: captura o áudio que sai do PC (monitor da saída padrão) e
//! mede graves (batida), agudos e volume. Usa `parec` (PulseAudio/PipeWire) ou `pw-record`.
use std::io::Read;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicI32, AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Duration;

const RATE: f32 = 16000.0;
const CHUNK: usize = 256; // ~16 ms por bloco

type Levels = Arc<[AtomicU32; 4]>; // [graves, agudos, volume, rpm], cada um 0..1 (bits de f32)

pub struct Beat {
    lv: Levels,
    run: Arc<AtomicBool>,
    gen: Arc<AtomicU32>,
    pid: Arc<AtomicI32>,
}

impl Beat {
    pub fn new() -> Self {
        Beat {
            lv: Arc::new([AtomicU32::new(0), AtomicU32::new(0), AtomicU32::new(0), AtomicU32::new(0)]),
            run: Arc::new(AtomicBool::new(false)),
            gen: Arc::new(AtomicU32::new(0)),
            pid: Arc::new(AtomicI32::new(0)),
        }
    }

    /// Liga/desliga a captura de áudio (só faz algo quando o estado muda).
    pub fn set_enabled(&self, on: bool) {
        let was = self.run.swap(on, Ordering::SeqCst);
        if on == was {
            return;
        }
        let mine = self.gen.fetch_add(1, Ordering::SeqCst) + 1;
        if on {
            let lv = self.lv.clone();
            let run = self.run.clone();
            let gen = self.gen.clone();
            let pid = self.pid.clone();
            std::thread::spawn(move || worker(lv, run, gen, pid, mine));
        } else {
            let p = self.pid.swap(0, Ordering::SeqCst);
            if p > 0 {
                unsafe {
                    libc::kill(p, libc::SIGTERM);
                }
            }
            zero(&self.lv);
        }
    }

    fn get(&self, i: usize) -> f32 {
        f32::from_bits(self.lv[i].load(Ordering::Relaxed))
    }
    /// Força da batida nos graves (0..1).
    pub fn level(&self) -> f32 {
        self.get(0)
    }
    /// Força da batida nos agudos (0..1).
    pub fn treble(&self) -> f32 {
        self.get(1)
    }
    /// Volume relativo da música (0..1).
    pub fn volume(&self) -> f32 {
        self.get(2)
    }
    /// Giro do motor estimado pelo tom grave do som (0..1).
    pub fn rpm(&self) -> f32 {
        self.get(3)
    }
}

fn zero(lv: &Levels) {
    for a in lv.iter() {
        a.store(0f32.to_bits(), Ordering::Relaxed);
    }
}

fn spawn_rec(kind: usize) -> Option<Child> {
    let mut c = if kind == 0 {
        let mut c = Command::new("parec");
        c.args(&["-d", "@DEFAULT_MONITOR@", "--format=s16le", "--rate=16000", "--channels=1", "--latency-msec=20"]);
        c
    } else {
        let mut c = Command::new("pw-record");
        c.args(&["-P", "{ stream.capture.sink=true }", "--format", "s16", "--rate", "16000", "--channels", "1", "-"]);
        c
    };
    c.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::null());
    c.spawn().ok()
}

fn worker(lv: Levels, run: Arc<AtomicBool>, gen: Arc<AtomicU32>, pid: Arc<AtomicI32>, mine: u32) {
    let alive = || run.load(Ordering::SeqCst) && gen.load(Ordering::SeqCst) == mine;
    let mut kind = 0usize;
    let mut warned = false;
    while alive() {
        let mut child = match spawn_rec(kind) {
            Some(c) => c,
            None => {
                if !warned {
                    eprintln!("Modo música: não consegui iniciar a captura de áudio (parec/pw-record).");
                    warned = true;
                }
                kind = 1 - kind;
                std::thread::sleep(Duration::from_secs(3));
                continue;
            }
        };
        pid.store(child.id() as i32, Ordering::SeqCst);
        let mut got = 0usize;
        if let Some(mut out) = child.stdout.take() {
            got = analyze(&mut out, &lv, &alive);
        }
        let _ = child.kill();
        let _ = child.wait();
        zero(&lv);
        if got == 0 {
            kind = 1 - kind; // este gravador não funcionou: tenta o outro
        }
        if alive() {
            std::thread::sleep(Duration::from_secs(2));
        }
    }
}

/// Detector de batida: compara a energia do bloco com a média recente.
struct Det {
    avg: f32,
    peak: f32,
    env: f32,
}

impl Det {
    fn new() -> Self {
        Det { avg: 0.0, peak: 0.01, env: 0.0 }
    }
    fn step(&mut self, e: f32) -> f32 {
        self.avg += (e - self.avg) * 0.04; // média lenta (~0,4 s)
        self.peak = e.max(self.peak * 0.998).max(0.004); // pico com queda lenta
        let base = self.avg * 1.1;
        let den = (self.peak - base).max(1e-4);
        let x = ((e - base) / den).clamp(0.0, 1.0);
        self.env = x.max(self.env * 0.82); // sobe na hora, desce rápido
        self.env
    }
}

/// Lê o áudio e atualiza os níveis a cada bloco. Retorna quantos bytes leu.
fn analyze(out: &mut dyn Read, lv: &Levels, alive: &dyn Fn() -> bool) -> usize {
    let mut buf = [0u8; CHUNK * 2];
    let a_lo = 1.0 - (-2.0 * std::f32::consts::PI * 150.0 / RATE).exp(); // graves ~150 Hz
    let a_hi = 1.0 - (-2.0 * std::f32::consts::PI * 2000.0 / RATE).exp(); // separa agudos ~2 kHz
    let a_eng = 1.0 - (-2.0 * std::f32::consts::PI * 350.0 / RATE).exp(); // motor: até ~350 Hz
    let a_dc = 1.0 - (-2.0 * std::f32::consts::PI * 30.0 / RATE).exp(); // tira o nível médio
    let (mut lp_lo, mut lp_hi) = (0.0f32, 0.0f32);
    let (mut e1, mut e2, mut dc) = (0.0f32, 0.0f32, 0.0f32);
    let (mut amp, mut above, mut since) = (0.0f32, false, 0u32);
    let (mut fest, mut fmin, mut fmax, mut rpm) = (60.0f32, 60.0f32, 300.0f32, 0.0f32);
    let mut bass = Det::new();
    let mut treb = Det::new();
    let (mut vpeak, mut vol) = (0.01f32, 0.0f32);
    let mut total = 0usize;
    while alive() {
        if out.read_exact(&mut buf).is_err() {
            break;
        }
        total += buf.len();
        let (mut sb, mut st, mut sv) = (0.0f32, 0.0f32, 0.0f32);
        for i in 0..CHUNK {
            let x = i16::from_le_bytes([buf[2 * i], buf[2 * i + 1]]) as f32 / 32768.0;
            lp_lo += a_lo * (x - lp_lo);
            lp_hi += a_hi * (x - lp_hi);
            let hp = x - lp_hi;
            sb += lp_lo * lp_lo;
            st += hp * hp;
            sv += x * x;
            // Tom do motor: intervalo entre cruzamentos por zero do sinal grave
            e1 += a_eng * (x - e1);
            e2 += a_eng * (e1 - e2);
            dc += a_dc * (e2 - dc);
            let y = e2 - dc;
            amp = y.abs().max(amp * 0.9995);
            let th = (amp * 0.2).max(1e-4);
            since += 1;
            if !above && y > th {
                above = true;
                if since >= 40 && since <= 400 {
                    let f = RATE / since as f32;
                    fest += (f - fest) * 0.2;
                }
                since = 0;
            } else if above && y < -th {
                above = false;
            }
        }
        let n = CHUNK as f32;
        let b = bass.step((sb / n).sqrt());
        let t = treb.step((st / n).sqrt());
        let v = (sv / n).sqrt();
        vpeak = v.max(vpeak * 0.9995).max(0.01);
        vol += ((v / vpeak).clamp(0.0, 1.0) - vol) * 0.25;
        // RPM: posição do tom atual entre o mais grave e o mais agudo vistos recentemente
        if fest < fmin { fmin = fest; } else { fmin += (fest - fmin) * 0.0003; }
        if fest > fmax { fmax = fest; } else { fmax -= (fmax - fest) * 0.0003; }
        let span = (fmax - fmin).max(30.0);
        let target = if vol > 0.15 { ((fest - fmin) / span).clamp(0.0, 1.0) } else { 0.0 };
        rpm += (target - rpm) * 0.3;
        lv[0].store(b.to_bits(), Ordering::Relaxed);
        lv[1].store(t.to_bits(), Ordering::Relaxed);
        lv[2].store(vol.to_bits(), Ordering::Relaxed);
        lv[3].store(rpm.to_bits(), Ordering::Relaxed);
    }
    total
}
