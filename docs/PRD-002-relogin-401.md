# PRD-002 — Relogin 401
**Data:** 19/03/2026
**Status:** PENDENTE
**Origem:** RESUMO-DIAGNOSTICO-190326.md § 5 — "Relogin 401 (bug ativo)"

---

## Contexto

Usuários relatam que relogin falha com 401 a menos que o browser limpe o localStorage.
O bug afeta todos os usuários do sistema. Causa raiz dupla identificada em 19/03/2026 via leitura direta do código.

---

## Causa raiz 1 — Email case-sensitive no backend

**Arquivo:** `app-editor/backend/app/routes/auth.py` linhas 88–91

```python
# ATUAL (bug)
usuario = db.query(Usuario).filter(
    Usuario.email == body.email,
    Usuario.ativo == True,
).first()
```

PostgreSQL compara `VARCHAR` com case-sensitivity por padrão.
Se o usuário foi cadastrado como `User@Email.com` e tenta logar com `user@email.com` → nenhuma linha encontrada → 401 imediato.

**Não investigado ainda:** como os usuários estão cadastrados no banco (maiúscula ou minúscula). Verificar antes do fix.

---

## Causa raiz 2 — `loadUser()` apaga token em qualquer erro

**Arquivo:** `app-portal/lib/auth-context.tsx` linhas 53–58

```typescript
// ATUAL (bug)
} catch (err) {
  if (!signal.aborted) {
    console.error("Failed to load user:", err)
    localStorage.removeItem("bo_auth_token")   // ← apaga em QUALQUER erro
    setUser(null)
  }
}
```

O `catch` remove `bo_auth_token` independentemente do tipo de erro:
- `ApiError` status 401 — token expirado — remoção **correta**
- `ApiError` status 5xx — servidor caiu — remoção **errada**
- `TypeError` / `AbortError` — falha de rede ou timeout — remoção **errada**

**Ciclo que reproduce o bug:**
1. Token expirou → `getMe()` retorna 401 → token removido → usuário redirecionado a `/login`
2. Usuário faz novo login → token novo salvo → `login()` chama `loadUser()`
3. `getMe()` falha por erro transitório (rede, backend lento) → catch remove o token recém-criado
4. `router.push("/dashboard")` executa, mas token já sumiu
5. Dashboard chama `loadUser()` no mount → sem token → `setUser(null)` → usuário aparece deslogado

---

## Causa raiz 3 — `base.ts` apaga token em qualquer 401, de qualquer endpoint

**Arquivo:** `app-portal/lib/api/base.ts` linhas 82–85

```typescript
// ATUAL
if (res.status === 401 && typeof window !== "undefined") {
  localStorage.removeItem("bo_auth_token")
  window.dispatchEvent(new CustomEvent("bo:unauthorized"))
}
```

Qualquer chamada à API que retorne 401 (não só `/me`) apaga o token e dispara logout.
Exemplos de 401 que NÃO indicam token inválido:
- Endpoint de admin acessado por usuário não-admin (deveria ser 403, mas se mal configurado retorna 401)
- Backend de curadoria ou redator com auth própria retornando 401 por configuração diferente

**Avaliação:** Este comportamento é conservador do ponto de vista de segurança e está correto para o caso nominal (token expirado). O problema principal é a Causa raiz 2 — que faz o mesmo logout por erros que não têm relação com validade do token. Corrigir CR-2 já elimina o ciclo. CR-3 é baixo risco; não alterar sem validar com o Bolivar.

---

## Arquivos envolvidos

| Arquivo | Linha(s) | Componente | Fix necessário |
|---|---|---|---|
| `app-editor/backend/app/routes/auth.py` | 88–91 | Backend login | Comparação case-insensitive |
| `app-portal/lib/auth-context.tsx` | 53–58 | Frontend auth | Só apagar token se 401 explícito |
| `app-portal/lib/api/base.ts` | 82–85 | Cliente HTTP | Sem alteração (ver CR-3) |

---

## Estado atual do código (lido em 19/03/2026)

### `auth.py` — comparação de email
```python
# linha 88 — BUG ATIVO
Usuario.email == body.email
```
Nenhuma normalização de case. SQLAlchemy passa o valor diretamente ao PostgreSQL.
Também afeta `registrar()` (linha 117): `Usuario.email == body.email` — duplicata detectada de forma case-sensitive também.

### `auth-context.tsx` — loadUser catch
```typescript
# linha 56 — BUG ATIVO
localStorage.removeItem("bo_auth_token")
```
Executado em qualquer exceção. `ApiError` com status 401 é o único caso correto para remoção.

### `auth.py` — `criar_token` / `get_current_user`
Funcionam corretamente. JWT decodificado por `user_id` (int), não por email — portanto case-sensitivity do email não afeta tokens já emitidos.

---

## Falsos alarmes descartados

| Suspeita | Veredicto | Motivo |
|---|---|---|
| JWT_EXPIRY_HOURS ignorado | ❌ Não é bug | Usado em `middleware/auth.py:20` — expiração aplicada corretamente |
| `get_current_user` usa email para busca | ❌ Não é bug | Busca por `user_id` (int) — imune ao case-sensitivity |
| AbortController faz race condition | ❌ Não é bug | `signal.aborted` protege corretamente atualizações tardias |

---

## Critério de "bug corrigido"

1. Usuário cadastrado como `User@Email.com` consegue logar digitando `user@email.com`
2. Login bem-sucedido + erro de rede imediato no `getMe()` **não** derruba a sessão
3. Login bem-sucedido + servidor respondendo normalmente → usuário permanece logado no dashboard
4. Sem necessidade de limpar localStorage entre sessões

**⚠️ BLOCKER antes do fix da CR-1:** verificar como os emails estão armazenados no banco de produção (`SELECT email FROM usuarios`). Se todos são lowercase, o bug de case nunca disparou na prática — corrigir assim mesmo para prevenir regressão futura.

---

## Próximo passo

Criar `SPEC-002-relogin-401.md` com:
- Task 01: Fix case-insensitive em `auth.py` login + registrar
- Task 02: Fix catch seletivo em `auth-context.tsx`
- Task 03: Verificar emails no banco (BLOCKER para confirmar impacto real da CR-1)
- Critério de done por tarefa
