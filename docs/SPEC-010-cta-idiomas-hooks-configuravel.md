# SPEC-010 — CTA Fixo por Marca, Idiomas Dinâmicos e Hooks Configuráveis

**Data:** 30/03/2026
**Baseado em:** PRD-010
**Status:** PENDENTE

---

## Contexto

O CTA do overlay ("Follow for more Best of Opera! 🎶" para BO, "Siga, o melhor da música clássica..." para RC) é um texto fixo por marca e por idioma. Atualmente, o sistema depende do Claude gerar o CTA como parte das legendas, resultando em inconsistência (às vezes gera, às vezes não).

Este SPEC detalha 4 blocos, executados **um por vez**, com tarefas atômicas por arquivo.

---

## Ordem de execução

```
BLOCO 1 — CTA fixo por marca (T1–T11)          ← resolve problema reportado
BLOCO 2 — Idiomas dinâmicos na tradução (T12–T14)   ← tradução correta por marca
BLOCO 3 — Detecção de idioma por marca (T15–T16)    ← geração no idioma certo
BLOCO 4 — Hooks editáveis no admin (T17–T22)        ← operabilidade sem deploy
```

---

## BLOCO 1 — CTA fixo por marca

**Objetivo:** Campo no Perfil para definir CTA em PT-BR, tradução automática via Google Translate para os idiomas da marca, injeção automática como última legenda do overlay.

---

### T1 — Novo campo `overlay_cta` no model Perfil

**Arquivo:** `app-editor/backend/app/models/perfil.py`
**Após:** linha 68 (`font_file_r2_key`)

**Adicionar:**
```python
overlay_cta = Column(JSON, default=dict)
# Estrutura: {"pt": {"text": "...", "manual": true}, "en": {"text": "...", "manual": false}, ...}
```

**Critério de feito:** Campo existe no model Python.

---

### T2 — Migration: adicionar coluna + seed BO e RC

**Arquivo:** `app-editor/backend/app/main.py`
**Onde:** bloco de migrations (após as existentes, ~linha 440+)

**Adicionar:**
```python
# Migration: overlay_cta
if "overlay_cta" not in perfil_cols:
    conn.execute(text("ALTER TABLE editor_perfis ADD COLUMN overlay_cta JSON"))
    logger.info("Migration: coluna overlay_cta adicionada")

# Seed CTA para BO (se campo vazio)
conn.execute(text("""
    UPDATE editor_perfis
    SET overlay_cta = :cta
    WHERE sigla = 'BO' AND (overlay_cta IS NULL OR overlay_cta = '{}')
"""), {"cta": _json.dumps({
    "pt": {"text": "Siga para mais Best of Opera! 🎶", "manual": True},
    "en": {"text": "Follow for more Best of Opera! 🎶", "manual": True},
})})

# Seed CTA para RC (se campo vazio)
conn.execute(text("""
    UPDATE editor_perfis
    SET overlay_cta = :cta
    WHERE sigla = 'RC' AND (overlay_cta IS NULL OR overlay_cta = '{}')
"""), {"cta": _json.dumps({
    "pt": {"text": "Siga, o melhor da música clássica, diariamente no seu feed. ❤️", "manual": True},
    "en": {"text": "Follow for the best of classical music, daily on your feed. ❤️", "manual": True},
    "es": {"text": "Sigue, lo mejor de la música clásica, a diario en tu feed. ❤️", "manual": True},
    "de": {"text": "Folge uns für die beste klassische Musik, täglich in deinem Feed. ❤️", "manual": True},
    "fr": {"text": "Suis-nous pour le meilleur de la musique classique. ❤️", "manual": True},
    "it": {"text": "Seguici per il meglio della musica classica, ogni giorno nel tuo feed. ❤️", "manual": True},
    "pl": {"text": "Obserwuj nas, najlepsza muzyka klasyczna codziennie na Twoim feedzie. ❤️", "manual": True},
})})
```

**Nota:** Os CTAs do RC vêm do Content Bible v3.4 §5.2 — são traduções manuais definidas no documento. Todos marcados como `manual: true` para não serem sobrescritos.

**Critério de feito:** Coluna existe no banco. BO e RC têm CTAs preenchidos.

