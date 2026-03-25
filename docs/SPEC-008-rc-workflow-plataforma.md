# SPEC-008 — Workflow RC dentro da Plataforma: Pipeline de Render Próprio

**Data:** 25/03/2026
**Baseado em:** PRD-008
**Status:** EM EXECUÇÃO

---

## Contexto

O Reels Classics (RC) é um canal instrumental que usa a plataforma do Best of Opera mas percorria o mesmo fluxo de edição — incluindo etapas irrelevantes como seleção de idioma da música, alinhamento de letra e render de 3 tracks via FFmpeg.

A decisão tomada nesta sessão: **Opção A — render dentro da plataforma via FFmpeg**, com pipeline simplificado de 1 track (overlay narrativo). O CapCut é eliminado do fluxo.

**Fluxo alvo do RC:**
```
Dashboard → Redator → Overlay → Post → Tradução → Editor (render 1 track) → Exportar
```

**Infraestrutura já existente (não requer criação):**
- `sem_lyrics` e `eh_instrumental` existem no model `Edicao`
- `gerar_ass()` já tem parâmetro `sem_lyrics=True` que gera só o track de overlay
- Página `/editor/edicao/[id]/letra` já redireciona para `conclusao` se `sem_lyrics=True`
- Fonte `Inter_24pt-Bold.ttf` já está em `app-editor/backend/fonts/`
- `gancho_fontsize` e `cta_fontsize` já são lidos do `overlay_style` do perfil
- Admin panel (`brand-preview.tsx`) já tem `perfil.sigla !== 'RC'` para ocultar lyrics

**Parâmetros visuais RC (Brand Definition v1.0):**
- Fonte: `Inter_24pt-Bold.ttf`
- Gancho (1ª legenda): 52px
- Corpo (legendas do meio): 48px
- CTA (última legenda): 44px
- Cor: branco `#FFFFFF`
- Alinhamento: centralizado
- Posicionamento: base do texto 28px acima do topo da imagem

---

## Ordem de execução

1. T1 — Corrigir `overlay_style` do perfil RC no banco *(pré-requisito: garante parâmetros corretos antes do render)*
2. T2 — Adicionar suporte a `corpo_fontsize` em `legendas.py`
3. T3 — Auto-setar `sem_lyrics=True` na importação para perfil RC em `importar.py`
4. T4 — Validação end-to-end

---

## T1 — Corrigir overlay_style do perfil RC no banco

**Arquivo:** banco de dados PostgreSQL (Railway) via script SQL ou admin panel

**Problema:** O perfil RC foi criado copiando o perfil BO. O campo `overlay_style` provavelmente contém os valores do BO (TeX Gyre Schola, tamanhos diferentes). Precisa ser corrigido para os valores do Brand Definition RC.

**O que verificar primeiro:**
Executar no banco:
```sql
SELECT sigla, overlay_style, lyrics_style, traducao_style, font_name
FROM perfis
WHERE sigla = 'RC';
```

**O que o `overlay_style` deve conter após a correção:**
```json
{
  "fontname": "Inter Bold",
  "fontsize": 48,
  "gancho_fontsize": 52,
  "corpo_fontsize": 48,
  "cta_fontsize": 44,
  "primary_colour": "&H00FFFFFF",
  "outline": 0,
  "shadow": 0,
  "alignment": 2,
  "margin_v": 28
}
```

**O que os demais campos devem conter:**
- `lyrics_style`: `{}` (objeto vazio — RC instrumental não tem lyrics por padrão)
- `traducao_style`: `{}` (objeto vazio)
- `font_name`: `"Inter Bold"`

**Script de atualização:**
```sql
UPDATE perfis
SET
  overlay_style = '{"fontname":"Inter Bold","fontsize":48,"gancho_fontsize":52,"corpo_fontsize":48,"cta_fontsize":44,"primary_colour":"&H00FFFFFF","outline":0,"shadow":0,"alignment":2,"margin_v":28}',
  lyrics_style = '{}',
  traducao_style = '{}',
  font_name = 'Inter Bold'
WHERE sigla = 'RC';
```

