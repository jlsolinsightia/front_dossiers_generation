from docx import Document
from src.domain.models import DossierViewModel, UiItem
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from datetime import datetime
import zipfile
import tempfile
from pathlib import Path

from docx.table import Table, _Cell
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P


# ============================================================
# Helpers de inserción y búsqueda
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


SECTION_LABELS = {
    "COMUNICACIONES": "Comunicaciones",
    "DICTAMENES": "Dictámenes",
    "DICTÁMENES": "Dictámenes",
    "INICIATIVAS": "Iniciativas",
    "PROPOSICIONES": "Proposiciones",
    "ACUERDOS PARLAMENTARIOS": "Acuerdos Parlamentarios",
    "MINUTAS": "Minutas",
}

# ✅ Títulos EXACTOS como aparecen en tu plantilla (para borrar secciones vacías)
# Ajusta el valor si en tu doc dice plural/singular distinto.
TEMPLATE_HEADINGS = {
    "COMUNICACIONES": "Comunicaciones",
    "DICTAMENES": "Dictámenes",
    "DICTÁMENES": "Dictámenes",
    "INICIATIVAS": "Iniciativas",
    "PROPOSICIONES": "Proposiciones",
    "ACUERDOS PARLAMENTARIOS": "Acuerdo Parlamentario",  # <-- ajusta si tu plantilla usa plural
    "MINUTAS": "Minutas",
}


def get_section_label(apartado_key: str) -> str:
    """
    Traduce la clave interna del ViewModel
    al texto usado en la plantilla de Word.
    """
    return SECTION_LABELS.get(apartado_key.upper(), apartado_key.title())


def find_paragraph_with_text(doc: Document, needle: str) -> Paragraph | None:
    needle = (needle or "").strip()
    if not needle:
        return None
    for p in doc.paragraphs:
        if needle in (p.text or ""):
            return p
    return None


def make_token(camara: str, apartado_key: str) -> str:
    cam = "SEN" if camara.upper() == "SENADO" else "DIP"
    ap = apartado_key.upper().replace(" ", "_")
    return f"{{{{{cam}_{ap}}}}}"


def add_item_block(anchor_p: Paragraph, item: UiItem) -> Paragraph:
    # Línea 1: título
    p1 = insert_paragraph_after(anchor_p, f"• ({item.fecha}) {item.titulo}")
    # Línea 2: promovente / estatus
    p2 = insert_paragraph_after(p1, f"  Promovente: {item.promovente} | Estatus: {item.estatus}")
    last = p2
    # Línea 3: resumen
    if item.resumen:
        last = insert_paragraph_after(last, f"  Resumen: {item.resumen}")
    # Línea 4: link
    if item.link:
        last = insert_paragraph_after(last, f"  Enlace: {item.link}")
    # Espacio
    return insert_paragraph_after(last, "")


# ============================================================
# Formato de fechas
# ============================================================

_MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}


def format_rango_fechas_es(date_from: str, date_to: str) -> str:
    """
    Recibe YYYY-MM-DD y regresa estilo:
    "23 al 27 de junio de 2025"
    o si cambia mes/año: "30 de junio de 2025 al 02 de julio de 2025"
    """
    d1 = datetime.strptime(date_from, "%Y-%m-%d")
    d2 = datetime.strptime(date_to, "%Y-%m-%d")
    if d1 > d2:
        d1, d2 = d2, d1

    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.day} al {d2.day} de {_MESES[d1.month]} de {d1.year}"

    return f"{d1.day} de {_MESES[d1.month]} de {d1.year} al {d2.day} de {_MESES[d2.month]} de {d2.year}"


# ============================================================
# Reemplazo en ZIP/XML (para TextBox / Shapes)
# ============================================================

def replace_token_in_docx_zip(template_path: str, replacements: dict[str, str]) -> str:
    """
    Crea una copia temporal del .docx y reemplaza tokens en TODOS los XML dentro de /word/.
    Esto sí alcanza texto dentro de TextBox/Shapes (w:txbxContent) en headers/footers.

    Regresa la ruta del docx temporal listo para abrir con python-docx.
    """
    template_path = str(template_path)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    tmp.close()
    tmp_path = tmp.name

    with zipfile.ZipFile(template_path, "r") as zin, zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)

            # Solo tocamos XMLs del documento (word/*.xml)
            if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    zout.writestr(item, data)
                    continue

                for token, value in replacements.items():
                    text = text.replace(token, value)

                data = text.encode("utf-8")

            zout.writestr(item, data)

    return tmp_path


# ============================================================
# Eliminar secciones vacías
# ============================================================

def _delete_paragraph(p: Paragraph) -> None:
    """Elimina un párrafo de python-docx de forma segura."""
    p._element.getparent().remove(p._element)
    p._p = p._element = None  # type: ignore


def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())


def _paragraph_text(p: Paragraph) -> str:
    return "".join(run.text for run in p.runs) if p.runs else (p.text or "")