---

### T3 — Expor `overlay_cta` no schema de saída e no redator-config

**Arquivo 1:** `app-editor/backend/app/routes/admin_perfil.py`
**Classe:** `PerfilDetalheOut` (~linha 105)

**Adicionar após** `font_file_r2_key` (~linha 141):
```python
overlay_cta: Optional[Dict[str, Any]] = None
```

**Arquivo 2:** `app-editor/backend/app/services/perfil_service.py`
**Função:** `build_redator_config()` (~linha 27)

**Adicionar ao dict retornado:**
```python
"overlay_cta": perfil.overlay_cta or {},
```

**Critério de feito:** GET do perfil retorna `overlay_cta`. Redator recebe `overlay_cta` na config.

---

### T4 — Endpoint para traduzir CTA via Google Translate

**Arquivo:** `app-editor/backend/app/routes/admin_perfil.py`
**Após:** endpoint `atualizar_perfil_parcial` (~linha 409)

**Novo endpoint:**
```python
@router.post("/{perfil_id}/traduzir-cta")
def traduzir_cta(perfil_id: int, db: Session = Depends(get_db)):
    """Traduz o CTA em PT para todos os idiomas_alvo da marca.
    Não sobrescreve traduções marcadas como manual=True."""
    perfil = db.query(Perfil).filter(Perfil.id == perfil_id).first()
    if not perfil:
        raise HTTPException(404, "Perfil não encontrado")

    cta_data = perfil.overlay_cta or {}
    pt_entry = cta_data.get("pt")
    if not pt_entry or not pt_entry.get("text", "").strip():
        raise HTTPException(400, "CTA em português não preenchido")

    pt_text = pt_entry["text"]
    idiomas = perfil.idiomas_alvo or ["en", "pt", "es", "de", "fr", "it", "pl"]

    # Traduzir via Google Translate (mesmo serviço do redator)
    import urllib.request, json as _json
    for lang in idiomas:
        if lang == "pt":
            continue
        existing = cta_data.get(lang, {})
        if existing.get("manual"):
            continue  # Não sobrescrever tradução manual
        try:
            # Chamar Google Translate diretamente
            import html as _html
            from urllib.parse import urlencode
            params = urlencode({
                "q": pt_text, "target": lang, "format": "text",
                "key": os.getenv("GOOGLE_TRANSLATE_API_KEY", ""),
            })
            url = f"https://translation.googleapis.com/language/translate/v2?{params}"
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
            translated = _html.unescape(data["data"]["translations"][0]["translatedText"])
            cta_data[lang] = {"text": translated, "manual": False}
        except Exception as exc:
            logger.warning(f"Erro ao traduzir CTA para {lang}: {exc}")
            continue

    # Garantir PT está salvo
    cta_data["pt"] = {"text": pt_text, "manual": True}
    perfil.overlay_cta = cta_data
    db.commit()
    db.refresh(perfil)

    dados = {c.name: getattr(perfil, c.name) for c in perfil.__table__.columns}
    return PerfilDetalheOut(**dados)
```

**Critério de feito:** POST `/{perfil_id}/traduzir-cta` traduz CTA para todos os idiomas e retorna perfil atualizado.

---

### T5 — Tipo `Perfil` no frontend: adicionar `overlay_cta`

**Arquivo:** `app-portal/lib/api/editor.ts`
**Interface:** `Perfil` (~linha 204)

**Adicionar após** `font_file_r2_key` (~linha 237):
```typescript
overlay_cta: Record<string, { text: string; manual: boolean }> | null
```

**Adicionar método** (após métodos existentes de `editorApi`):
```typescript
traduzirCta: (perfilId: number) => request<Perfil>(`${BASE()}/admin/perfis/${perfilId}/traduzir-cta`, { method: "POST" }),
```

**Critério de feito:** Tipo TypeScript reflete campo. Método API disponível.

---

### T6 — Seção "CTA do Overlay" na página de edição de marca

**Arquivo:** `app-portal/app/(app)/admin/marcas/[id]/page.tsx`
**Onde:** Nova `CollapsibleSection` após a seção "Prompts & Editorial"

