use serde::Deserialize;
use std::path::Path;

/// Um trecho de fita: em qual fita (device), em qual lado da tela, quantos LEDs
/// e se a ordem dos LEDs é invertida em relação ao padrão.
///
/// Ordem padrão de cada lado: esquerda e direita de cima para baixo;
/// topo e embaixo da esquerda para a direita.
#[derive(Debug, Deserialize, Clone)]
pub struct Segment {
    #[serde(default)]
    pub device: usize,
    #[serde(default = "default_edge")]
    pub edge: String, // "left" | "top" | "right" | "bottom"
    #[serde(default)]
    pub leds: usize,
    #[serde(default)]
    pub reverse: bool,
    /// Este trecho reage ao Modo música?
    #[serde(default = "default_true")]
    pub music: bool,
}

fn default_true() -> bool {
    true
}

fn default_edge() -> String {
    "top".to_string()
}

#[derive(Debug, Deserialize, Clone)]
#[serde(default)]
pub struct Config {
    // Layout antigo (usado só se não houver [[segment]])
    pub top: usize,
    pub right: usize,
    pub left: usize,
    pub bottom: usize,
    // Screen capture
    pub cap_w: usize,
    pub cap_h: usize,
    pub border: usize,
    // Margens da área de captura, em % da tela
    pub inset_left: f32,
    pub inset_top: f32,
    pub inset_right: f32,
    pub inset_bottom: f32,
    // Performance
    pub fps: u32,
    // Color processing
    pub brightness: u8,
    pub smoothing: f32,
    pub saturation: f32,
    pub gamma: f32,
    pub contrast: f32,
    pub gain_r: f32,
    pub gain_g: f32,
    pub gain_b: f32,
    /// "average" (média simples) ou "vivid" (dá mais peso aos pixels coloridos)
    pub color_mode: String,
    /// Pede ao KDE/gamescope no máximo `fps` quadros por segundo (economiza GPU)
    pub capture_limit: bool,
    /// "screen" | "dominant" | "static" | "effect"
    pub mode: String,
    pub static_r: u8,
    pub static_g: u8,
    pub static_b: u8,
    /// breathing | pulsing | rainbow | fade | comet | aurora | fire
    pub effect: String,
    pub effect_speed: f32,
    /// Brilho mínimo (%) da respiração e do pulso
    pub effect_min: f32,
    /// 0..1: quanto a cor dominante respeita o brilho da cena
    pub dom_scene: f32,
    /// Suavidade da troca de cor no modo dominante (0..0.99)
    pub dom_smooth: f32,
    /// Variação máxima por segundo, em fração da escala completa (0 = sem limite)
    pub slew: f32,
    /// Até 10 cores em "#rrggbb"; vazio = slot aleatório
    pub palette: Vec<String>,
    pub palette_random: bool,
    /// 0..1: preferência por cores vibrantes no modo dominante (0 = só a área conta)
    pub dom_vibrance: f32,
    /// 0..1: fidelidade da cor dominante à cena (1 = cor real, 0 = cor cheia)
    pub dom_fidelity: f32,
    /// Profundidade (%) das áreas no modo dominante de 4 áreas
    pub zone_depth: f32,
    pub gamma_r: f32,
    pub gamma_g: f32,
    pub gamma_b: f32,
    /// Brilho por software em % (100 = normal; acima de 100 realça sem estourar o tom)
    pub level: f32,
    /// Limite de potência em % (100 = sem limite)
    pub power_limit: f32,
    /// "Melhor acurácia de cores": balanço de branco, gamma por canal e proteção de neutros
    pub accuracy: bool,
    /// Suavização entre cores, em segundos (modos Cores das bordas e Cores selecionadas)
    pub fade_time: f32,
    /// Detecta barras pretas (letterbox/pillarbox) e recorta a área de captura
    pub auto_crop: bool,
    /// Velocidade da detecção de barras pretas (1 = lenta, 10 = rápida)
    pub crop_speed: f32,
    /// Modo música: a luz escurece na batida do som do PC e volta ao normal
    pub music: bool,
    /// Dimming mínimo (%) atingido na batida mais forte
    pub music_min: f32,
    /// "dim" (escurece na batida) | "boost" (acende na batida)
    pub music_style: String,
    /// Sensibilidade à batida (0.3 .. 4)
    pub music_sens: f32,
    /// Faixa que move a luz: "bass" | "treble" | "both"
    pub music_band: String,
    /// Entrada mínima / saída máxima (0..1) de cada faixa do som
    pub music_in_bass: f32,
    pub music_out_bass: f32,
    pub music_in_treble: f32,
    pub music_out_treble: f32,
    pub music_in_vol: f32,
    pub music_out_vol: f32,
    pub music_in_rpm: f32,
    pub music_out_rpm: f32,
    /// Liga/desliga cada faixa do som
    pub music_on_bass: bool,
    pub music_on_treble: bool,
    pub music_on_vol: bool,
    pub music_on_rpm: bool,
    // Screen selection — não usado no Wayland (mantido por compatibilidade)
    pub monitor: Option<String>,
    // Trechos de fita
    pub segment: Vec<Segment>,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            top: 29,
            right: 17,
            left: 17,
            bottom: 0,
            cap_w: 80,
            cap_h: 45,
            border: 3,
            inset_left: 0.0,
            inset_top: 0.0,
            inset_right: 0.0,
            inset_bottom: 0.0,
            fps: 60,
            brightness: 200,
            smoothing: 0.15,
            saturation: 1.4,
            gamma: 1.2,
            contrast: 1.0,
            gain_r: 1.0,
            gain_g: 1.0,
            gain_b: 1.0,
            color_mode: "average".to_string(),
            capture_limit: true,
            mode: "screen".to_string(),
            static_r: 255,
            static_g: 120,
            static_b: 40,
            effect: "breathing".to_string(),
            effect_speed: 3.0,
            effect_min: 20.0,
            dom_scene: 0.6,
            dom_smooth: 0.95,
            slew: 5.0,
            palette: Vec::new(),
            palette_random: true,
            dom_vibrance: 0.25,
            dom_fidelity: 0.4,
            zone_depth: 33.0,
            gamma_r: 1.0,
            gamma_g: 1.0,
            gamma_b: 1.0,
            level: 100.0,
            power_limit: 100.0,
            accuracy: false,
            fade_time: 0.10,
            auto_crop: false,
            crop_speed: 2.0,
            music: false,
            music_min: 25.0,
            music_style: "dim".to_string(),
            music_sens: 1.0,
            music_band: "bass".to_string(),
            music_in_bass: 0.0,
            music_out_bass: 1.0,
            music_in_treble: 0.0,
            music_out_treble: 1.0,
            music_in_vol: 0.0,
            music_out_vol: 1.0,
            music_in_rpm: 0.0,
            music_out_rpm: 1.0,
            music_on_bass: true,
            music_on_treble: true,
            music_on_vol: true,
            music_on_rpm: true,
            monitor: None,
            segment: Vec::new(),
        }
    }
}

