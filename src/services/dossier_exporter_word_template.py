from __future__ import annotations

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from datetime import datetime
from pathlib import Path
import unicodedata
import re
import zipfile
import tempfile

from docx.shared import RGBColor

from src.domain.models import DossierViewModel, UiItem


# ============================================================
# Utilidades: párrafos
# ============================================================

def insert_paragraph_after(paragraph: Paragraph, text: str = "", style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    p = Paragraph(new_p, paragraph._parent)
    if style:
        p.style = style
    if text:
        p.add_run(text)
    return p


def _delete_paragraph(p: Paragraph) -> None:
    """Elimina un párrafo de python-docx de forma segura."""
    p._element.getparent().remove(p._element)
    p._p = p._element = None  # type: ignore


def _paragraph_text(p: Paragraph) -> str:
    return "".join(run.text for run in p.runs) if p.runs else (p.text or "")


def find_paragraph_with_text(doc: Document, needle: str) -> Paragraph | None:
    needle = (needle or "").strip()
    if not needle:
        return None
    for p in doc.paragraphs:
        if needle in (_paragraph_text(p) or ""):
            return p
    return None


# ============================================================
# Normalización de keys -> tokens
# ============================================================

def normalize_key_for_token(s: str) -> str:
    """
    Convierte:
      'Dictámenes' -> 'DICTAMENES'
      'Declaratoria de reforma constitucional' -> 'DECLARATORIA_DE_REFORMA_CONSTITUCIONAL'
    """
    s = (s or "").strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace(" ", "_")
    return s


def make_token(camara: str, apartado_key: str) -> str:
    cam = "SEN" if camara.upper() == "SENADO" else "DIP"
    ap = normalize_key_for_token(apartado_key)
    return f"{{{{{cam}_{ap}}}}}"


def make_heading_token(camara: str, apartado_key: str) -> str:
    cam = "SEN" if camara.upper() == "SENADO" else "DIP"
    ap = normalize_key_for_token(apartado_key)
    return f"{{{{{cam}_HEADING_{ap}}}}}"


# ============================================================
# Formato de fechas
# ============================================================

_MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def format_rango_fechas_es(date_from: str, date_to: str) -> str:
    d1 = datetime.strptime(date_from, "%Y-%m-%d")
    d2 = datetime.strptime(date_to, "%Y-%m-%d")
    if d1 > d2:
        d1, d2 = d2, d1

    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day} al {d2.day} de {_MESES[d1.month]} de {d1.year}"

    return f"{d1.day} de {_MESES[d1.month]} de {d1.year} al {d2.day} de {_MESES[d2.month]} de {d2.year}"


# ============================================================
# Reemplazo en ZIP/XML (TextBox / Shapes)
# ============================================================

def _strip_xml_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def _replace_tokens_even_if_split(xml: str, replacements: dict[str, str]) -> str:
    """
    Reemplaza tokens aunque estén partidos por tags XML.
    - Encuentra secuencias que empiezan con '{{' y terminan con '}}' (aunque haya tags en medio)
    - Les quita tags para comparar con los tokens esperados
    - Si coincide exacto con una llave de replacements, reemplaza TODA la secuencia por el value
    """
    pattern = re.compile(r"\{\{.*?\}\}", flags=re.DOTALL)

    def repl(m: re.Match) -> str:
        raw = m.group(0)
        plain = _strip_xml_tags(raw)
        plain_norm = "".join(plain.split())
        for k, v in replacements.items():
            k_norm = "".join(k.split())
            if plain_norm == k_norm:
                return v
        return raw

    return pattern.sub(repl, xml)


def replace_token_in_docx_zip(template_path: str, replacements: dict[str, str]) -> str:
    """
    Crea una copia temporal del .docx y reemplaza tokens en TODOS los XML dentro de /word/.
    Esta versión también reemplaza tokens dentro de TextBox/Shapes aunque estén partidos en runs.
    """
    template_path = str(template_path)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.close()
    tmp_path = tmp.name

    with zipfile.ZipFile(template_path, "r") as zin, zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                try:
                    xml = data.decode("utf-8")
                except UnicodeDecodeError:
                    zout.writestr(item, data)
                    continue

                # 1) Reemplazo directo
                for token, value in replacements.items():
                    xml = xml.replace(token, value)

                # 2) Reemplazo robusto (tokens partidos)
                xml = _replace_tokens_even_if_split(xml, replacements)

                data = xml.encode("utf-8")

            zout.writestr(item, data)

    return tmp_path


# ============================================================
# Render de items
# ============================================================

def _add_blue_link_line(anchor_p: Paragraph, url: str) -> Paragraph:
    """
    Inserta una línea con 'Enlace: ' + URL en azul.
    (No es hyperlink clicable al 100% en todos los Word, pero visualmente es link.)
    """
    p = insert_paragraph_after(anchor_p, "  Enlace: ")
    run_url = p.add_run(url)
    run_url.font.color.rgb = RGBColor(0, 0, 255)
    run_url.underline = True
    return p


