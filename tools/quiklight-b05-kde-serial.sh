#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
SRC="$BASE/v28-p01-b02-c01-b03-b04-safe-20261125-211334-127542/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=b6b53bde323be81aa7149c28b884d2b33153304a8933fd0a3a8019524f49a9fb
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-b05-kde-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/b05-$STAMP"
echo "=== B05 KDE SERIAL ==="
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
pgrep -x kwin_wayland >/dev/null || { echo "Execute no KDE"; exit 1; }
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-b04"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/capture.rs" "$DEST/src/main.rs" <<'PY'
from pathlib import Path
import sys
p,m=map(Path,sys.argv[1:])
s=p.read_text(); t=m.read_text()
def rep(s,a,b):
    if s.count(a)!=1: raise SystemExit("ERRO: ancora B05: "+a)
    return s.replace(a,b,1)
# Only actual EOF / invalidation triggers recovery in a running session.
s=rep(s,'''        let last = self.last_frame_at.lock().ok().and_then(|t| *t);
        if self.mode == Mode::Gamescope {
            return false;
        }
        frame_is_stale(last, self.started, Instant::now())''','''        // B05: an idle source is not a dead consumer.
        false''')
# Replace the background recovery launch with a bounded restart.
a='''                let (tx, rx) = std::sync::mpsc::sync_channel(1);
                let next_cfg = cfg.clone();
                std::thread::spawn(move || {
                    let result = capture::Capturer::new(&next_cfg).map_err(|e| e.to_string());
                    let _ = tx.send(result);
                });
                capture_recovery = Some(rx);
                topology_restart_pending = false;
                eprintln!("Captura: preparando outra sessão em background (HID preservado)");'''
b='''                // B05: never overlap old and new portal sessions during recovery.
                // Bound automatic restarts per compositor instance across processes.
                let runtime = std::env::var_os("XDG_RUNTIME_DIR")
                    .map(std::path::PathBuf::from);
                let identity = capture::session_identity();
                let permitted = if let (Some(dir), Some((1, pid, ticks))) = (runtime, identity) {
                    let path = dir.join(format!("quiklight-b05-kde-{pid}-{ticks}.retry"));
                    let now = std::time::SystemTime::now();
                    let recent = std::fs::metadata(&path).and_then(|m| m.modified())
                        .ok().and_then(|t| now.duration_since(t).ok())
                        .is_some_and(|age| age < Duration::from_secs(120));
                    !recent && std::fs::write(&path, b"restart").is_ok()
                } else { false };
                topology_restart_pending = false;
                if permitted {
                    eprintln!("B05: recuperacao KDE serializada via systemd");
                    blackout(&mut workers, &counts);
                    drop(capturer.take());
                    return Err(anyhow!("B05: renovacao KDE sem sobreposicao de portal"));
                }
                capture_retry_at = Instant::now() + Duration::from_secs(120);
                eprintln!("B05: recuperacao KDE adiada para evitar ciclo de reinicios");'''
t=rep(t,a,b)
# Require the actual current session to be KDE, not the absent-session sentinel.
t=rep(t,'''                && session_at_start != 2
                && (topology_restart_pending''','''                && session_at_start == 1
                && (topology_restart_pending''')
p.write_text(s); m.write_text(t)
print("B05: ancoras validadas")
PY
diff -u "$SRC/src/capture.rs" "$DEST/src/capture.rs" || test "$?" -eq 1
diff -u "$SRC/src/main.rs" "$DEST/src/main.rs" || test "$?" -eq 1
cmp "$SRC/src/output.rs" "$DEST/src/output.rs"
distrobox enter dev -- bash -lc "cd '$DEST' && cargo test --locked && cargo build --release --locked"
C="$DEST/target/release/quiklight"
test -x "$C"
sha256sum "$C"
echo "$OLD  $BIN" | sha256sum -c -
sha256sum "$HOME/.local/share/quiklight-rust/config.toml" > "$B/config.sha256"
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -Eeuo pipefail
B="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin/quiklight"
echo "b6b53bde323be81aa7149c28b884d2b33153304a8933fd0a3a8019524f49a9fb  $B/quiklight-b04" | sha256sum -c -
systemctl --user stop quiklight.service
install -m755 "$B/quiklight-b04" "$BIN.b05.rollback"
mv -f "$BIN.b05.rollback" "$BIN"
systemctl --user reset-failed quiklight.service
systemctl --user start quiklight.service
RB
chmod +x "$B/rollback.sh"
trap 'r=$?; trap - ERR; bash "$B/rollback.sh"; exit "$r"' ERR
systemctl --user stop quiklight.service
install -m755 "$C" "$BIN.b05.tmp"
mv -f "$BIN.b05.tmp" "$BIN"
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
printf '%s\n' "$MARK" > "$HOME/.local/state/quiklight/b05-start"
sha256sum "$BIN"
echo "B05_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
