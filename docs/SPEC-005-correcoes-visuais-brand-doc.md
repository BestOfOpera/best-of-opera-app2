# SPEC-005 — Correções Visuais Brand Doc v1

**Status:** CONCLUÍDO
**Data:** 20/03/2026

---

## O que foi feito

### BO — fontes e tamanhos corrigidos (main.py)
- Fonte: `Playfair Display` → `TeX Gyre Schola` (já bundled como texgyreschola-bolditalic.otf)
- Overlay: gancho=46px, corpo=44px, CTA=44px (era 63px flat)
- italic=True, outline=0, shadow=0, gap_overlay_px=30
- Lyrics: fontsize=32, cor=#E4F042, outline=0
- Tradução: fontsize=32, outline=0
- Backfill incondicional do BO existente no banco (UPDATE WHERE sigla='BO')

### Crop landscape (ffmpeg_service.py + pipeline.py)
- Filtro: `crop=if(gt(iw/ih\,4/3)\,ih*4/3\,iw):ih` antes do scale+pad
- 16:9 (1920x1080): imagem vai de 32% → 42% da tela
- calcular_image_top corrigido: usa src_w_eff = min(src_w, src_h*4/3)
- Aplicado em ambas as branches (sem_legendas e com legendas)

### RC — sem mudanças (já correto do SPEC-004)
- gancho=52px, corpo=48px, CTA=44px ✅
- Inter, italic=False no overlay ✅

---

## Próxima sessão pendente

### Transcrição imprecisa (BO + RC)
- Problema: ópera é difícil — sílabas alongadas, orquestra por cima
- Pipeline JÁ usa Genius para letra (texto correto)
- Gemini faz apenas alinhamento de timestamps
- Investigar: quando Genius falha → Gemini transcreve sozinho → texto errado
- Arquivo: `app-editor/backend/app/services/gemini.py`
- Pipeline: `app-editor/backend/app/routes/pipeline.py` (~linha 657+)
- Antes de mexer: ver exemplo real de transcrição errada para saber qual ponto falha

### Ajuste manual de legendas (UX)
- Não existe ferramenta no app para editar timing/texto de segmentos
- Pendente de avaliação de escopo
