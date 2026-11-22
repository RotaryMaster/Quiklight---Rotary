# QuikLight MultiStrip / Stage 02 — diagnóstico de 2026-11-21

## Escopo e estado de validação
Registro de diagnóstico **somente leitura** no Bazzite KDE. Não constitui correção aplicada, confirmação da orientação física dos LEDs ou validação Windows. O serviço instalado estava ativo com executável `~/.local/bin/quiklight`; GUI Stage 02 v0.4 aberta separadamente com `--visual-demo`. **Não usar a Stage 02 v0.4 para aplicar edições de segmentos até corrigir o round-trip TOML.**

## Configuração ativa observada
Arquivo: `~/.local/share/quiklight-rust/config.toml`. Duas estruturas `[[strip]]`, cada uma com `physical_leds=65` e `enabled=true`.

| Dispositivo | Segmento | start_led (base 0) | leds | enabled | reverse | source_mode |
|---|---|---:|---:|---|---|---|
| 0 | left | 0 | 17 | true | true | independent |
| 0 | top | 17 | 31 | true | false | independent |
| 0 | right | 48 | 17 | true | false | independent |
| 1 | bottom | 17 | 31 | true | false | independent |
| 1 | left | 0 | 17 | false | false | off |
| 1 | right | 48 | 17 | false | false | off |

A ordem das tabelas no TOML **não** determina os offsets quando `start_led` explícito está presente. A fita 2 usa somente as posições físicas 17–47 para o trecho inferior; 0–16 e 48–64 permanecem reservadas/desativadas. Totais globais: top=31, right=34, bottom=31, left=34 (contagens por borda incluem segmentos desativados; não representam LEDs efetivamente acesos).

Cor ativa observada: `mode=screen`, `color_mode=vivid`, `gain_r=1.0`, `gain_g=0.52`, `gain_b=0.67`. Relato anterior: branco na captura/prévia parecia vermelho; causa ainda **não confirmada**. Esses ganhos podem afetar o balanço, mas não bastam para diagnosticar o sintoma.

## Comparação de snapshots
- `pre-v0351-20261121-175510-784891`: segmento 0/left tinha `reverse=false`; 1/right desativado tinha `source_mode=mirror`.
- Configuração ativa: 0/left `reverse=true`; 1/right desativado `source_mode=off`. A inversão observada no lado esquerdo pode ter relação com a alteração, mas **não está comprovado** se é configuração, código Rust ou direção física.
- `pre-v0345-20261121-145906`: fita 2 tinha os mesmos offsets físicos, porém as tabelas estavam na ordem left, bottom, right. A mudança na ordem de apresentação **não** significa que os LEDs inferiores mudaram de 17 para 0.

## Incompatibilidade identificada na GUI experimental
Código local: `~/Projetos/QuikLight-Figma-Stage02-v0.4/gui/backend_io.py`.
- `config_view()` reconstrói cada segmento retendo somente `device`, `edge`, `leds`, `reverse`, `music`.
- `patch_config()` ao editar segmentos reescreve `[[segment]]` somente com esses cinco campos e pode rejeitar seções desconhecidas depois da primeira tabela. **Risco de perda de `start_led`, `enabled`, `source_mode`, espelhamento, intensidade, modos de iluminação, paleta e controles individuais**, ou de falha de aplicação.
- `full_ui.py` / `LedOutline.paintEvent()` agrega LEDs por borda e desenha pontos genéricos: não representa `device`, `start_led`, `enabled` nem `reverse` fisicamente.
- A interface deve preservar todas as tabelas `[[strip]]`, campos desconhecidos e ordem/offsets físicos, inclusive ao mover segmentos visuais.

## Próximas ações (pendentes, não executadas)
1. Comparar `rust/src/multi_strip.rs`, `config.rs` e `main.rs` de `~/Projetos/QuikLight-MultiStrip-Builds/v0351-rev-ui-diagnostics/` com o executável instalado antes de concluir o significado runtime de `reverse`.
2. Implementar leitura e edição lossless/segura de segmentos e fitas na Stage 02, com testes de round-trip e detecção de conflitos de offsets, sem tocar no TOML ativo.
3. Desenhar prévia separada por fita, posições físicas 0–64, seções desligadas e orientação, distinguindo preview estático de dados QLV3 reais.
4. Diagnosticar esquerda invertida e branco/vermelho com testes reversíveis; preservar snapshots e rollback.
5. Verificar paridade Windows separadamente, sem presumir que o runtime Linux foi validado no Windows.

