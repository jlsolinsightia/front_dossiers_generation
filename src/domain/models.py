from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class UiItem:
    id: str
    fecha: str
    titulo: str
    promovente: str
    estatus: str
    link: str
    resumen: str


# ViewModel:
# {"SENADO": {"COMUNICACIONES": [UiItem, ...], ...}, "DIPUTADOS": {...}}
DossierViewModel = Dict[str, Dict[str, List[UiItem]]]
