//! Optional adaptive screen-color fidelity, before and after the user's
//! existing RGB white-balance calibration. Strength 0 must be legacy-exact.
//! This module does NOT change the calibrated gain_r/g/b or gamma_r/g/b.

#[derive(Clone, Copy, Debug)]
pub struct Adjustment {
    pub saturation_multiplier: f32,
    /// Uniform light reduction applied AFTER the usual calibrated transforms.
    /// Equal scaling of all output channels preserves the user's RGB ratios.
    pub output_scale: f32,
}

fn smoothstep(lo: f32, hi: f32, x: f32) -> f32 {
    let t = ((x - lo) / (hi - lo)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

fn srgb_to_linear(x: f32) -> f32 {
    let v = x.clamp(0.0, 1.0);
    if v <= 0.04045 {
        v / 12.92
    } else {
        ((v + 0.055) / 1.055).powf(2.4)
    }
}

/// Retain the original weighted-sampling behavior at strength zero.
/// At higher strengths, blend vivid's color-biased weights with equal weights:
/// the average is less likely to be pulled toward a few saturated pixels.
pub fn vivid_weight(original_weight: f32, strength: f32) -> f32 {
    let k = (strength / 100.0).clamp(0.0, 1.0);
    if k == 0.0 {
        return original_weight;
    }
    1.0 + (original_weight - 1.0) * (1.0 - 0.75 * k)
}

/// Pixel/sampled-zone adaptation occurs in SOURCE RGB space, *before* the
/// existing gain/gamma white-balance calibration. Neutral-white channel
/// calibration stays intact; do not try to make the resulting LED RGB equal.
pub fn adjustment(r: f32, g: f32, b: f32, strength: f32, saturation: f32) -> Adjustment {
    let k = (strength / 100.0).clamp(0.0, 1.0);
    if k <= 0.0 {
        return Adjustment {
            saturation_multiplier: saturation,
            output_scale: 1.0,
        };
    }

    let max = r.max(g).max(b).max(0.0);
    let min = r.min(g).min(b);
    let chroma = if max > 0.0 { (max - min) / max } else { 0.0 };

    // W3C sRGB-linearized relative luminance: not simply the largest channel
    // and not the current LED gains, which are a hardware calibration.
    let luminance = 0.2126 * srgb_to_linear(r)
        + 0.7152 * srgb_to_linear(g)
        + 0.0722 * srgb_to_linear(b);

    // Strong adaptation for bright, low-saturation (pastel) areas.
    // Naturally saturated highlights remain unchanged. Near-neutral white
    // is only softly dimmed: its calibrated physical white point is retained.
    let light = smoothstep(0.28, 0.72, luminance);
    let soft = 1.0 - smoothstep(0.18, 0.72, chroma);
    let pastel = light * soft;

    let saturation_multiplier = if saturation > 1.0 {
        1.0 + (saturation - 1.0) * (1.0 - 0.95 * k * pastel)
    } else {
        saturation
    };

    // 12% maximum reduction for neutral whites and up to 30% for pastels,
    // scaled by user strength. Applied uniformly after white calibration.
    let colorful = smoothstep(0.02, 0.16, chroma);
    let max_reduction = 0.12 + 0.18 * colorful;
    let output_scale = 1.0 - k * pastel * max_reduction;

    Adjustment { saturation_multiplier, output_scale }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_is_legacy_identical() {
        for (r,g,b) in [(0.0,0.0,0.0),(0.9,0.7,0.7),(1.0,0.0,0.0)] {
            let a = adjustment(r,g,b,0.0,1.4);
            assert_eq!(a.saturation_multiplier,1.4);
            assert_eq!(a.output_scale,1.0);
        }
        assert_eq!(vivid_weight(0.25,0.0),0.25);
    }

    #[test]
    fn pastel_has_more_protection_than_vibrant_red() {
        let pastel = adjustment(0.95,0.79,0.71,80.0,1.4);
        let vivid = adjustment(1.0,0.1,0.05,80.0,1.4);
        assert!(pastel.saturation_multiplier < vivid.saturation_multiplier);
        assert!(pastel.output_scale < vivid.output_scale);
        assert_eq!(vivid.output_scale,1.0);
    }

    #[test]
    fn near_white_is_dimmed_less_than_colored_pastel() {
        let white = adjustment(0.96,0.96,0.96,100.0,1.4);
        let colored = adjustment(0.95,0.79,0.71,100.0,1.4);
        assert!(white.output_scale >= 0.88 - 0.0001);
        assert!(colored.output_scale < white.output_scale);
    }

    #[test]
    fn no_gain_amplification_or_negative_output() {
        for k in [0.0,35.0,70.0,100.0,200.0] {
            let a = adjustment(0.9,0.8,0.8,k,1.4);
            assert!((0.7..=1.0).contains(&a.output_scale));
            assert!((1.0..=1.4).contains(&a.saturation_multiplier));
        }
    }
}
