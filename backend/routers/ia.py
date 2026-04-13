from datetime import datetime
from decimal import Decimal

try:
    from ollama import chat
    _OLLAMA_INSTALLED = True
except ImportError:
    chat = None
    _OLLAMA_INSTALLED = False

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from models import Registro_emocional

import requests

def ollama_disponible() -> bool:
    try:
        r = requests.get("http://localhost:11434")
        return r.status_code == 200
    except:
        return False
    

class Emociones(BaseModel):
  confianza: Decimal = Field(ge=0, le=100)
  duda: Decimal = Field(ge=0, le=100)
  euforia: Decimal = Field(ge=0, le=100)
  miedo: Decimal = Field(ge=0, le=100)
  neutral: Decimal = Field(ge=0, le=100)


def construir_prompt_emociones(texto: str) -> str:
    return f'''
Clasifica el siguiente texto en estas 5 emociones: confianza, duda, euforia, miedo y neutral.

Devuelve solo un JSON valido con estas 5 claves.
Cada valor debe ser un porcentaje entre 0 y 100 con maximo 2 decimales.
La suma total de los 5 porcentajes debe ser exactamente 100.

Texto: {texto}
'''.strip()


def clasificar_emociones(texto: str) -> Emociones:
    if not _OLLAMA_INSTALLED:
        raise RuntimeError(
            "El paquete 'ollama' no está instalado. Instala ollama para usar la clasificación de emociones."
        )

    prompt = construir_prompt_emociones(texto)

    response = chat(
        model='clasificador_texto:latest',
        messages=[{'role': 'user', 'content': prompt}],
        format=Emociones.model_json_schema(),
    )

    contenido = response.message.content.strip()

    if not contenido:
        raise ValueError(
            "El modelo no devolvio JSON en message.content. Revisa el modelo o cambia el prompt."
        )

    try:
        emociones = Emociones.model_validate_json(contenido)
    except ValidationError as error:
        raise ValueError(f"La respuesta del modelo no cumple el formato esperado: {contenido}") from error

    return emociones


def guardar_registro_emocional(texto: str, id_operacion: int, db: Session) -> Registro_emocional:
    registro = db.query(Registro_emocional).filter(
        Registro_emocional.id_operacion == id_operacion
    ).first()

    if registro is None:
        registro = Registro_emocional(id_operacion=id_operacion)
        db.add(registro)

    registro.fecha_hora = datetime.now()
    registro.texto_entrada = texto

    if not _OLLAMA_INSTALLED:
        registro.confianza = Decimal("0")
        registro.duda = Decimal("0")
        registro.euforia = Decimal("0")
        registro.miedo = Decimal("0")
        registro.neutral = Decimal("0")
        return registro

    try:
        emociones = clasificar_emociones(texto)
    except Exception as error:
        print(f"Advertencia: Ollama fallo al clasificar emociones, se guardaran valores en cero. Error: {error}")
        registro.confianza = Decimal("0")
        registro.duda = Decimal("0")
        registro.euforia = Decimal("0")
        registro.miedo = Decimal("0")
        registro.neutral = Decimal("0")
        return registro

    factor_porcentaje = Decimal("100")

    registro.confianza = emociones.confianza / factor_porcentaje
    registro.duda = emociones.duda / factor_porcentaje
    registro.euforia = emociones.euforia / factor_porcentaje
    registro.miedo = emociones.miedo / factor_porcentaje
    registro.neutral = emociones.neutral / factor_porcentaje

    return registro
