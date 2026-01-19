from docx import Document
from typing import Dict
from src.domain.models import DossierViewModel, UiItem
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.shared import Pt
from datetime import datetime
import zipfile
import tempfile
from pathlib import Path

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

def get_section_label(apartado_key: str) -> str:
    """
    Traduce la clave interna del ViewModel
    al texto EXACTO usado en la plantilla de Word.
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

def export_selected_to_template(
    vm: DossierViewModel,
    template_path: str,
    output_path: str,
    date_from: str,
    date_to: str,
    cliente: str | None = None,
) -> None:
    doc = Document(template_path)
    rango = format_rango_fechas_es(date_from, date_to)

    # 1) Reemplaza tokens a nivel ZIP/XML (sí funciona en TextBox)
    tmp_docx = replace_token_in_docx_zip(
        template_path,
        {"{{RANGO_FECHAS}}": rango}
)

    # 2) Ahora sí abre el doc ya “preparado”
    doc = Document(tmp_docx)

    # if replaced == 0:
    #     print("Aviso: no se encontró {{RANGO_FECHAS}} en body/header/footer (párrafos o tablas).")


    # (Opcional) reemplazar el texto “Cliente: ____”
    if cliente:
        p = find_paragraph_with_text(doc, "Cliente")
        if p and "Cliente" in (p.text or ""):
            # muy simple: reemplaza toda la línea por "Cliente: X"
            p.text = f"Cliente: {cliente}"

    # Recorre cámaras y apartados
    for camara in ["SENADO", "DIPUTADOS"]:
        apartados = (vm.get(camara) or {})
        for apartado_key, items in apartados.items():
            if not items:
                continue

            tok = make_token(camara, apartado_key)
            anchor = find_paragraph_with_text(doc, tok)

            # Si no existe el token en plantilla, intenta fallback por label
            if anchor is None:
                label = get_section_label(apartado_key)
                anchor = find_paragraph_with_text(doc, label)

            if anchor is None:
                # no encontramos dónde insertar; lo saltamos
                continue

            # Si era token, bórralo del texto del párrafo
            if tok in (anchor.text or ""):
                anchor.text = (anchor.text or "").replace(tok, "").strip()

            # Inserta items debajo del anchor
            last_p = anchor
            for it in items:
                last_p = add_item_block(last_p, it)

    doc.save(output_path)

    try:
        Path(tmp_docx).unlink(missing_ok=True)
    except Exception:
        pass

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

    # Si cambia mes o año, lo hacemos explícito
    return f"{d1.day} de {_MESES[d1.month]} de {d1.year} al {d2.day} de {_MESES[d2.month]} de {d2.year}"

def _replace_in_paragraph(paragraph: Paragraph, token: str, value: str) -> int:
    """
    Reemplaza token dentro del texto del párrafo.
    Nota: esto “aplana” runs (pierde formato por run). Para tu caso del header suele estar bien.
    """
    if token in (paragraph.text or ""):
        paragraph.text = (paragraph.text or "").replace(token, value)
        return 1
    return 0


def _replace_in_table(table, token: str, value: str) -> int:
    count = 0
    for row in table.rows:
        for cell in row.cells:
            # párrafos en celda
            for p in cell.paragraphs:
                count += _replace_in_paragraph(p, token, value)
            # tablas anidadas (por si acaso)
            for t in cell.tables:
                count += _replace_in_table(t, token, value)
    return count


def _replace_in_container(container, token: str, value: str) -> int:
    """
    container puede ser:
    - doc (Document)
    - section.header
    - section.footer
    """
    count = 0
    for p in container.paragraphs:
        count += _replace_in_paragraph(p, token, value)
    for t in container.tables:
        count += _replace_in_table(t, token, value)
    return count


def replace_token_everywhere(doc: Document, token: str, value: str) -> int:
    """
    Reemplaza token en:
    - body
    - headers
    - footers
    Incluye párrafos y tablas.
    Regresa cuántos reemplazos hizo.
    """
    count = 0

    # body
    count += _replace_in_container(doc, token, value)

    # headers/footers
    for s in doc.sections:
        count += _replace_in_container(s.header, token, value)
        count += _replace_in_container(s.footer, token, value)

    return count

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
                    # si algo raro, lo dejamos igual
                    zout.writestr(item, data)
                    continue

                for token, value in replacements.items():
                    text = text.replace(token, value)

                data = text.encode("utf-8")

            zout.writestr(item, data)

    return tmp_path

