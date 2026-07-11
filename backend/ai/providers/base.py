from abc import ABC, abstractmethod
from dataclasses import dataclass

from ai.emotions import Emociones


@dataclass(frozen=True)
class AiRuntimeSettings:
    use_case: str
    provider: str
    model: str
    base_url: str
    install_mode: str = "manual"
    source: str = "env"


class AIProvider(ABC):
    provider_id: str
    display_name: str
    description: str
    supports_local_install: bool = False

    def __init__(self, settings: AiRuntimeSettings):
        self.settings = settings

    @abstractmethod
    def status(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def clasificar_emociones(self, texto: str) -> Emociones:
        raise NotImplementedError

    @abstractmethod
    def generar_respuesta_chat(self, mensaje: str) -> str:
        raise NotImplementedError
