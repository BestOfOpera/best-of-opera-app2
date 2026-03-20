# SPEC-002 — Relogin 401
**Data:** 19/03/2026
**Status:** CONCLUÍDO
**Origem:** PRD-002-relogin-401.md

---

## Ordem de execução

```
Task 03 (verificação banco) → Task 01 (auth.py) → Task 02 (auth-context.tsx)
```

Task 03 é BLOCKER para confirmar impacto real da CR-1.
Task 01 e Task 02 são independentes entre si mas Task 03 deve ser feita antes de Task 01 para informar a decisão.

---

## Task 01 — Fix case-insensitive em `auth.py`

**Arquivo:** `app-editor/backend/app/routes/auth.py`
**Status:** CONCLUÍDO (19/03/2026)
**⚠️ DEPLOY PENDENTE:** `editor-backend` no Railway
**BLOCKER:** Executar Task 03 antes — confirmar distribuição de emails no banco.

### Mudança em `login()` (linha 88–91)

```python
# ANTES (bug)
usuario = db.query(Usuario).filter(
    Usuario.email == body.email,
    Usuario.ativo == True,
).first()

# DEPOIS
from sqlalchemy import func

usuario = db.query(Usuario).filter(
    func.lower(Usuario.email) == body.email.lower(),
    Usuario.ativo == True,
).first()
```

### Mudança em `registrar()` (linha 117)

```python
# ANTES (bug)
existente = db.query(Usuario).filter(Usuario.email == body.email).first()

# DEPOIS
existente = db.query(Usuario).filter(
    func.lower(Usuario.email) == body.email.lower()
).first()
```

### Notas
- `func` já está disponível em SQLAlchemy; verificar se `from sqlalchemy import func` já está importado no topo do arquivo antes de adicionar.
- A normalização `body.email.lower()` garante que o valor comparado é lowercase em ambos os lados.
- Não alterar `criar_token` nem `get_current_user` — esses usam `user_id` (int), imunes ao case.

### Critério de done
- Usuário cadastrado como `User@Email.com` consegue logar digitando `user@email.com`
- Tentativa de registrar `user@email.com` quando `User@Email.com` já existe retorna 409

---

## Task 02 — Fix catch seletivo em `auth-context.tsx`

**Arquivo:** `app-portal/lib/auth-context.tsx`
**Linhas:** 53–58
**Status:** CONCLUÍDO (19/03/2026)
**⚠️ DEPLOY PENDENTE:** `portal` no Railway

### Mudança

```typescript
// ANTES (bug)
} catch (err) {
  if (!signal.aborted) {
    console.error("Failed to load user:", err)
    localStorage.removeItem("bo_auth_token")   // apaga em QUALQUER erro
    setUser(null)
  }
}

// DEPOIS
} catch (err) {
  if (!signal.aborted) {
    console.error("Failed to load user:", err)
    // Só remover token se o erro for 401 explícito (token inválido/expirado).
    // Erros de rede, timeout, 5xx ou AbortError NÃO invalidam o token.
    if (err instanceof ApiError && err.status === 401) {
      localStorage.removeItem("bo_auth_token")
      setUser(null)
    }
    // Se não for 401, manter o token e não alterar o estado do usuário.
    // O usuário será carregado na próxima chamada bem-sucedida.
  }
}
```

### Import necessário
Verificar se `ApiError` já está importada no topo do arquivo. Se não:
```typescript
import { ApiError } from "@/lib/api/base"
```

### Notas
- O evento `bo:unauthorized` (disparado por `base.ts`) continua chamando `logout()` — isso é correto e não muda.
- Essa correção elimina o ciclo descrito no PRD: login bem-sucedido + erro transitório no `getMe()` deixará de derrubar a sessão.
- Não alterar `base.ts` (CR-3 marcada como baixo risco no PRD — aguarda validação com Bolivar).

### Critério de done
- Login bem-sucedido + simulação de erro de rede no `getMe()` → usuário permanece logado
- Login bem-sucedido + token expirado (401) → usuário redirecionado a `/login` normalmente
- Sem necessidade de limpar localStorage entre sessões

---

## Task 03 — Verificar emails no banco (BLOCKER para CR-1)

**Tipo:** Verificação (não modifica código)
**Status:** CONCLUÍDO (19/03/2026)

### Query a executar

```sql
-- Verificar distribuição de case nos emails cadastrados
SELECT
  email,
  CASE WHEN email = lower(email) THEN 'lowercase' ELSE 'mixed/uppercase' END AS case_status
FROM usuarios
ORDER BY case_status DESC, email;
```

Ou resumido:
```sql
SELECT
  COUNT(*) FILTER (WHERE email != lower(email)) AS emails_com_uppercase,
  COUNT(*) AS total
FROM usuarios;
```

### Interpretação do resultado

| Resultado | Ação |
|---|---|
| `emails_com_uppercase = 0` | Bug de case nunca disparou na prática. Corrigir assim mesmo para prevenir regressão futura. |
| `emails_com_uppercase > 0` | Bug ativo. Normalizar emails no banco ANTES ou JUNTO com o fix do código. |

### Se houver emails com uppercase no banco

Executar (em transação, com backup):
```sql
BEGIN;
UPDATE usuarios SET email = lower(email) WHERE email != lower(email);
-- Verificar resultado antes de confirmar:
SELECT email FROM usuarios WHERE email != lower(email);
COMMIT;
```

### Como acessar o banco
Ver credenciais em `dados-relevantes/`. Banco está no Railway (PostgreSQL).

### Critério de done
- Query executada e resultado documentado
- Se havia emails uppercase: normalização aplicada e confirmada
- Resultado registrado no PRD-002 ou em nota neste SPEC (atualizar campo abaixo)

**Resultado:** `emails_com_uppercase = 0` de 8 usuários (19/03/2026). Todos os emails já estão em lowercase. Nenhuma normalização necessária. Fix de código aplicado assim mesmo para prevenir regressão futura.

---

## Arquivos a modificar

| Arquivo | Task | Linhas | Tipo de mudança |
|---|---|---|---|
| `app-editor/backend/app/routes/auth.py` | 01 | 88–91, 117 | Edição — comparação case-insensitive |
| `app-portal/lib/auth-context.tsx` | 02 | 53–58 | Edição — catch seletivo por status 401 |
| `app-portal/lib/api/base.ts` | — | — | Sem alteração |

---

## Critério global de done

1. Usuário cadastrado como `User@Email.com` consegue logar digitando `user@email.com`
2. Login bem-sucedido + erro de rede imediato no `getMe()` **não** derruba a sessão
3. Login bem-sucedido + servidor respondendo normalmente → usuário permanece logado no dashboard
4. Sem necessidade de limpar localStorage entre sessões
5. Task 03 executada e resultado documentado
