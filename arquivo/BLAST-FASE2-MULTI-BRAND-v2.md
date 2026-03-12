# BLAST v4 — Fase 2: Multi-Brand + Infraestrutura (CORRIGIDO)

**Projeto:** Best of Opera — Multi-Brand Platform
**Data:** 10/03/2026
**Versao:** 4.1 (corrigido com valores reais do codebase)
**Pre-requisito:** Fase 1 (BLAST v3) concluida e em producao
**Protocolo:** BLAST Framework + Claude Code Agent Teams + Antigravity

---

## RESUMO EXECUTIVO

Transformar o sistema de "1 marca hardcoded" em "plataforma multi-marca". Qualquer pessoa pode criar um novo perfil de marca (como Reels Classics) sem mexer em codigo. Inclui autenticacao, stepper visual, e re-render/re-traducao individual.

**Mudanca principal v4.0 -> v4.1:**
- Valores de estilo corrigidos (extraidos do codigo real, nao inventados)
- Modelo Perfil usa JSON para estilos (nao 30+ colunas flat)
- Campos novos: editorial_lang, slug, r2_prefix, video_width, video_height
- Isolamento R2 por marca (prefixo no key)
- _detect_music_lang atualizado para aceitar language set do perfil
- Token em localStorage (decisao do Bolivar)
- Testes unitarios criticos incluidos
- Timeline ajustada para ser realista

---

## O QUE ENTRA

| Item | O que e | Custo |
|------|---------|-------|
| Multi-brand (Perfil) | Criar marcas novas sem mexer no codigo — tudo pela tela de admin | $0 |
| Admin de Marcas | Tela pra configurar nome, cores, fontes, idiomas, tom de voz, estilo de legenda | $0 |
| Autenticacao | Login simples — cada colaborador tem usuario e nivel de acesso | $0 |
| Stepper Visual | Barra de progresso no editor mostrando em que etapa o projeto esta | $0 |
| Re-render individual | Botao "Refazer" em cada idioma sem renderizar tudo de novo | $0 |
| Re-traducao individual | Corrigir traducao de 1 idioma sem refazer os 7 | $0 |
| Testes criticos | 5-8 testes unitarios para funcoes core do pipeline | $0 |

**Custo adicional: $0. Total mensal continua $70/mes.**

---

## ESTRATEGIA DE PARALELISMO

| Estrategia | Quando | Prompts |
|-----------|--------|---------|
| **Sessao unica** | Tarefas que editam pipeline.py + legendas.py + models | Prompt 1 |
| **Agent Teams** | Modulos NOVOS em arquivos separados | Prompt 2 |
| **Antigravity paralelo** | Frontend em componentes separados | Prompt 3 |

### Mapa de Conflitos de Arquivo

```
pipeline.py ——— Multi-brand (render por perfil) + Re-render/Re-traducao
                → SESSAO UNICA obrigatoria

legendas.py ——— Multi-brand (estilos dinamicos por marca)
                → Mesmo prompt que pipeline.py

models/edicao.py ——— Adicionar perfil_id (FK)
                     → Mesmo prompt

models/perfil.py (NOVO) ——— Teammate "admin"     ⎫
routes/admin_perfil.py (NOVO) ——— Teammate "admin" ⎬ AGENT TEAMS
models/usuario.py (NOVO) ——— Teammate "auth"       ⎬ (paralelo)
routes/auth.py (NOVO) ——— Teammate "auth"           ⎭
middleware/auth.py (NOVO) ——— Teammate "auth"       ⎭

components/admin/* (NOVO) → Antigravity Agente 1   ⎫
components/stepper/* (NOVO) → Antigravity Agente 1 ⎬ ANTIGRAVITY
components/auth/* (NOVO) → Antigravity Agente 2    ⎬ (paralelo)
components/re-render/* (NOVO) → Antigravity Agente 2⎭
```

---

## VALORES REAIS DO CODEBASE (referencia obrigatoria)

Estes valores foram extraidos diretamente do codigo em producao. Todo seed e default DEVE usar estes valores — nunca inventar.

```python
# legendas.py — ESTILOS_PADRAO (valores REAIS em producao)
ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "TeX Gyre Pagella",   # NAO "Georgia"
        "fontsize": 63,                    # NAO 47
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 3,
        "shadow": 1,
        "alignment": 2,                   # base (NAO 8/topo)
        "marginv": 1296,                  # NAO 490
        "bold": True,
        "italic": False,                  # NAO True
    },
    "lyrics": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 45,                    # NAO 35
        "primarycolor": "#FFFF64",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,
        "marginv": 573,
        "bold": True,
        "italic": True,
    },
    "traducao": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 43,                    # NAO 35
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 8,                   # topo (NAO 2)
        "marginv": 1353,                  # NAO 520
        "bold": True,
        "italic": True,
    },
}

# Limites de caracteres (valores REAIS)
OVERLAY_MAX_CHARS = 70
OVERLAY_MAX_CHARS_LINHA = 35
LYRICS_MAX_CHARS = 43
TRADUCAO_MAX_CHARS = 100

# Resolucao de video (valores REAIS)
PlayResX = 1080
PlayResY = 1920
FFmpeg: scale=1080:1920

# config.py
IDIOMAS_ALVO = ["en", "pt", "es", "de", "fr", "it", "pl"]

# importar.py
editorial_lang = "pt"
idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
```

---

## VISAO GERAL: 7 MEGA-PROMPTS

```
———————————————————————————————————————————————————————————
PROMPT 0 → Bolivar (Claude.ai)
         → Preencher definicoes do Reels Classics
         → 30 minutos (questionario interativo)
         → RODA EM PARALELO com Prompt 1
———————————————————————————————————————————————————————————
PROMPT 1 → Claude Code → Sessao Unica                    ✅ CONCLUIDO
         → Multi-brand backend + Re-render/Re-traducao + Testes
———————————————————————————————————————————————————————————
PROMPT 2 → Claude Code → AGENT TEAMS (2 teammates)       ✅ CONCLUIDO
         → Auth backend + Admin CRUD backend
———————————————————————————————————————————————————————————
PROMPT 1.5 → Claude Code → Sessao Unica                  ⬅️ PROXIMO
           → Unificar Perfil: campos de curadoria no editor
           → Curadoria le do editor via API (fallback JSON)
           → DEPENDE DOS PROMPTS 1+2, RODA ANTES DO PROMPT 3
           → ~1-2 dias
———————————————————————————————————————————————————————————
PROMPT 3 → Antigravity → Manager View (2 agentes)
         → Admin UI UNIFICADA (editor+curadoria) + Stepper + Auth UI + Re-render UI
         → ~5-7 dias
———————————————————————————————————————————————————————————
PROMPT 4 → Antigravity → Sessao Unica
         → Refinamento visual + Testes E2E via navegacao autonoma
         → ~2-3 dias
———————————————————————————————————————————————————————————
PROMPT 5 → Claude Code → Deploy + Seed
         → Deploy + validacao + seed do perfil padrao
         → ~1-2 dias
———————————————————————————————————————————————————————————

TOTAL ESTIMADO: ~19-27 dias (~3-4 semanas)
```

### Timeline Visual

```
Semana 1:  Prompt 0 (paralelo) + Prompt 1 (5-7 dias)     ✅
Semana 2:  Prompt 2 (3-4 dias)                            ✅
Semana 2+: Prompt 1.5 (1-2 dias)                          ⬅️ AGORA
Semana 3:  Prompt 3 (5-7 dias)
Semana 4:  Prompt 4 (2-3 dias) + Prompt 5 (deploy)
           Criar perfil Reels Classics via admin
```

---

---

# PROMPT 0 — Definicoes do Reels Classics (Claude.ai)

> **Quem faz:** Bolivar, no chat com Claude
> **Quando:** AGORA, em paralelo com os prompts tecnicos
> **Por que:** As definicoes ficam prontas pra colar no admin portal assim que ele estiver no ar

Basta dizer: **"Vamos preencher as definicoes do Reels Classics"** e eu conduzo um questionario interativo aqui mesmo. No final, gero o JSON completo pra importar no admin portal.

---

---

# PROMPT 1 — Claude Code (Sessao Unica)
## Multi-Brand Backend + Re-Render/Re-Traducao + Testes

> **Executor:** Claude Code (sessao unica — tudo edita os mesmos arquivos core)
> **Quem cola:** Bolivar ou Socio
> **Tempo estimado:** 5-7 dias
> **NAO usar Agent Teams aqui** — tarefas compartilham pipeline.py e legendas.py

