#!/usr/bin/env bash
set -Eeuo pipefail
BASE="$HOME/Projetos/QuikLight-MultiStrip-Builds"
SRC="$BASE/v28-b051-c022-20261128-002626-224270/rust"
BIN="$HOME/.local/bin/quiklight"
OLD=ff4ca3087a7a65f007b59fa2769f700f448794f385231f2c003bd2d0d594d752
STAMP="$(date +%Y%m%d-%H%M%S)-$$"
DEST="$BASE/v28-b051-c03-$STAMP/rust"
B="$HOME/.local/share/quiklight-integration-backups/c03-$STAMP"
echo "=== C03 ADAPTIVE WHITE BALANCE ==="
for f in "$BIN" "$SRC/target/release/quiklight"; do echo "$OLD  $f" | sha256sum -c -; done
pgrep -x kwin_wayland >/dev/null || { echo "Execute no KDE"; exit 1; }
mkdir -p "$DEST" "$B"
cp -a "$BIN" "$B/quiklight-c022"
(cd "$SRC" && tar --exclude=./target --exclude=./.git -cf - .) | (cd "$DEST" && tar -xf -)
python3 - "$DEST/src/multi_strip.rs" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text()
a='''                px.0 = ((px.0 as f32 * gains[0]).round().clamp(0.0, 255.0)) as u8;
                px.1 = ((px.1 as f32 * gains[1]).round().clamp(0.0, 255.0)) as u8;
                px.2 = ((px.2 as f32 * gains[2]).round().clamp(0.0, 255.0)) as u8;'''
b='''                if d == 0 {
                    *px = c03_calibrate(*px, gains);
                } else {
                    px.0 = ((px.0 as f32 * gains[0]).round().clamp(0.0, 255.0)) as u8;
                    px.1 = ((px.1 as f32 * gains[1]).round().clamp(0.0, 255.0)) as u8;
                    px.2 = ((px.2 as f32 * gains[2]).round().clamp(0.0, 255.0)) as u8;
                }'''
if s.count(a)!=1: raise SystemExit("ERRO: ancora C03")
s=s.replace(a,b,1)
s += '''
// C03: preserve uncalibrated near-black chroma on device 0, then
// smoothly restore the user's full white balance by RGB peak 64.
fn c03_calibrate(px: (u8,u8,u8), gains: [f32;3]) -> (u8,u8,u8) {
    let peak = px.0.max(px.1).max(px.2);
    if peak <= 8 { return px; }
    let w = if peak >= 64 { 1.0 } else {
        let t = (peak as f32 - 8.0) / 56.0;
        t*t*(3.0-2.0*t)
    };
    let apply = |v: u8, g: f32| {
        let effective = if w == 1.0 { g } else { 1.0 + (g-1.0)*w };
        ((v as f32 * effective).round().clamp(0.0,255.0)) as u8
    };
    (apply(px.0,gains[0]),apply(px.1,gains[1]),apply(px.2,gains[2]))
}

#[cfg(test)]
mod c03_tests {
    use super::*;
    const G: [f32;3] = [1.0,0.52,0.67];
    #[test]
    fn dark_neutral_and_blue_are_preserved() {
        for p in [(0,0,0),(2,2,2),(3,3,3),(4,5,5),(2,3,8),(8,0,0)] {
            assert_eq!(c03_calibrate(p,G),p);
        }
    }
    #[test]
    fn full_brightness_calibration_is_identical() {
        for p in [(64,64,64),(255,255,255),(100,20,200),(0,0,255)] {
            assert_eq!(c03_calibrate(p,G), (
                (p.0 as f32*G[0]).round() as u8,
                (p.1 as f32*G[1]).round() as u8,
                (p.2 as f32*G[2]).round() as u8));
        }
    }
    #[test]
    fn intermediate_calibration_is_bounded_and_smooth() {
        let mut last = (0u8,0u8,0u8);
        for v in 0u8..=255 {
            let p=c03_calibrate((v,v,v),G);
            assert_eq!(p.0,v);
            assert!(p.1 <= v && p.2 <= v);
            assert!(p.1 >= (v as f32*G[1]).round() as u8);
            assert!(p.2 >= (v as f32*G[2]).round() as u8);
            assert!(p.1.abs_diff(last.1)<=2 && p.2.abs_diff(last.2)<=2);
            last=p;
        }
    }
    #[test]
    fn unity_gains_are_identity() {
        for v in 0u8..=255 {
            let p=(v,v/2,255-v);
            assert_eq!(c03_calibrate(p,[1.0;3]),p);
        }
    }
}
'''
p.write_text(s)
print("C03: ancora validada")
PY
diff -u "$SRC/src/multi_strip.rs" "$DEST/src/multi_strip.rs" || test "$?" -eq 1
cmp "$SRC/src/output.rs" "$DEST/src/output.rs"
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
printf '%s\n' "$MARK" > "$HOME/.local/state/quiklight/c03-start"
sha256sum "$BIN"
echo "C03_INSTALADO_EXPERIMENTAL"
echo "FONTE=$DEST"
echo "Rollback: bash '$B/rollback.sh'"