**Adicionar:**
```tsx
<CollapsibleSection title="CTA do Overlay" description="Texto fixo exibido como última legenda em todos os vídeos." icon={Type}>
    <div className="space-y-5">
        <div className="space-y-2">
            <Label className="font-semibold text-muted-foreground">Texto base (PT-BR)</Label>
            <p className="text-[11px] text-muted-foreground -mt-1">
                Será traduzido automaticamente para os idiomas da marca. Traduções editadas manualmente não são sobrescritas.
            </p>
            <Input
                value={(formData.overlay_cta as any)?.pt?.text || ""}
                onChange={e => {
                    const cta = { ...(formData.overlay_cta || {}), pt: { text: e.target.value, manual: true } }
                    handleChange("overlay_cta", cta)
                }}
                className="bg-background text-sm"
                placeholder="Ex: Siga para mais Best of Opera! 🎶"
            />
        </div>
        <div className="flex items-center gap-2">
            <Button
                type="button" variant="secondary" size="sm"
                disabled={ctaTranslating || !(formData.overlay_cta as any)?.pt?.text?.trim()}
                onClick={async () => {
                    setCtaTranslating(true)
                    try {
                        // Salvar primeiro o PT, depois traduzir
                        await editorApi.atualizarPerfil(perfil.id, { overlay_cta: formData.overlay_cta })
                        const updated = await editorApi.traduzirCta(perfil.id)
                        setFormData(prev => ({ ...prev, overlay_cta: updated.overlay_cta }))
                        toast.success("CTA traduzido para todos os idiomas!")
                    } catch (err: any) {
                        toast.error(extractErrorMessage(err))
                    } finally {
                        setCtaTranslating(false)
                    }
                }}
            >
                {ctaTranslating ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Globe className="mr-2 h-3.5 w-3.5" />}
                {ctaTranslating ? "Traduzindo..." : "Traduzir automaticamente"}
            </Button>
        </div>
        {formData.idiomas_alvo?.filter(l => l !== "pt").map(lang => {
            const entry = (formData.overlay_cta as any)?.[lang]
            return (
                <div key={lang} className="flex items-center gap-3">
                    <Badge variant="outline" className="w-10 justify-center uppercase text-[10px] font-bold shrink-0">{lang}</Badge>
                    <Input
                        value={entry?.text || ""}
                        onChange={e => {
                            const cta = {
                                ...(formData.overlay_cta || {}),
                                [lang]: { text: e.target.value, manual: true }
                            }
                            handleChange("overlay_cta", cta)
                        }}
                        className="flex-1 bg-background text-sm"
                        placeholder={`CTA em ${lang.toUpperCase()}`}
                    />
                    {entry?.manual && (
                        <Badge variant="secondary" className="text-[9px] shrink-0">editado</Badge>
                    )}
                </div>
            )
        })}
    </div>
</CollapsibleSection>
```

**State adicional no componente** (junto aos outros useState):
```typescript
const [ctaTranslating, setCtaTranslating] = useState(false)
```

**Critério de feito:** Seção CTA aparece na página de edição de marca. Campo PT editável. Botão traduz. Idiomas listados e editáveis individualmente. Badge "editado" nas traduções manuais.

---

### T7 — Mesma seção na página de criação de marca

**Arquivo:** `app-portal/app/(app)/admin/marcas/nova/page.tsx`
**Onde:** Após seção "Prompts & Editorial"

**Mesma lógica da T6**, porém sem o botão "Traduzir automaticamente" (a marca ainda não existe no banco). O botão aparece só após criar a marca e ir para a página de edição.

Alternativa: permitir o botão de tradução na criação, fazendo um POST separado. Mas é mais simples exigir que a tradução seja feita após criar.

**Critério de feito:** Campo CTA PT disponível na criação. Nota informando "Salve a marca primeiro e use a página de edição para traduzir automaticamente."

---

### T8 — Prompt do overlay: remover instrução de CTA

**Arquivo:** `app-redator/backend/prompts/overlay_prompt.py`
**Linha 114:** regra 6 do prompt

