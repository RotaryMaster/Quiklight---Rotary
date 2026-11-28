#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
SRC="$BASE/v28-b051-c022-20261128-002626-224270/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=ff4ca3087a7a65f007b59fa2769f700f448794f385231f2c003bd2d0d594d752
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-b051-c023-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/c023-$STAMP"
echo "=== C02.3 RGB ATOMIC STRIP 1 ==="
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
pgrep -x kwin_wayland >/dev/null || { echo "Execute no KDE"; exit 1; }
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-c022"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/output.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit("ERRO: ancora C02.3: "+a)
    s=s.replace(a,b,1)
rep('''                    px[c] = c02_hold(*cur, q, dark, previous);
                }
                row.push((px[0], px[1], px[2]));''','''                    if d == 0 && dark {
                        px[c] = q;
                    } else {
                        px[c] = c02_hold(*cur, q, dark, previous);
                    }
                }
                // C02.3: only the first strip uses atomic RGB retention.
                if d == 0 && dark {
                    px = c023_hold(self.cur[d][i], px, &mut self.c02_last[d][i]);
                }
                row.push((px[0], px[1], px[2]));''')
# A prior color may be retained only if its channel ordering still agrees
# with the new quantized color. A zero channel is never resurrected by hold.
s += '''
fn c023_hold(cur: [f32; 3], q: [u8; 3], previous: &mut [Option<u8>; 3]) -> [u8; 3] {
    let out = match *previous {
        [Some(r), Some(g), Some(b)] => {
            let old = [r,g,b];
            let close = (0..3).all(|c| (cur[c] - old[c] as f32).abs() < 0.75);
            let same_support = (0..3).all(|c| (old[c] == 0) == (q[c] == 0));
            let same_order = (0..3).all(|c| (0..c).all(|k|
                old[c].cmp(&old[k]) == q[c].cmp(&q[k])));
            if close && same_support && same_order { old } else { q }
        }
        _ => q,
    };
    *previous = out.map(Some);
    out
}

#[cfg(test)]
mod c023_tests {
    use super::*;
    #[test]
    fn old_red_not_retained_when_new_color_is_blue() {
        let mut p = [Some(1), Some(0), Some(0)];
        assert_eq!(c023_hold([0.4,0.0,0.6], [0,0,1], &mut p), [0,0,1]);
    }
    #[test]
    fn neutral_color_not_changed_by_old_channel_bias() {
        let mut p = [Some(2),Some(1),Some(1)];
        assert_eq!(c023_hold([1.49,1.49,1.49], [1,1,1], &mut p), [1,1,1]);
    }
    #[test]
    fn joint_hold_keeps_small_same_hue_changes() {
        let mut p = [Some(2),Some(3),Some(5)];
        assert_eq!(c023_hold([2.6,3.2,5.1], [3,3,5], &mut p), [3,3,5]);
        let mut p = [Some(2),Some(4),Some(6)];
        assert_eq!(c023_hold([2.6,4.1,6.1], [3,4,6], &mut p), [2,4,6]);
    }
    #[test]
    fn second_strip_retains_original_c022_behavior() {
        let mut stage = Stage::new(&[1,1], 0.0);
        for n in 0..240 {
            let t = [vec![[0.0,0.0,0.0]], vec![[(n%2) as f32,0.0,0.0]]];
            assert_eq!(stage.step_by_strip(&t, 1.0/60.0, &[100.0;2], &[100.0;2])[1][0], (0,0,0));
        }
    }
}
'''
p.write_text(s)
print("C02.3: ancora validada; fita 2 preservada")
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
echo "ff4ca3087a7a65f007b59fa2769f700f448794f385231f2c003bd2d0d594d752  $B/quiklight-c022" | sha256sum -c -
systemctl --user stop quiklight.service
install -m755 "$B/quiklight-c022" "$BIN.c02.rollback"
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
printf '%s\n' "$MARK" > "$HOME/.local/state/quiklight/c023-start"
sha256sum "$BIN"
echo "C02.3_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
