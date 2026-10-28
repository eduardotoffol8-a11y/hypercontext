# Anthropic: cache e limpeza seletiva de resultados

## Arquivos e execução

A receita [request.py](../recipes/anthropic/request.py) monta uma chamada Messages
API usando o [payload de exemplo](../recipes/anthropic/request.example.json).
Preserva mensagens e blocos de ferramentas, adicionando controles nativos da API.

Na raiz do repositório:

```bash
python -m recipes.anthropic.request --preview
python -m recipes.anthropic.request --preview --prune-tools
python -m recipes.anthropic.request --preview --no-cache
```

Esses comandos não usam chave e não acessam a rede. O exemplo é sintético; suas
saídas de ferramenta não correspondem a arquivos de uma aplicação. Para uso real,
substitua sistema, ferramentas e histórico pelos dados autorizados da sua aplicação.

Configure `ANTHROPIC_API_KEY` por seu gerenciador de segredos ou ambiente do
processo. Selecione `ANTHROPIC_MODEL` entre os modelos disponíveis na sua conta.
Não coloque a chave no JSON ou na linha de comando.

Depois de configurar o ambiente:

```bash
python -m recipes.anthropic.request --send --input recipes/anthropic/request.example.json
```

Para seu próprio histórico, adapte o exemplo e salve-o em um arquivo local privado:

```bash
python -m recipes.anthropic.request --send --input /caminho/privado/request.json --prune-tools
```

`--send` realiza uma chamada que pode ser cobrada. A opção `--model` pode substituir
`ANTHROPIC_MODEL`. Os mesmos argumentos funcionam no PowerShell, ajustando o
caminho do arquivo. O CLI não grava request ou resposta em disco automaticamente.
O preview e a resposta impressa podem conter dados do seu histórico: trate seus
logs e redirecionamentos como dados da aplicação.

## Cache: prefixo estável

A string `system` vira um bloco de texto com `cache_control: {"type": "ephemeral"}`.
Reutilize o mesmo conteúdo e as mesmas ferramentas antes desse breakpoint.
Coloque alterações da tarefa nas mensagens posteriores. O preset usa o TTL padrão
do provedor; mínimos cacheáveis e modelos compatíveis devem ser conferidos na
[referência de prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).

Uma instrução curta não necessariamente atinge o mínimo do modelo. Não espere um
acerto de cache apenas porque existe `cache_control` no payload. O histórico
continua sujeito à janela de contexto.

## Pruning: tool-result clearing nativo

`--prune-tools` adiciona `context_management` e o cabeçalho beta documentado
`context-management-2025-06-27`. O preset utiliza:

| Campo | Valor | Intenção |
| --- | --- | --- |
| `type` | `clear_tool_uses_20250919` | Limpar resultados antigos no servidor |
| `trigger` | 30.000 tokens de entrada | Adiar a limpeza até o limiar configurado |
| `keep` | 3 usos recentes | Manter interações recentes com ferramentas |
| `clear_at_least` | 5.000 tokens | Evitar uma limpeza muito pequena |
| `exclude_tools` | `read_requirements` | Proteger a ferramenta de requisitos deste exemplo |
| `clear_tool_inputs` | `false` | Preservar os parâmetros das chamadas |

Os números são um ponto de partida, não limiares universais ou resultados de
benchmark. Para adaptar, altere `POLICY` no módulo e a lista de ferramentas
excluídas para os nomes reais da aplicação. Verifique a compatibilidade do modelo
com a funcionalidade beta antes de habilitá-la.

O cliente envia o histórico completo; a transformação ocorre no contexto do
modelo no servidor. O preset não apaga o seu arquivo original, não cria backup e
não persiste decisões por conta própria. Ele também não escolhe conteúdo por
relevância semântica: limpa resultados por idade, respeitando os controles da API.

Habilite apenas quando resultados elegíveis forem descartáveis e recuperáveis,
conforme os [critérios de adoção](methods.md). Separe ferramentas que retornam
estado crítico das que retornam evidências transitórias. Se essa separação não
existir, mantenha pruning desligado.

## Integração com seu agente

Este script envia **um turno**, não executa ferramentas. A resposta nativa é
retornada integralmente: `content`, `stop_reason`, `usage` e `context_management`
ficam disponíveis ao chamador.

Se `stop_reason` for `tool_use`, execute somente ferramentas autorizadas no loop
da sua aplicação e acrescente os respectivos resultados usando o protocolo
Messages. Isso não significa que a tarefa terminou. Uma parada por `max_tokens`
também exige tratamento pelo chamador. Blocos de thinking e assinaturas presentes
na resposta devem ser mantidos conforme as regras do modelo ao reproduzir o
histórico; a receita não tenta reescrevê-los.

O formato aceito é um objeto Messages API com `system` como string, `messages`
não vazio e `max_tokens` positivo. Streaming não é implementado. Políticas
`context_management` preexistentes são rejeitadas para evitar substituição
silenciosa. O timeout é 30 segundos e não há repetição automática de chamadas.

## Verificar cache e limpeza

- Cache: examine `usage.cache_creation_input_tokens` e
  `usage.cache_read_input_tokens` na resposta. Entrada total é a soma desses
  campos com `usage.input_tokens`; não subtraia o cache novamente.
- Pruning: examine `context_management.applied_edits`, incluindo quantos usos e
  tokens foram limpos. Ausência de limpeza no exemplo pequeno é esperada.
- Contagem antecipada: o endpoint `messages/count_tokens` também aceita context
  management e informa contagens antes e depois. Veja o exemplo oficial na
  [documentação de context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing).
- Qualidade: teste se o agente ainda encontra requisitos, decisões e artefatos
  antigos. Limpeza observada sem retomada correta não aprova a integração.

Mudanças anteriores ao breakpoint podem invalidar o cache. Considere o custo das
reescritas e a tarifa de cada modelo/TTL ao comparar os métodos.