impl Config {
    /// Trechos efetivos: os [[segment]] do arquivo ou, se não houver,
    /// o layout antigo (esquerda, topo, direita e, se > 0, embaixo).
    pub fn segments(&self) -> Vec<Segment> {
        let mut v: Vec<Segment> = if !self.segment.is_empty() {
            self.segment.clone()
        } else {
            let mk = |edge: &str, n: usize| Segment {
                device: 0,
                edge: edge.to_string(),
                leds: n,
                reverse: false,
                music: true,
            };
            vec![
                mk("left", self.left),
                mk("top", self.top),
                mk("right", self.right),
                mk("bottom", self.bottom),
            ]
        };
        v.retain(|s| s.leds > 0);
        for s in v.iter_mut() {
            s.device = s.device.min(7);
            s.edge = s.edge.to_lowercase();
        }
        v
    }

    /// Quantidade de LEDs de cada fita (índice = número da fita, começando em 0).
    pub fn leds_per_device(&self) -> Vec<usize> {
        let segs = self.segments();
        let n = segs.iter().map(|s| s.device + 1).max().unwrap_or(1);
        let mut v = vec![0usize; n];
        for s in &segs {
            v[s.device] += s.leds;
        }
        v
    }

    pub fn leds(&self) -> usize {
        self.leds_per_device().iter().sum()
    }

    pub fn load(path: &Path) -> Self {
        std::fs::read_to_string(path)
            .ok()
            .and_then(|s| toml::from_str(&s).ok())
            .unwrap_or_default()
    }

