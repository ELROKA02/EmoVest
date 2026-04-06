from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth

app = FastAPI(
    title="EMOVEST API",
    summary="Servicios base de autenticacion y acceso para la plataforma EMOVEST.",
    description=(
        "API backend de EMOVEST para la gestion de acceso a la plataforma de analisis "
        "conductual y estadistico aplicada al trading. La especificacion OpenAPI se "
        "define directamente en FastAPI para que Swagger UI refleje con precision los "
        "endpoints disponibles y sus respuestas."
    ),
    version="0.1.1",
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
            "name": "operaciones",
            "description": "Registro y consulta de operaciones financieras realizadas por el usuario."
        },
        {
            "name": "emociones",
            "description": "Registro y analisis del contexto emocional vinculado a las operaciones."
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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)

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