#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
SRC="$BASE/v28-b051-kde-20261126-205007-76824/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=8c1b37784fcf1ca6b851c5e60428436372d94e6462cab1c665b83d946a59a25f
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-b051-c02-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/c02-$STAMP"
echo "=== C02 DARK SCENE STABILIZER ==="
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
pgrep -x kwin_wayland >/dev/null || { echo "Execute no KDE"; exit 1; }
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-b051"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/output.rs" <<'PY'
from pathlib import Path
import sys,re
p=Path(sys.argv[1]); s=p.read_text()
def rep(a,b):
    global s
    if s.count(a)!=1: raise SystemExit("ERRO: ancora C02: "+a)
    s=s.replace(a,b,1)
# Preserve Stage initialization and resizing by storing the previous emitted
# dark level in a separate per-pixel state initialized lazily.
rep('    err: Vec<Vec<[f32; 3]>>,','    err: Vec<Vec<[f32; 3]>>,\n    c02_last: Vec<Vec<[Option<u8>; 3]>>,')
# Find Stage constructor's Self literal by its err field, not by guessed shape.
matches=list(re.finditer(r'(?m)^(\s*)err:\s*[^\n]+,\s*$',s))
if len(matches)!=1: raise SystemExit("ERRO: inicializador err ambiguo")
m=matches[0]
s=s[:m.end()]+ '\n'+m.group(1)+'c02_last: Vec::new(),'+s[m.end():]
rep('        let max_delta = if self.slew > 0.0 { self.slew * 255.0 * dt } else { f32::MAX };','''        // Resize only when physical layout changes; no per-frame allocation.
        if self.c02_last.len() != self.cur.len()
            || self.c02_last.iter().zip(&self.cur).any(|(a,b)| a.len() != b.len())
        {
            self.c02_last = self.cur.iter().map(|v| vec![[None; 3]; v.len()]).collect();
        }
        let max_delta = if self.slew > 0.0 { self.slew * 255.0 * dt } else { f32::MAX };''')
rep('                *cur += diff.clamp(-max_delta, max_delta);','''                // Extra filter only when both the target and current pixel
                // are in C01's dark range. Exact black keeps the original fade.
                let delta = if dark && tgt > 0.0 {
                    diff * (1.0 - (-dt.max(0.0) / 0.12).exp())
                } else { diff };
                *cur += delta.clamp(-max_delta, max_delta);''')
rep('                px[c] = quantize_c01(*cur, &mut self.err[d][i][c], dark);','''                let q = quantize_c01(*cur, &mut self.err[d][i][c], dark);
                px[c] = c02_hold(q, tgt, dark, &mut self.c02_last[d][i][c]);''')
s += '''
// C02: a small Schmitt-like deadband in the dark output range.
// Exact zero is not held above black; bright output bypasses this filter.
fn c02_hold(q: u8, target: f32, dark: bool, previous: &mut Option<u8>) -> u8 {
    if !dark {
        *previous = None;
        return q;
    }
    let out = match *previous {
        Some(old) if target > 0.0 && q > 0 && old > 0
            && old.abs_diff(q) < 2 => old,
        _ => q,
    };
    *previous = Some(out);
    out
}

#[cfg(test)]
mod c02_tests {
    use super::c02_hold;
    #[test]
    fn adjacent_dark_levels_do_not_toggle() {
        let mut p = None;
        assert_eq!(c02_hold(2, 2.0, true, &mut p), 2);
        for q in [3, 2, 3, 2] {
            assert_eq!(c02_hold(q, q as f32, true, &mut p), 2);
        }
        assert_eq!(c02_hold(4, 4.0, true, &mut p), 4);
    }
    #[test]
    fn black_and_bright_bypass_deadband() {
        let mut p = Some(2);
        assert_eq!(c02_hold(0, 0.0, true, &mut p), 0);
        assert_eq!(c02_hold(1, 1.0, true, &mut p), 1);
        assert_eq!(c02_hold(120, 120.0, false, &mut p), 120);
        assert_eq!(p, None);
    }
}
'''
p.write_text(s)
print("C02: ancoras validadas")
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
printf '%s\n' "$MARK" > "$HOME/.local/state/quiklight/c02-start"
sha256sum "$BIN"
echo "C02_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
