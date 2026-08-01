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
instalación y los directorios de datos.

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

Al cerrar, Tauri solicita un apagado ordenado y termina el sidecar como
salvaguarda. La API solo escucha en `127.0.0.1` y exige el encabezado
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

Las copias automáticas previas a migraciones se limitan según
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

## Instalador y actualizaciones

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

El actualizador oficial de Tauri solo se compila en releases de producción. Al
arrancar, EmoVest consulta en segundo plano el `latest.json` de la última release
estable de GitHub. Si existe una versión posterior, el usuario puede descargarla
y elegir «Reiniciar y actualizar». Antes de iniciar NSIS, EmoVest:

1. comprueba la política de compatibilidad del esquema;
2. crea una copia SQLite `pre-update-*`;
3. cierra únicamente el sidecar perteneciente a esa instancia;
4. verifica la firma criptográfica del instalador;
5. deja que NSIS sustituya la aplicación y la vuelva a abrir.

Los builds de desarrollo registran comandos inertes y no registran el plugin.
Esto evita consultas de red y hace imposible una configuración efectiva
`"updater": null`. El endpoint, la clave pública y la generación de firmas solo
se añaden mediante el overlay validado del job de release. Las claves privadas y
los certificados nunca se guardan en el repositorio.

La firma Tauri protege los bytes del instalador. Además, la release firma un
payload canónico que une versión, firma del instalador y revisiones Alembic; el
binario verifica ese payload antes de confiar en la política de compatibilidad.
Por tanto, modificar solo `latest.json` no permite rebajar el esquema mínimo.

## Estrategia de ramas y entregas

`develop` es la rama de integración interna. Las funcionalidades se desarrollan
en ramas de trabajo, se validan mediante pull request hacia `develop` y se
integran allí cuando están listas para pruebas conjuntas. Cada push a `develop`
ejecuta las pruebas de Windows, construye el sidecar y genera un instalador de
desarrollo como artefacto temporal de GitHub Actions. Ese artefacto no es una
release pública y no actualiza instalaciones existentes.

`main` representa la versión estable y visible para los usuarios. Solo deben
integrarse en ella cambios consolidados desde `develop`. Los pushes y pull
requests hacia `main` vuelven a ejecutar toda la validación, pero no publican
automáticamente.

Una release pública se publica al subir un tag exacto `desktop-vX.Y.Z` sobre un
commit ya contenido en `main`. El workflow toma `X.Y.Z` como versión, valida las
credenciales de firma y publica la release estable. No se deben crear tags sobre
commits de trabajo ni antes de que el push a `main` haya terminado correctamente.
El mecanismo manual `workflow_dispatch` se conserva para contingencias y exige
`publish_release`, versión SemVer y la confirmación `PUBLICAR` desde `main`.

Para publicar una versión validada, un agente debe ejecutar desde un checkout
actualizado de `main`:

```bash
git tag desktop-vX.Y.Z
git push origin desktop-vX.Y.Z
```

El tag no puede reutilizarse y la versión debe ser mayor que la última release
estable. La primera versión que contiene el updater se instala manualmente con
`EmoVest-Setup.exe`; desde esa versión, las releases estables posteriores pueden
detectarse desde la propia aplicación.

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
SQLite y apagado, compila Tauri y sube el instalador como artefacto. Los pushes y
pull requests ordinarios nunca publican una release. Solo un push de tag con el
formato exacto `desktop-vX.Y.Z` inicia la publicación automática, después de
comprobar que su commit está contenido en `main`.

Como contingencia, la publicación manual requiere ejecutar `workflow_dispatch`,
activar `publish_release`, indicar una versión SemVer y escribir `PUBLICAR`. La
automatización usa el entorno protegido de GitHub `desktop-production` y falla
antes de compilar si falta la clave privada del updater:

- `TAURI_SIGNING_PRIVATE_KEY`: clave privada real del updater;
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: contraseña de la clave cifrada del
  updater.

La clave pública correspondiente está versionada en
`frontend/src-tauri/updater.pub`; es pública por diseño y actúa como ancla de
confianza inmutable para las instalaciones existentes.

La firma Authenticode es opcional para poder iniciar el canal de actualizaciones
antes de adquirir un certificado. Cuando exista, añade conjuntamente
`WINDOWS_CERTIFICATE` (PFX en base64), `WINDOWS_CERTIFICATE_PASSWORD` y la
variable `WINDOWS_TIMESTAMP_URL`. El certificado se importa solo en el runner
efímero y nunca se escribe en el repositorio. Sin esos tres valores la firma
Tauri sigue protegiendo criptográficamente cada actualización, pero Windows
puede mostrar SmartScreen con «editor desconocido».

