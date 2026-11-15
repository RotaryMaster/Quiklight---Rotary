# QuikLight X11 — branch Windows/Linux (em desenvolvimento)

Este diretório separa as fontes que antes estavam embutidas em `instalar-quiklight-v27.sh`. Os módulos de captura para Linux e Windows seguem separados; a lógica de detecção central foi incorporada aos dois, e a varredura bidimensional só é executada quando algum eixo é inconclusivo.

**Estado:** preparação inicial do port Windows. Não existe binário Windows compilado ou validado nesta branch. O áudio WASAPI/CPAL, HID e a captura por `scrap` ainda exigem testes em Windows real. O instalador Linux oficial não foi substituído.

## Build (Windows, preparação)
1. Instale Rust com target `x86_64-pc-windows-msvc` e ferramentas de build C++ do Visual Studio.
2. Na pasta deste projeto, execute `cargo check --target x86_64-pc-windows-msvc`.
3. Após corrigir eventuais erros de compilação, execute `cargo build --release`.
4. Python 3 e PySide6 são necessários para `gui/quiklight_gui.py`. Ainda não há instalador Windows pronto.

O código pode requerer ajustes de dependências antes de compilar. Não o execute em produção como substituto da v29.

## Privacidade
As fontes foram separadas de scripts com caminhos em `$HOME` e as versões atuais foram verificadas quanto a e-mails, caminhos pessoais absolutos e padrões comuns de segredos. O relançamento da interface no Windows foi modificado para não concatenar argumentos em `cmd.exe`. Não publique logs, `config.toml` pessoal, presets ou relatórios reais.

## Origem
Baseada no projeto QuikLight para Linux/X11 de `Kevinsillo/quiklight-x11`, cujo README declara licença MIT, com adaptações de Linux/Wayland e Windows. Verificar o arquivo de licença do upstream antes de uma release distribuível.
