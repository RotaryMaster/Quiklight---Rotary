#!/usr/bin/env bash
# corrigir-sessao-gamescope-v28.sh  (v28)
# Corrige a troca KDE <-> Gamescope do Quiklight:
#   * a captura do KDE esperava até 300 s pelo portal sem perceber que o KDE já tinha saído (trava);
#   * o guarda de troca de sessão só existia depois da captura criada e a reconstrução em segundo plano
#     podia "adotar" o outro compositor no mesmo processo, sem reiniciar;
#   * o systemd tinha 5 drop-ins empilhados e apontava para um binário de teste.
# O que este script faz: copia o código atual para uma pasta nova (o original não é tocado), aplica a
# correção, compila no distrobox, instala o binário em ~/.local/bin/quiklight, troca os drop-ins por UM
# só (backup dos antigos) e reinicia o serviço.
#
# Uso:   bash corrigir-sessao-gamescope-v28.sh            (acha o código sozinho)
#        bash corrigir-sessao-gamescope-v28.sh /caminho/do/rust
set -euo pipefail
V=28
UNIT_DIR="$HOME/.config/systemd/user"
BIN="$HOME/.local/bin"
TS="$(date +%Y%m%d-%H%M%S)"

say() { echo; echo "==> $*"; }

say "1/6 Localizando o código-fonte atual"
SRC="${1:-}"
if [ -z "$SRC" ]; then
  EXEC="$(systemctl --user show -p ExecStart --value quiklight 2>/dev/null | sed -n 's/.*path=\([^ ;]*\).*/\1/p' | head -1 || true)"
  case "$EXEC" in */rust/target/release/quiklight) SRC="${EXEC%/target/release/quiklight}" ;; esac
fi
[ -z "$SRC" ] && [ -f "$HOME/quiklight-x11/src/main.rs" ] && SRC="$HOME/quiklight-x11"
if [ -z "$SRC" ] || [ ! -f "$SRC/src/main.rs" ] || ! grep -q "session_changed" "$SRC/src/main.rs"; then
  echo "Não achei o código do Quiklight. Passe o caminho da pasta que tem Cargo.toml e src/:"
  echo "  bash corrigir-sessao-gamescope-v28.sh /caminho/do/rust"
  exit 1
fi
echo "    código: $SRC"
if [ "$(basename "$SRC")" = "rust" ]; then BUILDS="$(dirname "$(dirname "$SRC")")"; else BUILDS="$HOME/Projetos/QuikLight-MultiStrip-Builds"; fi
DEST="$BUILDS/v0352-sessao-estavel-v28/rust"
mkdir -p "$DEST"
rm -rf "$DEST/src"
( cd "$SRC" && tar cf - --exclude=./target --exclude=./.git . ) | ( cd "$DEST" && tar xf - )
echo "    cópia de trabalho: $DEST"

say "2/6 Aplicando a correção (capture.rs e main.rs)"
PATCH="$(mktemp --suffix=_patch_sessao_v28.py)"
cat > "$PATCH" <<'EOF_PATCH'
#!/usr/bin/env python3
# patch_sessao_v28.py — aplica a correção de troca KDE <-> Gamescope no código Rust do Quiklight (v28)
import sys, pathlib
root = pathlib.Path(sys.argv[1])
cap = (root / "src" / "capture.rs"); mn = (root / "src" / "main.rs")
c = cap.read_text(encoding="utf-8"); m = mn.read_text(encoding="utf-8")

def rep(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"ERRO: trecho '{label}' encontrado {n} vez(es) (esperado 1). O código mudou; nada foi alterado.")
    return text.replace(old, new)

# ---------- capture.rs ----------
# 1) detect_mode ignora processos zumbis (kwin/gamescope que já morreram mas ainda aparecem em /proc)
c = rep(c, '''        if comm.starts_with("kwin_wayland") {
            return Some(Mode::Desktop);
        }
        if comm.starts_with("gamescope") {
            gamescope = true;
        }''', '''        if comm.starts_with("kwin_wayland") && !is_zombie(&entry.path()) {
            return Some(Mode::Desktop);
        }
        if comm.starts_with("gamescope") && !is_zombie(&entry.path()) {
            gamescope = true;
        }''', "detect_mode")
