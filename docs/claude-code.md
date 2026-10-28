# Claude Code: instruções estáveis e contexto recuperável

Para usar os métodos no agente da Anthropic, incorpore o
[CLAUDE.md](../templates/claude-code/CLAUDE.md) ao arquivo de instruções do projeto.
Se já houver instruções, preserve-as e integre apenas as diretrizes compatíveis.
Não copie o payload Messages API para um arquivo de configuração do Claude Code.

O template usa `.context/STATE.md` como fonte de continuidade. O
[modelo de estado](../templates/codex/CONTEXT_STATE.md) é Markdown independente
de plataforma e pode ser usado aqui. Os prompts de
[preparação](../templates/codex/prepare-handoff.md) e
[retomada](../templates/codex/resume.md) também podem ser enviados ao Claude Code.

## Uso

1. Na raiz do projeto, incorpore o `CLAUDE.md` e crie `.context/STATE.md` a partir
   do modelo. Não substitua arquivos existentes nem publique estado privado.
2. Inicie uma nova sessão e confirme as instruções carregadas. Mantenha regras
   duráveis estáveis e progresso fora dessas regras.
3. Peça buscas direcionadas e leituras das evidências relevantes. Preserve em
   artefatos as informações que precisarem ser recuperadas depois.
4. Antes de reduzir a conversa, envie o prompt de preparação e confira o estado.
5. Use `/compact` quando precisar da compactação nativa. Na retomada, envie o
   prompt correspondente e verifique checkout, restrições e evidências.

Claude Code gerencia seu próprio cache. Manter instruções e ferramentas estáveis
favorece o reaproveitamento de prefixos, mas o template não promete acertos ou
descontos. Arquivos lidos e resultados antigos continuam ocupando contexto até
que o runtime os gerencie; instruções em Markdown não limpam mensagens retroativamente.

Para limpeza seletiva de resultados em uma aplicação que você controla pela
API, use a [receita Anthropic](anthropic.md). A compactação do Claude Code e o
`clear_tool_uses_20250919` da API são mecanismos diferentes.

## Referências

- [Instruções de projeto e CLAUDE.md](https://code.claude.com/docs/en/memory)
- [Janela de contexto e compactação](https://code.claude.com/docs/en/context-window)
- [Engenharia do cache no Claude Code](https://claude.dev/blog/lessons-from-building-claude-code-prompt-caching-is-everything/)
