# Validação e critérios de adoção

## O que é verificado automaticamente

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m recipes.anthropic.request --preview
python -m recipes.anthropic.request --preview --prune-tools
```

A suíte testa contabilidade de tokens, custos desconhecidos, custo negativo de
cache frio, preservação do histórico, rejeição de formatos não suportados pelo
adaptador de texto, timeout e ausência de retry automático.

A receita Anthropic tem testes próprios: preservação de mensagens e ferramentas,
cache e pruning independentes, política nativa, cabeçalho beta, rejeição de
configuração preexistente e retorno integral da resposta, incluindo chamadas de
ferramentas e métricas de limpeza. O transporte externo é substituído por fixtures.

O [workflow](../.github/workflows/tests.yml) executa testes e previews em Python
3.9, 3.11 e 3.13. Seu status é evidência de execução, não um badge estático.

## O que depende do ambiente

| Verificação | Evidência necessária |
| --- | --- |
| Cache Anthropic | Resposta real com `cache_read_input_tokens` e `cache_creation_input_tokens` |
| Limpeza Anthropic | `context_management.applied_edits` em histórico elegível |
| Compatibilidade com a conta | Modelo e funcionalidade aceitos pela API |
| Carregamento no Codex | Sessão identificando as instruções aplicadas |
| Continuidade | Agente retomando restrições e evidências depois da compactação |
| Efetividade | Qualidade, tempo, consumo e custo por tarefa concluída |

O repositório não apresenta os testes com fixtures como execução desses testes
de ambiente. Não foram realizadas chamadas pagas para produzir os resultados
publicados aqui. A validação local não certifica segurança nem disponibilidade de
um provedor.

## Critérios de aceitação para usar pruning

- Os resultados elegíveis são descartáveis ou recuperáveis por referência verificável.
- Requisitos e decisões persistem em uma fonte disponível ao agente.
- O protocolo de ferramentas continua íntegro.
- Arquivos e histórico de origem não são apagados pelo processo de redução de contexto.
- A retomada identifica evidência desatualizada ou ausente antes de agir.
- A avaliação funcional não regride em relação ao fluxo sem pruning.

O cumprimento desses critérios reduz riscos operacionais; não torna a seleção de
contexto infalível. Se um critério não puder ser demonstrado, mantenha a limpeza
automática desligada até ajustar o fluxo.

## Compatibilidade do adaptador complementar

`caching_client.py` permanece disponível para chamadas síncronas de texto via
Anthropic Messages e OpenAI Chat Completions. Ele não é o runtime Codex e não
executa ferramentas. Modelo é explícito e tarifas opcionais são fornecidas pelo
chamador. Campos monetários desconhecidos retornam `None`.

O baseline financeiro compara o mesmo request e saída às tarifas comuns, sem
desconto. Ele não executa uma segunda chamada. Cobrança OpenAI de escrita de cache
não é estimada por esse adaptador; quando detectada, o custo fica desconhecido.

`example_agent.py` e `benchmarks.py` são utilitários offline complementares.
O segundo contém apenas cenários aritméticos, sem evidência de desempenho. O
nome é mantido por compatibilidade; não deve ser usado como benchmark empírico.
