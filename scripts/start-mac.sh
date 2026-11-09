#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || cp .env.example .env
docker compose up --build -d
echo "Frontend: http://localhost:3000"
echo "Swagger:  http://localhost:8000/docs"
