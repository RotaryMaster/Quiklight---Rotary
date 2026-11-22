#!/usr/bin/env python3
"""Stage02 v0.5.4 — diagnóstico seguro de integração Qt/backend.

SOMENTE LEITURA: não importa módulos da GUI, não executa serviço,
não acessa HID, não edita TOML. Mostra apenas parâmetros numéricos
de captura e campos físicos selecionados (sem serial/USB).
"""
import ast
from pathlib import Path
import re
import sys
import tomllib

home=Path.home()
root=home/"Projetos"/"quiklight-glass-teste"/"Stage02-v0.5.4-funcional"
config=home/".local/share/quiklight-rust/config.toml"
targets={
    "_commit":100, "apply_changes":35, "_auto_apply":35,
    "toggle_realtime":30, "_set_realtime":20,
    "update_pending":40, "set_local":65, "segment_set":75,
    "toggle_live":40, "ask_service":50, "service_action":50,
    "refresh_controls":50, "read_config":50,
}
signal=re.compile(r"(?i)(Recorte|Bordas|Tempo real|Aplicar|Ligar|Desligar|"
                  r"auto_crop|crop_speed|cap_w|cap_h|border|inset_|"
                  r"setTracking|sliderReleased|service_cmd|"
                  r"autosave_timer|realtime_chk|self\.original|"
                  r"self\.local|config_path|\.clicked\.connect|\.toggled\.connect)")
private=re.compile(r"(?i)(password|passwd|secret|token|api_key|"
                   r"serial|hidraw|usb_path|device_path|hid_device)")
home_path=re.compile(r"/(?:var/)?home/[^/\s\"']+")
def mask(t):
    return home_path.sub("/home/USUARIO",t)

def inspect(p):
    code=p.read_text("utf-8")
    lines=code.splitlines()
    tree=ast.parse(code,filename=p.name)
    hits=[n for n in ast.walk(tree)
          if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
          and n.name in targets]
    refs=[(i,ln) for i,ln in enumerate(lines) if signal.search(ln)
          and not private.search(ln)]
    if not hits and not refs:
        return
    print(f"\n=== FONTE: {p.relative_to(root)} ({len(lines)} linhas) ===")
    for n in sorted(hits,key=lambda n:n.lineno):
        top=min(n.end_lineno,n.lineno+targets[n.name]-1)
        print(f"\n--- {n.name}: linhas {n.lineno}-{n.end_lineno} ---")
        for idx in range(n.lineno-1,top):
            if not private.search(lines[idx]):
                print(f"{idx+1:4d}: {mask(lines[idx])[:220]}")
        if top<n.end_lineno:
            print(f"... {n.end_lineno-top} linhas omitidas")
    # Mostra referências de controles e campos não exibidos pelos handlers.
    print("\n--- Ligações e campos de interface (amostra) ---")
    scored=[]
    for i,ln in refs:
        weight=sum(word.lower() in ln.lower() for word in
                   ("recorte","bordas","auto_crop","crop_speed",
                    "cap_w","cap_h","inset_","border","tracking",
                    "ligar","desligar","realtime","service_cmd"))
        scored.append((weight,i,ln))
    for _,i,ln in sorted(sorted(scored,key=lambda x:(-x[0],x[1]))[:55],
                         key=lambda x:x[1]):
        print(f"{i+1:4d}: {mask(ln)[:220]}")
    print(f"Referências exibidas: {min(len(refs),55)}/{len(refs)}")