```
## 🎯 OBJETIVO
Transformar o app-editor de "1 marca hardcoded" em "pipeline multi-brand dinamico" + adicionar endpoints de re-render e re-traducao individual por idioma + testes unitarios criticos. Tudo em sessao unica sequencial.

## 📚 CONTEXTO
O Best of Opera Editor processa videos com estilos hardcoded: fontes, cores, margens de legenda, idiomas-alvo, tudo fixo no codigo. Vamos criar um modelo Perfil no banco que armazena TODA a configuracao de uma marca. O pipeline le do perfil em vez de constantes hardcoded.

IMPORTANTE: Todos os blocos editam pipeline.py, legendas.py ou models/edicao.py. Por isso executamos tudo em sessao unica sequencial — sem agent teams, sem subagents.

Estrategia de execucao: SESSAO UNICA SEQUENCIAL.

## ✅ TAREFAS (6 blocos sequenciais)

### BLOCO 1 — Modelo Perfil (a "ficha" de cada marca)

1. Criar `app-editor/backend/app/models/perfil.py`:

```python
class Perfil(Base):
    __tablename__ = "editor_perfis"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), unique=True, nullable=False)  # "Best of Opera"
    sigla = Column(String(5), nullable=False)  # "BO"
    slug = Column(String(50), unique=True, nullable=False)  # "best-of-opera" (URL-safe, prefixo R2)
    ativo = Column(Boolean, default=True)

    # Identidade
    identity_prompt = Column(Text)  # como a IA entende a marca
    tom_de_voz = Column(Text)  # descricao do tom editorial
    editorial_lang = Column(String(5), default="pt")  # idioma dos overlays/posts/SEO
    hashtags_fixas = Column(JSON, default=list)  # ["#BestOfOpera", "#Opera"]
    categorias_hook = Column(JSON, default=list)  # ["Emotional", "Historical"]

    # Idiomas
    idiomas_alvo = Column(JSON, default=list)  # ["en","pt","es","de","fr","it","pl"]
    idioma_preview = Column(String(5), default="pt")

    # Estilos de legenda — JSON (mesma estrutura do ESTILOS_PADRAO)
    overlay_style = Column(JSON, default=dict)
    lyrics_style = Column(JSON, default=dict)
    traducao_style = Column(JSON, default=dict)

    # Limites de caracteres
    overlay_max_chars = Column(Integer, default=70)
    overlay_max_chars_linha = Column(Integer, default=35)
    lyrics_max_chars = Column(Integer, default=43)
    traducao_max_chars = Column(Integer, default=100)

    # Video — prever dimensoes futuras, so implementar 9:16 agora
    video_width = Column(Integer, default=1080)
    video_height = Column(Integer, default=1920)

    # Curadoria
    escopo_conteudo = Column(Text)  # o que entra e nao entra
    duracao_corte_min = Column(Integer, default=30)
    duracao_corte_max = Column(Integer, default=90)

    # Visual
    cor_primaria = Column(String(10), default="#1a1a2e")
    cor_secundaria = Column(String(10), default="#e94560")

    # R2 — prefixo para isolar storage entre marcas
    r2_prefix = Column(String(100), default="editor")  # R2 key: {r2_prefix}/{r2_base}/...

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

2. Adicionar migration em `_run_migrations()` do main.py:
   - CREATE TABLE IF NOT EXISTS editor_perfis
   - Se tabela vazia: INSERT do perfil "Best of Opera" com valores EXATOS do ESTILOS_PADRAO atual (ver secao "VALORES REAIS" acima)
   - USAR `INSERT INTO editor_perfis (...) SELECT ... WHERE NOT EXISTS (SELECT 1 FROM editor_perfis WHERE sigla='BO')` para idempotencia (NAO assumir id=1)
   - ALTER TABLE editor_edicoes ADD COLUMN perfil_id INTEGER REFERENCES editor_perfis(id) — se nao existir
   - UPDATE editor_edicoes SET perfil_id = (SELECT id FROM editor_perfis WHERE sigla='BO') WHERE perfil_id IS NULL

3. O seed do perfil "Best of Opera" DEVE usar estes valores EXATOS:

```python
SEED_BEST_OF_OPERA = {
    "nome": "Best of Opera",
    "sigla": "BO",
    "slug": "best-of-opera",
    "editorial_lang": "pt",
    "idiomas_alvo": ["en", "pt", "es", "de", "fr", "it", "pl"],
    "idioma_preview": "pt",
    "overlay_style": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 63,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 3,
        "shadow": 1,
        "alignment": 2,
        "marginv": 1296,
        "bold": True,
        "italic": False,
    },
    "lyrics_style": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 45,
        "primarycolor": "#FFFF64",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,
        "marginv": 573,
        "bold": True,
        "italic": True,
    },
    "traducao_style": {
        "fontname": "TeX Gyre Pagella",
        "fontsize": 43,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 8,
        "marginv": 1353,
        "bold": True,
        "italic": True,
    },
    "overlay_max_chars": 70,
    "overlay_max_chars_linha": 35,
    "lyrics_max_chars": 43,
    "traducao_max_chars": 100,
    "video_width": 1080,
    "video_height": 1920,
    "r2_prefix": "editor",
    "cor_primaria": "#1a1a2e",
    "cor_secundaria": "#e94560",
    "duracao_corte_min": 30,
    "duracao_corte_max": 90,
}
```

4. Adicionar `perfil_id` ao modelo Edicao (models/edicao.py):
   - `perfil_id = Column(Integer, ForeignKey("editor_perfis.id"), nullable=True)`
   - Nullable pra nao quebrar edicoes existentes

5. Atualizar schemas.py:
   - PerfilOut, PerfilCreate, PerfilUpdate
   - EdicaoOut: adicionar perfil_id e perfil_nome (via join ou property)

### BLOCO 2 — Pipeline multi-brand (legendas dinamicas)

1. Ler `app-editor/backend/app/services/legendas.py`

2. Criar funcao que converte campos JSON do Perfil para o dict de estilos:

```python
def _estilos_do_perfil(perfil) -> dict:
    """Converte campos JSON do Perfil para dict de estilos ASS.
    Retorna estrutura identica a ESTILOS_PADRAO."""
    return {
        "overlay": perfil.overlay_style or ESTILOS_PADRAO["overlay"],
        "lyrics": perfil.lyrics_style or ESTILOS_PADRAO["lyrics"],
        "traducao": perfil.traducao_style or ESTILOS_PADRAO["traducao"],
    }
```

3. Modificar `gerar_ass()`: aceitar `perfil` como parametro opcional
   - Se perfil fornecido: usar `_estilos_do_perfil(perfil)`
   - Se nao: usar ESTILOS_PADRAO (retrocompatibilidade)
   - Para limites de caracteres: usar `perfil.overlay_max_chars` etc se disponivel
   - Para PlayResX/Y: usar `perfil.video_width` e `perfil.video_height` se disponivel

4. No `_render_task` em pipeline.py:
   - Antes do loop de render: carregar perfil da edicao (sessao curta)
   - Passar perfil para `gerar_ass()`
   - Usar `perfil.idiomas_alvo` em vez de `IDIOMAS_ALVO` da config
   - Usar `perfil.video_width` e `perfil.video_height` no FFmpeg scale/pad (em vez de 1080:1920 hardcoded)
   - Usar `perfil.r2_prefix` no R2 key (em vez de "editor" hardcoded)
   - FALLBACK: se perfil is None, usar IDIOMAS_ALVO e valores hardcoded atuais

5. No `_traducao_task`:
   - Carregar perfil para obter `idiomas_alvo`
   - Traduzir somente para os idiomas da marca (nao IDIOMAS_ALVO hardcoded)
   - FALLBACK: se perfil is None, usar IDIOMAS_ALVO

6. No endpoint `renderizar-preview`:
   - Usar `perfil.idioma_preview` em vez de logica hardcoded "pt"
   - FALLBACK: se perfil is None, manter logica atual

7. No endpoint `aprovar-preview`:
   - Usar `perfil.idiomas_alvo` e `perfil.idioma_preview` para calcular idiomas restantes
   - Em vez de `IDIOMAS_ALVO` hardcoded

8. Na importacao (`importar.py`):
   - Novo parametro opcional: `?perfil_id=X`
   - Se nao informado: usar perfil com sigla "BO" (Best of Opera) como padrao
   - Salvar perfil_id na edicao criada
   - Usar `perfil.editorial_lang` em vez de `editorial_lang = "pt"` hardcoded
   - Usar `perfil.idioma_preview` em vez de logica hardcoded
   - Atualizar `_detect_music_lang()`: aceitar `idiomas_alvo` do perfil como parametro
     em vez de `all_target = {"en","pt","es","de","fr","it","pl"}` hardcoded

9. Isolamento R2 por marca:
   - Na funcao `_get_r2_base(edicao)` (ou onde monta o R2 key):
     carregar perfil.r2_prefix e usar como prefixo
   - Resultado: `{perfil.r2_prefix}/{artista} - {musica}/...`
   - Perfil "Best of Opera" mantem r2_prefix="editor" (compatibilidade com arquivos existentes)

