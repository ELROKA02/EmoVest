#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_triple="${TAURI_TARGET_TRIPLE:?TAURI_TARGET_TRIPLE es obligatorio}"
python_command="${PYTHON_COMMAND:-python3}"
sidecar="${EMOVEST_SIDECAR_PATH:-$repository_root/frontend/src-tauri/binaries/emovest-backend-$target_triple}"
test_root="${EMOVEST_TEST_ROOT:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/EmoVest sidecar ñ con espacios}"
token="ci-sidecar-smoke-token-$(printf '0%.0s' {1..48})"

if [[ ! -x "$sidecar" ]]; then
  echo "No existe el sidecar macOS ejecutable esperado: $sidecar" >&2
  exit 1
fi

expected_schema_revision="$(cd "$repository_root/backend" && "$python_command" -c 'from migration_manager import get_head_revision; print(get_head_revision())')"
if [[ -z "$expected_schema_revision" ]]; then
  echo 'No se pudo resolver la revisión Alembic esperada.' >&2
  exit 1
fi

cleanup() {
  if [[ -n "${sidecar_pid:-}" ]] && kill -0 "$sidecar_pid" 2>/dev/null; then
    kill "$sidecar_pid" 2>/dev/null || true
    wait "$sidecar_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

mkdir -p "$test_root"
log_file="$test_root/sidecar.log"
APP_MODE=desktop \
EMOVEST_DESKTOP_TOKEN="$token" \
EMOVEST_DESKTOP_HOST=127.0.0.1 \
EMOVEST_DESKTOP_PORT=0 \
EMOVEST_DATA_DIR="$test_root/datos" \
EMOVEST_CONFIG_DIR="$test_root/configuración" \
EMOVEST_LOG_DIR="$test_root/registros" \
EMOVEST_BACKUP_DIR="$test_root/copias" \
EMOVEST_DATABASE_PATH="$test_root/datos/emovest.sqlite3" \
IMAGE_STORAGE_DIR="$test_root/datos/imágenes" \
EMOVEST_MODEL_DIR="$test_root/datos/modelos" \
SECRET_KEY='' \
"$sidecar" >"$log_file" 2>&1 &
sidecar_pid=$!

ready_line=''
for _ in $(seq 1 45); do
  if ready_line="$(grep -m1 '^EMOVEST_READY ' "$log_file" 2>/dev/null || true)"; then
    [[ -n "$ready_line" ]] && break
  fi
  if grep -q '^EMOVEST_ERROR ' "$log_file" 2>/dev/null; then
    cat "$log_file" >&2
    exit 1
  fi
  if ! kill -0 "$sidecar_pid" 2>/dev/null; then
    cat "$log_file" >&2
    exit 1
  fi
  sleep 1
done

if [[ -z "$ready_line" ]]; then
  cat "$log_file" >&2
  echo 'El sidecar no quedó listo dentro del plazo.' >&2
  exit 1
fi

port="$(printf '%s' "$ready_line" | sed -E 's/^EMOVEST_READY .*"port"[[:space:]]*:[[:space:]]*([0-9]+).*$/\1/')"
if [[ ! "$port" =~ ^[0-9]+$ ]]; then
  echo "No se pudo obtener el puerto de readiness: $ready_line" >&2
  exit 1
fi

base_url="http://127.0.0.1:$port"
if curl --silent --show-error --fail "$base_url/health/ready" >/dev/null 2>&1; then
  echo 'La API aceptó una petición sin token.' >&2
  exit 1
fi

health="$(curl --silent --show-error --fail -H "X-Emovest-Desktop-Token: $token" "$base_url/health/ready")"
health_ready="$(printf '%s' "$health" | "$python_command" -c 'import json, sys; payload=json.load(sys.stdin); print(payload.get("ready") is True)')"
health_schema="$(printf '%s' "$health" | "$python_command" -c 'import json, sys; print(json.load(sys.stdin).get("schema_revision", ""))')"
if [[ "$health_ready" != 'True' || "$health_schema" != "$expected_schema_revision" ]]; then
  echo "El health autenticado no confirmó el esquema esperado: $health" >&2
  exit 1
fi

curl --silent --show-error --fail -X POST -H "X-Emovest-Desktop-Token: $token" \
  -H 'Content-Type: application/json' -d '{}' "$base_url/desktop/shutdown" >/dev/null

for _ in $(seq 1 15); do
  if ! kill -0 "$sidecar_pid" 2>/dev/null; then
    wait "$sidecar_pid"
    sidecar_pid=''
    echo 'Sidecar macOS validado: READY, token, SQLite y shutdown.'
    exit 0
  fi
  sleep 1
done

echo 'El sidecar no terminó dentro del plazo de apagado.' >&2
exit 1
