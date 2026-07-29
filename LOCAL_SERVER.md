# Entorno Docker legado

> **No soportado:** EmoVest se distribuye ahora como aplicación de escritorio
> para Windows. Este documento y los archivos Docker se conservan únicamente
> como referencia histórica. Consulta
> [docs/escritorio-windows.md](docs/escritorio-windows.md).

Este entorno permite ejecutar EmoVest localmente: Docker levanta el frontend compilado, la API FastAPI, MySQL, Redis y el worker RQ. No requiere proxy inverso ni servidor. Ollama no se instala en Docker; se usa el servicio local de tu maquina en `localhost:11434`.

## Arranque

Antes de ejecutar Compose, asegurate de que Docker Desktop o el daemon de Docker esta arrancado.

```bash
cp .env.local-server.example .env.local-server
docker compose --env-file .env.local-server -f docker-compose.local-server.yml up --build
```

Si ya tenias un `.env.local-server` de una version anterior, actualiza `VITE_API_URL` a `http://localhost:8000`, `FRONTEND_URL` a `http://localhost:5173` y `WEB_PORT` a `5173`.

Abre:

- Frontend: http://localhost:5173
- API: http://localhost:8000/
- Documentación API: http://localhost:8000/docs

## Comprobaciones rapidas

```bash
curl http://localhost:8000/
docker compose --env-file .env.local-server -f docker-compose.local-server.yml ps
docker compose --env-file .env.local-server -f docker-compose.local-server.yml logs -f api worker
```

La base de datos se crea limpia en el volumen `mysql-data` y el servicio `api` ejecuta `python create_tables.py` antes de arrancar uvicorn.

## Ollama

Para validar el analisis emocional real, Ollama debe responder en tu maquina host:

```bash
curl http://localhost:11434/api/tags
```

El backend dentro de Docker lo alcanza mediante `OLLAMA_HOST=http://host.docker.internal:11434`. Si Ollama o el modelo no estan disponibles, la aplicacion no deberia romperse; el worker guardara valores emocionales en cero segun el comportamiento esperado.

## Resetear datos locales

```bash
docker compose --env-file .env.local-server -f docker-compose.local-server.yml down -v
```

Esto borra MySQL local y las imagenes subidas en este entorno.
