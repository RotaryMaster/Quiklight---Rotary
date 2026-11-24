#!/usr/bin/env bash
set -Eeuo pipefail
U="$HOME/.config/systemd/user/quiklight.service"
D="$HOME/.config/systemd/user/quiklight.service.d/50-sessao-v28.conf"
B="$HOME/.local/share/quiklight-integration-backups/boot-b01-$(date +%Y%m%d-%H%M%S)-$$"
test -f "$U"
test -f "$D"
grep -Fxq 'ExecStartPre=%h/.local/bin/quiklight-wait-session-v28' "$D"
test -x "$HOME/.local/bin/quiklight-wait-session-v28"
mkdir -p "$B"
cp -aL "$U" "$B/quiklight.service"
sha256sum "$HOME/.local/bin/quiklight" "$D" "$HOME/.local/share/quiklight-rust/config.toml" > "$B/preserved.sha256"
systemctl --user show quiklight.service -p After -p MainPID -p ActiveState
python3 - "$U" "$B" <<'PY'
import sys
from pathlib import Path
u,b=map(Path,sys.argv[1:])
s=u.read_text()
lines=s.splitlines(keepends=True)
hits=[i for i,l in enumerate(lines) if l.strip()=='After=graphical-session.target']
if len(hits)!=1:sys.exit('ERRO: dependencia original nao encontrada exatamente uma vez.')
del lines[hits[0]]
(b/'candidate.service').write_text(''.join(lines))
PY
diff -u "$B/quiklight.service" "$B/candidate.service" || test "$?" -eq 1
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -eu
B=$(cd -- "$(dirname -- "$0")" && pwd)
U="$HOME/.config/systemd/user/quiklight.service"
T=$(readlink -f "$U")
cp -a "$B/quiklight.service" "$T.rollback.tmp"
mv -f "$T.rollback.tmp" "$T"
systemctl --user daemon-reload
echo 'Unidade original restaurada; servico nao reiniciado.'
RB
T=$(readlink -f "$U")
cp -a "$T" "$T.b01.tmp"
cat "$B/candidate.service" > "$T.b01.tmp"
mv -f "$T.b01.tmp" "$T"
trap 'r=$?; bash "$B/rollback.sh"; exit "$r"' ERR
systemctl --user daemon-reload
AFTER=$(systemctl --user show quiklight.service -p After --value)
echo "After efetivo: $AFTER"
if [[ " $AFTER " == *" graphical-session.target "* ]]; then
    echo 'ERRO: dependencia ainda efetiva'
    false
fi
sha256sum -c "$B/preserved.sha256"
systemctl --user show quiklight.service -p MainPID -p ActiveState -p NRestarts -p Result
trap - ERR
echo "B01_APLICADO_SEM_REINICIAR | rollback: bash '$B/rollback.sh'"
echo 'Validacao de boot pendente. Nenhum servico do Bazzite alterado.'
echo '=== AUDITORIA FOCADA DO WATCHDOG (somente leitura) ==='
S="$HOME/Projetos/QuikLight-MultiStrip-Builds/v28-cpu-p01-20261123-232849-16724/rust/src"
python3 - "$S" <<'PY'
import sys,re
from pathlib import Path
root=Path(sys.argv[1])
for name,patterns in [('capture.rs',r'fn (recovery_needed|stable_for|latest_fresh|grab|new|start|spawn|.*watchdog)|Captura iniciada|não entregou imagem|last_frame|last_check|first_frame|last_good'),('main.rs',r'capture_retry_at|capture_recovery|recovery_needed|stable_for|topology_restart_pending')]:
 p=root/name
 if not p.is_file():
  print('Fonte ausente:',p);continue
 lines=p.read_text().splitlines()
 ix=set()
 for i,l in enumerate(lines):
  if re.search(patterns,l):
   ix.update(range(max(0,i-12),min(len(lines),i+22)))
 print('===',name,'===')
 prev=-2
 for i in sorted(ix):
  if i>prev+1:print('---')
  print(f'{i+1}: {lines[i]}')
  prev=i
PY
