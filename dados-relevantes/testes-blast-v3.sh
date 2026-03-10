#!/bin/bash

# ==============================================================================
# SCRIPT DE TESTES V3 - DASHBOARD & REPORTS (API BACKEND)
# ==============================================================================
# Endpoint Base: https://editor-backend-production.up.railway.app/api/v1/editor
# ==============================================================================

BASE_URL="https://editor-backend-production.up.railway.app/api/v1/editor"

echo "Iniciando testes da API BLAST v3..."
echo "URL Base: $BASE_URL"
echo ""

# ------------------------------------------------------------------------------
# 1. DASHBOARD
# ------------------------------------------------------------------------------
echo "========================================="
echo " TESTES DASHBOARD"
echo "========================================="

# [GET] /dashboard/stats 
# O que testa: Totais de edições, renders, status geral da produção do banco.
echo -e "\n[GET] /dashboard/stats"
curl -s -X GET "$BASE_URL/dashboard/stats" | jq

# [GET] /dashboard/edicoes-recentes
# O que testa: Lista as últimas edições criadas (limit=5).
echo -e "\n[GET] /dashboard/edicoes-recentes?limit=5"
curl -s -X GET "$BASE_URL/dashboard/edicoes-recentes?limit=5" | jq

# [GET] /dashboard/fila
# O que testa: Estado do Worker processador de fila de background.
echo -e "\n[GET] /dashboard/fila"
curl -s -X GET "$BASE_URL/dashboard/fila" | jq

# [GET] /dashboard/pipeline
# O que testa: Status atual das etapas do pipeline, processos em andamento e travados.
echo -e "\n[GET] /dashboard/pipeline"
curl -s -X GET "$BASE_URL/dashboard/pipeline" | jq


# [GET] /dashboard/saude
# O que testa: Saúde da conexão com banco, worker e R2.
echo -e "\n[GET] /dashboard/saude"
curl -s -X GET "$BASE_URL/dashboard/saude" | jq


# ------------------------------------------------------------------------------
# 2. REPORTS
# ------------------------------------------------------------------------------
echo -e "\n========================================="
echo " TESTES REPORTS"
echo "========================================="

# [GET] /reports
# O que testa: Listagem de todos os reports de bug/qualidade (com limit).
echo -e "\n[GET] /reports?limit=5"
curl -s -X GET "$BASE_URL/reports?limit=5" | jq


# [POST] /reports
# O que testa: Criação de um novo report no banco de dados.
echo -e "\n[POST] /reports"
echo "Enviando payload..."
RESPONSE_POST=$(curl -s -X POST "$BASE_URL/reports" \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "bug",
    "titulo": "Erro no script de carga (Teste cURL)",
    "descricao": "Teste automatizado gerado para validar POST do endpoint de reports",
    "prioridade": "alta"
  }')
  
echo "$RESPONSE_POST" | jq

# Pegamos o ID retornado via jq para encadear os testes de GET e PATCH por id.
REPORT_ID=$(echo "$RESPONSE_POST" | jq -r '.id // empty')

if [ -n "$REPORT_ID" ]; then
    echo -e "\n--> Report criado com sucesso. Testando endpoints especificos para ID: $REPORT_ID"

    # [GET] /reports/{id}
    # O que testa: Endpoint de resgate de details de 1 report pelo ID.
    echo -e "\n[GET] /reports/$REPORT_ID"
    curl -s -X GET "$BASE_URL/reports/$REPORT_ID" | jq

    # [PATCH] /reports/{id}
    # O que testa: Atualização parcial de dados do report criado.
    echo -e "\n[PATCH] /reports/$REPORT_ID"
    curl -s -X PATCH "$BASE_URL/reports/$REPORT_ID" \
      -H "Content-Type: application/json" \
      -d '{
        "status": "resolvido",
        "prioridade": "baixa",
        "descricao": "Resolvido via PATCH teste automatizado."
      }' | jq
else
    echo -e "\n[!] Falha ao criar Report via POST ou não retornou campo 'id'. Pulando testes GET e PATCH por ID."
fi


# [GET] /reports/resumo
# NOTA: Solicitado no escopo do teste, mas não implementado no backend app/routes/reports.py.
echo -e "\n[GET] /reports/resumo"
echo "ATENCAO: Este endpoint retornará 404 (Not Found) pois não existe no código backend!"
curl -s -w "\nHTTP Code: %{http_code}\n" -X GET "$BASE_URL/reports/resumo" | jq . 2>/dev/null || echo ""


echo -e "\n========================================="
echo " TESTES FINALIZADOS"
echo "========================================="
