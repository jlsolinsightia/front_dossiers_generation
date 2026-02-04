import tkinter as tk
from tkinter import ttk, messagebox
import threading
import traceback

from src.config.settings import Settings
from src.ui.styles import apply_styles
from src.services.dossier_repository import build_repository, DossierQuery
from src.services.dossier_mapper import normalize_for_ui_both_chambers
from src.ui.views.parametros_view import ParametrosView
from src.ui.views.resultados_view import ResultadosView

# auth + login view
from src.services.auth_service import build_auth_service, AuthResult
from src.ui.views.login_view import LoginView

from src.services.clientes_repository import ClientesRepositoryFile, ClienteTemas
from src.ui.views.clientes_view import ClientesView


def run_app():
    settings = Settings()

    root = tk.Tk()
    root.title(f"{settings.APP_NAME} v{settings.APP_VERSION}")
    root.geometry("1100x700")
    root.minsize(980, 640)

    apply_styles(root)

    # Servicios
    repo = build_repository(settings)
    auth = build_auth_service(settings)

    # Repo de clientes (una sola instancia)
    clientes_repo = ClientesRepositoryFile(settings.CLIENTES_TEMAS_PATH)

    container = ttk.Frame(root)
    container.pack(fill="both", expand=True)

    # Estado UI
    login_view: LoginView | None = None
    main_frame: ttk.Frame | None = None

    # Estado sesión
    session_user: str | None = None
    session_role: str | None = None

    # Cache de clientes (para combo en Parámetros)
    clientes_combo: list[str] = []

    def clear_container_frame(frame: ttk.Frame | None):
        if frame is not None:
            frame.destroy()

    def load_clientes_for_ui() -> tuple[list[ClienteTemas], list[str]]:
        """
        Tu repo devuelve List[ClienteTemas].
        Regresamos:
          - clientes_data: List[ClienteTemas] para ClientesView
          - nombres: List[str] para combobox de ParametrosView
        """
        try:
            clientes_data = clientes_repo.load() or []
        except Exception as ex:
            print("No se pudieron cargar clientes:", ex)
            clientes_data = []

        nombres = [c.nombre for c in clientes_data if (c.nombre or "").strip()]

        if not nombres:
            nombres = ["Abbott", "Aeroméxico", "Comex", "Mercado Libre"]

        # quitar duplicados conservando orden
        seen = set()
        uniq: list[str] = []
        for n in nombres:
            if n not in seen:
                uniq.append(n)
                seen.add(n)

        return clientes_data, uniq

    def show_login():
        nonlocal login_view, main_frame, session_user, session_role

        clear_container_frame(main_frame)
        main_frame = None

        session_user = None
        session_role = None

        login_view = LoginView(
            container,
            auth=auth,
            on_success=on_login_success,
            app_name=settings.APP_NAME,
        )
        login_view.pack(fill="both", expand=True)

    def on_login_success(res: AuthResult):
        nonlocal login_view, session_user, session_role
        session_user = res.username
        session_role = res.role

        if login_view is not None:
            login_view.destroy()
            login_view = None

        show_main()

    def logout():
        show_login()

    def show_main():
        nonlocal main_frame, session_user, session_role, clientes_combo

        main_frame = ttk.Frame(container)
        main_frame.pack(fill="both", expand=True)

        # role normalized
        role = (session_role or "").strip().lower()
        is_admin = role == "admin"

        # Header con usuario + logout
        header = ttk.Frame(main_frame)
        header.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(
            header,
            text=f"Usuario: {session_user or ''} ({session_role or ''})",
            style="Subtitle.TLabel",
        ).pack(side="left")

        ttk.Button(header, text="Cerrar sesión", command=logout).pack(side="right")

        # Cargar clientes para tabs + combobox
        clientes_data, clientes_combo = load_clientes_for_ui()

        # Notebook principal
        nb = ttk.Notebook(main_frame)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        tab_clientes = ttk.Frame(nb)
        tab_param = ttk.Frame(nb)
        tab_res = ttk.Frame(nb)

        # Orden de tabs: Clientes / Parámetros / Resultados
        nb.add(tab_clientes, text="Clientes")
        nb.add(tab_param, text="Parámetros")
        nb.add(tab_res, text="Resultados")

        # ✅ Si NO es admin, deshabilita la pestaña Clientes
        if not is_admin:
            nb.tab(tab_clientes, state="disabled")

        # --- Clientes tab (editable solo si admin)
        clientes_view = ClientesView(
            tab_clientes,
            clientes=clientes_data,         # List[ClienteTemas]
            can_edit=is_admin,
            on_save=(lambda updated: clientes_repo.save(updated)) if is_admin else None,
        )
        clientes_view.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Resultados tab
        resultados_view = ResultadosView(tab_res, template_path=str(settings.TEMPLATE_DOCX_PATH))
        resultados_view.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Callback de revisión
        def on_review(cliente: str, date_from: str, date_to: str):
            resultados_view.set_status("Cargando dossier...")

            def work():
                q = DossierQuery(cliente=cliente, camara="ALL", desde=date_from, hasta=date_to)
                payload = repo.get_dossier(q)
                vm = normalize_for_ui_both_chambers(payload, date_from, date_to)
                return vm

            def ok(vm):
                resultados_view.set_cliente(cliente)
                resultados_view.render(vm, date_from=date_from, date_to=date_to)
                nb.select(tab_res)

            def err(ex):
                resultados_view.set_status("Error al cargar.")
                print("ERROR:", repr(ex))
                traceback.print_exception(type(ex), ex, ex.__traceback__)
                messagebox.showerror("Error", f"No se pudo cargar el dossier:\n{ex}")

            def runner():
                try:
                    vm = work()
                    root.after(0, lambda: ok(vm))
                except Exception as ex:
                    root.after(0, lambda ex=ex: err(ex))

            threading.Thread(target=runner, daemon=True).start()

        # --- Parámetros tab (pasamos lista de clientes)
        parametros_view = ParametrosView(tab_param, on_review=on_review, clientes=clientes_combo)
        parametros_view.pack(fill="both", expand=True, padx=10, pady=10)

    # Arranca en login
    show_login()
    root.mainloop()
