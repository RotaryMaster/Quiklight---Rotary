#!/usr/bin/env bash
set -Eeuo pipefail
BIN="$HOME/.local/bin/quiklight"
C="$HOME/Projetos/QuikLight-MultiStrip-Builds/v28-cpu-p01-b02-20261124-183050-15477/rust/target/release/quiklight"
B="$HOME/.local/share/quiklight-integration-backups/boot-b02-20261124-183050-15477"
OLD=0f5bff7f08f2e24c560dde4a256bb1a678fe6e899cfe9dd848ee49de333eb381
NEW=981f4a6d18e02100845dfd33e9914d351d93dd67f2013b1aea17698760140ffe
for f in "$BIN" "$B/quiklight-p01"; do echo "$OLD  $f" | sha256sum -c -; done
echo "$NEW  $C" | sha256sum -c -
systemctl --user is-active --quiet quiklight.service
sha256sum "$HOME/.local/share/quiklight-rust/config.toml" "$HOME/.config/systemd/user/quiklight.service" "$HOME/.config/systemd/user/quiklight.service.d/50-sessao-v28.conf" > "$B/install-preserved.sha256"
cat > "$B/rollback-b02.sh" <<'RB'
#!/usr/bin/env bash
set -Eeuo pipefail
B=$(cd -- "$(dirname -- "$0")" && pwd)
BIN="$HOME/.local/bin/quiklight"
echo "0f5bff7f08f2e24c560dde4a256bb1a678fe6e899cfe9dd848ee49de333eb381  $B/quiklight-p01" | sha256sum -c -
systemctl --user stop quiklight.service
install -m 755 "$B/quiklight-p01" "$BIN.rollback.tmp"
mv -f "$BIN.rollback.tmp" "$BIN"
systemctl --user reset-failed quiklight.service
systemctl --user start quiklight.service
echo 'P01_RESTAURADA; B01 preservada'
RB
chmod u+x "$B/rollback-b02.sh"
trap 'r=$?; trap - ERR; echo "Falha na instalacao; restaurando P01"; bash "$B/rollback-b02.sh"; exit "$r"' ERR
systemctl --user stop quiklight.service
install -m 755 "$C" "$BIN.b02.tmp"
mv -f "$BIN.b02.tmp" "$BIN"
systemctl --user reset-failed quiklight.service
MARK=$(date '+%Y-%m-%d %H:%M:%S')
systemctl --user start quiklight.service
echo '=== VALIDACAO DO PRIMEIRO QUADRO E HID ==='
OK=0
for ((i=0;i<45;i++)); do
  PID=$(systemctl --user show quiklight.service -p MainPID --value)
  if [[ "$PID" != 0 ]] && systemctl --user is-active --quiet quiklight.service; then
    LOG=$(journalctl --user -u quiklight.service --since "$MARK" "_PID=$PID" --no-pager -o cat)
    if grep -Fq 'B02: quadro RGBx confirmado' <<< "$LOG" && grep -Fq 'Fita 1: HID reconectado e inicializado' <<< "$LOG" && grep -Fq 'Fita 2: HID reconectado e inicializado' <<< "$LOG"; then OK=1; break; fi
  fi
  sleep 1
done
journalctl --user -u quiklight.service --since "$MARK" --no-pager -n 80
test "$OK" -eq 1
sha256sum -c "$B/install-preserved.sha256"
echo "$NEW  $BIN" | sha256sum -c -
systemctl --user show quiklight.service -p ActiveState -p MainPID -p NRestarts -p Result
trap - ERR
echo "B02_INSTALADA_EXPERIMENTAL | rollback: bash '$B/rollback-b02.sh'"
