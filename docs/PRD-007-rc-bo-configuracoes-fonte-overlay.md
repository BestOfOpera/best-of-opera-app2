# PRD-007 — Diagnóstico: Configurações RC vs BO, Fontes Pequenas e Overlay Duration

**Data:** 25/03/2026
**Baseado em:** sessão de diagnóstico 25/03 — análise de documentos de marca + código
**Status do ciclo: PENDENTE**

---

## 1. Contexto e ponto de partida

O usuário reportou que as **letras estavam muito pequenas** nos cortes de vídeo e que o **Reels Classics (RC) estava usando as configurações do Best of Opera (BO)**, o que é incorreto. A sessão foi usada para ler e cruzar todos os documentos de marca com o código atual, identificar divergências e listar o que precisa ser corrigido.

Também foi levantada a questão do **overlay duration** (BO = 10s, RC = 6s) e se o campo na UI admin realmente funciona.

---

## 2. Documentos lidos e analisados

### 2.1 Best of Opera — Brand Definition v1.0
**Arquivo:** `c:\Users\filip\Dev\Airas\BestOfOpera-BrandDefinition-v1.txt`

Especificações técnicas visuais do canal Best of Opera:

| Campo | Valor |
|---|---|
| Fonte | TeX Gyre Schola Bold Italic |
| Arquivo de fonte | `texgyreschola-bolditalic.otf` |
| Overlay Gancho (1ª legenda) | **46px** |
| Overlay Corpo (demais) | **44px** |
| Overlay CTA (última) | **44px** |
| Cor overlay | Branco #FFFFFF |
| Lyrics (letra cantada) | **32px**, amarelo #E4F042 |
| Tradução | **32px**, branco #FFFFFF |
| Gap overlay → imagem | 30px acima da imagem |
| Gap imagem → lyrics | 10px abaixo da imagem |
| Gap lyrics → tradução | 8px |
| Camadas de texto | **3**: overlay + lyrics + tradução |
| Resolução | 1080×1920px (9:16) |
| Outline/sombra | Nenhum (texto sobre faixa preta) |
| Alinhamento | Centralizado |

Valores validados por análise pixel-a-pixel de 7 frames de produção real e 15 cenários de tamanho de imagem.

### 2.2 Reels Classics — Content Bible v3.4
**Arquivo:** `c:\Users\filip\Dev\Airas\RC_ContentBible_v3_4-_2_.pdf`

Especificações de **conteúdo e técnicas** do canal Reels Classics:

| Campo | Valor |
|---|---|
| Fonte (CapCut) | **Inter SemiBold** |
| Canvas | 1080×1920px |
| Max linhas por legenda | **2 (absoluto, sem exceção)** |
| Max caracteres (PT/EN/ES/FR/IT) | **66** |
| Max caracteres (DE/PL) | **60** |
| Duração por legenda | **4–6s dinâmico** (frases curtas=4s, médias=5s, longas=6s) |
| CTA duration | Flexível ~20% do vídeo (~15s para 80s, ~10s para 50s) |
| Gap entre legendas | **ZERO** (contínuo, sem espaço) |
| Camadas de texto | **1** (overlay apenas — canal instrumental) |
| Workflow de edição | **CapCut manual** — SRT importado à mão |
| Idiomas de tradução | en, es, de, fr, it, pl |

**Ponto crítico identificado:** O RC **não usa o app-editor/FFmpeg** para renderizar legendas. O operador importa o `.srt` gerado pelo Claude diretamente no CapCut. Portanto, as configurações de fonte/tamanho no perfil RC do app-editor são usadas **somente pelo redator** para geração de conteúdo, não para renderização de vídeo.

### 2.3 Reels Classics — Instruções do Projeto Claude v3.4
**Arquivo:** `c:\Users\filip\Dev\Airas\RC_InstrucaoProjeto_v3_4-_1_.pdf`

