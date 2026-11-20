#!/usr/bin/env bash
# Emergency restore if Qt GUI is broken. Uses the dated, validated snapshot
# made by install-adaptive-fidelity.sh. No sudo; no Bazzite system changes.
set -Eeuo pipefail
[[ "$(id -u)" != "0" ]] || { echo "Nao execute com sudo." >&2; exit 1; }
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VERSIONS="$DATA_HOME/quiklight-versions"
BIN="$HOME/.local/bin/quiklight"
GUI="$DATA_HOME/quiklight-gui-qt/quiklight_gui.py"
LAUNCHER="$HOME/.local/bin/quiklight-gui"
[[ -f "$BIN" && -f "$GUI" ]] || { echo "Quiklight nao encontrado." >&2; exit 2; }
if ! grep -Eq 'APP_VERSION = "29-adaptive-exp[123]"' "$GUI"; then
  echo "Interface atual nao e uma versao adaptativa experimental. Nada alterado." >&2
  exit 2
fi
shopt -s nullglob
snapshots=( "$VERSIONS"/v*-pre-adaptive-* )
(( ${#snapshots[@]} > 0 )) || { echo "Backup pre-adaptive ausente." >&2; exit 2; }
# Choose the newest backup by modification time, not alphabetic version name.
BACKUP="${snapshots[0]}"
for candidate in "${snapshots[@]:1}"; do
  if [[ "$candidate" -nt "$BACKUP" ]]; then BACKUP="$candidate"; fi
done
[[ -s "$BACKUP/quiklight" && -s "$BACKUP/quiklight_gui.py" ]] || {
  echo "Backup incompleto; nada alterado." >&2; exit 2;
}
echo "Restaurando: $BACKUP"
echo "A configuracao e os presets serao preservados."
ACTIVE=0
if systemctl --user is-active --quiet quiklight.service 2>/dev/null; then ACTIVE=1; fi

# Preserve the experimental binaries too (allow returning to the experiment).
CURRENT_VERSION="$(sed -nE 's/^APP_VERSION[[:space:]]*=[[:space:]]*"([^"]+)".*/\1/p' "$GUI" | head -n 1)"
EXPERIMENT="$(mktemp -d "$VERSIONS/v${CURRENT_VERSION}-pre-emergency-$(date +%Y%m%d-%H%M%S)-XXXX")"
cp -p -- "$BIN" "$EXPERIMENT/quiklight"
cp -p -- "$GUI" "$EXPERIMENT/quiklight_gui.py"
printf '%s\n' "$CURRENT_VERSION" > "$EXPERIMENT/VERSION"

TMP_BIN="$BIN.emergency-restore.$$"
TMP_GUI="$GUI.emergency-restore.$$"
trap 'rm -f "$TMP_BIN" "$TMP_GUI"' EXIT
cp -p -- "$BACKUP/quiklight" "$TMP_BIN"
cp -p -- "$BACKUP/quiklight_gui.py" "$TMP_GUI"
chmod 755 "$TMP_BIN"
mv -f -- "$TMP_BIN" "$BIN"
mv -f -- "$TMP_GUI" "$GUI"
if (( ACTIVE )); then systemctl --user restart quiklight.service; fi

# Old GUI may still be in memory. Close only processes launched from exact GUI path.
PIDS=()
for proc in /proc/[0-9]*; do
  [[ -r "$proc/cmdline" ]] || continue
  pid="${proc##*/}"
  [[ "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
  if tr '\0' '\n' < "$proc/cmdline" | grep -Fxq -- "$GUI"; then
    PIDS+=("$pid")
  fi
done
if (( ${#PIDS[@]} > 0 )); then
  for pid in "${PIDS[@]}"; do kill -TERM "$pid" 2>/dev/null || true; done
  sleep 1
  if [[ -x "$LAUNCHER" ]]; then
    nohup "$LAUNCHER" --tray </dev/null >/dev/null 2>&1 &
  fi
fi
echo "Rollback de arquivos concluido. Configuracao intacta."
echo "Se a GUI nao reabrir sozinha, abra-a pelo menu KDE."
