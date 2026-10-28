# HyperContext

**Prompt caching e context pruning: decisões de arquitetura, receitas executáveis e operação em Anthropic e Codex.**

[![CI](https://github.com/eduardotoffol8-a11y/hypercontext/actions/workflows/tests.yml/badge.svg)](https://github.com/eduardotoffol8-a11y/hypercontext/actions/workflows/tests.yml)

Cache reaproveita o processamento de prefixos repetidos. Pruning retira do contexto
ativo informações selecionadas que podem ser recuperadas quando necessário.
São mecanismos complementares: um reduz recomputação; o outro administra o conteúdo
que chega ao modelo. A decisão de usá-los depende da carga e do estado que a tarefa
precisa preservar.

Este repositório reúne padrões de uso, arquivos reutilizáveis, exemplos isolados e
testes de contrato. Não depende de um projeto de aplicação para explicar os métodos.

## Escolha o caminho

| Ambiente | Prompt caching | Context pruning e continuidade | Arquivos |
| --- | --- | --- | --- |
| Anthropic Messages API | Breakpoint explícito no prefixo estável | Limpeza nativa e seletiva de resultados de ferramentas, habilitada explicitamente | [Receita executável](recipes/anthropic/request.py) e [guia](docs/anthropic.md) |
| Claude Code | Gerenciado pelo agente da Anthropic | Seleção de evidências, estado persistido e compactação nativa | [CLAUDE.md](templates/claude-code/CLAUDE.md) e [guia](docs/claude-code.md) |
| Codex CLI / app | Gerenciado pelo runtime; organização estável das instruções evita alterações desnecessárias | Recuperação seletiva de arquivos, estado persistido e compactação nativa da conversa | [AGENTS.md](templates/codex/AGENTS.md), [prompts](templates/codex/) e [guia](docs/codex.md) |

**Codex não é um nome alternativo para a API OpenAI.** Um `AGENTS.md` orienta o
agente; não configura `cache_control` e não remove mensagens já presentes no
histórico. O guia distingue seleção de contexto, pruning e compactação.

## Comece em poucos comandos

Python 3.9+; as receitas usam a biblioteca padrão, sem instalação de dependências.

```bash
git clone https://github.com/eduardotoffol8-a11y/hypercontext.git
cd hypercontext
python -m recipes.anthropic.request --preview
python -m recipes.anthropic.request --preview --prune-tools
python -m unittest discover -s tests -p "test_*.py"
```

Os dois primeiros comandos mostram os payloads localmente. Para realizar uma
chamada Anthropic, escolha um modelo disponível na sua conta, configure a chave no
ambiente e use `--send`, conforme o [guia de integração](docs/anthropic.md).
O exemplo tem histórico sintético e pequeno: demonstra a configuração, sem provocar
um acerto de cache ou uma limpeza real.

Para Codex, incorpore as diretrizes do [template](templates/codex/AGENTS.md) ao
`AGENTS.md` do seu projeto e use o [roteiro de instalação e continuidade](docs/codex.md).

## O que torna os métodos efetivos

- **Cache:** um prefixo suficientemente longo e repetido, com reutilização antes
  da expiração, permite amortizar seu processamento. Acompanhe leituras e escritas
  de cache; a primeira escrita pode custar mais que uma entrada comum.
- **Pruning:** saídas volumosas, descartáveis e recuperáveis podem deixar o contexto
  ativo. Requisitos, decisões e trabalho pendente precisam permanecer disponíveis
  em estado verificável. O benefício deve superar a releitura e eventuais perdas
  de cache causadas pela alteração do prefixo.
- **Combinação:** mantenha as instruções estáveis separadas das evidências
  transitórias. Faça a seleção na camada adequada ao ambiente e valide o resultado
  da tarefa, além da redução de tokens.

O [guia técnico](docs/methods.md) apresenta critérios de adoção, relação entre os
custos e protocolo de avaliação. Não há percentual universal de economia.

## Conteúdo

| Arquivo | Uso |
| --- | --- |
| [docs/methods.md](docs/methods.md) | Arquitetura, efetividade, riscos e avaliação |
| [docs/anthropic.md](docs/anthropic.md) | Integração Messages API, cache e tool-result clearing |
| [docs/claude-code.md](docs/claude-code.md) | Uso no agente da Anthropic com CLAUDE.md |
| [docs/codex.md](docs/codex.md) | Uso no Codex, instruções estáveis e continuidade |
| [recipes/anthropic/](recipes/anthropic/) | Payload nativo e CLI com preview e envio explícito |
| [templates/codex/](templates/codex/) | Diretrizes e prompts para adotar em outros repositórios |
| [docs/validation.md](docs/validation.md) | Escopo dos testes e verificação em ambiente real |
| [caching_client.py](caching_client.py) | Adaptador complementar para conversas de texto, preservando o histórico |

As receitas suportam os mecanismos documentados nas fontes oficiais. Os testes
locais validam construção de requests, preservação de conteúdo e contabilização;
benefícios de latência, qualidade e custo exigem medição com a carga real.

## Referências

- [Anthropic: prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Anthropic: context editing](https://platform.claude.com/docs/en/build-with-claude/context-editing)
- [Codex: instruções com AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Codex: comandos e compactação](https://learn.chatgpt.com/docs/developer-commands)
- [OpenAI: prompt caching na API](https://developers.openai.com/api/docs/guides/prompt-caching)

[Licença MIT](LICENSE).