**Critério de feito:**
- Query de verificação retorna os valores corretos
- `sigla = 'RC'` tem `overlay_style` com `corpo_fontsize: 48`, `gancho_fontsize: 52`, `cta_fontsize: 44`
- `lyrics_style` e `traducao_style` são objetos vazios ou nulos

---

## T2 — Adicionar `corpo_fontsize` em `legendas.py`

**Arquivo:** `app-editor/backend/app/services/legendas.py`

**Problema:** A função `gerar_ass()` já lê `gancho_fontsize` (aplica na 1ª legenda) e `cta_fontsize` (aplica na última), mas não lê `corpo_fontsize` para as legendas do meio. Sem isso, as legendas do corpo usam o `fontsize` padrão do perfil, sem a tag `{\fs48}`.

**Localizar o bloco atual (aproximadamente linhas 411-420):**
```python
gancho_fs = overlay_estilo.get("gancho_fontsize")
cta_fs = overlay_estilo.get("cta_fontsize")
```

E o loop onde as tags são aplicadas (procurar por `{\fs` ou `gancho_fs`).

**Padrão do código após a mudança:**
```python
gancho_fs = overlay_estilo.get("gancho_fontsize")
corpo_fs = overlay_estilo.get("corpo_fontsize")   # ADICIONAR
cta_fs = overlay_estilo.get("cta_fontsize")

# No loop que monta cada legenda:
if i == 0 and gancho_fs:
    texto_final = f"{{\\fs{gancho_fs}}}{texto_final}"
elif i == len(overlays) - 1 and cta_fs:
    texto_final = f"{{\\fs{cta_fs}}}{texto_final}"
elif corpo_fs:                                     # ADICIONAR
    texto_final = f"{{\\fs{corpo_fs}}}{texto_final}"  # ADICIONAR
```

**Impacto no BO:** Zero. O `overlay_style` do BO não tem `corpo_fontsize`, então `overlay_estilo.get("corpo_fontsize")` retorna `None` e o bloco `elif` não executa.

**Critério de feito:**
- Função aceita `corpo_fontsize` no JSON do perfil sem erros
- Em um render de teste RC com 3+ legendas: 1ª tem `{\fs52}`, as do meio têm `{\fs48}`, a última tem `{\fs44}`
- Um render BO de teste não é afetado (sem tags extras)

---

## T3 — Auto-setar `sem_lyrics=True` na importação para RC

**Arquivo:** `app-editor/backend/app/routes/importar.py`

**Problema:** Quando o operador importa um projeto do Redator para o Editor, o campo `sem_lyrics` é setado baseado apenas no parâmetro `eh_instrumental` enviado pelo frontend. Para o RC, esse parâmetro pode não ser enviado, fazendo o sistema tratar o projeto como se tivesse lyrics.

**Localizar o bloco atual (aproximadamente linhas 140-210):**
```python
if perfil_id:
    perfil = db.get(Perfil, perfil_id)
else:
    perfil = db.query(Perfil).filter(Perfil.sigla == "BO").first()

# ... mais abaixo ...
eh_instrumental=eh_instrumental,
sem_lyrics=eh_instrumental,
```

**Padrão do código após a mudança:**
```python
if perfil_id:
    perfil = db.get(Perfil, perfil_id)
else:
    perfil = db.query(Perfil).filter(Perfil.sigla == "BO").first()

# RC é sempre instrumental — sem_lyrics independente do parâmetro
eh_instrumental_final = eh_instrumental or (perfil is not None and perfil.sigla == "RC")

# ... onde cria a edicao ...
eh_instrumental=eh_instrumental_final,
sem_lyrics=eh_instrumental_final,
```

**Impacto no BO:** Zero. `perfil.sigla == "BO"` nunca ativa a condição. O `eh_instrumental` continua sendo passado normalmente para o BO.

