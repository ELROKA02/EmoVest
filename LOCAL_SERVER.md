# Entorno local tipo servidor

Este entorno reproduce el VPS real de EmoVest de forma practica: Caddy sirve el frontend compilado, proxya `/api/*` al backend FastAPI, y Docker levanta MySQL, Redis y el worker RQ. Ollama no se instala en Docker; se usa el servicio local de tu maquina en `localhost:11434`.

## Arranque

Antes de ejecutar Compose, asegurate de que Docker Desktop o el daemon de Docker esta arrancado.

```bash
cp .env.local-server.example .env.local-server
docker compose --env-file .env.local-server -f docker-compose.local-server.yml up --build
```

Abre:

- Frontend: http://localhost:8080
- API via Caddy: http://localhost:8080/api/

## Comprobaciones rapidas

```bash
curl http://localhost:8080/api/
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