c = rep(c, '''/// Descobre em qual ambiente estamos olhando os processos em execução.''', '''/// Processo que já morreu mas ainda não foi recolhido (estado Z em /proc/<pid>/stat).
fn is_zombie(pid_dir: &std::path::Path) -> bool {
    std::fs::read_to_string(pid_dir.join("stat"))
        .ok()
        .and_then(|s| s.rsplit(')').next().map(|t| t.trim_start().starts_with('Z')))
        .unwrap_or(false)
}

/// Descobre em qual ambiente estamos olhando os processos em execução.''', "is_zombie")
# 2) assinatura da sessão (0 = nenhum compositor, 1 = KDE, 2 = gamescope)
c = rep(c, '''/// KScreen só pertence a uma sessão KDE realmente ativa.''', '''/// Compositor ativo agora: 0 = nenhum, 1 = KDE, 2 = gamescope (ignora processos zumbis).
pub fn session_signature() -> u8 {
    match detect_mode() {
        None => 0,
        Some(Mode::Desktop) => 1,
        Some(Mode::Gamescope) => 2,
    }
}

/// KScreen só pertence a uma sessão KDE realmente ativa.''', "session_signature")
# 3) espera pelo portal: confere a cada 0,5 s se o KDE ainda existe (antes ficava até 300 s às cegas)
c = rep(c, '''                let info = rx
                    .recv_timeout(Duration::from_secs(300))
                    .map_err(|_| {
                        anyhow!("Tempo esgotado esperando a permissão de captura de tela")
                    })?
                    .map_err(|e| anyhow!("Falha no portal de captura: {e}"))?;''', '''                let waited = Instant::now();
                let info = loop {
                    match rx.recv_timeout(Duration::from_millis(500)) {
                        Ok(r) => break r.map_err(|e| anyhow!("Falha no portal de captura: {e}"))?,
                        Err(mpsc::RecvTimeoutError::Timeout) => {
                            if detect_mode() != Some(Mode::Desktop) {
                                let _ = stop_tx.send(());
                                bail!("O KDE saiu enquanto esperava a permissão de captura; o serviço será reiniciado");
                            }
                            if waited.elapsed() > Duration::from_secs(300) {
                                bail!("Tempo esgotado esperando a permissão de captura de tela");
                            }
                        }
                        Err(mpsc::RecvTimeoutError::Disconnected) => {
                            bail!("Falha no portal de captura: canal encerrado")
                        }
                    }
                };''', "espera do portal")
# 4) compositor para o qual a captura foi criada
c = rep(c, '''    pub fn session_changed(&self) -> bool {
        detect_mode().is_some_and(|m| m != self.mode)
    }
''', '''    pub fn session_changed(&self) -> bool {
        detect_mode().is_some_and(|m| m != self.mode)
    }

    /// Compositor (1 = KDE, 2 = gamescope) para o qual esta captura foi criada.
    pub fn session_sig(&self) -> u8 {
        match self.mode {
            Mode::Desktop => 1,
            Mode::Gamescope => 2,
        }
    }
''', "session_sig")

