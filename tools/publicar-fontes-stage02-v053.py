#!/usr/bin/env python3
"""Publica SOMENTE fontes verificadas Stage 02 v0.5.3 no fork QuikLight correto.

Não instala software, não altera serviço Rust, não grava configuração TOML, não
toca no hardware e não muda repos locais. Verifica SHA256, evita secrets e
publica apenas código/fontes do ZIP sob uma subpasta experimental isolada.
Requer permissão git push na conta que executa este script.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

OWNER_REPO = "RotaryMaster/Quiklight---Rotary"
BRANCH = "feature/stage02-v054-apply-realtime"
EXPECTED_SHA256 = "0417444af2a9e060ed1b65e9a3968f0ffeaaa6aa30a2b07ad07b295adb3f5ea2"
FILE_NAME = "QuikLight-Stage02-v05.3-MultiStrip-QLV3-Fluido-FONTES.zip"
DEST_PREFIX = "experimental/stage02-v053-source"
SOURCE_ROOT = "Stage02-v0.5.3"
ALLOWED = {
    ".py", ".pyw", ".sh", ".md", ".qss", ".ui", ".qml", ".json",
    ".toml", ".txt", ".css", ".svg", ".desktop", ".png", ".jpg",
    ".jpeg", ".webp", ".ico", ".qrc", ".ini", ".yml", ".yaml"
}
BINARY = {".png", ".jpg", ".jpeg", ".webp", ".ico"}
SKIP_PARTS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", "target",
    ".pytest_cache", "build", "dist", "backups", "backup", "logs",
    "cache", "versions", ".cache", ".local", "private", "secrets"
}
SKIP_FILES = {
    ".env", ".env.local", "config.toml", "credentials.json",
    "token.json", "settings.ini", "secrets.json", "secrets.toml",
    "user.config", "key.pem", "id_rsa", "id_ed25519"
}
DANGEROUS_NAME = re.compile(
    r"(?i)(?:^|\b)(?:credential|access_token|refresh_token|"
    r"password|passwd|private_key|api_secret|secret_key)(?:\b|$)")
SECRET_TEXT = re.compile(
    r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{16,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"sk-[A-Za-z0-9]{32,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"(?i:Authorization\s*[:=]\s*['\"]?Bearer\s+)[A-Za-z0-9_.-]{20,}")
USER_HOME = re.compile(r"(?i)(?:/var)?/home/([^/\s\"']+)")
WINDOWS_HOME = re.compile(r"(?i)[A-Z]:[/\\]Users[/\\]([^/\\\s\"']+)")


def sha256(source: Path) -> str:
    h=hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_text(name: str, data: bytes) -> None:
    text=data.decode("utf-8")  # Não publicar arquivos indecodificáveis.
    if SECRET_TEXT.search(text):
        raise RuntimeError(f"Possível credencial encontrada em {name}: publicação bloqueada")
    for match in USER_HOME.finditer(text):
        if match.group(1).lower() not in {"usuario","user","username","example"}:
            raise RuntimeError(f"Caminho pessoal detectado em {name}: publicação bloqueada")
    for match in WINDOWS_HOME.finditer(text):
        if match.group(1).lower() not in {"usuario","user","username","example"}:
            raise RuntimeError(f"Caminho Windows pessoal detectado em {name}: publicação bloqueada")
    if name.endswith((".py", ".pyw")):
        ast.parse(text, filename=name)


def verified_sources(archive: Path) -> dict[str, bytes]:
    if not archive.is_file():
        raise RuntimeError(f"ZIP não localizado: {archive}")
    digest=sha256(archive)
    if digest!=EXPECTED_SHA256:
        raise RuntimeError(f"SHA256 não confere: {digest}")
    result={}
    total=0
    with zipfile.ZipFile(archive,"r") as z:
        if len(z.infolist())>1000:
            raise RuntimeError("ZIP com entradas demais")
        invalid=z.testzip()
        if invalid:
            raise RuntimeError(f"ZIP corrompido em {invalid}")
        for member in z.infolist():
            if member.is_dir():
                continue
            name=member.filename.replace("\\","/")
            p=PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts:
                raise RuntimeError("ZIP contém caminho inseguro")
            if len(p.parts)<2 or p.parts[0]!=SOURCE_ROOT:
                continue
            rel=PurePosixPath(*p.parts[1:])
            if any(x.lower() in SKIP_PARTS for x in rel.parts):
                continue
            if rel.name.lower() in SKIP_FILES or DANGEROUS_NAME.search(rel.name):
                continue
            if rel.suffix.lower() not in ALLOWED:
                continue
            if member.file_size>2_500_000 or total+member.file_size>25_000_000:
                raise RuntimeError("ZIP contém arquivo acima do limite de publicação")
            # Symlinks e outros tipos especiais são desabilitados.
            unix_mode=member.external_attr>>16
            if (unix_mode & 0o170000)==0o120000:
                raise RuntimeError(f"Link simbólico bloqueado: {rel}")
            data=z.read(member)
            if rel.suffix.lower() not in BINARY:
                scan_text(str(rel),data)
            total+=len(data)
            key=rel.as_posix()
            if key in result:
                raise RuntimeError(f"Caminho repetido no ZIP: {key}")
            result[key]=data
    required={"gui/full_ui.py","gui/backend_io.py","gui/telemetry_live.py",
              "gui/wheel_guard.py","iniciar-linux.sh"}
    missing=required-set(result)
    if missing:
        raise RuntimeError(f"Faltam fontes essenciais: {sorted(missing)}")
    if not any(x.startswith("tests/") for x in result):
        raise RuntimeError("Nenhum teste da Stage 02 encontrado; abortado")
    return result


def run(cmd: list[str], cwd: Path, env: dict[str,str] | None = None):
    return subprocess.run(cmd, cwd=cwd, env=env, check=True,
                          capture_output=True, text=True)


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip",type=Path,default=Path.home()/"Downloads"/FILE_NAME)
    p.add_argument("--preparar",action="store_true",
                   help="Somente verifica o ZIP e lista os arquivos, sem publicar")
    args=p.parse_args()
    sources=verified_sources(args.zip.expanduser())
    print("=== QUIKLIGHT STAGE02 — PUBLICAÇÃO RESTRITA DE FONTES ===",flush=True)
    print("Repositório correto:",OWNER_REPO,flush=True)
    print("Branch:",BRANCH,flush=True)
    print("SHA256 ZIP: OK",flush=True)
    print("Arquivos selecionados:",len(sources),flush=True)
    print("Bytes totais:",sum(len(x) for x in sources.values()),flush=True)
    print("Manifesto:")
    for rel in sorted(sources):
        print(" -",rel,flush=True)
    if args.preparar:
        print("Modo --preparar: não publicado.",flush=True)
        return 0
    with tempfile.TemporaryDirectory(prefix="quiklight-stage02-sync-") as td:
        work=Path(td)/"repo"
        env=os.environ.copy()
        env["GIT_TERMINAL_PROMPT"]="0"
        env["GIT_LFS_SKIP_SMUDGE"]="1"
        remote=f"https://github.com/{OWNER_REPO}.git"
        print("=== CLONANDO BRANCH EXPERIMENTAL ISOLADA ===",flush=True)
        try:
            subprocess.run(["git","clone","-q","--depth","1","--branch",BRANCH,
                            "--single-branch",remote,str(work)],
                           check=True,env=env)
        except (OSError,subprocess.CalledProcessError) as exc:
            raise RuntimeError("Não foi possível clonar a branch experimental") from exc
        dest=work/DEST_PREFIX
        if dest.exists():
            raise RuntimeError("Fontes v0.5.3 já publicadas nessa branch: não sobrescrever")
        dest.mkdir(parents=True)
        index=[]
        for rel,data in sorted(sources.items()):
            out=dest.joinpath(*PurePosixPath(rel).parts)
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(data)
            index.append({"path":rel,"bytes":len(data),
                          "sha256":hashlib.sha256(data).hexdigest()})
        (dest/"SOURCE-MANIFEST.json").write_text(
            json.dumps({"archive_sha256":EXPECTED_SHA256,
                        "stage":"Stage02-v0.5.3","files":index},
                       ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        run(["git","add","--",DEST_PREFIX],work,env)
        modified=run(["git","diff","--cached","--name-only"],work,env).stdout.splitlines()
        if len(modified)!=len(sources)+1:
            raise RuntimeError("Contagem de arquivos Git diferente do esperado")
        if any(not x.startswith(DEST_PREFIX+"/") for x in modified):
            raise RuntimeError("Arquivo fora do escopo; publicação bloqueada")
        if not run(["git","config","--get","user.name"],work,env).stdout.strip():
            run(["git","config","user.name","QuikLight Stage02 Source Sync"],work,env)
        try:
            email=run(["git","config","--get","user.email"],work,env).stdout.strip()
        except subprocess.CalledProcessError:
            email=""
        if not email:
            run(["git","config","user.email","noreply@users.noreply.github.com"],work,env)
        print("=== PUBLICANDO APENAS FONTES NA BRANCH EXPERIMENTAL ===",flush=True)
        run(["git","commit","-m","Stage02: import verified v0.5.3 GUI sources for v0.5.4 integration"],work,env)
        try:
            subprocess.run(["git","push","origin",f"HEAD:refs/heads/{BRANCH}"],
                           check=True,env=env)
        except (OSError,subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                "Git push falhou: autenticação GitHub local não disponível ou "
                "branch atualizada por outra sessão. Nenhum arquivo foi enviado. "
                "Não faça force-push. Use uma sessão autenticada de git/gh.") from exc
        sha=run(["git","rev-parse","HEAD"],work,env).stdout.strip()
        print("=== PUBLICAÇÃO CONCLUÍDA ===",flush=True)
        print("Commit:",sha,flush=True)
        print(f"https://github.com/{OWNER_REPO}/tree/{BRANCH}/{DEST_PREFIX}",flush=True)
        print("Nenhum serviço, hardware, configuração ativa ou instalação modificado.",flush=True)
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except (RuntimeError,ValueError,UnicodeError,zipfile.BadZipFile,
            OSError,subprocess.CalledProcessError,SyntaxError) as exc:
        print("ERRO: "+str(exc),file=sys.stderr,flush=True)
        sys.exit(2)
