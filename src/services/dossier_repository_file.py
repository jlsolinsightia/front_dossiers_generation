import json
from pathlib import Path
from typing import Any, Dict

from src.services.dossier_repository import DossierQuery


class FileDossierRepository:
    def __init__(self, json_path: Path):
        self.json_path = json_path

    def get_dossier(self, q: DossierQuery) -> Dict[str, Any]:
        if not self.json_path.exists():
            raise FileNotFoundError(f"No existe el mock JSON en: {self.json_path}")
        text = self.json_path.read_text(encoding="utf-8-sig")
        print("Leyendo mock JSON desde:", self.json_path.resolve())
        return json.loads(text)