Documento de instruções para o Claude no projeto de produção de conteúdo RC. Define:
- Pipeline sequencial de 7 etapas (confirmar dados → pesquisa → ângulos → overlay → descrição → automação → tradução)
- Regras absolutas de escrita (zero travessão, zero adjetivo vazio, zero marcas de IA)
- Regras de formato do `.srt` (apenas número, timestamp, texto puro, linha em branco)

### 2.4 Reels Classics — Content Bible v2.0 (versão anterior)
**Arquivo:** `c:\Users\filip\Dev\Airas\ReelsClassics-ContentBible-v2.txt`

Versão anterior do Content Bible RC. Ainda contém as regras de identidade e escopo, mas foi substituído pelo v3.4 que adicionou as regras técnicas de limite de caracteres e linhas.

### 2.5 Reels Classics — Manual do Operador v1.0
**Arquivo:** `c:\Users\filip\Dev\Airas\RC_Manual_Operador.pdf`

Guia prático para o operador humano. Confirma:
- **Workflow**: Claude gera SRT → operador importa no CapCut → aplica Inter SemiBold manualmente → exporta → publica
- **Limites técnicos** (Referência Rápida): 2 linhas máx, ~70 chars máx, 3–7s por legenda, CTA = 7s
- Etapa 5 explicitamente diz: "Aplique o estilo visual (Inter SemiBold, branco, centralizado)" — feito à mão no CapCut

> **Nota de inconsistência:** O Manual diz CTA = sempre 7s e range 3–7s; o Content Bible v3.4 diz CTA = ~20% do vídeo e range 4–6s. O v3.4 é o documento mais recente e deve ser a referência.

### 2.6 RC — Tradução de Legendas SRT
**Arquivo:** `c:\Users\filip\Dev\Airas\RC_Traducao_Legendas_SRT (1).md`

Instruções para um segundo projeto Claude dedicado à **retradução** de legendas que ultrapassam 2 linhas. Traduz para PL, IT, DE, FR. Limites: 33 chars por linha, 60–66 chars totais por bloco.

---

## 3. Arquivos de código investigados

### 3.1 Seed e backfill dos perfis
**Arquivo:** `best-of-opera-app2/app-editor/backend/app/main.py` (linhas 80–310)

**BUG CRÍTICO #1 — BO sobrescrito a cada startup:**
```python
# Linhas 227–240: UPDATE incondicional — executa a cada deploy/restart
UPDATE editor_perfis SET
    font_name = 'TeX Gyre Schola',
    overlay_style = :overlay_style,
    lyrics_style = :lyrics_style,
    traducao_style = :traducao_style
WHERE sigla = 'BO'
# Sem nenhuma condição de guarda → qualquer mudança feita na UI admin é apagada
```

**Seed RC — correto (idempotente):**
```python
# Linhas 282–305: INSERT só executa se RC não existir
INSERT INTO editor_perfis (...) SELECT ...
WHERE NOT EXISTS (SELECT 1 FROM editor_perfis WHERE sigla = 'RC')
```

**Valores atuais no seed do BO** (linhas 91–128):
- `fontname`: "TeX Gyre Schola" ✓ (correto conforme brand doc)
- `fontsize` corpo: **44** ✓
- `gancho_fontsize`: **46** ✓
- `cta_fontsize`: **44** ✓
- `lyrics fontsize`: **32** ✓
- `traducao fontsize`: **32** ✓
- `overlay_interval_secs`: **NÃO DEFINIDO** → herda default do banco = 6 ✗ (deveria ser 10)

**Valores atuais no seed do RC** (linhas 243–281):
- `fontname`: "Inter" ✓
- `fontsize` corpo: **48** (correto — maior que BO pois sans-serif)
- `gancho_fontsize`: **52**
- `cta_fontsize`: **44**
- `rc_lyrics_style fontsize`: **32** (não é usado — RC não tem lyrics)
- `overlay_interval_secs`: **NÃO DEFINIDO** → herda default = 6 ✓ (acidentalmente correto)
- `overlay_max_chars`: 70, `overlay_max_chars_linha`: 35 (mesmos do BO — deveria ser 66/33 conforme Content Bible)