## Fontes do registro
Saídas locais fornecidas pelo mantenedor em 2026-11-21: leituras TOML com `tomllib`, trechos de `backend_io.py` e `full_ui.py`, estado `systemctl --user show quiklight.service` e busca de fontes Rust. Nenhuma alteração de hardware ou serviço foi efetuada durante estas leituras.


## Atualização: código Rust analisado e Stage 02 v0.5.1 experimental preparado

**Base examinada:** fontes do arquivo `QuikLight-Stage02-v05-FONTES.zip`, diretório `Backend-Rust-v0351/src/`. Não foi demonstrada equivalência binária entre estes fontes e o executável instalado na máquina do usuário.

**Causa lógica da direção:** `capture.rs` usa `let j = if s.reverse { n - 1 - i } else { i };` para amostrar uma borda em ordem inversa. A função `multi_strip::map_output` usa `start_led` como posição física e escreve `out[d][first+i]`, sem uma segunda inversão para segmentos independentes. Portanto, `reverse=true` no lado esquerdo da fita 1 inverte **a amostragem**, não o offset físico. A orientação efetiva ainda depende do cabeamento e será validada apenas com teste em hardware.

**Correções na GUI separada v0.5.1 (ainda não instaladas ou verificadas no Bazzite do mantenedor):**
- `config_view()` agora conserva os campos completos de cada `[[segment]]`; a edição não elimina `start_led`, `enabled`, fontes, intensidade, efeitos, paleta ou campos desconhecidos.
- `patch_config()` reescreve somente linhas de campos editados e preserva tabelas externas, perfis `[[strip]]` e campos não editados. Confere a estrutura TOML após edição, bloqueia perda de campos e valida capacidade física, conflitos, espelhamento e perfis.
- O salvamento de presets globais foi ajustado para incluir `[[strip]]`.
- A GUI apresenta resumo de posições por fita, permite alternar `enabled`/`source_mode` nos segmentos que os contêm e exclui segmentos desligados da prévia **genérica** das bordas.
- Criação automática de trechos e redistribuição genérica ficam desabilitadas para mapeamento físico explícito, até existir um editor de offsets adequado.
- Testes automatizados: **43 passaram, 1 ignorado (Qt indisponível)**. Ainda pendentes execução real da GUI PySide6, validação LED/HID, Windows e teste de equivalência do binário instalado.

**Entrega experimental:** `QuikLight-Stage02-v05.1-MultiStrip-Safe-FONTES.zip` na conversa. O comando `Stage02-v0.5.1/testar-e-abrir-linux.sh` valida sintaxe e testes Python, lê a configuração ativa sem modificá-la e só então abre automaticamente a GUI em `--visual-demo`. Não substitui o backend, não reinicia o serviço nem modifica a base imutável.

**Pendências principais:** testar fisicamente se `reverse=false` corrige a esquerda; diagnóstico da prévia branco/vermelho; prévia QLV3 por dispositivo físico; controles completos de 22 campos por segmento, e compatibilidade Windows testada. **Não publicar como versão estável até a validação física.**


## Atualização 21/11/2026 — Stage 02 v0.5.2 QLV3 experimental

**Defeito confirmado nos fontes da GUI v0.5.1:** `LedOutline.paintEvent()` em `LEDs e fitas` desenhava pontos fixos sem ler frames do serviço. Já a prévia em `Captura` lia `$XDG_RUNTIME_DIR/quiklight-live.bin`, que concatena RGB das fitas e não identifica cada dispositivo. O Rust v0.3.5.1 também publica o formato `$XDG_RUNTIME_DIR/quiklight-live-v3.bin` com cabeçalho `QLV3`, sequência `u64 LE` e, por dispositivo, ID, contagem `u16 LE` e RGB. Ambos os arquivos são produzidos quando há um arquivo recente `quiklight-live.want` (telemetria solicitada).

