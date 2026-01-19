import tkinter as tk
from tkinter import ttk


class DatePicker(ttk.Frame):
    """
    DatePicker simple:
    - Si tkcalendar está instalado, usa DateEntry (con calendario).
    - Si no, usa Entry normal.
    Devuelve fecha en YYYY-MM-DD.
    """
    def __init__(self, parent, textvariable: tk.StringVar, width: int = 20):
        super().__init__(parent)
        self.textvariable = textvariable

        self._use_tkcalendar = False
        self._widget = None

        try:
            from tkcalendar import DateEntry  # type: ignore
            self._use_tkcalendar = True
            self._widget = DateEntry(
                self,
                textvariable=self.textvariable,
                width=width,
                date_pattern="yyyy-mm-dd"
            )
            self._widget.pack(side="left")
        except Exception:
            # fallback a entry simple
            self._widget = ttk.Entry(self, textvariable=self.textvariable, width=width)
            self._widget.pack(side="left")

    def get(self) -> str:
        return (self.textvariable.get() or "").strip()