# ---------- main.rs ----------
# 5) guarda de sessão independente da captura (vale também antes/durante reconstruções)
m = rep(m, '''    #[cfg(unix)]
    let mut last_session_check = Instant::now();
''', '''    #[cfg(unix)]
    let mut last_session_check = Instant::now();
    // Compositor em que este processo nasceu. Se ele trocar (KDE <-> gamescope) ou sumir,
    // apagamos as fitas e saímos com erro: o systemd recria tudo já na sessão nova.
    #[cfg(unix)]
    let session_at_start: u8 = capturer
        .as_ref()
        .map(|c| c.session_sig())
        .unwrap_or_else(capture::session_signature);
    #[cfg(unix)]
    let mut session_gone_since: Option<Instant> = None;
    #[cfg(unix)]
    eprintln!(
        "Sessão ao iniciar: compositor={} WAYLAND_DISPLAY={:?} XDG_CURRENT_DESKTOP={:?} DISPLAY={:?}",
        match session_at_start {
            1 => "KDE",
            2 => "gamescope",
            _ => "nenhum",
        },
        std::env::var("WAYLAND_DISPLAY").ok(),
        std::env::var("XDG_CURRENT_DESKTOP").ok(),
        std::env::var("DISPLAY").ok()
    );
''', "session_at_start")
old_guard = '''        #[cfg(unix)]
        if needs_capture && last_session_check.elapsed() >= Duration::from_secs(2) {
            last_session_check = Instant::now();

            if capturer
                .as_ref()
                .is_some_and(|capture| capture.session_changed())
            {
                eprintln!(
                    "Sessão KDE/Gamescope mudou; encerrando para reinício completo pelo systemd"
                );

                return Err(anyhow!(
                    "ambiente KDE/Gamescope mudou; reinício completo necessário"
                ));
            }
        }
'''
new_guard = '''        #[cfg(unix)]
        if needs_capture
            && session_at_start != 0
            && last_session_check.elapsed() >= Duration::from_secs(1)
        {
            last_session_check = Instant::now();
            let now_sig = capture::session_signature();
            let changed = now_sig != 0 && now_sig != session_at_start;
            let gone = if now_sig == 0 {
                session_gone_since
                    .get_or_insert_with(Instant::now)
                    .elapsed()
                    >= Duration::from_secs(3)
            } else {
                session_gone_since = None;
                false
            };
            if changed || gone {
                eprintln!(
                    "Sessão KDE/Gamescope mudou ({}); apagando as fitas e encerrando para reinício completo pelo systemd",
                    if changed { "outro compositor" } else { "o compositor encerrou" }
                );
                blackout(&mut workers, &counts);
                return Err(anyhow!(
                    "ambiente KDE/Gamescope mudou; reinício completo necessário"
                ));
            }
        }
'''
m = rep(m, old_guard, new_guard, "guarda de sessão")
# 6) a reconstrução em segundo plano nunca começa/vale durante uma troca de compositor
m = rep(m, '''                && (topology_restart_pending
                    || capturer.as_ref().is_some_and(|c| c.recovery_needed()))
            {''', '''                && (topology_restart_pending
                    || capturer.as_ref().is_some_and(|c| c.recovery_needed()))
                && capture::session_signature() == session_at_start
            {''', "gatilho da reconstrução")
m = rep(m, '''                    Ok(Ok(new_capture)) => {
                        capturer = Some(new_capture); // Drop frees previous portal + GStreamer.''', '''                    Ok(Ok(new_capture)) if new_capture.session_sig() != session_at_start => {
                        // Pertence a outro compositor: não adota; o guarda de sessão reinicia o serviço
                        capture_recovery = None;
                        capture_retry_at = Instant::now() + Duration::from_secs(2);
                        eprintln!("Captura: a nova sessão é de outro compositor; descartada");
                        drop(new_capture);
                    }
                    Ok(Ok(new_capture)) => {
                        capturer = Some(new_capture); // Drop frees previous portal + GStreamer.''', "adoção da nova captura")

cap.write_text(c, encoding="utf-8"); mn.write_text(m, encoding="utf-8")
print("OK: correção v28 aplicada em capture.rs e main.rs")
EOF_PATCH
python3 "$PATCH" "$DEST"
rm -f "$PATCH"

say "3/6 Compilando (no distrobox 'dev'; a primeira vez demora alguns minutos)"
if ! distrobox list 2>/dev/null | awk -F'|' '{gsub(/ /,"",$2); print $2}' | grep -qx dev; then
  distrobox create --name dev --image fedora:latest --yes
fi
distrobox enter dev -- bash -lc "
  set -e
  command -v cargo >/dev/null || sudo dnf install -y git gcc cargo pkgconf-pkg-config dbus-devel libxkbcommon-devel wayland-devel mesa-libEGL-devel mesa-libGL-devel
  cd '$DEST' && cargo build --release
