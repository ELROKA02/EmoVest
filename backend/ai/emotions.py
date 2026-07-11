from decimal import Decimal

from pydantic import BaseModel, Field


class Emociones(BaseModel):
    confianza: Decimal = Field(ge=0, le=100)
    duda: Decimal = Field(ge=0, le=100)
    euforia: Decimal = Field(ge=0, le=100)
    miedo: Decimal = Field(ge=0, le=100)
    neutral: Decimal = Field(ge=0, le=100)


def construir_prompt_emociones(texto: str) -> str:
    return f"""
Clasifica el siguiente texto en estas 5 emociones: confianza, duda, euforia, miedo y neutral.

Devuelve solo un JSON valido con estas 5 claves.
Cada valor debe ser un porcentaje entre 0 y 100 con maximo 2 decimales.
La suma total de los 5 porcentajes debe ser exactamente 100.

Texto: {texto}
""".strip()
