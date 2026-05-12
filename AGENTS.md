# AGENTS.md

Guia breve para que agentes de codigo sean productivos en EmoVest desde el primer turno.

## Alcance del proyecto

- Monorepo con 2 apps principales:
- `backend/`: API FastAPI + SQLAlchemy + MySQL + RQ/Redis + integracion con Ollama.
- `frontend/`: SPA React con Vite.
- Documentacion operativa: `docs/despliegue.md` y `docs/redis-workers.md`.

## Comandos de trabajo (desarrollo)

Ejecuta los comandos en la carpeta correcta:

- Frontend (`frontend/`):
- `npm install`
- `npm run dev`
- `npm run build`
- `npm run lint`

- Backend (`backend/`):
- `python -m venv venv`
- `venv\Scripts\activate` (Windows) o `source venv/bin/activate` (Linux/macOS)
- `pip install -r requirements.txt`
- `python create_tables.py`
- `uvicorn app:app --reload`

- Worker RQ (`backend/`, en otra terminal):
- `python worker.py`

## Arquitectura y limites

- No mezclar responsabilidades:
- Endpoints y orquestacion HTTP en `backend/routers/`.
- Modelo de datos y ORM en `backend/models.py`.
- Cola en `backend/rq_queue.py` y jobs en `backend/jobs/`.
- Clasificacion emocional con Ollama en `backend/routers/ia.py`.

- Flujo de operaciones con notas:
- Crear operacion en `backend/routers/operaciones.py`.
- Encolar job emocional en Redis.
- Procesar job en `backend/worker.py`.
- Guardar `Registro_emocional` en MySQL.

## Convenciones para agentes

- Haz cambios pequenos y enfocados; evita refactors amplios no pedidos.
- Si tocas endpoints de operaciones o IA, valida impacto en cola/worker (no solo en el request HTTP).
- Si agregas configuracion nueva, centralizala en `backend/config.py` y documenta variable de entorno.
- En frontend, usa scripts de `frontend/package.json`; no introduzcas tooling alternativo sin peticion.
- Antes de proponer despliegue o systemd/nginx, enlaza la documentacion oficial del repo en lugar de duplicarla.

## Pitfalls importantes

- El analisis emocional es asincrono (RQ): una respuesta `201` en operaciones no implica que el registro emocional ya exista.
- `backend/worker.py` usa `SimpleWorker` por compatibilidad local; evita cambiarlo sin revisar consecuencias en macOS/Linux.
- Si Redis o worker caen, la operacion puede guardarse sin analisis emocional. Esto es comportamiento esperado.

## Fuente de verdad (enlazar, no duplicar)

- Despliegue y servicios: [docs/despliegue.md](docs/despliegue.md)
- Cola Redis + workers + troubleshooting: [docs/redis-workers.md](docs/redis-workers.md)

## Checklist rapido al terminar cambios

- Backend: app levanta sin errores (`uvicorn app:app --reload`).
- Frontend: build/lint pasan (`npm run build`, `npm run lint`).
- Si tocaste flujo emocional: worker activo y procesamiento de cola verificado.