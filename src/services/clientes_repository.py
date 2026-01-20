from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict


@dataclass(frozen=True)
class ClienteTemas:
    nombre: str
    temas_interes: List[str]


class ClientesRepositoryFile:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> List[ClienteTemas]:
        raw = self.path.read_text(encoding="utf-8-sig")  # utf-8-sig por si trae BOM
        data = json.loads(raw)
        out: List[ClienteTemas] = []

        for c in data.get("clientes", []):
            out.append(
                ClienteTemas(
                    nombre=str(c.get("nombre", "")).strip(),
                    temas_interes=[str(x).strip() for x in (c.get("temas_interes", []) or []) if str(x).strip()],
                )
            )
        # orden alfabético
        out.sort(key=lambda x: x.nombre.lower())
        return out
