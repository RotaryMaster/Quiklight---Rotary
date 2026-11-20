#!/usr/bin/env bash
# Experimental QuikLight adaptive fidelity update for Bazzite KDE.
# All changed files are in the current user's home. Never touches rpm-ostree.
set -Eeuo pipefail

if [[ "$(id -u)" == 0 ]]; then
  echo "ERRO: execute como usuario normal, sem sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SOURCE_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd -P)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN="$HOME/.local/bin/quiklight"
GUI="$DATA_HOME/quiklight-gui-qt/quiklight_gui.py"
VERSIONS="$DATA_HOME/quiklight-versions"
CONFIG="$DATA_HOME/quiklight-rust/config.toml"
SRC_GUI="$SOURCE_DIR/gui/quiklight_gui.py"
BUILT="$SOURCE_DIR/target/release/quiklight"
GUI_LAUNCHER="$HOME/.local/bin/quiklight-gui"
TMP_BIN="$BIN.adaptive-install.$$"
TMP_GUI="$GUI.adaptive-install.$$"
BACKUP=""
COMMIT="not-in-git"
CHANGED=0
GUI_WAS_RUNNING=0
SERVICE_WAS_ACTIVE=0
GUI_PIDS=()

cleanup() { rm -f -- "$TMP_BIN" "$TMP_GUI"; }
revert_if_needed() {
  local status=$?
  trap - ERR EXIT
  cleanup
  if (( status != 0 )); then
    echo "Falha na instalacao, codigo $status." >&2
    if (( CHANGED )) && [[ -n "$BACKUP" ]]; then
      echo "Restaurando os arquivos anteriores de: $BACKUP" >&2
      cp -p -- "$BACKUP/quiklight" "$TMP_BIN"
      cp -p -- "$BACKUP/quiklight_gui.py" "$TMP_GUI"
      chmod 755 "$TMP_BIN"
      mv -f -- "$TMP_BIN" "$BIN"
      mv -f -- "$TMP_GUI" "$GUI"
      if (( SERVICE_WAS_ACTIVE )); then
        systemctl --user restart quiklight.service || true
      fi
    fi
  fi
  return "$status"
}
trap revert_if_needed EXIT

if [[ ! -f "$BIN" || ! -f "$GUI" ]]; then
  echo "Instalacao existente nao localizada: $BIN ou $GUI" >&2
  exit 2
fi
if [[ ! -f "$SRC_GUI" || ! -f "$SOURCE_DIR/src/color_fidelity.rs" ]]; then
  echo "Fonte experimental incompleta; nenhuma modificacao efetuada." >&2
  exit 2
fi
command -v cargo >/dev/null 2>&1 || { echo "Cargo ausente; nenhuma modificacao efetuada." >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo "Python3 ausente." >&2; exit 2; }

echo "=== QUIKLIGHT FIDELIDADE ADAPTATIVA ==="
echo "Backend atual: $BIN"
echo "GUI atual: $GUI"
echo "Fontes: $SOURCE_DIR"
echo

if command -v git >/dev/null 2>&1 && git -C "$SOURCE_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
  COMMIT="$(git -C "$SOURCE_DIR" rev-parse --short HEAD)"
fi

echo "=== VERIFICACOES ANTES DE INSTALAR ==="
(
  cd "$SOURCE_DIR"
  python3 -m py_compile "$SRC_GUI"
  cargo test --bin quiklight
  cargo build --release --bin quiklight
)
[[ -s "$BUILT" ]] || { echo "Binario nao foi gerado; nenhuma instalacao." >&2; exit 3; }

mkdir -p -- "$VERSIONS"
CURRENT_VERSION="$(sed -nE 's/^APP_VERSION[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$GUI" | head -n 1)"
CURRENT_VERSION="${CURRENT_VERSION:-anterior}"
CURRENT_VERSION="$(printf '%s' "$CURRENT_VERSION" | tr -cd '[:alnum:]._-')"
BACKUP="$(mktemp -d "$VERSIONS/v${CURRENT_VERSION}-pre-adaptive-$(date +%Y%m%d-%H%M%S)-XXXX")"
cp -p -- "$BIN" "$BACKUP/quiklight"
cp -p -- "$GUI" "$BACKUP/quiklight_gui.py"
printf '%s\n' "$CURRENT_VERSION-antes-da-fidelidade-adaptativa" > "$BACKUP/VERSION"
if [[ -f "$CONFIG" ]]; then cp -p -- "$CONFIG" "$BACKUP/config.toml"; fi
cmp -s -- "$BIN" "$BACKUP/quiklight"
cmp -s -- "$GUI" "$BACKUP/quiklight_gui.py"
echo "Backup reconhecivel pelo rollback: $BACKUP"

# Only stop the GUI that is using the exact installed Python script path.
for proc in /proc/[0-9]*; do
  [[ -r "$proc/cmdline" ]] || continue
  pid="${proc##*/}"
  [[ "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
  if tr '\0' '\n' < "$proc/cmdline" | grep -Fxq -- "$GUI"; then
    GUI_PIDS+=("$pid")
  fi
done
if (( ${#GUI_PIDS[@]} > 0 )); then GUI_WAS_RUNNING=1; fi
if systemctl --user is-active --quiet quiklight.service 2>/dev/null; then
  SERVICE_WAS_ACTIVE=1
fi

echo "=== INSTALACAO (SOMENTE ARQUIVOS DO USUARIO) ==="
# Atomic rename works even if the old executable is still mapped by Linux.
install -m 755 -- "$BUILT" "$TMP_BIN"
install -m 644 -- "$SRC_GUI" "$TMP_GUI"
CHANGED=1
mv -f -- "$TMP_BIN" "$BIN"
mv -f -- "$TMP_GUI" "$GUI"
cmp -s -- "$SRC_GUI" "$GUI"

if (( SERVICE_WAS_ACTIVE )); then
  echo "Reiniciando quiklight.service do usuario..."
  systemctl --user restart quiklight.service
  systemctl --user is-active --quiet quiklight.service
else
  echo "Servico estava parado; nao sera ligado automaticamente."
fi

if (( GUI_WAS_RUNNING )); then
  echo "Reabrindo interface com o controle experimental..."
  for pid in "${GUI_PIDS[@]}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for _ in $(seq 1 15); do
    live=0
    for pid in "${GUI_PIDS[@]}"; do
      if kill -0 "$pid" 2>/dev/null; then live=1; fi
    done
    (( live == 0 )) && break
    sleep 0.2
  done
  if [[ -x "$GUI_LAUNCHER" ]]; then
    nohup "$GUI_LAUNCHER" --tray </dev/null >/dev/null 2>&1 &
    echo "GUI iniciada usando launcher existente."
  else
    echo "Abra a GUI pelo menu de aplicativos KDE (launcher nao localizado)."
  fi
fi

CHANGED=0
echo
echo "=== INSTALACAO CONCLUIDA ==="
echo "Nova GUI: 29-adaptive-exp1 ($COMMIT)"
echo "Backup anterior: $BACKUP"
echo "Iluminacao e cores > Acuracia de cores > Ativar fidelidade adaptativa."
echo "Por padrao DESLIGADA. Ao ligar, primeiro teste intensidade 60%."
echo "Rollback disponivel em Sistema > Versoes e rollback."
echo "Calibracao RGB e config.toml existente preservados."
