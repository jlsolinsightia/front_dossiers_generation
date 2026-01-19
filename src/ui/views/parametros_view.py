import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from src.ui.components.datepicker import DatePicker

def _validate_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False


class ParametrosView(ttk.Frame):
    def __init__(self, parent, on_review):
        super().__init__(parent)
        self.on_review = on_review

        ttk.Label(self, text="Parámetros", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        form = ttk.Frame(self)
        form.pack(anchor="w")

        ttk.Label(form, text="Desde").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=6)
        self.date_from_var = tk.StringVar(value="")
        self.dp_from = DatePicker(form, textvariable=self.date_from_var, width=28)
        self.dp_from.grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(form, text="Hasta").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=6)
        self.date_to_var = tk.StringVar(value="")
        self.dp_to = DatePicker(form, textvariable=self.date_to_var, width=28)
        self.dp_to.grid(row=1, column=1, sticky="w", pady=6)

        actions = ttk.Frame(self)
        actions.pack(anchor="w", pady=(10, 0))

        ttk.Button(actions, text="Revisar Fechas", style="Primary.TButton", command=self._review).pack(side="left")

        self.hint = ttk.Label(
            self,
            text="Tip: usa formato YYYY-MM-DD. Ejemplo: 2026-01-01",
            style="Subtitle.TLabel",
        )
        self.hint.pack(anchor="w", pady=(10, 0))

    def _review(self):
        date_from = self.dp_from.get()
        date_to = self.dp_to.get()

        if not date_from or not date_to:
            messagebox.showwarning("Faltan fechas", "Selecciona fecha 'Desde' y 'Hasta'.")
            return

        if not _validate_date(date_from) or not _validate_date(date_to):
            messagebox.showerror("Formato inválido", "Las fechas deben tener formato YYYY-MM-DD.")
            return

        # callback
        self.on_review(date_from, date_to)
