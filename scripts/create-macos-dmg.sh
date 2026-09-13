#!/usr/bin/env bash

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_triple="${TAURI_TARGET_TRIPLE:?TAURI_TARGET_TRIPLE es obligatorio}"
version="${EMOVEST_DMG_VERSION:-}"

case "$target_triple" in
  aarch64-apple-darwin)
    architecture="aarch64"
    ;;
  x86_64-apple-darwin)
    architecture="x64"
    ;;
  *)
    echo "Target macOS no compatible: $target_triple" >&2
    exit 1
    ;;
esac

if [[ -z "$version" ]]; then
  version="$(sed -nE 's/^version = "([^"]+)"$/\1/p' "$repository_root/frontend/src-tauri/Cargo.toml" | head -n 1)"
fi

if [[ -z "$version" ]]; then
  echo 'No se pudo resolver la versión para el instalador macOS.' >&2
  exit 1
fi

bundle_root="$repository_root/frontend/src-tauri/target/$target_triple/release/bundle"
app="$bundle_root/macos/EmoVest.app"
dmg_directory="$bundle_root/dmg"
dmg="$dmg_directory/EmoVest_${version}_${architecture}.dmg"

if [[ ! -d "$app" ]]; then
  echo "No existe el bundle macOS esperado: $app" >&2
  exit 1
fi

mkdir -p "$dmg_directory"
rm -f "$dmg"

# Tauri deja una firma ad-hoc parcial cuando se construye sin identidad Apple.
# Antes de distribuir, se vuelve a firmar por completo para que Gatekeeper no
# interprete el bundle como dañado. No sustituye la firma/notarización de Apple:
# sigue siendo un instalador sin firmar de distribución.
codesign --force --deep --sign - "$app"
codesign --verify --deep --strict --verbose=2 "$app"

# Evita el script create-dmg interno de Tauri: en macos-15-intel puede fallar al
# montar la imagen temporal aunque la .app se haya construido correctamente. El
# staging añade el acceso estándar a Aplicaciones para que Finder permita arrastrar
# EmoVest.app a /Applications.
staging_directory="$(mktemp -d "${TMPDIR:-/tmp}/emovest-dmg.XXXXXX")"
cleanup() {
  rm -rf "$staging_directory"
}
trap cleanup EXIT

ditto "$app" "$staging_directory/EmoVest.app"
ln -s /Applications "$staging_directory/Applications"
hdiutil create -volname 'EmoVest' -srcfolder "$staging_directory" -format UDZO -ov "$dmg"
hdiutil verify "$dmg"

echo "DMG macOS creado: $dmg"