### 3.2 Route admin de perfis
**Arquivo:** `best-of-opera-app2/app-editor/backend/app/routes/admin_perfil.py`

- `overlay_interval_secs` **existe** no schema `PerfilDetalheOut` (linha 123, default=6)
- O endpoint `PATCH /{perfil_id}` aceita qualquer campo via `body.items()` → **salvar funciona via API**
- **MAS: não há campo visível na UI do portal para editar `overlay_interval_secs`** → o operador não consegue alterar pela interface

**Defaults errados em `ESTILOS_PADRAO`** (linhas 34–53):
```python
# Usados quando se cria um perfil novo sem estilos definidos
"overlay": {"fontname": "Playfair Display", "fontsize": 63, ...}
"lyrics":  {"fontname": "Playfair Display", "fontsize": 45, ...}
"traducao":{"fontname": "Playfair Display", "fontsize": 43, ...}
```
Não corresponde a nenhum dos dois perfis (nem BO nem RC).

### 3.3 Modelo do perfil
**Arquivo:** `best-of-opera-app2/app-editor/backend/app/models/perfil.py` (linha 37)
```python
overlay_interval_secs = Column(Integer, default=6)
```
DB default = 6.

### 3.4 Prompt builder do redator
**Arquivo:** `best-of-opera-app2/app-redator/backend/prompts/overlay_prompt.py` (linha 48)
```python
interval_secs = (brand_config or {}).get("overlay_interval_secs", 15)  # default = 15
```
**BUG #4:** Default inconsistente — o DB usa 6, o prompt usa 15 como fallback.

### 3.5 Claude service do redator
**Arquivo:** `best-of-opera-app2/app-redator/backend/services/claude_service.py` (linha 232)
```python
interval_secs = (brand_config or {}).get("overlay_interval_secs", 6)  # default = 6
```
Inconsistente com o prompt builder (um usa 6, outro usa 15 como fallback).

### 3.6 Serviço de legendas
**Arquivo:** `best-of-opera-app2/app-editor/backend/app/services/legendas.py`

- Usa `ESTILOS_PADRAO` como fallback (overlay=40px, lyrics=30px, traducao=30px)
- `PlayResY=1920` → com esta resolução, fontsize ASS = pixels literais no vídeo
- Posicionamento dinâmico calculado a partir de `image_top_px`
- Lógica correta de recalcular `marginv` baseado na posição da imagem

### 3.7 Frontend — preview de marca
**Arquivo:** `best-of-opera-app2/app-portal/components/admin/brand-preview.tsx`

- Renderiza as 3 tracks (overlay, lyrics, tradução) sempre
- Para o RC, as tracks de lyrics e tradução aparecem com texto placeholder mesmo sem conteúdo
- Não há lógica para esconder tracks não usadas por perfil

---

## 4. Comparação completa: o que deveria ser vs. o que está no código

| Campo | BO (deveria) | BO (código) | RC (deveria) | RC (código) |
|---|---|---|---|---|
| Fonte | TeX Gyre Schola | TeX Gyre Schola ✓ | Inter | Inter ✓ |
| Overlay corpo px | 44 | 44 ✓ | ~48 (CapCut) | 48 ✓ |
| Overlay gancho px | 46 | 46 ✓ | ~52 (CapCut) | 52 ✓ |
| Lyrics px | 32 | 32 ✓ | N/A | 32 (irrelevante) |
| overlay_interval_secs | **10** | 6 ✗ | 6 | 6 ✓ |
| overlay_max_chars | 70 | 70 ✓ | **66** | 70 ✗ |
| overlay_max_chars_linha | 35 | 35 ✓ | **33** | 35 ✗ |
| Backfill startup | Não deveria | SIM ✗ | Não faz | Não faz ✓ |

---

## 5. Lista consolidada de problemas identificados

