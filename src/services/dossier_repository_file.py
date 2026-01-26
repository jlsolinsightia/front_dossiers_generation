from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.services.dossier_repository import DossierQuery



#class FileDossierRepository:
#    def __init__(self, json_path: Path):
#        self.json_path = json_path
#
#    def get_dossier(self, q: DossierQuery) -> Dict[str, Any]:
#        if not self.json_path.exists():
#            raise FileNotFoundError(f"No existe el mock JSON en: {self.json_path}")
#        text = self.json_path.read_text(encoding="utf-8-sig")
#        print("Leyendo mock JSON desde:", self.json_path.resolve())
#        return json.loads(text)


def slugify_cliente(nombre: str) -> str:
    """
    Convierte 'Mercado Libre' -> 'mercado_libre'
    'Aeroméxico' -> 'aeromexico'
    """
    s = (nombre or "").strip().lower()
    s = (
        s.replace("á", "a")
         .replace("é", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ú", "u")
         .replace("ñ", "n")
    )
    s = s.replace("&", "and")
    s = "_".join(s.split())
    return s


class FileDossierRepository:
    def __init__(self, dossiers_dir: Path, fallback_json: Path | None = None):
        self.dossiers_dir = dossiers_dir
        self.fallback_json = fallback_json

    def _read_json(self, path: Path) -> Dict[str, Any]:
        # utf-8-sig evita error BOM
        text = path.read_text(encoding="utf-8-sig")
        return json.loads(text)

    def get_dossier(self, q: DossierQuery) -> Dict[str, Any]:
        slug = slugify_cliente(q.cliente)
        filename = f"dossier_{slug}_{q.desde}_{q.hasta}.json"
        path = self.dossiers_dir / filename

        print(f"[FILE] Buscando mock dossier: {path}")

        if path.exists():
            return self._read_json(path)

        # fallback (por si aún quieres soportar el JSON único)
        if self.fallback_json and self.fallback_json.exists():
            print(f"[FILE] No se encontró {filename}. Usando fallback: {self.fallback_json}")
            return self._read_json(self.fallback_json)

        raise FileNotFoundError(
            f"No se encontró mock para cliente+fechas.\n"
            f"Esperado: {path}\n"
            f"Verifica nombre del cliente, desde/hasta y archivos en: {self.dossiers_dir}"
        )