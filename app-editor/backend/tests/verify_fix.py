def _truncar_texto(texto: str, max_chars: int) -> str:
    """Trunca texto que excede max_chars, cortando no último espaço.
    Garante que nenhuma palavra seja cortada ao meio.
    Adiciona '...' no final."""
    if len(texto) <= max_chars:
        return texto
    
    # Limite efetivo para o texto antes dos pontos
    limite = max_chars - 3
    if limite <= 0:
        return "..."
    
    # Pega o trecho até o limite (3 caracteres para o '...')
    cortado = texto[:limite]
    
    # Tenta encontrar o último espaço ANTES do limite
    ultimo_espaco = cortado.rfind(" ")
    
    if ultimo_espaco != -1:
        # Trunca no espaço encontrado
        return cortado[:ultimo_espaco].rstrip() + "..."
    
    # Em caso de palavra única maior que o limite, trunca no limite (fallback)
    return cortado.rstrip() + "..."

def _formatar_overlay(texto: str, max_por_linha: int = 35) -> str:
    """Garante overlay com max 2 linhas equilibradas, max_por_linha chars cada."""
    texto = texto.strip()
    if len(texto) <= max_por_linha:
        return texto
    # Se já tem quebra manual (\n ou \\N), verificar cada linha
    for sep in ["\\N", "\n"]:
        if sep in texto:
            linhas = texto.split(sep)
            formatadas = []
            for l in linhas[:2]:
                l = l.strip()
                if len(l) > max_por_linha:
                    l = _truncar_texto(l, max_por_linha)
                formatadas.append(l)
            return "\\N".join(formatadas)
    # Sem quebra — inserir \\N no ponto mais equilibrado
    meio = len(texto) // 2
    pos_esq = texto.rfind(" ", 0, meio + 1)
    pos_dir = texto.find(" ", meio)
    if pos_esq == -1 and pos_dir == -1:
        return _truncar_texto(texto, max_por_linha)
    candidatos = []
    if pos_esq != -1:
        l1, l2 = texto[:pos_esq].strip(), texto[pos_esq:].strip()
        candidatos.append((abs(len(l1) - len(l2)), l1, l2))
    if pos_dir != -1 and pos_dir != pos_esq:
        l1, l2 = texto[:pos_dir].strip(), texto[pos_dir:].strip()
        candidatos.append((abs(len(l1) - len(l2)), l1, l2))
    candidatos.sort(key=lambda x: x[0])
    _, linha1, linha2 = candidatos[0]
    # Guarda: menor linha >= 35% do total
    total = len(linha1) + len(linha2)
    if min(len(linha1), len(linha2)) < total * 0.35:
        for offset in range(1, meio):
            for pos in [texto.rfind(" ", 0, meio - offset + 1), texto.find(" ", meio + offset)]:
                if pos is not None and pos > 0:
                    l1 = texto[:pos].strip()
                    l2 = texto[pos:].strip()
                    if min(len(l1), len(l2)) >= (len(l1) + len(l2)) * 0.35:
                        linha1, linha2 = l1, l2
                        break
            else:
                continue
            break
    if len(linha1) > max_por_linha:
        linha1 = _truncar_texto(linha1, max_por_linha)
    if len(linha2) > max_por_linha:
        linha2 = _truncar_texto(linha2, max_por_linha)
    return linha1 + "\\N" + linha2

def test_truncamento():
    print("VALIDANDO CORREÇÃO")
    # Limite 35
    LIMIT = 35

    # Teste 1: "— presta atenção no que ela faz agora mesmo porque é importante demais para ignorar"
    texto1 = "— presta atenção no que ela faz agora mesmo porque é importante demais para ignorar"
    res1 = _formatar_overlay(texto1, LIMIT)
    print(f"Original: '{texto1}' (len={len(texto1)})")
    print(f"Resultado: '{res1}'")
    l1, l2 = res1.split("\\N")
    print(f"Linha 1: '{l1}' (len={len(l1)})")
    print(f"Linha 2: '{l2}' (len={len(l2)})")
    
    # Teste 2: Casos do usuário
    casos = [
        "— presta atenção no que ela faz aqui agora",
        "Nessun Dorma termina com um Dorma maravilhoso hoje",
        "que destroça sopranos experientes demais para nós"
    ]
    for c in casos:
        # Se forçar ser tudo em uma linha (pra testar truncamento)
        res = _truncar_texto(c, LIMIT)
        print(f"Truncamento Manual (35): '{c}' -> '{res}' (len={len(res)})")

if __name__ == "__main__":
    test_truncamento()