10. Manter ESTILOS_PADRAO e IDIOMAS_ALVO como fallback — se perfil_id is None, comportamento IDENTICO ao atual

### BLOCO 3 — Re-render individual por idioma

1. Criar endpoint `POST /edicoes/{id}/re-renderizar/{idioma}`:
   - Carregar perfil da edicao
   - Validar que idioma esta nos `perfil.idiomas_alvo` (ou IDIOMAS_ALVO se sem perfil)
   - Check-and-set atomico: status deve ser "concluido", "preview_pronto" ou "erro"
   - Setar status="renderizando"
   - Deletar render anterior: DELETE FROM editor_renders WHERE edicao_id=X AND idioma=Y
   - Criar wrapper que chama `_render_task(edicao_id, idiomas_renderizar=[idioma])`
   - Enfileirar no task_queue
   - Retornar {"status": "re-render enfileirado", "idioma": idioma}

2. Progresso: `progresso_detalhe["re_render"] = {"idioma": idioma, "status": "em_andamento"}`

3. Apos render concluido: restaurar status anterior (concluido ou preview_pronto)

### BLOCO 4 — Re-traducao individual por idioma

1. Criar endpoint `POST /edicoes/{id}/re-traduzir/{idioma}`:
   - Carregar perfil da edicao
   - Validar idioma nos `perfil.idiomas_alvo`
   - Check-and-set atomico: status deve ser "montagem", "preview_pronto", "concluido" ou "erro"
   - Guardar status_anterior antes de mudar
   - Deletar traducao anterior: DELETE FROM editor_traducoes_letras WHERE edicao_id=X AND idioma=Y
   - Setar status="traducao"
   - Criar wrapper que traduz APENAS esse idioma
   - Enfileirar no task_queue
   - Apos traducao: status volta ao status_anterior

2. Progresso: `progresso_detalhe["re_traducao"] = {"idioma": idioma, "status": "em_andamento"}`

### BLOCO 5 — Testes unitarios criticos

Criar `app-editor/backend/tests/test_multi_brand.py`:

1. **test_estilos_do_perfil_retorna_padrao_quando_none**: verificar que _estilos_do_perfil com campos None retorna ESTILOS_PADRAO
2. **test_estilos_do_perfil_retorna_custom**: verificar que overlay_style custom e retornado corretamente
3. **test_seed_best_of_opera_valores_corretos**: verificar que o seed gera perfil com valores identicos ao ESTILOS_PADRAO
4. **test_gerar_ass_com_perfil_custom**: chamar gerar_ass com perfil que tem fontsize diferente e verificar output ASS
5. **test_gerar_ass_sem_perfil_retrocompativel**: chamar gerar_ass sem perfil e verificar output identico ao comportamento atual
6. **test_detect_music_lang_com_idiomas_custom**: testar _detect_music_lang com set de 4 idiomas em vez de 7
7. **test_perfil_slug_unico**: verificar constraint unique no slug
8. **test_edicao_perfil_nullable**: verificar que edicao sem perfil_id funciona (retrocompatibilidade)

Usar pytest. Criar conftest.py com fixture de banco in-memory (sqlite) se nao existir.

### BLOCO 6 — Retrocompatibilidade e finalizacao

1. Verificar que TODOS os caminhos de codigo funcionam com perfil_id=None:
   - _render_task: usa IDIOMAS_ALVO
   - _traducao_task: usa IDIOMAS_ALVO
   - renderizar-preview: usa "pt"
   - importar: usa "BO" como perfil padrao
   - gerar_ass: usa ESTILOS_PADRAO
   - R2 key: usa "editor" como prefixo

2. Rodar testes: `cd app-editor/backend && python -m pytest tests/ -v`

3. Atualizar HISTORICO-ERROS-CORRECOES-APP-EDITOR.md com:
   - ERR-063: Sistema hardcoded para 1 marca → modelo Perfil multi-brand
   - ERR-064: Impossivel re-renderizar 1 idioma sem refazer todos → endpoint individual
   - ERR-065: Impossivel re-traduzir 1 idioma sem refazer todos → endpoint individual
   - ERR-066: Idiomas-alvo e preview hardcoded → configuravel por perfil
   - ERR-067: editorial_lang hardcoded "pt" → configuravel por perfil
   - ERR-068: R2 keys sem isolamento entre marcas → prefixo por perfil

4. Atualizar MEMORIA-VIVA.md

5. NAO fazer git push — preparar commit: "feat: BLAST v4 — multi-brand backend + re-render/re-traducao individual + testes"

## 📁 ARQUIVOS RELEVANTES
- `app-editor/backend/app/models/perfil.py` — CRIAR
- `app-editor/backend/app/models/edicao.py` — EDITAR (perfil_id)
- `app-editor/backend/app/models/__init__.py` — EDITAR (import Perfil)
- `app-editor/backend/app/routes/pipeline.py` — EDITAR (brand-aware + re-render + re-traducao)
- `app-editor/backend/app/routes/importar.py` — EDITAR (perfil_id + editorial_lang + detect_music_lang)
- `app-editor/backend/app/services/legendas.py` — EDITAR (estilos dinamicos + limites dinamicos)
- `app-editor/backend/app/schemas.py` — EDITAR (novos schemas)
- `app-editor/backend/app/main.py` — EDITAR (migration + seed)
- `app-editor/backend/app/config.py` — LER (manter IDIOMAS_ALVO como fallback)
- `app-editor/backend/tests/test_multi_brand.py` — CRIAR
- `app-editor/backend/tests/conftest.py` — CRIAR (se nao existir)
- `HISTORICO-ERROS-CORRECOES-APP-EDITOR.md`
- `MEMORIA-VIVA.md`

## ⚙️ REGRAS
- NAO usar Agent Teams nem subagents — sessao unica sequencial
- Executar blocos na ordem (1 → 2 → 3 → 4 → 5 → 6)
- Nao perguntar ao Bolivar sobre detalhes tecnicos — decida sozinho
- So pedir aprovacao antes de fazer git push
- Imports dentro do try-except (padrao do projeto)
- Sessoes curtas de banco
- except BaseException (nao so Exception)
- Retrocompatibilidade total — sistema DEVE funcionar igual ao atual sem perfil
- Seed com WHERE NOT EXISTS (idempotencia — nao assumir id=1)
- Valores do seed DEVEM ser identicos ao ESTILOS_PADRAO real (ver secao "VALORES REAIS")

## 🎁 ENTREGA
Pipeline multi-brand funcional: modelo Perfil com estilos JSON, idiomas e configuracao por marca. Seed automatico do perfil "Best of Opera" com valores IDENTICOS ao codigo atual. Endpoints de re-render e re-traducao individual por idioma. Edicoes existentes migradas. R2 isolado por marca. 8 testes unitarios passando. Tudo retrocompativel.
```

*Cole direto no Claude Code. Prompt longo mas sequencial — ele executa bloco a bloco.*

---

---

# PROMPT 2 — Claude Code (Agent Teams)
## Auth Backend + Admin CRUD em paralelo

> **Executor:** Claude Code com **Agent Teams habilitado**
> **Quem cola:** Bolivar ou Socio
> **Tempo estimado:** 3-4 dias
> **Pre-requisito:** Prompt 1 concluido (modelo Perfil existe no banco)
> **AGENT TEAMS:** 2 teammates + 1 lead — arquivos NOVOS separados

```
## 🎯 OBJETIVO
Criar o sistema de autenticacao (login/roles) E o CRUD administrativo de perfis de marca, usando Agent Teams com 2 teammates em paralelo. Cada um cria arquivos NOVOS sem conflito.

Crie um Agent Team para implementar os dois modulos em paralelo.

## 📚 CONTEXTO
O Prompt 1 ja criou o modelo Perfil e tornou o pipeline multi-brand. Agora precisamos de: (1) sistema de login simples para colaboradores, e (2) tela de admin para criar/editar marcas.

Stack: FastAPI, PostgreSQL, Next.js. Deploy: Railway.
O modelo Perfil JA EXISTE em `app-editor/backend/app/models/perfil.py` — NAO recriar.
Os estilos de legenda sao campos JSON (overlay_style, lyrics_style, traducao_style) — NAO colunas flat.

## 👥 ESTRUTURA DO AGENT TEAM

### Lead (Coordenador)
- Distribui tarefas para os 2 teammates
- NAO implementa codigo — so coordena
- Apos AMBOS terminarem:
  - Registra os 2 novos routers no `main.py`
  - Adiciona migration de criacao da tabela `editor_usuarios`
  - Adiciona schemas novos ao `schemas.py` (ATENCAO: so o Lead edita schemas.py, nenhum teammate)
  - Seed do usuario admin padrao
  - Atualiza HISTORICO-ERROS-CORRECOES-APP-EDITOR.md
  - Roda testes
  - Prepara commit (SEM git push)

