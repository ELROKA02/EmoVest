# Contrato del sidecar de EmoVest

Tauri no incluye el ejecutable Python en Git. Antes de `tauri dev` o `tauri build`,
`pnpm desktop:prepare-sidecar` copia el ejecutable indicado por
`EMOVEST_SIDECAR_SOURCE` al nombre con target triple que exige Tauri.

Para Windows x64, el destino es:

`src-tauri/binaries/emovest-backend-x86_64-pc-windows-msvc.exe`

El proceso recibe estas variables:

- `APP_MODE=desktop`
- `EMOVEST_APP_VERSION` (versión del paquete Tauri)
- `EMOVEST_DESKTOP_TOKEN`
- `EMOVEST_DESKTOP_HOST=127.0.0.1`
- `EMOVEST_DESKTOP_PORT=0`
- `EMOVEST_DESKTOP_PARENT_PID`
- `EMOVEST_DESKTOP_CANCEL_FILE`
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

`EMOVEST_DESKTOP_CANCEL_FILE` es una señal interna única por lanzamiento. El
backend la vigila junto al PID padre para poder terminar incluso si el proceso
secundario de PyInstaller queda fuera del Job Object durante una carrera de
arranque. No es una variable que deba configurar el usuario.

Cuando la API ya escucha debe escribir una única línea:

`EMOVEST_READY {"port":49152}`

La API debe exigir el header `X-Emovest-Desktop-Token`, incluido en
`/health/ready`, `/desktop/update/prepare` y `/desktop/shutdown`. No debe escribir
el token en logs, errores ni archivos.

El updater solo se habilita con la feature Cargo `desktop-updater` y un overlay
de release que contenga un objeto `plugins.updater` completo. Los builds normales
no registran el plugin. En producción la interfaz invoca comandos Rust propios:
no tiene permiso directo para instalar y no puede saltarse
`/desktop/update/prepare`, el backup ni el cierre supervisado del sidecar.
