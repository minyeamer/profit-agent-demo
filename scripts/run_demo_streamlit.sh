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

HERMES_COMMAND="${HERMES_COMMAND:-}"
if [[ -z "${HERMES_COMMAND}" ]]; then
  HERMES_COMMAND="$(command -v hermes || true)"
elif [[ "${HERMES_COMMAND}" != */* ]]; then
  HERMES_COMMAND="$(command -v "${HERMES_COMMAND}" || true)"
fi
if [[ -z "${HERMES_COMMAND}" || ! -x "${HERMES_COMMAND}" ]]; then
  echo "Hermes CLI를 찾을 수 없습니다. 먼저 Hermes Desktop/CLI를 설치하고 로그인하세요." >&2
  exit 1
fi

# PostgreSQL runs in Docker, while Hermes OAuth runs on the macOS host.
export PGHOST="${DEMO_PGHOST:-127.0.0.1}"
export PGPORT="${DEMO_PGPORT:-15432}"
export PGDATABASE="${DEMO_PGDATABASE:-profit_demo}"
export PGUSER="${DEMO_PGUSER:-demo_readonly}"
export PGPASSWORD="${DEMO_PGPASSWORD:-demo_password}"
export PGSCHEMA="${PGSCHEMA:-analytics}"
export PROFIT_DAILY_FUNCTION="${PROFIT_DAILY_FUNCTION:-analytics.profit_daily}"
export AGENT_BACKEND=hermes
export HERMES_COMMAND
export STREAMLIT_BIND_ADDRESS="${DEMO_STREAMLIT_BIND_ADDRESS:-127.0.0.1}"
export STREAMLIT_PORT="${STREAMLIT_PORT:-8510}"

exec env -u PYTHONPATH uv run streamlit run src/profit_agent_demo/web_app.py \
  --server.address="${STREAMLIT_BIND_ADDRESS}" \
  --server.port="${STREAMLIT_PORT}"