"
[ -x "$DEST/target/release/quiklight" ] || { echo "A compilação não gerou o binário. Rode de novo e envie a mensagem de erro."; exit 1; }

say "4/6 Instalando o binário e o ajudante de espera da sessão"
mkdir -p "$BIN"
systemctl --user stop quiklight 2>/dev/null || true
[ -f "$BIN/quiklight" ] && cp -f "$BIN/quiklight" "$BIN/quiklight.bak-v$V-$TS"
install -m 0755 "$DEST/target/release/quiklight" "$BIN/quiklight"
cat > "$BIN/quiklight-wait-session-v28" <<'EOF_WAIT'
#!/usr/bin/env bash
# quiklight-wait-session-v28 — espera existir um compositor VIVO (KDE ou gamescope) por 2 s seguidos.
# Ignora processos zumbis (kwin que acabou de morrer no logout do KDE).
alive() {
  local p s
  for p in $(pgrep "$1" 2>/dev/null); do
    s="$(awk '/^State:/{print $2}' "/proc/$p/status" 2>/dev/null)"
    [ -n "$s" ] && [ "$s" != "Z" ] && return 0
  done
  return 1
}
up() { alive '^kwin_wayland' || alive '^gamescope'; }
while true; do
  if up; then sleep 2; up && exit 0; fi
  sleep 0.5
done
EOF_WAIT
chmod +x "$BIN/quiklight-wait-session-v28"

say "5/6 Trocando os drop-ins do systemd por um só (backup dos antigos)"
if [ -d "$UNIT_DIR/quiklight.service.d" ]; then
  mv "$UNIT_DIR/quiklight.service.d" "$UNIT_DIR/quiklight.service.d.bak-v$V-$TS"
  echo "    backup: $UNIT_DIR/quiklight.service.d.bak-v$V-$TS"
fi
mkdir -p "$UNIT_DIR/quiklight.service.d"
cat > "$UNIT_DIR/quiklight.service.d/50-sessao-v28.conf" <<'EOF_DROPIN'
# quiklight-sessao v28 — troca KDE <-> Gamescope
# O processo apaga as fitas e sai com erro quando o compositor muda ou some; o systemd o recria
# (Restart=on-failure) e o ajudante espera o compositor novo estar vivo antes de iniciar.
[Unit]
After=
StartLimitIntervalSec=120
StartLimitBurst=60

[Service]
ExecStartPre=
ExecStartPre=%h/.local/bin/quiklight-wait-session-v28
ExecStart=
ExecStart=%h/.local/bin/quiklight
ExecStopPost=
TimeoutStartSec=180s
Restart=on-failure
RestartSec=1s
EOF_DROPIN
systemctl --user daemon-reload
systemctl --user reset-failed quiklight 2>/dev/null || true
systemctl --user enable quiklight 2>/dev/null || true

say "6/6 Iniciando o serviço"
systemctl --user restart quiklight
sleep 6
{
  echo "=== quiklight v$V — status ==="
  systemctl --user status quiklight --no-pager -n 0 | head -8
  echo; echo "=== últimas linhas do registro ==="
  journalctl --user -u quiklight -n 25 --no-pager
} 2>&1 | { if command -v wl-copy >/dev/null 2>&1; then tee >(wl-copy); else cat; fi; }

echo
echo "Pronto (v$V). O resumo acima já foi copiado para a área de transferência (wl-copy)."
echo
echo "TESTE:  1) KDE -> Modo Gaming   2) Modo Gaming -> KDE   (as fitas devem voltar sozinhas nas duas)."
echo "Depois, para me enviar o registro da troca (copia automaticamente):"
echo "  journalctl --user -u quiklight -n 150 --no-pager 2>&1 | grep -v 'XKB\|xkbcomp\|keysym\|Compose' | tee >(wl-copy)"
echo
echo "Para voltar ao estado anterior:"
echo "  rm -rf $UNIT_DIR/quiklight.service.d && mv $UNIT_DIR/quiklight.service.d.bak-v$V-$TS $UNIT_DIR/quiklight.service.d"
echo "  systemctl --user daemon-reload && systemctl --user restart quiklight"
