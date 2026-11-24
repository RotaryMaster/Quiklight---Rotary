#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/Projetos/quiklight-glass-teste/Stage02-v0.5.9.4-area-amostragem"
F="$ROOT/gui/full_ui.py"
B="$HOME/.local/share/quiklight-integration-backups/p04-$(date +%Y%m%d-%H%M%S)-$$"
test -f "$F"
python3 - "$F" <<'PY'
import os,sys
from pathlib import Path
f=Path(sys.argv[1]).resolve()
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
        if p.stat().st_uid!=os.getuid() or int(p.name)==os.getpid():continue
        a=(p/'cmdline').read_bytes().split(b'\0')
        if not a or not Path(os.fsdecode(a[0])).name.startswith('python'):continue
        r=a[1:]
        while r and r[0] in (b'-u',b'-B',b'-E',b'-s',b'-S',b'-I',b'-O',b'-OO'):r=r[1:]
        if r and r[0] not in (b'-',b'-c',b'-m') and Path(os.fsdecode(r[0])).resolve()==f:
            sys.exit('ERRO: Stage02 em execucao PID '+p.name+'; saia pelo tray.')
    except (OSError,ValueError):pass
PY
mkdir -p "$B"
cp -a "$F" "$B/full_ui.py"
sha256sum "$HOME/.local/bin/quiklight" "$HOME/.local/share/quiklight-rust/config.toml" > "$B/before.sha256"
python3 - "$F" "$B" <<'PY'
import ast,sys,hashlib
from pathlib import Path
f,b=map(Path,sys.argv[1:]);s=f.read_text()
if hashlib.sha256(f.read_bytes()).hexdigest()!='99f64ed8889c9f0a030b2177e9c6c39037a8d648f875309c216d8de9f639dffe':
    sys.exit('ERRO: fonte diferente da auditoria P04; nenhuma alteracao.')
def rep(a,c):
    global s
    if s.count(a)!=1:sys.exit('ERRO: ancora P04: '+a[:120])
    s=s.replace(a,c,1)
# Global mode synchronization without rebuilding unrelated editors.
rep("        if self.local.get(key)!=value:\n            self.local[key]=value\n", """        if self.local.get(key)!=value:
            self.local[key]=value
            if key=='mode':
                combo=getattr(self,'_p04_global_mode',None)
                if combo is not None:
                    old=combo.blockSignals(True)
                    try: combo.setCurrentIndex(combo.findData(value))
                    finally: combo.blockSignals(old)
""")
rep("        _p03_mode = _p03_modes[0]", "        _p03_mode = _p03_modes[0]\n        self._p04_global_mode = _p03_mode")
# Hex fields only activate on actual edits; never on focus loss without changes.
rep("            for k,v in zip(keys,(int(s[i:i+2],16) for i in (1,3,5))):self.set_local(k,v)\n            sync()", """            values=tuple(int(s[i:i+2],16) for i in (1,3,5))
            changed=any(self.local.get(k)!=v for k,v in zip(keys,values))
            for k,v in zip(keys,values):self.set_local(k,v)
            if changed and tuple(keys)==('static_r','static_g','static_b'):
                self.set_local('mode','static')
            sync()""")
rep("        self._color_hex(static,'Cor estática',('static_r','static_g','static_b'))", """        self._color_hex(static,'Cor estática',('static_r','static_g','static_b'))
        activate_static=btn('Usar cor estática','Chip')
        activate_static.clicked.connect(lambda _=False:self.set_local('mode','static'))
        static.addWidget(activate_static)""")
rep("        self._check(palette,'Completar vazios com cores aleatórias','palette_random')", """        self._check(palette,'Completar vazios com cores aleatórias','palette_random')
        activate_palette=btn('Usar paleta como modo de iluminação','Chip')
        activate_palette.clicked.connect(lambda _=False:self.set_local('mode','palette'))
        palette.addWidget(activate_palette)""")
