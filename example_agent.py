"""
Demonstração de Agente com Context Pruning e Prompt Caching
Pode ser executado com provedor mock ou chamadas reais.
"""
from pruner import ContextPruner

def simulate_pruning():
    pruner = ContextPruner(keep_recent_turns=2)

    # Simulação de um histórico longo com blocos de código redundantes
    history = [
        {"role": "user", "content": "Crie um módulo de cálculo de frete."},
        {"role": "assistant", "content": "Aqui está o módulo:\n```python\n" + "\n".join([f"def rota_{i}(): pass" for i in range(50)]) + "\n```"},
        {"role": "user", "content": "Agora adicione a classe Veiculo."},
        {"role": "assistant", "content": "Aqui está o veículo:\n```python\n" + "\n".join([f"class Veiculo_{i}: pass" for i in range(40)]) + "\n```"},
        {"role": "user", "content": "Adicione validação de placa no Veiculo."},
    ]

    print("=== HISTÓRICO ORIGINAL ===")
    raw_chars = sum(len(m["content"]) for m in history)
    print(f"Total de caracteres brutos: {raw_chars} (~{raw_chars // 4} tokens)")

    pruned = pruner.prune_messages(history)

    print("\n=== HISTÓRICO APÓS CONTEXT PRUNING ===")
    pruned_chars = sum(len(m["content"]) for m in pruned)
    print(f"Total de caracteres podados: {pruned_chars} (~{pruned_chars // 4} tokens)")
    print(f"Economia de tokens: {100 - (pruned_chars / raw_chars * 100):.1f}%")

    print("\nConteúdo da mensagem antiga após poda:")
    print(pruned[1]["content"])

if __name__ == "__main__":
    simulate_pruning()
