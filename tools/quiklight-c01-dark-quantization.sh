#!/usr/bin/env bash
set -Eeuo pipefail
SRC="$HOME/Projetos/QuikLight-MultiStrip-Builds/v28-cpu-p01-b02-20261124-183050-15477/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=981f4a6d18e02100845dfd33e9914d351d93dd67f2013b1aea17698760140ffe
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$HOME/Projetos/QuikLight-MultiStrip-Builds/v28-p01-b02-c01-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/c01-$STAMP"
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-b02"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/output.rs" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); s=p.read_text()
def rep(a,b):
 global s
 if s.count(a)!=1:sys.exit('ERRO: ancora C01: '+a)
 s=s.replace(a,b,1)
rep('                let mut px = [0u8; 3];', '''                let mut px = [0u8; 3];
                // C01: only dark pixels use stable quantization.
                let dark = scaled.get(d).and_then(|v| v.get(i))
                    .is_some_and(|p| p[0].max(p[1]).max(p[2]) <= 24.0)
                    && self.cur[d][i].iter().all(|v| *v <= 24.0);''')
rep('''                    let v = *cur + self.err[d][i][c];
                    let q = v.round().clamp(0.0, 255.0);
                    self.err[d][i][c] = (v - q).clamp(-0.5, 0.5);
                    px[c] = q as u8;''','''                    px[c] = quantize_c01(*cur, &mut self.err[d][i][c], dark);''')
s+='''
fn quantize_c01(cur: f32, err: &mut f32, dark: bool) -> u8 {
    if dark {
        *err = 0.0;
        return cur.round().clamp(0.0, 255.0) as u8;
    }
    let v = cur + *err;
    let q = v.round().clamp(0.0, 255.0);
    *err = (v - q).clamp(-0.5, 0.5);
    q as u8
}

#[cfg(test)]
mod c01_tests {
    use super::*;
    #[test]
    fn dark_fraction_is_constant() {
        let mut stage = Stage::new(&[1], 0.0);
        for _ in 0..120 {
            assert_eq!(stage.step_by_strip(&[vec![[0.0, 1.5, 2.5]]], 1.0/60.0,
                &[100.0], &[100.0]), vec![vec![(0,2,3)]]);
        }
    }
    #[test]
    fn bright_dither_is_preserved() {
        let mut stage = Stage::new(&[1], 0.0);
        let t = [vec![[100.5, 0.0, 0.0]]];
        assert_eq!(stage.step_by_strip(&t, 1.0/60.0, &[100.0], &[100.0])[0][0].0, 101);
        assert_eq!(stage.step_by_strip(&t, 1.0/60.0, &[100.0], &[100.0])[0][0].0, 100);
    }
    #[test]
    fn black_clears_residual() {
        let mut err = 0.49;
        assert_eq!(quantize_c01(0.0, &mut err, true), 0);
        assert_eq!(err, 0.0);
    }
    #[test]
    fn large_change_uses_existing_slew() {
        let mut stage = Stage::new(&[1], 6.5);
        let a = stage.step_by_strip(&[vec![[255.0,0.0,0.0]]], 1.0/60.0,
            &[100.0], &[100.0]);
        assert_eq!(a[0][0].0, 28);
    }
}
'''
p.write_text(s)
PY
diff -u "$SRC/src/output.rs" "$DEST/src/output.rs" || test "$?" -eq 1
distrobox enter dev -- bash -lc "cd '$DEST' && cargo test --locked && cargo build --release --locked"
C="$DEST/target/release/quiklight"
test -x "$C"
sha256sum "$C"
sha256sum "$HOME/.local/share/quiklight-rust/config.toml" > "$B/config.sha256"
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -Eeuo pipefail
B=$(cd -- "$(dirname -- "$0")" && pwd)
BIN="$HOME/.local/bin/quiklight"
echo "981f4a6d18e02100845dfd33e9914d351d93dd67f2013b1aea17698760140ffe  $B/quiklight-b02" | sha256sum -c -
systemctl --user stop quiklight.service
install -m755 "$B/quiklight-b02" "$BIN.c01.rollback"
mv -f "$BIN.c01.rollback" "$BIN"
systemctl --user reset-failed quiklight.service
systemctl --user start quiklight.service
echo 'B02_RESTAURADA'
RB
trap 'r=$?; trap - ERR; bash "$B/rollback.sh"; exit "$r"' ERR
systemctl --user stop quiklight.service
install -m755 "$C" "$BIN.c01.tmp"
mv -f "$BIN.c01.tmp" "$BIN"
systemctl --user reset-failed quiklight.service
MARK=$(date '+%Y-%m-%d %H:%M:%S')
systemctl --user start quiklight.service
OK=0
for ((i=0;i<45;i++)); do
 PID=$(systemctl --user show quiklight.service -p MainPID --value)
 if [[ "$PID" != 0 ]] && systemctl --user is-active --quiet quiklight.service; then
  LOG=$(journalctl --user -u quiklight.service --since "$MARK" "_PID=$PID" --no-pager -o cat)
  if grep -Fq 'B02: quadro RGBx confirmado' <<< "$LOG" && grep -Fq 'Fita 1: HID reconectado e inicializado' <<< "$LOG" && grep -Fq 'Fita 2: HID reconectado e inicializado' <<< "$LOG"; then OK=1; break; fi
 fi
 sleep 1
done
test "$OK" -eq 1
sha256sum -c "$B/config.sha256"
journalctl --user -u quiklight.service --since "$MARK" --no-pager -n 40
trap - ERR
echo "C01_EXPERIMENTAL | rollback: bash '$B/rollback.sh'"
echo "FONTE=$DEST"
