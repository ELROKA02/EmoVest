# EmoVest para Windows

## Decisión de producto

Desde julio de 2026, EmoVest se distribuye como una aplicación de escritorio
local para Windows. La edición servidor basada en MySQL, Redis y RQ deja de ser
un producto soportado.

Los archivos Docker históricos se conservan como referencia y para evitar una
eliminación destructiva, pero no forman parte del build, las pruebas ni los
criterios de aceptación de la edición de escritorio.

El identificador estable de la aplicación es:

```text
io.github.elroka02.emovest
```

Cambiarlo después de distribuir una versión alteraría la identidad de la
instalación, los directorios de datos y el canal de actualización.

## Arquitectura

```text
Tauri 2 + React/Vite
        |
        | IPC: URL y token efímero
        v
FastAPI empaquetada con PyInstaller
        |
        +-- SQLite local
        +-- cola persistente SQLite
        +-- sesiones de chat SQLite
        +-- Ollama opcional
```

Tauri es el propietario del proceso FastAPI. Al arrancar:

1. Resuelve los directorios estándar de la aplicación.
2. Selecciona un puerto libre en loopback.
3. Genera un token aleatorio que no se persiste ni se escribe en logs.
4. Inicia el sidecar con la configuración necesaria.
5. Espera una señal de readiness autenticada.
6. Muestra la ventana principal únicamente cuando la API está preparada.

Al cerrar o actualizar, Tauri solicita un apagado ordenado y termina el sidecar
como salvaguarda. La API solo escucha en `127.0.0.1` y exige el encabezado
`X-EmoVest-Desktop-Token` en todas las solicitudes.

## Datos y directorios

Tauri entrega al sidecar rutas absolutas derivadas de los directorios estándar
de Windows. El backend no depende del directorio de instalación ni del
directorio de trabajo.

```text
data/
  emovest.sqlite3
  images/
  models/
config/
  jwt-secret
logs/
  emovest.log
backups/
  pre-migration-*.sqlite3
  manual-*.zip
```

Las rutas admiten espacios y caracteres Unicode. El instalador y el
desinstalador no deben eliminar estos datos por defecto.

## Esquema y migraciones

Alembic es la fuente de verdad del esquema. En la primera ejecución crea la
base SQLite. Antes de actualizar una base existente:

1. se detienen consumidores locales;
2. se crea un backup consistente mediante la API de backup de SQLite;
3. se valida la copia;
4. se ejecutan las migraciones;
5. solo después se inicia la API y la cola.

Si una migración falla, el original y el backup se conservan y el frontend
muestra un error recuperable.

Las copias automáticas previas a migraciones y actualizaciones se limitan según
`SQLITE_BACKUP_RETENTION` (cinco por defecto). Las copias manuales del usuario
no se eliminan automáticamente.

## Cola local

El análisis emocional continúa siendo asíncrono. La operación y su trabajo
pendiente se guardan en la misma transacción SQLite.

Los trabajos tienen estados `pending`, `running`, `completed` y `failed`.
Utilizan una clave de idempotencia, leases con caducidad, reintentos acotados y
backoff. Un trabajo interrumpido se recupera en el siguiente arranque. La
ausencia o el fallo de Ollama nunca revierte la operación.

## IA opcional

Ollama no se instala ni se inicia silenciosamente. El diagnóstico diferencia:

- no instalado;
- servicio detenido;
- modelo ausente;
- disponible;
- desactivado o mal configurado.

La aplicación sigue funcionando sin IA. Una futura integración con
`llama.cpp` podrá reutilizar el contrato de proveedores sin cambiar el
almacenamiento ni la cola.

## Instalador y actualización

El bundle Windows usa NSIS en modo por usuario y genera un instalador que se
publica como `EmoVest-Setup.exe`. WebView2 usa el bootstrapper controlado de
Tauri; la instalación inicial puede necesitar conexión si el runtime no está
presente.

El usuario final no necesita Python, Rust, Node.js, Docker, MySQL ni Redis.
Esas herramientas solo intervienen en el entorno de compilación. El
desinstalador de Tauri elimina la aplicación, pero los datos se almacenan fuera
de la carpeta instalada y se conservan por defecto. El instalador ofrece en su
pantalla final crear el acceso directo del escritorio; el acceso del menú Inicio
se crea siempre. El borrado de datos en la desinstalación es una opción
explícita y desmarcada por defecto.

