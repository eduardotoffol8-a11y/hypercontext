# Auditoria técnica — 27/10/2026

Base revisada: commit `86924b0` do repositório HyperContext.

## Parecer e decisões

Cache de prefixo é uma técnica documentada pelos provedores. Foi mantido com
preservação integral das mensagens. Não é uma garantia de economia, qualidade,
privacidade ou segurança operacional.

A compactação anterior removia blocos pelo tamanho e posição, sem comprovar que
eram obsoletos ou recuperáveis. O texto inserido afirmava que a implementação
estava salva em Git sem verificar isso. Essa funcionalidade foi retirada, em vez
de receber um rótulo de segurança que os testes não sustentam.

| Problema observado | Decisão aplicada |
| --- | --- |
| Código antigo e requisitos podiam desaparecer do contexto | Remover `ContextPruner` e seus parâmetros do cliente |
| AST preservava nomes, sem contratos ou comportamento | Retirar promessa de preservação semântica e o módulo de pruning |
| Conta da Anthropic subtraía cache de um campo já separado | Somar os buckets para total; cobrar cada bucket uma vez |
| Tarifas e modelos antigos tinham defaults e fallback silencioso | Modelo explícito; tarifas opcionais fornecidas pelo usuário |
| Economia negativa era escondida por arredondamento/clamp | Preservar resultados negativos e valores desconhecidos |
| Benchmark assumia cache quente desde a primeira chamada | Substituir por cenários aritméticos com escrita fria, leitura e expiração |
| Exemplo chamava APIs Python inexistentes | Substituir por exemplo offline executável |
| Compatibilidade com vLLM/SGLang era afirmada sem integração | Remover adaptador local e essas afirmações |
| Ausência de timeout e aceitação parcial de respostas | Timeout explícito; erros de rede propagados; respostas incompletas rejeitadas |
| Badge estático de testes aprovados e promessas de desempenho | Remover; adicionar workflow que realmente executa verificações |

## Evidência e limites

A suíte original tinha cinco testes do compactador. Eles passavam, enquanto
`example_agent.py` falhava com argumento inexistente. O benchmark original era
uma simulação de caracteres/tokens, sem chamadas ao modelo.

Testes de regressão foram executados contra a versão anterior antes das correções:
reproduziram remoção de histórico, tarifa presumida, métricas ausentes tratadas
como zero e aceitação do provedor local sem implementação compatível comprovada.

A suíte revisada testa payloads com histórico integral, buckets Anthropic/OpenAI,
escrita fria mais cara, ausência de tarifas e métricas, rejeição de ferramentas,
timeout sem repetição automática, breakpoint Anthropic e respostas incompletas.
O transporte HTTP é substituído por fixtures locais. Nenhum teste de API paga,
acerto real de cache, latência, qualidade de respostas ou segurança adversarial
foi realizado. A documentação não apresenta tais resultados como comprovados.

Modelos OpenAI com cobrança de escrita de cache exigem tratamento específico por
modelo/TTL. Quando esse uso aparece na resposta, o cliente mantém a contagem,
mas deixa o custo desconhecido. A integração é Chat Completions, não Responses.

## Migração 0.1 → 0.2

Mudança incompatível intencional: `pruner.py`, `ContextPruner`,
`preserve_recent_turns`, `enable_context_pruning` e `active_target_files` foram
removidos. Chamadas antigas falham explicitamente; não são redirecionadas para
outra forma de remoção de histórico. Informe `model` ao construir o cliente.
Custos podem ser `None`; descontos negativos precisam ser tratados como aumento
de custo. Não utilizar os números da versão anterior como evidência de desempenho.

## Fontes primárias consultadas

- [Anthropic: cache e campos de uso](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [OpenAI: regras de cache e precificação por modelo](https://developers.openai.com/api/docs/guides/prompt-caching)
- [Anthropic: compactação e risco de perda de contexto](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)

As fontes comprovam a existência das técnicas. Não comprovam adoção, endosso ou
auditoria deste projeto por essas empresas. Este documento também não é uma
certificação de segurança nem uma aprovação para uso em produção.

## Registro de validação local

- Python 3.11.0: 13 testes aprovados com `python -m unittest discover -s tests -p "test_*.py"`.
- `python example_agent.py` e `python benchmarks.py`: executados sem chamadas de rede.
- Sintaxe dos quatro arquivos Python conferida com a gramática Python 3.9;
  isso não equivale a executar os testes nessa versão.
- Wheel `hypercontext-0.2.0-py3-none-any.whl` gerado com sucesso, sem instalar
  dependências ou publicar no PyPI. Runtime sem dependências externas;
  empacotamento utiliza setuptools.
- Revisão independente das alterações sem achados importantes no escopo revisado.
- A execução da matriz no GitHub é uma verificação separada da validação local.
