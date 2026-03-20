# PRD-004 — Reels Classics: Correções Visuais (Fonte, Crop, Legendas)

**Status:** PENDENTE
**Data:** 20/03/2026
**Fonte:** Diagnóstico do parceiro + leitura de `ReelsClassics-ContentBible-v2.txt` e `ReelsClassics-BrandDefinition-v1.txt`

---

## 1. Contexto

O Reels Classics é a segunda marca do sistema (marca irmã do Best of Opera). O pipeline de produção foi implementado com base na infraestrutura multi-brand existente, mas as configurações visuais específicas da marca nunca foram aplicadas corretamente. O parceiro identificou três bloqueadores que impedem a finalização no app.

Referências de spec lidas:
- `c:\Users\filip\Dev\Airas\ReelsClassics-ContentBible-v2.txt`
- `c:\Users\filip\Dev\Airas\ReelsClassics-BrandDefinition-v1.txt`

---

## 2. Problemas confirmados

### BUG-RC-01 — Fonte errada (crítico)

**Sintoma:** Vídeos do Reels Classics renderizam com TeX Gyre Schola, a fonte do Best of Opera.

**Causa raiz:** O perfil do Reels Classics não tem `font_name` configurado, então herda o default global (`TeX Gyre Schola`). Além disso, os arquivos da fonte correta não existem no projeto.

**Spec exige:**
- Overlay: `Inter_24pt-Bold.ttf` (família Inter, peso 700, optical size 24pt)
- Lyrics/tradução (peças vocais): `Inter_24pt-BoldItalic.ttf`
- Fonte é sans-serif moderna — diferencia intencionalmente do Best of Opera (serifa)

**Fonte:** SIL Open Font License, uso comercial livre.
**Download:** Google Fonts → `static/Inter_24pt-Bold.ttf` e `static/Inter_24pt-BoldItalic.ttf`

**Estado atual dos arquivos:**
```
app-editor/backend/fonts/
  PlayfairDisplay-Bold.ttf          ← Best of Opera
  PlayfairDisplay-BoldItalic.ttf    ← Best of Opera
  PlayfairDisplay-Italic.ttf        ← Best of Opera
  PlayfairDisplay-Regular.ttf       ← Best of Opera
  texgyreschola-bold.otf            ← Best of Opera
  texgyreschola-bolditalic.otf      ← Best of Opera
  texgyreschola-italic.otf          ← Best of Opera
  texgyreschola-regular.otf         ← Best of Opera
  ← Inter NÃO EXISTE aqui
```

---

### BUG-RC-02 — Tamanhos de fonte errados (crítico)

**Sintoma:** Hierarquia visual do overlay não respeita a spec da marca.

**Causa raiz:** O sistema usa tamanhos fixos definidos em `legendas.py` (`ESTILOS_PADRAO`), sem diferenciação por tipo de legenda (gancho vs. corpo vs. CTA).

**Estado atual (`legendas.py`):**
```python
ESTILOS_PADRAO = {
    "overlay": {"fontsize": 40, ...},
    "lyrics":  {"fontsize": 30, ...},
    "traducao":{"fontsize": 30, ...},
}
```

**Spec exige (Reels Classics):**

| Elemento | Tamanho | Fonte |
|---|---|---|
| Gancho (1ª legenda) | 52px | Inter 24pt-Bold |
| Corpo (legendas 2+) | 48px | Inter 24pt-Bold |
| CTA (última legenda) | 44px | Inter 24pt-Bold |
| Lyrics (vocal) | 32px | Inter 24pt-BoldItalic, amarelo #E4F042 |
| Tradução (vocal) | 32px | Inter 24pt-BoldItalic, branco #FFFFFF |

**Spec exige (Best of Opera — para referência, não alterar):**

| Elemento | Tamanho | Fonte |
|---|---|---|
| Gancho | 46px | TeX Gyre Schola Bold |
| Corpo | 44px | TeX Gyre Schola Bold |
| CTA | 44px | TeX Gyre Schola Bold |
| Lyrics | 32px | TeX Gyre Schola BoldItalic, #E4F042 |
| Tradução | 32px | TeX Gyre Schola BoldItalic, branco |

O sistema precisa suportar tamanhos diferenciados por tipo de legenda (gancho/corpo/CTA) e por marca.

---

### BUG-RC-03 — Posicionamento do overlay não é dinâmico (crítico)

**Sintoma:** O overlay não respeita o gap correto em relação à imagem. Vídeos com tamanhos de imagem diferentes quebram o layout.

