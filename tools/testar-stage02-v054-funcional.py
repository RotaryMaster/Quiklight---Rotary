#!/usr/bin/env python3
"""Stage02 v0.5.4: abrir a GUI da v0.5.3 em modo funcional, isoladamente.

Não instala nem substitui a GUI/Rust, e não altera config.toml sozinho.
Extrai fontes numa pasta experimental, verifica SHA256, compila Python,
executa testes e cria backup privado do TOML antes de abrir sem --visual-demo.

ATENÇÃO: depois de abrir, os controles Aplicar/Tempo real podem gravar a
configuração ATIVA e acionar o serviço. Só os utilize após revisar os valores.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile

ARCHIVE = "QuikLight-Stage02-v05.3-MultiStrip-QLV3-Fluido-FONTES.zip"
EXPECTED = "0417444af2a9e060ed1b65e9a3968f0ffeaaa6aa30a2b07ad07b295adb3f5ea2"
WORKSPACE = Path.home() / "Projetos" / "quiklight-glass-teste"
STAGING = WORKSPACE / "Stage02-v0.5.4-funcional"
CONFIG = Path.home() / ".local" / "share" / "quiklight-rust" / "config.toml"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as src:
        for block in iter(lambda: src.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def extract_safe(archive: Path, output: Path) -> None:
    work = Path(tempfile.mkdtemp(prefix=".stage02-v054-", dir=WORKSPACE))
    try:
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            if not infos or len(infos) > 3000 or sum(i.file_size for i in infos) > 120_000_000:
                raise RuntimeError("Conteúdo ZIP inesperado; abortado")
            for info in infos:
                p = PurePosixPath(info.filename)
                if p.is_absolute() or ".." in p.parts or not p.parts:
                    raise RuntimeError("Caminho inseguro no ZIP")
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise RuntimeError("Link simbólico no ZIP não permitido")
                dst = work.joinpath(*p.parts)
                if info.is_dir():
                    dst.mkdir(parents=True, exist_ok=True)
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                if info.file_size > 15_000_000:
                    raise RuntimeError("Arquivo excessivo no ZIP")
                with z.open(info) as source, dst.open("xb") as target:
                    shutil.copyfileobj(source, target)
        # Somente diretório isolado, nunca altera a instalação .local do usuário.
        if output.exists() or output.is_symlink():
            raise RuntimeError(f"Destino já existe; não sobrescrever: {output}")
        work.rename(output)
    finally:
        if work.exists():
            shutil.rmtree(work)


def find_stage(root: Path) -> Path:
    launchers = [p for p in root.rglob("iniciar-linux.sh") if p.is_file() and
                 len(p.relative_to(root).parts) <= 5]
    if len(launchers) != 1:
        raise RuntimeError(f"Esperado exatamente um iniciar-linux.sh; encontrados {len(launchers)}")
    stage = launchers[0].parent
    full = stage / "gui" / "full_ui.py"
    back = stage / "gui" / "backend_io.py"
    if not full.is_file() or not back.is_file():
        raise RuntimeError("GUI/backend_io não encontrados: pacote incompatível")
    src = full.read_text("utf-8")
    for required in ("def apply_changes(", "def toggle_realtime(", "def _auto_apply(",
                     "self.visual_demo", "self.apply.setEnabled("):
        if required not in src:
            raise RuntimeError(f"Guarda do controle não encontrada: {required}")
    script = launchers[0].read_text("utf-8")
    if "--visual-demo" in script:
        raise RuntimeError("Launcher contém --visual-demo; não é possível ativar modo funcional com segurança")
    return stage


def backup_config() -> Path:
    if not CONFIG.is_file() or CONFIG.is_symlink():
        raise RuntimeError(f"Configuração ativa regular não encontrada: {CONFIG}")
    with CONFIG.open("rb") as src:
        content = src.read()
    try:
        data = tomllib.loads(content.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError(f"Configuração TOML inválida: {exc}") from exc
    if "segment" not in data or "strip" not in data:
        raise RuntimeError("Configuração física MultiStrip não detectada; abortado")
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backups = WORKSPACE / "backups" / "Stage02-v054"
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    backups.chmod(0o700)
    dst = backups / f"config-antes-teste-{stamp}-{os.getpid()}.toml"
    fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(content)
    if digest(CONFIG) != digest(dst):
        raise RuntimeError("Backup não confere com a configuração ativa; abortado")
    print(f"Backup privado OK: {dst}", flush=True)
    print(f"MultiStrip lido: {len(data['strip'])} fitas; {len(data['segment'])} segmentos", flush=True)
    return dst


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, default=Path.home() / "Downloads" / ARCHIVE)
    p.add_argument("--somente-preparar", action="store_true",
                   help="Valida e cria backup, mas não inicia a GUI")
    args = p.parse_args()
    archive = args.zip.expanduser().resolve()
    print("=== QUIKLIGHT STAGE02 v0.5.4 — ENSAIO FUNCIONAL ISOLADO ===", flush=True)
    print("Fonte:", archive, flush=True)
    if not archive.is_file() or digest(archive) != EXPECTED:
        raise RuntimeError("ZIP não encontrado ou SHA256 divergente; abortado sem extrair")
    print("SHA256 do ZIP confirmado.", flush=True)
    py = WORKSPACE / ".venv" / "bin" / "python"
    if not py.is_file():
        raise RuntimeError(f"Python de testes inexistente: {py}")
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    if not STAGING.exists():
        extract_safe(archive, STAGING)
        print("Fontes extraídas somente em", STAGING, flush=True)
    stage = find_stage(STAGING)
    if not (stage / "tests").is_dir():
        raise RuntimeError("Testes do pacote não encontrados; não abrir GUI")
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = os.pathsep.join([str(stage), str(stage / "gui"),
                                        env.get("PYTHONPATH", "")])
    env["VIRTUAL_ENV"] = str(py.parent.parent)
    env["PATH"] = str(py.parent) + os.pathsep + env.get("PATH", "")
    print("=== Verificando sintaxe ===", flush=True)
    subprocess.run([str(py), "-m", "compileall", "-q", str(stage / "gui")],
                   cwd=stage, env=env, check=True)
    print("=== Executando regressão do pacote ===", flush=True)
    subprocess.run([str(py), "-m", "unittest", "discover", "-s", str(stage / "tests")],
                   cwd=stage, env=env, check=True)
    backup_config()
    if args.somente_preparar:
        print("Preparação concluída. GUI NÃO iniciada.", flush=True)
        return 0
    state = subprocess.run(["systemctl", "--user", "is-active", "quiklight.service"],
                           capture_output=True, text=True, check=False)
    if state.stdout.strip() != "active":
        print("ATENÇÃO: serviço QuikLight não está ativo. Não será iniciado automaticamente.", flush=True)
        return 3
    env.pop("QT_QPA_PLATFORM", None)
    print("=== ABRINDO GUI EXPERIMENTAL SEM --visual-demo ===", flush=True)
    print("Até você clicar em Aplicar ou confirmar Tempo real, não há pedido de gravação.", flush=True)
    print("Não altere direção/offsets dos LEDs neste primeiro ensaio.", flush=True)
    return subprocess.run(["bash", str(stage / "iniciar-linux.sh")],
                          cwd=stage, env=env, check=False).returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile,
            subprocess.CalledProcessError) as exc:
        print("ERRO: procedimento interrompido:", exc, file=sys.stderr, flush=True)
        sys.exit(2)
