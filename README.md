# QuikLight — fork RotaryMaster

Fork comunitário do QuikLight / quiklight-x11, com experimentos de captura ambiente, interface Qt e suporte a múltiplas fitas LED. Este repositório preserva trabalho derivado do projeto original; consulte o histórico Git e os avisos de licença dos arquivos de origem. Não é um produto oficial dos autores upstream.

## Estado das versões (21/11/2026)

**Baseline validada pelo mantenedor: MultiStrip v0.3.4.4 (Bazzite KDE/Linux).** Foram confirmados dois controladores ROBOBLOQ USB HID (1A86:FE07), cada um com 65 posições físicas, captura funcionando e mudanças estruturais com a opção `Tempo real`. O teste relatado não constitui validação de todos os dispositivos, cenários nem da versão Windows.

A **próxima implementação de fonte por trecho (Independente / Espelhado / Desligado)** é trabalho experimental separado; **não faz parte da baseline estável v0.3.4.4**.

## Layout físico de referência

| Seção física | Fita 1 | Fita 2 |
| --- | --- | --- |
| LEDs 1–17 | Esquerda (captura) | Lateral esquerda (opcional; desligada no perfil inferior) |
| LEDs 18–48 | Topo (captura) | Baixo (captura) |
| LEDs 49–65 | Direita (captura) | Lateral direita (opcional; desligada no perfil inferior) |

Cada controlador possui seu próprio índice físico 1–65. A Fita 2 não deve deslocar LEDs nem consumir posições da Fita 1.

**Atenção:** quando duas seções ativas usam a mesma borda, o algoritmo `edge_window` divide a área de captura proporcionalmente entre elas; portanto, suas cores podem ser diferentes. **Isso não é espelhamento.** Se uma lateral estiver marcada como desligada e ainda acender fisicamente, verificar a configuração carregada, os estados de saída e a telemetria QLV3 antes de concluir que ela está inativa.

## Recursos

- Captura da tela no KDE/Wayland com detecção de barras pretas e ajustes de fidelidade/cores;
- Modo música, efeitos, cor estática e personalização Qt;
- Múltiplos controladores HID com isolamento das falhas na revisão v0.3.4.3+;
- Mapeamento físico por fita e trecho (`device`, `edge`, `leds`, `start_led`, `enabled`, `reverse`);
- Ajustes em tempo real na v0.3.4.4, inclusive mudanças estruturais de fita e captura;
- Backup/rollback de versão; preservação de `config.toml`.

## Segurança e reprodução

O sistema Bazzite é imutável; as instalações devem operar no diretório do usuário, sem modificar a base do sistema. **Não publicar** configurações pessoais, identificadores locais de hardware, caminhos de usuário, logs com dados privados ou chaves. Faça backup antes de instalar. O número da interface `hidrawN` não é um identificador persistente; prefira topologia e descritor para distinguir controladores. Alterações no protocolo ou firmware não devem ser feitas sem validação.

Os patches da série v0.3.4.x foram testados no ambiente do mantenedor. O código completo da compilação instalada e seus módulos auxiliares devem ser conferidos antes de anunciar um pacote fonte independente ou uma release reproduzível. **A baseline estável documentada aqui não é uma release/binário publicado automaticamente pelo GitHub.**

## Documentação

- [Estado de validação e próximos passos](docs/QUIKLIGHT-STATUS.md)
- [Mapeamento e modo de captura das seções](docs/QUIKLIGHT-MULTISTRIP.md)
- [Histórico da série MultiStrip](docs/QUIKLIGHT-CHANGELOG.md)

## Origem e créditos

Este trabalho parte do QuikLight/quiklight-x11 e de alterações mantidas neste fork. Verifique os arquivos originais, seu histórico e as respectivas licenças antes de redistribuição de binários. As adaptações incluem GUI Qt, captura KDE, portabilidade experimental para Windows e controle de múltiplas fitas.