# Individual strip mode selector refresh, without resetting other fields.
rep("        w.currentIndexChanged.connect(lambda ix:self._strip_set(device,key,w.itemData(ix)) if ix>=0 else None)", """        if key=='lighting_mode':
            self._p04_strip_modes[device]=w
        if key=='effect':
            def activate(ix):
                if ix<0 or w.itemData(ix) is None:return
                self._strip_set(device,'effect',w.itemData(ix))
                self._p04_strip_mode(device,'effect')
            w.activated.connect(activate)
        else:
            w.currentIndexChanged.connect(lambda ix:self._strip_set(device,key,w.itemData(ix)) if ix>=0 else None)""")
rep("        strip_sync_start=len(self.syncers)", "        self._p04_strip_modes={}\n        strip_sync_start=len(self.syncers)")
rep("    def _strip_checkbox(self,lay,device,key,text,default=False):", """    def _p04_strip_mode(self,device,mode):
        p=self._strip_profile(device)
        if p is None:return
        self._strip_set(device,'lighting_mode',mode)
        w=getattr(self,'_p04_strip_modes',{}).get(device)
        if w is not None:
            old=w.blockSignals(True)
            try:w.setCurrentIndex(w.findData(mode))
            finally:w.blockSignals(old)

    def _strip_checkbox(self,lay,device,key,text,default=False):""")
rep("            for key,pos in [('static_r',1),('static_g',3),('static_b',5)]:\n                self._strip_set(device,key,int(value[pos:pos+2],16))\n            refresh()", """            values={key:int(value[pos:pos+2],16) for key,pos in [('static_r',1),('static_g',3),('static_b',5)]}
            profile=self._strip_profile(device) or {}
            changed=any(profile.get(k)!=v for k,v in values.items())
            for key,v in values.items():self._strip_set(device,key,v)
            if changed:self._p04_strip_mode(device,'static')
            refresh()""")
rep("            self._strip_rgb(inside,d)", """            self._strip_rgb(inside,d)
            use_static=btn('Usar cor estática nesta fita','Chip')
            use_static.clicked.connect(lambda _=False,dev=d:self._p04_strip_mode(dev,'static'))
            inside.addWidget(use_static)""")
rep("            self._strip_palette(inside,d)", """            self._strip_palette(inside,d)
            use_palette=btn('Usar paleta nesta fita','Chip')
            use_palette.clicked.connect(lambda _=False,dev=d:self._p04_strip_mode(dev,'palette'))
            inside.addWidget(use_palette)""")
# Segment mode updates operate on the existing model, with blocked UI signals.
# Do not touch source_mode, enabled, physical offsets, or other segments.
rep("        self._segment_expand_buttons = {}", "        self._segment_expand_buttons = {}\n        self._p04_segment_modes={}")
rep("        w.currentIndexChanged.connect(changed)\n\n    def _segment_num", """        if key=='lighting_mode':
            self._p04_segment_modes[i]=w
        if key in ('effect','music_style'):
            def activate(ix):
                if ix<0 or w.itemData(ix) is None:return
                changed(ix)
                self._p04_segment_mode(i,'effect' if key=='effect' else 'music')
            w.activated.connect(activate)
        else:
            w.currentIndexChanged.connect(changed)

    def _p04_segment_mode(self,i,mode):
        if not 0<=i<len(self.segments):return
        g=self.segments[i]
        if not g.get('enabled',True) or g.get('source_mode','independent')!='independent':
            self.status_message('Modo local não ativado: trecho desligado ou espelhado.')
            return
        self.segment_set(i,'lighting_mode',mode)
        w=getattr(self,'_p04_segment_modes',{}).get(i)
        if w is not None:
            old=w.blockSignals(True)
            try:w.setCurrentIndex(w.findData(mode))
            finally:w.blockSignals(old)

    def _segment_num""")
