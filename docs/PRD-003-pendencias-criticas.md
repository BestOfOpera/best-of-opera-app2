# PRD-003 — Pendências Críticas Pós-SPEC-002
**Data:** 19/03/2026
**Status:** PENDENTE
**Origem:** RESUMO-DIAGNOSTICO-190326.md — itens 🔴/🟡/⬜ ainda abertos após SPEC-001 e SPEC-002

---

## Contexto

SPEC-001 e SPEC-002 foram concluídos em 19/03/2026. Restam 4 frentes de trabalho abertas
confirmadas no diagnóstico e na tabela de tarefas da reunião:

1. **Deploys pendentes** — código de SPEC-002 já escrito, aguardando push para produção
2. **BUG-F** — projeto exibe dados de outra marca (nunca investigado no código)
3. **Legendas/chars** — limite de caracteres errado + edição manual de tempos inexistente
4. **BUG-E** — `cached_videos` sem isolamento por `brand_slug`

---

## Frente 1 — Deploys pendentes de SPEC-002

### Estado atual

Dois fixes do SPEC-002 estão no código mas **não estão em produção**:

| Serviço Railway | Arquivo | Fix | Status |
|---|---|---|---|
| `editor-backend` | `app-editor/backend/app/routes/auth.py` | `func.lower()` em login + registrar | ⚠️ DEPLOY PENDENTE |
| `portal` | `app-portal/lib/auth-context.tsx` | Catch seletivo por status 401 | ⚠️ DEPLOY PENDENTE |

### Impacto de não deployar

- Usuários continuam sofrendo o bug de relogin 401 em produção mesmo com o código corrigido localmente.
- Qualquer nova sessão inicia sem as correções ativas.

### O que verificar antes do deploy

- Confirmar que não há mudanças de schema ou migration necessárias (não há — só lógica de aplicação).
- Os dois deploys são independentes e podem ser feitos em qualquer ordem.

### Arquivos envolvidos

| Arquivo | Linhas alteradas |
|---|---|
| `app-editor/backend/app/routes/auth.py` | 88–91 (login), 117 (registrar) |
| `app-portal/lib/auth-context.tsx` | 53–58 (catch seletivo) |

---

## Frente 2 — BUG-F: projeto exibe marca errada

### Sintoma (ponto 9 da reunião)

Tela exibe dados de outra marca. Exemplo reportado: Best of Opera aparecendo em projeto
que deveria ser da Reels Classics.

### Causa raiz

Desconhecida. Nunca investigada no código-fonte.

### Hipóteses a investigar

1. **Query sem filtro de `brand_slug`** — endpoint de listagem de projetos retorna todos os
   registros sem filtrar pela marca ativa do usuário logado.
2. **Brand_slug propagado errado no frontend** — contexto de marca resolvido incorretamente
   em algum estado do React/Next.js.
3. **Cache compartilhado de projetos** — se `cached_videos` (BUG-E, ver Frente 4) compartilha
   dados entre marcas, pode contaminar o contexto de projeto.
4. **Associação projeto → marca salva errada no banco** — ao criar um projeto, o `brand_slug`
   do projeto é salvo com o valor errado.

### Onde investigar

| Arquivo a ler | O que procurar |
|---|---|
| `app-editor/backend/app/routes/` — endpoint de listagem de projetos/edições | Filtro por marca na query |
| `app-portal/` — página/componente que lista projetos | Como o `brand_slug` ativo é lido e passado |
| Banco de dados — tabela `edicoes` ou equivalente | Se `brand_slug` está preenchido corretamente nos registros |
| `app-editor/backend/app/models/` | Se o model de edição tem campo `brand_slug` |

### Critério de "bug confirmado"

- Query de listagem retorna edições de outra marca para o usuário logado **OU**
- Registro no banco tem `brand_slug` errado **OU**
- Frontend exibe `brand_slug` de um contexto errado.

### Critério de "bug corrigido"

- Usuário da marca RC só vê projetos da RC.
- Usuário da marca BO só vê projetos da BO.
- Confirmado com registro no banco e output na tela.

---

## Frente 3 — Legendas: limite de caracteres e edição de tempos

### Estado atual (tabela da reunião — tarefa 6)

| Parâmetro | Valor atual no código | Valor solicitado na reunião |
|---|---|---|
| Limite overlay | 70 chars | 73 chars |
| Limite lyrics | 43 chars | 73 chars |
| Edição manual de tempos | Não existe | Solicitado na reunião |

**Arquivo de referência:** `legendas.py` (caminho exato a confirmar antes de editar).

### Impacto