def remove_empty_section_by_token(
    doc: Document,
    token: str,
    heading_text: str,
    remove_heading_duplicates: int = 2
) -> bool:
    """
    Busca el párrafo que contiene 'token' y elimina:
      - ese párrafo (token)
      - y los N párrafos anteriores que coincidan con el título del apartado (duplicado en plantilla)
    Retorna True si encontró y eliminó el token.
    """
    token_n = token.strip()
    heading_n = _norm(heading_text)

    paragraphs = list(doc.paragraphs)

    # 1) localizar token
    idx_token = None
    for i, p in enumerate(paragraphs):
        if token_n in _paragraph_text(p):
            idx_token = i
            break

    if idx_token is None:
        return False

    # 2) borrar token
    _delete_paragraph(paragraphs[idx_token])

    # 3) borrar títulos previos (duplicados)
    removed = 0
    j = idx_token - 1
    while j >= 0 and removed < remove_heading_duplicates:
        txt = _norm(_paragraph_text(paragraphs[j]))
        if txt == heading_n:
            _delete_paragraph(paragraphs[j])
            removed += 1
        j -= 1

    return True


def _starts_item_line(p: Paragraph) -> bool:
    t = (_paragraph_text(p) or "").strip()
    return t.startswith("• (")


def remove_empty_sections_by_headings(doc: Document, headings: list[str], heading_duplicates: int = 2) -> None:
    """
    Segunda pasada:
    Si entre un heading y el siguiente heading no hay items (líneas '• ('),
    borra ese heading (y duplicados) y algunos párrafos vacíos inmediatos.
    """
    norm_headings = [_norm(h) for h in headings]

    i = 0
    while i < len(doc.paragraphs):
        p = doc.paragraphs[i]
        txtn = _norm(_paragraph_text(p))

        if txtn in norm_headings:
            current_heading = txtn

            # Busca hasta el siguiente heading y revisa si hay items
            j = i + 1
            has_items = False
            while j < len(doc.paragraphs):
                tjn = _norm(_paragraph_text(doc.paragraphs[j]))
                if tjn in norm_headings:
                    break
                if _starts_item_line(doc.paragraphs[j]):
                    has_items = True
                    break
                j += 1

            # Si NO hay items, borrar heading(s) duplicados + vacíos cercanos
            if not has_items:
                removed = 0
                k = i
                # borra headings iguales consecutivos (típico duplicado en plantilla)
                while k < len(doc.paragraphs) and removed < heading_duplicates:
                    if _norm(_paragraph_text(doc.paragraphs[k])) == current_heading:
                        _delete_paragraph(doc.paragraphs[k])
                        removed += 1
                    else:
                        break

                # borra hasta 3 párrafos vacíos inmediatos después
                c = 0
                while i < len(doc.paragraphs) and c < 3:
                    if _norm(_paragraph_text(doc.paragraphs[i])) == "":
                        _delete_paragraph(doc.paragraphs[i])
                        c += 1
                    else:
                        break

                continue  # re-evaluar misma posición

        i += 1


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
    # 1) Reemplazo de rango en TextBox por ZIP
    rango = format_rango_fechas_es(date_from, date_to)
    tmp_docx = replace_token_in_docx_zip(
        template_path,
        {"{{RANGO_FECHAS}}": rango}
    )

    # 2) Abrir doc ya “preparado”
    doc = Document(tmp_docx)

    # 3) (Opcional) reemplazar “Cliente: ____”
    if cliente:
        p = find_paragraph_with_text(doc, "Cliente")
        if p and "Cliente" in (p.text or ""):
            p.text = f"Cliente: {cliente}"

    # 4) Inserción y/o borrado por token
    for camara in ["SENADO", "DIPUTADOS"]:
        apartados = (vm.get(camara) or {})

        for apartado_key in TEMPLATE_HEADINGS.keys():
            items = apartados.get(apartado_key, []) or []
            tok = make_token(camara, apartado_key)
            heading = TEMPLATE_HEADINGS.get(apartado_key, get_section_label(apartado_key))

            # Si NO hay items: intenta borrar token + headings previos
            if not items:
                removed = remove_empty_section_by_token(
                    doc,
                    token=tok,
                    heading_text=heading,
                    remove_heading_duplicates=2
                )
                # fallback: si no borró por headings, al menos elimina el token
                if not removed:
                    anchor_tok = find_paragraph_with_text(doc, tok)
                    if anchor_tok is not None:
                        _delete_paragraph(anchor_tok)
                continue

            # Si hay items: inserta debajo del token
            anchor = find_paragraph_with_text(doc, tok)

            # Fallback por label si no existe token
            if anchor is None:
                label = get_section_label(apartado_key)
                anchor = find_paragraph_with_text(doc, label)

            if anchor is None:
                continue

            if tok in (anchor.text or ""):
                anchor.text = (anchor.text or "").replace(tok, "").strip()

            last_p = anchor
            for it in items:
                last_p = add_item_block(last_p, it)

    # ✅ 5) Segunda pasada: eliminar headings que quedaron sin contenido
    headings = list(TEMPLATE_HEADINGS.values())
    remove_empty_sections_by_headings(doc, headings=headings, heading_duplicates=2)

    # 6) Guardar
    doc.save(output_path)

    # 7) Limpieza temporal
    try:
        Path(tmp_docx).unlink(missing_ok=True)
    except Exception:
        pass

def iter_paragraphs_in(container):
    """
    Itera párrafos en orden, incluyendo los que están dentro de tablas.
    container puede ser: Document o _Cell
    """
    # Document
    if hasattr(container, "element") and hasattr(container.element, "body"):
        parent_elm = container.element.body
    else:
        # _Cell
        parent_elm = container._tc

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, container)
        elif isinstance(child, CT_Tbl):
            tbl = Table(child, container)
            for row in tbl.rows:
                for cell in row.cells:
                    yield from iter_paragraphs_in(cell)
