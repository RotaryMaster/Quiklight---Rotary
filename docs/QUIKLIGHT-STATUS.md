# QuikLight — estado da série MultiStrip

Atualizado em 21/11/2026. Fork: RotaryMaster/rotaryopersonal.

## Baseline confirmada no Bazzite KDE

- **v0.3.4.4**: duas fitas em funcionamento e ajustes estruturais em Tempo Real confirmados pelo mantenedor; não equivale a validação universal ou release binária.
- Dois controladores ROBOBLOQ HID (VID:PID 1A86:FE07), cada um com 65 posições físicas.
- Fita 1: 17 esquerda + 31 topo + 17 direita.
- Fita 2: 17 esquerda + 31 inferiores + 17 direita; as laterais podem ser desativadas sem reduzir a capacidade física.
- v0.3.4.1: timeout HID e reinicializações; v0.3.4.3: isolamento por controlador relatado como funcional; v0.3.4.4: hot reload de ajustes.
- **Windows**: implementação em desenvolvimento, sem validação física dessa revisão.

## Próximos passos (não pertencem à baseline estável)

- Fonte de cores por trecho: Independente, Espelhado e Desligado.
- Testar explicitamente transições ao vivo, desligamento seguro e rollback.
- Verificar as laterais da Fita 2, que foram observadas emitindo cores físicas distintas: verificar se estavam marcadas ativas e conferir a telemetria QLV3.
- Consolidar o código-fonte completo e os módulos auxiliares em uma build reproduzível, antes de publicar uma release.

## Cuidados

Não versionar config.toml real, dados privados, serial de hardware, dumps de sistema, logs com identificadores ou credenciais. No Bazzite imutável instalar somente na área do usuário. Não substituir uma versão funcional sem snapshot.