**Critério de feito:**
- Importar um projeto com perfil RC seta `edicao.sem_lyrics = True` no banco
- Importar um projeto com perfil BO **não** seta `sem_lyrics = True` (a menos que `eh_instrumental=True` seja passado)
- Verificar via SQL após importação:
  ```sql
  SELECT id, perfil_id, sem_lyrics, eh_instrumental
  FROM edicoes
  WHERE perfil_id = (SELECT id FROM perfis WHERE sigla = 'RC')
  ORDER BY created_at DESC LIMIT 5;
  ```

---

## T4 — Validação end-to-end

Executar o fluxo completo do RC uma vez do início ao fim para confirmar que tudo funciona.

**Sequência de teste:**

1. **Dashboard:** Selecionar perfil RC no dropdown
2. **Redator:** Abrir um projeto RC existente (ou criar um novo)
3. **Overlay/Post/Tradução:** Confirmar que as etapas funcionam normalmente
4. **Exportar:** Confirmar que o `.srt` está disponível para download
5. **Avançar para Editor:** Clicar e confirmar que a edição é criada com `sem_lyrics=True`
6. **Editor — Letra:** Confirmar que a página redireciona automaticamente para Conclusão (não trava em letra/alinhamento)
7. **Editor — Conclusão:** Confirmar que o render é iniciado
8. **Render:** Confirmar que o vídeo final tem:
   - Overlay com Inter Bold
   - Gancho em 52px, corpo em 48px, CTA em 44px
   - Texto branco centralizado, 28px acima da imagem
   - **Sem** lyrics na barra inferior
9. **BO de controle:** Rodar uma edição BO e confirmar que o comportamento não mudou

**Critério de feito:**
- Vídeo RC renderizado com os parâmetros visuais corretos
- Nenhuma etapa de letra/alinhamento aparece para o RC
- Vídeo BO de controle renderiza normalmente sem alterações

---

## Arquivos afetados

| Arquivo | Tipo de mudança | Risco |
|---|---|---|
| Banco de dados — tabela `perfis`, linha do RC | UPDATE SQL | Baixo — só afeta perfil RC |
| `app-editor/backend/app/services/legendas.py` | +3 linhas (corpo_fontsize) | Muito baixo — aditivo, não quebra BO |
| `app-editor/backend/app/routes/importar.py` | +2 linhas (OR condition) | Baixo — aditivo, não quebra BO |

## Arquivos que NÃO precisam ser alterados

- `app-editor/backend/app/worker.py` — agnóstico ao perfil
- `app-editor/backend/app/routes/pipeline.py` — `sem_lyrics` já funciona
- `app-portal/components/editor/validate-lyrics.tsx` — já redireciona com `sem_lyrics`
- `app-portal/components/editor/conclusion.tsx` — já suporta `eh_instrumental`
- `app-portal/components/redator/export-page.tsx` — `.srt` já disponível
- Qualquer arquivo do frontend de redator — sem mudança no fluxo de conteúdo

---

## Notas de implementação

**Sobre o font_file no perfil RC:**
O campo `font_file_r2_key` (se existir no modelo) deve apontar para o arquivo `Inter_24pt-Bold.ttf`. Verificar se o pipeline do RC busca a fonte pelo `font_name` (nome lógico) ou pelo caminho no container. O arquivo já existe localmente em `app-editor/backend/fonts/Inter_24pt-Bold.ttf`.

**Sobre peças vocais do RC (exceção):**
O Brand Definition define que peças vocais do RC (oratórios, requiems) usam 3 camadas igual ao BO, mas com Inter BoldItalic. Esta exceção **não faz parte deste SPEC** — é um caso raro e pode ser tratado manualmente ou em SPEC futuro. Para este SPEC, todas as edições RC são tratadas como instrumentais (`sem_lyrics=True`).

**Sobre o overlay_style do BO:**
Não alterar. O BO continua com seus próprios parâmetros (TeX Gyre Schola, tamanhos BO, 3 tracks).
