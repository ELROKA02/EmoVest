# Contrato del sidecar de EmoVest

Tauri no incluye el ejecutable Python en Git. Antes de `tauri dev` o `tauri build`,
`pnpm desktop:prepare-sidecar` copia el ejecutable indicado por
`EMOVEST_SIDECAR_SOURCE` al nombre con target triple que exige Tauri.

Para Windows x64, el destino es:

`src-tauri/binaries/emovest-backend-x86_64-pc-windows-msvc.exe`

El proceso recibe estas variables:

- `APP_MODE=desktop`
- `EMOVEST_DESKTOP_TOKEN`
- `EMOVEST_DESKTOP_HOST=127.0.0.1`
- `EMOVEST_DESKTOP_PORT=0`
- `EMOVEST_DESKTOP_PARENT_PID`
- `EMOVEST_DATA_DIR`
- `EMOVEST_CONFIG_DIR`
- `EMOVEST_LOG_DIR`
- `EMOVEST_BACKUP_DIR`
- `EMOVEST_DATABASE_PATH`
- `IMAGE_STORAGE_DIR`
- `EMOVEST_MODEL_DIR`

Tauri fija estas rutas en cada arranque y limpia `SECRET_KEY` del entorno
heredado para que el backend utilice exclusivamente el secreto persistente en
su directorio de configuración.

Cuando la API ya escucha debe escribir una única línea:

`EMOVEST_READY {"port":49152}`

La API debe exigir el header `X-Emovest-Desktop-Token`, incluido en
`/health/ready`, `/desktop/update/prepare` y `/desktop/shutdown`. No debe escribir
el token en logs, errores ni archivos.

Las releases se construyen exclusivamente desde el workflow de CI, que genera
una configuración Tauri temporal con `createUpdaterArtifacts: true`, el endpoint
HTTPS y la clave pública reales. El repositorio no contiene una configuración
de release utilizable con claves ficticias. El workflow requiere:

- `EMOVEST_UPDATER_PUBLIC_KEY`
- `EMOVEST_UPDATER_ENDPOINT` (HTTPS)
- `TAURI_SIGNING_PRIVATE_KEY`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`, si aplica

El `latest.json` debe incluir `schema_revision` y
`minimum_schema_revision`; si falta cualquiera, la interfaz permite detectar la
versión pero bloquea descarga e instalación.

La clave privada nunca se guarda en el repositorio.
