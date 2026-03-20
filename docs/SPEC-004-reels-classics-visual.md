# SPEC-004 — Reels Classics: Correções Visuais

**Status:** CONCLUÍDO
**PRD:** PRD-004-reels-classics-visual.md
**Data:** 20/03/2026

---

## Visão geral

5 tarefas independentes, executar nesta ordem (T2 depende de T1, T4 depende de T3):

```
T1: Baixar e bundlar fontes Inter
T2: Seed do perfil RC no banco (depende de T1 para saber o font_name correto)
T3: Suporte a gancho/corpo/CTA com tamanhos distintos no gerar_ass
T4: Aplicar gancho/corpo/CTA via overlay_style do RC (depende de T2 e T3)
T5: Posicionamento dinâmico do overlay (marginv baseado na imagem real)
```

Regra geral: **não alterar nada que afete o Best of Opera.** Todas as mudanças são aditivas ou condicionais ao perfil.

---

## T1 — Baixar e bundlar fontes Inter

### O que fazer

1. Baixar o arquivo ZIP da família Inter em: `https://fonts.google.com/specimen/Inter` → "Download family"
2. Extrair os dois arquivos necessários:
   - `static/Inter_24pt-Bold.ttf`
   - `static/Inter_24pt-BoldItalic.ttf`
3. Copiar ambos para:
   ```
   app-editor/backend/fonts/Inter_24pt-Bold.ttf
   app-editor/backend/fonts/Inter_24pt-BoldItalic.ttf
   ```
4. Verificar o font family name exato executando:
   ```bash
   python3 -c "
   from fontTools.ttLib import TTFont
   tt = TTFont('app-editor/backend/fonts/Inter_24pt-Bold.ttf')
   for r in tt['name'].names:
       if r.nameID == 1:
           print(repr(r.toUnicode()))
   "
   ```
   O resultado é o `font_name` a usar no T2. Esperado: `"Inter 24pt"`.

### Critério de pronto
- Dois arquivos `.ttf` presentes em `app-editor/backend/fonts/`
- `font_name` confirmado via script acima

---

## T2 — Seed do perfil Reels Classics em main.py

### Arquivo
`app-editor/backend/app/main.py`

### O que fazer

Após o bloco de seed do Best of Opera (linha ~168), adicionar um bloco análogo para o Reels Classics. Usar `font_name` confirmado no T1 (esperado: `"Inter 24pt"`).

**Valores do overlay_style (RC):**
```python
rc_overlay_style = _json.dumps({
    "fontname": "Inter 24pt",   # confirmar via T1
    "fontsize": 48,             # tamanho base (corpo)
    "gancho_fontsize": 52,      # 1ª legenda
    "cta_fontsize": 44,         # última legenda
    "primarycolor": "#FFFFFF",
    "outlinecolor": "#000000",
    "outline": 0,               # sem contorno — texto sobre faixa preta
    "shadow": 0,                # sem sombra — texto sobre faixa preta
    "alignment": 2,             # bottom-center
    "marginv": 1291,            # calculado para 16:9: 1920 - (657 - 28)
    "bold": True,
    "italic": False,
    "gap_overlay_px": 28,       # gap overlay→imagem (para cálculo dinâmico no T5)
})
```

**Valores do lyrics_style (RC — peças vocais):**
```python
rc_lyrics_style = _json.dumps({
    "fontname": "Inter 24pt",   # confirmar via T1
    "fontsize": 32,
    "primarycolor": "#E4F042",  # amarelo spec
    "outlinecolor": "#000000",
    "outline": 0,
    "shadow": 0,
    "alignment": 2,
    "marginv": 614,             # 10px abaixo da imagem, calculado para 16:9
    "bold": True,
    "italic": True,
})
```

**Valores do traducao_style (RC — peças vocais):**
```python
rc_traducao_style = _json.dumps({
    "fontname": "Inter 24pt",   # confirmar via T1
    "fontsize": 32,
    "primarycolor": "#FFFFFF",
    "outlinecolor": "#000000",
    "outline": 0,
    "shadow": 0,
    "alignment": 8,             # top-center — tradução aparece abaixo das lyrics
    "marginv": 614,             # alinhado com lyrics; T5 calculará dinamicamente
    "bold": True,
    "italic": True,
})
```

**INSERT idempotente:**
```python
conn.execute(text("""
    INSERT INTO editor_perfis (
        nome, sigla, slug, ativo, editorial_lang,
        idiomas_alvo, idioma_preview,
        overlay_style, lyrics_style, traducao_style,
        overlay_max_chars, overlay_max_chars_linha,
        lyrics_max_chars, traducao_max_chars,
        video_width, video_height,
        r2_prefix, cor_primaria, cor_secundaria,
        font_name
    )
    SELECT
        'Reels Classics', 'RC', 'reels-classics', TRUE, 'pt',
        :idiomas_alvo, 'pt',
        :overlay_style, :lyrics_style, :traducao_style,
        70, 35, 43, 100, 1080, 1920,
        'reels-classics', '#0a0a0a', '#c0a060',
        :font_name
    WHERE NOT EXISTS (
        SELECT 1 FROM editor_perfis WHERE sigla = 'RC'
    )
"""), {
    "idiomas_alvo": idiomas_alvo,   # reusar a variável já declarada para BO
    "overlay_style": rc_overlay_style,
    "lyrics_style": rc_lyrics_style,
    "traducao_style": rc_traducao_style,
    "font_name": "Inter 24pt",      # confirmar via T1
})
logger.info("Migration: seed editor_perfis Reels Classics OK (idempotente)")
```