El updater oficial de Tauri:

- se desactiva en desarrollo cuando no hay configuración de release;
- comprueba actualizaciones sin bloquear el arranque;
- verifica obligatoriamente la firma del artefacto;
- crea un backup antes de instalar una versión con migraciones;
- permite descargar y aplicar la actualización con reinicio explícito.

La clave pública puede versionarse. La clave privada del updater, certificados
de firma Windows y sus contraseñas solo se proporcionan mediante secretos de
CI. Nunca se almacenan en este repositorio.

Cada `latest.json` declara también `schema_revision` y
`minimum_schema_revision`. Antes de instalar, EmoVest compara esos valores con
la base local y crea una copia de seguridad. Si el manifiesto no contiene
metadatos compatibles, la actualización se muestra pero no se puede descargar.

## Desarrollo

Requisitos de desarrollo:

- Windows 10/11 con WebView2;
- Python 3.12;
- Node.js 22 y pnpm 11;
- Rust estable con el target `x86_64-pc-windows-msvc`;
- herramientas de compilación de Microsoft Visual C++.

Preparación:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..\frontend
pnpm install
```

Para levantar la aplicación Tauri en desarrollo hay que preparar primero el
sidecar. El script usa PyInstaller y coloca el ejecutable con el nombre que
Tauri espera:

```powershell
cd ..
.\scripts\build-windows-sidecar.ps1

cd frontend
pnpm desktop:dev
```

Vite sigue disponible para trabajar únicamente en la interfaz:

```powershell
cd frontend
pnpm dev
```

El navegador no sustituye las comprobaciones de integración Tauri: no gestiona
el sidecar ni recibe su token efímero.

## Generar `EmoVest-Setup.exe`

Build local de desarrollo, sin firma:

```powershell
cd C:\ruta\al\repositorio
.\scripts\build-windows-sidecar.ps1

cd frontend
pnpm install --frozen-lockfile
pnpm desktop:build
```

Tauri deja el instalador original en:

```text
frontend/src-tauri/target/release/bundle/nsis/EmoVest_0.4.0_x64-setup.exe
```

El workflow de CI lo publica como artefacto con el nombre estable
`EmoVest-Setup.exe`.

## Validación

Comandos locales:

```powershell
cd backend
python -m unittest discover -s tests -v

