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
