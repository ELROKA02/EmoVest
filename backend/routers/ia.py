from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ai.emotions import Emociones
from ai.manager import (
    AI_USE_CASE_CHAT,
    AI_USE_CASE_EMOTION,
    default_base_url_for_provider,
    get_effective_ai_settings,
    get_provider,
    get_provider_catalog,
    list_recommended_models,
    list_use_cases,
    normalize_use_case,
)
from ai.providers.base import AiRuntimeSettings
from database import get_db
from models import AiSetting, Registro_emocional, Usuario
from routers.auth import get_current_user


router = APIRouter(prefix="/ia", tags=["emociones"])


class AiConfigUpdate(BaseModel):
    provider: str
    model: str
    base_url: str | None = None
    install_mode: str = "manual"


class AiTestRequest(BaseModel):
    texto: str


class AiChatTestRequest(BaseModel):
    mensaje: str


def _settings_to_response(settings: AiRuntimeSettings) -> dict:
    return {
        "use_case": settings.use_case,
        "provider": settings.provider,
        "model": settings.model,
        "base_url": settings.base_url,
        "install_mode": settings.install_mode,
        "source": settings.source,
    }


def clasificar_emociones(texto: str, db: Session | None = None) -> Emociones:
    settings = get_effective_ai_settings(AI_USE_CASE_EMOTION, db)
    provider = get_provider(settings)
    return provider.clasificar_emociones(texto)


def ollama_disponible(db: Session | None = None) -> bool:
    settings = get_effective_ai_settings(AI_USE_CASE_EMOTION, db)
    if settings.provider != "ollama":
        return False

    try:
        return bool(get_provider(settings).status().get("available"))
    except Exception:
        return False


def guardar_registro_emocional(texto: str, id_operacion: int, db: Session) -> Registro_emocional:
    registro = db.query(Registro_emocional).filter(
        Registro_emocional.id_operacion == id_operacion
    ).first()

    if registro is None:
        registro = Registro_emocional(id_operacion=id_operacion)
        db.add(registro)

    registro.fecha_hora = datetime.now()
    registro.texto_entrada = texto

    try:
        emociones = clasificar_emociones(texto, db)
    except Exception as error:
        print(f"Advertencia: la IA fallo al clasificar emociones, se guardaran valores en cero. Error: {error}")
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


@router.get(
    "/providers",
    tags=["configuracion"],
    summary="Listar proveedores de IA soportados",
    status_code=status.HTTP_200_OK,
)
def listar_proveedores(
    _current_user: Usuario = Depends(get_current_user),
):
    return {
        "use_cases": list_use_cases(),
        "providers": get_provider_catalog(),
    }


@router.get(
    "/config",
    tags=["configuracion"],
    summary="Obtener configuracion activa de IA",
    status_code=status.HTTP_200_OK,
)
def obtener_configuracion_ia(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    emotion_settings = get_effective_ai_settings(AI_USE_CASE_EMOTION, db)
    chat_settings = get_effective_ai_settings(AI_USE_CASE_CHAT, db)
    return {
        "configs": {
            AI_USE_CASE_EMOTION: _settings_to_response(emotion_settings),
            AI_USE_CASE_CHAT: _settings_to_response(chat_settings),
        },
        "recommended_models": {
            AI_USE_CASE_EMOTION: list_recommended_models(emotion_settings.provider, AI_USE_CASE_EMOTION),
            AI_USE_CASE_CHAT: list_recommended_models(chat_settings.provider, AI_USE_CASE_CHAT),
        },
    }


@router.put(
    "/config/{use_case}",
    tags=["configuracion"],
    summary="Actualizar configuracion de IA por uso",
    status_code=status.HTTP_200_OK,
)
def actualizar_configuracion_ia(
    use_case: str,
    payload: AiConfigUpdate,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    try:
        use_case = normalize_use_case(use_case)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    provider = payload.provider.strip().lower()
    model = payload.model.strip()
    install_mode = payload.install_mode.strip().lower()
    base_url = (payload.base_url or default_base_url_for_provider(provider, use_case)).rstrip("/")

    if not model:
        raise HTTPException(status_code=400, detail="El modelo de IA no puede estar vacio.")

    try:
        get_provider(
            AiRuntimeSettings(
                use_case=use_case,
                provider=provider,
                model=model,
                base_url=base_url,
                install_mode=install_mode,
            )
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    setting = db.query(AiSetting).filter(AiSetting.use_case == use_case).first()
    if setting is None:
        setting = AiSetting(use_case=use_case)
        db.add(setting)

    setting.use_case = use_case
    setting.provider = provider
    setting.model = model
    setting.base_url = base_url
    setting.install_mode = install_mode

    db.commit()
    db.refresh(setting)

    settings = get_effective_ai_settings(use_case, db)
    return {"config": _settings_to_response(settings)}


@router.get(
    "/status",
    tags=["configuracion"],
    summary="Consultar estado del proveedor de IA activo",
    status_code=status.HTTP_200_OK,
)
def consultar_estado_ia(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    emotion_settings = get_effective_ai_settings(AI_USE_CASE_EMOTION, db)
    chat_settings = get_effective_ai_settings(AI_USE_CASE_CHAT, db)
    return {
        "statuses": {
            AI_USE_CASE_EMOTION: {
                "config": _settings_to_response(emotion_settings),
                "status": get_provider(emotion_settings).status(),
                "recommended_models": list_recommended_models(
                    emotion_settings.provider,
                    AI_USE_CASE_EMOTION,
                ),
            },
            AI_USE_CASE_CHAT: {
                "config": _settings_to_response(chat_settings),
                "status": get_provider(chat_settings).status(),
                "recommended_models": list_recommended_models(
                    chat_settings.provider,
                    AI_USE_CASE_CHAT,
                ),
            },
        },
    }


@router.post(
    "/test",
    summary="Probar clasificacion emocional con la configuracion activa",
    status_code=status.HTTP_200_OK,
)
def probar_ia(
    payload: AiTestRequest,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    try:
        emociones = clasificar_emociones(payload.texto, db)
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {"emociones": emociones.model_dump()}


@router.post(
    "/chat/test",
    tags=["chat_ia"],
    summary="Probar respuesta de chat con la configuracion de chat activa",
    status_code=status.HTTP_200_OK,
)
def probar_chat_ia(
    payload: AiChatTestRequest,
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(get_current_user),
):
    settings = get_effective_ai_settings(AI_USE_CASE_CHAT, db)
    provider = get_provider(settings)

    try:
        respuesta = provider.generar_respuesta_chat(payload.mensaje)
    except Exception as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "config": _settings_to_response(settings),
        "respuesta": respuesta,
    }
