# AGENTS.md

Guía breve para que agentes de código sean productivos en EmoVest desde el primer turno.

## Alcance del proyecto

- Aplicación de escritorio Windows:
- `backend/`: sidecar FastAPI + SQLAlchemy + SQLite + cola local persistente + Ollama opcional.
- `frontend/`: React/Vite dentro de Tauri 2.
- Fuente de verdad: `docs/escritorio-windows.md`.
- Los archivos Docker/MySQL/Redis históricos son legado no soportado y no forman parte del producto.

## Comandos de trabajo (desarrollo)

Ejecuta los comandos en la carpeta correcta:

- Frontend (`frontend/`):
- `pnpm install`
- `pnpm dev`
- `pnpm build`
- `pnpm lint`
- `pnpm desktop:dev`
- `pnpm desktop:build`

- Backend (`backend/`):
- `python -m venv venv`
- `venv\Scripts\activate` (Windows) o `source venv/bin/activate` (Linux/macOS)
- `pip install -r requirements.txt`
- `python create_tables.py`
- `uvicorn app:app --reload`

- Sidecar Windows (raíz, PowerShell):
- `.\scripts\build-windows-sidecar.ps1`

## Arquitectura y limites

- No mezclar responsabilidades:
- Endpoints y orquestacion HTTP en `backend/routers/`.
- Modelo de datos y ORM en `backend/models.py`.
- Cola en `backend/queueing/` y jobs en `backend/jobs/`.
- Clasificacion emocional con Ollama en `backend/routers/ia.py`.
- Ciclo de vida del sidecar en `frontend/src-tauri/src/lib.rs`.

- Flujo de operaciones con notas:
- Crear operacion en `backend/routers/operaciones.py`.
- Guardar operación y job en la misma transacción SQLite.
- Procesar el job con el runner local persistente.
- Guardar `Registro_emocional` en SQLite; un fallo de IA nunca revierte la operación.

## Convenciones para agentes

- Haz cambios pequenos y enfocados; evita refactors amplios no pedidos.
- Si tocas endpoints de operaciones o IA, valida impacto en la cola local (no solo en el request HTTP).
- Si agregas configuracion nueva, centralizala en `backend/config.py` y documenta variable de entorno.
- En frontend, usa scripts de `frontend/package.json`; no introduzcas tooling alternativo sin peticion.
- No reactives el modo servidor ni dependencias MySQL/Redis/RQ salvo una decisión explícita del propietario.
- No guardes binarios de sidecar, certificados, claves privadas ni modelos en Git.
- Una release pública se dispara con un tag `desktop-vX.Y.Z` sobre un commit ya
  integrado en `main`; un push ordinario a `main` solo valida y genera artefactos
  de CI. Sigue `docs/escritorio-windows.md` antes de crear o publicar el tag.
- Para repartir trabajo o hablar con el equipo de EmoVest, usa Discord como canal de coordinacion.

## Equipo y reparto por Discord

- `enriquegr10`: frontend.
- `Alex~`: backend.
- `Elroka02`: Samuel, backend.
- `Rei☆★`: Annabel, frontend.
- Evita asignar trabajo a bots de Discord salvo peticion explicita.

## Pitfalls importantes

- El análisis emocional es asíncrono: una respuesta `201` no implica que el registro emocional ya exista.
- La cola usa leases e idempotencia; valida recuperación tras cierre y reinicio.
- Ollama es opcional. Ausencia del servicio o del modelo no debe impedir guardar operaciones.
- SQLite, imágenes, logs y backups deben permanecer fuera de la carpeta de instalación.
- Tauri debe fijar rutas absolutas, usar loopback y proteger la API con el token efímero.

## Fuente de verdad (enlazar, no duplicar)

- Escritorio, instalador, updater, datos y soporte: [docs/escritorio-windows.md](docs/escritorio-windows.md)
- `docs/despliegue.md` y `docs/redis-workers.md` solo describen el sistema legado.

## Checklist rapido al terminar cambios

- Backend: tests pasan (`python -m unittest discover -s tests -v`).
- Frontend: build/lint pasan (`pnpm build`, `pnpm lint`).
- Rust: `cargo check --locked` en `frontend/src-tauri/`.
- Si tocaste flujo emocional: cola local, reintentos y recuperación verificados.
- Si tocaste empaquetado: ejecutar CI Windows y no afirmar que NSIS funciona sin esa validación.
