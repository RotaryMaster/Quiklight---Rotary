#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
SRC="$BASE/v28-p01-b02-c01-b03-20261125-182156-15856/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=f0349f1d74dea505a728a5606bbcb38d9938b83ef8bd3c728b6843e26d3c245f
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-p01-b02-c01-b03-b04-safe-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/b04-safe-$STAMP"
echo "=== B04 PERSISTENT CAPTURE SAFE ==="
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
if ! pgrep -x kwin_wayland >/dev/null; then echo "Execute no KDE"; exit 1; fi
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-b03"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/capture.rs" "$DEST/src/main.rs" <<'PY'
from pathlib import Path
import sys,re
p,m=map(Path,sys.argv[1:])
s=p.read_text(); t=m.read_text()
def replace(s,a,b):
    if s.count(a)!=1: raise SystemExit("ERRO: ancora B04: "+a)
    return s.replace(a,b,1)
# Preserve the existing checks for process death and invalid mode.
a=s.index('pub fn recovery_needed(')
end=s.index('\n    }',a)
body=s[a:end]
if 'self.mode_invalid' not in body or 'self.alive.load' not in body or 'frame_is_stale(' not in body:
    raise SystemExit('ERRO: watchdog inesperado')
# Insert only immediately before the final stale-frame expression.
matches=list(re.finditer(r'(?m)^([ \t]*)frame_is_stale\(.*\)\s*$',body))
if len(matches)!=1: raise SystemExit('ERRO: ancora de freshness')
match=matches[0]
body=body[:match.start()]+match.group(1)+'''if self.mode == Mode::Gamescope {
            return false;
        }
'''+body[match.start():]
s=s[:a]+body+s[end:]
# B02 requires a complete initial frame before returning a Capturer.
# Never enter automatic recovery for Gamescope, including after process EOF.
t=replace(t,'''                && (session_at_start != 2 || Instant::now() >= b03_gaming_retry_at)''','''                && session_at_start != 2''')
# Remove now unreachable B03 stream-stop branch and retry variable.
t=replace(t,'''    #[cfg(unix)]
    let mut b03_gaming_retry_at = Instant::now();
''','')
t=replace(t,'''                if session_at_start == 2 {
                    if let Some(c) = capturer.as_mut() { c.stop_gamescope_stream(); }
                    b03_gaming_retry_at = Instant::now() + Duration::from_secs(120);
                    eprintln!("B03: recuperação Gamescope serializada; intervalo mínimo de 120s");
                }
''','')
# Log dead capture once per outage, outside the hot path.
t=replace(t,'''    let mut capture_rebuild_streak: u32 = 0;''','''    let mut capture_rebuild_streak: u32 = 0;
    #[cfg(unix)]
    let mut b04_fault_logged = false;''')
t=replace(t,'''            let identity = capture::session_identity();''','''            if session_at_start == 2 {
                let failed = capturer.as_ref().is_some_and(|c| c.recovery_needed());
                if failed && !b04_fault_logged {
                    eprintln!("B04: fluxo Gamescope encerrado; recuperação automática bloqueada nesta instância");
                }
                b04_fault_logged = failed;
            }
            let identity = capture::session_identity();''')
p.write_text(s); m.write_text(t)
print('B04: ancoras validadas')
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
echo "f0349f1d74dea505a728a5606bbcb38d9938b83ef8bd3c728b6843e26d3c245f  $B/quiklight-b03" | sha256sum -c -
systemctl --user stop quiklight.service
install -m755 "$B/quiklight-b03" "$BIN.b04.rollback"
mv -f "$BIN.b04.rollback" "$BIN"
systemctl --user reset-failed quiklight.service
systemctl --user start quiklight.service
echo "B03 restaurada: use somente no KDE devido aos crashes conhecidos"
RB
chmod +x "$B/rollback.sh"
trap 'r=$?; trap - ERR; bash "$B/rollback.sh"; exit "$r"' ERR
systemctl --user stop quiklight.service
install -m755 "$C" "$BIN.b04.tmp"
mv -f "$BIN.b04.tmp" "$BIN"
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
date '+%Y-%m-%d %H:%M:%S' > "$HOME/.local/state/quiklight/b04-start"
sha256sum "$BIN"
echo "B04_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
