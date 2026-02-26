#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$REPO_ROOT/.env.railway"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "❌ Arquivo .env.railway não encontrado em $REPO_ROOT"
    exit 1
fi
source "$ENV_FILE"
missing=()
[[ -z "${RAILWAY_TOKEN:-}" ]] && missing+=("RAILWAY_TOKEN")
[[ -z "${RAILWAY_PROJECT_ID:-}" ]] && missing+=("RAILWAY_PROJECT_ID")
[[ -z "${RAILWAY_SERVICE_ID_EDITOR:-}" ]] && missing+=("RAILWAY_SERVICE_ID_EDITOR")
[[ -z "${RAILWAY_ENVIRONMENT_ID:-}" ]] && missing+=("RAILWAY_ENVIRONMENT_ID")
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "❌ Variáveis faltando no .env.railway: ${missing[*]}"
    exit 1
fi
API_URL="https://backboard.railway.app/graphql/v2"
SID="$RAILWAY_SERVICE_ID_EDITOR"
EID="$RAILWAY_ENVIRONMENT_ID"
gql() {
    local query="$1"
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
        -H "Authorization: Bearer $RAILWAY_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$query")
    local http_code
    http_code=$(echo "$response" | tail -1)
    local body
    body=$(echo "$response" | sed '$d')
    if [[ "$http_code" != "200" ]]; then
        echo "❌ HTTP $http_code — resposta: $body" >&2
        return 1
    fi
    if echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'errors' not in d else 1)" 2>/dev/null; then
        echo "$body"
    else
        echo "❌ Erro GraphQL:" >&2
        echo "$body" | python3 -c "import sys,json; [print(f'  → {e[\"message\"]}') for e in json.load(sys.stdin).get('errors',[])]" 2>/dev/null
        return 1
    fi
}
cmd_list() {
    echo "📋 Variáveis do serviço Editor:"
    echo ""
    local result
    result=$(gql "{\"query\": \"{ variables(serviceId: \\\"$SID\\\", environmentId: \\\"$EID\\\", projectId: \\\"$RAILWAY_PROJECT_ID\\\") }\"}")
    echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
variables = data.get('data', {}).get('variables', {})
if not variables:
    print('  (nenhuma variável encontrada)')
else:
    max_key = max(len(k) for k in variables)
    for k in sorted(variables):
        v = variables[k]
        display = v
        if any(word in k.upper() for word in ['SECRET', 'KEY', 'TOKEN', 'PASSWORD', 'PRIVATE']):
            display = v[:4] + '...' + v[-4:] if len(v) > 12 else '****'
        print(f'  {k:<{max_key}}  =  {display}')
print(f\"\nTotal: {len(variables)} variáveis\")
"
}
cmd_get() {
    local var_name="$1"
    local result
    result=$(gql "{\"query\": \"{ variables(serviceId: \\\"$SID\\\", environmentId: \\\"$EID\\\", projectId: \\\"$RAILWAY_PROJECT_ID\\\") }\"}")
    echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
variables = data.get('data', {}).get('variables', {})
name = '$var_name'
if name in variables:
    print(variables[name])
else:
    print(f'❌ Variável {name} não encontrada', file=sys.stderr)
    sys.exit(1)
"
}
cmd_set() {
    local var_name="$1"
    local var_value="$2"
    local escaped_value
    escaped_value=$(echo "$var_value" | sed 's/\\/\\\\/g; s/"/\\"/g')
    local result
    result=$(gql "{\"query\": \"mutation { variableUpsert(input: { serviceId: \\\"$SID\\\", environmentId: \\\"$EID\\\", projectId: \\\"$RAILWAY_PROJECT_ID\\\", name: \\\"$var_name\\\", value: \\\"$escaped_value\\\" }) }\"}")
    if [[ $? -eq 0 ]]; then
        echo "✅ $var_name definida com sucesso"
    fi
}
cmd_delete() {
    local var_name="$1"
    local result
    result=$(gql "{\"query\": \"mutation { variableDelete(input: { serviceId: \\\"$SID\\\", environmentId: \\\"$EID\\\", projectId: \\\"$RAILWAY_PROJECT_ID\\\", name: \\\"$var_name\\\" }) }\"}")
    if [[ $? -eq 0 ]]; then
        echo "🗑️  $var_name removida"
    fi
}
cmd_redeploy() {
    echo "🔄 Forçando redeploy do serviço Editor..."
    local result
    result=$(gql "{\"query\": \"mutation { serviceInstanceRedeploy(serviceId: \\\"$SID\\\", environmentId: \\\"$EID\\\") }\"}")
    if [[ $? -eq 0 ]]; then
        echo "✅ Redeploy iniciado."
    fi
}
case "${1:-help}" in
    list)      cmd_list ;;
    get)       cmd_get "${2:?Uso: $0 get NOME_VAR}" ;;
    set)       cmd_set "${2:?Uso: $0 set NOME_VAR valor}" "${3:?Uso: $0 set NOME_VAR valor}" ;;
    delete)    cmd_delete "${2:?Uso: $0 delete NOME_VAR}" ;;
    redeploy)  cmd_redeploy ;;
    *)         echo "Uso: $0 {list|get|set|delete|redeploy} [args]" ;;
esac
