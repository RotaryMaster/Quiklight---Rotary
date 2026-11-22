# Stage 02 v0.5.4 — Aplicar e Tempo real (trabalho experimental)

**Repositório correto:** \`RotaryMaster/Quiklight---Rotary\`
**Branch:** \`feature/stage02-v054-apply-realtime\`
**Base funcional que NÃO deve ser substituída automaticamente:** serviço Linux QuikLight v0.3.5.1, Bazzite KDE.
**Estado:** diagnóstico e preparação; os controles ainda NÃO foram integrados nesta branch.

## Estado confirmado pelo mantenedor (21/11/2026)

- Stage 02 v0.5.3: 57 testes concluídos com sucesso no ambiente de teste.
- Interface experimental aparentemente estável, prévia QLV3 mais fluida.
- O mantenedor não conseguiu validar os botões **Aplicar** e **Tempo real**.
- O inicializador de testes da série Stage 02 utiliza \`--visual-demo\` para bloquear escrita no TOML e operações sobre o serviço. Precisamos verificar na fonte **exata da v0.5.3** se o bloqueio desses botões é intencional nesse modo ou se há problema adicional de ligação do sinal.
- A prévia QLV3 lê telemetria do serviço e **não é** a mesma coisa que aplicar configurações em tempo real.

## Fonte atual

A branch \`main\` contém histórico, diagnóstico, scripts legados e fontes de branches anteriores, **mas não contém os arquivos completos da GUI Stage 02 v0.5.3**. Não misturar com \`RotaryMaster/Lumasync\`; o LumaSync é um aplicativo independente.

O auditor somente leitura \`tools/auditar-stage02-v053-controles.py\` examina **o ZIP da v0.5.3 no computador do mantenedor**, sem importar/executar o projeto, e mostra os handlers, o modo visual, os sinais Qt e as funções de escrita. As alterações reais dependem desse mapeamento.

## Requisitos obrigatórios para a implementação

1. **Aplicar:** não gravar ou reiniciar nada no modo de demonstração. No modo normal, validar diferenças antes de persistir. Gravar com estratégia atômica e backup, verificar o TOML resultante e preservar \`[[strip]]\`, \`[[segment]]\`, \`start_led\`, \`enabled\`, \`source_mode\`, \`reverse\`, paletas, efeitos e campos desconhecidos. Não usar escrita reconstrutiva de configurações legadas.
2. **Tempo real:** debounce e fila de alterações; impedir execuções concorrentes, diferenciar campos ao vivo de mudanças estruturais e evitar reinicializar o USB a cada ajuste de slider. Em caso de erro, mostrar a falha e deixar alterações pendentes para nova tentativa.
3. **Proteção de hardware:** não aplicar configurações se houver conflito de endereços físicos, capacidade de fita ultrapassada ou corrupção de arquivo. Nunca forçar \`start\` depois de o usuário desligar o serviço. Preservar os drop-ins existentes de KDE/Gamescope, bindings USB e rollback. Bloquear testes destrutivos durante falhas HID.
4. **Interface:** botões precisam mostrar status de aplicado/pendente/erro, sem sinal enganoso de sucesso. Evitar alteração de controles pela roda do mouse, já tratada na v0.5.3.
5. **Preview:** QLV3 continua somente leitura. Não confundir frequência da prévia com taxa do serviço. GUI deve permanecer responsiva.
6. **Windows:** backend de aplicação precisa ter caminho separado e testado, sem chamar \`systemctl\` nessa plataforma.

## Plano de validação

- Inspecionar código exato dos handlers e testes da v0.5.3, sem escrever no sistema.
- Escrever integração e testes novos numa cópia isolada da GUI, sem substituir a instalada.
- Exercitar primeiro com configuração sintética e mocks de serviço.
- Testar com cópia do TOML real, exigir invariância física no round-trip e bloqueio de conflitos.
- Executar os testes de regressão e GUI offscreen existentes antes da primeira execução normal.
- Só então preparar procedimento explícito de ativação + backup + rollback e solicitar validação de hardware.

**Não é uma release estável e não contém ainda uma correção funcional dos botões.**

## Diagnóstico confirmado pela auditoria executada pelo mantenedor

**Fonte exata auditada:** `QuikLight-Stage02-v05.3-MultiStrip-QLV3-Fluido-FONTES.zip` (SHA256: `0417444af2a9e060ed1b65e9a3968f0ffeaaa6aa30a2b07ad07b295adb3f5ea2`).

- `testar-e-abrir-linux.sh:49` executa `iniciar-linux.sh --visual-demo`.
- `gui/full_ui.py:319` determina `self.apply.setEnabled(self.pending and not self.visual_demo)`.
- `gui/full_ui.py:534-537` recusa habilitar Tempo real no modo visual.
- `gui/full_ui.py:551-558` encaminha Aplicar a uma confirmação e `self._commit`.
- `gui/full_ui.py:546-550` contém salvamento automático após debounce; modo visual também o bloqueia.
- `gui/full_ui.py:270,276` conecta os sinais Qt de Aplicar e Tempo real aos handlers.
- `gui/backend_io.py:266-328` implementa patch TOML com preservação e validação de `[[segment]]`.

**Conclusão:** a indisponibilidade dos botões neste ensaio é consequência intencional do argumento `--visual-demo`; a auditoria não comprova falha nos handlers. Não alterar esses bloqueios para o modo visual. Para avaliação funcional, preparar fonte isolada e backup, executar testes e **abrir sem `--visual-demo`**, esclarecendo que cliques em Aplicar ou ativação de Tempo real poderão alterar o serviço e a configuração reais.

**Ainda não comprovado:** segurança do caminho `_commit` herdado, comportamento dos controladores físicos durante aplicação, recuperação de falhas HID e paridade Windows. Não declarar v0.5.4 funcionalmente validada sem teste em hardware.

## Próximo ensaio funcional (ferramenta publicada)

Arquivo: `tools/testar-stage02-v054-funcional.py`.

O lançador valida a identidade SHA256 da v0.5.3, extrai o pacote **somente** para a pasta experimental `~/Projetos/quiklight-glass-teste/Stage02-v0.5.4-funcional`, verifica sintaxe e testes Python, salva um backup privado da configuração física e somente então abre `iniciar-linux.sh` **sem** `--visual-demo`. Não substitui Rust, serviço, GUI instalada, atalhos nem configurações sozinho. Ativar Tempo real ou clicar Aplicar dentro da GUI funcional é uma ação operacional real, com efeito potencial no controlador; primeiro testar parâmetros não estruturais e manter restauração disponível. Nenhum resultado prático desse ensaio foi obtido ainda.

**Importante:** este helper habilita um **ensaio funcional sobre os fontes v0.5.3 existentes**, não implementa novos handlers nem valida o commit da configuração no hardware. A v0.5.4 continua em desenvolvimento.

## Retorno do mantenedor: teste funcional Stage 02 v0.5.4 (21/11/2026)

O script de lançamento v0.5.4 apenas abriu **os fontes existentes da v0.5.3 sem `--visual-demo`**. Não houve integração de novos controles nessa etapa — portanto, o ensaio realmente expôs o comportamento da implementação anterior. Não apresentar o lançador como correção concluída.

**Relato físico:** Aplicar aparentemente funciona; Tempo real não afeta liga/desliga de trechos; a alteração de segmentos só aparece depois de Aplicar. Sliders produzem resposta, mas perceptível somente após soltar o mouse e com atraso. Controles de Recorte/Bordas aparecem zerados, apesar de valores anteriores presumidos. Comandos de ligar/desligar também dependem de Aplicar.

**Análise com base no código já auditado:** `gui/full_ui.py:320` exclui `segment`, `mode`, `fps`, `cap_w`, `cap_h`, `capture_limit` de autoaplicação; `autosave_timer.start(650)` impõe debounce de 650 ms. Portanto, mudança de `enabled`/ `source_mode` dentro de segmento não é aplicada automaticamente. A origem dos zeros em Recorte/Bordas e a efetiva atualização durante slider ainda **não foram confirmadas**, e não devem ser atribuídas a um bug específico antes de comparar bindings Qt, `set_local`, `_commit` e TOML ativo.

**Próxima verificação:** `tools/auditar-stage02-v054-runtime.py` somente lê fontes Qt/backend e parâmetros não sensíveis da configuração ativa, sem executar handlers. O objetivo é determinar com precisão a correção mínima para recuperar Tempo real sem danificar `start_led`, sem reinicialização USB indevida, e sem troca de backend ou regressão Windows.


## Escopo consolidado após segunda rodada de validação: Tempo real, Captura e Música (21/11/2026)

**Relatos do mantenedor, considerados em conjunto:**

1. **Aplicar** parece funcionar; **Tempo real** não aciona alterações em \`[[segment]]\` (on/off de trechos) sem Aplicar.
2. Sliders movimentam o parâmetro na GUI, porém o resultado físico aparece com atraso, sobretudo ao soltar o mouse.
3. **Recorte/Bordas** são mostrados em zero, divergindo dos valores de antes da GUI experimental; ainda não se sabe se é falha de leitura/binding ou se algum TOML foi alterado. **Não sobrescrever esses campos nem salvar enquanto divergirem da configuração física.**
4. **Ligar/Desligar** aparenta depender de Aplicar: serviço e controle de efeitos precisam de comportamento explícito, não de edição de estado pendente.
5. A página **Música** não mostra nível sonoro real animado, diferentemente da GUI anterior; faltam controles integrados às barras.
6. O medidor precisa representar **Graves, Agudos, Volume, Motor (RPM) e Reação da luz com cores visualmente distintas**, inclusive com atualizações simultâneas. **RPM e Reação da luz não são a mesma grandeza**.
7. O estilo **REV/RPM** produz piscadas laranjas estranhas. Não afirmar que são falha de hardware nem que são intencionais sem correlacionar telemetria e saída física.

### Código anterior recuperável no próprio repositório (referência, não substituto)

Branch histórica \`quiklight-x11-windows\`, arquivo \`quiklight-x11/gui/quiklight_gui.py\`:
- Classe \`MusicMeter\` (a partir da linha ~855) renderiza **cinco canais**. Quatro possuem controles de limites \`music_in_*\` / \`music_out_*\` diretamente na barra, clique para ligar/desligar \`music_on_*\` e duplo clique para restaurar o intervalo. O quinto (\`Reação da luz\`) só mostra a saída após filtros.
- \`pg_musica\` (a partir da linha ~1356) inclui \`MusicMeter\`; \`update_music\` (a partir de ~1423) solicita \`quiklight-audio.want\` e lê cinco valores de \`quiklight-audio.txt\`, se atuais. A barra não deve inventar áudio quando não houver dados.
- Na referência histórica, os quatro primeiros canais eram **todos azuis** e Reação mudava entre laranja/vermelho. **Isso NÃO atende à nova exigência do mantenedor de cinco cores distintas**; recuperar interação e telemetria, evoluir a paleta e a acessibilidade.
- \`quiklight-x11/src/audio.rs\` fornece \`[bass, treble, volume, rpm]\` (0–1) por processamento de áudio no exemplo histórico; o quinto valor representa reação já filtrada. Não confundir estimativa RPM sonora com RPM real de jogo, que exige fonte de telemetria validada.
- \`quiklight-x11/src/music.rs\` estilo \`rev\` contém lógica \`shift_t\` e clarão \`flash\` ativado por queda detectada no RPM estimado. É uma **hipótese concreta** para piscadas, mas o backend instalado v0.3.5.1 não foi comparado a esse código histórico: não mudar algoritmo sem verificar a versão instalada.

### Correções de interface e backend — implementação e critérios de aceitação

**P0 — integridade da configuração**
- Antes de quaisquer testes de aplicação, comparar exatamente \`auto_crop\`, \`crop_speed\`, \`border\`, \`cap_w\`, \`cap_h\`, \`inset_left/top/right/bottom\` e demais valores atuais com o snapshot pré-teste e os campos que a GUI exibe.
- Detectar campos exibidos como zero por binding/default; **mostrar valor real, estado desconhecido ou bloqueio de edição**, nunca um zero substituto que possa ser gravado acidentalmente.
- Preservar offsets \`start_led\`, \`physical_leds\`, \`enabled\`, \`source_mode\`, limites por fita, bindings HID e seções desconhecidas no patch TOML. Acrescentar testes de round-trip e de colisão de offsets.

**P1 — Aplicar, Tempo real, serviços e sliders**
- Manter Aplicar manual para alterações estruturais (mudança de \`device\`, \`start_led\`, contagem física, porta USB, captura que requeira reinício) até validar suporte de runtime.
- Distinguir **edição dos parâmetros de segmento** (ex.: \`enabled\` e \`source_mode\`, com regras físicas já válidas) das mudanças estruturais. Habilitar propagação em tempo real somente para as opções efetivamente suportadas pelo Rust instalado, sem reinício de USB para alterações superficiais; \`off\` deve apagar trecho de maneira determinística.
- \`Ligar/Desligar\` devem ser comandos de serviço ou iluminação claros e imediatos, com status confirmado e sem forçar start após desligamento voluntário. Não confundir \`source_mode=off\` com serviço stop.
- Coalescer gravações em fila não concorrente, manter debounce para persistência mas implementar prévia/UI imediatamente ao mover o slider, com latência medida e feedback; nada de apresentar "Aplicado" antes de confirmação.
- Preservar bloqueio explícito do \`--visual-demo\`, backups e rollback.

**P1 — restauração completa de Música, mantendo a nova UI**
- Reintroduzir medidor animado continuamente com as **cinco barras independentes**: Graves, Agudos, Volume, Motor (RPM) e Reação da luz.
- Exibir as barras em **cinco cores distintas** e com legenda textual e percentual, não depender apenas da cor. A paleta deve ser centralizável no tema e adaptável a alto contraste; não compartilhar indevidamente a cor entre canais.
- Colocar **controles mínimo/máximo na própria barra** para os quatro canais de entrada, arrastáveis, com intervalo e valor numérico; ligar/desligar por canal, reset por barra e teclado; reação da luz é apenas leitura (resultado processado), não mais uma entrada.
- O medidor lê telemetria real do áudio, não a telemetria QLV3 de RGB. Renovar pedido de áudio e atualizar somente quando houver amostras novas. Exibir "Sem dados de áudio" em vez de criar níveis fictícios, especialmente se \`music\` estiver desativado ou sem fonte.
- Preservar 22 estilos de música, sensibilidade, presets, filtros \`music_in_*\`, \`music_out_*\`, \`music_on_*\`, mapeamento por fita/segmento e suporte Windows em arquitetura, sem prometer validação Windows.

**P2 — piscadas REV/RPM**
- Instrumentar (primeiro somente leitura) dados \`rpm\`, \`reaction\`, \`shift_t/flash\` (se disponíveis), cor RGB do frame QLV3 e log HID/USB em timestamps coincidentes.
- Verificar se laranja corresponde ao efeito de shift/redline, a um fallback RGB, a valores inválidos/stale, a confusão com \`Reação da luz\`, ou a falha física. Não desligar filtros cegamente.
- Se for um clarão intencional e indesejado, oferecer opção de suavizar/desativar **flash de troca de marcha** sem remover o modo REV. Caso seja defeito de hardware, preservar os logs e o rollback.

### Aceitação mínima para promover versão funcional

- Dois controladores ROBOBLOQ mapeados corretamente, inclusive a parte inferior na fita 2, sem troca de portas/offsets e sem alterações perdidas.
- Tempo real desligado: aplicar apenas quando clicado. Tempo real ligado: campos elegíveis aplicados e refletidos nos LEDs; estruturais informados como pendentes.
- Captura: valores na UI batem com TOML ativo e backup; abrir/fechar a interface **não zera campos**.
- Música: cinco barras mostram sinais distintos, variam ao tocar som e não congelam/stale; thresholds ajustam com arraste durante operação e persistem corretamente; sem dados -> estado informativo.
- RPM: cor/flash explicável a partir do estado mostrado, sem piscadas arbitrárias.
- Regressão Qt/offscreen, TOML, Rust, KDE↔Gamescope, rollback, e matriz Windows **separada** antes de afirmar paridade.

**Status desta seção:** especificação e evidência histórica analisadas; correções de GUI/back-end ainda pendentes, **nenhuma alteração no runtime instalada**.

## Implementação iniciada — telemetria e medidor musical

Arquivos criados na branch experimental, mas **ainda não ligados ao `gui/full_ui.py` real**:

- `experimental/stage02-v054/music_telemetry.py`: leitura validada de cinco canais de `quiklight-audio.txt`, detecção de stale, pedido controlado de `quiklight-audio.want`, limites e cores distintas.
- `experimental/stage02-v054/music_meter_widget.py`: Qt com cinco barras de cores diferentes, alças mínimo/máximo por canal de entrada, toggles por canal e quinta barra de reação somente leitura. Não grava TOML nem aciona serviço.
- `experimental/stage02-v054/tests/test_music_telemetry.py`: testes puros de parsing, ausência de dados, throttling e limites.
- `.github/workflows/stage02-v054-checks.yml`: workflow com sintaxe e testes puros. Primeira execução passou: https://github.com/RotaryMaster/Quiklight---Rotary/actions/runs/44969420256.

Para integrar com rigor os handlers existentes, é necessário publicar a fonte exata v0.5.3 na branch, sem publicar configuração ativa nem dados privados. `tools/publicar-fontes-stage02-v053.py` verifica o SHA256 do ZIP, seleciona somente fontes não sensíveis e publica no prefixo `experimental/stage02-v053-source/` via clone temporário. Se o Git local não tiver credenciais, a publicação falhará sem mudar a instalação nem fazer force-push.

**Próxima implementação após sincronização:** verificar bindings de Recorte/Bordas, separar comandos Ligar/Desligar do Apply, habilitar Tempo real para mudanças seguras com indicação de pendências estruturais e integrar o medidor de música na GUI atual sem redesenho. Testar com TOML sintético e snapshots antes de ativar no hardware. Não há release estável nesta etapa.
