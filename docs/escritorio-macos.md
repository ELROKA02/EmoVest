# Edición de escritorio para macOS

EmoVest para macOS usa la misma arquitectura local que la edición Windows:
Tauri inicia un sidecar FastAPI empaquetado con PyInstaller, que mantiene los
datos, SQLite, logs y copias de seguridad fuera de la carpeta instalada. La API
queda limitada a loopback y exige el token efímero generado por Tauri.

La edición macOS incluye el mismo importador local de reportes HTML de
MetaTrader 5 que Windows. El flujo, los límites y la resolución de posiciones
hedging están documentados en [Importar un historial de MetaTrader
5](importar-metatrader.md).

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

Estos artefactos son builds sin firma de distribución. Gatekeeper puede
advertir a la persona usuaria; en ese caso deberá abrir la app desde el Finder
con Control-clic y elegir **Abrir**.

## Publicación para usuarios finales

El workflow
[desktop-macos-release.yml](../.github/workflows/desktop-macos-release.yml) se
activa al publicar una release estable `desktop-vX.Y.Z` —o manualmente para un
tag existente—, construye los dos targets y adjunta los dos `.dmg` a esa
release. No modifica `latest.json`, de modo que el updater Windows permanece
aislado y no corre riesgo.

Los instaladores se publican sin firma ni notarización de Apple, igual que los
artefactos de CI. Si más adelante se configura una cuenta Apple Developer, el
workflow puede ampliarse con firma `Developer ID Application` y notarización.

Referencia: [DMG de Tauri](https://v2.tauri.app/distribute/dmg/).
