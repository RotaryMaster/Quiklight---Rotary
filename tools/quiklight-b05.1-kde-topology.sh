#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
BIN="$HOME/.local/bin/quiklight"
OLD=d5927a1387b7e1157b6024f59ea5cc22dadb2e153475801bd368e8ee803cd7ca
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-b051-kde-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/b051-$STAMP"
echo "=== B05.1 KDE TOPOLOGY ==="
echo "$OLD  $BIN" | sha256sum -c -
pgrep -x kwin_wayland >/dev/null || { echo "Execute no KDE"; exit 1; }
SRC=""
for d in "$BASE"/v28-b05-kde-*/rust; do
    if [[ -f "$d/target/release/quiklight" ]] && [[ "$(sha256sum "$d/target/release/quiklight" | cut -d' ' -f1)" == "$OLD" ]]; then SRC="$d"; break; fi
done
test -n "$SRC"
echo "BASE=$SRC"
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-b05"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/main.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
s=p.read_text()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit("ERRO: ancora B05.1: "+a)
    s=s.replace(a,b,1)
rep("    let mut b04_fault_logged = false;", """    let mut b04_fault_logged = false;
    #[cfg(unix)]
    let b051_topology_grace = Instant::now();""")
rep("""                    topology_restart_pending = true;
                    eprintln!(
                        "Captura: topologia KDE estabilizada; renovação da sessão programada"
                    );""","""                    // B05.1: consume initial topology settling without
                    // restarting an already live capture. Real failure
                    // recovery remains independent of this grace period.
                    if b051_topology_grace.elapsed() < Duration::from_secs(30)
                        && capturer.as_ref().is_some_and(|c| !c.recovery_needed())
                    {
                        eprintln!("B05.1: topologia inicial KDE estabilizada; captura viva preservada");
                    } else {
                        topology_restart_pending = true;
                        eprintln!(
                            "Captura: topologia KDE estabilizada; renovação da sessão programada"
                        );
                    }""")
p.write_text(s)
print("B05.1: ancoras validadas")
PY
diff -u "$SRC/src/main.rs" "$DEST/src/main.rs" || test "$?" -eq 1
cmp "$SRC/src/capture.rs" "$DEST/src/capture.rs"
cmp "$SRC/src/output.rs" "$DEST/src/output.rs"
distrobox enter dev -- bash -lc "cd '$DEST' && cargo test --locked && cargo build --release --locked"
C="$DEST/target/release/quiklight"
test -x "$C"
echo "$OLD  $BIN" | sha256sum -c -
sha256sum "$HOME/.local/share/quiklight-rust/config.toml" > "$B/config.sha256"
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -Eeuo pipefail
B="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/quiklight"
echo "d5927a1387b7e1157b6024f59ea5cc22dadb2e153475801bd368e8ee803cd7ca  $B/quiklight-b05" | sha256sum -c -
systemctl --user stop quiklight.service
install -m755 "$B/quiklight-b05" "$BIN.b051.rollback"
mv -f "$BIN.b051.rollback" "$BIN"
systemctl --user reset-failed quiklight.service
systemctl --user start quiklight.service
RB
chmod +x "$B/rollback.sh"
trap 'r=$?; trap - ERR; bash "$B/rollback.sh"; exit "$r"' ERR
systemctl --user stop quiklight.service
install -m755 "$C" "$BIN.b051.tmp"
mv -f "$BIN.b051.tmp" "$BIN"
systemctl --user reset-failed quiklight.service
MARK="$(date '+%Y-%m-%d %H:%M:%S')"
systemctl --user start quiklight.service
OK=0
for ((i=0;i<45;i++)); do
 PID="$(systemctl --user show quiklight.service -p MainPID --value)"
 if [[ "$PID" != 0 ]] && systemctl --user is-active --quiet quiklight.service; then
  LOG="$(journalctl --user -u quiklight.service --since "$MARK" "_PID=$PID" --no-pager -o cat)"
  if grep -Fq 'B02: quadro RGBx confirmado' <<< "$LOG" && grep -Fq 'Fita 1: HID reconectado e inicializado' <<< "$LOG" && grep -Fq 'Fita 2: HID reconectado e inicializado' <<< "$LOG"; then OK=1; break; fi
 fi
 sleep 1
done
test "$OK" -eq 1
sha256sum -c "$B/config.sha256"
trap - ERR
mkdir -p "$HOME/.local/state/quiklight"
printf '%s\n' "$MARK" > "$HOME/.local/state/quiklight/b051-start"
sha256sum "$BIN"
echo "B05.1_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
