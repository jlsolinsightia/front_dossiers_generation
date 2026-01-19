from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.domain.models import UiItem, DossierViewModel


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except Exception:
        return None


def _in_range(d: Optional[datetime], d1: datetime, d2: datetime) -> bool:
    # Si no hay fecha, lo dejamos pasar para no perder items.
    if d is None:
        return True
    return d1 <= d <= d2


def _pretty_section_name(section_key: str) -> str:
    return section_key.replace("_", " ").upper()


def _extract_item_date(it: Dict[str, Any]) -> Optional[datetime]:
    meta = it.get("metadata_json") or {}
    encabezado = meta.get("encabezado") or {}

    # prioridad 1: encabezado
    for key in ["fecha_sesion", "fecha_presentacion"]:
        d = _parse_date(encabezado.get(key))
        if d:
            return d

    # prioridad 2: campos directos del item (por si vienen así)
    for key in ["fecha_sesion", "fecha_presentacion", "fecha"]:
        d = _parse_date(it.get(key))
        if d:
            return d

    # fallback
    return _parse_date(it.get("scraped_at"))



def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x)


def normalize_for_ui_both_chambers(payload: Dict[str, Any], desde: str, hasta: str) -> DossierViewModel:
    d1 = datetime.strptime(desde, "%Y-%m-%d")
    d2 = datetime.strptime(hasta, "%Y-%m-%d")
    if d1 > d2:
        d1, d2 = d2, d1

    data = payload.get("data") or {}
    if not isinstance(data, dict):
        data = {}

    # Indexa llaves en minúsculas para poder acceder sin importar el caso
    data_lc = {str(k).strip().lower(): v for k, v in data.items()}

    out: DossierViewModel = {"SENADO": {}, "DIPUTADOS": {}}
    chambers = [
        ("SENADO", ["senado", "senadores", "camara_senadores", "camara_de_senadores"]),
        ("DIPUTADOS", ["diputados", "camara_diputados", "camara_de_diputados"]),
    ]

    for ui_chamber, aliases in chambers:
        chamber_obj = {}
        for a in aliases:
            obj = data_lc.get(a)
            if isinstance(obj, dict):
                chamber_obj = obj
                break

        # Si no hay dict para esa cámara, sigue
        if not isinstance(chamber_obj, dict):
            continue

        chamber_results: Dict[str, List[UiItem]] = {}

        for section_key, items in chamber_obj.items():
            if not isinstance(items, list):
                continue

            section_name = _pretty_section_name(section_key)
            ui_list: List[UiItem] = []

            for it in items:
                if not isinstance(it, dict):
                    continue

                d = _extract_item_date(it)
                if not _in_range(d, d1, d2):
                    continue

                meta = it.get("metadata_json") or {}
                encabezado = meta.get("encabezado") or {}

                _id = _safe_str(it.get("id") or it.get("gaceta_id") or "")
                titulo = _safe_str(it.get("titulo"))
                promovente = _safe_str(it.get("promovente") or encabezado.get("autor"))
                estatus = _safe_str(it.get("estatus_legislativo") or it.get("estatus"))
                link = _safe_str(it.get("source_url") or it.get("expediente_url"))
                resumen = _safe_str(it.get("synopsis") or it.get("resumen_generado") or "")

                fecha_txt = d.strftime("%Y-%m-%d") if d else ""

                ui_list.append(
                    UiItem(
                        id=_id,
                        fecha=fecha_txt,
                        titulo=titulo,
                        promovente=promovente,
                        estatus=estatus,
                        link=link,
                        resumen=resumen,
                    )
                )

            ui_list.sort(key=lambda x: x.fecha, reverse=True)
            chamber_results[section_name] = ui_list

        out[ui_chamber] = chamber_results

    # Si el JSON no trae cámaras, intenta tratar data como “general”
    if not out["SENADO"] and not out["DIPUTADOS"]:
        # fallback: si payload tuviera "apartados" directo o algo similar, aquí se extendería
        pass

    return out