**Antes:**
```python
6. Follow ALL instructions from the Brand Identity, Tone of Voice, and Content Scope sections above for narrative arc, hook style, CTA format, forbidden phrases, and writing rules.
```

**Depois:**
```python
6. Follow ALL instructions from the Brand Identity, Tone of Voice, and Content Scope sections above for narrative arc, hook style, forbidden phrases, and writing rules.
7. Do NOT generate a CTA (call-to-action) subtitle. The system adds it automatically. Your LAST subtitle must be the final NARRATIVE subtitle — the CTA will be appended after it.
```

**Critério de feito:** Claude não gera CTA. Última legenda é narrativa.

---

### T9 — `generate_overlay()`: anexar CTA como última legenda

**Arquivo:** `app-redator/backend/services/claude_service.py`
**Função:** `generate_overlay()` (~linha 214)
**Onde:** após a normalização de timestamps e antes do return (~linha 297)

**Adicionar:**
```python
# Anexar CTA fixo da marca como última legenda
cta_data = (brand_config or {}).get("overlay_cta", {})
editorial_lang = (brand_config or {}).get("editorial_lang", "pt")
cta_entry = cta_data.get(editorial_lang) or cta_data.get("pt")
if cta_entry and cta_entry.get("text", "").strip():
    # Timestamp do CTA: após a última legenda narrativa
    if parsed:
        last_ts = parsed[-1]["timestamp"]
        try:
            parts = last_ts.split(":")
            last_secs = int(parts[0]) * 60 + int(parts[1])
            cta_secs = last_secs + interval_secs
            # Não ultrapassar o final do vídeo
            if ceiling is not None and cta_secs > ceiling:
                cta_secs = ceiling
            cta_ts = f"{cta_secs // 60:02d}:{cta_secs % 60:02d}"
        except (ValueError, IndexError):
            cta_ts = "00:00"
    else:
        cta_ts = "00:00"
    parsed.append({"timestamp": cta_ts, "text": cta_entry["text"], "_is_cta": True})
    print(f"[generate_overlay] CTA anexado: '{cta_entry['text'][:40]}...' @ {cta_ts}")
```

**Nota:** O campo `_is_cta: True` é um marcador interno para que o frontend saiba que é CTA. Não afeta o render (legendas.py já trata o último overlay como CTA para fontsize).

**Critério de feito:** Overlay gerado sempre tem CTA como última legenda. Log confirma injeção.

---

### T10 — `translate_overlay_json()`: usar CTA fixo do idioma alvo

**Arquivo:** `app-redator/backend/services/translate_service.py`
**Função:** `translate_overlay_json()` (~linha 217)

**Antes:**
```python
def translate_overlay_json(overlay_json: list, target_lang: str) -> list:
    """Translate the text field of each overlay subtitle."""
    result = []
    for entry in overlay_json:
        translated_text = translate_text(entry.get("text", ""), target_lang)
        result.append({"timestamp": entry["timestamp"], "text": translated_text})
    return result
```

**Depois:**
```python
def translate_overlay_json(overlay_json: list, target_lang: str, brand_cta: dict = None) -> list:
    """Translate the text field of each overlay subtitle.

    Se a última legenda for CTA (_is_cta=True) e brand_cta tiver tradução
    para target_lang, usa o texto fixo em vez de traduzir via Google.
    """
    result = []
    for entry in overlay_json:
        # CTA fixo: usar tradução da marca em vez de Google Translate
        if entry.get("_is_cta") and brand_cta:
            cta_entry = brand_cta.get(target_lang) or brand_cta.get("pt")
            if cta_entry and cta_entry.get("text"):
                result.append({"timestamp": entry["timestamp"], "text": cta_entry["text"], "_is_cta": True})
                continue
        translated_text = translate_text(entry.get("text", ""), target_lang)
        result.append({"timestamp": entry["timestamp"], "text": translated_text})
    return result
```

**Critério de feito:** CTA é substituído pelo texto fixo do idioma alvo, não traduzido via Google.

---

### T11 — Passar `brand_cta` nas chamadas de tradução

**Arquivo:** `app-redator/backend/routers/translation.py`
**Linhas 64-67 e 125-128:** onde `translate_overlay_json` é chamado

