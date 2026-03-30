#!/usr/bin/env bash
# .devcontainer/start-servers.sh
# Builds and starts the Jira and Postman MCP server Docker containers.
# Called by devcontainer postStartCommand every time the Codespace starts.

set -e

COMPOSE_FILE="$(dirname "$0")/docker-compose.yaml"

echo "[das_buddy] Building and starting MCP server containers..."
docker compose -f "$COMPOSE_FILE" -p das_buddy up --build -d

echo "[das_buddy] Containers started."
echo "  Jira MCP  : http://localhost:8001/sse"
echo "  Post MCP  : http://localhost:8002/sse"
echo ""
echo "Container logs:"
echo "  docker compose -f $COMPOSE_FILE -p das_buddy logs -f"
