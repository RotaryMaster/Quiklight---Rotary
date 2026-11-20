#!/usr/bin/env python3
"""Live QuikLight RGB A/B diagnosis; non-root, reversible, no new capture backend.

Pause a scene on screen and minimize Konsole after starting. The test edits
only adaptive_fidelity_enabled, adaptive_fidelity, adaptive_light and color_mode temporarily.
The original TOML bytes are restored in finally. The existing Rust backend
reloads TOML and writes LED output to quiklight-live.bin when .want is fresh.
"""
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import datetime
from pathlib import Path

home = Path.home()
cfg_path = Path(os.environ.get("XDG_DATA_HOME", str(home / ".local/share"))) / "quiklight-rust/config.toml"
runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
want = runtime / "quiklight-live.want"
live = runtime / "quiklight-live.bin"


def change_keys(source: str, **updates) -> str:
    text = source
    for key, value in updates.items():
        regex = rf"(?m)^({re.escape(key)}\s*=\s*)([^\r\n]+)$"
        replacement = f'\\g<1>{value}'
        text, count = re.subn(regex, replacement, text)
        if count != 1:
            raise RuntimeError(f"configuração não contém uma chave única: {key}")
    return text


def atomic_write(data: bytes, mode: int) -> None:
    with tempfile.NamedTemporaryFile(mode="wb", prefix=".fidelity-test-", suffix=".tmp",
                                      dir=cfg_path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.chmod(tmp, mode)
        os.replace(tmp, cfg_path)
    finally:
        tmp.unlink(missing_ok=True)


def capture(label: str, source: str, **values) -> list[float]:
    new_toml = change_keys(source, **values)
    tomllib.loads(new_toml)  # never put malformed config in a live service
    atomic_write(new_toml.encode("utf-8"), old_mode)
    print(f"  {label} ...", flush=True)
    # Backend polls configuration roughly every 250 ms. Do not use stale frame.
    time.sleep(0.95)
    frames = []
    seen = -1
    deadline = time.monotonic() + 4.0
    while len(frames) < 8 and time.monotonic() < deadline:
        want.touch()
        try:
            stat = live.stat()
            if stat.st_mtime_ns > seen and stat.st_mtime > (time.time() - 1.0):
                data = live.read_bytes()
                if len(data) >= 3 and len(data) % 3 == 0:
                    frames.append(data)
                    seen = stat.st_mtime_ns
        except FileNotFoundError:
            pass
        time.sleep(0.16)
    if len(frames) < 5:
        raise RuntimeError("Não foi possível coletar quadros atuais do backend. "
                           "Verifique se o serviço está capturando a tela.")
    frame_size = len(frames[0])
    frames = [f for f in frames if len(f) == frame_size]
    avg = [statistics.mean(f[i] for f in frames) for i in range(frame_size)]
    brightness = statistics.mean(sum(avg[j:j+3]) / 3 for j in range(0,len(avg),3))
    leds = [sum(avg[j:j+3]) / 3 for j in range(0, len(avg), 3)]
    ranked = sorted(leds)
    p90 = ranked[min(len(ranked)-1, int(len(ranked)*0.9))]
    hot = sum(v >= 100.0 for v in leds)
    print(f"    {len(frames)} quadros; {frame_size//3} LEDs; brilho RGB médio {brightness:.2f}/255; "
          f"mediana {statistics.median(leds):.2f}; P90 {p90:.2f}; LEDs acima de 100/255: {hot}")
    return avg


def compare(label: str, a: list[float], b: list[float]) -> None:
    if len(a) != len(b):
        print(f"  {label}: quantidade de LEDs mudou; comparação inválida")
        return
    delta = [abs(x-y) for x,y in zip(a,b)]
    mean = statistics.mean(delta)
    maximum = max(delta, default=0)
    changing = sum(v >= 1.0 for v in delta)
    print(f"  {label}: diferença absoluta média {mean:.2f}/255,"
          f" máxima {maximum:.1f}/255; canais alterados >=1: {changing}/{len(delta)}")


def main() -> None:
    if os.geteuid() == 0:
        raise RuntimeError("Execute sem sudo.")
    result = subprocess.run(["systemctl","--user","is-active","--quiet","quiklight.service"])
    if result.returncode:
        raise RuntimeError("O serviço QuikLight não está ativo. Nada foi alterado.")
    if not cfg_path.is_file() or not runtime.is_dir():
        raise RuntimeError("Configuração ou diretório de execução não encontrado.")
    original = cfg_path.read_bytes()
    source = original.decode("utf-8")
    settings = tomllib.loads(source)
    if settings.get("mode") != "screen":
        raise RuntimeError("Este teste requer mode='screen', para comparar cores de borda.")
    for key in ("adaptive_fidelity_enabled","adaptive_fidelity","adaptive_light","color_mode"):
        if key not in settings:
            raise RuntimeError(f"Chave ausente: {key}")
    global old_mode
    old_mode = cfg_path.stat().st_mode & 0o777
    backup = cfg_path.with_name(f"config.toml.before-fidelity-diagnostic-{datetime.now():%Y%m%d-%H%M%S}.bak")
    if backup.exists():
        raise RuntimeError("Backup com nome já existente; não será sobrescrito.")
    shutil.copy2(cfg_path,backup)
    created_want = not want.exists()
    print("=== DIAGNÓSTICO RGB DE FIDELIDADE ADAPTATIVA ===")
    print(f"Configuração original: {settings['adaptive_fidelity_enabled']=}, "
          f"{settings['adaptive_fidelity']=}, {settings['adaptive_light']=}, "
          f"{settings['color_mode']=}")
    print(f"Backup extra: {backup}")
    label = sys.argv[1] if len(sys.argv) > 1 else "noturna"
    print(f"Cena selecionada: {label}. Deixe a cena do anime PAUSADA, sem menus nas bordas.")
    print("Minimize o Konsole agora. Comparação começa em 3 segundos...",flush=True)
    time.sleep(3)
    try:
        baseline = capture("A - original, vívido ligado",source,
                           adaptive_fidelity_enabled="false",adaptive_fidelity="100",
                           adaptive_light="0",color_mode='"vivid"')
        color = capture("B - fidelidade de cor 100%, luz 0%",source,
                        adaptive_fidelity_enabled="true",adaptive_fidelity="100",
                        adaptive_light="0",color_mode='"vivid"')
        light60 = capture("C - fidelidade 100%, luz 60%",source,
                          adaptive_fidelity_enabled="true",adaptive_fidelity="100",
                          adaptive_light="60",color_mode='"vivid"')
        light100 = capture("D - fidelidade 100%, luz 100%",source,
                           adaptive_fidelity_enabled="true",adaptive_fidelity="100",
                           adaptive_light="100",color_mode='"vivid"')
        baseline2 = capture("E - original novamente, vívido ligado",source,
                            adaptive_fidelity_enabled="false",adaptive_fidelity="100",
                            adaptive_light="0",color_mode='"vivid"')
        average = capture("F - original, vívido desligado",source,
                          adaptive_fidelity_enabled="false",adaptive_fidelity="100",
                          adaptive_light="0",color_mode='"average"')
        print()
        print("=== RESULTADOS (" + label.upper() + ") ===")
        compare("A -> B: fidelidade de cor sem reduzir luz",baseline,color)
        compare("B -> C: redução dinâmica da luz em 60%",color,light60)
        compare("B -> D: redução dinâmica da luz em 100%",color,light100)
        compare("A -> D: efeito total máximo",baseline,light100)
        compare("A -> E: deriva da cena (controle)",baseline,baseline2)
        compare("E -> F: efeito de desligar o vívido",baseline2,average)
        print("Compare A -> D com A -> E: se a diferença total for >> deriva, o efeito chegou aos LEDs.")
        print("Se o brilho continuar excessivo na cena noturna, precisamos adaptar a resposta a cenas escuras.")
    finally:
        atomic_write(original,old_mode)
        if created_want:
            want.unlink(missing_ok=True)
        print()
        print("Configuração original RESTAURADA; nenhum ganho RGB alterado.",flush=True)


if __name__=="__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO: {e}",file=sys.stderr)
        sys.exit(1)