**Implementação experimental separada v0.5.2**: adiciona `gui/telemetry_live.py` com decodificação validada de QLV3, quadros atualizados em Captura **e** LEDs/Fitas, dois controladores renderizados separadamente por posição física 0–64, amostragem orientada por `reverse`, reserva de LEDs desligados, indicadores de quadro e mensagem de falta de dados. Nenhuma cor é fabricada quando QLV3 está desatualizado. `--visual-demo` impede gravação de configuração e serviços mas **não torna o RGB simulado**: ele é lido do Rust em execução. A UI ativa o pedido de telemetria automaticamente ao abrir uma página de LEDs; arquivo `quiklight-live.want` no runtime do usuário é a única escrita operacional necessária para solicitar os quadros, sem alterar configuração ou serviço.

**Validação pré-instalação:** 53 testes Python (52 aprovados, 1 smoke Qt ignorado por falta de PySide6), sintaxe dos scripts bash e integridade do ZIP. **Ainda não validado visualmente no Bazzite KDE ou com dispositivos físicos.** Também não foi validado no Windows. A prévia mostra o RGB final calculado pelo backend, **não** leitura óptica/medição da luz emitida no hardware.

**Entrega:** `QuikLight-Stage02-v05.2-MultiStrip-QLV3-FONTES.zip` entregue na conversa, SHA256 `f31fe643f211dfbfcbc9def0c2103999ddf9e0fb644df66a18692592365c59bd`. Seu script `testar-e-abrir-linux.sh` valida testes/configuração, remove **apenas ZIPs antigos da família Stage02** presentes em Downloads depois de reconhecer o ZIP atual, e abre a GUI experimental. `iniciar-linux.sh` tem permissão executável e é chamado explicitamente com Bash. Nenhuma alteração foi feita no serviço QuikLight ativo por esta análise.

**Pendências:** teste visual de renderização Qt, confirmação física da direção esquerda (`reverse=true`), verificação da anomalia branco/vermelho, controle completo de perfis na Stage 02 e compatibilidade Windows.


## Atualização — Stage 02 v0.5.3 experimental (fluidez e proteção da roda do mouse)

O mantenedor confirmou no Bazzite KDE que a prévia QLV3 da v0.5.2 recebe cores reais, mas exibe atraso e travamentos. Solicitou também que a roda do mouse **não altere valores das opções**, incluindo listas suspensas, campos numéricos e sliders.

O pacote experimental `QuikLight-Stage02-v05.3-MultiStrip-QLV3-Fluido-FONTES.zip` implementa:
- `live_timer` preciso a cada **70 ms**, versus 350 ms na v0.5.2. O backend v0.3.5.1 continua a produzir QLV3 aproximadamente a cada 100 ms; **polling mais rápido não garante taxa de quadros superior à disponibilizada pelo serviço**.
- `QLV3Watcher` com cache por assinatura (inode, mtime_ns, tamanho), evitando leituras/decodificações quando não há novo frame, invalidação de quadros antigos e redesenho somente quando a sequência muda; pedido de telemetria renovado em 1,5 s.
- Mensagem de taxa de atualização efetiva da **prévia**, não de captura USB ou tela.
- `gui/wheel_guard.py`: filtro global de eventos Qt para `QComboBox`, `QAbstractSpinBox`, `QSlider`, `QDial` e editores internos; redireciona evento de roda para o `QScrollArea` ancestral sem alterar valor. A rolagem na lista suspensa **aberta**, teclado, clique e arraste continuam naturais. Regra vale também para controles herdados da Stage 01.
- Script de teste prefere o ambiente Python existente com PySide6 para executar *também* os testes visuais `offscreen` antes de iniciar a GUI normal, sem alterar a base imutável. Limpeza de ZIPs antigos restrita à família Stage02, após testes aprovados e identificação do ZIP atual.

**Validação local do pacote:** 57 testes descobertos, 52 executados e aprovados, 5 ignorados por falta de PySide6 no ambiente de empacotamento (os ignorados são de Qt). Scripts verificados com `bash -n`, ZIP íntegro, executáveis Linux em modo 0755. SHA256: `0417444af2a9e060ed1b65e9a3968f0ffeaaa6aa30a2b07ad07b295adb3f5ea2`.

**Não instalado nem validado no Bazzite do mantenedor; ainda experimental.** Não modifica serviço ou configuração Rust e não prova paridade Windows.
