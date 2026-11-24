#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/Projetos/quiklight-glass-teste/Stage02-v0.5.9.4-area-amostragem"
F="$ROOT/gui/full_ui.py"
B="$HOME/.local/share/quiklight-integration-backups/p03-$(date +%Y%m%d-%H%M%S)-$$"
[[ -f "$F" && -f "$ROOT/iniciar-linux.sh" ]] || { echo 'ERRO: caminho Stage02 nao encontrado'; exit 1; }
python3 - "$F" <<'PY'
import sys,os
from pathlib import Path
f=Path(sys.argv[1]).resolve()
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
        if p.stat().st_uid != os.getuid() or int(p.name)==os.getpid(): continue
        args=(p/'cmdline').read_bytes().split(b'\0')
        if len(args)>1 and Path(os.fsdecode(args[0])).name.startswith('python'):
            rest=args[1:]
            while rest and rest[0] in (b'-u',b'-B',b'-E',b'-s',b'-S',b'-I',b'-O',b'-OO'):
                rest=rest[1:]
            if rest and rest[0] not in (b'-',b'-c',b'-m') and Path(os.fsdecode(rest[0])).resolve()==f:
                sys.exit(f'ERRO: GUI em execucao PID {p.name}; saia pelo tray.')
    except (OSError,ValueError): pass
PY
mkdir -p "$B"
cp -a "$F" "$B/full_ui.py"
sha256sum "$HOME/.local/bin/quiklight" "$HOME/.local/share/quiklight-rust/config.toml" > "$B/before.sha256"
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -eu
D=$(cd -- "$(dirname -- "$0")" && pwd)
F="$HOME/Projetos/quiklight-glass-teste/Stage02-v0.5.9.4-area-amostragem/gui/full_ui.py"
cp -a "$D/full_ui.py" "$F.rollback.tmp"
mv -f "$F.rollback.tmp" "$F"
echo 'GUI restaurada. Feche a interface pelo tray e reabra.'
RB
python3 - "$F" "$B" <<'PY'
import ast,sys
from pathlib import Path
f,b=map(Path,sys.argv[1:]); s=f.read_text()
a="        self._combo(mode,'Modo ativo','mode',DYNAMIC+[('static','Cor estática'),('effect','Efeitos')])"
c="        self._combo(effects,'Efeito','effect',EFFECTS)"
if 'QL_P03_EFFECT_ACTIVATION' in s: sys.exit('P03 ja aplicada.')
for x in (a,c):
    if s.count(x)!=1: sys.exit('ERRO: ancora diferente; nenhuma alteracao.')
s=s.replace(a,"""        from PySide6.QtWidgets import QComboBox as _P03Combo
        _p03_before = set(mode_card.findChildren(_P03Combo))
"""+a+"""
        _p03_modes = [w for w in mode_card.findChildren(_P03Combo) if w not in _p03_before and w.findData('effect') >= 0]
        if len(_p03_modes) != 1:
            raise RuntimeError('P03: seletor de modo nao identificado')
        _p03_mode = _p03_modes[0]""")
s=s.replace(c,"""        # QL_P03_EFFECT_ACTIVATION: only explicit user selection.
        _p03_before = set(effects_card.findChildren(_P03Combo))
"""+c+"""
        _p03_effects = [w for w in effects_card.findChildren(_P03Combo) if w not in _p03_before and w.findData('breathing') >= 0]
        if len(_p03_effects) != 1:
            raise RuntimeError('P03: seletor de efeitos nao identificado')
        _p03_effect = _p03_effects[0]
        def _p03_activate_effect(index):
            value = _p03_effect.itemData(index)
            if value not in ('breathing','pulsing','rainbow','fade','comet','aurora','fire'):
                return
            self.set_local('effect', value)
            if self.local.get('mode') != 'effect':
                self.set_local('mode', 'effect')
            if _p03_mode.currentData() != 'effect':
                old = _p03_mode.blockSignals(True)
                try:
                    _p03_mode.setCurrentIndex(_p03_mode.findData('effect'))
                finally:
                    _p03_mode.blockSignals(old)
        _p03_effect.activated.connect(_p03_activate_effect)""")
ast.parse(s); compile(s,str(f),'exec'); (b/'candidate.py').write_text(s)
PY
cp -a "$F" "$F.p03.tmp"
cat "$B/candidate.py" > "$F.p03.tmp"
mv -f "$F.p03.tmp" "$F"
trap 'r=$?; bash "$B/rollback.sh"; exit "$r"' ERR
sha256sum -c "$B/before.sha256"
nohup bash "$ROOT/iniciar-linux.sh" > "$B/launch.log" 2>&1 </dev/null &
P=$!
sleep 4
cat "$B/launch.log"
if ! kill -0 "$P" 2>/dev/null; then echo 'ERRO: launcher encerrou; restaurando GUI.'; false; fi
systemctl --user show quiklight -p ActiveState -p MainPID
trap - ERR
echo "P03_INSTALADA | rollback: bash '$B/rollback.sh'"
echo 'Teste fisico pendente: selecione um efeito sem ativar previamente o modo.'
