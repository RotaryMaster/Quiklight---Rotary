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
