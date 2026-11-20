#!/usr/bin/env python3
"""Live QuikLight RGB A/B diagnosis; non-root, reversible, no new capture backend.

Pause a scene on screen and minimize Konsole after starting. The test edits
only adaptive_fidelity_enabled, adaptive_fidelity and color_mode temporarily.
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
    print(f"    {len(frames)} quadros; {frame_size//3} LEDs; brilho RGB médio {brightness:.2f}/255")
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
    for key in ("adaptive_fidelity_enabled","adaptive_fidelity","color_mode"):
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
          f"{settings['adaptive_fidelity']=}, {settings['color_mode']=}")
    print(f"Backup extra: {backup}")
    print("Deixe um quadro de Tengobu PAUSADO, sem controles sobre a borda.")
    print("Minimize o Konsole agora. Comparação começa em 3 segundos...",flush=True)
    time.sleep(3)
    try:
        baseline = capture("A - original, vívido ligado",source,
                           adaptive_fidelity_enabled="false",adaptive_fidelity="100",color_mode='"vivid"')
        active = capture("B - adaptativa 100%, vívido ligado",source,
                         adaptive_fidelity_enabled="true",adaptive_fidelity="100",color_mode='"vivid"')
        baseline2 = capture("C - original novamente, vívido ligado",source,
                            adaptive_fidelity_enabled="false",adaptive_fidelity="100",color_mode='"vivid"')
        average = capture("D - original, vívido desligado",source,
                          adaptive_fidelity_enabled="false",adaptive_fidelity="100",color_mode='"average"')
        print()
        print("=== RESULTADOS ===")
        compare("Efeito adaptativa A vs B",baseline,active)
        compare("Deriva da cena A vs C (ideal perto de zero)",baseline,baseline2)
        compare("Efeito vívido C vs D",baseline2,average)
        print("Interpretação: se A vs B ~ deriva, o efeito é pequeno/inexistente nesta cena.")
        print("Se A vs B >> deriva, o backend altera RGB, mas a diferença pode ser pouco visível.")
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