**Antes (~linha 64):**
```python
translated_overlay = (
    translate_overlay_json(project.overlay_json, lang)
    if project.overlay_json
    else None
)
```

**Depois:**
```python
brand_cta = brand_config.get("overlay_cta", {}) if brand_config else {}
translated_overlay = (
    translate_overlay_json(project.overlay_json, lang, brand_cta=brand_cta)
    if project.overlay_json
    else None
)
```

**Verificar:** o `brand_config` já está disponível no escopo da função de tradução. Se não, carregar via `load_brand_config(project.brand_slug)`.

**Fazer o mesmo** na segunda chamada (~linha 125-128).

**Critério de feito:** Tradução do overlay usa CTA fixo por idioma em vez de Google Translate.

---

### T11b — Approve overlay: indicação visual do CTA

**Arquivo:** `app-portal/components/redator/approve-overlay.tsx`
**Dentro do map de legendas (~linha 109-129)**

**Modificar** o render de cada legenda para verificar `_is_cta`:
```tsx
{overlay.map((entry, i) => {
    const isCta = (entry as any)._is_cta === true
    return (
        <div key={i} className={cn("flex items-center gap-3 px-4 py-2.5", isCta && "bg-muted/30")}>
            <span className="text-xs font-medium text-muted-foreground tabular-nums w-8">
                {isCta ? "CTA" : i + 1}
            </span>
            <Input
                value={entry.timestamp}
                onChange={(e) => updateEntry(i, "timestamp", e.target.value)}
                className="w-20 font-mono text-xs"
                disabled={isCta}
            />
            <Input
                value={entry.text}
                onChange={(e) => updateEntry(i, "text", e.target.value)}
                className={cn("flex-1 text-sm", isCta && "text-muted-foreground")}
                disabled={isCta}
            />
            {isCta ? (
                <Badge variant="secondary" className="text-[9px] shrink-0">Fixo</Badge>
            ) : (
                <>
                    <span className={`text-[10px] tabular-nums w-10 text-right ${entry.text.length > 70 ? "text-destructive font-medium" : "text-muted-foreground"}`}>
                        {entry.text.length}/70
                    </span>
                    <Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive" onClick={() => removeEntry(i)}>
                        <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                </>
            )}
        </div>
    )
})}
```

**Critério de feito:** CTA aparece com label "CTA", fundo diferenciado, badge "Fixo", campos desabilitados. Não é removível nem editável na aprovação.

---

## BLOCO 2 — Idiomas dinâmicos na tradução

**Objetivo:** Tradução respeitar `idiomas_alvo` do Perfil em vez de `ALL_LANGUAGES` hardcoded.

---

### T12 — Remover `ALL_LANGUAGES` hardcoded

**Arquivo:** `app-redator/backend/services/translate_service.py`
**Linha 8:** `ALL_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]`

**Antes:**
```python
ALL_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]

def get_target_languages(source_lang: str) -> list:
    return [l for l in ALL_LANGUAGES if l != source_lang]
```

**Depois:**
```python
_DEFAULT_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]

def get_target_languages(source_lang: str, idiomas_alvo: list = None) -> list:
    languages = idiomas_alvo if idiomas_alvo else _DEFAULT_LANGUAGES
    return [l for l in languages if l != source_lang]
```

**Critério de feito:** `get_target_languages` aceita lista de idiomas da marca.

---

### T13 — Passar `idiomas_alvo` na chamada de tradução

**Arquivo:** `app-redator/backend/routers/translation.py`
**Onde:** chamada a `get_target_languages` (~linha 54)

**Antes:**
```python
target_langs = get_target_languages(source_lang)
```

**Depois:**
```python
brand_config = load_brand_config(project.brand_slug) if project.brand_slug else {}
idiomas_alvo = brand_config.get("idiomas_alvo")
target_langs = get_target_languages(source_lang, idiomas_alvo=idiomas_alvo)
```

**Verificar:** se `brand_config` já é carregado antes no fluxo, reutilizar.

**Critério de feito:** Tradução gera apenas os idiomas configurados na marca.

---

### T14 — Expor `idiomas_alvo` no `build_redator_config`

