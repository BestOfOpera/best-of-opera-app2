# Amostra auditada (Frente B)

15 findings selecionados de 33 (cobertura: 45%).

## Critério de seleção

| Bucket | IDs | Justificativa |
|--------|-----|----------------|
| Sprint 1 completo (7) | R1, R2, R3, R4, R5, R7, P1-Trans | PROMPT 9 §3.2 B.2 — os 7 prioritários vão a produção primeiro |
| CRÍTICAS adicionais (2) | Ed-MIG1, P1-Ed5 | Ed-MIG1: migration SQL que força DB no startup (risco alto). P1-Ed5: lyrics (conteúdo editorial de peso) |
| ALTAS (3) | P1-Doc, P2-PathA-1, P3-Prob | Diversidade: docstring / clamp BO / algoritmo — cobre 3 naturezas distintas |
| MÉDIAS (3) | P1-UI1, C1, T9-spam | 1 por app: portal UI / curadoria filename / editor VARCHAR |

Das 7 CRÍTICAS do Sprint 1, apenas 5 são de fato CRÍTICAS na tabela; R4 e R5 são ALTAS. Isso será registrado em D2 (severidade inflada?).

## Distribuição severidade da amostra (real vs declarada)

- **CRÍTICA real:** 9 (R1, R2, R3, R7, P1-Trans, Ed-MIG1, P1-Ed5, + 2 adicionais que já são R4/R5 marcadas ALTA)
- Ajuste: 7 CRÍTICA efetiva + 5 ALTA + 3 MÉDIA = 15

## Finding IDs e path:linha declarados

| ID | Path:linha | Severidade | Categoria |
|----|------------|------------|-----------|
| R1 | app-redator/backend/services/claude_service.py:869-873 | CRÍTICA | T1+log |
| R2 | app-redator/backend/services/claude_service.py:880 | CRÍTICA | T2 |
| R3 | app-redator/backend/services/claude_service.py:921, :928 | CRÍTICA | T1+T2 sem log |
| R4 | app-redator/backend/services/claude_service.py:960 | ALTA | clamp |
| R5 | app-redator/backend/services/claude_service.py:1009 | ALTA | clamp |
| R7 | app-redator/backend/services/claude_service.py:659-729 | CRÍTICA | T6 |
| P1-Trans | app-redator/backend/routers/translation.py:189 | CRÍTICA | hardcode |
| Ed-MIG1 | app-editor/backend/app/main.py:363-370 | CRÍTICA | SQL migration |
| P1-Ed5 | app-editor/backend/app/services/legendas.py:653 | CRÍTICA | T1 |
| P1-Doc | app-redator/backend/services/translate_service.py:533 | ALTA (doc) | docstring |
| P2-PathA-1 | app-redator/backend/services/claude_service.py:434-445 | ALTA | clamp |
| P3-Prob | app-redator/backend/services/claude_service.py:819-887 | ALTA | algoritmo |
| P1-UI1 | app-portal/app/(app)/admin/marcas/nova/page.tsx:450-462 | MÉDIA | UI default |
| C1 | app-curadoria/backend/services/download.py:117 | MÉDIA | T1 |
| T9-spam | app-editor/backend/app/main.py:77 | MÉDIA | VARCHAR |