    /// Grava a configuração completa em TOML.
    pub fn save(&self, path: &Path) -> std::io::Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let monitor_line = match &self.monitor {
            Some(m) => format!("monitor = \"{m}\""),
            None => "# monitor = \"DP-4\"".to_string(),
        };
        let mut t = format!(
            "# Quiklight — configuration (written by `quiklight --save`)\n\n\
             top = {}\nright = {}\nleft = {}\nbottom = {}\n\n\
             cap_w = {}\ncap_h = {}\nborder = {}\n\n\
             inset_left = {:.1}\ninset_top = {:.1}\ninset_right = {:.1}\ninset_bottom = {:.1}\n\n\
             {}\n\n\
             fps = {}\n\n\
             brightness = {}\nsmoothing = {:.2}\nsaturation = {:.2}\ngamma = {:.2}\n\
             contrast = {:.2}\ngain_r = {:.2}\ngain_g = {:.2}\ngain_b = {:.2}\n\
             color_mode = \"{}\"\ncapture_limit = {}\n",
            self.top,
            self.right,
            self.left,
            self.bottom,
            self.cap_w,
            self.cap_h,
            self.border,
            self.inset_left,
            self.inset_top,
            self.inset_right,
            self.inset_bottom,
            monitor_line,
            self.fps,
            self.brightness,
            self.smoothing,
            self.saturation,
            self.gamma,
            self.contrast,
            self.gain_r,
            self.gain_g,
            self.gain_b,
            self.color_mode,
            self.capture_limit
        );
        t.push_str(&format!(
            "mode = \"{}\"\nstatic_r = {}\nstatic_g = {}\nstatic_b = {}\neffect = \"{}\"\neffect_speed = {:.1}\neffect_min = {:.1}\ndom_scene = {:.2}\ndom_smooth = {:.3}\nslew = {:.1}\n",
            self.mode,
            self.static_r,
            self.static_g,
            self.static_b,
            self.effect,
            self.effect_speed,
            self.effect_min,
            self.dom_scene,
            self.dom_smooth,
            self.slew
        ));
        let pal = self.palette.iter().map(|x| format!("\"{}\"", x)).collect::<Vec<_>>().join(", ");
        t.push_str(&format!(
            "palette = [{}]\npalette_random = {}\ndom_vibrance = {:.2}\ndom_fidelity = {:.2}\nzone_depth = {:.0}\ngamma_r = {:.2}\ngamma_g = {:.2}\ngamma_b = {:.2}\n",
            pal, self.palette_random, self.dom_vibrance, self.dom_fidelity, self.zone_depth, self.gamma_r, self.gamma_g, self.gamma_b
        ));
        t.push_str(&format!(
            "level = {:.0}\npower_limit = {:.0}\naccuracy = {}\n",
            self.level, self.power_limit, self.accuracy
        ));
        t.push_str(&format!("fade_time = {:.2}\n", self.fade_time));
        t.push_str(&format!("auto_crop = {}\ncrop_speed = {:.1}\n", self.auto_crop, self.crop_speed));
        t.push_str(&format!("music = {}\nmusic_min = {:.0}\nmusic_style = \"{}\"\nmusic_sens = {:.2}\nmusic_band = \"{}\"\n", self.music, self.music_min, self.music_style, self.music_sens, self.music_band));
        for &(k, v) in [
            ("music_in_bass", self.music_in_bass), ("music_out_bass", self.music_out_bass),
            ("music_in_treble", self.music_in_treble), ("music_out_treble", self.music_out_treble),
            ("music_in_vol", self.music_in_vol), ("music_out_vol", self.music_out_vol),
            ("music_in_rpm", self.music_in_rpm), ("music_out_rpm", self.music_out_rpm),
        ].iter() {
            t.push_str(&format!("{} = {:.2}\n", k, v));
        }
        t.push_str(&format!(
            "music_on_bass = {}\nmusic_on_treble = {}\nmusic_on_vol = {}\nmusic_on_rpm = {}\n",
            self.music_on_bass, self.music_on_treble, self.music_on_vol, self.music_on_rpm
        ));
        for s in &self.segment {
            t.push_str(&format!(
                "\n[[segment]]\ndevice = {}\nedge = \"{}\"\nleds = {}\nreverse = {}\nmusic = {}\n",
                s.device, s.edge, s.leds, s.reverse, s.music
            ));
        }
        std::fs::write(path, t)
    }
}