**Causa raiz:** O `marginv` do overlay é fixo (1296px no `ESTILOS_PADRAO`), calculado para um cenário específico. Não acompanha a posição real da imagem no frame.

**Spec exige:**
> "A BASE do bloco de texto overlay fica sempre 28px ACIMA do TOPO da imagem. O texto cresce para cima a partir desse ponto."

**Parâmetros FFmpeg corretos:**
```
y = IMAGE_TOP - 28 - text_h
```
Onde `IMAGE_TOP` é a coordenada Y do topo da imagem no frame 1080×1920 (varia conforme o tamanho da imagem).

**Validado em 15 cenários:**
- Imagem pequena (30% da tela): barras grandes, texto com respiro
- Imagem padrão (44%): layout equilibrado
- Imagem grande (60%): barras estreitas, sem corte
- Imagem máxima (64%): limite funcional

**Gap overlay→imagem:**
- Reels Classics: **28px**
- Best of Opera: **30px** (não alterar)

---

### BUG-RC-04 — Vídeos horizontais sem crop inteligente (moderado)

**Sintoma:** Vídeos originalmente horizontais (16:9) são convertidos para vertical (9:16) com barras pretas via `pad`, mas o overlay fica mal posicionado porque a imagem ocupa percentual diferente da tela dependendo do vídeo original.

**Causa raiz:** O FFmpeg usa `force_original_aspect_ratio=decrease` + `pad` com preto — comportamento correto para o formato vertical. O problema é que o `IMAGE_TOP` não é calculado dinamicamente após o pad.

**Nota:** Barras pretas são by design no layout do Reels Classics (a imagem ocupa 40-65% da tela). O problema não é a presença das barras — é que o overlay não sabe onde a imagem começa depois do pad.

---

### BUG-RC-05 — Estrutura narrativa das legendas não segue o Content Bible (moderado)

**Sintoma:** O overlay gerado não respeita a hierarquia Gancho (52px) → Corpo (48px) → CTA (44px).

**Causa raiz:** O sistema trata todas as legendas de overlay com o mesmo estilo. Não há distinção entre a 1ª legenda (gancho), as intermediárias (corpo) e a última (CTA).

**Spec exige:**
- 1ª legenda → estilo "gancho" (52px)
- Legendas 2 até penúltima → estilo "corpo" (48px)
- Última legenda → estilo "CTA" (44px, texto fixo: "Siga, o melhor da música clássica, diariamente no seu feed. ❤️")
- ~1 legenda a cada 5-6 segundos
- Máximo 3 linhas por legenda
- Sem contorno/sombra (texto sobre faixa preta)

---

## 3. Arquivos impactados

| Arquivo | O que muda |
|---|---|
| `app-editor/backend/fonts/` | Adicionar `Inter_24pt-Bold.ttf` e `Inter_24pt-BoldItalic.ttf` |
| `app-editor/backend/app/models/perfil.py` | Verificar campos de estilo por marca |
| `app-editor/backend/app/services/legendas.py` | Tamanhos por tipo (gancho/corpo/CTA), sem contorno/sombra para RC, posicionamento dinâmico |
| `app-editor/backend/app/services/ffmpeg_service.py` | Cálculo dinâmico de `IMAGE_TOP` após pad |
| `app-editor/backend/app/routes/admin_perfil.py` ou seed | Configurar perfil RC com Inter + gaps corretos |

---

## 4. O que NÃO mudar

- Configurações visuais do **Best of Opera** não devem ser tocadas
- A lógica de 3 camadas (overlay + lyrics + tradução) para peças vocais já existe — apenas ajustar fonte e tamanhos
- O formato vertical 1080×1920 está correto para ambas as marcas

---

## 5. Fora de escopo deste PRD

- **Transcrição imprecisa** (problema 1 do Best of Opera e problema 3 do Reels Classics relacionado a análise manual) — requer avaliação separada, provavelmente ajuste de prompt Gemini
- **Best of Opera** — fontes e configurações do BO serão tratadas em PRD separado se necessário

---

## 6. Critério de "pronto"

- [ ] Fonte Inter renderiza corretamente nos vídeos do Reels Classics
- [ ] Gancho 52px visível e maior que o corpo 48px
- [ ] CTA 44px com texto padrão na última legenda
- [ ] Overlay posicionado 28px acima da imagem independente do tamanho da imagem
- [ ] Best of Opera não foi afetado (teste de regressão)
