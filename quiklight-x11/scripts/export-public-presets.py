#!/usr/bin/env python3
"""Exporta somente parâmetros visuais de presets locais do Bazzite.

Os arquivos são preparados em Downloads; nada é enviado ao GitHub.
Nomes originais, IDs de hardware, monitores, caminhos, IPs e comentários
não são incluídos. Revise o resultado antes de publicar.
"""
from pathlib import Path
import re
import tomllib

home = Path.home()
source = home / ".local/share/quiklight-rust/presets"
out = home / "Downloads/quiklight-presets-publicos"
visual_numbers = {
    "brightness", "smoothing", "saturation", "gamma", "contrast",
    "gain_r", "gain_g", "gain_b", "static_r", "static_g", "static_b",
    "effect_speed", "effect_min", "dom_scene", "dom_smooth", "slew",
    "dom_vibrance", "dom_fidelity", "zone_depth", "gamma_r", "gamma_g",
    "gamma_b", "fade_time", "level", "power_limit", "crop_speed",
}
visual_bools = {"accuracy", "palette_random", "auto_crop"}
visual_strings = {"mode", "color_mode", "effect"}
visual_arrays = {"palette"}

def encode(key, value):
    if key in visual_bools and type(value) is bool:
        return "true" if value else "false"
    if key in visual_numbers and type(value) in (int, float):
        if key in ("static_r", "static_g", "static_b", "brightness"):
            if not 0 <= value <= 255: return None
        if not -10000 < float(value) < 10000: return None
        return repr(float(value))
    if key in visual_strings and isinstance(value, str):
        # Only short machine enum values, never paths, URLs or arbitrary text
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,30}", value):
            return '"' + value + '"'
        return None
    if key in visual_arrays and isinstance(value, list) and len(value) <= 10:
        if all(isinstance(v, str) and re.fullmatch(r"(?:#[0-9a-fA-F]{6}|)", v) for v in value):
            return "[" + ", ".join('"' + v + '"' for v in value) + "]"
    return None

if not source.is_dir():
    raise SystemExit(f"Pasta de presets não encontrada: {source}")
out.mkdir(parents=True, exist_ok=True)
items = []
for file in sorted(source.glob("*.toml")):
    if file.is_symlink():
        continue
    try:
        values = tomllib.loads(file.read_text(encoding="utf-8"))
        lines = []
        for key in sorted(visual_numbers | visual_bools | visual_strings | visual_arrays):
            if key in values:
                encoded = encode(key, values[key])
                if encoded is not None:
                    lines.append(f"{key} = {encoded}")
        if not lines:
            continue
        name = f"Preset-{len(items)+1:02d}.toml"
        (out / name).write_text("\n".join(lines)+"\n", encoding="utf-8")
        items.append(name)
    except (OSError, ValueError) as exc:
        print(f"Um preset não pôde ser exportado: {type(exc).__name__}")
print(f"Presets públicos gerados: {len(items)}")
print(f"Pasta local (ainda não publicada): {out}")
print("Verifique os valores e escolha quais disponibilizar antes do upload.")
