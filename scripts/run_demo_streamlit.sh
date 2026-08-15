#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f "${ROOT_DIR}/.env.demo" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env.demo"
  set +a
fi

# PostgreSQL runs in Docker and the chat UI runs on the macOS host.
export PGHOST="${DEMO_PGHOST:-127.0.0.1}"
export PGPORT="${DEMO_PGPORT:-15432}"
export PGDATABASE="${DEMO_PGDATABASE:-profit_demo}"
export PGUSER="${DEMO_PGUSER:-demo_readonly}"
export PGPASSWORD="${DEMO_PGPASSWORD:-demo_password}"
export PGSCHEMA="${PGSCHEMA:-analytics}"
export PROFIT_DAILY_FUNCTION="${PROFIT_DAILY_FUNCTION:-analytics.profit_daily}"
export STREAMLIT_BIND_ADDRESS="${DEMO_STREAMLIT_BIND_ADDRESS:-127.0.0.1}"
export STREAMLIT_PORT="${STREAMLIT_PORT:-8510}"

: "${API_TYPE:?API_TYPE을 설정하세요.}"
: "${API_KEY:?API_KEY를 설정하세요.}"
: "${MODEL:?MODEL을 설정하세요.}"

exec env -u PYTHONPATH uv run streamlit run src/profit_agent_demo/web_app.py \
  --server.address="${STREAMLIT_BIND_ADDRESS}" \
  --server.port="${STREAMLIT_PORT}"
