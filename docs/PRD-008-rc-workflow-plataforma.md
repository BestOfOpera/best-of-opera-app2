# PRD-008 — Diagnóstico: Workflow RC Dentro da Plataforma

**Data:** 25/03/2026
**Baseado em:** sessão de diagnóstico 25/03 — observação do operador usando a plataforma
**Status do ciclo: PENDENTE (aguarda sessão dedicada)**

---

## 1. Problema identificado

O operador, ao usar o Reels Classics na plataforma, percorre **exatamente o mesmo caminho** que o Best of Opera:

```
Dashboard → Playlist → Preparar edição → Redator → Overlay → Post →
Tradução (6 idiomas) → Exportar → Editor → Importar do redator →
Selecionar música → Importar idioma da música → ...
```

Isso é incorreto. O RC é um canal **instrumental** (sem letra cantada). O pipeline foi construído para o BO e o RC foi adicionado como um segundo perfil sem adaptar o fluxo da UI.

---

## 2. O que acontece hoje vs. o que deveria acontecer

### Hoje
```
RC: Claude gera .srt → operador baixa o arquivo → importa no CapCut →
aplica Inter SemiBold manualmente → exporta → publica
```
A plataforma continua rodando após a etapa do redator, pedindo para o operador:
- Selecionar idioma da música (RC não tem letra, logo não tem idioma de música)
- Importar no editor (que usa FFmpeg — nunca deveria ser chamado para o RC)
- Seguir os mesmos passos de alinhamento de letra (irrelevante para RC)

### O que o operador quer
Fazer tudo dentro da plataforma — sem precisar sair para o CapCut. Isso implica uma de duas coisas:

**Opção A — Renderização via FFmpeg dentro da plataforma (como o BO)**
A plataforma renderiza as legendas no vídeo usando FFmpeg/libass. O operador não precisa usar CapCut. O visual (fonte, tamanho, posição) seria controlado pelo perfil RC no banco.

**Opção B — Fluxo truncado: plataforma gera SRT, operador baixa e usa CapCut**
A plataforma para após o redator, oferece o arquivo `.srt` para download, e o fluxo continua no CapCut. Hoje já funciona assim, mas a UI não deixa isso claro — o operador fica confuso porque o sistema continua pedindo passos que não fazem sentido para o RC.

---

## 3. Por que o RC segue o mesmo caminho que o BO

Causa raiz: o portal não tem lógica de branching baseada no tipo de perfil. Todas as rotas do pipeline (redator → overlay → post → tradução → exportar → editor → render) são expostas igualmente para todos os perfis.

O perfil `sigla = 'RC'` existe no banco com os campos `overlay_style`, `lyrics_style`, `traducao_style` preenchidos (copiados do BO quando o RC foi criado), o que faz a plataforma tratar o RC como se fosse um canal com 3 tracks de legenda — o que é incorreto.

---

## 4. Impacto atual

- Operador fica confuso ao chegar na etapa de "selecionar idioma da música" (RC é instrumental)
- Etapa de alinhamento de letra é apresentada desnecessariamente
- Se o operador seguir o fluxo até o fim, o editor tentará renderizar via FFmpeg — o que tecnicamente funciona, mas não é o workflow definido no Manual do Operador RC
- Tempo perdido navegando por etapas irrelevantes

---

## 5. Decisões pendentes (para a sessão do SPEC-008)

Antes de implementar qualquer coisa, precisam ser definidos:

1. **Qual opção o operador quer?**
   - A: renderização dentro da plataforma via FFmpeg (paridade com BO)
   - B: fluxo truncado com download do SRT + CapCut

2. **Se Opção A:** o visual do RC (Inter SemiBold, tamanhos, posição) precisa ser validado antes de qualquer render. O brand doc não especifica os valores para renderização via FFmpeg — foi projetado para CapCut.

3. **Se Opção B:** a UI precisa de um ponto de parada explícito após a exportação do SRT, com um botão de download claro e instruções para o operador.

4. **Independente da opção:** a etapa "selecionar idioma da música" deve ser ocultada ou adaptada para perfis instrumentais (RC).

---

## 6. Arquivos que serão afetados (estimativa)

| Arquivo | O que muda |
|---|---|
| `app-portal/app/(app)/redator/projeto/[id]/exportar/page.tsx` | Ponto de parada para RC + download SRT |
| `app-portal/app/(app)/editor/` (várias páginas) | Ocultar ou adaptar etapas para RC |
| `app-editor/backend/app/main.py` | Se Opção A: ajustar pipeline RC para render single-track |
| `app-editor/backend/app/services/legendas.py` | Se Opção A: lógica de 1 track vs 3 tracks por perfil |

---

## 7. O que NÃO foi alterado

Nenhuma alteração foi feita no código nesta sessão. Este PRD é puramente documental. As correções emergenciais (P1–P8) foram registradas no SPEC-007.

---

## 8. Como retomar este assunto

1. Abrir nova sessão
2. Ler este PRD-008
3. Responder as perguntas da seção 5 (qual opção)
4. Criar SPEC-008 com o plano de implementação
