#!/usr/bin/env python3
"""Auditoria SOMENTE LEITURA dos controles Aplicar/Tempo real da Stage 02 v0.5.3.

Busca o pacote de fontes em ~/Downloads ou ~/Projetos (ou use --fonte CAMINHO).
Não executa o pacote, não extrai arquivos, não lê config.toml, não toca no serviço.
Saída curta adequada a copiar via: ... | tee >(wl-copy)
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
from pathlib import Path
import re
import sys
import zipfile

ZIP_RE = re.compile(r"(?i)(stage[\s._-]*0?2).*(?:v0?5[._-]?3|v0\.5\.3)")
KEEP = ("full_ui.py", "backend_io.py", "telemetry_live.py",
        "wheel_guard.py", "iniciar-linux.sh", "testar-e-abrir-linux.sh")
KEY = re.compile(r"(?i)(apply|aplicar|realtime|real_time|tempo.?real|on_rt|"
                 r"changed|pending|patch_config|config_view|write_config|"
                 r"save_config|service_cmd|visual_demo|dry_run)")
WIRING = re.compile(r"(?i)(\.connect\(|QTimer|--visual-demo|visual_demo|"
                    r"Aplicar|Tempo real|patch_config\(|read_config\(|"
                    r"write_config\(|service_cmd\()")
EXCLUDE = {".venv", "venv", ".git", "__pycache__", "node_modules",
           "target", "build", "dist", "cache", "backup", "backups"}


def choose_source(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Fonte informada não existe: {p}")
        return p
    found = []
    for root in (Path.home() / "Downloads", Path.home() / "Projetos"):
        if not root.is_dir():
            continue
        for cur, dirs, files in os.walk(root):
            relative = Path(cur).relative_to(root)
            if len(relative.parts) > 5:
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if d not in EXCLUDE and not d.startswith(".")]
            for name in files:
                if name.lower().endswith(".zip") and ZIP_RE.search(name):
                    p = Path(cur) / name
                    found.append((p.stat().st_mtime, p))
    if not found:
        raise FileNotFoundError("Pacote Stage 02 v0.5.3 não localizado em Downloads/Projetos. "
                                "Informe --fonte /caminho/para/arquivo.zip")
    return max(found)[1]


def sources_from_zip(path: Path) -> dict[str, str]:
    result = {}
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise ValueError(f"ZIP com erro de integridade: {bad}")
        entries = z.infolist()
        for e in entries:
            if e.is_dir() or e.file_size > 2_000_000:
                continue
            p = Path(e.filename.replace("\\", "/"))
            if p.name not in KEEP:
                continue
            if p.suffix == ".py" and "gui" not in [part.lower() for part in p.parts]:
                continue
            name = "/".join(p.parts)
            result[name] = z.read(e).decode("utf-8", errors="replace")
    return result


def sources_from_dir(path: Path) -> dict[str, str]:
    result = {}
    for p in path.rglob("*"):
        if not p.is_file() or p.is_symlink() or p.stat().st_size > 2_000_000:
            continue
        relative = p.relative_to(path)
        if len(relative.parts) > 8 or any(s in EXCLUDE for s in relative.parts):
            continue
        if p.name not in KEEP:
            continue
        if p.suffix == ".py" and "gui" not in [s.lower() for s in relative.parts]:
            continue
        result[str(relative)] = p.read_text("utf-8", errors="replace")
    return result


def masked(text: str) -> str:
    text = re.sub(r"(?i)(?:/var)?/home/[^/\s\"']+", "/home/USUARIO", text)
    text = re.sub(r"(?i)(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9_]{16,}", "[TOKEN_OCULTO]", text)
    text = re.sub(r"(?i)github_pat_[a-zA-Z0-9_]{20,}", "[TOKEN_OCULTO]", text)
    text = re.sub(r'''(?i)((?:secret|api_key|password|token)\s*[:=]\s*["'])([^"']+)(["'])''',
                  r"\1[OCULTO]\3", text)
    return text


def out_excerpt(lines: list[str], a: int, b: int):
    for i in range(a, min(len(lines), b)):
        print(f"{i+1:4d}: {masked(lines[i].rstrip())[:220]}")


def inspect(name: str, source: str):
    lines = source.splitlines()
    print(f"\n=== {name} | {len(lines)} linhas ===")
    if name.endswith(".sh"):
        for i, line in enumerate(lines):
            if WIRING.search(line):
                out_excerpt(lines, max(0, i-1), min(len(lines), i+2))
        return
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"ERRO DE SINTAXE: {exc}")
        return

    selected = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and KEY.search(node.name):
            selected.append(node)
    selected.sort(key=lambda n: n.lineno)
    print("Funções relacionadas:", ", ".join(f"{x.name}@{x.lineno}" for x in selected) or "(nenhuma)")

    # Os handlers são mais importantes que o restante do arquivo.
    priority = ("apply", "aplicar", "on_rt", "realtime", "tempo",
                "patch_config", "write_config", "changed", "pending", "service")
    selected.sort(key=lambda n: (min((i for i, k in enumerate(priority) if k in n.name.lower()), default=100),
                                 n.lineno))
    budget = 420
    for n in selected[:16]:
        if budget <= 0:
            break
        start = n.lineno - 1
        end = getattr(n, "end_lineno", n.lineno)
        count = min(70, end-start, budget)
        print(f"\n--- {n.name}({n.lineno}-{end}) ---")
        out_excerpt(lines, start, start+count)
        budget -= count

    print("\n--- Ligações, modo de demonstração e timers ---")
    hit_indices = [i for i, line in enumerate(lines) if WIRING.search(line)]
    for i in hit_indices[:55]:
        print(f"{i+1:4d}: {masked(lines[i].strip())[:220]}")
    if len(hit_indices) > 55:
        print(f"(... {len(hit_indices)-55} correspondências adicionais omitidas)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fonte", help="ZIP da Stage02 v0.5.3 ou pasta descompactada")
    a = ap.parse_args()
    try:
        path = choose_source(a.fonte)
        sources = sources_from_dir(path) if path.is_dir() else sources_from_zip(path)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print("ERRO:", exc)
        return 2

    print("STAGE 02 v0.5.3 — AUDITORIA DE CONTROLES / SOMENTE LEITURA")
    print("Origem:", masked(str(path)))
    if path.is_file():
        print("SHA256 ZIP:", hashlib.sha256(path.read_bytes()).hexdigest())
    print("Arquivos localizados:", len(sources))
    for key in sorted(sources):
        print(" -", key)

    if not sources:
        print("Não localizei o código de gui/ e os scripts de inicialização.")
        return 3
    for name, source in sorted(sources.items()):
        inspect(name, source)

    print("\nFIM: nenhum arquivo alterado; nenhum serviço reiniciado; "
          "nenhuma configuração ou dispositivo acessado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