**Arquivo:** `app-editor/backend/app/services/perfil_service.py`
**Função:** `build_redator_config()` (~linha 27)

**Verificar se já está incluído.** Se não, adicionar:
```python
"idiomas_alvo": perfil.idiomas_alvo or ["en", "pt", "es", "de", "fr", "it", "pl"],
```

**Critério de feito:** Redator recebe `idiomas_alvo` da marca.

---

## BLOCO 3 — Detecção de idioma por marca

**Objetivo:** `detect_hook_language()` respeitar `editorial_lang` do Perfil quando o operador usa categoria predefinida.

---

### T15 — `detect_hook_language()` usar `editorial_lang` da marca

**Arquivo:** `app-redator/backend/prompts/hook_helper.py`
**Função:** `detect_hook_language()` (~linha 24)

**Antes (~linha 33-34):**
```python
if cat_key and cat_key != "prefiro_escrever" and cat_key in HOOK_CATEGORIES:
    return "português"
```

**Depois:**
```python
# Mapeamento de código ISO para nome de idioma usado nos prompts
_LANG_CODE_TO_NAME = {
    "pt": "português", "en": "English", "es": "español",
    "de": "Deutsch", "fr": "français", "it": "italiano", "pl": "polski",
}

def detect_hook_language(project, brand_config=None) -> str:
    cat_key = getattr(project, "hook_category", "") or ""

    # Categorias predefinidas: usar idioma editorial da marca
    categories = HOOK_CATEGORIES
    if brand_config and brand_config.get("hook_categories_redator"):
        categories = brand_config["hook_categories_redator"]

    if cat_key and cat_key != "prefiro_escrever" and cat_key in categories:
        editorial_lang = (brand_config or {}).get("editorial_lang", "pt")
        return _LANG_CODE_TO_NAME.get(editorial_lang, "português")

    # ... resto da detecção por heurística permanece igual
```

**Critério de feito:** Categoria predefinida respeita `editorial_lang` da marca.

---

### T16 — Passar `brand_config` em todas as chamadas a `detect_hook_language`

**Arquivo:** `app-redator/backend/services/claude_service.py`
**Funções:** `generate_overlay()`, `generate_post()`, `generate_youtube()`

**Verificar** cada chamada a `detect_hook_language(project)` e substituir por `detect_hook_language(project, brand_config=brand_config)`.

Atualmente em `generate_overlay()` (~linha 215):
```python
lang = detect_hook_language(project)
```

**Depois:**
```python
lang = detect_hook_language(project, brand_config=brand_config)
```

**Repetir** para `generate_post()` e `generate_youtube()`.

**Critério de feito:** Todas as chamadas a `detect_hook_language` passam `brand_config`.

---

## BLOCO 4 — Hooks editáveis no admin

**Objetivo:** Mover categorias de hooks de hardcoded no `config.py` para editáveis via admin. Configuração global (não por marca).

---

### T17 — Nova tabela ou campo global para hook categories

**Decisão de design:** Usar um campo JSON na tabela de configurações globais, ou uma tabela dedicada `hook_categories`.

**Opção recomendada:** Campo JSON num registro de configuração global (mais simples, não precisa de nova tabela). Criar uma tabela `app_config` com um registro `hook_categories`:

**Arquivo:** `app-editor/backend/app/models/` — novo arquivo `app_config.py`

```python
from sqlalchemy import Column, Integer, String, JSON
from app.database import Base

class AppConfig(Base):
    __tablename__ = "app_config"
    id = Column(Integer, primary_key=True)
    chave = Column(String(100), unique=True, nullable=False)
    valor = Column(JSON, nullable=False)
```

**Critério de feito:** Model existe.

---

### T18 — Migration e seed das hook categories

**Arquivo:** `app-editor/backend/app/main.py`

**Adicionar:** Criar tabela `app_config` se não existe. Seed com as 10 categorias atuais do `config.py`.

**Critério de feito:** Tabela existe. Registro `hook_categories` contém as 10 categorias com labels, emojis e prompts.

---

### T19 — Endpoint CRUD para hook categories

**Arquivo:** `app-editor/backend/app/routes/admin_perfil.py` (ou novo router)

