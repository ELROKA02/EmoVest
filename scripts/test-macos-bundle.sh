#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_triple="${TAURI_TARGET_TRIPLE:?TAURI_TARGET_TRIPLE es obligatorio}"
architecture="${EMOVEST_MACOS_ARCHITECTURE:?EMOVEST_MACOS_ARCHITECTURE es obligatorio}"
python_command="${PYTHON_COMMAND:-python3}"
bundle_root="$repository_root/frontend/src-tauri/target/$target_triple/release/bundle"
dmg="$(find "$bundle_root/dmg" -maxdepth 1 -type f -name '*.dmg' -print -quit)"
app="$(find "$bundle_root/macos" -maxdepth 1 -type d -name 'EmoVest.app' -print -quit)"

if [[ -z "$dmg" || -z "$app" ]]; then
  echo 'Tauri no generó el .dmg y .app esperados.' >&2
  exit 1
fi

hdiutil verify "$dmg"
main_executable="$app/Contents/MacOS/emovest-desktop"
sidecar="$app/Contents/MacOS/emovest-backend"
if [[ ! -x "$main_executable" || ! -x "$sidecar" ]]; then
  echo 'El bundle no contiene los ejecutables macOS esperados.' >&2
  exit 1
fi

for executable in "$main_executable" "$sidecar"; do
  if ! lipo -archs "$executable" | tr ' ' '\n' | grep -qx "$architecture"; then
    echo "El bundle no contiene la arquitectura $architecture: $executable" >&2
    exit 1
  fi
done

mount_root="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
mkdir -p "$mount_root"
mount_dir="$(mktemp -d "$mount_root/emovest-dmg.XXXXXX")"
mounted=false

cleanup() {
  if [[ "$mounted" == true ]]; then
    hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
  fi
  rmdir "$mount_dir" >/dev/null 2>&1 || true
}
trap cleanup EXIT

hdiutil attach -nobrowse -readonly -mountpoint "$mount_dir" "$dmg" >/dev/null
mounted=true

mounted_app="$mount_dir/EmoVest.app"
mounted_main="$mounted_app/Contents/MacOS/emovest-desktop"
mounted_sidecar="$mounted_app/Contents/MacOS/emovest-backend"
if [[ ! -x "$mounted_main" || ! -x "$mounted_sidecar" ]]; then
  echo 'El instalador montado no contiene los ejecutables esperados.' >&2
  exit 1
fi

for executable in "$mounted_main" "$mounted_sidecar"; do
  if ! lipo -archs "$executable" | tr ' ' '\n' | grep -qx "$architecture"; then
    echo "El instalador montado no contiene la arquitectura $architecture: $executable" >&2
    exit 1
  fi
done

EMOVEST_SIDECAR_PATH="$mounted_sidecar" \
EMOVEST_TEST_ROOT="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/EmoVest mounted dmg ñ" \
PYTHON_COMMAND="$python_command" \
"$repository_root/scripts/test-macos-sidecar.sh"

echo "Bundle macOS validado: $dmg"
