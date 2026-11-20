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
    r: f32, g: f32, b: f32, strength: f32,
    light_reduction: f32, dark_reduction: f32, saturation: f32,
) -> Adjustment {
    let k = (strength / 100.0).clamp(0.0, 1.0);
    let light_knob = (light_reduction / 100.0).clamp(0.0, 1.0);
    let dark_knob = (dark_reduction / 100.0).clamp(0.0, 1.0);
    if k <= 0.0 && light_knob <= 0.0 && dark_knob <= 0.0 {
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

    // Independent bright-scene luminosity reduction. It does not depend
    // on the color-fidelity slider; the global toggle gates it in Config.
    let scene_light = smoothstep(0.08, 0.58, luminance);
    let color_protection = 1.0 - smoothstep(0.22, 0.75, chroma);
    let selective = 0.18 + 0.82 * color_protection;
    let bright_scale = 1.0 - 0.55 * light_knob * scene_light * selective;

    // Dark scene correction: in user measurements an anime night scene
    // produced mean 14/255 LED output, yet the room still appeared too lit.
    // The bright-scene function above returns ~1.0 in such regions.
    // This curve gently scales down very dark RGB without tinting it.
    // Dark-saturated highlights are reduced somewhat less than neutral darks;
    // fully black stays black. For a clear scene, shadow_scale ~= 1.0.
    let shadow_scene = 1.0 - smoothstep(0.012, 0.16, luminance);
    let dark_selective = 0.70 + 0.30 * (1.0 - smoothstep(0.30, 0.85, chroma));
    let shadow_scale = 1.0 - 0.72 * dark_knob * shadow_scene * dark_selective;
    let output_scale = (bright_scale * shadow_scale).clamp(0.0, 1.0);

    Adjustment { saturation_multiplier, output_scale }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_is_legacy_identical() {
        for (r, g, b) in [(0.0,0.0,0.0),(0.9,0.7,0.7),(1.0,0.0,0.0)] {
            let a = adjustment(r,g,b,0.0,0.0,0.0,1.4);
            assert_eq!(a.saturation_multiplier,1.4);
            assert_eq!(a.output_scale,1.0);
        }
        assert_eq!(vivid_weight(0.25,0.0),0.25);
    }

    #[test]
    fn dim_night_pixels_are_reduced_even_when_bright_control_zero() {
        let a = adjustment(0.15,0.10,0.06,0.0,0.0,60.0,1.4);
        assert!(a.output_scale < 0.75, "dark scene must be perceptibly dimmed");
        assert!(a.output_scale > 0.50, "avoid sudden complete extinction");
        assert_eq!(a.saturation_multiplier,1.4);
    }

    #[test]
    fn dark_knob_is_independent_of_color_strength() {
        let a = adjustment(0.15,0.10,0.06,0.0,0.0,60.0,1.4);
        let b = adjustment(0.15,0.10,0.06,100.0,0.0,60.0,1.4);
        assert_eq!(a.output_scale,b.output_scale);
    }

    #[test]
    fn dark_knob_has_no_effect_on_bright_white() {
        let a = adjustment(0.96,0.96,0.96,0.0,0.0,0.0,1.4);
        let b = adjustment(0.96,0.96,0.96,0.0,0.0,100.0,1.4);
        assert_eq!(a.output_scale,b.output_scale);
    }

    #[test]
    fn light_knob_is_independent_of_color_strength() {
        let a = adjustment(0.95,0.79,0.71,0.0,60.0,0.0,1.4);
        let b = adjustment(0.95,0.79,0.71,100.0,60.0,0.0,1.4);
        assert_eq!(a.output_scale,b.output_scale);
    }

    #[test]
    fn pastel_has_more_color_protection_than_vivid_red() {
        let pastel = adjustment(0.95,0.79,0.71,100.0,0.0,0.0,1.4);
        let vivid = adjustment(1.0,0.1,0.05,100.0,0.0,0.0,1.4);
        assert!(pastel.saturation_multiplier < vivid.saturation_multiplier);
        assert_eq!(pastel.output_scale, 1.0);
    }

    #[test]
    fn full_black_stays_black() {
        let a = adjustment(0.0,0.0,0.0,100.0,100.0,100.0,1.4);
        assert_eq!(a.saturation_multiplier,1.4);
        assert!((0.0..=1.0).contains(&a.output_scale));
        // The pipeline multiplies zero-valued channels by output_scale.
    }

    #[test]
    fn max_reduction_bound_and_no_brightness_amplification() {
        for k in [0.0,35.0,100.0] {
            for bright in [0.0,60.0,100.0] {
                for dark in [0.0,60.0,100.0] {
                    for (r,g,b) in [(0.0,0.0,0.0),(0.1,0.12,0.15),(0.9,0.7,0.5),(1.0,0.2,0.0)] {
                        let a = adjustment(r,g,b,k,bright,dark,1.4);
                        assert!((0.0..=1.0).contains(&a.output_scale));
                        assert!((1.0..=1.4).contains(&a.saturation_multiplier));
                    }
                }
            }
        }
    }
}
