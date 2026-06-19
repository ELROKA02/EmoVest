![Banner de EmoVest](docs/Emovest.png)

# EmoVest

![version](https://img.shields.io/badge/version-0.3.1-blue)
![license](https://img.shields.io/badge/license-MIT-green)

EmoVest es un diario de trading open source y gratuito para ejecutar en tu propio entorno. Registra operaciones, notas y capturas; cruza tus resultados con contexto emocional; y usa un modelo local con Ollama para detectar patrones en tus decisiones.

EMOVEST no proporciona asesoramiento financiero. Es una herramienta de analisis conductual y estadistico.

## Que hace

- Gestiona usuarios locales con email y contrasena.
- Permite crear varias cuentas de trading por usuario.
- Registra operaciones LONG/SHORT con precios, cantidad, resultado, stop loss, take profit, confianza, notas y captura opcional.
- Calcula metricas mensuales como beneficio neto, win rate, drawdown, rachas y rendimiento por dia.
- Encola el analisis emocional con Redis/RQ para que la app no dependa de una respuesta inmediata de Ollama.
- Guarda las capturas en filesystem local (`backend/images/` por defecto).

## Stack

| Capa | Tecnologia |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI + SQLAlchemy |
| Base de datos | MySQL |
| Cola | Redis + RQ |
| IA emocional | Ollama con modelo local |
| Auth | JWT |

## Instalacion rapida con Docker

Requisitos:

- Docker Desktop o Docker Engine
- Ollama corriendo en la maquina host si quieres analisis emocional real

```bash
cp .env.local-server.example .env.local-server
docker compose --env-file .env.local-server -f docker-compose.local-server.yml up --build
```

Abre:

- Frontend: http://localhost:8080
- API: http://localhost:8080/api/

Si Ollama no esta disponible, las operaciones se siguen guardando. El analisis emocional puede quedar pendiente o guardarse con valores de fallback segun el estado del worker.

## Desarrollo manual

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python create_tables.py
uvicorn app:app --reload
```

En Windows, activa el entorno con:

```bash
venv\Scripts\activate
```

### Worker RQ

En otra terminal:

```bash
cd backend
source venv/bin/activate
python worker.py
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Comandos utiles:

```bash
pnpm lint
pnpm build
```

## Variables de entorno

El backend usa `backend/.env.example` como plantilla. Las variables principales son:

- `DATABASE_URL`: conexion SQLAlchemy a MySQL.
- `SECRET_KEY`: clave secreta para firmar JWT.
- `REDIS_URL`: conexion a Redis.
- `RQ_QUEUE_NAME`: cola donde se encolan analisis emocionales.
- `FRONTEND_URL`: URL del frontend local.
- `CORS_ALLOWED_ORIGINS`: origenes permitidos separados por comas.
- `OLLAMA_HOST`: URL de Ollama.
- `IMAGE_STORAGE_DIR`: carpeta local para capturas.
- `MAX_IMAGE_SIZE_MB`: limite por captura.

EmoVest no envia correos transaccionales en la version open source inicial. El correo electronico se usa solo como identificador de cuenta.

## Documentacion

- Entorno Docker local: [LOCAL_SERVER.md](LOCAL_SERVER.md)
- Redis, workers y troubleshooting: [docs/redis-workers.md](docs/redis-workers.md)
- Despliegue avanzado en VPS: [docs/despliegue.md](docs/despliegue.md)
- Estado historico del VPS anterior: [docs/despliegue-vps.md](docs/despliegue-vps.md)

## Licencia

EmoVest se publica bajo licencia MIT. Consulta [LICENSE](LICENSE).
