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

El updater de Tauri está temporalmente desactivado: el binario no registra el
plugin, la interfaz no invoca comandos de actualización y CI no genera
`latest.json` ni firmas de updater. Las releases pueden seguir firmándose con
Authenticode y publicando `EmoVest-Setup.exe`. El endpoint interno
`/desktop/update/prepare` permanece reservado para una futura reactivación y no
se invoca en el hotfix.
