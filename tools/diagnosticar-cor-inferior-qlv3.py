#!/usr/bin/env python3
"""Diagnóstico de cor da fita inferior (somente leitura do TOML e RGB publicado).

ÚNICA ESCRITA OPERACIONAL: atualiza quiklight-live.want em XDG_RUNTIME_DIR
para solicitar ao Rust quadros de telemetria. NÃO escreve config, não aciona
serviço, USB, HID, nem muda cores/modos. Exibe SOMENTE parâmetros RGB/mapeamento.
O preview QLV3/v1 é output calculado, NÃO confirmação luminosa do hardware.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import os
import statistics
import struct
import sys
import time
import tomllib

HOME = Path.home()
CONFIG = HOME / ".local/share/quiklight-rust/config.toml"
BACKUPS = HOME / "Projetos/quiklight-glass-teste/backups/Stage02-v054"
RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
FIELDS = (
    "mode", "color_mode", "accuracy", "brightness", "smoothing",
    "saturation", "gamma", "gamma_r", "gamma_g", "gamma_b",
    "contrast", "gain_r", "gain_g", "gain_b", "level",
    "auto_crop", "crop_speed", "border", "cap_w", "cap_h",
    "inset_left", "inset_top", "inset_right", "inset_bottom",
    "black_level", "adaptive_black", "music", "music_style",
    "music_band", "music_sens", "zone_depth",
)
STRIP_FIELDS = ("physical_leds", "enabled", "mode", "lighting_mode",
                "brightness", "power_limit", "source_mode", "intensity",
                "color_mode", "effect", "music")
SEGMENT_FIELDS = ("device", "edge", "start_led", "leds", "enabled",
                  "reverse", "source_mode", "mirror_device", "mirror_edge",
                  "lighting_mode", "intensity", "music", "music_band")


def config_readonly():
    if not CONFIG.is_file() or CONFIG.is_symlink():
        raise RuntimeError("config.toml ativo não encontrado como arquivo regular")
    with CONFIG.open("rb") as f:
        cfg = tomllib.load(f)
    print("=== CONFIGURAÇÃO ATIVA — SOMENTE CAMPOS NÃO SENSÍVEIS ===")
    for key in FIELDS:
        if key in cfg:
            value = cfg[key]
            if type(value) in (str, float, int, bool) and len(str(value)) <= 80:
                print(f"{key} = {value}")
    strips = cfg.get("strip", [])
    segs = cfg.get("segment", [])
    print(f"Quantidade: {len(strips)} fita(s), {len(segs)} segmento(s)")
    for index, item in enumerate(strips):
        if isinstance(item, dict):
            print(f"fita[{index}]: " + " ".join(
                f"{k}={item[k]}" for k in STRIP_FIELDS
                if k in item and type(item[k]) in (int, float, bool, str)))
    for index, item in enumerate(segs):
        if isinstance(item, dict):
            print(f"segmento[{index}]: " + " ".join(
                f"{k}={item[k]}" for k in SEGMENT_FIELDS
                if k in item and type(item[k]) in (int, float, bool, str)))
    return cfg


def previous_comparison(current):
    print("\n=== COMPARAÇÃO COM BACKUP ANTES DO TESTE ===")
    if not BACKUPS.is_dir():
        print("Pasta de backup não localizada.")
        return
    snaps = [p for p in BACKUPS.glob("config-antes-teste-*.toml")
             if p.is_file() and not p.is_symlink()]
    if not snaps:
        print("Nenhum backup encontrado.")
        return
    snap = max(snaps, key=lambda p: p.stat().st_mtime)
    with snap.open("rb") as f:
        old = tomllib.load(f)
    print(f"Backup: {snap.name}")
    for k in FIELDS:
        a, b = old.get(k, "<ausente>"), current.get(k, "<ausente>")
        if a != b and type(a) in (int, float, bool, str) and type(b) in (
                int, float, bool, str):
            print(f"ALTERADO {k}: {a} -> {b}")
    for section in ("strip", "segment"):
        a, b = old.get(section, []), current.get(section, [])
        if a != b:
            print(f"ALTERADO [[{section}]]: snapshot={len(a)}, atual={len(b)}")
            keys = STRIP_FIELDS if section == "strip" else SEGMENT_FIELDS
            for i, (left, right) in enumerate(zip(a, b)):
                for k in keys:
                    if left.get(k) != right.get(k):
                        print(f"  {section}[{i}].{k}: "
                              f"{left.get(k, '<ausente>')} -> "
                              f"{right.get(k, '<ausente>')}")
        else:
            print(f"[[{section}]]: sem diferenças")
    if old == current:
        print("TOML semanticamente idêntico ao backup pré-teste.")


def samples_by_device(raw: bytes, sizes: list[int]):
    expected = sum(sizes) * 3
    if len(raw) != expected:
        print(f"quiklight-live.bin tamanho={len(raw)}; esperado={expected}. "
              "Não atribuirei bytes a dispositivos sem confirmar layout.")
        return None
    result = []
    pos = 0
    for n in sizes:
        row = [tuple(raw[pos + 3*i:pos + 3*i + 3]) for i in range(n)]
        result.append(row)
        pos += 3*n
    return result


def report_rgb(rows, cfg):
    print("\n=== RGB FINAL CALCULADO PELO BACKEND (NÃO É LEITURA ÓPTICA) ===")
    for i, row in enumerate(rows):
        if not row:
            continue
        med = tuple(round(statistics.mean(px[k]) for px in row), 1)
                    for k in range(3))
        print(f"Fita {i+1}: LEDs físicos={len(row)} média RGB={med}")
    for i, seg in enumerate(cfg.get("segment", [])):
        if not isinstance(seg, dict):
            continue
        d = int(seg.get("device", 0))
        st = seg.get("start_led")
        n = int(seg.get("leds", 0))
        if not (0 <= d < len(rows)) or not isinstance(st, int):
            print(f"Trecho {i}: mapeamento explícito ausente/índice inválido")
            continue
        if st < 0 or n < 0 or st + n > len(rows[d]):
            print(f"Trecho {i}: offset fora da faixa; analisar antes de aplicar.")
            continue
        if n == 0:
            continue
        pixels = rows[d][st:st+n]
        m = tuple(round(statistics.mean(p[k] for p in pixels), 1)
                  for k in range(3))
        maxima = tuple(max(p[k] for p in pixels) for k in range(3))
        counts = Counter(
            ("R" if p[0] > p[1]*1.25 and p[0] > p[2]*1.25
             else "G" if p[1] > p[0]*1.25 and p[1] > p[2]*1.25
             else "B" if p[2] > p[0]*1.25 and p[2] > p[1]*1.25
             else "neutro") for p in pixels if max(p) >= 8)
        print(f"Trecho {i} fita={d+1} borda={seg.get('edge')} "
              f"posições={st}-{st+n-1} ativo={seg.get('enabled', True)} "
              f"fonte={seg.get('source_mode', 'independent')} "
              f"RGB_médio={m} picos={maxima} dominância={dict(counts)}")


def live_capture(cfg):
    print("\n=== MONITORAMENTO DE SAÍDA RGB POR ~3 SEGUNDOS ===")
    if not RUNTIME.is_dir():
        print("XDG_RUNTIME_DIR não localizado; sem telemetria.")
        return
    sizes = []
    for entry in cfg.get("strip", []):
        n = entry.get("physical_leds") if isinstance(entry, dict) else None
        if not isinstance(n, int) or not 1 <= n <= 1000:
            print("Contagens physical_leds indisponíveis; decodificação v1 bloqueada.")
            return
        sizes.append(n)
    if not sizes:
        print("Sem perfis [[strip]] para decodificar a telemetria física.")
        return
    want = RUNTIME / "quiklight-live.want"
    source = RUNTIME / "quiklight-live.bin"
    qlv3 = RUNTIME / "quiklight-live-v3.bin"
    seen = set()
    start = time.monotonic()
    packets = 0
    while time.monotonic() - start < 3.3:
        try:
            want.touch()
        except OSError as exc:
            print(f"Não foi possível solicitar RGB: {exc}")
            return
        try:
            st = source.stat()
            age = time.time() - st.st_mtime
            if st.st_mtime_ns not in seen and 0 <= age < 2:
                seen.add(st.st_mtime_ns)
                data = source.read_bytes()
                parsed = samples_by_device(data, sizes)
                if parsed is not None and (packets == 0 or packets % 10 == 0):
                    print(f"\nFrame v1 nº {packets+1}, idade={age:.2f}s")
                    report_rgb(parsed, cfg)
                packets += 1
        except FileNotFoundError:
            pass
        except OSError as exc:
            print(f"Falha leitura telemetry: {exc}")
            break
        time.sleep(0.11)
    print(f"\nFrames distintos v1 recebidos: {packets}")
    try:
        stat3 = qlv3.stat()
        print(f"QLV3 disponível: {stat3.st_size} bytes, "
              f"idade={time.time()-stat3.st_mtime:.2f}s")
        with qlv3.open("rb") as f:
            head=f.read(24)
        print(f"QLV3 cabeçalho: {head.hex(' ')}")
    except OSError:
        print("QLV3 indisponível/sem acesso no intervalo.")
    if not packets:
        print("Sem quiklight-live.bin recente: não inferir cor física com ausência de frame.")
        print("Abra Captura/LEDs e fitas com prévia QLV3, ou verifique se o serviço está ativo.")


def main():
    print("QUIKLIGHT — AUDITORIA DA COR INFERIOR")
    print("Esta ferramenta só lê configurações; toca SOMENTE quiklight-live.want.")
    cfg = config_readonly()
    previous_comparison(cfg)
    live_capture(cfg)
    print("\nConcluído. Configuração, serviço, HID e LEDs não foram alterados.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(2)