### Teammate "auth"
- **OWNS (so ele edita):**
  - `app-editor/backend/app/models/usuario.py` (CRIAR NOVO)
  - `app-editor/backend/app/routes/auth.py` (CRIAR NOVO)
  - `app-editor/backend/app/middleware/auth.py` (CRIAR NOVO)
- **PODE LER (nao editar):** `models/perfil.py`, `config.py`, `database.py`, `schemas.py`
- **Tarefa:** Sistema de autenticacao completo (detalhes abaixo)
- **Entrega:** Login funcional com JWT + roles
- **Schemas necessarios (informar ao Lead):** UsuarioCreate, UsuarioOut, UsuarioUpdate, LoginRequest, TokenResponse

### Teammate "admin"
- **OWNS (so ele edita):**
  - `app-editor/backend/app/routes/admin_perfil.py` (CRIAR NOVO)
- **PODE LER (nao editar):** `models/perfil.py`, `schemas.py`, `database.py`
- **Tarefa:** CRUD completo de perfis de marca (detalhes abaixo)
- **Entrega:** API REST para gerenciar marcas
- **Schemas necessarios (informar ao Lead):** PerfilCreate, PerfilUpdate, PerfilOut, PerfilListItem, PerfilStats, PerfilPreviewLegenda

### IMPORTANTE: schemas.py
O Lead edita schemas.py DEPOIS de ambos teammates terminarem, reunindo os schemas que cada um precisa. Nenhum teammate edita schemas.py diretamente — eles definem schemas inline (Pydantic) nos seus arquivos e o Lead consolida.

## 📋 TASK LIST (dependencias)

```
1. [Teammate auth] Criar modelo Usuario + rotas de auth + middleware — SEM DEPENDENCIA
2. [Teammate admin] Criar CRUD de perfis — SEM DEPENDENCIA
3. [Lead] Consolidar schemas no schemas.py — DEPENDE DE 1 e 2
4. [Lead] Registrar routers no main.py — DEPENDE DE 1 e 2
5. [Lead] Migration da tabela editor_usuarios — DEPENDE DE 1
6. [Lead] Seed do usuario admin padrao — DEPENDE DE 1 e 5
7. [Lead] Atualizar HISTORICO e MEMORIA-VIVA — DEPENDE DE 1, 2
```

---

## 📦 BRIEFING COMPLETO PARA TEAMMATE "auth"

Criar sistema de autenticacao simples para o Best of Opera Editor. NAO precisa de OAuth nem SSO — e login com email + senha + JWT.

### Modelo — `models/usuario.py`
```python
class Usuario(Base):
    __tablename__ = "editor_usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    senha_hash = Column(String(500), nullable=False)
    role = Column(String(20), default="operador")  # "admin" ou "operador"
    ativo = Column(Boolean, default=True)
    ultimo_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Roles:**
- `admin`: acesso total — pode criar/editar marcas, gerenciar usuarios, ver dashboard completo
- `operador`: acesso ao editor e dashboard — pode processar videos, criar reports, mas NAO pode editar perfis de marca nem gerenciar usuarios

### Rotas — `routes/auth.py`
Router prefix: `/api/v1/editor/auth`, tags=["auth"]

**POST /login** — Email + senha → retorna JWT token
- Token expira em 24h
- Payload: {user_id, email, nome, role, exp}
- Atualizar `ultimo_login`
- Se credenciais invalidas: 401

**POST /registrar** — Criar novo usuario (SOMENTE admins podem)
- Body: nome, email, senha, role
- Senha salva como hash (bcrypt)
- Se email ja existe: 409

**GET /me** — Retorna dados do usuario logado
- Requer token valido no header Authorization: Bearer {token}

**PATCH /usuarios/{id}** — Atualizar usuario (admin only)
- Pode: mudar nome, email, role, ativo
- NAO pode: mudar proprio role (protecao)

**GET /usuarios** — Listar todos (admin only)

### Middleware — `middleware/auth.py`
- Funcao `get_current_user(token)` que decodifica JWT
- Funcao `require_admin(user)` que verifica role == "admin"
- Dependency injection do FastAPI: `current_user = Depends(get_current_user)`

### Dependencias (pip)
- `python-jose[cryptography]` para JWT
- `passlib[bcrypt]` para hash de senha
- Adicionar ao requirements.txt

### Config
- Usar `SECRET_KEY` que ja existe em config.py para assinar JWT (ja tem valor default)
- Variavel `JWT_EXPIRY_HOURS` default 24 — adicionar em config.py

**Regras:**
- SOMENTE LEITURA nos arquivos que nao sao seus
- Hash bcrypt SEMPRE — nunca salvar senha em texto
- Token JWT no header, nao em cookie
- 401 para token invalido/expirado, 403 para permissao insuficiente

---

## 📦 BRIEFING COMPLETO PARA TEAMMATE "admin"

Criar CRUD completo para gerenciar perfis de marca. O modelo Perfil JA EXISTE — voce so cria as rotas.

IMPORTANTE: Os estilos de legenda sao 3 campos JSON (overlay_style, lyrics_style, traducao_style), NAO colunas individuais. Cada campo e um dict com keys: fontname, fontsize, primarycolor, outlinecolor, outline, shadow, alignment, marginv, bold, italic.

### Rotas — `routes/admin_perfil.py`
Router prefix: `/api/v1/editor/admin/perfis`, tags=["admin-perfis"]

**GET /** — Listar todos os perfis
- Retorna: lista com id, nome, sigla, slug, ativo, idiomas_alvo, cor_primaria, cor_secundaria, created_at
- Ordenar por nome
- Inclui contagem de edicoes por perfil (subquery COUNT)

**GET /{id}** — Detalhe completo do perfil
- TODOS os campos do modelo (incluindo os 3 JSON de estilos)
- Inclui stats: total_edicoes, concluidas, em_andamento, em_erro

**POST /** — Criar novo perfil
- Body: todos os campos do modelo (exceto id, created_at, updated_at)
- Validar: nome, sigla e slug unicos
- Se duplicado: 409 com mensagem clara
- Defaults inteligentes: se overlay_style nao fornecido, usar ESTILOS_PADRAO["overlay"] como default
- Gerar slug automaticamente do nome se nao fornecido (slugify)

**PUT /{id}** — Atualizar perfil completo
- Todos os campos editaveis
- NAO permitir mudar nome/sigla do perfil com sigla "BO" (Best of Opera e protegido)
- Retorna perfil atualizado

**PATCH /{id}** — Atualizar campos individuais
- Body parcial: so os campos que mudam
- Mesma protecao do "BO"

**POST /{id}/duplicar** — Duplicar perfil como base
- Cria novo perfil copiando TODOS os valores do perfil original
- Altera nome para "{nome_original} (copia)" e sigla para "{sigla}2"
- Gera novo slug: "{slug_original}-copia"
- Gera novo r2_prefix baseado no slug
- Util para criar Reels Classics a partir do Best of Opera e so ajustar o que difere

**GET /{id}/preview-legenda** — Preview de como ficam as legendas
- Retorna JSON com os 3 estilos (overlay + lyrics + traducao) do perfil
- Inclui os limites de caracteres e dimensoes do video
- Frontend usa para montar preview visual

**Regras:**
- Tags: ["admin-perfis"]
- Perfil com sigla "BO" (Best of Opera) e protegido: nao pode ser deletado nem renomeado
- Se perfil tem edicoes vinculadas: nao pode ser deletado (soft delete via campo `ativo`)
- Validar cores como hex (#RRGGBB)
- Validar idiomas como codigos de 2 letras
- NAO editar schemas.py — definir schemas inline no arquivo e informar o Lead

---

## ⚙️ REGRAS GERAIS
- Nao perguntar ao Bolivar sobre detalhes tecnicos — decidam sozinhos
- Cada teammate edita SOMENTE seus arquivos owned
- NENHUM teammate edita schemas.py — o Lead faz isso no final
- Lead NAO implementa — so coordena e integra no final
- Se teammate precisar de info do outro: usar mailbox do Agent Teams
- So pedir aprovacao do Bolivar antes de git push
- Lead cria seed do usuario admin padrao no _run_migrations:
  - Email: admin@bestofopera.com
  - Senha: `BestOfOpera2026!` (senha simples, trocar apos primeiro login)
  - Role: admin
  - Usar INSERT ... WHERE NOT EXISTS (idempotencia)
  - Avisar no log se ja existe
- Preparar commit: "feat: BLAST v4 — auth + admin perfis"

## 🎁 ENTREGA
2 modulos backend completos: Auth (login JWT + roles admin/operador) + Admin CRUD de Perfis (listar, criar, editar, duplicar, preview). Routers registrados no main.py. Migration da tabela editor_usuarios. Schemas consolidados. Seed do admin padrao. HISTORICO atualizado. Commit preparado (sem push).
```

