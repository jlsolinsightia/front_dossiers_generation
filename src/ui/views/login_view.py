from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from src.services.auth_service import AuthService, AuthResult
from PIL import Image, ImageTk
from pathlib import Path

class LoginView(ttk.Frame):
    def __init__(
        self,
        parent,
        auth: AuthService,
        on_success: Callable[[AuthResult], None],
        app_name: str = "Dossiers App",
    ):
        super().__init__(parent)
        self.auth = auth
        self.on_success = on_success

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.show_pw_var = tk.BooleanVar(value=False)
        self.error_var = tk.StringVar(value="")

        # =========================
        # Banner superior
        # =========================
        # Ruta absoluta: .../tu_proyecto/data/assets/images/safie_banner.jpg
        banner_path = (Path(__file__).resolve().parents[3] / "data" / "assets" / "images" / "safie_banner.jpg")
        print("BANNER PATH:", banner_path)


        if banner_path.exists():
            try:
                img = Image.open(banner_path)

                # Ajuste de tamaño (opcional, recomendado)
                # Mantiene proporción y limita altura
                max_height = 300
                w, h = img.size
                if h > max_height:
                    ratio = max_height / h
                    img = img.resize((int(w * ratio), max_height), Image.LANCZOS)

                self._banner_img = ImageTk.PhotoImage(img)

                # Contenedor del banner (ocupa todo el ancho)
                banner_container = ttk.Frame(self)
                banner_container.pack(fill="x", pady=(5, 5))

                # Label centrado
                banner_label = ttk.Label(banner_container, image=self._banner_img)
                banner_label.pack(anchor="center")

            except Exception as ex:
                print(f"No se pudo cargar banner: {ex}")

        # =========================
        # Contenedor del login
        # =========================

        # Layout centrado
        container = ttk.Frame(self)
        container.pack(expand=True)

        ttk.Label(container, text=app_name, style="Title.TLabel").pack(pady=(0, 10))
        ttk.Label(container, text="Inicia sesión para continuar", style="Subtitle.TLabel").pack(pady=(0, 16))

        form = ttk.Frame(container)
        form.pack()

        ttk.Label(form, text="Usuario").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.e_user = ttk.Entry(form, textvariable=self.username_var, width=34)
        self.e_user.grid(row=1, column=0, sticky="we", pady=(0, 10))

        ttk.Label(form, text="Contraseña").grid(row=2, column=0, sticky="w", pady=(0, 4))
        self.e_pw = ttk.Entry(form, textvariable=self.password_var, width=34, show="•")
        self.e_pw.grid(row=3, column=0, sticky="we", pady=(0, 6))

        chk = ttk.Checkbutton(form, text="Mostrar contraseña", variable=self.show_pw_var, command=self._toggle_pw)
        chk.grid(row=4, column=0, sticky="w", pady=(0, 10))

        self.lbl_error = ttk.Label(form, textvariable=self.error_var, foreground="#b00020")
        self.lbl_error.grid(row=5, column=0, sticky="w", pady=(0, 10))

        self.btn = ttk.Button(form, text="Entrar", command=self._do_login)
        self.btn.grid(row=6, column=0, sticky="we", pady=(0, 8))

        # Enter = login
        self.e_user.bind("<Return>", lambda e: self._do_login())
        self.e_pw.bind("<Return>", lambda e: self._do_login())

        # foco inicial
        self.after(100, lambda: self.e_user.focus_set())

    def _toggle_pw(self):
        self.e_pw.configure(show="" if self.show_pw_var.get() else "•")

    def _do_login(self):
        self.error_var.set("")
        u = self.username_var.get()
        p = self.password_var.get()

        res = self.auth.authenticate(u, p)
        if not res.ok:
            self.error_var.set(res.error or "No se pudo autenticar.")
            return

        self.on_success(res)
