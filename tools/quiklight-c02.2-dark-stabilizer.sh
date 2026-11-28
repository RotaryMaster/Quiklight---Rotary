#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
SRC="$BASE/v28-b051-kde-20261126-205007-76824/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=8c1b37784fcf1ca6b851c5e60428436372d94e6462cab1c665b83d946a59a25f
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-b051-c022-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/c022-$STAMP"
echo "=== C02.2 DARK SCENE STABILIZER ==="
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
pgrep -x kwin_wayland >/dev/null || { echo "Execute no KDE"; exit 1; }
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-b051"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
echo "fa9d98902e6268312fbbf5957272d031279667ea90425e0d2c5133f2c0e75de6  $SRC/src/output.rs" | sha256sum -c -
python3 - "$DEST/src/output.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit("ERRO: ancora C02.2: "+a)
    s=s.replace(a,b,1)
rep('    err: Vec<Vec<[f32; 3]>>,','    err: Vec<Vec<[f32; 3]>>,\n    c02_last: Vec<Vec<[Option<u8>; 3]>>,')
rep('            err: counts.iter().map(|&n| vec![[0.0f32; 3]; n]).collect(),','            err: counts.iter().map(|&n| vec![[0.0f32; 3]; n]).collect(),\n            c02_last: counts.iter().map(|&n| vec![[None; 3]; n]).collect(),')
rep('''        let max_delta = if self.slew > 0.0 {
            self.slew * 255.0 * dt
        } else {
            f32::MAX
        };''','''        let max_delta = if self.slew > 0.0 {
            self.slew * 255.0 * dt
        } else {
            f32::MAX
        };
        let c02_alpha = 1.0 - (-dt.max(0.0) / 0.12).exp();''')
rep('''                    *cur += diff.clamp(-max_delta, max_delta);
                    px[c] = quantize_c01(*cur, &mut self.err[d][i][c], dark);''','''                    let previous = &mut self.c02_last[d][i][c];
                    let delta = if dark && previous.is_some() {
                        diff * c02_alpha
                    } else { diff };
                    *cur += delta.clamp(-max_delta, max_delta);
                    let q = quantize_c01(*cur, &mut self.err[d][i][c], dark);
                    px[c] = c02_hold(*cur, q, dark, previous);''')
s += '''
// C02.2: hysteresis on fractional intensity, including the 0/1 boundary.
fn c02_hold(cur: f32, q: u8, dark: bool, previous: &mut Option<u8>) -> u8 {
    if !dark {
        *previous = None;
        return q;
    }
    let out = match *previous {
        Some(old) if (cur - old as f32).abs() < 0.75 => old,
        _ => q,
    };
    *previous = Some(out);
    out
}

#[cfg(test)]
mod c022_tests {
    use super::*;
    #[test]
    fn fractional_boundary_is_stable() {
        let mut p = Some(2);
        for v in [2.49, 2.51, 2.49, 2.51] {
            assert_eq!(c02_hold(v, v.round() as u8, true, &mut p), 2);
        }
    }
    #[test]
    fn near_black_alternation_is_filtered() {
        let mut stage = Stage::new(&[1], 0.0);
        for n in 0..240 {
            let t = [vec![[(n % 2) as f32, 0.0, 0.0]]];
            assert_eq!(stage.step_by_strip(&t, 1.0/60.0, &[100.0], &[100.0])[0][0].0, 0);
        }
    }
    #[test]
    fn sustained_dim_color_and_black_are_reached() {
        let mut stage = Stage::new(&[1], 0.0);
        let mut out = (0,0,0);
        for _ in 0..120 {
            out = stage.step_by_strip(&[vec![[1.0,0.0,0.0]]], 1.0/60.0, &[100.0], &[100.0])[0][0];
        }
        assert_eq!(out, (1,0,0));
        for _ in 0..120 {
            out = stage.step_by_strip(&[vec![[0.0,0.0,0.0]]], 1.0/60.0, &[100.0], &[100.0])[0][0];
        }
        assert_eq!(out, (0,0,0));
    }
    #[test]
    fn bright_transition_uses_original_output() {
        let mut stage = Stage::new(&[1], 0.0);
        stage.step_by_strip(&[vec![[1.0,0.0,0.0]]], 1.0/60.0, &[100.0], &[100.0]);
        assert_eq!(stage.step_by_strip(&[vec![[100.5,0.0,0.0]]], 1.0/60.0, &[100.0], &[100.0])[0][0].0, 101);
    }
}
'''
p.write_text(s)
print("C02.2: todas as ancoras validadas")
PY
diff -u "$SRC/src/output.rs" "$DEST/src/output.rs" || test "$?" -eq 1
cmp "$SRC/src/main.rs" "$DEST/src/main.rs"
cmp "$SRC/src/capture.rs" "$DEST/src/capture.rs"
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
echo "8c1b37784fcf1ca6b851c5e60428436372d94e6462cab1c665b83d946a59a25f  $B/quiklight-b051" | sha256sum -c -
systemctl --user stop quiklight.service
install -m755 "$B/quiklight-b051" "$BIN.c02.rollback"
mv -f "$BIN.c02.rollback" "$BIN"
systemctl --user reset-failed quiklight.service
systemctl --user start quiklight.service
RB
chmod +x "$B/rollback.sh"
trap 'r=$?; trap - ERR; bash "$B/rollback.sh"; exit "$r"' ERR
systemctl --user stop quiklight.service
install -m755 "$C" "$BIN.c02.tmp"
mv -f "$BIN.c02.tmp" "$BIN"
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
printf '%s\n' "$MARK" > "$HOME/.local/state/quiklight/c022-start"
sha256sum "$BIN"
echo "C02.2_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