El workflow publica únicamente versiones `MAJOR.MINOR.PATCH`. Construye con la
feature Cargo `desktop-updater`, firma el sidecar y el instalador con
Authenticode, genera la firma Tauri y publica juntos `EmoVest-Setup.exe`,
`EmoVest-Setup.exe.sig` y `latest.json`. Primero crea un borrador, comprueba que
estén exactamente esos tres artefactos y solo entonces lo convierte en la última
release estable.

La versión del tag debe ser posterior a la versión base de Tauri y a cualquier
release estable previa. El tag `desktop-vX.Y.Z` no puede reutilizarse.

La política mínima de datos vive en `backend/update-policy.json`; la revisión
objetivo se obtiene de la cabecera Alembic durante la release. Cambiar la
revisión mínima exige revisar desde qué versión instalada se permite actualizar.

### Preparar las credenciales una sola vez

En GitHub, crea el entorno `desktop-production`, permite la rama `main` para el
procedimiento manual y los tags `desktop-v*` para las publicaciones automáticas,
y añade un revisor obligatorio. Guarda en ese entorno los secretos descritos
arriba; no los pongas en `.env`, commits, artifacts ni logs.

La pareja de claves del updater se genera cifrada en el directorio local
ignorado `.secrets/`:

```powershell
cd frontend
pnpm tauri signer generate --write-keys ..\.secrets\updater\emovest-updater.key
```

La salida pública se copia una sola vez a `frontend/src-tauri/updater.pub`. El
contenido de `emovest-updater.key` se guarda como
`TAURI_SIGNING_PRIVATE_KEY` y su contraseña como
`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. La copia local cifrada puede vivir en
`.secrets/updater/`, que está ignorado por Git, pero nunca debe ser la única:
conserva además una copia cifrada y offline. Si se pierde la clave privada, las
instalaciones existentes no podrán verificar actualizaciones futuras.

`frontend/src-tauri/updater.pub` se considera inmutable desde la primera release
pública. No cambies a la vez la clave pública y la privada: los clientes ya
instalados conservan la clave anterior y rechazarían las siguientes
actualizaciones. Cualquier rotación futura necesita una versión puente y un
procedimiento específico antes de sustituir esta ancla de confianza.

La clave de Tauri no sustituye el certificado Authenticode. La primera protege
el canal de actualización; el segundo permite que Windows identifique al
publicador del `.exe`. Son credenciales distintas; la primera es obligatoria y
la segunda queda preparada para activarse cuando el propietario obtenga un
certificado válido.

En el equipo macOS donde se generó inicialmente, la contraseña está almacenada
en Keychain con el servicio `EmoVest Tauri updater signing key`. Si GitHub CLI
está instalado y autenticado, los secretos pueden configurarse sin imprimirlos:

```bash
gh secret set --env desktop-production TAURI_SIGNING_PRIVATE_KEY \
  < .secrets/updater/emovest-updater.key
security find-generic-password \
  -s "EmoVest Tauri updater signing key" -w \
  | gh secret set --env desktop-production TAURI_SIGNING_PRIVATE_KEY_PASSWORD
```

## Datos, backups y diagnóstico

En Windows, Tauri guarda SQLite, imágenes, backups y modelos bajo el directorio
local por usuario (`LocalAppData`), no bajo un perfil itinerante ni dentro de la
instalación. La configuración usa el directorio estándar de configuración. El
backend recibe rutas absolutas fijadas por Tauri; admite nombres con espacios y
Unicode y no hereda rutas de base de datos o secretos genéricos del entorno.

La sección «Aplicación de escritorio» muestra versión y diagnóstico sin exponer
tokens, notas ni respuestas de IA. Desde ahí se puede
crear un ZIP manual de soporte con la base SQLite, las imágenes y un manifiesto.
Los logs rotan y excluyen contraseñas, claves, notas privadas y payloads de IA.

Variables de configuración admitidas para desarrollo o soporte:

| Variable | Función | Valor por defecto |
| --- | --- | --- |
| `APP_MODE` | Modo de producto; solo acepta `desktop` | `desktop` |
| `EMOVEST_APP_VERSION` | Versión inyectada por Tauri al sidecar | `0.4.0` |
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
6. instalar manualmente una versión posterior y verificar que conserva los datos;
7. desinstalar, reinstalar y confirmar conservación de datos;
8. instalar WebView2 mediante el bootstrapper cuando no exista;
9. verificar la firma Authenticode del instalador;
10. instalar la primera versión con updater y actualizar a una segunda release
    firmada, validando backup, compatibilidad, interrupciones y datos.

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
- El updater solo está activo en releases con configuración y firmas reales.

## Documentación oficial de referencia

- [Sidecars de Tauri 2](https://v2.tauri.app/develop/sidecar/)
- [Instalador Windows y NSIS](https://v2.tauri.app/distribute/windows-installer/)
- [Updater de Tauri 2](https://v2.tauri.app/plugin/updater/)
- [Firma de código para Windows](https://v2.tauri.app/distribute/sign/windows/)
- [Empaquetado con PyInstaller](https://pyinstaller.org/en/stable/)
