#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_triple="${TAURI_TARGET_TRIPLE:?TAURI_TARGET_TRIPLE es obligatorio}"
architecture="${EMOVEST_MACOS_ARCHITECTURE:?EMOVEST_MACOS_ARCHITECTURE es obligatorio}"
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

echo "Bundle macOS validado: $dmg"
