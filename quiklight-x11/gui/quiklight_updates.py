"""Safe GitHub Releases updater for Quiklight (Python standard library only).

Published stable tags must be quiklight-vMAJOR.MINOR.PATCH, with SHA-256
release asset digests. Never install source branches or prereleases.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile

REPO = "RotaryMaster/rotaryopersonal"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=50"
TAG = re.compile(r"^quiklight-v(\d+)\.(\d+)\.(\d+)$")
PLATFORM = "windows" if os.name == "nt" else "linux"
ASSETS = {"windows": "quiklight-windows-x64.zip",
          "linux": "quiklight-linux-x64.tar.gz"}
COMMON = ("gui/quiklight_gui.py", "gui/quiklight_updates.py", "gui/update-version.json")
FILES = {"windows": COMMON + ("gui/quiklight_windows.pyw", "bin/quiklight.exe"),
         "linux": COMMON + ("bin/quiklight",)}
NOWIN = 0x08000000 if os.name == "nt" else 0
MAX_ARCHIVE = 120 * 1024 * 1024
MAX_FILE = 70 * 1024 * 1024


def version_tuple(value):
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(value))
    if m is None:
        raise ValueError("Versão inválida: " + str(value))
    return tuple(int(v) for v in m.groups())


def installed_version():
    try:
        return json.loads((Path(__file__).resolve().parent / "update-version.json")
                          .read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError, TypeError):
        return "0.29.0"  # Existing installations before the updater.


def check_release():
    current = installed_version()
    request = urllib.request.Request(API, headers={
        "User-Agent": "Quiklight-Updater/1.0",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=10) as response:
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("Resposta do GitHub muito grande.")
    entries = json.loads(data)
    if not isinstance(entries, list):
        raise ValueError("Resposta inesperada do GitHub.")
    candidates = []
    for item in entries:
        if not isinstance(item, dict) or item.get("draft") or item.get("prerelease"):
            continue
        match = TAG.fullmatch(str(item.get("tag_name") or ""))
        if match:
            candidates.append((tuple(map(int, match.groups())), item))
    if not candidates:
        return {"status": "none", "current": current}
    number, item = max(candidates, key=lambda entry: entry[0])
    latest = ".".join(map(str, number))
    if number <= version_tuple(current):
        return {"status": "current", "current": current, "latest": latest}
    asset = next((a for a in item.get("assets", [])
                  if a.get("name") == ASSETS[PLATFORM]), None)
    if asset is None:
        return {"status": "unsupported", "current": current, "latest": latest,
                "reason": "Release sem pacote para este sistema."}
    digest = str(asset.get("digest") or "")
    if not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", digest):
        return {"status": "unsupported", "current": current, "latest": latest,
                "reason": "Release sem checksum SHA-256."}
    size = asset.get("size")
    if not isinstance(size, int) or not (0 < size <= MAX_ARCHIVE):
        raise ValueError("Tamanho do pacote inválido.")
    url = str(asset.get("browser_download_url") or "")
    if not url.startswith(f"https://github.com/{REPO}/releases/download/") or not url.endswith("/" + ASSETS[PLATFORM]):
        raise ValueError("Endereço do pacote não corresponde ao repositório.")
    return {"status": "available", "current": current, "latest": latest,
            "url": url, "digest": digest[7:].lower(), "size": size,
            "notes": str(item.get("body") or "")[:1400],
            "release_url": str(item.get("html_url") or "")}


def update_root():
    if PLATFORM == "windows":
        folder = Path(os.environ["LOCALAPPDATA"]) / "Quiklight" / "updates"
    else:
        folder = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "quiklight" / "updates"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def download_and_stage(info):
    if info.get("status") != "available":
        raise ValueError("Não há atualização disponível.")
    stage = Path(tempfile.mkdtemp(prefix="staged-", dir=update_root()))
    archive = stage / ("package.zip" if PLATFORM == "windows" else "package.tar.gz")
    try:
        request = urllib.request.Request(info["url"],
                                          headers={"User-Agent": "Quiklight-Updater/1.0"})
        digest = hashlib.sha256()
        total = 0
        with urllib.request.urlopen(request, timeout=30) as response, archive.open("wb") as dst:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_ARCHIVE:
                    raise ValueError("Pacote excede o tamanho máximo.")
                digest.update(block)
                dst.write(block)
        if total != info["size"] or digest.hexdigest() != info["digest"]:
            raise ValueError("Integridade SHA-256 do pacote não confere.")
        if PLATFORM == "windows":
            with zipfile.ZipFile(archive) as bundle:
                for name in FILES[PLATFORM]:
                    member = bundle.getinfo(name)
                    if not member.is_dir() and 0 < member.file_size <= MAX_FILE:
                        target = stage / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with bundle.open(member) as src, target.open("wb") as dst:
                            shutil.copyfileobj(src, dst)
                    else:
                        raise ValueError("Arquivo inválido no pacote: " + name)
        else:
            with tarfile.open(archive, "r:gz") as bundle:
                for name in FILES[PLATFORM]:
                    member = bundle.getmember(name)
                    if not member.isfile() or not 0 < member.size <= MAX_FILE:
                        raise ValueError("Arquivo inválido no pacote: " + name)
                    target = stage / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.extractfile(member) as src, target.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
            (stage / "bin/quiklight").chmod(0o755)
        manifest = json.loads((stage / "gui/update-version.json").read_text(encoding="utf-8"))
        if manifest["version"] != info["latest"]:
            raise ValueError("Versão informada não corresponde ao conteúdo do pacote.")
        # Syntax check all Python components before stopping the working driver.
        for name in FILES[PLATFORM]:
            if name.endswith((".py", ".pyw")):
                content = (stage / name).read_bytes()
                compile(content, name, "exec")
        (stage / "plan.json").write_text(
            json.dumps({"platform": PLATFORM, "files": list(FILES[PLATFORM]),
                        "version": info["latest"]}), encoding="utf-8")
        archive.unlink()
        return str(stage)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def launch_apply(stage):
    args = [sys.executable, str(Path(__file__).resolve()), "--apply",
            str(stage), str(os.getpid()), str(Path(__file__).resolve().with_name("quiklight_gui.py"))]
    options = {"close_fds": True}
    if PLATFORM == "windows":
        options["creationflags"] = NOWIN | 0x00000008
    subprocess.Popen(args, **options)


def _run(args, timeout):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          creationflags=NOWIN if PLATFORM == "windows" else 0)


def _alive(pid):
    if PLATFORM == "windows":
        try:
            p = _run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], 3)
            return str(pid) in p.stdout and "python" in p.stdout.lower()
        except (OSError, subprocess.TimeoutExpired):
            return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _stop_backend():
    if PLATFORM == "windows":
        _run(["taskkill", "/IM", "quiklight.exe", "/F"], 5)
        time.sleep(0.3)
        exe = Path(os.environ["LOCALAPPDATA"]) / "Quiklight/quiklight.exe"
        if exe.is_file():
            result = _run([str(exe), "--off"], 9)
            if result.returncode != 0:
                raise RuntimeError("Não foi possível apagar a fita: " + (result.stderr or "")[-250:])
        return True
    active = _run(["systemctl", "--user", "is-active", "quiklight.service"], 4)
    running = active.stdout.strip() in ("active", "activating")
    if running:
        result = _run(["systemctl", "--user", "stop", "quiklight.service"], 12)
        if result.returncode != 0:
            raise RuntimeError("Não foi possível parar o serviço existente.")
    return running


def _restart_backend(running):
    if PLATFORM == "linux" and running:
        result = _run(["systemctl", "--user", "start", "quiklight.service"], 12)
        if result.returncode != 0:
            raise RuntimeError("Não foi possível reiniciar o serviço existente.")


def _targets(gui_file):
    if PLATFORM == "windows":
        root = Path(os.environ["LOCALAPPDATA"]) / "Quiklight"
        return {"bin/quiklight.exe": root / "quiklight.exe",
                **{name: root / name for name in COMMON + ("gui/quiklight_windows.pyw",)}}
    # Bazzite installs the service binary in ~/.local/bin and GUI in ~/quiklight-gui.
    # Do not touch the existing systemd unit, XDG desktop entry or udev rules.
    return {"bin/quiklight": Path.home() / ".local/bin/quiklight",
            **{name: gui_file.parent / Path(name).name for name in COMMON}}


def _migrate_windows_autostart(gui_folder):
    if PLATFORM != "windows":
        return
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                            winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            try:
                winreg.QueryValueEx(key, "QuiklightWindows")
            except FileNotFoundError:
                return  # Do not enable autostart when user disabled it.
            python = Path(sys.executable)
            pythonw = python.with_name("pythonw.exe")
            if pythonw.is_file():
                python = pythonw
            command = subprocess.list2cmdline(
                [str(python), str(gui_folder / "quiklight_windows.pyw"), "--tray"])
            winreg.SetValueEx(key, "QuiklightWindows", 0, winreg.REG_SZ, command)
    except OSError:
        pass


def _restart_gui(gui):
    if PLATFORM == "windows":
        python = Path(sys.executable)
        pythonw = python.with_name("pythonw.exe")
        if pythonw.is_file():
            python = pythonw
        subprocess.Popen([str(python), str(gui.with_name("quiklight_windows.pyw")), "--tray"],
                         close_fds=True, creationflags=NOWIN | 0x00000008)
    else:
        subprocess.Popen([sys.executable, str(gui), "--tray"], close_fds=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)


def apply_stage(path, old_gui):
    stage = Path(path).resolve()
    old_gui = Path(old_gui).resolve()
    plan = json.loads((stage / "plan.json").read_text(encoding="utf-8"))
    if plan.get("platform") != PLATFORM or plan.get("files") != list(FILES[PLATFORM]):
        raise ValueError("Pacote incompatível com este sistema.")
    targets = _targets(old_gui)
    backup = update_root() / ("backup-" + time.strftime("%Y%m%d-%H%M%S"))
    backup.mkdir(parents=True, exist_ok=False)
    originals, deployed = {}, []
    was_running = False
    new_gui = targets["gui/quiklight_gui.py"]
    try:
        was_running = _stop_backend()
        for name, dest in targets.items():
            source = stage / name
            if not source.is_file():
                raise ValueError("Arquivo obrigatório não encontrado: " + name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                old = backup / name
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, old)
                originals[name] = old
            temp = dest.with_name(dest.name + ".quiklight-new")
            shutil.copy2(source, temp)
            if PLATFORM == "linux" and name == "bin/quiklight":
                temp.chmod(0o755)
            os.replace(temp, dest)
            deployed.append((name, dest))
        _migrate_windows_autostart(new_gui.parent)
        _restart_backend(was_running)
    except Exception:
        for name, dest in reversed(deployed):
            try:
                if name in originals:
                    shutil.copy2(originals[name], dest)
                else:
                    dest.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            _restart_backend(was_running)
        except Exception:
            pass
        _restart_gui(old_gui)
        raise
    else:
        _restart_gui(new_gui)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main():
    if len(sys.argv) != 5 or sys.argv[1] != "--apply":
        raise SystemExit("Usage: quiklight_updates.py --apply STAGE PID GUI")
    _, _, stage, pid, gui = sys.argv
    try:
        deadline = time.monotonic() + 12
        while _alive(int(pid)) and time.monotonic() < deadline:
            time.sleep(0.2)
        if _alive(int(pid)):
            raise RuntimeError("A interface anterior ainda está em execução.")
        apply_stage(stage, gui)
    except Exception as exc:
        (update_root() / "last-update-error.txt").write_text(
            str(exc)[:1600], encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
