#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/Projetos/quiklight-glass-teste/Stage02-v0.5.9.4-area-amostragem"
F="$ROOT/gui/full_ui.py"
B="$HOME/.local/share/quiklight-integration-backups/p05-$(date +%Y%m%d-%H%M%S)-$$"
test -f "$F"
mkdir -p "$B"
cp -a "$F" "$B/full_ui.py"
sha256sum "$HOME/.local/bin/quiklight" "$HOME/.local/share/quiklight-rust/config.toml" > "$B/before.sha256"
python3 - "$F" "$B" <<'PY'
import ast,sys
from pathlib import Path
f,b=map(Path,sys.argv[1:]);s=f.read_text()
if 'QL_P05_PALETTE' in s:sys.exit('P05 ja aplicada.')
a="""            self.palette_edit.append(edit)
            grid.addWidget(row,i//2,i%2)"""
if s.count(a)!=1:sys.exit('ERRO: ancora da paleta nao encontrada.')
s=s.replace(a,"""            self.palette_edit.append(edit)
            # QL_P05_PALETTE: one painted hue bar, no animation or polling.
            from PySide6.QtWidgets import QColorDialog
            from PySide6.QtGui import QLinearGradient
            class PaletteHueBar(QWidget):
                def __init__(bar,parent=None):
                    super().__init__(parent)
                    bar.hue=0
                    bar.setFixedHeight(20)
                    bar.setToolTip('Clique ou arraste para escolher o tom; use Cor para saturação e luminosidade.')
                def paintEvent(bar,event):
                    painter=QPainter(bar)
                    gradient=QLinearGradient(0,0,max(1,bar.width()-1),0)
                    for h in range(0,361,60):
                        gradient.setColorAt(h/360,QColor.fromHsv(h%360,255,255))
                    painter.fillRect(bar.rect(),gradient)
                    x=round(bar.hue/359*max(1,bar.width()-1))
                    painter.setPen(QPen(QColor('white'),2))
                    painter.drawLine(x,0,x,bar.height()-1)
                def choose(bar,event):
                    bar.hue=max(0,min(359,round(event.position().x()/max(1,bar.width()-1)*359)))
                    bar.update()
                def mousePressEvent(bar,event):
                    if event.button()==Qt.MouseButton.LeftButton:bar.choose(event)
                def mouseMoveEvent(bar,event):
                    if event.buttons() & Qt.MouseButton.LeftButton:bar.choose(event)
                def mouseReleaseEvent(bar,event):
                    if event.button()==Qt.MouseButton.LeftButton:
                        bar.choose(event)
                        bar.commit(QColor.fromHsv(bar.hue,255,255).name().upper())
                def wheelEvent(bar,event):event.ignore()
            bar=PaletteHueBar()
            bar.commit=lambda color,idx=i:self._set_palette(idx,color)
            def choose_color(_=False,idx=i,e=edit):
                initial=QColor(e.text())
                color=QColorDialog.getColor(initial if initial.isValid() else QColor('white'),self,'Selecionar cor da paleta')
                if color.isValid():self._set_palette(idx,color.name().upper())
            picker=btn('Cor…','Chip')
            picker.clicked.connect(choose_color)
            hl.insertWidget(hl.count()-1,picker)
            cell=QWidget()
            cell_layout=vbox(cell,(0,0,0,0),3)
            cell_layout.addWidget(row)
            cell_layout.addWidget(bar)
            if not hasattr(self,'_p05_palette_bars'):self._p05_palette_bars=[]
            self._p05_palette_bars.append(bar)
            grid.addWidget(cell,i//2,i%2)""")
# Update visual selection from the model without emitting configuration changes.
a="""                edit.blockSignals(True);edit.setText(str((self.local.get('palette') or ['']*10)[i]));edit.blockSignals(False)"""
if s.count(a)!=1:sys.exit('ERRO: ancora de sincronizacao nao encontrada.')
s=s.replace(a,"""                colors=list(self.local.get('palette') or [])
                value=str(colors[i]) if i<len(colors) else ''
                edit.blockSignals(True);edit.setText(value);edit.blockSignals(False)
                color=QColor(value)
                bar=self._p05_palette_bars[i]
                if color.isValid() and color.hsvHue()>=0:bar.hue=color.hsvHue()
                bar.update()""")
# Initialize registry on page construction, including rebuilds.
a="        self.palette_edit=[]"
if s.count(a)!=1:sys.exit('ERRO: registro da paleta ambiguo.')
s=s.replace(a,a+"\n        self._p05_palette_bars=[]")
# Existing palette setter is preserved; ensure visual fields sync after explicit selection.
s=s.replace("bar.commit=lambda color,idx=i:self._set_palette(idx,color)","bar.commit=lambda color,idx=i:self._set_palette(idx,color)")
ast.parse(s);compile(s,str(f),'exec');(b/'candidate.py').write_text(s)
print('P05: sintaxe e ancoras OK')
PY
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -eu
D=$(cd -- "$(dirname -- "$0")" && pwd)
F="$HOME/Projetos/quiklight-glass-teste/Stage02-v0.5.9.4-area-amostragem/gui/full_ui.py"
cp -a "$D/full_ui.py" "$F.rollback.tmp"
mv -f "$F.rollback.tmp" "$F"
echo 'GUI anterior restaurada; feche e reabra a interface.'
RB
python3 - "$F" <<'PY'
import os,sys,signal,time
from pathlib import Path
target=Path(sys.argv[1]).resolve()
pids=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if p.stat().st_uid!=os.getuid():continue
        a=(p/'cmdline').read_bytes().split(b'\0')
        if not a or not Path(os.fsdecode(a[0])).name.startswith('python'):continue
        r=a[1:]
        while r and r[0] in (b'-u',b'-B',b'-E',b'-s',b'-S',b'-I',b'-O',b'-OO'):r=r[1:]
        if r and r[0] not in (b'-',b'-c',b'-m') and Path(os.fsdecode(r[0])).resolve()==target:
            print('Encerrando GUI PID',p.name);os.kill(int(p.name),signal.SIGTERM);pids.append(p)
    except (OSError,ValueError):pass
for _ in range(30):
    if all(not p.exists() or (p/'stat').read_text().rsplit(')',1)[1].strip().startswith('Z') for p in pids):break
    time.sleep(.1)
else:sys.exit('GUI ainda ativa; nenhuma alteracao aplicada.')
PY
cp -a "$F" "$F.p05.tmp"
cat "$B/candidate.py" > "$F.p05.tmp"
mv -f "$F.p05.tmp" "$F"
trap 'r=$?; bash "$B/rollback.sh"; exit "$r"' ERR
sha256sum -c "$B/before.sha256"
nohup bash "$ROOT/iniciar-linux.sh" > "$B/launch.log" 2>&1 </dev/null &
P=$!
sleep 4
cat "$B/launch.log"
kill -0 "$P"
sha256sum -c "$B/before.sha256"
systemctl --user show quiklight -p ActiveState -p MainPID
trap - ERR
echo "P05_INSTALADA_TESTE_PENDENTE | rollback: bash '$B/rollback.sh'"