def config_readonly():
    print("\n=== CONFIGURAÇÃO ATIVA: CAMPOS NÃO SENSÍVEIS ===")
    if not config.is_file() or config.is_symlink():
        print("Arquivo regular de configuração não localizado")
        return
    with config.open("rb") as file:
        cfg=tomllib.load(file)
    keys=("auto_crop","crop_speed","border","cap_w","cap_h","fps",
          "capture_limit","inset_left","inset_top","inset_right",
          "inset_bottom","zone_depth","brightness","smoothing",
          "mode","color_mode")
    for k in keys:
        val=cfg.get(k,"AUSENTE")
        if val=="AUSENTE" or isinstance(val,(int,float,bool)) or (
             isinstance(val,str) and k in ("mode","color_mode")):
            print(f"{k}: {val}")
    ss=cfg.get("strip",[])
    segs=cfg.get("segment",[])
    print(f"Fitas: {len(ss)} | Segmentos: {len(segs)}")
    for i,seg in enumerate(segs[:25]):
        if not isinstance(seg,dict):
            continue
        keys=("device","edge","start_led","leds","enabled",
              "source_mode","reverse")
        data=", ".join(f"{k}={seg.get(k,'AUSENTE')}" for k in keys)
        print(f"segmento[{i}]: {data}")
    print("Outros campos, portas USB e identificadores não exibidos.")
    # Compare com snapshot privado criado pelo launcher; nenhum valor sensível.
    backup_dir=home/"Projetos"/"quiklight-glass-teste"/"backups"/"Stage02-v054"
    if backup_dir.is_dir():
        snapshots=[p for p in backup_dir.glob("config-antes-teste-*.toml")
                   if p.is_file() and not p.is_symlink()]
        if snapshots:
            snap=max(snapshots,key=lambda p:p.stat().st_mtime)
            with snap.open("rb") as file:
                before=tomllib.load(file)
            print("\n=== COMPARAÇÃO COM BACKUP PRÉ-TESTE (SOMENTE LEITURA) ===")
            print("Backup:",snap.name)
            for k in keys:
                old,new=before.get(k,"AUSENTE"),cfg.get(k,"AUSENTE")
                if old!=new and all(isinstance(v,(int,float,bool)) or
                                     v=="AUSENTE" or (k in ("mode","color_mode")
                                     and isinstance(v,str)) for v in (old,new)):
                    print(f"ALTERADO {k}: {old} -> {new}")
            oldsegs=before.get("segment",[])
            if oldsegs!=segs:
                print("ALERTA: diferenças em [[segment]] desde o backup pré-teste")
                print(f"Contagens: backup={len(oldsegs)}, atual={len(segs)}")
                for i,(o,n) in enumerate(zip(oldsegs,segs)):
                    for key in ("device","edge","start_led","leds",
                                "enabled","source_mode","reverse"):
                        if o.get(key)!=n.get(key):
                            print(f"segmento[{i}].{key}: "
                                  f"{o.get(key,'AUSENTE')} -> {n.get(key,'AUSENTE')}")
            elif before==cfg:
                print("Backup e configuração ativa têm os mesmos valores TOML.")
        else:
            print("Nenhum backup pré-teste encontrado para comparar.")


def main():
    print("=== QUIKLIGHT STAGE02 — ESTADO REAL DE CONTROLES ===")
    print("Fonte:",mask(str(root)))
    if not root.is_dir():
        print("ERRO: pasta experimental não encontrada")
        return 2
    fulls=[p for p in root.rglob("full_ui.py")
           if p.is_file() and len(p.relative_to(root).parts)<8]
    if len(fulls)!=1:
        print(f"ERRO: esperado 1 full_ui.py; encontrados {len(fulls)}")
        return 3
    stage=fulls[0].parent.parent
    for p in sorted(stage.rglob("*.py")):
        if not p.is_file() or any(x in p.parts for x in
            ("tests","test","__pycache__",".venv")):
            continue
        inspect(p)
    config_readonly()
    print("\nFIM: somente leitura; nenhuma configuração ou serviço alterado.")
    return 0

if __name__=="__main__":
    try:
        sys.exit(main())
    except (OSError,ValueError,SyntaxError,tomllib.TOMLDecodeError) as e:
        print("ERRO:",e,file=sys.stderr)
        sys.exit(4)
