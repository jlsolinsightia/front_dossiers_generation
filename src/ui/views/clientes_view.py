from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Callable, Optional

from src.services.clientes_repository import ClienteTemas


class ClientesView(ttk.Frame):
    def __init__(
        self,
        parent,
        clientes: List[ClienteTemas],
        can_edit: bool = False,
        on_save: Optional[Callable[[List[ClienteTemas]], None]] = None,
    ):
        super().__init__(parent)

        self.can_edit = can_edit
        self.on_save = on_save

        ttk.Label(self, text="Clientes y temas de interés", style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        # Aviso de modo
        mode_txt = "Modo administrador: edición habilitada." if self.can_edit else "Modo usuario: solo lectura."
        ttk.Label(self, text=mode_txt, style="Subtitle.TLabel").pack(anchor="w", pady=(0, 10))

        # Botón Guardar (solo admin)
        top_actions = ttk.Frame(self)
        top_actions.pack(fill="x", pady=(0, 8))

        self.btn_save = ttk.Button(top_actions, text="Guardar cambios", command=self._save_changes)
        if self.can_edit:
            self.btn_save.pack(side="right")
        else:
            # lo ocultamos en modo user
            pass

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # Estado en memoria (UI)
        self._clientes: Dict[str, List[str]] = {c.nombre: list(c.temas_interes) for c in clientes}

        for c in clientes:
            self._build_cliente_tab(c.nombre)

        if not clientes:
            empty = ttk.Label(self, text="No hay clientes configurados.", style="Subtitle.TLabel")
            empty.pack(anchor="w", padx=10, pady=10)

    def _build_cliente_tab(self, cliente: str):
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text=cliente)

        top = ttk.Frame(tab)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Temas de interés", style="Subtitle.TLabel").pack(side="left")

        actions = ttk.Frame(top)
        actions.pack(side="right")

        btn_add = ttk.Button(actions, text="Agregar", command=lambda: self._add_tema(cliente))
        btn_del = ttk.Button(actions, text="Eliminar", command=lambda: self._remove_selected(cliente))

        if self.can_edit:
            btn_add.pack(side="left", padx=(0, 6))
            btn_del.pack(side="left")
        else:
            # modo user: ocultamos los botones
            pass

        # Lista
        body = ttk.Frame(tab)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        lb = tk.Listbox(body, height=18)
        lb.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(body, orient="vertical", command=lb.yview)
        scroll.pack(side="right", fill="y")
        lb.configure(yscrollcommand=scroll.set)

        # guarda referencia
        tab._lb = lb  # type: ignore[attr-defined]

        # carga datos
        self._refresh_listbox(cliente, lb)

    def _refresh_listbox(self, cliente: str, lb: tk.Listbox):
        lb.delete(0, tk.END)
        temas = self._clientes.get(cliente, [])
        for t in sorted(set(temas), key=lambda x: x.lower()):
            lb.insert(tk.END, t)

    def _add_tema(self, cliente: str):
        if not self.can_edit:
            return

        # mini-dialog
        dialog = tk.Toplevel(self.winfo_toplevel())
        dialog.title(f"Agregar tema - {cliente}")
        dialog.geometry("420x160")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Tema de interés:").pack(anchor="w", padx=12, pady=(12, 6))
        var = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=var)
        entry.pack(fill="x", padx=12)
        entry.focus_set()

        def ok():
            tema = (var.get() or "").strip()
            if not tema:
                messagebox.showwarning("Dato requerido", "Escribe un tema.")
                return

            temas = self._clientes.setdefault(cliente, [])
            # evitar duplicados case-insensitive
            if tema.lower() in {t.lower() for t in temas}:
                messagebox.showinfo("Duplicado", "Ese tema ya existe para este cliente.")
                return

            temas.append(tema)

            tab = self.nb.nametowidget(self.nb.select())
            lb = getattr(tab, "_lb", None)
            if lb:
                self._refresh_listbox(cliente, lb)

            dialog.destroy()

        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=12, pady=12)
        ttk.Button(btns, text="Cancelar", command=dialog.destroy).pack(side="right")
        ttk.Button(btns, text="Guardar", command=ok).pack(side="right", padx=(0, 8))

        entry.bind("<Return>", lambda e: ok())

    def _remove_selected(self, cliente: str):
        if not self.can_edit:
            return

        tab = self.nb.nametowidget(self.nb.select())
        lb: tk.Listbox | None = getattr(tab, "_lb", None)
        if not lb:
            return

        sel = lb.curselection()
        if not sel:
            messagebox.showinfo("Selecciona un tema", "Selecciona un tema para eliminar.")
            return

        tema = lb.get(sel[0])
        if not messagebox.askyesno("Confirmar", f"¿Eliminar '{tema}' de {cliente}?"):
            return

        temas = self._clientes.get(cliente, [])
        self._clientes[cliente] = [t for t in temas if t != tema]
        self._refresh_listbox(cliente, lb)

    def _save_changes(self):
        if not self.can_edit:
            return
        if not self.on_save:
            messagebox.showwarning("Sin guardado", "No hay función configurada para guardar cambios.")
            return

        try:
            clientes_out: List[ClienteTemas] = []
            for nombre, temas in self._clientes.items():
                clean = [t.strip() for t in temas if (t or "").strip()]
                clientes_out.append(ClienteTemas(nombre=nombre.strip(), temas_interes=clean))

            self.on_save(clientes_out)
            messagebox.showinfo("Guardado", "Cambios guardados correctamente.")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo guardar:\n{ex}")
