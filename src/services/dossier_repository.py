from dataclasses import dataclass
from typing import Any, Dict, Protocol

from src.config.settings import Settings


@dataclass(frozen=True)
class DossierQuery:
    cliente: str
    camara: str   # "SENADORES" | "DIPUTADOS" | "ALL"
    desde: str    # YYYY-MM-DD
    hasta: str    # YYYY-MM-DD


class DossierRepository(Protocol):
    def get_dossier(self, q: DossierQuery) -> Dict[str, Any]:
        ...


def build_repository(settings: Settings) -> DossierRepository:
    if settings.DATA_SOURCE == "api":
        from src.services.dossier_repository_api import ApiDossierRepository
        return ApiDossierRepository(settings.API_BASE_URL, settings.API_DOSSIER_ENDPOINT)
    else:
        from src.services.dossier_repository_file import FileDossierRepository
        return FileDossierRepository(settings.MOCK_JSON_PATH)
