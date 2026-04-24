"""Verifica se o tier Anthropic do projeto suporta o server tool web_search_20250305.

Roda uma busca de teste curta. Se sucesso, a variável USE_ANTHROPIC_WEB_SEARCH pode ficar
'true' em produção (Ramo A). Se falhar com 400/permissão, implementar fallback Google CSE
conforme Passo 0.6 do BO_PLANO_V2.md (Ramo B).

Uso:
    ANTHROPIC_API_KEY=... python scripts/verify_web_search.py
"""
import os
import sys

try:
    from anthropic import Anthropic
except ImportError:
    print("FAIL — pacote `anthropic` não instalado. Rode: pip install anthropic>=0.40.0")
    sys.exit(2)

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("FAIL — ANTHROPIC_API_KEY não definido no ambiente.")
    sys.exit(2)

client = Anthropic(api_key=api_key)
try:
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": "Search web for: capital of France 2026"}],
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 2,
        }],
    )
    print("OK — web_search disponivel")
    print(f"Stop reason: {resp.stop_reason}")
    usage = getattr(resp, "usage", None)
    print(f"Server tool use: {getattr(usage, 'server_tool_use', 'N/A')}")
    sys.exit(0)
except Exception as e:
    print(f"FAIL — web_search indisponivel: {type(e).__name__}: {e}")
    print("Ramo B: implementar fallback Google CSE conforme BO_PLANO_V2 Passo 0.6.")
    sys.exit(1)
