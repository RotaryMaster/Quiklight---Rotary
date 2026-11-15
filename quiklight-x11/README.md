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


## Inicialização automática no Windows
Após instalar Python/PySide6 e copiar `quiklight.exe` para `%LOCALAPPDATA%\\Quiklight`:

```powershell
.\\windows\\setup-startup.ps1 -Mode Install
```

O script registra `pythonw.exe gui\\quiklight_windows.pyw --tray` na chave **HKCU Run**.
Não exige administrador; inicia somente **após o login do usuário**, não
antes do login. O serviço Rust é iniciado pela interface e esta fica oculta
na bandeja. Remover com `-Mode Remove`; verificar com `-Mode Status`.

## Encerramento e apagamento dos LEDs
No Windows, a GUI solicita `stop` em `commitDataRequest` (encerramento de
sessão normal). O backend também sinaliza `STOP` para eventos de
desligamento/fechamento da console, tentando enviar três quadros pretos.
A rotina `--off` continua disponível como fallback.
**Limitação:** não é possível garantir o apagamento de um dispositivo USB em
corte abrupto de energia, encerramento forçado ou se o dispositivo USB
desaparecer antes da transmissão. Verificar em reinício e desligamento reais.

## Presets e privacidade
`scripts/export-public-presets.py` é executado **localmente no Bazzite**,
gera arquivos sob `~/Downloads/quiklight-presets-publicos/` e não faz upload.
Remove nomes originais e qualquer campo que não seja um parâmetro visual
permitido. Após revisão, presets aprovados podem ser colocados na pasta
`gui/presets-default` do repositório. A interface importa somente chaves
visuais válidas e mantém configurações de hardware, monitor e LED da máquina
de destino; nunca substitui presets que já existam.

## Desempenho
Nenhuma redução de FPS, qualidade de cores ou modos de iluminação é realizada.
O meter gráfico de áudio só atualiza a cada 100 ms enquanto a página de Música
está visível, evitando wakeups desnecessários com a GUI minimizada.
O detector espacial adicional mantém a otimização de só executar quando
algum eixo for inconclusivo. Ganhos reais de CPU/GPU ainda exigem medição.