- Legendas com mais de 70 chars são cortadas ou quebradas incorretamente.
- Sem edição manual de tempos, qualquer timing incorreto gerado automaticamente
  exige re-renderização completa em vez de ajuste pontual.

### Pendência de decisão editorial

7 pontos sobre conteúdo da RC (estrutura de post, CTA overlay, hooks com referência a ópera,
hashtags, etc.) estão pendentes de resposta do Bolivar desde a sessão 12.
**Impacto aqui:** o limite de 73 chars para lyrics pode estar relacionado a esses pontos.
**Ação antes de codar:** confirmar com Bolivar se o valor 73 é definitivo para ambos os tracks
ou se overlay e lyrics têm limites diferentes.

### Arquivos envolvidos (a confirmar)

| Arquivo | O que verificar |
|---|---|
| `legendas.py` (app-editor) | Constantes de limite de chars por track (overlay, lyrics) |
| Teste `test_seed_best_of_opera_valores_corretos` | Falha conhecida: `fontsize` 63 vs 40 — não confundir com o limite de chars |
| Frontend de review de legendas (app-portal) | Se existe interface de edição de tempos |

### Critério de done

- Limites atualizados no código e confirmados via output real (legenda gerada com 73 chars sem corte).
- Edição manual de tempos: escopo definido (UI simples vs. editor completo) antes de implementar.

---

## Frente 4 — BUG-E: `cached_videos` sem `brand_slug`

### Estado atual

Tabela `cached_videos` no banco não tem coluna `brand_slug`.

**Arquivo:** `app-curadoria/backend/database.py`

### Impacto atual

Nenhum — BO e RC usam nomes de categorias diferentes, então os caches não colidem na prática.

### Risco futuro

Se uma nova marca usar a mesma categoria que BO ou RC (ex.: categoria "Opera"), o cache será
compartilhado silenciosamente. Vídeos de uma marca aparecerão na curadoria de outra.

### Fix necessário

1. Adicionar coluna `brand_slug VARCHAR` na tabela `cached_videos`.
2. Migration para adicionar a coluna (sem valor padrão obrigatório — NULL para registros antigos é aceitável).
3. Filtrar queries de cache por `brand_slug` onde relevante.

### Prioridade

🟡 Baixa urgência — risco só se materializa com nova marca. Implementar antes de onboarding
de terceira marca.

---

## Pendências fora de escopo deste PRD

| Item | Status | Observação |
|---|---|---|
| HARDENING tarefas 05/06/10 (gemini retry, R2 retry, connection pooling) | 🟠 | Verificar no código se já existem ou não — ver RESUMO-DIAGNOSTICO § 7 |
| 7 decisões editoriais RC (sessão 12) | 🟠 | Aguardam resposta do Bolivar — bloqueia alguns detalhes da Frente 3 |
| Reorganizar MEMORIA-VIVA.md | 🟡 | Arquivo com 27k tokens — mover para `arquivo/` na próxima oportunidade |
| Credenciais em MEMORIA-VIVA.md | 🟡 | Senha PostgreSQL e Railway token em texto plano — rotacionar se repo for exposto |

---

## Ordem de execução sugerida

```
Frente 1 (deploys) → Frente 2 (BUG-F investigação) → Frente 3 (legendas chars) → Frente 4 (BUG-E)
```

**Justificativa:**
- Frente 1 é blocker de produção — código pronto, só precisa de push com aprovação.
- Frente 2 é bug crítico de UX mas precisa de investigação antes de qualquer fix.
- Frente 3 depende de confirmação do Bolivar sobre o valor 73 chars.
- Frente 4 é prevenção, sem urgência imediata.

---

## Arquivos a ler antes de criar o SPEC-003

| Arquivo | Por quê |
|---|---|
| `app-editor/backend/app/routes/` (endpoint de projetos) | Investigar BUG-F — filtro de marca |
| `app-portal/` (páginas de projetos) | Investigar BUG-F — contexto de marca no frontend |
| `app-curadoria/backend/database.py` | Confirmar ausência de `brand_slug` em `cached_videos` |
| `legendas.py` (localizar via grep) | Confirmar constantes de limite de chars atuais |
| `app-editor/CLAUDE.md` | Regras de código do editor antes de qualquer mudança |

---

## Próximo passo

Criar `SPEC-003-pendencias-criticas.md` após:
1. Confirmar com Bolivar o valor de chars para lyrics (73 ou diferente)
2. Investigar BUG-F no código (ler endpoints + frontend antes de propor fix)
3. Verificar tarefas HARDENING 05/06/10 no código-fonte
