# Análise de truncamento — `app-curadoria/`, `shared/`, testes

## app-curadoria/backend/

Curadoria é descoberta/seleção de vídeos no YouTube. Pouca superfície de conteúdo editorial.

**Pontos MÉDIOS:**
| # | Path:linha | Categoria | O quê |
|---|------------|-----------|-------|
| C1 | [services/download.py:117](app-curadoria/backend/services/download.py:117) | T1 | `return s[:200] if s else 'video'` — sanitize_name para filename (paralelo a shared/storage_service.py:64) |
| C2 | [services/youtube.py:91, 164](app-curadoria/backend/services/youtube.py:91) | T1 log | `r1.text[:200]` em log warning — logs apenas |
| C3 | [services/download.py:230, 274, 303](app-curadoria/backend/services/download.py:230) | T1 log | Slices em logs yt-dlp / cobalt — logs apenas |
| C4 | [routes/curadoria.py:254-255](app-curadoria/backend/routes/curadoria.py:254), [services/youtube.py:123-124, 206-207](app-curadoria/backend/services/youtube.py:123) | **não-truncamento** | `pub[:10]` pega `YYYY-MM-DD` de ISO timestamp, `pub[:4]` pega ano. É extract de campo estruturado, não corte de conteúdo. ✓ |

**VARCHAR curadoria:** 0 matches no grep T9 (curadoria não tem tabelas próprias nesse grep — provavelmente compartilha infra com outro app ou usa JSON).

## shared/

| # | Path:linha | Categoria | O quê |
|---|------------|-----------|-------|
| R6 | [storage_service.py:64](shared/storage_service.py:64) | T1 | `return s[:200] if s else 'unknown'` — sanitize_name trunca nome de pasta R2 a 200 chars. Comentário diz "Remove caracteres problemáticos para uso como nome de pasta no R2/filesystem". Severidade MÉDIA — afeta key storage, não conteúdo editorial. Mas viola Princípio 1. |

Outros arquivos de `shared/`:
- `retry.py` — nenhum slice/truncamento
- `__init__.py` — vazio

## Testes / fixtures — `app-editor/backend/tests/`

| Arquivo | Relevância |
|---------|------------|
| [verify_fix.py](app-editor/backend/tests/verify_fix.py) | **Teste manual que valida `_truncar_texto` e `_formatar_overlay` como comportamento correto.** Assertion `res.endswith("...")`. Precisa ser invertido/removido na fase de execução quando `_truncar_texto` for eliminado. |
| [test_multi_brand.py](app-editor/backend/tests/test_multi_brand.py) | Testa `overlay_max_chars_linha=35` como default. Ajustar para 38 quando policy for unificada. |
| [test_perfil_unificado.py](app-editor/backend/tests/test_perfil_unificado.py) | Testa `duracao_max` em curadoria_filters — não é duração de legenda, é duração de vídeo. OK. |

**Projeto não tem suite automatizada rodando em CI** — confirmado no reconhecimento inicial. Os testes em `tests/` são smoke tests manuais (`pytest` local). Remediação não pode depender de testes automatizados.

## Validação pós-execução — ausência de testes automatizados

Por não haver suite automatizada, validação das remediações na fase de execução (PROMPT 10) será **manual**, via:

1. Rerun de pipeline RC completo em projeto teste (identificar "projeto canário" — sugestão: reprocessar projeto ID 355 referido em evidências históricas, ou equivalente em prod)
2. Critérios de "funcionando":
   - Nenhuma ocorrência de `[RC LineBreak] Texto truncado: sobrou '...'` no log do redator
   - Todas as legendas narrativas dentro do clamp 4-6s (após remediação do Problema 2)
   - Overlay renderizado no vídeo final (via editor) sem texto truncado visível
   - Post aprovado integralmente presente em prompt de automation (não truncado a 500)
   - Research aprovado integralmente presente em prompt de hooks/translation (não truncado)
   - Traduções geram N entries para N input entries
3. Comparação output antes/depois: git diff do JSON de overlay gerado para projeto canário, antes e depois do patch
4. Inspeção manual de ASS gerado: abrir ASS no Aegisub, verificar ausência de "..." em textos que não deveriam ter

Esta validação manual é documentada na seção "Validação pós-execução" do relatório principal.
