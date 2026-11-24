#!/usr/bin/env bash
set -Eeuo pipefail
SRC="$HOME/Projetos/QuikLight-MultiStrip-Builds/v28-cpu-p01-20261123-232849-16724/rust"
BIN="$HOME/.local/bin/quiklight"
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$HOME/Projetos/QuikLight-MultiStrip-Builds/v28-cpu-p01-b02-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/boot-b02-$STAMP"
EXPECTED=0f5bff7f08f2e24c560dde4a256bb1a678fe6e899cfe9dd848ee49de333eb381
echo '=== B02: BASE P01 ==='
for f in "$BIN" "$SRC/target/release/quiklight"; do
  echo "$EXPECTED  $f" | sha256sum -c -
done
test -f "$SRC/src/capture.rs"
test -f "$SRC/src/main.rs"
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-p01"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST" <<'PY'
import sys
from pathlib import Path
root=Path(sys.argv[1]); p=root/'src/capture.rs'; s=p.read_text()
def rep(a,b):
 global s
 if s.count(a)!=1:sys.exit('ERRO: ancora B02: '+a[:140])
 s=s.replace(a,b,1)
# Validate the fallback before returning success, with bounded cleanup.
rep('/// Tenta primeiro com limite de quadros (economiza GPU).', '''// B02: a child process alone is not evidence of successful capture.
fn wait_first_rgbx(
    mut child: Child,
    latest: Latest,
    alive: Arc<AtomicBool>,
    last_frame_at: Arc<Mutex<Option<Instant>>>,
) -> Result<(Child, Latest, Arc<AtomicBool>, Arc<Mutex<Option<Instant>>>)> {
    let started = Instant::now();
    loop {
        let last = last_frame_at.lock().ok().and_then(|t| *t);
        if !alive.load(Ordering::SeqCst) {
            break;
        }
        if last.is_some_and(|t| t.elapsed() < Duration::from_secs(2)) {
            return Ok((child, latest, alive, last_frame_at));
        }
        if started.elapsed() >= Duration::from_secs(8) {
            break;
        }
        thread::sleep(Duration::from_millis(100));
    }
    let _ = child.kill();
    let _ = child.wait();
    bail!("B02: GStreamer não entregou quadro RGBx completo dentro do prazo");
}

/// Tenta primeiro com limite de quadros (economiza GPU).''')
rep('        return start_gst(src, fd_raw, cw, ch, fps, false);', '''        let (child, latest, alive, last_frame_at) =
            start_gst(src, fd_raw, cw, ch, fps, false)?;
        return wait_first_rgbx(child, latest, alive, last_frame_at);''')
rep('        if got {\n            eprintln!("Captura limitada', '        if got && alive.load(Ordering::SeqCst) {\n            eprintln!("Captura limitada')
rep('    start_gst(src, fd_raw, cw, ch, fps, false)\n}', '''    let (child, latest, alive, last_frame_at) =
        start_gst(src, fd_raw, cw, ch, fps, false)?;
    wait_first_rgbx(child, latest, alive, last_frame_at)
}''')
# Explicit shutdown on KDE pipeline failure.
rep('                let c = launch_gst(&src, Some(fd_raw), cw, ch, cfg.fps, cfg.capture_limit)?;', '''                let c = match launch_gst(&src, Some(fd_raw), cw, ch, cfg.fps, cfg.capture_limit) {
                    Ok(c) => c,
                    Err(error) => {
                        let _ = stop_tx.send(());
                        return Err(error);
                    }
                };''')
# Track continuity with a cheap timestamp shared by the existing reader thread.
rep('    started: Instant,\n    mode_invalid:', '    started: Instant,\n    healthy_since: Cell<Option<Instant>>,\n    mode_invalid:')
rep('            started: Instant::now(),\n            mode_invalid:', '            started: Instant::now(),\n            healthy_since: Cell::new(None),\n            mode_invalid:')
rep('        self.started.elapsed() >= duration && !self.recovery_needed()', '''        let now = Instant::now();
        if self.recovery_needed() {
            self.healthy_since.set(None);
            return false;
        }
        let last = self.last_frame_at.lock().ok().and_then(|t| *t);
        // Reset continuity on missing or sparse frames; never use pixel equality.
        if !last.is_some_and(|t| now.saturating_duration_since(t) < Duration::from_secs(2)) {
            self.healthy_since.set(None);
            return false;
        }
        let since = self.healthy_since.get().unwrap_or(now);
        self.healthy_since.set(Some(since));
        now.saturating_duration_since(since) >= duration''')
rep('eprintln!("Captura iniciada ({cw}x{ch})");','eprintln!("Captura iniciada ({cw}x{ch}) — B02: quadro RGBx confirmado");')
# Retain 15-second runtime threshold and existing session guard.
p.write_text(s)
m=root/'src/main.rs'; s=m.read_text()
rep('                    Ok(Ok(new_capture)) => {\n                        capturer = Some(new_capture);', '''                    Ok(Ok(new_capture)) if new_capture.recovery_needed() => {
                        capture_recovery = None;
                        capture_failures = capture_failures.saturating_add(1);
                        let secs = (4u64 << capture_failures.min(3)).min(32);
                        capture_retry_at = Instant::now() + Duration::from_secs(secs);
                        eprintln!("B02: nova captura perdeu o fluxo antes da adoção; retry em {secs}s");
                        drop(new_capture);
                    }
                    Ok(Ok(new_capture)) => {
                        capturer = Some(new_capture);''')
# Keep backoff bounded and avoid escalation to a full minute.
rep('let secs = (8u64 << capture_rebuild_streak.min(3)).min(60);','let secs = (4u64 << capture_rebuild_streak.min(3)).min(32);')
rep('let secs = (4u64 << capture_failures.min(4)).min(60);','let secs = (4u64 << capture_failures.min(3)).min(32);')
# Avoid extra stable checks when there is nothing to reset.
rep('            if capturer\n                .as_ref()\n                .is_some_and(|c| c.stable_for(Duration::from_secs(90)))','            if capture_rebuild_streak != 0 && capturer\n                .as_ref()\n                .is_some_and(|c| c.stable_for(Duration::from_secs(90)))')
m.write_text(s)
print('B02: ancoras validadas; P01 e guarda v28 preservados.')
PY
echo '=== DIFF ==='
diff -u "$SRC/src/capture.rs" "$DEST/src/capture.rs" || test "$?" -eq 1
diff -u "$SRC/src/main.rs" "$DEST/src/main.rs" || test "$?" -eq 1
echo '=== COMPILACAO E TESTES ==='
distrobox enter dev -- bash -lc "cd '$DEST' && cargo test --locked && cargo build --release --locked"
test -x "$DEST/target/release/quiklight"
echo '=== CANDIDATO VALIDADO; NAO INSTALADO ==='
sha256sum "$BIN" "$DEST/target/release/quiklight"
echo "CANDIDATO=$DEST/target/release/quiklight"
echo "BACKUP=$B/quiklight-p01"
echo 'B02_BUILD_OK | servico e binario instalado permanecem intactos.'