*Cole direto no Claude Code. Ele cria o Agent Team e divide o trabalho automaticamente.*

---

---

# PROMPT 1.5 — Claude Code (Sessao Unica)
## Unificar Perfil: campos de curadoria no modelo do editor + curadoria lendo do Perfil

> **Executor:** Claude Code (sessao unica)
> **Quem cola:** Bolivar
> **Tempo estimado:** 1-2 dias
> **Pre-requisito:** Prompts 1 e 2 concluidos (modelo Perfil + auth existem)
> **DEVE rodar ANTES do Prompt 3** (frontend precisa do modelo unificado pra montar tela completa)

### Por que este prompt existe

O Prompt 1 criou o modelo Perfil com campos do **editor** (legendas, idiomas, cores).
A curadoria tem seus proprios dados (categories, elite_hits, scoring_weights, etc.) num **JSON avulso** (`data/best-of-opera.json`).
Se o Prompt 3 criar a tela de admin sem unificar, o operador teria que configurar a marca em **dois lugares** — isso quebra o objetivo "tudo numa tela so".

### O que fazer

```
## CONTEXTO
O modelo Perfil (app-editor/backend/app/models/perfil.py) ja tem campos do editor.
A curadoria le tudo de um JSON em app-curadoria/backend/data/best-of-opera.json.
O objetivo e que o operador configure TUDO (editor + curadoria) num unico Perfil no banco.

## TAREFAS (executar em ordem)

### TAREFA 1 — Adicionar campos de curadoria ao modelo Perfil do editor

Arquivo: app-editor/backend/app/models/perfil.py

Adicionar estes campos JSON ao modelo Perfil (todos com default vazio ou copiado do best-of-opera.json):

    # Curadoria — categorias e seeds de busca
    curadoria_categories = Column(JSON, default=dict)
    # Estrutura: {"icones": {"name": "Icones", "emoji": "👑", "desc": "...", "seeds": [...]}, ...}

    # Curadoria — listas de scoring
    elite_hits = Column(JSON, default=list)        # ["Nessun Dorma", "Ave Maria", ...]
    power_names = Column(JSON, default=list)        # ["Luciano Pavarotti", ...]
    voice_keywords = Column(JSON, default=list)     # ["live", "voice", ...]
    institutional_channels = Column(JSON, default=list)  # ["met opera", ...]
    category_specialty = Column(JSON, default=dict) # {"icones": ["pavarotti", ...], ...}

    # Curadoria — pesos do scoring V7
    scoring_weights = Column(JSON, default=dict)
    # Estrutura: {"elite_hit": 15, "power_name": 15, "specialty": 25, ...}

    # Curadoria — filtros
    curadoria_filters = Column(JSON, default=dict)  # {"duracao_max": 600}

    # Curadoria — anti-spam
    anti_spam_terms = Column(String(500), default="-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords")

    # Curadoria — playlist
    playlist_id = Column(String(100), default="")

NAO renomear campos existentes. NAO remover nada.

### TAREFA 2 — Atualizar seed do Perfil "Best of Opera"

Arquivo: app-editor/backend/app/main.py (ou onde o seed roda)

Ao criar o perfil BO padrao, popular os novos campos com os valores EXATOS do arquivo app-curadoria/backend/data/best-of-opera.json.

### TAREFA 3 — Atualizar admin_perfil.py para aceitar campos de curadoria

Arquivo: app-editor/backend/app/routes/admin_perfil.py

Os endpoints PUT e POST ja devem aceitar os novos campos no body.
O endpoint POST /{id}/duplicar deve copiar os campos de curadoria tambem.
Adicionar GET /{id}/curadoria-config que retorna SOMENTE os campos de curadoria do perfil (formato compativel com o JSON que a curadoria espera).

### TAREFA 4 — Criar endpoint interno no editor para curadoria consumir

Arquivo: app-editor/backend/app/routes/admin_perfil.py (ou novo arquivo routes/internal.py)

Endpoint: GET /api/internal/perfil/{slug}/curadoria-config
- NAO exige auth (comunicacao interna entre servicos)
- Retorna JSON no formato que a curadoria espera:
  {
    "name": "Best of Opera",
    "project_id": "best-of-opera",
    "categories": {...},
    "elite_hits": [...],
    "power_names": [...],
    "voice_keywords": [...],
    "institutional_channels": [...],
    "category_specialty": {...},
    "scoring_weights": {...},
    "filters": {...}
  }

### TAREFA 5 — Curadoria: ler config do editor via API em vez de JSON local

Arquivo: app-curadoria/backend/config.py

Alterar load_brand_config() para:
1. Tentar buscar de http://{EDITOR_API_URL}/api/internal/perfil/{slug}/curadoria-config
2. Se falhar (editor offline, erro de rede), fallback para JSON local (manter comportamento atual)
3. Nova env var: EDITOR_API_URL (default: "http://localhost:8000")
4. Nova env var: BRAND_SLUG (default: "best-of-opera")

Arquivo: app-curadoria/backend/routes/curadoria.py

Em vez de importar BRAND_CONFIG global no topo, chamar load_brand_config() a cada request (ou cachear com TTL de 5 min).
Isso permite que mudancas no admin reflitam na curadoria sem restart.

### TAREFA 6 — Deletar modelo Pydantic avulso da curadoria

Arquivo: app-curadoria/backend/models/perfil_curadoria.py → DELETAR
Remover imports desse modelo de qualquer lugar.

### TAREFA 7 — Testes

Criar/atualizar: app-editor/backend/tests/test_perfil_unificado.py

Testes:
1. Criar perfil com campos de curadoria → verificar que salva e retorna
2. Duplicar perfil → verificar que campos de curadoria sao copiados
3. GET /api/internal/perfil/best-of-opera/curadoria-config → retorna formato correto
4. Perfil sem campos de curadoria → retorna defaults vazios (nao quebra)

## CRITERIO DE ACEITE
- [ ] Modelo Perfil tem todos os campos de curadoria
- [ ] Seed BO tem valores reais do JSON
- [ ] Admin CRUD aceita campos de curadoria
- [ ] Endpoint interno retorna config no formato da curadoria
- [ ] Curadoria busca config do editor (fallback JSON local)
- [ ] perfil_curadoria.py deletado
- [ ] Testes passam
- [ ] Nenhum endpoint existente quebrou
```

*Cole direto no Claude Code. Executa antes do Prompt 3.*

---

# PROMPT 3 — Antigravity (Manager View)
## Frontend Admin + Stepper + Auth + Re-render em paralelo

> **Executor:** Antigravity (Manager View — 2 agentes paralelos)
> **Quem cola:** Bolivar ou Socio
> **Tempo estimado:** 5-7 dias
> **Pre-requisito:** Prompts 1 e 2 concluidos (backends prontos)

