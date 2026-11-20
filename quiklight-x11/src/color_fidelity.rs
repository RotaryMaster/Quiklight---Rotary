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
pub fn adjustment(
    r: f32, g: f32, b: f32, strength: f32, light_reduction: f32, saturation: f32,
) -> Adjustment {
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

    // Preserve chromatic highlights while reducing oversaturation for
    // moderately bright, low-saturation regions. Smooth transitions avoid
    // visible threshold-popping in animations.
    let pastel_light = smoothstep(0.16, 0.66, luminance);
    let pastel_soft = 1.0 - smoothstep(0.18, 0.72, chroma);
    let pastel = pastel_light * pastel_soft;

    let saturation_multiplier = if saturation > 1.0 {
        1.0 + (saturation - 1.0) * (1.0 - 0.95 * k * pastel)
    } else {
        saturation
    };

    // Independent adaptive brightness knob. Previously the maximum effect
    // remained under 7% on real anime material even at 100% strength.
    // Perceptual light control now also acts on moderately bright areas, while
    // saturated highlights get only a small reduction.
    // 0% = no additional dimming. 100% = up to 55% on neutral bright areas.
    let light_knob = (light_reduction / 100.0).clamp(0.0, 1.0);
    let scene_light = smoothstep(0.08, 0.58, luminance);
    let color_protection = 1.0 - smoothstep(0.22, 0.75, chroma);
    let selective = 0.18 + 0.82 * color_protection;
    let output_scale = 1.0 - 0.55 * k * light_knob * scene_light * selective;

    Adjustment { saturation_multiplier, output_scale }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_is_legacy_identical() {
        for (r,g,b) in [(0.0,0.0,0.0),(0.9,0.7,0.7),(1.0,0.0,0.0)] {
            let a = adjustment(r,g,b,0.0,100.0,1.4);
            assert_eq!(a.saturation_multiplier,1.4);
            assert_eq!(a.output_scale,1.0);
        }
        assert_eq!(vivid_weight(0.25,0.0),0.25);
    }

    #[test]
    fn pastel_has_more_protection_than_vibrant_red() {
        let pastel = adjustment(0.95,0.79,0.71,100.0,60.0,1.4);
        let vivid = adjustment(1.0,0.1,0.05,100.0,60.0,1.4);
        assert!(pastel.saturation_multiplier < vivid.saturation_multiplier);
        assert!(pastel.output_scale < vivid.output_scale);
        assert!(pastel.output_scale < 0.90);
    }

    #[test]
    fn light_zero_disables_only_brightness_adaptation() {
        let color = adjustment(0.95,0.79,0.71,100.0,0.0,1.4);
        assert_eq!(color.output_scale,1.0);
        assert!(color.saturation_multiplier < 1.4);
    }

    #[test]
    fn stronger_light_knob_reduces_output_more() {
        let a = adjustment(0.95,0.79,0.71,100.0,30.0,1.4);
        let b = adjustment(0.95,0.79,0.71,100.0,90.0,1.4);
        assert!(b.output_scale < a.output_scale);
        assert_eq!(a.saturation_multiplier,b.saturation_multiplier);
    }

    #[test]
    fn calibrated_white_keeps_relative_rgb_channel_ratios() {
        let white = adjustment(0.96,0.96,0.96,100.0,60.0,1.4);
        assert!(white.output_scale > 0.0 && white.output_scale <= 1.0);
        // Neutral whites have no chroma to saturate; the protection may
        // reduce the nominal multiplier without tinting the result.
        assert!(white.saturation_multiplier >= 1.0 && white.saturation_multiplier <= 1.4);
    }

    #[test]
    fn no_amplification_or_negative_output() {
        for k in [0.0,35.0,70.0,100.0,200.0] {
            for dim in [0.0,60.0,100.0,200.0] {
                let a = adjustment(0.9,0.8,0.8,k,dim,1.4);
                assert!((0.45..=1.0).contains(&a.output_scale));
                assert!((1.0..=1.4).contains(&a.saturation_multiplier));
            }
        }
    }
}
