#!/bin/sh
set -eu

if [ ! -f .env ]; then
  echo "missing .env; copy .env.example to .env and set secrets first" >&2
  exit 1
fi

set -a
. ./.env
set +a

api_bind_host="${API_BIND_HOST:-127.0.0.1}"
api_port="${API_PORT:-8000}"
mcp_bind_host="${MCP_BIND_HOST:-127.0.0.1}"
mcp_port="${MCP_PORT:-8001}"

echo "checking compose configuration"
docker compose config >/dev/null

echo "checking service status"
docker compose ps

echo "checking API health"
curl -fsS "http://${api_bind_host}:${api_port}/health" >/dev/null
echo "api health ok"

echo "checking API readiness"
curl -fsS -H "Authorization: Bearer ${API_ADMIN_TOKEN}" "http://${api_bind_host}:${api_port}/ready" >/dev/null
echo "api ready ok"

echo "checking MCP listener"
if curl -fsS -X POST "http://${mcp_bind_host}:${mcp_port}/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"aiconnect-smoke-check","version":"1.0"}}}' >/dev/null; then
  echo "mcp endpoint accepted initialize request"
else
  echo "mcp endpoint did not accept initialize request" >&2
  exit 1
fi

echo "smoke check complete"