rep("            for key,index in [('static_r',1),('static_g',3),('static_b',5)]:\n                self.segment_set(i,key,int(val[index:index+2],16))", """            values={key:int(val[index:index+2],16) for key,index in [('static_r',1),('static_g',3),('static_b',5)]}
            changed=any(self.segments[i].get(k)!=v for k,v in values.items())
            for key,v in values.items():self.segment_set(i,key,v)
            if changed:self._p04_segment_mode(i,'static')""")
rep("            self._segment_rgb(adv,i,'Cor estática do trecho')", """            self._segment_rgb(adv,i,'Cor estática do trecho')
            use_static=btn('Usar cor estática neste trecho','Chip')
            use_static.clicked.connect(lambda _=False,j=i:self._p04_segment_mode(j,'static'))
            adv.addWidget(use_static)""")
rep("            self._segment_palette(adv,i)", """            self._segment_palette(adv,i)
            use_palette=btn('Usar paleta neste trecho','Chip')
            use_palette.clicked.connect(lambda _=False,j=i:self._p04_segment_mode(j,'palette'))
            adv.addWidget(use_palette)""")
# CPU rollback helper created by consolidation; no new driver switching logic.
rep("                row.addWidget(b);self.versions_box.addLayout(row)", """                row.addWidget(b);self.versions_box.addLayout(row)
        helper=Path.home()/'.local/share/quiklight-cpu-versions/p01/switch.sh'
        if not IS_WIN and not self.visual_demo and helper.is_file():
            for target,title in [('v28','Rollback CPU: v28 original'),('p01','Restaurar CPU: v28 P01 otimizada')]:
                button=btn(title,'Chip')
                button.clicked.connect(lambda _=False,t=target:self.confirm(
                    'Trocar somente o driver CPU? As fitas reiniciarão; configurações preservadas.',
                    lambda:self._p04_cpu_switch(t)))
                self.versions_box.addWidget(button)

    def _p04_cpu_switch(self,target):
        from PySide6.QtCore import QProcess
        if getattr(self,'_p04_cpu_process',None) is not None:
            return self.status_message('Troca de driver em andamento.')
        helper=Path.home()/'.local/share/quiklight-cpu-versions/p01/switch.sh'
        proc=QProcess(self)
        self._p04_cpu_process=proc
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        def done(code,status):
            output=bytes(proc.readAllStandardOutput()).decode('utf-8','replace')
            self._p04_cpu_process=None
            proc.deleteLater()
            self.status_message(('Driver trocado. ' if code==0 and status==QProcess.ExitStatus.NormalExit else 'Falha na troca. ')+output[-1200:])
        def failed(error):
            if error==QProcess.ProcessError.FailedToStart:
                self._p04_cpu_process=None
                proc.deleteLater()
                self.status_message('Não foi possível iniciar o helper de rollback.')
        proc.finished.connect(done)
        proc.errorOccurred.connect(failed)
        proc.start('/usr/bin/bash',[str(helper),target])""")
ast.parse(s);compile(s,str(f),'exec');(b/'candidate.py').write_text(s)
print('P04: ancoras e sintaxe Python OK')
PY
cat > "$B/rollback.sh" <<'RB'
#!/usr/bin/env bash
set -eu
D=$(cd -- "$(dirname -- "$0")" && pwd)
F="$HOME/Projetos/quiklight-glass-teste/Stage02-v0.5.9.4-area-amostragem/gui/full_ui.py"
cp -a "$D/full_ui.py" "$F.rollback.tmp"
mv -f "$F.rollback.tmp" "$F"
echo 'P03.1 restaurada. Feche e reabra a GUI.'
RB
cp -a "$F" "$F.p04.tmp"
cat "$B/candidate.py" > "$F.p04.tmp"
mv -f "$F.p04.tmp" "$F"
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
echo "P04_INSTALADA_TESTE_PENDENTE | rollback: bash '$B/rollback.sh'"
