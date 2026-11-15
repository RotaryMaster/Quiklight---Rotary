"""Inicia o QuikLight no Windows sem abrir uma janela de console.

Execute por duplo clique com a associação .pyw do Python ou usando pythonw.exe.
Mantém a mesma instância única, ícone da bandeja e configurações da GUI principal.
"""
from pathlib import Path
import os
import sys

if os.name != "nt":
    raise SystemExit("Este iniciador é destinado ao Windows.")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from quiklight_gui import main

if __name__ == "__main__":
    sys.exit(main())
