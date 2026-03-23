from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth

app = FastAPI(
    title="API de Emovest",
    description="La maravillosa API de una plataforma que mejora el control de las inversiones para los inverosres",
    version="0.0.1"
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

@app.get("/")
def root():
    return {"mensaje": "API funcionando"}