```
## 🎯 OBJETIVO
Criar o frontend completo: Admin de Marcas + Stepper Visual + Tela de Login + Botoes de Re-render/Re-traducao. Usar Manager View com 2 agentes paralelos.

IMPORTANTE: Usar Manager View para rodar 2 agentes em paralelo:
- Agente 1: Admin de Marcas + Stepper Visual
- Agente 2: Tela de Login + Re-render/Re-traducao

Os backends ja estao prontos e retornando dados reais.

## 📚 CONTEXTO COMPARTILHADO
- Stack: Next.js em `app-portal/`, Tailwind CSS
- URLs backend: https://editor-backend-production.up.railway.app
- Perfis de marca ja existem no banco (endpoint GET /api/v1/editor/admin/perfis)
- Auth via JWT no header Authorization: Bearer {token}
- Rotas do Dashboard ja existem em `/dashboard`
- IMPORTANTE: Estilos de legenda sao 3 campos JSON (overlay_style, lyrics_style, traducao_style)
  cada um com keys: fontname, fontsize, primarycolor, outlinecolor, outline, shadow, alignment, marginv, bold, italic

---

## AGENTE 1 — ADMIN DE MARCAS + STEPPER VISUAL

**Pastas exclusivas:** `app-portal/components/admin/` + `app-portal/app/admin/` + `app-portal/components/editor/stepper/`

### Funcoes API (adicionar em editor.ts)
- `listarPerfis()` → GET /api/v1/editor/admin/perfis
- `detalharPerfil(id)` → GET /api/v1/editor/admin/perfis/{id}
- `criarPerfil(data)` → POST /api/v1/editor/admin/perfis
- `atualizarPerfil(id, data)` → PUT /api/v1/editor/admin/perfis/{id}
- `atualizarPerfilParcial(id, data)` → PATCH /api/v1/editor/admin/perfis/{id}
- `duplicarPerfil(id)` → POST /api/v1/editor/admin/perfis/{id}/duplicar
- `previewLegenda(id)` → GET /api/v1/editor/admin/perfis/{id}/preview-legenda

### Tela 1 — LISTA DE MARCAS (`/admin/marcas`)
Somente admins acessam esta tela.

- Cards de cada marca:
  - Sigla grande (ex: "BO") com cor primaria da marca como fundo
  - Nome: "Best of Opera"
  - Stats: 48 projetos | 42 concluidos | 3 em andamento | 3 com erro
  - Badge: Ativa / Inativa
  - Botao "Editar" | Botao "Duplicar como base"
- Botao "+ Nova Marca" (canto superior direito)
- Card "Best of Opera" com icone de cadeado (protegido — nao pode deletar)

### Tela 2 — EDITOR DE MARCA (`/admin/marcas/[id]`)
Formulario completo organizado em secoes colapsaveis:

**Secao 1 — Identidade**
- Nome, Sigla, Slug (auto-gerado do nome, editavel), Ativo (toggle)
- Editorial lang (dropdown: pt, en, es, de, fr, it)
- Identity prompt (textarea grande)
- Tom de voz (textarea)
- Hashtags fixas (input com tags, adicionar/remover)
- Categorias de hook (input com tags)
- Escopo de conteudo (textarea)

**Secao 2 — Idiomas**
- Grid de idiomas-alvo: checkboxes com bandeiras
  - Padrao: PT, EN, ES, DE, FR, IT, PL
  - Extras: JP, KR, CN, RU, SA, TR, NL
- Idioma do preview: dropdown entre os selecionados

**Secao 3 — Estilo de Legenda (3 tracks)**
Para cada track (Overlay, Lyrics, Traducao), os campos vem do JSON:
- Fonte (dropdown: TeX Gyre Pagella, Georgia, Arial, Palatino, Helvetica, TimesNewRoman)
- Tamanho (slider numerico — overlay default 63, lyrics 45, traducao 43)
- Bold (toggle) | Italic (toggle)
- Cor principal (color picker)
- Cor do contorno (color picker)
- Espessura contorno (slider 0-5)
- Shadow (slider 0-3)
- Alinhamento (dropdown: 2=base, 8=topo, 5=centro)
- Margem vertical (slider numerico — overlay default 1296, lyrics 573, traducao 1353)
- Max caracteres por linha (so overlay, default 35)
- Max caracteres total (overlay 70, lyrics 43, traducao 100)

**Secao 4 — Preview de Legendas**
- Botao "Visualizar" que chama GET /preview-legenda
- Mostra mockup de frame 9:16 (proporcao 1080x1920 escalada para caber na tela)
- 3 tracks posicionadas usando marginv como referencia (converter proporcionalmente)
- Texto de exemplo: Overlay="Pavarotti's most powerful moment" / Lyrics="Nessun dorma, nessun dorma!" / Traducao="Ninguem durma, ninguem durma!"
- Atualiza conforme muda valores nos sliders

**Secao 5 — Video**
- Largura x Altura (inputs numericos, default 1080 x 1920)
- Nota: "Apenas 9:16 (1080x1920) suportado atualmente"
- Duracao minima do corte (slider em segundos)
- Duracao maxima do corte (slider em segundos)

**Secao 6 — Visual**
- Cor primaria (color picker)
- Cor secundaria (color picker)
- R2 prefix (input texto, auto-gerado do slug)

Botao "Salvar" no topo fixo (sticky). Confirmacao visual ao salvar (toast).

### Tela 3 — CRIAR MARCA (`/admin/marcas/nova`)
- Duas opcoes iniciais:
  1. "Comecar do zero" — formulario vazio com defaults do Best of Opera
  2. "Duplicar marca existente" — dropdown → copia tudo e abre pra editar
- Mesmo formulario da Tela 2

### STEPPER VISUAL (componente reutilizavel)

Criar `components/editor/stepper/PipelineStepper.tsx`:
- Barra horizontal com 5 fases agrupadas do pipeline:
  1. Importar (Download + Letra)
  2. Preparar (Transcricao + Alinhamento + Corte)
  3. Traduzir (Traducao)
  4. Renderizar (Preview + Render)
  5. Exportar (Pacote)
- Cada fase: icone (Lucide, nao emoji) + nome curto
- Estados visuais:
  - Concluido: verde, icone de check
  - Em andamento: azul, animacao pulse
  - Erro: vermelho, icone de X, tooltip com erro_msg
  - Pendente: cinza claro
  - Aguardando acao: amarelo, tooltip "Precisa de aprovacao"
- Responsivo: mobile (375px) vira vertical com fases empilhadas
- Conexoes entre fases: linha que fica verde conforme avanca
- Props: `status: string`, `passo_atual: number`, `erro_msg?: string`
- Integrar no topo de TODAS as telas do editor

### Rotas Next.js
- `/admin/marcas` — lista de marcas
- `/admin/marcas/nova` — criar marca
- `/admin/marcas/[id]` — editar marca
- Menu: adicionar "Admin → Marcas" (so visivel para role=admin)

---

## AGENTE 2 — AUTH UI + RE-RENDER/RE-TRADUCAO

**Pastas exclusivas:** `app-portal/components/auth/` + `app-portal/app/login/` + atualizacoes em `components/editor/conclusion.tsx`

### Funcoes API (adicionar em editor.ts)
- `login(email, senha)` → POST /api/v1/editor/auth/login
- `getMe()` → GET /api/v1/editor/auth/me
- `listarUsuarios()` → GET /api/v1/editor/auth/usuarios
- `registrarUsuario(data)` → POST /api/v1/editor/auth/registrar
- `atualizarUsuario(id, data)` → PATCH /api/v1/editor/auth/usuarios/{id}
- `reRenderizar(edicaoId, idioma)` → POST /api/v1/editor/edicoes/{id}/re-renderizar/{idioma}
- `reTraduzir(edicaoId, idioma)` → POST /api/v1/editor/edicoes/{id}/re-traduzir/{idioma}

### Tela de Login (`/login`)
- Tela limpa e elegante, centralizada
- Logo "Best of Opera" no topo
- Campos: Email + Senha
- Botao "Entrar"
- Se erro: mensagem "Email ou senha incorretos"
- Apos login: salvar token em localStorage
- Redirecionar para `/dashboard`

### Auth Context (provider global)
- `AuthProvider` wrapping todo o app
- `useAuth()` hook retornando: user, isAdmin, isLoading, login(), logout()
- Token armazenado em localStorage com key "bo_auth_token"
- Ao carregar app: verificar se token existe e e valido (GET /me)
- Se token expirado/invalido: limpar e redirecionar para /login
- Interceptor em todas as chamadas API: adicionar header Authorization
- logout(): limpar localStorage + redirecionar para /login

### Protecao de Rotas
- Se nao logado: redirecionar para `/login`
- Se logado mas nao admin + tentando acessar `/admin/*`: redirecionar para `/dashboard`
- Componente `<RequireAuth>` e `<RequireAdmin>` wrapping rotas

### Tela de Gerenciar Usuarios (`/admin/usuarios`) — Admin only
- Lista de usuarios: nome, email, role (badge), ultimo login, ativo
- Botao "Convidar Colaborador" → modal com campos nome + email + senha + role
- Toggle "Ativo/Inativo" em cada usuario
- NAO pode desativar a si mesmo

### Re-render/Re-traducao na Tela de Conclusao
Modificar `components/editor/conclusion.tsx`:

Na grid de idiomas, adicionar para cada idioma:

**Se render concluido:**
- Botao "Baixar" (ja existe)
- Botao icone pequeno "Refazer render" (icone refresh da Lucide) → chama `reRenderizar(id, idioma)`
- Modal de confirmacao: "Tem certeza? O video atual desse idioma sera substituido."

**Se traducao existe:**
- Botao icone pequeno "Refazer traducao" (icone refresh) → chama `reTraduzir(id, idioma)`
- Modal de confirmacao: "Refazer traducao de {idioma}? O render desse idioma tambem sera refeito."

**Se render com erro:**
- Badge vermelho "Erro" + botao "Tentar novamente" em destaque

**Indicador visual durante re-render/re-traducao:**
- Spinner no idioma especifico (inline, nao fullscreen)
- Polling (use-polling.ts existente) para atualizar quando concluir

### Seletor de Marca na Importacao
Na tela de importacao do Redator, adicionar dropdown:
- "Marca: [Best of Opera ▾]"
- Lista marcas ativas vindas de GET /admin/perfis
- Default: Best of Opera
- Se so tem 1 marca: nao mostrar dropdown, usar automaticamente
- Valor selecionado e passado como `?perfil_id=X` na importacao

## ⚙️ REGRAS
- Nao perguntar ao Bolivar — decidam layout sozinhos
- So pedir aprovacao antes de git push
- Tailwind CSS, mobile-first (375px)
- Token de auth em localStorage com key "bo_auth_token"
- Loading states com skeleton loaders
- Se endpoint falhar: mensagem amigavel via toast (sonner), nunca quebrar tela
- Botoes de re-render/re-traducao com confirmacao obrigatoria (modal, nao alert do browser)

## 🎁 ENTREGA
Admin completo de marcas com editor visual de estilos JSON + preview de legendas. Stepper do pipeline com 5 fases integrado em todas as telas. Login com JWT + protecao de rotas + localStorage. Botoes de re-render/re-traducao individual por idioma na conclusao. Seletor de marca na importacao. Tudo responsivo.
```

*Cole direto no Antigravity. Ele vai usar Manager View pra dividir entre 2 agentes.*

---

---

# PROMPT 4 — Antigravity (Visual + Testes E2E)
## Refinamento visual + Testes de navegacao autonoma

> **Executor:** Antigravity (sessao unica)
> **Quem cola:** Bolivar ou Socio
> **Tempo estimado:** 2-3 dias
> **Pre-requisito:** Prompt 3 concluido

```
## 🎯 OBJETIVO
Refinar o visual de TODAS as telas novas + rodar testes E2E via navegacao autonoma simulando a experiencia do usuario.

## 📚 CONTEXTO
As telas foram criadas com funcionalidade completa mas visual basico. Agora refinamos tudo seguindo a paleta Best of Opera ja aplicada no Dashboard, e depois testamos navegando autonomamente como um usuario faria.

Paleta Best of Opera (ja em uso no Dashboard):
- Primario: #1a1a2e (azul escuro profundo)
- Secundario: #e94560 (vermelho vibrante)
- Acento: #0f3460 (azul medio)
- Fundo: #f8f9fa (cinza claro)
- Sucesso: #10b981 (verde)
- Erro: #ef4444 (vermelho)
- Aviso: #f59e0b (amarelo)
- Texto: #1f2937 (quase preto)
- Tipografia: Inter

## ✅ PARTE 1 — REFINAMENTO VISUAL

1. Ler TODOS os componentes novos em:
   - `app-portal/components/admin/`
   - `app-portal/components/auth/`
   - `app-portal/components/editor/stepper/`
   - `app-portal/components/editor/conclusion.tsx` (parte dos re-render/re-traducao)

2. Admin de Marcas:
   - Cards de marca com a COR PRIMARIA da marca como destaque
   - Editor de marca: secoes colapsaveis com icones Lucide
   - Color pickers integrados e bonitos
   - Preview de legendas: frame 9:16 proporcional com 3 tracks posicionadas
   - Sliders de margem com valor numerico visivel
   - Grid de idiomas com bandeiras (imagens ou Unicode flags)

3. Login:
   - Tela fullscreen com fundo gradiente escuro (#1a1a2e → #0f3460)
   - Card branco centralizado com sombra suave
   - Logo/nome no topo
   - Transicao suave ao entrar

4. Stepper:
   - Icones Lucide por fase (nao emojis)
   - Conexoes entre fases (linha que fica verde conforme avanca)
   - Animacao pulse no passo atual
   - Glow vermelho no passo com erro
   - Responsivo: horizontal → vertical no mobile

5. Re-render/Re-traducao:
   - Botoes "Refazer" discretos (icone pequeno ao lado do "Baixar")
   - Modal de confirmacao elegante (componente proprio, nao alert do browser)
   - Spinner inline no idioma durante re-processamento
   - Transicao suave quando status muda

6. Navegacao:
   - Menu lateral unificado: Dashboard | Saude | Producao | Reports | Admin (se admin)
   - Indicador de marca ativa no header (sigla + cor)

7. Consistencia com Dashboard Fase 1:
   - Mesmos skeleton loaders
   - Mesmos empty states
   - Mesmas transicoes

## ✅ PARTE 2 — TESTES E2E VIA NAVEGACAO AUTONOMA

Usar a capacidade de navegacao autonoma do Antigravity para testar como um usuario real:

### Fluxo 1 — Login
1. Acessar /login
2. Tentar login com credenciais erradas → verificar mensagem de erro
3. Login com admin@bestofopera.com → verificar redirect para /dashboard
4. Verificar que menu Admin aparece (role=admin)

### Fluxo 2 — Admin de Marcas
1. Navegar para /admin/marcas
2. Verificar que "Best of Opera" aparece com cadeado
3. Clicar "Editar" no Best of Opera
4. Verificar que nome/sigla estao protegidos (nao editaveis)
5. Verificar que os 3 blocos de estilo de legenda mostram valores corretos:
   - Overlay: TeX Gyre Pagella, 63, #FFFFFF, marginv 1296
   - Lyrics: TeX Gyre Pagella, 45, #FFFF64, marginv 573
   - Traducao: TeX Gyre Pagella, 43, #FFFFFF, marginv 1353
6. Clicar "Visualizar" no preview de legendas → verificar que aparece frame 9:16
7. Voltar para lista → clicar "Duplicar como base" no Best of Opera
8. Verificar que criou copia com nome "Best of Opera (copia)"

### Fluxo 3 — Criar Marca Nova
1. Clicar "+ Nova Marca"
2. Preencher: nome="Teste E2E", sigla="TE", idiomas=[en, pt, es]
3. Salvar → verificar toast de sucesso
4. Voltar para lista → verificar que "Teste E2E" aparece

### Fluxo 4 — Stepper
1. Abrir qualquer edicao existente
2. Verificar que stepper aparece no topo com 5 fases
3. Verificar que a fase atual esta highlighted
4. Se edicao concluida: todas as fases verdes

### Fluxo 5 — Re-render (se houver edicao concluida)
1. Abrir conclusao de edicao concluida
2. Verificar que cada idioma tem botao "Refazer"
3. Clicar "Refazer" em um idioma → verificar que modal de confirmacao aparece
4. Cancelar → verificar que nada mudou

### Fluxo 6 — Protecao de Rotas
1. Fazer logout
2. Tentar acessar /dashboard → verificar redirect para /login
3. Tentar acessar /admin/marcas → verificar redirect para /login

### Relatorio de Testes
Apos cada fluxo, documentar:
- PASSOU / FALHOU
- Screenshot se falhou
- Descricao do problema

## ⚙️ REGRAS
- APENAS Tailwind + componentes existentes
- Nao perguntar ao Bolivar
- Funcionalidade intacta — ZERO mudanca de logica
- Mobile-first (375px)
- So pedir aprovacao antes de git push
- Testes E2E: documentar resultado de cada fluxo

## 🎁 ENTREGA
Todas as telas novas com visual profissional. Admin de marcas bonito com preview de legendas. Login elegante. Stepper com 5 fases animado. Botoes de re-render discretos. Navegacao unificada. Relatorio de 6 fluxos E2E testados via navegacao autonoma.
```

*Cole direto no Antigravity.*

---

---

# PROMPT 5 — Claude Code (Deploy + Seed)
## Deploy final + validacao completa

> **Executor:** Claude Code
> **Quem cola:** Bolivar (somente Bolivar autoriza deploy)
> **Tempo estimado:** 1-2 dias

```
## 🎯 OBJETIVO
Deploy final de toda a Fase 2 (multi-brand + auth + stepper + re-render) + validacao completa em producao.

## 📚 CONTEXTO
Implementamos: modelo Perfil multi-brand com estilos JSON, admin de marcas, auth com JWT, stepper visual com 5 fases, re-render/re-traducao individual, testes unitarios. Tudo testado localmente + E2E pelo Antigravity.

URLs de producao:
- Editor backend: https://editor-backend-production.up.railway.app
- Portal frontend: https://portal-production-4304.up.railway.app

## ✅ TAREFAS

### Pre-deploy: Auditoria
1. `git status` e `git diff --name-only` → listar tudo que mudou
2. Verificar ZERO credenciais hardcoded (grep -r "password\|secret\|key" nos arquivos alterados — ignorar config.py que usa env vars)
3. Verificar todos os imports corretos
4. Verificar requirements.txt inclui `python-jose[cryptography]` e `passlib[bcrypt]`
5. Verificar que a migration cria perfil "Best of Opera" como seed com valores EXATOS do ESTILOS_PADRAO
6. Verificar que a migration cria usuario admin com senha
7. Verificar seed usa WHERE NOT EXISTS (idempotencia)
8. Verificar HISTORICO atualizado com TODOS os ERRs novos (063-068)
9. Rodar testes: `cd app-editor/backend && python -m pytest tests/ -v`

### Deploy
10. Commit: "feat: BLAST v4 — multi-brand, auth, stepper, re-render individual"
11. **PARAR — pedir aprovacao do Bolivar antes de git push**
12. Apos OK: `git push origin main`

### Validacao backend (~3-5 min rebuild)
13. `curl .../health`
14. `curl .../api/v1/editor/admin/perfis` → deve retornar [{"nome":"Best of Opera", "overlay_style":{"fontname":"TeX Gyre Pagella","fontsize":63,...},...}]
15. `curl -X POST .../api/v1/editor/auth/login -H "Content-Type: application/json" -d '{"email":"admin@bestofopera.com","senha":"BestOfOpera2026!"}'` → deve retornar JWT
16. Usar o JWT para testar rota protegida: `curl -H "Authorization: Bearer {token}" .../api/v1/editor/auth/me`
17. `curl .../api/v1/editor/dashboard/visao-geral` → verificar que edicoes mostram perfil_id

### Validacao frontend
18. Acessar /login → tela de login aparece
19. Login com admin@bestofopera.com → redireciona pro dashboard
20. Menu Admin → Marcas → "Best of Opera" aparece com valores corretos
21. Abrir editor de marca → verificar overlay_style tem fontname "TeX Gyre Pagella" e fontsize 63
22. Abrir editor → stepper aparece no topo com 5 fases
23. Abrir conclusao de edicao concluida → botoes "Refazer" visiveis por idioma

### Validacao de retrocompatibilidade
24. Abrir edicao existente (que recebeu perfil_id=BO via migration)
25. Verificar que pipeline funciona igual: renderizar-preview gera video identico ao de antes
26. Verificar que idiomas sao os mesmos 7

### Documentacao final
27. Atualizar MEMORIA-VIVA.md:
    ```
    ## BLAST v4 — Fase 2: Multi-Brand Platform
    - [x] B — Blueprint: Aprovado 09/03/2026, corrigido 10/03/2026
    - [x] L — Link: SECRET_KEY reutilizada para JWT
    - [x] A — Architect: Multi-brand + Auth + Stepper + Re-render + Testes
    - [x] S — Style: Visual refinado + E2E testado pelo Antigravity
    - [x] T — Trigger: Deploy validado em producao

    Modelo Perfil: estilos em JSON (overlay_style, lyrics_style, traducao_style)
    R2 isolado por marca via r2_prefix
    Auth: JWT com SECRET_KEY existente, token em localStorage
    Stepper: 5 fases (nao 9 etapas)

    Status: Plataforma multi-brand operacional.
    Proximo passo: Preencher definicoes Reels Classics → criar perfil via Admin.
    ```

### Pos-deploy
28. Avisar Bolivar para TROCAR a senha do admin apos primeiro login
29. Criar conta para o socio (via /admin/usuarios)

## ⚙️ REGRAS
- NAO git push sem aprovacao explicita do Bolivar
- SSH (nao HTTPS) para evitar hang
- Se falhar: capturar log completo, NAO tentar fix rapido
- Validar que overlay_style no seed tem fontname="TeX Gyre Pagella" e fontsize=63 (NAO Georgia/47)

## 🎁 ENTREGA
Tudo em producao: multi-brand com admin visual, login com roles, stepper no editor com 5 fases, re-render/re-traducao individual por idioma. Perfil "Best of Opera" ativo como padrao com valores IDENTICOS ao codigo original. Admin logado. Pronto para criar perfil Reels Classics.
```

*Cole direto no Claude Code. Ele PARA antes do push e pede aprovacao.*

---

---

# APOS O DEPLOY: Criar o Reels Classics

Quando tudo estiver em producao, o processo de criar o Reels Classics e **100% pela tela**, sem codigo:

1. Login como admin
2. Admin → Marcas → "Duplicar Best of Opera como base"
3. Editar nome para "Reels Classics", sigla "RC", slug "reels-classics"
4. Ajustar: identity prompt, escopo, tons, cores, idiomas, estilos de legenda
5. Salvar → marca ativa
6. Na importacao: selecionar "Reels Classics" no dropdown de marca
7. Pipeline ja usa os estilos da nova marca automaticamente

**Se ainda nao preencheu as definicoes:** Pode fazer no chat com Claude.ai — ele conduz o questionario e no final voce so copia os valores pra tela de admin.

---

---

# RESUMO FINAL

| # | Prompt | Agente | Estrategia | Tempo | Status |
|---|--------|--------|-----------|-------|--------|
| 0 | Definicoes Reels Classics | Claude.ai (chat) | Questionario | 30min | |
| 1 | Multi-brand backend + Re-render + Testes | Claude Code | Sessao unica | 5-7 dias | ✅ |
| 2 | Auth + Admin CRUD backend | Claude Code | **Agent Teams** (2 teammates) | 3-4 dias | ✅ |
| **1.5** | **Unificar Perfil editor+curadoria** | **Claude Code** | **Sessao unica** | **1-2 dias** | **⬅️** |
| 3 | Admin UI UNIFICADA + Stepper + Auth UI + Re-render UI | Antigravity | **Manager View** (2 agentes) | 5-7 dias | |
| 4 | Visual + Testes E2E | Antigravity | Sessao unica | 2-3 dias | |
| 5 | Deploy + seed + validacao | Claude Code | Sessao unica | 1-2 dias | |
| | | | **TOTAL** | **~19-27 dias** | |

## TIMELINE

```
Semana 1:  Prompt 0 (paralelo) ————————————————————————————
           Prompt 1 (multi-brand backend) ✅               │
                                                           │ Definicoes
Semana 2:  Prompt 2 (Agent Teams — auth + admin) ✅        │ prontas
           Prompt 1.5 (unificar Perfil) ⬅️ AGORA           │
                                                           │
Semana 3:  Prompt 3 (Antigravity — admin UNIFICADO) 5-7d   │
                                                           │
Semana 4:  Prompt 4 (visual + E2E) 2-3 dias                │
           Prompt 5 (deploy + validacao) 1-2 dias          │
           Criar perfil Reels Classics via admin ——————————
```

## DIFERENCAS v4.0 → v4.1

| Item | v4.0 (errado) | v4.1 (corrigido) |
|------|---------------|------------------|
| Fonte padrao | Georgia | TeX Gyre Pagella |
| overlay fontsize | 47 | 63 |
| overlay marginv | 490 | 1296 |
| overlay alignment | 8 (topo) | 2 (base) |
| overlay italic | True | False |
| traducao marginv | 520 | 1353 |
| traducao fontsize | 35 | 43 |
| traducao alignment | nao especificado | 8 (topo) |
| lyrics fontsize | 35 | 45 |
| Modelo estilos | 30+ colunas flat | 3 campos JSON |
| editorial_lang | nao existia | campo no Perfil |
| slug | nao existia | campo no Perfil |
| r2_prefix | nao existia | campo no Perfil (isolamento R2) |
| video_width/height | nao existia | campos no Perfil (futuro) |
| Token auth | memoria (React ref) | localStorage |
| Seed admin | senha no git history | senha simples, trocar apos login |
| Seed perfil | valores inventados | WHERE NOT EXISTS + valores exatos |
| _detect_music_lang | ignora perfil | aceita idiomas_alvo do perfil |
| Stepper | 9 etapas | 5 fases agrupadas |
| schemas.py | teammates editam | so Lead edita (evita conflito) |
| Testes | nenhum | 8 unitarios + 6 fluxos E2E |
| Timeline | 12-14 dias | 18-25 dias (realista) |
| Prompt 1 e 2 | "paralelos" | sequenciais (2 depende de 1) |

## AUDITORIA PRE-DEPLOY

Antes do Prompt 5, rodar os 2 revisores em paralelo (conforme skill workflow-completo-projetos):

**Revisor A (Claude Code):** Seguranca + Plano vs Implementado
**Revisor B (Antigravity):** Endpoints + Script de Testes

Veredicto do Claude Code → Bolivar autoriza → push.

---

## FASE 3 — APOS BLAST v4 (Futuro)

| # | Acao |
|---|------|
| 3.1 | Tabela EtapaLog + historico de transicoes por projeto |
| 3.2 | Separar aplicar-corte em calcular + aprovar |
| 3.3 | Railway 2o container para render paralelo |
| 3.4 | WhatsApp webhook para erros |
| 3.5 | Automacao: YouTube playlist → pipeline automatico |
| 3.6 | Integracao MLABS (scheduling automatico) |
| 3.7 | Analise automatica de screenshots via Gemini nos reports |
| 3.8 | Multi-plataforma: TikTok + YouTube Shorts + Instagram Reels (usar video_width/height) |
| 3.9 | Analytics: metricas de performance por marca |
| 3.10 | CORS restritivo (substituir allow_origins=["*"]) |
| 3.11 | Fila prioritaria para re-render individual |