Adicionar também **backfill** para o caso do RC já existir no banco sem `font_name`:
```python
conn.execute(text("""
    UPDATE editor_perfis SET
        font_name = :font_name,
        overlay_style = :overlay_style,
        lyrics_style = :lyrics_style,
        traducao_style = :traducao_style
    WHERE sigla = 'RC' AND font_name IS NULL
"""), {
    "font_name": "Inter 24pt",
    "overlay_style": rc_overlay_style,
    "lyrics_style": rc_lyrics_style,
    "traducao_style": rc_traducao_style,
})
logger.info("Migration: backfill Reels Classics font e estilos OK")
```

### Critério de pronto
- `SELECT font_name, overlay_style FROM editor_perfis WHERE sigla = 'RC'` retorna Inter 24pt e os estilos corretos após deploy

---

## T3 — Suporte a gancho/corpo/CTA no gerar_ass

### Arquivo
`app-editor/backend/app/services/legendas.py`

### O que fazer

Modificar a função `gerar_ass` para ler `gancho_fontsize` e `cta_fontsize` do `estilos["overlay"]` e aplicar como override ASS no texto de cada evento.

**Lógica:** o ASS suporta override de fontsize por evento via tag `{\fsN}` no texto. O estilo base define o tamanho padrão (corpo); gancho e CTA sobrescrevem apenas quando os campos existem.

**Mudança na seção "Track 1: Overlay"** dentro de `gerar_ass` (após linha 378 `texto = seg["text"]`):

```python
# Tamanhos por posição (gancho/corpo/CTA)
overlay_estilo = estilos.get("overlay", {})
gancho_fs = overlay_estilo.get("gancho_fontsize")
cta_fs = overlay_estilo.get("cta_fontsize")

# ... (loop existente for i, seg in enumerate(overlay_filtrado))
# Substituir a linha: event.text = "{\\q2}" + texto
# Por:

fs_tag = ""
if gancho_fs and i == 0:
    fs_tag = f"{{\\fs{gancho_fs}}}"
elif cta_fs and i == len(overlay_filtrado) - 1:
    fs_tag = f"{{\\fs{cta_fs}}}"

event.text = "{\\q2}" + fs_tag + texto
```

**Onde inserir:** logo antes da linha `event.text = "{\\q2}" + texto` (linha 383 no arquivo atual). A variável `i` já existe no loop.

**Importante:** esta mudança é transparente para o Best of Opera — quando `gancho_fontsize` e `cta_fontsize` são `None` (BO não os tem no overlay_style), `fs_tag` fica `""` e o comportamento é idêntico ao atual.

### Critério de pronto
- `gerar_ass` com perfil RC: evento 0 tem `{\fs52}` no texto, eventos intermediários sem tag, último evento tem `{\fs44}`
- `gerar_ass` com perfil BO: nenhum evento tem tag de tamanho (backward compat)

---

## T4 — Registrar Inter no font_service

### Arquivo
`app-editor/backend/app/services/font_service.py`

### O que fazer

Verificar se o `get_fontsdir()` já copia automaticamente todos os arquivos de `fonts/` para o diretório de fontes. Se sim, nenhuma mudança necessária — os novos `.ttf` da Inter serão copiados automaticamente.

**Verificar:**
```python
# Ler get_fontsdir() — se contém lógica de "copiar todos os *.ttf/*.otf de BUNDLED_FONTS_DIR"
# então Inter será incluída automaticamente após T1
```

Se `get_fontsdir()` lista arquivos hardcoded ou filtra por nome, adicionar `Inter_24pt-Bold.ttf` e `Inter_24pt-BoldItalic.ttf` à lista.

### Critério de pronto
- `fc-list | grep -i inter` retorna resultados no container após deploy
- Ou: `get_fontsdir()` confirmado que copia todos os arquivos de `fonts/` sem filtro

---

## T5 — Posicionamento dinâmico do overlay (marginv)

### Arquivos
- `app-editor/backend/app/services/ffmpeg_service.py` (nova função)
- `app-editor/backend/app/routes/pipeline.py` (passar dimensões para gerar_ass)
- `app-editor/backend/app/services/legendas.py` (aceitar image_top_px)

### O que fazer

#### 5a. Nova função em ffmpeg_service.py