cd ..\frontend
pnpm lint
pnpm build
```

El workflow `.github/workflows/desktop-windows.yml` repite esas comprobaciones
en Windows, crea y ejecuta el sidecar real `.exe`, valida `READY`, autenticación,
SQLite y apagado, compila Tauri y sube el instalador como artefacto. Los eventos
`push` y `pull_request` nunca publican una release.

La publicación requiere ejecutar manualmente `workflow_dispatch`, activar
`publish_release`, indicar una versión SemVer y escribir `PUBLICAR`. La
automatización falla antes de compilar si falta cualquiera de estos secretos:

- `TAURI_SIGNING_PRIVATE_KEY`: clave privada de firma del updater;
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: contraseña, si la clave la usa;
- `EMOVEST_UPDATER_PUBLIC_KEY`: clave pública correspondiente;
- `WINDOWS_CERTIFICATE`: certificado Authenticode PFX codificado en base64;
- `WINDOWS_CERTIFICATE_PASSWORD`: contraseña del PFX.

También requiere la variable de repositorio `WINDOWS_TIMESTAMP_URL`, que debe
apuntar al servicio de sellado de tiempo recomendado por la entidad que emitió
el certificado.

El certificado se importa solo en el runner efímero. No se escribe en el
repositorio. El propietario debe decidir la identidad legal y adquirir el
certificado; EmoVest no inventa publisher, dominio ni credenciales.

El workflow publica únicamente el canal estable
`MAJOR.MINOR.PATCH`. El binario recibe el endpoint mediante
`EMOVEST_UPDATER_ENDPOINT`, de modo que un futuro canal beta puede usar otro
manifiesto y otras reglas de versión sin mezclar artefactos estables.

## Datos, backups y diagnóstico

En Windows, Tauri guarda SQLite, imágenes, backups y modelos bajo el directorio
local por usuario (`LocalAppData`), no bajo un perfil itinerante ni dentro de la
instalación. La configuración usa el directorio estándar de configuración. El
backend recibe rutas absolutas fijadas por Tauri; admite nombres con espacios y
Unicode y no hereda rutas de base de datos o secretos genéricos del entorno.

La sección «Aplicación de escritorio» muestra versión, actualización y
diagnóstico sin exponer tokens, notas ni respuestas de IA. Desde ahí se puede
crear un ZIP manual de soporte con la base SQLite, las imágenes y un manifiesto.
Los logs rotan y excluyen contraseñas, claves, notas privadas y payloads de IA.

Variables de configuración admitidas para desarrollo o soporte:

| Variable | Función | Valor por defecto |
| --- | --- | --- |
| `APP_MODE` | Modo de producto; solo acepta `desktop` | `desktop` |
| `EMOVEST_DATA_DIR` | Datos persistentes | Directorio estándar por usuario |
| `EMOVEST_CONFIG_DIR` | Configuración y secreto local | Directorio estándar por usuario |
| `EMOVEST_LOG_DIR` | Logs rotados | `<data>/logs` |
| `EMOVEST_DATABASE_PATH` | Archivo SQLite | `<data>/emovest.sqlite3` |
| `IMAGE_STORAGE_DIR` | Capturas | `<data>/images` |
| `EMOVEST_MODEL_DIR` | Reserva para modelos futuros | `<data>/models` |
| `EMOVEST_BACKUP_DIR` | Copias de seguridad | `<data>/backups` |
| `AI_EMOTION_ENABLED` | Activa clasificación emocional opcional | `true` |
| `AI_CHAT_ENABLED` | Activa chat con IA opcional | `true` |
| `AI_EMOTION_MODEL` | Modelo de clasificación | Modelo documentado en `.env.example` |
| `AI_CHAT_MODEL` | Modelo del chat | Modelo documentado en `.env.example` |

`EMOVEST_DESKTOP_TOKEN` es interno: Tauri lo genera en cada arranque y nunca
debe configurarse ni persistirse manualmente en una instalación.

## Comprobaciones manuales de aceptación en Windows

Antes de declarar una versión pública hay que validar en una máquina Windows
limpia:

1. instalar y arrancar sin Python, Docker, MySQL, Redis ni Ollama;
2. repetir inicio/cierre y comprobar que no quedan procesos;
3. operar con rutas de usuario que tengan espacios y caracteres no ASCII;
4. guardar y reiniciar con trabajos pendientes;
5. detener Ollama durante un trabajo y comprobar que la operación permanece;
6. actualizar desde una versión anterior y verificar backup y datos;
7. desinstalar, reinstalar y confirmar conservación de datos;
8. instalar WebView2 mediante el bootstrapper cuando no exista;
9. verificar Authenticode y la firma criptográfica del updater.

## Criterios de aceptación

- La instalación no requiere Python, Docker, MySQL ni Redis.
- Tauri inicia y detiene FastAPI sin procesos huérfanos.
- La API solo acepta conexiones loopback autenticadas.
- SQLite, imágenes, logs y backups viven fuera de la instalación.
- Operaciones, trabajos y sesiones sobreviven reinicios según su política.
- EmoVest funciona sin Ollama y explica su estado.
- Actualizar o reinstalar conserva los datos.
- CI Windows construye el sidecar, Tauri y el instalador NSIS.
- Los builds de desarrollo no necesitan secretos.
- Una release firmada falla claramente si faltan credenciales.

## Documentación oficial de referencia

- [Sidecars de Tauri 2](https://v2.tauri.app/develop/sidecar/)
- [Instalador Windows y NSIS](https://v2.tauri.app/distribute/windows-installer/)
- [Updater de Tauri 2](https://v2.tauri.app/plugin/updater/)
- [Firma de código para Windows](https://v2.tauri.app/distribute/sign/windows/)
- [Empaquetado con PyInstaller](https://pyinstaller.org/en/stable/)
