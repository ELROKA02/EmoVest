from fastapi import FastAPI
from database import engine
from models import Base

app = FastAPI()

#CREA LAS TABLAS EN MYSQL
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"mensaje": "API funcionando"}