from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class ClienteTemas:
    nombre: str
    temas_interes: List[str]


class ClientesRepositoryFile:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> List[ClienteTemas]:
        raw = self.path.read_text(encoding="utf-8-sig")  # utf-8-sig por si trae BOM
        data = json.loads(raw)
        out: List[ClienteTemas] = []

        for c in data.get("clientes", []):
            out.append(
                ClienteTemas(
                    nombre=str(c.get("nombre", "")).strip(),
                    temas_interes=[
                        str(x).strip()
                        for x in (c.get("temas_interes", []) or [])
                        if str(x).strip()
                    ],
                )
            )

        out.sort(key=lambda x: x.nombre.lower())
        return out

    def save(self, clientes: List[ClienteTemas]) -> None:
        """
        Guarda en el MISMO formato que load() espera:

        {
          "clientes": [
            {"nombre": "...", "temas_interes": [...]},
            ...
          ]
        }
        """
        payload = {
            "clientes": [
                {
                    "nombre": c.nombre,
                    "temas_interes": sorted(list(set(c.temas_interes)), key=lambda s: s.lower()),
                }
                for c in sorted(clientes, key=lambda x: x.nombre.lower())
            ]
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
