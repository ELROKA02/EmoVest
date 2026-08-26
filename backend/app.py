from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import APP_VERSION, CORS_ALLOWED_ORIGINS
from database import SessionLocal, engine
from desktop_security import DesktopApiSecurityMiddleware
from backup_manager import current_schema_revision
from migration_manager import get_head_revision
from queueing.lifecycle import get_background_services_health
from routers import auth, chat, desktop, exportaciones, ia, importaciones, operaciones, cuentaTrading, estadisticas


@asynccontextmanager
async def lifespan(application: FastAPI):
    from queueing.lifecycle import start_background_services, stop_background_services
    from routers.estadisticas import start_stats_scheduler, stop_stats_scheduler

    start_background_services()
    start_stats_scheduler()
    application.state.background_services_ready = True
    try:
        yield
    finally:
        application.state.background_services_ready = False
        # Libera primero los leases emocionales; si el cálculo mensual está
        # ocupado, Tauri aún conserva margen para aplicar su kill de seguridad.
        stop_background_services()
        stop_stats_scheduler()
        engine.dispose()

app = FastAPI(
    title="EMOVEST API",
    summary="Servicios base de autenticacion y acceso para la plataforma EMOVEST.",
    description=(
        "API backend de EMOVEST para la gestion de acceso a la plataforma de analisis "
        "conductual y estadistico aplicada al trading. La especificacion OpenAPI se "
        "define directamente en FastAPI para que Swagger UI refleje con precision los "
        "endpoints disponibles y sus respuestas."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
    contact={
        "name": "Equipo EMOVEST"
    },
    openapi_tags=[
        {
            "name": "usuarios",
            "description": "Operaciones relacionadas con registro, acceso e identidad de usuarios."
        },
        {
            "name": "cuentas",
            "description": "Gestion de cuentas de trading y configuraciones asociadas."
        },
        {
            "name": "configuracion",
            "description": "Consulta y gestion de la configuracion de la plataforma, incluidos proveedores y modelos de IA."
        },
        {
            "name": "operaciones",
            "description": "Registro y consulta de operaciones financieras realizadas por el usuario."
        },
        {
            "name": "importaciones",
            "description": "Previsualización y confirmación idempotente de historiales de proveedores de trading."
        },
        {
            "name": "emociones",
            "description": "Registro y analisis del contexto emocional vinculado a las operaciones."
        },
        {
            "name": "chat_ia",
            "description": "Endpoints de conversacion y pruebas del asistente de IA."
        },
        {
            "name": "estadisticas",
            "description": "Metricas agregadas y resultados estadisticos derivados de la actividad."
        },
        {
            "name": "otros",
            "description": "Endpoints auxiliares que no pertenecen a una categoria funcional principal."
        },
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(DesktopApiSecurityMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(exportaciones.router)
app.include_router(importaciones.router)
app.include_router(operaciones.router)
app.include_router(cuentaTrading.router)
app.include_router(estadisticas.router)
app.include_router(ia.router)
app.include_router(chat.router)
app.include_router(desktop.router)


@app.get(
    "/health/ready",
    tags=["desktop"],
    summary="Comprobar que la edición de escritorio está preparada",
)
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos local no está preparada.",
        ) from error

    revision = current_schema_revision()
    if revision is None or revision != get_head_revision():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El esquema local no coincide con esta versión.",
        )
    if not getattr(app.state, "background_services_ready", False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Los servicios locales todavía no están preparados.",
        )
    if not get_background_services_health()["healthy"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La cola local no está disponible.",
        )

    return {
        "ready": True,
        "version": app.version,
        "schema_revision": revision,
    }

@app.get(
    "/",
    tags=["otros"],
    summary="Verificar disponibilidad de la API",
    description="Comprueba que el servicio backend esta levantado y puede responder peticiones.",
    responses={
        200: {
            "description": "La API esta disponible.",
            "content": {
                "application/json": {
                    "example": {
                        "mensaje": "API funcionando"
                    }
                }
            }
        }
    }
)
def root():
    return {"mensaje": "API funcionando"}
