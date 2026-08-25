# Edición de escritorio para macOS

EmoVest para macOS usa la misma arquitectura local que la edición Windows:
Tauri inicia un sidecar FastAPI empaquetado con PyInstaller, que mantiene los
datos, SQLite, logs y copias de seguridad fuera de la carpeta instalada. La API
queda limitada a loopback y exige el token efímero generado por Tauri.

Se construyen instaladores nativos separados para las dos arquitecturas de Mac:

| Equipo | Target Rust/Tauri | Instalador CI |
| --- | --- | --- |
| Apple Silicon (M1 o posterior) | `aarch64-apple-darwin` | `EmoVest-macOS-arm64.dmg` |
| Intel | `x86_64-apple-darwin` | `EmoVest-macOS-x64.dmg` |

Cada `.dmg` contiene `EmoVest.app` y el sidecar correspondiente a su misma
arquitectura. No hay traducción Rosetta como requisito para ninguna de las dos
distribuciones.

## Desarrollo local

Requisitos:

- macOS con Xcode o las Command Line Tools activas;
- Python 3.12;
- Node.js 22 y pnpm 11;
- Rust estable para la arquitectura del equipo.

Instalación y arranque en Apple Silicon:

```bash
cd backend
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt

cd ..
PYTHON_COMMAND="$PWD/backend/venv/bin/python" ./scripts/build-macos-sidecar.sh

cd frontend
pnpm install --frozen-lockfile
pnpm desktop:dev
```

Para Intel se usan los mismos comandos. El script detecta la arquitectura local
o acepta `TAURI_TARGET_TRIPLE=x86_64-apple-darwin` si se necesita declararla de
forma explícita.

## Generar un instalador `.dmg`

```bash
cd /ruta/a/EmoVest
PYTHON_COMMAND="$PWD/backend/venv/bin/python" ./scripts/build-macos-sidecar.sh

cd frontend
pnpm desktop:build:mac
```

Tauri deja los resultados bajo `frontend/src-tauri/target/.../release/bundle/`:

- `macos/EmoVest.app`
- `dmg/EmoVest_<versión>_<arquitectura>.dmg`

## Automatización de CI

El workflow [desktop-macos.yml](../.github/workflows/desktop-macos.yml) se
ejecuta en pull requests y pushes a `develop` y `main`, además de poder iniciarse
manualmente. Genera una matriz con un runner Apple Silicon y otro Intel. En cada
uno:

1. instala las dependencias bloqueadas;
2. ejecuta pruebas del backend y lint/build del frontend;
3. empaqueta y prueba el sidecar real (readiness, token, SQLite y shutdown);
4. ejecuta formato, `cargo check`, Clippy y tests Rust para el target nativo;
5. genera `EmoVest.app` y el `.dmg`;
6. verifica el disco, los binarios y la arquitectura del bundle;
7. publica el `.dmg` como artefacto temporal de Actions durante 14 días.

Estos artefactos son builds de CI sin firma de distribución. Son adecuados para
pruebas internas, pero no deben publicarse como release estable: Gatekeeper
puede advertir a la persona usuaria.

## Publicación para usuarios finales

Antes de una release pública se debe añadir firma `Developer ID Application` y
notarización de Apple al workflow. Apple exige ambos para distribuir un `.dmg`
fuera de la App Store. Las credenciales necesarias son propiedad del titular de
la cuenta Apple Developer y deben guardarse como secretos protegidos de GitHub;
nunca se versionan ni se incluyen en artefactos de CI.

Hasta que esas credenciales existan, el flujo automatiza builds verificables de
desarrollo, pero no una distribución pública notarizada.

Una vez configuradas, el workflow
[desktop-macos-release.yml](../.github/workflows/desktop-macos-release.yml) se
activa al publicar una release estable `desktop-vX.Y.Z` —o manualmente para un
tag existente—, construye los dos targets, firma, notariza y adjunta los dos
`.dmg` a esa release. No modifica `latest.json`, de modo que el updater Windows
permanece aislado y no corre riesgo.

Los secretos obligatorios del entorno protegido `desktop-production` son:
`APPLE_CERTIFICATE` (P12 Developer ID Application en base64),
`APPLE_CERTIFICATE_PASSWORD`, `APPLE_API_ISSUER`, `APPLE_API_KEY` (Key ID) y
`APPLE_API_KEY_BASE64` (la API key `.p8` de App Store Connect en base64). El
workflow falla de forma explícita si falta alguno; nunca publica un instalador
macOS sin firma ni notarización.

Referencias: [DMG de Tauri](https://v2.tauri.app/distribute/dmg/) y [firma y
notarización de macOS en Tauri](https://v2.tauri.app/distribute/sign/macos/).