| # | Problema | Arquivo | Linha | Impacto |
|---|---|---|---|---|
| P1 | BO sobrescrito incondicionalmente a cada startup | `main.py` | 227–240 | Qualquer ajuste na UI admin some no próximo deploy |
| P2 | BO sem `overlay_interval_secs` definido | `main.py` | 148–173 | BO fica com 6s ao invés de 10s |
| P3 | RC `overlay_max_chars` errado (70 em vez de 66) | `main.py` | 297 | Redator pode gerar legendas com mais chars que o permitido |
| P4 | Default inconsistente `overlay_interval_secs` no prompt | `overlay_prompt.py` | 48 | Fallback usa 15s, mas DB usa 6s |
| P5 | `overlay_interval_secs` não exposto na UI admin | `app-portal` | — | Operador não consegue alterar pela interface |
| P6 | Fontes visualmente pequenas | `main.py` | 92–94 | 44px/48px em 1920px = 2.3–2.5% da tela — pequeno |
| P7 | `ESTILOS_PADRAO` em admin com Playfair Display 63px | `admin_perfil.py` | 34–53 | Defaults da UI não correspondem a nenhum perfil real |
| P8 | `brand-preview.tsx` mostra 3 tracks para RC | `brand-preview.tsx` | 109–127 | Preview enganoso para perfil sem lyrics/tradução |

---

## 6. Diferença fundamental de workflow: BO vs RC

### Best of Opera
```
Claude (redator) → .srt gerado → app-editor (FFmpeg) → ASS baked no vídeo
```
- O app-editor **renderiza** as legendas no vídeo via FFmpeg/libass
- As configurações do perfil (fonte, tamanho, posição) são aplicadas programaticamente
- O perfil BO no banco **controla a aparência final do vídeo**

### Reels Classics
```
Claude (projeto RC) → .srt gerado → operador importa no CapCut → aplica Inter SemiBold manualmente → exporta
```
- O app-editor **não é usado** para renderizar legendas RC
- As configurações do perfil RC no banco são usadas **apenas pelo redator** (para calcular max_chars, interval_secs, etc.)
- A aparência visual final é controlada manualmente no CapCut pelo operador

### Implicação para o frontend
- **Não é necessário criar um frontend separado para o RC**
- O app-portal multi-brand já serve ambos
- O portal precisa apenas de ajustes menores para o RC:
  - Expor `overlay_interval_secs` na UI admin
  - Corrigir `overlay_max_chars` para 66 no perfil RC
  - Opcionalmente esconder tracks de lyrics/tradução no preview RC

---

## 7. Documentos de referência para o SPEC

Para implementar as correções, os documentos de referência são:
- **BO Brand Definition v1:** `c:\Users\filip\Dev\Airas\BestOfOpera-BrandDefinition-v1.txt`
- **RC Content Bible v3.4:** `c:\Users\filip\Dev\Airas\RC_ContentBible_v3_4-_2_.pdf`
- **RC Manual do Operador:** `c:\Users\filip\Dev\Airas\RC_Manual_Operador.pdf`
- **PRD-006** (overlay timestamps): `best-of-opera-app2/docs/PRD-006-overlay-timestamps.md` — relacionado, não reabrir

---

## 8. O que NÃO foi alterado nesta sessão

**Nenhuma alteração foi feita no código.** Esta sessão foi puramente de diagnóstico e análise documental. Todas as correções estão pendentes para o SPEC-007.

---

## 9. Próximos passos sugeridos (para o SPEC-007)

1. **Corrigir backfill BO** — adicionar guarda no UPDATE (só executar se valores forem diferentes, ou remover e deixar só no INSERT)
2. **Definir `overlay_interval_secs`** explicitamente: BO = 10, RC = 6
3. **Corrigir `overlay_max_chars`** do RC: 66 chars, 33 por linha
4. **Corrigir default inconsistente** no `overlay_prompt.py` (15 → 6)
5. **Expor `overlay_interval_secs`** na UI admin do portal
6. **Avaliar aumento de fonte** — discutir com o usuário qual tamanho desejado antes de alterar
7. **Corrigir `ESTILOS_PADRAO`** no `admin_perfil.py` para refletir valores reais
8. **(Opcional) Esconder tracks de lyrics/tradução** no preview do RC no `brand-preview.tsx`
