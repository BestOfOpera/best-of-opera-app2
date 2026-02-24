# Best of Opera — Instruções Gerais

## Deploy automático
Após qualquer alteração de código, SEMPRE fazer commit e push para o `main`:
```bash
git add <arquivos alterados>
git commit -m "mensagem descritiva em português"
git push origin main
```
O Railway faz redeploy automático a cada push. Nunca deixar alterações sem deploy.

## Autonomia
- Não pedir confirmação para commit/push de código funcional.
- Se houver erro de build/teste, resolver antes de fazer push.

## Stack resumida
Ver HANDOFF.md para arquitetura completa e IDs Railway.
- Portal: `app-portal/` (Next.js)
- Redator: `app-redator/` (FastAPI + React)
- Editor: `app-editor/` (FastAPI + React)
- Curadoria: `app-curadoria/` (FastAPI)
- UI Language: Português (PT-BR)
