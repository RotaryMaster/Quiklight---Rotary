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
