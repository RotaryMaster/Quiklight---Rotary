# Mapeamento de trechos e captura

Cada controladora usa índices próprios de LEDs. A configuração prevista possui 65 posições físicas **por fita**.

| Fita | LEDs físicos (1-based) | Captura | Situação no perfil inferior |
|---|---|---|---|
| 1 | 1–17 | esquerda | ativa |
| 1 | 18–48 | topo | ativa |
| 1 | 49–65 | direita | ativa |
| 2 | 1–17 | esquerda | desligada |
| 2 | 18–48 | baixo | ativa |
| 2 | 49–65 | direita | desligada |

Em `config.toml`, `device` começa em 0 e `start_led` também: primeiro LED físico = `start_led = 0`.

## As cores diferentes nas laterais

Se os segmentos laterais da segunda fita forem habilitados, o algoritmo `edge_window` divide uma borda compartilhada proporcionalmente entre **todos os segmentos ativos daquela borda**. Nesse caso, a Fita 2 pode capturar uma subfaixa diferente da Fita 1: **isso não é mirror**. Segmentos desativados deveriam enviar preto em `multi_strip::map_output`; a observação de cores físicas exige conferir os estados e a telemetria real.

## Nova escolha de fonte (planejada / ainda experimental)

- Independente: capturar a região atribuída por `edge_window`.
- Espelhado: reproduzir o RGB de outro trecho escolhido, sem dividir novamente a borda.
- Desligado: manter as posições físicas, mas enviar preto, sem deslocar o restante.

As transições devem respeitar Tempo Real, não reinicializar controladores e preservar rollback. Não marcar como estável antes de validar em hardware.