**Endpoints:**
- `GET /api/v1/editor/admin/hook-categories` — retorna as categorias ativas
- `PUT /api/v1/editor/admin/hook-categories` — atualiza todas as categorias

**Critério de feito:** API funcional. Categorias editáveis.

---

### T20 — Endpoint público (sem auth) para listar categorias

**Arquivo:** `app-editor/backend/app/routes/admin_perfil.py` (router_internal)

**Endpoint:** `GET /api/internal/hook-categories` — usado pelo app-redator e frontend.

**Critério de feito:** Redator e frontend conseguem listar categorias sem auth de admin.

---

### T21 — `hook_helper.py` carregar categorias do banco

**Arquivo:** `app-redator/backend/prompts/hook_helper.py`

**Antes (~linha 1-2):**
```python
from backend.config import HOOK_CATEGORIES
```

**Depois:**
```python
import json
import urllib.request
from backend.config import HOOK_CATEGORIES, EDITOR_API_URL

_cached_categories = None

def _load_hook_categories():
    global _cached_categories
    if _cached_categories:
        return _cached_categories
    try:
        url = f"{EDITOR_API_URL}/api/internal/hook-categories"
        with urllib.request.urlopen(url, timeout=3) as resp:
            _cached_categories = json.loads(resp.read().decode())
        return _cached_categories
    except Exception:
        return HOOK_CATEGORIES  # fallback ao hardcoded
```

**Usar** `_load_hook_categories()` em vez de `HOOK_CATEGORIES` diretamente.

**Critério de feito:** Hook categories vêm do banco. Fallback ao hardcoded se banco indisponível.

---

### T22 — Frontend: carregar categorias do API

**Arquivos:**
- `app-portal/app/(app)/admin/marcas/[id]/page.tsx` — remover `HOOK_CATEGORIES` hardcoded
- `app-portal/app/(app)/admin/marcas/nova/page.tsx` — idem
- `app-portal/components/redator/new-project.tsx` — idem (se usa hardcoded)

**Substituir** array hardcoded por chamada ao endpoint `GET /api/internal/hook-categories` ou rota Next.js equivalente.

**Critério de feito:** Frontend mostra categorias do banco. Novas categorias aparecem sem deploy.

---

## Checklist geral

| # | Tarefa | Bloco | Critério |
|---|--------|-------|----------|
| T1 | Campo `overlay_cta` no model | 1 | Model Python |
| T2 | Migration + seed BO/RC | 1 | Coluna no banco, CTAs preenchidos |
| T3 | Schema + redator-config | 1 | API retorna campo |
| T4 | Endpoint traduzir CTA | 1 | POST traduz e salva |
| T5 | Tipo Perfil no frontend | 1 | TypeScript + método API |
| T6 | Seção CTA na edição de marca | 1 | UI funcional |
| T7 | Seção CTA na criação de marca | 1 | UI funcional |
| T8 | Remover CTA do prompt overlay | 1 | Claude não gera CTA |
| T9 | Anexar CTA no generate_overlay | 1 | CTA sempre presente |
| T10 | CTA fixo no translate_overlay | 1 | CTA do idioma alvo |
| T11 | Passar brand_cta nas traduções | 1 | Tradução usa CTA fixo |
| T11b | UI aprovação com label CTA | 1 | CTA visível e não-editável |
| T12 | Remover ALL_LANGUAGES | 2 | get_target_languages aceita lista |
| T13 | Passar idiomas_alvo na tradução | 2 | Traduz só idiomas da marca |
| T14 | idiomas_alvo no redator-config | 2 | Campo disponível |
| T15 | detect_hook_language usar marca | 3 | Respeita editorial_lang |
| T16 | Passar brand_config nas chamadas | 3 | Todas as funções passam |
| T17 | Tabela app_config | 4 | Model existe |
| T18 | Migration + seed hooks | 4 | Categorias no banco |
| T19 | CRUD hook categories | 4 | API funcional |
| T20 | Endpoint público hooks | 4 | Sem auth, para redator/frontend |
| T21 | hook_helper carregar do banco | 4 | Categorias dinâmicas |
| T22 | Frontend carregar do API | 4 | Sem hardcoded |
