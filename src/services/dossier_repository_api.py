from typing import Any, Dict
import requests

from src.services.dossier_repository import DossierQuery


class ApiDossierRepository:
    def __init__(self, base_url: str, endpoint: str):
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"

    def get_dossier(self, q: DossierQuery) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoint}"
        params = {
            "cliente": q.cliente,
            "camara": q.camara,
            "desde": q.desde,
            "hasta": q.hasta,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
