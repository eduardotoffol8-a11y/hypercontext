# Codex: contexto enxuto e continuidade verificável

## O que é controlável

Codex é um ambiente de execução de agentes. Ele organiza instruções, ferramentas,
histórico e compactação. Os arquivos deste kit orientam descoberta de evidências,
registro de estado e continuidade. Eles não concedem acesso ao cache interno e
não configuram a API Anthropic.

`AGENTS.md` não ativa cache, não garante desconto e não remove mensagens antigas.
No Codex, pruning manual é uma política de seleção do que buscar e trazer para os
próximos turnos; a redução efetiva do histórico existente usa os mecanismos do
runtime. A compactação nativa resume o contexto e é distinta da limpeza seletiva
de resultados da API Anthropic.

## Arquivos prontos para incorporar

| Arquivo | Destino / uso |
| --- | --- |
| [AGENTS.md](../templates/codex/AGENTS.md) | Incorporar ao `AGENTS.md` do projeto |
| [CONTEXT_STATE.md](../templates/codex/CONTEXT_STATE.md) | Copiar para `.context/STATE.md`, preencher durante a tarefa |
| [prepare-handoff.md](../templates/codex/prepare-handoff.md) | Enviar ao Codex antes de compactar ou trocar de sessão |
| [resume.md](../templates/codex/resume.md) | Enviar na retomada |

Use os arquivos no repositório que você pretende trabalhar. Não os instale como
regras globais para todos os seus projetos sem avaliar o escopo. Se já existir
`AGENTS.md`, incorpore as diretrizes compatíveis e preserve as convenções atuais.

Exemplo PowerShell para um projeto **sem** esses arquivos, executado na raiz
dele, depois de definir `$kitPath` como o caminho deste clone:

```powershell
if (Test-Path -LiteralPath 'AGENTS.md') { throw 'Incorpore as diretrizes ao AGENTS.md existente.' }
if (Test-Path -LiteralPath '.context/STATE.md') { throw 'Preserve o estado existente.' }
Copy-Item -LiteralPath (Join-Path $kitPath 'templates/codex/AGENTS.md') -Destination 'AGENTS.md'
New-Item -ItemType Directory -Path '.context' -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $kitPath 'templates/codex/CONTEXT_STATE.md') -Destination '.context/STATE.md'
```

No Bash, para um projeto sem esses arquivos:

```bash
test ! -e AGENTS.md && test ! -e .context/STATE.md &&
  mkdir -p .context &&
  cp "$KIT_PATH/templates/codex/AGENTS.md" AGENTS.md &&
  cp "$KIT_PATH/templates/codex/CONTEXT_STATE.md" .context/STATE.md
```

Defina `KIT_PATH` com o caminho do clone antes de executar. Não publique em Git
estado de tarefas que contenha dados privados. Decida por projeto se `.context/`
deve ser versionado ou ignorado.

Inicie uma nova sessão na raiz do projeto e peça que o Codex identifique as
instruções carregadas. O runtime aplica a descoberta e precedência documentadas
de `AGENTS.md`; templates não substituem controles de permissão.

## Rotina de uso

1. Dê ao agente o objetivo e os critérios de aceitação. Mantenha regras duráveis
   no `AGENTS.md`; registre progresso em `.context/STATE.md`.
2. Busque caminhos e símbolos antes de abrir arquivos inteiros. Leia apenas os
   trechos necessários e amplie quando houver dependências ou evidência insuficiente.
3. Preserve os resultados completos em artefatos recuperáveis quando eles forem
   necessários; leve ao contexto a conclusão, a referência e as pendências.
4. Antes de compactar ou mudar de sessão, use o prompt `prepare-handoff.md`.
   Confira que os arquivos existem e que o estado separa fatos de hipóteses.
5. No Codex CLI, use `/compact` quando precisar reduzir o contexto da conversa.
   A compactação é nativa; o prompt de handoff não a executa sozinho. No app,
   confirme os comandos disponíveis na sua versão.
6. Depois da compactação ou em uma nova sessão, use `resume.md`. Confira branch,
   commit, alterações locais e evidências antes de continuar.

## Cache no Codex

Mantenha instruções concisas e estáveis durante a tarefa. Evite reescrever
`AGENTS.md`, trocar repetidamente as ferramentas ou incluir timestamps e progresso
nas instruções permanentes sem necessidade. Essas escolhas evitam variabilidade
desnecessária; o cache efetivo e a compactação continuam sob controle do runtime.

Não há neste kit um `cache_prompt=true` para Codex nem um parâmetro inventado de
pruning em `config.toml`. Também não se equipara o adaptador OpenAI Chat
Completions deste repositório ao produto Codex.

## Verificação operacional

Valide primeiro o carregamento de instruções e a qualidade da retomada, usando
uma tarefa pequena com restrições conhecidas. Depois teste uma tarefa longa.
O agente deve conseguir explicar o objetivo, reencontrar as evidências, perceber
arquivos alterados e reportar corretamente o que foi ou não testado.

Ter um arquivo menor ou uma conversa resumida não comprova cache hit, redução
de custo ou manutenção da qualidade. Se o ambiente não expõe contadores de cache,
reporte essa limitação; não estime descontos a partir da aparência da conversa.

## Fontes oficiais

- [Descoberta e precedência de AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
- [Comandos do Codex e /compact](https://learn.chatgpt.com/docs/developer-commands)
- [Guia de prompting do Codex e compactação](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
