# Política de instalação e limpeza de arquivos temporários (QuikLight)

Solicitação do mantenedor em 2026-11-21: **a cada nova instalação, inclusive experimental, evitar o acúmulo de ZIPs antigos em Downloads**.

## Comportamento obrigatório para futuros instaladores

1. Instalar/testar a partir de pasta extraída; validar conteúdo, dependências e, quando cabível, executar testes antes da limpeza.
2. Ao confirmar que a versão nova foi extraída e validada, localizar **apenas arquivos `.zip` antigos do mesmo pacote e componente** no diretório Downloads do usuário (incluindo `xdg-user-dir DOWNLOAD` no Linux, se disponível).
3. **Conservar o ZIP da versão atual**; remover somente ZIPs anteriores da mesma família e informar os nomes removidos. Se o arquivo atual não puder ser identificado com segurança, **não excluir nada**.
4. Nunca remover arquivos de outros projetos, pacotes não reconhecidos, backups de rollback, snapshots, configurações, pastas extraídas ou diretórios de fontes; não fazer `rm -rf ~/Downloads`, curingas genéricos nem exclusão silenciosa.
5. Repetir a proteção nos instaladores **Linux e Windows**. O Bazzite tem base imutável: instalação deve ser restrita ao usuário, com alterações reversíveis.
6. Separar claramente *teste visual/demo* de *aplicação efetiva*: sucesso de testes Python não prova validação física da GUI/LEDs.

## Erro específico Stage 02 v0.5.1

`testar-e-abrir-linux.sh` está executável no ZIP mas `iniciar-linux.sh` foi empacotado com modo `0644`. A última linha `exec "$HERE/iniciar-linux.sh" --visual-demo` resulta em `Permissão negada` mesmo após 44 testes Python (43 OK e 1 ignorado).

**Correção mínima e portátil:** invocar com `exec bash "$HERE/iniciar-linux.sh" --visual-demo` (ou preservar o bit de execução no empacotamento). Evitar depender de `chmod` em diretórios extraídos/partilhas. O erro **não** decorre de falha da GUI ou do backend Rust.

Pacote antigo permanece experimental e não deve substituir o executável instalado. O reparo pode ser aplicado diretamente no script já extraído, sem baixar outro ZIP.
