from fastapi import FastAPI
from routers import auth

app = FastAPI(
    title="API de Emovest",
    description="La maravillosa API de una plataforma que mejora el control de las inversiones para los inverosres",
    version="0.0.1"
)

# Routers
app.include_router(auth.router)

@app.get("/")
def root():
    return {"mensaje": "API funcionando"}