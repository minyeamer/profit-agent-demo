#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Use .env as a local fallback, but never overwrite connection settings that
# the caller intentionally supplied (for example, the public demo database).
ENV_NAMES=(PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD PGSCHEMA PROFIT_DAILY_FUNCTION)
# macOS ships Bash 3.2, which does not support associative arrays. Preserve
# caller-supplied connection settings using shell variables and restore them
# after sourcing the local .env fallback.
for name in "${ENV_NAMES[@]}"; do
  if [[ "${!name+x}" == x ]]; then
    eval "ORIGINAL_${name}_SET=1"
    eval "ORIGINAL_${name}=\${${name}}"
  else
    eval "ORIGINAL_${name}_SET=0"
  fi
done

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

for name in "${ENV_NAMES[@]}"; do
  eval "if [[ \${ORIGINAL_${name}_SET} == 1 ]]; then export ${name}=\"\${ORIGINAL_${name}}\"; fi"
done

exec "${ROOT_DIR}/.venv/bin/profit-agent-mcp"
