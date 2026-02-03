import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional
from tkinter import filedialog, messagebox
import os

from src.services.dossier_exporter_word_template import export_selected_to_template
from src.domain.models import UiItem, DossierViewModel


PREFERRED_SECTIONS = [
    "COMUNICACIONES",
    "DICTAMENES",
    "DICTÁMENES",
    "INICIATIVAS",
    "PROPOSICIONES",
    "ACUERDOS PARLAMENTARIOS",
    "MINUTAS",
    "INTERVENCIONES VERBALES",
    "OTROS",
]


class ResultadosView(ttk.Frame):
    def __init__(self, parent, template_path: str):
        self.template_path = template_path
        self._date_from = ""
        self._date_to = ""
        self._selected: set[str] = set()   # keys únicos de items seleccionados
        self._item_index: dict[str, UiItem] = {}  # key -> UiItem (para export y detalle)
        super().__init__(parent)

        ttk.Label(self, text="Resultados", style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        self.status = ttk.Label(self, text="", style="Subtitle.TLabel")
        self.status.pack(anchor="w", pady=(0, 10))

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(0,10))

        btn_select_all = ttk.Button(
            actions,
            text="Seleccionar todo",
            command=self._select_all
        )
        btn_select_all.pack(side="left")

        self.btn_export = ttk.Button(
            actions,
            text="Exportar a Word",
            command=self._export_word
        )
        self.btn_export.pack(side="right")


        self.btn_clear = ttk.Button(actions, text="Limpiar selección", command=self._clear_selection)
        self.btn_clear.pack(side="right", padx=(0, 8))

        # self.btn_export = ttk.Button(actions, text = "Exportar a Word", command = self._export_word)
        # self.btn_export.pack(side = "right")

        self.nb_camaras = ttk.Notebook(self)
        self.nb_camaras.pack(fill="both", expand=True)

        self._vm: Optional[DossierViewModel] = None
        self._trees: Dict[str, Dict[str, ttk.Treeview]] = {}  # camara -> apartado -> tree

    def set_status(self, text: str):
        self.status.configure(text=text)

    def _export_word(self):
        if not self._vm:
            messagebox.showwarning("Sin datos", "No hay resultados para exportar.")
            return

        if not self._selected:
            messagebox.showwarning(
                "Nada seleccionado",
                "Selecciona (☑) los items que quieres exportar en las tablas."
            )
            return

        filtered_vm = {"SENADO": {}, "DIPUTADOS": {}}
        for camara, apartados in (self._vm or {}).items():
            for apartado, items in (apartados or {}).items():
                kept = []
                for it in items:
                    rid = (it.id or f"{apartado}_{it.fecha}_{hash(it.titulo)}")[:200]
                    key = f"{camara}|{apartado}|{rid}"
                    if key in self._selected:
                        kept.append(it)
                if kept:
                    filtered_vm[camara][apartado] = kept

        # si por algún motivo el filtro quedó vacío:
        total_kept = sum(len(v) for cam in filtered_vm.values() for v in cam.values())
        if total_kept == 0:
            messagebox.showwarning("Sin elementos", "No quedó ningún item seleccionado para exportación.")
            return

        # ... aquí ya haces asksaveasfilename y exportas usando filtered_vm ...
        default_name = f"Dossier_{self._date_from}_a_{self._date_to}.docx".replace("-", "")
        path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=[("Word Document", "*.docx")],
            initialfile=default_name,
            title="Guardar Dossier en Word",
)

        if not path:
            return

        export_selected_to_template(
            vm=filtered_vm,
            template_path=self.template_path,
            output_path=path,
            date_from=self._date_from,
            date_to=self._date_to,
            cliente=None,
        )

        messagebox.showinfo("Exportación exitosa", f"Dossier guardado en:\n{path}")



    def render(self, vm: DossierViewModel, date_from: str, date_to: str):
        self._date_from = date_from
        self._date_to = date_to
        self._vm = vm
        self._trees.clear()
        self._item_index.clear()


        # Limpia tabs
        for tab_id in self.nb_camaras.tabs():
            self.nb_camaras.forget(tab_id)

        total = 0
        for cam in vm:
            for ap in vm[cam]:
                total += len(vm[cam][ap])

        self.set_status(f"Rango: {date_from} → {date_to} | Total items: {total}")

        for camara in ["SENADO", "DIPUTADOS"]:
            sections = vm.get(camara) or {}
            cam_tab = ttk.Frame(self.nb_camaras)
            self.nb_camaras.add(cam_tab, text=f"{camara.title()} ({sum(len(v) for v in sections.values())})")

            nb_sections = ttk.Notebook(cam_tab)
            nb_sections.pack(fill="both", expand=True)

            self._trees[camara] = {}

            # Orden de apartados
            keys = list(sections.keys())
            keys_sorted = [k for k in PREFERRED_SECTIONS if k in keys] + [k for k in keys if k not in PREFERRED_SECTIONS]

            if not keys_sorted:
                empty = ttk.Label(cam_tab, text="Sin resultados para esta cámara.")
                empty.pack(anchor="w", padx=10, pady=10)
                continue

            for apartado in keys_sorted:
                rows = sections.get(apartado, [])

                tab = ttk.Frame(nb_sections)
                nb_sections.add(tab, text=f"{apartado.title()} ({len(rows)})")

                tree = ttk.Treeview(
                tab,
                columns=("sel", "fecha", "titulo", "promovente", "estatus"),
                show="headings",
                height=18,
                )

                tree.heading("sel", text="Sel")
                tree.heading("fecha", text="Fecha")
                tree.heading("titulo", text="Título")
                tree.heading("promovente", text="Promovente")
                tree.heading("estatus", text="Estatus")

                tree.column("sel", width=50, anchor="center")
                tree.column("fecha", width=110, anchor="w")
                tree.column("titulo", width=520, anchor="w")
                tree.column("promovente", width=220, anchor="w")
                tree.column("estatus", width=160, anchor="w")


                tree.pack(fill="both", expand=True, padx=8, pady=8)

                for r in rows:
                    rid = (r.id or f"{apartado}_{r.fecha}_{hash(r.titulo)}")[:200]
                    key = f"{camara}|{apartado}|{rid}"   # key global único

                    self._item_index[key] = r

                    checked = "☑" if key in self._selected else "☐"
                    tree.insert(
                        "",
                        "end",
                        iid=key,   # usamos key como iid del tree
                        values=(checked, r.fecha, r.titulo, r.promovente, r.estatus),
                    )
                
                tree.bind("<Button-1>", lambda e, c=camara, a=apartado: self._on_tree_click(e, c, a), add="+")
                tree.bind("<Double-1>", lambda e, c=camara, a=apartado: self._open_selected(c, a))

                self._trees[camara][apartado] = tree

            # Selecciona primera sección con data
            for i, ap in enumerate(keys_sorted):
                if sections.get(ap):
                    nb_sections.select(i)
                    break

        # Selecciona Senado si tiene algo, si no Diputados
        if sum(len(v) for v in (vm.get("SENADO") or {}).values()) > 0:
            self.nb_camaras.select(0)
        else:
            self.nb_camaras.select(1)

    def _open_selected(self, camara: str, apartado: str):
        if not self._vm:
            return
        tree = self._trees.get(camara, {}).get(apartado)
        if not tree:
            return
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]  # iid == key completo
        row = self._item_index.get(iid)
        if not row:
            return  

        top = self.winfo_toplevel()
        dialog = tk.Toplevel(top)
        dialog.title(row.titulo[:90] if row.titulo else "Detalle")
        dialog.geometry("900x560")

        ttk.Label(dialog, text=row.titulo, style="Title.TLabel").pack(anchor="w", padx=12, pady=(12, 4))
        ttk.Label(
            dialog,
            text=f"Cámara: {camara} | Apartado: {apartado} | Fecha: {row.fecha} | Estatus: {row.estatus}",
            style="Subtitle.TLabel",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        if row.link:
            ttk.Label(dialog, text=f"Link: {row.link}").pack(anchor="w", padx=12, pady=(0, 8))

        txt = tk.Text(dialog, wrap="word")
        txt.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        txt.insert("1.0", row.resumen or "(Sin resumen)")
        txt.configure(state="disabled")

    def _on_tree_click(self, event, camara: str, apartado: str):
        if not self._vm:
            return

        tree = self._trees.get(camara, {}).get(apartado)
        if not tree:
            return

        # ¿qué columna se clickeó?
        col = tree.identify_column(event.x)  # '#1' = primera columna
        row_id = tree.identify_row(event.y)
        if not row_id:
            return

        # Solo toggle si fue en la columna "sel" (primera)
        if col != "#1":
            return

        key = row_id  # porque iid = key
        if key in self._selected:
            self._selected.remove(key)
            new_val = "☐"
        else:
            self._selected.add(key)
            new_val = "☑"

        # actualiza solo la columna sel del row
        current = list(tree.item(key, "values"))
        current[0] = new_val
        tree.item(key, values=tuple(current))

        # Actualiza status con conteo seleccionados
        self._update_selected_status()

    def _update_selected_status(self):
        sel = len(self._selected)
        # conserva el status principal y agrega seleccionados
        base = self.status.cget("text") or ""
        # evita duplicar
        if "| Seleccionados:" in base:
            base = base.split("| Seleccionados:")[0].strip()
        self.set_status(f"{base} | Seleccionados: {sel}")

    def _clear_selection(self):
        self._selected.clear()
        self._update_selected_status()
        # refresca el render para que vuelva a mostrar ☐
        if self._vm:
            self.render(self._vm, self._date_from, self._date_to)

    def _select_all(self):
        """
        Marca todos los items visibles en todas las tablas.
        """
        if not self._vm:
            return

        self._selected.clear()

        for camara, apartados in self._trees.items():
            for apartado, tree in apartados.items():
                for iid in tree.get_children():
                    # iid ya es la key global
                    self._selected.add(iid)

                    values = list(tree.item(iid, "values"))
                    values[0] = "☑"   # columna sel
                    tree.item(iid, values=tuple(values))

        self._update_selected_status()
