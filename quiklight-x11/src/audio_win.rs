//! Modo música no Windows: captura o som que sai do PC (loopback do WASAPI, via cpal)
//! e mede graves (batida), agudos, volume e giro do motor. Mesma interface do audio.rs do Linux.
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;
use std::time::Duration;

type Levels = Arc<[AtomicU32; 4]>; // [graves, agudos, volume, rpm], cada um 0..1 (bits de f32)

pub struct Beat {
    lv: Levels,
    run: Arc<AtomicBool>,
    gen: Arc<AtomicU32>,
}

impl Beat {
    pub fn new() -> Self {
        Beat {
            lv: Arc::new([AtomicU32::new(0), AtomicU32::new(0), AtomicU32::new(0), AtomicU32::new(0)]),
            run: Arc::new(AtomicBool::new(false)),
            gen: Arc::new(AtomicU32::new(0)),
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
            std::thread::spawn(move || worker(lv, run, gen, mine));
        } else {
            zero(&self.lv);
        }
    }

    fn get(&self, i: usize) -> f32 {
        f32::from_bits(self.lv[i].load(Ordering::Relaxed))
    }
    pub fn level(&self) -> f32 {
        self.get(0)
    }
    pub fn treble(&self) -> f32 {
        self.get(1)
    }
    pub fn volume(&self) -> f32 {
        self.get(2)
    }
    pub fn rpm(&self) -> f32 {
        self.get(3)
    }
}

fn zero(lv: &Levels) {
    for a in lv.iter() {
        a.store(0f32.to_bits(), Ordering::Relaxed);
    }
}

fn worker(lv: Levels, run: Arc<AtomicBool>, gen: Arc<AtomicU32>, mine: u32) {
    let alive = || run.load(Ordering::SeqCst) && gen.load(Ordering::SeqCst) == mine;
    let mut warned = false;
    while alive() {
        let failed = Arc::new(AtomicBool::new(false));
        match open_stream(&lv, failed.clone()) {
            Ok(stream) => {
                warned = false;
                while alive() && !failed.load(Ordering::SeqCst) {
                    std::thread::sleep(Duration::from_millis(100));
                }
                drop(stream);
            }
            Err(e) => {
                if !warned {
                    eprintln!("Modo música: não consegui abrir a captura de áudio do Windows: {}", e);
                    warned = true;
                }
                std::thread::sleep(Duration::from_secs(3));
            }
        }
        zero(&lv);
        if alive() {
            std::thread::sleep(Duration::from_secs(1));
        }
    }
}

fn open_stream(lv: &Levels, failed: Arc<AtomicBool>) -> Result<cpal::Stream, String> {
    let host = cpal::default_host();
    let dev = host.default_output_device().ok_or_else(|| "sem dispositivo de saída de áudio".to_string())?;
    // Pedir entrada em um dispositivo de SAÍDA ativa o loopback do WASAPI (o que está tocando)
    let supported = dev.default_output_config().map_err(|e| e.to_string())?;
    let channels = (supported.channels() as usize).max(1);
    let rate = supported.sample_rate().0 as f32;
    let fmt = supported.sample_format();
    let cfg: cpal::StreamConfig = supported.into();
    let err_cb = move |_e: cpal::StreamError| {
        failed.store(true, Ordering::SeqCst);
    };
    let mut an = Analyzer::new(rate, lv.clone());
    let stream = match fmt {
        cpal::SampleFormat::F32 => dev.build_input_stream(
            &cfg,
            move |data: &[f32], _: &cpal::InputCallbackInfo| {
                for fr in data.chunks(channels) {
                    let m: f32 = fr.iter().sum::<f32>() / channels as f32;
                    an.feed(m);
                }
            },
            err_cb,
            None,
        ),
        cpal::SampleFormat::I16 => dev.build_input_stream(
            &cfg,
            move |data: &[i16], _: &cpal::InputCallbackInfo| {
                for fr in data.chunks(channels) {
                    let m: f32 = fr.iter().map(|&s| s as f32 / 32768.0).sum::<f32>() / channels as f32;
                    an.feed(m);
                }
            },
            err_cb,
            None,
        ),
        _ => return Err("formato de áudio não suportado".to_string()),
    }
    .map_err(|e| e.to_string())?;
    stream.play().map_err(|e| e.to_string())?;
    Ok(stream)
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
        self.avg += (e - self.avg) * 0.04;
        self.peak = e.max(self.peak * 0.998).max(0.004);
        let base = self.avg * 1.1;
        let den = (self.peak - base).max(1e-4);
        let x = ((e - base) / den).clamp(0.0, 1.0);
        self.env = x.max(self.env * 0.82);
        self.env
    }
}