def add_item_block(anchor_p: Paragraph, item: UiItem) -> Paragraph:
    """
    Formato final:
    • PROMOVENTE (negritas)
      (fecha)
      Título normalizado + Resumen
      Enlace: URL (azul)
      Estatus: VALOR (VALOR en negritas)
    """

    # 1) Bullet con PROMOVENTE en negritas
    p_prom = insert_paragraph_after(anchor_p, "• ")
    run_prom = p_prom.add_run(item.promovente or "Sin promovente")
    run_prom.bold = True
    last = p_prom

    # 2) Fecha
    if item.fecha:
        last = insert_paragraph_after(last, f"  ({item.fecha})")

    # 3) Resumen = título normalizado + resumen
    titulo = (item.titulo or "").strip()
    if titulo:
        # título en "sentence case" simple
        titulo = titulo[:1].upper() + titulo[1:].lower()

    resumen = (item.resumen or "").strip()

    texto_resumen = titulo
    if resumen:
        texto_resumen = f"{titulo} {resumen}" if titulo else resumen

    if texto_resumen:
        last = insert_paragraph_after(last, f"  {texto_resumen}")

    # 4) Enlace (AZUL) — antes del estatus
    if item.link:
        last = _add_blue_link_line(last, item.link)

    # 5) Estatus — palabra normal, VALOR en negritas
    if item.estatus:
        p_est = insert_paragraph_after(last, "  Estatus: ")
        run_val = p_est.add_run(item.estatus)
        run_val.bold = True
        last = p_est

    # 6) Línea en blanco final
    return insert_paragraph_after(last, "")


# ============================================================
# Apartados soportados (8)
# ============================================================

APARTADOS = [
    "COMUNICACIONES",
    "DICTAMENES",
    "INICIATIVAS",
    "PROPOSICIONES",
    "ACUERDOS PARLAMENTARIOS",
    "MINUTAS",
    "DECLARATORIA DE REFORMA CONSTITUCIONAL",
    "DECLARATORIA DE PUBLICIDAD",
]

APARTADO_LABEL = {
    "COMUNICACIONES": "Comunicaciones",
    "DICTAMENES": "Dictámenes",
    "INICIATIVAS": "Iniciativas",
    "PROPOSICIONES": "Proposiciones",
    "ACUERDOS PARLAMENTARIOS": "Acuerdos Parlamentarios",
    "MINUTAS": "Minutas",
    "DECLARATORIA DE REFORMA CONSTITUCIONAL": "Declaratoria de reforma constitucional",
    "DECLARATORIA DE PUBLICIDAD": "Declaratoria de publicidad",
}


# ============================================================
# Export principal
# ============================================================

def export_selected_to_template(
    vm: DossierViewModel,
    template_path: str,
    output_path: str,
    date_from: str,
    date_to: str,
    cliente: str | None = None,
) -> None:
    # --------------------------------------------------------
    # 1) Reemplazos en TextBox por ZIP/XML:
    #   - {{RANGO_FECHAS}}
    #   - {{CLIENTE}}
    #   - {{SEN_HEADING_*}} / {{DIP_HEADING_*}}  (subtítulos)
    # --------------------------------------------------------
    rango = format_rango_fechas_es(date_from, date_to)

    repls: dict[str, str] = {
        "{{RANGO_FECHAS}}": rango,
        "{{CLIENTE}}": (cliente or ""),
    }

    for camara in ["SENADO", "DIPUTADOS"]:
        apartados = (vm.get(camara) or {})
        for ap in APARTADOS:
            items = apartados.get(ap, []) or []
            token_heading = make_heading_token(camara, ap)
            repls[token_heading] = APARTADO_LABEL.get(ap, ap.title()) if items else ""

    tmp_docx = replace_token_in_docx_zip(template_path, repls)

    # --------------------------------------------------------
    # 2) Abrir doc y llenar contenidos (tokens del body):
    #   - {{SEN_COMUNICACIONES}}, etc.
    #   Si NO hay items -> borrar el párrafo del token
    # --------------------------------------------------------
    doc = Document(tmp_docx)

    for camara in ["SENADO", "DIPUTADOS"]:
        apartados = (vm.get(camara) or {})

        for ap in APARTADOS:
            items = apartados.get(ap, []) or []
            tok = make_token(camara, ap)

            anchor = find_paragraph_with_text(doc, tok)
            if anchor is None:
                continue

            if not items:
                _delete_paragraph(anchor)
                continue

            anchor_text = _paragraph_text(anchor) or ""
            if tok in anchor_text:
                anchor.text = anchor_text.replace(tok, "").strip()

            last_p = anchor
            for it in items:
                last_p = add_item_block(last_p, it)

    doc.save(output_path)

    # Limpieza temporal
    try:
        Path(tmp_docx).unlink(missing_ok=True)
    except Exception:
        pass