```python
async def probar_video(video_path: str) -> tuple[int, int]:
    """Retorna (largura, altura) do vídeo via ffprobe."""
    process = await asyncio.create_subprocess_shell(
        f'ffprobe -v error -select_streams v:0 '
        f'-show_entries stream=width,height '
        f'-of csv=p=0 "{video_path}"',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await process.communicate()
    w, h = stdout.decode().strip().split(",")
    return int(w), int(h)


def calcular_image_top(src_w: int, src_h: int,
                       frame_w: int = 1080, frame_h: int = 1920) -> int:
    """Calcula coordenada Y do topo da imagem após scale+pad para frame_w x frame_h.

    Usa a mesma lógica do FFmpeg: scale com force_original_aspect_ratio=decrease
    + pad centralizado.

    Retorna IMAGE_TOP em pixels a partir do topo do frame.
    """
    # Escalar para caber em frame_w x frame_h mantendo aspect ratio
    scale = min(frame_w / src_w, frame_h / src_h)
    scaled_w = int(src_w * scale)
    scaled_h = int(src_h * scale)
    # Pad centralizado
    pad_y = (frame_h - scaled_h) // 2
    return pad_y  # IMAGE_TOP = offset vertical do topo da imagem
```

#### 5b. Modificar gerar_ass para aceitar image_top_px

Em `legendas.py`, adicionar parâmetro opcional à assinatura de `gerar_ass`:

```python
def gerar_ass(
    overlay: list,
    lyrics: list,
    traducao: Optional[list],
    idioma_versao: str,
    idioma_musica: str,
    estilos: dict = None,
    sem_lyrics: bool = False,
    perfil=None,
    image_top_px: Optional[int] = None,   # NOVO
) -> pysubs2.SSAFile:
```

No bloco de criação de estilos (após calcular `estilos`), **recalcular marginv do overlay** se `image_top_px` for fornecido:

```python
if image_top_px is not None:
    overlay_gap = estilos.get("overlay", {}).get("gap_overlay_px", 28)
    # marginv para alignment=2: distância do bottom do frame até o bottom do texto
    # text_bottom = image_top_px - overlay_gap
    # marginv = frame_h - text_bottom
    frame_h = int(subs.info.get("PlayResY", "1920"))
    computed_marginv = frame_h - (image_top_px - overlay_gap)
    estilos = dict(estilos)
    estilos["overlay"] = dict(estilos["overlay"])
    estilos["overlay"]["marginv"] = computed_marginv
```

**Nota:** este bloco deve vir ANTES da criação dos `pysubs2.SSAStyle` (antes do loop `for nome, config in estilos.items()`).

#### 5c. Passar image_top_px no pipeline

Localizar no `pipeline.py` onde `gerar_ass` é chamado. Antes da chamada, adicionar:

```python
from app.services.ffmpeg_service import probar_video, calcular_image_top

# Probar vídeo cortado (não o original — já está cortado na janela)
src_w, src_h = await probar_video(local_video_cortado_path)
image_top_px = calcular_image_top(src_w, src_h)

# Passar para gerar_ass
subs = gerar_ass(
    overlay=...,
    lyrics=...,
    traducao=...,
    ...,
    perfil=perfil,
    image_top_px=image_top_px,   # NOVO
)
```

**Importante:** se a probe falhar (ffprobe não disponível ou erro), fazer fallback silencioso:
```python
try:
    src_w, src_h = await probar_video(local_video_cortado_path)
    image_top_px = calcular_image_top(src_w, src_h)
except Exception:
    logger.warning("[pipeline] probar_video falhou — usando marginv do perfil como fallback")
    image_top_px = None
```

### Critério de pronto
- Vídeo 16:9 (1920×1080): `calcular_image_top(1920, 1080)` retorna `656`
- Vídeo 4:3 (1440×1080): `calcular_image_top(1440, 1080)` retorna `405`
- Overlay posicionado 28px acima da imagem em ambos os casos
- Fallback funciona quando ffprobe não disponível

---

## Ordem de execução recomendada

1. **T1** — baixar fontes (pré-requisito de tudo)
2. **T3** — modificar `gerar_ass` (sem deploy, só código)
3. **T5a** — adicionar `probar_video` e `calcular_image_top` no ffmpeg_service
4. **T5b** — modificar assinatura de `gerar_ass`
5. **T5c** — conectar no pipeline
6. **T4** — verificar font_service (provavelmente sem mudança)
7. **T2** — seed RC no main.py (com font_name confirmado do T1)
8. **Deploy** — Railway editor-backend

---

## Regressão: Best of Opera

Antes de fechar, verificar que BO não foi afetado:
- [ ] `gerar_ass` com perfil BO: nenhum `{\fsN}` nos textos de overlay
- [ ] `marginv` do BO calculado corretamente (ou mantido como está se `image_top_px=None` e perfil BO tem marginv no overlay_style)
- [ ] Fontes do BO (Playfair Display) ainda renderizam

---

## Fora de escopo neste SPEC

- Transcrição imprecisa (requer avaliação de prompts Gemini — PRD separado)
- Configuração de curadoria do RC (categorias, seeds, scoring) — PRD separado
- Ajuste do Best of Opera para fontes/tamanhos corretos — verificar se necessário