/// Analisa o áudio (mono, qualquer taxa) em blocos de ~16 ms.
struct Analyzer {
    rate: f32,
    chunk: usize,
    n: usize,
    a_lo: f32,
    a_hi: f32,
    a_eng: f32,
    a_dc: f32,
    lp_lo: f32,
    lp_hi: f32,
    e1: f32,
    e2: f32,
    dc: f32,
    amp: f32,
    above: bool,
    since: u32,
    fest: f32,
    fmin: f32,
    fmax: f32,
    rpm: f32,
    bass: Det,
    treb: Det,
    vpeak: f32,
    vol: f32,
    sb: f32,
    st: f32,
    sv: f32,
    lv: Levels,
}

impl Analyzer {
    fn new(rate: f32, lv: Levels) -> Self {
        let pi2 = 2.0 * std::f32::consts::PI;
        Analyzer {
            rate,
            chunk: ((rate * 0.016) as usize).max(64),
            n: 0,
            a_lo: 1.0 - (-pi2 * 150.0 / rate).exp(),
            a_hi: 1.0 - (-pi2 * 2000.0 / rate).exp(),
            a_eng: 1.0 - (-pi2 * 350.0 / rate).exp(),
            a_dc: 1.0 - (-pi2 * 30.0 / rate).exp(),
            lp_lo: 0.0,
            lp_hi: 0.0,
            e1: 0.0,
            e2: 0.0,
            dc: 0.0,
            amp: 0.0,
            above: false,
            since: 0,
            fest: 60.0,
            fmin: 60.0,
            fmax: 300.0,
            rpm: 0.0,
            bass: Det::new(),
            treb: Det::new(),
            vpeak: 0.01,
            vol: 0.0,
            sb: 0.0,
            st: 0.0,
            sv: 0.0,
            lv,
        }
    }

    fn feed(&mut self, x: f32) {
        self.lp_lo += self.a_lo * (x - self.lp_lo);
        self.lp_hi += self.a_hi * (x - self.lp_hi);
        let hp = x - self.lp_hi;
        self.sb += self.lp_lo * self.lp_lo;
        self.st += hp * hp;
        self.sv += x * x;
        // Tom do motor: intervalo entre cruzamentos por zero do sinal grave
        self.e1 += self.a_eng * (x - self.e1);
        self.e2 += self.a_eng * (self.e1 - self.e2);
        self.dc += self.a_dc * (self.e2 - self.dc);
        let y = self.e2 - self.dc;
        self.amp = y.abs().max(self.amp * 0.9995);
        let th = (self.amp * 0.2).max(1e-4);
        self.since += 1;
        if !self.above && y > th {
            self.above = true;
            let lo = (self.rate / 400.0) as u32;
            let hi = (self.rate / 40.0) as u32;
            if self.since >= lo && self.since <= hi {
                let f = self.rate / self.since as f32;
                self.fest += (f - self.fest) * 0.2;
            }
            self.since = 0;
        } else if self.above && y < -th {
            self.above = false;
        }
        self.n += 1;
        if self.n >= self.chunk {
            self.finish();
        }
    }

    fn finish(&mut self) {
        let n = self.chunk as f32;
        let b = self.bass.step((self.sb / n).sqrt());
        let t = self.treb.step((self.st / n).sqrt());
        let v = (self.sv / n).sqrt();
        self.vpeak = v.max(self.vpeak * 0.9995).max(0.01);
        self.vol += ((v / self.vpeak).clamp(0.0, 1.0) - self.vol) * 0.25;
        if self.fest < self.fmin {
            self.fmin = self.fest;
        } else {
            self.fmin += (self.fest - self.fmin) * 0.0003;
        }
        if self.fest > self.fmax {
            self.fmax = self.fest;
        } else {
            self.fmax -= (self.fmax - self.fest) * 0.0003;
        }
        let span = (self.fmax - self.fmin).max(30.0);
        let target = if self.vol > 0.15 { ((self.fest - self.fmin) / span).clamp(0.0, 1.0) } else { 0.0 };
        self.rpm += (target - self.rpm) * 0.3;
        self.lv[0].store(b.to_bits(), Ordering::Relaxed);
        self.lv[1].store(t.to_bits(), Ordering::Relaxed);
        self.lv[2].store(self.vol.to_bits(), Ordering::Relaxed);
        self.lv[3].store(self.rpm.to_bits(), Ordering::Relaxed);
        self.n = 0;
        self.sb = 0.0;
        self.st = 0.0;
        self.sv = 0.0;
    }
}
