#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_root="$repository_root/backend"
binary_directory="$repository_root/frontend/src-tauri/binaries"
target_triple="${TAURI_TARGET_TRIPLE:-}"

if [[ -z "$target_triple" ]]; then
  case "$(uname -m)" in
    arm64) target_triple="aarch64-apple-darwin" ;;
    x86_64) target_triple="x86_64-apple-darwin" ;;
    *)
      echo "Arquitectura macOS no compatible: $(uname -m)" >&2
      exit 1
      ;;
  esac
fi

case "$target_triple" in
  aarch64-apple-darwin|x86_64-apple-darwin) ;;
  *)
    echo "TAURI_TARGET_TRIPLE debe ser un target macOS compatible, se recibió: $target_triple" >&2
    exit 1
    ;;
esac

python_command="${PYTHON_COMMAND:-python3}"
sidecar_target="$binary_directory/emovest-backend-$target_triple"
pyinstaller_cache_dir="${PYINSTALLER_CONFIG_DIR:-${TMPDIR:-/tmp}/emovest-pyinstaller}"

mkdir -p "$binary_directory"
mkdir -p "$pyinstaller_cache_dir"

pushd "$backend_root" >/dev/null
PYINSTALLER_CONFIG_DIR="$pyinstaller_cache_dir" \
  "$python_command" -m PyInstaller --clean --noconfirm emovest-backend.spec
popd >/dev/null

built_sidecar="$backend_root/dist/emovest-backend"
if [[ ! -f "$built_sidecar" ]]; then
  echo "PyInstaller no generó el sidecar esperado: $built_sidecar" >&2
  exit 1
fi

if [[ ! -x "$built_sidecar" ]]; then
  echo "El sidecar generado no es ejecutable: $built_sidecar" >&2
  exit 1
fi

if ! file "$built_sidecar" | grep -q 'Mach-O'; then
  echo "El sidecar generado no es un ejecutable Mach-O: $built_sidecar" >&2
  exit 1
fi

case "$target_triple" in
  aarch64-apple-darwin)
    expected_architecture='arm64'
    ;;
  x86_64-apple-darwin)
    expected_architecture='x86_64'
    ;;
esac

if ! lipo -archs "$built_sidecar" | tr ' ' '\n' | grep -qx "$expected_architecture"; then
  echo "El sidecar no contiene la arquitectura $expected_architecture requerida por $target_triple." >&2
  exit 1
fi

cp "$built_sidecar" "$sidecar_target"
chmod 755 "$sidecar_target"
echo "Sidecar macOS preparado en $sidecar_target"
