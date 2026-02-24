#!/bin/bash
# Script para configurar variáveis R2 no Railway via GraphQL API
# Requer: RAILWAY_API_TOKEN definido como variável de ambiente
#
# Uso: RAILWAY_API_TOKEN=xxx bash scripts/configure-railway-r2.sh

set -euo pipefail

if [ -z "${RAILWAY_API_TOKEN:-}" ]; then
  echo "Erro: RAILWAY_API_TOKEN não definido"
  echo "Uso: RAILWAY_API_TOKEN=xxx bash $0"
  exit 1
fi

API="https://backboard.railway.app/graphql/v2"
PROJECT_ID="c4d0468d-f3da-4765-b582-42cf6ef5ff66"
ENV_ID="4ec5a08f-d29e-4d7b-a54d-a3e161edd716"

# Service IDs
REDATOR_ID="fade4ac2-8774-4287-b87d-7f2559898dcc"
EDITOR_ID="7e42a778-aa1e-4648-9ce1-07f5d6896fd5"
CURADORIA_ID="e3eb935a-7b11-44fd-889f-fbd45edb0602"

# R2 credentials
R2_ENDPOINT="https://77dc0fdddc9bec6bf3c801cc596034ab.r2.cloudflarestorage.com"
R2_ACCESS_KEY="bb4e89002c7628d143e72d07b2ab0e9d"
R2_SECRET_KEY="5dd3e9232a0cd936a52371eb324d89555d564e732bf29e9d2ca3a440d7de3c2d"
R2_BUCKET="appbestofopera"

upsert_var() {
  local service_id=$1
  local name=$2
  local value=$3
  echo "  Setting $name on $service_id..."
  curl -s -X POST "$API" \
    -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"query\": \"mutation { variableUpsert(input: { projectId: \\\"$PROJECT_ID\\\", environmentId: \\\"$ENV_ID\\\", serviceId: \\\"$service_id\\\", name: \\\"$name\\\", value: \\\"$value\\\" }) }\"
    }" | python3 -c "import sys,json; print(json.load(sys.stdin))" 2>/dev/null || true
}

update_root_dir() {
  local service_id=$1
  local service_name=$2
  echo "  Setting rootDirectory to repo root for $service_name..."
  curl -s -X POST "$API" \
    -H "Authorization: Bearer $RAILWAY_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"query\": \"mutation { serviceInstanceUpdate(serviceId: \\\"$service_id\\\", environmentId: \\\"$ENV_ID\\\", input: { rootDirectory: \\\"/\\\" }) }\"
    }" | python3 -c "import sys,json; print(json.load(sys.stdin))" 2>/dev/null || true
}

echo "=== Configurando variáveis R2 no Railway ==="

for SERVICE_ID in $EDITOR_ID $CURADORIA_ID $REDATOR_ID; do
  case $SERVICE_ID in
    $EDITOR_ID)   echo "Editor:" ;;
    $CURADORIA_ID) echo "Curadoria:" ;;
    $REDATOR_ID)   echo "Redator:" ;;
  esac
  upsert_var "$SERVICE_ID" "R2_ENDPOINT" "$R2_ENDPOINT"
  upsert_var "$SERVICE_ID" "R2_ACCESS_KEY" "$R2_ACCESS_KEY"
  upsert_var "$SERVICE_ID" "R2_SECRET_KEY" "$R2_SECRET_KEY"
  upsert_var "$SERVICE_ID" "R2_BUCKET" "$R2_BUCKET"
  echo ""
done

echo "=== Atualizando rootDirectory para repo root ==="
update_root_dir "$EDITOR_ID" "Editor"
update_root_dir "$CURADORIA_ID" "Curadoria"
update_root_dir "$REDATOR_ID" "Redator"

echo ""
echo "Pronto! Faça redeploy dos serviços para aplicar."
